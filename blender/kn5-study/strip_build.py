"""Thin-strip builder: narrow crease faces (steps, returns, ledges) as RULED surfaces between shared edge curves.

A crease region narrower than ~15 mm and more than 10x as long (the rear quarter's lamp-top channel: four strips
about 8 mm wide and 270 mm long) is not fitted as its own trimmed surface (its neighbours then overlap or gap by
~1 mm and the step looks ragged). Instead:
  * each long side of the strip is ONE fair 3D curve, a graph (t(s), h(s)) over the strip's axis, so its parameter
    is the distance s along the strip;
  * a side shared with a wide face = that face's own built edge (sampled densely in FreeCAD and refitted, 0.02 mm);
    a side shared with another strip or free (a gap edge) = fitted to the Kunos boundary vertices (5 mm resampled);
  * a curve shared by two strips is fitted once and used by both: the joins are exact by construction;
  * the strip surface = ruled surface between its two side curves over the same s range (rulings square to the axis).

Pure numpy (imported by panel_fit.py and by panel_fit_freecad.py inside FreeCAD).
"""
import numpy as np

WMAX = 0.015        # a strip: width below 15 mm ...
RATIO = 10.0        # ... and length above 10 x width


# ---------- B-spline graph y = g(s) (clamped uniform cubic, poles at Greville points => parameter = s) ----------
def knots(n, a, b, p=3):
    return np.r_[[a] * p, np.linspace(a, b, n - p + 1), [b] * p]


def basis(t, kv, n, p=3):
    t = np.clip(t, kv[p], kv[n] - 1e-12)
    N = np.zeros((len(t), len(kv) - 1))
    for i in range(len(kv) - 1):
        N[:, i] = (kv[i] <= t) & (t < kv[i + 1])
    for d in range(1, p + 1):
        M = np.zeros((len(t), len(kv) - 1 - d))
        for i in range(len(kv) - 1 - d):
            a = kv[i + d] - kv[i]; b = kv[i + d + 1] - kv[i + 1]
            if a > 0: M[:, i] += (t - kv[i]) / a * N[:, i]
            if b > 0: M[:, i] += (kv[i + d + 1] - t) / b * N[:, i + 1]
        N = M
    return N[:, :n]


def greville(kv, n, p=3):
    return np.array([kv[i + 1:i + p + 1].mean() for i in range(n)])


def fit_graph(s, Y, dom, tol, nmax=None, mu=1e-6):
    """Y (m, k) = g(s) as ONE cubic B-spline shared by all k columns: the fewest controls whose worst residual is
    within tol (light second-difference fairing). Returns dict(n, kv, g (Greville s), C (n, k), err)."""
    L = dom[1] - dom[0]
    if nmax is None: nmax = int(np.clip(L / 0.02, 4, 30))       # at most one control per 20 mm
    best = None
    for n in range(4, nmax + 1):
        kv = knots(n, *dom); B = basis(s, kv, n)
        D = np.zeros((n - 2, n))
        for i in range(n - 2): D[i, i:i + 3] = (1, -2, 1)
        C = np.linalg.solve(B.T @ B + mu * len(B) * D.T @ D, B.T @ Y)
        err = np.abs(B @ C - Y).max()
        best = dict(n=n, kv=kv, g=greville(kv, n), C=C, err=float(err))
        if err < tol: break
    return best


def eval_graph(f, s):
    return basis(np.asarray(s, float), f['kv'], f['n']) @ f['C']


# ---------- strip detection on the crease regions of one mesh ----------
def resample(P, step=0.005):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.unique(np.r_[np.arange(0, d[-1], step), d[-1]])
    return np.stack([np.interp(t, d, P[:, k]) for k in range(3)], 1)


