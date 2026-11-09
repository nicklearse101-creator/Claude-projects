"""Seed a new photo's camera from a handful of marks, using the current 3D points.
    python seed_cam.py cam marks.json result.json guess_pos(x,y,z) guess_target(x,y,z)
marks.json: {"W":..,"H":..,"pts":{name:[u,v],...}}  -> prints the camera and writes <cam>_seed.json"""
import json, sys
import numpy as np, cv2
from scipy.optimize import least_squares
cam, mk, res = sys.argv[1], json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
gp = [float(v) for v in sys.argv[4].split(",")]; gt = [float(v) for v in sys.argv[5].split(",")]
G = {}; exec(open("ba.py").read().split("# ---- initialisation")[0], G)
P = {n: np.array(res["points"][n]) for n in G["pairs"]}; PL = {n: np.array(res["points"][n]) for n in G["plates"]}
r = res["points"]["wheel_r_F400"]; W, H = mk["W"], mk["H"]
names = list(mk["pts"]); X = np.array([G["pt3"](n, P, PL, r) for n in names]); I = np.array([mk["pts"][n] for n in names], float)
pos, tgt = np.array(gp), np.array(gt); z = tgt - pos; z /= np.linalg.norm(z); x = np.cross(z, [0, 0, 1.0]); x /= np.linalg.norm(x); y = np.cross(z, x)
Rm = np.stack([x, y, z]); rv, _ = cv2.Rodrigues(Rm); t = -Rm @ pos
best = None
for fk in (0.8, 1.2, 1.6, 2.2):
    q0 = np.r_[rv.ravel(), t, fk * W]
    s = least_squares(lambda q: (G["project"](np.r_[q, 0.0], X, W, H)[0] - I).ravel(), q0)
    e = np.linalg.norm(G["project"](np.r_[s.x, 0.0], X, W, H)[0] - I, axis=1)
    if best is None or np.sqrt(np.mean(e ** 2)) < best[0]:
        best = (np.sqrt(np.mean(e ** 2)), s.x, e)
rms, q, e = best
Rm, _ = cv2.Rodrigues(q[:3]); C = -Rm.T @ q[3:6]
print("rms %.1f px  f/W %.3f  camera at %s" % (rms, q[6] / W, np.round(C, 2)))
for n, ee in zip(names, e): print("   %-12s %5.1f px" % (n, ee))
json.dump({"cam": list(map(float, np.r_[q, 0.0]))}, open("%s_seed.json" % cam, "w"))
