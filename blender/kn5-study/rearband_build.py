"""AE86 rear lower band: the side skin's (GEO_body crease piece 0) band below the body line, from the tail's centre round
the rear corner to the rear wheel arch, as ONE build (24 Nov).

    python rearband_build.py CAR_DIR OUT_DIR

Kunos's piece 0 is the whole side skin; below the lamps it carries one profile across the rear, round the corner and
along the side to the arch: a slanted foot from the bumper edge (y 509), a soft line at ~518, the knee (~576), the body
line (a two-row round at 604 / 609, ~20-28 deg) and, above it, the side face. The tail build (x < 0.45) and the quarter
(x > 0.45, with a 45 deg wrap split) used to make it in pieces: a 2-3 deg shading step at the clip plane x 0.45, gaps
and a hole-fill patch at the corner (5-8 mm misses). Now:
- ownership: piece-0 triangles below Y_TOP (exact cut on the plane y = Y_TOP, just above the body line's top row) and
  behind Z_FRONT (the arch) = this build; the tail and the quarter leave them out (PF_NOBAND=1 in panel_fit.load_mesh:
  the straddling triangles keep their part above the plane there, so both sides end on the same cut);
- SWEEP (left half, right = mirror) from x = X0 (where the plate panel's end leaves the band its full height) round the
  corner to the arch: vertical station planes square to the spine (plan line of the band's bottom edge), each section
  one run from the top (body line / lamp crease) to the bottom edge, PN-lifted (Kunos's shading surface), columns spaced
  by HEIGHT (the lines are horizontal: each stays on one column), rows smoothed in their own frames;
- CENTRE strip (|x| < X0, under the plate panel, full width): one fitted face with the sweep's first rows (both sides)
  as data, cut exactly on the sweep's first station planes;
- END face at the arch: the band triangles past the sweep's last full station, fitted with its last rows as data, cut
  on that plane (right = mirror).
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path:
    sys.path.append(r'D:\ClaudeData\pylibs')
import panel_fit as PF

MIR = np.array([-1.0, 1.0, 1.0])
Y_TOP = float(os.environ.get('RB_YTOP', 0.6097))      # just above the body line's top vertex row (y 0.609 along the side)
Z_FRONT = float(os.environ.get('RB_ZFRONT', -1.475))  # behind the rear arch (the band's main part ends at z -1.479)
X0 = float(os.environ.get('RB_X0', 0.33))             # sweep start: the plate panel's end (r0eL x 0.287-0.317) is passed
STEP = float(os.environ.get('RB_STEP', 0.015))


_CAND = {}
def candidates(car):
    """(V, F, N, B): the hatch-free raw GEO_body and the band's candidate triangles (vertex index triples): side-skin
    triangles reaching below Y_TOP, wholly behind Z_FRONT, the largest connected part (the arch flare's bits are not
    band). Kunos piece numbering of the hatch-free mesh, default crease angle (ownership must not depend on env)."""
    if car in _CAND: return _CAND[car]
    import hatch_build as HB
    V, F, N = PF.load_mesh(car, 'GEO_body', raw=True)
    own = {tuple(sorted(t)) for t in HB.hatch_owned(car)}
    F = F[np.array([tuple(sorted(t)) not in own for t in F], bool)]
    pcs = PF.crease_pieces(V, F, N, deg=20.0)
    probe = np.array([0.55, 0.56, -2.085])                      # on the band under the left lamp
    P0 = min(pcs[:5], key=lambda p: np.linalg.norm(V[p].mean(1) - probe, axis=1).min())
    T = V[P0]
    B = P0[(T[:, :, 1].min(1) < Y_TOP - 1e-6) & (T[:, :, 2].max(1) < Z_FRONT)]
    comps = PF.components(V, B)[0]
    B = max(comps, key=len)
    _CAND[car] = (V, F, N, B)
    return _CAND[car]


def band_owned(car):
    """the band's candidate triangles (raw GEO_body vertex index triples): other builds leave them out and keep only
    their parts above Y_TOP (PF_NOBAND in panel_fit.load_mesh)"""
    return candidates(car)[3]


def spine_points(V, Fb, x_min=-1.0):
    """the band's bottom edge: its boundary vertices below y 0.515 (the bumper edge), plan points"""
    _, wid = PF.components(V, Fb)
    loops = PF.boundary_loops(Fb, wid)
    pos = {}
    for i, w in enumerate(wid): pos.setdefault(int(w), V[i])
    X = np.array([pos[int(w)] for L in loops for w in L])
    return X[(X[:, 1] < 0.515) & (X[:, 0] >= x_min)]


def spine(X, centre_z=-1.55, step=0.001):
    """plan line (x, z) through the bottom-edge points X (both halves, mirrored for symmetry), as a dense polyline at
    y 0 from the centre out (left half) + arc lengths (as bumper_build.spine, from points)"""
    import strip_build as SB
    X = np.unique(np.round(X, 6), axis=0); X = np.r_[X, X * MIR]
    ang = np.arctan2(X[:, 0], -(X[:, 2] - centre_z))
    X = X[np.argsort(ang)]; P = np.c_[X[:, 0], np.zeros(len(X)), X[:, 2]]
    a = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    f = SB.fit_graph(a, P, [0, a[-1]], tol=1e-3, nmax=int(np.clip(a[-1] / 0.05, 4, 80)), mu=1e-4)
    S = SB.eval_graph(f, np.linspace(0, a[-1], int(a[-1] / step) + 1))
    S = (S + (S * MIR)[::-1]) / 2
    i0 = int(np.argmin(np.abs(S[:, 0]))); L = S[i0:]; L[0, 0] = 0.0
    return L, np.r_[0, np.cumsum(np.linalg.norm(np.diff(L, axis=0), axis=1))], f['err']


def plane_of(row, ref):
    """the station plane through a grid row: (point, unit normal pointing towards ref)"""
    m = row.mean(0); n = np.linalg.svd(row - m)[2][2]
    if n @ (ref - m) < 0: n = -n
    return m, n


