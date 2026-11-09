"""Scuttle: the body-colour cowl panel between the bonnet's rear edge and the windscreen base, with the
louvre row and the washer jets.

All three lines come from the project's own measurement, not from the shell: tools/photomatch/body_profile.json
"scuttle_curve", triangulated from c20 + cCF (centre wiper pivot 0, -0.800, 0.933 with 2-6 mm ray gaps, washer
jets at +-0.175, -0.811, the louvre row and the screen seal just behind them), ESTIMATE +-1.5 cm:

    bonnet rear edge   y = -0.900 + 0.33 x^2, never closer than 50 mm to the screen base
    screen base        y = min(-0.740 + 0.29 x^2, -0.702)
    louvres            |x| < 0.46, 8..48 mm ahead of the base, 11 mm pitch, 6 mm wide, broken at the pivots

Heights come off the Meshy ruler (it is good here - the scuttle is well covered by the photos Meshy was given),
raycast and then faired the same way as the bonnet. The panel's rear edge is bridged up to whatever the
windscreen object starts at, which is the screen base riser until the glass section is rebuilt.

blender -b blender/nova_proc.blend --python tools/gen/rebuild_scuttle.py -- out.blend [--ref MESHY_REF]
"""
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
REF = args[args.index("--ref") + 1] if "--ref" in args else "MESHY_REF"
SCREEN = args[args.index("--screen") + 1] if "--screen" in args else "Chassis_Front"

SIDE_X, GAP = 0.597, 0.002
REAR_Y0, REAR_K = -0.900, 0.33
SB_Y0, SB_K, SB_MAX = -0.740, 0.29, -0.702
LOUVRE = (0.46, 0.008, 0.048, 0.011, 0.006)     # half-width, near, far, pitch, slot width
JET = (0.175, -0.811, 0.006)                    # washer jets: |x|, y, radius
NX, NY = 49, 13
LAM = 20.0


def screen_base_y(x):
    return min(SB_Y0 + SB_K * x * x, SB_MAX)


def rear_y(x):
    return min(REAR_Y0 + REAR_K * x * x, screen_base_y(x) - 0.05)


def ray(ob, mwi, x, y):
    o = mwi @ Vector((x, y, 2.0))
    d = (mwi.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
    hit, loc, nor, idx = ob.ray_cast(o, d, distance=4.0)
    return (ob.matrix_world @ loc).z if hit else None


def fair_ring(z, lam=2.0, iters=60):
    z0 = z.copy(); z = z.copy()
    for _ in range(iters):
        nb = 0.5 * (np.roll(z, 1) + np.roll(z, -1))
        nb[0], nb[-1] = z[0], z[-1]
        z = (z0 + lam * nb) / (1.0 + lam)
        z[0], z[-1] = z0[0], z0[-1]
    return z


def fit(z0, pin, iters=600):
    z = z0.copy()
    for _ in range(iters):
        nb = np.zeros_like(z); cnt = np.zeros_like(z)
        nb[1:, :] += z[:-1, :]; cnt[1:, :] += 1
        nb[:-1, :] += z[1:, :]; cnt[:-1, :] += 1
        nb[:, 1:] += z[:, :-1]; cnt[:, 1:] += 1
        nb[:, :-1] += z[:, 1:]; cnt[:, :-1] += 1
        z = (z0 + LAM * nb / cnt) / (1.0 + LAM)
        z[pin] = z0[pin]
    return z


ref = bpy.data.objects[REF]
ref.hide_viewport = False
mwi = ref.matrix_world.inverted()

X = np.linspace(-(SIDE_X - GAP), SIDE_X - GAP, NX)
P = np.zeros((NY, NX, 3))
miss = 0
for j, x in enumerate(X):
    y0, y1 = rear_y(x) + GAP, screen_base_y(x)
    for i, t in enumerate(np.linspace(0.0, 1.0, NY)):
        y = y0 + t * (y1 - y0)
        zs = [z for z in (ray(ref, mwi, x + dx * 0.004, y + dy * 0.004)
                          for dx in (-1, 0, 1) for dy in (-1, 0, 1)) if z is not None]
        if not zs:
            miss += 1
            zs = [0.92]
        P[i, j] = (x, y, float(np.median(zs)))
print("scuttle grid %dx%d, %d nodes with no hit; width at the centre %.0f mm"
      % (NY, NX, miss, (screen_base_y(0.0) - rear_y(0.0)) * 1000))

z0 = P[:, :, 2].copy()
z0 = 0.5 * (z0 + z0[:, ::-1])                   # the wiper/washer blob on the shell is not symmetric; the car is
for k in (0, -1):
    z0[k, :] = fair_ring(z0[k, :])
    z0[:, k] = fair_ring(z0[:, k])
pin = np.zeros(z0.shape, bool)
pin[0, :] = pin[-1, :] = pin[:, 0] = pin[:, -1] = True
z = fit(z0, pin)
print("fit moved the surface: mean %.1f mm, max %.1f mm"
      % (np.abs(z - P[:, :, 2]).mean() * 1000, np.abs(z - P[:, :, 2]).max() * 1000))
P[:, :, 2] = z


def surf(x, y):
    """Height on the finished panel, for sitting the louvres and jets on it."""
    j = np.clip(np.searchsorted(X, x) - 1, 0, NX - 2)
    tx = (x - X[j]) / (X[j + 1] - X[j])
    col = P[:, j, 2] * (1 - tx) + P[:, j + 1, 2] * tx
    ys = P[:, j, 1] * (1 - tx) + P[:, j + 1, 1] * tx
    return float(np.interp(y, ys, col))


coll = bpy.data.objects["Hood_Panel"].users_collection[0]
for name in ("Scuttle_Panel", "Scuttle_Vent"):
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

bm = bmesh.new()
V = [[bm.verts.new(P[i, j]) for j in range(NX)] for i in range(NY)]
for i in range(NY - 1):
    for j in range(NX - 1):
        bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
bm.normal_update()
if sum(f.normal.z for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
# front edge returns downward, so the bonnet's shut line is a dark gap and not a view of the background
res = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary
                                             and max(v.co.y for v in e.verts) < rear_y(0.0) + 0.05])
