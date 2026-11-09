"""Nova GTE body shell geometry - pure Python, shared by blender/scripts/build_body.py and the photo-overlay
preview (tools/photomatch/preview.py), so the model checked against the photos is the model that gets built.

Loft of cross-sections along Y (car faces -Y, Z up, +X = car's left, origin on the ground midway between the
axles), left half only (the build mirrors it). Every station has the same point count: NS points up the side
(floor centre -> sill -> widest -> shoulder crease -> belt -> glass base -> glass top -> roof edge) truncated at
the station's edge height, then NT points across the top surface (bumper / grille face / bonnet / windscreen /
roof / hatch / tail panel) to the centreline. The ends are then swept back in plan (front: slight V + rounded
corners, lamps receding at the outer ends; rear: rounded corners) by a warp that fades out before the arches.

All profile numbers live in tools/photomatch/body_profile.json, in the photo (BA) frame; DZ lifts them onto the
model's unloaded tyres.
"""
import json
import math
import os
from pathlib import Path

ROOT = Path(os.environ.get("NOVA_ROOT", r"D:\Claude\vauxhall_nova_gte_1989"))
PF = json.loads((ROOT / "tools" / "photomatch" / "body_profile.json").read_text())
DZ = PF["dz"]
Y_FRONT, Y_REAR = PF["y_front"], PF["y_rear"]
NT = 28
STEP = 0.012


def interp(pts, y):
    if y <= pts[0][0]:
        return pts[0][1]
    for (y0, v0), (y1, v1) in zip(pts, pts[1:]):
        if y0 <= y <= y1:
            return v0 + (v1 - v0) * (y - y0) / (y1 - y0) if y1 > y0 else v1
    return pts[-1][1]


def pchip(pts):
    """Monotone cubic (Fritsch-Butland slopes) through pts -> callable; no overshoot at steep steps."""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else 2 / (1 / d[i - 1] + 1 / d[i]) for i in range(1, n - 1)] + [d[-1]]

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        lo, hi = 0, n - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        i = lo
        h = xs[i + 1] - xs[i]; t = (x - xs[i]) / h
        h00, h10, h01, h11 = 2*t**3 - 3*t**2 + 1, t**3 - 2*t**2 + t, -2*t**3 + 3*t**2, t**3 - t**2
        return h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1]
    return f


def ease_out(t):
    """0 -> 1, steepest at 0 and flat at 1 (nose blend: the drop fades fastest right behind the edge)."""
    t = min(1.0, max(0.0, t))
    return 1.0 - (1.0 - t) * (1.0 - t)


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


_TOP_SPLINE = pchip([tuple(p) for p in PF["top"]])
_TBF = PF.get("top_bonnet_fit")


def TOP_F(y):
    """Centreline height of the top surface; the bonnet part is the analytic constant-curvature fit (smooth
    reflections), the rest the monotone spline through the photo points."""
    if _TBF and _TBF["y"][0] <= y <= _TBF["y"][1]:
        a, b, c = _TBF["c"]
        return a * y * y + b * y + c
    return _TOP_SPLINE(y)
FLOOR_F = pchip([tuple(p) for p in PF["floor"]])
TOP = [(y / 1000, TOP_F(y / 1000)) for y in range(int(Y_FRONT * 1000), int(Y_REAR * 1000) + 1, 2)]
HALFW = PF["halfw"]
BELT = PF["belt"]
CANT = PF["cant"]
GX_BASE, GX_TOP = PF["glass_base_x"], PF["glass_top_x"]
CREASE, Z_WIDE = PF["crease"], PF["z_widest"]
Y_A = -0.700                    # windscreen base at the centreline: bonnet/wing stations in front of it
Y_WS_TOP = -0.235               # windscreen top (header) at the centreline
SWF, SWR = PF["sweep_front"], PF["sweep_rear"]


CF = PF.get("crown_fade", {})


def end_fade(y):
    if CF.get("front", True) is False:
        return min(1.0, (Y_REAR - y) / 0.08)
    return min(1.0, min(y - Y_FRONT, Y_REAR - y) / 0.08)


FC = PF.get("front_corner")


def corner_xmax(y):
    """Plan limit of the wing / bonnet front corner at unswept station y (None = no limit)."""
    if not FC or y >= FC["y_rs"]:
        return None
    dy = FC["y_rs"] - y
    return FC["xs"] - FC["R"] + math.sqrt(max(0.0, FC["R"] ** 2 - dy * dy))


def smin(a, b, k):
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


FT = PF.get("front_taper")


