"""Render check views of the model to export/views/ (runs inside Blender, workbench, no UI needed)."""
import math
import os

import bpy
from mathutils import Vector

OUT = r"D:\Claude\vauxhall_nova_gte_1989\export\views"


def cam(name, loc, target, ortho=None, lens=50):
    c = bpy.data.objects.get(name)
    if c is None:
        c = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        bpy.context.scene.collection.objects.link(c)
    c["no_export"] = 1
    c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        c.data.type = "ORTHO"; c.data.ortho_scale = ortho
    else:
        c.data.type = "PERSP"; c.data.lens = lens
    return c


def render(views=None, res=(1600, 900)):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    hidden = []
    for o in bpy.data.objects:
        if o.get("no_export") and o.type == "MESH" and not o.hide_render:
            o.hide_render = True; hidden.append(o)
    allv = {
        "side_right": ((-8.0, 0.0, 0.70), (0.0, 0.0, 0.70), 4.2),
        "front": ((0.0, -8.0, 0.70), (0.0, 0.0, 0.70), 2.4),
        "rear": ((0.0, 8.0, 0.70), (0.0, 0.0, 0.70), 2.4),
        "top": ((0.0, 0.0, 8.0), (0.0, 0.0, 0.0), 4.2),
        "q_front_right": ((-4.2, -4.6, 1.5), (0.0, -0.2, 0.55), None),
        "q_rear_left": ((3.8, 4.6, 1.6), (0.0, 0.2, 0.55), None),
    }
    out = []
    for name in (views or allv):
        loc, tgt, ortho = allv[name]
        sc.camera = cam("CHK_" + name, loc, tgt, ortho)
        if name == "top":
            sc.camera.rotation_euler = (0, 0, 0)
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
    for o in hidden:
        o.hide_render = False
    return out


if __name__ == "__main__":
    print(render())
