"""Stripped rear interior, bucket seats, harnesses + roll cage for the rally Sunbeam (runs in Blender on
sunbeam_rally_on_stock_model.blend; called from build_rally_parts.build()).

Seats + harnesses: the Escort Mk2 donor's high-back buckets and its harness belts replace the stock front seats and
3-point belts (fit_buckets, fit_harness). Both are placed from the driver's skeleton: the two cars use the same
driver_70 pose, and in bone terms (steer.ksanim centre frame on driver_base_pos.knh) our driver sits 14.7 cm
further forward and 14.9 cm lower than the Escort's - so seats and belts go exactly there (lifted 1 cm so the bucket
flanges clear the carpet) and sit on/around our driver as they did on the Escort's. The Escort is right-hand drive:
the driver's belts (worn = CINTURE_ON, loose = CINTURE_OFF, the nodes AC switches with the driver) are mirrored onto
our left-hand seat; the passenger seat gets the Escort driver's loose belt as it is. The shoulder straps wrap round
a harness bar across the main hoop.

Cage: the one Talbot recommended in the FIA homologation (form 1700, amendment 7, photo 11 -
refs/homologation/pages/img24.jpg): Safety Devices, 38 mm (1.5 in) x 2.74 mm tube throughout, 22.7 kg, six feet.
  * main hoop just behind the B-pillar (behind the stock seat-belt reels), legs vertical to the belt line then
    leaning in with the quarter-window glass, straight top bar under the headlining
  * front hoop up the A-pillars (bent back at the dash top) and across the top of the windscreen
  * a roof bar each side joining the hoop corners
  * two rear stays from the main hoop corners down onto the rear wheel-arch tops, and one diagonal from the
    right-hand stay foot up to the left-hand main hoop corner (as in the photo)
Positions were measured against the cabin trim with ray casts; check() reports each member's clearance.

Rear interior: the rear bench and parcel shelf and the seat back's boot-side panels go; the rear side trims,
armrests and boot carpet/trims stay but are repainted in the car's own black painted metal. The stock model has
no floor under the bench and the boot's front wall only faces the boot (AC draws one side of a face), so a
bulkhead panel facing the cabin and a floor strip up to it are added (RALLY_rear_bulkhead).
The sun visors go too - the front hoop's header bar runs where they hang.

Coordinates: Blender world, x = car's left, -y = front, z up (same as build_rally_parts). Symmetric parts are
given for the left side and mirrored.
"""
import importlib.util
import json
import math

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

TOOLS = r"D:\Claude\talbot_sunbeam_lotus\tools"

TUBE_R = 0.019            # 38 mm tube (homologation)
SEGMENTS = 16
PLATE = (0.090, 0.090, 0.005)   # foot plates (x, y, thickness)
CAGE_TEX = "rgba101010ff.dds"   # satin black (Nick 2026-09-28; first version dark grey 383838)

STRIP = ("parcelshelf_a_SUB0", "parcelshelf_a_SUB1", "parcelshelf_a_SUB2",   # rear bench, parcel shelf
         "trunkbay_a_SUB8", "trunkbay_a_SUB10",                            # back of the rear seat (boot side)
         "ficelles",                                                       # tailgate strings to the parcel shelf
         "pillartrim_a_SUB2",                                              # sun visors
         "seatl_a_SUB0", "seatl_a_SUB1", "seatl_a_SUB2", "seatl_a_SUB3", "seatl_a_SUB4", "seatl_a_SUB5",  # seats
         "seatbeltl_a_SUB0", "seatbeltl_a_SUB1", "seatbeltl_a_SUB2", "seatbeltl_a_SUB3", "seatbeltl_a_SUB4",
         "seatbeltl_a_SUB5")                                               # stock 3-point belts

# Escort -> our car, from the driver bones (see above): mirror x for the driver's side, then shift. Driver x: ours
# 0.330, Escort's -0.3335 -> +(-0.0036) after the mirror. The seat on our left is the Escort's left seat (a copy of
# its driver's seat 71.7 cm across, not a mirror), so it takes the offset that puts it where the mirrored driver's
# seat would be.
DRIVER_DY, DRIVER_DZ, DRIVER_DX_MIRRORED = -0.1466, -0.1490 + 0.010, -0.0036
SEAT_DONOR = {"L": {"fab": "seats_fab_HR_R001", "shell": "seats_plastic_HR_R001"},
              "R": {"fab": "seats_fab_HR_R", "shell": "seats_plastic_HR_R"}}
SEAT_SHIFT = {"L": (0.3545 + DRIVER_DX_MIRRORED - 0.3625, DRIVER_DY, DRIVER_DZ),
              "R": (-DRIVER_DX_MIRRORED, DRIVER_DY, DRIVER_DZ)}
