"""GTE 5J x 14 alloy wheels, 175/65 R14 tyres, front vented discs / rear drums (runs inside Blender).

Built in wheel-local space (axle = X, outboard = +X for the left wheels; right wheels are X-mirrored copies),
parented under the WHEEL_xx empties like Kunos cars: WHEEL_xx -> TIRE_xx (ksTyres), RIM_xx, DISK_xx.

SOURCED: 175/65 R14, 5J x 14 (brochure, Haynes); front disc 236 x 20 mm vented (FIA, Haynes).
ESTIMATE: tyre cross-section shape, rim profile, wheel offset (face 20 mm inside the outer flange).
Face design: traced from the F400 PTF front 3/4 photo rectified onto the wheel plane (tools/photomatch); the mesh
is generated outside Blender by tools/wheel_face.py (shapely + Triangle) into blender/data/wheel_face.json:
three 140 mm arms at 32/152/272 deg each with two slots, three windows between them, truncated-triangle centre
plate raised 9 mm. Here: lip and barrel lathed, face loaded from the JSON.
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix

R_RIM = 0.0254 * 14 / 2                 # 0.1778 bead seat
R_TYRE = R_RIM + 0.175 * 0.65           # 0.2916
HALF_W = 0.175 / 2
SEG = 72



def sharp_by_angle(me, deg):
    """Hard edges above deg (Blender 5.x: set_sharp_from_angle; 4.1-4.x: set_sharpness_by_angle)."""
    for name in ("set_sharp_from_angle", "set_sharpness_by_angle"):
        fn_ = getattr(me, name, None)
        if fn_:
            fn_(angle=math.radians(deg))
            return True
    raise RuntimeError("no sharp-by-angle API in this Blender")

def mat(name, rgba, shader=None, preset=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = rgba
    m.diffuse_color = rgba
    if shader:
        m["ac_shader"] = shader
    if preset:
        m["ac_preset"] = preset
        if "ac_shader" not in m:
            m["ac_shader"] = "ksPerPixelMultiMap"
    return m


def lathe(bm, profile, segments=SEG, closed=False):
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((x, r * c, r * s)) for x, r in profile])
    n = len(profile)
    for i in range(segments):
        r0, r1 = rings[i], rings[(i + 1) % segments]
        for j in range(n - (0 if closed else 1)):
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % n], r0[(j + 1) % n]))
    return rings


def tyre():
    # 175/65 R14: bead on the rim flange (r 188 mm, x 71 mm), sidewall bulge to the 175 section at r ~240 mm,
    # rounded shoulder, flat tread. Inside surface closes the torus behind the rim.
    half = [(0.0660, 0.1890), (0.0692, 0.1962), (0.0760, 0.2065), (0.0828, 0.2225), (0.0858, 0.2400),
            (0.0852, 0.2580), (0.0822, 0.2725), (0.0765, 0.2830), (0.0680, 0.2893), (0.0500, 0.2912),
            (0.0250, 0.2916)]
    prof = half + [(0.0, R_TYRE)] + [(-x, r) for x, r in reversed(half)]
    prof += [(-0.0650, 0.1840), (0.0650, 0.1840)]
    bm = bmesh.new()
    lathe(bm, prof, segments=96, closed=True)
    return bm


FACE_X = 0.0635 - 0.020                 # rim face plane: 20 mm inside the outer flange (5J = 127 mm)
FACE_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wheel_face.json")


def rim():
    """Lip and barrel lathed; the face is the photo-traced mesh from tools/wheel_face.py (data/wheel_face.json)."""
    bm = bmesh.new()
    with open(FACE_JSON) as f:
        d = json.load(f)
    r_face = d["params"]["R_FACE"]
    # outboard lip: tyre seat -> rounded lip top (r 195.5) -> lip inner face -> slope down to the face edge
    lip = [(0.0712, 0.1880), (0.0716, 0.1922), (0.0702, 0.1953), (0.0676, 0.1950), (0.0652, 0.1918),
           (0.0560, 0.1885), (FACE_X + 0.0004, r_face)]
    lathe(bm, lip, segments=180)
    # barrel seen through the windows: drop centre well, inboard flange
    barrel = [(FACE_X - 0.004, 0.1840), (0.030, 0.1760), (0.018, 0.1600), (-0.032, 0.1600), (-0.048, 0.1740),
              (-0.0635, 0.1770), (-0.0680, 0.1920), (-0.0712, 0.1950), (-0.0716, 0.1880)]
    lathe(bm, barrel, segments=96)
    base = len(bm.verts)
    vs = [bm.verts.new(co) for co in d["verts"]]
    for f, m in zip(d["faces"], d["mats"]):
        try:
            face = bm.faces.new([vs[i] for i in f])
            face.material_index = m
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=vs, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def disc(front):
    """Brake seen through the windows: disc + caliper (front) or drum (rear), plus the dark backing plate / dust
    shield behind it (material 1) so the openings read dark like the photos instead of showing the arch behind."""
    bm = bmesh.new()
    if front:     # 236 x 20 vented disc + caliper block
        lathe(bm, [(-0.040, 0.075), (-0.040, 0.118), (-0.060, 0.118), (-0.060, 0.075)], segments=48, closed=True)
        cal = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for v in cal:
            v.co.x = -0.050 + v.co.x * 0.050
            v.co.y = -0.095 + v.co.y * 0.070      # caliper behind the axle (rack is behind too)
            v.co.z = 0.0 + v.co.z * 0.060
    else:         # drum
        lathe(bm, [(-0.020, 0.040), (-0.020, 0.100), (-0.030, 0.112), (-0.075, 0.112), (-0.075, 0.040)], segments=48, closed=True)
    n0 = len(bm.faces)
    # backing plate (rear) / dust shield (front): shallow pressed dish out to just inside the barrel (ESTIMATE)
    lathe(bm, [(-0.080, 0.045), (-0.084, 0.120), (-0.078, 0.140), (-0.070, 0.150)], segments=48)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def place(name, bm, material, parent, mirror, extra=()):
    old = bpy.data.objects.get(name)
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old and me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    if mirror == "rotate":      # same wheel bolted on the other side: turned 180 deg, pattern keeps its handedness
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.pi, 4, "Z"), verts=bm.verts[:])
    elif mirror:                # brake parts are handed (caliper behind the axle on both sides)
        bmesh.ops.transform(bm, matrix=Matrix.Scale(-1, 4, (1, 0, 0)), verts=bm.verts[:])
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    sharp_by_angle(me, 35)                          # hard edges at the chamfers / walls
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    for m in extra:
        ob.data.materials.append(m)
    bpy.data.collections["WHEELS"].objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse.identity()
    ob.location = (0, 0, 0)
    return ob


def build():
    rubber = mat("tyre_rubber", (0.025, 0.025, 0.025, 1), shader="ksTyres")
    alloy = mat("rim_alloy", (0.62, 0.63, 0.65, 1), preset="chrome")
    steel = mat("disc_steel", (0.16, 0.155, 0.15, 1), preset="trim")          # used cast iron (photos: dark)
    backing = mat("brake_backplate", (0.02, 0.02, 0.02, 1), preset="trim")
    plate = mat("rim_alloy_plate", (0.62, 0.63, 0.65, 1), preset="trim")    # cap: same silver as the face (photos)
    stats = {}
    for tag in ("LF", "RF", "LR", "RR"):
        parent = bpy.data.objects[f"WHEEL_{tag}"]
        mirror = tag[0] == "R"
        place(f"TIRE_{tag}", tyre(), rubber, parent, "rotate" if mirror else False)
        r = place(f"RIM_{tag}", rim(), alloy, parent, "rotate" if mirror else False, extra=(plate,))
        place(f"DISK_{tag}", disc(tag[1] == "F"), steel, parent, mirror, extra=(backing,))
        stats[tag] = len(r.data.polygons)
    return stats


if __name__ == "__main__":
    print(build())
