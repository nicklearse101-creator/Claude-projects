"""Phase 11 - procedural Nova GTE: panel seams and shut lines (Nik's Phase 11 spec, 2026-10-20).

Targets the body components (3D pieces of the Side_Profile_* templates: Hood, Side_Profile_Door_Left, Chassis_Front /
Chassis_Rear, Tailgate) plus the front wing and rear quarter they meet (Fender_Front_Left, Quarter_Rear_Left):
 1. Component edges: the perimeter boundary edges of each object that lie on another body object's boundary
    (the seams where the independent objects meet - door to wing / quarter / roof, bonnet to wing / scuttle, hatch to
    quarter / roof). Centre line (x = 0), wheel arches, window openings and the light cavities are not seams.
 2. Shut lines: Blender's bevel needs an edge between two faces, so every seam edge first gets a short flange turned
    inward (FLANGE, along the inward surface normal); the seam edge then sits between the panel face and the flange
    and bpy.ops.mesh.bevel(offset=0.003, segments=2) rolls it inward - each panel edge drops away 3 mm before the
    seam, so two neighbouring panels leave a dark 6 mm shut line.
 3. Hood lip: the bonnet's leading edge (headlamp_top row) and the top edge of the grille / headlamp openings below
    it are pushed forward by LIP_FWD, the opening edge also flared down by LIP_DROP - the bonnet front sits proud of
    the grille line and hangs over the cavities as a metal lip.
 4. All edits run on the full (both sides) mesh, so the seams crossing the centre line (bonnet rear edge, hatch top)
    are one continuous bevel; then cut back to x >= 0 + Mirror modifier (X, clipping, merge).
    Hygiene: remove_doubles(0.0001) + normals_make_consistent(inside=False). Audit raises NovaSpecError.
Phases 4-10 are re-run first (phase10_light_housings.main).
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase11_panel_seams.py   (saves)"""
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
from mathutils.kdtree import KDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_front_block as p4          # noqa: E402
import phase10_light_housings as p10     # noqa: E402

NovaSpecError = p4.NovaSpecError
BEVEL_W = 0.003             # bevel width (m)
BEVEL_SEG = 2
FLANGE = 0.006              # inward flange the bevel rolls into
LIP_FWD = 0.004             # bonnet leading edge proud of the grille line
LIP_DROP = 0.003            # lip hangs down over the openings
SEAM_TOL = 0.004            # boundary edge counts as a seam if it lies on another object's boundary
PANELS = ("Hood", "Chassis_Front", "Chassis_Rear", "Tailgate", "Side_Profile_Door_Left", "Fender_Front_Left",
          "Quarter_Rear_Left")


def boundary_samples(bm, step=0.0005):
    """Points along the boundary edges (off the centre line), at most `step` m apart."""
    pts = []
    for e in bm.edges:
        if not e.is_boundary or all(abs(v.co.x) < 1e-6 for v in e.verts):
            continue
        a, b = e.verts[0].co, e.verts[1].co
        n = max(1, math.ceil((b - a).length / step))
        pts += [a.lerp(b, i / n) for i in range(n + 1)]
    return pts


def kd(points):
    t = KDTree(max(1, len(points)))
    for i, p in enumerate(points):
        t.insert(p, i)
    t.balance()
    return t


def seam_edges(bm, others):
    """Boundary edges of bm whose ends and middle lie on another panel's boundary (both sides of the car)."""
    out = {}
    for e in bm.edges:
        if not e.is_boundary or all(abs(v.co.x) < 1e-6 for v in e.verts):
            continue
        a, b = e.verts[0].co, e.verts[1].co
        # each point on SOME neighbour's boundary (a junction edge runs from one neighbour to the next);
        # the neighbour named is the one under the middle of the edge
        near = [min((t.find(p)[2], name) for name, t in others.items()) for p in (a, b, (a + b) / 2)]
        if all(d < SEAM_TOL for d, _ in near):
            out[e] = near[2][1]
    return out


def dist_point_segment(p, a, b):
    ab = b - a
    t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def merge_slivers(bm, seams):
    """Interior panel vertices closer than 1.5 x the bevel width to a seam vertex (sliver rows left by earlier cuts)
    are merged into that seam vertex, so the bevel has the full width of panel to roll into. Returns the count."""
    se = set(seams)
    sv = {v for e in seams for v in e.verts}
    n = 0
    for v in list(sv):
        if not v.is_valid:
            continue
        for e in list(v.link_edges):
            if not v.is_valid:
                break
            if not e.is_valid:
                continue
            o = e.other_vert(v)
            if o in sv or any(x.is_boundary for x in o.link_edges):
                continue
            # perpendicular distance of o from the seam edges at v (a row running alongside the seam is a sliver)
            dmin = min([dist_point_segment(o.co, x.verts[0].co, x.verts[1].co) for x in v.link_edges if x in se]
                       or [9.0])
            if dmin >= 1.5 * BEVEL_W:
                continue
            bmesh.ops.pointmerge(bm, verts=[v, o], merge_co=v.co.copy())
            n += 1
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges[:])
    return n


