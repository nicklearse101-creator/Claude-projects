"""Cut the wheel arches and the window apertures into the lofted shell.

The shell is one closed surface. The openings are cut with boolean prisms built from the traced
outlines, swept right through the car in x, so both sides get the same cut and the edges come out on
the outline rather than stair-stepped along the mesh.

Outlines, all already traced:
  wheel arches   `arch_shapes.front` / `.rear` in body_profile - the lip outlines off the side
                 photograph, 32 and 27 points (photo frame, so + DZ)
  door window    between the A-pillar's inner edge and the B-pillar, from `glass_base` up to `dlo_top`
  quarter window between the B-pillar and the C-pillar, the same two lines above and below

The pillar edges come from `zones.a_pillar_outer`, `zones.b_pillar` and `zones.quarter_rear_edge`,
measured on the photographs; the A and C pillars are leaning, so their y is taken at each height
rather than as a single station.

blender -b blender/nova_proc.blend --python tools/gen/cut_apertures.py -- out.blend [--keep-cutters]
"""
import json
import os
import sys

import bmesh
import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
KEEP = "--keep-cutters" in args

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
DZ = 0.0193
X_WIDE = 1.2                    # the cutters run right through the car


def curve(*names):
    return np.array(sorted({(round(a, 5), round(b, 5)) for n in names for a, b in SP[n]}), float)


