"""Shape fixes on the reference body (docs/MODEL_TODO.md): runs on export/ref/nova_ref.blend (REF_BODY after
fit_reference.py), result saved as export/ref/nova_ref_fix.blend, then prep_reference.py -> nova_ref_mat.blend.

1  transverse bonnet line (a ~2 mm step across the bonnet at y -1.265, |x| < 0.42) smoothed out; the two dips
   beside the creases near the scuttle levelled (bonnet_dips)
2  fuel flap: the model's raised cap behind the right rear arch removed; new recessed flap + black cap where the real
   car has it (matched side photo cS: centre y 0.813, z 0.61, cap ~113 mm across, right rear quarter)
3  the round fitting on the right B/C-pillar removed
4  sunroof: glass panel + black seal on the roof (body_profile.json glass_panels.sunroof, ESTIMATE from cCF / c20)
8  mirror heads scaled outward to the brochure 1725 mm across
9  front bumper ribs straightened at the arch end (bumper_ribs)
17 front wing: the arch flare's top line made straight (front_arch_line, line from the side photo)
5  the model's raised door lettering and mirrored rear badge flattened (new ones: details_ref.py)
6  cabin front (dash, footwells) mirrored to right-hand drive
Features are removed by fitting the skin round them (local quadratic least squares on the skin vertices of a ring
outside the feature) and moving the feature's vertices onto that surface; the custom normals there are rebuilt.
Car frame: x+ = car's left, y- = front, z up.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCAN = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\scan"
SPLIT = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\nova_ref_split.blend"   # REF_BODY before the arch edits
FLAP_C = Vector((-0.7547, 0.8127, 0.6105))      # cS ray hit, photo pixel (380, 576)
FLAP_N = Vector((-0.99, -0.03, 0.11)).normalized()
MIRROR_HALF = 0.8625                              # 1725 / 2


def scan(view):
    z = np.load(os.path.join(SCAN, view + ".npz"))
    return z["depth"].astype(np.float64), z["u"], z["v"]


def idx(a, x):
    return np.clip(np.round((x - a[0]) / (a[1] - a[0])).astype(int), 0, len(a) - 1)


def coords(me):
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ remove a feature by refitting the skin
def patch(view, ac, bc, ha, hb, blend, ring, nb, tol, ring_ok=None):
    """Height-field patch. view: 'top' (h = z over (x, y)), 'side_R' / 'side_L' (h = -x / x over (y, z)) or 'rear'
    (h = y over (x, z)). Inner box centre
    (ac, bc), half sizes (ha, hb); full replacement inside, blended to nothing over `blend`; the skin is fitted from
    the ring blend..blend+ring outside the box (neighbours within nb = (da, db) of each vertex). Only vertices within
    tol = (inward, outward) of the fitted skin move. Returns the moved vertex indices."""
    me = bpy.data.objects["REF_BODY"].data
    co = coords(me)
    hax, sgn, aax, bax = {"top": (2, 1, 0, 1), "side_R": (0, -1, 1, 2), "side_L": (0, 1, 1, 2), "rear": (1, 1, 0, 2)}[view]
    a, b, h = co[:, aax], co[:, bax], sgn * co[:, hax]
    dout = np.hypot(np.maximum(np.abs(a - ac) - ha, 0), np.maximum(np.abs(b - bc) - hb, 0))
    near = np.where(dout < blend + ring)[0]
    dep, u, v = scan(view)
    sk = sgn * dep[idx(v, b[near]), idx(u, a[near])]
    an, bn, hn, dn = a[near], b[near], h[near], dout[near]
    ok = np.isfinite(sk)
    ringm = ok & (dn >= blend) & (np.abs(hn - sk) < 0.002)
    if ring_ok is not None:
        ringm &= ring_ok(an, bn)
    Ra, Rb, Rh = an[ringm], bn[ringm], hn[ringm]
    tgt = np.where(ok & (dn < blend) & (np.abs(hn - sk) < tol[0] + tol[1] + 0.02))[0]
    fit = np.full(len(tgt), np.nan)
    for k, t in enumerate(tgt):
        m = (np.abs(Ra - an[t]) < nb[0]) & (np.abs(Rb - bn[t]) < nb[1])
        if m.sum() < 12:
            continue
        da, db = Ra[m] - an[t], Rb[m] - bn[t]
        A = np.stack([np.ones_like(da), da, db, da * da, da * db, db * db], 1)
        fit[k] = np.linalg.lstsq(A, Rh[m], rcond=None)[0][0]
    d = hn[tgt] - fit
    sel = np.isfinite(fit) & (d > -tol[0]) & (d < tol[1])
    t = tgt[sel]
    w = 1.0 - smoothstep(0.0, blend, dn[t])
    vid = near[t]
    co[vid, hax] = sgn * (hn[t] + w * (fit[sel] - hn[t]))
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return vid, float(np.abs(d[sel]).max()) if sel.any() else 0.0


def refresh_normals(vid, rings=2):
    """Custom normals of the corners round the given vertices (plus `rings` edge rings) reset to the area-weighted
    face normals - the stored ones belong to the old shape."""
    me = bpy.data.objects["REF_BODY"].data
    nv = len(me.vertices)
    mask = np.zeros(nv, bool); mask[vid] = True
    E = np.empty(len(me.edges) * 2, np.int64); me.edges.foreach_get("vertices", E); E = E.reshape(-1, 2)
    for _ in range(rings):
        e = mask[E[:, 0]] | mask[E[:, 1]]
        mask[E[e].ravel()] = True
    nl, npo = len(me.loops), len(me.polygons)
    L = np.empty(nl * 3, np.float32); me.corner_normals.foreach_get("vector", L); L = L.reshape(-1, 3)
    cv = np.empty(nl, np.int64); me.loops.foreach_get("vertex_index", cv)
    FN = np.empty(npo * 3); me.polygons.foreach_get("normal", FN); FN = FN.reshape(-1, 3)
    FA = np.empty(npo); me.polygons.foreach_get("area", FA)
    lt = np.empty(npo, np.int64); me.polygons.foreach_get("loop_total", lt)
    fl = np.repeat(np.arange(npo), lt)
    s = mask[cv]
    acc = np.zeros((nv, 3)); np.add.at(acc, cv[s], FN[fl[s]] * FA[fl[s], None])
    vn = acc[cv[s]]; vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    L[s] = vn
    me.normals_split_custom_set(L)
    return int(mask.sum())


def bonnet_line():
    vid, mx = patch("top", 0.0, -1.264, 0.42, 0.024, 0.012, 0.07, (0.015, 0.10), (0.004, 0.004))
    return {"moved": len(vid), "max_step_mm": round(mx * 1000, 2), "normals": refresh_normals(vid)}


def bonnet_dips():
    """Nik 2026-10-19: two dips either side near the scuttle. Between each lengthways crease and the bonnet edge
    the outer panel sinks 10-17 mm from y ~-1.15 back to the scuttle (further forward it is a straight slope from the
    crease down to the edge). Per cross-section the panel is raised to the straight line from the crease top to the
    edge (x 0.612, inside the shut line at 0.63); nothing is lowered."""
    o = bpy.data.objects["REF_BODY"]; me = o.data
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    zat = lambda x, y: (bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 2.0)[0] or Vector((0, 0, np.nan))).z
    xc = lambda y: np.interp(y, [-1.66, -0.95, -0.89], [0.41, 0.476, 0.47])      # crease line (SHELL_MAP)
    XE = 0.612
    rows = np.arange(-1.30, -0.8695, 0.005)
    lines = {}
    for s in (1, -1):
        L = []
        for y in rows:
            xs = np.arange(xc(y) - 0.008, xc(y) + 0.0021, 0.002)      # top of the crease ridge
            zs = [zat(s * x, y) for x in xs]
            k = int(np.nanargmax(zs))
            L.append((xs[k], zs[k], zat(s * XE, y)))
        lines[s] = np.array(L)
    co = coords(me)
    x, y, z = co.T
    out = {}
    moved = []
    for s in (1, -1):
        Lp = lines[s]
        xp = np.interp(y, rows, Lp[:, 0]); zp = np.interp(y, rows, Lp[:, 1]); ze = np.interp(y, rows, Lp[:, 2])
        cand = np.where((s * x > xp) & (s * x < XE) & (y > rows[0]) & (y < rows[-1]) & (z > zp - 0.06))[0]
        line = zp[cand] + (ze[cand] - zp[cand]) * (s * x[cand] - xp[cand]) / (XE - xp[cand])
        top = np.array([zat(x[i], y[i]) for i in cand])
        on_skin = np.isfinite(top) & (z[cand] > top - 0.003)
        d = line - z[cand]
        w = (smoothstep(0, 0.006, s * x[cand] - xp[cand]) * smoothstep(0, 0.006, XE - s * x[cand])
             * smoothstep(-1.29, -1.21, y[cand]) * smoothstep(0, 0.004, -0.8705 - y[cand]))
        sel = on_skin & (d > 0)
        idx_ = cand[sel]
        co[idx_, 2] += d[sel] * w[sel]
        moved.append(idx_)
        out["L" if s > 0 else "R"] = {"moved": int(sel.sum()), "max_raise_mm": round(float((d[sel] * w[sel]).max() * 1000), 1) if sel.any() else 0}
    me.vertices.foreach_set("co", co.ravel()); me.update()
    # second pass: between y -1.27 and -0.94 the panel still sat ~10 mm under the crease top (the drop there starts
    # inboard of the mapped crease line). Fit the outer panel as a smooth surface - z = cubic in y + (slope linear in
    # y) * distance from the crease - to the good parts: undisturbed front rows, the levelled rear rows and the edge
    # column (x ~0.60, not sunken); raise what lies below it.
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    zat = lambda x, y: (bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 2.0)[0] or Vector((0, 0, np.nan))).z
    Y0, Y1 = -1.27, -0.905                     # to just short of the scuttle edge (the right side dips to -0.94)
    for s in (1, -1):
        S = []
        for y in np.arange(-1.36, -0.8745, 0.005):
            band = y < Y0 - 0.01 or y > Y1 + 0.01
            for x in (np.arange(xc(y) + 0.006, 0.606, 0.01) if band else np.arange(0.585, 0.606, 0.005)):
                S.append((x - xc(y), y, zat(s * x, y)))
        S = np.array(S); S = S[np.isfinite(S[:, 2])]
        A = lambda d, y: np.stack([np.ones_like(y), y, y * y, y ** 3, d, d * y], 1)
        c = np.linalg.lstsq(A(S[:, 0], S[:, 1]), S[:, 2], rcond=None)[0]
        out["pass2_fit_rms_mm_" + ("L" if s > 0 else "R")] = round(float(np.sqrt(((A(S[:, 0], S[:, 1]) @ c - S[:, 2]) ** 2).mean()) * 1000), 2)
        co = coords(me); x, y, z = co.T
        cand = np.where((s * x > xc(y) - 0.012) & (s * x < XE) & (y > Y0 - 0.03) & (y < Y1 + 0.03) & (z > 0.75))[0]
        top = np.array([zat(x[i], y[i]) for i in cand])
        fit = A(s * x[cand] - xc(y[cand]), y[cand]) @ c
        d = fit - z[cand]
        w = (smoothstep(0, 0.006, s * x[cand] - (xc(y[cand]) - 0.012)) * smoothstep(0, 0.006, XE - s * x[cand])
             * smoothstep(Y0 - 0.03, Y0, y[cand]) * smoothstep(Y1 + 0.03, Y1, y[cand]))
        sel = np.isfinite(top) & (z[cand] > top - 0.003) & (d > 0)
        co[cand[sel], 2] += d[sel] * w[sel]
        me.vertices.foreach_set("co", co.ravel()); me.update()
        moved.append(cand[sel])
        out["pass2_" + ("L" if s > 0 else "R")] = {"moved": int(sel.sum()),
                                                  "max_raise_mm": round(float((d[sel] * w[sel]).max() * 1000), 1) if sel.any() else 0}
    # third pass: the two passes left wrinkles at the rear outer corner (Nik: rough). The whole outer panel, crease
    # to edge, y -1.32 .. -0.875, is one smooth slope: fit z = (cubic in y) + (linear in y) d + c d^2 (d = distance
    # out from the crease) to it and lay its skin onto that, both ways, capped at 6 mm, blended at the crease, edge
    # and ends.
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    zat = lambda x, y: (bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 2.0)[0] or Vector((0, 0, np.nan))).z
    Y0, Y1 = -1.32, -0.875
    A3 = lambda d, y: np.stack([np.ones_like(y), y, y * y, y ** 3, d, d * y, d * d], 1)
    for s in (1, -1):
        S = []
        for y in np.arange(Y0 - 0.04, Y1 + 0.0001, 0.005):
            for x in np.arange(xc(y) + 0.008, XE - 0.004, 0.006):
                S.append((x - xc(y), y, zat(s * x, y)))
        S = np.array(S); S = S[np.isfinite(S[:, 2])]
        c = np.linalg.lstsq(A3(S[:, 0], S[:, 1]), S[:, 2], rcond=None)[0]
        for _ in range(2):                                           # drop outliers (the dips' last traces), refit
            r = A3(S[:, 0], S[:, 1]) @ c - S[:, 2]
            k = np.abs(r) < 2.5 * r.std() + 1e-4
            c = np.linalg.lstsq(A3(S[k, 0], S[k, 1]), S[k, 2], rcond=None)[0]
        co = coords(me); x, y, z = co.T
        cand = np.where((s * x > xc(y) - 0.004) & (s * x < XE + 0.004) & (y > Y0 - 0.03) & (y < Y1) & (z > 0.75))[0]
        top = np.array([zat(x[i], y[i]) for i in cand])
        dd = s * x[cand] - xc(y[cand])
        fit = A3(dd, y[cand]) @ c
        d = np.clip(fit - z[cand], -0.006, 0.006)
        w = (smoothstep(0.0, 0.010, dd) * smoothstep(0, 0.010, XE - s * x[cand])
             * smoothstep(Y0 - 0.03, Y0, y[cand]) * smoothstep(0, 0.006, Y1 - y[cand]))
        sel = np.isfinite(top) & (z[cand] > top - 0.003)
        co[cand[sel], 2] += d[sel] * w[sel]
        me.vertices.foreach_set("co", co.ravel()); me.update()
        moved.append(cand[sel])
        out["pass3_" + ("L" if s > 0 else "R")] = {"moved": int(sel.sum()),
                                                  "max_mm": round(float(np.abs(d[sel] * w[sel]).max() * 1000), 1)}
    out["normals"] = refresh_normals(np.concatenate(moved))
    return out


def bonnet_edge_y(x):
    """Clean bonnet rear edge (measured on the model: y -0.896 at the centre, ~-0.874 outboard of |x| 0.4)."""
    t = np.clip(1 - (np.asarray(x) / 0.40) ** 2, 0, None)
    return -0.874 - 0.022 * t * t


def bonnet_refit():
    """Nik 2026-10-19: 'the dents are still in the bonnet'. The whole bonnet top (y -1.58 .. rear edge, inside the
    shut lines) is replaced by smooth surfaces: centre panel z = sum a_ij x^2i Y^j (i <= 2, j <= 4, symmetric), outer
    panels z = sum b_ij u^i Y^j (u = |x| - crease, i <= 2, j <= 3), fitted robustly to the old top skin; the crease
    is where the two meet (z = max of both). No cap - the dents go. Blended out over the nose (y -1.58 .. -1.52)
    and over the last 15 mm before the side shut lines."""
    o = bpy.data.objects["REF_BODY"]; me = o.data
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    zat = lambda x, y: (bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 2.0)[0] or Vector((0, 0, np.nan))).z
    xc = lambda y: np.interp(y, [-1.66, -0.95, -0.85], [0.41, 0.476, 0.47])
    Yn = lambda y: (y + 1.22) / 0.35
    S = []
    for x in np.arange(-0.60, 0.6001, 0.01):
        for y in np.arange(-1.58, float(bonnet_edge_y(x)) - 0.008, 0.01):
            S.append((x, y, zat(x, y)))
    S = np.array(S); S = S[np.isfinite(S[:, 2])]
    ax, Y = np.abs(S[:, 0]), Yn(S[:, 1])
    Ac = lambda x, Y: np.stack([(x * x) ** i * Y ** j for i in range(3) for j in range(5)], 1)
    Ao = lambda u, Y: np.stack([u ** i * Y ** j for i in range(3) for j in range(4)], 1)

    def robust(A, z):
        k = np.ones(len(z), bool)
        for _ in range(4):
            c = np.linalg.lstsq(A[k], z[k], rcond=None)[0]
            r = A @ c - z
            k = np.abs(r) < 2.5 * r[k].std() + 2e-4
        return c, float(r[k].std())
    mc = ax < xc(S[:, 1]) - 0.015
    cc, sc = robust(Ac(S[mc, 0], Y[mc]), S[mc, 2])
    mo = (ax > xc(S[:, 1]) + 0.015) & (ax < 0.605)
    co_, so = robust(Ao(ax[mo] - xc(S[mo, 1]), Y[mo]), S[mo, 2])
    co = coords(me); x, y, z = co.T
    cand = np.where((np.abs(x) < 0.618) & (y > -1.585) & (y < bonnet_edge_y(x) + 0.003) & (z > 0.65))[0]
    top = np.array([zat(x[i], y[i]) for i in cand])
    sel = np.isfinite(top) & (z[cand] > top - 0.006) & (z[cand] < top + 0.004)
    c = cand[sel]
    zc_ = Ac(x[c], Yn(y[c])) @ cc
    zo_ = Ao(np.abs(x[c]) - xc(y[c]), Yn(y[c])) @ co_
    dc = np.abs(x[c]) - xc(y[c])
    # centre fit inboard, outer fit outboard; across the raised crease ridge (+-3 cm) a linear blend of the two plus
    # the model's own ridge profile, averaged along the ridge (Gaussian, sigma 8 cm in y, per 3 mm bin across it):
    # the ridge keeps its shape, the dents in it go
    BAND = 0.03
    t = np.clip((dc + BAND) / (2 * BAND), 0, 1)
    base = np.where(dc < -BAND, zc_, np.where(dc > BAND, zo_, zc_ + (zo_ - zc_) * t))
    tgt = base.copy()
    inb = np.abs(dc) <= BAND
    R = z[c] - base
    side = np.sign(x[c])
    bins = np.floor((dc + BAND) / 0.003).astype(int)
    for sd in (-1, 1):
        for b_ in np.unique(bins[inb]):
            k = np.where(inb & (side == sd) & (bins == b_))[0]
            if len(k) < 3:
                continue
            yy = y[c][k]
            W = np.exp(-0.5 * ((yy[:, None] - yy[None, :]) / 0.08) ** 2)
            tgt[k] = base[k] + (W @ R[k]) / W.sum(1)
    step_mm = round(float(np.abs(R[inb]).max() * 1000), 1) if inb.any() else 0
    w = smoothstep(-1.58, -1.52, y[c]) * smoothstep(0.618, 0.603, np.abs(x[c]))
    d = (tgt - z[c]) * w
    co[c, 2] += d
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return {"moved": int((np.abs(d) > 1e-5).sum()), "max_mm": round(float(np.abs(d).max() * 1000), 1),
            "mean_mm": round(float(np.abs(d[np.abs(d) > 1e-5]).mean() * 1000), 2), "fit_rms_mm": (round(sc * 1000, 2), round(so * 1000, 2)),
            "ridge_height_max_mm": step_mm,
            "normals": refresh_normals(c[np.abs(d) > 1e-5])}


def scuttle_cut():
    """Cut the bonnet's rear edge clean along bonnet_edge_y (vertical planes, 4 cm segments) and delete the model's
    scuttle (grille with the wipers moulded in) behind it, up to the windscreen, inside |x| 0.60. scuttle_ref.py
    builds the new panel, the bonnet edge lip and separate wipers."""
    xs = np.arange(-0.60, 0.6001, 0.04)
    planes = []
    for x0, x1 in zip(xs, xs[1:]):
        p0 = np.array([x0, float(bonnet_edge_y(x0))]); p1 = np.array([x1, float(bonnet_edge_y(x1))])
        t = (p1 - p0) / np.linalg.norm(p1 - p0)
        planes.append(((x0, p0[1], 0.88), (-t[1], t[0], 0.0), (x0 - 0.001, x1 + 0.001, -0.93, -0.84, 0.80, 0.95)))
    import prep_reference as pr
    r = pr.bisect_planes(planes, grow=0.01)
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    x, y, z = C.T
    # up to just short of the windscreen base (glass base y = -0.720 + 0.27 x^2, measured), not the dash behind it
    dead = (np.abs(x) < 0.60) & (y > bonnet_edge_y(x)) & (y < -0.720 + 0.27 * x * x - 0.004) & (z > 0.80) & (z < 0.96)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in np.where(dead)[0]], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    return {"cut_edges": r["cut_edges"], "faces_removed": int(dead.sum())}


def arch_front_edge():
    """Nik: a bump in the front arch line where it meets the bumper. bumper_ribs (which takes the bumper back to its
    own heights below the shut line) also pulled the arch lip just above the bumper down with it, so between z 0.50
    and 0.60 the lip's front edge sat up to 3.2 cm behind the photo-traced arch (body_geom.arch_poly, which it matched
    before). Per 1 cm row the lip and the wing just in front of it are slid forward (y) onto the traced edge; full
    shift at the lip, fading to nothing 12 cm forward; it fades in over the bumper's top corner (z 0.485-0.515, a
    sideways move only, the ribs stay level) and out at the arch top."""
    import body_geom as g
    o = bpy.data.objects["REF_BODY"]; me = o.data
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    zr = np.arange(0.480, 0.6551, 0.005)
    co = coords(me)
    out, moved = {}, []
    for s in (1, -1):
        cur, dy = [], []
        for z in zr:
            e = None
            for y in np.arange(-1.17, -1.75, -0.002):
                h = bvh.ray_cast(Vector((1.5 * s, y, z)), Vector((-s, 0, 0)), 3.0)
                if h[0] is not None and abs(h[0].x) > 0.62:
                    e = y; break
            ph = g.arch_edge_y("front", z, "front")
            cur.append(e if e is not None else np.nan)
            dy.append(min(0.0, ph - e) if (e is not None and ph is not None) else 0.0)
        cur, dy = np.array(cur), np.array(dy)
        dy *= smoothstep(0.485, 0.515, zr) * (1 - smoothstep(0.62, 0.645, zr))   # into the bumper's top corner (y only: ribs stay level)
        cur = np.where(np.isfinite(cur), cur, np.nanmean(cur))
        x, y, z = co.T
        cand = np.where((s * x > 0.55) & (z > zr[0]) & (z < zr[-1]) & (y < -1.20) & (y > -1.75))[0]
        E = np.interp(z[cand], zr, cur); D = np.interp(z[cand], zr, dy)
        w = smoothstep(E - 0.12, E - 0.005, y[cand])                       # 1 at the lip, 0 12 cm forward
        w = w * (1 - smoothstep(E + 0.02, E + 0.06, y[cand]))               # lip curl moves too, not the well beyond
        co[cand, 1] += D * w
        moved.append(cand[np.abs(D * w) > 1e-6])
        out["L" if s > 0 else "R"] = {"max_shift_mm": round(float(-dy.min() * 1000), 1), "verts": int(len(moved[-1]))}
    me.vertices.foreach_set("co", co.ravel()); me.update()
    out["normals"] = refresh_normals(np.concatenate(moved))
    return out


ARCH_LINE = (0.6966, 0.0595, -1.1036)   # z = a + b (y - y0): wing line measured on Nik's grey side picture
                                        # (lower edge of the light band, 21 columns, straight) - 2026-10-19   # z = a + b (y - y0): straight flare-top line, side photo cS back-projected


def front_arch_line():
    """Item 17 (Nik): above the front arch the step from the flare face up to the wing has two edges. Its LOWER edge
    (where the light changes in the photos) is straight on the real car; ours bowed up over the wheel (the arch morph
    lifted it ~2.6 cm mid-arch). Its TOP edge, the flare line, stays arched over the wheel (Nik, 2026-10-19). Lower
    edge measured in cS (5 points along it, back-projected): z 0.627 at y -1.57 to 0.707 at y -0.70, straight within
    the +-7 mm picking error; the model's ends already sit on it. Per 1 cm slice the outer skin is remapped in z: arch
    lip fixed, lower edge onto the straight line (flare face below squeezed), top edge of the step and everything above
    it unchanged (step face stretched between them)."""
    o = bpy.data.objects["REF_BODY"]; me = o.data
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    a, b, y0 = ARCH_LINE
    zs = np.arange(0.56, 0.86, 0.002)
    ys = np.arange(-1.56, -0.7995, 0.01)
    co = coords(me)
    out, moved = {}, []
    for s in (1, -1):
        X = np.array([[(bvh.ray_cast(Vector((s * 1.5, y, z)), Vector((-s, 0, 0)), 2.0)[0] or Vector((np.nan, 0, 0))).x * s
                       for z in zs] for y in ys])
        ze, zlo = np.full(len(ys), np.nan), np.full(len(ys), np.nan)
        for j in range(len(ys)):
            x = X[j]
            for i in range(len(zs) - 2):
                if zs[i] > 0.60 and zs[i] < 0.74 and np.isfinite(x[i]) and x[i] > 0.70 and x[i + 2] - x[i] < -0.004:
                    ze[j] = zs[i]; break                       # lower edge of the step
            if np.isfinite(ze[j]):
                k = np.searchsorted(zs, ze[j])
                while k > 0 and np.isfinite(X[j, k - 1]) and X[j, k - 1] > 0.70 and zs[k - 1] > ze[j] - 0.06:
                    k -= 1
                zlo[j] = zs[k]                                 # arch lip edge (or 6 cm down outside the arch)
        ok = np.isfinite(ze)
        ze = np.interp(ys, ys[ok], ze[ok]); zlo = np.interp(ys, ys[ok], zlo[ok])
        ze = np.convolve(np.pad(ze, 2, mode="edge"), np.ones(5) / 5, "valid")
        w = smoothstep(-1.56, -1.48, ys) * (1 - smoothstep(-0.86, -0.80, ys))
        zt = ze + w * ((a + b * (ys - y0)) - ze)
        zt = np.maximum(zt, zlo + 0.008)
        # top edge of the step: where the drop from the lower edge has levelled off (x falls < 1.5 mm per 4 mm)
        zu = np.full(len(ys), np.nan)
        for j in range(len(ys)):
            k = np.searchsorted(zs, ze[j]) + 2
            while k < len(zs) - 2 and np.isfinite(X[j, k]) and X[j, k + 2] - X[j, k] < -0.0015 and zs[k] < ze[j] + 0.06:
                k += 1
            zu[j] = zs[k]
        zu = np.convolve(np.pad(zu, 2, mode="edge"), np.ones(5) / 5, "valid")
        zup = np.maximum(zu, zt + 0.008)
        x, y, z = co.T
        cand = np.where((s * x > 0.6) & (y > ys[0]) & (y < ys[-1]) & (z > 0.56) & (z < 0.84))[0]
        Zlo, Ze, Zt, Zup = (np.interp(y[cand], ys, v) for v in (zlo, ze, zt, zup))
        # outer skin only: within 12 mm of the outermost surface at that (y, z)
        jj = np.clip(np.round((y[cand] - ys[0]) / 0.01).astype(int), 0, len(ys) - 1)
        ii = np.clip(np.round((z[cand] - zs[0]) / 0.002).astype(int), 0, len(zs) - 1)
        skin = X[jj, ii]
        sel = np.isfinite(skin) & (s * x[cand] > skin - 0.012) & (z[cand] > Zlo) & (z[cand] < Zup)
        c, zc = cand[sel], z[cand][sel]
        Zlo, Ze, Zt, Zup = Zlo[sel], Ze[sel], Zt[sel], Zup[sel]
        new = np.where(zc < Ze, Zlo + (zc - Zlo) * (Zt - Zlo) / (Ze - Zlo),
                       Zt + (zc - Ze) * (Zup - Zt) / (Zup - Ze))
        co[c, 2] = new
        moved.append(c)
        mid = np.argmin(abs(ys + 1.16))
        out["L" if s > 0 else "R"] = {"moved": len(c), "step_mid_from_to": (round(float(ze[mid]), 3), round(float(zt[mid]), 3)),
                                      "top_edge_mid": round(float(zu[mid]), 3),
                                      "max_shift_mm": round(float(np.abs(new - zc).max() * 1000), 1)}
    me.vertices.foreach_set("co", co.ravel()); me.update()
    out["normals"] = refresh_normals(np.concatenate(moved))
    return out


def remove_bumps():
    out = {}
    # old fuel cap behind the right rear arch (protrudes ~11 mm); ring kept on the flat panel between the arch lip
    # (rolls in below z ~0.59) and the swage line (starts at z ~0.69)
    vid, mx = patch("side_R", 1.425, 0.650, 0.040, 0.033, 0.008, 0.035, (1, 1), (0.006, 0.025),
                    ring_ok=lambda a, b: (b > 0.598) & (b < 0.695))
    out["old_flap"] = {"moved": len(vid), "max_mm": round(mx * 1000, 1), "normals": refresh_normals(vid)}
    # round fitting on the B/C-pillar (protrudes ~15 mm); ring kept behind the door's rear shut line (y 0.455)
    vid, mx = patch("side_R", 0.510, 1.018, 0.028, 0.028, 0.006, 0.040, (1, 1), (0.006, 0.025),
                    ring_ok=lambda a, b: a > 0.468)
    out["pillar_fitting"] = {"moved": len(vid), "max_mm": round(mx * 1000, 1), "normals": refresh_normals(vid)}
    return out


def bumper_ribs():
    """Item 9: fit_reference.arch_morph_smooth lifted the front bumper's rear end by up to 24 mm (fading out ~15 cm
    forward), bending its ribs upwards at the arch. Put back the bumper's own heights (z from nova_ref_split.blend -
    y_shift_arch moves y only, so its z is the pre-morph z) below the bumper top, blending to the morphed arch over
    z 0.56-0.64; the morph's fore-aft shift stays so the bumper still meets the moved arch."""
    with bpy.data.libraries.load(SPLIT, link=False) as (src, dst):
        dst.meshes = ["REF_BODY"]
    sm = dst.meshes[0]
    me = bpy.data.objects["REF_BODY"].data
    co = coords(me)
    s = np.empty(len(sm.vertices) * 3); sm.vertices.foreach_get("co", s); s = s.reshape(-1, 3)
    bpy.data.meshes.remove(sm)
    assert len(s) == len(co) and np.abs(s[:, 0] - co[:, 0]).max() < 1e-6     # same vertices (x never moved)
    dz = co[:, 2] - s[:, 2]
    y, z = co[:, 1], co[:, 2]
    r = smoothstep(-1.36, -1.40, y) * (1 - smoothstep(0.56, 0.64, z))
    # rear bumper too (Nik 2026-10-19: 'this bend in the bumper shouldn't be there' - the rear arch move pushed its
    # front end up to 26 mm up, fading out within 15 cm, and crumpled the ribs)
    r = np.maximum(r, smoothstep(1.36, 1.40, y) * (1 - smoothstep(0.585, 0.64, z)))
    m = np.where((r > 0) & (np.abs(dz) > 1e-7))[0]
    co[m, 2] -= r[m] * dz[m]
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return {"moved": len(m), "max_restored_mm": round(float(np.abs(r[m] * dz[m]).max() * 1000), 1),
            "normals": refresh_normals(m)}


