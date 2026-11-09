"""Blind-test build method: visual hull + feature lines, then sections pulled in by a LEARNED prior.

Education, not a shortcut: from OTHER cars (never the test car), learn how far the real body sits inside
the outline-only build, as a function of where you are:
  side pull-in   d_side[zn, hn]  = hull half-width - true half-width, per row
                 zn = position along the car (0 rear .. 1 front), hn = height within this section (0 bottom .. 1 top)
  top pull-in    d_top[zn, xn]   = hull top - true top, per column
                 xn = |x| / section half-width (0 centre .. 1 side)
Medians over all training cars. Applied to the test car using only its own pictures.

    python m_prior.py train OUT_DIR car1 car2 ...     # writes OUT_DIR/prior.npz
    blind test: --method m_prior   (PRIOR env var or OUT_DIR/prior.npz next to the truth cache)
"""
import os, sys, json
import numpy as np
import blind_test as B
import m_lines

NZ, NH, NX = 24, 12, 12


def _sections(ctx, fn):
    """Yield per-station (i, zn, hull, truth-or-None) for usable stations."""
    zs, side = ctx['zs'], ctx['side']
    za, zb = B.bbox(side, 1); zlo, zhi = zs[za], zs[zb - 1]
    for i, z in enumerate(zs):
        if z < zlo or z > zhi: continue
        yield i, (z - zlo) / (zhi - zlo), fn(z)


def _row_profile(a, xx):
    """per row: outer half-width (mean of both sides) or nan"""
    has = a.any(0)
    left = np.where(has, xx[np.argmax(a, axis=0)], np.nan)
    right = np.where(has, xx[a.shape[0] - 1 - np.argmax(a[::-1], axis=0)], np.nan)
    return (right - left) / 2, has


def _col_top(a, yy):
    has = a.any(1)
    top = np.where(has, yy[a.shape[1] - 1 - np.argmax(a[:, ::-1], axis=1)], np.nan)
    return top, has


def _masks(ctx):
    nx, ny = ctx['front'].shape
    xx = ctx['X0'] + np.arange(nx) * ctx['RES']; yy = ctx['ylim'][0] + np.arange(ny) * ctx['RES']
    return xx, yy


def _skip_rows(ctx, z, yy):
    """rows we must not learn from or change: underbody and inside the arch openings"""
    s = yy - ctx['ground'] < 0.12
    for zc, yc, r in ctx['arches']:
        if abs(z - zc) < r + 0.03:
            s |= np.abs(yy - yc) < np.sqrt(max((r + 0.03) ** 2 - (z - zc) ** 2, 0))
    return s


def train(out, cars):
    C = 'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/'
    side_acc = [[[] for _ in range(NH)] for _ in range(NZ)]
    top_acc = [[[] for _ in range(NX)] for _ in range(NZ)]
    for car in cars:
        ctx = B.setup(C + car, out)
        fn, _ = m_lines.build(ctx)
        xx, yy = _masks(ctx); stack = ctx['stack']
        for i, zn, h in _sections(ctx, fn):
            t = stack[i]; z = ctx['zs'][i]
            hw_h, hh = _row_profile(h, xx); hw_t, ht = _row_profile(t, xx)
            rows = np.where(hh & ht & ~_skip_rows(ctx, z, yy))[0]
            if len(rows) < 5: continue
            bot, topy = yy[rows].min(), yy[rows].max()
            zi = min(int(zn * NZ), NZ - 1)
            for r in rows:
                hn = (yy[r] - bot) / max(topy - bot, 1e-6); side_acc[zi][min(int(hn * NH), NH - 1)].append(hw_h[r] - hw_t[r])
            th, ch = _col_top(h, yy)
            tt, ct = _col_top(t, yy)
            hwmax = np.nanmax(hw_h[rows])
            cols = np.where(ch & ct)[0]
            for c in cols:
                xn = abs(xx[c]) / max(hwmax, 1e-6)
                if xn > 1: continue
                top_acc[zi][min(int(xn * NX), NX - 1)].append(th[c] - tt[c])
        print('trained on', car, flush=True)
    med = lambda L: np.array([[np.median(v) if len(v) > 20 else 0.0 for v in row] for row in L])
    d_side, d_top = med(side_acc), med(top_acc)
    np.savez(os.path.join(out, 'prior.npz'), d_side=d_side, d_top=d_top, cars=np.array(cars))
    return d_side, d_top


def build(ctx):
    fn, info = m_lines.build(ctx)
    path = os.environ.get('PRIOR') or os.path.join(os.path.dirname(os.path.abspath(ctx.get('out', '.'))), 'prior.npz')
    P = np.load(path); d_side, d_top = P['d_side'], P['d_top']
    if ctx['car'] in [str(c) for c in P['cars']]:
        raise SystemExit('prior was trained on the test car: not a blind test')
    xx, yy = _masks(ctx)
    zs, side = ctx['zs'], ctx['side']
    za, zb = B.bbox(side, 1); zlo, zhi = zs[za], zs[zb - 1]
    xc = 0.0
    def f(z):
        h = fn(z)
        if not h.any(): return h
        zn = np.clip((z - zlo) / (zhi - zlo), 0, 0.999); zi = int(zn * NZ)
        hw_h, hh = _row_profile(h, xx)
        skip = _skip_rows(ctx, z, yy)
        rows = np.where(hh & ~skip)[0]
        out = h.copy()
        if len(rows) >= 5:
            bot, topy = yy[rows].min(), yy[rows].max()
            hn = np.clip((yy - bot) / max(topy - bot, 1e-6), 0, 0.999)
            new_hw = hw_h - np.maximum(d_side[zi, (hn * NH).astype(int)], 0)
            lim = np.where(hh & ~skip, new_hw, np.inf)
            out &= np.abs(xx - xc)[:, None] <= lim[None, :]
            th, ch = _col_top(h, yy); hwmax = np.nanmax(hw_h[rows])
            xn = np.clip(np.abs(xx) / max(hwmax, 1e-6), 0, 0.999)
            new_top = th - np.maximum(d_top[zi, (xn * NX).astype(int)], 0)
            out &= yy[None, :] <= np.where(ch, new_top, np.inf)[:, None]
        return out
    info['prior'] = path
    return f, info


if __name__ == '__main__':
    if sys.argv[1] == 'train':
        d_side, d_top = train(sys.argv[2], sys.argv[3:])
        np.set_printoptions(precision=0, suppress=True, linewidth=200)
        print('side pull-in mm (rows rear->front, cols bottom->top)'); print(d_side * 1000)
        print('top pull-in mm (rows rear->front, cols centre->side)'); print(d_top * 1000)
