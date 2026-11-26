"""The lower quarter AHEAD of the rear arch (arch -> door shut), built curves first (25 Nov).

Kunos's piece 0 below the body line between the rear arch and the door is one low-poly surface whose vertex ROWS run
straight along the car at constant height (x changes < 1 mm along a row): the rear band's profile carried forward -
body line (610 / 609, a 5 mm step in), the cove (604), the knee land (577 / 576 / 573), flat to ~512, then the
tuck-under to the sill's bottom edge (241). The quarter's band fits split it on two character lines, one of them only
arch -> door, and the strip between them had no face of its own (two hole-fill patches + the lower face's FreeCAD
approxSurface overlapping them: blotches in grey, Kunos vertices up to 4 mm off).

Now ONE structured grid: each vertex row one fair curve (x(z), y(z)) along the car, extended past both ends; per
station a centripetal Catmull-Rom through the rows (profile), resampled between rows by arc length with fixed column
counts (one grid); the grid runs past the region and is TRIMMED in FreeCAD on Kunos's own outline (arch edge, door
shut, the body-line cut at Y_TOP, the quarter / sill clip at z -0.5). The small ledge on it (its own Kunos pieces)
stays the quarter's: the surface runs on under it.
Ownership: these triangles are left out of the quarter (PF_NOBAND, panel_fit.load_mesh via rearband_build.band_owned).
    python frontband_build.py CAR_DIR OUT_DIR"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panel_fit as PF, bumper_build as BB, rearband_build as RB

# two such bands (25 Nov): the quarter's ahead of the rear arch ('rear') and the front wing's behind the front arch
# ('wing': the same profile mirrored - body line, cove, knee, ledge, tuck-under - between the arch and the door).
# zc: the quarter / wing clip plane (the sill / door side is cut off there), keep = side of it that is this band's
SIDES = dict(rear=dict(name='fband', zwin=(-1.2, -0.3), zc=-0.5, keep=-1.0, probe=(0.777, 0.55, -0.75)),
             wing=dict(name='wband', zwin=(0.3, 1.3), zc=0.62, keep=1.0, probe=(0.777, 0.55, 0.75), flat=(0.65, 0.78), ytop=float(os.environ.get('FB_WING_YTOP', 0.65)),
                       wall=tuple(float(v) for v in (os.environ.get('FB_WALL') or '0.55,1.0,0.025').split(',')) if os.environ.get('FB_WALL', '0') != '0' else None,
                       end=dict(A=(0.9566, 0.6351), C=(0.9059, 0.6086), B=(0.8990, 0.5794))))
# end (wing, 26 Nov): Kunos's groove END = three vertices (z, y): A the upper ridge's end, B the lower ridge's end, C the
# groove bottom's end. The upper flank stops on C-A, the lower flank on B-C; the end face is the flat triangle A-B-C;
# the outer skin (the wing's) starts on A-B. Band trimmed exactly on B-C-A, the end face built between the band's edge
# and the wing's surface along A-B (assemble.py), the wing clipped exactly on A-B and the band's outline.
# ytop (wing, 25 Nov): the band reaches over the whole groove (upper ridge y 0.637, bottom 0.606, lower ridge 0.575: 7.5 mm
# deep, its ridges 1-2 mm radius) - the wing's panel fit had it as one approxSurface 3 mm shallow, ridges 1.5 mm low
# 'flat' (wing): the side skin behind the front arch is ONE Kunos piece with the arch FLARE (15-30 mm proud, rows jump
# out at z 0.80-0.86) - the band = only the triangles on the flat profile: every vertex within FB_FLAT_TOL of x(y),
# the profile taken from Kunos's vertices in the clearly flat stretch z flat[0]..flat[1]
SIDE = os.environ.get('FB_SIDE', 'rear')


_CAND = {}
def candidates(car, side=None, nowall=False):
    """(V, F, N, B): raw hatch-free GEO_body (as rearband_build.candidates) and the front band's triangles: piece 0
    (the side skin) reaching below Y_TOP, centroid ahead of z -1.2, left side, the connected part round PROBE"""
    sd = dict(SIDES[side or SIDE]); key = (car, side or SIDE, nowall)
    if nowall: sd['wall'] = None
    if key in _CAND: return _CAND[key]
    V, F, N, _ = RB.candidates(car)
    pcs = PF.crease_pieces(V, F, N, deg=20.0)
    probe = np.array([0.55, 0.56, -2.085])
    P0 = min(pcs[:5], key=lambda p: np.linalg.norm(V[p].mean(1) - probe, axis=1).min())
    T = V[P0]; c = T.mean(1)
    Q = P0[(c[:, 0] > 0) & (T[:, :, 1].min(1) < sd.get('ytop', RB.Y_TOP) - 1e-6) & (c[:, 2] > sd['zwin'][0]) & (c[:, 2] < sd['zwin'][1])]
    if sd.get('flat'):
        u = np.unique(Q); X = V[u]; m = (X[:, 2] > sd['flat'][0]) & (X[:, 2] < sd['flat'][1])
        yb = np.round(X[m, 1] / 0.002); prof = {}
        for k_, x_ in zip(yb, X[m, 0]): prof.setdefault(k_, []).append(x_)
        ky = np.array(sorted(prof)); kx = np.array([np.median(prof[k_]) for k_ in ky])
        xf = lambda y: np.interp(y / 0.002, ky, kx)
        T = V[Q]; tol = float(os.environ.get('FB_FLAT_TOL', 8e-3))
        ok = (np.abs(T[:, :, 0] - xf(T[:, :, 1])) < tol).all(1)
        if sd.get('wall'):
            # the groove's END WALL (26 Nov): the groove stops at a wall facing back (z ~0.90-0.94) and the skin ahead
            # of it is the arch flare's, up to 15 mm proud of the groove - take that skin in above the lip (y > y0, z <
            # z1), so the groove's vertex rows run on up the wall onto it (the rows carried the groove straight on)
            y0_, z1_, tol2 = sd['wall']
            ok |= (T[:, :, 1].min(1) > y0_) & (T[:, :, 2].max(1) < z1_) & (np.abs(T[:, :, 0] - xf(T[:, :, 1])) < tol2).all(1)
        Q = Q[ok]
    comps = PF.components(V, Q)[0]
    B = min(comps, key=lambda k: np.linalg.norm(V[np.unique(k)] - np.array(sd['probe']), axis=1).min())
    _CAND[key] = (V, F, N, B)
    return _CAND[key]


def owned(car, side=None):
    return candidates(car, side)[3]


def region(car):
    """the band's triangles cut on y = Y_TOP (below kept) and z = Z_CLIP (behind kept): (V, F, N)"""
    V, F, N, B = candidates(car)
    Vb, Fb, Nb = BB.clip_tris(V, B, N, np.array([0.0, SIDES[SIDE].get('ytop', RB.Y_TOP), 0.0]), np.array([0.0, 1.0, 0.0]), 0.0)
    sd = SIDES[SIDE]
    Vb, Fb, Nb = BB.clip_tris(Vb, Fb, Nb, np.array([0.0, 0.0, sd['zc']]), np.array([0.0, 0.0, -sd['keep']]), 0.0)
    return Vb, Fb, Nb


