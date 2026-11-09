"""nick3_measure.py - numeric clearance checks (world space, metres)."""
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TYRES={'FL':'M_Tire_Max_Toyo_Proxes_TQ_Medium003.001','FR':'M_Tire_Max_Toyo_Proxes_TQ_Medium001.001',
       'RL':'M_Tire_Max_Toyo_Proxes_TQ_Medium004.001','RR':'M_Tire_Max_Toyo_Proxes_TQ_Medium002.001'}

def world_bvh(ob):
    dg=bpy.context.evaluated_depsgraph_get(); ev=ob.evaluated_get(dg)
    me=ev.to_mesh(); bm=bmesh.new(); bm.from_mesh(me); bm.transform(ob.matrix_world)
    bmesh.ops.triangulate(bm,faces=bm.faces[:])
    verts=[v.co.copy() for v in bm.verts]; tris=[[v.index for v in f.verts] for f in bm.faces]
    bm.free(); ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts,tris), verts

def clearance(obj_name, tyre_key, scene=None):
    """min distance between object surface and tyre surface, checked both ways (vertex->surface)."""
    ob=bpy.data.objects[obj_name]; ty=bpy.data.objects[TYRES[tyre_key]]
    bo,vo=world_bvh(ob); bt,vt=world_bvh(ty)
    best=(9,None)
    for v in vo:
        r=bt.find_nearest(v)
        if r[0] is not None and r[3]<best[0]: best=(r[3],('obj->tyre',tuple(round(c,3) for c in v)))
    for v in vt:
        r=bo.find_nearest(v)
        if r[0] is not None and r[3]<best[0]: best=(r[3],('tyre->obj',tuple(round(c,3) for c in v)))
    return best

def inside_count(obj_name, tyre_key):
    """number of obj vertices inside the tyre volume (ray parity along +x/-x not reliable; use nearest+normal)"""
    ob=bpy.data.objects[obj_name]; ty=bpy.data.objects[TYRES[tyre_key]]
    bt,_=world_bvh(ty); n=0
    for v in ob.data.vertices:
        w=ob.matrix_world@v.co; r=bt.find_nearest(w)
        if r[0] is not None and (w-r[0]).dot(r[1])<0: n+=1
    return n
