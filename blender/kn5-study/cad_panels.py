"""Panel-by-panel CAD build, step 1 (plain Python): feature-aligned section grids for every panel.

    python cad_panels.py CAR_DIR OUT_DIR [--du 0.05]

Method test: curves come from the true model. AC frame, left half (mirrored later).
1. Outer-skin triangles, grouped by their source mesh (the car's real panels), then split by facing
   (side / top / front / rear) and into connected pieces -> panels, each a height field h(u, v).
2. Sections every DU across the panel: the panel's outermost surface along v, gaps bridged.
3. Creases: sharp turns on each section, chained across sections; chains covering most of the panel
   become split lines. Every section is split at them -> strips; each strip segment is resampled to a
   fixed count, so grid rows follow the features.
4. Saves OUT/<car>_panels.npz: strip grids (sections x points x 3, AC metres) for FreeCAD.
"""
import sys, os, json, glob, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_test as B
import step3b_panels as S3b
from kn5full import KN5
from section import cut

FRAMES = {'side': (2, 1, 0, 1), 'top': (2, 0, 1, 1), 'front': (0, 1, 2, 1), 'rear': (0, 1, 2, -1)}
BINV = 0.003


def skin_by_mesh(ctx, car_dir):
    """outer-skin triangles with the index of the mesh they came from (left half)"""
    kn5 = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize, reverse=True)[0]
    k = KN5(kn5, load_textures=False)
    g = ctx['ground']; half_w = ctx['meas']['width'] / 2000
    Ts, ids, names = [], [], []
    for mi, m in enumerate(k.meshes):
        path = k.path_of(m.node); nm = (m.name + ' ' + path).lower()
        if any(s in m.name.lower() for s in B.MIR) or any(s in nm for s in B.SKIP): continue
        if any(t in path for t in ('WHEEL_', 'SUSP_', 'DISC_', 'COCKPIT_', 'STEER_')): continue
        if m.mat and m.mat.shader == 'ksBrokenGlass': continue
        if 'underside' in m.name.lower() or 'glassesint' in m.name.lower() or (m.mat and m.mat.name.lower().startswith('int')): continue
        T = m.pos[m.idx]
        T = T[~((np.abs(T[..., 0]) > half_w + 0.012) & (T[..., 1] - g > 0.6)).all(1)]
        if len(T): Ts.append(T); ids.append(np.full(len(T), len(names))); names.append(m.name)
    T = np.concatenate(Ts); mid = np.concatenate(ids)
    TB, TI = S3b.truth_boundary(ctx)
    cen = T.mean(1); zs = ctx['zs']
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
    keep = near & (T[:, :, 0].mean(1) > -0.002)
    T, mid = T[keep], mid[keep]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    c = np.c_[np.zeros(len(T)), np.full(len(T), g + 0.55), T.mean(1)[:, 2]]
    n *= np.sign(((T.mean(1) - c) * n).sum(1) + 1e-12)[:, None]
    return T, n, mid, names


def classify(n):
    cls = np.full(len(n), '', object); ax = np.abs(n).argmax(1)
    cls[(ax == 0) & (n[:, 0] > 0)] = 'side'; cls[(ax == 1) & (n[:, 1] > 0)] = 'top'
    cls[(ax == 2) & (n[:, 2] > 0)] = 'front'; cls[(ax == 2) & (n[:, 2] < 0)] = 'rear'
    return cls


def components(T, sel):
    key = lambda X: tuple(np.round(X / 1e-4).astype(np.int64))
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
    return [sel[comp == c] for c in np.unique(comp)]


def section_profile(Tp, frame, u):
    ua, va, ha, hs = FRAMES[frame]
    P = Tp.reshape(-1, 3); I = np.arange(len(P)).reshape(-1, 3)
    s = cut(P, I, ua, u)
    if not len(s): return None
    seg = s.reshape(-1, 2, 3); a, b = seg[:, 0], seg[:, 1]
    nseg = np.maximum(np.ceil(np.abs(b[:, va] - a[:, va]) / (BINV / 2)).astype(int), 1)
    pts = []
    for m in np.unique(nseg):
        sel = nseg == m; t = np.linspace(0, 1, m + 1)
        pts.append((a[sel, None, :] + t[None, :, None] * (b[sel] - a[sel])[:, None, :]).reshape(-1, 3))
    Q = np.concatenate(pts)
    vb = np.round(Q[:, va] / BINV).astype(int); h = hs * Q[:, ha]
    order = np.lexsort((-h, vb)); vb, h = vb[order], h[order]
    first = np.r_[True, vb[1:] != vb[:-1]]
    vv, hh = vb[first] * BINV, h[first]
    if len(vv) < 12: return None
    full = np.arange(vv[0], vv[-1] + BINV / 2, BINV)
    return np.c_[full, np.interp(full, vv, hh)]          # (v, h), gaps bridged


