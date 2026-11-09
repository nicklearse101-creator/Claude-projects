"""Ford Escort Mk2 DTM v20 - a rebuild of Nik's "90s DTM" conversion of ford_escort_mk2_tuned (mod by 101Creative &
graveltrap - personal use only). Writes staging/ford_escort_mk2_tuned/data; tools/install.py puts it in the game.

Why (2026-10-05 diagnosis, v19 against Kunos' own DTM cars - Merc 190E Evo II DTM, Alfa 155 V6 Ti, M3 E30 DTM):
springs 35/26 kN/m (refs 80-200 / 60-105), dampers ~10x too soft (bump 840/880 vs 5300-10600), push rods +140/+126 mm
(refs ~0: the car sat 140-180 mm up), road "Semislicks" (DY 1.28 vs DTM90 slicks 1.48), road aero with rear LIFT,
nearly open coast diff (0.02), 1800 Nm brakes, 55 deg steering lock, live axle. Setup Coach: 35-90 oversteer snaps per
100 corners, every session. v20 keeps the body, engine (power_dtm.lut, ~465 hp) and gearbox and replaces the chassis:

* rear: double wishbone (Nik's pick) - the Sunbeam v7 geometry, kinematically checked (camber -0.82 deg @ +40 mm,
  bump steer within 0.035 deg over +-60 mm); AC measures pivots inboard from the wheel centre, so it carries over
* springs/dampers/bars/packers at Merc 190 DTM levels scaled to the Escort's corner weights (ride ~2.9/3.0 Hz)
* Kunos "Slicks DTM90s" (S/M/H, default M as on the 190) resized to the Escort's 13" wheels, rear a touch wider
* the 190's splitter + wing curves (ground-effect splitter), span scaled to the Escort, adjustable in setup
* diff 60/35 % + 40 Nm preload, 2500 Nm brakes with a cockpit bias knob, 30 deg steering lock, yaw inertia +18 %
* ride height: ~25 mm below the ORIGINAL mod's stance (rods from its 0.060/0.099, corrected for the stiffer springs)
"""
import re
import shutil
from pathlib import Path

VERSION = "v25"
CAR_ID = "ford_escort_mk2_tuned"
PROJECT = Path(__file__).resolve().parent.parent
BASE = PROJECT / "decoded" / "data_acd"             # v19 as installed: starting point for everything model-tied
MERC = PROJECT / "ref" / "ks_mercedes_190_evo2"     # Kunos 190E Evo II DTM: tyre model, aero curves
OUT = PROJECT / "staging" / CAR_ID / "data"

INERTIA = "1.55,1.25,3.90"          # (the Kunos Mk1's own box is 1.40,1.50,4.30; 1.60,1.35,3.83 is the Sunbeam's); v19 1.40,1.05,3.6
STEER_LOCK = 390                    # / STEER_RATIO 13 = 30 deg at the wheel (v19 720 = 55 deg; refs 14-32)

ARB = {"FRONT": 45000, "REAR": 15000}   # 190 DTM 44000/14400; front roll stiffness share 58 % vs 55 % weight
FRONT = {"SPRING_RATE": 80000, "ROD_LENGTH": 0.012, "PACKER_RANGE": 0.085, "BUMP_STOP_RATE": 120000,
         "DAMP_BUMP": 7500, "DAMP_FAST_BUMP": 2500, "DAMP_FAST_BUMPTHRESHOLD": 0.060,
         "DAMP_REBOUND": 9500, "DAMP_FAST_REBOUND": 5000, "DAMP_FAST_REBOUNDTHRESHOLD": 0.090,
         "STATIC_CAMBER": -3.5, "TOE_OUT": 0.0002}
REAR = {"SPRING_RATE": 70000, "ROD_LENGTH": 0.055, "PACKER_RANGE": 0.065, "BUMP_STOP_RATE": 120000,
        "DAMP_BUMP": 6000, "DAMP_FAST_BUMP": 2500, "DAMP_FAST_BUMPTHRESHOLD": 0.080,
        "DAMP_REBOUND": 8500, "DAMP_FAST_REBOUND": 4000, "DAMP_FAST_REBOUNDTHRESHOLD": 0.110,
        "STATIC_CAMBER": -2.5, "TOE_OUT": -0.0004, "HUB_MASS": 45}
