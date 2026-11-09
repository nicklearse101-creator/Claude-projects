"""Camera for the grey side picture, constrained to a near-level side-on studio camera (free 6-DOF solves fall into
the distance/height ambiguity of a side view). Writes grey_cams.json (same format as solve_grey.py)."""
import json

import cv2
import numpy as np
from scipy.optimize import least_squares

exec(open('ba.py').read().split('# ---- initialisation')[0])
B = json.load(open('ba_result.json'))
P = {k: np.array(v) for k, v in B['points'].items() if isinstance(v, list) and not k.startswith('PL')}
PL = {k: np.array(v) for k, v in B['points'].items() if k.startswith('PL')}
r = B['points']['wheel_r_F400']
src = open('solve_grey.py').read()
OBS = eval(src[src.index("OBS = {") + 6: src.index("}\n", src.index("OBS = {")) + 1])
W, H = 667, 258
names = list(OBS); X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([OBS[n] for n in names])


def cam(p):
    yaw, pitch, roll, cy, cz, d, f = p
    C = np.array([d, cy, cz])
    R0 = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], float)      # look along -x, image right +y, image down -z
    Rx = cv2.Rodrigues(np.array([pitch, 0, 0.0]))[0]; Ry = cv2.Rodrigues(np.array([0, yaw, 0.0]))[0]
    Rz = cv2.Rodrigues(np.array([0, 0, roll]))[0]
    R = Rz @ Rx @ Ry @ R0
    rv, _ = cv2.Rodrigues(R)
    return np.r_[rv.ravel(), -R @ C, f, 0.0]


best = None
for d in (8, 12, 20, 40):
    p0 = [0, 0, 0, 0.0, 0.8, d, d * 160]
    res = lambda p: (project(cam(p), X, W, H)[0] - I).ravel()
    lb = [-0.02, -0.06, -0.03, -1.0, 0.2, 5, 300]; ub = [0.02, 0.06, 0.03, 1.0, 2.0, 200, 120000]
    s = least_squares(res, p0, bounds=(lb, ub), loss="soft_l1", f_scale=1.5)
    e = np.linalg.norm(project(cam(s.x), X, W, H)[0] - I, axis=1); rms = np.sqrt((e ** 2).mean())
    print("d0 %d -> rms %.2f  yaw %.3f pitch %.3f roll %.3f cy %.2f cz %.2f d %.1f f/W %.2f" % (d, rms, *s.x[:6], s.x[6] / W))
    if best is None or rms < best[0]:
        best = (rms, s.x, e)
rms, p, e = best
print(" ".join("%s:%.1f" % (n, e[i]) for i, n in enumerate(names)))
json.dump({"gS": [float(v) for v in cam(p)], "W": W, "H": H}, open("grey_cams.json", "w"), indent=1)
