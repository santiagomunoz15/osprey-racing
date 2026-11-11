"""CAN3 frames: preserve received byte order until engineering decoding is confirmed."""
import json
import re
from pathlib import Path

CHANNELS = {c['can_id']: c for c in json.loads(Path(__file__).with_name('can3_channels.json').read_text())}


def make_can3_point(line, timestamp_ns, device, source, session):
    from .usb_receiver import tag
    line = line.strip()
    # Preserve the signed raw integer from the user's single-channel check sketch.
    raw_match = re.fullmatch(
        r"\s*ID:\s*0x([0-9a-fA-F]+)\s*\|\s*Raw:\s*(-?\d+)"
        r"\s*\|\s*[^\r\n]+", line)
    if raw_match:
        raw = int(raw_match[2])
        if not -32768 <= raw <= 65535:
            raise ValueError('Raw value outside 16-bit range')
        line = json.dumps({'can_id': int(raw_match[1], 16),
                           'data': (raw & 0xffff).to_bytes(2, 'big').hex()})
    # Accept the diagnostic sketch's latest-sample rows, but never stale snapshots.
    if not line.lstrip().startswith('{'):
        match = re.fullmatch(
            r"\s*([0-9A-Fa-f]{3})/(\d+)\s+[^|]+\|\s*([0-9A-Fa-f]{2}) ([0-9A-Fa-f]{2})\s*\|"
            r"\s*\d+ / -?\d+\s*\|\s*[\d.]+\s*\|\s*(\d+)\s*\|\s*\d+\s*\|\s*\d+\s*", line)
        if not match or int(match[1], 16) != int(match[2]) or int(match[5]) > 2000:
            raise ValueError('Not a fresh CAN3 diagnostic sample')
        line = json.dumps({'can_id': int(match[1], 16), 'data': match[3] + match[4]})
    try:
        frame = json.loads(line)
        can_id = frame['can_id']
        if type(can_id) is not int or can_id not in CHANNELS:
            raise ValueError('Unknown CAN3 ID')
        data = frame['data']
        if not isinstance(data, str):
            raise ValueError('data must be hex text')
        payload = bytes.fromhex(data)
        if len(payload) != CHANNELS[can_id]['length']:
            raise ValueError('Incorrect CAN3 payload length')
    except (TypeError, KeyError, json.JSONDecodeError) as error:
        raise ValueError('Expected JSON: {"can_id": 1, "data": "1234"}') from error
    unsigned = int.from_bytes(payload, "big", signed=False)
    signed = int.from_bytes(payload, "big", signed=True)
    return (f'can3_raw,device={tag(device)},source={tag(source)},session={tag(session)},'
            f'can_id={can_id},channel={CHANNELS[can_id]["key"]} '
            f'byte_0={payload[0]}i,byte_1={payload[1]}i,unsigned_be={unsigned}i,signed_be={signed}i {timestamp_ns}')
