"""v45 on the v41 model (Nik 23 Nov 08:32): body kit 5 mm in towards the body all round (x towards the centreline),
sill/arch vent fills black carbon (NICK3_carbon, like the diffuser) instead of the steel mesh. Nothing else changed.
Run on "escort_v41 kadett kit paint.blend"; saves "escort_v45 kit in 5mm carbon vents.blend", exports export_staging_v45."""
import json, sys
import bpy, numpy as np
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_finish as kf

SHIFT = 0.005
MOVE = ("KK_kit", "KK_kit_inner", "KK_fins", "KK_sill_mesh", "KK_sill_back", "KK_vent_mesh", "KK_vent_back", "KK_exhaust_dark")
CARBON = ("KK_sill_mesh", "KK_vent_mesh")
kf.STAGE = r"D:\Claude\escort_mk2_dtm\export_staging_v45"
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v45 kit in 5mm carbon vents.blend"

rep = {}
for tag, scn in kf.SCENES.items():
    sc = bpy.data.scenes[scn]
    mats = kf.mats_of(sc)
    carbon = mats.get("NICK3_carbon") or mats["Material #166GG45"]
    for o in sc.objects:
        if o.type != "MESH":
            continue
        base = o.name.split(".")[0]
        if base not in MOVE:
            continue
        mw = np.array(o.matrix_world); inv = np.linalg.inv(mw)
        me = o.data
        co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        w = co @ mw[:3, :3].T + mw[:3, 3]
        w[:, 0] -= np.sign(w[:, 0]) * SHIFT
        me.vertices.foreach_set("co", ((np.c_[w, np.ones(len(w))] @ inv.T)[:, :3]).ravel()); me.update()
        if base in CARBON:
            for i in range(len(o.material_slots)):
                o.material_slots[i].material = carbon
            uvl = me.uv_layers.active.data
            for lp, d in zip(me.loops, uvl):
                p = w[lp.vertex_index]
                d.uv = (p[1] * 1.0, p[2] * 1.0)
        rep.setdefault(tag, []).append(o.name)
bpy.context.window.scene = bpy.data.scenes["Scene"]
bpy.ops.wm.save_as_mainfile(filepath=OUT)
rep["export"] = kf.export_all()
print("REPORT", json.dumps(rep))
