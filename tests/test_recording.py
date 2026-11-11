import signal
import time
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from osprey_telemetry.live.recording import Recording, read_points
from osprey_telemetry.live.usb_receiver import collect

ROOT = Path(__file__).resolve().parents[1]


class RecordingTests(unittest.TestCase):
    def test_queue_overflow_preserves_all_points_on_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.jsonl'
            args = SimpleNamespace(device='receiver', source='simulation', session='test',
                                   simulate=True, samples=10, rate=1000, local_only=False)
            stats = dict(received=0, invalid=0, dropped=0, written=0)
            recording = Recording(path, dict(device=args.device, source=args.source, session=args.session))
            collect(args, queue.Queue(maxsize=1), threading.Event(), stats, recording)
            recording.close()
            self.assertEqual(stats['received'], 10)
            self.assertEqual(stats['dropped'], 9)
            self.assertEqual(len(list(read_points(path))), 10)
            with self.assertRaises(FileExistsError):
                Recording(path, {})

    def test_record_and_replay_match_and_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.jsonl'
            captured = subprocess.run([sys.executable, 'scripts/receive-usb.py', '--simulate',
                '--samples', '10', '--rate', '100', '--dry-run', '--record', str(path)],
                cwd=ROOT, text=True, capture_output=True, check=True)
            command = [sys.executable, 'scripts/replay-usb.py', str(path), '--dry-run']
            replayed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
            self.assertEqual(captured.stdout, replayed.stdout)
            with path.open('a') as output:
                output.write('{"type":')
            broken = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(broken.returncode, 0)
            self.assertEqual(broken.stdout, '')

    def test_disk_failure_does_not_queue_unrecorded_point(self):
        args = SimpleNamespace(device='receiver', source='simulation', session='test',
                               simulate=True, samples=1, rate=50, local_only=False)
        inbox = queue.Queue()
        with tempfile.TemporaryDirectory() as directory:
            recording = Recording(Path(directory) / 'run.jsonl', {})
            try:
                with patch.object(recording, 'append', side_effect=OSError('disk full')):
                    with self.assertRaises(OSError):
                        collect(args, inbox, threading.Event(), dict(received=0, invalid=0), recording)
                self.assertTrue(inbox.empty())
            finally:
                recording.close()

    def test_shutdown_during_database_outage_retains_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'outage.jsonl'
            code = """
import os, sys
from unittest.mock import patch
from osprey_telemetry.live.usb_receiver import main
os.environ['INFLUX_DB_API_TOKEN'] = 'test-only'
sys.argv = ['receiver', '--simulate', '--samples', '20', '--rate', '100',
            '--queue-size', '2', '--batch-size', '1', '--record', sys.argv[1]]
with patch('osprey_telemetry.live.usb_receiver.InfluxWriter.write', side_effect=RuntimeError('offline')):
    main()
"""
            process = subprocess.Popen([sys.executable, '-c', code, str(path)], cwd=ROOT,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if path.exists() and len(path.read_text().splitlines()) == 21:
                        break
                    if process.poll() is not None:
                        self.fail('Receiver exited before completing recording')
                    time.sleep(0.05)
                self.assertEqual(len(list(read_points(path))), 20)
                process.send_signal(signal.SIGINT)
                _, errors = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, errors)
                self.assertIn('written=0', errors)
                self.assertEqual(len(list(read_points(path))), 20)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_local_only_needs_no_token_and_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.jsonl'
            result = subprocess.run([sys.executable, 'scripts/receive-usb.py', '--simulate',
                '--samples', '3', '--local-only', '--record', str(path),
                '--env-file', str(Path(directory) / 'missing.env')], cwd=ROOT,
                text=True, capture_output=True, check=True)
            self.assertEqual(len(list(read_points(path))), 3)
            self.assertIn('written=0', result.stderr)


if __name__ == '__main__':
    unittest.main()
