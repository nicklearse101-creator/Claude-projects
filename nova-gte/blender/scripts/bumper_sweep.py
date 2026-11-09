"""Bumper rib bands rebuilt as clean new geometry (Nik 2026-10-19: ragged ribs / bend at the arch; the bought model's
bumper skin is too messy to clean in place). Per bumper: the outer surface is measured in plan-polar form r(theta, z)
(bumper_clean.measure) and fitted as R(theta) + P(z) - one plan outline and one cross-section (top lip, ribs, lower
face) all the way round, as on the real car. A new quad mesh DET_BUMPER_F/R is swept from that (paint with the
pinstripe UVs of prep_reference) and the old outer skin in the band is deleted. Rows stop at the wheel arch (the
photo-traced arch outline, body_geom.arch_poly) so the band ends on the arch edge."""
import math
import sys
import os

import bmesh
import numpy as np

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bumper_clean as bcl   # noqa: E402

DTH, DZ = 0.004, 0.002


def arch_y(key, z, side_end):
    """y of the arch edge at height z on the bumper side of the arch (front arch: its front edge; rear: rear edge).
    Front: the outline traced on Nik's side picture (wing_new.arch_pic), else the old body profile."""
    if key == "front":
        import wing_new
        a = wing_new.arch_pic()
        pts = a[a[:, 0] < -1.1715] if side_end == "front" else a[a[:, 0] > -1.1715]
        if z < pts[:, 1].min() - 0.002 or z > pts[:, 1].max():
            return None if z > pts[:, 1].max() else float(pts[np.argmin(pts[:, 1]), 0])
        o = np.argsort(pts[:, 1])
        return float(np.interp(z, pts[o, 1], pts[o, 0]))
    import body_geom as g
    return g.arch_edge_y(key, z, side_end)


# Front bumper cross-section from Nik's grey side picture (front silhouette, 2026-10-20) and the red Commons photo:
# the face is most forward between z 0.36 and 0.47 (ribs + the single red pinstripe in the top groove), the top rounds
# back ~45 mm by z 0.53, the lower part leans back ~40 mm by z 0.26 and the grey spoiler sits below it. Recess d(z) in
# metres behind the face line; grooves 3.6 mm wide, 2.5 mm deep at the old model's rib heights.
FRONT_Z0 = 0.255
FRONT_RECESS = ((0.255, 0.042), (0.270, 0.040), (0.290, 0.033), (0.310, 0.022), (0.330, 0.010), (0.345, 0.004),
                (0.365, 0.0), (0.470, 0.0), (0.480, 0.003), (0.490, 0.008), (0.500, 0.016), (0.510, 0.026),
                (0.520, 0.036), (0.530, 0.044), (0.540, 0.050))
FRONT_GROOVES = (0.418, 0.4325, 0.4525, 0.476)
SPOILER = ((0.183, 0.042), (0.186, 0.030), (0.190, 0.023), (0.200, 0.020), (0.235, 0.020), (0.243, 0.024),
           (0.248, 0.034), (0.252, 0.050))          # (z, recess) of the grey spoiler under the bumper


def _front_profile(z):
    zz, dd = zip(*FRONT_RECESS)
    d = float(np.interp(z, zz, dd))
    for zg in FRONT_GROOVES:
        u = (z - zg) / 0.0018
        if abs(u) < 1:
            d += 0.0025 * 0.5 * (1 + math.cos(math.pi * u))
    return -d


def _front_rows(z1):
    rows = set(np.round(np.arange(FRONT_Z0, z1 + 1e-9, 0.003), 5))
    for zg in FRONT_GROOVES:
        rows |= set(np.round(zg + np.array([-0.0027, -0.0018, -0.0009, 0, 0.0009, 0.0018, 0.0027]), 5))
    return np.array(sorted(r for r in rows if FRONT_Z0 <= r <= z1))


def _face_plan(zs, ths, Rm):
    """Plan outline of the face (z 0.37-0.43), robust even polynomial in theta fitted outside the old plate plinth
    (|theta| > 0.35) so the centre has no hump."""
    k = (zs >= 0.37) & (zs <= 0.43)
    Rf = np.nanmedian(Rm[k], axis=0)
    ok = np.isfinite(Rf) & (np.abs(ths) > 0.35)
    A = lambda t: np.stack([t ** (2 * i) for i in range(6)], 1)
    keep = ok.copy()
    for _ in range(4):
        c = np.linalg.lstsq(A(ths[keep]), Rf[keep], rcond=None)[0]
        r = A(ths) @ c - Rf
        keep = ok & (np.abs(r) < 2.5 * max(np.nanstd(r[keep]), 5e-4))
    return A(ths) @ c


