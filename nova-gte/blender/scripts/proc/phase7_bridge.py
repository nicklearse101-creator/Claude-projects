"""Phase 7 - procedural Nova GTE: door / sill panel, greenhouse side and roof bridging the front and rear assemblies.

One new object, Side_Profile_Door_Left (left half, Mirror modifier X with clipping + merge), three welded patches:
  P1 door + sill: between the fender's trailing edge column (Fender_Front_Left at the front door shut line) and the
     quarter's leading edge column (Quarter_Rear_Left at the rear door shut line), sill up to the beltline; straight
     (slab-sided) blend between the two columns.
  P2 greenhouse side (pillars + side glass): Coons patch bounded by the beltline (P1 top + the quarter's top edge),
     the fender top + A-pillar (Chassis_Front outer edge), the roof edge, and the C-pillar / tailgate edge
     (Tailgate outer edge + Chassis_Rear outer edge).
  P3 roof: rows from the windscreen top (= Chassis_Front's top row) to the roof rear (= Chassis_Rear's front row),
     along the side-profile roof line (Side_Profile_Chassis), NCOL quads across to x = 0.
Edge columns / rows are read from the neighbouring objects by coordinates (never by index). The audit measures every
door boundary vertex against the neighbours (BVH distance) and lists any open edge that is not the underside.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase7_bridge.py   (saves)"""
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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FEAT = os.path.join(ROOT, "data", "proc", "side_features.json")
TOL = 0.001
DYC = 0.04                      # door column spacing
NT2 = 10                        # greenhouse rows
NovaSpecError = p4.NovaSpecError
NAME = "Side_Profile_Door_Left"


def world_verts(ob, kind_ok=None):
    me = ob.data
    kind = me.attributes.get("kind")
    out = []
    for i, v in enumerate(me.vertices):
        if kind is not None and kind_ok is not None and kind.data[i].value not in kind_ok:
            continue
        out.append(ob.matrix_world @ v.co)
    return out


def column(ob, y, kind_ok=(0, 1, 3)):
    """Vertices of a side panel at one y station (its edge column), sorted bottom -> top."""
    return sorted((p for p in world_verts(ob, kind_ok) if abs(p.y - y) < 1e-4), key=lambda p: p.z)


def row_outer(ob, rowname):
    """The vertices of one template row of a strip object (Chassis_Front / Chassis_Rear / Tailgate), outer -> centre."""
    me = ob.data
    layer = me.attributes["row"]
    pts = [ob.matrix_world @ me.vertices[i].co for i, d in enumerate(layer.data)
           if (d.value if isinstance(d.value, str) else d.value.decode()) == rowname]
    return sorted(pts, key=lambda p: -p.x)


def resample(pts, n):
    """n points along a polyline by arc length (endpoints kept)."""
    P = np.array([tuple(p) for p in pts])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, s[-1], n)
    return [Vector((np.interp(x, s, P[:, 0]), np.interp(x, s, P[:, 1]), np.interp(x, s, P[:, 2]))) for x in t]


def point_at_z(pts, z):
    """Point on a polyline (sorted by z) at height z."""
    for a, b in zip(pts[:-1], pts[1:]):
        if a.z <= z <= b.z and b.z > a.z:
            t = (z - a.z) / (b.z - a.z)
            return a.lerp(b, t)
    raise NovaSpecError("height %.3f outside the column" % z)


