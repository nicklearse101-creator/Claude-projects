"""Step 3: rebuild a body with OUR OWN mesh from outlines + character lines, then score it.

    python step3_rebuild.py CAR_DIR OUT_DIR [--method m_prior] [--lines all|none|creases|sections]

1. Start surface: the blind-test outline build (method, default m_prior) turned into our own structured
   quad mesh: one ring per station (every 20 mm), each ring = 160 rays from the section centre to the
   build's outline (a sectional loft, the classic section-based modelling method).
2. Lines (method test: taken from the true model; later they will be traced from pictures):
   - character lines: vertices on true edges bending > 12 deg, outer surface only (not the inner
     edge of the 5 mm panel returns)
   - window outlines (glass boundaries)
   - sections every 400 mm
3. Fit: ring vertices near a line point are pinned to it; every other vertex is solved as the smoothest
   surface (thin-plate) through the pins, with a weak pull back to the outline build (the pictures).
4. Score: each of our vertices against the true outer surface (distance along the true normal), outer
   skin only (no underbody, no arch wells). Writes OUT/<car>_step3_<lines>.npz (mesh) + report.
"""
import sys, os, json, glob, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_test as B
from kn5full import KN5
from section import cut

NRAY = 160
STEP = 2            # use every 2nd 10 mm station -> 20 mm rings


def loft(ctx, fn):
    zs, RES, X0 = ctx['zs'], ctx['RES'], ctx['X0']
    za, zb = B.bbox(ctx['side'], 1)
    ny = ctx['front'].shape[1]; y0 = ctx['ylim'][0]
    rings, zr = [], []
    th = np.linspace(0, 2 * np.pi, NRAY, endpoint=False)
    for i in range(za, zb, STEP):
        s = fn(zs[i])
        if s.sum() < 50: continue
        xs, ys = np.nonzero(s)
        cx, cy = 0.0, (ys.min() + ys.max()) / 2 * RES + y0
        R = np.zeros(NRAY)
        for k, t in enumerate(th):
            d = np.arange(0, 1.2, RES / 2)
            px = np.round((cx + d * np.cos(t) - X0) / RES).astype(int); py = np.round((cy + d * np.sin(t) - y0) / RES).astype(int)
            ok = (px >= 0) & (px < s.shape[0]) & (py >= 0) & (py < s.shape[1])
            inside = np.zeros(len(d), bool); inside[ok] = s[px[ok], py[ok]]
            R[k] = d[np.where(inside)[0].max()] if inside.any() else 0.0
        rings.append(np.c_[cx + R * np.cos(th), cy + R * np.sin(th), np.full(NRAY, zs[i])]); zr.append((zs[i], cx, cy, i))
    P = np.concatenate(rings); nr = len(rings)
    idx = lambda r, k: r * NRAY + (k % NRAY)
    F = [[idx(r, k), idx(r, k + 1), idx(r + 1, k + 1), idx(r + 1, k)] for r in range(nr - 1) for k in range(NRAY)]
    F = np.array(F)
    E = np.unique(np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 3]], F[:, [3, 0]]]), axis=1), axis=0)
    loft.meta = zr
    return P, F, E, nr


def ray_hits(mask, cx, cy, ctx):
    """outermost solid point of a section mask along each of the NRAY rays from (cx, cy)"""
    RES, X0, y0 = ctx['RES'], ctx['X0'], ctx['ylim'][0]
    th = np.linspace(0, 2 * np.pi, NRAY, endpoint=False); out = np.full((NRAY, 2), np.nan)
    d = np.arange(0, 1.2, RES / 2)
    for k, t in enumerate(th):
        px = np.round((cx + d * np.cos(t) - X0) / RES).astype(int); py = np.round((cy + d * np.sin(t) - y0) / RES).astype(int)
        ok = (px >= 0) & (px < mask.shape[0]) & (py >= 0) & (py < mask.shape[1])
        inside = np.zeros(len(d), bool); inside[ok] = mask[px[ok], py[ok]]
        if inside.any():
            r = d[np.where(inside)[0].max()]; out[k] = (cx + r * np.cos(t), cy + r * np.sin(t))
    return out


