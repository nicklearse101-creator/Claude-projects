"""Panel-level technique study across many cars (no Blender needed).

    python panel_study.py OUT.json CAR_DIR [CAR_DIR ...]

Per car, for every painted exterior mesh (the panels):
  split       - which panels exist (names, areas): how the body is divided
  edge recipe - spacing of the first 3 vertex rings in from each panel edge (turned-in return, holding
                loops), medians
  lines test  - keep only the panel's outline / + creases > 30 deg / + sections every 400 mm, rebuild
                every other vertex as a thin-plate fill, score along the true normals (lines_to_surface)
"""
import sys, os, json, glob, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5
import lines_to_surface as L2S

PAINT = re.compile(r'(car.?paint|carpaint|body|paint|ext_body|livery|skin)', re.I)


def weld(m, tol=1e-5):
    q = np.round(m.pos / tol).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    T = inv.ravel()[m.idx]; V = m.pos[first]
    return V, T


def mesh_graph(V, T):
    e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
    f = np.repeat(np.arange(len(T)), 3)
    o = np.lexsort((e[:, 1], e[:, 0])); e, f = e[o], f[o]
    uniq, start, cnt = np.unique(e, axis=0, return_index=True, return_counts=True)
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    A = np.zeros(len(uniq))
    two = cnt == 2
    A[two] = np.degrees(np.arccos(np.clip((n[f[start[two]]] * n[f[start[two] + 1]]).sum(1), -1, 1)))
    B = np.zeros(len(V), bool); B[uniq[cnt == 1].ravel()] = True
    N = np.zeros_like(V)
    for j in range(3): np.add.at(N, T[:, j], n)
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    # quad diagonals (near-coplanar triangle pairs) are not real edges for the rings / Laplacian
    return uniq, A, B, N, two


def edge_rings(V, E, B, k=3):
    """median spacing of rings 1..k going inward from boundary vertices, along the edge most perpendicular
    to the boundary"""
    nb = [[] for _ in range(len(V))]
    for a, b in E: nb[a].append(b); nb[b].append(a)
    rings = [[] for _ in range(k)]
    for v in np.where(B)[0]:
        bn = [u for u in nb[v] if B[u]]
        if len(bn) != 2: continue
        t = V[bn[0]] - V[bn[1]]; t /= max(np.linalg.norm(t), 1e-12)
        cur, prev = v, -1
        for r in range(k):
            cands = [u for u in nb[cur] if u != prev and not B[u]]
            if not cands: break
            u = min(cands, key=lambda u: abs(((V[u] - V[cur]) / max(np.linalg.norm(V[u] - V[cur]), 1e-12)) @ t))
            d = V[u] - V[cur]
            if abs(d @ t) / max(np.linalg.norm(d), 1e-12) > 0.5: break
            rings[r].append(np.linalg.norm(d) * 1000); prev, cur = cur, u
    return [round(float(np.median(x)), 1) if x else None for x in rings]


def lines_test(V, E, B, A, N):
    nv = len(V); res = {}
    def verts(mask):
        m = np.zeros(nv, bool); m[E[mask].ravel()] = True; return m
    def plane(axis, step):
        m = np.zeros(nv, bool); c = V[:, axis]
        for s in np.arange(np.floor(c.min() / step) * step, c.max(), step):
            a, b = c[E[:, 0]] - s, c[E[:, 1]] - s; hit = (a * b) <= 0
            m[np.where(np.abs(a[hit]) < np.abs(b[hit]), E[hit, 0], E[hit, 1])] = True
        return m
    sets = {'outline': B.copy()}
    sets['+creases'] = sets['outline'] | verts(A > 30)
    sets['+sections400'] = sets['+creases'] | plane(2, 0.4)       # AC z = along the car
    for k, f in sets.items():
        if f.all() or (~f).sum() < 20: res[k] = None; continue
        X, _ = L2S.solve(V, E, f, iters=2500)
        e = np.abs(((X - V) * N).sum(1))[~f] * 1000
        res[k] = dict(median=round(float(np.median(e)), 2), within3=round(float(np.mean(e <= 3) * 100), 1), fixed=round(float(f.mean() * 100), 1))
    return res


def study(car_dir):
    kn5 = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize, reverse=True)[0]
    k = KN5(kn5, load_textures=False)
    out = dict(car=os.path.basename(car_dir), panels=[])
    for m in k.meshes:
        if not m.mat: continue
        path = k.path_of(m.node)
        if any(t in path for t in ('COCKPIT_', 'WHEEL_')) or any(t in m.name.lower() for t in ('dmg', 'shadow', 'lod', 'collider')): continue
        is_paint = ('damage_dirt' in m.mat.shader) or (PAINT.search(m.mat.name) and 'int' not in m.mat.name.lower())
        is_bumper = 'bumper' in m.name.lower() or 'bumper' in path.lower()
        if not (is_paint or is_bumper) or len(m.idx) < 200: continue
        V, T = weld(m)
        area = 0.5 * np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1).sum()
        if area < 0.05: continue
        E, A, B, N, two = mesh_graph(V, T)
        parent = path.split('/')[-2] if '/' in path else ''
        rec = dict(name=m.name, parent=parent, area_m2=round(float(area), 3), tris=int(len(T)),
                   boundary_pct=round(float(B.mean() * 100), 1), crease30_pct=round(float((A > 30).mean() * 100), 1),
                   rings_mm=edge_rings(V, E, B))
        if len(V) < 40000: rec['lines'] = lines_test(V, E, B, A, N)
        out['panels'].append(rec)
    return out


if __name__ == '__main__':
    res = []
    for c in sys.argv[2:]:
        try:
            r = study(c); res.append(r)
            big = sorted(r['panels'], key=lambda p: -p['area_m2'])
            print(r['car'], len(r['panels']), 'panels:', ', '.join(f"{p['parent'] or p['name']}({p['area_m2']})" for p in big[:8]), flush=True)
        except Exception as e:
            import traceback; traceback.print_exc(); res.append(dict(car=os.path.basename(c), error=repr(e)))
        json.dump(res, open(sys.argv[1], 'w'), indent=1)
