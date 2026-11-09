"""Rebuild the front wing from the drawings and the photographs. No Meshy, anywhere.

The old Wing_Front_Left was cut out of the Meshy shell and smoothed. It carries the shell's lumps
(4.3 mm RMS vertex-to-neighbours, worst 78 mm), it is 11-48 mm narrower than the door at their shared
shut line, and its wheel arch is a flat-topped tunnel with a diagonal cut across the back - nothing like
the clean high semicircle in the photographs. Nik, 2026-10-26: the shell is for the general shape of the
car and nothing else. So this builds the wing the way the door and the rocker were built.

**The surface** is the flank's own: x(y, z) = halfw(y) * section(z) - an orthographic plan taper times
an orthographic end-elevation section. At the wing's front corner the plan reads x 0.677 at y -1.657,
against the 0.6752 the photographs triangulate for the same corner (body_profile `front_taper.wb`): 2 mm
apart, so the drawing is good this far forward.

**The boundaries** are all traced:
  top    - the bonnet's shut line (`bonnet_shut` on the line blueprint), dropping to the lamp panel's
           own top edge ahead of where that trace starts;
  rear   - the door's front shut line, the same -0.670 the door is built to, so the step Nik spotted
           closes from both sides;
  bottom - the blueprint's `sill` line behind the arch, and our own front bumper's top edge ahead of it;
  arch   - `arch_shapes.front` in body_profile: the lip outline traced on the side photograph, 32 points,
           crown z 0.641 against the blueprint's 0.657.

**The shoulder step** (body_profile `wing_flare`) is the crease that runs the whole length of the car at
z 0.700-0.704 on the wing, with the panel below it standing 8 mm proud.

The arch gets a rolled lip - the opening's edge returns inboard - rather than ending in a paper edge.

Left only, with a Mirror modifier.

blender -b blender/nova_proc.blend --python tools/gen/rebuild_wing_drawn.py -- out.blend
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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PLAN = np.array(json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(D, "section_body.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))

DZ = 0.0193
SHUT_F, GAP = -0.670, 0.0025
NY, NZ = 170, 34
LIP = 0.018                     # how far the arch lip returns inboard


# 2026-10-27 (14): the plan half-width is a pixel trace (3.5 mm samples), so its slope steps from sample to sample
# (dx/dy 0.857, 0.886, 0.829 ...) and the wing's surface normal jittered 2-5 deg from one station to the next - the
# vertical banding on the wing. Not smoothed: a local quadratic is FITTED to the trace over +-PLAN_FIT_H at each
# sample (the same kind of low-order fit the bonnet's centreline uses), and the fit is used only if it stays within
# PLAN_FIT_TOL of the trace everywhere. It eases back to the raw trace over the last 60 mm before the door shut, where
# the shell (built on the raw trace) carries on, so the wing still meets the door exactly.
PLAN_FIT_H, PLAN_FIT_TOL = 0.012, 0.0010


def _plan_fit(P, h):
    out = P[:, 1].copy()
    for i, y0 in enumerate(P[:, 0]):
        k = np.abs(P[:, 0] - y0) <= h
        if k.sum() >= 4:
            w = (1 - (np.abs(P[k, 0] - y0) / (h * 1.0001)) ** 3) ** 3
            c = np.polyfit(P[k, 0] - y0, P[k, 1], 2, w=np.sqrt(w))
            out[i] = c[-1]
    return out


_pf = _plan_fit(PLAN, PLAN_FIT_H)
_dev = np.abs(_pf - PLAN[:, 1])
_win = (PLAN[:, 0] > -1.80) & (PLAN[:, 0] < -0.60)
PLAN_USE_FIT = bool(_dev[_win].max() <= PLAN_FIT_TOL)
print("plan fit (local quadratic +-%.0f mm): within %.2f mm of the trace (worst %.2f mm at y %+.3f) -> %s"
      % (PLAN_FIT_H * 1000, 1000 * _dev[_win].mean(), 1000 * _dev[_win].max(),
         PLAN[_win, 0][np.argmax(_dev[_win])], "used" if PLAN_USE_FIT else "NOT used (over tolerance)"))
PLAN_F = np.c_[PLAN[:, 0], _pf]


def halfw(y):
    raw = float(np.interp(y, PLAN[:, 0], PLAN[:, 1]))
    if not PLAN_USE_FIT:
        return raw
    fit = float(np.interp(y, PLAN_F[:, 0], PLAN_F[:, 1]))
    t = min(max((y - (-0.670 - 0.060)) / 0.060, 0.0), 1.0)       # SHUT_F is defined below; the door shut, -0.670
    w = t * t * (3.0 - 2.0 * t)
    return (1.0 - w) * fit + w * raw


def skin_x(y, z):
    return halfw(y) * float(np.interp(z, SECT[:, 0], SECT[:, 1]))


def curve(*names):
    return np.array(sorted({(round(a, 5), round(b, 5)) for n in names for a, b in SP[n]}), float)


def smooth(p, n=9):
    q = p.copy()
    pad = np.r_[np.repeat(p[:1, 1], n // 2), p[:, 1], np.repeat(p[-1:, 1], n // 2)]
    q[:, 1] = np.convolve(pad, np.ones(n) / n, "valid")
    return q


bonnet = smooth(curve("bonnet_shut", "bonnet_shut_b"))
sill = smooth(curve("sill", "sill_b"))

# ---- the arch lip, traced on the photograph ----------------------------------------------------
AR = np.array(PF["arch_shapes"]["front"], float)
AR[:, 1] += DZ
AR = AR[AR[:, 1] > 0.10]                         # drop the two tails that run down off the drawing
o = np.argsort(AR[:, 0])
arch = AR[o]
Y_AF, Y_AR = float(arch[0, 0]), float(arch[-1, 0])
print("arch lip: y %+.4f .. %+.4f, crown z %.4f at y %+.4f, ends z %.4f / %.4f"
      % (Y_AF, Y_AR, arch[:, 1].max(), arch[np.argmax(arch[:, 1]), 0], arch[0, 1], arch[-1, 1]))

# ---- the wing's own front and the bumper it sits behind -----------------------------------------
bump = bpy.data.objects.get("BUMPER_F")
Z_BUMP = (max((bump.matrix_world @ v.co).z for v in bump.data.vertices
              if -1.55 < (bump.matrix_world @ v.co).y < -1.40) if bump else 0.33)
# The wing's front edge is the shut line beside the indicator, raked back as it rises - it does NOT run
# on past the lamps. body_profile `front_taper` has it triangulated from the photographs: wb at the
# bottom, wt at the top. redgte_22 shows the same thing - the lamp unit is the front of the car and the
# wing's leading edge comes down just outboard of the indicator.
# The wing's front edge is a PLANE, not a constant-y cut. body_profile `front_panel` carries it
# measured: `wing_edge` is two points on it, triangulated through the indicator's outer corners, and
# `wing_edge_normal` is its normal. The normal's x component is the biggest of the three, so the edge
# sweeps forward as the body widens - which is what the photographs show, the shut line running down
# just outboard of the indicator and following it round. Cutting at a single y, as the first version
# did, leaves a flat wall across the corner.
FP = PF["front_panel"]
# wing_edge is triangulated through IND_OB / IND_OT, so like every BA point it is in the photo frame (ground on
# the loaded tyres): + DZ into the model, as the bonnet, belt, glass and arches already get. It had been used raw.
WE = np.array(FP["wing_edge"], float) + np.array([0.0, 0.0, DZ])
WN = np.array(FP["wing_edge_normal"], float)
P0 = WE[0]
_chk = WE[1]
# body_profile front_panel z_split: "below z_split (indicator top + 3 mm) the wing ends on the indicator wrap line;
# above it the V edge trims bonnet and wing corner". The wing used the wrap plane all the way up, and that plane
# runs back as it comes inboard (x is its biggest normal component) - at the bonnet's corner, x 0.605, it had
# reached y -1.56, 100 mm behind the corner at -1.664. That cut the wing's top corner off and left the gash at the
# nose. Above z_split the wing now runs forward to the bonnet's own V line, so the three panels meet at its corner.
BVL = PF["front_panel"]["bonnet_v"]
Z_SPLIT = float(FP["z_split"]) + DZ
SPLIT_W = 0.006                                  # the corner is eased over +- 6 mm of height, not stepped


def y_front(z, x=None):
    """Where the wing starts: the lamp-panel shut plane below z_split, the bonnet's V line above it."""
    if x is None:
        x = skin_x(float(P0[1]), z)
    y_plane = float(P0[1] - (WN[0] * (x - P0[0]) + WN[2] * (z - P0[2])) / WN[1])
    y_v = float(BVL["y0"]) + float(BVL["a"]) * abs(x)
    t = min(max((z - (Z_SPLIT - SPLIT_W)) / (2 * SPLIT_W), 0.0), 1.0)
    w = t * t * (3.0 - 2.0 * t)
    return (1.0 - w) * y_plane + w * y_v


