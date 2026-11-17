"""AE86 bumpers as swept bands (first build: the rear bumper's main profile).

    python bumper_build.py CAR_DIR OUT_DIR [rear]

A Kunos bumper (GEO_rearbumper) is one profile swept along a U-shaped plan line: from one wheel arch round the tail to
the other. Its crease pieces are BANDS along the bumper: every vertical section square to the plan line crosses them in
the same order (rear, top to bottom: [inner lip r5, step r17: interrupted at x 0.34-0.55, a strip later] top r1, edge roll r12, upper face r0, groove r21 + r20,
lower face r0, lower slope r3). Below r3 the section changes (centre recess vs side parts): those pieces are built
separately (generic faces for now).

Build:
- spine: the plan line of the top edge (r1 / r12 shared vertices), one symmetric smoothing curve in plan (x, z);
- stations every STEP along it, vertical planes square to it; each section chained, split into runs by crease piece,
  matched to the band sequence (either direction); each run resampled evenly in arc length between its two crease
  points (consecutive bands share those points exactly);
- left half (x >= 0) only, mirrored: one symmetric set of rows; smoothed along the spine in each row's own frame
  (hatch_build.smooth_rows_local: a turn stays exact) and evaluated evenly, centre row once;
- split back into one grid face per band ('rbump:bK', structured mesh in the FreeCAD stage). Shared rows -> the bands
  meet within the FreeCAD approximation tolerance (0.02 mm).
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path:
    sys.path.append(r'D:\ClaudeData\pylibs')
import panel_fit as PF

MIR = np.array([-1.0, 1.0, 1.0])
SPEC = dict(rear=dict(mesh='GEO_rearbumper', bands=[1, 12, 0, 21, 20, 0, 3], spine_pair=(1, 12), anchor_band=2, name='rbump',
                      centre_z=-1.55, mm_per_col=5.0))
STEP = float(os.environ.get('BB_STEP', 0.015))


def spine(V, pcs, pair, centre_z, step=0.001):
    """plan line (x, z) of the edge shared by crease pieces pair, left half (x >= 0) from the centre out, as a dense
    3D polyline at y = 0 (m) with arc lengths; symmetric by construction (mirrored points, fit, left half)"""
    import strip_build as SB
    key = lambda X: np.round(X / 2e-5).astype(np.int64)
    A = {tuple(k) for k in key(V[np.unique(pcs[pair[0]])])}
    X = np.array([v for v, k in zip(V[np.unique(pcs[pair[1]])], key(V[np.unique(pcs[pair[1]])])) if tuple(k) in A])
    X = np.unique(np.round(X, 6), axis=0)
    X = np.r_[X, X * MIR]
    ang = np.arctan2(X[:, 0], -(X[:, 2] - centre_z))            # 0 at the tail centre, + towards x > 0
    X = X[np.argsort(ang)]; P = np.c_[X[:, 0], np.zeros(len(X)), X[:, 2]]
    a = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    f = SB.fit_graph(a, P, [0, a[-1]], tol=1e-3, nmax=int(np.clip(a[-1] / 0.05, 4, 60)), mu=1e-4)
    S = SB.eval_graph(f, np.linspace(0, a[-1], int(a[-1] / step) + 1))
    S = (S + (S * MIR)[::-1]) / 2                               # exact symmetry
    i0 = int(np.argmin(np.abs(S[:, 0])))
    L = S[i0:]; L[0, 0] = 0.0
    return L, np.r_[0, np.cumsum(np.linalg.norm(np.diff(L, axis=0), axis=1))], f['err']


def _runs(V, T, Lb, cen, o, t):
    import sweep_build as SW
    from blend_build import _section
    m = np.linalg.norm((cen - o)[:, [0, 2]], axis=1) < 0.25
    segs, tri = _section(T[m], o, t)
    if len(segs) < 5: return None, None
    Q, tr = SW._chain_near(segs, tri, o)
    lab = Lb[np.nonzero(m)[0][tr]]
    runs = []
    for k, l in enumerate(lab):
        if not runs or runs[-1][0] != l: runs.append([l, k, k])
        else: runs[-1][2] = k
    return Q, runs


def _match(seq, sq):
    for rev in (False, True):
        q = sq[::-1] if rev else sq
        for j in range(len(seq) - len(q) + 1):
            if seq[j:j + len(q)] == q: return rev, j
    return None


def station_rows(V, pcs, bands, Sp, arc, step, ncol, verbose=True, anchor_band=2, s_max=None, offsets=None):
    """rows (n_st, sum(ncol) - len(bands) + 1, 3) of the band sequence at stations every `step` along the left half's
    spine (arc positions returned too); stations whose section does not hold the full sequence are skipped.
    With `offsets` (per band: the columns' arc offsets from the band's crease on the anchor side, m) the stations past
    the last full one (up to s_max, towards the arch) give PARTIAL rows: the longest run of consecutive bands holding
    the anchor band is sampled at those fixed offsets (a band cut short by the arch outline is not squeezed: its
    columns past the outline are NaN, extrapolated later and trimmed away)."""
    Fb = np.vstack([pcs[b] for b in sorted(set(bands))]); Lb = np.concatenate([[b] * len(pcs[b]) for b in sorted(set(bands))])
    T = V[Fb]; cen = T.mean(1); yb = float(np.median(V[np.unique(pcs[bands[0]])][:, 1]))
    ncs = int(sum(ncol) - len(bands) + 1); c0 = np.cumsum([0] + [n - 1 for n in ncol])
    rows, arcs, skipped, partial = [], [], [], 0
    s_end = arc[-1] if s_max is None else s_max
    for s in np.arange(0.0, s_end + 1e-9, step):
        if s <= arc[-1]:
            i = int(np.clip(np.searchsorted(arc, s), 1, len(Sp) - 2))
            o = Sp[i].copy(); t = Sp[min(i + 1, len(Sp) - 1)] - Sp[i - 1]
        else:                                                            # past the spine's end: straight on
            t = Sp[-1] - Sp[-3]; o = Sp[-1] + (s - arc[-1]) * t / np.linalg.norm(t)
        t = t.copy(); t[1] = 0; t /= np.linalg.norm(t); o = o.copy(); o[1] = yb
        Q, runs = _runs(V, T, Lb, cen, o, t)
        if Q is None: skipped.append(s); continue
        seq = [r[0] for r in runs]
        hit = _match(seq, bands)
        if hit is not None:
            rev, j = hit
            rr = runs[j:j + len(bands)]
            if rev: rr = rr[::-1]
            row = []
            for k, (l, a, b) in enumerate(rr):
                P = Q[a:b + 2]
                if rev: P = P[::-1]
                d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
                q = np.linspace(0, d[-1], ncol[k])
                R = np.c_[[np.interp(q, d, P[:, c]) for c in range(3)]].T
                row.append(R if k == 0 else R[1:])
            rows.append(np.vstack(row)); arcs.append(s); continue
        if offsets is None or not arcs or s < arcs[-1]: skipped.append(s); continue
        # partial: the longest run of consecutive bands holding the anchor band
        best = None
        for k0 in range(anchor_band + 1):
            for k1 in range(len(bands) - 1, anchor_band - 1, -1):
                if k1 - k0 + 1 < 2: continue
                h = _match(seq, bands[k0:k1 + 1])
                if h is not None and (best is None or k1 - k0 > best[1] - best[0]): best = (k0, k1, h)
        if best is None: break
        k0, k1, (rev, j) = best
        rr = runs[j:j + k1 - k0 + 1]
        if rev: rr = rr[::-1]
        row = np.full((ncs, 3), np.nan)
        for kk, (l, a, b) in enumerate(rr):
            k = k0 + kk
            P = Q[a:b + 2]
            if rev: P = P[::-1]
            d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
            free_end = (k == k0 and k < anchor_band) or (k == k1 and k > anchor_band)   # cut by the outline here?
            if k < anchor_band:                                             # above the anchor: measured from its lower end
                q = d[-1] - offsets[k][::-1]
            else: q = offsets[k]
            if not free_end: q = np.linspace(0, d[-1], ncol[k])           # both creases present: evenly, as the full rows
            ok = (q >= -1e-6) & (q <= d[-1] + 1e-6)
            R = np.c_[[np.interp(q, d, P[:, c]) for c in range(3)]].T; R[~ok] = np.nan
            row[c0[k]:c0[k] + ncol[k]] = np.where(np.isnan(row[c0[k]:c0[k] + ncol[k]]), R, row[c0[k]:c0[k] + ncol[k]])
        rows.append(row); arcs.append(s); partial += 1
    if verbose:
        print(f'stations: {len(rows)} ({partial} partial, towards the arch) of {len(rows) + len(skipped)} (arc {arcs[0]*1e3:.0f}..{arcs[-1]*1e3:.0f} mm'
              f' of {arc[-1]*1e3:.0f}); skipped at ' + ', '.join(f'{x*1e3:.0f}' for x in skipped[:12]) + (' ...' if len(skipped) > 12 else ''), flush=True)
    return np.array(rows), np.array(arcs)


def fill_nan_rows(R, A):
    """NaN columns of the partial rows carried on from their last valid rows (G1: a cubic through the last 4 along the
    spine, its end tangent), so the grid stays whole; they lie past the arch outline and are trimmed away"""
    R = R.copy()
    for j in range(R.shape[1]):
        ok = ~np.isnan(R[:, j, 0])
        if ok.all(): continue
        iv = np.nonzero(ok)[0]; last = iv[-1]
        for i in range(iv[0], last):                                     # gaps between valid rows: along the spine
            if np.isnan(R[i, j, 0]): R[i, j] = [np.interp(A[i], A[iv], R[iv, j, c]) for c in range(3)]
        P = R[iv[-4:], j]; a = A[iv[-4:]]
        c = np.linalg.lstsq(np.vander(a - a[-1], min(4, len(a)), increasing=True), P, rcond=None)[0]
        tg = c[1] if len(c) > 1 else np.zeros(3)
        for i in range(last + 1, len(R)):
            if np.isnan(R[i, j, 0]): R[i, j] = R[last, j] + (A[i] - A[last]) * tg
    return R


def grid_project(G, X, iters=8):
    """closest points of X on the grid's index-space spline (row index s, column index t): (s, t, distance m); as
    hatch_build.grid_project, with the degree lowered for narrow grids (a 2 mm groove band has 3 columns)"""
    from scipy.interpolate import RectBivariateSpline
    from scipy.spatial import cKDTree
    nr, nc, _ = G.shape; kx, ky = min(3, nr - 1), min(3, nc - 1)
    Sp = [RectBivariateSpline(np.arange(nr, dtype=float), np.arange(nc, dtype=float), G[:, :, k], kx=kx, ky=ky, s=0) for k in range(3)]
    def ev(s, t, a=0, b=0): return np.stack([Sp[k].ev(s, t, dx=a, dy=b) for k in range(3)], -1)
    ss, tt = np.meshgrid(np.arange(0, nr - 1 + 1e-9, 0.25), np.arange(0, nc - 1 + 1e-9, 0.25), indexing='ij')
    _, k = cKDTree(ev(ss.ravel(), tt.ravel())).query(X); s, t = ss.ravel()[k].copy(), tt.ravel()[k].copy()
    for _ in range(iters):
        P = ev(s, t); Su, Sv = ev(s, t, 1, 0), ev(s, t, 0, 1); r = X - P
        A11, A12, A22 = (Su * Su).sum(1), (Su * Sv).sum(1), (Sv * Sv).sum(1); b1, b2 = (r * Su).sum(1), (r * Sv).sum(1)
        det = A11 * A22 - A12 ** 2 + 1e-18
        s = np.clip(s + (A22 * b1 - A12 * b2) / det, 0, nr - 1); t = np.clip(t + (A11 * b2 - A12 * b1) / det, 0, nc - 1)
    return s, t, np.linalg.norm(X - ev(s, t), axis=1)


def others(V, F, N, pcs, bands, pre, amin=2e-5):
    """every crease piece that is not a swept band, as panel_fit's 'rall' path builds a part: narrow pieces as ruled
    strips (strip_build) whose sides on a neighbour are that neighbour's BUILT edge, wide pieces as fitted faces. Every
    face of piece r<i> is named '<pre>:r<i>...' (the bands too: '<pre>:r0b2', '<pre>:r0eL'), so a strip side's
    nb_name '<pre>:r<nb>' finds its neighbour's faces by prefix."""
    import strip_build as SB
    out = []
    st = SB.find_strips(V, F, N, pcs, PF.components, PF.boundary_loops, amin=amin)
    # crease pieces of 1-3 triangles (the small folds at the arch ends are fans of facets, each its own crease piece):
    # too small for a fitted face (no outline wire). Touching ones (a shared edge) that face the same way are one
    # group -> one corner fill, its outline snapped onto the built edges in the FreeCAD stage
    _, wid = PF.components(V, F)
    tiny = [ri for ri, Fr in enumerate(pcs) if len(Fr) <= 3 and ri not in set(bands) and ri not in st]
    nr_ = {ri: (lambda n: n / np.linalg.norm(n))(N[pcs[ri]].mean((0, 1))) for ri in tiny}
    vs_ = {ri: set(wid[pcs[ri].ravel()]) for ri in tiny}
    par = {ri: ri for ri in tiny}
    def root(a):
        while par[a] != a: a = par[a]
        return a
    for i, a in enumerate(tiny):
        for b in tiny[i + 1:]:
            if len(vs_[a] & vs_[b]) >= 2 and nr_[a] @ nr_[b] > 0.3: par[root(b)] = root(a)
    groups = {}
    for ri in tiny: groups.setdefault(root(ri), []).append(ri)
    for g in groups.values():
        cf = corner_fill(V, F, N, np.concatenate([pcs[r] for r in g]), f'{pre}cf:r{g[0]}')
        if cf: out.append(cf)
        else: print(f'{pre}cf:r{g[0]} ({len(g)} pieces): no single outline - skipped', flush=True)
    tiny = set(tiny)
    for ri, Fr in enumerate(pcs):
        if ri in set(bands): continue
        T_ = V[Fr]; A_ = np.linalg.norm(np.cross(T_[:, 1] - T_[:, 0], T_[:, 2] - T_[:, 0]), axis=1).sum() / 2
        if A_ < amin: continue
        if ri in st:
            s_ = st[ri]
            for sd in [x for sub in s_.get('subs', [s_]) for x in sub['sides']]:
                for r in [sd] + list(sd.get('runs', [])):
                    if isinstance(r['key'], str): continue
                    r['nb_name'] = None if r['nb'] is None else f'{pre}:r{r["nb"]}'
                    r['nb_strip'] = r['nb'] in st and r['nb'] not in set(bands)
                    r['key'] = f'{pre}:' + '|'.join(str(x) for x in r['key'])
            subs = s_.get('subs') or [s_]
            for k, sub in enumerate(subs):
                out.append(dict(name=f'{pre}:r{ri}' + (f'f{k}' if len(subs) > 1 else ''), strip=sub, frame=sub['frame']))
            continue
        if ri in tiny: continue              # grouped below
        parts = PF.wrap_split(V, Fr, N)
        for wi, Fw in enumerate(parts):
            if len(parts) > 1 and len(Fw) < 4: continue
            nm = f'{pre}:r{ri}' + (f'w{wi}' if len(parts) > 1 else '')
            try:
                out.append(PF.fit_panel(nm, V, Fw, N, verbose=False))
            except Exception as ex:
                cf = corner_fill(V, F, N, Fw, f'{pre}cf:r{ri}' + (f'w{wi}' if len(parts) > 1 else ''))
                if cf: out.append(cf)
                print(f'{nm} fit failed ({ex}): ' + ('corner fill' if cf else 'skipped'), flush=True)
    print(f'other pieces: {sum(1 for o in out if o.get("strip"))} strips, {sum(1 for o in out if o.get("corner_fill"))} corner fills, '
          f'{sum(1 for o in out if not o.get("strip") and not o.get("corner_fill"))} faces', flush=True)
    return out


