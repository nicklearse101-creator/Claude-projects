"""How far each fitted curve strays from its source polyline (curve -> polyline segments), to catch loops a fit throws
across gaps. Reports lines over LIMIT.

python tools/cad/check_swing.py [lines.json] [lines_fit.json] [limit_mm]
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data", "cad")
R = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "lines_v2.json")))["lines"]
F = json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "lines_v2_fit.json")))["lines"]
LIM = float(sys.argv[3]) / 1000 if len(sys.argv) > 3 else 0.010


def seg_dist(S, P):
    A, B = P[:-1], P[1:]; AB = B - A; L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    out = np.empty(len(S))
    for i in range(0, len(S), 128):
        q = S[i:i + 128, None, :]
        t = np.clip(((q - A) * AB).sum(-1) / L2, 0, 1)
        out[i:i + 128] = np.sqrt(((q - (A + t[..., None] * AB)) ** 2).sum(-1).min(1))
    return out


bad = 0
for n, f in F.items():
    P = np.array(f["src_pts"] if "src_pts" in f else R[n]["pts"], float)     # split runs carry their own source
    S = np.array(f["pts"], float)
    if len(P) < 2:
        continue
    d = seg_dist(S, P)
    if d.max() > LIM:
        bad += 1
        print("%-26s swing %6.1f mm at %s" % (n, d.max() * 1000, np.round(S[np.argmax(d)], 3)))
print("%d of %d lines stray more than %.0f mm from their source polyline" % (bad, len(F), LIM * 1000))
