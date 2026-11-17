# Osprey Racing telemetry

The ESP32 sends CAN3 readings over USB to a Python receiver. The receiver saves
them to local InfluxDB and a JSONL recovery recording. Grafana displays live
readings and saved runs. Completed USB recordings can be copied automatically
to the team's Google Drive folder.

- [First-time setup](docs/setup.md): install dependencies, configure credentials and Drive, and prepare the ESP32.
- [Daily operation](docs/session-quickstart.md): start a named run, stop, review, share and replay recordings.
- [Technical reference](docs/technical-reference.md): data format, channel map, factors, thresholds and troubleshooting details.

| Dashboard | Purpose |
| --- | --- |
| [CAN3](http://localhost:3000/d/osprey-can3) | Live USB/Simulation readings; refreshes every second. |
| [Recorded Runs](http://localhost:3000/d/osprey-recorded) | Saved USB sessions; click a run to load its time range. |

GitHub shares code and dashboard configuration. Telemetry recordings, database
volumes, backups and `.env` credentials remain local. Completed JSONL recordings
are shared through Google Drive and imported into local InfluxDB instances for
analysis in Grafana.

## Project layout

- `firmware/can3_stream/`: all-channel ESP32 streaming sketch.
- `scripts/`: start capture, replay recordings, retry Drive copies and create credentials.
- `src/osprey_telemetry/live/`: receiver, recording, Drive copy and channel definitions.
- `config/grafana/`: both dashboard definitions and datasource provisioning.
- `data/recordings/`: local JSONL recordings, excluded from Git.
- `backups/`: local backups, excluded from Git.
- `tests/`: receiver, recovery and Drive-copy checks.

The runtime uses only InfluxDB and Grafana. Retired CSV/PostgreSQL/Prometheus
files and old CSV exports were archived locally under `backups/legacy-csv-cleanup-2026-11-17/`.
Their existing Docker volumes were not deleted.
