"""Score a bumper build: Kunos VERTICES of each band piece -> our faces (median / p95 / max, within 0.3 / 1 mm), all
Kunos vertices of the mesh, and the build's mirror symmetry.
    python bumper_score.py CAR_DIR BUILD.npz [rear|front]"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panel_fit as PF, bumper_build as BB
from exact_dist import point_to_tris
car, bp = sys.argv[1], sys.argv[2]; sp = BB.SPEC[sys.argv[3] if len(sys.argv) > 3 else 'rear']
d = np.load(bp); P = d['P'] / (1000 if np.abs(d['P']).max() > 10 else 1); TB = P[d['F']]
V, F, N = PF.load_mesh(car, sp['mesh']); pcs = BB.pieces(V, F, N, sp)
def line(nm, x):
    print(f'{nm:24s} {len(x):5d} vertices: median {np.median(x):.3f}  p95 {np.percentile(x, 95):.3f}  max {x.max():.3f} mm  '
          f'within 0.3 / 1 mm {np.mean(x < 0.3) * 100:.1f} / {np.mean(x < 1) * 100:.1f} %')
if sp['bands']:
    X = V[np.unique(np.vstack([pcs[b] for b in sorted(set(sp['bands']))]))]
    line('bands (all)', point_to_tris(X, TB) * 1000)
for b in sorted(set(sp['bands'])):
    line(f'  r{b}', point_to_tris(V[np.unique(pcs[b])], TB) * 1000)
line('whole mesh', point_to_tris(V[np.unique(F)], TB) * 1000)
S = P[::max(1, len(P) // 4000)]; ds = point_to_tris(S * BB.MIR, TB) * 1000
print(f'mirror check: median {np.median(ds):.4f}  max {ds.max():.4f} mm')