for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
    v.co.z -= 0.040

# bridge the rear edge up to the windscreen object's lowest row (the screen base riser)
screen = bpy.data.objects.get(SCREEN)
if screen is not None:
    sz = min(v.co.z for v in screen.data.vertices)
    sy = np.median([v.co.y for v in screen.data.vertices if v.co.z < sz + 0.01])
    print("%s starts at y %.3f z %.3f; bridging the scuttle's rear edge up to it" % (SCREEN, sy, sz))
    top = [bm.verts.new((P[-1, j, 0], float(sy), float(sz))) for j in range(NX)]
    for j in range(NX - 1):
        bm.faces.new((V[-1][j], top[j], top[j + 1], V[-1][j + 1]))
    bm.normal_update()

mesh = bpy.data.meshes.new("Scuttle_Panel")
bm.to_mesh(mesh); bm.free()
mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):      # keep the screen-base step crisp
    _f = getattr(mesh, _n, None)
    if _f:
        _f(angle=__import__("math").radians(30))
        break
paint = bpy.data.materials.get("paint_gunmetal")
if paint:
    mesh.materials.append(paint)
ob = bpy.data.objects.new("Scuttle_Panel", mesh)
coll.objects.link(ob)
print("Scuttle_Panel: %d verts, %d faces" % (len(mesh.vertices), len(mesh.polygons)))

# ---- louvres + washer jets ---------------------------------------------------
xl, d0, d1, pitch, wsl = LOUVRE
bm = bmesh.new()
n = int(xl / pitch)
for i in range(-n, n + 1):
    x = i * pitch
    if abs(x) < 0.03 or abs(abs(x) - 0.44) < 0.03:      # broken at the wiper pivots
        continue
    yb = screen_base_y(x)
    quad = []
    for dd, ss in ((-d1, -wsl / 2), (-d1, wsl / 2), (-d0, wsl / 2), (-d0, -wsl / 2)):
        qx, qy = x + ss, yb + dd
        quad.append(bm.verts.new((qx, qy, surf(qx, qy) + 0.0008)))
    bm.faces.new(quad)
for s in (1, -1):
    jx, jy, jr = s * JET[0], JET[1], JET[2]
    bmesh.ops.create_circle(bm, cap_ends=True, radius=jr, segments=12,
                            matrix=__import__("mathutils").Matrix.Translation((jx, jy, surf(jx, jy) + 0.004)))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
mesh = bpy.data.meshes.new("Scuttle_Vent")
bm.to_mesh(mesh); bm.free()
black = bpy.data.materials.get("trim_black")
if black:
    mesh.materials.append(black)
ob = bpy.data.objects.new("Scuttle_Vent", mesh)
coll.objects.link(ob)
print("Scuttle_Vent: %d slots + 2 jets, %d faces" % (len(mesh.polygons) - 2, len(mesh.polygons)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
