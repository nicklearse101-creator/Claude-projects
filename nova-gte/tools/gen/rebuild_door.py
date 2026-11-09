"""Rebuild the door skin as a clean quad panel, the first piece of the side profile.

Nothing here is sampled off the Meshy shell any more (Nik, 2026-10-26: the shell is only for reference
now we have the drawings). The surface is x(y, z), and it comes from two traced curves:

    x(y, z) = halfw(y) * section(z)

`halfw` is the plan view's taper from tools/trace_plan.py, anchored on the FIA widths; `section` is the
front elevation's silhouette from tools/trace_section.py, normalised, which is the flank's tumblehome -
parallel from the sill to z 0.65, then leaning in by 17 mm at z 0.75 and 52 mm at the belt. That product
is exactly what an orthographic plan and an orthographic end elevation say the body is, and it comes out
smooth, so there is nothing left for the Laplacian fit the shell-sampled panels needed.

Its four edges are traced, not guessed. Three come from the line blueprint via tools/trace_side.py -
the two shut lines, which are not plain verticals (the front one curls forward into the sill, the rear
one sweeps back over the arch), and the door's own lower edge, which on the drawing is the upper of the
two lines above the sill. The top edge is the belt line from tools/photomatch/body_profile.json, which
the blueprint agrees with to about 5 mm.

Longitudinally the shut lines are placed on the photo-measured body_profile zones.shut_y (-0.670 and
+0.465) and the blueprint's traced shape is shifted onto them; the blueprint's own straight sections sit
at -0.650 and +0.500, so this is a 20 / 35 mm correction and the two sources agree on the door's length
to within 15 mm.

The interior is a Coons patch over those four curves, the heights come off the Meshy ruler, and the
surface is fitted with a Laplacian term exactly as the bonnet and the wings were. As with the wing, the
shell is narrow here, so each station is widened onto the measured half-width.

blender -b blender/nova_proc.blend --python tools/gen/rebuild_door.py -- out.blend \
    [--panel Door] [--cut Side_Profile_Door_Left] [--diag]
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


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


PANEL = opt("--panel", "Door")
CUT = opt("--cut", "Side_Profile_Door_Left")
DIAG = "--diag" in args

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SP = json.load(open(os.path.join(ROOT, "blender", "data", "side_profile.json")))["lines"]
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))

DZ = 0.0193                     # photo frame -> model frame
SHUT_F, SHUT_R = -0.670, 0.465  # body_profile zones.shut_y, the project's measured shut lines
GAP = 0.0025                    # half the shut-line gap, taken off each end
NU, NV = 61, 29                 # grid: along the door / up it
LIP = 0.016                     # the door's edge returns inward behind the shut line


def curve(*names):
    """Traced polyline, concatenated and sorted along y."""
    pts = sorted({(round(a, 5), round(b, 5)) for n in names for a, b in SP[n]})
    return np.array(pts, float)


def mono(p, lo, hi):
    """Clip to a y range and make y strictly increasing so np.interp can use it."""
    p = p[(p[:, 0] >= lo) & (p[:, 0] <= hi)]
    keep = np.r_[True, np.diff(p[:, 0]) > 1e-6]
    return p[keep]


def smooth(p, n=9):
    """Running mean over the traced polyline: a pixel trace is a pixel wide, and the panel's edges are
    not. Without this the door's lower edge ripples by a few mm per station."""
    if len(p) < n:
        return p
    k = np.ones(n) / n
    q = p.copy()
    pad = np.r_[np.repeat(p[:1, 1], n // 2), p[:, 1], np.repeat(p[-1:, 1], n // 2)]
    q[:, 1] = np.convolve(pad, k, mode="valid")
    return q


# ---- the four edges ---------------------------------------------------------------------------
shut_f = np.array(SP["shut_door_front"], float)
shut_r = np.array(SP["shut_door_rear"], float)
shut_f = shut_f[shut_f[:, 1] >= 0.30]          # below the door's lower edge the trace follows the sill
shut_r = shut_r[shut_r[:, 1] >= 0.30]
# put each traced shape onto the measured shut line: the offset is read off the straight middle section
off_f = SHUT_F - float(np.median(shut_f[(shut_f[:, 1] > 0.45) & (shut_f[:, 1] < 0.80), 0]))
off_r = SHUT_R - float(np.median(shut_r[(shut_r[:, 1] > 0.45) & (shut_r[:, 1] < 0.80), 0]))
shut_f[:, 0] += off_f
shut_r[:, 0] += off_r
for c in (shut_f, shut_r):                     # same running mean, along z this time
    c[:, 0] = np.convolve(np.r_[np.repeat(c[0, 0], 3), c[:, 0], np.repeat(c[-1, 0], 3)],
                          np.ones(7) / 7.0, mode="valid")
print("shut lines moved onto the measured values: front %+.0f mm, rear %+.0f mm"
      % (off_f * 1000, off_r * 1000))

bottom = mono(curve("door_bottom", "door_bottom_b"), SHUT_F - 0.05, SHUT_R + 0.05)
bottom = smooth(bottom[bottom[:, 1] < 0.36])   # drop the ends where the trace climbs the arches
belt = np.array(PF["belt"], float)
belt[:, 1] += DZ


def z_bottom(y):
    return float(np.interp(y, bottom[:, 0], bottom[:, 1]))


def z_top(y):
    return float(np.interp(y, belt[:, 0], belt[:, 1]))


def y_shut(c, z):
    """Shut line y at this height; the curve is traced top-down so interp wants it z-ascending."""
    c = c[np.argsort(c[:, 1])]
    return float(np.interp(z, c[:, 1], c[:, 0]))


print("door: y %.3f .. %.3f (%.0f mm long), z %.3f .. %.3f at mid"
      % (SHUT_F, SHUT_R, (SHUT_R - SHUT_F) * 1000, z_bottom(0.0), z_top(0.0)))

# ---- Coons patch over the four edges ----------------------------------------------------------
U = np.linspace(0.0, 1.0, NU)
V = np.linspace(0.0, 1.0, NV)
YZ = np.zeros((NV, NU, 2))
for i, v in enumerate(V):
    for j, u in enumerate(U):
        # corner-consistent blend of the two shut lines (y given z) and the two rails (z given y)
        y_lin = (SHUT_F + GAP) + u * ((SHUT_R - GAP) - (SHUT_F + GAP))
        z = z_bottom(y_lin) + v * (z_top(y_lin) - z_bottom(y_lin))
        yf, yr = y_shut(shut_f, z) + GAP, y_shut(shut_r, z) - GAP
        y = yf + u * (yr - yf)
        z = z_bottom(y) + v * (z_top(y) - z_bottom(y))
        YZ[i, j] = (y, z)

# ---- the surface, from the plan taper and the end-elevation section ----------------------------
PLAN = json.load(open(os.path.join(ROOT, "blender", "data", "plan_profile.json")))
SECT = json.load(open(os.path.join(ROOT, "blender", "data", "section_profile.json")))
hwm = np.array(PLAN["halfw_merged"], float)
sec = np.array(SECT["profile"], float)
sec = sec[np.argsort(sec[:, 0])]


def half_width(y):
    return float(np.interp(y, hwm[:, 0], hwm[:, 1]))


def section(z):
    return float(np.interp(z, sec[:, 0], sec[:, 1]))


Xf = np.zeros((NV, NU))
for i in range(NV):
    for j in range(NU):
        y, z = YZ[i, j]
        Xf[i, j] = half_width(y) * section(z)
print("surface from the drawings: x %.4f..%.4f  (tumblehome %.0f mm from the sill to the belt)"
      % (Xf.min(), Xf.max(),
         (half_width(0.0) * section(float(YZ[0, NU // 2, 1]))
          - half_width(0.0) * section(float(YZ[-1, NU // 2, 1]))) * 1000))

# ---- build --------------------------------------------------------------------------------------
# The car is symmetric, so only the left door is built; a Mirror modifier makes the right one
# (Nik, 2026-10-26). Half the geometry, and the two sides cannot drift apart.
coll = bpy.data.objects[CUT.split(",")[0]].users_collection[0]
for old_name in ("%s_Left" % PANEL, "%s_Right" % PANEL):
    old = bpy.data.objects.get(old_name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)

bm = bmesh.new()
Vt = [[bm.verts.new((Xf[i, j], YZ[i, j, 0], YZ[i, j, 1])) for j in range(NU)] for i in range(NV)]
for i in range(NV - 1):
    for j in range(NU - 1):
        bm.faces.new((Vt[i][j], Vt[i][j + 1], Vt[i + 1][j + 1], Vt[i + 1][j]))
bm.faces.ensure_lookup_table(); bm.normal_update()
if sum(f.normal.x for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
res = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
    v.co.x -= LIP
bm.normal_update()

name = "%s_Left" % PANEL
mesh = bpy.data.meshes.new(name)
bm.to_mesh(mesh); bm.free()
if hasattr(mesh, "shade_smooth"):
    mesh.shade_smooth()
for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):
    _f = getattr(mesh, _n, None)
    if _f:
        _f(angle=math.radians(35))
        break
paint = bpy.data.materials.get("paint_gunmetal")
if paint:
    mesh.materials.append(paint)
ob = bpy.data.objects.new(name, mesh)
coll.objects.link(ob)
mir = ob.modifiers.new("Mirror", "MIRROR")
mir.use_axis[0] = True
mir.use_clip = False
objs = [ob]
print("%s: %d verts, %d faces, mirrored to the right-hand side" % (name, len(mesh.vertices),
                                                                   len(mesh.polygons)))

# ---- cut the matching opening in the blocky side -------------------------------------------------
# A proximity cut against the new panel leaves a ragged edge, because the blocky side is coarse and its
# faces straddle the boundary. The opening is cut from the door's own outline in (y, z) instead: every
# outer-skin face whose centre falls inside it goes, which gives an edge that follows the shut lines.
outline = ([tuple(YZ[0, j]) for j in range(NU)]                       # bottom, front -> rear
           + [tuple(YZ[i, NU - 1]) for i in range(1, NV)]             # up the rear shut line
           + [tuple(YZ[NV - 1, j]) for j in range(NU - 2, -1, -1)]    # top, rear -> front
           + [tuple(YZ[i, 0]) for i in range(NV - 2, 0, -1)])         # down the front shut line
OY = np.array([p[0] for p in outline])
OZ_ = np.array([p[1] for p in outline])
cy, cz = OY.mean(), OZ_.mean()
GROW = 1.012                                    # take a little more than the panel, so no sliver is left


def inside(y, z):
    yy = cy + (y - cy) / GROW
    zz = cz + (z - cz) / GROW
    j, n, hit = len(OY) - 1, len(OY), False
    for i in range(n):
        if (OZ_[i] > zz) != (OZ_[j] > zz):
            xi = OY[i] + (zz - OZ_[i]) * (OY[j] - OY[i]) / (OZ_[j] - OZ_[i])
            if yy < xi:
                hit = not hit
        j = i
    return hit


for name in CUT.split(","):
    cut_ob = bpy.data.objects.get(name)
    if cut_ob is None:
        continue
    bm = bmesh.new(); bm.from_mesh(cut_ob.data); bm.normal_update()
    kill = [f for f in bm.faces
            if abs((cut_ob.matrix_world @ f.calc_center_median()).x) >= 0.30
            and inside(*(lambda c: (c.y, c.z))(cut_ob.matrix_world @ f.calc_center_median()))]
    print("%s: %d faces removed for the door opening" % (name, len(kill)))
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(cut_ob.data); bm.free(); cut_ob.data.update()

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