def outline(Vb, Fb, holes=False):
    """the region's outer boundary loop (3D points, m); holes=True: its inner loops instead (the ledge's footprint)"""
    _, wid = PF.components(Vb, Fb)
    loops = PF.boundary_loops(Fb, wid)
    pos = {}
    for i, w in enumerate(wid): pos.setdefault(int(w), Vb[i])
    L = max(loops, key=len)
    if holes:
        return [clean(np.array([pos[int(w)] for w in l])) for l in loops if l is not L and len(l) >= 4]
    return clean(np.array([pos[int(w)] for w in L]))


def clean(E, step=0.01):
    # the cuts leave points 0.1 mm apart (a self-touching wire in FreeCAD: trim invalid): merge points < 1 mm apart;
    # long chords (the cuts, 120 mm) densified every 10 mm so the (u, v) polyline follows the surface
    keep = [E[0]]
    for p in E[1:]:
        if np.linalg.norm(p - keep[-1]) >= 1e-3: keep.append(p)
    if np.linalg.norm(keep[-1] - keep[0]) < 1e-3: keep.pop()
    E = np.array(keep); out = []
    for a, b in zip(E, np.roll(E, -1, axis=0)):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += [a + (b - a) * t for t in np.arange(k) / k]
    return np.array(out)


