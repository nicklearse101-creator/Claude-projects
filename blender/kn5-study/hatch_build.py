"""AE86 hatch (tailgate) as Class-A faces (research: blender/research/reports/Hatch surfacing.md).

    python hatch_build.py CAR_DIR OUT_DIR

The Kunos hatch is NOT a separate mesh: it is one smooth region of GEO_body (full-mesh crease piece 2) plus four
returns (pieces 4, 14, 22 and two 2 mm corner bits). It is a frame round the rear glass whose outer edge rolls over all
the way round: down both pillars, round the lower corners and across the tail, where a flat DECK under the glass rolls
over into a sloped SKIRT. Exactly symmetric (mirrored half-model, a vertex row on x = 0).

Faces (all named 'hatch:...'):
- hatch:U     the U-shaped sweep: side bands (the pillar's station profiles: top line + G2 shoulder + side line) and the
              tail roll (foot profiles: deck line + G2 roll + skirt curve), ONE grid from the left pillar top round the
              tail to the right pillar top. Built on the left half (sweep_build.sweep_grid, march run on to the
              centreline), mirrored, the rows smoothed along the spine as one symmetric set and resampled evenly
              across the centre: symmetric by construction, no seam at x = 0.
- hatch:hdr   the header across the top: one fitted face, both pillar ends' rows as data, cut by both end planes;
              its top outline on the roof's rear header strip (roof = master, PF_MASTER).
- hatch:deck  the flat deck under the glass, full width, cut on the U grid's real edge, the U's flat band as data.
Returns (glass-opening ring, glass-bottom wall, bottom-edge return, corners): a later step.

The rear-quarter build used to make the left third of this (its 'C-pillar' r1p / r1x00 / r1d0, clipped at x 0.45 on a
triangle zig-zag); it now leaves every hatch-owned triangle out (PF_NOHATCH=1 in panel_fit.load_mesh).
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path:
    sys.path.append(r'D:\ClaudeData\pylibs')
import panel_fit as PF

MIR = np.array([-1.0, 1.0, 1.0])
# full GEO_body crease pieces (PF.crease_pieces, largest first) and their Kunos triangle counts (checked on load)
PIECES = dict(skin=(2, 1270), ring=(4, 176), wall=(14, 88), bottom=(22, 60), cornerR=(116, 3), cornerL=(117, 3))
PILLAR_CLIP = (0.45, 1.0, 0.0, 1.3, -2.2, -0.5)      # the old quarter clip: its hatch triangles = the proven pillar piece
S_LIM = (-0.645, 0.135)                              # pillar stations along its axis (as the quarter's PF_PILLAR_S)
STEP_F = 0.015                                       # foot station spacing (m)


def pieces(car):
    """dict name -> Kunos triangles (vertex indices of the raw GEO_body)"""
    if car not in _PC:
        V, F, N = PF.load_mesh(car, 'GEO_body', raw=True)
        pf = PF.crease_pieces(V, F, N)
        out = {}
        for nm, (i, n) in PIECES.items():
            assert len(pf[i]) == n, f'hatch piece {nm}: crease piece {i} has {len(pf[i])} tris, expected {n}'
            out[nm] = pf[i]
        _PC[car] = (V, F, N, out)
    return _PC[car]
_PC = {}


def hatch_owned(car):
    """every Kunos GEO_body triangle the hatch build makes (skin + returns); other builds leave them out (PF_NOHATCH)"""
    return np.vstack(list(pieces(car)[3].values()))


def steady_rows(g, verbose=True, n_top=10, n_near=12, near=0.030, n_far=10, ramp=4, phi0=15.0):
    """ALL rows (pillar + foot) sampled from a STABLE feature, so the columns do not slide along the surface from
    station to station. sweep_build anchors a row on the profile point nearest the virtual corner X; with a free
    curvature at D (SIDE_C2) the split between blend and side curve is ambiguous, so A, D and X jitter (setbacks 2-24
    mm) although the curve itself barely changes, and the tightest blend point jumps too: smoothing then averaged
    points from both sides of the knee and cut the corner (3 mm). Here the anchor is where the profile's tangent has
    turned phi0 from the top line: it depends only on the curve's shape. Top part: pillar = from its real edge E0 to
    the anchor; foot = a fixed arc length before it (ramped from the pillar's last arm). Skirt length Ls median-filtered
    and smoothed along the spine (the far end is the U's free bottom edge). Columns n_top + n_near + n_far."""
    import sweep_build as SW
    import strip_build as SB
    st, npil = g['st'], g['npil']
    X = np.array([p['X'] for _, _, p in st]); arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))]
    Ls = np.array([float(p['Ls'][0]) for _, _, p in st])
    Lm = np.array([np.median(Ls[max(npil, k - 2):k + 3]) for k in range(len(Ls))])
    fl = SB.fit_graph(arc[npil:], Lm[npil:, None], [arc[npil], arc[-1]], tol=2e-3, nmax=12, mu=1e-4)
    Lsm = np.r_[Ls[:npil], SB.eval_graph(fl, arc[npil:])[:, 0]]

    def dense(p, Ls_):
        P = SW.build_profile(p['E0'], p['A'], p['D'], p['Dt'], p['ab'], Ls_, p['c'], nu=(40, 160, 120))
        ar = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
        tg = np.diff(P, axis=0); tg /= np.linalg.norm(tg, axis=1)[:, None]
        dt = (p['A'] - p['E0']) / np.linalg.norm(p['A'] - p['E0'])
        ang = np.degrees(np.arccos(np.clip(tg @ dt, -1, 1)))                  # turn from the top line, per segment
        am = 0.5 * (ar[:-1] + ar[1:])
        i = int(np.argmax(ang >= phi0))
        a0 = am[i] if i == 0 else np.interp(phi0, ang[i - 1:i + 1], am[i - 1:i + 1])
        return P, ar, a0, dt
    rows = [dense(p, float(Lsm[k] if k < npil else min(Lsm[k], p['Ls'][0] + 0.006))) + (k,) for k, (_, _, p) in enumerate(st)]
    L_pil = rows[npil - 1][2]                                                # pillar's last top arm (E0 -> anchor)
    L_top = float(np.median([r[2] for r in rows[npil:]]))
    out = []
    for P, ar, a0, dt, k in rows:
        if k < npil: Lt = a0
        else: w = min(1.0, (k - npil + 1) / ramp); Lt = (1 - w) * L_pil + w * L_top
        q_top = np.linspace(a0 - Lt, a0, n_top, endpoint=False)
        top = np.array([P[0] + q * dt if q < 0 else np.array([np.interp(q, ar, P[:, i]) for i in range(3)]) for q in q_top])
        q = np.r_[np.linspace(a0, min(a0 + near, ar[-1]), n_near, endpoint=False), np.linspace(min(a0 + near, ar[-1]), ar[-1], n_far)]
        rest = np.c_[[np.interp(q, ar, P[:, i]) for i in range(3)]].T
        out.append(np.r_[top, rest])
    if verbose:
        print(f'steady rows: anchor = {phi0:.0f} deg turn point, top arm {L_pil * 1e3:.1f} (pillar end) -> {L_top * 1e3:.1f} mm, '
              f'skirt length {Ls[npil:].min() * 1e3:.0f}-{Ls[npil:].max() * 1e3:.0f} mm smoothed (max change {np.abs(Lsm - Ls)[npil:].max() * 1e3:.1f} mm)', flush=True)
    return np.array(out)


