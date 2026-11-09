"""Phase 8 - procedural Nova GTE: windows carved out of the cabin, glass separated.

Targets the 3D cabin objects (the Side_Profile_* templates are 2D outlines): Chassis_Front (windscreen strip),
the greenhouse patch of Side_Profile_Door_Left (side glass) and the glass slope of Tailgate (rear screen).
- Window openings traced on Nik's grey pictures (tools/proc/trace_windows.py -> data/proc/windows.json; Nik
  2026-10-20: "the rear windows are not right" - the first version took the bright part of the glass, but behind
  it the far side's pillars / interior show through, so the opening is the outer edge of the black window rubber):
  the cabin mesh is cut along those edges (bisect planes), the faces inside an opening form the window zone.
  Door opening split by the quarter-light divider bar (vent pane + door pane, both in Glass_Side_Door_Left);
  quarter window = trapezoid with its rear edge parallel to the C-pillar; rear screen = trapezoid on the tailgate
  slope (narrower at the top, bottom 8 cm above the crease); windscreen = the whole Chassis_Front strip.
- Each zone is inset (frame width FRAME[...]) - the ring stays on the body (window lip / pillar) - and the inner
  faces are pushed RECESS inward (side glass along -X, windscreen / rear screen along their inward normal).
- The recessed inner faces move into Glass_Windshield, Glass_Side_Door_Left, Glass_Side_Quarter_Left, Glass_Rear
  (moved, not copied: a copy left in the body would sit on the glass and z-fight).
- Windscreen / rear screen meet the centre line: the half panel is mirrored, inset as one region (no frame along
  the centre line) and cut back to x >= 0, so the mirrored glass fuses at x = 0 (Mirror modifier with clipping).
Phases 4, 5, 6 and 7 are re-run first so the script can be run again on a clean cabin.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase8_windows.py   (saves)"""
import contextlib
import io
import json
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_front_block as p4      # noqa: E402
import phase5_rear_block as p5       # noqa: E402
import phase6_arches as p6           # noqa: E402
import phase7_bridge as p7           # noqa: E402

NovaSpecError = p4.NovaSpecError
RECESS = 0.015
FRAME = {"windshield": 0.035, "door": 0.018, "vent": 0.010, "quarter": 0.022, "rear": 0.030}   # black rubbers
WIN = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                   "data", "proc", "windows.json")
GLASS = ("Glass_Windshield", "Glass_Side_Door_Left", "Glass_Side_Quarter_Left", "Glass_Rear")


def rebuild_cabin():
    """Re-run phases 4-7 quietly so the window carving always starts from the clean bridged cabin."""
    for n in GLASS:
        ob = bpy.data.objects.get(n)
        if ob:
            bpy.data.objects.remove(ob)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        for mod in (p4, p5, p6, p7):
            mod.main()


def clean(ob):
    p4.clean_mesh(ob)


def inset_recess(bm, faces, frame, push):
    """Inset the face region (ring stays), push the inner faces by the vector `push`; returns the inner faces."""
    res = bmesh.ops.inset_region(bm, faces=faces, thickness=frame, depth=0.0, use_even_offset=True,
                                 use_boundary=True, use_interpolate=True)
    inner = [f for f in faces if f.is_valid]
    vs = {v for f in inner for v in f.verts}
    for v in vs:
        v.co += push
    return inner


def extrude_recess(bm, faces, push):
    """Recess a face region: extrude it (side walls join it to the frame around it), move the extruded faces by
    `push`, drop the originals. Returns the recessed faces."""
    r = bmesh.ops.extrude_face_region(bm, geom=list(faces))
    new = [g for g in r["geom"] if isinstance(g, bmesh.types.BMFace)]
    for v in {v for f in new for v in f.verts}:
        v.co += push
    bmesh.ops.delete(bm, geom=list(faces), context="FACES_ONLY")
    return new


