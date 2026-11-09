"""Rebuild the lower and rear edges of NICK3_front_clip (reproducible).

Input: mesh data `OLD_front_clip_pre_trim` (original stock clip). Output: new mesh.
 1. bisect at z=ZC (removes the stock folded hem) and y=YR (clean rear edge)
 2. delete the thin floating hem strip left on the cut
 3. extrude both skin layers' lower boundary straight down to the splitter top, bridge them with a
    closed 5 mm cap -> clean solid lower edge sitting on the splitter
Loops are handled as vertex REFERENCES (bmesh .index values go stale after operators).
"""
import bpy, bmesh, collections
from mathutils import Vector

ZC = -0.020
YR = -1.68


def zt(y):  # splitter top surface height
    return -0.053 - 0.0232 * (y + 2.128)


def _loops(edges):
    adj = collections.defaultdict(list); emap = collections.defaultdict(list)
    for e in edges:
        a, b = e.verts
        adj[a].append(b); adj[b].append(a); emap[a].append(e); emap[b].append(e)
    seen = set(); out = []
    for k in list(adj):
        if k in seen: continue
        st = [k]; seen.add(k); c = []; es = set()
        while st:
            a = st.pop(); c.append(a)
            for e in emap[a]: es.add(e)
            for b in adj[a]:
                if b not in seen: seen.add(b); st.append(b)
        out.append((c, list(es)))
    return out


def build(obj, old_mesh, skirt_clear=0.003):
    mw = obj.matrix_world; mwi = mw.inverted()
    bm = bmesh.new(); bm.from_mesh(old_mesh)

    def cut(co, no, inner):
        g = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=g, dist=1e-5, plane_co=co, plane_no=no,
                               clear_inner=inner, clear_outer=not inner)
    cut((0, 0, ZC), (0, 0, 1), True)
    cut((0, YR, 0), (0, 1, 0), False)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')

    def lowedges():
        return [e for e in bm.edges if e.is_boundary and all(abs((mw @ v.co).z - ZC) < 0.0008 for v in e.verts)]

    X = lambda v: (mw @ v.co).x
    LP = _loops(lowedges())
    kill = set()
    for side in (1, -1):
        cand = [(c, es) for c, es in LP if max(side * X(v) for v in c) > 0.8]
        cand.sort(key=lambda t: len(t[0]))
        region = set(f for v in cand[0][0] for f in v.link_faces)
        for _ in range(6):
            new = set()
            for f in region:
                for e in f.edges:
                    for g in e.link_faces:
                        if g not in region and (mw @ g.calc_center_median()).z < 0.04: new.add(g)
            if not new: break
            region |= new
        kill |= region
    bmesh.ops.delete(bm, geom=list(kill), context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')

    uvl = bm.loops.layers.uv.active
    LP = _loops(lowedges())
    for side in (1, -1):
        two = [(c, es) for c, es in LP if max(side * X(v) for v in c) > 0.8]
        assert len(two) == 2, (side, len(two))
        newloops = []
        for cv, es in two:
            uvmap = {}
            for v in cv:
                for l in v.link_loops:
                    uvmap[(round(v.co.x, 5), round(v.co.y, 5))] = l[uvl].uv.copy(); break
            r = bmesh.ops.extrude_edge_only(bm, edges=es)
            nv = [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]
            ne = [g for g in r['geom'] if isinstance(g, bmesh.types.BMEdge)]
            nf = [g for g in r['geom'] if isinstance(g, bmesh.types.BMFace)]
            nvs = set(nv)
            bottom = [e for e in ne if all(v in nvs for v in e.verts)]
            for v in nv:
                w = mw @ v.co
                v.co = mwi @ Vector((w.x, w.y, zt(w.y) - skirt_clear))
            for f in nf:
                for l in f.loops:
                    key = (round(l.vert.co.x, 5), round(l.vert.co.y, 5))
                    if key in uvmap: l[uvl].uv = uvmap[key]
            newloops += bottom
        r = bmesh.ops.bridge_loops(bm, edges=newloops)
        for f in r['faces']:
            for l in f.loops: l[uvl].uv = (0, 0)
    bm.normal_update()
    me = bpy.data.meshes.new("NICK3_front_clip_mesh_trimmed")
    bm.to_mesh(me); bm.free()
    for m in old_mesh.materials: me.materials.append(m)
    return me