def corner_normals(V, F, deg=12.0):
    """per-triangle-corner normals for the PN lift, CREASE-AWARE: each corner averages (area-weighted) the facet normals
    of the triangles round its vertex that face within `deg` of its own triangle. Kunos's vertex normals average across
    the knee: on the flat facets beside it the PN patch then bowed 1-2 mm out of the flat face (a dark band in grey)."""
    T = V[F]; fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ar = np.linalg.norm(fn, axis=1)
    fn = fn / np.maximum(ar, 1e-18)[:, None]
    key = np.round(V / 1e-6).astype(np.int64); kid = {}
    wid = np.array([kid.setdefault(tuple(k), len(kid)) for k in key])
    inc = {}
    for t_, f in enumerate(F):
        for c in f: inc.setdefault(int(wid[c]), []).append(t_)
    cosd = np.cos(np.radians(deg)); Nc = np.zeros((len(F), 3, 3))
    for t_, f in enumerate(F):
        for j, c in enumerate(f):
            ts = np.array(inc[int(wid[c])]); s = fn[ts] @ fn[t_]; k = ts[s > cosd]
            n = (fn[k] * ar[k, None]).sum(0); Nc[t_, j] = n / max(np.linalg.norm(n), 1e-18)
    return Nc


def knee_rows(Rd, ncol, ylo=0.568, yhi=0.597, arm=0.003):
    """the dense station rows Rd (top first) resampled with the KNEE on a fixed column: per row the point of largest
    turn between ylo and yhi (the knee drifts from y 587 at the rear to 576 on the side: with columns at fixed height
    steps it fell between columns and the approximated surface rounded it over 5-10 mm, a dark crescent in grey);
    top -> knee and knee -> bottom each spaced by height, column counts from the median heights. Returns (rows, knee column)."""
    def turn_at(P):
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
        q = np.arange(0, d[-1], 0.0005); C = np.c_[[np.interp(q, d, P[:, c]) for c in range(3)]].T
        k = max(int(arm / 0.0005), 2); a = np.zeros(len(C))
        for i in range(k, len(C) - k):
            u, v = C[i] - C[i - k], C[i + k] - C[i]
            a[i] = np.degrees(np.arccos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12), -1, 1)))
        m = (C[:, 1] > ylo) & (C[:, 1] < yhi)
        i = int(np.argmax(np.where(m, a, -1))); return C, d, q[i]
    info = [turn_at(P) for P in Rd]
    hk = np.array([C[np.searchsorted(q_, qk) if False else int(qk / 0.0005), 1] for (C, d, qk), q_ in zip(info, [None] * len(info))])
    top, bot = np.median(Rd[:, 0, 1]), np.median(Rd[:, -1, 1]); hkm = np.median(hk)
    n_top = max(3, int(round((ncol - 1) * (top - hkm) / (top - bot))) + 1); n_bot = max(3, ncol - n_top + 1)
    out = []
    for (C, d, qk), P in zip(info, Rd):
        ik = int(qk / 0.0005)
        def by_height(S, n):
            h = np.r_[0, np.cumsum(np.abs(np.diff(S[:, 1])) + 1e-7)]; s = np.linspace(0, h[-1], n)
            return np.c_[[np.interp(s, h, S[:, c]) for c in range(3)]].T
        out.append(np.r_[by_height(C[:ik + 1], n_top), by_height(C[ik:], n_bot)[1:]])
    return np.array(out), n_top - 1


def frame_at(Sp, arc, s):
    """spine point (y 0), horizontal unit tangent and outward normal at arc positions s"""
    s = np.atleast_1d(np.asarray(s, float))
    P = np.c_[[np.interp(s, arc, Sp[:, c]) for c in range(3)]].T
    h = 1e-3
    T = np.c_[[np.interp(np.clip(s + h, arc[0], arc[-1]), arc, Sp[:, c]) - np.interp(np.clip(s - h, arc[0], arc[-1]), arc, Sp[:, c]) for c in range(3)]].T
    T[:, 1] = 0; T /= np.linalg.norm(T, axis=1)[:, None]
    O = np.cross(np.array([0.0, 1.0, 0.0]), T)
    O *= np.sign((O * np.c_[P[:, 0], np.zeros(len(P)), P[:, 2] + 1.55]).sum(1))[:, None]    # away from the car's middle
    return P, T, O


def to_sbd(Sp, arc, X):
    """points -> (s along the spine, height y, outward offset d)"""
    import strip_build as SB
    s, _ = SB.spine_s(np.c_[Sp[:, 0], np.zeros(len(Sp)), Sp[:, 2]], np.c_[X[:, 0], np.zeros(len(X)), X[:, 2]])
    P, T, O = frame_at(Sp, arc, s)
    return np.c_[s, X[:, 1], ((X - P) * O).sum(1)]