# belts: (donor meshes, mirrored?, shift, AC node) - worn/loose for the driver, loose on the passenger seat always
BELTS = [("CINTURE_ON", ("CINTURE_ON_SUB0", "CINTURE_ON_SUB1"), True, "CINTURE_ON"),
         ("CINTURE_OFF", ("cinture_off_SUB0", "cinture_off_SUB1"), True, "CINTURE_OFF"),
         ("RALLY_belt_passenger", ("cinture_off_SUB0", "cinture_off_SUB1"), False, None)]
STRAP_BAND = (0.26, 0.85)  # v span of the blue webbing in MK2_seats.dds (black/stitching outside it, measured)
HARNESS_BAR_Z = 0.763     # the shoulder straps cross the main hoop at z 0.783 (lower face): bar top 1-2 mm under them
# Nik 2026-10-06: "the seatbelts need to be anchored to the floor in the back somewhere, not just draped over the
# bars" - the shoulder straps now run over the harness bar (as a guide) and down to eye bolts on the rear floor strip
# in front of the bulkhead (y 1.165): webbing ends at a snap hook ANCHOR_HOOK above the floor; a 3-bar adjuster sits
# ADJUSTER_AT down each tail. (Before: wrapped round the bar and tucked under it - wrap_on_bar.)
ANCHOR_Y, ANCHOR_FLOOR_Z = 1.10, 0.108
ANCHOR_HOOK = 0.050
ADJUSTER_AT = 0.13
HARDWARE = "steel_727473FF"      # stock solid mid-grey steel: eye bolts, hooks, adjusters
ANCHOR_PLATE = (0.070, 0.070, 0.003)
# the worn set was shaped round the Escort's driver, who sits more upright: on ours it went up to 5.4 cm into the
# chest and shoulders (Nick, in game). It is fitted to our driver's actual body - the driver_70 suit posed by our
# car's own skeleton files (driver_pose.py) - and kept BELT_CLEAR off it.
DRIVER_CAR = "talbot_sunbeam_lotus_lhd_stock"   # source of our car's animations/driver_base_pos.knh + steer.ksanim
BELT_CLEAR = 0.006
REPAINT = ("floor_a_SUB6", "floor_a_SUB7", "floor_a_SUB8",                  # rear arch/side trims, armrests
           "trunkbay_a_SUB1", "trunkbay_a_SUB6", "trunkbay_a_SUB7")        # boot carpet and trims
PAINT = "painted_metal_smooth"   # the stock car's black painted metal (inner door skins, floor pan)

# rear bulkhead where the seat back stood, and the floor strip in front of it
BULK_Y, BULK_TOP, BULK_X = 1.165, 0.745, 0.668
FLOOR_Z, FLOOR_Y0, FLOOR_X = 0.108, 1.00, 0.62

# cage nodes (left side)
MAIN_Y = 0.72             # stock belt reels/webbing reach y 0.68
# legs 6 mm inside the rear armrests' lower lip (x 0.641); the side trim above/below is at x 0.66-0.69
MAIN = {"foot": (0.616, MAIN_Y, 0.111), "knee": (0.616, MAIN_Y, 0.900), "corner": (0.539, MAIN_Y, 1.140)}
# front legs: up the A-pillar ~10 mm off the windscreen, then down through the dash end to the footwell floor
FRONT = {"foot": (0.598, -0.665, 0.111), "knee": (0.595, -0.540, 0.800), "corner": (0.495, -0.150, 1.122)}
STAY_FOOT = (0.560, 1.100)                # z found on the wheel-arch top
BEND = {"main_knee": 0.15, "main_corner": 0.11, "front_knee": 0.12, "front_corner": 0.10}


