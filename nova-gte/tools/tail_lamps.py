"""Nova GTE tail lamps -> blender/data/tail_lamps.json (BA/photo frame, z before DZ).

Shape from the four corners triangulated on the photographs (ba_result.json TL_TI / TL_TO / TL_BI / TL_BO) and
from the shell's own rear face, which those corners sit on to within 2-6 mm:

    y_face(x) = 1.735 - 0.88 * |x|^6.4          (tools/gen/build_shell2.py)

so the lamp is laid on that face rather than on a plane, which is what makes it wrap round the corner. It runs
from x_in (the inner edge, by the tailgate) out to zones.tail_lamp.x_out, where its frame meets the body side -
the BA corners stop at x 0.683, the lens carries on round to 0.712 (DECISIONS 2026-10-13).

Colour bands from the FACTORY REAR ELEVATION, reference/blueprints/GA_rear_elevation.jpg, which dimensions them
in millimetres above the ground - 800, 745, 685, 635 - and names them down the right-hand side: Brems- und
Schlussleuchte (brake and tail), Rueckstrahler (reflector), Blinkleuchte (indicator), Rueckfahrleuchte
(reverse). The drawing's 800 mm top agrees with the triangulated TL_TI at 804 mm, so the two sources are the
same lamp; the bottom (about 562) is the triangulated TL_BI / TL_BO.

    800 - 745   red, brake and tail
    745 - 685   red, reflector (a moulding line between them, visible in the photographs)
    685 - 635   amber, indicator
    635 - bot   clear, reverse

The 4298 px commons rear photograph agrees on the order and on the red/amber break within about 12 mm.

    python tools/tail_lamps.py
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PM = os.path.join(ROOT, "tools", "photomatch")
BA = json.load(open(os.path.join(PM, "ba_result.json")))["points"]
PF = json.load(open(os.path.join(PM, "body_profile.json")))
TL = PF["zones"]["tail_lamp"]

Y_END, A_WRAP, P_WRAP = 1.735, 0.88, 6.4
X_IN, X_OUT = float(TL["x_in"]), float(TL["x_out"])
PROUD, FRAME_W, FRAME_BACK = 0.004, 0.012, 0.006     # lens proud of the face; frame width and how far it sets back
Z_BAND = [0.800, 0.745, 0.685, 0.635]      # GA_rear_elevation.jpg, metres above the ground
NU, NV = 26, 40


def y_face(x):
    return Y_END - A_WRAP * np.abs(x) ** P_WRAP


def through(p0, p1):
    """Straight z(x) through two measured corners."""
    (x0, _, z0), (x1, _, z1) = p0, p1
    m = (z1 - z0) / (x1 - x0)
    return lambda x: z0 + m * (np.asarray(x, float) - x0)


z_top = through(BA["TL_TI"], BA["TL_TO"])
z_bot = through(BA["TL_BI"], BA["TL_BO"])
# the drawing's heights as fractions down the lens, taken on the lamp's inner edge where the drawing sees it
_zt, _zb = float(z_top(BA["TL_TI"][0])), float(z_bot(BA["TL_BI"][0]))
_v = [(_zt - z) / (_zt - _zb) for z in Z_BAND]
BANDS = [(0.0, _v[0], "lamp_red"), (_v[0], _v[1], "lamp_red"), (_v[1], _v[2], "lamp_amber"),
         (_v[2], 1.0, "lamp_clear")]
MOULD = _v[0]                                 # the moulding line between the two red sections

verts, faces, mat_idx = [], [], []
mats = []
for _, _, m in BANDS:
    if m not in mats:
        mats.append(m)
mats.append("trim_black")


def patch(x0, x1, v0, v1, out, mi):
    """A band of the lamp: x across, v down from the top edge to the bottom edge."""
    base = len(verts)
    xs = np.linspace(x0, x1, NU)
    for j, v in enumerate(np.linspace(v0, v1, NV)):
        for x in xs:
            zt, zb = float(z_top(x)), float(z_bot(x))
            z = zt + v * (zb - zt)
            # the lens bulges a little in the middle, so it does not read as a flat sticker
            bulge = out * (1.0 - (2 * v - 1) ** 2) ** 0.5 if out > 0 else out
            verts.append((float(x), float(y_face(x)) + bulge, z))
    for j in range(NV - 1):
        for i in range(NU - 1):
            a = base + j * NU + i
            faces.append((a, a + 1, a + NU + 1, a + NU))
            mat_idx.append(mi)


for v0, v1, m in BANDS:
    patch(X_IN, X_OUT, v0, v1, PROUD, mats.index(m))

# black surround: a flat band of the same face all round the lens, set back
base_frame = len(mats) - 1
for (x0, x1, v0, v1) in ((X_IN - FRAME_W, X_OUT + FRAME_W, -0.055, 0.0),
                         (X_IN - FRAME_W, X_OUT + FRAME_W, 1.0, 1.055),
                         (X_IN - FRAME_W, X_IN, 0.0, 1.0),
                         (X_OUT, X_OUT + FRAME_W, 0.0, 1.0)):
    patch(x0, x1, v0, v1, -FRAME_BACK, base_frame)

out = {}
for side, sx in (("L", 1.0), ("R", -1.0)):
    vs = [(sx * x, y, z) for x, y, z in verts]
    fs = [tuple(reversed(f)) for f in faces] if sx < 0 else [tuple(f) for f in faces]
    out["TAILLAMP_%s" % side] = {"verts": [[round(c, 5) for c in v] for v in vs],
                                 "faces": [list(f) for f in fs], "mats": mats, "mat_idx": list(mat_idx)}
out["_note"] = ("tail lamps on the shell's own rear face y = 1.735 - 0.88|x|^6.4, between the triangulated "
                "corners TL_TI/TO/BI/BO; colour bands measured on the 4298 px commons rear photograph. "
                "BA/photo frame, z before dz.")
json.dump(out, open(os.path.join(ROOT, "blender", "data", "tail_lamps.json"), "w"), indent=1)
a = np.array(out["TAILLAMP_L"]["verts"])
print("TAILLAMP_L  %d verts %d faces   x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f"
      % (len(a), len(faces), a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max(), a[:, 2].min(), a[:, 2].max()))
for n in ("TL_TI", "TL_TO", "TL_BI", "TL_BO"):
    x, y, z = BA[n]
    print("   %s measured (%.3f, %.3f, %.3f)  lamp face y %.3f  z_top %.3f z_bot %.3f"
          % (n, x, y, z, y_face(x), z_top(x), z_bot(x)))
print("   bands (GA_rear_elevation): " + "  ".join("%.0f mm -> v %.3f" % (z * 1000, v) for z, v in zip(Z_BAND, _v)))
print("wrote blender/data/tail_lamps.json")
