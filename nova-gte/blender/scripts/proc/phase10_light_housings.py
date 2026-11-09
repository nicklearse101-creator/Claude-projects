"""Phase 10 - procedural Nova GTE: light housings and grille recess (Nik's Phase 10 spec, 2026-10-20).

Targets the 3D pieces built from the Side_Profile_Hood / Side_Profile_Tailgate templates (objects Hood and
Tailgate; the 2D templates stay the rebuild references):
 1. Front: on the vertical fascia of the Hood (the grille / headlamp face between the front_bumper_top and
    headlamp_top rows) bounding boxes give the left headlight block (outer rectangle) and the centre grille block.
    bpy.ops.mesh.inset() sets the body frame round each, the inset faces are extruded straight back (+Y, into the
    engine bay) by FRONT_DEPTH = cavities for the grille mesh and the headlamp lenses.
 2. Rear: on the flat rear panel of the Tailgate (crease below the rear glass -> bumper top) a bounding box gives the
    vertical taillight block at the outer corner; inset = body lip, extruded forward (-Y, into the boot) by
    REAR_DEPTH = taillight housings.
 3. The cavity back faces are duplicated and separated into Housing_Headlight_Left, Housing_Grille and
    Housing_Taillight_Left (reference placeholders, mirrored like the body).
 4. The edits run on the full (mirrored) mesh so the grille, which crosses the centre line, is inset as ONE region
    (no frame / tear along x = 0); then the mesh is cut back to x >= 0 and the Mirror modifier (X, clipping, merge)
    regenerates the right side. Hygiene: remove_doubles(0.0001) + normals_make_consistent(inside=False).
Bounding boxes from Nik's grey pictures (172 px/m; front.png centre u 164.4, rear.png centre u 155.5,
rear z = (237.5 - v) / 158.6):
  headlight (incl. indicator) u 42.5..89.5  -> |x| 0.435 .. body edge   (both sides: 0.432 / 0.435)
  grille                      u 91.3..237.5 -> |x| <= 0.425
  taillight                   u 33.8..55.5, v 107.5..150 -> |x| 0.581 .. body edge, z bumper top .. 0.820
  heights of the front blocks: the whole fascia band (lamps and grille fill it on the picture).
Phases 4-9 are re-run first (phase9_proportions.main) so the script always starts from the clean body.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase10_light_housings.py   (saves)"""
import contextlib
import io
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_front_block as p4      # noqa: E402
import phase9_proportions as p9      # noqa: E402

NovaSpecError = p4.NovaSpecError
FRONT_DEPTH = 0.08          # headlight / grille cavities, straight back along +Y
REAR_DEPTH = 0.05           # taillight housings, forward along -Y
INSET = 0.010               # body frame / lip round each opening
GRILLE_X = 0.425            # grille block |x| <= this
HEAD_X = 0.435              # headlight block |x| >= this (to the body edge)
TAIL_X = 0.581              # taillight block |x| >= this (to the body edge)
TAIL_Z_TOP = 0.820          # taillight block top (bottom = rear bumper top row)
HOUSINGS = ("Housing_Headlight_Left", "Housing_Grille", "Housing_Taillight_Left")


def rows(template):
    return {p[0]: (p[1], p[2]) for p in p4.template_chain(template)[0]}


def ops_ctx():
    """Context override with a 3D view if the UI has one (headless runs need none)."""
    win = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
    if win:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                reg = [r for r in area.regions if r.type == "WINDOW"][0]
                return bpy.context.temp_override(window=win, area=area, region=reg)
    return contextlib.nullcontext()


