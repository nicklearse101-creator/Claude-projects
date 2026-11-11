"""C-pillar station analysis (research report 'Smooth region segmentation into faces', steps 3-6).
Sections of one crease region square to its main axis every PS_STEP mm; per station: the section polyline (cut through
the region's triangles), its turn profile, the turn's start/end (cumulative 5 % / 95 %), total turn theta, and the
tangent-circle radius r and setback d = r tan(theta/2) from lines fitted to the flats outside a guard band.
Usage: python pillar_stations.py CAR_DIR MESH REGION OUT.npz   (PF_CLIP as for panel_fit)"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panel_fit as P


def section(T, Nt, o, nrm):
    """segments of triangles T (k,3,3) cut by the plane (o, nrm); vertex normals Nt (k,3,3) interpolated"""
    d = (T - o) @ nrm; s = np.sign(d); m = (s.min(1) < 0) & (s.max(1) > 0)
    segs, nn = [], []
    for t, e, n in zip(T[m], d[m], Nt[m]):
        pts, ns = [], []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if e[i] * e[j] < 0:
                a = e[i] / (e[i] - e[j]); pts.append(t[i] + a * (t[j] - t[i])); ns.append(n[i] + a * (n[j] - n[i]))
        if len(pts) == 2: segs.append(pts); nn.append(ns)
    return np.array(segs), np.array(nn)


def chain(segs, nn, tol=1e-6):
    """join segments into the longest polyline (points + normals)"""
    if not len(segs): return np.zeros((0, 3)), np.zeros((0, 3))
    key = lambda p: tuple(np.round(p / 1e-5).astype(int))
    adj = {}
    for k, (a, b) in enumerate(segs):
        adj.setdefault(key(a), []).append((k, 0)); adj.setdefault(key(b), []).append((k, 1))
    used = np.zeros(len(segs), bool); best = None
    for k0 in range(len(segs)):
        if used[k0]: continue
        P_, N_ = [segs[k0][0], segs[k0][1]], [nn[k0][0], nn[k0][1]]; used[k0] = True
        for end in (1, 0):
            while True:
                p = P_[-1] if end else P_[0]
                nxt = [(k, w) for k, w in adj.get(key(p), []) if not used[k]]
                if not nxt: break
                k, w = nxt[0]; used[k] = True; q, qn = segs[k][1 - w], nn[k][1 - w]
                if end: P_.append(q); N_.append(qn)
                else: P_.insert(0, q); N_.insert(0, qn)
        if best is None or len(P_) > len(best[0]): best = (P_, N_)
    return np.array(best[0]), np.array(best[1])


def main():
    car, mesh, ri, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    step = float(os.environ.get('PS_STEP', 25)) / 1000
    V, F, Nv = P.load_mesh(car, mesh); pcs = P.crease_pieces(V, F, Nv); Fr = pcs[ri]
    X = V[np.unique(Fr)]; c0 = X.mean(0); es = np.linalg.svd(X - c0)[2][0]
    if es[2] > 0: es = -es                                   # run from the roof (front) to the tail
    s = (X - c0) @ es
    T = V[Fr]; Nt = Nv[Fr] / np.linalg.norm(Nv[Fr], axis=2)[..., None]
    st = []
    for sv in np.arange(s.min() + step / 2, s.max(), step):
        Q, QN = chain(*section(T, Nt, c0 + sv * es, es))
        if len(Q) < 3: continue
        # 2D frame: x across (outward-ish = mean normal projected), section plane basis
        nm = QN.mean(0); nm -= (nm @ es) * es; nm /= np.linalg.norm(nm); b = np.cross(es, nm)
        q2 = np.c_[(Q - Q.mean(0)) @ b, (Q - Q.mean(0)) @ nm]
        d = np.diff(q2, axis=0); l = np.linalg.norm(d, axis=1); keep = l > 1e-5
        if keep.sum() < 2: continue
        idx = np.r_[0, np.nonzero(keep)[0] + 1]; q2 = q2[idx]; Q = Q[idx]; QN = QN[idx]
        d = np.diff(q2, axis=0); l = np.linalg.norm(d, axis=1); d /= l[:, None]
        turn = np.arctan2(d[:-1, 0] * d[1:, 1] - d[:-1, 1] * d[1:, 0], (d[:-1] * d[1:]).sum(1))
        st.append(dict(s=sv, Q=Q, QN=QN, q2=q2, turn=turn, seglen=l, frame=np.array([c0 + sv * es, b, nm, es])))
    np.save(out, np.array(st, dtype=object), allow_pickle=True)
    for k in st:
        t = np.degrees(k['turn']); L = k['seglen'] * 1000
        segtxt = ' '.join(f'[{a:.0f}]{b:+.0f}' for a, b in zip(L[:-1], t)) + f' [{L[-1]:.0f}]'
        print(f"s {k['s']*1000:6.0f}  pts {len(k['Q']):2d}  width {L.sum():5.0f} mm  turn {t.sum():+5.0f}  : {segtxt}")


if __name__ == '__main__':
    main()
