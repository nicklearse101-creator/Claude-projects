"""Pillar + foot as ONE swept surface (2026-11-11, spec :pillarN with PF_PILLAR_FOOT=1, the default).
The AE86 C-pillar's shoulder carries on past the pillar's end as the roll between the rear deck (top) and the skirt
(side face -> broad plan corner -> rear face, one convex surface).

Stations: the pillar's square-to-axis sections with its proven profile (blend_build.shoulder_profile: top line + G2
blend + side LINE), then sections marched along the roll's spine round the corner and across the rear. The march
steers on the profile's virtual sharp corner X (top line x side tangent: stable whatever the blend split) and keeps
the station normal parallel to the deck. Foot profile (roll_profile): top LINE fitted to the last 60 mm before the
blend, arm clamped to the pillar's top width (the deck interior is its own face) + G2 quintic blend + side CURVE
h(u) = c3 u^3 + c4 u^4 off the blend's end tangent (zero curvature at D = G2 to the blend). The blend's ends are
searched round the turn-rate peak (least total squared error); pass 2 refits every foot station near the median-
filtered, smoothed setbacks. The raw profile ROWS are then smoothed column by column along the spine (smoothing the
parameters separately broke how they fit together: rows 7.7 mm off). FreeCAD builds the face by interpolating the grid
(approximate failed quietly on this grid: 6 poles over 54 stations). Pure numpy."""
import os
import numpy as np
from blend_build import _section, _line, _proj, _bez, split_shoulder, shoulder_profile, UP


def _chain_near(segs, tri, p):
    key = lambda q: tuple(np.round(q / 1e-6).astype(np.int64))
    adj = {}
    for k, (a, b) in enumerate(segs):
        adj.setdefault(key(a), []).append((k, 0)); adj.setdefault(key(b), []).append((k, 1))
    k0 = int(np.argmin(np.linalg.norm(segs.mean(1) - p, axis=1)))
    used = np.zeros(len(segs), bool); used[k0] = True
    Pp, Tt = [segs[k0][0], segs[k0][1]], [tri[k0]]
    for end in (1, 0):
        while True:
            q = Pp[-1] if end else Pp[0]
            nxt = [(k, w) for k, w in adj.get(key(q), []) if not used[k]]
            if not nxt: break
            k, w = nxt[0]; used[k] = True
            if end: Pp.append(segs[k][1 - w]); Tt.append(tri[k])
            else: Pp.insert(0, segs[k][1 - w]); Tt.insert(0, tri[k])
    return np.array(Pp), np.array(Tt, int)


SIDE_C2 = False     # hatch_build sets it: the side curve gets a u^2 term (curvature at D) and the blend is made G2 to it


def _side_fit(Sd, A_, nph=21, span=0.35, u0=None, pn=None):
    """side curve off D (Sd = side points - D, Sd[0] = 0): tangent angle searched, h = c3 u^3 + c4 u^4 by least squares.
    SIDE_C2: h = c2 u^2 + c3 u^3 + c4 u^4, c returned as (c3, c4, c2). The AE86 hatch skirt is close to an arc
    (R ~ 320 mm) from the knee down: with zero curvature at D the quartic missed it by 0.6-1 mm rms per station, and
    the misfit shifted from station to station (ripples along the tail)."""
    best = None
    for ph in np.linspace(-span, span, nph):
        ds = np.cos(ph) * u0 + np.sin(ph) * np.cross(pn, u0)
        ns = A_ - ((A_) @ ds) * ds; ns /= np.linalg.norm(ns)
        u = Sd[1:] @ ds; h = Sd[1:] @ ns
        if (u <= 0).any(): continue
        if SIDE_C2:
            Mx = np.c_[u ** 3, u ** 4, u ** 2]
            c = np.linalg.lstsq(np.r_[Mx, np.diag([1e-3, 1e-2, 1e-4])], np.r_[h, 0, 0, 0], rcond=None)[0]
        else:
            Mx = np.c_[u ** 3, u ** 4]
            c = np.linalg.lstsq(np.r_[Mx, np.diag([1e-3, 1e-2])], np.r_[h, 0, 0], rcond=None)[0]
        e2 = ((Mx @ c - h) ** 2).sum()
        if best is None or e2 < best[0]: best = (e2, ds, ns, c, u.max())
    return best


