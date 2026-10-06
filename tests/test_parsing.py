import tempfile
import unittest
from pathlib import Path
from parsing import read_motec

class ParserTests(unittest.TestCase):
    def test_sample_preserves_rate_units_and_time(self):
        run = read_motec(Path(__file__).resolve().parents[1] / "bristol.csv")
        self.assertEqual(run["sample_rate"], 50)
        self.assertEqual(len(run["channels"]), 11)
        self.assertEqual(run["units"][1], "rpm")
        self.assertAlmostEqual(run["samples"][1][0] - run["samples"][0][0], 0.02)
        self.assertEqual(run["started_at"].isoformat(), "2026-09-19T01:00:22+00:00")

    def test_rejects_bad_width_and_preserves_missing_values(self):
        base = 'Format,MoTeC CSV File\nLog Date,18/09/2026\nLog Time,21:00:22\nSample Rate,50\n\nDistance,RPM\nm,rpm\n\n0,\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.csv"
            path.write_text(base)
            self.assertIsNone(read_motec(path)["samples"][0][2][1])
            path.write_text(base + "1,2,3\n")
            with self.assertRaisesRegex(ValueError, "expected 2 values"):
                read_motec(path)

if __name__ == "__main__":
    unittest.main()
