"""Draw a world-coordinate grid on a reference/views image (or a crop of it), for reading trace guide points.

python tools/cad/grid_view.py ga_rear out.jpg [u0 u1 v0 v1] [scale] [step_m]
  u/v are world coordinates of the view's axes (see frame.json 'axes'); default = the whole view.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "reference", "views")
F = json.load(open(os.path.join(V, "frame.json")))["views"]
name, out = sys.argv[1], sys.argv[2]
v = F[name]; r0, r1, c0, c1 = v["rect"]; ppm = v["ppm"]
im = Image.open(os.path.join(V, v["file"])).convert("RGB")
W, H = im.size
plan = v["axes"].startswith("u = y") and "DOWN" in v["axes"]
flipu = v["axes"].startswith("u = -x")


def to_px(u, w):
    i = (u - r0) * ppm if not flipu else (r1 - u) * ppm
    j = (w - c0) * ppm if plan else (c1 - w) * ppm
    return i, j


u0, u1, w0, w1 = (float(a) for a in sys.argv[3:7]) if len(sys.argv) >= 7 else (r0, r1, c0, c1)
S = float(sys.argv[7]) if len(sys.argv) >= 8 else 1.0
step = float(sys.argv[8]) if len(sys.argv) >= 9 else 0.05
(ia, ja), (ib, jb) = to_px(u0, w0), to_px(u1, w1)
box = (int(min(ia, ib)), int(min(ja, jb)), int(max(ia, ib)), int(max(ja, jb)))
c = im.crop(box).resize((int((box[2] - box[0]) * S), int((box[3] - box[1]) * S)), Image.LANCZOS)
d = ImageDraw.Draw(c)
import math
k0 = math.floor(min(u0, u1) / step); k1 = math.ceil(max(u0, u1) / step)
for k in range(k0, k1 + 1):
    u = k * step; i, _ = to_px(u, w0); x = (i - box[0]) * S
    major = abs(round(u / 0.1) * 0.1 - u) < 1e-9
    d.line([(x, 0), (x, c.size[1])], fill=(255, 0, 0) if major else (0, 170, 255), width=1)
    if major:
        d.text((x + 2, 2), "%+.2f" % u, fill=(255, 0, 0))
k0 = math.floor(min(w0, w1) / step); k1 = math.ceil(max(w0, w1) / step)
for k in range(k0, k1 + 1):
    w = k * step; _, j = to_px(u0, w); y = (j - box[1]) * S
    major = abs(round(w / 0.1) * 0.1 - w) < 1e-9
    d.line([(0, y), (c.size[0], y)], fill=(255, 0, 0) if major else (0, 170, 255), width=1)
    if major:
        d.text((2, y + 2), "%.2f" % w, fill=(255, 0, 0))
c.save(out, quality=90)
print("wrote", out, c.size)
