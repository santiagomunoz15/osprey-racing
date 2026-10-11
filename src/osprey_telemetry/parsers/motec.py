"""Read MoTeC CSV exports without changing their sampling frequency."""
import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

def read_motec(filepath, timezone_name="America/New_York"):
    rows = list(csv.reader(Path(filepath).read_text(encoding="utf-8-sig").splitlines()))
    if not rows or rows[0][:2] != ["Format", "MoTeC CSV File"]:
        raise ValueError("Expected a MoTeC CSV export; other formats need a separate adapter.")
    header_idx = next((i for i, row in enumerate(rows)
                       if row and row[0] in ("Distance", "Time")
                       and i + 1 < len(rows)
                       and rows[i + 1] and rows[i + 1][0] in ("m", "s")), None)
    if header_idx is None:
        raise ValueError("Could not find a Time or Distance channel header with units.")
    metadata = {}
    for row in rows[:header_idx]:
        for offset in (0, 5):
            if len(row) > offset + 1 and row[offset]:
                metadata[row[offset]] = row[offset + 1]
    channels = rows[header_idx]
    units = rows[header_idx + 1]
    if len(channels) != len(units) or len(set(channels)) != len(channels):
        raise ValueError("Channel names and units must match, with unique channel names.")
    rate = float(metadata["Sample Rate"])
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("Sample Rate must be positive.")
    clock = metadata["Log Time"].strip()
    # AM/PM exports use the US date convention; 24-hour exports use day/month.
    date_format = "%m/%d/%Y %I:%M:%S %p" if clock.upper().endswith(("AM", "PM")) else "%d/%m/%Y %H:%M:%S"
    start = datetime.strptime(metadata["Log Date"] + " " + clock, date_format)
    start = start.replace(tzinfo=ZoneInfo(timezone_name)).astimezone(timezone.utc)
    offset = float(metadata.get("Start Time", "0"))
    if not math.isfinite(offset):
        raise ValueError("Start Time must be finite.")
    samples = []
    time_idx = channels.index("Time") if "Time" in channels else None
    if time_idx is not None and units[time_idx] != "s":
        raise ValueError("Time channel must use seconds.")
    for line_number, row in enumerate(rows[header_idx + 2:], header_idx + 3):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != len(channels):
            raise ValueError(f"Line {line_number}: expected {len(channels)} values.")
        values = [float(cell) if cell.strip() else None for cell in row]
        if any(value is not None and not math.isfinite(value) for value in values):
            raise ValueError(f"Line {line_number}: non-finite value.")
        elapsed = values[time_idx] if time_idx is not None else offset + len(samples) / rate
        if elapsed is None or (samples and elapsed <= samples[-1][0]):
            raise ValueError(f"Line {line_number}: sample times must be present and strictly increasing.")
        samples.append((elapsed, start + timedelta(seconds=elapsed), values))
    if not samples:
        raise ValueError("CSV contains no samples.")
    return {"metadata": metadata, "channels": channels, "units": units,
            "sample_rate": rate, "started_at": start, "timezone": timezone_name, "samples": samples}

def parse_motec_csv(filepath, timezone_name="America/New_York"):
    """Compatibility helper returning a pandas DataFrame and channel units."""
    import pandas as pd
    run = read_motec(filepath, timezone_name)
    frame = pd.DataFrame([sample[2] for sample in run["samples"]], columns=run["channels"])
    frame["Time"] = [sample[0] for sample in run["samples"]]
    return frame, dict(zip(run["channels"], run["units"]))
