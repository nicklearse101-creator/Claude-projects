"""Roll every open edge of the body under itself, instead of leaving it as a cut.

This is the thing that makes the front bumper read as a pressing and the rest of the car read as paper. The
bumper is a 40-row cross-section swept along a spline path (tools/front_end.py), and the first and last rows of
that section are *returns*: the surface turns through most of 180 degrees and runs back behind itself, so there
is no raw edge anywhere on it. Every other panel here was a single skin whose boundary was simply where the
faces stopped - a wheel arch cut straight through a 1-face-thick shell, a window aperture the same.

So each open boundary is given its own little swept section. For every boundary vertex the script builds a
frame on the surface:

    n   the surface normal (outwards)
    t   along the boundary
    h   n x t, flipped so it points AWAY from the mesh - "into the opening"

and then walks a profile of (d, e) pairs, d along h and e behind the surface (-n), making one ring of vertices
per profile row and stitching the rings into quads. Which profile an edge gets is decided by where it is:

    arch        rolls over the lip and turns back inboard into the wheel well
    window      steps back into the frame rebate the glass sits in
    screen      the same, a little deeper, for the windscreen and the hatch glass
    floor       the shell's bottom edge, folded flat inboard under the car
    hem         a short fold back, for the free edges of the bonnet, wings, scuttle, skirt and rear panel

Classification is by distance to the aperture outlines the car is actually built from - body_profile
arch_shapes, blender/data/windows.json, and the screen and hatch corners - not by guessed coordinates.

blender -b in.blend --python tools/gen/roll_edges.py -- out.blend
"""
import json
import math
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

# (d along the surface into the opening, e behind the surface). Row 0 is the edge itself.
PROFILES = {
    "arch":   [(0.000, 0.000), (0.0035, 0.0010), (0.0050, 0.0040), (0.0050, 0.0100),
               (0.0020, 0.0180), (-0.0050, 0.0280), (-0.0160, 0.0330)],
    "window": [(0.000, 0.000), (0.0015, 0.0030), (0.0020, 0.0080), (0.0010, 0.0130),
               (-0.0060, 0.0155), (-0.0150, 0.0160)],
    "screen": [(0.000, 0.000), (0.0015, 0.0035), (0.0020, 0.0095), (0.0005, 0.0150),
               (-0.0070, 0.0175), (-0.0170, 0.0180)],
    "floor":  [(0.000, 0.000), (0.0020, 0.0030), (0.0000, 0.0070), (-0.0120, 0.0085), (-0.0320, 0.0090)],
    "hem":    [(0.000, 0.000), (0.0008, 0.0018), (0.0000, 0.0045), (-0.0035, 0.0058), (-0.0090, 0.0062)],
    # a panel edge that butts against another panel is a shut line, not a free edge: it only turns under far
    # enough to stop the skin reading as paper, and never out into the gap
    # A panel edge that butts against another panel is a shut line, not a free edge. The edge itself is pulled
    # back SHUT_GAP along the surface so there is a real gap to see, then turned under; the panel on the other
    # side of the gap gets the same treatment, so the two returns make a shadow line the width of the gap.
    "shut":   [(0.000, 0.000), (-0.0006, 0.0016), (-0.0022, 0.0034), (-0.0065, 0.0040)],
}
SHUT_GAP = 0.0022      # half the panel gap, each side: a 4.4 mm shut line
MAT = {"arch": "trim_black", "window": "trim_black", "screen": "trim_black",
       "floor": "trim_black", "hem": None, "shut": None}


def poly(a, dz=0.0):
    b = np.array(a, float)
    b[:, 1] += dz
    return b


ARCH = {k: poly(PF["arch_shapes"][k], DZ) for k in ("front", "rear")}
WINS = {k: np.array(WIN[k], float) for k in ("door", "quarter")}
WS_B, WS_T = BA["WS_B"], BA["WS_T"]
HG_B, HG_T = BA["HG_B"], BA["HG_T"]


