"""How fair (un-wonky) each fitted character line is, before any surface is built on it.

A surface built through a curve network copies every wobble of the curves into its panels, so each line is measured:
  wobble_mm   max distance from a FAIR reference of the same line: a least-squares cubic with knots every
              FAIR_KNOT (200 mm), fitted piece by piece between real corners (turn > 35 deg over 40 mm chords).
              Whatever the line does on a shorter wavelength than that is wobble.
  wiggles/m   sign changes per metre of the second derivative of x, y and z along the arc (30 mm stencil, above a
              noise floor) - a fair panel line has very few; a pixel-chasing one has dozens.
  out-of-plane  for lines that should be flat (shut lines, lamps, windows) the RMS distance from their best plane.
Output: export/cad/fairness/fairness.txt (sorted, worst first) and sheet_*.png (each line drawn in its two main
projections with its fair reference, wobble exaggerated x10), plus blender/data/cad/fairness_<tag>.json.

python tools/cad/fairness.py [lines_fit.json] [tag]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "blender", "data", "cad", "lines_v2_fit.json")
TAG = sys.argv[2] if len(sys.argv) > 2 else "v2"
OD = os.path.join(ROOT, "export", "cad", "fairness_" + TAG)
os.makedirs(OD, exist_ok=True)
N = json.load(open(SRC))["lines"]
FAIR_KNOT, CORNER_ARM, CORNER_DEG = 0.200, 0.040, 35.0


def resample(P, step=0.005):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if s[-1] < step * 3:
        return P, s
    t = np.arange(0, s[-1], step)
    return np.c_[[np.interp(t, s, P[:, i]) for i in range(3)]].T, t


def corners(P, s):
    out, ang = [], np.zeros(len(P))
    if s[-1] < 3 * CORNER_ARM:
        return []
    for i in range(len(P)):
        if s[i] < CORNER_ARM or s[-1] - s[i] < CORNER_ARM:
            continue
        a = P[i] - P[int(np.searchsorted(s, s[i] - CORNER_ARM))]
        b = P[min(int(np.searchsorted(s, s[i] + CORNER_ARM)), len(P) - 1)] - P[i]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na > 1e-9 and nb > 1e-9:
            ang[i] = np.degrees(np.arccos(np.clip(a @ b / (na * nb), -1, 1)))
    for i in np.argsort(-ang):
        if ang[i] < CORNER_DEG:
            break
        if all(abs(s[i] - s[j]) > CORNER_ARM for j in out):
            out.append(int(i))
    return sorted(out)


def bspl(u, m):
    t = np.r_[[0.0] * 3, np.linspace(0, 1, m + 1), [1.0] * 3]
    B = np.zeros((len(u), len(t) - 1))
    for i in range(len(t) - 1):
        B[:, i] = (u >= t[i]) & (u < t[i + 1])
    B[u >= 1.0, m + 2] = 1.0
    for d in range(1, 4):
        Bn = np.zeros((len(u), len(t) - 1 - d))
        for i in range(len(t) - 1 - d):
            a = (u - t[i]) / (t[i + d] - t[i]) if t[i + d] > t[i] else 0
            b = (t[i + d + 1] - u) / (t[i + d + 1] - t[i + 1]) if t[i + d + 1] > t[i + 1] else 0
            Bn[:, i] = a * B[:, i] + b * B[:, i + 1]
        B = Bn
    return B[:, :m + 3]


def fair_ref(P, s):
    if len(P) < 8:
        return P.copy()
    L = s[-1]; m = max(1, int(round(L / FAIR_KNOT))); u = (s - s[0]) / max(L - s[0], 1e-9)
    A = bspl(u, m)
    C, *_ = np.linalg.lstsq(A, P, rcond=None)
    return A @ C


def wiggles(P, s, h=6):                       # 6 x 5 mm = 30 mm stencil
    if len(P) < 2 * h + 3:
        return 0
    d2 = P[2 * h:] - 2 * P[h:-h] + P[:-2 * h]
    n = 0
    for k in range(3):
        v = d2[:, k]; floor = 0.15 * np.abs(v).max() + 2e-6
        sg = np.sign(v[np.abs(v) > floor])
        n += int((np.diff(sg) != 0).sum())
    return n / max(s[-1], 1e-6)


rows, res = [], {}
for name, l in N.items():
    P0 = np.array(l["pts"], float)
    if len(P0) < 3:
        continue
    P, s = resample(P0)
    cs = corners(P, s)
    cuts = [0] + cs + [len(P) - 1]
    R = np.zeros_like(P)
    for a, b in zip(cuts[:-1], cuts[1:]):
        R[a:b + 1] = fair_ref(P[a:b + 1], s[a:b + 1])
    dev = np.linalg.norm(P - R, axis=1)
    w = np.mean([wiggles(P[a:b + 1], s[a:b + 1] - s[a]) for a, b in zip(cuts[:-1], cuts[1:])])
    c = P - P.mean(0); ev = np.linalg.svd(c, full_matrices=False)[1]
    oop = ev[2] / np.sqrt(len(P))
    res[name] = dict(wobble_mm=round(float(dev.max()) * 1000, 1), wobble_rms_mm=round(float(np.sqrt((dev ** 2).mean())) * 1000, 2),
                     wiggles_per_m=round(float(w), 1), out_of_plane_mm=round(float(oop) * 1000, 1),
                     length_m=round(float(s[-1]), 3), corners=len(cs), group=l["group"], src=l["src"])
    # signed curvature in the line's main plane, from the curve's own samples (~10 mm apart, 3-sample stencil);
    # a fair line has a smooth curvature plot with few extremes - wobble shows as a saw-tooth
    ax2 = sorted(np.argsort(-(P0.max(0) - P0.min(0)))[:2])
    Q = P0[:, ax2]; h = 3
    if len(Q) > 2 * h + 2:
        a, b, c = Q[:-2 * h], Q[h:-h], Q[2 * h:]
        cr = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        la, lb, lc = np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(c - a, axis=1)
        kap = 2 * cr / np.maximum(la * lb * lc, 1e-12)
        sk = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P0, axis=0), axis=1))][h:-h]
        kc = np.clip(kap, -20, 20)                               # corners clip at r = 50 mm
        dk = np.diff(kc); ext = int(((dk[:-1] * dk[1:]) < 0)[np.abs(kc[1:-1]) > 0.5].sum()) if len(dk) > 2 else 0
    else:
        kap, sk, ext = np.zeros(0), np.zeros(0), 0
    res[name]["curv_extrema_per_m"] = round(ext / max(s[-1], 1e-6), 1)
    rows.append((dev.max(), name, P, R, dev, kap, sk))
rows.sort(key=lambda r: -r[0])
with open(os.path.join(OD, "fairness.txt"), "w") as f:
    f.write("%-28s %-11s %8s %8s %9s %8s %7s %6s  %s\n" % ("line", "group", "wobble", "rms", "wiggle/m", "kext/m", "oop", "len", "source"))
    for _, n, *_ in rows:
        r = res[n]
        f.write("%-28s %-11s %6.1fmm %6.2fmm %9.1f %8.1f %5.1fmm %5.2fm  %s\n" % (
            n, r["group"], r["wobble_mm"], r["wobble_rms_mm"], r["wiggles_per_m"], r["curv_extrema_per_m"], r["out_of_plane_mm"], r["length_m"], r["src"][:50]))
json.dump(res, open(os.path.join(ROOT, "blender", "data", "cad", "fairness_%s.json" % TAG), "w"), indent=1)

# sheets: 4 x 4 panels, each line in its two widest projections, data (black) vs fair reference (green),
# the difference exaggerated x10 (red)
PW, PH, COLS, ROWS_ = 420, 300, 4, 4
for sheet in range(0, min(len(rows), 48), COLS * ROWS_):
    img = Image.new("RGB", (PW * COLS, PH * ROWS_), "white"); d = ImageDraw.Draw(img)
    for k, (wmax, n, P, R, dev, kap, sk) in enumerate(rows[sheet:sheet + COLS * ROWS_]):
        ox, oy = (k % COLS) * PW, (k // COLS) * PH
        span = P.max(0) - P.min(0); ax = np.argsort(-span)[:2]; ax = sorted(ax)
        if 1 in ax:
            ax = [1, [a for a in ax if a != 1][0]]          # y (along the car) horizontal when involved
        X = P[:, ax]; Rr = R[:, ax]; E = Rr + 10 * (X - Rr)
        lo = np.minimum(X.min(0), E.min(0)); hi = np.maximum(X.max(0), E.max(0)); sc = min((PW - 20) / max(hi[0] - lo[0], 1e-6), (PH - 50) / max(hi[1] - lo[1], 1e-6))

        def tp(Q):
            return [(ox + 10 + (q[0] - lo[0]) * sc, oy + PH - 10 - (q[1] - lo[1]) * sc) for q in Q]
        d.line(tp(Rr), fill=(0, 170, 0), width=3); d.line(tp(E), fill=(220, 0, 0), width=1); d.line(tp(X), fill=(0, 0, 0), width=1)
        d.rectangle([ox, oy, ox + PW - 1, oy + PH - 1], outline=(180, 180, 180))
        if len(kap) > 2:                                         # curvature strip along the top, +-10 /m
            y0 = oy + 50; kk = np.clip(kap, -10, 10)
            d.line([(ox + 10, y0), (ox + PW - 10, y0)], fill=(200, 200, 255))
            d.line([(ox + 10 + (sv - sk[0]) / max(sk[-1] - sk[0], 1e-6) * (PW - 20), y0 - kv * 3) for sv, kv in zip(sk, kk)],
                   fill=(0, 0, 230), width=1)
        d.text((ox + 6, oy + 4), "%s  wobble %.1f mm  %.0f curv-ext/m  [%s,%s]" % (n, wmax * 1000, res[n]["curv_extrema_per_m"], "xyz"[ax[0]], "xyz"[ax[1]]), fill=(0, 0, 0))
    img.save(os.path.join(OD, "sheet_%d.png" % (sheet // (COLS * ROWS_) + 1)))
print(open(os.path.join(OD, "fairness.txt")).read())