def load(name):
    spec = importlib.util.spec_from_file_location(name, rf"{TOOLS}\{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def stock_meshes():
    for o in bpy.data.collections["STOCK_MODEL"].all_objects:
        if o.type == "MESH" and o.get("kn5_class") == 2:
            yield o


def kn5(name):
    return next(o for o in bpy.data.objects if o.get("kn5_name") == name)


def stock_material(name):
    return next(m for m in bpy.data.materials if m.get("kn5_def") and json.loads(m["kn5_def"])["name"] == name
                and not m.name.startswith("MK2"))


def mirror(p):
    return Vector((-p[0], p[1], p[2]))


def make_obj(name, bm, materials, parent):
    """Like build_rally_parts.replace() but keeps the faces' winding as built (open sheets: recalculating
    normals on them can point them the wrong way)."""
    old = bpy.data.objects.get(name)
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old and me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["STOCK_MODEL"].objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


# ---------------------------------------------------------------- rear interior

def strip_rear():
    """Leave out STRIP, repaint REPAINT (original material kept on the object as orig_mat, so it is reversible)."""
    paint = stock_material(PAINT)
    done = {"stripped": [], "repainted": []}
    for o in stock_meshes():
        kn = o.get("kn5_name")
        if kn in STRIP:
            o["no_export"] = True
            if o.name in bpy.context.view_layer.objects:
                o.hide_set(True)
            done["stripped"].append(kn)
        elif kn in REPAINT:
            if "orig_mat" not in o:
                o["orig_mat"] = o.data.materials[0].name
            o.data.materials[0] = paint
            done["repainted"].append(kn)
    return done, paint


def bulkhead_mesh():
    """Cabin-facing bulkhead at the old seat back (with a 20 mm top return) and a floor strip up to it."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    y, t, x = BULK_Y, BULK_TOP, BULK_X

    def quad(ps, want):
        f = bm.faces.new([bm.verts.new(p) for p in ps])
        f.normal_update()
        if f.normal.dot(Vector(want)) < 0:
            f.normal_flip()
        for lp in f.loops:
            c = lp.vert.co
            lp[uv].uv = (c.x * 8.0, (c.y + c.z) * 8.0)

    quad([(-x, y, FLOOR_Z), (x, y, FLOOR_Z), (x, y, t), (-x, y, t)], (0, -1, 0))           # faces the cabin
    quad([(-x, y, t), (x, y, t), (x, y + 0.020, t), (-x, y + 0.020, t)], (0, 0, 1))        # top return
    quad([(-FLOOR_X, FLOOR_Y0, FLOOR_Z), (-FLOOR_X, y, FLOOR_Z), (FLOOR_X, y, FLOOR_Z),
          (FLOOR_X, FLOOR_Y0, FLOOR_Z)], (0, 0, 1))                                          # floor strip
    return bm


# ---------------------------------------------------------------- tubes

def fillet_path(nodes, radii):
    """Polyline through nodes with circular bends of radius radii[i] at each interior node -> dense points."""
    pts = [Vector(nodes[0])]
    for i in range(1, len(nodes) - 1):
        p0, p1, p2 = Vector(nodes[i - 1]), Vector(nodes[i]), Vector(nodes[i + 1])
        d0, d1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        theta = d0.angle(d1)
        r = radii[i]
        if theta < 1e-3 or r <= 0:
            pts.append(p1); continue
        a = p1 - d0 * (r * math.tan(theta / 2))
        axis = d0.cross(d1).normalized()
        centre = a + axis.cross(d0) * r
        n = max(2, math.ceil(math.degrees(theta) / 7.5))
        pts += [centre + Quaternion(axis, theta * k / n) @ (a - centre) for k in range(n + 1)]
    pts.append(Vector(nodes[-1]))
    out = [pts[0]]                                  # densify straight runs so clearance checks see them
    for a, b in zip(pts, pts[1:]):
        n = max(1, int((b - a).length / 0.04))
        out += [a.lerp(b, k / n) for k in range(1, n + 1)]
    return dedupe(out)


def dedupe(pts, eps=1e-5):
    out = [pts[0]]
    for p in pts[1:]:
        if (p - out[-1]).length > eps:
            out.append(p)
    return out


def sweep_tube(bm, uv, pts, r=TUBE_R, segs=SEGMENTS):
    """Round tube along pts (parallel-transported rings), capped both ends."""
    tans = [(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(len(pts))]
    ref = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = tans[0].cross(ref).normalized()
    rings, s = [], 0.0
    for i, (p, t) in enumerate(zip(pts, tans)):
        if i:
            s += (p - pts[i - 1]).length
            nrm = (tans[i - 1].rotation_difference(t) @ nrm).normalized()
        b = t.cross(nrm).normalized()
        ring = [bm.verts.new(p + (nrm * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r)
                for k in range(segs)]
        rings.append((ring, s))
    for (ra, sa), (rb, sb) in zip(rings, rings[1:]):
        for k in range(segs):
            k1 = (k + 1) % segs
            f = bm.faces.new((ra[k], ra[k1], rb[k1], rb[k]))
            for lp, (u, v) in zip(f.loops, ((sa, k), (sa, k + 1), (sb, k + 1), (sb, k))):
                lp[uv].uv = (u * 4.0, v / segs)
    for ring, _ in (rings[0], rings[-1]):
        f = bm.faces.new(ring)
        for lp in f.loops:
            lp[uv].uv = (0.0, 0.0)


def plate(bm, uv, centre, up, size=PLATE):
    """Foot plate: a thin box square to `up`, bottom face at centre."""
    up = Vector(up).normalized()
    ax = Vector((0, 1, 0)).cross(up).normalized()
    ay = up.cross(ax).normalized()
    c = Vector(centre)
    hx, hy, th = size[0] / 2, size[1] / 2, size[2]
    v = [bm.verts.new(c + ax * sx * hx + ay * sy * hy + up * sz * th)
         for sz in (0, 1) for sy in (-1, 1) for sx in (-1, 1)]
    for idx in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        f = bm.faces.new([v[i] for i in idx])
        for lp in f.loops:
            lp[uv].uv = (0.0, 0.0)


def nearest_on(path, p):
    """Nearest point to p on a dense polyline."""
    p = Vector(p)
    best, bd = None, 1e9
    for a, b in zip(path, path[1:]):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
        q = a + ab * t
        if (q - p).length < bd:
            best, bd = q, (q - p).length
    return best


def cabin_bvh():
    """The stock car as it will be exported (stripped parts and our own parts left out)."""
    verts, polys, owner = [], [], []
    for o in stock_meshes():
        kn = o.get("kn5_name") or o.name
        if (o.get("no_export") or kn in STRIP or o.name.startswith("RALLY_") or o.get("rally_graft")
                or o.get("rally_lamp") or o.get("rally_seat") or o.get("rally_belt")):
            continue
        mw = o.matrix_world
        base = len(verts)
        verts += [tuple(mw @ v.co) for v in o.data.vertices]
        for p in o.data.polygons:
            polys.append(tuple(base + i for i in p.vertices)); owner.append(kn)
    return BVHTree.FromPolygons(verts, polys), owner


def cage_members(bvh):
    """{member: dense centreline} and foot plates [(centre, up)]."""
    L = {k: Vector(v) for k, v in MAIN.items()}
    F = {k: Vector(v) for k, v in FRONT.items()}
    main_nodes = [L["foot"], L["knee"], L["corner"], mirror(L["corner"]), mirror(L["knee"]), mirror(L["foot"])]
    main_r = [0, BEND["main_knee"], BEND["main_corner"], BEND["main_corner"], BEND["main_knee"], 0]
    front_nodes = [F["foot"], F["knee"], F["corner"], mirror(F["corner"]), mirror(F["knee"]), mirror(F["foot"])]
    front_r = [0, BEND["front_knee"], BEND["front_corner"], BEND["front_corner"], BEND["front_knee"], 0]
    m = {"main_hoop": fillet_path(main_nodes, main_r), "front_hoop": fillet_path(front_nodes, front_r),
         "harness_bar": fillet_path([(-L["foot"].x, MAIN_Y, HARNESS_BAR_Z), (L["foot"].x, MAIN_Y, HARNESS_BAR_Z)],
                                    [0, 0])}
    up = Vector((0, 0, 1))
    feet = [(L["foot"], up), (mirror(L["foot"]), up), (F["foot"], up), (mirror(F["foot"]), up)]
    for side, sgn in (("L", 1), ("R", -1)):
        mc = nearest_on(m["main_hoop"], (sgn * L["corner"].x, L["corner"].y, L["corner"].z))
        fc = nearest_on(m["front_hoop"], (sgn * F["corner"].x, F["corner"].y, F["corner"].z))
        m[f"roof_{side}"] = fillet_path([fc, mc], [0, 0])
        hit = bvh.ray_cast(Vector((sgn * STAY_FOOT[0], STAY_FOOT[1], 0.95)), Vector((0, 0, -1)), 1.0)
        foot, n = hit[0], hit[1].normalized()
        feet.append((foot, n))
        top = foot + n * PLATE[2]
        m[f"stay_{side}"] = fillet_path([mc, top], [0, 0])
        if side == "R":
            m["diagonal"] = fillet_path([top, nearest_on(m["main_hoop"], L["corner"])], [0, 0])
    return m, feet


def check(bvh=None, owner=None):
    """Worst clearance of each member from the car: (tube surface to nearest face in metres - negative means it
    goes through something, point, what)."""
    if bvh is None:
        bvh, owner = cabin_bvh()
    members, _ = cage_members(bvh)
    rep = {}
    for name, path in members.items():
        worst = (9.0, None, None)
        for p in path[2:-2]:                       # ends sit on the floor / inside another tube by design
            hit = bvh.find_nearest(p)
            if hit[0] is not None and hit[3] - TUBE_R < worst[0]:
                worst = (round(hit[3] - TUBE_R, 4), tuple(round(c, 3) for c in p), owner[hit[2]])
        rep[name] = worst
    return rep


def finish(bm):
    """Closed parts (tubes, boxes): outward normals, smooth shading with crisp edges over 70 degrees."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(70):
            e.smooth = False
    return bm


# ---------------------------------------------------------------- seats

def stock_node(name):
    return next(o for o in bpy.data.collections["STOCK_MODEL"].all_objects if o.get("kn5_name") == name)


def fit_buckets():
    """Copies of the donor buckets where they sit round our driver (SEAT_SHIFT). At that height their side flanges
    rest on the floor, so there are no risers (the first version, fitted to the stock seat 8 cm higher, had rails)."""
    for o in [o for o in bpy.data.objects if o.get("rally_seat")]:
        bpy.data.objects.remove(o)
    donor = {o.get("kn5_name"): o for o in bpy.data.collections["DONOR_MK2"].all_objects if o.type == "MESH"}
    univers = stock_node("UNIVERS")
    made, seats = [], {}
    for side, parts in SEAT_DONOR.items():
        M = Matrix.Translation(SEAT_SHIFT[side])
        seats[side] = []
        for k, (part, src_name) in enumerate(parts.items()):
            src = donor[src_name]
            ob = src.copy(); ob.data = src.data.copy()
            bpy.data.collections["STOCK_MODEL"].objects.link(ob)
            ob.name = f"RALLY_seat_{side}_{part}"
            ob.parent = univers
            ob.matrix_world = M @ src.matrix_world
            ob["kn5_name"] = ob.name
            ob["kn5_order"] = 3 * 10 ** 6 + 10 + len(made)
            ob["kn5_pristine"] = False
            ob["rally_seat"] = side
            if "no_export" in ob:
                del ob["no_export"]
            ob.hide_set(False)
            made.append(ob.name); seats[side].append(ob)
    bpy.context.view_layer.update()
    return made


def wrap_on_bar(bm, r_min=TUBE_R + 0.002):
    """Shoulder straps running back past the main hoop: cut into 1 cm steps, bent over and round the harness bar
    (each vertex keeps its height above the bar's axis as its radius, so the strap keeps its thickness) and
    trimmed 3 cm after the half turn - the tail tucked under the bar."""
    y0, z0 = MAIN_Y, HARNESS_BAR_Z
    tail = y0 + math.pi * (TUBE_R + 0.003) + 0.03
    for k in range(int((tail - y0) / 0.01) + 1):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y0 + 0.01 * k, 0),
                               plane_no=(0, 1, 0))
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, tail, 0),
                           plane_no=(0, 1, 0), clear_outer=True)
    for v in bm.verts:
        if v.co.y > y0 and v.co.z > z0:
            d = v.co.y - y0
            r = max(v.co.z - z0, r_min)
            phi = d / r
            if phi <= math.pi:
                v.co.y, v.co.z = y0 + r * math.sin(phi), z0 + r * math.cos(phi)
            else:
                v.co.y, v.co.z = y0 - (d - math.pi * r), z0 - r


