"""Depth scans of the reference body (REF_BODY in export/ref/nova_ref.blend) for the feature map.

Orthographic ray grids from 5 directions; per cell: hit depth along the ray (NaN = no hit) and the hit normal.
  side_L: from +x (car's left), grid (y, z)      side_R: from -x, grid (y, z)
  front:  from -y, grid (x, z)                    rear:   from +y, grid (x, z)
  top:    from +z, grid (x, y)
Saved as export/ref/scan/<view>.npz (depth = coordinate of the hit along the view axis, plus the grid axes).
"""
import os

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = r"D:\Claude\vauxhall_nova_gte_1989\export\ref\scan"
STEP = 0.0025

VIEWS = {
    # name: (origin fn(u, v), direction, u-range, v-range, axis index of depth)
    "side_L": (lambda u, v: (1.5, u, v), (-1, 0, 0), (-1.86, 1.80), (0.10, 1.40), 0),
    "side_R": (lambda u, v: (-1.5, u, v), (1, 0, 0), (-1.86, 1.80), (0.10, 1.40), 0),
    "front": (lambda u, v: (u, -3.0, v), (0, 1, 0), (-0.88, 0.88), (0.10, 1.40), 1),
    "rear": (lambda u, v: (u, 3.0, v), (0, -1, 0), (-0.88, 0.88), (0.10, 1.40), 1),
    "top": (lambda u, v: (u, v, 3.0), (0, 0, -1), (-0.88, 0.88), (-1.86, 1.80), 2),
}


def main(step=STEP):
    os.makedirs(OUT, exist_ok=True)
    o = bpy.data.objects["REF_BODY"]
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    stats = {}
    for name, (orig, d, ur, vr, ax) in VIEWS.items():
        us = np.arange(ur[0], ur[1], step)
        vs = np.arange(vr[0], vr[1], step)
        dep = np.full((len(vs), len(us)), np.nan, np.float32)
        nrm = np.zeros((len(vs), len(us), 3), np.float16)
        D = Vector(d)
        for j, v in enumerate(vs):
            for i, u in enumerate(us):
                h = bvh.ray_cast(Vector(orig(u, v)), D, 6.0)
                if h[0] is not None:
                    dep[j, i] = h[0][ax]
                    nrm[j, i] = h[1]
        np.savez_compressed(os.path.join(OUT, name + ".npz"), depth=dep, normal=nrm, u=us, v=vs)
        stats[name] = {"grid": dep.shape, "hit_pct": round(float(np.isfinite(dep).mean() * 100), 1)}
    return stats


if __name__ == "__main__":
    print("==", main())
