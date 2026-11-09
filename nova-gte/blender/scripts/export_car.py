"""Export the open nova_gte.blend into the project's car package (runs inside Blender).

Writes car/vauxhall_nova_gte_1989/vauxhall_nova_gte_1989.kn5 and collider.kn5 with the Sunbeam
project's kn5 writer (tools/ac_kn5_export.py there; reused, not copied, so fixes stay in one place).
Deployment to AC is a separate step (tools/deploy.py).
"""
import importlib.util
import math
import os

import bmesh
import bpy

KN5_WRITER = r"D:\Claude\vauxhall_nova_gte_1989\tools\ac_kn5_export.py"   # Nova copy of the Sunbeam writer + glass blending
CAR = r"D:\Claude\vauxhall_nova_gte_1989\car\vauxhall_nova_gte_1989"
CAR_ID = "vauxhall_nova_gte_1989"
HELPERS = [f"{p}_{t}" for p in ("WHEEL", "SUSP") for t in ("LF", "RF", "LR", "RR")] + ["COCKPIT_HR", "COCKPIT_LR", "STEER_HR"]


def writer():
    spec = importlib.util.spec_from_file_location("ac_kn5_export", KN5_WRITER)
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
    bm.transform(body.matrix_world)
    ev.to_mesh_clear()
    # hull of a thinned point set: AC colliders should stay a few hundred triangles
    keep = set(list(bm.verts)[::25])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in keep], context="VERTS")
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(8), verts=bm.verts[:], edges=bm.edges[:])
    for f in bm.faces:
        f.material_index = 0
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
    hull.display_type = "WIRE"
    hull.hide_render = True
    hull["no_export"] = 1
    return hull


def export():
    exp = writer()
    O = bpy.data.objects
    os.makedirs(CAR, exist_ok=True)
    top = [O["BODY_shell"]] + ([O["BODY_glass"]] if "BODY_glass" in O else [])
    top += sorted((o for o in bpy.data.collections["BODY"].objects                     # inset glass panels + seals
                   if o.parent is None and not o.get("no_export") and o.type == "MESH" and o not in top),
                  key=lambda o: o.name)
    for cname in ("FRONT", "SIDE", "REAR", "DETAILS", "INTERIOR"):
        det = bpy.data.collections.get(cname)
        if det:
            top += sorted((o for o in det.objects if o.parent is None and not o.get("no_export")), key=lambda o: o.name)
    top += [O[n] for n in HELPERS]
    main = exp.export_kn5(os.path.join(CAR, CAR_ID + ".kn5"), top)
    col = exp.export_kn5(os.path.join(CAR, "collider.kn5"), [rebuild_collider()], collider=True)
    bpy.ops.wm.save_mainfile()
    return {"main": main, "collider": col}


if __name__ == "__main__":
    print(export())
