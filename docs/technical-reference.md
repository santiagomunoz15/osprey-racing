# Technical reference

For installation see [First-time setup](setup.md); for capture and sharing see
[Daily operation](session-quickstart.md).

## Current system

```text
Car CAN3 -> ESP32 CAN transceiver / streaming firmware -> USB -> Python receiver
                                                               |-> InfluxDB -> Grafana
                                                               |-> local JSONL
                                                                   -> closed copy to Drive
```

InfluxDB and Grafana run locally in Docker. The receiver runs directly on the
laptop to access USB. Grafana is the viewer; Python writes the readings. The
receiver sends InfluxDB line-protocol points over its HTTP API; the database
manages its own disk files. Grafana uses its Flux datasource to query them.
The default bucket is `telemetry-test`, with no automatic retention expiry.
Changing a graph factor does not rewrite the stored raw readings.

## Firmware and wire format

The working sketch is [can3_stream.ino](../firmware/can3_stream/can3_stream.ino).
It uses GPIO 4 TX / GPIO 5 RX, a CAN transceiver, 1 Mbit/s and NORMAL mode.
It accepts standard non-remote frames with exactly two payload bytes for the
configured IDs. IDs in the channel sheet are **hexadecimal**: throttle `022`
means `0x022` (decimal 34), not decimal 22.

USB runs at 115200 baud. Each new sample is a newline-terminated JSON message:

```json
{"can_id":34,"data":"0064"}
```

`can_id` is the actual ID as a decimal JSON integer. `data` preserves the two
received bytes as hexadecimal text. A CAN receive task updates the latest value;
the output loop forwards new values at up to 10 Hz per channel. Intermediate
frames are intentionally downsampled. This is live visualization sampling,
not a full-rate CAN-bus logger. Startup text is ignored as invalid input.

The receiver also accepts earlier diagnostic-table rows and single-channel
`ID: 0x012 | Raw: 0 | Sensor Reading: 0.0 Unit` messages. Those are compatibility
formats; the all-channel JSON sketch is the normal setup. The diagnostic sketch
under `firmware/can3_diagnostic/` remains available for troubleshooting.

## Stored readings and recovery

Measurement: `can3_raw`. Tags: `device`, `source`, `session`, `can_id`, `channel`.
Fields: `byte_0`, `byte_1`, `unsigned_be`, `signed_be`. Both 16-bit interpretations
are preserved. Timestamps are nanosecond laptop receipt timestamps, not sensor
acquisition times. Source is `usb` or `simulation`.

Each local JSONL file starts with session metadata, followed by sample records
containing original text, receipt time and the exact database point. Invalid
complete lines are retained with a null point. Each append is flushed and synced
to disk before upload queueing. JSONL is actual telemetry data, not an import
instruction file. The replay script supplies the database import logic.

USB reads run separately from writes. Writes batch at 50 points or 0.5 seconds;
the in-memory upload queue holds 5,000 points. Failed writes retry with original
timestamps. If the queue fills, new live-upload points are dropped but complete
messages remain locally recorded. Shutdown can leave a queued tail; replay the
completed file to recover it. Disk write failures stop capture. Partial lines
and oversized discarded lines are not preserved. Radio/bus losses before USB
cannot be recovered by the laptop.

Replay validates a whole recording before writing it and preserves timestamps
and tags. Damaged or truncated recordings are rejected. Keep originals intact
before investigating recovery. The optional `--local-only` receiver mode records
without InfluxDB; `--dry-run` prints rather than writes database points and still
creates a local recording. Use `--record` to choose a new file; files are not
overwritten.

## Channels and display factors

The machine-readable map is
[can3_channels.json](../src/osprey_telemetry/live/can3_channels.json). Its `display`
entries document factors, units, evidence and status. The actual Grafana queries
and styling are in [can3.json](../config/grafana/dashboards/can3.json) and
[recorded-runs.json](../config/grafana/dashboards/recorded-runs.json). Editing the
channel metadata alone does not update those provisioned dashboard queries;
keep all three consistent when changing a factor.

All listed channels have been verified as received; that does not establish
sensor calibration. Values use signed big-endian counts except battery voltage,
which uses unsigned big-endian counts. Offsets are currently zero.

