import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from osprey_telemetry.live.can3 import CHANNELS
from osprey_telemetry.live.usb_receiver import make_point

class CAN3Tests(unittest.TestCase):
    def test_all_ids_preserve_byte_order(self):
        self.assertEqual(set(CHANNELS), {int(str(i), 16) for i in range(1, 28)})
        self.assertEqual(CHANNELS[0x22]["key"], "throttle")
        self.assertEqual(CHANNELS[0x10]["key"], "fuel_pressure")
        for cid in CHANNELS:
            point = make_point(json.dumps({'can_id': cid, 'data': '80ff'}), 123, 'esp32', 'usb', 'test')
            self.assertIn(f'can_id={cid},', point)
            self.assertTrue(point.endswith('byte_0=128i,byte_1=255i,unsigned_be=33023i,signed_be=-32513i 123'))

    def test_invalid_frames(self):
        for frame in ({'can_id': 0x28, 'data': '1234'}, {'can_id': True, 'data': '1234'},
                      {'can_id': 1, 'data': '12'}, {'can_id': 1, 'data': 'zzzz'},
                      {'can_id': 1, 'data': 1234}, {}, []):
            with self.assertRaises(ValueError):
                make_point(json.dumps(frame), 123, 'esp32', 'usb', 'test')

    def test_record_and_replay(self):
        import tempfile
        from osprey_telemetry.live.recording import Recording, read_points
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.jsonl'
            raw = '{"can_id": 39, "data": "0102"}'
            point = make_point(raw, 123, 'esp32', 'usb', 'test')
            rec = Recording(path, dict(device='esp32', source='usb', session='test'))
            rec.append(dict(type='sample', timestamp_ns=123, raw=raw, point=point))
            rec.close()
            self.assertEqual(list(read_points(path)), [point])

    def test_diagnostic_table_and_stale_rejection(self):
        line = '016/22 Steering Wheel Angle | FF DB | 65499 / -37 | 10.0 | 12 | 100 | 0'
        point = make_point(line, 123, 'esp32', 'usb', 'test')
        self.assertIn('can_id=22,channel=steering_wheel_angle', point)
        self.assertIn('signed_be=-37i', point)
        for invalid in (line + ' STALE', line.replace('| 12 |', '| 2500 |'), line.replace('016/22', '016/34')):
            with self.assertRaises(ValueError):
                make_point(invalid, 123, 'esp32', 'usb', 'test')

    def test_single_channel_sensor_sketch(self):
        point = make_point('ID: 0x016 | Raw: -37 | Sensor Reading: -37.0 Unit\r', 123, 'esp32', 'usb', 'test')
        self.assertIn('can_id=22,channel=steering_wheel_angle', point)
        self.assertIn('signed_be=-37i', point)
        with self.assertRaises(ValueError):
            make_point('ID: 0x016 | Raw: 65536 | Sensor Reading: 0 Unit', 123, 'esp32', 'usb', 'test')
