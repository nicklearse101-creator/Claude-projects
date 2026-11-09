"""colliders.ini boxes and the fuel tank position fitted to the Sunbeam MODEL, in the car's own physics frame.

Why: the build used to copy the stock mod's colliders.ini (four thin slabs made for the stock car's frame, offset
0,-0.365,-0.247, no pitch, 3.1 m long from 0.2 m behind the nose to 0.5 m short of the tail) and the Escort donor's
tank position (0,-0.15,-1.85: 0.47 m behind the rear axle, in the bumper). Our frame is offset (0,-0.414,-0.174) with
GRAPHICS_PITCH_ROTATION -1.85, so the boxes sat ~7 cm off the model and ended well inside it (Nik, 6 Oct, CM showroom).

Maths (verified on the wheel nodes: model front axle z 1.212 -> physics 1.038):  P_phys = Rx(pitch) * (P_model + OFFSET)
with AC axes (x left, y up, z forward; Blender (x, y, z) = AC (x, z, -y)) and a negative pitch lowering the tail.

    python tools/collider_fit.py <car folder>/data      # rewrites colliders.ini + [FUELTANK] POSITION in that data dir
"""
import math
import re
import sys
from pathlib import Path

# body sections in MODEL (Blender) space: (name, y_from, y_to, half width, z_bottom, z_top)
# measured on the finished model 6 Oct: nose ends y -1.925, tail y 1.933, flares +-0.852, bumpers +-0.75,
# lowest body edges z 0.00-0.07 (blades), sills 0.02-0.10; bottom 0.06 keeps the old ground clearance (~0.21 m)
SECTIONS = [
    ("nose",       -1.925, -1.400, 0.750, 0.06, 0.75),
    ("front_body", -1.400,  0.000, 0.830, 0.06, 0.75),
    ("rear_body",   0.000,  1.400, 0.830, 0.06, 0.75),
    ("tail",        1.400,  1.933, 0.770, 0.06, 0.75),
]
# fuel tank: in the boot, on the boot carpet floor (z 0.33, trunkbay_a_SUB1), against the rear bulkhead side of the
# boot (front wall y 1.18, rear wall 1.81; wheel tubs leave 1.06 m between at y 1.3-1.45): ~0.9 x 0.45 x 0.26 m = 90 L
TANK_MODEL = (0.0, 1.45, 0.46)           # Blender x, y, z of the tank centre


def to_physics(p_blender, offset, pitch_deg):
    x, y, z = p_blender[0], p_blender[2], -p_blender[1]          # AC axes
    y, z = y + offset[1], z + offset[2]
    t = math.radians(pitch_deg)
    return (x + offset[0], y * math.cos(t) - z * math.sin(t), y * math.sin(t) + z * math.cos(t))


def colliders_text(offset, pitch_deg):
    out = []
    for i, (name, y0, y1, hw, z0, z1) in enumerate(SECTIONS):
        c = to_physics((0.0, (y0 + y1) / 2, (z0 + z1) / 2), offset, pitch_deg)
        out += [f"; {name}: y {y0:+.3f}..{y1:+.3f}, z {z0:.2f}..{z1:.2f} in the model",
                f"[COLLIDER_{i}]",
                f"CENTRE={c[0]:.3f},{c[1]:.3f},{c[2]:.3f}",
                f"SIZE={2 * hw:.2f},{z1 - z0:.2f},{abs(y1 - y0):.3f}",
                "GROUND_ENABLE=1", ""]
    return "\n".join(out)


def tank_position(offset, pitch_deg):
    p = to_physics(TANK_MODEL, offset, pitch_deg)
    return f"{p[0]:.3f},{p[1]:.3f},{p[2]:.3f}"


def read_frame(car_ini_text):
    off = re.search(r"^GRAPHICS_OFFSET\s*=\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)", car_ini_text, re.M)
    pit = re.search(r"^GRAPHICS_PITCH_ROTATION\s*=\s*([-\d.]+)", car_ini_text, re.M)
    return tuple(float(v) for v in off.groups()), float(pit.group(1)) if pit else 0.0


def apply(data_dir):
    """Rewrite colliders.ini and the tank position in a data folder, keeping its line endings."""
    data = Path(data_dir)
    car = data / "car.ini"
    raw = car.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    offset, pitch = read_frame(raw)
    new_pos = tank_position(offset, pitch)
    text, n = re.subn(r"(\[FUELTANK\]\s*\r?\n\s*POSITION\s*=)[^\r\n]*", r"\g<1>" + new_pos, raw)
    assert n == 1, "no [FUELTANK] POSITION found"
    car.write_bytes(text.encode("utf-8"))
    (data / "colliders.ini").write_bytes(colliders_text(offset, pitch).replace("\n", nl).encode("utf-8"))
    return offset, pitch, new_pos


if __name__ == "__main__":
    print(apply(sys.argv[1]))
