"""Assemble the AC car folder for the 1981 works Talbot Sunbeam Lotus (v0.1).

Physics start from Kunos' ks_ford_escort_mk1 (a race-prepared early-70s
Escort: strut front / live axle rear, 5-speed box close to the Sunbeam's
homologated ratios), decrypted to refs/donor_data, then reworked with the
Sunbeam's own numbers - FIA Group 2 homologation 1700 where it has them,
clearly-marked placeholders where it doesn't. The 3D model (.kn5) and
collider.kn5 are written separately by ac_kn5_export.py from Blender.

Re-running is safe: it rebuilds data/, ui/, sfx/, skins/ and shadows, and
never touches the .kn5 files.
"""
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

CAR_ID = "talbot_sunbeam_lotus_81_works"
AC = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa")
DONOR_ID = "ks_ford_escort_mk1"
PROJECT = Path(__file__).resolve().parent.parent
DONOR_DATA = PROJECT / "refs" / "donor_data" / DONOR_ID
CAR = AC / "content" / "cars" / CAR_ID

# --- numbers (FIA = homologation 1700; BP = blueprint; PH = placeholder to refine) ---
WHEELBASE = 2.413                     # FIA
TRACK_F = TRACK_R = 1.466             # BP (free under Group 2, not on the form)
TYRE_R, RIM_R = 0.300, 0.2032         # PH radius; 15" rims (FIA p30) -> AC wants nominal +1"
CG_LOCATION = 0.57                    # PH front weight fraction (stock road car mod uses 0.60)
BASEY_F, BASEY_R = -0.250, -0.280     # donor suspension geometry, kept
TOTALMASS = 1010                      # PH kg with driver, no fuel
# FIA p5 close-ratio box: 38/16x30/31, 39/21x30/31, 35/25x30/31, 33/28x30/31, direct; R 32/11x30/31
# (2nd was wrongly 1.60 until 2026-09-27)
GEARS = {"GEAR_R": -2.82, "GEAR_1": 2.30, "GEAR_2": 1.80, "GEAR_3": 1.36, "GEAR_4": 1.14, "GEAR_5": 1.00}
# Final drives for the setup screen's final.rto (pinion, crown, ratio). v3 (2026-09-28): the works cars' heavy-duty
# Salisbury 4HA axle ratios (FIA amendment 1/IV, p14: 6.17 ... 3.77) plus the three tallest standard-axle ratios
# (FIA p5/p19: 3.89, 3.70, 3.54) that Nick's circuit setups use. Same 10 entries as v1/v2, and indexes 5 (4.10->4.09)
# and 9 (3.54) keep their ratio, so his saved setups (they store the INDEX) barely move - only index 7 (3.89 -> 3.77).
FINAL_OPTIONS = [(6, 37, 6.17), (8, 43, 5.38), (9, 44, 4.89), (11, 50, 4.55), (11, 47, 4.27), (11, 45, 4.09),
                 (9, 35, 3.89), (13, 49, 3.77), (10, 37, 3.70), (11, 39, 3.54)]
