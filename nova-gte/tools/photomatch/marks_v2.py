"""New two-view photo marks (2026-10-27), triangulated with the BA cameras -> blender/data/cad/marks_v2.json.

Only POINT features are triangulated (a badge, a lock): an edge seen in two photos cannot be pinned along its own
direction, and the rear-glass bottom edge and the tailgate's lower edge run almost parallel to the epipolar line
in cAR, so their depth is unreliable - those were tried and rejected (see DECISIONS 2026-10-27 (21)).
Pixels are at each camera's working size (obs.json W x H), read from 10x gridded crops (grid_photo.py).
The 'gap' is the closest distance between the two rays: the consistency of the pair of marks.

python tools/photomatch/marks_v2.py
"""
import json
import os

from epi import tri

HERE = os.path.dirname(os.path.abspath(__file__))
MARKS = {
    # name: (camA, uA, vA, camB, uB, vB, what)
    "LOCK_R": ("c24", 629.0, 476.0, "cAR", 1149.0, 512.0, "tailgate lock barrel recess, centre (on the grey bar)"),
    "BADGE_R": ("c24", 627.8, 408.8, "cAR", 1128.0, 465.0, "Vauxhall griffin badge on the tailgate, centre"),
}
out = {}
for k, (a, ua, va, b, ub, vb, what) in MARKS.items():
    P, gap, ang = tri(a, ua, va, b, ub, vb)
    out[k] = {"xyz_model": [round(float(v), 4) for v in P], "ray_gap_mm": round(gap * 1000, 1), "angle_deg": round(ang),
              "marks": {a: [ua, va], b: [ub, vb]}, "what": what}
    print("%-8s %s  gap %.1f mm  angle %.0f" % (k, out[k]["xyz_model"], gap * 1000, ang))
json.dump({"_doc": __doc__.split("\n\n")[0], "frame": "model (photo z + 0.0193)", "points": out},
          open(os.path.join(HERE, "..", "..", "blender", "data", "cad", "marks_v2.json"), "w"), indent=1)
