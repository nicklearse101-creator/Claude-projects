"""Phase 4 interior for the Nova GTE (RHD), first full pass (runs inside Blender).

Layout from the FIA form p16 (interior width at the front seats 1280 mm, headroom above the front seat 959 mm,
steering wheel to brake pedal 635 mm, steering wheel to rear bulkhead 1540 mm) and the owner photos of F294 DVR
(redgte_08/09/10/11/12/15/35): grey dash with a flat top pad, angular instrument hood on the right, centre stack
(radio, two square vents, clock, hazard switch), glovebox lid with a pull handle, open parcel rail under the
dash, small console with switch blanks, gear lever with gaiter, handbrake between the seats, GTE sport seats in
grey cloth with red pinstripes, three-spoke wheel with a round griffin boss. Shapes are ESTIMATE from photos.

Instruments: speedo 20-120 mph (km/h inner), four small gauges (voltmeter, oil pressure, coolant temp, fuel),
tacho 0-7 x1000 with the orange band from ~6.4. Needles are separate objects pivoting about their local -Y
(AC's local Z after the exporter's axis change): ARROW_SPEED, ARROW_RPM, ARROW_FUEL, ARROW_WATER, ARROW_OIL,
ARROW_VOLT.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

COLL = "INTERIOR"
DRV_X = -0.36                       # driver centreline (RHD, car's right = -X)
PAS_X = 0.36


def coll():
    c = bpy.data.collections.get(COLL) or bpy.data.collections.new(COLL)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def mat(name, rgba, preset="trim"):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = rgba
    m.diffuse_color = rgba
    m["ac_preset"] = preset
    m["ac_shader"] = "ksPerPixelMultiMap"
    return m


def remove(name):
    o = bpy.data.objects.get(name)
    if o:
        for ch in list(o.children):
            remove(ch.name)
        me = o.data
        bpy.data.objects.remove(o)
        if me and getattr(me, "users", 1) == 0:
            bpy.data.meshes.remove(me)


def obj(name, bm, mats, bevel=0.0, seg=2, smooth=True, parent=None, loc=None):
    remove(name)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    for m in mats:
        o.data.materials.append(m)
    coll().objects.link(o)
    if parent:
        o.parent = parent
    if loc:
        o.location = loc
    if bevel:
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = seg
        b.limit_method = "ANGLE"
        b.harden_normals = False
    return o


def box(bm, lo, hi, mi=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r["verts"]:
        v.co = Vector(((lo[0] if v.co.x < 0 else hi[0]), (lo[1] if v.co.y < 0 else hi[1]), (lo[2] if v.co.z < 0 else hi[2])))
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mi
    return r["verts"]


def prism(bm, profile_yz, x0, x1, mi=0):
    """Extrude a closed (y, z) profile along X from x0 to x1."""
    a = [bm.verts.new((x0, y, z)) for y, z in profile_yz]
    b = [bm.verts.new((x1, y, z)) for y, z in profile_yz]
    n = len(profile_yz)
    faces = [bm.faces.new(a[::-1]), bm.faces.new(b)]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in faces:
        f.material_index = mi
    return faces


def cylinder(bm, centre, axis, radius, depth, seg=32, mi=0, r2=None):
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius, radius2=radius if r2 is None else r2, depth=depth)
    rot = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(centre) @ rot, verts=r["verts"])
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mi
    return r["verts"]


# ---------------------------------------------------------------- materials
def materials():
    return {
        "dash": mat("int_dash_grey", (0.20, 0.205, 0.21, 1)),
        "dark": mat("int_dark_grey", (0.07, 0.07, 0.075, 1)),
        "carpet": mat("int_carpet", (0.035, 0.035, 0.04, 1)),
        "cloth": mat("int_seat_cloth", (0.30, 0.30, 0.31, 1)),
        "stripe": mat("int_seat_stripe", (0.34, 0.26, 0.26, 1)),   # grey cloth with red pinstripes, averaged until textured
        "vinyl": mat("int_vinyl_grey", (0.24, 0.24, 0.25, 1)),
        "dial": mat("int_dial_black", (0.012, 0.012, 0.014, 1)),
        "mark": mat("int_dial_white", (0.85, 0.85, 0.82, 1), "lens"),
        "needle": mat("int_needle", (0.92, 0.80, 0.62, 1), "lens"),
        "orange": mat("int_dial_orange", (0.85, 0.35, 0.05, 1), "lens"),
        "chrome": bpy.data.materials["rim_alloy"],
        "red": mat("int_switch_red", (0.60, 0.03, 0.02, 1), "lens"),
        "head": mat("int_headlining", (0.42, 0.42, 0.41, 1)),
    }


_INNER = {}


def inner_x(y, z):
    """Half-width of the cabin at (y, z): first hit of a ray from the centreline outward onto the body's inner
    surface (BODY_shell with its Inner solidify, or BODY_glass). None where the ray escapes (arch openings)."""
    if "trees" not in _INNER:
        from mathutils.bvhtree import BVHTree
        dg = bpy.context.evaluated_depsgraph_get()
        _INNER["trees"] = [(BVHTree.FromObject(bpy.data.objects[n], dg), bpy.data.objects[n].matrix_world.copy())
                           for n in ("BODY_shell", "BODY_glass")]
    best = None
    for t, M in _INNER["trees"]:
        Mi = M.inverted()
        h = t.ray_cast(Mi @ Vector((0.0, y, z)), (Mi.to_3x3() @ Vector((1, 0, 0))).normalized())
        if h[0] is not None:
            w = M @ h[0]
            best = w.x if best is None else min(best, w.x)
    return best


def fitted_loft(bm, profile, x_of, n=40, mi=0, closed=True, caps=True):
    """Loft a (y, z) profile across the cabin: each profile point spans -x_of(y, z) .. +x_of(y, z), so the part
    follows the body's inner surface at its ends. Returns the grid of verts [row][col]."""
    rows = []
    for y, z in profile:
        X = x_of(y, z)
        rows.append([bm.verts.new((-X + 2 * X * j / n, y, z)) for j in range(n + 1)])
    nr = len(rows)
    for i in range(nr if closed else nr - 1):
        r0, r1 = rows[i], rows[(i + 1) % nr]
        for j in range(n):
            bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j])).material_index = mi
    if caps and closed:
        bm.faces.new([r[0] for r in rows]).material_index = mi
        bm.faces.new([r[-1] for r in rows][::-1]).material_index = mi
    return rows


