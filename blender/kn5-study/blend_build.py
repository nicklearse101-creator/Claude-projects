"""Soft-shoulder regions (research report 'Smooth region segmentation into faces'): a crease region whose cross-section
is flat face -> shoulder bend -> flat face (the AE86 C-pillar r1: top, a 63 deg shoulder over ~20 mm, side).
split_shoulder() labels the region's triangles top / shoulder / side / rest from per-station turn profiles:
sections square to the region's main axis every 5 mm; on a 'pillar-like' station (total turn 40-85 deg, section
narrower than 110 mm) the segments before 10 % of the turn are top, after 90 % side, between shoulder; each triangle
takes the majority label of the segments cut from it. Stations where the section widens (the foot fanning into the
deck) leave their triangles 'rest'. Pure numpy."""
import numpy as np

UP = np.array([0.0, 1.0, 0.0])


def _section(T, o, nrm):
    d = (T - o) @ nrm; s = np.sign(d); m = np.nonzero((s.min(1) < 0) & (s.max(1) > 0))[0]
    segs, tri = [], []
    for k in m:
        t, e = T[k], d[k]; pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if e[i] * e[j] < 0: a = e[i] / (e[i] - e[j]); pts.append(t[i] + a * (t[j] - t[i]))
        if len(pts) == 2: segs.append(pts); tri.append(k)
    return np.array(segs), np.array(tri, int)


def _chain(segs, tri):
    key = lambda p: tuple(np.round(p / 1e-6).astype(np.int64))
    adj = {}
    for k, (a, b) in enumerate(segs):
        adj.setdefault(key(a), []).append((k, 0)); adj.setdefault(key(b), []).append((k, 1))
    used = np.zeros(len(segs), bool); best = None
    for k0 in range(len(segs)):
        if used[k0]: continue
        Pp, Tt = [segs[k0][0], segs[k0][1]], [tri[k0]]; used[k0] = True
        for end in (1, 0):
            while True:
                p = Pp[-1] if end else Pp[0]
                nxt = [(k, w) for k, w in adj.get(key(p), []) if not used[k]]
                if not nxt: break
                k, w = nxt[0]; used[k] = True
                if end: Pp.append(segs[k][1 - w]); Tt.append(tri[k])
                else: Pp.insert(0, segs[k][1 - w]); Tt.insert(0, tri[k])
        if best is None or len(Pp) > len(best[0]): best = (Pp, Tt)
    return np.array(best[0]), np.array(best[1], int)


def split_shoulder(V, Fr, Nv, step=0.005, turn_rng=(40, 85), wmax=0.11, lo=0.10, hi=0.90):
    T = V[Fr]; X = V[np.unique(Fr)]; c0 = X.mean(0); es = np.linalg.svd(X - c0)[2][0]
    s = (X - c0) @ es
    votes = np.zeros((len(Fr), 3)); stations = []
    nt = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nt /= np.maximum(np.linalg.norm(nt, axis=1), 1e-12)[:, None]
    nt *= np.sign((nt * Nv[Fr].mean(1)).sum(1))[:, None]
    for sv in np.arange(s.min() + step / 2, s.max(), step):
        segs, tri = _section(T, c0 + sv * es, es)
        if len(segs) < 3: continue
        Q, tr = _chain(segs, tri)
        if len(Q) < 4: continue
        if nt[tr[0]] @ UP < nt[tr[-1]] @ UP: Q, tr = Q[::-1], tr[::-1]          # top first
        d = np.diff(Q, axis=0); l = np.linalg.norm(d, axis=1); ok = l > 1e-6
        Q = np.r_[Q[:1], Q[1:][ok]]; tr = tr[ok]; d = d[ok] / l[ok][:, None]; l = l[ok]
        if len(tr) < 3: continue
        tn = np.degrees(np.arccos(np.clip((d[:-1] * d[1:]).sum(1), -1, 1)))     # unsigned turn at interior points
        tot = tn.sum(); width = l.sum()
        pillar = turn_rng[0] <= tot <= turn_rng[1] and width <= wmax
        stations.append(dict(s=float(sv), turn=float(tot), width=float(width), pillar=bool(pillar)))
        if not pillar: continue
        cum = np.r_[0, np.cumsum(tn)] / tot                                   # turn before each segment
        cum_after = np.r_[np.cumsum(tn), tot] / tot
        lab = np.where(cum_after <= lo + 1e-9, 0, np.where(cum >= hi - 1e-9, 2, 1))
        for t_, lb, ln in zip(tr, lab, l): votes[t_, lb] += ln
    lab = np.full(len(Fr), 3)                       # 3 = rest
    hit = votes.sum(1) > 0; lab[hit] = votes[hit].argmax(1)
    return dict(labels=lab, axis=es, centre=c0, stations=stations)


