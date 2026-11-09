"""Ortho side render of the fitted Meshy body with the photo-traced Profile_Side outline (phase 2, from Nik's grey
side picture) overlaid in orange. blender -b nova_meshy.blend --python compare_side.py -- out.png [dy]"""
import sys, bpy
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]; dy = float(args[1]) if len(args) > 1 else 0.0
with bpy.data.libraries.load(r"D:\Claude\vauxhall_nova_gte_1989\blender\nova_proc.blend") as (a, b):
    b.objects = ["Profile_Side", "Arch_Profile_Front", "Arch_Profile_Rear"]
sc = bpy.context.scene
for o in b.objects:
    sc.collection.objects.link(o)
    o.location.x = 1.0                                   # in front of the body for the camera at +x
    m = o.modifiers.new("skin", "SKIN") if False else None
body = bpy.data.objects["Meshy_Body"]
body.location.y = dy
# outline as thick tubes
for o in b.objects:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="CURVE")
    o.data.bevel_depth = 0.006
    mat = bpy.data.materials.new("orange"); mat.diffuse_color = (1, 0.45, 0, 1); o.data.materials.append(mat)
    o.select_set(False)
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"; sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_cavity = True
for m in body.data.materials:
    m.diffuse_color = (0.75, 0.75, 0.77, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 4.0
cam.location = (10, 0, 0.68); cam.rotation_euler = (1.5708, 0, 1.5708)
sc.render.resolution_x, sc.render.resolution_y = 1600, 700
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
