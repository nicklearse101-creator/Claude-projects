"""Whole-body method test: curves (sections) -> exact lofted panels, no smoothing.

    python car_loft.py CAR_DIR OUT_DIR [--du 0.08] [--dv 0.004]

AC frame throughout (x = left, y = up, z = forward). Left half built, mirrored.
1. True outer skin (exterior triangles near the voxel outer skin; no cabin, wells, mirrors, wheels).
2. Split into panels by facing direction:
     side  : h = x(z, y)     (u = z along the car, v = y up)
     top   : h = y(z, x)     (u = z, v = x across)
     front : h = z(x, y)     (u = x, v = y)
     rear  : h = -z(x, y)
   Each connected piece is a panel.
3. Sections (method test: cut from the true panel; later traced from pictures): every DU along u, the
   outermost surface point every DV along v. Gaps inside a section (holes) are bridged linearly; the
   trim removes them again.
4. Surface: Catmull-Rom across the sections at each v (passes exactly through every section).
5. Trim to the panel's outline (from its own triangles, rasterised at 2 mm); border vertices snapped
   onto the outline.
6. Score both ways per panel (dense true-skin samples <-> our surface).
"""
import sys, os, json, argparse, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_test as B
import step3b_panels as S3b
from kn5full import KN5
from section import cut

FRAMES = {   # name: (u axis, v axis, h axis, h sign)
    'side': (2, 1, 0, 1), 'top': (2, 0, 1, 1), 'front': (0, 1, 2, 1), 'rear': (0, 1, 2, -1)}


def skin_triangles(ctx, car_dir):
    kn5 = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize, reverse=True)[0]
    k = KN5(kn5, load_textures=False)
    P, I = B.exterior(k, ctx['ground'], ctx['meas']['width'] / 2000)
    TB, TI = S3b.truth_boundary(ctx)
    T = P[I]; cen = T.mean(1); zs = ctx['zs']
    qi = np.clip(np.round((cen[:, 2] - zs[0]) / (zs[1] - zs[0])).astype(int), 0, len(zs) - 1)
    order = np.argsort(TI); TBs, TIs = TB[order], TI[order]; starts = np.searchsorted(TIs, np.arange(len(zs) + 1))
    near = np.zeros(len(cen), bool)
    for st in np.unique(qi):
        sel = np.where(qi == st)[0]; a, b = starts[max(st - 1, 0)], starts[min(st + 2, len(zs))]
        C = TBs[a:b]
        if not len(C): continue
        best = np.full(len(sel), np.inf)
        for s in range(0, len(C), 6000):
            best = np.minimum(best, ((cen[sel, None, :] - C[None, s:s + 6000, :]) ** 2).sum(-1).min(1))
        near[sel] = best < 0.008 ** 2
    T = T[near]
    T = T[T[:, :, 0].mean(1) > -0.002]                    # left half (+x); mirrored later
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    # orient outwards: away from the car's centre line at mid height
    c = np.c_[np.zeros(len(T)), np.full(len(T), ctx['ground'] + 0.55), T.mean(1)[:, 2]]
    n *= np.sign(((T.mean(1) - c) * n).sum(1) + 1e-12)[:, None]
    return T, n


def classify(n):
    cls = np.full(len(n), '', object)
    ax = np.abs(n).argmax(1)
    cls[(ax == 0) & (n[:, 0] > 0)] = 'side'
    cls[(ax == 1) & (n[:, 1] > 0)] = 'top'
    cls[(ax == 2) & (n[:, 2] > 0)] = 'front'
    cls[(ax == 2) & (n[:, 2] < 0)] = 'rear'
    return cls


def raster(T, frame, res, pad=4):
    """panel mask in (u, v) at res, rasterised from its triangles"""
    ua, va, ha, hs = FRAMES[frame]
    U = T[:, :, ua]; Vv = T[:, :, va]
    u0, v0 = U.min() - pad * res, Vv.min() - pad * res
    W = int((U.max() - u0) / res) + pad * 2; H = int((Vv.max() - v0) / res) + pad * 2
    from PIL import Image, ImageDraw
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for tu, tv in zip((U - u0) / res, (Vv - v0) / res):
        d.polygon(list(zip(tu, tv)), fill=255, outline=255)
    M = np.array(im).T > 0
    return M, u0, v0