def _w2(sf, b):
    """offset of the blend's 4th control point that makes the quintic G2 to the side curve's curvature at D:
    kappa_end = 4/5 w / b^2 and kappa_side = 2 c2  ->  w = 2.5 c2 b^2 along ns (zero without the u^2 term)"""
    c = sf[3]
    return 2.5 * c[2] * b * b * sf[2] if len(c) > 2 else 0.0 * sf[2]


def _corner(ct, dt, D_, ds, A_):
    """virtual sharp corner: closest point between the top line and the side's end tangent; setbacks of A and D"""
    M_ = np.c_[dt, -ds]; st_ = np.linalg.lstsq(M_, D_ - ct, rcond=None)[0]
    X_ = 0.5 * (ct + st_[0] * dt + D_ + st_[1] * ds)
    return X_, float((X_ - A_) @ dt), float((D_ - X_) @ ds)


def roll_profile(Q, top_max=None, rate_min=0.6, win=0.006, tmin=1.5, reach=6, chord_w=0.2, target=None, pen_mm=2.5, top_fit=0.06):
    """Q = section polyline, top first. The blend's ends (Q indices ia < idd) are searched round the turn-rate peak:
    each candidate = top line through Q[:ia+1] + side curve through Q[idd:] + G2 quintic blend; the pair with the
    least summed squared error of every vertex wins (low-turn vertices inside the blend - chord points on diagonal
    edges - weigh chord_w). target = (setback on the top line, setback on the side) from the virtual sharp corner X
    (top line x side tangent): candidates are penalised for leaving it (pen_mm off ~ doubles a good fit's error).
    Returns the profile's defining data or None."""
    d = np.diff(Q, axis=0); l = np.linalg.norm(d, axis=1); d = d / l[:, None]
    n_ = np.cross(d[:-1], d[1:]); ax = n_.sum(0); ax /= max(np.linalg.norm(ax), 1e-12)
    tn = np.degrees(np.arctan2(n_ @ ax, (d[:-1] * d[1:]).sum(1)))          # signed turn at Q[1:-1]
    ar = np.cumsum(l)[:-1]
    W = np.array([tn[np.abs(ar - a) <= win].sum() for a in ar]) / (2 * win * 1e3)   # deg / mm
    pk = int(np.argmax(W))
    if W[pk] < rate_min: return None
    qp = pk + 1                                                              # Q index of the peak
    tb = np.linspace(0, 1, 120); best = None
    arq = np.r_[0, np.cumsum(l)]                                             # arc position of every Q point
    for ia in range(max(1, qp - reach), qp + 1):
        j0 = int(np.searchsorted(arq, arq[ia] - top_fit)); j0 = min(j0, ia - 1)   # top line: only the last top_fit m before A
        ct, dt = _line(Q[j0:ia + 1])
        if (Q[ia] - Q[j0]) @ dt < 0: dt = -dt
        A_ = _proj(Q[ia], ct, dt)
        e_top = (np.linalg.norm(np.cross(Q[j0:ia + 1] - ct, dt), axis=1) ** 2).sum()
        for idd in range(max(qp, ia + 1), min(len(Q) - 2, qp + reach) + 1):
            D_ = Q[idd]; Sd = Q[idd:] - D_
            pn = np.cross(dt, D_ - A_); pn /= max(np.linalg.norm(pn), 1e-12)
            near = Sd[1:][np.linalg.norm(Sd[1:], axis=1) <= 0.025]
            u0 = near[-1] if len(near) else Sd[1]; u0 = u0 / np.linalg.norm(u0)
            sf = _side_fit(Sd, A_ - D_, u0=u0, pn=pn)
            if sf is None: continue
            e_side, ds = sf[0], sf[1]
            chord = np.linalg.norm(D_ - A_)
            mid = list(range(ia + 1, idd)); wts = np.array([1.0 if abs(tn[i - 1]) > tmin else chord_w for i in mid])
            bb = None
            for a in np.linspace(0.02, 0.6, 12) * chord:
                for b in np.linspace(0.02, 0.6, 12) * chord:
                    C_ = np.array([A_, A_ + a * dt, A_ + 2 * a * dt, D_ - 2 * b * ds + _w2(sf, b), D_ - b * ds, D_])
                    if mid:
                        B = _bez(C_, tb); e = (wts * np.array([np.linalg.norm(B - Q[i], axis=1).min() ** 2 for i in mid])).sum()
                    else: e = abs(a - b) * 1e-9
                    if bb is None or e < bb[0]: bb = (e, a, b)
            X_, sA, sD = _corner(ct, dt, D_, ds, A_)
            tot = e_top + e_side + bb[0]
            if target is not None:
                tot += len(Q) * 9e-8 * (((sA - target[0]) / (pen_mm * 1e-3)) ** 2 + ((sD - target[1]) / (pen_mm * 1e-3)) ** 2)
            if best is None or tot < best[0]: best = (tot, ia, idd, ct, dt, A_, D_, sf, bb)
    if best is None: return None
    tot, ia, idd, ct, dt, A_, D_, sf, bb = best
    # refine the tensions finely for the winner
    chord = np.linalg.norm(D_ - A_); ds = sf[1]; mid = list(range(ia + 1, idd))
    wts = np.array([1.0 if abs(tn[i - 1]) > tmin else chord_w for i in mid]); tb = np.linspace(0, 1, 200)
    for a in np.linspace(max(0.01, bb[1] / chord - 0.06), bb[1] / chord + 0.06, 13) * chord:
        for b in np.linspace(max(0.01, bb[2] / chord - 0.06), bb[2] / chord + 0.06, 13) * chord:
            C_ = np.array([A_, A_ + a * dt, A_ + 2 * a * dt, D_ - 2 * b * ds + _w2(sf, b), D_ - b * ds, D_])
            e = (wts * np.array([np.linalg.norm(_bez(C_, tb) - Q[i], axis=1).min() ** 2 for i in mid])).sum() if mid else abs(a - b) * 1e-9
            if e < bb[0]: bb = (e, a, b)
    E0 = _proj(Q[0], ct, dt)
    if top_max is not None and np.linalg.norm(A_ - E0) > top_max: E0 = A_ - top_max * dt   # (a constant arm put a hump over the window edge)
    C_ = np.array([A_, A_ + bb[1] * dt, A_ + 2 * bb[1] * dt, D_ - 2 * bb[2] * ds + _w2(sf, bb[2]), D_ - bb[2] * ds, D_])
    nside = max(len(Q) - idd - 1, 1); X_, sA, sD = _corner(ct, dt, D_, ds, A_)
    return dict(E0=E0, A=A_, D=D_.copy(), Dt=D_ + 0.01 * ds, ab=np.array([bb[1], bb[2]]) / chord, Ls=np.array([sf[4]]), c=sf[3],
                rms_side=float(np.sqrt(sf[0] / nside)), rms_blend=float(np.sqrt(bb[0] / max(len(mid), 1))),
                rms=float(np.sqrt(tot / len(Q))), M=_bez(C_, [0.5])[0], nmid=len(mid), turn=float(tn.sum()), Q=Q, X=X_, sb=np.array([sA, sD]))


