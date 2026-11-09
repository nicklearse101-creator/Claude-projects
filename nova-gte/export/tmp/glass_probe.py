import bpy, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get()
def tree(names):
    V, T = [], []
    for n in names:
        o = bpy.data.objects.get(n)
        if not o:
            continue
        me = o.evaluated_get(dg).to_mesh(); m = o.matrix_world; k = len(V)
        V += [tuple(m @ v.co) for v in me.vertices]
        for p in me.polygons:
            vs = list(p.vertices)
            for i in range(1, len(vs) - 1):
                T.append((k + vs[0], k + vs[i], k + vs[i + 1]))
        o.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(V, T)
g = tree(["GLASS_SCREEN_L"]); s = tree(["Body_Shell"])
o = bpy.data.objects["GLASS_SCREEN_L"]
print("screen mods:", [m.type for m in o.modifiers], "verts", len(o.data.vertices), "faces", len(o.data.polygons))
xs = np.arange(-0.60, 0.61, 0.06); zs = np.arange(1.30, 0.88, -0.03)
print("front view: G = glass, S = shell, . = see-through   x from -0.60 to 0.60")
for z in zs:
    row = ""
    for x in xs:
        p = Vector((x, -3.0, z)); d = Vector((0, 1, 0))
        hg = g.ray_cast(p, d, 6); hs = s.ray_cast(p, d, 6)
        if hg[0] and (not hs[0] or hg[3] <= hs[3] + 1e-4): row += "G"
        elif hs[0]: row += "S"
        else: row += "."
    print("z %.2f %s" % (z, row))
b = [o.matrix_world @ v.co for v in o.data.vertices]
print("screen pane x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f" % (min(v.x for v in b), max(v.x for v in b), min(v.y for v in b), max(v.y for v in b), min(v.z for v in b), max(v.z for v in b)))
