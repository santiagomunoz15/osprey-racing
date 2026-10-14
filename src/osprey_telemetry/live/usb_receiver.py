"""Read ESP32 USB messages and batch brake/throttle measurements into InfluxDB."""
import argparse
import logging
import math
import os
from pathlib import Path
import queue
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

LOG = logging.getLogger(__name__)
MESSAGE = re.compile(
    r"(?:Received Data\s*(?:->|→)\s*)?Brake Pressure:\s*(\S+)\s*\|\s*Throttle:\s*(\S+)%\s*"
)


def parse_message(line):
    match = MESSAGE.fullmatch(line.strip())
    if not match:
        raise ValueError("Expected Brake Pressure: NUMBER | Throttle: NUMBER%")
    pressure, throttle = map(float, match.groups())
    if not all(math.isfinite(value) for value in (pressure, throttle)):
        raise ValueError("Measurements must be finite")
    if pressure < 0 or not 0 <= throttle <= 100:
        raise ValueError("Pressure must be nonnegative and throttle between 0 and 100")
    return pressure, throttle


class LineFramer:
    """Retain partial USB reads until newline; discard oversized messages."""
    def __init__(self, limit=4096):
        self.buffer = bytearray()
        self.limit = limit
        self.discarding = False
        self.discarded = 0

    def feed(self, data):
        lines = []
        for byte in data:
            if byte == 10:
                if not self.discarding:
                    lines.append(self.buffer.decode("utf-8", errors="replace"))
                self.buffer.clear()
                self.discarding = False
            elif not self.discarding:
                self.buffer.append(byte)
                if len(self.buffer) > self.limit:
                    self.buffer.clear()
                    self.discarding = True
                    self.discarded += 1
        return lines


def load_env(path):
    """Load local settings without replacing values already set in the environment."""
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def tag(value):
    if not value or any(c in value for c in "\r\n"):
        raise ValueError("Tags must be nonempty and contain no newlines")
    return value.replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def make_point(line, timestamp_ns, device, source, session):
    pressure, throttle = parse_message(line)
    return (f"vehicle,device={tag(device)},source={tag(source)},session={tag(session)} "
            f"brake_pressure_raw={pressure},throttle_pct={throttle} {timestamp_ns}")


class InfluxWriter:
    def __init__(self, url, org, bucket, token):
        if urlparse(url).scheme not in ("http", "https"):
            raise ValueError("InfluxDB URL must use http or https")
        self.url = url.rstrip("/") + "/api/v2/write?" + urlencode(
            {"org": org, "bucket": bucket, "precision": "ns"})
        self.token = token

    def write(self, points):
        request = Request(self.url, data="\n".join(points).encode("utf-8"), method="POST",
                          headers={"Authorization": "Token " + self.token, "Content-Type": "text/plain"})
        try:
            with urlopen(request, timeout=5) as response:
                if response.status != 204:
                    raise RuntimeError(f"Unexpected InfluxDB status {response.status}")
        except HTTPError as error:
            # Avoid printing request headers, credentials, or server response bodies.
            raise RuntimeError(f"InfluxDB write rejected (HTTP {error.code})") from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError("InfluxDB connection failed") from None


