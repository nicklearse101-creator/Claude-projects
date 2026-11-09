"""Draw the model's outline onto each photograph, through that photograph's own solved camera.

A geometric check you can see: the model is rendered as a flat silhouette with back faces culled, so the window
openings and wheel arches come out as holes, and the edges of that mask - outline, window openings, arch lips -
are drawn in cyan on the photo. Where the cyan lies on the car's own edges the shape matches; where it parts,
the gap is the error, in the photo's own pixels.

Only NOVA_NEW is drawn (old blocky parts and guides are hidden at collection level).

blender -b blender/nova_proc.blend --python tools/gen/match_overlay.py -- [cam,cam,...]
then  python tools/overlay_edges.py
"""
import json
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


sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (1, 1, 1)
sh.show_backface_culling = True
sh.show_cavity = False; sh.show_object_outline = False; sh.show_specular_highlight = False
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith(("Glass_", "CUT_", "MATCH_")):
        o.hide_render = True

# Tyres at the axles, so the camera cannot see through an empty wheel well to the back of the bumper; the
# real car's tyre fills it, and the arch gap is then the band between the tyre and the lip, as in the photo.
import math
for y_ax, half in ((-1.1715, 1.320 / 2), (1.1715, 1.307 / 2)):     # BA frame axles, SPEC_SHEET tracks
    for sx in (1, -1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.2916, depth=0.175,
                                            location=(sx * half, y_ax, 0.2916), rotation=(0, math.radians(90), 0))
        bpy.context.active_object.name = "MATCH_tyre"

for name, c in cameras().items():
    if WANT and name not in WANT:
        continue
    cam = bpy.data.objects.new("MATCH_" + name, bpy.data.cameras.new("MATCH_" + name))
    sc.collection.objects.link(cam)
    cam.matrix_world = Matrix.Translation(c["loc"]) @ c["rot"].to_4x4()
    cam.data.sensor_fit = "HORIZONTAL"; cam.data.sensor_width = SENSOR
    cam.data.lens = c["f"] * SENSOR / c["W"]; cam.data.clip_start = 0.05
    sc.camera = cam
    s = 1.0 if c["W"] <= 1600 else 1434.0 / c["W"]
    sc.render.resolution_x = int(round(c["W"] * s)); sc.render.resolution_y = int(round(c["H"] * s))
    sc.render.filepath = os.path.join(OUT, "mask_%s.png" % name)
    bpy.ops.render.render(write_still=True)
    print("wrote mask_%s.png (%dx%d)" % (name, sc.render.resolution_x, sc.render.resolution_y))