def smooth_rows(A_, R_, spacing=0.03, nrm_rms=1e-4, nrm_max=5e-4):
    """the rows R_ (n, cols, 3) at spine arcs A_ (symmetric) smoothed column by column with ONE cubic B-spline of
    uniform knots ~spacing apart and third-difference fairing. The fairing weight is the largest whose residual NORMAL
    to the surface stays within nrm_rms (rms) and nrm_max: sliding ALONG the surface is free (that is the jitter being
    removed), leaving the surface is not. Returns (rows at arcs a, normal rms, normal max, lambda)."""
    n = max(4, int(np.ceil((A_[-1] - A_[0]) / spacing)) + 3)
    kv = PF.knots(n, A_[0], A_[-1]); B = PF.basis(A_, kv, n)
    D3 = np.zeros((n - 3, n))
    for i in range(n - 3): D3[i, i:i + 4] = (-1, 3, -3, 1)
    Y = R_.reshape(len(R_), -1)
    dr = np.gradient(R_, A_, axis=0); dc = np.gradient(R_, axis=1)          # surface normals at the raw points
    Nn = np.cross(dr, dc); Nn /= np.maximum(np.linalg.norm(Nn, axis=2), 1e-12)[..., None]
    BtB, BtY, DtD = B.T @ B, B.T @ Y, D3.T @ D3
    best, last = None, None
    for lam in 10.0 ** np.arange(-8, 3, 0.5):
        C = np.linalg.solve(BtB + lam * len(B) * DtD, BtY)
        Rf = (B @ C).reshape(R_.shape); en = np.abs(((Rf - R_) * Nn).sum(2))
        rms, mx = float(np.sqrt((en ** 2).mean())), float(en.max()); last = (C, rms, mx, lam)
        if rms <= nrm_rms and mx <= nrm_max: best = last
        elif best is not None: break
    if best is None:
        C = np.linalg.solve(BtB + 1e-8 * len(B) * DtD, BtY); Rf = (B @ C).reshape(R_.shape); en = np.abs(((Rf - R_) * Nn).sum(2))
        best = (C, float(np.sqrt((en ** 2).mean())), float(en.max()), 1e-8)
    C = best[0]
    return (lambda a: (PF.basis(np.asarray(a, float), kv, n) @ C).reshape(len(a), R_.shape[1], 3)), best[1], best[2], best[3]


