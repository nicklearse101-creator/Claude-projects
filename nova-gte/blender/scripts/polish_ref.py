"""Polish the outer skin of REF_BODY (Nik 2026-10-19: rough paint edges / body lines - polish them out without
warping the model). Runs after prep_reference.py (needs its colour zones), before frames_ref / details_ref (they are
laid onto the polished surface).

Feature-preserving denoise (bilateral normal filtering, then vertices moved to fit the filtered normals):
- face normals averaged with their edge neighbours, weighted by distance and by normal similarity (sigma_r ~20 deg),
  so ripples and streaks are evened out but real edges (panel gaps, creases, ribs) are kept;
- each vertex moved towards the planes of its filtered faces, the total move capped at MAX_MOVE (1 mm): the shape
  cannot change by more than that anywhere;
- shading normals rebuilt per corner from the faces round the vertex, weighted by how close they lie to the corner's
  own face (full within 20 deg, fading to none at 60 deg): smooth across noise, crisp along edges, no ragged switching
  where a crease zig-zags. The pinstripe rib band gets the shading normals only (its vertices do not move).
Only the body paint / black / grey trim / rubber faces of the outer skin move; vertices on the edge of that region or
on an open edge stay fixed. Left alone: the pinstripe rib band, grille, lamps, chrome, plates, interior, and the
surroundings of parts laid on the skin earlier (fuel flap, sunroof).
"""
import numpy as np

import bpy

MAX_MOVE = 0.0010
SIGMA_R = 0.35
CREASE_DEG = (20.0, 60.0)     # shading: faces within 20 deg blend fully, beyond 60 deg not at all (soft between:
                              # a hard cut-off made ragged lines where the model's creases zig-zag)
BODY_MATS = ("paint_gunmetal", "trim_black", "trim_grey", "rubber_black")
SHADE_ONLY = ("paint_stripes",)                # shading normals rebuilt, vertices not moved (the rib band)
KEEP_OUT = [  # (centre, radius): parts laid on the skin before this step
    ((-0.7547, 0.8127, 0.6105), 0.11),     # DET_FUEL
]
SUNROOF_BOX = (-0.38, 0.38, -0.17, 0.34, 1.20)   # x0, x1, y0, y1, z above


# stronger local pass where the model itself is crumpled (more than MAX_MOVE deep): boxes x0, x1, y0, y1, z0, z1
CRUMPLED = [(0.46, 0.68, -0.87, -0.66, 0.84, 1.00), (-0.68, -0.46, -0.87, -0.66, 0.84, 1.00)]   # scuttle ends