_r = y_front(float(_chk[2]), float(_chk[0])) - float(_chk[1])
print("front shut plane: through (%.4f, %.4f, %.4f), normal %s; its second measured point is %+.1f mm off"
      % (P0[0], P0[1], P0[2], np.round(WN, 2), _r * 1000))

Y_FRONT = y_front(0.93)                          # its rearmost point, at the top of the roll
print("front shut: y %+.4f at the bottom of the skin, %+.4f at the top of the roll"
      % (y_front(0.56), Y_FRONT))
print("   (the headlamp glass starts at y -1.745; the wing used to run to -1.755, past it)")
print("bumper top behind the arch z %.4f" % Z_BUMP)

FLARE = np.array(PF["wing_flare"]["z_step"], float)
D_FLARE = float(PF["wing_flare"]["d"])
LEDGE = float(PF["wing_flare"]["ledge"])


def z_step(y):
    return float(np.interp(y, FLARE[:, 0], FLARE[:, 1]))


# ---- where the wing has to finish: the bonnet's own side edge ----------------------------------
# The flank surface x = halfw(y) * section(z) is the car's widest at each height, so it describes the
# wing's side but not its top: above the shoulder the wing rolls inboard and dies into the bonnet's shut
# line. Built as a plain flank it stopped at x 0.70 while the bonnet's edge is at 0.595 - the 105 mm
# hole along the top. So the top edge is read off the bonnet panel we already have, and the wing turns
# over to meet it.
# Take the panels' real BOUNDARY, not the outermost vertex at each station. Those panels are built on
# a lattice about 25 mm apart in x, so a max-x-per-station scan hops between interior columns and comes
# back as a 56 mm sawtooth - which is what corrugated the first two attempts at the wing's top.
# 2026-10-27 (12): replaced. The top edge is no longer found by scanning the bonnet's mesh - it is the bonnet's and
# the scuttle's own side-edge columns, written by their scripts to blender/data/shut_bonnet_wing.json, so the wing
# and the bonnet share one shut line by construction. No rounding to stations, no smoothing.
SHUT = json.load(open(os.path.join(D, "shut_bonnet_wing.json")))
_pts = [tuple(p) + (s,) for p, s in zip(SHUT["bonnet"], SHUT["bonnet_slope"])]
_yb = max(p[1] for p in _pts)
_pts += [tuple(p) + (s,) for p, s in zip(SHUT.get("scuttle", []), SHUT.get("scuttle_slope", []))
         if p[1] > _yb + 1e-4]
