"""Nik 25 Nov: flames should come from one cylinder's stack at a time, not all 4 per side at once.
KK_flame_L1..3 / R1..3 (one mesh per side and length, a flame on each of that side's 4 stacks) are split per stack:
KK_flame_L{c}_{k} / KK_flame_R{c}_{k}, c = stack 1..4 front to back, k = length 1..3 (24 meshes, same KK_flame material,
same flags: active 0 = hidden until exhaust_flames.lua shows one). Faces are given to the stack nearest in Blender y.
No new textures/materials. Usage: blender -b in.blend --python kk15m_flames_per_cyl.py -- out.blend"""
import json, sys
import bmesh, bpy
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main
YS = (-1.46, -1.36, -1.26, -1.16)                      # stack exits, front to back (kk15d_zoomies_v11)
made = []
for tag in ("L", "R"):
    for k in (1, 2, 3):
        src = next(o for o in main.objects if o.type == "MESH" and o.name == f"KK_flame_{tag}{k}")
        mw = src.matrix_world
        for c, y in enumerate(YS, 1):
            ob = src.copy(); ob.data = src.data.copy(); ob.name = ob.data.name = f"KK_flame_{tag}{c}_{k}"
            for col in src.users_collection:
                col.objects.link(ob)
            bm = bmesh.new(); bm.from_mesh(ob.data)
            drop = [f for f in bm.faces if min(range(4), key=lambda i: abs((mw @ f.calc_center_median()).y - YS[i])) != c - 1]
            bmesh.ops.delete(bm, geom=drop, context="FACES")
            bm.to_mesh(ob.data); bm.free()
            ob["kn5_flags"] = src["kn5_flags"]
            made.append((ob.name, len(ob.data.polygons)))
        bpy.data.objects.remove(src)
assert all(n == 6 for _, n in made), made                 # 3 crossed quads x 2 sides per flame
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
print("REPORT", len(made), made[:3])
