"""Rebuild the bonnet as a clean quad panel fitted to the Meshy shell, which is used as the ruler.

Two ways round (Nik 2026-10-26 chose the second):
  Meshy shell itself   blender -b blender/nova_meshy.blend --python tools/gen/rebuild_bonnet.py -- \
                         out.blend --ref Meshy_Body --panel BONNET --cut Meshy_Body --uv
  Blocky model         blender -b blender/nova_proc.blend  --python tools/gen/rebuild_bonnet.py -- \
                         out.blend --ref MESHY_REF --panel Hood_Panel --cut Hood --symmetric


Outline traced on the shell itself (ortho top renders at 1 mm/px, base colour + height map):
  - side shut lines: dead straight at x = +-0.597 (dark line in the texture, y -0.85..-1.65, scatter +-3 mm)
  - rear edge (scuttle): y = -0.700 (height-map curvature minimum; left reads -0.72, right -0.66, the centre is
    masked by the wiper/washer blob -> one straight line through the mean)
  - front edge: the nose fold, found here by marching the raycast height forward until the slope passes
    FOLD_SLOPE, then a symmetric quadratic through those points (the fold bows ~70 mm forward at the centre).

The panel is an even quad grid inside that outline. Each node's height comes from raycasting the shell
(3x3 supersampled, median), then a Laplacian-regularised fit (implicit smoothing, LAM) keeps the overall
shape and drops the lumps. The four boundary rings are faired along the ring only and then pinned, so the
panel still meets the wings and scuttle at the shell's own height. UVs are sampled off the shell
(barycentric on the hit triangle), so the Meshy texture carries over unchanged. A short lip is extruded
down from the panel edge; the body gets the matching opening, bisected on the traced line with a 4 mm shut
gap and an inward jamb.

blender -b blender/nova_meshy.blend --python tools/gen/rebuild_bonnet.py -- out.blend
"""
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


REF = opt("--ref", "Meshy_Body")        # surface the panel is fitted to
PANEL = opt("--panel", "BONNET")        # object made
CUT = opt("--cut", REF)                 # object whose bonnet-area faces are removed ("none" to keep)
DO_UV = "--uv" in args                  # carry the reference's UVs onto the panel
SYMM = "--symmetric" in args            # mirror-average the fitted heights

SIDE_X = 0.597          # traced bonnet shut lines
# Rear edge. The dark transverse line I first traced on the shell at about -0.68 is the SCREEN BASE (the glass
# edge), not the bonnet's rear edge - the bonnet stops well in front of it, with the scuttle panel and the wiper
# spindles between. The project measured all three on one plan curve (tools/photomatch/body_profile.json
# "scuttle_curve", from the c20 + cCF triangulated wiper pivot, washer jets and louvre row; ESTIMATE +-1.5 cm):
REAR_Y0, REAR_K = -0.900, 0.33          # bonnet rear edge  y = REAR_Y0 + REAR_K x^2
SB_Y0, SB_K, SB_MAX = -0.740, 0.29, -0.702      # screen base  y = min(SB_Y0 + SB_K x^2, SB_MAX)


def screen_base_y(x):
    return min(SB_Y0 + SB_K * x * x, SB_MAX)


def rear_y(x):
    return min(REAR_Y0 + REAR_K * x * x, screen_base_y(x) - 0.05)
FOLD_SLOPE = 0.55       # dz/dy at which the nose turns down (kept for --fold, the ruler's own fold)
# Measured front edge (2026-10-26): the Meshy shell's nose is the weakest part of the generated mesh - its fold
# sits ~60 mm low and ~80 mm short of where the photos put the bonnet's leading edge. The project already has that
# edge triangulated from the matched cameras (docs/DECISIONS.md 2026-10-12 late, tools/front_end.py): a straight V
# in plan, y = EDGE_Y0 + EDGE_A*|x|, level at z = EDGE_Z, both photos agreeing within 4 mm. Photo frame, so DZ is
# added to put it on the model's unloaded tyres. Pass --fold to go back to the shell's own fold.
EDGE_Y0, EDGE_A, EDGE_Z = -1.755, 0.151, 0.722
DZ = 0.0193             # photo frame (loaded tyre contact) -> model frame; tools/photomatch/body_profile.json
EDGE_BLEND = 0.30       # the nose lifts onto the measured edge over this much of the panel's length
GAP = 0.002             # panel edge inboard of the traced line (the body cut is the same amount outboard)
NU, NV = 49, 41         # grid nodes across / along  (~25 mm spacing)
LAM = 30.0              # Laplacian weight in the fit (bigger = smoother)
LIP = 0.018             # panel edge lip, downward
JAMB = 0.045            # body opening return, inward and down
STEP = 0.004            # raycast supersample offset / fold march step


