"""Assetto Corsa wiper animation tool.

Recommended commands: tree, fitaxis, rigid, transplant, extract (see TOOLS.md). bend is deprecated.

Reads a car kn5, fits a single-axis rotation for a wiper node so the blade stays
on the windscreen through the sweep, and writes animations/car_wiper.ksanim
(the file CSP plays when the wipers are switched on).

  python ac_wiper.py tree  CAR.kn5                       # list nodes/meshes with world bounds
  python ac_wiper.py fit   CAR.kn5 --wiper wiper --glass ext_windows [--out car_wiper.ksanim]
  python ac_wiper.py check CAR.kn5 --wiper wiper --glass ext_windows --anim car_wiper.ksanim

Needs numpy. Wiper node is assumed to be an unscaled transform node whose
children are the wiper meshes.
"""
import argparse, math, os, struct, sys
import numpy as np

# ---------------------------------------------------------------- kn5 reader
class KN5:
    def __init__(self, path):
        self.d = open(path, 'rb').read(); self.p = 0
        assert self.d[:6] == b'sc6969', 'not a kn5'
        self.p = 6; ver, = self.r('<i')
        if ver > 5: self.r('<i')
        for _ in range(self.r('<i')[0]):                      # textures
            self.r('<i'); self.s(); n, = self.r('<i'); self.p += n
        self.mats = []
        for _ in range(self.r('<i')[0]):                      # materials
            self.mats.append(self.s()); self.s(); self.r('<bbi')
            for _ in range(self.r('<i')[0]): self.s(); self.p += 40   # float + v2 + v3 + v4
            for _ in range(self.r('<i')[0]): self.s(); self.r('<i'); self.s()
        self.nodes = []                                       # (depth, kind, name, local, world, parent_world, verts, idx, mat)
        self.span = {}                                        # transform node name -> (start, end) byte range incl. children
        self.raw = {}                                         # mesh name -> raw fields, for rewriting
        self._node(0, np.eye(4))

    def r(self, f):
        v = struct.unpack_from(f, self.d, self.p); self.p += struct.calcsize(f); return v

    def s(self):
        n, = self.r('<i'); v = self.d[self.p:self.p + n].decode('latin1'); self.p += n; return v

    def _node(self, depth, parent):
        start = self.p
        cls, = self.r('<i'); name = self.s(); nc, = self.r('<i'); self.r('<b')
        world = parent
        if cls == 1:
            local = np.array(self.r('<16f')).reshape(4, 4)    # row-vector matrix, translation in row 3
            world = local @ parent
            self.nodes.append((depth, 'N', name, local, world, parent, None, None, None))
        else:
            flags = self.r('<bbb')
            if cls == 3:
                for _ in range(self.r('<i')[0]): self.s(); self.r('<16f')
            vc, = self.r('<i'); st = 44 if cls == 2 else 76
            vraw = self.d[self.p:self.p + vc * st]
            v = np.array([struct.unpack_from('<3f', self.d, self.p + i * st) for i in range(vc)]).reshape(-1, 3)
            self.p += vc * st
            ic_at = self.p; ic, = self.r('<i'); idx = struct.unpack_from(f'<{ic}H', self.d, self.p); self.p += ic * 2
            mid, = self.r('<i'); layer, lod_in, lod_out = self.r('<iff'); self.r('<4f'); renderable, = self.r('<b')
            if cls == 2:
                self.raw[name] = dict(flags=flags, vraw=vraw, idx=idx, mid=mid, layer=layer, lod=(lod_in, lod_out), renderable=renderable, ic_at=ic_at)
            wv = v @ parent[:3, :3] + parent[3, :3] if vc else v
            self.nodes.append((depth, 'M', name, None, parent, parent, wv, idx, self.mats[mid] if mid < len(self.mats) else mid))
        for _ in range(nc): self._node(depth + 1, world)
        if cls == 1: self.span[name] = (start, self.p)

    def node(self, name):
        for n in self.nodes:
            if n[1] == 'N' and n[2] == name: return n
        sys.exit(f'node {name!r} not found')

    def meshes_under(self, name):
        """World verts/tris of all meshes below transform node `name` (or a mesh with that name)."""
        out = []; inside = None
        for n in self.nodes:
            if inside is not None:
                if n[0] <= inside: inside = None
                elif n[1] == 'M': out.append(n); continue
            if n[2] == name:
                if n[1] == 'M': out.append(n)
                else: inside = n[0]
        if not out: sys.exit(f'no meshes under {name!r}')
        return out

# ---------------------------------------------------------------- maths
def rot(a, th):
    a = a / np.linalg.norm(a); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K    # column-vector rotation

