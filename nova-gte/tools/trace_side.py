"""Trace the side-elevation lines off the line blueprint and write them in model coordinates.

Scale, and the 3622 that does not fit
-------------------------------------
The drawing carries its own dimension lines, and their extension lines sit at exactly px 31 (nose),
145 (front axle), 582 (rear axle) and 691 (tail). One scale fits three of the four:

    wheelbase  437 px -> 2343 mm  =  5.3616 mm/px
    front tyre  r 54.3 px         =   291 mm, the unloaded radius of a 175/65 R14 - so the drawing
                                      sits on unloaded tyres, like the model, and needs no dz
    height     254.6 px           =  1365 mm, exactly the printed figure
    length     660 px             =  3539 mm against the printed 3622   (-83)

So the printed 3622 is the odd one out, and it is the figure the project had been building to. It is not
the drawing being sloppy: tools/photomatch/body_profile.json, measured independently off the photos, puts
the body at y -1.779 .. +1.766 = 3545 mm, within 6 mm of what this drawing draws. Two independent
measurements of the car agree with each other and disagree with the homologated length by ~80 mm.

The scale here is therefore the plain 5.3616 mm/px pinned on the axles, with no stretching to reach 3622.
Independent checks against the photo measurements, which were never used to make this drawing:

    door shut lines  blueprint -0.648 / +0.500   photos -0.670 / +0.465   (22 / 35 mm)
    crease height    blueprint  0.70..0.76       photos  0.728
    rear of body     blueprint +1.786            photos +1.766            (20 mm)

This also corrects an earlier reading of the overlay: the blocky rear does NOT overhang the real tail -
the model was built out to +1.811 on the homologated length, and both measurements say the tail is
~40 mm short of that.

Lines come out by seeded run-following: at each pixel column the ink is reduced to run centres, and a
line is walked from its seed by taking the centre nearest the predicted continuation. That survives the
crossings (door handles, pillars, dimension lines) that a plain topmost/bottom-most scan trips over.

    python tools/trace_side.py [out.json] [diag.png]
"""
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "blender", "data", "side_profile.json")
DIAG = sys.argv[2] if len(sys.argv) > 2 else None

MPP = 5.36156 / 1000.0          # from the wheelbase: 2343 mm over 437 px
PX_NOSE, PX_FA, PX_RA, PX_TAIL = 31, 145, 582, 691
# ground from the fitted front tyre (centre px 146.4 py 210.3, r 54.3), not the drawn ground line,
# which sits about a line-width lower
PY_GROUND = 264.6
Y_FA, Y_RA = -1.1715, 1.1715    # the axles: the photo/BA frame, origin midway between them (DECISIONS 2026-10-26 (9))
PY_HUB, R_TYRE = 210.3, 54.3


def to_y(px):
    return Y_FA + (np.asarray(px, float) - PX_FA) * MPP


def to_z(py):
    return (PY_GROUND - np.asarray(py, float)) * MPP


A = np.array(Image.open(os.path.join(ROOT, "reference", "blueprints",
                                     "corsa_a_4view_blueprint.gif")).convert("L"))
INK = A < 150
BODY = INK[0:262, :]                     # above the ground line, so the dimension lines stay out

# ---- ink run centres, per column and per row ---------------------------------------------------
def run_centres(line):
    idx = np.nonzero(line)[0]
    if idx.size == 0:
        return np.empty(0)
    brk = np.nonzero(np.diff(idx) > 1)[0]
    return np.array([s.mean() for s in np.split(idx, brk + 1)])


COL = {j: run_centres(BODY[:, j]) for j in range(A.shape[1])}
ROW = {i: run_centres(BODY[i, :]) for i in range(BODY.shape[0])}


