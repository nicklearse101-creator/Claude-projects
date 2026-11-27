"""The front wing's SHOULDER roll, built curves first (27 Nov).

Kunos's wing turns from its side skin over to its top (beside the bonnet gap) through a smooth roll of vertex rows that
run the whole wing's length: the skin's top row (normal tilted ~30 deg from +x), then rows at ~51, 66, 74, 79, 84 and
89 deg (the flat top), then a fold into the bonnet gap (135 deg, not built here). Some rows are partial (74 deg
behind z 0.82, 84 deg ahead of 1.08).

Rows = mutual vertex chains along the car (neighbour with the most similar normal); each row is x(z), y(z) through its
vertices (PCHIP: rows are graphs over z). Stations at constant z (every STEP and at every row vertex); per station the
rows present there, ordered by tilt, joined as a rounded facet polygon (flare_build.rounded_profile: straight facets,
corners rounded with arms shared by turn); columns at fixed fractions of the profile's TURN (tilt), so the same part of
the roll lies on the same column at every station. One structured grid face.
    python shoulder_build.py CAR_DIR OUT_DIR"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wingskin_build as WS, flare_build as FB

TILT_LEVELS = (30, 51, 66, 74, 79, 84, 89)          # Kunos's rows by mean normal tilt (deg from +x)
STEP = float(os.environ.get('SH_STEP', 0.008))
NCOL = int(os.environ.get('SH_NCOL', 48))


def rows(car, verbose=True):
    X, NX, tilt = WS.skin_vertices(car)
    ch = [r for r in WS.shoulder_rows(X, NX, WS.skin_vertices.nb) if np.ptp(X[r, 2]) > 0.3 and tilt[r].mean() < 100]
    # chains -> levels (nearest mean tilt); chains of one level are merged (the skin's top row is two chains: 27-37 deg
    # behind z 1.37, 28-32 ahead)
    R = {}
    for r in ch:
        k = int(np.argmin([abs(tilt[r].mean() - t) for t in TILT_LEVELS]))
        if abs(tilt[r].mean() - TILT_LEVELS[k]) > 6: continue
        R.setdefault(k, []).append(r)
    # a level's chains must lie along the roll: within 60 mm under the 51 deg row (a skin chain beside the flare also
    # has a ~30 deg normal)
    if 1 in R:
        Q1 = X[np.concatenate(R[1])]; Q1 = Q1[np.argsort(Q1[:, 2])]
        y51 = lambda z: np.interp(z, Q1[:, 2], Q1[:, 1])
        for k in list(R):
            R[k] = [r for r in R[k] if np.median(y51(X[r, 2]) - X[r, 1]) < 0.06]
    out = {}
    for k, rs in sorted(R.items()):
        if not rs: continue
        Q = X[np.concatenate(rs)]; T = tilt[np.concatenate(rs)]; o = np.argsort(Q[:, 2]); Q, T = Q[o], T[o]
        keep = np.r_[True, np.diff(Q[:, 2]) > 1e-4]; Q, T = Q[keep], T[keep]
        out[k] = (Q, T)
        if verbose: print(f'row {TILT_LEVELS[k]:3d} deg: {len(Q):3d} vertices, z {Q[:, 2].min():.3f}..{Q[:, 2].max():.3f}', flush=True)
    return out


def at(row, z):
    """row's (x, y) at z (PCHIP over z); nan outside its z range"""
    from scipy.interpolate import PchipInterpolator
    Q = row[0]; ok = (z >= Q[0, 2] - 1e-9) & (z <= Q[-1, 2] + 1e-9)
    x = np.full(len(z), np.nan); y = np.full(len(z), np.nan)
    if len(Q) >= 2:
        x[ok] = PchipInterpolator(Q[:, 2], Q[:, 0])(z[ok]); y[ok] = PchipInterpolator(Q[:, 2], Q[:, 1])(z[ok])
    return x, y


