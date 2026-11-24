"""ESCORT 15" v7 (Nik 24 Nov: chrome stacks still looked wrong - "make the material same as the roll cage"):
KK_exhaust_pipes/tips -> the roll cage's Material #26DDDSA (ksPerPixelMultiMap on the AO_1 atlas). All their UVs are set
to the median UV of the cage tube mesh (rollcage_a_SUB5), so they pick up the cage's own colour / maps from the atlas.
Run on "escort15_v6.blend"; saves "escort15_v7.blend"."""
import json
import bpy, numpy as np
sc = bpy.data.scenes["Scene"]
cage = next(o for o in sc.objects if o.type == "MESH" and (o.get("kn5_name") or o.name) == "rollcage_a_SUB5")
uv = np.empty(len(cage.data.loops) * 2); cage.data.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
med = np.median(uv, axis=0)
mat = cage.material_slots[0].material
for n in ("KK_exhaust_pipes", "KK_exhaust_tips"):
    o = sc.objects[n]
    for i in range(len(o.material_slots)):
        o.material_slots[i].material = mat
    lay = o.data.uv_layers[0]
    lay.data.foreach_set("uv", np.tile(med, len(o.data.loops)))
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
names = [n for n in json.loads(sc["kn5_materials"]) if n != "KK_chrome"]   # chrome no longer used (purged on save)
sc["kn5_materials"] = json.dumps(names)
print("REPORT", mat.name, med.round(4).tolist())
bpy.ops.wm.save_as_mainfile(filepath=r"D:\Claude\escort_mk2_dtm\blender\escort15_v7.blend")
