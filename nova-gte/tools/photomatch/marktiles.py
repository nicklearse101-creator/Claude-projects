"""Tiles around where each known 3D point should be in a photo, with a pixel grid for reading marks precisely.
Grid lines every 10 px (brighter every 50), labelled in full-image px at the tile's left/top edges.
Red cross = predicted position. Existing marks (if any) in green.

    python marktiles.py cam marks.json cam_params.json result.json [names,..|all] [S] [Z] [cols]
"""
import json, os, sys
import numpy as np, cv2
cam = sys.argv[1]; mk = json.load(open(sys.argv[2])); cp = json.load(open(sys.argv[3]))["cam"]; res = json.load(open(sys.argv[4]))
want = sys.argv[5] if len(sys.argv) > 5 else "all"; S = int(sys.argv[6]) if len(sys.argv) > 6 else 100
Z = float(sys.argv[7]) if len(sys.argv) > 7 else 3.0; cols = int(sys.argv[8]) if len(sys.argv) > 8 else 5
G = {}; exec(open("ba.py").read().split("# ---- initialisation")[0], G)
P = {n: np.array(res["points"][n]) for n in G["pairs"]}; PL = {n: np.array(res["points"][n]) for n in G["plates"]}
r = res["points"]["wheel_r_F400"]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
im = cv2.imread(os.path.join(ROOT, "reference", "photos", mk["photo"])); H, W = im.shape[:2]
if want == "all":
    names = [n + s for n in G["pairs"] for s in ("_L", "_R")] + ["WC_RL", "WC_FL", "WC_RR", "WC_FR", "GC_RL", "GC_FL", "GC_RR", "GC_FR"]
else:
    names = want.split(",")
X = np.array([G["pt3"](n, P, PL, r) for n in names])
uv, d = G["project"](np.array(cp), X, W, H)
keep = [(n, u) for n, u, dd in zip(names, uv, d) if dd > 0 and 0 <= u[0] < W and 0 <= u[1] < H]
T = int(S * Z); rows = (len(keep) + cols - 1) // cols
sheet = np.full((rows * (T + 20), cols * T, 3), 25, np.uint8)
pad = cv2.copyMakeBorder(im, S, S, S, S, cv2.BORDER_CONSTANT, value=(40, 40, 40))
for k, (n, (u, v)) in enumerate(keep):
    u0, v0 = int(round(u)) - S // 2, int(round(v)) - S // 2          # tile origin in image px
    u0 -= u0 % 5; v0 -= v0 % 5                                    # snap so grid lines fall on round numbers
    t = pad[v0 + S: v0 + 2 * S, u0 + S: u0 + 2 * S].copy()
    t = cv2.resize(t, (T, T), interpolation=cv2.INTER_CUBIC)
    STEP = 5 if Z >= 4 else 10
    for g in range(0, S + 1, STEP):
        col = (255, 255, 255) if (u0 + g) % 50 == 0 else (200, 200, 200) if (u0 + g) % 10 == 0 else (90, 90, 90)
        cv2.line(t, (int(g * Z), 0), (int(g * Z), (4 if (u0 + g) % 10 else 8) if (u0 + g) % 50 else 14), col, 1)
        cv2.line(t, (int(g * Z), T - 7), (int(g * Z), T), col, 1)
        col = (255, 255, 255) if (v0 + g) % 50 == 0 else (200, 200, 200) if (v0 + g) % 10 == 0 else (90, 90, 90)
        cv2.line(t, (0, int(g * Z)), ((4 if (v0 + g) % 10 else 8) if (v0 + g) % 50 else 14, int(g * Z)), col, 1)
        cv2.line(t, (T - 7, int(g * Z)), (T, int(g * Z)), col, 1)
    LAB = 10 if S <= 70 else 50
    for g in range(0, S + 1, 5):
        if (u0 + g) % LAB == 0:
            cv2.putText(t, str(u0 + g), (int(g * Z) + 2, 26), 0, 0.36, (255, 255, 0), 1)
        if (v0 + g) % LAB == 0:
            cv2.putText(t, str(v0 + g), (16, int(g * Z) - 2), 0, 0.36, (0, 255, 255), 1)
    a, b = int((u - u0) * Z), int((v - v0) * Z)
    cv2.drawMarker(t, (a, b), (60, 60, 255), cv2.MARKER_CROSS, 14, 1)
    if n in mk["pts"]:
        mu, mv = mk["pts"][n]; cv2.drawMarker(t, (int((mu - u0) * Z), int((mv - v0) * Z)), (60, 255, 60), cv2.MARKER_TILTED_CROSS, 12, 1)
    i, j = divmod(k, cols)
    sheet[i * (T + 20): i * (T + 20) + T, j * T: j * T + T] = t
    cv2.putText(sheet, "%s  @%d,%d" % (n, u0, v0), (j * T + 3, i * (T + 20) + T + 14), 0, 0.42, (235, 235, 235), 1)
out = os.path.join(ROOT, "export", "match", "tiles_%s.png" % cam)
cv2.imwrite(out, sheet); print(out, sheet.shape, len(keep), "points:", " ".join(n for n, _ in keep))