def taper_xmax(y, z):
    """Plan limit of the front wing at station y, height z (None = no limit). The wing side runs back from the
    indicator's wrap-end line (raked, so z-dependent) at slope_back; in front of that line (the wing corner over
    the indicator) it closes in at slope_front. Fades out below the bumper top."""
    if not FT or y > FT["y_max"]:
        return None
    (xb, yb, zb), (xt, yt, zt) = FT["wb"], FT["wt"]
    t = min(1.0, max(0.0, (z - zb) / (zt - zb)))
    wx, wy = xb + (xt - xb) * t, yb + (yt - yb) * t
    sb, sf, e = FT["slope_back"], FT["slope_front"], FT["blend"]
    dy = y - wy
    xm = wx + 0.5 * (sb + sf) * dy + 0.5 * (sb - sf) * (math.sqrt(dy * dy + e * e) - e)
    z0, z1 = FT["z_fade"]
    return xm + (1.0 - smoothstep((z - z0) / (z1 - z0))) * 1.0


CROWN = PF["crown"]


def crown(y):
    """(drop from the centreline to the side/top corner, profile exponent) of the top surface at station y."""
    if y < Y_A and BCR:
        return bonnet_drop(y, xe_nominal(y)) + nose_roll(xe_nominal(y), y), 2.0
    if y < Y_A:
        c, p = CROWN["bonnet"]
        if "bonnet_nose" in CROWN:               # nose: the bonnet drops linearly to its front corners
            cn, pn, y0, y1 = CROWN["bonnet_nose"][:4]
            t = ease_out((y - y0) / (y1 - y0))
            c, p = cn + (c - cn) * t, pn + (p - pn) * t
        elif "bonnet_front" in CROWN:            # (old) the crown flattens towards the front edge (BA BON_F)
            c0, y0, L = CROWN["bonnet_front"]
            c = c0 + (c - c0) * smoothstep((y - y0) / L)
    elif y < Y_WS_TOP:
        c, p = CROWN["screen"]
    else:
        t = smoothstep((y - CROWN["hatch_blend"][0]) / (CROWN["hatch_blend"][1] - CROWN["hatch_blend"][0]))
        c = CROWN["roof"][0] * (1 - t) + CROWN["hatch"][0] * t
        p = CROWN["roof"][1] * (1 - t) + CROWN["hatch"][1] * t
        HF = CROWN.get("hatch_fin")
        if HF:                                   # flat fins beside the recessed tailgate glass
            cf, pf, a, b, c2, d2 = HF
            w = smoothstep((y - a) / (b - a)) * (1 - smoothstep((y - c2) / (d2 - c2)))
            c = c * (1 - w) + cf * w
            p = p * (1 - w) + pf * w
    return c * end_fade(y), p


def ridge_e(y):
    """Rounding of the nose crown's centre ridge (0 = profile u**p; >0 = soft-abs, keeps a linear crown from
    making a hard crease down the bonnet centre). Fades with the nose blend."""
    BN = CROWN.get("bonnet_nose")
    if y >= Y_A or not BN or len(BN) < 5 or BCR:
        return 0.0
    return BN[4] * (1.0 - ease_out((y - BN[2]) / (BN[3] - BN[2])))


def crown_shape(u, p, e):
    if e <= 0:
        return u ** p
    return ((math.sqrt(u * u + e * e) - e) / (math.sqrt(1 + e * e) - e)) ** p


def top_shape(y, u):
    """Normalised crown profile (0 at the centreline, 1 at the side/top corner) at station y. In the nose blend the
    two crown shapes themselves are blended (weighted by their drops), not their exponents - blending exponents
    made an S-shaped ripple across the bonnet."""
    BN = CROWN.get("bonnet_nose")
    if y < Y_A and BCR:
        return bonnet_shape(y, u, xe_nominal(y))
    if y < Y_A and BN:
        cn, pn, y0, y1 = BN[:4]
        e = BN[4] if len(BN) > 4 else 0.0
        cb, pb = CROWN["bonnet"]
        t = ease_out((y - y0) / (y1 - y0))
        dn, db = cn * crown_shape(u, pn, e), cb * u ** pb
        c = cn + (cb - cn) * t
        return ((1 - t) * dn + t * db) / c if c > 0 else 0.0
    return u ** crown(y)[1]


BCR = PF.get("bonnet_creases")


def crease_x(y):
    return BCR["x0"] + BCR["dxdy"] * (y - BCR["y0"])


def bonnet_drop(y, xe):
    """Total drop from the centreline to the side/top corner xe at station y: small crown c_in on the centre
    panel up to the crease, then a straight (flatter-looking, steeper) outer panel reaching drop_s at the shut line."""
    xc = crease_x(y)
    ds = interp(BCR["drop_s"], y)
    so = (ds - BCR["c_in"]) / max(BCR["x_shut"] - xc, 0.05)
    return BCR["c_in"] + so * max(xe - xc, 0.0)