def full_mesh(ob):
    """Write the mirrored (both sides) mesh into the object's data, consistent outward normals kept."""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.normal_update()
    ref = {f.calc_center_median().freeze(): f.normal.copy() for f in bm.faces}
    bmesh.ops.mirror(bm, geom=list(bm.faces) + list(bm.edges) + list(bm.verts), axis="X", merge_dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.normal_update()
    agree = sum(f.normal.dot(ref[c]) for f in bm.faces for c in [f.calc_center_median().freeze()] if c in ref)
    if agree < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def bisect(bm, faces, co, no):
    geom = set(faces) | {e for f in faces for e in f.edges} | {v for f in faces for v in f.verts}
    bmesh.ops.bisect_plane(bm, geom=list(geom), plane_co=co, plane_no=no, dist=1e-6)


def merge_near_corners(bm, faces, corners, r):
    """Box corners (x, z) on the cut lines: a vertex of the band lying on the same cut line within r of a corner
    (an old grid line crossing the box edge right next to the corner) is merged into the corner vertex, so the
    inset frame cannot fold there. Returns the number merged."""
    vs = {v for f in faces for v in f.verts}
    n = 0
    for cx, cz in corners:
        c = [v for v in vs if v.is_valid and abs(v.co.x - cx) < 1e-6 and abs(v.co.z - cz) < 1e-6]
        if not c:
            continue
        near = [v for v in vs if v.is_valid and v is not c[0] and (v.co - c[0].co).length < r
                and (abs(v.co.x - cx) < 1e-6 or abs(v.co.z - cz) < 1e-6)]
        for v in near:
            bmesh.ops.pointmerge(bm, verts=[c[0], v], merge_co=c[0].co.copy())
            n += 1
    return n


def half_back(bm):
    """Cut back to x >= 0, centre seam exactly on x = 0."""
    bmesh.ops.bisect_plane(bm, geom=list(bm.faces) + list(bm.edges) + list(bm.verts), plane_co=(0, 0, 0),
                           plane_no=(1, 0, 0), clear_inner=True, dist=1e-6)
    for v in bm.verts:
        if abs(v.co.x) < 1e-5:
            v.co.x = 0.0


def add_mirror(ob):
    m = ob.modifiers.get("Mirror_X") or ob.modifiers.new("Mirror_X", "MIRROR")
    m.use_axis = (True, False, False); m.use_clip = True; m.use_mirror_merge = True; m.merge_threshold = 0.0001
    m.show_viewport = True
    return m


def carve(ob, boxes, depth):
    """boxes: {name: test(centre) on the full mesh}. Edit mode: select the faces in the boxes, inset, extrude along Y
    by `depth`, duplicate the back faces and separate them. Returns {box name: [(back face verts)]} of the separated
    object (both sides, still mirrored) and that object."""
    ob.modifiers["Mirror_X"].show_viewport = False
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    ob.data.use_mirror_x = False
    with ops_ctx():
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.mesh.select_all(action="DESELECT")
        bm = bmesh.from_edit_mesh(ob.data)
        n_sel = {}
        for k, test in boxes.items():
            fs = [f for f in bm.faces if test(f.calc_center_median())]
            n_sel[k] = len(fs)
            for f in fs:
                f.select_set(True)
        bmesh.update_edit_mesh(ob.data)
        bpy.ops.mesh.inset(thickness=INSET, depth=0.0, use_even_offset=True, use_boundary=True,
                           use_relative_offset=False, use_individual=False)
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0.0, depth, 0.0),
                                                                  "orient_type": "GLOBAL"})
        bpy.ops.mesh.duplicate()
        before = set(bpy.data.objects)
        bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")
    new = [o for o in bpy.data.objects if o not in before]
    if len(new) != 1:
        raise NovaSpecError("%s: separate gave %d objects" % (ob.name, len(new)))
    return new[0], n_sel