def _from_shoulder(pr, Q):
    """blend_build.shoulder_profile (top line + G2 blend + side LINE) in roll_profile's form"""
    if pr is None: return None
    ds = pr['E1'] - pr['D']; L = np.linalg.norm(ds); ds = ds / L; dt = pr['A'] - pr['E0']; dt /= np.linalg.norm(dt)
    X_, sA, sD = _corner(pr['A'], dt, pr['D'], ds, pr['A'])
    return dict(E0=pr['E0'], A=pr['A'], D=pr['D'], Dt=pr['D'] + 0.01 * ds, ab=np.array(pr['ab']), Ls=np.array([L]),
                c=np.zeros(2), X=X_, sb=np.array([sA, sD]), M=pr['pts'][13], Q=Q, rms=pr['rms'], rms_side=0.0,
                rms_blend=pr['rms'], turn=pr['turn'], nmid=pr['nmid'])


def build_profile(E0, A_, D_, Dt, ab, Ls, c, nu=(6, 14, 12)):
    dt = A_ - E0; dt /= np.linalg.norm(dt); ds = Dt - D_; ds /= np.linalg.norm(ds)
    ns = (A_ - D_) - ((A_ - D_) @ ds) * ds; ns /= np.linalg.norm(ns)
    ch = np.linalg.norm(D_ - A_); a, b = ab * ch
    c2 = c[2] if len(c) > 2 else 0.0
    C_ = np.array([A_, A_ + a * dt, A_ + 2 * a * dt, D_ - 2 * b * ds + 2.5 * c2 * b * b * ns, D_ - b * ds, D_])
    u = np.linspace(0, Ls, nu[2])
    side = D_ + u[:, None] * ds + (c[0] * u ** 3 + c[1] * u ** 4 + c2 * u ** 2)[:, None] * ns
    return np.r_[np.linspace(0, 1, nu[0], endpoint=False)[:, None] * (A_ - E0) + E0,
                 _bez(C_, np.linspace(0, 1, nu[1], endpoint=False)), side]


