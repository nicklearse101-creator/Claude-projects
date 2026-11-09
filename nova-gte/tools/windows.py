"""Build the two side-window apertures as closed outlines, from the blueprint traces.

Both the line blueprint and the side photograph put the glass edges in the same places - the traces were drawn
onto anglia_side through its solved camera and land on the real car's window edges (tools/photomatch/
bp_on_photo.py, 2026-10-26) - so each aperture is four traced edges:

  door window      dw_front_edge / dlo_top_fwd + dlo_top_b / dw_rear_edge / dw_bot + dw_bot_b
  quarter window   qw_front_edge / qw_top + qw_top_b / the rest of qw_top_b (the C-pillar's leading edge, which
                   IS the window's rear edge, where the traced top turns down) / qw_bot + qw_bot_b

Each edge becomes a function - z(y) for the top and bottom, y(z) for the sides - fitted straight beyond its
traced span, and the four corners are where they cross. That keeps the corners on the traced lines instead of
wherever two polylines happened to stop.

The triangulated corners DG_RT / DG_RB are NOT used: on the photograph they sit in the middle of the B-pillar,
about 55 mm behind the glass edge that the blueprint and the picture agree on. QW_FT / QW_FB / QW_RT / QW_RB do
sit on the outline, and the traced quarter top runs ~13 mm above QW_FT and QW_RT, so the quarter window's top
and bottom are shifted onto them (front-to-rear ramp). The door window needs no shift: its traced top passes
through DG_RT's height exactly.

Output: blender/data/windows.json, model frame (the drawing is on unloaded tyres, so no dz).

    python tools/windows.py
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "blender", "data")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PF = json.load(open(os.path.join(ROOT, "tools", "photomatch", "body_profile.json")))
BA = json.load(open(os.path.join(ROOT, "tools", "photomatch", "ba_result.json")))["points"]
DZ = float(PF["dz"])


def merge(*names):
    a = np.array(sorted({(round(y, 5), round(z, 5)) for n in names for y, z in SP[n]}), float)
    return a[np.argsort(a[:, 0])]


def flat_run(a, tol=0.006):
    """Keep the longest run of the line that holds one height: the traced glass base jumps to the door trim at
    the front and climbs the pillar's lower corner at the rear, and both would drag a corner off the glass."""
    z = a[:, 1]
    best, run, start = (0, 0, 0), 1, 0
    for i in range(1, len(a)):
        if abs(z[i] - z[i - 1]) <= tol:
            run += 1
        else:
            start, run = i, 1
        if run > best[0]:
            best = (run, start, i + 1)
    return a[best[1]:best[2]]


