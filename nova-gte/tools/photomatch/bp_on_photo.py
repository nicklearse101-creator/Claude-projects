"""Draw traced blueprint lines and measured BA points onto a photo, through its solved camera, on the body side.

    python bp_on_photo.py cam line,line,... x_plane [pts] [crop u0,v0,u1,v1|auto] [zoom]
Lines come from blender/data/side_profile.json (model frame, z); the photo frame is z - dz, so dz is removed.
"""
import json, os, sys
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PH = {"c20": "user_red_gte/redgte_20.webp", "c22": "user_red_gte/redgte_22.webp", "c23": "user_red_gte/redgte_23.webp",
      "c24": "user_red_gte/redgte_24.webp", "cS": "other_sources/anglia_side.jpg", "cAR": "other_sources/anglia_rear.jpg",
      "cCF": "commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg", "cRL": "commons/1989_Vauxhall_Nova_GTE_1.6_Rear.jpg"}
cam = sys.argv[1]; want = sys.argv[2].split(","); XP = float(sys.argv[3])
pts_want = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] != "-" else []
Z = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
B = json.load(open("ba_result.json")); cp = np.array(B["cams"][cam])
SP = json.load(open(os.path.join(ROOT, "blender", "data", "side_profile.json")))["lines"]
_w = json.load(open(os.path.join(ROOT, "blender", "data", "windows.json")))
SP.update({"WIN_" + k: v for k, v in _w.items() if isinstance(v, list)})
im = cv2.imread(os.path.join(ROOT, "reference", "photos", PH[cam]))
if im is None:
    from PIL import Image
    im = cv2.cvtColor(np.array(Image.open(os.path.join(ROOT, "reference", "photos", PH[cam])).convert("RGB")), cv2.COLOR_RGB2BGR)
H, W = im.shape[:2]
sgn = -1.0 if cam in ("cS",) else 1.0          # cS sees the car's right side
def proj(P):
    P = np.atleast_2d(np.asarray(P, float)); R, _ = cv2.Rodrigues(cp[:3]); Xc = P @ R.T + cp[3:6]
    x = Xc[:, 0] / Xc[:, 2]; y = Xc[:, 1] / Xc[:, 2]; s = 1 + cp[7] * (x * x + y * y)
    return np.stack([W / 2 + cp[6] * x * s, H / 2 + cp[6] * y * s], 1)
COLS = [(60, 230, 60), (240, 120, 40), (40, 230, 240), (240, 60, 240), (60, 60, 240), (255, 255, 255)]
draw = []
for i, k in enumerate(want):
    a = np.array(SP[k], float) if k.startswith("WIN_") else np.array(sorted(SP[k]), float)
    draw.append((k, proj(np.c_[np.full(len(a), sgn * XP), a[:, 0], a[:, 1]]), COLS[i % len(COLS)]))
DZ = json.load(open("body_profile.json"))["dz"]
P = B["points"]
mk = [(n, proj([[sgn * P[n][0], P[n][1], P[n][2]]])[0]) for n in pts_want if n in P]
allp = np.vstack([d[1] for d in draw] + ([np.array([m[1] for m in mk])] if mk else []))
if len(sys.argv) > 5 and sys.argv[5] != "auto":
    u0, v0, u1, v1 = map(float, sys.argv[5].split(","))
else:
    u0, v0 = allp.min(0) - 60; u1, v1 = allp.max(0) + 60
u0, v0, u1, v1 = int(max(u0, 0)), int(max(v0, 0)), int(min(u1, W)), int(min(v1, H))
out = cv2.resize(im[v0:v1, u0:u1], None, fx=Z, fy=Z, interpolation=cv2.INTER_CUBIC)
def P2(p):
    return (int(round((p[0] - u0) * Z)), int(round((p[1] - v0) * Z)))
for k, uv, col in draw:
    for a, b in zip(uv[:-1], uv[1:]):
        cv2.line(out, P2(a), P2(b), col, 1, cv2.LINE_AA)
    cv2.putText(out, k, P2(uv[len(uv) // 2] + [3, -4]), 0, 0.4, col, 1)
for n, uv in mk:
    cv2.drawMarker(out, P2(uv), (40, 40, 255), cv2.MARKER_TILTED_CROSS, 13, 2)
    cv2.putText(out, n, P2(uv + [6, 12]), 0, 0.4, (40, 40, 255), 1)
o = os.path.join(ROOT, "export", "match", "bp_%s.png" % cam)
cv2.imwrite(o, out); print(o, out.shape)
