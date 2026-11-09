"""AC Skin Generator core - no AI, works from the car's own 3D model.

Pipeline
  1. read the car's kn5, find the skin-overridable body texture(s)
  2. rasterise every triangle that uses a body texture into texture space,
     storing each texel's 3D position and surface normal
  3. paintable texels = texels that differ between the car's stock skins
     (lights / grilles / interior are identical in every skin and are kept)
  4. the design is defined in CAR space (side view, top view, front, rear),
     so writing reads correctly on both sides whatever the UV layout does
  5. write a new skin folder (mipmapped DDS + ui_skin.json + livery.png)

AC axes: +X = car's left, +Y = up, +Z = forward (right-handed).
"""
import glob, io, json, os, re, shutil, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageColor

from kn5 import KN5

Image.MAX_IMAGE_PIXELS = None
FONT_DIR = r"C:\Windows\Fonts"
APP_NAME = "Ratty's4Skin Generator"
DEFAULT_FONT = next((f for f in (os.path.join(FONT_DIR, n) for n in ("bahnschrift.ttf", "arialnb.ttf", "arialbd.ttf"))
                     if os.path.isfile(f)), "arial.ttf")

# ------------------------------------------------------------------ helpers
def _lum(c):
    c = np.asarray(c, np.float64) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable(colour, background, *alternatives):
    """`colour` if it stands out on `background`, else the best of the alternatives / black / white."""
    if contrast(colour, background) >= 2.5: return np.asarray(colour, np.float32)
    cands = [np.asarray(c, np.float32) for c in alternatives] + [np.array([15, 15, 18], np.float32), np.array([245, 245, 245], np.float32)]
    return max(cands, key=lambda c: contrast(c, background))


def rgb(c):
    return np.array(ImageColor.getrgb(c)[:3], np.float32) if isinstance(c, str) else np.array(c[:3], np.float32)


def find_main_kn5(car_dir):
    name = os.path.basename(os.path.normpath(car_dir))
    p = os.path.join(car_dir, name + '.kn5')
    if os.path.isfile(p): return p
    ks = [k for k in glob.glob(os.path.join(car_dir, '*.kn5'))
          if not re.search(r'collider|_lod_?[b-z]|lod[1-9]|cockpit_lr|driver', os.path.basename(k), re.I)]
    if not ks: raise FileNotFoundError('no kn5 model in ' + car_dir)
    return max(ks, key=os.path.getsize)


def stock_skins(car_dir):
    d = os.path.join(car_dir, 'skins')
    return sorted([s for s in os.listdir(d) if os.path.isdir(os.path.join(d, s))]) if os.path.isdir(d) else []


def find_skin_file(skin_dir, texname):
    want = texname.lower()
    for f in os.listdir(skin_dir):
        if f.lower() == want: return os.path.join(skin_dir, f)
    return None


def fast_dds(data):
    """Uncompressed DDS (bitmask formats) straight into numpy; None if compressed."""
    if data[:4] != b'DDS ': return None
    h, w = struct.unpack_from('<II', data, 12)
    pf_flags, fourcc, bits = struct.unpack_from('<I4sI', data, 80)
    if pf_flags & 0x4 or bits not in (24, 32): return None
    masks = struct.unpack_from('<4I', data, 92)
    n = w * h * bits // 8
    raw = np.frombuffer(data, np.uint8, n, 128)
    if bits == 32: px = raw.view('<u4').reshape(h, w)
    else:
        b3 = raw.reshape(h, w, 3).astype(np.uint32); px = b3[..., 0] | (b3[..., 1] << 8) | (b3[..., 2] << 16)
    out = np.zeros((h, w, 4), np.uint8)
    for c, m in enumerate(masks):
        if m == 0:
            out[..., c] = 255 if c == 3 else 0; continue
        sh = (m & -m).bit_length() - 1
        out[..., c] = ((px & m) >> sh) * 255 // (m >> sh)
    if not (pf_flags & 0x1): out[..., 3] = 255
    return Image.fromarray(out, 'RGBA')


def load_image(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else open(path_or_bytes, 'rb').read()
    im = fast_dds(data)
    if im is not None: return im
    if data[:4] == b'DDS ' and data[84:88] == b'DX10' and len(data) > 132:
        # sRGB variants hold the same pixel data as the plain formats Pillow knows: relabel them
        fmt = struct.unpack_from('<I', data, 128)[0]
        plain = {72: 71, 75: 74, 78: 77, 99: 98, 29: 28, 91: 87, 93: 88}.get(fmt)
        if plain:
            data = bytearray(data); struct.pack_into('<I', data, 128, plain); data = bytes(data)
    path_or_bytes = data
    im = Image.open(io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes)
    return im.convert('RGBA')


def tri_area3(m):
    a, b, c = m.pos[m.idx[:, 0]], m.pos[m.idx[:, 1]], m.pos[m.idx[:, 2]]
    return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)


# ------------------------------------------------------------------ car analysis
class Car:
    """Everything the generator needs to know about one car."""

    def __init__(self, car_dir, log=print):
        self.dir = car_dir
        self.log = log
        self.kn5_path = find_main_kn5(car_dir)
        self.kn5 = KN5(self.kn5_path)
        # skins made by this tool are left out of the stock-skin comparison
        self.skins = [s for s in stock_skins(car_dir) if not os.path.exists(os.path.join(car_dir, 'skins', s, 'generator_preview.png'))]
        self._find_body_textures()

    def _find_body_textures(self):
        """Body textures = txDiffuse textures that skins override, ranked by 3D area."""
        area = {}
        wheelish = re.compile(r'WHEEL_|SUSP_|HUB_|DISC_|rim|tyre|tire', re.I)
        for m in self.kn5.meshes:
            if m.mat is None or not len(m.idx): continue
            if any(wheelish.search(p) for p in m.parents) or wheelish.search(m.name): continue
            t = m.mat.samplers.get('txDiffuse')
            if t: area[t] = area.get(t, 0) + tri_area3(m).sum()
        warea = {}
        for m in self.kn5.meshes:
            if m.mat is None or not len(m.idx): continue
            if any(wheelish.search(p) for p in m.parents) or wheelish.search(m.name):
                t = m.mat.samplers.get('txDiffuse')
                if t: warea[t] = warea.get(t, 0) + tri_area3(m).sum()
        self.wheel_textures = [t for t in sorted(warea, key=lambda t: -warea[t])
                               if t not in area and any(find_skin_file(os.path.join(self.dir, 'skins', s), t) for s in self.skins)]
        if self.wheel_textures: self.log('wheel textures (optional recolour): ' + ', '.join(self.wheel_textures))
        overridable = {}
        for t in area:
            n = sum(1 for s in self.skins if find_skin_file(os.path.join(self.dir, 'skins', s), t))
            if n: overridable[t] = n
        if not overridable:
            # skins can override any texture inside the kn5 by file name: use the paint material's own texture
            paintish = re.compile(r'paint|body|carpaint|skin|livery|ext_', re.I)
            cand = {}
            for m in self.kn5.meshes:
                if m.mat is None or not len(m.idx): continue
                t = m.mat.samplers.get('txDiffuse')
                if t in area and paintish.search(m.mat.name + ' ' + t) and t in self.kn5.textures:
                    cand[t] = area[t]
            if not cand:
                raise RuntimeError('no paintable body texture found in this car')
            overridable = {max(cand, key=cand.get): 0}     # only the main paint texture
            self.log('no stock skin overrides the body texture - using the one inside the model')
        best = max(area[t] for t in overridable)
        cands = sorted([t for t in overridable if area[t] > 0.15 * best], key=lambda t: -area[t])
        self.body_textures = cands[:1] + [t for t in cands[1:] if self._tex_size(t) >= 256]
        for t in cands[1:]:
            if t not in self.body_textures: self.log(f'{t}: only a small colour swatch - left as it is')
        self.tex_area = area
        self.log('body textures: ' + ', '.join(f'{t} ({area[t]:.1f} m²)' for t in self.body_textures))
        body = [m for m in self.kn5.meshes if m.mat is not None and m.mat.samplers.get('txDiffuse') in self.body_textures]
        P = np.concatenate([m.pos for m in body])
        lo, hi = np.percentile(P, 0.5, axis=0), np.percentile(P, 99.5, axis=0)
        self.lo, self.hi = lo, hi
        self.length = hi[2] - lo[2]
        self.wheels = {}
        for m in self.kn5.meshes:
            for w in ('WHEEL_LF', 'WHEEL_RF', 'WHEEL_LR', 'WHEEL_RR'):
                if w in m.parents and len(m.pos):
                    self.wheels.setdefault(w, []).append(m.pos)
        self.wheel_r = float(np.mean([(np.concatenate(v)[:, 1].max() - np.concatenate(v)[:, 1].min()) / 2
                                       for v in self.wheels.values()])) if self.wheels else 0.33
        self.wheels = {w: (np.concatenate(v).min(0) + np.concatenate(v).max(0)) / 2 for w, v in self.wheels.items()}
        if self.wheels:
            self.log('wheels found: ' + ', '.join(f'{w} z={c[2]:+.2f}' for w, c in self.wheels.items()))
        self.log(f'body size: {hi[0]-lo[0]:.2f} m wide, {hi[1]-lo[1]:.2f} m tall, {self.length:.2f} m long')

    def _tex_size(self, tex):
        for s in self.skins:
            f = find_skin_file(os.path.join(self.dir, 'skins', s), tex)
            if f:
                try:
                    h = open(f, 'rb').read(20)
                    if h[:4] == b'DDS ': return max(struct.unpack_from('<II', h, 12))
                    return max(Image.open(f).size)
                except Exception: pass
        if tex in self.kn5.textures:
            try: return max(load_image(self.kn5.textures[tex]).size)
            except Exception: pass
        return 0

    def meshes_for(self, tex):
        return [m for m in self.kn5.meshes if m.mat is not None and m.mat.samplers.get('txDiffuse') == tex and len(m.idx)]

    def stock_texture(self, tex, skin):
        f = find_skin_file(os.path.join(self.dir, 'skins', skin), tex)
        if not f: return None
        try:
            return load_image(f)
        except Exception as e:      # one odd file must not stop the whole skin
            self.log(f'skipped {skin}/{os.path.basename(f)}: cannot read it ({e})')
            return None


