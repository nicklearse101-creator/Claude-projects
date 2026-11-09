"""New front wings built from scratch (Nik 2026-10-19: replace each part with new clean geometry). The old wing is
scanned in sections around the axis (x 0.40, z 0.55) along the car: ray from outside towards the axis at angle phi
(0 = straight out, + up) -> radius R(y, phi), both sides averaged (the model is ~3 mm asymmetric) and lightly
smoothed (7.5 mm along the car, ~0.5 deg across; never across the panel edges). That one surface holds the side,
the wing-line step above the arch, the shoulder and the flat top strip at the bonnet gap.
New quad grid (5 mm x 0.5 deg) trimmed to the panel's real edges - door shut line (y -0.6825), bonnet gap (2.5 mm
outside the bonnet's side line), the lamp unit (front_new: indicator edge y -1.578 below the lamp top, the lamp face
above it), the bumper top (z 0.537), the wheel arch (scan outline) and the sill (z 0.292 behind the arch) - with the
edge vertices snapped onto those lines and each edge rolled in (arch lip, shut lines, gutter). Old wing skin is cut
along the same lines and deleted. Car frame: x+ = car's left, y- = front, z up."""
import math
import os

import bmesh
import numpy as np

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

CX, CZ = 0.40, 0.55
YS = np.round(np.arange(-1.680, -0.6774, 0.005), 4)
PH = np.radians(np.arange(-60.0, 66.01, 0.5))
YR = -0.6825                                  # door front shut line (groove at -0.680)
Z_BUMPER, Z_SILL = 0.537, 0.292               # bumper top (front of the arch), side skirt top (behind it)
Z_LAMP_TOP = 0.679                            # front_new.UNIT_Z[3]
WHEEL = (-1.1715, 0.2916)


def x_in(y):
    """Wing's inner (top) edge: the far side of the bonnet's 5 mm shut-line gap (bonnet_fit side line)."""
    return 0.6275 + (y + 1.65) * (0.015 / 0.75) + 0.0025


def scan():
    o = bpy.data.objects["REF_BODY"]
    b = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    mi = np.empty(len(o.data.polygons), int); o.data.polygons.foreach_get("material_index", mi)
    names = [m.name for m in o.data.materials]
    paint = {names.index(n) for n in ("paint_gunmetal",) if n in names}
    Rs = []
    for side in (1, -1):
        R = np.full((len(YS), len(PH)), np.nan)
        for i, y in enumerate(YS):
            for j, p in enumerate(PH):
                d = Vector((side * math.cos(p), 0, math.sin(p)))
                org = Vector((side * CX, y, CZ)) + d * 1.0
                h = b.ray_cast(org, -d, 1.0)
                if h[0] is not None and mi[h[2]] in paint:
                    R[i, j] = 1.0 - h[3]
        Rs.append(R)
    R = np.where(np.isfinite(Rs[0]) & np.isfinite(Rs[1]), (Rs[0] + Rs[1]) / 2, np.nan)
    return R


ARCH_PIC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "export", "ref", "arch_front_pic.json")


def arch_pic():
    """The arch edge to build to: traced on Nik's grey side picture, centred on the wheel like the picture's
    (export/ref/arch_front_pic.json, front-low -> top -> rear-low)."""
    import json
    return np.array(json.load(open(ARCH_PIC))["outline"])


