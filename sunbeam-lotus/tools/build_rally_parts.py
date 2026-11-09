"""Rally parts added onto the imported stock Sunbeam model (runs in Blender, on
sunbeam_rally_on_stock_model.blend after kn5_import).

Model space here is the stock kn5's: Blender Z up, front -Y, wheel centres at z 0.145
(ground ~ -0.155), left = +X. Reference: Nick's photos (yellow/green car with
body-colour flared arches, 8-spoke wheels, four spot lamps, black mud flaps).

  * RALLY_flares   body-colour arch flares, shaped round the stock arch openings
                   (measured from the stock carPaint meshes), stock carPaint material
                   with UVs copied from the nearest body vertex -> takes each skin's paint
  * RALLY_RIM_xx   8-spoke rims (13", fit the stock tyres) under the stock RIM_xx; the
                   stock rim meshes are left out of the export (no_export)
  * stock tyres    12% wider on the axle (they move out with the wider physics track)
  * RALLY_lamps    two 190 mm + two 150 mm spot lamps on a bar in front of the grille
  * RALLY_mudflaps black flaps behind all four wheels (stock black plastic material)
Everything symmetric is built on the left and mirrored.
"""
import importlib.util
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, kdtree

TOOLS = r"D:\Claude\talbot_sunbeam_lotus\tools"
HUB = 0.145
WHEELS = {"LF": (0.665, -1.212), "LR": (0.675, 1.207)}          # (x, y) of the left wheels
# stock arch opening, measured: angle (deg, 0 = towards the front, 90 = top) -> radius from the hub
OPEN = {"LF": [(-15, 0.370), (-8, 0.360), (7, 0.343), (22, 0.340), (37, 0.328), (52, 0.314), (67, 0.303),
               (82, 0.299), (97, 0.296), (112, 0.296), (127, 0.299), (142, 0.301), (157, 0.304), (172, 0.313),
               (188, 0.325), (195, 0.332)],
        "LR": [(-15, 0.350), (-8, 0.343), (7, 0.334), (22, 0.334), (37, 0.332), (52, 0.328), (67, 0.323),
               (82, 0.320), (97, 0.320), (112, 0.322), (127, 0.324), (142, 0.325), (157, 0.327), (172, 0.336),
               (188, 0.345), (195, 0.350)]}
LIP_OUT = 0.042          # flare lip stands this far proud of the body side (v0.5 had ~0.06 + a wider spread)
FLARE_W = 0.075          # how far the flare spreads onto the body beyond the opening
TYRE_CLEAR = 0.012       # tyre outer edge sits this far inside the lip
SILL_Z = 0.095           # stock sill bottom is z ~0.10-0.12, tucked in to x ~0.71
# each flare end: ("taper", z) stops at height z and tapers away (front arch at the bumper, rear arch at the
# rear valance); ("sweep", z) leaves the arch at height z and turns along the sill in one continuous surface -
# the lip curves round (FILLET_R) and runs SWEEP_LEN along the sill bottom, fading to nothing (the blend Nick
# asked for instead of a full-length skirt)
# ("cut" ends: full size to the end - flare_rings() trims them at JOIN_TRIM and build_lips lofts them into the
#  splitter lips; the lip running up the arch under a tapered flare end looked messy - Nick)
# The rear arch's rear end SWEEPS (fillet radius, straight run) round to run back along the bottom of the quarter
# panel: coming down the arch the flare's section lies fore-and-aft, the splitter lip's up-and-down, and a loft
# straight from one to the other had to turn it through 90 degrees (messy - Nick); after the sweep it lies like the
# lip's (flush edge up, proud edge down, as on the sill) and the loft only changes its shape.
# (the rear sweep's radius must exceed the flare's width, 75 mm, or the section folds over itself round the bend -
#  a 70 mm radius crumpled it; leaving the arch higher, at z 0.23, lands it on the quarter panel's bottom edge)
FLARE_ENDS = {"LF": (("cut", 0.20), ("sweep", 0.19)), "LR": (("sweep", 0.19), ("sweep", 0.23, 0.110, 0.030))}
JOIN_TRIM = {"front": 0.25, "rear": 0.17}     # z of the flare's opening edge where a "cut" end hands over
FILLET_R = 0.095
SWEEP_LEN = 0.14
# (Nick 2026-09-28: join everything up) the sweep ends settle at SILL_E and one small lip carries on along the sill
# from arch to arch (before the ease curve applied at the end of flare_path: 0.45 -> 0.425). The taper ends still
# go to nothing (FLARE_END_E 0): the splitter lips (build_lips.py) run up the arch edge under them instead - ending
# the flare at a set size where a lip met it left a visible step, and running it lower folded it over the corner.
FLARE_END_E = 0.0
SILL_E = 0.45
AC_TYRE_X = {"LF": 0.7125, "LR": 0.719}   # tyre centres in AC (physics track / 2) - the model's are further in
TYRE_W = 0.251
PAINT_UV_AT = (0.80, -1.20, 0.60)   # a clean spot on the front wing: every flare vertex uses its paint UV
TYRE_R = 0.295           # physics tyre radius the grafted wheels are scaled to
DONOR = "DONOR_MK2"      # Escort Mk2 rally spec (Alan Mc Enroe) imported with kn5_import(primary=False)