def u_grid(car, verbose=True):
    """the U sweep: dict(grid (rows, cols, 3) m, E0 row, npil, rows_pil, sweep = sweep_grid's dict)"""
    import sweep_build as SW
    import strip_build as SB
    SW.SIDE_C2 = os.environ.get('HT_C2', '1') == '1'          # skirt = near-arc: curvature at D, G2 blend
    V, F, N, pcs = pieces(car)
    skin = pcs['skin']; c = V[skin].mean(1)
    b = np.array(PILLAR_CLIP).reshape(3, 2)
    Fp = skin[((c >= b[:, 0]) & (c <= b[:, 1])).all(1)]                    # the proven pillar piece (455 tris)
    cache = os.environ.get('HT_SWEEP_CACHE')                               # pickle of the sweep this script wrote itself (debug cache: skips 2 min)
    if cache and os.path.exists(cache):
        import pickle; g = pickle.load(open(cache, 'rb'))
    else:
        g = SW.sweep_grid(V, Fp, N, s_lim=S_LIM, x_stop=0.0, Fm=skin, step_f=STEP_F, verbose=verbose,
                          edge_cos=float(os.environ.get('HT_EDGE_COS', 0)) or None)   # chord filter: off (upset the corner march)
        if cache:
            import pickle; pickle.dump(g, open(cache, 'wb'))
    X = np.array([p['X'] for _, _, p in g['st']]); raw = g['raw'].copy(); npil = g['npil']
    if os.environ.get('HT_STEADY', '1') == '1':
        raw = steady_rows(g, verbose, phi0=float(os.environ.get('HT_PHI0', 15)))
    keep = X[:, 0] > 0.002                                                   # left half only (the march overshoots)
    keep[:npil] = True
    X, raw = X[keep], raw[keep]
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))]
    t_end = (X[-1] - X[-2]) / np.linalg.norm(X[-1] - X[-2])
    Lc = arc[-1] + X[-1, 0] / max(-t_end[0], 0.2)                           # arc of the centreline crossing
    # one symmetric data set: left stations + mirrored ones at arc 2 Lc - a
    A_ = np.r_[arc, (2 * Lc - arc)[::-1]]
    R_ = np.r_[raw, (raw * MIR)[::-1]]
    nr, nc, _ = raw.shape
    fsm, nrms, nmax_, lam = smooth_rows(A_, R_, spacing=float(os.environ.get('HT_SPACING', 0.03)))
    # evaluate: pillar stations where they were; the foot evenly from the pillar's end to the centre (and mirrored)
    a_p = arc[:npil]
    nf = max(2, int(np.ceil((Lc - a_p[-1]) / STEP_F)))
    a_f = np.linspace(a_p[-1], Lc, nf + 1)[1:]                              # ends exactly on the centre
    a_left = np.r_[a_p, a_f]
    a_all = np.r_[a_left, (2 * Lc - a_left[:-1])[::-1]]                     # the centre row once
    G = fsm(a_all)
    Graw_err = float(np.abs(fsm(A_) - R_).max())
    # exact symmetry: average each row with its mirror partner (removes round-off; the fit is symmetric already)
    Gm = (G + (G * MIR)[::-1]) / 2
    asym = float(np.abs(G - Gm).max()); G = Gm
    if verbose:
        print(f'U grid: {npil} pillar + {len(a_f)} foot stations per side, {len(a_all)} rows x {nc}, spine {2 * Lc * 1e3:.0f} mm, '
              f'smoothing: lambda {lam:.0e}, normal rms {nrms * 1e3:.3f} max {nmax_ * 1e3:.3f} mm (shift max {Graw_err * 1e3:.2f} mm), asymmetry {asym * 1e3:.4f} mm, '
              f'last left station x {X[-1, 0] * 1e3:.1f} mm', flush=True)
    return dict(grid=G, E0=G[:, 0], npil=npil, nrows=len(a_all), sweep=g, axis=g['axis'], centre=g['centre'], s=g['s'],
                raw=R_, raw_arc=A_, arc=a_all, fit=fsm(A_))