def ray(ob, mwi, x, y):
    """World z of the shell's top surface at (x, y), with the hit face index and local hit point."""
    o = mwi @ Vector((x, y, 2.0))
    d = (mwi.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
    hit, loc, nor, idx = ob.ray_cast(o, d, distance=4.0)
    if not hit:
        return None
    return (ob.matrix_world @ loc).z, idx, loc


def uv_map(me, idx):
    """Affine 3D->UV map of triangle `idx`: uv(p) = uv0 + A @ (p - v0), in the triangle's plane.

    Sampling a UV per grid node straight off its own hit triangle puts the corners of a quad on
    different atlas islands, and the quad then sweeps across the whole texture (dark jigsaw lines).
    One triangle's map applied to all four corners keeps each face inside one island; neighbouring
    faces use neighbouring triangles of the same island, so they agree to well under a texel."""
    p = me.polygons[idx]
    uvs = [me.uv_layers.active.data[l].uv for l in p.loop_indices]
    if len(p.vertices) != 3:
        return None
    v0, v1, v2 = (me.vertices[v].co for v in p.vertices)
    e1, e2 = v1 - v0, v2 - v0
    g = np.array([[e1.dot(e1), e1.dot(e2)], [e1.dot(e2), e2.dot(e2)]])
    if abs(np.linalg.det(g)) < 1e-18:
        return None
    gi = np.linalg.inv(g)
    duv = np.array([[uvs[1].x - uvs[0].x, uvs[2].x - uvs[0].x],
                    [uvs[1].y - uvs[0].y, uvs[2].y - uvs[0].y]])
    E = np.array([list(e1), list(e2)])
    return np.array(v0), np.array([uvs[0].x, uvs[0].y]), duv @ gi @ E


def uv_of(m, p):
    v0, uv0, A = m
    return uv0 + A @ (np.asarray(p) - v0)


def find_fold(body, mwi):
    """March forward at each x; the front edge is where the surface slope first passes FOLD_SLOPE."""
    xs, ys = [], []
    for x in np.linspace(-0.55, 0.55, 23):
        prev = None
        for y in np.arange(-1.50, -1.81, -STEP):
            r = ray(body, mwi, x, y)
            if r is None:
                break
            if prev is not None and (prev - r[0]) / STEP > FOLD_SLOPE:
                xs.append(x)
                ys.append(y)
                break
            prev = r[0]
    xs, ys = np.array(xs), np.array(ys)
    a, b = np.linalg.lstsq(np.stack([np.ones_like(xs), xs ** 2], 1), ys, rcond=None)[0]
    res = ys - (a + b * xs ** 2)
    print("fold fit: y = %.4f %+.4f x^2  (rms %.1f mm, n=%d)" % (a, b, res.std() * 1000, len(xs)))
    return a, b


def fair_ring(z, lam=8.0, iters=400):
    """Implicit smoothing along one boundary ring; the two ends stay put."""
    z0 = z.copy()
    z = z.copy()
    for _ in range(iters):
        nb = 0.5 * (np.roll(z, 1) + np.roll(z, -1))
        nb[0], nb[-1] = z[0], z[-1]
        z = (z0 + lam * nb) / (1.0 + lam)
        z[0], z[-1] = z0[0], z0[-1]
    return z


def fit_surface(z0, pin, iters=800):
    """min ||z - z0||^2 + LAM ||L z||^2, Jacobi; pinned nodes keep their value."""
    z = z0.copy()
    for _ in range(iters):
        nb = np.zeros_like(z)
        cnt = np.zeros_like(z)
        nb[1:, :] += z[:-1, :]; cnt[1:, :] += 1
        nb[:-1, :] += z[1:, :]; cnt[:-1, :] += 1
        nb[:, 1:] += z[:, :-1]; cnt[:, 1:] += 1
        nb[:, :-1] += z[:, 1:]; cnt[:, :-1] += 1
        z = (z0 + LAM * nb / cnt) / (1.0 + LAM)
        z[pin] = z0[pin]
    return z


body = bpy.data.objects[REF]
body.hide_viewport = False                 # a hidden object is not evaluated / raycastable
me = body.data
mwi = body.matrix_world.inverted()
USE_FOLD = "--fold" in args
if USE_FOLD:
    a_f, b_f = find_fold(body, mwi)

    def front_y(x):
        return a_f + b_f * x * x
else:
    print("front edge: measured V  y = %.4f %+.4f |x|, level z %.4f (+DZ %.4f)" % (EDGE_Y0, EDGE_A, EDGE_Z, DZ))

    def front_y(x):
        return EDGE_Y0 + EDGE_A * abs(x)


# ---- grid nodes --------------------------------------------------------------
X = np.linspace(-(SIDE_X - GAP), SIDE_X - GAP, NU)
P = np.zeros((NV, NU, 3))
miss = 0
for j, x in enumerate(X):
    y0, y1 = rear_y(x) - GAP, front_y(x) + GAP
    for i, t in enumerate(np.linspace(0.0, 1.0, NV)):
        y = y0 + t * (y1 - y0)
        zs = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                r = ray(body, mwi, x + dx * STEP, y + dy * STEP)
                if r is not None:
                    zs.append(r[0])
        if not zs:
            miss += 1
            zs = [1.0]
        P[i, j] = (x, y, float(np.median(zs)))
print("grid %dx%d, %d nodes with no hit" % (NV, NU, miss))

# ---- fit ---------------------------------------------------------------------
z0 = P[:, :, 2].copy()
if not USE_FOLD:
    # lift the last stretch onto the measured edge: the ruler reads low there, and a hard pin would step
    t = np.linspace(0.0, 1.0, NV)[:, None]
    w = np.clip((t - (1.0 - EDGE_BLEND)) / EDGE_BLEND, 0.0, 1.0)
    w = w * w * (3.0 - 2.0 * w)                       # smoothstep: convex roll-down, no ridge
    lift = (EDGE_Z + DZ) - z0[-1, :][None, :]
    print("nose lifted onto the measured edge by %.0f..%.0f mm" % (lift.min() * 1000, lift.max() * 1000))
    z0 = z0 + w * lift
z0[0, :] = fair_ring(z0[0, :])
z0[-1, :] = fair_ring(z0[-1, :])
z0[:, 0] = fair_ring(z0[:, 0])
z0[:, -1] = fair_ring(z0[:, -1])
pin = np.zeros(z0.shape, bool)
pin[0, :] = pin[-1, :] = pin[:, 0] = pin[:, -1] = True
z = fit_surface(z0, pin)
d = np.abs(z - P[:, :, 2]) * 1000.0
print("fit moved the surface: mean %.1f mm, max %.1f mm" % (d.mean(), d.max()))
if SYMM:
    z = 0.5 * (z + z[:, ::-1])
    print("heights mirror-averaged (the blocky model is symmetric by construction)")
P[:, :, 2] = z

# ---- panel mesh --------------------------------------------------------------
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
V = [[bm.verts.new(P[i, j]) for j in range(NU)] for i in range(NV)]
nouv = 0
for i in range(NV - 1):
    for j in range(NU - 1):
        corners = ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))
        f = bm.faces.new([V[a][b] for a, b in corners])
        if not DO_UV:
            continue
        c = P[[a for a, b in corners], [b for a, b in corners]].mean(0)
        r = ray(body, mwi, c[0], c[1])
        m = uv_map(me, r[1]) if r is not None else None
        if m is None:
            nouv += 1
            continue
        for loop, (a, b) in zip(f.loops, corners):
            loop[uvl].uv = uv_of(m, mwi @ Vector(P[a, b]))
