"""Cross-sections v3 (master plan Phase 6 step 2; DECISIONS (19): the network has no sections).

Builds half-sections (x >= 0, model frame) at stations along y from evidence that already exists, WITHOUT editing any
existing file. Every point carries a class and an uncertainty:
  MEASURED  - read from a trace / BA-fitted window curve (fit tolerance ~5 mm)
  ENVELOPE  - GA front/rear silhouette (max |x| at z), +-16 mm (the two views disagree by up to 16 mm)
  ESTIMATE  - carried or interpolated, not measured at that station
Held-out check: bp_front.png (line-blueprint front elevation) was NOT used to build anything; its outer outline is
extracted here and compared with the GA-derived roof crown and the widest point.

python tools/cad/sections_v3.py   -> blender/data/cad/sections_v3.json, prints the findings
Reads only: lines_v2_fit.json, reference/views/bp_front.png, frame.json. Writes only sections_v3.json.
"""
import json
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAD = os.path.join(ROOT, "blender", "data", "cad")
L = json.load(open(os.path.join(CAD, "lines_v2_fit.json")))["lines"]
P = lambda k: np.array(L[k]["pts"], float)
STATIONS = [-0.10, 0.10, 0.40, 0.80, 1.15]


def cross(curve, y0):
    """(x, z) where the polyline crosses the plane y = y0 (all crossings)."""
    Q, out = P(curve), []
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - y0) * (b[1] - y0) <= 0 and a[1] != b[1]:
            t = (y0 - a[1]) / (b[1] - a[1])
            out.append(((1 - t) * a[0] + t * b[0], (1 - t) * a[2] + t * b[2]))
    return out


def first(curves, y0):
    for c in curves:
        r = cross(c, y0)
        if r:
            return r
    return []


def env(S, z):
    o = np.argsort(S[:, 2])
    return float(np.interp(z, S[o, 2], S[o, 0]))


# ---- evidence ------------------------------------------------------------------------------------------------
crown = P("front_roof_crown")                       # GA front silhouette of the roof: x 0..0.561, z
z_peak, x_lip_sil = crown[:, 2].max(), crown[:, 0].max()
drop = lambda x: z_peak - float(np.interp(x, crown[:, 0], crown[:, 2]))
fsil, rsil = P("front_body_sil"), P("rear_body_sil")
# the rear view reproduces the SOURCED 1535 mm max width; the front view is ~11 mm narrow -> widest point from the rear view
i = int(rsil[:, 0].argmax())
widest = (float(rsil[i, 0]), float(rsil[i, 2]))
re_ref = cross("roof_edge", 0.082)[0][0]            # roof_edge x at the y the GA roof silhouette is placed

# held-out outline of bp_front.png, needed while building so conflicts are reported against BOTH sources
_fr = json.load(open(os.path.join(ROOT, "reference", "views", "frame.json")))["views"]["bp_front"]
_img = cv2.imread(os.path.join(ROOT, "reference", "views", _fr["file"]), cv2.IMREAD_GRAYSCALE)
_dk = _img < 110
_dk[:, :4] = False; _dk[:, -4:] = False; _dk[:4, :] = False; _dk[-4:, :] = False


def bp_maxx(z):
    r = int(round((_fr["rect"][3] - z) * _fr["ppm"]))
    c0 = int(round((0.0 - _fr["rect"][0]) * _fr["ppm"])); c1 = int(round((0.95 - _fr["rect"][0]) * _fr["ppm"]))
    cols = np.where(_dk[r, c0:c1])[0]
    return float(cols.max() / _fr["ppm"]) if len(cols) else None

