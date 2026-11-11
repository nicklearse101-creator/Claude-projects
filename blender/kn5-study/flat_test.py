import sys, os, numpy as np
sys.path.insert(0, r'D:\Claude\Claude-\blender\kn5-study'); os.environ['PF_CLIP'] = '0.45,1,0,1.235,-2.2,-0.5'
import panel_fit as P
C = r'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86'
V, F, Nv = P.load_mesh(C, 'GEO_body'); pcs = P.crease_pieces(V, F, Nv)
ri = int(sys.argv[1]); Fr = pcs[ri]; ids = np.unique(Fr); X = V[ids]
fr = P.frame_of(X, Nv[ids]); S = P.to_plane(X, fr)
Nn = Nv / np.linalg.norm(Nv, axis=1)[:, None]
cosmin = np.minimum.reduce([(Nn[Fr[:, a]] * Nn[Fr[:, b]]).sum(1) for a, b in ((0, 1), (1, 2), (0, 2))])
for deg in (2.0, 4.0):
    flat = cosmin > np.cos(np.radians(deg)); T = V[Fr[flat]]
    A = 0.5*np.linalg.norm(np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]),axis=1)
    Xs = P.sample_tris_bary(T, 0.015); Ss = P.to_plane(Xs, fr)
    print(f'flat (normals within {deg} deg): {flat.sum()} of {len(Fr)} tris, {A.sum()*1e4:.0f} cm2, {len(Ss)} samples')
pad = 0.02; dom = [S[:,0].min()-pad, S[:,0].max()+pad, S[:,1].min()-pad, S[:,1].max()+pad]
f0, r0, _ = P.select_fit(S, dom)
S2 = np.r_[S, Ss]
f1, r1, _ = P.select_fit(S2, dom)
for nm, f in (('vertices only', f0), ('+ flat facets', f1)):
    rv = np.abs(P.eval_surface(f, S[:,0], S[:,1]) - S[:,2])*1e3; rs = np.abs(P.eval_surface(f, Ss[:,0], Ss[:,1]) - Ss[:,2])*1e3
    print(f'{nm:15s} ctrl {f["nu"]}x{f["nv"]}  vertices p50 {np.median(rv):.2f} p95 {np.percentile(rv,95):.2f} max {rv.max():.2f}   flat-facet samples p50 {np.median(rs):.2f} p95 {np.percentile(rs,95):.2f} max {rs.max():.2f}')
rv = np.abs(P.eval_surface(f1, S[:,0], S[:,1]) - S[:,2])*1e3
for lo, hi in ((-0.9,-1.2),(-1.2,-1.5),(-1.5,-1.75),(-1.75,-1.9),(-1.9,-2.1)):
    m = (X[:,2] <= lo) & (X[:,2] > hi); print('z %.2f..%.2f: %3d verts, p50 %.2f p95 %.2f max %.2f' % (lo, hi, m.sum(), np.median(rv[m]), np.percentile(rv[m],95), rv[m].max()))