def _line(P_):
    c = P_.mean(0); d = np.linalg.svd(P_ - c)[2][0] if len(P_) > 1 else np.zeros(3)
    return c, d / max(np.linalg.norm(d), 1e-12)


def _proj(p, c, d): return c + ((p - c) @ d) * d


def _bez(Pc, t):
    from math import comb
    n = len(Pc) - 1; t = np.asarray(t)[:, None]
    return sum(comb(n, k) * t ** k * (1 - t) ** (n - k) * Pc[k] for k in range(n + 1))


def shoulder_profile(Q, cum_lo=0.05, cum_hi=0.95, tmin=1.5, nu=(6, 14, 8)):
    """designer profile of one station: Q = section polyline (top -> side, 3D).
    top line through the points before A, side line through the points from D on (A / D = where the signed cumulative
    turn passes cum_lo / cum_hi of the total), and a G2 quintic Bezier from A' to D' (A, D projected on the lines;
    tangent to the lines with zero curvature at both ends) fitted to the turn points between them (they lie on Kunos
    row edges, i.e. on the surface; points on diagonal edges are chord points and are not used).
    Returns dict(pts (sum(nu), 3), kinds, rms of the turn points, A, D)."""
    d = np.diff(Q, axis=0); l = np.linalg.norm(d, axis=1); d /= l[:, None]
    n_ = np.cross(d[:-1], d[1:]); ax = n_.sum(0); ax /= max(np.linalg.norm(ax), 1e-12)
    tn = np.degrees(np.arctan2((n_ @ ax), (d[:-1] * d[1:]).sum(1)))          # signed turn at interior points
    cum = np.cumsum(tn); tot = cum[-1]
    if abs(tot) < 20: return None
    ia = int(np.argmax(cum / tot >= cum_lo)) + 1; idd = int(np.argmax(cum / tot >= cum_hi)) + 1   # indices into Q
    if idd <= ia: return None
    ct, dt = _line(Q[:ia + 1]); cs, ds = _line(Q[idd:])
    if (Q[ia] - Q[0]) @ dt < 0: dt = -dt                                     # top direction: towards A
    if (Q[-1] - Q[idd]) @ ds < 0: ds = -ds                                   # side direction: away from D
    A_ = _proj(Q[ia], ct, dt); D_ = _proj(Q[idd], cs, ds)
    mid = [i for i in range(ia + 1, idd) if abs(tn[i - 1]) > tmin]          # turn points inside the shoulder
    M = Q[mid] if mid else np.zeros((0, 3))
    chord = np.linalg.norm(D_ - A_)
    def ctrl(a, b): return np.array([A_, A_ + a * dt, A_ + 2 * a * dt, D_ - 2 * b * ds, D_ - b * ds, D_])
    best = None
    for a in np.linspace(0.01, 0.6, 60) * chord:
        for b in np.linspace(0.01, 0.6, 60) * chord:
            C_ = ctrl(a, b); B = _bez(C_, np.linspace(0, 1, 200))
            e = np.array([np.linalg.norm(B - m, axis=1).min() for m in M]) if len(M) else np.zeros(1)
            sc = np.sqrt((e ** 2).mean()) + (0 if len(M) else abs(a - b) * 1e-3)
            if best is None or sc < best[0]: best = (sc, a, b)
    C_ = ctrl(best[1], best[2])
    top = Q[0] + 0 * dt; top = _proj(Q[0], ct, dt); side = _proj(Q[-1], cs, ds)
    pts = np.r_[np.linspace(0, 1, nu[0], endpoint=False)[:, None] * (A_ - top) + top,
                _bez(C_, np.linspace(0, 1, nu[1], endpoint=False)),
                np.linspace(0, 1, nu[2])[:, None] * (side - D_) + D_]
    return dict(pts=pts, rms=float(best[0]), A=A_, D=D_, E0=top, E1=side, turn=float(tot), nmid=len(M), ab=(best[1] / chord, best[2] / chord))


