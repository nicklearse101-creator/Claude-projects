"""Rally conversion of the existing Sunbeam mod (personal use).

3D model, textures, skins, sound, CSP config and every model-tied data file come
from talbot_sunbeam_lotus_lhd_stock ("marcel du PMU / Mr.Hunt", v1.1 by ACTK).
Physics come from our own build (build_car.build_data: Kunos Escort Mk1 base +
Sunbeam FIA 1700 numbers), with the few values that position the model changed
to match THEIR model: track, tyre/rim radius, GRAPHICS_OFFSET, [GRAPHICS] cameras.

NOT for sharing or server use without the original authors' permission.
Re-running rebuilds the whole car folder from the two sources.
"""
import importlib.util
import json
import re
import shutil
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("build_car", TOOLS / "build_car.py")
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)
_cf = importlib.util.spec_from_file_location("collider_fit", TOOLS / "collider_fit.py")
collider_fit = importlib.util.module_from_spec(_cf)
_cf.loader.exec_module(collider_fit)

STOCK_ID = "talbot_sunbeam_lotus_lhd_stock"
STOCK = bc.AC / "content" / "cars" / STOCK_ID
STOCK_DATA = bc.PROJECT / "refs" / "stock_mod_data" / STOCK_ID
CAR, CAR_ID = bc.CAR, bc.CAR_ID
ARCHIVE = bc.PROJECT / "archive" / "v0.3_own_model"

# the stock model's wheels/body, as set up in its own data
STOCK_TRACK_F, STOCK_TRACK_R = 1.329, 1.342
STOCK_TYRE_R, STOCK_RIM_R = 0.295, 0.1651
STOCK_OFFSET = (0.0, -0.365, -0.247)
STOCK_CG_LOC, STOCK_BASEY = 0.60, (-0.230, -0.230)

MODEL_FILES = ["collider.kn5", "driver_base_pos.knh", "body_shadow.png"] + [f"tyre_{i}_shadow.png" for i in range(4)]
STOCK_LODS = ["TSL_LHD_stock.kn5", "TSL_LHD_stock_lod_b.kn5", "TSL_LHD_stock_lod_c.kn5", "TSL_LHD_stock_lod_d.kn5"]

# rally version: edited model from Blender (flares, 8-spoke rims, lamps, mud flaps) - see export_rally.py
RALLY_KN5 = bc.PROJECT / "export" / "sunbeam_rally.kn5"
# shown in the car's name, so the live car can't be mistaken for a backup (backups: "Talbot Sunbeam BACKUP vN - ...",
# folders ..._backup_vN - Nick drove the old "_v2" backup thinking it was the newest car, 2026-09-28)
PHYSICS_VERSION = "v7"
NAME = f"Talbot Sunbeam Lotus Rally {PHYSICS_VERSION}"
SHIFT_PRELOAD_RPM = 7500        # driver's hand goes to the gear lever from here, ready to upshift (stock mod: 6200)
RALLY_TRACK_ADD = 0.096        # from build_rally_parts.build(): tyre outer edge 12 mm inside the flare lip
RALLY_RIM_R = 0.2159            # grafted Mk2 wheel scaled to the 0.295 tyre: ~16" bead -> AC's nominal+1" rule
# Spot lamps light with MAIN BEAM only, which is CSP's (lights.ini only knows "headlights on"): the lens glows via
# [EMISSIVE_HIGHBEAM_...] and a [LIGHT_EXTRA_...] beam per lamp follows that glow (BOUND_TO + BOUND_EMISSIVE_MAX).
# LIGHT_EXTRA rather than LIGHT_HEADLIGHT so CSP's own headlight beams are left alone. Positions in kn5 space
# (x left, y up, z forward): lens faces from build_rally_parts.build_spot_lamps (Blender (x, y, z) -> (x, z, -y)).
RALLY_LIGHTS = []                     # (no lights.ini entries any more - they came on with dipped beam)
# lamp prefix, position, beam cone (deg), range (m), intensity. Each lamp: _a_SUB1 = front cover glass (OPAQUE in the
# stock fog lamp - the glow must go on it; v1 lit only the fluted lens _a_SUB0 behind it, so nothing showed)
SPOT_LAMPS = [
    ("RALLY_SPOT_LU", (0.215, 0.455, 2.03), 16, 150, 22),
    ("RALLY_SPOT_RU", (-0.215, 0.455, 2.03), 16, 150, 22),
    ("RALLY_SPOT_LD", (0.335, 0.262, 2.01), 42, 90, 16),
    ("RALLY_SPOT_RD", (-0.335, 0.262, 2.01), 42, 90, 16),
]
NL = "\n"


