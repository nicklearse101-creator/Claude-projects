"""Rebuild a front wing as a clean quad panel fitted to the Meshy shell (the ruler), same idea as
tools/gen/rebuild_bonnet.py but the wing wraps from horizontal to vertical, so it is sampled radially
instead of from above.

For each y station a fan of rays is cast inward at an origin inside the body, giving the body's own
cross-section r(theta). The panel's boundaries are read off that profile, not guessed:
  - top edge: where the surface crosses |x| = SIDE_X + GAP, i.e. just outboard of the bonnet panel's edge,
    so the two make one parallel shut line;
  - bottom edge: the first break going down - a radius jump (the wheel-arch lip, a lamp recess), a missed
    ray, or the skin wrapping under (normal z < -0.4). That one curve is the arch lip where the arch is and
    the valance/sill bottom elsewhere;
  - rear edge: y = DOOR_Y, the door's front shut line as cut in the Meshy shell;
  - front edge: y = front_y(SIDE_X), where the bonnet's nose fold reaches the shut line - forward of that is
    the front panel / headlamp section.

The grid is resampled by arc length between those two edges, the radii are fitted with a Laplacian term
(keeps the section, drops the lumps), boundary rings are faired along the ring and pinned.

blender -b blender/nova_proc.blend --python tools/gen/rebuild_wing.py -- out.blend \
    [--ref MESHY_REF] [--panel Wing_Front] [--cut Fender_Front_Left] [--symmetric] [--diag]
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


REF = opt("--ref", "MESHY_REF")
PANEL = opt("--panel", "Wing_Front")
CUT = opt("--cut", "Fender_Front_Left,Hood")   # comma list: every object whose skin the panels replace
SYMM = "--symmetric" in args
DIAG = "--diag" in args

SIDE_X = 0.597          # bonnet shut line (traced, see rebuild_bonnet.py)
GAP = 0.002
DOOR_Y = -0.700         # door front shut line, as the doors were cut in the Meshy shell
EDGE_Y0, EDGE_A = -1.755, 0.151         # measured bonnet front edge, a straight V in plan (rebuild_bonnet.py)
OZ = 0.55               # fan origin height, inside the body
TH_MAX = 165.0          # degrees from straight up
TH_STEP = 0.2
JUMP = 0.035            # radius drop that counts as an edge (arch lip, lamp recess)
NY, NT = 39, 41         # grid stations along y / points across the panel
KSTEP = 14              # grid row that sits exactly on the flare step line
LAM = 25.0
LIP = 0.018
DZ = 0.0193             # photo frame -> model frame

# The shell is not the ruler for the arch or the width either (Nik 2026-10-26: "the shape looks wrong"):
# measured against the project's own traces it is 15-30 mm narrow per side at the wing and its arch opening is
# ~26 mm tight all round the top, and the fairing had smoothed the GTE's flare step away completely. All three
# come from tools/photomatch/body_profile.json:
#   arch_shapes.front - the arch lip traced on anglia_side (cS, the best-calibrated camera, hubs to 1 px)
#   halfw             - body half-width along y (FIA A-5375: 1522 at the front axle, 1535 max)
#   wing_flare        - the crisp step with the flared panel below it, ~8 mm, headlamp corner to the door
PF = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 "tools", "photomatch", "body_profile.json")))
_arch = np.array(PF["arch_shapes"]["front"], float)
_top = _arch[_arch[:, 1] >= 0.30]
_ay, _az = _top[:, 0], _top[:, 1] + DZ
ARCH_Y0, ARCH_Y1 = float(_ay.min()), float(_ay.max())
_hw = np.array(PF["halfw"], float)
_fl = PF["wing_flare"]
_zstep = np.array(_fl["z_step"], float)
FL_D = _fl["d"]
FL_YS = _fl["front_y"]              # fade in / full / fade out along y
FL_ZLOW = _fl["z_low"]


def arch_z(y):
    """Traced arch lip height at this station (model frame), or None outside the arch."""
    if not (ARCH_Y0 < y < ARCH_Y1):
        return None
    return float(np.interp(y, _ay, _az))


def half_width(y):
    return float(np.interp(y, _hw[:, 0], _hw[:, 1]))


def flare(y, z):
    """Outward offset of the flared lower panel: crisp at the step, faded at both ends and low down."""
    y0, y1, y2, y3 = FL_YS
    fy = np.interp(y, [y0, y1, y2, y3], [0.0, 1.0, 1.0, 0.0]) if y0 <= y <= y3 else 0.0
    zs = float(np.interp(y, _zstep[:, 0], _zstep[:, 1])) + DZ
    if z > zs:
        return 0.0, zs
    fz = np.clip((z - FL_ZLOW[0]) / (FL_ZLOW[1] - FL_ZLOW[0]), 0.0, 1.0)
    return FL_D * fy * fz, zs


def fan(ref, s, y):
    """Cross-section of the shell at this station: hit points and radii for theta = 0..TH_MAX."""
    mwi = ref.matrix_world.inverted()
    O = Vector((0.0, y, OZ))
    th = np.arange(0.0, TH_MAX, TH_STEP)
    pts, rad, nz, face = [], [], [], []
    for t in np.radians(th):
        d = Vector((s * np.sin(t), 0.0, np.cos(t)))
        o = mwi @ (O + d * 2.5)
        dd = (mwi.to_3x3() @ (-d)).normalized()
        hit, loc, nor, idx = ref.ray_cast(o, dd, distance=5.0)
        if not hit:
            pts.append(None); rad.append(np.nan); nz.append(np.nan); face.append(np.nan)
            continue
        w = ref.matrix_world @ loc
        n = (ref.matrix_world.to_3x3() @ nor).normalized()
        pts.append(w)
        rad.append((w - O).length)
        nz.append(n.z)
        face.append(n.dot(d))        # > 0 = the skin faces the ray, < 0 = we are inside an opening
    return th, pts, np.array(rad), np.array(nz), np.array(face)


def edges_of(th, pts, rad, nz, face, s):
    """Index of the top edge (|x| crosses SIDE_X + GAP) and of the first break below it.

    A ray that passes through the wheel arch usually hits the inner wing or the tyre and comes back with a
    perfectly plausible radius, so a radius drop alone misses the arch lip. The reliable test is the hit
    normal: on the outer skin it faces the ray, inside an opening it does not."""
    top = None
    for i, p in enumerate(pts):
        if p is not None and s * p.x >= SIDE_X + GAP:
            top = i
            break
    if top is None:
        return None, None
    bot = len(th) - 1
    for i in range(top + 1, len(th)):
        if pts[i] is None or np.isnan(rad[i]) or face[i] < 0.15:
            bot = i - 1
            break
        if abs(rad[i] - rad[i - 1]) > JUMP:     # step: arch lip, lamp recess, bumper shut
            bot = i - 1
            break
        if nz[i] < -0.4 and pts[i].z < 0.35:    # skin wrapping under the sill / valance
            bot = i
            break
    return top, bot


def resample(th, pts, i0, i1, n):
    """n points evenly spaced by arc length between profile samples i0..i1."""
    P = np.array([list(pts[i]) for i in range(i0, i1 + 1)])
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if d[-1] < 1e-6:
        return None
    want = np.linspace(0.0, d[-1], n)
    t = np.interp(want, d, np.arange(i0, i1 + 1))
    return t


def fair_ring(z, lam=1.0, iters=30):
    """Mild: the wing's lower edge has real corners where the arch lip meets the valance, and a strong
    ring fairing cuts them off by over 100 mm."""
    z0 = z.copy(); z = z.copy()
    for _ in range(iters):
        nb = 0.5 * (np.roll(z, 1) + np.roll(z, -1))
        nb[0], nb[-1] = z[0], z[-1]
        z = (z0 + lam * nb) / (1.0 + lam)
        z[0], z[-1] = z0[0], z0[-1]
    return z


def fit(r0, pin, iters=800):
    r = r0.copy()
    for _ in range(iters):
        nb = np.zeros_like(r); cnt = np.zeros_like(r)
        nb[1:, :] += r[:-1, :]; cnt[1:, :] += 1
        nb[:-1, :] += r[1:, :]; cnt[:-1, :] += 1
        nb[:, 1:] += r[:, :-1]; cnt[:, 1:] += 1
        nb[:, :-1] += r[:, 1:]; cnt[:, :-1] += 1
        r = (r0 + LAM * nb / cnt) / (1.0 + LAM)
        r[pin] = r0[pin]
    return r


ref = bpy.data.objects[REF]
ref.hide_viewport = False
FRONT_Y = EDGE_Y0 + EDGE_A * SIDE_X     # where the bonnet edge meets the shut line
ys = np.linspace(DOOR_Y, FRONT_Y, NY)
print("wing stations y %.3f .. %.3f" % (ys[0], ys[-1]))

grids = {}
for s in (1, -1):
    TH = np.zeros((NY, NT)); R = np.zeros((NY, NT))
    steps = np.zeros(NY, bool)
    prof, tops, bots = [], [], []
    for y in ys:
        th, pts, rad, nz, face = fan(ref, s, float(y))
        i0, i1 = edges_of(th, pts, rad, nz, face, s)
        if i0 is None:
            raise RuntimeError("no top edge at y %.3f" % y)
        # Inside the arch the lip is the traced line, not a break; at the arch's two ends blend over 70 mm
        # into the detected break (valance ahead, sill behind), or the boundary notches and spikes there.
        za = arch_z(float(y))
        if za is None:
            d0 = min(abs(float(y) - ARCH_Y0), abs(float(y) - ARCH_Y1))
            if d0 < 0.07:
                za = arch_z(ARCH_Y0 + 1e-4 if abs(float(y) - ARCH_Y0) < abs(float(y) - ARCH_Y1)
                            else ARCH_Y1 - 1e-4)
                zd = pts[i1].z if pts[i1] is not None else za
                w = 1.0 - d0 / 0.07
                za = w * za + (1.0 - w) * zd
        if za is not None:
            below = [k for k in range(i0 + 1, len(pts)) if pts[k] is not None and pts[k].z < za]
            if below:
                i1 = below[0] - 1
        prof.append((th, pts, rad))
        tops.append(i0); bots.append(i1)
    # a single station that reads past the arch lip spikes the panel: median-filter the lower edge
    b = np.array(bots, float)
    bm_ = b.copy()
    for i in range(len(b)):
        med = np.median(b[max(0, i - 2):i + 3])
        if abs(b[i] - med) > 8.0 / TH_STEP:     # outlier only; a real corner at the arch ends is kept
            bm_[i] = med
    for i, (th, pts, rad) in enumerate(prof):
        i0, i1 = tops[i], int(round(min(bm_[i], len(th) - 1)))
        i1 = max(i1, i0 + 2)
        # split the profile at the flare step so row KSTEP lands on it at EVERY station - snapping the
        # nearest row per station instead makes the step jump between rows and zig-zag along the wing
        zs = flare(float(ys[i]), 0.0)[1]
        cand = [k for k in range(i0 + 2, i1 - 1) if pts[k] is not None and pts[k].z <= zs]
        istep = cand[0] if cand else None
        if istep is not None and istep - i0 >= 2 and i1 - istep >= 2:
            ta = resample(th, pts, i0, istep, KSTEP + 1)
            tb = resample(th, pts, istep, i1, NT - KSTEP)
            t = np.r_[ta, tb[1:]] if ta is not None and tb is not None else resample(th, pts, i0, i1, NT)
            steps[i] = True
        else:
            t = resample(th, pts, i0, i1, NT)
        TH[i] = np.interp(t, np.arange(len(th)), th)
        R[i] = np.interp(t, np.arange(len(rad)), rad)
        if DIAG and i % 6 == 0:
            print("  y %6.3f  top th %5.1f z %.3f  bottom th %5.1f z %.3f%s" % (
                ys[i], th[i0], pts[i0].z, th[i1], pts[i1].z,
                "   (raw %5.1f)" % th[bots[i]] if bots[i] != i1 else ""))
    grids[s] = (TH, R, steps)

if SYMM:
    TH = 0.5 * (grids[1][0] + grids[-1][0])
    R = 0.5 * (grids[1][1] + grids[-1][1])
    st = grids[1][2] & grids[-1][2]
    grids[1] = grids[-1] = (TH, R, st)
    print("profiles mirror-averaged (the blocky model is symmetric by construction)")

objs = []
for s in (1, -1):
    TH, R, steps = grids[s]
    r0 = R.copy()
    r0[0, :] = fair_ring(r0[0, :]); r0[-1, :] = fair_ring(r0[-1, :])
    r0[:, 0] = fair_ring(r0[:, 0]); r0[:, -1] = fair_ring(r0[:, -1])
    pin = np.zeros(r0.shape, bool)
    pin[0, :] = pin[-1, :] = pin[:, 0] = pin[:, -1] = True
    r = fit(r0, pin)
    print("side %+d: fit moved the surface mean %.1f mm, max %.1f mm" % (
        s, np.abs(r - R).mean() * 1000, np.abs(r - R).max() * 1000))

    P = np.zeros((NY, NT, 3))
    for i in range(NY):
        for j in range(NT):
            t = np.radians(TH[i, j])
            P[i, j] = (s * np.sin(t) * r[i, j], ys[i], OZ + np.cos(t) * r[i, j])

    # --- widen each station onto the measured half-width (the shell is 15-30 mm narrow per side here).
    # The correction is zero at the top edge, where the bonnet shut line is traced and right, and full from
    # the widest row down, so the panel still meets the bonnet panel exactly.
    wid = []
    for i in range(NY):
        jmax = int(np.argmax(np.abs(P[i, :, 0])))
        # the wing genuinely tapers in towards the indicator, so only widen behind where front_taper says
        # full width is reached (~y -1.50); ahead of that the taper is the real shape
        fy = float(np.clip((ys[i] - (-1.60)) / 0.15, 0.0, 1.0))
        d = (half_width(float(ys[i])) - abs(P[i, jmax, 0])) * fy
        wid.append(d)
        ramp = np.clip(np.arange(NT) / max(jmax, 1), 0.0, 1.0)
        ramp = ramp * ramp * (3.0 - 2.0 * ramp)
        for j in range(NT):
            t = np.radians(TH[i, j])
            P[i, j, 0] += s * np.sin(t) * d * ramp[j]
            P[i, j, 2] += np.cos(t) * d * ramp[j]
    print("side %+d: widened onto the measured half-width by %.0f..%.0f mm"
          % (s, min(wid) * 1000, max(wid) * 1000))

    # --- the GTE flare: rows below KSTEP stand proud of the step, the riser is the KSTEP->KSTEP+1 gap
    n_step = 0
    for i in range(NY):
        if not steps[i]:
            continue
        n_step += 1
        zs = flare(float(ys[i]), 0.0)[1]
        t = np.radians(TH[i, KSTEP + 1])
        P[i, KSTEP + 1, 2] = zs - 0.0015                 # keep the riser crisp, not smeared over the pitch
        for j in range(KSTEP + 1, NT):
            d, _ = flare(float(ys[i]), float(P[i, j, 2]))
            t = np.radians(TH[i, j])
            P[i, j, 0] += s * np.sin(t) * d
            P[i, j, 2] += np.cos(t) * d
    print("side %+d: flare step on %d of %d stations" % (s, n_step, NY))

    bm = bmesh.new()
    V = [[bm.verts.new(P[i, j]) for j in range(NT)] for i in range(NY)]
    for i in range(NY - 1):
        for j in range(NT - 1):
            bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
    bm.faces.ensure_lookup_table(); bm.normal_update()
    if sum(f.normal.x for f in bm.faces) * s < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    res = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
    O = Vector((0.0, 0.0, OZ))
    for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
        d = Vector((v.co.x, 0.0, v.co.z - OZ))
        if d.length > 1e-9:
            v.co -= d.normalized() * LIP
    bm.normal_update()
    name = "%s_%s" % (PANEL, "Left" if s > 0 else "Right")
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh); bm.free()
    if hasattr(mesh, "shade_smooth"):
        mesh.shade_smooth()
    for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):       # keep the flare step crisp
        _f = getattr(mesh, _n, None)
        if _f:
            _f(angle=math.radians(35))
            break
    ob = bpy.data.objects.new(name, mesh)
    bpy.data.objects[CUT.split(",")[0]].users_collection[0].objects.link(ob)
    objs.append(ob)
    print("%s: %d verts, %d faces" % (name, len(mesh.vertices), len(mesh.polygons)))
    grids[s] = (TH, r, steps)

# ---- remove the skin the new panels replace -----------------------------------
cut_obs = [bpy.data.objects[n] for n in CUT.split(",") if n != "none" and n in bpy.data.objects]
if cut_obs:
    from mathutils.bvhtree import BVHTree
    tris, verts = [], []
    for ob in objs:                             # one BVH over both new panels
        n0 = len(verts)
        verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
        for f in ob.data.polygons:
            vs = list(f.vertices)
            for k in range(1, len(vs) - 1):
                tris.append((n0 + vs[0], n0 + vs[k], n0 + vs[k + 1]))
    bvh = BVHTree.FromPolygons(verts, tris)
    NEAR = 0.08                                 # the skin the panels now carry
    for cut_ob in cut_obs:
        bm = bmesh.new(); bm.from_mesh(cut_ob.data); bm.normal_update()
        kill = []
        for f in bm.faces:
            c = cut_ob.matrix_world @ f.calc_center_median()
            if not (FRONT_Y - 0.01 < c.y < DOOR_Y + 0.01) or abs(c.x) < 0.25:
                continue
            if bvh.find_nearest(c, NEAR)[0] is not None:
                kill.append(f)
        print("%s: %d faces removed" % (cut_ob.name, len(kill)))
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        bm.to_mesh(cut_ob.data); bm.free(); cut_ob.data.update()

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