def box_between(bm, a, b, w, h, mi=0):
    """Box of width w (horizontal, square to a->b) and height h from point a to point b."""
    d = (b - a); d.normalize()
    side = Vector((0, 0, 1)).cross(d)
    side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
    up = d.cross(side).normalized()
    if up.z < 0:
        up = -up
    vs = []
    for e in (a, b):
        for ss, uu in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vs.append(bm.verts.new(e + side * (ss * w / 2) + up * (uu * h / 2)))
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([vs[i] for i in f]).material_index = mi
    return vs


BELT = [(-1.772, 0.76), (-1.0, 0.81), (-0.7, 0.88), (-0.64, 0.845), (-0.4, 0.8341), (0.0, 0.8405), (0.5, 0.8485),
        (1.0, 0.8565), (1.45, 0.8637), (1.776, 0.85)]          # body_profile belt (photo frame)


def _interp(pts, y):
    if y <= pts[0][0]:
        return pts[0][1]
    for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
        if y <= y1:
            return z0 + (z1 - z0) * (y - y0) / (y1 - y0)
    return pts[-1][1]


# ---------------------------------------------------------------- dashboard
DASH_TOP = 0.985                     # top pad height (photo: just under the screen base line)
DASH_FACE_Y = -0.42                  # vertical face of the dash (driver side of the pad)
SCREEN_BASE_Y = -0.69
HALF_IN = 0.64                       # interior half-width at the front seats (FIA 1280 mm)