# ---- sections --------------------------------------------------------------------------------------------------
out, findings = {}, []
for y0 in STATIONS:
    pts = []
    add = lambda name, x, z, cls, sig, src: pts.append(dict(id=name, x=round(float(x), 4), z=round(float(z), 4), cls=cls, sigma_mm=sig, src=src))
    zc = first(["centre_roof"], y0)
    if not zc:
        continue
    zc = zc[0][1]
    add("roof_centre", 0.0, zc, "MEASURED", 5, "centre_roof (line blueprint side trace)")
    re = first(["roof_edge"], y0)
    xe, ze = re[0] if re else (None, None)
    if re:
        x_lip = x_lip_sil * xe / re_ref
        for u in (0.25, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0):
            add("crown_%.2f" % u, u * x_lip, zc - drop(u * x_lip_sil), "ESTIMATE", 10,
                "crown SHAPE measured at y~0.08 (GA front silhouette), carried to this station")
        z_lip = zc - drop(x_lip_sil)
        add("glass_top_edge", xe, ze, "MEASURED", 5, "roof_edge (body_profile cant / side-glass top)")
        if z_lip < ze:
            findings.append("y=%.2f: carried crown puts the roof lip at z=%.3f, BELOW the glass-top edge z=%.3f (%.0f mm): crown shape does not carry to this station" % (y0, z_lip, ze, (ze - z_lip) * 1000))
    for w in ("window_door", "window_quarter"):
        c = cross(w, y0)
        if len(c) >= 2:
            c = sorted(c, key=lambda p: -p[1])
            add("glass_top", c[0][0], c[0][1], "MEASURED", 5, w + " (traced, BA-fitted)")
            add("glass_base", c[-1][0], c[-1][1], "MEASURED", 5, w + " (traced, BA-fitted)")
            break
    b = first(["belt#1", "belt#2"], y0)
    if b:
        add("belt", b[0][0], b[0][1], "MEASURED", 5, "belt z (trace); x from skin_x = numpy-shell estimate -> ESTIMATE in x")
        pts[-1]["x_cls"] = "ESTIMATE"
    add("widest", widest[0], widest[1], "ENVELOPE", 16, "GA rear silhouette peak; matches SOURCED FIA 1535 mm")
    for nm in ("moulding_bot", "sill"):
        c = first([nm], y0)
        if c:
            x, z = c[0]
            ev = env(fsil, z) if nm == "sill" else 0.5 * (env(fsil, z) + env(rsil, z))
            add(nm, x, z, "MEASURED", 5, nm + " z (trace); x from skin_x = ESTIMATE")
            pts[-1]["x_cls"] = "ESTIMATE"
            pts[-1]["x_minus_envelope_mm"] = round((x - ev) * 1000, 1)
            bpx = bp_maxx(z)
            pts[-1]["x_minus_bp_front_mm"] = None if bpx is None else round((x - bpx) * 1000, 1)
            if (x - ev) * 1000 > 16:
                findings.append("y=%.2f: %s x=%.3f (skin_x, ESTIMATE) is %.0f mm outside the GA envelope (%.3f) at z=%.2f but %s mm from the held-out bp_front outline (%s): SOURCES CONFLICT, unresolved. Sourced tyre half-width is 0.7475 (track 1320 + 175 mm section), wider than the GA envelope below z~0.4, so the GA low-z envelope is itself suspect." % (y0, nm, x, (x - ev) * 1000, ev, z, "n/a" if bpx is None else "%+.0f" % ((x - bpx) * 1000), "n/a" if bpx is None else "%.3f" % bpx))
    pts.sort(key=lambda p: (-p["z"], p["x"]))
    out["%.2f" % y0] = dict(points=pts)

# ---- checks ------------------------------------------------------------------------------------------------------
chk = {}
x = np.array([0.2, 0.3, 0.4, 0.45, 0.5, 0.53, 0.55, 0.561])
chk["crown_estimate_vs_silhouette_mm"] = {"%.3f" % xx: round((0.035 * (xx / 0.55) ** 2 - drop(xx)) * 1000, 1) for xx in x}
chk["front_vs_rear_silhouette_mm"] = {"%.2f" % z: round((env(rsil, z) - env(fsil, z)) * 1000, 1) for z in (0.4, 0.5, 0.6, 0.67, 0.75, 0.85)}

# held-out: bp_front.png (never used above). Outer outline per row/column from the dark pixels.
frame = json.load(open(os.path.join(ROOT, "reference", "views", "frame.json")))["views"]["bp_front"]
img = cv2.imread(os.path.join(ROOT, "reference", "views", frame["file"]), cv2.IMREAD_GRAYSCALE)
H, W = img.shape
ppm = frame["ppm"]
x0, x1, z0, z1 = frame["rect"]
dark = img < 110
dark[:, :4] = False; dark[:, -4:] = False; dark[:4, :] = False; dark[-4:, :] = False
col_of = lambda x: int(round((x - x0) * ppm))
row_of = lambda z: int(round((z1 - z) * ppm))
held = {"shape": [H, W]}
rows = {}
for z in (0.40, 0.50, 0.60, 0.65, 0.70, 0.80, 0.90):
    r = row_of(z)
    cols = np.where(dark[r, col_of(0.0):col_of(0.95)])[0]
    rows["%.2f" % z] = round(float(cols.max() / ppm), 4) if len(cols) else None
held["bp_front_max_x_at_z"] = rows
tops = {}
for xx in (0.0, 0.2, 0.3, 0.4, 0.45, 0.5, 0.53, 0.55):
    c = col_of(xx)
    rr = np.where(dark[:, c])[0]
    tops["%.3f" % xx] = round(float(z1 - rr.min() / ppm), 4) if len(rr) else None
held["bp_front_top_z_at_x"] = tops
t0 = tops["0.000"]
held["bp_front_roof_drop_mm"] = {k: (round((t0 - v) * 1000, 1) if (v is not None and t0 is not None) else None) for k, v in tops.items()}
held["ga_roof_drop_mm"] = {k: round(drop(float(k)) * 1000, 1) for k in tops}
chk["held_out_bp_front"] = held
json.dump(dict(_doc=__doc__.split("\n")[0], frame="model frame, left half (x>=0)", stations=out, checks=chk, findings=findings),
          open(os.path.join(CAD, "sections_v3.json"), "w"), indent=1)
print("widest (rear sil):", widest, "| crown peak z", round(z_peak, 3), "| lip x", x_lip_sil)
for k, v in out.items():
    print("== y=%s: %s" % (k, "  ".join("%s(%.3f,%.3f)%s" % (p["id"], p["x"], p["z"], "*" if p.get("x_cls") else "") for p in v["points"] if not p["id"].startswith("crown_"))))
print("== checks"); print(json.dumps(chk, indent=1)); print("== findings"); [print(" -", f) for f in findings]