def polish(iters_n=10, iters_v=10, region=None, max_move=MAX_MOVE, sigma_r=SIGMA_R, set_normals=True):
    o = bpy.data.objects["REF_BODY"]; me = o.data
    nv, nf, nl = len(me.vertices), len(me.polygons), len(me.loops)
    co = np.empty(nv * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    co0 = co.copy()
    ls = np.empty(nf, np.int64); me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(nf, np.int64); me.polygons.foreach_get("loop_total", lt)
    cv = np.empty(nl, np.int64); me.loops.foreach_get("vertex_index", cv)
    ce = np.empty(nl, np.int64); me.loops.foreach_get("edge_index", ce)
    mi = np.empty(nf, np.int64); me.polygons.foreach_get("material_index", mi)
    cf = np.repeat(np.arange(nf), lt)                                   # face of each corner
    names = [m.name for m in me.materials]
    sel = np.isin(mi, [names.index(n) for n in BODY_MATS if n in names])
    shade = sel | np.isin(mi, [names.index(n) for n in SHADE_ONLY if n in names])

    def centroids(P):
        return np.stack([np.bincount(cf, weights=P[cv, k], minlength=nf) for k in range(3)], 1) / lt[:, None]

    C = centroids(co)
    if region is not None:
        inr = np.zeros(nf, bool)
        for x0, x1, y0, y1, z0, z1 in region:
            inr |= ((C[:, 0] > x0) & (C[:, 0] < x1) & (C[:, 1] > y0) & (C[:, 1] < y1) & (C[:, 2] > z0) & (C[:, 2] < z1))
        sel &= inr; shade &= inr
    for c, r in KEEP_OUT:
        sel &= np.linalg.norm(C - np.array(c), axis=1) > r
    x0, x1, y0, y1, zt = SUNROOF_BOX
    sel &= ~((C[:, 0] > x0) & (C[:, 0] < x1) & (C[:, 1] > y0) & (C[:, 1] < y1) & (C[:, 2] > zt))
    for c, r in KEEP_OUT:
        shade &= np.linalg.norm(C - np.array(c), axis=1) > r
    shade &= ~((C[:, 0] > x0) & (C[:, 0] < x1) & (C[:, 1] > y0) & (C[:, 1] < y1) & (C[:, 2] > zt))

    # edge -> its two faces (open / non-manifold edges: their vertices stay fixed)
    order = np.argsort(ce, kind="stable")
    es, fs = ce[order], cf[order]
    cnt = np.bincount(es, minlength=len(me.edges))
    first = np.searchsorted(es, np.arange(len(me.edges)))
    two = np.where(cnt == 2)[0]
    fa, fb = fs[first[two]], fs[first[two] + 1]
    pair = sel[fa] & sel[fb]
    fa, fb = fa[pair], fb[pair]
    E = np.empty(len(me.edges) * 2, np.int64); me.edges.foreach_get("vertices", E); E = E.reshape(-1, 2)
    fixed = np.zeros(nv, bool)
    fixed[E[cnt != 2].ravel()] = True
    fixed[cv[~sel[cf]]] = True                                           # touches a face outside the region
    free = ~fixed
    free[cv[~sel[cf]]] = False

    # face normals / areas
    def normals_areas(P):
        Cc = centroids(P)
        nxt = np.arange(nl) + 1
        last = ls + lt - 1
        nxt[last] = ls                                                   # wrap round each face
        a, b = P[cv], P[cv[nxt]]
        Nn = np.stack([np.bincount(cf, weights=(a[:, (k + 1) % 3] - b[:, (k + 1) % 3]) * (a[:, (k + 2) % 3] + b[:, (k + 2) % 3]),
                                   minlength=nf) for k in range(3)], 1)  # Newell
        A = np.linalg.norm(Nn, axis=1) / 2
        return Cc, Nn / np.maximum(2 * A[:, None], 1e-15), A

    C, N, A = normals_areas(co)
    sig_s = float(np.linalg.norm(C[fa] - C[fb], axis=1).mean())
    ws = np.exp(-np.sum((C[fa] - C[fb]) ** 2, 1) / (2 * sig_s ** 2))
    Nf = N.copy()
    for _ in range(iters_n):
        wr = np.exp(-np.sum((Nf[fa] - Nf[fb]) ** 2, 1) / (2 * sigma_r ** 2)) * ws
        acc = Nf * A[:, None]
        for k in range(3):
            acc[:, k] += np.bincount(fa, weights=wr * A[fb] * Nf[fb, k], minlength=nf)
            acc[:, k] += np.bincount(fb, weights=wr * A[fa] * Nf[fa, k], minlength=nf)
        Nf = np.where(sel[:, None], acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-15), N)

    # vertices to the filtered planes, capped
    sc = sel[cf]
    deg = np.bincount(cv[sc], minlength=nv).astype(float)
    for _ in range(iters_v):
        C = centroids(co)
        d = np.sum(Nf[cf[sc]] * (C[cf[sc]] - co[cv[sc]]), 1)
        mv = np.stack([np.bincount(cv[sc], weights=Nf[cf[sc], k] * d, minlength=nv) for k in range(3)], 1)
        mv /= np.maximum(deg, 1)[:, None]
        co[free] += mv[free]
        disp = co - co0
        L = np.linalg.norm(disp, axis=1)
        over = L > max_move
        co[over] = co0[over] + disp[over] * (max_move / L[over])[:, None]
    me.vertices.foreach_set("co", co.ravel()); me.update()

    if not set_normals:                             # normals_ref.py sets the shading normals afterwards
        moved = np.linalg.norm(co - co0, axis=1)
        return {"faces": int(sel.sum()), "verts_moved": int((moved > 1e-5).sum()), "max_move_mm": round(float(moved.max() * 1000), 3)}
    # shading normals: per corner, faces round the vertex weighted by area and by how close their normal is to the
    # corner's own face (full within CREASE_DEG[0], none beyond CREASE_DEG[1])
    C, N, A = normals_areas(co)
    Lc = np.empty(nl * 3, np.float32); me.corner_normals.foreach_get("vector", Lc); Lc = Lc.reshape(-1, 3)
    vo = np.argsort(cv, kind="stable")
    vdeg = np.bincount(cv, minlength=nv)
    vst = np.concatenate([[0], np.cumsum(vdeg)])
    c_lo, c_hi = np.cos(np.radians(CREASE_DEG[1])), np.cos(np.radians(CREASE_DEG[0]))
    touched = np.unique(cv[shade[cf]])
    for k in np.unique(vdeg[touched]):
        vs = touched[vdeg[touched] == k]
        for s0 in range(0, len(vs), 40000):
            v = vs[s0:s0 + 40000]
            idx = vo[vst[v][:, None] + np.arange(k)]                      # (m, k) corners round each vertex
            F = cf[idx]
            NN = N[F].astype(np.float32); AA = (A[F] * shade[F]).astype(np.float32)
            dots = np.einsum("mid,mjd->mij", NN, NN)
            t = np.clip((dots - c_lo) / (c_hi - c_lo), 0, 1)
            w = (t * t * (3 - 2 * t)) * AA[:, None, :]
            R = np.einsum("mij,mjd->mid", w, NN)
            R /= np.maximum(np.linalg.norm(R, axis=2, keepdims=True), 1e-12)
            own = shade[F]
            Lc[idx[own]] = R[own]
    me.normals_split_custom_set(Lc)
    moved = np.linalg.norm(co - co0, axis=1)
    return {"faces": int(sel.sum()), "verts_moved": int((moved > 1e-5).sum()),
            "mean_move_mm": round(float(moved[moved > 1e-5].mean() * 1000), 3) if (moved > 1e-5).any() else 0,
            "max_move_mm": round(float(moved.max() * 1000), 3), "sigma_s_mm": round(sig_s * 1000, 2)}


def main():
    return {"skin": polish(set_normals=False),
            "crumpled": polish(iters_n=20, iters_v=20, region=CRUMPLED, max_move=0.003, sigma_r=0.6, set_normals=False)}


if __name__ == "__main__":
    print("==", main())
