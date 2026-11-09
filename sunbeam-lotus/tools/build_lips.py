"""All the rally Sunbeam's body-colour trim as ONE mesh per side (runs in Blender; called from
build_rally_parts.build()):

    front splitter lip -> loft -> front flare -> sill lip -> rear flare -> loft -> rear splitter lip

Nick (2026-09-28): the front splitter looked detached (raise it; join it to the bottom front of the arches as one
piece); widen the rear to the car's width joining the rear arches; then "the splitter to arch join looks messy, it
should look smooth in line with the arch trim" - a lip run up under a tapered flare end left a visible overlap. Now
every part shares one 12-point cross-section layout, [attached edge on the body ... free edge, return underneath],
so the pieces are consecutive rings of a single surface: no seams, no overlaps, continuous shading.

  lips   - traced from the stock carPaint panels' lowest edge (left half): front - the valance's bottom edge across
           the nose to where it starts to climb the corner (x 0.64); rear - the rear valance's bottom edge across the
           tail to its corner, then forward along the bottom of the quarter panel to y 1.66. At each point the lip
           grows from 10 mm up the panel, keeps the panel's slope and curves out along the (smoothed, levelled)
           body normal while dropping; a black blade runs under the straight part.
  flares - build_rally_parts.flare_rings(): flare + sill + flare, cut at JOIN_TRIM up each arch end
  lofts  - between a lip's end section and the flare's end section: each section point follows a Hermite curve
           leaving along the lip and arriving along the flare; every intermediate section is shifted so its
           attached edge sits on the bodywork
The rear lip is notched round the (enlarged) exhaust on the left, so the two sides are built separately.
"""
import importlib.util
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TOOLS = r"D:\Claude\talbot_sunbeam_lotus\tools"
FRONT = {"drop": 0.030, "reach": 0.070, "blade_proud": 0.035, "blade_under": 0.16, "blade_x": 0.70, "x_end": 0.64,
         "nose": 0.016, "sigma": 3.0}
REAR = {"drop": 0.050, "reach": 0.030, "blade_proud": 0.030, "blade_under": 0.22, "blade_x": 0.55,
        "strakes": (0.10, 0.28, 0.44), "y_end": 1.70, "nose": 0.014, "sigma": 8.0}
# Nik 2026-10-06: the splitters "look a bit 2D - should really follow the lines of the arches better", the rear one
# "looks a bit rushed, could do with blending to the arches better and smoothing out". The lip section had a knife
# edge (out to a point, straight back underneath): now a moulding with a rounded nose `nose` thick, like the flares'
# rolled edge; the rear trace is smoothed harder (`sigma`, the valance/quarter-panel edge is wavy) and the whole rear
# run smoothed as one; corner lofts longer and softer; blades get a rounded leading edge and ends that taper away.
LOFT_TANGENT = 1.35      # loft tangent length x section distance (1.1 made a tight turn up into the flare)
BLADE_TAPER = 0.12       # blade narrows to nothing over this much of its end (was 6 cm to 35 %)
LIP_END_K = 0.85         # lip size eases to this over its last 8 cm, where the loft takes over
LOFT_STEPS = 26
STEP = 0.010
N_ATTACH = 11            # section points from the attached edge to the free edge; +1 return underneath = 12
# the left rear valance has a notch (x 0.39-0.54, up to z 0.21) the twin exhaust tips come out of; the lip runs on
# under them (it used to stop either side - "just a gap under the exhaust", Nick), its top edge lowered across the
# notch to just under the tips (stock bottoms z 0.161): (x0, x1, ramp width, top z)
EXHAUST_ZONE = (0.395, 0.535, 0.045, 0.157)    # ramp 2 -> 4.5 cm (v-shaped dip)
# every lip/loft section's attached edge is pinned onto the bodywork (it sat 3-9 mm off it - a visible gap in the
# front corners, Nick): moved to SNAP_IN inside the surface, the next points following by SNAP_W
SNAP_MAX, SNAP_IN = 0.015, 0.0005
SNAP_RIGID = 0.035
# the rear join is smoothed along the trim from this many sections before the loft (the rear arch's sweep) to this
# many into the lip - the sweep, loft and quarter-panel lip built separately left a hump (Nick: "messy")
REAR_JOIN_BACK, REAR_JOIN_ON = 30, 400    # ON: the whole rear lip (was 25)
REAR_JOIN_SIGMA, REAR_JOIN_PASSES = 6.0, 6
SNAP_W = (1.0, 0.75, 0.45, 0.2, 0.08)


