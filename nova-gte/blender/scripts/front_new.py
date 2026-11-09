"""New front end built from scratch (Nik 2026-10-19: replace each part with new clean geometry, matched to the
pictures): body-colour grille frame with the groove across its top band, recessed black grille with horizontal slats
and short vertical dividers, and the two headlamp units (clear glass + amber indicator in a black bezel). Sizes are
read off Nik's grey front picture (reference/photos/grey_studio/front.png, camera grey_views.FRONT_CAM: 176 px/m at
the face, heights anchored on the number plate) and the detail off the red Commons photo
(1989_Vauxhall_Nova_GTE_1.6_Front.jpg). Depth (y) follows the old model's front face.
Replaces: the old grille faces of REF_BODY, DET_LAMP_HEAD (same name, lights.ini) and the front faces of
DET_LAMP_IND_L/R (same names, ext_config.ini). Runs after details_ref (which splits the lamps and places the badge).
Car frame: x+ = car's left, y- = front, z up."""
import bmesh
import numpy as np

import bpy
from mathutils import Vector

R = 0.004                                   # rounded front edges
# grille frame (picture: outer x +-0.415, z 0.518..0.685; opening x +-0.380, z 0.543..0.643)
FR_OUT = ((0.408, 0.415), 0.522, 0.684)     # (x at bottom, x at top), z bottom, z top - face area (rim adds R)
FR_IN = ((0.376, 0.384), 0.539, 0.649)      # opening as a hole in the face (rim adds R inwards)
GROOVE = (0.6625, 0.6665, 0.0015, 0.392)    # z0, z1, depth, half length
INSERT_D, SLAT_D, SLATS = 0.030, 0.007, 7
# headlamp unit (picture: x 0.415..0.706, z 0.533..0.682; glass/indicator split at x 0.628)
UNIT_X = (0.419, 0.424, 0.624, 0.632, 0.698, 0.703)
UNIT_Z = (0.536, 0.541, 0.674, 0.679)


def y_frame(x, z):
    return -1.762 + 0.23 * x * x + 0.20 * (z - 0.55)


WING_END = ((0.55, 0.705), (0.60, 0.700), (0.65, 0.690), (0.68, 0.683))   # wing front end: x at y -1.575 (scan)
Y_WING = -1.575


def x_end(z):
    zz, xx = zip(*WING_END)
    return float(np.interp(z, zz, xx))


def y_lamp(x, z):
    """Lamp glass face; the indicator curves back round the corner to meet the wing's front end (x_end, -1.575)."""
    ax = abs(x)
    y0 = lambda a: -1.703 + 0.175 * (a - 0.44) + 0.25 * (z - 0.60)
    if ax <= 0.628:
        return y0(ax)
    xe = x_end(z)
    t = min(1.0, (ax - 0.628) / (xe - 0.628))
    return y0(ax) + (Y_WING - y0(xe)) * t ** 2.5


def lin(a, b, n):
    return list(np.linspace(a, b, n + 1))


def breaks(spec):
    """[(a, b, n), ...] -> sorted unique break list."""
    out = []
    for a, b, n in spec:
        out += lin(a, b, n)
    return sorted(set(round(v, 6) for v in out))


