"""ESCORT 16" v2 (Nik 24 Nov): tyres (and rims) back to the 14in car's widths - every mesh under the WHEEL_xx nodes scaled
x14/16 across the car (world x) about the hub; diameter stays 16in. Run on "escort16_v1.blend"; saves "escort16_v2.blend"."""
import json, sys
import bpy, numpy as np
from mathutils import Vector
SX = 14.0 / 16.0          # widths back to the 14in car, diameter stays 16in
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort16_v2.blend"
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
            wco[:, 0] = c[0] + (wco[:, 0] - c[0]) * SX
            o.data.vertices.foreach_set("co", ((np.c_[wco, np.ones(n)] @ inv.T)[:, :3]).ravel()); o.data.update()
            if "kn5_pristine" in o:
                o["kn5_pristine"] = False
            rep.setdefault(sc.name + ":" + w, []).append(o.get("kn5_name") or o.name)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps({k: len(v) for k, v in rep.items()}), json.dumps(rep.get("Scene:WHEEL_LF")))