FINAL = 4.09                          # 45/11 on the Salisbury axle
MAX_FUEL = 90                         # FIA p17: FT3 90 L
LIMITER = 9000                        # works engines "red-lined at 9,250rpm" (DirtFish, works mechanic Jim Little); was 7800
# Steering: works "high ratio" rack 11.3:1, 2.3 turns lock to lock (tech-racingcars) - was the Escort's 16.0:1 / 450 deg.
# Wheel lock = STEER_LOCK / STEER_RATIO: 28.1 -> 36.6 deg. LINEAR_STEER_ROD_RATIO (the geometry calibration) unchanged.
STEER_RATIO, STEER_LOCK = 11.3, 414
# steering force: 2.30 was Nick's feel on the 16:1 rack (Escort 2.752 too heavy, 2026-09-27); a quicker rack
# raises the rim force by 16/11.3, so scaled down to keep the same weight
FFMULT = round(2.30 * STEER_RATIO / 16.0, 2)
# plate LSD (Salisbury 4HA works axle) - was the Escort's 25/25/0. Saved setups keep their own POWER/COAST values;
# the preload applies to every setup.
DIFF = {"POWER": 0.45, "COAST": 0.30, "PRELOAD": 40}
# brakes: twin master cylinders + bias box with a cockpit knob (FIA p22, p39) -> adjustable from the car; hardware
# alone ~59 % front. MAX_TORQUE stays the Escort's 1800 Nm.
BRAKE_FRONT_SHARE, BRAKE_COCKPIT_ADJUSTABLE = 0.62, 1
# body box for AC's inertia: 1405 mm tall hatchback (tech-racingcars) - was 1.35
INERTIA = "1.60,1.40,3.83"
AI_SHIFT_UP, AI_SHIFT_DOWN = 8600, 6000   # (Escort's 9350/6100: above our limiter)
# Crank torque (Nm): works Group 2 figures 245 hp @ 7000, 256 Nm @ 6000 (tech-racingcars; Bonhams/Silodrome say
# 240-250 bhp). Low/high rpm shape is ours. AC's power.lut is torque at the wheels (the Escort's reads ~200 bhp
# against its "260+bhp" UI figure), so the lut gets 85% of crank.
DRIVELINE = 0.85
# v3: above 7000 the power now holds to ~8000 and tails off to the 9000 limiter (works engines revved to 9,250 but
# "didn't like it"); v1/v2 fell away from 7000 (7500: 232, 8000: 200, 8500: 150) for the old 7800 limiter.
REAL_CRANK_TORQUE = [(0, 100), (1000, 130), (2000, 160), (3000, 190), (4000, 218), (5000, 240), (5500, 250),
                     (6000, 256), (6500, 255), (7000, 249), (7500, 234), (8000, 216), (8500, 190), (9000, 160),
                     (9500, 115)]
# +75 bhp over the real 245 (Nick, 2026-09-27): whole curve scaled, so it keeps the real car's shape
REAL_BHP, EXTRA_BHP = 245, 75
CRANK_TORQUE = [(r, round(t * (REAL_BHP + EXTRA_BHP) / REAL_BHP, 1)) for r, t in REAL_CRANK_TORQUE]
POWER_LUT = [(r, round(t * DRIVELINE, 1)) for r, t in CRANK_TORQUE]

# Rear axle location (AC [AXLE] joints: metres from the axle centre, x = car's left, y = up, z = forward; each link =
# car point + axle point). The Escort base had 2 lower + 2 PARALLEL upper trailing links + a Panhard rod 20 mm above the
# axle centre (rear roll centre ~0.315 m off the ground). The Sunbeam (FIA 1700 photo E; tech-racingcars "2 long
# radius arms and two 45o upper locating links"; Avenger-derived four-link) has no Panhard: the two upper links run
# from the top of the diff housing forward and outward at 45 deg in plan, so they locate the axle sideways too and the
# rear roll centre rises to their height (~0.415 m). Lower arms and the side view (both link pairs level, no
# anti-squat) are the Escort's, so only the lateral location / roll centre changes - v2, 2026-09-28, for Nick to test.
# (Backup of the Escort version: car talbot_sunbeam_lotus_81_works_v1, git tag v1-escort-chassis.)
REAR_LOWER = ((0.38735, -0.105, 0.481), (0.4005, -0.105, 0.0))     # Escort's, both sides (x mirrored)
REAR_UPPER = ((0.360, 0.120, 0.280), (0.110, 0.120, 0.030))        # car end, axle end (left); 45 deg, 0.354 m
AXLE_SECTION = [
    "LINK_COUNT=4",
    *[f"J{j}_{end}={s * p[0]:.5f},{p[1]:.5f},{p[2]:.5f}"
      for j, (s, pair) in enumerate(((1, REAR_LOWER), (-1, REAR_LOWER), (1, REAR_UPPER), (-1, REAR_UPPER)))
      for end, p in (("CAR", pair[0]), ("AXLE", pair[1]))],
    "TORQUE_REACTION=-0.5",
    "ATTACH_REL_POS=0.68",
    "LEAF_SPRING_LAT_K=0",
]

# model origin = ground level midway between the axles; physics origin = CG
cg_h = TYRE_R + CG_LOCATION * -BASEY_F + (1 - CG_LOCATION) * -BASEY_R
cg_z = WHEELBASE / 2 - (1 - CG_LOCATION) * WHEELBASE
GRAPHICS_OFFSET = f"0,{-cg_h:.3f},{-cg_z:.3f}"


