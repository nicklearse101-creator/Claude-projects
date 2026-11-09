"""Build the whole body as one closed shell, instead of eight panels that do not meet.

Panel by panel was not converging: each piece took a long session, they met badly, and the greenhouse
could not be expressed as a swept grid at all. A car body is one surface with shut lines scribed into
it, and that is how this builds it - the measurements already in hand define it completely.

Three rulers, all traced, all cross-checked already:

  **top(y) and floor(y)** - body_profile's own longitudinal silhouette, nose to tail: the bonnet, the
  screen, the roof and the tailgate on top, the valance, sill and bumpers underneath. In the photo
  frame, so + DZ.
  **halfw(y)** - the plan taper from the factory sheet, anchored on the FIA widths.
  **section(z)** - the front elevation's silhouette, which is the body's cross-section shape.

At each station the section's shape is mapped onto that station's own height range. Where the body is
widest the result is exactly the traced section; towards the nose and the tail it compresses with the
silhouette, which is what the body does. The side view and the plan are therefore right by construction
at every station, and only the cross-section's shape is interpolated between them.

The ends close by themselves: at the nose top and floor meet, and at the tail they nearly do.

This replaces the blocky slab and the greenhouse. The finished panels built from their own measurements
- bonnet, wing, door, rocker, skirt, roof - stay where they are and sit on top of it, so nothing
measured is lost; the shell fills everything between them.

blender -b blender/nova_proc.blend --python tools/gen/build_shell.py -- out.blend [--stations N]
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
NY = int(args[args.index("--stations") + 1]) if "--stations" in args else 260
NU = 44

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
PLAN = np.array(json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(D, "section_profile.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))

DZ = 0.0193
TOP = np.array(PF["top"], float); TOP[:, 1] += DZ
FLOOR = np.array(PF["floor"], float); FLOOR[:, 1] += DZ
Y0, Y1 = float(PF["y_front"]), float(PF["y_rear"])
Z_SILL_M, Z_CROWN_M = 0.22, float(SECT[-1, 0])      # the master section's own range


def smooth(a, n):
    return np.convolve(np.r_[np.repeat(a[0], n // 2), a, np.repeat(a[-1], n // 2)], np.ones(n) / n, "valid")


def half(y):
    return float(np.interp(y, PLAN[:, 0], PLAN[:, 1]))


def sect(z):
    return float(np.interp(z, SECT[:, 0], SECT[:, 1]))


ys = np.linspace(Y0, Y1, NY)
z_top = smooth(np.interp(ys, TOP[:, 0], TOP[:, 1]), 5)
z_bot = smooth(np.interp(ys, FLOOR[:, 0], FLOOR[:, 1]), 5)
print("shell y %+.3f .. %+.3f over %d stations" % (Y0, Y1, NY))
print("top    %.3f at the nose, %.3f at the screen header, %.3f at the roof, %.3f at the tail"
      % (np.interp(-1.70, ys, z_top), np.interp(-0.20, ys, z_top),
         np.interp(0.60, ys, z_top), np.interp(1.70, ys, z_top)))
print("floor  %.3f / %.3f / %.3f ; half-width %.3f at the arches, %.3f at the nose"
      % (np.interp(-1.70, ys, z_bot), np.interp(0.0, ys, z_bot), np.interp(1.70, ys, z_bot),
         half(0.0), half(-1.70)))

# master section, sampled evenly from the sill to the crown
ts = np.linspace(0.0, 1.0, NU)
zm = Z_SILL_M + ts * (Z_CROWN_M - Z_SILL_M)
sm = np.array([sect(z) for z in zm])
sm[-1] = 0.0                                        # close on the centreline
print("master section: %.3f wide at the sill, %.3f at the belt, %.3f at the shoulder, 0 at the crown"
      % (sm[0], sect(0.85), sect(1.26)))

bm = bmesh.new()
V = []
for i, y in enumerate(ys):
    hw, zb, zt = half(float(y)), float(z_bot[i]), float(z_top[i])
    col = []
    for j, t in enumerate(ts):
        col.append(bm.verts.new((hw * sm[j], float(y), zb + t * (zt - zb))))
    V.append(col)
for i in range(NY - 1):
    for j in range(NU - 1):
        a, b, c, d = V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]
        if (a.co - b.co).length < 1e-7 and (d.co - c.co).length < 1e-7:
            continue
        bm.faces.new((a, b, c, d))
bm.faces.ensure_lookup_table(); bm.normal_update()
if sum(f.normal.x for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
bm.normal_update()

name = "Body_Shell"
old = bpy.data.objects.get(name)
coll = old.users_collection[0] if old else bpy.data.objects["Door_Left"].users_collection[0]
if old:
    bpy.data.objects.remove(old, do_unlink=True)
mesh = bpy.data.meshes.new(name)
bm.to_mesh(mesh); bm.free()
if hasattr(mesh, "shade_smooth"):
    mesh.shade_smooth()
for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):
    _f = getattr(mesh, _n, None)
    if _f:
        _f(angle=math.radians(40))
        break
paint = bpy.data.materials.get("paint_gunmetal")
if paint:
    mesh.materials.append(paint)
ob = bpy.data.objects.new(name, mesh)
coll.objects.link(ob)
mir = ob.modifiers.new("Mirror", "MIRROR")
mir.use_axis[0] = True
mir.use_clip = True
mir.merge_threshold = 0.001
vs = [v.co for v in mesh.vertices]
print("%s: %d verts, %d faces, mirrored on the centreline" % (name, len(vs), len(mesh.polygons)))
print("   x 0..%.3f, y %+.3f..%+.3f, z %.3f..%.3f"
      % (max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs),
         min(v.z for v in vs), max(v.z for v in vs)))

# the slab and the failed greenhouse are what this replaces
for stale in ("Side_Profile_Door_Left", "Side_Profile_Door_Right", "Greenhouse_Left", "Greenhouse_Right"):
    o = bpy.data.objects.get(stale)
    if o:
        print("removed %s (%d faces)" % (stale, len(o.data.polygons)))
        bpy.data.objects.remove(o, do_unlink=True)

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
