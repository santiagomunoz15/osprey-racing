"""Generate local credentials without replacing an existing .env."""
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / ".env"
if path.exists():
    print("Existing .env retained.")
else:
    with path.open("x", encoding="utf-8") as output:
        for key in ("POSTGRES_PASSWORD", "GRAFANA_DB_PASSWORD", "GRAFANA_ADMIN_PASSWORD"):
            output.write(f"{key}={secrets.token_hex(24)}\n")
    print("Created .env. Keep it private.")
