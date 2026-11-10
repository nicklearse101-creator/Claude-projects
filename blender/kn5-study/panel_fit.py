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
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path:
    sys.path.append(r'D:\ClaudeData\pylibs')     # extra libraries (SciPy) live on D:, never C:
from kn5full import KN5
from exact_dist import point_to_tris, stats

TOL_SURF = 0.3e-3     # surface fit target (p95, metres)
TOL_EDGE = 0.4e-3     # outline fit target (max, metres)
BLEND = os.environ.get('PF_BLEND', '1') == '1'       # rolled edges built from their neighbour (tangent), not fitted freely
CORNERS = os.environ.get('PF_CORNERS', '0') == '1'   # roll bands: separate corner patches where the line stops (off: too few vertices there on the AE86, 13-18, unstable)


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
    V, F, N = m.pos.astype(float), m.idx.reshape(-1, 3), m.nrm.astype(float)
    clip = os.environ.get('PF_CLIP')            # 'xmin,xmax,ymin,ymax,zmin,zmax' (AC metres): one panel of a shell
    if clip:
        b = np.array([float(x) for x in clip.split(',')]).reshape(3, 2); c = V[F].mean(1)
        F = F[((c >= b[:, 0]) & (c <= b[:, 1])).all(1)]
    return V, F, N


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


def fit_surface(S, dom, nu, nv, lam, w=None):
    """least-squares height field h(s,t) with bending fairing; S (m,3) plane coords [m]; w: optional row weights"""
    ku = knots(nu, dom[0], dom[1]); kv = knots(nv, dom[2], dom[3])
    Bu = basis(S[:, 0], ku, nu); Bv = basis(S[:, 1], kv, nv)
    A = (Bu[:, :, None] * Bv[:, None, :]).reshape(len(S), -1)
    Du, Dv = diff2(nu), diff2(nv)
    R = np.r_[np.kron(Du, np.eye(nv)), np.kron(np.eye(nu), Dv)]
    Aw = A if w is None else A * w[:, None]
    M = Aw.T @ A + lam * len(S) * (R.T @ R)
    h = np.linalg.solve(M, Aw.T @ S[:, 2])
    return dict(nu=nu, nv=nv, ku=ku, kv=kv, H=h.reshape(nu, nv), gu=greville(ku, nu), gv=greville(kv, nv))


def select_fit(S, dom, folds=5, seed=0, nmax=None, strip=False):
    """control count and fairing chosen by k-fold cross-validation on the vertices: the surface that
    best predicts vertices it has not seen (an over-fitted surface wiggles between them and loses).
    A simpler model is preferred when it is within 5 % of the best."""
    Lu, Lv = dom[1] - dom[0], dom[3] - dom[2]
    # blocked folds: hold out whole 40 mm patches (checkerboard), not single vertices - a vertex always has
    # near neighbours on its own mesh row, so random hold-outs never see ripples BETWEEN the data
    # block size from the data's own spacing: the hidden patches must be bigger than the gap between vertex rows
    # (40 mm on the door; the wing's rows are 100-150 mm apart and 40 mm blocks let ripples between rows through)
    sub = S[:: max(1, len(S) // 400), :2]
    dnn = np.sqrt(((sub[:, None] - sub[None]) ** 2).sum(2) + np.eye(len(sub)) * 1e9).min(1)
    blk = float(np.clip(2.5 * np.median(dnn), 0.04, 0.15))
    fold = ((np.floor(S[:, 0] / blk) + 2 * np.floor(S[:, 1] / blk)) % folds).astype(int)
    if strip:          # a narrow strip (arch lip): hide whole 80 mm stretches along it, keep full cross-sections
        fold = (np.floor(S[:, 0] / 0.08) % folds).astype(int)
    cands = []
    # control counts searched independently in both directions (tying them to the panel's proportions
    # missed the 6x5 the lower door skin needs)
    # up to one control per ~50 mm along each direction (min 14, max 24): a 1.1 m arch lip needs ~20 along
    if nmax is None: nmax = [int(np.clip((dom[1] - dom[0]) / 0.05, 14, 24)), int(np.clip((dom[3] - dom[2]) / 0.05, 14, 24))]
    grid = [(nu, nv) for nu in range(4, nmax[0] + 1) for nv in range(4, nmax[1] + 1) if nu * nv <= max(20, 0.6 * len(S))]
    for nu, nv in grid:
        for lam in (1e-8, 1e-6, 1e-4):
            err = []
            for k in range(folds):
                tr = fold != k
                if tr.sum() < 8 or (~tr).sum() == 0: continue
                f = fit_surface(S[tr], dom, nu, nv, lam)
                err.append(eval_surface(f, S[~tr, 0], S[~tr, 1]) - S[~tr, 2])
            if not err: continue                       # too few vertices to cross-check this size
            e = np.concatenate(err); cands.append((float(np.sqrt(np.mean(e ** 2))), nu * nv, nu, nv, lam))
    if not cands:                                      # a handful of vertices: a plain, well-faired 4x4
        cands = [(0.0, 16, 4, 4, 1e-4)]
    best = min(c[0] for c in cands)
    ok = [c for c in cands if c[0] <= best * 1.05]
    cvr, _, nu, nv, lam = min(ok, key=lambda c: (c[1], -c[4]))
    f = fit_surface(S, dom, nu, nv, lam); f['lam'] = lam
    r = np.abs(eval_surface(f, S[:, 0], S[:, 1]) - S[:, 2])
    # Class-A rule: the FAIREST surface within tolerance, not the closest. Smooth harder (bending energy) while the
    # fit stays within 25 % / 0.3 mm of the best - ripples between Kunos's vertex rows show as swirls in zebra
    if os.environ.get('PF_FAIR', '1') == '1':
        p0 = np.percentile(r, 95); lim = max(1.25 * p0, p0 + 0.3e-3)
        for lam2 in (1e-5, 1e-4, 1e-3, 1e-2, 3e-2):
            if lam2 <= f['lam']: continue
            f2 = fit_surface(S, dom, nu, nv, lam2); r2 = np.abs(eval_surface(f2, S[:, 0], S[:, 1]) - S[:, 2])
            if np.percentile(r2, 95) > lim: break
            f, r = f2, r2; f['lam'] = lam2
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


def fit_panel(name, V, F, Nv, verbose=True, fr=None, outline_only=False):
    """one trimmed surface for a piece; fr = a given frame (default: the piece's own best-fit plane);
    outline_only = just the frame and outline wires (for a band patch that brings its own surface)"""
    T = V[F]; P = V[np.unique(F)]
    if fr is None: fr = frame_of(P, Nv[np.unique(F)])
    S = to_plane(P, fr)                      # vertices only
    pad = 0.02
    dom = [S[:, 0].min() - pad, S[:, 0].max() + pad, S[:, 1].min() - pad, S[:, 1].max() + pad]
    if outline_only:
        f = dict(nu=4, nv=4, lam=0.0, ku=knots(4, dom[0], dom[1]), kv=knots(4, dom[2], dom[3]))
        f.update(gu=greville(f['ku'], 4), gv=greville(f['kv'], 4), H=np.zeros((4, 4))); r = np.zeros(1); cv = 0.0; verbose = False
    else:
        f, r, cv = select_fit(S, dom)
    # outline: every boundary loop of the piece; outer = largest enclosed area, the others are openings
    _, wid = components(V, F)
    loops = boundary_loops(F, wid)
    def area2(L2): return 0.5 * abs(np.dot(L2[:, 0], np.roll(L2[:, 1], -1)) - np.dot(L2[:, 1], np.roll(L2[:, 0], -1)))
    rep = {w: i for i, w in enumerate(wid)}
    Ls = [to_plane(V[[rep[w] for w in L]], fr)[:, :2] for L in loops]
    order = np.argsort([-area2(L) for L in Ls])
    wires = []
    def despike(L):
        # Kunos outlines contain zero-width slits (the edge runs out and straight back: 781 -> 806 -> 781 mm);
        # they make the trim outline self-touching and invalid. Remove back-tracking vertices and duplicates.
        L = [q for i, q in enumerate(L) if i == 0 or np.linalg.norm(q - L[i - 1]) > 1e-4]
        changed = True
        while changed and len(L) > 4:
            changed = False
            for i in range(len(L)):
                a_, b_, c_ = L[i - 1], L[i], L[(i + 1) % len(L)]
                p_, q_ = b_ - a_, c_ - b_
                if np.linalg.norm(p_) < 1e-4 or np.linalg.norm(q_) < 1e-4 or p_ @ q_ / (np.linalg.norm(p_) * np.linalg.norm(q_)) < -0.98:
                    del L[i]; changed = True; break
                # a narrow tooth (out and back within a 25 mm base): a panel cut out of a shell across Kunos's long
                # thin triangles leaves a comb of them; the trim outline then crosses itself
                base_ = np.linalg.norm(c_ - a_)
                if base_ < 0.025 and np.linalg.norm(p_) + np.linalg.norm(q_) > 2.5 * base_ + 0.01:
                    del L[i]; changed = True; break
        return np.array(L)
    for k, oi in enumerate(order):
        Lp = despike(list(Ls[oi]))
        if k > 0 and area2(Lp) < 2e-4: continue          # tiny slits: not openings
        ci = vertex_corners(Lp)
        edges = []
        if len(ci) >= 2:
            for a_, b_ in zip(ci, ci[1:] + [ci[0] + len(Lp)]):
                Q_ = np.r_[Lp, Lp][a_:b_ + 1]; ln = np.linalg.norm(np.diff(Q_, axis=0), axis=1).sum()
                # long sides (a 1.35 m ledge edge) need more than 24 controls for 0.4 mm; capped ones trim wrongly
                # fitted to the side's polyline resampled every 5 mm (straight between the original edge vertices):
                # with only the vertices (200 mm apart on the ledge) extra controls wiggle between them
                dq = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q_, axis=0), axis=1))]
                tq = np.unique(np.r_[np.arange(0, dq[-1], 0.005), dq])
                Qd = np.c_[np.interp(tq, dq, Q_[:, 0]), np.interp(tq, dq, Q_[:, 1])]
                edges.append(fit_curve2d(Qd, TOL_EDGE, nmax=int(np.clip(ln / 0.03, 24, 80))))
        else:
            # smooth closed outline (oval mirror glass, lock barrel hole): fitted to its polyline resampled
            # densely - through its few vertices alone the closed curve overshoots far outside the panel
            per = np.linalg.norm(np.diff(np.r_[Lp, Lp[:1]], axis=0), axis=1).sum()
            edges.append(fit_closed_curve2d(resample_closed(Lp, min(0.005, per / 120)), TOL_EDGE))
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


