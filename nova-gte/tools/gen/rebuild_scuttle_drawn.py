"""Rebuild the scuttle - the panel between the bonnet's rear edge and the bottom of the windscreen - from the
points measured on the car. No Meshy.

The old Scuttle_Panel took its heights off the Meshy shell and sat ~45-58 mm low against the wiper pivot and
washer jets triangulated from c20 + cCF; an over-long bonnet had been hiding it.

body_profile scuttle_curve (both curved in plan, measured from c20 / cCF):
  bonnet rear edge   y = -0.900 + 0.33 x^2
  screen base        y = min(-0.740 + 0.29 x^2, -0.702)
Heights: the front edge is the bonnet's own rear edge less a 6 mm step down into the shut; the rear edge is the
base of the windscreen at z 0.960 - the measured screen corner WS_B, and the silhouette at the centre agrees. The
wiper pivot (0.952) and washer jets (0.947) stand on it, so the surface between runs at ~0.94 there.

blender -b in.blend --python tools/gen/rebuild_scuttle_drawn.py -- out.blend
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None
ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
BA = json.load(open(os.path.join(ROOT, "tools", "photomatch", "ba_result.json")))["points"]
DZ = float(PF["dz"])
SC = PF["scuttle_curve"]
X_SIDE = 0.605
Z_BASE = BA["WS_B"][2] + DZ
NX, NY = 30, 10


def y_rear(x):
    return SC["yr0"] + SC["kr"] * x * x


def y_base(x):
    return min(SC["yb0"] + SC["k"] * x * x, SC["yb_max"])


hood = bpy.data.objects["Hood_Panel"]
dg = bpy.context.evaluated_depsgraph_get()
me = hood.evaluated_get(dg).to_mesh(); m = hood.matrix_world
bvh = BVHTree.FromPolygons([tuple(m @ v.co) for v in me.vertices], [tuple(f.vertices) for f in me.polygons])
hood.evaluated_get(dg).to_mesh_clear()


def z_bonnet_edge(x):
    hit = bvh.ray_cast(Vector((x, y_rear(x) + 0.006, 3.0)), Vector((0, 0, -1)), 5.0)
    return hit[0].z if hit[0] else 0.93


bm = bmesh.new()
G = []
for x in np.linspace(0.0, X_SIDE, NX):
    zf = z_bonnet_edge(x) - SC["step"]
    y0, y1 = y_rear(x) + 0.003, y_base(x)
    col = []
    # a quarter-ellipse: the scuttle rises gently from the bonnet's shut and turns up into the screen base
    for t in np.linspace(0.0, 1.0, NY):
        col.append((float(x), y0 + t * (y1 - y0), zf + (Z_BASE - zf) * (1 - math.cos(t * math.pi / 2))))
    G.append(col)
# the scuttle's side edge carries the bonnet-to-wing shut line on behind the bonnet (see rebuild_bonnet_drawn)
_sj = os.path.join(ROOT, "blender", "data", "shut_bonnet_wing.json")
_shut = json.load(open(_sj)) if os.path.exists(_sj) else {}
_shut["scuttle"] = [[round(float(a), 6) for a in p] for p in G[-1]]
# dz/dx across the car at the side edge, from the last two columns (the wing matches it - see the bonnet script)
_shut["scuttle_slope"] = [round(float((a[2] - b[2]) / (a[0] - b[0])), 5) for a, b in zip(G[-1], G[-2])]
json.dump(_shut, open(_sj, "w"), indent=1)
print("shut line: scuttle side edge written, %d points" % len(G[-1]))
V = [[bm.verts.new(p) for p in col] for col in G]
for i in range(NX - 1):
    for j in range(NY - 1):
        bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
# the front edge drops into the bonnet shut, so the gap reads dark rather than as the background
res = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary
                                             and all(abs(v.co.y - y_rear(v.co.x) - 0.003) < 1e-4 for v in e.verts)])
for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
    v.co.z -= 0.030
bm.normal_update()
if sum(f.normal.z for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

for stale in ("Scuttle_Panel", "Scuttle_Vent"):
    o = bpy.data.objects.get(stale)
    if o:
        old = bpy.data.collections.get("NOVA_OLD")
        if stale == "Scuttle_Panel":
            bpy.data.objects.remove(o, do_unlink=True)
        elif old:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            old.objects.link(o)
            print("moved Scuttle_Vent to NOVA_OLD - its louvres sat on the old, low scuttle; to be redone")
mesh = bpy.data.meshes.new("Scuttle_Panel")
bm.to_mesh(mesh); bm.free()
if hasattr(mesh, "shade_smooth"):
    mesh.shade_smooth()
paint = bpy.data.materials.get("paint_gunmetal")
if paint:
    mesh.materials.append(paint)
ob = bpy.data.objects.new("Scuttle_Panel", mesh)
(bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection).objects.link(ob)
mir = ob.modifiers.new("Mirror", "MIRROR"); mir.use_axis[0] = True; mir.use_clip = True
print("Scuttle_Panel: y %.3f..%.3f at the centre, %.3f..%.3f at the side; z %.3f (bonnet shut) -> %.3f (screen base)"
      % (y_rear(0), y_base(0), y_rear(X_SIDE), y_base(X_SIDE), z_bonnet_edge(0) - SC["step"], Z_BASE))
for lab, x, y, z in (("wiper pivot", 0.0, -0.800, 0.933 + DZ), ("washer jet", 0.175, -0.811, 0.928 + DZ)):
    t = (y - y_rear(x)) / (y_base(x) - y_rear(x))
    zf = z_bonnet_edge(x) - SC["step"]
    zs = zf + (Z_BASE - zf) * (1 - math.cos(t * math.pi / 2))
    print("   %-11s stands %.0f mm proud of the new scuttle (it was ~58 mm on the old one)" % (lab, (z - zs) * 1000))
if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
