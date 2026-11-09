"""Bolt-on details for the rally Sunbeam (runs in Blender on sunbeam_rally_on_stock_model.blend; called from
build_rally_parts.build() after the cage/interior).

  * bonnet scoop - after Nick's photos of RTA 43X (box scoop on the rear of the bonnet, opening forward), at the
    size and low profile Nick set by hand in Blender (30 cm wide, 33 cm long, 6.6 cm tall at the front falling to
    2.2 cm). Body colour, faired into the bonnet (flared foot, ramp at the back), a black grille across the
    opening and a black duct behind it down through a hole cut in the bonnet, so the engine shows through.
  * bonnet pins - rally-style pin + R-clip on a chrome plate at both front corners of the bonnet
  * front number plate lifted from under the bumper onto its face, centred, top edge just under the spot-lamp bar
  * sequential shifter - the Escort Mk2 donor's lever and pear knob, placed so the knob sits in our driver's right
    fist 3/4 through his gear-change animation, leaning a little towards him, coming out of the Escort's shifter
    base, which sits in the console opening where the stock gear gaiter was (stock lever, knob and gaiter removed)
  * hydraulic handbrake - the Escort's, mirrored so it stands on the right of the gear stick (the driver's side
    of it faces the lever as on the Escort), its brackets on the tunnel side
  * both in the Sunbeam interior's own finishes (RESTYLE): leather knob and grip, satin black body, chrome lever
  * rally sliding windows in both door glasses (SLIDER), attached to the doors

Coordinates: Blender world, x = car's left, -y = front, z up.
"""
import importlib.util
import json
import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

TOOLS = r"D:\Claude\talbot_sunbeam_lotus\tools"
DRIVER_CAR = "talbot_sunbeam_lotus_lhd_stock"   # its animations/ = ours

# bonnet scoop (Nick's hand-set size): width, front/rear edge, height above the bonnet's centreline at front/rear,
# ramp behind the rear edge down to the bonnet, wall, top-edge radius, foot flare, duct depth below the bonnet,
# grille (set back, bar size, pitch across/up)
SCOOP = {"width": 0.30, "y_front": -1.290, "y_rear": -0.965, "h_front": 0.066, "h_rear": 0.022, "ramp": 0.040,
         "wall": 0.008, "radius": 0.010, "flare": 0.014, "duct": 0.070, "sections": 12,
         "grille_in": 0.012, "bar": 0.004, "pitch_x": 0.022, "pitch_z": 0.015}
PINS = [(0.55, -1.70), (-0.55, -1.70)]   # bonnet pins, clear of the Talbot badge (x 0.38-0.53, y to -1.776)
PLATE_LIFT = 0.050        # plate z 0.163..0.280 -> 0.213..0.330 (lamp bar tube bottom 0.332)
PLATE_OUT = 0.006         # and 6 mm forward: the bumper's crowned face came within 1 mm of the plate's centre

STOCK_LEVER = ("Levier", "centerconsolebezels_a_SUB10", "centerconsolebezels_a_SUB11", "centerconsolebezels_a_SUB15")
GAITER_EXIT = (0.009, 0.44)           # x, z where the stock lever came out of its gaiter
SHIFTER_PARTS = ("gear_shift_sub001_SUB0", "gear_shift_sub001_SUB1")   # upper lever + knob (base/cable: in tunnel)
SHIFT_FRAME = 75                      # the fist 3/4 through the push (frames 50-99: y -0.30 -> -0.36)
HANDBRAKE_PARTS = ("centerconsolebezels_a020_SUB11", "centerconsolebezels_a020_SUB4", "centerconsolebezels_a020_SUB7",
                   "centerconsolebezels_a020_SUB5", "centerconsolebezels_a020_SUB0",
                   "centerconsolebezels_a020_SUB16", "piping_1")
HANDBRAKE_AT = (-0.075, -0.345)        # lever axis x, y: right of the gear stick, on the tunnel's side
# the old road-car controls, out of BOTH cockpits (the low-res one AC shows from outside has its own copies, merged
# into other meshes - Nick still saw the old stick and handbrake): loose parts lying wholly inside these boxes
# (box, materials or None = any). The gear gaiter goes too (Nick): only its boot + stitching - the console bezel
# round the opening stays, and the rally shifter's base sits in that opening.
OLD_CONTROLS = {"gear stick": (((-0.020, 0.035), (-0.360, -0.270), (0.425, 0.540)), None),
                "handbrake": (((-0.050, 0.070), (-0.230, 0.200), (0.240, 0.340)), None),
                "gear gaiter": (((-0.050, 0.070), (-0.450, -0.328), (0.285, 0.445)),
                                {"soufflet", "stitch_003|shifterAssy_a"})}
# the rally shifter's base (the Escort's, left out in v1 when the lever came out of the stock gaiter): upright, its
# plate on the console bezel round the old gaiter opening (x -0.044..0.063, y -0.446..-0.333, rim z 0.323), centred
# where the tilted lever crosses the base's top
SHIFTER_BASE_PARTS = tuple(f"gear_shift_base_SUB{i}" for i in range(8))
SHIFTER_BASE_Z = 0.325
# finishes to match the Sunbeam's own interior (black grained leather wheel/console, satin black painted metal,
# chrome trim) instead of the Escort's carbon / red / brass / silver - Nick: "look kind of basic against the rest of
# the car". Donor material -> stock material; the knob's pear (top KNOB_LEATHER m) gets the steering wheel's leather.
RESTYLE = {"MK2_metal_anodized_black_handbrake_a": "painted_metal_smooth",
           "MK2_metal_machined_nomal_handbrake_a": "metal_smooth",
           "MK2_plastic_smooth_RED_handbrake_a": "volant",
           "MK2_brass_satin_handbrake_a": "metal_smooth",
           "MK2_rubbertrim_lines_handbrake_a": "rubber",
           "MK2_gunmetal_satin_shifterAssy_a": "painted_metal_smooth",
           "MK2_metal_alloy_ch1_screw_02_shifterAssy_a": "metal_smooth",
           "MK2_metal_anodized_allOptions_screw_shifterAssy_a": "metal_smooth",
           "MK2_plastic_embossed_alpha_screw_03_handbrake_a": "painted_metal_smooth"}
