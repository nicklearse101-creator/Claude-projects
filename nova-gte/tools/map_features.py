"""Measure the reference body's features from the depth scans (export/ref/scan/*.npz, blender/scripts/scan_shell.py).

Grooves (shut lines, panel joints): the hit surface lies deeper than its 1 cm neighbourhood by > GROOVE.
Openings (windows, arches): no hit, or the hit lies deep inside the body (> DEEP behind the local skin).
Writes export/ref/scan/features.json and groove/opening overlay images (map_<view>.png)."""
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "export", "ref", "scan")
GROOVE = 0.0012
TOWARD = {"side_L": 1, "side_R": -1, "front": -1, "rear": 1, "top": 1}   # sign of 'closer to the viewer'


def load(view):
    z = np.load(os.path.join(D, view + ".npz"))
    return z["depth"].astype(np.float64), z["u"], z["v"]


def toward(view, dep):
    """Depth expressed as distance toward the viewer (bigger = nearer), NaN kept."""
    return dep * TOWARD[view]


def highpass(t, sigma=4):
    m = np.isfinite(t)
    f = np.where(m, t, 0.0)
    w = ndi.gaussian_filter(m.astype(float), sigma)
    s = ndi.gaussian_filter(f, sigma) / np.maximum(w, 1e-6)
    return np.where(m, t - s, np.nan)


def maps(view):
    dep, u, v = load(view)
    t = toward(view, dep)
    hp = highpass(t)
    groove = hp < -GROOVE
    return dep, t, hp, groove, u, v


def nearest_idx(a, x):
    return int(np.argmin(np.abs(a - x)))


def groove_cross(view, along, at, lo, hi, groove, u, v):
    """Groove positions along a probe line. along='u': row at v=at, scan u in [lo, hi]; along='v': column at u=at."""
    if along == "u":
        j = nearest_idx(v, at)
        sel = (u >= lo) & (u <= hi)
        g = groove[max(0, j - 1):j + 2, :].any(0) & sel
        coords = u
    else:
        i = nearest_idx(u, at)
        sel = (v >= lo) & (v <= hi)
        g = groove[:, max(0, i - 1):i + 2].any(1) & sel
        coords = v
    lab, n = ndi.label(g)
    return [round(float(coords[lab == k].mean()), 3) for k in range(1, n + 1)]


def openings(view, t, u, v, deep=0.08, min_area=0.01):
    """Connected regions where the ray misses or lands > deep behind the local outer skin."""
    skin = ndi.maximum_filter(np.nan_to_num(t, nan=-9), size=41)
    op = ~np.isfinite(t) | (t < skin - deep)
    # only inside the car's outline (skin present around)
    inside = ndi.binary_fill_holes(np.isfinite(t))
    op &= inside
    lab, n = ndi.label(op)
    du, dv = u[1] - u[0], v[1] - v[0]
    out = []
    for k in range(1, n + 1):
        jj, ii = np.where(lab == k)
        area = len(jj) * du * dv
        if area < min_area:
            continue
        out.append({"u": [round(float(u[ii.min()]), 3), round(float(u[ii.max()]), 3)],
                    "v": [round(float(v[jj.min()]), 3), round(float(v[jj.max()]), 3)],
                    "area_m2": round(float(area), 3), "centre": [round(float(u[ii].mean()), 3), round(float(v[jj].mean()), 3)]})
    return sorted(out, key=lambda r: r["u"][0]), lab


def image(view, t, groove, lab):
    g = np.nan_to_num(t, nan=np.nanmin(t))
    g = (g - np.nanmin(g)) / max(np.nanmax(g) - np.nanmin(g), 1e-6)
    rgb = np.dstack([g * 180 + 40] * 3)
    rgb[lab > 0] = (40, 90, 200)
    rgb[groove] = (255, 40, 40)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)[::-1])     # v up
    if view in ("side_R", "rear"):
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im.save(os.path.join(D, "map_%s.png" % view))


def main():
    F = {}
    P = {}
    for view in ("side_L", "side_R", "front", "rear", "top"):
        dep, t, hp, groove, u, v = maps(view)
        ops, lab = openings(view, t, u, v)
        image(view, t, groove, lab)
        P[view] = (groove, u, v)
        F["openings_" + view] = ops
    gL, uL, vL = P["side_L"]
    gR, uR, vR = P["side_R"]
    F["door_shut_lines_L"] = {f"row_z{z}": groove_cross("side_L", "u", z, -0.80, 0.60, gL, uL, vL) for z in (0.40, 0.55, 0.70)}
    F["door_shut_lines_R"] = {f"row_z{z}": groove_cross("side_R", "u", z, -0.80, 0.60, gR, uR, vR) for z in (0.40, 0.55, 0.70)}
    F["door_bottom_L"] = {f"col_y{y}": groove_cross("side_L", "v", y, 0.22, 0.42, gL, uL, vL) for y in (-0.4, 0.0, 0.3)}
    F["side_rows_L"] = {f"col_y{y}": groove_cross("side_L", "v", y, 0.15, 1.38, gL, uL, vL) for y in (-1.6, -1.2, -0.4, 0.0, 0.3, 0.7, 1.2, 1.6)}
    gT, uT, vT = P["top"]
    F["top_cols"] = {f"col_x{x}": groove_cross("top", "v", x, -1.85, 1.80, gT, uT, vT) for x in (0.0, 0.2, 0.42)}
    F["top_rows"] = {f"row_y{y}": groove_cross("top", "u", y, -0.85, 0.85, gT, uT, vT) for y in (-1.5, -1.2, -0.95, 0.3, 1.0)}
    gF, uF, vF = P["front"]
    F["front_cols"] = {f"col_x{x}": groove_cross("front", "v", x, 0.15, 1.38, gF, uF, vF) for x in (0.0, 0.25, 0.5, 0.66)}
    F["front_rows"] = {f"row_z{z}": groove_cross("front", "u", z, -0.85, 0.85, gF, uF, vF) for z in (0.30, 0.42, 0.60, 0.80)}
    gB, uB, vB = P["rear"]
    F["rear_cols"] = {f"col_x{x}": groove_cross("rear", "v", x, 0.15, 1.38, gB, uB, vB) for x in (0.0, 0.25, 0.5, 0.62)}
    F["rear_rows"] = {f"row_z{z}": groove_cross("rear", "u", z, -0.85, 0.85, gB, uB, vB) for z in (0.30, 0.45, 0.65, 0.75, 0.85)}
    json.dump(F, open(os.path.join(D, "features.json"), "w"), indent=1)
    return F


if __name__ == "__main__":
    for k, val in main().items():
        print(k, json.dumps(val))