def take_faces(bm_src, faces, name, mats_from, coll, mirror=True):
    """Move faces out of bm_src into a new object."""
    bm = bmesh.new()
    vmap = {}
    for f in faces:
        vs = []
        for v in f.verts:
            if v not in vmap:
                vmap[v] = bm.verts.new(v.co)
            vs.append(vmap[v])
        bm.faces.new(vs)
    bmesh.ops.delete(bm_src, geom=list(faces), context="FACES_ONLY")
    bmesh.ops.delete(bm_src, geom=[v for v in bm_src.verts if not v.link_faces], context="VERTS")
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = (0, 0, 0)
    ob["nova_glass"] = 1
    if mirror:
        m = ob.modifiers.new("Mirror_X", "MIRROR")
        m.use_axis = (True, False, False); m.use_clip = True; m.use_mirror_merge = True; m.merge_threshold = 0.0001
    return ob


def write_back(ob, bm):
    bm.to_mesh(ob.data); bm.free(); ob.data.update()


def cut_polygon(bm, faces, poly, axes):
    """Bisect `faces` along every edge of a polygon given in two coordinates (axes, e.g. (1, 2) = y, z); the cut planes
    contain the third axis. Returns the faces of the cut region afterwards."""
    geom = set(faces) | {e for f in faces for e in f.edges} | {v for f in faces for v in f.verts}
    for (a0, b0), (a1, b1) in zip(poly, poly[1:] + poly[:1]):
        no = [0.0, 0.0, 0.0]; no[axes[0]] = -(b1 - b0); no[axes[1]] = a1 - a0
        co = [0.0, 0.0, 0.0]; co[axes[0]] = a0; co[axes[1]] = b0
        r = bmesh.ops.bisect_plane(bm, geom=[g for g in geom if g.is_valid], plane_co=co,
                                   plane_no=Vector(no).normalized(), dist=1e-6)
        geom = {g for g in geom if g.is_valid} | set(r["geom"])
    return [g for g in geom if isinstance(g, bmesh.types.BMFace) and g.is_valid]


def inside(poly, a, b):
    """Point (a, b) inside a polygon (even-odd)."""
    ins = False
    for (a0, b0), (a1, b1) in zip(poly, poly[1:] + poly[:1]):
        if (b0 > b) != (b1 > b) and a < a0 + (a1 - a0) * (b - b0) / (b1 - b0):
            ins = not ins
    return ins


