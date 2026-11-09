"""Trace the body's cross-section - how far out the side sits at each height - off the rectified GA sheet.

The plan view gives the taper along the car and the side elevation gives the panel outlines, but neither
says how the flank leans in from the sill to the belt. The front elevation does: it is a projection, so
at each height its silhouette is the widest the body gets anywhere along the car, which is exactly the
section envelope.

Only the front elevation is usable. The rear one has the tailgate, the lamps and half a dozen label
leaders crossing its silhouette and comes out unreadable.

Two things the trace has to survive:
  - the label leaders reach the car from one side only, so the nearer of the two sides is taken at each
    row and the leader is ignored;
  - the door mirrors stick out at about z 0.95, well outside the body, and are cut out by hand.

The result is normalised, so it carries shape only; the absolute width comes from the plan trace, which
is itself anchored on the FIA widths. The sheet is the Nov-1990 CC GSI facelift, so the section below
about z 0.55 is its bumper, not ours - our own front end is measured in tools/front_end.py and the
sill/skirt comes from the photographs.

    python tools/trace_section.py [out.json] [diag.png]
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reference", "blueprints", "GA_rectified.png")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "blender", "data", "section_profile.json")
DIAG = sys.argv[2] if len(sys.argv) > 2 else None

MPP_X = 3.4970 / 1000.0                 # along the sheet's x, from the side elevation's wheelbase marks
VSC = 1365.0 / 355.5 / 1000.0           # the sheet's vertical scale, from the front elevation's own 1365
GROUND, X0, X1 = 515, 2210, 2725        # the front elevation on the rectified sheet
MIRROR_Z = (0.88, 1.02)                 # the door mirrors stick out over this band
MED = 19

A = cv2.imread(SRC, cv2.IMREAD_GRAYSCALE)
bl = cv2.GaussianBlur(A, (3, 3), 0)
INK = cv2.adaptiveThreshold(bl, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 10) > 0

L, R, Z, rows = [], [], [], []
for y in range(GROUND - 4, 155, -1):
    idx = np.nonzero(INK[y, X0:X1])[0] + X0
    if idx.size < 2:
        continue
    L.append(float(idx[0])); R.append(float(idx[-1])); Z.append((GROUND - y) * VSC); rows.append(y)
L, R, Z = np.array(L), np.array(R), np.array(Z)
CX = float(np.median(0.5 * (L + R)))
half = np.minimum(CX - L, R - CX) * MPP_X
print("front elevation: centreline x %.1f, %d rows, z %.3f..%.3f" % (CX, len(Z), Z.min(), Z.max()))

sm = half.copy()
for i in range(len(half)):
    sm[i] = float(np.median(half[max(0, i - MED // 2):i + MED // 2 + 1]))

keep = ~((Z > MIRROR_Z[0]) & (Z < MIRROR_Z[1]))
zk, hk = Z[keep], sm[keep]
order = np.argsort(zk)
zk, hk = zk[order], hk[order]
hk = np.interp(Z, zk, hk)               # bridge the mirror band
# Normalise on the flank's own full width - the median over the band where the side is parallel - not
# on a maximum. The sheet has a few percent of rows reading several centimetres wide where a leader
# touches both sides at once, and a maximum of any kind lands on those.
band = (Z > 0.20) & (Z < 0.65)
hmax = float(np.median(hk[band]))
prof = hk / hmax
# Nothing on the body sits outboard of the flank, so cap the profile there; the few rows that read
# wider are leaders touching both sides at once. Above the flank the greenhouse only ever narrows, so
# enforce that too - otherwise a leader across the glass puts a bulge in the roof.
prof = np.minimum(prof, 1.0)
up = np.argsort(Z)
zs_, ps_ = Z[up], prof[up]
top_band = zs_ > 0.65
ps_[top_band] = np.minimum.accumulate(ps_[top_band])
prof[up] = ps_
# A median filter leaves plateaus, and normalising then forcing the greenhouse to narrow puts the steps
# back: adjacent rows 3.8 mm apart were jumping up to 7 mm of width. On a panel that spans a lot of
# height - the wing above all - those steps read as horizontal bands across the paint. A running mean
# over about 25 mm takes the staircase out without moving the shape (the two differ by under 1 mm).
SM = 15
_p = np.r_[np.repeat(prof[up][0], SM // 2), prof[up], np.repeat(prof[up][-1], SM // 2)]
prof[up] = np.convolve(_p, np.ones(SM) / SM, "valid")
_b = (zs_ > 0.35) & (zs_ < 0.85)
print("staircase removed: over the wing's band the row-to-row kink falls from %.2f mm to %.2f mm"
      % (np.abs(np.diff(ps_[_b], 2)).mean() * hmax * 1000,
         np.abs(np.diff(prof[up][_b], 2)).mean() * hmax * 1000))
print("flank full width %.4f m over z 0.20..0.65  (FIA half-width 0.7675: the sheet reads %+.1f%%)"
      % (hmax, 100 * (hmax / 0.7675 - 1)))
print("\nsection, normalised to the widest:")
for zq in (0.20, 0.30, 0.40, 0.47, 0.55, 0.65, 0.75, 0.80, 0.86, 0.95, 1.05, 1.15, 1.25, 1.33):
    if Z.min() <= zq <= Z.max():
        print("   z %.2f   %.4f   (%+4.0f mm off the widest)"
              % (zq, np.interp(zq, Z, prof), (np.interp(zq, Z, prof) - 1.0) * hmax * 1000))

json.dump({
    "source": "reference/blueprints/GA_rectified.png, front elevation silhouette",
    "note": "normalised section envelope: width at this height divided by the widest. Mirrors cut out "
            "over z %.2f..%.2f. Facelift sheet, so below about z 0.55 this is its bumper, not ours."
            % MIRROR_Z,
    "z_widest": round(float(Z[band][int(np.argmax(hk[band]))]), 4),
    "profile": [[round(float(z), 4), round(float(p), 5)] for z, p in zip(Z, prof)][::-1],
}, open(OUT, "w"), indent=1)
print("\nwrote", OUT)

if DIAG:
    rgb = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)
    for i, y in enumerate(rows):
        d = int(round(sm[i] / MPP_X))
        rgb[y, int(CX - d)] = (40, 40, 220)
        rgb[y, int(CX + d)] = (40, 160, 40)
    cv2.imwrite(DIAG, rgb[140:540, X0 - 30:X1 + 30])
    print("wrote", DIAG)
