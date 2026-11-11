# ESP32 USB receiver

Car -> wireless -> receiving ESP32 -> USB -> Python receiver -> InfluxDB -> Grafana.
Run Python directly on the laptop so it can access its USB ports; InfluxDB runs in Docker.

## Setup

From the project root, install the live dependency:

```sh
python -m pip install "pyserial>=3.5,<4"
```

Keep INFLUX_DB_API_TOKEN in .env. INFLUX_DB_API is also accepted for older setups.
Defaults are http://127.0.0.1:8086, organization osprey-racing, bucket telemetry-test.
Override with INFLUX_URL, INFLUX_ORG, INFLUX_BUCKET or --url, --org, --bucket.
Use a token with write permission for the chosen bucket. Keep credentials out of Git.
Run `python scripts/setup-env.py`, then `docker compose up -d influxdb postgres grafana`.
On first startup, InfluxDB creates the configured organization and bucket. The local bucket has no
automatic expiry. Its data is stored in persistent Docker volumes; do not use `docker compose down -v`.

## Test without hardware

```sh
python scripts/receive-usb.py --simulate --samples 100 --rate 50 --dry-run
python scripts/receive-usb.py --simulate --samples 100 --rate 50
```

The first command prints points; the second writes two seconds of simulated measurements into InfluxDB.
Simulation has source=simulation and cannot be mistaken for source=usb.

## Connect the receiver ESP32

Close Arduino Serial Monitor and any other program using the port. Connect by USB and list ports:

```sh
python scripts/receive-usb.py --list-ports
python scripts/receive-usb.py --port COM5 --dry-run
python scripts/receive-usb.py --port COM5
```

Replace COM5 with the detected Windows port. On macOS use a path such as /dev/cu.usbserial-1430
(and python3 if python is unavailable). The default baud is 115200, matching the screenshot.
Stop with Ctrl+C. Opening a serial port can reset some ESP32 boards; startup text is ignored.
Automatic reconnection retries the same port every two seconds.

Expected messages end in newline and have this format (ASCII -> or Unicode arrow are accepted):

```text
Received Data -> Brake Pressure: 0.0 | Throttle: 12.0%
```

Stored measurement: vehicle. Fields: brake_pressure_raw and throttle_pct.
Brake-pressure units are unconfirmed, so the receiver does not label or convert them as bar/psi.
Tags: device, source, session. Start a new process/session for each recording.
Timestamps reflect laptop receipt time, not sensor acquisition time. Use ESP32 timestamps and sequence
numbers later to measure wireless delay and packet loss.

## Grafana

Open http://localhost:3000/d/osprey-usb-live (Osprey Racing - Live USB Telemetry).
Choose Simulation to verify generated data, or USB receiver for real messages.
The dashboard shows throttle and brake-pressure traces plus latest readings. It refreshes every 5 seconds
and defaults to the last 5 minutes. Latest-reading cards require a point from the last 10 seconds;
otherwise they show No recent data. Historical traces remain visible in the selected time window.

For a visible one-minute test, run:

```sh
python scripts/receive-usb.py --simulate --samples 3000 --rate 50
```

Run `docker compose up -d influxdb postgres grafana` to start the database and dashboard.
Compose puts both services on the same network; Grafana connects to `http://influxdb:8086`.
INFLUX_DB_API_TOKEN needs read permission for Grafana and write permission for the receiver.
On another computer, configure its own .env and InfluxDB instance; Git does not transfer credentials
or Docker volumes. The new dashboard and data-source files do transfer through Git.

Use the existing Flux data source with access to telemetry-test. In Explore or a time-series panel:

```flux
from(bucket: "telemetry-test")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "vehicle")
  |> filter(fn: (r) => r._field == "throttle_pct" or r._field == "brake_pressure_raw")
  |> filter(fn: (r) => r.source == "simulation")
```

Change source to usb for actual receiver readings. Use Last 5 minutes and a 1-second refresh.
Put throttle and pressure in separate panels because their units differ.
The existing simulated RPM alert is unchanged; this stream has no RPM field.

## Performance and limitations

USB reads run in a dedicated thread. Database writes are batched at 50 points or every 0.5 seconds,
so a network request is not made for each sample. A bounded queue holds 5,000 pending points.
Failed writes retry with the original timestamps. While retrying, USB reading continues; when the queue
fills, new measurements are dropped and the count is logged. Malformed and oversized lines are counted.
The startup/session and batch/final counters show received, invalid, dropped, and written measurements.
Dry-run written means printed, not stored. A lost response may cause a safe retry of an already-written point.

The upload queue is in memory, but complete received messages are recorded locally before enqueueing.
Shutdown reports unsent queued points; use recording replay to recover them. HTTP writes have a 5-second timeout.
Measured synthetic throughput does not establish the real radio/USB performance. Test with the hardware
at its actual rate before a car session. Future work includes disk buffering and sensor-side timing.

## Local recordings and recovery

The receiver now saves every complete decoded serial message to a new JSONL file under
`data/recordings/` **before** queuing a valid measurement for InfluxDB. Each append is flushed
and synced to disk. The startup log prints the filename. Files are ignored by Git and never
overwritten. They contain a session header, original message text, receipt timestamps, and the
exact database points; invalid complete messages are retained with a null point.

Record and upload together:

```sh
python scripts/receive-usb.py --port /dev/cu.usbserial-1430 --session shop-test-001
```

Choose a filename or record without a running database/token:

```sh
python scripts/receive-usb.py --port /dev/cu.usbserial-1430 --session shop-test-002 --record data/recordings/shop-test-002.jsonl --local-only
```

`--dry-run` still prints instead of uploading, but now also records locally. Simulation is
recorded with `source=simulation`. Use a fresh session name for each run.

Validate and print a recording, then upload/recover it:

```sh
python scripts/replay-usb.py data/recordings/shop-test-002.jsonl --dry-run
python scripts/replay-usb.py data/recordings/shop-test-002.jsonl
```

Replay validates the entire file before sending any data. It preserves original timestamps,
source, device, and session, so re-uploading the same points to the same bucket is safe.
It uploads in batches rather than replaying at the original speed; `--interval 1` pauses one
second between batches. To see historical uploads, select the original run's date/time range
in Grafana. Replaying old data does not make the live latest-reading cards current.

During database outages the USB reader keeps saving locally. If the upload queue fills,
`dropped` counts measurements skipped for live upload, not deleted from the recording.
After Ctrl+C or a failed upload, replay the file to recover all recorded valid points.
Disk write failures stop capture with an error rather than silently continuing without a recording.

Files are local backups, not protection against laptop/disk loss: copy completed runs to team
storage. Partial serial lines at disconnect/shutdown and oversized lines rejected by the framer
are not recorded. Disk synchronization can limit capture throughput and cannot recover packets
lost before Python receives them. Test the real hardware rate. A damaged/truncated JSONL file
is rejected by replay; preserve the original before repairing a copy.
