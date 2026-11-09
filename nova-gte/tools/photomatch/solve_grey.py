"""Camera for Nik's grey side picture (reference/photos/grey_studio/side.png, the car's LEFT side, front to the left),
solved against the bundle-adjusted 3D points of the real car (ba_result.json) from points marked by eye on the picture
(4x zoom with a pixel grid, 2026-10-19). Writes grey_cams.json {"gS": [rvec, tvec, f, k1], W, H} for
blender/scripts/grey_views.py (render the grey model through the same camera as the picture).
Run from tools/photomatch: ..\\..\\.venv\\Scripts\\python.exe solve_grey.py"""
import json

import cv2
import numpy as np
from scipy.optimize import least_squares

src = open('ba.py').read().split('# ---- initialisation')[0]
exec(src)
B = json.load(open('ba_result.json'))
P = {k: np.array(v) for k, v in B['points'].items() if isinstance(v, list) and not k.startswith('PL')}
PL = {k: np.array(v) for k, v in B['points'].items() if k.startswith('PL')}
r = B['points']['wheel_r_F400']
W, H = 667, 258
OBS = {
    'WC_FL': (151.75, 193.75), 'WC_RL': (520.0, 193.75), 'GC_FL': (151.75, 236.25), 'GC_RL': (520.0, 236.25),
    'HANDLE_F_L': (381.75, 113.75), 'HANDLE_R_L': (400.5, 113.75),
    'DG_RT_L': (399.5, 41.25), 'DG_RB_L': (399.5, 98.75),
    'QW_FT_L': (426.25, 40.0), 'QW_FB_L': (426.25, 95.0), 'QW_RB_L': (566.25, 95.0),
    'TL_TO_L': (601.25, 102.5), 'TL_BO_L': (605.0, 143.75), 'SR_L': (208.75, 118.75), 'DSR_B_L': (408.75, 187.5),
}


def solve():
    names = list(OBS)
    X = np.array([pt3(n, P, PL, r) for n in names]); I = np.array([OBS[n] for n in names])
    best = None
    for dist in (6, 10, 16, 25):
        for fk in (2, 4, 8, 14):
            C = np.array([dist, 0.0, 0.8]); look = np.array([0.0, 0.0, 0.6]) - C
            z = look / np.linalg.norm(look); x = np.cross(z, [0, 0, -1.0]); x /= np.linalg.norm(x); y = np.cross(z, x)
            R = np.stack([x, y, z]); rv, _ = cv2.Rodrigues(R)
            q0 = np.r_[rv.ravel(), -R @ C, fk * W, 0.0]

            def res(q):
                uv, d = project(q, X, W, H)
                return np.r_[(uv - I).ravel(), np.minimum(d - 0.5, 0) * 100, q[7] * 50]
            s = least_squares(res, q0, loss='soft_l1', f_scale=1.5)
            e = np.linalg.norm(project(s.x, X, W, H)[0] - I, axis=1)
            rms = float(np.sqrt(np.mean(e ** 2)))
            if best is None or rms < best[0]:
                best = (rms, s.x, e)
    rms, q, e = best
    R, _ = cv2.Rodrigues(q[:3]); C = -R.T @ q[3:6]
    print("rms %.2f px  f/W %.2f  camera at %s" % (rms, q[6] / W, C.round(2)))
    print("  " + " ".join("%s:%.1f" % (n, e[i]) for i, n in enumerate(names)))
    json.dump({"gS": [float(v) for v in q], "W": W, "H": H}, open('grey_cams.json', 'w'), indent=1)


if __name__ == "__main__":
    solve()
