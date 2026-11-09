"""Phase 1 placeholder scene for the Vauxhall Nova GTE 1989 (runs inside Blender).

Layout (same as the Sunbeam pipeline): car faces -Y, Z up, +X = car's left, origin on the ground midway
between the axles. All numbers trace to docs/SPEC_SHEET.md.
"""
import math

import bmesh
import bpy

# --- numbers (tag = source in SPEC_SHEET.md) ---
WHEELBASE = 2.343          # FIA
OVERHANG_F, OVERHANG_R = 0.670, 0.609   # FIA (length 3.622)
WIDTH = 1.535              # FIA, overall at the front wing
HEIGHT = 1.365             # BROCHURE
TRACK_F, TRACK_R = 1.320, 1.307   # SOURCED
TYRE_SECTION, TYRE_ASPECT, RIM_IN = 0.175, 0.65, 14   # 175/65 R14 (brochure, Haynes)
RIM_R = RIM_IN * 0.0254 / 2
TYRE_R = RIM_R + TYRE_SECTION * TYRE_ASPECT           # nominal unloaded radius (ESTIMATE of AC's static radius)
CLEARANCE = 0.140          # ESTIMATE (auto-data 140 mm, later model) - placeholder until ride height is sourced

O = bpy.data.objects
C = bpy.data.collections


def wipe():
    for o in list(O):
        if o.type in {"MESH", "EMPTY"}:
            me = o.data if o.type == "MESH" else None
            O.remove(o)
            if me and me.users == 0:
                bpy.data.meshes.remove(me)


def coll(name):
    c = C.get(name) or C.new(name)
    if name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def mat(name, rgba, shader=None, preset=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = rgba
    if shader:
        m["ac_shader"] = shader
    if preset:
        m["ac_preset"] = preset
    return m


def add_obj(name, bm, material, collection, parent=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = O.new(name, me)
    ob.data.materials.append(material)
    collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    return ob


def empty(name, loc, collection, kind="PLAIN_AXES", size=0.05):
    e = O.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = loc
    collection.objects.link(e)
    return e


def cylinder_x(radius, width, x_centre=0.0, seg=48):
    """Closed cylinder around the X axis."""
    bm = bmesh.new()
    rings = []
    for x in (x_centre - width / 2, x_centre + width / 2):
        rings.append([bm.verts.new((x, radius * math.cos(2 * math.pi * i / seg), radius * math.sin(2 * math.pi * i / seg)))
                      for i in range(seg)])
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
    for ring, flip in ((rings[0], True), (rings[1], False)):
        bm.faces.new(ring[::-1] if flip else ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def box(x0, x1, y0, y1, z0, z1):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    return bm


def build():
    wipe()
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    scn.unit_settings.scale_length = 1.0
    body_c, wheel_c, help_c = coll("BODY"), coll("WHEELS"), coll("HELPERS")

    paint = mat("paint_gunmetal", (0.12, 0.13, 0.14, 1.0), preset="paint")
    rubber = mat("tyre_rubber", (0.02, 0.02, 0.02, 1.0), shader="ksTyres")
    alloy = mat("rim_alloy", (0.65, 0.65, 0.68, 1.0), preset="trim")
    steel = mat("disc_steel", (0.35, 0.33, 0.30, 1.0), preset="trim")

    y_front, y_rear = -(WHEELBASE / 2 + OVERHANG_F), WHEELBASE / 2 + OVERHANG_R
    # placeholder body: one box at overall width/height/length (replaced in Phase 2 by the real shell)
    add_obj("BODY_shell", box(-WIDTH / 2, WIDTH / 2, y_front, y_rear, CLEARANCE, HEIGHT), paint, body_c)

    for tag, sx, sy in (("LF", 1, -1), ("RF", -1, -1), ("LR", 1, 1), ("RR", -1, 1)):
        front = sy < 0
        track = TRACK_F if front else TRACK_R
        centre = (sx * track / 2, sy * WHEELBASE / 2, TYRE_R)
        w = empty(f"WHEEL_{tag}", centre, help_c, "ARROWS", 0.12)
        empty(f"SUSP_{tag}", centre, help_c, "PLAIN_AXES", 0.08)
        # tyre and rim are built in wheel-local space; outboard = +X on the left, mirrored on the right
        out = sx
        add_obj(f"TIRE_{tag}", cylinder_x(TYRE_R, TYRE_SECTION, 0.0), rubber, wheel_c, parent=w)
        add_obj(f"RIM_{tag}", cylinder_x(RIM_R, 0.127, out * 0.0), alloy, wheel_c, parent=w)   # 5J = 127 mm
        add_obj(f"DISK_{tag}", cylinder_x(0.118 if front else 0.100, 0.020 if front else 0.010, -out * 0.050), steel, wheel_c, parent=w)

    # driver reference points (RHD: driver on the car's right = -X). Placeholders until the cockpit is modelled
    empty("COCKPIT_HR", (-0.36, -0.20, 1.00), help_c, "SPHERE", 0.06)
    empty("COCKPIT_LR", (-0.36, -0.20, 1.00), help_c, "SPHERE", 0.06)
    empty("STEER_HR", (-0.36, -0.62, 0.86), help_c, "SPHERE", 0.06)
    return {"tyre_radius": TYRE_R, "rim_radius": RIM_R, "length": y_rear - y_front}


if __name__ == "__main__":
    print(build())
