"""Two-way exact score of a panel build against the true outer skin (point -> surface, no sampling error).

    python score_exact.py BUILD.npz [CAR_DIR]
BUILD.npz holds quad grids (nu,nv,3) in metres (cad_panels_freecad.py output).
Also prints the worst panels (real->cad by panel nearest) and writes BUILD_err.npz for heatmaps.
"""
import sys, os, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_test as B, car_loft as CL, cad_panels as CP
from exact_dist import point_to_tris, quads_to_tris, stats

CAR = sys.argv[2] if len(sys.argv) > 2 else 'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86'
t0 = time.time()
ctx = B.setup(CAR, os.path.dirname(os.path.abspath(sys.argv[1])))
T, n, mid, names = CP.skin_by_mesh(ctx, CAR)
d = np.load(sys.argv[1])
tris, owner, pts, powner = [], [], [], []
for k in d.files:
    P = d[k]
    if P.ndim != 3 or min(P.shape[:2]) < 2: continue
    q = quads_to_tris(P); tris.append(q); owner.append(np.full(len(q), len(pts)))
    pts.append(P.reshape(-1, 3)); powner.append(k)
CT = np.concatenate(tris); own = np.concatenate(owner)
TP = CL.sample_tris(T, 0.006)                     # truth sample points (only the query side samples)
a = point_to_tris(TP, CT)                          # real -> cad
G = np.concatenate(pts); gk = np.concatenate([np.full(len(p), i) for i, p in enumerate(pts)])
b = point_to_tris(G, T)                            # cad -> real
res = dict(real_to_cad=stats(a), cad_to_real=stats(b), panels=len(pts), secs=round(time.time() - t0))
print(json.dumps(res))
worst = sorted(((float(np.percentile(b[gk == i], 90)) * 1000, powner[i]) for i in range(len(pts))), reverse=True)[:12]
print('worst strips by cad->real p90 (mm):', [(k, round(v, 1)) for v, k in worst])
np.savez(sys.argv[1].replace('.npz', '_err.npz'), TP=TP, a=a, G=G, b=b, gk=gk)
