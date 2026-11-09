"""Nova GTE rear bumper parts (plain Python) -> blender/data/rear_end.json.

BA/photo frame (car faces -Y, Z up, +X = car's left; ground = loaded tyre contact). Built with the front bumper's
machinery in a y-mirrored frame (so the plan path runs from the centreline outward and *back* along the side
return), then mirrored back to the rear.

Sources (2026-10-12; ESTIMATE shapes, measured heights):
  centre heights, cAR (anglia_rear, rays on the face plane y 1.78): top 0.550, ribs 0.498 / 0.486 / 0.473 / 0.460,
    red bottom 0.377, grey valance bottom 0.272
  side return heights, cS (anglia_side, rays at x -0.745): top 0.561, ribs 0.519 / 0.508 / 0.497 / 0.485,
    red bottom 0.372, valance bottom 0.300 - heights blend between x 0.50 and 0.72 (the plan corner)
  face at the centreline y 1.7805 = FIA rear overhang 609 mm; the side photo silhouette agrees within ~1 cm.
  plan corner follows the shell's rear sweep about 1-1.5 cm proud; side return x 0.762 (FIA body width at the
    rear axle 1529 mm -> 0.7645); ends on the rear arch circle + 10 mm with a return flange
  four ribs with the GTE red insert (brochure: red insert on the bumpers for GTE); number-plate lamp housing on
    the top at the centre (photos cAR / c24)
"""
import math
import os
import sys

import numpy as np

import meshkit as mk

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender", "scripts"))
import body_geom as g  # noqa: E402

APEX_Y = 1.7805
CTRL = [(0.0, APEX_Y), (0.30, 1.7795), (0.45, 1.7755), (0.55, 1.7665), (0.62, 1.7515), (0.68, 1.728),
        (0.72, 1.700), (0.745, 1.662), (0.758, 1.612), (0.762, 1.560), (0.762, 1.400)]
TOP = (0.550, 0.561)
# ribs (red inserts) LEVEL end to end (Nik 2026-10-12); cAR centre and cS side disagree by ~2 cm (docstring) ->
# mean of the two, same at the centre and the side (ESTIMATE, each view within ~1 cm)
RIBS = ((0.5085, 0.497, 0.485, 0.4725), (0.5085, 0.497, 0.485, 0.4725))
Z_RB = (0.377, 0.372)
Z_VB = (0.272, 0.300)
RIB_HW, RIB_D = 0.0030, 0.0026
ARCH_R = (1.142, 0.281, 0.340)      # body_profile arch_rear (y, z, r), BA frame


def corner_t(x):
    t = min(1.0, max(0.0, (abs(x) - 0.50) / 0.22))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def bumper_profile(x):
    """(d, z) rows, d = outward plan offset: top shelf, upper face, 4 rib grooves, lower face tucking under.
    Same row count for every x."""
    t = corner_t(x)
    zt = lerp(*TOP, t)
    ribs = [lerp(c, s, t) for c, s in zip(*RIBS)]
    zrb = lerp(*Z_RB, t)
    pr = [(-0.045, zt), (-0.030, zt), (-0.016, zt - 0.0015), (-0.007, zt - 0.004), (-0.002, zt - 0.009),
          (0.000, zt - 0.016)]
    z_up0, z_up1 = zt - 0.016, ribs[0] + RIB_HW + 0.004
    for k in range(1, 4):
        z = z_up0 + (z_up1 - z_up0) * k / 4
        pr.append((0.0015 * math.sin(math.pi * k / 4), z))
    for zc in ribs:
        for kk in (RIB_HW + 0.0008, RIB_HW * 0.45, 0.0, -RIB_HW * 0.45, -RIB_HW - 0.0008):
            u = abs(kk) / RIB_HW
            d = -RIB_D * (1 - u * u) if u < 1 else 0.0
            pr.append((d, zc + kk))
    z_lo0 = ribs[-1] - RIB_HW - 0.006
    for k in range(9):
        f = k / 8
        pr.append((-0.002 - 0.014 * f ** 1.6, z_lo0 + (zrb + 0.006 - z_lo0) * f))
    pr += [(-0.024, zrb + 0.002), (-0.040, zrb - 0.001), (-0.060, zrb - 0.002)]
    return pr


