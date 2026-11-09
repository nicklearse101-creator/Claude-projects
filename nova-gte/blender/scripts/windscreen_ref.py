"""Windscreen rebuilt to a clean outline (Nik 2026-10-19: the surround 'looks like utter crap', gap under the roof).
Runs after frames_ref.py, before details_ref.py; replaces GLASS_WINDSCREEN and DET_WS_RUBBER.

Body opening measured on the body (rays along the glass normal, 5 mm grid): sides straight, x = +-(0.640 - 0.3125
(z - 0.96)), header z 1.293; base lowered to z 0.885 (the model's scuttle slope continues the screen surface to there). Outline = that trapezoid with 50 mm corner radii.
- Everything of REF_BODY inside the outline (grown 3 mm) lying within -40 / +12 mm of the glass surface is removed
  (the model's ragged frame, rubber and old-screen leftovers).
- Glass: rows across the outline set 10 mm in, on the smooth screen surface (quadratic fit of the old screen).
- Rubber gasket (black): from 16 mm in on the glass, a 4.5 mm bead, out to 7 mm past the opening edge where it is laid
  on the body (rays along the glass normal) - closes any gap to the roof header, pillars and scuttle.
Car frame: x+ = car's left, y- = front, z up. 'In-plane' coordinates are (x, z) on the screen surface.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SIDE = (0.640, 0.3125, 0.96)        # x = a - b (z - z0)
Z_BASE, Z_HEAD, R = 0.885, 1.293, 0.05      # base lowered from the opening's 0.938 (Nik: windscreen too high;
                                            # photos 20/22: glass sits right on the slotted strip behind the bonnet)
N_EDGE = {"base": 48, "right": 30, "head": 44, "left": 30}
N_ARC = 10


def fit():
    """Screen surface y = f(x, z) from the current GLASS_WINDSCREEN (prep_reference's fitted pane)."""
    G = np.array([v.co[:] for v in bpy.data.objects["GLASS_WINDSCREEN"].data.vertices])
    A = np.stack([np.ones(len(G)), G[:, 0] ** 2, G[:, 2], G[:, 2] ** 2, G[:, 0] ** 2 * G[:, 2]], 1)
    return np.linalg.lstsq(A, G[:, 1], rcond=None)[0]


def surf(c, x, z):
    y = c[0] + c[1] * x * x + c[2] * z + c[3] * z * z + c[4] * x * x * z
    n_in = Vector((-(2 * c[1] * x + 2 * c[4] * x * z), 1.0, -(c[2] + 2 * c[3] * z + c[4] * x * x))).normalized()
    return Vector((x, y, z)), n_in


def _trapezoid():
    a, b, z0 = SIDE
    xb, xt = a - b * (Z_BASE - z0), a - b * (Z_HEAD - z0)
    return [(-xb, Z_BASE), (xb, Z_BASE), (xt, Z_HEAD), (-xt, Z_HEAD)]       # counter-clockwise seen from the front


def _offset_lines(P, d):
    """Edges of convex polygon P offset outward by d -> list of (point, direction, outward normal)."""
    out = []
    for i in range(len(P)):
        p, q = np.array(P[i]), np.array(P[(i + 1) % len(P)])
        t = (q - p) / np.linalg.norm(q - p)
        n = np.array([t[1], -t[0]])                                          # outward for CCW
        out.append((p + n * d, t, n))
    return out


def _intersect(l1, l2):
    p1, t1, _ = l1; p2, t2, _ = l2
    A = np.array([[t1[0], -t2[0]], [t1[1], -t2[1]]])
    s = np.linalg.solve(A, p2 - p1)
    return p1 + t1 * s[0]


def outline(d):
    """Rounded outline offset d (outward +) from the opening edge: same point layout for every d (base, right side,
    head, left side, each followed by its corner arc)."""
    P = _trapezoid()
    core_lines = _offset_lines(P, -R)
    core = [_intersect(core_lines[i - 1], core_lines[i]) for i in range(len(P))]   # core[i] = corner at P[i]
    rad = R + d
    pts = []
    names = ["base", "right", "head", "left"]
    for i in range(len(P)):
        _, t, n = core_lines[i]
        a0, a1 = core[i] + n * rad, core[(i + 1) % len(P)] + n * rad
        k = N_EDGE[names[i]]
        pts += [tuple(a0 + (a1 - a0) * s / k) for s in range(k)]
        # arc round core corner i+1 from this edge's normal to the next edge's normal
        n2 = core_lines[(i + 1) % len(P)][2]
        ang0, ang1 = math.atan2(n[1], n[0]), math.atan2(n2[1], n2[0])
        while ang1 < ang0:
            ang1 += 2 * math.pi
        cc = core[(i + 1) % len(P)]
        pts += [tuple(cc + rad * np.array([math.cos(ang0 + (ang1 - ang0) * s / N_ARC), math.sin(ang0 + (ang1 - ang0) * s / N_ARC)]))
                for s in range(N_ARC)]
    return np.array(pts)


def _inside(poly, X, Z):
    """Point-in-polygon (even-odd) for arrays X, Z."""
    ins = np.zeros(len(X), bool)
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % n]
        crosses = ((z1 > Z) != (z2 > Z))
        xi = x1 + (Z - z1) * (x2 - x1) / np.where(z2 - z1 == 0, 1e-12, z2 - z1)
        ins ^= crosses & (X < xi)
    return ins