def bar_tangent(r=TUBE_R + 0.003):
    """Angle past the bar's top where a strap over it leaves on the tangent to its floor anchor, the leave point and
    the run (unit direction, length) from there to the strap end."""
    y0, z0 = MAIN_Y, HARNESS_BAR_Z
    A = Vector((ANCHOR_Y, ANCHOR_FLOOR_Z + ANCHOR_HOOK))
    d = A - Vector((y0, z0))
    theta = math.atan2(d.x, d.y)                     # angle of the anchor in (sin, cos) = (y, z) terms
    phi = theta - math.acos(r / d.length)
    T = Vector((y0 + r * math.sin(phi), z0 + r * math.cos(phi)))
    run = A - T
    return phi, T, run.normalized(), run.length


def band_v(v, ref):
    """v folded back and forth inside the webbing band of ref's texture tile - continuous, so no seam."""
    lo = math.floor(ref) + STRAP_BAND[0]
    span = STRAP_BAND[1] - STRAP_BAND[0]
    x = (v - lo) % (2 * span)
    return lo + (x if x <= span else 2 * span - x)


def over_bar_to_floor(bm, steps=12):
    """Shoulder straps running back past the main hoop: bent over the harness bar (each vertex keeps its height
    above the bar's axis as its radius, so the strap keeps its thickness) to the tangent towards the floor anchor,
    then the strap's own cut section is extruded down that line to the snap hook - webbing, thickness and texture
    carry on. Returns [(x, top of the hook)] for the hardware, one per strap end."""
    y0, z0 = MAIN_Y, HARNESS_BAR_Z
    r_mid = TUBE_R + 0.003
    phi_t, T, tdir, L = bar_tangent(r_mid)
    y_cut = y0 + r_mid * phi_t
    for k in range(int((y_cut - y0) / 0.008) + 1):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y0 + 0.008 * k, 0),
                               plane_no=(0, 1, 0))
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y_cut, 0),
                           plane_no=(0, 1, 0), clear_outer=True)
    uvl = bm.loops.layers.uv.active
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    # v along the strap per metre, per strap island (fitted on the flat strap just in front of the cut)
    cut = {v for v in bm.verts if abs(v.co.y - y_cut) < 1e-6 and v.co.z > z0}
    rate, island_of = {}, {}
    seen = set()
    for v0 in cut:
        if v0 in seen:
            continue
        comp, st = [], [v0]
        seen.add(v0)
        while st:
            u = st.pop(); comp.append(u)
            for e in u.link_edges:
                w = e.other_vert(u)
                if w not in seen:
                    seen.add(w); st.append(w)
        ys, vs = [], []
        for u in comp:
            if u.co.y > y_cut - 0.12:
                for lp in u.link_loops:
                    ys.append(u.co.y); vs.append(lp[uvl].uv.y)
        b = 0.0
        if len(ys) > 3:
            my, mv = sum(ys) / len(ys), sum(vs) / len(vs)
            den = sum((y - my) ** 2 for y in ys)
            b = sum((y - my) * (v - mv) for y, v in zip(ys, vs)) / den if den > 1e-12 else 0.0
        for u in comp:
            island_of[u] = id(comp)
        rate[id(comp)] = b
    cut_uv = {v: tuple(v.link_loops[0][uvl].uv) for v in cut if v.link_loops}
    # bend everything behind the hoop over the bar
    for v in bm.verts:
        if v.co.y > y0 and v.co.z > z0:
            d = v.co.y - y0
            r = max(v.co.z - z0, TUBE_R + 0.002)
            phi = d / r
            v.co.y, v.co.z = y0 + r * math.sin(phi), z0 + r * math.cos(phi)
    # the run to the floor: extrude the cut boundary in `steps` straight segments
    edges = [e for e in bm.edges if e.verts[0] in cut and e.verts[1] in cut and len(e.link_faces) == 1]
    t3 = Vector((0.0, tdir.x, tdir.y))
    seg = L / steps
    origin = {v: v for v in cut}                    # every tail vertex -> the cut vertex it was extruded from
    step = {v: 0 for v in cut}
    for k in range(1, steps + 1):
        before = {tuple(round(c, 7) for c in v.co): v for v in origin if step[v] == k - 1}
        res = bmesh.ops.extrude_edge_only(bm, edges=edges)
        new_verts = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
        new_faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
        for nv in new_verts:                         # extruded copies start where their source is
            src = before[tuple(round(c, 7) for c in nv.co)]
            origin[nv], step[nv] = origin[src], k
            nv.co = nv.co + t3 * seg
        for f in new_faces:
            f.smooth = True
            for lp in f.loops:
                base = origin[lp.vert]
                u0, v0 = cut_uv.get(base, (0.0, 0.0))
                v = v0 + rate.get(island_of.get(base), 0.0) * seg * step[lp.vert]
                if STRAP_BAND[0] <= v0 % 1.0 <= STRAP_BAND[1]:      # keep the tail on the webbing, not the black
                    v = band_v(v, v0)
                lp[uvl].uv = (u0, v)
        edges = [g for g in res["geom"] if isinstance(g, bmesh.types.BMEdge)
                 and all(step.get(v) == k for v in g.verts)]
    return sorted({round(v.co.x, 3) for v in cut})


