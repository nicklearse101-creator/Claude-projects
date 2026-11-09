"""Nova GTE rear panel (the tailgate below the glass) -> blender/data/rear_panel.json. BA/photo frame.

The body shell is a loft of cross-sections along the car, so it cannot hold a vertical rear face: every point of
one has the same y, and the loft's last stations collapse into a sliver. The tail therefore came out as a
rounded blob with the lamps buried inside it. The rear panel is built here instead, as its own measured surface,
the way the bonnet, wings and scuttle are.

Across the car it uses the shell's own rear-face curve

    wrap(x) = 0.88 * |x|^6.4                       (tools/gen/build_shell2.py)

which reproduces the four triangulated tail-lamp corners to 2-8 mm. Up the car it uses the centreline profile
y0(z) read off those same points and the number plate:

    TL_BI  z 0.562 -> y0 1.736      PLR400/PLR294 (plate centre)  z 0.668 -> y0 1.731
    TL_TI  z 0.804 -> y0 1.732      HG_B (hatch glass lower edge) z 0.900 -> y0 1.640

so the panel stands vertical from the bumper to the top of the lamps and then turns forward over about 100 mm
to meet the glass seal - the body-colour band that carries the griffin badge on the real car.

Materials: body colour, with the black GTE panel between the lamps (z 0.60 - 0.81, |x| < the lamps' inner edge,
photographs c24 / cAR / the 4298 px commons rear) and the number plate on it (520 x 111 mm, centred on
PLR400 / PLR294).

    python tools/rear_panel.py
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PM = os.path.join(ROOT, "tools", "photomatch")
BA = json.load(open(os.path.join(PM, "ba_result.json")))["points"]
PF = json.load(open(os.path.join(PM, "body_profile.json")))
TL = PF["zones"]["tail_lamp"]

A_WRAP, P_WRAP = 0.88, 6.4
Z_LO, Z_HI = 0.540, 1.185          # bumper top to the hatch glass's top corners; the shell carries the roof
PLAN = np.array(json.load(open(os.path.join(ROOT, "blender", "data", "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(ROOT, "blender", "data", "section_body.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
SEAL = 0.014                       # glass seal: the aperture is inset this far from the measured corners
X_BLACK = float(TL["x_in"])        # the black panel runs between the lamps
Z_BLACK = (0.600, 0.810)
PLATE_W, PLATE_H = 0.520, 0.111
NU, NV = 54, 44


def wrap(x):
    return A_WRAP * np.abs(x) ** P_WRAP


# centreline profile, from the measured points (z, y0)
# below the lamps' tops the panel is vertical; it then turns forward over ~100 mm into the band that carries the
# griffin badge, and from the glass's lower corners it runs straight up the glass plane to the top ones
KNOTS = np.array([[0.500, 1.737], [0.562, 1.736], [0.668, 1.731], [0.804, 1.732],
                  [0.860, 1.700], [0.900, 1.640], [1.178, 1.447], [1.230, 1.411]])


def y0(z):
    return np.interp(z, KNOTS[:, 0], KNOTS[:, 1])


def halfw(y):
    return float(np.interp(y, PLAN[:, 0], PLAN[:, 1]))


def sect(z):
    return float(np.interp(z, SECT[:, 0], SECT[:, 1]))


def x_seam(z):
    """Where the panel meets the body side. The shell's own skin is x = halfw(y) * sect(z) (an orthographic plan
    taper times a front-elevation section), so the seam is the x that satisfies that at this height - using the
    plan's half-width alone put the seam 60 mm outside the car up at the glass, where the sides tuck in."""
    x, s = 0.70, sect(z)
    for _ in range(60):
        x_new = halfw(float(y0(z)) - wrap(x)) * s
        if abs(x_new - x) < 1e-6:
            break
        x += 0.5 * (x_new - x)
    return float(x)


# hatch glass aperture, from the two triangulated corner pairs, inset by the seal
GB, GT = BA["HG_B"], BA["HG_T"]


def x_glass(z):
    t = (z - GB[2]) / (GT[2] - GB[2])
    return GB[0] + t * (GT[0] - GB[0]) - SEAL