_pts.sort(key=lambda p: p[1])
hy = np.array([p[1] for p in _pts]); hx = np.array([p[0] for p in _pts]); hz = np.array([p[2] for p in _pts])
hs = np.array([p[3] for p in _pts])                # the bonnet / scuttle cross-slope dz/dx at the shut
print("   cross-slope at the shut: %.2f .. %.2f (%.0f .. %.0f deg)"
      % (hs.min(), hs.max(), math.degrees(math.atan(-hs.max())), math.degrees(math.atan(-hs.min()))))


def shut_slope(y):
    return float(np.interp(y, hy, hs))
print("shared shut line: %d points (bonnet + scuttle side edges), y %+.4f .. %+.4f, x %.4f .. %.4f"
      % (len(hy), hy[0], hy[-1], hx.min(), hx.max()))
OLD_SCAN = False
cols = {}
for nm in (("Hood_Panel", "Scuttle_Panel") if OLD_SCAN else ()):
    src = bpy.data.objects.get(nm)
    if src is None:
        raise SystemExit("%s is missing - the wing's top edge comes off its side edge" % nm)
    sm = src.matrix_world
    bmv = bmesh.new(); bmv.from_mesh(src.data)
    for v in bmv.verts:
        if not any(e.is_boundary for e in v.link_edges):
            continue
        p = sm @ v.co
        # the SIDE edge only: these panels' front and rear boundary rows also pass the x filter, and
        # they run inboard across the car, which is where the remaining sawtooth was coming from
        if p.x < 0.57:
            continue
        # Round the station to a millimetre, not to a tenth of one. At the bonnet's front corner the V edge
        # and the side edge interleave, and at 4 dp each landed on its own station - so the fitted edge got a
        # 12 mm zigzag there, which is what opened the shut into a gash at the nose. At 3 dp they share a
        # station and the max-x test keeps the side edge, which is the one the wing has to meet.
        k = round(p.y, 3)
        if k not in cols or p.x > cols[k][0]:
            cols[k] = (p.x, p.z)
    bmv.free()
