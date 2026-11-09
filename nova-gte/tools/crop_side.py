"""Close crop of the side picture vs our grey side view at the same scale: tools/crop_side.py X0 X1 Y0 Y1 out.jpg
(picture pixel box; picture above, ours below, 5x)."""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def on_white(im):
    im = im.convert("RGBA"); b = Image.new("RGBA", im.size, (255, 255, 255, 255)); b.alpha_composite(im); return b.convert("RGB")


def bbox(im):
    a = np.asarray(im.convert("RGBA")).astype(int); m = (a[..., 3] > 40) & (a[..., :3].min(-1) < 235)
    ys, xs = np.where(m); return xs.min(), xs.max(), ys.min(), ys.max()


def crop_cam(x0, x1, y0, y1, out, K=5):
    """Same, using the render through the picture's solved camera (export/match/grey_pic_side.png, 4x the picture)."""
    ref = on_white(Image.open(os.path.join(ROOT, "reference", "photos", "grey_studio", "side.png")))
    ours = on_white(Image.open(os.path.join(ROOT, "export", "match", "grey_pic_side.png")))
    R = ref.resize((ref.width * K, ref.height * K), Image.LANCZOS); O = ours.resize(R.size, Image.LANCZOS)
    box = (x0 * K, y0 * K, x1 * K, y1 * K)
    r, o = R.crop(box), O.crop(box)
    S = Image.new("RGB", (r.width, r.height * 2 + 8), "white"); S.paste(r, (0, 0)); S.paste(o, (0, r.height + 8))
    S.save(out, quality=92)


def crop(x0, x1, y0, y1, out, K=5):
    ref = Image.open(os.path.join(ROOT, "reference", "photos", "grey_studio", "side.png"))
    ours = Image.open(os.path.join(ROOT, "export", "match", "grey_side.png"))
    rx0, rx1, ry0, ry1 = bbox(ref); ox0, ox1, oy0, oy1 = bbox(ours)
    s = (rx1 - rx0) / (ox1 - ox0) * K                  # length -> length
    t = (ry1 - ry0) / (oy1 - oy0) * K                  # ground..roof -> ground..roof (the picture is ~2.5 % tall)
    big = ours.resize((round(ours.width * s), round(ours.height * t)), Image.LANCZOS)
    dx = round((rx0 + rx1) / 2 * K - (ox0 + ox1) / 2 * s); dy = round(ry1 * K - oy1 * t)
    canvas = Image.new("RGBA", (ref.width * K, ref.height * K), (255, 255, 255, 0)); canvas.paste(big, (dx, dy), big)
    O = on_white(canvas); R = on_white(ref).resize(O.size, Image.LANCZOS)
    box = (x0 * K, y0 * K, x1 * K, y1 * K)
    r, o = R.crop(box), O.crop(box)
    S = Image.new("RGB", (r.width, r.height * 2 + 8), "white"); S.paste(r, (0, 0)); S.paste(o, (0, r.height + 8))
    S.save(out, quality=92)


if __name__ == "__main__":
    a = sys.argv[1:]
    crop_cam(int(a[0]), int(a[1]), int(a[2]), int(a[3]), a[4])