| CAN ID (hex) | Channel | Display conversion | Unit | Status |
| --- | --- | --- | --- | --- |
| 0x001 | Battery Volts | raw / 100 | V | comparison-based |
| 0x002 | Front Brake | raw / 10 | psi | provisional |
| 0x003 | Rear Brake | raw / 10 | psi | provisional |
| 0x004 | Coolant Pressure | raw / 10 | psi | provisional |
| 0x005 | Coolant Temperature | raw / 10 | °C | comparison-based |
| 0x006 | Oil Pressure | raw / 10 | psi | provisional |
| 0x007 | Oil Temperature | raw / 10 | °F | provisional |
| 0x008 | RPM | raw counts | raw RPM counts | scaling pending |
| 0x009 | Lambda | raw / 10 | Ratio | provisional |
| 0x010 | Fuel Pressure | raw / 100 | psi | provisional |
| 0x011 | Fuel Level | raw counts | unconfirmed | scaling pending |
| 0x012 | G Force Lat | raw / 100 | G | comparison-based |
| 0x013 | G Force Long | raw / 100 | G | comparison-based |
| 0x014 | G Force Vert | raw / 100 | G | comparison-based |
| 0x015 | Gear | integer; 0 = N | Gear | comparison-based |
| 0x016 | Steering Wheel Angle | raw / 10 | degrees | comparison-based |
| 0x017 | Steered Angle | raw / 10 | degrees | comparison-based |
| 0x018 | Sus Pos FL | raw / 100 | mm | comparison-based |
| 0x019 | Sus Pos FR | raw / 100 | mm | comparison-based |
| 0x020 | Sus Pos RL | raw / 100 | mm | comparison-based |
| 0x021 | Sus Pos RR | raw / 100 | mm | comparison-based |
| 0x022 | Throttle | raw / 10 | % | provisional |
| 0x023 | Yaw Rate | raw counts | unconfirmed | scaling pending |
| 0x024 | Wheel Speed FL | raw / 10 | m/s | provisional |
| 0x025 | Wheel Speed FR | raw / 10 | m/s | provisional |
| 0x026 | Wheel Speed RL | raw / 10 | m/s | provisional |
| 0x027 | Wheel Speed RR | raw / 10 | m/s | provisional |

Comparison-based factors come from the dash observations. Provisional factors
were selected for initial visualization and need nonzero reference comparisons.
Both rear suspension channels still need proper scale/offset calibration; /100
and a fixed mm label are only the current display setup. Decide whether to
measure sensor travel or wheel travel before calibration; wheel travel also
requires the suspension geometry/motion ratio.

## Dashboard behavior

- **CAN3:** only USB receiver/Simulation selection; 1-second refresh. Latest cards
  require a point received within five seconds. Firmware sample rate and browser
  refresh rate are separate.
- **Recorded Runs:** saved USB session catalog for the past 365 days; no Input
  selector or automatic refresh. Click a session to set its actual time range.
  Last-value cards use the selected historical window, not the last five seconds.
  An active session can appear in the catalog; refresh to update its end time.
- **Colors:** FL blue, FR orange, RL green, RR purple for suspension and wheel speed.
- **Suspension:** fixed mm suffix with two decimals, avoiding automatic unit-prefix changes.
- **Oil:** pressure and temperature share one graph, psi on the left and °F on the right.
- **Thresholds:** RPM red at 9,000 and above, assuming raw counts equal RPM; oil
  temperature yellow below 20°F, green from 20 to below 100°F, red at 100°F and above.
- **G forces:** signed raw /100; displayed graph range 0–3 G. Values outside that
  display range remain stored.

Threshold colors are visualization settings, not a newly configured notification
system. CSV dashboard controls, the USB-only demo dashboard and Bristol example
were removed. The retired CSV importer, parser, PostgreSQL and Prometheus
services/configuration were also removed. Their files and old CSV exports were
archived under `backups/legacy-csv-cleanup-2026-11-17/`; existing legacy Docker
volumes were left intact. InfluxDB is the only telemetry database in use.

## Run identity and team sharing

New sessions use `YYYY-MM-DD__HH-MM-SS__location__driver`, with Eastern start time
and no extension. JSONL filenames on the laptop use timestamp IDs; the header
contains the session. Shared copies use a sanitized session name plus a unique
suffix. Renaming a file does not change the embedded session.

The first all-channel run uses internal session `can3-all-live-20261111` and the
friendly label `2026-11-11__17-11-50__shop__no-driver`. Its mapping is documented
in [run-names.json](../config/run-names.json) and explicitly applied in the
Recorded Runs selector, catalog and filters. Editing this metadata file alone
does not automatically rename dashboard results or database tags.

The private `.env` setting `RECORDING_SYNC_DIR` selects an existing Drive for
desktop folder on each computer. After a USB recording closes, the receiver
stages a copy, verifies its SHA-256 hash, and renames it to a uniquely named JSONL.
The local original remains. Drive for desktop uploads it independently; the
receiver cannot confirm cloud completion. An unavailable folder is not created
silently; the copy fails and can be retried with `scripts/sync-recording.py`.
Simulations copy only when an explicit `--sync-dir` is supplied.

Git excludes `.env`, `data/recordings/` and `backups/`. Database volumes also do
not travel through Git. Teammates use their own credentials, download a completed
recording from Drive and replay it into their own InfluxDB. The code and schema
must support the recording version; strict replay also checks reconstructed
points against recorded points.

## Maintaining the configuration

Grafana dashboards and datasources are provisioned from `config/grafana/` through
Docker mounts. Keep intentional dashboard edits in the repository files so they
transfer to other computers. Both dashboards should receive matching conversion,
color and threshold changes. Restart/reload Grafana provisioning when needed.
The current session selector's friendly-name mapping is explicit in its queries.

Use `python -m unittest discover -s tests -q` for receiver, recording, replay,
Drive-copy checks. Raw recordings and private Drive paths should not be committed.
