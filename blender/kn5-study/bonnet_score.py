"""Score a bonnet build against the Kunos skin (GEO_hood_SUB1 crease region 0).
    python bonnet_score.py CAR_DIR BUILD.npz
Kunos VERTICES -> our faces (facets are chords). Reported per zone: centre / outer / step band rows / nose (the nose
zone = Kunos skin vertices ahead of z 1790: roll + front face; with BN_NOSE=0 it is not built)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exact_dist import point_to_tris
import bonnet_build as BB
V, F, N, R0, P = BB.skin(sys.argv[1]); d = np.load(sys.argv[2]); TB = d['P'][d['F']]
dv = point_to_tris(P / 1000.0, TB) * 1000
line = BB.Line(BB.LINE_PTS); dl, sl = line.project(np.c_[np.abs(P[:, 0]), P[:, 2]])
nose = P[:, 2] > BB.NOSE_Z; band = (np.abs(dl) < 16) & (sl > -10) & (sl < line.L + 10) & ~nose
allm = np.ones(len(P), bool) if BB.NOSE else ~nose
for nm, m in (('all' if BB.NOSE else 'all (no nose)', allm), ('step band rows', band), ('panels', ~nose & ~band), ('nose', nose)):
    x = dv[m]
    print(f'{nm:22s} {m.sum():4d} vertices: median {np.median(x):.3f}  p95 {np.percentile(x, 95):.3f}  max {x.max():.3f} mm  within 0.3 / 1 mm {np.mean(x < 0.3) * 100:.1f} / {np.mean(x < 1) * 100:.1f} %')
# edge strips: Kunos vertices of each edge crease region (r1-r13) -> our build (skin + strips)
import panel_fit as PF
if os.environ.get('BN_STRIPS', '1') != '0':
    Vh, Fh, Nh = PF.load_mesh(sys.argv[1], BB.MESH, raw=True); pcs = PF.crease_pieces(Vh, Fh, Nh)
    names = {1: 'rear flange', 2: 'side return L', 3: 'side return R', 4: 'nose lip', 5: 'lamp-bay wall L', 6: 'lamp-bay wall R',
             7: 'tongue wall L', 8: 'tongue wall R', 9: 'side chamfer L', 10: 'side chamfer R', 11: 'nose chamfer',
             12: 'notch chamfer L', 13: 'notch chamfer R'}
    allv = []
    for ri, nm in names.items():
        X = Vh[np.unique(pcs[ri])]; dd = point_to_tris(X, TB) * 1000; allv.append(dd)
        print(f'  r{ri:<2d} {nm:16s} {len(X):3d} vertices: median {np.median(dd):.3f}  max {dd.max():.3f} mm')
    dd = np.concatenate(allv)
    print(f'edges (r1-r13) {len(dd):4d} vertices: median {np.median(dd):.3f}  p95 {np.percentile(dd, 95):.3f}  max {dd.max():.3f} mm  within 0.3 / 1 mm {np.mean(dd < 0.3) * 100:.1f} / {np.mean(dd < 1) * 100:.1f} %')