def top_boundary(car):
    """piece 0's top edge along the wing (its boundary on the bonnet-gap side): the fold's return row (normal ~135 deg,
    z 0.72 - 1.88) and, behind it, the edge turning out to the door (the wing's top narrows to the A-pillar). Ordered by z."""
    import panel_fit as PF
    V, F, N = PF.load_mesh(car, 'GEO_body', raw=True)
    p = PF.crease_pieces(V, F, N)[0]; cc = V[p].mean(1); P0 = p[(cc[:, 0] > 0.5) & (cc[:, 2] > 0.6) & (cc[:, 1] > 0.15)]
    kk = np.round(V / 1e-6).astype(np.int64); _, wid = np.unique(kk, axis=0, return_inverse=True); wid = wid.ravel()
    rep = np.zeros(wid.max() + 1, int); rep[wid] = np.arange(len(wid))
    G = wid[P0]; E = np.sort(np.r_[G[:, [0, 1]], G[:, [1, 2]], G[:, [2, 0]]], 1); u, c = np.unique(E, axis=0, return_counts=True)
    be = u[c == 1]; M = V[rep[be]].mean(1); be = be[(M[:, 1] > 0.6) & (M[:, 0] < 0.70) & (M[:, 2] > 0.6)]
    Q = np.unique(V[rep[np.unique(be)]], axis=0)
    # the part from the door to the front corner's turn (the front corner, along y 0.6355, is not the shoulder's)
    Q = Q[(Q[:, 0] < 0.6935) & (Q[:, 1] > 0.64)]
    return Q[np.argsort(Q[:, 2])]


def grid(Rw, B):
    """B: the top boundary (x, y, z by z): every station's last point"""
    z0 = max(Rw[0][0][0, 2], B[0, 2]) + 1e-4; z1 = min(Rw[0][0][-1, 2], B[-1, 2]) - 1e-4
    zs = np.unique(np.r_[np.arange(z0, z1, STEP), z1, np.concatenate([q[0][:, 2] for q in Rw.values()]), B[:, 2]])
    zs = zs[(zs >= z0) & (zs <= z1)]
    # stations at least 3 mm apart (FreeCAD's interpolating surface rang between stations 0.3 mm apart: slivers along the roll)
    keep = [0]
    for i in range(1, len(zs)):
        if zs[i] - zs[keep[-1]] >= 0.003 or i == len(zs) - 1: keep.append(i)
    zs = zs[keep]
    XY = {k: at(Rw[k], zs) for k in Rw}
    bx = np.interp(zs, B[:, 2], B[:, 0]); by = np.interp(zs, B[:, 2], B[:, 1])
    G = []
    for j, z in enumerate(zs):
        # the rows present here that lie before the boundary along the profile (x falls along it: over the top to the gap)
        pts = [(XY[k][0][j], XY[k][1][j]) for k in sorted(Rw) if np.isfinite(XY[k][0][j]) and (k == 0 or XY[k][0][j] > bx[j] + 0.0015)]
        pts.append((bx[j], by[j]))
        P = np.array(pts)                                         # (x, y): profile in the station plane, skin top first
        C, ci = FB.rounded_profile(np.c_[P[:, 1], P[:, 0]])       # (y, x) as (d, x): it only needs a 2D polyline
        C = C[:, ::-1]                                            # back to (x, y)
        tg = np.gradient(C, axis=0); ang = np.unwrap(np.arctan2(tg[:, 1], tg[:, 0]))
        # columns at fixed fractions of the TURN (tangent angle) between the ends; within straight facets (no turn) by
        # arc length (the turn stalls there)
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
        # cumulative ABSOLUTE turn (always increasing: |ang - ang0| ran backwards where the profile's tangent wiggles and
        # the columns jumped - folds, white slivers along the roll) mixed with arc length
        ct = np.r_[0, np.cumsum(np.abs(np.diff(ang)))]
        w = float(os.environ.get('SH_WTURN', 0.3)) * ct / max(ct[-1], 1e-9) + (1 - float(os.environ.get('SH_WTURN', 0.3))) * s / s[-1]   # (0.7 turn: columns 0.35 mm apart at the fold - FreeCAD's surface rang)
        t = np.linspace(0, 1, NCOL)
        G.append(np.c_[np.interp(t, w, C[:, 0]), np.interp(t, w, C[:, 1]), np.full(NCOL, z)])
    return zs, np.array(G)


def build(car, out):
    Rw = rows(car)
    B = top_boundary(car)
    print(f'top boundary: {len(B)} vertices, z {B[0, 2]:.3f}..{B[-1, 2]:.3f}', flush=True)
    zs, G = grid(Rw, B)
    print(f'grid: {len(zs)} stations (z {zs[0]:.3f}..{zs[-1]:.3f}) x {G.shape[1]} columns', flush=True)
    res = [dict(name='shoulder:L', structured=True, maxlen=float(os.environ.get('SH_MAXLEN', 5)), grid=(G * 1000).tolist(),
                frame=[[0, 0, 0], [0, 0, 1], [0, 1, 0], [1.0, 0, 0]])]
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'shoulder_grid.npz'), grid=G, z=zs)
    print('saved', os.path.join(out, 'panels_fit.json'), flush=True)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