def sweep_grid(V, Fr, Nv, s_lim=(-0.645, 0.135), step_p=0.025, step_f=0.015, x_stop=0.46, Rd=0.2, ramp=4, verbose=True, Fm=None, edge_cos=None):
    """Returns dict(grid (ns, nu, 3) metres, E0 row, arc, deck normal nd, st = [(plane origin, normal, profile)],
    nfoot, axis, centre, s = pillar range, raw = unsmoothed rows).
    Fm: triangles the FOOT stations are cut from (default Fr). The hatch build passes the whole hatch skin (both halves)
    with x_stop 0, so the march runs on round the corner and across the tail to the centreline, while the pillar
    stations still come from Fr alone (the proven pillar piece: same axis, same stations).
    edge_cos: foot sections keep only the points on edges crossing the plane steeply (|cos(edge, plane normal)| >=
    edge_cos) plus the section's two ends. Kunos's tail is rows of vertices joined by diagonals: a plane between two
    rows cuts the diagonals at CHORD points (~1 mm inside a curved skirt), so the profile wobbled with the row spacing
    (ripples in grey); the edges running across the plane join two rows at the same profile position = surface points."""
    sp = split_shoulder(V, Fr, Nv, step=0.005)
    ps = [x['s'] for x in sp['stations'] if x['pillar']]
    s0, s1 = max(min(ps), s_lim[0]), min(max(ps), s_lim[1])
    T0 = V[Fr]; cen0 = T0.mean(1); es, c0 = sp['axis'], sp['centre']
    nt0 = np.cross(T0[:, 1] - T0[:, 0], T0[:, 2] - T0[:, 0]); nt0 /= np.maximum(np.linalg.norm(nt0, axis=1), 1e-12)[:, None]
    nt0 *= np.sign((nt0 * Nv[Fr].mean(1)).sum(1))[:, None]

    Fm = Fr if Fm is None else Fm
    Tm = V[Fm]; cenm = Tm.mean(1)
    ntm = np.cross(Tm[:, 1] - Tm[:, 0], Tm[:, 2] - Tm[:, 0]); ntm /= np.maximum(np.linalg.norm(ntm, axis=1), 1e-12)[:, None]
    ntm *= np.sign((ntm * Nv[Fm].mean(1)).sum(1))[:, None]

    def section(o, nrm, rd, foot=False):
        T, cen, nt = (Tm, cenm, ntm) if foot else (T0, cen0, nt0)
        m = np.linalg.norm(cen - o, axis=1) < rd
        if m.sum() < 3: return None
        segs, tri = _section(T[m], o, nrm)
        if len(segs) < 3: return None
        Q, tr = _chain_near(segs, tri, o); idx = np.nonzero(m)[0][tr]
        if nt[idx[0]] @ UP < nt[idx[-1]] @ UP: Q = Q[::-1]
        ok = np.r_[True, np.linalg.norm(np.diff(Q, axis=0), axis=1) > 1e-6]; Q = Q[ok]
        if foot and edge_cos is not None and len(Q) > 6:
            Tc = T[m]; dd_ = (Tc - o) @ nrm; cs = {}
            for t_, e_ in zip(Tc, dd_):
                for i, j in ((0, 1), (1, 2), (2, 0)):
                    if e_[i] * e_[j] < 0:
                        q_ = t_[i] + e_[i] / (e_[i] - e_[j]) * (t_[j] - t_[i]); ev = t_[j] - t_[i]
                        cs[tuple(np.round(q_ / 1e-6).astype(np.int64))] = abs(ev @ nrm) / np.linalg.norm(ev)
            c_ = np.array([cs.get(tuple(np.round(q_ / 1e-6).astype(np.int64)), 1.0) for q_ in Q])
            keep = c_ >= edge_cos; keep[0] = keep[-1] = True
            if keep.sum() >= 6: Q = Q[keep]
        return Q if len(Q) >= 5 else None

    st = []
    for sv in np.linspace(s0, s1, max(4, int(round((s1 - s0) / step_p)) + 1)):
        o = c0 + sv * es; Q = section(o, es, 0.15)
        pr = _from_shoulder(shoulder_profile(Q), Q) if Q is not None else None     # the pillar's proven profile
        if pr is not None: st.append((o, es, pr))
    npil = len(st)
    top_max = float(np.median([np.linalg.norm(p['A'] - p['E0']) for _, _, p in st[-4:]]))
    uf = np.unique(Fr[((V[Fr] - c0) @ es > s1).any(1)])
    Nn = Nv[uf] / np.linalg.norm(Nv[uf], axis=1)[:, None]; nd = Nn[Nn @ UP > 0.9].mean(0); nd /= np.linalg.norm(nd)

    def proj_t(tv, kk):                       # ramp the station normal into the deck plane over the first stations
        w = min(1.0, (kk + 1) / ramp); tp = tv - (tv @ nd) * nd; tp /= np.linalg.norm(tp)
        r = (1 - w) * tv + w * tp; return r / np.linalg.norm(r)

    M = st[-1][2]['X']; t = es.copy(); nfoot = 0
    for k in range(150):                      # march on the virtual corner X (stable whatever the blend split)
        p = M + step_f * t; Q = section(p, t, Rd, foot=True)
        pr = roll_profile(Q, top_max) if Q is not None else None
        if pr is None: break
        tn_ = pr['X'] - M; tn_ /= np.linalg.norm(tn_)
        t2 = proj_t(0.6 * t + 0.4 * tn_, k)
        p2 = M + step_f * t2; Q2 = section(p2, t2, Rd, foot=True)
        pr2 = roll_profile(Q2, top_max) if Q2 is not None else None
        if pr2 is None or np.linalg.norm(pr2['X'] - M) < 0.006: break
        t = t2; M = pr2['X']; st.append((p2, t2, pr2)); nfoot += 1
        if M[0] < x_stop: break
    while nfoot > 2 and st[-1][2]['Ls'][0] < 0.5 * np.median([p['Ls'][0] for _, _, p in st[-6:-1]]):
        st.pop(); nfoot -= 1                  # a last section cut short by the clip box edge
    import strip_build as SB
    Xs = np.array([p['X'] for _, _, p in st]); arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Xs, axis=0), axis=1))]
    # pass 2: setbacks smoothed along the spine, every station refitted near them
    sb = np.array([p['sb'] for _, _, p in st])
    sb = np.array([np.median(sb[max(0, k - 2):k + 3], axis=0) for k in range(len(sb))])     # robust to odd stations
    fsb = SB.fit_graph(arc, sb, [arc[0], arc[-1]], tol=3e-3, nmax=int(np.clip(arc[-1] / 0.08, 4, 20)), mu=1e-4)
    sbs = SB.eval_graph(fsb, arc)
    st = [(o, n, p if k < npil else (roll_profile(p['Q'], top_max, target=sbs[k]) or p)) for k, (o, n, p) in enumerate(st)]

    # the profile's defining points smoothed along the spine, every profile rebuilt from them
    def sm(Y, tol, per):
        f = SB.fit_graph(arc, Y, [arc[0], arc[-1]], tol=tol, nmax=int(np.clip(arc[-1] / per, 4, 60)), mu=1e-5)
        return SB.eval_graph(f, arc), f['err']
    # raw profile rows smoothed column by column along the spine (each column keeps its meaning: E0, the top arm,
    # the blend, the side curve), so a parameter can't drift away from the others it belongs with
    def resample(p, n_top=10, n_near=12, near=0.030, n_far=10):
        """the profile at fixed arc distances from its anchor (the point nearest the virtual corner X): the blend's
        ends A / D jitter between stations, and columns tied to them slid along the surface (18 mm kinks, a pinch)"""
        P = build_profile(p['E0'], p['A'], p['D'], p['Dt'], p['ab'], float(p['Ls'][0]), p['c'], nu=(40, 80, 80))
        ar = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
        a0 = ar[np.argmin(np.linalg.norm(P - p['X'], axis=1))]
        top = np.linspace(0, a0, n_top, endpoint=False)
        nr = np.linspace(a0, min(a0 + near, ar[-1]), n_near, endpoint=False)
        far = np.linspace(min(a0 + near, ar[-1]), ar[-1], n_far)
        q = np.r_[top, nr, far]
        return np.c_[[np.interp(q, ar, P[:, i]) for i in range(3)]].T
    if os.environ.get('PF_SWEEP_RESAMPLE', '1') == '1':
        Gr = np.array([resample(p) for _, _, p in st])
    else:
        Gr = np.array([build_profile(p['E0'], p['A'], p['D'], p['Dt'], p['ab'], float(p['Ls'][0]), p['c']) for _, _, p in st])
    Gs, e0 = sm(Gr.reshape(len(st), -1), 5e-4, 0.02)
    G = Gs.reshape(Gr.shape); E0 = G[:, 0]; ea = ed = float(np.abs(G - Gr).max())
    if verbose:
        rs = np.array([p['rms_side'] for _, _, p in st]) * 1e3; rb = np.array([p['rms_blend'] for _, _, p in st]) * 1e3
        print(f'sweep_grid: {npil} pillar + {nfoot} foot stations, spine {arc[-1]*1e3:.0f} mm, top arm max {top_max*1e3:.0f} mm; '
              f'smoothing (mm) E0 {e0*1e3:.2f} A {ea*1e3:.2f} D {ed*1e3:.2f}; raw rms side p95 {np.percentile(rs, 95):.2f}, '
              f'blend p95 {np.percentile(rb, 95):.2f}', flush=True)
    return dict(grid=G, E0=E0, arc=arc, nd=nd, st=st, npil=npil, nfoot=nfoot, axis=es, centre=c0, s=(s0, s1), top_max=top_max, raw=Gr)
