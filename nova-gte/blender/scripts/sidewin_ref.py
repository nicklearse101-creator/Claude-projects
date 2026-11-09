"""Side windows rebuilt to clean outlines (Nik 2026-10-19: window surrounds should be black rubber, not grey and
jagged; step in the bottom edge of the rear windows). Runs after frames_ref.py (whose side frame strips it removes),
before details_ref.py; replaces GLASS_DOOR_*, GLASS_VENT_*, GLASS_QUARTER_*.

Outlines measured on the body openings (side scan, 2.5 mm; car's left, mirrored for the right), straight edges with
rounded corners, in (y, z):
  DOOR    bottom z = 0.8605 + 0.020 y, rear y = 0.400 + 0.036 (z - 0.88), top z = 1.225 + 0.025 y,
          front (division bar) y = -0.218 + 0.077 (z - 0.88)
  VENT    bottom z 0.860, rear (bar) y = -0.258 + 0.089 (z - 0.86), A-pillar y = -0.403 + 1.13 (z - 1.0),
          front y -0.400 (the mirror sail covers the glass ahead of it)
  QUARTER front y 0.621, bottom z = 0.883 + 0.023 (y - 0.65) straight through to the rear (the step is gone),
          rear = the C-pillar fin line y = 1.36 - 0.75 (z - 0.93), top z = 1.220 - 0.0233 (y - 0.65)
For each: REF_BODY faces inside the outline (+3 mm) within 6 cm inside / 12 mm outside the glass plane removed; glass
10 mm inside the outline on the fitted glass plane (prep_reference.side_apertures); black rubber seal from 14 mm in on
the glass, a 3.5 mm bead, laid onto the body 7 mm outside the opening edge.
"""
import math

import bmesh
import bpy
import numpy as np

import prep_reference as pr

WINDOWS = {
    "DOOR": ([("z", 0.8605, 0.020), ("y", 0.400, 0.036, 0.88), ("z", 1.225, 0.025), ("y", -0.218, 0.077, 0.88)],
             (0.012, 0.012, 0.03, 0.05)),
    "VENT": ([("z", 0.860, 0.0), ("y", -0.258, 0.089, 0.86), ("a", -0.403, 1.13, 1.0), ("y", -0.400, 0.0, 0.0)],
             (0.008, 0.012, 0.012, 0.008)),
    "QUARTER": ([("zq", 0.883, 0.023, 0.65), ("y", 1.36, -0.75, 0.93), ("zq", 1.220, -0.0233, 0.65), ("y", 0.621, 0.0, 0.0)],
                (0.012, 0.02, 0.04, 0.03)),
}
STEP = 0.006
SEAL = [(-0.014, 0.0010), (-0.010, 0.0030), (-0.005, 0.0035), (0.000, 0.0030)]
LAY_OUT = 0.007


def _line(spec):
    """Line in (y, z) as (point, direction)."""
    k = spec[0]
    if k == "z":                                        # z = c + s y
        _, c, s = spec; return np.array([0.0, c]), np.array([1.0, s])
    if k == "zq":                                       # z = c + s (y - y0)
        _, c, s, y0 = spec; return np.array([y0, c]), np.array([1.0, s])
    if k in ("y", "a"):                                 # y = c + s (z - z0)
        _, c, s, z0 = spec; return np.array([c, z0]), np.array([s, 1.0])
    raise ValueError(k)


def _isect(l1, l2):
    (p1, t1), (p2, t2) = l1, l2
    s = np.linalg.solve(np.array([[t1[0], -t2[0]], [t1[1], -t2[1]]]), p2 - p1)
    return p1 + t1 * s[0]


def polygon(name):
    lines, _ = WINDOWS[name]
    L = [_line(s) for s in lines]
    P = [_isect(L[i - 1], L[i]) for i in range(len(L))]            # P[i] = start of edge i
    area = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
    if area < 0:
        raise ValueError("outline not counter-clockwise: " + name)
    return P


def outline(name, d):
    """Rounded outline offset d (outward +); same point layout for every d."""
    P = polygon(name)
    R = WINDOWS[name][1]
    n = len(P)
    edges = []
    for i in range(n):
        p, q = P[i], P[(i + 1) % n]
        t = (q - p) / np.linalg.norm(q - p)
        edges.append((p, q, t, np.array([t[1], -t[0]])))               # outward normal for CCW
    pts = []
    for i in range(n):
        p, q, t, nrm = edges[i]
        r0, r1 = R[i], R[(i + 1) % n]                                    # radii at this edge's start / end corner
        # corner centres (inside by r along both edge normals)
        def centre(k, r):
            a = edges[k - 1]; b = edges[k]
            l1 = (a[0] - a[3] * r, a[2]); l2 = (b[0] - b[3] * r, b[2])
            return _isect(l1, l2)
        c0, c1 = centre(i, r0), centre((i + 1) % n, r1)
        a0, a1 = c0 + nrm * (r0 + d), c1 + nrm * (r1 + d)
        k = max(2, int(np.linalg.norm(a1 - a0) / STEP))
        pts += [a0 + (a1 - a0) * s / k for s in range(k)]
        n2 = edges[(i + 1) % n][3]
        ang0, ang1 = math.atan2(nrm[1], nrm[0]), math.atan2(n2[1], n2[0])
        while ang1 < ang0:
            ang1 += 2 * math.pi
        m = 8
        pts += [c1 + (r1 + d) * np.array([math.cos(ang0 + (ang1 - ang0) * s / m), math.sin(ang0 + (ang1 - ang0) * s / m)])
                for s in range(m)]
    return np.array(pts)


