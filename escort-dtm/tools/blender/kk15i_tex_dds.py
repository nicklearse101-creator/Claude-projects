"""Nik 24 Nov: the new engine textures showed the BMW/RaceLogic atlas in game although the kn5 references were right -
switch the 6 generated KK_*.png textures to DDS (like every other car texture): sampler names + kn5_textures list.
Usage: blender -b in.blend --python kk15i_tex_dds.py -- out.blend"""
import json, sys
import bpy
NAMES = ("KK_crinkle_red", "KK_alu_satinblack", "KK_alu_machined", "KK_polished", "KK_yellow", "KK_braid")
sc = bpy.data.scenes["Scene"]; n = 0
for m in bpy.data.materials:
    if m.get("kn5_def"):
        d = json.loads(m["kn5_def"]); ch = False
        for smp in d["samplers"]:
            for nm in NAMES:
                if smp[2] == nm + ".png":
                    smp[2] = nm + ".dds"; ch = True
        if ch:
            m["kn5_def"] = json.dumps(d); n += 1
t = json.loads(sc["kn5_textures"])
for x in t:
    for nm in NAMES:
        if x["name"] == nm + ".png":
            x["name"] = nm + ".dds"
sc["kn5_textures"] = json.dumps(t)
print("REPORT materials", n, [x["name"] for x in t if x["name"].startswith("KK_")])
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