def sections(T, frame, us, vs):
    """outermost h at each (u_i, v_j) from cuts of the panel's triangles; nan where nothing"""
    ua, va, ha, hs = FRAMES[frame]
    P = T.reshape(-1, 3); I = np.arange(len(P)).reshape(-1, 3)
    Hs = np.full((len(us), len(vs)), np.nan)
    dv = vs[1] - vs[0]
    for i, u in enumerate(us):
        s = cut(P, I, ua, u)
        if not len(s): continue
        seg = s.reshape(-1, 2, 3)
        # sample each segment densely along v so every v-bin it crosses gets a value
        a, b = seg[:, 0], seg[:, 1]
        n = np.maximum(np.ceil(np.abs(b[:, va] - a[:, va]) / (dv / 2)).astype(int), 1)
        for m in np.unique(n):
            sel = n == m
            t = np.linspace(0, 1, m + 1)
            pts = a[sel, None, :] + t[None, :, None] * (b[sel] - a[sel])[:, None, :]
            pts = pts.reshape(-1, 3)
            j = np.round((pts[:, va] - vs[0]) / dv).astype(int); ok = (j >= 0) & (j < len(vs))
            h = hs * pts[ok, ha]; j = j[ok]
            cur = Hs[i]
            for jj, hh in zip(j, h):
                if not (cur[jj] >= hh): cur[jj] = hh
    return Hs


def bridge_gaps(H):
    """within each section, bridge nan gaps linearly (holes); outside the first/last value stays nan"""
    H = H.copy()
    for i in range(len(H)):
        ok = np.isfinite(H[i])
        if ok.sum() < 2: continue
        j = np.where(ok)[0]; lo, hi = j[0], j[-1]
        mid = np.arange(lo, hi + 1)
        H[i, mid] = np.interp(mid, j, H[i, j])
    return H


def catmull_rom_rows(us, H, uq):
    """interpolate sections (rows of H at us) to positions uq, per column; nan-aware (falls back to linear)"""
    out = np.full((len(uq), H.shape[1]), np.nan)
    for q, u in enumerate(uq):
        i = int(np.clip(np.searchsorted(us, u) - 1, 0, len(us) - 2))
        t = (u - us[i]) / (us[i + 1] - us[i])
        p1, p2 = H[i], H[i + 1]
        p0 = H[i - 1] if i > 0 else 2 * p1 - p2
        p3 = H[i + 2] if i + 2 < len(us) else 2 * p2 - p1
        cr = 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
        lin = (1 - t) * p1 + t * p2
        out[q] = np.where(np.isfinite(cr), cr, lin)
    return out


def build_panel(T, frame, du, dv, step, Tall=None, dil=0.0):
    ua, va, ha, hs = FRAMES[frame]
    U = T[:, :, ua]; Vv = T[:, :, va]
    U = np.r_[U.ravel(), U.min() - dil, U.max() + dil]; Vv = np.r_[Vv.ravel(), Vv.min() - dil, Vv.max() + dil]
    us = np.arange(U.min() + du / 4, U.max(), du)
    us = np.r_[U.min() + 1e-4, us[(us > U.min() + 0.01) & (us < U.max() - 0.01)], U.max() - 1e-4]
    vs = np.arange(Vv.min(), Vv.max() + dv, dv)
    Hs = bridge_gaps(sections(Tall if Tall is not None else T, frame, us, vs))
    uq = np.arange(us[0], us[-1] + step / 2, step)
    Hq = catmull_rom_rows(us, Hs, uq)
    # resample v to the mesh step
    vq = np.arange(vs[0], vs[-1] + step / 2, step)
    G = np.full((len(uq), len(vq)), np.nan)
    for q in range(len(uq)):
        ok = np.isfinite(Hq[q])
        if ok.sum() >= 2: G[q] = np.where((vq >= vs[ok][0]) & (vq <= vs[ok][-1]), np.interp(vq, vs[ok], Hq[q, ok]), np.nan)
    # trim to the panel outline
    M, u0, v0 = raster(T, frame, 0.002, pad=int(dil / 0.002) + 4)
    if dil > 0:
        n = int(dil / 0.002)
        for _ in range(n):
            b = M.copy(); b[1:] |= M[:-1]; b[:-1] |= M[1:]; b[:, 1:] |= M[:, :-1]; b[:, :-1] |= M[:, 1:]; M = b
    iu = np.clip(((uq - u0) / 0.002).round().astype(int), 0, M.shape[0] - 1)
    iv = np.clip(((vq - v0) / 0.002).round().astype(int), 0, M.shape[1] - 1)
    inside = M[np.ix_(iu, iv)] & np.isfinite(G)
    return dict(uq=uq, vq=vq, G=G, inside=inside, M=M, u0=u0, v0=v0, us=us)


