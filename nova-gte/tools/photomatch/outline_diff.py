"""Compare model vs photo outlines in one camera: top outline per column and end outlines per row.
Prints, for bins along the car, the model 3D point behind the outline and the needed dz (top) or dy (ends)."""
import sys, json, numpy as np, cv2
import preview as pv
import body_geom as g


def idrender(c):
    """Render triangle ids -> per-pixel 3D centroid (shell only) and mask."""
    W, H = pv.O[c]['W'], pv.O[c]['H']
    V, F, M, n = pv.shell_mesh()
    VR = V.copy(); VR[:, 0] *= -1
    T, M = pv.tri_list(V, F, M)
    VA = np.vstack([V, VR]); TA = np.vstack([T, T[:, ::-1] + len(V)])
    cen = VA[TA].mean(1)
    keep = np.ones(len(TA), bool)
    for k, (cy, cz, r) in g.arches(photo_frame=True).items():
        keep &= ~(((cen[:, 1] - cy) ** 2 + (cen[:, 2] - cz) ** 2 < r * r) & (np.abs(cen[:, 0]) > 0.5))
    TMA = np.concatenate([M, M])
    keep &= TMA != 'glass_tint'
    TA, cen = TA[keep], cen[keep]
    uv, z, _, _ = pv.project(c, VA)
    tz = z[TA].mean(1); order = np.argsort(-tz)
    idimg = np.zeros((H, W, 3), np.uint8)
    for t in order:
        if (z[TA[t]] < 0.2).any():
            continue
        i = int(t) + 1
        cv2.fillConvexPoly(idimg, np.round(uv[TA[t]] * 4).astype(np.int32), (i & 255, (i >> 8) & 255, i >> 16), shift=2)
    ids = idimg[..., 0].astype(np.int64) | (idimg[..., 1].astype(np.int64) << 8) | (idimg[..., 2].astype(np.int64) << 16)
    P = np.full((H, W, 3), np.nan)
    m = ids > 0
    P[m] = cen[ids[m] - 1]
    return P, m, tz, z


if __name__ == '__main__':
    c = sys.argv[1]
    seg = cv2.imread(f'seg_{c}.png', 0) > 0
    P, m, _, _ = idrender(c)
    cp = np.array(pv.B['cams'][c]); f = cp[6]
    R, _ = cv2.Rodrigues(cp[:3]); t = cp[3:6]
    H, W = m.shape
    rows = []
    for u in range(0, W, 2):
        mm = np.where(m[:, u])[0]; ss = np.where(seg[:, u])[0]
        if len(mm) == 0 or len(ss) == 0:
            continue
        vm, vp = mm[0], ss[0]
        X = P[vm + 1, u] if not np.isnan(P[vm + 1, u]).any() else P[vm, u]
        d = (R @ X + t)[2]
        rows.append((X[1], X[0], X[2], vp - vm, -(vp - vm) * d / f))
    rows = np.array(rows)
    print('TOP outline: y-bin  model(x,z)  dv_px  dz_needed')
    for y0 in np.arange(-1.80, 1.80, 0.05):
        s = rows[(rows[:, 0] >= y0) & (rows[:, 0] < y0 + 0.05)]
        if len(s):
            print(f"{y0+0.025:+.3f}  x{np.median(s[:,1]):+.2f} z{np.median(s[:,2]):.3f}  dv {np.median(s[:,3]):+5.1f}  dz {np.median(s[:,4]):+.4f}  n{len(s)}")
    # ends per row
    print('ENDS: v  z_model  front(du, dy)   rear(du, dy)')
    for v in range(0, H, 6):
        mm = np.where(m[v])[0]; ss = np.where(seg[v])[0]
        if len(mm) == 0 or len(ss) == 0:
            continue
        out = []
        for side in (1, 0):   # front = max u in cS (car faces right), rear = min u
            um = mm[-1] if side else mm[0]; up = ss[-1] if side else ss[0]
            X = P[v, um - 1 if side else um + 1]
            if np.isnan(X).any():
                out.append(None); continue
            d = (R @ X + t)[2]
            out.append((X[1], X[2], up - um, (up - um) * d / f))
        if out[0] and out[1]:
            print(f"{v:4d} z{out[0][1]:.3f} F y{out[0][0]:+.3f} du{out[0][2]:+4d} dy{-out[0][3]:+.4f} | R y{out[1][0]:+.3f} z{out[1][1]:.3f} du{out[1][2]:+4d} dy{-out[1][3]:+.4f}")
