"""Phase 2 - procedural Nova GTE: side profile outline, wheel arch outlines and wheel guides (2D, YZ plane, x = 0).

Input: data/proc/side_profile_raw.json from tools/proc/trace_side_profile.py (Nik's grey side picture, traced and
mapped to metres with the solved side camera). Fitting to the master dimensions (scene['nova_gte_dimensions'],
Phase 1):
  1. level: the solved camera has a small spurious roll (both picture wheel centres sit on the same pixel row but
     map 18 mm apart in z) -> z_d = z - k (y - y_wheel_front), k from the two wheel centres;
  2. ground = the levelled tyre-contact height (picture tyre bottoms);
  3. outline: y' = a + b y so nose/tail land on -/+ length/2; z' = c (z_d - ground) so the roof is the master height;
  4. arches: same scale b / c, each moved so the picture's wheel centre sits on its axle locator (the picture's
     tyres are ~0.270 m radius, the brochure 175/65 R14 is 0.2916 - the arch is anchored on the wheel, as in the
     picture, not on the ground).
Objects (collection NOVA_PROC): Profile_Side (closed edge loop), Arch_Profile_Front / _Rear (edge chains),
Wheel_Guide_Front / _Rear (tyre circles). Ends with an audit that raises NovaSpecError on any failure.
Run: blender -b blender/nova_proc.blend --python blender/scripts/proc/phase2_profile.py   (saves the file)"""
import json
import math
import os

import bmesh
import bpy
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RAW = os.path.join(ROOT, "data", "proc", "side_profile_raw.json")
TOL = 0.001
MIN_ARCH_CLEARANCE = 0.005          # arch lip above the tyre top
MIN_ARCH_SIDE_CLEARANCE = 0.010     # arch opening beyond the tyre at wheel-centre height


class NovaSpecError(Exception):
    """Geometry deviates from the master dimensions or fails a structural check."""


def dims():
    sc = bpy.context.scene
    if "nova_gte_dimensions" not in sc:
        raise NovaSpecError("scene has no nova_gte_dimensions - run phase1_bounds.py first")
    return {k: float(v) for k, v in sc["nova_gte_dimensions"].items()}


def fit(D, raw):
    wf, wr = raw["wheel_centres_m"]["front"], raw["wheel_centres_m"]["rear"]
    k = (wr[1] - wf[1]) / (wr[0] - wf[0])
    lev = lambda y, z: np.asarray(z) - k * (np.asarray(y) - wf[0])
    g = float(np.mean([lev(*raw["ground_m"][s]) for s in ("front", "rear")]))
    O = np.array(raw["outline_m"])
    zd = lev(O[:, 0], O[:, 1])
    b = D["length"] / (O[:, 0].max() - O[:, 0].min())
    a = -D["length"] / 2 - b * O[:, 0].min()
    c = D["height"] / (zd.max() - g)
    outline = np.c_[a + b * O[:, 0], c * (zd - g)]
    y_axle = {"front": -D["length"] / 2 + D["overhang_front"]}
    y_axle["rear"] = y_axle["front"] + D["wheelbase"]
    arches, shifts = {}, {}
    for s in ("front", "rear"):
        A = np.array(raw["arch_m"][s]); wy, wz = raw["wheel_centres_m"][s]
        wzd = float(lev(wy, wz))
        arch = np.c_[y_axle[s] + b * (A[:, 0] - wy), D["wheel_radius"] + c * (lev(A[:, 0], A[:, 1]) - wzd)]
        # centre the opening on the axle exactly (mid of its front/rear edges 40-150 mm above the wheel centre)
        cen = [((edge_y_at(arch, z, "front") or np.nan) + (edge_y_at(arch, z, "rear") or np.nan)) / 2
               for z in np.linspace(D["wheel_radius"] + 0.04, D["wheel_radius"] + 0.15, 12)]
        arch[:, 0] += y_axle[s] - float(np.nanmean(cen))
        arches[s] = arch
        shifts[s] = {"dy_mm": round((y_axle[s] - (a + b * wy)) * 1000, 1),
                     "dz_mm": round((D["wheel_radius"] - c * (wzd - g)) * 1000, 1),
                     "picture_tyre_radius_m": round(c * (wzd - g), 4)}
    params = {"roll_slope": k, "ground_m": g, "a": a, "b": b, "c": c, "arch_shift": shifts}
    return outline, arches, y_axle, params


