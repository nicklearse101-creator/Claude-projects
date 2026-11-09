"""Nova GTE front end parts (plain Python) -> blender/data/front_end.json.

BA/photo frame (car faces -Y, Z up, +X = car's left; ground = loaded tyre contact). Sources:
  FIA A-5375: front overhang 670 mm -> bumper apex y = -1.1715 - 0.670 = -1.8415 (SOURCED)
  ba_result.json multi-view points: headlamp HL_*, indicator IND_*, grille GRO_*, bonnet corner BON_F
  cCF + c20 (agree): bonnet front edge at the centreline (0, -1.777, 0.740); grille badge (0, -1.784, 0.62)
  c22 + c20: front plate centre ~(0, -1.805, 0.44)
  cS side rays: bumper side heights (top 0.54, ribs 0.426-0.476, red bottom 0.303, lip bottom 0.222), side end
  y -1.48; photos 18/19/22: shelf, 4 ribs, rounded corner, grey chin lip, plate recess (ESTIMATE shapes)
"""
import math
import os
import sys

import numpy as np

import meshkit as mk

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender", "scripts"))
import body_geom as g  # noqa: E402

# ---------------- front bumper ----------------
APEX_Y = -1.815           # face at the centreline (plate at -1.805 in a 10 mm recess; c22 + cCF). FIA overhang
                          # 670 mm would put it at -1.8415: 27 mm further; photos win (DECISIONS.md)
FACE_MAX = 0.003          # the face bulges this far ahead of the path line at rib height
BUMPER_A = 0.05           # plan V slope at the centre (c20: the bumper lines kink at the centreline)
# plan path of the face (d = 0) from the centre round the corner to the side return; keeps a ~55 mm shelf in
# front of the lamp panel (HL_IB / HL_OB / IND_OB) and runs into the side return at x 0.748 (just outside the wing)
BUMPER_CTRL = [(0.0, APEX_Y + FACE_MAX), (0.30, -1.7985), (0.45, -1.7885), (0.55, -1.7705), (0.62, -1.7485),
               (0.68, -1.7165), (0.715, -1.6785), (0.735, -1.6285), (0.740, -1.5785), (0.740, -1.480)]
# c20 + cCF two-view at x = 0.45: shelf front edge (-1.783, 0.518), ribs (-1.79, 0.497 .. 0.465)
# Ribs (red inserts) run LEVEL from end to end (Nik 2026-10-12: straight, not dipping round the corners). The photos
# disagree by ~2 cm: centre 0.497-0.4655 (c20 + cCF at x 0.45), side return ~0.476-0.4445 (cS + cCF); level band at
# the mean of the two (ESTIMATE, each view within ~1 cm).
RIBS = [0.4865, 0.4760, 0.4655, 0.4550]
RIB_HW, RIB_D = 0.0032, 0.0028
PLATE = {"w": 0.520, "h": 0.111, "z": 0.440, "recess": 0.010, "margin": 0.008}
# lower edges rise towards the centre (c20 at the centre: red bottom ~0.33, lip bottom ~0.28; cS at the side
# return: 0.303 / 0.222)
Z_RB = (0.325, 0.318)     # red bottom edge, centre / corner: c20 + cCF two-view at the centre 0.325 (2026-10-12);
                          # cCF along the bumper 0.31-0.33 - nearly level (was 0.335 / 0.325: bowed up in the middle)
Z_LB = (0.255, 0.248)     # grey lip bottom, centre / corner: two-view 0.255 at the centre, cCF 0.24-0.26 along it


def side_t(x):
    """0 at the centre region, 1 at the corners/side (smooth)."""
    t = min(1.0, max(0.0, (abs(x) - 0.25) / 0.40))
    return t * t * (3 - 2 * t)


# Side return (anglia_side cS + cCF mirrored two-view, ray gaps <= 1.7 cm, 2026-10-12): ribs z 0.441-0.483, top 0.542,
# red bottom 0.311, lip bottom 0.227 - the rib band and lower edges step down round the corners from the front-face
# values (c20 + cCF at x 0.45). corner_t blends them in between x 0.50 and 0.72 (the plan corner).
RIB_DROP, RB_DROP, LB_DROP = 0.0, -0.007, -0.021   # ribs level (see RIBS)


def corner_t(x):
    t = min(1.0, max(0.0, (abs(x) - 0.50) / 0.22))
    return t * t * (3 - 2 * t)