def bonnet_drop_at(y, x):
    """Drop below the centreline at lateral x (centre panel crown up to the crease, straight outer panel)."""
    xc = crease_x(y)
    if x <= xc:
        return BCR["c_in"] * (x / xc) ** 2
    ds = interp(BCR["drop_s"], y)
    so = (ds - BCR["c_in"]) / max(BCR["x_shut"] - xc, 0.05)
    return BCR["c_in"] + so * (x - xc)


def edge_y(x):
    """Plan position of the bonnet front edge (straight V) at lateral x."""
    BV = PF["front_panel"]["bonnet_v"]
    return BV["y0"] + BV["a"] * abs(x)


def nose_roll(x, y):
    """Roll-down of the bonnet nose: the surface curves down over the last L metres to the level front edge E
    (both photos: the V edge sits at z ~0.722 right across), independent of x - no centre ridge."""
    NR = BCR.get("nose_roll") if BCR else None
    if not NR:
        return 0.0
    ye = edge_y(x)
    R = TOP_F(ye) - bonnet_drop_at(ye, x) - NR["E"]
    if R <= 0:
        return 0.0
    s = max(0.0, (y - ye) / NR["L"])
    return R * (1.0 - s) ** NR.get("power", 2) if s < 1.0 else 0.0


def bonnet_shape(y, u, xe):
    """Normalised bonnet profile with the lengthways crease (slope break) at crease_x(y)."""
    D = bonnet_drop(y, xe)
    if D <= 0:
        return u * u
    uc = min(0.95, crease_x(y) / xe)
    fi = BCR["c_in"] / D
    if u <= uc:
        return fi * (u / uc) ** 2
    return fi + (1.0 - fi) * (u - uc) / (1.0 - uc)


def xe_nominal(y):
    return interp(HALFW, y) - 0.09


def z_edge(y):
    """Height where the side curve hands over to the top surface."""
    return max(TOP_F(y) - crown(y)[0], FLOOR_F(y) + 0.05)


def _nose_h(y):
    if not NV:
        return 0.0
    y0, y1, y2, y3 = NV["y"]
    if y <= y0 or y >= y3:
        return 0.0
    return smoothstep((y - y0) / (y1 - y0)) if y < y1 else (1.0 if y <= y2 else 1 - smoothstep((y - y2) / (y3 - y2)))


def belt(y):
    if y < Y_A:                                  # wing top edge, just under the bonnet surface
        return z_edge(y) - 0.008
    return interp(BELT, y)


FL = PF.get("wing_flare")


def trap(y, ys):
    """0 -> 1 -> 1 -> 0 over the four y breakpoints (smooth ramps)."""
    a, b, c, d = ys
    if y <= a or y >= d:
        return 0.0
    if y < b:
        return smoothstep((y - a) / (b - a))
    if y > c:
        return 1.0 - smoothstep((y - c) / (d - c))
    return 1.0


def crease_z(y):
    """Height of the shoulder crease / wing step line at station y (photo frame)."""
    return interp(FL["z_step"], y) if FL else CREASE


def flare(y):
    """(outward step size, step height) of the wing flare at station y; size 0 between the flares."""
    if not FL:
        return 0.0, 0.70
    zs = interp(FL["z_step"], y)
    return FL["d"] * max(trap(y, FL["front_y"]), trap(y, FL["rear_y"])), zs


def side_curve(y):
    """Key points (x, z) from the floor centre up the side to above the roof edge."""
    w, f, b = interp(HALFW, y), FLOOR_F(y), belt(y)
    ct = interp(CANT, y)
    if y < Y_A:
        xg, xc = w - 0.100, w - 0.110
    else:
        xg, xc = interp(GX_BASE, y), interp(GX_TOP, y)
    # sill rounding keys at fixed heights (clamped onto the floor where it rises at the bumpers), so each key row
    # stays at one height along the car and the bumper corners are not twisted
    pts = [(0.0, f), (0.55 * w, f), (w - 0.045, f), (w - 0.012, max(f + 0.0005, 0.240)), (w - 0.003, max(f + 0.001, 0.290)),
           (w, max(f + 0.0015, Z_WIDE))]
    # lower side up to the shoulder crease, with the wing flare: the panel under the step stands out by d, the
    # ledge (FL ledge high) closes it back to the body line at the step height zs; blends out below z_low
    d, zs = flare(y)
    zc = crease_z(y)                             # the shoulder crease = the step line (measured, continuous)
    lin = lambda z: w - 0.036 * (z - Z_WIDE) / (zc - Z_WIDE)
    zl = FL["z_low"][1] if FL else 0.60
    ledge = FL["ledge"] if FL else 0.012
    # lower side -> flare (proud by d on the wings) -> ledge -> crease (sharp row) -> upper side turning in
    pts += [(lin(zl) + d, zl), (lin(zc - ledge) + d, zc - ledge), (lin(zc) + d * 0.15, zc)]
    # above the glass top: black frame + body-colour band nearly in the glass plane (2.6 cm), drip gutter, roof roll
    pts += [(w - 0.046, zc + 0.016), (w - 0.064, b - 0.040), (w - 0.093, b - 0.006), (xg, b + 0.008), (xc, ct), (xc - 0.004, ct + 0.026),
           (xc - 0.022, ct + 0.046), (xc - 0.10, ct + 0.075)]
    out = [pts[0]]
    for x, z in pts[1:]:                         # same key count at every station; keep z non-decreasing
        out.append((x, max(z, out[-1][1] + 1e-4)))
    return out


