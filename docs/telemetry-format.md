# Telemetry format

The initial parser supports MoTeC CSV exports beginning with Format,MoTeC CSV File.
Metadata includes Log Date (DD/MM/YYYY), Log Time (HH:MM:SS), Sample Rate, and optional Start Time.
The channel header begins with Distance; the next row contains channel units.
Add a separate parser adapter when the team confirms another export format.

The importer preserves channel names, units, metadata, every sample, and elapsed seconds.
Timestamp = logger start interpreted using --timezone + Start Time + sample index / Sample Rate.
Unknown formats, duplicate channel names, malformed row widths, and non-finite values are rejected.
Blank measurements remain missing. Import is atomic; file contents plus timezone identify duplicates.

PostgreSQL tables: runs (metadata), channels (names/units), samples (measurements/timestamps).
The bristol.csv example contains 2,953 samples, 11 channels, and a 50 Hz sample rate.
Its metadata describes a simulator sample; it is not an Osprey Racing vehicle recording.

Live InfluxDB telemetry conventions are planned, not implemented:
measurement engine, field rpm, with explicit timestamps and a source tag distinguishing simulation
from actual telemetry. Confirm units and schema before connecting the vehicle.