def load(name):
    spec = importlib.util.spec_from_file_location(name, rf"{TOOLS}\{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def interp(pts, a):
    if a <= pts[0][0]:
        return pts[0][1]
    for (a0, v0), (a1, v1) in zip(pts, pts[1:]):
        if a0 <= a <= a1:
            return v0 + (v1 - v0) * (a - a0) / (a1 - a0)
    return pts[-1][1]


def kn5(name):
    return next(o for o in bpy.data.objects if o.get("kn5_name") == name)


def world_pts(o):
    n = len(o.data.vertices)
    c = np.empty(n * 3, np.float32); o.data.vertices.foreach_get("co", c); c = c.reshape(-1, 3)
    m = np.array(o.matrix_world); return c @ m[:3, :3].T + m[:3, 3]


class BodySampler:
    """Stock carPaint surface on the car's left: side x at a (y, z) point, and the UV there."""
    def __init__(self):
        pts, uvs = [], []
        for o in bpy.data.collections["STOCK_MODEL"].objects:
            # original stock body panels only - never our own flares (same material) or grafted parts
            if (o.type == "MESH" and o.get("kn5_class") == 2 and not o.get("rally_graft") and not o.get("rally_lamp")
                    and not o.name.startswith("RALLY_") and o.data.materials and o.data.materials[0].name == "carPaint"):
                p = world_pts(o)
                lv = np.empty(len(o.data.loops), np.int64); o.data.loops.foreach_get("vertex_index", lv)
                uv = np.empty(len(o.data.loops) * 2, np.float32); o.data.uv_layers.active.data.foreach_get("uv", uv)
                vuv = np.zeros((len(p), 2), np.float32); vuv[lv] = uv.reshape(-1, 2)
                keep = p[:, 0] > 0.5
                pts.append(p[keep]); uvs.append(vuv[keep])
        self.p, self.uv = np.concatenate(pts), np.concatenate(uvs)
        self.kd = kdtree.KDTree(len(self.p))
        for i, q in enumerate(self.p):
            self.kd.insert(q, i)
        self.kd.balance()
        self.kd_yz = kdtree.KDTree(len(self.p))
        for i, q in enumerate(self.p):
            self.kd_yz.insert((0.0, q[1], q[2]), i)
        self.kd_yz.balance()

    def _bvh(self):
        if getattr(self, "bvh", None) is None:
            from mathutils.bvhtree import BVHTree
            verts, polys = [], []
            for o in bpy.data.collections["STOCK_MODEL"].objects:
                if (o.type == "MESH" and o.get("kn5_class") == 2 and not o.get("no_export") and not o.get("rally_graft")
                        and not o.get("rally_lamp") and not o.name.startswith("RALLY_") and o.data.materials
                        and o.data.materials[0].name in ("carPaint", "carPaint_2")):
                    base = len(verts)
                    verts += [tuple(v) for v in world_pts(o)]
                    polys += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
            self.bvh = BVHTree.FromPolygons(verts, polys)
        return self.bvh

    def side_x(self, y, z):
        """Body side at (y, z): a ray from outside the car straight in (-X) onto the stock paintwork. (The old
        estimate - max x of the nearest vertices - sat several cm off the surface where the wing's polygons are
        big: the flare stood off the body at the top of the arch.)"""
        hit = self._bvh().ray_cast(Vector((1.3, y, z)), Vector((-1.0, 0.0, 0.0)), 0.75)
        if hit[0] is not None:
            return hit[0].x
        near = self.kd_yz.find_n((0.0, y, z), 12)
        return max(self.p[i][0] for _, i, _ in near)

    def uv_at(self, p):
        return self.uv[self.kd.find(p)[1]]


def replace(name, bm, materials, parent, mirror=True):
    old = bpy.data.objects.get(name)
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old and me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(70):
            e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["STOCK_MODEL"].objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    if mirror:
        md = ob.modifiers.new("Mirror", "MIRROR"); md.use_axis = (True, False, False); md.use_mirror_merge = False
    return ob


# flare cross-section: (fraction of the flare width out from the opening, fraction of LIP_OUT proud of the body)
# - a rounded lip that rolls over and eases back onto the body
SECTION = [(0.000, 0.55), (0.010, 0.88), (0.030, 1.00), (0.070, 1.00), (0.160, 0.95), (0.300, 0.80),
           (0.460, 0.58), (0.620, 0.36), (0.780, 0.17), (0.900, 0.06), (1.000, 0.00)]
STEPS = 120


def smooth(a, sigma):
    """Gaussian smoothing along axis 0 (edge values held)."""
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    pad = np.concatenate([np.repeat(a[:1], r, 0), a, np.repeat(a[-1:], r, 0)])
    return np.stack([np.convolve(pad[:, j], k, mode="valid") for j in range(a.shape[1])], axis=1)


def _rotate(v, a):
    c, s = math.cos(a), math.sin(a)
    return np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])


