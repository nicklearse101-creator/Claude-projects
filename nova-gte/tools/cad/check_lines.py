"""Draw the character-line network on every drawing view (orthographic, reference/views) and every solved photo
(BA cameras), so each line can be judged against the real car before any surface is built.

python tools/cad/check_lines.py [lines.json] [outdir]
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LJ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "blender", "data", "cad", "lines_v1.json")
OD = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "export", "cad", "lines_check")
os.makedirs(OD, exist_ok=True)
N = json.load(open(LJ))
F = json.load(open(os.path.join(ROOT, "reference", "views", "frame.json")))
PM = os.path.join(ROOT, "tools", "photomatch")
B = json.load(open(os.path.join(PM, "ba_result.json"))); O = json.load(open(os.path.join(PM, "obs.json")))
DZ = 0.0193
COL = {"centre": (255, 210, 0), "body": (0, 200, 230), "crease": (240, 0, 200), "shut": (0, 200, 60),
       "arch": (255, 130, 0), "dlo": (40, 90, 255), "roof": (150, 60, 220), "plan": (120, 120, 120),
       "front": (230, 20, 20), "rear": (230, 20, 20)}
PH = {"c20": "user_red_gte/redgte_20.webp", "c22": "user_red_gte/redgte_22.webp", "c23": "user_red_gte/redgte_23.webp",
      "c24": "user_red_gte/redgte_24.webp", "cS": "other_sources/anglia_side.jpg", "cAR": "other_sources/anglia_rear.jpg",
      "cCF": "commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg"}


def both(P):
    P = np.asarray(P, float)
    return [P, P * np.array([-1.0, 1, 1])]


def view_proj(name, v):
    a0, a1, b0, b1 = v["rect"]; ppm = v["ppm"]
    if name.endswith("side"):
        return lambda P: np.c_[(P[:, 1] - a0) * ppm, (b1 - P[:, 2]) * ppm], lambda P: P[:, 0] >= -1e-6
    if name.endswith("plan"):
        return lambda P: np.c_[(P[:, 1] - a0) * ppm, (P[:, 0] - b0) * ppm], lambda P: np.ones(len(P), bool)
    if name.endswith("front"):
        return lambda P: np.c_[(P[:, 0] - a0) * ppm, (b1 - P[:, 2]) * ppm], lambda P: np.ones(len(P), bool)
    return lambda P: np.c_[(-P[:, 0] - a0) * ppm, (b1 - P[:, 2]) * ppm], lambda P: np.ones(len(P), bool)


def cam_proj(c):
    p = np.array(B["cams"][c]); R, _ = cv2.Rodrigues(p[0:3]); t = p[3:6]; f, k1 = p[6], p[7]
    W, H = O[c]["W"], O[c]["H"]
    C = -R.T @ t

    def proj(P):
        Q = P.copy(); Q[:, 2] -= DZ
        X = (R @ Q.T).T + t
        x, y = X[:, 0] / X[:, 2], X[:, 1] / X[:, 2]; r2 = x * x + y * y
        return np.c_[W / 2 + f * x * (1 + k1 * r2), H / 2 + f * y * (1 + k1 * r2)]

    # draw only the half facing the camera
    return proj, (lambda P: np.sign(P[:, 0] + 1e-9) == np.sign(C[0]) if abs(C[0]) > 1.0 else np.ones(len(P), bool)), (W, H)


ONLY = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None     # draw only these groups / line names
COL.update({"model_parts": (235, 235, 235), "envelope": (0, 255, 255)})


def draw(img, proj, vis, width, photo=False):
    d = ImageDraw.Draw(img)
    for n, l in N["lines"].items():
        if ONLY and l["group"] not in ONLY and n not in ONLY:
            continue
        if photo and l["group"] == "envelope":          # silhouettes are not lines on the body: views only
            continue
        for P in both(l["pts"]):
            m = vis(P)
            if m.sum() < 2:
                continue
            q = proj(P[m])
            d.line([tuple(p) for p in q], fill=COL.get(l["group"], (255, 255, 255)), width=width)
    for k, p in N["points"].items():
        for P in both([p]):
            if not vis(P)[0]:
                continue
            u, v = proj(P)[0]
            r = 5 * width
            d.ellipse([u - r, v - r, u + r, v + r], outline=(255, 0, 0) if k not in N["single_view_points"] else (255, 0, 255),
                      width=width)
    return img


for name, v in F["views"].items():
    img = Image.open(os.path.join(ROOT, "reference", "views", v["file"])).convert("RGB")
    img = Image.blend(img, Image.new("RGB", img.size, "white"), 0.45)
    proj, vis = view_proj(name, v)
    draw(img, proj, vis, 2).save(os.path.join(OD, "L_%s.jpg" % name), quality=88)
for c, f in PH.items():
    proj, vis, (W, H) = cam_proj(c)
    img = Image.open(os.path.join(ROOT, "reference", "photos", f)).convert("RGB").resize((W, H))
    draw(img, proj, vis, 2, photo=True).save(os.path.join(OD, "L_%s.jpg" % c), quality=88)
print("wrote", OD)
