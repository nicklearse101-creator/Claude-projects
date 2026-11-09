"""Swap the staged build (staging/<car id>, made by build_rally_on_stock.build() with CAR pointed at it) into
AC's content/cars. Refuses while acs.exe is running - AC holds the car's files open during a session.
The previous installed version is moved to archive/replaced_<timestamp>/ rather than deleted."""
import shutil
import subprocess
import sys
import time
from pathlib import Path

CAR_ID = "talbot_sunbeam_lotus_81_works"
PROJECT = Path(__file__).resolve().parent.parent
STAGE = PROJECT / "staging" / CAR_ID
LIVE = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars") / CAR_ID


def ac_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/NH"], capture_output=True, text=True).stdout
    return "acs.exe" in out.lower()


def main():
    if not STAGE.exists():
        sys.exit(f"nothing staged at {STAGE}")
    if ac_running():
        sys.exit("Assetto Corsa (acs.exe) is running - exit the session first")
    backup = PROJECT / "archive" / f"replaced_{time.strftime('%Y%m%d_%H%M%S')}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if LIVE.exists():
        shutil.move(str(LIVE), str(backup))
    shutil.move(str(STAGE), str(LIVE))
    print(f"installed {LIVE}\nprevious version kept in {backup}")


if __name__ == "__main__":
    main()