def flatten_lettering():
    """Item 5: the model's raised GTE door lettering (both sides, y -0.65..-0.39, z 0.418..0.49) and the mirrored rear
    badge (x 0.36..0.54, z 0.76..0.80 on the black panel) flattened into their panels; details_ref.py adds new ones."""
    out = {}
    for view in ("side_L", "side_R"):
        # old letters' base edge reaches z 0.418; the door's own line at z ~0.397 and the front shut line (y -0.678)
        # stay out of the fitting ring
        vid, mx = patch(view, -0.52, 0.456, 0.135, 0.042, 0.008, 0.030, (1, 1), (0.006, 0.012),
                        ring_ok=lambda a, b: (a > -0.668) & (b > 0.401))
        out["door_" + view[-1]] = {"moved": len(vid), "max_mm": round(mx * 1000, 1), "normals": refresh_normals(vid)}
    vid, mx = patch("rear", 0.45, 0.78, 0.095, 0.025, 0.006, 0.025, (1, 1), (0.006, 0.012),
                    ring_ok=lambda a, b: (a > 0.33) & (a < 0.56))       # off the handle strip and the tail lamp
    out["rear_badge"] = {"moved": len(vid), "max_mm": round(mx * 1000, 1), "normals": refresh_normals(vid)}
    return out