def bumper_profile(x):
    """(d, z) from the shelf back edge over the top, down the face (ribs as grooves, exact rows at the plate
    recess edges), down the tucked-in lower face to the underside return. Same row count for every x."""
    t = side_t(x); tc = corner_t(x)
    zrb = Z_RB[0] + (Z_RB[1] - Z_RB[0]) * t + RB_DROP * tc
    ribs = [zc + RIB_DROP * tc for zc in RIBS]
    pr = [(-0.050, 0.538), (-0.034, 0.535), (-0.018, 0.532), (-0.008, 0.529), (-0.003, 0.5255), (-0.0005, 0.521),
          (0.001, 0.517)]
    z1 = PLATE["z"] + PLATE["h"] / 2 + PLATE["margin"]; z0 = PLATE["z"] - PLATE["h"] / 2 - PLATE["margin"]
    upper = sorted({0.512, z1 + 0.003, z1, z0, z0 - 0.003, 0.398, 0.390} |
                   {zc + k for zc in ribs for k in (RIB_HW + 0.0008, RIB_HW * 0.45, 0.0, -RIB_HW * 0.45,
                                                    -RIB_HW - 0.0008)}, reverse=True)
    face = {0.517: 0.001, 0.512: 0.002, 0.505: FACE_MAX, 0.420: FACE_MAX, 0.405: 0.002, 0.390: -0.001}
    fz = sorted(face); fd = [face[k] for k in fz]
    for z in upper:
        d = float(np.interp(z, fz, fd))
        for zc in ribs:
            u = abs(z - zc) / RIB_HW
            if u < 1.0:
                d -= RIB_D * (1 - u * u)
        pr.append((d, z))
    # tucked-in lower face, 8 rows from 0.385 down to the red bottom edge
    for k in range(1, 9):
        f = k / 8
        z = 0.385 + (zrb - 0.385) * f
        pr.append((-0.001 - 0.026 * f ** 1.6, z))
    pr += [(-0.034, zrb - 0.004), (-0.060, zrb - 0.006)]
    return pr


def lip_profile(x):
    t = side_t(x); tc = corner_t(x)
    zt = Z_RB[0] + (Z_RB[1] - Z_RB[0]) * t + RB_DROP * tc + 0.004
    zb = Z_LB[0] + (Z_LB[1] - Z_LB[0]) * t + LB_DROP * tc
    h = zt - zb
    return [(-0.060, zt), (-0.034, zt - 0.001), (-0.026, zt - 0.003), (-0.022, zt - 0.007), (-0.019, zt - 0.27 * h),
            (-0.016, zt - 0.52 * h), (-0.014, zt - 0.76 * h), (-0.015, zb + 0.009), (-0.019, zb + 0.003),
            (-0.026, zb + 0.0005), (-0.060, zb), (-0.140, zb)]


def rib_mat(z):
    return "bumper_stripe" if any(abs(z - zc) < RIB_HW * 0.6 for zc in RIBS) else "paint_gunmetal"


def bumper_path():
    return mk.spline_path(BUMPER_CTRL, ds=0.008, start_slope=BUMPER_A)


def end_cap(part, G, mat, ends=(0, -1)):
    n = G.shape[1]
    for end in ends:
        e = end % len(G)
        ci = part.add_v(G[e].mean(axis=0))
        base = e * n
        for j in range(n - 1):
            f = [base + j, base + j + 1, ci]
            part.add_f(f if e == 0 else f[::-1], mat)


ARCH_F = (-1.155, 0.317, 0.324)   # body_profile arch_front (y, z, r), BA frame


def arch_end(G, path, y0=-1.53, gap=0.010):
    """Stretch the side-return columns (y > y0) row by row so each row ends on the front arch circle + gap."""
    yl = path[-1, 1]
    for j in range(G.shape[1]):
        z = G[-1, j, 2]
        ya = g.arch_edge_y("front", z, "front", photo_frame=True)     # traced lip outline (body_profile arch_shapes)
        ye = ya - gap if ya is not None else yl
        ye = min(ye, yl + 0.06)
        for i in range(len(path)):
            if path[i, 1] > y0:
                t = (path[i, 1] - y0) / (yl - y0)
                G[i, j, 1] = y0 + t * (ye - y0)