def build(name):
    import prep_reference as pr
    cy, sg, z0, z1, th_max, mid = bcl.BUMPERS[name]
    key = "rear" if sg > 0 else "front"
    if key == "front":
        z0 = FRONT_Z0
    o = bpy.data.objects["REF_BODY"]; me = o.data
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    zs, ths, Rm = bcl.measure(bvh, cy, sg, z0, z1, th_max, dz=DZ, dth=DTH)
    R, P = bcl.fit(zs, ths, Rm, mid)
    zrow = zs[(zs >= z0) & (zs <= z1)]
    Pz = np.interp(zrow, zs, P)
    if key == "front":
        R = _face_plan(zs, ths, Rm)
        zrow = _front_rows(z1)
        Pz = np.array([_front_profile(z) for z in zrow])
        bpy.app.driver_namespace["front_bumper_plan"] = (ths, R, cy, sg, th_max)
    # per row: the theta where the side reaches the arch edge (both sides symmetric)
    pts = {}
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    for i, z in enumerate(zrow):
        ya = arch_y(key, z, "rear" if key == "rear" else "front")
        row = []
        for j, th in enumerate(ths):
            rr = R[j] + Pz[i]
            p = Vector((math.sin(th) * rr, cy + sg * math.cos(th) * rr, z))
            inside_arch = ya is not None and ((p.y < ya) if key == "rear" else (p.y > ya)) and abs(p.x) > 0.55
            row.append(None if inside_arch else bm.verts.new(p))
        grid.append(row)
    faces = 0
    for i in range(len(zrow) - 1):
        for j in range(len(ths) - 1):
            q = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
            if all(v is not None for v in q):
                f = bm.faces.new(q); f.smooth = True; faces += 1
                for lp, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                    zz = zrow[ii]; yy = lp.vert.co.y
                    zr = zz - (np.interp(yy, *pr.FRONT_RISE) if key == "front" else 0.0)
                    lp[uvl].uv = ((0.06 if key == "front" else 0.56) + 0.38 * (jj / (len(ths) - 1)),
                                  (zr - pr.STRIPE_Z0) / pr.STRIPE_H)
    if key == "front":
        # top ledge: the bumper's upper face runs back flat (rounded front edge) under the lamps / grille / wings
        top = grid[-1]; zt = float(zrow[-1])
        rings = []
        for dr, dz in ((0.0015, 0.0012), (0.004, 0.0025), (0.075, 0.0025)):
            ring = []
            for j, th in enumerate(ths):
                if top[j] is None:
                    ring.append(None); continue
                rr = R[j] + Pz[-1] - dr
                ring.append(bm.verts.new((math.sin(th) * rr, cy + sg * math.cos(th) * rr, zt + dz)))
            rings.append(ring)
        prev = top
        for ring in rings:
            for j in range(len(ths) - 1):
                q = (prev[j], prev[j + 1], ring[j + 1], ring[j])
                if all(v is not None for v in q):
                    f = bm.faces.new(q); f.smooth = True; faces += 1
                    for lp in f.loops:                        # same paint as the band's top row
                        zr = zt - np.interp(lp.vert.co.y, *pr.FRONT_RISE)
                        lp[uvl].uv = (0.06 + 0.38 * (j / (len(ths) - 1)), (zr - pr.STRIPE_Z0) / pr.STRIPE_H)
            prev = ring
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    for f in bm.faces:
        f.normal_update()
    f0 = max(bm.faces, key=lambda f: f.calc_area())
    outward = Vector((f0.calc_center_median().x, (f0.calc_center_median().y - cy), 0))
    if f0.normal.dot(outward) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    # ends at the wheel arches: roll the free edge in (toward the car's centre) so the end is closed
    import front_new as fn
    for sx in (1, -1):
        ends = [e for e in bm.edges if e.is_boundary and all(v.co.x * sx > 0.55 for v in e.verts)
                and all(abs(v.co.y) > 1.38 and abs(v.co.y) < 1.62 for v in e.verts)
                and all(z0 + 0.003 < v.co.z < z1 - 0.003 for v in e.verts)]
        if ends:
            new = fn.rim(bm, 0.03, 0.003, back=Vector((-sx, 0, 0)), steps=2, edges=ends,
                         dfn=lambda v: Vector((0, -sg, 0)))
            u0 = (0.06 if key == "front" else 0.56) + (0.38 if sx > 0 else 0.0)
            for f in new:                                  # stripes carry on round the end
                for lp in f.loops:
                    zr = lp.vert.co.z - (np.interp(lp.vert.co.y, *pr.FRONT_RISE) if key == "front" else 0.0)
                    lp[uvl].uv = (u0, (zr - pr.STRIPE_Z0) / pr.STRIPE_H)
    nm = "DET_BUMPER_" + ("R" if key == "rear" else "F")
    old = bpy.data.objects.get(nm)
    if old:
        bpy.data.objects.remove(old)
    mesh = bpy.data.meshes.new(nm); bm.to_mesh(mesh); bm.free()
    mesh.materials.append(bpy.data.materials["paint_stripes"])
    ob = bpy.data.objects.new(nm, mesh); bpy.data.collections["REF"].objects.link(ob)
    # cut the old skin along the band's top and bottom so its edge is straight, then delete the outer skin between
    yb = (1.20, 1.95) if key == "rear" else (-1.95, -1.25)
    pr.bisect_planes([((0, cy, z0), (0, 0, 1), (-0.9, 0.9, yb[0], yb[1], z0 - 0.01, z0 + 0.01)),
                      ((0, cy, z1), (0, 0, 1), (-0.9, 0.9, yb[0], yb[1], z1 - 0.01, z1 + 0.01))], grow=0.005)
    n = len(me.polygons)
    C = np.empty(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    rel = np.stack([C[:, 0], (C[:, 1] - cy) * sg], 1)
    r = np.linalg.norm(rel, axis=1); th = np.arctan2(rel[:, 0], rel[:, 1])
    band = (C[:, 2] > z0) & (C[:, 2] < z1) & (np.abs(th) < th_max) & ((C[:, 1] - cy) * sg > 0.2)
    idx = np.where(band)[0]
    prof = (lambda zz: np.array([_front_profile(v) for v in zz])) if key == "front" else (lambda zz: np.interp(zz, zs, P))
    tgt = np.interp(th[idx], ths, R) + prof(C[idx, 2])
    tol = 0.045 if key == "front" else 0.03
    dead = idx[(r[idx] > tgt - tol) & (r[idx] < tgt + tol)]
    if key == "front":                                   # old top ledge (now the new band's ledge)
        led = np.where((C[:, 2] > z1 - 0.002) & (C[:, 2] < z1 + 0.035) & (np.abs(th) < th_max)
                       & ((C[:, 1] - cy) * sg > 0.2))[0]
        tt = np.interp(th[led], ths, R) + prof(np.array([z1]))[0]
        dead = np.union1d(dead, led[(r[led] > tt - 0.09) & (r[led] < tt + 0.02)])
    # keep faces in the arch opening (the lip curl) - only those the new band covers
    ya_c = np.array([arch_y(key, zz, key) or (9 if key == "rear" else -9) for zz in C[dead, 2]])
    covered = ~(((C[dead, 1] < ya_c) if key == "rear" else (C[dead, 1] > ya_c)) & (np.abs(C[dead, 0]) > 0.55))
    dead = dead[covered]
    bmo = bmesh.new(); bmo.from_mesh(me); bmo.faces.ensure_lookup_table()
    bmesh.ops.delete(bmo, geom=[bmo.faces[int(i)] for i in dead], context="FACES")
    bmo.to_mesh(me); bmo.free(); me.update()
    return {"faces": faces, "old_faces_removed": int(len(dead))}


if __name__ == "__main__":
    print("==", {k: build(k) for k in ("rear", "front")})


def spoiler_front():
    """Grey front spoiler under the bumper (SPOILER profile on the bumper's face plan), ends at the arches with a rolled
    edge; the old lower lip is deleted."""
    import prep_reference as pr
    import front_new as fn
    ths, R, cy, sg, th_max = bpy.app.driver_namespace["front_bumper_plan"]
    zz = [z for z, _ in SPOILER]
    bm = bmesh.new()
    grid = []
    for z, d in SPOILER:
        ya = arch_y("front", max(z, 0.20), "front")
        row = []
        for th in ths:
            rr = np.interp(th, ths, R) - d
            p = Vector((math.sin(th) * rr, cy + sg * math.cos(th) * rr, z))
            row.append(None if (ya is not None and p.y > ya and abs(p.x) > 0.55) else bm.verts.new(p))
        grid.append(row)
    for i in range(len(grid) - 1):
        for j in range(len(ths) - 1):
            q = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
            if all(v is not None for v in q):
                f = bm.faces.new(q); f.smooth = True
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    for f in bm.faces:
        f.normal_update()
    f0 = max(bm.faces, key=lambda f: f.calc_area())
    if f0.normal.dot(Vector((f0.calc_center_median().x, f0.calc_center_median().y - cy, 0))) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    for sx in (1, -1):
        ends = [e for e in bm.edges if e.is_boundary and all(v.co.x * sx > 0.55 and abs(v.co.y) < 1.62 for v in e.verts)]
        if ends:
            fn.rim(bm, 0.03, 0.003, back=Vector((-sx, 0, 0)), steps=2, edges=ends, dfn=lambda v: Vector((0, 1, 0)))
    old = bpy.data.objects.get("DET_SPOILER_F")
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new("DET_SPOILER_F"); bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials["trim_grey"])
    ob = bpy.data.objects.new("DET_SPOILER_F", me); bpy.data.collections["REF"].objects.link(ob)
    # old lower lip / valance under the new band
    o = bpy.data.objects["REF_BODY"]; mo = o.data; n = len(mo.polygons)
    C = np.empty(n * 3); mo.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
    rel = np.stack([C[:, 0], (C[:, 1] - cy) * sg], 1); r = np.linalg.norm(rel, axis=1); th = np.arctan2(rel[:, 0], rel[:, 1])
    sel = np.where((C[:, 2] > 0.15) & (C[:, 2] < FRONT_Z0 + 0.003) & (np.abs(th) < th_max) & ((C[:, 1] - cy) * sg > 0.2))[0]
    tgt = np.interp(th[sel], ths, R)
    dead = sel[(r[sel] > tgt - 0.10) & (r[sel] < tgt + 0.03)]
    ya = np.array([arch_y("front", max(z, 0.20), "front") or -9 for z in C[dead, 2]])
    dead = dead[~((C[dead, 1] > ya) & (np.abs(C[dead, 0]) > 0.55))]
    pr.bisect_planes([((0, cy, 0.183), (0, 0, 1), (-0.9, 0.9, -1.95, -1.25, 0.17, 0.19))], grow=0.005)
    bmo = bmesh.new(); bmo.from_mesh(mo); bmo.faces.ensure_lookup_table()
    bmesh.ops.delete(bmo, geom=[bmo.faces[int(i)] for i in dead], context="FACES")
    bmo.to_mesh(mo); bmo.free(); mo.update()
    return {"faces": len(ob.data.polygons), "old_removed": int(len(dead))}


