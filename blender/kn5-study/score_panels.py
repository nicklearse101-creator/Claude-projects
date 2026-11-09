import sys, numpy as np, json
sys.path.insert(0, 'D:/Claude/Claude-/blender/kn5-study')
import blind_test as B, car_loft as CL, cad_panels as CP
ctx = B.setup('D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86', '.')
T, n, mid, names = CP.skin_by_mesh(ctx, 'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86')
TP = CL.sample_tris(T)
d = np.load(sys.argv[1])
G = []
for k in d.files:
    P = d[k]
    for a in (0, 0.25, 0.5, 0.75):
        for b in (0, 0.25, 0.5, 0.75):   # densify between grid points
            Q = P[:-1, :-1] * (1 - a) * (1 - b) + P[1:, :-1] * a * (1 - b) + P[:-1, 1:] * (1 - a) * b + P[1:, 1:] * a * b
            G.append(Q.reshape(-1, 3))
G = np.concatenate(G)
a = CL.nearest(TP, G, 2) * 1000; b = CL.nearest(G, TP, 2) * 1000
print(json.dumps(dict(real_to_cad=dict(median=round(float(np.median(a)), 2), p90=round(float(np.percentile(a, 90)), 2), within_3mm=round(float(np.mean(a <= 3) * 100), 1)),
                      cad_to_real=dict(median=round(float(np.median(b)), 2), p90=round(float(np.percentile(b, 90)), 2), within_3mm=round(float(np.mean(b <= 3) * 100), 1)))))