# fixed subdivisions per key segment (corners on fixed rows): floor, sill, widest -> flare low -> ledge -> step ->
# crease -> belt -> glass base -> side glass -> roof edge
SUB = [2, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 5, 2, 1, 1]          # 13: frame row + body band row above the glass
GLASS_SEG = 12
NS = sum(SUB) + 1
KEY_BELT, KEY_CANT = sum(SUB[:GLASS_SEG]), sum(SUB[:GLASS_SEG + 1])  # ring rows of the glass base and the glass top


GLASS_BULGE = 0.010             # side glass / C-pillar curvature (outward at mid-height), ESTIMATE


def sample(poly, bulge=True):
    out = []
    for si, ((a, b), n) in enumerate(zip(zip(poly, poly[1:]), SUB)):
        for k in range(n):
            t = k / n
            x = a[0] + (b[0] - a[0]) * t
            if si == GLASS_SEG and bulge:
                x += GLASS_BULGE * math.sin(math.pi * t)
            out.append((x, a[1] + (b[1] - a[1]) * t))
    out.append(poly[-1])
    return out


def add_glass_bulge(side, keys):
    """Side-glass / C-pillar outward curvature, applied AFTER the truncation: sin(pi t) over whatever is left of the
    glass segment, amplitude scaled by the fraction left - so the bulge shrinks smoothly where the tailgate slope cuts
    down through the side instead of stopping in a crease (2026-10-13: X-shaped folds on the C-pillars)."""
    s0, s1 = KEYS[GLASS_SEG], KEYS[GLASS_SEG + 1]
    za, zb = keys[GLASS_SEG][1], keys[GLASS_SEG + 1][1]
    p0, p1 = side[s0], side[s1]
    frac = max(0.0, min(1.0, (p1[1] - p0[1]) / (zb - za))) if zb > za else 0.0
    out = list(side)
    for i in range(s0 + 1, s1):
        t = (i - s0) / (s1 - s0)
        out[i] = (side[i][0] + GLASS_BULGE * frac * math.sin(math.pi * t), side[i][1])
    return out


KEYS = [sum(SUB[:k]) for k in range(len(SUB) + 1)]   # sampled-row index of each key point


def clamp_top(side, ze):
    """Truncate the side at the edge height ze (the ring keeps its point count). The key segment that ze cuts keeps
    its rows, re-spaced evenly from its start to the crossing point, so they move smoothly from station to station
    as ze changes (collapsing them at the crossing made the rows jump between stations: twisted, faceted C-pillars);
    rows of later segments collapse at the crossing (merged away by the mesh build)."""
    j = next((i for i, p in enumerate(side) if p[1] > ze), None)
    if j is None:
        return side
    a, b = side[j - 1], side[j]
    t = (ze - a[1]) / (b[1] - a[1])
    e = (a[0] + (b[0] - a[0]) * t, ze)
    s0 = max(k for k in KEYS if k <= j - 1)                  # start row of the segment that ze cuts
    s1 = min(k for k in KEYS if k >= j)                      # its end row
    p0 = side[s0]
    seg = [(p0[0] + (e[0] - p0[0]) * (i - s0) / (s1 - s0), p0[1] + (e[1] - p0[1]) * (i - s0) / (s1 - s0))
           for i in range(s0, s1 + 1)]
    return side[:s0] + seg + [e] * (len(side) - s1 - 1)


BC = PF.get("bonnet_crease")