def arch_outline():
    """OLD model's arch opening edge in (y, z), from the horizontal paint scan (both sides) - only used to mask the
    old lip roll out of the surface scan."""
    o = bpy.data.objects["REF_BODY"]
    b = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    pts = []
    for z in np.arange(0.27, 0.70, 0.0025):
        row = []
        for y in np.arange(-1.52, -0.80, 0.0025):
            hs = []
            for side in (1, -1):
                h = b.ray_cast(Vector((side * 1.0, y, z)), Vector((-side, 0, 0)), 0.6)
                hs.append(h[0] is not None and abs(h[0].x) > 0.62)
            row.append(all(hs))
        row = np.array(row)
        ys = np.arange(-1.52, -0.80, 0.0025)
        holes = np.where(~row & (ys > -1.49) & (ys < -0.83))[0]
        if len(holes) > 4:
            pts.append((z, ys[holes.min()] - 0.00125, ys[holes.max()] + 0.00125))
    pts = np.array(pts)
    # polar around the wheel, smoothed: r(theta) fitted with a low-order Fourier series
    P = np.concatenate([np.c_[pts[:, 1], pts[:, 0]], np.c_[pts[:, 2], pts[:, 0]]])
    th = np.arctan2(P[:, 1] - WHEEL[1], P[:, 0] - WHEEL[0]); th = np.where(th < -np.pi / 2, th + 2 * np.pi, th)
    r = np.hypot(P[:, 0] - WHEEL[0], P[:, 1] - WHEEL[1])
    A = np.stack([np.ones_like(th)] + [f(k * th) for k in range(1, 7) for f in (np.cos, np.sin)], 1)
    c = np.linalg.lstsq(A, r, rcond=None)[0]
    t = np.linspace(th.min(), th.max(), 800)
    At = np.stack([np.ones_like(t)] + [f(k * t) for k in range(1, 7) for f in (np.cos, np.sin)], 1)
    rt = At @ c
    curve = np.c_[WHEEL[0] + rt * np.cos(t), WHEEL[1] + rt * np.sin(t)]     # rear-low -> top -> front-low
    res = float(np.sqrt(np.mean((A @ c - r) ** 2)))
    return curve[::-1], res                                                # front-low -> top -> rear-low


def gaussian_filter(A, sig, mode=None):
    """Separable Gaussian (edge values repeated) - Blender's Python has no scipy."""
    out = A.astype(float)
    for ax, sg in enumerate(sig):
        if sg <= 0:
            continue
        k = int(3 * sg + 1); t = np.arange(-k, k + 1); w = np.exp(-0.5 * (t / sg) ** 2); w /= w.sum()
        pad = [(0, 0)] * out.ndim; pad[ax] = (k, k)
        P = np.pad(out, pad, mode="edge")
        out = sum(w[i] * np.take(P, np.arange(i, i + out.shape[ax]), axis=ax) for i in range(len(w)))
    return out


def smooth(R):
    m = np.isfinite(R).astype(float)
    V = np.nan_to_num(R)
    s = (1.5, 1.0)
    num = gaussian_filter(V * m, s, mode="nearest"); den = gaussian_filter(m, s, mode="nearest")
    out = np.where(m > 0, num / np.maximum(den, 1e-9), np.nan)
    return out


# Flare ledge over the front arch, read off Nik's grey side picture (the light band above the arch, moved onto the
# model's wheel): its lower edge is a straight line, its height grows from ~1 cm at the lamp to ~4.5 cm just ahead of
# the wheel and runs out at y -0.836 - a lens, as over the rear arch. z_l = polyval(LEDGE_ZL, y), h = polyval(LEDGE_H, y)
LEDGE_ZL = [0.04789308729441894, 0.739798076858345]
LEDGE_H = [-7.0983296139536565, -43.5452360845599, -105.47228376153502, -126.29373753397266, -74.90601973804553,
           -17.606117015634307]
LEDGE_Y = (-1.565, -0.836)


def ledge_band(y):
    zl = float(np.polyval(LEDGE_ZL, y))
    h = float(np.polyval(LEDGE_H, y)) if LEDGE_Y[0] <= y <= LEDGE_Y[1] else 0.0
    return zl, max(0.0, h)


def band_edges(y):
    """Ledge band [z0, z1] at y: the picture's band where it has height; where it runs out the band widens to a soft
    45 mm blend so any old step there is faded out (continuous in y)."""
    zl, h = ledge_band(y)
    q = float(np.clip(1.0 - h / 0.012, 0.0, 1.0))
    return zl - 0.001 - 0.011 * q, zl + max(h, 0.045 * q)


