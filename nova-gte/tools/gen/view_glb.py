"""Render a generated GLB from 4 angles (textured + grey) for comparison: blender -b --factory-startup --python view_glb.py -- in.glb out_prefix"""
import sys, math, bpy
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
src, out = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr, size = (lo + hi) / 2, hi - lo
print("BBOX size %.3f %.3f %.3f  tris %d" % (size.x, size.y, size.z, sum(len(o.data.polygons) for o in obs)))
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.render.resolution_x, sc.render.resolution_y = 1000, 700
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
R = max(size) * 1.9
views = {"front34": (-0.7, -1, 0.35), "side": (1, 0, 0.12), "rear34": (0.7, 1, 0.35), "front": (0, -1, 0.1)}
# Meshy: Y-up glTF -> Blender Z-up; car length along the longest horizontal axis
long_axis = "x" if size.x > size.y else "y"
for shade in ("TEXTURE", "SINGLE"):
    sc.display.shading.color_type = shade
    for name, d in views.items():
        dv = Vector(d) if long_axis == "y" else Vector((d[1], d[0], d[2]))
        cam.location = ctr + dv.normalized() * R
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 50
        sc.render.filepath = "%s_%s_%s.png" % (out, name, "tex" if shade == "TEXTURE" else "grey")
        bpy.ops.render.render(write_still=True)
