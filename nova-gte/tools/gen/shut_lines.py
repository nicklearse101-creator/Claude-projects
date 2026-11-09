"""Cut the panel shut lines into the body as real grooves.

The car's sides read as one blob because the door is not a separate panel here - the shell carries that whole
area - so nothing marks where the door starts and stops. On the real car those lines are the strongest shapes
on the side: three near-vertical shadows, the door's front and rear shuts and the tailgate's.

They are made the way `front_end.py` makes the groove under the grille: a narrow strip of its own geometry
lying in the surface, dark, with walls. For every point of the traced line the body is sampled - nearest point
and normal on a BVH of the painted parts - and a five-row section is laid across it:

    +HW out on the surface -> the wall -> DEPTH behind it -> the wall -> -HW out on the surface

so the groove has sides to catch the light instead of being a painted line.

Lines, all traced on the side elevation of the line blueprint (tools/trace_side.py):

    shut_door_front   the door's leading edge, which curls forward into the sill
    shut_door_rear    its trailing edge, sweeping back over the rear arch
    tailgate_shut     the tailgate's side edge

blender -b in.blend --python tools/gen/shut_lines.py -- out.blend
"""
import json
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
D = os.path.join(ROOT, "blender", "data")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]

HW, DEPTH, WALL = 0.0024, 0.0035, 0.0007      # half width, depth, how far in the wall sits from the lip
STEP = 0.004                                   # sample spacing along the line
BODY = ("Body_Shell", "Wing_Front_Left", "Skirt_Left", "PANEL_R_L", "PANEL_R_R", "Hood_Panel", "Scuttle_Panel")
LINES = ("shut_door_front", "shut_door_rear", "tailgate_shut")


def resample(pts, step):
    a = np.array(sorted(pts, key=lambda p: p[1]), float)       # along z, these lines are near-vertical
    keep = np.r_[True, np.linalg.norm(np.diff(a, axis=0), axis=1) > 1e-6]
    a = a[keep]
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(a, axis=0), axis=1))]
    n = max(3, int(d[-1] / step))
    u = np.linspace(0, d[-1], n)
    return np.c_[np.interp(u, d, a[:, 0]), np.interp(u, d, a[:, 1])]


def smooth(a, n=7):
    if len(a) < n:
        return a
    out = a.copy()
    for k in (0, 1):
        pad = np.r_[np.repeat(a[0, k], n // 2), a[:, k], np.repeat(a[-1, k], n // 2)]
        out[:, k] = np.convolve(pad, np.ones(n) / n, "valid")
    return out


verts, tris = [], []
for n in BODY:
    o = bpy.data.objects.get(n)
    if not o or not len(o.data.polygons):
        continue
    dg = bpy.context.evaluated_depsgraph_get()
    me = o.evaluated_get(dg).to_mesh()
    m = o.matrix_world
    n0 = len(verts)
    verts += [tuple(m @ v.co) for v in me.vertices]
    for f in me.polygons:
        vs = list(f.vertices)
        for k in range(1, len(vs) - 1):
            tris.append((n0 + vs[0], n0 + vs[k], n0 + vs[k + 1]))
    o.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(verts, tris)

mat = bpy.data.materials.get("panel_gap")
if mat is None:
    mat = bpy.data.materials.new("panel_gap")
    mat.use_nodes = True
    b = next(nd for nd in mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1)
    b.inputs["Roughness"].default_value = 0.80
    mat.diffuse_color = (0.01, 0.01, 0.01, 1)

coll = bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection
made = 0
for name in LINES:
    if name not in SP:
        continue
    line = smooth(resample(SP[name], STEP))
    bm = bmesh.new()
    rows = []
    for y, z in line:
        # start from outside the car on the left side and find the skin
        loc, nrm, _, _ = bvh.find_nearest(Vector((0.80, float(y), float(z))), 0.35)
        if loc is None:
            rows.append(None)
            continue
        n = nrm.normalized()
        if n.x < 0:
            n = -n
        rows.append((loc, n))
    ok = [r for r in rows if r is not None]
    if len(ok) < 3:
        print("%-18s no surface found" % name)
        bm.free()
        continue
    cols = []
    for i, r in enumerate(rows):
        if r is None:
            cols.append(None)
            continue
        loc, n = r
        j = i + 1 if i + 1 < len(rows) and rows[i + 1] else i - 1
        other = rows[j][0] if rows[j] else loc + Vector((0, 0, 0.001))
        t = (other - loc)
        if t.length < 1e-9:
            cols.append(None)
            continue
        t.normalize()
        h = n.cross(t).normalized()
        sec = [(HW, 0.0), (HW - WALL, DEPTH), (0.0, DEPTH + 0.0004), (-HW + WALL, DEPTH), (-HW, 0.0)]
        cols.append([bm.verts.new(loc + h * d - n * e) for d, e in sec])
    for a, b2 in zip(cols[:-1], cols[1:]):
        if a is None or b2 is None:
            continue
        for k in range(len(a) - 1):
            try:
                bm.faces.new((a[k], b2[k], b2[k + 1], a[k + 1]))
            except ValueError:
                pass
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obn = "SHUT_" + name.replace("shut_", "").upper()
    old = bpy.data.objects.get(obn)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(obn)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(obn, me)
    coll.objects.link(ob)
    mir = ob.modifiers.new("Mirror", "MIRROR")
    mir.use_axis[0] = True
    zs = [v.co.z for v in me.vertices]
    print("%-18s %4d faces  z %.3f..%.3f  (%d samples)" % (obn, len(me.polygons), min(zs), max(zs), len(ok)))
    made += len(me.polygons)
print("shut lines: %d faces" % made)

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
