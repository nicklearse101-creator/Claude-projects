"""Orthographic side render over an exact world rectangle, so it can be overlaid on the calibrated
blueprint pixel for pixel. Prints the mapping it used.

blender -b blender/nova_proc.blend --python tools/gen/side_ortho.py -- out.png [clay|paint|silhouette]
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
MODE = args[1] if len(args) > 1 else "clay"

Y0, Y1, Z0, Z1 = -1.95, 1.95, -0.05, 1.50      # world rectangle the image covers
PPM = 400                                      # pixels per metre

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 24
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x = int((Y1 - Y0) * PPM)
sc.render.resolution_y = int((Z1 - Z0) * PPM)
sc.render.resolution_percentage = 100
sc.render.film_transparent = True

w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN"))
sc.collection.objects.link(sun)
sun.data.energy = 3.0
sun.rotation_euler = (0.85, 0.15, -1.1)

mat = bpy.data.materials.new("M")
mat.use_nodes = True
b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
if MODE == "silhouette":
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (0.1, 0.35, 0.9, 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], o.inputs[0])
else:
    b.inputs["Base Color"].default_value = (0.62, 0.63, 0.64, 1)
    b.inputs["Roughness"].default_value = 0.45

for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    o.hide_viewport = False
    o.hide_render = o.name.startswith("MESHY_REF") or "Guide" in o.name or len(o.data.polygons) == 0
    if not o.hide_render and MODE != "paint":
        o.data.materials.clear()
        o.data.materials.append(mat)

cd = bpy.data.cameras.new("C")
cd.type = "ORTHO"
cd.ortho_scale = Y1 - Y0
cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cam.location = (6.0, 0.5 * (Y0 + Y1), 0.5 * (Z0 + Z1))
cam.rotation_euler = (1.5707963, 0.0, 1.5707963)        # local +X -> world +Y, local +Y -> world +Z

sc.render.filepath = OUT
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
bpy.ops.render.render(write_still=True)
print("saved %s  rect y %.2f..%.2f z %.2f..%.2f  %d px/m  %dx%d"
      % (OUT, Y0, Y1, Z0, Z1, PPM, sc.render.resolution_x, sc.render.resolution_y))