def build_dash(M):
    bm = bmesh.new()
    # main pad: closed y-z profile lofted across the cabin and trimmed to the body's inner surface at every point
    # (screen corners / A-pillar bases / doors), so its ends can't poke through the shell. Flat top with the defrost
    # strip along the screen, rounded brow, slightly raked face, open parcel tray under it (photos 08 / 15)
    pad = [(-0.662, 0.930), (-0.650, 0.972), (-0.620, 0.984), (-0.470, 0.988), (-0.440, 0.984), (-0.421, 0.973),
           (-0.412, 0.956), (DASH_FACE_Y + 0.010, 0.930), (DASH_FACE_Y + 0.006, 0.800), (DASH_FACE_Y - 0.004, 0.700),
           (DASH_FACE_Y - 0.014, 0.640), (DASH_FACE_Y - 0.040, 0.624), (-0.52, 0.620), (-0.60, 0.660), (-0.662, 0.750)]
    fitted_loft(bm, pad, lambda y, z: min((inner_x(y, z) or HALF_IN) - 0.006, 0.66), n=48, mi=0)
    # defrost grille: dark strip along the front of the top pad
    fitted_loft(bm, [(-0.640, 0.9805), (-0.612, 0.9875), (-0.612, 0.9895), (-0.640, 0.9825)],
                lambda y, z: min((inner_x(y, z) or HALF_IN) - 0.08, 0.58), n=24, mi=1)
    # glovebox lid (passenger side, slightly proud) with a recessed pull handle
    box(bm, (0.08, DASH_FACE_Y + 0.006, 0.66), (0.54, DASH_FACE_Y + 0.020, 0.84), 0)
    box(bm, (0.24, DASH_FACE_Y + 0.019, 0.775), (0.32, DASH_FACE_Y + 0.030, 0.805), 1)
    # parcel rail under the dash: an open tray across the full width with a grille strip
    box(bm, (-HALF_IN, DASH_FACE_Y - 0.06, 0.555), (HALF_IN, DASH_FACE_Y + 0.05, 0.575), 0)
    box(bm, (-HALF_IN, DASH_FACE_Y + 0.04, 0.575), (HALF_IN, DASH_FACE_Y + 0.055, 0.60), 0)
    # end vents (black louvred squares) on both sides, inboard of the door seals
    for sx in (-1, 1):
        box(bm, (sx * 0.555 - 0.04, DASH_FACE_Y + 0.008, 0.78), (sx * 0.555 + 0.04, DASH_FACE_Y + 0.02, 0.88), 1)
    o = obj("INT_DASH", bm, [M["dash"], M["dark"]], bevel=0.004)
    return o


def build_centre_stack(M):
    bm = bmesh.new()
    x0, x1 = -0.13, 0.16                  # stack between the binnacle and the glovebox (photo 08)
    box(bm, (x0, DASH_FACE_Y - 0.02, 0.60), (x1, DASH_FACE_Y + 0.035, 0.955), 0)     # housing
    box(bm, (x0 + 0.015, DASH_FACE_Y + 0.034, 0.865), (x1 - 0.015, DASH_FACE_Y + 0.045, 0.925), 1)   # radio (Philips)
    for cx in (-0.075, 0.035):                                                      # two square vents
        box(bm, (cx - 0.045, DASH_FACE_Y + 0.034, 0.765), (cx + 0.045, DASH_FACE_Y + 0.046, 0.845), 1)
    for cx in (0.105, 0.135):                                                       # vertical sliders
        box(bm, (cx - 0.008, DASH_FACE_Y + 0.034, 0.70), (cx + 0.008, DASH_FACE_Y + 0.044, 0.845), 1)
    box(bm, (-0.12, DASH_FACE_Y + 0.034, 0.69), (-0.06, DASH_FACE_Y + 0.044, 0.75), 1)   # clock
    box(bm, (-0.045, DASH_FACE_Y + 0.040, 0.705), (-0.025, DASH_FACE_Y + 0.050, 0.725), 2)   # hazard switch
    box(bm, (0.005, DASH_FACE_Y + 0.034, 0.69), (0.075, DASH_FACE_Y + 0.044, 0.75), 1)   # heater knob panel
    # console: from the stack down to the floor, switch blanks, then the gear lever surround
    box(bm, (-0.09, DASH_FACE_Y + 0.02, 0.28), (0.09, DASH_FACE_Y + 0.33, 0.55), 0)
    box(bm, (-0.075, DASH_FACE_Y + 0.05, 0.50), (0.075, DASH_FACE_Y + 0.16, 0.555), 1)  # switch blanks
    return obj("INT_CONSOLE", bm, [M["dash"], M["dark"], M["red"]], bevel=0.004)


