"""Scale and place the high-detail reference model (Nik's Novamodel.blend, one mesh) in the car frame.

Uniform scale to the FIA length 3622 (its length : width : height already match the real car within mm), centred
on x, ground z = 0, nose at y = -(1.1715 + 0.670) (FIA front overhang), nose towards -y. Result: object REF_BODY in
collection REF. Prints the tyre contacts so the wheel positions can be checked against the real axles."""
import bpy
import numpy as np
from mathutils import Matrix

SRC = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\Novamodel_src.blend"
L, NOSE_Y = 3.622, -(1.1715 + 0.670)


def load():
    with bpy.data.libraries.load(SRC, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == "classic car 3d model"]
    o = dst.objects[0]
    coll = bpy.data.collections.get("REF") or bpy.data.collections.new("REF")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    coll.objects.link(o)
    o.name = o.data.name = "REF_BODY"
    return o


def fit(o):
    me = o.data
    me.transform(o.matrix_world); o.matrix_world = Matrix()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    mn, mx = co.min(0), co.max(0)
    s = L / (mx[1] - mn[1])
    co = (co - np.array([(mn[0] + mx[0]) / 2, mn[1], mn[2]])) * s + np.array([0.0, NOSE_Y, 0.0])
    me.vertices.foreach_set("co", co.ravel()); me.update()
    size = co.max(0) - co.min(0)
    zl = 0.012 * size[2]
    cp = {}
    for sx in (1, -1):
        for sy in (1, -1):
            q = co[(co[:, 2] < zl) & (co[:, 0] * sx > 0.15 * size[0]) & ((co[:, 1] - co[:, 1].mean()) * sy > 0.15 * size[1])]
            cp[(sx, sy)] = q.mean(0)
    yf = (cp[(1, -1)][1] + cp[(-1, -1)][1]) / 2
    yr = (cp[(1, 1)][1] + cp[(-1, 1)][1]) / 2
    return {"scale": round(float(s), 4), "size_mm": (size * 1000).round(0).tolist(),
            "front_axle_y": round(float(yf), 4), "rear_axle_y": round(float(yr), 4), "wheelbase": round(float(yr - yf), 4),
            "track_f": round(float(cp[(1, -1)][0] - cp[(-1, -1)][0]), 4), "track_r": round(float(cp[(1, 1)][0] - cp[(-1, 1)][0]), 4)}


def split_wheels():
    """Loose parts: the body stays REF_BODY, the four wheels go to REF_WHEELS (hidden), stray specks are deleted."""
    o = bpy.data.objects["REF_BODY"]
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE"); bpy.ops.object.mode_set(mode="OBJECT")
    R = bpy.data.collections["REF"]
    wc = bpy.data.collections.get("REF_WHEELS") or bpy.data.collections.new("REF_WHEELS")
    if wc.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(wc)
    parts = sorted((p for p in R.objects if p.type == "MESH"), key=lambda p: -len(p.data.polygons))
    parts[0].name = parts[0].data.name = "REF_BODY"
    for p in parts[1:]:
        if len(p.data.polygons) > 100000:
            R.objects.unlink(p); wc.objects.link(p); p.hide_render = True
        else:
            bpy.data.objects.remove(p)
    wc.hide_render = True
    return len(parts)


def main():
    o = bpy.data.objects.get("REF_BODY") or load()
    return fit(o)


if __name__ == "__main__":
    print("==", main())


# ---------------------------------------------------------------- arch openings onto the photo-traced arches
Z_LIP0 = 0.29        # lowest lip height compared (below it the openings run on under the bumpers)
def _side_outline(bvh, yc, sx, top_guess):
    """Arch lip of the body on one side (sx +1/-1) seen from the side: rays along -x*sx at (y, z) grid.
    Returns the outline polyline (y, z) from the front bottom, over the top, to the rear bottom."""
    import numpy as np
    from mathutils import Vector
    def open_at(y, z):
        h = bvh.ray_cast(Vector((1.5 * sx, y, z)), Vector((-sx, 0, 0)), 3.0)
        return h[0] is None or abs(h[0].x) < 0.62
    ys = np.arange(yc - 0.6, yc + 0.6, 0.003)
    i0 = int(np.argmin(np.abs(ys - yc)))
    fr, rr = [], []
    for z in np.arange(Z_LIP0, top_guess, 0.01):
        op = [open_at(y, z) for y in ys]
        if not op[i0]:
            break
        a = b = i0
        while a > 0 and op[a - 1]:
            a -= 1
        while b < len(ys) - 1 and op[b + 1]:
            b += 1
        fr.append((ys[a], z)); rr.append((ys[b], z))
    top = []
    for y in np.arange(fr[-1][0] + 0.01, rr[-1][0] - 0.01, 0.01):
        for z in np.arange(fr[-1][1], 0.85, 0.002):
            if not open_at(y, z):
                top.append((y, z)); break
    return fr + top + rr[::-1]


