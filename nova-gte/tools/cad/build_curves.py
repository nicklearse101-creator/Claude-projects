"""FreeCAD: turn the character-line polylines into smooth B-spline curves (REPLICA_PLAN 4.1).

Each line is FITTED, not smoothed: a least-squares cubic B-spline with uniform knots by arc length, accepted only
when every input point lies within the source's own resolution - one pixel of the drawing it was traced on
(5.36 mm for the line blueprint, 3 mm otherwise). The fit starts with knots KNOT0 apart (a long, calm curve) and
halves the spacing, down to KNOT_MIN, only while a line cannot be held within that resolution. A free tolerance fit
(Part.BSplineCurve.approximate) was tried first and followed the traces' pixel staircases with 100-190 poles.

Curves go to cad/nova_lines.FCStd (one Part feature per line, left half) and are sampled into <lines>_fit.json for
Blender and tools/cad/check_lines.py.

D:\\FreeCAD\\bin\\freecadcmd.exe tools/cad/build_curves.py   (reads blender/data/cad/lines_v1.json)
"""
import json
import os

import numpy as np
import FreeCAD as App
import Part

ROOT = r"D:\Claude\vauxhall_nova_gte_1989"
SRC = os.path.join(ROOT, "blender", "data", "cad", os.environ.get("NOVA_LINES", "lines_v1.json"))
OUT_J = SRC.replace(".json", "_fit_v1method.json" if os.environ.get("FIT") == "v1" else "_fit.json")
OUT_F = os.path.join(ROOT, "cad", "nova_lines.FCStd" if SRC.endswith("v1.json") else
                     "nova_lines_" + os.path.basename(SRC)[6:-5] + ".FCStd")
os.makedirs(os.path.dirname(OUT_F), exist_ok=True)
KNOT0, KNOT_MIN = 0.12, 0.025
N = json.load(open(SRC))
V = App.Vector


def basis(x, t, k=3):
    n = len(t) - k - 1
    B = np.zeros((len(x), len(t) - 1))
    for i in range(len(t) - 1):
        B[:, i] = (x >= t[i]) & (x < t[i + 1])
    B[x >= t[-1], n - 1] = 1.0
    for d in range(1, k + 1):
        Bn = np.zeros((len(x), len(t) - 1 - d))
        for i in range(len(t) - 1 - d):
            a = (x - t[i]) / (t[i + d] - t[i]) if t[i + d] > t[i] else 0.0
            b = (t[i + d + 1] - x) / (t[i + d + 1] - t[i + 1]) if t[i + d + 1] > t[i + 1] else 0.0
            Bn[:, i] = a * B[:, i] + b * B[:, i + 1]
        B = Bn
    return B[:, :n]


