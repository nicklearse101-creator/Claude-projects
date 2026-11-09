"""New scuttle panel, bonnet rear-edge lip and separate wipers (Nik 2026-10-19: wipers moulded into the scuttle).
Runs after windscreen_ref.py (uses its screen surface), before details_ref.py. fix_shape.scuttle_cut has already cut
the bonnet's rear edge clean and removed the model's scuttle.

- DET_SCUTTLE: black plastic panel from just under the bonnet's rear edge (12 mm down, tucked under it) to under the
  windscreen rubber, |x| <= 0.60; cross-section flat then curving up to the glass (as the model's). Slots as a
  texture (scuttle_slots.png): a band of 5 mm slots every 11 mm along the front half (photo redgte_20).
- DET_BONNET_LIP: 12 mm turned-down edge along the bonnet's rear edge (paint), so the cut edge has thickness.
- DET_WIPERS: two tandem wipers as in redgte_20 (front view): pivots on the scuttle on the car's right of each half,
  blades lying along the screen base pointing to the car's left. Positions back-projected from the photo through
  the matched camera c20 onto the screen / scuttle. Pivot boss, arm, blade - black.
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fix_shape as fs          # noqa: E402
import windscreen_ref as ws     # noqa: E402

TEX = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\tex"
XMAX = 0.60
# redgte_20 pixels (1200 x 900): pivots, blade ends, arm ends (left / right as seen in the photo)
PHOTO = {"pivot": [(430, 304), (621.5, 304)], "blade": [((476, 284), (671, 276.5)), ((690, 281.5), (841.5, 271.5))],
         "arm_end": [(580, 279), (775, 275)]}


def _object(name, bm, mats):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.data.collections["REF"].objects.link(o)
    return o


def slots_material():
    W, H = 2048, 128
    img = np.full((H, W, 3), 0.035, np.float32)
    u = (np.arange(W) + 0.5) / W * (2 * XMAX)                        # metres across
    v = (np.arange(H) + 0.5) / H
    slot_u = (np.mod(u, 0.011) < 0.005)
    band = (v > 0.10) & (v < 0.42)
    img[np.ix_(band, slot_u)] = 0.006
    os.makedirs(TEX, exist_ok=True)
    path = os.path.join(TEX, "scuttle_slots.png")
    im = bpy.data.images.get("scuttle_slots.png")
    if im is not None and tuple(im.size) != (W, H):
        bpy.data.images.remove(im); im = None
    im = im or bpy.data.images.new("scuttle_slots.png", W, H)
    px = np.ones((H, W, 4), np.float32); px[:, :, :3] = img
    im.pixels.foreach_set(px.ravel()); im.filepath_raw = path; im.file_format = "PNG"; im.save()
    im.colorspace_settings.name = "Non-Color"
    m = bpy.data.materials.get("scuttle_grille") or bpy.data.materials["trim_black"].copy()
    m.name = "scuttle_grille"
    m["ac_tex"] = json.dumps({"DIFFUSE": path}); m["ac_preset"] = "trim"; m["ac_shader"] = "ksPerPixelMultiMap"
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tx = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    tx.image = im
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    return m


def panel(c, zat):
    xs = np.linspace(-XMAX, XMAX, 121)
    nt_ = 24
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows, uvs = [], []
    for x in xs:
        ye = float(fs.bonnet_edge_y(x))
        zF = zat(x, ye - 0.004) - 0.012
        F = np.array([ye + 0.003, zF])
        S = ws.surf(c, x, ws.Z_BASE - 0.006)[0]
        R = np.array([S.y, S.z])
        P1 = np.array([F[0] + 0.5 * (R[0] - F[0]), F[1] + 0.004])
        P2 = np.array([R[0] - 0.015, R[1] - 0.020])
        row = []
        for t in np.linspace(0, 1, nt_):
            p = (1 - t) ** 3 * F + 3 * (1 - t) ** 2 * t * P1 + 3 * (1 - t) * t * t * P2 + t ** 3 * R
            row.append(bm.verts.new((x, p[0], p[1])))
        rows.append(row)
    for i in range(len(xs) - 1):
        for k in range(nt_ - 1):
            f = bm.faces.new((rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]))
            f.smooth = True
            for lp, (ii, kk) in zip(f.loops, ((i, k), (i + 1, k), (i + 1, k + 1), (i, k + 1))):
                lp[uvl].uv = ((xs[ii] + XMAX) / (2 * XMAX), kk / (nt_ - 1))
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    return _object("DET_SCUTTLE", bm, [slots_material()])


def lip(zat):
    bm = bmesh.new()
    top, bot = [], []
    for x in np.linspace(-XMAX, XMAX, 121):
        ye = float(fs.bonnet_edge_y(x)); zt = zat(x, ye - 0.004)
        top.append(bm.verts.new((x, ye - 0.0005, zt - 0.0005)))
        bot.append(bm.verts.new((x, ye + 0.001, zt - 0.012)))
    for i in range(len(top) - 1):
        f = bm.faces.new((top[i], bot[i], bot[i + 1], top[i + 1])); f.smooth = True
        f.normal_update()
        if f.normal.y < 0:
            f.normal_flip()
    return _object("DET_BONNET_LIP", bm, [bpy.data.materials["paint_gunmetal"]])


def _ray(px, py):
    import render_matched as rm
    cam = rm.cameras()["c20"]
    W, H, f = cam["W"], cam["H"], cam["f"]
    d = cam["rot"] @ Vector(((px - W / 2) / f, -(py - H / 2) / f, -1)); d.normalize()
    return Vector(cam["loc"]), d


def on_screen(c, px, py):
    """Ray from the photo pixel to the windscreen surface y = f(x, z) (bisection on the signed distance)."""
    C, d = _ray(px, py)
    g = lambda t: (C + d * t).y - ws.surf(c, (C + d * t).x, (C + d * t).z)[0].y
    a, b = 0.5, 15.0
    for _ in range(80):
        m = (a + b) / 2
        if g(a) * g(m) <= 0:
            b = m
        else:
            a = m
    p = C + d * ((a + b) / 2)
    return p, ws.surf(c, p.x, p.z)[1]


def on_object(obj, px, py):
    """Ray from the photo pixel onto obj; if it misses (the pixel is a few mm off the panel), the point of the ray
    nearest to obj, snapped onto obj."""
    C, d = _ray(px, py)
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    hit = bvh.ray_cast(C, d, 20.0)
    if hit[0] is not None:
        return hit[0], hit[1]
    best = None
    for t in np.arange(0.5, 15.0, 0.002):
        q = bvh.find_nearest(C + d * t)
        if q[0] is not None and (best is None or q[3] < best[3]):
            best = q
    return best[0], best[1]


def _box(bm, a, b, up, w, h):
    """Box from a to b (centre line), height h along 'up', width w across."""
    ax = (b - a); L = ax.length; ax.normalize()
    side = ax.cross(up).normalized(); up2 = side.cross(ax).normalized()
    M = Matrix((ax * L, side * w, up2 * h)).transposed().to_4x4()
    M.translation = (a + b) / 2
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=M, verts=r["verts"])


def wipers(c, scut):
    bm = bmesh.new()
    out = []
    for i in range(2):
        piv, pn = on_object(scut, *PHOTO["pivot"][i])
        b0, n0 = on_screen(c, *PHOTO["blade"][i][0]); b1, n1 = on_screen(c, *PHOTO["blade"][i][1])
        ae, ne = on_screen(c, *PHOTO["arm_end"][i])
        outn = -(n0 + n1).normalized()                                # out of the glass
        # boss on the scuttle
        _box(bm, piv - pn * 0.002, piv + pn * 0.022, Vector((1, 0, 0)), 0.03, 0.03)
        # arm: from the top of the boss to the blade's middle, 12 mm above the glass
        a0 = piv + pn * 0.02
        a1 = ae - ne * 0.014
        _box(bm, a0, a1, outn, 0.012, 0.006)
        # blade: on the glass, 8 mm off it, 18 mm tall
        _box(bm, b0 - n0 * 0.009, b1 - n1 * 0.009, outn, 0.008, 0.016)
        out.append({"pivot": tuple(round(v, 3) for v in piv), "blade_len_m": round((b1 - b0).length, 3)})
    for f in bm.faces:
        f.smooth = False
    o = _object("DET_WIPERS", bm, [bpy.data.materials["trim_black"]])
    return out


def main():
    c = ws.fit()
    bvh = BVHTree.FromObject(bpy.data.objects["REF_BODY"], bpy.context.evaluated_depsgraph_get())
    zat = lambda x, y: (bvh.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)), 2.0)[0] or Vector((0, 0, 0.87))).z
    scut = panel(c, zat)
    lip(zat)
    return {"scuttle_faces": len(scut.data.polygons), "wipers": wipers(c, scut)}


if __name__ == "__main__":
    print("==", main())