def smooth(a, n=7):
    if len(a) < n:
        return a
    pad = np.r_[np.repeat(a[0, 1], n // 2), a[:, 1], np.repeat(a[-1, 1], n // 2)]
    b = a.copy(); b[:, 1] = np.convolve(pad, np.ones(n) / n, "valid")
    return b


class Edge:
    """A traced edge as f(u), straight (least-squares over the nearest 8 samples) beyond the traced span."""

    def __init__(self, pts, flip=False):
        a = np.array(pts, float)
        if flip:
            a = a[:, ::-1]
        a = a[np.argsort(a[:, 0])]
        # one value per u, so a near-vertical edge traced row by row becomes a function
        us = np.unique(np.round(a[:, 0], 4))
        self.u = us
        self.v = np.array([a[np.abs(a[:, 0] - u) < 5e-5, 1].mean() for u in us])
        self.lo = np.polyfit(self.u[:8], self.v[:8], 1)
        self.hi = np.polyfit(self.u[-8:], self.v[-8:], 1)

    def __call__(self, u):
        u = np.atleast_1d(np.asarray(u, float))
        v = np.interp(u, self.u, self.v)
        v[u < self.u[0]] = np.polyval(self.lo, u[u < self.u[0]])
        v[u > self.u[-1]] = np.polyval(self.hi, u[u > self.u[-1]])
        return v if v.size > 1 else float(v[0])


def corner(side, horiz, y0):
    """Where a side edge y(z) meets a top/bottom edge z(y); y0 seeds the iteration."""
    y = float(y0)
    for _ in range(60):
        z = float(horiz(y))
        y_new = float(side(z))
        if abs(y_new - y) < 1e-7:
            y = y_new
            break
        y += 0.5 * (y_new - y)
    return float(y), float(horiz(y))


def build(front, rear, top, bot, n_v=16, n_h=64):
    fb = corner(front, bot, front(bot(front(1.0))))
    ft = corner(front, top, fb[0])
    rt = corner(rear, top, rear(top(rear(1.2))))
    rb = corner(rear, bot, rt[0])
    zs = np.linspace(fb[1], ft[1], n_v)
    loop = [(float(front(z)), float(z)) for z in zs]
    ys = np.linspace(ft[0], rt[0], n_h)
    loop += [(float(y), float(top(y))) for y in ys[1:]]
    zs = np.linspace(rt[1], rb[1], n_v)
    loop += [(float(rear(z)), float(z)) for z in zs[1:]]
    ys = np.linspace(rb[0], fb[0], n_h)
    loop += [(float(y), float(bot(y))) for y in ys[1:-1]]
    return loop, dict(front_bottom=fb, front_top=ft, rear_top=rt, rear_bottom=rb)


out = {"_note": "side-window apertures traced on corsa_a_4view_blueprint.gif (side elevation) and checked "
                "against anglia_side through its solved camera; model frame, no dz."}

# ---- door window --------------------------------------------------------------------------------
dw_top = smooth(merge("dlo_top_fwd", "dlo_top_b"))
dw_bot = smooth(flat_run(merge("dw_bot", "dw_bot_b")), 9)
door, dc = build(Edge(SP["dw_front_edge"], flip=True), Edge(SP["dw_rear_edge"], flip=True),
                 Edge(dw_top), Edge(dw_bot))
out["door"] = [[round(y, 4), round(z, 4)] for y, z in door]

# ---- quarter window -----------------------------------------------------------------------------
qtop = smooth(merge("qw_top", "qw_top_b"))
qbot = smooth(merge("qw_bot", "qw_bot_b"), 9)
d = np.gradient(qtop[:, 1], qtop[:, 0])
knee = int(np.argmax(d < -0.30))                       # where the top turns down the C-pillar
rear_pts, qtop = qtop[knee:], qtop[:knee + 1]
qbot = flat_run(qbot)

QF_T, QR_T, QF_B, QR_B = BA["QW_FT"], BA["QW_RT"], BA["QW_FB"], BA["QW_RB"]


def onto(a, p0, p1):
    """Ramp the traced line onto two measured corners (front to rear)."""
    d0 = (p0[2] + DZ) - float(np.interp(p0[1], a[:, 0], a[:, 1]))
    y1 = min(p1[1], a[-1, 0])
    d1 = (p1[2] + DZ) - float(np.interp(y1, a[:, 0], a[:, 1]))
    t = np.clip((a[:, 0] - p0[1]) / (y1 - p0[1]), 0, 1)
    b = a.copy(); b[:, 1] += d0 + t * (d1 - d0)
    return b, (round(d0 * 1000, 1), round(d1 * 1000, 1))


qtop, s_top = onto(qtop, QF_T, QR_T)
qbot, s_bot = onto(qbot, QF_B, QR_B)
rear_pts = rear_pts.copy(); rear_pts[:, 1] += s_top[1] / 1000.0
quarter, qc = build(Edge(SP["qw_front_edge"], flip=True), Edge(rear_pts, flip=True), Edge(qtop), Edge(qbot))
out["quarter"] = [[round(y, 4), round(z, 4)] for y, z in quarter]
out["_fit"] = {"quarter_top_shift_mm": list(s_top), "quarter_bottom_shift_mm": list(s_bot)}

json.dump(out, open(os.path.join(D, "windows.json"), "w"), indent=1)
for k, c in (("door", dc), ("quarter", qc)):
    a = np.array(out[k])
    print("%-8s %3d pts  y %+.3f..%+.3f  z %.3f..%.3f   corners " % (k, len(a), a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max())
          + "  ".join("%s (%+.3f, %.3f)" % (n, *v) for n, v in c.items()))
print("quarter put onto the measured corners, mm:", out["_fit"])
print("wrote", os.path.join(D, "windows.json"))
