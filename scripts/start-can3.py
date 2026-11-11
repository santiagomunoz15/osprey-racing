"""Start the local dashboard and capture a CAN3 receiver until Ctrl+C."""
import argparse
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', required=True, help='Close Arduino Serial Monitor first')
parser.add_argument('--session', help='Optional unique session name')
args = parser.parse_args()
subprocess.run(['docker', 'compose', 'up', '-d', 'influxdb', 'postgres', 'grafana'], cwd=root, check=True)
print('Dashboard: http://localhost:3000/d/osprey-can3', flush=True)
command = [sys.executable, str(root / 'scripts/receive-usb.py'), '--port', args.port]
if args.session:
    command += ['--session', args.session]
try:
    result = subprocess.run(command, cwd=root)
except KeyboardInterrupt:
    pass
else:
    sys.exit(result.returncode)
