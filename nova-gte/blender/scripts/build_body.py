"""Nova GTE body shell (runs inside Blender).

Shape: blender/scripts/body_geom.py, which is shared with the photo-overlay preview (tools/photomatch/preview.py),
so the shell checked against the reference photos is the shell that gets built. Profile numbers live in
tools/photomatch/body_profile.json (photo/BA frame; body_geom lifts them by DZ onto the unloaded tyres).

This script adds what only the real mesh needs, all on the unswept loft before the end sweep is applied:
  * exact cut lines for every trim / glass / lamp zone (bisect planes) so zone edges are straight,
  * real V-groove panel shut lines (doors, bonnet, hatch, bumper joints) and the GTE bumper ribs,
  * the sharp shoulder crease,
then sweeps the ends in plan, lifts to the model frame and swaps the mesh into BODY_shell, keeping its
modifiers (Mirror, Inner solidify, arch Booleans) and material slots. Groove sizes are ESTIMATE.
"""
import importlib
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r"D:\Claude\vauxhall_nova_gte_1989")
if str(ROOT / "blender" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "blender" / "scripts"))
import body_geom as g  # noqa: E402
importlib.reload(g)
import glass_panels as gp  # noqa: E402
importlib.reload(gp)

GAP = g.GAP                     # panel gap width 5 mm
DEPTH = 0.004                   # shut-line groove depth
RIB_W, RIB_D = 0.004, 0.0025    # bumper rib groove width / depth
XB = 0.605                      # bonnet edge along the wing tops (BA BON_F 0.599 front, WS_B 0.609 rear)
ZB = 0.742                      # bonnet front edge over the lamps / grille surround (BON_F z 0.757 at the corner)
YB_REAR = -0.765                # bonnet rear edge in front of the scuttle vent
ZBUMP_F, ZBUMP_R = 0.545, 0.560 # bumper top joints front / rear (rear: under the lamps, photos cAR / c24)
XH, ZH, YH = 0.585, 0.815, 1.190  # hatch side (legacy), bottom and top shut lines; top line ahead of the roof visor
# tailgate side shut line, triangulated anglia_side (mirrored) x anglia_rear as a 3D line (fit residuals 2-3 px,
# 2026-10-13): (0.659, 1.633, 0.82) .. (0.597, 1.457, 1.00) .. (0.507, 1.203, 1.26) - 45 deg, parallel to the quarter
# glass rear edge and ~15 cm behind it (was a vertical cut at x 0.585, 12 cm too far back)
SHUT_TG = ((0.597, 1.457, 1.00), (0.528, 1.262, 1.20))
RIBS_F = [0.390, 0.405, 0.420, 0.435, 0.450]   # GTE ribbed band, front bumper (photos c20 / cS)
RIBS_R = [0.465, 0.480, 0.495, 0.510, 0.525]   # rear bumper (cAR / cS)

COLOURS = {"paint_gunmetal": ((0.12, 0.13, 0.14, 1), "paint"), "glass_tint": ((0.04, 0.05, 0.05, 1), "glass"),
           "trim_black": ((0.015, 0.015, 0.015, 1), "trim"), "trim_grey": ((0.10, 0.10, 0.105, 1), "trim"),
           "lamp_clear": ((0.75, 0.75, 0.72, 1), "lens"), "lamp_red": ((0.45, 0.02, 0.02, 1), "lens"),
           "lamp_amber": ((0.80, 0.38, 0.02, 1), "lens"), "panel_gap": ((0.0, 0.0, 0.0, 1), "trim")}


def ensure_materials():
    out = []
    for name in g.MATS:
        rgba, preset = COLOURS[name]
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = rgba
        m.diffuse_color = rgba
        if name == "glass_tint":
            m["ac_shader"] = "ksPerPixel"; m["ac_blend"] = 1; m["ac_depth"] = 1; m["ac_alpha"] = 0.30
            if "ac_preset" in m:
                del m["ac_preset"]
        else:
            m["ac_preset"] = preset; m["ac_shader"] = "ksPerPixelMultiMap"
        out.append(m)
    return out


def side(f, rl):
    return 0 <= f[rl] < g.NS - 1


def top(f, rl):
    return f[rl] >= g.NS - 1


def bisect(bm, co, no, keep):
    faces = [f for f in bm.faces if keep(f)]
    if not faces:
        return
    geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(co), plane_no=Vector(no).normalized())


