# Osprey Racing telemetry

Recorded MoTeC CSV -> PostgreSQL -> Grafana. Future live exporter -> Prometheus -> Grafana.

## Start on macOS or Windows

Install Docker Desktop with Linux containers and start it. From this directory:

The Docker commands below work in both macOS Terminal and Windows PowerShell.

```powershell
docker compose config --quiet
docker compose up -d
docker compose run --rm --build importer /data/bristol.csv --timezone America/New_York
```

Open http://localhost:3000 and log in as **admin** using GRAFANA_ADMIN_PASSWORD from the generated local .env file.
Open Dashboards > Osprey Racing > Osprey Racing — Recorded Runs.
Choose the run, then a channel. The graph deliberately queries the entire run regardless of the global time picker.
Refresh the dashboard after importing another CSV.

Import another file placed in this folder:

```powershell
docker compose run --rm importer /data/your-run.csv --name "Practice run 1" --timezone America/New_York
```

Only MoTeC exports matching the sample format are supported initially. Unknown formats fail explicitly.
The log date/time is a local clock without timezone information: confirm the logger's timezone and pass --timezone accordingly.
Start Time plus sample index / Sample Rate determines timestamps. Blank values stay missing; malformed rows fail the import.
The file and chosen timezone identify each run; importing the same file twice does not duplicate it.
Imports are atomic. Original metadata, channel units, elapsed seconds, and every CSV sample are retained.
The pandas compatibility helper is optional and requires pandas; the importer does not.

Validate a file without Docker using Python plus tzdata (required on Windows):

On macOS, use a local virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python import_csv.py bristol.csv --dry-run
python -B -m unittest discover -s tests
```

On Windows:

```powershell
python -m pip install -r requirements.txt
python import_csv.py bristol.csv --dry-run
python -B -m unittest discover -s tests
```

## Storage and operation

PostgreSQL and Grafana use persistent Docker volumes. Grafana has a read-only database account.
Initialization scripts run only when PostgreSQL's data volume is first created.
The generated .env contains random local passwords; keep it private and retain it.
Changing .env does not automatically update passwords inside an existing database or Grafana volume.
docker compose down stops services while retaining data. Avoid down -v: it deletes stored runs and dashboards.
Back up PostgreSQL before moving to another host.
Image tags are initial development defaults; pin tested versions before deploying the team server.

## Future live telemetry

```powershell
docker compose --profile live up -d
```

Prometheus is at http://localhost:9090. The car_exporter target stays down until an exporter exposes /metrics on host port 8000.
There is no live exporter implemented yet. Edit prometheus.yml when the car connection is known.
A one-second scrape is an initial live monitoring setting, not a way to retain every 50 Hz vehicle sample.
Keep raw telemetry recording alongside live metrics if full-resolution run analysis is needed.
The Grafana Live telemetry source is preconfigured but unavailable until this profile is started.

## Phone and portable access

Initially Grafana binds to localhost. After the laptop setup works, move this same stack to an always-on pit computer
or an ARM-compatible Raspberry Pi with adequate storage. A phone can then open Grafana over the same Wi-Fi.
For LAN access change the Grafana port binding to "3000:3000", allow port 3000 on the private-network firewall,
and browse to http://PIT-COMPUTER-IP:3000. Use authenticated access; do not expose database ports or forward Grafana to the internet.
A phone provides the viewer; the server still stores and processes telemetry.
