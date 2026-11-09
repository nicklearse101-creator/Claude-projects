"""Gridded crop of a solved photo at the camera's working resolution (obs.json W x H), for reading pixel marks.

python tools/photomatch/grid_photo.py <cam> <out.jpg> x0 y0 x1 y1 [scale] [step]
Optionally overlay 3D points (model frame) from a JSON list in env MARK_PTS: [[name, x, y, z], ...] (green crosses).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
B = json.load(open(os.path.join(HERE, "ba_result.json"))); O = json.load(open(os.path.join(HERE, "obs.json")))
PH = {"c20": "user_red_gte/redgte_20.webp", "c22": "user_red_gte/redgte_22.webp", "c23": "user_red_gte/redgte_23.webp",
      "c24": "user_red_gte/redgte_24.webp", "cS": "other_sources/anglia_side.jpg", "cAR": "other_sources/anglia_rear.jpg",
      "cCF": "commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg"}
c, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = (int(a) for a in sys.argv[3:7])
S = float(sys.argv[7]) if len(sys.argv) > 7 else 3.0
step = int(sys.argv[8]) if len(sys.argv) > 8 else 10
W, H = O[c]["W"], O[c]["H"]
im = Image.open(os.path.join(ROOT, "reference", "photos", PH[c])).convert("RGB").resize((W, H))
cr = im.crop((x0, y0, x1, y1)).resize((int((x1 - x0) * S), int((y1 - y0) * S)), Image.LANCZOS)
d = ImageDraw.Draw(cr)
for X in range((x0 // step) * step, x1 + 1, step):
    if X < x0:
        continue
    maj = X % (5 * step) == 0
    d.line([((X - x0) * S, 0), ((X - x0) * S, cr.size[1])], fill=(255, 0, 0) if maj else (0, 170, 255))
    if maj:
        d.text(((X - x0) * S + 2, 2), str(X), fill=(255, 255, 0))
for Y in range((y0 // step) * step, y1 + 1, step):
    if Y < y0:
        continue
    maj = Y % (5 * step) == 0
    d.line([(0, (Y - y0) * S), (cr.size[0], (Y - y0) * S)], fill=(255, 0, 0) if maj else (0, 170, 255))
    if maj:
        d.text((2, (Y - y0) * S + 2), str(Y), fill=(255, 255, 0))
if os.environ.get("MARK_PTS"):
    p = np.array(B["cams"][c]); R, _ = cv2.Rodrigues(p[0:3]); t = p[3:6]; f, k1 = p[6], p[7]
    for nm, *X in json.loads(os.environ["MARK_PTS"]):
        Q = np.array(X, float); Q[2] -= 0.0193
        Xc = R @ Q + t; xx, yy = Xc[0] / Xc[2], Xc[1] / Xc[2]; r2 = xx * xx + yy * yy
        u, v = W / 2 + f * xx * (1 + k1 * r2), H / 2 + f * yy * (1 + k1 * r2)
        U, Vv = (u - x0) * S, (v - y0) * S
        d.line([(U - 8, Vv), (U + 8, Vv)], fill=(0, 255, 0), width=2); d.line([(U, Vv - 8), (U, Vv + 8)], fill=(0, 255, 0), width=2)
        d.text((U + 6, Vv + 4), nm, fill=(0, 255, 0))
cr.save(out, quality=90)
print("wrote", out, cr.size)