def hood_lip(ob, zf1, orig_tree):
    """Bonnet leading edge (headlamp_top row) and the opening top edge below it: forward LIP_FWD, edge down LIP_DROP."""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bnd = {v.index for v in bm.verts if v.co.x > 1e-6 and
           any(e.is_boundary and not all(abs(w.co.x) < 1e-6 for w in e.verts) for e in v.link_edges)}     # seam welds stay put
    bm.free()
    row_y = min(v.co.y for v in me.vertices if abs(v.co.z - zf1) < 1e-4)
    top = [v for v in me.vertices if abs(v.co.z - zf1) < 1e-4 and abs(v.co.y - row_y) < 1e-4 and v.index not in bnd]
    edge = [v for v in me.vertices if v.index not in bnd and v.co.y < -1.70 and zf1 - 0.015 < v.co.z < zf1 - 0.005
            and orig_tree.find_nearest(v.co)[3] < 1e-5]
    for v in top:
        v.co.y -= LIP_FWD
    for v in edge:
        v.co.y -= LIP_FWD
        v.co.z -= LIP_DROP
    me.update()
    return len(top), len(edge)


def shut_lines(ob, seams):
    """Edit mode on the full mesh: flange the seam edges inward, then bpy.ops.mesh.bevel the seam edges."""
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    ob.modifiers["Mirror_X"].show_viewport = False
    ob.data.use_mirror_x = False
    with p10.ops_ctx():
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action="DESELECT")
        bm = bmesh.from_edit_mesh(ob.data)
        bm.normal_update()
        keys = {(tuple(round(c, 6) for c in a), tuple(round(c, 6) for c in b)) for a, b in seams}
        sel = [e for e in bm.edges if e.is_boundary and
               ((tuple(round(c, 6) for c in e.verts[0].co), tuple(round(c, 6) for c in e.verts[1].co)) in keys or
                (tuple(round(c, 6) for c in e.verts[1].co), tuple(round(c, 6) for c in e.verts[0].co)) in keys)]
        vn = {v: v.normal.copy() for e in sel for v in e.verts}
        r = bmesh.ops.extrude_edge_only(bm, edges=sel)
        new_v = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
        # each new vertex sits on its source vertex: move it inward along that vertex's surface normal
        src = {v: min(vn, key=lambda s: (s.co - v.co).length) for v in new_v}
        for v in new_v:
            d = -vn[src[v]] * FLANGE
            if abs(v.co.x) < 1e-6:
                d.x = 0.0
            v.co += d
        bm.normal_update()                                      # flange faces were created flat: refresh normals
        for e in sel:
            e.select_set(True)
        bmesh.update_edit_mesh(ob.data)
        n_sel = len(sel)
        nv0 = len(bm.verts)
        bpy.ops.mesh.bevel(offset_type="OFFSET", offset=BEVEL_W, segments=BEVEL_SEG, profile=0.5,
                           affect="EDGES", clamp_overlap=False, loop_slide=True)
        bm = bmesh.from_edit_mesh(ob.data)
        n_new = len(bm.verts) - nv0
        bpy.ops.object.mode_set(mode="OBJECT")
    return n_sel, n_new


def surface_agreement(ob, tree):
    """Area-weighted agreement of the face normals with the outward reference surface (faces on that surface)."""
    me = ob.data
    agree = 0.0
    for p in me.polygons:
        hit = tree.find_nearest(p.center)
        if hit[0] is not None and hit[3] < 1e-4:
            agree += p.normal.dot(hit[1]) * p.area
    return agree