def mirror_interior():
    """Item 6: the model's cabin front is left-hand drive (instrument recess, column boss and an offset centre panel
    on the car's left, the passenger-side panel on the right). Every cabin face in the dash / footwell zone (inside the
    side skin and under the roof, y -0.80..-0.28, |x| < 0.60, z 0.25..1.02) is replaced by its mirror image in x, so the
    driver's side is on the right (UK); symmetric parts land where they were. Custom normals mirrored with them."""
    import prep_reference as pr
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    x, y, z = C.T
    S, su, sv = pr.skin_side(); sk = S[pr.idx(sv, z), pr.idx(su, y)]
    T, tu, tv = pr.scan("top"); tz = T[pr.idx(tv, y), pr.idx(tu, x)]
    inside = np.isfinite(sk) & (np.abs(x) < sk - 0.035) & np.isfinite(tz) & (z < tz - 0.035) & (z > 0.25)
    R = np.where(inside & (y > -0.80) & (y < -0.28) & (np.abs(x) < 0.60) & (z < 1.02))[0]
    nl = len(me.loops)
    L = np.empty(nl * 3, np.float32); me.corner_normals.foreach_get("vector", L); L = L.reshape(-1, 3)
    ls = np.empty(n, np.int64); me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(n, np.int64); me.polygons.foreach_get("loop_total", lt)
    flip = np.array([-1.0, 1.0, 1.0], np.float32)
    new_ln = [(L[ls[f]:ls[f] + lt[f]] * flip)[::-1] for f in R]     # new face loops run in reverse order
    bm = bmesh.new(); bm.from_mesh(me)
    bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    old = [bm.faces[int(f)] for f in R]
    vmap = {}
    for F in old:
        vs = []
        for v in reversed(F.verts):
            nv = vmap.get(v.index)
            if nv is None:
                nv = vmap[v.index] = bm.verts.new((-v.co.x, v.co.y, v.co.z))
            vs.append(nv)
        nf = bm.faces.new(vs); nf.material_index = F.material_index; nf.smooth = F.smooth
    bmesh.ops.delete(bm, geom=old, context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    # the new faces are the last len(R) polygons, in the same order: put their mirrored corner normals back
    n2 = len(me.polygons); nl2 = len(me.loops)
    L2 = np.empty(nl2 * 3, np.float32); me.corner_normals.foreach_get("vector", L2); L2 = L2.reshape(-1, 3)
    ls2 = np.empty(n2, np.int64); me.polygons.foreach_get("loop_start", ls2)
    first = n2 - len(R)
    for i, ln in enumerate(new_ln):
        a0 = ls2[first + i]
        L2[a0:a0 + len(ln)] = ln
    me.normals_split_custom_set(L2)
    return {"faces_mirrored": len(R), "verts_new": len(vmap)}


def mirrors_wider():
    """Mirror heads (outboard of |x| 0.715) scaled outward about their root to 1725 mm across."""
    me = bpy.data.objects["REF_BODY"].data
    co = coords(me)
    ax = np.abs(co[:, 0])
    box = (co[:, 1] > -0.60) & (co[:, 1] < -0.36) & (co[:, 2] > 0.82) & (co[:, 2] < 1.0) & (ax > 0.705)
    x0, x1 = 0.715, ax[box].max()
    k = (MIRROR_HALF - x0) / (x1 - x0)
    w = smoothstep(0.705, 0.725, ax[box])
    new = ax[box] + w * (x0 + (ax[box] - x0) * k - ax[box])
    co[box, 0] = np.sign(co[box, 0]) * new
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return {"verts": int(box.sum()), "k": round(float(k), 4), "across_mm": round(float(2 * np.abs(co[:, 0]).max() * 1000), 1)}


# ------------------------------------------------------------------ new detail parts (objects DET_* in REF)
def material(name, base, preset, shader="ksPerPixelMultiMap", rough=0.3):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*base, 1)
    m["ac_shader"] = shader; m["ac_preset"] = preset
    return m


