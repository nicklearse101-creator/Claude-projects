"""Same crop of Nik's picture and of the model rendered through that picture's own camera, stacked.

    python tools/cmp_pic.py X0 X1 Y0 Y1 out.png [zoom]

X0..Y1 are pixels of reference/photos/grey_studio/side.png; the render
(export/match/grey_pic_side.png, any multiple of the picture's size) is resampled to match it exactly, so
the two crops are the same piece of car at the same size. Picture on top, model below.
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
x0, x1, y0, y1 = (int(v) for v in sys.argv[1:5])
OUT = sys.argv[5]
K = int(sys.argv[6]) if len(sys.argv) > 6 else 6


def on_white(a):
    if a.shape[2] == 4:
        al = a[:, :, 3:4].astype(float) / 255.0
        return (a[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
    return a


ph = cv2.imread(os.path.join(ROOT, "reference", "photos", "grey_studio", "side.png"), cv2.IMREAD_UNCHANGED)
md = cv2.imread(os.path.join(ROOT, "export", "match", "grey_pic_side.png"), cv2.IMREAD_UNCHANGED)
md = cv2.resize(md, (ph.shape[1], ph.shape[0]), interpolation=cv2.INTER_AREA)
a = cv2.resize(on_white(ph)[y0:y1, x0:x1], None, fx=K, fy=K, interpolation=cv2.INTER_CUBIC)
b = cv2.resize(on_white(md)[y0:y1, x0:x1], None, fx=K, fy=K, interpolation=cv2.INTER_CUBIC)
gap = np.full((8, a.shape[1], 3), 255, np.uint8)
cv2.imwrite(OUT, np.vstack([a, gap, b]))
print("wrote %s  (%d x %d each)" % (OUT, a.shape[1], a.shape[0]))
