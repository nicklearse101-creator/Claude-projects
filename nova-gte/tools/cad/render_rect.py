"""Render the blend orthographically into exactly the world rectangles of reference/views/frame.json, so a model
render and a drawing view can be laid on each other pixel for pixel (tools/cad/overlay.py).

Cameras: side from +x (right = +y), front from -y (right = +x), rear from +y (right = -x), plan from above rotated
90 deg so right = +y and DOWN = +x - the same axes as the drawing views.

blender -b file.blend --python tools/cad/render_rect.py -- outdir [view,view,...]
"""
import json
import math
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
OUTDIR = os.path.abspath(args[0])
WANT = set(args[1].split(",")) if len(args) > 1 else None
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = json.load(open(os.path.join(ROOT, "reference", "views", "frame.json")))
os.makedirs(OUTDIR, exist_ok=True)

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.45, 0.46, 0.47)
sh.show_cavity = True; sh.cavity_type = "BOTH"; sh.show_object_outline = True; sh.object_outline_color = (0, 0, 0)
sc.render.film_transparent = True
sc.render.resolution_percentage = 100
cam_data = bpy.data.cameras.new("RECT_CAM"); cam_data.type = "ORTHO"; cam_data.clip_start = 0.1; cam_data.clip_end = 40
cam = bpy.data.objects.new("RECT_CAM", cam_data); sc.collection.objects.link(cam); sc.camera = cam

KIND = {"ga_side": "side", "bp_side": "side", "ga_front": "front", "bp_front": "front", "ga_rear": "rear",
        "ga_plan": "plan"}
done = set()
for name, v in F["views"].items():
    k = KIND[name]
    if (WANT and name not in WANT) or k in done:
        continue
    a0, a1, b0, b1 = v["rect"]
    W, H = v["size"]
    sc.render.resolution_x, sc.render.resolution_y = W, H
    cam_data.ortho_scale = max(a1 - a0, b1 - b0)
    am, bm = 0.5 * (a0 + a1), 0.5 * (b0 + b1)
    if k == "side":
        cam.location = (12.0, am, bm); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    elif k == "front":
        cam.location = (am, -12.0, bm); cam.rotation_euler = (math.radians(90), 0, 0)
    elif k == "rear":
        cam.location = (-am, 12.0, bm); cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    else:   # plan: u = y, v = x downwards -> camera right = +y, camera up = -x
        cam.location = (-bm, am, 12.0); cam.rotation_euler = (0, 0, math.radians(90))
    sc.render.filepath = os.path.join(OUTDIR, "rect_%s.png" % k)
    bpy.ops.render.render(write_still=True)
    done.add(k)
    print("wrote rect_%s.png %dx%d" % (k, W, H))