def flare_path(tag):
    """Centre-line stations of one flare in the side view: (y, z) of the lip line, unit section direction
    (pointing away from the wheel - the flare spreads that way), and ease (lip height 0..1, width follows).
    Arc part follows the arch opening; 'sweep' ends continue with a fillet that turns the line to run along the
    sill, then a short straight, both fading out."""
    prof = OPEN[tag]
    yw = WHEELS[tag][1]
    r_end = interp(prof, 0) + FLARE_W
    lim = lambda z: math.degrees(math.asin(max(-1.0, min(1.0, (z - HUB) / r_end))))
    (kind0, z0, *opt0), (kind1, z1, *opt1) = FLARE_ENDS[tag]
    opts = {0: opt0, 1: opt1}
    a0, a1 = lim(z0), 180.0 - lim(z1)
    angles = np.linspace(a0, a1, STEPS + 1)
    r_open = smooth(np.array([[interp(prof, a)] for a in angles]), 4.0)[:, 0]
    st = []
    for a, r in zip(np.radians(angles), r_open):
        st.append({"p": np.array([yw - r * math.cos(a), HUB + r * math.sin(a)]),
                   "d": np.array([-math.cos(a), math.sin(a)]), "e": 1.0})
    for side, kind, a_end in ((0, kind0, a0), (1, kind1, a1)):
        seq = st if side == 1 else st[::-1]              # travel towards this end
        n_t = 16
        if kind == "cut":
            continue
        if kind == "taper":
            for k in range(n_t):                          # last n_t stations taper down to the lips' size
                seq[-(k + 1)]["e"] = min(seq[-(k + 1)]["e"], FLARE_END_E + (1 - FLARE_END_E) * (k / n_t))
            continue
        # sweep: fillet from the current heading round to run along the sill, away from the wheel
        fillet_r, sweep_len = (opts[side] if opts[side] else (FILLET_R, SWEEP_LEN))
        p, d = seq[-1]["p"].copy(), seq[-1]["d"].copy()
        tangent = seq[-1]["p"] - seq[-2]["p"]; tangent /= np.linalg.norm(tangent)
        away = np.array([1.0 if p[0] > yw else -1.0, 0.0])
        turn = math.atan2(tangent[0] * away[1] - tangent[1] * away[0], tangent @ away)
        n_f, n_s = 18, 12
        total = fillet_r * abs(turn) + sweep_len
        run = 0.0
        for k in range(1, n_f + n_s + 1):
            if k <= n_f:
                da = turn / n_f
                ds = fillet_r * abs(da)
                tangent = _rotate(tangent, da / 2); p = p + tangent * ds; tangent = _rotate(tangent, da / 2)
                d = _rotate(d, da)
            else:
                ds = sweep_len / n_s
                p = p + tangent * ds
            run += ds
            t = run / total
            seq.append({"p": p.copy(), "d": d.copy(), "e": SILL_E + (1 - SILL_E) * (1.0 - t * t * (3 - 2 * t))})
        if side == 0:
            st = seq[::-1]
        else:
            st = seq
    for s in st:
        s["e"] = s["e"] * s["e"] * (3 - 2 * s["e"])
    return st


def flare_and_sill():
    """One continuous lip per side: front flare (front end -> arch -> sweep into the sill), a small lip along the
    sill at the sweeps' end size, rear flare (sweep off the sill -> arch -> rear end)."""
    f, r = flare_path("LF"), flare_path("LR")
    pa, pb = f[-1], r[0]
    n = max(2, int(abs(pb["p"][0] - pa["p"][0]) / 0.012))
    sill = []
    for i in range(1, n):
        u = i / n
        d = pa["d"] * (1 - u) + pb["d"] * u
        sill.append({"p": pa["p"] * (1 - u) + pb["p"] * u, "d": d / np.linalg.norm(d),
                     "e": pa["e"] * (1 - u) + pb["e"] * u})
    return f + sill + r


def flare_ends(run=0.06):
    """The arch edge from the front flare's front end, and from the rear flare's rear end, `run` metres up the
    arch: [(y, z), ...] starting at the end - the splitter lips carry on along it, tucked under the flare."""
    out = {}
    for key, st in (("front", flare_path("LF")), ("rear", flare_path("LR")[::-1])):
        pts, s = [tuple(float(v) for v in st[0]["p"])], 0.0
        for a, b in zip(st, st[1:]):
            s += float(np.linalg.norm(b["p"] - a["p"]))
            pts.append(tuple(float(v) for v in b["p"]))
            if s >= run:
                break
        out[key] = pts
    return out


def flare_rings(body):
    """Section rings (left side) of flare + sill + flare, trimmed at JOIN_TRIM at both arch ends: [[(x, y, z) x 12]]
    in section order [tucked, SECTION f=0 (opening edge) .. f=1 (flush on the body)]."""
    st = flare_and_sill()
    nsec = len(SECTION)
    yz = np.zeros((len(st), nsec, 2)); xb = np.zeros((len(st), nsec))
    for i, s in enumerate(st):
        width = FLARE_W * (0.35 + 0.65 * s["e"]) * min(1.0, 4.0 * s["e"])
        for j, (f, _) in enumerate(SECTION):
            y, z = s["p"] + s["d"] * f * width
            z = max(z, SILL_Z)
            yz[i, j] = (y, z)
            xb[i, j] = body.side_x(y, max(z, 0.115))
    xb = smooth(xb, 5.0)
    rings = []
    for i, s in enumerate(st):
        ring = [(float(xb[i, 0] - 0.015), float(yz[i, 0, 0]), float(yz[i, 0, 1]))]
        for j, (_, o) in enumerate(SECTION):
            ring.append((float(xb[i, j] + LIP_OUT * s["e"] * o + (0.002 if j == nsec - 1 else 0.0)),
                         float(yz[i, j, 0]), float(yz[i, j, 1])))
        rings.append(ring)
    z_edge = [r[1][2] for r in rings]
    i0, i1 = 0, len(rings) - 1
    if FLARE_ENDS["LF"][0][0] == "cut":
        i0 = next(i for i in range(len(rings)) if z_edge[i] >= JOIN_TRIM["front"])
    if FLARE_ENDS["LR"][1][0] == "cut":
        i1 = next(i for i in range(len(rings) - 1, -1, -1) if z_edge[i] >= JOIN_TRIM["rear"])
    return rings[i0:i1 + 1]