Z_G = (GB[2] + SEAL, GT[2] - SEAL)


def in_glass(x, z):
    return Z_G[0] < z < Z_G[1] and abs(x) < x_glass(z)


plate = BA.get("PLR400", BA.get("PLR294"))
PZ, PX = float(plate[2]), 0.0
MATS = ["paint_gunmetal", "trim_black", "plate_front"]


def mat_of(x, z):
    if abs(x) < PLATE_W / 2 - 0.002 and abs(z - PZ) < PLATE_H / 2 - 0.002:
        return 2
    if abs(x) < X_BLACK and Z_BLACK[0] < z < Z_BLACK[1]:
        return 1
    return 0


# one row of NU points per height, each row running from the centreline out to its own seam with the body side,
# so the panel's edge follows the plan outline instead of a straight cut
zs = np.unique(np.r_[np.linspace(Z_LO, Z_HI, NV), PZ - PLATE_H / 2, PZ + PLATE_H / 2,
                     Z_BLACK[0], Z_BLACK[1], Z_G[0], Z_G[1]])
zs = zs[(zs >= Z_LO) & (zs <= Z_HI)]
verts, faces, mat_idx, rows = [], [], [], []
for z in zs:
    xe = x_seam(z)
    xs = np.unique(np.r_[np.linspace(0.0, xe, NU), X_BLACK, PLATE_W / 2, max(x_glass(z), 0.0)])
    xs = xs[(xs >= 0.0) & (xs <= xe)]
    rows.append((z, xs, len(verts)))
    for x in xs:
        inset = 0.004 if (abs(x) < X_BLACK and Z_BLACK[0] <= z <= Z_BLACK[1]) else 0.0
        verts.append((float(x), float(y0(z) - wrap(x) - inset), float(z)))
for (z0_, xs0, b0), (z1_, xs1, b1) in zip(rows[:-1], rows[1:]):
    n = min(len(xs0), len(xs1))
    for i in range(n - 1):
        xm, zm = 0.5 * (xs0[i] + xs0[i + 1]), 0.5 * (z0_ + z1_)
        if in_glass(xm, zm):
            continue
        faces.append((b0 + i, b0 + i + 1, b1 + i + 1, b1 + i))
        mat_idx.append(mat_of(xm, zm))

out = {}
for side, sx in (("L", 1.0), ("R", -1.0)):
    vs = [(sx * x, y, z) for x, y, z in verts]
    fs = [list(reversed(f)) for f in faces] if sx < 0 else [list(f) for f in faces]
    out["PANEL_R_%s" % side] = {"verts": [[round(c, 5) for c in v] for v in vs],
                                "faces": fs, "mats": MATS, "mat_idx": list(mat_idx)}
out["_note"] = ("rear panel on the shell's rear-face curve 0.88|x|^6.4 with the centreline profile read off "
                "TL_BI / plate / TL_TI / HG_B; black GTE panel and number plate as material bands. "
                "BA/photo frame, z before dz.")
json.dump(out, open(os.path.join(ROOT, "blender", "data", "rear_panel.json"), "w"), indent=1)
a = np.array(out["PANEL_R_L"]["verts"])
print("PANEL_R  %d verts %d faces   x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f"
      % (len(a), len(faces), a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max(), a[:, 2].min(), a[:, 2].max()))
for n in ("TL_TI", "TL_BI", "HG_B"):
    x, y, z = BA[n]
    print("   %-6s measured y %.3f   panel y %.3f   (%+.0f mm)" % (n, y, y0(z) - wrap(x), (y0(z) - wrap(x) - y) * 1000))
print("   plate  centre z %.3f, %d x %d mm" % (PZ, PLATE_W * 1000, PLATE_H * 1000))
print("   seam with the body side: x %.3f at z %.2f -> %.3f at z %.2f" % (x_seam(Z_LO), Z_LO, x_seam(Z_HI), Z_HI))
print("   glass aperture z %.3f..%.3f, half-width %.3f..%.3f" % (Z_G[0], Z_G[1], x_glass(Z_G[0]), x_glass(Z_G[1])))
print("wrote blender/data/rear_panel.json")