def edge_object(name, coll, pts, closed, x=0.0):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    bm = bmesh.new()
    vs = [bm.verts.new((x, float(y), float(z))) for y, z in pts]
    for i in range(len(vs) - (0 if closed else 1)):
        bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.display_type = "WIRE"; ob.hide_render = True
    clean_mesh(ob)
    return ob


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


def ordered_loop(ob):
    """Vertex coordinates (y, z) walked along the edges; also returns whether the chain is a single closed loop."""
    me = ob.data
    adj = {v.index: [] for v in me.vertices}
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)
    degs = [len(n) for n in adj.values()]
    start = next((i for i, n in adj.items() if len(n) == 1), 0)
    order, prev, cur = [start], None, start
    while True:
        nxt = [n for n in adj[cur] if n != prev]
        if not nxt or nxt[0] == start:
            break
        prev, cur = cur, nxt[0]
        order.append(cur)
    co = np.array([(me.vertices[i].co.y, me.vertices[i].co.z) for i in order])
    return co, degs


def self_intersections(P):
    """Count proper crossings between non-adjacent segments of a closed polyline (2D, vectorised per segment)."""
    A, B = P, np.roll(P, -1, 0)
    n = len(P); hits = 0
    for i in range(n):
        p, r = A[i], B[i] - A[i]
        q, s = A, B - A
        den = r[0] * s[:, 1] - r[1] * s[:, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = ((q[:, 0] - p[0]) * s[:, 1] - (q[:, 1] - p[1]) * s[:, 0]) / den
            u = ((q[:, 0] - p[0]) * r[1] - (q[:, 1] - p[1]) * r[0]) / den
        ok = (np.abs(den) > 1e-12) & (t > 1e-9) & (t < 1 - 1e-9) & (u > 1e-9) & (u < 1 - 1e-9)
        idx = np.arange(n)
        ok &= (idx != i) & (idx != (i + 1) % n) & (idx != (i - 1) % n)
        hits += int(ok.sum())
    return hits // 2


def edge_y_at(chain, z, side):
    """y of the arch chain's front (min) or rear (max) side at height z."""
    ys = []
    for (y0, z0), (y1, z1) in zip(chain[:-1], chain[1:]):
        if min(z0, z1) <= z <= max(z0, z1) and z1 != z0:
            ys.append(y0 + (y1 - y0) * (z - z0) / (z1 - z0))
    if not ys:
        return None
    return min(ys) if side == "front" else max(ys)


def audit(D, objs, y_axle):
    rows, bad = [], []

    def check(name, meas, spec, tol=TOL, cmp="eq"):
        if cmp == "eq":
            okk = abs(meas - spec) < tol
        elif cmp == "ge":
            okk = meas >= spec
        else:
            okk = meas <= spec
        rows.append("%-46s %9.4f %9.4f %s" % (name, meas, spec, "" if okk else " <-- FAIL"))
        if not okk:
            bad.append(name)

    P, degs = ordered_loop(objs["Profile_Side"])
    check("outline: nose y", P[:, 0].min(), -D["length"] / 2)
    check("outline: tail y", P[:, 0].max(), D["length"] / 2)
    check("outline: length", P[:, 0].max() - P[:, 0].min(), D["length"])
    check("outline: roof z (height)", P[:, 1].max(), D["height"])
    check("outline: lowest body point z >= 0.10", P[:, 1].min(), 0.10, cmp="ge")
    check("outline: closed loop (all vertex degree 2)", float(all(d == 2 for d in degs)), 1.0)
    check("outline: walk visits every vertex", float(len(P)), float(len(objs["Profile_Side"].data.vertices)))
    check("outline: self-intersections", float(self_intersections(P)), 0.0)
    for s in ("front", "rear"):
        A, _ = ordered_loop(objs["Arch_Profile_" + s.title()])
        zc = D["wheel_radius"]
        cen = []
        for z in np.linspace(zc + 0.04, zc + 0.15, 12):
            yf, yr = edge_y_at(A, z, "front"), edge_y_at(A, z, "rear")
            if yf is not None and yr is not None:
                cen.append((yf + yr) / 2)
        check("%s arch: centre y (z %.2f-%.2f) vs axle" % (s, zc + 0.04, zc + 0.15), float(np.mean(cen)), y_axle[s])
        check("%s arch: top above tyre top (>= %d mm)" % (s, MIN_ARCH_CLEARANCE * 1000),
              A[:, 1].max() - 2 * D["wheel_radius"], MIN_ARCH_CLEARANCE, cmp="ge")
        zlo = max(zc, max(A[0, 1], A[-1, 1]) + 0.005)          # lowest height where both sides of the lip exist
        yf, yr = edge_y_at(A, zlo, "front"), edge_y_at(A, zlo, "rear")
        dz = zlo - zc
        tyre_half = math.sqrt(max(D["wheel_radius"] ** 2 - dz * dz, 0.0))
        check("%s arch: half-opening - tyre at z %.3f" % (s, zlo), min(y_axle[s] - yf, yr - y_axle[s]) - tyre_half,
              MIN_ARCH_SIDE_CLEARANCE, cmp="ge")
        check("%s arch: inside the outline (top below roof)" % s, A[:, 1].max(), P[:, 1].max(), cmp="le")
    for s in ("front", "rear"):
        W, _ = ordered_loop(objs["Wheel_Guide_" + s.title()])
        r = np.hypot(W[:, 0] - y_axle[s], W[:, 1] - D["wheel_radius"])
        check("%s wheel guide: radius" % s, float(r.mean()), D["wheel_radius"])
        check("%s wheel guide: touches ground (min z)" % s, float(W[:, 1].min()), 0.0)
    print("NOVA GTE PHASE 2 - SIDE PROFILE VERIFICATION")
    print("%-46s %9s %9s" % ("check", "measured", "spec/limit"))
    print("\n".join(rows))
    if bad:
        raise NovaSpecError("failed: " + "; ".join(bad))
    print("RESULT: PASS")


def main():
    D = dims()
    raw = json.load(open(RAW))
    outline, arches, y_axle, params = fit(D, raw)
    coll = bpy.data.collections["NOVA_PROC"]
    objs = {"Profile_Side": edge_object("Profile_Side", coll, outline, True)}
    for s in ("front", "rear"):
        a = arches[s]
        if a[0, 0] > a[-1, 0]:
            a = a[::-1]                                      # front-low -> top -> rear-low
        objs["Arch_Profile_" + s.title()] = edge_object("Arch_Profile_" + s.title(), coll, a, False)
        t = np.linspace(0, 2 * math.pi, 97)[:-1]
        circ = np.c_[y_axle[s] + D["wheel_radius"] * np.cos(t), D["wheel_radius"] + D["wheel_radius"] * np.sin(t)]
        objs["Wheel_Guide_" + s.title()] = edge_object("Wheel_Guide_" + s.title(), coll, circ, True)
    bpy.context.scene["nova_gte_profile"] = {
        "source": raw["source"], "roll_slope": params["roll_slope"], "ground_m": params["ground_m"],
        "scale_y": params["b"], "scale_z": params["c"], "offset_y": params["a"],
        "front_arch_dy_mm": params["arch_shift"]["front"]["dy_mm"], "front_arch_dz_mm": params["arch_shift"]["front"]["dz_mm"],
        "rear_arch_dy_mm": params["arch_shift"]["rear"]["dy_mm"], "rear_arch_dz_mm": params["arch_shift"]["rear"]["dz_mm"],
        "picture_tyre_radius_m": params["arch_shift"]["front"]["picture_tyre_radius_m"]}
    print("fit: scale y %.4f, z %.4f; roll slope %.5f; arch shifts %s" % (params["b"], params["c"], params["roll_slope"],
                                                                        params["arch_shift"]))
    audit(D, objs, y_axle)
    bpy.ops.wm.save_mainfile()
    print("saved", bpy.data.filepath)


if __name__ == "__main__":
    main()
