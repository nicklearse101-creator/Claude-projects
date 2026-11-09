"""Phase 4 - procedural Nova GTE: front 3D block (hood / nose) and windscreen section, mirrored.

Frame: metres, x+ = car's left, y- = front, z up. Width runs along X: the outer edge sits at x = width / 2 and the
Mirror modifier (X axis, clipping, merge) generates the right-hand side from the left half (x >= 0).

Hood: every vertex of the Side_Profile_Hood template (Phase 3) becomes a row across the car, from the outer edge
inward to the centre line x = 0 (NCOL quads per row). Outer half-width = width / 2, minus a forward taper
(TAPER, smoothstep from the front axle to the nose) - the nose rows sit further in than the windscreen-base row.
Grille stance: the nose rows between the bumper top and the headlamp top (selected by coordinates) are snapped onto
one straight line in Y-Z, i.e. one flat face across the car; its rake is the picture's (top set back, ~16 deg).
Chassis_Front: the front section of Side_Profile_Chassis (windscreen base -> windscreen top), extruded the same way
with the greenhouse tumblehome measured on the grey front picture (half-width 0.665 at the base, 0.557 at the top).
The 2D templates are left as they are. Origins at the world centre. Audit raises NovaSpecError on any failure.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase4_front_block.py   (saves)"""
import math

import bmesh
import bpy
import numpy as np

TOL = 0.001
NCOL = 6                      # quads across the half width
TAPER = 0.060                 # nose rows pulled in by this much at the very front (smoothstep from the front axle)
WS_HALF = {"windshield_base": 0.665, "windshield_top": 0.557}   # grey front picture, FRONT_CAM (phase 3 notes)
# Wing tumblehome (Nik 2026-10-20: "the wings are inside out" - a full-width top edge made the wing lean out): the
# front silhouette on the grey front picture narrows from the lower body (z 0.62) to the scuttle; ratio of the
# silhouette width at height z to the full width (v 100-140 of front.png, mapped on the face plane).
TUMBLE = ((0.62, 1.000), (0.67, 0.992), (0.72, 0.973), (0.77, 0.950), (0.81, 0.927), (0.86, 0.889), (0.95, 0.850))
GRILLE_Z = (0.52, 0.68)       # nose rows in this height band form the grille / headlamp face
CHASSIS_FRONT = ("windshield_base", "windshield_top")


class NovaSpecError(Exception):
    """Geometry deviates from the master dimensions or fails a structural check."""


def dims():
    sc = bpy.context.scene
    if "nova_gte_dimensions" not in sc:
        raise NovaSpecError("scene has no nova_gte_dimensions - run phase1_bounds.py first")
    return {k: float(v) for k, v in sc["nova_gte_dimensions"].items()}