def _object(name, bm, mats):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.data.collections["REF"].objects.link(o)
    return o


def clear_opening(c):
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    poly = outline(0.003)
    ins = _inside(poly, C[:, 0], C[:, 2])
    idx = np.where(ins)[0]
    keep = np.zeros(n, bool)
    for i in idx:
        S, nin = surf(c, C[i, 0], C[i, 2])
        dd = (Vector(C[i]) - S).dot(nin)
        keep[i] = -0.04 < dd < 0.012
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in np.where(keep)[0]], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    return int(keep.sum())


def glass(c):
    poly = outline(-0.010)
    zs = np.arange(poly[:, 1].min() + 0.0005, poly[:, 1].max(), 0.01)
    zs = np.append(zs, poly[:, 1].max() - 0.0005)
    bm = bmesh.new()
    rows = []
    for z in zs:
        xs = []
        for i in range(len(poly)):                                          # x-extent of the outline at height z
            (x1, z1), (x2, z2) = poly[i], poly[(i + 1) % len(poly)]
            if (z1 - z) * (z2 - z) <= 0 and z1 != z2:
                xs.append(x1 + (z - z1) * (x2 - x1) / (z2 - z1))
        x0, x1 = min(xs), max(xs)
        rows.append([bm.verts.new(surf(c, x, z)[0]) for x in np.linspace(x0, x1, 61)])
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(60):
            f = bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = _object("GLASS_WINDSCREEN", bm, [bpy.data.materials["glass_tint"]])
    return len(o.data.polygons)


def gasket(c, bvh):
    """Rings (in-plane offset d, height h above the glass along the outward normal); the last ring is laid on the body."""
    spec = [(-0.016, 0.0012), (-0.012, 0.0035), (-0.006, 0.0045), (0.000, 0.0040)]
    bm = bmesh.new()
    rings = []
    for d, h in spec:
        rings.append([bm.verts.new(surf(c, x, z)[0] - surf(c, x, z)[1] * h) for x, z in outline(d)])
    body = []
    for x, z in outline(0.007):
        S, nin = surf(c, x, z)
        hit = bvh.ray_cast(S - nin * 0.06, nin, 0.12)
        ok = hit[0] is not None and -0.03 < (hit[0] - S).dot(nin) < 0.025
        body.append(bm.verts.new((hit[0] - nin * 0.0005) if ok else (S - nin * 0.002)))
    rings.append(body)
    out = -surf(c, 0.0, 1.1)[1]
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        fs = [bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])) for k in range(n)]
        f0 = max(fs, key=lambda f: f.calc_area()); f0.normal_update()
        if f0.normal.dot(out) < 0:
            bmesh.ops.reverse_faces(bm, faces=fs)
        for f in fs:
            f.smooth = True
    o = _object("DET_WS_RUBBER", bm, [bpy.data.materials["rubber_black"]])
    return len(o.data.polygons)


def main():
    c = fit()
    cut = clear_opening(c)
    bvh = BVHTree.FromObject(bpy.data.objects["REF_BODY"], bpy.context.evaluated_depsgraph_get())
    return {"faces_removed": cut, "glass_faces": glass(c), "gasket_faces": gasket(c, bvh)}


if __name__ == "__main__":
    print("==", main())
