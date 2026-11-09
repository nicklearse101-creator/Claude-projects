"""Bundle adjustment with a fuller camera model - tests whether the old solve's 5-18 mm error is the camera model.

ba.py fixes each camera's principal point at the image centre and has one distortion term. Wikimedia and
auction photos are usually CROPPED, which moves the principal point off-centre; that alone can leave
residuals no pose can remove. This solve adds, per camera, a principal-point offset (cx, cy, in px, with a weak
prior towards the centre) and a second radial term k2, starting from ba.py's own solution.

Same points, same anchors (wheel centres at +-WB2, plates 520 x 111 mm) and the same frame as ba.py - so a
better fit here is a better camera, not a different car.

    python ba2.py [base|pp|pp_k2]       default pp_k2; writes ba2_result.json (same layout as ba_result.json,
                                        cams carry 11 numbers: rvec tvec f k1 k2 cx cy)
"""
import json
import sys

import cv2
import numpy as np
from scipy.optimize import least_squares

import importlib.util
MODE = sys.argv[1] if len(sys.argv) > 1 else "pp_k2"
O = json.load(open("obs.json"))
R0 = json.load(open("ba_result.json"))

# reuse ba.py's point model without running its solve
src = open("ba.py").read().split("# ---- initialisation")[0]
G = {}
exec(src, G)
pairs, plates, cams, pt3 = G["pairs"], G["plates"], G["cams"], G["pt3"]
NC = 11


def unpack(p):
    i = 0; P = {}; PL = {}
    for n in pairs: P[n] = p[i:i + 3]; i += 3
    for n in plates: PL[n] = p[i:i + 3]; i += 3
    r = p[i]; i += 1
    C = {}
    for c in cams: C[c] = p[i:i + NC]; i += NC
    return P, PL, r, C


def project(cp, X, W, H):
    rv, tv, f, k1, k2, cx, cy = cp[0:3], cp[3:6], cp[6], cp[7], cp[8], cp[9], cp[10]
    R, _ = cv2.Rodrigues(rv); Xc = X @ R.T + tv
    x = Xc[:, 0] / Xc[:, 2]; y = Xc[:, 1] / Xc[:, 2]
    r2 = x * x + y * y; s = 1 + k1 * r2 + k2 * r2 * r2
    return np.stack([W / 2 + cx + f * x * s, H / 2 + cy + f * y * s], 1), Xc[:, 2]


FREE_PP = MODE in ("pp", "pp_k2")
FREE_K2 = MODE == "pp_k2"


def residuals(p):
    P, PL, r, C = unpack(p); out = []
    for c in cams:
        W, H = O[c]["W"], O[c]["H"]; names = list(O[c]["pts"])
        X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([O[c]["pts"][n] for n in names])
        uv, depth = project(C[c], X, W, H)
        out.append(((uv - I) / (W / 1000.0)).ravel())
        out.append(np.minimum(depth - 0.5, 0) * 100)
        out.append([C[c][7] * 50.0])
        out.append([C[c][8] * (20.0 if FREE_K2 else 1e4)])
        # principal point: weak prior when free (10% of the width costs as much as 1 px everywhere), pinned otherwise
        w_pp = 10.0 / W if FREE_PP else 1e4
        out.append([C[c][9] * w_pp, C[c][10] * w_pp])
        out.append([(C[c][6] / W - 0.8) * 5])
    return np.concatenate(out)


p = []
for n in pairs: p += list(R0["points"][n])
for n in plates: p += list(R0["points"][n])
p += [R0["points"]["wheel_r_F400"]]
for c in cams: p += list(R0["cams"][c][:8]) + [0.0, 0.0, 0.0]
p = np.array(p, float)
LOSS = sys.argv[2] if len(sys.argv) > 2 else "linear"
s = least_squares(residuals, p, x_scale="jac", max_nfev=40000, loss=LOSS, f_scale=2.0)
P, PL, r, C = unpack(s.x)
print("mode", MODE, "cost", round(s.cost, 2))
print("cam   rms px  max px (point)          mm/px  rms mm   f/W    k1     k2     cx px  cy px")
for c in cams:
    W, H = O[c]["W"], O[c]["H"]; names = list(O[c]["pts"])
    X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([O[c]["pts"][n] for n in names])
    uv, depth = project(C[c], X, W, H); e = np.linalg.norm(uv - I, axis=1)
    mmpp = float(np.median(depth)) / C[c][6] * 1000
    print("%-4s  %6.2f  %6.1f (%-12s)  %5.2f  %6.1f  med %4.1f mm  %.3f %+.3f %+.3f %+6.1f %+6.1f"
          % (c, np.sqrt(np.mean(e ** 2)), e.max(), names[int(e.argmax())], mmpp, np.sqrt(np.mean(e ** 2)) * mmpp,
             np.median(e) * mmpp, C[c][6] / W, C[c][7], C[c][8], C[c][9], C[c][10]))
res = {n: [round(float(v), 4) for v in P[n]] for n in pairs}
res.update({n: [round(float(v), 4) for v in PL[n]] for n in plates})
res["wheel_r_F400"] = float(r)
moved = {n: round(float(np.linalg.norm(np.array(res[n]) - np.array(R0["points"][n]))) * 1000, 1) for n in pairs}
print("points moved vs ba_result (mm):", dict(sorted(moved.items(), key=lambda kv: -kv[1])[:12]))
json.dump({"mode": MODE, "points": res, "cams": {c: [float(v) for v in C[c]] for c in cams}},
          open("ba2_result_%s%s.json" % (MODE, "" if LOSS == "linear" else "_" + LOSS), "w"), indent=1)
