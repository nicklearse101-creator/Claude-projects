"""Back up the installed Escort as its own drivable car, or install the staged build.

    python install.py backup v19 "DTM conversion as it was"
        -> content/cars/ford_escort_mk2_tuned_backup_v19, "Ford Escort BACKUP v19 - DTM conversion as it was"
           (data.acd decoded into data/ - the acd is keyed to the folder name; sound bank + GUIDs renamed; setups copied)
    python install.py install [--with-model]
        -> moves the live data.acd to archive/replaced_<time>/ (AC loads data.acd over a data/ folder), copies
           staging/<car>/data in as data/, and renames the car in ui_car.json. Nik packs data.acd himself afterwards.
           The 3D model (export/*.kn5 + animations) is only copied with --with-model: a physics-only build (v26+,
           tools/mk1_build.py) must not overwrite a model Nik may have changed.
Both refuse while acs.exe runs; backup never overwrites a car folder. Backups are named BACKUP so they can never look
newer than the live car (feedback-backup-naming).
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, r"D:\Claude\setupcoach-tools\acd")
import acd_decoder  # noqa: E402
import mk1_build    # noqa: E402  (v26+; dtm_build.py = the v20-v25 Merc-190-based build, kept for history)

CAR_ID = mk1_build.CAR_ID
CARS = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars")
SETUPS = Path.home() / "Documents" / "Assetto Corsa" / "setups"
PROJECT = mk1_build.PROJECT
DESCRIPTION = ("DTM Class 1 inspired conversion: ~400hp 4.0L N/A V8 to 8500rpm, 6-speed sequential, 1050kg, 90s DTM aero kit "
               "(air dam + splitter, skirts, rear lip, pedestal rear wing), opening doors, treadplate door panels, 4.0 V8 in the "
               "bay, Mk2 door mirrors, stainless tank on the boot floor. v26: chassis physics rebuilt on the Kunos Ford Escort "
               "Mk1 - strut front, 5-link live axle, Mk1 geometry/dampers/brakes scaled for the extra mass (same ride frequency "
               "and damping as the Mk1), Vintage GT70 tyres with the Kunos DTM90 slicks as optional compounds. "
               "Model: 101Creative; physics base: Kunos / graveltrap. Personal use only.")
# v24: door animations (tools/blender/model_fixes.py) + CSP binding: the car's ext_config already had an empty
# [ANIMATION_2] bound to Extra C - both doors go on it (Extra C opens/closes them in game; CM's showroom uses the files)
DOOR_ANIMS = {"ANIMATION_2": "car_door_L.ksanim", "ANIMATION_3": "car_door_R.ksanim"}


def refuse_if_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/NH"], capture_output=True, text=True).stdout
    if "acs.exe" in out.lower():
        sys.exit("Assetto Corsa (acs.exe) is running - exit the session first")


def files_from_acd(acd, key):
    files = acd_decoder.decrypt_acd(acd, key)
    assert "[GEARS]" in files.get("drivetrain.ini", "") or "[TRACTION]" in files.get("drivetrain.ini", ""), "bad decode"
    return files


def backup(version, label):
    refuse_if_running()
    src, new_id = CARS / CAR_ID, f"{CAR_ID}_backup_{version}"
    dst = CARS / new_id
    if dst.exists():
        sys.exit(f"{dst} already exists")
    skip = lambda d, names: [n for n in names if Path(d) == src and (n.startswith("data.acd") or n == "data"
                                                                       or n.endswith(".acd"))]
    shutil.copytree(src, dst, ignore=skip)
    data = dst / "data"
    data.mkdir()
    if (src / "data.acd").exists():                       # what the game loads
        for name, text in files_from_acd(src / "data.acd", CAR_ID).items():
            with open(data / name, "w", encoding="utf-8", newline="") as fh:     # newline="": the acd text already has CRLF
                fh.write(text if isinstance(text, str) else text.decode("utf-8", "replace"))
    else:
        shutil.copytree(src / "data", data, dirs_exist_ok=True)
    sfx = dst / "sfx"
    (sfx / f"{CAR_ID}.bank").rename(sfx / f"{new_id}.bank")
    g = sfx / "GUIDs.txt"
    g.write_text(g.read_text(encoding="utf-8").replace(f"bank:/{CAR_ID}", f"bank:/{new_id}").replace(f"/cars/{CAR_ID}/", f"/cars/{new_id}/"),
                 encoding="utf-8")
    ui = dst / "ui" / "ui_car.json"
    info = json.loads(ui.read_text(encoding="utf-8-sig"), strict=False)
    info["name"] = f"Ford Escort BACKUP {version} - {label}"
    ui.write_text(json.dumps(info, indent=2), encoding="utf-8")
    if (SETUPS / CAR_ID).exists():
        shutil.copytree(SETUPS / CAR_ID, SETUPS / new_id, dirs_exist_ok=True)
    print(f"backup: {dst}\nin Content Manager: {info['name']}")


def install(with_model=False):
    refuse_if_running()
    live, staged = CARS / CAR_ID, PROJECT / "staging" / CAR_ID / "data"
    if not staged.exists():
        sys.exit(f"nothing staged at {staged} - run mk1_build.py")
    arc = PROJECT / "archive" / f"replaced_{time.strftime('%Y%m%d_%H%M%S')}"
    arc.mkdir(parents=True)
    for name in ("data.acd", "data"):
        if (live / name).exists():
            shutil.move(str(live / name), str(arc / name))
    shutil.copytree(staged, live / "data")
    ui = live / "ui" / "ui_car.json"
    shutil.copy2(ui, arc / "ui_car.json")
    info = json.loads(ui.read_text(encoding="utf-8-sig"), strict=False)
    info["name"] = f"Ford Escort Mk2 DTM {mk1_build.VERSION}"
    info["description"] = DESCRIPTION
    info["version"] = mk1_build.VERSION
    ui.write_text(json.dumps(info, indent=2), encoding="utf-8")    # specs + torque/power curves stay as installed (engine unchanged)
    # 3D model with the aero kit (tools/blender/export_aero.py) - only when all four files are exported
    models = [f"{CAR_ID}.kn5"] + [f"{CAR_ID}_lod_{t}.kn5" for t in "bcd"]
    export = PROJECT / "export"
    if not with_model:
        print("model + animations: untouched (physics-only install; pass --with-model to copy export/)")
        print(f"installed {mk1_build.VERSION} into {live}\nprevious data kept in {arc}")
        return
    if all((export / m).exists() for m in models):
        for m in models:
            shutil.copy2(live / m, arc / m)
            shutil.copy2(export / m, live / m)
        print(f"model: {', '.join(models)} from {export}")
    anims = sorted((export / "animations").glob("*.ksanim"))
    if anims:
        (arc / "animations").mkdir(exist_ok=True)
        for a in anims:
            if (live / "animations" / a.name).exists():
                shutil.copy2(live / "animations" / a.name, arc / "animations" / a.name)
            shutil.copy2(a, live / "animations" / a.name)
        print(f"animations: {', '.join(a.name for a in anims)}")
        bind_door_anims(live, arc)
    print(f"installed {mk1_build.VERSION} into {live}\nprevious data kept in {arc}")


def bind_door_anims(live, arc):
    """ext_config: [ANIMATION_2] (empty FILE, Extra C) -> left door, add [ANIMATION_3] -> right door, same button."""
    cfg = live / "extension" / "ext_config.ini"
    text = cfg.read_text(encoding="utf-8", errors="replace")
    shutil.copy2(cfg, arc / "ext_config.ini")
    for sec, fname in DOOR_ANIMS.items():
        block = f"[{sec}]\nFILE={fname}\nTIME= 1\nBIND_TO_EXTRA_C=1\n"
        m = re.search(rf"^\[{sec}\]\s*\n(?:(?!\[).*\n?)*", text, re.M)
        text = text[:m.start()] + block + "\n" + text[m.end():] if m else text.rstrip("\n") + "\n\n" + block
    cfg.write_text(text, encoding="utf-8")
    print(f"ext_config: doors on Extra C ({', '.join(DOOR_ANIMS.values())})")


if __name__ == "__main__":
    if sys.argv[1:2] == ["backup"]:
        backup(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["install"]:
        install(with_model="--with-model" in sys.argv[2:])
    else:
        sys.exit(__doc__)