def _poly_terms(y, w):
    yn = (np.asarray(y) - 1.15 * -1) / 0.45 if False else (np.asarray(y) + 1.15) / 0.45
    return np.stack([yn ** i * np.asarray(w) ** j for i in range(7) for j in range(3)], -1)


def _robust_fit(A, b):
    k = np.ones(len(b), bool)
    for _ in range(4):
        c = np.linalg.lstsq(A[k], b[k], rcond=None)[0]
        r = A @ c - b
        k = np.abs(r) < 2.5 * max(r[k].std(), 2e-4)
    return c


def reshape_ledge(F):
    """The flare ledge: smooth surfaces fitted just below (flare) and just above (upper panel) the picture's band,
    each continued into the band and blended there (smoothstep); seams faded over 20 mm."""
    F = F.copy()
    Yg = np.repeat(YS[:, None], len(PH), 1); Pg = np.repeat(PH[None, :], len(YS), 0)
    X = CX + F * np.cos(Pg); Z = CZ + F * np.sin(Pg)
    E = gaussian_filter(np.array([band_edges(y) for y in YS]), (8.0, 0.0))     # band edges smooth along the car
    Z0 = E[:, 0][:, None] + 0 * X; Z1 = E[:, 1][:, None] + 0 * X
    sel = np.isfinite(X) & (Yg > -1.575) & (Yg < -0.70) & (Pg > math.radians(5)) & (Pg < math.radians(45))
    lo = sel & (Z > Z0 - 0.05) & (Z < Z0 - 0.003)
    hi = sel & (Z > Z1 + 0.003) & (Z < Z1 + 0.03)
    cL = _robust_fit(_poly_terms(Yg[lo], Z[lo] - Z0[lo]), X[lo])
    cU = _robust_fit(_poly_terms(Yg[hi], Z[hi] - Z1[hi]), X[hi])
    def upper(y, zz, z1):
        """Upper panel: the fit inside its window, a straight continuation below it."""
        if zz >= z1:
            return float(_poly_terms(y, zz - z1) @ cU)
        u0 = float(_poly_terms(y, 0.0) @ cU); u1 = float(_poly_terms(y, 0.002) @ cU)
        return u0 + (u1 - u0) / 0.002 * (zz - z1)
    def ramp(t, e=0.18):
        """Straight ledge with tight rounded edges (as the rear arch's), 0..1."""
        t = min(1.0, max(0.0, t))
        if t < e:
            return t * t / (2 * e * (1 - e))
        if t > 1 - e:
            return 1 - (1 - t) ** 2 / (2 * e * (1 - e))
        return (t - e / 2) / (1 - e)
    for i, y in enumerate(YS):
        if y < -1.58 or y > -0.70:
            continue
        z0, z1 = E[i]
        # step depth: full over the arch, fading over the last 12 cm before the band's rear point and to ~40 % at
        # the lamp (picture band ~1 cm tall there)
        sr = float(np.clip((LEDGE_Y[1] - y) / 0.12, 0.0, 1.0)); sf = float(np.clip((y - LEDGE_Y[0]) / 0.15, 0.0, 1.0))
        tau = (sr * sr * (3 - 2 * sr)) * (0.4 + 0.6 * sf * sf * (3 - 2 * sf))
        for j in range(len(PH)):
            if not (sel[i, j] and z0 - 0.09 < Z[i, j] < z1 + 0.045):
                continue
            p = PH[j]; R = F[i, j]; R0 = R
            for _ in range(6):
                zz = CZ + R * math.sin(p)
                xo = CX + R0 * math.cos(p)                    # original surface (approx, same ray)
                xu = upper(y, zz, z1)
                xl = float(_poly_terms(y, zz - z0) @ cL)
                # where the band runs out both surfaces meet halfway (the door's profile), not one onto the other
                wv = 1.0 - min(1.0, max(0.0, (z0 - zz) / 0.08, (zz - z1) / 0.045))
                wv = wv * wv * (3 - 2 * wv)
                te = 1.0 - (1.0 - tau) * wv
                mid = 0.5 * (xl + xu)
                xl = mid + (xl - mid) * te; xu = mid + (xu - mid) * te
                xt = xl + (xu - xl) * ramp((zz - z0) / (z1 - z0))
                if zz < z0 - 0.06:                            # fade in from the scan well below the band
                    u = min(1.0, (z0 - 0.06 - zz) / 0.03); xt = xt * (1 - u) + xo * u
                elif zz > z1 + 0.02:
                    u = min(1.0, (zz - z1 - 0.02) / 0.025); xt = xt * (1 - u) + xo * u
                R = (xt - CX) / math.cos(p)
            F[i, j] = R
    return F


