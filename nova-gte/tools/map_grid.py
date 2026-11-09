"""Overlay a car-frame grid (every 0.1 m, labelled) on the orthographic cavity renders (export/ref/scan/cav_*.png)."""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "export", "ref", "scan")
meta = json.load(open(os.path.join(D, "cav_meta.json")))
AX = {"side_L": ("y", "z"), "side_R": ("y", "z"), "front": ("x", "z"), "rear": ("x", "z"), "top": ("x", "y")}
try:
    F = ImageFont.truetype("arial.ttf", 18)
except OSError:
    F = ImageFont.load_default()
for name, m in meta.items():
    im = Image.open(os.path.join(D, "cav_%s.png" % name)).convert("RGB")
    d = ImageDraw.Draw(im)
    s = m["px_per_m"]; u0, u1 = m["u"]; v0, v1 = m["v"]
    flip_u = name in ("side_R", "rear")          # camera looks the other way: u runs right-to-left
    def px(u, v):
        x = (u1 - u) * s if flip_u else (u - u0) * s
        return x, (v1 - v) * s
    k = int(u0 * 10) - 1
    while k / 10 <= u1 + 1e-9:
        u = k / 10
        if u >= u0:
            x, _ = px(u, v0)
            d.line([(x, 0), (x, im.height)], fill=(255, 60, 60) if k % 5 == 0 else (230, 160, 0), width=2 if k % 5 == 0 else 1)
            d.text((x + 3, 3), "%s%+.1f" % (AX[name][0], u), fill=(255, 255, 0), font=F)
        k += 1
    k = int(v0 * 10) - 1
    while k / 10 <= v1 + 1e-9:
        v = k / 10
        if v >= v0:
            _, y = px(u0, v)
            d.line([(0, y), (im.width, y)], fill=(255, 60, 60) if k % 5 == 0 else (230, 160, 0), width=2 if k % 5 == 0 else 1)
            d.text((3, y + 2), "%s%.1f" % (AX[name][1], v), fill=(0, 255, 255), font=F)
        k += 1
    im.save(os.path.join(D, "grid_%s.jpg" % name), quality=88)
print("ok")