def build(D):
    O = bpy.data.objects
    feats = json.load(open(FEAT))
    y_df = float(np.mean(feats["features"]["door_front_y"]))
    y_dr = float(np.mean(feats["features"]["door_rear_y"]))
    z_belt = float(np.mean([p[1] for p in feats["features"]["beltline_rear"]]))
    fender, quarter = O["Fender_Front_Left"], O["Quarter_Rear_Left"]
    cf, cr, tg = O["Chassis_Front"], O["Chassis_Rear"], O["Tailgate"]

    # ---- P1 door + sill
    fcol_all = column(fender, round(y_df, 5))
    if not fcol_all:                               # stations were rounded to 5 decimals
        ys = sorted({round(p.y, 5) for p in world_verts(fender, (0, 1, 3))})
        y_df = max(ys); fcol_all = column(fender, y_df)
    qcol_all = column(quarter, min(round(p.y, 5) for p in world_verts(quarter, (0, 1, 3))))
    y_df, y_dr = fcol_all[0].y, qcol_all[0].y
    fcol = [p for p in fcol_all if p.z < z_belt - 1e-4] + [point_at_z(fcol_all, z_belt)]
    qcol = [p for p in qcol_all if p.z <= z_belt + 1e-4]
    if abs(qcol[-1].z - z_belt) > 2e-3:
        qcol.append(point_at_z(qcol_all, z_belt))
    nrow = len(fcol)
    qres = resample(qcol, nrow)
    ycols = list(np.linspace(y_df, y_dr, max(2, int(round((y_dr - y_df) / DYC))) + 1))
    P1 = []
    for k, y in enumerate(ycols):
        t = k / (len(ycols) - 1)
        P1.append([fcol[i].lerp(qres[i], t) for i in range(nrow)])
        for p in P1[-1]:
            p.y = y
    # ---- P2 greenhouse side
    qtop = sorted((max((p for p in world_verts(quarter, (0, 3)) if abs(p.y - y) < 1e-4), key=lambda p: p.z)
                   for y in sorted({round(p.y, 5) for p in world_verts(quarter, (0, 3))})), key=lambda p: p.y)
    qtop = [p for p in qtop if abs(p.z - z_belt) < 2e-3 and p.y > y_dr + 1e-4]
    bottom = [col[-1] for col in P1] + qtop
    a_pillar = [row_outer(cf, "windshield_base")[0], row_outer(cf, "windshield_top")[0]]
    front = [bottom[0]] + [p for p in fcol_all if p.z > z_belt + 1e-4] + a_pillar
    roof_pts = [(p[1], p[2]) for c in p4.template_chain("Side_Profile_Chassis") for p in c
                if p[0] in ("windshield_top", "roof_front", "roof_apex", "roof_rear")]
    roof_pts.sort()
    w0, w1 = a_pillar[1], row_outer(cr, "roof_rear")[0]
    top_line = []
    for y, z in roof_pts:
        t = (y - w0.y) / (w1.y - w0.y)
        top_line.append(Vector((w0.x + (w1.x - w0.x) * t, y, z)))
    tg_edge = [row_outer(tg, n)[0] for n in ("tailgate_lower", "tailgate_slope", "tailgate_top")]
    rear = [bottom[-1], point_at_z(sorted(tg_edge, key=lambda p: p.z), z_belt)] + \
           [p for p in sorted(tg_edge, key=lambda p: p.z) if p.z > z_belt] + [w1]
    ns = len(bottom)
    topr = resample(top_line, ns)
    frr, rrr = resample(front, NT2 + 1), resample(rear, NT2 + 1)
    # bottom keeps its exact vertices; s from its arc length
    B = bottom
    sB = np.r_[0, np.cumsum([(b - a).length for a, b in zip(B[:-1], B[1:])])]; sB /= sB[-1]
    Tl = resample(top_line, 400)
    sT = np.linspace(0, 1, 400)
    top_at = lambda s: Vector((np.interp(s, sT, [p.x for p in Tl]), np.interp(s, sT, [p.y for p in Tl]),
                               np.interp(s, sT, [p.z for p in Tl])))
    P2 = []
    for j in range(NT2 + 1):
        t = j / NT2
        row = []
        for i, s in enumerate(sB):
            b, r_ = B[i], top_at(s)
            f, g = frr[j], rrr[j]
            c00, c10, c01, c11 = B[0], B[-1], top_at(0.0), top_at(1.0)
            p = b * (1 - t) + r_ * t + f * (1 - s) + g * s - (c00 * (1 - s) * (1 - t) + c10 * s * (1 - t) + c01 * (1 - s) * t + c11 * s * t)
            row.append(p)
        P2.append(row)
    for i in range(ns):                     # exact boundaries
        P2[0][i] = B[i]
    for j in range(NT2 + 1):
        P2[j][0], P2[j][-1] = frr[j], rrr[j]
    # ---- P3 roof: rows at the greenhouse top row's points, across to x = 0
    roof_rows = sorted(P2[-1], key=lambda p: p.y)
    first, last = row_outer(cf, "windshield_top"), row_outer(cr, "roof_rear")
    P3 = []
    for k, p in enumerate(roof_rows):
        if k == 0:
            P3.append(first); continue
        if k == len(roof_rows) - 1:
            P3.append(last); continue
        P3.append([Vector((p.x * (1 - j / p4.NCOL), p.y, p.z)) for j in range(p4.NCOL + 1)])
    return {"P1": P1, "P2": P2, "P3": P3, "y_df": y_df, "y_dr": y_dr, "z_belt": z_belt, "neighbours":
            {"Fender_Front_Left": fcol_all, "Quarter_Rear_Left": qcol + qtop, "Chassis_Front": a_pillar + first,
             "Chassis_Rear": last, "Tailgate": tg_edge}}


