"""Exact point -> triangle-surface distances (no scipy): triangles hashed into a uniform grid.

    d = point_to_tris(P, T, cell=0.02, cap=0.02)   # metres, capped at cap
Point-to-point scoring against 4 mm samples adds ~1 mm of sampling error; this has none.
"""
import numpy as np


def _seg(P, A, B):
    AB = B - A; t = np.clip(((P - A) * AB).sum(-1) / np.maximum((AB * AB).sum(-1), 1e-18), 0, 1)
    Q = A + t[..., None] * AB
    return np.sqrt(((P - Q) ** 2).sum(-1))


def pt_tri(P, T):
    """P (m,3), T (k,3,3) -> (m,k) exact distances"""
    A, B, C = T[None, :, 0], T[None, :, 1], T[None, :, 2]; X = P[:, None, :]
    n = np.cross(B - A, C - A); nn = np.linalg.norm(n, axis=-1, keepdims=True); n = n / np.maximum(nn, 1e-18)
    h = ((X - A) * n).sum(-1); Y = X - h[..., None] * n
    c1 = (np.cross(B - A, Y - A) * n).sum(-1); c2 = (np.cross(C - B, Y - B) * n).sum(-1); c3 = (np.cross(A - C, Y - C) * n).sum(-1)
    inside = (c1 >= 0) & (c2 >= 0) & (c3 >= 0)
    e = np.minimum(np.minimum(_seg(X, A, B), _seg(X, B, C)), _seg(X, C, A))
    return np.where(inside, np.abs(h), e)


def point_to_tris(P, T, cell=0.02, cap=0.02):
    lo = np.minimum(P.min(0), T.reshape(-1, 3).min(0)) - cap
    key = lambda c: (c[:, 0] * 100003 + c[:, 1]) * 100019 + c[:, 2]
    # triangle -> every cell its (cap-expanded) bbox touches
    b0 = np.floor((T.min(1) - cap - lo) / cell).astype(np.int64); b1 = np.floor((T.max(1) + cap - lo) / cell).astype(np.int64)
    span = b1 - b0 + 1; tk, ti = [], []
    for dx in range(span[:, 0].max()):
        for dy in range(span[:, 1].max()):
            for dz in range(span[:, 2].max()):
                m = (dx < span[:, 0]) & (dy < span[:, 1]) & (dz < span[:, 2])
                c = b0[m] + [dx, dy, dz]; tk.append(key(c)); ti.append(np.where(m)[0])
    tk = np.concatenate(tk); ti = np.concatenate(ti); o = np.argsort(tk); tk, ti = tk[o], ti[o]
    pc = np.floor((P - lo) / cell).astype(np.int64); pk = key(pc)
    po = np.argsort(pk); pks = pk[po]
    out = np.full(len(P), cap)
    ukeys, starts = np.unique(pks, return_index=True); ends = np.r_[starts[1:], len(pks)]
    a = np.searchsorted(tk, ukeys, 'left'); b = np.searchsorted(tk, ukeys, 'right')
    for u in range(len(ukeys)):
        if a[u] == b[u]: continue
        pi = po[starts[u]:ends[u]]; tri = T[ti[a[u]:b[u]]]
        for s in range(0, len(pi), 256):
            q = pi[s:s + 256]
            out[q] = np.minimum(pt_tri(P[q], tri).min(1), cap)
    return out


def quads_to_tris(P):
    """grid (nu,nv,3) -> triangles (k,3,3)"""
    a, b, c, d = P[:-1, :-1], P[1:, :-1], P[1:, 1:], P[:-1, 1:]
    return np.concatenate([np.stack([a, b, c], -2).reshape(-1, 3, 3), np.stack([a, c, d], -2).reshape(-1, 3, 3)])


def stats(d):
    d = d * 1000
    return dict(median=round(float(np.median(d)), 2), p90=round(float(np.percentile(d, 90)), 2),
                within_1mm=round(float(np.mean(d <= 1) * 100), 1), within_3mm=round(float(np.mean(d <= 3) * 100), 1))
