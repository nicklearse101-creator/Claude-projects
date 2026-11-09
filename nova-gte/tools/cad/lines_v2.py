"""Character-line network v2: v1 (lines.py) plus the GA end and plan views traced (trace_view.py) and the outlines of the
parts already built from measured points (lines_from_parts.py), so the ends of the car are as well covered as the flank.

Each new GA line is 2D in its own view; the missing coordinate comes from a second source, recorded per line:
  rear face   y = 1.735 - 0.88|x|^6.4  (rear-face plan curve, fits BA TL_BI / TL_BO to 1 mm)
  rear glass  y(z) on the line through BA HG_T / HG_B  (ESTIMATE: no plan curvature)
  C-pillar    y(z) from the side tailgate_shut trace below z 0.882, the HG line above  (ESTIMATE above)
  spoiler     y = tail of the side roof trace  (ESTIMATE)
  bumpers     y from the GA plan trace, shifted so the centre sits on the FIA overhang (front 670, rear 609 mm)
              - the GA sheet is the 1990 facelift, its bumpers stand ~1.5-2 cm further out  (ESTIMATE)
  front face  y from the nearest point of the built lamp panel / headlamp / grille outline  (ESTIMATE)
  screen      y from BA WS_T (header) / the WS_B->WS_T line (A-pillar)
  silhouettes front_body_sil / rear_body_sil are envelopes (max |x| at each z), placed at the y where the GA
              plan half-width peaks in that half; group "envelope" - check against the surface's max |x|, not a curve
Parts outlines come from the model (r8 stage) - group "model_parts", "from_model": true: reference, not truth.

python tools/cad/lines_v2.py   -> blender/data/cad/lines_v2.json
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
V1 = json.load(open(os.path.join(D, "cad", "lines_v1.json")))
TR = json.load(open(os.path.join(D, "cad", "traces_views.json")))["lines"]
LP = json.load(open(os.path.join(D, "cad", "lines_parts.json")))["lines"]
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PLAN = np.array(json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"], float)
BA = V1["points"]                                    # already in the model frame (+dz)
Y_FA, OH_F, OH_R = 1.1715, 0.670, 0.609
Y_FRONT, Y_REAR = -(Y_FA + OH_F), Y_FA + OH_R        # FIA homologation overhangs (SPEC_SHEET)

L = dict(V1["lines"])
# centre_top_photo (body_profile top, photo-fitted) bulges 11 mm off its own points and 10 cm above the tail;
# the GA side tail line and the line blueprint's centre traces cover it - dropped from v2
L.pop("centre_top_photo", None)


def add(name, group, pts, src, x_src, **kw):
    P = [[round(float(x), 5), round(float(y), 5), round(float(z), 5)] for x, y, z in pts]
    if len(P) >= 2:
        L[name] = dict({"group": group, "pts": P, "src": src, "x_from": x_src}, **kw)


def tr(name):
    return np.array(TR[name]["pts"], float)


def rear_face_y(x):
    return 1.735 - 0.88 * abs(x) ** 6.4


hgT, hgB = np.array(BA["HG_T"]), np.array(BA["HG_B"])


def hg_y(z):
    return hgT[1] + (z - hgT[2]) * (hgB[1] - hgT[1]) / (hgB[2] - hgT[2])


ts = np.array(SP["tailgate_shut"], float); ts = ts[np.argsort(ts[:, 1])]
roof_tail = max(p[0] for p in SP["roof_b"])
GA = "GA 1990 sheet, %s view trace"

# ---- rear -------------------------------------------------------------------------------------------------------
for nm in ("rear_lamp", "rear_panel_recess"):
    add(nm, "rear", [(x, rear_face_y(x), z) for x, z in tr(nm)], GA % "rear", "rear view; y = rear-face plan curve")
# centre of the tailgate: the outermost tail line of the GA side view; cubic in z to smooth the pixel jitter
stc = np.array(TR["side_tail_centre"]["pts"], float); stc = stc[(stc[:, 1] > 0.86) & (stc[:, 1] < 1.30)]
yc_poly = np.polyfit(stc[:, 1], stc[:, 0], 3)
X_EDGE = 0.54                                         # glass edge x at the BA HG points


GLASS_BULGE = 0.010     # centre of the backlight behind its edge corners (photo, see below)


def glass_y(x, z):
    # 2026-10-27 (21): the first version took the centre from the GA side tail line, which put the glass bottom
    # centre ~8 cm behind its corners. Two-view photo marks say otherwise: the griffin badge (BADGE_R, gap 7.5 mm)
    # sits at y 1.661 z 0.867, which puts the glass bottom centre ~1 cm behind the BA corner HG_B; at the top the
    # c24 ray through the glass top centre crosses z 1.29 at y ~1.38, ~1 cm behind the HG line. The backlight is
    # nearly flat in plan; the GA side silhouette below z ~1.0 is the quarter corners, not the tailgate centre.
    return hg_y(z) + GLASS_BULGE * (1.0 - min(abs(x) / X_EDGE, 1.0) ** 2)


add("rear_glass", "rear", [(x, glass_y(x, z), z) for x, z in tr("rear_glass")], GA % "rear",
    "rear view; y on the BA HG_T-HG_B line + 10 mm centre bulge (photo marks BADGE_R / c24 glass top)",
    estimate="y: bulge from two photo checks")
# the tailgate below the glass carries on in the glass's plane: glass_y at the badge (z 0.867) is 1.668, the photo
# mark BADGE_R 1.661 - so the tailgate's bottom edge takes glass_y too (it was on the rear face, ~6 cm too far back)
add("rear_tailgate_bottom", "rear", [(x, glass_y(x, z), z) for x, z in tr("rear_tailgate_bottom")], GA % "rear",
    "rear view; y in the tailgate plane (HG line + bulge), checked by BADGE_R", estimate="y")
# the side tail silhouette is the tailgate centre only above z ~1.05 (see glass_y); below that it is dropped
add("tail_centre", "centre", [(0.0, y, z) for y, z in tr("side_tail_centre") if z >= 1.05], GA % "side", "centreline")
def cp_y(z):
    # the two sources disagree by ~27 mm where they meet at the belt; a hard switch put a step in the line
    # (fairness_v2: rear_c_pillar worst of all, 12.8 mm) - blend them over 0.85..0.92 instead
    t = min(max((z - 0.85) / 0.07, 0.0), 1.0); t = t * t * (3 - 2 * t)
    return (1 - t) * float(np.interp(z, ts[:, 1], ts[:, 0])) + t * hg_y(z)


add("rear_c_pillar", "rear", [(x, cp_y(z), z) for x, z in tr("rear_c_pillar")], GA % "rear",
    "rear view; y from side tailgate_shut below the belt, HG line above, blended 0.85-0.92", estimate="y above the belt")
add("rear_spoiler_top", "rear", [(x, roof_tail, z) for x, z in tr("rear_spoiler_top")], GA % "rear",
    "rear view; y = tail of the side roof trace", estimate="y")
add("rear_spoiler_bottom", "rear", [(x, glass_y(x, z), z) for x, z in tr("rear_spoiler_bottom")], GA % "rear",
    "rear view; y from the side tail line (extrapolated above z 1.30)", estimate="y")
pr = tr("plan_rear_corner"); pr = pr[pr[:, 1] < 0.6]; pr = pr[np.argsort(pr[:, 1])]
dyr = Y_REAR - float(np.interp(0.0, pr[:, 1], pr[:, 0]))


def bumper_r_y(x):
    return float(np.interp(x, pr[:, 1], pr[:, 0])) + dyr


for nm in ("rear_bumper_top", "rear_bumper_bottom"):
    add(nm, "rear", [(x, bumper_r_y(x), z) for x, z in tr(nm)], GA % "rear",
        "rear view; y = GA plan bumper line shifted to the FIA rear overhang", estimate="y (facelift bumper)")
add("plan_rear_bumper", "plan", [(x, y + dyr, 0.45) for y, x in pr], GA % "plan",
    "plan; z = mid bumper (0.45)", estimate="z")

# ---- front ------------------------------------------------------------------------------------------------------
pf = tr("plan_front_corner"); pf = pf[pf[:, 1] < 0.55]; pf = pf[np.argsort(pf[:, 1])]
dyf = Y_FRONT - float(np.interp(0.0, pf[:, 1], pf[:, 0]))


def bumper_f_y(x):
    return float(np.interp(x, pf[:, 1], pf[:, 0])) + dyf


add("front_bumper_top", "front", [(x, bumper_f_y(x), z) for x, z in tr("front_bumper_top")], GA % "front",
    "front view; y = GA plan bumper line shifted to the FIA front overhang", estimate="y (facelift bumper)")
add("plan_front_bumper", "plan", [(x, y + dyf, 0.45) for y, x in pf], GA % "plan",
    "plan; z = mid bumper (0.45)", estimate="z")
face = np.array([p for k in ("lamp_panel_1", "headlamp_glass_l_1", "indicator_f_l_1", "grille_surround_1")
                 for p in LP[k]["pts"]], float)


def face_y(x, z):
    d = (face[:, 0] - x) ** 2 + (face[:, 2] - z) ** 2
    return float(face[np.argmin(d), 1])


for nm in ("front_grille", "front_headlamp"):
    add(nm, "front", [(x, face_y(x, z), z) for x, z in tr(nm)], GA % "front",
        "front view; y from the built lamp-panel face", estimate="y; facelift lamp/grille shapes")
wsb, wst = np.array(BA["WS_B"]), np.array(BA["WS_T"])


def ap_y(z):
    t = min(max((z - wsb[2]) / (wst[2] - wsb[2]), 0.0), 1.0)
    return wsb[1] + t * (wst[1] - wsb[1])


add("front_screen_header", "dlo", [(x, wst[1], z) for x, z in tr("front_screen_header")], GA % "front",
    "front view; y = BA WS_T")
add("front_a_pillar", "dlo", [(x, ap_y(z), z) for x, z in tr("front_roof_sil") if z < wst[2]], GA % "front",
    "front view outer A-pillar; y on the WS_B-WS_T line")
add("front_roof_crown", "envelope", [(x, wst[1] + 0.3, z) for x, z in tr("front_roof_sil") if z >= wst[2]],
    GA % "front", "front-view roof silhouette (envelope); y nominal", estimate="y (silhouette)")

# ---- end silhouettes (envelopes) ---------------------------------------------------------------------------------
yf = float(PLAN[PLAN[:, 0] < 0][np.argmax(PLAN[PLAN[:, 0] < 0][:, 1]), 0])
yr = float(PLAN[PLAN[:, 0] > 0][np.argmax(PLAN[PLAN[:, 0] > 0][:, 1]), 0])
add("front_body_sil", "envelope", [(x, yf, z) for x, z in tr("front_body_sil")], GA % "front",
    "front-view silhouette = max |x| at z; placed at the plan's widest front y", estimate="y (silhouette)")
add("rear_body_sil", "envelope", [(x, yr, z) for x, z in tr("rear_body_sil")], GA % "rear",
    "rear-view silhouette = max |x| at z; placed at the plan's widest rear y", estimate="y (silhouette)")

# ---- outlines of parts built from measured points ---------------------------------------------------------------
for nm, l in LP.items():
    add("part_" + nm, "model_parts", l["pts"], "model part outline (" + l.get("src", "r8") + ")", "model",
        from_model=True)

MK = json.load(open(os.path.join(D, "cad", "marks_v2.json")))["points"]
pts = dict(V1["points"]); pts.update({k: v["xyz_model"] for k, v in MK.items()})
out = dict(V1, lines=L, points=pts, _doc=__doc__.split("\n\n")[0],
           hard_points={"front_bumper_face_y": Y_FRONT, "rear_bumper_face_y": Y_REAR,
                        "src": "FIA homologation: length 3622, overhangs 670 / 609 mm (docs/SPEC_SHEET.md)"})
json.dump(out, open(os.path.join(D, "cad", "lines_v2.json"), "w"), indent=1)
new = [n for n in L if n not in V1["lines"]]
for n in new:
    P = np.array(L[n]["pts"])
    print("%-24s %-11s %4d pts  x %.3f..%.3f  y %+.3f..%+.3f  z %.3f..%.3f" % (
        n, L[n]["group"], len(P), P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max(), P[:, 2].min(), P[:, 2].max()))
print("v1 %d lines + %d new = %d" % (len(V1["lines"]), len(new), len(L)))
print("bumper shift: front %+.3f, rear %+.3f (GA plan -> FIA)" % (dyf, dyr))
