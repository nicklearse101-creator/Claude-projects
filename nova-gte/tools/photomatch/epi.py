"""Two-view marking: show where a pixel marked in camera A can lie in camera B (its epipolar line), then triangulate.

  python tools/photomatch/epi.py show A uA vA B out.jpg [d0 d1]    gridded crop of B around the epipolar line,
        with ticks every 2 cm of depth along A's ray (labelled with the model y of that point)
  python tools/photomatch/epi.py tri  A uA vA B uB vB              triangulate: closest point of the two rays,
        printed in the model frame (+dz) with the gap between the rays (the mark's consistency)
Model frame z = photo z + 0.0193.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
import raycam  # noqa: E402

B = json.load(open("ba_result.json")); O = json.load(open("obs.json"))
DZ = 0.0193


def proj(c, X):
    p = np.array(B["cams"][c]); R, _ = cv2.Rodrigues(p[0:3]); t = p[3:6]; f, k1 = p[6], p[7]
    Xc = R @ np.asarray(X, float) + t; x, y = Xc[0] / Xc[2], Xc[1] / Xc[2]; r2 = x * x + y * y
    return np.array([O[c]["W"] / 2 + f * x * (1 + k1 * r2), O[c]["H"] / 2 + f * y * (1 + k1 * r2)]), Xc[2]


def tri(a, ua, va, b, ub, vb):
    Ca, da = raycam.ray(a, ua, va); Cb, db = raycam.ray(b, ub, vb)
    w = Ca - Cb; A_ = da @ da; B_ = da @ db; C_ = db @ db; D_ = da @ w; E_ = db @ w
    den = A_ * C_ - B_ * B_
    s = (B_ * E_ - C_ * D_) / den; t = (A_ * E_ - B_ * D_) / den
    Pa, Pb = Ca + s * da, Cb + t * db
    P = (Pa + Pb) / 2; P[2] += DZ
    ang = np.degrees(np.arccos(abs(da @ db)))
    return P, float(np.linalg.norm(Pa - Pb)), ang


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "tri":
        a, ua, va, b, ub, vb = sys.argv[2], *map(float, sys.argv[3:5]), sys.argv[5], *map(float, sys.argv[6:8])
        P, gap, ang = tri(a, ua, va, b, ub, vb)
        print("model xyz %.4f %.4f %.4f   ray gap %.1f mm   angle %.0f deg" % (*P, gap * 1000, ang))
    else:
        a, ua, va, b, out = sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]
        d0, d1 = (float(sys.argv[7]), float(sys.argv[8])) if len(sys.argv) > 8 else (1.0, 8.0)
        C, d = raycam.ray(a, ua, va)
        pts = []
        for s in np.arange(d0, d1, 0.02):
            X = C + s * d; uv, depth = proj(b, X)
            if depth > 0 and 0 <= uv[0] < O[b]["W"] and 0 <= uv[1] < O[b]["H"]:
                pts.append((s, X, uv))
        if not pts:
            print("epipolar line not in view"); sys.exit()
        U = np.array([p[2] for p in pts])
        x0, y0 = int(max(U[:, 0].min() - 60, 0)), int(max(U[:, 1].min() - 60, 0))
        x1, y1 = int(min(U[:, 0].max() + 60, O[b]["W"])), int(min(U[:, 1].max() + 60, O[b]["H"]))
        mk = [["y%.3f" % X[1], X[0], X[1], X[2] + DZ] for i, (s, X, uv) in enumerate(pts) if i % 3 == 0]
        env = dict(os.environ, MARK_PTS=json.dumps(mk))
        sc = max(1.0, min(3.0, 900 / max(x1 - x0, y1 - y0)))
        subprocess.run([sys.executable, os.path.join(HERE, "grid_photo.py"), b, out, str(x0), str(y0), str(x1), str(y1),
                        "%.2f" % sc, "10"], env=env, check=True)
