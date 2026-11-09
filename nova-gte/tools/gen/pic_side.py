"""Render nova_proc.blend through the grey side picture's own camera, so the two can be laid side by side.

tools/photomatch/grey_cams.json holds the camera solved for reference/photos/grey_studio/side.png. Same
camera, same framing, so a crop of the render and the same crop of the picture show the same piece of car
at the same size - which is the only way Nik wants shape judged (CLAUDE.md, 2026-10-19).

blender -b blender/nova_proc.blend --python tools/gen/pic_side.py -- out.png [K] [only,objects]
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix

args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
K = int(args[1]) if len(args) > 1 else 4
ONLY = set(args[2].split(",")) if len(args) > 2 and args[2] else None

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAM = json.load(open(os.path.join(ROOT, "tools", "photomatch", "grey_cams.json")))
Q = np.array(CAM["gS"], float); W, H = CAM["W"], CAM["H"]
DZ = 0.0193                                     # the camera lives in the picture frame

def rodrigues(rv):
    """cv2.Rodrigues in six lines - Blender's Python has numpy but not OpenCV."""
    th = float(np.linalg.norm(rv))
    if th < 1e-12:
        return np.eye(3)
    k = np.asarray(rv, float).ravel() / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * Kx + (1 - math.cos(th)) * (Kx @ Kx)


R = rodrigues(Q[:3])
C = -R.T @ Q[3:6]
f = Q[6]
print("camera at %s, f/W %.2f, k1 %.4f" % (np.round(C, 3), f / W, Q[7]))

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.42, 0.43, 0.44)
sh.show_cavity = True; sh.cavity_type = "BOTH"
sh.show_object_outline = False; sh.show_specular_highlight = True
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = W * K, H * K

HIDE = ("Glass_", "MESHY_REF", "BLUEPRINT", "Chassis_Guide", "Wheel_Guide", "Profile_Side", "Side_Profile_Chassis",
        "Side_Profile_Hood", "Side_Profile_Tailgate", "Arch_Profile")
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    o.hide_render = o.name.startswith(HIDE) or (ONLY is not None and o.name not in ONLY)

cam_d = bpy.data.cameras.new("PIC_CAM")
cam_d.type = "PERSP"
cam_d.sensor_fit = "HORIZONTAL"
cam_d.sensor_width = 36.0
cam_d.lens = f / W * 36.0
cam_d.clip_start, cam_d.clip_end = 0.05, 60.0
cam = bpy.data.objects.new("PIC_CAM", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
# OpenCV looks down +z with +y down; Blender looks down -z with +y up
Rw = R.T @ np.diag([1.0, -1.0, -1.0])
M = Matrix([[Rw[0, 0], Rw[0, 1], Rw[0, 2], C[0]],
            [Rw[1, 0], Rw[1, 1], Rw[1, 2], C[1]],
            [Rw[2, 0], Rw[2, 1], Rw[2, 2], C[2]],
            [0, 0, 0, 1]])
cam.matrix_world = M
# the model is in the model frame; the camera was solved in the picture frame
cam.location.z += DZ

sc.render.filepath = bpy.path.abspath(OUT)
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