class Surf:
    def __init__(self, R):
        self.R = R
        # fill holes (side repeater, nan) by nearest along phi for interpolation only
        F = R.copy()
        # grow valid values into the masked edge bands (both directions), then the plain fills below
        for _ in range(12):
            P = np.pad(F, 1, constant_values=np.nan)
            nb = np.stack([P[:-2, 1:-1], P[2:, 1:-1], P[1:-1, :-2], P[1:-1, 2:]])
            cnt = np.isfinite(nb).sum(0)
            avg = np.where(cnt > 0, np.nansum(nb, 0) / np.maximum(cnt, 1), np.nan)
            grow = ~np.isfinite(F) & (cnt >= 2)
            # linear extrapolation where a straight pair exists, else the neighbour mean
            F = np.where(grow, avg, F)
        for i in range(F.shape[0]):
            ok = np.isfinite(F[i])
            if ok.sum() > 2:
                F[i] = np.interp(PH, PH[ok], F[i][ok])
        for j in range(F.shape[1]):
            ok = np.isfinite(F[:, j])
            if ok.sum() > 2:
                F[:, j] = np.interp(YS, YS[ok], F[:, j][ok])
        F = reshape_ledge(F)
        # light smoothing along the car so neighbouring columns' blends join up
        self.F = gaussian_filter(F, (1.0, 0.0))

    def r(self, y, p):
        fi = np.clip((y - YS[0]) / (YS[1] - YS[0]), 0, len(YS) - 1.001)
        fj = np.clip((p - PH[0]) / (PH[1] - PH[0]), 0, len(PH) - 1.001)
        i, j = int(fi), int(fj); a, b = fi - i, fj - j
        F = self.F
        return (F[i, j] * (1 - a) * (1 - b) + F[i + 1, j] * a * (1 - b) + F[i, j + 1] * (1 - a) * b
                + F[i + 1, j + 1] * a * b)

    def xz(self, y, p):
        r = self.r(y, p)
        return CX + r * math.cos(p), CZ + r * math.sin(p)

    def phi_at_z(self, y, z):
        lo, hi = PH[0], math.radians(40)
        for _ in range(40):
            m = (lo + hi) / 2
            if self.xz(y, m)[1] < z:
                lo = m
            else:
                hi = m
        return (lo + hi) / 2

    def phi_at_x(self, y, x):
        """Top edge: phi where the surface comes in to x (x falls with phi over the shoulder)."""
        lo, hi = math.radians(30), PH[-1]
        for _ in range(40):
            m = (lo + hi) / 2
            if self.xz(y, m)[0] > x:
                lo = m
            else:
                hi = m
        return (lo + hi) / 2


def y_front(S, y, p):
    import front_new as fn
    x, z = S.xz(y, p)
    if z <= Z_LAMP_TOP:
        return -1.578
    return min(-1.578, fn.y_lamp(min(x, fn.x_end(Z_LAMP_TOP)), Z_LAMP_TOP) - 0.002)


def z_low_fn(arch):
    """Lower edge z(y): bumper top in front of the arch, the arch outline, the sill behind it."""
    a = arch[(arch[:, 1] >= Z_SILL)]
    front = a[a[:, 0] < a[np.argmax(a[:, 1]), 0]]
    keep = np.ones(len(a), bool)
    # front-low part of the outline under the bumper top is not an edge of the wing
    keep &= ~((a[:, 0] < a[np.argmax(a[:, 1]), 0]) & (a[:, 1] < Z_BUMPER))
    a = a[keep]
    a = a[np.argsort(a[:, 0], kind="stable")]
    ya = a[:, 0]
    def f(y):
        if y < ya.min():
            return Z_BUMPER
        if y > ya.max():
            return Z_SILL
        return float(np.interp(y, ya, a[:, 1]))
    return f, a