def split_housing(src, name, test, coll, outward_y):
    """Faces of `src` passing test(centre) -> object `name`, cut back to x >= 0, mirrored, normals facing outward_y."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    bm = bmesh.new(); bm.from_mesh(src.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not test(f.calc_center_median())], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    half_back(bm)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = (0, 0, 0)
    ob["nova_housing"] = 1
    p4.clean_mesh(ob)
    me.update()
    if sum(p.normal.y * p.area for p in me.polygons) * outward_y < 0:
        me.flip_normals()
    add_mirror(ob)
    return ob


def restore_half(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    half_back(bm)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    add_mirror(ob)
    p4.clean_mesh(ob)


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        p9.main()
    if "RESULT: PASS" not in buf.getvalue():
        raise NovaSpecError("phase 9 rebuild did not pass")
    O = bpy.data.objects
    coll = bpy.data.collections["NOVA_PROC"]
    H, T = rows("Side_Profile_Hood"), rows("Side_Profile_Tailgate")
    zf0, zf1 = H["front_bumper_top"][1], H["headlamp_top"][1]          # front fascia band
    zr0 = T["rear_bumper_top"][1]                                       # rear panel: bumper top .. crease
    zr1 = T["tailgate_lower"][1]
    orig = {}
    for n in ("Hood", "Tailgate"):
        bm0 = bmesh.new(); bm0.from_mesh(O[n].data)
        orig[n] = {"tree": BVHTree.FromBMesh(bm0), "bounds": bound_length(bm0)}; bm0.free()
    # ---------------- front
    hood = O["Hood"]
    bm = full_mesh(hood)
    face = lambda c: c.y < -1.70 and zf0 + 1e-4 < c.z < zf1 - 1e-4          # the grille / headlamp face band
    band = [f for f in bm.faces if face(f.calc_center_median())]
    if not band:
        raise NovaSpecError("Hood: no faces in the fascia band")
    for x in (GRILLE_X, HEAD_X):
        for s in (1, -1):
            bisect(bm, [f for f in bm.faces if face(f.calc_center_median())], (s * x, 0, 0), (1, 0, 0))
    bm.to_mesh(hood.data); bm.free(); hood.data.update()
    front_boxes = {
        "headlight": lambda c: face(c) and abs(c.x) > HEAD_X,
        "grille": lambda c: face(c) and abs(c.x) < GRILLE_X,
    }
    sep_f, sel_f = carve(hood, front_boxes, FRONT_DEPTH)
    hl = split_housing(sep_f, "Housing_Headlight_Left", lambda c: abs(c.x) > HEAD_X, coll, -1)
    gr = split_housing(sep_f, "Housing_Grille", lambda c: abs(c.x) < GRILLE_X, coll, -1)
    bpy.data.objects.remove(sep_f)
    restore_half(hood)
    # ---------------- rear
    tg = O["Tailgate"]
    bm = full_mesh(tg)
    panel = lambda c: c.y > 1.74 and zr0 + 1e-4 < c.z < zr1 - 1e-4          # flat rear panel below the crease
    for s in (1, -1):
        bisect(bm, [f for f in bm.faces if panel(f.calc_center_median())], (s * TAIL_X, 0, 0), (1, 0, 0))
    bisect(bm, [f for f in bm.faces if panel(f.calc_center_median())], (0, 0, TAIL_Z_TOP), (0, 0, 1))
    merged = merge_near_corners(bm, [f for f in bm.faces if f.calc_center_median().y > 1.74],
                                [(s * TAIL_X, z) for s in (1, -1) for z in (zr0, TAIL_Z_TOP)], 1.5 * INSET)
    bm.to_mesh(tg.data); bm.free(); tg.data.update()
    rear_boxes = {"taillight": lambda c: panel(c) and abs(c.x) > TAIL_X and c.z < TAIL_Z_TOP}
    sep_r, sel_r = carve(tg, rear_boxes, -REAR_DEPTH)
    tl = split_housing(sep_r, "Housing_Taillight_Left", lambda c: abs(c.x) > TAIL_X, coll, +1)
    bpy.data.objects.remove(sep_r)
    restore_half(tg)
    info = {"sel": {**sel_f, **sel_r}, "z": (zf0, zf1, zr0, zr1), "band_faces": len(band), "merged": merged}
    audit(orig, info)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


def bound_length(bm):
    """Total length of the open boundary of the half mesh, excluding the centre seam (x = 0)."""
    return sum(e.calc_length() for e in bm.edges if e.is_boundary and not all(abs(v.co.x) < 1e-6 for v in e.verts))


def audit(orig, info):
    O = bpy.data.objects
    rows_, bad = [], []

    def check(label, meas, spec, tol=0.001, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows_.append("%-66s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    dg = bpy.context.evaluated_depsgraph_get()
    zf0, zf1, zr0, zr1 = info["z"]
    for k, n in info["sel"].items():
        check("bounding box %s: faces selected (both sides)" % k, float(n > 0), 1.0)
    spec = {"Housing_Headlight_Left": ("Hood", FRONT_DEPTH, -1, lambda x: x > HEAD_X),
            "Housing_Grille": ("Hood", FRONT_DEPTH, -1, lambda x: x < GRILLE_X),
            "Housing_Taillight_Left": ("Tailgate", -REAR_DEPTH, +1, lambda x: x > TAIL_X)}
    for hn, (body, depth, oy, in_x) in spec.items():
        me = O[hn].data
        V = np.array([tuple(v.co) for v in me.vertices])
        # every back-face vertex = the original fascia surface moved by exactly the depth along Y
        off = max((Vector(p) - Vector((0, depth, 0)) - orig[body]["tree"].find_nearest(Vector(p) - Vector((0, depth, 0)))[0]).length
                  for p in V)
        check("%s: back face = fascia moved %+.2f m along Y (max err)" % (hn, depth), float(off), 0.0)
        check("%s: inside its bounding box (x range)" % hn, float(all(in_x(x) or x == 0.0 for x in V[:, 0])), 1.0)
        check("%s: normals face outward (%sY)" % (hn, "+" if oy > 0 else "-"),
              float(all(p.normal.y * oy > 0 for p in me.polygons)), 1.0)
        check("%s: degenerate faces" % hn, float(sum(1 for p in me.polygons if p.area < 1e-8)), 0.0)
        def folded(p):                       # bow-tie / non-convex: corner turns disagree with the face normal
            co = [me.vertices[i].co for i in p.vertices]
            return any((co[i] - co[i - 1]).cross(co[(i + 1) % len(co)] - co[i]).dot(p.normal) < -1e-12
                       for i in range(len(co)))
        check("%s: folded / non-convex faces" % hn, float(sum(1 for p in me.polygons if folded(p))), 0.0)
        m = O[hn].modifiers.get("Mirror_X")
        check("%s: mirror X + clipping + merge" % hn, float(bool(m) and m.use_axis[0] and m.use_clip and m.use_mirror_merge), 1.0)
        rows_.append("    %s: x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f  (%d faces)" % (
            hn, V[:, 0].min(), V[:, 0].max(), V[:, 1].min(), V[:, 1].max(), V[:, 2].min(), V[:, 2].max(), len(me.polygons)))
    # frame width: housing outline vs the bounding box edges it was inset from (in the fascia plane)
    hl = np.array([tuple(v.co) for v in O["Housing_Headlight_Left"].data.vertices])
    gr = np.array([tuple(v.co) for v in O["Housing_Grille"].data.vertices])
    tl = np.array([tuple(v.co) for v in O["Housing_Taillight_Left"].data.vertices])
    check("headlight frame: inner edge |x| - box edge = inset", float(hl[:, 0].min() - HEAD_X), INSET)
    check("grille frame: outer edge box edge - |x| = inset", float(GRILLE_X - gr[:, 0].max()), INSET)
    check("taillight frame: inner edge |x| - box edge = inset", float(tl[:, 0].min() - TAIL_X), INSET)
    check("taillight frame: top z below the box top by the inset", float(TAIL_Z_TOP - tl[:, 2].max()), INSET, tol=0.0015)
    rows_.append("    rear panel: %d old grid vertices merged into the taillight box corners" % info["merged"])
    check("grille: one region across the centre (housing reaches x = 0)", float(gr[:, 0].min()), 0.0, tol=1e-9)
    # grille at x = 0: no frame strip along the centre line - no body vertex on the centre seam inside the opening
    hood = O["Hood"].data
    seam_in = [v for v in hood.vertices if v.co.x == 0.0 and v.co.y < -1.70 and zf0 + INSET * 1.2 < v.co.z < zf1 - INSET * 1.2
               and orig["Hood"]["tree"].find_nearest(v.co)[3] < 1e-5]
    check("grille: no frame on the centre line inside the opening (verts)", float(len(seam_in)), 0.0)
    for n in ("Hood", "Tailgate") + HOUSINGS:
        ob = O[n]; me = ob.data
        X = np.array([v.co.x for v in me.vertices])
        seam = [v for v in me.vertices if abs(v.co.x) < 1e-5]
        check("%s: no vertex right of the centre line (min x >= 0)" % n, float(X.min()), 0.0, cmp="ge")
        check("%s: centre-seam vertices exactly x = 0" % n, float(max([abs(v.co.x) for v in seam] or [0.0])), 0.0, tol=1e-12)
        ev = ob.evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored verts = 2 x half - seam (no rip at x = 0)" % n, float(len(ev.vertices)),
              float(2 * len(me.vertices) - len(seam)))
        check("%s: mirrored symmetric (max x + min x)" % n, float(EX.max() + EX.min()), 0.0, tol=1e-6)
        ob.evaluated_get(dg).to_mesh_clear()
        bm = bmesh.new(); bm.from_mesh(me)
        check("%s: degenerate faces / zero edges" % n, float(sum(1 for f in bm.faces if f.calc_area() < 1e-9)
                                                          + sum(1 for e in bm.edges if e.calc_length() < 1e-6)), 0.0)
        check("%s: edges with > 2 faces" % n, float(sum(1 for e in bm.edges if len(e.link_faces) > 2)), 0.0)
        if n in orig:
            check("%s: open boundary unchanged (cavities closed, m)" % n, bound_length(bm), orig[n]["bounds"])
            # normals outward: the body faces still on the original surface keep their outward sense
            tr = orig[n]["tree"]
            flips = 0
            for f in bm.faces:
                c = f.calc_center_median(); hit = tr.find_nearest(c)
                if hit[3] < 1e-5 and f.normal.dot(hit[1]) < 0:
                    flips += 1
            check("%s: faces on the original surface keep outward normals (flipped)" % n, float(flips), 0.0)
        bm.free()
    print("NOVA GTE PHASE 10 - LIGHT HOUSINGS AND GRILLE RECESS VERIFICATION")
    print("%-66s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows_))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