# ------------------------------------------------------------------ texture-space rasteriser
class TexelMap:
    """Per-texel 3D position / normal for one body texture."""

    def __init__(self, meshes, W, H, log=print):
        self.W, self.H = W, H
        pos, nrm, uv, mid = [], [], [], []
        for m in meshes:
            t = m.idx
            pos.append(m.pos[t]); nrm.append(m.nrm[t]); uv.append(m.uv[t])
            mid += [m.name] * len(t)
        pos = np.concatenate(pos); nrm = np.concatenate(nrm); uv = np.concatenate(uv)
        uv = uv - np.floor(uv.min(1, keepdims=True))          # bring tiled triangles into 0..1
        self.mesh_of_tri = np.array(mid)
        px = np.stack([uv[..., 0] * W - 0.5, uv[..., 1] * H - 0.5], -1)

        def draw(order):
            # interiors first; edge pixels only where no triangle covers the texel centre
            im = Image.new('I', (W, H), -1); d = ImageDraw.Draw(im)
            ed = Image.new('I', (W, H), -1); de = ImageDraw.Draw(ed)
            for i in order:
                q = [tuple(p) for p in px[i]]
                d.polygon(q, fill=int(i))
                de.polygon(q, outline=int(i))
            a = np.asarray(im, dtype=np.int64).copy(); e = np.asarray(ed, dtype=np.int64)
            a[a < 0] = e[a < 0]
            return a

        # texture-space area of each triangle; slivers (near zero area, long in 3D) would map
        # whole texel rows to the wrong place, so they are left out
        pa = 0.5 * np.abs((px[:, 1, 0] - px[:, 0, 0]) * (px[:, 2, 1] - px[:, 0, 1]) -
                          (px[:, 2, 0] - px[:, 0, 0]) * (px[:, 1, 1] - px[:, 0, 1]))
        e = np.stack([np.linalg.norm(px[:, i] - px[:, (i + 1) % 3], axis=1) for i in range(3)], 1).max(1)
        width = 2 * pa / np.maximum(e, 1e-9)                       # thinnest height in texels
        a3 = 0.5 * np.linalg.norm(np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0]), axis=1)
        dens = a3 / np.maximum(pa, 1e-9)                            # m² per texel
        med = np.median(dens[pa > 1])
        keep = np.nonzero((pa > 0.3) & ~((width < 1.5) & (dens > 2.5 * med)))[0]
        keep = keep[np.argsort(width[keep], kind='stable')]        # thin first, solid panels drawn over them
        ida = draw(keep)
        idb = draw(keep[::-1])
        self.covered = ida >= 0
        self.shared = self.covered & (ida != idb)               # two triangles use the same texels
        tid = ida
        yy, xx = np.nonzero(self.covered)
        t = tid[yy, xx]
        a, b, c = px[t, 0], px[t, 1], px[t, 2]
        p = np.stack([xx, yy], -1).astype(np.float64)
        v0, v1, v2 = b - a, c - a, p - a
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        den[np.abs(den) < 1e-12] = 1e-12
        w1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
        w2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        w0 = 1 - w1 - w2
        out = (w0 < 0) | (w1 < 0) | (w2 < 0)
        if out.any():
            # texel centre outside its (edge-pass) triangle: use the closest point on the triangle
            o = np.nonzero(out)[0]
            pts = p[o]; A_, B_, C_ = a[o], b[o], c[o]
            best_d = np.full(len(o), np.inf); bw = np.zeros((len(o), 3))
            for (P0, P1, i0, i1) in ((A_, B_, 0, 1), (B_, C_, 1, 2), (C_, A_, 2, 0)):
                e = P1 - P0; l2 = np.maximum((e ** 2).sum(1), 1e-12)
                tt = np.clip(((pts - P0) * e).sum(1) / l2, 0, 1)
                q = P0 + e * tt[:, None]; dd = ((pts - q) ** 2).sum(1)
                better = dd < best_d
                best_d[better] = dd[better]
                ww = np.zeros((len(o), 3)); ww[np.arange(len(o)), i0] = 1 - tt; ww[np.arange(len(o)), i1] += tt
                bw[better] = ww[better]
            w0[o], w1[o], w2[o] = bw[:, 0], bw[:, 1], bw[:, 2]
        P = pos[t, 0] * w0[:, None] + pos[t, 1] * w1[:, None] + pos[t, 2] * w2[:, None]
        N = nrm[t, 0] * w0[:, None] + nrm[t, 1] * w1[:, None] + nrm[t, 2] * w2[:, None]
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        self.yy, self.xx, self.P, self.N, self.tri = yy, xx, P, N, t
        a3 = 0.5 * np.linalg.norm(np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0]), axis=1).sum()
        self.texel_m = float(np.sqrt(a3 / max(1, len(yy))))     # metres per texel (average)
        share = self.shared.sum() / max(1, self.covered.sum())
        log(f'texture {W}x{H}: {self.covered.mean()*100:.0f}% of texels on the body, {share*100:.1f}% shared by two surfaces')


# ------------------------------------------------------------------ views (car space -> 2D, as a person sees it)
#   a = rightwards in the viewer's picture, b = upwards (metres)
VIEWS = {
    #            view dir (towards the viewer)   a(P)            b(P)
    'left':  (np.array([1, 0, 0]),  lambda P: -P[:, 2], lambda P: P[:, 1]),
    'right': (np.array([-1, 0, 0]), lambda P: P[:, 2],  lambda P: P[:, 1]),
    'front': (np.array([0, 0, 1]),  lambda P: P[:, 0],  lambda P: P[:, 1]),
    'rear':  (np.array([0, 0, -1]), lambda P: -P[:, 0], lambda P: P[:, 1]),
    # bonnet / boot: read standing in front of the car looking back over it
    'top':   (np.array([0, 1, 0]),  lambda P: P[:, 0],  lambda P: -P[:, 2]),
    # roof: read from the car's left side
    'roof_l': (np.array([0, 1, 0]), lambda P: -P[:, 2], lambda P: -P[:, 0]),
}