def orient_outward(ob, tree):
    """normals_make_consistent picks a side by itself on an open shell with inward flanges (it turned the door
    inside out): keep the panel's outward side - flip the whole mesh if it disagrees with the reference surface."""
    if surface_agreement(ob, tree) < 0:
        ob.data.flip_normals()
        ob.data.update()


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        p10.main()
    if "RESULT: PASS" not in buf.getvalue():
        raise NovaSpecError("phase 10 rebuild did not pass")
    O = bpy.data.objects
    zf1 = p10.rows("Side_Profile_Hood")["headlamp_top"][1]
    orig = {}
    for n in PANELS:
        bm0 = bmesh.new(); bm0.from_mesh(O[n].data)
        orig[n] = BVHTree.FromBMesh(bm0); bm0.free()
    # ---- 3. hood lip (on the half mesh, before the seams)
    lip = hood_lip(O["Hood"], zf1, orig["Hood"])
    for n in PANELS:                                            # the lip moved bonnet vertices: refresh the reference
        bm0 = bmesh.new(); bm0.from_mesh(O[n].data)
        orig[n] = BVHTree.FromBMesh(bm0); bm0.free()
    # ---- 1. seams, found on the full (both sides) meshes
    full = {n: p10.full_mesh(O[n]) for n in PANELS}
    trees = {n: kd(boundary_samples(bm)) for n, bm in full.items()}
    seams = {n: seam_edges(full[n], {m: t for m, t in trees.items() if m != n}) for n in PANELS}
    slivers = {n: merge_slivers(full[n], seams[n]) for n in PANELS}
    for n in PANELS:                                            # reference surface = the prepared panel
        orig[n] = BVHTree.FromBMesh(full[n])
    seams = {n: seam_edges(full[n], {m: t for m, t in trees.items() if m != n}) for n in PANELS}
    seam_pts = {}
    pairs = {}
    ends = {}
    for n in PANELS:            # chain ends: seam vertices that also touch an open edge which is not a seam
        se = set(seams[n])
        ends[n] = {tuple(round(c, 6) for c in v.co) for e in se for v in e.verts
                   if any(x.is_boundary and x not in se and not all(abs(w.co.x) < 1e-6 for w in x.verts)
                          for x in v.link_edges)}
        for v in {v for e in se for v in e.verts}:                  # corners / junctions: the bevel mitres there
            ve = [x for x in v.link_edges if x in se]
            if len(ve) != 2:
                ends[n].add(tuple(round(c, 6) for c in v.co))
                continue
            d0 = (ve[0].other_vert(v).co - v.co).normalized(); d1 = (ve[1].other_vert(v).co - v.co).normalized()
            if d0.dot(d1) > math.cos(math.radians(135)):            # seam turns by more than 45 deg
                ends[n].add(tuple(round(c, 6) for c in v.co))
    for n in PANELS:
        seam_pts[n] = [((e.verts[0].co + e.verts[1].co) / 2, e.verts[0].co.copy(), e.verts[1].co.copy(), m)
                       for e, m in seams[n].items()]
        for e, m in seams[n].items():
            if e.verts[0].co.x >= 0 and e.verts[1].co.x >= 0:
                pairs[(n, m)] = pairs.get((n, m), 0.0) + e.calc_length()
    for n in PANELS:
        full[n].to_mesh(O[n].data); full[n].free(); O[n].data.update()
    # ---- 2. flange + bevel per object
    stats = {}
    for n in PANELS:
        segs = [(a, b) for _, a, b, _ in seam_pts[n]]
        stats[n] = shut_lines(O[n], segs) if segs else (0, 0)
    # ---- 4. back to the half mesh + mirror, hygiene
    for n in PANELS:
        p10.restore_half(O[n])
        orient_outward(O[n], orig[n])
    stats["slivers"] = slivers
    audit(O, orig, seam_pts, pairs, stats, lip, ends)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


