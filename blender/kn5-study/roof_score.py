"""Score a roof build against the Kunos roof region (roof_build.roof_region).
    python roof_score.py CAR_DIR BUILD.npz      (BUILD.npz from pack_build.py)
Main score = Kunos VERTICES -> our faces (the facets are chords and sit up to ~1-2.6 mm inside a curved roof);
area coverage of the Kunos facets within 1 / 3 mm is printed for reference only."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exact_dist import point_to_tris
import roof_build as RB
V, R0, N = RB.roof_region(sys.argv[1]); d = np.load(sys.argv[2]); TB = d['P'][d['F']]
u = np.unique(R0); dv = point_to_tris(V[u], TB) * 1000
print(f'Kunos roof vertices -> ours: median {np.median(dv):.3f}  p95 {np.percentile(dv, 95):.3f}  max {dv.max():.3f} mm  '
      f'within 0.3 / 1 mm: {np.mean(dv < 0.3) * 100:.1f} / {np.mean(dv < 1) * 100:.1f} %')
T = V[R0]; A = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
dc = point_to_tris(T.mean(1), TB) * 1000
print(f'Kunos roof area within 1 / 3 mm of ours (facet centres, chords - reference only): {A[dc < 1].sum() / A.sum() * 100:.1f} / {A[dc < 3].sum() / A.sum() * 100:.1f} %')
# the roof's neighbour strips (roof_build.neighbour_strips): their Kunos vertices -> ours, per strip
if os.environ.get('RS_STRIPS', '1') != '0':
    import panel_fit as PF
    Vb, Fb, Nb = PF.load_mesh(sys.argv[1], 'GEO_body', raw=True); cb = Vb[Fb].mean(1); pcs = PF.crease_pieces(Vb, Fb[cb[:, 1] > 1.0], Nb)
    names = [k[:-2] for k in d.files if k.endswith('_F')] if 'names' not in d.files else []
    out = []
    for ri in (9, 10, 11, 12, 13, 18, 19):
        dv_ = point_to_tris(Vb[np.unique(pcs[ri])], TB) * 1000
        out.append(f'r{ri} {np.median(dv_):.2f}/{dv_.max():.2f}')
    print('neighbour strips, Kunos vertices -> ours (median / max mm): ' + '  '.join(out))