def _straps(xs, gap=0.010):
    """Strap edge x values (each strap has an inner and outer edge) -> [(x_centre, width)]."""
    xs = sorted(xs)
    out, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] > gap:
            out.append(cur); cur = [x]
        else:
            cur.append(x)
    out.append(cur)
    return [((c[0] + c[-1]) / 2, c[-1] - c[0]) for c in out]


def anchor_hardware(ends):
    """Per strap: 3-bar adjuster on the tail, snap hook at its end, eye bolt + reinforcement plate on the floor.
    Material slot 0 = steel, 1 = black plate."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    phi_t, T, tdir, L = bar_tangent()
    t3 = Vector((0.0, tdir.x, tdir.y))
    n3 = Vector((0.0, -tdir.y, tdir.x))
    X = Vector((1, 0, 0))

    def faces(vs, quads, mi):
        for idx in quads:
            f = bm.faces.new([vs[i] for i in idx]); f.material_index = mi
            for lp in f.loops:
                lp[uv].uv = (0.5, 0.5)

    def box(c, ax, ay, az, mi=0):
        c = Vector(c)
        v = [bm.verts.new(c + ax * sx + ay * sy + az * sz) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
        faces(v, ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)), mi)

    def ring(c, axis, R, r, segs=16, rsegs=6, mi=0):
        c, axis = Vector(c), Vector(axis).normalized()
        a = axis.orthogonal().normalized(); b = axis.cross(a)
        rows = []
        for i in range(segs):
            t = 2 * math.pi * i / segs
            radial = a * math.cos(t) + b * math.sin(t)
            cc = c + radial * R
            rows.append([bm.verts.new(cc + (radial * math.cos(2 * math.pi * j / rsegs) + axis * math.sin(2 * math.pi * j / rsegs)) * r)
                         for j in range(rsegs)])
        flat = [v for row in rows for v in row]
        faces(flat, [(i * rsegs + j, ((i + 1) % segs) * rsegs + j, ((i + 1) % segs) * rsegs + (j + 1) % rsegs,
                      i * rsegs + (j + 1) % rsegs) for i in range(segs) for j in range(rsegs)], mi)

    def cyl(p0, p1, r, segs=12, mi=0):
        p0, p1 = Vector(p0), Vector(p1)
        ax = (p1 - p0).normalized(); a = ax.orthogonal().normalized(); b = ax.cross(a)
        v = [bm.verts.new(p + (a * math.cos(2 * math.pi * i / segs) + b * math.sin(2 * math.pi * i / segs)) * r)
             for p in (p0, p1) for i in range(segs)]
        faces(v, [(i, (i + 1) % segs, segs + (i + 1) % segs, segs + i) for i in range(segs)]
              + [tuple(range(segs - 1, -1, -1)), tuple(range(segs, 2 * segs))], mi)

    for xc, w in _straps(ends):
        w = max(w, 0.045)
        top = Vector((xc, T.x, T.y))
        end = top + t3 * L                               # where the webbing stops (ANCHOR_HOOK above the floor)
        box(top + t3 * ADJUSTER_AT, X * (w / 2 + 0.004), t3 * 0.016, n3 * 0.0045)      # 3-bar adjuster
        base = Vector((xc, ANCHOR_Y, ANCHOR_FLOOR_Z + 0.003))
        eye_c = base + Vector((0, 0, 0.010 + 0.016))
        h0, h1 = end - t3 * 0.008, end + t3 * 0.022                                      # snap hook body
        box((h0 + h1) / 2, X * (w / 2 + 0.003), t3 * ((h1 - h0).length / 2), n3 * 0.004)
        cyl(h1, eye_c + Vector((0, 0, 0.013)), 0.0045)                                  # hook nose into the eye
        cyl(base, base + Vector((0, 0, 0.010)), 0.012, segs=6)                          # eye bolt hex + ring
        ring(eye_c, X, 0.013, 0.0035)
        box(base - Vector((0, 0, 0.0015)), X * (ANCHOR_PLATE[0] / 2), Vector((0, ANCHOR_PLATE[1] / 2, 0)),
            Vector((0, 0, ANCHOR_PLATE[2] / 2)), mi=1)                                  # reinforcement plate
        for sx in (-1, 1):
            for sy in (-1, 1):
                cyl(base + Vector((sx * 0.026, sy * 0.026, 0)), base + Vector((sx * 0.026, sy * 0.026, 0.003)), 0.005, segs=6)
    return finish(bm)


def driver_bvh():
    V, T = load("driver_pose").posed_driver(DRIVER_CAR)
    return BVHTree.FromPolygons(V.tolist(), T.tolist())


def _signed(dbvh, p):
    """Distance from the driver's surface (negative inside) and the outward normal there."""
    h = dbvh.find_nearest(p)
    if h[0] is None:
        return 9.0, Vector((0, 0, 1))
    return (h[3] if (p - h[0]).dot(h[1]) >= 0 else -h[3]), h[1]


