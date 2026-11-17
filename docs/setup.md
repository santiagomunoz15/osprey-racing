# First-time setup

Use this once per computer. For each test session, follow [Daily operation](session-quickstart.md).

## Install and clone

Install Git, Docker Desktop and Python **3.10 or newer**. Arduino IDE and its
ESP32 board package are needed only to flash firmware, not to review saved runs.
Clone the repository and open a Terminal in it:

```sh
git clone https://github.com/santiagomunoz15/osprey-racing.git
cd osprey-racing
```

## Create the Python environment

On macOS/Linux, use a Python 3.10+ interpreter:

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[live]'
```

If `python3` is older than 3.10, use the installed newer interpreter instead.
On Windows PowerShell:

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[live]'
```

The remaining Python commands assume this environment is activated.

## Configure local credentials and storage

Generate `.env` directly; do not copy another teammate's credentials:

```sh
python scripts/setup-env.py
```

The script adds missing credentials and preserves existing values. Do not first
copy the blank password entries in `.env.example`: the generator checks whether
keys exist, not whether their values are blank. `.env.example` is a settings
reference. Keep the populated `.env` private.

Open Docker Desktop and wait for its engine, then run:

```sh
docker compose config --quiet
docker compose up -d influxdb grafana
```

Open http://localhost:3000/d/osprey-can3. The Grafana username is `admin`; use
`GRAFANA_ADMIN_PASSWORD` from this computer's `.env`. Services bind to localhost.
InfluxDB defaults to organization `osprey-racing`, bucket `telemetry-test` and
http://127.0.0.1:8086. Grafana connects to it inside Docker using the configured
read/write token. No internet is required for capture once dependencies and
Docker images are installed.

Database initialization only runs on a new volume. Editing `.env` afterward
does not rotate passwords/tokens already stored in the databases. Docker volumes
persist across restarts; `docker compose stop` is safe for ending services.
Do not remove volumes to stop a run. Git does not transfer these databases.

## Prepare the ESP32 for capture

Open [can3_stream.ino](../firmware/can3_stream/can3_stream.ino) in Arduino IDE.
Use the board configuration matching the hardware; this laptop's working setup
used **ESP32 Wrover Module**, upload speed **115200**. The sketch uses GPIO 4 TX,
GPIO 5 RX through the CAN transceiver, a 1 Mbit/s bus and NORMAL mode. Retain the
verified car wiring. It sends all 27 configured channels as JSON over USB at
115200 baud, with up to 10 updates per second per channel.

Close the Python receiver before flashing. Close Arduino Serial Monitor before
starting Python. Only one program can own the USB port. A teammate who only
replays downloaded recordings does not need an ESP32.

## Optional automatic Google Drive sharing

Install Google Drive for desktop and sign in with an account that can access the
team's Shared drive. Find or create the **Telemetry Runs** folder in Finder or
File Explorer. Shared-drive desktop uploads require suitable write permissions.
Add this computer's real existing folder path to its private `.env`:

```dotenv
RECORDING_SYNC_DIR="/path/to/Shared drives/Osprey Racing/Telemetry Runs"
```

On macOS, select the folder in Finder and press Option–Command–C to copy its path.
Each computer uses its own path; the personal path is not stored in Git.

A newly started USB receiver reads this setting. After recording closes, it
copies the completed JSONL file there and verifies the copy's SHA-256 hash.
Google Drive for desktop handles the upload; check its sync status to confirm
cloud availability. The original stays in `data/recordings/`. An unavailable
folder produces an error and leaves the original for retry. Simulations are not
copied automatically. Removing the setting disables automatic copies.

## Verify installation

```sh
python -m unittest discover -s tests -q
python scripts/receive-usb.py --simulate --protocol can3 --samples 270 --rate 270 --dry-run
```

The dry run creates a local test recording and prints points without writing to
InfluxDB or the configured Drive folder. Omit `--dry-run` to write labeled
simulation data to InfluxDB, then choose Simulation on live CAN3.

Continue with [Daily operation](session-quickstart.md).
