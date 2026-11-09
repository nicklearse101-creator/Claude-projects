"""Rebuild the rocker and the GTE's grey sill skirt - the second piece of the side profile.

Two parts, from two different sources, because they come from two different cars.

**The rocker** is body, and the line blueprint draws it: its lower edge is the `sill` line (z 0.245 at
the front, 0.239 at the rear) and its upper edge is `door_bottom` (z 0.30), the same curve the door's own
lower edge is built on, so the two panels meet without a step. Its surface is the flank's own,
x(y, z) = halfw(y) * section(z), exactly as the door is - an orthographic plan taper times an
orthographic end-elevation section.

**The skirt** is a GTE part and the blueprint is a base-model Corsa, so it is not drawn anywhere. It is
traced off Nik's grey side picture through that picture's solved camera instead
(tools/trace_skirt.py -> blender/data/skirt_profile.json): flat at z 0.32 from the front arch to about
y +0.64, then sweeping up in front of the rear wheel to meet the rear arch lip. How far the moulding
stands proud of the body is the one number the pictures do not give squarely - 12 mm, ESTIMATE, from the
earlier reading of photos 01/22/cAR (tools/side_parts.py used 15).

It is body-coloured, not the grey the older tools/side_parts.py assumed: on the white GTE in
reference/photos/commons/1989_Vauxhall_Nova_GTE__15643768649_.jpg the skirt is plainly the same white as
the car. On Nik's gun-metal picture it only looks like a darker part because its face is turned down and
away from the light - which is exactly the step the tracer keys on, so the trace itself still holds. The
wheel arches carry no trim at all on this car; their lips belong to the wing and the rear quarter.

Both ends are trimmed to the traced wheel-arch lips in body_profile.arch_shapes, and both parts are
built left-only with a Mirror modifier (Nik, 2026-10-26).

blender -b blender/nova_proc.blend --python tools/gen/rebuild_sill.py -- out.blend [--cut <objects>]
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


CUT = opt("--cut", "Side_Profile_Door_Left")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PLAN = np.array(json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(D, "section_profile.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
SK = json.load(open(os.path.join(D, "skirt_profile.json")))
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))

DZ = 0.0193                     # photo frame -> model frame
GAP = 0.004                     # panel-to-arch-lip gap
PROUD = 0.012                   # how far the skirt's face stands off the body. ESTIMATE
NY = 150


def skin_x(y, z):
    return float(np.interp(y, PLAN[:, 0], PLAN[:, 1])) * float(np.interp(z, SECT[:, 0], SECT[:, 1]))


def curve(*names):
    pts = sorted({(round(a, 5), round(b, 5)) for n in names for a, b in SP[n]})
    return np.array(pts, float)


def smooth(p, n=9):
    k = np.ones(n) / n
    q = p.copy()
    pad = np.r_[np.repeat(p[:1, 1], n // 2), p[:, 1], np.repeat(p[-1:, 1], n // 2)]
    q[:, 1] = np.convolve(pad, k, mode="valid")
    return q


sill = smooth(curve("sill", "sill_b"))
door_bot = smooth(curve("door_bottom", "door_bottom_b"))
door_bot = door_bot[door_bot[:, 1] < 0.36]      # drop the ends, where the trace climbs the arches

# ---- the wheel-arch lips, as the panels' end stops ---------------------------------------------
ARCH_F = np.array(PF["arch_shapes"]["front"], float); ARCH_F[:, 1] += DZ
ARCH_R = np.array(PF["arch_shapes"]["rear"], float); ARCH_R[:, 1] += DZ
# the front arch's REAR side is the tail of its outline, the rear arch's FRONT side is the head of its
f_rear = ARCH_F[ARCH_F[:, 0] > -1.0]            # y -0.841 .. -0.876, z low -> up
r_front = ARCH_R[ARCH_R[:, 0] < 1.0]            # y +0.814 .. +0.987


def lip_front_y(z):
    c = f_rear[np.argsort(f_rear[:, 1])]
    return float(np.interp(z, c[:, 1], c[:, 0]))


def lip_rear_y(z):
    """Where the rear arch lip stands at this height - the skirt's and the rocker's rear end stop."""
    c = r_front[np.argsort(r_front[:, 1])]
    return float(np.interp(z, c[:, 1], c[:, 0]))


def lip_rear_z(y):
    """Height of the rear arch lip at this station; below its leading corner there is no lip."""
    c = r_front[np.argsort(r_front[:, 0])]
    return float(np.interp(y, c[:, 0], c[:, 1]))


Y_LIP_F = float(f_rear[:, 0].max())             # -0.841, the straight part of the front arch's rear edge
Y_LIP_R = float(r_front[:, 0].min())            # +0.814
print("arch lips: front rear edge y %+.4f, rear front edge y %+.4f (model frame)" % (Y_LIP_F, Y_LIP_R))

# ---- the skirt's traced top edge ---------------------------------------------------------------
top = np.array(SK["skirt_top"], float)
top = top[np.argsort(top[:, 0])]
knee_y, knee_z = SK["knee"]
# the kick-up runs into the rear arch lip; cut it where the two meet
keep = [True] * len(top)
for i, (y, z) in enumerate(top):
    if y > knee_y and y >= Y_LIP_R and z >= lip_rear_z(y) - GAP:
        keep[i] = False
top = top[np.array(keep)]
print("skirt top edge: %d points, y %+.3f .. %+.3f, z %.3f .. %.3f (knee at y %+.3f)"
      % (len(top), top[0, 0], top[-1, 0], top[:, 1].min(), top[:, 1].max(), knee_y))


def z_sill(y):
    return float(np.interp(y, sill[:, 0], sill[:, 1]))


def z_door(y):
    return float(np.interp(y, door_bot[:, 0], door_bot[:, 1]))


CREST_Y, CREST_Z = float(top[-1, 0]), float(top[-1, 1])


def z_skirt_top(y):
    """The traced top edge: flat, then the kick-up. Past the kick-up's crest it runs level to the arch,
    which is the short near-horizontal piece the picture shows between the crest and the lip."""
    return CREST_Z if y >= CREST_Y else float(np.interp(y, top[:, 0], top[:, 1]))


def grid(name, rows_at, y_span, nrow, ny, mat, flip=False, cap=False):
    """One quad grid. rows_at(j, y) gives the (x, z) of section row j at station y; y_span(j) gives that
    row's own y range, so the two ends can follow the wheel-arch lips instead of being cut straight."""
    spans = [y_span(j) for j in range(nrow)]
    bm = bmesh.new()
    V = []
    for i in range(ny):
        u = i / (ny - 1.0)
        col = []
        for j in range(nrow):
            y0_, y1_ = spans[j]
            y = y0_ + u * (y1_ - y0_)
            x, z = rows_at(j, y)
            col.append(bm.verts.new((x, y, z)))
        V.append(col)
    for i in range(ny - 1):
        for j in range(nrow - 1):
            a, b, c, d = V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]
            if (a.co - b.co).length < 1e-6 and (d.co - c.co).length < 1e-6:
                continue
            bm.faces.new((a, b, c, d))
    if cap:                                     # close the two cut ends, so no open edge shows
        for col in (V[0], V[-1]):
            try:
                bm.faces.new(col)
            except ValueError:
                pass
    bm.faces.ensure_lookup_table(); bm.normal_update()
    if (sum(f.normal.x for f in bm.faces) < 0) != flip:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.normal_update()
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh); bm.free()
    if hasattr(mesh, "shade_smooth"):
        mesh.shade_smooth()
    for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):
        _f = getattr(mesh, _n, None)
        if _f:
            _f(angle=math.radians(35))
            break
    m = bpy.data.materials.get(mat)
    if m:
        mesh.materials.append(m)
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    mir = ob.modifiers.new("Mirror", "MIRROR")
    mir.use_axis[0] = True
    mir.use_clip = False
    print("%-14s %4d verts, %4d faces, mirrored" % (name, len(mesh.vertices), len(mesh.polygons)))
    return ob


