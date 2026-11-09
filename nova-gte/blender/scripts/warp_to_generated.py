"""Warp the hand-built (procedural) car onto the shape of the AI-generated body, keeping its clean surfaces.

The generated mesh (nova_gen.blend: GEN_BODY + GEN_GLASS, fitted to the FIA dimensions on the same wheel positions)
has the right proportions but a lumpy surface; the procedural shell has clean panels, creases and details but
guessed shapes. So the generated body is used only as a measured template:
  1. control points = BODY_shell vertices (both halves); each looks along its normal (+-) for the generated surface
     (<= REACH, similar facing) -> an offset vector. Not near the wheels (arches stay on the wheels), not underneath;
  2. the offsets are smoothed over ~SIGMA_C so the generated lumps do not carry over, only the shape;
  3. every procedural mesh (shell, cutters, glass, bumpers, lamps, details, interior) moves by the smoothed offset
     field at its vertices (fading out away from the shell), so all parts stay together and keep their edges.
Run on a copy of nova_gte.blend:  blender -b nova_warp.blend --python-expr "...warp_to_generated.main()"
"""
import math
import os

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
GEN_BLEND = os.path.join(ROOT, "blender", "nova_gen.blend")
REACH = 0.15          # max search distance along the normal (m)
SIGMA_C = 0.12        # smoothing of the offsets between control points (0.07 let panel ripples through)
SIGMA_V = 0.10        # interpolation of the field at a vertex
FADE = (0.12, 0.30)   # field fades out from this distance to the nearest control point (interior centre stays)
SKIP_COLL = {"WHEELS", "HELPERS", "Collection", "GEN_REF", "GEN"}


def load_reference():
    names = ["GEN_BODY", "GEN_GLASS"]
    with bpy.data.libraries.load(GEN_BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    coll = bpy.data.collections.get("GEN_REF") or bpy.data.collections.new("GEN_REF")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    objs = []
    for o in dst.objects:
        if o is None:
            continue
        coll.objects.link(o)
        o.modifiers.clear()
        o.hide_render = True; o.hide_set(True); o["no_export"] = 1
        objs.append(o)
    verts, polys = [], []
    for o in objs:
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def wheel_centres():
    return [bpy.data.objects["WHEEL_" + t].matrix_world.translation.copy() for t in ("LF", "RF", "LR", "RR")]


def controls(bvh):
    sh = bpy.data.objects["BODY_shell"]
    M = sh.matrix_world
    N = M.to_3x3().inverted().transposed()
    wc = wheel_centres()
    pts, offs = [], []
    stats = {"no_hit": 0, "wheel": 0, "under": 0}
    for v in sh.data.vertices:
        p = M @ v.co
        n = (N @ v.normal).normalized()
        if n.z < -0.5:
            stats["under"] += 1; continue
        if any(abs(p.x) > 0.40 and (p.y - w.y) ** 2 + (p.z - w.z) ** 2 < 0.42 ** 2 for w in wc):
            stats["wheel"] += 1; continue
        best = None
        for d in (n, -n):
            h = bvh.ray_cast(p, d, REACH)
            if h[0] is not None and abs(h[1].dot(n)) > 0.6 and (best is None or h[3] < best[3]):
                best = h
        if best is None:
            stats["no_hit"] += 1; continue
        off = best[0] - p
        for s in (1, -1):                                     # both halves (the shell mesh is the x >= 0 half)
            if s == -1 and p.x < 0.002:
                continue
            pts.append(Vector((p.x * s, p.y, p.z)))
            offs.append(Vector((off.x * s, off.y, off.z)))
    stats["controls"] = len(pts)
    return pts, offs, stats


def smooth_field(pts, offs):
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    out = []
    r = 2.5 * SIGMA_C
    for p in pts:
        acc, wsum = Vector(), 0.0
        for co, j, dist in kd.find_range(p, r):
            w = math.exp(-0.5 * (dist / SIGMA_C) ** 2)
            acc += offs[j] * w; wsum += w
        out.append(acc / wsum)
    return kd, out


def field_at(kd, offs, p):
    found = kd.find_n(p, 24)
    if not found:
        return Vector()
    dmin = found[0][2]
    acc, wsum = Vector(), 0.0
    for co, j, dist in found:
        w = math.exp(-0.5 * (dist / SIGMA_V) ** 2) + 1e-12
        acc += offs[j] * w; wsum += w
    f = 1.0 if dmin <= FADE[0] else max(0.0, 1.0 - (dmin - FADE[0]) / (FADE[1] - FADE[0]))
    return acc / wsum * f


def warp_objects(kd, offs):
    moved = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.startswith(("CUT_arch", "COLLIDER", "GEN_")):
            continue
        if any(c.name in SKIP_COLL for c in o.users_collection):
            continue
        M = o.matrix_world
        Mi = M.inverted()
        mirrored = any(m.type == "MIRROR" for m in o.modifiers)
        wc = wheel_centres()
        for v in o.data.vertices:
            p = M @ v.co
            d = field_at(kd, offs, p)
            if abs(p.x) > 0.40:                               # arches stay put: the arch cutters / liners / wheels
                r = min(math.hypot(p.y - w.y, p.z - w.z) for w in wc)      # do not move (slivers otherwise)
                t = min(1.0, max(0.0, (r - 0.38) / 0.17))
                d *= t * t * (3 - 2 * t)
            if mirrored and abs(p.x) < 0.002:
                d.x = 0.0                                     # keep the mirror seam on the centreline
            v.co = Mi @ (p + d)
        o.data.update()
        moved += 1
    return moved


def spike_clean(obj_name="BODY_shell", xmax=0.80):
    """Geometry Nodes step before SmoothNormals: delete stray points outside the body width (Boolean slivers of the
    fixed arch cutters where the warped shell meets them)."""
    o = bpy.data.objects[obj_name]
    if "SpikeClean" in o.modifiers:
        return
    ng = bpy.data.node_groups.new("NOVA_spike_clean", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    pos, sep = N.new("GeometryNodeInputPosition"), N.new("ShaderNodeSeparateXYZ")
    ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
    gt = N.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = xmax
    de = N.new("GeometryNodeDeleteGeometry"); de.domain = "POINT"
    L.new(pos.outputs[0], sep.inputs[0]); L.new(sep.outputs[0], ab.inputs[0]); L.new(ab.outputs[0], gt.inputs[0])
    L.new(gi.outputs[0], de.inputs["Geometry"]); L.new(gt.outputs[0], de.inputs["Selection"])
    L.new(de.outputs[0], go.inputs[0])
    m = o.modifiers.new("SpikeClean", "NODES"); m.node_group = ng
    idx = next((i for i, mm in enumerate(o.modifiers) if mm.type == "DATA_TRANSFER"), len(o.modifiers) - 1)
    with bpy.context.temp_override(object=o):
        bpy.ops.object.modifier_move_to_index(modifier="SpikeClean", index=idx)


def main():
    bvh = load_reference()
    pts, offs, stats = controls(bvh)
    kd, sm = smooth_field(pts, offs)
    mags = sorted(o.length for o in sm)
    stats["offset_median_mm"] = round(1000 * mags[len(mags) // 2], 1)
    stats["offset_p95_mm"] = round(1000 * mags[int(len(mags) * 0.95)], 1)
    stats["objects_warped"] = warp_objects(kd, sm)
    spike_clean()
    return stats


if __name__ == "__main__":
    print("==", main())
