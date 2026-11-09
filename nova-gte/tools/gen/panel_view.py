"""Reflective check render of a panel: a banded studio environment on a polished-metal override shows waves
that a diffuse clay render hides. Also renders the Meshy texture as it is.

blender -b <blend> --python tools/gen/panel_view.py -- out.png [metal|tex] [front34|top|side34]
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
MODE = args[1] if len(args) > 1 else "metal"
VIEW = args[2] if len(args) > 2 else "front34"

VIEWS = {                       # (camera location, target, lens)
    "front34": ((2.30, -4.70, 2.15), (0.0, -1.18, 0.88), 55.0),
    "top":     ((0.05, -1.25, 3.20), (0.0, -1.20, 0.95), 60.0),
    "side34":  ((2.60, -2.30, 1.55), (0.0, -1.15, 0.92), 80.0),
    "nose":    ((1.15, -2.85, 1.35), (0.30, -1.55, 0.93), 85.0),
}

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 64
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 1500, 1000
sc.render.resolution_percentage = 100
sc.render.film_transparent = False

# banded environment: horizontal light/dark stripes, so a wavy surface shows kinked reflections
w = bpy.data.worlds.new("STUDIO")
sc.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
wave = nt.nodes.new("ShaderNodeTexWave")
wave.bands_direction = "Z"
wave.inputs["Scale"].default_value = 2.5
wave.inputs["Distortion"].default_value = 0.0
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.42
ramp.color_ramp.elements[1].position = 0.58
ramp.color_ramp.elements[0].color = (0.04, 0.04, 0.05, 1)
ramp.color_ramp.elements[1].color = (2.2, 2.2, 2.3, 1)
bg = nt.nodes.new("ShaderNodeBackground")
out = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
nt.links.new(wave.outputs["Color"], ramp.inputs[0])
nt.links.new(ramp.outputs["Color"], bg.inputs[0])
nt.links.new(bg.outputs[0], out.inputs[0])

objs = [o for o in bpy.data.objects if o.type == "MESH"]
if MODE == "metal":
    m = bpy.data.materials.new("CHECK")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.55, 0.56, 0.58, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.06
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(m)

loc, tgt, lens = VIEWS[VIEW]
cd = bpy.data.cameras.new("C")
cd.lens = lens
cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cam.location = loc
emp = bpy.data.objects.new("T", None)
sc.collection.objects.link(emp)
emp.location = tgt
tr = cam.constraints.new("TRACK_TO")
tr.target = emp
tr.track_axis = "TRACK_NEGATIVE_Z"
tr.up_axis = "UP_Y"

sc.render.filepath = OUT
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("saved", OUT)
