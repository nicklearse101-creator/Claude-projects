"""Trace the plan view off the de-keystoned factory GA sheet: the body's half-width along the car.

This is what replaces the Meshy shell as the ruler for how far out the body sits (Nik, 2026-10-26: the
shell is only for reference now that we have the drawings). The plan view is the one thing neither the
side elevation nor the photographs give directly.

Scale along the car: 3.4970 mm/px, from the side elevation's own wheelbase marks (670 px = 2343 mm) and
confirmed by the front elevation's track (378 px = 1320 mm -> 3.4921). The plan is projected directly
below the side elevation and measures 1048 px nose to tail against the side elevation's 1044.5, so the
two share this scale.

Scale across the car: NOT taken from the sheet. The photographed paper is not flat, and a single
homography leaves about 2.5% of local distortion behind - enough that the sheet disagrees with itself:
the front elevation's own 1532 marks read 1572 on the scale its own 1320 track marks give, and the plan
body reads 1498 on the scale the front elevation's 1365 height gives. So the trace here supplies the
*shape* of the taper, and one scale factor is fitted to the three SOURCED widths in docs/SPEC_SHEET.md
(FIA A-5375: 1522 mm at the front axle, 1529 at the rear, 1535 maximum). Same treatment the side
elevation's length gets: drawings for shape, spec sheet for size.

The sheet is the Nov-1990 CC GSI facelift, so the bumpers are not ours, but the body sides, the glass
and the apertures are.

    python tools/trace_plan.py [out.json] [diag.png]
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reference", "blueprints", "GA_rectified.png")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "blender", "data", "plan_profile.json")
DIAG = sys.argv[2] if len(sys.argv) > 2 else None

MPP_Y = 3.4970 / 1000.0
PX_FA = 1114.0
Y_FA = -1.1715                          # BA frame, as body_profile (DECISIONS 2026-10-26 (9))
BAND = (950, 1950, 700, 1180)           # where to look for the plan's centreline
SPAN = (918, 1966)                      # the plan body, nose to tail, in sheet px
REACH = 240                             # how far either side of the centreline the body can reach
SEED = 1340                             # a column where both edges of the body are clean
# FIA A-5375, SOURCED (docs/SPEC_SHEET.md): width at the front axle, at the rear axle, and maximum
ANCHORS = [(-1.1715, 1.522 / 2), (1.1715, 1.529 / 2), (None, 1.535 / 2)]


def to_y(px):
    return Y_FA + (np.asarray(px, float) - PX_FA) * MPP_Y


A = cv2.imread(SRC, cv2.IMREAD_GRAYSCALE)
bl = cv2.GaussianBlur(A, (3, 3), 0)
INK = cv2.adaptiveThreshold(bl, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 10) > 0

bx0, bx1, by0, by1 = BAND
rs = INK[by0:by1, bx0:bx1].sum(1)
CY = int(np.argmax(rs)) + by0
print("plan centreline at sheet y %d (%d of %d columns inked)" % (CY, rs.max(), bx1 - bx0))

# The outline cannot be taken as the outermost ink: long label leaders run alongside the plan, above it
# to "Fahrgestell-Nummer" and below it to "Motor-Nummer" / "Ausf. C", and they are straight enough that
# no median filter tells them from the body. Follow the outline from a seed instead, the same way
# tools/trace_side.py does, taking at each column the ink run nearest the predicted continuation.
runs = {}
for x in range(SPAN[0], SPAN[1] + 1):
    idx = np.nonzero(INK[CY - REACH:CY + REACH, x])[0] + CY - REACH
    if idx.size == 0:
        runs[x] = np.empty(0)
        continue
    brk = np.nonzero(np.diff(idx) > 1)[0]
    runs[x] = np.array([s.mean() for s in np.split(idx, brk + 1)])


def follow(x_seed, y_seed, x_to, tol=3.0, smooth=0.5, maxgap=12):
    step = 1 if x_to >= x_seed else -1
    out, cur, slope, gap = {x_seed: float(y_seed)}, float(y_seed), 0.0, 0
    for x in range(x_seed + step, x_to + step, step):
        c = runs.get(x)
        pred = cur + slope * step
        hit = None
        if c is not None and c.size:
            k = int(np.argmin(np.abs(c - pred)))
            if abs(c[k] - pred) <= tol + 0.4 * gap:
                hit = float(c[k])
        if hit is None:
            gap += 1
            if gap > maxgap:
                break
            cur = pred
            continue
        slope = (1 - smooth) * slope + smooth * (hit - cur) / (step * (gap + 1))
        cur, gap = hit, 0
        out[x] = cur
    return out


# Following one edge still breaks where the outline passes close to a leader. The body, though, is
# symmetric about the plan's own centreline, and the leaders are not: at each column take the pair of
# runs - one above the centreline, one below - that is most nearly symmetric about it. A leader line has
# no partner at the mirrored distance, so it cannot win.
best_t, best_b, cols = [], [], []
for x in range(SPAN[0], SPAN[1] + 1):
    c = runs.get(x)
    if c is None or c.size < 2:
        continue
    up = c[c < CY - 40]
    dn = c[c > CY + 40]
    if up.size == 0 or dn.size == 0:
        continue
    pick, err = None, 1e9
    for a_ in up:
        for b_ in dn:
            half = 0.5 * (b_ - a_)
            if not (120 <= half <= REACH):
                continue
            e = abs((CY - a_) - (b_ - CY)) + 0.15 * abs(half - 192)
            if e < err:
                err, pick = e, (a_, b_)
    if pick is None:
        continue
    cols.append(x); best_t.append(pick[0]); best_b.append(pick[1])

px = np.array(cols)
top_m = np.array(best_t)
bot_m = np.array(best_b)
half_px = 0.5 * (bot_m - top_m)
good = ~np.isnan(half_px)
ys = to_y(px[good])
hp = half_px[good]
# The outline is a pixel wide and the body is not, and the real car's width changes slowly: smooth over
# about 280 mm. Without this the trace keeps 20-30 mm dips where a label leader crowds the outline.
W = 81
hp = np.convolve(np.r_[np.repeat(hp[0], W // 2), hp, np.repeat(hp[-1], W // 2)], np.ones(W) / W, "valid")
print("plan body %d px long -> %.0f mm at the along-car scale (side elevation reads 1044.5 px)"
      % (px[-1] - px[0], (px[-1] - px[0]) * MPP_Y * 1000))

# one scale factor, least squares onto the three sourced widths
rows = []
for y_a, h_a in ANCHORS:
    meas = float(np.max(hp)) if y_a is None else float(np.interp(y_a, ys, hp))
    rows.append((meas, h_a))
scale = sum(m * h for m, h in rows) / sum(m * m for m, h in rows)
print("lateral scale fitted to the sourced widths: %.5f m/px" % scale)
for (meas, h_a), (y_a, _) in zip(rows, ANCHORS):
    where = "maximum" if y_a is None else "y %+.4f" % y_a
    print("   %-12s  drawn %6.1f px -> %.4f m   sourced %.4f   resid %+3.0f mm"
          % (where, meas, meas * scale, h_a, (meas * scale - h_a) * 1000))

hw = hp * scale
print("\nhalf-width along the car:")
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
old = np.array(PF["halfw"], float)
for yq in (-1.70, -1.50, -1.141, -0.80, -0.40, 0.0, 0.40, 0.80, 1.171, 1.45, 1.65):
    if ys[0] <= yq <= ys[-1]:
        a = float(np.interp(yq, ys, hw))
        b = float(np.interp(yq, old[:, 0], old[:, 1]))
        print("   y %+6.3f   plan %.4f   body_profile %.4f   %+4.0f mm" % (yq, a, b, (a - b) * 1000))

# Merge with the FIA-anchored curve. Between the arches the FIA figures are SOURCED at three stations
# and the body is parallel, so they win there; at the two ends body_profile says ESTIMATE and the plan
# is the only measurement of the taper, so the plan wins. Blended over 200 mm either side.
BLEND = [(-1.45, -1.25), (1.25, 1.45)]
merged = []
for y, h in zip(ys, hw):
    hb = float(np.interp(y, old[:, 0], old[:, 1]))
    if y <= BLEND[0][0] or y >= BLEND[1][1]:
        w = 1.0
    elif y >= BLEND[0][1] and y <= BLEND[1][0]:
        w = 0.0
    elif y < 0:
        w = (BLEND[0][1] - y) / (BLEND[0][1] - BLEND[0][0])
    else:
        w = (y - BLEND[1][0]) / (BLEND[1][1] - BLEND[1][0])
    merged.append([round(float(y), 4), round(float(w * h + (1 - w) * hb), 4)])
print("merged: plan at the ends (where body_profile is an ESTIMATE), FIA between the arches")

json.dump({
    "source": "reference/blueprints/GA_rectified.png, plan view (Ausfuehrung bb)",
    "halfw_merged": merged,
    "merged_note": "plan taper outboard of y -1.25 / +1.25, FIA-anchored body_profile halfw between "
                   "them, blended over 200 mm; use this one",
    "mm_per_px_along": MPP_Y * 1000,
    "m_per_px_across": round(scale, 6),
    "note": "taper traced off the plan; one lateral scale fitted to the FIA A-5375 widths, because the "
            "photographed sheet keeps about 2.5% local distortion after rectifying. Nov-1990 CC GSI "
            "facelift sheet: body sides and apertures yes, bumpers no",
    "halfw": [[round(float(a), 4), round(float(b), 4)] for a, b in zip(ys, hw)],
}, open(OUT, "w"), indent=1)
print("\nwrote", OUT)

if DIAG:
    rgb = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)
    for i, x in enumerate(px):
        rgb[int(round(top_m[i])), x] = (40, 40, 220)
        rgb[int(round(bot_m[i])), x] = (40, 160, 40)
    cv2.imwrite(DIAG, rgb[by0 - 40:by1 + 20, SPAN[0] - 40:SPAN[1] + 40])
    print("wrote", DIAG)
