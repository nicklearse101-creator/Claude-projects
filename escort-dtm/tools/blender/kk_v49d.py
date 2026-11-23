"""v49d (2nd version): the v49 exact-boolean arch cut left sliver triangles (spikes behind the rear arches). Delete ONLY slivers made
by the cut: longest edge > 4 cm, area/L^2 < 0.02 AND at least one vertex that is not in the pre-cut panel (v48 blend).
The 1st version deleted every sliver near the arches and took out the original swage-line strips (white lines in game)."""
import bpy, bmesh
from mathutils import kdtree
V48 = r"D:\Claude\escort_mk2_dtm\blender\escort_v48 fog lamps.blend"
main = bpy.data.scenes["Scene"]
with bpy.data.libraries.load(V48) as (src, dst):
    dst.objects = list(src.objects)
old = {}
for o in dst.objects:
    if o is not None and o.type == "MESH" and o.get("kn5_name") in ("fenders_a_SUB2", "body_a_SUB1") and o.get("kn5_name") not in old:
        old[o.get("kn5_name")] = o
def wmat(o):                      # library-loaded objects are in no scene: matrix_world is stale, build it from the chain
    m = o.matrix_basis.copy()
    while o.parent:
        m = o.parent.matrix_basis @ o.matrix_parent_inverse @ m if False else wmat_parent(o) @ m
        break
    return m
def wmat_parent(o):
    return wmat(o.parent) @ o.matrix_parent_inverse
rep = {}
for name, oo in old.items():
    W = wmat(oo)
    kd = kdtree.KDTree(len(oo.data.vertices))
    for i, v in enumerate(oo.data.vertices):
        kd.insert(W @ v.co, i)
    kd.balance()
    o = next(o for o in main.objects if o.type == "MESH" and o.get("kn5_name") == name)
    mw = o.matrix_world
    bm = bmesh.new(); bm.from_mesh(o.data)
    new_v = {v for v in bm.verts if kd.find(mw @ v.co)[2] > 1e-4}
    bad = []
    for f in bm.faces:
        if not any(v in new_v for v in f.verts):
            continue
        L = max(((mw @ e.verts[0].co) - (mw @ e.verts[1].co)).length for e in f.edges)
        if L > 0.04 and f.calc_area() / (L * L) < 0.02:
            bad.append(f)
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data); bm.free(); rep[name] = (len(new_v), len(bad))
for o in list(dst.objects):
    if o is not None and o.users == 0:
        bpy.data.objects.remove(o)
print("REPORT", rep)
bpy.ops.wm.save_mainfile()
