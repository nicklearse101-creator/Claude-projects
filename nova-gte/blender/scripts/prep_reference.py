"""Glass + materials for the reference body (REF_BODY in export/ref/nova_ref.blend), zones from docs/SHELL_MAP.md.

Glass: door, vent and quarter panes (both sides) and the tailgate pane are built over the open apertures measured
in the depth scans (export/ref/scan/*.npz): outline per grid column grown 12 mm under the frame, surface fitted to the
frame around the opening (least squares) and set 10 mm inside it. The striated windscreen faces are deleted and
replaced by a smooth pane fitted to them.
Materials: per face from position + facing, using the measured map (car frame: x+ = car's left, y- = front, z up).
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

SCAN = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\scan"
TEX = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\tex"
GROW, INSET = 0.012, 0.010
# bumper pinstripes (MODEL_TODO 10; moved 2026-10-19, Nik: wrong place): red lines IN the bumpers' rib grooves, the
# band of fine ribs on the upright face below the rounded top (photos: silver GTE 15643768649, E19 GTE front/rear).
# Groove heights traced on the model at 0.5 mm (front face; rear all round). The front ribs rise as they wrap round
# the corner to the arch (+8.5 mm at y -1.50): FRONT_RISE. Lines 3 mm wide.
STRIPES = {"front": (0.476,), "rear": (0.4655, 0.4965, 0.509, 0.522)}   # front: grey pictures show one red line, in the top rib groove (ribs 0.418/0.4325/0.4525/0.476), 2026-10-20
STRIPE_ZONE = {"front": (0.405, 0.490), "rear": (0.455, 0.535)}       # faces carrying the stripe texture
FRONT_RISE = ((-1.80, -1.74, -1.70, -1.65, -1.60, -1.55, -1.50), (0, 0.0015, 0.0025, 0.0035, 0.005, 0.0065, 0.0085))
STRIPE_Z0, STRIPE_H, STRIPE_W = 0.38, 0.18, 0.003                    # texture v = (z - rise - Z0) / H
STRIPE_RED = (0.60, 0.04, 0.04)


# front indicator (Nik: line it up with the model's indicator line on the wing): the lens wraps from the headlamp
# edge (x +-0.624) over the diagonal corner facet onto the side face of the lamp unit and ends at the model's
# vertical groove on the wing, y -1.5815 (10 mm deep, side scan at 0.5 mm); bottom/top edges z 0.522 / 0.6765
IND_X, IND_Z = 0.624, (0.522, 0.6765)
BPIL_TOP = 1.296                       # roof gutter line above the B-pillar (side profile: frame band ends z ~1.298)
IND_LINE = ((0.535, 0.665), (-1.5815, -1.5815))


def ind_line(z):
    (z0, z1), (y0, y1) = IND_LINE
    return y0 + (y1 - y0) * (z - z0) / (z1 - z0)


def stripe_rise(y):
    return np.where(y < 0, np.interp(y, *FRONT_RISE), 0.0)


# ------------------------------------------------------------------ scans
def scan(view):
    z = np.load(os.path.join(SCAN, view + ".npz"))
    return z["depth"].astype(np.float64), z["u"], z["v"]


def idx(a, x):
    return np.clip(np.round((x - a[0]) / (a[1] - a[0])).astype(int), 0, len(a) - 1)


def dilate(m, n):
    out = m.copy()
    for _ in range(n):
        o = out.copy()
        o[1:] |= out[:-1]; o[:-1] |= out[1:]; o[:, 1:] |= out[:, :-1]; o[:, :-1] |= out[:, 1:]
        out = o
    return out


def enclosed_miss(dep):
    """Missed cells NOT connected to the scan border (sky round the car is not a window opening)."""
    miss = ~np.isfinite(dep)
    outside = np.zeros_like(miss)
    stack = [(j, i) for j in range(miss.shape[0]) for i in (0, miss.shape[1] - 1) if miss[j, i]]
    stack += [(j, i) for i in range(miss.shape[1]) for j in (0, miss.shape[0] - 1) if miss[j, i]]
    while stack:
        j, i = stack.pop()
        if outside[j, i] or not miss[j, i]:
            continue
        outside[j, i] = True
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            jj, ii = j + dj, i + di
            if 0 <= jj < miss.shape[0] and 0 <= ii < miss.shape[1] and miss[jj, ii] and not outside[jj, ii]:
                stack.append((jj, ii))
    return miss & ~outside


def largest_region(m):
    """The largest 4-connected region of a boolean grid."""
    lab = np.full(m.shape, -1, np.int64)
    sizes = []
    for j0, i0 in zip(*np.where(m)):
        if lab[j0, i0] >= 0:
            continue
        k = len(sizes); lab[j0, i0] = k; stack = [(j0, i0)]; n = 0
        while stack:
            j, i = stack.pop(); n += 1
            for jj, ii in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
                if 0 <= jj < m.shape[0] and 0 <= ii < m.shape[1] and m[jj, ii] and lab[jj, ii] < 0:
                    lab[jj, ii] = k; stack.append((jj, ii))
        sizes.append(n)
    return lab == int(np.argmax(sizes)) if sizes else m


def aperture(open_mask, u, v, ub, vb):
    """Mask of the open cells inside the bounding box (the aperture)."""
    m = open_mask.copy()
    m[:, (u < ub[0]) | (u > ub[1])] = False
    m[(v < vb[0]) | (v > vb[1]), :] = False
    return m


def column_outline(m, u, v):
    """Per grid column: (u, vmin, vmax) of the longest run of open cells."""
    cols = []
    for i in range(m.shape[1]):
        rows = np.where(m[:, i])[0]
        if len(rows) < 3:
            continue
        splits = np.where(np.diff(rows) > 1)[0]
        runs = np.split(rows, splits + 1)
        r = max(runs, key=len)
        cols.append((u[i], v[r[0]], v[r[-1]]))
    return cols


def fit_frame(dep, m, u, v, terms):
    """Least-squares surface depth = sum c_k * term_k(u, v) over the ring of skin cells round the aperture."""
    ring = dilate(m, 8) & ~dilate(m, 3) & np.isfinite(dep)
    jj, ii = np.where(ring)
    U, V, Dp = u[ii], v[jj], dep[jj, ii]
    A = np.stack([t(U, V) for t in terms], 1)
    c, *_ = np.linalg.lstsq(A, Dp, rcond=None)
    res = Dp - A @ c
    keep = np.abs(res) < 2.5 * res.std() + 1e-4                       # drop seal/trim outliers, refit
    c, *_ = np.linalg.lstsq(A[keep], Dp[keep], rcond=None)
    return lambda uu, vv: sum(ck * t(uu, vv) for ck, t in zip(c, terms)), float(np.abs(res[keep]).mean())


def pane(name, cols, surf, to3, n_v=10, mats=None, mirror_x=False):
    """Grid mesh over the column outline (grown by GROW), vertices on surf (depth along the view axis)."""
    du = cols[1][0] - cols[0][0] if len(cols) > 1 else 0.01
    cols = [(cols[0][0] - GROW, cols[0][1] + 0.01, cols[0][2] - 0.01)] + cols + [(cols[-1][0] + GROW, cols[-1][1] + 0.01, cols[-1][2] - 0.01)]
    step = max(1, int(round(0.02 / max(du, 1e-4))))
    cols = cols[::step] + ([cols[-1]] if (len(cols) - 1) % step else [])
    bm = bmesh.new()
    rows = []
    for uu, v0, v1 in cols:
        v0, v1 = v0 - GROW, v1 + GROW
        rows.append([bm.verts.new(to3(uu, vv, surf(uu, vv))) for vv in np.linspace(v0, v1, n_v)])
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(n_v - 1):
            bm.faces.new((r0[k], r1[k], r1[k + 1], r0[k + 1]))
    if mirror_x:
        for vtx in bm.verts:
            vtx.co.x = -vtx.co.x
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    o = bpy.data.objects.new(name, me)
    bpy.data.collections["REF"].objects.link(o)
    o.data.materials.append(bpy.data.materials["glass_tint"])
    for p in o.data.polygons:
        p.use_smooth = True
    return o


SIDE_BOXES = (("DOOR", (-0.225, 0.42), (0.84, 1.25)), ("VENT", (-0.70, -0.228), (0.84, 1.20)),
              ("QUARTER", (0.60, 1.40), (0.87, 1.24)))


QTAIL = (1.36, 0.75, 0.93, 1.215)     # fin line y = 1.36 - 0.75 (z - 0.93), window bottom z 0.93, top z 1.215 (scan)


def quarter_tail(dep, u, v):
    """Cells of the solid tail of the quarter window: in the glass plane (not open), ahead of the fin line."""
    y0, k, zb, zt = QTAIL
    UU, VV = np.meshgrid(u, v)
    return (VV > zb) & (VV < zt) & (UU > 1.0) & (UU < y0 - k * (VV - zb) - 0.004) & np.isfinite(dep) & (dep < 0.665)


def cut_quarter_tail(surf):
    """Delete REF_BODY's solid quarter-window tail faces and the trim just behind them, both sides. The mesh is first
    cut along the tail's outline (bottom, top, fin line), so no saw-tooth scraps are left on its edges."""
    y0, k, zb, zt = QTAIL
    planes = []
    for sx in (1, -1):
        box = (0.50, 0.80) if sx > 0 else (-0.80, -0.50)
        b = (*box, 0.98, 1.42, 0.90, 1.24)
        planes += [((0.7 * sx, 0, zb + 0.003), (0, 0, 1), b), ((0.7 * sx, 0, zt - 0.003), (0, 0, 1), b),
                   ((0.7 * sx, y0 - 0.006, zb), (0, 1, k), b)]
    bisect_planes(planes, grow=0.01)
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    N = np.empty(n * 3); me.polygons.foreach_get("normal", N); N = N.reshape(-1, 3)
    y0, k, zb, zt = QTAIL
    x, y, z = C.T; ax = np.abs(x)
    # every face of the panel (its rim faces point any way) and the rough template trim close behind it (Nik: it
    # shouldn't be there), from 2 cm out to 8 cm in, inside the opening by 3 mm / 6 mm short of the fin edge
    sel = ((z > zb + 0.003) & (z < zt - 0.003) & (y > 1.0) & (y < y0 - k * (z - zb) - 0.006)
           & (ax - surf(y, z) > -0.08) & (ax - surf(y, z) < 0.02))
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in np.where(sel)[0]], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    return int(sel.sum())


