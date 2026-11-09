"""Phase 9 - procedural Nova GTE: proportional deformation and swage creases (Nik's Phase 9 spec, 2026-10-20).

Applied as spatial deformation fields to every body and glass object, so vertices shared by neighbouring objects
move together and the welded seams stay closed (the 2D Side_Profile_* templates are the rebuild references for
phases 4-8 and are left unchanged; their 3D pieces are Chassis_Front / Chassis_Rear / Side_Profile_Door_Left /
Tailgate):
 1. Greenhouse roof taper: every vertex above the window bottom trim line (beltline z_belt) is scaled toward the
    centre line: x' = x (1 - ROOF_TAPER t), t = smoothstep from the beltline (0) to the roof top (1).
 2. Swage line + tailgate shelf: the beltline loop under the side windows is pushed out (+x by SWAGE) and the loop
    continues round the back as the crease row below the rear glass (pushed rearward +y by SWAGE); the tailgate's
    lower panel (crease row down to the bumper top) is pushed rearward by SHELF relative to the glass base.
 3. Rear arch flat top: the rear arch lip vertices within FLAT_BAND of the arch top are raised to the top height
    (the panel column above each one is re-spaced so no face folds; the wheel-well wall follows the lip).
Phases 4-8 are re-run first (phase8_windows.main) so the script always starts from the clean cabin.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase9_proportions.py   (saves)"""
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
import phase7_bridge as p7           # noqa: E402
import phase8_windows as p8          # noqa: E402

NovaSpecError = p4.NovaSpecError
ROOF_TAPER = 0.10          # 10 % narrower at the roof top
SWAGE = 0.008              # shoulder crease displacement
SHELF = 0.015              # tailgate lower panel pushed rearward
FLAT_BAND = 0.035          # rear arch lip vertices this close to the top are flattened
BAND = 0.0025              # vertex selection tolerance for the crease loops
BODY = ("Hood", "Chassis_Front", "Chassis_Rear", "Tailgate", "Fender_Front_Left", "Quarter_Rear_Left",
        "Side_Profile_Door_Left")
ALL = BODY + p8.GLASS


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def tailgate_rows():
    return {p[0]: (p[1], p[2]) for p in p4.template_chain("Side_Profile_Tailgate")[0]}


def roof_width(z_top_band=0.006):
    """Roof width at mid roof (y -0.1 .. 0.6): twice the largest |x| of the vertices at the roof top."""
    best = 0.0
    for n in ("Side_Profile_Door_Left", "Chassis_Rear"):
        for v in bpy.data.objects[n].data.vertices:
            if -0.1 < v.co.y < 0.6 and v.co.z > roof_z(v.co.y) - z_top_band:
                best = max(best, abs(v.co.x))
    return 2 * best