def set_ini(path, section, key, value, pattern=False):
    """Replace KEY=... inside [section] (section may be a regex), keeping everything else."""
    lines = path.read_text(encoding="utf-8").splitlines()
    cur, hits = None, 0
    for i, line in enumerate(lines):
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            cur = m.group(1)
            continue
        in_sec = (re.fullmatch(section, cur or "") if pattern else cur == section)
        if in_sec and re.match(rf"\s*{re.escape(key)}\s*=", line):
            lines[i] = f"{key}={value}"
            hits += 1
    if not hits:
        raise KeyError(f"{path.name}: [{section}] {key} not found")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Damper adjustment (setup.ini). Values are N s/m like suspensions.ini; every MIN and default is a whole multiple of
# STEP so the car's default lands on a click whichever way AC counts them. Fast dampers moved <2 % to sit on a click.
DAMPER_DEFAULTS = {"FRONT": {"DAMP_BUMP": 2500, "DAMP_FAST_BUMP": 1400, "DAMP_REBOUND": 4000, "DAMP_FAST_REBOUND": 2100},
                   "REAR":  {"DAMP_BUMP": 1300, "DAMP_FAST_BUMP": 800,  "DAMP_REBOUND": 2700, "DAMP_FAST_REBOUND": 1200}}
# (setup name, help key, MIN, MAX, STEP) per axle, in on-screen order
# v6: maxima raised ~45 % for stiffer spring choices; MIN/STEP unchanged, so saved setups (clicks) keep their values
DAMPER_RANGES = {"FRONT": [("DAMP_BUMP", "Bump", "BUMP", 1500, 6500, 250), ("DAMP_FAST_BUMP", "FST Bump", "FBUMP", 800, 3200, 100),
                           ("DAMP_REBOUND", "Rebound", "REBOUND", 2500, 9500, 250), ("DAMP_FAST_REBOUND", "FST Rebound", "FREBOUND", 1300, 3900, 100)],
                 "REAR":  [("DAMP_BUMP", "Bump", "BUMP", 700, 3700, 100), ("DAMP_FAST_BUMP", "FST Bump", "FBUMP", 400, 2200, 50),
                           ("DAMP_REBOUND", "Rebound", "REBOUND", 1500, 6600, 150), ("DAMP_FAST_REBOUND", "FST Rebound", "FREBOUND", 600, 2800, 100)]}


def add_dampers(data):
    """Set the damper defaults in suspensions.ini and append a DAMPERS tab (4 dampers x 4 corners) to setup.ini."""
    sus, setup = data / "suspensions.ini", data / "setup.ini"
    for axle, vals in DAMPER_DEFAULTS.items():
        for k, v in vals.items():
            set_ini(sus, axle, k, str(v))
    text = setup.read_text(encoding="utf-8")
    assert "DAMP_BUMP" not in text, "setup.ini already has dampers"
    out = ["", "/////////////////////////////////////////////////////", ";DAMPERS", "/////////////////////////////////////////////////////", ""]
    for axle, y0 in (("FRONT", 0), ("REAR", 5)):
        for side, x in (("L", 0), ("R", 1)):
            corner = f"{side}{axle[0]}"
            for row, (key, name, help_, lo, hi, step) in enumerate(DAMPER_RANGES[axle]):
                assert lo % step == 0 and DAMPER_DEFAULTS[axle][key] % step == 0 and lo <= DAMPER_DEFAULTS[axle][key] <= hi
                out += [f"[{key}_{corner}]", "SHOW_CLICKS=2", "TAB=DAMPERS", f"NAME={name}", f"MIN={lo}", f"MAX={hi}", f"STEP={step}",
                        f"POS_X={x}", f"POS_Y={y0 + row}", f"HELP=HELP_{corner}_DAMPER_{help_}", ""]
    setup.write_text(text.rstrip("\n") + "\n" + "\n".join(out), encoding="utf-8")


