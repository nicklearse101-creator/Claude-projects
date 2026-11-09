"""Export nova_gen.blend (generated body, see fit_generated / prep_generated) into the car package.
Same writer and package as export_car.py; the body is GEN_BODY + GEN_GLASS instead of the procedural shell."""
import math
import os

import bmesh
import bpy

import export_car as ec


def hull():
    body = bpy.data.objects["GEN_BODY"]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.transform(body.matrix_world)
    keep = set(list(bm.verts)[::12])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in keep], context="VERTS")
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(8), verts=bm.verts[:], edges=bm.edges[:])
    old = bpy.data.objects.get("COLLIDER_gen")
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new("COLLIDER_gen")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("COLLIDER_gen", me)
    bpy.data.collections["GEN"].objects.link(o)
    o.hide_render = True
    o.display_type = "WIRE"
    o.hide_set(True)                                   # helper only: never drawn over the car in the viewport
    o["no_export"] = 1
    return o


def export():
    O = bpy.data.objects
    body = O["GEN_BODY"]
    paint = bpy.data.materials["paint_gunmetal"]
    for slot in body.material_slots:                    # nearest-zone hits on the old shell's inside -> paint
        if slot.material and slot.material.name.startswith("int_"):
            slot.material = paint
    top = [body, O["GEN_GLASS"]]
    top += sorted((o for o in O if o.name.startswith("ARCH_LINER_") and o.parent is None), key=lambda o: o.name)
    det = bpy.data.collections.get("INTERIOR")
    top += sorted((o for o in det.objects if o.parent is None and not o.get("no_export")), key=lambda o: o.name)
    top += [O[n] for n in ec.HELPERS]
    exp = ec.writer()
    main = exp.export_kn5(os.path.join(ec.CAR, ec.CAR_ID + ".kn5"), top)
    col = exp.export_kn5(os.path.join(ec.CAR, "collider.kn5"), [hull()], collider=True)
    bpy.ops.wm.save_mainfile()
    return {"main": main, "collider": col}


if __name__ == "__main__":
    print(export())
