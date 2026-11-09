"""Leave-one-photo-out: re-solve (robust, base camera model) without each photo in turn and report how key
points move - shows which photo decides each point, and whether the photos agree."""
import json, sys
import numpy as np
from scipy.optimize import least_squares
O_all = json.load(open("obs.json"))
G = {}; exec(open("ba.py").read().split("# ---- initialisation")[0], G)
R0 = json.load(open("ba2_result_base_soft_l1.json"))
pairs, plates = G["pairs"], G["plates"]
KEY = ["WS_B", "WS_T", "HL_OT", "HL_IB", "GRO_B", "IND_OB", "BON_F", "HG_B", "HG_T", "DG_RB", "QW_FB", "SR", "TL_TO"]
def solve(cams):
    def unpack(p):
        i = 0; P = {}; PL = {}
        for n in pairs: P[n] = p[i:i + 3]; i += 3
        for n in plates: PL[n] = p[i:i + 3]; i += 3
        r = p[i]; i += 1; C = {}
        for c in cams: C[c] = p[i:i + 8]; i += 8
        return P, PL, r, C
    def res(p):
        P, PL, r, C = unpack(p); out = []
        for c in cams:
            W, H = O_all[c]["W"], O_all[c]["H"]; names = list(O_all[c]["pts"])
            X = np.array([G["pt3"](n, P, PL, r) for n in names]); I = np.array([O_all[c]["pts"][n] for n in names])
            uv, depth = G["project"](C[c], X, W, H)
            out += [((uv - I) / (W / 1000.0)).ravel(), np.minimum(depth - 0.5, 0) * 100, [C[c][7] * 50.0], [(C[c][6] / W - 0.8) * 5]]
        # points nobody sees any more: weak prior to stay put
        out.append((p[:3 * len(pairs)] - p0[:3 * len(pairs)]) * 1e-3)
        return np.concatenate(out)
    p = []
    for n in pairs: p += list(R0["points"][n])
    for n in plates: p += list(R0["points"][n])
    p += [R0["points"]["wheel_r_F400"]]
    for c in cams: p += list(R0["cams"][c][:8])
    global p0; p0 = np.array(p, float)
    s = least_squares(res, p0, x_scale="jac", max_nfev=20000, loss="soft_l1", f_scale=2.0)
    return unpack(s.x)[0]
allc = sorted(O_all)
full = solve(allc)
print("drop   " + "  ".join("%-17s" % k for k in KEY))
print("(all)  " + "  ".join("%+.3f %+.3f %+.3f"[0:0] + "y%+.3f z%+.3f" % (full[k][1], full[k][2]) for k in KEY))
for c in allc:
    P = solve([d for d in allc if d != c])
    print("%-5s  " % c + "  ".join("%+5.0f %+5.0f %+4.0f" % tuple((P[k] - full[k]) * 1000) if True else "" for k in KEY))