def new_object(name, bm, mats):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.data.collections["REF"].objects.link(o)
    return o


def ring_strip(bm, A, B, mat, expect, smooth=True):
    """Quads between point rings A and B (same count, closed); flipped so the first face normal agrees with
    expect(centre)."""
    n = len(A)
    fs = [bm.faces.new((A[k], A[(k + 1) % n], B[(k + 1) % n], B[k])) for k in range(n)]
    f0 = max(fs, key=lambda f: f.calc_area()); f0.normal_update()
    if f0.normal.dot(expect(f0.calc_center_median())) < 0:
        bmesh.ops.reverse_faces(bm, faces=fs)
    for f in fs:
        f.material_index = mat; f.smooth = smooth
    return fs


def fan(bm, A, c, mat, expect):
    n = len(A)
    fs = [bm.faces.new((A[k], A[(k + 1) % n], c)) for k in range(n)]
    fs[0].normal_update()
    if fs[0].normal.dot(expect(fs[0].calc_center_median())) < 0:
        bmesh.ops.reverse_faces(bm, faces=fs)
    for f in fs:
        f.material_index = mat; f.smooth = False
    return fs


def sunroof(bvh):
    """Glass x +-0.345, y -0.13..0.30, corner radius 0.05, 16 mm black seal round it, laid on the roof (glass
    1.2 mm, seal 1.5 mm proud) - the opaque dark glass reads as the closed tilt/slide roof with its blind."""
    hx, hy, r, yc, seal = 0.345, 0.215, 0.05, 0.085, 0.016
    up = Vector((0, 0, 1))

    def outline(d):
        rc = max(r + d, 0.0); cx, cy = hx + d - rc, hy + d - rc
        pts = []
        for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
            ccx, ccy = sx * cx, sy * cy
            for k in range(8):
                t = math.radians(a0 + 90 * k / 8)
                pts.append((ccx + rc * math.cos(t), ccy + rc * math.sin(t)))
            # straight side to the next corner
            nxt = {0: (-cx, hy + d), 90: (-(hx + d), -cy), 180: (cx, -(hy + d)), 270: (hx + d, cy)}[a0]
            start = (ccx + rc * math.cos(math.radians(a0 + 90)), ccy + rc * math.sin(math.radians(a0 + 90)))
            ns = 12 if a0 in (0, 180) else 8
            for k in range(ns):
                pts.append((start[0] + (nxt[0] - start[0]) * k / ns, start[1] + (nxt[1] - start[1]) * k / ns))
        return pts

    def drop(x, y, off):
        hit = bvh.ray_cast(Vector((x, y + yc, 2.0)), Vector((0, 0, -1)), 3.0)
        return hit[0] + hit[1] * off

    bm = bmesh.new()
    # rings from the seal's outer edge in to the centre line (d = -hy: the outline collapses to y = 0); every ring
    # has the same point layout, so strips of quads join them and follow the roof crown
    offs = [(seal, 0.0008, 0), (seal * 0.5, 0.0015, 0), (0.0, 0.0012, 1)] + \
           [(-d, 0.0012, 1) for d in (0.01, 0.04, 0.08, 0.12, 0.16, 0.20, hy)]
    rings = [[bm.verts.new(drop(x, y, off)) for (x, y) in outline(d)] for (d, off, _) in offs]
    for i in range(len(rings) - 1):
        ring_strip(bm, rings[i], rings[i + 1], offs[i][2], lambda c: up)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    glass = material("glass_sunroof_dark", (0.02, 0.025, 0.03), "glass", rough=0.05)
    o = new_object("DET_SUNROOF", bm, [bpy.data.materials["rubber_black"], glass])
    return {"verts": len(o.data.vertices), "faces": len(o.data.polygons)}