def _resample(poly, n=90):
    import numpy as np
    p = np.array(poly, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, p[:, 0]), np.interp(t, d, p[:, 1])]


def arch_morph(up=0.12, side=0.22, x_in=(0.45, 0.60)):
    """Reshape the reference body's arch openings onto the photo-traced arches (body_profile arch_shapes, model
    frame): lip-point displacements by arc length, spread with a falloff (shorter upward so the shoulder crease
    above the arch stays put). Wheels (REF_WHEELS) are discarded later - the car's own wheels go in."""
    import sys
    import numpy as np
    from mathutils.bvhtree import BVHTree
    sys.path.insert(0, r"D:\Claude\vauxhall_nova_gte_1989\blender\scripts")
    import body_geom as g
    o = bpy.data.objects["REF_BODY"]
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    me = o.data
    co = np.empty(len(me.vertices) * 3, np.float64); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    disp = np.zeros_like(co)
    report = {}
    for key, yc in (("front", -1.1715), ("rear", 1.1715)):
        loop = list(g.arch_poly(key))
        if loop[0] == loop[-1]:
            loop = loop[:-1]
        n = len(loop)
        keep = [z > Z_LIP0 - 0.01 for y, z in loop]
        start = next(i for i in range(n) if keep[i] and not keep[i - 1])     # first point after the bottom
        ph = []
        i = start
        while keep[i % n] and len(ph) < n:
            ph.append(loop[i % n]); i += 1
        if ph[0][0] > ph[-1][0]:
            ph = ph[::-1]                                       # front bottom -> over the top -> rear bottom
        P = _resample(ph)
        for sx in (1, -1):
            M = _resample(_side_outline(bvh, yc, sx, 0.80))
            D = P - M                                            # (dy, dz) per lip sample
            assert np.linalg.norm(D, axis=1).mean() < 0.06, "%s: lip correspondence off (mean %.0f mm)" % (
                key, 1000 * np.linalg.norm(D, axis=1).mean())
            side_sel = np.where((co[:, 0] * sx > x_in[0]) & (np.abs(co[:, 1] - yc) < 0.75) & (co[:, 2] < 0.95))[0]
            pts = co[side_sel][:, 1:3]
            # nearest lip sample per vertex
            dd = np.linalg.norm(pts[:, None, :] - M[None, :, :], axis=2)
            j = dd.argmin(1); dist = dd[np.arange(len(j)), j]
            above = pts[:, 1] > M[j, 1] + 0.005
            reach = np.where(above, up, side)
            t = np.clip(1.0 - dist / reach, 0, 1); f = t * t * (3 - 2 * t)
            xw = np.clip((co[side_sel, 0] * sx - x_in[0]) / (x_in[1] - x_in[0]), 0, 1)
            disp[side_sel, 1] += D[j, 0] * f * xw
            disp[side_sel, 2] += D[j, 1] * f * xw
            report[f"{key}{'L' if sx > 0 else 'R'}"] = {"max_shift_mm": round(float(np.abs(D).max() * 1000), 1),
                                                        "mean_shift_mm": round(float(np.linalg.norm(D, axis=1).mean() * 1000), 1)}
    co += disp
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return report


