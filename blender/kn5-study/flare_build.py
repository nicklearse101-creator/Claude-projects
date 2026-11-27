"""The front wing's wheel-arch FLARE, built curves first (27 Nov).

Kunos's flare (GEO_body piece 0 round the front arch) is a low-poly band whose vertex ROWS run round the arch at a
near-constant distance d in from the opening edge (side view): the edge (d 0), a flat top face to a crisp INNER round
(three rows ~3.5 mm apart, d 22-35), a straight wall down to an OUTER round (three rows, d 50-77) into the wing's skin.
At the arch top it stands 45 mm proud of the skin (x 809 -> 764). The wing's panel fit had it as one smooth surface
85 mm wide (fit p95 2.6 mm): both rounds soft, a rounded tube in grey.

Now: arch coordinates (a = arc length along a fair side-view curve through the edge vertices, d = distance in from it
along its normal), Kunos's rows found per COLUMN (vertices at one a, ranked by d inside the inner / outer band), each
row one curve through its vertices; per station a profile edge -> straight top face -> inner round -> straight wall ->
outer round (Hermite segments, tangent to the straight spans: G1, exact through every row) -> one structured grid.
    python flare_build.py CAR_DIR OUT_DIR"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panel_fit as PF

BOX = dict(x=0.5, z=(0.62, 1.8), y=0.15)                 # the left front wing (GEO_body)
INNER = (float(os.environ.get('FL_INLO', 0.008)), 0.045)                                   # d bands of the inner / outer round's rows (m)
OUTER = (0.045, 0.082)
A_RANGE = tuple(float(v) for v in os.environ.get('FL_A', '0.006,0.805').split(','))   # stations (m along the edge)


def region(car):
    V, F, N = PF.load_mesh(car, 'GEO_body', raw=True)
    c = V[F].mean(1)
    m = (c[:, 0] > BOX['x']) & (c[:, 2] > BOX['z'][0]) & (c[:, 2] < BOX['z'][1]) & (c[:, 1] > BOX['y'])
    return V, F[m], N


def weld(V):
    kk = np.round(V / 1e-6).astype(np.int64)
    _, wid = np.unique(kk, axis=0, return_inverse=True); wid = wid.ravel()
    rep = np.zeros(wid.max() + 1, int); rep[wid] = np.arange(len(wid))
    return wid, rep


def edge_chain(V, Fw, wid, rep):
    """the arch opening's boundary vertices in order, front end first (3D, m)"""
    G = wid[Fw]; E = np.sort(np.r_[G[:, [0, 1]], G[:, [1, 2]], G[:, [2, 0]]], 1)
    u, cnt = np.unique(E, axis=0, return_counts=True); be = u[cnt == 1]
    Pm = V[rep[be]].mean(1); r = np.hypot(Pm[:, 2] - 1.2, Pm[:, 1] - 0.33)
    be = be[(r < 0.42) & (Pm[:, 1] > 0.18)]
    adj = {}
    for a, b in be: adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    ends = [v for v, n in adj.items() if len(n) == 1]
    ch = [max(ends, key=lambda v: V[rep[v], 2])]; prev = None
    while True:
        nx = [n for n in adj[ch[-1]] if n != prev]
        if not nx: break
        prev = ch[-1]; ch.append(nx[0])
    ch = np.array(ch); Q = V[rep[ch]]
    # the arch proper starts after the front corner (the edge's run along the bumper top turns 90 deg up into the arch
    # there): from the last sharp turn (> 40 deg) in the first third of the chain
    P2 = Q[:, [2, 1]]; turn = np.zeros(len(Q))
    for i in range(1, len(Q) - 1):
        u_, v_ = P2[i] - P2[i - 1], P2[i + 1] - P2[i]
        turn[i] = np.degrees(np.arccos(np.clip(u_ @ v_ / (np.linalg.norm(u_) * np.linalg.norm(v_) + 1e-12), -1, 1)))
    k = [i for i in range(1, len(Q) // 3) if turn[i] > 40]
    i0 = k[-1] if k else 0
    # ... and it ends at the bottom corner (the edge turns along the sill there): up to the first sharp turn in the last third
    k = [i for i in range(len(Q) - 2, 2 * len(Q) // 3, -1) if turn[i] > 40]
    i1 = k[-1] + 1 if k else len(Q)
    return ch[i0:i1], Q[i0:i1]


class Edge:
    """fair side-view (z, y) curve through the edge vertices, arc-length parameter a; normal En into the panel"""
    def __init__(self, Q):
        # centripetal Catmull-Rom THROUGH the edge vertices (C1; a smoothing fit dropped the corner ones as outliers)
        import rearband_build as RB
        C = RB.catmull_rom(Q[:, [2, 1]], 200)
        L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
        self.t, self.L, self.C = L, L, C
        self.length = float(L[-1])
        print(f'edge: {len(Q)} vertices, Catmull-Rom through them, length {self.length * 1e3:.0f} mm', flush=True)
        # station directions: the edge's normal SMOOTHED along it (Gaussian, sigma SIG): the raw tangent swings at tight
        # vertex clusters (the body crease's three edge vertices 1.2 mm apart) and neighbouring station lines crossed
        # 20-60 mm in (a fold across the flare)
        tg = np.c_[np.gradient(C[:, 0]), np.gradient(C[:, 1])]
        ph = np.unwrap(np.arctan2(tg[:, 1], tg[:, 0]))
        sig = float(os.environ.get('FL_SIG', 0.010)); ds_ = np.median(np.diff(L))
        h = int(np.ceil(3 * sig / ds_)); kern = np.exp(-0.5 * (np.arange(-h, h + 1) * ds_ / sig) ** 2); kern /= kern.sum()
        php = np.r_[np.full(h, ph[0]), ph, np.full(h, ph[-1])]
        ph = np.convolve(php, kern, mode='valid')
        n = np.c_[-np.sin(ph), np.cos(ph)]
        # into the panel = away from the arch centre
        cen = np.array([1.2, 0.33]); k = len(C) // 2
        if (C[k] - cen) @ n[k] < 0: n = -n
        self.n0 = n.copy(); self.n = n
        from scipy.spatial import cKDTree
        self.tree = cKDTree(C)

    def set_psi(self, a_s, psi_s, sig=0.015):
        """turn the station lines by psi(a) from the edge's normal (Kunos's columns' direction: at the rear they run
        along the body's horizontal lines, 11 deg off the normal); psi smoothed (Gaussian, sig) and interpolated"""
        o = np.argsort(a_s); a_s, psi_s = a_s[o], psi_s[o]
        w = np.exp(-0.5 * ((self.L[:, None] - a_s[None]) / sig) ** 2)
        ps = (w * psi_s[None]).sum(1) / np.maximum(w.sum(1), 1e-12)
        c, s_ = np.cos(ps), np.sin(ps)
        self.n = np.c_[c * self.n0[:, 0] - s_ * self.n0[:, 1], s_ * self.n0[:, 0] + c * self.n0[:, 1]]
        self.psi = ps

    def E(self, a):
        a = np.atleast_1d(a); return np.c_[np.interp(a, self.L, self.C[:, 0]), np.interp(a, self.L, self.C[:, 1])]

    def En(self, a):
        a = np.atleast_1d(a); n = np.c_[np.interp(a, self.L, self.n[:, 0]), np.interp(a, self.L, self.n[:, 1])]
        return n / np.linalg.norm(n, axis=1)[:, None]

    def ad(self, X):
        """(a, d) of points X (k x 3): the station line through them (X = E(a) + d En(a), En the smoothed normal):
        the sign change of cross(En(a), X - E(a)) next to the nearest curve point, refined linearly"""
        _, j = self.tree.query(X[:, [2, 1]]); Y = X[:, [2, 1]]
        a = np.empty(len(X)); d = np.empty(len(X)); m = len(self.C)
        for i, (y, j0) in enumerate(zip(Y, j)):
            lo, hi = max(j0 - 400, 0), min(j0 + 400, m - 1); jj = np.arange(lo, hi + 1)
            r = y - self.C[jj]; g = self.n[jj, 0] * r[:, 1] - self.n[jj, 1] * r[:, 0]
            sc = np.nonzero(np.sign(g[:-1]) != np.sign(g[1:]))[0]
            if len(sc):
                q = sc[np.argmin(np.abs(sc + lo - j0))]; f = g[q] / (g[q] - g[q + 1])
                a[i] = self.L[lo + q] + f * (self.L[lo + q + 1] - self.L[lo + q])
            else: a[i] = self.L[j0]
            e = self.E(a[i])[0]; nn = self.En(a[i])[0]; d[i] = (y - e) @ nn
        return a, d


def columns(a, d, idx, band, nb, ratio=0.5, P=None):
    """Kunos's columns across one round's band: vertices with d inside band, each linked to its mesh neighbour OUTWARD
    (d + 1.5 mm or more, smallest |da| / dd) when that one picks it back inward (mutual); chains of three = one column
    (in0, in1, in2). By a alone, the body crease that crosses the flare at the rear (three rows 1.2 mm apart, y 0.34)
    put nine vertices into one 'column'. nb: welded-vertex neighbour sets; idx: the vertices' welded ids."""
    m = (d > band[0]) & (d < band[1]); pos = {int(w): i for i, w in enumerate(idx) if m[i]}
    def pick(v, sg):
        best = None; i = pos[v]
        for n in nb.get(v, ()):
            j = pos.get(int(n))
            if j is None: continue
            dd = (d[j] - d[i]) * sg
            if dd < 0.0015: continue
            r = abs(a[j] - a[i]) / dd
            # P given: the SHORTEST such edge (Kunos's column edges are 3-4 mm, its row edges 15-30 mm; at the front end
            # the rows themselves run steeply in (a, d) and won by the ratio)
            key = r if P is None else float(np.linalg.norm(P[j] - P[i]))
            if r < ratio and (best is None or key < best[0]): best = (key, int(n))
        return None if best is None else best[1]
    out_ = {v: pick(v, 1) for v in pos}; in_ = {v: pick(v, -1) for v in pos}
    nxt = {v: n for v, n in out_.items() if n is not None and in_.get(n) == v}
    has_prev = set(nxt.values()); cols = []
    for v in pos:
        if v in has_prev: continue
        ch = [v]
        while ch[-1] in nxt: ch.append(nxt[ch[-1]])
        if len(ch) >= 3: cols.append([pos[c] for c in ch[:3]])
    return sorted(cols, key=lambda c: a[c[0]])


def rows(car, verbose=True, skew=True):
    V, Fw, N = region(car); wid, rep = weld(V)
    ch, Q = edge_chain(V, Fw, wid, rep)
    ed = Edge(Q)
    vv = np.unique(wid[Fw]); X = V[rep[vv]]
    a, d = ed.ad(X)
    if skew and os.environ.get('FL_SKEW', '1') == '1':
        # station lines along Kunos's own columns: each column chain's direction (first -> last vertex, side view)
        # against the edge's normal at it; then (a, d) again on the turned stations
        nb0 = {}
        for f in wid[Fw]:
            for i_, j_ in ((0, 1), (1, 2), (2, 0)): nb0.setdefault(int(f[i_]), set()).add(int(f[j_])); nb0.setdefault(int(f[j_]), set()).add(int(f[i_]))
        pa, pp = [], []
        for band in (INNER, OUTER):
            cols0 = columns(a, d, vv, band, nb0)
            for c in cols0:
                v_ = X[c[-1], [2, 1]] - X[c[0], [2, 1]]
                if np.linalg.norm(v_) < 0.004: continue
                n_ = ed.En(np.mean(a[c]))[0]
                pa.append(np.mean(a[c])); pp.append(np.arctan2(n_[0] * v_[1] - n_[1] * v_[0], n_ @ v_))
        pa, pp = np.array(pa), np.array(pp)
        ok = np.abs(pp) < np.radians(35)
        ed.set_psi(pa[ok], pp[ok])
        if verbose: print(f'stations along Kunos columns: {ok.sum()} column directions, turn {np.degrees(pp[ok]).min():.1f}..{np.degrees(pp[ok]).max():.1f} deg', flush=True)
        a, d = ed.ad(X)
    nb = {}
    for f in wid[Fw]:
        for i_, j_ in ((0, 1), (1, 2), (2, 0)): nb.setdefault(int(f[i_]), set()).add(int(f[j_])); nb.setdefault(int(f[j_]), set()).add(int(f[i_]))
    # each welded vertex's Kunos normal (its raw copies averaged: the flare has no hard edges)
    nsum = np.zeros((wid.max() + 1, 3)); np.add.at(nsum, wid[np.unique(Fw)], N[np.unique(Fw)])
    NX = nsum[vv]; NX /= np.maximum(np.linalg.norm(NX, axis=1), 1e-12)[:, None]
    def theta(aa, nn):
        # the normal's angle in the station plane (d along the edge's normal, x out): 0 = facing +x, + = tilted to +d
        en = ed.En(aa); return np.arctan2(nn[:, 1] * en[:, 1] + nn[:, 2] * en[:, 0], nn[:, 0])
    ae = ed.ad(Q)[0]
    from scipy.spatial import cKDTree
    NQ = NX[cKDTree(X).query(Q)[1]]
    R = {'edge': (ae, np.zeros(len(Q)), Q[:, 0], theta(ae, NQ))}
    for name, band in (('in', INNER), ('out', OUTER)):
        sel = (a > A_RANGE[0] - 0.03) & (a < A_RANGE[1] + 0.03); ii = np.nonzero(sel)[0]
        aa, dd = a[sel], d[sel]
        cols = columns(aa, np.where(aa > 5e-4, dd, -1.0), vv[ii], band, nb)     # (a clamped to 0: ahead of the corner)
        # (front end) the rounds dive into the corner on the bumper line: Kunos's columns there tilt 50-60 deg off the
        # stations (|da| / dd 1-2): chains allowed that steep in the first FRONT_A of the edge; vertices ahead of the
        # corner (a clamped to 0) are not the flare's
        fa = float(os.environ.get('FL_FRONT_A', 0.07))
        if fa > 0:
            mf = (aa < fa) & (aa > 5e-4)
            cf = columns(np.where(mf, aa, -1.0), np.where(mf, dd, -1.0), vv[ii], band, nb, ratio=2.5, P=X[ii])
            have = {tuple(c) for c in cols}
            cols = sorted(cols + [c for c in cf if tuple(c) not in have and aa[c].max() < fa], key=lambda c: aa[c[0]])
        # rows = the chains' ranks (in0 / in1 / in2 per column: right where the rounds converge into the front corner);
        # band vertices in no chain (the body crease's extra columns at the rear) go to the nearest row's level there
        # (within 1.5 mm), the levels interpolated from the chain columns
        inchain = np.zeros(len(aa), bool)
        for c in cols: inchain[c] = True
        lev = []
        for k in range(3):
            ca = np.array([aa[c[k]] for c in cols]); cd = np.array([dd[c[k]] for c in cols]); o = np.argsort(ca); lev.append((ca[o], cd[o]))
        inb = (dd > band[0] - 0.002) & (dd < band[1]) & (aa < A_RANGE[1] + 0.0015) & (aa > 5e-4) & ~inchain
        Lk = np.array([np.interp(aa, xa, xd) for xa, xd in lev])
        dist = np.abs(dd[None] - Lk); kbest = np.argmin(dist, axis=0); ok = inb & (dist.min(0) < 0.0015)
        for k in range(3):
            sel = np.r_[np.array([c[k] for c in cols], int), np.nonzero(ok & (kbest == k))[0]]
            sel = sel[aa[sel] < A_RANGE[1] + 0.0015]          # (past the end: the ledge's stacked vertices at y 0.241)
            o = np.argsort(aa[sel]); sel = sel[o]
            pa, pd, px = aa[sel], dd[sel], X[ii[sel], 0]; nn = NX[ii[sel]]
            R[f'{name}{k}'] = (pa, pd, px, theta(pa, nn))
        if verbose:
            sp = np.array([[dd[c[1]] - dd[c[0]], dd[c[2]] - dd[c[1]]] for c in cols])
            print(f'{name}: {len(cols)} columns, row spacing median {np.median(sp[:, 0]) * 1e3:.1f} / {np.median(sp[:, 1]) * 1e3:.1f} mm '
                  f'(max {sp.max() * 1e3:.1f})', flush=True)
    return ed, R, (V, Fw, N, wid, rep)


ORDER = ['edge', 'in0', 'in1', 'in2', 'out0', 'out1', 'out2']


def row_at(row, a):
    """(d, x, theta) of a row at stations a: monotone cubic (PCHIP) through its vertices as functions of a - rows are
    graphs over a; a Catmull-Rom in (a, d, x) ran backwards in a at the body crease (three vertices 1.2 mm apart after
    a 12 mm gap, x stepping 8 mm) and folded the grid"""
    from scipy.interpolate import PchipInterpolator
    ra, rd, rx, rt = row; o = np.argsort(ra); ra, rd, rx, rt = ra[o], rd[o], rx[o], rt[o]
    keep = np.r_[True, np.diff(ra) > 1e-5]; ra, rd, rx, rt = ra[keep], rd[keep], rx[keep], rt[keep]
    a = np.clip(a, ra[0], ra[-1])
    return PchipInterpolator(ra, rd)(a), PchipInterpolator(ra, rx)(a), PchipInterpolator(ra, rt)(a)


def hermite(P0, P1, t0, t1, n):
    """cubic Bezier P0 -> P1 (2D) leaving along t0 and arriving along t1 (unit), handles chord / 3: n + 1 points"""
    L = np.linalg.norm(P1 - P0); B1 = P0 + t0 * L / 3; B2 = P1 - t1 * L / 3
    u = np.linspace(0, 1, n + 1)[:, None]
    return (1 - u) ** 3 * P0 + 3 * u * (1 - u) ** 2 * B1 + 3 * u * u * (1 - u) * B2 + u ** 3 * P1


def rounded_profile(P, n=60):
    """Kunos's facet polygon P (k x 2: d, x) as a smooth G1 curve: straight along its facets, every CORNER (turn >
    corner_deg) rounded by a quadratic Bezier whose arms run the whole facet to a flat neighbour row (a holding row:
    on the face's own plane) and half of it to a neighbouring corner. Kunos's rounds are a corner vertex with a
    holding row each side (top of the arch: in0 / in1 / in2) or two corners joined by one straight facet (the rear's
    wall in2 -> out0: shaded soft by averaged normals, but straight; long arms there made an S, 1.9 mm off the corners).
    Returns dense points and, per row, its index on them (a corner row -> its round's middle)."""
    k = len(P); seg = np.diff(P, axis=0); L = np.linalg.norm(seg, axis=1); u = seg / L[:, None]
    turn = np.zeros(k)
    for i in range(1, k - 1):
        turn[i] = np.degrees(np.arccos(np.clip(u[i - 1] @ u[i], -1, 1)))
    corner = turn > 0.2
    # each facet's length shared between its two end corners in proportion to their turns (a flat holding row takes
    # none: the corner reaches all the way to it); a round's arms = the smaller share of its two facets (symmetric:
    # a straight facet between two corners keeps a straight middle). Continuous along the arch where the corner
    # moves from one row to the next (in1 -> in2 behind the arch top): an on / off corner test drew two lines there.
    sh_lo = L * turn[:-1] / np.maximum(turn[:-1] + turn[1:], 1e-9)     # facet i: the share of its start vertex i
    sh_hi = L * turn[1:] / np.maximum(turn[:-1] + turn[1:], 1e-9)      # ... and of its end vertex i + 1
    out, idx = [P[0]], [0]
    for i in range(1, k):
        if i < k - 1 and corner[i]:
            r_ = min(sh_hi[i - 1], sh_lo[i])
            A = P[i] - u[i - 1] * r_; B = P[i] + u[i] * r_
            if np.linalg.norm(A - out[-1]) > 1e-7: out.append(A)
            t = np.linspace(0, 1, n + 1)[1:, None]
            Qb = (1 - t) ** 2 * A + 2 * t * (1 - t) * P[i] + t ** 2 * B
            idx.append(len(out) + n // 2 - 1); out += list(Qb)
        else:
            if np.linalg.norm(P[i] - out[-1]) > 1e-7: out.append(P[i])
            idx.append(len(out) - 1)
    out = np.array(out)
    # dense: straight runs subdivided too (the grid resamples by arc length)
    dense, didx, j = [out[0]], [0], 0
    for q in range(1, len(out)):
        m = max(1, int(np.ceil(np.linalg.norm(out[q] - out[q - 1]) / 2e-4)))
        dense += list(out[q - 1] + (out[q] - out[q - 1]) * np.linspace(0, 1, m + 1)[1:, None])
        while j + 1 < len(idx) and idx[j + 1] == q: didx.append(len(dense) - 1); j += 1
    return np.array(dense), np.array(didx)


def grid(ed, R, step=0.005, ds=0.0012):
    """stations every step along the edge; per station the rows' facet polygon rounded at its corners
    (rounded_profile); columns per row-to-row segment fixed by its median width / ds"""
    # stations every step + at every Kunos column (the body crease at the rear is three columns 1.2 mm apart: 5 mm
    # stations smeared it into a soft patch)
    a = np.arange(A_RANGE[0], A_RANGE[1] + 1e-9, step)
    a = np.unique(np.r_[a, np.concatenate([R[k][0] for k in ORDER])])
    a = a[(a >= A_RANGE[0]) & (a <= A_RANGE[1])]
    keep = np.r_[True, np.diff(a) > 3e-4]; a = a[keep]
    D, X, T = (np.array(v) for v in zip(*[row_at(R[k], a) for k in ORDER]))       # (rows, stations)
    w = np.median(np.hypot(np.diff(D, axis=0), np.diff(X, axis=0)), axis=1)
    ncol = np.maximum(2, np.ceil(w / ds).astype(int))
    G = []
    for j, aj in enumerate(a):
        C, ci = rounded_profile(np.c_[D[:, j], X[:, j]])
        s_ = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
        pts = [C[:1]]
        for k in range(len(ci) - 1):
            t_ = np.linspace(s_[ci[k]], s_[ci[k + 1]], ncol[k] + 1)[1:]
            pts.append(np.c_[np.interp(t_, s_, C[:, 0]), np.interp(t_, s_, C[:, 1])])
        pd = np.concatenate(pts)
        e, n = ed.E(aj)[0], ed.En(aj)[0]
        G.append(np.c_[pd[:, 1], e[1] + pd[:, 0] * n[1], e[0] + pd[:, 0] * n[0]])
    return a, np.array(G), ncol


def grid_mesh(G):
    ns, nc = G.shape[:2]; ii = np.arange(ns * nc).reshape(ns, nc)
    F = np.r_[np.c_[ii[:-1, :-1].ravel(), ii[1:, :-1].ravel(), ii[1:, 1:].ravel()], np.c_[ii[:-1, :-1].ravel(), ii[1:, 1:].ravel(), ii[:-1, 1:].ravel()]]
    return G.reshape(-1, 3), F


def footprint(G):
    """the grid's outline in side view ((z, y) polygon, closed): edge row, end station, outer row back, start station"""
    E = np.r_[G[:, 0], G[-1, 1:], G[::-1, -1], G[0, ::-1][1:]]
    return E[:, [2, 1]]


def build(car, out):
    ed, R, _ = rows(car)
    a, G, ncol = grid(ed, R)
    print(f'grid: {G.shape[0]} stations (a {a[0] * 1e3:.0f}..{a[-1] * 1e3:.0f} mm) x {G.shape[1]} columns ({ncol.tolist()} per row gap)', flush=True)
    res = [dict(name='flare:L', structured=True, maxlen=float(os.environ.get('FL_MAXLEN', 4)), grid=(G * 1000).tolist(),
                frame=[[0, 0, 0], [0, 0, 1], [0, 1, 0], [1.0, 0, 0]])]
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'flare_grid.npz'), grid=G, a=a, foot=footprint(G))
    print('saved', os.path.join(out, 'panels_fit.json'), flush=True)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
