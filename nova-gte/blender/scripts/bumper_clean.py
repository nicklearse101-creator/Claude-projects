"""Rebuild the bumpers' rib band clean (Nik 2026-10-19: ragged ribs, bend at the arch - also in the original model).
The bumper surface is measured in plan-polar form r(theta, z) from a centre inside the car (rays cast inward from
outside, so the first hit is the outer skin) and replaced by a clean separable surface R(theta) + P(z): one plan
outline and one cross-section (top lip + ribs + lower face) all the way round, as on the real car. The mesh is first
cut along the rib edges (horizontal planes at P's steps) so the rib lines are clean, then the outer-skin vertices are
moved radially onto the clean surface (blended out at the band ends and towards the arches)."""
import math

import numpy as np

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BUMPERS = {  # name: (centre y, direction sign, z0, z1, theta half-range rad, theta of the mid section for P)
    "rear": (1.00, 1, 0.37, 0.585, 1.08, 0.45),
    "front": (-1.00, -1, 0.36, 0.535, 1.12, 0.45),
}


def _ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def measure(bvh, cy, sg, z0, z1, th_max, dz=0.002, dth=0.004):
    zs = np.arange(z0 - 0.01, z1 + 0.01, dz); ths = np.arange(-th_max, th_max + 1e-9, dth)
    Rm = np.full((len(zs), len(ths)), np.nan)
    for i, z in enumerate(zs):
        C = Vector((0.0, cy, z))
        for j, th in enumerate(ths):
            d = Vector((math.sin(th), sg * math.cos(th), 0.0))
            h = bvh.ray_cast(C + d * 2.5, -d, 2.5)
            if h[0] is not None:
                Rm[i, j] = (h[0] - C).length
    return zs, ths, Rm


def fit(zs, ths, Rm, mid):
    """r = R(theta) + P(z), robust (medians), P normalised to 0 at its median."""
    P = np.zeros(len(zs))
    for _ in range(3):
        R = np.nanmedian(Rm - P[:, None], axis=0)
        cols = np.abs(ths) < mid
        P = np.nanmedian((Rm - R[None, :])[:, cols], axis=1)
        P -= np.nanmedian(P)
    # plan outline: smooth along theta (5-point binomial)
    Rf = np.where(np.isfinite(R), R, np.interp(ths, ths[np.isfinite(R)], R[np.isfinite(R)]))
    for _ in range(4):
        Rf = np.convolve(np.pad(Rf, 2, mode="edge"), np.array([1, 4, 6, 4, 1]) / 16, "valid")
    return Rf, P


def rib_edges(zs, P, min_step=0.0012):
    """Heights where the profile steps (rib edges)."""
    d = np.abs(np.diff(P))
    return [float((zs[i] + zs[i + 1]) / 2) for i in range(len(d)) if d[i] > min_step and d[i] >= d[max(i - 1, 0)] and d[i] >= d[min(i + 1, len(d) - 1)]]


def clean(name, cut=True):
    import prep_reference as pr
    cy, sg, z0, z1, th_max, mid = BUMPERS[name]
    o = bpy.data.objects["REF_BODY"]; me = o.data
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    zs, ths, Rm = measure(bvh, cy, sg, z0, z1, th_max)
    R, P = fit(zs, ths, Rm, mid)
    edges = rib_edges(zs, P)
    if cut and edges:
        planes = []
        for ze in edges:
            box = (-0.85, 0.85, 1.40, 1.95, ze - 0.02, ze + 0.02) if sg > 0 else (-0.85, 0.85, -1.95, -1.42, ze - 0.02, ze + 0.02)
            planes.append(((0, cy, ze), (0, 0, 1), box))
        pr.bisect_planes(planes, grow=0.005)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    x, y, z = co.T
    rel = np.stack([x, (y - cy) * sg], 1)
    r = np.linalg.norm(rel, axis=1); th = np.arctan2(rel[:, 0], rel[:, 1])
    inb = (np.abs(th) < th_max) & (z > z0 - 0.01) & (z < z1 + 0.01) & ((y - cy) * sg > 0.2)
    idx = np.where(inb)[0]
    # measured outermost r at the vertex's (theta, z): only the outer skin moves
    zi = np.clip(np.round((z[idx] - zs[0]) / (zs[1] - zs[0])).astype(int), 0, len(zs) - 1)
    ti = np.clip(np.round((th[idx] - ths[0]) / (ths[1] - ths[0])).astype(int), 0, len(ths) - 1)
    rm = Rm[zi, ti]
    skin = np.isfinite(rm) & (r[idx] > rm - 0.012)
    target = np.interp(th[idx], ths, R) + np.interp(z[idx], zs, P)
    w = _ss(z0 - 0.0, z0 + 0.015, z[idx]) * _ss(z1, z1 - 0.012, z[idx]) * _ss(th_max, th_max - 0.08, np.abs(th[idx]))
    w = w * skin
    dr = (target - r[idx]) * w
    dr = np.clip(dr, -0.008, 0.008)
    k = idx[np.abs(dr) > 1e-6]
    scale = (r[k] + dr[np.abs(dr) > 1e-6]) / np.maximum(r[k], 1e-9)
    co[k, 0] = x[k] * scale
    co[k, 1] = cy + (y[k] - cy) * scale
    me.vertices.foreach_set("co", co.ravel()); me.update()
    return {"rib_edges": [round(e, 4) for e in edges], "moved": int(len(k)),
            "max_mm": round(float(np.abs(dr).max() * 1000), 1), "profile_mm": round(float(np.nanmax(P) - np.nanmin(P)) * 1000, 1)}


if __name__ == "__main__":
    print("==", {k: clean(k) for k in BUMPERS})
