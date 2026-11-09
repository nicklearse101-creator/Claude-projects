"""Generate the GTE alloy face mesh (runs in plain Python, not Blender) -> blender/data/wheel_face.json.

Wheel-local frame as build_wheels.py: x = axial (outboard +), y = u (rearward on a left wheel), z = v (up).
Design traced from tools/photomatch wheel_rect.png (F400 PTF front wheel rectified onto the face plane).
The face centre was taken from the centre plate (the rim-lip ellipse is shifted by parallax, ~25 mm outboard):
  centre (410, 345) px, 1473 px/m (lip radius 288 px = 195.5 mm).
Re-measured 2026-10-13 (ESTIMATE, +-2 mm): cS (anglia_side) front-right and rear-right wheels rectified onto the
face plane (near-perpendicular view), windows/slots fitted to the dark openings (between-class grey-level fit over both
wheels), slots measured across each arm; cap shape checked against the sharper cCF front-left wheel:
  arms: radial bands at 120 deg spacing, half-width 72 mm, from the cap to the outer ring
  windows: everything between neighbouring arms inside r = 153 mm, 6 mm fillets (inner V tip at r ~84 mm)
  slots: two per arm, +-24 mm either side of the arm axis (parallel to it), 17 mm wide, r 80..160 mm, round ends
    (was +-38 mm: the slots sat at the arm edges and made the arms read as thin bars)
  centre cap: straight edges across the arms at 73 mm (the slots start just outside), its other sides are the window
    edges (the windows bite V-notches into it, 3 mm land), 8 mm corner radii, raised 9 mm with a 3 mm chamfer
  outer ring: r 153..186 mm; lip lathed in build_wheels.py
"""
import json
import math
import os
import sys

import numpy as np
import triangle
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

R_FACE = 0.186
R_WIN = 0.153
ARM_DEG = (32.0, 152.0, 272.0)
ARM_HW = 0.072
FILLET = 0.006
SLOT_P, SLOT_HW, SLOT_A = 0.024, 0.0085, (0.0885, 0.1515)
PLATE_ARM_D, PLATE_GAP, PLATE_R = 0.073, 0.003, 0.008
PLATE_H, PLATE_CH = 0.009, 0.003
FACE_X = 0.0635 - 0.020          # outer ring plane (20 mm inside the outer flange)
DISH = 0.006                     # face dishes 6 mm towards the centre
WALL = 0.030                     # depth of the window / slot walls
CHAMF = 0.002                    # edge chamfer on window / slot edges
STEP = 0.004                     # boundary resampling step


def depth(r):
    return FACE_X - DISH * max(0.0, 1.0 - r / R_FACE) ** 1.5


def band(deg, hw, a0=-0.01, a1=0.3):
    b = box(a0, -hw, a1, hw)
    return affinity.rotate(b, deg, origin=(0, 0))


def windows():
    disk = Point(0, 0).buffer(R_WIN, 256)
    arms = unary_union([band(a, ARM_HW) for a in ARM_DEG])
    w = disk.difference(arms)
    w = w.buffer(-FILLET, 64).buffer(FILLET, 64)
    return list(w.geoms)


def slots():
    out = []
    for a in ARM_DEG:
        for s in (-1, 1):
            ln = box(SLOT_A[0], s * SLOT_P - 1e-6, SLOT_A[1], s * SLOT_P + 1e-6)
            sl = ln.buffer(SLOT_HW, 32)
            out.append(affinity.rotate(sl, a, origin=(0, 0)))
    return out


def plate():
    """Cap: inside the three edges across the arms, minus the windows (plus a PLATE_GAP land), corners rounded."""
    big = 1.0
    p = Point(0, 0).buffer(0.3, 64)
    for a in ARM_DEG:
        p = p.intersection(affinity.rotate(box(-big, -big, PLATE_ARM_D, big), a, origin=(0, 0)))
    p = p.difference(unary_union(windows()).buffer(PLATE_GAP, 64))
    p = p.buffer(-PLATE_R, 64).buffer(PLATE_R, 64)
    return max(p.geoms, key=lambda g: g.area) if p.geom_type == "MultiPolygon" else p


def resample(poly_coords, step=STEP):
    pts = np.asarray(poly_coords)[:-1]
    seg = np.r_[np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1)]
    L = seg.sum()
    n = max(12, int(round(L / step)))
    cum = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, L, n, endpoint=False)
    closed = np.vstack([pts, pts[:1]])
    x = np.interp(t, cum, closed[:, 0]); y = np.interp(t, cum, closed[:, 1])
    out = np.c_[x, y]
    # orient counter-clockwise
    area = 0.5 * np.sum(out[:, 0] * np.roll(out[:, 1], -1) - np.roll(out[:, 0], -1) * out[:, 1])
    return out if area > 0 else out[::-1]