def centre_line_panel(ob, zone_test, frame, glass_name, coll, cut=None):
    """Windscreen / rear screen: mirror the half panel, inset the whole zone as one region (no frame along the centre
    line), cut back to x >= 0. zone_test(centre, normal) on the left half; the mirror image is tested with |x|."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bm.normal_update()
    if cut is not None:
        cut(bm)
        bm.normal_update()
    zone = [f for f in bm.faces if zone_test(f.calc_center_median(), f.normal)]
    if not zone:
        raise NovaSpecError("%s: no faces in the window zone" % ob.name)
    n = sum((f.normal * f.calc_area() for f in zone), Vector()).normalized()     # outward
    bmesh.ops.mirror(bm, geom=list(bm.faces) + list(bm.edges) + list(bm.verts), axis="X", merge_dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    left = [f for f in bm.faces if f.calc_center_median().x > 0]
    if sum(f.normal.dot(n) for f in left if zone_test(f.calc_center_median(), f.normal) or True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.normal_update()
    def mirrored_ok(f):
        c, nn = f.calc_center_median(), f.normal
        return zone_test(Vector((abs(c.x), c.y, c.z)), Vector((nn.x if c.x >= 0 else -nn.x, nn.y, nn.z)))
    zone_all = [f for f in bm.faces if mirrored_ok(f)]
    if frame > 0:
        inset_recess(bm, zone_all, frame, -n * RECESS)
    else:                                   # zone = the glass itself (frame cut in already): recess only
        extrude_recess(bm, zone_all, -n * RECESS)
    bmesh.ops.bisect_plane(bm, geom=list(bm.faces) + list(bm.edges) + list(bm.verts), plane_co=(0, 0, 0),
                           plane_no=(1, 0, 0), clear_inner=True, dist=1e-6)
    for v in bm.verts:
        if abs(v.co.x) < 1e-5:
            v.co.x = 0.0
    bm.faces.ensure_lookup_table()
    glass = [f for f in bm.faces if all(v.co.x >= -1e-9 for v in f.verts) and
             abs((f.calc_center_median() - original_point(ob, f.calc_center_median())).length - RECESS) < 0.004]
    return bm, glass, n


_ORIG = {}


def original_point(ob, p):
    t = _ORIG.get(ob.name)
    loc = t.find_nearest(p)[0] if t else p
    return loc if loc is not None else p


def main():
    rebuild_cabin()
    D = p4.dims()
    coll = bpy.data.collections["NOVA_PROC"]
    O = bpy.data.objects
    dg = bpy.context.evaluated_depsgraph_get()
    for n in ("Chassis_Front", "Tailgate", "Side_Profile_Door_Left"):     # untouched surfaces for the audit
        bm0 = bmesh.new(); bm0.from_mesh(O[n].data)
        _ORIG[n] = BVHTree.FromBMesh(bm0); bm0.free()
    report = {}
    # ---- windscreen: all Chassis_Front faces
    cf = O["Chassis_Front"]
    bm, glass, n_ws = centre_line_panel(cf, lambda c, nn: True, FRAME["windshield"], "Glass_Windshield", coll)
    g = take_faces(bm, glass, "Glass_Windshield", cf, coll); write_back(cf, bm)
    report["Glass_Windshield"] = (g, n_ws, "centre")
    # ---- rear screen: traced opening (outer edge of the black rubber) and glass outline on the tailgate slope,
    # symmetrised (half-widths averaged); the band between them stays body (frame), the glass is recessed
    W = json.load(open(WIN))

    def trap(key):
        q = W["rear_xz"][key]
        return q[0][1], q[2][1], (abs(q[0][0]) + abs(q[1][0])) / 2, (abs(q[2][0]) + abs(q[3][0])) / 2
    tg = O["Tailgate"]
    zt = max(p[2] for p in p4.template_chain("Side_Profile_Tailgate")[0])
    zl = [p[2] for p in p4.template_chain("Side_Profile_Tailgate")[0] if p[0] == "tailgate_lower"][0]
    slope = lambda c, nn: zl + 1e-4 < c.z < zt and nn.z > 0.2 and nn.y > 0.2

    def tpoly(key):
        top_z, bot_z, top_hw, bot_hw = trap(key)
        return [(0.0, bot_z), (bot_hw, bot_z), (top_hw, top_z), (0.0, top_z)]

    def rear_cut(bm):
        for key in ("rear_opening", "rear_glass"):
            fs = [f for f in bm.faces if slope(f.calc_center_median(), f.normal)]
            top_z, bot_z, top_hw, bot_hw = trap(key)
            if key == "rear_opening":                # opening top = the tailgate top edge: only bottom + sides
                far = (top_hw + (top_hw - bot_hw) * 2, top_z + (top_z - bot_z) * 2)
                cut_polygon(bm, fs, [(0.0, bot_z), (bot_hw, bot_z), far, (0.0, far[1])], (0, 2))
            else:
                cut_polygon(bm, fs, tpoly(key), (0, 2))
    gpoly = tpoly("rear_glass")
    rear_test = lambda c, nn: slope(c, nn) and inside(gpoly, c.x, c.z)
    bm, glass, n_r = centre_line_panel(tg, rear_test, 0.0, "Glass_Rear", coll, cut=rear_cut)
    g = take_faces(bm, glass, "Glass_Rear", tg, coll); write_back(tg, bm)
    report["Glass_Rear"] = (g, n_r, "centre")
    # ---- side glass: traced openings (outer edge of the black rubber) and glass outlines, cut into the greenhouse
    # of the door object; band between them = frame (body), glass recessed along -X
    S = W["side_yz"]
    P_ = {k: [tuple(p) for p in S[k]] for k in ("door_opening", "door_glass", "quarter_opening", "quarter_glass")}
    bar0, bar1 = S["vent_bar"][0][0], S["vent_bar"][1][0]
    dr = O["Side_Profile_Door_Left"]
    bm = bmesh.new(); bm.from_mesh(dr.data); bm.normal_update()
    gh = [f for f in bm.faces if f.normal.x > 0.3 and f.calc_center_median().z > 0.80]
    for k in ("door_opening", "door_glass", "quarter_opening", "quarter_glass"):
        gh = cut_polygon(bm, gh, P_[k], (1, 2))
    gh = cut_polygon(bm, gh, [(bar0, 0.0), (bar0, 2.0), (bar1, 2.0), (bar1, 0.0)], (1, 2))
    bm.normal_update()
    cen = lambda f: f.calc_center_median()
    in_door = [f for f in gh if f.normal.x > 0.3 and inside(P_["door_glass"], cen(f).y, cen(f).z)]
    door_zone = [f for f in in_door if cen(f).y < bar0 or cen(f).y > bar1]          # vent pane + door pane
    quarter_zone = [f for f in gh if f.normal.x > 0.3 and inside(P_["quarter_glass"], cen(f).y, cen(f).z)]
    push = Vector((-RECESS, 0, 0))
    vent = [f for f in door_zone if cen(f).y < bar0]; main_ = [f for f in door_zone if cen(f).y > bar1]
    dz = extrude_recess(bm, vent, push) + extrude_recess(bm, [f for f in main_ if f.is_valid], push)
    qz = extrude_recess(bm, [f for f in quarter_zone if f.is_valid], push)
    g1 = take_faces(bm, [f for f in dz if f.is_valid], "Glass_Side_Door_Left", dr, coll)
    g2 = take_faces(bm, [f for f in qz if f.is_valid], "Glass_Side_Quarter_Left", dr, coll)
    write_back(dr, bm)
    report["Glass_Side_Door_Left"] = (g1, Vector((1, 0, 0)), "side")
    report["Glass_Side_Quarter_Left"] = (g2, Vector((1, 0, 0)), "side")
    for ob in [r[0] for r in report.values()] + [cf, tg, dr]:
        clean(ob)
    for name, (g, n, kind) in report.items():                # glass normals face out
        me = g.data
        if sum(p.normal.dot(n) * p.area for p in me.polygons) < 0:
            me.flip_normals()
        for v in me.vertices:
            if abs(v.co.x) < 1e-5:
                v.co.x = 0.0
    audit(D, report, {"Chassis_Front": cf, "Tailgate": tg, "Side_Profile_Door_Left": dr})
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


def audit(D, report, bodies):
    rows, bad = [], []

    def check(label, meas, spec, tol=0.001, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-62s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    dg = bpy.context.evaluated_depsgraph_get()
    src = {"Glass_Windshield": "Chassis_Front", "Glass_Rear": "Tailgate", "Glass_Side_Door_Left": "Side_Profile_Door_Left",
           "Glass_Side_Quarter_Left": "Side_Profile_Door_Left"}
    frame_of = {"Glass_Windshield": "windshield", "Glass_Rear": "rear", "Glass_Side_Door_Left": "door",
                "Glass_Side_Quarter_Left": "quarter"}
    for name, (g, n, kind) in report.items():
        me = g.data
        V = np.array([tuple(v.co) for v in me.vertices])
        area = sum(p.area for p in me.polygons)
        check("%s: faces" % name, float(len(me.polygons)), 1.0, cmp="ge")
        check("%s: glass area (m2)" % name, float(area), 0.05, cmp="ge")
        t = _ORIG[src[name]]
        dep = [t.find_nearest(Vector(p))[3] for p in V]
        check("%s: recess depth (median, m)" % name, float(np.median(dep)), RECESS, tol=0.003)
        nd = sum(p.normal.dot(n) * p.area for p in me.polygons) / max(area, 1e-9)
        check("%s: faces point out (area-weighted cos)" % name, float(nd), 0.5, cmp="ge")
        check("%s: degenerate faces" % name, float(sum(1 for p in me.polygons if p.area < 1e-9)), 0.0)
        m = g.modifiers.get("Mirror_X")
        check("%s: mirror X + clipping" % name, float(bool(m) and m.use_axis[0] and m.use_clip), 1.0)
        ev = g.evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored symmetric" % name, float(EX.max() + EX.min()), 0.0, tol=1e-6)
        g.evaluated_get(dg).to_mesh_clear()
        if kind == "centre":
            seam = int((np.abs(V[:, 0]) < 1e-9).sum())
            check("%s: centre-line vertices at x = 0 (fuses when mirrored)" % name, float(seam), 2.0, cmp="ge")
            check("%s: no vertex past the centre line" % name, float(V[:, 0].min()), 0.0, tol=1e-9)
        else:
            check("%s: clear of the centre line (min x)" % name, float(V[:, 0].min()), 0.3, cmp="ge")
        rows.append("    %s: %d verts, %d faces, area %.3f m2, frame %.3f m, x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f"
                    % (name, len(me.vertices), len(me.polygons), area, FRAME[frame_of[name]], V[:, 0].min(), V[:, 0].max(),
                       V[:, 1].min(), V[:, 1].max(), V[:, 2].min(), V[:, 2].max()))
    W = json.load(open(WIN))
    tr = {"Glass_Side_Door_Left": ("side_yz", "door_glass", 1), "Glass_Side_Quarter_Left": ("side_yz", "quarter_glass", 1),
          "Glass_Rear": ("rear_xz", "rear_glass", 0)}
    for gname, (grp, key, ax) in tr.items():
        T = np.array(W[grp][key]); G = np.array([tuple(v.co) for v in report[gname][0].data.vertices])
        if ax == 1:
            for lab, mv, tv in (("front y", G[:, 1].min(), T[:, 0].min()), ("rear y", G[:, 1].max(), T[:, 0].max()),
                                ("bottom z", G[:, 2].min(), T[:, 1].min()), ("top z", G[:, 2].max(), T[:, 1].max())):
                check("%s vs picture glass: %s" % (gname, lab), float(mv), float(tv), tol=0.006)
        else:                                    # glass moved back onto the body surface (undo the recess), symmetrised
            G = G + np.array(tuple(report[gname][1])) * RECESS
            hw = ((abs(T[1][0]) + abs(T[0][0])) / 2, (abs(T[2][0]) + abs(T[3][0])) / 2)
            for lab, mv, tv in (("max half-width", G[:, 0].max(), max(hw)),
                                ("bottom z", G[:, 2].min(), T[:, 1].min()), ("top z", G[:, 2].max(), T[:, 1].max())):
                check("%s vs picture glass: %s" % (gname, lab), float(mv), float(tv), tol=0.006)
    for gname in ("Glass_Side_Door_Left", "Glass_Side_Quarter_Left"):
        gz = max(v.co.z for v in report[gname][0].data.vertices)
        check("%s: roof rail above the glass (1.30 - glass top, m)" % gname, 1.30 - gz, 0.05, cmp="ge")
    for n, ob in bodies.items():
        me = ob.data
        check("%s (body): degenerate faces" % n, float(sum(1 for p in me.polygons if p.area < 1e-9)), 0.0)
        rows.append("    %s keeps its window frame: %d faces" % (n, len(me.polygons)))
    print("NOVA GTE PHASE 8 - WINDOWS & GLASS VERIFICATION")
    print("%-62s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    print("GLASS OBJECTS:", ", ".join(report))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
