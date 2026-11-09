"""Stills of the car rendered to PNG files (EEVEE) - screenshots for Nik without viewport captures.
Renders only what the viewport shows: the stock parts the build stows are viewport-hidden but still render-enabled,
so every mesh that is not visible_get() is hidden for the render. Temporary camera/sun/ground, all removed after.
Settings used for the 6 Oct shots:

    shots = load("render_stills")
    shots.render("engine", (0.62, -2.02, 1.12), (0.02, -1.24, 0.43), lens=28, hide=shots.bonnet())
    shots.render("belts", (0.0, 0.30, 2.0), (0.0, 0.95, 0.30), lens=32, clip=1.24, sun_shadow=False)  # roof cut away
    shots.render("rear", (1.45, 2.65, 0.16), (0.45, 1.62, 0.20), lens=32, ground=-0.1506, sun_rot=(50, 0, 60))
"""
import math
import os

import bpy
from mathutils import Vector

OUT = r"D:\Claude\talbot_sunbeam_lotus\docs\screenshots"


def descendants(name):
    root = bpy.data.objects.get(name)
    if not root:
        return []
    out, todo = [], [root]
    while todo:
        o = todo.pop()
        out.append(o)
        todo.extend(o.children)
    return out


def render(name, loc, target, lens=35, clip=0.05, hide=(), res=(1600, 900), engine="BLENDER_EEVEE", sun_shadow=True,
           ground=None, sun_rot=(40, -25, 35), sun_energy=3.0):
    """Camera at loc looking at target; clip > the near-side panels' distance gives a cutaway. ground = z of a grey
    floor (tyre bottoms are at -0.1506). Returns the PNG path."""
    sc = bpy.context.scene
    cam_data = bpy.data.cameras.new("TMP_shot")
    cam_data.lens, cam_data.clip_start, cam_data.clip_end = lens, clip, 50
    cam = bpy.data.objects.new("TMP_shot", cam_data)
    sc.collection.objects.link(cam)
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sun_data = bpy.data.lights.new("TMP_sun", 'SUN')
    sun_data.energy, sun_data.angle = sun_energy, math.radians(8)
    sun_data.use_shadow = sun_shadow
    sun = bpy.data.objects.new("TMP_sun", sun_data)
    sc.collection.objects.link(sun)
    sun.rotation_euler = tuple(math.radians(a) for a in sun_rot)
    gnd = None
    if ground is not None:
        gm = bpy.data.meshes.new("TMP_ground")
        gm.from_pydata([(-20, -20, ground), (20, -20, ground), (20, 20, ground), (-20, 20, ground)], [], [(0, 1, 2, 3)])
        mat = bpy.data.materials.get("TMP_ground_mat") or bpy.data.materials.new("TMP_ground_mat")
        mat.use_nodes = True
        b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs["Base Color"].default_value = (0.42, 0.42, 0.42, 1)
        b.inputs["Roughness"].default_value = 0.8
        gm.materials.append(mat)
        gnd = bpy.data.objects.new("TMP_ground", gm)
        sc.collection.objects.link(gnd)
    bg = next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND')
    old_bg = (tuple(bg.inputs[0].default_value), bg.inputs[1].default_value)
    bg.inputs[0].default_value, bg.inputs[1].default_value = (0.55, 0.57, 0.6, 1), 1.2
    old = dict(cam=sc.camera, engine=sc.render.engine, res=(sc.render.resolution_x, sc.render.resolution_y),
               pct=sc.render.resolution_percentage, path=sc.render.filepath)
    hidden = []
    vl = bpy.context.view_layer
    hide = set(hide) | {o for o in vl.objects if o.type == 'MESH' and not o.visible_get()}
    for o in hide:
        hidden.append((o, o.hide_render, o.visible_camera, o.visible_shadow))
        o.hide_render, o.visible_camera, o.visible_shadow = True, False, False
    path = os.path.join(OUT, f"{name}.png")
    try:
        sc.camera = cam
        try:
            sc.render.engine = engine
        except TypeError:
            pass
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 100
        if hasattr(sc.eevee, "taa_render_samples"):
            sc.eevee.taa_render_samples = 32
        os.makedirs(OUT, exist_ok=True)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
    finally:
        for o, hr, vc, vs in hidden:
            o.hide_render, o.visible_camera, o.visible_shadow = hr, vc, vs
        sc.camera = old["cam"]
        sc.render.engine = old["engine"]
        sc.render.resolution_x, sc.render.resolution_y = old["res"]
        sc.render.resolution_percentage = old["pct"]
        sc.render.filepath = old["path"]
        bg.inputs[0].default_value, bg.inputs[1].default_value = old_bg
        bpy.data.objects.remove(cam)
        bpy.data.cameras.remove(cam_data)
        bpy.data.objects.remove(sun)
        bpy.data.lights.remove(sun_data)
        if gnd:
            gm = gnd.data
            bpy.data.objects.remove(gnd)
            bpy.data.meshes.remove(gm)
        m = bpy.data.materials.get("TMP_ground_mat")
        if m and not m.users:
            bpy.data.materials.remove(m)
    return path


def bonnet():
    """The bonnet and its liners (hidden for engine-bay shots)."""
    objs = descendants("MOTORHOOD") + descendants("hoodliner_a__slod")
    objs.append(bpy.data.objects["enginebay_a__slod_SUB1.001"])   # black plane under the bonnet
    return [o for o in objs if o.type == 'MESH']
