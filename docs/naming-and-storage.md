# Naming and storage

## Recorded runs

Folder: data/raw/YYYY/YYYY-MM-DD_event/
Filename: YYYY-MM-DD_HHMMSS-TZ_car_session_run-NNN_format.csv

Example: data/raw/2026/2026-10-11_unf-testing/2026-10-11_143025-0400_or26_skidpad_run-001_motec.csv

Use the recorded run start, a 24-hour clock, and the numeric UTC offset (-0400 for Eastern daylight time,
-0500 for Eastern standard time). If the time is unknown, use unknown-time rather than inventing a time.
Confirm the team's car identifier; or26 is an example.
Use practice, skidpad, autocross, acceleration, or endurance for sessions.
Number runs from 001 within each event. Use lowercase names and no spaces.
The importer does not extract timing from filenames; its --timezone must match the logger clock.
Keep original CSV contents unchanged. Put derived exports in data/processed/ with the same run stem
and a descriptive suffix, such as _filtered.csv.

Copy docs/session-notes-template.md into each event directory as session-notes.md.
Raw and processed event folders can be committed to the private team repository.
Keep backups of complete recordings and session notes in shared team storage as well.
Never commit .env, API tokens, or database backups.
The supplied bristol.csv retains its original vendor/sample name under data/examples/.

## Other names

- Configuration files and folders: lowercase with hyphens, such as engine-rpm-high.json.
- Python modules and functions: lowercase with underscores, such as import_csv.py.
- Grafana dashboard titles: readable names, such as Osprey Racing - Live Telemetry.
- Alert titles: source, signal, condition; for example Live - Engine RPM above 9000.
- InfluxDB measurement/field names: lowercase with underscores, such as engine and rpm.
- Include units where ambiguous: speed_mps, oil_pressure_kpa, coolant_temperature_c.
- Keep stable Grafana dashboard, data-source, and alert UIDs across computers.
