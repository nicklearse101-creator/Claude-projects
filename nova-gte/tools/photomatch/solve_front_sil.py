"""Perspective camera for Nik's grey front picture (reference/photos/grey_studio/front.png, 329x257), fitted on the
silhouette: straight-ahead camera at (cx, -d, h) looking +y, focal f px, principal point (u0, v0), small yaw/roll.
Model = export/ref/scan/world_tris.npz (all visible meshes, world coords). Writes grey_front_cam.json."""
import json, os, sys
import cv2, numpy as np
from scipy.optimize import minimize
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
view = sys.argv[1] if len(sys.argv) > 1 else "front"
im = cv2.imread(os.path.join(ROOT, "reference/photos/grey_studio/%s.png" % view), cv2.IMREAD_UNCHANGED)
H, W = im.shape[:2]
ref = (im[..., 3] > 100) & (im[..., :3].min(-1) < 240)
D = np.load(os.path.join(ROOT, "export/ref/scan/world_tris.npz")); V, T = D["V"], D["T"]
sg = 1 if view == "front" else -1          # front: camera at -y looking +y; rear: at +y looking -y
keep = (V[T].mean(1)[:, 1] * sg < 0.6)      # only the half facing the camera matters for the outline
T = T[keep[:]] if keep.ndim == 1 else T

def proj(p, P):
    d, h, f, u0, v0, yaw, roll, cx = p
    c = np.array([cx, -sg * d, h])
    q = P - c
    # camera axes: forward = sg*y, right = -sg*x? front view: car's right (x-) appears on image left -> image right = +x for front
    fwd = np.array([0, sg, 0.0]); right = np.array([sg, 0, 0.0]); up = np.array([0, 0, 1.0])
    cy_, sy = np.cos(yaw), np.sin(yaw)
    fwd, right = cy_ * fwd + sy * right, cy_ * right - sy * fwd
    cr, sr = np.cos(roll), np.sin(roll)
    right, up = cr * right + sr * up, cr * up - sr * right
    z = q @ fwd
    return np.stack([u0 + f * (q @ right) / z, v0 - f * (q @ up) / z], -1)

rng = np.random.default_rng(0)
VS = V[rng.choice(len(V), min(len(V), 200000), replace=False)]
VS = VS[VS[:, 1] * sg < 0.8]


def mask(p, P=None):
    uv = np.round(proj(p, VS if P is None else P)).astype(int)
    ok = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
    m = np.zeros((H, W), np.uint8); m[uv[ok, 1], uv[ok, 0]] = 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return m.astype(bool)


def cost(p):
    m = mask(p)
    return 1 - (m & ref).sum() / (m | ref).sum()

if __name__ == "__main__":
    ys, xs = np.where(ref)
    best = None
    for d in (4, 5, 6, 7, 8.5, 10, 12, 15, 20, 25, 35):
        for h in (0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6):
            f = (d - 1.8) * (xs.max() - xs.min()) / 1.70
            p0 = np.array([d, h, f, (xs.min() + xs.max()) / 2, 0, 0, 0, 0])
            gnd = proj(p0, np.array([[0.0, -1.2 * sg, 0.0]]))[0, 1]
            p0[4] = ys.max() - gnd
            c = cost(p0)
            if best is None or c < best[0]:
                best = (c, p0)
    print("init", best[0], best[1])
    SC = np.array([10, 1, 1000, 100, 100, 0.1, 0.1, 1.0])
    x = best[1] / SC
    for d0 in (5, 7, 10, 15, 25, 40):
        for h0 in (0.6, 0.9, 1.2, 1.5):
            pass
    s = minimize(lambda x: cost(x * SC), x, method="Nelder-Mead",
                 options={"maxiter": 3000, "xatol": 1e-4, "fatol": 1e-6, "initial_simplex": None})
    s.x = s.x * SC
    print("fit 1-IoU %.4f" % s.fun, "d %.2f h %.3f f %.1f u0 %.1f v0 %.1f yaw %.4f roll %.4f cx %.3f" % tuple(s.x))
    json.dump({"p": s.x.tolist(), "W": W, "H": H, "iou": 1 - s.fun}, open(os.path.join(ROOT, "tools/photomatch/grey_%s_cam.json" % view), "w"))
