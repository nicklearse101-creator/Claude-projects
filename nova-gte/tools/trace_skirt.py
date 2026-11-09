"""Trace the GTE's grey sill skirt off Nik's grey side picture, through that picture's own solved camera.

The line blueprint is a base-model Corsa drawing: it carries the rocker's own lower edge (the `sill` line,
z 0.245) and the door's lower edge (`door_bottom`, z 0.30), but nothing of the GTE's bolt-on skirt, which
covers both and sweeps up in front of the rear wheel. The picture is the only source for that, and
tools/photomatch/grey_cams.json holds a camera solved against the bundle-adjusted 3D points, so a point
on the body can be put on the picture and read back.

Method: walk up the body's own surface - x(y, z) = halfw(y) * section(z), the same surface the door is
built on - project each step into the picture, and read the luminance along that path. The skirt is a
dark grey moulding against dark grey paint, so its top edge is a step up in brightness going up.

Two passes, because the edge changes direction:
  - along the car, seeded in the middle of the flat run and followed out both ways, with a slope limit;
  - up the kick-up in front of the rear wheel, where the edge is too steep to have one height per
    station, followed the other way round - one y per height - exactly as the blueprint's pillars are.

A third pass takes the lowest pixel of the car at each station: that is the body's own bottom edge, and
it comes out on the blueprint's `sill` line to within 10 mm, which is the cross-check that the camera and
the surface are both right.

    python tools/trace_skirt.py [out.json] [diag.png]
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "blender", "data", "skirt_profile.json")
DIAG = sys.argv[2] if len(sys.argv) > 2 else None

DZ = 0.0193                                     # model frame -> picture frame is a subtraction
CAM = json.load(open(os.path.join(ROOT, "tools", "photomatch", "grey_cams.json")))
Q, W, H = np.array(CAM["gS"], float), CAM["W"], CAM["H"]
PLAN = np.array(json.load(open(os.path.join(ROOT, "blender", "data", "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(ROOT, "blender", "data", "section_profile.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
SP = json.load(open(os.path.join(ROOT, "blender", "data", "side_profile.json")))["lines"]

R, _ = cv2.Rodrigues(Q[:3])
TV, F, K1 = Q[3:6], Q[6], Q[7]


def project(X):
    Xc = np.atleast_2d(np.asarray(X, float)) @ R.T + TV
    x, y = Xc[:, 0] / Xc[:, 2], Xc[:, 1] / Xc[:, 2]
    s = 1 + K1 * (x * x + y * y)
    return np.stack([W / 2 + F * x * s, H / 2 + F * y * s], 1)


def skin_x(y, z_model):
    return float(np.interp(y, PLAN[:, 0], PLAN[:, 1])) * float(np.interp(z_model, SECT[:, 0], SECT[:, 1]))


IM = cv2.imread(os.path.join(ROOT, "reference", "photos", "grey_studio", "side.png"), cv2.IMREAD_UNCHANGED)
ALPHA = IM[:, :, 3].astype(float) / 255.0 if IM.shape[2] == 4 else np.ones(IM.shape[:2])
GR = cv2.cvtColor(IM[:, :, :3], cv2.COLOR_BGR2GRAY).astype(float)


def sample(img, u, v):
    u = min(max(u, 0.0), img.shape[1] - 1.001); v = min(max(v, 0.0), img.shape[0] - 1.001)
    i, j = int(v), int(u); a, b = v - i, u - j
    return ((1 - a) * ((1 - b) * img[i, j] + b * img[i, j + 1])
            + a * ((1 - b) * img[i + 1, j] + b * img[i + 1, j + 1]))


def ramp(pts):
    """Luminance, the car's alpha, and the smoothed first difference along a list of 3D points."""
    uv = project(pts)
    lum = np.array([sample(GR, u, v) for u, v in uv])
    alp = np.array([sample(ALPHA, u, v) for u, v in uv])
    sm = np.convolve(np.r_[np.repeat(lum[0], 3), lum, np.repeat(lum[-1], 3)], np.ones(7) / 7.0, "valid")
    return uv, alp > 0.6, np.diff(sm)


def curve(*names):
    pts = sorted({(round(a, 5), round(b, 5)) for n in names for a, b in SP[n]})
    return np.array(pts, float)


door_bottom = curve("door_bottom", "door_bottom_b")
sill_line = curve("sill", "sill_b")

Y0, Y1, DY = -0.92, 0.95, 0.01                  # past both arch lips; the ends are trimmed when built
ZS = np.arange(0.120, 0.560, 0.0015)
COLS = {y: ramp([[skin_x(y, z), y, z - DZ] for z in ZS]) for y in np.round(np.arange(Y0, Y1 + 1e-9, DY), 4)}
YS = sorted(COLS)

# ---- the body's own bottom edge ----------------------------------------------------------------
bots = {}
for y in YS:
    body = COLS[y][1]
    k = int(np.argmax(body)) if body.any() else None
    if k is not None and body[k]:
        bots[y] = float(ZS[k])

# ---- the skirt's top edge, along the car -------------------------------------------------------
MINSTEP = 0.6


def peaks(y, lo, hi):
    """Local maxima of the brighten-going-up step inside a height band, with their strengths."""
    body, d = COLS[y][1], COLS[y][2]
    m = (ZS[:-1] > lo) & (ZS[:-1] < hi) & body[:-1]
    if not m.any():
        return np.empty(0), np.empty(0)
    zz, dd = ZS[:-1][m], d[m]
    pk = [i for i in range(1, len(dd) - 1) if dd[i] >= dd[i - 1] and dd[i] > dd[i + 1] and dd[i] > MINSTEP]
    return zz[pk], dd[pk]


