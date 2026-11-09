"""Clay render of the procedural (blocky) model with the Meshy shell ghosted over it as the ruler.

Grey = the model we are editing. Red haze = the Meshy reference surface where it sits outside the model;
where the grey covers the red the model is proud of the reference.

blender -b blender/nova_proc.blend --python tools/gen/ruler_view.py -- out.png [view] [ghost|solid|off]
"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
VIEW = args[1] if len(args) > 1 else "front34"
REF = args[2] if len(args) > 2 else "ghost"
ONLY = set(args[3].split(",")) if len(args) > 3 else None   # render only these objects (+ the ruler)

VIEWS = {
    "front34": ((2.30, -4.70, 2.15), (0.0, -1.18, 0.88), 55.0),
    "nose":    ((1.15, -2.85, 1.35), (0.30, -1.55, 0.93), 85.0),
    "side":    ((6.00, -1.15, 1.05), (0.0, -1.15, 0.80), 85.0),
    "front":   ((0.01, -8.50, 0.80), (0.0, -1.30, 0.76), 50.0),
    "nose34":  ((1.30, -3.20, 1.25), (0.25, -1.68, 0.72), 95.0),
    "top":     ((0.05, -1.25, 4.60), (0.0, -1.20, 0.95), 45.0),
    "cowl":    ((0.95, -2.30, 1.95), (0.0, -0.82, 0.92), 95.0),
    "door":    ((6.00, -0.10, 0.80), (0.0, -0.10, 0.60), 80.0),
    "door34":  ((4.60, -3.00, 1.55), (0.0, -0.25, 0.62), 60.0),
    "sill34":  ((4.20, -2.20, 1.05), (0.0, -0.05, 0.45), 60.0),
    "bonnet_down": ((0.0, -3.30, 1.62), (0.0, -1.15, 0.86), 40.0),
    "corner":  ((1.55, -2.70, 0.90), (0.60, -1.69, 0.66), 30.0),
    "archlip": ((1.35, -1.55, 0.92), (0.66, -1.17, 0.62), 26.0),
    "wingnose":((1.95, -2.75, 0.95), (0.55, -1.62, 0.70), 32.0),
    "wing34":  ((3.10, -3.25, 1.30), (0.35, -1.25, 0.62), 55.0),
    "wingarch":((3.40, -1.60, 0.95), (0.55, -1.15, 0.55), 45.0),
    "sillF":   ((2.40, -1.95, 0.72), (0.72, -0.80, 0.31), 55.0),
    "sillR":   ((2.40, 1.95, 0.72), (0.72, 0.78, 0.36), 55.0),
}

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 48
sc.cycles.transparent_max_bounces = 32
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 1500, 1000
sc.render.film_transparent = False

w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.88, 0.92, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN"))
sc.collection.objects.link(sun)
sun.data.energy = 3.0
sun.rotation_euler = (0.9, 0.2, -0.9)

clay = bpy.data.materials.new("CLAY")
clay.use_nodes = True
b = next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
# "paint" renders the body in the car's own gunmetal grey: judging a light clay model against a dark grey
# photo exaggerates every edge, which is how the grille was nearly "corrected" the wrong way
PAINT = REF == "paint"
b.inputs["Base Color"].default_value = (0.055, 0.060, 0.068, 1) if PAINT else (0.62, 0.63, 0.64, 1)
b.inputs["Roughness"].default_value = 0.18 if PAINT else 0.42
if PAINT:
    b.inputs["Metallic"].default_value = 0.65
    pg = bpy.data.materials.get("paint_gunmetal")
    if pg and pg.node_tree:
        pb = next(n for n in pg.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        pb.inputs["Base Color"].default_value = (0.055, 0.060, 0.068, 1)
        pb.inputs["Metallic"].default_value = 0.65
        pb.inputs["Roughness"].default_value = 0.18

ghost = bpy.data.materials.new("GHOST")
ghost.use_nodes = True
ghost.blend_method = "BLEND" if hasattr(ghost, "blend_method") else None
nt = ghost.node_tree
nt.nodes.clear()
em = nt.nodes.new("ShaderNodeEmission")
em.inputs[0].default_value = (0.85, 0.12, 0.12, 1)
em.inputs[1].default_value = 1.0
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mx = nt.nodes.new("ShaderNodeMixShader")
mx.inputs[0].default_value = 0.80
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(em.outputs[0], mx.inputs[1])
nt.links.new(tr.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], out.inputs[0])

refs = [o for o in bpy.data.objects if o.name.startswith("MESHY_REF")]
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    o.hide_viewport = False
    if "Guide" in o.name or len(o.data.polygons) == 0:    # block-out box and the profile curves
        o.hide_render = True
        continue
    if ONLY is not None and o not in refs and o.name not in ONLY:
        o.hide_render = True
        continue
    if o in refs:
        o.hide_render = REF in ("off", "mat", "paint")
        o.data.materials.clear()
        o.data.materials.append(ghost if REF == "ghost" else clay)
    else:
        o.hide_render = REF == "solid"
        if REF not in ("mat", "paint"):  # these keep each part's own material
            o.data.materials.clear()
            o.data.materials.append(clay)
        elif not o.data.materials:
            o.data.materials.append(clay)
for lc in bpy.context.view_layer.layer_collection.children:
    lc.exclude = False
    lc.hide_viewport = False

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
t = cam.constraints.new("TRACK_TO")
t.target = emp
t.track_axis = "TRACK_NEGATIVE_Z"
t.up_axis = "UP_Y"

sc.render.filepath = OUT
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("saved", OUT)
