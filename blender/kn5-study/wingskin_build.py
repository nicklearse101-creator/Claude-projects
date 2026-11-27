"""The front wing's side SKIN, one surface (27 Nov).

Kunos's wing side (GEO_body piece 0) between the top shoulder roll, the door shut, the arch flare, the wing band (groove
behind the arch) and the small ledge ahead of the arch is a sparse net of big triangles (about one vertex per 100 mm, no
rows), shaded smooth by its normals. The wing's panel fit split it into sub-panels on a line 80 mm above the arch top
(above / front / rear) and fitted each on its own: a crack along y 0.70 and steps where they met the lip.

Now ONE height field x(z, y) (side view), a thin-plate spline THROUGH Kunos's skin vertices plus dense edge data from
the finished neighbours (the flare's outer round, the band's top, the shoulder's first rows, the ledge's top, the door
edge): the fairest surface through the data, meeting the neighbours in position and slope. Kunos's normals are not used:
on this low-poly skin they disagree with its own vertex positions (a fit to both was worse on held-out vertices).
Sampled on a 4 mm lattice -> one grid face, trimmed in FreeCAD on the skin's outline (side view).
    python wingskin_build.py CAR_DIR REGRESS_DIR OUT_DIR"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.append(r'D:\ClaudeData\pylibs')
import panel_fit as PF
import shapely
from shapely.geometry import Polygon, box

Z_FRONT = float(os.environ.get('WS_ZFRONT', 1.70))      # the front corner's fan starts here (Kunos's column at z 1.70)
Y_LEDGE = float(os.environ.get('WS_YLEDGE', 0.607))     # top of the ledge ahead of the arch
TILT_MAX = 38.0                                          # skin vertices: normal within this of +x (the roll is steeper)


def skin_vertices(car):
    """Kunos piece-0 vertices of the wing side (welded, normals averaged) and their normals' tilt from +x"""
    V, F, N = PF.load_mesh(car, 'GEO_body', raw=True)
    pcs = PF.crease_pieces(V, F, N); p = pcs[0]; cc = V[p].mean(1)
    P0 = p[(cc[:, 0] > 0.5) & (cc[:, 2] > 0.6) & (cc[:, 1] > 0.15)]
    kk = np.round(V / 1e-6).astype(np.int64); _, wid = np.unique(kk, axis=0, return_inverse=True); wid = wid.ravel()
    u = np.unique(P0); ns = np.zeros((wid.max() + 1, 3)); np.add.at(ns, wid[u], N[u])
    uw, first = np.unique(wid[u], return_index=True); X = V[u[first]]; NX = ns[uw]; NX /= np.linalg.norm(NX, axis=1)[:, None]
    pos = {int(w): i for i, w in enumerate(uw)}; nb = {}
    for t in wid[P0]:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            i, j = pos[int(t[a])], pos[int(t[b])]; nb.setdefault(i, set()).add(j); nb.setdefault(j, set()).add(i)
    skin_vertices.nb = nb
    return X, NX, np.degrees(np.arccos(np.clip(NX[:, 0], -1, 1)))


def shoulder_rows(X, NX, nb):
    """Kunos's shoulder rows (the roll along the wing's top): chains of vertices linked to their mesh neighbour along
    the car with the most similar normal (< 8 deg), mutual; long chains only"""
    cand = [i for i in nb if X[i, 1] > 0.6 and X[i, 2] > 0.6]
    def pick(i, sg):
        best = None
        for j in nb[i]:
            if (X[i, 2] - X[j, 2]) * sg < 0.01: continue
            dn = np.degrees(np.arccos(np.clip(NX[i] @ NX[j], -1, 1)))
            if dn < 8 and (best is None or dn < best[0]): best = (dn, j)
        return None if best is None else best[1]
    ah = {i: pick(i, 1) for i in cand}; bh = {i: pick(i, -1) for i in cand}
    nxt = {i: j for i, j in ah.items() if j is not None and bh.get(j) == i}; hp = set(nxt.values()); rows = []
    for i in cand:
        if i in hp: continue
        ch = [i]
        while ch[-1] in nxt: ch.append(nxt[ch[-1]])
        if len(ch) >= 6: rows.append(np.array(ch))
    return rows


