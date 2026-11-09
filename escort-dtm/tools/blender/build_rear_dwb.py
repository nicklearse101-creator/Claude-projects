"""Rear suspension on the MODEL: the original live axle on leaf springs -> double wishbone (looks only - the physics
has been a double wishbone since v20). Runs inside Blender on blender/escort_aero.blend AFTER build_aero.build()
(which deletes every aero_part, these included). Plan: docs/plans/2026-10-05-rear-dwb-visual.md.

    import build_rear_dwb as r
    r.remove_leaf_rear()   # main + LOD B/C: leaf springs, shackles, U-bolts, axle tubes, radius rods, old dampers
                           #   (the diff housing - the centre pieces of suspension_a_SUB3 - stays, now body-mounted)
    r.build()              # AERO_rsus_* parts from dtm_build.REAR_DWB; uprights hang off SUSP_LR/RR (move with the
                           #   wheel like the calipers), everything else is static at ride height
    r.check()              # clearance of every new part to the rest of the car

Geometry: every pivot is dtm_build.REAR_DWB (x inboard from the wheel centre, y up, z forward) placed on the
model's wheel (SUSP_xR node = the static wheel centre in game, see STATIC). Body-side pivots sit at the DESIGN
height, DESIGN_UP above the static wheel: design wheel centre = CoG height (-GRAPHICS_OFFSET y 0.400) + BASEY_R
(-0.280) = 0.120 vs static 0.092 (rod 0.055 down, spring sag ~0.027 up) - so at ride height the arms droop a little,
as in the physics. Blender: +X = car's left, +Y = rear, Z up.
"""
import importlib.util
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import build_aero as ba

_spec = importlib.util.spec_from_file_location("dtm_build", os.path.join(os.path.dirname(__file__), "..", "dtm_build.py"))
dtm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dtm)

GRAPHICS_COG_Y, BASEY_R = 0.400, -0.280            # car.ini GRAPHICS_OFFSET y (negated), suspensions.ini [REAR] BASEY
METAL = "Material #503ds"                           # the exhaust's metal - damper bodies, drive shafts, CV joints
SIZES = dict(upper_r=0.010, lower_r=0.012, bush_r=0.017, bush_len=0.045, ball_upper=0.018, ball_lower=0.021,
             toe_r=0.008, rod_end=0.013, shaft_r=0.013, cv_r=0.040, boot_r=0.034, sides=10)
# coilover in the wheel tub, where the old dampers stood: the boot floor is only ~0.11 high inboard of the tub wall
# (x 0.536, vertical), the tub ceiling ~0.32-0.33 outboard of it; the tyre's inner face is 0.62-0.68 out behind the
# axle line. So: a slim coilover (52 mm spring) centred 0.146 inboard of the wheel (x 0.568), 78 mm behind the axle
# line (clear of the drive shaft), top just under the tub ceiling. Lower eye on the lower wishbone's rear leg.
COILOVER = dict(inboard=0.146, top_up=0.226, top_back=0.078, body_r=0.020, shaft_r=0.007, spring_r=0.026,
                wire=0.0050, turns=6.0, seat_r=0.030)
DIFF_OUT = dict(inboard_x=0.165, z=0.025)          # diff output flanges (axle tubes ran at 0.01; +15 mm clears the exhaust)
# the upper inner pivots (0.40 inboard, z 0.25) are inside the car, above the floor over the axle - not under it as
# the plan assumed: posts DOWN to that floor (tube-frame style), a pivot shaft through both bushes
TURRET = dict(above=0.15, max_down=0.30, post_r=0.012, foot=0.028, shaft_r=0.008, shaft_ext=0.035)
OLD_PARTS_MAIN = ("suspension_a_SUB1", "suspension_a_SUB4")   # removed whole: U-bolts/plates, old dampers
OLD_SPRINGS = "suspension_a_SUB3"                  # leafs + axle + diff: keep only the diff pieces
DIFF_BOX = ((-0.165, 0.98, -0.14), (0.165, 1.35, 0.12))


# ---- removal ---------------------------------------------------------------------------------------------------
def _islands(bm):
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        st, comp = [v], []
        seen.add(v.index)
        while st:
            u = st.pop(); comp.append(u)
            for e in u.link_edges:
                w = e.other_vert(u)
                if w.index not in seen:
                    seen.add(w.index); st.append(w)
        out.append(comp)
    return out