def dist_to(pl, y, z):
    q = np.array([y, z])
    a, b = pl[:-1], pl[1:]
    ab = b - a
    tt = np.clip(np.einsum("ij,ij->i", q - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0, 1)
    p = a + ab * tt[:, None]
    return float(np.min(np.linalg.norm(p - q, axis=1)))


def seg_dist(p0, p1, y, z):
    a, b = np.array(p0), np.array(p1)
    ab = b - a
    t = np.clip(np.dot(np.array([y, z]) - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
    return float(np.linalg.norm(a + t * ab - np.array([y, z])))


# Only the shell carries the apertures. A separate panel whose edge happens to pass near one was being given a
# deep window or screen return, which stuck out into the opening as a flap - the wing beside the screen, the
# rear panel round the hatch glass. Those panels get a hem or a shut return and nothing else.
APERTURE_PART = "Body_Shell"
HATCH_PART = ("PANEL_R_L", "PANEL_R_R")


def classify(co, obj_name):
    x, y, z = co.x, co.y, co.z
    ax = abs(x)
    shell = obj_name == APERTURE_PART
    if obj_name in HATCH_PART and seg_dist((HG_B[1], HG_B[2] + DZ), (HG_T[1], HG_T[2] + DZ), y, z) < 0.040 and ax < 0.56:
        return "screen"
    if z < 0.26 and ax > 0.30:
        if dist_to(ARCH["front"], y, z) < 0.030 or dist_to(ARCH["rear"], y, z) < 0.030:
            return "arch"
        return "floor"
    if ax > 0.30:
        if dist_to(ARCH["front"], y, z) < 0.030 or dist_to(ARCH["rear"], y, z) < 0.030:
            return "arch"
        if shell and (dist_to(WINS["door"], y, z) < 0.030 or dist_to(WINS["quarter"], y, z) < 0.030):
            return "window"
    if shell and seg_dist((WS_B[1], WS_B[2] + DZ), (WS_T[1], WS_T[2] + DZ), y, z) < 0.050 and ax < 0.58:
        return "screen"
    if shell and seg_dist((HG_B[1], HG_B[2] + DZ), (HG_T[1], HG_T[2] + DZ), y, z) < 0.050 and ax < 0.58:
        return "screen"
    if z < 0.30:
        return "floor"
    return "hem"


def material(ob, name):
    if name is None:
        return 0
    for i, m in enumerate(ob.data.materials):
        if m and m.name == name:
            return i
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
        b.inputs["Roughness"].default_value = 0.65
        m.diffuse_color = (0.02, 0.02, 0.02, 1)
    ob.data.materials.append(m)
    return len(ob.data.materials) - 1


def already_folded(e, limit=math.radians(52)):
    """True if the surface has already turned over at this boundary - the wing and the sill build their own
    arch lips, and rolling those a second time is what put flaps along them. Compares the boundary face's
    normal with the one behind it: on a flat skin they agree, on a return they do not."""
    if not e.link_faces:
        return False
    f0 = e.link_faces[0]
    best = 0.0
    for ed in f0.edges:
        if ed is e:
            continue
        for f1 in ed.link_faces:
            if f1 is f0:
                continue
            best = max(best, f0.normal.angle(f1.normal, 0.0))
    return best > limit


def other_bvh(ob, parts):
    """A BVH of every other body part, so an edge that butts against one can be told from a free edge."""
    from mathutils.bvhtree import BVHTree
    verts, tris = [], []
    for o in parts:
        if o is ob:
            continue
        me = o.data
        n0 = len(verts)
        verts += [tuple(o.matrix_world @ v.co) for v in me.vertices]
        for f in me.polygons:
            vs = list(f.vertices)
            for k in range(1, len(vs) - 1):
                tris.append((n0 + vs[0], n0 + vs[k], n0 + vs[k + 1]))
    return BVHTree.FromPolygons(verts, tris) if tris else None


def roll(ob, bvh=None):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    be = [e for e in bm.edges if e.is_boundary]
    if not be:
        bm.free()
        return 0, {}
    # ordered neighbours along the boundary, so the tangent follows the opening rather than the mesh grid
    folded = {v for e in be if already_folded(e) for v in e.verts}
    be = [e for e in be if e.verts[0] not in folded and e.verts[1] not in folded]
    if not be:
        bm.free()
        return 0, {}
    nb = defaultdict(list)
    for e in be:
        nb[e.verts[0]].append(e.verts[1])
        nb[e.verts[1]].append(e.verts[0])
    bverts = list(nb)
    kinds = {}
    frame = {}
    for v in bverts:
        ns = nb[v]
        t = (ns[0].co - ns[-1].co) if len(ns) > 1 else (ns[0].co - v.co)
        if t.length < 1e-9:
            t = Vector((0, 1, 0))
        t.normalize()
        n = v.normal.copy()
        if n.length < 1e-9:
            n = Vector((0, 0, 1))
        n.normalize()
        h = n.cross(t)
        if h.length < 1e-9:
            continue
        h.normalize()
        inward = Vector((0, 0, 0))
        for f in v.link_faces:
            inward += (f.calc_center_median() - v.co)
        if inward.dot(h) > 0:          # h points into the mesh: flip it so it points into the opening
            h = -h
        frame[v] = (h, n)
        k = classify(v.co, ob.name)
        if k == "hem" and bvh is not None:
            loc, _, _, dd = bvh.find_nearest(v.co, 0.012)
            if loc is not None:
                k = "shut"
        kinds[v] = k
    made = 0
    counts = defaultdict(int)
    for kind in PROFILES:
        prof = PROFILES[kind]
        vs = [v for v in bverts if kinds.get(v) == kind and v in frame]
        if not vs:
            continue
        mi = material(ob, MAT[kind])
        if kind == "shut":
            for v in vs:
                h, _n = frame[v]
                v.co -= h * SHUT_GAP
        ring = {v: [v] for v in vs}
        for d, e in prof[1:]:
            for v in vs:
                h, n = frame[v]
                ring[v].append(bm.verts.new(v.co + h * d - n * e))
        for ed in be:
            a, b = ed.verts
            if kinds.get(a) != kind or kinds.get(b) != kind or a not in ring or b not in ring:
                continue
            for k in range(len(prof) - 1):
                try:
                    f = bm.faces.new((ring[a][k], ring[b][k], ring[b][k + 1], ring[a][k + 1]))
                except ValueError:
                    continue
                f.material_index = mi
                made += 1
            counts[kind] += 1
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return made, counts


coll = bpy.data.collections.get("NOVA_NEW")
targets = [o for o in (coll.objects if coll else bpy.data.objects)
           if o.type == "MESH" and len(o.data.polygons) and not o.name.startswith(("BUMPER_", "GRILLE_", "HEADLAMP_", "INDICATOR_", "PLATE_", "LAMP_PANEL", "TAILLAMP_",
                                                                                 # the previous build's gutter is still in the blend here; it is rebuilt after this step and must not
                                                                                 # be rolled or count as a neighbouring panel (2026-10-27 (14))
                                                                                 "SHUT_GUTTER",
                                                                                 # likewise parts built after this step (add_mirrors, add_wheels)
                                                                                 "MIRROR_", "WHEEL_", "TIRE_", "RIM_", "DISK_"))]
total = 0
for ob in sorted(targets, key=lambda o: o.name):
    made, counts = roll(ob, other_bvh(ob, targets))
    if made:
        total += made
        print("%-18s %5d faces added  (%s)" % (ob.name, made, ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
print("rolled edges: %d faces added over %d parts" % (total, len(targets)))

if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath(OUT))
    print("saved", OUT)
