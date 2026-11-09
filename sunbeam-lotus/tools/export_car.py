"""Export the Sunbeam from the open .blend into the AC car folder (runs in Blender).

  * main model: BODY_shell, BODY_arch_flares, every DETAILS object, and the AC
    helper nodes (WHEEL_/SUSP_ top-level siblings, COCKPIT_HR/LR, STEER_HR)
  * collider.kn5: convex hull of the evaluated body, rebuilt every export
  * deletes data/proview_nodes.ini so AC rewrites it for the current node tree
  * renders skins/works_white/preview.jpg and a progress snapshot
"""
import importlib.util
import math
import os

import bmesh
import bpy
from mathutils import Vector

TOOLS = r"D:\Claude\talbot_sunbeam_lotus\tools"
CAR = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works"
CAR_ID = "talbot_sunbeam_lotus_81_works"
HELPERS = [f"{p}_{t}" for p in ("WHEEL", "SUSP") for t in ("LF", "RF", "LR", "RR")] + ["COCKPIT_HR", "COCKPIT_LR", "STEER_HR"]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rebuild_collider():
    body = bpy.data.objects["BODY_shell"]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    src = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(src)
    ev.to_mesh_clear()
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(8), verts=bm.verts[:], edges=bm.edges[:])
    for f in bm.faces:
        f.material_index = 0            # one mesh; the hull inherits the body's glass/rubber indices otherwise
    old = bpy.data.objects.get("COLLIDER_hull")
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    me = bpy.data.meshes.new("COLLIDER_hull")
    bm.to_mesh(me)
    bm.free()
    hull = bpy.data.objects.new("COLLIDER_hull", me)
    bpy.data.collections["BODY"].objects.link(hull)
    hull.display_type = "WIRE"; hull.hide_render = True; hull.hide_set(True)
    return hull


def render_previews(snapshot_name):
    scene = bpy.context.scene
    old = (scene.render.filepath, scene.render.image_settings.file_format)
    shots = [(os.path.join(CAR, "skins", "works_white", "preview.jpg"), "JPEG"),
             (os.path.join(r"D:\Claude\talbot_sunbeam_lotus\progress", snapshot_name), "PNG")]
    for area in bpy.context.screen.areas:
        if area.type != "VIEW_3D":
            continue
        sp = area.spaces.active; r3d = sp.region_3d
        region = next(r for r in area.regions if r.type == "WINDOW")
        sp.shading.show_xray = False; sp.shading.color_type = "MATERIAL"
        eye = Vector((3.4, -4.1, 1.45))
        r3d.view_perspective = "PERSP"; r3d.view_rotation = (-eye).to_track_quat("-Z", "Y")
        r3d.view_location = (0.0, -0.1, 0.55); r3d.view_distance = 5.0; r3d.update()
        ov = sp.overlay.show_overlays; sp.overlay.show_overlays = False
        with bpy.context.temp_override(area=area, region=region):
            for path, fmt in shots:
                scene.render.filepath = path; scene.render.image_settings.file_format = fmt
                bpy.ops.render.opengl(write_still=True, view_context=True)
        sp.overlay.show_overlays = ov
        break
    scene.render.filepath, scene.render.image_settings.file_format = old
    return shots[1][0]


def export(snapshot_name="snapshot.png"):
    exp = _load("ac_kn5_export")
    O = bpy.data.objects
    top = [O["BODY_shell"], O["BODY_arch_flares"]]
    top += sorted((o for o in bpy.data.collections["DETAILS"].objects if o.parent is None), key=lambda o: o.name)
    top += [O[n] for n in HELPERS]
    main = exp.export_kn5(os.path.join(CAR, CAR_ID + ".kn5"), top)
    col = exp.export_kn5(os.path.join(CAR, "collider.kn5"), [rebuild_collider()], collider=True)
    pv = os.path.join(CAR, "data", "proview_nodes.ini")
    if os.path.exists(pv):
        os.remove(pv)
    snap = render_previews(snapshot_name)
    bpy.ops.wm.save_mainfile(relative_remap=True)
    return {"main": main, "collider": col, "snapshot": snap}