def warp_scuttle(bm, rl):
    """Bonnet rear edge, scuttle and screen base onto their plan curves (body_profile scuttle_curve) by bending the
    mesh rows themselves (like the end sweeps), not by cutting across them - clean rows, no sliver faces. The loft is
    built with straight rows at the bonnet rear groove (YB_REAR) and the screen base (Y_A + riser / seal); each top
    vertex moves in y by a warp that is the bonnet-edge curve at YB_REAR, the base curve at Y_A, linear between and
    fading out ahead (to y_f0) and behind (to y_f1). Heights are resampled from the unwarped surface at the new
    position, so the bonnet and the screen keep their shape; the scuttle panel is rebuilt between the bonnet edge
    (step below it) and the screen base (riser + seal); the screen surface is extended down at its own slope where the
    base moves forward. Runs on the unswept loft, before the grooves are pushed."""
    S = g.SCU
    Y0, Y1 = YB_REAR + GAP / 2, g.Y_A
    yf0, yf1 = -1.25, -0.45
    bmc = bm.copy()
    bvh = BVHTree.FromBMesh(bmc)
    bmc.free()

    def z_old(x, y):
        h = bvh.ray_cast(Vector((x, y, 3.0)), Vector((0.0, 0.0, -1.0)))
        return h[0].z if h[0] is not None else None

    def glass(x, y):
        if y >= Y1:
            return z_old(x, y)
        z0, z1 = z_old(x, Y1), z_old(x, Y1 + 0.04)
        return None if z0 is None or z1 is None else z0 - (z1 - z0) / 0.04 * (Y1 - y)

    def dr(x):
        return min(0.0, g.bonnet_rear_y(x) - YB_REAR)

    def db(x):
        return min(0.0, g.screen_base_y(x) - Y1)

    def delta(x, y):
        fx = 1.0 - g.smoothstep((x - 0.60) / 0.06)
        if y <= yf0 or y >= yf1:
            return 0.0
        if y < YB_REAR:
            w = dr(x) * g.smoothstep((y - yf0) / (YB_REAR - yf0))
        elif y <= Y1:
            w = dr(x) + (db(x) - dr(x)) * (y - YB_REAR) / (Y1 - YB_REAR)
        else:
            w = db(x) * (1.0 - g.smoothstep((y - Y1) / (yf1 - Y1)))
        return w * fx
    verts = {v for f in bm.faces if top(f, rl) for v in f.verts if yf0 < v.co.y < yf1 and v.co.x < 0.66}
    new_co = {}
    for v in verts:
        x, y = v.co.x, v.co.y
        y1 = y + delta(x, y)
        if y < Y0 - 1e-6:                                          # bonnet (incl. the rear groove rows)
            z = z_old(x, y1)
        elif y < Y1 - 1e-6 or abs(y - Y1) <= 1e-6:                 # scuttle panel up to the screen base row
            ye, yb = Y0 + delta(x, Y0), Y1 + delta(x, Y1)
            ze, zg = z_old(x, ye), glass(x, yb + S["riser"])
            if ze is None or zg is None:
                continue
            za, zb = ze - S["step"], zg - S["riser"]
            t = min(1.0, max(0.0, (y - Y0) / (Y1 - Y0)))
            z = za + (zb - za) * t
        else:                                                      # riser top, seal and screen
            z = glass(x, y1)
        if z is not None:
            new_co[v] = (y1, z)
    for v, (y1, z) in new_co.items():
        v.co.y, v.co.z = y1, z
    return len(new_co)


