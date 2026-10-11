"""Start Grafana and PostgreSQL from any working directory."""
from pathlib import Path
import subprocess

subprocess.run(["docker", "compose", "up", "-d", "postgres", "grafana"],
               cwd=Path(__file__).resolve().parents[1], check=True)
