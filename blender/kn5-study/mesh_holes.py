"""Watertight check on a packed build (mesh level): free boundary loops between the faces.

    python mesh_holes.py BUILD.npz [TOL_MM=0.3] [--fill OUT.npz]

Every face's display mesh is separate. A boundary edge of one face is JOINED when its midpoint lies within TOL of
another face's triangles; otherwise it is FREE. Free edges are chained into loops (endpoints within 0.05 mm). The long
loop(s) are the panel's real open edges (bonnet: the bottom of the returns, flange, lip and walls); short loops are
holes. (OCC sewing refused the bonnet's boolean-cut skin faces even at 1 mm although the joins are 0.02 mm: 11 Nov.)
Prints the loops; writes BUILD_holes.npz (each free loop as a polyline, metres).
--fill: free groups smaller than 12 mm are pin-holes (corner meetings: bonnet rounds / chamfer ends / skin corner).
Groups within 8 mm of each other are one hole; its free points are ordered round their centre in their best-fit
plane and closed by a triangle fan from the centre (lifted onto the plane fit). Mesh-only G0 patches of a few mm,
written with the build as faces 'holefill:k' to OUT.npz.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path: sys.path.append(r'D:\ClaudeData\pylibs')
from exact_dist import point_to_tris


def boundary_edges(F):
    e = np.sort(np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=1)
    u, c = np.unique(e, axis=0, return_counts=True)
    return u[c == 1]


def main():
    d = np.load(sys.argv[1]); tol = float(sys.argv[2]) / 1000 if len(sys.argv) > 2 else 0.3e-3
    P, F, L, names = d['P'], d['F'], d['L'], list(d['names'])
    segs = []                                               # free boundary segments (a, b) in metres
    per = {}
    for i, nm in enumerate(names):
        Fi = F[L == i]; vi = np.unique(Fi);
        if not len(Fi): continue
        be = boundary_edges(Fi)
        A, B = P[be[:, 0]], P[be[:, 1]]; M = (A + B) / 2
        other = F[L != i]
        # only triangles near this face's box (speed)
        lo, hi = P[vi].min(0) - 0.005, P[vi].max(0) + 0.005
        T = P[other]; keep = np.all((T.max(1) >= lo) & (T.min(1) <= hi), axis=1); T = T[keep]
        dist = point_to_tris(M, T) if len(T) else np.full(len(M), 1.0)
        free = dist > tol
        per[nm] = (len(be), int(free.sum()), float(np.linalg.norm(B[free] - A[free], axis=1).sum() * 1000))
        segs += list(zip(A[free], B[free]))
    print(f'{len(segs)} free boundary segments, {sum(np.linalg.norm(a - b) for a, b in segs) * 1000:.0f} mm')
    for nm, (n, f, ln) in sorted(per.items(), key=lambda kv: -kv[1][2]):
        if f: print(f'  {nm:16s} boundary {n:5d} edges, free {f:5d} ({ln:7.1f} mm)')
    # chain segments into connected groups
    X = np.array([p for ab in segs for p in ab]); n = len(segs)
    par = list(range(n))
    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    from scipy.spatial import cKDTree
    tr = cKDTree(X)
    for a, b in tr.query_pairs(5e-5):
        ra, rb = find(a // 2), find(b // 2)
        if ra != rb: par[ra] = rb
    groups = {}
    for i in range(n): groups.setdefault(find(i), []).append(i)
    out = []
    for g in groups.values():
        Q = np.array([segs[i] for i in g]).reshape(-1, 3)
        ln = sum(np.linalg.norm(segs[i][0] - segs[i][1]) for i in g) * 1000
        out.append((ln, float(np.linalg.norm(np.ptp(Q, axis=0)) * 1000), Q.mean(0) * 1000, Q))
    out.sort(key=lambda o: -o[0])
    print(f'{len(out)} free groups:')
    for ln, sz, c, _ in out[:40]:
        print(f'  length {ln:8.1f} mm  size {sz:7.1f} mm  centre ({c[0]:6.0f},{c[1]:5.0f},{c[2]:6.0f})')
    np.savez(os.path.splitext(sys.argv[1])[0] + '_holes.npz', **{f'g{k}': o[3] for k, o in enumerate(out)})
    if '--fill' in sys.argv:
        fill(d, [o for o in out if o[1] < 12.0], sys.argv[sys.argv.index('--fill') + 1])


def fill(d, small, out_path):
    P, F, N, L, names = d['P'], d['F'], d['N'], d['L'], list(d['names'])
    cl = []                                                  # clusters of small groups
    for o in small:
        for c in cl:
            if np.linalg.norm(c['c'] - o[2]) < 8.0: c['Q'].append(o[3]); c['c'] = np.mean([q.mean(0) for q in c['Q']], 0) * 1000; break
        else: cl.append(dict(c=o[2], Q=[o[3]]))
    P2, F2, N2, L2, nm2 = [P], [F], [N], [L], names[:]
    off = len(P)
    for k, c in enumerate(cl):
        Q = np.unique(np.round(np.vstack(c['Q']), 7), axis=0)
        if len(Q) < 3: continue
        m = Q.mean(0); U, S, Vt = np.linalg.svd(Q - m); n = Vt[2]
        a = (Q - m) @ Vt[0]; b = (Q - m) @ Vt[1]; o = np.argsort(np.arctan2(b, a)); Q = Q[o]
        # outward: the build's normals at the nearest vertices
        near = np.argsort(np.linalg.norm(P - m, axis=1))[:20]; nb = N[near].mean(0)
        if n @ nb < 0: n = -n
        V = np.r_[[m], Q]; T = np.array([[0, 1 + i, 1 + (i + 1) % len(Q)] for i in range(len(Q))])
        g = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        if (g @ n).mean() < 0: T = T[:, [0, 2, 1]]
        P2.append(V); F2.append(T + off); N2.append(np.tile(n, (len(V), 1))); L2.append(np.full(len(T), len(nm2)))
        nm2.append(f'holefill:{k}'); off += len(V)
        print(f'  holefill:{k}: {len(Q)} boundary points round ({m[0] * 1000:.0f},{m[1] * 1000:.0f},{m[2] * 1000:.0f}), size {np.ptp(Q, axis=0).max() * 1000:.1f} mm, flatness {S[2] / max(S[0], 1e-12):.2f}')
    np.savez(out_path, P=np.concatenate(P2), F=np.concatenate(F2), N=np.concatenate(N2), L=np.concatenate(L2), names=np.array(nm2))
    print(f'{len(nm2) - len(names)} hole fills -> {out_path}')


if __name__ == '__main__':
    main()
