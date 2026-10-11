import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from osprey_telemetry.parsers.motec import read_motec

class ParserTests(unittest.TestCase):
    def test_sample_preserves_rate_units_and_time(self):
        run = read_motec(Path(__file__).resolve().parents[1] / "data" / "examples" / "bristol.csv")
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

    def test_time_first_us_export_preserves_explicit_timing(self):
        base = ('Format,MoTeC CSV File\nLog Date,9/15/2026\nLog Time,5:17:19 PM\n'
                'Sample Rate,50\nStart Time,12\n\nTime,Engine RPM,Ground Speed\n'
                's,rpm,km/h\n\n12.000,8000,40\n12.030,9200,45\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.csv"
            path.write_text(base)
            run = read_motec(path)
            self.assertEqual(run["started_at"].isoformat(), "2026-09-15T21:17:19+00:00")
            self.assertEqual([row[0] for row in run["samples"]], [12, 12.03])
            self.assertEqual(run["samples"][0][1].isoformat(), "2026-09-15T21:17:31+00:00")
            path.write_text(base + "12.030,8500,42\n")
            with self.assertRaisesRegex(ValueError, "strictly increasing"):
                read_motec(path)

if __name__ == "__main__":
    unittest.main()