def rim(bm, depth, r, back=Vector((0, 1, 0)), steps=3, faces=None, edges=None, dfn=None):
    """Round the free edges of the patch over (quarter round, radius r) and run a wall straight back to depth."""
    faces = set(faces or bm.faces)
    if edges is None:
        edges = [e for e in bm.edges if e.is_boundary and e.link_faces[0] in faces]
    dirs = {}
    for e in edges:
        f = e.link_faces[0]
        a, b = e.verts
        t = (b.co - a.co).normalized()
        d = t.cross(f.normal).normalized()
        if d.dot(a.co - f.calc_center_median()) < 0:
            d = -d
        d = (d - back * d.dot(back)).normalized()
        for v in (a, b):
            dirs.setdefault(v, []).append(d)
    rings = {}
    for v, ds in dirs.items():
        d = sum(ds, Vector()).normalized()
        if len(ds) == 2:
            d = d / max(0.5, ds[0].dot(d))       # corner: keep the offset on both edges
        if dfn is not None:
            d = dfn(v)
        ring = [v]
        for k in range(1, steps + 1):
            a = np.pi / 2 * k / steps
            ring.append(bm.verts.new(v.co + d * r * np.sin(a) + back * r * (1 - np.cos(a))))
        ring.append(bm.verts.new(v.co + d * r + back * depth))
        rings[v] = ring
    new = []
    for e in edges:
        a, b = e.verts
        f0 = e.link_faces[0]
        for k in range(len(rings[a]) - 1):
            q = (rings[a][k], rings[b][k], rings[b][k + 1], rings[a][k + 1])
            f = bm.faces.new(q); f.material_index = f0.material_index; f.smooth = True
            new.append(f)
    return new


def patch(bm, xs, zs, yfn, keep=lambda i, j, x, z: True, xfn=None, mat=lambda i, j, x, z: 0):
    """Quad grid over breaks xs (|x| list, mirrored by caller) x zs; xfn(x, z) remaps x (trapezoids)."""
    V = {}
    for i, z in enumerate(zs):
        for j, x in enumerate(xs):
            xx = xfn(x, z) if xfn else x
            V[i, j] = (xx, z)
    made = {}
    def vert(i, j):
        if (i, j) not in made:
            x, z = V[i, j]
            made[i, j] = bm.verts.new((x, yfn(x, z), z))
        return made[i, j]
    fs = []
    for i in range(len(zs) - 1):
        for j in range(len(xs) - 1):
            xc = (V[i, j][0] + V[i, j + 1][0]) / 2; zc = (zs[i] + zs[i + 1]) / 2
            if not keep(i, j, xc, zc):
                continue
            f = bm.faces.new((vert(i, j), vert(i, j + 1), vert(i + 1, j + 1), vert(i + 1, j)))
            f.material_index = mat(i, j, xc, zc); f.smooth = True
            fs.append(f)
    return fs, made


def orient(bm, outward=Vector((0, -1, 0))):
    for f in bm.faces:
        f.normal_update()
    big = [f for f in bm.faces if abs(f.normal.y) > 0.7]
    if big and sum(f.normal.dot(outward) for f in big) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])


def to_object(name, bm, mats, parent_coll="REF"):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(bpy.data.materials[m])
    ob = bpy.data.objects.new(name, me); bpy.data.collections[parent_coll].objects.link(ob)
    return ob


def frame():
    (xb, xt), z0, z1 = FR_OUT
    (ib, it), i0, i1 = FR_IN
    g0, g1, gd, gl = GROOVE
    # x breaks in a unit space: -1..1 outer, inner at +-u_in, remapped per z to the trapezoid
    u_in = 0.92
    us = breaks([(-1, -u_in, 4), (-u_in, u_in, 60), (u_in, 1, 4)])
    zs = breaks([(z0, i0, 4), (i0, i1, 24), (i1, g0, 4), (g0, g1, 2), (g1, z1, 3)])

    def xo(z):
        return xb + (xt - xb) * (z - z0) / (z1 - z0)

    def xi(z):
        return ib + (it - ib) * (z - i0) / (i1 - i0)

    def xfn(u, z):
        a = abs(u)
        x = xi(z) * a / u_in if a <= u_in else xi(z) + (xo(z) - xi(z)) * (a - u_in) / (1 - u_in)
        return float(np.sign(u) * x)

    def yfn(x, z):
        y = y_frame(x, z)
        if g0 < z < g1 and abs(x) < gl:
            y += gd
        if abs(z - g0) < 1e-6 or abs(z - g1) < 1e-6:
            y += 0.0
        return y

    def keep(i, j, x, z):
        return not (i0 < z < i1 and abs(x) < xi(z))
    bm = bmesh.new()
    zs_g = [z if not (g0 < z < g1) else z for z in zs]
    fs, made = patch(bm, us, zs_g, yfn, keep=keep, xfn=xfn)
    # groove: the row strictly inside (g0, g1) has no verts; push the two groove rows' middle verts back instead
    for (i, j), v in made.items():
        if abs(zs[i] - (g0 + g1) / 2) < (g1 - g0) / 2 + 1e-6 and abs(v.co.x) < gl and \
                (abs(zs[i] - g0) < 1e-6 or abs(zs[i] - g1) < 1e-6):
            pass
    rim(bm, 0.045, R)
    orient(bm)
    return to_object("DET_GRILLE_FRAME", bm, ["paint_gunmetal"])


