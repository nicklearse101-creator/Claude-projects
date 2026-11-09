"""Put the Meshy body (nova_meshy.blend: Meshy_Body, DOOR_L, DOOR_R) into the car file.
Runs inside blender/nova_meshy_car.blend, a copy of nova_gen.blend (our wheels WHEEL_*/SUSP_* at y -1.171 / +1.171,
helpers, interior, materials, KN5 export settings):
  1. append the Meshy parts, move them onto the wheel helpers (y shift) and scale to the master width / height;
  2. cut the generated wheels out (our wheels replace them);
  3. glass: faces in the window zones whose own texture colour is window glass (dark, unsaturated, not paint red)
     -> MESHY_GLASS / DOOR_*_GLASS with the tinted glass material (majority filter against speckle);
  4. paint: everything else keeps the Meshy texture, recoloured to gun-metal by tools/gen_textures.py (tail-lamp lenses
     protected), as MESHY_paint (ksPerPixelMultiMap, paint preset); a 3 mm inner skin (Solidify) on the body;
  5. the old generated body (GEN_*) and the procedural exterior stay in the file but are no_export / hidden.
blender -b --factory-startup blender/nova_meshy_car.blend --python tools/gen/meshy_car.py"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
SRC = os.path.join(ROOT, "blender", "nova_meshy.blend")
TEX = os.path.join(ROOT, "export", "meshy", "tex")
W_MESHY, H_MESHY = 1.580, 1.339       # measured Meshy body width (no mirrors) and height, after the length fit
W_SPEC, H_SPEC = 1.532, 1.365
TYRE_R = 0.300
BELT = 0.86


def append():
    with bpy.data.libraries.load(SRC) as (src, dst):
        dst.objects = ["Meshy_Body", "DOOR_L", "DOOR_R"]
    coll = bpy.data.collections.get("MESHY") or bpy.data.collections.new("MESHY")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    for o in dst.objects:
        coll.objects.link(o)
    bpy.context.view_layer.update()
    return {o.name.split(".")[0]: o for o in dst.objects}, coll


def fit(parts):
    """Axles onto the wheel helpers, then width / height to the master dimensions (about the ground centre)."""
    wf = bpy.data.objects["WHEEL_LF"].matrix_world.translation.y
    wr = bpy.data.objects["WHEEL_LR"].matrix_world.translation.y
    body = parts["Meshy_Body"]
    dy = (wf + wr) / 2 - (-1.141 + 1.202) / 2           # nova_meshy axles sit at -1.141 / +1.202
    T = Matrix.Diagonal((W_SPEC / W_MESHY, 1.0, H_SPEC / H_MESHY, 1.0)) @ Matrix.Translation((0, dy, 0))
    body.data.transform(body.matrix_basis); body.matrix_world = Matrix.Identity(4)
    body.data.transform(T)
    for n in ("DOOR_L", "DOOR_R"):
        d = parts[n]
        piv = T @ d.matrix_basis.translation
        d.data.transform(d.matrix_basis); d.data.transform(T)
        d.data.transform(Matrix.Translation(-piv)); d.matrix_world = Matrix.Translation(piv)
    return dy, T


def wheels_out(ob):
    cs = [bpy.data.objects["WHEEL_" + t].matrix_world.translation.copy() for t in ("LF", "RF", "LR", "RR")]
    bm = bmesh.new(); bm.from_mesh(ob.data)
    dead = [f for f in bm.faces for c in [f.calc_center_median()]
            if abs(c.x) > 0.40 and any(c.x * w.x > 0 and (c.y - w.y) ** 2 + (c.z - w.z) ** 2 < TYRE_R ** 2 for w in cs)]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(ob.data); bm.free()
    return len(dead)


def face_colours(ob):
    """sRGB colour of the Meshy texture at each face's UV centre -> (rgb Nx3, centre Nx3, normal Nx3, uv centre Nx2)."""
    me = ob.data
    img = next(n.image for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes
               if n.type == "TEX_IMAGE" and n.image)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)[..., :3]
    nl = len(me.loops); n = len(me.polygons)
    uv = np.empty(nl * 2, np.float32); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    ls = np.empty(n, np.int64); me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(n, np.int64); me.polygons.foreach_get("loop_total", lt)
    ce = np.empty(n * 3, np.float32); me.polygons.foreach_get("center", ce); ce = ce.reshape(-1, 3)
    no = np.empty(n * 3, np.float32); me.polygons.foreach_get("normal", no); no = no.reshape(-1, 3)
    cuv = np.add.reduceat(uv, ls) / lt[:, None]
    iy = np.clip((cuv[:, 1] % 1.0 * h).astype(int), 0, h - 1); ix = np.clip((cuv[:, 0] % 1.0 * w).astype(int), 0, w - 1)
    rgb = px[iy, ix]
    if img.colorspace_settings.name != "sRGB" or img.is_float:
        pass
    return rgb, ce, no, cuv, img