def bonnet_step(x, y):
    """Bonnet centre panel raised between two longitudinal creases (drop outboard of the crease line)."""
    if not BC or not (Y_FRONT < y < Y_A - 0.05):
        return 0.0
    (y0, x0), (y1, x1) = BC["x"]
    xcr = x0 + (x1 - x0) * min(1.0, max(0.0, (y - y0) / (y1 - y0)))
    fade = min(1.0, (Y_A - 0.05 - y) / 0.05) * end_fade(y)
    return BC["drop"] * smoothstep((x - xcr) / BC["width"] + 0.5) * fade


NV = PF.get("nose_v")


def nose_v(x, y):
    """Front 'beak': near the bonnet front edge the centre of the surface drops to a point (V seen from the front)."""
    if not NV:
        return 0.0
    y0, y1, y2, y3 = NV["y"]
    if y <= y0 or y >= y3:
        return 0.0
    h = smoothstep((y - y0) / (y1 - y0)) if y < y1 else (1.0 if y <= y2 else 1 - smoothstep((y - y2) / (y3 - y2)))
    return -NV["dz"] * (1.0 - min(1.0, abs(x) / NV["x"])) ** 1.3 * h


def section(y):
    zt = TOP_F(y)
    ze = z_edge(y)
    keys = side_curve(y)
    side = add_glass_bulge(clamp_top(sample(keys, bulge=False), ze), keys)
    zf = FLOOR_F(y)
    squash = zt < zf + 0.05                      # end stations: the profile closes (top meets floor)
    xe, zl = side[-1]
    p = crown(y)[1]
    e = ridge_e(y)
    top = []
    for k in range(1, NT + 1):
        u = 1 - k / NT
        x = xe * u
        if BCR and y < Y_A and not squash:
            top.append((x, zt - bonnet_drop_at(y, x) - nose_roll(x, y)))   # lengthways creases + nose roll
        else:
            top.append((x, zt - (zt - zl) * top_shape(y, u) - bonnet_step(x, y) + nose_v(x, y) if not squash else ze))
    pts = side + top
    if FT and y <= FT["y_max"]:
        # shift the wing's cross-section inward (keeps the shoulder / tumblehome shape) by how far its side at lamp
        # height sticks out past the taper line; the bonnet (x < shift_x[0]) stays, the bumper-level rows fade out
        zr = FT.get("z_ref", 0.63)
        xs = max((x for (x, z0), (x1, z1) in zip(side, side[1:]) if min(z0, z1) <= zr <= max(z0, z1)), default=None)
        if xs is not None:
            sx0, sx1 = FT.get("shift_x", (0.58, 0.70))
            D = xs - taper_xmax(y, zr)
            D = 0.5 * (D + math.sqrt(D * D + 1e-5))      # smooth max(0, D)
            zf0, zf1 = FT["z_fade"]
            pts = [(x - D * smoothstep((x - sx0) / (sx1 - sx0)) * smoothstep((z - zf0) / (zf1 - zf0)), z) for x, z in pts]
            # over the indicator height, pull the side exactly onto the wrap line at the lamp and blend back into the
            # shifted profile within near_len behind it (flush wing / indicator, no flat slab further back)
            (xb, yb, zb), (xt, yt, zt) = FT["wb"], FT["wt"]
            band, near = FT.get("band", 0.02), FT.get("near_len", 0.05)
            out = []
            for x, z in pts:
                wz = smoothstep((z - (zb - band)) / band) * (1 - smoothstep((z - zt) / band))
                if wz > 0 and x > sx0:
                    t = min(1.0, max(0.0, (z - zb) / (zt - zb)))
                    wy = yb + (yt - yb) * t
                    wn = 1.0 - smoothstep((y - wy) / near)
                    x = x + (taper_xmax(y, z) - x) * wn * wz * smoothstep((x - sx0) / (sx1 - sx0))
                out.append((x, z))
            pts = out
    elif FC and not FT:
        xm = corner_xmax(y)
        if xm is not None:
            pts = [(smin(x, xm, FC["soft"]) if x > xm - FC["soft"] else x, z) for x, z in pts]
    if squash:                                   # fit the section between floor and top: a flat line at the very end
        z0, z1 = min(p[1] for p in pts), max(p[1] for p in pts)
        k = (zt - zf) / (z1 - z0) if z1 > z0 else 0.0
        pts = [(x, zf + (z - z0) * k) for x, z in pts]
    return pts


