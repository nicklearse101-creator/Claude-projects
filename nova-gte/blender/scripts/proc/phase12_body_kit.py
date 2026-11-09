"""Phase 12 - procedural Nova GTE: wrap-around GTE bumpers and side skirts (Nik's Phase 12 spec, 2026-10-20).

Separate objects wrapped over the lower body, built from duplicated body faces (the 3D pieces of the Side_Profile_*
templates and the wing / quarter they wrap onto). The faces are copied from the welded body BEFORE the Phase 11 shut-line
bevels, so each piece is one continuous skin; the panels then get their seams as in Phase 11.
 1. Bumper_Front_GTE: nose faces below the headlight housings (Hood below the front_bumper_top row + the front wing
    ahead of the front arch, so it wraps round to the arch). Shell extruded outward along the vertex normals by THICK
    (plastic cover over the metal); bottom edge extended straight down by VALANCE (deep GTE valance, closed underneath);
    two rectangular fog-light recesses cut into the lower corners (position from Nik's grey front picture) and
    recessed by FOG_DEPTH.
 2. Bumper_Rear_GTE: rear faces below the taillight housings (Tailgate below the rear_bumper_top row + the rear quarter
    behind the rear arch, below the same height), shell extruded outward by THICK; its front end runs along the rear
    arch lip (boxes round the arch edge).
 3. Side_Skirt_Left: the sill band (body bottom up to SKIRT_H) between the arches - front wing behind the front arch,
    door / sill, rear quarter ahead of the rear arch; shell extruded outward by THICK, bottom edge pulled down by DROP.
 4. Bumpers built on the full (both sides) mesh, cut back to x >= 0; all three get the Mirror modifier (X, clipping,
    merge); hygiene remove_doubles(0.0001) + normals_make_consistent(inside=False), outward side kept.
A vertex attribute "part" tags the shell: 0 inner edge (on the metal), 1 outer skin, 2 valance / drop, 3 bottom lip,
4 fog recess. Audit raises NovaSpecError on any failure.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase12_body_kit.py   (saves)"""
import contextlib
import io
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_front_block as p4          # noqa: E402
import phase5_rear_block as p5           # noqa: E402
import phase10_light_housings as p10     # noqa: E402
import phase11_panel_seams as p11        # noqa: E402

NovaSpecError = p4.NovaSpecError
THICK = 0.025               # plastic cover over the metal (outward along the normals)
VALANCE = 0.05              # front valance: bottom edge extended straight down
SKIRT_H = 0.10              # side skirt band height above the body bottom
DROP = 0.02                 # side skirt bottom pulled down
FOG_X = (0.422, 0.514)      # fog-light recess |x| (grey front picture u 73.8..90, 172 px/m about centre u 164.4)
FOG_Z = (0.260, 0.352)      # fog-light recess z   (v 178.8..195 on the bumper face, FRONT_CAM h 0.62)
FOG_DEPTH = THICK - 0.003   # recess back to 3 mm in front of the metal
WELD = 0.001               # copies from neighbouring panels welded within this
KIT = ("Bumper_Front_GTE", "Bumper_Rear_GTE", "Side_Skirt_Left")


def kinds(ob):
    a = ob.data.attributes.get("kind")
    return [d.value for d in a.data] if a else [0] * len(ob.data.vertices)


def lip_curve(ob, ahead_of_axle, axle_y):
    """The arch lip's front (ahead_of_axle) or rear half as y(z); below its lowest point the lowest y is kept."""
    pts = sorted((v.co.z, v.co.y) for v, k in zip(ob.data.vertices, kinds(ob))
                 if k == 1 and ((v.co.y < axle_y) == ahead_of_axle))
    zs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return lambda z: float(np.interp(z, zs, ys))


def capture(ob, test, z_cut=None):
    """Copies of the faces of `ob` passing test(centre, normal, vertex kinds) as (coords, normal, kinds) polygons.
    z_cut: bisect the mesh at that height first (clean top edge for a band)."""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.normal_update()
    kl = bm.verts.layers.int.get("kind")
    if z_cut is not None:
        bmesh.ops.bisect_plane(bm, geom=list(bm.faces) + list(bm.edges) + list(bm.verts), plane_co=(0, 0, z_cut),
                               plane_no=(0, 0, 1), dist=1e-6)
        bm.normal_update()
    out = []
    for f in bm.faces:
        k = [v[kl] if kl else 0 for v in f.verts]
        if test(f.calc_center_median(), f.normal, k):
            out.append(([v.co.copy() for v in f.verts], f.normal.copy(), k))
    bm.free()
    return out