# Sunbeam v7 rear (talbot_sunbeam_lotus/tools/build_car.py REAR_DWB): x inboard from wheel centre, y up, z forward
REAR_DWB = {
    "WBCAR_TOP_FRONT": (0.400, 0.130, 0.150), "WBCAR_TOP_REAR": (0.400, 0.130, -0.100),
    "WBCAR_BOTTOM_FRONT": (0.400, -0.090, 0.220), "WBCAR_BOTTOM_REAR": (0.400, -0.105, -0.150),
    "WBTYRE_TOP": (0.075, 0.140, 0.000), "WBTYRE_BOTTOM": (0.050, -0.120, 0.000),
    "WBCAR_STEER": (0.360, 0.060, 0.130), "WBTYRE_STEER": (0.050, 0.060, 0.130),
}
TYRE = {"RADIUS": 0.268, "RIM_RADIUS": 0.1778, "WIDTH_FRONT": 0.245, "WIDTH_REAR": 0.255}
TYRE_SRC_RADIUS = 0.3225            # the 190's DTM90 tyre; angular inertia scaled by (r/r0)^2
DIFF = {"POWER": 0.60, "COAST": 0.35, "PRELOAD": 40}
# v22 (Nik: "the brakes are very sharp"): v20 copied the 190's 2500 Nm without allowing for the Escort's smaller tyre
# (r 0.268 vs 0.3225) - the same torque pushed ~20 % harder at the road (~1.8 g, past the tyres -> instant lock-ups).
# 2500 x 0.268/0.3225 = 2078 -> 2100 Nm = the 190 DTM's braking force at the tyre.
BRAKES = {"MAX_TORQUE": 1680, "FRONT_SHARE": 0.70}
# v23 (Nik: "I set the brakes to 80% power and they felt better - make that the default"): 2100 x 0.80 = 1680 Nm, so
# Brake power 100 % (the setup default) is what he liked; the slider now runs 70-100 %.
# v22 (Nik: "lower the bhp to 400"): v19-v21's power_dtm.lut reads 466 bhp in the UI; the whole torque curve x 400/466
# (same shape, peak torque still 6260, peak power ~7600, limiter 8500). With it the drag-limited top speed (default wing
# angles, CdA 0.91) falls from ~290 to ~276 km/h - right where 6th meets the limiter on the existing 3.09 final
# (278 km/h), which 466 bhp was bouncing off - so the gearing stays. Fuel use scaled with the power.
POWER_BHP, POWER_BHP_V21 = 400, 466
POWER_SCALE = POWER_BHP / POWER_BHP_V21
KM_PER_LITER = round(2.5 * POWER_BHP_V21 / POWER_BHP, 2)        # v19-v21: 2.5
UI_SPECS = {"bhp": f"{POWER_BHP} bhp", "torque": f"{round(476 * POWER_SCALE)} Nm", "weight": "1050 kg",
            "topspeed": "~275 km/h", "pwratio": f"{1050 / POWER_BHP:.2f} kg/hp"}
