"""Draw a car-coordinate ruler into a photo through its solved camera, so positions can be read off the photo
in millimetres: ticks along y every 10 mm (long every 50, labelled every 100) on lines of constant z, on a
plane x = X (or a list of (z, x) pairs for a sloping side), plus z ticks on vertical lines of constant y.

    python ruler.py cam  x_or_z:x,...  z0,z1,dz  y0,y1  crop(u0,v0,u1,v1|auto)  [zoom] [out]
  e.g. python ruler.py cS 0.95:0.60,0.85:0.63 0.85,1.25,0.05 0.20,0.80 auto 2
Photo frame (z as in ba_result, no DZ).
"""
import json, os, sys
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PH = {"c20": "user_red_gte/redgte_20.webp", "c22": "user_red_gte/redgte_22.webp", "c23": "user_red_gte/redgte_23.webp",
      "c24": "user_red_gte/redgte_24.webp", "cS": "other_sources/anglia_side.jpg", "cAR": "other_sources/anglia_rear.jpg",
      "cCF": "commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg", "cRL": "commons/1989_Vauxhall_Nova_GTE_1.6_Rear.jpg"}
cam = sys.argv[1]
xz = [tuple(map(float, s.split(":")))[::-1] for s in sys.argv[2].split(",")]          # (x, z) pairs -> sorted by z
xz = sorted([(z, x) for x, z in xz])
z0, z1, dz = map(float, sys.argv[3].split(",")); y0, y1 = map(float, sys.argv[4].split(","))
Z = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
B = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ba_result.json")))
cp = np.array(B["cams"][cam]) if cam in B["cams"] else np.array(json.load(open(cam + "_cam.json"))["cam"])
path = os.path.join(ROOT, "reference", "photos", PH[cam])
im = cv2.imread(path)
if im is None:
    from PIL import Image
    im = cv2.cvtColor(np.array(Image.open(path).convert("RGB")), cv2.COLOR_RGB2BGR)
H, W = im.shape[:2]
def xof(z):
    zs = [a for a, _ in xz]; xs = [b for _, b in xz]
    return float(np.interp(z, zs, xs))
def proj(P):
    P = np.atleast_2d(P); R, _ = cv2.Rodrigues(cp[:3]); Xc = P @ R.T + cp[3:6]; x = Xc[:, 0] / Xc[:, 2]; y = Xc[:, 1] / Xc[:, 2]
    s = 1 + cp[7] * (x * x + y * y); return np.stack([W / 2 + cp[6] * x * s, H / 2 + cp[6] * y * s], 1)
zs = np.arange(z0, z1 + 1e-9, dz); ys = np.arange(round(y0, 2), y1 + 1e-9, 0.01)
corners = proj(np.array([[xof(z), y, z] for z in (z0, z1) for y in (y0, y1)]))
if sys.argv[5] == "auto":
    u0, v0 = corners.min(0) - 40; u1, v1 = corners.max(0) + 40
else:
    u0, v0, u1, v1 = map(float, sys.argv[5].split(","))
u0, v0 = int(max(u0, 0)), int(max(v0, 0)); u1, v1 = int(min(u1, W)), int(min(v1, H))
crop = cv2.resize(im[v0:v1, u0:u1], None, fx=Z, fy=Z, interpolation=cv2.INTER_CUBIC)
def P2(p):
    return (int(round((p[0] - u0) * Z)), int(round((p[1] - v0) * Z)))
for z in zs:
    pts = proj(np.array([[xof(z), y, z] for y in ys]))
    for k, y in enumerate(ys):
        mm = int(round(y * 1000))
        L = 9 if mm % 50 == 0 else 4
        # tick perpendicular-ish: draw a short vertical segment
        a = proj(np.array([[xof(z), y, z - L * 0.001], [xof(z), y, z + L * 0.001]]))
        col = (0, 255, 255) if mm % 100 == 0 else (0, 200, 0) if mm % 50 == 0 else (0, 140, 0)
        cv2.line(crop, P2(a[0]), P2(a[1]), col, 1, cv2.LINE_AA)
        if mm % 100 == 0:
            cv2.putText(crop, "%+.1f" % y, P2(a[1] + [2, -2]), 0, 0.33, (0, 255, 255), 1)
    cv2.putText(crop, "z%.2f" % z, P2(pts[0] + [-40, 0]), 0, 0.33, (255, 200, 0), 1)
out = sys.argv[7] if len(sys.argv) > 7 else os.path.join(ROOT, "export", "match", "ruler_%s.png" % cam)
cv2.imwrite(out, crop); print(out, crop.shape, "crop", u0, v0, u1, v1)
