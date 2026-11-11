# CAN3 dashboard and capture

Open http://localhost:3000/d/osprey-can3 (Osprey Racing - CAN3).
All 27 workbook channels are grouped into engine/power, brakes/driver controls,
fuel/combustion, dynamics, suspension, and wheel speeds. Workbook IDs are hexadecimal 0x001–0x027, using the listed
labels 001 through 027 (not every integer in that hexadecimal range).
Panels also show their decimal equivalents. Workbook names and explicit masks are preserved
in `src/osprey_telemetry/live/can3_channels.json`.

The workbook specifies two-byte messages but does not define byte order,
signedness, scaling, offsets, units, bus bitrate, or USB framing. Until confirmed,
we store each received byte separately as `byte_0` and `byte_1` under measurement
`can3_raw`, with channel, CAN ID, source, device, and session tags. These are not
engineering readings. Blank workbook masks remain unknown. No thresholds or
physical units are inferred, and no vehicle firmware or bus configuration is changed.

The receiver now accepts this proposed newline-delimited USB format alongside
its existing brake/throttle messages:

```json
{"can_id": 1, "data": "1234"}
```

`can_id` is the actual identifier as a decimal JSON integer (throttle 0x022 is 34); `data` contains exactly two bytes in hex in
received order (spaces accepted). The ESP32 must forward each CAN3 frame in this
format; the workbook alone does not establish its current USB protocol.

From the project root:

```sh
python3 scripts/receive-usb.py --list-ports
python3 scripts/receive-usb.py --port /dev/cu.usbserial-1430 --session can3-shop-001
```

Use the detected port. Baud defaults to 115200. Local durable recording, bounded
upload buffering and replay work for CAN3 exactly as for legacy USB messages.
See [USB receiver](usb-receiver.md). Receipt times are laptop times.

To verify all channels without hardware:

```sh
python3 scripts/receive-usb.py --simulate --protocol can3 --samples 8100 --rate 270
```

This produces 30 seconds at 10 Hz per channel, tagged `source=simulation`.
Choose Simulation in Grafana and Last 5 minutes. The dashboard defaults to USB
receiver so test data never appears as vehicle data. The simulation stops after
its requested sample count; the dashboard continues running.

Before showing engineering values, supply a DBC or MoTeC export confirming the
wire encoding and scaling for every channel, plus a real USB message example.

## Verify channels on the ESP32 first

Open `firmware/can3_diagnostic/can3_diagnostic.ino` in Arduino IDE. Select the
same ESP32 board and port as the working sensor sketch, upload, then open Serial
Monitor at 115200 baud. It retains GPIO 4/5, 1 Mbit/s and NORMAL mode from that
sketch. No firmware has been flashed automatically.

The summary shows all 27 hexadecimal workbook IDs, latest two bytes, candidate
big-endian unsigned/signed values, observed valid-frame rate, age, valid count,
and incorrect-length count. NO DATA means no valid two-byte frame; STALE means
no valid update for over two seconds (a diagnostic marker, not a channel-specific
failure threshold). Both number interpretations are raw, not calibrated units.
A dedicated receive task keeps draining the queue during summary printing.
Unknown IDs and extended/remote frames are counted separately. Bus errors,
missed frames and overruns are cumulative; rising losses mean the capture is
incomplete. Unexpected traffic is counted, not individually listed.

1. Check for expected IDs and two-byte payloads with the dash powered.
2. Move throttle, steering, each suspension corner and each wheel independently;
   apply brakes and compare front/rear responses.
3. Compare at least three readings per channel against the dash, including
   negative readings where applicable. Determine scale/offset and signedness
   from MoTeC transmit settings, then verify against these readings.
4. Compare engine/fluid channels during suitable operating conditions. A constant
   plausible value alone does not validate the mapping.
5. Fill `docs/can3-verification.csv`. Check for increasing loss/error counters
   while all channels run. Only then enable engineering decoding and telemetry.

The diagnostic sketch produces a human-readable table; it is not the JSON
stream expected by the Python CAN3 receiver. After validation, use a separate
streaming mode that emits the confirmed actual IDs and original bytes.

