# Setup and operation

## Docker

Run commands from the project root:

```sh
python scripts/setup-env.py
docker compose config --quiet
docker compose up -d postgres grafana
docker compose run --rm --build importer /data/examples/bristol.csv --timezone America/New_York
```

Alternatively, python scripts/start.py starts the services from any working directory.
The importer mounts only data/ at /data inside its container.
Refresh Grafana after importing. The recorded-run chart uses elapsed seconds and queries the complete selected run.
The RPM alert checks the maximum Engine RPM in the latest run by recorded start time; it is not a live alert.

## Local Python

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m osprey_telemetry.import_csv data/examples/bristol.csv --dry-run
python -B -m unittest discover -s tests
```

macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m osprey_telemetry.import_csv data/examples/bristol.csv --dry-run
python -B -m unittest discover -s tests
```

The optional parse_motec_csv compatibility helper additionally requires pandas.

## Persistent storage

Existing volume names remain postgres_data and grafana_data within the Compose project.
Restarting or recreating containers retains these volumes. Do not use docker compose down -v.
Database initialization runs only for a new database volume.
Keep .env private. Regenerating it or changing its values does not update passwords already stored in the databases.
Back up PostgreSQL and Grafana data before moving computers; Git does not transfer Docker volumes.
Pin tested image versions before a team deployment.

## InfluxDB transition and phone access

Run `python scripts/setup-env.py` to add missing local credentials, then
`docker compose up -d influxdb postgres grafana` for live USB telemetry.
InfluxDB uses persistent volumes and initializes its bucket without automatic expiry.
Existing database credentials are preserved; changing .env does not rotate database credentials.
The old Prometheus service and data-source configuration are retained for compatibility.

Grafana initially binds to localhost. To enable private LAN access later, change its port mapping
to 3000:3000 and permit port 3000 on the private-network firewall. A phone can then visit
http://PIT-COMPUTER-IP:3000. Keep authenticated access and database ports private.
