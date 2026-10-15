"""Generate missing local credentials, preserving existing values."""
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / ".env"
existing = path.read_text(encoding="utf-8") if path.exists() else ""
keys = {line.split("=", 1)[0].strip() for line in existing.splitlines() if "=" in line}
missing = [key for key in ("POSTGRES_PASSWORD", "GRAFANA_DB_PASSWORD",
           "GRAFANA_ADMIN_PASSWORD", "INFLUX_ADMIN_PASSWORD", "INFLUX_DB_API_TOKEN")
           if key not in keys]
if missing:
    with path.open("a", encoding="utf-8") as output:
        if existing and not existing.endswith("\n"):
            output.write("\n")
        for key in missing:
            output.write(f"{key}={secrets.token_hex(32)}\n")
    path.chmod(0o600)
print("Local credentials ready; existing values retained. Keep .env private.")