def lines_sweep(Fb, Vb, Sp, arc, s0, s1, verbose=True, knee_pts=None):
    """the DOOR method in the band's own coordinates (24 Nov): every Kunos band vertex mapped to (s along the spine, y,
    d outward); the KNEE = one fair curve (y_k(s), d_k(s)) through Kunos's knee vertices (edges turning > 10 deg in
    y 0.568-0.597); each band (bottom -> knee, knee -> top) = ONE smooth height field d(s, y) fitted to Kunos's
    VERTICES only (control counts by cross-validation, select_fit), the knee curve as heavy data in both; grids per
    station from boundary to boundary with the knee as the shared column. No sections: section rows sampled Kunos's
    facet chords (or PN bulges) and the band shaded blotchy, rougher than the door. Returns (lower grid, upper grid)."""
    u = np.unique(Fb); X = Vb[u]
    S3 = to_sbd(Sp, arc, X)
    m = (S3[:, 0] > s0 - 0.04) & (S3[:, 0] < s1 + 0.04) & (X[:, 0] > 0) & (X[:, 1] < Y_TOP - 2e-4)
    S3 = S3[m]
    # knee vertices: ends of band edges turning more than RB_KNEE_DEG, in the knee's height window
    T = Vb[Fb]; fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-18)[:, None]
    kk = np.round(Vb / 1e-6).astype(np.int64); kid = {}
    wid = np.array([kid.setdefault(tuple(k), i) for i, k in enumerate(kk)])
    E = {}
    for k, f in enumerate(wid[Fb]):
        for a_, b_ in ((0, 1), (1, 2), (2, 0)): E.setdefault(tuple(sorted((int(f[a_]), int(f[b_])))), []).append(k)
    KV = set(); thr = float(os.environ.get('RB_KNEE_DEG', 10))
    for (a_, b_), ks in E.items():
        if len(ks) == 2 and np.degrees(np.arccos(np.clip(abs(fn[ks[0]] @ fn[ks[1]]), -1, 1))) > thr:
            ya, yb = Vb[a_, 1], Vb[b_, 1]
            if 0.568 < ya < 0.597 and 0.568 < yb < 0.597: KV.update((a_, b_))
    K = Vb[sorted(KV)]; K = K[K[:, 0] > 0]
    if knee_pts is not None and os.environ.get('RB_KNEE_SEC', '1') == '1':
        # the stations' knee points: each section crosses the knee ON Kunos's crease edge (the vertex set had two
        # rows 4 mm apart at the rear: a 2.6 mm noisy curve, vertices sorted into the wrong band)
        K = np.asarray(knee_pts)
    SK = to_sbd(Sp, arc, K); SK = SK[(SK[:, 0] > s0 - 0.06) & (SK[:, 0] < s1 + 0.06)]
    SK = SK[np.argsort(SK[:, 0])]
    dom_s = [s0 - 0.08, s1 + 0.08]
    nk = int(os.environ.get('RB_KNEE_N', 12))
    fy = PF.fit_func(SK[:, 0], SK[:, 1], dom_s, tol=0.6e-3, nmax=nk)
    fd = PF.fit_func(SK[:, 0], SK[:, 2], dom_s, tol=0.6e-3, nmax=nk)
    if verbose: print(f'knee: {len(SK)} Kunos vertices, y(s) {fy["n"]} controls p95 {fy["err"] * 1e3:.2f} mm, d(s) {fd["n"]} controls p95 {fd["err"] * 1e3:.2f} mm', flush=True)
    yk = lambda s: PF.eval_func(fy, s)
    dk = lambda s: PF.eval_func(fd, s)
    # boundaries as y(s): bottom edge (Kunos outline ~509) and top (the cut at Y_TOP / the lamp crease)
    _, wid2 = PF.components(Vb, Fb); pos = {}
    for i, w in enumerate(wid2): pos.setdefault(int(w), Vb[i])
    Bd = np.array([pos[int(w)] for L in PF.boundary_loops(Fb, wid2) for w in L]); Bd = Bd[Bd[:, 0] > 0]
    SB_ = to_sbd(Sp, arc, Bd); inr = (SB_[:, 0] > s0 - 0.06) & (SB_[:, 0] < s1 + 0.06)
    lo = SB_[inr & (SB_[:, 1] < 0.53)]; lo = lo[np.argsort(lo[:, 0])]
    hi = SB_[inr & (SB_[:, 1] > 0.595)]; hi = hi[np.argsort(hi[:, 0])]
    fb = PF.fit_func(lo[:, 0], lo[:, 1], dom_s, tol=0.5e-3, nmax=10)
    ft = PF.fit_func(hi[:, 0], np.minimum(hi[:, 1], Y_TOP), dom_s, tol=0.5e-3, nmax=10)
    yb_ = lambda s: PF.eval_func(fb, s)
    yt_ = lambda s: np.minimum(PF.eval_func(ft, s), Y_TOP)
    # band fits: vertices + the knee curve (repeated) in both
    sk = np.linspace(s0 - 0.03, s1 + 0.03, 120); KL = np.c_[sk, yk(sk), dk(sk)]
    rep = int(os.environ.get('RB_KNEE_REP', 5))
    fits = []
    for nm, sel in (('lower', S3[:, 1] <= yk(S3[:, 0]) + 5e-4), ('upper', S3[:, 1] >= yk(S3[:, 0]) - 5e-4)):
        S = np.r_[S3[sel], np.repeat(KL, rep, axis=0)]
        dom = [dom_s[0], dom_s[1], S[:, 1].min() - 0.01, S[:, 1].max() + 0.01]
        f, r, cv = PF.select_fit(S, dom)
        rv = r[:sel.sum()]
        if verbose: print(f'{nm} band: {sel.sum()} vertices, {f["nu"]}x{f["nv"]} controls lam {f["lam"]:.0e}, cv {cv * 1e3:.2f} mm; '
                          f'own vertices p95 {np.percentile(rv, 95) * 1e3:.2f} max {rv.max() * 1e3:.2f} mm', flush=True)
        fits.append(f)
    ss = np.linspace(s0, s1, max(2, int(np.ceil((s1 - s0) / STEP))) + 1)
    P, T_, O = frame_at(Sp, arc, ss); up = np.array([0.0, 1.0, 0.0])
    n_lo = int(os.environ.get('RB_NLO', 18)); n_up = int(os.environ.get('RB_NUP', 9))
    def grid(f, ya, yb, n, knee_last):
        Y = np.linspace(0, 1, n)[None, :] * (yb - ya)[:, None] + ya[:, None]
        D = np.array([PF.eval_surface(f, np.full(n, s_), Y[i]) for i, s_ in enumerate(ss)])
        if knee_last: D[:, -1] = dk(ss)
        else: D[:, 0] = dk(ss)
        return P[:, None] + Y[..., None] * up + D[..., None] * O[:, None]
    yK = yk(ss)
    return grid(fits[0], yb_(ss), yK, n_lo, True), grid(fits[1], yK, yt_(ss), n_up, False)


def vertex_rows(Vb, Fb, Sp, arc, ratio=0.12, top_y=0.6065):
    """Kunos's vertex ROWS of the band (left half), traced along the spine: each strip triangle has one edge running
    along a row (two corners on one row, one on the next) - per triangle the edge with the smallest |dy| / |ds| below
    `ratio` joins its two vertices. Rows above top_y (the lamp crease under the lamp, the body line's top row along the
    side) are ONE top row. Returns [(s, y, d) arrays sorted by s], bottom row first."""
    kk = np.round(Vb / 1e-6).astype(np.int64); kid = {}
    wid = np.array([kid.setdefault(tuple(k), i) for i, k in enumerate(kk)])
    S = to_sbd(Sp, arc, Vb); left = Vb[:, 0] > -1e-6
    par = {}
    def find(x):
        while par.setdefault(x, x) != x: par[x] = par[par[x]]; x = par[x]
        return x
    for f in wid[Fb]:
        best = None
        for a_, b_ in ((0, 1), (1, 2), (2, 0)):
            a_, b_ = int(f[a_]), int(f[b_])
            if not (left[a_] and left[b_]): continue
            ds, dy = abs(S[a_, 0] - S[b_, 0]), abs(S[a_, 1] - S[b_, 1])
            if ds < 0.003: continue
            if best is None or dy / ds < best[0]: best = (dy / ds, a_, b_)
        if best is not None and best[0] < ratio: par[find(best[1])] = find(best[2])
    groups = {}
    for v in set(wid[np.unique(Fb)].tolist()):
        if left[v]: groups.setdefault(find(v), []).append(v)
    rows = [np.array(g) for g in groups.values() if len(g) >= 3]
    top = [r for r in rows if np.median(S[r, 1]) > top_y]
    rows = [r for r in rows if np.median(S[r, 1]) <= top_y] + ([np.concatenate(top)] if top else [])
    out = []
    for r in sorted(rows, key=lambda r: np.median(S[r, 1])):
        Q = S[r]; Q = Q[np.argsort(Q[:, 0])]; Q[:, 1] = np.minimum(Q[:, 1], Y_TOP); out.append(Q)
    return out


