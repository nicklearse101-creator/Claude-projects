"""Draw the model's mask edges (export/match/mask_<cam>.png, from tools/gen/match_overlay.py) onto each photo.

    python tools/overlay_edges.py [cam,cam,...]

Writes export/match/edges_<cam>.png: the photograph with the model's outline, window openings and arch lips in
cyan. Lines on the car's own lines = the shape matches there.
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "export", "match")
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
want = sys.argv[1].split(",") if len(sys.argv) > 1 else list(PHOTOS)
for cam in want:
    mp = os.path.join(M, "mask_%s.png" % cam)
    if not os.path.exists(mp):
        print("no mask for", cam); continue
    mask = cv2.imread(mp, cv2.IMREAD_UNCHANGED)
    a = (mask[:, :, 3] > 127).astype(np.uint8)
    ph = cv2.imread(PHOTOS[cam])
    if ph is None:
        from PIL import Image
        ph = cv2.cvtColor(np.array(Image.open(PHOTOS[cam]).convert("RGB")), cv2.COLOR_RGB2BGR)
    ph = cv2.resize(ph, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    cnts, _ = cv2.findContours(a, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    out = ph.copy()
    cv2.drawContours(out, [c for c in cnts if len(c) > 25], -1, (255, 255, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(M, "edges_%s.png" % cam), out)
    print("wrote edges_%s.png  (%d contours)" % (cam, len([c for c in cnts if len(c) > 25])))
