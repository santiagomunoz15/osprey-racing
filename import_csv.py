"""Validate or transactionally import a MoTeC run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from parsing import read_motec

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--timezone", default="America/New_York", help="Timezone of the logger's local clock")
    parser.add_argument("--name", help="Friendly run name")
    parser.add_argument("--dry-run", action="store_true", help="Validate without a database")
    args = parser.parse_args()
    run = read_motec(args.csv, args.timezone)
    print(f'{args.csv.name}: {len(run["samples"])} samples, {len(run["channels"])} channels, {run["sample_rate"]:g} Hz')
    print(f'Logger time interpreted as {args.timezone}; UTC start: {run["started_at"].isoformat()}')
    if args.dry_run:
        return
    import psycopg
    identity = hashlib.sha256(args.csv.read_bytes() + args.timezone.encode()).hexdigest()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        result = conn.execute(
            "INSERT INTO runs (file_hash, name, started_at, sample_rate, metadata, source_timezone) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (file_hash) DO NOTHING RETURNING id",
            (identity, args.name or args.csv.stem, run["started_at"], run["sample_rate"],
             json.dumps(run["metadata"]), args.timezone)).fetchone()
        if result is None:
            print("Already imported; no duplicate data added.")
            return
        run_id = result[0]
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO channels (run_id,name,unit) VALUES (%s,%s,%s)",
                            [(run_id, name, unit) for name, unit in zip(run["channels"], run["units"])])
            with cur.copy("COPY samples (run_id, channel, elapsed_s, recorded_at, value) FROM STDIN") as copy:
                for elapsed, timestamp, values in run["samples"]:
                    for name, value in zip(run["channels"], values):
                        copy.write_row((run_id, name, elapsed, timestamp, value))
    print(f"Imported run {run_id}. Open Grafana and refresh the run selector.")

if __name__ == "__main__":
    main()
