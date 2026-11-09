"""NICK3 rear diffuser rebuild (reproducible). Replaces the stock/loose-quad floor, fences and end plates
in the carbon meshes with clean thick solids. Run build_all() once per mesh set.
Coordinates: metres, car faces -Y, +Z up. Ramp: top surface z = -0.092 + 0.164*(y-1.49).
"""
import bpy, bmesh
from mathutils import Vector
import nick3_parts as P

Y0, Y1 = 1.49, 2.30
XF = 0.775                      # floor half-width
FENCE_X = (0.202, 0.480)        # fence centre lines (both sides)
PLATE_X = 0.771                 # end plate centre line
FLOOR_T = 0.006
FENCE_T = 0.008
PLATE_T = 0.008


YB = 1.77                       # ramp bend (5.5 deg -> 11.3 deg), measured from the stock floor


def zt(y):                      # ramp top surface (two-slope, matches stock floor within 3 mm)
    if y <= YB: return -0.092 + 0.096 * (y - Y0)
    return -0.092 + 0.096 * (YB - Y0) + 0.2 * (y - YB)


def zb(y):                      # fence bottom line
    return -0.108 - 0.0222 * (y - Y0)


def is_old_part(c, b):
    """island belongs to the old diffuser floor / fences / end plates"""
    if not (b[2] > 1.45 and b[3] < 2.31): return False
    xc = (b[0] + b[1]) / 2; w = b[1] - b[0]
    if w < 0.012:
        for t in FENCE_X + (PLATE_X, 0.7685, 0.775):
            if abs(abs(xc) - t) < 0.012 and b[4] > -0.14 and b[5] < 0.19: return True
    if max(abs(b[0]), abs(b[1])) < 0.78 and b[2] > 1.45:
        ok = all(abs(v_z - zt(v_y)) < 0.012 for v_y, v_z in b_pts(c))
        if ok: return True
    return False


_cur = {}
def b_pts(c):
    mw = _cur['mw']
    for v in c:
        w = mw @ v.co
        yield w.y, w.z


def make_solids(bevel, segs, plate_bevel=None):
    out = []
    pb = bevel * 1.2 if plate_bevel is None else plate_bevel
    for s in (1, -1):
        # floor (one piece, built on the +x side only once)
        pass
    prof = [(Y0, zt(Y0)), (YB, zt(YB)), (Y1, zt(Y1)), (Y1, zt(Y1) - FLOOR_T), (YB, zt(YB) - FLOOR_T), (Y0, zt(Y0) - FLOOR_T)]
    fl = [Vector((-XF, y, z)) for y, z in prof]
    out.append(P.solid_from_outline(fl, Vector((2 * XF, 0, 0)), bevel=bevel, segs=segs))
    for s in (1, -1):
        for xc in FENCE_X:
            x = s * xc - FENCE_T / 2
            pts = [Vector((x, Y0, zt(Y0) - 0.004)), Vector((x, YB, zt(YB) - 0.004)), Vector((x, Y1, zt(Y1) - 0.004)),
                   Vector((x, Y1, zb(Y1))), Vector((x, Y0, zb(Y0)))]
            out.append(P.solid_from_outline(pts, Vector((FENCE_T, 0, 0)), bevel=bevel * 0.6, segs=segs))
        x = s * PLATE_X - PLATE_T / 2
        poly = [(1.56, -0.117), (2.30, -0.005), (2.30, 0.140), (2.25, 0.158), (1.70, 0.074), (1.56, 0.003)]
        pts = [Vector((x, y, z)) for y, z in poly]
        out.append(P.solid_from_outline(pts, Vector((PLATE_T, 0, 0)), bevel=pb, segs=segs))
    return out


def rebuild(obj, bevel, segs):
    _cur['mw'] = obj.matrix_world
    n = P.delete_islands(obj, is_old_part)
    for bm in make_solids(bevel, segs):
        P.inject(bm, obj, matidx=0, uvscale=1.0)
        bm.free()
    return n
