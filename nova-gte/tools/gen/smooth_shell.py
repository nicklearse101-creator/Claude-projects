"""Smooth the waviness out of the Meshy shell, keeping its shape lines and its texture.
Feature-preserving mesh denoising (Sun, Rosin, Martin, Langbein 2007, "Fast and effective feature-preserving mesh
denoising"): 1) face normals are averaged only with neighbouring faces whose normal is similar (weight
(n_i . n_j - T)^2 above the threshold T, area-weighted) - real edges (arch lips, window frames, bumper lines, door cuts)
separate faces that differ a lot, so they stay sharp; 2) the vertices are moved to fit the filtered normals.
Vertices move (almost) only along the surface normal, and the texture lives on the face corners, so it stays put.
glTF import splits vertices at every UV seam: they are welded first (WELD) so the surface is one piece.
Waviness metric: mean angle between each face normal and its neighbours' (deg).
blender -b nova_meshy.blend --python smooth_shell.py -- T normal_iters vertex_iters rounds [out.blend]"""
import sys

import bmesh
import bpy
import numpy as np

WELD = 1e-4


def weld(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    return n0 - len(ob.data.vertices)


def arrays(me):
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    T = np.empty(nt * 3, np.int64); me.loop_triangles.foreach_get("vertices", T); T = T.reshape(-1, 3)
    P = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", P)
    return T, P.reshape(-1, 3)


def face_geo(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    cr = np.cross(b - a, c - a)
    A = np.linalg.norm(cr, axis=1)
    N = cr / np.maximum(A, 1e-12)[:, None]
    return N, A / 2, (a + b + c) / 3


def edge_pairs(T):
    """Pairs of triangles sharing an edge."""
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    f = np.tile(np.arange(len(T)), 3)
    e.sort(1)
    key = e[:, 0] * (T.max() + 1) + e[:, 1]
    o = np.argsort(key, kind="stable"); key, f = key[o], f[o]
    same = key[1:] == key[:-1]
    return np.stack([f[:-1][same], f[1:][same]], 1)


def waviness(N, pairs):
    d = np.clip((N[pairs[:, 0]] * N[pairs[:, 1]]).sum(1), -1, 1)
    return float(np.degrees(np.arccos(d)).mean())


def denoise(ob, thr, n_it, v_it, rounds):
    me = ob.data
    welded = weld(ob)
    T, P = arrays(me)
    pairs = edge_pairs(T)
    N, A, C = face_geo(P, T)
    before = waviness(N, pairs)
    vf = np.concatenate([T[:, 0], T[:, 1], T[:, 2]]); ff = np.tile(np.arange(len(T)), 3)
    cnt = np.bincount(vf, minlength=len(P)).astype(float)
    for _ in range(rounds):
        N, A, C = face_geo(P, T)
        Nf = N.copy()
        for _ in range(n_it):
            dot = (Nf[pairs[:, 0]] * Nf[pairs[:, 1]]).sum(1)
            w = np.where(dot > thr, (dot - thr) ** 2, 0.0)
            S = Nf * A[:, None]                                   # the face itself
            np.add.at(S, pairs[:, 0], Nf[pairs[:, 1]] * (A[pairs[:, 1]] * w)[:, None])
            np.add.at(S, pairs[:, 1], Nf[pairs[:, 0]] * (A[pairs[:, 0]] * w)[:, None])
            Nf = S / np.maximum(np.linalg.norm(S, axis=1), 1e-12)[:, None]
        for _ in range(v_it):
            C = (P[T[:, 0]] + P[T[:, 1]] + P[T[:, 2]]) / 3
            d = np.zeros_like(P)
            k = (Nf[ff] * (C[ff] - P[vf])).sum(1)[:, None] * Nf[ff]
            np.add.at(d, vf, k)
            P = P + d / np.maximum(cnt, 1)[:, None]
    me.vertices.foreach_set("co", P.ravel()); me.update()
    N, A, C = face_geo(P, T)
    return {"welded": welded, "tris": len(T), "wavy_before_deg": round(before, 3), "wavy_after_deg": round(waviness(N, pairs), 3)}


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    thr, n_it, v_it, rounds = float(a[0]), int(a[1]), int(a[2]), int(a[3])
    for n in ("Meshy_Body", "DOOR_L", "DOOR_R"):
        print(n, denoise(bpy.data.objects[n], thr, n_it, v_it, rounds))
    if len(a) > 4:
        bpy.ops.wm.save_as_mainfile(filepath=a[4], copy=True)
        print("saved", a[4])
