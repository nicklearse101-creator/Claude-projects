import bpy, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get()
def tree(pred):
    V, T = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not pred(o.name) or o.hide_render:
            continue
        me = o.evaluated_get(dg).to_mesh(); m = o.matrix_world; k = len(V)
        V += [tuple(m @ v.co) for v in me.vertices]
        for p in me.polygons:
            vs = list(p.vertices)
            for i in range(1, len(vs) - 1):
                T.append((k + vs[0], k + vs[i], k + vs[i + 1]))
        o.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(V, T)
nc = bpy.data.collections.get("NOVA_NEW")
names = {o.name for o in nc.objects} if nc else {o.name for o in bpy.data.objects}
g = tree(lambda n: n.startswith("GLASS_") and n in names)
b = tree(lambda n: (not n.startswith("GLASS_")) and n in names)
def scan(label, origin, d, us, vs, mk):
    print(label)
    for v in vs:
        row = ""
        for u in us:
            p = mk(u, v); hg = g.ray_cast(p, d, 8); hb = b.ray_cast(p, d, 8)
            row += "G" if hg[0] and (not hb[0] or hg[3] <= hb[3] + 1e-4) else ("B" if hb[0] else ".")
        print("  %.2f %s" % (v, row))
scan("REAR view (x -0.6..0.6 across, z down)", None, Vector((0, -1, 0)), np.arange(-0.6, 0.61, 0.05), np.arange(1.25, 0.80, -0.03),
     lambda u, v: Vector((u, 4.0, v)))
scan("LEFT SIDE view (y -0.8..1.6 across, z down)", None, Vector((-1, 0, 0)), np.arange(-0.8, 1.61, 0.08), np.arange(1.25, 0.84, -0.03),
     lambda u, v: Vector((4.0, u, v)))
