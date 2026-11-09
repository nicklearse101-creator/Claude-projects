
import bpy, bmesh, math
from mathutils import Vector, Matrix

CARBON_MESHES = ["NICK3_STATIC_MESH_NICK3_carbon.001"]
LOD_MESHES = ["NICK3_LOD_MESH_NICK3_carbon.001","NICK3_LOD_MESH_NICK3_carbon.003","NICK3_LOD_MESH_NICK3_carbon.005"]

def islands(bm):
    bm.verts.ensure_lookup_table()
    seen=set(); parts=[]
    for v in bm.verts:
        if v.index in seen: continue
        st=[v]; seen.add(v.index); c=[]
        while st:
            a=st.pop(); c.append(a)
            for e in a.link_edges:
                b=e.other_vert(a)
                if b.index not in seen: seen.add(b.index); st.append(b)
        parts.append(c)
    return parts

def bbox(vs, mw=None):
    ps=[(mw@v.co) if mw else v.co for v in vs]
    return (min(p.x for p in ps),max(p.x for p in ps),min(p.y for p in ps),max(p.y for p in ps),min(p.z for p in ps),max(p.z for p in ps))

def delete_islands(obj, pred):
    me=obj.data; mw=obj.matrix_world
    bm=bmesh.new(); bm.from_mesh(me)
    dele=[]; n=0
    for c in islands(bm):
        if pred(c, bbox(c,mw)):
            dele+=c; n+=1
    bmesh.ops.delete(bm,geom=dele,context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return n

def solid_from_outline(pts3, thickness_vec, bevel=0.004, segs=2):
    """pts3: list of world-space Vector forming a closed planar-ish outline (CCW seen from +thickness side).
    Extrudes by thickness_vec (negative side), bevels all edges, returns bmesh (world coords)."""
    bm=bmesh.new()
    vs=[bm.verts.new(p) for p in pts3]
    f=bm.faces.new(vs)
    # make sure the face normal points along +thickness (outwards on top)
    if f.normal.dot(thickness_vec)>0: f.normal_flip()
    # extrude opposite to normal direction: use thickness_vec as direction of the back side
    r=bmesh.ops.extrude_face_region(bm,geom=[f])
    nv=[e for e in r['geom'] if isinstance(e,bmesh.types.BMVert)]
    bmesh.ops.translate(bm,vec=thickness_vec,verts=nv)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
    if bevel>0:
        bmesh.ops.bevel(bm,geom=list(bm.edges),offset=bevel,segments=segs,profile=0.5,affect='EDGES')
    return bm

def inject(bm, obj, matidx=0, uvscale=1.0, flip=False):
    """append bmesh bm (world coords) into mesh object obj"""
    me=obj.data; mi=obj.matrix_world.inverted()
    b2=bmesh.new(); b2.from_mesh(me)
    uvl=b2.loops.layers.uv.active
    vmap={}
    for v in bm.verts: vmap[v]=b2.verts.new(mi@v.co)
    for f in bm.faces:
        try:
            nf=b2.faces.new([vmap[v] for v in f.verts])
        except ValueError:
            continue
        nf.material_index=matidx; nf.smooth=True
        for l in nf.loops:
            co=l.vert.co
            l[uvl].uv=((co.x+co.y)*uvscale,(co.z+co.y*0.5)*uvscale)
    b2.normal_update()
    b2.to_mesh(me); b2.free(); me.update()

def sections_ok():
    return True
