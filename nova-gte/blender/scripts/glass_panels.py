"""Inset glass panels in the body shell: tailgate glass and sunroof (runs inside Blender, called by build_body).

The zone approach (glass material on the loft's own faces) can only make straight-edged glass along the loft rows.
Here each panel is a rounded outline in its own plane (u across the car, v along the glass, n outward), measured
from the photos (body_profile glass_panels, model frame = photo frame + DZ):
  * the shell faces inside the outline (+ a small margin) are deleted - the hole's ragged edge is hidden under the seal;
  * the glass is a separate mesh following the shell surface, recessed along -n;
  * a black rubber seal ring runs from just outside the hole edge (lying on the paint) down into the recess.
Glass uses the shell's glass material (AC: transparent, sorted), the seal trim_black.
"""
import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def rounded_outline(corners, radii, n_arc=10):
    """Convex polygon (u, v) corners (counter-clockwise) with a fillet radius per corner -> dense outline."""
    out = []
    n = len(corners)
    for i in range(n):
        p0, p1, p2 = Vector(corners[i - 1]), Vector(corners[i]), Vector(corners[(i + 1) % n])
        r = radii[i]
        a, b = (p0 - p1).normalized(), (p2 - p1).normalized()
        half = a.angle(b) / 2
        d = r / math.tan(half)                       # tangent points along each edge
        c = p1 + (a + b).normalized() * (r / math.sin(half))
        t0, t1 = p1 + a * d, p1 + b * d
        a0 = math.atan2(t0.y - c.y, t0.x - c.x)
        a1 = math.atan2(t1.y - c.y, t1.x - c.x)
        da = a1 - a0
        while da > math.pi:
            da -= 2 * math.pi
        while da < -math.pi:
            da += 2 * math.pi
        for k in range(n_arc + 1):
            ang = a0 + da * k / n_arc
            out.append((c.x + r * math.cos(ang), c.y + r * math.sin(ang)))
    return out


