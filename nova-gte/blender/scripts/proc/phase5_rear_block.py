"""Phase 5 - procedural Nova GTE: rear 3D block (tailgate / rear panel / bumper) and rear roof section, mirrored.

Frame: metres, x+ = car's left, y- = front, z up; width along X, Mirror modifier on X (clipping + merge).
Tailgate: every vertex of the Side_Profile_Tailgate template (Phase 3) becomes a row across the car from its outer
half-width to x = 0. Chassis_Rear: the rear-most section of Side_Profile_Chassis (roof rear -> tailgate top).
Half-widths per row: Nik's grey rear picture (reference/photos/grey_studio/rear.png), silhouette width at the row's
height. Calibration: across 172 px/m (rear plate 520 x 111 mm = 175 px/m, bumper = factory width 169 px/m);
height v = 237.5 - 158.6 z (tyre contact v 237.5 = ground, roof top v 21 = master height; the plate centre then
lands at z 0.668, the bumper stripe at z 0.47 - consistent with the side template).
Rear stance: the rows of the flat rear fascia (crease below the glass -> bumper face, selected by coordinates) are
squared up - every row straight across the car (one y, one z), the bumper-face rows on one vertical plane at the
tail; the crease row below the rear window is marked sharp. Body must cover the rear tyres: max half-width >=
rear track / 2 + tyre half-width (175 mm section). Audit raises NovaSpecError on any failure.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase5_rear_block.py   (saves)"""
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4_front_block as p4      # noqa: E402  (shared builders: template_chain, strip_object, clean_mesh)

TOL = 0.001
TYRE_HALF_W = 0.175 / 2
HALF_W = {                              # m, grey rear picture (see module notes)
    "roof_rear": 0.474, "tailgate_top": 0.512, "tailgate_slope": 0.596, "tailgate_lower": 0.701,
    "rear_bumper_top": 0.741, "rear_bumper_upper_edge": 0.753, "rear_bumper_face": 0.750,
    "rear_bumper_lower_edge": 0.733,
}
CREASE_ROW = "tailgate_lower"           # crease below the rear window
FASCIA_ROWS = ("tailgate_lower", "rear_bumper_top", "rear_bumper_upper_edge", "rear_bumper_face",
               "rear_bumper_lower_edge")
CHASSIS_REAR = ("roof_rear", "tailgate_top")
NovaSpecError = p4.NovaSpecError


def row_names(ob):
    layer = ob.data.attributes.get("row")
    return [d.value if isinstance(d.value, str) else d.value.decode() for d in layer.data]


def square_up(ob, D):
    """Fascia rows: each row exactly straight across (mean y, mean z of the row); the bumper-face rows (at the tail)
    exactly on y = length / 2. Returns the lower-panel rake (crease row -> bumper top)."""
    me = ob.data
    names = row_names(ob)
    rows = {}
    for v, n in zip(me.vertices, names):
        if n in FASCIA_ROWS:
            rows.setdefault(n, []).append(v)
    for n, vs in rows.items():
        y = float(np.mean([v.co.y for v in vs])); z = float(np.mean([v.co.z for v in vs]))
        if n in ("rear_bumper_upper_edge", "rear_bumper_face"):
            y = D["length"] / 2
        for v in vs:
            v.co.y, v.co.z = y, z
    me.update()
    a, b = rows["tailgate_lower"][0].co, rows["rear_bumper_top"][0].co
    return math.degrees(math.atan2(b.y - a.y, a.z - b.z)), rows


def mark_crease(ob):
    me = ob.data
    names = row_names(ob)
    n = 0
    for e in me.edges:
        if all(names[i] == CREASE_ROW for i in e.vertices):
            e.use_edge_sharp = True
            n += 1
    return n