def side_apertures():
    """Side window openings in the left scan: {name: (mask, column outline, glass-plane surf, fit error)}.
    Open = the ray reaches the cabin (depth < 0.50) - the old 0.60 test also took the roof sides (drip rails at
    0.59) and the C-pillar top, so the openings ran up into the roof band and over the pillar; below that top
    edge, cells to 0.60 count too (seats and trims close behind the glass)."""
    dep, u, v = scan("side_L")
    encl = enclosed_miss(dep)
    m50 = encl | (np.isfinite(dep) & (dep < 0.50))
    m60 = encl | (np.isfinite(dep) & (dep < 0.60))
    terms = [lambda a, b: np.ones_like(a), lambda a, b: a, lambda a, b: b, lambda a, b: b * b, lambda a, b: a * a]
    out = {}
    for name, ub, vb in SIDE_BOXES:
        m = aperture(m50, u, v, ub, vb)
        if name == "VENT":                       # behind the A-pillar line only (rays in front of the pillar pass
            UU, VV = np.meshgrid(u, v)           # over the bonnet and hit the far side: they read as 'deep' too)
            m &= VV < 0.86 + (UU + 0.66) * (0.33 / 0.42) - 0.005
        m = largest_region(m)                    # stray deep cells (over the C-pillar top) are not the opening
        top = np.full(len(u), -1)
        for i in range(len(u)):
            r = np.where(m[:, i])[0]
            if len(r):
                top[i] = r.max()
        below = np.arange(len(v))[:, None] <= top[None, :]
        m = m | (aperture(m60, u, v, ub, vb) & below & (top[None, :] >= 0))
        if name == "QUARTER":
            # the back of the quarter window is modelled as a solid panel in the glass plane (Nik: 'supposed to be
            # glass but solid grey'); its real edge is the slanted line where the C-pillar fin stands ~1 cm proud
            m |= quarter_tail(dep, u, v)
        cols = column_outline(m, u, v)
        if name == "VENT":                       # same pane plane as the door glass (its own frame ring takes in
            surf, err = out["DOOR"][2], out["DOOR"][3]   # the mirror and the A-pillar: a twisted fit)
        else:
            surf, err = fit_frame(dep, m, u, v, terms)
        out[name] = (m, cols, surf, err)
    return out