def front_cut(bm):
    """Open the loft's front: the lamp panel, lamps, grille and bumper are separate parts (front_end.json).
    * above z_split (indicator top + 3 mm): bonnet and the wing corner over the indicator are trimmed on the
      straight V front edge (centre tip + photo-triangulated outer corner, body_profile front_panel.bonnet_v);
    * below z_split the wing ends on the indicator's wrap-end line (front_taper wb / wt; the plan taper in
      body_geom makes the wing side meet the indicator there);
    * the V edge is turned down as the lip (12 mm, never below the lamp tops);
    * everything of the loft below the bumper top in front of the arches is removed (inside the bumper)."""
    FP = g.PF["front_panel"]; BV = FP["bonnet_v"]; FT = g.PF["front_taper"]
    dz = g.DZ
    z_split = FP["z_split"] + dz
    C = lambda f: f.calc_center_median()
    P0 = Vector((0.0, BV["y0"], 0.0)); nv = Vector((-BV["a"], 1.0, 0.0)).normalized()
    # wrap-end plane: contains the raked wrap line, normal along the tapered wing side (pointing back)
    Wb = Vector(FT["wb"]) + Vector((0, 0, dz)); Wt = Vector(FT["wt"]) + Vector((0, 0, dz))
    side_dir = Vector((FT["slope_back"], 1.0, 0.0)).normalized()
    n = side_dir - side_dir.project(Wt - Wb); n.normalize()
    near_front = lambda f: C(f).y < -1.55
    wing = lambda f: C(f).x > BV["x_shut"] - 0.03
    bisect(bm, Vector((0, 0, z_split)), Vector((0, 0, 1)), lambda f: near_front(f) and wing(f))
    bisect(bm, P0, nv, near_front)
    bisect(bm, Wb, n, lambda f: near_front(f) and wing(f) and C(f).z < z_split + 0.002)
    # under the indicator the wing wraps forward to the lamp panel (closes the slot above the bumper)
    z_ib = FT["wb"][2] + dz
    pb = dict((round(x, 3), y) for x, y in FP["bottom"])
    P1 = Vector((0.663, pb[0.663], FP["z_ref"] + dz)); P2 = Vector((0.70, pb[0.7], FP["z_ref"] + dz))
    npl = (P2 - P1).cross(Vector((0.0, FP["rake"], 1.0))).normalized()
    if npl.y > 0:
        npl = -npl                                       # points forward, out of the panel
    bisect(bm, Vector((0, 0, z_ib)), Vector((0, 0, 1)), lambda f: near_front(f) and wing(f) and C(f).z < z_split)
    bisect(bm, P1, npl, lambda f: near_front(f) and wing(f) and C(f).z < z_ib + 0.002)
    ay, _ = g.arch_centre("front")
    def ahead_of_arch(c, gap=0.004):                     # in front of the front wheel arch lip at this height
        ye = g.arch_edge_y("front", c.z, "front")
        return c.y < ye - gap if ye is not None else c.y < ay
    kill = []
    for f in bm.faces:
        c = C(f)
        if not near_front(f):
            if c.y < -1.40 and c.z - dz < 0.53 and ahead_of_arch(c):
                kill.append(f)                               # lower wing between bumper end and arch: inside the bumper
            continue
        if (c - P0).dot(nv) < -1e-6:
            kill.append(f)                                   # in front of the bonnet / wing-corner V edge
        elif c.z < z_split and c.x > BV["x_shut"] - 0.03 and (
                (c.z > z_ib and (c - Wb).dot(n) < -1e-6) or (c.z <= z_ib and (c - P1).dot(npl) > 1e-6)):
            kill.append(f)                                   # wing in front of the indicator / lamp panel
        elif c.z - dz < 0.53:
            kill.append(f)                                   # inside the bumper
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # lip: extrude the V boundary down, length limited so it stops at the lamp tops (z_split)
    on_v = lambda v: abs((v.co - P0).dot(nv)) < 2e-4 and v.co.z > z_split + 1e-4
    edges = [e for e in bm.edges if e.is_boundary and all(on_v(v) for v in e.verts)]
    if edges:
        res = bmesh.ops.extrude_edge_only(bm, edges=edges)
        new = {v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)}
        for v in new:
            L = max(0.0, min(BV["lip"], v.co.z - z_split))
            v.co += nv * 0.004 * (L / BV["lip"]) + Vector((0, 0, -L))
    # wing front edge beside the indicator: turned in 7 mm (a hemmed panel edge, not a raw cut through the shell)
    on_w = lambda v: abs((v.co - Wb).dot(n)) < 2e-4 and v.co.z < z_split + 1e-4 and v.co.x > BV["x_shut"]
    wedges = [e for e in bm.edges if e.is_boundary and all(on_w(v) for v in e.verts)]
    if wedges:
        bm.normal_update()
        res = bmesh.ops.extrude_edge_only(bm, edges=wedges)
        new = {v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)}
        for v in new:
            src = next((e.other_vert(v) for e in v.link_edges if e.other_vert(v) not in new), None)
            nh = Vector((src.normal.x, src.normal.y, 0.0)) if src is not None else Vector((1, 0, 0))
            nh = nh.normalized() if nh.length > 1e-6 else Vector((1, 0, 0))
            v.co += -nh * 0.007 + n * 0.003
    # the new folds (lip, wing end) shade as hard edges
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.verts[0].co.y < -1.5 and e.calc_face_angle(0.0) > math.radians(35):
            e.smooth = False
    return len(edges)


