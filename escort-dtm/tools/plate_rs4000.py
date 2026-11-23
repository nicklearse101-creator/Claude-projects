"""Rear plate "RS 1800" -> "RS 4000" in the same outlined font (PLATE_2.dds colour + PLATE_22.dds normal map).

"RS" is kept pixel for pixel; the "0" is the plate's own last "0" (its right half mirrored to a whole glyph); the
"4" is drawn with the same boundary-line weight and the same 20 px stroke as the plate's "1"; glyph outlines
overlap/cross like the original. The normal map is rebuilt from the new lettering with the gradient->normal
mapping fitted on the original pair, so the relief matches.

    python plate_rs4000.py <in_png_colour> <in_png_normal> <out_dir>
(PNG copies of the kn5's PLATE_2.dds / PLATE_22.dds; writes PLATE_2.dds / PLATE_22.dds (uncompressed RGBA) + PNGs.)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4                 # supersampling for the drawn "4"
LINE = 5.5             # outline width (px), measured on the plate


def load(p):
    return np.array(Image.open(p).convert("RGBA")).astype(np.float64)


def intensity(rgb, bg, fg):
    return np.clip((rgb[:, :, :3].mean(2) - bg) / (fg - bg), 0, 1)


def zero_ring(I):
    """Outline of the plate's last '0' (x 547-641 line centres): right half mirrored about its centre."""
    cx = 593.5                     # 2*cx integer: every column mirrors onto exactly one column
    h, w = I.shape
    ring = np.zeros_like(I)
    xs = np.arange(int(cx), 650)
    for x in xs:
        xm = int(round(2 * cx - x))
        ring[:, x] = np.maximum(ring[:, x], I[:, x])
        if 0 <= xm < w:
            ring[:, xm] = np.maximum(ring[:, xm], I[:, x])
    ring[:, :int(2 * cx - 650)] = 0
    ring[:, 650:] = 0
    return ring, cx


def four_ring(h, w, x0, y0):
    """'4' outline: boundary box 92 x 132.5 px, stems 20 px (as the plate's '1' / '0' walls)."""
    W, H = 92.0, 132.5
    outer = [(56, 0), (76, 0), (76, 88), (92, 88), (92, 108), (76, 108), (76, H), (56, H), (56, 108), (0, 108),
             (0, 88)]
    counter = [(56, 38), (56, 88), (24, 88)]
    img = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(img)
    for poly in (outer, counter):
        pts = [((x0 + x) * SS, (y0 + y) * SS) for x, y in poly]
        d.line(pts + [pts[0]], fill=255, width=int(LINE * SS), joint="curve")
    img = img.resize((w, h), Image.LANCZOS)
    return np.asarray(img, np.float64) / 255.0


def shift(a, dx):
    out = np.zeros_like(a)
    if dx >= 0:
        out[:, dx:] = a[:, :a.shape[1] - dx]
    else:
        out[:, :dx] = a[:, -dx:]
    return out


def grad(I):
    H = np.asarray(Image.fromarray((I * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6)), np.float64) / 255
    gx = np.zeros_like(H); gy = np.zeros_like(H)
    gx[:, 1:-1] = (H[:, 2:] - H[:, :-2]) / 2
    gy[1:-1, :] = (H[2:, :] - H[:-2, :]) / 2
    return gx, gy


def main(col_png, nrm_png, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    C = load(col_png); N = load(nrm_png)
    bg = C[5, 5, :3].mean(); fg = 241.0
    I = intensity(C, bg, fg)
    h, w = I.shape
    # layout: exactly the RS 1800 layout - "RS" untouched in place, "4000" fills the space "1800" used
    # (line-centre x 330 .. 640.25), digits overlapping/interlocking by the same amount each
    zr, cx = zero_ring(I)
    new = I.copy(); new[:, 318:] = 0
    w4, w0, x_l, x_r = 92.0, 93.5, 330.0, cx + 46.75
    ov = (w4 + 3 * w0 - (x_r - x_l)) / 3
    four_left = x_l
    z_lefts = [x_l + w4 - ov, x_l + w4 - ov + (w0 - ov), x_l + w4 - ov + 2 * (w0 - ov)]
    centre_dx = 0
    for zl in z_lefts:
        new = np.maximum(new, shift(zr, int(round(zl + 46.75 - cx))))
    print(f"digit overlap {ov:.1f} px")
    y0 = 28.75
    new = np.maximum(new, four_ring(h, w, four_left + centre_dx, y0))
    # colour: background + white lines, alpha as the original
    rgb = np.empty((h, w, 4))
    for k in range(3):
        rgb[:, :, k] = C[5, 5, k] + new * (fg - C[5, 5, k])
    rgb[:, :, 3] = C[:, :, 3]
    # normal map: fit original N(R,G) ~ 128 + a*gx, 128 + b*gy on the original lettering, apply to the new one
    gx0, gy0 = grad(I)
    m = (np.abs(gx0) + np.abs(gy0)) > 0.01
    a = np.linalg.lstsq(gx0[m][:, None], N[:, :, 0][m] - 128, rcond=None)[0][0]
    b = np.linalg.lstsq(gy0[m][:, None], N[:, :, 1][m] - 128, rcond=None)[0][0]
    gx, gy = grad(new)
    nr = np.clip(128 + a * gx, 0, 255); ng = np.clip(128 + b * gy, 0, 255)
    x = (nr - 128) / 127; y = (ng - 128) / 127
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    nrm = np.empty((h, w, 4)); nrm[:, :, 0] = nr; nrm[:, :, 1] = ng; nrm[:, :, 2] = 128 + z * 127; nrm[:, :, 3] = N[:, :, 3]
    flat = N[5, 5]
    print(f"fit a={a:.1f} b={b:.1f}; original flat texel {flat}")
    for arr, name in ((rgb, "PLATE_2"), (nrm, "PLATE_22")):
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        im.save(out / f"{name}.png")
        im.save(out / f"{name}.dds")
    print("written", out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