def region(X, NX, tilt, R):
    """the skin's side-view polygon and its boundary pieces"""
    fl = np.load(os.path.join(R, 'flare/flare_grid.npz')); G = fl['grid']
    foot = Polygon(fl['foot']).buffer(0)
    endw = Polygon(np.load(os.path.join(R, 'wingband/band_grid.npz'))['end_wing']).buffer(0)
    E0 = G[:, 0][:, [2, 1]]                                    # the arch edge: the opening below it
    hole = Polygon(np.r_[E0, [[E0[-1, 0], 0.0], [E0[0, 0], 0.0]]]).buffer(0)
    # door edge: the skin's last vertex before the shut return (normal still facing out, n_z ~ 0), per height
    de = (X[:, 2] < 0.76) & (X[:, 1] > 0.58) & (np.abs(NX[:, 2]) < 0.15) & (tilt < 40)
    D = X[de]; D = D[np.argsort(D[:, 1])]
    keep = [0]
    for i in range(1, len(D)):
        if D[i, 1] - D[keep[-1], 1] > 0.003: keep.append(i)
        elif D[i, 2] < D[keep[-1], 2]: keep[-1] = i
    D = D[keep]
    # top: the shoulder build's first row (shoulder_build.py: Kunos's ~30 deg row, the roll above it is the shoulder's);
    # behind the shoulder's start (by the door) Kunos's own ~30 deg row vertices
    sg = np.load(os.path.join(R, 'shoulder/shoulder_grid.npz'))['grid']
    top = sg[:, 0]
    rr = (tilt > 25) & (tilt < 38) & (X[:, 2] < top[0, 2] - 0.005) & (X[:, 1] > top[0, 1] - 0.05)
    if rr.any(): top = np.r_[X[rr], top]
    top = top[np.argsort(top[:, 2])]
    ztop = lambda z: np.interp(z, np.r_[D[-1, 2], top[:, 2]], np.r_[D[-1, 1], top[:, 1]])
    zs = np.linspace(D[-1, 2], Z_FRONT, 200)
    outer = np.r_[D[:, [2, 1]], np.c_[zs, ztop(zs)], [[Z_FRONT, 0.55], [D[0, 2], 0.55]]]
    P = Polygon(outer).buffer(0)
    P = P.difference(foot).difference(endw).difference(hole).difference(box(1.38, 0.0, 3.0, Y_LEDGE))
    P = max(getattr(P, 'geoms', [P]), key=lambda q: q.area)
    return P, dict(door=D, top=top, foot=foot, endw=endw, G=G, SG=sg)


def edge_data(R, info, X, tilt):
    """dense data from the neighbours, so the skin meets them in position and slope"""
    G = info['G']
    fl = G[::2, -2:].reshape(-1, 3)                            # the flare's outer edge (its last 2 columns: past the round)
    bg = np.load(os.path.join(R, 'wingband/band_grid.npz'))
    Bp = bg['grid'].reshape(-1, 3)        # its flat top facet only (above the groove's upper ridge, y 0.637 +- 1.5 mm)
    Bp = Bp[(Bp[:, 1] > 0.6445) & shapely.contains_xy(Polygon(bg['end_band']).buffer(0.002), Bp[:, 2], Bp[:, 1])]
    # the shoulder roll's first rows (normal tilt 38-50 deg) set the skin's slope at its top edge
    sh = info['SG'][::2, :3].reshape(-1, 3)                  # the shoulder's first 3 columns (position + slope)
    # the ledge's top ahead of the arch
    lg = X[(X[:, 2] > 1.40) & (X[:, 2] < Z_FRONT + 0.02) & (X[:, 1] > Y_LEDGE - 0.004) & (X[:, 1] < Y_LEDGE + 0.002) & (tilt < 30)]
    return np.r_[fl, Bp, sh, lg], dict(flare=len(fl), band=len(Bp), shoulder=len(sh), ledge=len(lg))


