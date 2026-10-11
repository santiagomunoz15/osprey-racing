"""Import a CSV under data/ using Docker. Additional arguments go to the importer."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
if len(sys.argv) < 2:
    raise SystemExit("Usage: python scripts/import-run.py data/examples/bristol.csv [--timezone America/New_York]")
source = (Path.cwd() / sys.argv[1]).resolve()
data = (root / "data").resolve()
if not source.is_file() or not source.is_relative_to(data):
    raise SystemExit("Choose an existing CSV inside the project's data directory.")
container_path = "/data/" + source.relative_to(data).as_posix()
result = subprocess.run(["docker", "compose", "run", "--rm", "--build", "importer",
                         container_path, *sys.argv[2:]], cwd=root)
raise SystemExit(result.returncode)
