"""Cut the arches, side windows, windscreen and backlight into the shell - without booleans.

An exact boolean needs a closed solid. On the open shell it invented cap faces inside the car that filled the
windows from behind; made solid, it showed its inner skin through the openings and threw a spike under the car.
So the openings are cut from the shell's own faces:

  arches, side windows   faces whose centre falls inside the traced outline are removed, then the new edge's
                         vertices are snapped onto the outline, so the edge follows the measured curve rather than
                         the grid's staircase. Side windows only take the glass-plane segment (gh_seg 2).
  windscreen, backlight  the roof-arch segment (gh_seg 4, and the frame row for the hatch) is removed over each
                         glass's own stretch of the car, inside its measured width - grid lines, clean edges.

Outlines: body_profile arch_shapes, zones (pillars), belt (glass base), side_profile dlo_top (glass top), the
measured screen corners WS_B / WS_T and hatch-glass corners HG_B / HG_T.

blender -b in.blend --python tools/gen/cut_apertures2.py -- out.blend
"""
import json
import os
import sys

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None
ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
D = os.path.join(ROOT, "blender", "data")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
BA = json.load(open(os.path.join(ROOT, "tools", "photomatch", "ba_result.json")))["points"]
WIN = json.load(open(os.path.join(D, "windows.json")))
DZ = float(PF["dz"])


