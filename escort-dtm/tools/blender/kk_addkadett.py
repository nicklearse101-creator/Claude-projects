import sys, bpy, numpy as np
sys.path.insert(0, r"D:\Claude\escort_mk2_dtm\tools\blender")
import kn5_import
main = bpy.data.scenes["Scene"]
sc = bpy.data.scenes.new("KADETT"); bpy.context.window.scene = sc
kn5_import.import_kn5(r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\opel_kadett_s2\opel_kadett_s2.kn5",
                      r"D:\Claude\escort_mk2_dtm\blender\kadett_textures", "KADETT_REF", prefix="K_", primary=False)
bpy.context.view_layer.update()
bpy.context.window.scene = main
bpy.ops.wm.save_as_mainfile(filepath=r"D:\Claude\escort_mk2_dtm\blender\escort_v37 kadett kit 1 with kadett ref.blend")
print("OK")
