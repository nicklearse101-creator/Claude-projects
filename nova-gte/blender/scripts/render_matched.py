"""Render the model through the photo-matched cameras for overlay checks (runs inside Blender).

Cameras: tools/photomatch/ba_result.json (bundle adjustment, photo frame) + obs.json (image sizes). Blender
camera = OpenCV pose with R_bl = R_cv^T * diag(1, -1, -1), lifted by DZ onto the model frame; lens distortion k1
is ignored (|k1| < 0.05). Writes export/match/<cam>.png (workbench, flat colours, transparent background) and,
with look=True, export/match/<cam>_look.png (studio-lit, for side-by-side comparison with the photo).
"""
import json
import os

import bpy
from mathutils import Matrix, Vector

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
PM = os.path.join(ROOT, "tools", "photomatch")
OUT = os.path.join(ROOT, "export", "match")
SENSOR = 36.0


def cameras():
    import math
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


def render(names=None, look=False):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.color_type = "MATERIAL"
    sh.show_object_outline = False
    sc.render.resolution_percentage = 100
    hidden = []
    for o in bpy.data.objects:
        if o.get("no_export") and o.type == "MESH" and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    out = []
    for name, c in cameras().items():
        if names and name not in names:
            continue
        cam = bpy.data.objects.get("MATCH_" + name)
        if cam is None:
            cam = bpy.data.objects.new("MATCH_" + name, bpy.data.cameras.new("MATCH_" + name))
            sc.collection.objects.link(cam)
        cam["no_export"] = 1
        cam.matrix_world = Matrix.Translation(c["loc"]) @ c["rot"].to_4x4()
        cam.data.type = "PERSP"
        cam.data.sensor_fit = "HORIZONTAL"
        cam.data.sensor_width = SENSOR
        cam.data.lens = c["f"] * SENSOR / c["W"]
        cam.data.clip_start = 0.05
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = c["W"], c["H"]
        for mode in (["flat", "look"] if look else ["flat"]):
            if mode == "flat":
                sh.light = "FLAT"; sh.show_cavity = False; sc.render.film_transparent = True
                sc.render.filepath = os.path.join(OUT, name + ".png")
            else:
                sh.light = "STUDIO"; sh.show_cavity = True; sh.show_specular_highlight = True
                sc.render.film_transparent = True
                sc.render.filepath = os.path.join(OUT, name + "_look.png")
            bpy.ops.render.render(write_still=True)
            out.append(sc.render.filepath)
    for o in hidden:
        o.hide_render = False
    sc.render.film_transparent = False
    sh.light = "STUDIO"
    return out


if __name__ == "__main__":
    print(render())
