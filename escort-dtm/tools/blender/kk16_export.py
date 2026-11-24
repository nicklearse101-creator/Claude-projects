"""Export ESCORT 16 (ford_escort_mk2_tuned_16) (step 5 of kk_v49)."""
import json, os, sys
import bpy
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kk_finish as kf
import ac_kn5_export as ex
kf.FILES = {k: v.replace("ford_escort_mk2_tuned", "ford_escort_mk2_tuned_16") for k, v in kf.FILES.items()}
STAGE = r"D:\Claude\escort_mk2_dtm\export_staging_16"
LOD_RATIO = {"B": 0.30, "C": 0.12, "D": 0.04}
main = bpy.data.scenes["Scene"]; bpy.context.window.scene = main; bpy.context.view_layer.update()
rep = {}
# 5 ---------------------------------------------------------------- export main + LODs from this model
os.makedirs(STAGE, exist_ok=True)
root = next(o for o in main.objects if o.get("kn5_root"))
st = ex.export_kn5(os.path.join(STAGE, kf.FILES["A"]), [root])
rep["A"] = st.get("tris")
meshes = [o for o in main.objects if o.type == "MESH" and not o.get("no_export")]
saved = {o.name: o.get("kn5_pristine") for o in meshes}
for o in meshes:
    if "kn5_pristine" in o:
        o["kn5_pristine"] = False
for tag, ratio in LOD_RATIO.items():
    for o in meshes:
        n = len(o.data.polygons)
        if n > 24:
            m = o.modifiers.new("LOD", "DECIMATE"); m.ratio = max(ratio, 12 / n); m.use_collapse_triangulate = True
    bpy.context.view_layer.update()
    keep_tex = main["kn5_textures"]; main["kn5_textures"] = "[]"      # LODs carry no textures (AC takes them from the main kn5)
    try:
        st = ex.export_kn5(os.path.join(STAGE, kf.FILES[tag]), [root], share_textures=True)
    finally:
        main["kn5_textures"] = keep_tex
    rep[tag] = st.get("tris")
    for o in meshes:
        for m in [m for m in o.modifiers if m.name == "LOD"]:
            o.modifiers.remove(m)
for o in meshes:
    if saved[o.name] is not None:
        o["kn5_pristine"] = saved[o.name]
print("REPORT", json.dumps(rep, default=str))