def audit(O, orig, seam_pts, pairs, stats, lip, ends):
    rows, bad = [], []

    def check(label, meas, spec, tol=0.001, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-68s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    dg = bpy.context.evaluated_depsgraph_get()
    rows.append("    seams found (left half, m):")
    for (a, b), L in sorted(pairs.items()):
        rows.append("      %-24s | %-24s %7.3f" % (a, b, L))
    for n in ("Hood", "Side_Profile_Door_Left", "Chassis_Front", "Chassis_Rear", "Tailgate"):
        check("%s: seam edges selected and beveled (both sides)" % n, float(stats[n][0] > 0), 1.0)
    for n in PANELS:
        rows.append("    %-24s bevel: %3d seam edges, %4d new vertices; %d sliver vertices merged into the seam"
                    % (n, *stats[n], stats["slivers"][n]))
    # surface faces = faces still on the panel's original surface; the seam line is now BEVEL_W away from them
    gap = {}
    for n in PANELS:
        if not seam_pts[n]:
            continue
        bm = bmesh.new(); bm.from_mesh(O[n].data); bm.normal_update()
        surf = [f for f in bm.faces if all(orig[n].find_nearest(v.co)[3] < 1e-5 for v in f.verts)]
        # set-back line = edges between a surface face and a bevel face (open edges such as windows excluded)
        sset = set(surf)
        outline = [(e.verts[0].co.copy(), e.verts[1].co.copy()) for e in bm.edges
                   if sum(1 for f in e.link_faces if f in sset) == 1 and len(e.link_faces) == 2]
        ok = kd([a.lerp(b, i / max(1, math.ceil((b - a).length / 0.0002))) for a, b in outline
                 for i in range(max(1, math.ceil((b - a).length / 0.0002)) + 1)])

        class _T:
            @staticmethod
            def find_nearest(q):
                return (None, None, None, ok.find(q)[2])
        t = _T
        # measured at the seam vertices (the bevel offset is defined there; long seam edges are chords of curved,
        # non-planar panel faces, so a chord midpoint is not a fair sample)
        d = []
        pts = {}
        for mid, a, b, m in seam_pts[n]:
            for q in (a, b):
                if q.x >= 0:
                    pts[tuple(round(c, 6) for c in q)] = (q, m)
        n_end = 0
        for key in list(pts):
            if key in ends[n]:              # the shut line runs out into an open edge here: tapers, not measured
                del pts[key]; n_end += 1
        rows.append("    %s: %d seam vertices measured; %d chain ends / corners (seam meets an open edge, turns > 45 deg "
                    "or three panels meet: the bevel tapers or mitres there) listed apart" % (n, len(pts), n_end))
        for q, m in pts.values():
            d.append(t.find_nearest(q)[3])
            gap.setdefault(tuple(sorted((n, m))), []).append(d[-1])
        d = np.array(d)
        low = sorted((t.find_nearest(q)[3], tuple(round(c, 3) for c in q), m) for q, m in pts.values()
                     if t.find_nearest(q)[3] < BEVEL_W - 0.001)
        if low:
            rows.append("    %s seam points closer than width - 1 mm: %s" % (n, low[:6]))
        check("%s: panel edge set back from the seam = bevel width (median)" % n, float(np.median(d)), BEVEL_W)
        check("%s: ... nowhere less than the width - 1 mm (min)" % n, float(d.min()), BEVEL_W - 0.001, cmp="ge")
        # rolled inward: every vertex off the original surface is behind it (inside the body)
        behind = 0
        for v in bm.verts:
            hit = orig[n].find_nearest(v.co)
            if hit[3] > 1e-5 and (v.co - hit[0]).dot(hit[1]) > 5e-4:     # 0.5 mm (non-planar quads triangulate differently)
                behind += 1
                rows.append("    %s vertex outside the surface at %s by %.5f m" % (n, tuple(round(c, 4) for c in v.co),
                                                                            (v.co - hit[0]).dot(hit[1])))
        check("%s: bevel / flange vertices outside the panel surface" % n, float(behind), 0.0)
        bm.free()
    for k, v in sorted(gap.items()):
        rows.append("    shut line %-24s / %-24s mean gap %.4f m (2 x %.3f)" % (k[0], k[1], 2 * float(np.mean(v)), BEVEL_W))
    check("hood lip: bonnet leading edge row moved forward (vertices)", float(lip[0] > 0), 1.0)
    check("hood lip: opening top edge flared forward + down (vertices)", float(lip[1] > 0), 1.0)
    for n in PANELS:
        ob = O[n]; me = ob.data
        X = np.array([v.co.x for v in me.vertices])
        seam = [v for v in me.vertices if abs(v.co.x) < 1e-5]
        check("%s: no vertex right of the centre line (min x >= 0)" % n, float(X.min()), 0.0, cmp="ge")
        check("%s: centre-seam vertices exactly x = 0" % n, float(max([abs(v.co.x) for v in seam] or [0.0])), 0.0, tol=1e-12)
        m = ob.modifiers.get("Mirror_X")
        check("%s: mirror X + clipping + merge" % n, float(bool(m) and m.use_axis[0] and m.use_clip and m.use_mirror_merge), 1.0)
        ev = ob.evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored verts = 2 x half - seam (clean at x = 0)" % n, float(len(ev.vertices)),
              float(2 * len(me.vertices) - len(seam)))
        check("%s: mirrored symmetric (max x + min x)" % n, float(EX.max() + EX.min()), 0.0, tol=1e-6)
        ob.evaluated_get(dg).to_mesh_clear()
        bm = bmesh.new(); bm.from_mesh(me)
        check("%s: degenerate faces / zero edges" % n, float(sum(1 for f in bm.faces if f.calc_area() < 1e-10)
                                                          + sum(1 for e in bm.edges if e.calc_length() < 1e-6)), 0.0)
        check("%s: edges with > 2 faces" % n, float(sum(1 for e in bm.edges if len(e.link_faces) > 2)), 0.0)
        bm.free()
        check("%s: normals outward (agree with the outward panel surface)" % n,
              float(surface_agreement(ob, orig[n]) > 0), 1.0)
    print("NOVA GTE PHASE 11 - PANEL SEAMS AND SHUT LINES VERIFICATION")
    print("%-68s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
