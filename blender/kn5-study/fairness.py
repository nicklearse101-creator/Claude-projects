"""How a body surface was laid out, and how fair (smooth) it is. numpy only.

    python fairness.py CAR_DIR MESH_NAME [CAR_DIR MESH_NAME ...]

layout   - fraction of edges lying in a constant-z plane (station / cross-section loops), constant-x (side
           lines seen in plan), constant-y (waterlines). High values = modelled from orthographic blueprints
           with loops placed on stations; low = free-flow topology (sculpt, scan retopo, photogrammetry).
symmetry - median distance (mm) from each vertex on the left to the nearest mirrored right vertex.
           ~0.00 = built as a half and mirrored; mm-level = modelled or scanned whole.
fairness - curvature noise: per vertex, mean curvature from the umbrella Laplacian, then how much it
           jumps relative to its neighbours' mean (1/m). Low = fair surface; high = lumpy / noisy.
           Reported as median and p90 over smooth vertices (hard edges excluded).
"""
import sys, os, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5


def welded(m, tol=1e-5):
    q = np.round(m.pos / tol).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    return m.pos[first], inv.ravel()[m.idx]


def nearest_dist(A, B, cell=0.01):
    """For each point in A, distance to the nearest point in B (grid hashing, exact within 1 cell)."""
    keys = np.floor(B / cell).astype(np.int64)
    grid = {}
    for i, k in enumerate(map(tuple, keys)): grid.setdefault(k, []).append(i)
    out = np.full(len(A), np.inf)
    for i, p in enumerate(A):
        k = np.floor(p / cell).astype(np.int64); best = np.inf
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        d = np.sum((B[j] - p) ** 2)
                        if d < best: best = d
        out[i] = np.sqrt(best)
    return out


def analyse(m):
    V, T = welded(m)
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); E.sort(1); E = np.unique(E, axis=0)
    d = np.abs(V[E[:, 0]] - V[E[:, 1]]); L = np.linalg.norm(d, axis=1); ok = L > 2e-3
    r = dict(verts=len(V), edges=len(E))
    for ax, nm in ((2, 'station_loops_z'), (0, 'plan_lines_x'), (1, 'waterlines_y')):
        r[nm] = round(float(np.mean(d[ok, ax] < 1e-3)), 3)
    # symmetry
    left = V[V[:, 0] > 0.02]; right = V[V[:, 0] < -0.02] * [-1, 1, 1]
    if len(left) > 20 and len(right) > 20:
        sub = left[np.random.default_rng(0).choice(len(left), min(1500, len(left)), replace=False)]
        nd = nearest_dist(sub, right)
        r['sym_median_mm'] = round(float(np.median(nd)) * 1000, 2)
        r['sym_exact_pct'] = round(100 * float(np.mean(nd < 1e-4)), 1)
    # fairness: umbrella-Laplacian mean curvature, then its local jump
    n = len(V)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = np.zeros((n, 3))
    for k in range(3): np.add.at(vn, T[:, k], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    deg = np.zeros(n); nbsum = np.zeros((n, 3)); elen = np.zeros(n)
    for i, j in ((0, 1), (1, 0)):
        np.add.at(nbsum, E[:, i], V[E[:, j]]); np.add.at(deg, E[:, i], 1); np.add.at(elen, E[:, i], L)
    inner = deg >= 4
    lap = nbsum / np.maximum(deg, 1)[:, None] - V
    h = np.einsum('ij,ij->i', lap, vn) / np.maximum((elen / np.maximum(deg, 1)) ** 2, 1e-12) * 2  # ~ curvature 1/m
    hs = np.zeros(n); hc = np.zeros(n)
    for i, j in ((0, 1), (1, 0)):
        np.add.at(hs, E[:, i], h[E[:, j]]); np.add.at(hc, E[:, i], 1)
    jump = np.abs(h - hs / np.maximum(hc, 1))
    # boundary vertices excluded: an edge used by one face only
    cnt = {}
    for t in T:
        for x, y in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (min(x, y), max(x, y)); cnt[key] = cnt.get(key, 0) + 1
    bnd = np.zeros(n, bool)
    for (x, y), c_ in cnt.items():
        if c_ == 1: bnd[x] = bnd[y] = True
    sel = inner & ~bnd & (np.abs(h) < 50)          # ignore tight fillets (<20 mm radius)
    r['curv_noise_med'] = round(float(np.median(jump[sel])), 2)
    r['curv_noise_p90'] = round(float(np.percentile(jump[sel], 90)), 2)
    r['curv_med'] = round(float(np.median(np.abs(h[sel]))), 2)
    return r


if __name__ == '__main__':
    args = sys.argv[1:]
    for car, mesh in zip(args[::2], args[1::2]):
        kn5 = sorted(glob.glob(os.path.join(car, '*.kn5')), key=os.path.getsize)[-1]
        k = KN5(kn5, load_textures=False)
        m = [x for x in k.meshes if x.name == mesh]
        if not m: print(os.path.basename(car), 'no mesh', mesh); continue
        print(os.path.basename(car).ljust(24), mesh.ljust(20), analyse(m[0]))
