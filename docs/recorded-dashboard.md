# Recorded-run dashboard

Open http://localhost:3000/d/osprey-recorded and choose a Run.
The stacked traces show speed, engine RPM, throttle, steering, acceleration, and suspension.
Session details, channel statistics, and peak RPM appear on the right.
Extra channel displays any channel from the selected run, with units in the selector.

Horizontal axis switches between elapsed seconds and the original CSV Distance in metres.
Time is aligned to each run's first sample. Graphs show complete runs independently of the global time picker.
Choose Compare with to overlay a second imported run in gray. None disables the reference.
Reference traces use their own first sample in time mode and original Distance in distance mode.
There is no lap segmentation, distance resampling, or automatic lap alignment.

The fixed traces use the demonstration MoTeC channel names. Different export names may leave a trace empty;
use Extra channel or adapt the dashboard's channel names after confirming the car's export format.
Grafana XY charts have independent cursors and zoom; they do not provide MoTeC's linked cursor.

The dashboard UID and recorded-run alert are unchanged. The peak-RPM card shows the selected run;
the recorded-run alert independently checks the latest stored run by recorded start time.