_home = bpy.data.objects.get("Skirt_Left") or bpy.data.objects.get(CUT.split(",")[0])
coll = _home.users_collection[0] if _home else (bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection)
for stale in ("Side_Skirt_Left", "Side_Skirt_Right"):
    o = bpy.data.objects.get(stale)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)
        print("removed the old %s" % stale)

# ---- the rocker ---------------------------------------------------------------------------------
# From the sill line up to the door's lower edge, on the flank's own surface, then a return inboard at
# the bottom so the panel is not a paper edge where the floor would be.
NZ = 9
ROCK_N = NZ + 2


def rocker_rows(j, y):
    zb, zt = z_sill(y), z_door(y)
    if j == 0:
        return (skin_x(y, zb) - 0.035, zb - 0.012)
    if j == 1:
        return (skin_x(y, zb) - 0.004, zb - 0.003)
    z = zb + (zt - zb) * (j - 2) / (NZ - 1.0)
    return (skin_x(y, z), z)


def rocker_span(j):
    return (Y_LIP_F + GAP, Y_LIP_R - GAP)


rocker = grid("Rocker_Left", rocker_rows, rocker_span, ROCK_N, NY, "paint_gunmetal")
print("   rocker z %.3f..%.3f at mid, %.0f mm tall" % (z_sill(0.0), z_door(0.0), (z_door(0.0) - z_sill(0.0)) * 1000))