def corner_fill(V, F, N, Fr, name):
    """a small piece as a corner fill (as bonnet_build): its one outline every 1 mm + inner vertices, in mm"""
    _, wid = PF.components(V, F); rep = {}
    for i, w in enumerate(wid): rep.setdefault(w, i)
    loops = PF.boundary_loops(Fr, wid)
    if len(loops) != 1 and len(Fr) == 1: loops = [list(wid[Fr[0]])]   # a lone triangle: its own three corners
    if len(loops) != 1: return None
    Q = V[[rep[w] for w in loops[0]]] * 1000; Q = np.r_[Q, Q[:1]]
    dq = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.arange(0, dq[-1], 1.0)
    R = np.c_[[np.interp(t, dq, Q[:, k]) for k in range(3)]].T
    inner = V[[rep[w] for w in sorted(set(wid[Fr.ravel()]) - set(loops[0]))]] * 1000 if len(Fr) > 1 else np.zeros((0, 3))
    T = V[Fr] * 1000; A = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2
    if A < 0.5 or len(R) < 3: return None                  # degenerate slivers (0 mm2 facets)
    nrm = N[Fr].mean((0, 1)); nrm /= np.linalg.norm(nrm)
    return dict(name=name, frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0], nrm.tolist()],
                corner_fill=dict(outline=R.tolist(), inner=inner.tolist(), area=float(A), normal=nrm.tolist()))


