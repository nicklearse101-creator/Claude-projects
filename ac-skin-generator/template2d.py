"""2D mode for cars whose model is protected by Custom Shaders Patch (Nik 17 Nov; research/Encrypted cars 2D livery
painting.md). The protection scrambles the model's texture mapping, so the 3D projection can't be used - but the car's
skins are normal pictures of its paint sheet. This paints that sheet directly, the way a painter does in GIMP:

  source  - the maker's template skin (an AO-shaded white sheet) if there is one, else the car's lightest skin;
  panels  - the islands of the sheet; mirrored pairs (left / right side) found by flipping;
  paint   - pattern + colours on the panels, times the source's own shading; carbon / see-through parts (alpha) and
            the background are left exactly as they are;
  decals  - number, team, driver name and logos placed on the sheet (texture pixels); one on a paired panel is copied
            onto its mirror panel, turned 180 degrees so it reads the right way there.

Nothing of the protected model is read except names (which texture is the paint) - never its mapping or data."""
import os, re
import numpy as np
from PIL import Image, ImageDraw, ImageOps

# a maker's template skin: 'template' / 'blank' anywhere, or a skin called just 'white' / 'plain' (not race liveries
# such as '2_white_red' or 'GR_Racing_Red_White')
TEMPLATE_RE = re.compile(r'template|blank|^[\W_]*(?:new\s*)?(?:plain|white|plain\s*white|base)[\W_]*$', re.I)
# a template skin's working files: never copied into a new skin
SKIP_COPY_RE = re.compile(r'\.(psd|xcf|pdf|txt|ai|kra|svg|pdn|tif|tiff)$|wire.?frame|template|alpha.?for|_mask\.|readme', re.I)
_MEMO = {}


# ------------------------------------------------------------------ islands
def runs_of(mask):
    m = np.pad(mask.astype(np.int8), ((0, 0), (1, 1)))
    d = np.diff(m, axis=1)
    r, s = np.nonzero(d == 1)
    _, e = np.nonzero(d == -1)
    return r, s, e