def rear_cut(bm, z_cut=0.562):
    """The rear bumper is a separate part (rear_end.json): remove the shell below the tail-panel bottom behind the
    rear wheel arch (the old moulded bumper, its ribs and valance)."""
    dz = g.DZ
    ay, _ = g.arch_centre("rear")
    C = lambda f: f.calc_center_median()

    def behind_arch(c, gap=0.004):
        ye = g.arch_edge_y("rear", c.z, "rear")
        return c.y > ye + gap if ye is not None else c.y > ay
    bisect(bm, Vector((0, 0, z_cut + dz)), Vector((0, 0, 1)), lambda f: C(f).y > 1.25)
    kill = [f for f in bm.faces if C(f).y > 1.25 and C(f).z - dz < z_cut and behind_arch(C(f))]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    return len(kill)


def build():
    # exact stations at the vertical lines (door shuts, B-pillar / glass edges, bonnet rear, hatch top)
    ex = []
    for yl in g.SHUT_Y + [YB_REAR, YH]:
        ex += [yl - GAP / 2, yl, yl + GAP / 2]
    bp = g.B_PILLAR
    ex += [bp[0] - 0.012, bp[0], bp[1], bp[1] + 0.012, g.ZN["ws_y"][0], g.ZN["ws_y"][1]]
    if g.SCU:
        ex += [g.Y_A + g.SCU["riser"], g.Y_A + g.SCU["seal"], g.ZN["ws_y"][1] - g.WS_SEAL]
    g.EXTRA_Y[:] = ex
    rs, caps, faces, rows = g.loft()
    bm = bmesh.new()
    vs = [bm.verts.new(p) for r in rs for p in r] + [bm.verts.new(c) for c in caps]
    rl = bm.faces.layers.int.new("row")
    for fi, row in zip(faces, rows):
        f = bm.faces.new([vs[i] for i in fi]); f[rl] = row
    # merge the coincident points clamp_top leaves at each ring's edge so cuts and grooves never meet degenerate faces
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0002)
    bmesh.ops.dissolve_degenerate(bm, dist=0.0002, edges=bm.edges[:])
    bm.faces.ensure_lookup_table()
    C = lambda f: f.calc_center_median()

    # ---- zone cut lines (plain splits) ----
    for line, dy in ((g.APO, 0.0), (g.APO, 0.045), (g.QR, 0.0), (g.QR, -0.012)):
        (y0, z0), (y1, z1) = line
        no = (0.0, -(z1 - z0), (y1 - y0))
        bisect(bm, (0.0, y0 + dy, z0), no, lambda f: g.KEY_BELT <= f[rl] < g.KEY_CANT and min(y0, y1) - 0.25 < C(f).y < max(y0, y1) + 0.25)
    # quarter glass frame line (sloped like the belt)
    yq = 1.0
    bisect(bm, (0.0, yq, g.belt(yq) + g.QUARTER_FRAME), (0.0, -(g.belt(yq + 0.1) - g.belt(yq)) / 0.1, 1.0),
           lambda f: g.KEY_BELT <= f[rl] < g.KEY_CANT and g.B_PILLAR[1] < C(f).y < g.QR[0][0] + 0.05)
    front = lambda f: top(f, rl) and C(f).y < g.ZN["front_face_y"]
    rear = lambda f: top(f, rl) and C(f).y > g.ZN["rear_face_y"]
    hl, ind, gr, tl = g.ZN["headlamp"], g.ZN["indicator"], g.ZN["grille"], g.ZN["tail_lamp"]
    bisect(bm, (tl["x_in"], 0, 0), (1, 0, 0), rear)
    bisect(bm, (tl["x_out"], 0, 0), (1, 0, 0), rear)
    for z in (tl["z"][0], g.ZN["rear_panel_z0"], tl["z"][1]):
        bisect(bm, (0, 0, z), (0, 0, 1), rear)
    HG = g.ZN.get("hatch_glass")
    if HG and g.GP:
        pass                                             # inset panel (glass_panels.py) instead of zone cuts
    elif HG:
        hz = lambda f: top(f, rl) and C(f).y > 1.3 and 0.8 < C(f).z < 1.3
        for z in (HG["z_bot"] - HG["seal"], HG["z_bot"], HG["z_top"], HG["z_top"] + HG["seal"]):
            bisect(bm, (0, 0, z), (0, 0, 1), hz)
        k = (HG["x_top"] - HG["x_bot"]) / (HG["z_top"] - HG["z_bot"])
        for off in (0.0, HG["seal"]):
            bisect(bm, (HG["x_bot"] + off, 0, HG["z_bot"]), (1.0, 0.0, -k), hz)
        bisect(bm, (0, 0, g.ZN["rear_panel_z1"]), (0, 0, 1), rear)
    else:
        for z in g.ZN["hatch_glass_z"]:
            bisect(bm, (0, 0, z), (0, 0, 1), lambda f: top(f, rl) and C(f).y > 1.3 and C(f).z > 0.8)
    sk = g.SKIRT
    for (y0, z0), (y1, z1) in zip(sk, sk[1:]):
        bisect(bm, (0, y0, z0), (0, -(z1 - z0), (y1 - y0)), lambda f, a=y0, b=y1: side(f, rl) and a <= C(f).y <= b and C(f).z < 0.5)

    # ---- grooves: three parallel cuts, the middle line pushed in ----
    grooves = []

    def groove(co, no, keep, w=GAP, d=DEPTH):
        co, no = Vector(co), Vector(no).normalized()
        for o in (-w / 2, 0.0, w / 2):
            bisect(bm, co + no * o, no, keep)
        grooves.append((co, no, keep, w, d))

    def out_of_arch(c, grow=0.012):
        x, y, z = g.finalize((c.x, c.y, c.z))
        return not any(g.in_arch(k, y, z, grow) for k in ("front", "rear"))

    door = lambda yl: (lambda f: 4 <= f[rl] < g.KEY_BELT and abs(C(f).y - yl) < 0.03)
    for yl in g.SHUT_Y:
        grooves.append((Vector((0, yl, 0)), Vector((0, 1, 0)), door(yl), GAP, DEPTH))   # stations already exact
    grooves.append((Vector((0, YB_REAR, 0)), Vector((0, 1, 0)), lambda f: top(f, rl) and C(f).x < XB and abs(C(f).y - YB_REAR) < 0.03, GAP, DEPTH))
    y_bend = YB_REAR
    groove((XB, 0, 0), (1, 0, 0), lambda f: top(f, rl) and -1.74 < C(f).y < y_bend)
    # sunroof seal and the side-skirt top edge
    sr = g.ZN["sunroof"]
    for co, no, keep in () if g.GP else (((sr["x"], 0, 0), (1, 0, 0), lambda f: top(f, rl) and sr["y"][0] - 0.01 < C(f).y < sr["y"][1] + 0.01 and C(f).z > 1.2),
                         ((0, sr["y"][0], 0), (0, 1, 0), lambda f: top(f, rl) and C(f).x < sr["x"] + 0.01 and abs(C(f).y - sr["y"][0]) < 0.03),
                         ((0, sr["y"][1], 0), (0, 1, 0), lambda f: top(f, rl) and C(f).x < sr["x"] + 0.01 and abs(C(f).y - sr["y"][1]) < 0.03)):
        groove(co, no, keep, GAP, 0.003)
    sk = g.SKIRT
    for (y0, z0), (y1, z1) in zip(sk, sk[1:]):
        groove((0, y0, z0), (0, -(z1 - z0), (y1 - y0)), lambda f, a=y0, b=y1: side(f, rl) and a <= C(f).y <= b and C(f).z < 0.5 and out_of_arch(C(f)), 0.004, 0.0025)
    bump_f = lambda f: C(f).y < -1.12 and C(f).z < 0.62 and (side(f, rl) or front(f)) and out_of_arch(C(f))
    bump_r = lambda f: C(f).y > 1.18 and C(f).z < 0.65 and (side(f, rl) or rear(f)) and out_of_arch(C(f))
    groove((0, 0, ZBUMP_R), (0, 0, 1), bump_r)
    for z in RIBS_R:
        groove((0, 0, z), (0, 0, 1), bump_r, RIB_W, RIB_D)
    (xa, ya, za), (xb, yb, zb) = SHUT_TG
    ya += g.SWR and 0.0
    dyz = Vector((0.0, yb - ya, zb - za)).normalized()
    n_tg = Vector((0.0, -dyz.z, dyz.y))                       # in the y-z plane, square to the line
    if n_tg.y < 0:
        n_tg = -n_tg
    # the line ends on the tail-lamp top (TL_TO 0.677, 1.656, 0.80): below that the body corner turns hard and a
    # groove crumpled it; no horizontal shut line across the tailgate (photos c24 / cAR show none at z 0.815)
    # (2026-10-13: the diagonal side shut line is no longer cut in - pushed in along the pillar it creased the
    # surface into an X with the glass edge; the real line is a fine gap that reads at a distance only)
    # (tailgate top shut line across the roof not cut: on the car it sits under the spoiler moulding)

    # ---- materials ----
    mats = ensure_materials()
    for f in bm.faces:
        c = C(f); row = f[rl]
        tk = row - (g.NS - 1) if row >= g.NS - 1 else -1
        f.material_index = g.zone(c.x, c.y, c.z, row, tk)
    for co, no, keep, w, d in grooves:
        for f in bm.faces:
            if keep(f) and abs((C(f) - co).dot(no)) < w / 2 - 1e-6:
                if f.material_index == g.M["paint_gunmetal"] or w == GAP:
                    f.material_index = g.M["panel_gap"]
    # lamp, indicator and grille openings: the shell is cut away there and the lamp units (build_details) sit in
    # the holes with their own lens, reflector and housing
    hl, ind, gr, tl = g.ZN["headlamp"], g.ZN["indicator"], g.ZN["grille"], g.ZN["tail_lamp"]
    inside = lambda c, xr, zr: xr[0] < c.x < xr[1] and zr[0] < c.z < zr[1]
    holes = []
    for f in bm.faces:
        c = C(f)
        if rear(f) and inside(c, (tl["x_in"], tl["x_out"]), tl["z"]):
            holes.append(f)
    bmesh.ops.delete(bm, geom=holes, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    roof = min((f for f in bm.faces if top(f, rl) and abs(C(f).y - 0.4) < 0.02), key=lambda f: C(f).x)
    if roof.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    # groove centre-line vertices, found on the unswept loft (where the cut planes are defined) ...
    push = {}
    for co, no, keep, w, d in grooves:
        for v in {v for f in bm.faces if keep(f) for v in f.verts}:
            if abs((v.co - co).dot(no)) < 1e-6 and v.co.x > 1e-4:
                push[v] = max(push.get(v, 0.0), d)
    if g.SCU:
        warp_scuttle(bm, rl)
    # sharp shoulder crease + hard angles
    for e in bm.edges:
        a, b = e.verts
        if (abs(a.co.z - g.crease_z(a.co.y)) < 1e-6 and abs(b.co.z - g.crease_z(b.co.y)) < 1e-6
                and min(a.co.x, b.co.x) > 0.5):
            e.smooth = False
        elif len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(35):
            e.smooth = False
    # ---- end sweep + model frame ----
    for v in bm.verts:
        v.co = Vector(g.finalize(tuple(v.co)))
    front_cut(bm)
    rear_cut(bm)
    push = {v: d for v, d in push.items() if v.is_valid}
    # ... and pushed in along the final surface normals (after the sweep, so steep corner sweeps can't shear them)
    bm.normal_update()

    def spread(v):                                   # how much the surface turns around v (corner seams)
        ns_ = [f.normal for f in v.link_faces if f.calc_area() > 1e-8]
        return max((a.angle(b_, 0.0) for i, a in enumerate(ns_) for b_ in ns_[i + 1:]), default=0.0)
    moves = {v: v.normal.copy() * d * max(0.0, 1.0 - spread(v) / math.radians(70)) for v, d in push.items()}
    # smooth shading source: the shell before the grooves are pushed in (cuts / folds included, glass dropped below)
    bm_src = bm.copy()
    for v, m_ in moves.items():
        v.co -= m_
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    # zero-area slivers left by the cuts have no normal: the Inner solidify would shoot their vertices metres away
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    for f in bm.faces:
        f.smooth = True
    # inset glass panels: measure the surface, then open the holes they sit in (glass_panels.py)
    pans = []
    if g.GP:
        pans = gp.panels(g.PF, g.DZ)
        pbvh = gp.shell_bvh(bm)
        for P in pans:
            P.prepare()
        # the openings are cut by exact Boolean prisms along each outline (below) - deleting whole faces left a
        # stair-stepped edge that showed through the recess walls
    # glass goes to its own object (one layer, no inner shell under it; AC sorts it as a transparent mesh)
    gi = g.M["glass_tint"]
    bmg = bm.copy()
    bmesh.ops.delete(bmg, geom=[f for f in bmg.faces if f.material_index != gi], context="FACES")
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == gi], context="FACES")
    for f in bmg.faces:
        f.material_index = 0
    meg = bpy.data.meshes.new("BODY_glass"); bmg.to_mesh(meg); bmg.free()
    me = bpy.data.meshes.new("BODY_shell")
    # vertices that take the smooth shading normals: the quarter / C-pillar / tailgate sides, where the zone cuts and
    # shut-line grooves slice the loft (zigzag reflections); never on folds, open edges or sharp edges (there the
    # transfer picks the wrong side and saws the edge)
    bm.verts.index_update()
    xfer_idx = [v.index for v in bm.verts
                if v.co.y > 0.30 and 0.80 + g.DZ < v.co.z < 1.27 + g.DZ and v.co.x > 0.30 and not v.is_boundary
                and all(e.smooth for e in v.link_edges)
                and all(f.normal.angle(v.link_faces[0].normal, 0.0) < math.radians(30) for f in v.link_faces)]
    bm.to_mesh(me); nv, nf = len(bm.verts), len(bm.faces); bm.free()

    ob = bpy.data.objects.get("BODY_shell")
    if ob is None:
        ob = bpy.data.objects.new("BODY_shell", me); bpy.data.collections["BODY"].objects.link(ob)
        m = ob.modifiers.new("Mirror", "MIRROR"); m.use_clip = True; m.use_mirror_merge = True; m.merge_threshold = 1e-4
        for m_ in mats:
            me.materials.append(m_)
    else:
        old = ob.data
        for m_ in old.materials:
            me.materials.append(m_)
        ob.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
        me.name = "BODY_shell"
    for i, m_ in enumerate(mats):
        me.materials[i] = m_
    gl = bpy.data.objects.get("BODY_glass")
    if gl is None:
        gl = bpy.data.objects.new("BODY_glass", meg); bpy.data.collections["BODY"].objects.link(gl)
        mm = gl.modifiers.new("Mirror", "MIRROR"); mm.use_clip = True; mm.use_mirror_merge = True; mm.merge_threshold = 1e-4
    else:
        oldg = gl.data; gl.data = meg
        if oldg.users == 0:
            bpy.data.meshes.remove(oldg)
        meg.name = "BODY_glass"
    meg.materials.append(mats[gi])
    sun = bpy.data.materials.get("glass_sunroof") or bpy.data.materials.new("glass_sunroof")
    sun.use_nodes = True
    next(n for n in sun.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.02, 0.025, 0.03, 1)
    sun.diffuse_color = (0.02, 0.025, 0.03, 1)
    sun["ac_shader"] = "ksPerPixel"; sun["ac_blend"] = 1; sun["ac_depth"] = 1; sun["ac_alpha"] = 0.80   # dark tint + blind
    for P in pans:
        gp.build_meshes(P, pbvh, sun if P.name == "SUNROOF" else mats[gi], mats[g.M["trim_black"]], bpy.data.collections["BODY"],
                        paint_mat=mats[g.M["paint_gunmetal"]])
    # arch cutters from the fitted circles
    cut_coll = bpy.data.collections.get("CUTTERS") or bpy.data.collections.new("CUTTERS")
    if cut_coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(cut_coll)
    for key in ("front", "rear"):
        name = "CUT_arch_" + key
        cb = bmesh.new()
        poly = g.arch_poly(key)                                    # lip outline, closed along its bottom
        seg = len(poly)
        for sx in (1, -1):
            ring0 = [cb.verts.new((sx * 0.50, y, z)) for y, z in poly]
            ring1 = [cb.verts.new((sx * 0.95, v.co.y, v.co.z)) for v in ring0]
            for i in range(seg):
                j = (i + 1) % seg
                cb.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
            cb.faces.new(ring0); cb.faces.new(ring1[::-1])
        bmesh.ops.recalc_face_normals(cb, faces=cb.faces[:])
        co = bpy.data.objects.get(name)
        cm = bpy.data.meshes.new(name); cb.to_mesh(cm); cb.free()
        if co is None:
            co = bpy.data.objects.new(name, cm); cut_coll.objects.link(co)
        else:
            oldm = co.data; co.data = cm
            if oldm.users == 0:
                bpy.data.meshes.remove(oldm)
        co.display_type = "WIRE"; co.hide_render = True; co["no_export"] = 1
        b = ob.modifiers.get(name) or ob.modifiers.new(name, "BOOLEAN")
        b.operation = "DIFFERENCE"; b.object = co; b.solver = "EXACT"
        b.use_hole_tolerant = True          # the shell is open at the front since the front-end split
    # glass openings: prism along the panel normal around its outline (+ margin), from 60 mm outside the surface to
    # 100 mm inside; full width (the outline spans both halves), after the Mirror / Inner modifiers
    for P in pans:
        name = "CUT_glass_" + P.name.lower()
        cb = bmesh.new()
        ring = [P.project(pbvh, u, v) for u, v in gp.offset(P.poly, P.margin)]
        ptop = [cb.verts.new(p + P.N * 0.06) for p in ring]
        pbot = [cb.verts.new(p - P.N * 0.10) for p in ring]
        n_ = len(ring)
        for i in range(n_):
            j = (i + 1) % n_
            cb.faces.new((ptop[i], ptop[j], pbot[j], pbot[i]))
        cb.faces.new(ptop); cb.faces.new(pbot[::-1])
        bmesh.ops.recalc_face_normals(cb, faces=cb.faces[:])
        co = bpy.data.objects.get(name)
        cm = bpy.data.meshes.new(name); cb.to_mesh(cm); cb.free()
        cm.materials.append(mats[g.M["paint_gunmetal"]])          # the cut edge between the shell layers: paint
        if co is None:
            co = bpy.data.objects.new(name, cm); cut_coll.objects.link(co)
        else:
            oldm = co.data; co.data = cm
            if oldm.users == 0:
                bpy.data.meshes.remove(oldm)
        co.display_type = "WIRE"; co.hide_render = True; co["no_export"] = 1
        b = ob.modifiers.get(name) or ob.modifiers.new(name, "BOOLEAN")
        b.operation = "DIFFERENCE"; b.object = co; b.solver = "EXACT"; b.use_hole_tolerant = True
        b.material_mode = "TRANSFER"
    # shading normals from the smooth source: the zone cuts (quarter glass edge, shut lines) slice the loft into
    # slivers whose own normals shade as zigzags; the outer skin (within 6 mm, so grooves included and the inner
    # layer excluded) takes the source's interpolated corner normals - panel gaps stay visible by their black material
    bmesh.ops.remove_doubles(bm_src, verts=bm_src.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm_src, dist=1e-5, edges=bm_src.edges[:])
    for f in bm_src.faces:
        f.smooth = True
    sname = "BODY_normals_src"
    sme = bpy.data.meshes.new(sname); bm_src.to_mesh(sme); bm_src.free()
    so = bpy.data.objects.get(sname)
    if so is None:
        so = bpy.data.objects.new(sname, sme); cut_coll.objects.link(so)
        sm = so.modifiers.new("Mirror", "MIRROR"); sm.use_clip = True; sm.use_mirror_merge = True; sm.merge_threshold = 1e-4
    else:
        oldm = so.data; so.data = sme
        if oldm.users == 0:
            bpy.data.meshes.remove(oldm)
    so.display_type = "WIRE"; so.hide_render = True; so["no_export"] = 1
    vg = ob.vertex_groups.get("xfer") or ob.vertex_groups.new(name="xfer")
    vg.remove(list(range(len(ob.data.vertices))))
    vg.add(xfer_idx, 1.0, "REPLACE")
    dt = ob.modifiers.get("SmoothNormals") or ob.modifiers.new("SmoothNormals", "DATA_TRANSFER")
    dt.object = so
    dt.use_loop_data = True
    dt.data_types_loops = {"CUSTOM_NORMAL"}
    dt.loop_mapping = "POLYINTERP_LNORPROJ"
    dt.vertex_group = "xfer"
    dt.use_max_distance = True
    dt.max_distance = 0.006
    dt.mix_factor = 1.0
    while ob.modifiers.find("SmoothNormals") < len(ob.modifiers) - 1:      # last in the stack (after the cuts)
        ob.modifiers.move(ob.modifiers.find("SmoothNormals"), ob.modifiers.find("SmoothNormals") + 1)
    return {"stations": len(rs), "verts": nv, "faces": nf, "modifiers": [m.name for m in ob.modifiers]}


if __name__ == "__main__":
    print(build())