# v21: aero centres where the 3D parts are (tools/blender/build_aero.py), from the CoG: x, y up, z forward.
# CoG in model space = -GRAPHICS_OFFSET = (0, 0.400, 0.140). Splitter blade centre: model y -1.785 fwd, z -0.022;
# wing chord centre: 1.993 back, z 0.905. v20 had the splitter at 0,-0.33,2.00 - about 0.17 m above the ground,
# off the end of height_front_CL.lut (0-0.13 m, so always its last value 0.85); at -0.42 it reads ~0.08 m (CL x1.08)
# like Kunos' DTM cars (-0.37/-0.38). Net: total downforce +12 %, aero balance unchanged (46 % front), and the
# splitter now gains grip as the nose drops (the 190's ground-effect curve working as intended).
FRONT_SPLITTER_POS = "0,-0.42,1.65"
REAR_WING_POS = "0,0.50,-2.13"
# v24 (Nik: "add a stainless steel fuel tank where this box is"): CM draws the physics tank as a 0.76 x 0.38 x 0.19 m box
# (55 l, 4:2:1); its front ran 5 cm into the boot's front wall, so the 3D tank (tools/blender/build_tank.py, model
# centre 0, 1.63, 0.40) and this point moved back together (-1.70 -> -1.77): 41 kg of fuel 7 cm back = ~3 mm on the CoG.
# v25 (Nik: the tank should sit on the floor, not on legs): tank centre down from model z 0.40 to 0.252 -> y -0.148;
# 41 kg of fuel 15 cm lower = CoG ~6 mm lower with a full tank.
FUELTANK_POS = "0,-0.148,-1.77"
# v25 (Nik: "add original Ford Escort wing mirrors ... make sure they reflect as a mirror should in game"): the door
# mirrors' glass meshes (tools/blender/v25.build_mirrors) after the interior mirror, as Kunos' 190 DTM lists C, L, R
MIRRORS = ["overheadconsole_a_SUB4", "AERO_mirror_glass_L", "AERO_mirror_glass_R"]
# v24 (Nik: "the collider files seem out of line with the car"): the floor box's bottom sat at model z 0.03, 3-5 cm above
# the floor pan (z ~0.00), with the air dam/splitter (-0.025) 5 cm below it. Now the floor box runs from just ahead of
# the front axle to the heel board with its bottom on the floor pan, plus a second box under the front overhang down to
# the air dam, as on Kunos' 190 DTM (COLLIDER_1). Model -> physics: up - 0.400, forward - 0.140. The cyan box CM showed
# is the INERTIA box, drawn from the model origin, not a collider; collider.kn5 hugs the body within 3 cm: both unchanged.
COLLIDERS = [   # (centre x, y, z from the CoG; size x, y, z)
    ((0, -0.355, 0.055), (1.52, 0.10, 2.29)),       # floor: model 1.34 ahead .. 0.95 behind the origin, bottom z -0.005
    ((0, -0.380, 1.455), (1.46, 0.10, 0.51)),       # front overhang: 1.85 .. 1.34 ahead, bottom z -0.030 (air dam)
]

