"""Ford Escort Mk2 DTM v26 - the chassis physics rebuilt on the Kunos Ford Escort Mk1 (ks_ford_escort_mk1).
Writes staging/ford_escort_mk2_tuned/data; tools/install.py puts it in the game.

Why: Nik (13 Oct) - "re-write the escort dtm v25 physics to be modelled on the Kunos Escort Mk1". v20-v25 were modelled on
Kunos' Mercedes 190E DTM (dtm_build.py, kept for history). The Mk1 is the parent of this mod's own physics (same wheelbase
2.407 m, same strut / 5-link-axle hardpoints) and of the Talbot Sunbeam that Nik drives and loves, so the recipe is the
Sunbeam's: the Mk1 file set as the template, rates scaled up for the extra mass, nothing else invented.

  * The Mk1 is the source of truth: suspension types + every hardpoint (strut front with the Mk1's caster, 5-link live
    axle), damper/spring/bump-stop philosophy, ARB 12500/0, ride rods 0.040/0.080, Vintage GT70 tyre model, brakes
    (1800 Nm, 0.695 front, simple system), steering 450 deg / 16:1, yaw/pitch/roll inertia box 1.40 x 1.50 x 4.30.
  * "Same car, heavier": this car is 1050 kg against the Mk1's 885 (x1.186), so every rate that scales with mass does -
    springs (rounded to the setup's 2 kN/m grid: 46 / 40 kN/m = the Sunbeam's), dampers, front ARB, bump stops, and the
    tyre's reference load FZ0 (a wider tyre carrying more load at the same grip level). Ride frequency, static
    deflection and damping ratios therefore come out exactly as on the Mk1 (report printed by the build).
  * Kept from the live car because they are the model's / this car's identity, not chassis feel: the 400 bhp V8
    (power_dtm.lut), 6-speed sequential gearbox + final.rto, the 90s DTM aero kit's curves and positions (the wing and
    splitter are on the 3D model), ABS/TC electronics (driver-toggled), tracks, graphics offsets, colliders, mirrors, fuel
    tank, lights, sounds, cameras - everything that ties to the kn5 - and the tyre sizes CM measured off the model
    (255/265 on r 0.268).
  * Tyres: compound 0 = the Mk1's Vintage GT70 resized to this car (r 0.268, 255/265, inertia x (r/r0)^2, FZ0 x mass
    ratio); compounds 1-3 = Kunos' DTM90 slicks S/M/H (as v20-v25) for when Nik wants slicks for the V8 - pick in CM.
  * Diff 0.45 / 0.30 / 40 Nm = the Sunbeam v6's (the Mk1's own is 0.25 / 0.25 / 0 for 150 hp; coefficients act on torque).
  * Steering force: FFMULT 2.30 = the Sunbeam's 1.62 at 11.3:1 expressed at the Mk1's 16:1 - same front geometry, so the
    same wheel weight Nik chose there (Mk1 default 2.752 was "very heavy").
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dtm_build as T      # text helpers (sections / join / set_keys / drop_section / fmt) and the car constants

VERSION = "v26"
CAR_ID = T.CAR_ID
PROJECT = T.PROJECT
MK1 = PROJECT / "ref" / "ks_ford_escort_mk1"
MERC = PROJECT / "ref" / "ks_mercedes_190_evo2"              # DTM90 slick compounds (optional compounds 1-3)
BASE = PROJECT / "decoded" / "data_acd_v25_live"            # the live car's data.acd of 13 Oct = what Nik had installed
OUT = PROJECT / "staging" / CAR_ID / "data"

sections, join, set_keys, drop_section, fmt = T.sections, T.join, T.set_keys, T.drop_section, T.fmt


def read(path):
    return path.read_text(encoding="utf-8", errors="replace")


def get(path, section, key):
    for name, body in sections(read(path)):
        if name == section:
            for line in body:
                m = re.match(rf"\s*{re.escape(key)}\s*=\s*([^;\s]+)", line)
                if m:
                    return m.group(1)
    raise KeyError(f"{path.name} [{section}] {key}")


def getf(path, section, key):
    return float(get(path, section, key))


def put(body, key, value):
    """Replace the value of KEY in a section body (list of lines), keeping any trailing comment."""
    for i, line in enumerate(body):
        m = re.match(rf"(\s*{re.escape(key)}\s*=\s*)([^;\s]+)(.*)", line)
        if m:
            body[i] = f"{m.group(1)}{value}{m.group(3)}"
            return
    raise KeyError(key)


def snap(value, step):
    return round(value / step) * step


# ---------------------------------------------------------------------------------------------------------------- design
MASS_MK1 = getf(MK1 / "car.ini", "BASIC", "TOTALMASS")           # 885
MASS = getf(BASE / "car.ini", "BASIC", "TOTALMASS")              # 1050: DTM minimum weight with driver, unchanged
K = MASS / MASS_MK1
CG = getf(MK1 / "suspensions.ini", "BASIC", "CG_LOCATION")       # 0.55 = the live car's too
assert abs(CG - getf(BASE / "suspensions.ini", "BASIC", "CG_LOCATION")) < 1e-9
assert abs(getf(MK1 / "suspensions.ini", "BASIC", "WHEELBASE") - getf(BASE / "suspensions.ini", "BASIC", "WHEELBASE")) < 1e-9

SPRING_STEP = 2000                       # the setup's grid (2 kN/m); 38000 x K = 45.1k -> 46k, 34000 x K = 40.3k -> 40k
SPRING = {"FRONT": snap(getf(MK1 / "suspensions.ini", "FRONT", "SPRING_RATE") * K, SPRING_STEP),
          "REAR": snap(getf(MK1 / "suspensions.ini", "REAR", "SPRING_RATE") * K, SPRING_STEP)}
BUMP_STOP = snap(getf(MK1 / "suspensions.ini", "FRONT", "BUMP_STOP_RATE") * K, 500)
ARB = {"FRONT": snap(getf(MK1 / "suspensions.ini", "ARB", "FRONT") * K, 2500), "REAR": 0}
# damper (key, setup grid step) - physics value = Mk1 x K snapped to the grid the setup uses, so default == physics
DAMPERS = {
    "FRONT": {"DAMP_BUMP": 250, "DAMP_FAST_BUMP": 100, "DAMP_REBOUND": 250, "DAMP_FAST_REBOUND": 100},
    "REAR": {"DAMP_BUMP": 100, "DAMP_FAST_BUMP": 50, "DAMP_REBOUND": 100, "DAMP_FAST_REBOUND": 50},
}
DAMP = {c: {k: snap(getf(MK1 / "suspensions.ini", c, k) * K, step) for k, step in d.items()} for c, d in DAMPERS.items()}
TRACK = {c: getf(BASE / "suspensions.ini", c, "TRACK") for c in ("FRONT", "REAR")}   # from the model's wheel pivots
ROD = {c: getf(MK1 / "suspensions.ini", c, "ROD_LENGTH") for c in ("FRONT", "REAR")}  # 0.040 / 0.080 (see report: v20 stance)
STATIC_CAMBER_F = getf(MK1 / "suspensions.ini", "FRONT", "STATIC_CAMBER")             # -0.65, as on the Sunbeam

DIFF = {"POWER": 0.45, "COAST": 0.30, "PRELOAD": 40}             # Sunbeam v6
FFMULT = 2.30
BRAKES = {"MAX_TORQUE": 1800, "FRONT_SHARE": 0.70, "HANDBRAKE_TORQUE": 1600}   # Mk1 (0.695 front -> 0.70, the setup's 1 % grid)
# Mk1 inertia box (width, height, length); the Escort Mk2's body is the same size class
INERTIA = get(MK1 / "car.ini", "BASIC", "INERTIA")

TYRE = {"RADIUS": getf(BASE / "tyres.ini", "FRONT", "RADIUS"), "RIM_RADIUS": getf(BASE / "tyres.ini", "FRONT", "RIM_RADIUS"),
        "WIDTH_FRONT": getf(BASE / "tyres.ini", "FRONT", "WIDTH"), "WIDTH_REAR": getf(BASE / "tyres.ini", "REAR", "WIDTH")}
TYRE_SRC_MK1 = getf(MK1 / "tyres.ini", "FRONT", "RADIUS")        # 0.288
TYRE_SRC_MERC = 0.3225                                           # the 190's DTM90 tyre

# setup.ini: (section, tab, label, min, max, step, show_clicks, x, y, help, default-in-setup-units)
SETUP = [
    ("WING_1", "AERO", "Front splitter", 0, 3, 1, 1, 0.5, 0, "HELP_WING_FRONT", 3),
    ("WING_2", "AERO", "Rear wing", 0, 4, 1, 2, 0.5, 2, "HELP_WING_REAR", 3),
    ("SPRING_RATE_LF", "SUSPENSIONS", "Wheel rate LF", 30, 90, 2, 0, 0, 1, "HELP_LF_WHEELRATE", SPRING["FRONT"] // 1000),
    ("SPRING_RATE_RF", "SUSPENSIONS", "Wheel rate RF", 30, 90, 2, 0, 1, 1, "HELP_RF_WHEELRATE", SPRING["FRONT"] // 1000),
    ("ROD_LENGTH_LF", "SUSPENSIONS", "Height LF", 0, 800, 10, 2, 0, 2, "HELP_LF_RODLENGTH", round(ROD["FRONT"] * 10000)),
    ("ROD_LENGTH_RF", "SUSPENSIONS", "Height RF", 0, 800, 10, 2, 1, 2, "HELP_RF_RODLENGTH", round(ROD["FRONT"] * 10000)),
    ("ARB_FRONT", "SUSPENSIONS", "ARB Front", 5000, 40000, 2500, 2, 0.5, 3, "HELP_FRONT_ARB", ARB["FRONT"]),
    ("SPRING_RATE_LR", "SUSPENSIONS", "Wheel rate LR", 24, 80, 2, 0, 0, 6, "HELP_LR_WHEELRATE", SPRING["REAR"] // 1000),
    ("SPRING_RATE_RR", "SUSPENSIONS", "Wheel rate RR", 24, 80, 2, 0, 1, 6, "HELP_RR_WHEELRATE", SPRING["REAR"] // 1000),
    ("ROD_LENGTH_LR", "SUSPENSIONS", "Height LR", 300, 1300, 10, 2, 0, 7, "HELP_LR_RODLENGTH", round(ROD["REAR"] * 10000)),
    ("ROD_LENGTH_RR", "SUSPENSIONS", "Height RR", 300, 1300, 10, 2, 1, 7, "HELP_RR_RODLENGTH", round(ROD["REAR"] * 10000)),
    ("ARB_REAR", "SUSPENSIONS", "ARB Rear", 0, 12000, 1500, 2, 0.5, 8, "HELP_REAR_ARB", ARB["REAR"]),
    # camber: the Mk1's -0.65 default (as the Sunbeam); range to -4.5 because Setup Coach drives the strut front there
    ("CAMBER_LF", "ALIGNMENT", "CAMBER_LF", -4.5, -0.2, 1, 0, 0, 0, "HELP_LF_CAMBER", STATIC_CAMBER_F),
    ("CAMBER_RF", "ALIGNMENT", "CAMBER_RF", -4.5, -0.2, 1, 0, 1, 0, "HELP_RF_CAMBER", STATIC_CAMBER_F),
    ("TOE_OUT_LF", "ALIGNMENT", "Toe LF", -60, 70, 5, 2, 0, 1, "HELP_LF_TOE", round(getf(MK1 / "suspensions.ini", "FRONT", "TOE_OUT") * 1e5)),
    ("TOE_OUT_RF", "ALIGNMENT", "Toe RF", -60, 70, 5, 2, 1, 1, "HELP_RF_TOE", round(getf(MK1 / "suspensions.ini", "FRONT", "TOE_OUT") * 1e5)),
    ("DIFF_POWER", "DRIVETRAIN", "Diff Power", 10, 70, 5, 0, 0.5, 2, "HELP_DIFF_POWER", round(DIFF["POWER"] * 100)),
    ("DIFF_PRELOAD", "DRIVETRAIN", "Diff Preload", 10, 200, 10, 0, 0.5, 4, "HELP_DIFF_PRELOAD", DIFF["PRELOAD"]),
    ("DIFF_COAST", "DRIVETRAIN", "Diff Coast", 10, 70, 5, 0, 0.5, 6, "HELP_DIFF_COAST", round(DIFF["COAST"] * 100)),
    ("BRAKE_POWER_MULT", "GENERIC", "Brake power", 80, 100, 1, 0, 0.5, 1, "HELP_BRAKE_POWER_MULT", 100),
    ("FRONT_BIAS", "GENERIC", "Brake Bias", 52, 80, 1, 0, 0.5, 2, "HELP_BRAKE_BIAS", round(BRAKES["FRONT_SHARE"] * 100)),
]
# damper ranges bracket the default (min, max); step comes from DAMPERS
DAMP_RANGE = {
    "FRONT": {"DAMP_BUMP": (1500, 7000), "DAMP_FAST_BUMP": (800, 3600), "DAMP_REBOUND": (2500, 10000), "DAMP_FAST_REBOUND": (1300, 4500)},
    "REAR": {"DAMP_BUMP": (700, 4200), "DAMP_FAST_BUMP": (400, 2400), "DAMP_REBOUND": (1500, 7000), "DAMP_FAST_REBOUND": (600, 3200)},
}
for _corner, _x, _y0 in (("FRONT", 0, 0), ("FRONT", 1, 0), ("REAR", 0, 5), ("REAR", 1, 5)):
    _side, _c = ("L" if _x == 0 else "R"), _corner[0]
    for _row, (_key, _label, _help) in enumerate((("DAMP_BUMP", "Bump", "BUMP"), ("DAMP_FAST_BUMP", "FST Bump", "FBUMP"),
                                                  ("DAMP_REBOUND", "Rebound", "REBOUND"),
                                                  ("DAMP_FAST_REBOUND", "FST Rebound", "FREBOUND"))):
        _lo, _hi = DAMP_RANGE[_corner][_key]
        SETUP.append((f"{_key}_{_side}{_c}", "DAMPERS", _label, _lo, _hi, DAMPERS[_corner][_key], 2, _x, _y0 + _row,
                      f"HELP_{_side}{_c}_DAMPER_{_help}", DAMP[_corner][_key]))


# ---------------------------------------------------------------------------------------------------------------- builders
def build_suspensions():
    sus = OUT / "suspensions.ini"
    shutil.copy2(MK1 / "suspensions.ini", sus)                   # types, hardpoints, [AXLE] 5-link, damage: all the Mk1's
    set_keys(sus, "ARB", ARB)
    for corner in ("FRONT", "REAR"):
        vals = {"TRACK": f"{TRACK[corner]:.4f}", "SPRING_RATE": SPRING[corner], "BUMP_STOP_RATE": BUMP_STOP,
                **{k: v for k, v in DAMP[corner].items()}}
        set_keys(sus, corner, vals)
    # graphics offsets belong to the model's wheel/suspension nodes: from the live car
    base = {n: b for n, b in sections(read(BASE / "suspensions.ini"))}
    secs = sections(read(sus))
    for i, (name, _) in enumerate(secs):
        if name == "GRAPHICS_OFFSETS":
            secs[i] = (name, base["GRAPHICS_OFFSETS"])
    sus.write_text(join(secs), encoding="utf-8")


def resize_tyre_sections(secs, widths, r_src, rim=None, load_k=1.0, rename=None):
    """Return (name, body) pairs for the FRONT/REAR (+ THERMAL) sections of a tyre file, resized to this car."""
    out = []
    k_inertia = (TYRE["RADIUS"] / r_src) ** 2
    for name, body in secs:
        m = re.fullmatch(r"(FRONT|REAR|THERMAL_FRONT|THERMAL_REAR)(_\d+)?", name)
        if not m:
            continue
        body = list(body)
        if m.group(1) in ("FRONT", "REAR"):
            put(body, "RADIUS", TYRE["RADIUS"])
            put(body, "RIM_RADIUS", TYRE["RIM_RADIUS"])
            put(body, "WIDTH", widths[m.group(1)])
            for key in ("ANGULAR_INERTIA",):
                v = float(re.search(rf"{key}\s*=\s*([^;\s]+)", "\n".join(body)).group(1))
                put(body, key, f"{v * k_inertia:.3f}")
            if load_k != 1.0:
                v = float(re.search(r"^\s*FZ0\s*=\s*([^;\s]+)", "\n".join(body), re.M).group(1))
                put(body, "FZ0", round(v * load_k))
        out.append((rename(name) if rename else name, body))
    return out


def build_tyres():
    widths = {"FRONT": f"{TYRE['WIDTH_FRONT']:.3f}", "REAR": f"{TYRE['WIDTH_REAR']:.3f}"}
    mk1 = sections(read(MK1 / "tyres.ini"))
    merc = sections(read(MERC / "tyres.ini"))
    ext = [s for s in sections(read(BASE / "tyres.ini")) if s[0] == "_EXTENSION"]
    # compound 0: the Mk1's Vintage GT70, FZ0 x mass ratio (same grip level at this car's static load)
    gt70 = resize_tyre_sections(mk1, widths, TYRE_SRC_MK1, load_k=K)
    # compounds 1-3: DTM90 S/M/H (the 190's file: unsuffixed = soft, _1 = medium, _2 = hard) -> _1 / _2 / _3
    shift = lambda n: re.sub(r"^(.*?)(?:_(\d+))?$", lambda m: f"{m.group(1)}_{int(m.group(2) or 0) + 1}", n)
    dtm = resize_tyre_sections(merc, widths, TYRE_SRC_MERC, rename=shift)
    secs = [("", ["[HEADER]", "VERSION=10", ""]), *ext, ("VIRTUALKM", ["USE_LOAD=1", ""]),
            ("COMPOUND_DEFAULT", ["INDEX=0", ""]), *[(n, b + [""]) for n, b in gt70 + dtm]]
    # first element holds the text before the first section; build the file by hand
    lines = ["[HEADER]", "VERSION=10", ""]
    for n, b in secs[1:]:
        lines += [f"[{n}]", *b]
    text = "\n".join(lines).rstrip("\n") + "\n"
    (OUT / "tyres.ini").write_text(text, encoding="utf-8")
    luts = set(re.findall(r"=\s*([\w.-]+\.lut)", text))
    for lut in sorted(luts):
        src = MK1 / lut if (MK1 / lut).exists() else MERC / lut
        assert src.exists(), lut
        shutil.copy2(src, OUT / lut)
    return luts


def build_brakes():
    brakes = OUT / "brakes.ini"
    shutil.copy2(MK1 / "brakes.ini", brakes)                     # simple system + the Mk1's disc/pad temperature model
    set_keys(brakes, "DATA", {**BRAKES, "COCKPIT_ADJUSTABLE": 1})
    base = {n: b for n, b in sections(read(BASE / "brakes.ini"))}   # disc node names + glow: the model's
    secs = sections(read(brakes))
    for i, (name, _) in enumerate(secs):
        if name == "DISCS_GRAPHICS":
            secs[i] = (name, base["DISCS_GRAPHICS"])
    brakes.write_text(join(secs), encoding="utf-8")


def build_setup():
    keep = {n: b for n, b in sections(read(BASE / "setup.ini"))}
    lines = ["[DISPLAY_METHOD]", "SHOW_CLICKS=1", ""]
    for p in ("PRESSURE_LF", "PRESSURE_RF", "PRESSURE_LR", "PRESSURE_RR", "FINAL_GEAR_RATIO", "FUEL"):
        lines += [f"[{p}]", *[l for l in keep[p] if l.strip() and not l.startswith(("/", ";"))], ""]
    for sec, tab, label, lo, hi, step, sc, x, y, help_, default in SETUP:
        assert lo <= default <= hi, (sec, default)
        if not sec.startswith(("CAMBER", "TOE")):               # Mk1's own defaults (-0.65 deg camber) sit between grid points
            assert (default - lo) % step == 0, (sec, default, lo, step)
        lines += [f"[{sec}]", f"SHOW_CLICKS={sc}", f"TAB={tab}", f"NAME={label}", f"MIN={fmt(lo)}", f"MAX={fmt(hi)}",
                  f"STEP={step}", f"POS_X={fmt(x)}", f"POS_Y={fmt(y)}", f"HELP={help_}", ""]
    (OUT / "setup.ini").write_text("\n".join(lines), encoding="utf-8")


def check_defaults():
    """Every setup default must equal the physics value it adjusts (a fresh setup = the designed car)."""
    sus = OUT / "suspensions.ini"
    rod = lambda m: round(m * 10000)
    want = {"SPRING_RATE_LF": SPRING["FRONT"] // 1000, "SPRING_RATE_LR": SPRING["REAR"] // 1000,
            "ROD_LENGTH_LF": rod(ROD["FRONT"]), "ROD_LENGTH_LR": rod(ROD["REAR"]),
            "ARB_FRONT": ARB["FRONT"], "ARB_REAR": ARB["REAR"], "CAMBER_LF": STATIC_CAMBER_F,
            "TOE_OUT_LF": round(getf(sus, "FRONT", "TOE_OUT") * 1e5),
            "DIFF_POWER": round(DIFF["POWER"] * 100), "DIFF_COAST": round(DIFF["COAST"] * 100), "DIFF_PRELOAD": DIFF["PRELOAD"],
            "FRONT_BIAS": round(BRAKES["FRONT_SHARE"] * 100)}
    for k in ("DAMP_BUMP", "DAMP_FAST_BUMP", "DAMP_REBOUND", "DAMP_FAST_REBOUND"):
        want[f"{k}_LF"], want[f"{k}_LR"] = DAMP["FRONT"][k], DAMP["REAR"][k]
    table = {s[0]: s[-1] for s in SETUP}
    for k, v in want.items():
        assert table[k] == v, (k, table[k], v)
    # and the files say the same as the constants
    assert getf(sus, "FRONT", "SPRING_RATE") == SPRING["FRONT"] and getf(sus, "REAR", "SPRING_RATE") == SPRING["REAR"]
    assert abs(getf(sus, "FRONT", "ROD_LENGTH") - ROD["FRONT"]) < 1e-9 and abs(getf(sus, "REAR", "ROD_LENGTH") - ROD["REAR"]) < 1e-9
    for c in ("FRONT", "REAR"):
        for k, v in DAMP[c].items():
            assert getf(sus, c, k) == v, (c, k)
    assert getf(OUT / "drivetrain.ini", "DIFFERENTIAL", "POWER") == DIFF["POWER"]
    assert getf(OUT / "brakes.ini", "DATA", "FRONT_SHARE") == BRAKES["FRONT_SHARE"]


def report():
    """Dimensionless behaviour of the Mk1 and of v26 side by side: same ride frequency / damping / brake margin."""
    import math
    g = 9.81

    def line(label, mass, cg, sus, brakes, tyre_r, mu_f):
        out = [f"  {label}: {mass:.0f} kg, {cg * 100:.0f} % front"]
        for corner, share in (("FRONT", cg), ("REAR", 1 - cg)):
            m = mass * share / 2
            k = getf(sus, corner, "SPRING_RATE")
            f = math.sqrt(k / m) / (2 * math.pi)
            defl = m * g / k * 1000
            zb = getf(sus, corner, "DAMP_BUMP") / (2 * math.sqrt(k * m))
            zr = getf(sus, corner, "DAMP_REBOUND") / (2 * math.sqrt(k * m))
            out.append(f"    {corner:5s} {k / 1000:5.1f} kN/m  {f:.2f} Hz  static {defl:4.0f} mm  zeta bump {zb:.2f} / rebound {zr:.2f}")
        torque = getf(brakes, "DATA", "MAX_TORQUE")
        cap = 2 * torque / tyre_r / (mass * g)
        out.append(f"    brakes {torque:.0f} Nm, r {tyre_r:.3f} -> {cap:.2f} g capacity (tyre peak DY {mu_f:.2f})")
        return "\n".join(out)

    print("ride / damping / brake margin (all-four-wheel brake capacity = 2 x MAX_TORQUE / r / (m g))")
    print(line("Kunos Mk1", MASS_MK1, CG, MK1 / "suspensions.ini", MK1 / "brakes.ini", TYRE_SRC_MK1,
               getf(MK1 / "tyres.ini", "FRONT", "DY0")))
    print(line("Escort DTM v26", MASS, CG, OUT / "suspensions.ini", OUT / "brakes.ini", TYRE["RADIUS"],
               getf(OUT / "tyres.ini", "FRONT", "DY0")))
    # stance: S = rod - m g / k (higher = car sits higher); v20-v25's design stance vs the Mk1 rods vs the live car
    def stance(front_rod, rear_rod, kf, kr):
        mf, mr = MASS * CG / 2, MASS * (1 - CG) / 2
        return ((front_rod - mf * g / kf) * 1000, (rear_rod - mr * g / kr) * 1000)
    for label, vals in (("v20-v25 design (rods .012/.055, 80/70 kN/m)", stance(0.012, 0.055, 80000, 70000)),
                        ("live car 13 Oct (rods .100/.126, 45.4/45.6)", stance(0.100, 0.126, 45393, 45569)),
                        ("v26 (rods .040/.080, 46/40)", stance(ROD["FRONT"], ROD["REAR"], SPRING["FRONT"], SPRING["REAR"]))):
        print(f"  stance index {label}: front {vals[0]:+5.1f} mm  rear {vals[1]:+5.1f} mm")


def build():
    if OUT.parent.exists():
        shutil.rmtree(OUT.parent)
    shutil.copytree(BASE, OUT)
    for p in list(OUT.glob("__cm_*")):                           # CM's tyre-tool files; CM regenerates them if wanted
        p.unlink()
    for name in ("proview_nodes.ini", "tdx_235.lut", "tdy_235.lut", "semislicks_front.lut", "tcurve_street.lut",
                 "brake_pad_DS2500.lut", "brake_pad_ds3000.lut"):
        (OUT / name).unlink(missing_ok=True)                     # AC rewrites proview_nodes; the rest are replaced / unused

    car = OUT / "car.ini"
    set_keys(car, "BASIC", {"INERTIA": INERTIA})
    set_keys(car, "CONTROLS", {"FFMULT": f"{FFMULT:.3f}", "STEER_LOCK": get(MK1 / "car.ini", "CONTROLS", "STEER_LOCK"),
                               "STEER_RATIO": get(MK1 / "car.ini", "CONTROLS", "STEER_RATIO"),
                               "LINEAR_STEER_ROD_RATIO": get(MK1 / "car.ini", "CONTROLS", "LINEAR_STEER_ROD_RATIO")})
    set_keys(car, "INFO", {"SCREEN_NAME": f"Ford Escort Mk2 DTM {VERSION}"}, add=True)

    build_suspensions()
    tyre_luts = build_tyres()
    build_brakes()
    set_keys(OUT / "drivetrain.ini", "DIFFERENTIAL", DIFF)
    build_setup()
    check_defaults()

    # every file the physics points at must be there
    for f in ("tyres.ini", "aero.ini", "engine.ini", "brakes.ini", "drivetrain.ini", "suspensions.ini", "electronics.ini"):
        text = read(OUT / f)
        for ref in re.findall(r"=\s*([\w.-]+\.(?:lut|rto))", text):
            if f == "engine.ini" and ref == "coast.lut" and "FROM_COAST_REF" in text:
                continue                                         # Kunos-standard unused entry (coast from COAST_REF)
            assert (OUT / ref).exists(), f"{f} points at missing {ref}"
    print(f"built {VERSION} -> {OUT}\n  tyre luts {sorted(tyre_luts)}")
    report()


if __name__ == "__main__":
    build()
