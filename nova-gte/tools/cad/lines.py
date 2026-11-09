"""Character-line network v1 (REPLICA_PLAN 4.1): the Nova's key lines as 3D polylines, assembled from what the
project has already measured, so they can be checked against every drawing and photo before anything is surfaced.

Every line is (y, z) from one source and x from another, both recorded per line in the output:
  side traces   blender/data/side_profile.json - the line blueprint's side elevation, model frame (unloaded tyres)
  flank x       skin_x(y, z) = plan half-width (GA plan, plan_profile.json) x normalised section (GA front,
                section_body.json) - the same surface the wing and shell are built on
  glass x       body_profile glass_base_x at the glass base, glass_top_x at the window top, linear between
  roof edge     body_profile cant (y, z) with the roof outline half-width (roof_profile.json)
  bonnet shut   shut_bonnet_wing.json (already 3D)
  windscreen    body_profile scuttle_curve (base, curved in plan), WS_B / WS_T (BA), header straight in plan
  BA points     ba_result.json, every triangulated point (single-view ones flagged)
body_profile and BA heights are in the photo frame: + dz (0.0193) into the model frame.

Left half only (x >= 0); the right is the mirror. Output: blender/data/cad/lines_v1.json

python tools/cad/lines.py
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "blender", "data")
PM = os.path.join(ROOT, "tools", "photomatch")
SP = json.load(open(os.path.join(D, "side_profile.json")))["lines"]
PF = json.load(open(os.path.join(PM, "body_profile.json")))
BA = json.load(open(os.path.join(PM, "ba_result.json")))["points"]
PLAN = np.array(json.load(open(os.path.join(D, "plan_profile.json")))["halfw_merged"], float)
SECT = np.array(json.load(open(os.path.join(D, "section_body.json")))["profile"], float)
SECT = SECT[np.argsort(SECT[:, 0])]
ROOF = json.load(open(os.path.join(D, "roof_profile.json")))
WIN = json.load(open(os.path.join(D, "windows.json")))
SHUT = json.load(open(os.path.join(D, "shut_bonnet_wing.json")))
DZ = float(PF["dz"])
SINGLE_VIEW = {"MIR", "BON_F", "PNL_B", "DSR_B"}           # ba_result _note: weak, single-view


def tr(*names):
    pts = sorted({(round(a, 5), round(b, 5)) for n in names if n in SP for a, b in SP[n]})
    return np.array(pts, float)


def halfw(y):
    return float(np.interp(y, PLAN[:, 0], PLAN[:, 1]))


def skin_x(y, z):
    return halfw(y) * float(np.interp(z, SECT[:, 0], SECT[:, 1]))


GB = np.array(PF["glass_base_x"], float); GT = np.array(PF["glass_top_x"], float)
gb_z = tr("glass_base", "glass_base_b"); gt_z = tr("dlo_top_fwd", "dlo_top", "dlo_top_b")


def glass_x(y, z):
    zb = float(np.interp(y, gb_z[:, 0], gb_z[:, 1])); zt = float(np.interp(y, gt_z[:, 0], gt_z[:, 1]))
    xb = float(np.interp(y, GB[:, 0], GB[:, 1])); xt = float(np.interp(y, GT[:, 0], GT[:, 1]))
    t = min(max((z - zb) / max(zt - zb, 1e-6), 0.0), 1.0)
    return xb + t * (xt - xb)


L = {}


def add(name, group, pts, src, x_src):
    P = [[round(float(x), 5), round(float(y), 5), round(float(z), 5)] for x, y, z in pts]
    if len(P) >= 2:
        L[name] = {"group": group, "pts": P, "src": src, "x_from": x_src}


# ---- centreline (x = 0) ---------------------------------------------------------------------------------------
# separate lines: merged and sorted by y, the overlapping bonnet/screen/roof/backlight traces zigzagged at the tail
for nm, srcs in (("centre_bonnet", ("bonnet_top", "bonnet_top_b")), ("centre_screen", ("screen",)),
                 ("centre_roof", ("roof", "roof_b")), ("centre_backlight", ("backlight",))):
    c = tr(*srcs)
    add(nm, "centre", [(0.0, y, z) for y, z in c], "line blueprint side: " + "+".join(srcs), "centreline")
t = np.array(PF["top"], float)
add("centre_top_photo", "centre", [(0.0, y, z + DZ) for y, z in t], "body_profile top (photo-fitted)", "centreline")

# ---- flank lines (x = skin) -----------------------------------------------------------------------------------
for nm, srcs, grp in (("belt", ("belt", "belt_b"), "body"),
                      ("crease_front", ("crease_front", "crease_front_b"), "crease"),
                      ("crease_rear", ("crease_rear", "crease_rear_b"), "crease"),
                      ("moulding_top", ("moulding_top", "moulding_top_b"), "body"),
                      ("moulding_bot", ("moulding_bot", "moulding_bot_b"), "body"),
                      ("door_bottom", ("door_bottom", "door_bottom_b"), "shut"),
                      ("sill", ("sill", "sill_b"), "body"),
                      ("arch_front", ("arch_front", "arch_front_b"), "arch"),
                      ("arch_rear", ("arch_rear", "arch_rear_b"), "arch"),
                      ("shut_door_front", ("shut_door_front",), "shut"),
                      ("shut_door_rear", ("shut_door_rear",), "shut"),
                      ("tailgate_shut", ("tailgate_shut",), "shut")):
    p = tr(*srcs)
    if nm.startswith(("shut_", "tailgate")):
        p = np.array(SP[srcs[0]], float)               # keep the traced order (these run up/down, not along)
    add(nm, grp, [(skin_x(y, z), y, z) for y, z in p], "line blueprint side: " + "+".join(srcs), "skin_x (plan x section)")

# ---- glass and roof -------------------------------------------------------------------------------------------
add("glass_base", "dlo", [(glass_x(y, z), y, z) for y, z in gb_z], "line blueprint side: glass_base", "body_profile glass_base_x")
add("dlo_top", "dlo", [(glass_x(y, z), y, z) for y, z in gt_z], "line blueprint side: dlo_top", "body_profile glass_top_x")
for k in ("door", "quarter"):
    w = np.array(WIN[k], float)
    add("window_" + k, "dlo", [(glass_x(y, z), y, z) for y, z in w] + [(glass_x(*w[0]), *w[0])],
        "windows.json (traced, fitted to BA corners)", "glass x")
OUT = np.array(ROOF["outline"], float)
cant = np.array(PF["cant"], float)
add("roof_edge", "roof", [(float(np.interp(y, OUT[:, 0], OUT[:, 1])), y, z + DZ) for y, z in cant],
    "body_profile cant (photo)", "roof_profile outline")

# ---- plan: widest line ----------------------------------------------------------------------------------------
zw = float(json.load(open(os.path.join(D, "section_body.json")))["z_widest"])
add("plan_widest", "plan", [(hw, y, zw) for y, hw in PLAN[::4]], "GA plan half-width (plan_profile halfw_merged)",
    "plan; z = section's widest")

# ---- bonnet shut, bonnet V, windscreen ------------------------------------------------------------------------
add("bonnet_shut", "shut", [tuple(p) for p in SHUT["bonnet"]] + [tuple(p) for p in SHUT["scuttle"]],
    "shut_bonnet_wing.json", "bonnet edge column")
v = SHUT["v_line"]; zc = SHUT["bonnet_corner"][2]
add("bonnet_v", "front", [(x, v["y_tip"] + v["a"] * x, zc) for x in np.linspace(0, SHUT["bonnet_corner"][0], 12)],
    "body_profile bonnet_v", "measured V")
SC = PF["scuttle_curve"]
zb = BA["WS_B"][2] + DZ
xb = BA["WS_B"][0]
add("screen_base", "dlo", [(x, min(SC["yb0"] + SC["k"] * x * x, SC["yb_max"]), zb) for x in np.linspace(0, xb, 16)],
    "body_profile scuttle_curve + BA WS_B", "plan curve")
yt, ztp = BA["WS_T"][1], BA["WS_T"][2] + DZ
add("screen_header", "dlo", [(x, yt, ztp) for x in np.linspace(0, BA["WS_T"][0], 10)], "BA WS_T, header straight in plan",
    "BA")
add("a_pillar", "dlo", [(xb, BA["WS_B"][1], zb), (BA["WS_T"][0], yt, ztp)], "BA WS_B -> WS_T", "BA")

# ---- BA points ------------------------------------------------------------------------------------------------
pts = {k: [round(v[0], 5), round(v[1], 5), round(v[2] + DZ, 5)] for k, v in BA.items() if isinstance(v, list) and len(v) == 3}

out = {"_doc": __doc__.split("\n\n")[0], "frame": "model frame, left half (mirror for the right)", "lines": L,
       "points": pts, "single_view_points": sorted(SINGLE_VIEW & set(pts))}
os.makedirs(os.path.join(D, "cad"), exist_ok=True)
json.dump(out, open(os.path.join(D, "cad", "lines_v1.json"), "w"), indent=1)
for n, l in L.items():
    P = np.array(l["pts"])
    print("%-17s %-6s %4d pts  y %+.3f..%+.3f  z %.3f..%.3f  x %.3f..%.3f" % (n, l["group"], len(P), P[:, 1].min(),
          P[:, 1].max(), P[:, 2].min(), P[:, 2].max(), P[:, 0].min(), P[:, 0].max()))
print("points:", len(pts))