# v5 (2026-09-29): springs for the Sunbeam's own weight. v1-v4 kept the Kunos Escort Mk1's 38/34 N/mm, sized for an
# 885 kg car with 55 % on the front; ours is 1010 kg with 57 %, so it sat about half way into its travel at rest and ran
# into the packers every lap (Setup Coach, Nurburgring GP: median lap 110-112 % F / 103-106 % R of PACKER_RANGE).
# Scaled to the corner weights: 38 x 575.7/486.8 = 45 F, 34 x 434.3/398.3 = 37 R; Setup Coach's own target from Nik's
# laps 45-46 / 38-39; Nik drove 46/40 there on 29 Sep ("a lot of fun", packer hits gone) - that is the default now.
SPRING_RATES = {"FRONT": 46000, "REAR": 40000}                 # N/m wheel rate
# setup ranges in N/mm - saved setups store springs as values, so widening/re-stepping changes no saved setup
SPRING_SETUP = {"F": (20, 90, 2), "R": (16, 80, 2)}   # v6: wider (Nik); v5 was 30-60 / 20-50
# stiffer springs lift the car (static load x (1/k_old - 1/k_new): ~11 mm F, ~8 mm R), so the push rods come down to
# keep v4's stance (and the graphics fit). setup.ini heights are clicks in saved setups (units 0.1 mm, F step 1 mm,
# R step 10 mm) - MIN/STEP stay, so saved setups keep their heights; the new defaults must sit on those grids.
ROD_LENGTHS = {"FRONT": 0.029, "REAR": 0.070}


def ini_value(path, section, key):
    cur = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            cur = m.group(1)
        elif cur == section and re.match(rf"\s*{re.escape(key)}\s*=", line):
            return line.split("=", 1)[1].split(";")[0].strip()
    raise KeyError(f"{path.name}: [{section}] {key} not found")


def apply_springs(data):
    """v5 spring rates + ride-height rods in suspensions.ini, spring ranges in setup.ini."""
    sus, setup = data / "suspensions.ini", data / "setup.ini"
    for axle, k in SPRING_RATES.items():
        set_ini(sus, axle, "SPRING_RATE", str(k))
        set_ini(sus, axle, "ROD_LENGTH", f"{ROD_LENGTHS[axle]:.3f}")
    for end, (lo, hi, step) in SPRING_SETUP.items():
        axle = "FRONT" if end == "F" else "REAR"
        k = SPRING_RATES[axle] // 1000
        assert lo <= k <= hi and (k - lo) % step == 0, (end, k)
        units = round(ROD_LENGTHS[axle] * 10000)                   # setup.ini ROD_LENGTH units are 0.1 mm
        for side in "LR":
            sec = f"SPRING_RATE_{side}{end}"
            for key, v in (("MIN", lo), ("MAX", hi), ("STEP", step)):
                set_ini(setup, sec, key, str(v))
            rod = f"ROD_LENGTH_{side}{end}"
            rmin, rmax, rstep = (int(ini_value(setup, rod, key)) for key in ("MIN", "MAX", "STEP"))
            assert rmin <= units <= rmax and (units - rmin) % rstep == 0, (rod, units)


# v6 (2026-09-30): adjustable anti-roll bars and diff preload. The real car had a front bar (it doubles as the front
# tension strut) and works-spec rear axles carried a 1/2 inch rose-jointed rear bar (ex-works listings); Group 2 left
# bar sizes free. Defaults stay as driven since v1 (front 12500, rear 0 = bar off): a 1/2 inch bar on the axle is
# ~6000 N/m (2GJ/(L r^2), L ~1 m, arm ~0.2 m, x motion ratio^2 ~0.64) = click 4 of the rear range. Kunos' live-axle
# AE86 runs 4200-8400.
ARB_DEFAULTS = {"FRONT": 12500, "REAR": 0}                             # N/m
ARB_SETUP = {"FRONT": (5000, 40000, 2500), "REAR": (0, 12000, 1500)}    # new items (clicks in saved setups)
DIFF_PRELOAD_SETUP = (10, 200, 10)                                     # Nm, a value in saved setups; default DIFF["PRELOAD"]


