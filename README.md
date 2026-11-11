# Osprey Racing telemetry

For daily operation, see [Start Grafana and record a named CAN3 session](docs/session-quickstart.md).

Live capture: car -> receiving ESP32 -> USB Python receiver -> InfluxDB -> Grafana.
Recorded Runs reviews the same InfluxDB readings by session and time range.
The receiver also saves local JSONL recordings for recovery.

## Start

Open Docker Desktop and close Arduino Serial Monitor. From the project root:

```sh
python3 scripts/setup-env.py
docker compose up -d influxdb postgres grafana
.venv/bin/python scripts/receive-usb.py --list-ports
session_name="$(TZ=America/New_York date '+%Y-%m-%d__%H-%M-%S')__shop__no-driver"
.venv/bin/python scripts/start-can3.py --port /dev/cu.usbserial-1410 --session "$session_name"
```

Use the detected USB port. See the quick-start guide above for Python environment
setup assumptions, recording checks, stopping, and recovery. Open
http://localhost:3000/d/osprey-can3 for live telemetry or
http://localhost:3000/d/osprey-recorded for saved runs. Log in as admin using
GRAFANA_ADMIN_PASSWORD from .env. Press Ctrl+C in the receiver Terminal to stop
capture; saved readings remain available. Use a unique session name for each run.

## Layout

- src/osprey_telemetry/: CAN receiver, local recording/replay, and optional MoTeC CSV importer.
- data/examples/: optional shareable test exports.
- data/raw/: untouched full recordings, grouped by year and testing event.
- data/processed/: derived data, kept separate from original recordings.
- config/grafana/: dashboard, data-source, and alert provisioning.
- config/postgres/: database initialization.
- config/influxdb/: reserved for the live database configuration.
- config/prometheus/: legacy configuration retained during the InfluxDB transition.
- scripts/: commands for starting services, creating credentials, and importing runs.
- tests/: parser checks.
- docs/: setup, file naming, telemetry format, and session notes.

See [setup](docs/setup.md), [naming and storage](docs/naming-and-storage.md),
and [telemetry format](docs/telemetry-format.md).

## Import future runs

Place recordings under data/raw/YYYY/YYYY-MM-DD_event/.
From the project root, for example:

```sh
python scripts/import-run.py data/raw/2026/2026-10-11_unf-testing/2026-10-11_143025-0400_or26_skidpad_run-001_motec.csv --timezone America/New_York
```

The filename is for organization; the importer reads timing from CSV metadata and --timezone.
Duplicate detection uses file contents and timezone, so moving or renaming a CSV does not duplicate it.

## CAN3 channels

The 27-channel CAN3 dashboard is at http://localhost:3000/d/osprey-can3.
See [CAN3 capture and decoding status](docs/can3.md) for the channel map, USB frame
format, simulation command, and pending engineering conversions.