def fit(P, spacing):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]; L = s[-1]; u = s / L
    # never more knot spans than the points can support: with empty spans the least-squares system is singular and
    # the curve can swing wildly - the 27 Oct 12:22 run sat at 100% CPU for 2 h on such a line
    m = max(1, min(int(round(L / spacing)), (len(P) - 1) // 3))
    inner = np.linspace(0, 1, m + 1)
    t = np.r_[[0.0] * 3, inner, [1.0] * 3]
    A = basis(u, t)
    A[0] = 0; A[0, 0] = 1; A[-1] = 0; A[-1, -1] = 1          # pin the end points
    # a faint second-difference penalty on the poles: where a knot span holds no points (a gap in a trace) the
    # minimum-norm least-squares answer put the free poles at the ORIGIN (plan_rear_bumper swung 1.7 m, 27 Oct);
    # with this they fill the gap smoothly instead, and the fit elsewhere moves by far less than a micron
    n = A.shape[1]
    D2 = np.zeros((max(n - 2, 0), n))
    for i in range(n - 2):
        D2[i, i:i + 3] = (1.0, -2.0, 1.0)
    C, *_ = np.linalg.lstsq(np.r_[A, 1e-3 * D2], np.r_[P, np.zeros((len(D2), 3))], rcond=None)
    C[0], C[-1] = P[0], P[-1]
    cur = Part.BSplineCurve()
    cur.buildFromPolesMultsKnots([V(*c) for c in C], [4] + [1] * (m - 1) + [4], list(inner), False, 3)
    return cur


def clean(pts, eps=1e-4):
    out = []
    for p in pts:
        if not out or np.linalg.norm(np.subtract(p, out[-1])) > eps:
            out.append(p)
    return np.array(out, float)


CORNER_DEG, CORNER_ARM = 35.0, 0.040


def corners(P):
    """Indices where the line turns sharply (window corners, the bottom of a shut line, the screen base).

    The turn is measured between chords CORNER_ARM (40 mm) of arc length either side, not a fixed number of points:
    over ~15 mm a single drawing-pixel step reads as a 30-40 deg turn, so the first version found 8-14 false
    'corners' on smooth lines (bonnet, belt, glass base) - kinks the surfaces must not inherit. Over 40 mm a pixel
    step is ~7 deg while a real window corner is ~90. One index per corner, the sharpest; corners closer than one
    arm to each other or to an end are dropped."""
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if s[-1] < 3 * CORNER_ARM:
        return []
    ang = np.zeros(len(P))
    for i in range(len(P)):
        if s[i] < CORNER_ARM or s[-1] - s[i] < CORNER_ARM:
            continue
        a = P[i] - P[int(np.searchsorted(s, s[i] - CORNER_ARM))]
        b = P[min(int(np.searchsorted(s, s[i] + CORNER_ARM)), len(P) - 1)] - P[i]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na > 1e-9 and nb > 1e-9:
            ang[i] = np.degrees(np.arccos(np.clip(a @ b / (na * nb), -1, 1)))
    out = []
    for i in np.argsort(-ang):
        if ang[i] < CORNER_DEG:
            break
        if all(abs(s[i] - s[j]) > CORNER_ARM for j in out):
            out.append(int(i))
    return sorted(out)


def swing(S, P):
    """Furthest the curve strays from the data (curve -> data). The data -> curve deviation alone cannot see a loop
    the curve throws across a gap in the points: 2026-10-27 the GA tail trace (a gap below the spoiler) fitted
    'within 3.6 mm' while the curve swung 1.2 m away and back."""
    sw = 0.0
    for i in range(0, len(S), 256):
        blk = S[i:i + 256]
        sw = max(sw, float(np.sqrt(((blk[:, None, :] - P[None, :, :]) ** 2).sum(-1).min(1).max())))
    return sw


FAIR_KNOT = 0.020                  # knot spacing of the fairing spline (the penalty, not the knots, sets smoothness)
MAX_TOL, RMS_TOL, OUT_TOL = 1.5, 0.6, 3.0   # x tol: worst point, RMS, and outlier cut-off
OUTLIERS = {}


def fair_fit(P, tol):
    """The fairest curve the data allow (2026-10-27, after fairness_v2 showed the 'within one pixel' fits wobbling
    5-12 mm on a 30-100 mm wavelength). Many knots (FAIR_KNOT), and a penalty on the third differences of the poles
    (change of curvature): the penalty weight is raised by bisection as far as the measurement allows - worst point
    within MAX_TOL x tol and RMS within RMS_TOL x tol, tol = one source pixel. A trace pixel is +-1 px of noise, so
    a curve that must touch every pixel to within one px has to follow the noise; one that keeps the RMS under
    0.6 px and the worst under 1.5 px follows the line. Points further than OUT_TOL x tol from the fair curve (a
    tracer hop onto the next drawn line; at most 5% of a line) are dropped and counted, never moved."""
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]; L = s[-1]; u = s / L
    m = max(1, min(int(round(L / FAIR_KNOT)), (len(P) - 1) // 2))
    inner = np.linspace(0, 1, m + 1)
    A = basis(u, np.r_[[0.0] * 3, inner, [1.0] * 3]); n = A.shape[1]
    k = 3 if n >= 5 else 2 if n >= 3 else 0
    D = np.diff(np.eye(n), k, axis=0) if k else np.zeros((0, n))
    w = np.ones(len(P)); w[0] = w[-1] = 100.0                # ends (corners, line ends) held

    def solve(lam):
        C, *_ = np.linalg.lstsq(np.r_[w[:, None] * A, np.sqrt(lam) * D], np.r_[w[:, None] * P, np.zeros((len(D), 3))],
                                rcond=None)
        C[0], C[-1] = P[0], P[-1]          # clamped: the end poles ARE the ends, so pieces meet exactly at corners
        r = np.linalg.norm(A @ C - P, axis=1)
        return C, r

    def ok(r):
        q = r[w > 0]
        return q.max() <= MAX_TOL * tol and np.sqrt((q ** 2).mean()) <= RMS_TOL * tol

    def search():
        lo, hi = -10.0, 2.0
        C, r = solve(10 ** lo)
        if not ok(r):
            return C, r, 10 ** lo
        best = (C, r, 10 ** lo)
        for _ in range(30):
            mid = 0.5 * (lo + hi); C, r = solve(10 ** mid)
            if ok(r):
                lo, best = mid, (C, r, 10 ** mid)
            else:
                hi = mid
        return best

    C, r, lam = search()
    out = (r > OUT_TOL * tol) & (w > 0)
    out[0] = out[-1] = False
    if 0 < out.sum() <= 0.05 * len(P):
        w[out] = 0.0
        C, r, lam = search()
        OUTLIERS[len(OUTLIERS)] = int(out.sum())
    cur = Part.BSplineCurve()
    cur.buildFromPolesMultsKnots([V(*c) for c in C], [4] + [1] * (m - 1) + [4], list(inner), False, 3)
    return cur, float(r[w > 0].max()), float(L / m), int(out.sum()) if 0 < out.sum() <= 0.05 * len(P) else 0


def fit_line(P, tol):
    if os.environ.get("FIT") == "v1":                    # the old 'finest knots until within one px' fit, for comparison
        return fit_line_v1(P, tol)
    cur, dev, sp, nout = fair_fit(P, tol)
    fit_line.dropped += nout
    return cur, dev, sp


fit_line.dropped = 0


def fit_line_v1(P, tol):
    sp, best = KNOT0, None
    while True:
        cur = fit(P, sp)
        S = np.array([[q.x, q.y, q.z] for q in
                      cur.discretize(Number=int(min(20000, max(200, cur.length() / 0.0005))))])
        dev = 0.0
        for i in range(0, len(P), 64):
            blk = P[i:i + 64]
            dev = max(dev, float(np.sqrt(((blk[:, None, :] - S[None, :, :]) ** 2).sum(-1).min(1).max())))
        gap = float(np.linalg.norm(np.diff(P, axis=0), axis=1).max())
        if swing(S[::8], P) > max(3 * tol, 0.6 * gap + tol):    # finer knots made it loop: keep the last good fit
            if best is not None:
                return best
        else:
            best = (cur, dev, sp)
            if dev <= tol:
                return best
        if sp <= KNOT_MIN:
            return best if best is not None else (cur, dev, sp)
        sp /= 2


def split_gaps(lines):
    """A dense line with a hole in it (a faint stretch of drawing the tracer could not see, a boundary loop that
    jumps between two mesh islands) is fitted as separate runs 'name#1', 'name#2' rather than bridged: the gap
    has no data, and a curve made to cross it only invents shape. Sparse lines (corner-to-corner, a few BA points)
    are left whole - their long steps are the data."""
    out = {}
    for name, l in lines.items():
        P = np.asarray(l["pts"], float)
        if len(P) < 20:
            out[name] = l; continue
        st = np.linalg.norm(np.diff(P, axis=0), axis=1)
        cut = np.where(st > max(0.03, 8 * float(np.median(st))))[0]
        if not len(cut):
            out[name] = l; continue
        runs = np.split(np.arange(len(P)), cut + 1)
        k = 0
        for r in runs:
            if len(r) >= 3:
                k += 1
                out["%s#%d" % (name, k)] = dict(l, pts=P[r].tolist(), src_pts=P[r].tolist(), split_from=name)
        print("%-17s split at %d gap(s) up to %.0f mm -> %d runs" % (name, len(cut), st[cut].max() * 1000, k))
    return out


doc = App.newDocument("nova_lines")
res = {}
for name, l in split_gaps(N["lines"]).items():
    P = clean(l["pts"])
    if len(P) < 2:
        continue
    # one source pixel: line blueprint 5.36 mm, GA sheet ~4 mm (3.5-4.0 mm/px before resampling), else 3 mm
    tol = 0.00536 if "line blueprint" in l["src"] else 0.004 if l["src"].startswith("GA ") else 0.003
    cs = corners(P) if len(P) > 12 else []
    if cs:
        # 2026-10-27: a line with real corners is fitted piece by piece between them, joined at the corner points,
        # so the corners stay sharp instead of being rounded off by one smooth curve
        cuts = [0] + cs + [len(P) - 1]
        pieces, devs, sps, npol = [], [], [], 0
        for a, b in zip(cuts[:-1], cuts[1:]):
            seg = P[a:b + 1]
            if len(seg) <= 3:
                c = Part.LineSegment(V(*seg[0]), V(*seg[-1])); d_, s_ = 0.0, 0.0; npol += 2
            else:
                c, d_, s_ = fit_line(seg, tol); npol += c.NbPoles
            pieces.append(c.toShape()); devs.append(d_); sps.append(s_)
        sh = Part.Wire(pieces) if len(pieces) > 1 else pieces[0]
        dev, sp = max(devs), min(s for s in sps if s > 0) if any(s > 0 for s in sps) else 0.0
        o = doc.addObject("Part::Feature", name); o.Shape = sh
        n = max(20, int(sh.Length / 0.01))
        samp = [[round(p.x, 5), round(p.y, 5), round(p.z, 5)] for p in sh.discretize(Number=n)]
        res[name] = dict(l, pts=samp, fit_dev_mm=round(dev * 1000, 2), fit_tol_mm=round(tol * 1000, 2),
                         poles=npol, knot_mm=round(sp * 1000), corners=len(cs))
        print("%-17s %4d pts -> %3d poles in %d pieces (%d corners), worst %4.1f mm of %3.1f%s" % (
            name, len(P), npol, len(pieces), len(cs), dev * 1000, tol * 1000,
            "  OVER" if dev > MAX_TOL * tol * 1.01 else ""), flush=True)
        continue
    if len(P) <= 3:
        cur = Part.BSplineCurve(); cur.interpolate([V(*p) for p in P]) if len(P) == 3 else None
        if len(P) == 2:
            cur = Part.LineSegment(V(*P[0]), V(*P[1]))
        sp, dev = 0.0, 0.0
    else:
        # deviation against a dense sampling of the curve (0.5 mm steps), plus the curve -> data swing check
        cur, dev, sp = fit_line(P, tol)
    sh = cur.toShape()
    o = doc.addObject("Part::Feature", name); o.Shape = sh
    n = max(20, int(sh.Length / 0.01))
    samp = [[round(p.x, 5), round(p.y, 5), round(p.z, 5)] for p in sh.discretize(Number=n)]
    poles = cur.NbPoles if hasattr(cur, "NbPoles") else 2
    res[name] = dict(l, pts=samp, fit_dev_mm=round(dev * 1000, 2), fit_tol_mm=round(tol * 1000, 2), poles=poles,
                     knot_mm=round(sp * 1000))
    print("%-17s %4d pts -> %3d poles (knots %3d mm), worst %4.1f mm of %3.1f%s" % (
        name, len(P), poles, sp * 1000, dev * 1000, tol * 1000, "  OVER" if dev > MAX_TOL * tol * 1.01 else ""), flush=True)
doc.saveAs(OUT_F)
print("tracer hops dropped as outliers:", fit_line.dropped, "points")
json.dump(dict(N, lines=res, _fit="fair cubic B-splines (third-difference penalty, as fair as the data allow: worst <= 1.5 px, RMS <= 0.6 px); "
               "cad/nova_lines.FCStd"), open(OUT_J, "w"), indent=1)
print("saved", OUT_F, "and", OUT_J)