def load(name):
    spec = importlib.util.spec_from_file_location(name, rf"{TOOLS}\{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def paint_points(brp):
    P = []
    for o in bpy.data.collections["STOCK_MODEL"].objects:
        if (o.type == "MESH" and o.get("kn5_class") == 2 and not o.get("no_export") and o.data.materials
                and o.data.materials[0].name == "carPaint" and not o.name.startswith("RALLY_")):
            P.append(brp.world_pts(o))
    return np.concatenate(P)


def paint_bvh():
    verts, polys = [], []
    for o in bpy.data.collections["STOCK_MODEL"].objects:
        if (o.type == "MESH" and o.get("kn5_class") == 2 and not o.get("no_export") and o.data.materials
                and o.data.materials[0].name in ("carPaint", "carPaint_2") and not o.name.startswith("RALLY_")):
            mw = o.matrix_world
            base = len(verts)
            verts += [tuple(mw @ v.co) for v in o.data.vertices]
            polys += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def edge_bin(P, sel, pick_axis, pick_max):
    """Lowest points of a bin of panel points -> the edge point (extreme along pick_axis)."""
    b = P[sel]
    if len(b) == 0:
        return None
    zmin = b[:, 2].min()
    e = b[b[:, 2] < zmin + 0.008]
    i = e[:, pick_axis].argmax() if pick_max else e[:, pick_axis].argmin()
    return e[i]


def smooth_path(pts, sigma=3.0, keep_ends=True):
    a = np.array(pts, float)
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    pad = np.concatenate([np.repeat(a[:1], r, 0), a, np.repeat(a[-1:], r, 0)])
    s = np.stack([np.convolve(pad[:, j], k, mode="valid") for j in range(a.shape[1])], axis=1)
    if keep_ends:
        s[0], s[-1] = a[0], a[-1]
    return s


def smooth_path_sym(pts, sigma):
    """smooth_path for a path starting on the centre line (x = 0): padded with its own mirror image there, so the
    centre is smoothed like everywhere else (pinning it left a small point where the two halves meet); the far end
    stays pinned (it meets the arch)."""
    a = np.array(pts, float)
    r = int(3 * sigma)
    m = a[1:r + 1][::-1] * np.array([-1.0, 1.0, 1.0])
    s = smooth_path(np.concatenate([m, a]), sigma=sigma, keep_ends=False)[len(m):]
    s[-1] = a[-1]
    s[0, 0] = 0.0
    return s


def resample(a, step=STEP):
    seg = np.linalg.norm(np.diff(a, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.arange(0.0, s[-1] + 1e-9, step)
    if t[-1] < s[-1] - 1e-4:
        t = np.append(t, s[-1])
    return np.stack([np.interp(t, s, a[:, j]) for j in range(3)], axis=1), t


def resample_polyline(pts, n):
    a = np.array([tuple(p) for p in pts], float)
    seg = np.linalg.norm(np.diff(a, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.linspace(0.0, s[-1], n)
    return [Vector([float(np.interp(ti, s, a[:, j])) for j in range(3)]) for ti in t]


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


# ---------------------------------------------------------------- lips

def front_path(brp):
    fit = brp.valance_edge(-1, FRONT["x_end"])                # x, y_edge, z_edge, y_up, z_up
    return [(float(r[0]), float(r[1]), float(r[2])) for r in fit]


def exhaust_w(x):
    """1 across the exhaust notch, easing to 0 over the ramp either side (left side, x > 0)."""
    x0, x1, r, _ = EXHAUST_ZONE
    return min(ease((x - (x0 - r)) / r), ease(((x1 + r) - x) / r))


def rear_path(brp, exhaust=False):
    P = paint_points(brp)
    P = P[(P[:, 1] > 1.40) & (P[:, 2] < 0.45)]
    fit = brp.valance_edge(+1, 0.54)
    pts = [(float(r[0]), float(r[1]), float(r[2])) for r in fit]
    for y in np.arange(1.74, REAR["y_end"] - 1e-6, -0.01):   # forward along the bottom of the quarter panel
        e = edge_bin(P, (np.abs(P[:, 1] - y) < 0.006) & (P[:, 0] > 0.52), 0, True)
        if e is not None:
            pts.append((float(e[0]), float(y), float(e[2])))
    if exhaust:
        z_top = EXHAUST_ZONE[3]
        pts = [(x, y, z + (min(z, z_top) - z) * exhaust_w(x)) for x, y, z in pts]
    return pts


def smooth_window(seq, i0, i1, sigma=3.0, passes=3, ramp=8):
    """Gaussian-smooth corresponding section points along the sequence between i0 and i1 (a join), fading in and
    out over `ramp` sections - irons out humps where a loft meets a lip or flare that were built separately."""
    seq = [list(s) for s in seq]
    i0, i1 = max(0, i0), min(len(seq) - 1, i1)
    r = int(3 * sigma)
    k = [math.exp(-0.5 * (t / sigma) ** 2) for t in range(-r, r + 1)]
    for _ in range(passes):
        new = [list(s) for s in seq]
        for i in range(i0, i1 + 1):
            w = min(ease((i - i0) / ramp), ease((i1 - i) / ramp))
            if w <= 0:
                continue
            for j in range(len(seq[i])):
                acc, tot = Vector(), 0.0
                for t, kt in zip(range(-r, r + 1), k):
                    q = min(max(i + t, 0), len(seq) - 1)
                    acc += seq[q][j] * kt; tot += kt
                new[i][j] = seq[i][j].lerp(acc / tot, w)
        seq = new
    return seq


def snap(sec, bvh, pinned=True):
    """Pin a section's attached edge onto the bodywork (see SNAP_*); pinned=False leaves it."""
    if not pinned:
        return sec
    h = bvh.find_nearest(sec[0])
    if h[0] is None or h[3] > SNAP_RIGID:
        return sec
    n = Vector(h[1]).normalized()
    if n.dot(sec[4] - h[0]) < 0:                     # the body's outward side is where the lip is
        n = -n
    delta = (h[0] - n * SNAP_IN) - sec[0]
    # small gaps: the attached edge is pulled in and the next points follow (SNAP_W); bigger ones (the rear corners
    # sat 16-22 mm off the body - Nik: rear "rushed") move the whole section, blending between the two by distance
    t = ease((h[3] - 0.005) / 0.010)
    return [p + delta * ((SNAP_W[j] if j < len(SNAP_W) else 0.0) * (1 - t) + t) for j, p in enumerate(sec)]


def lip_rows(path, end, drop, reach, bvh, centre_y, zone=None, nose=0.0, sigma=3.0):
    """Lip sections along a path of edge points (from the centre line outwards): rows of 12 points, the lip's
    bottom line [(B, outward n, size k, E)] for the blade, and the resampled path. zone(x) -> 0..1: there the lip
    starts at the edge itself, not 10 mm up the panel (under the exhaust, where there is no panel).
    nose > 0: the free edge is a rounded nose that thick - section = attached point, 6 on the upper face, 3 round
    the nose, the nose's underside, the return under the panel (12, as before, so lofts and flares still match)."""
    a, s = resample(smooth_path_sym(path, sigma) if abs(path[0][0]) < 0.02 else smooth_path(path, sigma=sigma))
    total = s[-1]
    N = []
    for p in a:
        E = Vector(p)
        hit = bvh.find_nearest(E)
        n = Vector((hit[1].x, hit[1].y, 0.0)) if hit[0] is not None else Vector((0, end, 0))
        if n.length < 0.2:
            n = Vector((0, end, 0))
        n.normalize()
        if n.dot(Vector((E.x, E.y - centre_y, 0.0))) < 0:
            n = -n
        N.append(tuple(n))
    N = smooth_path(N, sigma=6.0, keep_ends=False)
    D = []
    for p, n in zip(a, N):
        E, n = Vector(p), Vector(n).normalized()
        hit = bvh.ray_cast(E + n * 0.08 + Vector((0, 0, 0.03)), -n, 0.2)     # the panel 30 mm up: its slope
        U = hit[0] if hit[0] is not None else E + Vector((0, 0, 0.03)) - n * 0.005
        D.append(tuple((E - U).normalized()))
    D = smooth_path(D, sigma=6.0, keep_ends=False)
    rows, bottom = [], []
    for i, p in enumerate(a):
        E, n, d = Vector(p), Vector(N[i]).normalized(), Vector(D[i]).normalized()
        k = 1.0 - (1.0 - LIP_END_K) * ease((s[i] - (total - 0.08)) / 0.08)
        up = 0.010 * (1.0 - (zone(E.x) if zone else 0.0))
        start = E - d * up + n * 0.0015
        B = E + n * (reach * k) + Vector((0, 0, -drop * k))
        C = E + d * (0.35 * drop * k)
        Q = E + n * 0.0015
        ret = E - n * 0.018 + Vector((0, 0, 0.004))
        if nose <= 0:
            curve = [start] + [(1 - q) ** 2 * Q + 2 * (1 - q) * q * C + q * q * B for q in (m / 12 for m in range(13))]
            rows.append(resample_polyline(curve, N_ATTACH) + [ret])
            bottom.append((B, n, k, E))
            continue
        th = nose * k
        tB = (B - C).normalized()                                   # the upper face's direction at the edge
        down = Vector((0, 0, -1))
        m = (down - tB * down.dot(tB)).normalized()                 # into the lip from the upper face
        Bt = B - tB * (th / 2)                                      # nose top
        Cn = Bt + m * (th / 2)                                      # nose centre
        upper = [start] + [(1 - q) ** 2 * Q + 2 * (1 - q) * q * C + q * q * Bt for q in (j / 12 for j in range(13))]
        arc = [Cn + (-m * math.cos(t) + tB * math.sin(t)) * (th / 2) for t in (math.pi / 4, math.pi / 2, 3 * math.pi / 4)]
        Bu = Cn + m * (th / 2)                                      # nose underside
        rows.append(resample_polyline(upper, 7) + arc + [Bu, ret])
        bottom.append((Bu, n, k, E))
    return rows, bottom, a


def flare_section(ring):
    """flare ring [tucked, f0 .. f1] -> [f1 (flush on the body) .. f0 (opening edge), tucked]."""
    return [Vector(p) for p in ring[1:][::-1]] + [Vector(ring[0])]


def loft(sec0, t0, sec1, t1, bvh, steps=LOFT_STEPS):
    """Intermediate sections from sec0 (leaving along t0) to sec1 (arriving along t1); the attached edge (point 0)
    of each is pulled onto the bodywork."""
    c0 = sum(sec0, Vector()) / len(sec0)
    c1 = sum(sec1, Vector()) / len(sec1)
    L = (c1 - c0).length * LOFT_TANGENT
    out = []
    for m in range(1, steps):
        u = m / steps
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        sec = [h00 * a + h10 * L * t0 + h01 * b + h11 * L * t1 for a, b in zip(sec0, sec1)]
        hit = bvh.find_nearest(sec[0])
        if hit[0] is not None:
            w = min(1.0, 4 * u, 4 * (1 - u))
            shift = (hit[0] - sec[0]) * w
            sec = [p + shift for p in sec]
        out.append(sec)
    return out


# ---------------------------------------------------------------- blades

def blade_along(bottom, proud, under, x_max, thick=0.006, strakes=(), tyre_taper=False, bm=None, mirror_x=False):
    """Thin black blade under the lip's bottom line, `proud` out along the lip's normal, `under` back beneath.
    bm: add to this bmesh; mirror_x: the right-hand one."""
    if bm is None:
        bm = bmesh.new()
    sx = -1.0 if mirror_x else 1.0
    new_verts = bm.verts.new
    mv = lambda p: new_verts((sx * p.x, p.y, p.z))
    rows = []
    for B, n, k, E in bottom:
        x = E.x
        if x > x_max or k < 0.95:
            break
        und = under
        if tyre_taper and x > 0.50:                   # front: pull the back edge in ahead of the steered tyres
            und = under * (1.0 - 0.75 * ease((x - 0.50) / 0.20))
        # last BLADE_TAPER: the leading edge sweeps back into the lip and the blade thins - no square end
        e = 0.04 + 0.96 * ease((x_max - x) / BLADE_TAPER)
        p = B + n * proud * e
        q = B - n * und
        th = thick * (0.5 + 0.5 * e)
        dz = Vector((0, 0, th))
        h = Vector((0, 0, th / 2))
        # rounded leading edge: top, two points round the front, bottom (6-point loop with the back edge)
        nose = [p - h + n * (th / 2) * math.cos(t) + Vector((0, 0, th / 2)) * math.sin(t) for t in (math.pi / 3, -math.pi / 3)]
        rows.append([mv(p - dz), mv(nose[1]), mv(nose[0]), mv(p), mv(q), mv(q - dz)])
    m = len(rows[0])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(m):
            bm.faces.new((r0[j], r0[(j + 1) % m], r1[(j + 1) % m], r1[j]))
    bm.faces.new(list(reversed(rows[-1])))
    if strakes:
        # diffuser fins: thin, deepest at the back edge, sweeping up to nothing 2/3 of the way forward
        for x in strakes:
            B0, n0, _, _ = min(bottom, key=lambda b: abs(b[3].x - x))
            y_front, y_back = sorted(((B0 - n0 * under).y, (B0 + n0 * proud).y))
            z_top = B0.z - thick
            # side outline (y, z): starts flush 30 % back, drops to 30 mm just before the back edge
            outline = [(y_front + (y_back - y_front) * 0.30, z_top), (y_back - 0.012, z_top - 0.030),
                       (y_back, z_top - 0.026), (y_back, z_top)]
            vl = [new_verts((sx * (x - 0.003), y, z)) for y, z in outline]
            vr = [new_verts((sx * (x + 0.003), y, z)) for y, z in outline]
            k_ = len(outline)
            bm.faces.new(vl); bm.faces.new(list(reversed(vr)))
            for j in range(k_):
                bm.faces.new((vl[j], vr[j], vr[(j + 1) % k_], vl[(j + 1) % k_]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)       # the two halves meet on the centre line
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# ---------------------------------------------------------------- the whole trim

def build(brp, body, paint_uv):
    paint, black = bpy.data.materials["carPaint"], bpy.data.materials["plastic_textured_002"]
    bvh = paint_bvh()
    univers = brp.kn5("UNIVERS")

    f_rows, f_bottom, f_path = lip_rows(front_path(brp), -1, FRONT["drop"], FRONT["reach"], bvh, -1.0,
                                        nose=FRONT["nose"], sigma=FRONT["sigma"])
    # rear: the left half runs under the exhaust (lowered across the valance notch), the right half is plain
    r_rows, r_bottom, r_path = lip_rows(rear_path(brp), +1, REAR["drop"], REAR["reach"], bvh, 1.0,
                                        nose=REAR["nose"], sigma=REAR["sigma"])
    rx_rows, rx_bottom, _ = lip_rows(rear_path(brp, exhaust=True), +1, REAR["drop"], REAR["reach"], bvh, 1.0,
                                     zone=exhaust_w, nose=REAR["nose"], sigma=REAR["sigma"])
    rings = [flare_section(r) for r in brp.flare_rings(body)]
    edge = lambda sec: sec[N_ATTACH - 1]                       # the free edge point of a section

    t_lip_f = Vector(f_path[-1] - f_path[-2]).normalized()
    t_flare_f = (edge(rings[1]) - edge(rings[0])).normalized()
    t_flare_r = (edge(rings[-1]) - edge(rings[-2])).normalized()
    t_lip_r = Vector(r_path[-2] - r_path[-1]).normalized()
    middle = (f_rows
              + loft(f_rows[-1], t_lip_f, rings[0], t_flare_f, bvh)
              + rings
              + loft(rings[-1], t_flare_r, r_rows[-1], t_lip_r, bvh))
    # rear join: from the start of the rear arch's sweep, through the loft, into the lip - smoothed as one run
    j0 = len(middle) - LOFT_STEPS - REAR_JOIN_BACK

    def finish(tail, pin_tail):
        seq = smooth_window(middle + tail, j0, len(middle) + REAR_JOIN_ON)
        # the rear corner (lip -> loft -> the rear arch's pinched sweep end) a second, wider pass: it necked in there
        seq = smooth_window(seq, j0 - 10, len(middle) + 40, sigma=REAR_JOIN_SIGMA, passes=REAR_JOIN_PASSES, ramp=14)
        n = len(middle)
        return ([snap(sec, bvh) for sec in seq[:n]] + [snap(sec, bvh, pin_tail(sec)) for sec in seq[n:]])

    x0n, x1n = EXHAUST_ZONE[0] - 0.01, EXHAUST_ZONE[1] + 0.01        # no panel to pin to only in the notch itself
    left = finish(rx_rows[::-1], lambda sec: not (x0n < sec[0].x < x1n))
    right = finish(r_rows[::-1], lambda sec: True)
    # the centre-line sections of both halves must be the same points on x = 0, or remove_doubles leaves an open
    # seam down the middle of each lip (snapping/smoothing moved them up to 0.1 mm apart - a shading line)
    for i in (0, -1):
        centre = [Vector((0.0, p.y, p.z)) for p in left[i]]
        left[i], right[i] = centre, list(centre)
    gaps = [round(bvh.find_nearest(sec[0])[3] * 1000, 1) for sec in left]
    build.seqs = (left, right)
    build.sizes = {"left": [round((sec[8] - sec[0]).length * 1000, 1) for sec in left],
                   "right": [round((sec[8] - sec[0]).length * 1000, 1) for sec in right], "j0": j0,
                   "n_middle": len(middle)}

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for side, seq in ((1, left), (-1, right)):
        rows = [[bm.verts.new((side * p.x, p.y, p.z)) for p in sec] for sec in seq]
        m = len(rows[0])
        for r0, r1 in zip(rows, rows[1:]):
            for j in range(m - 1):
                q = (r0[j], r0[j + 1], r1[j + 1], r1[j])
                bm.faces.new(q if side == 1 else q[::-1])
    # the two halves meet on the centre line at the front and rear lips
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    for f in bm.faces:
        f.smooth = True
        for l in f.loops:
            l[uvl].uv = paint_uv
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(70):
            e.smooth = False
    # built wound outwards throughout (section attached->free edge x path direction); NOT through replace(),
    # whose normal recalculation flipped long stretches of this single open strip (rear flare + sill inside out)
    made = [load("build_cage").make_obj("RALLY_flares", bm, [paint], univers).name]

    fb = blade_along(f_bottom, FRONT["blade_proud"], FRONT["blade_under"], FRONT["blade_x"], tyre_taper=True)
    made.append(brp.replace("RALLY_blade_front", fb, [black], univers).name)
    rb = blade_along(rx_bottom, REAR["blade_proud"], REAR["blade_under"], REAR["blade_x"], strakes=REAR["strakes"])
    blade_along(r_bottom, REAR["blade_proud"], REAR["blade_under"], REAR["blade_x"], strakes=REAR["strakes"],
                bm=rb, mirror_x=True)
    made.append(brp.replace("RALLY_blade_rear", rb, [black], univers, mirror=False).name)
    build.gaps = gaps
    return made
