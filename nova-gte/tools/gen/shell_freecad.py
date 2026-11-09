"""Loft the body shell as a NURBS surface in FreeCAD, and bring it back as a fine mesh.

The Blender version of this (tools/gen/build_shell.py) interpolates a quad lattice between traced
stations. That is where the ripples, creases and corrugations keep coming from: a lattice is only as
fair as its rows, and every wobble in a traced row shows up in the paint. A lofted B-spline surface is
fair by construction - it is a single surface with continuous curvature, which is what a car body is.

Same rulers as the Blender version, nothing new measured:
  top(y) / floor(y)  body_profile's longitudinal silhouette, nose to tail, + DZ into the model frame
  halfw(y)           the plan taper from the factory sheet, anchored on the FIA widths
  section(z)         the front elevation's silhouette - the body's cross-section shape

Each station becomes one B-spline through its section's points; FreeCAD lofts them into a surface and
writes a STEP (for anything else that wants real surfaces) and a fine mesh for Blender.

    D:\\FreeCAD\\bin\\freecadcmd.exe tools/gen/shell_freecad.py
"""
import json
import os
import sys

import FreeCAD as App
import Part
import Mesh
import MeshPart

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
D = os.path.join(ROOT, "blender", "data")
OUT_STEP = os.path.join(ROOT, "export", "shell.step")
OUT_MESH = os.path.join(ROOT, "export", "shell.obj")

NY, NU = 22, 26                 # loft sections along the car / points per section
# 56 x 34 made the surface approximation run for ten minutes at 2 GB and still not finish.
# A body loft wants a handful of well-placed sections, not a dense sampling: the whole point
# of a B-spline surface is that it fairs between them.
DZ = 0.0193
Z_SILL_M = 0.22
Z_BELT_M = 0.85                 # the master section's belt, where the flank stops being parallel

PLAN = json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"]
SECT = sorted(json.load(open(os.path.join(D, "section_profile.json")))["profile"])
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
TOP = [[y, z + DZ] for y, z in PF["top"]]
FLOOR = [[y, z + DZ] for y, z in PF["floor"]]
Y0, Y1 = float(PF["y_front"]), float(PF["y_rear"])
Z_CROWN_M = SECT[-1][0]

SIDE = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
_b = sorted(set((round(a, 5), round(b, 5)) for n in ("belt", "belt_b") for a, b in SIDE[n]))
BELT = [[y, z] for y, z in _b]


def interp(table, x):
    xs = [r[0] for r in table]
    ys = [r[1] for r in table]
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]


# The master section is sampled in two stretches, below and above the belt, and each station maps
# them onto its own floor-to-belt and belt-to-top. Mapping the whole section onto one height range
# was the fault the front and rear views showed: at the greenhouse the glass taper got applied from
# the sill upwards, so the body came out barrel-sided and the roof far too narrow, where the real car
# has a near-vertical flank to the belt and only then leans in.
NLO = NU // 3
ts, zs_m = [], []
for i in range(NLO):
    f = i / float(NLO)
    ts.append(("lo", f)); zs_m.append(Z_SILL_M + f * (Z_BELT_M - Z_SILL_M))
for i in range(NU - NLO):
    f = i / float(NU - NLO - 1)
    ts.append(("hi", f)); zs_m.append(Z_BELT_M + f * (Z_CROWN_M - Z_BELT_M))
sm = [interp(SECT, z) for z in zs_m]
sm[-1] = 0.0
print("master section: %.3f at the sill, %.3f at the belt, %.3f above it, 0.000 at the crown"
      % (sm[0], sm[NLO], sm[(NLO + NU) // 2]))

# Stations are closer together where the silhouette turns - the nose, the screen header, the tail -
# so the loft follows those without needing them everywhere.
raw = []
for i in range(NY):
    u = i / float(NY - 1)
    raw.append(Y0 + (Y1 - Y0) * u)
ys = raw

sections = []
for y in ys:
    hw = interp(PLAN, y)
    zb, zt = interp(FLOOR, y), interp(TOP, y)
    zbelt = interp(BELT, y)
    if not (zb + 0.02 < zbelt < zt - 0.02):          # the nose and tail, where there is no flank
        zbelt = zb + 0.45 * (zt - zb)
    pts = []
    for j, (zone, f) in enumerate(ts):
        z = (zb + f * (zbelt - zb)) if zone == "lo" else (zbelt + f * (zt - zbelt))
        pts.append(App.Vector(hw * sm[j], y, z))
    # Every section must have the SAME number of points, in the same order. Dropping repeats
    # per-station gave the splines different knot structures and the lofted surface then swung out to
    # x 1.58 and z 1.60 - more than twice the car. Instead, stations too shallow to carry a real
    # section are left out altogether, and within a station coincident samples are nudged apart.
    if (zt - zb) < 0.05 or hw < 0.05:
        continue
    for k in range(1, len(pts)):
        if (pts[k] - pts[k - 1]).Length < 1e-5:
            pts[k] = pts[k] + App.Vector(0, 0, 1e-4)
    bs = Part.BSplineCurve()
    bs.interpolate(pts)
    sections.append(bs.toShape())

print("built %d loft sections over y %+.3f .. %+.3f" % (len(sections), ys[0], ys[-1]))

loft = Part.makeLoft(sections, False, False, False)   # not solid, not ruled, not closed
print("loft: %d faces, area %.4f m2, bound %s"
      % (len(loft.Faces), loft.Area, [round(v, 3) for v in loft.BoundBox.__repr__().split()[1:7]]
         if False else [round(loft.BoundBox.XMin, 3), round(loft.BoundBox.XMax, 3),
                        round(loft.BoundBox.YMin, 3), round(loft.BoundBox.YMax, 3),
                        round(loft.BoundBox.ZMin, 3), round(loft.BoundBox.ZMax, 3)]))

mirrored = loft.mirror(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
both = Part.makeCompound([loft, mirrored])

os.makedirs(os.path.join(ROOT, "export"), exist_ok=True)
both.exportStep(OUT_STEP)
print("wrote", OUT_STEP)

doc = App.newDocument("shell")
o = doc.addObject("Part::Feature", "Shell")
o.Shape = both
doc.recompute()
m = doc.addObject("Mesh::Feature", "ShellMesh")
m.Mesh = MeshPart.meshFromShape(Shape=both, LinearDeflection=0.0025, AngularDeflection=0.12,
                                Relative=False)
doc.recompute()
Mesh.export([m], OUT_MESH)
print("wrote %s  (%d facets, deflection 2.5 mm)" % (OUT_MESH, m.Mesh.CountFacets))