def ring_pins(ctx, meta, L, section_every):
    """pins on our own rings: whole rings at section stations, ray-matched points for character lines"""
    pins = {}
    zr = np.array([m[0] for m in meta])
    # sections: every section_every metres, the ring takes the true outline along its own rays
    if section_every:
        last = -9
        for r, (z, cx, cy, i) in enumerate(meta):
            if z - last >= section_every - 1e-6 or r == 0:
                last = z
                hits = ray_hits(ctx['stack'][i], cx, cy, ctx)
                for k in range(NRAY):
                    if np.isfinite(hits[k, 0]): pins[r * NRAY + k] = [np.array([hits[k, 0], hits[k, 1], z])]
    # character lines: each point pins the ray it lies on, on its nearest ring
    for p in L:
        r = int(np.argmin(np.abs(zr - p[2])))
        if abs(zr[r] - p[2]) > 0.012: continue
        z, cx, cy, i = meta[r]
        k = int(round((np.arctan2(p[1] - cy, p[0] - cx) % (2 * np.pi)) / (2 * np.pi) * NRAY)) % NRAY
        pins.setdefault(r * NRAY + k, []).append(np.array([p[0], p[1], z]))
    return {i: np.mean(v, 0) for i, v in pins.items()}


def truth_lines(k, g, half_w):
    """line points from the true model: creases > 12 deg on the outer skin, glass outlines, 400 mm sections"""
    pts, sec = [], []
    paint = [m for m in k.meshes if m.mat and (('damage_dirt' in m.mat.shader) or 'bumper' in m.name.lower()
             or m.mat.shader in ('ksWindscreen',) or 'glass' in m.mat.name.lower())
             and not any(t in k.path_of(m.node) for t in ('COCKPIT_', 'WHEEL_')) and 'dmg' not in m.name.lower()
             and m.mat.shader != 'ksBrokenGlass' and 'light' not in m.mat.name.lower() and 'int' not in m.mat.name.lower()]
    for m in paint:
        P = m.pos; q = np.round(P / 1e-5).astype(np.int64)
        _, inv = np.unique(q, axis=0, return_inverse=True); T = inv.ravel()[m.idx]
        V = np.zeros((T.max() + 1, 3)); V[T.ravel()] = P[m.idx.ravel()]
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        n = np.cross(b - a, c - a); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), axis=1)
        f = np.repeat(np.arange(len(T)), 3)
        order = np.lexsort((e[:, 1], e[:, 0])); e, f = e[order], f[order]
        same = np.all(e[1:] == e[:-1], axis=1)
        pair_a, pair_b = f[:-1][same], f[1:][same]; pe = e[:-1][same]
        ang = np.degrees(np.arccos(np.clip((n[pair_a] * n[pair_b]).sum(1), -1, 1)))
        cnt = np.bincount(np.concatenate([e[:, 0], e[:, 1]]), minlength=len(V))
        # boundary vertices: on an edge used by one face only
        uniq, uc = np.unique(e, axis=0, return_counts=True)
        bnd = np.zeros(len(V), bool); bnd[uniq[uc == 1].ravel()] = True
        crease = np.zeros(len(V), bool); crease[pe[ang > float(os.environ.get("CREASE_DEG", 12))].ravel()] = True
        is_glass = m.mat.shader == 'ksWindscreen' or 'glass' in m.mat.name.lower()
        sel = bnd if is_glass else (crease & ~bnd)
        pts.append(V[sel])
        for zc in np.arange(-2.4, 2.4, 0.4):
            s = cut(V, T, 2, zc)
            if len(s): sec.append(s.reshape(-1, 3))
    L = np.concatenate(pts); S = np.concatenate(sec) if sec else np.zeros((0, 3))
    keep = lambda X: X[~((np.abs(X[:, 0]) > half_w + 0.012) & (X[:, 1] - g > 0.6))]   # no mirrors
    return keep(L), keep(S)


def thin(X, cell=0.008):
    if not len(X): return X
    k = np.floor(X / cell).astype(np.int64); _, i = np.unique(k, axis=0, return_index=True); return X[i]


def nearest(A, Bp, chunk=4000):
    """index of nearest B point for each A point (brute force in chunks)"""
    out = np.empty(len(A), int); dist = np.empty(len(A))
    for s in range(0, len(A), chunk):
        d = ((A[s:s + chunk, None, :] - Bp[None, :, :]) ** 2).sum(-1)
        j = d.argmin(1); out[s:s + chunk] = j; dist[s:s + chunk] = np.sqrt(d[np.arange(len(j)), j])
    return out, dist


