"""Export the reference-model car (export/ref/nova_ref_mat.blend: REF_BODY + GLASS_* from prep_reference.py) into the
car package, with the project's wheels/helpers and the RHD driver cluster (steering wheel, column, binnacle, dials,
needles - analog_instruments.ini needs the ARROW_* nodes). The model's own (LHD) interior is part of REF_BODY."""
import math
import os

import bmesh
import bpy

import export_car as ec

DRIVER = ("STEER_WHEEL", "INT_COLUMN")      # INT_BINNACLE dropped: the dials sit in the model's (mirrored) instrument recess


def hull():
    body = bpy.data.objects["REF_BODY"]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.transform(body.matrix_world)
    keep = set(list(bm.verts)[::150])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in keep], context="VERTS")
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(8), verts=bm.verts[:], edges=bm.edges[:])
    old = bpy.data.objects.get("COLLIDER_ref")
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new("COLLIDER_ref")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("COLLIDER_ref", me)
    bpy.data.collections["REF"].objects.link(o)
    o.hide_render = True
    o.display_type = "WIRE"
    o.hide_set(True)
    o["no_export"] = 1
    return o


def export():
    O = bpy.data.objects
    top = [O["REF_BODY"]] + sorted((o for o in O if o.name.startswith(("GLASS_", "DET_")) and o.type == "MESH" and o.parent is None
                                    and "REF" in [c.name for c in o.users_collection]), key=lambda o: o.name)
    interior = bpy.data.collections["INTERIOR"].objects
    top += sorted((o for o in interior if o.parent is None and (o.name in DRIVER or o.name.startswith(("INT_DIAL_", "ARROW_")))),
                  key=lambda o: o.name)
    # STEER_WHEEL hangs under STEER_HR (helpers): exported with it
    for o in interior:
        if o.parent is not None and o.name not in DRIVER:
            o["no_export"] = 1
    if O.get("BONNET_HINGE"):
        top.append(O["BONNET_HINGE"])                 # hinge dummy with the new bonnet under it
    top += [O[n] for n in ec.HELPERS]
    exp = ec.writer()
    main = exp.export_kn5(os.path.join(ec.CAR, ec.CAR_ID + ".kn5"), top)
    col = exp.export_kn5(os.path.join(ec.CAR, "collider.kn5"), [hull()], collider=True)
    bpy.ops.wm.save_mainfile()
    return {"main": main, "collider": col, "objects": len(top)}


if __name__ == "__main__":
    print(export())
