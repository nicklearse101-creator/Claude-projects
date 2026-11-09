"""Copy only the exported model files (export/sunbeam_rally*.kn5) into an installed car, leaving its data/, data.acd,
sfx, skins and extension alone - for model-only changes to a car whose physics Nik has edited himself.
The kn5s being replaced go to archive/replaced_<timestamp>_<car>_models/ first. Refuses while acs.exe is running.

    python tools/install_models.py talbot_sunbeam_lotus_81_works_backup_v6
"""
import shutil
import sys
import time
from pathlib import Path

from install_staged import ac_running

PROJECT = Path(__file__).resolve().parent.parent
EXPORT = PROJECT / "export"
CARS = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars")
MODELS = ("sunbeam_rally.kn5", "sunbeam_rally_lod_b.kn5", "sunbeam_rally_lod_c.kn5", "sunbeam_rally_lod_d.kn5")


def main(car_id):
    car = CARS / car_id
    if not car.is_dir():
        sys.exit(f"no car at {car}")
    missing = [m for m in MODELS if not (EXPORT / m).exists()]
    if missing:
        sys.exit(f"not exported: {missing}")
    if ac_running():
        sys.exit("Assetto Corsa (acs.exe) is running - exit the session first")
    backup = PROJECT / "archive" / f"replaced_{time.strftime('%Y%m%d_%H%M%S')}_{car_id}_models"
    backup.mkdir(parents=True)
    for m in MODELS:
        if (car / m).exists():
            shutil.copy2(car / m, backup / m)
        shutil.copy2(EXPORT / m, car / m)
        print(f"{m}: {(car / m).stat().st_size:,} bytes")
    print(f"installed into {car}\nprevious models kept in {backup}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "talbot_sunbeam_lotus_81_works_backup_v6")