def text_image(text, px_height, color, font_path=DEFAULT_FONT, style='Bold Condensed', track=0.04,
               stroke=0, stroke_color=(0, 0, 0)):
    f = ImageFont.truetype(font_path, max(8, int(px_height)))
    try: f.set_variation_by_name(style)
    except Exception: pass
    tr = track * px_height
    w = int(sum(f.getlength(ch) for ch in text) + tr * len(text) + px_height)
    im = Image.new('RGBA', (w, int(px_height * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = px_height * 0.3
    sw = int(stroke * px_height)
    for ch in text:
        d.text((x, px_height * 0.2), ch, font=f, fill=tuple(int(v) for v in color) + (255,),
               stroke_width=sw, stroke_fill=tuple(int(v) for v in stroke_color) + (255,))
        x += f.getlength(ch) + tr
    bb = im.getbbox()
    return im.crop(bb) if bb else im


def prep_logo(path, tint=None, bg='auto'):
    """Key out the logo's background (colour taken from its border) and optionally re-tint its glow."""
    im = Image.open(path).convert('RGBA')
    a = np.asarray(im).astype(np.float32)
    rgbv = a[..., :3]
    border = np.concatenate([rgbv[0], rgbv[-1], rgbv[:, 0], rgbv[:, -1]])
    plain_bg = border.std(0).mean() < 22            # one flat background colour?
    if bg == 'auto': bg = 'remove' if plain_bg else 'keep'
    mode = bg
    if a[..., 3].min() < 250:            # already has transparency
        out = a
    elif bg == 'keep':                    # a picture: keep all of it, with softly rounded corners
        m = Image.new('L', im.size, 0)
        r = int(min(im.size) * 0.06)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=r, fill=255)
        out = np.dstack([rgbv, np.asarray(m.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)])
    else:
        bg = np.median(border, 0)
        dist = np.sqrt(((rgbv - bg) ** 2).sum(-1))
        alpha = np.clip((dist - 28) / 40, 0, 1) * 255
        out = np.dstack([rgbv, alpha])
    if tint is not None:
        hsv = np.asarray(Image.fromarray(out[..., :3].astype(np.uint8)).convert('HSV')).astype(np.float32)
        th = np.asarray(Image.new('RGB', (1, 1), tuple(int(v) for v in tint)).convert('HSV'))[0, 0, 0]
        sat = hsv[..., 1] / 255.0
        w = np.clip((sat - 0.25) / 0.3, 0, 1)
        # rotate every saturated colour so that the logo's main hue lands on the tint hue
        weights = (hsv[..., 1] * (out[..., 3] / 255.0)).ravel()
        main = np.average(hsv[..., 0].ravel(), weights=weights + 1e-6) if weights.sum() > 0 else th
        hist, _ = np.histogram(hsv[..., 0].ravel(), bins=32, range=(0, 256), weights=weights)
        main = (np.argmax(hist) + 0.5) * 8
        dh = np.abs(((hsv[..., 0] - main + 128) % 256) - 128)
        w = w * np.clip((40 - dh) / 15, 0, 1)
        hsv[..., 0] = np.where(w > 0, (hsv[..., 0] + (th - main)) % 256, hsv[..., 0])
        rgbt = np.asarray(Image.fromarray(hsv.astype(np.uint8), 'HSV').convert('RGB')).astype(np.float32)
        out = np.dstack([out[..., :3] * (1 - w[..., None]) + rgbt * w[..., None], out[..., 3]])
    # make the inside of the logo solid: only background connected to the border stays clear
    solid = Image.fromarray(((out[..., 3] > 128) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    pad = Image.new('L', (solid.width + 2, solid.height + 2), 0); pad.paste(solid, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)
    inside = np.asarray(pad)[1:-1, 1:-1] != 128
    inside = np.asarray(Image.fromarray((inside * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))
                        .filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)
    out[..., 3] = np.maximum(out[..., 3], inside)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')
    if mode == 'keep':
        img.info['picture'] = True
        return img
    bb = img.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox()
    return img.crop(bb) if bb else img


class Decal:
    def __init__(self, img, view, a, b, height, rot=0, region=None, glow=None, facing=0.35):
        self.img, self.view, self.a, self.b, self.height = img, view, a, b, height
        self.rot, self.region, self.glow, self.facing = rot, region, glow, facing


# ------------------------------------------------------------------ design
DEFAULT_DESIGN = dict(
    base='#0c0b10', accent='#7020d2', accent2='#be6eff', text='#f0eef5',
    pattern='sweep', halftone=True, carbon=False,
    logo=None, tint_logo=True, logos=None, number='101', number_style='board', number_doors=True, number_roof=True,
    name='', team='RATTY RACING', wheel_colour=None, lens_colour=None, beam_colour=None,
    win_enable=False, win_clear=True, win_banner='RATTY RACING', win_banner_colour='#111111', win_text_colour='#ffffff',
    win_number=True, win_name=True,
    font=DEFAULT_FONT,
)


def side_profile(car, tm, paint):
    """Sill and belt (window) line from side-facing texels -> door area for decals.
    The belt line is the bottom of the biggest vertical gap (the side windows) in each slice."""
    sel = (np.abs(tm.N[:, 0]) > 0.5) & paint[tm.yy, tm.xx]
    P = tm.P[sel]
    z0, z1 = car.lo[2], car.hi[2]
    nb = 40
    bins = np.linspace(z0, z1, nb + 1)
    lowv, beltv = np.full(nb, np.nan), np.full(nb, np.nan)
    for i in range(nb):
        y = np.sort(P[(P[:, 2] >= bins[i]) & (P[:, 2] < bins[i + 1]), 1])
        if len(y) < 30: continue
        lowv[i] = np.percentile(y, 2)
        ys = np.unique(np.round(y, 2))
        if len(ys) < 2: continue
        gaps = np.diff(ys)
        j = np.argmax(gaps)
        beltv[i] = ys[j] if gaps[j] > 0.12 else np.percentile(y, 98)
    zc = (bins[:-1] + bins[1:]) / 2
    mid = (zc > z0 + 0.3 * car.length) & (zc < z1 - 0.3 * car.length) & ~np.isnan(lowv)
    sill = np.nanmedian(lowv[mid]) if mid.any() else car.lo[1] + 0.15
    belt = np.nanmedian(beltv[mid]) if mid.any() else car.lo[1] + 0.55 * (car.hi[1] - car.lo[1])
    # door area: the stretch whose lower edge stays near the sill (no wheel arch)
    span = mid | ((zc > z0 + 0.15 * car.length) & (zc < z1 - 0.15 * car.length))
    ok = span & ~np.isnan(lowv) & (lowv < sill + 0.12 * (belt - sill) + 0.04)
    zs = zc[ok] if ok.any() else zc[mid]
    df, dr = zs.max(), zs.min()
    fw = [c[2] for w, c in car.wheels.items() if w.endswith('F')]
    rw = [c[2] for w, c in car.wheels.items() if w.endswith('R')]
    if fw and rw:   # doors sit between the wheel arches
        r = car.wheel_r
        df, dr = np.mean(fw) - r - 0.08, np.mean(rw) + r + 0.08
    return dict(sill=sill, belt=belt, door_front=df, door_rear=dr)


def top_panels(car, tm, paint, belt):
    """Centre z, length and width of the bonnet, roof and boot from upward-facing paint texels."""
    up = (tm.N[:, 1] > 0.6) & paint[tm.yy, tm.xx]
    P = np.c_[tm.P[up], tm.N[up, 1]]           # x, y, z, normal-y
    out = {}
    if not len(P): return out
    # keep only the uppermost surface at each point along the car (drops sills, arch lips, splitter)
    zb_all = np.floor((P[:, 2] - car.lo[2]) / 0.05).astype(int)
    half = (car.hi[0] - car.lo[0]) / 2
    centre = np.abs(P[:, 0]) < 0.4 * half
    top = np.full(zb_all.max() + 1, -1e9)
    np.maximum.at(top, zb_all[centre], P[centre, 1])
    P = P[(P[:, 1] > top[zb_all] - 0.08) & (P[:, 1] > belt - 0.3)]
    roof = P[P[:, 1] > car.hi[1] - 0.2]
    low = P[P[:, 1] < car.hi[1] - 0.25]
    mid = (car.hi[2] + car.lo[2]) / 2
    flat = low[low[:, 3] > 0.8] if low.shape[1] > 3 else low
    for name, Q in (('roof', roof), ('bonnet', flat[flat[:, 2] > mid]), ('boot', flat[flat[:, 2] < mid])):
        if len(Q) < 200: continue
        z5, z95 = np.percentile(Q[:, 2], [3, 97]); x5, x95 = np.percentile(Q[:, 0], [3, 97])
        out[name] = ((z5 + z95) / 2, z95 - z5, x95 - x5)
    return out


def render_design(car, tm, paint, design, log=print):
    """Return an (n_texels, 3) colour array for the texels in tm (car-space design)."""
    P, N = tm.P, tm.N
    base, acc, acc2, txt = (rgb(design[k]) for k in ('base', 'accent', 'accent2', 'text'))
    n = len(P)
    col = np.tile(base, (n, 1))
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    prof = side_profile(car, tm, paint)
    sill, belt = prof['sill'], prof['belt']
    zf, zr = car.hi[2], car.lo[2]
    L = car.length
    s = (zf - z) / L                                     # 0 at the front, 1 at the rear
    log(f"side panels: sill {sill:.2f} m, belt line {belt:.2f} m, doors z {prof['door_rear']:+.2f}..{prof['door_front']:+.2f}")

    if design.get('carbon'):
        u = (np.abs(x) * 0 + z + y) * 220                  # fine diagonal weave in the base colour
        col = col + (np.sin(u) > 0.6)[:, None] * 6

    pat = design.get('pattern', 'sweep')
    if pat == 'sweep':
        h0 = sill + (belt - sill) * (0.14 + 0.62 * s)       # rising from the front to the rear
        h0 = np.minimum(h0, belt - 0.02)
        t = np.clip((s - 0.05) / 0.85, 0, 1)[:, None]
        band = (y < h0)
        darkacc = acc * 0.42
        col = np.where(band[:, None], darkacc * (1 - t) + acc * t, col)
        e1 = (y >= h0 + 0.012) & (y < h0 + 0.03)
        col = np.where(e1[:, None], acc2, col)
        e2 = (y >= h0 + 0.045) & (y < h0 + 0.053)
        col = np.where(e2[:, None], acc, col)
        if design.get('halftone'):
            g = 0.032
            gz = np.round(z / g); gy = np.round(y / g)
            dz = z - gz * g; dy = y - gy * g
            d = np.sqrt(dz ** 2 + dy ** 2)
            dist = y - (h0 + 0.07)
            r = g * 0.42 * np.clip(1 - dist / 0.26, 0, 1)
            dots = (dist > 0) & (d < r) & (s < 0.7) & (np.abs(N[:, 0]) > 0.5)
            col = np.where(dots[:, None], acc, col)
    elif pat == 'stripes':
        ax = np.abs(x)
        st = ((ax > 0.06) & (ax < 0.16)) | ((ax > 0.19) & (ax < 0.215))
        st &= y > sill + 0.1
        col = np.where(st[:, None], acc, col)
        edge = (ax > 0.16) & (ax < 0.17) & (y > sill + 0.1)
        col = np.where(edge[:, None], acc2, col)
        low = y < sill + (belt - sill) * 0.22
        col = np.where(low[:, None], acc, col)
    elif pat == 'split':
        low = y < sill + (belt - sill) * 0.55
        col = np.where(low[:, None], acc, col)
        e = (y >= sill + (belt - sill) * 0.55) & (y < sill + (belt - sill) * 0.55 + 0.02)
        col = np.where(e[:, None], acc2, col)

    # ---- decals
    decals = place_decals(car, tm, paint, design, prof, base, acc, acc2, txt, log)
    col = apply_decals(col, tm, paint, decals, log)
    return np.clip(col, 0, 255)


PLACES = {
    'doors': 'Doors (big)', 'bonnet': 'Bonnet', 'front_wings': 'Front wings', 'rear_quarters': 'Rear quarters',
    'lower_doors': 'Lower doors (sill)', 'roof': 'Roof', 'boot': 'Boot lid', 'rear': 'Rear panel',
    'front': 'Front bumper', 'windscreen': 'Windscreen banner', 'rear_window': 'Rear window',
    'side_windows': 'Rear side windows',
}


def place_decals(car, tm, paint, design, prof, base, acc, acc2, txt, log):
    """Turn the design's number / names / logos into decals at places found on this car."""
    sill, belt = prof['sill'], prof['belt']
    sh = belt - sill
    zf, zr, L = car.hi[2], car.lo[2], car.length
    fnt = design.get('font') or DEFAULT_FONT
    door_len = prof['door_front'] - prof['door_rear']
    pan = top_panels(car, tm, paint, belt)
    t_txt = readable(txt, base, acc2, acc)            # writing straight on the paint
    t_acc2 = readable(acc2, base, acc, txt)
    edge = readable(acc2, txt, acc, base)             # number-board outline vs the board
    fw = [c for w, c in car.wheels.items() if w.endswith('F')]
    rw = [c for w, c in car.wheels.items() if w.endswith('R')]
    side_reg = {'left': lambda P: P[:, 0] > 0.1, 'right': lambda P: P[:, 0] < -0.1}

    def above_arch(wheels, default_z):
        z = np.mean([c[2] for c in wheels]) if wheels else default_z
        top = (np.mean([c[1] for c in wheels]) + car.wheel_r + 0.03) if wheels else sill + 0.5 * sh
        return z, top, max(belt - top, 0.08)

    def sides(z, b, h):
        return [(sd, (-z if sd == 'left' else z), b, h, side_reg[sd], 0.35, 0) for sd in ('left', 'right')]

    # every place -> list of (view, a, b, max height, region, facing, rotation)
    def geo(place):
        if place == 'doors':
            return sides(prof['door_rear'] + 0.24 * door_len, sill + 0.52 * sh, min(0.55, sh * 0.8))
        if place == 'lower_doors':
            return sides(prof['door_rear'] + 0.5 * door_len, sill + 0.11 * sh, sh * 0.13)
        if place == 'front_wings':
            z, top, room = above_arch(fw, zf - 0.2 * L)
            return sides(z, top + room * 0.55, min(room * 0.6, sh * 0.3))
        if place == 'rear_quarters':
            z, top, room = above_arch(rw, zr + 0.2 * L)
            return sides(z, top + room * 0.5, min(room * 0.75, sh * 0.35))
        if place == 'bonnet' and 'bonnet' in pan:
            zc, ln, wd = pan['bonnet']
            return [('top', 0.0, -zc, min(ln * 0.7, wd * 0.6),
                     lambda P, z0=zc - ln: (P[:, 2] > z0) & (P[:, 1] > belt - 0.15), 0.2, 0)]
        if place == 'roof' and 'roof' in pan:
            zc, ln, wd = pan['roof']
            return [('top', 0.0, -(zc - 0.28 * ln), min(wd * 0.5, ln * 0.3),
                     lambda P: P[:, 1] > car.hi[1] - 0.3, 0.3, 0)]
        if place == 'boot' and 'boot' in pan:
            zc, ln, wd = pan['boot']
            zc = zc - 0.2 * ln
            return [('top', 0.0, -zc, min(ln * 0.45, wd * 0.4),
                     lambda P, zc=zc, ln=ln: (P[:, 2] < zc + ln) & (P[:, 1] > belt - 0.15), 0.4, 180)]
        if place == 'rear':
            return [('rear', 0.0, sill + 0.72 * sh, sh * 0.22, lambda P: P[:, 2] < zr + 0.6, 0.35, 0)]
        if place == 'front':
            return [('front', 0.0, sill + 0.24 * sh, sh * 0.16, lambda P: P[:, 2] > zf - 0.5, 0.35, 0)]
        return []

    decals = []

    def put(place, img, scale=1.0, glow=None, b_shift=0.0):
        for view, a, b, h, reg, facing, rot in geo(place):
            hh = h * scale
            decals.append(Decal(img, view, a, b + b_shift * h, hh, rot=rot, region=reg, glow=glow, facing=facing))

    # logos from the library (one per place; later ones win)
    logos = list(design.get('logos') or [])
    if design.get('logo'):
        logos += [dict(path=design['logo'], place=p, tint=design.get('tint_logo', True)) for p in ('doors', 'bonnet')]
    taken = set()
    for lg in logos:
        p = lg.get('place')
        if p not in PLACES or not lg.get('path') or not os.path.isfile(lg['path']): continue
        try:
            img = prep_logo(lg['path'], acc2 if lg.get('tint') else None, lg.get('bg', 'auto'))
        except Exception as e:
            log(f'logo {os.path.basename(lg["path"])}: cannot read it ({e})'); continue
        is_pic = bool(img.info.get('picture'))
        put(p, img, glow=acc2 if p in ('doors', 'bonnet') and not is_pic else None)
        taken.add(p)

    # racing number
    num = str(design.get('number') or '').strip()
    style = design.get('number_style') or 'board'
    if num and style != 'none':
        if design.get('number_doors', True):
            z = prof['door_rear'] + 0.7 * door_len
            if style == 'board':
                img = number_board(num, txt, readable(base, txt, acc, acc2), edge, fnt)
            else:
                img = text_image(num, 300, t_txt, fnt, stroke=0.05, stroke_color=base, track=-0.02)
            for view, a, b, h, reg, facing, rot in sides(z, sill + 0.55 * sh, min(0.42, sh * 0.62)):
                decals.append(Decal(img, view, a, b, h, region=reg))
        if design.get('number_roof', True) and 'roof' in pan:
            zc, ln, wd = pan['roof']
            zc_n = zc + (0.12 * ln if 'roof' in taken else 0)
            decals.append(Decal(text_image(num, 300, t_txt, fnt, stroke=0.04, stroke_color=base), 'roof_l',
                                -zc_n, 0.0, min(wd * 0.45, ln * 0.45), region=lambda P: P[:, 1] > car.hi[1] - 0.3))

    # team wordmark + driver name
    team, name = (design.get('team') or '').strip(), (design.get('name') or '').strip()
    wing = 'front_wings' if 'front_wings' not in taken else ('lower_doors' if 'lower_doors' not in taken else None)
    if wing == 'front_wings':
        if team: put(wing, text_image(team, 200, t_txt, fnt), scale=0.62, b_shift=0.16 if name else 0)
        if name: put(wing, text_image(name, 200, t_acc2, fnt, style='SemiBold Condensed', track=0.12), scale=0.32, b_shift=-0.42)
    elif wing == 'lower_doors':
        if team: put(wing, text_image(team + (f'  |  {name}' if name else ''), 200, t_txt, fnt))
    if team:
        if 'boot' not in taken: put('boot', text_image(team, 200, t_txt, fnt), scale=0.4)
        if 'rear' not in taken: put('rear', text_image(team, 200, t_txt, fnt), scale=0.7)
        if 'front' not in taken: put('front', text_image(team, 200, t_acc2, fnt), scale=0.65)
    return decals


def number_board(num, txt, base, edge, fnt):
    t = text_image(num, 300, base, fnt, track=-0.02)
    w = max(int(t.height * 1.1), t.width + 90); h = t.height + 110
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, w - 5, h - 5], radius=40, fill=tuple(int(v) for v in txt) + (255,),
                        outline=tuple(int(v) for v in edge) + (255,), width=18)
    im.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
    return im


def apply_decals(col, tm, paint, decals, log):
    for dc in decals:
        vdir, fa, fb = VIEWS[dc.view]
        facing = tm.N @ vdir > dc.facing
        if dc.view in ('left', 'right'):
            facing &= ~tm.shared[tm.yy, tm.xx]        # mirrored UV would mirror the writing
        if dc.region is not None: facing &= dc.region(tm.P)
        img = dc.img.rotate(dc.rot, expand=True, resample=Image.BICUBIC) if dc.rot else dc.img
        if dc.glow is not None:
            pad = img.height // 6
            g = Image.new('RGBA', (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
            g.paste(img, (pad, pad))
            halo = g.getchannel('A').filter(ImageFilter.GaussianBlur(pad / 2)).point(lambda v: int(v * 0.6))
            gl = Image.new('RGBA', g.size, tuple(int(v) for v in dc.glow) + (0,)); gl.putalpha(halo)
            gl.alpha_composite(g); img = gl
            hscale = dc.height * g.height / max(1, dc.img.height if not dc.rot else img.height - 2 * pad)
        else:
            hscale = dc.height
        aspect = img.width / img.height
        hm, wm = hscale, hscale * aspect
        want_h = int(np.clip(hm / tm.texel_m * 1.5, 8, img.height))
        if want_h < img.height:
            img = img.resize((max(2, int(want_h * aspect)), want_h), Image.LANCZOS)
        a = fa(tm.P) - dc.a; b = fb(tm.P) - dc.b
        inside = facing & (np.abs(a) < wm / 2) & (np.abs(b) < hm / 2)
        idx = np.nonzero(inside)[0]
        if not len(idx): log(f'  decal on {dc.view}: no surface found'); continue
        arr = np.asarray(img).astype(np.float32)
        u = (a[idx] / wm + 0.5) * (img.width - 1)
        v = (0.5 - b[idx] / hm) * (img.height - 1)
        smp = bilinear(arr, u, v)
        al = smp[:, 3:4] / 255.0
        col[idx] = col[idx] * (1 - al) + smp[:, :3] * al
    return col


def bilinear(arr, u, v):
    h, w = arr.shape[:2]
    u = np.clip(u, 0, w - 1.001); v = np.clip(v, 0, h - 1.001)
    x0 = u.astype(int); y0 = v.astype(int); fx = (u - x0)[:, None]; fy = (v - y0)[:, None]
    return (arr[y0, x0] * (1 - fx) * (1 - fy) + arr[y0, x0 + 1] * fx * (1 - fy) +
            arr[y0 + 1, x0] * (1 - fx) * fy + arr[y0 + 1, x0 + 1] * fx * fy)


# ------------------------------------------------------------------ paint mask + shading from stock skins
def stock_analysis(car, tex, W, H, tm, log=print):
    imgs = []
    for s in car.skins:
        im = car.stock_texture(tex, s)
        if im is not None: imgs.append(im.resize((W, H), Image.LANCZOS))
    missing = sum(1 for s in car.skins if not find_skin_file(os.path.join(car.dir, 'skins', s), tex))
    if imgs and missing and tex in car.kn5.textures:
        # skins without this file show the model's own copy: it is one more look to compare against
        try:
            imgs.append(load_image(car.kn5.textures[tex]).resize((W, H), Image.LANCZOS))
            log(f'{missing} skin(s) use the model\'s own {tex}: included in the comparison')
        except Exception: pass
    if not imgs and tex in car.kn5.textures:
        imgs = [load_image(car.kn5.textures[tex]).resize((W, H), Image.LANCZOS)]
    A = np.stack([np.asarray(i.convert('RGB')).astype(np.float32) for i in imgs])
    alpha = np.asarray(imgs[0].getchannel('A'))
    base = A[0]
    if len(A) >= 3:
        sd = A.std(0).mean(-1)
        m = Image.fromarray(((sd > 9) * 255).astype(np.uint8))
        m = m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7)).filter(ImageFilter.MinFilter(3))
        paint = (np.asarray(m) > 127) & tm.covered
        # fill small holes (logos/number boards common to every stock skin)
        holes = ~paint & tm.covered
        hm = Image.fromarray((holes * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(int(W / 60) | 1)).filter(ImageFilter.MaxFilter(int(W / 60) | 1))
        big_holes = np.asarray(hm) > 127
        paint |= holes & ~big_holes & (A.mean(0).mean(-1) > 60)
        lum = A.mean(-1).max(0)
        li = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(W / 290))
        lum = np.asarray(li).astype(np.float32)
        ref = np.percentile(lum[paint], 90) if paint.any() else 255
        shade = np.clip(lum / ref, 0.6, 1.0) ** 0.8
        frac = paint.sum() / max(1, tm.covered.sum())
        if frac < 0.5:
            # skins differ only in decals (colour comes from elsewhere, e.g. Kunos' detail texture):
            # light, colourless texels are bare paint too
            mean = A.mean(0)
            light = (mean.mean(-1) > 110) & ((mean.max(-1) - mean.min(-1)) < 35) & tm.covered
            paint |= light
            log(f'stock skins only differ in decals ({frac * 100:.0f}%); light bare paint added')
        log(f'paint area from {len(A)} stock skins: {paint.sum() / tm.covered.sum() * 100:.0f}% of the body texels')
    else:
        # few skins: everything on the body except light/glass/grille-looking meshes
        bad = re.compile(r'light|lamp|glass|window|grill|grid|mesh|int_|interior|badge|logo|plate|exhaust|tyre|tire|rim', re.I)
        good_tri = np.array([not bad.search(n) for n in tm.mesh_of_tri])
        paint = np.zeros((H, W), bool)
        paint[tm.yy, tm.xx] = good_tri[tm.tri]
        shade = np.ones((H, W), np.float32)
        log(f'only {len(A)} stock skin(s): paint area guessed from mesh names ({paint.sum() / tm.covered.sum() * 100:.0f}%)')
    return base, alpha, paint, shade


# ------------------------------------------------------------------ wheels
def recolour_wheels(car, tex, colour, log=print):
    """Recolour a wheel texture: texels that differ between stock skins (or every coloured
    texel when there are too few skins) take the new colour, keeping their light and shade."""
    imgs = [car.stock_texture(tex, s) for s in car.skins]
    imgs = [i for i in imgs if i is not None]
    W, H = imgs[0].size
    A = np.stack([np.asarray(i.resize((W, H)).convert('RGB')).astype(np.float32) for i in imgs])
    base = A[0]
    if len(A) >= 3:
        mask = A.std(0).mean(-1) > 9
    else:
        mx, mn = base.max(-1), base.min(-1)
        mask = (mx - mn) > 40                      # coloured (not grey/black/chrome) texels
        if mask.mean() < 0.02:                     # plain grey rim: colourise the whole rim by brightness
            mask = base.mean(-1) > 25
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1))
    mm = np.asarray(m).astype(np.float32)[..., None] / 255
    lum = A.max(0).mean(-1) if len(A) >= 3 else base.mean(-1)
    ref = np.percentile(lum[mask], 85) if mask.any() else 255
    shade = np.clip(lum / max(ref, 1), 0.25, 1.15)[..., None]
    new = np.clip(rgb(colour) * shade, 0, 255)
    out = base * (1 - mm) + new * mm
    log(f'wheels {tex}: recoloured {mask.mean() * 100:.0f}% of the texture')
    return Image.fromarray(np.dstack([out.astype(np.uint8), np.asarray(imgs[0].getchannel('A'))]), 'RGBA')


