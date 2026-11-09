"""Draw the SHELL_MAP outlines + labels (blender/scripts/shell_map.py) on the orthographic cavity renders."""
import importlib.util
import json
import os

from PIL import Image, ImageDraw, ImageFont

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(R, "export", "ref", "scan")
spec = importlib.util.spec_from_file_location("shell_map", os.path.join(R, "blender", "scripts", "shell_map.py"))
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
meta = json.load(open(os.path.join(D, "cav_meta.json")))
VIEW = {"L": "side_L", "R": "side_R", "F": "front", "B": "rear", "T": "top"}
try:
    FONT = ImageFont.truetype("arialbd.ttf", 22)
except OSError:
    FONT = ImageFont.load_default()
ims = {v: Image.open(os.path.join(D, "cav_%s.png" % v)).convert("RGB") for v in VIEW.values()}
drw = {v: ImageDraw.Draw(im) for v, im in ims.items()}


def px(view, a, b):
    m = meta[view]; s = m["px_per_m"]; u0, u1 = m["u"]; v0, v1 = m["v"]
    x = (u1 - a) * s if view in ("side_R", "rear") else (a - u0) * s
    return x, (v1 - b) * s


for name, kind, plane, pts, _ in sm.F:
    view = VIEW[plane]
    col = tuple(int(c * 255) for c in sm.KIND_COL[kind])
    P = [px(view, a, b) for a, b in pts]
    drw[view].line(P, fill=col, width=4)
    if name:
        x = min(p[0] for p in P); y = min(p[1] for p in P)
        drw[view].text((x + 2, y - 26), name, fill=col, font=FONT, stroke_width=3, stroke_fill=(0, 0, 0))
for v, im in ims.items():
    im.save(os.path.join(D, "MAP_%s.jpg" % v), quality=90)
print("ok")