def build_binnacle(M):
    """Angular hood over the cluster, cluster face and dials (driver side, RHD)."""
    bm = bmesh.new()
    cx, w = DRV_X, 0.20                    # cluster half-width ~200 mm (6 dials across, photo 10)
    # cluster face just proud of the dash face (the driver sits towards +Y); the hood is an open visor:
    # top plate, two cheeks and a lower lip, so the dials stay visible
    face_y, face_z0, face_z1 = DASH_FACE_Y + 0.022, 0.80, 0.93      # clear of the pad's sloping face
    box(bm, (cx - w - 0.02, face_y - 0.02, face_z1 + 0.03), (cx + w + 0.02, face_y + 0.13, face_z1 + 0.05), 0)   # visor
    for sx in (-1, 1):
        cheek = [(face_y, face_z0 - 0.03), (face_y, face_z1 + 0.03), (face_y + 0.13, face_z1 + 0.03), (face_y + 0.05, face_z0 - 0.03)]
        prism(bm, cheek, cx + sx * (w + 0.02) - 0.012, cx + sx * (w + 0.02) + 0.012, 0)
    box(bm, (cx - w - 0.02, face_y, face_z0 - 0.035), (cx + w + 0.02, face_y + 0.05, face_z0 - 0.015), 0)       # lower lip
    box(bm, (cx - w, face_y - 0.004, face_z0), (cx + w, face_y, face_z1), 1)                                    # black cluster face
    o = obj("INT_BINNACLE", bm, [M["dash"], M["dial"]], bevel=0.004)

    # dials: printed rings as thin discs on the face, numbers left to a texture later
    dials = {   # name: (x offset, z, radius, needle name, zero angle note)
        "SPEED": (-0.125, 0.865, 0.058, "ARROW_SPEED"),
        "VOLT": (-0.025, 0.893, 0.027, "ARROW_VOLT"),
        "OIL": (0.050, 0.893, 0.027, "ARROW_OIL"),
        "WATER": (-0.025, 0.833, 0.027, "ARROW_WATER"),
        "FUEL": (0.050, 0.833, 0.027, "ARROW_FUEL"),
        "RPM": (0.138, 0.865, 0.058, "ARROW_RPM"),
    }
    # car's right is -X and the driver looks towards -Y, so the driver's left (speedo side) is +X... the
    # cluster is seen from behind: image-left in photo 10 = car's left = +X. Mirror the offsets accordingly.
    for name, (dx, z, r, needle) in dials.items():
        x = cx - dx
        bm = bmesh.new()
        cylinder(bm, (x, face_y + 0.002, z), (0, 1, 0), r, 0.004, seg=48, mi=0)
        # tick ring: 12 small marks around the 270-degree sweep
        for k in range(13):
            a = math.radians(225 - 270 * k / 12)
            tx, tz = x - math.cos(a) * r * 0.85, z + math.sin(a) * r * 0.85
            box(bm, (tx - 0.0015, face_y + 0.004, tz - 0.0015), (tx + 0.0015, face_y + 0.0055, tz + 0.0015), 1)
        if name == "RPM":   # orange band from ~6.4 to 7 (x1000)
            for k in range(3):
                a = math.radians(225 - 270 * (6.4 + 0.3 * k) / 7)
                tx, tz = x - math.cos(a) * r * 0.85, z + math.sin(a) * r * 0.85
                box(bm, (tx - 0.003, face_y + 0.004, tz - 0.003), (tx + 0.003, face_y + 0.0058, tz + 0.003), 2)
        obj(f"INT_DIAL_{name}", bm, [M["dial"], M["mark"], M["orange"]], smooth=False)
        # needle: object origin at the pivot, pointing straight up at rest (AC adds ZERO + value * STEP)
        bm = bmesh.new()
        box(bm, (-0.0012, 0.0, -0.010), (0.0012, 0.0015, r * 0.88), 0)
        cylinder(bm, (0, 0.002, 0), (0, 1, 0), 0.006, 0.004, seg=16, mi=1)
        obj(needle, bm, [M["needle"], M["dial"]], smooth=False, loc=(x, face_y + 0.006, z))
    return o


