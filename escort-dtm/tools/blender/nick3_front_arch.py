"""Rebuild the front arch flare as a clean constant-section ring.

Reproducible: reads mesh data `OLD_NICK3_front_arch_L_pre_ring` (the arch as it was before this rebuild)
and returns a new mesh.

 1. outer-lip waviness removed: x-offset of every vertex is rescaled per angle so the lip width is a constant
    X_LIP all round the wheel (profile shape kept).
 2. the stretched lower-front 'tongue' (angles below THETA_CUT) is deleted and rebuilt by sweeping the clean
    profile row forward/down: the ring centre drifts forward by SHIFT (smooth), and the flare tapers to a
    point (x-offset and radial width scale to zero) before it gets near the splitter.
Angles: theta=0 forward(-Y) at hub height, 90 = top, 180 = rearward at hub height. Wheel centre CY,CZ.
"""
import bpy, bmesh, math
from mathutils import Vector

CY, CZ = -1.218, 0.148
X_LIP = 0.926          # lip width over the wheel / rear
X_FRONT = 0.842        # lip width where the flare meets the front clip wall (clip wall x = 0.83-0.855)
TH_N0, TH_N1 = 70.0, 2.0   # lip narrows between these angles
THETA_CUT = 34.5
SHIFT = 0.18           # centre of the ring drifts forward by this much so the flare runs into the clip
TH_SHIFT0, TH_SHIFT1 = 40.0, 0.0
TH_END = -14.0         # last row of the sweep (end is hidden inside the clip skin)
TH_TAPER0, TH_TAPER1 = -999.0, -1000.0  # no taper
STEP = 2.0
TAPER = True
XB_TAPER = 0.733
UVC = (0.2165787, 0.1224134)


def theta(co):
    t = math.degrees(math.atan2(co.z - CZ, -(co.y - CY)))
    return t + 360.0 if t < -100 else t


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def xt(th):
    return X_LIP + (X_FRONT - X_LIP) * smooth((TH_N0 - th) / (TH_N0 - TH_N1))


def build(old_mesh, mirror=False):
    bm = bmesh.new(); bm.from_mesh(old_mesh)
    uvl = bm.loops.layers.uv.active
    # --- 1. delete the lower front (tongue + irregular rows)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if theta(v.co) < THETA_CUT], context='VERTS')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for t in (bm.verts, bm.edges, bm.faces): t.ensure_lookup_table()
    # --- 2. waviness: per-row k so that lip x == X_LIP (rows 34..165), constant beyond
    bins = {}
    for v in bm.verts:
        th = theta(v.co)
        if th <= 165:
            bins.setdefault(round(th), []).append(v.co.x)
    keys = sorted(bins)
    xmin = {k: min(bins[k]) for k in keys}; xmax = {k: max(bins[k]) for k in keys}
    kraw = {k: (xt(k) - xmin[k]) / (xmax[k] - xmin[k]) for k in keys}
    def mavg(d, w=3):
        out = {}
        for i, k in enumerate(keys):
            ks = keys[max(0, i - w): i + w + 1]
            out[k] = sum(d[j] for j in ks) / len(ks)
        return out
    ksm = mavg(kraw); xbs = mavg(xmin)
    def interp(d, th):
        if th <= keys[0]: return d[keys[0]]
        if th >= keys[-1]: return d[keys[-1]]
        lo = max(k for k in keys if k <= th); hi = min(k for k in keys if k >= th)
        if lo == hi: return d[lo]
        u = (th - lo) / (hi - lo)
        return d[lo] * (1 - u) + d[hi] * u
    for v in bm.verts:
        th = theta(v.co)
        k = interp(ksm, th); xb = interp(xbs, th)
        v.co.x = xb + (v.co.x - xb) * k
    # --- 3. template row = lowest-angle remaining row
    thb_vals = sorted(theta(v.co) for v in bm.verts)
    thb = thb_vals[0]
    cut = [e for e in bm.edges if e.is_boundary and all(abs(theta(v.co) - thb) < 0.6 for v in e.verts)]
    # chain order
    deg = {}
    for e in cut:
        for v in e.verts: deg[v] = deg.get(v, 0) + 1
    ends = [v for v, d in deg.items() if d == 1]
    assert len(ends) == 2, ("chain ends", len(ends), len(cut))
    order = [ends[0]]; prev = None
    while True:
        cur = order[-1]
        nxt = [e.other_vert(cur) for e in cut if cur in e.verts and e.other_vert(cur) is not prev]
        nxt = [n for n in nxt if n not in order]
        if not nxt: break
        prev = cur; order.append(nxt[0])
    assert len(order) == len(deg), (len(order), len(deg))
    tmpl = [(v.co.x, math.hypot(v.co.y - CY, v.co.z - CZ)) for v in order]
    rm = 0.5 * (min(r for _, r in tmpl) + max(r for _, r in tmpl))
    # --- 4. sweep rows
    cur_edges = cut; cur_order = order
    th = thb - STEP
    rows = 0
    while th >= TH_END - 1e-6:
        res = bmesh.ops.extrude_edge_only(bm, edges=cur_edges)
        geom = res['geom']
        nv = set(g for g in geom if isinstance(g, bmesh.types.BMVert))
        ne = [g for g in geom if isinstance(g, bmesh.types.BMEdge)]
        newedges = [e for e in ne if all(v in nv for v in e.verts)]
        mp = {}
        for v in cur_order:
            for e in v.link_edges:
                w = e.other_vert(v)
                if w in nv: mp[v] = w
        neworder = [mp[v] for v in cur_order]
        f = max(0.04, smooth((th - TH_TAPER1) / (TH_TAPER0 - TH_TAPER1))) if TAPER else 1.0
        kk = (f if TAPER else 1.0)*(xt(th) - XB_TAPER) / (xt(thb) - XB_TAPER)
        sh = SHIFT * smooth((TH_SHIFT0 - th) / (TH_SHIFT0 - TH_SHIFT1))
        c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
        for (xj, rj), w in zip(tmpl, neworder):
            r = rm + (rj - rm) * f
            x = XB_TAPER + (xj - XB_TAPER) * kk
            w.co = Vector((x, CY - sh - r * c, CZ + r * s))
        cur_edges = newedges; cur_order = neworder
        th -= STEP; rows += 1
    for f_ in bm.faces:
        for l in f_.loops: l[uvl].uv = UVC
    if mirror:
        for v in bm.verts: v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.normal_update()
    me = bpy.data.meshes.new(old_mesh.name + "_ring")
    bm.to_mesh(me); bm.free()
    for m in old_mesh.materials: me.materials.append(m)
    return me, rows
