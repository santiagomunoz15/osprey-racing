"""Run the local USB receiver from the project root without installing the package."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from osprey_telemetry.live.usb_receiver import main

if __name__ == "__main__":
    main()
