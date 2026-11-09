"""Put glass in the apertures.

Every opening is cut right through a one-skin body at the moment, so the car is see-through and reads as a
shell rather than a car. `tools/gen/roll_edges.py` has already turned each aperture's edge back into a rebate -
the step the glass sits in on the real car - so the glass is simply the innermost ring of that rebate, filled.

That is the point: the glass is not modelled from coordinates of its own. It is taken from the hole the body
makes, so it can never disagree with it. For each aperture the script walks the finished mesh's boundary loop
(which, after the rolls, is the back of the rebate), sorts it into order, pushes it in a little further to the
seal depth, and fills it.

Which loop is which is decided by where its centre is, against the outlines the car is built from:
blender/data/windows.json for the two side windows and the triangulated WS_B/WS_T and HG_B/HG_T for the
windscreen and the hatch.

blender -b in.blend --python tools/gen/add_glass.py -- out.blend
"""
import json
import os
import sys
from collections import defaultdict

import bmesh
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = args[0] if args and not args[0].startswith("--") else None
ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
D = os.path.join(ROOT, "blender", "data")
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
BA = json.load(open(os.path.join(ROOT, "tools", "photomatch", "ba_result.json")))["points"]
WIN = json.load(open(os.path.join(D, "windows.json")))
DZ = float(PF["dz"])
SEAL = 0.004          # how much further in than the rebate the glass sits
SRC = ("Body_Shell", "PANEL_R_L", "PANEL_R_R")


def centre_of(pts):
    a = np.array(pts, float)
    return a.mean(axis=0)


def win_box(name):
    a = np.array(WIN[name], float)
    return a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max()


BOX = {k: win_box(k) for k in ("door", "quarter")}
WS = (min(WS_B_Y := BA["WS_B"][1], WS_T_Y := BA["WS_T"][1]), max(WS_B_Y, WS_T_Y),
      BA["WS_T"][2] + DZ, BA["WS_B"][2] + DZ)
HG = (min(BA["HG_T"][1], BA["HG_B"][1]), max(BA["HG_T"][1], BA["HG_B"][1]))


def which(c, obj):
    x, y, z = c
    ax = abs(x)
    if obj.startswith("PANEL_R"):
        return "hatch" if HG[0] - 0.08 < y < HG[1] + 0.08 else None
    for k, (y0, y1, z0, z1) in BOX.items():
        if y0 - 0.05 < y < y1 + 0.05 and z0 - 0.05 < z < z1 + 0.05 and ax > 0.30:
            return k
    if ax < 0.62 and WS[0] - 0.12 < y < WS[1] + 0.12 and z > 0.85:
        return "screen"
    return None


def loops_of(bm):
    """Closed boundary loops, plus half-loops that run from the mirror plane back to it - the windscreen and
    the hatch glass straddle the centreline, and the shell is a half model, so their apertures come out as
    open chains with both ends on x = 0. Those are closed along the centreline before filling."""
    be = [e for e in bm.edges if e.is_boundary]
    nb = defaultdict(list)
    for e in be:
        nb[e.verts[0]].append(e)
        nb[e.verts[1]].append(e)
    out = []
    seen = set()
    ends = [v for v in nb if len(nb[v]) == 1 or abs(v.co.x) < 1e-4]
    for start in ends + [e.verts[0] for e in be]:
        if start in seen:
            continue
        for e0 in nb[start]:
            if e0 in seen:
                continue
            order = [start]
            edge, cur = e0, e0.other_vert(start)
            chain_edges = [e0]
            while True:
                order.append(cur)
                if cur is start:
                    break
                nxt = [e for e in nb[cur] if e is not edge and e not in chain_edges]
                if len(nxt) != 1:
                    break
                edge = nxt[0]
                chain_edges.append(edge)
                cur = edge.other_vert(cur)
            closed = order[-1] is start
            on_axis = abs(order[0].co.x) < 1e-3 and abs(order[-1].co.x) < 1e-3
            if len(order) > 40 and (closed or on_axis):
                seen.update(chain_edges)
                seen.add(start)
                out.append(order[:-1] if closed else order)
    return out