def groove_fix(ob):
    """Groove across the top band: verts between g0 and g1 (the row centre line) pushed back gd."""
    g0, g1, gd, gl = GROOVE
    zc = (g0 + g1) / 2
    for v in ob.data.vertices:
        if abs(v.co.z - zc) < 0.0005 and abs(v.co.x) < gl and v.co.y < -1.69:
            v.co.y += gd


def insert():
    (ib, it), i0, i1 = FR_IN

    def xi(z):
        return ib + (it - ib) * (z - i0) / (i1 - i0) + R + 0.004

    bm = bmesh.new()

    def qf(vs, expect):
        f = bm.faces.new(vs); f.normal_update()
        if f.normal.dot(Vector(expect)) < 0:
            f.normal_flip()
        f.smooth = False
        return f
    zs = lin(i0 - R - 0.004, i1 + R + 0.004, 20)
    us = lin(-1, 1, 40)
    patch(bm, us, zs, lambda x, z: y_frame(x, z) + INSERT_D, xfn=lambda u, z: u * xi(z))
    # horizontal slats: thin plates 3.5 mm tall, front edge SLAT_D behind the frame face, running back to the insert
    zc = np.linspace(i0 + 0.008, i1 - 0.008, SLATS)
    for z in zc:
        xs = lin(-1, 1, 30)
        for zz0, zz1 in ((z - 0.00175, z + 0.00175),):
            # front face, top face, bottom face
            fr = [bm.verts.new((u * (xi(z) - 0.002), y_frame(u * xi(z), z) + SLAT_D, zz)) for zz in (zz0, zz1) for u in xs]
            n = len(xs)
            bk = [bm.verts.new((v.co.x, y_frame(v.co.x, v.co.z) + INSERT_D - 0.001, v.co.z)) for v in fr]
            for k in range(n - 1):
                qf((fr[k], fr[k + 1], fr[n + k + 1], fr[n + k]), (0, -1, 0))                 # front
                qf((fr[n + k], fr[n + k + 1], bk[n + k + 1], bk[n + k]), (0, 0, 1))          # top
                qf((bk[k], bk[k + 1], fr[k + 1], fr[k]), (0, 0, -1))                         # bottom
    # short vertical dividers between slats, a little further back
    for r, z in enumerate(zc[:-1]):
        for x in np.arange(-0.33, 0.331, 0.066) + (0.033 if r % 2 else 0.0):
            if abs(x) > 0.36:
                continue
            za, zb = z + 0.00175, z + (zc[1] - zc[0]) - 0.00175
            yf = y_frame(x, z) + SLAT_D + 0.008; yb = y_frame(x, z) + INSERT_D - 0.001
            c = [bm.verts.new((x + dx, y, zz)) for y in (yf, yb) for dx in (-0.0006, 0.0006) for zz in (za, zb)]
            qf((c[0], c[2], c[3], c[1]), (0, -1, 0))                                         # front
            qf((c[0], c[1], c[5], c[4]), (-1, 0, 0)); qf((c[2], c[6], c[7], c[3]), (1, 0, 0))  # sides
    for f in bm.faces:                       # the back plate (patch) faces forward
        f.normal_update()
        if abs(f.normal.y) > 0.9 and f.normal.y > 0:
            f.normal_flip()
    return to_object("DET_GRILLE", bm, ["grille_black"])