def build_glass():
    made = {}
    # ---- side glass (left scan; the right side is the mirror image - the scans match to the mm)
    for name, (m, cols, surf, err) in side_apertures().items():
        if name == "QUARTER":
            made["QUARTER_TAIL_FACES_CUT"] = cut_quarter_tail(surf)
        for side, mx in (("L", False), ("R", True)):
            o = pane("GLASS_%s_%s" % (name, side), cols, lambda a, b: surf(a, b) - INSET,
                     lambda uu, vv, d: (d, uu, vv), mirror_x=mx)
        made[name] = {"cols": len(cols), "fit_err_mm": round(err * 1000, 2)}
    # ---- tailgate glass (rear scan, depth = y)
    dep, u, v = scan("rear")
    open_ = enclosed_miss(dep) | (np.isfinite(dep) & (dep < 1.20))
    m = aperture(open_, u, v, (-0.56, 0.56), (0.90, 1.30))
    cols = column_outline(m, u, v)
    terms = [lambda a, b: np.ones_like(a), lambda a, b: a * a, lambda a, b: b, lambda a, b: b * b]
    surf, err = fit_frame(dep, m, u, v, terms)
    pane("GLASS_TAILGATE", cols, lambda a, b: surf(a, b) - INSET, lambda uu, vv, d: (uu, d, vv))
    made["TAILGATE"] = {"cols": len(cols), "fit_err_mm": round(err * 1000, 2)}
    # ---- windscreen: delete the striated faces, replace by a smooth fitted pane
    made["WINDSCREEN"] = windscreen()
    made["WINDSCREEN"]["slivers_removed"] = ws_cleanup()
    return made


def ws_inside(x, z, grow=0.0):
    """Windscreen outline in the front view: base z 0.93 (x +-0.65), header z 1.29 (x +-0.54)."""
    t = np.clip((z - 0.93) / 0.36, 0, 1)
    half = 0.65 - 0.11 * t + grow
    return (np.abs(x) < half) & (z > 0.93 - grow) & (z < 1.29 + grow)