# setup.ini: (section, tab, label, min, max, step, show_clicks, x, y, help, default-in-setup-units)
SETUP = [
    ("WING_1", "AERO", "Front splitter", 0, 3, 1, 1, 0.5, 0, "HELP_WING_FRONT", 3),
    ("WING_2", "AERO", "Rear wing", 0, 4, 1, 2, 0.5, 2, "HELP_WING_REAR", 3),
    ("SPRING_RATE_LF", "SUSPENSIONS", "Wheel rate LF", 50, 140, 5, 0, 0, 1, "HELP_LF_WHEELRATE", 80),
    ("SPRING_RATE_RF", "SUSPENSIONS", "Wheel rate RF", 50, 140, 5, 0, 1, 1, "HELP_RF_WHEELRATE", 80),
    ("ROD_LENGTH_LF", "SUSPENSIONS", "Height LF", -300, 500, 10, 2, 0, 2, "HELP_LF_RODLENGTH", 120),
    ("ROD_LENGTH_RF", "SUSPENSIONS", "Height RF", -300, 500, 10, 2, 1, 2, "HELP_RF_RODLENGTH", 120),
    ("ARB_FRONT", "SUSPENSIONS", "ARB Front", 20000, 80000, 5000, 2, 0.5, 3, "HELP_FRONT_ARB", 45000),
    ("SPRING_RATE_LR", "SUSPENSIONS", "Wheel rate LR", 40, 120, 5, 0, 0, 6, "HELP_LR_WHEELRATE", 70),
    ("SPRING_RATE_RR", "SUSPENSIONS", "Wheel rate RR", 40, 120, 5, 0, 1, 6, "HELP_RR_WHEELRATE", 70),
    ("ROD_LENGTH_LR", "SUSPENSIONS", "Height LR", 0, 1200, 10, 2, 0, 7, "HELP_LR_RODLENGTH", 550),
    ("ROD_LENGTH_RR", "SUSPENSIONS", "Height RR", 0, 1200, 10, 2, 1, 7, "HELP_RR_RODLENGTH", 550),
    ("ARB_REAR", "SUSPENSIONS", "ARB Rear", 0, 35000, 2500, 2, 0.5, 8, "HELP_REAR_ARB", 15000),
    ("CAMBER_LF", "ALIGNMENT", "CAMBER_LF", -5.0, -1.0, 1, 0, 0, 0, "HELP_LF_CAMBER", -3.5),
    ("CAMBER_RF", "ALIGNMENT", "CAMBER_RF", -5.0, -1.0, 1, 0, 1, 0, "HELP_RF_CAMBER", -3.5),
    ("TOE_OUT_LF", "ALIGNMENT", "Toe LF", -60, 60, 5, 2, 0, 1, "HELP_LF_TOE", 20),
    ("TOE_OUT_RF", "ALIGNMENT", "Toe RF", -60, 60, 5, 2, 1, 1, "HELP_RF_TOE", 20),
    ("CAMBER_LR", "ALIGNMENT", "CAMBER_LR", -5.0, 0.0, 1, 0, 0, 3, "HELP_LR_CAMBER", -2.5),
    ("CAMBER_RR", "ALIGNMENT", "CAMBER_RR", -5.0, 0.0, 1, 0, 1, 3, "HELP_RR_CAMBER", -2.5),
    # v23 camber review (Setup Coach on v22, DTM90 slick peaks at -2.48 deg): front -3.7 static ran -2.3..-2.65 loaded = on
    # the peak (default -3.0 -> -3.5); rear asked for -3.9..-4.5 and hit the -3.5 limit every Build - the DWB only
    # cancels ~30 % of body roll at the outer rear wheel - so the rear range opens to -5.0 and the default goes -1.5 -> -2.5
    ("BRAKE_POWER_MULT", "GENERIC", "Brake power", 70, 100, 1, 0, 0.5, 1, "HELP_BRAKE_POWER_MULT", 100),
    ("TOE_OUT_LR", "ALIGNMENT", "Toe LR", -100, 40, 5, 2, 0, 4, "HELP_LR_TOE", -40),
    ("TOE_OUT_RR", "ALIGNMENT", "Toe RR", -100, 40, 5, 2, 1, 4, "HELP_RR_TOE", -40),
    ("DIFF_POWER", "DRIVETRAIN", "Diff Power", 10, 90, 5, 0, 0.5, 2, "HELP_DIFF_POWER", 60),
    ("DIFF_PRELOAD", "DRIVETRAIN", "Diff Preload", 10, 150, 10, 0, 0.5, 4, "HELP_DIFF_PRELOAD", 40),
    ("DIFF_COAST", "DRIVETRAIN", "Diff Coast", 10, 90, 5, 0, 0.5, 6, "HELP_DIFF_COAST", 35),
    ("FRONT_BIAS", "GENERIC", "Brake Bias", 55, 80, 1, 0, 0.5, 2, "HELP_BRAKE_BIAS", 70),
]
for _corner, _x, _y0 in (("F", 0, 0), ("F", 1, 0), ("R", 0, 5), ("R", 1, 5)):
    _side = "L" if _x == 0 else "R"
    _d = FRONT if _corner == "F" else REAR
    _rng = ({"DAMP_BUMP": (4000, 12000, 500), "DAMP_FAST_BUMP": (1000, 5000, 250), "DAMP_REBOUND": (5000, 14000, 500),
             "DAMP_FAST_REBOUND": (2000, 8000, 250)} if _corner == "F" else
            {"DAMP_BUMP": (3000, 10000, 500), "DAMP_FAST_BUMP": (1000, 5000, 250), "DAMP_REBOUND": (4000, 13000, 500),
             "DAMP_FAST_REBOUND": (1500, 7000, 250)})
    for _row, (_key, _label, _help) in enumerate((("DAMP_BUMP", "Bump", "BUMP"), ("DAMP_FAST_BUMP", "FST Bump", "FBUMP"),
                                                  ("DAMP_REBOUND", "Rebound", "REBOUND"),
                                                  ("DAMP_FAST_REBOUND", "FST Rebound", "FREBOUND"))):
        _lo, _hi, _st = _rng[_key]
        SETUP.append((f"{_key}_{_side}{_corner}", "DAMPERS", _label, _lo, _hi, _st, 2, _x, _y0 + _row,
                      f"HELP_{_side}{_corner}_DAMPER_{_help}", _d[_key]))


