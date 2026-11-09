"""Step 3, third try: one seamless quad mesh (a cube inflated onto the body) + character lines.

    python step3c_quadsphere.py CAR_DIR OUT_DIR [--n 192] [--lines all|none] [--w 0.0003]

Fixes the panel generator's two main faults:
  1. seams: the body is ONE connected quad mesh, a cube with each face split into N x N quads and inflated
     onto the car (the 8 cube corners are the only poles). It works in a space scaled by the car's
     half-dimensions, so quads are spread evenly over the sides, top and ends.
  2. ripples/dimples: each vertex has ONE unknown, its distance from the car's centre along its own ray.
     Line points pin the ray they lie on. Pins that disagree with their neighbouring pins by more than
     PIN_TOL are dropped as noise (inner panel returns, pixel steps). Then a thin-plate fill with a weak
     pull to the outline build.
Score: 3D distance to the true outer skin, like step3b_panels.py.
"""
import sys, os, json, glob, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_test as B
import step3_rebuild as S3
import step3b_panels as S3b
from kn5full import KN5


def quad_sphere(n):
    """unit-cube surface split into n x n quads per face; returns welded vertices (on the cube), quads, edges"""
    t = np.linspace(-1, 1, n + 1)
    V, F = [], []
    for ax in range(3):
        for s in (-1, 1):
            a, b = [i for i in range(3) if i != ax]
            uu, vv = np.meshgrid(t, t, indexing='ij')
            P = np.zeros((n + 1, n + 1, 3)); P[..., ax] = s; P[..., a] = uu; P[..., b] = vv
            base = sum(len(x) for x in V)
            V.append(P.reshape(-1, 3))
            idx = base + np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
            q = np.c_[idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()]
            if (s > 0) != (ax == 1): q = q[:, ::-1]
            F.append(q)
    V = np.concatenate(V); F = np.concatenate(F)
    key = np.round(V * n * 4).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V = V[first]; F = inv.ravel()[F]
    E = np.unique(np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 3]], F[:, [3, 0]]]), axis=1), axis=0)
    return V, F, E