HANDBRAKE_BODY = {"centerconsolebezels_a020_SUB5": "painted_metal_smooth"}   # its machined body: satin black
KNOB_LEATHER = 0.062
# rally sliding windows in both door glasses: a black channel frame bonded on the outside of the glass round the
# lower part of the window, split in two by a divider; the front pane is the slider (a second pane in the channels,
# just outboard, with a grab tab). (y from, y to, z bottom, z top, divider y) on the left door; mirrored on the right.
SLIDER = {"y0": -0.270, "y1": 0.405, "z0": 0.780, "z1": 0.935, "ydiv": 0.070, "channel": 0.013, "proud": 0.006,
          "pane_out": 0.0035, "tab": (0.018, 0.028, 0.012)}
# side stripes (carPaint_2 sheets laid over the paint): the stock mod floats them only 0.01-0.57 mm (median 0.25) off
# the body, so beyond a few metres the depth buffer can't tell them apart and they flicker in and out (Nick: "fade
# in and out as if the paint is blurring", in game and in Blender). Lifted to at least STRIPE_GAP (LODs: build_lods).
STRIPE_MAT, STRIPE_GAP = "carPaint_2", 0.0015
# speedo + rev counter needles: fluorescent red (the white ones were hard to see on the dials - Nick)
NEEDLES = ("ARROW_SPEED", "ARROW_RPM", "ARROW_BATTERY", "ARROW_FUEL", "ARROW_OIL_PRESS", "ARROW_WATER_TEMP")
NEEDLE_TEX = "rgbaff0b0099.dds"        # (255, 11, 0) - drawn opaque, the alpha is ignored
NEEDLE_EMISSIVE = (0.9, 0.05, 0.03)
# exhaust (stock twin tips, left rear, ~49 mm each, filling a notch in the valance): stock size where they pass
# through the valance, flaring out behind it (original y flare_y0 -> flare_y1) to tip_scale across the outlets'
# centre line (x, z), and stretched tip_out further out behind the valance. (v1 scaled them 1.5x all along - they
# stuck through the sides of the valance notch; the collector behind the valance stays stock.)
EXHAUST = {"centre": (0.470, 0.1855), "tips": ("exhaust_a_SUB1", "exhaust_a_SUB0"), "tip_scale": 1.5,
           "tip_out": 0.025, "flare_y0": 1.835, "flare_y1": 1.872, "stretch_y0": 1.80, "stretch_y1": 1.85,
           "pipe": (), "pipe_scale": 1.0}


