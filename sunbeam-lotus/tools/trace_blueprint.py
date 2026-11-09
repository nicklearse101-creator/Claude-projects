"""Trace the Sunbeam Lotus blueprint preview into car-space profiles (metres).

Car space matches the .blend: car faces -Y, +X = car's left, Z up, ground Z=0,
origin midway between the axles. Scale and anchors were measured by hand off
the blueprint's own dimension lines (see memory / project notes):
  2413 mm wheelbase line = px 261..676.5  ->  S = 2.413 / 415.5 m/px
  side & front views: ground at px y 330;  rear view: ground at px y 748
  front view centreline px x 1055, rear 1056, top view centreline px y 626

Pixel classes: the drawing's body fill is beige (R-B >= 6); outlines, bumpers,
tyres are dark; the watermark and glass are neutral light grey, background white.

Writes profiles.json next to this script and an overlay PNG per view so the
trace can be checked by eye.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
SRC = HERE.parent / "refs" / "blueprints" / "the-blueprints_preview-wm_talbot_sunbeam_lotus_1979.jpg"
S = 2.413 / 415.5
AXLE_PX, YF = 261.0, -2.413 / 2

im = Image.open(SRC).convert("RGB")
px = im.load()

def beige(x, y):
    r, g, b = px[x, y]
    return r - b >= 6 and r < 252

def solid(x, y):
    r, g, b = px[x, y]
    return beige(x, y) or max(r, g, b) < 170

def y_of(x):
    return YF + (x - AXLE_PX) * S

profiles = {}

# --- side view: roof/bonnet/hatch top line and body (beige) bottom line per station
side = []
for x in range(105, 826):
    col = range(82, 334)
    top = next((y for y in col if solid(x, y)), None)
    bot = next((y for y in reversed(col) if beige(x, y)), None)
    if top is not None and bot is not None:
        side.append({"y": round(y_of(x), 4), "z_top": round((330 - top) * S, 4), "z_bot": round((330 - bot) * S, 4), "px": x})
profiles["side"] = side

# --- top view: plan half-width from the car's LEFT edge (image bottom); right edge has mirror + aerial
top = []
for x in range(105, 812):
    col = range(472, 783)
    upper = next((y for y in col if solid(x, y)), None)
    lower = next((y for y in reversed(col) if solid(x, y)), None)
    if upper is not None and lower is not None:
        top.append({"y": round(y_of(x), 4), "half_w_left": round((lower - 626) * S, 4), "half_w_right": round((626 - upper) * S, 4), "px": x})
profiles["top"] = top

# --- front / rear views: half-width vs height from the car's LEFT side (mirror is on the right)
def section(x_range, y_range, ground, centre, left_is_image_right):
    rows = []
    for y in y_range:
        xs = [x for x in x_range if solid(x, y)]
        if not xs:
            continue
        edge = max(xs) if left_is_image_right else min(xs)
        rows.append({"z": round((ground - y) * S, 4), "half_w": round(abs(edge - centre) * S, 4), "px": y})
    return rows

profiles["front"] = section(range(1056, 1212), range(82, 334), 330, 1055, True)
profiles["rear"] = section(range(897, 1056), range(502, 752), 748, 1056, False)

(HERE / "profiles.json").write_text(json.dumps(profiles, indent=1))

# overlays for checking by eye
ov = im.copy(); d = ImageDraw.Draw(ov)
for p in side:
    d.point((p["px"], 330 - p["z_top"] / S), fill=(255, 0, 0)); d.point((p["px"], 330 - p["z_bot"] / S), fill=(0, 0, 255))
for p in top:
    d.point((p["px"], 626 + p["half_w_left"] / S), fill=(255, 0, 0)); d.point((p["px"], 626 - p["half_w_right"] / S), fill=(0, 160, 0))
for p in profiles["front"]:
    d.point((1055 + p["half_w"] / S, p["px"]), fill=(255, 0, 0))
for p in profiles["rear"]:
    d.point((1056 - p["half_w"] / S, p["px"]), fill=(255, 0, 0))
ov.save(HERE / "trace_overlay.png")
print({k: len(v) for k, v in profiles.items()})