def build_flares(body):
    """Per arch: a rounded lip standing LIP_OUT proud of the body along the opening, easing back onto the body
    FLARE_W out. Body-side samples are smoothed along the flare (raw samples of the stock mesh are noisy - the
    jagged v0.6 edges). Ends either taper away or sweep round into the sill (see FLARE_ENDS)."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    paint_uv = body.uv_at(PAINT_UV_AT)
    nsec = len(SECTION)
    for st in (flare_and_sill(),):
        yz = np.zeros((len(st), nsec, 2)); xb = np.zeros((len(st), nsec))
        for i, s in enumerate(st):
            width = FLARE_W * (0.35 + 0.65 * s["e"]) * min(1.0, 4.0 * s["e"])   # ends pinch to a point
            for j, (f, _) in enumerate(SECTION):
                y, z = s["p"] + s["d"] * f * width
                z = max(z, SILL_Z)
                yz[i, j] = (y, z)
                xb[i, j] = body.side_x(y, max(z, 0.115))
        xb = smooth(xb, 5.0)
        rings = []
        for i, s in enumerate(st):
            ring = [(xb[i, 0] - 0.015, yz[i, 0, 0], yz[i, 0, 1])]           # tucked in behind the lip
            for j, (_, o) in enumerate(SECTION):
                ring.append((xb[i, j] + LIP_OUT * s["e"] * o + (0.002 if j == nsec - 1 else 0.0),
                             yz[i, j, 0], yz[i, j, 1]))
            rings.append([bm.verts.new(q) for q in ring])
        n = len(rings[0])
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(n - 1):
                bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
        bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = paint_uv
    return bm


# The stock fog lamp's glass (SUB1 front, SUB0 fluted lens) is amber "rgbaffb25f99" drawn OPAQUE and its reflector
# (SUB4) solid amber, so with the covers off the lamps looked like amber discs - covers again (Nick). Re-dressed with
# lamp-only copies of the car's own clear windscreen glass and a polished-metal reflector (own copies, so CSP's
# lamp glow can never spill onto the windscreen or headlights sharing a material).
LAMP_DRESS = {
    # (Nick 2026-09-28: first version "very reflective / mirror-like" - toned down: reflector spec 1.6->0.8,
    #  fresnel 0.7/1.0 -> 0.3/0.55; glass spec 2.0->1.3, fresnel max 0.7->0.45)
    "SUB1": ("RALLY_spot_glass", "glass", {"props": {"ksSpecular": 1.3, "fresnelMaxLevel": 0.45}}),
    "SUB0": ("RALLY_spot_glass", "glass", {"props": {"ksSpecular": 1.3, "fresnelMaxLevel": 0.45}}),
    "SUB4": ("RALLY_spot_reflector", "glass", {"blend": 0, "texture": "rgba8c8d8dff.dds",
                                                "props": {"ksAmbient": 0.3, "ksDiffuse": 0.35, "ksSpecular": 0.8,
                                                          "ksSpecularEXP": 120.0, "fresnelC": 0.3,
                                                          "fresnelMaxLevel": 0.55}}),
}


def spot_material(name, base, change):
    """A new kn5 material copied from a stock one's full definition (so the exporter writes it verbatim)."""
    import json
    src = next(mat for mat in bpy.data.materials if "kn5_def" in mat and json.loads(mat["kn5_def"])["name"] == base)
    d = json.loads(src["kn5_def"])
    d["name"] = name
    if "blend" in change:
        d["blend"] = change["blend"]
    if "texture" in change:
        d["samplers"] = [[s, slot, change["texture"] if s == "txDiffuse" else t] for s, slot, t in d["samplers"]]
    for p in d["props"]:
        if p[0] in change.get("props", {}):
            p[1] = change["props"][p[0]]
    m = bpy.data.materials.get(name)
    if m is None:
        m = src.copy()
        m.name = name
    m["kn5_def"] = json.dumps(d)          # always rewritten, so edits to LAMP_DRESS take effect on rebuilds
    return m