def panel_mesh(p, frame):
    ua, va, ha, hs = FRAMES[frame]
    uq, vq, G, inside = p['uq'], p['vq'], p['G'], p['inside']
    idx = -np.ones(G.shape, int); keepv = np.zeros(G.shape, bool)
    q = inside[:-1, :-1] & inside[1:, :-1] & inside[1:, 1:] & inside[:-1, 1:]
    keepv[:-1, :-1] |= q; keepv[1:, :-1] |= q; keepv[1:, 1:] |= q; keepv[:-1, 1:] |= q
    idx[keepv] = np.arange(keepv.sum())
    uu, vv = np.meshgrid(uq, vq, indexing='ij')
    P = np.zeros((keepv.sum(), 3)); P[:, ua] = uu[keepv]; P[:, va] = vv[keepv]; P[:, ha] = hs * G[keepv]
    F = np.c_[idx[:-1, :-1][q], idx[1:, :-1][q], idx[1:, 1:][q], idx[:-1, 1:][q]]
    # snap border vertices onto the outline (nearest outline pixel), keep their h via the local slope
    M, u0, v0 = p['M'], p['u0'], p['v0']
    edge = M & ~(np.roll(M, 1, 0) & np.roll(M, -1, 0) & np.roll(M, 1, 1) & np.roll(M, -1, 1))
    eu, ev = np.nonzero(edge); EU = u0 + eu * 0.002; EV = v0 + ev * 0.002
    deg = np.bincount(np.r_[F.ravel()], minlength=len(P))
    border = deg < 4
    if len(EU) and border.any():
        bi = np.where(border)[0]
        for s in range(0, len(bi), 2000):
            b = bi[s:s + 2000]
            d = (P[b, ua][:, None] - EU[None, :]) ** 2 + (P[b, va][:, None] - EV[None, :]) ** 2
            j = d.argmin(1); ok = d[np.arange(len(b)), j] < (0.02 ** 2)
            P[b[ok], ua] = EU[j[ok]]; P[b[ok], va] = EV[j[ok]]
    return P, F


def sample_tris(T, step=0.004):
    L = np.maximum(np.linalg.norm(T[:, 1] - T[:, 0], axis=1), np.linalg.norm(T[:, 2] - T[:, 0], axis=1))
    out = []
    nseg = np.clip(np.ceil(L / step).astype(int), 1, 30)
    for n in np.unique(nseg):
        sel = nseg == n
        for i in range(n + 1):
            for j in range(n + 1 - i):
                out.append(T[sel, 0] + (i / n) * (T[sel, 1] - T[sel, 0]) + (j / n) * (T[sel, 2] - T[sel, 0]))
    return np.concatenate(out)


def nearest(A, Bp, axis, slab=0.02, chunk=400):
    o = np.argsort(Bp[:, axis]); Bs = Bp[o]; by = Bs[:, axis]
    oa = np.argsort(A[:, axis]); As = A[oa]; out = np.empty(len(A))
    for s in range(0, len(As), chunk):
        q = As[s:s + chunk]
        lo, hi = np.searchsorted(by, q[:, axis].min() - slab), np.searchsorted(by, q[:, axis].max() + slab)
        C = Bs[lo:hi]
        if not len(C): out[s:s + chunk] = slab; continue
        d = np.full(len(q), np.inf)
        for c in range(0, len(C), 4000):
            d = np.minimum(d, ((q[:, None, :] - C[None, c:c + 4000, :]) ** 2).sum(-1).min(1))
        out[s:s + chunk] = np.minimum(np.sqrt(d), slab)
    res = np.empty(len(A)); res[oa] = out; return res