def tow_eye():
    """Black tow-eye cover on the front bumper (car's right, x -0.49..-0.39, z 0.30..0.37, shell map + front picture):
    a thin plate laid on the bumper face, 1.5 mm proud."""
    import bmesh as _bm
    o = bpy.data.objects["REF_BODY"]
    bvhs = [BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get()) for ob in (o, bpy.data.objects.get("DET_BUMPER_F")) if ob]
    bm = _bm.new()
    xs, zs = np.linspace(-0.49, -0.39, 11), np.linspace(0.30, 0.37, 8)
    grid = []
    for z in zs:
        row = []
        for x in xs:
            best = None
            for b in bvhs:
                h = b.ray_cast(Vector((x, -2.5, z)), Vector((0, 1, 0)), 2.0)
                if h[0] is not None and (best is None or h[0].y < best.y):
                    best = h[0]
            row.append(bm.verts.new((x, (best.y if best else -1.83) - 0.0015, z)))
        grid.append(row)
    for i in range(len(zs) - 1):
        for j in range(len(xs) - 1):
            f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
            f.normal_update()
            if f.normal.y > 0:
                f.normal_flip()
    old = bpy.data.objects.get("DET_TOWEYE")
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new("DET_TOWEYE"); bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials["trim_black"])
    ob = bpy.data.objects.new("DET_TOWEYE", me); bpy.data.collections["REF"].objects.link(ob)
    return len(me.polygons)
