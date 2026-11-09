"""Nik's pictures against the model from every angle, each pair at the same scale.

    python tools/cmp_views.py out.png [front rear side]

The model is rendered orthographically (tools/gen/ortho_views.py) and each view is scaled so its
silhouette's width matches the picture's, then both are put on a common canvas, picture above, model
below. Scaling on the silhouette rather than on a camera solve means front and rear can be compared
too - there is only a solved camera for the side.
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1]
VIEWS = sys.argv[2:] or ["front", "side", "rear"]


def bbox(a):
    ys, xs = np.where(a[:, :, 3] > 60)
    return xs.min(), xs.max(), ys.min(), ys.max()


def on_white(a):
    al = a[:, :, 3:4].astype(float) / 255.0
    return (a[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)


panels = []
for v in VIEWS:
    ph = cv2.imread(os.path.join(ROOT, "reference", "photos", "grey_studio", v + ".png"),
                    cv2.IMREAD_UNCHANGED)
    md = cv2.imread(os.path.join(ROOT, "export", "match", "ortho_%s.png" % v), cv2.IMREAD_UNCHANGED)
    if ph is None or md is None:
        print("skipping %s (missing picture or render)" % v)
        continue
    px0, px1, py0, py1 = bbox(ph)
    mx0, mx1, my0, my1 = bbox(md)
    s = (px1 - px0 + 1) / float(mx1 - mx0 + 1)
    md2 = cv2.resize(md, (int(round(md.shape[1] * s)), int(round(md.shape[0] * s))),
                     interpolation=cv2.INTER_AREA)
    mx0, mx1, my0, my1 = bbox(md2)
    H = max(py1 - py0, my1 - my0) + 20
    W = (px1 - px0) + 20
    out = []
    for img, (x0, y0, x1, y1) in ((ph, (px0, py0, px1, py1)), (md2, (mx0, my0, mx1, my1))):
        can = np.full((H, W, 3), 255, np.uint8)
        crop = on_white(img)[y0:y1 + 1, x0:x1 + 1][:H - 20, :W - 20]
        can[10:10 + crop.shape[0], 10:10 + crop.shape[1]] = crop
        out.append(can)
    gap = np.full((6, W, 3), 210, np.uint8)
    lab = np.full((22, W, 3), 255, np.uint8)
    cv2.putText(lab, "%s  (picture above, model below; model scaled x%.3f)" % (v, s), (6, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 40, 40), 1, cv2.LINE_AA)
    panels.append(np.vstack([lab, out[0], gap, out[1]]))

w = max(p.shape[1] for p in panels)
pad = [np.pad(p, ((0, 0), (0, w - p.shape[1]), (0, 0)), constant_values=255) for p in panels]
K = 2
big = np.vstack([np.vstack([p, np.full((14, w, 3), 160, np.uint8)]) for p in pad])
cv2.imwrite(OUT, cv2.resize(big, None, fx=K, fy=K, interpolation=cv2.INTER_CUBIC))
print("wrote %s  (%d views)" % (OUT, len(panels)))