def build_steering(M):
    """Column, shroud, stalks and the three-spoke GTE wheel. STEER_HR is the rotating node AC turns about its
    local Z (Blender local -Y after the axis change), so the wheel is built square to the column."""
    tilt = math.radians(24)                 # column angle from horizontal (photo 08/11, ESTIMATE)
    centre = Vector((DRV_X, -0.29, 0.86))   # wheel centre (FIA p16 wheel->pedal 635 mm with pedals at y -0.75)
    steer = bpy.data.objects["STEER_HR"]
    steer.location = centre
    steer.rotation_euler = (-tilt, 0, 0)
    for ch in list(steer.children):
        remove(ch.name)
    # wheel in STEER_HR local space: rim in the local XZ plane (normal along local Y)
    R, tube = 0.183, 0.016                  # 370 mm wheel (ESTIMATE)
    bm = bmesh.new()
    seg, tseg = 64, 12
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new(((R + tube * math.cos(2 * math.pi * j / tseg)) * c,
                                     tube * math.sin(2 * math.pi * j / tseg) * 1.25,
                                     (R + tube * math.cos(2 * math.pi * j / tseg)) * s)) for j in range(tseg)])
    for i in range(seg):
        for j in range(tseg):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % tseg], rings[i][(j + 1) % tseg]))
    # three spokes (left, right slightly below centre, and bottom), each a flat bar with a lightening hole look
    for a_deg in (190, -10, 270):
        a = math.radians(a_deg)
        d = Vector((math.cos(a), 0, math.sin(a)))
        side = Vector((-d.z, 0, d.x))
        p0, p1 = d * 0.05, d * (R - 0.01)
        quad = [p0 + side * 0.03, p1 + side * 0.022, p1 - side * 0.022, p0 - side * 0.03]
        vs_a = [bm.verts.new(v + Vector((0, -0.006, 0))) for v in quad]
        vs_b = [bm.verts.new(v + Vector((0, 0.006, 0))) for v in quad]
        bm.faces.new(vs_a[::-1]); bm.faces.new(vs_b)
        for k in range(4):
            bm.faces.new((vs_a[k], vs_a[(k + 1) % 4], vs_b[(k + 1) % 4], vs_b[k]))
    # round boss with the griffin badge (badge detail left to the texture)
    cylinder(bm, (0, -0.02, 0), (0, 1, 0), 0.062, 0.05, seg=40, mi=0, r2=0.058)
    w = obj("STEER_WHEEL", bm, [M["dark"]], bevel=0.0, parent=steer)
    w.matrix_parent_inverse.identity()
    # column shroud and stalks (fixed, not under STEER_HR)
    bm = bmesh.new()
    sh = [(0.0, -0.05), (0.0, 0.05), (0.22, 0.06), (0.22, -0.06)]
    shroud = [(centre.y - 0.04 - u * math.cos(tilt), centre.z - 0.03 + v - u * math.sin(tilt)) for u, v in sh]
    prism(bm, shroud, DRV_X - 0.055, DRV_X + 0.055, 0)
    for sx in (-1, 1):
        box(bm, (DRV_X + sx * 0.055, centre.y - 0.09, centre.z - 0.01), (DRV_X + sx * 0.16, centre.y - 0.075, centre.z + 0.005), 0)
    obj("INT_COLUMN", bm, [M["dark"]], bevel=0.008)