if OLD_SCAN:
    print("bonnet/scuttle side boundary: %d stations, y %+.3f .. %+.3f"
          % (len(cols), min(cols), max(cols)))
    hy0 = np.array(sorted(cols))
    hx0 = np.array([cols[k][0] for k in hy0])
    hz0 = np.array([cols[k][1] for k in hy0])
# Those are whichever vertices of the bonnet and scuttle happen to land nearest each station - and the
# bonnet is itself still Meshy-derived and lumpy, so its edge carries that lumpiness. Following it
# vertex by vertex put corrugations right across the top of the wing. The real edge is a shut line: a
# long, gentle curve. So a cubic is fitted to it in both x and z, and the wing is built to the fit.
# (Kept only behind OLD_SCAN; the shared shut line above needs none of it.)


def ease(a_, n=3, passes=1):
    """Light running mean. This averaged over about 160 mm, because the bonnet was cut out of the Meshy
    shell then and its side edge carried that shell's lumps. The bonnet has been built analytically from
    the drawings since 2026-10-26 (rebuild_bonnet_drawn.py) and its edge is smooth already, so the heavy
    averaging was only doing harm: it pulled the fitted edge up to 24 mm off in x and 29 mm in z, worst at
    the nose where the real edge drops away sharply - which is what opened the bonnet-to-wing shut into a
    41 mm gash at the front."""
    out = np.asarray(a_, float)
    for _ in range(passes):
        out = np.convolve(np.r_[np.repeat(out[0], n // 2), out, np.repeat(out[-1], n // 2)],
                          np.ones(n) / n, "valid")
    return out


if OLD_SCAN:
    hy = np.linspace(hy0[0], hy0[-1], 260)
    hx = ease(np.interp(hy, hy0, hx0))
    hz = ease(np.interp(hy, hy0, hz0))

# The wing's top lands ON the bonnet's side edge. The shut gap itself is opened later, by roll_edges.py,
# which pulls both panels' edges back 2.2 mm along the surface before turning them under - so allowing a gap
# here as well made it about 10 mm, twice what the car has.
SHUT_T = 0.000                  # the bonnet-to-wing shut gap (opened by roll_edges, not here)
FLUSH_TOP = True                # the wing's top arrives on the bonnet's cross-slope (2026-10-27 (13))
CHORD_CREASE = True             # above the shoulder crease the panel leans in along the chord (2026-10-27 (14))
CREASE_EASE = 0.150             # ...easing back to the flank over this much before the door shut
TURN = 0.075                    # how much height the wing's top roll takes


def top_edge(y):
    """Where the wing's top finishes: just outboard of the bonnet's side edge."""
    if y < hy[0]:
        return float(hx[0]), float(hz[0])
    if y > hy[-1]:
        return float(hx[-1]), float(hz[-1])
    return float(np.interp(y, hy, hx)) + SHUT_T, float(np.interp(y, hy, hz))


def z_top(y):
    return top_edge(y)[1]


def z_bot(y):
    """The arch lip where the arch is, the sill line behind it, the bumper's top edge in front."""
    if Y_AF <= y <= Y_AR:
        return float(np.interp(y, arch[:, 0], arch[:, 1]))
    if y > Y_AR:
        return float(np.interp(y, sill[:, 0], sill[:, 1]))
    return Z_BUMP


# Put grid lines exactly on the arch's two vertical ends so those edges come out straight, and on the
# shut line and the front edge. Everything between is spaced evenly.
keys = sorted({y_front(0.56) - 0.004, Y_AF - 0.0005, Y_AF, Y_AR, Y_AR + 0.0005, SHUT_F - GAP})
ys = []
for a, b in zip(keys[:-1], keys[1:]):
    n = max(2, int(round((b - a) / ((SHUT_F - GAP - y_front(0.56)) / NY))))
    ys += list(np.linspace(a, b, n, endpoint=False))
ys.append(keys[-1])
ys = np.array(ys)


def rows(y):
    """Up the wing from its lower edge: the arch lip's return, then the skin, with the shoulder step.

    The lip is a **recessed flange, not a rolled ridge** (Nik, and redgte_22 shows it plainly): the skin
    runs out to the opening at full width, turns in through a tight corner, and the flange folds back
    UP inside the wheel well. Folding it down and out, as the first build did, makes a bead round the
    arch - the opposite of the concave step the car has.
    """
    zb, zt, zs = z_bot(y), z_top(y), z_step(y)
    inner = Y_AF <= y <= Y_AR                     # the arch opening, as opposed to the sill or bumper
    if inner:
        out = [(skin_x(y, zb) + D_FLARE - LIP, zb + 0.014),      # the flange, back up inside the well
               (skin_x(y, zb) + D_FLARE - 0.012, zb + 0.0025),   # the tight inward corner
               (skin_x(y, zb) + D_FLARE - 0.002, zb)]            # the lip itself, at the skin
    else:
        out = [(skin_x(y, zb) + D_FLARE - LIP, zb - 0.004),
               (skin_x(y, zb) + D_FLARE - 0.006, zb - 0.001),
               (skin_x(y, zb) + D_FLARE - 0.002, zb)]
    lo = [z for z in np.linspace(zb, zs, max(2, NZ // 2)) if z < zs - 1e-6]
    for z in lo:
        out.append((skin_x(y, z) + D_FLARE, z))           # the flared panel, 8 mm proud
    out.append((skin_x(y, zs) + D_FLARE, zs))             # the step's lower lip
    out.append((skin_x(y, zs + LEDGE), zs + LEDGE))       # and its top
    xt, _ = top_edge(y)
    # Up the top of the wing. The first build held the flank until 75 mm from the top and then rolled
    # over a quarter-ellipse, which put a crease right across the wing where the roll started. The real
    # panel has no such line: it leaves the flank gradually and arrives at the bonnet's shut line
    # already lying over. So the pull-in is blended with a curve that is flat at both ends - no crease
    # where it starts, no corner where it lands.
    z0 = zs + LEDGE
    n_top = NZ - len(out) + 1
    if not FLUSH_TOP:
        pull = skin_x(y, zt) - xt
        for z in np.linspace(z0, zt, n_top)[1:]:
            t = (z - z0) / max(zt - z0, 1e-6)
            w = t * t * t * (10.0 - 15.0 * t + 6.0 * t * t)      # smootherstep
            out.append((skin_x(y, z) - pull * w, z))
        return out
    # 2026-10-27 (13): flush with the bonnet. The smootherstep above left the wing arriving at the shut with the
    # FLANK's slope (the section's tumblehome, ~57 deg) while the bonnet leaves it at ~23 deg, so the two met at a
    # 34 deg fold and, once roll_edges pulled each back 2.2 mm along its own surface, the wing's lip sat 5-7 mm below
    # the bonnet's. On the car the wing's top is the bonnet's outer panel carried on over the shut. So the top is a
    # cubic Hermite in the (x, z) section: it leaves the shoulder step along the flank's own tangent and arrives at
    # the shut along the bonnet's cross-slope (shut_slope, written by the bonnet / scuttle scripts) - tangent-
    # continuous at both ends, no fold at either.
    x0 = skin_x(y, z0)
    hz_ = 0.002
    dxdz = (skin_x(y, z0 + hz_) - skin_x(y, z0 - hz_)) / (2 * hz_)
    T_flank = np.array([dxdz, 1.0]); T_flank /= np.linalg.norm(T_flank)   # up the flank
    s = shut_slope(y)                                                # dz/dx, < 0 falling outboard
    T1 = np.array([-1.0, -s]); T1 /= np.linalg.norm(T1)              # inboard and up, along the bonnet
    P0 = np.array([x0, z0]); P1 = np.array([xt, zt])
    L = float(np.linalg.norm(P1 - P0))
    # 2026-10-27 (14): the shoulder crease. Leaving the step along the flank's tangent made the panel above the
    # crease lean in no more than the panel below it (19 vs 21 deg off vertical at y -1.10), so the crease was only
    # an 8 mm offset and read faintly - where in anglia_side / redgte_22 the panel above it is bright (lying back to
    # the sky) and the one below dark. No drawing gives that lean (the GA front elevation's outline at these heights
    # is the door's, which hides the wing's top), so the least-invented shape is used: above the crease the panel
    # heads straight for the shut (the chord), curving onto the bonnet's slope at the top. It eases back to the
    # flank tangent over the last CREASE_EASE before the door shut, where the shell's door skin carries on.
    # SHAPE ESTIMATE - judge against the photographs.
    T0 = T_flank
    if CHORD_CREASE:
        tc = (P1 - P0) / max(L, 1e-9)
        k = min(max((SHUT_F - y) / CREASE_EASE, 0.0), 1.0)
        k = k * k * (3.0 - 2.0 * k)
        T0 = (1.0 - k) * T_flank + k * tc
        T0 /= np.linalg.norm(T0)
    for t in np.linspace(0.0, 1.0, n_top)[1:]:
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1; h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2;    h11 = t ** 3 - t ** 2
        p = h00 * P0 + h10 * L * T0 + h01 * P1 + h11 * L * T1
        out.append((float(p[0]), float(p[1])))
    return out


NR = len(rows(float(ys[len(ys) // 2])))
for y in ys:
    if len(rows(float(y))) != NR:
        raise SystemExit("row count varies (%d vs %d at y %+.4f)" % (len(rows(float(y))), NR, y))

# The front shut is raked, so stations ahead of it at a given height are pulled back onto it; the
# corner then closes as a fan of collapsed quads, which remove_doubles tidies into a clean edge.
bm = bmesh.new()
V = []
for y in ys:
    col = []
    for x_, z_ in rows(float(y)):
        col.append(bm.verts.new((x_, max(float(y), y_front(z_, x_)), z_)))
    V.append(col)
for i in range(len(ys) - 1):
    for j in range(NR - 1):
        a, b, c, d = V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]
        if (a.co - b.co).length < 1e-7 and (d.co - c.co).length < 1e-7:
            continue
        bm.faces.new((a, b, c, d))
bm.faces.ensure_lookup_table(); bm.normal_update()
if sum(f.normal.x for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
# 2026-10-27 (14): the banding on the wing's top at the nose. Above z_split about twenty stations ahead of the
# bonnet's V line are pulled back onto it, but each keeps its own x, so they do not coincide - they land 0.1 mm
# apart and leave a fan of sliver faces whose normals scatter, which shades as bands. Merge what lies within
# MERGE (no two real rows or stations of the wing are closer than 2.5 mm), then dissolve what collapsed.
MERGE = 0.0008
_sliv = lambda: sum(1 for f in bm.faces if f.calc_area() < 2e-6)
_n0, _s0 = len(bm.verts), _sliv()
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=MERGE)
bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=MERGE)
print("   front-edge fan: %d -> %d verts, sliver faces (< 2 mm2) %d -> %d" % (_n0, len(bm.verts), _s0, _sliv()))
bm.normal_update()

name = "Wing_Front_Left"
for stale in ("Wing_Front_Left", "Wing_Front_Right", "Fender_Front_Left", "Fender_Front_Right"):
    ob = bpy.data.objects.get(stale)
    if ob:
        coll = ob.users_collection[0]
        bpy.data.objects.remove(ob, do_unlink=True)
        print("removed %s" % stale)
coll = (bpy.data.collections.get("NOVA_NEW")
        or (bpy.data.objects["Door_Left"].users_collection[0] if bpy.data.objects.get("Door_Left") else None)
        or bpy.context.scene.collection)

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
mir.use_clip = False
print("%s: %d verts, %d faces, mirrored" % (name, len(mesh.vertices), len(mesh.polygons)))
print("   y %+.3f .. %+.3f, z %.3f .. %.3f, x %.4f .. %.4f"
      % (ys[0], ys[-1], min(v.co.z for v in mesh.vertices), max(v.co.z for v in mesh.vertices),
         min(v.co.x for v in mesh.vertices), max(v.co.x for v in mesh.vertices)))
print("   at the door shut the wing reaches x %.4f (the door is built to %.4f)"
      % (skin_x(SHUT_F - GAP, 0.55), skin_x(SHUT_F, 0.55)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