def load(name):
    spec = importlib.util.spec_from_file_location(name, rf"{TOOLS}\{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def stock(kn):
    """All stock-model objects with this kn5 name (the HR and LR cockpits can both have one)."""
    return [o for o in bpy.data.collections["STOCK_MODEL"].all_objects
            if o.get("kn5_name") == kn and not o.get("mod_of") and not o.name.startswith("RALLY_")]


def stock_material(name):
    return next(m for m in bpy.data.materials if m.get("kn5_def") and json.loads(m["kn5_def"])["name"] == name
                and not m.name.startswith("MK2"))


def remove(obj):
    me = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def new_object(name, bm, materials, parent, **props):
    old = bpy.data.objects.get(name)
    if old:
        remove(old)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["STOCK_MODEL"].objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    for k, v in props.items():
        ob[k] = v
    return ob


def graft(src, name, M, parent, mirrored=False, **props):
    """Copy of a donor/stock mesh with M baked into its vertices (world space); mirrored: faces reversed and the
    donor's stored normals dropped (they don't survive a mirror)."""
    me = src.data.copy()
    bm = bmesh.new(); bm.from_mesh(me)
    bm.transform(M @ src.matrix_world)
    if mirrored:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    if mirrored:
        for a in ("custom_normal", "kn5_nrm", "kn5_tan"):
            if a in me.attributes:
                me.attributes.remove(me.attributes[a])
    old = bpy.data.objects.get(name)
    if old:
        remove(old)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["STOCK_MODEL"].objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    ob["kn5_class"] = 2
    ob["kn5_name"] = name
    ob["kn5_pristine"] = False
    for k, v in props.items():
        ob[k] = v
    return ob


def restore_modified():
    """Undo last build's edited copies of stock meshes (mod_*): drop them, put the originals back."""
    for o in [o for o in bpy.data.objects if o.get("mod_of")]:
        src = bpy.data.objects.get(o["mod_of"])
        if src is not None and "no_export" in src:
            del src["no_export"]
            if src.name in bpy.context.view_layer.objects:
                src.hide_set(False)
        remove(o)


def modified_copy(src):
    """An editable copy of a stock mesh that takes its place in the export (same kn5 name/parent/order)."""
    ob = src.copy(); ob.data = src.data.copy()
    bpy.data.collections["STOCK_MODEL"].objects.link(ob)
    ob.name = f"mod_{src.name}"
    ob["mod_of"] = src.name
    ob["kn5_pristine"] = False
    if "no_export" in ob:
        del ob["no_export"]
    src["no_export"] = True
    if src.name in bpy.context.view_layer.objects:
        src.hide_set(True)
    return ob


def bvh_of(objs):
    verts, polys = [], []
    for o in objs:
        mw = o.matrix_world
        base = len(verts)
        verts += [tuple(mw @ v.co) for v in o.data.vertices]
        polys += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def tube(bm, uv, pts, r, segs=8):
    load("build_cage").sweep_tube(bm, uv, [Vector(p) for p in pts], r=r, segs=segs)


def disc(bm, uv, centre, n, r, h, segs=20):
    """Closed thin cylinder standing on `centre` along n."""
    n = Vector(n).normalized()
    a = n.orthogonal().normalized(); b = n.cross(a)
    c = Vector(centre)
    rings = [[bm.verts.new(c + n * z + (a * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r)
              for k in range(segs)] for z in (0.0, h)]
    faces = [bm.faces.new((rings[0][k], rings[0][(k + 1) % segs], rings[1][(k + 1) % segs], rings[1][k]))
             for k in range(segs)]
    faces += [bm.faces.new(rings[0]), bm.faces.new(rings[1])]
    for f in faces:
        for lp in f.loops:
            lp[uv].uv = (0.0, 0.0)


# ---------------------------------------------------------------- bonnet

def bonnet_mesh():
    return next(o for o in stock("hood_a") if o.type == "MESH")


def paint_uv_at(obj, p):
    """UV of obj's corner nearest to p - so a painted part can take the paint colour there."""
    mw = obj.matrix_world
    best, bi = 1e9, 0
    for i, v in enumerate(obj.data.vertices):
        d = (mw @ v.co - p).length
        if d < best:
            best, bi = d, i
    uvl = obj.data.uv_layers.active.data
    for lp in obj.data.loops:
        if lp.vertex_index == bi:
            return tuple(uvl[lp.index].uv)
    return (0.0, 0.0)


def scoop_bmesh(bonnet, paint_uv):
    """Material 0 body colour (skin, rim), 1 black inside (duct), 2 grille."""
    s = SCOOP
    zb = lambda x, y: bonnet.ray_cast(Vector((x, y, 1.5)), Vector((0, 0, -1)), 2.0)[0].z
    W, t, fl = s["width"] / 2, s["wall"], s["flare"]
    y0, y1, y2 = s["y_front"], s["y_rear"], s["y_rear"] + s["ramp"]
    draft = math.tan(math.radians(5))

    def height(y):
        if y <= y1:
            return s["h_front"] + (s["h_rear"] - s["h_front"]) * (y - y0) / (y1 - y0)
        u = (y - y1) / (y2 - y1)
        return s["h_rear"] + (0.0015 - s["h_rear"]) * (3 * u * u - 2 * u ** 3)     # smooth ramp to the bonnet

    def outer(y):
        """left flare foot -> fillet -> wall -> rounded top -> ... -> right flare foot (8 points a side)."""
        ztop = zb(0.0, y) + height(y)
        r = min(s["radius"], height(y) * 0.45)
        pts = []
        for sgn in (-1, 1):
            base = zb(sgn * W, y)
            side = [(sgn * (W + fl), y, zb(sgn * (W + fl), y) - 0.002),
                    (sgn * (W + 0.45 * fl), y, zb(sgn * (W + 0.45 * fl), y) + 0.0012),
                    (sgn * (W + 0.12 * fl), y, base + 0.0040),
                    (sgn * W, y, base + min(0.0075, (ztop - base) * 0.5))]
            sx = sgn * (W - max(0.0, ztop - r - base) * draft)
            side.append((sx, y, max(ztop - r, side[-1][2] + 0.0005)))
            side += [(sx - sgn * r * (1 - math.cos(a)), y, ztop - r + r * math.sin(a))
                     for a in (math.radians(30), math.radians(60), math.radians(90))]
            pts += side if sgn < 0 else side[::-1]
        return pts

    def inner(y):
        """the duct: wall from below the bonnet up, rounded under the top (same point count as the upper outer)."""
        ztop = zb(0.0, y) + height(y) - t
        r = max(0.002, s["radius"] - t)
        w = W - t
        pts = []
        for sgn in (-1, 1):
            base = zb(sgn * w, y)
            sx = sgn * (w - max(0.0, ztop - r - base) * draft)
            side = [(sgn * w, y, base - s["duct"]), (sgn * w, y, base), (sx, y, ztop - r)]
            side += [(sx - sgn * r * (1 - math.cos(a)), y, ztop - r + r * math.sin(a))
                     for a in (math.radians(30), math.radians(60), math.radians(90))]
            pts += side if sgn < 0 else side[::-1]
        return pts

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    groups = {"skin": [], "front": [], "rear": [], "duct": [], "apron": [], "duct_end": [], "grille": []}
    n = s["sections"]
    ys = [y0 + (y1 - y0) * i / n for i in range(n + 1)] + [y1 + (y2 - y1) * k / 4 for k in range(1, 5)]
    rings = [[bm.verts.new(p) for p in outer(y)] for y in ys]
    for a, b in zip(rings, rings[1:]):
        groups["skin"] += [bm.faces.new((a[k], a[k + 1], b[k + 1], b[k])) for k in range(len(a) - 1)]
    groups["rear"].append(bm.faces.new(rings[-1]))
    # front: rim from the upper outer profile to the duct's top edge; the flare's little front faces
    O = rings[0]
    yd1 = y1 - 0.02
    dys = [y0 + (yd1 - y0) * i / n for i in range(n + 1)]
    drings = [[bm.verts.new(p) for p in inner(y)] for y in dys]
    I = drings[0]
    half = len(O) // 2                       # 8 per side outer; inner has 6 per side: map outer[3:8] <- inner[1:6]
    for side in (0, 1):
        o = O[:half] if side == 0 else O[half:][::-1]
        i = I[:len(I) // 2] if side == 0 else I[len(I) // 2:][::-1]
        for k in range(3, 7):                 # wall foot .. arc60 on the outside, bonnet level .. arc60 inside
            groups["front"].append(bm.faces.new((o[k], o[k + 1], i[k - 1], i[k - 2])))
        groups["front"].append(bm.faces.new((o[0], o[1], o[2], o[3])))         # flare end
    groups["front"].append(bm.faces.new((O[half - 1], O[half], I[len(I) // 2], I[len(I) // 2 - 1])))   # top middle
    for a, b in zip(drings, drings[1:]):
        m = len(a)
        groups["duct"] += [bm.faces.new((a[k], a[k + 1], b[k + 1], b[k])) for k in range(m - 1)]
    groups["duct_end"].append(bm.faces.new(drings[-1]))
    # apron: the duct's front wall below the bonnet, just behind the opening
    L, R = I[0], I[-1]
    ya = y0 + 0.002
    ap = [bm.verts.new(p) for p in ((L.co.x, ya, L.co.z), (R.co.x, ya, R.co.z),
                                    (R.co.x, ya, zb(R.co.x, ya)), (L.co.x, ya, zb(L.co.x, ya)))]
    groups["apron"].append(bm.faces.new(ap))
    # grille: square bars across the opening, set back from the rim
    yg = y0 + s["grille_in"]
    zlo = zb(0.0, yg) + 0.001
    ztop = zb(0.0, yg) + height(yg) - t - 0.002
    wg = W - t - 0.001
    hb = s["bar"] / 2

    def bar(p0, p1):
        d = (Vector(p1) - Vector(p0)).normalized()
        a = Vector((0, 1, 0)); b = d.cross(a).normalized()
        c = [bm.verts.new(Vector(p) + a * sa * hb + b * sb * hb) for p in (p0, p1) for sa in (-1, 1) for sb in (-1, 1)]
        for idx in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            groups["grille"].append(bm.faces.new([c[i] for i in idx]))

    zz = zlo + s["pitch_z"] * 0.6
    while zz < ztop - 0.004:
        bar((-wg, yg, zz), (wg, yg, zz)); zz += s["pitch_z"]
    xx = -wg + s["pitch_x"] * 0.5
    while xx < wg - 0.004:
        bar((xx, yg, zb(xx, yg) - 0.01), (xx, yg, ztop)); xx += s["pitch_x"]

    def axis(y, frac):
        yc = min(max(y, y0), y2)
        return Vector((0.0, y, zb(0.0, yc) + frac * height(yc)))

    bm.normal_update()
    want = {"skin": (lambda c: c - axis(c.y, 0.25), 0), "front": (lambda c: Vector((0, -1, 0)), 0),
            "rear": (lambda c: Vector((0, 1, 0)), 0), "duct": (lambda c: axis(c.y, 0.0) - c, 1),
            "apron": (lambda c: Vector((0, 1, 0)), 1), "duct_end": (lambda c: Vector((0, -1, 0)), 1)}
    for g, faces in groups.items():
        for f in faces:
            if g == "grille":
                f.material_index = 2
            else:
                fn, mi = want[g]
                if f.normal.dot(fn(f.calc_center_median())) < 0:
                    f.normal_flip()
                f.material_index = mi
            f.smooth = True
            for lp in f.loops:
                lp[uv].uv = paint_uv if f.material_index == 0 else (0.0, 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=groups["grille"])
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(45):
            e.smooth = False
    return bm


def cut_bonnet():
    """A hole through every layer of the bonnet (skin, liner, insulation, engine-bay cover) inside the scoop's duct,
    cut exactly at the duct walls (bisected first) - the duct hides the cut edges."""
    s = SCOOP
    w = s["width"] / 2 - s["wall"] - 0.001
    ya, yb = s["y_front"] + 0.003, s["y_rear"] - 0.021
    hood = stock("MOTORHOOD")[0]
    cut = {}
    for src in [c for c in hood.children_recursive if c.type == "MESH" and not c.name.startswith("RALLY_")
                and not c.get("no_export") and not c.get("mod_of")]:
        mw = src.matrix_world
        P = [mw @ v.co for v in src.data.vertices]
        if not (min(p.x for p in P) < w and max(p.x for p in P) > -w and min(p.y for p in P) < yb
                and max(p.y for p in P) > ya):
            continue
        ob = modified_copy(src)
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bm.transform(mw)
        for co, no in (((w, 0, 0), (1, 0, 0)), ((-w, 0, 0), (1, 0, 0)), ((0, ya, 0), (0, 1, 0)), ((0, yb, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
        gone = [f for f in bm.faces if abs(f.calc_center_median().x) < w and ya < f.calc_center_median().y < yb]
        bmesh.ops.delete(bm, geom=gone, context="FACES")
        bm.transform(mw.inverted())
        bm.to_mesh(ob.data); bm.free()
        cut[src.get("kn5_name")] = len(gone)
    return cut


def build_scoop():
    hood = bonnet_mesh()
    bonnet = bvh_of([hood])
    zc = bonnet.ray_cast(Vector((0, -1.12, 1.5)), Vector((0, 0, -1)), 2.0)[0]
    paint_uv = paint_uv_at(hood, zc)
    mats = [stock_material("carPaint"), stock_material("zeroBlack|bodyVent_a"), load("build_cage").cage_material()]
    ob = new_object("RALLY_bonnet_scoop", scoop_bmesh(bonnet, paint_uv), mats, stock("MOTORHOOD")[0],
                    no_decimate=True)
    return ob, cut_bonnet()


def build_pins():
    """Bonnet pins: chrome plate on the bonnet, pin through it, R-clip through the pin lying back on the plate."""
    bonnet = bvh_of([bonnet_mesh()])
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for x, y in PINS:
        hit = bonnet.ray_cast(Vector((x, y, 1.5)), Vector((0, 0, -1)), 2.0)
        p, n = hit[0], hit[1].normalized()
        u = Vector((0, -1, 0)); u = (u - n * u.dot(n)).normalized()     # along the bonnet, pointing forward
        v = n.cross(u)
        disc(bm, uv, p - n * 0.0005, n, 0.021, 0.0025)                     # plate
        disc(bm, uv, p, n, 0.0045, 0.024, segs=12)                          # pin
        disc(bm, uv, p + n * 0.024, n, 0.0035, 0.002, segs=12)              # rounded-off head
        leg_h = 0.016
        clip = [p + n * leg_h - v * 0.011, p + n * leg_h + v * 0.009,       # straight leg through the pin
                p + n * (leg_h - 0.004) + v * 0.013 + u * 0.004,
                p + n * 0.0045 + v * 0.011 + u * 0.010,                     # loops down onto the plate
                p + n * 0.0045 - v * 0.004 + u * 0.013,
                p + n * 0.0045 - v * 0.015 + u * 0.008]
        tube(bm, uv, load("build_cage").fillet_path(clip, [0, 0.003, 0.004, 0.004, 0.004, 0]), 0.0011, segs=6)
    load("build_cage").finish(bm)
    return new_object("RALLY_bonnet_pins", bm, [stock_material("chrome")], stock("MOTORHOOD")[0],
                      no_decimate=True, no_lod=True)


# ---------------------------------------------------------------- exhaust

def _ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def exhaust_move(p, part):
    """Where a point of the stock exhaust goes (world coords; part 'tips' or 'pipe')."""
    e = EXHAUST
    cx, cz = e["centre"]
    if part != "tips":
        k = e["pipe_scale"]
        return Vector((cx + (p.x - cx) * k, p.y, cz + (p.z - cz) * k))
    k = 1.0 + (e["tip_scale"] - 1.0) * _ease((p.y - e["flare_y0"]) / (e["flare_y1"] - e["flare_y0"]))
    out = e["tip_out"] * _ease((p.y - e["stretch_y0"]) / (e["stretch_y1"] - e["stretch_y0"]))
    return Vector((cx + (p.x - cx) * k, p.y + out, cz + (p.z - cz) * k))


def build_exhaust():
    done = {}
    for part, names in (("tips", EXHAUST["tips"]), ("pipe", EXHAUST["pipe"])):
        for kn in names:
            for src in [o for o in stock(kn) if o.type == "MESH"]:
                ob = modified_copy(src)
                mw = ob.matrix_world
                inv = mw.inverted()
                bm = bmesh.new(); bm.from_mesh(ob.data)
                bm.transform(mw)
                if part == "tips":        # cut across the pipes where they flare/stretch: long faces would taper
                    y = min(EXHAUST["stretch_y0"], EXHAUST["flare_y0"])
                    while y < EXHAUST["flare_y1"] + 1e-6:
                        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                               plane_co=(0, y, 0), plane_no=(0, 1, 0))
                        y += 0.006
                for v in bm.verts:
                    v.co = exhaust_move(v.co, part)
                bm.transform(inv)
                bm.to_mesh(ob.data); bm.free()
                for a in ("kn5_nrm", "kn5_tan"):
                    if a in ob.data.attributes:
                        ob.data.attributes.remove(ob.data.attributes[a])
                done[kn] = len(ob.data.vertices)
    return done


# ---------------------------------------------------------------- stripes

def lift_off(obj, verts, body_bvh, gap):
    """Move obj's vertices (indices) out to at least `gap` outside the body surface, along the body's normal
    (oriented by the vertex's own normal - the stripes face outwards). Returns how many moved."""
    mw = obj.matrix_world
    inv = mw.inverted()
    nrm = mw.to_3x3().inverted().transposed()
    moved = set()
    verts = list(verts)
    for _ in range(4):              # near a crease, lifting off one face can leave a vertex close to the next
        n_moved = 0
        for i in verts:
            v = obj.data.vertices[i]
            p = mw @ v.co
            h = body_bvh.find_nearest(p)
            if h[0] is None or h[3] > 0.05:
                continue
            n = Vector(h[1]).normalized()
            if n.dot((nrm @ v.normal).normalized()) < 0:
                n = -n
            s = (p - h[0]).dot(n)
            if s < gap * 0.97:
                v.co = inv @ (p + n * (gap - s))
                moved.add(i); n_moved += 1
        if not n_moved:
            break
    return len(moved)


def paint_bvh_of(objs, mat="carPaint"):
    verts, polys = [], []
    for o in objs:
        names = [json.loads(m["kn5_def"])["name"] if m and "kn5_def" in m else None for m in o.data.materials]
        if mat not in names:
            continue
        mw = o.matrix_world
        for p in o.data.polygons:
            if names[p.material_index] == mat:
                base = len(verts)
                verts += [tuple(mw @ o.data.vertices[i].co) for i in p.vertices]
                polys.append(tuple(range(base, base + len(p.vertices))))
    return BVHTree.FromPolygons(verts, polys)


def lift_stripes():
    meshes = [o for o in bpy.data.collections["STOCK_MODEL"].all_objects
              if o.type == "MESH" and not o.get("no_export") and not o.get("mod_of") and o.data.materials
              and not o.name.startswith("RALLY_")]
    body = paint_bvh_of(meshes)
    done = {}
    for src in [o for o in meshes if json.loads(o.data.materials[0].get("kn5_def", "{}")).get("name") == STRIPE_MAT]:
        ob = modified_copy(src)
        done[src.get("kn5_name")] = lift_off(ob, range(len(ob.data.vertices)), body, STRIPE_GAP)
    return done


# ---------------------------------------------------------------- number plate

def lift_plate():
    plate = next(o for o in stock("Plate_LODA002") if o.type == "MESH")
    if "orig_matrix_world" not in plate:
        plate["orig_matrix_world"] = [v for row in plate.matrix_world for v in row]
    m = plate["orig_matrix_world"]
    plate.matrix_world = Matrix.Translation((0, -PLATE_OUT, PLATE_LIFT)) @ Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
    plate["kn5_pristine"] = False
    return plate.name


# ---------------------------------------------------------------- shifter + handbrake

def fist(frame):
    """Our driver's right fist during the gear change (mean of the finger middle joints, thumb tip and wrist)."""
    dp = load("driver_pose")
    w = dp.skeleton_world(dp.AC + rf"\cars\{DRIVER_CAR}", shift_frame=frame)
    names = ("HAND_Index5", "HAND_Middle5", "HAND_Ring5", "HAND_Pinkie5", "HAND_R_Thumb3", "RIG_HAND_R")
    P = [w["DRIVER:" + nm].translation for nm in names]
    return Vector((sum(p.x for p in P), -sum(p.z for p in P), sum(p.y for p in P))) / len(P)


def donor(kn):
    return next(o for o in bpy.data.collections["DONOR_MK2"].all_objects if o.type == "MESH" and o.get("kn5_name") == kn)


def build_shifter():
    """Knob in the fist, lever tilted about the knob so it comes out of the stock gaiter where the stock lever did."""
    for kn in STOCK_LEVER:
        for o in stock(kn):
            o["no_export"] = True
            if o.name in bpy.context.view_layer.objects:
                o.hide_set(True)
    for o in [o for o in bpy.data.objects if o.get("rally_shifter")]:
        remove(o)
    knob = donor("gear_shift_sub001_SUB0")
    K = [knob.matrix_world @ v.co for v in knob.data.vertices]
    top = max(p.z for p in K)
    bulb = [p for p in K if p.z > top - 0.095]
    ce = sum(bulb, Vector()) / len(bulb)                  # Escort knob centre
    base = donor("gear_shift_base_SUB6")
    B = [base.matrix_world @ v.co for v in base.data.vertices]
    be = sum(B, Vector()) / len(B)                        # Escort base centre: the lever's lower end
    c = fist(SHIFT_FRAME)
    gx, gz = GAITER_EXIT
    axis = (ce - be).normalized()
    down = c.z - gz                                       # knob centre above the gaiter exit
    x_at_exit = c.x - axis.x / axis.z * down              # where the untilted lever would come out
    tilt = math.atan2(x_at_exit - gx, down)
    M = Matrix.Translation(c) @ Matrix.Rotation(tilt, 4, "Y") @ Matrix.Translation(-ce)
    univers = stock("UNIVERS")[0]
    objs = [graft(donor(kn), f"RALLY_shifter_{kn}", M, univers, rally_shifter=True, no_lod=True,
                  kn5_order=3 * 10 ** 6 + 60 + i) for i, kn in enumerate(SHIFTER_PARTS)]
    a2 = Matrix.Rotation(tilt, 3, "Y") @ axis
    exit_pt = c - a2 * (down / a2.z)                      # where the lever now passes the gaiter's height

    # the base, upright on the console where the gaiter was, centred on the tilted lever at the base's top
    plate, housing = donor("gear_shift_base_SUB2"), donor("gear_shift_base_SUB6")
    Pp = [plate.matrix_world @ v.co for v in plate.data.vertices]
    Ph = [housing.matrix_world @ v.co for v in housing.data.vertices]
    z_bot, z_top = min(p.z for p in Pp), max(p.z for p in Ph)
    bcx = (min(p.x for p in Ph) + max(p.x for p in Ph)) / 2
    bcy = (min(p.y for p in Ph) + max(p.y for p in Ph)) / 2
    top = SHIFTER_BASE_Z + (z_top - z_bot)
    at = c - a2 * ((c.z - top) / a2.z)
    MB = Matrix.Translation((at.x - bcx, at.y - bcy, SHIFTER_BASE_Z - z_bot))
    objs += [graft(donor(kn), f"RALLY_shifter_{kn}", MB, univers, rally_shifter=True, no_lod=True,
                   kn5_order=3 * 10 ** 6 + 70 + i) for i, kn in enumerate(SHIFTER_BASE_PARTS)]
    restyle(objs)
    leather_knob(objs[0])
    return [o.name for o in objs], {"knob": tuple(round(v, 3) for v in c), "tilt_deg": round(math.degrees(tilt), 1),
                                    "lever_at_gaiter": tuple(round(v, 3) for v in exit_pt),
                                    "base_centre": tuple(round(v, 3) for v in at)}


def restyle(objs, overrides=None):
    """Swap the donor finishes for the Sunbeam interior's own materials (RESTYLE; overrides by donor part name)."""
    for o in objs:
        for i, m in enumerate(o.data.materials):
            new = (overrides or {}).get(o.get("donor_part")) or RESTYLE.get(m.name if m else None)
            if new:
                o.data.materials[i] = stock_material(new)


def leather_knob(knob):
    """The pear of the knob (top KNOB_LEATHER along the lever) in the steering wheel's black leather."""
    me = knob.data
    me.materials.append(stock_material("volant"))
    mw = knob.matrix_world
    top = max((mw @ v.co).z for v in me.vertices)
    for p in me.polygons:
        if (mw @ p.center).z > top - KNOB_LEATHER:
            p.material_index = len(me.materials) - 1


def islands(bm):
    """Loose parts of a bmesh: [[BMVert, ...], ...]."""
    seen, out = set(), []
    for v0 in bm.verts:
        if v0 in seen:
            continue
        isl, stack = [], [v0]
        seen.add(v0)
        while stack:
            v = stack.pop(); isl.append(v)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w not in seen:
                    seen.add(w); stack.append(w)
        out.append(isl)
    return out


def cockpit_of(o):
    p = o.parent
    while p is not None:
        if p.get("kn5_name") in ("COCKPIT_HR", "COCKPIT_LR"):
            return p.get("kn5_name")
        p = p.parent
    return None


def kdef_name(m):
    return json.loads(m["kn5_def"])["name"] if m is not None and "kn5_def" in m else None


def remove_old_controls():
    """Delete the old gear stick, road handbrake and gear gaiter (loose parts inside OLD_CONTROLS, of the listed
    materials) from both cockpits."""
    inside = lambda P, b: all(b[0][0] <= p.x <= b[0][1] and b[1][0] <= p.y <= b[1][1] and b[2][0] <= p.z <= b[2][1]
                              for p in P)
    done = {}
    for src in [o for o in bpy.data.collections["STOCK_MODEL"].all_objects
                if o.type == "MESH" and cockpit_of(o) and not o.get("no_export") and not o.get("mod_of")
                and not o.name.startswith("RALLY_")]:
        mat = kdef_name(src.data.materials[0]) if src.data.materials else None
        boxes = [b for b, mats in OLD_CONTROLS.values() if mats is None or mat in mats]
        if not boxes:
            continue
        mw = src.matrix_world
        bm = bmesh.new(); bm.from_mesh(src.data)
        gone = [isl for isl in islands(bm) if any(inside([mw @ v.co for v in isl], b) for b in boxes)]
        bm.free()
        if not gone:
            continue
        ob = modified_copy(src)
        bm = bmesh.new(); bm.from_mesh(ob.data)
        doomed = [isl for isl in islands(bm) if any(inside([mw @ v.co for v in isl], b) for b in boxes)]
        bmesh.ops.delete(bm, geom=[v for isl in doomed for v in isl], context="VERTS")
        bm.to_mesh(ob.data); bm.free()
        done[f"{cockpit_of(src)}:{src.get('kn5_name')}"] = len(doomed)
    return done


def needle_material():
    m = bpy.data.materials.get("RALLY_needle_red")
    if m is None:
        base = stock_material("plastic_LGL|needles_a")
        m = base.copy(); m.name = "RALLY_needle_red"
    else:
        base = m          # (the stock needle material has no users once replaced - Blender drops it on save)
    d = json.loads(base["kn5_def"])
    d["name"] = "RALLY_needle_red"
    d["samplers"] = [[s, slot, NEEDLE_TEX if s == "txDiffuse" else t] for s, slot, t in d["samplers"]]
    for p in d["props"]:
        if p[0] == "ksAmbient":
            p[1] = 0.55
        elif p[0] == "ksDiffuse":
            p[1] = 0.6
        elif p[0] == "ksSpecular":
            p[1] = 0.3
        elif p[0] == "ksEmissive":
            p[4:7] = list(NEEDLE_EMISSIVE)
    m["kn5_def"] = json.dumps(d)
    m.diffuse_color = (1.0, 0.04, 0.02, 1.0)
    return m


def red_needles():
    mat = needle_material()
    done = []
    for kn in NEEDLES:
        for o in [o for o in stock(kn) if o.type == "MESH"]:
            if "orig_mat" not in o:
                o["orig_mat"] = o.data.materials[0].name
            o.data.materials[0] = mat
            done.append(f"{cockpit_of(o)}:{kn}")
    return done


def build_handbrake():
    """The Escort's hydraulic handbrake mirrored across its own lever, stood on the tunnel side right of the stick."""
    for o in [o for o in bpy.data.objects if o.get("rally_handbrake")]:
        remove(o)
    lever = donor("centerconsolebezels_a020_SUB4")
    Lp = [lever.matrix_world @ v.co for v in lever.data.vertices]
    lx = (min(p.x for p in Lp) + max(p.x for p in Lp)) / 2
    ly = (min(p.y for p in Lp) + max(p.y for p in Lp)) / 2
    zlow = min((o.matrix_world @ v.co).z for kn in HANDBRAKE_PARTS[:5] for o in [donor(kn)] for v in o.data.vertices)
    x, y = HANDBRAKE_AT
    cabin, _ = load("build_cage").cabin_bvh()
    floor = cabin.ray_cast(Vector((x, y, 0.9)), Vector((0, 0, -1)), 1.0)[0].z
    M = (Matrix.Translation((x, y, floor - 0.012)) @ Matrix.Scale(-1, 4, (1, 0, 0))
         @ Matrix.Translation((-lx, -ly, -zlow)))
    univers = stock("UNIVERS")[0]
    objs = [graft(donor(kn), f"RALLY_handbrake_{kn.split('_')[-1]}", M, univers, mirrored=True,
                  rally_handbrake=True, no_lod=True, donor_part=kn, kn5_order=3 * 10 ** 6 + 80 + i)
            for i, kn in enumerate(HANDBRAKE_PARTS)]
    restyle(objs, HANDBRAKE_BODY)
    made = [o.name for o in objs]
    grip = donor("centerconsolebezels_a020_SUB11")
    gtop = max((M @ grip.matrix_world @ v.co).z for v in grip.data.vertices)
    return made, {"tunnel_z": round(floor, 3), "grip_top": round(gtop, 3)}


def glass_surface(side):
    """(y, z) -> (point, outward normal) on the door's outer glass (side +1 left, -1 right)."""
    glass = next(o for o in stock("EXT_GLASS_DOOR_L" if side > 0 else "EXT_GLASS_DOOR_R") if o.type == "MESH")
    bvh = bvh_of([glass])

    def at(y, z):
        hit = bvh.ray_cast(Vector((side * 1.3, y, z)), Vector((-side, 0, 0)), 1.0)
        n = hit[1].normalized()
        return hit[0], (n if n.x * side > 0 else -n)
    return at


def channel(bm, uv, at, a, b, w, h, base=0.0005, step=0.02):
    """Straight black channel strip on the glass from (y, z) a to b: w wide, from `base` to h off the surface."""
    a, b = Vector(a), Vector(b)
    n = max(2, int((b - a).length / step) + 1)
    rings = []
    for i in range(n):
        q = a.lerp(b, i / (n - 1))
        p, nrm = at(q.x, q.y)
        p2, _ = at(*(q + (b - a).normalized() * 0.005))
        t = (p2 - p).normalized()
        s = nrm.cross(t).normalized()
        rings.append([bm.verts.new(p + s * sw * w / 2 + nrm * hh) for sw, hh in ((-1, base), (1, base), (1, h), (-1, h))])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    bm.faces.new(rings[0]); bm.faces.new(rings[-1][::-1])


def build_windows():
    """Rally sliding windows (SLIDER) in both door glasses: black frame + slider pane + grab tab, on the door nodes."""
    s = SLIDER
    w, hp = s["channel"], s["proud"]
    black = load("build_cage").cage_material()
    glass, ws = stock_material("glass"), stock_material("ws_glass")
    made = []
    for side, tag in ((1, "L"), (-1, "R")):
        at = glass_surface(side)
        door = next(o for o in stock(f"DOOR_{tag}") if o.type == "EMPTY")
        y0, y1, z0, z1, yd = s["y0"], s["y1"], s["z0"], s["z1"], s["ydiv"]
        e = w / 2
        bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
        for a, b in (((y0 - e, z0), (y1 + e, z0)), ((y0 - e, z1), (y1 + e, z1)),       # bottom and top rails
                     ((y0, z0 + e), (y0, z1 - e)), ((y1, z0 + e), (y1, z1 - e)),       # ends
                     ((yd, z0 + e), (yd, z1 - e))):                                    # divider
            channel(bm, uv, at, a, b, w, hp)
        # grab tab on the slider, near its trailing edge
        tw, th, tp = s["tab"]
        channel(bm, uv, at, (yd - 0.035, (z0 + z1) / 2 - th / 2), (yd - 0.035, (z0 + z1) / 2 + th / 2), tw, tp,
                base=s["pane_out"])
        for f in bm.faces:
            for lp in f.loops:
                lp[uv].uv = (0.0, 0.0)
        frame = new_object(f"RALLY_slider_frame_{tag}", load("build_cage").finish(bm), [black], door,
                           no_lod=True, rally_window=tag)
        # the slider pane: a second sheet in the channels, just outboard of the glass (outer face glass, inner ws)
        bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
        ys = [y0 + e * 0.6 + (yd + 0.012 - y0 - e * 0.6) * i / 8 for i in range(9)]
        zs = [z0 + e * 0.6 + (z1 - z0 - e * 1.2) * j / 4 for j in range(5)]
        for mi, off, want in ((0, s["pane_out"] + 0.0006, 1), (1, s["pane_out"], -1)):
            grid = [[bm.verts.new(at(y, z)[0] + at(y, z)[1] * off) for z in zs] for y in ys]
            for i in range(len(ys) - 1):
                for j in range(len(zs) - 1):
                    f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
                    f.normal_update()
                    if f.normal.x * side * want < 0:
                        f.normal_flip()
                    f.material_index = mi
                    for lp in f.loops:
                        lp[uv].uv = ((lp.vert.co.y - y0) * 2, lp.vert.co.z * 2)
        pane = load("build_cage").make_obj(f"RALLY_slider_pane_{tag}", bm, [glass, ws], door)
        pane["no_lod"] = True; pane["rally_window"] = tag
        made += [frame.name, pane.name]
    return made


def build():
    bpy.context.view_layer.update()
    restore_modified()                              # (last build's handbrake move / bonnet cut)
    for o in [o for o in bpy.data.objects if o.name == "RALLY_shifter_riser"
              or (o.get("rally_shifter") and not o.name.startswith("RALLY_shifter_gear_shift_sub001"))]:
        remove(o)
    scoop, cut = build_scoop()
    pins = build_pins()
    plate = lift_plate()
    shifter, shifter_info = build_shifter()
    handbrake, hb_info = build_handbrake()
    exhaust = build_exhaust()
    old = remove_old_controls()
    needles = red_needles()
    stripes = lift_stripes()
    windows = build_windows()
    return {"made": [scoop.name, pins.name] + shifter + handbrake + windows, "plate": plate, "bonnet_cut": cut,
            "shifter": shifter_info, "handbrake": hb_info, "exhaust": exhaust, "old_controls_removed": old,
            "needles": needles, "stripes_lifted": stripes}