def rib_rows():
    """Row indices of the groove centre rows (red stripe material) in bumper_profile."""
    base = 6 + 3
    return {base + 5 * i + 2 for i in range(4)} | {base + 5 * i + 1 for i in range(4)} | {base + 5 * i + 3 for i in range(4)}


def valance_profile(x):
    t = corner_t(x)
    zrb, zvb = lerp(*Z_RB, t), lerp(*Z_VB, t)
    h = zrb - zvb
    return [(-0.065, zrb + 0.004), (-0.044, zrb + 0.002), (-0.034, zrb - 0.004), (-0.029, zrb - 0.25 * h),
            (-0.028, zrb - 0.55 * h), (-0.030, zvb + 0.012), (-0.034, zvb + 0.004), (-0.042, zvb),
            (-0.070, zvb), (-0.140, zvb + 0.004)]


def arch_end(G, path, y_from=1.50, gap=0.010):
    """(mirrored frame: y' = -y) stretch the side-return columns so each row ends on the rear arch circle + gap."""
    yl = path[-1, 1]
    for j in range(G.shape[1]):
        z = G[-1, j, 2]
        ya = g.arch_edge_y("rear", z, "rear", photo_frame=True)      # traced lip outline (body_profile arch_shapes)
        ye = -(ya + gap) if ya is not None else yl
        ye = min(ye, yl + 0.06)
        for i in range(len(path)):
            if path[i, 1] > -y_from:
                tt = (path[i, 1] + y_from) / (yl + y_from)
                G[i, j, 1] = -y_from + tt * (ye + y_from)


def return_flange(G, depth=0.025):
    last = G[-1].copy()
    last[:, 0] -= depth
    last[:, 1] += 0.004          # mirrored frame: +y' = toward the arch (real -y)
    return np.concatenate([G, last[None]], axis=0)


def to_rear(part):
    """Mirrored frame -> real frame: y' -> -y, faces reversed (mirroring flips handedness)."""
    part.v = [[x, -y, z] for x, y, z in part.v]
    part.f = [f[::-1] for f in part.f]
    return part


def bumper():
    ctrl = [(x, -y) for x, y in CTRL]                     # mirrored frame: centre at -APEX_Y, side runs +y'
    path, tan, _ = mk.spline_path(ctrl, ds=0.008, start_slope=0.0)
    G = mk.sweep_var(path, tan, lambda x, y: bumper_profile(x))
    arch_end(G, path)
    G = return_flange(G)
    G = mk.full_from_half(G)
    stripe = rib_rows()
    p = mk.Part()
    p.grid(G, None, mats=lambda i, j: "bumper_stripe" if j in stripe else "paint_gunmetal", flip=True)
    V = mk.sweep_var(path, tan, lambda x, y: valance_profile(x))
    arch_end(V, path)
    V = return_flange(V)
    V = mk.full_from_half(V)
    val = mk.Part(); val.grid(V, "trim_grey", flip=True)
    # number-plate lamp housing on the bumper top at the centre (grey, 110 x 30 x 22 mm)
    lamp = mk.Part()
    zt = TOP[0]
    y0 = -(APEX_Y - 0.030)
    P = np.zeros((2, 2, 3))
    corners = [(-0.055, y0 - 0.012), (0.055, y0 - 0.012), (0.055, y0 + 0.018), (-0.055, y0 + 0.018)]
    vs = [lamp.add_v((x, y, zt - 0.002)) for x, y in corners] + [lamp.add_v((x, y, zt + 0.020)) for x, y in corners]
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        lamp.add_f([vs[a], vs[b], vs[b + 4], vs[a + 4]], "trim_grey")
    lamp.add_f([vs[4], vs[5], vs[6], vs[7]], "trim_grey")
    return {"BUMPER_R": to_rear(p.weld()), "BUMPER_R_VALANCE": to_rear(val.weld()), "PLATE_LAMP_R": to_rear(lamp)}


def build():
    return bumper()


if __name__ == "__main__":
    parts = build()
    mk.save(parts, sys.argv[1] if len(sys.argv) > 1 else "data/rear_end.json")
    for k, p in parts.items():
        print(k, len(p.v), "verts", len(p.f), "faces", sorted(set(p.m)))
