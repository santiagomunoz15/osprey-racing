"""Append-only local telemetry recordings and validated replay."""
import json
import os
from pathlib import Path


class Recording:
    def __init__(self, path, metadata):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open('x', encoding='utf-8')
        self.append({'type': 'session', 'version': 1, **metadata})

    def append(self, record):
        self.file.write(json.dumps(record, ensure_ascii=True) + '\n')
        self.file.flush()
        os.fsync(self.file.fileno())

    def close(self):
        self.file.close()


def read_points(path):
    """Reject damaged recordings, including a partially written final record."""
    from .usb_receiver import make_point
    with Path(path).open(encoding='utf-8') as source:
        header = json.loads(source.readline())
        if not isinstance(header, dict) or header.get('type') != 'session' or header.get('version') != 1:
            raise ValueError('Unsupported recording format')
        for key in ('device', 'source', 'session'):
            if not isinstance(header.get(key), str):
                raise ValueError(f'Missing or invalid {key}')
        previous = 0
        for number, line in enumerate(source, 2):
            if not line.endswith('\n'):
                raise ValueError(f'Incomplete recording at line {number}; preserve the original before recovery')
            row = json.loads(line)
            if not isinstance(row, dict) or row.get('type') != 'sample':
                raise ValueError(f'Unexpected record at line {number}')
            timestamp = row['timestamp_ns']
            if type(timestamp) is not int or timestamp <= previous:
                raise ValueError(f'Invalid timestamp at line {number}')
            previous = timestamp
            if row['point'] is None:
                continue
            expected = make_point(row['raw'], timestamp, header['device'], header['source'], header['session'])
            if row['point'] != expected:
                raise ValueError(f'Point mismatch at line {number}')
            yield expected