def roof_z(y):
    pts = sorted((p[1], p[2]) for c in p4.template_chain("Side_Profile_Chassis") for p in c
                 if p[0] in ("windshield_top", "roof_front", "roof_apex", "roof_rear", "tailgate_top"))
    return float(np.interp(y, [p[0] for p in pts], [p[1] for p in pts]))


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        p8.main()
    D = p4.dims()
    O = bpy.data.objects
    z_belt = float(np.mean([p[1] for p in json.load(open(p7.FEAT))["features"]["beltline_rear"]]))
    z_top = D["height"]
    TR = tailgate_rows()
    crease_y, crease_z = TR["tailgate_lower"]
    btop_y, btop_z = TR["rear_bumper_top"]
    y_face = lambda z: crease_y + (btop_y - crease_y) * (crease_z - z) / (crease_z - btop_z)
    before = {"roof_w": roof_width()}
    bm0 = bmesh.new(); bm0.from_mesh(O["Side_Profile_Door_Left"].data)
    before["door_tree"] = BVHTree.FromBMesh(bm0); bm0.free()
    before_belt = {}
    stats = {"swage_side": 0, "swage_rear": 0, "shelf": 0, "taper": 0, "arch": 0}
    # ---- 3. rear arch flat top (Quarter_Rear_Left: lip kind 1, well wall kind 2, panel 0 / 3)
    q = O["Quarter_Rear_Left"]; me = q.data
    kind = np.array([d.value for d in me.attributes["kind"].data])
    lip = [v for v, k in zip(me.vertices, kind) if k == 1]
    z_arch_top = max(v.co.z for v in lip)
    raise_by = {}
    for v in lip:
        if v.co.z > z_arch_top - FLAT_BAND:
            raise_by[round(v.co.y, 5)] = (v.co.z, z_arch_top)
    for v, k in zip(me.vertices, kind):
        key = round(v.co.y, 5)
        if key not in raise_by:
            continue
        old, new = raise_by[key]
        if k in (1, 2) and abs(v.co.z - old) < 1e-6:
            v.co.z = new
            stats["arch"] += int(k == 1)
        elif k in (0, 3) and old < v.co.z < old + 0.10:          # re-space the panel column above the lip
            v.co.z = new + (v.co.z - old) * (old + 0.10 - new) / 0.10
    me.update()
    # ---- 2 + 1. field deformation on every body / glass object
    def bump(dz, hw=0.012):
        u = 1.0 - (dz / hw) ** 2
        return u * u if u > 0 else 0.0
    for n in ALL:
        ob = O[n]; me = ob.data
        for v in me.vertices:
            x, y, z = v.co
            # swage loop under the side windows: smooth crease bump at the beltline, along the door / quarter
            # (faded in after the front door shut line and out before the C-pillar, where the rear loop takes over)
            wy = smoothstep(-0.664, -0.62, y) * (1.0 - smoothstep(crease_y - 0.14, crease_y - 0.03, y))
            w = bump(z - z_belt) * wy if abs(x) > 0.45 else 0.0
            if w > 0:
                v.co.x += (SWAGE if x > 0 else -SWAGE) * w
                stats["swage_side"] += int(w > 0.99)
            # rear: shelf (lower panel crease -> bumper top pushed rearward) + swage bump at the crease row
            wr = smoothstep(crease_y - 0.20, crease_y - 0.06, y)
            if wr > 0:
                wz = smoothstep(btop_z - 0.02, btop_z, z) * (1.0 - smoothstep(crease_z, crease_z + 0.08, z))
                dy = SHELF * wz + SWAGE * bump(z - crease_z)
                if dy > 0:
                    v.co.y += dy * wr
                    stats["shelf"] += int(wz * wr > 0.99)
                    stats["swage_rear"] += int(bump(z - crease_z) * wr > 0.99)
            # greenhouse taper above the beltline
            if z > z_belt:
                t = smoothstep(z_belt, z_top, z)
                v.co.x *= 1.0 - ROOF_TAPER * t
                stats["taper"] += 1
        me.update()
    # re-weld: door seam vertices that ended up off a neighbour's (curved / re-spaced) edge by < 6 mm snap onto it
    dg = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(O[n], dg) for n in ("Fender_Front_Left", "Quarter_Rear_Left", "Chassis_Front",
                                                    "Chassis_Rear", "Tailgate", "Hood")]
    dm = O["Side_Profile_Door_Left"].data
    bm = bmesh.new(); bm.from_mesh(dm)
    snapped = 0
    for vv in {v for e in bm.edges if e.is_boundary for v in e.verts}:
        if abs(vv.co.x) < 1e-6:
            continue
        hit = min((t.find_nearest(vv.co) for t in trees), key=lambda h: h[3] if h[0] is not None else 9)
        lim = 0.03 if vv.co.y > crease_y - 0.20 else 0.006      # C-pillar foot: neighbours' long straight edges
        if hit[0] is not None and 1e-6 < hit[3] < lim:
            vv.co = hit[0]; snapped += 1
    bm.to_mesh(dm); bm.free(); dm.update()
    stats["snapped"] = snapped
    for n in ALL:
        p4.clean_mesh(O[n])
    audit(D, before, stats, z_belt, z_arch_top, (crease_y, crease_z, btop_y, btop_z))
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


