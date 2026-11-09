"""Line up the grey model views (export/match/grey_<view>.png) with Nik's grey reference views
(reference/photos/grey_studio/<view>.png): each scaled so the car's overall length (side) / width (front, rear) match,
bottoms (tyres on the ground) and centres aligned. Writes export/match/greycmp_<view>.jpg: reference | ours | overlay
(reference with our outline in red), upscaled for viewing.
Run: .venv\\Scripts\\python.exe tools\\compare_grey.py [side front rear]"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = 3


def on_white(im):
    im = im.convert("RGBA"); b = Image.new("RGBA", im.size, (255, 255, 255, 255)); b.alpha_composite(im)
    return b.convert("RGB")


def mask(im):
    a = np.asarray(im.convert("RGBA")).astype(int)
    return (a[..., 3] > 40) & (a[..., :3].min(-1) < 235)


def bbox(m):
    ys, xs = np.where(m)
    return xs.min(), xs.max(), ys.min(), ys.max()


def main(views):
    for v in views:
        ref = Image.open(os.path.join(ROOT, "reference", "photos", "grey_studio", v + ".png"))
        ours = Image.open(os.path.join(ROOT, "export", "match", "grey_%s.png" % v))
        rx0, rx1, ry0, ry1 = bbox(mask(ref))
        ox0, ox1, oy0, oy1 = bbox(mask(ours))
        if v == "side":
            s = (rx1 - rx0) / (ox1 - ox0)
        else:
            # front / rear: the mirrors are nearer / further from the camera than the body (perspective), so line
            # up on the body width at bumper height (30 % of the car's height up from the ground)
            def width_at(m, y0, y1):
                r = m[int(round(y1 - 0.30 * (y1 - y0)))]; xs = np.where(r)[0]; return xs.min(), xs.max()
            ra, rb = width_at(mask(ref), ry0, ry1); oa, ob = width_at(mask(ours), oy0, oy1)
            s = (rb - ra) / (ob - oa); rx0, rx1, ox0, ox1 = ra, rb, oa, ob
        sm = ours.resize((max(1, round(ours.width * s)), max(1, round(ours.height * s))), Image.LANCZOS)
        # place so the bottoms and horizontal centres line up
        dx = round((rx0 + rx1) / 2 - (ox0 + ox1) / 2 * s)
        dy = round(ry1 - oy1 * s)
        canvas = Image.new("RGBA", ref.size, (255, 255, 255, 0))
        canvas.alpha_composite(sm, (dx, dy)) if dx >= 0 and dy >= 0 else canvas.paste(sm, (dx, dy), sm)
        a = on_white(ref).resize((ref.width * UP, ref.height * UP), Image.LANCZOS)
        b = on_white(canvas).resize(a.size, Image.LANCZOS)
        m = mask(canvas)
        edge = m & ~binary_erosion(m, iterations=1)
        ov = np.asarray(on_white(ref)).copy(); ov[edge] = (255, 0, 0)
        c = Image.fromarray(ov).resize(a.size, Image.NEAREST)
        S = Image.new("RGB", (a.width * 3 + 16, a.height + 24), "white"); d = ImageDraw.Draw(S)
        for i, (im, t) in enumerate(((a, "REFERENCE"), (b, "OURS (grey model)"), (c, "OVERLAY: our outline in red"))):
            S.paste(im, (i * (a.width + 8), 24)); d.text((i * (a.width + 8) + 6, 6), t, fill=(0, 0, 0))
        p = os.path.join(ROOT, "export", "match", "greycmp_%s.jpg" % v)
        S.save(p, quality=90)
        print(v, "scale", round(s, 4), "ref bbox h", ry1 - ry0, "ours h", round((oy1 - oy0) * s, 1), p)


if __name__ == "__main__":
    main(sys.argv[1:] or ["side", "front", "rear"])
