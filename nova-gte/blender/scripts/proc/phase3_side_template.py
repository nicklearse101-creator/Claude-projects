"""Phase 3 - procedural Nova GTE: low-poly 2D side-profile template (one continuous loop -> three objects).

Every position is computed from scene['nova_gte_dimensions'] (Phase 1): y and z as fractions of the master length
and height, the sill ends as fractions of the wheelbase measured from the axles. The fractions are the feature
points of the Phase 2 outline traced on Nik's grey side picture (Profile_Side, fitted to the master dimensions),
picked at the profile's corners (bumper face/top, lamp, bonnet nose, scuttle, windscreen base and top, roof,
tailgate, rear bumper, sill) - 22 vertices.
The template stands on the outer edge of the track (x = max track / 2, car's left side) in the Y-Z plane:
local x of every vertex = 0 (flattened), object location x = track edge.
Split into Side_Profile_Hood (front bumper -> windscreen base), Side_Profile_Chassis (windscreen base -> roof ->
tailgate top, plus the sill from the rear bumper bottom to the front bumper bottom) and Side_Profile_Tailgate
(tailgate top -> rear bumper bottom). Shared corner vertices are duplicated so each piece is self-contained.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase3_side_template.py   (saves)"""
import bmesh
import bpy
import numpy as np

TOL = 0.001


class NovaSpecError(Exception):
    """Template deviates from the master dimensions or fails a structural check."""


# (name, y as fraction of length from the centre, z as fraction of height) - loop order, front bumper first.
# Exactly-defined points: nose -0.5 L, tail +0.5 L, roof apex 1.0 H.
LOOP = [
    ("front_bumper_lower_edge", -0.4904, 0.1360),
    ("front_bumper_face", -0.5000, 0.2761),
    ("front_bumper_upper_edge", -0.4991, 0.3664),
    ("front_bumper_top", -0.4862, 0.3916),
    ("headlamp_top", -0.4762, 0.4865),
    ("hood_nose", -0.4557, 0.5487),
    ("hood_mid", -0.3446, 0.6342),
    ("scuttle", -0.2187, 0.6668),            # bonnet rear edge / scuttle panel
    ("windshield_base", -0.1875, 0.6999),
    ("windshield_top", -0.0590, 0.9547),
    ("roof_front", 0.0054, 0.9871),
    ("roof_apex", 0.2111, 1.0000),
    ("roof_rear", 0.3119, 0.9839),
    ("tailgate_top", 0.3720, 0.9598),
    ("tailgate_slope", 0.4215, 0.8183),
    ("tailgate_lower", 0.4818, 0.6151),
    ("rear_bumper_top", 0.4875, 0.4079),
    ("rear_bumper_upper_edge", 0.5000, 0.3877),
    ("rear_bumper_face", 0.5000, 0.3271),
    ("rear_bumper_lower_edge", 0.4932, 0.1747),
    ("sill_rear", None, 0.1364),          # y: rear axle - 0.1427 wheelbase
    ("sill_front", None, 0.1313),         # y: front axle + 0.1328 wheelbase
]
SILL_WB = {"sill_rear": ("rear", -0.1427), "sill_front": ("front", 0.1328)}
PIECES = {
    "Side_Profile_Hood": [["front_bumper_lower_edge", "front_bumper_face", "front_bumper_upper_edge",
                           "front_bumper_top", "headlamp_top", "hood_nose", "hood_mid", "scuttle",
                           "windshield_base"]],
    "Side_Profile_Chassis": [["windshield_base", "windshield_top", "roof_front", "roof_apex", "roof_rear",
                              "tailgate_top"],
                             ["rear_bumper_lower_edge", "sill_rear", "sill_front", "front_bumper_lower_edge"]],
    "Side_Profile_Tailgate": [["tailgate_top", "tailgate_slope", "tailgate_lower", "rear_bumper_top",
                               "rear_bumper_upper_edge", "rear_bumper_face", "rear_bumper_lower_edge"]],
}


def dims():
    sc = bpy.context.scene
    if "nova_gte_dimensions" not in sc:
        raise NovaSpecError("scene has no nova_gte_dimensions - run phase1_bounds.py first")
    return {k: float(v) for k, v in sc["nova_gte_dimensions"].items()}


def points(D):
    """Loop vertices (y, z) in metres from the master dimensions."""
    L, H, WB = D["length"], D["height"], D["wheelbase"]
    axle = {"front": -L / 2 + D["overhang_front"]}
    axle["rear"] = axle["front"] + WB
    pts = {}
    for name, fy, fz in LOOP:
        if fy is None:
            side, k = SILL_WB[name]
            y = axle[side] + k * WB
        else:
            y = fy * L
        pts[name] = (y, fz * H)
    return pts