def wrap_split(V, F, Nv, max_spread=60.0, kmax=8):
    """a smooth face that wraps too far for one height field (normals spread > 70 deg, e.g. a rounded boss)
    split into connected pieces whose normals stay within max_spread of their mean (k-means on the normals)"""
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    n *= np.sign((n * Nv[F].mean(1)).sum(1))[:, None]
    spread = lambda m: np.degrees(np.arccos(np.clip(n[m] @ (lambda c: c / np.linalg.norm(c))(n[m].mean(0)), -1, 1))).max()
    if spread(np.ones(len(F), bool)) <= 70: return [F]
    rng = np.random.default_rng(0)
    for k in range(2, kmax + 1):
        C = n[rng.choice(len(F), k, replace=False)]
        for _ in range(30):
            lab = np.argmax(n @ C.T, axis=1)
            C = np.array([n[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)]); C /= np.linalg.norm(C, axis=1)[:, None]
        if all(spread(lab == j) <= max_spread for j in range(k) if (lab == j).any()): break
    out = []
    for j in range(k):
        if not (lab == j).any(): continue
        pcs, _ = components(V, F[lab == j]); out += pcs
    return sorted(out, key=lambda p: -len(p))


def crease_pieces(V, F, Nv, deg=None):
    """the mesh split at its creases (dihedral > deg, default 20; PF_CREASE overrides: the wing's crease strip
    edges are softer than the door's), largest first"""
    if deg is None: deg = float(os.environ.get('PF_CREASE', 20.0))
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


def feature_lines(V, Fr, fr, ds=0.02, thr=10.0, arm=None, span=0.35):
    """character lines of a region: sharp turns on sections across it (s = const), chained along s,
    each fitted as one smooth curve t = g(s) over the whole region.
    The section arm is 12 mm, shorter on narrow regions (a 45 mm crease strip with a 5 mm chamfer along
    one side needs ~4 mm arms, or the whole section is skipped and the chamfer is fitted into the strip)"""
    from section import cut
    P = to_plane(V, fr); u = np.unique(Fr); s0, s1 = P[u, 0].min(), P[u, 0].max()
    if arm is None: arm = float(np.clip(np.ptp(P[u, 1]) / 10, 0.004, 0.012))
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
            # arms shrink (to 4 mm) near a run's ends, so a roll right at a panel edge (beltline into the
            # window) is still seen; otherwise its first 12 mm are invisible and fall into the next band
            for i in range(2, len(C) - 2):
                kk = min(k, i, len(C) - 1 - i)
                p_, q_ = C[i] - C[i - kk], C[i + kk] - C[i]
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
                # a roll that runs out at the panel edge (end vertices carry no turn) owns the edge too
                if t_lo - Rv[0, 0] < 0.003: t_lo = Rv[0, 0] - 0.005
                if Rv[-1, 0] - t_hi < 0.003: t_hi = Rv[-1, 0] + 0.005
                # a SHARP line (turning within 3 mm, not a roll) sits ON a profile vertex: snap to the vertex
                # carrying most of the turn (the 2 mm resampled corner is up to a few mm off, bending both faces)
                if t_hi - t_lo < 0.003:
                    nv_ = np.where((np.abs(Rv[:, 0] - tc) < arm) & (np.sign(ang) == sg))[0]
                    if len(nv_):
                        tc = Rv[nv_[np.argmax(np.abs(ang[nv_]))], 0]; t_lo = min(t_lo, tc); t_hi = max(t_hi, tc)
                hits.append((si, tc, a[i], max(tc - t_lo, 0.0), max(t_hi - tc, 0.0)))
    chains = []
    for si, tt, aa, el, er in sorted(hits):
        best = None
        for ch in chains:
            if 0 < si - ch[-1][0] <= 3 and abs(ch[-1][1] - tt) < 0.012 and np.sign(ch[-1][2]) == np.sign(aa):
                if best is None or abs(ch[-1][1] - tt) < abs(best[-1][1] - tt): best = ch
        if best is not None: best.append((si, tt, aa, el, er))
        else: chains.append([(si, tt, aa, el, er)])
    # a line broken by an opening (the wheel arch cuts the wing's side crease in two): join pieces that carry on
    # across the gap at the same height and turn direction
    chains.sort(key=lambda c: c[0][0]); merged = True
    while merged:
        merged = False
        for a in chains:
            for b in chains:
                if a is b or b[0][0] <= a[-1][0] or np.sign(a[-1][2]) != np.sign(b[0][2]): continue
                if (b[0][0] - a[-1][0]) * ds > 0.8 or len(a) < 3 or len(b) < 3: continue
                if abs(np.median([c[1] for c in a[-3:]]) - np.median([c[1] for c in b[:3]])) < 0.015:
                    a.extend(b); chains.remove(b); merged = True; break
            if merged: break
    if os.environ.get('PF_DEBUG'):
        for ch in sorted(chains, key=len, reverse=True)[:14]:
            print(f'   chain {len(ch):3d} hits s {secs[ch[0][0]]*1e3:6.0f}..{secs[ch[-1][0]]*1e3:6.0f} t {np.median([c[1] for c in ch])*1e3:6.0f} turn {np.median([c[2] for c in ch]):+5.0f}')
    lines = []
    dom = [s0 - 0.1, s1 + 0.1]
    for ch in chains:
        ss = secs[[c[0] for c in ch]]
        if ss.max() - ss.min() < span * (s1 - s0) or len(ch) < 6: continue
        # one control per ~12 sections at most: more lets the line chase facet-corner jumps and swing past
        # its last hit (AE86 beltline: n=10 put the rear end 10 mm off)
        # controls by cross-validation on the line's own hits (every 3rd held out): a curved line (arch lip)
        # gets what it needs, a wobbly one (facet-corner jumps) does not
        tt = np.array([c[1] for c in ch]); cvs = []
        for n_ in range(4, 11):
            e_ = []
            for k_ in range(3):
                tr_ = np.arange(len(ss)) % 3 != k_
                if tr_.sum() < n_ + 2: continue
                g_ = fit_func(ss[tr_], tt[tr_], dom, nmax=n_, tol=0.0)
                e_.append(eval_func(g_, ss[~tr_]) - tt[~tr_])
            if e_: cvs.append((float(np.sqrt(np.mean(np.concatenate(e_) ** 2))), n_))
        nbest = min(n_ for c_, n_ in cvs if c_ <= min(cvs)[0] * 1.1) if cvs else 4
        f = fit_func(ss, tt, dom, nmax=nbest, tol=0.0)
        f.update(s_lo=float(ss.min()), s_hi=float(ss.max()), turn=float(np.mean([c[2] for c in ch])), hits=len(ch),
                 ext_lo=float(np.median([c[3] for c in ch])), ext_hi=float(np.median([c[4] for c in ch])))
        lines.append(f)
    lines = [f for f in lines if f['err'] < 3e-3]          # a chain that does not fit one smooth curve is not a line
    # one line per feature: drop a weaker line that runs within 6 mm of a stronger one
    lines.sort(key=lambda f: -abs(f['turn']) * f['hits'])
    sg = np.linspace(s0, s1, 50); out = []
    for f in lines:
        if all(np.median(np.abs(eval_func(f, sg) - eval_func(g, sg))) > 0.006 for g in out): out.append(f)
    out.sort(key=lambda f: np.mean(eval_func(f, sg)))
    return out


def eval_surface_ext(f, s, t, h=1e-4):
    """height field continued past its domain along its edge slope (no flat clamp -> no kink)"""
    s = np.asarray(s, float); t = np.asarray(t, float)
    a0, a1 = f['ku'][3], f['ku'][-4]; b0, b1 = f['kv'][3], f['kv'][-4]
    sc, tc = np.clip(s, a0 + h, a1 - h), np.clip(t, b0 + h, b1 - h)
    z = eval_surface(f, sc, tc)
    gs = (eval_surface(f, sc + h, tc) - eval_surface(f, sc - h, tc)) / (2 * h)
    gt = (eval_surface(f, sc, tc + h) - eval_surface(f, sc, tc - h)) / (2 * h)
    return z + gs * (s - sc) + gt * (t - tc)


def re_fit(S_mm, nu=8, nv=8):
    """FreeCAD ReverseEngineering.approxSurface on points (plane mm): a general surface (not a height field) for a
    face that wraps. Runs freecadcmd with all temp/user data on D:. Returns (poles mm, ku, kv, distances) or None."""
    import subprocess, tempfile
    tmp = r'D:\ClaudeData\tmp\re_fit'; os.makedirs(tmp, exist_ok=True)
    f_ = os.path.join(tmp, f'pts_{os.getpid()}_{len(S_mm)}.npz'); np.savez(f_, P=S_mm, NU=nu, NV=nv)
    env = dict(os.environ, RE_IN=f_, TEMP=r'D:\ClaudeData\tmp', TMP=r'D:\ClaudeData\tmp', TMPDIR=r'D:\ClaudeData\tmp',
               FREECAD_USER_HOME=r'D:\ClaudeData\FreeCAD', FREECAD_USER_DATA=r'D:\ClaudeData\FreeCAD',
               FREECAD_USER_TEMP=r'D:\ClaudeData\tmp', PYTHONPYCACHEPREFIX=r'D:\ClaudeData\tmp\pycache')
    try:
        subprocess.run([r'D:\FreeCAD\bin\freecadcmd.exe', os.path.join(os.path.dirname(os.path.abspath(__file__)), 're_fit_freecad.py')],
                       env=env, capture_output=True, timeout=600)
        R_ = np.load(f_ + '.out.npz')
        return R_['poles'], R_['ku'], R_['kv'], R_['d']
    except Exception as ex:
        print('   re_fit failed:', ex); return None


def fit_drop(s, tau, D, tmin, ns, nt, lam):
    """D(s, tau) as a tensor cubic B-spline over [s-dom] x [tmin, 0], value and slope forced to 0 at tau = 0"""
    ks = knots(ns, s.min() - 0.02, s.max() + 0.02); kt = knots(nt, tmin, 0.0)
    Bs = basis(s, ks, ns); Bt = basis(tau, kt, nt)[:, :nt - 2]          # last two tau controls = 0
    A = (Bs[:, :, None] * Bt[:, None, :]).reshape(len(s), -1)
    R = np.r_[np.kron(diff2(ns), np.eye(nt - 2)), np.kron(np.eye(ns), diff2(nt)[:, :nt - 2])]
    c = np.linalg.solve(A.T @ A + lam * len(s) * (R.T @ R), A.T @ D)
    C = np.zeros((ns, nt)); C[:, :nt - 2] = c.reshape(ns, nt - 2)
    return dict(ks=ks, kt=kt, ns=ns, nt=nt, C=C)