def sweep(x, y, z):
    """Plan warp of the ends: returns the y offset for a left-half point (x >= 0)."""
    x = abs(x)
    s = 0.0
    if y < SWF["fade"][1]:
        t = smoothstep((z - SWF["z_lo"]) / (SWF["z_hi"] - SWF["z_lo"]))
        k = SWF["k_low"] * (1 - t) + SWF["k_high"] * t
        c = SWF["c_low"] * (1 - t) + SWF["c_high"] * t
        sf = SWF["a"] * x + k * x ** 4 + c * max(0.0, x - SWF["xc"]) ** SWF.get("cp", 2)
        wf = 1 - smoothstep((y - SWF["fade"][0]) / (SWF["fade"][1] - SWF["fade"][0]))
        s += sf * wf
    if y > SWR["fade"][0]:
        tb = smoothstep((z - SWR["z_b"][0]) / (SWR["z_b"][1] - SWR["z_b"][0]))   # bumper (below) -> panel
        sr = (SWR["k_bumper"] * (1 - tb) + SWR["k"] * tb) * x ** SWR["p"] + SWR.get("cr", 0.0) * max(0.0, x - SWR.get("xr", 1.0)) ** 3
        wr = smoothstep((y - SWR["fade"][0]) / (SWR["fade"][1] - SWR["fade"][0]))
        s -= sr * wr
    return s


def stations():
    """Adaptive: finer where the top line is steep (nose/tail faces, windscreen, hatch) and near the ends."""
    ys, y = [], Y_FRONT
    while y < Y_REAR:
        ys.append(y)
        slope = abs(TOP_F(y + 0.003) - TOP_F(y - 0.003)) / 0.006
        d = min(y - Y_FRONT, Y_REAR - y)
        step = min(STEP, 0.010 / max(slope, 1e-6))
        if d < 0.03:
            step = min(step, 0.004)
        y += max(step, 0.0008)
    ys.append(Y_REAR)
    ys += EXTRA_Y
    ys = sorted(set(round(v, 5) for v in ys if Y_FRONT <= v <= Y_REAR))
    out = [ys[0]]
    for v in ys[1:]:
        if v - out[-1] > 0.0006:
            out.append(v)
    return out


EXTRA_Y = []                    # build_body adds exact stations at shut lines / glass edges


def rings(photo_frame=False):
    """List of rings (left half), each a list of (x, y, z); y already swept, z in model frame unless photo_frame."""
    dz = 0.0 if photo_frame else DZ
    out = []
    for y in stations():
        out.append([(x, y + sweep(x, y, z), z + dz) for x, z in section(y)])
    return out


AS = PF.get("arch_shapes")


def arch_poly(key, photo_frame=False):
    """Wheel-arch lip outline (y, z), front to rear over the top, open at the bottom (body_profile arch_shapes)."""
    dz = 0.0 if photo_frame else DZ
    return [(y, z + dz) for y, z in AS[key]]


def arch_centre(key, photo_frame=False):
    y, z = AS["wheel"][key]
    return y, z + (0.0 if photo_frame else DZ)


def arch_edge_y(key, z, side, photo_frame=False):
    """y of the arch lip at height z on the 'front' (min y) or 'rear' (max y) side; None above the arch top."""
    P = arch_poly(key, photo_frame)
    ys = []
    for (y0, z0), (y1, z1) in zip(P, P[1:]):
        if min(z0, z1) <= z <= max(z0, z1) and z1 != z0:
            ys.append(y0 + (y1 - y0) * (z - z0) / (z1 - z0))
    if not ys:
        return None
    return min(ys) if side == "front" else max(ys)


def in_arch(key, y, z, grow=0.0, photo_frame=False):
    """Inside the arch opening (the polygon closed along its bottom), or within grow of its lip."""
    P = arch_poly(key, photo_frame)
    inside = False
    Q = P + [P[0]]
    for (y0, z0), (y1, z1) in zip(Q, Q[1:]):
        if (z0 > z) != (z1 > z) and y < y0 + (y1 - y0) * (z - z0) / (z1 - z0):
            inside = not inside
    if inside or grow <= 0:
        return inside
    for (y0, z0), (y1, z1) in zip(P, P[1:]):
        dy, dzz = y1 - y0, z1 - z0
        L = dy * dy + dzz * dzz
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((y - y0) * dy + (z - z0) * dzz) / L))
        if (y - y0 - t * dy) ** 2 + (z - z0 - t * dzz) ** 2 < grow * grow:
            return True
    return False


def arches(photo_frame=False):
    """Legacy circle view (y, z, r) of each arch: centre at the wheel, radius to the lip top."""
    out = {}
    for key in ("front", "rear"):
        cy, cz = arch_centre(key, photo_frame)
        top = max(z for _, z in arch_poly(key, photo_frame))
        out[key] = (cy, cz, top - cz)
    return out


