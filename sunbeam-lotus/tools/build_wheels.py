"""15" Minilite-style 8-spoke wheels, tyres and brake discs (runs in Blender).

Built in wheel-local space (axle = X, outboard = +X for the left wheels; right
wheels get an X-mirrored copy), parented under the existing WHEEL_xx empties
exactly like Kunos cars: WHEEL_xx -> TIRE_xx (ksTyres), RIM_xx, DISK_xx.
Tyre: 0.300 m radius (physics TYRE_R) on a 15" bead (0.1905), ~205 section.
"""
import importlib.util
import math

import bmesh
import bpy

_spec = importlib.util.spec_from_file_location("build_body", r"D:\Claude\talbot_sunbeam_lotus\tools\build_body.py")
body = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(body)

R_TYRE, R_BEAD, SEG = 0.300, 0.1905, 64
TYRE_PROFILE = [(-0.088, 0.1935), (-0.098, 0.212), (-0.1025, 0.245), (-0.098, 0.277), (-0.086, 0.294),
                (-0.062, 0.300), (0.062, 0.300), (0.086, 0.294), (0.098, 0.277), (0.1025, 0.245),
                (0.098, 0.212), (0.088, 0.1935)]
X_FACE = 0.058            # rim face plane (outboard of the axle centre)
N_SPOKES, SPOKE_W = 8, 0.024


def lathe(bm, profile, segments=SEG, mi=0, closed=False):
    """Revolve [(x, r)] around the X axis."""
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((x, r * c, r * s)) for x, r in profile])
    n = len(profile)
    for i in range(segments):
        r0, r1 = rings[i], rings[(i + 1) % segments]
        for j in range(n - (0 if closed else 1)):
            f = bm.faces.new((r0[j], r1[j], r1[(j + 1) % n], r0[(j + 1) % n]))
            f.material_index = mi
    return rings


def rim_face(bm, mi):
    """Dished 8-spoke face with a hub; holes are the gaps between constant-width spokes."""
    radii = [0.030, 0.048, 0.062, 0.080, 0.100, 0.120, 0.140, 0.156, 0.170, 0.182]
    depth = lambda r: X_FACE - 0.030 * (1 - (r - 0.030) / 0.152) ** 1.5      # hub sits 30 mm deeper than the lip
    segs = 128
    grid = [[bm.verts.new((depth(r), r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs)))
             for k in range(segs)] for r in radii]

    def in_hole(r, a):
        if not (0.075 < r < 0.160):
            return False
        pitch = 2 * math.pi / N_SPOKES
        d = abs(((a % pitch) - pitch / 2))                   # angle from the middle of the gap
        half_gap = pitch / 2 - math.asin(min(1.0, (SPOKE_W / 2) / r))
        return d < half_gap * (0.82 if r > 0.15 or r < 0.085 else 1.0)

    for i in range(len(radii) - 1):
        for k in range(segs):
            r = (radii[i] + radii[i + 1]) / 2
            a = 2 * math.pi * (k + 0.5) / segs
            if in_hole(r, a):
                continue
            k1 = (k + 1) % segs
            f = bm.faces.new((grid[i][k], grid[i + 1][k], grid[i + 1][k1], grid[i][k1]))
            f.material_index = mi
    # hub cap + 4 nuts
    centre = bm.verts.new((depth(0.03) + 0.004, 0, 0))
    for k in range(segs):
        f = bm.faces.new((grid[0][k], grid[0][(k + 1) % segs], centre))
        f.material_index = mi
    for q in range(4):
        a = math.pi / 4 + q * math.pi / 2
        ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.009, radius2=0.009, depth=0.022)
        bmesh.ops.rotate(bm, verts=ret["verts"], cent=(0, 0, 0),
                         matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "Y"))
        bmesh.ops.translate(bm, verts=ret["verts"], vec=(depth(0.04) + 0.008, 0.040 * math.cos(a), 0.040 * math.sin(a)))
        for f in {f for v in ret["verts"] for f in v.link_faces}:
            f.material_index = mi


def build_tyre():
    bm = bmesh.new()
    lathe(bm, TYRE_PROFILE, mi=0)
    return bm


def build_rim():
    bm = bmesh.new()
    # barrel: outer lip, bead seats, inner lip - open tube seen through the spokes
    barrel = [(X_FACE + 0.004, 0.196), (X_FACE + 0.004, 0.186), (X_FACE - 0.004, 0.182),
              (-0.080, 0.182), (-0.088, 0.190), (-0.090, 0.196)]
    lathe(bm, barrel, mi=0)
    rim_face(bm, mi=0)
    return bm


def build_disc():
    bm = bmesh.new()
    lathe(bm, [(-0.045, 0.060), (-0.045, 0.140), (-0.065, 0.140), (-0.065, 0.060)], segments=48, mi=0, closed=True)
    return bm


def replace(name, bm, mats, parent, mirror_x):
    old = bpy.data.objects.get(name)
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old and me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    if mirror_x:
        for v in bm.verts:
            v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(45):
            e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["BODY"].objects.link(ob)
    ob.parent = parent
    ob.matrix_parent_inverse.identity()
    ob.location = (0, 0, 0)
    return ob


def build():
    tyre = bpy.data.materials["EXT_tyre"]
    rim = body.material("EXT_rim_silver", (0.66, 0.67, 0.69), preset="chrome")
    disc = body.material("EXT_disc", (0.22, 0.22, 0.23), preset="trim")
    made = []
    for tag in ("LF", "RF", "LR", "RR"):
        wheel = bpy.data.objects[f"WHEEL_{tag}"]
        right = tag[0] == "R"
        made.append(replace(f"TIRE_{tag}", build_tyre(), [tyre], wheel, right).name)
        made.append(replace(f"RIM_{tag}", build_rim(), [rim], wheel, right).name)
        made.append(replace(f"DISK_{tag}", build_disc(), [disc], wheel, right).name)
    return made


if __name__ == "__main__":
    build()
