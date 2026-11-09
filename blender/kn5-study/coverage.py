import sys, numpy as np
sys.path.insert(0, 'D:/Claude/Claude-/blender/kn5-study')
import blind_test as B, car_loft as CL, cad_panels as CP
C = 'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86'
ctx = B.setup(C, '.')
T, n, mid, names = CP.skin_by_mesh(ctx, C)
cls = CP.classify(n)
d = np.load(sys.argv[1]); G = []
for k in d.files:
    P = d[k]
    for a in (0, 0.25, 0.5, 0.75):
        for b in (0, 0.25, 0.5, 0.75):
            G.append((P[:-1, :-1] * (1 - a) * (1 - b) + P[1:, :-1] * a * (1 - b) + P[:-1, 1:] * (1 - a) * b + P[1:, 1:] * a * b).reshape(-1, 3))
G = np.concatenate(G)
cen = T.mean(1)
dist = CL.nearest(cen, G, 2) * 1000
TPd = CL.sample_tris(T)
area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
unc = dist > 10
print('uncovered area %.3f of %.3f m2' % (area[unc].sum(), area.sum()))
rows = {}
for i in np.where(unc)[0]:
    k = (names[mid[i]], cls[i]); rows[k] = rows.get(k, 0) + area[i]
for k, a in sorted(rows.items(), key=lambda kv: -kv[1])[:15]: print(f'  {k[0][:26]:26s} {k[1]:5s} {a:6.3f} m2')
print('uncovered by height (m):', np.histogram(cen[unc, 1], bins=[0, 0.2, 0.35, 0.5, 0.7, 0.9, 1.1, 1.4], weights=area[unc])[0].round(3))
print('uncovered by z (m):', np.histogram(cen[unc, 2], bins=np.arange(-2.2, 2.3, 0.4), weights=area[unc])[0].round(3))
np.savez('uncovered_tris.npz', T=T[unc], dist=dist[unc])
