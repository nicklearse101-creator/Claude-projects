"""Quick workbench renders of the current scene: qrender.shots(prefix, objects=None, views=...)."""
import bpy, math
from mathutils import Vector

VIEWS = {"fl": (1.0, -1.2, 0.55), "rl": (1.0, 1.2, 0.55), "side": (1, 0, 0.05), "front": (0, -1, 0.1),
         "rear": (0, 1, 0.1), "top": (0.001, 0, 1), "fr": (-1.0, -1.2, 0.55), "low_side": (1, -0.25, -0.02)}

def shots(prefix, objs=None, views=("fl", "rl", "side", "front"), res=1100, center=None, dist=6.5, ortho=None, colour="MATERIAL"):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = colour
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = res; sc.render.resolution_y = int(res * 0.62)
    sc.render.film_transparent = False
    keep = None if objs is None else set(objs)
    for ob in sc.objects:
        if ob.type == "MESH":
            ob.hide_render = (keep is not None and ob.name not in keep) or bool(ob.get("qr_hide"))
    if sc.world is None:
        sc.world = bpy.data.worlds.new("QW")
    sc.world.color = (0.05, 0.05, 0.06)
    sc.display.shading.background_type = "WORLD"
    cam_d = bpy.data.cameras.new("QCAM"); cam = bpy.data.objects.new("QCAM", cam_d); sc.collection.objects.link(cam)
    sc.camera = cam
    c = Vector(center or (0, 0, 0.45))
    out = []
    for v in views:
        d = Vector(VIEWS[v] if isinstance(v, str) else v).normalized()
        cam.location = c + d * dist
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        if ortho: cam_d.type = "ORTHO"; cam_d.ortho_scale = ortho
        else: cam_d.lens = 50
        name = v if isinstance(v, str) else "v"
        sc.render.filepath = f"{prefix}_{name}.png"
        bpy.ops.render.render(write_still=True); out.append(sc.render.filepath)
    bpy.data.objects.remove(cam)
    return out
