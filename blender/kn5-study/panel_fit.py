"""Panel = one smooth surface with few control points, trimmed to its real outline (CAD reverse-engineering).

    python panel_fit.py CAR_DIR OUT_DIR MESHNAME[:component] ...

For each panel (a mesh, or one connected piece of it):
1. Frame: best-fit plane (PCA); u along the car where possible, w = outward normal.
2. Surface: cubic B-spline height field over that plane, least squares + fairing (bending energy).
   Control grid starts coarse and is refined only until the fit is within tolerance -> as few
   control points as the shape needs (flat stays flat, curves stay even; nothing is smoothed afterwards).
   With uniform clamped knots and poles at the Greville points, the surface parameter equals the plane
   coordinate, so the outline projected onto the plane IS the trim curve in parameter space.
3. Outline: the mesh's boundary loop -> corners -> each side fitted as a 2D B-spline (ends pinned to
   the corners, fewest control points within tolerance).
4. Saves OUT/panels_fit.json for panel_fit_freecad.py (trimmed faces, STEP, mesh).
All lengths in the json are millimetres (plane coordinates); the frame maps them back to AC metres.
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5
from exact_dist import point_to_tris, stats

TOL_SURF = 0.3e-3     # surface fit target (p95, metres)
TOL_EDGE = 0.4e-3     # outline fit target (max, metres)


# ---------- B-spline basics (clamped uniform, degree 3) ----------
def knots(n, a, b, p=3):
    inner = np.linspace(a, b, n - p + 1)
    return np.r_[[a] * p, inner, [b] * p]


def basis(t, kv, n, p=3):
    """B (len(t), n) basis matrix"""
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


def diff2(n):
    D = np.zeros((n - 2, n))
    for i in range(n - 2): D[i, i:i + 3] = (1, -2, 1)
    return D


# ---------- data ----------
def load_mesh(car_dir, name):
    kn5 = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize)[-1]
    k = KN5(kn5, load_textures=False)
    m = next(m for m in k.meshes if m.name == name)
    return m.pos.astype(float), m.idx.reshape(-1, 3), m.nrm.astype(float)


def components(V, F):
    """connected pieces by shared (welded) vertex positions"""
    key = {tuple(np.round(v, 5)): i for i, v in enumerate(V)}
    wid = np.array([key[tuple(np.round(v, 5))] for v in V])
    parent = np.arange(len(V))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for f in wid[F]:
        for a in f[1:]:
            ra, rb = find(f[0]), find(a)
            if ra != rb: parent[ra] = rb
    root = np.array([find(w) for w in wid[F[:, 0]]])
    return [F[root == r] for r in np.unique(root)], wid


def boundary_loops(F, wid):
    """boundary edges (used by one face, welded ids) chained into loops of welded vertex ids"""
    W = wid[F]; cnt = {}
    for f in W:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            k = (min(a, b), max(a, b)); cnt[k] = cnt.get(k, 0) + 1
    nb = {}
    for (a, b), c in cnt.items():
        if c == 1: nb.setdefault(a, []).append(b); nb.setdefault(b, []).append(a)
    loops, seen = [], set()
    for s in nb:
        if s in seen: continue
        loop = [s]; seen.add(s); prev, cur = None, s
        while True:
            nxt = [x for x in nb[cur] if x != prev and x not in seen]
            if not nxt: break
            prev, cur = cur, nxt[0]; loop.append(cur); seen.add(cur)
        if len(loop) >= 4: loops.append(loop)
    return loops


# ---------- frame and fits ----------
def frame_of(P, Nrm):
    c = P.mean(0); U, S, Vt = np.linalg.svd(P - c, full_matrices=False)
    w = Vt[2] * np.sign(Vt[2] @ Nrm.mean(0))
    z = np.array([0, 0, 1.0]); y = np.array([0, 1.0, 0])
    e1 = z - (z @ w) * w
    if np.linalg.norm(e1) < 0.5: e1 = y - (y @ w) * w        # panel faces forward/back: u runs up
    e1 /= np.linalg.norm(e1); e2 = np.cross(w, e1)
    return c, e1, e2, w


def to_plane(P, fr):
    c, e1, e2, w = fr; Q = P - c
    return np.c_[Q @ e1, Q @ e2, Q @ w]


def from_plane(S, fr):
    c, e1, e2, w = fr
    return c + S[:, :1] * e1 + S[:, 1:2] * e2 + S[:, 2:3] * w


def sample_tris_bary(T, step=0.004):
    import car_loft as CL
    return CL.sample_tris(T, step)


def fit_surface(S, dom, nu, nv, lam):
    """least-squares height field h(s,t) with bending fairing; S (m,3) plane coords [m]"""
    ku = knots(nu, dom[0], dom[1]); kv = knots(nv, dom[2], dom[3])
    Bu = basis(S[:, 0], ku, nu); Bv = basis(S[:, 1], kv, nv)
    A = (Bu[:, :, None] * Bv[:, None, :]).reshape(len(S), -1)
    Du, Dv = diff2(nu), diff2(nv)
    R = np.r_[np.kron(Du, np.eye(nv)), np.kron(np.eye(nu), Dv)]
    M = A.T @ A + lam * len(S) * (R.T @ R)
    h = np.linalg.solve(M, A.T @ S[:, 2])
    return dict(nu=nu, nv=nv, ku=ku, kv=kv, H=h.reshape(nu, nv), gu=greville(ku, nu), gv=greville(kv, nv))


def select_fit(S, dom, folds=5, seed=0):
    """control count and fairing chosen by k-fold cross-validation on the vertices: the surface that
    best predicts vertices it has not seen (an over-fitted surface wiggles between them and loses).
    A simpler model is preferred when it is within 5 % of the best."""
    Lu, Lv = dom[1] - dom[0], dom[3] - dom[2]
    # blocked folds: hold out whole 40 mm patches (checkerboard), not single vertices - a vertex always has
    # near neighbours on its own mesh row, so random hold-outs never see ripples BETWEEN the data
    fold = ((np.floor(S[:, 0] / 0.04) + 2 * np.floor(S[:, 1] / 0.04)) % folds).astype(int)
    cands = []
    # control counts searched independently in both directions (tying them to the panel's proportions
    # missed the 6x5 the lower door skin needs)
    grid = [(nu, nv) for nu in range(4, 15) for nv in range(4, 15) if nu * nv <= max(20, 0.6 * len(S))]
    for nu, nv in grid:
        for lam in (1e-8, 1e-6, 1e-4):
            err = []
            for k in range(folds):
                tr = fold != k
                if tr.sum() < 8 or (~tr).sum() == 0: continue
                f = fit_surface(S[tr], dom, nu, nv, lam)
                err.append(eval_surface(f, S[~tr, 0], S[~tr, 1]) - S[~tr, 2])
            e = np.concatenate(err); cands.append((float(np.sqrt(np.mean(e ** 2))), nu * nv, nu, nv, lam))
    best = min(c[0] for c in cands)
    ok = [c for c in cands if c[0] <= best * 1.05]
    cvr, _, nu, nv, lam = min(ok, key=lambda c: (c[1], -c[4]))
    f = fit_surface(S, dom, nu, nv, lam); f['lam'] = lam
    r = np.abs(eval_surface(f, S[:, 0], S[:, 1]) - S[:, 2])
    return f, r, cvr


def eval_surface(fit, s, t):
    Bu = basis(np.asarray(s, float), fit['ku'], fit['nu']); Bv = basis(np.asarray(t, float), fit['kv'], fit['nv'])
    return np.einsum('ki,ij,kj->k', Bu, fit['H'], Bv)


def surf_grid(fit, dom, n=120):
    s = np.linspace(dom[0], dom[1], n); t = np.linspace(dom[2], dom[3], n)
    Bu = basis(s, fit['ku'], fit['nu']); Bv = basis(t, fit['kv'], fit['nv'])
    H = Bu @ fit['H'] @ Bv.T
    Ss, Tt = np.meshgrid(s, t, indexing='ij')
    return np.stack([Ss, Tt, H], -1)


def corners_of(L2, step=0.002, arm=0.012, thr=28.0, sep=0.03):
    """indices of corners on a closed 2D loop (resampled at step)"""
    n = len(L2); k = max(int(arm / step), 2)
    a = np.zeros(n)
    for i in range(n):
        p, q = L2[i] - L2[i - k], L2[(i + k) % n] - L2[i]
        a[i] = np.degrees(np.arccos(np.clip(p @ q / (np.linalg.norm(p) * np.linalg.norm(q) + 1e-12), -1, 1)))
    idx = []
    for i in np.argsort(-a):
        if a[i] < thr: break
        if all(min(abs(i - j), n - abs(i - j)) * step > sep for j in idx): idx.append(int(i))
    return sorted(idx), a


def vertex_corners(L, thr=35.0):
    """corners of a closed polygon: vertices where the outline turns sharply"""
    a = np.zeros(len(L))
    for i in range(len(L)):
        p, q = L[i] - L[i - 1], L[(i + 1) % len(L)] - L[i]
        a[i] = np.degrees(np.arccos(np.clip(p @ q / (np.linalg.norm(p) * np.linalg.norm(q) + 1e-12), -1, 1)))
    return [int(i) for i in np.where(a > thr)[0]]


def resample_closed(L, step):
    L = np.r_[L, L[:1]]; d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(L, axis=0), axis=1))]
    t = np.arange(0, d[-1], step)
    return np.c_[[np.interp(t, d, L[:, k]) for k in range(L.shape[1])]].T


def fit_curve2d(Q, tol, nmax=24, mu=1e-4):
    """open 2D cubic B-spline near the vertices Q, ends pinned to the corners, fewest poles within tol.
    A little bending fairing keeps it even when a side has only a few vertices."""
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]; u = d / d[-1]
    for n in range(4, nmax + 1):
        kv = knots(n, 0.0, 1.0); B = basis(u, kv, n)
        Bi = B[:, 1:-1]; rhs = Q - np.outer(B[:, 0], Q[0]) - np.outer(B[:, -1], Q[-1])
        D = diff2(n); Di = D[:, 1:-1]; drhs = -(np.outer(D[:, 0], Q[0]) + np.outer(D[:, -1], Q[-1]))
        M = Bi.T @ Bi + mu * (Di.T @ Di)
        Pm = np.linalg.solve(M, Bi.T @ rhs + mu * Di.T @ drhs); P = np.r_[Q[:1], Pm, Q[-1:]]
        err = np.linalg.norm(B @ P - Q, axis=1).max()
        if err < tol: break
    return dict(poles=P, knots=kv, err=float(err))


def fit_closed_curve2d(Q, tol, nmax=60):
    """periodic cubic B-spline for a smooth closed outline (no corners)"""
    Q = np.asarray(Q); d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.r_[Q, Q[:1]], axis=0), axis=1))]
    u = d[:-1] / d[-1]
    for n in range(6, nmax + 1):
        # periodic basis via wrapped uniform knots
        kv = np.arange(-3, n + 4) / n
        B = basis_periodic(u, n)
        P = np.linalg.lstsq(B, Q, rcond=None)[0]
        err = np.linalg.norm(B @ P - Q, axis=1).max()
        if err < tol: break
    return dict(poles=P, n=n, err=float(err), periodic=True)


def basis_periodic(u, n, p=3):
    kv = np.arange(-p, n + p + 1) / n
    B = basis_open_raw(u, kv, n + p)
    out = np.zeros((len(u), n))
    for i in range(n + p): out[:, i % n] += B[:, i]
    return out


def basis_open_raw(t, kv, n, p=3):
    N = np.zeros((len(t), len(kv) - 1))
    for i in range(len(kv) - 1): N[:, i] = (kv[i] <= t) & (t < kv[i + 1])
    for d in range(1, p + 1):
        M = np.zeros((len(t), len(kv) - 1 - d))
        for i in range(len(kv) - 1 - d):
            a = kv[i + d] - kv[i]; b = kv[i + d + 1] - kv[i + 1]
            if a > 0: M[:, i] += (t - kv[i]) / a * N[:, i]
            if b > 0: M[:, i] += (kv[i + d + 1] - t) / b * N[:, i + 1]
        N = M
    return N[:, :n]


def fit_panel(name, V, F, Nv, verbose=True):
    T = V[F]; P = V[np.unique(F)]
    fr = frame_of(P, Nv[np.unique(F)])
    S = to_plane(P, fr)                      # vertices only
    pad = 0.02
    dom = [S[:, 0].min() - pad, S[:, 0].max() + pad, S[:, 1].min() - pad, S[:, 1].max() + pad]
    f, r, cv = select_fit(S, dom)
    # outline: every boundary loop of the piece; outer = largest enclosed area, the others are openings
    _, wid = components(V, F)
    loops = boundary_loops(F, wid)
    def area2(L2): return 0.5 * abs(np.dot(L2[:, 0], np.roll(L2[:, 1], -1)) - np.dot(L2[:, 1], np.roll(L2[:, 0], -1)))
    rep = {w: i for i, w in enumerate(wid)}
    Ls = [to_plane(V[[rep[w] for w in L]], fr)[:, :2] for L in loops]
    order = np.argsort([-area2(L) for L in Ls])
    wires = []
    for k, oi in enumerate(order):
        Lp = Ls[oi]
        if k > 0 and area2(Lp) < 2e-4: continue          # tiny slits: not openings
        ci = vertex_corners(Lp)
        edges = []
        if len(ci) >= 2:
            for a_, b_ in zip(ci, ci[1:] + [ci[0] + len(Lp)]):
                edges.append(fit_curve2d(np.r_[Lp, Lp][a_:b_ + 1], TOL_EDGE))
        else:
            edges.append(fit_closed_curve2d(Lp, TOL_EDGE))
        wires.append(edges)
    edges = wires[0]; ci = [0] * (len(edges) if len(edges) > 1 else 0)
    if verbose:
        print(f'{name:28s} tris {len(F):5d}  control {f["nu"]}x{f["nv"]} lam {f["lam"]:g} cv {cv*1000:.2f} mm  fit p95 {np.percentile(r, 95)*1000:.2f} mm max {r.max()*1000:.2f} mm'
              f'  loops {len(loops)} wires {len(wires)} sides {[len(w) for w in wires]} max err {max(e["err"] for w in wires for e in w)*1000:.2f} mm')
    mm = lambda a: (np.asarray(a) * 1000).tolist()
    return dict(name=name, frame=[x.tolist() for x in fr], dom=mm(dom), nu=f['nu'], nv=f['nv'], ku=mm(f['ku']), kv=mm(f['kv']),
                poles=mm(np.stack(list(np.meshgrid(f['gu'], f['gv'], indexing='ij')) + [f['H']], -1)),
                wires=[[dict(poles=mm(e['poles']), knots=(e.get('knots', np.array([])).tolist()), periodic=bool(e.get('periodic', False))) for e in w] for w in wires],
                fit_p95_mm=float(np.percentile(r, 95) * 1000), fit_max_mm=float(r.max() * 1000))


def crease_pieces(V, F, Nv, deg=20.0):
    """the mesh split at its creases (dihedral > deg), largest first"""
    import cad_panels as CP
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); A = np.linalg.norm(n, axis=1)
    n /= np.maximum(A, 1e-12)[:, None]; n *= np.sign((n * Nv[F].mean(1)).sum(1))[:, None]
    regs = CP.crease_regions(T, n, np.arange(len(F)), deg)
    return [F[r] for r in sorted(regs, key=lambda r: -A[r].sum())]


def feature_pieces(V, F, Nv, R=0.10, deg=20.0, min_area=3e-4, grow=2):
    """split a mesh like a surface modeller: at creases (dihedral > deg) and between gentle 'primary'
    surfaces and tight 'blend' bands (local radius < R, from the authored vertex normals).
    Returns [(kind, F_piece)] largest first; kind 'primary' or 'blend'."""
    import cad_panels as CP
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); A = np.linalg.norm(n, axis=1) / 2
    n /= np.maximum(2 * A, 1e-12)[:, None]; n *= np.sign((n * Nv[F].mean(1)).sum(1))[:, None]
    # curvature per triangle at a modeller's scale: median normal change per metre to the triangles
    # 15-35 mm away inside the same crease region (single edges are too noisy)
    cen = T.mean(1); kap = np.zeros(len(F))
    regs = CP.crease_regions(T, n, np.arange(len(F)), deg)
    for reg in regs:
        C = cen[reg]; Nr = n[reg]
        for s in range(0, len(reg), 512):
            d = np.linalg.norm(C[s:s + 512, None] - C[None], axis=2)
            ang = np.arccos(np.clip(Nr[s:s + 512] @ Nr.T, -1, 1))
            m = (d > 0.015) & (d < 0.035)
            q = np.where(m, ang / np.maximum(d, 1e-6), np.nan)
            with np.errstate(all='ignore'): kap[reg[s:s + 512]] = np.nan_to_num(np.nanmedian(q, axis=1))
    tight = kap > 1.0 / R
    # grow the bands a little along the surface so a band that stops just short of a panel end still
    # separates the surfaces either side of it (a modeller runs a feature line edge to edge)
    for _ in range(grow):
        tc = cen[tight]
        if not len(tc): break
        near = np.zeros(len(F), bool)
        for s in range(0, len(F), 1024):
            near[s:s + 1024] = (np.linalg.norm(cen[s:s + 1024, None] - tc[None], axis=2) < 0.012).any(1)
        tight = tight | near
    out = []
    for reg in regs:
        for kind, sel in (('primary', reg[~tight[reg]]), ('blend', reg[tight[reg]])):
            if not len(sel): continue
            for c in CP.components(T, sel):
                if A[c].sum() >= min_area: out.append((kind, F[c], float(A[c].sum())))
    return [(k_, f_) for k_, f_, a_ in sorted(out, key=lambda x: -x[2])]


# ---------- feature lines and bands (a modeller's character lines, drawn end to end) ----------
def fit_func(s, y, dom, tol=1.0e-3, nmax=10, mu=1e-5):
    """smooth y = g(s) as a clamped cubic B-spline (poles at Greville points => exact 2D curve); robust"""
    keep = np.ones(len(s), bool)
    for n in range(4, nmax + 1):
        kv = knots(n, dom[0], dom[1]); D = diff2(n)
        for _ in range(4):
            B = basis(s[keep], kv, n)
            c = np.linalg.solve(B.T @ B + mu * len(B) * D.T @ D, B.T @ y[keep])
            r = np.abs(basis(s, kv, n) @ c - y)
            new = r < max(3e-3, 3 * np.median(r[keep]))
            if (new == keep).all(): break
            keep = new
        if np.percentile(r[keep], 95) < tol: break
    return dict(n=n, kv=kv, c=c, g=greville(kv, n), err=float(np.percentile(r[keep], 95)), used=int(keep.sum()))


def eval_func(f, s):
    return basis(np.asarray(s, float), f['kv'], f['n']) @ f['c']


def covered_runs(seg2, gap=0.003):
    """section segments (n,2,2: t,h) -> continuous runs of points sorted by t; a run breaks only where no
    segment covers the interval (an opening), not where triangle vertices happen to be far apart"""
    a = np.minimum(seg2[:, 0, 0], seg2[:, 1, 0]); b = np.maximum(seg2[:, 0, 0], seg2[:, 1, 0])
    o = np.argsort(a); runs, cur, end = [], [], -np.inf
    for i in o:
        if cur and a[i] > end + gap:
            runs.append(cur); cur = []
        cur.append(i); end = max(end, b[i]) if cur[:-1] else b[i]
    if cur: runs.append(cur)
    out = []
    for r in runs:
        Q = seg2[r].reshape(-1, 2); Q = Q[np.argsort(Q[:, 0])]
        out.append(Q)
    return out


def feature_lines(V, Fr, fr, ds=0.02, thr=10.0, arm=0.012, span=0.35):
    """character lines of a region: sharp turns on sections across it (s = const), chained along s,
    each fitted as one smooth curve t = g(s) over the whole region"""
    from section import cut
    P = to_plane(V, fr); u = np.unique(Fr); s0, s1 = P[u, 0].min(), P[u, 0].max()
    hits = []                                   # (section index, t, turn)
    secs = np.arange(s0 + ds / 2, s1, ds)
    k = max(int(arm / 0.002), 2)
    for si, s in enumerate(secs):
        seg = cut(P, Fr, 0, s)
        if not len(seg): continue
        for R_ in covered_runs(seg[:, :, 1:]):
            if np.ptp(R_[:, 0]) < 4 * arm: continue
            tq = np.arange(R_[0, 0], R_[-1, 0], 0.002); hq = np.interp(tq, R_[:, 0], R_[:, 1]); C = np.c_[tq, hq]
            a = np.zeros(len(C))
            for i in range(k, len(C) - k):
                p_, q_ = C[i] - C[i - k], C[i + k] - C[i]
                cr = p_[0] * q_[1] - p_[1] * q_[0]
                a[i] = np.sign(cr) * np.degrees(np.arccos(np.clip(p_ @ q_ / (np.linalg.norm(p_) * np.linalg.norm(q_) + 1e-12), -1, 1)))
            idx = []
            for i in np.argsort(-np.abs(a)):
                if abs(a[i]) < thr: break
                if all(abs(i - j) > 5 for j in idx): idx.append(i)
            # extent of the roll around each turn: the band holding 90 % of the turning (same sign) within
            # 40 mm, from the real profile vertices (faceted meshes put the turning at single vertices)
            Rv = R_[np.r_[True, np.linalg.norm(np.diff(R_, axis=0), axis=1) > 5e-4]]
            ang = np.zeros(len(Rv))
            for j in range(1, len(Rv) - 1):
                p_, q_ = Rv[j] - Rv[j - 1], Rv[j + 1] - Rv[j]
                ang[j] = np.degrees(np.arctan2(p_[0] * q_[1] - p_[1] * q_[0], p_ @ q_))
            for i in idx:
                tc = C[i, 0]; sg = np.sign(a[i])
                w_ = (np.abs(Rv[:, 0] - tc) < 0.04) & (np.sign(ang) == sg)
                if not w_.any():
                    hits.append((si, tc, a[i], 0.0, 0.0)); continue
                tv, av = Rv[w_, 0], np.abs(ang[w_]); o_ = np.argsort(tv); tv, av = tv[o_], av[o_]
                cum = np.cumsum(av) / av.sum()
                t_lo = tv[np.searchsorted(cum, 0.05)]; t_hi = tv[min(np.searchsorted(cum, 0.95), len(tv) - 1)]
                hits.append((si, tc, a[i], max(tc - t_lo, 0.0), max(t_hi - tc, 0.0)))
    chains = []
    for si, tt, aa, el, er in sorted(hits):
        best = None
        for ch in chains:
            if 0 < si - ch[-1][0] <= 3 and abs(ch[-1][1] - tt) < 0.012 and np.sign(ch[-1][2]) == np.sign(aa):
                if best is None or abs(ch[-1][1] - tt) < abs(best[-1][1] - tt): best = ch
        if best is not None: best.append((si, tt, aa, el, er))
        else: chains.append([(si, tt, aa, el, er)])
    lines = []
    dom = [s0 - 0.1, s1 + 0.1]
    for ch in chains:
        ss = secs[[c[0] for c in ch]]
        if ss.max() - ss.min() < span * (s1 - s0) or len(ch) < 6: continue
        f = fit_func(ss, np.array([c[1] for c in ch]), dom)
        f.update(s_lo=float(ss.min()), s_hi=float(ss.max()), turn=float(np.mean([c[2] for c in ch])), hits=len(ch),
                 ext_lo=float(np.median([c[3] for c in ch])), ext_hi=float(np.median([c[4] for c in ch])))
        lines.append(f)
    # one line per feature: drop a weaker line that runs within 6 mm of a stronger one
    lines.sort(key=lambda f: -abs(f['turn']) * f['hits'])
    sg = np.linspace(s0, s1, 50); out = []
    for f in lines:
        if all(np.median(np.abs(eval_func(f, sg) - eval_func(g, sg))) > 0.006 for g in out): out.append(f)
    out.sort(key=lambda f: np.mean(eval_func(f, sg)))
    return out


def fit_bands(name, V, Fr, Nv, overlap=0.002):
    """a region split into bands by its character lines; each band one surface, trimmed exactly on the lines"""
    u = np.unique(Fr); fr = frame_of(V[u], Nv[u])
    base = fit_panel(name, V, Fr, Nv, verbose=False)            # frame, outline wires (shared by all bands)
    lines = feature_lines(V, Fr, fr)
    P = to_plane(V[u], fr)
    # a strong line (rolled edge) gets its own narrow fillet band: two bounds at its measured extent
    cut_lines = []
    for L in lines:
        if abs(L['turn']) >= 25 and L['ext_lo'] > 0.003 and L['ext_hi'] > 0.003:
            for off in (-L['ext_lo'], L['ext_hi']):
                M = dict(L); M['c'] = L['c'] + off; cut_lines.append(M)
        else:
            cut_lines.append(L)
    bounds = [None] + cut_lines + [None]
    out = []
    for b in range(len(bounds) - 1):
        lo, hi = bounds[b], bounds[b + 1]
        m = np.ones(len(P), bool)
        if lo is not None: m &= P[:, 1] > eval_func(lo, P[:, 0]) - overlap
        if hi is not None: m &= P[:, 1] < eval_func(hi, P[:, 0]) + overlap
        S = P[m]
        if len(S) < 12: continue
        pad = 0.02
        dom = [S[:, 0].min() - pad, S[:, 0].max() + pad, S[:, 1].min() - pad, S[:, 1].max() + pad]
        f, r, cv = select_fit(S, dom)
        mm = lambda a: (np.asarray(a) * 1000).tolist()
        line = lambda L: None if L is None else dict(kv=mm(L['kv']), g=mm(L['g']), c=mm(L['c']))
        e = dict(base); e.update(name=f'{name}:b{b}', dom=mm(dom), nu=f['nu'], nv=f['nv'], ku=mm(f['ku']), kv=mm(f['kv']),
                                poles=mm(np.stack(list(np.meshgrid(f['gu'], f['gv'], indexing='ij')) + [f['H']], -1)),
                                band_lo=line(lo), band_hi=line(hi), fit_p95_mm=float(np.percentile(r, 95) * 1000))
        out.append(e)
        print(f"{e['name']:28s} verts {len(S):4d} control {f['nu']}x{f['nv']} lam {f['lam']:g}  cv {cv*1000:.2f} mm  fit p95 {np.percentile(r,95)*1000:.2f} max {r.max()*1000:.2f} mm")
    print(f"{name}: {len(lines)} character lines: " + ', '.join(f"turn {L['turn']:+.0f} deg ({L['ext_lo']*1000:.0f}/{L['ext_hi']*1000:.0f} mm), {L['hits']} hits, fit {L['err']*1000:.2f} mm" for L in lines))
    return out


def main():
    car, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    res = []
    for spec in sys.argv[3:]:
        name, _, comp = spec.partition(':')
        V, F, Nv = load_mesh(car, name)
        if comp.startswith('f'):
            fp = feature_pieces(V, F, Nv)
            for i, (kind, Fr) in enumerate(fp if comp == 'fall' else [fp[int(x)] for x in comp[1:].split(',')]):
                res.append(fit_panel(f'{name}:f{i}:{kind}', V, Fr, Nv))
            continue
        if comp.startswith('b'):
            for ri in comp[1:].split(','):
                res += fit_bands(f'{name}:r{ri}', V, crease_pieces(V, F, Nv)[int(ri)], Nv)
            continue
        if comp.startswith('r'):
            for ri in comp[1:].split(','):
                Fr = crease_pieces(V, F, Nv)[int(ri)]
                res.append(fit_panel(f'{name}:r{ri}', V, Fr, Nv))
            continue
        pieces, _ = components(V, F)
        pieces = sorted(pieces, key=lambda p: -len(p))
        if comp == 'all':
            sel = list(enumerate(pieces))
        elif comp:
            sel = [(int(c), pieces[int(c)]) for c in comp.split(',')]
        else:
            sel = [(0, pieces[0])]
        for ci, Fp in sel:
            res.append(fit_panel(f'{name}:{ci}', V, Fp, Nv))
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))


if __name__ == '__main__':
    main()


def exact_normals(p, X):
    """unit normals of fitted panel p (json entry) at world points X (metres): from the B-spline height field"""
    fr = [np.array(v) for v in p['frame']]; c, e1, e2, w = fr
    f = dict(nu=p['nu'], nv=p['nv'], ku=np.array(p['ku']) / 1000, kv=np.array(p['kv']) / 1000, H=np.array(p['poles'])[:, :, 2] / 1000)
    S = to_plane(X, fr); e = 1e-4
    hs = (eval_surface(f, S[:, 0] + e, S[:, 1]) - eval_surface(f, S[:, 0] - e, S[:, 1])) / (2 * e)
    ht = (eval_surface(f, S[:, 0], S[:, 1] + e) - eval_surface(f, S[:, 0], S[:, 1] - e)) / (2 * e)
    N = -hs[:, None] * e1 - ht[:, None] * e2 + w
    return N / np.linalg.norm(N, axis=1, keepdims=True)
