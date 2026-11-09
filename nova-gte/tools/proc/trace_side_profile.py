"""Phase 2 input: the car's side profile traced on Nik's grey side picture (reference/photos/grey_studio/side.png).

- Arch openings: radial scans from each picture wheel centre (OBS WC_FL / WC_RL of tools/photomatch/solve_grey.py)
  outward-in until the dark wheel well; outliers (bumper-top shadow line, stray dark gaps) dropped, r(theta)
  smoothed. Pixel outlines kept (to cut the wheels out of the silhouette) and mapped to metres on the plane of the
  arch lips (x 0.752) with the solved side camera (tools/photomatch/grey_cams.json).
- Body silhouette: picture alpha minus the two arch openings (closed down to the ground) -> outer contour, mapped
  to metres on x 0.55 (the bumper corners / roof edge that form the side-view silhouette).
Raw metres, no fitting to the master dimensions here - phase2_profile.py does that and audits it.
Writes data/proc/side_profile_raw.json and export/match/proc_side_trace.png (trace drawn on the picture).
Run: .venv\\Scripts\\python.exe tools\\proc\\trace_side_profile.py"""
import json
import os

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PIC = os.path.join(ROOT, "reference", "photos", "grey_studio", "side.png")
CAM = os.path.join(ROOT, "tools", "photomatch", "grey_cams.json")
WHEELS = {"front": (151.75, 193.75), "rear": (520.0, 193.75)}       # picture wheel centres (solve_grey.py OBS)
X_SIL, X_ARCH = 0.55, 0.752
DARK = 22                                  # wheel well ~7; dark grey sill / skirt plastic ~34


def camera():
    J = json.load(open(CAM)); cp = np.array(J["gS"]); W, H = J["W"], J["H"]
    R, _ = cv2.Rodrigues(cp[:3]); t = cp[3:6]; f = cp[6]; C = -R.T @ t

    def hit(u, v, X):
        d = R.T @ np.array([(u - W / 2) / f, (v - H / 2) / f, 1.0])
        s = (X - C[0]) / d[0]
        p = C + s * d
        return float(p[1]), float(p[2])
    return hit


def radial_trace(L, centre, keep):
    """Body/well boundary along rays from the wheel centre, every 1 deg; keep(angle_deg) -> bool."""
    S = 8
    Lb = cv2.resize(L, None, fx=S, fy=S, interpolation=cv2.INTER_CUBIC)
    H, W = L.shape
    cx, cy = centre
    out = []
    for a in np.arange(-6, 187, 1.0):
        if not keep(a):
            continue
        ar = np.radians(a)
        for r in np.arange(80, 34, -0.125):
            u, v = cx + r * np.cos(ar), cy - r * np.sin(ar)
            if not (0 <= u < W - 1 and 0 <= v < H - 1):
                continue
            u2, v2 = cx + (r - 2) * np.cos(ar), cy - (r - 2) * np.sin(ar)
            if Lb[int(v * S), int(u * S)] < DARK and Lb[int(v2 * S), int(u2 * S)] < DARK:
                out.append((a, r))
                break
    return np.array(out)


