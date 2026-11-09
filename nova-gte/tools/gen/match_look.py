"""Render the model like the photographs, through each photograph's own solved camera.

The seven bundle-adjusted cameras in tools/photomatch/ba_result.json all look at red GTEs (redgte_20/22/23/24,
the F400 PTF side and rear, and the commons front). So the model is rendered glossy red under a sky, which is
what makes creases, ridges and panel breaks visible on the real car - a light clay render shows none of them, and
judging against it has misled me more than once. Placeholder tyres sit at the axles so the silhouettes compare.

For each camera it writes export/match/look_<cam>.png (lit) and export/match/mask_<cam>.png (silhouette). Nothing
is saved to the blend - the tyres, materials and world exist only for the render.

blender -b blender/nova_proc.blend --python tools/gen/match_look.py -- [cam,cam,...]
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WANT = set(args[0].split(",")) if args and args[0] else None

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
PM = os.path.join(ROOT, "tools", "photomatch")
OUT = os.path.join(ROOT, "export", "match")
os.makedirs(OUT, exist_ok=True)
SENSOR = 36.0
R_TYRE, W_TYRE = 0.29155, 0.175
AXLES = ((-1.1715, 1.320 / 2), (1.1715, 1.307 / 2))      # BA frame axles, SPEC_SHEET tracks

HIDE = ("MESHY", "BLUEPRINT", "Chassis_Guide", "Wheel_Guide", "Profile_Side", "Side_Profile_Chassis",
        "Side_Profile_Hood", "Side_Profile_Tailgate", "Arch_Profile", "CUT_", "MATCH_", "GREY_CAM", "PIC_CAM")
DARK = ("GRILLE_INSERT", "GRILLE_GROOVE", "Scuttle_Vent", "Glass_", "HEADLAMP_REFLECTOR", "Housing_Taillight",
        "MIRROR_BASE", "MIRROR_GLASS")
CLEAR = ("HEADLAMP_GLASS", "INDICATOR_F", "INDICATOR_HOUSING")


def cameras():
    B = json.load(open(os.path.join(PM, "ba_result.json")))
    O = json.load(open(os.path.join(PM, "obs.json")))
    dz = json.load(open(os.path.join(PM, "body_profile.json")))["dz"]
    out = {}
    for name, p in B["cams"].items():
        rv = Vector(p[0:3]); t = Vector(p[3:6]); ang = rv.length
        R = Matrix.Rotation(ang, 3, rv.normalized()) if ang > 0 else Matrix.Identity(3)
        C = -(R.transposed() @ t)
        Rbl = R.transposed() @ Matrix(((1, 0, 0), (0, -1, 0), (0, 0, -1)))
        out[name] = {"loc": (C.x, C.y, C.z + dz), "rot": Rbl, "f": p[6], "W": O[name]["W"], "H": O[name]["H"]}
    return out


def material(name, base, metallic=0.0, rough=0.4, coat=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = base
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    for key in ("Coat Weight", "Clearcoat"):
        if key in b.inputs:
            b.inputs[key].default_value = coat
            break
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
    return m


sc = bpy.context.scene
engines = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next((e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in engines), "CYCLES")
if sc.render.engine == "CYCLES":
    sc.cycles.samples = 64
sc.view_settings.view_transform = "Standard"

paint = material("MATCH_paint", (0.30, 0.012, 0.014, 1), metallic=0.25, rough=0.14, coat=1.0)
dark = material("MATCH_dark", (0.012, 0.012, 0.013, 1), rough=0.5)
clear = material("MATCH_clear", (0.75, 0.75, 0.72, 1), rough=0.05)
rubber = material("MATCH_tyre", (0.02, 0.02, 0.02, 1), rough=0.8)
alloy = material("MATCH_alloy", (0.55, 0.56, 0.58, 1), metallic=0.8, rough=0.3)
# the panes built by add_glass.py: dark and glossy, so the openings read as glazed rather than as holes
glass = material("MATCH_glass", (0.035, 0.040, 0.047, 1), rough=0.04, coat=1.0)

for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    if o.name.startswith(HIDE) or len(o.data.polygons) == 0:
        o.hide_render = True
        continue
    o.hide_render = False
    if o.name.startswith("GLASS_"):
        m = glass
    elif o.name.startswith("TIRE_"):          # the real wheels (add_wheels.py, 2026-10-27 (15))
        m = rubber
    elif o.name.startswith("RIM_"):
        m = alloy
    elif o.name.startswith(("SHUT_", "DISK_")):
        m = dark
    else:
        m = dark if o.name.startswith(DARK) else clear if o.name.startswith(CLEAR) else paint
    o.data.materials.clear()
    o.data.materials.append(m)

REAL_WHEELS = any(o.name.startswith("TIRE_") for o in bpy.data.objects)
for y, half in (() if REAL_WHEELS else AXLES):        # placeholders only while the blend has no wheels
    for sx in (1, -1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=R_TYRE, depth=W_TYRE,
                                            location=(sx * (half - 0.0), y, R_TYRE),
                                            rotation=(0, math.radians(90), 0))
        t = bpy.context.active_object; t.data.materials.append(rubber)
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.178, depth=W_TYRE + 0.004,
                                            location=(sx * half, y, R_TYRE),
                                            rotation=(0, math.radians(90), 0))
        r = bpy.context.active_object; r.data.materials.append(alloy)

# a sky with a bright overhead and a darker horizon: that gradient is what draws creases in paint
w = bpy.data.worlds.new("MATCH_sky"); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
sky = nt.nodes.new("ShaderNodeTexSky") if hasattr(bpy.types, "ShaderNodeTexSky") else None
grad = nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type = "LINEAR"
tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Rotation"].default_value = (0, math.radians(-90), 0)
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.10, 0.10, 0.11, 1)
ramp.color_ramp.elements[1].color = (0.95, 0.97, 1.0, 1)
nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
nt.links.new(mp.outputs["Vector"], grad.inputs["Vector"])
nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.2
sun = bpy.data.objects.new("MATCH_sun", bpy.data.lights.new("MATCH_sun", "SUN"))
sc.collection.objects.link(sun); sun.data.energy = 2.5; sun.rotation_euler = (0.7, 0.15, 0.5)

for name, c in cameras().items():
    if WANT and name not in WANT:
        continue
    cam = bpy.data.objects.new("MATCH_" + name, bpy.data.cameras.new("MATCH_" + name))
    sc.collection.objects.link(cam)
    cam.matrix_world = Matrix.Translation(c["loc"]) @ c["rot"].to_4x4()
    cam.data.sensor_fit = "HORIZONTAL"; cam.data.sensor_width = SENSOR
    cam.data.lens = c["f"] * SENSOR / c["W"]; cam.data.clip_start = 0.05
    sc.camera = cam
    scale = 1.0 if c["W"] <= 1600 else 1434.0 / c["W"]
    sc.render.resolution_x = int(round(c["W"] * scale)); sc.render.resolution_y = int(round(c["H"] * scale))
    sc.render.film_transparent = True
    sc.render.filepath = os.path.join(OUT, "look_%s.png" % name)
    bpy.ops.render.render(write_still=True)
    print("wrote look_%s.png (%dx%d)" % (name, sc.render.resolution_x, sc.render.resolution_y))
