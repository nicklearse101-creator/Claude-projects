"""Step 1 of the Kadett kit: import the LIVE Escort kn5s (main + LOD b/c/d) into a fresh blend and check the
round trip is byte-identical. Run: blender -b --factory-startup --python kk_load.py"""
import sys, os, hashlib, json, bpy
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kn5_import, ac_kn5_export as ex, escort_scene as es
LIVE = es.CAR
TEX = r"D:\Claude\escort_mk2_dtm\blender\kn5_textures_v37"
OUT = r"D:\Claude\escort_mk2_dtm\blender\escort_v37 kadett kit 0 live import.blend"
bpy.ops.wm.read_factory_settings(use_empty=True)
main = bpy.context.scene; main.name = "Scene"
for tag, fname in es.FILES.items():
    sc = main if tag == "A" else bpy.data.scenes.new(f"LOD_{tag}")
    bpy.context.window.scene = sc
    st = kn5_import.import_kn5(os.path.join(LIVE, fname), TEX if tag == "A" else os.path.join(TEX, f"lod_{tag.lower()}"),
                               "ESCORT" if tag == "A" else f"LOD_{tag}_MODEL")
    bpy.context.view_layer.update()
    print("IMPORT", tag, st["tris"], st["materials"], st["textures"], flush=True)
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
for tag, fname in es.FILES.items():
    bpy.context.window.scene = es.scene_of(tag)
    out = os.path.join(r"D:\ClaudeData\tmp\kadett", f"rt_{tag}.kn5")
    ex.export_kn5(out, [es.root_of(tag)])
    print("ROUNDTRIP", tag, h(out) == h(os.path.join(LIVE, fname)), flush=True); os.remove(out)
bpy.context.window.scene = main
bpy.ops.wm.save_as_mainfile(filepath=OUT)
for tag in "ABCD":
    sc = es.scene_of(tag)
    print(tag, sorted({o.get("kn5_name") for o in sc.objects if str(o.get("kn5_name","")).startswith(("NICK3","AERO_wing","AERO_end","AERO_skirt","AERO_air","AERO_splitter","AERO_strak","AERO_rear"))}))
