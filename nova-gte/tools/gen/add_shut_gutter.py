"""The gutter under the bonnet-to-wing shut: the wing's inner flange, which on the car sits under the gap.

With the shut built from one shared line (2026-10-27 (12)) the gap was open straight through to the ground in
places (0.6-1.3 mm slits at y -1.58..-1.40 and -0.80..-0.72), and where it was not, what showed through it was
whatever happened to be below. On the car the wing's top is turned down into a flange under the bonnet's edge,
so the shut reads as a dark channel. This lays that channel along the shared shut line
(blender/data/shut_bonnet_wing.json): at each station a U section in the plane across the car, set in the
surface's own frame - u along the bonnet's cross-slope, n out of the surface - so it follows the shut down the
nose roll and round the bonnet corner.

It sits below roll_edges' shut returns, which end 4 mm under the surface and 8.7 mm either side of the line
(2.2 mm gap pull + 6.5 mm return): lips 7 mm deep at +-12 mm, floor 16 mm deep over +-4 mm.

Runs after roll_edges (so its own edges are not rolled), left side only with a Mirror modifier, dark trim.

blender -b in.blend --python tools/gen/add_shut_gutter.py -- out.blend
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = json.load(open(os.path.join(ROOT, "blender", "data", "shut_bonnet_wing.json")))

pts = [tuple(p) + (s,) for p, s in zip(S["bonnet"], S["bonnet_slope"])]
yb = max(p[1] for p in pts)
pts += [tuple(p) + (s,) for p, s in zip(S["scuttle"], S["scuttle_slope"]) if p[1] > yb + 1e-4]
pts.sort(key=lambda p: p[1])
P = np.array(pts, float)                           # x, y, z, dz/dx

# (u, n) of the section, inboard to outboard: lip, wall, floor, floor, wall, lip
SECTION = [(-0.012, -0.007), (-0.004, -0.016), (0.004, -0.016), (0.012, -0.007)]
STEP = 0.005

# Run on 20 mm past the shut line's rear end, holding its last section, so the channel ends under the A-pillar's
# side wall rather than 2 mm short of it (a pinhole at y -0.71, z 0.928, 2026-10-27 (14)).
END_RUN = 0.020
ys = np.arange(P[0, 1], P[-1, 1] + END_RUN, STEP).tolist() + [float(P[-1, 1]) + END_RUN]
bm = bmesh.new()
rows = []
for y in ys:
    x = float(np.interp(y, P[:, 1], P[:, 0])); z = float(np.interp(y, P[:, 1], P[:, 2]))
    s = float(np.interp(y, P[:, 1], P[:, 3]))
    u = np.array([1.0, s]) / math.hypot(1.0, s)          # outboard, along the surface across the car
    n = np.array([-s, 1.0]) / math.hypot(1.0, s)         # out of the surface
    row = []
    for a, b in SECTION:
        q = np.array([x, z]) + a * u + b * n
        row.append(bm.verts.new((float(q[0]), y, float(q[1]))))
    rows.append(row)
for r0, r1 in zip(rows[:-1], rows[1:]):
    for j in range(len(SECTION) - 1):
        bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
bm.normal_update()
if sum(f.normal.z for f in bm.faces) < 0:             # the channel's inside faces up, into the gap
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

name = "SHUT_GUTTER_BONNET"
old = bpy.data.objects.get(name)
if old:
    bpy.data.objects.remove(old, do_unlink=True)
mesh = bpy.data.meshes.new(name)
bm.to_mesh(mesh); bm.free()
mat = bpy.data.materials.get("trim_black")
if mat is None:
    mat = bpy.data.materials.new("trim_black")
    mat.diffuse_color = (0.02, 0.02, 0.02, 1.0)
mesh.materials.append(mat)
if hasattr(mesh, "shade_smooth"):
    mesh.shade_smooth()
ob = bpy.data.objects.new(name, mesh)
(bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection).objects.link(ob)
mir = ob.modifiers.new("Mirror", "MIRROR"); mir.use_axis[0] = True
print("%s: %d faces along y %+.3f .. %+.3f, lips +-%.0f mm at %.0f mm deep, floor %.0f mm deep"
      % (name, len(mesh.polygons), ys[0], ys[-1], 1000 * SECTION[-1][0], -1000 * SECTION[-1][1],
         -1000 * SECTION[1][1]))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
