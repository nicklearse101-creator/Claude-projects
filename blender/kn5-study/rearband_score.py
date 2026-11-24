"""Score a rear lower band build: Kunos's band vertices (rearband_build.candidates, at or below Y_TOP) -> our faces, per
zone (centre strip |x| < X0, sweep, arch end), and the build's own mirror symmetry.
    python rearband_score.py CAR_DIR BUILD.npz"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exact_dist import point_to_tris
import rearband_build as RB
car, bp = sys.argv[1], sys.argv[2]
V, F, N, B = RB.candidates(car)
X = V[np.unique(B)]; X = X[X[:, 1] <= RB.Y_TOP + 1e-6]
d = np.load(bp); P = d['P'] / (1000 if np.abs(d['P']).max() > 10 else 1); TB = P[d['F']]
e = point_to_tris(X, TB) * 1000
# Kunos's band is NOT symmetric (right 304 vertices, left 251; 97 right ones have no mirror partner, up to 37 mm off):
# our build is made on the left and mirrored, so the LEFT side (x >= 0) is the score; the right is shown for reference
L_ = X[:, 0] >= -1e-6
zones = (('left (score)', L_), ('  centre |x| < X0', L_ & (np.abs(X[:, 0]) < RB.X0)), ('  sweep + end', L_ & (np.abs(X[:, 0]) >= RB.X0)),
         ('right (Kunos asym.)', ~L_))
for nm, m in zones:
    x = e[m]
    print(f'{nm:18s} {len(x):4d} vertices: median {np.median(x):.3f}  p95 {np.percentile(x, 95):.3f}  max {x.max():.3f} mm  within 0.3 / 1 mm {np.mean(x < 0.3) * 100:.1f} / {np.mean(x < 1) * 100:.1f} %')
o = np.argsort(-np.where(L_, e, 0))[:6]; print('worst (left):', [(tuple(np.round(X[i] * 1e3).astype(int)), round(float(e[i]), 2)) for i in o])
S = P[::max(1, len(P) // 3000)]; ds = point_to_tris(S * RB.MIR, TB) * 1000
print(f'mirror check: median {np.median(ds):.4f}  max {ds.max():.4f} mm')
