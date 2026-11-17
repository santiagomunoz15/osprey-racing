import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from osprey_telemetry.live.drive_sync import copy_recording

class DriveSyncTests(unittest.TestCase):
    def test_copy_is_exact_unique_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'run.jsonl'; source.write_bytes(b'{"type":"session"}\n')
            folder = root / 'drive'; folder.mkdir()
            first = copy_recording(source, folder, '../shop / no-driver')
            second = copy_recording(source, folder, '../shop / no-driver')
            self.assertEqual(first.read_bytes(), source.read_bytes())
            self.assertEqual(second.read_bytes(), source.read_bytes())
            self.assertNotEqual(first, second)
            self.assertEqual(first.parent, folder)
            self.assertFalse(list(folder.glob('*.partial')))

    def test_unavailable_drive_keeps_local_file_and_does_not_create_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'run.jsonl'; source.write_text('local copy\n')
            folder = Path(tmp) / 'unmounted'
            with self.assertRaises(OSError):copy_recording(source, folder, 'run')
            self.assertTrue(source.exists()); self.assertFalse(folder.exists())

    def test_receiver_copies_only_after_recording_closes(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root / 'drive'; folder.mkdir()
            recording = root / 'run.jsonl'
            result = subprocess.run([sys.executable, 'scripts/receive-usb.py', '--simulate',
                '--samples', '5', '--rate', '100', '--dry-run', '--record', str(recording),
                '--sync-dir', str(folder), '--session', 'sync-test'],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
            copies = list(folder.glob('*.jsonl'))
            self.assertEqual(len(copies), 1)
            self.assertEqual(copies[0].read_bytes(), recording.read_bytes())
            self.assertEqual(len(recording.read_text().splitlines()), 6)
            self.assertIn('Google Drive for desktop handles upload', result.stderr)
