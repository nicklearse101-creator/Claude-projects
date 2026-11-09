"""Ortho left-side render of the door area of the Meshy body (textured and grey) for reading the shut lines; a 0.1 m
grid in the Nova frame is drawn afterwards. blender -b nova_meshy.blend --python door_view.py -- out_prefix"""
import sys, bpy
args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.show_cavity = True; sc.display.shading.cavity_type = "BOTH"
sc.world = sc.world or bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 2.6
CY, CZ = 0.0, 0.75
cam.location = (10, CY, CZ); cam.rotation_euler = (1.5708, 0, 1.5708)
sc.render.resolution_x, sc.render.resolution_y = 2000, 1000
for shade in ("TEXTURE", "SINGLE"):
    sc.display.shading.color_type = shade
    sc.render.filepath = "%s_%s.png" % (out, shade.lower())
    bpy.ops.render.render(write_still=True)
print("MAP", CY, CZ, 2.6, 2000, 1000)