# ---- the skirt ------------------------------------------------------------------------------------
# Section, from the top edge down: the moulding tucks into the body at the top, rolls over a small lip
# onto its face, and wraps under at the bottom. The lip radii are fixed millimetres, not a fraction of
# the height, because the moulding keeps its section while the band it fills narrows to nothing at the
# rear arch - so the rows are clamped to stay in order where it gets thin.
# (d factor on PROUD, dz) - from the top edge for the upper rows, from the bottom edge for the lower
SKIRT_SEC = [(-0.002 / 0.012, +0.003, "t"), (0.42, -0.002, "t"), (0.75, -0.006, "t"), (0.96, -0.011, "t"),
             (1.00, -0.020, "t"), (1.00, +0.020, "b"),
             (0.88, +0.008, "b"), (0.58, +0.003, "b"), (0.08, 0.000, "b"), (-2.5, -0.004, "b")]
SKIRT_N = len(SKIRT_SEC)


def skirt_z(j, y):
    """Height of section row j at this station, clamped so the rows stay in order where the band is thin."""
    zt, zb = z_skirt_top(y), z_sill(y)
    z = None
    for k in range(j + 1):
        f, dz, ref = SKIRT_SEC[k]
        zk = (zt + dz) if ref == "t" else (zb + dz)
        if ref == "t":
            zk = max(zk, zb + 0.002)
        else:
            zk = min(zk, zt - 0.002)
        z = zk if z is None else min(z, zk)
    return z


def skirt_rows(j, y):
    z = skirt_z(j, y)
    zt, zb = z_skirt_top(y), z_sill(y)
    return (skin_x(y, min(max(z, zb), zt)) + SKIRT_SEC[j][0] * PROUD, z)


def skirt_span(j):
    """This row's own ends: the two arch lips at the row's own height, found by a couple of iterations
    because the height itself depends on where along the car the row is."""
    y0_, y1_ = Y_LIP_F + GAP, CREST_Y
    for _ in range(12):
        y0_ = lip_front_y(skirt_z(j, y0_)) + GAP
        y1_ = lip_rear_y(skirt_z(j, y1_)) - GAP
    return (y0_, y1_)


skirt = grid("Skirt_Left", skirt_rows, skirt_span, SKIRT_N, NY, "paint_gunmetal", cap=True)
s0, s1 = skirt_span(SKIRT_N // 2)
print("   skirt y %+.3f..%+.3f at the face, top z %.3f at mid, crest %.3f at y %+.3f, %.0f mm proud"
      % (s0, s1, z_skirt_top(0.0), CREST_Z, CREST_Y, PROUD * 1000))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