def build(car, out, which='rear'):
    import hatch_build as HB
    sp = SPEC[which]
    V, F, N = PF.load_mesh(car, sp['mesh']); pcs = PF.crease_pieces(V, F, N)
    bands = sp['bands']
    Sp, arc, err = spine(V, pcs, sp['spine_pair'], sp['centre_z'])
    print(f'spine: {arc[-1]*1e3:.0f} mm (left half), fit max {err*1e3:.2f} mm', flush=True)
    # columns per band: from the band's typical width
    R0, _ = station_rows(V, pcs, bands, Sp, arc, 0.1, [3] * len(bands), verbose=False)
    w = [np.median([np.linalg.norm(np.diff(r[2 * k:2 * k + 3], axis=0), axis=1).sum() for r in R0]) for k in range(len(bands))]
    ncol = [int(np.clip(round(x * 1e3 / sp['mm_per_col']) + 1, 3, 40)) for x in w]
    print('bands', bands, 'widths', [round(x * 1e3, 1) for x in w], 'columns', ncol, flush=True)
    R, A = station_rows(V, pcs, bands, Sp, arc, STEP, ncol, anchor_band=sp['anchor_band'])
    # column offsets per band (from the crease on the anchor side) at the last full stations: for the partial rows
    c0_ = np.cumsum([0] + [n - 1 for n in ncol]); offs = []
    for k in range(len(bands)):
        Rk = R[-5:, c0_[k]:c0_[k] + ncol[k]]
        d = np.c_[np.zeros(len(Rk)), np.cumsum(np.linalg.norm(np.diff(Rk, axis=1), axis=2), axis=1)].mean(0)
        offs.append(d if k >= sp['anchor_band'] else d[-1] - d[::-1])
    if float(os.environ.get('BB_TAIL', 0)) > 0:      # partial rows towards the arch (tried 17 Nov: rows kink and fold there)
        R, A = station_rows(V, pcs, bands, Sp, arc, STEP, ncol, anchor_band=sp['anchor_band'], s_max=arc[-1] + float(os.environ['BB_TAIL']), offsets=offs)
        R = fill_nan_rows(R, A)
    if A[0] > 1e-6:                                             # the centre station: the mirror plane
        pass
    # symmetric data set: left rows + mirrored rows at arcs -a
    keep = A > 1e-6
    A_ = np.r_[-A[keep][::-1], A]; R_ = np.r_[(R[keep] * MIR)[::-1], R]
    ab = sp['anchor_band']; anchor = int(np.cumsum([0] + [n - 1 for n in ncol])[ab] + ncol[ab] // 2)     # a point on the upper face
    fsm, nrms, nmax_, lam = HB.smooth_rows_local(A_, R_, spacing=float(os.environ.get('BB_SPACING', 0.03)), col=anchor,
                                                 nrm_rms=1e-4, nrm_p99=4e-4)
    n_half = int(np.ceil(A[-1] / STEP))
    a_l = np.linspace(0, A[-1], n_half + 1)
    a_all = np.r_[-a_l[::-1], a_l[1:]]
    G = fsm(a_all); G = (G + (G * MIR)[::-1]) / 2
    print(f'grid {G.shape[0]} rows x {G.shape[1]}: smoothing lambda {lam:.0e}, normal rms {nrms*1e3:.3f} max {nmax_*1e3:.2f} mm', flush=True)
    res = []
    nr = len(G); c0_ = np.cumsum([0] + [n - 1 for n in ncol])
    for k, b in enumerate(bands):
        nb = N[np.unique(pcs[b])].mean(0); nb /= np.linalg.norm(nb)
        res.append(dict(name=f'{sp["name"]}:r{b}b{k}', maxlen=float(os.environ.get('BB_MAXLEN', 8)), structured=True,
                        grid=(G[:, c0_[k]:c0_[k] + ncol[k]] * 1000).tolist(), frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0], nb.tolist()], band_piece=int(b)))
    # END faces at the arch (left; right = mirror): the sweep stops at its last full station; each band piece's
    # triangles past that station's plane are one fitted face over its own plane, with the sweep's last rows of that
    # piece as extra data (so it meets the band), cut exactly on the plane of the sweep's last row (the hatch header's
    # join to its pillars, 12 Nov). A piece split in two bands (the face r0 above and below the groove) is ONE end
    # face: the groove closes to a point before the arch and the face runs on round its end.
    Lr = G[-1]; m_ = Lr.mean(0); n_ = np.linalg.svd(Lr - m_)[2][2]
    if n_ @ (G[-2].mean(0) - m_) < 0: n_ = -n_                            # points back into the sweep (that side is cut)
    _, wid = PF.components(V, F)
    for b in dict.fromkeys(bands):
        ks = [k for k, bb in enumerate(bands) if bb == b]
        Fp = pcs[b]; cv = ((V[Fp] - m_) @ n_)
        Fe = Fp[(cv.min(1) < -1e-4) & (V[Fp][:, :, 0].mean(1) > 0)]        # any corner past the plane, left half
        if len(Fe) < 2: print(f'r{b}: no end region', flush=True); continue
        comps = PF.components(V, Fe)[0]; Fe = max(comps, key=len)
        X = np.vstack([G[-3:, c0_[k]:c0_[k] + ncol[k]].reshape(-1, 3) for k in ks])
        try:
            e = PF.fit_panel(f'{sp["name"]}:r{b}eL', V, Fe, N, extra=X, extra_rep=3)
        except Exception as ex:
            print(f'r{b}: end face failed ({ex})', flush=True); continue
        e['cut_planes'] = [[(m_ * 1000).tolist(), n_.tolist()]]
        res.append(e); res.append(dict(name=f'{sp["name"]}:r{b}eR', mirror_of=f'{sp["name"]}:r{b}eL'))
        print(f'r{b}: end face over {len(Fe)} triangles (bands {ks})', flush=True)
    if os.environ.get('BB_OTHERS', '1') == '1':
        res += others(V, F, N, pcs, bands, sp['name'])
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'grid.npz'), G=G, arcs=a_all, raw=R_, raw_arc=A_, ncol=ncol, bands=bands)
    print('saved', os.path.join(out, 'panels_fit.json'), flush=True)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'rear')