def build_pedals_controls(M):
    bm = bmesh.new()
    # pedals: clutch, brake, throttle (left to right from the driver = +X to -X on a RHD car)
    for i, dx in enumerate((0.11, 0.0, -0.11)):
        x = DRV_X + dx
        w = 0.035 if i == 2 else 0.05
        box(bm, (x - w, -0.76, 0.33), (x + w, -0.745, 0.41), 0)          # pad
        box(bm, (x - 0.008, -0.79, 0.40), (x + 0.008, -0.76, 0.55), 0)    # arm
    obj("INT_PEDALS", bm, [M["dark"]], bevel=0.004)
    # gear lever (gaiter cone + rod + round knob), handbrake lever between the seats
    bm = bmesh.new()
    cylinder(bm, (0.0, -0.09, 0.50), (0, 0.0, 1), 0.055, 0.07, seg=24, mi=0, r2=0.02)
    cylinder(bm, (0.0, -0.10, 0.62), (0, -0.15, 1), 0.006, 0.17, seg=12, mi=1)
    knob = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.023)
    bmesh.ops.translate(bm, vec=(0.0, -0.115, 0.72), verts=knob["verts"])
    obj("INT_GEARLEVER", bm, [M["dark"], M["chrome"]])
    bm = bmesh.new()
    box(bm, (-0.035, 0.05, 0.28), (0.035, 0.30, 0.36), 0)                 # tunnel console
    box(bm, (-0.012, 0.05, 0.34), (0.012, 0.27, 0.38), 1)                  # handbrake lever
    obj("INT_HANDBRAKE", bm, [M["dash"], M["dark"]], bevel=0.006)


def seat(M, name, x, y_back, rear=False):
    """GTE sport seat: cushion with side bolsters, backrest with wings, integrated headrest; cloth with a
    red-striped centre panel (stripes are a texture job, here a single stripe material on the centre)."""
    bm = bmesh.new()
    w = 0.25
    cz = 0.40                                   # cushion top (FIA headroom 959 mm to the headlining)
    box(bm, (x - w, y_back - 0.50, cz - 0.10), (x + w, y_back - 0.02, cz - 0.03), 0)          # cushion base
    box(bm, (x - w + 0.06, y_back - 0.49, cz - 0.03), (x + w - 0.06, y_back - 0.03, cz), 1)   # centre panel
    for sx in (-1, 1):
        box(bm, (x + sx * (w - 0.03) - 0.03, y_back - 0.49, cz - 0.03), (x + sx * (w - 0.03) + 0.03, y_back - 0.05, cz + 0.035), 0)
    # backrest, leaning back ~20 deg
    lean = math.radians(20)
    back = bmesh.new()
    box(back, (-w, -0.05, 0.0), (w, 0.04, 0.62), 0)
    box(back, (-w + 0.07, -0.065, 0.06), (w - 0.07, -0.04, 0.50), 1)
    for sx in (-1, 1):
        box(back, (sx * (w - 0.03) - 0.035, -0.11, 0.05), (sx * (w - 0.03) + 0.035, -0.02, 0.48), 0)
    box(back, (-0.13, -0.06, 0.62), (0.13, 0.03, 0.82), 0)                                  # headrest
    me = bpy.data.meshes.new("tmp")
    back.to_mesh(me); back.free()
    tb = bmesh.new(); tb.from_mesh(me); bpy.data.meshes.remove(me)
    bmesh.ops.transform(tb, matrix=Matrix.Translation((x, y_back, cz - 0.03)) @ Matrix.Rotation(-lean, 4, "X"), verts=tb.verts[:])
    me2 = bpy.data.meshes.new("tmp2"); tb.to_mesh(me2); tb.free()
    bm.from_mesh(me2); bpy.data.meshes.remove(me2)
    # runner / base frame to the floor
    box(bm, (x - 0.20, y_back - 0.45, 0.27), (x + 0.20, y_back - 0.08, cz - 0.10), 2)
    return obj(name, bm, [M["cloth"], M["stripe"], M["dark"]], bevel=0.018, seg=3)