def boundary_points(S, arch_pts):
    """Edge lines sampled densely in (y, phi), each tagged."""
    B = []
    # lower: bumper top line, arch, sill line
    a0 = arch_pts[0]; a1 = arch_pts[-1]
    for y in np.arange(-1.60, a0[0], 0.001):
        B.append((y, S.phi_at_z(y, Z_BUMPER), "low"))
    for (y0, z0), (y1, z1) in zip(arch_pts[:-1], arch_pts[1:]):
        n = max(1, int(math.hypot(y1 - y0, z1 - z0) / 0.001))
        for t in np.linspace(0, 1, n, endpoint=False):
            y, z = y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
            B.append((y, S.phi_at_z(y, z), "arch"))
    for y in np.arange(a1[0], YR + 0.0005, 0.001):
        B.append((y, S.phi_at_z(y, Z_SILL), "low"))
    # rear (door shut line), top (gutter), front (lamp)
    for p in np.arange(PH[0], PH[-1], math.radians(0.1)):
        B.append((YR, p, "rear"))
    for y in np.arange(-1.70, YR, 0.001):
        B.append((y, S.phi_at_x(y, x_in(y)), "top"))
    for p in np.arange(math.radians(-10), PH[-1], math.radians(0.1)):
        y = -1.578
        for _ in range(3):
            y = y_front(S, y, p)
        B.append((y, p, "front"))
    return B


def build(S, zlow):
    """Left wing grid -> trimmed, snapped. Returns bmesh and per-vertex edge tags."""
    import front_new as fn
    bm = bmesh.new()
    V = {}
    for i, y in enumerate(YS):
        for j, p in enumerate(PH):
            V[i, j] = (y, p)

    def inside(y, p):
        x, z = S.xz(y, p)
        return (y <= YR and y >= y_front(S, y, p) and x >= x_in(y) and z >= zlow(y))
    made = {}

    def vert(i, j):
        if (i, j) not in made:
            y, p = V[i, j]
            v = bm.verts.new((0, y, 0)); v[uv_y] = y; v[uv_p] = p
            made[i, j] = v
        return made[i, j]
    uv_y = bm.verts.layers.float.new("py"); uv_p = bm.verts.layers.float.new("pp")
    for i in range(len(YS) - 1):
        for j in range(len(PH) - 1):
            yc = (YS[i] + YS[i + 1]) / 2; pc = (PH[j] + PH[j + 1]) / 2
            if inside(yc, pc):
                bm.faces.new((vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)))
    return bm, uv_y, uv_p


