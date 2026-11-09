"""Copy the installed car to a second car id, as a drivable backup (e.g. before physics changes).

    python backup_car.py v3 "what it is"   ->  content/cars/talbot_sunbeam_lotus_81_works_backup_v3,
                                               shown as "Talbot Sunbeam BACKUP v3 - what it is"
Backups are named BACKUP so they can never look newer than the live car (which carries its version in its own name,
build_rally_on_stock.PHYSICS_VERSION) - a backup called "_v2" next to an unnumbered live car was mistaken for the
newest one (2026-09-28).

* a packed data.acd can't be used under another folder name (the folder name is its key), so it is decoded into a
  plain data/ folder (setupcoach-tools acd_decoder); when data.acd and data/ both exist, data.acd is used (the game loads it)
* the sound bank and GUIDs.txt are renamed to the new id; ui name gets the label
* Nick's saved setups for the car are copied to the new id, so they work on the backup too
Refuses while acs.exe runs, and never overwrites an existing car folder.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Claude\setupcoach-tools\acd")
import acd_decoder  # noqa: E402

CAR_ID = "talbot_sunbeam_lotus_81_works"
CARS = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars")
SETUPS = Path.home() / "Documents" / "Assetto Corsa" / "setups"


def main(version, label):
    if "acs.exe" in subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/NH"],
                                   capture_output=True, text=True).stdout.lower():
        sys.exit("Assetto Corsa (acs.exe) is running - exit the session first")
    src, new_id = CARS / CAR_ID, f"{CAR_ID}_backup_{version}"
    dst = CARS / new_id
    if dst.exists():
        sys.exit(f"{dst} already exists")
    # the physics as the game loads them: data.acd wins over a data/ folder when both exist
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if Path(d) == src and n in ("data", "data.acd")])
    if (src / "data.acd").exists():
        tmp = dst.parent / f"__{new_id}_acd"
        out = acd_decoder.extract_car(CAR_ID, tmp)
        shutil.move(str(out), str(dst / "data"))
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        shutil.copytree(src / "data", dst / "data")
    sfx = dst / "sfx"
    (sfx / f"{CAR_ID}.bank").rename(sfx / f"{new_id}.bank")
    g = sfx / "GUIDs.txt"
    g.write_text(g.read_text(encoding="utf-8").replace(CAR_ID, new_id), encoding="utf-8")
    ui = dst / "ui" / "ui_car.json"
    info = json.loads(ui.read_text(encoding="utf-8"))
    info["name"] = f"Talbot Sunbeam BACKUP {version} - {label}"
    ui.write_text(json.dumps(info, indent=2), encoding="utf-8")
    if (SETUPS / CAR_ID).exists():
        shutil.copytree(SETUPS / CAR_ID, SETUPS / new_id, dirs_exist_ok=True)
    print(f"backup: {dst}\nin game: {info['name']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
