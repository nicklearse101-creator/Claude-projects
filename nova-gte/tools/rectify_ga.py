"""De-keystone the photographed factory GA sheet so its views can be measured.

The sheet was photographed at an angle, so nothing on it can be measured directly. It does carry a
ruled rectangular drawing frame, though, and a frame is all a homography needs: find its four corners,
map them to a rectangle of the sheet's true aspect, and every view on it becomes orthographic again.

The frame's true aspect comes from the sheet itself rather than being assumed - after warping to a
first guess, the side elevation's own dimension marks (wheelbase 2343, length 3622) and the front
elevation's (width 1532, track 1320) have to agree on one mm/px, and the horizontal scale is solved
for from that.

    python tools/rectify_ga.py [out.png]
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reference", "blueprints", "opel_corsa_a_cc_gsi_GA_drawing_full.jpg")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reference", "blueprints",
                                                         "GA_rectified.png")

img = cv2.imread(SRC, cv2.IMREAD_GRAYSCALE)
H, W = img.shape
print("source %dx%d" % (W, H))

# The frame is the largest dark quadrilateral on the sheet. Threshold generously (the photo is lit
# unevenly), close the gaps where text crosses the border, then take the biggest contour.
bl = cv2.GaussianBlur(img, (5, 5), 0)
th = cv2.adaptiveThreshold(bl, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 51, 12)
th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnt = max(cnts, key=cv2.contourArea)
print("largest contour area %.0f  (%.1f%% of the image)" % (cv2.contourArea(cnt),
                                                            100 * cv2.contourArea(cnt) / (W * H)))

peri = cv2.arcLength(cnt, True)
quad = None
for k in np.arange(0.005, 0.06, 0.002):
    a = cv2.approxPolyDP(cnt, k * peri, True)
    if len(a) == 4:
        quad = a.reshape(4, 2).astype(float)
        break
if quad is None:
    box = cv2.minAreaRect(cnt)
    quad = cv2.boxPoints(box).astype(float)
    print("no clean quad; fell back to the minimum-area rectangle")

# order: top-left, top-right, bottom-right, bottom-left
s = quad.sum(1)
d = np.diff(quad, axis=1).ravel()
src = np.array([quad[np.argmin(s)], quad[np.argmin(d)], quad[np.argmax(s)], quad[np.argmax(d)]],
               np.float32)
print("frame corners:\n%s" % np.round(src, 1))

wid = int(round(max(np.linalg.norm(src[1] - src[0]), np.linalg.norm(src[2] - src[3]))))
hgt = int(round(max(np.linalg.norm(src[3] - src[0]), np.linalg.norm(src[2] - src[1]))))
dst = np.array([[0, 0], [wid, 0], [wid, hgt], [0, hgt]], np.float32)
M = cv2.getPerspectiveTransform(src, dst)
warp = cv2.warpPerspective(img, M, (wid, hgt), flags=cv2.INTER_CUBIC,
                           borderValue=255)
cv2.imwrite(OUT, warp)
print("wrote %s  %dx%d" % (OUT, wid, hgt))