def snap(bm, uv_y, uv_p, B, S):
    Bp = np.array([(y, p) for y, p, _ in B]); tags = [t for _, _, t in B]
    Rm = 0.33
    from mathutils.kdtree import KDTree
    kd = KDTree(len(Bp))
    for k, (y, p) in enumerate(Bp):
        kd.insert((y, p * Rm, 0.0), k)
    kd.balance()
    tag = bm.verts.layers.string.new("edge")
    kix = bm.verts.layers.int.new("k")
    bverts = {v for e in bm.edges if e.is_boundary for v in e.verts}
    for v in bverts:
        _, k, _ = kd.find((v[uv_y], v[uv_p] * Rm, 0.0))
        v[kix] = k
        v[tag] = tags[k].encode()
    # walk the boundary loop(s); in each run of one edge type spread the vertices evenly along that edge line
    # (curve index from the first to the last vertex of the run) - no inversions or bunching
    seen = set()
    for v0 in bverts:
        if v0 in seen:
            continue
        loop = [v0]; seen.add(v0); prev = None; cur = v0
        while True:
            nxt = [e.other_vert(cur) for e in cur.link_edges if e.is_boundary and e.other_vert(cur) is not prev]
            nxt = [w for w in nxt if w not in seen] or [w for w in nxt if w is v0]
            if not nxt or nxt[0] is v0:
                break
            prev, cur = cur, nxt[0]; loop.append(cur); seen.add(cur)
        n = len(loop)
        # start the walk at a change of edge type
        st = next((i for i in range(n) if loop[i][tag] != loop[i - 1][tag]), 0)
        loop = loop[st:] + loop[:st]
        runs, cur_run = [], [loop[0]]
        for w in loop[1:]:
            if w[tag] == cur_run[-1][tag]:
                cur_run.append(w)
            else:
                runs.append(cur_run); cur_run = [w]
        runs.append(cur_run)
        for run in runs:
            if len(run) < 3:
                continue
            k0, k1 = run[0][kix], run[-1][kix]
            for i, w in enumerate(run):
                k = int(round(k0 + (k1 - k0) * i / (len(run) - 1)))
                w[uv_y], w[uv_p] = Bp[k]
        for w in loop:
            pass
    for v in bverts:
        if v[kix] >= 0:
            pass
    # relax the first rings inside the edge (param space), edge vertices fixed
    ring = set(bverts)
    near = set()
    for _ in range(4):
        nxt = {e.other_vert(v) for v in (ring | near) for e in v.link_edges} - bverts
        near |= nxt
    for _ in range(15):
        new = {}
        for v in near:
            nb = [e.other_vert(v) for e in v.link_edges]
            new[v] = (sum(w[uv_y] for w in nb) / len(nb), sum(w[uv_p] for w in nb) / len(nb))
        for v, (yy, pp) in new.items():
            v[uv_y] = 0.5 * v[uv_y] + 0.5 * yy; v[uv_p] = 0.5 * v[uv_p] + 0.5 * pp
    for v in bm.verts:
        x, z = S.xz(v[uv_y], v[uv_p])
        v.co = (x, v[uv_y], z)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0012)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0005)
    return tag


LAST_GROUPS = {}
BACKS = {"arch": ((-1, 0, 0), 0.025, 0.004), "low": ((-1, 0, 0), 0.02, 0.003), "rear": ((-1, 0, 0), 0.02, 0.002),
         "top": ((0, 0, -1), 0.02, 0.003), "front": ((-1, 0, 0), 0.02, 0.002)}


def rims(bm, tag):
    import front_new as fn
    for f in bm.faces:
        f.normal_update()
    edges = [e for e in bm.edges if e.is_boundary]
    groups = {}
    global LAST_GROUPS
    for e in edges:
        a, b = e.verts
        ta, tb = a[tag].decode(), b[tag].decode()
        t = ta if ta == tb else (ta if ta in ("front", "top") else tb)
        if t == "front" and (a.co.z > Z_LAMP_TOP + 0.001 or b.co.z > Z_LAMP_TOP + 0.001):
            t = "cap"
        groups.setdefault(t, []).append(e)
    LAST_GROUPS = {t: len(es) for t, es in groups.items()}
    faces = set(bm.faces)
    for t, es in groups.items():
        if t == "cap":
            # wall straight down from the wing's front edge to the lamp top
            low = {}
            for e in es:
                for v in e.verts:
                    if v not in low:
                        low[v] = bm.verts.new((v.co.x, v.co.y, min(v.co.z, Z_LAMP_TOP)))
            for e in es:
                a, b = e.verts
                if (a.co - low[a].co).length < 1e-5 and (b.co - low[b].co).length < 1e-5:
                    continue
                q = [a, b, low[b], low[a]]
                q2 = [q[0]] + [w for k, w in enumerate(q[1:]) if (w.co - q[k].co).length > 1e-6 and w is not q[0]]
                try:
                    f = bm.faces.new(list(dict.fromkeys(q2)))
                    f.smooth = False
                except ValueError:
                    pass
            continue
        back, depth, r = BACKS.get(t, ((-1, 0, 0), 0.02, 0.002))
        dfn = None
        if t == "arch":                          # lip rolls towards the wheel axis (the edge is a smooth curve round it)
            dfn = lambda v: Vector((0, WHEEL[0] - v.co.y, WHEEL[1] - v.co.z)).normalized()
        fn.rim(bm, depth, r, back=Vector(back), steps=3, faces=faces, edges=es, dfn=dfn)


