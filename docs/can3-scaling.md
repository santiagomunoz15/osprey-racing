# CAN3 display conversions

The CAN3 dashboard refreshes every second. Grafana's minimum refresh interval is
also set to one second in Compose. Capture remains up to 10 Hz per channel;
refreshing the screen once per second does not reduce stored sample frequency.
InfluxDB already stores live readings in persistent Docker volumes, with session
IDs and timestamps. Local JSONL recordings provide a second copy.

Conversions are applied at query time, preserving original bytes and signed and
unsigned integers. Per-channel factors, source interpretation, evidence and units
are recorded in `src/osprey_telemetry/live/can3_channels.json` under `display`.
Both recent cards and historical plots use the same conversion.

| Channels | Display conversion | Units |
| --- | --- | --- |
| Battery | unsigned raw / 100 | V |
| Coolant temperature | signed raw / 10 | °C |
| Lateral, longitudinal, vertical acceleration | signed raw / 100 | G |
| Steering wheel and steered angle | signed raw / 10 | degrees |
| Four suspension positions | signed raw / 100 | mm |
| Gear | integer; 0 displayed as N | gear |

Battery conversion is based on live raw 1293 versus approximately 12.9 V on the
dash. Suspension observations imply /100 but were not identical snapshots;
confirm simultaneously at multiple positions before relying on calibration.
All offsets are currently zero. G plots retain the requested 0–3 G axis range.

Pressure channels, oil temperature, lambda, fuel level, RPM, throttle, yaw rate
and wheel speeds remain explicitly labeled raw/scaling pending. Workbook units
are recorded, but a zero pair cannot establish a scale, and a unit alone does
not establish the CAN encoding. Obtain the MoTeC transmit multiplier/offset or
simultaneous nonzero raw/dash pairs. Do not infer a conversion from plausibility
alone. The raw-interpretation selector applies only to these unscaled channels.

Run selection and naming UI are a subsequent task; the receiver already tags
stored points by its session, source and device. Do not remove Docker volumes.

## Provisional /10 conversions agreed with the user

Pressure channels (front/rear brake, coolant, oil and fuel), oil temperature,
lambda, throttle and four wheel speeds now use signed raw /10. These are
user-selected starting assumptions, not confirmed sensor calibrations. Units
come from the workbook (psi, °F, ratio, %, m/s). Both cards and graphs are marked
provisional. Fuel level, RPM and yaw remain raw pending a conversion decision.
The earlier pending list above describes the evidence gap; /10 now supplies
these agreed provisional displays without changing stored samples.

Fuel pressure was subsequently changed to provisional raw /100 at the user’s
request (94.6 psi at /10 becomes 9.46 psi). This is not reference calibration.
