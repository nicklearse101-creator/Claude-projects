"""Contact sheet of every mark in one photo, at full resolution: green = where the point was marked,
red = where the solved 3D point projects through the solved camera. Each tile is SxS photo px, scaled up.

    python marksheet.py cam [result.json] [S] [zoom]  -> export/match/marks_<cam>.png
"""
import json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
cam = sys.argv[1]
RES = sys.argv[2] if len(sys.argv) > 2 else "ba2_result_base.json"
S = int(sys.argv[3]) if len(sys.argv) > 3 else 120
Z = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PH = os.path.join(ROOT, "reference", "photos")
PHOTOS = {"c20": "user_red_gte/redgte_20.webp", "c22": "user_red_gte/redgte_22.webp", "c23": "user_red_gte/redgte_23.webp",
          "c24": "user_red_gte/redgte_24.webp", "cS": "other_sources/anglia_side.jpg", "cAR": "other_sources/anglia_rear.jpg",
          "cCF": "commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg"}
O = json.load(open("obs.json")); R = json.load(open(RES))
G = {}; exec(open("ba.py").read().split("# ---- initialisation")[0], G)
P = {n: np.array(R["points"][n]) for n in G["pairs"]}; PL = {n: np.array(R["points"][n]) for n in G["plates"]}
r = R["points"]["wheel_r_F400"]
im = cv2.imread(os.path.join(PH, PHOTOS[cam]))
if im is None:
    from PIL import Image
    im = cv2.cvtColor(np.array(Image.open(os.path.join(PH, PHOTOS[cam])).convert("RGB")), cv2.COLOR_RGB2BGR)
W, H = O[cam]["W"], O[cam]["H"]
assert im.shape[1] == W, (im.shape, W)
cp = R["cams"][cam]
names = list(O[cam]["pts"])
X = np.array([G["pt3"](n, P, PL, r) for n in names])
Rm, _ = cv2.Rodrigues(np.array(cp[0:3])); Xc = X @ Rm.T + np.array(cp[3:6]); x = Xc[:, 0] / Xc[:, 2]; y = Xc[:, 1] / Xc[:, 2]
k2 = cp[8] if len(cp) > 8 else 0.0; cx = cp[9] if len(cp) > 9 else 0.0; cy = cp[10] if len(cp) > 10 else 0.0
r2 = x * x + y * y; s = 1 + cp[7] * r2 + k2 * r2 * r2
UV = np.stack([W / 2 + cx + cp[6] * x * s, H / 2 + cy + cp[6] * y * s], 1)
pad = cv2.copyMakeBorder(im, S, S, S, S, cv2.BORDER_CONSTANT, value=(40, 40, 40))
T = int(S * Z); cols = 8; rows = (len(names) + cols - 1) // cols
sheet = np.full((rows * (T + 18), cols * T, 3), 30, np.uint8)
for k, n in enumerate(names):
    u0, v0 = O[cam]["pts"][n]
    cxp, cyp = int(round(u0)), int(round(v0))
    tile = pad[cyp: cyp + S, cxp: cxp + S].copy()        # centred on the mark (pad offset S, half tile S/2... see below)
    tile = pad[cyp + S - S // 2: cyp + S + S // 2, cxp + S - S // 2: cxp + S + S // 2].copy()
    tile = cv2.resize(tile, (T, T), interpolation=cv2.INTER_CUBIC)
    def pt(u, v):
        return (int(round((u - cxp + S // 2) * Z)), int(round((v - cyp + S // 2) * Z)))
    for (u, v), col in (((u0, v0), (60, 230, 60)), (tuple(UV[k]), (60, 60, 240))):
        a, b = pt(u, v)
        cv2.line(tile, (a - 7, b), (a - 2, b), col, 1); cv2.line(tile, (a + 2, b), (a + 7, b), col, 1)
        cv2.line(tile, (a, b - 7), (a, b - 2), col, 1); cv2.line(tile, (a, b + 2), (a, b + 7), col, 1)
    i, j = divmod(k, cols)
    sheet[i * (T + 18): i * (T + 18) + T, j * T: j * T + T] = tile
    cv2.putText(sheet, "%d %s" % (k, n), (j * T + 3, i * (T + 18) + T + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1)
out = os.path.join(ROOT, "export", "match", "marks_%s.png" % cam)
cv2.imwrite(out, sheet)
print(out, sheet.shape, "tile = %d photo px, x%.1f" % (S, Z))
