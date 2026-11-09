"""Import a generated GLB in an empty scene, put it in the car frame (z up, length along y, scaled to the
FIA length), render 4 views into one sheet.  blender -b --factory-startup --python gen_view.py -- in.glb out.png [flip]"""
import math, sys
import bpy
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], a[1]
rotz = float(a[2]) if len(a) > 2 else 0.0
clay = "clay" in a          # extra yaw (deg) once the nose direction is known
L = 3.622

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=src)
objs = [o for o in bpy.data.objects if o.type == "MESH"]
pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
mn = Vector((min(p[i] for p in pts) for i in range(3))); mx = Vector((max(p[i] for p in pts) for i in range(3)))
size = mx - mn
print("raw size", tuple(round(s, 3) for s in size))
yaw = (90.0 if size.x > size.y else 0.0) + rotz          # length onto y
s = L / max(size.x, size.y)
c = (mn + mx) / 2
M = Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Scale(s, 4) @ Matrix.Translation(Vector((-c.x, -c.y, -mn.z)))
for o in [o for o in bpy.data.objects if o.parent is None]:
    o.matrix_world = M @ o.matrix_world
bpy.context.view_layer.update()
pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
mn = Vector((min(p[i] for p in pts) for i in range(3))); mx = Vector((max(p[i] for p in pts) for i in range(3)))
print("car frame size", tuple(round(v, 3) for v in (mx - mn)), "verts", len(pts),
      "tris", sum(len(o.data.polygons) for o in objs))

sc = bpy.context.scene
if clay:
    cm = bpy.data.materials.new("clay"); cm.use_nodes = True
    b = next(n for n in cm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.18, 0.18, 0.19, 1); b.inputs["Roughness"].default_value = 0.25
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(cm)
        for f in o.data.polygons: f.use_smooth = True
w = sc.world or bpy.data.worlds.new("W"); sc.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.8, 0.82, 0.85, 1); bg.inputs[1].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(40), 0, math.radians(30))
try:
    sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 800, 500
sc.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
views = [("fr34", (-4.2, -5.6, 1.6)), ("rr34", (4.2, 5.6, 1.6)), ("side", (-8.5, 0.0, 0.75)), ("top", (0.0, 0.01, 9.0))]
import os
tiles = []
for name, loc in views:
    cam.location = loc
    d = Vector((0, 0, 0.62)) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    p = out.replace(".png", "_%s.png" % name)
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    tiles.append(p)
# sheet
imgs = [bpy.data.images.load(p) for p in tiles]
W, H = 800, 500
sheet = bpy.data.images.new("sheet", W * 2, H * 2)
px = [0.0] * (W * 2 * H * 2 * 4)
for k, im in enumerate(imgs):
    ox, oy = (k % 2) * W, (1 - k // 2) * H
    sp = list(im.pixels)
    for y in range(H):
        row = sp[y * W * 4:(y + 1) * W * 4]
        i0 = ((oy + y) * W * 2 + ox) * 4
        px[i0:i0 + W * 4] = row
sheet.pixels = px
sheet.filepath_raw = out; sheet.file_format = "PNG"; sheet.save()
bpy.ops.wm.save_as_mainfile(filepath=out.replace(".png", ".blend"))
print("sheet", out)