def make_object(G, coll):
    old = bpy.data.objects.get(NAME)
    if old:
        bpy.data.objects.remove(old)
    bm = bmesh.new()
    tag = bm.verts.layers.int.new("patch")

    def grid(rows, pid, wrap_cols=False):
        vs = [[bm.verts.new(tuple(p)) for p in r] for r in rows]
        for r in vs:
            for v in r:
                v[tag] = pid
        for a, b in zip(vs[:-1], vs[1:]):
            for i in range(len(a) - 1):
                q = (a[i], a[i + 1], b[i + 1], b[i])
                if len({tuple(round(c, 6) for c in v.co) for v in q}) == 4:
                    bm.faces.new(q)
        return vs
    grid([list(c) for c in zip(*G["P1"])], 1)       # rows = heights, columns = y
    grid(G["P2"], 2)
    grid(G["P3"], 3)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0005)      # weld the patches
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=0.0001)
    me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(NAME, me); coll.objects.link(ob)
    ob.location = (0, 0, 0)
    p4.clean_mesh(ob)
    me.update()
    s = sum((p.normal.x if p.center.z < 1.2 else p.normal.z) * p.area for p in me.polygons)
    if s < 0:
        me.flip_normals()
    for v in me.vertices:
        if abs(v.co.x) < 1e-5:
            v.co.x = 0.0
    m = ob.modifiers.new("Mirror_X", "MIRROR")
    m.use_axis = (True, False, False); m.use_clip = True; m.use_mirror_merge = True; m.merge_threshold = 0.0001
    return ob


def audit(D, G, ob):
    rows, bad = [], []

    def check(label, meas, spec, tol=TOL, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-64s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bverts = {v for e in bm.edges if e.is_boundary for v in e.verts}
    trees = {n: BVHTree.FromObject(bpy.data.objects[n], dg) for n in
             ("Fender_Front_Left", "Quarter_Rear_Left", "Chassis_Front", "Chassis_Rear", "Tailgate", "Hood")}
    attached = {n: [] for n in trees}
    loose = []
    for v in bverts:
        best = min(((n, t.find_nearest(v.co)[3]) for n, t in trees.items()), key=lambda x: x[1])
        if best[1] <= TOL:
            attached[best[0]].append(best[1])
        else:
            loose.append((v.co.copy(), best))
    for n in ("Fender_Front_Left", "Quarter_Rear_Left", "Chassis_Front", "Chassis_Rear", "Tailgate"):
        d = attached[n]
        check("connected to %s: boundary verts within 1 mm" % n, float(len(d)), 2.0, cmp="ge")
        if d:
            rows.append("    %s: %d shared boundary verts, max gap %.3f mm" % (n, len(d), max(d) * 1000))
    # open edges that are not attached: allowed = the underside (sill bottom, z below 0.25) and the centre seam (x=0)
    open_ok = [p for p, _ in loose if p.z < 0.25 or abs(p.x) < 1e-6]
    open_bad = [(p, b) for p, b in loose if not (p.z < 0.25 or abs(p.x) < 1e-6)]
    rows.append("    unattached boundary verts: %d underside / centre seam, %d elsewhere" % (len(open_ok), len(open_bad)))
    for p, (n, dd) in open_bad[:8]:
        rows.append("      gap at (%.3f, %.3f, %.3f): %.1f mm to %s" % (p.x, p.y, p.z, dd * 1000, n))
    check("unattached boundary verts away from the underside / seam", float(len(open_bad)), 0.0, tol=4.5)
    bm.free()
    seam = [v for v in me.vertices if abs(v.co.x) < 1e-5]
    check("roof centre-seam vertices exactly x = 0 (max |x|)", float(max(abs(v.co.x) for v in seam)), 0.0, tol=1e-12)
    m = ob.modifiers.get("Mirror_X")
    check("mirror X + clipping + merge", float(bool(m) and m.use_axis[0] and m.use_clip and m.use_mirror_merge), 1.0)
    ev = ob.evaluated_get(dg).to_mesh()
    EX = np.array([v.co.x for v in ev.vertices])
    check("mirrored symmetric (max x + min x)", float(EX.max() + EX.min()), 0.0, tol=1e-6)
    check("mirrored verts = 2 x half - seam", float(len(ev.vertices)), float(2 * len(me.vertices) - len(seam)))
    ob.evaluated_get(dg).to_mesh_clear()
    check("degenerate faces", float(sum(1 for p in me.polygons if p.area < 1e-9)), 0.0)
    check("max width <= factory width / 2", float(max(v.co.x for v in me.vertices)), D["width"] / 2 + 1e-6, cmp="le")
    Z = [v.co.z for v in me.vertices]
    check("roof top = master height", float(max(Z)), D["height"])
    mid = G["P1"][len(G["P1"]) // 2]
    slab = max(p.x for p in mid) - min(p.x for p in mid)
    rows.append("    door mid-column x spread (slab side) %.1f mm over %.3f m height" % (slab * 1000, mid[-1].z - mid[0].z))
    check("door slab: x spread over the door height (m)", float(slab), 0.03, cmp="le")
    rows.append("    door y %.4f .. %.4f, beltline z %.4f; %d verts, %d faces" % (G["y_df"], G["y_dr"], G["z_belt"],
                                                                                 len(me.vertices), len(me.polygons)))
    print("NOVA GTE PHASE 7 - CABIN / DOOR BRIDGE VERIFICATION")
    print("%-64s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS - front and rear assemblies connected through %s" % NAME)


def main():
    D = p4.dims()
    coll = bpy.data.collections["NOVA_PROC"]
    G = build(D)
    ob = make_object(G, coll)
    audit(D, G, ob)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


if __name__ == "__main__":
    main()
