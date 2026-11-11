# Start Grafana and record a CAN3 run

## Before starting

Connect the ESP32 running `firmware/can3_stream/can3_stream.ino` and power the
car/dash when ready to collect data. Close Arduino Serial Monitor: it and the
Python receiver cannot use the USB port simultaneously.

Open Docker Desktop and wait until its engine is running. These instructions
assume this laptop's existing project, `.env`, and Python virtual environment.
```

## 1. Start Grafana and the databases

```sh
docker compose up -d influxdb postgres grafana
```

Open http://localhost:3000/d/osprey-can3. Log in using the existing Grafana
credentials; the configured administrator password is in the local `.env` file.
Choose **USB receiver** for the car. The dashboard refreshes every second.
Starting Grafana alone does not record any telemetry.

## 2. Find the ESP32 port

```sh
.venv/bin/python scripts/receive-usb.py --list-ports
```

Use the USB Serial port, not a Bluetooth port. The port used in this setup was
`/dev/cu.usbserial-1410`, but it can change when reconnecting the board.

## 3. Start a named session

Use this naming convention:

```text
YYYY-MM-DD__HH-MM-SS__location__driver
```

Use the actual start time in Eastern Time, a meaningful location, and the driver
name. Use `no-driver` for a stationary test. Keep location and driver to letters,
digits, and hyphens. The name identifies a database session and has no file
extension. Use a unique name for every run.

This command generates the current Eastern date/time automatically:

```sh
session_name="$(TZ=America/New_York date '+%Y-%m-%d__%H-%M-%S')__shop__no-driver"
.venv/bin/python scripts/start-can3.py \
  --port /dev/cu.usbserial-1410 \
  --session "$session_name"
```

Replace the port if needed. Change `shop` and `no-driver` before starting when
appropriate. `start-can3.py` also starts the Docker services, so step 2 is optional
if you use this command and Docker Desktop is already running.

Keep that Terminal running throughout the test. The startup log prints the
session name and the local recording path, such as:

```text
Local recording: data/recordings/1794435110362773000.jsonl
Session: 2026-11-11__17-11-50__shop__no-driver; source: usb
```

Confirm **Received** and **written** counters increase. A connected port alone
does not establish that CAN data is arriving. Avoid starting a second receiver
while one already owns the port.

## 4. Stop capture

Press **Ctrl+C in the receiver Terminal** and wait for its final log.

Readings are saved throughout the run; stopping does not trigger saving.
Grafana and InfluxDB remain running after capture stops. Previously stored data
remains available. If shutdown reports unwritten points, recover them from the
recording path printed in the log:

```sh
.venv/bin/python scripts/replay-usb.py data/recordings/ACTUAL_FILENAME.jsonl
```

Replace `ACTUAL_FILENAME` with the real filename. Replay preserves timestamps
and session identity; it does not make an old run appear as current live data.
If you want to stop the dashboards/databases afterward, use `docker compose stop`.
Never remove the Docker volumes to end a recording.

## 5. Review the run

Open http://localhost:3000/d/osprey-recorded. Refresh the page if necessary, then
click the session name in **Saved runs**. This selects its complete stored time
range. Drag on a plot to inspect a smaller interval. Recorded Runs has no
automatic refresh; CAN3 is the dashboard for current live readings.

## Where the data goes

| Storage | Purpose |
| --- | --- |
| InfluxDB, persistent Docker volumes | Main telemetry storage read by Grafana, with timestamps and session IDs. |
| `data/recordings/*.jsonl` | Automatic local recording of received messages and database points; used for recovery. |

Raw values remain stored. Current dashboard factors and thresholds are applied
when viewing them; provisional factors are not confirmed sensor calibrations.

## Preserve completed runs

Review saved runs directly in Grafana. No CSV export is needed.
Copy completed JSONL recordings or database backups to team storage or another
drive. InfluxDB and local JSONL files are both on this laptop; they do not protect
against loss of the laptop itself.

## Quick troubleshooting

- **Port busy:** stop any other receiver and close Arduino Serial Monitor.
- **Docker unavailable:** open Docker Desktop and wait for the engine.
- **Received stays at zero:** check the ESP32 stream, car/dash power, CAN connection,
  and selected USB port. Starting the service does not verify the sensors.
- **Received increases but written does not:** check InfluxDB; preserve the JSONL
  recording and replay it once the database is available.
- **No historical plots:** click the run in Saved runs to set its date/time range.