def build_spot_lamps():
    """Four spot lamps made from copies of the stock Sunbeam fog lamp (housing, chrome bezel, reflector,
    fluted lens, front glass - its own materials), scaled up, on a black bar; the stock fog lamps behind
    them are left out. Left lamps copy the left fog lamp, right lamps the right one (no mirrored copies)."""
    stock_c = {"L": Vector((0.261, -1.930, 0.475)), "R": Vector((-0.261, -1.930, 0.475))}
    front_y_offset = -0.029                      # stock lamp front face relative to its centre
    lamps = [("U", 0.215, 0.455, 0.190, -2.010), ("D", 0.335, 0.262, 0.150, -1.990)]   # name, |x|, z, dia, face y
    # (not "foglightl_a__slod": that is the stock lamp's matt-grey stone-guard COVER - it sits over the lens, so with
    #  it the lamps could never be seen to light up)
    parts = ("foglightl_a_SUB3", "foglightl_a_SUB4", "glasslfl_a_SUB0", "glasslfl_a_SUB1")
    meshes = lambda root: [o for o in root.children_recursive if o.type == "MESH"]
    left = {p: next(o for o in meshes(kn5("EXT_FOGLIGHT_L_STOCK")) if o.get("kn5_name") == p) for p in parts}

    def source(side, pname):
        if side == "L":
            return left[pname]
        ref = left[pname]                          # right lamp: same material, closest vertex count
        cands = [o for o in meshes(kn5("EXT_FOGLIGHT_R_STOCK")) if o.data.materials
                 and o.data.materials[0] == ref.data.materials[0]]
        return min(cands, key=lambda o: abs(len(o.data.vertices) - len(ref.data.vertices)))

    made, lens_names = [], []
    for o in [o for o in bpy.data.objects if not o.users_collection]:
        bpy.data.objects.remove(o)                 # strays from an interrupted run
    for side in ("L", "R"):
        stock = kn5(f"EXT_FOGLIGHT_{side}_STOCK")
        for c in stock.children_recursive:
            c["no_export"] = True
            if c.name in bpy.context.view_layer.objects:
                c.hide_set(True)
        for c in stock.children:
            c["no_export"] = True
        for o in [o for o in bpy.data.objects if o.get("rally_lamp") == side]:
            bpy.data.objects.remove(o)
        sgn = 1 if side == "L" else -1
        for tag, ax, z, dia, face_y in lamps:
            k = dia / 0.148
            target = Vector((sgn * ax, face_y - front_y_offset * k, z))
            M = Matrix.Translation(target) @ Matrix.Scale(k, 4) @ Matrix.Translation(-stock_c[side])
            for pname in parts:
                src = source(side, pname)
                ob = src.copy(); ob.data = src.data.copy()
                bpy.data.collections["STOCK_MODEL"].objects.link(ob)
                ob.parent = kn5("UNIVERS")
                ob.matrix_world = M @ src.matrix_world
                name = f"RALLY_SPOT_{side}{tag}_{pname.split('_', 1)[1]}"
                ob["kn5_name"] = name
                ob["kn5_order"] = 2 * 10 ** 6 + len(made)
                ob["kn5_pristine"] = False
                ob["rally_lamp"] = side
                if "no_export" in ob:
                    del ob["no_export"]            # copied from a stock lamp that is itself left out
                ob.hide_set(False)
                dress = LAMP_DRESS.get(pname.split("_a_", 1)[1] if "_a_" in pname else "")
                if dress:
                    ob.data.materials[0] = spot_material(*dress)
                made.append(ob.name)
                if pname == "glasslfl_a_SUB0":
                    lens_names.append(name)
    # mounting bar + brackets (stock black plastic)
    old = bpy.data.objects.get("RALLY_lamps")
    if old:
        bpy.data.objects.remove(old)
    wd = load("build_details")
    bm = bmesh.new()
    wd.add_cyl(bm, (0.0, -1.945, 0.345), 0.013, 0.80, "X", mi=0, segments=16)
    for _, ax, z, dia, face_y in lamps:
        z_edge = z - dia / 2 if z > 0.345 else z + dia / 2
        wd.add_box(bm, ax - 0.011, ax + 0.011, -1.955, -1.935, min(z_edge, 0.345), max(z_edge, 0.345), 0)
        wd.add_cyl(bm, (ax, -1.945, z), 0.018, 0.03, "Y", mi=0, segments=12)       # lamp pivot boss
    made.append(replace("RALLY_lamp_bar", bm, [bpy.data.materials["plastic_textured_002"]], kn5("UNIVERS")).name)
    return made, lens_names


def valance_edge(end, x_max, step=0.02):
    """The stock body-colour valance's bottom edge at the nose (end=-1) or tail (+1): per x, the edge point and the
    point on the panel 30 mm above it (gives the panel's slope), smoothed."""
    P = []
    for o in bpy.data.collections["STOCK_MODEL"].objects:
        if (o.type == "MESH" and o.get("kn5_class") == 2 and not o.get("no_export") and o.data.materials
                and o.data.materials[0].name == "carPaint"):
            p = world_pts(o)
            P.append(p[(p[:, 1] * end > 1.50) & (p[:, 2] < 0.40)])
    P = np.concatenate(P)
    rows = []
    pick = (lambda a: a[:, 1].min()) if end < 0 else (lambda a: a[:, 1].max())
    for x in np.arange(0.0, x_max + 0.05, 0.01):
        b = P[np.abs(np.abs(P[:, 0]) - x) < 0.03]
        if not len(b):
            continue                                   # the valance is big polygons - bins can fall between vertices
        zmin = b[:, 2].min()
        e = b[b[:, 2] < zmin + 0.008]
        u = b[np.abs(b[:, 2] - (zmin + 0.03)) < 0.012]
        rows.append([x, pick(e), zmin, pick(u) if len(u) else pick(e) - end * 0.02, zmin + 0.03])
    a = np.array(rows)
    xs = np.arange(0.0, x_max + 1e-6, step)
    # robust fit in x^2 (the car is symmetric): cutouts in the valance (tow eye, etc.) are dropped as outliers,
    # so the lip follows the panel's overall line instead of rippling over every notch
    cols = [xs]
    for j in range(1, 5):
        keep = np.ones(len(a), bool)
        for _ in range(3):
            c = np.polyfit(a[keep, 0] ** 2, a[keep, j], 3)
            res = a[:, j] - np.polyval(c, a[:, 0] ** 2)
            keep = np.abs(res) < max(2.0 * res[keep].std(), 0.002)
        cols.append(np.polyval(c, xs ** 2))
    return np.stack(cols, axis=1)                      # columns: x, y_edge, z_edge, y_up, z_up


def body_outline(end, z_lo, z_hi, x_max, step=0.03):
    """Plan outline of the body's nose (end=-1) or tail (end=+1): extreme y per |x|, from stock meshes."""
    pts = []
    for o in bpy.data.collections["STOCK_MODEL"].objects:
        if (o.type == "MESH" and o.get("kn5_class") == 2 and not o.get("no_export") and not o.get("rally_graft")
                and not o.get("rally_lamp") and not o.name.startswith("RALLY_")):
            p = world_pts(o)
            pts.append(p[(p[:, 2] > z_lo) & (p[:, 2] < z_hi) & (p[:, 1] * end > 1.5)])
    P = np.concatenate(pts)
    # a smooth fitted curve, not the raw extremes (plates, brackets and lamp mounts made the raw outline wavy):
    # y(x) = y_centre - end * sweep * (x / x_max)^4, with y_centre and sweep from robust percentiles
    def extreme(x0, x1):
        b = P[(np.abs(P[:, 0]) >= x0) & (np.abs(P[:, 0]) < x1), 1]
        return float(np.percentile(b, 3 if end < 0 else 97))
    y_c, y_e = extreme(0.0, 0.35), extreme(x_max - 0.06, x_max)
    xs = np.linspace(0.0, x_max, 25)
    return np.stack([xs, y_c + (y_e - y_c) * (xs / x_max) ** 4], axis=1)