def add_setup_v6(data):
    """ARB_FRONT / ARB_REAR on the SUSPENSIONS tab, DIFF_PRELOAD on DRIVETRAIN."""
    sus, setup, dt = data / "suspensions.ini", data / "setup.ini", data / "drivetrain.ini"
    text = setup.read_text(encoding="utf-8")
    assert "[ARB_FRONT]" not in text and "[DIFF_PRELOAD]" not in text
    out = [""]
    for end, y, help_ in (("FRONT", 3, "HELP_FRONT_ARB"), ("REAR", 8, "HELP_REAR_ARB")):
        lo, hi, step = ARB_SETUP[end]
        k = ARB_DEFAULTS[end]
        assert lo <= k <= hi and (k - lo) % step == 0 and (hi - lo) % step == 0, (end, k)
        set_ini(sus, "ARB", end, str(k))
        out += [f"[ARB_{end}]", "SHOW_CLICKS=2", "TAB=SUSPENSIONS", f"NAME=ARB {end.title()}", f"MIN={lo}", f"MAX={hi}",
                f"STEP={step}", "POS_X=0.5", f"POS_Y={y}", f"HELP={help_}", ""]
    lo, hi, step = DIFF_PRELOAD_SETUP
    p = int(float(ini_value(dt, "DIFFERENTIAL", "PRELOAD")))
    assert lo <= p <= hi and (p - lo) % step == 0, p
    out += ["[DIFF_PRELOAD]", "SHOW_CLICKS=0", "TAB=DRIVETRAIN", "NAME=Diff Preload", f"MIN={lo}", f"MAX={hi}",
            f"STEP={step}", "POS_X=0.5", "POS_Y=4", "HELP=HELP_DIFF_PRELOAD", ""]
    setup.write_text(text.rstrip("\n") + "\n" + "\n".join(out), encoding="utf-8")


# v7 (2026-09-30): a double-wishbone rear - NOT historical (the works car kept its four-link live axle, v2-v6; Nik: "or
# double wishbone (yes!)"). AC measures every pivot inboard from the wheel centre (x), up from it (y) and forward (z):
# Kunos' Lotus Exos only makes sense that way, and it gives our front strut its real ~13 deg kingpin angle.
# Checked with a kinematic sweep (scratch dwb_kinematics.py): camber -0.40/-0.82/-1.25 deg at +20/40/60 mm bump,
# +0.39/+0.76/+1.13 in droop; bump steer within +-0.035 deg over +-60 mm, slight toe-in in droop (a leading toe link
# just above the hub - found by search, the first trailing-link try toed out 0.25 deg per 20 mm of bump = roll
# oversteer); lower arm tilted ~2 deg for a little anti-squat.
REAR_TYPE = "DWB"                                   # v7 (v2-v6: "AXLE", the real four-link live axle)
REAR_DWB = {
    "WBCAR_TOP_FRONT": (0.400, 0.130, 0.150), "WBCAR_TOP_REAR": (0.400, 0.130, -0.100),
    "WBCAR_BOTTOM_FRONT": (0.400, -0.090, 0.220), "WBCAR_BOTTOM_REAR": (0.400, -0.105, -0.150),
    "WBTYRE_TOP": (0.075, 0.140, 0.000), "WBTYRE_BOTTOM": (0.050, -0.120, 0.000),
    "WBCAR_STEER": (0.360, 0.060, 0.130), "WBTYRE_STEER": (0.050, 0.060, 0.130),
}
REAR_DWB_HUB_MASS = 40                              # kg a corner: wheel, upright, brake, half a drive shaft
REAR_STATIC_CAMBER, REAR_TOE_OUT = -1.0, -0.00040   # a little toe-in, like Kunos' E30 (-0.00045)
# rear alignment items: camber in degrees (saved as 0.1 deg), toe in AC's 1e-5 units (saved as clicks)
REAR_ALIGN_SETUP = {"CAMBER": (-3.0, 0.0, 1), "TOE_OUT": (-100, 40, 5)}