def hsv(rgb):
    mx = rgb.max(1); mn = rgb.min(1); d = mx - mn
    s = np.where(mx > 1e-4, d / np.maximum(mx, 1e-4), 0)
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    h = np.zeros(len(rgb))
    m = d > 1e-5
    rr = m & (mx == r); gg = m & (mx == g) & ~rr; bb = m & ~rr & ~gg
    h[rr] = (60 * ((g - b)[rr] / d[rr])) % 360
    h[gg] = 60 * ((b - r)[gg] / d[gg]) + 120
    h[bb] = 60 * ((r - g)[bb] / d[bb]) + 240
    return h, s, mx


def neighbours(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
    nb = [[f2.index for e in f.edges for f2 in e.link_faces if f2 is not f] for f in bm.faces]
    bm.free()
    return nb


def majority(lab, nb, iters=4):
    for _ in range(iters):
        new = lab.copy()
        for i, ns in enumerate(nb):
            if len(ns) < 2:
                continue
            c = np.bincount(lab[ns + [i]], minlength=2)
            if c.argmax() != lab[i] and c.max() > c[lab[i]]:
                new[i] = c.argmax()
        lab = new
    return lab


def glass_labels(ob, belt_z):
    rgb, ce, no, cuv, img = face_colours(ob)
    h, s, v = hsv(rgb)
    red = ((h < 20) | (h > 330)) & (s > 0.25)
    top = no[:, 2] > 0.85                                   # roof / sunroof stay opaque
    lab = ((ce[:, 2] > belt_z) & ~red & ~top & (v > 0.10) & (v < 0.62) & (s < 0.5) &
           (np.abs(ce[:, 1]) < 1.75)).astype(np.int64)
    return majority(lab, neighbours(ob)), rgb, ce, no, cuv


def split_off(ob, sel, name, coll, mat, parent=None):
    """Move the selected faces (bool per face) to a new object with mat; returns it."""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
    faces = [bm.faces[i] for i in np.nonzero(sel)[0]]
    nm = bmesh.new()
    uv_s = bm.loops.layers.uv.active; uv_d = nm.loops.layers.uv.new("UVMap")
    vmap = {}
    for f in faces:
        nf = nm.faces.new([vmap.setdefault(v, nm.verts.new(v.co)) for v in f.verts])
        for la, lb in zip(f.loops, nf.loops):
            lb[uv_d].uv = la[uv_s].uv
    bmesh.ops.delete(bm, geom=faces, context="FACES")
    bm.to_mesh(ob.data); bm.free()
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); nm.to_mesh(me); nm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    if parent is not None:
        o.parent = parent; o.matrix_parent_inverse = parent.matrix_world.inverted()
    o.matrix_world = ob.matrix_world.copy()
    return o


def protect_polys(ob, rgb, ce, no, cuv_all):
    """UV polygons of the tail-lamp lenses (rear-facing red at the rear corners) for gen_textures.py."""
    h, s, v = hsv(rgb)
    sel = (ce[:, 1] > 1.45) & (no[:, 1] > 0.5) & (np.abs(ce[:, 0]) > 0.42) & (ce[:, 2] > 0.45) & (ce[:, 2] < 0.95) & \
          ((h < 20) | (h > 330)) & (s > 0.35)
    uvl = ob.data.uv_layers.active.data
    return [[tuple(uvl[li].uv) for li in ob.data.polygons[i].loop_indices] for i in np.nonzero(sel)[0]]