def build_seats(M):
    seat(M, "INT_SEAT_DRIVER", DRV_X, 0.30)
    seat(M, "INT_SEAT_PASSENGER", PAS_X, 0.30)
    # rear bench: cushion + back, full width between the arches (photo 35)
    bm = bmesh.new()
    box(bm, (-0.55, 0.62, 0.30), (0.55, 1.05, 0.40), 0)
    box(bm, (-0.45, 0.64, 0.40), (0.45, 1.03, 0.415), 1)
    back = [(1.05, 0.40), (1.16, 0.40), (1.27, 0.95), (1.18, 0.96)]
    prism(bm, back, -0.55, 0.55, 0)
    return obj("INT_REAR_SEAT", bm, [M["cloth"], M["stripe"]], bevel=0.02, seg=3)


def build_floor_trim(M):
    bm = bmesh.new()
    # carpeted floor pan with a centre tunnel, from the bulkhead to the rear seat
    box(bm, (-0.70, -0.80, 0.255), (0.70, 0.78, 0.275), 0)
    box(bm, (-0.49, 0.78, 0.255), (0.49, 1.10, 0.275), 0)          # between the rear wheel houses
    tunnel = [(-0.80, 0.275), (-0.80, 0.33), (0.50, 0.33), (0.50, 0.275)]
    prism(bm, tunnel, -0.10, 0.10, 0)
    # toe board / bulkhead up to the dash
    prism(bm, [(-0.80, 0.275), (-0.92, 0.45), (-0.80, 0.62), (-0.76, 0.62), (-0.76, 0.275)], -0.66, 0.66, 0)
    obj("INT_FLOOR", bm, [M["carpet"]], bevel=0.01)
    # door cards: a panel following the door's inner skin 12 mm in, from the shut lines to just under the belt
    # (photo 14): padded upper band with the red pinstripe under it, diagonal pull / armrest in the front half,
    # door release at the front top, window winder front-low, long map pocket along the bottom
    DZ_ = 0.0193
    belt = lambda y: _interp(BELT, y) + DZ_
    y0, y1 = -0.645, 0.445
    for sx, nm in ((1, "L"), (-1, "R")):
        bm = bmesh.new()
        ny, nz = 28, 12
        grid = []
        for i in range(ny + 1):
            y = y0 + (y1 - y0) * i / ny
            col = []
            for j in range(nz + 1):
                z = 0.31 + (belt(y) - 0.018 - 0.31) * j / nz
                xi = inner_x(y, z) or 0.70
                band = 0.006 if z > 0.715 + DZ_ else 0.0          # padded upper band stands proud
                col.append(bm.verts.new((sx * (xi - 0.012 - band), y, z)))
            grid.append(col)
        for i in range(ny):
            for j in range(nz):
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                bm.faces.new(q if sx < 0 else q[::-1]).material_index = 0
        xa = lambda y, z: sx * ((inner_x(y, z) or 0.70) - 0.012)
        # red pinstripe under the padded band
        za = 0.712 + DZ_
        for i in range(ny):
            ya_, yb_ = y0 + (y1 - y0) * i / ny, y0 + (y1 - y0) * (i + 1) / ny
            q = [bm.verts.new((xa(ya_, za) - sx * 0.002, ya_, za)), bm.verts.new((xa(yb_, za) - sx * 0.002, yb_, za)),
                 bm.verts.new((xa(yb_, za) - sx * 0.002, yb_, za + 0.004)), bm.verts.new((xa(ya_, za) - sx * 0.002, ya_, za + 0.004))]
            bm.faces.new(q if sx < 0 else q[::-1]).material_index = 3
        # diagonal pull / armrest: front-low to rear-high
        pa, pb = Vector((xa(-0.38, 0.60), -0.38, 0.60)), Vector((xa(0.02, 0.665), 0.02, 0.665))
        box_between(bm, pa - Vector((sx * 0.025, 0, 0)), pb - Vector((sx * 0.025, 0, 0)), 0.05, 0.035, 1)
        # map pocket along the bottom
        xp = xa(0.0, 0.40)
        box(bm, (min(xp, xp - sx * 0.025), -0.56, 0.33), (max(xp, xp - sx * 0.025), 0.30, 0.43), 1)
        # door release lever (chrome) front-top, window winder front-low
        xr = xa(-0.56, 0.74)
        box(bm, (min(xr, xr - sx * 0.015), -0.585, 0.732), (max(xr, xr - sx * 0.015), -0.535, 0.748), 2)
        xw = xa(-0.46, 0.53)
        cylinder(bm, (xw - sx * 0.012, -0.46, 0.53), (sx, 0, 0), 0.035, 0.024, seg=24, mi=1)
        box(bm, (min(xw - sx * 0.024, xw - sx * 0.034), -0.47, 0.53), (max(xw - sx * 0.024, xw - sx * 0.034), -0.45, 0.60), 2)
        obj(f"INT_DOORCARD_{nm}", bm, [M["vinyl"], M["dash"], M["chrome"], M["red"]], bevel=0.0)
        # rear side trim behind the door: follows the inner skin; over the wheel arch only above the arch
        bm = bmesh.new()
        ys = [0.47 + (1.30 - 0.47) * i / 16 for i in range(17)]
        grid = []
        for y in ys:
            zlo = 0.32 if y < 0.78 else 0.64
            col = []
            for j in range(9):
                z = zlo + (belt(y) - 0.018 - zlo) * j / 8
                xi = inner_x(y, z) or 0.66
                col.append(bm.verts.new((sx * (xi - 0.012), y, z)))
            grid.append(col)
        for i in range(len(ys) - 1):
            for j in range(8):
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                bm.faces.new(q if sx < 0 else q[::-1])
        obj(f"INT_QUARTER_TRIM_{nm}", bm, [M["vinyl"]], bevel=0.0)
    # parcel shelf / load cover
    bm = bmesh.new()
    box(bm, (-0.62, 1.20, 0.86), (0.62, 1.62, 0.875), 0)
    obj("INT_PARCEL_SHELF", bm, [M["dark"]], bevel=0.004)