def return_flange(G, depth=0.025):
    """Append a last column turned inward (-x) at the arch end: the bumper's return flange into the wheel arch."""
    last = G[-1].copy()
    last[:, 0] -= depth
    last[:, 1] += 0.004
    return np.concatenate([G, last[None]], axis=0)


def bumper():
    path, tan, s = bumper_path()
    xp = PLATE["w"] / 2 + PLATE["margin"]
    path, tan = insert_x(path, tan, [xp - 0.004, xp])
    G = mk.sweep_var(path, tan, lambda x, y: bumper_profile(x))
    prof0 = bumper_profile(0.0)
    z0, z1 = PLATE["z"] - PLATE["h"] / 2 - PLATE["margin"], PLATE["z"] + PLATE["h"] / 2 + PLATE["margin"]
    nrm = np.c_[tan[:, 1], -tan[:, 0]]
    for i, (x, _) in enumerate(path):                 # plate recess (flat, ribs stop at its edges)
        if x > xp - 0.004 + 1e-6:
            continue
        for j, (d, z) in enumerate(prof0):
            if z0 - 1e-6 <= z <= z1 + 1e-6 and j > 6:
                dd = (FACE_MAX - PLATE["recess"]) - d
                G[i, j, 0] += nrm[i, 0] * dd; G[i, j, 1] += nrm[i, 1] * dd
    arch_end(G, path)
    G = return_flange(G)
    G = mk.full_from_half(G)
    zs = [z for _, z in prof0]
    p = mk.Part()
    p.grid(G, None, mats=lambda i, j: rib_mat(0.5 * (zs[j] + zs[j + 1])), flip=True)
    lip = mk.Part()
    Lh = mk.sweep_var(path, tan, lambda x, y: lip_profile(x))
    arch_end(Lh, path)
    Lh = return_flange(Lh)
    Lg = mk.full_from_half(Lh)
    lip.grid(Lg, "trim_grey", flip=True)
    # number plate (white, 520 x 111) sitting in the recess, following the V of the face behind it
    pl = mk.Part()
    w, h = PLATE["w"] / 2, PLATE["h"] / 2
    P = np.zeros((9, 3, 3))
    for i in range(9):
        x = -w + 2 * w * i / 8
        yb = float(np.interp(abs(x), path[:, 0], path[:, 1]))
        for j in range(3):
            P[i, j] = (x, yb - FACE_MAX + PLATE["recess"] - FACE_MAX - 0.004, PLATE["z"] - h + 2 * h * j / 2)
    pl.grid(P, "plate_front")
    return {"BUMPER_F": p.weld(), "BUMPER_F_LIP": lip.weld(), "PLATE_F": pl}


def insert_x(path, tan, xs):
    """Insert exact path points at the given x on the straight front segment (keeps columns at recess edges)."""
    P, T = list(path), list(tan)
    for xv in xs:
        for i in range(len(P) - 1):
            if P[i][0] < xv < P[i + 1][0] and abs(T[i][1]) < 0.2:
                t = (xv - P[i][0]) / (P[i + 1][0] - P[i][0])
                P.insert(i + 1, P[i] + (P[i + 1] - P[i]) * t); T.insert(i + 1, T[i]); break
    return np.array(P), np.array(T)


# ---------------- lamp panel, grille surround, lamps ----------------
from scipy.interpolate import PchipInterpolator

PANEL_Z0, PANEL_Z1 = 0.540, 0.712          # bumper shelf -> under the bonnet lip
PANEL_RAKE = 0.32                          # dy/dz of the lamp panel (HL_IB->HL_IT, IND_OB->IND_OT)
_PB = PchipInterpolator([0.0, 0.344, 0.40, 0.50, 0.60, 0.663, 0.70],
                        [-1.7795, -1.7525, -1.7495, -1.7345, -1.7105, -1.6815, -1.655])
HL = {k: np.array(v) for k, v in {"IB": (0.4003, -1.748, 0.5651), "OB": (0.600, -1.7084, 0.5629),
                                  "IT": (0.4011, -1.7027, 0.7034), "OT": (0.5951, -1.6699, 0.7051)}.items()}
