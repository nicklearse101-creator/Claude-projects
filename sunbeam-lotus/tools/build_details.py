"""Bolt-on details for the Sunbeam (runs in Blender, after build_body.build()).

Positions from the blueprint front/rear/side views (tools/features_side.json + the
front/rear readings below) and Nick's reference collage (lamp layout, silver
bumpers with black ends, mirrors both sides, mud flaps behind all four wheels).
Symmetric parts are built on the car's left (+X) and mirrored in X.
Names that AC will need later: HEADLIGHT (lights.ini), TAILLIGHT (brake/tail),
LAMP_POD_LENS (spot lamps), MIRROR_L/R.
"""
import importlib.util
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

_spec = importlib.util.spec_from_file_location("build_body", r"D:\Claude\talbot_sunbeam_lotus\tools\build_body.py")
body = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(body)

Y_FRONT, Y_REAR = -1.915, 1.935
HUB, WB = 0.300, 2.413
# (axle Y, opening r, flare blend r, lip X): blueprint openings ~0.345, flare edge ~0.47
ARCHES = [(-WB / 2, 0.345, 0.47, 0.865), (WB / 2, 0.35, 0.475, 0.877)]
# spot lamps (X, Z, diameter) - reference collage layout at blueprint scale
SPOTS = [(0.19, 0.66, 0.175), (0.35, 0.455, 0.145)]
Y_SPOT = -1.975


def mat(name, rgb, preset=None, shader=None):
    return body.material(name, rgb, shader, preset)


def new_obj(name, bm, material_list, mirror=True, collection="DETAILS"):
    col = bpy.data.collections.get(collection)
    if col is None:
        col = bpy.data.collections.new(collection)
        bpy.context.scene.collection.children.link(col)
    old = bpy.data.objects.get(name)
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old and me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(40):
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for m in material_list:
        me.materials.append(m)
    if mirror:
        md = ob.modifiers.new("Mirror", "MIRROR")
        md.use_axis = (True, False, False)
        md.use_mirror_merge = False
    return ob


def add_box(bm, x0, x1, y0, y1, z0, z1, mi=0, bevel=0.0):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    vs = ret["verts"]
    bmesh.ops.scale(bm, verts=vs, vec=(x1 - x0, y1 - y0, z1 - z0))
    bmesh.ops.translate(bm, verts=vs, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    faces = list({f for v in vs for f in v.link_faces})
    if bevel > 0:
        edges = list({e for v in vs for e in v.link_edges})
        res = bmesh.ops.bevel(bm, geom=edges + vs, offset=bevel, segments=2, affect="EDGES", profile=0.5)
        faces += res.get("faces", [])
    for f in set(faces):
        if f.is_valid:
            f.material_index = mi
    return vs


def add_cyl(bm, centre, radius, depth, axis="Y", mi=0, segments=32, mi_front=None):
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=depth)
    vs = ret["verts"]
    rot = {"Y": Matrix.Rotation(math.radians(90), 3, "X"), "X": Matrix.Rotation(math.radians(90), 3, "Y"), "Z": Matrix.Identity(3)}[axis]
    bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, 0), matrix=rot)
    bmesh.ops.translate(bm, verts=vs, vec=centre)
    faces = {f for v in vs for f in v.link_faces}
    for f in faces:
        f.material_index = mi
    if mi_front is not None:            # the cap facing forward (-Y) becomes the lens
        front = min(faces, key=lambda f: f.calc_center_median().y)
        front.material_index = mi_front
    return vs