def inner_shell(M):
    """Give the body an inside: Solidify the shell inwards; inner faces take materials offset by the shell's
    material count, mapped to interior colours (headlining, trim, glass stays glass)."""
    ob = bpy.data.objects["BODY_shell"]
    base = [m.name for m in ob.data.materials][:8]
    inner = {"paint_gunmetal": M["head"], "glass_tint": bpy.data.materials["glass_tint"], "trim_black": M["dark"],
             "trim_grey": M["dark"], "lamp_clear": M["dark"], "lamp_red": M["dark"], "lamp_amber": M["dark"],
             "panel_gap": M["dark"]}
    while len(ob.data.materials) > 8:
        ob.data.materials.pop()
    for n in base:
        ob.data.materials.append(inner[n])
    sol = ob.modifiers.get("Inner") or ob.modifiers.new("Inner", "SOLIDIFY")
    sol.thickness = 0.012
    sol.offset = -1.0
    sol.use_even_offset = False          # even offset blows up at any zero-area sliver (10 m spikes, 2026-10-13)
    sol.use_rim = False
    sol.material_offset = 8
    # keep Solidify after Mirror and before the arch Booleans
    while ob.modifiers.find("Inner") > 1:
        bpy.ops.object.modifier_move_up({"object": ob}, modifier="Inner") if False else ob.modifiers.move(ob.modifiers.find("Inner"), 1)
    return ob


def build():
    M = materials()
    build_dash(M)
    build_centre_stack(M)
    build_binnacle(M)
    build_steering(M)
    build_pedals_controls(M)
    build_seats(M)
    build_floor_trim(M)
    inner_shell(M)
    # driver reference points
    for n, loc in (("COCKPIT_HR", (DRV_X, 0.10, 1.13)), ("COCKPIT_LR", (DRV_X, 0.10, 1.13))):
        bpy.data.objects[n].location = loc
    return sorted(o.name for o in coll().objects)


if __name__ == "__main__":
    print(build())
