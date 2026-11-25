"""Nik 25 Nov: on the horn the driver sticks his arm out of the window and gives the middle finger. The driver rig
(driver_70) has no finger bones - the hand is one gripping fist - so the car carries KK_finger: a glove-dark finger
(capsule, 18 mm thick, 80 mm long) built at the model origin along AC +Z (Blender -Y), hidden in the kn5 (active 0);
exhaust_flames.lua shows it and places it on the fist every frame while the horn is held.
Usage: blender -b in.blend --python kk15l_finger.py -- out.blend"""
import json, math, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main
root = next(o for o in main.objects if o.get("kn5_root")); col = bpy.data.collections["KADETT_KIT"]
dark = next(m for m in bpy.data.materials if m.get("kn5_def") and json.loads(m["kn5_def"])["name"] == "bumperFrame_radiator")
for o in [o for o in main.objects if o.name.startswith("KK_finger")]:
    bpy.data.objects.remove(o)
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
R, L, SEG = 0.009, 0.08, 12
axis = Vector((0, -1, 0))                      # AC +Z
prof = [(R * math.sin(math.radians(a)), -R * math.cos(math.radians(a))) for a in (0, 30, 60, 90)]          # rounded base
prof += [(R, 0.02), (R * 0.95, 0.045), (R * 0.9, L - R)]                                                     # finger (knuckle-ish taper)
prof += [(R * 0.9 * math.cos(math.radians(a)), L - R + R * 0.9 * math.sin(math.radians(a))) for a in (30, 60, 90)]   # tip
rings = []
for r, h in prof:
    c = axis * h
    rings.append([bm.verts.new(c + Vector((math.cos(t) * r, 0, math.sin(t) * r))) for t in np.linspace(0, 2 * math.pi, SEG, endpoint=False)])
for j in range(len(rings) - 1):
    for k in range(SEG):
        f = bm.faces.new((rings[j][k], rings[j][(k + 1) % SEG], rings[j + 1][(k + 1) % SEG], rings[j + 1][k]))
        f.normal_update()
        mid = axis * ((prof[j][1] + prof[j + 1][1]) / 2)
        if f.normal.dot(f.calc_center_median() - mid) < 0:
            f.normal_flip()
        for lp in f.loops:
            lp[uvl].uv = (0.5 + 0.01 * k / SEG, 0.5 + 0.01 * j / len(rings))
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
me = bpy.data.meshes.new("KK_finger"); bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
ob = bpy.data.objects.new("KK_finger", me); kb.set_material(ob, dark); kb.link(ob, main, root, col)
ob.matrix_world = root.matrix_world.copy()
ob["kn5_flags"] = json.dumps({"active": 0, "cast": 1, "visible": 1, "transparent": 0, "renderable": 1})
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
print("REPORT finger", len(me.polygons))
