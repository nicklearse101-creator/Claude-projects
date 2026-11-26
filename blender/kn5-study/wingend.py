"""The front wing's groove END (26 Nov): exact clipping of a mesh on a side-view polygon, and the end face.

Kunos's groove ends on three vertices (frontband_build.SIDES['wing']['end']): A the upper ridge's end, B the lower
ridge's end, C the groove bottom's end. The band is trimmed on B-C-A (frontband_build.groove_end); here
  - clip_mesh: the wing's mesh with the band's footprint cut out EXACTLY (B-A straight across the end): triangles that
    cross the outline are split on it (shapely, constrained Delaunay of the remaining piece, lifted back onto the
    triangle's plane) - no whole-triangle teeth, no overlap;
  - end_face: the flat end face between the band's own edge (B-C-A on the band mesh) and the wing's surface along A-B
    (on the wing mesh): its two edges ARE its neighbours' edges."""
import sys
import numpy as np
sys.path.append(r'D:\ClaudeData\pylibs')
import shapely
from shapely.geometry import Polygon


def clip_mesh(P, F, N, poly, xmin=0.6):
    """remove the part of the mesh (P, F, N) inside poly ((z, y) points) on the side x > xmin; split crossing triangles"""
    W = Polygon(poly); W = shapely.make_valid(W)
    z0, y0, z1, y1 = W.bounds
    T = P[F]; c = T.mean(1)
    cand = (c[:, 0] > xmin) & (T[:, :, 2].max(1) >= z0) & (T[:, :, 2].min(1) <= z1) & (T[:, :, 1].max(1) >= y0) & (T[:, :, 1].min(1) <= y1)
    ci = np.where(cand)[0]
    tris = shapely.polygons(T[ci][:, :, [2, 1]])
    ok = shapely.is_valid(tris) & (shapely.area(tris) > 1e-12)
    inside = ok & shapely.contains(W, tris)
    cross = ok & ~inside & shapely.intersects(W, tris)
    drop = np.zeros(len(F), bool); drop[ci[inside | cross]] = True
    newP, newN, newF = [], [], []; base = len(P)
    for k in ci[cross]:
        t = T[k]; piece = Polygon(t[:, [2, 1]]).difference(W)
        if piece.is_empty: continue
        tri = shapely.constrained_delaunay_triangles(piece)
        q = np.array([np.array(g.exterior.coords)[:3] for g in tri.geoms]) if not tri.is_empty else np.zeros((0, 3, 2))
        if not len(q): continue
        # lift (z, y) back onto the parent triangle (barycentric in its side view: the wing faces sideways here)
        a, b, cc = t[:, [2, 1]]; M = np.array([a - cc, b - cc]).T
        l = np.linalg.solve(M, (q.reshape(-1, 2) - cc).T).T; l = np.c_[l, 1 - l.sum(1)]
        X = l @ t; Nn = l @ N[F[k]]
        newP.append(X); newN.append(Nn); newF.append(base + np.arange(len(X)).reshape(-1, 3)); base += len(X)
    keepF = F[~drop]
    if newP:
        P = np.r_[P, np.concatenate(newP)]; N = np.r_[N, np.concatenate(newN)]; keepF = np.r_[keepF, np.concatenate(newF)]
    return P, keepF, N, int(inside.sum()), int(cross.sum())


def x_on(P, F, y, z):
    """x of the mesh's outer skin at (y, z): largest hit of a ray along x; nan where nothing covers it"""
    T = P[F]; out = np.full(len(y), np.nan)
    for i, (yy, zz) in enumerate(zip(y, z)):
        m = (T[:, :, 1].min(1) <= yy) & (T[:, :, 1].max(1) >= yy) & (T[:, :, 2].min(1) <= zz) & (T[:, :, 2].max(1) >= zz)
        if not m.any(): continue
        a, b, c = T[m, 0], T[m, 1], T[m, 2]
        d = (b[:, 1] - c[:, 1]) * (a[:, 2] - c[:, 2]) + (c[:, 2] - b[:, 2]) * (a[:, 1] - c[:, 1])
        okd = np.abs(d) > 1e-16; d = np.where(okd, d, 1)
        l1 = ((b[:, 1] - c[:, 1]) * (zz - c[:, 2]) + (c[:, 2] - b[:, 2]) * (yy - c[:, 1])) / d
        l2 = ((c[:, 1] - a[:, 1]) * (zz - c[:, 2]) + (a[:, 2] - c[:, 2]) * (yy - c[:, 1])) / d
        l3 = 1 - l1 - l2; e = -1e-9; h = okd & (l1 >= e) & (l2 >= e) & (l3 >= e)
        if h.any(): out[i] = (l1 * a[:, 0] + l2 * b[:, 0] + l3 * c[:, 0])[h].max()
    return out


