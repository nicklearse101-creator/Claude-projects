"""NICK3 rear wing: end plates, struts and feet rebuilt as clean thick solids (reproducible).
Keeps the main plane and gurney. Coordinates metres; car faces -Y; +Z up.
"""
import math, bpy, bmesh
from mathutils import Vector
import nick3_parts as P

STRUT_X = 0.372
STRUT_T = 0.010
PLATE_T = 0.012
FOOT_T = 0.011


def is_old(c, b):
    xc = (b[0] + b[1]) / 2
    if abs(xc) > 0.69: return True                      # end plates
    if 0.3 < abs(xc) < 0.45 and b[5] < 0.95: return True   # struts + feet
    return False


def round_poly(pts, r, n=5):
    """fillet every corner of a closed 2D polygon (list of (y,z)) with radius r"""
    out = []
    N = len(pts)
    for i in range(N):
        p0 = Vector(pts[i - 1]); p1 = Vector(pts[i]); p2 = Vector(pts[(i + 1) % N])
        a = (p0 - p1).normalized(); b = (p2 - p1).normalized()
        ang = math.acos(max(-1, min(1, a.dot(b))))
        t = min(r / math.tan(ang / 2), (p0 - p1).length * 0.45, (p2 - p1).length * 0.45)
        s = p1 + a * t; e = p1 + b * t
        rad = t * math.tan(ang / 2)
        bis = (a + b).normalized()
        c = p1 + bis * (rad / math.sin(ang / 2))
        v0 = (s - c); v1 = (e - c)
        a0 = math.atan2(v0.y, v0.x); a1 = math.atan2(v1.y, v1.x)
        d = a1 - a0
        while d > math.pi: d -= 2 * math.pi
        while d < -math.pi: d += 2 * math.pi
        for k in range(n + 1):
            th = a0 + d * k / n
            out.append((c.x + rad * math.cos(th), c.y + rad * math.sin(th)))
    return out


def plate_x(y):                     # end plate inner face, toed 3 deg like the stock plate
    return 0.709 + 0.0508 * (y - 1.70)


def make_solids(bevel, segs, rn):
    out = []
    # --- end plates
    outline = [(1.70, 0.86), (1.70, 0.99), (1.735, 1.026), (2.238, 1.062), (2.268, 1.03), (2.268, 0.85), (2.24, 0.818), (2.152, 0.806), (1.735, 0.826)]
    poly = round_poly(outline, 0.022, rn)
    for s in (1, -1):
        pts = [Vector((s * plate_x(y), y, z)) for y, z in poly]
        tv = Vector((s * PLATE_T, -s * PLATE_T * 0.0508, 0))
        out.append(P.solid_from_outline(pts, tv, bevel=bevel, segs=segs))
        # --- strut: parallelogram leaning rearward, rounded corners
        so = [(1.816, 0.690), (1.944, 0.650), (2.040, 0.936), (1.912, 0.936)]
        sp = round_poly(so, 0.014, rn)
        x = s * STRUT_X - STRUT_T / 2
        pts = [Vector((x, y, z)) for y, z in sp]
        out.append(P.solid_from_outline(pts, Vector((STRUT_T, 0, 0)), bevel=bevel * 0.6, segs=segs))
        # --- foot plate (slightly raked like the roof/boot surface)
        fo = [(0.332, 1.784, 0.697), (0.412, 1.784, 0.692), (0.412, 1.976, 0.640), (0.332, 1.976, 0.643)]
        fpts = [Vector((s * a, y, z)) for a, y, z in fo]
        out.append(P.solid_from_outline(fpts, Vector((0, 0, -FOOT_T)), bevel=bevel * 0.7, segs=segs))
    return out


def rebuild(obj, bevel, segs, rn=4):
    mw = obj.matrix_world
    n = P.delete_islands(obj, is_old)
    for bm in make_solids(bevel, segs, rn):
        P.inject(bm, obj, matidx=0, uvscale=1.0)
        bm.free()
    return n