def fuel_flap(bvh):
    """Delete the body skin over a 60.5 mm disc at the photo position, then a separate part: paint rim laid on the
    skin out to 92 mm (covers the cut edge, 0.3-0.4 mm proud), recess wall 8 mm deep, black cap 111 mm across with a
    chrome lock in the middle."""
    n0 = FLAP_N
    hit = bvh.find_nearest(FLAP_C); c0, n0 = hit[0], hit[1].normalized()
    if n0.x > 0:
        n0 = -n0
    t2 = (Vector((0, 0, 1)) - n0 * n0.z).normalized(); t1 = t2.cross(n0)
    N = 48

    def surf(r, k, depth):
        th = 2 * math.pi * k / N
        p = c0 + (t1 * math.cos(th) + t2 * math.sin(th)) * r
        q, nn = bvh.find_nearest(p)[:2]
        if nn.dot(n0) < 0:
            nn = -nn
        return q + nn * depth if depth > 0 else q + n0 * depth

    # cut the body skin
    o = bpy.data.objects["REF_BODY"]; me = o.data
    co = coords(me)
    d = co - np.array(c0)
    dn = d @ np.array(n0)
    rt = np.linalg.norm(d - np.outer(dn, np.array(n0)), axis=1)
    inside = (rt < 0.0605) & (np.abs(dn) < 0.012)
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    dead = {f for i in np.where(inside)[0] for f in bm.verts[int(i)].link_faces}
    nd = len(dead)
    bmesh.ops.delete(bm, geom=list(dead), context="FACES")
    bm.to_mesh(me); bm.free(); me.update()

    bm = bmesh.new()
    R = lambda r, dep: [bm.verts.new(surf(r, k, dep)) for k in range(N)]
    rim = [R(0.092, 0.0003), R(0.075, 0.0004), R(0.0625, 0.0004), R(0.0600, -0.0015), R(0.0585, -0.0080)]
    out_n = lambda c: n0
    for i in range(3):
        ring_strip(bm, rim[i], rim[i + 1], 0, out_n)
    ring_strip(bm, rim[3], rim[4], 0, lambda c: (c0 - c) - n0 * (c0 - c).dot(n0), smooth=False)   # wall faces the axis
    fan(bm, rim[4], bm.verts.new(c0 - n0 * 0.0080), 1, out_n)
    cap = [R(0.0555, -0.0079), R(0.0555, -0.0035), R(0.0530, -0.0025), R(0.0100, -0.0020), R(0.0075, -0.0020),
           R(0.0075, -0.0010)]
    radial = lambda c: (c - c0) - n0 * (c - c0).dot(n0)
    ring_strip(bm, cap[0], cap[1], 1, radial, smooth=False)
    ring_strip(bm, cap[1], cap[2], 1, out_n, smooth=False)
    ring_strip(bm, cap[2], cap[3], 1, out_n, smooth=False)
    ring_strip(bm, cap[3], cap[4], 1, out_n, smooth=False)
    ring_strip(bm, cap[4], cap[5], 2, radial, smooth=False)
    fan(bm, cap[5], bm.verts.new(c0 - n0 * 0.0010), 2, out_n)
    obj = new_object("DET_FUEL", bm, [bpy.data.materials["paint_gunmetal"], bpy.data.materials["trim_black"],
                                      bpy.data.materials["chrome"]])
    return {"body_faces_cut": nd, "centre": tuple(round(v, 4) for v in c0), "verts": len(obj.data.vertices)}


def main():
    res = {"bumper_ribs": bumper_ribs(), "arch_front": arch_front_edge(), "arch_line": front_arch_line(), "bonnet_line": bonnet_line(),
           "bonnet_dips": bonnet_dips(), "bumps": remove_bumps(),
           "mirrors": mirrors_wider(), "lettering": flatten_lettering(), "interior": mirror_interior()}
    o = bpy.data.objects["REF_BODY"]
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    res["fuel_flap"] = fuel_flap(bvh)
    res["sunroof"] = sunroof(bvh)
    return res


if __name__ == "__main__":
    print("==", main())
