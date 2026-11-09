"""Step 3, second try: panel-based generator.

    python step3b_panels.py CAR_DIR OUT_DIR [--lines all|none] [--res 0.010]

The body is split into panels by which way they face, as Kunos splits a car into panels:
    side   x = f(z, y)   (left side, mirrored to the right like a Kunos half-model)
    top    y = f(z, x)   bonnet, roof, boot
    front  z = f(x, y)   front end
    rear   z = f(x, y)   rear end
Each panel is our own regular quad grid (RES). A cell belongs to a panel where that panel's height field
is shallower than 45 deg (the surface faces that way). Wheel arches are cut out.

Each panel's heights are solved as the smoothest surface (thin-plate) through the character lines,
which are drawn into the grid as continuous curves, with a weak pull to the outline build (pictures).
Lines (method test): taken from the true model, as in step3_rebuild.py.
Score: blind-test metric, each point against the true outer outline at its station.
"""
import sys, os, json, glob, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_test as B
import step3_rebuild as S3
from kn5full import KN5


def built_stack(ctx, fn):
    return np.stack([fn(z) for z in ctx['zs']])           # [nz, nx, ny] built solid from the pictures


def height_fields(ctx, Bs, res):
    """outline-build height fields for each panel on its own grid"""
    zs, RES, X0, y0 = ctx['zs'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
    nz, nx, ny = Bs.shape
    xx = X0 + np.arange(nx) * RES; yy = y0 + np.arange(ny) * RES
    xs = xx >= 0                                            # left half (AC +x = left)
    # side: for each station and row, outermost x of the build (left half)
    has = Bs[:, xs, :].any(1)                               # [nz, ny]
    last = nx - 1 - np.argmax(Bs[:, ::-1, :], axis=1)       # [nz, ny] index of outermost solid
    side = np.where(has, xx[last], np.nan)
    # top: for each station and column, top y
    hasT = Bs.any(2); topi = ny - 1 - np.argmax(Bs[:, :, ::-1], axis=2)
    top = np.where(hasT, yy[topi], np.nan)                  # [nz, nx]
    # front/rear: for each (x, y) the first/last station that is solid
    hasF = Bs.any(0)
    fi = nz - 1 - np.argmax(Bs[::-1], axis=0); ri = np.argmax(Bs, axis=0)
    front = np.where(hasF, zs[fi], np.nan); rear = np.where(hasF, zs[ri], np.nan)  # [nx, ny]
    return dict(side=(zs, yy, side), top=(zs, xx, top), front=(xx, yy, front), rear=(xx, yy, rear))


def resample(u, v, H, res):
    """resample a height field onto a regular res grid (nearest)"""
    U = np.arange(u.min(), u.max() + 1e-9, res); V = np.arange(v.min(), v.max() + 1e-9, res)
    iu = np.clip(np.round((U - u[0]) / (u[1] - u[0])).astype(int), 0, len(u) - 1)
    iv = np.clip(np.round((V - v[0]) / (v[1] - v[0])).astype(int), 0, len(v) - 1)
    return U, V, H[np.ix_(iu, iv)]


def slope_mask(H, res):
    gu, gv = np.gradient(H, res)
    with np.errstate(invalid='ignore'):
        return np.isfinite(H) & (np.abs(gu) < 1.0) & (np.abs(gv) < 1.0)


def grid_edges(M):
    idx = -np.ones(M.shape, int); idx[M] = np.arange(M.sum())
    E = []
    a, b = idx[:-1, :], idx[1:, :]; m = (a >= 0) & (b >= 0); E.append(np.c_[a[m], b[m]])
    a, b = idx[:, :-1], idx[:, 1:]; m = (a >= 0) & (b >= 0); E.append(np.c_[a[m], b[m]])
    return idx, np.concatenate(E)


def solve_height(H0, M, pins, res, w_data, iters=8000):
    """thin-plate on the masked grid: min |L h|^2 + w_data |h - H0|^2, pinned cells fixed"""
    idx, E = grid_edges(M)
    h0 = H0[M]
    fixed = np.zeros(len(h0), bool); tgt = h0.copy()
    for (i, j), v in pins.items():
        if M[i, j]: fixed[idx[i, j]] = True; tgt[idx[i, j]] = v
    X, _ = _fit1(h0, tgt, fixed, E, w_data, iters)
    out = np.full(M.shape, np.nan); out[M] = X; return out, fixed.sum()


def _fit1(h0, tgt, fixed, E, w, iters):
    nv = len(h0); deg = np.bincount(E.ravel(), minlength=nv).astype(float); deg[deg == 0] = 1
    def lap(x):
        s = np.zeros_like(x); np.add.at(s, E[:, 0], x[E[:, 1]]); np.add.at(s, E[:, 1], x[E[:, 0]]); return x - s / deg
    def lapT(y):
        q = y / deg; s = np.zeros_like(y); np.add.at(s, E[:, 0], q[E[:, 1]]); np.add.at(s, E[:, 1], q[E[:, 0]]); return y - s
    free = ~fixed
    A = lambda u: lapT(lap(u)) + w * u * free
    b = -lapT(lap(np.where(fixed, tgt, 0))) + w * h0 * free; b[fixed] = 0
    x = np.where(fixed, 0, h0)
    r = b - A(x); r[fixed] = 0; p = r.copy(); rs = (r * r).sum()
    for k in range(iters):
        Ap = A(p); Ap[fixed] = 0; a = rs / max((p * Ap).sum(), 1e-30)
        x = x + a * p; r = r - a * Ap; rn = (r * r).sum()
        if rn < 1e-16: break
        p = r + (rn / rs) * p; rs = rn
    return np.where(fixed, tgt, x), k


def panel_points(name, U, V, H):
    uu, vv = np.meshgrid(U, V, indexing='ij'); m = np.isfinite(H)
    u, v, h = uu[m], vv[m], H[m]
    if name == 'side': return np.c_[h, v, u]
    if name == 'top': return np.c_[v, h, u]
    return np.c_[u, v, h]


def to_panel(name, P):
    """3D points -> (u, v, h) in a panel's frame"""
    if name == 'side': return P[:, 2], P[:, 1], P[:, 0]
    if name == 'top': return P[:, 2], P[:, 0], P[:, 1]
    return P[:, 0], P[:, 1], P[:, 2]


def score_points(X, ctx):
    zs, stack, RES, X0, y0 = ctx['zs'], ctx['stack'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
    g = ctx['ground']; tin = ctx['meas']['track_f'] / 2000 - 0.13
    i = np.clip(np.round((X[:, 2] - zs[0]) / (zs[1] - zs[0])).astype(int), 0, len(zs) - 1)
    ok = np.abs(zs[i] - X[:, 2]) < 0.0026
    keep = ok & (X[:, 1] - g > 0.12)
    for zc, yc, r in ctx['arches']:
        keep &= ((X[:, 2] - zc) ** 2 + (X[:, 1] - yc) ** 2 > (r + 0.01) ** 2)
    zlo, zhi = zs[stack.any((1, 2))][[0, -1]]
    keep &= ~((X[:, 1] - g < 0.35) & (np.abs(X[:, 0]) < tin) & (X[:, 2] > zlo + 0.25) & (X[:, 2] < zhi - 0.25))
    d = np.full(len(X), np.nan)
    for st in np.unique(i[keep]):
        sel = np.where(keep & (i == st))[0]
        o = B.outline(stack[st])
        if not len(o): continue
        T = np.c_[X0 + o[:, 0] * RES, y0 + o[:, 1] * RES]
        Q = X[sel, :2]
        dd = np.sqrt(((Q[:, None, :] - T[None, :, :]) ** 2).sum(-1)).min(1)
        px = np.clip(np.round((Q[:, 0] - X0) / RES).astype(int), 0, stack.shape[1] - 1)
        py = np.clip(np.round((Q[:, 1] - y0) / RES).astype(int), 0, stack.shape[2] - 1)
        d[sel] = np.where(stack[st][px, py], -dd, dd) * 1000
    m = np.isfinite(d); e = np.abs(d[m])
    return dict(n=int(m.sum()), median_mm=round(float(np.median(e)), 1), p90_mm=round(float(np.percentile(e, 90)), 1),
                within_3mm_pct=round(float(np.mean(e <= 3) * 100), 1), within_10mm_pct=round(float(np.mean(e <= 10) * 100), 1),
                bias_mm=round(float(np.median(d[m])), 1)), d


def truth_boundary(ctx):
    """3D points of the true outer skin: solid voxels with an empty neighbour (incl. along the car)"""
    S = ctx['stack']; zs, RES, X0, y0 = ctx['zs'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
    inner = S.copy()
    inner[1:-1, 1:-1, 1:-1] = (S[1:-1, 1:-1, 1:-1] & S[:-2, 1:-1, 1:-1] & S[2:, 1:-1, 1:-1] & S[1:-1, :-2, 1:-1] &
                               S[1:-1, 2:, 1:-1] & S[1:-1, 1:-1, :-2] & S[1:-1, 1:-1, 2:])
    i, x, y = np.nonzero(S & ~inner)
    return np.c_[X0 + x * RES, y0 + y * RES, zs[i]], i


def score3d(X, ctx, TB, TI):
    """unsigned 3D distance from each of our points to the true outer skin (mm); same exclusions"""
    zs = ctx['zs']; g = ctx['ground']; tin = ctx['meas']['track_f'] / 2000 - 0.13
    keep = X[:, 1] - g > 0.12
    for zc, yc, r in ctx['arches']:
        keep &= ((X[:, 2] - zc) ** 2 + (X[:, 1] - yc) ** 2 > (r + 0.01) ** 2)
    zlo, zhi = TB[:, 2].min(), TB[:, 2].max()
    keep &= ~((X[:, 1] - g < 0.35) & (np.abs(X[:, 0]) < tin) & (X[:, 2] > zlo + 0.25) & (X[:, 2] < zhi - 0.25))
    d = np.full(len(X), np.nan)
    qi = np.clip(np.round((X[:, 2] - zs[0]) / (zs[1] - zs[0])).astype(int), 0, len(zs) - 1)
    order = np.argsort(TI); TBs, TIs = TB[order], TI[order]
    starts = np.searchsorted(TIs, np.arange(len(zs) + 1))
    for st in np.unique(qi[keep]):
        sel = np.where(keep & (qi == st))[0]
        a, b = starts[max(st - 3, 0)], starts[min(st + 4, len(zs))]
        C = TBs[a:b]
        if not len(C): continue
        best = np.full(len(sel), np.inf)
        for s in range(0, len(C), 6000):
            dd = ((X[sel, None, :] - C[None, s:s + 6000, :]) ** 2).sum(-1).min(1); best = np.minimum(best, dd)
        d[sel] = np.sqrt(best) * 1000
    m = np.isfinite(d); e = d[m]
    return dict(n=int(m.sum()), median_mm=round(float(np.median(e)), 1), p90_mm=round(float(np.percentile(e, 90)), 1),
                within_3mm_pct=round(float(np.mean(e <= 3) * 100), 1), within_10mm_pct=round(float(np.mean(e <= 10) * 100), 1)), d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('car'); ap.add_argument('out')
    ap.add_argument('--lines', default='all'); ap.add_argument('--res', type=float, default=0.010)
    ap.add_argument('--w', type=float, default=float(os.environ.get('W_DATA', 0.002)))
    a = ap.parse_args(); res = a.res
    ctx = B.setup(a.car, a.out)
    import m_prior
    fn, _ = m_prior.build(ctx)
    Bs = built_stack(ctx, fn)
    HF = height_fields(ctx, Bs, res)
    kn5 = sorted(glob.glob(os.path.join(a.car, '*.kn5')), key=os.path.getsize, reverse=True)[0]
    k = KN5(kn5, load_textures=False); g = ctx['ground']; half_w = ctx['meas']['width'] / 2000
    L, Sec = S3.truth_lines(k, g, half_w)
    # sections: every 400 mm, the true outer outline (from the truth slices), as curves
    secpts = []
    zs, RES, X0, y0 = ctx['zs'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
    for zc in np.arange(zs[0], zs[-1], 0.4):
        i = int(np.argmin(np.abs(zs - zc))); o = B.outline(ctx['stack'][i])
        if len(o): secpts.append(np.c_[X0 + o[:, 0] * RES, y0 + o[:, 1] * RES, np.full(len(o), zs[i])])
    lines = np.concatenate([L] + secpts) if a.lines == 'all' else np.zeros((0, 3))
    lines = lines[lines[:, 0] >= -0.005]                     # left half; the right is the mirror
    out_pts, report, meshes = [], {}, {}
    for name in ('side', 'top', 'front', 'rear'):
        u, v, H = HF[name]
        if name in ('front', 'rear'):
            sel = u >= -0.005; u, H = u[sel], H[sel]
        if name == 'top':
            sel = v >= -0.005; v, H = v[sel], H[:, sel]
        U, V, H0 = resample(u, v, H, res)
        M = slope_mask(H0, res)
        if name == 'front': M &= H0 > (zs[0] + zs[-1]) / 2
        if name == 'rear': M &= H0 < (zs[0] + zs[-1]) / 2
        # pins: line points that belong to this panel (close to its build height, in a valid cell)
        pins = {}
        if len(lines):
            pu, pv, ph = to_panel(name, lines)
            iu = np.round((pu - U[0]) / res).astype(int); iv = np.round((pv - V[0]) / res).astype(int)
            ok = (iu >= 0) & (iu < len(U)) & (iv >= 0) & (iv < len(V))
            for a_, b_, h in zip(iu[ok], iv[ok], ph[ok]):
                if M[a_, b_] and abs(h - H0[a_, b_]) < 0.06: pins.setdefault((a_, b_), []).append(h)
            pins = {kk: float(np.mean(vv)) for kk, vv in pins.items()}
        Hs, npin = solve_height(H0, M, pins, res, a.w)
        P = panel_points(name, U, V, Hs)
        out_pts.append(P); meshes[name] = (U, V, Hs)
        report[name] = dict(cells=int(M.sum()), pinned=int(npin))
    X = np.concatenate(out_pts)
    X = np.concatenate([X, X * [-1, 1, 1]])                # mirror to the right side
    TB, TI = truth_boundary(ctx)
    rep, d = score3d(X, ctx, TB, TI)
    rep.update(panels=report, lines=a.lines, res=res)
    np.savez(os.path.join(a.out, f"{ctx['car']}_step3b_{a.lines}.npz"), X=X, d=d,
             **{f'{n}_{q}': arr for n, (U, V, H) in meshes.items() for q, arr in (('U', U), ('V', V), ('H', H))})
    json.dump(rep, open(os.path.join(a.out, f"{ctx['car']}_step3b_{a.lines}.json"), 'w'), indent=1)
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