def lip_mesh(edge, end, drop, reach, x_fade0, x_end, paint_uv, blade=None):
    """A body-colour lip grown from a valance's bottom edge: it starts 10 mm up the panel (just proud of it),
    carries on the panel's own slope, then curves `reach` outwards (end=-1: forwards, +1: rearwards) while dropping
    `drop`. Height fades to nothing between x_fade0 and x_end so it melts into the corners. Returns (bm, bottom
    line) - the bottom line is where a blade attaches."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows, bottom = [], []
    for x, ye, ze, yu, zu in (map(float, r) for r in edge):
        if x > x_end:
            break
        t = 0.0 if x <= x_fade0 else min(1.0, (x - x_fade0) / (x_end - x_fade0))
        k = 1.0 - t * t * (3 - 2 * t)
        E = Vector((0.0, ye, ze))
        d = (E - Vector((0.0, yu, zu))).normalized()           # down the panel
        start = E - d * 0.010 + Vector((0.0, end * 0.0015, 0.0))
        B = E + Vector((0.0, end * reach * k, -drop * k))
        C = E + d * (0.35 * drop * k)                            # keeps the panel's slope before bending out
        pts = [start]
        for s in (i / 6 for i in range(7)):
            q = (1 - s) ** 2 * (E + Vector((0.0, end * 0.0015, 0.0))) + 2 * (1 - s) * s * C + s * s * B
            pts.append(q)
        inner = B + Vector((0.0, -end * 0.012, 0.004))           # thickness: the lip's back face
        pts.append(inner)
        pts.append(E + Vector((0.0, -end * 0.018, 0.004)))
        rows.append([bm.verts.new((x, p.y, p.z)) for p in pts])
        bottom.append((x, B.y, B.z, k))
    n = len(rows[0])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(n - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]) if end < 0 else (r0[j], r0[j + 1], r1[j + 1], r1[j]))
    bm.faces.new(rows[-1] if end < 0 else list(reversed(rows[-1])))
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = paint_uv
    return bm, bottom


def blade_mesh(bottom, end, proud, under, thick=0.006, strakes=(), x_max=None):
    """Thin black blade along a lip's bottom line: `proud` beyond it, `under` back beneath the car."""
    bm = bmesh.new()
    rows = []
    for x, y, z, k in bottom:
        if k < 0.25 or (x_max is not None and x > x_max):
            break
        p = proud * (0.4 + 0.6 * k)
        rows.append([bm.verts.new((x, y + end * p, z - thick)), bm.verts.new((x, y + end * p, z)),
                     bm.verts.new((x, y - end * under, z)), bm.verts.new((x, y - end * under, z - thick))])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(4):
            bm.faces.new((r0[j], r0[(j + 1) % 4], r1[(j + 1) % 4], r1[j]))
    bm.faces.new(list(reversed(rows[-1])))
    if strakes:
        wd = load("build_details")
        y0, z0 = bottom[0][1], bottom[0][2]
        for x in strakes:
            wd.add_box(bm, x - 0.004, x + 0.004, min(y0 + end * proud, y0 - end * under),
                       max(y0 + end * proud, y0 - end * under), z0 - thick - 0.03, z0 - thick, 0)
    return bm


def build_splitters():
    """Front and rear lips that grow out of the stock body-colour valances (so they read as part of the car),
    each finished with a thin black blade; rear gets two diffuser strakes a side. Left half, mirrored."""
    body = BodySampler()
    paint_uv = body.uv_at(PAINT_UV_AT)
    for old in ("RALLY_skirts", "RALLY_splitter_front", "RALLY_splitter_rear", "RALLY_lip_front", "RALLY_lip_rear",
                "RALLY_blade_front", "RALLY_blade_rear"):
        o = bpy.data.objects.get(old)
        if o:
            bpy.data.objects.remove(o)
    # v1 (lip_mesh/blade_mesh, kept above): lips only across the valances, fading out short of the arches, the front
    # one dropped 50 mm and looked detached (Nick). Now they run round to the flares' ends (build_lips.py).
    import types
    brp = types.SimpleNamespace(world_pts=world_pts, valance_edge=valance_edge, kn5=kn5, replace=replace)
    return load("build_lips").build(brp, body, paint_uv, flare_ends())


def tyre_material(name, stock_def, diffuse, normal, donor_dir):
    """ksTyres version of a donor tyre texture set (AC/CSP find a car's tyres by this shader)."""
    import json
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m["kn5_def"] = json.dumps({"name": name, "shader": "ksTyres", "blend": 0, "alphaTested": 0, "depth": 0,
                               "props": stock_def["props"],
                               "samplers": [["txDiffuse", 0, diffuse], ["txNormal", 1, normal], ["txDirty", 2, diffuse],
                                            ["txBlur", 3, diffuse], ["txNormalBlur", 4, normal]],
                               "tex_dir": donor_dir})
    return m


