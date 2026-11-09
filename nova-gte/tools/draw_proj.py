"""Draw export/match/proj_<cam>.json (model glass outlines) onto the matched photos -> export/match/projcheck_<cam>.jpg"""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH = {"c20": "user_red_gte/redgte_20.webp", "c22": "user_red_gte/redgte_22.webp", "cCF": "commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg",
      "cS": "other_sources/anglia_side.jpg", "cAR": "other_sources/anglia_rear.jpg"}
COL = {"GLASS_WINDSCREEN": (0, 255, 255), "DET_SUNROOF": (255, 0, 255), "GLASS_TAILGATE": (255, 255, 0)}
for cam in (sys.argv[1:] or PH):
    J = json.load(open(os.path.join(ROOT, "export", "match", "proj_%s.json" % cam)))
    im = Image.open(os.path.join(ROOT, "reference", "photos", PH[cam])).convert("RGB")
    sx, sy = im.width / J["W"], im.height / J["H"]
    d = ImageDraw.Draw(im)
    for name, lps in J["lines"].items():
        for lp in lps:
            if len(lp) > 1:
                d.line([(x * sx, y * sy) for x, y in lp] + [(lp[0][0] * sx, lp[0][1] * sy)], fill=COL.get(name, (0, 255, 0)), width=2)
    im.save(os.path.join(ROOT, "export", "match", "projcheck_%s.jpg" % cam), quality=88)
    print(cam, im.size)