def pillar_grid(V, Fr, Nv, step=0.025, smooth_per=0.06, s_lim=None):
    """station profiles of a soft-shoulder region over its pillar-like stretch, smoothed along the length.
    Returns dict(grid (ns, nu, 3) metres, s (ns,), s_range, axis, centre, info)"""
    sp = split_shoulder(V, Fr, Nv, step=0.005)
    ps = [x['s'] for x in sp['stations'] if x['pillar']]
    s0, s1 = min(ps), max(ps)
    if s_lim: s0, s1 = max(s0, s_lim[0]), min(s1, s_lim[1])
    T = V[Fr]; es, c0 = sp['axis'], sp['centre']
    nt = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nt /= np.maximum(np.linalg.norm(nt, axis=1), 1e-12)[:, None]
    nt *= np.sign((nt * Nv[Fr].mean(1)).sum(1))[:, None]
    rows, ss, info = [], [], []
    for sv in np.linspace(s0, s1, max(4, int(round((s1 - s0) / step)) + 1)):
        segs, tri = _section(T, c0 + sv * es, es)
        if len(segs) < 3: continue
        Q, tr = _chain(segs, tri)
        if nt[tr[0]] @ UP < nt[tr[-1]] @ UP: Q = Q[::-1]
        ok = np.r_[True, np.linalg.norm(np.diff(Q, axis=0), axis=1) > 1e-6]; Q = Q[ok]
        if len(Q) < 4: continue
        pr = shoulder_profile(Q)
        if pr is None: continue
        rows.append(pr['pts']); ss.append(sv); info.append(pr)
    G = np.array(rows); ss = np.array(ss)
    # smooth the profile's DEFINING data along the length (not grid columns): the two edge points, the blend's ends
    # A and D, and the blend tensions a, b (chord fractions); then rebuild every profile from them
    import strip_build as SB
    def sm(Y, tol):
        f = SB.fit_graph(ss, Y, [ss[0], ss[-1]], tol=tol, nmax=int(np.clip((ss[-1] - ss[0]) / smooth_per, 4, 24)), mu=1e-5)
        return SB.eval_graph(f, ss), f['err']
    E0, e0 = sm(np.array([i['E0'] for i in info]), 5e-4); E1, e1 = sm(np.array([i['E1'] for i in info]), 5e-4)
    A_, ea = sm(np.array([i['A'] for i in info]), 5e-4); D_, ed = sm(np.array([i['D'] for i in info]), 5e-4)
    ab, _ = sm(np.array([i['ab'] for i in info]), 0.02)
    Gs = []
    for k in range(len(ss)):
        dt = A_[k] - E0[k]; dt /= np.linalg.norm(dt); ds = E1[k] - D_[k]; ds /= np.linalg.norm(ds)
        ch = np.linalg.norm(D_[k] - A_[k]); a, b = ab[k] * ch
        C_ = np.array([A_[k], A_[k] + a * dt, A_[k] + 2 * a * dt, D_[k] - 2 * b * ds, D_[k] - b * ds, D_[k]])
        Gs.append(np.r_[np.linspace(0, 1, 6, endpoint=False)[:, None] * (A_[k] - E0[k]) + E0[k],
                        _bez(C_, np.linspace(0, 1, 14, endpoint=False)), np.linspace(0, 1, 8)[:, None] * (E1[k] - D_[k]) + D_[k]])
    Gs = np.array(Gs)
    print(f'pillar_grid: {len(ss)} stations, smoothing error (mm) edges {e0*1e3:.2f} / {e1*1e3:.2f}, A {ea*1e3:.2f}, D {ed*1e3:.2f}')
    return dict(grid=Gs, raw=G, s=ss, axis=es, centre=c0, info=info, split=sp)