def follow(seed_px, seed_py, to, axis="col", tol=3.5, smooth=0.6, maxgap=14):
    """Walk a line from its seed, taking the run centre nearest the predicted continuation.

    axis "col" steps along px and tracks py (shallow lines: roof, belt, mouldings, sill);
    axis "row" steps along py and tracks px (steep lines: screen, pillars, tailgate).
    """
    table, a, b = (COL, seed_px, seed_py) if axis == "col" else (ROW, seed_py, seed_px)
    step = 1 if to >= a else -1
    pts, cur, slope, gap = [(a, float(b))], float(b), 0.0, 0
    for k in range(a + step, to + step, step):
        c = table.get(k)
        pred = cur + slope * step
        hit = None
        if c is not None and c.size:
            i = int(np.argmin(np.abs(c - pred)))
            # a line interrupted by a handle or a pillar is re-acquired from further away
            if abs(c[i] - pred) <= tol + (1.0 if gap else 0.0) * gap * 0.4:
                hit = float(c[i])
        if hit is None:
            gap += 1
            if gap > maxgap:
                break
            cur = pred                      # coast on the last slope and try again next column
            continue
        slope = (1 - smooth) * slope + smooth * (hit - cur) / (step * (gap + 1))
        cur, gap = hit, 0
        pts.append((k, cur))
    return pts if axis == "col" else [(int(round(v)), float(u)) for u, v in pts]


# Seeds read off the 4x zooms of the drawing. Each entry: (name, seed px, seed py, trace to px).
SEEDS = [
    # name              px   py   to   axis      what it is
    ("bonnet_top",     150,  96,  40, "col"),   # bonnet crown, forward to the nose
    ("bonnet_top_b",   150,  96, 232, "col"),   # ... and back to the screen base
    ("bonnet_shut",    150, 102,  60, "col"),   # the bonnet/wing shut line under it
    ("bonnet_shut_b",  150, 102, 230, "col"),
    ("screen",         245,  90,  20, "row"),   # windscreen, bottom to top
    ("roof",           400,  10, 300, "col"),   # roof panel, forward
    ("roof_b",         400,  10, 600, "col"),   # ... and back to where it turns into the backlight
    ("dlo_top",        350,  30, 250, "col"),   # door glass upper edge
    ("dlo_top_b",      350,  30, 474, "col"),   # ... to the B-pillar, where the line stops
    # The quarter window is its own aperture behind the B-pillar and the door-glass trace cannot cross it:
    # dlo_top_b used to coast past the pillar and then flatten, leaving the quarter window's top 25-33 mm
    # below the corners measured on the photographs (QW_FT 1.237, QW_RT 1.229 model z).
    ("dlo_top_fwd",    350,  30, 331, "col"),   # door glass top, forward only to its front corner
    ("qw_top",         550,  34, 476, "col"),   # quarter glass upper edge, forward to the B-pillar
    ("qw_top_b",       550,  34, 632, "col"),   # ... and back to the C-pillar
    ("dw_bot",         390, 101, 335, "col"),   # door glass lower edge
    ("dw_bot_b",       390, 101, 444, "col"),
    ("qw_bot",         550, 101, 476, "col"),   # quarter glass lower edge
    ("qw_bot_b",       550, 101, 632, "col"),
    ("backlight",      600,  40,  25, "row"),   # rear screen
    ("belt",           350, 113, 215, "col"),   # shoulder line under the glass
    ("belt_b",         350, 113, 640, "col"),
    ("glass_base",     350, 101, 240, "col"),   # the glass's own lower edge
    ("glass_base_b",   350, 101, 530, "col"),
    ("crease_front",   150, 128,  90, "col"),   # front wing feature line
    ("crease_front_b", 150, 128, 228, "col"),
    ("crease_rear",    520, 132, 455, "col"),   # rear quarter feature line
    ("crease_rear_b",  520, 132, 665, "col"),
    ("moulding_top",   350, 170, 212, "col"),   # side rubbing strip, upper edge
    ("moulding_top_b", 350, 170, 520, "col"),
    ("moulding_bot",   350, 184, 212, "col"),   # ... lower edge
    ("moulding_bot_b", 350, 184, 520, "col"),
    ("door_bottom",    350, 208, 215, "col"),   # the door's own lower edge, above the sill
    ("door_bottom_b",  350, 208, 515, "col"),
    ("sill",           350, 218, 212, "col"),   # sill / rocker
    ("sill_b",         350, 218, 515, "col"),
    ("arch_front",     150, 143, 100, "col"),   # front wheel-arch lip, crown forward
    ("arch_front_b",   150, 143, 203, "col"),   # ... and back
    ("arch_rear",      590, 161, 528, "col"),   # rear wheel-arch lip
    ("arch_rear_b",    590, 161, 645, "col"),
]

