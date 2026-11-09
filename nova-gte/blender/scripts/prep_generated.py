"""Turn the fitted GEN_BODY (fit_generated.py) into AC parts. Runs inside nova_gen.blend (a copy of nova_gte.blend).

  1. the generated wheels are cut out (our WHEELS with brakes / physics pivots replace them);
  2. the windows are cut with slabs made from the photo-matched procedural glass (BODY_glass, GLASS_HATCH):
     GEN_BODY keeps the openings, GEN_GLASS gets the cut-out surface with the tinted glass material;
  3. UV triangles of the faces inside the tail lamps are written out so the paint recolour leaves the red lenses alone
     (tools/gen_textures.py makes the gun-metal paint texture + txMaps from the generated texture);
  4. materials: GEN_paint (ksPerPixelMultiMap, the texture files), GEN_inner (inside of the shell: a 3 mm Solidify
     so the hollow shell reads from inside the cabin and through the glass);
  5. the procedural exterior (BODY, FRONT, SIDE, REAR, DETAILS except the arch liners) is marked no_export / hidden.
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
TEX = os.path.join(ROOT, "export", "gen", "tex")
TYRE_R = 0.300                       # cut radius round each wheel centre (tyre 0.2916 + 8 mm)
KEEP = ("ARCH_LINER_",)              # procedural parts kept with the generated body


def world_bm(objs):
    bm = bmesh.new()
    for o in objs:
        me = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(o.matrix_world)
        me2 = bpy.data.meshes.new("_tmp"); tmp.to_mesh(me2); tmp.free()
        bm.from_mesh(me2); bpy.data.meshes.remove(me2)
        o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return bm


def wheels_out(ob):
    cs = [bpy.data.objects["WHEEL_" + t].matrix_world.translation.copy() for t in ("LF", "RF", "LR", "RR")]
    bm = bmesh.new(); bm.from_mesh(ob.data)
    dead = []
    for f in bm.faces:
        c = f.calc_center_median()
        for w in cs:
            if abs(c.x) > 0.40 and c.x * w.x > 0 and (c.y - w.y) ** 2 + (c.z - w.z) ** 2 < TYRE_R ** 2:
                dead.append(f); break
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(ob.data); bm.free()
    return len(dead)


def slab(names, thick=0.16):
    """Closed slab round the procedural glass surfaces (both sides), for the window Booleans."""
    srcs = [bpy.data.objects[n] for n in names if n in bpy.data.objects]
    bm = world_bm(srcs)
    me = bpy.data.meshes.new("CUT_gen_glass")
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.get("CUT_gen_glass")
    if o:
        bpy.data.objects.remove(o)
    o = bpy.data.objects.new("CUT_gen_glass", me)
    bpy.data.collections["GEN"].objects.link(o)
    m = o.modifiers.new("Solidify", "SOLIDIFY"); m.thickness = thick; m.offset = 0.0; m.use_even_offset = True
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    o.hide_render = True; o.display_type = "WIRE"; o["no_export"] = 1
    return o


def boolean(target, cutter, op):
    m = target.modifiers.new("Bool", "BOOLEAN")
    m.operation = op; m.object = cutter; m.solver = "EXACT"
    for attr, val in (("use_hole_tolerant", True), ("use_self", False)):
        if hasattr(m, attr):
            setattr(m, attr, val)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)


def lamp_uv_polys(ob, boxes):
    """UV triangles (0..1) of faces whose centre lies in any box (min, max Vectors)."""
    out = []
    uv = ob.data.uv_layers.active.data
    for p in ob.data.polygons:
        c = p.center
        if any(all(b0[i] <= c[i] <= b1[i] for i in range(3)) for b0, b1 in boxes):
            out.append([tuple(uv[li].uv) for li in p.loop_indices])
    return out


def box_of(name, grow=0.015):
    o = bpy.data.objects[name]
    ws = [o.matrix_world @ Vector(b) for b in o.bound_box]
    mn = Vector((min(w[i] for w in ws) - grow for i in range(3)))
    mx = Vector((max(w[i] for w in ws) + grow for i in range(3)))
    mn.y -= 0.04; mx.y += 0.04                                  # generated lens surface may sit a few cm off
    return mn, mx


ZONE_SRC = ("BODY_shell", "RECESS_HATCH", "SEAL_HATCH", "BUMPER_F", "BUMPER_F_LIP", "GRILLE_GROOVE", "GRILLE_INSERT",
            "GRILLE_SURROUND", "HEADLAMP_GLASS_L", "HEADLAMP_GLASS_R", "INDICATOR_F_L", "INDICATOR_F_R", "LAMP_PANEL",
            "SKIRT_L", "SKIRT_R", "BUMPER_R", "BUMPER_R_VALANCE", "MIRROR_L", "MIRROR_R", "REAR_PANEL_TRIM",
            "SPOILER_HATCH", "TAILLAMP_L", "TAILLAMP_R", "SCUTTLE_VENT", "DOOR_BAR_L", "DOOR_BAR_R", "PLATE_R",
            "REPEATER_L", "REPEATER_R")


def _slot_images(ob):
    """Per material slot: the base-colour image as an HxWx3 float array (sRGB values), or None."""
    import numpy as np
    out = []
    for ms in ob.material_slots:
        img = None
        m = ms.material
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image and n.image.size[0] > 0:
                    img = n.image; break
        if img is None:
            out.append(None); continue
        w, h = img.size
        a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
        out.append(a.reshape(h, w, 4)[..., :3])
    return out


def zones_from_texture(ob, smooth_iters=4):
    """Material per face from the generated model's OWN photo texture (colour at the face's UV centre) plus where the
    face is on the car, then a majority filter over neighbouring faces to remove speckle. The black rear panel, grey
    skirts/valances, window frames and lamps then follow the generated shape instead of the old procedural parts."""
    import colorsys
    import numpy as np
    me = ob.data
    imgs = _slot_images(ob)
    uvl = me.uv_layers.active.data
    nl = len(me.loops)
    uv = np.empty(nl * 2, np.float32); uvl.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    np_ = len(me.polygons)
    ls = np.empty(np_, np.int64); me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(np_, np.int64); me.polygons.foreach_get("loop_total", lt)
    mi = np.empty(np_, np.int64); me.polygons.foreach_get("material_index", mi)
    ce = np.empty(np_ * 3, np.float32); me.polygons.foreach_get("center", ce); ce = ce.reshape(-1, 3)
    cuv = np.add.reduceat(uv, ls) / lt[:, None]
    M = {k: bpy.data.materials.get(k) for k in ("paint_gunmetal", "trim_black", "trim_grey", "lamp_glass_amber",
                                                "lamp_glass_clear", "lamp_glass_red", "plate_yellow")}
    names = list(M)
    lab = np.zeros(np_, np.int64)                      # 0 = paint
    for i in range(np_):
        a = imgs[mi[i]] if mi[i] < len(imgs) else None
        x, y, z = ce[i]
        if a is None:
            lab[i] = 1; continue
        H, W = a.shape[:2]
        u, v = cuv[i]
        r, g, b = a[min(H - 1, max(0, int(v * H))), min(W - 1, max(0, int((u % 1.0) * W)))]
        h, s, val = colorsys.rgb_to_hsv(float(r), float(g), float(b)); h *= 360
        ends = y < -1.45 or y > 1.45
        if val < 0.13 or (s < 0.25 and val < 0.25):
            lab[i] = 1                                                     # black trim / rear panel / frames
        elif 20 <= h <= 50 and s > 0.45 and val > 0.35 and ends:
            lab[i] = 3                                                     # amber indicators
        elif 45 < h < 65 and s > 0.5 and y > 1.6:
            lab[i] = 6                                                     # rear plate
        elif (h < 15 or h > 340) and s > 0.55 and y > 1.62 and z > 0.55:
            lab[i] = 5                                                     # tail-lamp red
        elif y < -1.65 and 0.45 < z < 0.8 and abs(x) > 0.3 and s < 0.2 and val > 0.55:
            lab[i] = 4                                                     # headlamp glass
        elif s < 0.15 and val < 0.6 and z < 0.45:
            lab[i] = 2                                                     # grey skirts / valances
    # majority filter over edge neighbours
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    nb = [[f2.index for e in f.edges for f2 in e.link_faces if f2 is not f] for f in bm.faces]
    bm.free()
    for _ in range(smooth_iters):
        new = lab.copy()
        for i, ns in enumerate(nb):
            if len(ns) < 2:
                continue
            c = np.bincount(lab[ns + [i]], minlength=len(names))
            k = int(c.argmax())
            if c[k] > c[lab[i]]:
                new[i] = k
        lab = new
    used = sorted(set(lab.tolist()))
    me.materials.clear()
    for k in used:
        me.materials.append(M[names[k]] or M["paint_gunmetal"])
    remap = {k: j for j, k in enumerate(used)}
    me.polygons.foreach_set("material_index", [remap[int(k)] for k in lab])
    return [me.materials[j] for j in range(len(used))]


def zones_by_projection(ob, smooth_iters=5):
    """Material per generated face projected from the photo-matched procedural parts (ZONE_SRC) along the car's main
    axes: faces looking forward/back take the part seen straight ahead/behind at the same (x, z), side faces the part
    seen from the side at the same (y, z), upward faces are paint. Depth differences between the two models no
    longer matter, so trim edges stay straight. Then a short majority filter."""
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new(); face_mat = []
    for n in ZONE_SRC:
        o = bpy.data.objects.get(n)
        if o is None or o.type != "MESH":
            continue
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(o.matrix_world)
        mats = [ms.material for ms in o.material_slots]
        face_mat += [mats[f.material_index] if f.material_index < len(mats) else None for f in tmp.faces]
        me2 = bpy.data.meshes.new("_z"); tmp.to_mesh(me2); tmp.free(); ev.to_mesh_clear()
        bm.from_mesh(me2); bpy.data.meshes.remove(me2)
    bvh = BVHTree.FromBMesh(bm); bm.free()
    paint = bpy.data.materials["paint_gunmetal"]; black = bpy.data.materials["trim_black"]

    def norm(m):
        if m is None or m.name.startswith("int_") or m.name in ("panel_gap", "bumper_stripe"):
            return paint
        return black if m.name == "glass_tint" else m
    slots, idx, lab = [], {}, []
    for p in ob.data.polygons:
        c, nrm = Vector(p.center), p.normal
        m = paint
        ends = abs(c.y) > 1.45 and nrm.z < 0.8                    # nose / tail: always seen from ahead / behind
        if ends or abs(nrm.y) > 0.55 or abs(nrm.x) > 0.45:
            if ends or abs(nrm.y) >= abs(nrm.x):
                sgn = 1 if (c.y > 0 if ends else nrm.y > 0) else -1
                o, d = Vector((c.x, 5.0 * sgn, c.z)), Vector((0, -sgn, 0))
            else:
                sgn = 1 if nrm.x > 0 else -1
                o, d = Vector((5.0 * sgn, c.y, c.z)), Vector((-sgn, 0, 0))
            hit = bvh.ray_cast(o, d, 10.0)
            if hit[0] is not None:
                m = norm(face_mat[hit[2]])
        if m.name not in idx:
            idx[m.name] = len(slots); slots.append(m)
        lab.append(idx[m.name])
    lab = np.array(lab)
    bmm = bmesh.new(); bmm.from_mesh(ob.data); bmm.faces.ensure_lookup_table()
    nb = [[f2.index for e in f.edges for f2 in e.link_faces if f2 is not f] for f in bmm.faces]
    bmm.free()
    for _ in range(smooth_iters):
        new = lab.copy()
        for i, ns in enumerate(nb):
            if len(ns) >= 2:
                cnt = np.bincount(lab[ns + [i]], minlength=len(slots)); k = int(cnt.argmax())
                if cnt[k] > cnt[lab[i]]:
                    new[i] = k
        lab = new
    ob.data.materials.clear()
    for m in slots:
        ob.data.materials.append(m)
    ob.data.polygons.foreach_set("material_index", lab.tolist())
    return slots


def zones_from_procedural(ob, reach=0.10):
    """Material per generated face = material of the nearest photo-matched procedural surface (paint, black trim,
    grey skirts/valances, lamps, plates). Returns the list of materials now on ob (slot order)."""
    bm = bmesh.new()
    face_mat = []
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ZONE_SRC:
        o = bpy.data.objects.get(n)
        if o is None or o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(o.matrix_world)
        mats = [ms.material for ms in o.material_slots]
        for f in tmp.faces:
            face_mat.append(mats[f.material_index] if f.material_index < len(mats) else None)
        me2 = bpy.data.meshes.new("_z"); tmp.to_mesh(me2); tmp.free(); ev.to_mesh_clear()
        bm.from_mesh(me2); bpy.data.meshes.remove(me2)
    bvh = BVHTree.FromBMesh(bm)
    paint = bpy.data.materials["paint_gunmetal"]
    black = bpy.data.materials["trim_black"]
    slots, idx = [], {}
    assign = []
    for p in ob.data.polygons:
        c = Vector(p.center)
        hit = bvh.find_nearest(c, reach)
        m = face_mat[hit[2]] if hit[0] is not None else black          # underside etc.
        if m is None or m.name in ("glass_tint", "panel_gap"):
            m = black if (m and m.name == "glass_tint") else paint
        if m.name not in idx:
            idx[m.name] = len(slots); slots.append(m)
        assign.append(idx[m.name])
    bm.free()
    ob.data.materials.clear()
    for m in slots:
        ob.data.materials.append(m)
    ob.data.polygons.foreach_set("material_index", assign)
    return slots


def material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    return m


def textured(m, img_path):
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img_path, check_existing=True)
    tex.image.reload()
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])


def build():
    ob = bpy.data.objects["GEN_BODY"]
    n_wheel = wheels_out(ob)

    # windows: difference on the body, intersect on a copy for the glass
    cut = slab(["BODY_glass", "GLASS_HATCH"])
    gl = bpy.data.objects.get("GEN_GLASS")
    if gl:
        bpy.data.objects.remove(gl)
    gl = ob.copy(); gl.data = ob.data.copy(); gl.name = gl.data.name = "GEN_GLASS"
    bpy.data.collections["GEN"].objects.link(gl)
    boolean(gl, cut, "INTERSECT")
    boolean(ob, cut, "DIFFERENCE")

    # tail-lamp lenses keep their red: UV polygons for gen_textures.py
    boxes = [box_of(n) for n in ("TAILLAMP_L", "TAILLAMP_R") if n in bpy.data.objects]
    polys = lamp_uv_polys(ob, boxes)
    os.makedirs(TEX, exist_ok=True)
    json.dump({"protect": polys}, open(os.path.join(TEX, "protect_uv.json"), "w"))

    # materials
    paint = material("GEN_paint")
    paint["ac_shader"] = "ksPerPixelMultiMap"; paint["ac_preset"] = "paint"
    paint["ac_tex"] = json.dumps({"DIFFUSE": os.path.join(TEX, "gen_body_col.dds"), "MAPS": os.path.join(TEX, "gen_body_maps.dds")})
    png = os.path.join(TEX, "gen_body_col.png")
    textured(paint, png if os.path.exists(png) else os.path.join(TEX, "Image_0.png"))
    b = next(n for n in paint.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Roughness"].default_value = 0.3
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 1.0
    inner = material("GEN_inner")
    bi = next(n for n in inner.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bi.inputs["Base Color"].default_value = (0.035, 0.035, 0.037, 1); bi.inputs["Roughness"].default_value = 0.8
    glass = bpy.data.materials.get("glass_tint")
    slots = zones_by_projection(ob)                                 # procedural trim layout projected on
    ob.data.materials.append(inner)                                 # last slot: the Solidify's inside faces
    gl.data.materials.clear(); gl.data.materials.append(glass)
    for p in gl.data.polygons:
        p.material_index = 0
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    s = ob.modifiers.new("Inner", "SOLIDIFY")
    s.thickness = 0.003; s.offset = -1.0; s.use_even_offset = False; s.use_rim = True
    s.material_offset = 64; s.material_offset_rim = 64              # clamped to the last slot = GEN_inner

    # procedural exterior out of the export / renders
    hidden = 0
    for cn in ("BODY", "FRONT", "SIDE", "REAR", "DETAILS", "CUTTERS"):
        c = bpy.data.collections.get(cn)
        if not c:
            continue
        c.hide_render = False
        for o in c.objects:
            if o.name.startswith(KEEP):
                continue
            o["no_export"] = 1; o.hide_render = True; o.hide_viewport = True; hidden += 1
    for cn in ("GEN", "WHEELS", "INTERIOR", "HELPERS"):
        c = bpy.data.collections.get(cn)
        if c:
            c.hide_render = False
    return {"zones": [m.name for m in slots], "wheel_faces_cut": n_wheel, "glass_tris": len(gl.data.polygons), "body_faces": len(ob.data.polygons),
            "lamp_polys": len(polys), "procedural_hidden": hidden}


if __name__ == "__main__":
    print("==", build())
