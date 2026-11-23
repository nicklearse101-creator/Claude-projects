"""v49d: the v49 boolean arch cut left long sliver triangles that poked out behind the rear arches in game -> delete every sliver
(longest edge > 4 cm, area/L^2 < 0.02) of fenders_a_SUB2 / body_a_SUB1 inside the arch zones (|x| > 0.55, within 0.75 m of a wheel)."""
import sys, bpy, bmesh
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
main = bpy.data.scenes["Scene"]
rep = {}
for name in ("fenders_a_SUB2", "body_a_SUB1"):
    o = next(o for o in main.objects if o.type == "MESH" and o.get("kn5_name") == name)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    mw = o.matrix_world
    bad = []
    for f in bm.faces:
        c = mw @ f.calc_center_median()
        if abs(c.x) < 0.55 or not any(abs(c.y - wy) < 0.75 for wy in (kb.E_F[0], kb.E_R[0])):
            continue
        L = max(((mw @ e.verts[0].co) - (mw @ e.verts[1].co)).length for e in f.edges)
        if L > 0.04 and f.calc_area() * (mw.to_scale().x ** 2) / (L * L) < 0.02:
            bad.append(f)
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data); bm.free(); rep[name] = len(bad)
print("REPORT", rep)
bpy.ops.wm.save_mainfile()
