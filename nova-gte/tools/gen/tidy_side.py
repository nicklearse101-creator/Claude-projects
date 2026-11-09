"""Tidy the side: close the gap the wing leaves at the door, and clear the torn blocky leftovers.

Two jobs.

**The wing stops short of the door.** The wings were built to y -0.700, which is where the door was cut
out of the Meshy shell; the door is built to the photo-measured shut line at -0.670, and the line
blueprint reads -0.648. So -0.700 is the outlier, and it leaves a 30 mm gap between the two panels. The
wing's rear boundary ring is extruded back onto the door's shut line rather than the wing being rebuilt,
which keeps every measured thing about it.

**The blocky slab is torn.** Each panel rebuilt so far cut its own opening in the old one-piece sides,
and what is left between the openings is ragged and in places no longer covers anything. Faces that now
sit behind a finished panel, and faces left floating with no neighbours, are removed. What still carries
geometry nothing has replaced - the belt, the window frame, the sill, the rear quarter - is left alone.

blender -b blender/nova_proc.blend --python tools/gen/tidy_side.py -- out.blend [--dry]
"""
import sys

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
DRY = "--dry" in args

SHUT_F = -0.670                 # the door's front shut line (body_profile zones.shut_y)
GAP = 0.0025
WINGS = ("Wing_Front_Left", "Wing_Front_Right")
PANELS = ("Hood_Panel", "Scuttle_Panel", "Wing_Front_Left", "Wing_Front_Right", "Door_Left",
          "Rocker_Left", "Skirt_Left", "Roof_Panel", "Greenhouse_Left")
SLABS = ("Fender_Front_Left", "Hood", "Side_Profile_Door_Left")
NEAR = 0.045                    # a slab face this close to a finished panel is behind it


def report(ob):
    return "%s (%d faces)" % (ob.name, len(ob.data.polygons))


# ---- 1. extend each wing's rear edge onto the door's shut line ---------------------------------
for name in WINGS:
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    bm = bmesh.new(); bm.from_mesh(ob.data)
    ymax = max(v.co.y for v in bm.verts)
    want = SHUT_F - GAP
    if ymax >= want - 0.0005:
        print("%s already reaches y %.4f" % (name, ymax))
        bm.free()
        continue
    ring = [e for e in bm.edges if e.is_boundary and all(v.co.y > ymax - 0.004 for v in e.verts)]
    if not ring:
        print("%s: no rear boundary ring found at y %.4f" % (name, ymax))
        bm.free()
        continue
    res = bmesh.ops.extrude_edge_only(bm, edges=ring)
    moved = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in moved:
        v.co.y = want
    bm.normal_update()
    print("%s: rear edge %.4f -> %.4f, %d edges extruded (%d verts)"
          % (name, ymax, want, len(ring), len(moved)))
    if not DRY:
        bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()

# ---- 1b. drop each wing's lower rear corner onto the sill line ----------------------------------
# The wings were cut out of the Meshy shell and stop at z 0.343, where the shell's own sill ended; the
# rocker is built to the blueprint's sill line at 0.246, so behind the front arch there was a 25 mm slit
# between the wing and the top of the skirt. Same treatment as the shut line above: the wing's own lower
# boundary, over the stretch behind the arch, is extruded down rather than the wing being rebuilt.
Z_SILL = 0.252                  # blueprint `sill` at the front of the rocker, less a couple of mm
Y_ARCH = -0.845                 # the front arch's rear edge (body_profile arch_shapes)
for name in WINGS:
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    bm = bmesh.new(); bm.from_mesh(ob.data)
    ring = [e for e in bm.edges if e.is_boundary and all(v.co.z < 0.36 and v.co.y > Y_ARCH for v in e.verts)]
    zmin = min((v.co.z for e in ring for v in e.verts), default=None)
    if not ring or zmin is None or zmin <= Z_SILL + 0.002:
        print("%s: lower rear corner already at z %s" % (name, "%.4f" % zmin if zmin else "-"))
        bm.free()
        continue
    res = bmesh.ops.extrude_edge_only(bm, edges=ring)
    moved = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in moved:
        v.co.z = Z_SILL
    bm.normal_update()
    print("%s: lower rear corner %.4f -> %.4f, %d edges extruded" % (name, zmin, Z_SILL, len(ring)))
    if not DRY:
        bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()

# ---- 2. clear the slab faces the finished panels now carry -------------------------------------
tris, verts = [], []
for name in PANELS:
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    mir = any(m.type == "MIRROR" for m in ob.modifiers)
    for sx in ((1, -1) if mir else (1,)):
        n0 = len(verts)
        verts += [(sx * (ob.matrix_world @ v.co).x,
                   (ob.matrix_world @ v.co).y,
                   (ob.matrix_world @ v.co).z) for v in ob.data.vertices]
        for f in ob.data.polygons:
            vs = list(f.vertices)
            for k in range(1, len(vs) - 1):
                tris.append((n0 + vs[0], n0 + vs[k], n0 + vs[k + 1]))
bvh = BVHTree.FromPolygons(verts, tris)
print("coverage from %d finished panels: %d triangles" % (len(PANELS), len(tris)))

from mathutils import Vector

for name in SLABS:
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    before = len(ob.data.polygons)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.normal_update()
    bm.faces.ensure_lookup_table()

    covered = []
    for f in bm.faces:
        c = ob.matrix_world @ f.calc_center_median()
        if abs(c.x) < 0.25:                     # keep anything near the centreline (roof, screen)
            continue
        if bvh.find_nearest(c, NEAR)[0] is not None:
            covered.append(f)
    if covered and not DRY:
        bmesh.ops.delete(bm, geom=covered, context="FACES")
        bm.faces.ensure_lookup_table()

    # anything left with no neighbour at all is a torn scrap, not a panel
    loose = [f for f in bm.faces if not any(len(e.link_faces) > 1 for e in f.edges)]
    tiny = [f for f in bm.faces if f.calc_area() < 1e-6 and f not in loose]
    if (loose or tiny) and not DRY:
        bmesh.ops.delete(bm, geom=loose + tiny, context="FACES")

    print("%-26s %4d faces: %3d behind a finished panel, %3d floating, %3d degenerate -> %d"
          % (name, before, len(covered), len(loose), len(tiny), len(bm.faces)))
    if not DRY:
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
        bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()

for name in SLABS:
    ob = bpy.data.objects.get(name)
    if ob is not None and len(ob.data.polygons) == 0:
        print("removed %s, nothing left of it" % name)
        if not DRY:
            bpy.data.objects.remove(ob, do_unlink=True)

if OUT and not DRY:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