def sections(text):
    """[(name, [lines])] in order; text before the first section is under ''."""
    out, cur = [("", [])], None
    for line in text.splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            out.append((m.group(1), []))
        else:
            out[-1][1].append(line)
    return out


def join(secs):
    lines = list(secs[0][1])
    for name, body in secs[1:]:
        lines += [f"[{name}]", *body]
    return "\n".join(lines).rstrip("\n") + "\n"


def set_keys(path, section, values, add=False):
    """Set KEY=value inside [section]; with add=True, missing keys are appended to the section."""
    secs = sections(path.read_text(encoding="utf-8"))
    hits = [s for s in secs if s[0] == section]
    if not hits:
        raise KeyError(f"{path.name}: no [{section}]")
    body = hits[0][1]
    for k, v in values.items():
        idx = [i for i, l in enumerate(body) if re.match(rf"\s*{re.escape(k)}\s*=", l)]
        if idx:
            body[idx[0]] = f"{k}={v}"
            for i in reversed(idx[1:]):
                del body[i]
        elif add:
            while body and not body[-1].strip():
                body.pop()
            body.append(f"{k}={v}")
            body.append("")
        else:
            raise KeyError(f"{path.name}: [{section}] {k} not found")
    path.write_text(join(secs), encoding="utf-8")


def drop_section(path, section):
    secs = sections(path.read_text(encoding="utf-8"))
    kept = [s for s in secs if s[0] != section]
    if len(kept) == len(secs):
        raise KeyError(f"{path.name}: no [{section}]")
    path.write_text(join(kept), encoding="utf-8")


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def build_tyres():
    src = (MERC / "tyres.ini").read_text(encoding="utf-8")
    secs = sections(src)
    k = (TYRE["RADIUS"] / TYRE_SRC_RADIUS) ** 2
    luts = set()
    for name, body in secs:
        m = re.fullmatch(r"(FRONT|REAR)(_\d+)?", name)
        for i, line in enumerate(body):
            kv = re.match(r"\s*([A-Z0-9_]+)\s*=\s*([^;\s]+)", line)
            if not kv:
                continue
            key, val = kv.groups()
            if val.lower().endswith(".lut"):
                luts.add(val)
            if m:
                if key == "RADIUS":
                    body[i] = f"RADIUS={TYRE['RADIUS']}"
                elif key == "RIM_RADIUS":
                    body[i] = f"RIM_RADIUS={TYRE['RIM_RADIUS']}"
                elif key == "WIDTH":
                    body[i] = f"WIDTH={TYRE['WIDTH_FRONT'] if m.group(1) == 'FRONT' else TYRE['WIDTH_REAR']}"
                elif key == "ANGULAR_INERTIA":
                    body[i] = f"ANGULAR_INERTIA={float(val) * k:.3f}"
    # keep v19's CSP tyre-ray settings (they belong to the car, not the tyre model)
    ext = [s for s in sections((BASE / "tyres.ini").read_text(encoding="utf-8")) if s[0] == "_EXTENSION"]
    head = [i for i, s in enumerate(secs) if s[0] == "HEADER"][0]
    secs[head + 1:head + 1] = ext
    (OUT / "tyres.ini").write_text(join(secs), encoding="utf-8")
    for lut in luts:
        shutil.copy2(MERC / lut, OUT / lut)
    return luts


def build_aero():
    merc = {n: b for n, b in sections((MERC / "aero.ini").read_text(encoding="utf-8"))}
    aero = OUT / "aero.ini"
    copied = set()
    for wing in ("WING_1", "WING_2"):
        mv = {m.group(1): m.group(2).strip() for m in (re.match(r"\s*([A-Z_]+)\s*=\s*([^;]*)", l) for l in merc[wing]) if m}
        vals = {k: mv[k] for k in ("LUT_AOA_CL", "LUT_GH_CL", "CL_GAIN", "LUT_AOA_CD", "LUT_GH_CD", "CD_GAIN", "ANGLE")}
        vals["POSITION"] = FRONT_SPLITTER_POS if wing == "WING_1" else REAR_WING_POS
        set_keys(aero, wing, vals)
        for k in ("LUT_AOA_CL", "LUT_GH_CL", "LUT_AOA_CD", "LUT_GH_CD"):
            if vals[k]:
                shutil.copy2(MERC / vals[k], OUT / vals[k])
                copied.add(vals[k])
    return copied


