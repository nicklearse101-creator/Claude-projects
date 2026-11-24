"""ESCORT 15" v7 (Nik 24 Nov: chrome stacks looked wrong - "make the material same as the roll cage"):
KK_exhaust_pipes/tips -> the roll cage's Material #26DDDSA (ksPerPixelMultiMap, AO_1 atlas); collars/soot (KK_exhaust_dark)
keep the bumper black #166GG45.
UVs: the stacks kept rendering black because a normal-mapped shader needs non-degenerate UVs for tangents - constant UVs
(v7a) or none (v5) give NaN tangents = black. So every part gets its own cylindrical/planar UVs squeezed into a tiny patch
(~4 mm of atlas) around a sample of its material's own mesh (cage tube / front bumper), i.e. that mesh's colour, with
valid tangents. Run on "escort15_v6.blend"; saves "escort15_v7.blend"."""
import json
import bpy, numpy as np
sc = bpy.data.scenes["Scene"]
PATCH = 0.004


def median_uv(name):
    o = next(o for o in sc.objects if o.type == "MESH" and (o.get("kn5_name") or o.name) == name)
    uv = np.empty(len(o.data.loops) * 2); o.data.uv_layers[0].data.foreach_get("uv", uv)
    return o, np.median(uv.reshape(-1, 2), axis=0)


cage, cmed = median_uv("rollcage_a_SUB5")
bump, bmed = median_uv("bumperf_a_SUB1")
for n, mat, med in (("KK_exhaust_pipes", cage.material_slots[0].material, cmed),
                    ("KK_exhaust_tips", cage.material_slots[0].material, cmed),
                    ("KK_exhaust_dark", bump.material_slots[0].material, bmed)):
    o = sc.objects[n]
    for i in range(len(o.material_slots)):
        o.material_slots[i].material = mat
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    lay = me.uv_layers[0]
    if n == "KK_exhaust_dark":                       # discs: planar from position
        co = np.array([me.vertices[l.vertex_index].co[:] for l in me.loops])
        a, b = co[:, 0], co[:, 1] + co[:, 2]
        uv = np.c_[(a - a.min()) / max(np.ptp(a), 1e-6), (b - b.min()) / max(np.ptp(b), 1e-6)]
    else:                                            # tubes: their own cylindrical UVs (u 0..1 around, v along)
        uv = np.empty(len(me.loops) * 2); lay.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
        uv[:, 1] = (uv[:, 1] - uv[:, 1].min()) / max(np.ptp(uv[:, 1]), 1e-6)
    lay.data.foreach_set("uv", (med + (uv - 0.5) * PATCH).ravel())
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
names = [n for n in json.loads(sc["kn5_materials"]) if n != "KK_chrome"]   # chrome no longer used (purged on save)
sc["kn5_materials"] = json.dumps(names)
print("REPORT cage", cmed.round(4).tolist(), "bumper", bmed.round(4).tolist())
bpy.ops.wm.save_as_mainfile(filepath=r"D:\Claude\escort_mk2_dtm\blender\escort15_v7.blend")
