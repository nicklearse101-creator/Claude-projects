"""Render the Meshy body with the doors closed and open (left 60 deg, right 60 deg) to check the cut.
blender -b nova_meshy.blend --python door_test.py -- out_prefix"""
import sys, math, bpy
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1:][0]
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"; sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 900
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
def shot(name, loc, tgt, lens=40):
    cam.location = loc; cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = lens
    sc.render.filepath = "%s_%s.png" % (out, name); bpy.ops.render.render(write_still=True)
L, R = bpy.data.objects["DOOR_L"], bpy.data.objects["DOOR_R"]
shot("closed_left", (4.2, -2.6, 1.3), (0.3, 0, 0.6))
L.rotation_euler.z = math.radians(-62); R.rotation_euler.z = math.radians(62)
shot("open_left", (4.2, -2.6, 1.3), (0.3, 0, 0.6))
shot("open_right", (-4.2, -2.6, 1.3), (-0.3, 0, 0.6))
shot("open_front", (0.0, -5.5, 1.8), (0, 0, 0.6), 35)