def paint_material(img_png):
    m = bpy.data.materials.get("MESHY_paint") or bpy.data.materials.new("MESHY_paint")
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img_png, check_existing=True); tex.image.reload()
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    m["ac_shader"] = "ksPerPixelMultiMap"; m["ac_preset"] = "paint"
    m["ac_tex"] = json.dumps({"DIFFUSE": os.path.join(TEX, "gen_body_col.dds"), "MAPS": os.path.join(TEX, "gen_body_maps.dds")})
    return m


def stage1():
    """Append, fit, wheels out, glass split, tail-lamp UVs -> protect_uv.json, source texture -> TEX/meshy_src.png."""
    parts, coll = append()
    dy, T = fit(parts)
    body = parts["Meshy_Body"]
    n_wheel = wheels_out(body)
    glass_mat = bpy.data.materials["glass_tint"]
    belt = BELT * H_SPEC / H_MESHY
    os.makedirs(TEX, exist_ok=True)
    out = {"dy": dy, "wheel_faces_cut": n_wheel}
    polys = []
    for n, gname in (("Meshy_Body", "MESHY_GLASS"), ("DOOR_L", "DOOR_L_GLASS"), ("DOOR_R", "DOOR_R_GLASS")):
        ob = parts[n]
        # door meshes are local to the hinge: classify in world space
        wm = ob.matrix_world.copy()
        ob.data.transform(wm); ob.matrix_world = Matrix.Identity(4)
        lab, rgb, ce, no, cuv = glass_labels(ob, belt)
        if n == "Meshy_Body":
            polys = protect_polys(ob, rgb, ce, no, cuv)
            img = face_colours(ob)[4]
            img.save_render(os.path.join(TEX, "meshy_src.png"))
        g = split_off(ob, lab.astype(bool), gname, coll, glass_mat)
        ob.data.transform(wm.inverted()); ob.matrix_world = wm
        g.data.transform(wm.inverted()); g.matrix_world = wm
        if n != "Meshy_Body":
            g.parent = ob; g.matrix_parent_inverse = Matrix.Identity(4); g.matrix_basis = Matrix.Identity(4)
        out[gname] = int(lab.sum())
    json.dump({"protect": polys}, open(os.path.join(TEX, "protect_uv.json"), "w"))
    out["lamp_polys"] = len(polys)
    bpy.ops.wm.save_mainfile()
    return out


def stage2():
    """After gen_textures.py: gun-metal paint material on body + doors, inner skin, old bodies out of the export."""
    paint = paint_material(os.path.join(TEX, "gen_body_col.png"))
    inner = bpy.data.materials.get("GEN_inner")
    for n in ("Meshy_Body", "DOOR_L", "DOOR_R"):
        ob = bpy.data.objects[n]
        ob.data.materials.clear(); ob.data.materials.append(paint)
        for p in ob.data.polygons:
            p.material_index = 0
    body = bpy.data.objects["Meshy_Body"]
    body.data.materials.append(inner)
    for m in list(body.modifiers):
        body.modifiers.remove(m)
    s = body.modifiers.new("Inner", "SOLIDIFY")
    s.thickness = 0.003; s.offset = -1.0; s.use_even_offset = False; s.use_rim = True
    s.material_offset = 64; s.material_offset_rim = 64
    hidden = 0
    for o in bpy.data.objects:
        if o.name in ("GEN_BODY", "GEN_GLASS") or o.name.startswith("ARCH_LINER_"):
            o["no_export"] = 1; o.hide_render = True; o.hide_viewport = True; hidden += 1
    bpy.ops.wm.save_mainfile()
    return {"paint": paint.name, "hidden": hidden}


def _stage():
    import sys
    return sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "1"


if __name__ == "__main__" and _stage() in ("1", "2"):
    print("==", stage1() if _stage() == "1" else stage2())


