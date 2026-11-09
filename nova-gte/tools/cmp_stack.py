"""Photo above, model-over-photo below, for one solved camera - the like-for-like check.

Reads export/match/cmp_<cam>.jpg (written by the comparison step: photo on the left, the model composited over
it on the right) and stacks the two halves, optionally cropped to one area of the car and scaled.

    python tools/cmp_stack.py cam [x0,y0,x1,y1] [scale] [out.jpg]
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cam = sys.argv[1]
box = [int(v) for v in sys.argv[2].split(",")] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(ROOT, "export", "match", "_cmp_%s.jpg" % cam)

im = cv2.imread(os.path.join(ROOT, "export", "match", "cmp_%s.jpg" % cam))
W = im.shape[1] // 2
p, c = im[:, :W], im[:, W:]
if box:
    x0, y0, x1, y1 = box
    p, c = p[y0:y1, x0:x1], c[y0:y1, x0:x1]
sh = np.vstack([p, c])
if scale != 1.0:
    sh = cv2.resize(sh, None, fx=scale, fy=scale,
                    interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
cv2.imwrite(out, sh, [cv2.IMWRITE_JPEG_QUALITY, 92])
print(out, sh.shape)