def fine_points(P, F, n=4):
    Q = P[F]
    out = []
    for a in np.linspace(0, 1, n + 1):
        for b in np.linspace(0, 1, n + 1):
            out.append((1 - a) * (1 - b) * Q[:, 0] + a * (1 - b) * Q[:, 1] + a * b * Q[:, 2] + (1 - a) * b * Q[:, 3])
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('car'); ap.add_argument('out')
    ap.add_argument('--du', type=float, default=0.08); ap.add_argument('--dv', type=float, default=0.003)
    ap.add_argument('--step', type=float, default=0.010)
    a = ap.parse_args()
    ctx = B.setup(a.car, a.out)
    T, n = skin_triangles(ctx, a.car)
    cls = classify(n)
    global ALLTP
    ALLTP = sample_tris(T)
    # connected pieces per class (shared vertices)
    key = lambda X: tuple(np.round(X / 1e-4).astype(np.int64))
    panels, report, allP, allF = [], {}, [], []
    for frame in FRAMES:
        sel = np.where(cls == frame)[0]
        if not len(sel): continue
        # union-find on shared vertex positions
        parent = list(range(len(sel)))
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        owner = {}
        for ti, t in enumerate(sel):
            for v in T[t]:
                kk = key(v)
                if kk in owner:
                    ra, rb = find(owner[kk]), find(ti)
                    if ra != rb: parent[ra] = rb
                else: owner[kk] = ti
        comp = np.array([find(i) for i in range(len(sel))])
        for ci in np.unique(comp):
            tsel = sel[comp == ci]
            Tp = T[tsel]
            area = 0.5 * np.linalg.norm(np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0]), axis=1).sum()
            if area < 0.001: continue
            ua_, va_ = FRAMES[frame][0], FRAMES[frame][1]
            box = (T[:, :, ua_].max(1) > Tp[:, :, ua_].min() - 0.05) & (T[:, :, ua_].min(1) < Tp[:, :, ua_].max() + 0.05) &                   (T[:, :, va_].max(1) > Tp[:, :, va_].min() - 0.05) & (T[:, :, va_].min(1) < Tp[:, :, va_].max() + 0.05)
            # same facing, or within 30 deg past the 45 deg split (keeps the overlap on the true surface)
            hax, hs_ = FRAMES[frame][2], FRAMES[frame][3]
            facing = n[:, hax] * hs_ > 0.45
            p = build_panel(Tp, frame, a.du, a.dv, a.step, Tall=T[box & facing], dil=float(os.environ.get('DIL', 0.02)))
            P, F = panel_mesh(p, frame)
            if not len(F): continue
            TP = sample_tris(Tp); FP = fine_points(P, F)
            TPall = ALLTP[(ALLTP[:, FRAMES[frame][0]] > FP[:, FRAMES[frame][0]].min() - 0.03) & (ALLTP[:, FRAMES[frame][0]] < FP[:, FRAMES[frame][0]].max() + 0.03)]
            ax = FRAMES[frame][0]
            d1 = nearest(TP, FP, ax) * 1000; d2 = nearest(FP, TPall, ax) * 1000
            name = f'{frame}_{len([x for x in panels if x[0] == frame])}'
            panels.append((frame, name))
            report[name] = dict(area_m2=round(float(area), 3), quads=int(len(F)), sections=int(len(p['us'])),
                                truth_to_build_med=round(float(np.median(d1)), 2), truth_within3=round(float(np.mean(d1 <= 3) * 100), 1),
                                build_to_truth_med=round(float(np.median(d2)), 2), build_within3=round(float(np.mean(d2 <= 3) * 100), 1),
                                _d1=d1, _d2=d2)
            allF.append(F + sum(len(x) for x in allP)); allP.append(P)
    P = np.concatenate(allP); F = np.concatenate(allF)
    D1 = np.concatenate([r.pop('_d1') for r in report.values()]); D2 = np.concatenate([r.pop('_d2') for r in report.values()])
    total = dict(panels=len(report), quads=int(len(F)),
                 truth_to_build=dict(median=round(float(np.median(D1)), 2), p90=round(float(np.percentile(D1, 90)), 2), within_3mm=round(float(np.mean(D1 <= 3) * 100), 1)),
                 build_to_truth=dict(median=round(float(np.median(D2)), 2), p90=round(float(np.percentile(D2, 90)), 2), within_3mm=round(float(np.mean(D2 <= 3) * 100), 1)))
    np.savez(os.path.join(a.out, f"{ctx['car']}_carloft.npz"), P=P, F=F)
    json.dump(dict(total=total, panels=report), open(os.path.join(a.out, f"{ctx['car']}_carloft.json"), 'w'), indent=1)
    print(json.dumps(total))
    big = sorted(report.items(), key=lambda kv: -kv[1]['area_m2'])[:14]
    for k_, v in big: print(f"  {k_:9s} {v['area_m2']:6.3f} m2  sections {v['sections']:3d}  truth->build {v['truth_to_build_med']:5.2f} mm ({v['truth_within3']:5.1f}% <=3)  build->truth {v['build_to_truth_med']:5.2f} mm ({v['build_within3']:5.1f}%)")


if __name__ == '__main__':
    main()