def smooth_outline(tr, centre, sigma_deg=2.5, med_win=7, tol=2.0):
    """Robust r(theta): running-median outlier rejection, linear gap fill on a 0.5 deg grid, Gaussian smoothing."""
    a, r = tr[:, 0], tr[:, 1]
    med = np.array([np.median(r[max(0, i - med_win // 2): i + med_win // 2 + 1]) for i in range(len(r))])
    ok = np.abs(r - med) < tol
    T = np.arange(a[ok].min(), a[ok].max() + 1e-9, 0.5)
    rr = gaussian_filter1d(np.interp(T, a[ok], r[ok]), sigma_deg / 0.5, mode="nearest")
    cx, cy = centre
    return np.c_[cx + rr * np.cos(np.radians(T)), cy - rr * np.sin(np.radians(T))], int((~ok).sum())


def main():
    im = cv2.imread(PIC, cv2.IMREAD_UNCHANGED)
    a = im[..., 3:4] / 255.0
    rgb = (im[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    L = rgb.astype(float).mean(-1)
    hit = camera()
    # front arch: the bumper-top gap (dark slot at z ~0.55 in front of the arch, 134-150 deg) is not the arch edge;
    # rear arch: the bumper-top shadow line runs out of the arch at 35-62 deg.
    keeps = {"front": lambda d: not (134 <= d <= 150), "rear": lambda d: not (35 <= d <= 62)}
    arches_px, arches_m, dropped = {}, {}, {}
    for k, c in WHEELS.items():
        tr = radial_trace(L, c, keeps[k])
        px, nbad = smooth_outline(tr, c)
        arches_px[k] = px; dropped[k] = nbad
        arches_m[k] = [hit(u, v, X_ARCH) for u, v in px]
    # body mask: alpha minus arch openings closed down to the bottom of the picture
    A = (im[..., 3] > 128).astype(np.uint8)
    S = 4
    Ab = cv2.resize(A, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST)
    for k, px in arches_px.items():
        poly = np.vstack([px, [[px[-1, 0], A.shape[0] + 5], [px[0, 0], A.shape[0] + 5]]])
        cv2.fillPoly(Ab, [np.round(poly * S).astype(np.int32)], 0)
    Ab = cv2.morphologyEx(Ab, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))      # specks / thin slivers
    cnts, _ = cv2.findContours(Ab, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    body = max(cnts, key=cv2.contourArea)[:, 0, :].astype(float) / S
    body = cv2.approxPolyDP(body.astype(np.float32).reshape(-1, 1, 2), 0.15, True)[:, 0, :]
    body_m = [hit(u, v, X_SIL) for u, v in body]
    wc = {k: hit(u, v, X_ARCH) for k, (u, v) in WHEELS.items()}
    # tyre contact = lowest opaque pixel under each wheel centre (the ground line; the picture is level: same row)
    ground = {}
    for k, (u, v) in WHEELS.items():
        col = np.where(im[:, int(round(u)), 3] > 128)[0]
        ground[k] = hit(u, float(col.max()) + 0.5, X_ARCH)
    out = {"source": "reference/photos/grey_studio/side.png", "camera": "tools/photomatch/grey_cams.json gS",
           "planes": {"silhouette_x": X_SIL, "arch_x": X_ARCH},
           "wheel_centres_m": wc, "ground_m": ground, "outline_m": body_m, "outline_px": body.tolist(),
           "arch_m": arches_m, "arch_px": {k: v.tolist() for k, v in arches_px.items()},
           "arch_points_dropped": dropped}
    os.makedirs(os.path.join(ROOT, "data", "proc"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "proc", "side_profile_raw.json"), "w"), indent=1)
    # picture with the trace for checking by eye
    Z = 4
    big = cv2.resize(rgb, None, fx=Z, fy=Z, interpolation=cv2.INTER_CUBIC)
    cv2.polylines(big, [np.round(body * Z).astype(np.int32)], True, (0, 0, 255), 2)
    for px in arches_px.values():
        cv2.polylines(big, [np.round(px * Z).astype(np.int32)], False, (0, 255, 0), 2)
    for u, v in WHEELS.values():
        cv2.circle(big, (int(u * Z), int(v * Z)), 4, (255, 0, 0), -1)
    cv2.imwrite(os.path.join(ROOT, "export", "match", "proc_side_trace.png"), big)
    ys = [p[0] for p in body_m]; zs = [p[1] for p in body_m]
    print("outline points", len(body_m), "y %.3f..%.3f  z %.3f..%.3f" % (min(ys), max(ys), min(zs), max(zs)))
    print("wheel centres (m, plane x %.3f):" % X_ARCH, {k: tuple(round(c, 4) for c in v) for k, v in wc.items()})
    print("arch points dropped as outliers:", dropped)


if __name__ == "__main__":
    main()