def audit(D, before, stats, z_belt, z_arch_top, tg):
    rows, bad = [], []

    def check(label, meas, spec, tol=0.001, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-62s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    O = bpy.data.objects
    dg = bpy.context.evaluated_depsgraph_get()
    rw = roof_width()
    rows.append("ROOF vs TRACK:")
    rows.append("    roof width (mid roof, top)  before %.3f m -> after %.3f m  (%.1f %% narrower)"
                % (before["roof_w"], rw, 100 * (1 - rw / before["roof_w"])))
    rows.append("    front track %.3f m  -> roof / front track = %.3f" % (D["track_front"], rw / D["track_front"]))
    rows.append("    rear track  %.3f m  -> roof / rear track  = %.3f" % (D["track_rear"], rw / D["track_rear"]))
    rows.append("    body width  %.3f m  -> roof / body width  = %.3f" % (D["width"], rw / D["width"]))
    check("roof narrowed by the taper factor at the roof top", rw / before["roof_w"], 1 - ROOF_TAPER, tol=0.01)
    # swage: beltline loop sits SWAGE outside its neighbours just above and below
    door = O["Side_Profile_Door_Left"].data
    loop = [v.co for v in door.vertices if abs(v.co.z - z_belt) < BAND and abs(v.co.x) > 0.45]
    d = [before["door_tree"].find_nearest(c)[3] for c in loop]
    d_mid = [dd for c, dd in zip(loop, d) if -0.55 < c.y < tg[0] - 0.16]
    check("swage: beltline loop pushed out from the panel (min, mid door/quarter, m)", float(min(d_mid)), SWAGE, tol=0.0015)
    check("swage: beltline loop pushed out from the panel (max, mid door/quarter, m)", float(max(d_mid)), SWAGE, tol=0.0015)
    check("swage: side loop vertices moved", float(stats["swage_side"]), 20.0, cmp="ge")
    check("swage: rear loop (crease row) vertices moved", float(stats["swage_rear"]), 7.0, cmp="ge")
    crease_y, crease_z, btop_y, btop_z = tg
    T = np.array([tuple(v.co) for v in O["Tailgate"].data.vertices])
    cr = T[np.abs(T[:, 2] - crease_z) < BAND]
    check("shelf: crease row y = template + SHELF + SWAGE", float(cr[:, 1].max()), crease_y + SHELF + SWAGE, tol=5e-4)
    bt = T[np.abs(T[:, 2] - btop_z) < BAND]
    check("shelf: bumper-top row y = template + SHELF", float(bt[:, 1].max()), btop_y + SHELF, tol=5e-4)
    check("shelf: still inside the car length (max y)", float(T[:, 1].max()), D["length"] / 2 + 1e-6, cmp="le")
    # rear arch
    q = O["Quarter_Rear_Left"].data
    kind = np.array([d.value for d in q.attributes["kind"].data])
    L = np.array([tuple(v.co) for v, k in zip(q.vertices, kind) if k == 1])
    top = L[L[:, 2] > z_arch_top - 1e-6]
    rows.append("    rear arch flat top: %d lip vertices at z %.4f, from y %.3f to %.3f (%.0f mm long)"
                % (len(top), z_arch_top, top[:, 1].min(), top[:, 1].max(), (top[:, 1].max() - top[:, 1].min()) * 1000))
    check("rear arch: flat-top length (m)", float(top[:, 1].max() - top[:, 1].min()), 0.15, cmp="ge")
    check("rear arch: flat top z spread", float(np.ptp(top[:, 2])), 0.0, tol=1e-6)
    # seams: the door object's boundary still welded to its neighbours
    trees = {n: BVHTree.FromObject(O[n], dg) for n in ("Fender_Front_Left", "Quarter_Rear_Left", "Chassis_Front",
                                                         "Chassis_Rear", "Tailgate") + p8.GLASS}
    bm = bmesh.new(); bm.from_mesh(door)
    bverts = {v for e in bm.edges if e.is_boundary for v in e.verts}
    gaps = [min(t.find_nearest(v.co)[3] for t in trees.values()) for v in bverts if v.co.z > 0.25 and abs(v.co.x) > 1e-6]
    bm.free()
    check("seams: door boundary to neighbours, max gap (m)", float(max(gaps)), 0.0, tol=0.001)
    for n in ALL:
        me = O[n].data
        check("%s: degenerate faces" % n, float(sum(1 for p in me.polygons if p.area < 1e-10)), 0.0)
        ev = O[n].evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored symmetric" % n, float(EX.max() + EX.min()), 0.0, tol=1e-6)
        O[n].evaluated_get(dg).to_mesh_clear()
    rows.append("    vertices moved (full weight): taper %d, swage side %d, swage rear %d, shelf %d, arch lip %d; seam verts re-welded %d"
                % (stats["taper"], stats["swage_side"], stats["swage_rear"], stats["shelf"], stats["arch"], stats["snapped"]))
    print("NOVA GTE PHASE 9 - PROPORTIONAL DEFORMATION & SWAGE VERIFICATION")
    print("%-62s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