# ------------------------------------------------------------------ headlights
LIGHT_RE = re.compile(r'light|lamp|head|faro|lens|scheinwerfer|emissive|flash|\bhl\b|_hl|hl_|lhigh|llow|lday|ldown', re.I)
NOT_FRONT_RE = re.compile(r'rear|brake|tail|back|revers|aux|int_|interior|cockpit|dash|turn|indicat|blink|'
                          r'window|windscreen|windshield|win_|plate|number|fog|rain|pit|btn|button|shadow|direction', re.I)


def find_headlights(car):
    """Front light meshes (lamps, reflectors and their glass) found by name and position."""
    out = []
    front = car.hi[2] - 0.28 * car.length
    for m in car.kn5.meshes:
        if not len(m.idx) or m.mat is None: continue
        label = f'{m.name} {m.mat.name}'
        if not LIGHT_RE.search(label) or NOT_FRONT_RE.search(label): continue
        c = m.pos.mean(0)
        if c[2] < front or c[1] > car.lo[1] + 0.8 * (car.hi[1] - car.lo[1]): continue
        out.append(m)
    return out


def current_texture(car, tex, made, copy_from=None):
    """The texture as the new skin will have it: made here > copied skin > a stock skin > inside the kn5."""
    if tex in made: return made[tex]
    if copy_from:
        im = car.stock_texture(tex, copy_from)
        if im is not None: return im
    if tex in car.kn5.textures: return load_image(car.kn5.textures[tex])
    for s in car.skins:
        im = car.stock_texture(tex, s)
        if im is not None: return im
    return None