def end_face(Pb, Fb, Pw, Fw, ABC, n=48):
    """the end face's mesh (P, F, N): a strip between the band's edge B-C-A and the wing's surface along A-B"""
    A, B, C = (np.asarray(p, float) for p in ABC)                   # (z, y)
    def path(pts, k):
        pts = np.array(pts); s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
        t = np.linspace(0, s[-1], k); return np.c_[np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])]
    e1 = path([B, C, A], n); e2 = path([B, A], n)
    # each point a hair inside its own mesh (the band ends ON B-C-A, the wing ON A-B: a ray exactly on the edge can miss)
    x1 = x_on(Pb, Fb, e1[:, 1], e1[:, 0]); x2 = x_on(Pw, Fw, e2[:, 1], e2[:, 0])
    for x, e, Pm, Fm, sg in ((x1, e1, Pb, Fb, -1), (x2, e2, Pw, Fw, 1)):
        bad = ~np.isfinite(x)
        if bad.any():
            # nudge towards its own side by 0.2 mm along z (band: behind, wing: ahead)
            x[bad] = x_on(Pm, Fm, e[bad, 1], e[bad, 0] + sg * 2e-4)
    if not (np.isfinite(x1).all() and np.isfinite(x2).all()):
        raise RuntimeError(f'end face: {(~np.isfinite(x1)).sum()} band / {(~np.isfinite(x2)).sum()} wing edge points not on their mesh')
    Q1 = np.c_[x1, e1[:, 1], e1[:, 0]]; Q2 = np.c_[x2, e2[:, 1], e2[:, 0]]
    P = np.r_[Q1, Q2]; F = []
    for i in range(n - 1):
        F += [[i, i + 1, n + i + 1], [i, n + i + 1, n + i]]
    F = np.array(F)
    t = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    if (t[:, 0] < 0).sum() > len(t) / 2: F = F[:, [0, 2, 1]]; t = -t       # facing out (+x)
    nrm = t.sum(0); nrm /= np.linalg.norm(nrm)                                  # flat face: one normal
    gap = np.abs(Q1[[0, -1], 0] - Q2[[0, -1], 0]) * 1e3
    return P, F, np.tile(nrm, (len(P), 1)), gap


def feather(P, F, poly, Pb, Fb, skip_seg=None, fw=0.02, maxd=4e-3, xmin=0.6, ymin=-9.0, N=None, Nb=None, zmin=-9.0, seg_target=None):
    """move the mesh's vertices near the side-view outline poly (within fw, outside it) along x so the mesh meets the
    band's edge with no step: delta = band x - mesh x at the nearest outline point, faded out (smoothstep) over fw.
    Where they differ by more than maxd it is a real crease (the arch lip): left alone. skip_seg: (z, y) pair of a
    segment of the outline that is not the band's (the groove end's A-B: the end face sits there)."""
    from scipy.spatial import cKDTree
    W = Polygon(poly); E = np.array(W.exterior.coords)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(E, axis=0), axis=1))]; t = np.arange(0, s[-1], 0.002)
    Q = np.c_[np.interp(t, s, E[:, 0]), np.interp(t, s, E[:, 1])]
    k = np.searchsorted(s, t, side='right') - 1; k = np.clip(k, 0, len(E) - 2)
    tg = E[k + 1] - E[k]; tg /= np.maximum(np.linalg.norm(tg, axis=1), 1e-12)[:, None]; nv = np.c_[-tg[:, 1], tg[:, 0]]
    ins = shapely.contains_xy(W, *(Q + nv * 5e-4).T)
    nv[~ins] *= -1                                           # nv points into the band
    keep = np.ones(len(Q), bool)
    if skip_seg is not None:
        a, b = np.asarray(skip_seg[0]), np.asarray(skip_seg[1]); ab = b - a
        u = np.clip(((Q - a) @ ab) / (ab @ ab), 0, 1); keep = np.linalg.norm(Q - (a + u[:, None] * ab), axis=1) > 1e-3
    Qi = Q + nv * 5e-4; Qo = Q - nv * 5e-4
    xb = x_on(Pb, Fb, Qi[:, 1], Qi[:, 0]); xm = x_on(P, F, Qo[:, 1], Qo[:, 0])
    band_s = keep.copy()                                       # samples where the BAND is the neighbour (normals blend there only)
    if seg_target is not None and skip_seg is not None:
        # along A-B (the end face's outer edge) the wing goes onto Kunos's own skin there (it was 1.4 mm off: a dimple
        # where its feathering faded out); the end face is then built on it
        xb[~keep] = x_on(seg_target[0], seg_target[1], Qo[~keep, 1], Qo[~keep, 0]); keep = keep | True
    d = xb - xm; ok = keep & np.isfinite(d) & (np.abs(d) < maxd) & (Q[:, 1] > ymin) & (Q[:, 0] > zmin)
    if not ok.any(): return P, 0, 0.0, N
    tree = cKDTree(Q[ok]); dist, j = tree.query(P[:, [2, 1]])
    # only vertices outside the outline, on this side of the car, near a used outline point
    # (vertices ON the outline count as outside: copies of one point from split and whole triangles differ by 1e-12)
    out = (P[:, 0] > xmin) & (dist < fw) & ~shapely.contains_xy(W.buffer(-1e-6), P[:, 2], P[:, 1])
    w = 1 - dist / fw; w = w * w * (3 - 2 * w)
    if skip_seg is not None and seg_target is None:
        # faded out towards the end face's edge A-B: the skin ahead of the groove end is the wing's own (it carried the
        # top edge's and the arch edge's deltas into a lumpy patch there)
        u2 = np.clip(((P[:, [2, 1]] - a) @ ab) / (ab @ ab), 0, 1); ds = np.linalg.norm(P[:, [2, 1]] - (a + u2[:, None] * ab), axis=1)
        w2 = np.clip(ds / fw, 0, 1); w = w * w2 * w2 * (3 - 2 * w2)
    P = P.copy(); P[out, 0] += (d[ok][j] * w)[out]
    if Nb is not None and N is not None:
        # shading: the band's normal at the edge, faded into the mesh's own over the same width (one surface in grey)
        nb = Nb[cKDTree(Pb).query(np.c_[xb[ok], Qi[ok][:, 1], Qi[ok][:, 0]])[1]]
        N = N.copy(); sg = np.sign((nb[j] * N).sum(1)); sg[sg == 0] = 1
        wn = w * band_s[ok][j]
        Nn = wn[:, None] * nb[j] * sg[:, None] + (1 - wn[:, None]) * N
        N[out] = (Nn / np.linalg.norm(Nn, axis=1)[:, None])[out]
    return P, int(out.sum()), float(np.abs(d[ok]).max()), N
