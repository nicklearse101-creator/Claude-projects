"""GTE lettering and number plates for the reference-model car (MODEL_TODO 5); runs after prep_reference.py (the
model's own mirrored / garbled lettering is flattened in fix_shape.py or covered here).

GTE lettering in the period decal style (anglia_side / redgte photos): wide letters built from bars - G with a
rounded left side and a spur, T = top bar + stem, E = three bars. Door decals: light-grey outline letters (two-line
style of the photos) laid on the doors; grille and rear badges: solid chrome letters 2.5 mm proud.
Number plates: flat plates in front of the recesses with tools/make_plates.py textures (made-up registration).
Car frame: x+ = car's left, y- = front, z up.
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TEX = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\tex"
BAR, GAP, SPACE = 0.30, 0.05, 0.30          # bar height, gap (letter height 1), letter spacing
WG, WT, WE, STEM = 1.90, 1.60, 1.55, 0.42    # letter widths, T stem width
STEP = 0.004                                  # boundary point spacing in metres (decals follow the panel)


def _arc(cx, cz, r, a0, a1, n=10):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def gte_polys():
    """Letter outlines (counter-clockwise, letter height 1) and the total width."""
    P = []
    t = BAR
    # G: rounded-left block with the C opening and a spur at mid height (top-right, along the top, round the left,
    # along the bottom, up the right to the spur, then back round the inside)
    g = [(WG, 1.0)] + _arc(0.5, 0.5, 0.5, 90, 270) + [(WG, 0.0), (WG, 0.56), (WG * 0.55, 0.56), (WG * 0.55, 0.42),
                                                      (WG - t, 0.42), (WG - t, t)]
    g += _arc(0.5, 0.5, 0.5 - t, 270, 90) + [(WG, 1 - t)]
    P.append(g)
    x0 = WG + SPACE
    rect = lambda a, b, c, d: [(a, b), (c, b), (c, d), (a, d)]
    P.append(rect(x0, 1 - BAR, x0 + WT, 1.0))                                           # T bar
    P.append(rect(x0 + (WT - STEM) / 2, 0.0, x0 + (WT + STEM) / 2, 1 - BAR - GAP))     # T stem
    x0 += WT + SPACE
    mid = (1 - BAR) / 2
    P.append(rect(x0, 1 - BAR, x0 + WE, 1.0))                                           # E bars
    P.append(rect(x0, mid, x0 + WE * 0.86, mid + BAR))
    P.append(rect(x0, 0.0, x0 + WE, BAR))
    return P, x0 + WE


def _densify(poly, step):
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        n = max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    return out


def lettering(name, origin, s_dir, n_dir, L, H, mat, bvh=None, off=0.0004, depth=0.0, outline=0.0):
    """GTE letters L long, H high; origin = bottom-left of the text, s_dir = reading direction, n_dir = outward.
    With bvh the letters are laid on the surface (projected along -n_dir) `off` proud; outline > 0 keeps only a ring
    of that width round each letter part (decal outlines); depth > 0 extrudes solid letters outwards."""
    s_dir, n_dir = Vector(s_dir).normalized(), Vector(n_dir).normalized()
    t_dir = n_dir.cross(s_dir).normalized()
    polys, W = gte_polys()
    ks, kt = L / W, H
    bm = bmesh.new()
    for poly in polys:
        pts = _densify([(x * ks, z * kt) for x, z in poly], STEP)
        vs = [bm.verts.new(Vector(origin) + s_dir * a + t_dir * b) for a, b in pts]
        f = bm.faces.new(vs)
        f.normal_update()
        if f.normal.dot(n_dir) < 0:
            f.normal_flip()
        if outline > 0:
            r = bmesh.ops.inset_individual(bm, faces=[f], thickness=outline, use_even_offset=True)
            bmesh.ops.delete(bm, geom=[f], context="FACES")
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    if bvh is not None:
        for v in bm.verts:
            hit = bvh.ray_cast(v.co + n_dir * 0.30, -n_dir, 0.60)
            if hit[0] is not None:
                v.co = hit[0] + n_dir * off
    if depth > 0:
        r = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
        bmesh.ops.translate(bm, vec=n_dir * depth, verts=[e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = False
    return _object(name, bm, [mat])


def _object(name, bm, mats):
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


def _material(name, base, preset, tex=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Roughness"].default_value = 0.4
    m.diffuse_color = (*base, 1)
    m["ac_shader"] = "ksPerPixelMultiMap"; m["ac_preset"] = preset
    if tex:
        m["ac_tex"] = json.dumps({"DIFFUSE": tex})
        img = bpy.data.images.load(tex, check_existing=True)
        img.colorspace_settings.name = "Non-Color"      # bytes as AC reads them (same as the flat colour swatches)
        tx = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None) or nt.nodes.new("ShaderNodeTexImage")
        tx.image = img
        nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    return m


def plate(name, centre, s_dir, n_dir, size, tex, base):
    """Flat textured plate, u along s_dir (reading direction), v up."""
    s_dir, n_dir = Vector(s_dir).normalized(), Vector(n_dir).normalized()
    t_dir = n_dir.cross(s_dir).normalized()
    w, h = size
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    c = Vector(centre)
    vs = [bm.verts.new(c + s_dir * (a * w / 2) + t_dir * (b * h / 2)) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uvl].uv = uv
    f.normal_update()
    if f.normal.dot(n_dir) < 0:
        raise ValueError("plate faces inwards")
    return _object(name, bm, [_material(name.lower() + "_mat", base, "trim", tex)])


LAMPS = {   # object: (material, face test on centres) - names used by data/lights.ini and extension/ext_config.ini
    "DET_LAMP_HEAD": ("lamp_clear", lambda x, y, z: y < 0),
    "DET_LAMP_REV": ("lamp_clear", lambda x, y, z: y > 1.4),
    "DET_LAMP_TAIL": ("lamp_red", lambda x, y, z: (y > 1.4) & (z > 0.751)),            # upper red band: tail light
    "DET_LAMP_BRAKE": ("lamp_red", lambda x, y, z: (y > 1.4) & (z > 0.55) & (z <= 0.751)),  # lower red band: brake
    "DET_LAMP_FOG": ("lamp_red", lambda x, y, z: (y > 1.4) & (z < 0.45)),
    "DET_LAMP_IND_L": ("lamp_amber", lambda x, y, z: x > 0),
    "DET_LAMP_IND_R": ("lamp_amber", lambda x, y, z: x < 0),
}


def split_lamps():
    """Item 11: lamp faces out of REF_BODY into their own objects (lights.ini / CSP name meshes), custom normals kept.
    Vanilla AC cannot drive tail and brake on one mesh, so the red section is split: upper band tail, lower brake."""
    import numpy as np
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    mi = np.empty(n, np.int64); me.polygons.foreach_get("material_index", mi)
    names = [m.name for m in me.materials]
    nl = len(me.loops)
    L = np.empty(nl * 3, np.float32); me.corner_normals.foreach_get("vector", L); L = L.reshape(-1, 3)
    ls = np.empty(n, np.int64); me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(n, np.int64); me.polygons.foreach_get("loop_total", lt)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    cv = np.empty(nl, np.int64); me.loops.foreach_get("vertex_index", cv)
    taken = np.zeros(n, bool); out = {}
    for name, (mat, test) in LAMPS.items():
        sel = np.where((mi == names.index(mat)) & test(*C.T) & ~taken)[0]
        taken[sel] = True
        vids = np.unique(np.concatenate([cv[ls[f]:ls[f] + lt[f]] for f in sel]))
        remap = {int(v): k for k, v in enumerate(vids)}
        lme = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
        lme.clear_geometry()
        lme.from_pydata(co[vids].tolist(), [], [[remap[int(v)] for v in cv[ls[f]:ls[f] + lt[f]]] for f in sel])
        lme.materials.clear(); lme.materials.append(bpy.data.materials[mat])
        lme.polygons.foreach_set("use_smooth", [True] * len(sel))
        lme.normals_split_custom_set(np.concatenate([L[ls[f]:ls[f] + lt[f]] for f in sel]))
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old)
        lo = bpy.data.objects.new(name, lme); bpy.data.collections["REF"].objects.link(lo)
        lo["kn5_dummy_name"] = name + "_DUMMY"
        out[name] = len(sel)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(f)] for f in np.where(taken)[0]], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    return out


def main():
    o = bpy.data.objects["REF_BODY"]
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    grey = _material("decal_grey", (0.60, 0.60, 0.62), "trim")
    chrome = bpy.data.materials["chrome"]
    out = {}
    # door decals (cS: y -0.647..-0.376, z 0.457..0.504 on the right door; mirrored on the left), reading front -> rear
    # on the left side and rear -> front on the right, as seen from that side
    L, H, z0 = 0.271, 0.047, 0.457
    out["door_L"] = len(lettering("DET_DECAL_L", (0.80, -0.647, z0), (0, 1, 0), (1, 0, 0), L, H, grey, bvh,
                                  outline=0.0032).data.polygons)
    out["door_R"] = len(lettering("DET_DECAL_R", (-0.80, -0.376, z0), (0, -1, 0), (-1, 0, 0), L, H, grey, bvh,
                                  outline=0.0032).data.polygons)
    # rear badge (top left of the black panel seen from behind: car's left), x 0.36..0.54, z 0.762..0.798
    out["badge_rear"] = len(lettering("DET_BADGE_R", (0.54, 1.80, 0.762), (-1, 0, 0), (0, 1, 0), 0.18, 0.036, chrome,
                                      bvh, depth=0.0025).data.polygons)
    # grille badge: on the grille front, x -0.08..0.08, z 0.567..0.605
    hit = bvh.ray_cast(Vector((0, -2.5, 0.586)), Vector((0, 1, 0)), 2.0)
    yg = hit[0].y - 0.003
    out["badge_grille"] = len(lettering("DET_BADGE_F", (-0.08, yg, 0.567), (1, 0, 0), (0, -1, 0), 0.16, 0.038, chrome,
                                        None, depth=0.0025).data.polygons)
    # number plates (scans: front plate plane y -1.8345 with letters 6.4 mm proud; rear plane y = 1.7404 - 0.0515 z,
    # letters 7.3 mm proud) - 1 mm clear of the old letters, 500 x 120 mm (fills the recess)
    plate("DET_PLATE_F", (0, -1.8345 - 0.0075, 0.390), (1, 0, 0), (0, -1, 0), (0.50, 0.120),
          os.path.join(TEX, "plate_front.png"), (0.85, 0.85, 0.82))
    nr = Vector((0, 1, 0.0515)).normalized()
    zc = 0.687
    plate("DET_PLATE_R", Vector((0, 1.7404 - 0.0515 * zc, zc)) + nr * 0.0083, (-1, 0, 0), nr, (0.50, 0.120),
          os.path.join(TEX, "plate_rear.png"), (0.80, 0.60, 0.03))
    out["grille_y"] = round(yg, 4)
    out["lamps"] = split_lamps()
    return out


if __name__ == "__main__":
    print("==", main())