NOSE_R = 0.045                               # wing nose curls down over this length (bonnet nose: 0.78 x drop)


def nose_round(bm):
    """The wing's front end above the lamp curls down onto the lamp top like the bonnet's nose (quarter ellipse):
    within NOSE_R of the front edge the height above the lamp top is scaled down to zero at the edge."""
    import front_new as fn
    for v in bm.verts:
        if v.co.z <= Z_LAMP_TOP:
            continue
        x = abs(v.co.x)
        ye = min(-1.578, fn.y_lamp(min(x, fn.x_end(Z_LAMP_TOP)), Z_LAMP_TOP) - 0.002)
        d = v.co.y - ye
        if d >= NOSE_R:
            continue
        f = math.sqrt(max(0.0, 1.0 - (1.0 - max(d, 0.0) / NOSE_R) ** 2))
        v.co.z = Z_LAMP_TOP + (v.co.z - Z_LAMP_TOP) * max(f, 0.04)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0004)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0003)


def mirror(bm):
    out = bm.copy()
    for v in out.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(out, faces=out.faces[:])
    return out


def orient(bm):
    for f in bm.faces:
        f.normal_update()
    side = [f for f in bm.faces if abs(f.normal.x) > 0.5]
    if side and sum(np.sign(f.calc_center_median().x) * f.normal.x for f in side) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])


def inside_poly(P, poly):
    """Even-odd point-in-polygon for many points (numpy)."""
    x, y = P[:, 0], P[:, 1]
    ins = np.zeros(len(P), bool)
    for (x0, y0), (x1, y1) in zip(poly[:-1], poly[1:]):
        c = ((y0 > y) != (y1 > y))
        xi = x0 + (y - y0) * (x1 - x0) / np.where(y1 != y0, y1 - y0, 1e-12)
        ins ^= c & (x < xi)
    return ins


def remove_old(S, zlow, arch_pts):
    import prep_reference as pr
    planes = []
    k = 0.015 / 0.75                              # x_in slope along y
    for s in (1, -1):
        X = (0.55, 0.82) if s > 0 else (-0.82, -0.55)
        XT = (0.60, 0.70) if s > 0 else (-0.70, -0.60)
        planes += [((0, YR, 0), (0, 1, 0), (X[0], X[1], YR - 0.01, YR + 0.01, Z_SILL - 0.01, 0.92)),
                   ((0, 0, Z_BUMPER), (0, 0, 1), (X[0], X[1], -1.60, -1.42, Z_BUMPER - 0.01, Z_BUMPER + 0.01)),
                   ((0, 0, Z_SILL), (0, 0, 1), (X[0], X[1], -0.86, YR, Z_SILL - 0.01, Z_SILL + 0.01)),
                   ((s * x_in(-1.2), -1.2, 0), (s * 1.0, -k, 0), (XT[0], XT[1], -1.70, YR, 0.65, 0.93))]
        ap = arch_pic(); ap = ap[ap[:, 1] > 0.22]          # whole arch edge (also the bumper / spoiler ends)
        for (y0, z0), (y1, z1) in zip(ap[:-1:6], ap[6::6]):
            t = np.array([y1 - y0, z1 - z0]); n = np.array([-t[1], t[0]]); n /= np.linalg.norm(n) + 1e-12
            planes.append(((0, y0, z0), (0, n[0], n[1]),
                           (X[0], X[1], min(y0, y1) - 0.004, max(y0, y1) + 0.004, min(z0, z1) - 0.004,
                            max(z0, z1) + 0.004)))
    fixed = planes
    pr.bisect_planes(fixed, grow=0.005)
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    x, y, z = C.T
    ax = np.abs(x)
    cand = np.where((ax > 0.55) & (y > -1.70) & (y < YR + 0.0005) & (z > Z_SILL - 0.005) & (z < 0.93))[0]
    dead = []
    for i in cand:
        p = math.atan2(z[i] - CZ, ax[i] - CX); r = math.hypot(ax[i] - CX, z[i] - CZ)
        if p < PH[0] or p > PH[-1]:
            continue
        rs = S.r(y[i], p)
        if abs(r - rs) > 0.03:
            continue
        xx, zz = S.xz(y[i], p)
        if y[i] <= YR and y[i] >= y_front(S, y[i], p) - 0.001 and xx >= x_in(y[i]) - 0.001 and zz >= zlow(y[i]) - 0.001:
            dead.append(i)
    # old lip / flare pieces left inside the (moved) arch opening: everything out at the skin (|x| > 0.64) whose
    # (y, z) lies inside the new arch outline
    ap = arch_pic()
    poly = np.r_[ap, ap[:1]]
    sel = np.where((ax > 0.64) & (y > -1.56) & (y < -0.78) & (z > 0.22) & (z < 0.66))[0]
    ins = inside_poly(np.c_[y[sel], z[sel]], poly)
    dead = set(dead) | set(int(i) for i in sel[ins])
    # leftovers of the old bumper top / wing bottom at the front corners (new bumper band + ledge cover this zone)
    dead |= set(int(i) for i in np.where((ax > 0.62) & (y > -1.76) & (y < -1.40) & (z > 0.45) & (z < 0.545))[0])
    dead = sorted(dead)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in dead], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    return len(dead)