def frame(ctx, Bs):
    """centre and half-dimensions of the build (normalised space = (p - c) / h)"""
    zs, RES, X0, y0 = ctx['zs'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
    iz = np.where(Bs.any((1, 2)))[0]; ix = np.where(Bs.any((0, 2)))[0]; iy = np.where(Bs.any((0, 1)))[0]
    lo = np.array([X0 + ix[0] * RES, y0 + iy[0] * RES, zs[iz[0]]]); hi = np.array([X0 + ix[-1] * RES, y0 + iy[-1] * RES, zs[iz[-1]]])
    c = (lo + hi) / 2; c[0] = 0.0
    c[1] = ctx['ground'] + 0.45 * (hi[1] - ctx['ground'])     # a bit below mid-height: rays hit the roof squarer
    h = (hi - lo) / 2 * 1.02
    return c, h


def _solid_at(ctx, Bs, P):
    zs, RES, X0, y0 = ctx['zs'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
    nz, nx, ny = Bs.shape
    iz = np.round((P[..., 2] - zs[0]) / (zs[1] - zs[0])).astype(int)
    ix = np.round((P[..., 0] - X0) / RES).astype(int); iy = np.round((P[..., 1] - y0) / RES).astype(int)
    ok = (iz >= 0) & (iz < nz) & (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    s = np.zeros(ok.shape, bool); s[ok] = Bs[iz[ok], ix[ok], iy[ok]]
    return s


def initial_r(ctx, Bs, c, h, D):
    """distance (normalised units) along each direction to the outermost solid point of the build:
    coarse march, then a fine march around the hit (~0.5 mm steps)"""
    ts = np.arange(0.02, 1.8, 0.004)
    r = np.zeros(len(D))
    for s in range(0, len(D), 4000):
        d = D[s:s + 4000]
        solid = _solid_at(ctx, Bs, c + (d[:, None, :] * ts[None, :, None]) * h)
        last = np.where(solid.any(1), solid.shape[1] - 1 - np.argmax(solid[:, ::-1], axis=1), 0)
        t0 = ts[last]
        fine = t0[:, None] + np.arange(-0.004, 0.0081, 0.0002)[None, :]
        sf = _solid_at(ctx, Bs, c + (d[:, None, :] * fine[:, :, None]) * h)
        lf = np.where(sf.any(1), sf.shape[1] - 1 - np.argmax(sf[:, ::-1], axis=1), 0)
        r[s:s + 4000] = fine[np.arange(len(d)), lf]
    return r


def line_pins(points, c, h, n, Vcube, tol):
    """map line points to (vertex, r): vertex = nearest grid vertex on the point's own ray"""
    q = (points - c) / h
    r = np.linalg.norm(q, axis=1); d = q / r[:, None]
    # direction -> cube surface point -> nearest grid vertex
    cube = d / np.abs(d).max(1)[:, None]
    g = np.round((cube + 1) / 2 * n) / n * 2 - 1
    key = np.round(g * n * 4).astype(np.int64)
    vkey = np.round(Vcube * n * 4).astype(np.int64)
    lut = {tuple(k): i for i, k in enumerate(vkey)}
    pins = {}
    for k, rr, cu, gg in zip(map(tuple, key), r, cube, g):
        i = lut.get(k)
        if i is None: continue
        # the point's direction and the vertex's direction differ slightly: scale r by the cosine
        dv = Vcube[i] / np.linalg.norm(Vcube[i]); dp = cu / np.linalg.norm(cu)
        pins.setdefault(i, []).append(rr * max(float(dv @ dp), 0.0))
    return {i: float(np.median(v)) for i, v in pins.items() if len(v) and np.ptp(v) < 3 * tol} if pins else {}


def denoise_pins(pins, E, nv, tol):
    """drop pins that disagree with the median of pinned neighbours (within 2 rings) by > tol"""
    adj = [[] for _ in range(nv)]
    for a, b in E: adj[a].append(b); adj[b].append(a)
    keep = {}
    for i, r in pins.items():
        nb = set(adj[i])
        for j in list(nb): nb.update(adj[j])
        vals = [pins[j] for j in nb if j in pins and j != i]
        if len(vals) < 2 or abs(r - np.median(vals)) < tol: keep[i] = r
    return keep


def smooth_scalar(v, E, n, lam=0.5, mu=-0.53):
    nv = len(v); deg = np.bincount(E.ravel(), minlength=nv).astype(float)
    for _ in range(n):
        for f in (lam, mu):
            s = np.zeros(nv); np.add.at(s, E[:, 0], v[E[:, 1]]); np.add.at(s, E[:, 1], v[E[:, 0]])
            v = v + f * (s / deg - v)
    return v


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('car'); ap.add_argument('out')
    ap.add_argument('--n', type=int, default=192); ap.add_argument('--lines', default='all')
    ap.add_argument('--w', type=float, default=0.0003)
    a = ap.parse_args()
    ctx = B.setup(a.car, a.out)
    import m_prior
    fn, _ = m_prior.build(ctx)
    Bs = S3b.built_stack(ctx, fn)
    c, h = frame(ctx, Bs)
    Vc, F, E = quad_sphere(a.n)
    D = Vc / np.linalg.norm(Vc, axis=1)[:, None]
    r0 = initial_r(ctx, Bs, c, h, D)
    r0 = smooth_scalar(r0, E, int(os.environ.get('SMOOTH_IT', 40)))   # remove the build's pixel/slice steps
    tol = float(os.environ.get('PIN_TOL', 0.004))      # normalised units (~3-8 mm)
    pins = {}
    if a.lines == 'all':
        kn5 = sorted(glob.glob(os.path.join(a.car, '*.kn5')), key=os.path.getsize, reverse=True)[0]
        k = KN5(kn5, load_textures=False); g = ctx['ground']; half_w = ctx['meas']['width'] / 2000
        L, Sec = S3.truth_lines(k, g, half_w)
        zs, RES, X0, y0 = ctx['zs'], ctx['RES'], ctx['X0'], ctx['ylim'][0]
        # sections: exact cuts through the model's outer panels every 400 mm (not pixel outlines)
        pts = np.concatenate([L, Sec[np.isin(np.round(Sec[:, 2] / 0.4), np.round(np.arange(-2.4, 2.41, 0.4) / 0.4))]])
        # only points on the outer skin as seen along their ray: within 6 cm of the outline build
        pins = line_pins(pts, c, h, a.n, Vc, tol)
        pins = {i: v for i, v in pins.items() if abs(v - r0[i]) * np.linalg.norm(D[i] * h) < 0.06}
        pins = denoise_pins(pins, E, len(Vc), tol)
    # thin-plate on r with a weak pull to r0
    fixed = np.zeros(len(Vc), bool); tgt = r0.copy()
    for i, v in pins.items(): fixed[i] = True; tgt[i] = v
    r, it = S3b._fit1(r0, tgt, fixed, E, a.w, 12000)
    X = c + (D * r[:, None]) * h
    TB, TI = S3b.truth_skin_dense(ctx, a.car)
    rep, d = S3b.score3d(X, ctx, TB, TI)
    rep.update(lines=a.lines, grid_n=a.n, verts=int(len(X)), quads=int(len(F)), pins=int(fixed.sum()), cg_iters=int(it), w=a.w, pin_tol=tol)
    np.savez(os.path.join(a.out, f"{ctx['car']}_step3c_{a.lines}.npz"), X=X, F=F, d=d, fixed=fixed)
    json.dump(rep, open(os.path.join(a.out, f"{ctx['car']}_step3c_{a.lines}.json"), 'w'), indent=1)
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