def rows_of(car, verbose=True):
    """Kunos's vertex rows of the (uncut) band, each one fair curve: [(y_median, fx(z), fy(z), n, z range)]"""
    V, F, N, B = candidates(car, nowall=True)            # rows from the band's own triangles only (not the skin ahead)
    Sp = np.c_[np.full(200, 0.78), np.zeros(200), np.linspace(*SIDES[SIDE]['zwin'], 200)]
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Sp, axis=0), axis=1))]
    yt0 = RB.Y_TOP; RB.Y_TOP = SIDES[SIDE].get('ytop', yt0)        # (it clamps rows at RB.Y_TOP)
    try: rows = RB.vertex_rows_mutual(V, B, Sp, arc, min_n=2, top_y=9.0)
    finally: RB.Y_TOP = yt0
    dom = list(SIDES[SIDE]['zwin'])
    out = []
    for r in rows:
        z = r[:, 0] + SIDES[SIDE]['zwin'][0]; x = r[:, 2] + 0.78; y = r[:, 1]
        if len(r) == 2 and np.ptp(x) > 1e-3: continue                     # a diagonal pair at the ledge's end: not a row
        if np.median(y) > SIDES[SIDE].get('ytop', RB.Y_TOP) + 1e-3: continue
        if SIDES[SIDE].get('ytop') and os.environ.get('FB_TOPROW', '1') == '1' and np.median(y) > 0.641: continue   # (wing) above the ridge: the top row is Kunos's skin (below); vertex 'rows' there link two heights (0.650-0.676)   # (wing) a 'row' wandering in height (0.650-0.676: vertices of two heights linked) - not a row
        n = int(np.clip(np.ptp(z) / 0.08, 1, 6))
        if os.environ.get('FB_ROWFIT', 'interp') == 'interp' and len(r) >= 2:
            # through the row's vertices (straight between them, as Kunos's edges; ends held): the rows ARE straight
            # lines along the car except where the cove turns out into the arch edge over its last 17 mm (x 767 ->
            # 773) - a fair spline (and its outlier rejection) dropped that turn: 6 mm off
            o = np.argsort(z); zq, xq, yq = z[o], x[o], y[o]
            if SIDES[SIDE].get('end') and os.environ.get('FB_END', '1') == '1':
                # (wing) the groove's rows end ON the end line B-C-A: vertices past it are the end face's own corners
                # (604: 905.2 mm, 1 mm proud) - in the row they kinked it (a streak down the flank)
                past = end_past(zq, yq)
                if past.any() and (~past).sum() >= 2: zq, xq, yq = zq[~past], xq[~past], yq[~past]
            if SIDES[SIDE].get('ytop') and os.environ.get('FB_ROWEXT', '1') == '1' and 0.45 < np.median(y) < 0.574:
                # (wing) a row stopping short of the band's front edge (below the lower ridge, near the arch): on over
                # the band's OWN Kunos triangles at its height, 8 mm steps, until they end (carried flat it sat 1.4 mm in)
                ze = np.arange(zq[-1] + 0.008, 1.1, 0.008); xe = x_on(V, B, np.full(len(ze), np.median(y)), ze)
                k_ = np.argmax(~np.isfinite(xe)) if (~np.isfinite(xe)).any() else len(ze)
                if k_: zq, xq, yq = np.r_[zq, ze[:k_]], np.r_[xq, xe[:k_]], np.r_[yq, np.full(k_, np.median(y))]
            if os.environ.get('FB_WALL_ROWS', '0') == '1' and SIDES[SIDE].get('wall') and np.median(y) > SIDES[SIDE]['wall'][0] + 0.03:
                # past the row's front end: Kunos's own surface at the row's height (the groove's end wall, then the
                # flare skin), every 8 mm up to the wall zone's end - the loft climbs the wall instead of carrying on
                ze = np.arange(zq[-1] + 0.008, SIDES[SIDE]['wall'][1], 0.008)
                xe = x_on(V, B, np.full(len(ze), np.median(y)), ze)
                ok_ = np.isfinite(xe)
                if ok_.any():
                    k_ = np.argmax(~ok_) if (~ok_).any() else len(ze)      # up to the first miss
                    zq, xq, yq = np.r_[zq, ze[:k_]], np.r_[xq, xe[:k_]], np.r_[yq, np.full(k_, np.median(y))]
            if len(zq) >= 3 and os.environ.get('FB_ROWCR', '1') == '1':
                # smooth THROUGH the vertices (centripetal Catmull-Rom in (z, x, y)): straight segments kinked the
                # rows at every vertex - faint ripples in grey where neighbouring rows kink at different z
                C = RB.catmull_rom(np.c_[zq, xq, yq], 20); C = C[np.argsort(C[:, 0])]
                zq, xq, yq = C[:, 0], C[:, 1], C[:, 2]
            fx = ('i', zq, xq); fy = ('i', zq, yq)
        elif len(r) < 4 or n < 2:                                         # short: constant along the car
            fx = ('c', float(np.mean(x))); fy = ('c', float(np.mean(y)))
        else:
            # as many controls as the row has vertices (up to 10): the cove's rows turn out over their last 20 mm into
            # the arch edge (x 767 -> 773); a stiffer curve missed those vertices by 6 mm
            nn = int(os.environ.get('FB_ROWN', 0)) or int(np.clip(len(r), 4, 10))
            fx = PF.fit_func(z, x, dom, tol=0.1e-3, nmax=nn); fy = PF.fit_func(z, y, dom, tol=0.1e-3, nmax=nn)
        out.append((float(np.median(y)), fx, fy, len(r), (float(z.min()), float(z.max()))))
    if SIDES[SIDE].get('ytop') and os.environ.get('FB_TOPROW', '1') == '1':
        # (wing, 26 Nov) the top edge row: Kunos's own surface at y = ytop (big flat triangles above the ridge), every
        # 10 mm over the ridge rows' length - the band's top edge then lies ON Kunos's skin
        yt = SIDES[SIDE]['ytop']; zz = np.arange(SIDES[SIDE]['zwin'][0], SIDES[SIDE]['zwin'][1], 0.01)
        xx = x_on(V, F, np.full(len(zz), yt), zz)
        ok = np.isfinite(xx) & (xx > 0.7)
        if ok.sum() >= 3:
            out.append((yt, ('i', zz[ok], xx[ok]), ('c', yt), int(ok.sum()), (float(zz[ok].min()), float(zz[ok].max()))))
            print(f'top row: Kunos skin at y {yt:.3f}, z {zz[ok].min():.2f}..{zz[ok].max():.2f}', flush=True)
    out.sort(key=lambda t: t[0])
    if verbose:
        print(f'rows: {len(out)} (' + ', '.join(f'{t[0] * 1e3:.0f}' for t in out) + ')', flush=True)
    return out