def mask_edges(R, arch):
    """Drop scan samples on the old arch lip (rolls in over the last ~15 mm), the gutter roll at the top edge and
    everything ahead of y -1.555 (old lamp / bonnet corner pieces - the wing's section is carried straight forward):
    the new panel runs straight out to its edge, which then gets its own clean roll (rims)."""
    from mathutils.kdtree import KDTree
    kd = KDTree(len(arch))
    for k, (y, z) in enumerate(arch):
        kd.insert((y, z, 0), k)
    kd.balance()
    R = R.copy()
    for i, y in enumerate(YS):
        for j, p in enumerate(PH):
            r = R[i, j]
            if not np.isfinite(r):
                continue
            x, z = CX + r * math.cos(p), CZ + r * math.sin(p)
            if kd.find((y, z, 0))[2] < 0.016 or (p > math.radians(35) and x < x_in(y) + 0.006) or y < -1.555:
                R[i, j] = np.nan
    return R


def main():
    import front_new as fn
    cache = bpy.app.driver_namespace.get("wing_scan") if bpy.app.driver_namespace.get("wing_scan_file") == bpy.data.filepath else None
    if cache is None:
        arch, arch_rms = arch_outline(); raw = scan()
        if not bpy.app.background:
            bpy.app.driver_namespace["wing_scan"] = (arch, arch_rms, raw)
            bpy.app.driver_namespace["wing_scan_file"] = bpy.data.filepath
    else:
        arch, arch_rms, raw = cache
    R = smooth(mask_edges(mask_edges(raw, arch), arch_pic()))
    S = Surf(R)
    arch = arch_pic()
    zlow, arch_pts = z_low_fn(arch)
    B = boundary_points(S, arch_pts)
    bm, uy, up = build(S, zlow)
    tag = snap(bm, uy, up, B, S)
    orient(bm)
    rims(bm, tag)
    for f in bm.faces:
        f.smooth = True
    nose_round(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])     # rim faces wound like the panel
    orient(bm)
    right = mirror(bm)
    out = {"arch_fit_rms_mm": round(arch_rms * 1000, 1), "edges": LAST_GROUPS}
    for nm, b in (("DET_WING_L", bm), ("DET_WING_R", right)):
        ob = fn.to_object(nm, b, ["paint_gunmetal"])
        out[nm] = len(ob.data.polygons)
    out["old_removed"] = remove_old(S, zlow, arch_pts)
    return out


if __name__ == "__main__":
    print("==", main())
