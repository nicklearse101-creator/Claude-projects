"""Trace the roof's outline in plan off the rectified factory sheet, and read its arch off the section.

**The arch across the car is already traced.** blender/data/section_profile.json is the front elevation's
silhouette, and above the belt that silhouette *is* the roof: half-width 0.572 m at z 1.26, 0.543 at
1.30, 0.425 at 1.34, closing to the crown at 1.378. Re-tracing the front elevation only found the
windscreen header's inner line and the mirror, so the section is used as it stands and this tool only
inverts it into a (half-width -> height) arch.

**The outline along the car has to come from the plan**, and nothing else on the sheet carries it. That
plan is a cutaway with the whole interior drawn inside it, so an outermost-ink scan is hopeless; the
symmetric-pair test from tools/trace_plan.py works here too, with the expected half-width moved in from
the body's 192 px to the roof's ~143 px. Seats, trim and label leaders have no mirrored partner at the
right distance.

As with the body's plan taper, the drawing supplies the shape and the scale is anchored on something
better: the roof's widest point has to agree with the front elevation's own silhouette, which is itself
anchored on the FIA widths. Drawings for shape, spec sheet for size.

    python tools/trace_roof.py [out.json] [diag.png]
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reference", "blueprints", "GA_rectified.png")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "blender", "data", "roof_profile.json")
DIAG = sys.argv[2] if len(sys.argv) > 2 else None

MPP_Y = 3.4970 / 1000.0                 # along the car
PX_FA, Y_FA = 1114.0, -1.1715          # BA frame (DECISIONS 2026-10-26 (9))
CY = 928                                # the plan's centreline, found in trace_plan.py
HM = 0.7746                             # the flank's full half-width, from trace_section.py

SECT = np.array(json.load(open(os.path.join(ROOT, "blender", "data", "section_profile.json")))["profile"],
                float)
SECT = SECT[np.argsort(SECT[:, 0])]
SIDE = json.load(open(os.path.join(ROOT, "blender", "data", "side_profile.json")))["lines"]

# ---- 1. the arch, inverted out of the section --------------------------------------------------
Z_SHOULDER = 1.26                       # where the roof's own curve starts, above the side glass
arch_z = SECT[SECT[:, 0] >= Z_SHOULDER, 0]
arch_h = SECT[SECT[:, 0] >= Z_SHOULDER, 1] * HM
o = np.argsort(-arch_h)                 # widest (the shoulder) first
arch_h, arch_z = arch_h[o], arch_z[o]
keep = np.r_[True, np.diff(arch_h) < -1e-6]
arch_h, arch_z = arch_h[keep][::-1], arch_z[keep][::-1]
H_SHOULDER, Z_CROWN = float(arch_h.max()), float(arch_z.max())
print("arch from the section: shoulder half %.4f m at z %.4f, crown z %.4f (dome %.0f mm)"
      % (H_SHOULDER, float(arch_z[np.argmax(arch_h)]), Z_CROWN,
         (Z_CROWN - float(arch_z[np.argmax(arch_h)])) * 1000))
for q in (0.00, 0.15, 0.30, 0.40, 0.50, 0.55, H_SHOULDER):
    zq = float(np.interp(q, arch_h, arch_z))
    print("   |x| %.3f m   z %.4f   %+6.1f mm below the crown" % (q, zq, (zq - Z_CROWN) * 1000))

# ---- 2. the outline, off the plan ---------------------------------------------------------------
A = cv2.imread(SRC, cv2.IMREAD_GRAYSCALE)
bl = cv2.GaussianBlur(A, (3, 3), 0)
INK = cv2.adaptiveThreshold(bl, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 10) > 0

SPAN = (1320, 1860)
HALF_LO, HALF_HI, HALF_WANT = 125, 165, 143
px, ph, pair = [], [], []
for x in range(*SPAN):
    idx = np.nonzero(INK[CY - 240:CY + 240, x])[0] + CY - 240
    if idx.size == 0:
        continue
    brk = np.nonzero(np.diff(idx) > 1)[0]
    c = np.array([s.mean() for s in np.split(idx, brk + 1)])
    up, dn = c[c < CY - 80], c[c > CY + 80]
    if up.size == 0 or dn.size == 0:
        continue
    best, err = None, 1e9
    for a_ in up:
        for b_ in dn:
            h = 0.5 * (b_ - a_)
            if not (HALF_LO <= h <= HALF_HI):
                continue
            e = abs((CY - a_) - (b_ - CY)) + 0.25 * abs(h - HALF_WANT)
            if e < err:
                err, best = e, (a_, b_, h)
    if best is not None:
        px.append(x); ph.append(best[2]); pair.append(best[:2])

px = np.array(px, float)
ph = np.array(ph, float)
W = 121                                 # ~420 mm: the drip rail is drawn as a close pair of lines
                                        # and the trace swaps between them; this averages them out
ph = np.convolve(np.r_[np.repeat(ph[0], W // 2), ph, np.repeat(ph[-1], W // 2)], np.ones(W) / W, "valid")
ys = Y_FA + (px - PX_FA) * MPP_Y
# The roof cannot be wider than the car's own front-elevation silhouette at the same height, and that
# silhouette is anchored on the FIA widths - so the section sets the scale, not the sheet. The drip
# gutter sits at z 1.287 (body_profile `_cant_src`), where the section reads:
Z_DRIP = 1.287
H_DRIP = float(np.interp(Z_DRIP, SECT[:, 0], SECT[:, 1])) * HM
# The taper itself does NOT come from this trace. The drip rail is drawn as a close pair of lines and
# the trace swaps between them, which is +-15 mm of noise against a real taper of about 25 mm: it comes
# out with a waist in the middle of the roof and wide ends, which is the wrong shape both ways.
# tools/photomatch/body_profile.json `glass_top_x` carries the same line properly measured - the top of
# the side glass, triangulated from the photographs (BA points DG_RT, QW_FT, QW_RT) - so the shape is
# taken from there and only the overall size from the section. The plan trace is kept as a cross-check.
PFJ = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
gtx = np.array(PFJ["glass_top_x"], float)
span = (gtx[:, 0] > -0.30) & (gtx[:, 0] < 1.35)
rel = gtx[:, 1] / float(gtx[span, 1].max())
ys_o = gtx[span, 0]
hw = H_DRIP * rel[span]
ph_at = np.interp(ys_o, ys, ph * (H_DRIP / float(np.median(ph[(ys > -0.05) & (ys < 1.20)]))))
print("\nroof outline: shape from the photographs' glass-top line, size from the section "
      "(widest %.4f m at the drip height z %.3f)" % (H_DRIP, Z_DRIP))
print("   y        this    the sheet's plan trace")
for y_, h_, p_ in zip(ys_o, hw, ph_at):
    print("   %+5.2f   %.4f   %.4f   %+4.0f mm" % (y_, h_, p_, (h_ - p_) * 1000))
ys = ys_o
for yq in ():
    if ys[0] <= yq <= ys[-1]:
        print("   y %+5.2f   half %.4f m   (%4.0f mm between the drip rails)"
              % (yq, np.interp(yq, ys, hw), 2000 * np.interp(yq, ys, hw)))

# ---- 3. the crown line along the car, straight off the side elevation ---------------------------
crown = np.array(sorted({(round(a, 5), round(b, 5))
                         for n in ("roof", "roof_b") for a, b in SIDE[n]}), float)
print("\ncrown line (side elevation): y %+.3f .. %+.3f, z %.4f .. %.4f"
      % (crown[0, 0], crown[-1, 0], crown[:, 1].min(), crown[:, 1].max()))

json.dump({
    "source": "arch: blender/data/section_profile.json (GA front elevation); outline: GA_rectified.png "
              "plan view; crown: GA line blueprint side elevation via trace_side.py",
    "note": "arch is (half-width from the centreline, height) for the roof's own curve above z %.2f; "
            "outline is the roof's half-width along the car, scaled so its widest matches the section's "
            "shoulder; crown is the roof's centreline height along the car." % Z_SHOULDER,
    "z_shoulder": Z_SHOULDER,
    "z_crown": round(Z_CROWN, 4),
    "half_shoulder": round(H_SHOULDER, 4),
    "arch": [[round(float(a), 4), round(float(b), 4)] for a, b in zip(arch_h, arch_z)],
    "outline": [[round(float(a), 4), round(float(b), 4)] for a, b in zip(ys, hw)],
    "crown": [[round(float(a), 4), round(float(b), 4)] for a, b in crown],
}, open(OUT, "w"), indent=1)
print("\nwrote", OUT)

if DIAG:
    rgb = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)
    for x, (a_, b_) in zip(px, pair):
        rgb[int(round(a_)), int(x)] = (40, 40, 220)
        rgb[int(round(b_)), int(x)] = (40, 200, 40)
    cv2.imwrite(DIAG, cv2.resize(rgb[CY - 220:CY + 220, SPAN[0] - 30:SPAN[1] + 30],
                                 (1500, int(1500 * 440 / (SPAN[1] - SPAN[0] + 60)))))
    print("wrote", DIAG)
