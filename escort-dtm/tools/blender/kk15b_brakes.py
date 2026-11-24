"""ESCORT 15" v2 (Nik 24 Nov "do the brakes to match"): brake discs (for_rotorxx, under WHEEL_xx) and calipers
(for_caliperxx, under SUSP_xx) scaled 15/13 in the wheel plane about each hub - same thickness, calipers stay on the disc
edge with the same clearance to the (also 15/13) rim. Physics: brakes.ini MAX_TORQUE x15/13 (escort15_data.py).
Run on "escort15_v1.blend"; saves "escort15_v2.blend"."""
import json
import bpy, numpy as np
S = 15.0 / 13.0
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort15_v2.blend"
rep = {}
for sc in bpy.data.scenes:
    hubs = {}
    for w in ("LF", "RF", "LR", "RR"):
        r = next((o for o in sc.objects if (o.get("kn5_name") or o.name) == "WHEEL_" + w), None)
        if r:
            hubs[w] = np.array(r.matrix_world.translation)
    for o in sc.objects:
        if o.type != "MESH" or o.users_scene[0] != sc:
            continue
        name = (o.get("kn5_name") or o.name)
        low = name.lower()
        tag = next((w for w in hubs if f"rotor{w.lower()}" in low or f"caliper{w.lower()}" in low), None)
        if not tag:
            continue
        c = hubs[tag]
        if o.data.users > 1:
            o.data = o.data.copy()
        mw = np.array(o.matrix_world); inv = np.linalg.inv(mw)
        n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        wco = (np.c_[co, np.ones(n)] @ mw.T)[:, :3]
        wco[:, 1] = c[1] + (wco[:, 1] - c[1]) * S
        wco[:, 2] = c[2] + (wco[:, 2] - c[2]) * S
        o.data.vertices.foreach_set("co", ((np.c_[wco, np.ones(n)] @ inv.T)[:, :3]).ravel()); o.data.update()
        if "kn5_pristine" in o:
            o["kn5_pristine"] = False
        rep.setdefault(sc.name, []).append(name)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("REPORT", json.dumps({k: len(v) for k, v in rep.items()}), json.dumps(rep.get("Scene")))