Earlier CAN3 simulation recordings used a decimal interpretation of workbook
labels. They are test artifacts from the old mapping, not verified vehicle data;
do not replay them as validation of the corrected channel map.

## Visualize the current diagnostic sketch

The Python receiver now accepts fresh rows from `can3_diagnostic.ino` directly,
as well as JSON frames. Close Arduino Serial Monitor, start Docker Desktop, then:

```sh
.venv/bin/python scripts/start-can3.py --port /dev/cu.usbserial-1410
```

Use the current detected port. Open http://localhost:3000/d/osprey-can3 and choose
USB receiver. The graph selector switches signed/unsigned big-endian raw counts.
Latest-value cards include only samples received in the last five seconds. Each
panel is marked verified/pending from the current workbook, and its description
contains workbook units and comparison notes. These marks do not indicate live
reception or completed calibration. No engineering conversion is applied yet.

Diagnostic rows with NO DATA, a STALE flag, age over 2000 ms, or inconsistent
hex/decimal IDs are rejected. Headers/status rows count as invalid input in the
receiver counters, which is expected for this mixed human-readable format.
Diagnostic capture records one snapshot per summary, not every CAN frame, and
laptop receipt time rather than acquisition time. Workbook observations suggest
coolant temperature /10, G forces /100, steering angles /10; suspension values
need confirmation. Units alone do not establish a scale factor.

New CAN3 recordings include raw signed/unsigned fields alongside the original
bytes. Older CAN3 recordings produced before these fields were added will fail
strict replay point matching; keep those originals intact. Legacy brake/throttle
recordings are unaffected.

## Verified single-channel sketch and all-channel streaming

The receiver accepts `ID: 0x012 | Raw: 0 | Sensor Reading: 0.0 Unit`
lines from the team's channel-check sketch, including Arduino CRLF endings.
It uses the hexadecimal ID and raw integer, not the human-readable scaled value.
All channels are now marked verified based on team confirmation; engineering
scale factors remain separate from reception verification.

To send all channels together, upload `firmware/can3_stream/can3_stream.ino`
using the same ESP32 board. This retains GPIO 4/5, 1 Mbit/s and NORMAL mode. A
receive task captures the latest two-byte value of each configured standard ID;
the output loop forwards new samples at up to 10 Hz per channel as JSON at
115200 baud. Intermediate frames are intentionally downsampled. This is for
live visualization, not full-rate CAN logging. Close the Python receiver before
uploading; close Arduino Serial Monitor before starting the receiver again.
The existing single-channel firmware can visualize only its selected channel.

### G-force display

Lateral, longitudinal and vertical G-force panels use signed big-endian counts
divided by 100, matching the workbook comparisons. Their display range is 0–3 G
with two decimals. Negative and above-range values remain stored without clipping;
negative values fall below the requested graph range. Recent-value cards convert
these same three channels to G while the remaining channels still show raw counts.

## Start and stop a named run

Close Arduino Serial Monitor. With the ESP32 connected, from the project root:

```sh
.venv/bin/python scripts/start-can3.py --port /dev/cu.usbserial-1410 --session 2026-11-11_shop_run-002
```

Use a fresh session name for each run and the detected USB port. Keep that
Terminal open while recording. The receiver prints its local JSONL recording
path and received/written counters. Press Ctrl+C in that Terminal to stop capture;
Grafana and InfluxDB remain running and their saved data remains available.
If shutdown reports unwritten points, recover the entire recording safely with:

```sh
.venv/bin/python scripts/replay-usb.py data/recordings/RECORDING_FILENAME.jsonl
```

Replay preserves original timestamps and session identity. In Recorded Runs,
click a saved session to load its absolute date/time range. Historical cards
follow that selected range. Live CAN3 has only the USB/Simulation input selector.
Starting/stopping a receiver session does not erase previous runs.
InfluxDB is a database, while JSONL recordings are files saved separately.
Copy completed backups to team storage or another drive for protection against
loss of the laptop. Local backups alone are on the same disk as the originals.