def build(car, out):
    V, F, N, pcs = pieces(car)
    skin = pcs['skin']
    U = u_grid(car)
    G = U['grid']; es, c0 = U['axis'], U['centre']; s0, s1 = U['s']; npil = U['npil']; nrow = len(G)
    esR, c0R = es * MIR, c0 * MIR
    res = []
    u_ = np.unique(skin); nout = N[u_].mean(0); nout /= np.linalg.norm(nout)
    res.append(dict(name='hatch:U', grid=(G * 1000).tolist(), frame=[c0.tolist(), es.tolist(), np.cross(nout, es).tolist(), nout.tolist()]))

    # which side of the pillar planes each skin triangle lies on (left half by the left pillar's axis, right by its mirror)
    cx = V[skin].mean(1)[:, 0]
    sv = np.where(cx[:, None] >= 0, (V[skin] - c0) @ es, (V[skin] - c0R) @ esR)
    # header: above both pillar tops
    Fh = skin[(sv < s0).any(1)]
    nj = int(os.environ.get('HT_JOIN', 3))                              # pillar end rows given to the header as data
    comps = PF.components(V, Fh)[0]
    Fh = max(comps, key=len) if comps else Fh
    e = PF.fit_panel('hatch:hdr', V, Fh, N, extra=np.r_[G[:nj], G[-nj:]].reshape(-1, 3))
    e['cut_planes'] = [[((c0 + s0 * es) * 1000).tolist(), es.tolist()], [((c0R + s0 * esR) * 1000).tolist(), esR.tolist()]]
    res.append(e)

    # deck: foot vertices on the deck side of the U's top edge (E0 row of the foot stations, both halves)
    Ft = skin[(sv > s1).any(1)]
    E0r = G[npil - 1:nrow - npil + 1, 0]
    Dr = G[npil - 1:nrow - npil + 1, 6] - E0r; Dr /= np.linalg.norm(Dr, axis=1)[:, None]
    uu = np.unique(Ft); kk = np.argmin(np.linalg.norm(V[uu][:, None] - E0r[None], axis=2), axis=1)
    dd = np.full(len(V), np.inf); dd[uu] = ((V[uu] - E0r[kk]) * Dr[kk]).sum(1)
    F_out = Ft[(dd[Ft] < 0.02).any(1)]; F_dat = Ft[(dd[Ft] < -0.001).all(1)]
    comps = [Fp for Fp in PF.components(V, F_out)[0] if len(Fp) >= 4]
    Fo = max(comps, key=len)
    vs_ = set(np.unique(Fo).tolist()); Fd = np.array([t for t in F_dat if t[0] in vs_], int).reshape(-1, 3)
    e = PF.fit_panel('hatch:deck', V, Fo, N, extra=(E0r[:, None] + np.array([0, 0.008, 0.016, 0.024])[None, :, None] * Dr[:, None]).reshape(-1, 3), data_F=Fd)
    fr_ = [np.array(x) for x in e['frame']]
    row = np.r_[[E0r[0] - 0.03 * (E0r[1] - E0r[0]) / np.linalg.norm(E0r[1] - E0r[0])], E0r,
                [E0r[-1] + 0.03 * (E0r[-1] - E0r[-2]) / np.linalg.norm(E0r[-1] - E0r[-2])]]
    Drx = np.r_[Dr[:1], Dr, Dr[-1:]]
    band = np.r_[row, (row + 0.3 * Drx)[::-1]]
    e['cut_grid_edge'] = dict(grid='hatch:U', near=(E0r * 1000).tolist(), dirs=Dr.tolist(),
                              fallback=[dict(poly=(PF.to_plane(band, fr_)[:, :2] * 1000).tolist(), frame=e['frame'])])
    res.append(e)
    print(f'header {len(Fh)} tris; deck {len(Fo)} tris ({len(Fd)} data)', flush=True)

    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'u_grid.npz'), grid=G, npil=npil, raw=U['raw'], raw_arc=U['raw_arc'], arc=U['arc'], fit=U['fit'])
    print('saved', os.path.join(out, 'panels_fit.json'))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
