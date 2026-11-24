"""Nik 24 Nov: "make this shiny back strip normal body colour". The strip is the rear-facing lower part of trunk_a_SUB0 (body
paint material); the skins paint its AO_BODY area dark (my_skin 50,24,0 vs lid 200,100,2), which with the paint's
reflection reads as chrome. Its UVs are re-pointed (planar, x/z) into a 2 % patch of the boot-lid top's UV area, so it takes
the lid's colour on every skin. ESCORT letters (trunk_a_SUB1) and the Ford badge are separate meshes - unchanged.
Usage: blender -b in.blend --python kk15j_rearstrip.py -- out.blend"""
import json, sys
import bpy, numpy as np
sc = bpy.data.scenes["Scene"]
PATCH = 0.008
LID = (0.8744, 0.4688)          # plainest lid spot matching each skin's lid colour (checked on my_skin, 00_nicks_hillclimb, nik)
o = next(o for o in sc.objects if o.type == "MESH" and (o.get("kn5_name") or o.name) == "trunk_a_SUB0")
me = o.data; mw = o.matrix_world; uv = me.uv_layers[0].data; r3 = mw.to_3x3()
strip, top = [], []
for p in me.polygons:
    n = (r3 @ p.normal).normalized(); c = mw @ p.center
    if n.y > 0.8 and c.z < 0.56:
        strip.append(p)
    elif n.z > 0.6:
        top.append(p)
lid = np.array(LID)
pts = np.array([(mw @ me.vertices[me.loops[l].vertex_index].co)[:] for p in strip for l in p.loop_indices])
x0, x1, z0, z1 = pts[:, 0].min(), pts[:, 0].max(), pts[:, 2].min(), pts[:, 2].max()
for p in strip:
    for l in p.loop_indices:
        w = mw @ me.vertices[me.loops[l].vertex_index].co
        uv[l].uv = (lid[0] + ((w.x - x0) / (x1 - x0) - 0.5) * PATCH, lid[1] + ((w.z - z0) / (z1 - z0) - 0.5) * PATCH * 0.5)
if "kn5_pristine" in o:
    o["kn5_pristine"] = False
print("REPORT strip faces", len(strip), "lid uv", lid.round(4).tolist())
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