def quat_from_rot(R):
    w = math.sqrt(max(0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    if w > 1e-6:
        return np.array([(R[2, 1] - R[1, 2]) / (4 * w), (R[0, 2] - R[2, 0]) / (4 * w), (R[1, 0] - R[0, 1]) / (4 * w), w])
    i = int(np.argmax(np.diag(R))); j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(max(0, 1 + R[i, i] - R[j, j] - R[k, k])) * 2; q = np.zeros(4)
    q[i] = s / 4; q[j] = (R[j, i] + R[i, j]) / s; q[k] = (R[k, i] + R[i, k]) / s; q[3] = (R[k, j] - R[j, k]) / s
    return q

class Glass:
    """Vertical (Y) ray cast onto the windscreen triangles."""
    def __init__(self, meshes, zmin):
        tris = []
        for m in meshes:
            v, idx = m[6], m[7]
            for i in range(0, len(idx), 3):
                t = v[list(idx[i:i + 3])]
                if t[:, 2].mean() > zmin: tris.append(t)
        self.t = np.array(tris)

    def y(self, x, z):
        t = self.t
        x0, z0, x1, z1, x2, z2 = t[:, 0, 0], t[:, 0, 2], t[:, 1, 0], t[:, 1, 2], t[:, 2, 0], t[:, 2, 2]
        den = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2)
        ok = np.abs(den) > 1e-12; den = np.where(ok, den, 1)
        l0 = ((z1 - z2) * (x - x2) + (x2 - x1) * (z - z2)) / den
        l1 = ((z2 - z0) * (x - x2) + (x0 - x2) * (z - z2)) / den; l2 = 1 - l0 - l1
        hit = ok & (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not hit.any(): return None
        return (l0 * t[:, 0, 1] + l1 * t[:, 1, 1] + l2 * t[:, 2, 1])[hit].max()

def clearance(V, glass):
    c = [v[1] - g for v in V if (g := glass.y(v[0], v[2])) is not None]
    return min(c) if c else None

# ---------------------------------------------------------------- commands
def cmd_tree(a):
    k = KN5(a.kn5)
    for depth, kind, name, local, world, _, v, _, mat in k.nodes:
        pad = '  ' * depth
        if kind == 'N':
            print(f'{pad}[N] {name}  world_pos={np.round(world[3, :3], 3).tolist()}')
        elif len(v):
            print(f'{pad}[M] {name} v={len(v)} mat={mat} min={np.round(v.min(0), 3).tolist()} max={np.round(v.max(0), 3).tolist()}')

def setup(a):
    k = KN5(a.kn5); wn = k.node(a.wiper)
    W = np.vstack([m[6] for m in k.meshes_under(a.wiper)])
    if a.pivot:
        P = np.array([float(x) for x in a.pivot.split(',')])
    else:
        # pivot = hub verts at the wiper end nearest the car centreline (or --pivot-end)
        end = a.pivot_end
        if end == 'auto': end = 'min-x' if abs(W[:, 0].min()) < abs(W[:, 0].max()) else 'max-x'
        ex = W[:, 0].min() if end == 'min-x' else W[:, 0].max()
        P = W[np.abs(W[:, 0] - ex) < a.hub_radius].mean(0)
    off = getattr(a, 'offset', None)
    if off:                                                   # relocate the whole wiper (world-space move dx:dy:dz)
        o = np.array([float(x) for x in off.split(':')]); W = W + o; P = P + o
        local = wn[3].copy(); local[3, :3] += o @ np.linalg.inv(wn[5][:3, :3])
        wn = (wn[0], wn[1], wn[2], local, local @ wn[5], wn[5], *wn[6:])
    zmin = a.glass_zmin if a.glass_zmin is not None else P[2] - 1.2
    glass = Glass(k.meshes_under(a.glass), zmin)
    prot = float(getattr(a, 'park_rot', 0) or 0)
    if prot:                                                  # turn the parked wiper about its pivot, around the glass normal
        pa = getattr(a, 'park_axis', '') or ''
        if pa:                                                # tilt:lean of an axis known to follow the glass here
            t_, l_ = (float(v) for v in pa.split(':')); n_ = axis_lean(t_, l_)
        else:
            gaps(glass, (P + np.array([0, 0.05, -0.08]))[None]); n_ = glass.last_n[0]
        R = rot(n_, math.radians(prot)); W = (W - P) @ R.T + P
        A_ = np.eye(4); A_[:3, :3] = R.T; A_[3, :3] = P - P @ R.T
        local = wn[4] @ A_ @ np.linalg.inv(wn[5]); wn = (wn[0], wn[1], wn[2], local, local @ wn[5], wn[5], *wn[6:])
    tip_i = np.argmax(np.linalg.norm(W - P, axis=1)); tip = W[tip_i]
    print(f'wiper verts {len(W)}  pivot {np.round(P, 4).tolist()}  tip {np.round(tip, 3).tolist()}  glass tris {len(glass.t)}')
    return k, wn, W, P, tip, glass

def axis_of(tilt): return np.array([0, math.sin(math.radians(tilt)), math.cos(math.radians(tilt))])

def cmd_fit(a):
    k, wn, W, P, tip, glass = setup(a)
    Ws = W[::max(1, len(W) // 80)]
    base = clearance(Ws, glass)
    if base is None:
        print('parked wiper does not project onto glass; using 0 as target clearance'); base = 0
    target = np.array([-tip[0], tip[1], tip[2]])            # mirror of park position across centreline
    def score(tilt, deg, steps=11):
        ax = axis_of(tilt); dev = 0
        for i in range(steps):
            c = clearance((Ws - P) @ rot(ax, math.radians(deg) * i / (steps - 1)).T + P, glass)
            if c is not None: dev = max(dev, abs(c - base))
        end = 0 if a.sweep else np.linalg.norm(rot(ax, math.radians(deg)) @ (tip - P) + P - target)
        return dev + end, dev, end
    # sweep direction: rotate the tip up the glass (towards -Z / +Y), not down into the cowl
    sign = 1 if (rot(axis_of(55), 0.3) @ (tip - P))[1] > (tip - P)[1] else -1
    degs = [a.sweep * sign] if a.sweep else sign * np.arange(100, 178, 2.0)
    best = None
    for tilt in np.arange(30, 80, 2.5):
        for deg in degs:
            sc = score(tilt, deg)
            if best is None or sc[0] < best[0]: best = (sc[0], tilt, deg, sc[1], sc[2])
    _, t0, d0, _, _ = best
    for tilt in np.arange(t0 - 2.5, t0 + 2.51, 0.25):
        for deg in ([d0] if a.sweep else np.arange(d0 - 2, d0 + 2.01, 0.25)):
            sc = score(tilt, deg)
            if sc[0] < best[0]: best = (sc[0], tilt, deg, sc[1], sc[2])
    _, tilt, deg, dev, end = best
    print(f'axis tilt {tilt:.2f} deg  sweep {deg:.2f} deg  clearance deviation {dev * 1000:.1f} mm  end-point error {end * 1000:.1f} mm')
    write_anim(a.out, a.wiper, wn, P, axis_of(tilt), math.radians(deg), a.frames)
    print('wrote', a.out); a.anim = a.out; cmd_check(a, (k, wn, W, P, tip, glass))

def write_anim(path, name, wn, P, ax, ang, N):
    local0, parent = wn[3], wn[5]; world0 = local0 @ parent; inv_parent = np.linalg.inv(parent)
    frames = []
    for i in range(N):
        th = ang * (1 - math.cos(2 * math.pi * i / (N - 1))) / 2   # park -> full sweep -> park, eased
        R = rot(ax, th); A = np.eye(4); A[:3, :3] = R.T; A[3, :3] = P - P @ R.T   # row-vector rotation about P
        L = world0 @ A @ inv_parent
        q = quat_from_rot(L[:3, :3].T); q = q if q[3] >= 0 else -q
        frames.append(struct.pack('<10f', *q, *L[3, :3], 1, 1, 1))
    nm = name.encode()
    open(path, 'wb').write(struct.pack('<2i', 2, 1) + struct.pack('<i', len(nm)) + nm + struct.pack('<i', N) + b''.join(frames))

def cmd_check(a, pre=None):
    k, wn, W, P, tip, glass = pre or setup(a)
    d = open(a.anim, 'rb').read(); ver, cnt = struct.unpack_from('<2i', d, 0); p = 8
    for _ in range(cnt):
        n, = struct.unpack_from('<i', d, p); p += 4; nm = d[p:p + n].decode(); p += n
        fc, = struct.unpack_from('<i', d, p); p += 4; fl = 10 if ver == 2 else 16
        if nm != a.wiper: p += fc * fl * 4; continue
        local0, parent = wn[3], wn[5]; Lw = np.linalg.inv(local0 @ parent)
        Wl = np.c_[W, np.ones(len(W))] @ Lw                    # verts in wiper-node space
        ti = np.argmax(np.linalg.norm(W - P, axis=1))
        for i in range(0, fc, max(1, fc // 14)):
            x, y, z, w, tx, ty, tz = struct.unpack_from('<7f', d, p + i * fl * 4)
            M = np.eye(4)
            M[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
                         [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
                         [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]]
            M[3, :3] = (tx, ty, tz)
            V = (Wl @ M @ parent)[:, :3]
            c = clearance(V[::3], glass)
            print(f'frame {i:3d}  tip {np.round(V[ti], 3).tolist()}  min dy to glass {"-" if c is None else f"{c:+.4f}"}')
        return
    print(f'node {a.wiper!r} not in {a.anim}')

# ---------------------------------------------------------------- bend: split the wiper so the blade follows the glass
def glass_gap(glass, v):
    """Signed distance from v to the glass plane of the triangle under it (vertical ray); None off-glass."""
    t = glass.t; x, z = v[0], v[2]
    x0, z0, x1, z1, x2, z2 = t[:, 0, 0], t[:, 0, 2], t[:, 1, 0], t[:, 1, 2], t[:, 2, 0], t[:, 2, 2]
    den = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2); ok = np.abs(den) > 1e-12; den = np.where(ok, den, 1)
    l0 = ((z1 - z2) * (x - x2) + (x2 - x1) * (z - z2)) / den; l1 = ((z2 - z0) * (x - x2) + (x0 - x2) * (z - z2)) / den
    hit = np.where(ok & (l0 >= -1e-6) & (l1 >= -1e-6) & (1 - l0 - l1 >= -1e-6))[0]
    if not len(hit): return None
    ys = l0 * t[:, 0, 1] + l1 * t[:, 1, 1] + (1 - l0 - l1) * t[:, 2, 1]; tr = t[hit[np.argmax(ys[hit])]]
    n = np.cross(tr[1] - tr[0], tr[2] - tr[0]); n /= np.linalg.norm(n)
    return float((v - tr[0]) @ (n if n[1] > 0 else -n))

def gaps(glass, X):
    """Vectorised glass_gap for points X (n,3); NaN where the point is not over the glass."""
    t = glass.t
    if not hasattr(glass, 'n'):
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); n /= np.linalg.norm(n, axis=1)[:, None]
        glass.n = n * np.sign(n[:, 1:2] + 1e-12)
    x, z = X[:, 0:1], X[:, 2:3]
    x0, z0, x1, z1, x2, z2 = t[:, 0, 0], t[:, 0, 2], t[:, 1, 0], t[:, 1, 2], t[:, 2, 0], t[:, 2, 2]
    den = (z1 - z2) * (x0 - x2) + (x2 - x1) * (z0 - z2); ok = np.abs(den) > 1e-12; den = np.where(ok, den, 1)
    l0 = ((z1 - z2) * (x - x2) + (x2 - x1) * (z - z2)) / den; l1 = ((z2 - z0) * (x - x2) + (x0 - x2) * (z - z2)) / den
    hit = ok & (l0 >= -1e-6) & (l1 >= -1e-6) & (1 - l0 - l1 >= -1e-6)
    ys = np.where(hit, l0 * t[:, 0, 1] + l1 * t[:, 1, 1] + (1 - l0 - l1) * t[:, 2, 1], -np.inf)
    j = np.argmax(ys, axis=1); g = np.einsum('ij,ij->i', X - t[j, 0], glass.n[j])
    glass.last_n = glass.n[j]                                  # normal under each point, for callers that need it
    return np.where(hit.any(1), g, np.nan)

def min_gap(glass, X):
    g = gaps(glass, X)
    return float(np.nanmin(g)) if np.isfinite(g).any() else None

def surface_samples(tris, n=2):
    """Barycentric grid of points on each triangle (tris: (m,3,3)); n=2 gives corners, edge midpoints, centre."""
    w = [(i / n, j / n, 1 - (i + j) / n) for i in range(n + 1) for j in range(n + 1 - i)]
    if n == 2: w.append((1 / 3, 1 / 3, 1 / 3))
    w = np.array(w)
    return np.einsum('kw,mwc->mkc', w, tris).reshape(-1, 3)

def islands(V, idx):
    par = list(range(len(V)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for t in range(0, len(idx), 3):
        x, y, z = idx[t:t + 3]; par[f(x)] = f(y); par[f(y)] = f(z)
    seen = {}
    for i, v in enumerate(V):
        kk = tuple(np.round(v, 4))
        if kk in seen: par[f(i)] = f(seen[kk])
        else: seen[kk] = i
    return np.array([f(i) for i in range(len(V))])

def compose(T2, T1): return (T2[0] @ T1[0], T2[0] @ T1[1] + T2[1])
def rot_about(C, w, d): R = rot(w, d); return (R, C - R @ C)
def apply(T, X): return X @ T[0].T + T[1]
def row_form(T): A = np.eye(4); A[:3, :3] = T[0].T; A[3, :3] = T[1]; return A

def underside_gap(glass, X, bins):
    """Highest point of the blade underside: max over slices (bins) of each slice's lowest gap. None if off-glass."""
    g = gaps(glass, X); ok = np.isfinite(g)
    if not ok.any(): return None
    return max(float(g[ok & (bins == b)].min()) for b in np.unique(bins[ok]))

def seat(glass, X, make, bins):
    """Find bend angle d (positive = down) that presses the whole underside of X onto the glass (highest point at 0).
    Where the glass folds under a piece, part of the rubber ends up a fraction of a mm inside it rather than above."""
    # scan, then bisect the sign change nearest to no bend; pieces with nothing over the glass stay straight
    min_gap = lambda glass, Y: underside_gap(glass, Y, bins)
    grid = np.linspace(-0.3, 0.3, 41); g = [min_gap(glass, apply(make(d), X)) for d in grid]
    best = None
    for j in range(len(grid) - 1):
        if g[j] is not None and g[j + 1] is not None and g[j] >= 0 > g[j + 1]:
            if best is None or abs(grid[j]) < abs(grid[best]): best = j
    if best is None:                                          # no exact touch: take the angle closest to touching
        ok = [j for j in range(len(grid)) if g[j] is not None]
        return float(grid[min(ok, key=lambda j: (abs(g[j]), abs(grid[j])))]) if ok else 0.0
    lo, hi = grid[best], grid[best + 1]
    for _ in range(30):
        m = (lo + hi) / 2; gm = min_gap(glass, apply(make(m), X))
        if gm is None: break
        lo, hi = (m, hi) if gm >= 0 else (lo, m)
    return lo

def kn5_str(s): b = s.encode(); return struct.pack('<i', len(b)) + b

def slice_mesh(A, idx, dv, cuts):
    """Cut triangles at planes d = c (A: per-vertex pos3 nrm3 uv2 tan3). Returns [(3 vertex rows, centroid d, source tri)]."""
    pieces = []
    for ti, t in enumerate(idx):
        polys = [([A[j] for j in t], [dv[j] for j in t])]
        for c in cuts:
            nxt = []
            for pa, pd in polys:
                lo, hi = ([], []), ([], [])
                for m in range(len(pa)):
                    a1, d1, a2, d2 = pa[m], pd[m], pa[(m + 1) % len(pa)], pd[(m + 1) % len(pa)]
                    side = lo if d1 < c else hi; side[0].append(a1); side[1].append(d1)
                    if (d1 < c) != (d2 < c):
                        x = a1 + (c - d1) / (d2 - d1) * (a2 - a1)
                        for sl in (slice(3, 6), slice(8, 11)):
                            n = np.linalg.norm(x[sl]); x[sl] = x[sl] / n if n else x[sl]
                        for q in (lo, hi): q[0].append(x); q[1].append(c)
                nxt += [q for q in (lo, hi) if len(q[0]) >= 3]
            polys = nxt
        for pa, pd in polys:
            for m in range(1, len(pa) - 1):
                pieces.append(([pa[0], pa[m], pa[m + 1]], (pd[0] + pd[m] + pd[m + 1]) / 3, ti))
    return pieces

def axis_lean(tilt, lean=0.0):
    t, l = math.radians(tilt), math.radians(lean)
    return np.array([math.sin(l), math.cos(l) * math.sin(t), math.cos(l) * math.cos(t)])

def bend_one(a, bak, wname, tilt, lean, sweep, pivot_end, offset='', park_rot=0.0):
    """Cut one wiper into hinged pieces and animate them. Returns (kn5 span, new node bytes, ksanim tracks, mesh names)."""
    a_src = argparse.Namespace(**{**vars(a), 'kn5': bak, 'wiper': wname, 'pivot_end': pivot_end, 'offset': offset, 'park_rot': park_rot})
    print(f'== {wname}')
    k, wn, W, P, tip, glass = setup(a_src)
    meshes = k.meshes_under(wname)
    if len(meshes) != 1 or meshes[0][2] not in k.raw: sys.exit('bend expects exactly one static mesh under the wiper node')
    raw = k.raw[meshes[0][2]]; idx = np.array(raw['idx']).reshape(-1, 3)
    A = np.frombuffer(raw['vraw'], dtype='<f4').reshape(-1, 11).astype(float)
    M0 = wn[3][:3, :3]
    if np.abs(np.linalg.norm(M0, axis=1) - 1).max() > 1e-3 or np.linalg.det(M0) < 0:
        # scaled or mirrored wiper node: ksanim frames are rotation+position only, so bake the node's
        # rotation/scale into the vertices and leave the node a plain translation
        A[:, :3] = A[:, :3] @ M0
        nrm = A[:, 3:6] @ np.linalg.inv(M0).T; A[:, 3:6] = nrm / np.maximum(np.linalg.norm(nrm, axis=1)[:, None], 1e-12)
        tan = A[:, 8:11] @ M0; A[:, 8:11] = tan / np.maximum(np.linalg.norm(tan, axis=1)[:, None], 1e-12)
        if np.linalg.det(M0) < 0: idx = idx[:, ::-1]
        local = np.eye(4); local[3, :3] = wn[3][3, :3]
        wn = (wn[0], wn[1], wn[2], local, local @ wn[5], wn[5], *wn[6:])
        print(f'baked node scale {np.round(np.linalg.norm(M0, axis=1), 3).tolist()} into the wiper vertices')
    world0, parent = wn[3] @ wn[5], wn[5]
    ax = axis_lean(tilt, lean); ang = math.radians(sweep)
    u_rest = tip - P; u_rest -= (u_rest @ ax) * ax; u_rest /= np.linalg.norm(u_rest)
    to_world = lambda X: X @ world0[:3, :3] + world0[3, :3]

    # blade = longest island that doesn't start at the hub (the arm does); hinge planes are spread evenly along it
    isl = islands(W, raw['idx']); rr = np.linalg.norm(W - P, axis=1)
    blade_id = max(set(isl), key=lambda i: np.ptp(rr[isl == i]) - (1 if rr[isl == i].min() < a.hub_radius else 0))
    dv = (W - P) @ u_rest; d0, d1 = dv[isl == blade_id].min(), dv.max()
    K = a.segments; L = (d1 - d0) / K; cuts = [d0 + j * L for j in range(K)]
    pieces = slice_mesh(A, idx, dv, cuts)
    segs = {}
    for tri, dc, ti in pieces:
        segs.setdefault(int(np.searchsorted(cuts, dc, side='right')), []).append((tri, isl[idx[ti][0]] == blade_id))
    # blade surface sample points per piece (world, rest pose); contact and the report both use these
    seg_blade, seg_dense, seg_bins = {}, {}, {}
    for s_ in range(1, K + 1):
        tris = [to_world(np.array([v[:3] for v in tri])) for tri, bl in segs.get(s_, []) if bl]
        seg_blade[s_] = surface_samples(np.array(tris), 6) if tris else np.zeros((0, 3))
        lo_d = cuts[s_ - 1]; hi_d = cuts[s_] if s_ < K else d1
        seg_bins[s_] = np.clip(((seg_blade[s_] - P) @ u_rest - lo_d) / (hi_d - lo_d) * 4, 0, 3).astype(int)  # 4 slices per piece
        seg_dense[s_] = surface_samples(np.array(tris), 16) if tris else np.zeros((0, 3))
    # hinge points: lowest blade point on each cut plane
    joints, rings = {}, {}
    for s_ in range(2, K + 1):
        X = seg_blade[s_][np.abs((seg_blade[s_] - P) @ u_rest - cuts[s_ - 1]) < 1e-5]
        rings[s_] = X; joints[s_] = X[np.argmin((X - P) @ ax)]
    print(f'blade {d0:.3f}-{d1:.3f} m from pivot, {K} hinged pieces of {L * 1000:.0f} mm, {len(pieces)} triangles after cutting')

    # per frame: sweep about the pivot, pitch about the pivot to seat piece 1, then hinge each piece down onto the glass
    N = a.frames; frames = []
    for i in range(N):
        th = ang * (1 - math.cos(2 * math.pi * i / (N - 1))) / 2
        Tb = rot_about(P, ax, th); w0 = np.cross(ax, Tb[0] @ u_rest)
        p0 = seat(glass, seg_blade[1], lambda d: compose(rot_about(P, w0, d), Tb), seg_bins[1])
        T = [compose(rot_about(P, w0, p0), Tb)] * 2
        for s_ in range(2, K + 1):
            Tp = T[-1]; w = np.cross(Tp[0] @ ax, Tp[0] @ u_rest)
            # hinge on the point of this piece's cut face that is lowest relative to the glass right now
            ring = apply(Tp, rings[s_]); gr = gaps(glass, ring)
            if np.isfinite(gr).any():
                j = int(np.nanargmin(gr)); J = ring[j]
                if gr[j] < -0.0005:                              # inherited penetration: lift this piece clear
                    lift = -gr[j] * glass.last_n[j]; Tp = (Tp[0], Tp[1] + lift); J = J + lift
            else:
                J = apply(Tp, joints[s_][None])[0]
            d = seat(glass, seg_blade[s_], lambda d, J=J, w=w, Tp=Tp: compose(rot_about(J, w, d), Tp), seg_bins[s_])
            T.append(compose(rot_about(J, w, d), Tp))
            if os.environ.get('WIPER_DEBUG') == str(i):
                mk = lambda d: compose(rot_about(J, w, d), Tp)
                print(f'  piece {s_} bend {math.degrees(d):+.2f} deg  joint gap {glass_gap(glass, J)}  gap@-17deg {min_gap(glass, apply(mk(-0.3), seg_blade[s_]))}  @0 {min_gap(glass, apply(mk(0), seg_blade[s_]))}  @+17deg {min_gap(glass, apply(mk(0.3), seg_blade[s_]))}')
        frames.append((Tb, T))

    # ---- write kn5: wiper node -> one transform + mesh per piece
    out = struct.pack('<i', 1) + kn5_str(wname) + struct.pack('<ib', len(segs), 1) + struct.pack('<16f', *wn[3].ravel())
    seg_names = []
    for s_ in sorted(segs):
        verts, keys, tri_idx = [], {}, []
        for tri, _ in segs[s_]:
            for v in tri:
                b_ = struct.pack('<11f', *v)
                if b_ not in keys: keys[b_] = len(verts); verts.append(b_)
                tri_idx.append(keys[b_])
        lv = np.array([struct.unpack('<3f', v_[:12]) for v_ in verts]); c = (lv.min(0) + lv.max(0)) / 2
        rad = float(np.linalg.norm(lv - c, axis=1).max()); nm = f'{wname}_seg{s_}'; seg_names.append((s_, nm))
        out += struct.pack('<i', 1) + kn5_str(nm) + struct.pack('<ib', 1, 1) + struct.pack('<16f', *np.eye(4).ravel())
        out += struct.pack('<i', 2) + kn5_str(nm) + struct.pack('<ib', 0, 1) + struct.pack('<bbb', *raw['flags'])
        out += struct.pack('<i', len(verts)) + b''.join(verts) + struct.pack('<i', len(tri_idx)) + struct.pack(f'<{len(tri_idx)}H', *tri_idx)
        out += struct.pack('<iiff', raw['mid'], raw['layer'], *raw['lod']) + struct.pack('<4f', *c, rad) + struct.pack('<b', raw['renderable'])

    # ---- write ksanim: wiper node sweeps rigidly (LODs follow it); pieces carry the bend relative to it
    inv_parent = np.linalg.inv(parent); inv_w0 = np.linalg.inv(world0)
    def q_pos(Lm):
        q = quat_from_rot(Lm[:3, :3].T); q = q if q[3] >= 0 else -q
        return struct.pack('<10f', *q, *Lm[3, :3], 1, 1, 1)
    tracks = [(wname, [q_pos(world0 @ row_form(Tb) @ inv_parent) for Tb, _ in frames])]
    for s_, nm in seg_names:
        tracks.append((nm, [q_pos(world0 @ row_form(T[s_]) @ np.linalg.inv(row_form(Tb)) @ inv_w0) for Tb, T in frames]))

    # ---- report: blade surface vs glass in 5 mm bins along the blade (lowest point of each bin)
    worst_hi, worst_lo = (0, 0), (0, 0); bins = np.arange(d0, d1 + 0.005, 0.005)
    for i in range(N):
        Tb, T = frames[i]; per_bin = {}
        for s_ in range(1, K + 1):
            X = seg_dense[s_]
            if not len(X): continue
            g = gaps(glass, apply(T[s_], X)); b_ = np.digitize((X - P) @ u_rest, bins)
            for bb, gg in zip(b_, g):
                if np.isfinite(gg): per_bin[bb] = min(per_bin.get(bb, 9), gg)
        v = list(per_bin.values())
        if os.environ.get('WIPER_DEBUG') == str(i):
            for bb in sorted(per_bin): print(f'  d {bins[bb - 1]:.3f} gap {per_bin[bb] * 1000:+.2f} mm')
        if v:
            worst_hi = max(worst_hi, (max(v), i)); worst_lo = min(worst_lo, (min(v), i))
        if i % 7 == 0:
            print(f'frame {i:3d}  blade over glass {len(v) * 5:3d} mm  gap {min(v) * 1000 if v else 0:+.2f} .. {max(v) * 1000 if v else 0:+.2f} mm')
    print(f'all frames: blade gap {worst_lo[0] * 1000:+.2f} mm (frame {worst_lo[1]}) .. {worst_hi[0] * 1000:+.2f} mm (frame {worst_hi[1]})')
    return k.span[wname], out, tracks, [nm for _, nm in seg_names], k.d

def cmd_bend(a):
    import os, shutil
    bak = a.kn5 + '.bak_wiper'
    if not os.path.exists(bak): shutil.copy2(a.kn5, bak); print('backup', bak)
    names = a.wiper.split(','); n = len(names)
    per = lambda v, conv: [conv(x) for x in v.split(',')] * (1 if ',' in v else n)   # one value, or one per wiper
    tilts, sweeps = per(a.tilt, float), per(a.sweep, float); leans = per(a.lean, float); ends = per(a.pivot_end, str)
    offs = per(a.offset, str) if a.offset else [''] * n; prots = per(a.park_rot, float); paxes = per(a.park_axis, str) if a.park_axis else [''] * n
    results = [bend_one(argparse.Namespace(**{**vars(a), 'park_axis': paxes[i]}), bak, w, tilts[i], leans[i], sweeps[i], ends[i], offs[i], prots[i]) for i, w in enumerate(names)]
    # every wiper is rebuilt from the untouched backup, so splice all of them in one pass (last span first)
    data = results[0][4]
    for (s0, e0), out, _, _, _ in sorted(results, key=lambda r: -r[0][0]): data = data[:s0] + out + data[e0:]
    open(a.kn5, 'wb').write(data); KN5(a.kn5)                  # re-parse as a sanity check
    print('wrote', a.kn5)
    tracks = [t for r in results for t in r[2]]
    blob = struct.pack('<2i', 2, len(tracks))
    for nm, fr in tracks: blob += kn5_str(nm) + struct.pack('<i', len(fr)) + b''.join(fr)
    open(a.out, 'wb').write(blob); print('wrote', a.out, f'({len(tracks)} tracks)')
    print('ext_config WIPERS =', ', '.join(nm for r in results for nm in r[3]))

def cmd_fitaxis(a):
    """Per wiper: axis (tilt, lean) that keeps the rigid blade closest to the glass over a provisional sweep,
    the sweep direction (up the glass), and the angle where the blade would leave the windscreen."""
    names = a.wiper.split(','); ends = (a.pivot_end.split(',') * len(names))[:len(names)]; args = []
    for wname, end in zip(names, ends):
        s_ = argparse.Namespace(**{**vars(a), 'wiper': wname, 'pivot_end': end, 'pivot': None, 'offset': a.offset})
        print(f'== {wname}'); k, wn, W, P, tip, glass = setup(s_)
        raw = k.raw[k.meshes_under(wname)[0][2]]; idx = np.array(raw['idx']).reshape(-1, 3)
        isl = islands(W, raw['idx']); r = np.linalg.norm(W - P, axis=1)
        blade_id = max(set(isl), key=lambda i: np.ptp(r[isl == i]) - (1 if r[isl == i].min() < a.hub_radius else 0))
        X = surface_samples(W[idx[np.all(isl[idx] == blade_id, axis=1)]], 6); u = (tip - P) / np.linalg.norm(tip - P)
        bins = np.clip(((X - P) @ u) / 0.02, 0, 60).astype(int)
        def blade_gap(V):
            g = gaps(glass, V); ok = np.isfinite(g)
            if ok.mean() < 0.98: return None
            return [float(g[ok & (bins == b)].min()) for b in np.unique(bins[ok])]
        def score(ax, sign):
            worst = 0
            for deg in np.linspace(0, a.sweep, 8):
                gb = blade_gap((X - P) @ rot(ax, math.radians(sign * deg)).T + P)
                if gb is None and deg < 15: continue                 # parked blades often rest partly in the cowl
                if gb is None: return None
                worst = max(worst, max(abs(x) for x in gb))
            return worst
        best = None
        for tilt in np.arange(10, 85, 2.5):
            for lean in np.arange(-40, 41, 2.5):
                ax = axis_lean(tilt, lean); sign = 1 if (rot(ax, 0.3) @ (tip - P))[1] > (tip - P)[1] else -1
                sc = score(ax, sign)
                if sc is not None and (best is None or sc < best[0]): best = (sc, tilt, lean, sign)
        if best is None: print('  no axis keeps the blade on the glass for that sweep; try a smaller --sweep'); continue
        sc, tilt, lean, sign = best; ax = axis_lean(tilt, lean); limit = None
        for deg in range(16, 181, 2):
            if blade_gap((X - P) @ rot(ax, math.radians(sign * deg)).T + P) is None: limit = deg; break
        print(f'  pivot {np.round(P, 3).tolist()}  tilt {tilt}  lean {lean}  sweep {sign * a.sweep:+g}  rigid blade gap up to {sc * 1000:.1f} mm'
              f'  blade leaves glass at {limit if limit is not None else ">180"} deg')
        args.append((wname, tilt, lean, sign * a.sweep, end))
    if args:
        print('\nbend args: --wiper ' + ','.join(x[0] for x in args) + ' --tilt ' + ','.join(f'{x[1]:g}' for x in args) +
              ' --lean ' + ','.join(f'{x[2]:g}' for x in args) + ' --sweep ' + ','.join(f'{x[3]:g}' for x in args) +
              ' --pivot-end ' + ','.join(x[4] for x in args))

def ksanim_frame(Lm):
    """Row-form local matrix (scale * rotation, then translation) -> ksanim v2 frame bytes, keeping the node's scale."""
    sc = np.linalg.norm(Lm[:3, :3], axis=1); R = Lm[:3, :3] / sc[:, None]
    q = quat_from_rot(R.T); q = q if q[3] >= 0 else -q
    return struct.pack('<10f', *q, *Lm[3, :3], *sc)

def frame_matrix(f):
    x, y, z, w, tx, ty, tz, sx, sy, sz = f; M = np.eye(4)
    M[:3, :3] = np.diag([sx, sy, sz]) @ np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
                                                   [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
                                                   [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]])
    M[3, :3] = (tx, ty, tz); return M

def cmd_rigid(a):
    """One-piece wipers: sweep about the pivot, and on every frame tilt the whole wiper about the pivot (like the arm
    spring) so the blade sits as close to the glass as a straight blade can. The kn5 mesh is left untouched; only the
    wiper node's matrix is rewritten when the wiper is moved (--offset / --park-rot)."""
    import shutil
    bak = a.kn5 + '.bak_wiper'
    if os.path.exists(bak): shutil.copy2(bak, a.kn5); print('restored original model from', bak)
    else: shutil.copy2(a.kn5, bak); print('backup', bak)
    names = a.wiper.split(','); n = len(names)
    per = lambda v, conv: [conv(x) for x in v.split(',')] * (1 if ',' in v else n)
    tilts, leans, sweeps, ends = per(a.tilt, float), per(a.lean, float), per(a.sweep, float), per(a.pivot_end, str)
    offs = per(a.offset, str) if a.offset else [''] * n; prots = per(a.park_rot, float); paxes = per(a.park_axis, str) if a.park_axis else [''] * n
    data = bytearray(open(a.kn5, 'rb').read()); tracks = []; N = a.frames
    for i, wname in enumerate(names):
        s_ = argparse.Namespace(**{**vars(a), 'kn5': bak, 'wiper': wname, 'pivot_end': ends[i], 'offset': offs[i],
                                   'park_rot': prots[i], 'park_axis': paxes[i], 'pivot': None})
        print(f'== {wname}'); k, wn, W, P, tip, glass = setup(s_)
        raw = k.raw[k.meshes_under(wname)[0][2]]; idx = np.array(raw['idx']).reshape(-1, 3)
        isl = islands(W, raw['idx']); rr = np.linalg.norm(W - P, axis=1)
        blade_id = max(set(isl), key=lambda j: np.ptp(rr[isl == j]) - (1 if rr[isl == j].min() < a.hub_radius else 0))
        X = surface_samples(W[idx[np.all(isl[idx] == blade_id, axis=1)]], 6)
        ax = axis_lean(tilts[i], leans[i]); ang = math.radians(sweeps[i])
        u_rest = tip - P; u_rest -= (u_rest @ ax) * ax; u_rest /= np.linalg.norm(u_rest)
        bins = np.clip(((X - P) @ u_rest) / 0.02, 0, 60).astype(int)
        def cost(Y):
            g = gaps(glass, Y); ok = np.isfinite(g)
            if ok.mean() < 0.5: return None
            m = [float(g[ok & (bins == b)].min()) for b in np.unique(bins[ok])]
            return max(abs(min(m)), abs(max(m))), min(m), max(m)
        pitches, Tbs = [], []
        for f in range(N):
            th = ang * (1 - math.cos(2 * math.pi * f / (N - 1))) / 2
            Tb = rot_about(P, ax, th); w0 = np.cross(ax, Tb[0] @ u_rest); Tbs.append((Tb, w0))
            best = (None, 0.0)
            for d in np.linspace(-0.12, 0.12, 49):
                c = cost(apply(compose(rot_about(P, w0, d), Tb), X))
                if c is not None and (best[0] is None or c[0] < best[0]): best = (c[0], d)
            if best[0] is not None:
                for d in np.linspace(best[1] - 0.005, best[1] + 0.005, 11):
                    c = cost(apply(compose(rot_about(P, w0, d), Tb), X))
                    if c is not None and c[0] < best[0]: best = (c[0], d)
            pitches.append(best[1])
        pitches = np.convolve(np.pad(pitches, 2, mode='edge'), np.ones(5) / 5, mode='valid')   # no jitter between frames
        world0, parent = wn[4], wn[5]; inv_parent = np.linalg.inv(parent); frames, worst = [], [0, 0]
        for f in range(N):
            Tb, w0 = Tbs[f]; T = compose(rot_about(P, w0, pitches[f]), Tb)
            frames.append(ksanim_frame(world0 @ row_form(T) @ inv_parent))
            c = cost(apply(T, X))
            if c: worst = [min(worst[0], c[1]), max(worst[1], c[2])]
        # self-check: rebuild every frame from the written floats and compare with the intended wiper position
        rest_local = np.c_[W, np.ones(len(W))] @ np.linalg.inv(world0)
        err = max(np.abs((rest_local @ frame_matrix(struct.unpack('<10f', fr)) @ parent)[:, :3] -
                         apply(compose(rot_about(P, Tbs[f][1], pitches[f]), Tbs[f][0]), W)).max() for f, fr in enumerate(frames))
        print(f'  sweep {sweeps[i]:+g} deg, arm tilt {math.degrees(min(pitches)):+.1f}..{math.degrees(max(pitches)):+.1f} deg, '
              f'blade vs glass {worst[0] * 1000:+.1f} .. {worst[1] * 1000:+.1f} mm, replay error {err * 1000:.3f} mm')
        tracks.append((wname, frames))
        if offs[i] or prots[i]:                               # moved wiper: parked pose goes into the kn5 too
            s0 = k.span[wname][0]; mo = s0 + 4 + 4 + len(wname.encode()) + 4 + 1
            T0 = compose(rot_about(P, Tbs[0][1], pitches[0]), Tbs[0][0])
            data[mo:mo + 64] = struct.pack('<16f', *(world0 @ row_form(T0) @ inv_parent).ravel())
            print('  moved wiper: parked pose written to the model')
    open(a.kn5, 'wb').write(bytes(data)); KN5(a.kn5)
    blob = struct.pack('<2i', 2, len(tracks))
    for nm, fr in tracks: blob += kn5_str(nm) + struct.pack('<i', N) + b''.join(fr)
    open(a.out, 'wb').write(blob); print('wrote', a.kn5, 'and', a.out)

def cmd_transplant(a):
    """Copy a wiper (transform node + its one mesh) from a donor car into a car that has none, using one of the
    target's own materials. Keeps the untouched model as .bak_original and also writes the result to .bak_wiper,
    which is what fit/rigid build from."""
    import shutil
    orig = a.kn5 + '.bak_original'
    if not os.path.exists(orig): shutil.copy2(a.kn5, orig); print('backup', orig)
    t = KN5(orig); d = KN5(a.donor)
    if any(n[2] == a.name for n in t.nodes): sys.exit(f'{a.name!r} already exists in {a.kn5}')
    dn = d.node(a.wiper); mesh = d.meshes_under(a.wiper)
    if len(mesh) != 1 or mesh[0][2] not in d.raw: sys.exit('donor wiper must be one static mesh under one node')
    raw = d.raw[mesh[0][2]]
    if a.material not in t.mats: sys.exit(f'material {a.material!r} not in target')
    local = dn[4].copy(); local[3, :3] += np.array([float(v) for v in a.offset.split(':')])    # donor world pose, shifted
    lv = np.frombuffer(raw['vraw'], dtype='<f4').reshape(-1, 11)[:, :3]; c = (lv.min(0) + lv.max(0)) / 2
    rad = float(np.linalg.norm(lv - c, axis=1).max())
    node = struct.pack('<i', 1) + kn5_str(a.name) + struct.pack('<ib', 1, 1) + struct.pack('<16f', *local.ravel())
    node += struct.pack('<i', 2) + kn5_str(a.name) + struct.pack('<ib', 0, 1) + struct.pack('<bbb', *raw['flags'])
    node += struct.pack('<i', len(lv)) + raw['vraw'] + struct.pack('<i', len(raw['idx'])) + struct.pack(f'<{len(raw["idx"])}H', *raw['idx'])
    node += struct.pack('<iiff', t.mats.index(a.material), raw['layer'], *raw['lod']) + struct.pack('<4f', *c, rad) + struct.pack('<b', raw['renderable'])
    root = t.nodes[0][2]; s0, e0 = t.span[root]; cnt_at = s0 + 4 + 4 + len(root.encode('latin1'))
    data = bytearray(t.d); cnt, = struct.unpack_from('<i', data, cnt_at); struct.pack_into('<i', data, cnt_at, cnt + 1)
    data = bytes(data[:e0]) + node + bytes(data[e0:])
    for p in (a.kn5, a.kn5 + '.bak_wiper'): open(p, 'wb').write(data)
    KN5(a.kn5); print(f'added {a.name!r} ({len(lv)} verts, material {a.material}) under {root!r}; wrote {a.kn5} and .bak_wiper')

def cmd_extract(a):
    """Pull a wiper that was merged into a bigger mesh out into its own node (same material, same look), and delete
    other merged parts (e.g. a second wiper). Parts are the mesh's loose pieces lying wholly inside the given boxes.
    Keeps the untouched model as .bak_original; writes the result to the kn5 and .bak_wiper."""
    import shutil
    orig = a.kn5 + '.bak_original'
    if not os.path.exists(orig): shutil.copy2(a.kn5, orig); print('backup', orig)
    t = KN5(orig)
    if any(n[2] == a.name for n in t.nodes): sys.exit(f'{a.name!r} already exists')
    m = [n for n in t.nodes if n[1] == 'M' and n[2] == a.mesh][0]; raw = t.raw[a.mesh]
    V, idx = m[6], np.array(raw['idx']).reshape(-1, 3); isl = islands(V, raw['idx'])
    def parts_in(box):
        b = np.array([float(v) for v in box.split(':')]).reshape(3, 2)
        return {i for i in set(isl) if np.all((V[isl == i] >= b[:, 0]) & (V[isl == i] <= b[:, 1]))}
    keep = parts_in(a.keep_box); drop = parts_in(a.drop_box) if a.drop_box else set()
    print(f'wiper parts: {[int((isl == i).sum()) for i in keep]} verts; deleted parts: {[int((isl == i).sum()) for i in drop]} verts')
    if not keep: sys.exit('nothing inside --keep-box')
    tri_isl = isl[idx[:, 0]]; take = np.isin(tri_isl, list(keep)); gone = take | np.isin(tri_isl, list(drop))
    # new wiper mesh: its triangles and the vertices they use, in the source mesh's coordinates
    used = np.unique(idx[take]); remap = {o: n for n, o in enumerate(used)}
    A = np.frombuffer(raw['vraw'], dtype='<f4').reshape(-1, 11); lv = A[used]
    c = (lv[:, :3].min(0) + lv[:, :3].max(0)) / 2; rad = float(np.linalg.norm(lv[:, :3] - c, axis=1).max())
    root = t.nodes[0][2]; local = m[5] @ np.linalg.inv([n for n in t.nodes if n[2] == root][0][4])
    node = struct.pack('<i', 1) + kn5_str(a.name) + struct.pack('<ib', 1, 1) + struct.pack('<16f', *local.ravel())
    node += struct.pack('<i', 2) + kn5_str(a.name) + struct.pack('<ib', 0, 1) + struct.pack('<bbb', *raw['flags'])
    ni = [remap[o] for o in idx[take].ravel()]
    node += struct.pack('<i', len(used)) + lv.astype('<f4').tobytes() + struct.pack('<i', len(ni)) + struct.pack(f'<{len(ni)}H', *ni)
    node += struct.pack('<iiff', raw['mid'], raw['layer'], *raw['lod']) + struct.pack('<4f', *c, rad) + struct.pack('<b', raw['renderable'])
    # source mesh keeps its vertices but loses the extracted/deleted triangles
    keep_idx = idx[~gone].ravel(); old = len(raw['idx']); at = raw['ic_at']
    data = t.d[:at] + struct.pack('<i', len(keep_idx)) + struct.pack(f'<{len(keep_idx)}H', *keep_idx) + t.d[at + 4 + old * 2:]
    shift = len(data) - len(t.d)
    s0, e0 = t.span[root]; cnt_at = s0 + 4 + 4 + len(root.encode('latin1')); e0 += shift if e0 > at else 0
    data = bytearray(data); cnt, = struct.unpack_from('<i', data, cnt_at); struct.pack_into('<i', data, cnt_at, cnt + 1)
    data = bytes(data[:e0]) + node + bytes(data[e0:])
    for p in (a.kn5, a.kn5 + '.bak_wiper'): open(p, 'wb').write(data)
    KN5(a.kn5); print(f'{a.mesh}: {len(idx)} -> {int((~gone).sum())} triangles; new node {a.name!r} ({len(used)} verts, {int(take.sum())} triangles)')

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
ex = sp.add_parser('extract'); ex.add_argument('kn5'); ex.add_argument('--mesh', required=True); ex.add_argument('--name', default='wiper')
ex.add_argument('--keep-box', required=True, help='x0:x1:y0:y1:z0:z1 - loose parts wholly inside become the wiper')
ex.add_argument('--drop-box', default='', help='x0:x1:y0:y1:z0:z1 - loose parts wholly inside are deleted')
tp = sp.add_parser('transplant'); tp.add_argument('kn5'); tp.add_argument('--donor', required=True); tp.add_argument('--wiper', required=True)
tp.add_argument('--material', required=True); tp.add_argument('--name', default='wiper'); tp.add_argument('--offset', default='0:0:0', help='dx:dy:dz shift from the donor position')
rg = sp.add_parser('rigid'); rg.add_argument('kn5'); rg.add_argument('--wiper', required=True); rg.add_argument('--glass', required=True)
rg.add_argument('--tilt', required=True); rg.add_argument('--lean', default='0'); rg.add_argument('--sweep', required=True)
rg.add_argument('--pivot-end', default='auto'); rg.add_argument('--offset', default=''); rg.add_argument('--park-rot', default='0')
rg.add_argument('--park-axis', default=''); rg.add_argument('--hub-radius', type=float, default=0.05); rg.add_argument('--glass-zmin', type=float)
rg.add_argument('--frames', type=int, default=100); rg.add_argument('--out', default='car_wiper.ksanim')
fa = sp.add_parser('fitaxis'); fa.add_argument('kn5'); fa.add_argument('--wiper', required=True); fa.add_argument('--glass', required=True)
fa.add_argument('--sweep', type=float, default=85, help='provisional sweep magnitude, deg'); fa.add_argument('--pivot-end', default='auto')
fa.add_argument('--hub-radius', type=float, default=0.05); fa.add_argument('--glass-zmin', type=float); fa.add_argument('--pivot')
fa.add_argument('--offset', default='', help='move the wiper first: dx:dy:dz metres')
fa.add_argument('--park-rot', type=float, default=0, help='turn the parked wiper about its pivot first, deg')
fa.add_argument('--park-axis', default='', help='tilt:lean of the park-rot axis')
b = sp.add_parser('bend', help='DEPRECATED: cuts the wiper into hinged pieces - looks broken in-game, use rigid'); b.add_argument('kn5'); b.add_argument('--wiper', required=True); b.add_argument('--glass', required=True)
b.add_argument('--tilt', required=True, help='axis tilt from fit (comma list per wiper)'); b.add_argument('--sweep', required=True, help='signed sweep deg (comma list per wiper)')
b.add_argument('--lean', default='0', help='axis lean towards +x, deg (comma list per wiper)')
b.add_argument('--segments', type=int, default=10); b.add_argument('--frames', type=int, default=100); b.add_argument('--out', default='car_wiper.ksanim')
b.add_argument('--pivot'); b.add_argument('--pivot-end', default='auto', help='auto|min-x|max-x (comma list per wiper)')
b.add_argument('--hub-radius', type=float, default=0.05); b.add_argument('--glass-zmin', type=float)
b.add_argument('--offset', default='', help='move a wiper before animating: dx:dy:dz metres (comma list per wiper)')
b.add_argument('--park-rot', default='0', help='turn the parked wiper about its pivot, deg (comma list per wiper)')
b.add_argument('--park-axis', default='', help='tilt:lean of the park-rot axis, e.g. the fitaxis axis at the original position (comma list)')
t = sp.add_parser('tree'); t.add_argument('kn5')
for nm in ('fit', 'check'):
    s = sp.add_parser(nm); s.add_argument('kn5'); s.add_argument('--wiper', required=True); s.add_argument('--glass', required=True)
    s.add_argument('--pivot', help='x,y,z override'); s.add_argument('--pivot-end', default='auto', choices=['auto', 'min-x', 'max-x'])
    s.add_argument('--hub-radius', type=float, default=0.05); s.add_argument('--glass-zmin', type=float)
    if nm == 'fit':
        s.add_argument('--out', default='car_wiper.ksanim'); s.add_argument('--frames', type=int, default=100)
        s.add_argument('--sweep', type=float, help='fixed sweep in degrees instead of mirror-fit')
    else:
        s.add_argument('--anim', required=True)
a = ap.parse_args()
{'tree': cmd_tree, 'fit': cmd_fit, 'check': cmd_check, 'bend': cmd_bend, 'fitaxis': cmd_fitaxis, 'rigid': cmd_rigid, 'transplant': cmd_transplant, 'extract': cmd_extract}[a.cmd](a)
