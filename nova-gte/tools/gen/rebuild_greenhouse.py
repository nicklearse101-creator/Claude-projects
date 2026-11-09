"""Build the greenhouse side: the A, B and C pillars and the window frames, with the apertures cut.

This is the hole in the car. Everything above the belt was still the old blocky slab, which is why the
model does not read as a car from any angle.

The surface is the flank's own, x(y, z) = halfw(y) * section(z) - above the belt the section leans the
body in, which is the tumblehome, so the pillars come out leaning the right way without anything extra.

The outline comes from the traced lines and the photogrammetry:
  belt        - `belt` / `belt_b` on the line blueprint (the panel's lower edge)
  cant        - `cant` + `glass_top_x` in body_profile: the top of the side glass, where the roof panel
                already finishes, so the two meet without a step
  A-pillar    - `zones.a_pillar_outer`: its outer edge from the belt at y -0.699 up to the roof at -0.192
  B-pillar    - `zones.b_pillar`: y 0.425 to 0.570
  C-pillar    - `zones.quarter_rear_edge`: from y 1.458 at the belt up to 1.096 at the roof
  apertures   - `dlo_top` / `glass_base` on the blueprint: the top and bottom of the side glass

Each station is built with the same number of rows whether or not it has an aperture there: where there
is none, the aperture's two edges are collapsed onto each other. That keeps one clean quad grid and
gives the window openings a crisp edge instead of a staircase - the same trick the sill skirt uses for
its kick-up.

blender -b blender/nova_proc.blend --python tools/gen/rebuild_greenhouse.py -- out.blend
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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PLAN = np.array(json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(D, "section_profile.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))

DZ = 0.0193
FLANGE = 0.020                  # how far the aperture's edge returns inboard
NZ_LO, NZ_HI = 6, 10


def skin_x(y, z):
    return float(np.interp(y, PLAN[:, 0], PLAN[:, 1])) * float(np.interp(z, SECT[:, 0], SECT[:, 1]))


def curve(*names):
    return np.array(sorted({(round(a, 5), round(b, 5)) for n in names for a, b in SP[n]}), float)


def smooth(p, n=9):
    q = p.copy()
    pad = np.r_[np.repeat(p[:1, 1], n // 2), p[:, 1], np.repeat(p[-1:, 1], n // 2)]
    q[:, 1] = np.convolve(pad, np.ones(n) / n, "valid")
    return q


belt = smooth(curve("belt", "belt_b"))
dlo = smooth(curve("dlo_top", "dlo_top_b"))
gbase = smooth(curve("glass_base", "glass_base_b"))
cant = np.array(PF["cant"], float); cant[:, 1] += DZ
gtx = np.array(PF["glass_top_x"], float)

AP = np.array(PF["zones"]["a_pillar_outer"], float); AP[:, 1] += DZ      # (y, z) bottom then top
QR = np.array(PF["zones"]["quarter_rear_edge"], float); QR[:, 1] += DZ   # (y, z) bottom then top
B0, B1 = PF["zones"]["b_pillar"]                                          # the B-pillar's two edges
A_W = 0.070                     # the A-pillar's width, back from its outer edge
C_W = 0.090                     # the C-pillar's width, forward from its rear edge


def z_belt(y):
    return float(np.interp(y, belt[:, 0], belt[:, 1]))


def z_cant(y):
    return float(np.interp(y, cant[:, 0], cant[:, 1]))


def x_cant(y):
    return float(np.interp(y, gtx[:, 0], gtx[:, 1]))


def z_dlo(y):
    return float(np.interp(y, dlo[:, 0], dlo[:, 1]))


def z_gbase(y):
    return float(np.interp(y, gbase[:, 0], gbase[:, 1]))


def line_y(pts, z):
    """y of a pillar edge at this height (its two measured ends, extended)."""
    (y0, z0), (y1, z1) = pts
    return float(y0 + (y1 - y0) * (z - z0) / (z1 - z0))


Y_F = float(AP[0, 0])                   # the A-pillar's foot, at the belt
Y_R = float(QR[0, 0])                   # the C-pillar's foot
print("greenhouse y %+.3f .. %+.3f; A-pillar outer %+.3f at the belt to %+.3f at the roof"
      % (Y_F, Y_R, AP[0, 0], AP[1, 0]))
print("B-pillar y %+.3f .. %+.3f; C-pillar rear %+.3f at the belt to %+.3f at the roof"
      % (B0, B1, QR[0, 0], QR[1, 0]))
print("belt z %.3f at y 0, cant z %.3f at x %.3f; glass %.3f .. %.3f"
      % (z_belt(0.0), z_cant(0.0), x_cant(0.0), z_gbase(0.0), z_dlo(0.0)))


def aperture(y, z_mid):
    """(bottom, top) of the window opening at this station, collapsed where there is a pillar."""
    for lo, hi in APERTURES:
        if lo(z_mid) + 1e-6 < y < hi(z_mid) - 1e-6:
            return max(z_gbase(y), z_belt(y) + 0.006), min(z_dlo(y), z_cant(y) - 0.006)
    return z_mid, z_mid


APERTURES = [
    (lambda z: line_y(AP, z) + A_W, lambda z: B0),          # the door's window
    (lambda z: B1, lambda z: line_y(QR, z) - C_W),          # the quarter window
]

# Stations: every pillar edge gets one exactly on it, so those edges come out straight.
keys = {Y_F, Y_R, B0, B1}
for z in np.linspace(0.95, 1.26, 24):
    keys.add(line_y(AP, z) + A_W)
    keys.add(line_y(QR, z) - C_W)
ys = sorted(y for y in keys if Y_F - 1e-9 <= y <= Y_R + 1e-9)
dense = []
for a, b in zip(ys[:-1], ys[1:]):
    n = max(1, int(round((b - a) / 0.012)))
    dense += list(np.linspace(a, b, n, endpoint=False))
dense.append(ys[-1])
ys = np.array(dense)


def rows(y):
    zb, zt = z_belt(y), z_cant(y)
    zm = 0.5 * (zb + zt)
    a0, a1 = aperture(y, zm)
    out = [(skin_x(y, zb) - 0.018, zb - 0.010), (skin_x(y, zb) - 0.002, zb)]
    for t in np.linspace(0.0, 1.0, NZ_LO)[1:]:
        z = zb + t * (a0 - zb)
        out.append((skin_x(y, z), z))
    out.append((skin_x(y, a0) - FLANGE, a0))          # into the aperture
    out.append((skin_x(y, a1) - FLANGE, a1))          # and back out at its top
    for t in np.linspace(0.0, 1.0, NZ_HI)[1:]:
        z = a1 + t * (zt - a1)
        out.append((skin_x(y, z), z))
    out.append((x_cant(y), zt))                       # meet the roof panel's own lower edge
    out.append((x_cant(y) - 0.012, zt - 0.004))
    return out


NR = len(rows(float(ys[len(ys) // 2])))
bm = bmesh.new()
V = [[bm.verts.new((r[0], float(y), r[1])) for r in rows(float(y))] for y in ys]
for i in range(len(ys) - 1):
    for j in range(NR - 1):
        a, b, c, d = V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]
        if (a.co - b.co).length < 1e-7 and (d.co - c.co).length < 1e-7:
            continue
        bm.faces.new((a, b, c, d))
bm.faces.ensure_lookup_table(); bm.normal_update()
if sum(f.normal.x for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
bm.normal_update()

name = "Greenhouse_Left"
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
        _f(angle=math.radians(32))
        break
paint = bpy.data.materials.get("paint_gunmetal")
if paint:
    mesh.materials.append(paint)
ob = bpy.data.objects.new(name, mesh)
coll.objects.link(ob)
mir = ob.modifiers.new("Mirror", "MIRROR")
mir.use_axis[0] = True
mir.use_clip = False
vs = [v.co for v in mesh.vertices]
print("%s: %d verts, %d faces, %d stations x %d rows, mirrored"
      % (name, len(vs), len(mesh.polygons), len(ys), NR))
print("   x %.4f..%.4f, y %+.3f..%+.3f, z %.4f..%.4f"
      % (min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs),
         min(v.z for v in vs), max(v.z for v in vs)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