def turning(prof, w=4):
    a = np.zeros(len(prof))
    for i in range(w, len(prof) - w):
        p, q = prof[i] - prof[i - w], prof[i + w] - prof[i]
        a[i] = np.degrees(np.arccos(np.clip(p @ q / (np.linalg.norm(p) * np.linalg.norm(q) + 1e-12), -1, 1)))
    return a


def peaks(a, thr=12, sep=7):
    idx = []
    for i in np.argsort(-a):
        if a[i] < thr: break
        if all(abs(i - j) > sep for j in idx): idx.append(i)
    return sorted(idx)


def build_panel(Tp, frame, du):
    ua, va, ha, hs = FRAMES[frame]
    U = Tp[:, :, ua]
    u0, u1 = U.min() + 0.004, U.max() - 0.004
    if u1 - u0 < 0.03: return None
    ns = max(int(round((u1 - u0) / du)) + 1, 5)
    us = np.linspace(u0, u1, ns)
    profs = [(u, section_profile(Tp, frame, u)) for u in us]
    profs = [(u, p) for u, p in profs if p is not None]
    if len(profs) < 4: return None
    # creases: chain section peaks across sections by v
    chains = []
    for si, (u, p) in enumerate(profs):
        for i in peaks(turning(p)):
            v = p[i, 0]
            best = None
            for ch in chains:
                if ch[-1][0] == si - 1 and abs(ch[-1][1] - v) < 0.015 and (best is None or abs(ch[-1][1] - v) < abs(best[-1][1] - v)):
                    best = ch
            if best is not None: best.append((si, v))
            else: chains.append([(si, v)])
    long = [ch for ch in chains if len(ch) >= float(os.environ.get('CREASE_SPAN', 0.4)) * len(profs)]
    # crease v for every section (interpolate missing), sorted by mean v
    cv = []
    for ch in long:
        si = np.array([c[0] for c in ch]); vv = np.array([c[1] for c in ch])
        cv.append(np.interp(np.arange(len(profs)), si, vv))
    cv = sorted(cv, key=lambda x: x.mean())
    # segments: start | creases | end ; counts by mean length / 10 mm
    rows_per_seg = None; strips = []
    bounds = []
    for k, (u, p) in enumerate(profs):
        b = [p[0, 0]] + [min(max(c[k], p[0, 0] + 0.002), p[-1, 0] - 0.002) for c in cv] + [p[-1, 0]]
        bounds.append(np.maximum.accumulate(b))
    bounds = np.array(bounds)
    seglen = np.diff(bounds, axis=1).mean(0)
    counts = [max(int(round(L / 0.010)), 3) for L in seglen]
    for j in range(len(counts)):
        G = []
        for k, (u, p) in enumerate(profs):
            vq = np.linspace(bounds[k, j], bounds[k, j + 1], counts[j] + 1)
            hq = np.interp(vq, p[:, 0], p[:, 1])
            X = np.zeros((len(vq), 3)); X[:, ua] = u; X[:, va] = vq; X[:, ha] = hs * hq
            G.append(X)
        strips.append(np.array(G))
    return dict(strips=strips, creases=len(cv), sections=len(profs))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('car'); ap.add_argument('out')
    ap.add_argument('--du', type=float, default=0.05)
    a = ap.parse_args()
    ctx = B.setup(a.car, a.out)
    T, n, mid, names = skin_by_mesh(ctx, a.car)
    cls = classify(n)
    out = {}; info = []
    for m in np.unique(mid):
        for frame in FRAMES:
            sel = np.where((mid == m) & (cls == frame))[0]
            if len(sel) < 20: continue
            for comp in components(T, sel):
                Tp = T[comp]
                area = 0.5 * np.linalg.norm(np.cross(Tp[:, 1] - Tp[:, 0], Tp[:, 2] - Tp[:, 0]), axis=1).sum()
                if area < 0.003: continue
                r = build_panel(Tp, frame, a.du)
                if r is None: continue
                pid = len(info)
                for j, G in enumerate(r['strips']): out[f'p{pid}_s{j}'] = G
                info.append(dict(id=pid, mesh=names[m], frame=frame, area=round(float(area), 3), sections=r['sections'],
                                 creases=r['creases'], strips=len(r['strips'])))
    np.savez(os.path.join(a.out, f"{ctx['car']}_panels.npz"), **out)
    json.dump(info, open(os.path.join(a.out, f"{ctx['car']}_panels.json"), 'w'), indent=1)
    big = sorted(info, key=lambda x: -x['area'])
    print(len(info), 'panels,', sum(i['strips'] for i in info), 'strips')
    for i in big[:15]: print(f"  {i['mesh'][:24]:24s} {i['frame']:5s} {i['area']:6.3f} m2  sections {i['sections']:3d}  creases {i['creases']}")


if __name__ == '__main__':
    main()