def foot_fill_data(V, Fr, Nv, g, components, boundary_loops, corner_deg=35.0, flat_deg=1.5):
    """the foot beyond the pillar's last station as a filling patch: its outline beyond the end plane (Kunos boundary,
    split into edges at corners), the pillar's end profile (G1 to the pillar surface) and its Kunos vertices as
    points (+ samples inside flat-intended facets: corner normals within flat_deg). Metres."""
    es, c0, s1 = g['axis'], g['centre'], g['s'][-1]
    sv = (V[Fr] - c0) @ es
    Ff = Fr[(sv > s1).any(1)]
    parts = components(V, Ff)[0]; Ff = max(parts, key=len)
    _, wid = components(V, Ff)
    rep = {}
    for i, w in enumerate(wid): rep.setdefault(w, i)
    L = max(boundary_loops(Ff, wid), key=len); Q = V[[rep[w] for w in L]]
    s_ = (Q - c0) @ es
    # the outline beyond the plane: rotate the loop to start at the first point beyond s1 after a point before it
    beyond = s_ > s1 + 1e-4
    k0 = next(i for i in range(len(Q)) if beyond[i] and not beyond[i - 1])
    Q, beyond, s_ = np.roll(Q, -k0, 0), np.roll(beyond, -k0), np.roll(s_, -k0)
    k1 = next(i for i in range(len(Q)) if not beyond[i])
    run = Q[:k1]
    # end points ON the plane (interpolated along the loop) -> join the pillar's end profile corners
    def on_plane(p, q, sp, sq): a = (s1 - sp) / (sq - sp); return p + a * (q - p)
    pa = on_plane(Q[-1], Q[0], s_[-1], s_[0]); pb = on_plane(Q[k1 - 1], Q[k1], s_[k1 - 1], s_[k1])
    end_row = g['grid'][-1]
    snap = lambda p: end_row[0] if np.linalg.norm(end_row[0] - p) < np.linalg.norm(end_row[-1] - p) else end_row[-1]
    out = np.r_[[snap(pa)], run, [snap(pb)]]
    # split at corners
    d = np.diff(out, axis=0); d /= np.maximum(np.linalg.norm(d, axis=1), 1e-12)[:, None]
    ang = np.degrees(np.arccos(np.clip((d[:-1] * d[1:]).sum(1), -1, 1)))
    cuts = [0] + [i + 1 for i in range(len(ang)) if ang[i] > corner_deg] + [len(out) - 1]
    edges = [out[a:b + 1] for a, b in zip(cuts[:-1], cuts[1:]) if b > a]
    # interior data: vertices beyond the plane not on the outline + flat facet samples
    bset = set(L); inner = [rep[w] for w in set(wid[Ff.ravel()]) - bset]
    X = V[inner]; X = X[((X - c0) @ es) > s1 + 0.005]
    Nn = Nv / np.linalg.norm(Nv, axis=1)[:, None]
    cosmin = np.minimum.reduce([(Nn[Ff[:, a]] * Nn[Ff[:, b]]).sum(1) for a, b in ((0, 1), (1, 2), (0, 2))])
    import car_loft as CL
    Tf = V[Ff[cosmin > np.cos(np.radians(flat_deg))]]
    S = CL.sample_tris(Tf, 0.02) if len(Tf) else np.zeros((0, 3))
    S = S[((S - c0) @ es) > s1 + 0.005] if len(S) else S
    return dict(edges=edges, pts=X, flat=S, plane=(c0 + s1 * es, es), tris=Ff)