lines = {}
for name, px, py, to, axis in SEEDS:
    pts = follow(px, py, to, axis)
    lines[name] = pts
    print("%-16s seed px %3d py %3d  ->  %3d pts, px %3d..%3d,  z %.3f..%.3f"
          % (name, px, py, len(pts), min(p[0] for p in pts), max(p[0] for p in pts),
             to_z(max(p[1] for p in pts)), to_z(min(p[1] for p in pts))))

# ---- the shut lines, as curves: they lean and they curl at the bottom --------------------------
def vertical(px_lo, px_hi, py_lo, py_hi):
    """Strongest near-vertical ink column in a window, as a starting point for the row-follow."""
    best, bpx = -1, None
    for px in range(px_lo, px_hi + 1):
        n = int(BODY[py_lo:py_hi, px].sum())
        if n > best:
            best, bpx = n, px
    return bpx, best


for name, w, span in (("shut_door_front", (230, 242, 110, 210), (103, 232)),
                      ("shut_door_rear", (444, 458, 110, 200), (103, 215)),
                      ("tailgate_shut", (660, 680, 100, 170), (100, 196)),
                      ("qw_front_edge", (466, 474, 40, 95), (36, 100)),
                      # the door glass's own front and rear edges, both near-vertical and distinct from the
                      # A-pillar sweep that dlo_top follows and from the door shut lines
                      ("dw_front_edge", (318, 332, 45, 98), (40, 101)),
                      ("dw_rear_edge", (438, 450, 45, 98), (40, 101))):
    px, n = vertical(*w)
    mid = (span[0] + span[1]) // 2
    up = follow(px, mid, span[0], "row", tol=2.5)
    dn = follow(px, mid, span[1], "row", tol=2.5)
    pts = sorted(set(up + dn), key=lambda p: p[1])
    lines[name] = pts
    print("%-16s px %3d (%d ink)  ->  %3d pts, y %+.3f..%+.3f over z %.3f..%.3f"
          % (name, px, n, len(pts), to_y(min(p[0] for p in pts)), to_y(max(p[0] for p in pts)),
             to_z(max(p[1] for p in pts)), to_z(min(p[1] for p in pts))))

out = {
    "source": "reference/blueprints/corsa_a_4view_blueprint.gif, side elevation",
    "mm_per_px": MPP * 1000,
    "pinned_on": {"px": [PX_FA, PX_RA], "y": [Y_FA, Y_RA], "py_ground": PY_GROUND,
                  "tyre": {"py_hub": PY_HUB, "r_px": R_TYRE, "r_mm": round(R_TYRE * MPP * 1000, 1)}},
    "drawn_extent_y": [round(float(to_y(PX_NOSE)), 4), round(float(to_y(PX_TAIL)), 4)],
    "note": "plain wheelbase scale, no stretching: the drawing's 3539 mm body agrees with the "
            "photo-measured 3545 and both disagree with the homologated 3622",
    "lines": {k: [[round(float(to_y(p[0])), 4), round(float(to_z(p[1])), 4)] for p in v]
              for k, v in lines.items()},
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), indent=1)
print("\nwrote", OUT)

if DIAG:
    rgb = np.dstack([A] * 3)
    cols = [(220, 30, 30), (30, 140, 230), (20, 170, 70), (230, 140, 20), (170, 40, 200)]
    for i, (k, v) in enumerate(lines.items()):
        c = cols[i % len(cols)]
        for px, py in v:
            rgb[int(round(py)), int(round(px))] = c
    Image.fromarray(rgb[0:290, 20:710]).resize((690 * 2, 290 * 2), Image.NEAREST).save(DIAG)
    print("wrote", DIAG)