def vertex_rows_track(Vb, Fb, Sp, arc, tol=1.0e-3, top_y=0.6065, min_n=8):
    """Kunos's vertex ROWS by continuity along the spine: vertices sorted by s, each joins the row whose height,
    extrapolated from its last two vertices, it continues within `tol` (rows 2.5 mm apart: the knee is THREE rows,
    582 / 584 / 587 at the rear, 579 / 581 / 584 on the side; tracing by triangle row edges swapped them round the
    corner, fair curves through the mix missed by 1.3 mm). Rows above top_y = one top row. Bottom row first."""
    u = np.unique(Fb); X = Vb[u]; X = X[X[:, 0] > -1e-6]
    S = to_sbd(Sp, arc, X)
    S = np.unique(np.round(S, 6), axis=0); S = S[np.argsort(S[:, 0])]
    tracks = []
    for p_ in S:
        best = None
        for tr in tracks:
            if p_[0] - tr[-1][0] < 0.003: continue                       # one vertex per row at a station
            if len(tr) >= 2:
                sl = (tr[-1][1] - tr[-2][1]) / max(tr[-1][0] - tr[-2][0], 1e-3); sl = float(np.clip(sl, -0.08, 0.08))
            else: sl = 0.0
            e = abs(p_[1] - (tr[-1][1] + sl * (p_[0] - tr[-1][0])))
            tol_ = tol if 0.565 < p_[1] < 0.595 else float(os.environ.get('RB_TRACK_TOL', 2.5)) * 1e-3   # tight only in the knee's 3 rows
            if e < tol_ and (best is None or e < best[0]): best = (e, tr)
        if best is None: tracks.append([p_])
        else: best[1].append(p_)
    rows = [np.array(tr) for tr in tracks if len(tr) >= min_n]
    top = [r for r in rows if np.median(r[:, 1]) > top_y]
    rows = [r for r in rows if np.median(r[:, 1]) <= top_y]
    if top:
        Tq = np.concatenate(top); Tq = Tq[np.argsort(Tq[:, 0])]; rows.append(Tq)
    out = []
    for Q in sorted(rows, key=lambda r: np.median(r[:, 1])):
        Q = Q.copy(); Q[:, 1] = np.minimum(Q[:, 1], Y_TOP); out.append(Q)
    return out


def vertex_rows_mutual(Vb, Fb, Sp, arc, ratio=0.25, top_y=0.6065, min_n=8):
    """Kunos's vertex ROWS from the strip mesh's topology: for every vertex its row neighbour AHEAD (the mesh edge
    with ds > 3 mm and the smallest |dy| / ds) and BEHIND (same, ds < -3 mm); two vertices are linked only when they
    pick each other (mutual), so diagonals never join two rows - the knee is three rows 2.5 mm apart (582 / 584 / 587
    at the rear) and continuity tracking swapped them across the corner's long gaps. Chains = rows; rows above top_y
    (lamp crease, body line top) = one top row. Bottom row first, (s, y, d) arrays."""
    kk = np.round(Vb / 1e-6).astype(np.int64); kid = {}
    wid = np.array([kid.setdefault(tuple(k), i) for i, k in enumerate(kk)])
    S = to_sbd(Sp, arc, Vb); left = Vb[:, 0] > -1e-6
    nb = {}
    for f in wid[Fb]:
        for a_, b_ in ((0, 1), (1, 2), (2, 0)):
            a_, b_ = int(f[a_]), int(f[b_])
            if left[a_] and left[b_]: nb.setdefault(a_, set()).add(b_); nb.setdefault(b_, set()).add(a_)
    def pick(v, sgn):
        best = None
        for n in nb.get(v, ()):
            ds = (S[n, 0] - S[v, 0]) * sgn
            if ds < 0.003: continue
            r = abs(S[n, 1] - S[v, 1]) / ds
            if r < ratio and (best is None or r < best[0]): best = (r, n)
        return None if best is None else best[1]
    ahead = {v: pick(v, 1) for v in nb}; behind = {v: pick(v, -1) for v in nb}
    nxt = {v: n for v, n in ahead.items() if n is not None and behind.get(n) == v}
    has_prev = set(nxt.values())
    rows = []
    for v in nb:
        if v in has_prev: continue
        ch = [v]
        while ch[-1] in nxt: ch.append(nxt[ch[-1]])
        if len(ch) >= min_n: rows.append(S[ch])
    top = [r for r in rows if np.median(r[:, 1]) > top_y]
    rows = [r for r in rows if np.median(r[:, 1]) <= top_y]
    if top:
        Tq = np.concatenate(top); Tq = Tq[np.argsort(Tq[:, 0])]; rows.append(Tq)
    out = []
    for Q in sorted(rows, key=lambda r: np.median(r[:, 1])):
        Q = Q[np.argsort(Q[:, 0])].copy(); Q[:, 1] = np.minimum(Q[:, 1], Y_TOP); out.append(Q)
    return out