def remove_section(path, section):
    out, skip, hit = [], False, False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            skip = m.group(1) == section
            hit = hit or skip
        if not skip:
            out.append(line)
    if not hit:
        raise KeyError(f"{path.name}: no [{section}]")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def apply_rear_dwb(data):
    """v7: [REAR] becomes a double wishbone, [AXLE] goes, rear camber + toe join the ALIGNMENT tab."""
    sus, setup = data / "suspensions.ini", data / "setup.ini"
    set_ini(sus, "REAR", "TYPE", "DWB")
    for key, (x, y, z) in REAR_DWB.items():
        set_ini(sus, "REAR", key, f"{x:.4f}, {y:.4f}, {z:.4f}")
    set_ini(sus, "REAR", "HUB_MASS", str(REAR_DWB_HUB_MASS))
    set_ini(sus, "REAR", "STATIC_CAMBER", f"{REAR_STATIC_CAMBER:.1f}")
    set_ini(sus, "REAR", "TOE_OUT", f"{REAR_TOE_OUT:.5f}")
    remove_section(sus, "AXLE")
    text = setup.read_text(encoding="utf-8")
    assert "[CAMBER_LR]" not in text and "[TOE_OUT_LR]" not in text
    (clo, chi, cstep), (tlo, thi, tstep) = REAR_ALIGN_SETUP["CAMBER"], REAR_ALIGN_SETUP["TOE_OUT"]
    toe = round(REAR_TOE_OUT * 1e5)
    assert clo <= REAR_STATIC_CAMBER <= chi and tlo <= toe <= thi and (toe - tlo) % tstep == 0
    out = [""]
    for side, x in (("L", 0), ("R", 1)):
        out += [f"[CAMBER_{side}R]", "SHOW_CLICKS=0", "TAB=ALIGNMENT", f"NAME=CAMBER_{side}R", f"MIN={clo:g}",
                f"MAX={chi:g}", f"STEP={cstep}", f"POS_X={x}", "POS_Y=3", f"HELP=HELP_{side}R_CAMBER", "",
                f"[TOE_OUT_{side}R]", "SHOW_CLICKS=2", "TAB=ALIGNMENT", f"NAME=Toe {side}R", f"MIN={tlo}", f"MAX={thi}",
                f"STEP={tstep}", f"POS_X={x}", "POS_Y=4", f"HELP=HELP_{side}R_TOE", ""]
    setup.write_text(text.rstrip("\n") + "\n" + "\n".join(out), encoding="utf-8")


