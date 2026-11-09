"""Correct the traced front-elevation section where the car's own measured skin points say it is too wide.

blender/data/section_profile.json is the front elevation's silhouette - the widest the body gets anywhere along
the car at each height. Low down that is the side itself (the flank is parallel from the sill to z 0.65). Higher
up it over-states the door and the wing: the door handle (HANDLE_F/R) and the side repeater (SR), triangulated
from four cameras each, sit 10-16 mm inside it at z 0.75-0.79, after allowing ~4-5 mm for each standing proud of
the paint. So the upper flank is pulled in by a smooth ramp from nothing at z 0.62 to 16 mm by z 0.80, and the
result is written as section_body.json for the shell and the wing to share - same input for both, so they still
meet at the door shut.

    python tools/section_body.py
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "blender", "data")
S = json.load(open(os.path.join(D, "section_profile.json")))
prof = np.array(S["profile"], float)

HW_REF = 0.765          # half-width of the cabin, to turn millimetres into the section's normalised units
Z0, Z1, PULL = 0.62, 0.80, 0.016


def ramp(z):
    t = np.clip((z - Z0) / (Z1 - Z0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


out = prof.copy()
out[:, 1] = prof[:, 1] - ramp(prof[:, 0]) * PULL / HW_REF
for zq in (0.60, 0.70, 0.75, 0.79, 0.85):
    i = int(np.argmin(np.abs(prof[:, 0] - zq)))
    print("z %.2f  envelope %.4f -> body %.4f  (%.1f mm in at the cabin)"
          % (zq, prof[i, 1], out[i, 1], (prof[i, 1] - out[i, 1]) * HW_REF * 1000))
S2 = dict(S)
S2["profile"] = [[round(float(z), 4), round(float(p), 5)] for z, p in out]
S2["note"] = ("section_profile.json pulled in above z %.2f by up to %.0f mm, fitted to the measured door handle "
              "and side repeater; use for side skins (shell, wing)" % (Z0, PULL * 1000))
json.dump(S2, open(os.path.join(D, "section_body.json"), "w"), indent=1)
print("wrote section_body.json")