def sweep(bm, path, profile, mi_of=lambda x: 0):
    """Loft a cross-section profile [(inward offset, z)] along a plan path [(x, y)] (left half)."""
    rings = []
    for i, (x, y) in enumerate(path):
        a = Vector(path[max(i - 1, 0)]); b = Vector(path[min(i + 1, len(path) - 1)])
        d = (b - a).normalized()
        inward = Vector((-d.y, d.x))
        if inward.dot(Vector((-x, -y * 0.0 - (1 if y < 0 else -1) * 0.0))) < 0 and abs(d.x) < 0.5:
            inward = -inward
        rings.append([bm.verts.new((x + inward.x * o, y + inward.y * o, z)) for o, z in profile])
    n = len(profile)
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for j in range(n):
            f = bm.faces.new((r0[j], r0[(j + 1) % n], r1[(j + 1) % n], r1[j]))
            f.material_index = mi_of((path[i][0] + path[i + 1][0]) / 2)
    for cap in (rings[0], rings[-1]):
        f = bm.faces.new(cap)
        f.material_index = mi_of(path[-1][0] if cap is rings[-1] else path[0][0])


def build():
    black, silver = mat("EXT_black", (0.025, 0.025, 0.025), "trim"), mat("EXT_silver", (0.62, 0.63, 0.65), "chrome")
    head_lens, indicator = mat("EXT_head_lens", (0.80, 0.82, 0.86), "lens"), mat("EXT_indicator", (0.95, 0.42, 0.02), "lens")
    tail_red, plate = mat("EXT_tail_red", (0.55, 0.01, 0.01), "lens"), mat("EXT_plate_yellow", (0.95, 0.78, 0.05), "trim")
    lamp_lens, exhaust = mat("EXT_lamp_lens", (0.93, 0.92, 0.86), "lens"), mat("EXT_exhaust", (0.16, 0.16, 0.17), "chrome")
    body_white = bpy.data.materials["EXT_body_white"]

    # --- front: grille panel, headlamps + bezels, indicators, badge
    bm = bmesh.new()
    add_box(bm, 0.0, 0.715, Y_FRONT - 0.006, Y_FRONT + 0.010, 0.595, 0.725, 0)
    add_box(bm, 0.458, 0.617, Y_FRONT - 0.009, Y_FRONT - 0.004, 0.605, 0.697, 1)
    add_box(bm, 0.0, 0.03, Y_FRONT - 0.010, Y_FRONT - 0.005, 0.63, 0.66, 1)
    new_obj("DET_front_panel", bm, [black, silver])
    bm = bmesh.new()
    add_box(bm, 0.465, 0.610, Y_FRONT - 0.013, Y_FRONT - 0.006, 0.612, 0.690, 0)
    new_obj("HEADLIGHT", bm, [head_lens])
    bm = bmesh.new()
    add_box(bm, 0.635, 0.705, Y_FRONT - 0.012, Y_FRONT - 0.004, 0.612, 0.695, 0)
    new_obj("INDICATOR_FRONT", bm, [indicator])

    # --- bumpers: silver bar, black end caps, wrapping round the corners
    fpath = [(0.0, -1.938), (0.60, -1.938), (0.70, -1.934), (0.755, -1.915), (0.788, -1.88), (0.800, -1.83), (0.803, -1.75)]
    rpath = [(0.0, 1.958), (0.60, 1.958), (0.70, 1.954), (0.755, 1.937), (0.790, 1.90), (0.805, 1.84), (0.808, 1.66)]
    prof = lambda z0, z1: [(0.0, z0 + 0.008), (0.0, z1 - 0.008), (0.010, z1), (0.034, z1), (0.034, z0), (0.010, z0)]
    for name, path, (z0, z1) in (("DET_bumper_front", fpath, (0.425, 0.515)), ("DET_bumper_rear", rpath, (0.440, 0.535))):
        bm = bmesh.new()
        sweep(bm, path, prof(z0, z1), mi_of=lambda x: 1 if x > 0.70 else 0)
        new_obj(name, bm, [silver, black])

    # --- spot lamps on a bar in front of the grille
    bm = bmesh.new()
    for x, z, d in SPOTS:
        add_cyl(bm, (x, Y_SPOT, z), d / 2, 0.075, "Y", mi=0, mi_front=1)
    add_cyl(bm, (0.0, Y_SPOT + 0.045, 0.545), 0.012, 0.80, "X", mi=0, segments=12)   # lamp bar (spans both sides)
    for x, z, d in SPOTS:                                                            # brackets down to the bar
        add_box(bm, x - 0.012, x + 0.012, Y_SPOT + 0.030, Y_SPOT + 0.050, min(z, 0.545), max(z, 0.545), 0)
    new_obj("LAMP_POD", bm, [black, lamp_lens])

    # --- rear: tail lamps (amber inner segment), yellow plate, exhausts
    bm = bmesh.new()
    add_box(bm, 0.470, 0.765, Y_REAR + 0.002, Y_REAR + 0.010, 0.612, 0.712, 0)
    new_obj("TAILLIGHT", bm, [tail_red])
    bm = bmesh.new()
    add_box(bm, 0.400, 0.468, Y_REAR + 0.002, Y_REAR + 0.010, 0.612, 0.712, 0)
    new_obj("INDICATOR_REAR", bm, [indicator])
    bm = bmesh.new()
    add_box(bm, 0.0, 0.26, Y_REAR + 0.002, Y_REAR + 0.009, 0.600, 0.710, 0)
    new_obj("DET_plate_rear", bm, [plate])
    bm = bmesh.new()
    for x in (0.490, 0.535):
        add_cyl(bm, (x, Y_REAR + 0.02, 0.33), 0.022, 0.12, "Y", 0, segments=16)
    new_obj("DET_exhaust", bm, [exhaust], mirror=False)

    # --- sides: mirrors, handles, mud flaps
    bm = bmesh.new()
    add_box(bm, 0.795, 0.830, -0.645, -0.625, 0.905, 0.925, 0)                   # stalk
    add_box(bm, 0.825, 0.905, -0.665, -0.615, 0.900, 0.975, 0, bevel=0.012)       # housing
    new_obj("MIRROR", bm, [black])
    bm = bmesh.new()
    add_box(bm, 0.800, 0.812, 0.30, 0.43, 0.815, 0.835, 0, bevel=0.004)
    new_obj("DET_door_handle", bm, [silver])
    bm = bmesh.new()
    add_box(bm, 0.62, 0.84, -0.815, -0.805, 0.10, 0.42, 0)
    add_box(bm, 0.62, 0.86, 1.640, 1.650, 0.10, 0.45, 0)
    new_obj("DET_mudflaps", bm, [black])

    # --- arch flares: lip band sitting on the body side, ending cleanly at the sill
    bm = bmesh.new()
    for y_c, r_in, r_out, x_out in ARCHES:
        z_min = 0.24
        a_in = math.asin((HUB - z_min) / r_in)
        a_out = math.asin((HUB - z_min) / r_out)
        rings, steps = [], 40
        for i in range(steps + 1):
            t = i / steps
            ai = math.pi + a_in + (-a_in - math.pi - a_in) * t        # lip: front-bottom -> over the top -> rear-bottom
            ao = math.pi + a_out + (-a_out - math.pi - a_out) * t
            yi, zi = y_c + r_in * math.cos(ai), HUB + r_in * math.sin(ai)
            yo, zo = y_c + r_out * math.cos(ao), HUB + r_out * math.sin(ao)
            ym, zm = y_c + (r_in + 0.35 * (r_out - r_in)) * math.cos(ai), HUB + (r_in + 0.35 * (r_out - r_in)) * math.sin(ai)
            wb = lambda y: body.interp(body.HALFW, y) - 0.004            # sit just inside the body surface
            prof = [(wb(yi), yi, zi), (x_out - 0.008, yi, zi - 0.004 * math.sin(ai)), (x_out, ym, zm),
                    (wb(yo) + 0.004, yo, zo)]
            rings.append([bm.verts.new(p) for p in prof])
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(3):
                bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
            bm.faces.new((r0[3], r0[0], r1[0], r1[3]))
        bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    old = bpy.data.objects.get("BODY_arch_flares")
    fl = new_obj("BODY_arch_flares", bm, [body_white], collection="BODY")
    return sorted(o.name for o in bpy.data.collections["DETAILS"].objects)


if __name__ == "__main__":
    build()
