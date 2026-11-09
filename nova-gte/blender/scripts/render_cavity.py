"""Orthographic Workbench renders of REF_BODY with cavity shading (grooves dark, edges light) for the feature map.
Exact scale: each view's pixel -> car-frame mapping is written next to the image (json)."""
import json
import math
import os

import bpy
from mathutils import Vector

OUT = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\scan"
PX_PER_M = 820          # ~1.2 mm per pixel
VIEWS = {   # name: (camera location, look direction (to target), up, u-range, v-range)
    "side_L": ((5.0, -0.03, 0.75), (-1, 0, 0), (0, 0, 1), (-1.86, 1.80), (0.10, 1.40)),
    "side_R": ((-5.0, -0.03, 0.75), (1, 0, 0), (0, 0, 1), (-1.86, 1.80), (0.10, 1.40)),
    "front": ((0.0, -6.0, 0.75), (0, 1, 0), (0, 0, 1), (-0.88, 0.88), (0.10, 1.40)),
    "rear": ((0.0, 6.0, 0.75), (0, -1, 0), (0, 0, 1), (-0.88, 0.88), (0.10, 1.40)),
    "top": ((0.0, -0.03, 6.0), (0, 0, -1), (0, 1, 0), (-0.88, 0.88), (-1.86, 1.80)),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    for o in bpy.data.objects:
        o.hide_render = o.name != "REF_BODY"
    for c in bpy.data.collections:
        c.hide_render = c.name != "REF"
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.72, 0.72, 0.72)
    sh.show_cavity = True; sh.cavity_type = "BOTH"
    sh.cavity_ridge_factor = 1.0; sh.cavity_valley_factor = 2.0
    sh.curvature_ridge_factor = 1.0; sh.curvature_valley_factor = 2.0
    sh.show_object_outline = False
    sc.render.film_transparent = False
    cam = bpy.data.objects.get("MAP_CAM") or bpy.data.objects.new("MAP_CAM", bpy.data.cameras.new("MAP_CAM"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    sc.camera = cam
    meta = {}
    for name, (loc, d, up, ur, vr) in VIEWS.items():
        w, h = ur[1] - ur[0], vr[1] - vr[0]
        cu, cv = (ur[0] + ur[1]) / 2, (vr[0] + vr[1]) / 2
        # place the camera over the view centre
        loc = Vector(loc)
        if name.startswith("side"):
            loc.y, loc.z = cu, cv
        elif name in ("front", "rear"):
            loc.x, loc.z = cu, cv
        else:
            loc.x, loc.y = cu, cv
        cam.location = loc
        cam.rotation_euler = Vector(d).to_track_quat("-Z", "Y" if name != "top" else "Y").to_euler()
        if name == "top":
            cam.rotation_euler = (0, 0, 0)
        cam.data.ortho_scale = max(w, h)
        sc.render.resolution_x = int(round(w * PX_PER_M))
        sc.render.resolution_y = int(round(h * PX_PER_M))
        sc.render.resolution_percentage = 100
        p = os.path.join(OUT, "cav_%s.png" % name)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        meta[name] = {"u": ur, "v": vr, "px_per_m": PX_PER_M, "w": sc.render.resolution_x, "h": sc.render.resolution_y}
    json.dump(meta, open(os.path.join(OUT, "cav_meta.json"), "w"), indent=1)
    return meta


if __name__ == "__main__":
    print("==", main())
