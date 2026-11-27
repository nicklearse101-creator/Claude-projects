"""Score the arch flare build: Kunos's flare vertices (between the edge and the outer round's last row, inside the
built station range) -> our faces.   python flare_score.py CAR_DIR BUILD.npz"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, flare_build as FB
from exact_dist import point_to_tris
car, b = sys.argv[1], sys.argv[2]
ed, R, (V, Fw, N, wid, rep) = FB.rows(car, verbose=False)
vv = np.unique(wid[Fw]); X = V[rep[vv]]; a, d = ed.ad(X)
m = (a > FB.A_RANGE[0] + 0.003) & (a < FB.A_RANGE[1] - 0.003) & (d > -0.001) & (d < FB.row_at(R['out2'], a)[0] + 0.0005)
db = np.load(b); P = db['P'] / (1000 if np.abs(db['P']).max() > 10 else 1)
e = point_to_tris(X[m], P[db['F']], cap=0.02) * 1e3
print(f'flare: {m.sum()} Kunos vertices: median {np.median(e):.2f} p95 {np.percentile(e, 95):.2f} max {e.max():.2f} mm, within 0.3 / 1 mm {np.mean(e < 0.3) * 100:.1f} / {np.mean(e < 1) * 100:.1f} %')
