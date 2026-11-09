"""Lines -> surface experiment: how much of a car body is decided by its character lines?

    python lines_to_surface.py MESH.npz [MESH.npz ...]

MESH.npz holds a panel exported from Blender (V verts in Blender frame, E edges, B boundary flags,
A edge dihedral angles in degrees, N vertex normals).

For each curve set, the vertices on the lines keep their true positions. Every other vertex is
forgotten, then rebuilt as the smoothest surface through the lines: a bi-Laplacian (thin-plate) fill,
like a modeller's smooth patch. The score is the distance of each rebuilt vertex from the true surface
along the true normal, in mm.

Curve sets (cumulative):
  A  panel outlines (boundaries)
  B  + character creases (dihedral > 30 deg)
  C  + softer lines (dihedral > 12 deg)
  D  + sections every 400 mm along the car (lengthwise station curves)
  E  + sections every 200 mm
  F  + waterlines every 200 mm (height curves), i.e. a curve grid of ~200 mm
"""
import sys, os, json
import numpy as np


def neighbours(nv, E):
    deg = np.bincount(E.ravel(), minlength=nv).astype(float)
    return deg


def lap(x, E, deg):
    s = np.zeros_like(x)
    np.add.at(s, E[:, 0], x[E[:, 1]]); np.add.at(s, E[:, 1], x[E[:, 0]])
    return x - s / np.maximum(deg, 1)[:, None]


def lapT(y, E, deg):
    w = y / np.maximum(deg, 1)[:, None]
    s = np.zeros_like(y)
    np.add.at(s, E[:, 0], w[E[:, 1]]); np.add.at(s, E[:, 1], w[E[:, 0]])
    return y - s


def solve(V, E, fixed, iters=4000, tol=1e-10):
    """minimise |L x|^2 over the free vertices (thin-plate fill), conjugate gradients"""
    deg = neighbours(len(V), E)
    free = ~fixed
    x0 = np.where(fixed[:, None], V, 0.0)
    A = lambda u: lapT(lap(u, E, deg), E, deg)
    b = -A(x0); b[fixed] = 0
    x = np.zeros_like(V)
    # initial guess: mean of fixed positions (keeps CG well conditioned)
    x[free] = V[fixed].mean(0)
    r = b - A(x); r[fixed] = 0; p = r.copy(); rs = (r * r).sum()
    for k in range(iters):
        Ap = A(p); Ap[fixed] = 0
        a = rs / max((p * Ap).sum(), 1e-30)
        x += a * p; r -= a * Ap
        rn = (r * r).sum()
        if rn < tol: break
        p = r + (rn / rs) * p; rs = rn
    return x0 + x * free[:, None], k


def curve_sets(V, E, B, A):
    nv = len(V)
    def verts_of(edge_mask):
        m = np.zeros(nv, bool); m[E[edge_mask].ravel()] = True; return m
    sets = {}
    cur = B.copy(); sets['A outlines'] = cur.copy()
    cur |= verts_of(A > 30); sets['B + creases >30'] = cur.copy()
    cur |= verts_of(A > 12); sets['C + soft lines >12'] = cur.copy()
    # sections: edges crossing a station plane -> take the nearer vertex of each crossing edge
    def plane_verts(axis, step):
        m = np.zeros(nv, bool); c = V[:, axis]
        for s in np.arange(np.floor(c.min() / step) * step, c.max(), step):
            a, b = c[E[:, 0]] - s, c[E[:, 1]] - s
            hit = (a * b) <= 0
            near = np.where(np.abs(a[hit]) < np.abs(b[hit]), E[hit, 0], E[hit, 1])
            m[near] = True
        return m
    cur |= plane_verts(1, 0.4); sets['D + sections 400mm'] = cur.copy()     # Blender y = along the car
    cur |= plane_verts(1, 0.2); sets['E + sections 200mm'] = cur.copy()
    cur |= plane_verts(2, 0.2); sets['F + waterlines 200mm'] = cur.copy()
    return sets


def run(path):
    d = np.load(path); V, E, B, A, N = d['V'], d['E'], d['B'], d['A'], d['N']
    rows = []
    for name, fixed in curve_sets(V, E, B, A).items():
        X, k = solve(V, E, fixed)
        err = np.abs(((X - V) * N).sum(1))[~fixed] * 1000
        raw = np.linalg.norm(X - V, axis=1)[~fixed] * 1000
        rows.append(dict(set=name, fixed_pct=round(100 * fixed.mean(), 1), free=int((~fixed).sum()),
                         median_mm=round(float(np.median(err)), 2) if len(err) else 0,
                         p90_mm=round(float(np.percentile(err, 90)), 2) if len(err) else 0,
                         within_3mm_pct=round(float(np.mean(err <= 3) * 100), 1) if len(err) else 100,
                         raw_median_mm=round(float(np.median(raw)), 2) if len(raw) else 0, cg_iters=k))
        np.save(path.replace('_mesh.npz', f'_rebuilt_{name[0]}.npy'), X)
    return rows


if __name__ == '__main__':
    out = {}
    for p in sys.argv[1:]:
        out[os.path.basename(p)] = run(p)
        print('==', os.path.basename(p))
        for r in out[os.path.basename(p)]:
            print(f"  {r['set']:22s} fixed {r['fixed_pct']:5.1f}%  median {r['median_mm']:6.2f}  p90 {r['p90_mm']:7.2f}  <=3mm {r['within_3mm_pct']:5.1f}%  (cg {r['cg_iters']})")
    json.dump(out, open(os.path.join(os.path.dirname(sys.argv[1]), 'lines_to_surface.json'), 'w'), indent=1)