IND = {"OB": np.array((0.6632, -1.6787, 0.5599)), "OT": np.array((0.6570, -1.6434, 0.7015))}
# Grille surround (two-view triangulation c20 + cCF, 2026-10-12; ray gaps < 1 cm): opening edge at x 0.341,
# z 0.569 / 0.648 (outer end), 0.578 / 0.651 (centre) - matches BA GRO_B / GRO_T; frame outer edge x 0.379-0.385,
# top corner z 0.695, bottom z 0.550; groove line across the top bar z 0.666. The face is raked back like the
# headlamps (dy/dz 0.33) and V-shaped in plan (0.15); its front sits ~1 cm ahead of the visible opening edge
# (chamfer). Top edge rises to ~0.717 at the centre, tucked under the bonnet lip (c20 centre column).
SUR_Y0, SUR_A, SUR_RAKE, SUR_ZR = -1.797, 0.15, 0.33, 0.60   # face: y = SUR_Y0 + SUR_A*|x| + SUR_RAKE*(z - SUR_ZR)
SUR = {"x": 0.382, "z0": 0.551, "z1": (0.708, 0.695), "ox": 0.341, "oz": (0.573, 0.650), "r": 0.010,
       "depth": 0.012, "groove_z": 0.666}


def panel_y(x, z):
    return float(_PB(min(abs(x), 0.70))) + PANEL_RAKE * (z - 0.556)


def map_panel(V2, off=0.0):
    return np.array([(x, panel_y(x, z) + off, z) for x, z in V2])


def lamp_panel():
    """Body-colour lamp panel (left half + mirror): C-shaped region round the lamp cluster opening."""
    x_end = 0.672                                  # just past the indicator wrap, meets the wing (build_body front_cut)
    zl0, zl1, xl = 0.5665, 0.7015, 0.403
    r = 0.010
    ring = [(0.0, PANEL_Z0), (x_end, PANEL_Z0), (x_end, zl0)]
    for cx, cz, a0 in ((xl + r, zl0 + r, 270), (xl + r, zl1 - r, 180)):
        for k in range(1, 7):
            a = math.radians(a0 - 90 * k / 6); ring.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    # hole behind the grille surround, following its sloped top edge; open at the centre where the surround top
    # rises above the panel top
    xs_, zs0 = SUR["x"] - 0.003, SUR["z0"] + 0.003
    zt = lambda x: sur_ztop(x) - 0.003
    xc = min(xs_, max(0.0, (zt(0.0) - PANEL_Z1) / (zt(0.0) - zt(SUR["x"])) * SUR["x"])) if zt(0.0) > PANEL_Z1 else None
    ring += [(x_end, zl1), (x_end, PANEL_Z1)]
    if xc is not None:
        ring += [(xc, PANEL_Z1), (xs_, zt(xs_)), (xs_, zs0), (0.0, zs0)]
    else:
        ring += [(0.0, PANEL_Z1), (0.0, zt(0.0)), (xs_, zt(xs_)), (xs_, zs0), (0.0, zs0)]
    # densify long edges so the V and the rake are followed
    ring = densify(ring, 0.01)
    V2, T = mk.tri_region(ring, max_area=0.00012)
    p = mk.Part()
    for q in map_panel(V2):
        p.add_v(q)
    for t in T:
        p.add_f([int(t[0]), int(t[1]), int(t[2])], "paint_gunmetal")
    full = p.merge(p.mirrored()).weld(1e-5)
    return full


def densify(ring, step):
    out = []
    R = list(ring)
    for a, b in zip(R, R[1:] + R[:1]):
        a, b = np.array(a), np.array(b)
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        for k in range(n):
            out.append(tuple(a + (b - a) * k / n))
    return out


def sur_y(x, z):
    return SUR_Y0 + SUR_A * abs(x) + SUR_RAKE * (z - SUR_ZR)


def sur_ztop(x):
    zc, zo = SUR["z1"]
    return zc + (zo - zc) * min(1.0, abs(x) / SUR["x"])