def tint_lenses(car, lights, colour, made, copy_from=None, log=print):
    """Tint the texels the headlight meshes use. AC's lamp glow takes the texture colour,
    so this colours both the unlit lens and the lit glow (no CSP needed)."""
    by_tex = {}
    for m in lights:
        t = m.mat.samplers.get('txDiffuse')
        if t: by_tex.setdefault(t, []).append(m)
    out = {}
    col = rgb(colour) / 255.0
    for tex, ms in by_tex.items():
        img = current_texture(car, tex, made, copy_from)
        if img is None: continue
        W, H = img.size
        tm = TexelMap(ms, W, H, log=lambda s: None)
        mask = Image.fromarray((tm.covered * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
        m = (np.asarray(mask) > 0)
        a = np.asarray(img).astype(np.float32)
        rgbv = a[..., :3]
        lum = rgbv.mean(-1, keepdims=True)
        tinted = np.clip(lum * col * 1.15 + np.clip(lum - 200, 0, 55) * 0.8, 0, 255)   # bright glints stay bright
        mix = 0.6
        if m.mean() < 0.0005: continue           # nothing of the lamps lands in this texture
        rgbv[m] = rgbv[m] * (1 - mix) + tinted[m] * mix
        a[..., :3] = rgbv
        out[tex] = Image.fromarray(a.astype(np.uint8), 'RGBA')
        log(f'headlight lenses: tinted {m.mean() * 100:.1f}% of {tex} ({", ".join(x.name for x in ms[:4])}{"…" if len(ms) > 4 else ""})')
    if not out: log('headlight lenses: no front light meshes found on this car')
    return out


def existing_headlight_sections(car):
    """[LIGHT_HEADLIGHT_n] sections (and their COLOR) in the car's CSP configs."""
    ac_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.normpath(car.dir))))
    carname = os.path.basename(os.path.normpath(car.dir))
    files = [os.path.join(car.dir, 'extension', 'ext_config.ini')]
    files += glob.glob(os.path.join(ac_root, 'extension', 'config', 'cars', '**', carname + '.ini'), recursive=True)
    cfg_root = os.path.join(ac_root, 'extension', 'config', 'cars')
    found, auto = {}, 0

    def scan(path, depth=0):
        nonlocal auto
        try: txt = open(path, encoding='utf8', errors='ignore').read()
        except OSError: return
        cur = None
        for line in txt.splitlines():
            st = line.split(';')[0].strip()
            m = re.match(r'\[\s*INCLUDE\s*:\s*(.+?)\s*\]', st, re.I)
            if m and depth < 2:
                scan(os.path.join(cfg_root, m.group(1)), depth + 1); cur = None; continue
            m = re.match(r'\[(LIGHT_HEADLIGHT_)(\d+|\.\.\.)\]', st, re.I)
            if m:
                if m.group(2) == '...': idx = auto; auto += 1
                else: idx = int(m.group(2)); auto = max(auto, idx + 1)
                cur = idx; found.setdefault(idx, None); continue
            if st.startswith('['): cur = None; continue
            if cur is not None and st.upper().startswith('COLOR'):
                try: found[cur] = [float(v) for v in st.split('=', 1)[1].split(',')]
                except ValueError: pass
    for f in files:
        if os.path.isfile(f): scan(f)
    return found


