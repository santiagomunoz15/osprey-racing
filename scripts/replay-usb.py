"""Validate and re-upload a recording with original session IDs and timestamps."""
import argparse
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from osprey_telemetry.live.recording import read_points
from osprey_telemetry.live.usb_receiver import InfluxWriter, load_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--env-file', type=Path, default=Path('.env'))
    parser.add_argument('--interval', type=float, default=0, help='Seconds between batches; 0 uploads immediately')
    args = parser.parse_args()
    if not 0 <= args.interval <= 60:
        parser.error('Interval must be between 0 and 60 seconds')
    try:
        count = sum(1 for _ in read_points(args.recording))
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        parser.error(f'Invalid recording: {error}')
    print(f'Validated {count} measurements; preserving original timestamps and session.', file=sys.stderr)
    load_env(args.env_file)
    token = os.getenv('INFLUX_DB_API_TOKEN') or os.getenv('INFLUX_DB_API')
    if not args.dry_run and not token:
        parser.error('Set INFLUX_DB_API_TOKEN in .env')
    writer = None if args.dry_run else InfluxWriter(
        os.getenv('INFLUX_URL', 'http://127.0.0.1:8086'),
        os.getenv('INFLUX_ORG', 'osprey-racing'),
        os.getenv('INFLUX_BUCKET', 'telemetry-test'), token)
    batch = []
    def send():
        if writer:
            writer.write(batch)
        else:
            print('\n'.join(batch))
        batch.clear()
    try:
        for point in read_points(args.recording):
            batch.append(point)
            if len(batch) == 50:
                send()
                time.sleep(args.interval)
        if batch:
            send()
    except RuntimeError as error:
        parser.exit(1, f'{error}. Recording retained; rerun replay to retry.\n')
    print(f'Replayed {count} measurements.', file=sys.stderr)


if __name__ == '__main__':
    main()