def spot_lamp_csp():
    out = ["", "; ---- rally spot lamps: main beam only (added by build_rally_on_stock.py) ----"]
    for mesh, pos, cone, rng, power in SPOT_LAMPS:
        out += ["", "[EMISSIVE_HIGHBEAM_...]", f"MESHES={mesh}_a_SUB4, {mesh}_a_SUB1, {mesh}_a_SUB0", "COLOR=400, 380, 320, 0.2",
                "LAG=0.3", "SIMULATE_HEATING=1", "LOCATION=FRONT"]   # strength as CSP's Alfa 33 config; warm white (clear lenses since v0.13)
    for mesh, pos, cone, rng, power in SPOT_LAMPS:
        out += ["", "[LIGHT_EXTRA_...]", f"POSITION={pos[0]}, {pos[1]}, {pos[2]}", "DIRECTION=0, -0.02, 1",
                f"COLOR=1, 0.95, 0.82, {power}", f"RANGE={rng}", "RANGE_GRADIENT_OFFSET=0.1", f"SPOT={cone}",
                "SPOT_SHARPNESS=0.4", "DIFFUSE_CONCENTRATION=0.88", "SPECULAR_MULT=1", "FADE_AT=600", "FADE_SMOOTH=100",
                "AFFECTS_TRACK=1", "EXTERIOR_ONLY=0", "INTERIOR_ONLY=0", "BIND_TO_HEADLIGHTS=0",
                f"BOUND_TO={mesh}_a_SUB1", "BOUND_EMISSIVE_MAX=60"]
    return NL.join(out) + NL


def fix_driver3d(path):
    """The stock mod hides one helmet part under a mistyped name (DRIVER:DRIVER:HELMET_1975_SUB0), so it shows in the
    cockpit view as a line swinging at the top of the windscreen. Rewrite the hide list with the real node names."""
    sections, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            cur = [m.group(1), []]
            sections.append(cur)
        elif cur is not None and line.strip():
            cur[1].append(line)
    hidden = []
    for name, body in sections:
        if name.startswith("HIDE_OBJECT_"):
            for l in body:
                if l.startswith("NAME="):
                    n = l[5:].strip().replace("DRIVER:DRIVER:", "DRIVER:")
                    if n not in hidden:
                        hidden.append(n)
    out = []
    for name, body in sections:
        if not name.startswith("HIDE_OBJECT_"):
            out += [f"[{name}]"] + body + [""]
    for i, n in enumerate(hidden):
        out += [f"[HIDE_OBJECT_{i}]", f"NAME={n}", ""]
    path.write_text(NL.join(out), encoding="utf-8")
    return hidden


RALLY_SKINS = {
    # skin folder: (label, body paint, stripe paint, rim colour) - sRGB 0-1
    "rally_yellow_green": ("Rally yellow / green", (0.97, 0.76, 0.02), (0.05, 0.50, 0.20), (0.72, 0.60, 0.30)),
}


