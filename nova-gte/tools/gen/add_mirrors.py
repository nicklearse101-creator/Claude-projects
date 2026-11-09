"""Door mirrors: body-colour housing, glass on the rear face, black base plate to the window line.

Measured (2026-10-27 (15)):
  - tip x 0.8625: the brochure's 1725 mm width including mirrors (SPEC_SHEET, SOURCED).
  - the housing's side outline: read off anglia_side (cS) on a pixel grid and back-projected through cS's solved
    camera onto x = -0.8625 (cS looks at the car's right side; mirrored here): rear edge y -0.393 from z 0.868 to
    0.980, top running forward to (-0.479, 0.990), front edge sloping down to (-0.532, 0.883). The same camera puts
    the triangulated side repeater within 2 px of where the photo shows it, so it is good here. Changing the assumed
    depth from x 0.86 to 0.72 moves these by <= 15 mm. (BA point MIR, y -0.207, is single-view and projects onto
    the door glass behind the mirror in cS - not used.)
  - body colour: SPEC_SHEET "colour-coded ... door mirror housings", and both red cars.
ESTIMATES (no measurement): housing inboard end x 0.725; corner radius 14 mm; the base plate's shape; glass inset.

Left only, Mirror modifier for the right. Runs after add_glass (needs the shell), before organise.

blender -b in.blend --python tools/gen/add_mirrors.py -- out.blend
"""
import math
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args else None

X_TIP = 1.725 / 2                 # SOURCED, brochure width incl. mirrors
X_IN = 0.725                      # ESTIMATE, housing's inboard end
R_CORNER = 0.014                  # ESTIMATE
# side outline (y, z), anticlockwise seen from the car's left: rear-bottom, rear-top, front-top, front-bottom
OUTLINE = [(-0.394, 0.868), (-0.393, 0.980), (-0.479, 0.990), (-0.532, 0.883)]
CAP = 0.022                       # the outer end rounds over this much x
GLASS_INSET = 0.008


def fillet(poly, r, n=4):
    """Round each corner of a convex polygon with an n-segment arc of radius r."""
    out = []
    m = len(poly)
    for i in range(m):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % m])
        a, b = (p0 - p1).normalized(), (p2 - p1).normalized()
        ang = math.acos(max(-1.0, min(1.0, a.dot(b))))
        d = min(r / math.tan(ang / 2), 0.45 * (p0 - p1).length, 0.45 * (p2 - p1).length)
        s, e = p1 + a * d, p1 + b * d
        # quadratic Bezier with the corner as control point - tangent to both edges
        for k in range(n + 1):
            t = k / n
            q = (1 - t) ** 2 * s + 2 * (1 - t) * t * p1 + t * t * e
            out.append((q.x, q.y))
    return out


PROF = fillet(OUTLINE, R_CORNER)
cy = sum(p[0] for p in PROF) / len(PROF); cz = sum(p[1] for p in PROF) / len(PROF)


def ring(x, scale):
    return [(x, cy + (y - cy) * scale, cz + (z - cz) * scale) for y, z in PROF]


def new_obj(name, bm, mat_name, colour=None, mirror=True):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
        if colour:
            mat.diffuse_color = colour
    me.materials.append(mat)
    if hasattr(me, "shade_smooth"):
        me.shade_smooth()
    for _n in ("set_sharp_from_angle", "set_sharpness_by_angle"):
        _f = getattr(me, _n, None)
        if _f:
            _f(angle=math.radians(40))
            break
    ob = bpy.data.objects.new(name, me)
    (bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection).objects.link(ob)
    if mirror:
        md = ob.modifiers.new("Mirror", "MIRROR"); md.use_axis[0] = True
    return ob


def outward(bm, centre):
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median() - centre) < 0:
            f.normal_flip()


# ---- housing: the outline lofted along x, the outer end rounded over CAP -----------------------------------
stations = [(X_IN, 1.0), (X_TIP - CAP, 1.0)]
for k in range(1, 6):
    a = k / 5 * math.pi / 2
    stations.append((X_TIP - CAP + CAP * math.sin(a), 0.55 + 0.45 * math.cos(a)))
bm = bmesh.new()
rings = [[bm.verts.new(p) for p in ring(x, s)] for x, s in stations]
n = len(PROF)
for r0, r1 in zip(rings[:-1], rings[1:]):
    for i in range(n):
        bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
outward(bm, Vector(((X_IN + X_TIP) / 2, cy, cz)))
new_obj("MIRROR_HOUSING_L", bm, "paint_gunmetal")

# ---- glass: on the rear face (the outline's rear edge, y -0.393), inset ------------------------------------
y_r = max(p[0] for p in OUTLINE[:2]) + 0.0012
z0, z1 = OUTLINE[0][1] + GLASS_INSET, OUTLINE[1][1] - GLASS_INSET
x0, x1 = X_IN + GLASS_INSET, X_TIP - CAP + 0.004
bm = bmesh.new()
v = [bm.verts.new(p) for p in ((x0, y_r, z0), (x1, y_r, z0), (x1, y_r, z1), (x0, y_r, z1))]
f = bm.faces.new(v); bm.normal_update()
if f.normal.y < 0:
    f.normal_flip()
new_obj("MIRROR_GLASS_L", bm, "mirror_glass", (0.55, 0.57, 0.6, 1.0))

# ---- base: black plate from the window line out into the housing's lower front -----------------------------
dg = bpy.context.evaluated_depsgraph_get()
sh = bpy.data.objects["Body_Shell"]
me = sh.evaluated_get(dg).to_mesh(); m = sh.matrix_world
bvh = BVHTree.FromPolygons([tuple(m @ q.co) for q in me.vertices], [tuple(p.vertices) for p in me.polygons])
sh.evaluated_get(dg).to_mesh_clear()


def skin_at(y, z):
    hit = bvh.ray_cast(Vector((1.5, y, z)), Vector((-1, 0, 0)), 2.0)
    return hit[0].x if hit[0] else 0.62


# ESTIMATE: a wedge whose section is the housing's lower-front corner region, ending inside the housing
BASE = [(-0.420, 0.872), (-0.430, 0.935), (-0.545, 0.905), (-0.560, 0.866)]
bm = bmesh.new()
inner = [bm.verts.new((skin_at(y, z) - 0.004, y, z)) for y, z in BASE]
X_BASE_IN = min(q.co.x for q in inner)
outer = [bm.verts.new((X_IN + 0.015, cy + (y - cy) * 0.9, cz + (z - cz) * 0.9)) for y, z in BASE]
for i in range(4):
    bm.faces.new((inner[i], inner[(i + 1) % 4], outer[(i + 1) % 4], outer[i]))
bm.faces.new(inner[::-1]); bm.faces.new(outer)
outward(bm, Vector((0.68, -0.49, 0.90)))
new_obj("MIRROR_BASE_L", bm, "trim_black")

print("mirrors: housing x %.3f..%.4f (tip = brochure 1725/2), y %.3f..%.3f, z %.3f..%.3f; glass on the rear face; "
      "base from the window line (x %.3f) out" % (X_IN, X_TIP, min(p[0] for p in PROF), max(p[0] for p in PROF),
                                                    min(p[1] for p in PROF), max(p[1] for p in PROF),
                                                    X_BASE_IN))
if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