SEED_Y = 0.00
zc, dc = peaks(SEED_Y, 0.28, 0.40)
seed = float(zc[int(np.argmax(dc))])
print("seed at y %+.2f: skirt top z %.4f (step %.1f)" % (SEED_Y, seed, dc.max()))

# Along the flat run the edge moves by a millimetre or two per station. A loose tolerance lets it climb
# onto the lower body crease, which is a soft shading change a hundred millimetres higher and runs the
# whole length of the car; TOL keeps it on the crisp one.
TOL = 0.006
tops = {SEED_Y: seed}
ends = {}
for direction in (-1, 1):
    ys = sorted([y for y in YS if (y < SEED_Y if direction < 0 else y > SEED_Y)], reverse=direction < 0)
    cur, slope, gap = seed, 0.0, 0
    last = SEED_Y
    for y in ys:
        pred = cur + slope * DY * direction
        zc, dc = peaks(y, pred - TOL - 0.002 * gap, pred + TOL + 0.002 * gap)
        if zc.size:
            k = int(np.argmin(np.abs(zc - pred)))
            slope = 0.6 * slope + 0.4 * (zc[k] - cur) / (DY * (gap + 1)) * direction
            cur, gap, last = float(zc[k]), 0, y
            tops[y] = cur
        else:
            gap += 1
            if gap > 6:
                break
            cur = pred
    ends[direction] = last
print("flat run follows from y %+.3f to %+.3f" % (ends[-1], ends[1]))

# ---- the kick-up in front of the rear wheel ----------------------------------------------------
# Here the edge climbs about 200 mm in 200 mm, so there is no single height per station. Scan along the
# car at a fixed height instead and take the y where the body darkens into the skirt wedge.
y_knee = ends[1]
z_knee = tops[y_knee]
kick = []
cur, slope, gap = y_knee, 0.9, 0
for z in np.arange(z_knee + 0.004, 0.560, 0.004):
    pred = cur + slope * 0.004
    ys_ = np.arange(max(pred - 0.090, y_knee - 0.02), min(pred + 0.090, 1.10), 0.002)
    uv, body, d = ramp([[skin_x(yy, z), yy, z - DZ] for yy in ys_])
    m = body[:-1]
    if m.sum() < 5:
        break
    zz, dd = ys_[:-1][m], -d[m]                 # darkening going rearward = entering the wedge
    pk = [i for i in range(1, len(dd) - 1) if dd[i] >= dd[i - 1] and dd[i] > dd[i + 1] and dd[i] > MINSTEP]
    if not pk:
        gap += 1
        if gap > 5:
            break
        cur = pred
        continue
    k = pk[int(np.argmin(np.abs(zz[pk] - pred)))]
    if abs(zz[k] - pred) > 0.045 + 0.01 * gap:
        gap += 1
        if gap > 5:
            break
        cur = pred
        continue
    slope = 0.6 * slope + 0.4 * (zz[k] - cur) / (0.004 * (gap + 1))
    cur, gap = float(zz[k]), 0
    kick.append((cur, float(z)))
print("kick-up from (y %+.3f, z %.3f) to (y %+.3f, z %.3f), %d points"
      % (y_knee, z_knee, kick[-1][0], kick[-1][1], len(kick)) if kick else "no kick-up found")

top_line = sorted([(y, z) for y, z in tops.items()] + kick)

print("\n  y      skirt top   body bottom   (blueprint: door_bottom / sill)")
for y in YS:
    if round(y * 100) % 10 or y not in tops:
        continue
    db = float(np.interp(y, door_bottom[:, 0], door_bottom[:, 1]))
    sl = float(np.interp(y, sill_line[:, 0], sill_line[:, 1]))
    print("  %+5.2f   %.3f        %s         %.3f / %.3f"
          % (y, tops[y], "%.3f" % bots[y] if y in bots else "  -  ", db, sl))
d_sill = [bots[y] - float(np.interp(y, sill_line[:, 0], sill_line[:, 1]))
          for y in bots if -0.70 < y < 0.80]
print("\nbody bottom vs the blueprint's sill line: %+.0f mm mean, %.0f mm spread"
      % (1000 * np.mean(d_sill), 1000 * (max(d_sill) - min(d_sill))))

json.dump({
    "source": "reference/photos/grey_studio/side.png through tools/photomatch/grey_cams.json gS",
    "frame": "model frame (picture z + %.4f)" % DZ,
    "note": "skirt_top is the crisp luminance step where the grey moulding starts, followed along the "
            "car and then up the kick-up in front of the rear wheel. body_bottom is the lowest pixel of "
            "the car read on the body surface. ESTIMATE - one picture, one camera.",
    "knee": [round(float(y_knee), 4), round(float(z_knee), 4)],
    "skirt_top": [[round(float(y), 4), round(float(z), 4)] for y, z in top_line],
    "body_bottom": [[round(float(y), 4), round(float(bots[y]), 4)] for y in sorted(bots)],
}, open(OUT, "w"), indent=1)
print("\nwrote", OUT)

if DIAG:
    K = 4
    big = cv2.resize(IM[:, :, :3], None, fx=K, fy=K, interpolation=cv2.INTER_CUBIC)
    for y, z in top_line:
        u, v = project([[skin_x(y, z), y, z - DZ]])[0]
        cv2.circle(big, (int(u * K), int(v * K)), 2, (40, 40, 230), -1)
    for y, z in bots.items():
        u, v = project([[skin_x(y, z), y, z - DZ]])[0]
        cv2.circle(big, (int(u * K), int(v * K)), 2, (40, 200, 40), -1)
    cv2.imwrite(DIAG, big[int(0.42 * H) * K:int(0.95 * H) * K, int(0.15 * W) * K:int(0.80 * W) * K])
    print("wrote", DIAG)
