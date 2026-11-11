# Recorded Runs

Open http://localhost:3000/d/osprey-recorded. Click a session in Saved runs to
load its full time range. The plots match live CAN3 colors, units and thresholds.
Drag on a plot to zoom in; the last-value cards follow the selected time window.
Automatic refresh is off. Current scaling factors apply to historical raw data.
The catalog lists the past 365 days filtered by USB receiver or Simulation.

Live CAN3 has only the Input selector and shows incoming telemetry across
sessions in its selected live time window. Use Recorded Runs for session review.
CSV controls, CSV panels and the Bristol imported demonstration run were removed.
The PostgreSQL importer remains available separately; CAN3 recordings are in
InfluxDB and local JSONL files. No real CAN3 recordings were removed.

## Run names

The November 11 all-channel shop run is displayed as
`2026-11-11__17-11-50__shop__no-driver` (Eastern start time).
Its underlying database session remains `can3-all-live-20261111`, preserving
sample identity. The mapping is recorded in `config/run-names.json` and applied
to the dashboard run selector, catalog and filters. Run names have no extension.

Review telemetry directly in Grafana. InfluxDB is the main storage and local
JSONL recordings are retained for recovery. The CSV export workflow was removed.
