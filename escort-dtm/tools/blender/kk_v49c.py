"""v49c: belts worn again + yellow. v49 had copied the CM (CINTURE_OFF) meshes into CINTURE_ON -> driver not wearing them and still
not yellow. CINTURE_ON meshes back from the v48 blend (worn shape, v47 floor routing); every belt mesh gets its own yellow
material copy (textures BELT_Y_*.dds made from the belts' own AO/strap textures, alpha 255, isAdditive 0); anchor eyes untouched."""
import json, bpy
V48 = r"D:\Claude\escort_mk2_dtm\blender\escort_v48 fog lamps.blend"
main = bpy.data.scenes["Scene"]
ON = ("CINTURE_ON_SUB1", "CINTURE_ON_SUB0", "CINTURE_ON_SUB1__lr")
with bpy.data.libraries.load(V48) as (src, dst):
    dst.meshes = list(src.meshes)
want = {}
for me in dst.meshes:
    if me is None:
        continue
    for o in main.objects:
        pass
# map v48 object names -> mesh names via a second load of objects
with bpy.data.libraries.load(V48) as (src, dst2):
    dst2.objects = list(src.objects)
donor = {o.get("kn5_name"): o for o in dst2.objects if o is not None and o.type == "MESH" and o.get("kn5_name") in ON
         and o.users_scene == () }
donor = {}
for o in dst2.objects:
    if o is not None and o.type == "MESH" and o.get("kn5_name") in ON and o.get("kn5_name") not in donor:
        donor[o.get("kn5_name")] = o
rep = {}
for o in main.objects:
    k = o.get("kn5_name")
    if o.type == "MESH" and k in ON and k in donor:
        o.data = donor[k].data.copy(); rep[k] = len(o.data.polygons)
        if "kn5_pristine" in o:
            o["kn5_pristine"] = False
texs = json.loads(main["kn5_textures"])
for n in ("BELT_Y_97.dds", "BELT_Y_98.dds", "BELT_Y_STRAP.dds"):
    if n not in [t["name"] for t in texs]:
        texs.append({"name": n, "active": 1})
main["kn5_textures"] = json.dumps(texs)
new = {}
def ymat(src, tex):
    key = (src.name, tex)
    if key in new:
        return new[key]
    m = src.copy(); d = json.loads(src["kn5_def"]); d["name"] = "KK_belt_" + tex.replace(".dds", "")
    for s in d["samplers"]:
        if s[0] == "txDiffuse":
            s[2] = tex
    for p in d["props"]:
        if p[0] == "isAdditive":
            p[1] = 0.0
    m["kn5_def"] = json.dumps(d); m.name = d["name"]; new[key] = m
    return m
TEXFOR = {"Material #100TT34": "BELT_Y_97.dds", "Material #101III": "BELT_Y_98.dds", "INT_Cinture": "BELT_Y_STRAP.dds"}
for sc in bpy.data.scenes:
    for o in sc.objects:
        if o.type != "MESH" or not str(o.get("kn5_name", "")).startswith("CINTURE"):
            continue
        for s in o.material_slots:
            if s.material and "kn5_def" in s.material:
                k = json.loads(s.material["kn5_def"])["name"]
                if k in TEXFOR:
                    s.material = ymat(s.material, TEXFOR[k])
mats = json.loads(main["kn5_materials"])
for m in new.values():
    if m.name not in mats:
        mats.append(m.name)
main["kn5_materials"] = json.dumps(mats)
for o in list(dst2.objects):
    if o is not None and o.users == 0:
        bpy.data.objects.remove(o)
print("REPORT", rep, [m.name for m in new.values()])
bpy.ops.wm.save_mainfile()