def fit(P0, E, pins, w_data=float(os.environ.get("W_DATA", 0.002)), iters=6000):
    """min |L x|^2 + sum w_i |x_i - target_i|^2: pinned vertices get a strong (soft) pull to their line point
    (W_PIN; 0 = hard pins), all others a weak pull back to the outline build"""
    nv = len(P0); deg = np.bincount(E.ravel(), minlength=nv).astype(float)
    def lap(x):
        s = np.zeros_like(x); np.add.at(s, E[:, 0], x[E[:, 1]]); np.add.at(s, E[:, 1], x[E[:, 0]]); return x - s / deg[:, None]
    def lapT(y):
        w = y / deg[:, None]; s = np.zeros_like(y); np.add.at(s, E[:, 0], w[E[:, 1]]); np.add.at(s, E[:, 1], w[E[:, 0]]); return y - s
    w_pin = float(os.environ.get('W_PIN', 0.0))
    tgt = P0.copy(); w = np.full(nv, w_data); fixed = np.zeros(nv, bool)
    for i, p in pins.items():
        tgt[i] = p
        if w_pin > 0: w[i] = w_pin
        else: fixed[i] = True
    X = np.where(fixed[:, None], tgt, P0)
    A = lambda u: lapT(lap(u)) + w[:, None] * u * (~fixed)[:, None]
    b = -lapT(lap(np.where(fixed[:, None], tgt, 0))) + w[:, None] * tgt * (~fixed)[:, None]
    b[fixed] = 0
    x = np.where(fixed[:, None], 0, P0)
    r = b - A(x); r[fixed] = 0; p = r.copy(); rs = (r * r).sum()
    for k in range(iters):
        Ap = A(p); Ap[fixed] = 0; a = rs / max((p * Ap).sum(), 1e-30)
        x = x + a * p; r = r - a * Ap; rn = (r * r).sum()
        if rn < 1e-14: break
        p = r + (rn / rs) * p; rs = rn
    fixed_or_pinned = np.zeros(nv, bool); fixed_or_pinned[list(pins.keys())] = True
    return np.where(fixed[:, None], tgt, x), fixed_or_pinned


def truth_skin(k, g, half_w):
    P, I = B.exterior(k, g, half_w)
    # vertex normals of the exterior meshes
    a, b, c = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    n = np.cross(b - a, c - a); N = np.zeros_like(P)
    for j in range(3): np.add.at(N, I[:, j], n)
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    used = np.unique(I.ravel())
    return P[used], N[used]


def score(X, ctx, TP, TN, mask_extra=None):
    g = ctx['ground']; tin = ctx['meas']['track_f'] / 2000 - 0.13
    keep = X[:, 1] - g > 0.12
    for zc, yc, r in ctx['arches']:
        keep &= ((X[:, 2] - zc) ** 2 + (X[:, 1] - yc) ** 2 > (r + 0.01) ** 2)
    zlo, zhi = X[:, 2].min(), X[:, 2].max()
    keep &= ~((X[:, 1] - g < 0.35) & (np.abs(X[:, 0]) < tin) & (X[:, 2] > zlo + 0.25) & (X[:, 2] < zhi - 0.25))
    # only the outer skin: our vertex's nearest truth point must face outwards towards us
    j, dist = nearest(X[keep], TP)
    d = ((X[keep] - TP[j]) * TN[j]).sum(1) * 1000
    e = np.abs(d)
    return dict(n=int(keep.sum()), median_mm=round(float(np.median(e)), 1), p90_mm=round(float(np.percentile(e, 90)), 1),
                within_3mm_pct=round(float(np.mean(e <= 3) * 100), 1), within_10mm_pct=round(float(np.mean(e <= 10) * 100), 1)), keep, d


def taubin(P, E, n=20, lam=0.5, mu=-0.53):
    nv = len(P); deg = np.bincount(E.ravel(), minlength=nv).astype(float)
    for i in range(n):
        for f in (lam, mu):
            s = np.zeros_like(P); np.add.at(s, E[:, 0], P[E[:, 1]]); np.add.at(s, E[:, 1], P[E[:, 0]])
            P = P + f * (s / deg[:, None] - P)
    return P


