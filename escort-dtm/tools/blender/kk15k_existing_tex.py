"""Nik 24 Nov: the new engine still showed the M4/RaceLogic decal atlas (also on untouched parts) after the PNG -> DDS
switch - adding textures to this kn5 shifts the donor M4 textures and the game mixes them up. Nik: "just use textures like
the old engine". So: NO new textures. The 6 KK_* engine textures are dropped from kn5_textures and every engine material
points at textures the car already had:
  KK_redcrinkle  ksPerPixelNM   txDiffuse v8_red_d.dds (engine's red anodised) + v8_crinkle_nm.dds
  KK_alu_black   -> block uses v8_crinkle_black (engine's own black crinkle)
  heads etc      -> back to v8_cast_alu
  KK_polished    -> NICK3_alloy (bonnet-vent polished alloy, ksPerPixelMultiMap: UVs already non-degenerate)
  KK_yellow_lead ksPerPixel     txDiffuse KK_fog_lens_col.dds (existing flat yellow)
  KK_braid       ksPerPixel     txDiffuse v8_alu_d.dds
Usage: blender -b in.blend --python kk15k_existing_tex.py -- out.blend"""
import json, sys
import bpy
sc = bpy.data.scenes["Scene"]
NEW_TEX = ("KK_crinkle_red", "KK_alu_satinblack", "KK_alu_machined", "KK_polished", "KK_yellow", "KK_braid")


def bykn5(name):
    return next(m for m in bpy.data.materials if m.get("kn5_def") and json.loads(m["kn5_def"])["name"] == name)


def retex(mat, samplers):
    d = json.loads(mat["kn5_def"])
    d["samplers"] = [[s[0], s[1], samplers.get(s[0], s[2])] for s in d["samplers"]]
    mat["kn5_def"] = json.dumps(d)


retex(bpy.data.materials["KK_redcrinkle"], {"txDiffuse": "v8_red_d.dds"})
retex(bpy.data.materials["KK_yellow_lead"], {"txDiffuse": "KK_fog_lens_col.dds"})
retex(bpy.data.materials["KK_braid"], {"txDiffuse": "v8_alu_d.dds"})
swap = {"KK_V8_block": bykn5("v8_crinkle_black"), "V8_alloy": bykn5("v8_cast_alu"), "KK_itb_bodies": bykn5("v8_cast_alu"),
        "KK_itb_trumpets": bykn5("NICK3_alloy"), "KK_cam_lettering": bykn5("NICK3_alloy")}
for o in sc.objects:
    n = o.get("kn5_name") or o.name
    if o.type == "MESH" and n in swap:
        for i in range(len(o.material_slots)):
            o.material_slots[i].material = swap[n]
# drop the generated textures + now-unused materials from the kn5 lists
t = [x for x in json.loads(sc["kn5_textures"]) if not any(x["name"].startswith(p + ".") for p in NEW_TEX)]
sc["kn5_textures"] = json.dumps(t)
ml = [m for m in json.loads(sc["kn5_materials"]) if m not in ("KK_alu_black", "KK_alu_machined", "KK_polished")]
sc["kn5_materials"] = json.dumps(ml)
for m in bpy.data.materials:
    if m.get("kn5_def"):
        for s in json.loads(m["kn5_def"])["samplers"]:
            assert not any(s[2].startswith(p + ".") for p in NEW_TEX) or m.users == 0, (m.name, s)
print("REPORT textures", len(t), "materials", len(ml))
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
