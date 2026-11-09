"""Lay a model render from render_rect.py on a drawing view from views.py (same world rectangle, same pixels).

Drawing ink in red, the model as translucent grey with its outline in blue. Anything that does not line up is a
real difference between the model and the drawing - or a calibration error in views.py, which is why every new
calibration is checked here against the model's photo-verified side first.

python tools/cad/overlay.py render_dir out_dir [view,...]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RD, OD = sys.argv[1], sys.argv[2]
WANT = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
F = json.load(open(os.path.join(ROOT, "reference", "views", "frame.json")))
KIND = {"ga_side": "side", "bp_side": "side", "ga_front": "front", "bp_front": "front", "ga_rear": "rear",
        "ga_plan": "plan"}
os.makedirs(OD, exist_ok=True)
for name, v in F["views"].items():
    if WANT and name not in WANT:
        continue
    rp = os.path.join(RD, "rect_%s.png" % KIND[name])
    if not os.path.exists(rp):
        continue
    d = np.array(Image.open(os.path.join(ROOT, "reference", "views", v["file"])).convert("L"), float)
    m = Image.open(rp).convert("RGBA")
    a = np.array(m)[:, :, 3].astype(float) / 255.0
    out = np.full(d.shape + (3,), 255.0)
    ink = np.clip((170 - d) / 120.0, 0, 1)
    out = out * (1 - ink[..., None]) + np.array([200, 30, 30]) * ink[..., None]
    out = out * (1 - 0.35 * a[..., None]) + np.array([90, 92, 95]) * (0.35 * a[..., None])
    edge = np.array(Image.fromarray((a > 0.5).astype(np.uint8) * 255).filter(ImageFilter.FIND_EDGES)) > 0
    out[edge] = (20, 90, 230)
    Image.fromarray(out.astype(np.uint8)).save(os.path.join(OD, "ov_%s.png" % name))
    print("wrote ov_%s.png" % name)
