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
    metadata = {}
    for row in rows:
        if row and row[0] == "Distance":
            break
        for offset in (0, 5):
            if len(row) > offset + 1 and row[offset]:
                metadata[row[offset]] = row[offset + 1]
    header_idx = next((i for i, row in enumerate(rows) if row and row[0] == "Distance"), None)
    if header_idx is None:
        raise ValueError("Could not find the Distance channel header.")
    channels = rows[header_idx]
    units = rows[header_idx + 1]
    if len(channels) != len(units) or len(set(channels)) != len(channels):
        raise ValueError("Channel names and units must match, with unique channel names.")
    rate = float(metadata["Sample Rate"])
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("Sample Rate must be positive.")
    start = datetime.strptime(metadata["Log Date"] + " " + metadata["Log Time"], "%d/%m/%Y %H:%M:%S")
    start = start.replace(tzinfo=ZoneInfo(timezone_name)).astimezone(timezone.utc)
    offset = float(metadata.get("Start Time", "0"))
    if not math.isfinite(offset):
        raise ValueError("Start Time must be finite.")
    samples = []
    for line_number, row in enumerate(rows[header_idx + 2:], header_idx + 3):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != len(channels):
            raise ValueError(f"Line {line_number}: expected {len(channels)} values.")
        values = [float(cell) if cell.strip() else None for cell in row]
        if any(value is not None and not math.isfinite(value) for value in values):
            raise ValueError(f"Line {line_number}: non-finite value.")
        elapsed = offset + len(samples) / rate
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