def _axis_fit(P):
    """Spin axis (unit, pointing +X-ish) and centre of a round part: the smallest-variance direction of its vertices."""
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    a = vt[2] / np.linalg.norm(vt[2])
    return (a if a[0] >= 0 else -a), c


# parts of a grafted wheel that must move together (rigid groups) - aligning parts one by one pulled the tread 7 mm
# off the sidewall (v0.11); the first material in each group is the round part the group is aligned by
WHEEL_GROUPS = [("MK2_TREAD", "MK2_WALL"),
                ("MK2_OUTER_RIM", "MK2_INNER_RIM", "MK2_WHEELNUTS", "MK2_VALVE"),
                ("MK2_SPOKES",)]


def true_up_wheel(tag, objs):
    """AC spins a wheel about its WHEEL_xx node's X axis, so the wheel's round parts must be coaxial with that axis and
    centred on it, or it wobbles (Escort Mk2 donor: rear tyre, outer rim and nuts modelled with 2 deg of camber, spokes
    not; everything 7-8 mm off-centre). Each rigid group (tyre / rim assembly / spokes) is rotated onto the axis by the
    SVD axis of its round members and centred by the midpoint of its key part's extents (vertex means are biased by
    uneven vertex spacing). Finally the wheel is scaled about the axle so the tread's outer radius is TYRE_R."""
    wheel = kn5(f"WHEEL_{tag}")
    W = wheel.matrix_world.copy()
    Winv = W.inverted()
    Wi = np.array(Winv)

    def local(o):
        return world_pts(o) @ Wi[:3, :3].T + Wi[:3, 3]

    def mat(o):
        return o.data.materials[0].name

    for group in WHEEL_GROUPS:
        members = [o for o in objs if mat(o).startswith(group)]
        key = [o for o in members if mat(o).startswith(group[0])]
        round_ = [o for o in members if not mat(o).startswith(("MK2_VALVE", "MK2_WHEELNUTS"))]
        if not key:
            continue
        a, c = _axis_fit(np.concatenate([local(o) for o in round_]))
        R = Vector(a).rotation_difference(Vector((1.0, 0.0, 0.0))).to_matrix().to_4x4()
        T = R @ Matrix.Translation(-Vector(c))
        K = np.concatenate([local(o) for o in key])
        K = K - c
        K = K @ np.array(R)[:3, :3].T
        mid = (K.min(0) + K.max(0)) / 2
        T = Matrix.Translation((float(c[0]), -float(mid[1]), -float(mid[2]))) @ T
        for o in members:
            o.matrix_world = W @ T @ Winv @ o.matrix_world
        bpy.context.view_layer.update()
    tread = next(o for o in objs if mat(o).startswith("MK2_TREAD"))
    P = local(tread)
    S = Matrix.Scale(TYRE_R / float(np.hypot(P[:, 1], P[:, 2]).max()), 4)
    for o in objs:
        o.matrix_world = W @ S @ Winv @ o.matrix_world
    bpy.context.view_layer.update()
    return {o.get("kn5_name"): round(math.degrees(math.acos(min(1.0, abs(_axis_fit(local(o))[0][0])))), 2) for o in objs}


def graft_donor_wheels():
    """Copy the donor car's wheels (rim, spokes, nuts, tyre) onto the stock wheel nodes, scaled to TYRE_R and
    centred on the stock wheel centre. Returns the tyre tread width after scaling."""
    import json
    donor = {o.get("kn5_name"): o for o in bpy.data.collections[DONOR].objects}
    stock_tyre = json.loads(bpy.data.materials["tire"]["kn5_def"])
    ddir = json.loads(bpy.data.materials["MK2_MCK_DRY_TREAD"]["kn5_def"])["tex_dir"]
    tread_m = tyre_material("MK2_TREAD_tyres", stock_tyre, "MK2_mck_ttread.dds", "MK2_mck_ttread_nm.dds", ddir)
    wall_m = tyre_material("MK2_WALL_tyres", stock_tyre, "MK2_mck_tireside_kumho.dds", "MK2_flat_nm.dds", ddir)
    widths, made = [], []
    for tag in ("LF", "RF", "LR", "RR"):
        for n in (f"RALLY_RIM_{tag}",):
            old = bpy.data.objects.get(n)
            if old:
                bpy.data.objects.remove(old)
        for node in (kn5(f"RIM_{tag}"), kn5(f"TYRE_{tag}")):
            for c in node.children_recursive:
                c["no_export"] = True; c.hide_set(True)
            for c in node.children:
                c["no_export"] = True
        for o in [o for o in bpy.data.objects if o.get("rally_graft") == tag]:
            bpy.data.objects.remove(o)
        parts = [c for c in donor[f"WHEEL_{tag}"].children_recursive if c.type == "MESH"
                 and c.data.materials and c.data.materials[0].name != "MK2_discs_material"]
        tread = next(p for p in parts if p.data.materials[0].name == "MK2_MCK_DRY_TREAD")
        T = world_pts(tread)
        lo, hi = T.min(0), T.max(0)
        centre = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
        r_tread = float(np.hypot(T[:, 1] - centre.y, T[:, 2] - centre.z).max())
        k = TYRE_R / r_tread
        target = kn5(f"WHEEL_{tag}").matrix_world.translation
        M = Matrix.Translation(target) @ Matrix.Scale(k, 4) @ Matrix.Translation(-centre)
        widths.append(float(hi[0] - lo[0]) * k)
        wheel_objs = []
        for i, p in enumerate(parts):
            ob = p.copy(); ob.data = p.data.copy()
            bpy.data.collections["STOCK_MODEL"].objects.link(ob)
            mname = p.data.materials[0].name
            if mname == "MK2_MCK_DRY_TREAD":
                ob.data.materials[0] = tread_m
            elif mname == "MK2_MCK_TYREWALL_KUMHO":
                ob.data.materials[0] = wall_m
            is_tyre = mname in ("MK2_MCK_DRY_TREAD", "MK2_MCK_TYREWALL_KUMHO")
            parent = kn5(f"TYRE_{tag}") if is_tyre else kn5(f"RIM_{tag}")
            world = M @ p.matrix_world
            ob.parent = parent
            ob.matrix_world = world
            ob["kn5_name"] = f"RALLY_{'TYRE' if is_tyre else 'RIM'}_{tag}_{i}"
            ob["kn5_order"] = 10 ** 6 + i
            ob["kn5_pristine"] = False
            wheel_objs.append(ob)
            ob["rally_graft"] = tag
            ob.hide_set(False)
            made.append(ob.name)
        bpy.context.view_layer.update()
        WHEEL_TILTS[tag] = true_up_wheel(tag, wheel_objs)
    return max(widths), made