def rounded_polyline(Q, a=0.004, n=12):
    """the polyline through Q (k x 3) with a G1 round at every interior point: straight between the points (Kunos's flat
    facets between its rows), a quadratic Bezier from a before to a after each corner (a capped at 0.45 x the shorter
    neighbouring segment: the knee's rows are 2.5 mm apart). Dense points along it."""
    out = [Q[0]]
    for i in range(1, len(Q) - 1):
        u0 = Q[i] - Q[i - 1]; l0 = np.linalg.norm(u0); u1 = Q[i + 1] - Q[i]; l1 = np.linalg.norm(u1)
        r = min(a, 0.45 * l0, 0.45 * l1)
        A_, B_ = Q[i] - r * u0 / l0, Q[i] + r * u1 / l1
        out += list(np.linspace(out[-1], A_, n)[1:])
        tt = np.linspace(0, 1, n)[1:, None]
        out += list((1 - tt) ** 2 * A_ + 2 * tt * (1 - tt) * Q[i] + tt ** 2 * B_)
    out += list(np.linspace(out[-1], Q[-1], n)[1:])
    return np.array(out)


def catmull_rom(Q, n_seg):
    """centripetal Catmull-Rom through the points Q (k x 3): C1, no overshoot / cusps between unevenly spaced rows;
    n_seg samples per segment (the points themselves included): (k - 1) * n_seg + 1 points"""
    P = np.r_[[2 * Q[0] - Q[1]], Q, [2 * Q[-1] - Q[-2]]]
    t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1) ** float(os.environ.get('RB_CR_ALPHA', 0.5)))]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1:i + 3]; t0, t1, t2, t3 = t[i - 1:i + 3]
        for u in np.linspace(t1, t2, n_seg + 1)[:-1] if i < len(P) - 3 else np.linspace(t1, t2, n_seg + 1):
            A1 = (t1 - u) / (t1 - t0) * p0 + (u - t0) / (t1 - t0) * p1
            A2 = (t2 - u) / (t2 - t1) * p1 + (u - t1) / (t2 - t1) * p2
            A3 = (t3 - u) / (t3 - t2) * p2 + (u - t2) / (t3 - t2) * p3
            B1 = (t2 - u) / (t2 - t0) * A1 + (u - t0) / (t2 - t0) * A2
            B2 = (t3 - u) / (t3 - t1) * A2 + (u - t1) / (t3 - t1) * A3
            out.append((t2 - u) / (t2 - t1) * B1 + (u - t1) / (t2 - t1) * B2)
    return np.array(out)


def row_loft(Fb, Vb, Sp, arc, s0, s1, verbose=True):
    """the band LOFTED through Kunos's vertex rows (24 Nov, curves first): rows from the strip mesh's topology
    (vertex_rows_mutual), each one fair curve (y(s), d(s)) over its OWN stretch (Kunos's mesh changes topology at the
    corner: a knee row ends at s 711 and another starts at 769, the body line / top rows hand over between 630 and
    770); at every station the profile = a centripetal Catmull-Rom spline through the rows PRESENT there (all lie on
    one surface), resampled by height: top -> knee zone, the knee zone (+-RB_KZ mm round the middle knee row) at
    1 mm, knee zone -> bottom; every station the same column counts (one structured grid).
    Kunos's band is low-poly (rows 2.5-30 mm apart, long flat triangles between them, shaded smooth by its normals):
    sections through it gave a kinked, blotchy profile; one smooth surface through so few vertices missed by 7 mm."""
    rows = vertex_rows_mutual(Vb, Fb, Sp, arc, min_n=3, top_y=9.0)
    rows = [Q for Q in rows if Q[-1, 0] > s0 - 0.02 and Q[0, 0] < s1 + 0.02]
    fits = []
    for Q in rows:
        L = Q[-1, 0] - Q[0, 0]; dom = [Q[0, 0] - 0.02, Q[-1, 0] + 0.02]
        n_ = int(np.clip(L / float(os.environ.get('RB_ROW_DS', 0.03)), 2, 40))
        if len(Q) < 4 or n_ < 4:                                          # a short row: a straight / gentle piece
            c = np.polyfit(Q[:, 0], Q[:, 1:], min(len(Q) - 1, 2))
            fits.append((dom, lambda s, c=c: np.c_[np.polyval(c[:, 0], s), np.polyval(c[:, 1], s)]))
        else:
            fy = PF.fit_func(Q[:, 0], Q[:, 1], dom, tol=0.3e-3, nmax=n_); fd = PF.fit_func(Q[:, 0], Q[:, 2], dom, tol=0.3e-3, nmax=n_)
            fits.append((dom, lambda s, fy=fy, fd=fd: np.c_[PF.eval_func(fy, s), PF.eval_func(fd, s)]))
    if verbose: print(f'loft: {len(rows)} rows (' + ', '.join(f'{np.median(Q[:, 1]) * 1e3:.0f}' for Q in rows) + ')', flush=True)
    ss = np.linspace(s0, s1, max(2, int(np.ceil((s1 - s0) / STEP))) + 1)
    P, T_, O = frame_at(Sp, arc, ss); up = np.array([0.0, 1.0, 0.0])
    kz = float(os.environ.get('RB_KZ', 4.5)) * 1e-3
    n_top, n_k, n_bot = int(os.environ.get('RB_NTOP', 7)), int(os.environ.get('RB_NK', 10)), int(os.environ.get('RB_NBOT', 17))
    G = []
    for i, s_ in enumerate(ss):
        pts = [f(np.array([s_]))[0] for dom, f in fits if dom[0] <= s_ <= dom[1]]
        pts = np.array(sorted(pts, key=lambda q: -q[0]))                    # (y, d), top first
        keep = np.r_[True, np.abs(np.diff(pts[:, 0])) > 8e-4]; pts = pts[keep]
        pts[:, 0] = np.minimum(pts[:, 0], Y_TOP)
        Q = P[i] + pts[:, :1] * up + pts[:, 1:] * O[i]
        C = catmull_rom(Q, 20)
        ky = [y for y in pts[:, 0] if 0.565 < y < 0.595]
        yk = float(np.median(ky)) if ky else float(np.median(pts[:, 0]))
        y_top, y_bot = C[0, 1], C[-1, 1]
        hs = np.r_[np.linspace(y_top, yk + kz, n_top, endpoint=False), np.linspace(yk + kz, yk - kz, n_k, endpoint=False),
                   np.linspace(yk - kz, y_bot, n_bot)]
        # the spline is single-valued in height here (the profile only climbs from the bottom edge to the top)
        o = np.argsort(C[:, 1]); yv = C[o, 1]
        G.append(np.c_[[np.interp(hs, yv, C[o, c]) for c in range(3)]].T)
    G = np.array(G)
    if verbose: print(f'loft: {G.shape[0]} stations x {G.shape[1]} columns (knee zone +-{kz * 1e3:.1f} mm at {2 * kz / n_k * 1e3:.1f} mm)', flush=True)
    return G