def audit(D, objs, info):
    rows, bad = [], []

    def check(label, meas, spec, tol=TOL, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-60s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    dg = bpy.context.evaluated_depsgraph_get()
    for name, ob in objs.items():
        me = ob.data
        X = np.array([v.co.x for v in me.vertices])
        check("%s: origin at world centre (|location|)" % name, float(ob.location.length), 0.0, tol=1e-9)
        check("%s: no vertex left of the centre line (min x)" % name, float(X.min()), 0.0, tol=1e-9)
        seam = [v for v in me.vertices if abs(v.co.x) < 1e-5]
        check("%s: centre-seam vertices exactly x = 0 (max |x|)" % name, float(max(abs(v.co.x) for v in seam)), 0.0, tol=1e-12)
        check("%s: one seam vertex per row" % name, float(len(seam)), float(len(me.vertices) // (p4.NCOL + 1)))
        m = ob.modifiers.get("Mirror_X")
        check("%s: mirror X + clipping + merge" % name, float(bool(m) and m.use_axis[0] and m.use_clip and m.use_mirror_merge), 1.0)
        ev = ob.evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored verts = 2 x half - seam (merged)" % name, float(len(ev.vertices)), float(2 * len(me.vertices) - len(seam)))
        check("%s: mirrored symmetric (max x + min x)" % name, float(EX.max() + EX.min()), 0.0, tol=1e-9)
        check("%s: mirrored width <= factory width" % name, float(EX.max() - EX.min()), D["width"], cmp="le")
        ob.evaluated_get(dg).to_mesh_clear()
        check("%s: degenerate faces" % name, float(sum(1 for p in me.polygons if p.normal.length < 0.5)), 0.0)
    tg = objs["Tailgate"].data
    W = np.array([tuple(v.co) for v in tg.vertices])
    check("Tailgate: tail y = length / 2", float(W[:, 1].max()), D["length"] / 2)
    check("Tailgate: body covers the rear tyres (max half-width)", float(W[:, 0].max()),
          D["track_rear"] / 2 + TYRE_HALF_W, cmp="ge")
    check("Tailgate: top z = tailgate-top template height", float(W[:, 2].max()),
          max(p[2] for p in p4.template_chain("Side_Profile_Tailgate")[0]))
    for n, vs in info["rows"].items():
        ys = [v.co.y for v in vs]; zs = [v.co.z for v in vs]
        check("Tailgate: row %s squared (y/z spread)" % n, float(max(ys) - min(ys) + max(zs) - min(zs)), 0.0, tol=1e-9)
    face = [v.co.y for n in ("rear_bumper_upper_edge", "rear_bumper_face") for v in info["rows"][n]]
    check("Tailgate: bumper face vertical on the tail plane (max |y - L/2|)", float(max(abs(y - D["length"] / 2) for y in face)), 0.0, tol=1e-6)   # float32 coordinates
    check("Tailgate: crease below the glass marked sharp (edges)", float(info["crease_edges"]), float(p4.NCOL))
    rows.append("    lower rear panel rake (crease -> bumper top): %.1f deg from vertical (top set forward)" % info["rake"])
    rows.append("    Tailgate z %.4f .. %.4f, y %.4f .. %.4f; Chassis_Rear half-width %.3f .. %.3f" % (
        W[:, 2].min(), W[:, 2].max(), W[:, 1].min(), W[:, 1].max(),
        min(v.co.x for v in objs["Chassis_Rear"].data.vertices if v.co.x > 0),
        max(v.co.x for v in objs["Chassis_Rear"].data.vertices)))
    print("NOVA GTE PHASE 5 - REAR BLOCK VERIFICATION")
    print("%-60s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


def main():
    D = p4.dims()
    coll = bpy.data.collections["NOVA_PROC"]
    tg_rows = p4.template_chain("Side_Profile_Tailgate")[0]
    if tg_rows[0][1] > tg_rows[-1][1]:
        tg_rows = tg_rows[::-1]
    out = lambda c: (c - type(c)((0.0, c.y - 0.5, 0.45))).normalized()     # outward: up / rearward
    tg = p4.strip_object("Tailgate", tg_rows, [HALF_W[p[0]] for p in tg_rows], coll, out)
    rake, rows = square_up(tg, D)
    p4.clean_mesh(tg)
    # the edit-mode round trip reallocates the vertices: collect the rows again (stale references read garbage)
    names = row_names(tg)
    rows = {n: [v for v, nm in zip(tg.data.vertices, names) if nm == n] for n in rows}
    info = {"rake": rake, "rows": rows, "crease_edges": mark_crease(tg)}
    rr = sorted(p4.template_chain("Side_Profile_Chassis", only=CHASSIS_REAR)[0], key=lambda p: p[1])
    cr = p4.strip_object("Chassis_Rear", rr, [HALF_W[p[0]] for p in rr], coll, out)
    objs = {"Tailgate": tg, "Chassis_Rear": cr}
    audit(D, objs, info)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


if __name__ == "__main__":
    main()
