"""Phase 8 input: window openings read off Nik's grey pictures (Nik 2026-10-20: "the rear windows are not right").
Corner pixels were read by eye from 5-6x crops with a pixel grid (export/match/quarter_win_crop.png,
door_win_crop.png, rear_win_crop.png): the OUTER edge of each black window frame (= the opening in the body) and
the edge of the glass inside it.
Side picture -> model (y, z) with the Phase 2 mapping (solved side camera, plane x 0.65, levelled, y anchored on the
nearest axle, z body-referenced) - same as trace_side_features.py.
Rear picture -> model (x, z): x = (u - 155.5) / 172 (plate 520 mm = 175 px/m, bumper = factory width 169 px/m),
z = (237.5 - v) / 158.6 (tyre contact = ground, roof top = master height).
Writes data/proc/windows.json. Run: .venv\\Scripts\\python.exe tools\\proc\\trace_windows.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace_side_profile as tsp      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AXLE = {"front": -1.141, "rear": 1.202}

SIDE_PX = {   # (u, v) on side.png, polygons front-top -> rear-top -> rear-bottom -> front-bottom
    "door_opening": [(304, 37), (401, 37), (401, 98), (266, 98)],
    "door_glass": [(306, 40), (397, 40), (397, 96), (270, 96)],
    "vent_bar": [(302, 70), (307, 70)],                    # quarter-light divider bar, front / rear face
    "quarter_opening": [(424, 36), (510, 36), (570, 97.5), (424, 97.5)],
    "quarter_glass": [(427, 40), (505, 40), (563, 95), (427, 95)],
}
REAR_PX = {   # (u, v) on rear.png: top-left, top-right, bottom-right, bottom-left
    "rear_opening": [(75, 30), (237, 30), (257, 91), (58, 91)],
    "rear_glass": [(82, 35), (230, 35), (252, 88), (62, 88)],
}


def main():
    raw = json.load(open(os.path.join(ROOT, "data", "proc", "side_profile_raw.json")))
    P = json.load(open(os.path.join(ROOT, "data", "proc", "phase2_geometry.json")))["params"]
    hit = tsp.camera()
    wf = raw["wheel_centres_m"]["front"]
    k, g, b, c = P["roll_slope"], P["ground_m"], P["scale_y"], P["scale_z"]

    def side(u, v):
        half = "front" if u < 330 else "rear"
        y, z = hit(u, v, 0.65)
        zd = z - k * (y - wf[0])
        return [round(AXLE[half] + b * (y - raw["wheel_centres_m"][half][0]), 4), round(c * (zd - g), 4)]

    out = {"side_yz": {n: [side(u, v) for u, v in pts] for n, pts in SIDE_PX.items()},
           "rear_xz": {n: [[round((u - 155.5) / 172, 4), round((237.5 - v) / 158.6, 4)] for u, v in pts]
                       for n, pts in REAR_PX.items()},
           "source": "grey_studio side.png / rear.png, frame outer edges + glass edges read from gridded crops"}
    json.dump(out, open(os.path.join(ROOT, "data", "proc", "windows.json"), "w"), indent=1)
    for grp in ("side_yz", "rear_xz"):
        for n, p in out[grp].items():
            print(grp, n, p)


if __name__ == "__main__":
    main()