def normal_field(car, P, step=0.006):
    """Kunos's interpolated normals (what its shading shows) on a side-view lattice inside P: (z, y, n)"""
    V, F, N = PF.load_mesh(car, 'GEO_body', raw=True)
    F0 = PF.crease_pieces(V, F, N)[0]; c = V[F0].mean(1); F0 = F0[(c[:, 0] > 0.6) & shapely.contains_xy(P.buffer(0.03), c[:, 2], c[:, 1])]
    Nn = N / np.linalg.norm(N, axis=1)[:, None]
    z0, y0, z1, y1 = P.bounds; Zq, Yq = np.meshgrid(np.arange(z0, z1, step), np.arange(y0, y1, step), indexing='ij')
    m = shapely.contains_xy(P, Zq, Yq); Zs, Ys = Zq[m], Yq[m]
    NI = np.full((len(Zs), 3), np.nan); XI = np.full(len(Zs), -9.0)
    for t in F0:
        T = V[t]; zt, yt = T[:, 2], T[:, 1]
        mm = (Zs >= zt.min()) & (Zs <= zt.max()) & (Ys >= yt.min()) & (Ys <= yt.max())
        if not mm.any(): continue
        den = (yt[1] - yt[2]) * (zt[0] - zt[2]) + (zt[2] - zt[1]) * (yt[0] - yt[2])
        if abs(den) < 1e-14: continue
        a = ((yt[1] - yt[2]) * (Zs[mm] - zt[2]) + (zt[2] - zt[1]) * (Ys[mm] - yt[2])) / den
        b = ((yt[2] - yt[0]) * (Zs[mm] - zt[2]) + (zt[0] - zt[2]) * (Ys[mm] - yt[2])) / den; cc = 1 - a - b
        ok = (a >= -1e-9) & (b >= -1e-9) & (cc >= -1e-9); xx = a * T[0, 0] + b * T[1, 0] + cc * T[2, 0]
        ii = np.nonzero(mm)[0]; sel = ok & (xx > XI[ii])
        NI[ii[sel]] = a[sel, None] * Nn[t[0]] + b[sel, None] * Nn[t[1]] + cc[sel, None] * Nn[t[2]]; XI[ii[sel]] = xx[sel]
    ok = np.isfinite(NI[:, 0]); NI = NI[ok] / np.linalg.norm(NI[ok], axis=1)[:, None]
    return Zs[ok], Ys[ok], NI


def fit_height(car, P, Pd, isk):
    """x(z, y): cubic B-spline (controls ~40 x 30 mm) fitted to the vertices / edge data (edges weighted 3x) and, more
    weakly, to the slopes of Kunos's interpolated normals over the whole region: the vertices fix it, the normals keep it
    fair (through the vertices alone it was lumpy - Kunos's sparse vertex heights wobble; its normal field does not)"""
    z0, y0, z1, y1 = P.bounds; pad = 0.03; Z0, Z1, Y0, Y1 = z0 - pad, z1 + pad, y0 - pad, y1 + pad
    nz = int(os.environ.get('WS_NZ', 0)) or max(8, int(round((Z1 - Z0) / 0.038))); ny = int(os.environ.get('WS_NY', 0)) or max(5, int(round((Y1 - Y0) / 0.032)))
    def design(z, y):
        kz = PF.knots(nz, Z0, Z1); ky = PF.knots(ny, Y0, Y1); h = 1e-5
        Bz = PF.basis(z, kz, nz); By = PF.basis(y, ky, ny)
        dBz = (PF.basis(z + h, kz, nz) - PF.basis(z - h, kz, nz)) / (2 * h); dBy = (PF.basis(y + h, ky, ny) - PF.basis(y - h, ky, ny)) / (2 * h)
        T = lambda A, B: (A[:, :, None] * B[:, None, :]).reshape(len(z), -1)
        return T(Bz, By), T(dBz, By), T(Bz, dBy)
    Zs, Ys, NI = normal_field(car, P)
    gz = -NI[:, 2] / NI[:, 0]; gy = -NI[:, 1] / NI[:, 0]
    Bk = design(Pd[:, 2], Pd[:, 1])[0]; wpt = np.where(isk, 1.0, float(os.environ.get('WS_WE', 25.0)))
    _, Bz, By = design(Zs, Ys)
    Dz = PF.diff2(nz); Dy = PF.diff2(ny); Rg = np.r_[np.kron(Dz, np.eye(ny)), np.kron(np.eye(nz), Dy)]
    wg = float(os.environ.get('WS_WG', 2.0)); lam = float(os.environ.get('WS_LAM', 1e-3))
    Lg = wg * 0.03 * np.sqrt(len(Pd) / len(Zs))
    A = np.r_[Bk * wpt[:, None], Lg * Bz, Lg * By, lam * Rg]; b = np.r_[Pd[:, 0] * wpt, Lg * gz, Lg * gy, np.zeros(len(Rg))]
    cf = np.linalg.lstsq(A, b, rcond=None)[0]
    r = np.abs(Bk @ cf - Pd[:, 0]) * 1e3; gres = np.degrees(np.arctan(np.hypot(Bz @ cf - gz, By @ cf - gy)))
    print(f'height field {nz}x{ny} controls: Kunos vertices off median {np.median(r[isk]):.2f} p95 {np.percentile(r[isk], 95):.2f} max {r[isk].max():.2f} mm; '
          f'edge data median {np.median(r[~isk]):.2f} p95 {np.percentile(r[~isk], 95):.2f} max {r[~isk].max():.2f} mm; normals off median {np.median(gres):.1f} p95 {np.percentile(gres, 95):.1f} deg', flush=True)
    return lambda z, y: design(np.asarray(z, float), np.asarray(y, float))[0] @ cf


