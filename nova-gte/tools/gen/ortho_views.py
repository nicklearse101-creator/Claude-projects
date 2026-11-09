"""Orthographic front / rear / top / side views of the working blend, for comparing against the
pictures from every angle rather than just the side.

blender -b blender/nova_proc.blend --python tools/gen/ortho_views.py -- outdir [px_per_m]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUTDIR = args[0]
PPM = float(args[1]) if len(args) > 1 else 420.0

VIEWS = {                     # name: (location, euler, width m, height m)
    "front": ((0.0, -6.0, 0.70), (1.5708, 0.0, 0.0), 2.0, 1.7),
    "rear": ((0.0, 6.0, 0.70), (1.5708, 0.0, 3.14159), 2.0, 1.7),
    "side": ((6.0, 0.0, 0.70), (1.5708, 0.0, 1.5708), 4.2, 1.7),
    "top": ((0.0, 0.0, 6.0), (0.0, 0.0, 0.0), 4.2, 2.0),
}

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.42, 0.43, 0.44)
sh.show_cavity = True; sh.cavity_type = "BOTH"
sh.show_object_outline = False; sh.show_specular_highlight = True
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"

HIDE = ("Glass_", "MESHY_REF", "BLUEPRINT", "Chassis_Guide", "Wheel_Guide", "Profile_Side",
        "Side_Profile_Chassis", "Side_Profile_Hood", "Side_Profile_Tailgate", "Arch_Profile", "CUT_")
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = o.name.startswith(HIDE)

cam_d = bpy.data.cameras.new("ORTHO")
cam_d.type = "ORTHO"
cam = bpy.data.objects.new("ORTHO", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
os.makedirs(OUTDIR, exist_ok=True)
for name, (loc, rot, w, h) in VIEWS.items():
    cam.location = Vector(loc)
    cam.rotation_euler = rot
    cam_d.ortho_scale = max(w, h)
    sc.render.resolution_x = int(round(max(w, h) * PPM))
    sc.render.resolution_y = int(round(max(w, h) * PPM * h / w)) if w >= h else int(round(max(w, h) * PPM))
    sc.render.resolution_x = int(round(w * PPM))
    sc.render.resolution_y = int(round(h * PPM))
    cam_d.ortho_scale = w
    sc.render.filepath = os.path.join(OUTDIR, "ortho_%s.png" % name)
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    print("wrote ortho_%s.png  %dx%d at %.0f px/m" % (name, sc.render.resolution_x,
                                                      sc.render.resolution_y, PPM))
