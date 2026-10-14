import sys
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from osprey_telemetry.live.usb_receiver import LineFramer, InfluxWriter, make_point, parse_message


class USBReceiverTests(unittest.TestCase):
    def test_captured_formats_and_invalid_readings(self):
        for arrow in ("->", "→"):
            self.assertEqual(parse_message(f"Received Data {arrow} Brake Pressure: 0.0 | Throttle: 12.0%"), (0, 12))
        for line in ("booting...", "Brake Pressure: 0 | Throttle:",
                     "Brake Pressure: nan | Throttle: 0%", "Brake Pressure: 0 | Throttle: 101%",
                     "Brake Pressure: -1 | Throttle: 10%"):
            with self.assertRaises(ValueError):
                parse_message(line)

    def test_fragmented_utf8_multiple_lines_and_oversized_recovery(self):
        message = "Received Data → Brake Pressure: 1.5 | Throttle: 12.0%\r\n".encode()
        framer = LineFramer()
        result = []
        for byte in message:
            result.extend(framer.feed(bytes([byte])))
        self.assertEqual(parse_message(result[0]), (1.5, 12))
        framer = LineFramer(limit=4)
        self.assertEqual(framer.feed(b"12345\nst\n"), ["st"])
        self.assertEqual(framer.discarded, 1)

    def test_point_and_batch_request(self):
        point = make_point("Brake Pressure: 1 | Throttle: 12%", 123, "pit box", "usb", "run=1")
        self.assertIn("device=pit\\ box", point)
        self.assertIn("session=run\\=1", point)
        self.assertIn("brake_pressure_raw=1.0,throttle_pct=12.0 123", point)
        response = MagicMock()
        response.__enter__.return_value.status = 204
        with patch("osprey_telemetry.live.usb_receiver.urlopen", return_value=response) as send:
            InfluxWriter("http://localhost:8086", "osprey-racing", "telemetry-test", "test-token").write([point, point])
            request = send.call_args.args[0]
            self.assertEqual(request.data.decode(), point + "\n" + point)
            self.assertIn("precision=ns", request.full_url)
        error = HTTPError("http://localhost", 401, "secret-content", {}, None)
        with patch("osprey_telemetry.live.usb_receiver.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
                InfluxWriter("http://localhost:8086", "org", "bucket", "token").write([point])

    def test_simulation_end_to_end_without_database(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, "-B", "scripts/receive-usb.py", "--simulate",
                                 "--samples", "20", "--rate", "200", "--dry-run"],
                                cwd=root, capture_output=True, text=True, check=True)
        self.assertEqual(len(result.stdout.splitlines()), 20)
        self.assertIn("source=simulation", result.stdout)
        self.assertIn("written=20", result.stderr)


if __name__ == "__main__":
    unittest.main()
