"""Measure how far the model's outline is from the real car's edges in each photograph - in pixels and mm.

For every view, points are taken every few pixels along the model's mask contours (export/match/mask_<cam>.png,
from tools/gen/match_overlay.py: outline, window openings, arch gaps). At each point the photo's intensity
gradient is searched along the contour's normal, +-SEARCH px, for the strongest edge; the signed distance to it
is that point's error. The model's line is then drawn 1 px wide and coloured by the error - green under 5 mm,
yellow under 15 mm, red beyond - over the photo at full resolution, and a table is printed per region.

mm per pixel comes from the camera: distance from the camera to the car's middle over the focal length in
pixels. It is the scale at the car's centre, so it is approximate at the near and far ends.

This replaces judging overlays by eye. A strong photo edge can belong to a reflection or a shadow rather than
the panel, so the numbers are read as medians over a region, never point by point.

    python tools/edge_error.py [cam,cam,...]
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "export", "match")
PM = os.path.join(ROOT, "tools", "photomatch")
PH = os.path.join(ROOT, "reference", "photos")
PHOTOS = {
    "c20": os.path.join(PH, "user_red_gte", "redgte_20.webp"),
    "c22": os.path.join(PH, "user_red_gte", "redgte_22.webp"),
    "c23": os.path.join(PH, "user_red_gte", "redgte_23.webp"),
    "c24": os.path.join(PH, "user_red_gte", "redgte_24.webp"),
    "cS": os.path.join(PH, "other_sources", "anglia_side.jpg"),
    "cAR": os.path.join(PH, "other_sources", "anglia_rear.jpg"),
    "cCF": os.path.join(PH, "commons", "1989_Vauxhall_Nova_GTE_1.6_Front.jpg"),
}
SEARCH, STEP = 22, 4
B = json.load(open(os.path.join(PM, "ba_result.json")))


def cam_scale(name, w_render):
    p = np.array(B["cams"][name], float)
    import math
    rv, t, f = p[0:3], p[3:6], p[6]
    ang = np.linalg.norm(rv)
    k = rv / ang
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    R = np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K
    C = -R.T @ t
    dist = float(np.linalg.norm(C - np.array([0.0, 0.0, 0.6])))
    W = json.load(open(os.path.join(PM, "obs.json")))[name]["W"]
    return dist / (f * w_render / W) * 1000.0          # mm per rendered pixel at the car's middle


def load_photo(path, shape):
    im = cv2.imread(path)
    if im is None:
        from PIL import Image
        im = cv2.cvtColor(np.array(Image.open(path).convert("RGB")), cv2.COLOR_RGB2BGR)
    return cv2.resize(im, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)


want = sys.argv[1].split(",") if len(sys.argv) > 1 else list(PHOTOS)
summary = {}
for cam in want:
    mp = os.path.join(M, "mask_%s.png" % cam)
    if not os.path.exists(mp):
        continue
    a = (cv2.imread(mp, cv2.IMREAD_UNCHANGED)[:, :, 3] > 127).astype(np.uint8)
    ph = load_photo(PHOTOS[cam], a.shape)
    g = cv2.GaussianBlur(cv2.cvtColor(ph, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    mmpp = cam_scale(cam, a.shape[1])
    cnts, _ = cv2.findContours(a, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    out = ph.copy()
    errs = []
    H, W = a.shape
    for c in cnts:
        if len(c) < 40:
            continue
        pts = c[:, 0, :].astype(float)
        n = len(pts)
        for i in range(0, n, STEP):
            p0, p1 = pts[(i - 3) % n], pts[(i + 3) % n]
            tvec = p1 - p0
            if np.linalg.norm(tvec) < 1e-6:
                continue
            nrm = np.array([-tvec[1], tvec[0]]) / np.linalg.norm(tvec)
            best, bd = -1.0, 0
            for d in range(-SEARCH, SEARCH + 1):
                q = pts[i] + d * nrm
                x, y = int(round(q[0])), int(round(q[1]))
                if 0 <= x < W and 0 <= y < H and mag[y, x] > best:
                    best, bd = mag[y, x], d
            if best < 8.0:                    # no real edge nearby: do not score it
                continue
            e_mm = abs(bd) * mmpp
            errs.append((pts[i][0], pts[i][1], bd, e_mm))
            col = (60, 200, 60) if e_mm < 5 else (40, 210, 230) if e_mm < 15 else (40, 40, 230)
            x0, y0 = int(pts[i][0]), int(pts[i][1])
            x1, y1 = int(pts[min(i + STEP, n - 1)][0]), int(pts[min(i + STEP, n - 1)][1])
            cv2.line(out, (x0, y0), (x1, y1), col, 1, cv2.LINE_AA)
    e = np.array([r[3] for r in errs]) if errs else np.zeros(1)
    summary[cam] = (len(errs), float(np.median(e)), float(np.percentile(e, 90)), float((e < 5).mean()),
                    float((e > 15).mean()), mmpp)
    cv2.imwrite(os.path.join(M, "err_%s.png" % cam), out)

print("view   samples  median   90th   <5mm   >15mm   (mm/px)")
for cam, (k, med, p90, ok, bad, s) in summary.items():
    print("%-5s  %6d  %5.1f mm %5.1f mm  %3.0f%%   %3.0f%%    (%.2f)" % (cam, k, med, p90, ok * 100, bad * 100, s))
print("wrote export/match/err_<cam>.png - model line coloured by error: green <5 mm, yellow <15, red >15")
