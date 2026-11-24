"""Nik 24 Nov: SetupCoach setups of the 13" car -> handling-equivalent setups for the 15" car (garden wheel swap: tyres
28 mm taller in radius, discs x15/13, brake torque 2310). Written to setups/ford_escort_mk2_tuned_15/generic/.
  ROD_LENGTH_xx  -28 clicks (1 click = 1 mm): body - and so aero, ride-height readings, camber curves - back where it was
  FINAL_RATIO    the ratio x 0.296/0.268 (same overall gearing); final.rto of the 15" car gets 3.41 and 3.85 added
  BRAKE_POWER    x (2000/0.268) / (2310/0.296) = 0.956 -> same braking force at the road
everything else (tyres, pressures, springs, dampers, ARBs, alignment, diff, aero, TC/ABS, fuel) unchanged."""
import re, sys
from pathlib import Path
sys.path.insert(0, r"D:\Claude\setupcoach-tools\acd"); sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools")
import acd_decoder, acd_patch

R13, R15 = 0.268, 0.296
OLD_RTO = [2.77, 2.91, 3.09, 3.25, 3.49, 3.68]
NEW_RTO = [2.77, 2.91, 3.09, 3.25, 3.41, 3.49, 3.68, 3.85]       # + 3.09 and 3.49 scaled by R15/R13
BRAKE = (2000 / R13) / (2310 / R15)
CAR15 = Path(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ford_escort_mk2_tuned_15")
SRC = Path.home() / "Documents" / "Assetto Corsa" / "setups" / "ford_escort_mk2_tuned"
DST = Path.home() / "Documents" / "Assetto Corsa" / "setups" / "ford_escort_mk2_tuned_15" / "generic"

# final.rto of the 15" car (only add ratios, sorted - the default FINAL in drivetrain.ini is untouched)
d = acd_decoder.decrypt_acd(CAR15 / "data.acd", CAR15.name)
want = "\r\n".join(f"{r:.3f}|{r:.3f}" for r in NEW_RTO) + "\r\n"
if d["final.rto"] != want:
    acd_patch.put_file(CAR15, "final.rto", want)


def get(t, sec):
    m = re.search(rf"(?ms)^\[{sec}\]\s*\r?\nVALUE=(-?[0-9.]+)", t)
    return float(m.group(1)) if m else None


def put(t, sec, val):
    if re.search(rf"(?m)^\[{sec}\]", t):
        return re.sub(rf"(?ms)(^\[{sec}\]\s*\r?\nVALUE=)(-?[0-9.]+)", lambda m: m.group(1) + str(val), t)
    return t.replace("[CAR]", f"[{sec}]\nVALUE={val}\n\n[CAR]")


DST.mkdir(parents=True, exist_ok=True)
for f in sorted(SRC.glob("*/SetupCoach_Optimized*.ini")):
    t = f.read_text(encoding="utf-8", errors="replace")
    track = f.parent.name
    notes = []
    for side in ("LF", "RF", "LR", "RR"):
        v = get(t, f"ROD_LENGTH_{side}")
        if v is not None:
            nv = max(0, int(v) - 28)
            t = put(t, f"ROD_LENGTH_{side}", nv)
            if v - 28 < 0:
                notes.append(f"{side} rod limited ({int(v)} -> 0, {int(28 - v)} mm short of equivalent)")
    fi = get(t, "FINAL_RATIO")
    if fi is not None:
        target = OLD_RTO[int(fi)] * R15 / R13
        ni = min(range(len(NEW_RTO)), key=lambda i: abs(NEW_RTO[i] - target))
        t = put(t, "FINAL_RATIO", ni)
        notes.append(f"final {OLD_RTO[int(fi)]} -> {NEW_RTO[ni]} (exact {target:.3f})")
    bp = get(t, "BRAKE_POWER_MULT") or 100
    t = put(t, "BRAKE_POWER_MULT", round(bp * BRAKE))
    t = t.replace("MODEL=ford_escort_mk2_tuned\n", "MODEL=ford_escort_mk2_tuned_15\n").replace(
        "MODEL=ford_escort_mk2_tuned\r\n", "MODEL=ford_escort_mk2_tuned_15\r\n")
    desc = f"15in equivalent of {track}/{f.stem} (13in car): rods -28 mm, final drive and brake power matched to the taller tyres"
    t = re.sub(r"(?m)^DESCRIPTION=.*$", "DESCRIPTION=" + desc, t, count=1)
    suffix = "_1" if f.stem.endswith("1") else ""
    out = DST / f"SetupCoach_{track}{suffix}.ini"
    out.write_text(t, encoding="utf-8")
    print(out.name, "|", "; ".join(notes))