def build_brakes():
    v19 = {n: b for n, b in sections((BASE / "brakes.ini").read_text(encoding="utf-8"))}
    discs = [l for l in v19["DISCS_GRAPHICS"] if l.strip()]
    text = ("[HEADER]\nVERSION=1\n\n[DATA]\n"
            f"MAX_TORQUE={BRAKES['MAX_TORQUE']}\nFRONT_SHARE={BRAKES['FRONT_SHARE']:.2f}\nHANDBRAKE_TORQUE=1600\n"
            "COCKPIT_ADJUSTABLE=1\nADJUST_STEP=0.5\n\n[DISCS_GRAPHICS]\n" + "\n".join(discs) + "\n")
    (OUT / "brakes.ini").write_text(text, encoding="utf-8")


def build_setup():
    keep = {n: b for n, b in sections((BASE / "setup.ini").read_text(encoding="utf-8"))}
    lines = ["[DISPLAY_METHOD]", "SHOW_CLICKS=1", ""]
    for p in ("PRESSURE_LF", "PRESSURE_RF", "PRESSURE_LR", "PRESSURE_RR", "FINAL_GEAR_RATIO", "FUEL"):
        lines += [f"[{p}]", *[l for l in keep[p] if l.strip() and not l.startswith(("/", ";"))], ""]
    for sec, tab, label, lo, hi, step, sc, x, y, help_, default in SETUP:
        units = round(default * 10) if sec.startswith("CAMBER") else default
        lo_u = round(lo * 10) if sec.startswith("CAMBER") else lo
        assert lo <= default <= hi, (sec, default)
        assert (units - lo_u) % (step if not sec.startswith("CAMBER") else step) == 0, (sec, default, lo, step)
        lines += [f"[{sec}]", f"SHOW_CLICKS={sc}", f"TAB={tab}", f"NAME={label}", f"MIN={fmt(lo)}", f"MAX={fmt(hi)}",
                  f"STEP={step}", f"POS_X={fmt(x)}", f"POS_Y={fmt(y)}", f"HELP={help_}", ""]
    (OUT / "setup.ini").write_text("\n".join(lines), encoding="utf-8")


def build_power():
    """v22: the torque curve x POWER_SCALE (same shape) and fuel use to match."""
    eng = (OUT / "engine.ini").read_text(encoding="utf-8")
    curve = re.search(r"^\s*POWER_CURVE\s*=\s*([^\s;]+)", eng, re.M).group(1)
    src = (BASE / curve).read_text(encoding="utf-8")
    pts = re.findall(r"^\s*([\d.]+)\s*\|\s*([-\d.]+)", src, re.M)
    assert len(pts) > 5, curve
    (OUT / curve).write_text("".join(f"{r}|{float(t) * POWER_SCALE:.1f}\n" for r, t in pts), encoding="utf-8")
    set_keys(OUT / "fuel_cons.ini", "FUEL_EVAL", {"KM_PER_LITER": f"{KM_PER_LITER:.2f}"})
    set_keys(OUT / "engine.ini", "HEADER", {"POWER_CURVE": f"{curve}\t\t\t; wheel torque curve - v22: v19's x {POWER_BHP}/{POWER_BHP_V21} = {POWER_BHP} bhp"})