def set_section(path, section, body):
    """Replace everything inside [section] with body (list of lines)."""
    out, skip = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            skip = False
            if m.group(1) == section:
                out += [line, *body, ""]
                skip = True
                continue
        if not skip:
            out.append(line)
    if not any(re.match(rf"\s*\[{re.escape(section)}\]", l) for l in out):
        raise KeyError(f"{path.name}: no [{section}]")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def build_data():
    data = CAR / "data"
    if data.exists():
        shutil.rmtree(data)
    shutil.copytree(DONOR_DATA, data)
    for junk in ("analog_instruments.ini_", "engine.ini.bak", "suspensions_anti.ini", "suspensions_org.ini"):
        (data / junk).unlink(missing_ok=True)

    car = data / "car.ini"
    set_ini(car, "INFO", "SCREEN_NAME", "Talbot Sunbeam Lotus 1981 Works")
    set_ini(car, "BASIC", "GRAPHICS_OFFSET", GRAPHICS_OFFSET)
    set_ini(car, "BASIC", "GRAPHICS_PITCH_ROTATION", "0")
    set_ini(car, "BASIC", "TOTALMASS", str(TOTALMASS))
    set_ini(car, "BASIC", "INERTIA", INERTIA)
    set_ini(car, "FUEL", "MAX_FUEL", str(MAX_FUEL))
    set_ini(car, "FUEL", "FUEL", "40")
    set_ini(car, "CONTROLS", "FFMULT", f"{FFMULT:.3f}")
    set_ini(car, "CONTROLS", "STEER_RATIO", f"{STEER_RATIO:.1f}")
    set_ini(car, "CONTROLS", "STEER_LOCK", str(STEER_LOCK))

    br = data / "brakes.ini"
    set_ini(br, "DATA", "FRONT_SHARE", f"{BRAKE_FRONT_SHARE:.3f}")
    set_ini(br, "DATA", "COCKPIT_ADJUSTABLE", str(BRAKE_COCKPIT_ADJUSTABLE))

    sus = data / "suspensions.ini"
    set_ini(sus, "BASIC", "WHEELBASE", f"{WHEELBASE:.3f}")
    set_ini(sus, "BASIC", "CG_LOCATION", f"{CG_LOCATION:.2f}")
    set_ini(sus, "FRONT", "TRACK", f"{TRACK_F:.3f}")
    set_ini(sus, "REAR", "TRACK", f"{TRACK_R:.3f}")
    set_section(sus, "AXLE", AXLE_SECTION)

    tyres = data / "tyres.ini"
    set_ini(tyres, r"(FRONT|REAR)(_\d+)?", "RADIUS", f"{TYRE_R:.3f}", pattern=True)
    set_ini(tyres, r"(FRONT|REAR)(_\d+)?", "RIM_RADIUS", f"{RIM_R:.4f}", pattern=True)

    dt = data / "drivetrain.ini"
    for k, v in GEARS.items():
        set_ini(dt, "GEARS", k, f"{v:.3f}")
    set_ini(dt, "GEARS", "FINAL", f"{FINAL:.3f}")
    for k, v in DIFF.items():
        set_ini(dt, "DIFFERENTIAL", k, str(v))
    set_ini(dt, "AUTO_SHIFTER", "UP", str(AI_SHIFT_UP))
    set_ini(dt, "AUTO_SHIFTER", "DOWN", str(AI_SHIFT_DOWN))
    set_ini(data / "ai.ini", "GEARS", "UP", str(AI_SHIFT_UP))
    set_ini(data / "ai.ini", "GEARS", "DOWN", str(AI_SHIFT_DOWN))
    (data / "final.rto").write_text("\n".join(f"{p}//{c}|{r}" for p, c, r in FINAL_OPTIONS), encoding="utf-8")

    eng = data / "engine.ini"
    set_ini(eng, "ENGINE_DATA", "LIMITER", str(LIMITER))
    set_ini(eng, "ENGINE_DATA", "MINIMUM", "1000")
    set_ini(eng, "DAMAGE", "RPM_THRESHOLD", str(LIMITER + 300))
    (data / "power.lut").write_text("\n".join(f"{r}|{t}" for r, t in POWER_LUT) + "\n", encoding="utf-8")

    set_ini(data / "driver3d.ini", "SHIFT_ANIMATION", "PRELOAD_RPM", str(LIMITER - 300))

    (data / "lods.ini").write_text(
        f"[COCKPIT_HR]\nDISTANCE_SWITCH=7\n\n[LOD_0]\nFILE={CAR_ID}.kn5\nIN=0\nOUT=2000\n", encoding="utf-8")
    # light meshes by kn5 node name (build_details.py objects; a two-material object exports as NAME_SUB0/1)
    (data / "lights.ini").write_text(
        "[HEADER]\nVERSION=2\n\n"
        "[LIGHT_0]\nNAME=HEADLIGHT\nCOLOR=60,60,55\n\n"
        "[LIGHT_1]\nNAME=LAMP_POD_SUB1\nCOLOR=55,55,45\n\n"
        "[BRAKE_0]\nNAME=TAILLIGHT\nCOLOR=75,3,0\nOFF_COLOR=22,0,0\n", encoding="utf-8")
    # these point at named parts of the Escort's model that ours doesn't have (yet)
    for f in ("blurred_objects.ini", "mirrors.ini", "analog_instruments.ini"):
        (data / f).write_text("", encoding="utf-8")
    # AC writes this itself when it's missing; an empty or stale one makes it log a KEY_NOT_FOUND per node
    (data / "proview_nodes.ini").unlink(missing_ok=True)
    (data / "colliders.ini").write_text(
        "[COLLIDER_0]\nCENTRE=0,-0.33,0.0\nSIZE=1.55,0.1,3.4\nGROUND_ENABLE=1\n", encoding="utf-8")
    (data / "ambient_shadows.ini").write_text("[SETTINGS]\nWIDTH=1.0\nLENGTH=2.7\n", encoding="utf-8")