print("UVs: %d faces without a map" % nouv)
bm.faces.ensure_lookup_table()
bm.normal_update()
if sum(f.normal.z for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
res = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
    v.co.z -= LIP
bm.normal_update()
mesh = bpy.data.meshes.new(PANEL)
bm.to_mesh(mesh)
bm.free()
if DO_UV and me.materials:          # only the Meshy route wants the shell's textured material
    mesh.materials.append(me.materials[0])
if hasattr(mesh, "shade_smooth"):
    mesh.shade_smooth()
else:
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
old = bpy.data.objects.get(PANEL)
if old:
    bpy.data.objects.remove(old, do_unlink=True)
bonnet = bpy.data.objects.new(PANEL, mesh)
coll = bpy.data.objects[CUT].users_collection[0] if CUT != "none" else body.users_collection[0]
coll.objects.link(bonnet)
bonnet.matrix_world = body.matrix_world.copy()
bonnet.data.transform(body.matrix_world.inverted())
print("%s: %d verts, %d faces" % (PANEL, len(mesh.vertices), len(mesh.polygons)))

# ---- matching opening in the body -------------------------------------------
poly = [(float(x), rear_y(x) + GAP) for x in np.linspace(-(SIDE_X + GAP), SIDE_X + GAP, 25)]
poly += [(float(x), front_y(x) - GAP) for x in np.linspace(SIDE_X + GAP, -(SIDE_X + GAP), 25)]


def inside(x, y):
    ins = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (x1 - x0) * (y - y0) / (y1 - y0):
            ins = not ins
    return ins


cut_ob = bpy.data.objects[CUT] if CUT != "none" else None
if cut_ob is not None:
    cme = cut_ob.data
    bm = bmesh.new()
    bm.from_mesh(cme)
    bm.normal_update()
    near = [f for f in bm.faces
            if -1.90 < f.calc_center_median().y < -0.60 and f.calc_center_median().z > 0.60
            and abs(f.calc_center_median().x) < 0.78 and f.normal.z > 0.15]
    geom = set(near) | {e for f in near for e in f.edges} | {v for f in near for v in f.verts}
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        no = Vector((-(y1 - y0), x1 - x0, 0.0)).normalized()
        out = bmesh.ops.bisect_plane(bm, geom=[g for g in geom if g.is_valid],
                                     plane_co=(x0, y0, 0.9), plane_no=no, dist=1e-6)
        geom = {g for g in geom if g.is_valid} | set(out["geom"])
    bm.normal_update()
    kill = [f for f in bm.faces
            if f.normal.z > 0.15 and f.calc_center_median().z > 0.60
            and inside(f.calc_center_median().x, f.calc_center_median().y)]
    print("%s: %d faces removed for the opening" % (CUT, len(kill)))
    bmesh.ops.delete(bm, geom=kill, context="FACES")

    if CUT == REF:                      # the Meshy shell is a closed skin -> return the opening inward
        def emid(e):
            return (e.verts[0].co + e.verts[1].co) * 0.5

        bnd = [e for e in bm.edges if e.is_boundary
               and min(v.co.z for v in e.verts) > 0.55
               and -1.95 < emid(e).y < -0.50 and abs(emid(e).x) < 0.80]
        res = bmesh.ops.extrude_edge_only(bm, edges=bnd)
        cen = Vector((0.0, 0.5 * (rear_y(0.0) + front_y(0.0)), 0.0))
        for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
            dvec = Vector((cen.x - v.co.x, cen.y - v.co.y, 0.0))
            if dvec.length > 1e-9:
                v.co += dvec.normalized() * (JAMB * 0.35)
            v.co.z -= JAMB
    bm.normal_update()
    bm.to_mesh(cme)
    bm.free()
    cme.update()

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