def offset(poly, d):
    """Offset a convex counter-clockwise polygon outward by d (vertex normals, mitred)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((e0.y, -e0.x)), Vector((e1.y, -e1.x))
        m = (n0 + n1).normalized()
        k = max(0.3, m.dot(n0))
        q = p1 + m * (d / k)
        out.append((q.x, q.y))
    return out


def inside(poly, u, v):
    c = False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i - 1], poly[i]
        if (y0 > v) != (y1 > v) and u < x0 + (x1 - x0) * (v - y0) / (y1 - y0):
            c = not c
    return c


class Panel:
    def __init__(self, name, origin, v_dir, n_dir, corners, radii, recess, seal, margin=0.004, wall_seal=None):
        self.name = name
        self.O = Vector(origin)
        self.U = Vector((1.0, 0.0, 0.0))
        self.V = Vector(v_dir).normalized()
        self.N = Vector(n_dir).normalized()
        self.poly = rounded_outline(corners, radii)
        self.recess, self.seal, self.margin = recess, seal, margin
        self.wall_seal = wall_seal              # set: deep recess with body-colour walls and a seal of this width

    def uv(self, p):
        d = p - self.O
        return d.dot(self.U), d.dot(self.V)

    def p3(self, u, v):
        return self.O + self.U * u + self.V * v

    def in_hole(self, p):
        u, v = self.uv(p)
        return inside(offset(self.poly, self.margin), u, v) if not hasattr(self, "_hole") else inside(self._hole, u, v)

    def prepare(self):
        self._hole = offset(self.poly, self.margin)

    def project(self, bvh, u, v):
        """Point on the shell surface over (u, v): ray from outside along -n."""
        start = self.p3(u, v) + self.N * 0.3
        h = bvh.ray_cast(start, -self.N, 0.6)
        return h[0] if h[0] is not None else self.p3(u, v)


def shell_bvh(bm):
    """BVH of a half shell (x >= 0) mirrored to both sides."""
    bmc = bm.copy()
    geom = bmc.verts[:] + bmc.edges[:] + bmc.faces[:]
    ret = bmesh.ops.duplicate(bmc, geom=geom)
    vs = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    for v in vs:
        v.co.x = -v.co.x
    bvh = BVHTree.FromBMesh(bmc)
    bmc.free()
    return bvh


def build_meshes(panel, bvh, glass_mat, seal_mat, coll, paint_mat=None):
    """Glass (rings shrinking to the centroid, recessed) and the seal ring, both full width."""
    P = panel
    poly = P.poly
    cu = sum(u for u, v in poly) / len(poly)
    cv = sum(v for u, v in poly) / len(poly)
    # glass: concentric rings at the outline scaled towards the centroid
    bm = bmesh.new()
    rings = []
    for s in (1.0, 0.85, 0.68, 0.5, 0.32, 0.15):
        ring = []
        for u, v in poly:
            uu, vv = cu + (u - cu) * s, cv + (v - cv) * s
            ring.append(bm.verts.new(P.project(bvh, uu, vv) - P.N * P.recess))
        rings.append(ring)
    centre = bm.verts.new(P.project(bvh, cu, cv) - P.N * P.recess)
    n = len(poly)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    for i in range(n):
        bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], centre))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bm.faces and sum(f.normal.dot(P.N) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    g = _obj("GLASS_" + P.name, bm, [glass_mat], coll)
    if P.wall_seal and paint_mat is not None:
        # deep recess: body-colour wall from a lip on the paint (covers the ragged hole edge) rolling over and down
        # to just above the glass; then a black rubber seal stepping onto the glass edge
        bm = bmesh.new()
        D = P.recess
        wprof = [(P.margin + 0.006, 0.0006), (P.margin + 0.002, 0.0002), (P.margin, -0.003),
                 (P.margin * 0.5, -0.30 * D), (0.0, -D + P.wall_seal * 0.6)]
        _ring_strip(bm, P, bvh, poly, wprof)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        w = _obj("RECESS_" + P.name, bm, [seal_mat], coll)
        for poly_ in w.data.polygons:
            poly_.use_smooth = True
        bm = bmesh.new()
        sprof = [(0.0015, -D + P.wall_seal * 0.6), (0.0, -D + 0.003), (-P.wall_seal * 0.5, -D + 0.0025),
                 (-P.wall_seal, -D + 0.0008)]
        _ring_strip(bm, P, bvh, poly, sprof)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        s_ = _obj("SEAL_" + P.name, bm, [seal_mat], coll)
        for poly_ in s_.data.polygons:
            poly_.use_smooth = True
        return g, s_
    # seal: outer lip on the paint (covers the hole's ragged edge), round over into the recess, down to the glass
    bm = bmesh.new()
    prof = [(P.seal, 0.0012), (P.seal * 0.55, 0.0025), (P.margin, 0.0015), (0.0, -P.recess * 0.6), (-0.004, -P.recess + 0.001)]
    loops = []
    for d, h in prof:
        loop = []
        for u, v in offset(poly, d):
            base = P.project(bvh, u, v)
            loop.append(bm.verts.new(base + P.N * h))
        loops.append(loop)
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((l0[i], l0[j], l1[j], l1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    s = _obj("SEAL_" + P.name, bm, [seal_mat], coll)
    for o in (g, s):
        for poly_ in o.data.polygons:
            poly_.use_smooth = True
    return g, s


def _ring_strip(bm, P, bvh, poly, prof):
    """Closed strip of rings around the outline: each (offset outward, height along n above the shell surface)."""
    n = len(poly)
    loops = []
    for dd, hh in prof:
        loops.append([bm.verts.new(P.project(bvh, u, v) + P.N * hh) for u, v in offset(poly, dd)])
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((l0[i], l0[j], l1[j], l1[i]))


def _obj(name, bm, mats, coll):
    old = bpy.data.objects.get(name)
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        if me_old and me_old.users == 0:
            bpy.data.meshes.remove(me_old)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    for m in mats:
        o.data.materials.append(m)
    coll.objects.link(o)
    return o


def panels(PF, dz):
    """Panels from body_profile glass_panels (photo frame) -> model frame (+dz)."""
    out = []
    GP = PF.get("glass_panels", {})
    for name, d in GP.items():
        if name.startswith("_"):
            continue
        o = (0.0, d["origin"][0], d["origin"][1] + dz)
        out.append(Panel(name.upper(), o, (0.0, d["v_dir"][0], d["v_dir"][1]), (0.0, d["n_dir"][0], d["n_dir"][1]),
                         [tuple(c) for c in d["corners"]], d["radii"], d["recess"], d["seal"], d.get("margin", 0.004),
                         d.get("wall_seal")))
    return out