WHEEL_TILTS = {}


def rim_bm(r_face):
    """8-spoke face + barrel, axle along X, outboard +X, sized to a rim radius."""
    wheels = load("build_wheels")
    k = r_face / 0.1905
    bm = wheels.build_rim()
    bmesh.ops.scale(bm, vec=(1.0, k, k), verts=bm.verts)
    return bm


def build():
    # back to the stock meshes first (last build's edited copies - lifted stripes, cut bonnet, ... - would otherwise
    # be sampled as the body and every rebuild would drift a little)
    load("build_extras").restore_modified()
    bpy.context.view_layer.update()
    body = BodySampler()
    paint = bpy.data.materials["carPaint"]
    black = bpy.data.materials["plastic_textured_002"]
    univers = kn5("UNIVERS")
    # all the body-colour trim as one mesh per side: front lip - loft - flare - sill - flare - loft - rear lip
    # (build_lips.py), plus the black blades
    import types
    for old in ("RALLY_lip_front", "RALLY_lip_rear", "RALLY_splitter_front", "RALLY_splitter_rear", "RALLY_skirts"):
        o = bpy.data.objects.get(old)
        if o:
            bpy.data.objects.remove(o)
    brp = types.SimpleNamespace(world_pts=world_pts, valance_edge=valance_edge, kn5=kn5, replace=replace,
                                flare_rings=flare_rings)
    made = load("build_lips").build(brp, body, body.uv_at(PAINT_UV_AT))

    width, grafted = graft_donor_wheels()
    made += grafted
    # where the physics must put the wheels: tyre outer edge TYRE_CLEAR inside the flare lip
    lip_x = body.side_x(-1.212, HUB + 0.34) + LIP_OUT
    track_add = 2 * ((lip_x - TYRE_CLEAR - width / 2) - WHEELS["LF"][0])

    lamps, lens_names = build_spot_lamps()
    made += lamps
    wd = load("build_details")

    for old in ("RALLY_arch_feet", "RALLY_skirts"):
        o = bpy.data.objects.get(old)
        if o:
            bpy.data.objects.remove(o)

    # mud flaps: hung just behind each arch's trailing edge, centred on where the tyre runs in AC, bottom 70 mm
    # off the ground. Top edge: up to the arch opening at the flap (+20 mm, tucked under the flare lip) - the rear
    # flap used to stop 25 mm short of the rear arch; the front one meets the sill.
    bm = bmesh.new()
    flap_tops = {}
    for tag in ("LF", "LR"):
        yw = WHEELS[tag][1]
        xc = AC_TYRE_X[tag]
        if tag == "LF":
            # front wheel steers: flap stays clear, behind the arch's trailing edge, top up to the sill
            y0 = yw + math.sqrt(max(0.0, interp(OPEN[tag], 185) ** 2 - (HUB - 0.05) ** 2)) + 0.010
            top_z = 0.17
        else:
            # rear: 20 mm inside the arch opening (35 mm behind the tyre), running up behind the arch edge so it
            # meets the arch; the flare lip covers its outer edge
            r_back = interp(OPEN[tag], 180)
            y0 = yw + r_back - 0.020
            top_z = HUB + math.sqrt(max(0.0, r_back ** 2 - (y0 - yw) ** 2)) + 0.015
        wd.add_box(bm, xc - TYRE_W / 2 - 0.01, xc + TYRE_W / 2 - 0.004, y0, y0 + 0.008, -0.085, top_z, 0, bevel=0.003)
        flap_tops[tag] = round(top_z, 3)
    made.append(replace("RALLY_mudflaps", bm, [black], univers).name)

    # stripped rear interior + homologated roll cage (build_cage.py)
    cage = load("build_cage").build()
    made += cage["made"]
    # bonnet scoop, number plate on the bumper, sequential shifter (build_extras.py)
    extras = load("build_extras").build()
    made += extras["made"]
    # engine swap (build_engine_swap.ENGINE: the Escort Mk2 twin-cam four with a Lotus badge, or "stock")
    engine = load("build_engine_swap").build()
    extras["engine"] = {k: v for k, v in engine.items() if k != "placed"}
    extras["engine_kept"] = engine.get("placed", {}).get("dropped")
    return {"made": made, "tyre_width": round(width, 3), "lip_x": round(lip_x, 3), "track_add": round(track_add, 3),
            "lamp_lenses": lens_names, "flap_tops": flap_tops, "cage_clearance": cage["clearance"],
            "extras": {k: v for k, v in extras.items() if k != "made"}}


if __name__ == "__main__":
    build()
