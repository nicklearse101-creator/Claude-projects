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
             wing=dict(name='wband', zwin=(0.3, 1.3), zc=0.62, keep=1.0, probe=(0.777, 0.55, 0.75), flat=(0.65, 0.78)))
# 'flat' (wing): the side skin behind the front arch is ONE Kunos piece with the arch FLARE (15-30 mm proud, rows jump
# out at z 0.80-0.86) - the band = only the triangles on the flat profile: every vertex within FB_FLAT_TOL of x(y),
# the profile taken from Kunos's vertices in the clearly flat stretch z flat[0]..flat[1]
SIDE = os.environ.get('FB_SIDE', 'rear')


_CAND = {}
def candidates(car, side=None):
    """(V, F, N, B): raw hatch-free GEO_body (as rearband_build.candidates) and the front band's triangles: piece 0
    (the side skin) reaching below Y_TOP, centroid ahead of z -1.2, left side, the connected part round PROBE"""
    sd = SIDES[side or SIDE]; key = (car, side or SIDE)
    if key in _CAND: return _CAND[key]
    V, F, N, _ = RB.candidates(car)
    pcs = PF.crease_pieces(V, F, N, deg=20.0)
    probe = np.array([0.55, 0.56, -2.085])
    P0 = min(pcs[:5], key=lambda p: np.linalg.norm(V[p].mean(1) - probe, axis=1).min())
    T = V[P0]; c = T.mean(1)
    Q = P0[(c[:, 0] > 0) & (T[:, :, 1].min(1) < RB.Y_TOP - 1e-6) & (c[:, 2] > sd['zwin'][0]) & (c[:, 2] < sd['zwin'][1])]
    if sd.get('flat'):
        u = np.unique(Q); X = V[u]; m = (X[:, 2] > sd['flat'][0]) & (X[:, 2] < sd['flat'][1])
        yb = np.round(X[m, 1] / 0.002); prof = {}
        for k_, x_ in zip(yb, X[m, 0]): prof.setdefault(k_, []).append(x_)
        ky = np.array(sorted(prof)); kx = np.array([np.median(prof[k_]) for k_ in ky])
        xf = lambda y: np.interp(y / 0.002, ky, kx)
        T = V[Q]; tol = float(os.environ.get('FB_FLAT_TOL', 8e-3))
        Q = Q[(np.abs(T[:, :, 0] - xf(T[:, :, 1])) < tol).all(1)]
    comps = PF.components(V, Q)[0]
    B = min(comps, key=lambda k: np.linalg.norm(V[np.unique(k)] - np.array(sd['probe']), axis=1).min())
    _CAND[key] = (V, F, N, B)
    return _CAND[key]


def owned(car, side=None):
    return candidates(car, side)[3]


def region(car):
    """the band's triangles cut on y = Y_TOP (below kept) and z = Z_CLIP (behind kept): (V, F, N)"""
    V, F, N, B = candidates(car)
    Vb, Fb, Nb = BB.clip_tris(V, B, N, np.array([0.0, RB.Y_TOP, 0.0]), np.array([0.0, 1.0, 0.0]), 0.0)
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


def clean(E):
    # the cuts leave points 0.1 mm apart (a self-touching wire in FreeCAD: trim invalid): merge points < 1 mm apart;
    # long chords (the cuts, 120 mm) densified every 10 mm so the (u, v) polyline follows the surface
    keep = [E[0]]
    for p in E[1:]:
        if np.linalg.norm(p - keep[-1]) >= 1e-3: keep.append(p)
    if np.linalg.norm(keep[-1] - keep[0]) < 1e-3: keep.pop()
    E = np.array(keep); out = []
    for a, b in zip(E, np.roll(E, -1, axis=0)):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / 0.01)))
        out += [a + (b - a) * t for t in np.arange(k) / k]
    return np.array(out)