def dds_solid(rgb, size=16):
    """Uncompressed 32-bit BGRA DDS, one flat colour (what a skin's paint 'detail' texture needs)."""
    import struct
    head = struct.pack("<4s7I44s", b"DDS ", 124, 0x100F, size, size, size * 4, 0, 0, b"\0" * 44)
    pf = struct.pack("<8I", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps = struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    r, g, b = (max(0, min(255, round(c * 255))) for c in rgb)
    return head + pf + caps + bytes((b, g, r, 255)) * (size * size)
MODEL_DIRS = ["animations", "texture", "extension", "skins"]
# data files that name nodes/meshes of the model or place cameras on it
MODEL_DATA = ["lods.ini", "lights.ini", "mirrors.ini", "blurred_objects.ini", "driver3d.ini",
              "extra_animations.ini", "dash_cam.ini", "cameras.ini", "analog_instruments.ini",
              "digital_instruments.ini", "flames.ini", "flame_presets.ini", "ambient_shadows.ini",
              "colliders.ini", "suspension_graphics.ini", "wing_animations.ini", "sounds.ini"]


def cg(tyre_r, cg_loc, basey):
    """(CG height above ground, CG distance ahead of mid-wheelbase) in AC's own terms."""
    return tyre_r + cg_loc * -basey[0] + (1 - cg_loc) * -basey[1], bc.WHEELBASE * (cg_loc - 0.5)


def graphics_offset():
    """Keep the stock model exactly where it sat relative to its wheels, under our CG."""
    h0, a0 = cg(STOCK_TYRE_R, STOCK_CG_LOC, STOCK_BASEY)
    h1, a1 = cg(STOCK_TYRE_R, bc.CG_LOCATION, (bc.BASEY_F, bc.BASEY_R))
    return (STOCK_OFFSET[0], STOCK_OFFSET[1] - (h1 - h0), STOCK_OFFSET[2] + (a0 - a1))


def archive_own_model():
    if ARCHIVE.exists():
        return
    ARCHIVE.mkdir(parents=True)
    for f in (f"{CAR_ID}.kn5", "collider.kn5"):
        if (CAR / f).exists():
            shutil.copy2(CAR / f, ARCHIVE / f)


def replace_section(path, section, new_body_lines):
    lines = path.read_text(encoding="utf-8").splitlines()
    out, skip = [], False
    for line in lines:
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            if skip:
                skip = False
            if m.group(1) == section:
                out.append(line)
                out.extend(new_body_lines)
                skip = True
                continue
        if not skip:
            out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def section_body(path, section):
    body, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            inside = m.group(1) == section
            continue
        if inside:
            body.append(line)
    return body


def build():
    archive_own_model()
    # clean slate (keep nothing of the old model)
    for p in CAR.iterdir():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()

    bc.build_data()                       # our physics (writes data/)
    data = CAR / "data"
    for f in MODEL_DATA:
        src = STOCK_DATA / f
        if src.exists():
            shutil.copyfile(src, data / f)
        else:
            (data / f).unlink(missing_ok=True)
    (data / "proview_nodes.ini").unlink(missing_ok=True)

    car = data / "car.ini"
    replace_section(car, "GRAPHICS", section_body(STOCK_DATA / "car.ini", "GRAPHICS"))
    off = graphics_offset()
    fit = bc.PROJECT / "export" / "graphics_fit.json"          # measured in AC by ac_static_ride.py, if done
    if fit.exists():
        m = json.loads(fit.read_text())
        off = tuple(m["GRAPHICS_OFFSET"])
        bc.set_ini(car, "BASIC", "GRAPHICS_PITCH_ROTATION", f"{m['GRAPHICS_PITCH_ROTATION']:.2f}")
    bc.set_ini(car, "BASIC", "GRAPHICS_OFFSET", f"{off[0]:.3f},{off[1]:.3f},{off[2]:.3f}")
    # colliders + fuel tank fitted to OUR model in OUR frame (the stock mod's slabs and the Escort's tank position
    # sat ~7 cm off the model, ended short of nose/tail, and the tank sat in the bumper) - see collider_fit.py
    pitch = float(re.search(r"^GRAPHICS_PITCH_ROTATION\s*=\s*([-\d.]+)", car.read_text(encoding="utf-8"), re.M).group(1))
    (data / "colliders.ini").write_text(collider_fit.colliders_text(off, pitch), encoding="utf-8")
    bc.set_ini(car, "FUELTANK", "POSITION", collider_fit.tank_position(off, pitch))
    bc.set_ini(car, "INFO", "SCREEN_NAME", NAME)
    rally = RALLY_KN5.exists()
    add = RALLY_TRACK_ADD if rally else 0.0
    sus = data / "suspensions.ini"
    bc.set_ini(sus, "FRONT", "TRACK", f"{STOCK_TRACK_F + add:.3f}")
    bc.set_ini(sus, "REAR", "TRACK", f"{STOCK_TRACK_R + add:.3f}")
    tyres = data / "tyres.ini"
    bc.set_ini(tyres, r"(FRONT|REAR)(_\d+)?", "RADIUS", f"{STOCK_TYRE_R:.3f}", pattern=True)
    bc.set_ini(tyres, r"(FRONT|REAR)(_\d+)?", "RIM_RADIUS", f"{RALLY_RIM_R if rally else STOCK_RIM_R:.4f}", pattern=True)
    # front camber range widened to -4.5 deg in the installed (CM-packed data.acd) copy on 2026-09-28 ~17:00 - Setup
    # Coach's Bathurst setup runs -4.2; kept here so a rebuild doesn't take it away (Escort default MIN=-2.5)
    bc.set_ini(data / "setup.ini", r"CAMBER_[LR]F", "MIN", "-4.5", pattern=True)
    bc.add_dampers(data)                  # v4: adjustable dampers (bump / fast bump / rebound / fast rebound, each corner)
    bc.apply_springs(data)                # v5: springs for the Sunbeam's weight, rods lowered to keep the stance
    bc.add_setup_v6(data)                 # v6: adjustable anti-roll bars front + rear, diff preload
    if bc.REAR_TYPE == "DWB":
        bc.apply_rear_dwb(data)           # v7: double-wishbone rear (not historical) + rear camber/toe

    for f in MODEL_FILES:
        shutil.copy2(STOCK / f, CAR / f)
    for d in MODEL_DIRS:
        # (Content Manager watches car folders and can recreate e.g. skins/ the moment it's deleted)
        shutil.copytree(STOCK / d, CAR / d, dirs_exist_ok=True)
    fix_driver3d(data / "driver3d.ini")
    bc.set_ini(data / "driver3d.ini", "SHIFT_ANIMATION", "PRELOAD_RPM", str(SHIFT_PRELOAD_RPM))
    if rally:
        ext = CAR / "extension" / "ext_config.ini"
        ext.write_text(ext.read_text(encoding="utf-8") + spot_lamp_csp(), encoding="utf-8")
        shutil.copy2(RALLY_KN5, CAR / RALLY_KN5.name)
        # distance LODs from build_lods.py (the stock LODs + decimated rally parts), stock switch distances
        lods = [(RALLY_KN5.name, 0, 15)]
        for tag, (lo, hi) in (("b", (15, 45)), ("c", (45, 201)), ("d", (201, 2000))):
            f = RALLY_KN5.with_name(f"sunbeam_rally_lod_{tag}.kn5")
            if f.exists():
                shutil.copy2(f, CAR / f.name)
                lods.append((f.name, lo, hi))
        lods[-1] = (lods[-1][0], lods[-1][1], 2000)
        text = "[COCKPIT_HR]\nDISTANCE_SWITCH=7\n"
        for i, (f, lo, hi) in enumerate(lods):
            text += f"\n[LOD_{i}]\nFILE={f}\nIN={lo}\nOUT={hi}\n"
        (data / "lods.ini").write_text(text, encoding="utf-8")
        lights = data / "lights.ini"
        text = lights.read_text(encoding="utf-8")
        n = max([int(m) for m in re.findall(r"^\[LIGHT_(\d+)\]", text, re.M)] + [-1]) + 1
        for i, (mesh, colour) in enumerate(RALLY_LIGHTS):
            text += f"\n[LIGHT_{n + i}]\nNAME={mesh}\nCOLOR={colour}\n"
        lights.write_text(text, encoding="utf-8")
        for folder, (label, paint, stripe, rim) in RALLY_SKINS.items():
            sk = CAR / "skins" / folder
            sk.mkdir(parents=True, exist_ok=True)
            (sk / "metal_detail.dds").write_bytes(dds_solid(paint))
            (sk / "metal_detail_2.dds").write_bytes(dds_solid(stripe))
            (sk / "ui_skin.json").write_text(json.dumps({"skinname": label, "drivername": "", "country": "Great Britain",
                                                         "team": "", "number": "", "priority": 1}, indent=2), encoding="utf-8")
    else:
        for f in STOCK_LODS:
            shutil.copy2(STOCK / f, CAR / f)

    # their engine sound, renamed to our car id
    sfx = CAR / "sfx"; sfx.mkdir()
    shutil.copyfile(STOCK / "sfx" / f"{STOCK_ID}.bank", sfx / f"{CAR_ID}.bank")
    guids = (STOCK / "sfx" / "GUIDs.txt").read_text(encoding="utf-8").replace(STOCK_ID, CAR_ID)
    (sfx / "GUIDs.txt").write_text(guids, encoding="utf-8")

    bc.build_ui()
    ui = CAR / "ui" / "ui_car.json"
    info = json.loads(ui.read_text(encoding="utf-8"))
    info["name"] = NAME
    info["author"] = "Model: marcel du PMU / Mr.Hunt (v1.1 ACTK) - rally physics: Nicklearse101"
    info["description"] = ("Rally conversion for personal use. 3D model, textures, sound and CSP config from "
                           "'Talbot Sunbeam Lotus' by marcel du PMU / Mr.Hunt (v1.1 by ACTK). Physics: 1981 works "
                           "Group 2 spec (FIA homologation 1700 gearbox, 90 L tank, " + ("Sunbeam four-link rear axle" if bc.REAR_TYPE == "AXLE"
                           else "double-wishbone rear in place of the real four-link axle") + ") on a "
                           "Kunos Escort Mk1 base. Do not share without the original authors' permission.")
    info["version"] = "0.6" if rally else "0.4"
    ui.write_text(json.dumps(info, indent=2), encoding="utf-8")
    shutil.copyfile(STOCK / "ui" / "badge.png", CAR / "ui" / "badge.png")
    return off


if __name__ == "__main__":
    off = build()
    print(f"built {CAR}\nGRAPHICS_OFFSET={off}")
