# Daily operation

Complete [First-time setup](setup.md) once. Run commands from the repository root
with its Python environment activated. On this laptop the project is at
`/Users/santiagom/Desktop/Formula SAE/osprey-racing`.

## 1. Prepare the laptop and car

Open Docker Desktop and wait for the engine. Connect the ESP32 running the
all-channel streaming sketch, then power the car/dash when ready. Close Arduino
Serial Monitor and any other receiver process.

Activate the environment in each new Terminal:

```sh
# macOS/Linux, from the project folder
source .venv/bin/activate
```

```powershell
# Windows PowerShell, from the project folder
.\.venv\Scripts\Activate.ps1
```

Find the USB port:

```sh
python scripts/receive-usb.py --list-ports
```

Use the listed USB Serial port, not Bluetooth. `/dev/cu.usbserial-1410` was used
on this Mac; it can change. Windows uses a name such as `COM5`.

## 2. Start a named session

Use `YYYY-MM-DD__HH-MM-SS__location__driver`, with Eastern start time, no file
extension and a new name for each run. Keep location and driver names to letters,
digits and hyphens. Use `shop` and `no-driver` for a stationary test.

On macOS/Linux, this fills in the current Eastern date/time:

```sh
session_name="$(TZ=America/New_York date '+%Y-%m-%d__%H-%M-%S')__shop__no-driver"
python scripts/start-can3.py --port /dev/cu.usbserial-1410 --session "$session_name"
```

On Windows, replace the example with the actual Eastern start time and port:

```powershell
python scripts/start-can3.py --port COM5 --session "2026-11-17__14-30-00__shop__no-driver"
```

`start-can3.py` starts InfluxDB and Grafana, then runs the receiver.
Open http://localhost:3000/d/osprey-can3 and choose **USB receiver**. The only live
selector is Input (USB/Simulation); graphs refresh every second. Running Grafana
alone does not record telemetry.

Keep the receiver Terminal open. Confirm **Received** and **written** counters
increase and check the graphs. The log prints the session name and local JSONL
path. Messages are saved locally before being queued for InfluxDB; a connected
port alone does not establish that CAN data is arriving.

## 3. Stop and share

Press **Ctrl+C in the receiver Terminal** and wait for the final log and any
Drive copy to finish. Data is saved continuously; stopping ends capture.
Grafana and InfluxDB stay running and retain saved readings.

If `RECORDING_SYNC_DIR` is configured, the closed USB recording is copied to the
team's Drive folder with a session-based name and unique suffix. The original
local file stays intact. Check Google Drive's sync status to confirm upload.

If shutdown reports unwritten points, recover them from the exact recording
path in the log:

```sh
python scripts/replay-usb.py "data/recordings/ACTUAL_FILENAME.jsonl"
```

If the Drive copy fails, retry after stopping the receiver and restoring Drive
access:

```sh
python scripts/sync-recording.py "data/recordings/ACTUAL_FILENAME.jsonl"
```

Use only completed recordings for sharing. To shut down the services afterward:

```sh
docker compose stop
```

## 4. Review a saved run

Open http://localhost:3000/d/osprey-recorded and refresh the page if needed.
Click a session name in **Saved runs** to load its complete recorded time range.
Drag on a graph to zoom; last-reading cards follow the selected interval.
Recorded Runs reviews real USB sessions and does not automatically refresh.
Changing its Run dropdown alone does not reset the time picker; use the catalog
link to load the run's bounds. The catalog covers the past 365 days, which is a
viewing filter, not an automatic deletion policy.

Current dashboard factors and thresholds also apply to historical raw readings.
Some factors remain provisional; rear suspension calibration is still pending.

## 5. Review a teammate's recording

Download the completed `.jsonl` from **Telemetry Runs** into `data/recordings/`.
On your own computer, complete setup and start Docker Desktop, then:

```sh
docker compose up -d influxdb grafana
python scripts/replay-usb.py "data/recordings/DOWNLOADED_FILENAME.jsonl"
```

Replay validates the entire recording and writes samples with their original
session, source and timestamps. It does not require the ESP32 and does not make
old readings current on live CAN3. Refresh Recorded Runs and click that session.
Replaying the same recording into the same bucket is safe.

## Storage and backups

- **InfluxDB:** main readings stored in persistent Docker volumes on this laptop.
- **`data/recordings/*.jsonl`:** original messages, timestamps and database points
  for recovery and sharing. These contain the actual telemetry.
- **Google Drive:** copies of completed recordings; teammates replay these locally.
- **GitHub:** code and dashboard configuration, not recordings, volumes or `.env`.

Both local storage copies are on the laptop. Confirm shared recordings have
synced, or copy backups to another drive. No CSV export is part of this workflow.

## Quick troubleshooting

| Symptom | Check |
| --- | --- |
| Port busy | Close Serial Monitor and stop other receivers. |
| Docker unavailable | Start Docker Desktop and wait for its engine. |
| Received stays zero | Car/dash power, CAN wiring, streaming firmware and USB port. |
| Received rises, written stalls | InfluxDB connection; keep the JSONL and replay after recovery. |
| No saved-run plot | Click the session in Saved runs to load its time range. |
| Drive copy fails | Existing folder, desktop app and write permissions; retry the completed file. |

For a test session, note the date, location, driver, car setup, conditions, run
name and any observations or calibration changes alongside the recording.