def _inside(poly, Y, Z):
    ins = np.zeros(len(Y), bool)
    for i in range(len(poly)):
        y1, z1 = poly[i]; y2, z2 = poly[(i + 1) % len(poly)]
        cr = (z1 > Z) != (z2 > Z)
        yi = y1 + (Z - z1) * (y2 - y1) / np.where(z2 - z1 == 0, 1e-12, z2 - z1)
        ins ^= cr & (Y < yi)
    return ins


def _object(name, bm, mat):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.data.collections["REF"].objects.link(o)
    return o


def clear(surfs):
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    dead = np.zeros(n, bool)
    for name in WINDOWS:
        poly = outline(name, 0.003)
        ins = _inside(poly, C[:, 1], C[:, 2])
        idx = np.where(ins)[0]
        if len(idx):
            dd = np.abs(C[idx, 0]) - surfs[name](C[idx, 1], C[idx, 2])
            dead[idx[(dd > -0.06) & (dd < 0.012)]] = True
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in np.where(dead)[0]], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    return int(dead.sum())


def build(surfs):
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    bvh = BVHTree.FromObject(bpy.data.objects["REF_BODY"], bpy.context.evaluated_depsgraph_get())
    glass_m, rubber = bpy.data.materials["glass_tint"], bpy.data.materials["rubber_black"]
    out = {}
    for name in WINDOWS:
        surf = surfs[name]
        for side, sx in (("L", 1.0), ("R", -1.0)):
            # glass: rows across the outline (10 mm in)
            poly = outline(name, -0.010)
            bm = bmesh.new()
            zs = np.linspace(poly[:, 1].min() + 1e-4, poly[:, 1].max() - 1e-4, max(3, int(np.ptp(poly[:, 1]) / 0.01)))
            rows = []
            for z in zs:
                ys = []
                for i in range(len(poly)):
                    (y1, z1), (y2, z2) = poly[i], poly[(i + 1) % len(poly)]
                    if (z1 - z) * (z2 - z) <= 0 and z1 != z2:
                        ys.append(y1 + (z - z1) * (y2 - y1) / (z2 - z1))
                y0, y1 = min(ys), max(ys)
                rows.append([bm.verts.new((sx * (surf(y, z) - pr.INSET), y, z)) for y in np.linspace(y0, y1, 40)])
            for r0, r1 in zip(rows, rows[1:]):
                for k in range(39):
                    f = bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k])); f.smooth = True
            for f in bm.faces:
                f.normal_update()
                if f.normal.x * sx < 0:
                    f.normal_flip()
            _object("GLASS_%s_%s" % (name, side), bm, glass_m)
            # rubber seal
            bm = bmesh.new()
            rings = []
            for d, h in SEAL:
                rings.append([bm.verts.new((sx * (surf(y, z) - pr.INSET + h), y, z)) for y, z in outline(name, d)])
            body = []
            for y, z in outline(name, LAY_OUT):
                g = surf(y, z)
                hit = bvh.ray_cast(Vector((sx * (g + 0.06), y, z)), Vector((-sx, 0, 0)), 0.12)
                ok = hit[0] is not None and -0.03 < abs(hit[0].x) - g < 0.025
                body.append(bm.verts.new((hit[0].x + sx * 0.0005, y, z) if ok else (sx * (g + 0.002), y, z)))
            rings.append(body)
            for a, b in zip(rings, rings[1:]):
                n = len(a)
                fs = [bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])) for k in range(n)]
                f0 = max(fs, key=lambda f: f.calc_area()); f0.normal_update()
                if f0.normal.x * sx < 0:
                    bmesh.ops.reverse_faces(bm, faces=fs)
                for f in fs:
                    f.smooth = True
            out["%s_%s" % (name, side)] = len(_object("DET_SEAL_%s_%s" % (name, side), bm, rubber).data.polygons)
    return out


def main():
    for o in [o for o in bpy.data.objects if o.name.startswith("DET_FRAME_")]:
        bpy.data.objects.remove(o)
    surfs = {name: surf for name, (m, cols, surf, err) in pr.side_apertures().items()}
    removed = clear(surfs)
    res = build(surfs)
    res["faces_removed"] = removed
    return res


if __name__ == "__main__":
    print("==", main())