CLASSES = (('bottom', 0.0, 0.513), ('foot', 0.513, 0.527), ('mid', 0.540, 0.562), ('body', 0.598, 0.6065), ('top', 0.6065, 9.0))


def class_loft(Fb, Vb, Sp, arc, s0, s1, verbose=True):
    """the band lofted through FAIR LINES (design intent, 24 Nov): Kunos's vertex rows (topology, vertex_rows_mutual)
    grouped by kind - bottom edge, foot line, middle row, body line, top - and each kind ONE fair curve (y(s), d(s))
    through all its rows' vertices (rows hand over at the corner: one curve, no jump). The KNEE = the mid-line of the
    two knee rows that run the whole stretch, a CRISP crease (its three rows 2.5 mm apart wobble ~1 mm in depth: lofted
    through them the knee twisted and dashed in grey). Per station: lower face = Catmull-Rom knee -> mid -> foot ->
    bottom, upper face = top -> body -> knee, meeting at the knee with a corner; columns by height, knee on a column."""
    rows = vertex_rows_mutual(Vb, Fb, Sp, arc, min_n=3, top_y=9.0)
    rows = [Q for Q in rows if Q[-1, 0] > s0 - 0.02 and Q[0, 0] < s1 + 0.02]
    dom = [s0 - 0.12, s1 + 0.12]
    nmax = int(np.clip((s1 - s0) / float(os.environ.get('RB_ROW_DS', 0.03)), 4, 40))
    def fair(Q, tol=0.3e-3, n=None):
        Q = Q[np.argsort(Q[:, 0])]
        fy = PF.fit_func(Q[:, 0], Q[:, 1], dom, tol=tol, nmax=n or nmax); fd = PF.fit_func(Q[:, 0], Q[:, 2], dom, tol=tol, nmax=n or nmax)
        return fy, fd
    curves = {}
    for nm, lo, hi in CLASSES:
        sel = [Q for Q in rows if lo <= np.median(Q[:, 1]) < hi]
        if not sel: continue
        Q = np.concatenate(sel); Q[:, 1] = np.minimum(Q[:, 1], Y_TOP)
        curves[nm] = fair(Q)
        if verbose: print(f'{nm:6s}: {len(sel)} rows, {len(Q)} vertices, fair curve p95 {curves[nm][0]["err"] * 1e3:.2f} (y) / {curves[nm][1]["err"] * 1e3:.2f} (d) mm', flush=True)
    kn = sorted([Q for Q in rows if 0.565 <= np.median(Q[:, 1]) < 0.592], key=lambda Q: -(Q[-1, 0] - Q[0, 0]))[:2]
    ROUND = float(os.environ.get('RB_KNEE_A', 2.6)) * 1e-3
    if ROUND > 0:
        # Kunos's knee = a 5 mm round of three rows 2.5 mm apart (the middle one 0.3-0.5 mm proud): the two rows that
        # run the whole stretch are always its lower and MIDDLE rows -> the middle row is the apex line; the round =
        # the profile spline through points ROUND along each face from it (constant width, no row wobble)
        kn = sorted(kn, key=lambda Q: np.median(Q[:, 1]))                  # [lower row A, middle row B]
        # 24 Nov: the topology rows CROSS-LINK at Kunos's mesh gap (s 381 -> 438): rear rows 582 / 584 / 587, side rows
        # 579 / 581 / 584 - mutual linking joined rear 582 to side 581 (a 0.6 mm RISE where the knee drops 1.6 mm) and
        # the upper rear row / lower side row were left as stubs (C was guessed as 2B - A, ~1 mm off). Every station
        # has exactly THREE knee vertices: rank them by height per station -> the three real rows lower / middle / upper
        Kv = np.concatenate([Q for Q in rows if 0.555 < np.median(Q[:, 1]) < 0.600])
        Kv = Kv[np.argsort(Kv[:, 0])]
        cl = np.split(Kv, np.where(np.diff(Kv[:, 0]) > 0.003)[0] + 1)
        cl = [c[np.argsort(c[:, 1])] for c in cl if len(c) == 3]
        if len(cl) >= 6 and os.environ.get("RB_KNEE3", "1") == "1":
            kn = [np.array([c[j] for c in cl]) for j in range(3)]
    kf = [fair(Q, n=int(os.environ.get('RB_KNEE_N', 14))) for Q in kn]
    if verbose: print(f'knee: {"apex row" if ROUND > 0 else "mid-line of the 2 longest rows"} (' + ', '.join(f'{np.median(Q[:, 1]) * 1e3:.0f} s {Q[0, 0] * 1e3:.0f}..{Q[-1, 0] * 1e3:.0f}' for Q in kn) + ')' + (f', round +-{ROUND * 1e3:.1f} mm' if ROUND > 0 else ''), flush=True)
    ev = lambda c, s: np.array([PF.eval_func(c[0], [s])[0], PF.eval_func(c[1], [s])[0]])
    ss = np.linspace(s0, s1, max(2, int(np.ceil((s1 - s0) / STEP))) + 1)
    P, T_, O = frame_at(Sp, arc, ss); up = np.array([0.0, 1.0, 0.0])
    n_up, n_lo = int(os.environ.get('RB_NUP', 9)), int(os.environ.get('RB_NLO', 19))
    def by_height(C, n):
        o = np.argsort(C[:, 1]); h = np.linspace(C[0, 1], C[-1, 1], n)
        return np.c_[[np.interp(h, C[o, 1], C[o, c]) for c in range(3)]].T
    G = []
    for i, s_ in enumerate(ss):
        pt = lambda yd: P[i] + yd[0] * up + yd[1] * O[i]
        K = pt(np.mean([ev(c, s_) for c in kf], axis=0)) if ROUND <= 0 else pt(ev(kf[1], s_))
        upr = [pt(ev(curves[k], s_)) for k in ('top', 'body') if k in curves] + [K]
        low = [K] + [pt(ev(curves[k], s_)) for k in ('mid', 'foot', 'bottom') if k in curves]
        if ROUND > 0:
            # the knee LAND: Kunos's three knee rows 2.5 mm apart at one depth (a narrow, nearly vertical land between
            # the slanted faces); A, B = the two long rows (fair curves), the upper edge C = B + (B - A)
            A_ = pt(ev(kf[0], s_)); B_ = pt(ev(kf[1], s_)); C_ = pt(ev(kf[2], s_)) if len(kf) > 2 else 2 * B_ - A_
            if verbose and os.environ.get('RB_KDBG') and (i % 8 == 0 or i == len(ss) - 1): print(f'  s {s_ * 1e3:.0f}: knee y/d ' + ' '.join(f'{ev(c, s_)[0] * 1e3:.1f}/{ev(c, s_)[1] * 1e3:.1f}' for c in kf), flush=True)
            Pa, Pb = C_, A_
            pts_ = np.array(upr[:-1] + [C_, B_, A_] + low[1:])
            C = rounded_polyline(pts_, a=float(os.environ.get('RB_FILLET', 4.0)) * 1e-3) if os.environ.get('RB_PROFILE', 'spline') == 'polyline' else catmull_rom(pts_, 20)
            o = np.argsort(C[:, 1]); yv = C[o, 1]
            n_k = int(os.environ.get('RB_NK', 7))
            hs = np.r_[np.linspace(C[0, 1], Pa[1], n_up, endpoint=False), np.linspace(Pa[1], Pb[1], n_k, endpoint=False), np.linspace(Pb[1], C[-1, 1], n_lo)]
            G.append(np.c_[[np.interp(hs, yv, C[o, c]) for c in range(3)]].T)
            continue
        Cu = catmull_rom(np.array(upr), 20); Cl = catmull_rom(np.array(low), 20)
        G.append(np.r_[by_height(Cu, n_up), by_height(Cl, n_lo)[1:]])
    G = np.array(G)
    if verbose: print(f'loft: {G.shape[0]} stations x {G.shape[1]} columns, knee column {n_up - 1}', flush=True)
    return G