def beam_config(car, lights, colour, log=print):
    """ext_config.ini text that sets the headlight beam colour for this skin (needs CSP)."""
    c = rgb(colour) / 255.0
    c = c / max(c.max(), 1e-6)
    found = existing_headlight_sections(car)
    lines = ['; headlight beam colour, made by ' + APP_NAME]
    if found:
        for idx in sorted(found):
            old = found[idx]
            if old and len(old) >= 3:
                bright = max(old[:3]) or 1.0
                vals = list(c * bright) + (old[3:4] if len(old) > 3 else [])
            else:
                vals = list(c) + [25]
            lines += ['', f'[LIGHT_HEADLIGHT_{idx}]', 'COLOR=' + ', '.join(f'{v:.3g}' for v in vals)]
        log(f'headlight beams: recoloured {len(found)} existing CSP headlight(s)')
    else:
        emit = [m for m in lights if 'glass' not in (m.name + m.mat.name).lower()] or lights
        if not emit:
            log('headlight beams: no headlights found on this car - skipped'); return None
        P = np.concatenate([m.pos for m in emit])
        y, z = float(np.median(P[:, 1])), float(np.percentile(P[:, 2], 90))
        xo = float(np.median(np.abs(P[:, 0])))
        lines += ['', '[LIGHT_HEADLIGHT_0]', f'POSITION=0, {y:.3f}, {z:.3f}', f'MIRROR={xo:.3f}',
                  'DIRECTION=0, -0.04, 1', 'COLOR=' + ', '.join(f'{v:.3g}' for v in c) + ', 22',
                  'RANGE=70', 'SPOT=60', 'SPOT_SHARPNESS=0.4', 'DIFFUSE_CONCENTRATION=0.85',
                  'BIND_TO_HEADLIGHTS=1', 'AFFECTS_TRACK=1', 'AFFECTS_CAR=0', 'FADE_AT=400', 'FADE_SMOOTH=50',
                  'SECOND_SPOT=120', 'SECOND_SPOT_INTENSITY=0.2', 'SECOND_SPOT_RANGE=15']
        log(f'headlight beams: the car has no CSP headlights, added a pair at y={y:.2f} z={z:.2f} x=±{xo:.2f}')
    return '\n'.join(lines) + '\n'


def merge_ini(path, text):
    """Add/replace sections of `text` in the ini at `path` (keeps everything else)."""
    def parse(t):
        secs, cur = [], [None, []]
        for line in t.splitlines():
            m = re.match(r'\s*\[([^\]]+)\]', line)
            if m: secs.append(cur); cur = [m.group(1).strip(), []]
            else: cur[1].append(line)
        secs.append(cur); return secs
    old = parse(open(path, encoding='utf8', errors='ignore').read()) if os.path.isfile(path) else [[None, []]]
    new = parse(text)
    for name, body in new:
        if name is None: continue
        keys = {l.split('=', 1)[0].strip().upper() for l in body if '=' in l}
        hit = next((s for s in old if s[0] and s[0].upper() == name.upper()), None)
        if hit:
            hit[1] = [l for l in hit[1] if '=' not in l or l.split('=', 1)[0].strip().upper() not in keys] + \
                     [l for l in body if '=' in l]
        else:
            old.append([name, body])
    with open(path, 'w', encoding='utf8') as f:
        for name, body in old:
            if name is not None: f.write(f'[{name}]\n')
            for l in body: f.write(l + '\n')


# ------------------------------------------------------------------ window stickers
GLASS_RE = re.compile(r'window|windscreen|windshield|glass|(?<![a-z])win_|_win(?![a-z])|parabrezza|vetr|lunotto|scheibe', re.I)
NOT_GLASS_RE = re.compile(r'light|lamp|head|lens|emissive|faro|mirror|gauge|dial|display|screen_|lcd|visor|helmet|mold|mould|trim|seal|rubber|frame|gasket|wiper', re.I)
INSIDE_RE = re.compile(r'int_|_int\b|interior|inside|cockpit|inner', re.I)


OVERLAY_RE = re.compile(r'banner|sun.?strip|visor_?decal|window.?decal|glass.?decal|win.?decal', re.I)
DECAL_RE = re.compile(r'decal|sticker', re.I)


def window_meshes(car, with_overlays=False):
    """Glass meshes (outside / inside). With with_overlays: also the sticker overlay meshes some
    cars use instead (Kunos: EXT_Banner on the windscreen, EXT_DECALS_DOOR_x on the side windows)."""
    ext, inner, ov_ext, ov_inner = [], [], [], []
    y_min = car.lo[1] + 0.6 * (car.hi[1] - car.lo[1])
    for m in car.kn5.meshes:
        if not len(m.idx) or m.mat is None or not m.mat.samplers.get('txDiffuse'): continue
        label = f'{m.name} {m.mat.name}'
        inside = bool(INSIDE_RE.search(label))
        if OVERLAY_RE.search(label) or (DECAL_RE.search(label) and 'door' in label.lower() and m.pos.mean(0)[1] > y_min):
            if tri_area3(m).sum() > 0.02:          # tiny patches (door-pin labels etc.) are not sticker sheets
                (ov_inner if inside else ov_ext).append(m)
            continue
        if not GLASS_RE.search(label) or NOT_GLASS_RE.search(label): continue
        (inner if inside else ext).append(m)
    return (ext, inner, ov_ext, ov_inner) if with_overlays else (ext, inner)


def banner_image(text, colour, text_colour, fnt, aspect):
    """A sun-strip banner: solid band with centred text, `aspect` = width / height."""
    h = 160; w = int(h * aspect)
    im = Image.new('RGBA', (w, h), tuple(int(v) for v in colour) + (255,))
    if text:
        t = text_image(text, 110, text_colour, fnt, track=0.06)
        if t.width > w * 0.9: t = t.resize((int(w * 0.9), int(t.height * w * 0.9 / t.width)), Image.LANCZOS)
        im.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
    return im


