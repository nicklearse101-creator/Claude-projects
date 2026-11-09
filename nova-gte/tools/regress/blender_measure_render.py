"""Runs INSIDE Blender (background). Read-only on the model: measures NOVA_NEW, renders fixed clay views and a zebra pass.
Called by run_regression.py:  blender -b blender/nova_proc.blend --python this.py -- <outdir>
Zebra settings FIXED 2026-11-02 (stripe scale 2.5, 48 samples, 1000x625): do not change between runs you intend to compare. Never saves the .blend. Writes <outdir>/measure.json and PNGs.
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
body_col = bpy.data.collections["NOVA_NEW"]

# ---- measurement ------------------------------------------------------------------------------------------------
objs = {}
for o in body_col.objects:
    if o.type != "MESH":
        continue
    mn, mx = [1e9] * 3, [-1e9] * 3
    for v in o.bound_box:
        w = o.matrix_world @ Vector(v)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    objs[o.name] = dict(min=[round(a, 5) for a in mn], max=[round(a, 5) for a in mx], tris=len(o.data.polygons))

is_wheel = lambda n: n.startswith(("TIRE_", "RIM_", "DISK_"))
is_mirror = lambda n: n.startswith("MIRROR_")
body = {n: d for n, d in objs.items() if not is_wheel(n) and not is_mirror(n)}
ty = {n: objs[n] for n in ("TIRE_LF", "TIRE_RF", "TIRE_LR", "TIRE_RR")}
cx = {n: 0.5 * (d["min"][0] + d["max"][0]) for n, d in ty.items()}
cy = {n: 0.5 * (d["min"][1] + d["max"][1]) for n, d in ty.items()}
rad = {n: 0.5 * (d["max"][2] - d["min"][2]) for n, d in ty.items()}
yf, yr = 0.5 * (cy["TIRE_LF"] + cy["TIRE_RF"]), 0.5 * (cy["TIRE_LR"] + cy["TIRE_RR"])
miny = min(d["min"][1] for d in body.values()); maxy = max(d["max"][1] for d in body.values())
maxz = max(d["max"][2] for d in body.values())
wid = sorted(((max(abs(d["min"][0]), abs(d["max"][0])), n) for n, d in body.items()), reverse=True)
topz = sorted(((d["max"][2], n) for n, d in body.items()), reverse=True)[:3]
derived = {
    "wheelbase_mm": (yr - yf) * 1000,
    "track_front_mm": abs(cx["TIRE_LF"] - cx["TIRE_RF"]) * 1000,
    "track_rear_mm": abs(cx["TIRE_LR"] - cx["TIRE_RR"]) * 1000,
    "tyre_radius_mm": sum(rad.values()) / 4 * 1000,
    "length_mm": (maxy - miny) * 1000,
    "width_mm": 2 * wid[0][0] * 1000,
    "height_mm": maxz * 1000,
    "overhang_front_mm": (yf - miny) * 1000,
    "overhang_rear_mm": (maxy - yr) * 1000,
}
mirror_w = 2 * max(max(abs(d["min"][0]), abs(d["max"][0])) for n, d in objs.items() if is_mirror(n)) * 1000
drivers = {"width": [(n, round(2 * w * 1000, 1)) for w, n in wid[:5]], "height": [(n, round(z * 1000, 1)) for z, n in topz],
           "mirror_width_mm": round(mirror_w, 1), "n_objects": len(objs), "total_tris": sum(d["tris"] for d in objs.values())}
json.dump(dict(objects=objs, derived={k: round(v, 2) for k, v in derived.items()}, drivers=drivers),
          open(os.path.join(OUT, "measure.json"), "w"), indent=1)
print("measured", {k: round(v, 1) for k, v in derived.items()})

# ---- fixed views ------------------------------------------------------------------------------------------------
for c in bpy.data.collections:
    c.hide_render = c.name != "NOVA_NEW"
T = Vector((0, 0, 0.65))
VIEWS = [("front", True, (0, -1, 0), 2.7), ("rear", True, (0, 1, 0), 2.7), ("left", True, (1, 0, 0), 4.3), ("right", True, (-1, 0, 0), 4.3),
         ("top", True, (0, 0, 1), 4.3), ("q_front_left", False, (0.8, -1, 0.45), None), ("q_rear_left", False, (0.8, 1, 0.45), None)]


def cam_for(name, ortho, d, scale):
    cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); scene.collection.objects.link(cam)
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", scale
    else:
        cd.type, cd.lens = "PERSP", 50
    cd.clip_start, cd.clip_end = 0.1, 100
    d = Vector(d).normalized()
    if name == "top":
        cam.location = (0, 0, 10); cam.rotation_euler = (0, 0, math.pi)
    else:
        cam.location = T + d * (6.2 if not ortho else 9.0)
        cam.rotation_euler = (T - cam.location).to_track_quat("-Z", "Y").to_euler()
    return cam


scene.render.resolution_x, scene.render.resolution_y, scene.render.image_settings.file_format = 800, 500, "PNG"
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light, sh.color_type, sh.single_color = "STUDIO", "SINGLE", (0.72, 0.72, 0.74)
sh.show_object_outline, sh.object_outline_color = True, (0.0, 0.0, 0.0)
if scene.world is None:
    scene.world = bpy.data.worlds.new("W")
scene.world.color = (0.2, 0.2, 0.22)
cams = {}
t0 = time.time()
for name, ortho, d, sc in VIEWS:
    cams[name] = cam_for(name, ortho, d, sc); scene.camera = cams[name]
    scene.render.filepath = os.path.join(OUT, "clay_%s.png" % name); bpy.ops.render.render(write_still=True)
print("clay views %.1fs" % (time.time() - t0))

# ---- zebra pass: striped environment reflected by a mirror-finish override material ----------------------------------
t0 = time.time()
w = bpy.data.worlds.new("ZEBRA"); w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
tc, wave, ramp, bg, out = (nt.nodes.new(t) for t in ("ShaderNodeTexCoord", "ShaderNodeTexWave", "ShaderNodeValToRGB", "ShaderNodeBackground", "ShaderNodeOutputWorld"))
wave.wave_type, wave.bands_direction, wave.wave_profile = "BANDS", "Z", "SAW"
wave.inputs["Scale"].default_value, wave.inputs["Distortion"].default_value = 2.5, 0.0
ramp.color_ramp.interpolation = "CONSTANT"
ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (0.0, 0.0, 0.0, 1.0)
ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.5, (1.0, 1.0, 1.0, 1.0)
for a, b in ((tc.outputs["Generated"], wave.inputs["Vector"]), (wave.outputs["Fac"], ramp.inputs["Fac"]),
             (ramp.outputs["Color"], bg.inputs["Color"]), (bg.outputs["Background"], out.inputs["Surface"])):
    nt.links.new(a, b)
scene.world = w
mat = bpy.data.materials.new("ZEBRA_MIRROR"); mat.use_nodes = True
pb = mat.node_tree.nodes["Principled BSDF"]
pb.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1.0); pb.inputs["Metallic"].default_value = 1.0; pb.inputs["Roughness"].default_value = 0.03
bpy.context.view_layer.material_override = mat
scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 48; scene.cycles.use_denoising = False
scene.render.film_transparent = True
scene.render.resolution_x, scene.render.resolution_y = 1000, 625
for name in ("left", "front", "q_front_left", "q_rear_left"):
    scene.camera = cams[name]
    scene.render.filepath = os.path.join(OUT, "zebra_%s.png" % name); bpy.ops.render.render(write_still=True)
print("zebra views %.1fs" % (time.time() - t0))
