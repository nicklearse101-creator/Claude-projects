"""Score the front band build: Kunos's band vertices (frontband_build.region) -> our faces.  python frontband_score.py CAR_DIR BUILD.npz [OLD.npz]"""
import sys, os; sys.path.insert(0, r'D:\Claude\Claude-\blender\kn5-study')
import numpy as np, frontband_build as FB
from exact_dist import point_to_tris
C = sys.argv[1]; sys.argv = [sys.argv[0]] + sys.argv[2:]
Vb, Fb, Nb = FB.region(C); X = np.unique(np.round(Vb[np.unique(Fb)], 6), axis=0)
d = np.load(sys.argv[1]); P = d['P'] / (1000 if np.abs(d['P']).max() > 10 else 1)
e = point_to_tris(X, P[d['F']]) * 1000
print(f'front band: {len(X)} Kunos vertices: median {np.median(e):.3f} p95 {np.percentile(e, 95):.3f} max {e.max():.3f} mm, within 0.3 / 1 mm {np.mean(e < 0.3) * 100:.1f} / {np.mean(e < 1) * 100:.1f} %')
o = np.argsort(-e)[:8]; print('worst:', [(tuple(np.round(X[i] * 1e3).astype(int)), round(float(e[i]), 2)) for i in o])
# same vertices vs the old quarter build
if len(sys.argv) > 2:
    d = np.load(sys.argv[2]); P = d['P'] / (1000 if np.abs(d['P']).max() > 10 else 1); e2 = point_to_tris(X, P[d['F']]) * 1000
    print(f'old quarter on them: median {np.median(e2):.3f} p95 {np.percentile(e2, 95):.3f} max {e2.max():.3f} mm, within 0.3 / 1 mm {np.mean(e2 < 0.3) * 100:.1f} / {np.mean(e2 < 1) * 100:.1f} %')