def _closest_on_poly(P, q):
    """Closest point on polyline P (Nx2) to q (2,)."""
    import numpy as np
    a, b = P[:-1], P[1:]
    ab = b - a
    t = np.clip(((q - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-12), 0, 1)
    c = a + ab * t[:, None]
    return c[np.argmin(((c - q) ** 2).sum(1))]


def arch_morph_smooth(up=0.14, side=0.25, sigma=0.06, x_in=(0.20, 0.35)):
    """v2 (v1 crumpled the skin: arc-length pairing slid the lip sideways and nearest-sample lookup jumped).
    Each model lip point moves straight onto the closest point of the photo-traced arch (no sliding); the offsets
    are smoothed along the lip; every nearby vertex takes a Gaussian-weighted blend of them (smooth field) with a
    smooth falloff - shorter upward so the shoulder crease above the arch stays put."""
    import sys
    import numpy as np
    from mathutils.bvhtree import BVHTree
    sys.path.insert(0, r"D:\Claude\vauxhall_nova_gte_1989\blender\scripts")
    import body_geom as g
    o = bpy.data.objects["REF_BODY"]
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    me = o.data
    co = np.empty(len(me.vertices) * 3, np.float64); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    disp = np.zeros_like(co)
    report = {}
    for key, yc in (("front", -1.1715), ("rear", 1.1715)):
        ph = np.array([(y, z) for y, z in g.arch_poly(key) if z > Z_LIP0 - 0.03])
        P = _resample(sorted(ph.tolist(), key=lambda p: 0) if False else ph.tolist(), 400)
        for sx in (1, -1):
            M = _resample(_side_outline(bvh, yc, sx, 0.80), 120)
            D = np.array([_closest_on_poly(P, m) - m for m in M])
            k = 7                                                # smooth the offsets along the lip
            Dp = np.pad(D, ((k, k), (0, 0)), mode="edge")
            D = np.array([Dp[i:i + 2 * k + 1].mean(0) for i in range(len(D))])
            sel = np.where((co[:, 0] * sx > x_in[0]) & (np.abs(co[:, 1] - yc) < 0.75) & (co[:, 2] < 0.95))[0]
            pts = co[sel][:, 1:3]
            d2 = ((pts[:, None, :] - M[None, :, :]) ** 2).sum(2)
            w = np.exp(-0.5 * d2 / sigma ** 2) + 1e-30
            Dv = (w[:, :, None] * D[None, :, :]).sum(1) / w.sum(1)[:, None]
            dmin = np.sqrt(d2.min(1))
            jn = d2.argmin(1)
            above = pts[:, 1] > M[jn, 1] + 0.005
            reach = np.where(above, up, side)
            t = np.clip(1.0 - dmin / reach, 0, 1); f = t * t * (3 - 2 * t)
            xw = np.clip((co[sel, 0] * sx - x_in[0]) / (x_in[1] - x_in[0]), 0, 1)
            disp[sel, 1] += Dv[:, 0] * f * xw
            disp[sel, 2] += Dv[:, 1] * f * xw
            report[f"{key}{'L' if sx > 0 else 'R'}"] = {"max_mm": round(float(np.linalg.norm(D, axis=1).max() * 1000), 1),
                                                        "mean_mm": round(float(np.linalg.norm(D, axis=1).mean() * 1000), 1)}
    co += disp
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return report


def y_shift_arch(key="front", delta=-0.035, core=(-1.33, -1.00), ends=(-1.8415, -0.72)):
    """Move an arch along the car with a y-only remap applied to EVERY vertex (all surfaces at one y move alike, so
    nothing can pass through anything): full shift over the arch core, smooth ramps to zero at the nose and at the
    door's front shut line. Monotonic as long as |delta| is small against the ramp lengths."""
    import numpy as np
    o = bpy.data.objects["REF_BODY"]
    me = o.data
    co = np.empty(len(me.vertices) * 3, np.float64); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    y = co[:, 1]
    ss = lambda t: np.clip(t, 0, 1) ** 2 * (3 - 2 * np.clip(t, 0, 1))
    w = np.where(y < core[0], ss((y - ends[0]) / (core[0] - ends[0])),
                 np.where(y > core[1], 1 - ss((y - core[1]) / (ends[1] - core[1])), 1.0))
    w = np.where((y < ends[0]) | (y > ends[1]), 0.0, w)
    co[:, 1] += delta * w
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return {"key": key, "delta_mm": delta * 1000, "moved_verts": int((w > 0).sum())}
