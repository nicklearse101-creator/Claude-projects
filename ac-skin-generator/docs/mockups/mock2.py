"""Mix: B's colours + C's floor + ghosted 296 GT3 (drawn from the car's own model). Throwaway."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import mock
from mock import P, hexc

HERE = os.path.dirname(os.path.abspath(__file__))


def ghost_image(view, colour, width_px):
    g = np.asarray(Image.open(os.path.join(HERE, f'ghost_{view}.png')).convert('L'), np.float32)
    mask = (g > 2).astype(np.float32)
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1])); gy = np.abs(np.diff(g, axis=0, prepend=g[:1]))
    edge = np.clip((gx + gy) / 22.0, 0, 1)
    edge = np.asarray(Image.fromarray((edge * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
    shade = (g - 100) / 100 * mask
    a = np.clip(mask * (0.05 + 0.10 * shade) + edge * 0.55, 0, 1)
    rgb = np.empty(g.shape + (3,), np.float32)
    c = np.array(colour[:3], np.float32)
    rgb[:] = c * 0.65 + 255 * 0.35 * edge[..., None]
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA')
    h = int(im.height * width_px / im.width)
    im = im.resize((width_px, h), Image.LANCZOS)
    # fade the lower part into the floor
    arr = np.asarray(im).copy()
    fade = np.clip(np.linspace(1.25, 0.0, h), 0, 1) ** 0.9
    arr[..., 3] = (arr[..., 3] * fade[:, None]).astype(np.uint8)
    glow = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(P(5)))
    out = Image.alpha_composite(glow, Image.fromarray(arr))
    return out


def preview_bg_mix(img, th, x0, y0, x1, y1, floor_y):
    X0, Y0, X1, Y1, FY = P(x0), P(y0), P(x1), P(y1), P(floor_y)
    w, h = X1 - X0, Y1 - Y0
    fy = FY - Y0
    # B: carbon weave + vignette + orange spotlight
    t = P(7)
    tile = Image.new('RGB', (2 * t, 2 * t)); td = ImageDraw.Draw(tile)
    for i in range(t):
        c1 = 22 + int(14 * i / t); c2 = 30 - int(12 * i / t)
        td.line([(0, i), (t - 1, i)], fill=(c1,) * 3); td.line([(t + i, t), (t + i, 2 * t - 1)], fill=(c1,) * 3)
        td.line([(t + i, 0), (t + i, t - 1)], fill=(c2,) * 3); td.line([(0, t + i), (t - 1, t + i)], fill=(c2,) * 3)
    tex = Image.new('RGB', (w, h))
    for yy in range(0, h, 2 * t):
        for xx in range(0, w, 2 * t):
            tex.paste(tile, (xx, yy))
    lay = tex.convert('RGBA')
    vig = Image.new('RGBA', (w, h), (0, 0, 0, 0)); vd = ImageDraw.Draw(vig)
    vd.rectangle([0, 0, w, h], fill=(0, 0, 0, 160)); vd.ellipse([w * 0.05, -h * 0.2, w * 0.95, h * 1.0], fill=(0, 0, 0, 0))
    lay.alpha_composite(vig.filter(ImageFilter.GaussianBlur(P(60))))
    sp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sp).polygon([(w * 0.42, 0), (w * 0.58, 0), (w * 0.95, fy + P(30)), (w * 0.05, fy + P(30))], fill=hexc(th['acc'], 22))
    lay.alpha_composite(sp.filter(ImageFilter.GaussianBlur(P(26))))
    # the ghosted 296 GT3, big, behind everything
    gw, gh_ = Image.open(os.path.join(HERE, 'ghost_front.png')).size
    gh = ghost_image('front', hexc(th['acc']), int(min(w * 0.98, (fy - P(20)) * 1.05 * gw / gh_)))
    lay.alpha_composite(gh, ((w - gh.width) // 2, P(14)))
    # C: floor - dark, halftone dots, hazard stripes, floor line, spotlight
    fl = Image.new('RGBA', (w, h), (0, 0, 0, 0)); fd = ImageDraw.Draw(fl)
    fd.rectangle([0, fy, w, h], fill=(8, 8, 8, 215))
    step = P(13)
    for yy in range(fy + step // 2, h, step):
        for xx in range(0, w, step):
            r = ((yy - fy) / (h - fy)) ** 1.3 * step * 0.40
            if r > 0.6:
                fd.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(40, 40, 40, 255))
    band = P(22)
    for i in range(-30, 40):
        x = i * band * 2
        fd.polygon([(x, h), (x + band, h), (x + band + P(40), h - P(40)), (x + P(40), h - P(40))], fill=hexc(th['acc']))
    lay.alpha_composite(fl)
    gl = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([w * 0.12, fy - P(16), w * 0.88, fy + P(30)], fill=hexc(th['acc'], 120))
    lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(P(24))))
    ImageDraw.Draw(lay).line([(0, fy), (w, fy)], fill=hexc(th['acc'], 220), width=P(2))
    img.alpha_composite(lay, (X0, Y0))


if __name__ == '__main__':
  mock.preview_bg = preview_bg_mix
  th = dict(mock.THEMES['B_carbon_orange'])
  th['name'] = 'CARBON + STREET FLOOR'
  mock.render(th, 'D_carbon_street_296.jpg')