def label(mask):
    """8-connected islands of a mask: run-based union-find (about half a second for 2048 x 2048)."""
    H, W = mask.shape
    r, s, e = runs_of(mask)
    n = len(r)
    if n == 0: return np.zeros(mask.shape, np.int32), 0
    big = W + 4
    ks, ke = r * big + s, r * big + e
    j = np.nonzero(r > 0)[0]
    lo = np.searchsorted(ke, (r[j] - 1) * big + s[j] - 1, 'right')
    hi = np.searchsorted(ks, (r[j] - 1) * big + e[j] + 1, 'left')
    cnt = np.maximum(hi - lo, 0)
    u = np.repeat(j, cnt)
    v = np.repeat(lo, cnt) + (np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    lab = np.arange(n)
    while len(u):
        prev = lab.copy()
        m = np.minimum(lab[u], lab[v])
        for w in (u, v, lab[u], lab[v]): np.minimum.at(lab, w, m)
        while True:
            nxt = lab[lab]
            if np.array_equal(nxt, lab): break
            lab = nxt
        if np.array_equal(lab, prev): break
    uniq, comp = np.unique(lab, return_inverse=True)
    comp = comp.ravel() + 1
    out = np.zeros(H * W, np.int32)
    lens = e - s
    idx = np.repeat(r * W + s, lens) + (np.arange(lens.sum()) - np.repeat(np.cumsum(lens) - lens, lens))
    out[idx] = np.repeat(comp, lens)
    return out.reshape(H, W), len(uniq)


# ------------------------------------------------------------------ the source sheet
def find_source(car, tex):
    """(skin, RGBA image) to paint over: the maker's template skin (white / AO-shaded, e.g. the Ferrari 296 GT3's
    "Template"). None when the car has none: a race livery as the base let its lettering show through and its alpha
    hide panels (McLaren 570S GT4, 17 Nov) - such cars keep the plain colour."""
    from skingen import find_skin_file, load_image, app_made
    cands = []
    for s_ in sorted(os.listdir(os.path.join(car.dir, 'skins'))):
        if app_made(car.dir, s_) or not TEMPLATE_RE.search(s_) or 'carbon' in s_.lower(): continue
        f = find_skin_file(os.path.join(car.dir, 'skins', s_), tex)
        if f: cands.append((s_, f))
    if not cands: return None
    best = None
    for s_, f in cands:
        try: im = load_image(f)
        except Exception: continue
        sm = np.asarray(im.convert('RGB').resize((256, 256))).astype(np.float32)
        lum = sm @ [0.299, 0.587, 0.114]
        on = lum > 20
        if on.mean() < 0.05: continue
        sat = (sm.max(2) - sm.min(2))[on].mean()
        score = np.median(lum[on]) - 1.5 * sat                  # the whitest, plainest template
        if best is None or score > best[0]: best = (score, s_, im)
    return (best[1], best[2].convert('RGBA')) if best else None


class Sheet:
    """The source sheet worked out: shading, paint mask, islands and mirrored pairs."""

    def __init__(self, img):
        a = np.asarray(img.convert('RGBA'))
        self.H, self.W = a.shape[:2]
        self.alpha = a[..., 3].copy()
        rgb = a[..., :3].astype(np.float32)
        self.rgb = rgb
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        border = np.concatenate([lum[0], lum[-1], lum[:, 0], lum[:, -1]])
        bg = float(np.median(border))
        uses_alpha = (self.alpha < 8).mean() > 0.01 and (self.alpha > 200).mean() > 0.05
        self.paint = (lum > bg + 12) & ((self.alpha > 8) if uses_alpha else True)
        ref = np.percentile(lum[self.paint], 95) if self.paint.any() else 255
        self.S = np.clip(lum / max(ref, 1), 0, 1.15)
        # panels: islands of the paint (on a half-size copy for speed, then scaled back)
        half = self.paint[::2, ::2]
        lab, n = label(half)
        self.lab = np.kron(lab, np.ones((2, 2), np.int32))[:self.H, :self.W] * self.paint
        self.islands = {}
        tot = self.paint.sum()
        areas = np.bincount(lab.ravel(), minlength=n + 1) * 4
        for i in np.nonzero(areas > 0.004 * max(tot, 1))[0]:
            if i == 0: continue
            ys, xs = np.nonzero(lab == i)
            self.islands[int(i)] = dict(area=int(areas[i]), x0=int(xs.min()) * 2, x1=int(xs.max()) * 2 + 1,
                                        y0=int(ys.min()) * 2, y1=int(ys.max()) * 2 + 1,
                                        cx=float(xs.mean()) * 2, cy=float(ys.mean()) * 2)
        self.pairs = self._pairs(lab)

    def _pairs(self, lab):
        """Islands that are mirror images of each other (the car's left and right panels): {i: (j, 'v' | 'h')}."""
        def shape(i, flip=None):
            b = self.islands[i]
            m = lab[b['y0'] // 2:b['y1'] // 2 + 1, b['x0'] // 2:b['x1'] // 2 + 1] == i
            im = Image.fromarray(m.astype(np.uint8) * 255)
            if flip == 'v': im = ImageOps.flip(im)
            if flip == 'h': im = ImageOps.mirror(im)
            return np.asarray(im.resize((48, 48))) > 127
        out, ids = {}, sorted(self.islands, key=lambda k: -self.islands[k]['area'])
        for a_ in ids:
            if a_ in out: continue
            for b_ in ids:
                if b_ == a_ or b_ in out: continue
                A, B = self.islands[a_], self.islands[b_]
                if not 0.85 < A['area'] / B['area'] < 1.18: continue
                sb = shape(b_)
                for fl in ('v', 'h'):
                    sa = shape(a_, fl)
                    iou = (sa & sb).sum() / max(1, (sa | sb).sum())
                    if iou > 0.8:
                        out[a_] = (b_, fl); out[b_] = (a_, fl); break
                if a_ in out: break
        return out

    def island_at(self, u, v):
        u = int(np.clip(u, 0, self.W - 1)); v = int(np.clip(v, 0, self.H - 1))
        i = int(self.lab[v, u])
        if i in self.islands: return i
        # nearest island centre
        return min(self.islands, key=lambda k: (self.islands[k]['cx'] - u) ** 2 + (self.islands[k]['cy'] - v) ** 2) if self.islands else 0

    def mirror(self, i, u, v):
        """Where (u, v) on island i lands on its mirror island: (j, u', v') or None."""
        return mirror_pos(self.islands, self.pairs, i, u, v)


def mirror_pos(islands, pairs, i, u, v):
    """Where (u, v) on island i lands on its mirror island: (j, u', v') or None. (Also used by the app while a decal
    is dragged: islands / pairs as in the preview's info, keys may be strings.)"""
    if not islands or not pairs: return None
    get = lambda m, k: m.get(k, m.get(str(k)))
    pr = get(pairs, i)
    if not pr: return None
    j, fl = pr
    A, B = get(islands, i), get(islands, j)
    if A is None or B is None: return None
    fu = (u - A['x0']) / max(1, A['x1'] - A['x0']); fv = (v - A['y0']) / max(1, A['y1'] - A['y0'])
    if fl == 'v': fv = 1 - fv
    else: fu = 1 - fu
    return j, B['x0'] + fu * (B['x1'] - B['x0']), B['y0'] + fv * (B['y1'] - B['y0'])


def sheet_for(car, tex):
    """The worked-out source sheet of this car's paint texture (kept while the same car is used)."""
    key = (car.dir, tex)
    if _MEMO.get('key') != key:
        src = find_source(car, tex)
        _MEMO.clear()
        _MEMO['key'] = key
        _MEMO['src'] = src
        _MEMO['sheet'] = Sheet(src[1]) if src else None
    return _MEMO['src'], _MEMO['sheet']


# ------------------------------------------------------------------ painting
def pattern_layer(sheet, design, pattern_colours, swatch_car):
    """The pattern over the whole sheet in texture space (kept while the pattern and colours stay the same)."""
    keys = ('pattern', 'base', 'accent', 'accent2', 'text', 'halftone', 'carbon', 'pattern_image', 'pattern_mode',
            'pattern_simplify', 'pattern_recolour')
    k = ('pat', id(sheet)) + tuple(str(design.get(x)) for x in keys)
    if _MEMO.get('pat_key') == k: return _MEMO['pat']
    H, W = sheet.H, sheet.W
    sel = np.flatnonzero(sheet.paint.ravel())
    vv, uu = np.divmod(sel, W)
    u, v = uu / W, vv / H
    P = np.stack([np.full(len(sel), 0.86, np.float32), (1 - v) * 2.6, (0.5 - u) * 5.2], 1).astype(np.float32)
    N = np.tile(np.array([1.0, 0, 0], np.float32), (len(sel), 1))
    col = np.zeros((H * W, 3), np.float32)
    for c0 in range(0, len(sel), 1 << 20):
        sl = slice(c0, c0 + (1 << 20))
        col[sel[sl]] = pattern_colours(dict(design, pattern_image=design.get('pattern_image')), P[sl], N[sl], swatch_car,
                                       0.15, 0.8, lambda m: None)
    col = col.reshape(H, W, 3)
    _MEMO['pat_key'], _MEMO['pat'] = k, col
    return col


def shade(sheet, col):
    """Colours times the source's own shading (highlights roll a little towards white); outside the paint the source
    stays exactly as it was."""
    S = sheet.S[..., None]
    painted = col * np.minimum(S, 1) + (255 - col) * np.clip(S - 1, 0, None) * 0.6
    out = np.where(sheet.paint[..., None], painted, sheet.rgb)
    return np.clip(out, 0, 255).astype(np.uint8)


def default_decals(sheet, design, front=0):
    """Where the number, names and logos go before the user moves them: the number (team above it, driver name under
    it) on the biggest mirrored panel - the lower / left one of the pair upright, its mirror copy turned - and the logos
    on the biggest panel that has no mirror (the roof or bonnet), turned to the front the user chose."""
    out = []
    # the car's two sides are usually laid out one above the other, mirrored top to bottom (as on the 296's race skins
    # and the Talbot): those pairs first, biggest first
    pairs = sorted((i for i in sheet.islands if i in sheet.pairs),
                   key=lambda k: (sheet.pairs[k][1] != 'v', -sheet.islands[k]['area']))
    single = [i for i in sorted(sheet.islands, key=lambda k: -sheet.islands[k]['area']) if i not in sheet.pairs]
    if pairs:
        i = pairs[0]; j, fl = sheet.pairs[i]
        A, B = sheet.islands[i], sheet.islands[j]
        # the lower (vertical pair) / left (side by side) one is upright
        main = i if ((fl == 'v' and A['cy'] > B['cy']) or (fl == 'h' and A['cx'] < B['cx'])) else j
        I = sheet.islands[main]
        short = min(I['x1'] - I['x0'], I['y1'] - I['y0'])
        cx, cy = I['cx'], I['cy']
        nh = short * 0.34
        if design.get('number') and design.get('number_style') != 'none':
            out.append(dict(key='2d:number', kind='number', u=cx, v=cy, h=nh, rot=0.0))
        if design.get('team'):
            out.append(dict(key='2d:team', kind='team', u=cx, v=cy - nh * 0.85, h=nh * 0.32, rot=0.0))
        if design.get('name'):
            out.append(dict(key='2d:name', kind='name', u=cx, v=cy + nh * 0.8, h=nh * 0.24, rot=0.0))
    logos = [l for l in (design.get('logos') or [])]
    seen = []
    for l in logos:
        if l['path'] not in seen: seen.append(l['path'])
    if seen and (single or pairs):
        I = sheet.islands[single[0] if single else pairs[0]]
        short = min(I['x1'] - I['x0'], I['y1'] - I['y0'])
        h = short * 0.45 / max(1, len(seen) ** 0.5)
        for k, p in enumerate(seen):
            off = (k - (len(seen) - 1) / 2) * h * 1.1
            out.append(dict(key='2d:logo:' + os.path.basename(p), kind='logo', path=p, u=I['cx'] + off, v=I['cy'], h=h,
                            rot=float(front)))
    return out


def decal_sprite(d, design, text_image, prep_logo, rgb, fonts):
    """The picture of one decal (RGBA, upright)."""
    txt_col = tuple(int(x) for x in rgb(design.get('text') or '#ffffff'))
    dark = sum(txt_col) / 3 > 128
    outline = (16, 16, 16) if dark else (240, 240, 240)
    if d['kind'] == 'number':
        num = str(design.get('number'))
        t = text_image(num, 240, (17, 17, 17), fonts.get('number'))
        if design.get('number_style') == 'plain':
            return text_image(num, 240, txt_col, fonts.get('number'), stroke=0.05, stroke_color=outline)
        w, h = int(max(t.width * 1.25, 300)), 300
        b = Image.new('RGBA', (w, h), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        acc = tuple(int(x) for x in rgb(design.get('accent2') or '#ffffff'))
        bd.rounded_rectangle([0, 0, w - 1, h - 1], 36, fill=(250, 250, 250, 255), outline=acc + (255,), width=10)
        t.thumbnail((int(w * 0.86), int(h * 0.8)), Image.LANCZOS)
        b.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
        return b
    if d['kind'] in ('team', 'name'):
        words = design.get('team' if d['kind'] == 'team' else 'name') or ''
        return text_image(words, 200, txt_col, fonts.get(d['kind']), stroke=0.06, stroke_color=outline)
    if d['kind'] == 'logo':
        return prep_logo(d['path']).convert('RGBA')
    return Image.new('RGBA', (2, 2))


def apply_adjust(decals, adjust):
    """The user's moves (texture pixels: u, v; scale; rot; deleted) over the defaults."""
    out = []
    for d in decals:
        ad = (adjust or {}).get(d['key'], {})
        if ad.get('deleted'): continue
        d = dict(d)
        if 'u' in ad: d['u'] = ad['u']
        if 'v' in ad: d['v'] = ad['v']
        d['h'] *= ad.get('scale', 1.0)
        d['rot'] = (d['rot'] + ad.get('rot', 0.0)) % 360
        out.append(d)
    return out


def room(sheet, u, v, rot):
    """How long the panel under (u, v) runs along the decal's own direction (pixels): its width at that row (decal
    level or upside down) or its height at that column (turned a quarter)."""
    i = sheet.island_at(u, v)
    u = int(np.clip(u, 0, sheet.W - 1)); v = int(np.clip(v, 0, sheet.H - 1))
    line = (sheet.lab[:, u] if round(rot / 90) % 2 else sheet.lab[v]) == i
    at = v if round(rot / 90) % 2 else u
    if not line[at]: return int(line.sum())
    a = at
    while a > 0 and line[a - 1]: a -= 1
    b = at
    while b < len(line) - 1 and line[b + 1]: b += 1
    return b - a + 1


def place(sheet, col_img, d, sprite, clip=True):
    """Paint one decal onto the colour layer (RGBA float array H x W x 3 in col_img): scaled to its height, turned, kept
    on its own panel. Returns its box (u, v, w, h, rot, island)."""
    h = max(4, int(d['h']))
    w = max(4, int(sprite.width * h / max(1, sprite.height)))
    sp = sprite.resize((w, h), Image.LANCZOS)
    if d['rot']: sp = sp.rotate(d['rot'], expand=True, resample=Image.BICUBIC)
    x0, y0 = int(d['u'] - sp.width / 2), int(d['v'] - sp.height / 2)
    isl = sheet.island_at(d['u'], d['v'])
    own = int(sheet.lab[int(np.clip(d['v'], 0, sheet.H - 1)), int(np.clip(d['u'], 0, sheet.W - 1))])
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(sheet.W, x0 + sp.width), min(sheet.H, y0 + sp.height)
    if xb <= xa or yb <= ya: return (d['u'], d['v'], w, h, d['rot'], isl)
    a = np.asarray(sp).astype(np.float32)[ya - y0:yb - y0, xa - x0:xb - x0]
    al = a[..., 3:4] / 255
    if clip:      # kept on its own panel; one put between panels shows on whatever paint is under it
        keep = (sheet.lab[ya:yb, xa:xb] == own) if own in sheet.islands else sheet.paint[ya:yb, xa:xb]
        al = al * keep[..., None]
    region = col_img[ya:yb, xa:xb]
    col_img[ya:yb, xa:xb] = region * (1 - al) + a[..., :3] * al
    return (d['u'], d['v'], w, h, d['rot'], isl)


def paint(car, tex, design, log, pattern_colours, swatch_car, text_image, prep_logo, rgb, fonts):
    """The livery painted on the sheet: (RGBA image, info dict) or None when the car has no usable sheet."""
    src, sheet = sheet_for(car, tex)
    if not src or sheet is None or not sheet.islands:
        return None
    skin, img = src
    log(f'2D mode: painting the paint sheet of the skin "{skin}" ({sheet.W}x{sheet.H}, {len(sheet.islands)} panels, '
        f'{len(sheet.pairs) // 2} mirrored pairs)')
    col = pattern_layer(sheet, design, pattern_colours, swatch_car).copy()
    clean = shade(sheet, col)
    adj = design.get('adjust') or {}
    front = (adj.get('2d:front') or {}).get('rot', 0)
    decals = apply_adjust(default_decals(sheet, design, front), adj)
    boxes = []
    for d in decals:
        try: sp = decal_sprite(d, design, text_image, prep_logo, rgb, fonts)
        except Exception as e:
            log(f'2D mode: {d["key"]} left off ({e})'); continue
        if 'scale' not in adj.get(d['key'], {}):        # not sized by hand: it fits across its panel
            fit = 0.88 * room(sheet, d['u'], d['v'], d['rot']) / max(1, sp.width / max(1, sp.height))
            if fit < d['h']: d = dict(d, h=fit)
        u, v, w, h, rot, isl = place(sheet, col, d, sp)
        mir = sheet.mirror(isl, u, v)
        twin = None
        if mir:                                  # the mirror panel: same place, turned 180 so it reads right there
            j, u2, v2 = mir
            twin = place(sheet, col, dict(d, u=u2, v=v2, rot=(rot + 180) % 360), sp)
        thumb = sp.copy(); thumb.thumbnail((512, 512))
        boxes.append(dict(key=d['key'], label=d['kind'], u=u, v=v, w=w, h=h, rot=rot, island=isl, sprite=thumb,
                          twin=list(twin[:5]) if twin else None))
    out = shade(sheet, col)
    rgba = np.dstack([out, sheet.alpha])
    image = Image.fromarray(rgba, 'RGBA')
    info = dict(mode='2d', source_skin=skin, size=(sheet.W, sheet.H), decals2d=boxes, front=front,
                islands2d={i: {k: sheet.islands[i][k] for k in ('x0', 'x1', 'y0', 'y1')} for i in sheet.islands},
                pairs2d=dict(sheet.pairs),
                sheet=image, sheet_clean=Image.fromarray(np.dstack([clean, sheet.alpha]), 'RGBA'))
    return image, info


def ini_number(text, number):
    """A copied ext_config.ini: an LED number panel's text role shows the new number."""
    if not number: return text
    return re.sub(r'(?im)^(\s*ROLE_\d+_TEXT\s*=\s*)\S+', lambda m: m.group(1) + str(number), text)
