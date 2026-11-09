"""Phase 6 input: body-side features on Nik's grey side picture, in the model frame of Phase 2.
- Flare ledges over both arches: the light band (upward-facing step between the proud lower body and the inset
  upper panel); per column its bottom (the crease, a straight line) and top (arched) -> z_low(y), z_high(y).
- Door shut lines (front, rear) and the rear beltline (bottom of the quarter-window frame).
Mapping: picture -> solved side camera on the plane x 0.752 -> levelled (Phase 2 roll slope) -> y anchored on the
nearest axle with the Phase 2 scale (as the arches), z on the ground with the Phase 2 scale (body-referenced).
Writes data/proc/side_features.json. Run: .venv\\Scripts\\python.exe tools\\proc\\trace_side_features.py"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace_side_profile as tsp      # noqa: E402

AXLE = {"front": -1.141, "rear": 1.202}          # phase 1 (FIA overhangs) - checked against the blend in phase 6


def main():
    raw = json.load(open(os.path.join(ROOT, "data", "proc", "side_profile_raw.json")))
    P = json.load(open(os.path.join(ROOT, "data", "proc", "phase2_geometry.json")))["params"]
    hit = tsp.camera()
    wf = raw["wheel_centres_m"]["front"]
    k, g, b, c = P["roll_slope"], P["ground_m"], P["scale_y"], P["scale_z"]

    def to_model(u, v, half):
        y, z = hit(u, v, 0.752)
        zd = z - k * (y - wf[0])
        wy = raw["wheel_centres_m"][half][0]
        return AXLE[half] + b * (y - wy), c * (zd - g)

    im = cv2.imread(tsp.PIC, cv2.IMREAD_UNCHANGED)
    a = im[..., 3:4] / 255.0
    L = ((im[..., :3] * a + 255 * (1 - a))).mean(-1)
    S = 4
    Lb = cv2.resize(L, None, fx=S, fy=S, interpolation=cv2.INTER_CUBIC)
    bands = {}
    for half, (u0, u1, v0, v1) in {"front": (88, 206, 124, 146), "rear": (448, 586, 108, 134)}.items():
        pts = []
        for u in np.arange(u0, u1, 1.0):
            col = Lb[v0 * S:v1 * S, int(u * S)]
            vs = np.arange(v0 * S, v1 * S) / S
            if col.max() - col.min() < 25:
                continue
            idx = np.where(col > col.min() + 0.5 * (col.max() - col.min()))[0]
            runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
            r = max(runs, key=len)
            yb, zb = to_model(u, vs[r.max()], half)
            yt, zt = to_model(u, vs[r.min()], half)
            pts.append((round(float(yb), 4), round(float(zb), 4), round(float(zt), 4)))
        bands[half] = pts
    # straight crease line (band bottom) and lens height, fitted per half
    fits = {}
    for half, pts in bands.items():
        A = np.array(pts)
        keep = np.ones(len(A), bool)
        for _ in range(4):                                   # robust: drop columns off the line / the lens curve
            cl = np.polyfit(A[keep, 0], A[keep, 1], 1)
            r = A[:, 1] - np.polyval(cl, A[:, 0])
            hh = A[:, 2] - np.polyval(cl, A[:, 0])
            ch_ = np.polyfit(A[keep, 0], hh[keep], 4)
            r2 = hh - np.polyval(ch_, A[:, 0])
            keep = (np.abs(r) < 2.5 * max(r[keep].std(), 5e-4)) & (np.abs(r2) < 2.5 * max(r2[keep].std(), 5e-4))
        A = A[keep]
        cl = np.polyfit(A[:, 0], A[:, 1], 1)
        h = np.clip(A[:, 2] - np.polyval(cl, A[:, 0]), 0, None)
        ch = np.polyfit(A[:, 0], h, 4)
        fits[half] = {"crease": cl.tolist(), "lens": ch.tolist(), "y_range": [float(A[:, 0].min()), float(A[:, 0].max())],
                      "lens_max_m": float(np.polyval(ch, A[:, 0]).max()), "columns_kept": int(len(A)), "crease_rms_mm": float(np.std(np.polyval(cl, A[:, 0]) - A[:, 1]) * 1000)}
    # door shut lines (dark vertical line) and rear beltline (quarter-window frame bottom) - picture pixels
    feats = {"door_front_y": [to_model(227.0, v, "front")[0] for v in (150, 170, 190)],
             "door_rear_y": [to_model(407.5, v, "rear")[0] for v in (130, 150, 170)],
             "beltline_rear": [to_model(u, 99.0, "rear") for u in (420, 470, 520, 560)]}
    out = {"bands": bands, "fits": fits, "features": feats,
           "note": "model frame of phase 2 (y wheel-anchored per half, z body-referenced)"}
    json.dump(out, open(os.path.join(ROOT, "data", "proc", "side_features.json"), "w"), indent=1)
    for half, f in fits.items():
        print(half, "crease z = %.4f y + %.4f (rms %.1f mm), lens max %.1f mm, y %.3f..%.3f" % (
            f["crease"][0], f["crease"][1], f["crease_rms_mm"], f["lens_max_m"] * 1000, *f["y_range"]))
    print("door front y", np.round(feats["door_front_y"], 4), "door rear y", np.round(feats["door_rear_y"], 4))
    print("rear beltline", [tuple(round(x, 4) for x in p) for p in feats["beltline_rear"]])


if __name__ == "__main__":
    main()