def groove_end(E):
    """the band outline (3D, m) cut exactly on the groove end B-C-A; returns dict(band=(z, y) polygon, wing=(z, y)
    polygon the wing is clipped by (B-A straight instead of B-C-A), band3d=outline points with x to be set later)"""
    sys.path.append(r'D:\ClaudeData\pylibs')
    from shapely.geometry import Polygon
    from shapely import make_valid
    en = SIDES[SIDE]['end']; A, B, C = (np.array(en[k]) for k in 'ABC')
    P = make_valid(Polygon(E[:, [2, 1]]))
    # the strip over the groove (B.y up to the band's top), z 0.75..1.0, is the band's up to the end: Kunos's piece
    # outline there is a ragged edge of whole triangles (the skin ahead filtered out triangle by triangle)
    yt = E[:, 1].max()
    P = P.union(Polygon([(0.75, B[1]), (1.0, B[1]), (1.0, yt), (0.75, yt)]))
    def keep(front):
        return Polygon([(-1, -1), (3, -1), (3, B[1]), *front, (A[0], 1), (-1, 1)])
    Pb = P.intersection(keep([tuple(B), tuple(C), tuple(A)]))
    Pw = P.intersection(keep([tuple(B), tuple(A)]))
    big = lambda g: max(getattr(g, 'geoms', [g]), key=lambda q: q.area)
    Pb, Pw = big(Pb), big(Pw)
    zb, yb = np.array(Pb.exterior.coords).T
    pts = np.c_[np.full(len(zb), 0.78), yb, zb][:-1]
    print(f'groove end: band outline cut on B-C-A ({len(pts)} points), area {Pb.area * 1e4:.0f} cm2 (wing clip {Pw.area * 1e4:.0f})', flush=True)
    return dict(band=np.array(Pb.exterior.coords), wing=np.array(Pw.exterior.coords), band3d=clean(pts, step=0.003))


def end_past(z, y):
    """(wing) points (z, y) ahead of the groove end line B-C-A (by more than 0.2 mm), within its height B.y..A.y"""
    en = SIDES[SIDE]['end']; A, B, C = (np.array(en[k]) for k in 'ABC')
    ys = np.array([B[1], C[1], A[1]]); zs = np.array([B[0], C[0], A[0]])
    inside_h = (y >= B[1]) & (y <= A[1])
    return inside_h & (z > np.interp(y, ys, zs) + 2e-4)