def clean_glass(arr, sel):
    """Remove old stickers: texels that differ from the most common glass value become plain glass."""
    px = arr[sel].astype(np.float32)
    if not len(px): return
    q = (px // 24).astype(np.int32)
    key = q[:, 0] * 1000000 + q[:, 1] * 10000 + q[:, 2] * 100 + q[:, 3]
    vals, cnt = np.unique(key, return_counts=True)
    plain = px[key == vals[np.argmax(cnt)]].mean(0)
    d = np.abs(px - plain)
    old = (d[:, :3].max(1) > 45) | (d[:, 3] > 40)
    px[old] = plain
    arr[sel] = px.astype(np.uint8)


def make_window_stickers(car, design, made, copy_from=None, log=print):
    ext, inner, ov_ext, ov_inner = window_meshes(car, with_overlays=True)
    if not ext and not ov_ext:
        log('windows: no glass meshes found on this car'); return {}
    if not ext: ext = ov_ext
    fnt = design.get('font') or DEFAULT_FONT
    txt = rgb(design.get('win_text_colour') or '#ffffff')
    band = rgb(design.get('win_banner_colour') or '#111111')
    num = str(design.get('number') or '').strip()
    name = (design.get('name') or '').strip()
    logos = {lg['place']: lg for lg in (design.get('logos') or [])
             if lg.get('place') in ('windscreen', 'rear_window', 'side_windows') and os.path.isfile(lg.get('path', ''))}
    acc2 = rgb(design.get('accent2') or '#ffffff')

    # where the glass is (all exterior glass, world space)
    P = np.concatenate([m.pos for m in ext]); Nn = np.concatenate([m.nrm for m in ext])
    mid = (car.hi[2] + car.lo[2]) / 2
    fr = P[(Nn[:, 2] > 0.3) & (P[:, 2] > mid)]
    rr = P[(Nn[:, 2] < -0.3) & (P[:, 2] < mid)]
    sd = P[np.abs(Nn[:, 0]) > 0.6]
    decals = []
    bh = 0.11
    if len(fr) > 3:
        top = np.percentile(fr[:, 1], 99); wd = np.percentile(fr[:, 0], 99) - np.percentile(fr[:, 0], 1)
        bn = [m for m in ov_ext if 'banner' in (m.name + m.mat.name).lower() and m.pos.mean(0)[2] > mid]
        if bn:   # the car has its own sun-strip mesh: fit the banner to it
            Q = np.concatenate([m.pos for m in bn])
            top = Q[:, 1].max(); bh = max(0.05, Q[:, 1].max() - Q[:, 1].min())
            wd = Q[:, 0].max() - Q[:, 0].min()
        reg = lambda Q, top=top: (Q[:, 2] > mid) & (Q[:, 1] > top - 0.35)
        if 'windscreen' in logos:
            lg = prep_logo(logos['windscreen']['path'], acc2 if logos['windscreen'].get('tint') else None, logos['windscreen'].get('bg', 'auto'))
            decals.append(Decal(banner_image('', band, txt, fnt, wd / bh), 'front', 0.0, top - bh / 2, bh, region=reg))
            decals.append(Decal(lg, 'front', 0.0, top - bh / 2, bh * 0.85, region=reg))
        else:
            decals.append(Decal(banner_image(design.get('win_banner', '').strip(), band, txt, fnt, wd / bh), 'front',
                                0.0, top - bh / 2, bh, region=reg))
    if len(rr) > 3:
        top = np.percentile(rr[:, 1], 99); bot = np.percentile(rr[:, 1], 5)
        wd = np.percentile(rr[:, 0], 99) - np.percentile(rr[:, 0], 1)
        reg = lambda Q: Q[:, 2] < mid
        decals.append(Decal(banner_image(design.get('win_banner', '').strip(), band, txt, fnt, wd / (bh * 0.8)), 'rear',
                            0.0, top - bh * 0.4, bh * 0.8, region=reg))
        if 'rear_window' in logos:
            lg = prep_logo(logos['rear_window']['path'], acc2 if logos['rear_window'].get('tint') else None, logos['rear_window'].get('bg', 'auto'))
            decals.append(Decal(lg, 'rear', 0.0, bot + (top - bot) * 0.6, (top - bot) * 0.38, region=reg))
        elif design.get('win_number', True) and num:
            decals.append(Decal(text_image(num, 300, txt, fnt, stroke=0.05, stroke_color=band), 'rear', 0.0,
                                bot + (top - bot) * 0.62, (top - bot) * 0.34, region=reg))
        if design.get('win_name', True) and name:
            decals.append(Decal(text_image(name, 200, txt, fnt, track=0.08), 'rear', 0.0, bot + (top - bot) * 0.36,
                                (top - bot) * 0.1, region=reg))
    if len(sd) > 3:
        # the rear-most side window on each side
        zcut = np.percentile(sd[:, 2], 30)
        rs = sd[sd[:, 2] < zcut]
        zc = float(np.median(rs[:, 2])); yc = float(np.median(rs[:, 1]))
        hgt = np.percentile(rs[:, 1], 95) - np.percentile(rs[:, 1], 5)
        for view, sg in (('left', 1), ('right', -1)):
            a = -zc if view == 'left' else zc
            reg = (lambda Q, sg=sg, zc=zc: (Q[:, 0] * sg > 0.1) & (Q[:, 2] < zcut + 0.05))
            dm = [m for m in ov_ext if 'door' in (m.name + m.mat.name).lower() and m.pos.mean(0)[0] * sg > 0]
            if dm:   # the car has its own door-window sticker sheet: put them there
                Q = np.concatenate([m.pos for m in dm])
                z0_, z1_ = Q[:, 2].min(), Q[:, 2].max()
                zc_d = float((z0_ + z1_) / 2); yc = float((Q[:, 1].min() + Q[:, 1].max()) / 2)
                hgt = float(Q[:, 1].max() - Q[:, 1].min()) * 1.6
                a = -zc_d if view == 'left' else zc_d
                reg = (lambda Q2, sg=sg, z0_=z0_, z1_=z1_: (Q2[:, 0] * sg > 0.1) & (Q2[:, 2] > z0_ - 0.05) & (Q2[:, 2] < z1_ + 0.05))
            if 'side_windows' in logos:
                lg = prep_logo(logos['side_windows']['path'], acc2 if logos['side_windows'].get('tint') else None, logos['side_windows'].get('bg', 'auto'))
                decals.append(Decal(lg, view, a, yc, hgt * 0.6, region=reg))
            else:
                if design.get('win_number', True) and num:
                    decals.append(Decal(text_image(num, 300, txt, fnt, stroke=0.05, stroke_color=band), view, a,
                                        yc + hgt * 0.1, hgt * 0.45, region=reg))
                if design.get('win_name', True) and name:
                    decals.append(Decal(text_image(name, 200, txt, fnt, track=0.06), view, a, yc - hgt * 0.25,
                                        hgt * 0.13, region=reg))

    # (meshes, inside, overlay) per texture. Overlays are clear sticker sheets: cleaning makes them transparent.
    by_tex = {}
    for group, inside, overlay in ((ext if ext is not ov_ext else [], False, False), (inner, True, False),
                                   (ov_ext, False, True), (ov_inner, True, True)):
        for m in group:
            by_tex.setdefault(m.mat.samplers['txDiffuse'], {}).setdefault((inside, overlay), []).append(m)
    back = np.array([28, 28, 30], np.float32)          # the back of a sticker, seen from inside
    arrs = {}
    for tex in by_tex:
        img = current_texture(car, tex, made, copy_from)
        if img is None: continue
        if max(img.size) < 64:
            log(f'windows: {tex} is only {img.size[0]}x{img.size[1]} (plain glass, no room for stickers) - skipped')
            continue
        arrs[tex] = np.asarray(img.convert('RGBA')).copy()
    # pass 1 outside, pass 2 inside (only the backs of stickers that landed outside; outside wins shared texels)
    hit, touched, changed = set(), {}, set()
    cleaned = set()
    for inside_pass in (False, True):
        for tex, arr in arrs.items():
            H, W = arr.shape[:2]
            for (inside, overlay), meshes in by_tex[tex].items():
                if inside != inside_pass: continue
                tm = TexelMap(meshes, W, H, log=lambda s: None)
                if inside and not hit: continue
                keep = arr.copy() if inside else None
                if design.get('win_clear', True):
                    if overlay:
                        cov = Image.fromarray((tm.covered * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
                        arr[np.asarray(cov) > 0] = 0
                    else:
                        clean_glass(arr, tm.covered)
                    if not inside: changed.add(tex)
                col = arr[tm.yy, tm.xx, :3].astype(np.float32)
                alp = arr[tm.yy, tm.xx, 3].astype(np.float32)
                use = [d for i, d in enumerate(decals) if (not inside) or i in hit]
                col, alp, got = apply_decals_rgba(col, alp, tm, use, inside, back)
                if not inside: hit |= {decals.index(use[i]) for i in got}
                if inside and not got:                   # nothing lands on this inside glass: leave it as it was
                    arr[:] = keep
                    continue
                if got: changed.add(tex)
                arr[tm.yy, tm.xx, :3] = np.clip(col, 0, 255).astype(np.uint8)
                arr[tm.yy, tm.xx, 3] = np.clip(alp, 0, 255).astype(np.uint8)
                if inside and tex in touched:            # never paint over texels the outside already uses
                    arr[touched[tex]] = keep[touched[tex]]
                if not inside:
                    m_ = np.zeros((H, W), bool); m_[tm.yy, tm.xx] = True
                    touched[tex] = touched.get(tex, np.zeros((H, W), bool)) | m_
                touched.setdefault(tex + '#names', []).extend(m.name for m in meshes)
    out = {}
    if not hit:
        log('windows: this car has no glass texture with room for stickers - window stickers skipped')
        return out
    for tex in changed:
        out[tex] = Image.fromarray(arrs[tex], 'RGBA')
        log(f'windows: stickers on {tex} ({", ".join(touched.get(tex + "#names", []))[:80]})')
    return out


def apply_decals_rgba(col, alp, tm, decals, inside=False, back=None):
    """Like apply_decals, but for glass: stickers are opaque, and inside glass shows their back.
    Returns colours, alpha and the indices of the decals that landed."""
    got = []
    for k, dc in enumerate(decals):
        vdir, fa, fb = VIEWS[dc.view]
        f = tm.N @ vdir
        facing = (f < -0.2) if inside else (f > 0.2)
        if dc.region is not None: facing &= dc.region(tm.P)
        img = dc.img.rotate(dc.rot, expand=True, resample=Image.BICUBIC) if dc.rot else dc.img
        aspect = img.width / img.height
        hm, wm = dc.height, dc.height * aspect
        want_h = int(np.clip(hm / tm.texel_m * 1.5, 8, img.height))
        if want_h < img.height:
            img = img.resize((max(2, int(want_h * aspect)), want_h), Image.LANCZOS)
        a = fa(tm.P) - dc.a; b = fb(tm.P) - dc.b
        idx = np.nonzero(facing & (np.abs(a) < wm / 2) & (np.abs(b) < hm / 2))[0]
        if not len(idx): continue
        arr = np.asarray(img).astype(np.float32)
        smp = bilinear(arr, (a[idx] / wm + 0.5) * (img.width - 1), (0.5 - b[idx] / hm) * (img.height - 1))
        al = smp[:, 3:4] / 255.0
        c = np.broadcast_to(back, smp[:, :3].shape) if inside else smp[:, :3]
        col[idx] = col[idx] * (1 - al) + c * al
        alp[idx] = alp[idx] * (1 - al[:, 0]) + 255 * al[:, 0]
        if (al > 0.5).sum() > 20: got.append(k)
    return col, alp, got


# ------------------------------------------------------------------ DDS writer
def write_dds(img, path):
    """Uncompressed A8R8G8B8 with a full mip chain (what AC reads without tools)."""
    img = img.convert('RGBA')
    levels, im = [], img
    while True:
        levels.append(im)
        if im.width == 1 and im.height == 1: break
        im = im.resize((max(1, im.width // 2), max(1, im.height // 2)), Image.LANCZOS)
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, 0x2100F, img.height, img.width, img.width * 4, 0, len(levels))
    hdr += struct.pack('<IIIIIIII', 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    hdr += struct.pack('<IIIII', 0x401008, 0, 0, 0, 0)
    with open(path, 'wb') as f:
        f.write(hdr)
        for lv in levels:
            f.write(np.asarray(lv)[..., [2, 1, 0, 3]].copy().tobytes())


# ------------------------------------------------------------------ preview renderer (texel splat + grey shell)
def render_view(car, view, tex_imgs, tms, width=1000, bg=(235, 236, 240)):
    vdir, fa, fb = VIEWS[view]
    allP = np.concatenate([m.pos for m in car.kn5.meshes if len(m.pos)])
    A, B = fa(allP), fb(allP)
    a0, a1, b0, b1 = np.percentile(A, 0.2), np.percentile(A, 99.8), np.percentile(B, 0.2), np.percentile(B, 99.8)
    pad = 0.04 * (a1 - a0)
    a0 -= pad; a1 += pad; b0 -= pad; b1 += pad
    sc = width / (a1 - a0); height = int((b1 - b0) * sc)
    img = Image.new('RGB', (width, height), bg)
    d = ImageDraw.Draw(img)
    light = np.array([0.4, 0.8, 0.45]); light /= np.linalg.norm(light)
    # grey shell: all triangles, back to front
    tris = []
    for m in car.kn5.meshes:
        if not len(m.idx): continue
        T = m.pos[m.idx]; Nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        ln = np.linalg.norm(Nn, axis=1); ok = ln > 0
        tris.append((T[ok], Nn[ok] / ln[ok, None]))
    T = np.concatenate([t[0] for t in tris]); Nn = np.concatenate([t[1] for t in tris])
    depth = (T.mean(1) @ vdir)
    flat = T.reshape(-1, 3)
    QA = ((fa(flat) - a0) * sc).reshape(-1, 3); QB = ((b1 - fb(flat)) * sc).reshape(-1, 3)
    area2 = np.abs((QA[:, 1] - QA[:, 0]) * (QB[:, 2] - QB[:, 0]) - (QA[:, 2] - QA[:, 0]) * (QB[:, 1] - QB[:, 0]))
    G = (110 + 80 * np.abs(Nn @ light)).astype(int)
    order = np.argsort(depth)
    order = order[area2[order] > 0.05]
    for i in order.tolist():
        g = int(G[i])
        d.polygon([(QA[i, 0], QB[i, 0]), (QA[i, 1], QB[i, 1]), (QA[i, 2], QB[i, 2])], fill=(g, g, g))
    # textured body: splat texels at half resolution then scale up
    hw, hh = width // 2, height // 2
    zbuf = np.full((hh, hw), -1e9); cbuf = np.zeros((hh, hw, 3)); mbuf = np.zeros((hh, hw), bool)
    for tex, tm in tms.items():
        arr = np.asarray(tex_imgs[tex].convert('RGB')).astype(np.float32)
        sel = tm.N @ vdir > 0.05
        P = tm.P[sel]
        c = arr[tm.yy[sel], tm.xx[sel]]
        shade = 0.6 + 0.4 * np.clip(tm.N[sel] @ light, 0, 1)
        c = c * shade[:, None]
        u = ((fa(P) - a0) * sc / 2).astype(int); v = ((b1 - fb(P)) * sc / 2).astype(int)
        dp = P @ vdir
        ok = (u >= 0) & (u < hw) & (v >= 0) & (v < hh)
        u, v, dp, c = u[ok], v[ok], dp[ok], c[ok]
        o = np.argsort(dp)
        u, v, dp, c = u[o], v[o], dp[o], c[o]
        upd = dp > zbuf[v, u] - 0.0
        zbuf[v[upd], u[upd]] = dp[upd]; cbuf[v[upd], u[upd]] = c[upd]; mbuf[v[upd], u[upd]] = True
    ci = Image.fromarray(np.clip(cbuf, 0, 255).astype(np.uint8))
    mi = Image.fromarray((mbuf * 255).astype(np.uint8))
    # close pin-holes
    ci2 = ci.filter(ImageFilter.MaxFilter(3))
    holes = Image.fromarray(((~mbuf) & (np.asarray(mi.filter(ImageFilter.MaxFilter(3))) > 0)).astype(np.uint8) * 255)
    ci.paste(ci2, (0, 0), holes)
    mi = mi.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    ci = ci.resize((width, height), Image.LANCZOS); mi = mi.resize((width, height), Image.NEAREST)
    img.paste(ci, (0, 0), mi)
    return img


def preview_sheet(car, tex_imgs, tms, width=900):
    views = [render_view(car, v, tex_imgs, tms, width) for v in ('left', 'right')]
    tv = [render_view(car, v, tex_imgs, tms, width // 2) for v in ('front', 'rear')]
    top = render_view(car, 'top', tex_imgs, tms, width // 2).rotate(90, expand=True)
    H = views[0].height + views[1].height + max(tv[0].height, top.height)
    sheet = Image.new('RGB', (width, H), (235, 236, 240))
    sheet.paste(views[0], (0, 0)); sheet.paste(views[1], (0, views[0].height))
    y = views[0].height + views[1].height
    sheet.paste(tv[0], (0, y)); sheet.paste(tv[1], (tv[0].width, y))
    return sheet


# ------------------------------------------------------------------ the whole job
def generate(car_dir, design, skin_name, out_root=None, resolution=None, log=print, preview_path=None,
             copy_other_from=None):
    car = Car(car_dir, log)
    skin_id = re.sub(r'[^a-z0-9_]+', '_', skin_name.lower()).strip('_') or 'custom'
    out = os.path.join(out_root or os.path.join(car_dir, 'skins'), skin_id)
    if os.path.exists(out) and os.listdir(out):
        raise FileExistsError(f'skin folder already exists: {out}')
    tex_out, tms = {}, {}
    for tex in car.body_textures:
        ref = None
        for s in car.skins:
            ref = car.stock_texture(tex, s)
            if ref is not None: break
        if ref is None: ref = load_image(car.kn5.textures[tex])
        W, H = ref.size
        if max(W, H) < 1024:
            log(f'{tex} is only {W}x{H}; making the new texture 2048 wide')
            k = 2048 / max(W, H); W, H = int(W * k), int(H * k)
        if resolution and max(W, H) < resolution:
            k = resolution / max(W, H); W, H = int(W * k), int(H * k)
            log(f'making {tex} {W}x{H} for sharper writing and logos')
        log(f'--- {tex}')
        tm = TexelMap(car.meshes_for(tex), W, H, log)
        base, alpha, paint, shade = stock_analysis(car, tex, W, H, tm, log)
        cols = render_design(car, tm, paint, design, log)
        canvas = base.copy()
        sel = paint[tm.yy, tm.xx]
        yy, xx = tm.yy[sel], tm.xx[sel]
        canvas[yy, xx] = cols[sel] * shade[yy, xx, None]
        # soften the mask edge by one texel
        m = Image.fromarray((paint * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
        mm = np.asarray(m).astype(np.float32)[..., None] / 255
        painted = np.clip(canvas, 0, 255)
        out_rgb = base * (1 - mm) + painted * mm
        out_rgb[paint] = painted[paint]
        img = Image.fromarray(np.dstack([np.clip(out_rgb, 0, 255).astype(np.uint8), alpha]), 'RGBA')
        tex_out[tex] = img; tms[tex] = tm
    wheel_out = {}
    if design.get('wheel_colour'):
        for tex in car.wheel_textures:
            wheel_out[tex] = recolour_wheels(car, tex, design['wheel_colour'], log)
    made = dict(tex_out); made.update(wheel_out)
    if design.get('win_enable'):
        made.update(make_window_stickers(car, design, made, copy_other_from, log))
    lights = find_headlights(car) if (design.get('lens_colour') or design.get('beam_colour')) else []
    if design.get('lens_colour'):
        made.update(tint_lenses(car, lights, design['lens_colour'], made, copy_other_from, log))
    os.makedirs(out, exist_ok=True)
    mine = {t.lower() for t in made} | {os.path.splitext(t)[0].lower() + '.dds' for t in made}
    if copy_other_from:   # copy first, so files made here replace the copies
        src = os.path.join(car_dir, 'skins', copy_other_from)
        for f in os.listdir(src):
            if f.lower() in mine or f.lower() in ('preview.jpg', 'ui_skin.json', 'livery.png', 'generator_preview.png'):
                continue
            if os.path.isfile(os.path.join(src, f)):
                shutil.copyfile(os.path.join(src, f), os.path.join(out, f))
    for tex, img in made.items():
        name = os.path.splitext(tex)[0] + '.dds'
        for s_ in car.skins:     # use the file-name spelling the car's own skins use
            f_ = find_skin_file(os.path.join(car_dir, 'skins', s_), tex)
            if f_: name = os.path.splitext(os.path.basename(f_))[0] + '.dds'; break
        write_dds(img, os.path.join(out, name))
        log(f'wrote {name}')
    # Kunos-style paint: the colour lives in the body material's detail texture (e.g. metal_detail.dds),
    # multiplied over the diffuse. Give the new skin a plain white one so the livery shows its own colours.
    for tex in car.body_textures:
        for m in car.meshes_for(tex):
            det = m.mat.samplers.get('txDetail')
            if det and det not in made and any(find_skin_file(os.path.join(car_dir, 'skins', s_), det) for s_ in car.skins):
                write_dds(Image.new('RGBA', (64, 64), (255, 255, 255, 255)), os.path.join(out, os.path.splitext(det)[0] + '.dds'))
                made[det] = None
                log(f'wrote a plain white {det} (this car takes its paint colour from it)')
    if design.get('beam_colour'):
        txt = beam_config(car, lights, design['beam_colour'], log)
        if txt: merge_ini(os.path.join(out, 'ext_config.ini'), txt); log('wrote ext_config.ini (beam colour, needs CSP)')
    num = design.get('number') or ''
    json.dump({'skinname': skin_name, 'drivername': design.get('name') or '', 'country': '',
               'team': design.get('team') or '', 'number': int(num) if str(num).isdigit() else num},
              open(os.path.join(out, 'ui_skin.json'), 'w'), indent=4)
    lv = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(lv)
    d.ellipse([2, 2, 61, 61], fill=tuple(int(v) for v in rgb(design['base'])) + (255,),
              outline=tuple(int(v) for v in rgb(design['accent2'])) + (255,), width=3)
    d.pieslice([2, 2, 61, 61], 200, 340, fill=tuple(int(v) for v in rgb(design['accent'])) + (255,))
    lv.save(os.path.join(out, 'livery.png'))
    sheet = preview_sheet(car, tex_out, tms)
    if preview_path: sheet.save(preview_path)
    log(f'skin saved: {out}')
    return out, sheet, car, tms, tex_out
