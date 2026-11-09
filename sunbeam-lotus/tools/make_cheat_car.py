"""Make a KNOWN-CHEAT test car for ac-physics-watchdog: a copy of the installed Sunbeam with more engine power.

    python make_cheat_car.py 10   ->  content/cars/talbot_sunbeam_lotus_81_works_cheat_plus10,
                                      named "Talbot Sunbeam CHEAT +10% power (watchdog test)"

* the engine's torque curve (engine.ini POWER_CURVE, i.e. power.lut) x (1 + pct/100) at every rpm - nothing else
  in the physics changes
* named CHEAT in Content Manager (ui_car.json), in game (car.ini SCREEN_NAME) and in its description and specs, so it
  can never be mistaken for the real car (a backup once was - see backup_car.py)
* the real car's files are written to watchdog_reference/<new id>/data: list that folder FIRST in the watchdog's
  watchdog.ini [analysis] content_dirs and it judges the test car against the honest files, the way a server judges
  a cheater against its own copy (the watchdog takes the first folder that has the car)
* physics are taken as the game loads them: data.acd when there is one (it wins over data/), else data/
* sound bank + GUIDs renamed to the new id; Nik's saved setups copied
Refuses while acs.exe runs and never overwrites an existing car or reference folder.
"""
import filecmp
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Claude\setupcoach-tools\acd")
import acd_decoder  # noqa: E402

CAR_ID = "talbot_sunbeam_lotus_81_works"
CARS = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars")
SETUPS = Path.home() / "Documents" / "Assetto Corsa" / "setups"
REFERENCE = Path(__file__).resolve().parent.parent / "watchdog_reference"


def read_lut(path):
    return [(float(a), float(b)) for a, b in re.findall(r"^\s*([-\d.]+)\s*\|\s*([-\d.]+)", path.read_text(encoding="utf-8"), re.M)]


def scale_lut(path, factor):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\s*[-\d.]+\s*\|\s*)([-\d.]+)(.*)$", line)
        out.append(f"{m.group(1)}{float(m.group(2)) * factor:.2f}{m.group(3)}" if m else line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main(pct):
    pct = float(pct)
    factor = 1 + pct / 100
    new_id = f"{CAR_ID}_cheat_plus{pct:g}".replace(".", "_")
    name = f"Talbot Sunbeam CHEAT +{pct:g}% power (watchdog test)"
    if "acs.exe" in subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/NH"],
                                   capture_output=True, text=True).stdout.lower():
        sys.exit("Assetto Corsa (acs.exe) is running - exit the session first")
    src, dst, ref = CARS / CAR_ID, CARS / new_id, REFERENCE / new_id / "data"
    for p in (dst, ref.parent):
        if p.exists():
            sys.exit(f"{p} already exists")

    # the honest physics, exactly as the game loads them -> the watchdog's reference copy
    tmp = None
    if (src / "data.acd").exists():
        tmp = REFERENCE / f"__decode_{new_id}"
        honest = Path(acd_decoder.extract_car(CAR_ID, tmp))
    else:
        honest = src / "data"
    if not (honest / "drivetrain.ini").exists():
        sys.exit(f"no readable physics in {honest}")
    shutil.copytree(honest, ref)
    if tmp:
        shutil.rmtree(tmp)

    # the car: everything but its physics, then the honest physics, then the cheat
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if Path(d) == src and n in ("data", "data.acd")])
    data = dst / "data"
    shutil.copytree(ref, data)
    curve = re.search(r"^\s*POWER_CURVE\s*=\s*([^\s;]+)", (data / "engine.ini").read_text(encoding="utf-8"), re.M).group(1)
    scale_lut(data / curve, factor)
    car = data / "car.ini"
    car.write_text(re.sub(r"(?m)^SCREEN_NAME=.*$", f"SCREEN_NAME={name}", car.read_text(encoding="utf-8")), encoding="utf-8")

    sfx = dst / "sfx"
    (sfx / f"{CAR_ID}.bank").rename(sfx / f"{new_id}.bank")
    g = sfx / "GUIDs.txt"
    g.write_text(g.read_text(encoding="utf-8").replace(CAR_ID, new_id), encoding="utf-8")

    ui = dst / "ui" / "ui_car.json"
    info = json.loads(ui.read_text(encoding="utf-8"))
    info["name"] = name
    info["description"] = (f"WATCHDOG TEST CAR - NOT FOR RACING. A known cheat for ac-physics-watchdog: the real car "
                           f"({CAR_ID}) with +{pct:g}% engine power, nothing else changed. " + info["description"])
    info["tags"] = info.get("tags", []) + ["watchdog test"]
    s = info["specs"]
    bhp = round(float(re.match(r"[\d.]+", s["bhp"]).group()) * factor)
    s["bhp"] = f"{bhp}bhp"
    s["torque"] = f"{round(float(re.match(r'[\d.]+', s['torque']).group()) * factor)}Nm"
    s["pwratio"] = f"{float(re.match(r'[\d.]+', s['weight']).group()) / bhp:.2f}kg/hp"
    for key in ("torqueCurve", "powerCurve"):
        info[key] = [[r, round(v * factor, 1)] for r, v in info[key]]
    ui.write_text(json.dumps(info, indent=2), encoding="utf-8")

    if (SETUPS / CAR_ID).exists():
        shutil.copytree(SETUPS / CAR_ID, SETUPS / new_id, dirs_exist_ok=True)

    # prove it: only the torque curve and the screen name differ from the real car, by exactly the factor
    cmp = filecmp.dircmp(ref, data)
    assert set(cmp.diff_files) == {curve, "car.ini"} and not cmp.left_only and not cmp.right_only, cmp.diff_files
    ratios = {round(c / h, 4) for (_, h), (_, c) in zip(read_lut(ref / curve), read_lut(data / curve)) if h}
    assert ratios == {round(factor, 4)}, ratios
    assert json.loads(ui.read_text(encoding="utf-8"))["name"] == name
    print(f"cheat car: {dst}\nin Content Manager and in game: {name}\n{curve} x{factor:g} at every rpm; "
          f"everything else identical to {CAR_ID}\nwatchdog reference (honest files): {ref}")


if __name__ == "__main__":
    main(sys.argv[1])
