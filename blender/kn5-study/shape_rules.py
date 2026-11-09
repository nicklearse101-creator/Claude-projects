"""Measure the modelling rules hidden in a kn5 mesh (numpy only).

    python shape_rules.py CAR.kn5 MESH_SUBSTR [MESH_SUBSTR ...]

For each mesh:
- bend per edge: dihedral angle between the two faces on each smooth edge (the "chord tolerance" the
  modeller worked to). Hard edges (normals split) are reported separately.
- edge length vs bend: whether density follows curvature (flat = long edges, bends = short).
- normals: stored normal vs (a) plain average of face normals and (b) area-weighted average.
  If (b) fits much better, the model was exported with weighted / face-area normals (a pro trick that
  keeps big flat panels flat-shaded next to tight bevels).
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5


def analyse(m):
    P, N, I = m.pos, m.nrm, m.idx
    q = np.round(P / 1e-5).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True); inv = inv.ravel()
    T = inv[I]
    a, b, c = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    cr = np.cross(b - a, c - a); ar = np.linalg.norm(cr, axis=1); ok = ar > 1e-12
    fn = np.zeros_like(cr); fn[ok] = cr[ok] / ar[ok, None]
    # edges keyed on welded verts
    edges = {}
    for f in np.flatnonzero(ok):
        for k in range(3):
            u, v = T[f, k], T[f, (k + 1) % 3]
            cu, cv = I[f, k], I[f, (k + 1) % 3]          # split corners (to see if normals differ)
            key = (min(u, v), max(u, v))
            edges.setdefault(key, []).append((f, cu, cv))
    bend, length, hard = [], [], 0
    for (u, v), lst in edges.items():
        if len(lst) != 2: continue
        (f1, a1, b1), (f2, a2, b2) = lst
        ang = np.degrees(np.arccos(np.clip(fn[f1] @ fn[f2], -1, 1)))
        # same welded edge; are the stored corner normals shared across it?
        n1 = {inv[a1]: N[a1], inv[b1]: N[b1]}; n2 = {inv[a2]: N[a2], inv[b2]: N[b2]}
        split = any(n1[w] @ n2[w] < np.cos(np.radians(2)) for w in n1 if w in n2)
        if split:
            hard += 1; continue
        bend.append(ang); length.append(np.linalg.norm(P[a1] - P[b1]))
    bend = np.array(bend); length = np.array(length) * 1000
    # normals: plain vs area-weighted vs angle-weighted face averages per welded vertex
    nv = inv.max() + 1
    plain = np.zeros((nv, 3)); area = np.zeros((nv, 3))
    for k in range(3):
        np.add.at(plain, T[ok, k], fn[ok]); np.add.at(area, T[ok, k], cr[ok])
    def nrmz(x):
        l = np.linalg.norm(x, axis=1, keepdims=True); l[l == 0] = 1; return x / l
    plain, area = nrmz(plain), nrmz(area)
    # compare only on vertices whose stored normals are all equal (smooth vertices)
    devp, deva = [], []
    order = np.argsort(inv)
    grp = np.split(order, np.flatnonzero(np.diff(inv[order])) + 1)
    for g in grp:
        if np.any(N[g] @ N[g[0]] < np.cos(np.radians(2))): continue
        w = inv[g[0]]
        devp.append(np.degrees(np.arccos(np.clip(N[g[0]] @ plain[w], -1, 1))))
        deva.append(np.degrees(np.arccos(np.clip(N[g[0]] @ area[w], -1, 1))))
    devp, deva = np.array(devp), np.array(deva)
    pct = lambda x, p: float(np.percentile(x, p)) if len(x) else float('nan')
    out = dict(mesh=m.name, tris=len(I), smooth_edges=len(bend), hard_edges=hard,
               bend_med=pct(bend, 50), bend_p90=pct(bend, 90), bend_p99=pct(bend, 99),
               len_med=pct(length, 50))
    # density vs curvature: median edge length in bend bands
    for lo, hi in [(0, 1), (1, 3), (3, 8), (8, 20), (20, 60), (60, 180)]:
        s = (bend >= lo) & (bend < hi)
        out[f'len_mm@{lo}-{hi}deg'] = (round(pct(length[s], 50), 1), int(s.sum()))
    out['normal_dev_plain_med'] = pct(devp, 50); out['normal_dev_area_med'] = pct(deva, 50)
    out['normal_dev_plain_p90'] = pct(devp, 90); out['normal_dev_area_p90'] = pct(deva, 90)
    return out


if __name__ == '__main__':
    k = KN5(sys.argv[1], load_textures=False)
    for m in k.meshes:
        if any(s.lower() in m.name.lower() for s in sys.argv[2:]):
            r = analyse(m)
            print(r['mesh'], f"tris={r['tris']} smooth={r['smooth_edges']} hard={r['hard_edges']}")
            print(f"   bend per edge deg: median {r['bend_med']:.2f}  p90 {r['bend_p90']:.2f}  p99 {r['bend_p99']:.2f}   edge median {r['len_med']:.1f} mm")
            print('   edge length by bend:', {k2[7:]: v for k2, v in r.items() if k2.startswith('len_mm@')})
            print(f"   stored normal vs plain avg: med {r['normal_dev_plain_med']:.2f} p90 {r['normal_dev_plain_p90']:.2f} | vs area-weighted: med {r['normal_dev_area_med']:.2f} p90 {r['normal_dev_area_p90']:.2f}")
