"""ESCORT 15" v8 (Nik 24 Nov: "remove the doors and put a cross across the door attached to the rollcage" - backup kept:
D:/ClaudeData/tmp/kadett/BACKUP_15in_before_doorless_*, blend escort15_v7):
  - DOOR_L / DOOR_R nodes (skin, glass, trims, door cards, handles, inner panels) switched off (kn5 active 0) - not deleted
  - KK_door_bars: an X of 42 mm tube in each door opening, welded to the cage: A-pillar leg (line (0.60,-0.81,0.05) ->
    (0.59,-0.43,0.75)) at z 0.20 / 0.62 to the main-hoop leg (x 0.60, y ~0.51) at z 0.15 / 0.62; roll cage material
    (Material #26DDDSA) with real UVs in a tiny atlas patch at the cage tube's median UV (valid tangents).
Run on "escort15_v7.blend"; saves "escort15_v8.blend"."""
import json, math, sys
import bmesh, bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb

OUT = r"D:\Claude\escort_mk2_dtm\blender\escort15_v8.blend"
R = 0.021
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main
A0, A1 = Vector((0.60, -0.81, 0.05)), Vector((0.59, -0.43, 0.75))
on_a = lambda z: A0 + (A1 - A0) * ((z - A0.z) / (A1.z - A0.z))
HOOP = lambda z: Vector((0.598, 0.51 + 0.04 * max(0, z - 0.5), z))

off = []
for sc in bpy.data.scenes:
    for o in sc.objects:
        if (o.get("kn5_name") or o.name) in ("DOOR_L", "DOOR_R") and "kn5_flags" in o:
            fl = json.loads(o["kn5_flags"]); fl["active"] = 0; o["kn5_flags"] = json.dumps(fl); off.append(sc.name + ":" + o.name)
        elif (o.get("kn5_name") or o.name) in ("DOOR_L", "DOOR_R"):
            o["kn5_flags"] = json.dumps({"active": 0}); off.append(sc.name + ":" + o.name)

cage = next(o for o in main.objects if o.type == "MESH" and (o.get("kn5_name") or o.name) == "rollcage_a_SUB5")
uv = np.empty(len(cage.data.loops) * 2); cage.data.uv_layers[0].data.foreach_get("uv", uv)
med = np.median(uv.reshape(-1, 2), axis=0); mat = cage.material_slots[0].material

bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")


def bar(p0, p1, seg=16, n=6):
    t = (p1 - p0).normalized(); ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 0, 1))
    nrm = t.cross(ref).normalized(); bi = t.cross(nrm)
    rings = [[bm.verts.new(p0 + (p1 - p0) * (i / n) + (nrm * math.cos(a) + bi * math.sin(a)) * R)
              for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)] for i in range(n + 1)]
    for j in range(n):
        for k in range(seg):
            f = bm.faces.new((rings[j][k], rings[j][(k + 1) % seg], rings[j + 1][(k + 1) % seg], rings[j + 1][k]))
            f.normal_update()
            if f.normal.dot(f.calc_center_median() - (p0 + (p1 - p0) * ((j + 0.5) / n))) < 0:
                f.normal_flip()
            for lp in f.loops:
                kk = rings[j].index(lp.vert) if lp.vert in rings[j] else rings[j + 1].index(lp.vert)
                jj = j if lp.vert in rings[j] else j + 1
                lp[uvl].uv = (med[0] + (kk / seg - 0.5) * 0.004, med[1] + (jj / n - 0.5) * 0.004)


for s in (1, -1):
    m = lambda v: Vector((s * v.x, v.y, v.z))
    # ends sunk 15 mm into the cage tubes so the joints look welded
    for a, b in ((on_a(0.20), HOOP(0.62)), (on_a(0.62), HOOP(0.15))):
        d = (b - a).normalized()
        bar(m(a - d * 0.015), m(b + d * 0.015))
me = bpy.data.meshes.new("KK_door_bars"); bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
ob = bpy.data.objects.new("KK_door_bars", me); kb.set_material(ob, mat)
root = next(o for o in main.objects if o.get("kn5_root"))
kb.link(ob, main, root, bpy.data.collections["KADETT_KIT"])
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT off", off, "bars", len(me.polygons), "front ends", [round(v, 3) for v in on_a(0.20)], [round(v, 3) for v in on_a(0.62)])
