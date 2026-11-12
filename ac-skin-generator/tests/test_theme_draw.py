"""theme.py drawing (no Tk): slanted shapes, garage, ghost, cut-out, preview composition.
python -m pytest -p no:cacheprovider tests/test_theme_draw.py -q"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import theme

KINDS = ('primary', 'secondary', 'outline', 'tab', 'tab_active', 'chip', 'chip_active')
STATES = ('normal', 'hover', 'pressed', 'disabled')


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def test_slant_sizes():
    for k in KINDS:
        for s in STATES:
            im = theme.slant_image(120, 30, 'Preview', k, s)
            assert im.mode == 'RGBA' and im.size == (120 + 2 * theme.PAD, 30 + 2 * theme.PAD), (k, s)
            assert im.getpixel((0, 0))[3] == 0, (k, s)
            assert np.asarray(im)[..., 3].max() > 0, (k, s)


def test_garage_opaque():
    w, h = 600, 400
    g = theme.garage(w, h, int(h * 0.8))
    a = np.asarray(g)
    assert g.size == (w, h) and a[..., 3].min() == 255
    stripe = {tuple(int(v) for v in a[h - 5, x, :3]) for x in range(0, w, 3)}   # the hazard stripes on the bottom edge
    assert any(max(abs(c - t) for c, t in zip(px, hexrgb(theme.ACC))) < 30 for px in stripe)


def grey_car(w=300, h=200):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    a = np.asarray(im).copy()
    a[20:180, 30:270] = (150, 150, 150, 255)
    a[60:120, 80:220] = (190, 190, 190, 255)                       # a lighter panel: gives an edge
    return Image.fromarray(a)


def test_ghost_fits_and_fades():
    gh = theme.ghost_image(grey_car(), 500, 250)
    assert gh.width <= 500 and gh.height <= 250 and gh.mode == 'RGBA'
    a = np.asarray(gh)[..., 3]
    assert a[-1].max() == 0 and a.max() > 0


def test_cutout_unmixes():
    bg = (235, 236, 240)
    mix = tuple(round(255 * 0.5 + b * 0.5) if i == 0 else round(b * 0.5) for i, b in enumerate(bg))
    im = Image.new('RGBA', (4, 4), bg + (0,))
    im.putpixel((1, 1), mix + (128,))
    px = theme.cutout(im, bg).getpixel((1, 1))
    assert px[3] == 128 and px[0] > 245 and px[1] < 10 and px[2] < 10


def side_car():
    """A view like the renderer's: the car with an empty margin round it (here 40 px under the wheels)."""
    im = Image.new('RGBA', (1600, 560), (0, 0, 0, 0))
    im.paste((200, 30, 30, 255), (40, 20, 1560, 520))
    im.paste((200, 200, 200, 255), (500, 520, 502, 552))          # a thin flap edge hanging lower: not the floor line
    return im


def test_compose_side_on_floor():
    W, H = 900, 700
    bg = theme.preview_background(W, H, grey_car())
    img, geom = theme.compose_preview(bg, side_car(), 'left', 'LEFT SIDE', 'PREVIEW ONLY · NOT SAVED', None)
    ox, oy, w, h = geom
    assert img.mode == 'RGB' and img.size == (W, H)
    lowest = oy + round(520 * h / 560)                             # the car's lowest visible row
    assert abs(lowest - int(H * 0.80)) <= 1
    assert 0 <= ox and ox + w <= W and oy >= 0


def test_compose_tiny():
    for W, H in ((200, 200), (60, 60)):
        bg = theme.preview_background(W, H, grey_car())
        img, geom = theme.compose_preview(bg, side_car(), 'all', 'ALL SIDES', None, None)
        assert img.size == (W, H)
        ox, oy, w, h = geom
        assert ox >= 0 and oy >= 0 and ox + w <= W and oy + h <= H and w >= 1 and h >= 1
        img, geom = theme.compose_preview(bg, None, 'left', 'LEFT SIDE', None, ('PRESS PREVIEW', 'to see your livery on the car'))
        assert geom is None


def test_text_image_fallback(monkeypatch):
    monkeypatch.setattr(theme, 'BAHN', r'D:\no\such\font.ttf')
    theme._FONTS.clear()
    im = theme.text_image('CREATE SKIN IN CAR', 20, theme.TEXT)
    assert im.width > 50 and np.asarray(im)[..., 3].max() > 0
    theme._FONTS.clear()


def test_text_image_symbols():
    """'Turn ↺' / 'Turn ↻': Bahnschrift has no arrows; they come from Segoe UI Symbol."""
    runs = theme._runs('TURN ↺', 15, 'Bold Condensed')
    assert runs[0][0] == 'TURN ' and runs[-1][0] == '↺'
    assert runs[-1][1].path.lower().endswith('seguisym.ttf')
    assert theme.text_image('TURN ↻', 15).width > theme.text_image('TURN ', 15).width


def test_compose_all_above_stripes():
    W, H = 640, 760
    bg = theme.preview_background(W, H, None)
    sheet = Image.new('RGBA', (1600, 2600), (200, 30, 30, 255))      # 'all sides': a tall sheet
    _, (ox, oy, w, h) = theme.compose_preview(bg, sheet, 'all', 'ALL SIDES', 'PREVIEW ONLY · NOT SAVED', None)
    assert oy + h <= H - 46                                           # clear of the hazard stripes and the pill
