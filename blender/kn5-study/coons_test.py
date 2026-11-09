"""Patch-from-curves test: build a panel as a Coons patch of its 4 edge curves (no smoothing at all).

    python coons_test.py PANEL_mesh.npz [--inner N]

PANEL_mesh.npz: a panel exported from Blender (V, E, B as in lines_to_surface.py).
1. Outer edge loop of the panel -> split at its 4 sharpest corners -> 4 edge curves (method test:
   taken from the model; later traced from pictures).
2. Coons patch: S(u,v) = ruled(u) + ruled(v) - bilinear(corners)   (exact transfinite interpolation)
   Gordon variant (--inner N): N extra section curves across the panel, interpolated the same way.
3. Our quad grid on the patch (loops follow the edges). Score: true panel vertices -> our surface.
"""
import sys, os, json, argparse
import numpy as np


def boundary_loops(V, E, B):
    be = E[B[E[:, 0]] & B[E[:, 1]]]
    adj = {}
    for a, b in be: adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen, loops = set(), []
    for s in adj:
        if s in seen: continue
        loop = [s]; seen.add(s); prev, cur = None, s
        while True:
            nxt = [x for x in adj[cur] if x != prev and x not in seen]
            if not nxt: break
            prev, cur = cur, nxt[0]; loop.append(cur); seen.add(cur)
        if len(loop) > 10: loops.append(np.array(loop))
    return loops


def resample(P, n):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n)
    return np.c_[[np.interp(t, d, P[:, k]) for k in range(3)]].T