# ---------------- trim / glass zones (evaluated on the unswept loft, photo frame) ----------------
ZN = PF["zones"]
GAP = 0.005
QUARTER_FRAME = 0.010           # extra black frame under the quarter glass (frame ~2 cm vs ~1 cm seal on the door)
SHUT_Y = ZN["shut_y"]                       # door rear / front shut lines
B_PILLAR = ZN["b_pillar"]                   # black B-pillar (y range)
APO = ZN["a_pillar_outer"]                  # A-pillar outer line (y, z) base -> top, side view
QR = ZN["quarter_rear_edge"]                # quarter glass rear edge (y, z) bottom -> top
SKIRT = ZN["skirt_top"]
WS_SEAL = 0.018                             # windscreen rubber surround at the header (photos c20 / cCF / redgte_21)
GP = PF.get("glass_panels")                 # tailgate glass / sunroof as inset panels (glass_panels.py)
SCU = PF.get("scuttle_curve")               # windscreen base / scuttle / bonnet rear edge on one plan curve


def screen_base_y(x):
    """Windscreen base line in plan (glass starts seal + riser behind it); scuttle panel in front of it."""
    return min(SCU["yb0"] + SCU["k"] * x * x, SCU["yb_max"])


def bonnet_rear_y(x):
    return min(SCU["yr0"] + SCU["kr"] * x * x, screen_base_y(x) - 0.05)
MATS = ["paint_gunmetal", "glass_tint", "trim_black", "trim_grey", "lamp_clear", "lamp_red", "lamp_amber", "panel_gap"]
M = {n: i for i, n in enumerate(MATS)}


def hatch_x(z):
    """Half-width of the hatch glass at height z (BA HG_B / HG_T corners), photo frame."""
    HG = ZN["hatch_glass"]
    return HG["x_bot"] + (HG["x_top"] - HG["x_bot"]) * (z - HG["z_bot"]) / (HG["z_top"] - HG["z_bot"])


def line_y(pts, z):
    (y0, z0), (y1, z1) = pts
    return y0 + (y1 - y0) * (z - z0) / (z1 - z0)


def zone(cx, cy, cz, row, top_k):
    """Material index for a face of the left half (unswept coords, photo frame); top_k = index across the top
    surface from the side/top corner, -1 on the side rows."""
    top_row = top_k >= 0
    if not top_row:
        for yl in SHUT_Y:
            if abs(cy - yl) < GAP / 2 + 1e-4 and interp(SKIRT, cy) < cz < belt(cy):
                return M["panel_gap"]
        if KEY_BELT <= row < KEY_CANT and cz > belt(cy) - 0.005:
            if B_PILLAR[0] <= cy <= B_PILLAR[1]:
                return M["trim_black"]
            if B_PILLAR[1] < cy < QR[0][0] + 0.05 and cz < belt(cy) + QUARTER_FRAME:
                return M["trim_black"]                     # quarter glass sits in a deeper black frame (cS photo)
            ya = line_y(APO, cz)
            if ya + 0.045 <= cy <= B_PILLAR[0] - 0.012:
                return M["glass_tint"]
            if B_PILLAR[1] + 0.012 <= cy <= line_y(QR, cz) - 0.012:
                return M["glass_tint"]
            if ya <= cy <= B_PILLAR[0] or B_PILLAR[1] <= cy <= line_y(QR, cz):
                return M["trim_black"]
        if row == KEY_BELT - 1 and Y_A < cy < QR[0][0] and cz > 0.8:
            return M["trim_black"]                         # waist seal along the glass base
        if row == KEY_CANT and line_y(APO, cz) - 0.01 <= cy <= line_y(QR, cz) + 0.01:
            return M["trim_black"]                         # black window frame along the glass top (cS photo)
    else:
        if SCU and cy < ZN["ws_y"][1]:
            yb = ZN["ws_y"][0]                             # straight here; build_body bends these rows onto the curve
            if yb < cy and (top_k == 0 or cy > ZN["ws_y"][1] - WS_SEAL):
                return M["trim_black"]                     # rubber surround up the A-pillars and along the header
            if yb + SCU["seal"] < cy and top_k >= 1:
                return M["glass_tint"]
            if yb - 1e-4 < cy <= yb + SCU["seal"] and top_k >= 1:
                return M["trim_black"]                     # rubber seal along the screen base
            # in front of the base: body-colour scuttle panel (louvres are a separate part, build_details)
        elif ZN["ws_y"][0] < cy < ZN["ws_y"][1] and top_k >= 1:
            return M["glass_tint"]
        elif ZN["scuttle_y"][0] < cy < ZN["scuttle_y"][1] and cx < 0.60:
            return M["trim_black"]
        sr = ZN.get("sunroof")
        if sr and not GP and sr["y"][0] < cy < sr["y"][1] and cx < sr["x"]:
            return M["glass_tint"]
        HG = ZN.get("hatch_glass")
        if GP and cy > 1.3:
            pass                                           # tailgate glass is an inset panel: paint here
        elif HG and cy > 1.3:
            if HG["z_bot"] < cz < HG["z_top"] and cx < hatch_x(cz):
                return M["glass_tint"]
            if HG["z_bot"] - HG["seal"] < cz < HG["z_top"] + HG["seal"] and cx < hatch_x(cz) + HG["seal"]:
                return M["trim_black"]                     # rubber seal round the hatch glass
        elif ZN["hatch_glass_z"][0] < cz < ZN["hatch_glass_z"][1] and cy > 1.3 and top_k >= 2:
            return M["glass_tint"]
        if cy > ZN["rear_face_y"]:
            tl = ZN["tail_lamp"]
            if tl["z"][0] < cz < tl["z"][1]:
                if tl["x_in"] < cx < tl.get("x_out", 9):
                    frac = (cz - tl["z"][0]) / (tl["z"][1] - tl["z"][0])
                    return M["lamp_red"] if frac > 0.45 else (M["lamp_amber"] if frac > 0.18 else M["lamp_clear"])
                if ZN["rear_panel_z0"] < cz < ZN.get("rear_panel_z1", 9.0) and cx < tl["x_in"] + 0.005:
                    return M["trim_black"]                 # black panel only between the lamps (photos)
        if cy < ZN["front_face_y"]:
            hl, ind, gr = ZN["headlamp"], ZN["indicator"], ZN["grille"]
            if hl["z"][0] < cz < hl["z"][1] and hl["x"][0] < cx < hl["x"][1]:
                return M["lamp_clear"]
            if ind["z"][0] < cz < ind["z"][1] and ind["x"][0] < cx < ind["x"][1]:
                return M["lamp_amber"]
            if gr["z"][0] < cz < gr["z"][1] and cx < gr["x"]:
                return M["trim_black"]
    if cy < ZN["front_spoiler"][0] and cz < ZN["front_spoiler"][1]:
        return M["trim_grey"]
    if cy > ZN["rear_valance"][0] and cz < ZN["rear_valance"][1]:
        return M["trim_grey"]
    if ZN["front_spoiler"][0] <= cy <= ZN["rear_valance"][0] and cz < interp(SKIRT, cy) and cx > 0.55:
        return M["trim_grey"]
    return M["paint_gunmetal"]


