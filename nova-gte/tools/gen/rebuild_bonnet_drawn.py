"""Rebuild the bonnet from the measurements. No Meshy.

The old Hood_Panel came off the Meshy shell and sits 25-53 mm **below** the drawn line from y -1.55
back to -1.00, which is why its nose reads lifted - the panel is too flat, so relative to its own rear
the front looks raised. It is also the thing that was corrugating the wing's top edge, because the wing
is built to meet it.

Everything needed is already measured, and two independent sources agree on it:

  **centreline** - `top_bonnet_fit` in body_profile: a quadratic fitted to six photo points, chosen over
  a spline because the spline's curvature jumped 4x between knots and showed as waves in the
  reflections. Against the line blueprint's own `bonnet_top` it reads within -17 to +15 mm from y -1.60
  to -0.80. (Ahead of -1.68 the blueprint trace dives over the bonnet's front edge and is not
  comparable.)

  **crown across** - `crown.bonnet` = 30 mm, quadratic in |x|/x_shut. At the shut line that puts the
  edge at z 0.8515 at y -1.20 against the blueprint's `bonnet_shut` 0.8611: 10 mm.

  **the front V** - `front_panel.bonnet_v`: the leading edge is a straight V from the tip at
  (0, -1.755) opening at a = 0.151, reaching the corner at (0.605, -1.664), with both photographs
  putting its height at z 0.722 +- 4 mm.

  **the nose roll** - `bonnet_creases.nose_roll`: the surface rolls down to that edge over 150 mm with
  the drop fading as (1-s)^3. Power 3 rather than 2 because 2 left a curvature step, which reads as a
  line in the reflections.

  **the creases** - `bonnet_creases`: two lengthwise creases, traced in redgte_20, 8 mm deep, running
  from x 0.379 at y -1.661 outwards at dx/dy 0.1249. Nik, 2026-10-12: the only bonnet creases run
  lengthways.

Left half only, Mirror clipped on the centreline.

blender -b blender/nova_proc.blend --python tools/gen/rebuild_bonnet_drawn.py -- out.blend [--no-creases]
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
CREASES = "--no-creases" not in args

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]

FIT = PF["top_bonnet_fit"]
C = np.array(FIT["c"], float)
BV = PF["front_panel"]["bonnet_v"]
BC = PF["bonnet_creases"]
NR = BC["nose_roll"]
CROWN, CROWN_P = PF["crown"]["bonnet"]

DZ = 0.0193                                  # body_profile is in the photo frame; the model is DZ up
X_SHUT = float(BV["x_shut"])                 # 0.605
Y_TIP = float(BV["y0"])                      # -1.755 at the centreline
V_A = float(BV["a"])                         # the V opens at this rate
Z_EDGE = float(NR["E"]) + DZ                 # 0.722 in the photo frame
ROLL_L, ROLL_P = float(NR["L"]), float(NR["power"])
# The bonnet's REAR edge is curved in plan, measured on the bonnet surface from c20 / cCF (body_profile
# scuttle_curve): y = -0.900 + 0.33 x^2 - the centre 115 mm further forward than at the sides. A straight cut at
# -0.785 (where the old panel happened to end) ran the bonnet back over the scuttle and lifted the screen base.
SC = PF["scuttle_curve"]
Y_REAR = -0.785                              # rearmost (at the shut line), kept for the crease printout


def y_rear(x):
    return float(SC["yr0"] + SC["kr"] * x * x) - 0.002
NX, NY = 40, 90


bt = np.array(sorted({(round(a, 5), round(b, 5))
                      for n in ("bonnet_top", "bonnet_top_b") for a, b in SP[n]}), float)
bs = np.array(sorted({(round(a, 5), round(b, 5))
                      for n in ("bonnet_shut", "bonnet_shut_b") for a, b in SP[n]}), float)
_pad = lambda a, n: np.r_[np.repeat(a[0], n // 2), a, np.repeat(a[-1], n // 2)]
_bs_raw = bs[:, 1].copy()
bs[:, 1] = np.convolve(_pad(bs[:, 1], 9), np.ones(9) / 9.0, "valid")
# 2026-10-27 (14): the shut line's height is a pixel trace - 2.7 mm steps in z every 5.4 mm in y - and the 9-tap
# mean of it still ripples about half a millimetre every ~50 mm. The bonnet's edge drop and the wing's top both
# carry it, so it showed as streaks running across the shut in the viewport. The data cannot say anything finer
# than a pixel, so from the nose back to y -0.84 the curve used is a least-squares cubic B-spline (knots 120 mm,
# tools/gen/trace_fit.py) that stays within one pixel of the trace. Behind -0.84 the trace climbs 32 mm onto the
# cowl - a different feature - and the old curve is kept there, blended in over 20 mm.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trace_fit import bspline_fit                  # noqa: E402
FIT_END, FIT_BLEND, FIT_KNOT = -0.84, 0.020, 0.12
_m = bs[:, 0] <= FIT_END
_f, _worst = bspline_fit(bs[_m, 0], _bs_raw[_m], knot=FIT_KNOT)
_in = int((np.abs(_f(bs[_m, 0]) - _bs_raw[_m]) <= 0.0027).sum())
_fz = _f(bs[:, 0])
_t = np.clip((bs[:, 0] - FIT_END) / FIT_BLEND, 0.0, 1.0)
_w = _t * _t * (3.0 - 2.0 * _t)
_old = bs[:, 1].copy()
bs[:, 1] = (1.0 - _w) * _fz + _w * _old
print("bonnet_shut: B-spline fit (knots %.0f mm) to y %+.2f: %d of %d trace points within one pixel, worst %.1f mm; "
      "moves the old 9-tap curve by up to %.1f mm"
      % (FIT_KNOT * 1000, FIT_END, _in, int(_m.sum()), 1000 * _worst, 1000 * np.abs(bs[:, 1] - _old).max()))


def z_centre(y):
    """The fitted centreline, lifted into the model frame.

    This is the fault that put the bonnet low. `top_bonnet_fit` is a fit to *photo* points, so it is in
    the photo/BA frame like everything else in body_profile - ground at the loaded tyre contact. Every
    other quantity taken from that file (belt, cant, arch_shapes, glass) gets + DZ; this one did not,
    and the bonnet came out 13-32 mm below where the photograph's own silhouette puts it.
    """
    return float(np.polyval(C, y)) + DZ


def y_front(x):
    """The leading edge: a straight V from the tip, opening outboard."""
    return Y_TIP + V_A * abs(x)


def z_crown(x, y):
    """The bonnet's surface before the nose rolls down to the front edge.

    Nik, 2026-10-26: the bonnet has a RIDGE down the middle and its sides slope down to the wing. The
    line blueprint's hatchback front view shows it - two short diagonals where the raised centre meets
    the sloping outer panel, at |x| 351 to 440 mm, which is `bonnet_creases` (379 mm at the nose rising
    to 498 at the scuttle) seen head on.

    So the section is flat between the creases and then falls away, rather than doming from the
    centreline. How far it falls is not guessed either: the drop is solved at each station so the edge
    lands on the blueprint's own `bonnet_shut` line. That comes out around 40 mm, against the 30 mm the
    old `crown.bonnet` carried - which is why the first rebuild sat 12 mm proud of the shut line.
    """
    xc = crease_x(y)
    a = abs(x)
    if a <= xc:
        return z_centre(y)
    drop = z_centre(y) - z_shut(y)
    t = (a - xc) / max(X_SHUT - xc, 1e-6)
    return z_centre(y) - drop * (t ** CROWN_P)


def z_shut(y):
    """Where the bonnet's edge has to finish: the blueprint's own shut line, which is the side-elevation
    silhouette of the bonnet-to-wing joint."""
    return float(np.interp(y, bs[:, 0], bs[:, 1]))


def z_at(x, y):
    zc = z_crown(x, y)
    ye = y_front(x)
    s = (y - ye) / ROLL_L
    if s >= 1.0:
        return zc
    s = max(s, 0.0)
    drop = z_crown(x, ye) - Z_EDGE                # how far the surface has to come down at the edge
    return zc - drop * (1.0 - s) ** ROLL_P


def crease_x(y):
    return float(BC["x0"] + BC["dxdy"] * (y - BC["y0"]))


d = [z_centre(y) - float(np.interp(y, bt[:, 0], bt[:, 1])) for y in np.arange(-1.60, -0.79, 0.02)]
print("centreline vs the blueprint over y -1.60..-0.80: %+.0f mm mean, %+.0f min, %+.0f max"
      % (1000 * np.mean(d), 1000 * min(d), 1000 * max(d)))
e = [z_crown(X_SHUT, y) - float(np.interp(y, bs[:, 0], bs[:, 1])) for y in np.arange(-1.55, -0.79, 0.02)]
print("shut-line edge vs the blueprint's bonnet_shut: %+.0f mm mean, %+.0f min, %+.0f max"
      % (1000 * np.mean(e), 1000 * min(e), 1000 * max(e)))
print("front V: tip (0, %.3f, %.3f), corner (%.3f, %.3f, %.3f); rolls down over %.0f mm"
      % (Y_TIP, z_at(0.0, Y_TIP), X_SHUT, y_front(X_SHUT), z_at(X_SHUT, y_front(X_SHUT)), ROLL_L * 1000))

# ---- the grid ------------------------------------------------------------------------------------
# Columns are laid out by a parameter, not by a fixed x, so that three of them sit ON the crease at
# EVERY station. The crease line moves outboard as it runs back (x 379 mm at the nose, 498 at the
# scuttle); columns at a fixed x let it wander between them and the fold came out scalloped - the same
# fault the wing's flare step had, and for the same reason.
W_CR = 0.013                    # the fold's radius: it is a soft crease on the car, not a groove
N_IN, N_CR, N_OUT = 18, 5, 14


def col_x(u, y):
    """x at parameter u (0 at the centreline, 1 at the shut line) for this station."""
    xc = crease_x(y)
    a0 = N_IN / float(N_IN + N_CR + N_OUT)
    a1 = (N_IN + N_CR) / float(N_IN + N_CR + N_OUT)
    if u <= a0:
        return (u / a0) * (xc - W_CR)
    if u <= a1:
        return (xc - W_CR) + (u - a0) / (a1 - a0) * (2 * W_CR)
    return (xc + W_CR) + (u - a1) / (1.0 - a1) * (X_SHUT - xc - W_CR)


US = [i / float(N_IN + N_CR + N_OUT) for i in range(N_IN + N_CR + N_OUT + 1)]

G = []
for u in US:
    col = []
    for t in np.linspace(0.0, 1.0, NY):
        # the station's own front edge depends on x, so solve x and y together down the column
        x = col_x(u, -1.2)
        for _ in range(3):
            ye = y_front(x)
            y = ye + t * (y_rear(x) - ye)
            x = col_x(u, y)
        col.append((x, y, z_at(x, y)))
    G.append(col)
print("grid: %d columns x %d stations; crease columns track x %.3f at the nose to %.3f at the scuttle"
      % (len(G), NY, crease_x(Y_TIP), crease_x(Y_REAR)))

# ---- the shared bonnet-to-wing shut line ---------------------------------------------------------
# The wing used to find its top edge by scanning this panel's mesh boundary, rounding stations and smoothing,
# which is what left the shut 7-40 mm wide (2026-10-27 (12)). Instead this panel writes its own side-edge
# column - the exact vertices of the u = 1 column - and the wing builds its top edge on the same points, so the
# two edges coincide by construction and roll_edges opens the real gap. The scuttle appends its side edge.
SHUT_JSON = os.path.join(D, "shut_bonnet_wing.json")
_shut = {"_src": "rebuild_bonnet_drawn.py (u=1 column) + rebuild_scuttle_drawn.py (x = X_SIDE column); "
                 "model frame; the wing's top edge is built on these points",
         "bonnet": [[round(p[0], 6), round(p[1], 6), round(p[2], 6)] for p in G[-1]],
         # dz/dx of the bonnet's surface across the car AT its side edge (negative: falling outboard). The wing's
         # top arrives with this slope so the two surfaces are flush across the shut (2026-10-27 (13)).
         "bonnet_slope": [round((z_at(X_SHUT, p[1]) - z_at(X_SHUT - 0.002, p[1])) / 0.002, 5) for p in G[-1]],
         "bonnet_corner": [X_SHUT, y_front(X_SHUT), z_at(X_SHUT, y_front(X_SHUT))],
         "v_line": {"y_tip": Y_TIP, "a": V_A}}
if os.path.exists(SHUT_JSON):
    _old = json.load(open(SHUT_JSON))
    for _k in ("scuttle", "scuttle_slope"):
        if _k in _old:
            _shut[_k] = _old[_k]
json.dump(_shut, open(SHUT_JSON, "w"), indent=1)
print("shut line: bonnet side edge written, %d points, y %+.4f .. %+.4f"
      % (len(G[-1]), G[-1][0][1], G[-1][-1][1]))

bm = bmesh.new()
V = [[bm.verts.new(p) for p in col] for col in G]
for i in range(len(G) - 1):
    for j in range(NY - 1):
        bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
# the front edge turns under into a lip
res = bmesh.ops.extrude_edge_only(bm, edges=[e_ for e_ in bm.edges if e_.is_boundary
                                             and all(v.co.y < y_front(abs(v.co.x)) + 1e-4 for v in e_.verts)])
for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
    v.co.y += 0.004
    v.co.z -= float(BV["lip"])
bm.faces.ensure_lookup_table(); bm.normal_update()
if sum(f.normal.z for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
bm.normal_update()

name = "Hood_Panel"
old = bpy.data.objects.get(name)
coll = old.users_collection[0] if old else bpy.data.objects["Side_Profile_Door_Left"].users_collection[0]
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
mir.use_clip = True
mir.merge_threshold = 0.001
vs = [v.co for v in mesh.vertices]
print("%s: %d verts, %d faces, mirrored on the centreline%s"
      % (name, len(vs), len(mesh.polygons), "" if CREASES else " (creases off)"))
print("   x 0..%.3f, y %.3f..%.3f, z %.4f..%.4f"
      % (max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs),
         min(v.z for v in vs), max(v.z for v in vs)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