def remove_leaf_rear():
    """Idempotent: whatever of the old rear is still there goes; reports what it removed per scene."""
    done = {}
    for tag in ("Scene", "LOD_B", "LOD_C", "LOD_D"):
        sc = bpy.data.scenes[tag]
        rep = []
        for ob in list(sc.objects):
            if ob.type != "MESH":
                continue
            nm = ob.get("kn5_name") or ob.name
            if nm in OLD_PARTS_MAIN:
                rep.append((nm, "removed", len(ob.data.vertices))); bpy.data.objects.remove(ob); continue
            if nm != OLD_SPRINGS:
                continue
            mw = ob.matrix_world
            bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
            lo, hi = DIFF_BOX
            kill = []
            for comp in _islands(bm):
                ws = [mw @ u.co for u in comp]
                if not all(lo[i] <= p[i] <= hi[i] for p in ws for i in range(3)):
                    kill += comp
            if kill:
                n = len(kill)
                bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(ob.data); ob.data.update()
                rep.append((nm, f"kept the diff ({len(bm.verts)} verts), removed", n))
            bm.free()
        done[tag] = rep
    return done


# ---- geometry helpers (world space) ----------------------------------------------------------------------------
def _frame(d):
    d = d.normalized()
    a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized()
    return u, d.cross(u).normalized()


def ring(c, d, r, n):
    u, v = _frame(d)
    return [tuple(c + (u * math.cos(2 * math.pi * k / n) + v * math.sin(2 * math.pi * k / n)) * r) for k in range(n)]


def tube(p0, p1, r0, r1=None, n=None):
    n = n or SIZES["sides"]
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    return ba.loft([ring(p0, d, r0, n), ring(p1, d, r1 if r1 is not None else r0, n)])


def bellows(p0, p1, r0, r1, folds=4, n=None):
    """CV boot: a cone with ribs."""
    n = n or SIZES["sides"]
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    secs = []
    for k in range(folds * 2 + 1):
        t = k / (folds * 2)
        r = r0 + (r1 - r0) * t
        secs.append(ring(p0 + d * t, d, r * (1.0 if k % 2 == 0 else 0.86), n))
    return ba.loft(secs)


def sphere(c, r, n=None):
    n = n or SIZES["sides"]
    c = Vector(c)
    secs = []
    for k in range(1, 5):
        a = -math.pi / 2 + math.pi * k / 5
        secs.append(ring(c + Vector((0, 0, r * math.sin(a))), Vector((0, 0, 1)), max(r * math.cos(a), 1e-4), n))
    return ba.loft(secs)