def clean_mesh(ob):
    """Hygiene block: merge by distance + consistent normals, back to object mode."""
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def make_piece(name, chains, pts, x_track, coll):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    bm = bmesh.new()
    tag = bm.verts.layers.string.new("point")
    for chain in chains:
        vs = []
        for p in chain:
            v = bm.verts.new((0.0, pts[p][0], pts[p][1]))      # local x = 0: flat in the Y-Z plane
            v[tag] = p.encode()
            vs.append(v)
        for a, b in zip(vs[:-1], vs[1:]):
            bm.edges.new((a, b))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = (x_track, 0.0, 0.0)
    ob.display_type = "WIRE"; ob.hide_render = True
    ob["nova_template"] = "side_profile"
    clean_mesh(ob)
    for v in ob.data.vertices:                                  # enforce the flattening after any operator
        v.co.x = 0.0
    ob.data.update()
    return ob


def audit(D, pts, objs, x_track):
    rows, bad = [], []

    def check(label, meas, spec, tol=TOL, cmp="eq"):
        ok = abs(meas - spec) < tol if cmp == "eq" else (meas >= spec if cmp == "ge" else meas <= spec)
        rows.append("%-52s %9.4f %9.4f %s" % (label, meas, spec, "" if ok else " <-- FAIL"))
        if not ok:
            bad.append(label)

    bpy.context.view_layer.update()
    allw = []
    for name, ob in objs.items():
        W = np.array([tuple(ob.matrix_world @ v.co) for v in ob.data.vertices])
        allw.append(W)
        nchain_verts = sum(len(c) for c in PIECES[name])
        nchain_edges = sum(len(c) - 1 for c in PIECES[name])
        check("%s: vertex count" % name, float(len(ob.data.vertices)), float(nchain_verts))
        check("%s: edge count" % name, float(len(ob.data.edges)), float(nchain_edges))
        check("%s: local x flat (max |x|)" % name, float(max(abs(v.co.x) for v in ob.data.vertices)), 0.0, tol=1e-9)
        check("%s: global x = track edge" % name, float(W[:, 0].mean()), x_track)
        rows.append("    %s z range %.4f .. %.4f (height %.4f), y range %.4f .. %.4f" % (
            name, W[:, 2].min(), W[:, 2].max(), W[:, 2].max() - W[:, 2].min(), W[:, 1].min(), W[:, 1].max()))
    A = np.vstack(allw)
    check("Chassis: roof apex z = master height", float(np.array([tuple(objs["Side_Profile_Chassis"].matrix_world @ v.co)
                                                                 for v in objs["Side_Profile_Chassis"].data.vertices])[:, 2].max()),
          D["height"])
    check("all pieces: top z = master height", float(A[:, 2].max()), D["height"])
    check("all pieces: nose y = -length/2", float(A[:, 1].min()), -D["length"] / 2)
    check("all pieces: tail y = +length/2", float(A[:, 1].max()), D["length"] / 2)
    check("all pieces: length", float(A[:, 1].max() - A[:, 1].min()), D["length"])
    check("all pieces: lowest point z > 0 (above ground)", float(A[:, 2].min()), 0.0, cmp="ge")
    # the three pieces join into the one loop: every piece end meets exactly one other piece end
    ends = []
    for name, chains in PIECES.items():
        for c in chains:
            ends += [(c[0], name), (c[-1], name)]
    names = [e[0] for e in ends]
    check("loop continuity: every end shared by exactly 2 pieces", float(all(names.count(n) == 2 for n in names)), 1.0)
    uniq = {n for c in sum(PIECES.values(), []) for n in c}
    check("unique loop vertices (16-22)", float(len(uniq)), 22.0, tol=6.5)
    check("unique loop vertices = LOOP table", float(len(uniq)), float(len(LOOP)))
    # how closely the low-poly loop follows the traced Phase 2 outline (report, and fail only if grossly off)
    prof = bpy.data.objects.get("Profile_Side")
    if prof is not None:
        T = np.array([(v.co.y, v.co.z) for v in prof.data.vertices])
        loop = np.array([pts[n] for n, _, _ in LOOP] + [pts[LOOP[0][0]]])
        segs = []
        for (y0, z0), (y1, z1) in zip(loop[:-1], loop[1:]):
            d = np.array([y1 - y0, z1 - z0]); Ls = np.dot(d, d)
            t = np.clip(((T[:, 0] - y0) * d[0] + (T[:, 1] - z0) * d[1]) / Ls, 0, 1)
            segs.append(np.hypot(T[:, 0] - (y0 + t * d[0]), T[:, 1] - (z0 + t * d[1])))
        dist = np.min(np.stack(segs), axis=0)
        upper = T[:, 1] > 0.62                       # above the arch tops: bonnet, glass, roof, tailgate
        rows.append("    traced outline vs template above z 0.62: mean %.1f mm, max %.1f mm" % (
            dist[upper].mean() * 1000, dist[upper].max() * 1000))
        check("traced outline above arches: max deviation (m)", float(dist[upper].max()), 0.03, cmp="le")
    print("NOVA GTE PHASE 3 - SIDE PROFILE TEMPLATE VERIFICATION")
    print("%-52s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


def main():
    D = dims()
    pts = points(D)
    x_track = max(D["track_front"], D["track_rear"]) / 2
    coll = bpy.data.collections["NOVA_PROC"]
    objs = {name: make_piece(name, chains, pts, x_track, coll) for name, chains in PIECES.items()}
    audit(D, pts, objs, x_track)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


if __name__ == "__main__":
    main()
