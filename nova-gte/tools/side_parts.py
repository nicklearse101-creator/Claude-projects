"""Nova GTE side parts (plain Python) -> blender/data/side_parts.json: grey sill skirts with the kick-up in front
of the rear wheel. BA/photo frame, left side generated and mirrored.

Sources (ESTIMATE from photos): cS side rays (side_lines.json): skirt top z ~0.30 along the sill, rising to ~0.46
at the rear arch (skirt_top), sill bottom z ~0.23 (sill_bottom); arches from body_profile.json; photos 01/22/cAR:
separate grey plastic moulding standing ~15 mm proud of the sill, rounded top edge, tucked under at the bottom.
"""
import json
import math
import os
import sys

import numpy as np

import meshkit as mk

os.environ.setdefault("NOVA_ROOT", "/home/claude/novaroot")
import body_geom as g  # noqa: E402

TOP = [(-0.8356, 0.2967), (-0.8069, 0.3236), (0.6727, 0.2966), (0.7679, 0.3654), (0.8229, 0.4594)]
Z_BOT = 0.232
GAP = 0.010


def z_top(y):
    ys = [p[0] for p in TOP]; zs = [p[1] for p in TOP]
    if y <= ys[1]:
        return zs[1]
    return float(np.interp(y, ys[1:], zs[1:]))


def arch_y(key, z, front_side):
    """Skirt end at height z: the arch lip (traced outline) + GAP; front_side = the arch's rear edge (skirt front end)."""
    y = g.arch_edge_y(key, z, "rear" if front_side else "front", photo_frame=True)
    if y is None:
        return None
    return y + GAP if front_side else y - GAP


def profile(zt, zb):
    """(d, z) rows from the top edge down, d = outward offset from the body skin."""
    h = zt - zb
    return [(-0.002, zt + 0.004), (0.004, zt + 0.002), (0.010, zt - 0.001), (0.0135, zt - 0.006),
            (0.0150, zt - 0.014), (0.0155, zt - 0.40 * h), (0.0150, zb + 0.25 * h), (0.0125, zb + 0.010),
            (0.0080, zb + 0.003), (0.0010, zb), (-0.020, zb - 0.002)]


def skirt():
    ny = 160
    y0 = arch_y("front", Z_BOT + 0.03, True) or -0.84
    y1 = arch_y("rear", Z_BOT + 0.03, False) or 0.80
    ys = np.linspace(y0, y1 + 0.08, ny)
    G = []
    for y in ys:
        zt = z_top(y)
        rows = []
        for d, z in profile(zt, Z_BOT):
            x = g.skin_x(float(y), max(z, 0.235))
            if x is None:
                x = g.skin_x(float(y), 0.29)
            rows.append([x + d, y, z])
        G.append(rows)
    G = np.array(G)
    # each row's ends follow the arch circles (solved per row, rows are not level at the kick-up)
    def row_z(j, y):
        return profile(z_top(y), Z_BOT)[j][1]

    def solve(j, key, y_guess):
        """Fixed point: the row's end y where it meets the arch lip (+ GAP) at the row's own height there."""
        y = y_guess
        for _ in range(30):
            ye = arch_y(key, row_z(j, y), key == "front")
            if ye is None:
                return None
            if abs(ye - y) < 1e-5:
                break
            y = ye
        return y
    nrow = G.shape[1]
    for j in range(nrow):
        ya = solve(j, "front", y0) or y0
        yb = solve(j, "rear", y1) or y1
        for i in range(ny):
            y = ya + (yb - ya) * i / (ny - 1)
            d, zz = profile(z_top(y), Z_BOT)[j]
            x = g.skin_x(float(y), max(zz, 0.235)) or g.skin_x(float(y), 0.29)
            G[i, j] = (x + d, y, zz)
    p = mk.Part()
    p.grid(G, "trim_grey", flip=True)
    return p


def build():
    s = skirt()
    return {"SKIRT_L": s, "SKIRT_R": s.mirrored()}


if __name__ == "__main__":
    parts = build()
    mk.save(parts, sys.argv[1] if len(sys.argv) > 1 else "data/side_parts.json")
    for k, p in parts.items():
        print(k, len(p.v), len(p.f))