def smooth(p, n=9):
    q = p.copy()
    pad = np.r_[np.repeat(p[:1, 1], n // 2), p[:, 1], np.repeat(p[-1:, 1], n // 2)]
    q[:, 1] = np.convolve(pad, np.ones(n) / n, "valid")
    return q


dlo = smooth(curve("dlo_top", "dlo_top_b"))
gbase = smooth(curve("glass_base", "glass_base_b"))
AP = np.array(PF["zones"]["a_pillar_outer"], float); AP[:, 1] += DZ
QR = np.array(PF["zones"]["quarter_rear_edge"], float); QR[:, 1] += DZ
B0, B1 = PF["zones"]["b_pillar"]
A_W = 0.070
# zones.quarter_rear_edge IS the quarter window's rear edge - its ends match the measured QW_RB / QW_RT corners
# (y 1.458 vs 1.446, 1.096 vs 1.110). Pulling it 90 mm forward as if it were the pillar's outer face left a
# small window and a 200 mm C-pillar where the car has one glass running back to a slim pillar (Nik).
C_W = 0.0


def pillar_y(pts, z):
    """A leaning pillar's y at this height, clamped to the range it was actually measured over.

    Extrapolated below its foot the A-pillar line runs away forward: the window's lower front corner
    came out at y -0.696 instead of -0.629, and the cut ate the pillar."""
    (y0, z0), (y1, z1) = pts
    z = min(max(z, min(z0, z1)), max(z0, z1))
    return float(y0 + (y1 - y0) * (z - z0) / (z1 - z0))


def z_dlo(y):
    return float(np.interp(y, dlo[:, 0], dlo[:, 1]))


_belt = np.array(sorted(PF["belt"]), float)


def z_gbase(y):
    """The window's lower edge: the photo-traced paint/black boundary, where the measured glass corners sit."""
    return float(np.interp(y, _belt[:, 0], _belt[:, 1] + DZ))


def window_outline(front, rear, n=28):
    """A window as one simple loop: along the top, down the back, along the bottom, up the front.

    The first version walked the top and bottom AND then added the two side edges separately, which
    repeated the corners and made a figure-of-eight. A self-intersecting prism is not a solid, so the
    boolean silently did nothing and the greenhouse stayed shut.
    """
    # the four corners, each pillar evaluated at the height it actually meets
    zf_t = z_dlo(front(z_dlo(0.0)))
    zf_b = z_gbase(front(z_gbase(0.0)))
    zr_t = z_dlo(rear(z_dlo(0.0)))
    zr_b = z_gbase(rear(z_gbase(0.0)))
    yf_t, yf_b = front(zf_t), front(zf_b)
    yr_t, yr_b = rear(zr_t), rear(zr_b)
    pts = []
    for t in np.linspace(0.0, 1.0, n):           # the top, front to rear
        y = yf_t + t * (yr_t - yf_t)
        pts.append((y, z_dlo(y)))
    for t in np.linspace(0.0, 1.0, 6)[1:]:       # down the rear pillar
        pts.append((yr_t + t * (yr_b - yr_t), zr_t + t * (zr_b - zr_t)))
    for t in np.linspace(0.0, 1.0, n)[1:]:       # the bottom, rear to front
        y = yr_b + t * (yf_b - yr_b)
        pts.append((y, z_gbase(y)))
    for t in np.linspace(0.0, 1.0, 6)[1:-1]:     # up the front pillar
        pts.append((yf_b + t * (yf_t - yf_b), zf_b + t * (zf_t - zf_b)))
    return pts


def screen_outline(n=30):
    """The windscreen: the traced `screen` line up the front, the roof's header across the top, and
    the scuttle along the bottom."""
    scr = smooth(np.array(sorted({(round(a, 5), round(b, 5)) for a, b in SP["screen"]}), float), 5)
    y_lo, z_lo = float(scr[0, 0]), float(scr[0, 1])          # at the scuttle
    y_hi, z_hi = float(scr[-1, 0]), float(scr[-1, 1])        # at the header
    pts = [(float(y), float(z)) for y, z in scr]             # up the screen's own line
    pts.append((y_hi + 0.030, z_hi - 0.010))                 # across the header
    pts.append((y_lo + 0.090, z_lo + 0.030))                 # down the back of the opening
    pts.append((y_lo + 0.050, z_lo + 0.004))                 # and along the scuttle
    return pts


def backlight_outline():
    """The rear screen, from the tailgate glass corners triangulated in body_profile `glass_panels`
    (c24 + cAR) - bottom at z 0.905, top at 1.181 - with the C-pillars for its sides."""
    hg = PF["zones"]["hatch_glass"]
    z0, z1 = float(hg["z_bot"]) + DZ, float(hg["z_top"]) + DZ
    gp = PF["glass_panels"]["hatch"]
    y_bot = float(gp["origin"][0])
    # the glass leans forward going up: its top is further forward than its bottom
    y_top = y_bot + float(gp["v_dir"][0]) * (z1 - z0) / max(abs(float(gp["v_dir"][1])), 1e-6)
    front = lambda z: pillar_y(QR, z) - 0.010
    pts = []
    for t in np.linspace(0.0, 1.0, 20):          # up the rear edge of the glass
        pts.append((y_bot + t * (y_top - y_bot), z0 + t * (z1 - z0)))
    for t in np.linspace(0.0, 1.0, 14)[1:]:      # across the top, forward to the C-pillar
        pts.append((y_top + t * (front(z1) - y_top), z1))
    for t in np.linspace(0.0, 1.0, 14)[1:]:      # down the C-pillar
        z = z1 + t * (z0 - z1)
        pts.append((front(z), z))
    for t in np.linspace(0.0, 1.0, 14)[1:-1]:    # and back along the bottom
        pts.append((front(z0) + t * (y_bot - front(z0)), z0))
    return pts


def arch_outline(key):
    a = np.array(PF["arch_shapes"][key], float)
    a[:, 1] += DZ
    pts = [(float(y), float(z)) for y, z in a]
    # close it off well below the car so the prism cuts the whole opening
    return pts + [(pts[-1][0], -0.40), (pts[0][0], -0.40)]


def prism(name, outline):
    bm = bmesh.new()
    lo = [bm.verts.new((-X_WIDE, y, z)) for y, z in outline]
    hi = [bm.verts.new((X_WIDE, y, z)) for y, z in outline]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        try:
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        except ValueError:
            pass
    bmesh.ops.contextual_create(bm, geom=lo)
    bmesh.ops.contextual_create(bm, geom=hi)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


CUTS = [
    ("CUT_arch_front", arch_outline("front")),
    ("CUT_arch_rear", arch_outline("rear")),
    ("CUT_win_door", window_outline(lambda z: pillar_y(AP, z) + A_W, lambda z: B0)),
    ("CUT_win_quarter", window_outline(lambda z: B1, lambda z: pillar_y(QR, z) - C_W)),
    ("CUT_screen", screen_outline()),
    ("CUT_backlight", backlight_outline()),
]

shell = bpy.data.objects.get("Body_Shell")
if shell is None:
    raise SystemExit("Body_Shell is missing")
print("shell before: %d faces" % len(shell.data.polygons))
bpy.context.view_layer.objects.active = shell
for o in bpy.context.selected_objects:
    o.select_set(False)
shell.select_set(True)

# An exact boolean needs a closed solid. Cut into an open surface it invents cap faces to close it - big flat
# n-gons left INSIDE the car, which filled the windows from behind. So: mirror the halves together, give the
# shell a 2 mm skin (a real panel has thickness, and every opening then gets a proper return edge), cut, done.
for m in list(shell.modifiers):
    if m.type == "MIRROR":
        bpy.ops.object.modifier_apply(modifier=m.name)
sol = shell.modifiers.new("Skin", "SOLIDIFY")
sol.thickness = 0.002; sol.offset = -1.0; sol.use_rim = True; sol.use_even_offset = True
bpy.ops.object.modifier_apply(modifier=sol.name)
print("shell made a 2 mm solid: %d faces" % len(shell.data.polygons))

for name, outline in CUTS:
    ys = [p[0] for p in outline]; zs = [p[1] for p in outline]
    ob = prism(name, outline)
    print("%-18s %3d points, y %+.3f..%+.3f  z %+.3f..%+.3f"
          % (name, len(outline), min(ys), max(ys), min(zs), max(zs)))
    m = shell.modifiers.new(name, "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.object = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    if not KEEP:
        bpy.data.objects.remove(ob, do_unlink=True)

# The shell is an open surface, not a solid, and the exact boolean responds by keeping the cutters' end caps:
# flat faces at x = +-X_WIDE, outside the car, which then show through the openings from the far side. Nothing
# of the car lies further out than ~0.80 m, so anything beyond that is cutter debris.
bm = bmesh.new(); bm.from_mesh(shell.data)
junk = [f for f in bm.faces if abs(f.calc_center_median().x) > 0.80]
bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
bmesh.ops.delete(bm, geom=junk, context="FACES")
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context="VERTS")
bm.to_mesh(shell.data); bm.free(); shell.data.update()
print("removed %d cutter-cap faces outside the car" % len(junk))
print("shell after:  %d faces" % len(shell.data.polygons))
vs = [shell.matrix_world @ v.co for v in shell.data.vertices]
print("   x %.3f..%.3f  y %+.3f..%+.3f  z %.3f..%.3f"
      % (min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs),
         min(v.z for v in vs), max(v.z for v in vs)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
