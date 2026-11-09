"""Put the model's orthographic side render and the calibrated blueprint in the same world rectangle.

tools/gen/side_ortho.py renders the model over an exact world rect; this resamples the blueprint's side
elevation into that same rect using the calibration in tools/trace_side.py, so the two can be flicked
between or blended. Anything that does not line up here is a real difference, not a framing artefact.

    python tools/blueprint_overlay.py model_side.png out.png
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL, OUT = sys.argv[1], sys.argv[2]

Y0, Y1, Z0, Z1, PPM = -1.95, 1.95, -0.05, 1.50, 400      # must match tools/gen/side_ortho.py
MPP = 5.36156 / 1000.0
PX_FA, Y_FA, PY_GROUND = 145, -1.1715, 264.6

bp = Image.open(os.path.join(ROOT, "reference", "blueprints",
                             "corsa_a_4view_blueprint.gif")).convert("L")
B = np.array(bp)

model = Image.open(MODEL).convert("RGBA")
W, H = model.size
# world coordinate of each output pixel, then the blueprint pixel it comes from
ys = Y0 + (np.arange(W) + 0.5) / PPM
zs = Z1 - (np.arange(H) + 0.5) / PPM
pxs = np.clip(np.round(PX_FA + (ys - Y_FA) / MPP).astype(int), 0, B.shape[1] - 1)
pys = np.clip(np.round(PY_GROUND - zs / MPP).astype(int), 0, B.shape[0] - 1)
bl = B[np.ix_(pys, pxs)]

out = np.zeros((H, W, 3), np.uint8)
out[:] = 255
ink = bl < 150
out[ink] = (210, 40, 40)                       # blueprint in red

M = np.array(model).astype(float)
a = (M[:, :, 3:4] / 255.0) * 0.72              # model in grey over it
out = (out * (1 - a) + M[:, :, :3] * a).astype(np.uint8)
out[ink] = (210, 40, 40)                       # keep the blueprint lines on top

Image.fromarray(out).save(OUT)
print("wrote %s  (%dx%d, rect y %.2f..%.2f z %.2f..%.2f)" % (OUT, W, H, Y0, Y1, Z0, Z1))