def rows_of(car, verbose=True):
    """Kunos's vertex rows of the (uncut) band, each one fair curve: [(y_median, fx(z), fy(z), n, z range)]"""
    V, F, N, B = candidates(car)
    Sp = np.c_[np.full(200, 0.78), np.zeros(200), np.linspace(*SIDES[SIDE]['zwin'], 200)]
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Sp, axis=0), axis=1))]
    rows = RB.vertex_rows_mutual(V, B, Sp, arc, min_n=2, top_y=9.0)
    dom = list(SIDES[SIDE]['zwin'])
    out = []
    for r in rows:
        z = r[:, 0] + SIDES[SIDE]['zwin'][0]; x = r[:, 2] + 0.78; y = r[:, 1]
        if len(r) == 2 and np.ptp(x) > 1e-3: continue                     # a diagonal pair at the ledge's end: not a row
        if np.median(y) > RB.Y_TOP + 1e-3: continue
        n = int(np.clip(np.ptp(z) / 0.08, 1, 6))
        if os.environ.get('FB_ROWFIT', 'interp') == 'interp' and len(r) >= 2:
            # through the row's vertices (straight between them, as Kunos's edges; ends held): the rows ARE straight
            # lines along the car except where the cove turns out into the arch edge over its last 17 mm (x 767 ->
            # 773) - a fair spline (and its outlier rejection) dropped that turn: 6 mm off
            o = np.argsort(z); zq, xq, yq = z[o], x[o], y[o]
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
    out.sort(key=lambda t: t[0])
    if verbose:
        print(f'rows: {len(out)} (' + ', '.join(f'{t[0] * 1e3:.0f}' for t in out) + ')', flush=True)
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
    print(f'{SIDE} band: {len(owned(car))} Kunos triangles -> {len(Fb)} after the cuts (y {RB.Y_TOP:.4f}, z {SIDES[SIDE]['zc']}); area {A_ * 1e4:.0f} cm2; '
          f'y {Vb[:, 1].min():.3f}..{Vb[:, 1].max():.3f} z {Vb[:, 2].min():.3f}..{Vb[:, 2].max():.3f}', flush=True)
    R = rows_of(car)
    for _, fx, fy, n, zr in R:
        for f in (fx, fy):
            if isinstance(f, dict): f['dom_data'] = zr
    E = outline(Vb, Fb)
    # the ledge (its own Kunos pieces, the quarter's) sits in a hole of this mesh: cut it out, so the ledge's edge strips
    # meet this band's real edge (they ran past under it: white slivers at the ledge's rear end)
    HL = outline(Vb, Fb, holes=True) if os.environ.get('FB_HOLES', '1') == '1' else []
    print(f'outline {len(E)} points, {len(HL)} holes ' + str([len(h) for h in HL]), flush=True)
    z0, z1 = E[:, 2].min() - 0.03, E[:, 2].max() + 0.03                  # stations past the region both ends
    zs = np.linspace(z0, z1, int(np.ceil((z1 - z0) / float(os.environ.get('FB_STEP', 0.02)))) + 1)
    prof = lambda z: np.array([[ev(fx, z)[0], ev(fy, z)[0], z] for _, fx, fy, _, _ in R])
    # columns per segment between rows (fixed for the grid), from the profile at the middle station
    Pm = prof(0.5 * (z0 + z1)); seg = np.linalg.norm(np.diff(Pm, axis=0), axis=1)
    ncol = np.maximum(1, np.ceil(seg / float(os.environ.get('FB_DS', 0.006))).astype(int))
    EXT = float(os.environ.get('FB_EXT', 0.004))
    G = []
    for z in zs:
        Q = prof(z)
        C = RB.catmull_rom(Q, 24)                                         # 24 samples per segment, rows included
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
    print(f'grid: {G.shape[0]} stations (z {z0:.3f}..{z1:.3f}) x {G.shape[1]} columns', flush=True)
    res = [dict(name=SIDES[SIDE]['name'] + ':L', maxlen=float(os.environ.get('FB_MAXLEN', 6)), structured=False, grid=(G * 1000).tolist(),
                trim=(E * 1000).tolist(), trim_any=True, holes=[(H * 1000).tolist() for H in HL], frame=[[0, 0, 0], [0, 0, 1], [0, 1, 0], [1.0, 0, 0]])]
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'band_grid.npz'), grid=G, outline=E)
    print('saved', os.path.join(out, 'panels_fit.json'))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