def windscreen():
    o = bpy.data.objects["REF_BODY"]
    me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    N = np.empty(n * 3); me.polygons.foreach_get("normal", N); N = N.reshape(-1, 3)
    dep, u, v = scan("front")
    sd = dep[idx(v, C[:, 2]), idx(u, C[:, 0])]
    sel = ws_inside(C[:, 0], C[:, 2], -0.012) & (N[:, 1] < -0.2) & np.isfinite(sd) & (np.abs(C[:, 1] - sd) < 0.02)
    P = C[sel]
    # smooth stand-in for the striated surface: local average of the old surface (follows its real curvature and
    # the wrap at the corners - a single global fit ran off forward at the corners), outline from where it was
    from mathutils.kdtree import KDTree
    kd = KDTree(len(P))
    for i, p_ in enumerate(P):
        kd.insert((p_[0], p_[2], 0.0), i)
    kd.balance()

    def surf(x, z):
        f = kd.find_range((x, z, 0.0), 0.035) or kd.find_n((x, z, 0.0), 12)
        w = np.array([math.exp(-0.5 * (d / 0.02) ** 2) + 1e-9 for _, _, d in f])
        return float((w * P[[i for _, i, _ in f], 1]).sum() / w.sum())
    A = np.stack([np.ones(len(P)), P[:, 0] ** 2, P[:, 2], P[:, 2] ** 2, P[:, 0] ** 2 * P[:, 2]], 1)
    c, *_ = np.linalg.lstsq(A, P[:, 1], rcond=None)
    fit = lambda x, z: c[0] + c[1] * x * x + c[2] * z + c[3] * z * z + c[4] * x * x * z
    dy = C[:, 1] - fit(C[:, 0], C[:, 2])
    sel |= ws_inside(C[:, 0], C[:, 2], -0.012) & (dy > -0.02) & (dy < 0.03) & (np.abs(N[:, 1]) > 0.2)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(sel)[0]], context="FACES")
    bm.to_mesh(me); bm.free()
    cols = []
    for x in np.arange(-0.70, 0.7001, 0.02):
        near = P[np.abs(P[:, 0] - x) < 0.012]
        if len(near) > 20:
            cols.append((x, near[:, 2].min() + GROW - 0.004, near[:, 2].max() - GROW + 0.004))
    pane("GLASS_WINDSCREEN", cols, surf, lambda uu, vv, d: (uu, d, vv), n_v=14)
    return {"faces_replaced": int(sel.sum()), "striation_rms_mm": round(float(np.sqrt(((A @ c - P[:, 1]) ** 2).mean()) * 1000), 2)}


def ws_cleanup():
    """Remove the leftover slivers of the model's striated windscreen (everything up to 10 cm behind the new pane),
    keeping the interior mirror. (This also takes the front edge of the dash top; the interior is ignored for now.)"""
    g = bpy.data.objects["GLASS_WINDSCREEN"]
    G = np.array([v.co[:] for v in g.data.vertices])
    A = np.stack([np.ones(len(G)), G[:, 0] ** 2, G[:, 2], G[:, 2] ** 2, G[:, 0] ** 2 * G[:, 2]], 1)
    c, *_ = np.linalg.lstsq(A, G[:, 1], rcond=None)
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    N = np.empty(n * 3); me.polygons.foreach_get("normal", N); N = N.reshape(-1, 3)
    x, y, z = C[:, 0], C[:, 1], C[:, 2]
    dy = y - (c[0] + c[1] * x * x + c[2] * z + c[3] * z * z + c[4] * x * x * z)
    # glass normal from the fit: grad of (y - f(x, z))
    gn = np.stack([-(2 * c[1] * x + 2 * c[4] * x * z), np.ones_like(x), -(c[2] + 2 * c[3] * z + c[4] * x * x)], 1)
    gn /= np.linalg.norm(gn, axis=1, keepdims=True)
    cs = np.abs(np.sum(N * gn, 1))
    mirror = (np.abs(x) < 0.14) & (z > 1.13)
    sel = ws_inside(x, z, -0.005) & (z > 0.95) & (dy > -0.03) & (dy < 0.10) & ~mirror   # (interior: ignored, Nik)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(sel)[0]], context="FACES")
    # loose fragments round the interior mirror: small islands in the header region (mirror ~4500 faces stays)
    bm.faces.ensure_lookup_table()
    reg = {f for f in bm.faces if abs(f.calc_center_median().x) < 0.40 and f.calc_center_median().z > 1.0
           and -0.50 < f.calc_center_median().y < -0.15}
    seen, dead = set(), []
    for f in reg:
        if f in seen:
            continue
        stack, isl = [f], []
        seen.add(f)
        while stack:
            g_ = stack.pop(); isl.append(g_)
            for e in g_.edges:
                for h in e.link_faces:
                    if h not in seen and h in reg:
                        seen.add(h); stack.append(h)
        if len(isl) < 500:
            dead += isl
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(me); bm.free()
    return int(sel.sum()) + len(dead)


# ------------------------------------------------------------------ materials
def plate_white():
    m = bpy.data.materials.get("plate_white")
    if m is None:
        m = bpy.data.materials["plate_yellow"].copy(); m.name = "plate_white"
        b = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.85, 0.85, 0.85, 1)
    return m