def lamp_units():
    """Per side: bezel (black) with the head lamp glass and the indicator glass; reflector bowl behind the glass."""
    xb = [(UNIT_X[0], UNIT_X[1], 1), (UNIT_X[1], UNIT_X[2], 24), (UNIT_X[2], UNIT_X[3], 1),
          (UNIT_X[3], UNIT_X[4], 10), (UNIT_X[4], UNIT_X[5], 1)]
    zb = [(UNIT_Z[0], UNIT_Z[1], 1), (UNIT_Z[1], UNIT_Z[2], 16), (UNIT_Z[2], UNIT_Z[3], 1)]
    xs, zs = breaks(xb), breaks(zb)

    def kind(x, z):
        ax = abs(x)
        if UNIT_Z[1] < z < UNIT_Z[2]:
            if UNIT_X[1] < ax < UNIT_X[2]:
                return "head"
            if UNIT_X[3] < ax < UNIT_X[4]:
                return "ind"
        return "bezel"
    out = {}
    for side in (1, -1):
        sx = [side * x for x in xs]
        if side < 0:
            sx = sx[::-1]
        for k in ("head", "ind", "bezel"):
            bm = bmesh.new()
            def xfn(x, z):
                ax = abs(x)
                if ax <= UNIT_X[3]:
                    return x
                xe = x_end(z)
                return float(np.sign(x) * (UNIT_X[3] + (ax - UNIT_X[3]) * (xe - UNIT_X[3]) / (UNIT_X[5] - UNIT_X[3])))
            fs, _ = patch(bm, sx, zs, y_lamp, keep=lambda i, j, x, z, k=k, sx=sx: kind((sx[j] + sx[j + 1]) / 2, z) == k,
                          xfn=xfn)
            if k == "bezel":
                face = set(bm.verts)
                rim(bm, 0.06, 0.002)
                # the outer end's wall would lie on the wing skin (z-fighting): angle it inwards under the wing
                for v in bm.verts:
                    if v not in face and abs(v.co.x) > 0.66:
                        dy = max(0.0, v.co.y - (Y_WING - 0.004))
                        v.co.x -= np.sign(v.co.x) * 1.2 * dy
            else:
                # glass sits 1.5 mm behind the bezel face: drop its verts back
                for v in bm.verts:
                    v.co.y += 0.0015
            orient(bm)
            out.setdefault(k, []).append(bm)
    # reflector bowls behind the head lamp glass (chrome), 35 mm deep, one per side
    refl = bmesh.new()
    for side in (1, -1):
        xs2 = lin(UNIT_X[1], UNIT_X[2], 16); zs2 = lin(UNIT_Z[1], UNIT_Z[2], 10)
        cx, cz = (UNIT_X[1] + UNIT_X[2]) / 2, (UNIT_Z[1] + UNIT_Z[2]) / 2
        hx, hz = (UNIT_X[2] - UNIT_X[1]) / 2, (UNIT_Z[2] - UNIT_Z[1]) / 2

        def yb(x, z, side=side):
            u = (abs(x) - cx) / hx; w = (z - cz) / hz
            return y_lamp(x, z) + 0.006 + 0.03 * max(0.0, 1 - max(u * u, w * w)) ** 0.5
        sx = [side * x for x in xs2]
        patch(refl, sx if side > 0 else sx[::-1], zs2, yb)
    orient(refl)
    return out, refl


def merge(bms):
    bm = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_tmp"); b.to_mesh(me); b.free()
        bm.from_mesh(me); bpy.data.meshes.remove(me)
    return bm