def spine_s(Sp, X):
    """arc length along spine polyline Sp (dense) of the nearest point to each X; also returns the distance"""
    Sp = np.asarray(Sp); X = np.atleast_2d(X)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Sp, axis=0), axis=1))]
    A, B = Sp[:-1], Sp[1:]; AB = B - A; l2 = np.maximum((AB * AB).sum(1), 1e-18)
    out = np.zeros(len(X)); dist = np.zeros(len(X))
    for k in range(0, len(X), 512):
        Xk = X[k:k + 512]
        t = np.clip(((Xk[:, None] - A[None]) * AB[None]).sum(2) / l2[None], 0, 1)
        Q = A[None] + t[..., None] * AB[None]; e = np.linalg.norm(Xk[:, None] - Q, axis=2)
        j = e.argmin(1); out[k:k + 512] = d[j] + t[np.arange(len(Xk)), j] * np.sqrt(l2[j]); dist[k:k + 512] = e[np.arange(len(Xk)), j]
    return out, dist


def find_strips(V, F, Nv, pcs, components, boundary_loops, wmax=WMAX, ratio=RATIO, amin=3e-4):
    """{region index: strip dict} for the narrow regions of pcs (crease pieces of one mesh).
    strip dict: axis frame (c, es, et, en), s range, outward normal, and its two long sides, each with the key of
    the curve it lies on ((i, j) shared with region j, or ('free', i)), the neighbour j (or None) and the side's
    boundary polyline (metres, ordered along s, resampled every 5 mm)."""
    _, wid = components(V, F)
    vreg = {}
    for ri, Fr in enumerate(pcs):
        for w in set(wid[Fr.ravel()]): vreg.setdefault(w, set()).add(ri)
    rep = {}
    for i, w in enumerate(wid): rep.setdefault(w, i)
    out = {}
    for ri, Fr in enumerate(pcs):
        T = V[Fr]; A = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2
        if A < amin: continue
        P = V[np.unique(Fr)]; c = P.mean(0)
        n_ = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n_ *= np.sign((n_ * Nv[Fr].mean(1)).sum(1))[:, None]
        en = n_.sum(0); en /= np.linalg.norm(en)
        es = np.linalg.svd(P - c)[2][0]; es -= (es @ en) * en; es /= np.linalg.norm(es); et = np.cross(en, es)
        s = (P - c) @ es; Ln = np.ptp(s); W = A / max(Ln, 1e-9)
        if not (W < wmax and Ln > ratio * W): continue
        # significant neighbours: share at least 4 welded vertices with the strip
        cnt = {}
        for w in set(wid[Fr.ravel()]):
            for o in vreg[w] - {ri}: cnt[o] = cnt.get(o, 0) + 1
        sig = {o for o, k in cnt.items() if k >= 4}
        loops = boundary_loops(Fr, wid)
        if len(loops) != 1: continue                       # a strip has one outline (no openings)
        L = loops[0]
        lab = []
        for w in L:
            o = vreg[w] & sig - {ri}
            lab.append(('free',) if not (vreg[w] - {ri}) else (tuple(sorted(o)) if o else None))
        # runs of one label round the loop; corners (several neighbours) / junk labels split runs
        m = len(L); runs = []
        start = next((i for i in range(m) if lab[i] != lab[i - 1]), None)
        if start is None: continue
        i = start
        while True:
            j = i
            while lab[(j + 1) % m] == lab[i] and (j + 1) % m != start: j += 1
            runs.append((lab[i], [L[k % m] for k in range(i, j + 1)]))
            i = (j + 1) % m
            if i == start: break
        good = [(lb, r) for lb, r in runs if lb is not None and (lb == ('free',) or len(lb) == 1)]
        def run_len(r): Q = V[[rep[w] for w in r]]; return np.ptp((Q - c) @ es)
        good.sort(key=lambda x: -run_len(x[1]))
        if len(good) < 2: continue
        (la, ra), (lb_, rb) = good[0], good[1]
        if la == lb_ and la != ('free',): continue
        if min(run_len(ra), run_len(rb)) < 0.7 * Ln: continue    # both long sides must run (nearly) the whole strip
        sides = []
        for lbl, r in ((la, ra), (lb_, rb)):
            # extend the run by one vertex each way (the corner vertices belong to the side too)
            k0 = L.index(r[0]); k1 = L.index(r[-1])
            r = [L[(k0 - 1) % m]] + r + [L[(k1 + 1) % m]]
            Q = V[[rep[w] for w in r]]
            if ((Q[-1] - Q[0]) @ es) < 0: Q = Q[::-1]
            nb = None if lbl == ('free',) else lbl[0]
            key = ('free', ri) if nb is None else tuple(sorted((ri, nb)))
            sides.append(dict(key=[str(k) for k in key], nb=nb, pts=resample(Q).tolist()))
        # spine: the strip's midline from nearest-point pairs between the two sides (not equal arc fractions: one side
        # can run longer, e.g. a tapered end), lightly faired; every curve of the strip is parametrised by arc length
        # along it, so a curved strip (a 1.4 m roof-rail drip) works too. Points that wrap round the strip's ends are
        # dropped from the sides (further from the spine than the strip is wide).
        A_, B_ = [np.array(sd['pts']) for sd in sides]
        Wd = max(2.5 * W, 0.006)
        def nearest(X, Q):
            _, d_ = spine_s(Q, X); return d_
        ka = nearest(A_, B_) < Wd; kb = nearest(B_, A_) < Wd
        if ka.sum() < 4 or kb.sum() < 4: continue
        A2, B2 = A_[ka], B_[kb]
        Bn = np.array([B2[np.linalg.norm(B2 - a_, axis=1).argmin()] for a_ in A2])
        M_ = (A2 + Bn) / 2                                  # in side A's polyline order (a curved strip must not fold)
        u_ = np.r_[0, np.cumsum(np.linalg.norm(np.diff(A2, axis=0), axis=1))]   # side A's arc length (smooth)
        if u_[-1] < 0.5 * Ln: continue
        g_ = fit_graph(u_, M_, [0, u_[-1]], tol=5e-4, nmax=int(np.clip(u_[-1] / 0.03, 4, 40)), mu=1e-5)
        Sp = eval_graph(g_, np.linspace(0, u_[-1], max(20, int(u_[-1] / 0.001))))
        u_ = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Sp, axis=0), axis=1))]   # its own arc length from here on
        for sd, X_, k_ in ((sides[0], A_, ka), (sides[1], B_, kb)):
            sv, dv = spine_s(Sp, X_)
            # the longest stretch (in polyline order) running ALONG the spine: ds/darc > 0.7 (at the strip's ends the
            # outline turns across the strip - same s, other position - and would bend the side curve by the width)
            darc = np.linalg.norm(np.diff(X_, axis=0), axis=1); ok_ = np.r_[(np.diff(sv) > 0.7 * np.maximum(darc, 1e-9)), False]
            ok_ &= k_ & (dv < Wd)
            best, cur = (0, 0), None
            for i_, v_ in enumerate(ok_):
                if v_ and cur is None: cur = i_
                if (not v_) and cur is not None:
                    if i_ + 1 - cur > best[1] - best[0]: best = (cur, i_ + 1)
                    cur = None
            if best[1] - best[0] < 4: sd['pts'] = []; continue
            sd['pts'] = X_[best[0]:best[1]].tolist()
        if min(len(sd['pts']) for sd in sides) < 4: continue
        ulen = u_[-1]
        if min(np.ptp(spine_s(Sp, np.array(sd['pts']))[0]) for sd in sides) < 0.7 * ulen: continue   # a side too short
        # a long side made of runs along several neighbours (a 1.4 m drip rail: r1, r4, r21) needs a chain of curves:
        # not yet - such a region stays an ordinary trimmed face
        if ulen < 0.85 * Ln: continue
        for sd in sides: sd['maker'] = ri
        out[ri] = dict(spine=Sp.tolist(), frame=[c.tolist(), es.tolist(), et.tolist(), en.tolist()], s=[float(s.min()), float(s.max())],
                       width=float(W), length=float(Ln), area=float(A), sides=sides, strips_nb=sorted(sig))
    return out
