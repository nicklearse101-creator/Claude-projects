"""ESCORT 15" v9 (Nik 24 Nov, doorless: "some of the window frame is still there - only when you look from inside"):
the cockpit-only mesh dashstructure_a_SUB0 (COCKPIT_HR) carries the door quarter-light frame: a vertical post at y ~-0.16
and the diagonal to the front. Delete those islands (both sides, + the low-res copy): islands whose whole bbox lies inside the
window aperture (|x| 0.5-0.70, y -0.52..-0.12, z 0.64..1.04) and don't touch the aperture seal (z min > 0.6).
Usage: blender -b escort15_v8.blend --python kk15g_quarterlight.py -- <out.blend>"""
import json, sys
import bmesh, bpy, numpy as np
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_build as kb
OUT = sys.argv[-1]
sc = bpy.data.scenes["Scene"]
rep = {}
for o in [o for o in sc.objects if o.type == "MESH" and (o.get("kn5_name") or o.name) in ("dashstructure_a_SUB0", "dashstructure_a_SUB0__lr")]:
    co = kb.world_co(o); r = kb.islands(o.data); drop = np.zeros(len(co), bool); hit = []
    for k in np.unique(r):
        p = co[r == k]; ax = np.abs(p[:, 0])
        if ax.min() > 0.5 and ax.max() < 0.70 and p[:, 1].min() > -0.52 and p[:, 1].max() < -0.12 and p[:, 2].min() > 0.64 and p[:, 2].max() < 1.04:
            drop[r == k] = True; hit.append(int(k))
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if drop[v.index]], context="VERTS")
    bm.to_mesh(o.data); bm.free()
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
    rep[o.get("kn5_name") or o.name] = (len(hit), int(drop.sum()), hit)
print("REPORT", json.dumps(rep))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
