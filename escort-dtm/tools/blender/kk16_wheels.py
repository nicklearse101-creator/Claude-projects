"""ESCORT 16" (separate car ford_escort_mk2_tuned_16, Nik 24 Nov, option 2): everything under each WHEEL_xx node (rim, rim
blur, tyre, brake disc) scaled 16/14 about the wheel node origin (= hub centre). Nothing else touched; AC positions the wheel
nodes from the physics (BASEY), so the lower wheel position comes from suspensions.ini, not from the model.
Run on "escort_v51 flames.blend"; saves "escort16_v1.blend" (the 14" blend is not modified)."""
import json, sys
import bpy, numpy as np
from mathutils import Vector
S = 16.0 / 14.0
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort16_v1.blend"
rep = {}
for sc in bpy.data.scenes:                                   # main + LOD scenes, if any
    for w in ("WHEEL_LF", "WHEEL_RF", "WHEEL_LR", "WHEEL_RR"):
        root = next((o for o in sc.objects if (o.get("kn5_name") or o.name) == w), None)
        if not root:
            continue
        c = np.array(root.matrix_world.translation)
        for o in root.children_recursive:
            if o.type != "MESH" or o.users_scene[0] != sc:
                continue
            if o.data.users > 1:
                o.data = o.data.copy()
            mw = np.array(o.matrix_world); inv = np.linalg.inv(mw)
            n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            wco = (np.c_[co, np.ones(n)] @ mw.T)[:, :3]
            wco = c + (wco - c) * S
            o.data.vertices.foreach_set("co", ((np.c_[wco, np.ones(n)] @ inv.T)[:, :3]).ravel()); o.data.update()
            if "kn5_pristine" in o:
                o["kn5_pristine"] = False
            rep.setdefault(sc.name + ":" + w, []).append(o.get("kn5_name") or o.name)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps({k: len(v) for k, v in rep.items()}), json.dumps(rep.get("Scene:WHEEL_LF")))