def build(car, out):
    import bumper_build as BB, hatch_build as HB
    V, F, N, B = candidates(car)
    # the band: candidates cut at Y_TOP (keep y <= Y_TOP)
    Vb, Fb, Nb = BB.clip_tris(V, B, N, np.array([0.0, Y_TOP, 0.0]), np.array([0.0, 1.0, 0.0]), 0.0)
    T = Vb[Fb]; A_ = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2
    print(f'band: {len(B)} Kunos triangles -> {len(Fb)} after the cut at y {Y_TOP:.4f}; area {A_ * 1e4:.0f} cm2; '
          f'x {Vb[:, 0].min():.3f}..{Vb[:, 0].max():.3f} z {Vb[:, 2].min():.3f}..{Vb[:, 2].max():.3f}', flush=True)
    Sp, arc, err = spine(spine_points(Vb, Fb))
    print(f'spine: {arc[-1] * 1e3:.0f} mm (left half), fit max {err * 1e3:.2f} mm', flush=True)
    # sweep from X0: the spine cut there, arcs from 0
    i0 = int(np.argmax(Sp[:, 0] >= X0)); Sp2 = Sp[i0:]; arc2 = arc[i0:] - arc[i0]
    LINES = os.environ.get('RB_METHOD', 'sections') == 'lines'   # lines-first (door method): in test, 24 Nov
    BB.YCOLS = (0,) if os.environ.get('RB_YCOLS', '1') == '1' else ()
    BB.BRIDGE = 0.0
    pcs = [Fb]
    R0, _ = BB.station_rows(Vb, pcs, [0], Sp2, arc2, 0.1, [3], verbose=False)
    w = float(np.median([np.linalg.norm(np.diff(r, axis=0), axis=1).sum() for r in R0]))
    ncol = int(np.clip(round(w * 1e3 / float(os.environ.get('RB_MMCOL', 4.0))) + 1, 5, 40))
    knee_mode = os.environ.get('RB_KNEE', '1') == '1'
    R, A = BB.station_rows(Vb, pcs, [0], Sp2, arc2, STEP, [400 if knee_mode else ncol], anchor_band=0)
    if knee_mode:
        R, kcol = knee_rows(R, ncol)
        R_knee = R[:, kcol].copy()                        # on Kunos's crease edges (before any PN lift)
        print(f'knee: one grid line per station (rows resampled top -> knee -> bottom by height, knee column {kcol})', flush=True)
    # stop at the last station whose run still spans the band's height (towards the arch the section is cut short)
    hgt = R[:, :, 1].max(1) - R[:, :, 1].min(1)
    ok = hgt > float(os.environ.get('RB_HFRAC', 0.85)) * np.median(hgt)
    last = len(ok) if ok.all() else int(np.argmin(ok))
    R, A = R[:last], A[:last]
    print(f'profile {w * 1e3:.0f} mm, {ncol} columns (by height); {len(R)} full stations to {A[-1] * 1e3:.0f} mm of {arc2[-1] * 1e3:.0f}', flush=True)
    if os.environ.get('RB_PN', '1') == '1':
        cdeg = float(os.environ.get('RB_PN_CREASE', 0))   # crease-aware corner normals: tried 24 Nov, the face then followed the facets (streaks)
        R = BB.pn_lift(Vb, Fb, Nb, R, Nc=corner_normals(Vb, Fb, cdeg) if cdeg > 0 else None)
    anchor = kcol if knee_mode else ncol // 2
    fsm, nrms, nmax_, lam = HB.smooth_rows_local(A, R, spacing=float(os.environ.get('RB_SPACING', 0.03)), col=anchor,
                                                 nrm_rms=float(os.environ.get('RB_NRMS', 0.1)) * 1e-3, nrm_p99=float(os.environ.get('RB_NP99', 0.4)) * 1e-3)
    a_e = np.linspace(0, A[-1], max(2, int(np.ceil(A[-1] / STEP))) + 1)
    G = fsm(a_e)
    print(f'grid {G.shape[0]} rows x {G.shape[1]}: smoothing lambda {lam:.0e}, normal rms {nrms * 1e3:.3f} max {nmax_ * 1e3:.2f} mm', flush=True)
    res = []
    nb = Nb[np.unique(Fb)].mean(0); nb /= np.linalg.norm(nb)
    if os.environ.get('RB_METHOD', 'rows') == 'rows':
        # the swept stretch LOFTED through Kunos's vertex rows (curves first, the door / pillar way); the section rows
        # above only fix the stretch's extent and its end planes
        i0f = int(np.argmax(Sp[:, 0] >= X0))
        G = (class_loft if os.environ.get('RB_LOFT', 'classes') == 'classes' else row_loft)(Fb, Vb, Sp, arc, arc[i0f] + float(A[0]), arc[i0f] + float(A[-1]))
        res.append(dict(name='rband:sL', maxlen=float(os.environ.get('RB_MAXLEN', 6)), structured=True, grid=(G * 1000).tolist(),
                        frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0], nb.tolist()]))
        res.append(dict(name='rband:sR', mirror_of='rband:sL'))
    elif LINES:
        # the swept stretch rebuilt the door way (vertices -> smooth bands between fair lines); the section rows above
        # only fix the stretch's extent (first / last full station) and the end planes
        Glo, Gup = lines_sweep(Fb, Vb, Sp2, arc2, float(A[0]), float(A[-1]), knee_pts=R_knee[:last] if knee_mode else None)
        G = np.concatenate([Glo, Gup[:, 1:]], axis=1)[:, ::-1]                       # top first, as the section rows
        for nm_, Gk in (('lo', Glo), ('up', Gup)):
            res.append(dict(name=f'rband:{nm_}L', maxlen=float(os.environ.get('RB_MAXLEN', 6)), structured=True, grid=(Gk * 1000).tolist(),
                            frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0], nb.tolist()]))
            res.append(dict(name=f'rband:{nm_}R', mirror_of=f'rband:{nm_}L'))
    else:
        res.append(dict(name='rband:sL', maxlen=float(os.environ.get('RB_MAXLEN', 6)), structured=True, grid=(G * 1000).tolist(),
                        frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0], nb.tolist()]))
        res.append(dict(name='rband:sR', mirror_of='rband:sL'))

    def region(sel, planes, margin=3e-3):
        """band triangles of a region, clipped `margin` past each plane (Kunos's long triangles straddle it)"""
        Fr = Fb[sel]; Vr, Nr = Vb, Nb
        for m_, n_ in planes:
            Vr, Fr, Nr = BB.clip_tris(Vr, Fr, Nr, m_, n_, margin)
        return Vr, Fr, Nr

    # centre: the narrow strip under the plate panel (|x| < XT, full width) + a TRANSITION face each side (XT..X0,
    # left; right = mirror) where the band's top edge climbs from y 534 to 608 (the plate panel's end, x 0.29-0.32):
    # one face over both missed Kunos by up to 1.9 mm there. Internal cuts get OVERLAP data (Kunos triangles clipped
    # 15 mm past the plane) so the two faces agree across it; the sweep's first rows are the transition's data.
    m0, n0 = plane_of(G[0], G[0].mean(0) - np.array([1.0, 0, 0]))        # normal towards the centre
    n0c = -n0                                                             # cut_planes removes the side the normal points into
    cen = Vb[Fb].mean(1); XT = float(os.environ.get('RB_XT', 0.285)); OV = float(os.environ.get('RB_OVERLAP', 0.015))
    ex, ey = np.array([1.0, 0, 0]), np.array([XT, 0, 0])
    if os.environ.get('RB_TRANS', '1') == '1':
        Vc, Fc, Nc = region(np.abs(cen[:, 0]) < XT + 0.05, [(ey, ex), (ey * MIR, -ex)], margin=OV)
        e = PF.fit_panel('rband:c', Vc, Fc, Nc)
        e['cut_planes'] = [[(ey * 1000).tolist(), ex.tolist()], [((ey * MIR) * 1000).tolist(), (-ex).tolist()]]
        res.append(e)
        Vt, Ft, Nt = region((cen[:, 0] > XT - 0.05) & (cen[:, 0] < X0 + 0.05), [(ey, -ex), (m0, -n0)], margin=OV)
        e = PF.fit_panel('rband:tL', Vt, Ft, Nt, extra=G[:3].reshape(-1, 3), extra_rep=3)
        e['cut_planes'] = [[(ey * 1000).tolist(), (-ex).tolist()], [(m0 * 1000).tolist(), n0c.tolist()]]
        res.append(e); res.append(dict(name='rband:tR', mirror_of='rband:tL'))
        print(f'centre strip |x| < {XT * 1e3:.0f} mm ({len(Fc)} tris) + transition faces to the sweep start x {abs(m0[0]) * 1e3:.0f} ({len(Ft)} tris)', flush=True)
    else:
        Vc, Fc, Nc = region(np.abs(cen[:, 0]) < X0 + 0.03, [(m0, -n0), (m0 * MIR, -(n0 * MIR))])
        X = G[:3].reshape(-1, 3); X = np.r_[X, X * MIR]
        e = PF.fit_panel('rband:c', Vc, Fc, Nc, extra=X, extra_rep=3)
        e['cut_planes'] = [[(m0 * 1000).tolist(), n0c.tolist()], [((m0 * MIR) * 1000).tolist(), (n0c * MIR).tolist()]]
        res.append(e)
        print(f'centre strip: {len(Fc)} triangles, cut on the sweep start planes x +-{abs(m0[0]) * 1e3:.0f} mm', flush=True)

    # end face at the arch (left; right = mirror): past the last full station's plane
    m1, n1 = plane_of(G[-1], G[-2].mean(0))                               # normal back into the sweep
    cv = (Vb[Fb] - m1) @ n1
    sel = (cv.min(1) < -1e-4) & (cen[:, 0] > 0)
    if sel.sum() >= 2:
        Ve, Fe, Ne = region(sel, [(m1, n1)])
        comps = PF.components(Ve, Fe)[0]; Fe = max(comps, key=len)
        e = PF.fit_panel('rband:eL', Ve, Fe, Ne, extra=G[-3:].reshape(-1, 3), extra_rep=3)
        e['cut_planes'] = [[(m1 * 1000).tolist(), n1.tolist()]]
        res.append(e); res.append(dict(name='rband:eR', mirror_of='rband:eL'))
        print(f'end face: {len(Fe)} triangles past the last station (z {m1[2] * 1e3:.0f})', flush=True)
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'band_grid.npz'), grid=G, rows=R, arcs=A)
    print('saved', os.path.join(out, 'panels_fit.json'))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
