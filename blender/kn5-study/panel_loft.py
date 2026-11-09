"""Curves -> exact surface for a side panel: section curves + a lofted quad surface through them.

No smoothing anywhere: every section curve lies exactly on the surface, and between sections the
surface is a Catmull-Rom spline through the matching points of the sections (C1, passes through all).

Sections (method test: cut from the true panel; later traced from pictures/blueprints):
  - cut the panel mesh with planes across it (constant lengthwise position)
  - keep the outer skin: outermost point per height bin
  - trim at the top and bottom where the section turns in (> TURN deg from the panel's general direction)
  - split at feature points (creases: sharpest bends) so every crease becomes an edge loop
  - resample each part to a fixed point count (same for every section)

Frame: Blender (x = out, y = along the car, z = up), from the panel npz exported from Blender.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from section import cut


def tris(F):
    T = []
    for f in F:
        f = f[f >= 0]
        for i in range(1, len(f) - 1): T.append([f[0], f[i], f[i + 1]])
    return np.array(T)


def section_curve(V, T, y, zlo, zhi, binw=0.003, turn=55):
    s = cut(V, T, 1, y)
    if not len(s): return None
    P = s.reshape(-1, 3)
    P = P[(P[:, 2] > zlo) & (P[:, 2] < zhi)]
    if len(P) < 10: return None
    zb = np.floor(P[:, 2] / binw).astype(int)
    order = np.lexsort((-P[:, 0], zb)); P = P[order]; zb = zb[order]
    first = np.r_[True, zb[1:] != zb[:-1]]
    C = P[first]                                    # outermost point per height bin, ordered bottom -> top
    # trim where the curve turns inwards (returns at the bottom, belt turn-in at the top)
    t = np.diff(C[:, [0, 2]], axis=0); ang = np.degrees(np.arctan2(np.abs(t[:, 0]), np.abs(t[:, 1]) + 1e-9))
    ok = ang < turn
    # longest run of ok segments
    best, cur, bs = (0, 0), 0, 0
    for i, o in enumerate(ok):
        if o:
            if cur == 0: bs = i
            cur += 1
            if cur > best[1] - best[0]: best = (bs, i + 1)
        else: cur = 0
    C = C[best[0]:best[1] + 1]
    return C if len(C) > 10 else None


def resample(P, n):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n)
    return np.c_[[np.interp(t, d, P[:, k]) for k in range(3)]].T


CLEAN = int(os.environ.get('CLEAN_DEG', 3))


def clean_part(seg, n):
    """a section part as a CLEAN curve: depth x as a cubic of height z through the part, with its end points
    held (weighted) so neighbouring parts meet exactly at the crease; sampled evenly in z"""
    z, x = seg[:, 2], seg[:, 0]
    if CLEAN <= 0 or len(seg) < 6: return resample(seg, n)
    w = np.ones(len(z)); w[0] = w[-1] = 50.0
    c = np.polyfit(z, x, min(CLEAN, len(z) - 1), w=w)
    zz = np.linspace(z[0], z[-1], n)
    return np.c_[np.polyval(c, zz), np.full(n, seg[:, 1].mean()), zz]


def split_resample(C, splits_z, counts):
    """split the curve at the given heights (crease heights) and give each part as a clean curve"""
    z = C[:, 2]
    def at(zz):
        i = int(np.clip(np.searchsorted(z, zz), 1, len(z) - 1))
        w = (zz - z[i - 1]) / max(z[i] - z[i - 1], 1e-9); return C[i - 1] + w * (C[i] - C[i - 1])
    edges = [z[0]] + list(splits_z) + [z[-1]]
    out = []
    for i in range(len(edges) - 1):
        m = (z > edges[i]) & (z < edges[i + 1])
        seg = np.r_[[at(edges[i])], C[m], [at(edges[i + 1])]]
        if len(seg) < 3: return None
        r = clean_part(seg, counts[i])
        out.append(r if i == 0 else r[1:])
    return np.concatenate(out)


def crease_height(C, zlo, zhi):
    """height of the sharpest bend of a section within [zlo, zhi]"""
    m = (C[:, 2] > zlo) & (C[:, 2] < zhi)
    idx = np.where(m)[0]
    if len(idx) < 5: return None
    best, bz = 0, None
    for i in idx:
        if i < 3 or i > len(C) - 4: continue
        a, b = C[i] - C[i - 3], C[i + 3] - C[i]
        ang = np.degrees(np.arccos(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12), -1, 1)))
        if ang > best: best, bz = ang, C[i, 2]
    return bz


def catmull_rom_loft(S, k):
    """S: [ns, m, 3] sections; insert k rows between sections with centripetal-free uniform Catmull-Rom"""
    ns = len(S); rows = []
    for i in range(ns - 1):
        p0 = S[max(i - 1, 0)]; p1 = S[i]; p2 = S[i + 1]; p3 = S[min(i + 2, ns - 1)]
        if i == 0: p0 = 2 * p1 - p2
        if i == ns - 2: p3 = 2 * p2 - p1
        for j in range(k):
            t = j / k
            rows.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    rows.append(S[-1])
    return np.array(rows)


def nearest(A, Bp, slab=0.02, chunk=400):
    """nearest distance A -> Bp, searching only Bp points within +-slab along the car (y); exact up to slab"""
    o = np.argsort(Bp[:, 1]); Bs = Bp[o]; by = Bs[:, 1]
    oa = np.argsort(A[:, 1]); As = A[oa]
    out = np.empty(len(A))
    for s in range(0, len(As), chunk):
        q = As[s:s + chunk]
        lo, hi = np.searchsorted(by, q[:, 1].min() - slab), np.searchsorted(by, q[:, 1].max() + slab)
        C = Bs[lo:hi]
        if not len(C): out[s:s + chunk] = slab; continue
        d = np.full(len(q), np.inf)
        for c in range(0, len(C), 4000):
            d = np.minimum(d, ((q[:, None, :] - C[None, c:c + 4000, :]) ** 2).sum(-1).min(1))
        out[s:s + chunk] = np.minimum(np.sqrt(d), slab)
    res = np.empty(len(A)); res[oa] = out
    return res


def sample_tris(V, T, step=0.004):
    P = V[T]; L = np.maximum(np.linalg.norm(P[:, 1] - P[:, 0], axis=1), np.linalg.norm(P[:, 2] - P[:, 0], axis=1))
    out = []
    for n in np.unique(np.clip(np.ceil(L / step).astype(int), 1, 30)):
        sel = np.clip(np.ceil(L / step).astype(int), 1, 30) == n
        for i in range(n + 1):
            for j in range(n + 1 - i):
                u, v = i / n, j / n
                out.append(P[sel, 0] + u * (P[sel, 1] - P[sel, 0]) + v * (P[sel, 2] - P[sel, 0]))
    return np.concatenate(out)


def robust_fit(x, y, deg=2, tol=0.008, it=4):
    """clean curve through noisy edge points: polynomial fit, dropping points further than tol, repeated"""
    x, y = np.asarray(x, float), np.asarray(y, float); keep = np.isfinite(y)
    for _ in range(it):
        c = np.polyfit(x[keep], y[keep], min(deg, keep.sum() - 1))
        r = np.abs(np.polyval(c, x) - y); new = keep & (r < max(tol, np.percentile(r[keep], 60)))
        if new.sum() < deg + 2 or (new == keep).all(): break
        keep = new
    return c


def clip_curve(C, za, zb):
    """the part of a bottom->top section between heights za and zb, with exact end points"""
    z = C[:, 2]
    def at(zz):
        i = np.searchsorted(z, zz); i = np.clip(i, 1, len(z) - 1)
        w = (zz - z[i - 1]) / max(z[i] - z[i - 1], 1e-9); return C[i - 1] + w * (C[i] - C[i - 1])
    mid = C[(z > za) & (z < zb)]
    return np.r_[[at(za)], mid, [at(zb)]]


def build_side_panel(npz, n_sections, zlo, zhi, crease_band, counts=(20, 24), k=6, ymargin=0.012):
    d = np.load(npz); V, F, N = d['V'], d['F'], d['N']
    T = tris(F)
    # panel extent along the car from the outward-facing skin
    skin = (N[:, 0] > 0.6) & (V[:, 2] > zlo) & (V[:, 2] < zhi)
    y0, y1 = V[skin, 1].min() + ymargin, V[skin, 1].max() - ymargin
    ys = np.linspace(y0, y1, n_sections)
    secs, used = [], []
    raw = [section_curve(V, T, y, zlo, zhi) for y in ys]
    ok = [c is not None for c in raw]
    yk = ys[ok]; rk = [c for c in raw if c is not None]
    # clean edge lines (bottom edge, top edge) and crease line, each a robust quadratic along the car
    cb = robust_fit(yk, [c[0, 2] for c in rk], deg=int(os.environ.get('EDGE_DEG', 1))); ct = robust_fit(yk, [c[-1, 2] for c in rk], deg=int(os.environ.get('EDGE_DEG', 1)))
    crz = [crease_height(c, *crease_band) for c in rk]
    cc = robust_fit(yk, [np.nan if v is None else v for v in crz], deg=1) if sum(v is not None for v in crz) >= 3 else None
    cz = None if cc is None else float(np.polyval(cc, yk).mean())
    for y, C in zip(yk, rk):
        za, zb = np.polyval(cb, y) + 0.002, np.polyval(ct, y) - 0.002
        if za < C[0, 2] - 0.03 or zb > C[-1, 2] + 0.03: continue        # section does not span the panel
        Cc = clip_curve(C, max(za, C[0, 2]), min(zb, C[-1, 2]))
        sp = [float(np.polyval(cc, y))] if cc is not None else []
        R = split_resample(Cc, sp, counts if sp else (sum(counts),))
        if R is None: continue
        secs.append(R); used.append(y)
    # common top/bottom: every section must share the same parameter structure -> already same counts
    S = np.array(secs)
    G = catmull_rom_loft(S, k)          # [rows, m, 3]
    # scores both ways against the true skin between the first and last section
    Tsk = T[(N[T][:, :, 0].mean(1) > 0.5)]
    TP = sample_tris(V, Tsk)
    TP = TP[(TP[:, 1] >= used[0]) & (TP[:, 1] <= used[-1]) & (TP[:, 2] >= G[..., 2].min()) & (TP[:, 2] <= G[..., 2].max())]
    fine = catmull_rom_loft(np.array([resample(s, 200) for s in S]), k * 4).reshape(-1, 3)
    a = nearest(TP, fine) * 1000; b = nearest(fine, TP) * 1000
    rep = dict(sections=len(S), points_per_section=int(S.shape[1]), crease_height=None if cz is None else round(float(cz), 3),
               truth_to_build=dict(median=round(float(np.median(a)), 2), p90=round(float(np.percentile(a, 90)), 2), within_1mm=round(float(np.mean(a <= 1) * 100), 1), within_3mm=round(float(np.mean(a <= 3) * 100), 1)),
               build_to_truth=dict(median=round(float(np.median(b)), 2), p90=round(float(np.percentile(b, 90)), 2), within_3mm=round(float(np.mean(b <= 3) * 100), 1)))
    return G, S, rep


if __name__ == '__main__':
    npz = sys.argv[1]; out = sys.argv[2]
    for ns in (5, 8, 12):
        G, S, rep = build_side_panel(npz, ns, 0.27, 0.84, (0.43, 0.56))
        print(ns, json.dumps(rep))
        np.savez(out.replace('.npz', f'_{ns}.npz'), G=G, S=S)