def remove_old():
    """REF_BODY faces in front of / just behind the new parts; DET_LAMP_IND front faces. The wing's front end is cut
    straight first (plane y = Y_WING) so it meets the indicator's outer edge on a clean line."""
    import prep_reference as pr
    yc = Y_WING - 0.002
    pr.bisect_planes([((0, yc, 0), (0, 1, 0), (0.64, 0.78, yc - 0.06, yc + 0.06, 0.527, 0.70)),
                      ((0, yc, 0), (0, 1, 0), (-0.78, -0.64, yc - 0.06, yc + 0.06, 0.527, 0.70))], grow=0.005)
    o = bpy.data.objects["REF_BODY"]; me = o.data
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    x, y, z = C.T
    cand = np.where((np.abs(x) < 0.78) & (z > 0.527) & (z < 0.700) & (y < -1.55))[0]
    dead = []
    for i in cand:
        ax = abs(x[i])
        if ax > 0.64 and y[i] < yc:
            dead.append(i); continue
        if ax < FR_OUT[0][1] + R:
            ys = y_frame(x[i], z[i])
        else:
            if z[i] > UNIT_Z[3] + 0.003 or ax > x_end(z[i]) + 0.004:
                continue
            ys = y_lamp(x[i], z[i])
        if y[i] < ys + 0.035:
            dead.append(i)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in dead], context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    gone = {"body": len(dead)}
    for nm in ("DET_LAMP_IND_L", "DET_LAMP_IND_R"):
        lo = bpy.data.objects[nm]
        bm = bmesh.new(); bm.from_mesh(lo.data)
        fr = [f for f in bm.faces if f.calc_center_median().y < -1.45]
        bmesh.ops.delete(bm, geom=fr, context="FACES")
        bm.to_mesh(lo.data); bm.free(); lo.data.update()
        gone[nm] = len(fr)
    return gone


def add_to(name, bm):
    """Append a bmesh to an existing lamp object (keeps its name / custom props for lights.ini, ext_config)."""
    lo = bpy.data.objects[name]
    old = bmesh.new(); old.from_mesh(lo.data)
    me = bpy.data.meshes.new("_tmp"); bm.to_mesh(me); bm.free()
    old.from_mesh(me); bpy.data.meshes.remove(me)
    old.to_mesh(lo.data); old.free()
    lo.data.polygons.foreach_set("use_smooth", [True] * len(lo.data.polygons))


def main():
    out = {"removed": remove_old()}
    fr = frame(); groove_fix(fr)
    gr = insert()
    lamps, refl = lamp_units()
    # head lamp glass -> DET_LAMP_HEAD (new object, same name; lights.ini)
    keep_props = dict(bpy.data.objects["DET_LAMP_HEAD"].items()) if bpy.data.objects.get("DET_LAMP_HEAD") else {}
    head = to_object("DET_LAMP_HEAD", merge(lamps["head"]), ["lamp_clear"])
    for k, v in keep_props.items():
        head[k] = v
    to_object("DET_LAMP_UNIT", merge(lamps["bezel"]), ["trim_black"])
    to_object("DET_LAMP_REFL", refl, ["chrome"])
    left, right = lamps["ind"]
    add_to("DET_LAMP_IND_L", left)
    add_to("DET_LAMP_IND_R", right)
    # badge onto the slats
    b = bpy.data.objects.get("DET_BADGE_F")
    if b:
        ys = [b.matrix_world @ v.co for v in b.data.vertices]
        back = max(v.y for v in ys)
        b.location.y += (y_frame(0, 0.586) + SLAT_D - 0.0005) - back
    out.update({o: len(bpy.data.objects[o].data.polygons) for o in
                ("DET_GRILLE_FRAME", "DET_GRILLE", "DET_LAMP_HEAD", "DET_LAMP_UNIT", "DET_LAMP_REFL")})
    return out


if __name__ == "__main__":
    print("==", main())
