"""Sub-pixel corners of a yellow/white number plate: threshold the plate's colour, take the biggest blob, fit a
straight line to each of its four sides (RANSAC-free: the side's own edge pixels, by least squares) and
intersect them. Prints TL TR BR BL in full-image pixels.

    python plate_corners.py image x0 y0 x1 y1 [yellow|white]
"""
import sys
import cv2
import numpy as np
path = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); kind = sys.argv[6] if len(sys.argv) > 6 else "yellow"
im = cv2.imread(path)[y0:y1, x0:x1]
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
if kind == "yellow":
    m = cv2.inRange(hsv, (15, 90, 120), (40, 255, 255))
else:
    m = cv2.inRange(hsv, (0, 0, 170), (180, 50, 255))
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(m)
k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
blob = (lab == k).astype(np.uint8) * 255
blob = cv2.morphologyEx(blob, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))     # fill the black lettering
cnt = max(cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)[:, 0, :].astype(float)
# split the outline by tangent direction: the plate's straight sides have two dominant directions; the rounded
# corners sit in between and are left out. Each side is then a straight-line fit (Huber) to its own pixels.
n = len(cnt); tng = cnt[(np.arange(n) + 4) % n] - cnt[(np.arange(n) - 4) % n]
ang = np.degrees(np.arctan2(tng[:, 1], tng[:, 0])) % 180
hist = np.histogram(ang, bins=180, range=(0, 180))[0]
a_h = float(np.argmax(np.convolve(np.r_[hist, hist[:10]], np.ones(5), "same")[:180]))      # most common: the long sides
def near(a, a0, tol=12):
    return np.abs((a - a0 + 90) % 180 - 90) < tol
rest = ~near(ang, a_h, 30)
a_v = float(np.median(ang[rest])) if rest.any() else (a_h + 90) % 180
cen = cnt.mean(0)
lines = []
for a0 in (a_h, a_v):
    sel = cnt[near(ang, a0)]
    t = np.array([np.cos(np.radians(a0)), np.sin(np.radians(a0))]); nrm = np.array([-t[1], t[0]])
    off = (sel - cen) @ nrm
    for side in (off < 0, off > 0):
        q = sel[side].astype(np.float32)
        vx, vy, x_, y_ = cv2.fitLine(q, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        d = np.array([vx, vy]); p0 = np.array([x_, y_]); nn = np.array([-vy, vx])
        lines.append((p0, d, len(q), float(np.sqrt(np.mean(((q - p0) @ nn) ** 2)))))
def inter(l1, l2):
    (p1, d1, *_), (p2, d2, *_) = l1, l2
    ts = np.linalg.solve(np.array([d1, -d2]).T, p2 - p1); return p1 + ts[0] * d1
P4 = np.array([inter(lines[i], lines[j]) for i in (0, 1) for j in (2, 3)])
c = P4.mean(0); P4 = P4[np.argsort(np.arctan2(P4[:, 1] - c[1], P4[:, 0] - c[0]))]
pts = list(P4)
pts = np.array(pts) + [x0, y0]
# the contour runs on the outer pixel boundary; a pixel-centre convention moves it in by 0.5 px - negligible here
for nm, p in zip(("TL", "TR", "BR", "BL"), pts):
    print("%s %.1f %.1f" % (nm, *p))
print("side fit rms px:", " ".join("%.2f(%d)" % (l[3], l[2]) for l in lines))
w_top, w_bot = np.linalg.norm(pts[1] - pts[0]), np.linalg.norm(pts[2] - pts[3]); h_l, h_r = np.linalg.norm(pts[3] - pts[0]), np.linalg.norm(pts[2] - pts[1])
print("aspect %.3f (520/111 = %.3f)" % ((w_top + w_bot) / (h_l + h_r), 520 / 111))