def eval_drop(d, s, tau):
    """D(s, tau): 0 beyond the boundary (tau > 0), continued linearly past the far edge (no kink there)"""
    tau = np.minimum(tau, 0.0); a = d['kt'][0]; h = 1e-4
    Bs = basis(s, d['ks'], d['ns'])
    ev = lambda t_: np.einsum('ki,ij,kj->k', Bs, d['C'], basis(t_, d['kt'], d['nt']))
    out = ev(np.maximum(tau, a))
    lo = tau < a
    if lo.any():
        slope = (ev(np.full(len(s), a + h)) - ev(np.full(len(s), a))) / h
        out[lo] += slope[lo] * (tau[lo] - a)
    return out


def blend_fillet(P, mk, B, sg, nb, dom_s, t_span):
    """a rolled edge built from its neighbour: h = h_nb(s, t) - D(s, tau), tau = sg * (t - B(s)) <= 0 inside
    the roll, D = 0 with zero slope on the boundary B -> tangent to the neighbour by construction; D is smooth
    along the line with few controls (Kunos gives ~9 vertex rows over 1.3 m). Returned as one tensor B-spline
    in plane coordinates (the composite is evaluated densely and approximated to < 0.03 mm)."""
    S = P[mk]; tau = sg * (S[:, 1] - eval_func(B, S[:, 0]))
    D = eval_surface_ext(nb, S[:, 0], S[:, 1]) - S[:, 2]
    # measure across the roll NORMALISED between its far edge (-1) and the boundary (0): the far edge (window
    # edge) is a real feature on every vertex row, so the rows line up; plain distance from the boundary line
    # blurs them by the line's error (1-2 mm) and the profile comes out too stiff
    sb = np.floor(S[:, 0] / 0.04); far = []
    for k in np.unique(sb):
        i = np.where(sb == k)[0]; far.append(i[np.argmin(tau[i])])
    far = np.array(far)
    Ef = fit_func(S[far, 0], tau[far], [S[:, 0].min() - 0.1, S[:, 0].max() + 0.1], tol=0.5e-3, nmax=int(np.clip(len(far) // 4, 4, 6)))
    width = lambda s_: np.maximum(-eval_func(Ef, s_), 0.003)
    tau = tau / width(S[:, 0])
    tmin = tau.min() - 0.05
    fold = (np.floor(S[:, 0] / 0.1) % 5).astype(int)                    # hold out whole vertex rows
    cands = []
    for ns in (4, 5, 6, 7):
        for nt in range(4, 15):                 # a sharp lip at a panel edge needs ~9 across
            for lam in (1e-7, 1e-5, 1e-3):
                e = []
                for k in range(5):
                    tr = fold != k
                    if (~tr).sum() == 0 or tr.sum() < ns * nt: continue
                    d = fit_drop(S[tr, 0], tau[tr], D[tr], tmin, ns, nt, lam)
                    e.append(eval_drop(d, S[~tr, 0], tau[~tr]) - D[~tr])
                if e: cands.append((float(np.sqrt(np.mean(np.concatenate(e) ** 2))), ns * nt, ns, nt, lam))
    cvb = min(c[0] for c in cands)
    best = min((c for c in cands if c[0] <= cvb * 1.05), key=lambda c: (c[1], -c[4]))
    _, _, ns, nt, lam = best
    d = fit_drop(S[:, 0], tau, D, tmin, ns, nt, lam)
    r = np.abs(eval_drop(d, S[:, 0], tau) - D)
    # composite surface -> one general 3D B-spline with its own directions: s along the line, rho across the
    # roll (rho = -1 far edge, 0 boundary, > 0 into the neighbour for the band-cut margin). A plain height-field
    # grid over the door plane loses 0.4-0.8 mm because the lip runs diagonally across it.
    s0, s1 = dom_s; r0, r1 = tmin - 0.2, 0.6                 # a margin past its band edges (trims only remove)
    sg_ = np.linspace(s0, s1, 240); rg = np.linspace(r0, r1, 120)
    SS, RR = np.meshgrid(sg_, rg, indexing='ij')
    TT = eval_func(B, SS.ravel()) + sg * RR.ravel() * width(SS.ravel())
    HH = eval_surface_ext(nb, SS.ravel(), TT) - eval_drop(d, SS.ravel(), RR.ravel())
    X = np.c_[SS.ravel(), TT, HH]
    for nu, nv in ((10, 12), (14, 16), (18, 20), (24, 26), (30, 32)):
        ku = knots(nu, s0, s1); kv = knots(nv, r0, r1)
        A = (basis(SS.ravel(), ku, nu)[:, :, None] * basis(RR.ravel(), kv, nv)[:, None, :]).reshape(len(X), -1)
        Pl = np.linalg.lstsq(A, X, rcond=None)[0]
        ea = np.linalg.norm(A @ Pl - X, axis=1).max()
        if ea < 3e-5: break
    if os.environ.get('PF_DEBUG'):
        er = np.linalg.norm(A @ Pl - X, axis=1); i = np.argmax(er)
        print('  approx worst at s %.0f rho %.2f (tmin %.2f): %.3f mm; p95 %.3f; rho-band worst:' % (SS.ravel()[i]*1e3, RR.ravel()[i], tmin, er[i]*1e3, np.percentile(er, 95)*1e3),
              [(round(a_, 2), round(er[(RR.ravel() >= a_) & (RR.ravel() < a_ + 0.2)].max()*1e3, 3)) for a_ in np.arange(r0, r1, 0.2)])
        print('  s-band worst:', [(int(a_*1e3), round(er[(SS.ravel() >= a_) & (SS.ravel() < a_ + 0.1)].max()*1e3, 3)) for a_ in np.arange(s0, s1, 0.1)])
    f = dict(nu=nu, nv=nv, ku=ku, kv=kv, poles3=Pl.reshape(nu, nv, 3), lam=lam)
    return f, r, dict(ns=ns, nt=nt, cv=best[0], approx=float(ea), nu=nu, nv=nv)


def fit_bands(name, V, Fr, Nv, overlap=0.002, keep=None, Fr_lines=None, cut_poly=None, fr=None, Fr_outline=None, area_poly=None, extra_lines=()):
    """a region split into bands by its character lines; each band one surface, trimmed exactly on the lines.
    keep: vertices usable as data (False = belongs to another surface, e.g. an arch lip); Fr_lines: triangles to
    look for character lines in; cut_poly: area (plane mm, region frame) cut out of every band (the lip)"""
    u = np.unique(Fr)
    if fr is None: fr = frame_of(V[u], Nv[u])
    base = fit_panel(name, V, Fr if Fr_outline is None else Fr_outline, Nv, verbose=False, fr=fr, outline_only=True)
    if cut_poly is not None: base = dict(base, cut_poly=cut_poly, cut_frame=[x.tolist() for x in fr])
    if area_poly is not None: base = dict(base, band_poly=area_poly)     # a sub-panel: kept to its own area
    lines = feature_lines(V, Fr if Fr_lines is None else Fr_lines, fr)
    P = to_plane(V[u], fr)
    if extra_lines:                                  # steps the section scan cannot see (a ledge seen edge-on)
        sg_ = np.linspace(P[:, 0].min(), P[:, 0].max(), 30)
        lines = sorted(list(lines) + list(extra_lines), key=lambda L_: float(np.mean(eval_func(L_, sg_))))
    # a strong line (rolled edge) gets its own narrow fillet band: two bounds at its measured extent
    cut_lines = []
    for L in lines:
        if abs(L['turn']) >= 25 and L['ext_lo'] > 0.003 and L['ext_hi'] > 0.003:
            for off in (-L['ext_lo'], L['ext_hi']):
                M = dict(L); M['c'] = L['c'] + off; M['pair'] = id(L); cut_lines.append(M)
        else:
            cut_lines.append(L)
    bounds = [None] + cut_lines + [None]
    out, fits, cores, deferred = [], {}, {}, []; pieces_done = []
    for b in range(len(bounds) - 1):
        lo, hi = bounds[b], bounds[b + 1]
        m = np.ones(len(P), bool) if keep is None else keep[u].copy()
        # overlap across a line: 2 mm, but tight on a sharp line placed to < 0.5 mm, or a vertex of the face
        # beyond a sharp corner (1 mm away) is fitted into this face and bends it
        # (a STEP - a ledge seen edge-on - has both edges on its line at different depths: neither face takes them)
        ov = lambda L: -1.5e-3 if L.get('step') else (overlap if (L['ext_lo'] + L['ext_hi'] > 0.003 or L['err'] > 0.5e-3) else max(0.3e-3, 1.5 * L['err']))
        if lo is not None: m &= P[:, 1] > eval_func(lo, P[:, 0]) - ov(lo)
        if hi is not None: m &= P[:, 1] < eval_func(hi, P[:, 0]) + ov(hi)
        # across a SOFT bound (roll edge) the surface is smooth, so the band also takes the next vertex row
        # beyond it: Kunos rows can be 25 mm apart, and a band edge with no data under it swings wildly
        inb = np.zeros(len(V), bool); inb[u[m]] = True
        ring = np.isin(u, np.unique(Fr[inb[Fr].any(1)]))
        for L, sg in ((lo, -1), (hi, 1)):
            if L is not None:                                 # at most 50 mm beyond (Kunos triangles reach 200 mm)
                ring &= (P[:, 1] - eval_func(L, P[:, 0])) * sg < (ov(L) if ov(L) < overlap else 0.05)
        core = m.copy()
        tb = np.c_[[eval_func(L, P[:, 0]) for L in cut_lines]].T if cut_lines else np.zeros((len(P), 0))
        for j, L in enumerate(cut_lines):                     # never across any sharp line of the region
            if ov(L) < overlap:
                side = np.sign(P[:, 1] - tb[:, j]); cs = np.sign(np.median(side[core])) if core.any() else 1
                ring &= (side == cs) | (np.abs(P[:, 1] - tb[:, j]) < ov(L))
        if keep is not None: ring &= keep[u]               # never borrow vertices that belong to another surface (lip)
        m |= ring
        mm = lambda a: (np.asarray(a) * 1000).tolist()
        line = lambda L: None if L is None else dict(kv=mm(L['kv']), g=mm(L['g']), c=mm(L['c']))
        # a rolled edge (fillet band) is one surface only along its line; where the line stops (window
        # corners: the roll turns into the pillars, and folds over the door plane) each end is its own
        # corner patch over its own plane - as a modeller builds a corner blend
        is_fillet = lo is not None and hi is not None and lo.get('pair') is not None and lo.get('pair') == hi.get('pair')
        if BLEND and is_fillet:
            deferred.append((b, lo, hi, core)); continue
        pieces = [('', m, fr, None)]
        if CORNERS and lo is not None and hi is not None and lo.get('pair') is not None and lo.get('pair') == hi.get('pair'):
            sl, sh = lo['s_lo'], lo['s_hi']
            pieces = [('', m & (P[:, 0] >= sl) & (P[:, 0] <= sh), fr, [sl, sh]),
                      ('c0', m & (P[:, 0] < sl), None, [-10.0, sl]), ('c1', m & (P[:, 0] > sh), None, [sh, 10.0])]
        # a band facing far from the panel's plane (wing top vs wing side: ~70 deg) is not a height field over
        # it: fit it over its own plane (trimmed by 3D prisms like a patch)
        # a band split by an opening (the lowest wing band: in front of and behind the wheel arch) is one
        # surface per connected piece, each over its own stretch of the car (cut halfway across the gap)
        if pieces[0][3] is None:
            inb_ = np.zeros(len(V), bool); inb_[u[core]] = True
            Tin = Fr[inb_[Fr].all(1)]
            if len(Tin):
                comps_, _ = components(V, Tin)
                big = [np.isin(u, np.unique(c_)) for c_ in comps_ if len(np.unique(c_)) >= 25]
                if len(big) > 1:
                    big.sort(key=lambda k_: P[k_, 0].min())
                    rng_ = [(P[k_, 0].min(), P[k_, 0].max()) for k_ in big]
                    if all(rng_[i][1] < rng_[i + 1][0] for i in range(len(rng_) - 1)):      # apart along the car
                        cuts = [-10.0] + [(rng_[i][1] + rng_[i + 1][0]) / 2 for i in range(len(rng_) - 1)] + [10.0]
                        pieces = [(f'p{i}', m & (P[:, 0] > cuts[i]) & (P[:, 0] <= cuts[i + 1]), fr, [cuts[i], cuts[i + 1]]) for i in range(len(big))]
        cosw = (lambda nn: nn @ fr[3] / np.linalg.norm(nn))(Nv[u[m]].mean(0)) if m.any() else 1.0
        if cosw < np.cos(np.radians(35)) and pieces[0][3] is None:
            pieces = [('', m, None, None)]
        for tag, mk, frp, band_s in pieces:
            if mk.sum() < 12: continue
            own = frp is None
            if own: frp = frame_of(V[u[mk]], Nv[u[mk]])
            S = to_plane(V[u[mk]], frp); iscore = core[mk]
            pad = 0.02
            dom = [S[:, 0].min() - pad, S[:, 0].max() + pad, S[:, 1].min() - pad, S[:, 1].max() + pad]
            if not own and band_s is None:
                # the surface must reach every part of its band (line to line, panel edge to panel edge), not just
                # where it has data: trimming only removes surface (a crescent gap above the AE86 arch). Fairing
                # keeps it smooth where there is no data.
                Pall_ = to_plane(V[u], fr); sg_ = np.linspace(Pall_[:, 0].min(), Pall_[:, 0].max(), 40)
                t_lo_ = eval_func(lo, sg_).min() if lo is not None else Pall_[:, 1].min()
                t_hi_ = eval_func(hi, sg_).max() if hi is not None else Pall_[:, 1].max()
                dom = [min(dom[0], Pall_[:, 0].min() - pad), max(dom[1], Pall_[:, 0].max() + pad),
                       min(dom[2], max(t_lo_, Pall_[:, 1].min()) - pad), max(dom[3], min(t_hi_, Pall_[:, 1].max()) + pad)]
            f, r, cv = select_fit(S, dom)
            re_ = None
            if not own and np.percentile(r[iscore], 95) > 3e-3 and len(S) >= 30 and os.environ.get('PF_RE', '1') == '1':
                # the face wraps too much for a height field over the panel plane: FreeCAD's reverse-engineering fit
                re_ = re_fit(S * 1000, nu=min(10, max(5, f['nu'] + 2)), nv=min(10, max(5, f['nv'] + 2)))
                if re_ is not None and np.percentile(re_[3][iscore], 95) < 0.8 * np.percentile(r[iscore], 95) * 1000:
                    print(f"   {name}:b{b}{tag}: height field p95 {np.percentile(r[iscore], 95)*1000:.2f} mm -> FreeCAD approxSurface p95 {np.percentile(re_[3][iscore], 95):.2f} mm (kept)")
                else:
                    re_ = None
            e = dict(base)                    # outline wires stay in the region's frame (own-plane patches are
                                              # trimmed by a prism of them; projected onto a tilted plane they fold)
            e.update(name=f'{name}:b{b}{tag}', dom=mm(dom), nu=f['nu'], nv=f['nv'], ku=mm(f['ku']), kv=mm(f['kv']),
                     poles=mm(np.stack(list(np.meshgrid(f['gu'], f['gv'], indexing='ij')) + [f['H']], -1)),
                     band_lo=line(lo), band_hi=line(hi), fit_p95_mm=float(np.percentile(r[iscore], 95) * 1000))
            if re_ is not None:
                e.update(nu=re_[0].shape[0], nv=re_[0].shape[1], ku=re_[1].tolist(), kv=re_[2].tolist(), poles=re_[0].tolist(),
                         general=True, own_plane=True, line_frame=[x.tolist() for x in fr], fit_p95_mm=float(np.percentile(re_[3][iscore], 95)))
            if own:
                e['frame'] = [x.tolist() for x in frp]; e['own_plane'] = True
                # its outline in ITS plane: the panel outline drawn in the region plane collapses for a face that
                # faces away (wing top seen from the side). Boundary of the band's own triangles; points on the
                # panel's real edge stay put, the others (along its character lines) go out 15 mm, where the
                # line prism makes the exact cut.
                inb2 = np.zeros(len(V), bool); inb2[u[mk]] = True
                # every triangle TOUCHING the face (Kunos's long triangles cross face boundaries; taking only those
                # wholly inside left crescent-shaped holes beside the arch). Other faces' areas are cut away anyway.
                Tb = Fr[inb2[Fr].any(1)]
                if len(Tb) > 4:
                    _, wid2 = components(V, Tb); lps = boundary_loops(Tb, wid2); rep2 = {w_: i_ for i_, w_ in enumerate(wid2)}
                    _, widR = components(V, Fr); edgeR = set(); [edgeR.update(l_) for l_ in boundary_loops(Fr, widR)]
                    repR = {i_: w_ for i_, w_ in enumerate(widR)}
                    Lb = max(lps, key=len); vid = [rep2[w_] for w_ in Lb]
                    Q2 = to_plane(V[vid], frp)[:, :2]
                    on_edge = np.array([repR[v_] in edgeR for v_ in vid])
                    cen = Q2.mean(0); out_ = Q2 - cen; out_ /= np.maximum(np.linalg.norm(out_, axis=1), 1e-9)[:, None]
                    Q2 = Q2 + (~on_edge)[:, None] * out_ * 0.015
                    e['own_poly'] = mm(Q2)
            if own or band_s is not None:
                e['line_frame'] = [x.tolist() for x in fr]          # the band lines live in the region's frame
                if band_s is not None: e['band_s'] = mm(band_s)
            out.append(e)
            if not tag and not own: fits[b] = f; cores[b] = core
            if not own and re_ is None: pieces_done.append(dict(f=f, lo=lo, hi=hi, band_s=band_s, S=S, core=iscore, dom=dom, idx=len(out) - 1, name=e['name']))   # for line matching + wrap seams
            print(f"{e['name']:28s} verts {len(S):4d} control {f['nu']}x{f['nv']} lam {f['lam']:g}  cv {cv*1000:.2f} mm  fit p95 {np.percentile(r[iscore],95)*1000:.2f} max {r[iscore].max()*1000:.2f} mm (band's own vertices)" + ('  (own plane)' if own else ''))
    # bands meet ON their character lines (G0): Kunos data near a line is sparse, so each band extrapolates to it on its
    # own and they can disagree by 1-3 mm (thin dark lines along the rear quarter's lines). Average both bands'
    # heights along each shared line and refit both with that line as heavily weighted data - two surfaces pinned to one
    # edge curve. Steps (ledges) and roll bounds are left alone (a roll is built from its neighbour).
    if os.environ.get('PF_LINEMATCH', '1') == '1':
        tgt_ = {}
        s_all = (P[:, 0].min(), P[:, 0].max())
        for L in bounds[1:-1]:
            if L.get('step') or L.get('pair') is not None: continue
            below = [pc for pc in pieces_done if pc['hi'] is L]; above = [pc for pc in pieces_done if pc['lo'] is L]
            for pa in below:
                for pb in above:
                    ra = pa['band_s'] or s_all; rb = pb['band_s'] or s_all
                    s0_, s1_ = max(ra[0], rb[0], s_all[0]), min(ra[1], rb[1], s_all[1])
                    if s1_ - s0_ < 0.03: continue
                    s0_, s1_ = max(s0_, L['s_lo'] - 0.01), min(s1_, L['s_hi'] + 0.01)          # where the line really runs
                    if s1_ - s0_ < 0.03: continue
                    sg = np.arange(s0_ + 0.005, s1_ - 0.004, 0.01); tg = eval_func(L, sg)
                    from scipy.spatial import cKDTree
                    ok_ = (cKDTree(pa['S'][:, :2]).query(np.c_[sg, tg])[0] < 0.04) & (cKDTree(pb['S'][:, :2]).query(np.c_[sg, tg])[0] < 0.04)
                    sg, tg = sg[ok_], tg[ok_]                                                     # both bands have data near
                    if len(sg) < 3: continue
                    ha = eval_surface_ext(pa['f'], sg, tg); hb = eval_surface_ext(pb['f'], sg, tg); hm = 0.5 * (ha + hb)
                    print(f"   {pa['name']} | {pb['name']}: on their line {np.median(np.abs(ha - hb))*1e3:.2f} / {np.abs(ha - hb).max()*1e3:.2f} mm apart (median / max) -> pinned")
                    for pc in (pa, pb): tgt_.setdefault(id(pc), (pc, []))[1].append(np.c_[sg, tg, hm])
        for pc, lst in tgt_.values():
            T_ = np.concatenate(lst); S_ = pc['S']; f_ = pc['f']
            wv = np.r_[np.ones(len(S_)), np.full(len(T_), 3.0 * len(S_) / len(T_))]
            Sc_ = S_[pc['core']]                                   # judged on the band's own (core) vertices
            r0_ = np.percentile(np.abs(eval_surface(f_, Sc_[:, 0], Sc_[:, 1]) - Sc_[:, 2]), 95); lim_ = max(1.25 * r0_, r0_ + 0.3e-3)
            best_ = None
            for du_, dv_ in ((0, 0), (2, 0), (0, 2), (2, 2), (4, 2), (2, 4), (4, 4)):   # more freedom if pinning costs accuracy
                if (f_['nu'] + du_) * (f_['nv'] + dv_) > max(20, 0.6 * len(S_)) and (du_ or dv_): continue
                f2 = fit_surface(np.r_[S_, T_], pc['dom'], f_['nu'] + du_, f_['nv'] + dv_, f_['lam'], w=wv)
                q_ = np.percentile(np.abs(eval_surface(f2, Sc_[:, 0], Sc_[:, 1]) - Sc_[:, 2]), 95)
                if best_ is None or q_ < best_[0]: best_ = (q_, f2)
                if q_ <= lim_: best_ = (q_, f2); break
            lam_ = f_['lam']; f_.update(best_[1]); f_['lam'] = lam_
            out[pc['idx']].update(nu=f_['nu'], nv=f_['nv'], ku=mm(f_['ku']), kv=mm(f_['kv']))
            out[pc['idx']]['poles'] = mm(np.stack(list(np.meshgrid(f_['gu'], f_['gv'], indexing='ij')) + [f_['H']], -1))
            r_ = np.abs(eval_surface(f_, Sc_[:, 0], Sc_[:, 1]) - Sc_[:, 2])
            out[pc['idx']]['fit_p95_mm'] = float(np.percentile(r_, 95) * 1000)
            print(f"   {pc['name']}: refitted on its lines ({f_['nu']}x{f_['nv']}), own vertices p95 {r0_*1e3:.2f} -> {np.percentile(r_, 95)*1e3:.2f} mm, on line {np.abs(eval_surface_ext(f_, T_[:, 0], T_[:, 1]) - T_[:, 2]).max()*1e3:.2f} mm max")
    # rolled edges: built from the neighbour that really borders them (data within 30 mm of the boundary
    # along most of the line); the other side may be a free panel edge (beltline into the window)
    mm = lambda a: (np.asarray(a) * 1000).tolist()
    line = lambda L: None if L is None else dict(kv=mm(L['kv']), g=mm(L['g']), c=mm(L['c']))
    for b, lo, hi, core in deferred:
        opts = []
        for nb_i, B, sg in ((b + 1, hi, 1), (b - 1, lo, -1)):
            if nb_i not in fits: continue
            dd = sg * (P[cores[nb_i], 1] - eval_func(B, P[cores[nb_i], 0]))
            near = (dd > 0) & (dd < 0.03)
            cov = np.ptp(P[cores[nb_i]][near, 0]) if near.sum() > 3 else 0.0
            opts.append((cov, nb_i, B, sg))
        if not opts:                                      # nothing to build it from: a plain surface over its own data
            print(f'{name}:b{b} roll: no neighbour - fitted plainly')
            S = P[core]
            if len(S) >= 12:
                dom = [S[:, 0].min() - 0.02, S[:, 0].max() + 0.02, S[:, 1].min() - 0.02, S[:, 1].max() + 0.02]
                f, r, cv = select_fit(S, dom); e = dict(base)
                e.update(name=f'{name}:b{b}', dom=mm(dom), nu=f['nu'], nv=f['nv'], ku=mm(f['ku']), kv=mm(f['kv']),
                         poles=mm(np.stack(list(np.meshgrid(f['gu'], f['gv'], indexing='ij')) + [f['H']], -1)),
                         band_lo=line(lo), band_hi=line(hi), fit_p95_mm=float(np.percentile(r, 95) * 1000))
                out.append(e)
            continue
        cov, nb_i, B, sg = max(opts, key=lambda o: o[0])
        Sc = P[core]; Bs = eval_func(B, np.linspace(Sc[:, 0].min(), Sc[:, 0].max(), 50))
        # its band's full length inside its area (a roll in the rear sub-panel runs from the rear edge to the arch,
        # beyond its last vertices): trims only remove surface. Within the panel, not the whole shell.
        dom_s = [P[core, 0].min() - 0.05, P[core, 0].max() + 0.05]
        if area_poly is not None:
            ap_ = np.array(area_poly) / 1000; s_in = P[:, 0][(P[:, 0] >= ap_[:, 0].min()) & (P[:, 0] <= ap_[:, 0].max())]
            if len(s_in): dom_s = [min(dom_s[0], s_in.min() - 0.02), max(dom_s[1], s_in.max() + 0.02)]
        t_span = [min(Sc[:, 1].min(), Bs.min()) - 0.008, max(Sc[:, 1].max(), Bs.max()) + 0.012]
        f, r, info = blend_fillet(P, core, B, sg, fits[nb_i], dom_s, t_span)
        # keep the blend only if it really fits better than a plain surface over the roll's own data (including
        # what is lost turning it into a B-spline); a short roll with few vertices can be better plain
        Sp = P[core]
        domp = [min(Sp[:, 0].min(), dom_s[0]) - 0.02, max(Sp[:, 0].max(), dom_s[1]) + 0.02, Sp[:, 1].min() - 0.02, Sp[:, 1].max() + 0.02]
        fp, rp, cvp = select_fit(Sp, domp)
        if np.percentile(rp, 95) < np.percentile(r, 95) + info['approx']:
            e = dict(base)
            e.update(name=f'{name}:b{b}', dom=mm(domp), nu=fp['nu'], nv=fp['nv'], ku=mm(fp['ku']), kv=mm(fp['kv']),
                     poles=mm(np.stack(list(np.meshgrid(fp['gu'], fp['gv'], indexing='ij')) + [fp['H']], -1)),
                     band_lo=line(lo), band_hi=line(hi), fit_p95_mm=float(np.percentile(rp, 95) * 1000))
            if area_poly is not None: e['own_plane'] = True; e['line_frame'] = [x.tolist() for x in fr]
            out.append(e)
            print(f"{e['name']:28s} verts {core.sum():4d} roll kept PLAIN ({fp['nu']}x{fp['nv']}, p95 {np.percentile(rp,95)*1000:.2f} mm) - the blend was "
                  f"{np.percentile(r,95)*1000:.2f} + {info['approx']*1000:.2f} mm")
            continue
        e = dict(base)
        # general surface (not a height field): trimmed by 3D prisms of the outline and the band, like a patch
        e.update(name=f'{name}:b{b}', dom=mm([*dom_s, *t_span]), nu=f['nu'], nv=f['nv'], ku=mm(f['ku']), kv=mm(f['kv']),
                 poles=mm(f['poles3']), general=True, own_plane=True, line_frame=[x.tolist() for x in fr],
                 band_lo=line(lo), band_hi=line(hi), fit_p95_mm=float(np.percentile(r, 95) * 1000), blend_of=f'{name}:b{nb_i}')
        out.append(e)
        print(f"{e['name']:28s} verts {core.sum():4d} ROLL from b{nb_i} (tangent): drop {info['ns']}x{info['nt']} cv {info['cv']*1000:.2f} mm"
              f"  fit p95 {np.percentile(r, 95)*1000:.2f} max {r.max()*1000:.2f} mm  as {info['nu']}x{info['nv']} B-spline (approx {info['approx']*1000:.3f} mm)")
    print(f"{name}: {len(lines)} character lines: " + ', '.join(f"turn {L['turn']:+.0f} deg ({L['ext_lo']*1000:.0f}/{L['ext_hi']*1000:.0f} mm), {L['hits']} hits, fit {L['err']*1000:.2f} mm" for L in lines))
    fit_bands.last = dict(fits=fits, bounds=bounds, pieces=pieces_done, fr=fr)      # for a feature built against these faces (arch lip)
    return out


# ---------- wheel arch: lip as its own strip round the opening, the side surface trimmed around it ----------
def circle2(Q):
    A = np.c_[2 * Q[:, 0], 2 * Q[:, 1], np.ones(len(Q))]; b = (Q ** 2).sum(1)
    cx, cy, k = np.linalg.lstsq(A, b, rcond=None)[0]; R = np.sqrt(k + cx ** 2 + cy ** 2)
    return np.array([cx, cy]), R, np.abs(np.linalg.norm(Q - [cx, cy], axis=1) - R)


def find_arch(L2, step=0.01, win=0.40, rmin=0.25, rmax=0.55, tol=0.012):
    """the wheel opening on a panel outline (closed 2D loop, plane metres): the longest run of the outline that
    is a circular arc of wheel-arch size (radius 250-550 mm) - a notch the wheel bites out of the panel"""
    Q = resample_closed(L2, step); n = len(Q); k = int(win / step / 2)
    ok = np.zeros(n, bool)
    for i in range(n):
        idx = np.arange(i - k, i + k + 1) % n; c, R, r = circle2(Q[idx])
        ok[i] = rmin < R < rmax and r.max() < tol
    if not ok.any(): return None
    best, cur, start = (0, 0), 0, 0
    for i in range(2 * n):
        if ok[i % n]:
            if cur == 0: start = i
            cur += 1
            if cur > best[0]: best = (cur, start)
        else: cur = 0
    run = list(np.arange(best[1] - k, best[1] + min(best[0], n) + k) % n)
    # trim the ends back while they leave the arch's circle (the window reaches past the arch into the panel edge)
    while len(run) > 2 * k:
        c, R, r = circle2(Q[run])
        if r.max() < 0.006: break
        if r[0] >= r[-1]: run.pop(0)
        else: run.pop()
    seg = Q[run]; c, R, r = circle2(seg)
    return dict(seg=seg, c=c, R=R, dev=float(r.max()), Q=Q, run=run)


def ledge_lines(V, Fr, Nv, others, fr, min_area=4e-4):
    """narrow faces seen edge-on from the panel plane (a ledge or step between a proud strip and the body):
    each becomes a sharp cut line t = g(s) through its middle - the panel's surface jumps there"""
    out = []
    u = np.unique(Fr); P = to_plane(V[u], fr)
    for Fo in others:
        T_ = V[Fo]; n_ = np.cross(T_[:, 1] - T_[:, 0], T_[:, 2] - T_[:, 0]); A_ = np.linalg.norm(n_, axis=1)
        if A_.sum() / 2 < min_area: continue
        n_ /= A_[:, None]
        if np.median(np.abs(n_ @ fr[3])) > 0.35: continue          # not edge-on
        Q_ = to_plane(V[np.unique(Fo)], fr)
        if not ((Q_[:, 0] > P[:, 0].min()) & (Q_[:, 0] < P[:, 0].max()) & (Q_[:, 1] > P[:, 1].min()) & (Q_[:, 1] < P[:, 1].max())).all(): continue
        if np.ptp(Q_[:, 1]) > 0.02 * max(1.0, np.ptp(Q_[:, 0]) / 0.3): continue   # a narrow strip along s
        dom_ = [P[:, 0].min() - 0.1, P[:, 0].max() + 0.1]
        g_ = fit_func(Q_[:, 0], Q_[:, 1], dom_, tol=0.5e-3, nmax=4)
        g_.update(s_lo=float(Q_[:, 0].min()), s_hi=float(Q_[:, 0].max()), turn=90.0, hits=len(Q_), ext_lo=0.0, ext_hi=0.0, err=0.3e-3, step=True)
        out.append(g_)
        print(f'   ledge face ({len(Fo)} tris, {A_.sum()/2*1e4:.0f} cm2) -> cut line at t {np.mean(Q_[:, 1])*1e3:.0f} mm, s {Q_[:,0].min()*1e3:.0f}..{Q_[:,0].max()*1e3:.0f} mm')
    return out


def fit_arch_panel(name, V, Fr, Nv, others=()):
    """a panel with a wheel arch (front wing): (1) find the opening on the outline; (2) the side surface around
    the arch, extended across it ('main surface first'); (3) lip width = where the real surface leaves that side
    surface; (4) the lip as a strip in arch coordinates (arc length round the arch x distance out from the real
    edge) = side surface minus a drop profile, tangent to the side at the lip's outer edge; (5) the rest of the
    panel by the band method, with the lip area cut out of it"""
    u = np.unique(Fr); fr = frame_of(V[u], Nv[u]); P = to_plane(V[u], fr)
    _, wid = components(V, Fr); loops = boundary_loops(Fr, wid); rep = {w: i for i, w in enumerate(wid)}
    L2 = to_plane(V[[rep[w] for w in max(loops, key=len)]], fr)[:, :2]
    A = find_arch(L2)
    if A is None:
        print(f'{name}: no wheel arch found; plain bands'); return fit_bands(name, V, Fr, Nv)
    c, R, seg = A['c'], A['R'], A['seg']
    # the lip follows the WHOLE opening edge, corner to corner - not only its circular part: on the AE86 the flare
    # carries on down the straight rear edge to the bottom of the wing, 30 mm proud of the body behind it.
    # Coordinates (research: 'rail' surfaces): a = arc length along the edge, d = distance in from it.
    Q, run = A['Q'], list(A['run']); n_ = len(Q)
    def turn(i, k=3):
        p_, q_ = Q[i % n_] - Q[(i - k) % n_], Q[(i + k) % n_] - Q[i % n_]
        return np.degrees(np.arccos(np.clip(p_ @ q_ / (np.linalg.norm(p_) * np.linalg.norm(q_) + 1e-12), -1, 1)))
    i0 = run[0]; i1 = run[0] + len(run) - 1                  # unwrapped (the run may pass the loop's start)
    for _ in range(80):
        if turn(i0 - 1) > 30: break
        i0 -= 1
    for _ in range(80):
        if turn(i1 + 1) > 30: break
        i1 += 1
    EQ = Q[np.arange(i0, i1 + 1) % n_]
    al = np.r_[0, np.cumsum(np.linalg.norm(np.diff(EQ, axis=0), axis=1))]; Alen = al[-1]
    fs_ = fit_func(al, EQ[:, 0], [-0.2, Alen + 0.2], tol=0.5e-3, nmax=14)
    ft_ = fit_func(al, EQ[:, 1], [-0.2, Alen + 0.2], tol=0.5e-3, nmax=14)
    def E(a_):
        a_ = np.asarray(a_, float); return np.c_[eval_func(fs_, a_), eval_func(ft_, a_)]
    def En(a_):                                              # unit normal into the panel
        a_ = np.asarray(a_, float); h_ = 1e-4; tg_ = (E(a_ + h_) - E(a_ - h_)) / (2 * h_)
        nn_ = np.c_[-tg_[:, 1], tg_[:, 0]]; return sgn_ * nn_ / np.linalg.norm(nn_, axis=1)[:, None]
    sgn_ = 1.0
    ad = np.linspace(-0.05, Alen + 0.05, 4000); Ed = E(ad)
    try:
        from scipy.spatial import cKDTree
        nearest = cKDTree(Ed).query(P[:, :2])[1]
    except ImportError:
        nearest = np.concatenate([np.argmin(((P[i_:i_ + 500, None, :2] - Ed[None]) ** 2).sum(2), axis=1) for i_ in range(0, len(P), 500)])
    apos = ad[nearest]; d = ((P[:, :2] - Ed[nearest]) * En(apos)).sum(1)
    if np.median(d[np.abs(d) < 0.15]) < 0: sgn_ = -1.0; d = -d          # panel material on the positive side
    # the lip runs only where there IS a flare: step along the edge; at each station the profile across the edge
    # (height vs distance in, 0-100 mm) is either flat (a plain panel - the recessed panel in front of the AE86
    # arch) or bent (the flare). The rail is cut back to the bent stretch round the arch.
    st_ = np.arange(0.0, Alen, 0.03); bent = np.zeros(len(st_), bool)
    for k_, a_ in enumerate(st_):
        mk_ = (np.abs(apos - a_) < 0.025) & (d > 0) & (d < 0.10)
        if mk_.sum() < 4: continue
        A_ = np.c_[np.ones(mk_.sum()), d[mk_]]; cf_ = np.linalg.lstsq(A_, P[mk_, 2], rcond=None)[0]
        bent[k_] = np.abs(A_ @ cf_ - P[mk_, 2]).max() > 0.003
    mid_ = st_[np.argmin(np.abs(st_ - 0.5 * (al[run[0] - i0] + al[min(run[0] + len(run) - 1 - i0, len(al) - 1)])))]
    k0 = k1 = int(np.argmin(np.abs(st_ - mid_)))
    while k0 > 0 and (bent[k0 - 1] or (k0 > 1 and bent[k0 - 2])): k0 -= 1
    while k1 < len(st_) - 1 and (bent[k1 + 1] or (k1 < len(st_) - 2 and bent[k1 + 2])): k1 += 1
    a_lo, a_hi = max(st_[k0] - 0.03, 0.0), min(st_[k1] + 0.03, Alen)
    if a_lo > 0.03 or a_hi < Alen - 0.03:
        print(f'{name}: flare only along {a_lo*1e3:.0f}..{a_hi*1e3:.0f} mm of the {Alen*1e3:.0f} mm edge - the lip stops where the surface is flat')
    sector = (apos > a_lo - 0.01) & (apos < a_hi + 0.01)
    if os.environ.get('PF_DEBUG'):
        W_ = V[u]
        for yz in ((0.638, 1.253), (0.285, 0.810), (0.616, 1.197)):
            i_ = np.argmin(np.hypot(W_[:, 1] - yz[0], W_[:, 2] - yz[1]))
            print(f'  vertex y {W_[i_,1]:.3f} z {W_[i_,2]:.3f}: along rail {apos[i_]*1e3:.0f} mm, in from edge {d[i_]*1e3:.0f} mm')
        print(f'  rail ends at y,z: start {np.round(from_plane(np.c_[E([0.0]), [[0]]], fr)[0, 1:], 3)} end {np.round(from_plane(np.c_[E([Alen]), [[0]]], fr)[0, 1:], 3)}')
    th = apos; R = 1.0; ts = np.array([0.0, Alen])                       # a = arc length along the edge
    print(f'{name}: wheel arch radius {A["R"]*1e3:.0f} mm (edge within {A["dev"]*1e3:.1f} mm of a circle); lip rail {Alen*1e3:.0f} mm along the opening edge, corner to corner')

    def side_fit(d0, d1):
        mk = sector & (d > d0) & (d < d1)
        S = P[mk]; dom = [S[:, 0].min() - .05, S[:, 0].max() + .05, S[:, 1].min() - .05, S[:, 1].max() + .05]
        return select_fit(S, dom)[0]
    # side surface over a narrow ring just outside any plausible lip (a wide ring crosses other features:
    # the AE86 side crease runs 100 mm above the arch)
    f0 = side_fit(0.09, 0.17)
    res = np.abs(eval_surface_ext(f0, P[:, 0], P[:, 1]) - P[:, 2])
    Dlip = 0.07
    for dd in np.arange(0.03, 0.09, 0.005):
        beyond = sector & (d > dd) & (d < 0.17)
        if beyond.sum() > 5 and np.median(res[beyond]) < 1e-3 and np.percentile(res[beyond], 90) < 2e-3:
            Dlip = dd; break
    nb = side_fit(Dlip, 0.17)
    if os.environ.get('PF_DEBUG'):
        mk_ = sector & (d > Dlip) & (d < 0.17); rr0 = np.abs(eval_surface(nb, P[mk_, 0], P[mk_, 1]) - P[mk_, 2])
        print(f'  side ring fit {nb["nu"]}x{nb["nv"]}: {mk_.sum()} verts, p95 {np.percentile(rr0, 95)*1e3:.2f} max {rr0.max()*1e3:.2f} mm')
    print(f'{name}: lip {Dlip*1e3:.0f} mm wide (where the surface rejoins the side surface)')
    # the lip's width along the edge: Dlip, except where the flare ends in a WALL (a steep drop to the body, as at the
    # AE86's rear lower corner): there the lip stops at the top of the wall, and the wall's own vertices go to
    # neither the lip nor the side face (the hole filler gives the wall its own face)
    st_w = np.arange(0.0, Alen + 1e-9, 0.02); Wst = np.full(len(st_w), Dlip); wall = np.zeros(len(st_w), bool)
    for k_, a_ in enumerate(st_w):
        mk_ = (np.abs(apos - a_) < 0.015) & (d > 0.005) & (d < Dlip + 0.01)
        if mk_.sum() < 4: continue
        o_ = np.argsort(d[mk_]); dd_, hh_ = d[mk_][o_], P[mk_, 2][o_]
        for j_ in range(len(dd_) - 1):
            gd, gh = dd_[j_ + 1] - dd_[j_], hh_[j_ + 1] - hh_[j_]
            if gd > 0.002 and abs(gh) > 0.008 and abs(gh) / gd > 1.2:
                Wst[k_] = dd_[j_]; wall[k_] = True; break
    if wall.any():
        Wst = np.array([np.median(Wst[max(0, k_ - 1):k_ + 2]) for k_ in range(len(Wst))])
        print(f'{name}: flare ends in a wall along {wall.sum()*20} mm of the edge (lip {Wst[wall].min()*1e3:.0f}-{Wst[wall].max()*1e3:.0f} mm wide there)')
    Wf = lambda a_: np.interp(np.asarray(a_, float), st_w, Wst)
    wallf = lambda a_: np.interp(np.asarray(a_, float), st_w, wall.astype(float)) > 0.5
    mm = lambda q: (np.asarray(q) * 1000).tolist()
    tt_ = np.linspace(a_lo - (0.01 if a_lo < 0.03 else 0.0), a_hi + (0.01 if a_hi > Alen - 0.03 else 0.0), 160)   # the lip's stretch
    outer = E(tt_) + Wf(tt_)[:, None] * En(tt_)
    inner = (E(tt_) - 0.06 * En(tt_))[::-1]
    poly = mm(np.r_[outer, inner])
    # (5) the side faces first ('main surfaces first'), with the arch zone left out of their data
    in_lip_v = np.zeros(len(V), bool)
    in_lip_v[u[sector & ((d < Wf(apos) - 0.003) | (wallf(apos) & (d < Wf(apos) + 0.02)))]] = True   # lip, and the wall
    Fl = Fr[~in_lip_v[Fr].any(1)]
    # sub-panels at the arch (Class-A practice: patch boundaries through the arch ends): above the arch, behind
    # it and in front of it. Character lines that stop at the arch then run edge to edge inside their sub-panel.
    # Panel plane: s along the car, t across (t grows downward here when the frame's e2 points down).
    Er = E(np.linspace(0, Alen, 400)); tsign = 1.0 if (to_plane(V[u], fr)[:, 1] @ (-V[u, 1]) > 0) else -1.0
    t_top = (Er[:, 1] * tsign).min() * tsign                    # the arch's highest point (t)
    t_cut = t_top - tsign * (Dlip + 0.01)                        # the line above the lip
    s_lo = s_hi = c[0]                                           # below the cut: behind / in front of the arch centre
    BIG = 5.0
    below = lambda T: (T - t_cut) * tsign > 0
    areas = {'above': lambda S_, T_: ~below(T_),
             'rear': lambda S_, T_: below(T_) & (S_ < s_lo),
             'front': lambda S_, T_: below(T_) & (S_ > s_hi)}
    rect = {'above': [[-BIG, t_cut - tsign * BIG], [BIG, t_cut - tsign * BIG], [BIG, t_cut], [-BIG, t_cut]],
            'rear': [[-BIG, t_cut], [s_lo, t_cut], [s_lo, t_cut + tsign * BIG], [-BIG, t_cut + tsign * BIG]],
            'front': [[s_hi, t_cut], [BIG, t_cut], [BIG, t_cut + tsign * BIG], [s_hi, t_cut + tsign * BIG]]}
    out, side = [], dict(fits={}, bounds=[])
    Pall = to_plane(V, fr); cen = Pall[Fr].mean(1)
    ledges = ledge_lines(V, Fr, Nv, others, fr)
    for key, inside in areas.items():
        # data: its triangles plus 20 mm round its cut edges (so the surface reaches its seam with support)
        pad_ = np.zeros(len(Fr), bool)
        for ds_, dt_ in ((0.02, 0), (-0.02, 0), (0, 0.02), (0, -0.02)):
            pad_ |= inside(cen[:, 0] + ds_, cen[:, 1] + dt_)
        Fs = Fr[pad_ & ~in_lip_v[Fr].all(1)]
        if len(Fs) < 20: continue
        ex_ = [L_ for L_ in ledges if inside(np.array([0.5 * (L_['s_lo'] + L_['s_hi'])]), eval_func(L_, [0.5 * (L_['s_lo'] + L_['s_hi'])]))[0]]
        res_ = fit_bands(f'{name}:{key}', V, Fs, Nv, keep=~in_lip_v, Fr_lines=Fs[~in_lip_v[Fs].any(1)], cut_poly=poly, fr=fr,
                         Fr_outline=Fr, area_poly=mm(np.array(rect[key])), extra_lines=ex_)
        out += res_
        last = fit_bands.last
        if key == 'above' or not side['fits']:
            pass
        # the lip is matched to whichever sub-panel's faces lie next to it
        off = len(side['bounds'])
        for bi, f_ in last['fits'].items():
            side['fits'][off + bi] = (f_, last['bounds'][bi], last['bounds'][bi + 1], inside)
        side['bounds'] += last['bounds']
    # (4) the lip in arch coordinates (arc length round the arch, distance out from the real edge), height above
    # the panel plane; samples of the ACTUAL side faces on a 25 mm ring just outside it go in as data, so the lip
    # meets them in position and slope (no ridge at its outer edge)
    # data from 50 mm past each end (flat panel there): the lip fades into the panel instead of ending square
    inspan = (th > max(a_lo - 0.05, 0.005)) & (th < min(a_hi + 0.05, Alen - 0.005))
    lip = inspan & (d > -0.015) & (d < np.where(wallf(th), Wf(th) - 0.0015, Dlip + 0.002))
    a = th[lip] * R; dl = d[lip]; hl = P[lip, 2]
    ag, dg = np.meshgrid(np.linspace(a.min(), a.max(), 80), np.linspace(Dlip, Dlip + 0.025, 6), indexing='ij')
    ag, dg = ag.ravel(), dg.ravel()
    keep_s = ~wallf(ag); ag, dg = ag[keep_s], dg[keep_s]          # no side samples beyond a wall (body is 30 mm lower)
    XY_ = E(ag) + dg[:, None] * En(ag)
    sx, tx = XY_[:, 0], XY_[:, 1]
    hs = np.full(len(sx), np.nan)
    for bi, (f_, lo_, hi_, inside_) in side['fits'].items():
        inb = inside_(sx, tx)
        if lo_ is not None: inb &= tx > eval_func(lo_, sx)
        if hi_ is not None: inb &= tx < eval_func(hi_, sx)
        hs[inb] = eval_surface_ext(f_, sx[inb], tx[inb])
    ok_ = ~np.isnan(hs)
    S = np.r_[np.c_[a, dl, hl], np.c_[ag[ok_], dg[ok_], hs[ok_]]]
    dom = [a.min() - 0.03, a.max() + 0.03, dl.min() - 0.005, Dlip + 0.03]
    if os.environ.get('PF_LIPNV'):                           # experiment: fixed controls along x across
        nu_, nv_ = [int(x) for x in os.environ['PF_LIPNV'].split('x')]
        lf = fit_surface(S, dom, nu_, nv_, 1e-6); lf['lam'] = 1e-6
        rr_ = np.abs(eval_surface(lf, S[:, 0], S[:, 1]) - S[:, 2]); cvb = 0.0
    else:
        lf, rr_, cvb = select_fit(S, dom, strip=True)
    r = rr_[:len(a)]; ns, nt = lf['nu'], lf['nv']
    if os.environ.get('PF_DEBUG'):
        for i_ in np.argsort(-r)[:6]: print(f'  lip worst: {np.degrees(a[i_]/R):5.0f} deg round, {dl[i_]*1e3:4.0f} mm out: {r[i_]*1e3:.1f} mm')
    a0, a1 = dom[0], dom[1]; d0, d1 = dom[2] - Dlip, dom[3] - Dlip
    AA, TT = np.meshgrid(np.linspace(a0, a1, 260), np.linspace(d0, d1, 90), indexing='ij'); AA, TT = AA.ravel(), TT.ravel()
    XY_ = E(AA) + (TT + Dlip)[:, None] * En(AA)
    X = np.c_[XY_[:, 0], XY_[:, 1], eval_surface(lf, AA, TT + Dlip)]
    for nu, nv in ((14, 10), (20, 14), (28, 18), (36, 24)):
        ku = knots(nu, a0, a1); kv = knots(nv, d0, d1)
        Bm = (basis(AA, ku, nu)[:, :, None] * basis(TT, kv, nv)[:, None, :]).reshape(len(X), -1)
        Pl = np.linalg.lstsq(Bm, X, rcond=None)[0]; ea = np.linalg.norm(Bm @ Pl - X, axis=1).max()
        if ea < 5e-5: break
    base = fit_panel(name, V, Fr, Nv, verbose=False, fr=fr, outline_only=True)
    e = dict(base)
    e.update(name=f'{name}:lip', dom=mm([a0, a1, d0, d1]), nu=nu, nv=nv, ku=mm(ku), kv=mm(kv), poles=mm(Pl.reshape(nu, nv, 3)),
             general=True, own_plane=True, line_frame=[x.tolist() for x in fr], band_poly=poly, band_lo=None, band_hi=None,
             fit_p95_mm=float(np.percentile(r, 95) * 1000))
    print(f"{e['name']:28s} verts {lip.sum():4d} ARCH LIP (arch coordinates, matched to the side faces: {ok_.sum()} samples): {ns}x{nt} cv {cvb*1e3:.2f} mm  fit p95 {np.percentile(r,95)*1e3:.2f} max {r.max()*1e3:.2f} mm  as {nu}x{nv} (approx {ea*1e3:.3f} mm)")
    return out + [e]


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
        if comp.startswith('arch'):                    # GEO_body:arch0 = crease region 0 has a wheel arch
            pcs_ = crease_pieces(V, F, Nv); ri_ = int(comp[4:] or 0)
            res += fit_arch_panel(f'{name}:r{ri_}', V, pcs_[ri_], Nv, others=[q for i_, q in enumerate(pcs_) if i_ != ri_])
            continue
        if comp.startswith('w'):                       # GEO_body:w0 = crease region 0 wraps a corner (rear quarter into
            # the tail): sub-panels by normal direction (PF_WRAP deg spread each, default 50), each by the band method
            # over its own plane; data padded 20 mm past the seam so each surface reaches it with support
            pcs_ = crease_pieces(V, F, Nv)
            for ri in comp[1:].split(','):
                Fr = pcs_[int(ri)]
                # ONE cut, at the corner: the main sub-panel = triangles within PF_WRAP deg (45) of the region's
                # area-weighted main direction (k-means slices a tumblehome side into strips and loses its lines)
                T_ = V[Fr]; n_ = np.cross(T_[:, 1] - T_[:, 0], T_[:, 2] - T_[:, 0]); A_ = np.linalg.norm(n_, axis=1)
                n_ /= np.maximum(A_, 1e-12)[:, None]; n_ *= np.sign((n_ * Nv[Fr].mean(1)).sum(1))[:, None]
                d0 = (n_ * A_[:, None]).sum(0); d0 /= np.linalg.norm(d0)
                for _ in range(5):                                         # the dominant direction, not the mean
                    w_ = A_ * (n_ @ d0 > np.cos(np.radians(30))); d0 = (n_ * w_[:, None]).sum(0); d0 /= np.linalg.norm(d0)
                main_ = n_ @ d0 > np.cos(np.radians(float(os.environ.get('PF_WRAP', 45))))
                parts = []
                for is_main, sel_ in ((True, main_), (False, ~main_)):
                    if sel_.sum(): parts += [(is_main, p_) for p_ in components(V, Fr[sel_])[0] if len(p_) >= 20]
                parts.sort(key=lambda p_: (not p_[0], -len(p_[1])))           # the main side first
                cen = V[Fr].mean(1); main_fit = None
                from scipy.spatial import cKDTree
                # one smooth SEAM curve per non-main sub-panel, through the vertices it shares with the main one: both
                # sides are trimmed exactly on it (outlines reach one triangle past it, then the far side is cut away),
                # not along the zig-zag of Kunos's triangle edges (teeth and slivers at the rear corner)
                _, wid_ = components(V, Fr); Fm0 = next((q_ for m_, q_ in parts if m_), None)
                seams = {}
                if Fm0 is not None and os.environ.get('PF_SEAM', '1') == '1':
                    for wi, (is_main, Fw) in enumerate(parts):
                        if is_main: continue
                        sh_ = set(wid_[Fm0.ravel()]) & set(wid_[Fw.ravel()])
                        if len(sh_) < 4: continue
                        X_ = V[[i_ for i_ in sorted(set(Fr.ravel())) if wid_[i_] in sh_]]
                        X_ = np.unique(np.round(X_, 6), axis=0)
                        # the seam's own frame: normal halfway between the two faces, so both cross it at ~45 deg
                        nm_ = Nv[np.unique(Fm0)].mean(0); nm_ /= np.linalg.norm(nm_)
                        np_ = Nv[np.unique(Fw)].mean(0); np_ /= np.linalg.norm(np_)
                        w_ = nm_ + np_; w_ /= np.linalg.norm(w_)
                        cx_ = X_.mean(0); e1_ = np.linalg.svd(X_ - cx_)[2][0]; e1_ -= (e1_ @ w_) * w_; e1_ /= np.linalg.norm(e1_)
                        fm0 = (cx_, e1_, np.cross(w_, e1_), w_)
                        Q_ = to_plane(X_, fm0)[:, :2]
                        if len(Q_) < 4: continue
                        c_ = Q_.mean(0); d1_ = np.linalg.svd(Q_ - c_)[2][0]; d2_ = np.array([-d1_[1], d1_[0]])
                        a_, b_ = (Q_ - c_) @ d1_, (Q_ - c_) @ d2_
                        g_ = fit_func(a_, b_, [a_.min() - 0.15, a_.max() + 0.15], tol=3e-3, nmax=4)   # a fair curve through the middle of a zig-zag zone
                        Pw_ = to_plane(V[np.unique(Fw)], fm0)[:, :2]
                        sg_ = np.sign(np.median(((Pw_ - c_) @ d2_) - eval_func(g_, (Pw_ - c_) @ d1_)))
                        aa_ = np.linspace(a_.min() - 0.1, a_.max() + 0.1, 80); C_ = c_ + aa_[:, None] * d1_ + eval_func(g_, aa_)[:, None] * d2_
                        side_ = lambda sgn: (np.r_[C_, C_[::-1] + sgn * 3.0 * d2_] * 1000).tolist()
                        dev_ = np.abs(b_ - eval_func(g_, a_))
                        seams[wi] = dict(part=side_(sg_), main=side_(-sg_), frame=[x.tolist() for x in fm0])
                        print(f'{name}:r{ri}w{wi}: seam curve through {len(Q_)} shared vertices (within {dev_.max()*1e3:.1f} mm), {np.ptp(a_)*1e3:.0f} mm long')
                def grown(Fw, others):                     # outline one triangle past each seam
                    ws_ = set(wid_[Fw.ravel()]); ext_ = [Fw]
                    for Fo_ in others:
                        ext_.append(Fo_[np.array([any(wid_[v_] in ws_ for v_ in t_) for t_ in Fo_])])
                    return np.concatenate(ext_)
                for wi, (is_main, Fw) in enumerate(parts):
                    tree = cKDTree(V[np.unique(Fw)])
                    near = tree.query(cen)[0] < 0.02
                    own_ = {tuple(t_) for t_ in Fw}; isown = np.array([tuple(t_) in own_ for t_ in Fr]); near |= isown
                    Vx, Nx, Fdat = V, Nv, Fr[near]
                    if not is_main and main_fit is not None and os.environ.get('PF_WMATCH', '1') == '1':
                        # seam matching (as the arch lip): on the main side of the seam, samples of the FINISHED main
                        # surfaces replace the raw padding vertices, so this sub-panel meets them in position and slope
                        Fm = main_fit['F']; fm = main_fit['last']['fr']
                        Tm = V[Fm]; Tm = Tm[tree.query(Tm.mean(1))[0] < 0.06]
                        X = sample_tris_bary(Tm, 0.006) if len(Tm) else np.zeros((0, 3))
                        X = X[tree.query(X)[0] < 0.025] if len(X) else X
                        S_ = to_plane(X, fm); h_ = np.full(len(X), np.nan); hs_ = np.zeros(len(X)); ht_ = np.zeros(len(X))
                        for pc in main_fit['last']['pieces']:
                            mk = np.isnan(h_)
                            if pc['lo'] is not None: mk &= S_[:, 1] > eval_func(pc['lo'], S_[:, 0])
                            if pc['hi'] is not None: mk &= S_[:, 1] < eval_func(pc['hi'], S_[:, 0])
                            if pc['band_s'] is not None: mk &= (S_[:, 0] > pc['band_s'][0]) & (S_[:, 0] <= pc['band_s'][1])
                            if not mk.any(): continue
                            e_ = 1e-4; f_ = pc['f']
                            h_[mk] = eval_surface_ext(f_, S_[mk, 0], S_[mk, 1])
                            hs_[mk] = (eval_surface_ext(f_, S_[mk, 0] + e_, S_[mk, 1]) - eval_surface_ext(f_, S_[mk, 0] - e_, S_[mk, 1])) / (2 * e_)
                            ht_[mk] = (eval_surface_ext(f_, S_[mk, 0], S_[mk, 1] + e_) - eval_surface_ext(f_, S_[mk, 0], S_[mk, 1] - e_)) / (2 * e_)
                        ok_ = ~np.isnan(h_)
                        Xs = from_plane(np.c_[S_[ok_, :2], h_[ok_]], fm)
                        Ns = -hs_[ok_, None] * fm[1] - ht_[ok_, None] * fm[2] + fm[3]; Ns /= np.linalg.norm(Ns, axis=1)[:, None]
                        Ns *= np.sign(Ns @ Nv[np.unique(Fw)].mean(0))[:, None] if len(Ns) else 1
                        mainset = {tuple(t_) for t_ in Fm}
                        keep_ = np.array([tuple(t_) not in mainset for t_ in Fdat])      # drop raw main-side padding
                        n0 = len(V); Vx = np.r_[V, Xs]; Nx = np.r_[Nv, Ns]
                        Fdat = np.r_[Fdat[keep_], np.repeat(np.arange(n0, n0 + len(Xs))[:, None], 3, axis=1)]
                        print(f'{name}:r{ri}w{wi}: matched to the main side by {len(Xs)} samples of its finished surfaces')
                    print(f'{name}:r{ri}w{wi}: {len(Fw)} tris (+{near.sum() - len(Fw)} padding)' + (' MAIN' if is_main else ''))
                    if is_main: Fo_ = grown(Fw, [parts[k_][1] for k_ in seams])
                    elif wi in seams: Fo_ = grown(Fw, [Fm0])
                    else: Fo_ = Fw
                    n_before = len(res)
                    res += fit_bands(f'{name}:r{ri}w{wi}', Vx, Fdat, Nx, Fr_outline=Fo_, Fr_lines=Fw if Vx is not V else None)
                    for e_ in res[n_before:]:
                        cps_ = [dict(poly=seams[k_]['part'], frame=seams[k_]['frame']) for k_ in seams] if is_main else                                ([dict(poly=seams[wi]['main'], frame=seams[wi]['frame'])] if wi in seams else [])
                        if cps_: e_['cut_polys'] = cps_
                    if is_main and main_fit is None: main_fit = dict(F=Fw, last=fit_bands.last)
            continue
        if comp.startswith('b'):
            for ri in comp[1:].split(','):
                res += fit_bands(f'{name}:r{ri}', V, crease_pieces(V, F, Nv)[int(ri)], Nv)
            continue
        if comp.startswith('rall'):                     # rall!0,1,2,5 = all except those (built as bands)
            # every crease face of a part above a minimum area (small ledges and chamfers matter: a missing 5 mm
            # ledge read as a groove); each one surface over its own plane
            amin = float(os.environ.get('PF_MINAREA', 3e-4))
            skip = {int(x) for x in comp[5:].split(',') if x} if comp.startswith('rall!') else set()
            for ri, Fr in enumerate(crease_pieces(V, F, Nv)):
                if ri in skip: continue
                T_ = V[Fr]; A_ = np.linalg.norm(np.cross(T_[:, 1] - T_[:, 0], T_[:, 2] - T_[:, 0]), axis=1).sum() / 2
                if A_ < amin: continue
                parts = wrap_split(V, Fr, Nv)
                for wi, Fw in enumerate(parts):
                    if len(parts) > 1 and len(Fw) < 4: continue
                    try:
                        res.append(fit_panel(f'{name}:r{ri}' + (f'w{wi}' if len(parts) > 1 else ''), V, Fw, Nv))
                    except Exception as ex:
                        print(f'{name}:r{ri}w{wi} failed: {ex}')
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