def weld_tjunctions(bm):
    """Where two panels' copies meet, a vertex of one may lie on the middle of the other's open edge: split that edge
    there, so remove_doubles joins the copies into one skin."""
    n = 0
    for _ in range(3):
        changed = False
        bverts = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
        bedges = [e for e in bm.edges if e.is_boundary]
        for v in bverts:
            for e in bedges:
                if not e.is_valid or v in e.verts:
                    continue
                a, b = e.verts[0].co, e.verts[1].co
                ab = b - a
                if ab.length < 1e-6:
                    continue
                t = (v.co - a).dot(ab) / ab.length_squared
                if 0.001 < t < 0.999 and (v.co - (a + ab * t)).length < WELD:
                    ne, nv = bmesh.utils.edge_split(e, e.verts[0], t)
                    nv.co = v.co.copy()
                    n += 1; changed = True
                    break
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
        if not changed:
            break
    return n


def islands(bm):
    seen, out = set(), []
    for f in bm.faces:
        if f in seen:
            continue
        st, comp = [f], []
        seen.add(f)
        while st:
            g = st.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen:
                        seen.add(h); st.append(h)
        out.append(comp)
    return out


def zip_corner(bm):
    """The fascia copy (nose / tail, the island on the centre line) and the wing / quarter copy do not touch at the
    corner (the wing's end sits inboard of the fascia's side edge): bridge the fascia's side edge (its outermost
    boundary verts) to the wing's end edge (its boundary verts nearest the fascia) with a strip of triangles,
    walking both edges bottom to top."""
    isl = islands(bm)
    if len(isl) < 2:
        return 0
    def bverts(comp):
        return {v for f in comp for v in f.verts if any(e.is_boundary for e in v.link_edges)}
    fascia_i = min(range(len(isl)), key=lambda i: min(v.co.x for f in isl[i] for v in f.verts))
    fascia = bverts(isl[fascia_i])
    wing = set().union(*[bverts(c) for i, c in enumerate(isl) if i != fascia_i])
    ymean = sum(v.co.y for v in fascia) / len(fascia)
    allv = [v for f in isl[fascia_i] for v in f.verts]
    A = sorted([v for v in fascia if v.co.x > 1e-6 and                 # outermost vertex of each row (side edge)
                not any(abs(w.co.z - v.co.z) < 1e-3 and w.co.x > v.co.x + 1e-4 for w in allv)],
               key=lambda v: v.co.z)
    if ymean < 0:
        ye = min(v.co.y for v in wing); B = [v for v in wing if v.co.y < ye + 0.002]
    else:
        ye = max(v.co.y for v in wing); B = [v for v in wing if v.co.y > ye - 0.002]
    B.sort(key=lambda v: v.co.z)
    i = j = 0; n = 0
    while i < len(A) - 1 or j < len(B) - 1:
        if j == len(B) - 1 or (i < len(A) - 1 and A[i + 1].co.z <= B[j + 1].co.z):
            tri = (A[i], A[i + 1], B[j]); i += 1
        else:
            tri = (A[i], B[j + 1], B[j]); j += 1
        try:
            bm.faces.new(tri); n += 1
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return n