def x_on(V, B, y, z):
    """x of the triangles B's surface at (y, z) (largest hit, the outer skin); nan where none covers the point"""
    T = V[B]; out = np.full(len(y), np.nan)
    for i, (yy, zz) in enumerate(zip(y, z)):
        a, b_, c = T[:, 0], T[:, 1], T[:, 2]
        d = (b_[:, 1] - c[:, 1]) * (a[:, 2] - c[:, 2]) + (c[:, 2] - b_[:, 2]) * (a[:, 1] - c[:, 1])
        ok = np.abs(d) > 1e-14
        l1 = ((b_[:, 1] - c[:, 1]) * (zz - c[:, 2]) + (c[:, 2] - b_[:, 2]) * (yy - c[:, 1])) / np.where(ok, d, 1)
        l2 = ((c[:, 1] - a[:, 1]) * (zz - c[:, 2]) + (a[:, 2] - c[:, 2]) * (yy - c[:, 1])) / np.where(ok, d, 1)
        l3 = 1 - l1 - l2; m = ok & (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if m.any(): out[i] = (l1 * a[:, 0] + l2 * b_[:, 0] + l3 * c[:, 0])[m].max()
    return out


def ev(f, z):
    z = np.atleast_1d(np.asarray(z, float))
    if isinstance(f, tuple) and f[0] == 'i': return np.interp(z, f[1], f[2])
    if isinstance(f, tuple): return np.full(len(z), f[1])
    # past its data a row carries on at its end value (rows are straight along the car; a spline's slope there is noise)
    return PF.eval_func(f, np.clip(z, f['dom_data'][0], f['dom_data'][1])) if 'dom_data' in f else PF.eval_func(f, z)


def build(car, out):
    Vb, Fb, Nb = region(car)
    T = Vb[Fb]; A_ = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2
    print(f'{SIDE} band: {len(owned(car))} Kunos triangles -> {len(Fb)} after the cuts (y {SIDES[SIDE].get('ytop', RB.Y_TOP):.4f}, z {SIDES[SIDE]['zc']}); area {A_ * 1e4:.0f} cm2; '
          f'y {Vb[:, 1].min():.3f}..{Vb[:, 1].max():.3f} z {Vb[:, 2].min():.3f}..{Vb[:, 2].max():.3f}', flush=True)
    R = rows_of(car)
    for _, fx, fy, n, zr in R:
        for f in (fx, fy):
            if isinstance(f, dict): f['dom_data'] = zr
    E = outline(Vb, Fb)
    END = None
    if SIDES[SIDE].get('end') and os.environ.get('FB_END', '1') == '1':
        END = groove_end(E)
        E = END['band3d']
    # the ledge (its own Kunos pieces, the quarter's) sits in a hole of this mesh: cut it out, so the ledge's edge strips
    # meet this band's real edge (they ran past under it: white slivers at the ledge's rear end)
    HL = outline(Vb, Fb, holes=True) if os.environ.get('FB_HOLES', '1') == '1' else []
    print(f'outline {len(E)} points, {len(HL)} holes ' + str([len(h) for h in HL]), flush=True)
    z0, z1 = E[:, 2].min() - 0.03, E[:, 2].max() + 0.03                  # stations past the region both ends
    zs = np.linspace(z0, z1, int(np.ceil((z1 - z0) / float(os.environ.get('FB_STEP', 0.01 if SIDES[SIDE].get('ytop') else 0.02)))) + 1)
    prof = lambda z: np.array([[ev(fx, z)[0], ev(fy, z)[0], z] for _, fx, fy, _, _ in R])
    # columns per segment between rows (fixed for the grid), from the profile at the middle station
    FLAT = []
    Pm = prof(0.5 * (z0 + z1)); seg = np.linalg.norm(np.diff(Pm, axis=0), axis=1)
    ncol = np.maximum(1, np.ceil(seg / float(os.environ.get('FB_DS', 0.006))).astype(int))
    if SIDES[SIDE].get('ytop') and os.environ.get('FB_TOPROW', '1') == '1':
        # (wing) the straight span above the ridge sampled as finely as the ridge (1.5 mm): coarse columns next to the
        # ridge's 1-2 mm rows made the surface ring 1.4 mm proud there
        # the groove's flanks too: each a flat Kunos facet between tight ridge / bottom rows (1-2 mm apart) - a long span
        # (> 8 mm) with a tight row (< 4 mm) at both ends is straight and finely sampled (the curve rang 1.4 mm deep)
        yq = np.array([r_[0] for r_ in R])
        FLAT = [len(seg) - 1] + [k for k in range(1, len(seg) - 1) if yq[k] > 0.56 and seg[k] > 0.008 and seg[k - 1] < 0.006 and seg[k + 1] < 0.006]
        for k in FLAT: ncol[k] = max(ncol[k], int(np.ceil(seg[k] / 0.0015)))
        print('straight spans (rows): ' + ', '.join(f'{yq[k] * 1e3:.0f}-{yq[k + 1] * 1e3:.0f}' for k in FLAT), flush=True)
    EXT = float(os.environ.get('FB_EXT', 0.004))
    G = []
    for z in zs:
        Q = prof(z)
        C = RB.catmull_rom(Q, 24)                                         # 24 samples per segment, rows included
        if SIDES[SIDE].get('ytop') and os.environ.get('FB_TOPROW', '1') == '1':
            # (wing) ridge -> top row: Kunos's flat facet, a straight span (the curve through the tight ridge rows
            # overshot it by 1.3 mm: a second ridge above the groove)
            for k_ in FLAT:
                C[24 * k_:24 * (k_ + 1) + 1] = Q[k_] + np.linspace(0, 1, 25)[:, None] * (Q[k_ + 1] - Q[k_])
        cols = []
        for k in range(len(Q) - 1):
            S = C[24 * k:24 * (k + 1) + 1]
            a = np.r_[0, np.cumsum(np.linalg.norm(np.diff(S, axis=0), axis=1))]
            t = np.linspace(0, a[-1], ncol[k] + 1)[:-1]
            cols += [np.c_[[np.interp(t, a, S[:, c]) for c in range(3)]].T]
        cols.append(Q[-1:])
        Gz = np.concatenate(cols)
        # past the bottom and top rows along the profile's end tangents (the trim lies inside the grid)
        tb = Gz[0] - Gz[1]; tt = Gz[-1] - Gz[-2]
        Gz = np.r_[[Gz[0] + tb / np.linalg.norm(tb) * EXT], Gz, [Gz[-1] + tt / np.linalg.norm(tt) * EXT]]
        G.append(Gz)
    G = np.array(G)
    if END is not None:
        # the trim points' x ON the grid surface (FreeCAD maps them to (u, v) by projection: 9 mm off in the groove they
        # would slide along it)
        ns, nc = G.shape[:2]; ii = np.arange(ns * nc).reshape(ns, nc)
        TG = np.r_[np.c_[ii[:-1, :-1].ravel(), ii[1:, :-1].ravel(), ii[1:, 1:].ravel()], np.c_[ii[:-1, :-1].ravel(), ii[1:, 1:].ravel(), ii[:-1, 1:].ravel()]]
        Vg = G.reshape(-1, 3); E = E.copy(); E[:, 0] = x_on(Vg, TG, E[:, 1], E[:, 2])
        bad = ~np.isfinite(E[:, 0])
        if bad.any():                                    # on the grid's very edge (rounding): the nearest grid point's x
            from scipy.spatial import cKDTree
            E[bad, 0] = Vg[cKDTree(Vg[:, 1:]).query(E[bad, 1:])[1], 0]
            print(f'trim: {bad.sum()} points on the grid edge (nearest grid x), max off {np.abs(E[bad, 1:] - Vg[cKDTree(Vg[:, 1:]).query(E[bad, 1:])[1], 1:]).max() * 1e3:.1f} mm', flush=True)
    print(f'grid: {G.shape[0]} stations (z {z0:.3f}..{z1:.3f}) x {G.shape[1]} columns', flush=True)
    res = [dict(name=SIDES[SIDE]['name'] + ':L', maxlen=float(os.environ.get('FB_MAXLEN', 6)), structured=False, grid=(G * 1000).tolist(),
                trim=(E * 1000).tolist(), trim_any=True, tess=float(os.environ.get('FB_TESS', 0.01 if SIDES[SIDE].get('ytop') else 0.05)), holes=[(H * 1000).tolist() for H in HL], frame=[[0, 0, 0], [0, 0, 1], [0, 1, 0], [1.0, 0, 0]])]
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'band_grid.npz'), grid=G, outline=E, **({'end_band': END['band'], 'end_wing': END['wing'], 'end_ABC': np.array([SIDES[SIDE]['end'][k] for k in 'ABC'])} if END is not None else {}), **{f'hole{i}': H for i, H in enumerate(HL)})
    print('saved', os.path.join(out, 'panels_fit.json'))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
