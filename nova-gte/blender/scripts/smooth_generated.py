"""Smooth the lumpy generated panels: Laplacian-style vertex smoothing on GEN_BODY, skipping open edges and
creases sharper than 35 deg (panel edges, arch lips, bumper lines stay crisp)."""
import math
import bmesh, bpy

def smooth(iters=6, factor=0.5, crease=35.0):
    ob = bpy.data.objects["GEN_BODY"]
    bm = bmesh.new(); bm.from_mesh(ob.data)
    lim = math.radians(crease)
    keep = set()
    for e in bm.edges:
        if not e.is_manifold or (len(e.link_faces) == 2 and e.calc_face_angle(0) > lim):
            keep.update(e.verts)
    vs = [v for v in bm.verts if v not in keep]
    for _ in range(iters):
        bmesh.ops.smooth_vert(bm, verts=vs, factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(ob.data); bm.free()
    return {"smoothed": len(vs), "kept": len(keep)}