def paint_stripes():
    """paint_gunmetal with a diffuse texture: the paint colour with the red lines - left half the front bumper's
    lines, right half the rear's (u < 0.5 / > 0.5); v = (z - rise - STRIPE_Z0) / STRIPE_H."""
    import json
    base = next(n for n in bpy.data.materials["paint_gunmetal"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    col = tuple(base.inputs["Base Color"].default_value)[:3]
    H = 1024
    zrow = STRIPE_Z0 + (np.arange(H) + 0.5) / H * STRIPE_H
    rgb = np.zeros((H, 16, 3))
    for half, key in ((slice(0, 8), "front"), (slice(8, 16), "rear")):
        a = np.zeros(H)
        for t in STRIPES[key]:                                  # 3 mm lines, ~0.2 mm soft edges
            a = np.maximum(a, np.clip((STRIPE_W / 2 - np.abs(zrow - t)) / 0.0002 + 0.5, 0, 1))
        rgb[:, half] = (np.array(col)[None] * (1 - a[:, None]) + np.array(STRIPE_RED)[None] * a[:, None])[:, None, :]
    os.makedirs(TEX, exist_ok=True)
    path = os.path.join(TEX, "bumper_stripes.png")
    img = bpy.data.images.get("bumper_stripes.png")
    if img is not None and tuple(img.size) != (16, H):
        bpy.data.images.remove(img); img = None
    img = img or bpy.data.images.new("bumper_stripes.png", 16, H)
    px = np.ones((H, 16, 4), np.float32); px[:, :, :3] = rgb
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path; img.file_format = "PNG"; img.save()
    img.colorspace_settings.name = "Non-Color"          # Blender preview reads the bytes raw, as AC does
    m = bpy.data.materials.get("paint_stripes")
    if m is None:
        m = bpy.data.materials["paint_gunmetal"].copy(); m.name = "paint_stripes"
    m["ac_tex"] = json.dumps({"DIFFUSE": path})
    m["stripe_bg"] = list(col)                          # lookdev tints the preview to its paint look
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    tx.image = img; tx.interpolation = "Linear"
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    return m


def body_uv(lab, stripe):
    """UV map for REF_BODY: box projection by each face's main axis (every face non-degenerate, so tangents are
    sound); the pinstripe faces: v = height (less the front ribs' rise), u along the bumper inside its half of the
    stripe texture (front 0.06-0.44, rear 0.56-0.94)."""
    me = bpy.data.objects["REF_BODY"].data
    nl, npo = len(me.loops), len(me.polygons)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    cv = np.empty(nl, np.int64); me.loops.foreach_get("vertex_index", cv)
    lt = np.empty(npo, np.int64); me.polygons.foreach_get("loop_total", lt)
    FN = np.empty(npo * 3); me.polygons.foreach_get("normal", FN); FN = FN.reshape(-1, 3)
    fl = np.repeat(np.arange(npo), lt)
    P = co[cv]; dom = np.abs(FN[fl]).argmax(1)
    u = np.where(dom == 0, P[:, 1], P[:, 0])
    v = np.where(dom == 2, P[:, 1], P[:, 2])
    s = lab[fl] == stripe
    for key in STRIPES:
        k = s & ((P[:, 1] < 0) if key == "front" else (P[:, 1] > 0))
        v[k] = (P[k, 2] - stripe_rise(P[k, 1]) - STRIPE_Z0) / STRIPE_H
        along = np.where(np.abs(FN[fl][k, 0]) > np.abs(FN[fl][k, 1]), np.abs(P[k, 1]) - 1.45, np.abs(P[k, 0]))
        u[k] = (0.06 if key == "front" else 0.56) + 0.38 * np.clip(along / 0.9, 0, 1)
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    me.uv_layers.active = uv
    uv.data.foreach_set("uv", np.stack([u, v], 1).ravel())
    return int(s.sum())


def skin_side():
    """Outer half-width of the body at (y, z) - apertures filled from their frame ring (glass plane)."""
    dep, u, v = scan("side_L")
    s = dep.copy()
    s[~np.isfinite(s) | (s < 0.60)] = np.nan
    # fill holes row by row (linear across the aperture) so the glass openings count as skin
    for j in range(s.shape[0]):
        r = s[j]; ok = np.isfinite(r)
        if ok.sum() > 2:
            first, last = np.where(ok)[0][[0, -1]]
            mid = np.arange(first, last + 1)
            r[mid] = np.interp(mid, np.where(ok)[0], r[ok])
    return s, u, v


def assign_materials():
    o = bpy.data.objects["REF_BODY"]
    me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    N = np.empty(n * 3); me.polygons.foreach_get("normal", N); N = N.reshape(-1, 3)
    x, y, z = C[:, 0], C[:, 1], C[:, 2]
    ax = np.abs(x)
    names = ["paint_gunmetal", "trim_black", "trim_grey", "int_dark_grey", "lamp_clear", "lamp_amber", "lamp_red",
             "grille_black", "plate_yellow", "plate_white", "chrome", "mirror_glass", "rubber_black", "paint_stripes"]
    plate_white()
    paint_stripes()
    K = {nm: i for i, nm in enumerate(names)}
    lab = np.zeros(n, int)

    def put(mask, nm):
        lab[mask] = K[nm]

    S, su, sv = skin_side()
    sk = S[idx(sv, z), idx(su, y)]
    T, tu, tv = scan("top")
    tz = T[idx(tv, y), idx(tu, x)]
    outer = ~np.isfinite(sk) | (ax > sk - 0.03)
    # interior: inside the side skin, under the roof, in the cabin length
    inside = np.isfinite(sk) & (ax < sk - 0.035) & np.isfinite(tz) & (z < tz - 0.035) & (y > -0.75) & (y < 1.62) & (z > 0.25)
    put(inside, "int_dark_grey")
    side = outer & (np.abs(N[:, 0]) > 0.45)
    front = (N[:, 1] < -0.45) & (y < -1.35)
    rear = (N[:, 1] > 0.45) & (y > 1.35)
    top = N[:, 2] > 0.5
    # underside + wheel wells
    put((N[:, 2] < -0.75) & (z < 0.40) & ~inside, "trim_black")      # mostly downward (not the bumpers' lower curve)
    for yc in (-1.1715, 1.1715):
        # not the skin round the arch: outward-facing faces never count (the scans predate fix_shape's wing remap)
        put((np.hypot(y - yc, z - 0.2916) < 0.40) & (ax < 0.72) & ~inside & ~outer & ~((N[:, 0] * np.sign(x) > 0.5) & (ax > 0.69)), "trim_black")
    # ---- sides
    put(side & (z < 0.288) & (y > -0.83) & (y < 0.81), "trim_grey")                             # skirts
    put(side & (y >= 0.50) & (y < 0.81) & (z < 0.288 + (y - 0.50) / 0.31 * 0.112), "trim_grey")  # kick-up
    put(side & (y < -1.48) & (z < 0.26), "trim_grey")                                           # front lip
    put(side & (y > 1.47) & (z < 0.36), "trim_grey")                                            # rear valance
    # B-pillar: black from the belt line right up to the roof gutter (Nik: it turned grey at the top)
    put(~inside & (N[:, 0] * np.sign(x) > 0.2) & (ax > 0.50) & (y > 0.415) & (y < 0.62) & (z > 0.855) & (z < BPIL_TOP),
        "trim_black")
    put(side & (y > -0.255) & (y < -0.205) & (z > 0.85) & (z < 1.25), "trim_black")             # vent bar
    put(side & (y > 0.31) & (y < 0.40) & (z > 0.745) & (z < 0.80), "trim_black")                # door handle
    put(side & (y > 0.335) & (y < 0.37) & (z > 0.685) & (z < 0.715), "chrome")                  # lock
    put(side & (y > -0.80) & (y < -0.755) & (z > 0.725) & (z < 0.755), "lamp_amber")            # repeater
    # tail lamp wrap - bands as the rear (redgte_24): red z > 0.682, amber 0.613-0.682, clear reversing lamp below
    put(side & (y > 1.60) & (y < 1.71) & (z > 0.682) & (z < 0.82), "lamp_red")
    put(side & (y > 1.60) & (y < 1.71) & (z > 0.613) & (z <= 0.682), "lamp_amber")
    put(side & (y > 1.60) & (y < 1.71) & (z > 0.565) & (z <= 0.613), "lamp_clear")
    # (window frames, windscreen rubber and tailgate seal are strips of their own: frames_ref.py)
    # mirrors: body colour, glass on the rear face
    put((N[:, 1] > 0.6) & (ax > 0.66) & (y > -0.56) & (y < -0.38) & (z > 0.86) & (z < 0.98), "mirror_glass")
    # ---- front
    put(front & (ax > 0.405) & (ax <= 0.624) & (z > 0.524) & (z < 0.674), "lamp_clear")
    # indicator: front face and its wrap round the corner up to the model's indicator line on the wing (Nik)
    put(~inside & (ax > IND_X) & (y < ind_line(z)) & (z > IND_Z[0]) & (z < IND_Z[1])
        & ((N[:, 0] * np.sign(x) > 0.2) | (N[:, 1] < -0.2)), "lamp_amber")
    # grille: every face inside the surround (slat tops/undersides too, not only the front-facing ones)
    put((y < -1.70) & (ax < 0.383) & (z > 0.534) & (z < 0.661) & ~inside, "grille_black")
    # (griffin: the real one is a white decal - the model's ragged relief stays body colour; decal still to do)
    put(front & (ax < 0.25) & (z > 0.33) & (z < 0.45), "plate_white")
    put(front & (ax > 0.25) & (ax < 0.34) & (z > 0.36) & (z < 0.40), "trim_black")             # air slots
    put(front & (x > -0.49) & (x < -0.39) & (z > 0.30) & (z < 0.38), "trim_black")             # tow-eye cover
    put(front & (z < 0.26), "trim_grey")                                                         # lower lip
    # ---- rear
    # GTE black rear panel: the tailgate plane (y < 1.725, ~5 cm ahead of the bumper face) down to the bumper top
    put(rear & (ax < 0.565) & (z > 0.548) & (z < 0.92) & (y < 1.725), "trim_black")
    put(rear & (ax < 0.31) & (z > 0.772) & (z < 0.817), "trim_grey")                           # handle strip
    put(rear & (ax < 0.25) & (z > 0.626) & (z < 0.748), "plate_yellow")
    put(rear & (ax < 0.03) & (z > 0.85) & (z < 0.90), "chrome")                                # lock / badge
    put(rear & (ax >= 0.565) & (ax < 0.69) & (z > 0.682) & (z < 0.82), "lamp_red")             # redgte_24 bands
    put(rear & (ax >= 0.565) & (ax < 0.69) & (z > 0.613) & (z <= 0.682), "lamp_amber")
    put(rear & (ax >= 0.565) & (ax < 0.69) & (z > 0.565) & (z <= 0.613), "lamp_clear")         # reversing lamp
    put(rear & (z < 0.36), "trim_grey")                                                          # valance
    put(rear & (x > -0.541) & (x < -0.474) & (z > 0.32) & (z < 0.37), "lamp_red")              # fog lamp
    put(rear & (x > 0.526) & (x < 0.569) & (z > 0.35) & (z < 0.41), "trim_black")
    put((y > 1.55) & (x > 0.48) & (x < 0.62) & (z > 0.24) & (z < 0.35) & (N[:, 1] > -0.2), "chrome")   # tailpipe
    # ---- top
    # scuttle grille + wiper spindles: every face in the box (not only upward-facing)
    put((ax < 0.48) & (y > -0.84) & (y < -0.70) & (z > 0.84) & (N[:, 2] > -0.3) & ~inside, "trim_black")
    # ---- bumper pinstripes: painted faces facing out of each bumper's rib band
    for key, (zlo, zhi) in STRIPE_ZONE.items():
        if key == "front":
            reg = (y < -1.46) & ((N[:, 1] < -0.3) | (N[:, 0] * np.sign(x) > 0.3))
        else:
            reg = (y > 1.47) & ((N[:, 1] > 0.3) | (N[:, 0] * np.sign(x) > 0.3))
        zr = z - stripe_rise(y)
        put((lab == K["paint_gunmetal"]) & reg & ~inside & (zr > zlo) & (zr < zhi), "paint_stripes")
    # write
    me.materials.clear()
    for nm in names:
        me.materials.append(bpy.data.materials[nm])
    me.polygons.foreach_set("material_index", lab.tolist())
    me.update()
    body_uv(lab, K["paint_stripes"])
    return {nm: int((lab == K[nm]).sum()) for nm in names}


def _sym(planes):
    """Mirror each (co, no, box) across x = 0 as well (box = x0, x1, y0, y1, z0, z1)."""
    out = []
    for co, no, (x0, x1, y0, y1, z0, z1) in planes:
        out.append((co, no, (x0, x1, y0, y1, z0, z1)))
        out.append(((-co[0], co[1], co[2]), (-no[0], no[1], no[2]), (-x1, -x0, y0, y1, z0, z1)))
    return out


def zone_cuts():
    """Cut planes along the colour-zone edges of assign_materials (same numbers), each limited to a box."""
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    (iz0, iz1), (iy0, iy1) = IND_LINE
    ind_no = (0.0, iz1 - iz0, -(iy1 - iy0))                      # normal of the slanted indicator line (in y-z)
    kick_no = (0.0, -0.112, 0.31)                                 # skirt kick-up line (y 0.50 -> 0.81, z +0.112)
    P = _sym([
        # front lamps / grille
        ((0.405, 0, 0), X, (0.39, 0.42, -1.86, -1.68, 0.50, 0.70)),
        ((IND_X, 0, 0), X, (0.61, 0.64, -1.86, -1.66, 0.50, 0.70)),
        ((0.5, 0, IND_Z[0]), Z, (0.40, 0.76, -1.86, -1.575, 0.505, 0.535)),
        ((0.5, 0, IND_Z[1]), Z, (0.40, 0.76, -1.86, -1.575, 0.665, 0.69)),
        ((0.7, iy0, iz0), ind_no, (0.64, 0.76, -1.595, -1.568, 0.50, 0.70)),
        ((0.383, 0, 0), X, (0.37, 0.40, -1.86, -1.68, 0.52, 0.68)),
        ((0.2, 0, 0.534), Z, (0.0, 0.39, -1.86, -1.68, 0.52, 0.55)),
        ((0.2, 0, 0.661), Z, (0.0, 0.39, -1.86, -1.68, 0.645, 0.675)),
        ((0.5, 0, 0.26), Z, (0.0, 0.80, -1.90, -1.44, 0.24, 0.28)),
        # sides
        ((0.6, 0.415, 0), Y, (0.50, 0.80, 0.40, 0.43, 0.84, 1.31)),          # B-pillar edges and top
        ((0.6, 0.62, 0), Y, (0.50, 0.80, 0.61, 0.63, 0.84, 1.31)),
        ((0.6, 0, BPIL_TOP), Z, (0.50, 0.80, 0.40, 0.64, 1.28, 1.31)),
        ((0.7, 0, 0.288), Z, (0.60, 0.80, -0.85, 0.52, 0.27, 0.31)),
        ((0.7, 0.50, 0.288), kick_no, (0.60, 0.80, 0.48, 0.83, 0.27, 0.42)),
        ((0.7, 0.31, 0), Y, (0.60, 0.80, 0.30, 0.32, 0.73, 0.81)),
        ((0.7, 0.40, 0), Y, (0.60, 0.80, 0.39, 0.41, 0.73, 0.81)),
        ((0.7, 0, 0.745), Z, (0.60, 0.80, 0.30, 0.41, 0.735, 0.755)),
        ((0.7, 0, 0.80), Z, (0.60, 0.80, 0.30, 0.41, 0.79, 0.81)),
        ((0.7, -0.80, 0), Y, (0.60, 0.80, -0.81, -0.79, 0.715, 0.765)),
        ((0.7, -0.755, 0), Y, (0.60, 0.80, -0.765, -0.745, 0.715, 0.765)),
        ((0.7, 0, 0.725), Z, (0.60, 0.80, -0.81, -0.745, 0.715, 0.735)),
        ((0.7, 0, 0.755), Z, (0.60, 0.80, -0.81, -0.745, 0.745, 0.765)),
        # rear: tail lamps (bands, tail/brake split, inner edge), black panel, handle strip, valance
        ((0.6, 0, 0.682), Z, (0.54, 0.76, 1.55, 1.80, 0.67, 0.695)),
        ((0.6, 0, 0.613), Z, (0.54, 0.76, 1.55, 1.80, 0.60, 0.625)),
        ((0.6, 0, 0.751), Z, (0.54, 0.76, 1.55, 1.80, 0.74, 0.76)),
        ((0.6, 1.60, 0), Y, (0.62, 0.78, 1.59, 1.61, 0.55, 0.83)),
        ((0.565, 0, 0), X, (0.55, 0.58, 1.55, 1.80, 0.54, 0.93)),
        ((0.3, 0, 0.548), Z, (0.0, 0.58, 1.60, 1.80, 0.535, 0.56)),
        ((0.31, 0, 0), X, (0.30, 0.32, 1.60, 1.80, 0.76, 0.83)),
        ((0.2, 0, 0.772), Z, (0.0, 0.32, 1.60, 1.80, 0.76, 0.785)),
        ((0.2, 0, 0.817), Z, (0.0, 0.32, 1.60, 1.80, 0.805, 0.83)),
        ((0.5, 0, 0.36), Z, (0.0, 0.80, 1.45, 1.90, 0.345, 0.375)),
    ])
    return P


def bisect_planes(planes, grow=0.03):
    """Cut REF_BODY along planes, each only inside its box (co, no, (x0, x1, y0, y1, z0, z1)). Nothing moves; the new
    vertices lie on the existing surface (custom normals of new corners interpolated by bmesh)."""
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    pool_mask = np.zeros(n, bool)
    for co, no, (x0, x1, y0, y1, z0, z1) in planes:
        pool_mask |= ((C[:, 0] > x0 - grow) & (C[:, 0] < x1 + grow) & (C[:, 1] > y0 - grow) & (C[:, 1] < y1 + grow)
                      & (C[:, 2] > z0 - grow) & (C[:, 2] < z1 + grow))
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    pool = {bm.faces[int(i)] for i in np.where(pool_mask)[0]}
    cuts = 0
    for co, no, (x0, x1, y0, y1, z0, z1) in planes:
        sel = []
        for f in pool:
            if not f.is_valid:
                continue
            vs = [v.co for v in f.verts]
            if (min(v.x for v in vs) < x1 and max(v.x for v in vs) > x0 and min(v.y for v in vs) < y1
                    and max(v.y for v in vs) > y0 and min(v.z for v in vs) < z1 and max(v.z for v in vs) > z0):
                sel.append(f)
        if not sel:
            continue
        geom = set(sel)
        for f in sel:
            geom.update(f.edges); geom.update(f.verts)
        r = bmesh.ops.bisect_plane(bm, geom=list(geom), dist=1e-6, plane_co=co, plane_no=Vector(no).normalized())
        cut_edges = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        cuts += len(cut_edges)
        for e in cut_edges:
            pool.update(e.link_faces)
    bm.to_mesh(me); bm.free(); me.update()
    return {"planes": len(planes), "cut_edges": cuts, "faces": len(me.polygons)}


def cut_zone_edges():
    """Clean colour edges: the mesh is cut along every zone edge (inside a small box round it), so the per-face
    zones of assign_materials end on straight lines instead of on the model's triangle edges."""
    return bisect_planes(zone_cuts())


def main():
    g = build_glass()
    c = cut_zone_edges()
    m = assign_materials()
    return {"glass": g, "cuts": c, "materials": m}


if __name__ == "__main__":
    print("==", main())
