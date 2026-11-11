"""Score a bonnet build against the Kunos skin (GEO_hood_SUB1 crease region 0).
    python bonnet_score.py CAR_DIR BUILD.npz
Kunos VERTICES -> our faces (facets are chords). Reported per zone: centre / outer / step band rows / nose (the nose
roll is not built yet, so its vertices are listed apart)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exact_dist import point_to_tris
import bonnet_build as BB
V, F, N, R0, P = BB.skin(sys.argv[1]); d = np.load(sys.argv[2]); TB = d['P'][d['F']]
dv = point_to_tris(P / 1000.0, TB) * 1000
line = BB.Line(BB.LINE_PTS); dl, sl = line.project(np.c_[np.abs(P[:, 0]), P[:, 2]])
nose = P[:, 2] > BB.NOSE_Z; band = (np.abs(dl) < 16) & (sl > -10) & (sl < line.L + 10) & ~nose
for nm, m in (('all (no nose)', ~nose), ('step band rows', band), ('panels', ~nose & ~band), ('nose (not built yet)', nose)):
    x = dv[m]
    print(f'{nm:22s} {m.sum():4d} vertices: median {np.median(x):.3f}  p95 {np.percentile(x, 95):.3f}  max {x.max():.3f} mm  within 0.3 / 1 mm {np.mean(x < 0.3) * 100:.1f} / {np.mean(x < 1) * 100:.1f} %')