def sm(p, n=9):
    q = np.array(p, float)
    pad = np.r_[np.repeat(q[:1, 1], n // 2), q[:, 1], np.repeat(q[-1:, 1], n // 2)]
    q[:, 1] = np.convolve(pad, np.ones(n) / n, "valid")
    return q


dlo = sm(sorted({(round(a, 5), round(b, 5)) for n in ("dlo_top", "dlo_top_b") for a, b in SP[n]}))
belt = np.array(sorted(PF["belt"]), float)
belt[:, 1] += DZ
AP = np.array(PF["zones"]["a_pillar_outer"], float)
AP[:, 1] += DZ
QR = np.array(PF["zones"]["quarter_rear_edge"], float)
QR[:, 1] += DZ
B0, B1 = PF["zones"]["b_pillar"]
A_W = 0.070


def z_top(y):
    return float(np.interp(y, dlo[:, 0], dlo[:, 1]))


def z_bot(y):
    return float(np.interp(y, belt[:, 0], belt[:, 1]))


def pillar(pts, z):
    (y0, z0), (y1, z1) = pts
    z = min(max(z, min(z0, z1)), max(z0, z1))
    return float(y0 + (y1 - y0) * (z - z0) / (z1 - z0))


def window(front, rear, n=40):
    """One simple loop: along the top, down the back, along the bottom, up the front."""
    zf_t, zf_b = z_top(front(1.2)), z_bot(front(0.86))
    zr_t, zr_b = z_top(rear(1.2)), z_bot(rear(0.86))
    yf_t, yf_b, yr_t, yr_b = front(zf_t), front(zf_b), rear(zr_t), rear(zr_b)
    pts = [(yf_t + t * (yr_t - yf_t), z_top(yf_t + t * (yr_t - yf_t))) for t in np.linspace(0, 1, n)]
    pts += [(yr_t + t * (yr_b - yr_t), zr_t + t * (zr_b - zr_t)) for t in np.linspace(0, 1, 8)[1:]]
    pts += [(yr_b + t * (yf_b - yr_b), z_bot(yr_b + t * (yf_b - yr_b))) for t in np.linspace(0, 1, n)[1:]]
    pts += [(yf_b + t * (yf_t - yf_b), zf_b + t * (zf_t - zf_b)) for t in np.linspace(0, 1, 8)[1:-1]]
    return np.array(pts)


def arch(key):
    a = np.array(PF["arch_shapes"][key], float)
    a[:, 1] += DZ
    a = a[a[:, 1] > -0.04]
    return np.vstack([a, [[a[-1, 0], -0.5], [a[0, 0], -0.5]]])


def inside(poly, y, z):
    n, hit, j = len(poly), False, len(poly) - 1
    for i in range(n):
        yi, zi = poly[i]
        yj, zj = poly[j]
        if (zi > z) != (zj > z) and y < yi + (z - zi) * (yj - yi) / (zj - zi):
            hit = not hit
        j = i
    return hit


def nearest_on(poly, y, z):
    best, bp = 1e9, None
    q = np.array([y, z])
    for k in range(len(poly) - 1):
        a, b = poly[k], poly[k + 1]
        ab = b - a
        t = np.clip(np.dot(q - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
        p = a + t * ab
        dd = float(np.hypot(*(p - q)))
        if dd < best:
            best, bp = dd, p
    return best, bp


sh = bpy.data.objects["Body_Shell"]
bm = bmesh.new()
bm.from_mesh(sh.data)
L_SEG = bm.faces.layers.int.get("gh_seg")
if L_SEG is None:
    raise SystemExit("Body_Shell has no gh_seg layer - rebuild it with build_shell2.py")
print("shell before: %d faces" % len(bm.faces))


def cut_outline(name, poly, segs=None, xmin=0.0, snap=0.018):
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(c.x) < xmin or (segs is not None and f[L_SEG] not in segs):
            continue
        if inside(poly, c.y, c.z):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    moved = 0
    for v in bm.verts:
        if not v.link_faces or not any(e.is_boundary for e in v.link_edges):
            continue
        d_, p = nearest_on(poly, v.co.y, v.co.z)
        if d_ < snap:
            v.co.y, v.co.z = float(p[0]), float(p[1])
            moved += 1
    print("%-14s %4d faces removed, %3d edge vertices snapped onto the outline" % (name, len(kill), moved))


cut_outline("arch front", arch("front"))
cut_outline("arch rear", arch("rear"))
# The side windows are the outlines traced on the blueprint and checked against the side photograph
# (tools/windows.py -> blender/data/windows.json). They replace the old construction from dlo_top + belt, whose
# quarter window was 25-33 mm short at the top (dlo_top stops at the B-pillar and was being held flat beyond it)
# and whose bottoms came from the paint line rather than the glass edge.
cut_outline("door window", np.array(WIN["door"], float), segs={2}, xmin=0.30, snap=0.026)
cut_outline("quarter window", np.array(WIN["quarter"], float), segs={2}, xmin=0.30, snap=0.026)

ws_b, ws_t = BA["WS_B"][1], BA["WS_T"][1]
y_hg_t, y_hg_b = BA["HG_T"][1], BA["HG_B"][1]
x_hg_t, x_hg_b = 0.40, BA["HG_B"][0]


def x_glass_hatch(y):
    t = np.clip((y - y_hg_t) / (y_hg_b - y_hg_t), 0, 1)
    return x_hg_t + t * (x_hg_b - x_hg_t)


def x_glass_screen(y):
    t = np.clip((y - ws_b) / (ws_t - ws_b), 0, 1)
    return BA["WS_B"][0] + t * (BA["WS_T"][0] - BA["WS_B"][0]) - 0.020


# The screen's lower edge is curved in plan (body_profile scuttle_curve): -0.740 at the centre, -0.702 from
# |x| 0.36 out. A single y across the width put the glass's bottom edge 100 mm too far back at the centre,
# which reads as a screen sitting too high (Nik).
SCV = PF["scuttle_curve"]


def y_screen_base(x):
    return min(SCV["yb0"] + SCV["k"] * x * x, SCV["yb_max"])


kill = []
for f in bm.faces:
    c = f.calc_center_median()
    if (f[L_SEG] in (3, 4) and y_screen_base(abs(c.x)) + 0.006 < c.y < ws_t - 0.020
            and abs(c.x) < x_glass_screen(c.y)):
        kill.append(f)
bmesh.ops.delete(bm, geom=kill, context="FACES")
print("%-14s %4d faces removed" % ("windscreen", len(kill)))
# The hatch glass is a flat panel between the two triangulated corners. Cutting on y alone took the whole
# tail with it: at the back of the car there is no greenhouse, so the frame and roof segments wrap the entire
# rear face, and every one of their faces between those two y values was inside the test. The cut now also has
# to lie in the glass's own plane - within BAND of the line HG_T -> HG_B in (y, z).
BAND = 0.045
P0 = np.array([y_hg_t, BA["HG_T"][2] + DZ])
P1 = np.array([y_hg_b, BA["HG_B"][2] + DZ])
D = P1 - P0
D = D / np.linalg.norm(D)
N = np.array([-D[1], D[0]])


def on_glass(y, z):
    q = np.array([y, z]) - P0
    t = float(q @ D)
    return abs(float(q @ N)) < BAND and -0.010 < t < float(np.linalg.norm(P1 - P0)) + 0.010


kill = []
for f in bm.faces:
    c = f.calc_center_median()
    if f[L_SEG] in (3, 4) and on_glass(c.y, c.z) and abs(c.x) < x_glass_hatch(c.y):
        kill.append(f)
bmesh.ops.delete(bm, geom=kill, context="FACES")
print("%-14s %4d faces removed" % ("backlight", len(kill)))

loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
bm.normal_update()
bm.to_mesh(sh.data)
bm.free()
sh.data.update()
print("shell after:  %d faces" % len(sh.data.polygons))
if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
