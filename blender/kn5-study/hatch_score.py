"""Score a hatch build against the Kunos hatch (GEO_body pieces owned by hatch_build.py).
    python hatch_score.py CAR_DIR BUILD.npz
Kunos VERTICES -> our faces (facets are chords), per zone of the skin (header / pillars / deck / tail roll + skirt)
and per return piece. Also the build's own mirror symmetry (each build point -> the mirrored build)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exact_dist import point_to_tris
import hatch_build as HB

car, bp = sys.argv[1], sys.argv[2]
V, F, N, pcs = HB.pieces(car)
d = np.load(bp); TB = d['P'][d['F']]
TB = TB / 1000.0 if np.abs(TB).max() > 10 else TB
X = V[np.unique(pcs['skin'])]
dv = point_to_tris(X, TB) * 1000
# zones: header = above the glass (y > 1.15 or z > -1.0), deck/roll/skirt = behind the glass's lower edge, pillars = rest
top = X[:, 2] > -1.0
tail = X[:, 2] < -1.80
pil = ~top & ~tail


def line(nm, x):
    print(f'{nm:22s} {len(x):4d} vertices: median {np.median(x):.3f}  p95 {np.percentile(x, 95):.3f}  max {x.max():.3f} mm  '
          f'within 0.3 / 1 mm {np.mean(x < 0.3) * 100:.1f} / {np.mean(x < 1) * 100:.1f} %')


line('skin (all)', dv)
for nm, m in (('header', top), ('pillars', pil), ('deck + roll + skirt', tail)):
    line('  ' + nm, dv[m])
if os.environ.get('HT_RETURNS', '0') == '1':
    for nm in ('ring', 'wall', 'bottom', 'cornerL', 'cornerR'):
        Y = V[np.unique(pcs[nm])]; line(nm, point_to_tris(Y, TB) * 1000)
# symmetry of our build: sample points -> mirrored build
P = d['P'] / 1000.0 if np.abs(d['P']).max() > 10 else d['P']
S = P[::max(1, len(P) // 4000)]
ds = point_to_tris(S * HB.MIR, TB) * 1000
print(f'mirror check: {len(S)} build points -> mirrored build: median {np.median(ds):.4f}  max {ds.max():.4f} mm')