def template_chain(name, only=None):
    """(point name, y, z) along the template's edges, world coordinates; optional point filter."""
    ob = bpy.data.objects[name]
    me = ob.data
    names = {}
    layer = me.attributes.get("point")
    if layer is not None:
        for i, d in enumerate(layer.data):
            names[i] = d.value if isinstance(d.value, str) else d.value.decode()
    adj = {v.index: [] for v in me.vertices}
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)
    chains, seen = [], set()
    for s in [i for i, n in adj.items() if len(n) == 1]:
        if s in seen:
            continue
        chain, prev, cur = [s], None, s
        seen.add(s)
        while True:
            nxt = [n for n in adj[cur] if n != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            chain.append(cur); seen.add(cur)
        chains.append(chain)
    out = []
    for c in chains:
        pts = [(names.get(i, str(i)), *(ob.matrix_world @ me.vertices[i].co)[1:]) for i in c]
        if only is None or any(p[0] in only for p in pts):
            out.append([p for p in pts if only is None or p[0] in only])
    return out


def wing_half_width(D, y, z):
    """Outer edge of the front body at (y, z): half the factory width, the forward taper, the wing tumblehome."""
    zz, rr = zip(*TUMBLE)
    y_front_axle = -D["length"] / 2 + D["overhang_front"]
    return (D["width"] / 2 - TAPER * smoothstep(y_front_axle, -D["length"] / 2, y)) * float(np.interp(z, zz, rr))


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def clean_mesh(ob):
    """Hygiene block: merge by distance + consistent outward normals, back to object mode."""
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def strip_object(name, rows, half_widths, coll, up_hint):
    """Rows (name, y, z) extruded from x = half width to x = 0; quads between neighbouring rows."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    bm = bmesh.new()
    tag = bm.verts.layers.string.new("row")
    grid = []
    for (pn, y, z), hw in zip(rows, half_widths):
        row = []
        for j in range(NCOL + 1):
            v = bm.verts.new((hw * (1 - j / NCOL), y, z))           # j = NCOL -> x = 0 exactly
            v[tag] = pn.encode()
            row.append(v)
        grid.append(row)
    for i in range(len(grid) - 1):
        for j in range(NCOL):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = (0.0, 0.0, 0.0)                                   # origin at the world centre
    clean_mesh(ob)
    # outward = away from the car's inside: flip if most normals point against the hint (up / forward)
    me.update()
    s = sum(p.normal.dot(up_hint(p.center)) for p in me.polygons)
    if s < 0:
        me.flip_normals()
    for v in me.vertices:                                           # centre seam exactly on x = 0
        if abs(v.co.x) < 1e-6:
            v.co.x = 0.0
    m = ob.modifiers.new("Mirror_X", "MIRROR")
    m.use_axis = (True, False, False)
    m.use_clip = True
    m.use_mirror_merge = True
    m.merge_threshold = 0.0001
    return ob


def grille_stance(ob):
    """Snap the nose rows inside GRILLE_Z (front-most quarter of the hood rows) onto one straight Y-Z line."""
    me = ob.data
    ys = np.array([v.co.y for v in me.vertices])
    sel = [v for v in me.vertices if v.co.y < ys.min() + 0.12 and GRILLE_Z[0] <= v.co.z <= GRILLE_Z[1]]
    P = np.array([(v.co.y, v.co.z) for v in sel])
    rows = np.unique(np.round(P, 6), axis=0)
    if len(rows) < 2:
        raise NovaSpecError("grille stance: fewer than 2 nose rows in the grille band")
    # line y = a + b z through the rows (least squares), then project every selected vertex onto it
    b, a = np.polyfit(rows[:, 1], rows[:, 0], 1)
    for v in sel:
        v.co.y = a + b * v.co.z
    me.update()
    return {"rows": len(rows), "rake_deg": math.degrees(math.atan(b)), "a": a, "b": b, "verts": len(sel)}


def audit(D, objs, info, half_w):
    rows, bad = [], []

    def check(label, meas, spec, tol=TOL, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-56s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
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
        check("%s: one seam vertex per row" % name, float(len(seam)), float(len(me.vertices) // (NCOL + 1)))
        m = ob.modifiers.get("Mirror_X")
        check("%s: mirror X + clipping + merge" % name,
              float(bool(m) and m.use_axis[0] and m.use_clip and m.use_mirror_merge), 1.0)
        ev = ob.evaluated_get(dg).to_mesh()
        EX = np.array([v.co.x for v in ev.vertices])
        check("%s: mirrored verts = 2 x half - seam (merged)" % name, float(len(ev.vertices)),
              float(2 * len(me.vertices) - len(seam)))
        check("%s: mirrored symmetric (max x + min x)" % name, float(EX.max() + EX.min()), 0.0, tol=1e-9)
        if name == "Hood":
            check("Hood: max width (mirrored) <= factory width", float(EX.max() - EX.min()), D["width"], cmp="le")
            err = max(abs(max(v.co.x for v in me.vertices if abs(v.co.y - y) < 1e-6 and abs(v.co.z - z) < 1e-6)
                          - wing_half_width(D, y, z)) for y, z in {(round(v.co.y, 6), round(v.co.z, 6)) for v in me.vertices})
            check("Hood: outer edge = width/2 x taper x tumblehome (max err)", float(err), 0.0)
        else:
            check("Chassis_Front: windscreen base half-width", float(X.max()), WS_HALF["windshield_base"])
        ob.evaluated_get(dg).to_mesh_clear()
        nz = sum(1 for p in me.polygons if p.normal.length < 0.5)
        check("%s: degenerate faces" % name, float(nz), 0.0)
    hood = objs["Hood"].data
    ymin = min(v.co.y for v in hood.vertices)
    nose_hw = max(v.co.x for v in hood.vertices if abs(v.co.y - ymin) < 0.03)
    base_y = max(v.co.y for v in hood.vertices)
    base_hw = max(v.co.x for v in hood.vertices if abs(v.co.y - base_y) < 1e-6)
    zn = [v.co.z for v in hood.vertices if abs(v.co.y - ymin) < 0.03 and v.co.x == nose_hw][0]
    check("Hood: taper at the nose (width/2 x tumble - nose half-width)",
          (D["width"] / 2) * float(np.interp(zn, *zip(*TUMBLE))) - nose_hw, TAPER, tol=0.004)
    g = info["grille"]
    sel = [v for v in hood.vertices if v.co.y < ymin + 0.12 and GRILLE_Z[0] <= v.co.z <= GRILLE_Z[1]]
    res = max(abs(v.co.y - (g["a"] + g["b"] * v.co.z)) for v in sel)
    check("Hood: grille face planar (max residual)", float(res), 0.0, tol=1e-6)
    rows.append("    grille face: %d rows, %d verts, rake %.1f deg from vertical (top set back), y = %.4f + %.4f z"
                % (g["rows"], g["verts"], g["rake_deg"], g["a"], g["b"]))
    tz = [v.co.z for v in hood.vertices]
    rows.append("    Hood z range %.4f .. %.4f, y range %.4f .. %.4f" % (min(tz), max(tz), ymin, base_y))
    print("NOVA GTE PHASE 4 - FRONT BLOCK VERIFICATION")
    print("%-56s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


def main():
    D = dims()
    half_w = D["width"] / 2
    coll = bpy.data.collections["NOVA_PROC"]
    y_front_axle = -D["length"] / 2 + D["overhang_front"]
    hood_rows = template_chain("Side_Profile_Hood")[0]
    if hood_rows[0][1] > hood_rows[-1][1]:
        hood_rows = hood_rows[::-1]
    hw = [wing_half_width(D, y, z) for _, y, z in hood_rows]
    up = lambda c: (c - type(c)((0.0, c.y, 0.35))).normalized()   # outward from a line through the car's middle
    hood = strip_object("Hood", hood_rows, hw, coll, up)
    info = {"grille": grille_stance(hood)}
    clean_mesh(hood)
    ws = [p for p in template_chain("Side_Profile_Chassis", only=CHASSIS_FRONT)[0]]
    ws.sort(key=lambda p: p[1])
    cf = strip_object("Chassis_Front", ws, [WS_HALF[p[0]] for p in ws], coll, up)
    objs = {"Hood": hood, "Chassis_Front": cf}
    audit(D, objs, info, half_w)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


if __name__ == "__main__":
    main()