def zone_labels(ob, glass_tree=None):
    """1 = keep the Meshy texture (trim, lamps, plates, grille, window surrounds, sills), 0 = gun-metal paint.
    Colour says what a face could be, position says where trim can exist; a short majority filter removes speckle."""
    rgb, ce, no, cuv, img = face_colours(ob)
    h, s, v = hsv(rgb)
    x, y, z = ce[:, 0], ce[:, 1], ce[:, 2]
    trimlike = (v < 0.20) | ((s < 0.18) & (v < 0.70)) | ((h > 18) & (h < 70) & (s > 0.45)) | ((v > 0.75) & (s < 0.15))
    redlamp = ((h < 20) | (h > 330)) & (s > 0.35) & (y > 1.45) & (no[:, 1] > 0.5) & (np.abs(x) > 0.42) & (z > 0.45) & (z < 0.95)
    nose = y < -1.62
    tail = y > 1.58
    low = z < 0.36
    surround = (z > 0.86) & (np.abs(no[:, 0]) > 0.45) & (no[:, 2] < 0.6)
    mirror = (np.abs(x) > 0.70) & (z > 0.84) & (z < 1.08) & (y > -0.80) & (y < -0.40)
    lab = ((trimlike & (nose | tail | low | surround | mirror)) | redlamp).astype(np.int64)
    return majority(lab, neighbours(ob), iters=3)


def stage3():
    """Zones: paint faces -> paint_gunmetal (uniform, AC paint preset); trim / lamps / plates -> MESHY_detail (the
    original Meshy texture, low reflection)."""
    paint = bpy.data.materials["paint_gunmetal"]
    det = bpy.data.materials.get("MESHY_detail") or bpy.data.materials.new("MESHY_detail")
    det.use_nodes = True
    nt = det.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(TEX, "meshy_src_2k.png"), check_existing=True)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.6
    det["ac_shader"] = "ksPerPixelMultiMap"; det["ac_preset"] = "trim"
    det["ac_tex"] = json.dumps({"DIFFUSE": os.path.join(TEX, "meshy_detail.dds"), "MAPS": os.path.join(TEX, "meshy_detail_maps.dds")})
    inner = bpy.data.materials.get("GEN_inner")
    out = {}
    for n in ("Meshy_Body", "DOOR_L", "DOOR_R"):
        ob = bpy.data.objects[n]
        # classify with the Meshy texture (put it back on the slot first)
        ob.data.materials.clear(); ob.data.materials.append(det)
        wm = ob.matrix_world.copy(); ob.data.transform(wm); ob.matrix_world = Matrix.Identity(4)
        lab = zone_labels(ob)
        ob.data.transform(wm.inverted()); ob.matrix_world = wm
        ob.data.materials.clear(); ob.data.materials.append(paint); ob.data.materials.append(det)
        if n == "Meshy_Body":
            ob.data.materials.append(inner)
        ob.data.polygons.foreach_set("material_index", lab.tolist())
        out[n] = {"paint": int((lab == 0).sum()), "detail": int(lab.sum())}
    bpy.ops.wm.save_mainfile()
    return out


def stage4():
    """Nik 2026-10-20: keep the Meshy texture as it is (no recolour; he changes the colour later). Body and doors:
    one material with the original texture (AC paint preset for the reflections); glass stays split off."""
    m = bpy.data.materials.get("MESHY_tex") or bpy.data.materials.new("MESHY_tex")
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(TEX, "meshy_src_2k.png"), check_existing=True)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.35
    m["ac_shader"] = "ksPerPixelMultiMap"; m["ac_preset"] = "paint"
    m["ac_tex"] = json.dumps({"DIFFUSE": os.path.join(TEX, "meshy_detail.dds"), "MAPS": os.path.join(TEX, "meshy_detail_maps.dds")})
    inner = bpy.data.materials.get("GEN_inner")
    for n in ("Meshy_Body", "DOOR_L", "DOOR_R"):
        me = bpy.data.objects[n].data
        me.materials.clear(); me.materials.append(m)
        if n == "Meshy_Body":
            me.materials.append(inner)
        me.polygons.foreach_set("material_index", [0] * len(me.polygons))
    bpy.ops.wm.save_mainfile()
    return {"material": m.name}


if __name__ == "__main__" and _stage() == "3":
    print("== stage3", stage3())
if __name__ == "__main__" and _stage() == "4":
    print("== stage4", stage4())
