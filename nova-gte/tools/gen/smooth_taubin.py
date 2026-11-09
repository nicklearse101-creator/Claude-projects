"""Gentle smoothing of the Meshy shell: weld the UV-seam splits, then Taubin (lambda/mu, no shrink) Laplacian
smoothing with the displacement projected on the vertex normal (no sliding -> the texture stays put). Only open edges
(door cuts, arch openings, the hollow underside) are pinned. Smooth shading on. iters=0 gives the welded baseline.
blender -b nova_meshy.blend --python smooth_taubin.py -- iters out.blend"""
import sys

import bmesh
import bpy
import numpy as np

LAM, MU = 0.5, -0.53
# door outline (y, z) as cut by cut_doors.py, after prep's axle shift; doors and body stay matched along it
DOOR_POLY = [(-0.700, 0.305), (0.475, 0.305), (0.475, 0.865), (0.415, 0.865), (0.415, 1.265), (-0.195, 1.265),
             (-0.690, 0.860)]
EDGE_PIN = 0.025        # vertices this close (y-z) to the door outline stay put
WIN_Z = (0.89, 1.27)    # side-window glass band (flat already; smoothing folded it at the frames)


def near_outline(y, z):
    best = np.full(len(y), 9.0)
    for (a0, b0), (a1, b1) in zip(DOOR_POLY, DOOR_POLY[1:] + DOOR_POLY[:1]):
        dy, dz = a1 - a0, b1 - b0
        t = np.clip(((y - a0) * dy + (z - b0) * dz) / (dy * dy + dz * dz), 0, 1)
        best = np.minimum(best, np.hypot(y - (a0 + t * dy), z - (b0 + t * dz)))
    return best


def run(ob, iters):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bm.verts.index_update()
    pin = np.zeros(len(bm.verts), bool)
    for e in bm.edges:
        if not e.is_manifold:
            pin[e.verts[0].index] = pin[e.verts[1].index] = True
    E = np.array([(e.verts[0].index, e.verts[1].index) for e in bm.edges], np.int64)
    bm.to_mesh(ob.data); bm.free()
    me = ob.data
    if me.has_custom_normals:
        me.free_normals_split() if hasattr(me, "free_normals_split") else None
        bpy.context.view_layer.objects.active = ob
        try:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except RuntimeError:
            pass
    me.shade_smooth() if hasattr(me, "shade_smooth") else me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    deg = np.bincount(E.ravel(), minlength=len(pin)).astype(float)
    P = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", P); P = P.reshape(-1, 3)
    W = P @ np.array(ob.matrix_world)[:3, :3].T + np.array(ob.matrix_world)[:3, 3]      # world positions
    me.update()
    n0 = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("normal", n0); n0 = n0.reshape(-1, 3)
    pin |= (near_outline(W[:, 1], W[:, 2]) < EDGE_PIN) & (np.abs(W[:, 0]) > 0.3)
    pin |= (np.abs(n0[:, 0]) > 0.6) & (W[:, 2] > WIN_Z[0]) & (W[:, 2] < WIN_Z[1])

    def normals():
        me.vertices.foreach_set("co", P.ravel()); me.update()
        n = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("normal", n)
        return n.reshape(-1, 3).astype(float)
    N = normals()
    for k in range(iters):
        for f in (LAM, MU):
            S = np.zeros_like(P)
            np.add.at(S, E[:, 0], P[E[:, 1]]); np.add.at(S, E[:, 1], P[E[:, 0]])
            L = S / np.maximum(deg, 1)[:, None] - P
            L[deg == 0] = 0
            d = (L * N).sum(1)[:, None] * N
            d[pin] = 0
            P += f * d
        if k % 5 == 4:
            N = normals()
    normals()
    return {"verts": len(P), "pinned_open_edges": int(pin.sum())}


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    for n in ("Meshy_Body", "DOOR_L", "DOOR_R"):
        print(n, run(bpy.data.objects[n], int(a[0])))
    bpy.ops.wm.save_as_mainfile(filepath=a[1], copy=True)
