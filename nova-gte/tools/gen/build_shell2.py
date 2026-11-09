"""Build the body shell with each cross-section assembled from what was measured at that station.

The first shell stretched ONE master section along the car. Measured against the 34 points triangulated on the
real car (tools/gen/geo_check.py) it was right on the flank and the glass tops, but 56-75 mm too wide at the
bottom of every window - the real car has a belt shoulder and the side glass sits ~70 mm inboard of the flank,
which a stretched envelope cannot have - and it stopped 170 mm short of the tail.

Now each section is built from segments, in this order, each segment with a FIXED number of rows so every
feature lands on the same row at every station and runs straight along the car:

  A  flank      floor -> belt          x = halfw(y) * section(z)   (plan taper x front-elevation section)
  B  shoulder   belt -> glass base     in to body_profile glass_base_x, at the traced glass_base height
  C  glass      glass base -> top      the side glass plane, up to body_profile glass_top_x / cant
  D  frame      glass top -> drip      the 41 mm black frame + body band + gutter measured above the glass
  E  roof       drip -> crown          the roof arch, down to the centreline at the silhouette's height

Where a station has no greenhouse - over the bonnet, down the screen, over the tailgate - the upper segments are
squeezed under the silhouette's own top line, so the same row structure carries on.

The tail ends on a measured rear face rather than fading out: y 1.735 at the centre, wrapping forward at the
corners through the tail-lamp points (TL_TI at x 0.58 y 1.708, TL_TO at x 0.68 y 1.656).

All inputs are in the model frame (body_profile values get + DZ). Sparse photo lists are interpolated and then
smoothed along the car so their knots do not show as kinks.

blender -b blender/nova_proc.blend --python tools/gen/build_shell2.py -- out.blend
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

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
D = os.path.join(ROOT, "blender", "data")
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
BA = json.load(open(os.path.join(ROOT, "tools", "photomatch", "ba_result.json")))["points"]
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PLAN = np.array(json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(D, "section_body.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
ROOF = json.load(open(os.path.join(D, "roof_profile.json")))
WIN = json.load(open(os.path.join(D, "windows.json")))
DZ = float(PF["dz"])

Y0, Y_END, DY = -1.62, 1.735, 0.012
NA, NB, NC, ND, NE = 12, 3, 20, 3, 11   # glass band 20 rows: the window cuts land on a ~18 mm
#                                         grid instead of a 46 mm one, so their edges stop reading
#                                         as a staircase against the photographs
ARCH_P = 3.0                     # roof arch: drop ~ (x/x_drip)^3, fitted to roof_profile's measured arch
FRAME = 0.041                    # glass top -> drip gutter, measured above the windows (body_profile _cant_src)

ys = np.arange(Y0, Y_END + 1e-9, DY)
ys[-1] = Y_END


def smooth(v, sigma_m):
    """Gaussian smoothing along the car, in metres."""
    s = max(sigma_m / DY, 1e-6)
    k = np.arange(-int(3 * s) - 1, int(3 * s) + 2)
    w = np.exp(-0.5 * (k / s) ** 2); w /= w.sum()
    pad = len(k) // 2
    return np.convolve(np.r_[np.repeat(v[0], pad), v, np.repeat(v[-1], pad)], w, "valid")


def table(pts, dz=0.0):
    a = np.array(sorted(pts), float)
    return np.interp(ys, a[:, 0], a[:, 1] + dz)


def line(*names):
    return sorted({(round(a, 5), round(b, 5)) for n in names for a, b in SP[n]})


half = np.interp(ys, PLAN[:, 0], PLAN[:, 1])
floor = smooth(table(PF["floor"], DZ), 0.020)
top = smooth(table(PF["top"], DZ), 0.018)
belt = smooth(table(line("belt", "belt_b")), 0.040)
# Glass base height: the paint/black boundary traced along the side photograph (body_profile `belt`), which is
# where the measured window corners sit - DG_RB 0.858, QW_FB 0.881, QW_RB 0.868. The blueprint's `glass_base`
# line reads 0.92 here and is something else (the trim above the seal); building to it left every window
# bottom ~60 mm high.
z_gb = smooth(table(PF["belt"], DZ), 0.050)
x_gb = smooth(table(PF["glass_base_x"]), 0.070)
# Ahead of the B-pillar the glass-top line carries on DOWN THE A-PILLAR, through the two windscreen corners
# triangulated from c20 + cCF (WS_T at the header, WS_B at the scuttle). Without them both lists were clamped flat
# forward of y -0.25 and the A-pillar base came out 18-31 mm inside the real one.
WS_B, WS_T = BA["WS_B"], BA["WS_T"]
x_gt = smooth(table(PF["glass_top_x"] + [[WS_B[1], WS_B[0]]]), 0.050)
z_gt = smooth(table([[y, z + DZ] for y, z in PF["cant"]] + [[WS_B[1], WS_B[2] + DZ], [WS_T[1], WS_T[2] + DZ]]), 0.050)
x_dr = smooth(table(ROOF["outline"]), 0.070)


# ---- the side windows' own top and bottom edges, as tables along the car -------------------------------------
# The bumper reads as a pressing because every feature on it is a ROW of the swept section - the rib grooves, the
# plate recess edges, the lower tuck. The shell's windows were not: they were cut out of the finished grid
# afterwards, across the rows, so their top and bottom came out as a staircase of whatever cell the outline
# happened to fall in. Here the glass band is made to START on the window's lower edge and END on its upper one
# wherever a window exists, so both are exact grid lines and the cut has nothing left to approximate.
def win_edges(name):
    a = np.array(WIN[name], float)
    y0, y1 = a[:, 0].min(), a[:, 0].max()
    ys_in = (ys > y0 + 1e-6) & (ys < y1 - 1e-6)
    lo = np.full(len(ys), np.nan); hi = np.full(len(ys), np.nan)
    for i in np.nonzero(ys_in)[0]:
        zz = a[np.abs(a[:, 0] - ys[i]) < 0.030, 1]
        if len(zz) < 2:
            # the outline is sampled coarsely here: take the nearest point either side
            k = np.argsort(np.abs(a[:, 0] - ys[i]))[:6]
            zz = a[k, 1]
        lo[i], hi[i] = zz.min(), zz.max()
    return lo, hi, (y0, y1)


WLO = np.full(len(ys), np.nan)
WHI = np.full(len(ys), np.nan)
for _n in ("door", "quarter"):
    _lo, _hi, _span = win_edges(_n)
    m = ~np.isnan(_lo)
    WLO[m], WHI[m] = _lo[m], _hi[m]
# ease the forced rows in and out over EASE, so the band does not kink at a window's ends
EASE = 0.055
_w = np.zeros(len(ys))
for i in range(len(ys)):
    if np.isnan(WLO[i]):
        continue
    d = 1e9
    for j in (i,):
        k = i
        while k > 0 and not np.isnan(WLO[k - 1]):
            k -= 1
        k2 = i
        while k2 < len(ys) - 1 and not np.isnan(WLO[k2 + 1]):
            k2 += 1
        d = min(ys[i] - ys[k], ys[k2] - ys[i])
    t = min(1.0, max(0.0, d / EASE))
    _w[i] = t * t * (3 - 2 * t)
WW = _w


def sect(z):
    return float(np.interp(z, SECT[:, 0], SECT[:, 1]))


# the rear face in plan: flat across the middle, wrapping forward at the corners through the tail-lamp points
A_WRAP, P_WRAP = 0.88, 6.4


def y_face(x):
    return Y_END - A_WRAP * abs(x) ** P_WRAP


def section(i):
    """Rows of (x, z) for station i, outboard at the floor round to the centreline at the crown."""
    y = ys[i]
    zb, zt, hw = floor[i], top[i], half[i]
    # the shoulder has to start BELOW the glass base: at the rear the blueprint's belt line climbs above it
    zbe = min(belt[i], zt - 0.060, z_gb[i] - 0.040)
    zbe = max(zbe, zb + 0.050)
    xf = lambda z: hw * sect(z)
    rows = [(xf(zb) - 0.035, zb - 0.006)]                                       # under-return
    for t in np.linspace(0.0, 1.0, NA):                                         # A flank
        z = zb + t * (zbe - zb)
        rows.append((xf(z), z))
    zg0 = min(max(z_gb[i], zbe + 0.004), zt - 0.045)
    if not math.isnan(WLO[i]):
        zg0 = zg0 + WW[i] * (WLO[i] - zg0)
    xg0 = min(x_gb[i], xf(zbe) - 0.020)
    for t in np.linspace(0.0, 1.0, NB + 1)[1:]:                                 # B shoulder
        rows.append((xf(zbe) + t * (xg0 + 0.004 - xf(zbe)), zbe + t * (zg0 - zbe)))
    zg1 = min(max(min(z_gt[i], zt - 0.020), zg0 + 0.010), zt - 0.012)
    if not math.isnan(WHI[i]):
        zg1 = min(max(zg1 + WW[i] * (WHI[i] - zg1), zg0 + 0.010), zt - 0.008)
    xg1 = min(x_gt[i], xg0 - 0.005)
    for t in np.linspace(0.0, 1.0, NC + 1)[1:]:                                 # C glass plane
        rows.append((xg0 + t * (xg1 - xg0), zg0 + t * (zg1 - zg0)))
    zd = min(max(min(z_gt[i] + FRAME, zt - 0.004), zg1 + 0.004), zt - 0.002)
    xd = min(max(x_dr[i], xg1), xg1 + 0.030)
    for t in np.linspace(0.0, 1.0, ND + 1)[1:]:                                 # D frame / drip
        rows.append((xg1 + t * (xd - xg1), zg1 + t * (zd - zg1)))
    for k in range(1, NE + 1):                                                  # E roof arch
        u = math.cos(0.5 * math.pi * k / NE)            # 1 at the drip -> 0 at the crown, denser near the drip
        rows.append((xd * u, zt - (zt - zd) * u ** ARCH_P))
    rows[-1] = (0.0, zt)
    return rows


NR = len(section(0))
bm = bmesh.new()
V = []
for i, y in enumerate(ys):
    col = []
    for x, z in section(i):
        col.append(bm.verts.new((x, min(float(y), y_face(x)), z)))
    V.append(col)
# Each face remembers which segment of the section it belongs to (0 flank, 1 shoulder, 2 glass, 3 frame,
# 4 roof), so the window and screen cuts can work on the shell's own structure instead of coordinates.
L_SEG = bm.faces.layers.int.new("gh_seg")
SEG_OF_ROW = [0] * (1 + NA) + [1] * NB + [2] * NC + [3] * ND + [4] * NE
for i in range(len(ys) - 1):
    for j in range(NR - 1):
        a, b, c, d = V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]
        if (a.co - d.co).length < 1e-7 and (b.co - c.co).length < 1e-7:
            continue
        f = bm.faces.new((a, b, c, d))
        f[L_SEG] = SEG_OF_ROW[min(j + 1, len(SEG_OF_ROW) - 1)]
# close the tail: fan the last section in to a point on the centreline, half-way up the face
last = V[-1]
mid = bm.verts.new((0.0, Y_END, 0.5 * (floor[-1] + top[-1])))
for j in range(NR - 1):
    try:
        bm.faces.new((last[j], mid, last[j + 1]))
    except ValueError:
        pass
bm.faces.ensure_lookup_table(); bm.normal_update()
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.normal_update()
if sum(f.normal.x * f.calc_center_median().x for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])

name = "Body_Shell"
old = bpy.data.objects.get(name)
coll = old.users_collection[0] if old else (bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection)
if old:
    bpy.data.objects.remove(old, do_unlink=True)
mesh = bpy.data.meshes.new(name)
bm.to_mesh(mesh); bm.free()
if hasattr(mesh, "shade_smooth"):
    mesh.shade_smooth()
for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):
    _f = getattr(mesh, _n, None)
    if _f:
        _f(angle=math.radians(38))
        break
paint = bpy.data.materials.get("paint_gunmetal")
if paint:
    mesh.materials.append(paint)
ob = bpy.data.objects.new(name, mesh)
coll.objects.link(ob)
mir = ob.modifiers.new("Mirror", "MIRROR")
mir.use_axis[0] = True; mir.use_clip = True; mir.merge_threshold = 0.001

print("Body_Shell: %d stations x %d rows (A%d B%d C%d D%d E%d), %d faces"
      % (len(ys), NR, NA, NB, NC, ND, NE, len(mesh.polygons)))
for yq in (-0.40, 0.39, 0.59, 1.10, 1.45):
    i = int(np.argmin(np.abs(ys - yq))); r = section(i)
    print("  y %+.2f  belt z %.3f  flank x %.3f | glass base (%.3f, %.3f)  top (%.3f, %.3f)  drip (%.3f, %.3f)  crown %.3f"
          % (ys[i], r[NA][1], r[NA][0], r[NA + NB][0], r[NA + NB][1], r[NA + NB + NC][0], r[NA + NB + NC][1],
             r[NA + NB + NC + ND][0], r[NA + NB + NC + ND][1], top[i]))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
