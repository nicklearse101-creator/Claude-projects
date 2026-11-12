"""Ratty's4Skin Generator - the look (v1.8.0): carbon + orange, slanted 'game' shapes, a garage behind the preview
with a ghost of the car being edited. Top part: drawing with PIL only. Bottom part: the Tk side (styles, widgets,
dialogs). Every look decision lives here; rattys4skin.py only asks for themed widgets."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BG, PANEL, RAISED, FIELD, LINE = '#0d0d0d', '#171717', '#202020', '#101010', '#363636'
TEXT, MUTED, ACC, ACC2 = '#f4f4f4', '#8e8e8e', '#ff6a00', '#ffffff'
PAD = 6                                    # room round every slanted shape for its glow
FONT_DIR = r'C:\Windows\Fonts'
BAHN = os.path.join(FONT_DIR, 'bahnschrift.ttf')
SEGOE_B = os.path.join(FONT_DIR, 'segoeuib.ttf')
SEGOE = os.path.join(FONT_DIR, 'segoeui.ttf')
_FONTS = {}


def hexc(h, a=255):
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a


def _font(size, style):
    """Bahnschrift in one of its named styles; Segoe UI (bold) where Bahnschrift is missing. style 'Segoe' = Segoe UI."""
    key = (size, style, BAHN)
    if key not in _FONTS:
        f = None
        if style != 'Segoe':
            try:
                f = ImageFont.truetype(BAHN, max(1, int(round(size))))
                f.set_variation_by_name(style)
            except Exception:
                f = None
        if f is None:
            try: f = ImageFont.truetype(SEGOE if style == 'Segoe' else SEGOE_B, max(1, int(round(size))))
            except Exception: f = ImageFont.load_default()
        _FONTS[key] = f
    return _FONTS[key]


SYMBOLS = set('↺↻←→↑↓')                    # not in Bahnschrift: drawn with Segoe UI Symbol
SYM_FONT = os.path.join(FONT_DIR, 'seguisym.ttf')


def _runs(text, size, style):
    """The text cut into pieces with the font each one is drawn in: [(piece, font)]."""
    runs = []
    for ch in text:
        sym = ch in SYMBOLS
        if not runs or runs[-1][2] != sym: runs.append([ch, None, sym])
        else: runs[-1][0] += ch
    for r in runs:
        if r[2]:
            try: r[1] = ImageFont.truetype(SYM_FONT, max(1, int(round(size))))
            except Exception: r[1] = _font(size, style)
        else:
            r[1] = _font(size, style)
    return [(s, f) for s, f, _ in runs]


def text_image(text, size, colour=TEXT, style='Bold Condensed', italic=0.18, glow=None):
    """Words as an RGBA picture: slanted like the NFS menus (italic = shear), with an optional soft glow."""
    fill = hexc(colour) if isinstance(colour, str) else colour
    pad = 10 if glow else 2
    runs = _runs(text or ' ', size, style)
    if len(runs) == 1:
        f = runs[0][1]
        l, t, r, b = f.getbbox(text or ' ')
        w, h = max(1, r - l + 4), max(1, b - t + 4)
        H = h + 2 * pad
        extra = int(italic * H) + 1 if italic else 0
        lay = Image.new('RGBA', (w + extra + 2 * pad, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((pad - l, pad - t), text, font=f, fill=fill)
    else:                                     # mixed fonts: pieces side by side on one baseline
        asc, desc = _font(size, style).getmetrics()
        w, h = int(sum(f.getlength(s) for s, f in runs)) + 4, asc + desc + 2
        H = h + 2 * pad
        extra = int(italic * H) + 1 if italic else 0
        lay = Image.new('RGBA', (w + extra + 2 * pad, H), (0, 0, 0, 0))
        d, x = ImageDraw.Draw(lay), pad
        for s, f in runs:
            d.text((x, pad + asc), s, font=f, fill=fill, anchor='ls')
            x += f.getlength(s)
    if italic:
        lay = lay.transform(lay.size, Image.AFFINE, (1, italic, -italic * H, 0, 1, 0), Image.BICUBIC)
    if glow:
        g = Image.new('RGBA', lay.size, hexc(glow) if isinstance(glow, str) else glow)
        g.putalpha(lay.split()[3].filter(ImageFilter.GaussianBlur(6)))
        lay = Image.alpha_composite(Image.alpha_composite(g, g), lay)
    return lay


def _shade(rgb, k):
    """k > 0 lighter, k < 0 darker."""
    return tuple(int(round(c + (255 - c) * k)) if k > 0 else int(round(c * (1 + k))) for c in rgb[:3]) + (rgb[3],)


_KINDS = {     # fill, outline, outline width, text colour, text style, glow
    'primary': (ACC, None, 0, '#ffffff', 'Bold Condensed', True),
    'tab_active': (ACC, None, 0, '#ffffff', 'Bold Condensed', True),
    'secondary': (RAISED, ACC2, 2, ACC2, 'Bold Condensed', False),
    'outline': (RAISED, LINE, 1, TEXT, 'SemiBold Condensed', False),
    'tab': (RAISED, LINE, 1, MUTED, 'Bold Condensed', False),
    'chip': (RAISED, LINE, 1, TEXT, 'Bold Condensed', False),
    'chip_active': (ACC2, None, 0, '#111111', 'Bold Condensed', False),
}


def slant_image(w, h, label, kind, state='normal', size=13):
    """A button / tab / chip: a parallelogram leaning right, its words in slanted capitals. Size (w + 2*PAD, h + 2*PAD)."""
    fill, outline, ow, fg, style, glow = _KINDS[kind]
    fill = hexc(fill)
    if state == 'hover': fill = _shade(fill, 0.12)
    elif state == 'pressed': fill = _shade(fill, -0.15)
    W, H = w + 2 * PAD, h + 2 * PAD
    k = h // 4
    ss = 3                                                    # drawn 3x and scaled down: smooth slanted edges
    poly = [((PAD + k) * ss, PAD * ss), ((PAD + w) * ss, PAD * ss), ((PAD + w - k) * ss, (PAD + h) * ss), (PAD * ss, (PAD + h) * ss)]
    big = Image.new('RGBA', (W * ss, H * ss), (0, 0, 0, 0))
    ImageDraw.Draw(big).polygon(poly, fill=fill, outline=hexc(outline) if outline else None, width=ow * ss)
    shape = big.resize((W, H), Image.LANCZOS)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if glow and state != 'disabled':
        g = Image.new('RGBA', (W, H), hexc(ACC, 0))
        g.putalpha(shape.split()[3].point(lambda v: v * 150 // 255).filter(ImageFilter.GaussianBlur(4)))
        img = Image.alpha_composite(img, g)
    img = Image.alpha_composite(img, shape)
    t = text_image(label.upper(), size, fg, style, italic=0.14)
    _put(img, t, (W - t.width) // 2 + 1, (H - t.height) // 2)
    if state == 'disabled':
        img.putalpha(img.split()[3].point(lambda v: v * 45 // 100))
    return img


def _put(base, im, x, y):
    """alpha_composite that clips at the edges (negative or overflowing positions are fine)."""
    x, y = int(x), int(y)
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, base.width - x), min(im.height, base.height - y)
    if r <= l or b <= t: return
    base.alpha_composite(im.crop((l, t, r, b)) if (l, t, r, b) != (0, 0, im.width, im.height) else im, (x + l, y + t))


def garage(w, h, floor_y):
    """Behind the preview: carbon weave, dark edges, an orange spotlight; below floor_y a street floor - dark, dots
    growing towards the front, orange-black hazard stripes on the bottom edge, an orange floor line and glow."""
    w, h = max(1, int(w)), max(1, int(h))
    fy = min(max(0, int(floor_y)), h)
    t = 7
    tile = np.zeros((2 * t, 2 * t), np.uint8)
    for i in range(t):
        c1, c2 = 22 + int(14 * i / t), 30 - int(12 * i / t)
        tile[i, :t] = c1; tile[t:, t + i] = c1; tile[:t, t + i] = c2; tile[t + i, :t] = c2
    weave = np.tile(tile, (h // (2 * t) + 1, w // (2 * t) + 1))[:h, :w]
    img = Image.fromarray(np.dstack([weave] * 3 + [np.full((h, w), 255, np.uint8)]), 'RGBA')
    vig = Image.new('L', (w, h), 160)
    ImageDraw.Draw(vig).ellipse([w * 0.05, -h * 0.2, w * 0.95, h * 1.0], fill=0)
    img.alpha_composite(Image.merge('RGBA', [Image.new('L', (w, h), 0)] * 3 + [vig.filter(ImageFilter.GaussianBlur(60))]))
    sp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sp).polygon([(w * 0.42, 0), (w * 0.58, 0), (w * 0.95, fy + 30), (w * 0.05, fy + 30)], fill=hexc(ACC, 22))
    img.alpha_composite(sp.filter(ImageFilter.GaussianBlur(26)))
    fl = Image.new('RGBA', (w, h), (0, 0, 0, 0)); fd = ImageDraw.Draw(fl)
    if fy < h:
        fd.rectangle([0, fy, w, h], fill=(8, 8, 8, 215))
        step = 13
        for yy in range(fy + step // 2, h, step):
            r = ((yy - fy) / max(1, h - fy)) ** 1.3 * step * 0.40
            if r > 0.6:
                for xx in range(0, w, step):
                    fd.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(40, 40, 40, 255))
    band, sh = 22, min(40, h)
    for i in range(-2, w // (2 * band) + 3):
        x = i * band * 2
        fd.polygon([(x, h), (x + band, h), (x + band + sh, h - sh), (x + sh, h - sh)], fill=hexc(ACC))
    img.alpha_composite(fl)
    gl = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([w * 0.12, fy - 16, w * 0.88, fy + 30], fill=hexc(ACC, 120))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(24)))
    ln = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(ln).line([(0, fy), (w, fy)], fill=hexc(ACC, 220), width=2)
    img.alpha_composite(ln)
    return img


def ghost_image(grey, max_w, max_h):
    """The ghost: the car's untextured front view (RGBA on black, alpha = coverage) as orange lines with a faint fill,
    fitted inside max_w x max_h and fading out towards the bottom."""
    arr = np.asarray(grey.convert('RGBA'), np.float32)
    g = arr[..., :3].mean(-1)
    mask = arr[..., 3] / 255
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1])); gy = np.abs(np.diff(g, axis=0, prepend=g[:1]))
    edge = np.clip((gx + gy) / 22.0, 0, 1) * mask
    edge = np.asarray(Image.fromarray((edge * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
    shade = np.clip((g - 100) / 100, 0, 1) * mask
    a = np.clip(mask * (0.05 + 0.10 * shade) + edge * 0.55, 0, 1)
    rgb = np.array(hexc(ACC)[:3], np.float32) * 0.65 + 255 * 0.35 * edge[..., None]
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA')
    sc = min(max_w / im.width, max_h / im.height)
    nw, nh = int(im.width * sc), int(im.height * sc)
    if nw < 2 or nh < 2: return Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    im = im.resize((nw, nh), Image.LANCZOS)
    im = Image.alpha_composite(im.filter(ImageFilter.GaussianBlur(5)), im)
    out = np.asarray(im).copy()
    fade = np.clip(np.linspace(1.25, 0.0, nh), 0, 1) ** 0.9
    out[..., 3] = (out[..., 3] * fade[:, None]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def cutout(view, bg=(235, 236, 240)):
    """A preview view (RGBA, alpha = coverage) with the light-grey background taken out of its edge pixels."""
    arr = np.asarray(view.convert('RGBA'), np.float32)
    a = arr[..., 3:] / 255
    rgb = np.where(a > 0, (arr[..., :3] - np.array(bg, np.float32) * (1 - a)) / np.maximum(a, 1 / 255), 0)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), arr[..., 3]]).astype(np.uint8), 'RGBA')


def floor_of(h):
    return int(h * 0.80)


def preview_background(w, h, ghost):
    """The garage for a preview area of w x h, with the ghost (grey front view from skingen.ghost_view) above the floor."""
    fy = floor_of(h)
    img = garage(w, h, fy)
    if ghost is not None:
        gi = ghost_image(ghost, int(w * 0.98), max(1, fy - 20))
        _put(img, gi, (w - gi.width) // 2, 14)
    return img


def compose_preview(background, car, view, title, pill, prompt):
    """The preview as shown: background + the car (side views stand on the floor with a reflection; 'top' and
    'all' sit in the middle) + the title, the 'preview only' pill and a prompt. Returns (RGB image, car box or None)."""
    img = background.copy().convert('RGBA')
    W, H = img.size
    fy = floor_of(H)
    top_m, bot_m, side_m = min(70, int(H * 0.12)), min(48, int(H * 0.07)), min(20, int(W * 0.03))   # bottom: clear of the stripes
    geom = None
    if car is not None:
        side = view in ('left', 'right', 'front', 'rear')
        bw, bh = max(1, W - 2 * side_m), max(1, (fy if side else H - bot_m) - top_m)
        sc = min(bw / car.width, bh / car.height)
        cw, ch = max(1, min(bw, int(car.width * sc))), max(1, min(bh, int(car.height * sc)))
        c = car.convert('RGBA').resize((cw, ch), Image.LANCZOS)
        ox = (W - cw) // 2
        oy = top_m + (bh - ch) // 2
        if side:   # the car's lowest row (tyres; not the picture's empty margin, not thin flap edges) on the floor
            rows = np.nonzero((np.asarray(c)[..., 3] > 24).sum(1) >= max(2, cw * 0.005))[0]
            low = int(rows[-1]) + 1 if len(rows) else ch
            oy = fy - low
            if fy < H:
                ref = c.crop((0, 0, cw, low)).transpose(Image.FLIP_TOP_BOTTOM)
                ra = np.asarray(ref).copy()
                ra[..., 3] = (ra[..., 3] * np.linspace(0.28, 0.0, ref.height)[:, None]).astype(np.uint8)
                _put(img, Image.fromarray(ra, 'RGBA'), ox, fy)
        _put(img, c, ox, oy)
        geom = (ox, oy, cw, ch)
    if title:
        _put(img, text_image(title, 20, TEXT, italic=0.2), 16, 10)
    if pill:
        t = text_image(pill, 12, ACC, italic=0.12)
        pw, ph = t.width + 26, 26
        px, py = W - 18 - pw, H - 46
        lay = Image.new('RGBA', (pw + 1, ph + 1), (0, 0, 0, 0))
        ImageDraw.Draw(lay).polygon([(7, 0), (pw, 0), (pw - 7, ph), (0, ph)], fill=hexc(RAISED), outline=hexc(ACC), width=1)
        _put(lay, t, (pw - t.width) // 2, (ph - t.height) // 2)
        _put(img, lay, px, py)
    if prompt:
        t1 = text_image(prompt[0], 46, '#ffffff', italic=0.2, glow=hexc(ACC, 200))
        t2 = text_image(prompt[1], 15, MUTED, style='Segoe', italic=0)
        cy = int(H * 0.62)
        _put(img, t1, (W - t1.width) // 2, cy - t1.height // 2)
        _put(img, t2, (W - t2.width) // 2, cy + t1.height // 2 - 4)
    return img.convert('RGB'), geom


# ===================================================================================================== Tk side
import types
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from PIL import ImageTk

UI_FONT = ('Segoe UI', 9)
HEAD = 'Bahnschrift SemiBold Condensed'           # Tk family for field labels / section titles (fallback below)


def _swap(layout, old, new):
    """A ttk layout with element `old` renamed `new` (recursively)."""
    out = []
    for name, opts in layout:
        opts = dict(opts)
        if 'children' in opts: opts['children'] = _swap(opts['children'], old, new)
        out.append((new if name == old else name, opts))
    return out


def _field_img(focus):
    im = Image.new('RGBA', (24, 24), hexc(FIELD))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 23, 23], outline=hexc(ACC if focus else LINE))
    d.rectangle([0, 22, 23, 23], fill=hexc(ACC))
    return im


def _check_img(on, disabled=False):
    big = Image.new('RGBA', (48, 48), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    d.rectangle([3, 3, 44, 44], fill=hexc(FIELD), outline=hexc(ACC if on else MUTED), width=4)
    if on: d.line([(12, 24), (20, 33), (36, 13)], fill=hexc(ACC), width=6)
    im = Image.new('RGBA', (22, 16), (0, 0, 0, 0))
    im.alpha_composite(big.resize((16, 16), Image.LANCZOS), (0, 0))
    if disabled: im.putalpha(im.split()[3].point(lambda v: v * 45 // 100))
    return im


def _row_img(selected):
    """Tree row background: plain field, or (selected) a 4 px orange bar and an orange fade to the right."""
    w, h = 1600, 4
    a = np.zeros((h, w, 4), np.uint8); a[..., :3] = hexc(FIELD)[:3]; a[..., 3] = 255
    if selected:
        acc = np.array(hexc(ACC)[:3], np.float32); base = np.array(hexc(FIELD)[:3], np.float32)
        k = np.linspace(0.55, 0.0, 520)
        a[:, :520, :3] = (base * (1 - k[:, None]) + acc * k[:, None]).astype(np.uint8)
        a[:, :4, :3] = acc.astype(np.uint8)
    return Image.fromarray(a, 'RGBA')


def apply_style(root):
    """The whole ttk look on the clam theme. Images are kept on root._theme_imgs."""
    global HEAD
    if HEAD not in tkfont.families(root): HEAD = 'Segoe UI Semibold'
    s = ttk.Style(root)
    s.theme_use('clam')
    root.configure(bg=BG)
    imgs = root._theme_imgs = {}

    def photo(key, im):
        imgs[key] = ImageTk.PhotoImage(im, master=root)
        return imgs[key]
    s.configure('.', background=PANEL, foreground=TEXT, fieldbackground=FIELD, bordercolor=LINE, lightcolor=PANEL,
                darkcolor=PANEL, troughcolor=RAISED, selectbackground=ACC, selectforeground='#ffffff', insertcolor=TEXT,
                font=UI_FONT, focuscolor=ACC, arrowcolor=ACC)
    s.map('.', foreground=[('disabled', MUTED)])
    s.configure('TFrame', background=PANEL)
    s.configure('Window.TFrame', background=BG)
    s.configure('TLabel', background=PANEL, foreground=TEXT)
    s.configure('Window.TLabel', background=BG, foreground=TEXT)
    s.configure('Note.TLabel', foreground=MUTED, font=UI_FONT)
    s.configure('Field.TLabel', foreground=MUTED, font=(HEAD, 10))
    s.configure('Section.TLabel', foreground=TEXT, font=(HEAD, 12))
    s.configure('Status.TLabel', background=BG, foreground=MUTED, font=UI_FONT)
    s.configure('Hint.TLabel', background=BG, foreground=MUTED, font=UI_FONT)
    s.configure('WField.TLabel', background=BG, foreground=MUTED, font=(HEAD, 10))
    s.configure('Pct.TLabel', background=BG, foreground=ACC, font=(HEAD, 11))
    # entry / combobox / spinbox: dark field with an orange underline (whole border orange with focus)
    s.configure('TEntry', foreground=TEXT, padding=(6, 4))
    s.configure('TCombobox', foreground=TEXT, background=RAISED, arrowsize=16, padding=(6, 4))
    s.configure('TSpinbox', foreground=TEXT, background=RAISED, arrowsize=12, padding=(6, 3))
    s.map('TCombobox', fieldbackground=[('readonly', FIELD)], foreground=[('readonly', TEXT)],
          selectbackground=[('readonly', FIELD), ('', ACC)], selectforeground=[('readonly', TEXT), ('', '#ffffff')],
          background=[('active', RAISED), ('pressed', RAISED)], arrowcolor=[('', ACC)])
    s.map('TSpinbox', background=[('active', RAISED)], arrowcolor=[('', ACC)])
    try:
        s.element_create('Dark.field', 'image', photo('field', _field_img(False)), ('focus', photo('field_f', _field_img(True))),
                         border=3, sticky='nswe')
        for w in ('TEntry', 'TCombobox', 'TSpinbox'):
            s.layout(w, _swap(s.layout(w), w[1:] + '.field', 'Dark.field'))
    except tk.TclError:
        s.map('TEntry', bordercolor=[('focus', ACC)]); s.map('TCombobox', bordercolor=[('focus', ACC)])
    root.option_add('*TCombobox*Listbox.background', FIELD)
    root.option_add('*TCombobox*Listbox.foreground', TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground', ACC)
    root.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
    root.option_add('*TCombobox*Listbox.font', UI_FONT)
    # tick boxes: dark square, orange border and tick
    s.configure('TCheckbutton', background=PANEL, foreground=TEXT, padding=(0, 2))
    s.map('TCheckbutton', background=[('active', PANEL)], foreground=[('disabled', MUTED)])
    try:
        s.element_create('Dark.check', 'image', photo('chk0', _check_img(False)),
                         ('disabled', 'selected', photo('chk1d', _check_img(True, True))), ('selected', photo('chk1', _check_img(True))),
                         ('disabled', photo('chk0d', _check_img(False, True))), sticky='w')
        s.layout('TCheckbutton', [('Checkbutton.padding', {'sticky': 'nswe', 'children': [
            ('Dark.check', {'side': 'left', 'sticky': ''}),
            ('Checkbutton.focus', {'side': 'left', 'sticky': 'w', 'children': [('Checkbutton.label', {'sticky': 'nswe'})]})]})])
    except tk.TclError:
        s.configure('TCheckbutton', indicatorbackground=FIELD, indicatorforeground=ACC)
    # lists
    s.configure('Treeview', background=FIELD, fieldbackground=FIELD, foreground=TEXT, bordercolor=LINE,
                lightcolor=FIELD, darkcolor=FIELD)
    s.map('Treeview', background=[('selected', '#3a1d08')], foreground=[('selected', ACC)])
    try:
        s.element_create('Dark.row', 'image', photo('row', _row_img(False)), ('selected', photo('row_s', _row_img(True))),
                         border=(4, 0, 0, 0), sticky='nswe')
        s.layout('Treeview.Row', [('Dark.row', {'sticky': 'nswe'})])
    except tk.TclError:
        pass
    s.configure('Treeview.Heading', background=PANEL, foreground=ACC2, font=(HEAD, 10), bordercolor=LINE,
                lightcolor=PANEL, darkcolor=PANEL, relief='flat')
    s.map('Treeview.Heading', background=[('active', RAISED)])
    s.configure('Orange.Horizontal.TProgressbar', troughcolor=RAISED, background=ACC, bordercolor=BG, lightcolor=ACC,
                darkcolor=ACC, thickness=6, arrowsize=6)
    s.configure('TScrollbar', background=RAISED, troughcolor=PANEL, bordercolor=PANEL, arrowcolor=MUTED,
                lightcolor=RAISED, darkcolor=RAISED)
    s.map('TScrollbar', background=[('active', LINE)])
    s.configure('TLabelframe', background=PANEL, bordercolor=LINE, lightcolor=PANEL, darkcolor=PANEL)
    s.configure('TLabelframe.Label', background=PANEL, foreground=ACC2, font=(HEAD, 11))
    s.configure('TSeparator', background=LINE)
    s.configure('TButton', background=RAISED, foreground=TEXT, bordercolor=LINE, lightcolor=RAISED, darkcolor=RAISED)
    s.map('TButton', background=[('active', LINE)])


def _parent_bg(parent):
    try: return parent.cget('bg')
    except tk.TclError: pass
    try:
        st = parent.cget('style') or parent.winfo_class()
        return ttk.Style(parent).lookup(st, 'background') or PANEL
    except tk.TclError:
        return PANEL


class SlantButton(tk.Canvas):
    """A slanted game-style button. Behaves like a ttk button where the app needs it: invoke(), state([...])."""

    def __init__(self, parent, text, command=None, kind='outline', size=15, width=None, height=30, bg=None):
        self._text, self._kind, self._size, self._h = text, kind, size, height
        self._bw = width or (text_image(text.upper(), size).width + 22)
        super().__init__(parent, width=self._bw + 2 * PAD, height=height + 2 * PAD, bg=bg or _parent_bg(parent),
                         highlightthickness=0, bd=0, cursor='hand2')
        self.command = command
        self._disabled = self._hover = self._pressed = False
        self._imgs = {}
        self.bind('<Enter>', lambda e: self._set(hover=True))
        self.bind('<Leave>', lambda e: self._set(hover=False, pressed=False))
        self.bind('<ButtonPress-1>', lambda e: self._set(pressed=True))
        self.bind('<ButtonRelease-1>', self._release)
        self._draw()

    def _set(self, **kw):
        for k, v in kw.items(): setattr(self, '_' + k, v)
        self._draw()

    def _draw(self):
        st = 'disabled' if self._disabled else 'pressed' if self._pressed else 'hover' if self._hover else 'normal'
        if st not in self._imgs:
            self._imgs[st] = ImageTk.PhotoImage(slant_image(self._bw, self._h, self._text, self._kind, st, self._size), master=self)
        self.delete('all')
        self.create_image(0, 0, image=self._imgs[st], anchor='nw')

    def _release(self, e):
        was = self._pressed
        self._set(pressed=False)
        if was and 0 <= e.x < int(self.cget('width')) and 0 <= e.y < int(self.cget('height')):
            self.invoke()

    def invoke(self):
        if not self._disabled and self.command: return self.command()

    def state(self, spec=None):
        for s_ in spec or ():
            if s_ == 'disabled': self._disabled = True
            elif s_ == '!disabled': self._disabled = False
        if spec:
            super().configure(cursor='arrow' if self._disabled else 'hand2'); self._draw()
        return ('disabled',) if self._disabled else ()

    def configure(self, cnf=None, **kw):
        if 'text' in kw:
            self._text = kw.pop('text'); self._imgs.clear(); self._draw()
        if 'command' in kw: self.command = kw.pop('command')
        return super().configure(cnf, **kw) if (cnf or kw) else None
    config = configure


class SlantTabs(ttk.Frame):
    """A strip of slanted tabs over pages; pages share one grid cell (the panel keeps the tallest page's size)."""

    def __init__(self, parent, size=16, height=34):
        super().__init__(parent, style='Window.TFrame')
        self._size, self._h = size, height
        self.strip = tk.Canvas(self, height=height + 2 * PAD, bg=BG, highlightthickness=0, bd=0)
        self.strip.pack(fill='x')
        tk.Frame(self, height=2, bg=ACC).pack(fill='x')
        self.body = ttk.Frame(self, style='TFrame')
        self.body.pack(fill='both', expand=True)
        self.body.columnconfigure(0, weight=1)
        self.pages, self.titles, self.current, self._hover = [], [], 0, None
        self._imgs = {}

    def add(self, title, padding=10):
        p = ttk.Frame(self.body, padding=padding)
        p.grid(row=0, column=0, sticky='nsew')
        if self.pages: p.grid_remove()
        self.pages.append(p); self.titles.append(title)
        self._draw()
        return p

    def select(self, index):
        self.current = index
        for i, p in enumerate(self.pages):
            if i == index: p.grid()
            else: p.grid_remove()
        self.update_idletasks()
        self.body.grid_rowconfigure(0, minsize=max(p.winfo_reqheight() for p in self.pages))
        self.body.grid_columnconfigure(0, minsize=max(p.winfo_reqwidth() for p in self.pages))
        self._draw()
        self.event_generate('<<TabChanged>>')

    def index(self):
        return self.current

    def _img(self, i, w, state):
        kind = 'tab_active' if i == self.current else 'tab'
        key = (i, w, kind, state)
        if key not in self._imgs:
            self._imgs[key] = ImageTk.PhotoImage(slant_image(w, self._h, self.titles[i], kind, state, self._size), master=self)
        return self._imgs[key]

    def _draw(self):
        c = self.strip
        c.delete('all')
        x = 0
        for i, t in enumerate(self.titles):
            w = text_image(t.upper(), self._size).width + 18
            tag = f'tab{i}'
            c.create_image(x, 0, image=self._img(i, w, 'hover' if self._hover == i and i != self.current else 'normal'),
                           anchor='nw', tags=tag)
            c.tag_bind(tag, '<Button-1>', lambda e, i=i: self.select(i))
            c.tag_bind(tag, '<Enter>', lambda e, i=i: self._set_hover(i))
            c.tag_bind(tag, '<Leave>', lambda e: self._set_hover(None))
            x += w - 4
        c.configure(width=x + 2 * PAD, cursor='hand2')

    def _set_hover(self, i):
        if self._hover != i:
            self._hover = i
            self._draw()


class ChipGroup(tk.Canvas):
    """View chips (one picked) bound to a StringVar."""

    def __init__(self, parent, items, variable, command=None, bg=None, size=14, height=30):
        super().__init__(parent, height=height + 2 * PAD, bg=bg or _parent_bg(parent), highlightthickness=0, bd=0, cursor='hand2')
        self.items, self.var, self.command, self._size, self._h = list(items), variable, command, size, height
        self._imgs = {}
        variable.trace_add('write', lambda *a: self._draw())
        self._draw()

    def pick(self, key):
        self.var.set(key)
        if self.command: self.command()

    def _draw(self):
        self.delete('all')
        x = 0
        for key, label in self.items:
            w = text_image(label.upper(), self._size).width + 18
            kind = 'chip_active' if self.var.get() == key else 'chip'
            if (key, kind) not in self._imgs:
                self._imgs[(key, kind)] = ImageTk.PhotoImage(slant_image(w, self._h, label, kind, 'normal', self._size), master=self)
            self.create_image(x, 0, image=self._imgs[(key, kind)], anchor='nw', tags=f'c_{key}')
            self.tag_bind(f'c_{key}', '<Button-1>', lambda e, k=key: self.pick(k))
            x += w - 2
        self.configure(width=x + 2 * PAD)


def _fit_text(text, size, colour, maxw, style='Bold Condensed', italic=0.12):
    im = text_image(text, size, colour, style, italic)
    if im.width <= maxw: return im
    lo, hi = 0, len(text)
    while lo < hi:                                  # the longest start of the text that fits with '…'
        mid = (lo + hi + 1) // 2
        if text_image(text[:mid] + '…', size, colour, style, italic).width <= maxw: lo = mid
        else: hi = mid - 1
    return text_image(text[:lo] + '…', size, colour, style, italic)


class Header(tk.Canvas):
    """The strip on top: RATTY'S 4SKIN GENERATOR on the left; the car, skin and version on the right."""

    def __init__(self, parent, version):
        super().__init__(parent, height=54, bg=PANEL, highlightthickness=0, bd=0)
        self.version, self.car, self.skin = version, '', ''
        self.last_widths = (0, 0)
        self._imgs = []
        self.bind('<Configure>', lambda e: self._draw())

    def set_car(self, car, skin):
        self.car, self.skin = car or '', skin or ''
        self._draw()

    def _draw(self):
        W = max(self.winfo_width(), self.winfo_pixels(self.cget('width')), 200)
        self.delete('all'); self._imgs = []

        def put(im, x, y, anchor):
            ph = ImageTk.PhotoImage(im, master=self); self._imgs.append(ph)
            self.create_image(x, y, image=ph, anchor=anchor)
            return im.width
        x = 16
        x += put(text_image("RATTY'S", 30, TEXT, italic=0.22), x, 27, 'w') - 4
        x += put(text_image('4SKIN', 30, ACC, italic=0.22, glow=hexc(ACC, 170)), x - 10, 27, 'w') - 6
        put(text_image('GENERATOR', 14, MUTED, 'SemiBold Condensed', italic=0.15), x, 33, 'w')
        half = W // 2 - 20
        car = _fit_text(self.car.upper(), 15, TEXT, half)
        skin = _fit_text(f'SKIN {self.skin.upper()}  ·  v{self.version}', 11.5, MUTED, half, 'SemiBold Condensed', 0.1)
        put(car, W - 14, 20, 'e'); put(skin, W - 14, 40, 'e')
        self.last_widths = (car.width, skin.width)
        self.create_rectangle(0, 52, int(W * 0.6), 54, fill=ACC, width=0)
        self.create_rectangle(int(W * 0.6), 52, W, 54, fill=ACC2, width=0)


def dark_title_bar(win):
    """Windows 10 (20H1+) / 11: a dark title bar. False where Windows refuses."""
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                return True
    except Exception:
        pass
    return False


def style_toplevel(win):
    win.configure(bg=PANEL)
    dark_title_bar(win)


_open_dialogs = []


def _dialog(heading, title, message, parent=None, buttons=('OK',), warn=False):
    root = parent or tk._default_root
    win = tk.Toplevel(root)
    win.withdraw(); win.title(title); win.resizable(False, False)
    win.configure(bg=PANEL)
    if root is not None and root.winfo_viewable(): win.transient(root)
    f = ttk.Frame(win, padding=(20, 16, 20, 14)); f.pack(fill='both', expand=True)
    ttk.Label(f, text=heading, style='Section.TLabel', foreground=ACC if warn else TEXT).pack(anchor='w')
    ttk.Label(f, text=message, wraplength=440, justify='left').pack(anchor='w', pady=(6, 12))
    bf = ttk.Frame(f); bf.pack(anchor='e')
    result = {'v': None}
    win.buttons = {}

    def close(v):
        result['v'] = v; win.destroy()
    for i, label in enumerate(buttons):
        b = SlantButton(bf, label, command=lambda v=label: close(v), kind='primary' if i == 0 else 'outline', width=86)
        b.pack(side='left', padx=2); win.buttons[label] = b
    win.bind('<Return>', lambda e: close(buttons[0]))
    win.bind('<Escape>', lambda e: close(buttons[-1]))
    win.update_idletasks()
    if root is not None and root.winfo_viewable():
        x = root.winfo_rootx() + (root.winfo_width() - win.winfo_reqwidth()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - win.winfo_reqheight()) // 3
        win.geometry(f'+{x}+{y}')
    win.minsize(360, 0)
    win.deiconify()
    win.update_idletasks()
    win.dark_title = dark_title_bar(win)              # only takes once the window is shown
    try: win.grab_set()
    except tk.TclError: pass
    win.focus_set()
    _open_dialogs.append(win)
    try: win.wait_window()
    finally: _open_dialogs.remove(win)
    return result['v']


def _showerror(title, message, parent=None, icon=None, **kw):
    _dialog('ERROR', title, message, parent, warn=True)


def _showwarning(title, message, parent=None, icon=None, **kw):
    _dialog('WARNING', title, message, parent, warn=True)


def _showinfo(title, message, parent=None, icon=None, **kw):
    _dialog('INFO', title, message, parent)


def _askyesno(title, message, parent=None, icon=None, **kw):
    return _dialog('QUESTION', title, message, parent, ('Yes', 'No'), warn=icon == 'warning') == 'Yes'


# same names and call shape as tkinter.messagebox, so the app (and its tests) use it the same way
messagebox = types.SimpleNamespace(showerror=_showerror, showwarning=_showwarning, showinfo=_showinfo, askyesno=_askyesno)


class ButtonBar(tk.Canvas):
    """A row of slanted outline buttons that wraps onto more lines when the window is narrow."""

    def __init__(self, parent, items, size=13, height=26, bg=None, kind='outline'):
        super().__init__(parent, height=height + 2 * PAD, bg=bg or _parent_bg(parent), highlightthickness=0, bd=0, cursor='hand2')
        self.items, self._size, self._h, self._kind = list(items), size, height, kind
        self._widths = [text_image(t.upper(), size).width + 18 for t, _ in self.items]
        self._imgs, self._pos, self._hover, self._pressed, self.rows = {}, [], None, None, 1
        self.bind('<Configure>', lambda e: self._layout())
        self._layout()

    def invoke(self, label):
        return dict(self.items)[label]()

    def _layout(self):
        W = self.winfo_width()
        if W <= 1: W = 10 ** 6
        x = y = 0; rows = 1; self._pos = []
        for w in self._widths:
            if x > 0 and x + w + 2 * PAD > W:
                x, y, rows = 0, y + self._h + PAD, rows + 1
            self._pos.append((x, y)); x += w - 4
        self.rows = rows
        need = rows * (self._h + PAD) + PAD
        if self.winfo_reqheight() != need: super().configure(height=need)
        self._draw()

    def _img(self, i, state):
        if (i, state) not in self._imgs:
            self._imgs[(i, state)] = ImageTk.PhotoImage(
                slant_image(self._widths[i], self._h, self.items[i][0], self._kind, state, self._size), master=self)
        return self._imgs[(i, state)]

    def _draw(self):
        self.delete('all')
        for i, (x, y) in enumerate(self._pos):
            st = 'pressed' if self._pressed == i else 'hover' if self._hover == i else 'normal'
            tag = f'b{i}'
            self.create_image(x, y, image=self._img(i, st), anchor='nw', tags=tag)
            self.tag_bind(tag, '<Enter>', lambda e, i=i: self._state(hover=i))
            self.tag_bind(tag, '<Leave>', lambda e: self._state(hover=None, pressed=None))
            self.tag_bind(tag, '<ButtonPress-1>', lambda e, i=i: self._state(pressed=i))
            self.tag_bind(tag, '<ButtonRelease-1>', lambda e, i=i: self._release(i))

    def _state(self, **kw):
        for k, v in kw.items(): setattr(self, '_' + k, v)
        self._draw()

    def _release(self, i):
        was = self._pressed == i
        self._state(pressed=None)
        if was: self.items[i][1]()