def vnormals(loop):
    """Outward normals (for a CCW loop) per vertex, mitre-averaged."""
    prev = np.roll(loop, 1, axis=0); nxt = np.roll(loop, -1, axis=0)
    t = nxt - prev
    n = np.c_[t[:, 1], -t[:, 0]]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def build():
    disk = resample(Point(0, 0).buffer(R_FACE, 512).exterior.coords, 0.004)
    holes = [resample(w.exterior.coords) for w in windows()] + [resample(s.exterior.coords, 0.003) for s in slots()]
    pl = resample(plate().exterior.coords, 0.003)
    loops = [disk] + holes + [pl]
    V = []; S = []; H = []
    for lp in loops:
        i0 = len(V)
        V.extend(lp.tolist())
        n = len(lp)
        S.extend([[i0 + k, i0 + (k + 1) % n] for k in range(n)])
    for lp in holes + [pl]:
        H.append(Polygon(lp).representative_point().coords[0])
    tri = triangle.triangulate({"vertices": np.array(V), "segments": np.array(S), "holes": np.array(H)}, "pq28a0.00003Y")
    tv = tri["vertices"]; tt = tri["triangles"]
    verts = [[depth(math.hypot(u, v)), u, v] for u, v in tv]
    faces = [[int(a), int(b), int(c)] for a, b, c in tt]
    mats = [0] * len(faces)
    # map the original loop vertices to triangulated indices (Y keeps them, same order first)
    idx = 0; loop_idx = []
    for lp in loops:
        loop_idx.append(list(range(idx, idx + len(lp)))); idx += len(lp)
    assert np.allclose(tv[:idx], np.array(V)), "triangle reordered the input vertices"

    def add(p):
        verts.append([float(p[0]), float(p[1]), float(p[2])]); return len(verts) - 1

    # walls: chamfer then straight wall into the dish (holes are CCW loops; their inside is the opening)
    for li, lp in zip(loop_idx[1:1 + len(holes)], holes):
        nrm = vnormals(lp)            # outward of the opening = into the metal
        ring0 = li
        ring1 = [add((depth(math.hypot(*p)) - CHAMF, *(p - nrm[k] * CHAMF))) for k, p in enumerate(lp)]
        ring2 = [add((depth(math.hypot(*p)) - WALL, *(p - nrm[k] * CHAMF))) for k, p in enumerate(lp)]
        n = len(lp)
        for a, b in ((ring0, ring1), (ring1, ring2)):
            for k in range(n):
                k1 = (k + 1) % n
                faces.append([a[k], b[k], b[k1], a[k1]]); mats.append(0)
    # centre plate: chamfer up to a flat top (material 1)
    li = loop_idx[-1]
    nrm = vnormals(pl)
    zb = [depth(math.hypot(*p)) for p in pl]
    top = [add((zb[k] + PLATE_H, *(p - nrm[k] * PLATE_CH))) for k, p in enumerate(pl)]
    mid = [add((zb[k] + PLATE_H - PLATE_CH, *p)) for k, p in enumerate(pl)]
    n = len(pl)
    for a, b in ((li, mid), (mid, top)):
        for k in range(n):
            k1 = (k + 1) % n
            faces.append([a[k1], b[k1], b[k], a[k]]); mats.append(0)
    # flat top: triangulate the inset loop
    tl = np.array([verts[i][1:] for i in top])
    tr = triangle.triangulate({"vertices": tl, "segments": np.array([[k, (k + 1) % n] for k in range(n)])}, "pq28a0.00004Y")
    assert np.allclose(tr["vertices"][:n], tl)
    base = len(verts)
    for k in range(n, len(tr["vertices"])):
        u, v = tr["vertices"][k]; add((zb[0] + PLATE_H, u, v))
    zt = zb[0] + PLATE_H
    for i in top:
        verts[i][0] = zt
    m = lambda i: top[i] if i < n else base + (i - n)
    for a, b, c in tr["triangles"]:
        faces.append([m(int(a)), m(int(b)), m(int(c))]); mats.append(1)
    return {"verts": verts, "faces": faces, "mats": mats,
            "params": {"R_FACE": R_FACE, "FACE_X": FACE_X, "WALL": WALL, "R_WIN": R_WIN}}


if __name__ == "__main__":
    out = sys.argv[1]
    d = build()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(d, f, separators=(",", ":"))
    print(len(d["verts"]), "verts", len(d["faces"]), "faces")