def collect(args, inbox, stop, stats):
    """USB reads continue in this thread while the main thread writes batches."""
    last_timestamp = 0

    def accept(line):
        nonlocal last_timestamp
        timestamp = max(time.time_ns(), last_timestamp + 1)
        last_timestamp = timestamp
        try:
            point = make_point(line, timestamp, args.device, args.source, args.session)
        except ValueError:
            stats["invalid"] += 1
            return
        stats["received"] += 1
        try:
            inbox.put_nowait(point)
        except queue.Full:
            stats["dropped"] += 1
            LOG.error("Receiver queue full; dropped measurements=%d", stats["dropped"])

    if args.simulate:
        deadline = time.monotonic()
        for index in range(args.samples):
            if stop.is_set():
                break
            accept(f"Received Data -> Brake Pressure: {index % 20 / 10} | Throttle: {index % 101}%")
            deadline += 1 / args.rate
            stop.wait(max(0, deadline - time.monotonic()))
        return
    import serial
    while not stop.is_set():
        framer = LineFramer()
        try:
            with serial.Serial(args.port, args.baud, timeout=0.1) as connection:
                LOG.info("USB connected: %s at %d baud", args.port, args.baud)
                while not stop.is_set():
                    for line in framer.feed(connection.read(max(1, min(connection.in_waiting, 4096)))):
                        accept(line)
                    if framer.discarded:
                        stats["invalid"] += framer.discarded
                        framer.discarded = 0
        except (serial.SerialException, OSError):
            LOG.warning("USB unavailable; reconnecting in 2 seconds")
            stop.wait(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Windows COM port or macOS /dev/cu.usbserial-* path")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--simulate", action="store_true", help="Generate messages without an ESP32")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--rate", type=float, default=50, help="Simulation messages per second")
    parser.add_argument("--dry-run", action="store_true", help="Print measurements without database writes")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--url")
    parser.add_argument("--org")
    parser.add_argument("--bucket")
    parser.add_argument("--device", default="esp32-receiver")
    parser.add_argument("--source", choices=("usb", "simulation"))
    parser.add_argument("--session", default="usb-" + str(time.time_ns()))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--flush-interval", type=float, default=0.5)
    parser.add_argument("--queue-size", type=int, default=5000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.list_ports:
        from serial.tools.list_ports import comports
        ports = list(comports())
        for port in ports:
            print(f"{port.device}: {port.description}")
        if not ports:
            print("No serial ports detected. Connect the receiving ESP32 by USB.")
        return
    if not args.simulate and not args.port:
        parser.error("Choose --port or --simulate")
    if args.port and args.simulate:
        parser.error("Choose either --port or --simulate")
    if not args.simulate:
        try:
            import serial  # Check before starting the background reader.
        except ImportError:
            parser.error('Install the USB dependency: python -m pip install "pyserial>=3.5,<4"')
    if any(v <= 0 for v in (args.baud, args.samples, args.rate, args.batch_size,
                            args.flush_interval, args.queue_size)) or not all(
                                math.isfinite(v) for v in (args.rate, args.flush_interval)):
        parser.error("Rates, sizes, and intervals must be positive and finite")
    args.source = args.source or ("simulation" if args.simulate else "usb")
    for value in (args.device, args.source, args.session):
        tag(value)
    load_env(args.env_file)
    token = os.getenv("INFLUX_DB_API_TOKEN") or os.getenv("INFLUX_DB_API")
    if not args.dry_run and not token:
        parser.error("Set INFLUX_DB_API_TOKEN in .env (never pass tokens on the command line)")
    writer = None if args.dry_run else InfluxWriter(
        args.url or os.getenv("INFLUX_URL", "http://127.0.0.1:8086"),
        args.org or os.getenv("INFLUX_ORG", "osprey-racing"),
        args.bucket or os.getenv("INFLUX_BUCKET", "telemetry-test"), token)
    inbox = queue.Queue(maxsize=args.queue_size)
    stop = threading.Event()
    stats = {"received": 0, "invalid": 0, "dropped": 0, "written": 0}
    reader = threading.Thread(target=collect, args=(args, inbox, stop, stats), daemon=True)
    reader.start()
    pending = []
    last_flush = time.monotonic()
    started = last_flush
    LOG.info("Session: %s; source: %s", args.session, args.source)
    try:
        while reader.is_alive() or not inbox.empty() or pending:
            try:
                pending.append(inbox.get(timeout=0.1))
            except queue.Empty:
                pass
            finished = not reader.is_alive() and inbox.empty()
            if pending and (len(pending) >= args.batch_size or finished or
                            time.monotonic() - last_flush >= args.flush_interval):
                if writer:
                    try:
                        writer.write(pending)
                    except RuntimeError as error:
                        LOG.error("%s; retaining batch and retrying in 2 seconds", error)
                        stop.wait(2)
                        # Leave queued points in the bounded inbox while retrying this batch.
                        while True:
                            try:
                                writer.write(pending)
                                break
                            except RuntimeError as error:
                                LOG.error("%s; retrying in 2 seconds", error)
                                stop.wait(2)
                else:
                    for point in pending:
                        print(point)
                stats["written"] += len(pending)
                pending.clear()
                last_flush = time.monotonic()
                LOG.info("Received=%d written=%d invalid=%d dropped=%d", stats["received"],
                         stats["written"], stats["invalid"], stats["dropped"])
    except KeyboardInterrupt:
        LOG.info("Stopping; unwritten queued points=%d", inbox.qsize() + len(pending))
    finally:
        stop.set()
        reader.join(timeout=2)
        LOG.info("Final: received=%d invalid=%d dropped=%d written=%d elapsed=%.2fs",
                 *stats.values(), time.monotonic() - started)


if __name__ == "__main__":
    main()
