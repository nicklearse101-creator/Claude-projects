"""Bonnet underside cap + washer nozzles (research: Bonnet surfacing.md step 14), built from OUR skin, as meshes.

    python underside_build.py CAR_DIR BUILD.npz OUT.npz

AC needs a closed bonnet: the inside is a dark cap ('EXT_underside' in Kunos: GEO_hood_SUB2, 290 tris). Ours:
- bottom loop = our free boundary (bottom of the returns, flange, lip and walls; mesh_holes.py logic), chained into
  one closed loop and resampled every 10 mm;
- rim = a ruled band from each bottom point inward: 10 mm in from the edge (plan, square to the loop, pointing into
  the bonnet) at the height of the skin there minus 10 mm (Kunos: rim loop 10 mm inside the skin along its normal);
- lid = the rim loop plus a 120 mm plan grid inside it at skin height - 25 mm (Kunos: 19-30 mm under the skin),
  Delaunay in plan, triangles kept inside the rim polygon. Normals face down (into the engine bay).
Washer nozzles (Kunos GEO_hood_SUB0, EXT_details): one small wedge per side at x +-235.5, z 966: superellipse
sections lofted along z, 18.6 -> 8 mm wide, 13 -> 6 mm tall, base sunk 0.5 mm into our skin.
The cap and nozzles are appended to the build as faces 'hood:underside', 'hood:nozzleR/L'.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path: sys.path.append(r'D:\ClaudeData\pylibs')
from scipy.spatial import cKDTree, Delaunay
from scipy.interpolate import LinearNDInterpolator
from exact_dist import point_to_tris
import mesh_holes as MH


def free_segments(P, F, L, names, tol=0.3e-3):
    segs = []
    for i, nm in enumerate(names):
        Fi = F[L == i]
        if not len(Fi): continue
        be = MH.boundary_edges(Fi); A, B = P[be[:, 0]], P[be[:, 1]]
        vi = np.unique(Fi); lo, hi = P[vi].min(0) - 0.005, P[vi].max(0) + 0.005
        T = P[F[L != i]]; T = T[np.all((T.max(1) >= lo) & (T.min(1) <= hi), axis=1)]
        free = point_to_tris((A + B) / 2, T) > tol if len(T) else np.ones(len(A), bool)
        segs += list(zip(A[free], B[free]))
    return segs


def chain_loop(segs):
    """free segments -> one closed polyline: walk connected chains, then join chains end to nearest end"""
    key = lambda p: tuple(np.round(p * 2e4).astype(int))        # 0.05 mm
    adj = {}
    for a, b in segs:
        ka, kb = key(a), key(b)
        if ka == kb: continue
        adj.setdefault(ka, []).append((kb, b)); adj.setdefault(kb, []).append((ka, a))
    pos = {key(a): a for a, b in segs}; pos.update({key(b): b for a, b in segs})
    used = set(); chains = []
    for start in adj:
        if any((start, n) in used for n, _ in adj[start]) and len(adj[start]) == 2: continue
        for nb, _ in adj[start]:
            if (start, nb) in used: continue
            ch = [start]; cur, nxt = start, nb
            while True:
                used.add((cur, nxt)); used.add((nxt, cur)); ch.append(nxt)
                nx = [n for n, _ in adj[nxt] if (nxt, n) not in used]
                if not nx or nxt == start: break
                cur, nxt = nxt, nx[0]
            chains.append([pos[c] for c in ch])
    chains = [np.array(c) for c in chains if len(c) > 2]
    chains.sort(key=lambda c: -len(c))
    loop = list(chains.pop(0))
    while chains:                                               # attach the chain whose end is nearest the loop's end
        e = loop[-1]
        best = min([(np.linalg.norm(c[0] - e), i, False) for i, c in enumerate(chains)] +
                   [(np.linalg.norm(c[-1] - e), i, True) for i, c in enumerate(chains)])
        d, i, rev = best
        if d > 0.03: break                                      # > 30 mm away: not part of this loop
        c = chains.pop(i); loop += list(c[::-1] if rev else c)
    return np.array(loop), len(chains)


def resample(Q, step):
    Q = np.r_[Q, Q[:1]]; d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.arange(0, d[-1], step); return np.c_[[np.interp(t, d, Q[:, k]) for k in range(3)]].T


def inside_poly(pts, poly):
    x, y = pts[:, 0], pts[:, 1]; ins = np.zeros(len(pts), bool); n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        c = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 - y1 == 0, 1e-12, y2 - y1) + x1)
        ins ^= c
    return ins


def main():
    car, build, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d = np.load(build); P, F, N, L, names = d['P'], d['F'], d['N'], d['L'], list(d['names'])
    skin_ids = [i for i, n in enumerate(names) if n.startswith('hood:')]
    Sv = np.unique(F[np.isin(L, skin_ids)]); SP = P[Sv]
    hskin = LinearNDInterpolator(SP[:, [0, 2]], SP[:, 1])     # skin height over the plan (x, z) -> y
    segs = free_segments(P, F, L, names)
    loop, left = chain_loop(segs)
    B = resample(loop, 0.010)
    print(f'bottom loop: {len(segs)} free segments -> {len(B)} points every 10 mm, {np.linalg.norm(np.diff(np.r_[B, B[:1]], axis=0), axis=1).sum() * 1000:.0f} mm'
          f' ({left} small chains left over)')
    # plan orientation: counter-clockwise in (x, z) -> inward = left normal
    xz = B[:, [0, 2]]; area = 0.5 * np.sum(xz[:, 0] * np.roll(xz[:, 1], -1) - np.roll(xz[:, 0], -1) * xz[:, 1])
    if area < 0: B = B[::-1]; xz = xz[::-1]
    t = np.roll(xz, -1, 0) - np.roll(xz, 1, 0); t /= np.linalg.norm(t, axis=1)[:, None]
    nin = np.c_[-t[:, 1], t[:, 0]]
    Rxz = xz + 0.010 * nin
    hy = hskin(Rxz)
    bad = np.isnan(hy)
    if bad.any():                                               # outside the skin's hull (tight corners): nearest skin point
        tr = cKDTree(SP[:, [0, 2]]); _, j = tr.query(Rxz[bad]); hy[bad] = SP[j, 1]
    R = np.c_[Rxz[:, 0], hy - 0.010, Rxz[:, 1]]
    R[:, 1] = np.minimum(R[:, 1], B[:, 1] + 0.004)              # never above its own bottom edge by more than 4 mm
    n = len(B); Vr = np.r_[B, R]
    Fr = np.array([[i, (i + 1) % n, n + i] for i in range(n)] + [[(i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)])
    # lid
    lo, hi = Rxz.min(0), Rxz.max(0); gx, gz = np.meshgrid(np.arange(lo[0], hi[0], 0.12), np.arange(lo[1], hi[1], 0.12))
    G = np.c_[gx.ravel(), gz.ravel()]; G = G[inside_poly(G, Rxz)]
    dmin = np.min(np.linalg.norm(G[:, None] - Rxz[None], axis=2), axis=1); G = G[dmin > 0.05]
    Gy = hskin(G); G3 = np.c_[G[:, 0], Gy - 0.025, G[:, 1]]; G3 = G3[~np.isnan(Gy)]
    Vl = np.r_[R, G3]; tri = Delaunay(Vl[:, [0, 2]]).simplices
    cen = Vl[tri].mean(1)[:, [0, 2]]; tri = tri[inside_poly(cen, Rxz)]
    Vu = np.r_[Vr, G3]; Fu = np.r_[Fr, np.where(tri < n, tri + n, tri - n + 2 * n)]
    # normals face down / into the bonnet: flip triangles whose normal points up on average
    g = np.cross(Vu[Fu[:, 1]] - Vu[Fu[:, 0]], Vu[Fu[:, 2]] - Vu[Fu[:, 0]])
    Fu = np.where((g[:, 1] > 0)[:, None], Fu[:, [0, 2, 1]], Fu)
    g = np.cross(Vu[Fu[:, 1]] - Vu[Fu[:, 0]], Vu[Fu[:, 2]] - Vu[Fu[:, 0]]); g /= np.maximum(np.linalg.norm(g, axis=1), 1e-12)[:, None]
    Nu = np.zeros_like(Vu); np.add.at(Nu, Fu.ravel(), np.repeat(g, 3, axis=0)); Nu /= np.maximum(np.linalg.norm(Nu, axis=1), 1e-12)[:, None]
    hs = hskin(Vu[n:, [0, 2]]); ok = ~np.isnan(hs); above = Vu[n:, 1][ok] - hs[ok]   # rim + lid (the bottom loop IS the edge)
    print(f'underside: {len(Vu)} vertices, {len(Fu)} tris (rim {len(Fr)}, lid {len(tri)}); rim/lid vs skin above: max {above.max() * 1000:+.1f} mm (must be < 0)')
    # Kunos comparison (information): our cap vs GEO_hood_SUB2
    import panel_fit as PF
    Vk, Fk, _ = PF.load_mesh(car, 'GEO_hood_SUB2', raw=True)
    dk = point_to_tris(Vk, Vu[Fu]) * 1000
    print(f'Kunos underside vertices -> ours: median {np.median(dk):.1f}, p95 {np.percentile(dk, 95):.1f}, max {dk.max():.1f} mm')
    parts = [('hood:underside', Vu, Fu, Nu)]
    # nozzles
    for sgn, nm in ((1, 'R'), (-1, 'L')):
        zs = np.linspace(954.7, 973.9, 17) / 1000; us = np.linspace(0, 2 * np.pi, 25)[:-1]
        V_, rows = [], []
        for z in zs:
            # measured on Kunos (width / height above its base per z): full 18.6 x 11.5 mm back to z 963, then a
            # quarter-ellipse in plan to 8.4 mm and a linear fall to ~6 mm high at the blunt front (z 973.9)
            zz = z * 1000; q = max(zz - 963.0, 0.0)
            w = 18.6 * np.sqrt(max(1 - (q / 11.5) ** 2, 0.2)) / 2000; h = (11.5 - 0.55 * q) / 1000
            xc = sgn * 0.2355; base = float(hskin([[xc, z]])[0]) - 0.0015
            ring = []
            for u in us:
                c, s_ = np.cos(u), np.sin(u)
                ex = np.sign(c) * abs(c) ** (2 / 2.5); ey = np.sign(s_) * abs(s_) ** (2 / 2.5)
                yy = base + h * max(ey, 0.0) if ey >= 0 else base + 0.0 * ey
                ring.append([xc + w * ex, yy, z])
            rows.append(len(V_)); V_ += ring
        V_ = np.array(V_); m = len(us); Fn = []
        for i in range(len(zs) - 1):
            for j in range(m):
                a, b, c2, d2 = i * m + j, i * m + (j + 1) % m, (i + 1) * m + j, (i + 1) * m + (j + 1) % m
                Fn += [[a, c2, b], [b, c2, d2]]
        # end caps on their OWN vertices (flat shading: shared ring vertices averaged them into a dark hollow)
        r0, r1 = V_[:m].copy(), V_[-m:].copy(); cA = len(V_)
        V_ = np.r_[V_, [r0.mean(0)], r0, [r1.mean(0)], r1]; c0, c1 = cA, cA + 1 + m
        Fn += [[c0, c0 + 1 + (j + 1) % m, c0 + 1 + j] for j in range(m)] + [[c1, c1 + 1 + j, c1 + 1 + (j + 1) % m] for j in range(m)]
        Fn = np.array(Fn); g = np.cross(V_[Fn[:, 1]] - V_[Fn[:, 0]], V_[Fn[:, 2]] - V_[Fn[:, 0]])
        inw = ((V_[Fn].mean(1) - V_.mean(0)) * g).sum(1) < 0      # convex part: every face must point away from its centre
        Fn[inw] = Fn[inw][:, [0, 2, 1]]; g[inw] = -g[inw]
        g /= np.maximum(np.linalg.norm(g, axis=1), 1e-12)[:, None]
        Nn = np.zeros_like(V_); np.add.at(Nn, Fn.ravel(), np.repeat(g, 3, axis=0)); Nn /= np.maximum(np.linalg.norm(Nn, axis=1), 1e-12)[:, None]
        parts.append((f'hood:nozzle{nm}', V_, Fn, Nn))
    Vk0, Fk0, _ = PF.load_mesh(car, 'GEO_hood_SUB0', raw=True)
    allN = np.r_[parts[1][1], parts[2][1]]; allF = np.r_[parts[1][2], parts[2][2] + len(parts[1][1])]
    dn = point_to_tris(Vk0, allN[allF]) * 1000
    print(f'nozzles: Kunos nozzle vertices -> ours: median {np.median(dn):.2f}, p95 {np.percentile(dn, 95):.2f}, max {dn.max():.2f} mm')
    P2, F2, N2, L2, nm2, off = [P], [F], [N], [L], names[:], len(P)
    for nm, V_, F_, N_ in parts:
        P2.append(V_); F2.append(F_ + off); N2.append(N_); L2.append(np.full(len(F_), len(nm2))); nm2.append(nm); off += len(V_)
    np.savez(out, P=np.concatenate(P2), F=np.concatenate(F2), N=np.concatenate(N2), L=np.concatenate(L2), names=np.array(nm2))
    print('saved', out)


if __name__ == '__main__':
    main()