def score_rings(X, ctx, nr):
    """blind-test scoring: each ring vs the true outer outline at its station (2D, mm, + = too fat)"""
    zs, stack, RES, X0, y0 = ctx['zs'], ctx['stack'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
    g = ctx['ground']; tin = ctx['meas']['track_f'] / 2000 - 0.13
    za, zb = B.bbox(ctx['side'], 1)
    d = np.full(len(X), np.nan)
    R = X.reshape(nr, NRAY, 3)
    for r in range(nr):
        z = R[r, :, 2].mean(); i = int(np.argmin(np.abs(zs - z)))
        o = B.outline(stack[i])
        if not len(o): continue
        T = np.c_[X0 + o[:, 0] * RES, y0 + o[:, 1] * RES]
        Q = R[r, :, :2]
        dd = np.sqrt(((Q[:, None, :] - T[None, :, :]) ** 2).sum(-1)).min(1)
        px = np.clip(np.round((Q[:, 0] - X0) / RES).astype(int), 0, stack.shape[1] - 1)
        py = np.clip(np.round((Q[:, 1] - y0) / RES).astype(int), 0, stack.shape[2] - 1)
        inside = stack[i][px, py]
        d[r * NRAY:(r + 1) * NRAY] = np.where(inside, -dd, dd) * 1000
    keep = np.isfinite(d) & (X[:, 1] - g > 0.12)
    for zc, yc, rr in ctx['arches']:
        keep &= ((X[:, 2] - zc) ** 2 + (X[:, 1] - yc) ** 2 > (rr + 0.01) ** 2)
    zlo, zhi = X[:, 2].min(), X[:, 2].max()
    keep &= ~((X[:, 1] - g < 0.35) & (np.abs(X[:, 0]) < tin) & (X[:, 2] > zlo + 0.25) & (X[:, 2] < zhi - 0.25))
    e = np.abs(d[keep])
    return dict(n=int(keep.sum()), median_mm=round(float(np.median(e)), 1), p90_mm=round(float(np.percentile(e, 90)), 1),
                within_3mm_pct=round(float(np.mean(e <= 3) * 100), 1), within_10mm_pct=round(float(np.mean(e <= 10) * 100), 1),
                bias_mm=round(float(np.median(d[keep])), 1)), keep, np.nan_to_num(d)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('car'); ap.add_argument('out')
    ap.add_argument('--method', default='m_prior'); ap.add_argument('--lines', default='all')
    a = ap.parse_args()
    ctx = B.setup(a.car, a.out)
    import importlib
    fn, _ = (B.build_hull(ctx['side'], ctx['top'], ctx['front'], ctx['spec'], ctx['zs'], ctx['ylim'])
             if a.method == 'hull' else importlib.import_module(a.method).build(ctx))
    P0, F, E, nr = loft(ctx, fn)
    P0 = taubin(P0, E)          # remove the pixel steps of the traced outlines
    kn5 = sorted(glob.glob(os.path.join(a.car, '*.kn5')), key=os.path.getsize, reverse=True)[0]
    k = KN5(kn5, load_textures=False); g = ctx['ground']; half_w = ctx['meas']['width'] / 2000
    TP, TN = truth_skin(k, g, half_w)
    # orient truth normals outwards (away from the car's centre line), so signed errors mean something
    c = np.c_[np.zeros(len(TP)), np.full(len(TP), g + 0.6), TP[:, 2]]
    TN *= np.sign(((TP - c) * TN).sum(1))[:, None]
    L, S = truth_lines(k, g, half_w)
    meta = loft.meta
    sec = float(os.environ.get('SECTIONS', 0.4))
    use_L = a.lines in ('all', 'creases'); use_S = a.lines in ('all', 'sections')
    pts = thin(L) if use_L else np.zeros((0, 3))
    pins = ring_pins(ctx, meta, pts, sec if use_S else 0)
    X, fixed = fit(P0, E, pins) if pins else (P0, np.zeros(len(P0), bool))
    rep, keep, d = score_rings(X, ctx, nr)
    rep.update(lines=a.lines, method=a.method, line_points=int(len(pts)), pinned_pct=round(100 * fixed.mean(), 1), rings=nr, quads=int(len(F)))
    np.savez(os.path.join(a.out, f"{ctx['car']}_step3_{a.lines}.npz"), X=X, F=F, keep=keep, d=d, fixed=fixed)
    json.dump(rep, open(os.path.join(a.out, f"{ctx['car']}_step3_{a.lines}.json"), 'w'), indent=1)
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