def corners(L, k=4, win=6):
    """indices of the k sharpest turns of a closed polyline"""
    n = len(L); ang = np.zeros(n)
    for i in range(n):
        a, b, c = L[i - win], L[i], L[(i + win) % n]
        u, v = b - a, c - b
        ang[i] = np.degrees(np.arccos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12), -1, 1)))
    idx = []
    for i in np.argsort(-ang):
        if all(min(abs(i - j), n - abs(i - j)) > n // 12 for j in idx): idx.append(i)
        if len(idx) == k: break
    return sorted(idx), ang


def coons(C0, C1, D0, D1, nu, nv):
    """C0(u) bottom, C1(u) top, D0(v) left, D1(v) right; corners shared"""
    u = np.linspace(0, 1, nu)[:, None, None]; v = np.linspace(0, 1, nv)[None, :, None]
    C0r, C1r = resample(C0, nu)[:, None, :], resample(C1, nu)[:, None, :]
    D0r, D1r = resample(D0, nv)[None, :, :], resample(D1, nv)[None, :, :]
    P00, P10, P01, P11 = C0[0], C0[-1], C1[0], C1[-1]
    Lc = (1 - v) * C0r + v * C1r
    Ld = (1 - u) * D0r + u * D1r
    Bl = ((1 - u) * (1 - v)) * P00 + (u * (1 - v)) * P10 + ((1 - u) * v) * P01 + (u * v) * P11
    return Lc + Ld - Bl


def nearest_dist(A, Bp, chunk=3000):
    out = np.empty(len(A))
    for s in range(0, len(A), chunk):
        out[s:s + chunk] = np.sqrt(((A[s:s + chunk, None, :] - Bp[None, :, :]) ** 2).sum(-1).min(1))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mesh'); ap.add_argument('--n', type=int, default=60)
    a = ap.parse_args()
    d = np.load(a.mesh); V, E, B = d['V'], d['E'], d['B']
    loops = boundary_loops(V, E, B)
    L = max(loops, key=lambda l: np.linalg.norm(np.diff(V[l], axis=0), axis=1).sum())
    P = resample(np.r_[V[L], V[L][:1]], 400)[:-1]
    ci, ang = corners(P)
    sides = [np.r_[P[ci[i]:], P[:ci[(i + 1) % 4] + 1]] if ci[(i + 1) % 4] < ci[i] else P[ci[i]:ci[(i + 1) % 4] + 1] for i in range(4)]
    # opposite sides: 0 & 2 (reverse 2), 1 & 3 (reverse 3)
    C0, D1, C1, D0 = sides[0], sides[1], sides[2][::-1], sides[3][::-1]
    S = coons(C0, C1, D0, D1, a.n, a.n)
    Sp = S.reshape(-1, 3)
    # dense sample of our patch for distance (bilinear refine x4)
    fine = coons(C0, C1, D0, D1, a.n * 4, a.n * 4).reshape(-1, 3)
    dist = nearest_dist(V[~B], fine) * 1000
    rep = dict(panel=os.path.basename(a.mesh), corners_deg=[round(float(ang[i]), 0) for i in ci],
               side_lengths_m=[round(float(np.linalg.norm(np.diff(s, axis=0), axis=1).sum()), 3) for s in sides],
               median_mm=round(float(np.median(dist)), 2), p90_mm=round(float(np.percentile(dist, 90)), 2),
               within_3mm_pct=round(float(np.mean(dist <= 3) * 100), 1), within_1mm_pct=round(float(np.mean(dist <= 1) * 100), 1))
    np.savez(a.mesh.replace('_mesh.npz', '_coons.npz'), S=S, sides=np.array(sides, dtype=object), dist=dist)
    print(json.dumps(rep))


if __name__ == '__main__':
    main()


def side_panel_curves(Q, nb=80):
    """4 edge curves of a side-facing panel from its points Q (Blender frame: x out, y along car, z up):
    bottom/top = lowest/highest point per lengthwise bin, front/rear = extreme lengthwise point per height bin.
    Each curve keeps the points' true depth (x)."""
    y, z = Q[:, 1], Q[:, 2]
    yb = np.linspace(y.min(), y.max(), nb); zb = np.linspace(z.min(), z.max(), nb)
    def prof(coord, other, bins, pick):
        out = []
        for i in range(len(bins) - 1):
            m = (coord >= bins[i]) & (coord < bins[i + 1])
            if m.sum() < 3: continue
            j = np.where(m)[0][pick(other[m])]
            out.append(Q[j])
        return np.array(out)
    bottom = prof(y, z, yb, np.argmin); top = prof(y, z, yb, np.argmax)
    front = prof(z, y, zb, np.argmin); rear = prof(z, y, zb, np.argmax)
    return bottom, top, front, rear


def patch_test(Q, n=60, trim=0.02):
    """Coons patch from the 4 traced edge curves; corners made consistent; score Q -> patch"""
    bottom, top, front, rear = side_panel_curves(Q)
    # trim ends near corners (curves meet there), then force shared corners
    tr = lambda C: C[int(len(C) * trim): len(C) - int(len(C) * trim)]
    bottom, top, front, rear = tr(bottom), tr(top), tr(front), tr(rear)
    P00 = (bottom[0] + front[0]) / 2; P10 = (bottom[-1] + rear[0]) / 2
    P01 = (top[0] + front[-1]) / 2; P11 = (top[-1] + rear[-1]) / 2
    C0 = np.r_[[P00], bottom, [P10]]; C1 = np.r_[[P01], top, [P11]]
    D0 = np.r_[[P00], front, [P01]]; D1 = np.r_[[P10], rear, [P11]]
    S = coons(C0, C1, D0, D1, n, n)
    fine = coons(C0, C1, D0, D1, n * 4, n * 4).reshape(-1, 3)
    return S, fine, (C0, C1, D0, D1)


def clean_side_curves(Q, cell=0.01, n_out=200):
    """4 clean edge curves of a side-facing panel: ordered outline in side view (y along, z up) split at
    the 4 corners nearest the bounding-box corners; depth (x) of each outline point = median x of the
    panel points within 20 mm."""
    y, z = Q[:, 1], Q[:, 2]
    y0, z0 = y.min() - 3 * cell, z.min() - 3 * cell
    W = int((y.max() - y0) / cell) + 4; H = int((z.max() - z0) / cell) + 4
    img = np.zeros((W, H), bool); img[((y - y0) / cell).astype(int), ((z - z0) / cell).astype(int)] = True
    def dil(a, n):
        for _ in range(n):
            b = a.copy(); b[1:] |= a[:-1]; b[:-1] |= a[1:]; b[:, 1:] |= a[:, :-1]; b[:, :-1] |= a[:, 1:]; a = b
        return a
    def ero(a, n): return ~dil(~a, n)
    sol = ero(dil(img, 3), 3)
    from PIL import Image, ImageDraw
    im = Image.fromarray(np.where(sol, 255, 0).astype(np.uint8)).copy(); ImageDraw.floodfill(im, (0, 0), 128)
    sol = np.array(im) != 128
    inner = ero(sol, 1); bd = np.argwhere(sol & ~inner)
    cy, cz = bd.mean(0); ang = np.arctan2(bd[:, 1] - cz, bd[:, 0] - cy)
    loop = bd[np.argsort(ang)]
    P2 = np.c_[y0 + loop[:, 0] * cell, z0 + loop[:, 1] * cell]
    # depth from the panel's own points
    X = np.empty(len(P2))
    for i, (py, pz) in enumerate(P2):
        dd = (y - py) ** 2 + (z - pz) ** 2
        near = dd < 0.02 ** 2
        X[i] = np.median(Q[near, 0]) if near.any() else Q[np.argmin(dd), 0]
    L3 = np.c_[X, P2]
    # corners: nearest outline points to the bbox corners (order: bottom-front, bottom-rear, top-rear, top-front)
    bb = [(P2[:, 0].min(), P2[:, 1].min()), (P2[:, 0].max(), P2[:, 1].min()), (P2[:, 0].max(), P2[:, 1].max()), (P2[:, 0].min(), P2[:, 1].max())]
    ci = [int(np.argmin(((P2 - np.array(c)) ** 2).sum(1))) for c in bb]
    def seg(i, j):
        return L3[i:j + 1] if j >= i else np.r_[L3[i:], L3[:j + 1]]
    # the loop runs anticlockwise in (y, z): bottom (front->rear), rear (bottom->top), top (rear->front), front (top->bottom)
    bottom, rear, top, front = seg(ci[0], ci[1]), seg(ci[1], ci[2]), seg(ci[2], ci[3]), seg(ci[3], ci[0])
    rs = lambda C: resample(C, n_out)
    return rs(bottom), rs(top[::-1]), rs(front[::-1]), rs(rear)


def two_way(Q, fine):
    """truth -> patch and patch -> truth distances (mm); the second catches folds and overhangs"""
    return nearest_dist(Q, fine) * 1000, nearest_dist(fine, Q) * 1000
