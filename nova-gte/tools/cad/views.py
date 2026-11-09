"""The measurement foundation (REPLICA_PLAN step 3): every drawing view resampled into ONE world frame.

Frame (as the whole project): car faces -Y, Z up, +X is the car's left, origin on the ground midway between the axles
(y = +-1.1715), unloaded tyres (photo/BA z + 0.0193 = model z). Each view is written as an image covering a fixed
world rectangle at PPM px per metre, so a pixel means the same thing in every view and in every model render made by
tools/cad/render_rect.py. `reference/views/frame.json` records each rectangle, the axes and where every number came
from.

Calibrations (read 2026-10-27 off pixel-gridded crops, export/map/ga_*_grid.jpg, and the existing tracers):
  GA sheet (GA_rectified.png - photographed and de-keystoned, so each axis carries its own scale; the paper is not
  flat and the across-car scale differs from the along-car one by ~12%):
    side   along 3.4970 mm/px from its wheelbase marks (670 px = 2343), front axle px 1114 (wheel centre read
           1113.3); ground row 521 (tyre bottoms and ground line); vertical 1365 mm / (521 - 174) px = 3.934 mm/px
    plan   along as the side (shared sheet x); centreline row 928 (trace_plan.py); across 4.001 mm/px - one
           scale fitted to the FIA widths in trace_plan.py; +x (car's left) is DOWN the sheet (the LHD steering
           wheel is in the lower half)
    front  centreline x 2464.8 (dash-dot line 2464; widest-body midpoint 2464.8); ground row 515; vertical
           1365 / 354 px = 3.856 mm/px; across 1532 mm / 447.5 px (widest body, mirrors excluded) = 3.423 mm/px;
           image right = +x (seen from the front)
    rear   centreline x 440.5; ground row 513.5; vertical 1365 / 351 px = 3.889 mm/px; across 1532 / 441 px =
           3.474 mm/px; image right = -x (seen from behind). Check: its 800 mm lamp-top mark reads 815 (2%).
  Line blueprint corsa_a_4view_blueprint.gif (secondary: overhangs 83 mm short; good between the axles):
    side   5.36156 mm/px both ways, front axle px 145, ground py 264.6 (tyre fit) - as tools/trace_side.py
    front  5.36156 mm/px both ways (same drawing scale; body width reads 1517 vs 1532, 1%), centreline x 940.5,
           ground py 270; image right = +x

The GA sheet is the Nov 1990 facelift: hard points, apertures, glass and plan shape only (DECISIONS (16)).

    python tools/cad/views.py            -> reference/views/*.png + frame.json
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BP = os.path.join(ROOT, "reference", "blueprints")
OUT = os.path.join(ROOT, "reference", "views")
os.makedirs(OUT, exist_ok=True)
PPM = 500.0
Y_FA = -1.1715

SIDE_RECT = (-2.00, 2.00, -0.05, 1.45)          # y0 y1 z0 z1
END_RECT = (-1.00, 1.00, -0.05, 1.45)           # x0 x1 z0 z1
PLAN_RECT = (-2.00, 2.00, -1.00, 1.00)          # y0 y1 x0 x1

VIEWS = {
    "ga_side": dict(src="GA_rectified.png", kind="side", px_fa=1114.0, mpp_u=3.4970e-3, ground=521.0, mpp_v=3.934e-3),
    "ga_plan": dict(src="GA_rectified.png", kind="plan", px_fa=1114.0, mpp_u=3.4970e-3, row_c=928.0, mpp_v=4.001e-3),
    "ga_front": dict(src="GA_rectified.png", kind="front", col_c=2464.8, mpp_u=3.423e-3, ground=515.0, mpp_v=3.856e-3),
    "ga_rear": dict(src="GA_rectified.png", kind="rear", col_c=440.5, mpp_u=3.474e-3, ground=513.5, mpp_v=3.889e-3),
    "bp_side": dict(src="corsa_a_4view_blueprint.gif", kind="side", px_fa=145.0, mpp_u=5.36156e-3, ground=264.6,
                    mpp_v=5.36156e-3),
    "bp_front": dict(src="corsa_a_4view_blueprint.gif", kind="front", col_c=940.5, mpp_u=5.36156e-3, ground=270.0,
                     mpp_v=5.36156e-3),
}


def grid(rect):
    a0, a1, b0, b1 = rect
    W = int(round((a1 - a0) * PPM)); H = int(round((b1 - b0) * PPM))
    return W, H, a0 + (np.arange(W) + 0.5) / PPM, b1 - (np.arange(H) + 0.5) / PPM


def build(name, c):
    src = np.array(Image.open(os.path.join(BP, c["src"])).convert("L"), float)
    if c["kind"] == "side":                       # u = y (front at the left), v = z
        W, H, ys, zs = grid(SIDE_RECT)
        pu = c["px_fa"] + (ys - Y_FA) / c["mpp_u"]
        pv = c["ground"] - zs / c["mpp_v"]
        rect, axes = SIDE_RECT, "u = y (right = rearward), v = z (up)"
    elif c["kind"] == "plan":                     # u = y, v = x with +x DOWN (as the sheet)
        W, H, ys, xs_desc = grid(PLAN_RECT)
        xs = xs_desc[::-1]                        # row 0 = x0 (car's right, -x), last row = x1 (+x, car's left)
        pu = c["px_fa"] + (ys - Y_FA) / c["mpp_u"]
        pv = c["row_c"] + xs / c["mpp_v"]
        rect, axes = PLAN_RECT, "u = y (right = rearward), v = x (DOWN = +x, the car's left)"
    else:                                         # front: u = x (right = +x); rear: u = -x (seen from behind)
        W, H, xs, zs = grid(END_RECT)
        sgn = 1.0 if c["kind"] == "front" else -1.0
        pu = c["col_c"] + sgn * xs / c["mpp_u"]
        pv = c["ground"] - zs / c["mpp_v"]
        rect = END_RECT
        axes = "u = x (right = +x, seen from the front), v = z" if sgn > 0 else \
               "u = -x (right = -x, seen from behind), v = z"
    PU, PV = np.meshgrid(pu, pv)
    x0 = np.clip(np.floor(PU).astype(int), 0, src.shape[1] - 2); y0 = np.clip(np.floor(PV).astype(int), 0, src.shape[0] - 2)
    fx = np.clip(PU - x0, 0, 1); fy = np.clip(PV - y0, 0, 1)
    img = (src[y0, x0] * (1 - fx) * (1 - fy) + src[y0, x0 + 1] * fx * (1 - fy) +
           src[y0 + 1, x0] * (1 - fx) * fy + src[y0 + 1, x0 + 1] * fx * fy)
    out = (PU < 0) | (PU > src.shape[1] - 1) | (PV < 0) | (PV > src.shape[0] - 1)
    img[out] = 255
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name + ".png"))
    return {"file": name + ".png", "rect": rect, "ppm": PPM, "size": [W, H], "axes": axes,
            "source": c["src"], "calibration": {k: v for k, v in c.items() if k != "src"}}


frame = {"_doc": __doc__.split("\n\n")[0], "frame": "car faces -Y, Z up, +X = car's left, origin on the ground "
         "midway between the axles (y +-1.1715), unloaded tyres; photo/BA z + 0.0193 = model z", "views": {}}
for n, c in VIEWS.items():
    frame["views"][n] = build(n, c)
    print("%-9s %s  %dx%d px" % (n, frame["views"][n]["axes"], *frame["views"][n]["size"]))
json.dump(frame, open(os.path.join(OUT, "frame.json"), "w"), indent=1)
print("wrote", os.path.join(OUT, "frame.json"))