def check_defaults():
    """Every setup default must equal the physics value it adjusts (so a fresh setup = the designed car)."""
    rod = lambda m: round(m * 10000)
    want = {"SPRING_RATE_LF": FRONT["SPRING_RATE"] // 1000, "SPRING_RATE_LR": REAR["SPRING_RATE"] // 1000,
            "ROD_LENGTH_LF": rod(FRONT["ROD_LENGTH"]), "ROD_LENGTH_LR": rod(REAR["ROD_LENGTH"]),
            "ARB_FRONT": ARB["FRONT"], "ARB_REAR": ARB["REAR"], "CAMBER_LF": FRONT["STATIC_CAMBER"],
            "CAMBER_LR": REAR["STATIC_CAMBER"], "TOE_OUT_LF": round(FRONT["TOE_OUT"] * 1e5),
            "TOE_OUT_LR": round(REAR["TOE_OUT"] * 1e5), "DIFF_POWER": round(DIFF["POWER"] * 100),
            "DIFF_COAST": round(DIFF["COAST"] * 100), "DIFF_PRELOAD": DIFF["PRELOAD"],
            "FRONT_BIAS": round(BRAKES["FRONT_SHARE"] * 100)}
    for k in ("DAMP_BUMP", "DAMP_FAST_BUMP", "DAMP_REBOUND", "DAMP_FAST_REBOUND"):
        want[f"{k}_LF"], want[f"{k}_LR"] = FRONT[k], REAR[k]
    table = {s[0]: s[-1] for s in SETUP}
    for k, v in want.items():
        assert table[k] == v, (k, table[k], v)


def build():
    if OUT.parent.exists():
        shutil.rmtree(OUT.parent)
    shutil.copytree(BASE, OUT)
    for p in OUT.glob("__cm_*"):
        p.unlink()
    # AC writes this node list itself; v19's copy predates the aero kit (a stale one logs a KEY_NOT_FOUND per node)
    (OUT / "proview_nodes.ini").unlink(missing_ok=True)

    car = OUT / "car.ini"
    set_keys(car, "BASIC", {"INERTIA": INERTIA})
    set_keys(car, "CONTROLS", {"STEER_LOCK": STEER_LOCK})
    set_keys(car, "INFO", {"SCREEN_NAME": f"Ford Escort Mk2 DTM {VERSION}"}, add=True)
    set_keys(car, "FUELTANK", {"POSITION": FUELTANK_POS})
    (OUT / "mirrors.ini").write_text("".join(f"[MIRROR_{i}]\nNAME={n}\n\n" for i, n in enumerate(MIRRORS)), encoding="utf-8")
    (OUT / "colliders.ini").write_text("".join(
        f"[COLLIDER_{i}]\nCENTRE={','.join(f'{v:g}' for v in c)}\nSIZE={','.join(f'{v:g}' for v in s)}\nGROUND_ENABLE=1\n\n"
        for i, (c, s) in enumerate(COLLIDERS)), encoding="utf-8")

    sus = OUT / "suspensions.ini"
    set_keys(sus, "ARB", ARB)
    set_keys(sus, "FRONT", {k: fmt(v) for k, v in FRONT.items()})
    rear = {"TYPE": "DWB", **{k: fmt(v) for k, v in REAR.items()},
            **{k: f"{x:.4f}, {y:.4f}, {z:.4f}" for k, (x, y, z) in REAR_DWB.items()}}
    set_keys(sus, "REAR", rear)
    drop_section(sus, "AXLE")

    tyre_luts = build_tyres()
    aero_luts = build_aero()
    build_brakes()
    set_keys(OUT / "drivetrain.ini", "DIFFERENTIAL", DIFF)
    build_power()
    check_defaults()
    build_setup()

    # every file the physics points at must be there
    for f in ("tyres.ini", "aero.ini", "engine.ini", "brakes.ini", "drivetrain.ini", "suspensions.ini"):
        text = (OUT / f).read_text(encoding="utf-8")
        for ref in re.findall(r"=\s*([\w.-]+\.(?:lut|rto))", text):
            if f == "engine.ini" and ref == "coast.lut" and "FROM_COAST_REF" in text:
                continue                                    # Kunos-standard unused entry (coast from COAST_REF)
            assert (OUT / ref).exists(), f"{f} points at missing {ref}"
    print(f"built {VERSION} -> {OUT}\n  tyre luts {sorted(tyre_luts)}\n  aero luts {sorted(aero_luts)}")


if __name__ == "__main__":
    build()