def grille():
    """Body-colour surround (raked V face, sloped top under the bonnet lip, groove across the top bar, chamfered
    opening) and the black slatted insert."""
    X, Z0, OX, (OZ0, OZ1), r = SUR["x"], SUR["z0"], SUR["ox"], SUR["oz"], SUR["r"]
    Z1 = sur_ztop(X)
    # left half front face: outer C ring with the half opening
    ring = [(0.0, Z0)]
    for cx, cz, a0 in ((X - r, Z0 + r, 270), (X - r, Z1 - r, 0)):
        for k in range(7):
            a = math.radians(a0 + 90 * k / 6); ring.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    ring += [(0.0, sur_ztop(0.0)), (0.0, OZ1)]
    hole = []
    for cx, cz, a0 in ((OX - r, OZ1 - r, 90), (OX - r, OZ0 + r, 0)):
        for k in range(7):
            a = math.radians(a0 - 90 * k / 6); hole.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    ring += hole + [(0.0, OZ0)]
    ring = densify(ring, 0.012)
    V2, T = mk.tri_region(ring, max_area=0.0001)
    sur = mk.Part()
    for x, z in V2:
        sur.add_v((x, sur_y(x, z), z))
    for t in T:
        sur.add_f([int(t[0]), int(t[1]), int(t[2])], "paint_gunmetal")
    # outer walls back to the lamp panel (outer ring part from (0,Z0) round to the top at the centre)
    k1 = next(i for i, q in enumerate(ring) if abs(q[0]) < 1e-9 and abs(q[1] - sur_ztop(0.0)) < 1e-9)
    outer = ring[:k1 + 1]
    front = [sur.add_v((x, sur_y(x, z), z)) for x, z in outer]
    back = [sur.add_v((x, min(panel_y(x, z) - 0.003, sur_y(x, z) + 0.040), z)) for x, z in outer]
    for i in range(len(outer) - 1):
        sur.add_f([front[i], back[i], back[i + 1], front[i + 1]], "paint_gunmetal")
    # opening chamfer: from the opening edge back SUR depth and a few mm inwards to the insert
    k2 = next(i for i, q in enumerate(ring) if abs(q[0]) < 1e-9 and abs(q[1] - OZ1) < 1e-9)
    op = ring[k2:]
    f2 = [sur.add_v((x, sur_y(x, z), z)) for x, z in op]
    cen = np.array([0.0, 0.5 * (OZ0 + OZ1)])
    b2 = []
    for x, z in op:
        dx, dz = x - cen[0], z - cen[1]
        L = math.hypot(dx / 0.35, dz / 0.035) or 1
        sx = x - 0.004 * (dx / 0.35) / L * (1 if x > 0.01 else 0)
        sz = z - 0.005 * (dz / 0.035) / L
        b2.append(sur.add_v((sx, sur_y(sx, sz) + SUR["depth"], sz)))
    for i in range(len(op) - 1):
        sur.add_f([f2[i], b2[i], b2[i + 1], f2[i + 1]], "paint_gunmetal")
    sur = sur.merge(sur.mirrored()).weld(1e-6)
    # groove across the top bar: thin dark strip a hair in front of the face (reads as the pressed line)
    gr = mk.Part()
    zg, hw, xg = SUR["groove_z"], 0.0015, X - 0.014
    Gg = np.zeros((25, 2, 3))
    for i in range(25):
        x = -xg + 2 * xg * i / 24
        for j, z in enumerate((zg - hw, zg + hw)):
            Gg[i, j] = (x, sur_y(x, z) - 0.0006, z)
    gr.grid(Gg, "panel_gap")
    # insert: black backing plane + horizontal slats, following the raked V face
    ins = mk.Part()
    G = np.zeros((25, 2, 3))
    for i in range(25):
        x = -OX + 2 * OX * i / 24
        for j, z in enumerate((OZ0 - 0.004, OZ1 + 0.004)):
            G[i, j] = (x, sur_y(x, z) + SUR["depth"] + 0.012, z)
    ins.grid(G, "grille_black")
    n_sl = 6
    for k in range(n_sl):
        zc = OZ0 + (OZ1 - OZ0) * (k + 0.5) / n_sl
        prof = [(0.0, zc + 0.0035), (-0.004, zc + 0.0045), (-0.010, zc + 0.002), (-0.010, zc - 0.002), (-0.004, zc - 0.0045), (0.0, zc - 0.0035)]
        S = np.zeros((25, len(prof), 3))
        for i in range(25):
            x = -OX + 2 * OX * i / 24
            for j, (d, z) in enumerate(prof):
                S[i, j] = (x, sur_y(x, z) + SUR["depth"] + 0.012 + d, z)
        ins.grid(S, "grille_black", flip=True)
    return {"GRILLE_SURROUND": sur, "GRILLE_INSERT": ins, "GRILLE_GROOVE": gr}


