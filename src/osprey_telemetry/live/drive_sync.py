"""Copy closed recordings to an existing Drive for desktop folder."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
from uuid import uuid4


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.digest()


def copy_recording(path, directory, session):
    """Stage and verify a complete copy before publishing a uniquely named JSONL."""
    path, directory = Path(path), Path(directory)
    if not directory.is_dir():
        raise OSError('Sync folder is unavailable; check Drive for desktop and access permissions')
    slug = re.sub(r'[^A-Za-z0-9_-]+', '-', session).strip('-_')[:140] or 'run'
    destination = directory / f'{slug}__{uuid4().hex[:12]}.jsonl'
    descriptor, staging = tempfile.mkstemp(prefix='.telemetry-', suffix='.partial', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as target, path.open('rb') as source:
            shutil.copyfileobj(source, target, 1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        if digest(path) != digest(staging):
            raise OSError('Recording copy verification failed')
        os.rename(staging, destination)
    finally:
        Path(staging).unlink(missing_ok=True)
    return destination
