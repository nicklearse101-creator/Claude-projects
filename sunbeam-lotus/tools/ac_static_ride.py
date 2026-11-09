"""Measure where AC's physics puts the wheel hubs relative to the car body, and the model placement that fits.

Run with the car loaded in AC, sitting still on flat ground (pit lane / grid), engine running, no inputs:
    python ac_static_ride.py            (prints numbers and writes export/graphics_fit.json)
    python ac_static_ride.py --any --out ../export/graphics_fit_backup_v6.json     (another car id, own file)
Run it from a normal console/PowerShell: a sandboxed shell sees an empty "Local\\" shared-memory namespace.

Reads AC's shared memory (acpmf_physics / acpmf_static), 60 samples over 3 s, averaged:
  * cgHeight  - CG height above the ground
  * rideHeight[front, rear] - heights of the car.ini PICKUP points; their difference gives the body pitch
  * wheelLoad - to take the tyre's static squash (load / tyres.ini RATE) off its radius
Hub height in the body frame (relative to the CG, body pitch removed) for each axle:
    y_i = (R_loaded_i - cgHeight - x_i * sin(pitch)) / cos(pitch)
Then GRAPHICS_OFFSET y and GRAPHICS_PITCH_ROTATION that put the model's hub centres (y 0.145, level) there.
Pitch sign follows the Kunos Escort: its level model with rear hubs lower in physics uses a NEGATIVE rotation.
"""
import json
import math
import mmap
import struct
import sys
import time
from pathlib import Path

WB, CG_LOCATION = 2.413, 0.57
X_FRONT, X_REAR = WB * (1 - CG_LOCATION), -WB * CG_LOCATION     # axles relative to the CG, forward +
TYRE_R = 0.295
RATE_F, RATE_R = 300260.0, 316084.0          # tyres.ini RATE (front, rear)
MODEL_HUB_Y = 0.145                          # stock model wheel centres (AC model space, both axles)
MODEL_HUB_Z = (1.212, -1.207)                # front, rear
CAR_ID = "talbot_sunbeam_lotus_81_works"
OUT = Path(__file__).resolve().parent.parent / "export" / "graphics_fit.json"
if "--out" in sys.argv:
    OUT = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()


def read_page(tag, size):
    m = mmap.mmap(-1, size, tag, access=mmap.ACCESS_READ)
    try:
        return m.read(size)
    finally:
        m.close()


def main():
    static = read_page("Local\\acpmf_static", 200)
    car = static[68:134].decode("utf-16-le", "ignore").split("\x00")[0]
    print("car loaded in AC:", car or "(none - is AC running with a car on track?)")
    if car != CAR_ID and "--any" not in sys.argv:
        sys.exit(f"expected {CAR_ID} - load it and sit still in the pits (or pass --any)")
    rows = []
    for _ in range(60):
        p = read_page("Local\\acpmf_physics", 600)
        speed = struct.unpack_from("<f", p, 28)[0]
        load = struct.unpack_from("<4f", p, 72)
        travel = struct.unpack_from("<4f", p, 184)
        pitch_sm = struct.unpack_from("<f", p, 212)[0]
        cg = struct.unpack_from("<f", p, 220)[0]
        rh = struct.unpack_from("<2f", p, 268)
        rows.append((speed, load, travel, pitch_sm, cg, rh))
        time.sleep(0.05)
    avg = lambda f: sum(f(r) for r in rows) / len(rows)
    speed = max(abs(r[0]) for r in rows)
    if speed > 0.5:
        print(f"warning: car moving ({speed:.1f} km/h) - results unreliable")
    load = [avg(lambda r, i=i: r[1][i]) for i in range(4)]
    travel = [avg(lambda r, i=i: r[2][i]) for i in range(4)]
    cg = avg(lambda r: r[4]); rh_f = avg(lambda r: r[5][0]); rh_r = avg(lambda r: r[5][1])
    pitch_sm = avg(lambda r: r[3])
    pitch = math.asin(max(-1.0, min(1.0, (rh_f - rh_r) / (X_FRONT - X_REAR))))      # nose-up positive
    r_f = TYRE_R - (load[0] + load[1]) / 2 / RATE_F
    r_r = TYRE_R - (load[2] + load[3]) / 2 / RATE_R
    y_f = (r_f - cg - X_FRONT * math.sin(pitch)) / math.cos(pitch)
    y_r = (r_r - cg - X_REAR * math.sin(pitch)) / math.cos(pitch)
    # model placement: body_y = model_y + off_y + k * (model_z + off_z), k = tan(model rotation)
    off_z = -(MODEL_HUB_Z[0] - X_FRONT)
    zf, zr = MODEL_HUB_Z[0] + off_z, MODEL_HUB_Z[1] + off_z
    k = ((y_f - MODEL_HUB_Y) - (y_r - MODEL_HUB_Y)) / (zf - zr)
    off_y = y_f - MODEL_HUB_Y - k * zf
    rot_deg = -math.degrees(math.atan(k))
    res = {"cgHeight": round(cg, 4), "rideHeight": [round(rh_f, 4), round(rh_r, 4)],
           "pitch_deg_from_rideheight": round(math.degrees(pitch), 3), "pitch_shared_memory": round(pitch_sm, 4),
           "wheel_load": [round(x) for x in load], "susp_travel": [round(x, 4) for x in travel],
           "hub_y_body": {"front": round(y_f, 4), "rear": round(y_r, 4)},
           "GRAPHICS_OFFSET": [0.0, round(off_y, 3), round(off_z, 3)], "GRAPHICS_PITCH_ROTATION": round(rot_deg, 2)}
    print(json.dumps(res, indent=2))
    OUT.write_text(json.dumps(res, indent=2))
    print("written", OUT)


if __name__ == "__main__":
    main()