def headlamp():
    """Left headlamp: flat glass on the BA quad (4 mm proud of nothing: recessed 3 mm), black housing walls back
    90 mm, chrome parabolic reflector, plus the amber indicator wrapping round the corner to the wing."""
    ib, ob, it, ot = HL["IB"], HL["OB"], HL["IT"], HL["OT"]
    n = np.cross(ob - ib, it - ib); n /= np.linalg.norm(n)
    if n[1] > 0:
        n = -n
    inset = -0.003 * n
    P = mk.quad_patch(ib + inset, ob + inset, ot + inset, it + inset, 16, 10)
    glass = mk.Part(); glass.grid(P, "lamp_clear", flip=False)
    # housing: walls from the glass rim back along -n
    rim = list(P[:, 0]) + list(P[-1, 1:]) + list(P[::-1, -1][1:]) + list(P[0, ::-1][1:-1])
    house = mk.Part()
    a = [house.add_v(q) for q in rim]
    b = [house.add_v(q - 0.09 * n) for q in rim]
    for i in range(len(rim)):
        j = (i + 1) % len(rim)
        house.add_f([a[i], a[j], b[j], b[i]], "trim_black")
    # reflector: paraboloid behind the glass
    c = 0.25 * (ib + ob + it + ot) - 0.012 * n
    u = (ob - ib) / np.linalg.norm(ob - ib); v = np.cross(n, u)
    R = np.zeros((25, 9, 3))
    for i in range(25):
        th = 2 * math.pi * i / 24
        for j in range(9):
            rr = 0.065 * j / 8
            ex = rr * math.cos(th) * 1.45; ey = rr * math.sin(th)
            depth = 0.075 * (j / 8) ** 2
            R[i, j] = c + u * ex + v * ey - n * (0.075 - depth)
    refl = mk.Part(); refl.grid(R, "chrome", close_u=True, flip=True)
    # indicator: front face from the headlamp outer edge to the corner, then a 22 mm wrap back along the wing
    ob2, ot2 = ob + inset, ot + inset
    iob, iot = IND["OB"], IND["OT"]
    side = np.array([0.012, 0.022, 0.0])
    G = np.array([[ob2, ot2], [iob + 0.25 * (ob2 - iob) * 0 , iot], [iob + side, iot + side]])
    Gd = np.zeros((9, 6, 3))
    for i in range(9):
        t = i / 8
        if t <= 0.6:
            s = t / 0.6; A = ob2 + (iob - ob2) * s; B = ot2 + (iot - ot2) * s
        else:
            s = (t - 0.6) / 0.4; A = iob + side * s; B = iot + side * s
        for j in range(6):
            Gd[i, j] = A + (B - A) * j / 5
    ind = mk.Part(); ind.grid(Gd, "lamp_amber", flip=False)
    # indicator housing: black walls from the lens rim straight back 50 mm, closed at the back (no see-through)
    irim = list(Gd[:, 0]) + list(Gd[-1, 1:]) + list(Gd[::-1, -1][1:]) + list(Gd[0, ::-1][1:-1])
    ih = mk.Part()
    back = np.array([-0.025, 0.045, 0.0])            # angled inward so the outer wall stays inside the wing
    a = [ih.add_v(q + np.array([0.0, 0.001, 0.0])) for q in irim]
    b = [ih.add_v(q + back) for q in irim]
    for i in range(len(irim)):
        j = (i + 1) % len(irim)
        ih.add_f([a[i], b[i], b[j], a[j]], "trim_black")
    cb = ih.add_v(np.mean(irim, axis=0) + back)
    for i in range(len(irim)):
        ih.add_f([b[i], cb, b[(i + 1) % len(irim)]], "trim_black")
    parts = {"HEADLAMP_GLASS": glass, "HEADLAMP_HOUSING": house, "HEADLAMP_REFLECTOR": refl, "INDICATOR_F": ind,
             "INDICATOR_HOUSING_F": ih}
    out = {}
    for k, p in parts.items():
        out[k + "_L"] = p
        out[k + "_R"] = p.mirrored()
    return out


def build():
    parts = {}
    parts.update(bumper())
    parts["LAMP_PANEL"] = lamp_panel()
    parts.update(grille())
    parts.update(headlamp())
    return parts


if __name__ == "__main__":
    parts = build()
    mk.save(parts, sys.argv[1] if len(sys.argv) > 1 else "data/front_end.json")
    for k, p in parts.items():
        print(k, len(p.v), "verts", len(p.f), "faces", sorted(set(p.m)))
