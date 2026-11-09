"""Island utilities for NICK3 clean-up (metres, car faces -Y, +Z up, +X = car left)."""
import bpy, bmesh

def islands(bm):
    bm.verts.ensure_lookup_table()
    seen = set(); res = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; seen.add(v.index); comp = []
        while st:
            a = st.pop(); comp.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen: seen.add(b.index); st.append(b)
        res.append(comp)
    return res

def island_stats(comp, mw):
    pts = [mw @ c.co for c in comp]
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    return mn, mx, [(mn[i]+mx[i])/2 for i in range(3)]

def delete_islands(obj, test):
    """test(n_verts, mn, mx, centre) -> bool. Deletes matching islands, returns number of verts removed."""
    me = obj.data; mw = obj.matrix_world
    bm = bmesh.new(); bm.from_mesh(me)
    kill = []
    for comp in islands(bm):
        mn, mx, c = island_stats(comp, mw)
        if test(len(comp), mn, mx, c): kill += comp
    n = len(kill)
    if n:
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(me); me.update()
    bm.free()
    return n