def loft(photo_frame=False):
    """Unswept rings + quad/cap faces with ring rows; returns (rings, faces, rows). Faces index into the flat
    vertex list ring-major; the two cap centres are appended after the rings."""
    rs = [[(x, y, z) for x, z in section(y)] for y in stations()]
    n = len(rs[0])
    faces, rows = [], []
    for j in range(len(rs) - 1):
        for i in range(n - 1):
            a, b = j * n + i, (j + 1) * n + i
            faces.append((a, a + 1, b + 1, b)); rows.append(i)
    caps = []
    for j, flip in ((0, True), (len(rs) - 1, False)):
        cidx = len(rs) * n + len(caps)
        caps.append((0.0, rs[j][0][1], sum(p[2] for p in rs[j]) / n))
        for i in range(n - 1):
            f = (j * n + i, j * n + i + 1, cidx)
            faces.append(f[::-1] if flip else f); rows.append(-1)
    return rs, caps, faces, rows


def finalize(p, photo_frame=False):
    """Unswept photo-frame point -> swept point (model frame unless photo_frame)."""
    x, y, z = p
    return (x, y + sweep(x, y, z), z + (0.0 if photo_frame else DZ))


# ---------------- surface queries for bolt-on parts (unswept, photo frame) ----------------
def skin_x(y, z):
    """Outer x of the left side surface at station y, height z (side rows only)."""
    pts = section(y)[:NS]
    best = None
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        if min(z0, z1) <= z <= max(z0, z1) and z1 != z0:
            x = x0 + (x1 - x0) * (z - z0) / (z1 - z0)
            best = x if best is None else max(best, x)
    return best


def top_z(y, x):
    """Height of the top surface (bonnet / roof / hatch) at station y, lateral x."""
    pts = section(y)[NS - 1:]
    if x >= pts[0][0]:
        return pts[0][1]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        if x1 <= x <= x0 and x0 != x1:
            return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def to_model(x, y, z):
    """Unswept photo-frame point -> model frame (sweep + DZ), keeping the sign of x."""
    xs, ys, zs = finalize((abs(x), y, z))
    return (x, ys, zs)