def build_ui():
    ui = CAR / "ui"
    ui.mkdir(parents=True, exist_ok=True)
    power = [[r, round(t * r / 9549 * 1.341, 1)] for r, t in CRANK_TORQUE if r]   # UI shows crank figures
    info = {
        "name": "Talbot Sunbeam Lotus 1981 Works",
        "brand": "Talbot",
        "description": "1981 works Group 2 rally car (FIA homologation 1700). "
                       "v0.1 - blockout body and placeholder physics: dimensions, gearbox and fuel tank "
                       "from the homologation form; power, weight and tyres still to be tuned.",
        "tags": ["rally", "group 2", "rwd", "1980s", "manual"],
        "class": "race",
        "specs": {"bhp": f"{REAL_BHP + EXTRA_BHP}bhp", "torque": f"{max(t for _, t in CRANK_TORQUE):.0f}Nm", "weight": f"{TOTALMASS}kg",
                  "topspeed": "210km/h", "acceleration": "--s 0-100", "pwratio": f"{TOTALMASS / (REAL_BHP + EXTRA_BHP):.2f}kg/hp"},
        "torqueCurve": [[r, t] for r, t in CRANK_TORQUE if r],
        "powerCurve": power,
        "year": 1981,
        "country": "Great Britain",
        "author": "Nicklearse101",
        "version": "0.1",
        "url": "",
    }
    (ui / "ui_car.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    badge = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(badge)
    d.ellipse((4, 4, 124, 124), fill=(20, 40, 110, 255), outline=(230, 230, 230, 255), width=6)
    d.text((64, 64), "TALBOT", fill=(255, 255, 255, 255), anchor="mm")
    badge.save(ui / "badge.png")


def build_skin():
    skin = CAR / "skins" / "works_white"
    skin.mkdir(parents=True, exist_ok=True)
    (skin / "ui_skin.json").write_text(json.dumps(
        {"skinname": "Works white", "drivername": "", "country": "Great Britain", "team": "Talbot",
         "number": "", "priority": 1}, indent=2), encoding="utf-8")
    liv = Image.new("RGB", (64, 64), (240, 240, 240))
    ImageDraw.Draw(liv).rectangle((0, 26, 64, 38), fill=(40, 90, 200))
    liv.save(skin / "livery.png")


def build_sfx():
    sfx = CAR / "sfx"
    sfx.mkdir(parents=True, exist_ok=True)
    bank = AC / "content" / "cars" / DONOR_ID / "sfx" / f"{DONOR_ID}.bank"
    dst = sfx / f"{CAR_ID}.bank"
    if not dst.exists() or dst.stat().st_size != bank.stat().st_size:
        shutil.copyfile(bank, dst)
    master = (AC / "content" / "sfx" / "GUIDs.txt").read_text(encoding="utf-8").splitlines()
    lines = [l.replace(f"/{DONOR_ID}", f"/{CAR_ID}") for l in master
             if l.rstrip().endswith(f"bank:/{DONOR_ID}") or f"/cars/{DONOR_ID}/" in l]
    (sfx / "GUIDs.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def build_shadows():
    def blob(size, inset, blur, peak):
        im = Image.new("L", (size, size), 0)
        ImageDraw.Draw(im).rounded_rectangle((inset, inset, size - inset, size - inset), radius=size // 6, fill=peak)
        im = im.filter(ImageFilter.GaussianBlur(blur))
        return Image.merge("RGBA", (im, im, im, Image.new("L", (size, size), 255)))
    blob(512, 70, 40, 190).save(CAR / "body_shadow.png")
    for i in range(4):
        blob(64, 12, 6, 147).save(CAR / f"tyre_{i}_shadow.png")


def build_misc():
    donor = AC / "content" / "cars" / DONOR_ID
    shutil.copyfile(donor / "driver_base_pos.knh", CAR / "driver_base_pos.knh")
    anim = CAR / "animations"
    anim.mkdir(exist_ok=True)
    for f in ("steer.ksanim", "shift.ksanim"):   # driver arm animations used by driver3d.ini
        shutil.copyfile(donor / "animations" / f, anim / f)


if __name__ == "__main__":
    CAR.mkdir(parents=True, exist_ok=True)
    build_data(); build_ui(); build_skin(); n = build_sfx(); build_shadows(); build_misc()
    print(f"built {CAR}")
    print(f"GRAPHICS_OFFSET={GRAPHICS_OFFSET} (CG height {cg_h:.3f}, CG {cg_z:.3f} m ahead of mid-wheelbase)")
    print(f"sfx GUID lines: {n}")
