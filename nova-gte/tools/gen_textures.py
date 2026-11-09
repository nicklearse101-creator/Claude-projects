"""Paint + txMaps textures for the generated body (run with the project .venv after prep_generated.py).

The generator's texture is the red photo car with its lighting baked in. The paint (red hue) is replaced by gun-metal
grey times a high-pass of its own brightness, so shut lines, badges and edges stay while the baked sky reflections
flatten out. Tail-lamp texels (UV triangles from protect_uv.json) keep their red. txMaps (R specular, G gloss,
B reflection) is full on the paint, low elsewhere. Writes DDS (uncompressed BGRA with mipmaps) + PNG previews.
usage: python tools/gen_textures.py [src.png] [tex_dir]   (tex_dir default export/gen/tex; holds protect_uv.json)
"""
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "export", "gen", "tex")
GUNMETAL = np.array([0.30, 0.31, 0.33])          # sRGB diffuse; AC's paint preset adds the reflections


def dds_rgba(img):
    """Uncompressed 32-bit BGRA DDS with a full box-filtered mip chain. img: HxWx4 uint8."""
    h, w = img.shape[:2]
    mips = [img]
    while mips[-1].shape[0] > 1 and mips[-1].shape[1] > 1:
        a = mips[-1].astype(np.float32)
        a = (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4
        mips.append(np.clip(a + 0.5, 0, 255).astype(np.uint8))
    flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000              # caps height width pitch pixelformat mipmapcount
    head = struct.pack("<4s7I44s", b"DDS ", 124, flags, h, w, w * 4, 0, len(mips), b"\0" * 44)
    pf = struct.pack("<8I", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps = struct.pack("<5I", 0x1000 | 0x8 | 0x400000, 0, 0, 0, 0)   # texture | complex | mipmap
    body = b"".join(m[..., [2, 1, 0, 3]].tobytes() for m in mips)
    return head + pf + caps + body


def main():
    global TEX
    if len(sys.argv) > 2:
        TEX = sys.argv[2]
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TEX, "Image_0.png")
    im = Image.open(src).convert("RGB")
    W, H = im.size
    a = np.asarray(im).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    # red hue within ~17 deg either side of 0 (pinks included, the amber indicators not)
    hsv_h = np.asarray(im.convert("HSV"))[..., 0].astype(np.int32)
    hue_red = (hsv_h < 12) | (hsv_h > 243)
    paint = hue_red & ((sat > 0.18) | ((sat > 0.05) & (mx > 0.55))) & (mx > 0.07)    # + the washed-out pink roof
    pm = Image.fromarray((paint * 255).astype(np.uint8))                                # close pin-holes
    paint = np.asarray(pm.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))) > 127
    # protect the tail lamps
    prot = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(prot)
    for poly in json.load(open(os.path.join(TEX, "protect_uv.json")))["protect"]:
        d.polygon([(u * W, (1 - v) * H) for u, v in poly], fill=255)
    prot = np.asarray(prot.filter(ImageFilter.MaxFilter(5))) > 0
    m = (paint & ~prot).astype(np.float32)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
    # high-pass brightness inside the paint: L / blur(L) with a mask-normalised blur
    L = 0.299 * r + 0.587 * g + 0.114 * b
    blur = lambda x, rad: gaussian_filter(x.astype(np.float32), rad)
    Lb = blur(L * m, 18) / np.maximum(blur(m, 18), 1e-3)
    detail = np.clip(1.0 + 0.85 * (L / np.maximum(Lb, 1e-3) - 1.0), 0.45, 1.20)
    col = GUNMETAL[None, None, :] * detail[..., None]
    out = col * m[..., None] + a * (1 - m[..., None])
    rgba = np.concatenate([np.clip(out * 255 + 0.5, 0, 255), np.full((H, W, 1), 255)], -1).astype(np.uint8)
    maps = np.stack([0.25 + 0.75 * m, 0.20 + 0.80 * m, 0.05 + 0.95 * m, np.ones_like(m)], -1)
    maps = np.clip(maps * 255 + 0.5, 0, 255).astype(np.uint8)
    for name, arr in (("gen_body_col", rgba), ("gen_body_maps", maps)):
        open(os.path.join(TEX, name + ".dds"), "wb").write(dds_rgba(arr))
        Image.fromarray(arr[..., :3]).save(os.path.join(TEX, name + ".png"))
    print("paint texels %.1f%%, protected %.2f%%" % (100 * m.mean(), 100 * prot.mean()))


if __name__ == "__main__":
    main()