def box(c, ax, ay, az):
    """Box at c with half-extent vectors ax, ay, az."""
    c, ax, ay, az = Vector(c), Vector(ax), Vector(ay), Vector(az)
    corners = [c + sx * ax + sy * ay + sz * az for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    v = [tuple(p) for p in corners]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return v, f


def helix(p0, p1, coil_r, wire_r, turns, seg_per_turn=18, n=6):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    u, v = _frame(d)
    steps = int(turns * seg_per_turn)
    pts = [p0 + d * (i / steps) + (u * math.cos(2 * math.pi * turns * i / steps)
                                    + v * math.sin(2 * math.pi * turns * i / steps)) * coil_r for i in range(steps + 1)]
    secs = [ring(pts[i], (pts[min(i + 1, steps)] - pts[max(i - 1, 0)]), wire_r, n) for i in range(steps + 1)]
    return ba.loft(secs)


# ---- the suspension --------------------------------------------------------------------------------------------
def corner_points(side):
    """World points for one rear corner. side +1 = car's left (SUSP_LR), -1 = right (SUSP_RR)."""
    node = ba.kn5_obj("SUSP_LR" if side > 0 else "SUSP_RR", "EMPTY")
    w = node.matrix_world.translation.copy()
    design_up = (GRAPHICS_COG_Y + BASEY_R) - w.z
    P = lambda inb, up, fwd, body=False: Vector((w.x - side * inb, w.y - fwd, w.z + up + (design_up if body else 0.0)))
    g = dtm.REAR_DWB
    pts = {k: P(*g[k], body=True) for k in ("WBCAR_TOP_FRONT", "WBCAR_TOP_REAR", "WBCAR_BOTTOM_FRONT",
                                            "WBCAR_BOTTOM_REAR", "WBCAR_STEER")}
    pts.update({k: P(*g[k]) for k in ("WBTYRE_TOP", "WBTYRE_BOTTOM", "WBTYRE_STEER")})
    pts["hub"], pts["node"], pts["design_up"] = w.copy(), node, design_up
    pts["P"] = P
    return pts


def _floor_above(p, bvh_all, max_up=0.45):
    hit = bvh_all.ray_cast(Vector(p), Vector((0, 0, 1)), max_up)
    return hit[0]


def _scene_bvh(exclude_prefix=("AERO", "M_Tire", "for_5_escort", "for_rotor", "for_caliper", "suspension_a")):
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    for o in ba.main_scene().objects:
        if o.type == "MESH" and not str(o.get("kn5_name") or o.name).startswith(exclude_prefix):
            t = o.data.copy(); t.transform(o.matrix_world); bm.from_mesh(t); bpy.data.meshes.remove(t)
    tree = BVHTree.FromBMesh(bm); bm.free()
    return tree


def build():
    sc = ba.main_scene()
    bpy.context.window.scene = sc
    for o in [o for o in bpy.data.objects if o.get("rsus_part")]:
        bpy.data.objects.remove(o)
    trim, metal = ba.material(ba.TRIM), ba.material(METAL)
    tuv = ba.pick_uv(trim, (0.70, 0.30, 0.75))[1]
    muv = ba.pick_uv(metal, (0.30, 1.00, 0.00))[1]
    rt = ba.root()
    world = _scene_bvh(exclude_prefix=("AERO", "M_Tire", "for_5_escort", "for_rotor", "for_caliper",
                                       "suspension_a", "exhaust_a"))      # brackets go to the floor, never the exhaust
    s = SIZES
    arms, toe, coil_metal, coil_spring, shafts, brackets = [], [], [], [], [], []
    out = {}
    for side in (1, -1):
        c = corner_points(side)
        P = c["P"]
        ubj, lbj, to = c["WBTYRE_TOP"], c["WBTYRE_BOTTOM"], c["WBTYRE_STEER"]
        uf, ur, lf, lr, ti = (c[k] for k in ("WBCAR_TOP_FRONT", "WBCAR_TOP_REAR", "WBCAR_BOTTOM_FRONT",
                                            "WBCAR_BOTTOM_REAR", "WBCAR_STEER"))
        # wishbones: two legs to the ball joint, a bush on each inner pivot (axis = the pivot line), a ball joint
        for (a, b, j, r, rb) in ((uf, ur, ubj, s["upper_r"], s["ball_upper"]), (lf, lr, lbj, s["lower_r"], s["ball_lower"])):
            axis = (b - a).normalized()
            for p in (a, b):
                arms.append(tube(p - axis * s["bush_len"] / 2, p + axis * s["bush_len"] / 2, s["bush_r"]))
                arms.append(tube(p, j, r))
                if p.z > TURRET["above"]:
                    # upper pivots are ABOVE the floor over the axle (0.105-0.11; the front one under the rear seat
                    # back, the rear one inside the boot's front wall): a turret post down to the floor + foot plate
                    foot = world.ray_cast(p - Vector((0, 0, s["bush_r"])), Vector((0, 0, -1)), TURRET["max_down"])[0]
                    if foot is not None:
                        brackets.append(tube(p, foot, TURRET["post_r"]))
                        brackets.append(box(foot + Vector((0, 0, 0.003)), Vector((TURRET["foot"], 0, 0)),
                                            Vector((0, TURRET["foot"], 0)), Vector((0, 0, 0.003))))
                    continue
                top = _floor_above(p, world)                           # lower pivots: bracket up to the floor pan
                if top is not None and (top - p).length > 0.03:
                    brackets.append(box((p + top) / 2, Vector((side * 0.004, 0, 0)), axis * 0.022,
                                        Vector((0, 0, (top - p).length / 2 + 0.004))))
            if a.z > TURRET["above"]:                                  # pivot shaft through both upper bushes
                brackets.append(tube(a - axis * TURRET["shaft_ext"], b + axis * TURRET["shaft_ext"], TURRET["shaft_r"]))
            arms.append(sphere(j, rb))
        # toe link with rod ends
        toe.append(tube(ti, to, s["toe_r"])); toe.append(sphere(ti, s["rod_end"])); toe.append(sphere(to, s["rod_end"]))
        # coilover: lower eye on the lower wishbone's rear leg (clear of the drive shaft), top mount above
        f = (dtm.REAR_DWB["WBCAR_BOTTOM_REAR"][0] - COILOVER["inboard"]) / (dtm.REAR_DWB["WBCAR_BOTTOM_REAR"][0] - dtm.REAR_DWB["WBTYRE_BOTTOM"][0])
        cl = lr + (lbj - lr) * f + Vector((0, 0, s["lower_r"] + 0.012))
        ct = P(COILOVER["inboard"], COILOVER["top_up"], -COILOVER["top_back"])
        ax = (ct - cl).normalized()
        L = (ct - cl).length
        coil_metal.append(tube(cl, cl + ax * L * 0.55, COILOVER["body_r"]))                 # damper body
        coil_metal.append(tube(cl + ax * L * 0.55, ct, COILOVER["shaft_r"]))                 # shaft
        coil_metal.append(tube(cl + ax * L * 0.30, cl + ax * (L * 0.30 + 0.006), COILOVER["seat_r"]))   # lower seat
        coil_metal.append(tube(ct - ax * 0.026, ct - ax * 0.020, COILOVER["seat_r"]))      # upper seat
        coil_metal.append(tube(cl - ax * 0.012, cl + ax * 0.012, 0.014))                   # lower eye
        coil_spring.append(helix(cl + ax * (L * 0.30 + 0.006), ct - ax * 0.026, COILOVER["spring_r"], COILOVER["wire"], COILOVER["turns"]))
        brackets.append(box(ct + ax * 0.004, Vector((0.026, 0, 0)), Vector((0, 0.03, 0)), Vector((0, 0, 0.004))))   # top plate
        # drive shaft: diff flange -> outer CV at the upright (static: the outer CV sits at the hub's ride position)
        hub = c["hub"]
        d_in = Vector((side * DIFF_OUT["inboard_x"], hub.y, DIFF_OUT["z"]))
        d_out = P(0.085, 0.0, 0.0)
        dd = (d_out - d_in).normalized()
        shafts.append(tube(d_in, d_in + dd * 0.045, s["cv_r"]))
        shafts.append(bellows(d_in + dd * 0.045, d_in + dd * 0.125, s["boot_r"], s["shaft_r"] * 1.3))
        shafts.append(tube(d_in + dd * 0.12, d_out - dd * 0.12, s["shaft_r"]))
        shafts.append(bellows(d_out - dd * 0.125, d_out - dd * 0.045, s["shaft_r"] * 1.3, s["boot_r"]))
        shafts.append(tube(d_out - dd * 0.045, d_out, s["cv_r"] * 0.95))
        # upright (moves with the wheel: parented to SUSP_xR like the brake caliper)
        up = []
        col_c = (ubj + lbj) / 2
        span = ubj - lbj
        up.append(box(col_c, Vector((side * 0.016, 0, 0)), Vector((0, 0.032, 0)), span / 2 * 0.86))
        up.append(tube(P(0.035, 0, 0), P(0.085, 0, 0), 0.056))                                 # hub boss / bearing housing
        up.append(tube(P(0.06, 0.06, 0.02), to, 0.010))                                         # steering arm to the toe link
        up.append(tube(ubj + Vector((0, 0, -0.03)), ubj, 0.015)); up.append(tube(lbj, lbj + Vector((0, 0, 0.03)), 0.017))
        name = "AERO_rsus_upright_" + ("L" if side > 0 else "R")
        ob = ba.make_obj(name, ba.merge(*up), trim, tuv, c["node"])
        ob["rsus_part"] = True
        out[name] = dict(design_up=round(c["design_up"], 4), hub=[round(v, 3) for v in hub])
    for name, parts, mat, uv in (("AERO_rsus_wishbones", arms, trim, tuv), ("AERO_rsus_toe_links", toe, trim, tuv),
                                 ("AERO_rsus_dampers", coil_metal, metal, muv), ("AERO_rsus_springs", coil_spring, trim, tuv),
                                 ("AERO_rsus_driveshafts", shafts, metal, muv), ("AERO_rsus_brackets", brackets, trim, tuv)):
        ob = ba.make_obj(name, ba.merge(*parts), mat, uv, rt)
        ob["rsus_part"] = True
        out[name] = len(ob.data.polygons)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_mainfile()
    return out


def check():
    """Nearest distance from each new part to the rest of the car (tyres/wheels/brakes/old suspension excluded)."""
    world = _scene_bvh()
    res = {}
    for o in [o for o in ba.main_scene().objects if o.get("rsus_part")]:
        mw = o.matrix_world
        best = (9.0, None)
        for v in o.data.vertices:
            p = mw @ v.co
            loc, nrm, idx, dist = world.find_nearest(p, 0.2)
            if loc is not None and dist < best[0]:
                inside = nrm.dot(p - loc) < 0
                best = (dist, inside)
        res[o.name] = dict(faces=len(o.data.polygons), nearest_mm=round(best[0] * 1000, 1), touching_inside=best[1])
    return res
