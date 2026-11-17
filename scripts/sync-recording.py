"""Copy an already completed JSONL recording to the configured Drive folder."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from osprey_telemetry.live.drive_sync import copy_recording
from osprey_telemetry.live.recording import read_points
from osprey_telemetry.live.usb_receiver import load_env

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('recording', type=Path, help='Use only after stopping the receiver for this recording')
parser.add_argument('--sync-dir', type=Path)
parser.add_argument('--env-file', type=Path, default=Path('.env'))
args = parser.parse_args()
load_env(args.env_file)
destination = args.sync_dir or os.getenv('RECORDING_SYNC_DIR')
if not destination:
    parser.error('Set RECORDING_SYNC_DIR in .env or use --sync-dir')
try:
    # Validate before sharing. Recordings must be closed and not being appended.
    count = sum(1 for _ in read_points(args.recording))
    with args.recording.open() as source:
        header = json.loads(source.readline())
    result = copy_recording(args.recording, destination, header['session'])
except (OSError, ValueError, KeyError, TypeError) as error:
    parser.exit(1, f'Copy failed: {error}. Original recording retained.\n')
print(f'Copied {count} measurements: {result}')
print('Check Google Drive for desktop to confirm upload completion.')