def build_bm(polys, mirror, zip_nose=False):
    bm = bmesh.new()
    kl = bm.verts.layers.int.new("kind")
    for co, n, k in polys:
        vs = []
        for c, kk in zip(co, k):
            v = bm.verts.new(c); v[kl] = kk; vs.append(v)
        f = bm.faces.new(vs)
        f.normal_update()
        if f.normal.dot(n) < 0:
            f.normal_flip()
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)      # weld the copies from neighbouring panels
    weld_tjunctions(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
    if zip_nose:
        ref0 = [(f.calc_center_median(), f.normal.copy()) for f in bm.faces]
        build_bm.zipped = zip_corner(bm)
        bm.normal_update()
        t0 = BVHTree.FromBMesh(bm)
        if sum(t0.find_nearest(c)[1].dot(n) for c, n in ref0 if t0.find_nearest(c)[0] is not None) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    for v in bm.verts:
        if abs(v.co.x) < 1e-6:
            v.co.x = 0.0
    if mirror:
        ref = {f.calc_center_median().freeze(): f.normal.copy() for f in bm.faces}
        bmesh.ops.mirror(bm, geom=list(bm.faces) + list(bm.edges) + list(bm.verts), axis="X", merge_dist=1e-5)
        for f in bm.faces:                                          # mirrored copies come out reversed: re-orient
            f.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.normal_update()
        if sum(f.normal.dot(ref[c]) for f in bm.faces for c in [f.calc_center_median().freeze()] if c in ref) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()
    return bm


def shell(bm, thick):
    """Extrude the skin outward along the vertex normals by `thick` (even thickness), drop the inner copy.
    Returns (outer faces, walls, inner boundary verts)."""
    pl = bm.verts.layers.int.get("part") or bm.verts.layers.int.new("part")
    orig_f = set(bm.faces); orig_v = set(bm.verts)
    bm.normal_update()
    vn = {}
    for v in orig_v:
        # offset d with n_i . d = thick for every face plane round the vertex (least squares; at most 3 x thick)
        ns = []
        for f in v.link_faces:
            if all(abs(f.normal.dot(m)) < 0.9998 for m in ns):
                ns.append(f.normal.copy())
        if not ns:
            vn[v] = v.normal * thick
            continue
        N = np.array([tuple(m) for m in ns])
        d = np.linalg.lstsq(N, np.full(len(ns), thick), rcond=None)[0]
        d = Vector(d)
        if d.length > 1.6 * thick:              # near-parallel / sliver faces blow the solution up: plain normal
            m = min([v.normal.dot(f.normal) for f in v.link_faces] or [1.0])
            d = v.normal * (thick / max(0.5, m))
        vn[v] = d
    skin = BVHTree.FromBMesh(bm)                                    # the copied body surface
    r = bmesh.ops.extrude_face_region(bm, geom=list(orig_f))
    new_v = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
    # each new vertex was copied from an original one at the same place
    from mathutils.kdtree import KDTree
    kd = KDTree(len(orig_v)); ol = list(orig_v)
    for i, v in enumerate(ol):
        kd.insert(v.co, i)
    kd.balance()
    for v in new_v:
        src = ol[kd.find(v.co)[1]]
        v.co += vn[src]
        v[pl] = 1
    for _ in range(3):                      # nowhere thinner than `thick` (corners where a non-adjacent face is nearer)
        for v in new_v:
            loc, _n, _i, d = skin.find_nearest(v.co)
            if loc is not None and d < thick - 1e-5:
                v.co = loc + (v.co - loc).normalized() * thick
    for v in orig_v:
        v[pl] = 0
    bmesh.ops.delete(bm, geom=list(orig_f), context="FACES_ONLY")
    new_set = set(new_v)
    outer = [f for f in bm.faces if all(v in new_set for v in f.verts)]
    walls = [f for f in bm.faces if f not in outer]
    bm.normal_update()
    return outer, walls


def extend_down(bm, walls, depth, src_bottom):
    """Bottom edge of the outer skin extended straight down by `depth` and closed back to the metal with a lip.
    src_bottom: test(edge between two inner verts) -> True for the skin's bottom edge."""
    pl = bm.verts.layers.int["part"]
    bottom_walls = [f for f in walls if f.is_valid and
                    any(src_bottom(e) for e in f.edges if all(v[pl] == 0 for v in e.verts))]
    inner_bottom = {v for f in bottom_walls for v in f.verts if v[pl] == 0}
    outer_edges = [e for f in bottom_walls for e in f.edges if all(v[pl] == 1 for v in e.verts)]
    # keep the inner bottom verts used by other walls (ends), drop the bottom walls
    bmesh.ops.delete(bm, geom=bottom_walls, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context="EDGES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context="VERTS")
    outer_edges = [e for e in outer_edges if e.is_valid]
    bm.normal_update()
    hn = {}
    for v in {v for e in outer_edges for v in e.verts}:
        n = Vector((v.normal.x, v.normal.y, 0.0))
        hn[v] = n.normalized() if n.length > 1e-6 else Vector((0, 0, 0))
    r = bmesh.ops.extrude_edge_only(bm, edges=outer_edges)
    down = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
    src = {}
    for v in down:
        s = min(hn, key=lambda o: (o.co - v.co).length)
        src[v] = s
        v.co.z -= depth
        v[pl] = 2
    down_edges = [g for g in r["geom"] if isinstance(g, bmesh.types.BMEdge) and all(v in src for v in g.verts)]
    r2 = bmesh.ops.extrude_edge_only(bm, edges=down_edges)
    lip = [g for g in r2["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in lip:
        s = min(src, key=lambda o: (o.co - v.co).length)
        v.co -= hn[src[s]] * THICK
        v[pl] = 3
    # end caps: where the extension meets an end wall, close the notch (outer top, outer bottom, lip, wall bottom)
    caps = 0
    for v in down:
        if sum(1 for e in v.link_edges if all(w in src for w in e.verts)) != 1:
            continue                                                # not an end of the extended edge
        top = src[v]
        l = [e.other_vert(v) for e in v.link_edges if e.other_vert(v)[pl] == 3]
        w = [x for x in inner_bottom if x.is_valid and any(e.other_vert(x) is top for e in x.link_edges)]
        if l and w:
            try:
                bm.faces.new((top, v, l[0], w[0]))
                caps += 1
            except ValueError:
                pass
    bm.normal_update()
    return len(outer_edges), caps


def cut_back(bm):
    p10.half_back(bm)


def to_object(bm, name, coll, ref_tree):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = (0, 0, 0)
    ob["nova_kit"] = 1
    p10.add_mirror(ob)
    p4.clean_mesh(ob)
    outward(ob, ref_tree)
    return ob


def outward(ob, ref_tree):
    """Outer skin faces must face the same way as the body surface under them."""
    me = ob.data
    part = [d.value for d in me.attributes["part"].data]
    agree = 0.0
    for p in me.polygons:
        if all(part[i] == 1 for i in p.vertices):
            hit = ref_tree.find_nearest(p.center)
            if hit[0] is not None:
                agree += p.normal.dot(hit[1]) * p.area
    if agree < 0:
        me.flip_normals(); me.update()
    return agree


def tree(polys, mirror, zip_nose=False):
    bm = build_bm(polys, mirror, zip_nose)
    t = BVHTree.FromBMesh(bm); bm.free()
    return t


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        p10.main()
    if "RESULT: PASS" not in buf.getvalue():
        raise NovaSpecError("phase 10 rebuild did not pass")
    O = bpy.data.objects
    coll = bpy.data.collections["NOVA_PROC"]
    zf0 = p10.rows("Side_Profile_Hood")["front_bumper_top"][1]
    zr0 = p10.rows("Side_Profile_Tailgate")["rear_bumper_top"][1]
    lip = {}
    for n in ("Fender_Front_Left", "Quarter_Rear_Left"):
        k = kinds(O[n])
        ys = [v.co.y for v, kk in zip(O[n].data.vertices, k) if kk == 1]
        lip[n] = (min(ys), max(ys))
    yf, yr = O["Axle_Front"].location.y, O["Axle_Rear"].location.y
    f_front, f_rear = lip_curve(O["Fender_Front_Left"], True, yf), lip_curve(O["Fender_Front_Left"], False, yf)
    q_front, q_rear = lip_curve(O["Quarter_Rear_Left"], True, yr), lip_curve(O["Quarter_Rear_Left"], False, yr)
    z_bottom = min(v.co.z for n in ("Fender_Front_Left", "Side_Profile_Door_Left", "Quarter_Rear_Left")
                   for v in O[n].data.vertices)
    skirt_top = z_bottom + SKIRT_H
    no_well = lambda k: 2 not in k
    # the wing / quarter close off with a wall tucked inside the nose / tail fascia corner (behind the bumper rows,
    # inboard of the fascia edge): not part of the visible skin
    D = p4.dims()
    H, T = p10.rows("Side_Profile_Hood"), p10.rows("Side_Profile_Tailgate")
    y_nose = max(H[r][0] for r in ("front_bumper_top", "front_bumper_upper_edge", "front_bumper_face",
                                   "front_bumper_lower_edge"))
    y_tail = min(T[r][0] for r in ("rear_bumper_top", "rear_bumper_upper_edge", "rear_bumper_face",
                                   "rear_bumper_lower_edge"))
    tz = sorted((T[r][1], p5.HALF_W[r]) for r in
                ("rear_bumper_top", "rear_bumper_upper_edge", "rear_bumper_face", "rear_bumper_lower_edge"))
    tail_hw = lambda z: float(np.interp(z, [a for a, _ in tz], [b for _, b in tz]))
    in_nose = lambda c: c.y <= y_nose + 1e-4 and c.x < p4.wing_half_width(D, c.y, c.z) - 0.003
    in_tail = lambda c: c.y >= y_tail - 1e-4 and c.x < tail_hw(c.z) + 0.003
    # ---- 1-3. duplicate the faces (welded body, before the shut-line bevels)
    front = (capture(O["Hood"], lambda c, n, k: c.z < zf0) +
             capture(O["Fender_Front_Left"], lambda c, n, k: c.z < zf0 and c.y < f_front(c.z)
                     and no_well(k) and n.x > -0.2 and not in_nose(c), z_cut=zf0))
    rear = (capture(O["Tailgate"], lambda c, n, k: c.z < zr0) +
            capture(O["Quarter_Rear_Left"], lambda c, n, k: c.z < zr0 and c.y > q_rear(c.z)
                    and no_well(k) and n.x > -0.2 and not in_tail(c), z_cut=zr0))
    side = (capture(O["Fender_Front_Left"], lambda c, n, k: c.z < skirt_top and c.y > f_rear(c.z)
                    and no_well(k) and n.x > 0.3, z_cut=skirt_top) +
            capture(O["Side_Profile_Door_Left"], lambda c, n, k: c.z < skirt_top and n.x > 0.3, z_cut=skirt_top) +
            capture(O["Quarter_Rear_Left"], lambda c, n, k: c.z < skirt_top and c.y < q_front(c.z)
                    and no_well(k) and n.x > 0.3, z_cut=skirt_top))
    for nm, p in (("front", front), ("rear", rear), ("side", side)):
        if not p:
            raise NovaSpecError("no faces captured for the %s piece" % nm)
    refs = {"Bumper_Front_GTE": tree(front, True, True), "Bumper_Rear_GTE": tree(rear, True, True),
            "Side_Skirt_Left": tree(side, False)}
    src_min = {"Bumper_Front_GTE": min(c.z for co, _, _ in front for c in co),
               "Bumper_Rear_GTE": min(c.z for co, _, _ in rear for c in co),
               "Side_Skirt_Left": min(c.z for co, _, _ in side for c in co)}
    # ---- the panels get their shut lines (Phase 11) - the kit copies above are independent of it
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        p11.main()
    if "RESULT: PASS" not in buf.getvalue():
        raise NovaSpecError("phase 11 rebuild did not pass")
    info = {"src_min": src_min, "skirt_top": skirt_top, "lip": lip, "zr0": zr0}

    def is_bottom(bm):
        kl = bm.verts.layers.int["kind"]

        def test(e):
            a, b = e.verts
            if a[kl] == 1 or b[kl] == 1:                            # arch lip edges are not the bottom
                return False
            d = b.co - a.co
            if abs(d.z) > 0.5 * d.length:
                return False
            fs = [f for f in e.link_faces]
            mid = (a.co + b.co) / 2
            return any(f.calc_center_median().z > mid.z + 0.002 for f in fs)
        return test
    # ---- front bumper + valance + fog recesses
    bm = build_bm(front, True, zip_nose=True)
    info["nose_zip"] = build_bm.zipped
    bottom_test = is_bottom(bm)
    bottom_edges = {e for e in bm.edges if e.is_boundary and bottom_test(e)}
    outer, walls = shell(bm, THICK)
    pl = bm.verts.layers.int["part"]
    keyset = {tuple(sorted((tuple(round(c, 6) for c in e.verts[0].co), tuple(round(c, 6) for c in e.verts[1].co))))
              for e in bottom_edges if e.is_valid}
    keyed = lambda e: tuple(sorted((tuple(round(c, 6) for c in e.verts[0].co),
                                    tuple(round(c, 6) for c in e.verts[1].co)))) in keyset
    info["front_valance"] = extend_down(bm, walls, VALANCE, keyed)
    face_front = lambda f: f.normal.y < -0.7 and all(v[pl] == 1 for v in f.verts)
    for x in FOG_X:
        for s in (1, -1):
            p10.bisect(bm, [f for f in bm.faces if face_front(f)], (s * x, 0, 0), (1, 0, 0))
    for z in FOG_Z:
        p10.bisect(bm, [f for f in bm.faces if face_front(f)], (0, 0, z), (0, 0, 1))
    bm.normal_update()
    fog = [f for f in bm.faces if face_front(f) and FOG_X[0] < abs(f.calc_center_median().x) < FOG_X[1]
           and FOG_Z[0] < f.calc_center_median().z < FOG_Z[1]]
    r = bmesh.ops.extrude_face_region(bm, geom=fog)
    for v in [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]:
        v.co.y += FOG_DEPTH
        v[pl] = 4
    bmesh.ops.delete(bm, geom=fog, context="FACES_ONLY")
    info["fog_faces"] = len(fog)
    cut_back(bm)
    bf = to_object(bm, "Bumper_Front_GTE", coll, refs["Bumper_Front_GTE"])
    # ---- rear bumper (shell only, front end on the rear arch lip)
    bm = build_bm(rear, True, zip_nose=True)
    info["tail_zip"] = build_bm.zipped
    shell(bm, THICK)
    cut_back(bm)
    br = to_object(bm, "Bumper_Rear_GTE", coll, refs["Bumper_Rear_GTE"])
    # ---- side skirt: shell, bottom pulled down
    bm = build_bm(side, False)
    bottom_test = is_bottom(bm)
    bottom_edges = {e for e in bm.edges if e.is_boundary and bottom_test(e)}
    keyset = {tuple(sorted((tuple(round(c, 6) for c in e.verts[0].co), tuple(round(c, 6) for c in e.verts[1].co))))
              for e in bottom_edges}
    outer, walls = shell(bm, THICK)
    info["skirt_drop"] = extend_down(bm, walls, DROP, keyed)
    sk = to_object(bm, "Side_Skirt_Left", coll, refs["Side_Skirt_Left"])
    audit({"Bumper_Front_GTE": bf, "Bumper_Rear_GTE": br, "Side_Skirt_Left": sk}, refs, info)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


def audit(objs, refs, info):
    rows, bad = [], []

    def check(label, meas, spec, tol=0.001, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-66s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    D = p4.dims()
    dg = bpy.context.evaluated_depsgraph_get()
    for n, ob in objs.items():
        me = ob.data
        part = np.array([d.value for d in me.attributes["part"].data])
        V = np.array([tuple(v.co) for v in me.vertices])
        rows.append("    %-18s %5d verts %5d faces  x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" % (
            n, len(V), len(me.polygons), V[:, 0].min(), V[:, 0].max(), V[:, 1].min(), V[:, 1].max(),
            V[:, 2].min(), V[:, 2].max()))
        # outer skin = THICK off the body surface
        d = np.array([refs[n].find_nearest(Vector(p))[3] for p in V[part == 1]])
        check("%s: outer skin off the body surface = thickness (median)" % n, float(np.median(d)), THICK)
        check("%s: ... nowhere closer than thickness - 1 mm (min)" % n, float(d.min()), THICK - 0.001, cmp="ge")
        thin = [(round(float(dd), 4), tuple(np.round(p, 3))) for dd, p in zip(d, V[part == 1]) if dd < THICK - 0.001]
        if thin:
            rows.append("    %s thin skin at: %s" % (n, thin[:6]))
        d0 = np.array([refs[n].find_nearest(Vector(p))[3] for p in V[part == 0]])
        check("%s: inner edge sits on the body (max gap)" % n, float(d0.max()), 0.0)
        m = ob.modifiers.get("Mirror_X")
        check("%s: mirror X + clipping + merge" % n, float(bool(m) and m.use_axis[0] and m.use_clip and m.use_mirror_merge), 1.0)
        seam = [v for v in me.vertices if abs(v.co.x) < 1e-5]
        check("%s: no vertex right of the centre line (min x >= 0)" % n, float(V[:, 0].min()), 0.0, cmp="ge")
        check("%s: centre-seam vertices exactly x = 0" % n, float(max([abs(v.co.x) for v in seam] or [0.0])), 0.0, tol=1e-12)
        ev = ob.evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored verts = 2 x half - seam (clean at x = 0)" % n, float(len(ev.vertices)),
              float(2 * len(me.vertices) - len(seam)))
        check("%s: mirrored symmetric (max x + min x)" % n, float(EX.max() + EX.min()), 0.0, tol=1e-6)
        ob.evaluated_get(dg).to_mesh_clear()
        bm = bmesh.new(); bm.from_mesh(me)
        check("%s: degenerate faces / zero edges" % n, float(sum(1 for f in bm.faces if f.calc_area() < 1e-9)
                                                          + sum(1 for e in bm.edges if e.calc_length() < 1e-6)), 0.0)
        check("%s: edges with > 2 faces" % n, float(sum(1 for e in bm.edges if len(e.link_faces) > 2)), 0.0)
        bm.free()
        check("%s: outer skin normals outward" % n, float(outward(ob, refs[n]) > 0), 1.0)
    bf = objs["Bumper_Front_GTE"].data
    part = np.array([d.value for d in bf.attributes["part"].data])
    V = np.array([tuple(v.co) for v in bf.vertices])
    check("front valance: bottom = outer skin bottom - valance depth", float(V[:, 2].min()),
          float(V[part == 1][:, 2].min()) - VALANCE)
    rows.append("    front valance: %d bottom edges extended, %d end caps; nose corner bridged with %d faces"
                % (*info["front_valance"], info["nose_zip"]))
    F = V[part == 4]
    check("front fog recesses: faces cut (both sides)", float(info["fog_faces"] > 0), 1.0)
    check("front fog recess: x range = picture (min |x|)", float(F[:, 0].min()), FOG_X[0])
    check("front fog recess: x range = picture (max |x|)", float(F[:, 0].max()), FOG_X[1])
    check("front fog recess: z range = picture (min z)", float(F[:, 2].min()), FOG_Z[0])
    check("front fog recess: z range = picture (max z)", float(F[:, 2].max()), FOG_Z[1])
    sk = objs["Side_Skirt_Left"].data
    SV = np.array([tuple(v.co) for v in sk.vertices])
    spart = np.array([d.value for d in sk.attributes["part"].data])
    check("side skirt: bottom = outer skin bottom - drop", float(SV[:, 2].min()), float(SV[spart == 1][:, 2].min()) - DROP)
    rows.append("    side skirt: %d bottom edges pulled down, %d end caps; band top z %.3f; y %.3f .. %.3f" % (
        *info["skirt_drop"], info["skirt_top"], SV[:, 1].min(), SV[:, 1].max()))
    lf, lr = info["lip"]["Fender_Front_Left"], info["lip"]["Quarter_Rear_Left"]
    check("side skirt runs between the arches (front end >= front arch rear)", float(SV[:, 1].min()), lf[1] - THICK, cmp="ge")
    check("side skirt runs between the arches (rear end <= rear arch front)", float(SV[:, 1].max()), lr[0] + THICK, cmp="le")
    rows.append("    rear bumper: tail corner bridged with %d faces" % info["tail_zip"])
    br = objs["Bumper_Rear_GTE"].data
    RV = np.array([tuple(v.co) for v in br.vertices])
    q = bpy.data.objects["Quarter_Rear_Left"]
    lipv = [Vector(v.co) for v, k in zip(q.data.vertices, kinds(q)) if k == 1 and v.co.z < info["zr0"] - 0.03
            and v.co.y > bpy.data.objects["Axle_Rear"].location.y]
    bp = [v.co for v in br.vertices]
    dl = max(min((l - b).length for b in bp) for l in lipv) if lipv else 9.0
    check("rear bumper boxes the arch: every arch-lip point below it is on the bumper (max gap)", float(dl), 0.0)
    # overall size with the kit (informational vs the master dimensions)
    allx = max(float(SV[:, 0].max()), float(RV[:, 0].max()), float(V[:, 0].max()))
    L = float(RV[:, 1].max() - V[:, 1].min())
    rows.append("    with the kit: overall length %.3f m (master %.3f), max width %.3f m (master %.3f)" % (
        L, D["length"], 2 * allx, D["width"]))
    print("NOVA GTE PHASE 12 - GTE BUMPERS AND SIDE SKIRTS VERIFICATION")
    print("new objects: " + ", ".join(objs))
    print("%-66s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