def build(car, R, out):
    X, NX, tilt = skin_vertices(car)
    P, info = region(X, NX, tilt, R)
    ins = shapely.contains_xy(P.buffer(0.0015), X[:, 2], X[:, 1]) & (tilt < 62) & (np.abs(NX[:, 2]) < 0.3)
    Xs = X[ins]
    De, cnt = edge_data(R, info, X, tilt)
    print(f'skin: region {P.area * 1e4:.0f} cm2, {ins.sum()} Kunos vertices; edge data ' + ', '.join(f'{k} {v}' for k, v in cnt.items()), flush=True)
    Pd = np.r_[Xs, De]; isk = np.r_[np.ones(len(Xs), bool), np.zeros(len(De), bool)]
    near = shapely.contains_xy(P.buffer(0.02), Pd[:, 2], Pd[:, 1]); Pd, isk = Pd[near], isk[near]
    f = fit_height(car, P, Pd, isk)
    z0, y0, z1, y1 = P.bounds; st = float(os.environ.get('WS_STEP', 0.008)); pad = 0.012
    zz = np.arange(z0 - pad, z1 + pad + 1e-9, st); yy = np.arange(y0 - pad, y1 + pad + 1e-9, st)
    Zg, Yg = np.meshgrid(zz, yy, indexing='ij')
    Xg = f(Zg.ravel(), Yg.ravel()).reshape(Zg.shape)
    G = np.stack([Xg, Yg, Zg], -1)                                         # stations along z, columns up y
    # outline (side view) -> 3D on the surface, 3 mm steps
    E = np.array(P.exterior.coords)[:-1]
    out_ = []
    for a, b in zip(E, np.roll(E, -1, axis=0)):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / 0.003))); out_ += [a + (b - a) * t for t in np.arange(k) / k]
    E = np.array(out_); E3 = np.c_[f(E[:, 0], E[:, 1]), E[:, 1], E[:, 0]]
    holes = [np.array(h.coords)[:-1] for h in P.interiors]
    res = [dict(name='wskin:L', maxlen=float(os.environ.get('WS_MAXLEN', 6)), structured=False, grid=(G * 1000).tolist(),
                trim=(E3 * 1000).tolist(), trim_any=True, tess=float(os.environ.get('WS_TESS', 0.03)),
                holes=[(np.c_[f(h[:, 0], h[:, 1]), h[:, 1], h[:, 0]] * 1000).tolist() for h in holes], frame=[[0, 0, 0], [0, 0, 1], [0, 1, 0], [1.0, 0, 0]])]
    os.makedirs(out, exist_ok=True)
    if os.environ.get('WS_ZEBRA'):                     # isophote stripes (debug): out/zebra.png
        from PIL import Image
        st2 = 0.002; za = np.arange(z0, z1, st2); ya = np.arange(y0, y1, st2); Za, Ya = np.meshgrid(za, ya, indexing='ij')
        Xa = f(Za.ravel(), Ya.ravel()).reshape(Za.shape); gz_ = np.gradient(Xa, st2, axis=0); gy_ = np.gradient(Xa, st2, axis=1)
        nn = np.stack([np.ones_like(Xa), -gy_, -gz_], -1); nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
        Lz = np.array([0.6, 0.6, 0.5]); Lz /= np.linalg.norm(Lz)
        img = np.where((np.floor((nn @ Lz) * 40) % 2) == 0, 230, 60).astype(np.uint8); img[~shapely.contains_xy(P, Za, Ya)] = 255
        Image.fromarray(img.T[::-1, ::-1]).save(os.path.join(out, 'zebra.png'))
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'skin_grid.npz'), grid=G, outline=E3, poly=np.array(P.exterior.coords), data=Pd, kunos=Xs, isk=isk)
    print(f'grid {G.shape[0]} x {G.shape[1]} (z {zz[0]:.3f}..{zz[-1]:.3f}, y {yy[0]:.3f}..{yy[-1]:.3f}); outline {len(E3)} points, {len(holes)} holes', flush=True)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3])