def glass_mat():
    m = bpy.data.materials.get("glass_tinted")
    if m is None:
        m = bpy.data.materials.new("glass_tinted")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.055, 0.065, 0.075, 1)
    b.inputs["Roughness"].default_value = 0.06
    for k, val in (("Transmission Weight", 0.80), ("IOR", 1.52), ("Metallic", 0.0)):
        if k in b.inputs:
            b.inputs[k].default_value = val
    m.diffuse_color = (0.055, 0.065, 0.075, 1)
    m.use_backface_culling = False
    return m


coll = bpy.data.collections.get("NOVA_NEW") or bpy.context.scene.collection
mat = glass_mat()
found = defaultdict(list)
for name in SRC:
    ob = bpy.data.objects.get(name)
    if not ob:
        continue
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    for order in loops_of(bm):
        pts = [tuple(ob.matrix_world @ v.co) for v in order]
        nrm = [(v.normal.copy()) for v in order]
        c = centre_of(pts)
        k = which(c, name)
        if k is None:
            continue
        found[k].append((pts, nrm, c, name))
    bm.free()

# The windscreen does not come out as a loop of its own: on the half-model its aperture runs into the shell's
# other open edges, so it is gathered differently - every boundary vertex that lies along the measured screen
# line, ordered round the centroid in the screen's own plane and filled. The outline is still the body's own
# hole, not a shape invented for the glass.
def screen_pane():
    ob = bpy.data.objects.get("Body_Shell")
    if not ob:
        return None
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    P0 = np.array([BA["WS_B"][1], BA["WS_B"][2] + DZ])
    P1 = np.array([BA["WS_T"][1], BA["WS_T"][2] + DZ])
    Dv = (P1 - P0) / np.linalg.norm(P1 - P0)
    Nv = np.array([-Dv[1], Dv[0]])
    L = float(np.linalg.norm(P1 - P0))
    pick = []
    # 2026-10-27 (17): the screen is curved in plan - its base is ~80 mm further forward at the centre than at the
    # corner (body_profile scuttle_curve: y = yb0 + k x^2) - so a straight WS_B-WS_T line missed the middle of the
    # bottom edge and the pane came out as two outer wedges with a triangle hole between. Each point is moved back
    # along y by the plan curve to the corner's station before it is tested against the line. The header at the top
    # is straight across in plan (y ~ -0.22 at the centre and at WS_T), so the correction fades out with height.
    _k = float(PF["scuttle_curve"]["k"]); _xb = float(BA["WS_B"][0])
    for v in bm.verts:
        if not any(e.is_boundary for e in v.link_edges):
            continue
        _s = min(max(float((np.array([v.co.y, v.co.z]) - P0) @ Dv) / L, 0.0), 1.0)
        q = np.array([v.co.y - _k * (v.co.x ** 2 - _xb ** 2) * (1.0 - _s), v.co.z]) - P0
        t = float(q @ Dv)
        if abs(float(q @ Nv)) < 0.055 and -0.02 < t < L + 0.02 and abs(v.co.x) < 0.60:
            pick.append(v)
    if len(pick) < 12:
        bm.free()
        return None
    pts = np.array([[v.co.x, v.co.y, v.co.z] for v in pick])
    nrm = np.array([[v.normal.x, v.normal.y, v.normal.z] for v in pick]).mean(axis=0)
    nrm /= np.linalg.norm(nrm)
    c = pts.mean(axis=0)
    e1 = np.cross(nrm, [0, 0, 1.0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    ang = np.arctan2((pts - c) @ e2, (pts - c) @ e1)
    order = np.argsort(ang)
    bm.free()
    return pts[order], nrm


made = 0
if "screen" not in found:
    _sp = screen_pane()
    if _sp is not None:
        _pts, _n = _sp
        found["screen"] = [([tuple(p) for p in _pts], [Vector(_n)] * len(_pts), _pts.mean(axis=0), "Body_Shell")]

for kind, items in found.items():
    for idx, (pts, nrm, c, src) in enumerate(items):
        n_avg = Vector((0, 0, 0))
        for n in nrm:
            n_avg += n
        if n_avg.length < 1e-9:
            continue
        n_avg.normalize()
        bm = bmesh.new()
        if abs(pts[0][0]) < 1e-3 and abs(pts[-1][0]) < 1e-3 and len(pts) > 2:
            pts = [(0.0, p[1], p[2]) if i in (0, len(pts) - 1) else p for i, p in enumerate(pts)]
        # 2026-10-27 (17): a proper polygon fill, not a fan. The fan from the centroid left wedges uncovered
        # wherever the outline was not star-shaped round that point - on the half-model screen and hatch that
        # was the big see-through triangle at the centreline in every front and rear view. The outline is
        # flattened onto the pane's own plane and triangulated as a polygon (mathutils tessellate_polygon, which
        # handles concave outlines); the triangles keep the 3D points, so the pane still follows the opening.
        # An angle-sorted outline (the screen) is first rotated so it starts and ends at the centreline gap -
        # the polygon's closing edge then runs along x = 0, which is where the half pane is meant to close.
        if kind == "screen" and len(pts) > 3:
            P = np.array(pts, float)
            gaps = [np.linalg.norm(P[(k + 1) % len(P)] - P[k]) if (abs(P[k][0]) < 0.06 and abs(P[(k + 1) % len(P)][0]) < 0.06)
                    else -1.0 for k in range(len(P))]
            kb = int(np.argmax(gaps))
            if gaps[kb] > 0:
                pts = [tuple(p) for p in np.roll(P, -(kb + 1), axis=0)]
                # the shell's nearest column to the centreline is at x ~0.009, so the half pane stopped 9 mm short of
                # it and the two mirrored halves left an 18 mm crack down the middle - pull both ends onto x = 0
                pts = [(0.0, p[1], p[2]) if i in (0, len(pts) - 1) and abs(p[0]) < 0.03 else p for i, p in enumerate(pts)]
        from mathutils.geometry import tessellate_polygon
        e1 = n_avg.orthogonal().normalized(); e2 = n_avg.cross(e1).normalized()
        cv = Vector((float(c[0]), float(c[1]), float(c[2])))
        flat = [Vector(((Vector(p) - cv).dot(e1), (Vector(p) - cv).dot(e2), 0.0)) for p in pts]
        vs = [bm.verts.new(Vector(p) - n_avg * SEAL) for p in pts]
        for tri in tessellate_polygon([flat]):
            a, b2, c2 = (vs[i] for i in tri)
            if len({a, b2, c2}) < 3:
                continue
            try:
                bm.faces.new((a, b2, c2))
            except ValueError:
                pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
        if not bm.faces:
            bm.free()
            continue
        bm.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        if sum(fc.normal.dot(n_avg) for fc in bm.faces) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        side = "L" if c[0] > 0 else "R"
        # GLASS_ in capitals: the blocky leftovers are called Glass_* and must not be confused with these
        nm = "GLASS_%s_%s" % (kind.upper(), side)
        while bpy.data.objects.get(nm):
            bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
        me = bpy.data.meshes.new(nm)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mat)
        ob2 = bpy.data.objects.new(nm, me)
        coll.objects.link(ob2)
        # the shell and the rear panel are half-models with a Mirror modifier, so their apertures - and so the
        # panes taken from them - only exist on the left; mirror the glass the same way
        if any(m.type == "MIRROR" for m in bpy.data.objects[src].modifiers):
            mir = ob2.modifiers.new("Mirror", "MIRROR")
            mir.use_axis[0] = True
        made += 1
        print("%-20s %4d verts  centre (%.2f, %.2f, %.2f)  from %s" % (nm, len(me.vertices), *c, src))
print("glass: %d panes" % made)

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
