"""Plain grey model views for shape checks against reference/photos/grey_studio/{side,front,rear}.png (Nik 2026-10-19:
compare a grey model, not the paint colours). Workbench, studio light with cavity, every part one grey, glass dark,
rubber/seals near-black; orthographic: side from the car's left (front on the left, as the reference), front, rear.
Writes export/match/grey_<view>.png (transparent background). tools/compare_grey.py lines them up with the references.
Run: blender -b export/ref/nova_ref_mat.blend --python blender/scripts/grey_views.py"""
import os

import bpy
from mathutils import Euler, Vector

OUT = r"D:\Claude\vauxhall_nova_gte_1989\export\match"
PX = 0.002                                      # metres per pixel
VIEWS = {  # name: (camera location, euler, width m, height m)
    "side": ((3.0, -0.03, 0.70), (1.5708, 0, 1.5708), 4.2, 1.6),
    "front": ((0.0, -4.0, 0.70), (1.5708, 0, 0.0), 2.0, 1.6),
    "rear": ((0.0, 4.0, 0.70), (1.5708, 0, 3.14159), 2.0, 1.6),
}
GREY, GLASS, RUBBER = (0.42, 0.43, 0.44, 1), (0.07, 0.08, 0.09, 1), (0.05, 0.05, 0.05, 1)


def main(views=None):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "OBJECT"
    sh.show_cavity = True; sh.cavity_type = "BOTH"
    sh.show_object_outline = False; sh.show_specular_highlight = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_percentage = 100
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        n = o.name
        hide = bool(o.get("no_export")) or n.startswith(("COLLIDER", "CUT_", "MAP", "NRM_PROXY")) or \
            any(c.name in ("SHELL_MAP",) for c in o.users_collection)
        o.hide_render = hide
        o.color = GLASS if n.startswith("GLASS_") else RUBBER if n.startswith(("DET_SEAL", "DET_WS_RUBBER", "DET_TG_SEAL", "TIRE_"))             else (0.75, 0.75, 0.76, 1) if n.startswith("RIM_") else GREY
    sm = bpy.data.collections.get("SHELL_MAP")
    if sm:
        sm.hide_render = True
    wc = bpy.data.collections.get("WHEELS")              # the car's own wheels (exported via the WHEEL_ helpers)
    if wc:
        wc.hide_render = False
    cam = bpy.data.objects.get("GREY_CAM") or bpy.data.objects.new("GREY_CAM", bpy.data.cameras.new("GREY_CAM"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam["no_export"] = 1
    cam.data.type = "ORTHO"; cam.data.clip_start = 0.1; cam.data.clip_end = 20
    sc.camera = cam
    out = []
    for name, (loc, rot, w, h) in VIEWS.items():
        if views and name not in views:
            continue
        cam.location = Vector(loc); cam.rotation_euler = Euler(rot)
        cam.data.ortho_scale = max(w, h)
        sc.render.resolution_x, sc.render.resolution_y = int(w / PX), int(h / PX)
        sc.render.filepath = os.path.join(OUT, "grey_%s.png" % name)
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
    # through the solved camera of the grey side picture (tools/photomatch/solve_grey.py): same framing as the picture
    import json
    from mathutils import Matrix
    J = json.load(open(os.path.join(os.path.dirname(os.path.dirname(OUT)), "tools", "photomatch", "grey_cams.json")))
    q = J["gS"]; W, H = J["W"], J["H"]
    rv = Vector(q[0:3]); ang = rv.length
    R = Matrix.Rotation(ang, 3, rv.normalized()) if ang > 0 else Matrix.Identity(3)
    C = -(R.transposed() @ Vector(q[3:6]))
    cam.data.type = "PERSP"; cam.data.sensor_fit = "HORIZONTAL"; cam.data.sensor_width = 36.0
    cam.data.lens = q[6] * 36.0 / W
    cam.matrix_world = Matrix.Translation(C) @ (R.transposed() @ Matrix(((1, 0, 0), (0, -1, 0), (0, 0, -1)))).to_4x4()
    sc.render.resolution_x, sc.render.resolution_y = W * 4, H * 4
    sc.render.filepath = os.path.join(OUT, "grey_pic_side.png")
    bpy.ops.render.render(write_still=True)
    out.append(sc.render.filepath)
    return out


if __name__ == "__main__":
    print("==", main())


FRONT_CAM = {"d": 11.16, "f": 1975.0, "u0": 164.4, "W": 329, "H": 257}   # front.png: from plate width, track, mirrors, body width


def pic_cam(view="front", h=1.0, v0=None, scale=4, name=None):
    """Perspective grey render matching Nik's grey front picture: camera on the centre line d m ahead of the plate,
    level, focal f px, principal point (u0, v0); v0 defaults to putting the front tyre contact on the picture's
    tyre bottom (v 235). Writes export/match/grey_pic_<view>[_name].png."""
    from math import radians
    C = FRONT_CAM
    sc = bpy.context.scene
    if v0 is None:
        v0 = 235 - C["f"] * h / (C["d"] + 1.842 - 1.172)
    cam = sc.camera
    cam.data.type = "PERSP"; cam.data.sensor_fit = "HORIZONTAL"; cam.data.sensor_width = 36.0
    cam.data.lens = C["f"] * 36.0 / C["W"]
    cam.data.shift_x = (C["W"] / 2 - C["u0"]) / C["W"]
    cam.data.shift_y = (v0 - C["H"] / 2) / C["W"]
    cam.data.clip_end = 40
    cam.location = Vector((0.0, -1.842 - C["d"], h)); cam.rotation_euler = Euler((radians(90), 0, 0))
    sc.render.resolution_x, sc.render.resolution_y = C["W"] * scale, C["H"] * scale
    sc.render.filepath = os.path.join(OUT, "grey_pic_%s%s.png" % (view, "_" + name if name else ""))
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath
