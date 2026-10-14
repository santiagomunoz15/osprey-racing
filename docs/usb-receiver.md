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
The receiver does not create buckets. The existing telemetry-test bucket expires data after one day.
Choose a team-approved bucket/retention before recording real testing sessions.

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

Start the existing influxdb-test container with docker start influxdb-test and run
docker compose up -d postgres grafana to load the provisioned USB telemetry data source.
The InfluxDB container must share the osprey-telemetry_default Docker network.
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

This first receiver keeps its queue in memory. Closing it, Ctrl+C, or losing power can lose unwritten points;
shutdown reports their count. It is not a durable offline logger. HTTP writes have a 5-second timeout.
Measured synthetic throughput does not establish the real radio/USB performance. Test with the hardware
at its actual rate before a car session. Future work includes disk buffering and sensor-side timing.
