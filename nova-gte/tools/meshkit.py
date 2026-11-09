"""Small mesh toolkit for the Nova parts (plain Python, no Blender): sweeps of a 2D profile along a plan path,
rounded-V plan paths, triangulated regions, and a JSON part format the Blender loader understands.

Part = {"verts": [[x,y,z],...], "faces": [[i,j,k(,l)],...], "mats": [name per face]} in the BA/photo frame
(car faces -Y, Z up, +X = car's left, ground = loaded tyre contact). The Blender side adds DZ.
"""
import json
import math

import numpy as np


class Part:
    def __init__(self):
        self.v = []; self.f = []; self.m = []

    def add_v(self, p):
        self.v.append([float(p[0]), float(p[1]), float(p[2])]); return len(self.v) - 1

    def add_f(self, idx, mat):
        self.f.append([int(i) for i in idx]); self.m.append(mat)

    def grid(self, P, mat, close_u=False, flip=False, mats=None):
        """P: array (nu, nv, 3) -> quads. mats(i, j) optional per-quad material."""
        P = np.asarray(P); nu, nv = P.shape[:2]
        base = len(self.v)
        for i in range(nu):
            for j in range(nv):
                self.add_v(P[i, j])
        for i in range(nu - (0 if close_u else 1)):
            i1 = (i + 1) % nu
            for j in range(nv - 1):
                q = [base + i * nv + j, base + i1 * nv + j, base + i1 * nv + j + 1, base + i * nv + j + 1]
                self.add_f(q[::-1] if flip else q, mats(i, j) if mats else mat)
        return base

    def merge(self, other):
        o = len(self.v); self.v += other.v
        self.f += [[i + o for i in f] for f in other.f]; self.m += other.m
        return self

    def mirrored(self):
        """Copy mirrored in X (faces reversed)."""
        p = Part(); p.v = [[-x, y, z] for x, y, z in self.v]; p.f = [f[::-1] for f in self.f]; p.m = list(self.m)
        return p

    def weld(self, tol=1e-6):
        V = np.asarray(self.v); key = np.round(V / tol).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        order = np.argsort(first); remap = np.empty_like(order); remap[order] = np.arange(len(order))
        self.v = V[first[order]].tolist()
        nf, nm = [], []
        for f, m in zip(self.f, self.m):
            g = [int(remap[inv[i]]) for i in f]
            g2 = [a for k, a in enumerate(g) if a != g[k - 1]]
            if len(set(g2)) >= 3:
                nf.append(g2); nm.append(m)
        self.f, self.m = nf, nm
        return self

    def to_dict(self):
        mats = sorted(set(self.m))
        return {"verts": [[round(c, 6) for c in v] for v in self.v], "faces": self.f,
                "mats": mats, "mat_idx": [mats.index(m) for m in self.m]}


def save(parts, path):
    with open(path, "w") as fh:
        json.dump({k: p.to_dict() for k, p in parts.items()}, fh, separators=(",", ":"))


# ---------------- plan paths ----------------
def v_arc_path(y0, a, R, xs, y_end, ds=0.01, n_arc=24):
    """Left-half plan path from the centreline: straight V line y = y0 + a*x, an arc of radius R tangent to it
    and to the side line x = xs, then the side line back to y_end. Returns (pts (n,2), tangents, s)."""
    k = math.sqrt(1 + a * a)
    x1 = xs - R + R * a / k
    cx, cy = xs - R, y0 + a * x1 + R / k
    pts = []
    n1 = max(2, int(math.ceil(x1 / ds)))
    for i in range(n1):
        x = x1 * i / n1; pts.append((x, y0 + a * x))
    th0 = math.atan2((y0 + a * x1) - cy, x1 - cx)      # angle of T1 seen from the centre
    th1 = 0.0                                            # T2 = (xs, cy)
    for i in range(n_arc):
        t = th0 + (th1 - th0) * i / n_arc
        pts.append((cx + R * math.cos(t), cy + R * math.sin(t)))
    n2 = max(2, int(math.ceil((y_end - cy) / ds)))
    for i in range(n2 + 1):
        pts.append((xs, cy + (y_end - cy) * i / n2))
    return resample_tan(np.array(pts))


