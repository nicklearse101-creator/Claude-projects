"""Window frames, windscreen rubber and tailgate seal as strips of their own (MODEL_TODO 12); runs after
prep_reference.py. Colouring whole body faces (10-25 mm) near the openings gave ragged bands; these strips follow
the measured opening outlines, so their edges are clean whatever the mesh does underneath.

Side windows (door, vent, quarter; left scan, mirrored for the right): outline = the opening's column outline
(prep_reference.side_apertures), smoothed. Strip: a lip wall from the glass plane up to the skin at the opening's
edge, then 15 mm out over the skin (cS photo: black frames ~14 mm), 0.6 mm proud.
Windscreen: black rubber from 8 mm in on the glass to 22 mm out onto the body. Tailgate: black seal on the glass
edge, 26 mm wide (12 mm of it under the frame).
Car frame: x+ = car's left, y- = front, z up.
"""
import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import prep_reference as pr

FRAME_W, PROUD, STEP = 0.015, 0.0006, 0.005


def _smooth(a, k):
    p = np.pad(a, (k, k), mode="edge")
    return np.convolve(p, np.ones(2 * k + 1) / (2 * k + 1), mode="valid")


def _outline(cols):
    """Closed 2D outline (u, v) from the column outline: bottom left -> right, top right -> left (counter-clockwise),
    smoothed over ~2 cm and resampled every STEP."""
    c = np.array(cols)
    u, lo, hi = c[:, 0], _smooth(c[:, 1], 4), _smooth(c[:, 2], 4)
    P = np.concatenate([np.stack([u, lo], 1), np.stack([u[::-1], hi[::-1]], 1)])
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(0, s[-1], STEP)
    Q = np.stack([np.interp(t, s, np.append(P[:, 0], P[0, 0])), np.interp(t, s, np.append(P[:, 1], P[0, 1]))], 1)
    T = np.roll(Q, -1, 0) - np.roll(Q, 1, 0)
    N = np.stack([T[:, 1], -T[:, 0]], 1)
    for _ in range(3):                                           # round the corners of the offset a little
        N = (np.roll(N, 1, 0) + 2 * N + np.roll(N, -1, 0)) / 4
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    return Q, N


def _strips(bm, rings, mat, outward):
    """Quads between consecutive closed rings; each strip flipped to face outward(centre of its first face)."""
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        fs = [bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k])) for k in range(n)]
        f0 = max(fs, key=lambda f: f.calc_area()); f0.normal_update()
        if f0.normal.dot(outward(f0.calc_center_median())) < 0:
            bmesh.ops.reverse_faces(bm, faces=fs)
        for f in fs:
            f.material_index = mat; f.smooth = False


def _object(name, bm, mats):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.data.collections["REF"].objects.link(o)
    return o


def side_frames(bvh):
    out = {}
    black = bpy.data.materials["trim_black"]
    for name, (m, cols, surf, err) in pr.side_apertures().items():
        Q, N = _outline(cols)

        def skin(p2, fallback):
            hit = bvh.ray_cast(Vector((1.5, p2[0], p2[1])), Vector((-1, 0, 0)), 1.5)
            x = hit[0].x if hit[0] is not None else None
            return x if x is not None and abs(x - fallback) < 0.03 else fallback

        lip, edge, outer = [], [], []
        for q, n in zip(Q, N):
            xf = float(surf(q[0], q[1]))                                  # fitted frame surface (skin plane)
            lip.append((xf - pr.INSET - 0.001, q[0], q[1]))
            pe = q + n * 0.004
            edge.append((skin(pe, xf) + PROUD, q[0], q[1]))
            po = q + n * FRAME_W
            outer.append((skin(po, xf) + PROUD, po[0], po[1]))
        for side, sx in (("L", 1), ("R", -1)):
            bm = bmesh.new()
            rings = [[bm.verts.new((sx * x, y, z)) for x, y, z in r] for r in (lip, edge, outer)]
            cy, cz = Q[:, 0].mean(), Q[:, 1].mean()
            # lip wall faces into the opening; the band on the skin faces outward (+x on the left)
            _strips(bm, rings[:2], 0, lambda c: Vector((0, cy - c.y, cz - c.z)))
            _strips(bm, rings[1:], 0, lambda c: Vector((sx, 0, 0)))
            out[f"{name}_{side}"] = len(_object(f"DET_FRAME_{name}_{side}", bm, [black]).data.polygons)
    return out


def _boundary_loop(o):
    """Ordered outer boundary of a glass pane (world coords, vertex normals)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
    bm.normal_update()
    bedges = [e for e in bm.edges if e.is_boundary]
    nxt = {}
    for e in bedges:
        a, b = e.verts
        nxt.setdefault(a, []).append(b); nxt.setdefault(b, []).append(a)
    start = bedges[0].verts[0]
    loop, prev, cur = [start], None, start
    while True:
        cand = [v for v in nxt[cur] if v is not prev]
        if not cand or cand[0] is start:
            break
        prev, cur = cur, cand[0]
        loop.append(cur)
    P = np.array([v.co[:] for v in loop]); Nn = np.array([v.normal[:] for v in loop])
    bm.free()
    return P, Nn


def glass_band(bvh, glass, name, w_in, w_out, mat, on_body):
    """Black band round a glass pane: from w_in inside its edge (on the glass) to w_out outside it - laid onto the
    body along the pane normal when on_body, else kept on the glass plane."""
    P, Nn = _boundary_loop(bpy.data.objects[glass])
    cen = P.mean(0)
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    O = np.cross(T, Nn)
    O /= np.maximum(np.linalg.norm(O, axis=1, keepdims=True), 1e-9)
    if (O * (P - cen)).sum() < 0:
        O = -O
    for _ in range(2):
        O = (np.roll(O, 1, 0) + 2 * O + np.roll(O, -1, 0)) / 4
    O /= np.linalg.norm(O, axis=1, keepdims=True)
    # the pane's normal may point either way: make it point out of the car (away from the cabin centre)
    if (Nn * (P - np.array([0, 0.3, 0.8]))).sum() < 0:
        Nn = -Nn
    rings = [P - O * w_in + Nn * 0.0008, P + Nn * 0.0008]
    if on_body:
        R = []
        for p, o, n in zip(P, O, Nn):
            q = Vector(p + o * w_out)
            hit = bvh.ray_cast(q + Vector(n) * 0.06, -Vector(n), 0.12)
            R.append((hit[0] + hit[1].normalized() * 0.0008)[:] if hit[0] is not None else (q + Vector(n) * 0.0008)[:])
        rings.append(np.array(R))
    elif w_out > 0:
        rings.append(P + O * w_out + Nn * 0.0008)
    bm = bmesh.new()
    vr = [[bm.verts.new(tuple(p)) for p in r] for r in rings]
    nmean = Vector(Nn.mean(0)).normalized()
    _strips(bm, vr, 0, lambda c: nmean)
    return len(_object(name, bm, [bpy.data.materials[mat]]).data.polygons)


def main():
    o = bpy.data.objects["REF_BODY"]
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    res = {"side": side_frames(bvh)}
    # (windscreen: glass + gasket rebuilt by windscreen_ref.py)
    res["tailgate"] = glass_band(bvh, "GLASS_TAILGATE", "DET_TG_SEAL", 0.026, 0.0, "rubber_black", False)
    return res


if __name__ == "__main__":
    print("==", main())
