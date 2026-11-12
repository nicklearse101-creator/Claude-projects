"""Mockups of the Ratty's4Skin Generator reskin (same layout, game look). Throwaway."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

APP = r'D:\Claude\Claude-\ac-skin-generator'
OUT = os.path.dirname(os.path.abspath(__file__))
S = 1.4                      # render scale
W, H = 1500, 950             # base canvas (same proportions as the current window shot)


def P(v):
    return int(round(v * S))


def hexc(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


_fc = {}


def bahn(size, style='Bold Condensed'):
    k = ('b', size, style)
    if k not in _fc:
        f = ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf', P(size))
        f.set_variation_by_name(style)
        _fc[k] = f
    return _fc[k]


def segoe(size, bold=False):
    k = ('s', size, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype('C:/Windows/Fonts/' + ('segoeuib.ttf' if bold else 'segoeui.ttf'), P(size))
    return _fc[k]


def mono(size):
    k = ('m', size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', P(size))
    return _fc[k]


def text(img, x, y, s, font, fill, anchor='lm', italic=0.0, glow=None, spacing=0):
    """Text at base coords; italic = shear (0.2 looks like NFS); glow = colour for a soft halo."""
    if spacing:
        s = (' ' * 0).join(s)
    l, t, r, b = font.getbbox(s)
    w, h = r - l + P(4), b - t + P(4)
    pad = P(14) if glow else P(2)
    k = italic
    lay = Image.new('RGBA', (int(w + k * h) + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((pad - l + int(k * h), pad - t), s, font=font, fill=fill)
    if k:
        Hh = lay.size[1]
        lay = lay.transform(lay.size, Image.AFFINE, (1, k, -k * Hh, 0, 1, 0), Image.BICUBIC)
    if glow:
        g = Image.new('RGBA', lay.size, (0, 0, 0, 0))
        a = lay.split()[3]
        g.paste(Image.new('RGBA', lay.size, glow), (0, 0), a)
        g = g.filter(ImageFilter.GaussianBlur(P(6)))
        lay = Image.alpha_composite(g, Image.alpha_composite(g, lay))
    X, Y = P(x), P(y)
    tw, th = lay.size
    if anchor[0] == 'm':
        X -= tw // 2
    elif anchor[0] == 'r':
        X -= tw - pad
    else:
        X -= pad
    if anchor[1] == 'm':
        Y -= th // 2
    elif anchor[1] == 't':
        Y -= pad
    img.alpha_composite(lay, (X, Y))
    return (r - l) / S


def tw(s, font):
    l, t, r, b = font.getbbox(s)
    return (r - l) / S


def glow_shape(img, draw_fn, colour, radius=8):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(lay))
    lay = lay.filter(ImageFilter.GaussianBlur(P(radius)))
    img.alpha_composite(lay)


def para(x, y, w, h, k):
    """Parallelogram leaning right (NFS button shape), base coords."""
    return [(P(x + k), P(y)), (P(x + w), P(y)), (P(x + w - k), P(y + h)), (P(x), P(y + h))]


def button(img, x, y, w, h, label, th, kind='outline', size=15, k=8):
    d = ImageDraw.Draw(img)
    poly = para(x, y, w, h, k)
    if kind == 'primary':
        glow_shape(img, lambda dd: dd.polygon(poly, fill=hexc(th['acc'], 150)), None, 9)
        d.polygon(poly, fill=hexc(th['acc']))
        fg = th['on_acc']
    elif kind == 'secondary':
        d.polygon(poly, fill=hexc(th['panel2']), outline=hexc(th['acc2']), width=P(1.6))
        fg = th['acc2']
    else:
        d.polygon(poly, fill=hexc(th['panel2']), outline=hexc(th['line']), width=P(1.2))
        fg = th['text']
    text(img, x + w / 2, y + h / 2, label.upper(), bahn(size, 'SemiBold Condensed' if kind == 'outline' else 'Bold Condensed'),
         hexc(fg), anchor='mm', italic=0.12)


def checkbox(img, x, y, label, th, on=False, font=None):
    d = ImageDraw.Draw(img)
    d.rectangle([P(x), P(y - 8), P(x + 16), P(y + 8)], outline=hexc(th['acc'] if on else th['muted']), width=P(1.5),
                fill=hexc(th['panel2']))
    if on:
        d.line([(P(x + 3.5), P(y)), (P(x + 7), P(y + 4)), (P(x + 13), P(y - 5))], fill=hexc(th['acc']), width=P(2.4))
    text(img, x + 24, y, label, font or segoe(12.5), hexc(th['text']))


def combo(img, x, y, w, value, th):
    d = ImageDraw.Draw(img)
    d.rectangle([P(x), P(y), P(x + w), P(y + 30)], fill=hexc(th['field']), outline=hexc(th['line']), width=P(1))
    d.line([(P(x), P(y + 30)), (P(x + w), P(y + 30))], fill=hexc(th['acc']), width=P(2))
    text(img, x + 10, y + 15, value, segoe(12.5), hexc(th['text']))
    cx, cy = x + w - 16, y + 15
    d.polygon([(P(cx - 6), P(cy - 3)), (P(cx + 6), P(cy - 3)), (P(cx), P(cy + 4))], fill=hexc(th['acc']))


def logo_thumb(name, size):
    p = os.path.join(APP, 'starter_logos', name)
    im = Image.open(p).convert('RGBA')
    im.thumbnail((P(size), P(size)), Image.LANCZOS)
    bg = Image.new('RGBA', (P(size), P(size)), (255, 255, 255, 0))
    bg.alpha_composite(im, ((P(size) - im.width) // 2, (P(size) - im.height) // 2))
    return bg


def car_cutout():
    im = np.asarray(Image.open(os.path.join(APP, 'talbot_v150_preview.png')).convert('RGB')).astype(np.float32)
    bg = np.array([235, 236, 240], np.float32)
    dist = np.sqrt(((im - bg) ** 2).sum(-1))
    a = np.clip((dist - 8) / 26, 0, 1)
    rgb = np.where(a[..., None] > 0.02, (im - bg * (1 - a[..., None])) / np.maximum(a[..., None], 0.02), 0)
    out = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


CAR = car_cutout()


def preview_bg(img, th, x0, y0, x1, y1, floor_y):
    """Themed 'garage' behind the car (base coords)."""
    X0, Y0, X1, Y1, FY = P(x0), P(y0), P(x1), P(y1), P(floor_y)
    w, h = X1 - X0, Y1 - Y0
    lay = Image.new('RGBA', (w, h), hexc(th['bg']))
    d = ImageDraw.Draw(lay)
    yy = np.linspace(0, 1, h)[:, None]
    style = th['preview']
    if style == 'neon':
        top, bot = np.array(hexc('#140f33')[:3]), np.array(hexc('#04050b')[:3])
        grad = (top * (1 - yy) + bot * yy)
        arr = np.repeat(grad[:, None, :], w, 1).astype(np.uint8)
        lay = Image.fromarray(np.dstack([arr, np.full((h, w), 255, np.uint8)]), 'RGBA')
        d = ImageDraw.Draw(lay)
        fy = FY - Y0
        grid = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        g = ImageDraw.Draw(grid)
        vx = w // 2
        for i in range(-14, 15):
            g.line([(vx, fy), (vx + i * P(95), h + P(200))], fill=hexc(th['acc'], 110), width=P(1.2))
        yv = 1.0
        while True:
            yline = fy + (h - fy) * (yv ** 2.2)
            g.line([(0, yline), (w, yline)], fill=hexc(th['acc'], 110), width=P(1.2))
            yv *= 0.80
            if yv < 0.04:
                break
        mask = np.zeros((h, w), np.float32)
        mask[fy:] = np.linspace(0.0, 1.0, h - fy)[:, None] ** 0.8
        grid.putalpha(Image.fromarray((np.asarray(grid.split()[3], np.float32) * mask).astype(np.uint8)))
        lay.alpha_composite(grid)
        gl = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(gl).ellipse([w * 0.12, fy - P(170), w * 0.88, fy + P(40)], fill=hexc(th['acc'], 60))
        ImageDraw.Draw(gl).ellipse([w * 0.18, fy - P(14), w * 0.82, fy + P(26)], fill=hexc(th['acc2'], 120))
        lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(P(30))))
        ImageDraw.Draw(lay).line([(0, fy), (w, fy)], fill=hexc(th['acc2'], 90), width=P(1))
    elif style == 'carbon':
        t = P(7)
        tile = Image.new('RGB', (2 * t, 2 * t))
        td = ImageDraw.Draw(tile)
        for i in range(t):
            c1 = 22 + int(14 * i / t)
            c2 = 30 - int(12 * i / t)
            td.line([(0, i), (t - 1, i)], fill=(c1, c1, c1))
            td.line([(t + i, t), (t + i, 2 * t - 1)], fill=(c1, c1, c1))
            td.line([(t + i, 0), (t + i, t - 1)], fill=(c2, c2, c2))
            td.line([(0, t + i), (t - 1, t + i)], fill=(c2, c2, c2))
        tex = Image.new('RGB', (w, h))
        for yy_ in range(0, h, 2 * t):
            for xx in range(0, w, 2 * t):
                tex.paste(tile, (xx, yy_))
        lay = tex.convert('RGBA')
        vig = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vig)
        vd.rectangle([0, 0, w, h], fill=(0, 0, 0, 150))
        vd.ellipse([w * 0.05, -h * 0.2, w * 0.95, h * 1.0], fill=(0, 0, 0, 0))
        lay.alpha_composite(vig.filter(ImageFilter.GaussianBlur(P(60))))
        fy = FY - Y0
        sp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sp)
        sd.polygon([(w * 0.42, 0), (w * 0.58, 0), (w * 0.95, fy + P(30)), (w * 0.05, fy + P(30))], fill=hexc(th['acc'], 28))
        sd.ellipse([w * 0.08, fy - P(18), w * 0.92, fy + P(34)], fill=hexc(th['acc'], 110))
        lay.alpha_composite(sp.filter(ImageFilter.GaussianBlur(P(26))))
        fl = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(fl).rectangle([0, fy, w, h], fill=(0, 0, 0, 120))
        lay.alpha_composite(fl)
        ImageDraw.Draw(lay).line([(0, fy), (w, fy)], fill=hexc(th['acc'], 120), width=P(1.5))
    else:  # street
        lay = Image.new('RGBA', (w, h), hexc('#0c0c0c'))
        d = ImageDraw.Draw(lay)
        step = P(14)
        for yy_ in range(0, h, step):
            for xx in range(0, w, step):
                r = (xx / w) ** 1.6 * step * 0.42
                if r > 0.6:
                    d.ellipse([xx - r, yy_ - r, xx + r, yy_ + r], fill=(34, 34, 34, 255))
        fy = FY - Y0
        big = bahn(150, 'Bold Condensed')
        tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        text(tmp, 0, 0, '', big, (0, 0, 0, 0))
        hz = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hz)
        band = P(22)
        for i in range(-30, 30):
            x = i * band * 2
            hd.polygon([(x, h), (x + band, h), (x + band + P(40), h - P(40)), (x + P(40), h - P(40))], fill=hexc(th['acc'], 255))
        lay.alpha_composite(hz)
        sp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sp).ellipse([w * 0.12, fy - P(16), w * 0.88, fy + P(30)], fill=(255, 255, 255, 70))
        lay.alpha_composite(sp.filter(ImageFilter.GaussianBlur(P(24))))
        ImageDraw.Draw(lay).line([(0, fy), (w, fy)], fill=hexc(th['acc'], 200), width=P(2))
    img.alpha_composite(lay, (X0, Y0))


def place_car(img, x, y, width, floor_y):
    car = CAR.copy()
    sc = P(width) / car.width
    car = car.resize((P(width), int(car.height * sc)), Image.LANCZOS)
    X, Y = P(x), P(floor_y) - car.height + P(6)
    ref = car.transpose(Image.FLIP_TOP_BOTTOM)
    m = np.asarray(ref.split()[3], np.float32)
    fade = np.linspace(0.28, 0.0, ref.height)[:, None] ** 1.0
    ref.putalpha(Image.fromarray((m * fade).astype(np.uint8)))
    img.alpha_composite(ref, (X, Y + car.height - P(4)))
    img.alpha_composite(car, (X, Y))
    return X, Y, sc


def dashed_rect(d, box, colour, dash=P(7), width=P(1.6)):
    x0, y0, x1, y1 = box
    for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        L = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        n = int(L // dash)
        for i in range(0, n, 2):
            t0, t1 = i / n, min((i + 1) / n, 1)
            d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                    (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=colour, width=width)
    for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        d.rectangle([cx - P(4), cy - P(4), cx + P(4), cy + P(4)], fill=colour)


def render(th, fname):
    img = Image.new('RGBA', (P(W), P(H)), hexc(th['bg']))
    d = ImageDraw.Draw(img)

    # ---- header strip (brand) ----
    d.rectangle([0, 0, P(W), P(54)], fill=hexc(th['panel']))
    glow_shape(img, lambda dd: dd.line([(0, P(54)), (P(W), P(54))], fill=hexc(th['acc'], 255), width=P(3)), None, 5)
    d.line([(0, P(54)), (P(W * 0.6), P(54))], fill=hexc(th['acc']), width=P(2.5))
    d.line([(P(W * 0.6), P(54)), (P(W), P(54))], fill=hexc(th['acc2']), width=P(2.5))
    x = 20
    x += text(img, x, 28, "RATTY'S", bahn(30), hexc(th['text']), italic=0.22) + 6
    x += text(img, x, 28, '4SKIN', bahn(30), hexc(th['acc']), italic=0.22, glow=hexc(th['acc'], 170)) + 14
    text(img, x, 33, 'GENERATOR', bahn(14, 'SemiBold Condensed'), hexc(th['muted']), italic=0.15)
    text(img, W - 20, 22, 'TALBOT SUNBEAM LOTUS', bahn(15, 'Bold Condensed'), hexc(th['text']), anchor='rm', italic=0.12)
    text(img, W - 20, 40, 'SKIN  RATTY_101   ·   v1.8.0', bahn(11.5, 'SemiBold Condensed'), hexc(th['muted']), anchor='rm', italic=0.1)

    # ---- tabs ----
    tabs = ['CAR', 'LIVERY', 'NUMBER & NAMES', 'LOGOS', 'WINDOWS', 'LIGHTS & WHEELS']
    x, y, h = 16, 68, 32
    f = bahn(14.5, 'Bold Condensed')
    for t in tabs:
        w = tw(t, f) + 26
        poly = para(x, y, w, h, 9)
        if t == 'LOGOS':
            glow_shape(img, lambda dd, p=poly: dd.polygon(p, fill=hexc(th['acc'], 170)), None, 8)
            d.polygon(poly, fill=hexc(th['acc']))
            text(img, x + w / 2, y + h / 2, t, f, hexc(th['on_acc']), anchor='mm', italic=0.16)
        else:
            d.polygon(poly, fill=hexc(th['panel2']), outline=hexc(th['line']), width=P(1))
            text(img, x + w / 2, y + h / 2, t, f, hexc(th['muted']), anchor='mm', italic=0.16)
        x += w - 2

    # ---- left content panel ----
    L0, L1, T0 = 16, 566, 108
    d.rectangle([P(L0), P(T0), P(L1), P(716)], fill=hexc(th['panel']))
    d.line([(P(L0), P(T0)), (P(L1), P(T0))], fill=hexc(th['acc']), width=P(2))
    text(img, L0 + 14, T0 + 20, 'LOGO LIBRARY', bahn(17, 'Bold Condensed'), hexc(th['text']), italic=0.18)
    text(img, L0 + 14, T0 + 42, 'Your logos stay in the library for next time. Pick each one\'s place on the car.',
         segoe(11.5), hexc(th['muted']))
    text(img, L0 + 14, T0 + 59, 'PNGs with transparency work best; a plain background is removed.',
         segoe(11.5), hexc(th['muted']))
    # table
    ty = T0 + 76
    cols = [(L0 + 14, 'LOGO'), (L0 + 230, 'PLACE ON CAR'), (L0 + 370, 'BACKGROUND'), (L0 + 480, 'TINT')]
    for cx, c in cols:
        text(img, cx, ty + 10, c, bahn(12, 'SemiBold Condensed'), hexc(th['acc2']), italic=0.1)
    d.line([(P(L0 + 10), P(ty + 22)), (P(L1 - 10), P(ty + 22))], fill=hexc(th['line']), width=P(1))
    rows = [('ratty_racing_logo.jpg', 'Ratty Racing', 'Bonnet', 'Auto', 'yes'),
            ('Black_Sabbath_logo.svg_2.png', 'Black_Sabbath_logo.svg', 'Bonnet', 'Auto', ''),
            ('chucknorris_2.jpeg', 'chucknorris', 'Doors (big)', 'Auto', ''),
            ('24h.png', '24h', 'Not used', 'Auto', ''),
            ('africa twin honda.png', 'africa twin honda', 'Not used', 'Auto', ''),
            ('agip1.png', 'agip1', 'Not used', 'Auto', ''),
            ('AGV_04.png', 'AGV_04', 'Not used', 'Auto', '')]
    ry = ty + 26
    for i, (fn, name, place, bg, tint) in enumerate(rows):
        rh = 34
        sel = name == 'chucknorris'
        if sel:
            band = Image.new('RGBA', (P(L1 - L0 - 20), P(rh)), (0, 0, 0, 0))
            arr = np.zeros((P(rh), P(L1 - L0 - 20), 4), np.uint8)
            arr[..., :3] = hexc(th['acc'])[:3]
            arr[..., 3] = (np.linspace(120, 10, arr.shape[1])[None, :]).astype(np.uint8)
            img.alpha_composite(Image.fromarray(arr, 'RGBA'), (P(L0 + 10), P(ry)))
            d.rectangle([P(L0 + 10), P(ry), P(L0 + 14), P(ry + rh)], fill=hexc(th['acc']))
        elif i % 2:
            d.rectangle([P(L0 + 10), P(ry), P(L1 - 10), P(ry + rh)], fill=hexc(th['panel2']))
        img.alpha_composite(logo_thumb(fn, 28), (P(L0 + 20), P(ry + 3)))
        used = place != 'Not used'
        fc = hexc(th['text']) if used else hexc(th['muted'])
        text(img, L0 + 60, ry + rh / 2, name, segoe(12.5, bold=sel), fc)
        text(img, cols[1][0], ry + rh / 2, place, segoe(12.5, bold=sel), hexc(th['acc']) if used else fc)
        text(img, cols[2][0], ry + rh / 2, bg, segoe(12.5), fc)
        if tint:
            text(img, cols[3][0], ry + rh / 2, tint.upper(), bahn(12, 'Bold Condensed'), hexc(th['acc2']))
        ry += rh
    ry += 10
    button(img, L0 + 12, ry, 128, 30, 'Add logos…', th, 'primary', 14)
    button(img, L0 + 148, ry, 96, 30, 'Remove', th, 'outline', 14)
    button(img, L0 + 252, ry, 160, 30, 'Clear all (not used)', th, 'outline', 14)
    ry += 48
    checkbox(img, L0 + 14, ry, 'Keep logos off areas the car mirrors (no backwards copies)', th, False, segoe(12))
    ry += 30
    text(img, L0 + 14, ry + 15, 'PLACE ON CAR', bahn(13, 'SemiBold Condensed'), hexc(th['muted']), italic=0.1)
    combo(img, L0 + 130, ry, 170, 'Doors (big)', th)
    checkbox(img, L0 + 318, ry + 15, 'Tint glow to highlight colour', th, False, segoe(12))
    ry += 38
    text(img, L0 + 14, ry + 15, 'BACKGROUND', bahn(13, 'SemiBold Condensed'), hexc(th['muted']), italic=0.1)
    combo(img, L0 + 130, ry, 170, 'Auto', th)
    ry += 46
    text(img, L0 + 14, ry, 'ON THE CAR', bahn(15, 'Bold Condensed'), hexc(th['text']), italic=0.18)
    d.line([(P(L0 + 14), P(ry + 11)), (P(L0 + 90), P(ry + 11))], fill=hexc(th['acc']), width=P(2))
    ry += 18
    for name, place in (('chucknorris', 'Doors (big)'), ('Ratty Racing', 'Bonnet'), ('Black_Sabbath_logo.svg', 'Bonnet')):
        text(img, L0 + 22, ry + 12, name, segoe(12), hexc(th['text']))
        text(img, L0 + 250, ry + 12, place, segoe(12), hexc(th['acc']))
        d.line([(P(L0 + 14), P(ry + 25)), (P(L1 - 14), P(ry + 25))], fill=hexc(th['line']), width=P(1))
        ry += 26

    # ---- action buttons, progress, log ----
    button(img, 16, 728, 190, 44, 'Preview', th, 'secondary', 19, k=12)
    button(img, 216, 728, 350, 44, 'Create skin in car', th, 'primary', 21, k=12)
    py = 784
    d.rectangle([P(16), P(py), P(566), P(py + 6)], fill=hexc(th['panel2']))
    glow_shape(img, lambda dd: dd.rectangle([P(16), P(py), P(16 + 550 * 0.66), P(py + 6)], fill=hexc(th['acc'], 255)), None, 5)
    d.rectangle([P(16), P(py), P(16 + 550 * 0.66), P(py + 6)], fill=hexc(th['acc']))
    text(img, 16, py + 18, 'STAGE 4 / 6  ·  LOGOS', bahn(11.5, 'SemiBold Condensed'), hexc(th['muted']), italic=0.1)
    text(img, 566, py + 18, '66%', bahn(12, 'Bold Condensed'), hexc(th['acc']), anchor='rm', italic=0.1)
    d.rectangle([P(16), P(812), P(566), P(936)], fill=hexc(th['field']), outline=hexc(th['line']), width=P(1))
    lines = [('talbot_sunbeam_lotus  ·  skin ratty_101  ·  4K, compressed', th['muted']),
             ('Pattern: hexagon fade, base #00e000, accent #1010e0', th['muted']),
             ('Number 101 on doors (board)', th['muted']),
             ('Logos: chucknorris -> doors, Ratty Racing + Black Sabbath -> bonnet', th['muted']),
             ('PREVIEW ONLY - the skin in the car has NOT changed.', th['acc'])]
    ly = 826
    for s, c in lines:
        text(img, 26, ly, s, mono(10.5), hexc(c))
        ly += 18

    # ---- right side: view chips, edit row ----
    R0, R1 = 586, 1484
    text(img, R0, 84, 'VIEW', bahn(13, 'Bold Condensed'), hexc(th['muted']), italic=0.15)
    x = R0 + 46
    for v in ('ALL SIDES', 'LEFT', 'RIGHT', 'FRONT', 'REAR', 'TOP'):
        fw = tw(v, bahn(13.5, 'Bold Condensed')) + 24
        poly = para(x, 69, fw, 30, 8)
        if v == 'LEFT':
            d.polygon(poly, fill=hexc(th['acc2']))
            text(img, x + fw / 2, 84, v, bahn(13.5, 'Bold Condensed'), hexc(th['on_acc2']), anchor='mm', italic=0.14)
        else:
            d.polygon(poly, fill=hexc(th['panel2']), outline=hexc(th['line']), width=P(1))
            text(img, x + fw / 2, 84, v, bahn(13.5, 'Bold Condensed'), hexc(th['text']), anchor='mm', italic=0.14)
        x += fw + 2
    button(img, R1 - 140, 69, 140, 30, 'Open full size', th, 'outline', 13)
    text(img, R0, 124, 'EDIT', bahn(13, 'Bold Condensed'), hexc(th['muted']), italic=0.15)
    x = R0 + 46
    for b in ('Bigger', 'Smaller', 'Turn left', 'Turn right', 'Flip', 'Edit text…', 'Delete', 'Reset all'):
        fw = max(66, tw(b.upper(), bahn(12.5, 'SemiBold Condensed')) + 24)
        button(img, x, 110, fw, 28, b, th, 'outline', 12.5, k=7)
        x += fw + 4
    text(img, R0, 156, 'Click a logo, number or name, then drag to move · wheel = size · Shift+wheel = turn',
         segoe(11.5), hexc(th['muted']))

    # ---- preview ----
    PY0, PY1, FLOOR = 172, 936, 735
    preview_bg(img, th, R0, PY0, R1, PY1, FLOOR)
    d = ImageDraw.Draw(img)
    d.rectangle([P(R0), P(PY0), P(R1), P(PY1)], outline=hexc(th['line']), width=P(1))
    for (cx, cy, sx, sy) in ((R0, PY0, 1, 1), (R1, PY0, -1, 1), (R0, PY1, 1, -1), (R1, PY1, -1, -1)):
        d.line([(P(cx), P(cy)), (P(cx + 26 * sx), P(cy))], fill=hexc(th['acc']), width=P(3))
        d.line([(P(cx), P(cy)), (P(cx), P(cy + 26 * sy))], fill=hexc(th['acc']), width=P(3))
    X, Y, sc = place_car(img, R0 + 40, 0, R1 - R0 - 80, FLOOR)
    d = ImageDraw.Draw(img)
    # selected logo box (the rat on the door in the source picture: x 915-1045, y 262-382)
    dashed_rect(d, (X + 905 * sc, Y + 255 * sc, X + 1052 * sc, Y + 388 * sc), hexc(th['acc']))
    text(img, R0 + 18, PY0 + 24, 'LEFT SIDE', bahn(20, 'Bold Condensed'), hexc(th['text']), italic=0.2)
    text(img, R0 + 18, PY0 + 46, 'chucknorris  ·  DOORS (BIG)  ·  selected', bahn(12, 'SemiBold Condensed'), hexc(th['acc']), italic=0.1)
    pill = para(R1 - 190, PY1 - 40, 172, 26, 7)
    d.polygon(pill, fill=hexc(th['panel2']), outline=hexc(th['acc']), width=P(1.2))
    text(img, R1 - 104, PY1 - 27, 'PREVIEW ONLY · NOT SAVED', bahn(12, 'Bold Condensed'), hexc(th['acc']), anchor='mm', italic=0.12)
    # theme name tag (for the comparison only)
    text(img, R1 - 18, PY0 + 24, th['name'], bahn(14, 'Bold Condensed'), hexc(th['muted']), anchor='rm', italic=0.15)
    img.convert('RGB').save(os.path.join(OUT, fname), quality=92)
    print('saved', fname)


THEMES = {
    'A_neon_night': dict(name='STYLE A · NEON NIGHT', bg='#07080f', panel='#0f1122', panel2='#161936', field='#0a0b18',
                         line='#2a2f5c', text='#eef0ff', muted='#8a8fb8', acc='#ff2d7a', acc2='#1fe3ff',
                         on_acc='#ffffff', on_acc2='#04121a', preview='neon'),
    'B_carbon_orange': dict(name='STYLE B · CARBON', bg='#0d0d0d', panel='#171717', panel2='#202020', field='#101010',
                            line='#363636', text='#f4f4f4', muted='#8e8e8e', acc='#ff6a00', acc2='#ffffff',
                            on_acc='#ffffff', on_acc2='#111111', preview='carbon'),
    'C_street_yellow': dict(name='STYLE C · STREET', bg='#0a0a0a', panel='#141414', panel2='#1c1c1c', field='#0e0e0e',
                            line='#303030', text='#ffffff', muted='#9a9a9a', acc='#ffe600', acc2='#ff3355',
                            on_acc='#0a0a0a', on_acc2='#ffffff', preview='street'),
}

if __name__ == '__main__':
    for k, th in THEMES.items():
        if len(sys.argv) < 2 or sys.argv[1] in k:
            render(th, k + '.jpg')