def resample_tan(pts):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    keep = np.r_[True, np.diff(d) > 1e-7]
    pts, d = pts[keep], d[keep]
    t = np.gradient(pts, d, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    return pts, t, d


def sweep_var(path, tan, prof_fn, out_sign=-1.0):
    """Like sweep() but the profile depends on the path point: prof_fn(x, y) -> list of (d, z), same length."""
    nrm = np.c_[-tan[:, 1], tan[:, 0]] * out_sign
    rows = [prof_fn(p[0], p[1]) for p in path]
    G = np.zeros((len(path), len(rows[0]), 3))
    for i, pr in enumerate(rows):
        for j, (d, z) in enumerate(pr):
            G[i, j] = (path[i, 0] + nrm[i, 0] * d, path[i, 1] + nrm[i, 1] * d, z)
    return G


def sweep(path, tan, profile, out_sign=-1.0):
    """profile: list of (d, z) with d along the outward plan normal. Returns grid (n_path, n_prof, 3).
    Outward normal of a left-half path running from the centreline outwards and back = (-t_y, t_x) * out_sign."""
    nrm = np.c_[-tan[:, 1], tan[:, 0]] * out_sign
    G = np.zeros((len(path), len(profile), 3))
    for j, (d, z) in enumerate(profile):
        G[:, j, 0] = path[:, 0] + nrm[:, 0] * d
        G[:, j, 1] = path[:, 1] + nrm[:, 1] * d
        G[:, j, 2] = z
    return G


def full_from_half(G):
    """Mirror a left-half sweep grid (rows from the centreline outwards) into a full grid, centre shared."""
    M = G[::-1].copy(); M[:, :, 0] *= -1
    return np.concatenate([M[:-1], G], axis=0)


def spline_path(ctrl, ds=0.008, start_slope=0.0):
    """Smooth interpolating plan path through ctrl points (x, y) (scipy cubic spline in chord length), resampled
    at ~ds; returns (pts, tangents, s). The first point should be on the centreline with a tangent along +x."""
    from scipy.interpolate import CubicSpline
    C = np.asarray(ctrl, float)
    u = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    t0 = np.array([1.0, start_slope]); t0 /= np.linalg.norm(t0)
    cs = CubicSpline(u, C, bc_type=((1, t0), (1, np.array([0.0, 1.0]))))
    n = int(np.ceil(u[-1] / ds)) + 1
    uu = np.linspace(0, u[-1], n)
    return resample_tan(cs(uu))


def tri_region(outer, holes=(), max_area=None, quality=True):
    """Triangulate a 2D polygon (outer ring CCW, hole rings) with Triangle; returns (V2 (n,2), T (m,3)) with the
    input ring vertices first, in order (boundary kept: 'Y')."""
    import triangle
    from shapely.geometry import Polygon
    rings = [np.asarray(outer, float)] + [np.asarray(h, float) for h in holes]
    V, S, H = [], [], []
    for r in rings:
        i0 = len(V); V.extend(r.tolist()); n = len(r)
        S.extend([[i0 + k, i0 + (k + 1) % n] for k in range(n)])
    for h in holes:
        H.append(Polygon(h).representative_point().coords[0])
    opts = "p" + ("q28" if quality else "") + (f"a{max_area:.8f}" if max_area else "") + "Y"
    d = {"vertices": np.array(V), "segments": np.array(S)}
    if H:
        d["holes"] = np.array(H)
    t = triangle.triangulate(d, opts)
    return t["vertices"], t["triangles"]


def rounded_rect(x0, x1, z0, z1, r, n=6):
    """CCW rounded rectangle ring in 2D."""
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return np.array(pts)


def quad_patch(c00, c10, c11, c01, nu, nv):
    """Bilinear patch grid (nu+1, nv+1, 3) from corners (u along c00->c10, v along c00->c01)."""
    c00, c10, c11, c01 = map(np.asarray, (c00, c10, c11, c01))
    G = np.zeros((nu + 1, nv + 1, 3))
    for i in range(nu + 1):
        u = i / nu
        for j in range(nv + 1):
            v = j / nv
            G[i, j] = (1 - u) * (1 - v) * c00 + u * (1 - v) * c10 + u * v * c11 + (1 - u) * v * c01
    return G
