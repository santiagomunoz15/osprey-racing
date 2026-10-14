# Osprey Racing telemetry

Recorded runs: MoTeC CSV -> Python importer -> PostgreSQL -> Grafana.
Live telemetry: car -> receiving ESP32 -> USB Python receiver -> InfluxDB -> Grafana.
See [USB receiver setup and tests](docs/usb-receiver.md).

## Start

Install and start Docker Desktop. From the project root:

```sh
python scripts/setup-env.py
docker compose config --quiet
docker compose up -d postgres grafana
docker compose run --rm --build importer /data/examples/bristol.csv --timezone America/New_York
```

On macOS, use python3 where python is unavailable. Docker commands work on both platforms.
Open http://localhost:3000. Log in as admin using GRAFANA_ADMIN_PASSWORD from .env.
Open Dashboards > Osprey Racing > Recorded Runs and choose a run and channel.

## Layout

- src/osprey_telemetry/: CSV importer, format parsers, and future live receiver.
- data/examples/: shareable test exports; bristol.csv is the original demonstration sample.
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