def clear_of_driver(ob, dbvh, rigid):
    """Move a worn-belt mesh out of the driver's body to BELT_CLEAR off it. rigid: buckles and adjusters - each
    loose part is moved whole along the body normal; webbing: long edges near the body are subdivided, then
    each vertex is pushed out and the displacement smoothed along the strap (repeat until clear), fading out to
    nothing 10-15 cm from the body so the anchors and the harness-bar wraps stay put. Returns the deepest point
    left inside (m)."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    mw = ob.matrix_world
    bm.transform(mw)
    if rigid:
        seen = set()
        for v0 in bm.verts:
            if v0 in seen:
                continue
            island, stack = [], [v0]
            seen.add(v0)
            while stack:
                v = stack.pop(); island.append(v)
                for e in v.link_edges:
                    w = e.other_vert(v)
                    if w not in seen:
                        seen.add(w); stack.append(w)
            for _ in range(30):
                worst, n_sum = 0.0, Vector()
                for v in island:
                    d, n = _signed(dbvh, v.co)
                    if -0.12 < d < BELT_CLEAR:
                        worst = max(worst, BELT_CLEAR - d); n_sum += n
                if worst < 1e-4:
                    break
                step = n_sum.normalized() * worst
                for v in island:
                    v.co += step
    else:
        for _ in range(3):
            long = [e for e in bm.edges if e.calc_length() > 0.02
                    and min(abs(_signed(dbvh, v.co)[0]) for v in e.verts) < 0.10]
            if not long:
                break
            bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
        verts = list(bm.verts)
        ix = {v: i for i, v in enumerate(verts)}
        nbrs = [[ix[e.other_vert(v)] for e in v.link_edges] for v in verts]
        base = [v.co.copy() for v in verts]
        d0 = [abs(_signed(dbvh, p)[0]) for p in base]
        fade = [max(0.0, min(1.0, (0.15 - d) / 0.05)) for d in d0]     # 1 near the body, 0 beyond 15 cm
        D = [Vector() for _ in verts]
        for _ in range(60):
            pushed = False
            for i in range(len(verts)):
                d, n = _signed(dbvh, base[i] + D[i])
                if -0.12 < d < BELT_CLEAR and fade[i] > 0:
                    D[i] += n * (BELT_CLEAR - d); pushed = True
            if not pushed:
                break
            for _ in range(2):
                D = [(D[i] * 0.5 + sum((D[j] for j in nbrs[i]), Vector()) * (0.5 / len(nbrs[i]))) * fade[i]
                     if nbrs[i] else D[i] for i in range(len(verts))]
        for i in range(len(verts)):                     # last pass unsmoothed: nothing left inside
            d, n = _signed(dbvh, base[i] + D[i])
            if -0.12 < d < BELT_CLEAR and fade[i] > 0:
                D[i] += n * (BELT_CLEAR - d)
            verts[i].co = base[i] + D[i]
    deepest = max([0.0] + [-_signed(dbvh, v.co)[0] for v in bm.verts if -0.12 < _signed(dbvh, v.co)[0] < 0])
    bm.transform(mw.inverted())
    bm.to_mesh(ob.data); bm.free()
    return deepest


def fit_harness():
    """The donor's harness belts (see the module docstring): the driver's worn and loose sets under CINTURE_ON /
    CINTURE_OFF dummies (AC shows one or the other with the driver), a loose set on the passenger seat."""
    for o in [o for o in bpy.data.objects if o.get("rally_belt")]:
        me = o.data if o.type == "MESH" else None
        bpy.data.objects.remove(o)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    donor = {o.get("kn5_name"): o for o in bpy.data.collections["DONOR_MK2"].all_objects if o.type == "MESH"}
    univers = stock_node("UNIVERS")
    col = bpy.data.collections["STOCK_MODEL"]
    made = []

    def attach(ob, parent):
        col.objects.link(ob)
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
        ob["rally_belt"] = True
        ob["kn5_order"] = 3 * 10 ** 6 + 40 + len(made)
        made.append(ob.name)

    for name, parts, mirrored, node in BELTS:
        if mirrored:
            M = Matrix.Translation((DRIVER_DX_MIRRORED, DRIVER_DY, DRIVER_DZ)) @ Matrix.Scale(-1, 4, (1, 0, 0))
        else:
            M = Matrix.Translation(SEAT_SHIFT["R"])
        parent = univers
        if node:
            parent = bpy.data.objects.new(f"harness_{node}", None)
            parent["kn5_name"] = node
            attach(parent, univers)
        for k, src_name in enumerate(parts):
            src = donor[src_name]
            me = src.data.copy()
            bm = bmesh.new(); bm.from_mesh(me)
            bm.transform(M @ src.matrix_world)          # into car space (the mirror is baked in, not left on the node)
            if mirrored:
                bmesh.ops.reverse_faces(bm, faces=bm.faces)
            ends = over_bar_to_floor(bm) if k == 0 else []      # SUB0 = webbing, SUB1 = buckle hardware
            bm.to_mesh(me); bm.free()
            for a in ("custom_normal", "kn5_nrm", "kn5_tan"):   # the donor's stored normals don't survive the mirror
                if a in me.attributes:
                    me.attributes.remove(me.attributes[a])
            kn = f"{node}_SUB{k}" if node else f"RALLY_belt_passenger_{k}"
            ob = bpy.data.objects.new(f"harness_{kn}", me)   # not "RALLY_...": the distance LODs leave belts out
            ob["kn5_class"] = 2
            ob["kn5_name"] = kn
            ob["kn5_pristine"] = False
            attach(ob, parent)
            if ends:
                hw = anchor_hardware(ends)
                ho = make_obj(f"harness_anchors_{node or 'passenger'}", hw, [bpy.data.materials[HARDWARE],
                                                                              cage_material()], parent)
                ho["kn5_name"] = f"BELT_anchors_{node or 'passenger'}"
                ho["rally_belt"] = True
                ho["kn5_order"] = 3 * 10 ** 6 + 40 + len(made)
                made.append(ho.name)
    bpy.context.view_layer.update()

    # the worn set onto our driver's body (webbing first, then the buckle hardware - SUB1 - as rigid parts)
    dbvh = driver_bvh()
    left_inside = {}
    for ob in sorted((o for o in bpy.data.objects if o.get("rally_belt") and o.type == "MESH"
                      and o.get("kn5_name", "").startswith("CINTURE_ON")), key=lambda o: o.get("kn5_name")):
        left_inside[ob.get("kn5_name")] = round(clear_of_driver(ob, dbvh, rigid=ob["kn5_name"].endswith("SUB1")), 4)
    fit_harness.left_inside = left_inside
    return made


def cage_material():
    return load("build_rally_parts").spot_material(
        "RALLY_cage", "plastic_textured_002",
        {"texture": CAGE_TEX, "props": {"ksAmbient": 0.45, "ksDiffuse": 0.45, "ksSpecular": 0.35,
                                        "ksSpecularEXP": 30.0}})


def cage_bmesh(bvh, segs=SEGMENTS):
    """The whole cage (tubes + foot plates) as one finished bmesh; fewer segments for the distance LODs."""
    members, feet = cage_members(bvh)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for path in members.values():
        sweep_tube(bm, uv, path, segs=segs)
    for c, up in feet:
        plate(bm, uv, c, up)
    return finish(bm)


def build():
    """Strip the interior, add the bulkhead, the bucket seats and the cage. Returns names made + the clearance
    report."""
    bpy.context.view_layer.update()
    done, paint = strip_rear()
    bulk = make_obj("RALLY_rear_bulkhead", bulkhead_mesh(), [paint], stock_node("UNIVERS"))
    bvh, owner = cabin_bvh()
    seats = fit_buckets()
    belts = fit_harness()
    cage = make_obj("RALLY_cage", cage_bmesh(bvh), [cage_material()], stock_node("UNIVERS"))
    return {"made": [bulk.name, cage.name] + seats + belts, **done, "clearance": check(bvh, owner)}
