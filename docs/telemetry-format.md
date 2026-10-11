# Telemetry format

The initial parser supports MoTeC CSV exports beginning with Format,MoTeC CSV File.
Metadata includes Log Date (DD/MM/YYYY), Log Time (HH:MM:SS), Sample Rate, and optional Start Time.
The channel header begins with Distance (m) or Time (s); the next row contains channel units.
24-hour exports use DD/MM/YYYY dates. AM/PM exports use MM/DD/YYYY dates.
Add a separate parser adapter when the team confirms another export format.

The importer preserves channel names, units, metadata, every sample, and elapsed seconds.
Timestamp = logger start interpreted using --timezone + explicit Time in seconds when available.
Without a Time column, elapsed time uses Start Time + sample index / Sample Rate.
Explicit Time values must be present, finite, and strictly increasing; they are not resampled.
Unknown formats, duplicate channel names, malformed row widths, and non-finite values are rejected.
Blank measurements remain missing. Import is atomic; file contents plus timezone identify duplicates.

PostgreSQL tables: runs (metadata), channels (names/units), samples (measurements/timestamps).
The bristol.csv example contains 2,953 samples, 11 channels, and a 50 Hz sample rate.
Its metadata describes a simulator sample; it is not an Osprey Racing vehicle recording.

Live InfluxDB telemetry conventions are planned, not implemented:
measurement engine, field rpm, with explicit timestamps and a source tag distinguishing simulation
from actual telemetry. Confirm units and schema before connecting the vehicle.

The speed graph accepts Corr Speed or Ground Speed in km/h. A Distance channel is needed for
the distance view; Lap Distance is not substituted because it resets at each lap.
