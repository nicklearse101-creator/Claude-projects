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
import copy, glob, io, json, os, re, shutil, struct
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageColor, ImageOps

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
TYRE_RE = re.compile(r'tyre|tire|tread|slick|pneu|gomm|reifen|sidewall', re.I)


def is_tyre(m):
    return m.mat is not None and (m.mat.shader.lower() == 'kstyres' or bool(TYRE_RE.search(f'{m.name} {m.mat.name}')))

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
        # AC's wheel dummies by their exact names; parts by a word in their own name (never inside another word:
        # 'primera', 'trim' and the model's root node 'FBX: ...' once made whole cars count as a wheel)
        wheelish = re.compile(r'(?<![a-z])(?:WHEEL_|SUSP_|HUB_|DISC_|rims?(?=[^a-z]|lf|rf|lr|rr|$)|tyres?|tires?)', re.I)
        for m in self.kn5.meshes:
            if m.mat is None or not len(m.idx): continue
            if any(wheelish.search(p) for p in m.parents) or wheelish.search(m.name): continue
            if re.search(r'window|windscreen|windshield|glass|parabrezza|vetr', f'{m.name} {m.mat.name} {m.mat.samplers.get("txDiffuse", "")}', re.I):
                continue                              # glass: handled by the window stickers, never painted
            t = m.mat.samplers.get('txDiffuse')
            if t: area[t] = area.get(t, 0) + tri_area3(m).sum()
        warea = {}
        for m in self.kn5.meshes:
            if m.mat is None or not len(m.idx): continue
            if any(wheelish.search(p) for p in m.parents) or wheelish.search(m.name):
                t = m.mat.samplers.get('txDiffuse')
                if t: warea[t] = warea.get(t, 0) + tri_area3(m).sum()
        rimish = re.compile(r'(?<![a-z])rims?(?=[^a-z]|lf|rf|lr|rr|$)|cerchi|wheel|felge|jante', re.I)
        notrim = re.compile(r'tyre|tire|blur|disc|brake|calip|hub|susp|nut|logo|badge', re.I)
        rim_tex = {m.mat.samplers.get('txDiffuse') for m in self.kn5.meshes if m.mat is not None and len(m.idx)
                   and rimish.search(m.name + ' ' + m.mat.name) and not notrim.search(m.name + ' ' + m.mat.name)}
        wheel_tex = [t for t in sorted(warea, key=lambda t: -warea[t])
                     if t not in area and (any(find_skin_file(os.path.join(self.dir, 'skins', s), t) for s in self.skins)
                                           or (t in rim_tex and t in self.kn5.textures))]
        # tyres and rims apart: a texture is a tyre texture when tyre meshes use it (the tyre shader or a
        # tyre-like name), a rim texture when anything else on the wheel does. A texture both use is
        # recoloured only where each kind of mesh sits on it.
        self.tyre_meshes, self.rim_meshes = {}, {}
        for m in self.kn5.meshes:
            if m.mat is None or not len(m.idx): continue
            label = f'{m.name} {m.mat.name}'
            tyre = is_tyre(m)
            for slot in ('txDiffuse', 'txBlur') if tyre else ('txDiffuse',):
                t = m.mat.samplers.get(slot)
                if not t: continue
                if tyre and (t in wheel_tex or (slot == 'txBlur' and (t in self.kn5.textures or
                             any(find_skin_file(os.path.join(self.dir, 'skins', s), t) for s in self.skins)))):
                    self.tyre_meshes.setdefault(t, []).append(m)
                elif not tyre and t in wheel_tex and not re.search(r'disc|brake|calip|hub|susp|nut', label, re.I):
                    self.rim_meshes.setdefault(t, []).append(m)
        self.wheel_textures = [t for t in wheel_tex if t in self.rim_meshes]
        self.tyre_textures = [t for t in list(dict.fromkeys(wheel_tex + list(self.tyre_meshes))) if t in self.tyre_meshes]
        if self.wheel_textures: self.log('rim textures (optional recolour): ' + ', '.join(self.wheel_textures))
        if self.tyre_textures: self.log('tyre textures (optional recolour): ' + ', '.join(self.tyre_textures))
        overridable = {}
        for t in area:
            n = sum(1 for s in self.skins if find_skin_file(os.path.join(self.dir, 'skins', s), t))
            if n: overridable[t] = n
        # skins can override any texture inside the kn5 by file name: the paint material's own texture counts
        # too when no stock skin overrides it (cars whose skins only change the paint colour)
        paintish = re.compile(r'paint|body|carpaint|skin|livery|ext_', re.I)
        cand = {}
        for m in self.kn5.meshes:
            if m.mat is None or not len(m.idx): continue
            t = m.mat.samplers.get('txDiffuse')
            if t in area and t not in overridable and paintish.search(m.mat.name + ' ' + t) and t in self.kn5.textures:
                cand[t] = area[t]
        top = max((area[t] for t in overridable), default=0)
        if overridable:      # only a real livery texture may take over from what the skins override
            cand = {t: a_ for t, a_ in cand.items() if a_ > top and self._tex_size(t) >= 256 and uv_overlap(self.meshes_for(t)) <= 3.0}
        if cand:
            t = max(cand, key=cand.get)
            overridable[t] = 0
            self.log(f'no stock skin overrides the body texture - using the one inside the model ({t})')
        if not overridable:
            raise RuntimeError('no paintable body texture found in this car')
        best = max(area[t] for t in overridable)
        # smaller second paint textures count too when their material is car paint (e.g. separate stripe panels
        # on body_2.dds): left out, they keep their stock colour and hide the livery under them
        paint_mat = re.compile(r'carpaint|car_paint|paint|livery|ext_body|bodywork', re.I)
        extra = {}
        for m in self.kn5.meshes:
            t = m.mat.samplers.get('txDiffuse') if m.mat is not None and len(m.idx) else None
            if t and t in area and t not in overridable and paint_mat.search(m.mat.name + ' ' + t) and \
                    (t in self.kn5.textures or any(find_skin_file(os.path.join(self.dir, 'skins', s_), t) for s_ in self.skins)):
                extra[t] = area[t]
        cands = sorted([t for t in overridable if area[t] > 0.15 * best], key=lambda t: -area[t])
        cands += sorted([t for t in list(overridable) + list(extra) if t not in cands and area[t] > 0.2 and
                         (t in extra or paint_mat.search(' '.join({m_.mat.name for m_ in self.meshes_for(t)})))],
                        key=lambda t: -area[t])
        inside = re.compile(r'leather|interior|(?<![a-z])int_|seat|carpet|dash|cockpit|alcantara|fabric|cage|bord|tableau|console', re.I)
        keep = []
        for t in cands[1:]:
            mats = ' '.join({m.mat.name for m in self.meshes_for(t)})
            if self._tex_size(t) < 256 or inside.search(t + ' ' + mats) or uv_overlap(self.meshes_for(t)) > 3.0:
                self.log(f'{t}: not a livery texture (small swatch, interior or shared material) - left as it is')
            else:
                keep.append(t)
        self.body_textures = cands[:1] + keep
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
def raster_tris(px, order, W, H, crop=False):
    """Which triangle each texel belongs to (-1 = none): triangles `order` of px (n, 3, 2 texel
    coordinates) drawn in that order, later ones on top. Interiors first; edge pixels only where no
    triangle covers the texel centre. With crop: only the triangles' bounding box; returns ids, x0, y0."""
    x0 = y0 = 0; w, h = W, H
    if crop and len(order):
        q = px[order].reshape(-1, 2)
        x0, y0 = max(0, int(q[:, 0].min()) - 2), max(0, int(q[:, 1].min()) - 2)
        w, h = min(W, int(q[:, 0].max()) + 3) - x0, min(H, int(q[:, 1].max()) + 3) - y0
    im = Image.new('I', (max(w, 1), max(h, 1)), -1); d = ImageDraw.Draw(im)
    ed = Image.new('I', (max(w, 1), max(h, 1)), -1); de = ImageDraw.Draw(ed)
    pts = (px[order] - (x0, y0)).tolist()
    for i, t in zip(order.tolist(), pts):
        q = [tuple(t[0]), tuple(t[1]), tuple(t[2])]
        d.polygon(q, fill=i)
        de.polygon(q, outline=i)
    a = np.asarray(im, dtype=np.int64).copy(); e = np.asarray(ed, dtype=np.int64)
    a[a < 0] = e[a < 0]
    return a, x0, y0


def locate_texels(px, pos, nrm, t, xx, yy):
    """3D point and normal of texel centres (xx, yy) on triangles t."""
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
    return P, N


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

        # texture-space area of each triangle; slivers (near zero area, long in 3D) would map
        # whole texel rows to the wrong place, so they are left out
        pa = 0.5 * np.abs((px[:, 1, 0] - px[:, 0, 0]) * (px[:, 2, 1] - px[:, 0, 1]) -
                          (px[:, 2, 0] - px[:, 0, 0]) * (px[:, 1, 1] - px[:, 0, 1]))
        e = np.stack([np.linalg.norm(px[:, i] - px[:, (i + 1) % 3], axis=1) for i in range(3)], 1).max(1)
        width = 2 * pa / np.maximum(e, 1e-9)                       # thinnest height in texels
        a3 = 0.5 * np.linalg.norm(np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0]), axis=1)
        dens = a3 / np.maximum(pa, 1e-9)                            # m² per texel
        med = np.median(dens[pa > 1]) if (pa > 1).any() else np.median(dens)
        good = (pa > 0.3) & ~((width < 1.5) & (dens > 2.5 * med))
        keep = np.nonzero(good)[0]
        keep = keep[np.argsort(width[keep], kind='stable')]        # thin first, solid panels drawn over them
        ida, _, _ = raster_tris(px, keep, W, H)
        idb, _, _ = raster_tris(px, keep[::-1], W, H)
        self.covered = ida >= 0
        self.t_px, self.t_pos, self.t_nrm, self.t_good = px, pos, nrm, good     # the triangles, for the decals
        self.tri_size = np.sqrt(np.clip(dens, 0, 0.05 ** 2))                    # metres per texel on each triangle
        self.last_sharp = None

        yy, xx = np.nonzero(self.covered)
        t = ida[yy, xx]
        P, N = locate_texels(px, pos, nrm, t, xx, yy)
        # "shared" = the same texels really are used by two different places on the car (mirrored /
        # overlapping UVs). Neighbouring triangles always overlap on their edges: that is not sharing.
        cand = np.nonzero(idb[yy, xx] != t)[0]
        self.shared = np.zeros((H, W), bool)
        # "mirrored" = shared with a place on the other side of the car (writing would read backwards there)
        self.mirrored = np.zeros((H, W), bool)
        if len(cand):
            Pb, _ = locate_texels(px, pos, nrm, idb[yy[cand], xx[cand]], xx[cand], yy[cand])
            far = np.linalg.norm(P[cand] - Pb, axis=1) > 0.05
            self.shared[yy[cand[far]], xx[cand[far]]] = True
            mir = far & (P[cand, 0] * Pb[:, 0] < 0) & (np.abs(P[cand, 0] - Pb[:, 0]) > 0.2)
            self.mirrored[yy[cand[mir]], xx[cand[mir]]] = True
        self.yy, self.xx, self.P, self.N, self.tri = yy, xx, P, N, t
        self.texel_m = float(np.sqrt(a3.sum() / max(1, len(yy))))     # metres per texel (average)
        self._index = None
        share = self.shared.sum() / max(1, self.covered.sum())
        log(f'texture {W}x{H}: {self.covered.mean()*100:.0f}% of texels on the body, {share*100:.1f}% shared by two surfaces')

    @property
    def index(self):
        """(H, W) image: position of each texel in the yy / xx / P / N arrays (-1 = not on the body)."""
        if self._index is None:
            self._index = np.full((self.H, self.W), -1, np.int32)
            self._index[self.yy, self.xx] = np.arange(len(self.yy), dtype=np.int32)
        return self._index


def uv_coverage(meshes, size=256):
    """Which cells of a size x size grid over the texture the meshes' triangles cover."""
    im = Image.new('L', (size, size), 0); d = ImageDraw.Draw(im)
    for m in meshes:
        if not len(m.idx): continue
        uv = m.uv[m.idx]; uv = uv - np.floor(uv.min(1, keepdims=True))
        for t in (uv * size).tolist():
            d.polygon([tuple(p) for p in t], fill=255, outline=255)
    return np.asarray(im) > 0


def uv_overlap(meshes):
    """Total texture area of all triangles / texture area actually covered (estimated on a 256 grid).
    1 = each texel used once; big numbers = every panel reuses the same texels."""
    uv = np.concatenate([m.uv[m.idx] for m in meshes if len(m.idx)])
    uv = uv - np.floor(uv.min(1, keepdims=True))
    a = 0.5 * np.abs((uv[:, 1, 0] - uv[:, 0, 0]) * (uv[:, 2, 1] - uv[:, 0, 1]) - (uv[:, 2, 0] - uv[:, 0, 0]) * (uv[:, 1, 1] - uv[:, 0, 1]))
    c = np.clip((uv.mean(1) * 256).astype(int), 0, 255)
    cells = np.zeros((256, 256), bool); cells[c[:, 1], c[:, 0]] = True
    big = a > 1 / 256 ** 2 * 4
    if big.any():   # large triangles cover many cells: mark their bounding boxes
        lo = np.clip((uv[big].min(1) * 256).astype(int), 0, 255); hi = np.clip((uv[big].max(1) * 256).astype(int), 0, 255)
        for (x0, y0), (x1, y1) in zip(lo[:2000], hi[:2000]): cells[y0:y1 + 1, x0:x1 + 1] = True
    return float(a.sum() / max(cells.mean(), 1e-6))


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
    """A picture placed in car space. view = the side it is read from; (a, b) = its centre in that
    view (metres); height in metres (width follows the picture unless `width` is given).
    coords: optional P -> (a, b) replacing the flat view projection (banners that follow the glass edge).
    movable: may slide along the car to get off mirrored texels. mirror_ok: may sit on mirrored texels."""
    def __init__(self, img, view, a, b, height, rot=0, region=None, glow=None, facing=0.35, width=None,
                 coords=None, movable=False, mirror_ok=False, label='', key='', kind='logo'):
        self.key, self.kind, self.flip = key, kind, False        # key: its name for hand adjustments; kind: logo / number / text
        self.img, self.view, self.a, self.b, self.height = img, view, a, b, height
        self.rot, self.region, self.glow, self.facing = rot, region, glow, facing
        self.width, self.coords, self.movable, self.mirror_ok, self.label = width, coords, movable, mirror_ok, label


# ------------------------------------------------------------------ design
DEFAULT_DESIGN = dict(
    base='#0c0b10', accent='#7020d2', accent2='#be6eff', text='#f0eef5',
    pattern='sweep', halftone=True, carbon=False,
    logo=None, tint_logo=True, logos=None, number='101', number_style='board', number_doors=True, number_roof=True,
    name='', team='RATTY RACING', wheel_colour=None, tyre_colour=None, lens_colour=None, beam_colour=None,
    team_places=None, name_places=None, pattern_image=None, pattern_mode='side_left', pattern_simplify='medium',
    pattern_recolour=False,
    win_tint=None, win_tint_dark=0.5, win_tint_windscreen=False,
    win_enable=False, win_clear=True, win_banner='RATTY RACING', win_banner_colour='#111111', win_text_colour='#ffffff',
    win_number=True, win_name=True, win_banner_height=0.12, win_side_place='rear', debug_decals=False,
    font_team=None, font_name=None, font_number=None, adjust=None, compress=True,
    font=DEFAULT_FONT,
)


PATTERNS = {
    'sweep': 'Sweep (rising band + dots)',
    'stripes': 'Twin centre stripes',
    'split': 'Two-tone split',
    'triple': 'Triple side stripes (classic 70s)',
    'centre_band': 'Centre band over the top',
    'chevron': 'Chevron nose',
    'hockey': 'Hockey stick',
    'tricolour': 'Tricolour diagonal bands',
    'fade': 'Front-to-rear fade',
    'chequer': 'Chequered flag fade',
    'shards': 'Geometric shards',
    'hex': 'Hexagon fade',
    'camo': 'Digital camo',
    'none': 'Plain (no pattern)',
}


def _hash(*ints):
    h = np.zeros_like(ints[0], dtype=np.int64)
    for k, v in zip((73856093, 19349663, 83492791, 2654435761), ints):
        h = h ^ (v.astype(np.int64) * k)
    return (h & 0x7fffffff) % 1000 / 1000.0


PATTERNS.update({
    'lightning': 'Lightning bolt',
    'sunburst': 'Sunburst rays',
    'tiger': 'Tiger stripes',
    'splatter': 'Paint splatter',
    'pinstripes': 'Pinstripe bundle',
    'picture': 'Pattern from a picture…',
})
PATTERNS['none'] = PATTERNS.pop('none')          # keep "plain" last
PICTURE_MODES = {'side_left': 'Side view of a car, front on the left',
                 'side_right': 'Side view of a car, front on the right',
                 'wrap': 'Flat pattern / wrap print'}
SIMPLIFY = {'off': 'Off (keep everything)', 'light': 'Light', 'medium': 'Medium (removes writing)', 'strong': 'Strong'}


def more_patterns(pat, col, P, N, car, sill, belt, base, acc, acc2, txt):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L = car.length; sh = belt - sill
    s = (car.hi[2] - z) / L
    hn = (y - sill) / max(sh, 1e-3)
    side = np.abs(N[:, 0]) > 0.45
    put = lambda m, c: np.where(m[:, None], np.asarray(c, np.float32), col)
    if pat == 'lightning':
        # a zig-zag bolt running along the side, front to rear
        k = (s * 7.0) % 1.0
        zz = np.where(k < 0.5, k * 2, 2 - k * 2)          # triangle wave 0..1
        c = 0.3 + 0.35 * zz
        col = put(side & (np.abs(hn - c) < 0.07) & (s > 0.04) & (s < 0.92), acc)
        col = put(side & (np.abs(hn - c) >= 0.07) & (np.abs(hn - c) < 0.1) & (s > 0.04) & (s < 0.92), acc2)
    elif pat == 'sunburst':
        fw = [c for w, c in car.wheels.items() if w.endswith('F')]
        cz = np.mean([c[2] for c in fw]) if fw else car.hi[2] - 0.25 * L
        cy = np.mean([c[1] for c in fw]) if fw else sill
        ang = np.arctan2(y - cy, cz - z)
        rays = (np.floor(ang / np.radians(9)) % 2) == 0
        dist = np.sqrt((z - cz) ** 2 + (y - cy) ** 2)
        col = put(side & rays & (dist > 0.45) & (dist < 1.6), acc)
    elif pat == 'tiger':
        w = np.sin(z * 9.0 + np.sin(y * 13.0) * 1.6 + np.sin(x * 7.0)) + 0.35 * np.sin(z * 23 + y * 17)
        col = put((w > 0.75) & (s > 0.2), acc)
    elif pat == 'splatter':
        g = 0.12
        cu, cv, cw = np.floor(z / g), np.floor(y / g), np.floor(x / g)
        out = np.zeros(len(P), bool)
        for dz in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cz_, cy_ = cu + dz, cv + dy
                r = _hash(cz_, cy_, cw)
                pz = (cz_ + _hash(cz_ + 3, cy_, cw)) * g; py = (cy_ + _hash(cz_, cy_ + 5, cw)) * g
                rad = np.where(r > 0.7, g * (0.15 + 0.6 * (r - 0.7)), 0)
                out |= ((z - pz) ** 2 + (y - py) ** 2) < rad ** 2
        dens = np.clip((s - 0.3) / 0.5, 0, 1)
        col = put(out & (_hash(cu, cv) < dens + 0.15), acc)
    elif pat == 'pinstripes':
        for k, c in enumerate((acc, acc2, acc, acc2, acc)):
            c0 = 0.38 + 0.045 * k
            col = put(side & (np.abs(hn - c0) < 0.012), c)
        col = put(~side & (np.abs(np.abs(x) - 0.12) < 0.01), acc)
    return col


def load_pattern_picture(path, mode, simplify, recolour, palette):
    """The picture as a simplified colour map (writing / small detail removed) + where it is valid."""
    im = Image.open(path).convert('RGB')
    im.thumbnail((1200, 1200), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    valid = np.ones(a.shape[:2], bool)
    if mode in ('side_left', 'side_right'):
        border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
        bg = np.median(border, 0)
        if border.std(0).mean() < 30:                # plain background: cut the car out of it
            fg = np.sqrt(((a - bg) ** 2).sum(-1)) > 40
            fgi = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
            fg = np.asarray(fgi) > 127
            ys, xs = np.nonzero(fg)
            if len(ys):
                y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
                a, valid = a[y0:y1, x0:x1], fg[y0:y1, x0:x1]
        if mode == 'side_right':
            a, valid = a[:, ::-1], valid[:, ::-1]
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    size = {'off': 0, 'light': 5, 'medium': 9, 'strong': 15}.get(simplify, 9)
    if size:
        k = 8 if simplify == 'light' else 6
        q = img.quantize(k, method=Image.Quantize.MEDIANCUT)
        for _ in range(3):
            q = q.filter(ImageFilter.ModeFilter(size))  # small things (writing, stickers) melt into what surrounds them
        img = q.convert('RGB')
    a = np.asarray(img).astype(np.float32)
    if recolour:
        cols, inv = np.unique(a.reshape(-1, 3), axis=0, return_inverse=True)
        cnt = np.bincount(inv.ravel(), weights=valid.ravel().astype(float))
        order = np.argsort(-cnt)
        pal = [np.asarray(c, np.float32) for c in palette]
        newc = cols.copy()
        for rank, ci in enumerate(order):
            if rank < len(pal):
                newc[ci] = pal[rank]
            else:   # extra colours: the palette colour of nearest brightness
                lum = cols[ci] @ np.array([0.3, 0.59, 0.11])
                newc[ci] = min(pal, key=lambda p: abs(p @ np.array([0.3, 0.59, 0.11]) - lum))
        a = newc[inv.ravel()].reshape(a.shape)
    # fill outside the car silhouette with the nearest car colour (so arches / edges don't pick up background)
    if not valid.all():
        fill = a.copy(); ok = valid.copy()
        for _ in range(60):
            if ok.all(): break
            acc_ = np.zeros_like(fill); n = np.zeros(ok.shape, np.float32)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sh_ok = np.roll(ok, (dy, dx), (0, 1)); sh_f = np.roll(fill, (dy, dx), (0, 1))
                acc_ += sh_f * sh_ok[..., None]; n += sh_ok
            grow = (~ok) & (n > 0)
            fill[grow] = acc_[grow] / n[grow, None]; ok = ok | grow
        a = fill
    return a


_PICTURE_CACHE = {}


def picture_pattern(design, P, N, car, sill, belt, palette, log=print):
    path = design.get('pattern_image')
    if not path or not os.path.isfile(path):
        log('pattern picture: none chosen - left plain'); return None
    mode = design.get('pattern_mode') or 'wrap'
    key = (path, os.path.getmtime(path), mode, design.get('pattern_simplify') or 'medium', bool(design.get('pattern_recolour')),
           tuple(tuple(np.asarray(c).tolist()) for c in palette))
    if key not in _PICTURE_CACHE:                      # the pattern is worked out several times per skin: load it once
        _PICTURE_CACHE.clear()
        _PICTURE_CACHE[key] = load_pattern_picture(path, mode, key[3], key[4], palette)
    a = _PICTURE_CACHE[key]
    H, W = a.shape[:2]
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L = car.length
    s = np.clip((car.hi[2] - z) / L, 0, 1)                       # 0 front .. 1 rear
    if mode in ('side_left', 'side_right'):
        # the picture's car is stretched over this car's side profile; top / front / rear take the
        # colour of the profile at the same point along the car and height
        top_y = car.hi[1]; bot_y = car.lo[1]
        v = np.clip((top_y - y) / (top_y - bot_y), 0, 1)
        u = s
    else:
        # flat print: spans the car's length; side texels use height, top texels use width across
        side = np.abs(N[:, 0]) > 0.45
        span = (car.hi[1] - car.lo[1]) / L * W                      # picture rows covering the car height
        u = s
        v_side = (car.hi[1] - y) / (car.hi[1] - car.lo[1]) * min(1.0, span / H)
        v_top = (x - car.lo[0]) / (car.hi[0] - car.lo[0]) * min(1.0, span / H)
        v = np.clip(np.where(side, v_side, v_top), 0, 1)
    log(f'pattern picture: {os.path.basename(path)} ({PICTURE_MODES.get(mode, mode)})')
    return bilinear(a, u * (W - 1), v * (H - 1))


def extra_pattern(pat, col, P, N, car, sill, belt, base, acc, acc2, txt):
    """Patterns made from 3D functions of the car's surface (so they wrap round it seamlessly)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L = car.length; sh = belt - sill
    s = (car.hi[2] - z) / L                       # 0 front .. 1 rear
    hn = (y - sill) / max(sh, 1e-3)               # 0 sill .. 1 window line
    half = (car.hi[0] - car.lo[0]) / 2
    side = np.abs(N[:, 0]) > 0.45
    put = lambda m, c: np.where(m[:, None], np.asarray(c, np.float32), col)

    if pat == 'triple':
        # three parallel stripes along the side, lifting towards the nose
        c0 = 0.55 + 0.18 * np.clip(0.35 - s, 0, 1)
        for off, c in ((0.0, acc), (0.075, acc2), (0.15, txt)):
            d = hn - (c0 - off)
            col = put(side & (d > 0) & (d < 0.055), c)
    elif pat == 'centre_band':
        w = 0.3 * half
        col = put(np.abs(x) < w, acc)
        col = put((np.abs(x) >= w + 0.02) & (np.abs(x) < w + 0.045), acc2)
        col = put(side & (hn > 0.42) & (hn < 0.52), acc)
    elif pat == 'chevron':
        q = np.where(side, np.abs(hn - 0.5) * 1.1, np.abs(x) / half)
        edge = 0.42 - 0.3 * q
        col = put(s < edge, acc)
        col = put((s >= edge) & (s < edge + 0.025), acc2)
    elif pat == 'hockey':
        # band low along the side that kicks up to the window line in front of the rear wheel
        t = np.clip((s - 0.62) / 0.12, 0, 1)
        lo_, hi_ = 0.12 + 0.6 * t ** 2, 0.38 + 0.62 * t ** 2
        band = side & (hn > lo_) & (hn < hi_) & (s < 0.8)
        col = put(band, acc)
        col = put(side & (hn >= hi_) & (hn < hi_ + 0.05) & (s < 0.8), acc2)
    elif pat == 'tricolour':
        u = hn - 0.9 * (0.75 - s)
        for k, c in enumerate((acc, acc2, txt)):
            col = put(side & (u > 0.05 + 0.13 * k) & (u < 0.15 + 0.13 * k), c)
        col = put(~side & (np.abs(x) < 0.2 * half) & (np.abs(x) > 0.14 * half), acc)
    elif pat == 'fade':
        t = np.clip((s - 0.25) / 0.6, 0, 1)[:, None]
        col = col * (1 - t) + np.asarray(acc, np.float32) * t
        g = 0.03; gz = np.round(z / g); gy = np.round(y / g); gx = np.round(x / g)
        d = np.sqrt((z - gz * g) ** 2 + np.where(side, (y - gy * g) ** 2, (x - gx * g) ** 2))
        r = g * 0.45 * np.clip(1 - np.abs(s - 0.25) / 0.18, 0, 1)
        col = put((d < r) & (s < 0.25), acc)
    elif pat == 'chequer':
        g = 0.07
        cu = np.floor(z / g); cv = np.floor(np.where(side, y, x) / g)
        dark = ((cu + cv) % 2) == 0
        keep = _hash(cu, cv) < np.clip((s - 0.45) / 0.45, 0, 1) * 1.2
        col = put(dark & keep, acc)
    elif pat == 'shards':
        a = np.radians(28)
        u = z * np.cos(a) + np.where(side, y, x) * np.sin(a)
        cell = np.floor(u / 0.11)
        r = _hash(cell, np.floor(np.where(side, y, x) / 0.35))
        zone = np.clip((s - 0.35) / 0.4, 0, 1)
        col = put((r < 0.22 * zone + 0.02) & (s > 0.35), acc)
        col = put((r > 1 - 0.12 * zone) & (s > 0.35), acc2)
    elif pat == 'hex':
        g = 0.05
        su = z / (g * 1.5); col_i = np.floor(su)
        sv = (np.where(side, y, x) / (g * np.sqrt(3))) - 0.5 * (col_i % 2)
        row_i = np.floor(sv)
        fu, fv = su - col_i - 0.5, sv - row_i - 0.5
        d = np.maximum(np.abs(fv), (np.abs(fu) * 1.5 + np.abs(fv)) / 2)
        size = np.clip((s - 0.4) / 0.5, 0, 1) * 0.45
        col = put(d < size, acc)
    elif pat == 'camo':
        g = 0.09
        c1 = _hash(np.floor(x / g), np.floor(y / g), np.floor(z / g))
        c2 = _hash(np.floor(x / (g * 2.3)) + 7, np.floor(y / (g * 2.3)), np.floor(z / (g * 2.3)))
        v = 0.6 * c2 + 0.4 * c1
        mid = (np.asarray(base, np.float32) + np.asarray(acc, np.float32)) / 2
        col = put(v > 0.55, mid)
        col = put(v > 0.72, acc)
        col = put(v < 0.18, acc2)
    return col


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
    zs = zc[ok] if ok.any() else (zc[mid] if mid.any() else zc)
    df, dr = zs.max(), zs.min()
    fw = [c[2] for w, c in car.wheels.items() if w.endswith('F')]
    rw = [c[2] for w, c in car.wheels.items() if w.endswith('R')]
    if fw and rw:   # doors sit between the wheel arches
        r = car.wheel_r
        df, dr = np.mean(fw) - r - 0.08, np.mean(rw) + r + 0.08
    return dict(sill=sill, belt=belt, door_front=df, door_rear=dr)


def top_panels(car, tm, paint, belt, tm_tex=None):
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
    if len(roof) > 200:
        # the roof is the longest unbroken stretch of high surface: a rear wing or roof spoiler standing
        # behind a gap (the rear window) is not part of it
        zb = np.floor((roof[:, 2] - roof[:, 2].min()) / 0.04).astype(int)
        cnt = np.bincount(zb)
        on = np.r_[False, cnt > 0.08 * cnt.max(), False]
        edges = np.flatnonzero(np.diff(on.astype(int)))
        runs = sorted(zip(edges[::2], edges[1::2]), key=lambda r_: cnt[r_[0]:r_[1]].sum())
        if runs:
            r0, r1 = runs[-1]
            roof = roof[(zb >= r0) & (zb < r1)]
    for name, Q in (('roof', roof), ('bonnet', flat[flat[:, 2] > mid]), ('boot', flat[flat[:, 2] < mid])):
        if len(Q) < 200: continue
        z5, z95 = np.percentile(Q[:, 2], [3, 97]); x5, x95 = np.percentile(Q[:, 0], [3, 97])
        out[name] = ((z5 + z95) / 2, z95 - z5, x95 - x5)
    # where the model names its bonnet / boot lid, writing there is kept to that part's width (flat wing
    # tops beside the bonnet would otherwise count as bonnet, and the writing runs onto them)
    names = {'bonnet': re.compile(r'hood|bonnet|capot|cofano|motorhaube', re.I),
             'boot': re.compile(r'trunk|boot|tailgate|bootlid|hatch|coffre|baule|heckklappe', re.I)}
    skip = re.compile(r'liner|hinge|emblem|badge|pin|scoop|vent|light|lamp|handle|lock|bay|int', re.I)
    for name, rx in names.items():
        if name not in out: continue
        ms = [m for m in car.meshes_for(tm_tex) if rx.search(m.name) and not skip.search(m.name)] if tm_tex else []
        if not ms: continue
        Q = np.concatenate([m.pos for m in ms])
        w = float(np.percentile(Q[:, 0], 97) - np.percentile(Q[:, 0], 3))
        if 0.3 < w < out[name][2]:
            out[name] = (out[name][0], out[name][1], w)
    return out


PATTERN_AA = True       # patterns worked out at 4 points per texel (smooth edges)


def pattern_colours(design, P, N, car, sill, belt, log=print):
    """The livery pattern (no decals) at points P with normals N."""
    base, acc, acc2, txt = (rgb(design[k]) for k in ('base', 'accent', 'accent2', 'text'))
    n = len(P)
    col = np.tile(base, (n, 1))
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    zf, zr = car.hi[2], car.lo[2]
    L = car.length
    s = (zf - z) / L                                     # 0 at the front, 1 at the rear
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

    if pat == 'picture':
        pc = picture_pattern(design, P, N, car, sill, belt, (base, acc, acc2, txt), log)
        if pc is not None: col = pc
    elif pat in ('lightning', 'sunburst', 'tiger', 'splatter', 'pinstripes'):
        col = more_patterns(pat, col, P, N, car, sill, belt, base, acc, acc2, txt)
    elif pat not in ('sweep', 'stripes', 'split', 'none'):
        col = extra_pattern(pat, col, P, N, car, sill, belt, base, acc, acc2, txt)

    return col


class SwatchCar:
    """A plain 4.2 m car shape for the pattern preview in the app."""
    lo, hi = np.array([-0.85, 0.0, -2.1]), np.array([0.85, 1.35, 2.1])
    length, wheel_r = 4.2, 0.3
    wheels = {'WHEEL_LF': np.array([0.75, 0.3, 1.35]), 'WHEEL_RF': np.array([-0.75, 0.3, 1.35]),
              'WHEEL_LR': np.array([0.75, 0.3, -1.35]), 'WHEEL_RR': np.array([-0.75, 0.3, -1.35])}


def pattern_swatch(design, width=300):
    """A small picture of the pattern: the car's left side over its top view (front on the left)."""
    car = SwatchCar()
    hs, ht = int(width * 0.3), int(width * 0.22)
    zz = np.linspace(car.hi[2], car.lo[2], width * 2)
    out = []
    for h, plane in ((hs, 'side'), (ht, 'top')):
        if plane == 'side':
            yy = np.linspace(1.2, 0.05, h * 2)
            Z, Y = np.meshgrid(zz, yy); X = np.full_like(Z, 0.86)
            N = np.tile([1.0, 0, 0], (Z.size, 1))
        else:
            xs = np.linspace(0.8, -0.8, h * 2)
            Z, X = np.meshgrid(zz, xs); Y = np.full_like(Z, 1.3)
            N = np.tile([0, 1.0, 0], (Z.size, 1))
        P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        c = pattern_colours(dict(design, pattern_image=design.get('pattern_image')), P, N, car, 0.15, 0.8, lambda m: None)
        im = Image.fromarray(np.clip(c, 0, 255).reshape(Z.shape + (3,)).astype(np.uint8)).resize((width, h), Image.LANCZOS)
        out.append(im)
    sheet = Image.new('RGB', (width, hs + ht + 4), (235, 236, 240))
    sheet.paste(out[0], (0, 0)); sheet.paste(out[1], (0, hs + 4))
    return sheet


def render_design(car, tm, paint, design, log=print, info=None, ctx=None, mem=None):
    """Return an (n_texels, 3) colour array for the texels in tm (car-space design) and which
    texels a decal covers."""
    P, N = tm.P, tm.N
    base, acc, acc2, txt = (rgb(design[k]) for k in ('base', 'accent', 'accent2', 'text'))
    n = len(P)
    col = np.tile(base, (n, 1))
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # the main body texture sets the car's lines and where every decal goes; other paint textures (stripe
    # panels, a second body texture) reuse them, so the design runs on across them unbroken
    ctx = {} if ctx is None else ctx
    first = 'decals' not in ctx
    prof = ctx['prof'] = ctx['prof'] if 'prof' in ctx else side_profile(car, tm, paint)
    sill, belt = prof['sill'], prof['belt']
    zf, zr = car.hi[2], car.lo[2]
    L = car.length
    log(f"side panels: sill {sill:.2f} m, belt line {belt:.2f} m, doors z {prof['door_rear']:+.2f}..{prof['door_front']:+.2f}")

    # patterns are worked out at four points inside every texel and averaged, so edges are smooth, not stepped
    if mem is not None and 'pattern' in mem:
        col = mem['pattern'].copy()                    # same pattern as last time: only the decals change
    elif PATTERN_AA and tm is not None and getattr(tm, 't_px', None) is not None:
        col = np.zeros((n, 3))
        for k, (dx, dy) in enumerate(((-0.125, -0.375), (0.375, -0.125), (0.125, 0.375), (-0.375, 0.125))):
            for c0 in range(0, n, 1 << 21):            # in pieces, so 4K textures do not need much memory
                sl = slice(c0, min(n, c0 + (1 << 21)))
                Pk, Nk = locate_texels(tm.t_px, tm.t_pos, tm.t_nrm, tm.tri[sl], tm.xx[sl] + dx, tm.yy[sl] + dy)
                col[sl] += pattern_colours(design, Pk, Nk, car, sill, belt, log if (k == 0 and c0 == 0) else (lambda m: None))
        col /= 4
    else:
        col = pattern_colours(design, P, N, car, sill, belt, log)
    if mem is not None and 'pattern' not in mem: mem['pattern'] = col.copy()

    # ---- decals
    decals = ctx['decals'] = place_decals(car, tm, paint, design, prof, base, acc, acc2, txt, log) if first else ctx['decals']
    if info is not None:
        have = {(d_['key'], d_['view']) for d_ in info.setdefault('decals', [])}
        for dc in decals:
            if (dc.key, dc.view) not in have:
                info['decals'].append(dict(key=dc.key, label=dc.label, view=dc.view, a=float(dc.a), b=float(dc.b), h=float(dc.height),
                                           w=float(dc.width or dc.height * dc.img.width / dc.img.height), rot=float(dc.rot)))
    col, _, forced, _ = apply_decals(col, tm, decals, log if first else (lambda m: None),
                                     debug=bool(design.get('debug_decals')), allow_move=first)
    return np.clip(col, 0, 255), forced


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
    fnt_team = design.get('font_team') or fnt
    fnt_name = design.get('font_name') or fnt
    fnt_num = design.get('font_number') or fnt
    door_len = prof['door_front'] - prof['door_rear']
    pan = top_panels(car, tm, paint, belt, getattr(tm, 'tex', None))
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
    wide = car.hi[0] - car.lo[0]
    # how wide a decal may be at each place (metres)
    room = {'doors': 0.95 * door_len, 'lower_doors': 0.95 * door_len, 'front_wings': 0.9 * max(zf - prof['door_front'], 0.3),
            'rear_quarters': 0.9 * max(prof['door_rear'] - zr, 0.3), 'rear': 0.8 * wide, 'front': 0.8 * wide}
    for k_ in ('bonnet', 'roof', 'boot'):
        if k_ in pan: room[k_] = 0.85 * pan[k_][2]

    def put(place, img, scale=1.0, glow=None, b_shift=0.0, what='logo', key=None, share=1, a_shift=0.0):
        for view, a, b, h, reg, facing, rot in geo(place):
            hh = h * scale
            lim = room.get(place)
            if lim and hh * img.width / img.height > lim / share:   # long writing: shrink it to the panel, never run off it
                hh = lim / share * img.height / img.width
            if a_shift: a = a + (-a_shift if view == 'right' else a_shift)   # along the car, the same way on both sides
            decals.append(Decal(img, view, a, b + b_shift * h, hh, rot=rot, region=reg, glow=glow, facing=facing,
                                label=f'{what} on the {PLACES[place].lower()} ({view})',
                                key=key or f'{what}:{place}', kind='logo' if what == 'logo' else 'text'))

    team, name = (design.get('team') or '').strip(), (design.get('name') or '').strip()
    adj = design.get('adjust') or {}
    tplaces = design.get('team_places') or ['front_wings', 'boot', 'rear', 'front']
    nplaces = design.get('name_places') or ['front_wings']
    written = {p for p in PLACES if (team and p in tplaces) or (name and p in nplaces)}

    # logos from the library (one per place; later ones win)
    logos = list(design.get('logos') or [])
    if design.get('logo'):
        logos += [dict(path=design['logo'], place=p, tint=design.get('tint_logo', True)) for p in ('doors', 'bonnet')]
    taken = set()
    by_place = {}                                  # every logo asked for goes on: several on one panel sit side by side
    for lg in logos:
        p = lg.get('place')
        if p not in PLACES or not lg.get('path') or not os.path.isfile(lg['path']): continue
        try:
            img = prep_logo(lg['path'], acc2 if lg.get('tint') else None, lg.get('bg', 'auto'))
        except Exception as e:
            log(f'logo {os.path.basename(lg["path"])}: cannot read it ({e})'); continue
        by_place.setdefault(p, []).append(img)
    for p, imgs in by_place.items():
        n = len(imgs)
        sc = (0.68 if p in written else 1.0) * (1.0 if n == 1 else max(0.45, 1.0 / n ** 0.5))
        h0 = geo(p)[0][3] * sc if geo(p) else 0.0
        lim = room.get(p)
        ws = []
        for img in imgs:
            hh = h0
            if lim and hh * img.width / img.height > lim / n: hh = lim / n * img.height / img.width
            ws.append(hh * img.width / img.height)
        gap = 0.03
        total = sum(ws) + gap * (n - 1)
        x = -total / 2
        for i, img in enumerate(imgs):
            is_pic = bool(img.info.get('picture'))
            # a place with writing as well: the logo is made smaller and moved up, the writing goes under it
            put(p, img, glow=acc2 if p in ('doors', 'bonnet') and not is_pic else None,
                key=f'logo:{p}' if i == 0 else f'logo:{p}:{i + 1}', share=n, a_shift=x + ws[i] / 2 if n > 1 else 0.0,
                scale=sc, **(dict(b_shift=0.16) if p in written else {}))
            x += ws[i] + gap
        if n > 1: log(f'{n} logos on the {PLACES[p].lower()}: side by side - move them on the preview')
        taken.add(p)

    # racing number
    num = str(design.get('number') or '').strip()
    style = design.get('number_style') or 'board'
    if num and style != 'none':
        if design.get('number_doors', True):
            z = prof['door_rear'] + 0.7 * door_len
            if style == 'board':
                img = number_board(num, txt, readable(base, txt, acc, acc2), edge, fnt_num)
            else:
                img = text_image(num, 300, t_txt, fnt_num, stroke=0.05, stroke_color=base, track=-0.02)
            for view, a, b, h, reg, facing, rot in sides(z, sill + 0.55 * sh, min(0.42, sh * 0.62)):
                decals.append(Decal(img, view, a, b, h, region=reg, label=f'number on the doors ({view})',
                                    key='number:doors', kind='number'))
        if design.get('number_roof', True) and 'roof' in pan:
            zc, ln, wd = pan['roof']
            zc_n = zc + (0.12 * ln if 'roof' in taken else 0)
            decals.append(Decal(text_image(num, 300, t_txt, fnt_num, stroke=0.04, stroke_color=base), 'roof_l',
                                -zc_n, 0.0, min(wd * 0.45, ln * 0.45), region=lambda P: P[:, 1] > car.hi[1] - 0.3,
                                label='number on the roof', key='number:roof', kind='number'))

    # team wordmark + driver name, at the places chosen
    scale = {'front_wings': 0.62, 'lower_doors': 1.0, 'rear_quarters': 0.55, 'doors': 0.3, 'bonnet': 0.3,
             'roof': 0.5, 'boot': 0.4, 'rear': 0.7, 'front': 0.65}
    for p in PLACES:
        if p in ('windscreen', 'rear_window', 'side_windows'): continue
        t_on, n_on = bool(team) and p in tplaces, bool(name) and p in nplaces
        if not (t_on or n_on): continue
        sc = scale.get(p, 0.5)
        tc = t_acc2 if p == 'front' else t_txt
        ol = dict(stroke=0.045, stroke_color=base)     # outline: stays readable where it crosses a pattern band
        # each box can have its own words, font and colour (set on the preview)
        ot, on_ = adj.get(f'team name:{p}', {}), adj.get(f'driver name:{p}', {})
        t_img = text_image(ot.get('text') or team, 200, rgb(ot['colour']) if ot.get('colour') else tc, ot.get('font') or fnt_team,
                           **ol) if t_on else None
        n_img = text_image(on_.get('text') or name, 200,
                           rgb(on_['colour']) if on_.get('colour') else (t_acc2 if (t_on or p != 'front') else t_txt),
                           on_.get('font') or fnt_name, style='SemiBold Condensed', track=0.12 if t_on else 0.1, **ol) if n_on else None
        if p in taken:                                  # under the logo (which was made smaller for this)
            if t_on and n_on:
                put(p, t_img, scale=0.15, b_shift=-0.33, what='team name')
                put(p, n_img, scale=0.09, b_shift=-0.47, what='driver name')
            else:
                put(p, t_img or n_img, scale=0.17, b_shift=-0.36, what='team name' if t_on else 'driver name')
        elif t_on and n_on:
            put(p, t_img, scale=sc, b_shift=0.16, what='team name')
            put(p, n_img, scale=sc * 0.52, b_shift=-0.42 * min(1, sc / 0.62), what='driver name')
        elif t_on:
            put(p, t_img, scale=sc, what='team name')
        else:
            put(p, n_img, scale=sc * 0.8, what='driver name')
    return arrange_decals(decals, design, log, {'left': (sill, belt), 'right': (sill, belt)})


def _rect(dc):
    """A decal's box in its surface group (roof numbers are turned into the top view's axes): group, a, b, w, h."""
    h = dc.height; w = dc.width or h * dc.img.width / dc.img.height
    if dc.rot % 180 == 90: w, h = h, w
    if dc.view == 'roof_l': return 'top', -dc.b, dc.a, h, w
    return dc.view, dc.a, dc.b, w, h


def _set_centre(dc, a, b):
    if dc.view == 'roof_l': dc.a, dc.b = b, -a
    else: dc.a, dc.b = a, b


def arrange_decals(decals, design, log, limits=None):
    """Decals go where they were asked for - overlapping ones too (Nik, 11 Nov: never moved, shrunk or left off
    because they cover each other; they can be moved on the preview). Deleted ones are left off, then the hand
    adjustments from the preview (move / size / turn / flip) are applied."""
    adj = design.get('adjust') or {}
    gone = [d for d in decals if adj.get(d.key, {}).get('deleted')]
    if gone:
        decals = [d for d in decals if d not in gone]
        log(f'left off (deleted on the preview): {", ".join(sorted({d.label.split(" (")[0] for d in gone}))}')
    return hand_adjust(decals, adj)


def hand_adjust(decals, adj):
    """The changes made on the preview (move / size / turn / flip), the same on both sides of the car."""
    for dc in decals:
        ad = adj.get(dc.key)
        if not ad: continue
        sgn = -1 if dc.view == 'right' else 1            # the same change on both sides of the car
        dc.a += sgn * float(ad.get('da', 0)); dc.b += float(ad.get('db', 0))
        dc.height *= float(ad.get('scale', 1)); dc.rot += sgn * float(ad.get('rot', 0))
        dc.flip = dc.view in (ad.get('flip') or [])
        dc.by_hand = True
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


MIN_FACING = 0.03          # only surfaces facing completely away (backs of panels) are left out
DEPTH_CELL = 0.005         # 5 mm grid for the outer-surface test
DEBUG_COLOURS = [(255, 0, 255), (0, 255, 255), (255, 255, 0), (255, 128, 0), (0, 128, 255), (128, 255, 0),
                 (255, 0, 128), (128, 0, 255)]


def decal_size(dc, texel_m):
    """The decal's picture (rotated, with glow, sized for the texture) and its size on the car (h, w in metres)."""
    img = ImageOps.mirror(dc.img) if getattr(dc, 'flip', False) else dc.img
    if dc.rot:
        h0 = img.height
        img = img.rotate(dc.rot, expand=True, resample=Image.BICUBIC)
    hscale = dc.height * (img.height / h0 if dc.rot else 1.0)      # height = the picture's own height, before turning
    if dc.glow is not None:
        pad = img.height // 6
        g = Image.new('RGBA', (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
        g.paste(img, (pad, pad))
        halo = g.getchannel('A').filter(ImageFilter.GaussianBlur(pad / 2)).point(lambda v: int(v * 0.6))
        gl = Image.new('RGBA', g.size, tuple(int(v) for v in dc.glow) + (0,)); gl.putalpha(halo)
        gl.alpha_composite(g)
        hscale = dc.height * gl.height / max(1, img.height)
        img = gl
    aspect = img.width / img.height
    hm = hscale
    wm = dc.width if dc.width else hscale * aspect
    want_h = int(np.clip(hm / texel_m * 1.5, 8, img.height))
    if want_h < img.height:
        img = img.resize((max(2, int(img.width * want_h / img.height)), want_h), Image.LANCZOS)
    return img, hm, wm


def decal_hits(tm, dc, hm, wm, a_shift=0.0, inside=False, b_shift=0.0):
    """Texels the decal lands on: the outer surface inside its footprint, however steeply it is angled.
    Hidden surfaces behind the outer skin (arch liners, doubled panels, damage meshes) get nothing.
    The decal is painted through the triangles that are really visible there, nearest last - so where
    the car's UVs fold over themselves the visible surface still gets the whole picture.
    Returns texel indices and their (a, b) position in the decal (metres from its centre)."""
    vdir, fa, fb = VIEWS[dc.view]
    none = (np.zeros(0, np.int64), np.zeros(0), np.zeros(0))

    def ab(P):
        a, b = dc.coords(P) if dc.coords is not None else (fa(P), fb(P))
        return a - (dc.a + a_shift), b - (dc.b + b_shift)
    # 1. triangles that reach into the footprint and face the viewer
    T, TN = tm.t_pos, tm.t_nrm
    a, b = ab(T.reshape(-1, 3)); a, b = a.reshape(-1, 3), b.reshape(-1, 3)
    f = TN.mean(1) @ vdir
    if inside: f = -f
    ok = (a.min(1) < wm / 2) & (a.max(1) > -wm / 2) & (b.min(1) < hm / 2) & (b.max(1) > -hm / 2) & (f > MIN_FACING)
    if dc.region is not None: ok &= dc.region(T.mean(1))
    thin = np.nonzero(ok & ~tm.t_good)[0]        # mouldings / strips with next to no room in the texture
    C = np.nonzero(ok & tm.t_good)[0]
    if not len(C): return none
    # 2. the outer surface: points spread over those triangles, front-most per 5 mm cell
    S, rep = sample_tris(T[C], 0.003, with_index=True)
    sa, sb = ab(S)
    ins = (np.abs(sa) < wm / 2) & (np.abs(sb) < hm / 2)
    S, rep, sa, sb = S[ins], rep[ins], sa[ins], sb[ins]
    if not len(S): return none
    sd = S @ vdir
    # parts standing well in front of the panel (mirrors, wing end plates) neither take the decal nor hide it
    mid = (np.abs(sa) < 0.2 * wm) & (np.abs(sb) < 0.2 * hm)
    z_lim = np.percentile(sd[mid], 90) + 0.12 if mid.sum() > 20 else np.inf
    near = sd < z_lim
    ny = int(hm / DEPTH_CELL) + 2
    cell = lambda a_, b_: ((a_ + wm / 2) / DEPTH_CELL).astype(np.int64) * ny + ((b_ + hm / 2) / DEPTH_CELL).astype(np.int64)
    zmax = np.full((int(wm / DEPTH_CELL) + 2) * ny, -np.inf)
    np.maximum.at(zmax, cell(sa[near], sb[near]), sd[near])
    if len(thin):                                # they cannot show a picture, but they do hide what is behind them
        O = sample_tris(T[thin], 0.004)
        oa, ob = ab(O); od = O @ vdir
        k_ = (np.abs(oa) < wm / 2) & (np.abs(ob) < hm / 2) & (od < z_lim)
        np.maximum.at(zmax, cell(oa[k_], ob[k_]), od[k_])
    # other solid parts of the car lying over the panel (sill trims, bumpers, strips) hide the paint under them
    occ = getattr(tm, 'occluders', None)
    if occ is not None and len(occ) and not inside:
        oa, ob = ab(occ.reshape(-1, 3)); oa, ob = oa.reshape(-1, 3), ob.reshape(-1, 3)
        o_in = (oa.min(1) < wm / 2) & (oa.max(1) > -wm / 2) & (ob.min(1) < hm / 2) & (ob.max(1) > -hm / 2)
        if dc.region is not None and o_in.any(): o_in[o_in] = dc.region(occ[o_in].mean(1))
        if o_in.any():
            O = sample_tris(occ[o_in], 0.004)
            oa, ob = ab(O); od = O @ vdir
            k_ = (np.abs(oa) < wm / 2) & (np.abs(ob) < hm / 2) & (od < z_lim)
            np.maximum.at(zmax, cell(oa[k_], ob[k_]), od[k_])

    def tol(f_):
        fc = np.clip(f_, 0.05, 1.0)
        return 0.015 + np.minimum(0.04, DEPTH_CELL * np.sqrt(1 - fc ** 2) / fc)
    vis = near & (sd > zmax[cell(sa, sb)] - tol(f[C][rep]))
    V = C[np.unique(rep[vis])]
    if not len(V): return none
    # 3. those triangles drawn into the texture, far ones first: each texel belongs to the nearest visible one
    order = V[np.argsort(T[V].mean(1) @ vdir)]
    ids, x0, y0 = raster_tris(tm.t_px, order, tm.W, tm.H, crop=True)
    yy, xx = np.nonzero(ids >= 0)
    t = ids[yy, xx]
    yy += y0; xx += x0
    idx = tm.index[yy, xx]
    on = idx >= 0
    yy, xx, t, idx = yy[on], xx[on], t[on], idx[on]
    P, N = locate_texels(tm.t_px, T, TN, t, xx, yy)
    a, b = ab(P)
    fp = N @ vdir
    if inside: fp = -fp
    d = P @ vdir
    keep = (np.abs(a) < wm / 2) & (np.abs(b) < hm / 2) & (fp > MIN_FACING) & (d < z_lim)
    idx, a, b, fp, d = idx[keep], a[keep], b[keep], fp[keep], d[keep]
    t = t[keep]
    keep = d > zmax[cell(a, b)] - tol(fp)
    # parts whose piece of the texture is squeezed small (mouldings, strips) take the colour but cannot show
    # a picture: the placement check counts them as "not showing"
    tm.last_sharp = tm.tri_size[t[keep]] < 3.0 * tm.texel_m
    return idx[keep].astype(np.int64), a[keep], b[keep]


def coverage(img, a, b, wm, hm, ok=None):
    """How much of the picture's solid part landed on the car (0..1), on a 1 cm grid. ok: which hits count."""
    if ok is not None and len(ok) == len(a): a, b = a[ok], b[ok]
    nx, ny = max(2, int(wm / 0.01)), max(2, int(hm / 0.01))
    solid = np.asarray(img.getchannel('A').resize((nx, ny), Image.BILINEAR)) > 64
    if not solid.any(): return 1.0
    got = np.zeros((ny, nx), bool)
    got[np.clip(((0.5 - b / hm) * ny).astype(int), 0, ny - 1), np.clip(((a / wm + 0.5) * nx).astype(int), 0, nx - 1)] = True
    return float((got & solid).sum() / solid.sum())


def place_hits(tm, dc, hm, wm, log, inside=False, allow_move=True, no_shared=False, img=None, others=()):
    """decal_hits, but never on texels the left and right of the car share (writing would be mirrored):
    a side decal slides along the car to get clear of them; if it cannot, it is left off whole."""
    idx, a, b = decal_hits(tm, dc, hm, wm, 0.0, inside)
    if not len(idx): return None
    name = dc.label or dc.view
    if no_shared and not dc.mirror_ok and tm.shared[tm.yy[idx], tm.xx[idx]].mean() >= 0.004:
        log(f'  {name}: note - this glass shares its picture with another window, so it shows there too')
    if allow_move and img is not None and dc.coords is None and not getattr(dc, 'by_hand', False):
        # placement check: is the whole picture on the panel? If part of it hangs off (over the sill, a
        # panel edge, an opening) it is slid to where it fits best
        cov = coverage(img, a, b, wm, hm, tm.last_sharp)
        if cov < 0.985:
            best = (cov, 0.0, 0.0, idx, a, b)
            g, ra, rb, rw, rh = _rect(dc)

            def free(da, db):                           # other decals may overlap it: moved on the preview if wanted
                return True
            for da, db in ((0, .02), (0, -.02), (0, .04), (0, -.04), (0, .06), (0, -.06), (0, .1), (0, -.1), (.05, 0), (-.05, 0),
                           (.1, 0), (-.1, 0), (.05, -.04), (-.05, -.04), (0, .15)):
                if not free(da, db): continue
                i2, a2, b2 = decal_hits(tm, dc, hm, wm, da, inside, db)
                c2 = coverage(img, a2, b2, wm, hm, tm.last_sharp) if len(i2) else 0
                if c2 > best[0] + 0.01: best = (c2, da, db, i2, a2, b2)
                if best[0] >= 0.99: break
            if best[1] or best[2]:
                c2, da, db, idx, a, b = best
                dc.a += da; dc.b += db
                log(f'  placement check: {name} moved {abs(da + db) * 100:.0f} cm to sit on the panel ({cov * 100:.0f}% -> {c2 * 100:.0f}% of it showing)')
            elif cov < 0.85:
                log(f'  placement check: only {cov * 100:.0f}% of the {name} fits on the car there - move or shrink it on the preview')
    frac = tm.mirrored[tm.yy[idx], tm.xx[idx]].mean()
    if frac >= 0.25 and not dc.mirror_ok:          # only worth a note when much of it is shared
        log(f'  {name}: put where asked - note the car uses one picture for both sides here, so it also shows '
            f'(mirrored) on the other side. Move it on the preview if you do not like it.')
    return idx, a, b


def apply_decals(col, tm, decals, log, alp=None, inside=False, back=None, debug=False, allow_move=True, quiet=False,
                 no_shared=False):
    """Draw the decals over the texel colours `col`. With `alp` (glass): stickers are opaque and inside
    glass shows their back. Returns col, alp, the texels covered by a decal, and which decals landed."""
    forced = np.zeros(len(col), bool)
    got = []
    for k, dc in enumerate(decals):
        img, hm, wm = decal_size(dc, tm.texel_m)
        h0 = dc.height
        hit = place_hits(tm, dc, hm, wm, log, inside, allow_move, no_shared, img if alp is None else None, decals)
        if not hit:
            if hit is None and not quiet: log(f'  {dc.label or dc.view}: no surface found')
            continue
        if dc.height != h0: img, hm, wm = decal_size(dc, tm.texel_m)       # made smaller to fit
        idx, a, b = hit
        if getattr(dc, 'twin', False):
            # the mirrored copy on the right half: painted there too, so it is whole even where that half has
            # texels of its own
            tw = copy.copy(dc); tw.twin = False; tw.a = -dc.a; tw.flip = not getattr(dc, 'flip', False)
            r0 = getattr(dc, 'region0', None)
            tw.region = lambda P, r0=r0: (P[:, 0] < -0.01) & (r0(P) if r0 is not None else True)
            timg, thm, twm = decal_size(tw, tm.texel_m)
            ti, ta, tb = decal_hits(tm, tw, thm, twm, 0.0, inside)
            if len(ti):
                tarr = np.asarray(timg).astype(np.float32)
                tsmp = bilinear(tarr, (ta / twm + 0.5) * (timg.width - 1), (0.5 - tb / thm) * (timg.height - 1))
                tal = tsmp[:, 3:4] / 255.0
                col[ti] = col[ti] * (1 - tal) + tsmp[:, :3] * tal
                forced[ti[tal[:, 0] > 0.5]] = True
        arr = np.asarray(img).astype(np.float32)
        smp = bilinear(arr, (a / wm + 0.5) * (img.width - 1), (0.5 - b / hm) * (img.height - 1))
        al = smp[:, 3:4] / 255.0
        c = np.broadcast_to(back, smp[:, :3].shape) if (inside and back is not None) else smp[:, :3]
        if debug:
            dbg = np.asarray(DEBUG_COLOURS[k % len(DEBUG_COLOURS)], np.float32)
            col[idx] = col[idx] * 0.45 + dbg * 0.55
        col[idx] = col[idx] * (1 - al) + c * al
        if alp is not None: alp[idx] = alp[idx] * (1 - al[:, 0]) + 255 * al[:, 0]
        solid = al[:, 0] > 0.5
        forced[idx[solid]] = True
        if solid.sum() > 20: got.append(k)
    return col, alp, forced, got


def bilinear(arr, u, v):
    h, w = arr.shape[:2]
    u = np.clip(u, 0, w - 1.001); v = np.clip(v, 0, h - 1.001)
    x0 = u.astype(int); y0 = v.astype(int); fx = (u - x0)[:, None]; fy = (v - y0)[:, None]
    return (arr[y0, x0] * (1 - fx) * (1 - fy) + arr[y0, x0 + 1] * fx * (1 - fy) +
            arr[y0 + 1, x0] * (1 - fx) * fy + arr[y0 + 1, x0 + 1] * fx * fy)


# ------------------------------------------------------------------ paint mask + shading from stock skins
NOT_PAINT_RE = re.compile(r'light|lamp|glass|window|grill|grid|mesh|(?<![a-z])int_|interior|badge|logo|plate|exhaust|tyre|tire|(?<![a-z])rims?(?=[^a-z]|lf|rf|lr|rr|$)', re.I)
def stock_analysis(car, tex, W, H, tm, log=print):
    """Compare the stock skins one at a time (memory stays small even with many 4K skins).
    The comparison runs at up to 2048 px; the masks are then scaled to the texture size."""
    def sources():
        for s_ in car.skins:
            im = car.stock_texture(tex, s_)
            if im is not None: yield im
        missing = sum(1 for s_ in car.skins if not find_skin_file(os.path.join(car.dir, 'skins', s_), tex))
        if missing and tex in car.kn5.textures:
            # skins without this file show the model's own copy: one more look to compare against
            try:
                im = load_image(car.kn5.textures[tex])
                log(f"{missing} skin(s) use the model's own {tex}: included in the comparison")
                yield im
            except Exception: pass

    k = min(1.0, 2048 / max(W, H))
    aW, aH = max(1, int(W * k)), max(1, int(H * k))
    n = 0; base = alpha = None
    S1 = S2 = LMAX = None
    for im in sources():
        # resize colour and alpha separately: Pillow premultiplies RGBA, which blacks out alpha-0 texels
        if base is None:
            base = np.asarray(im.convert('RGB').resize((W, H), Image.LANCZOS)).astype(np.float32)
            alpha = np.asarray(im.getchannel('A').resize((W, H), Image.LANCZOS))
        a = np.asarray(im.convert('RGB').resize((aW, aH), Image.BILINEAR)).astype(np.float32)
        if S1 is None:
            S1 = np.zeros_like(a); S2 = np.zeros_like(a); LMAX = np.zeros(a.shape[:2], np.float32)
        S1 += a; S2 += a * a; LMAX = np.maximum(LMAX, a.mean(-1)); n += 1
    if base is None:
        if tex in car.kn5.textures:
            full = load_image(car.kn5.textures[tex])
            base = np.asarray(full.convert('RGB').resize((W, H), Image.LANCZOS)).astype(np.float32)
            alpha = np.asarray(full.getchannel('A').resize((W, H), Image.LANCZOS))
        else:
            base = np.full((H, W, 3), 200, np.float32); alpha = np.zeros((H, W), np.uint8)
    cov_a = np.asarray(Image.fromarray((tm.covered * 255).astype(np.uint8)).resize((aW, aH), Image.NEAREST)) > 0
    up = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)) > 127
    if n >= 3:
        mean = S1 / n
        sd = np.sqrt(np.maximum(S2 / n - mean * mean, 0)).mean(-1)
        m = Image.fromarray(((sd > 9) * 255).astype(np.uint8))
        f = max(3, int(7 * aW / 2048) | 1)
        m = m.filter(ImageFilter.MaxFilter(f)).filter(ImageFilter.MinFilter(f)).filter(ImageFilter.MinFilter(3))
        paint = (np.asarray(m) > 127) & cov_a
        # fill small holes (logos / number boards common to every stock skin)
        holes = ~paint & cov_a
        hf = int(aW / 60) | 1
        hm = Image.fromarray((holes * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(hf)).filter(ImageFilter.MaxFilter(hf))
        paint |= holes & ~(np.asarray(hm) > 127) & (mean.mean(-1) > 60)
        li = Image.fromarray(np.clip(LMAX, 0, 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(f + 2)).filter(ImageFilter.GaussianBlur(aW / 290))
        lum = np.asarray(li).astype(np.float32)
        ref = np.percentile(lum[paint], 90) if paint.any() else 255
        shade_a = np.clip(lum / ref, 0.6, 1.0) ** 0.8
        frac = paint.sum() / max(1, cov_a.sum())
        if frac < 0.5:
            # skins differ only in decals (colour comes from elsewhere, e.g. Kunos' detail texture):
            # light, colourless texels are bare paint too
            light = (mean.mean(-1) > 110) & ((mean.max(-1) - mean.min(-1)) < 35) & cov_a
            paint |= light
            log(f'stock skins only differ in decals ({frac * 100:.0f}%); light bare paint added')
        paint = up(paint) & tm.covered
        shade = np.asarray(Image.fromarray((shade_a * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
        log(f'paint area from {n} stock skins: {paint.sum() / max(1, tm.covered.sum()) * 100:.0f}% of the body texels')
    else:
        # few skins: everything on the body except light/glass/grille-looking meshes
        good_tri = np.array([not NOT_PAINT_RE.search(nm) for nm in tm.mesh_of_tri])
        paint = np.zeros((H, W), bool)
        paint[tm.yy, tm.xx] = good_tri[tm.tri]
        shade = np.ones((H, W), np.float32)
        log(f'only {n} stock skin(s): paint area guessed from mesh names ({paint.sum() / max(1, tm.covered.sum()) * 100:.0f}%)')
    return base, alpha, paint, shade


# ------------------------------------------------------------------ wheels
def recolour_wheels(car, tex, colour, log=print, only=None, start=None, what='wheels'):
    """Recolour a wheel texture: texels that differ between stock skins (or every coloured
    texel when there are too few skins) take the new colour, keeping their light and shade.
    only: meshes whose part of the texture may change (a texture shared by rim and tyre).
    start: the texture as made so far (the rim colour already in, when the tyre is done second)."""
    imgs = [car.stock_texture(tex, s) for s in car.skins]
    imgs = [i for i in imgs if i is not None]
    if not imgs: imgs = [load_image(car.kn5.textures[tex])]
    W, H = imgs[0].size
    limit = None
    if only:
        limit = np.asarray(Image.fromarray((uv_coverage(only, 1024) * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)
                           .filter(ImageFilter.MaxFilter(5))) > 0
    keep = np.asarray(start.convert('RGB').resize((W, H))).astype(np.float32) if start is not None else None
    flat = np.asarray(imgs[0].convert('RGB')).astype(np.float32)
    if flat.reshape(-1, 3).std(0).max() < 6:
        # a plain one-colour rim texture (often black): nothing to shade, the whole of it takes the new colour
        out = np.empty_like(flat); out[:] = rgb(colour)
        if limit is not None: out = np.where(limit[..., None], out, flat if keep is None else keep)
        log(f'{what} {tex}: plain one-colour texture - set to the new colour')
        return Image.fromarray(np.dstack([out.astype(np.uint8), np.asarray(imgs[0].getchannel('A'))]), 'RGBA')
    A = np.stack([np.asarray(i.convert('RGB').resize((W, H))).astype(np.float32) for i in imgs])
    base = A[0]
    if len(A) >= 3:
        mask = A.std(0).mean(-1) > 9
    else:
        mx, mn = base.max(-1), base.min(-1)
        mask = (mx - mn) > 40                      # coloured (not grey/black/chrome) texels
        if mask.mean() < 0.02:                     # plain grey rim: colourise the whole rim by brightness
            mask = base.mean(-1) > 25
    if what == 'tyres' and len(A) < 3:
        mask = np.ones_like(mask)                  # a tyre is one rubber colour: all of it, keeping its shading
    if limit is not None: mask = mask & limit
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1))
    mm = np.asarray(m).astype(np.float32)[..., None] / 255
    if limit is not None: mm = mm * limit[..., None]
    lum = A.max(0).mean(-1) if len(A) >= 3 else base.mean(-1)
    ref = np.percentile(lum[mask], 85) if mask.any() else 255
    shade = np.clip(lum / max(ref, 1), 0.25, 1.15)[..., None]
    new = np.clip(rgb(colour) * shade, 0, 255)
    out = (base if keep is None else keep) * (1 - mm) + new * mm
    log(f'{what} {tex}: recoloured {mask.mean() * 100:.0f}% of the texture')
    return Image.fromarray(np.dstack([out.astype(np.uint8), np.asarray(imgs[0].getchannel('A'))]), 'RGBA')


# ------------------------------------------------------------------ headlights
LIGHT_RE = re.compile(r'light|lamp|head|faro|lens|scheinwerfer|emissive|flash|\bhl\b|_hl|hl_|lhigh|llow|lday|ldown', re.I)
NOT_FRONT_RE = re.compile(r'rear|brake|tail|back|revers|aux|(?<![a-z])int_|interior|cockpit|dash|turn|indicat|blink|'
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
    if isinstance(made.get(tex), Image.Image): return made[tex]
    if copy_from:
        im = car.stock_texture(tex, copy_from)
        if im is not None: return im
    for s in car.skins:
        im = car.stock_texture(tex, s)
        if im is not None: return im
    if tex in car.kn5.textures: return load_image(car.kn5.textures[tex])
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
    light_names = {m.name for m in lights}
    for tex, ms in by_tex.items():
        # texels the lamps use that other parts also use (generic chrome / black plastic): don't tint those
        other_ms = [m for m in car.kn5.meshes if m.mat is not None and m.mat.samplers.get('txDiffuse') == tex
                    and m.name not in light_names and len(m.idx)]
        mine_cov = uv_coverage(ms)
        other_cov = uv_coverage(other_ms) if other_ms else np.zeros_like(mine_cov)
        clash = (mine_cov & other_cov).sum() / max(1, mine_cov.sum())
        if clash > 0.5:
            log(f'headlight lenses: {tex} is shared with other parts of the car - left as it is')
            continue
        img = current_texture(car, tex, made, copy_from)
        if img is None: continue
        W, H = img.size
        tm = TexelMap(ms, W, H, log=lambda s: None)
        mask = Image.fromarray((tm.covered * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
        m = (np.asarray(mask) > 0)
        a = np.asarray(img).astype(np.float32)
        rgbv = a[..., :3]
        colourless = (rgbv.max(-1) - rgbv.min(-1)) < 45
        m = m & colourless
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
GLASS_RE = re.compile(r'window|windscr|windshield|glass|(?<![a-z])win_|_win(?![a-z])|parabrezza|vetr|lunotto|scheibe|'
                      r'vidro|vidrio|parabris|luneta|cristal|verre|vitre|pare.?brise|glas(?![a-z])|lasi(?![a-z])|ruit(?![a-z])', re.I)
NOT_GLASS_RE = re.compile(r'damage|crack|broken|light|lamp|(?<!over)head|lens|emissive|faro|fanal|mirror|gauge|dial|display|(?<!wind)screen_|lcd|'
                          r'visor|helmet|mold|mould|trim|seal|rubber|frame|gasket|wiper|stop|brake|tail|indicat|blink|gabarit|'
                          r'chrom|crome|dash|instr|cluster|defrost|sbrina|netting|plastic|revers|[rl]hl|'
                          r'farol|lanterna|pisca|milha|medios|maximos|tulipa|nevoeiro|neblin|faros?(?![a-z])|feux|phare|clignot|'
                          r'cover|guard|(?<!wind)shield|sticker|decal|cambio|shifter|sunblock|deflect|visier|(?<![a-z])fara|fog|[lr]tl_|'
                          r'vetrovik|plate|logo|number|rim_glass|red_glass|orange|amber|wing|spoiler', re.I)
INSIDE_RE = re.compile(r'(?<![a-z])int_|_int\b|interior|inside|inner|\.int\b|glassint|(?<![a-z])int$', re.I)


OVERLAY_RE = re.compile(r'banner|sun.?strip|visor_?decal|(?:window|windows|glass|win|wind)[\W_]*(?:decal|sticker)|'
                        r'(?:decal|sticker)s?[\W_]*(?:glass|window)|windowforstickers|numglass|glasstickers', re.I)
DECAL_RE = re.compile(r'decal|sticker', re.I)
SIDE_PLACES = {'rear': 'Rear side windows', 'door': 'Front door windows', 'both': 'Both'}


def see_through(mat):
    """Glass is drawn see-through: alpha blending, alpha test or the windscreen shader."""
    return mat.blend == 1 or mat.alpha_tested or mat.shader.lower() == 'kswindscreen'


def window_meshes(car, with_overlays=False, log=None):
    """Glass meshes (outside / inside). With with_overlays: also the sticker overlay meshes some
    cars use instead (Kunos: EXT_Banner on the windscreen, EXT_DECALS_DOOR_x on the side windows).
    A mesh is glass only if its name says so, it is see-through, it is not on the paint texture and
    it is not a light, trim, frame or chrome part."""
    strict, loose, ov_ext, ov_inner = [], [], [], []
    body = set(getattr(car, 'body_textures', ()))
    y_min = car.lo[1] + 0.6 * (car.hi[1] - car.lo[1])
    for m in car.kn5.meshes:
        if not len(m.idx) or m.mat is None or not m.mat.samplers.get('txDiffuse'): continue
        label = f'{m.name} {m.mat.name}'
        inside = bool(INSIDE_RE.search(label)) or m.mat.shader.lower() == 'kswindscreen'
        painted = m.mat.samplers['txDiffuse'] in body
        if not painted and not re.search(r'light|lens|lamp|dash', m.name, re.I) and (OVERLAY_RE.search(label) or
                            (DECAL_RE.search(label) and 'door' in label.lower() and m.pos.mean(0)[1] > y_min)):
            if tri_area3(m).sum() > 0.02:          # tiny patches (door-pin labels etc.) are not sticker sheets
                (ov_inner if inside else ov_ext).append(m)
            continue
        tex = m.mat.samplers['txDiffuse']
        named = GLASS_RE.search(label) or (see_through(m.mat) and GLASS_RE.search(tex) and
                                           # named only by its texture: must be window-sized, at window height
                                           tri_area3(m).sum() >= 0.05 and m.pos.mean(0)[1] > car.lo[1] + 0.5 * (car.hi[1] - car.lo[1]))
        if painted or not named or NOT_GLASS_RE.search(label) or re.search(r'damage|crack|broken', tex, re.I) or \
                (not GLASS_RE.search(label) and NOT_GLASS_RE.search(tex)): continue
        loose.append((m, inside))
        if see_through(m.mat) and tri_area3(m).sum() >= 0.015: strict.append((m, inside))
    use = strict if any(not i for _, i in strict) else loose
    if use is loose and loose and log: log('windows: no see-through glass found by material - glass picked by name only')
    ext = [m for m, i in use if not i]; inner = [m for m, i in use if i]
    if log and ext: log('windows: glass = ' + ', '.join(m.name for m in ext)[:160])
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
    """Remove old stickers. Stickers are opaque and clear glass is see-through, so every glass texel
    more opaque than the clear-glass level becomes plain glass. (Textures with no see-through part:
    texels that differ from the most common colour.) Returns how many texels were cleaned."""
    px = arr[sel].astype(np.float32)
    n = len(px)
    if not n: return 0
    al = px[:, 3]
    hist = np.bincount(al.astype(np.int64), minlength=256)[:256]
    win = np.convolve(hist, np.ones(16), 'full')[15:]            # texels with alpha in [v, v+16)
    v = int(np.argmax(win >= 0.1 * n)) if (win >= 0.1 * n).any() else int(np.argmax(win))
    clear = (al >= v) & (al < v + 16)
    old = al > v + 16 + 60
    if v >= 180 or not clear.any():
        # no see-through level: fall back to the most common colour
        q = (px // 24).astype(np.int32)
        key = q[:, 0] * 1000000 + q[:, 1] * 10000 + q[:, 2] * 100 + q[:, 3]
        vals, cnt = np.unique(key, return_counts=True)
        clear = key == vals[np.argmax(cnt)]
        d = np.abs(px - px[clear].mean(0))
        old = (d[:, :3].max(1) > 30) | (d[:, 3] > 30)
    # the soft edges of old stickers go too
    m2 = np.zeros(sel.shape, np.uint8); m2[sel] = old * 255
    old = (np.asarray(Image.fromarray(m2).filter(ImageFilter.MaxFilter(7))) > 0)[sel]
    px[old] = np.median(px[clear & ~old], axis=0) if (clear & ~old).any() else np.median(px[clear], axis=0)
    arr[sel] = px.astype(np.uint8)
    return int(old.sum())


def sample_tris(T, spacing=0.008, seed=1, with_index=False):
    """Points spread over the triangles T (n, 3, 3): about one per spacing x spacing (and, with
    with_index, which triangle each point is on)."""
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    rep = np.repeat(np.arange(len(T)), np.clip(np.ceil(area / spacing ** 2), 1, 4000).astype(int))
    rng = np.random.default_rng(seed)
    u, v = rng.random(len(rep)), rng.random(len(rep))
    f = u + v > 1; u[f], v[f] = 1 - u[f], 1 - v[f]
    S = T[rep, 0] + (T[rep, 1] - T[rep, 0]) * u[:, None] + (T[rep, 2] - T[rep, 0]) * v[:, None]
    return (S, rep) if with_index else S


def glass_islands(meshes):
    """Connected pieces (one per window pane) of the glass meshes: triangles, mean normal, centre, area."""
    pos, nrm, tri, off = [], [], [], 0
    for m in meshes:
        pos.append(m.pos); nrm.append(m.nrm); tri.append(m.idx + off); off += len(m.pos)
    pos, nrm, tri = np.concatenate(pos), np.concatenate(nrm), np.concatenate(tri)
    _, inv = np.unique(np.round(pos / 0.002).astype(np.int64), axis=0, return_inverse=True)
    inv = inv.ravel()
    wt = inv[tri]
    lab = np.arange(inv.max() + 1)
    while True:                                   # every vertex takes the lowest label in its triangles
        new = lab.copy()
        np.minimum.at(new, wt.ravel(), np.repeat(lab[wt].min(1), 3))
        new = new[new]
        if np.array_equal(new, lab): break
        lab = new
    tl = lab[wt[:, 0]]
    T = pos[tri]
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    tn = nrm[tri].mean(1)
    out = []
    for l in np.unique(tl):
        sel = tl == l
        A = area[sel].sum()
        if A < 1e-4: continue
        n = (tn[sel] * area[sel, None]).sum(0); n /= max(np.linalg.norm(n), 1e-9)
        c = (T[sel].mean(1) * area[sel, None]).sum(0) / A
        out.append(dict(T=T[sel], n=n, c=c, area=float(A)))
    return out


class EdgeFrame:
    """Surface coordinates on a windscreen or rear window: `a` = distance along its top edge (0 at the
    middle, growing to the viewer's right), `b` = minus the distance down from that edge along the glass.
    A banner drawn in these coordinates hugs the curved top edge at a fixed height."""

    def __init__(self, P, flip=False):
        x = P[:, 0]
        x0, x1 = np.percentile(x, 0.5), np.percentile(x, 99.5)
        nb = max(8, int((x1 - x0) / 0.02))
        bi = np.clip(((x - x0) / (x1 - x0) * nb).astype(int), 0, nb - 1)
        order = np.lexsort((P[:, 1], bi))                       # last of each bin = its highest point
        last = np.r_[np.nonzero(np.diff(bi[order]))[0], len(order) - 1]
        top = P[order[last]]
        xm = (x0 + x1) / 2
        cen = np.abs(top[:, 0] - xm) < 0.42 * (x1 - x0)
        if cen.sum() < 6: cen[:] = True
        deg = 4 if cen.sum() > 14 else 2
        xa, xb = top[cen, 0].min(), top[cen, 0].max()
        cy = np.polyfit(top[cen, 0] - xm, top[cen, 1], deg); cz = np.polyfit(top[cen, 0] - xm, top[cen, 2], deg)

        def ev(c, xs):                                         # the fit, carried on in a straight line past its ends
            xc = np.clip(xs, xa, xb)
            return np.polyval(c, xc - xm) + np.polyval(np.polyder(c), xc - xm) * (xs - xc)
        self.xs = np.linspace(x0, x1, 240)
        self.yt, self.zt = ev(cy, self.xs), ev(cz, self.xs)
        seg = np.sqrt(np.diff(self.xs) ** 2 + np.diff(self.yt) ** 2 + np.diff(self.zt) ** 2)
        self.s = np.r_[0, np.cumsum(seg)]
        self.s -= np.interp(xm, self.xs, self.s)
        self.S = float(self.s[-1] - self.s[0])                  # length of the top edge
        self.flip = flip

    def ab(self, P):
        x = P[:, 0]
        yt, zt = np.interp(x, self.xs, self.yt), np.interp(x, self.xs, self.zt)
        dy = yt - P[:, 1]
        d = np.sign(dy) * np.hypot(dy, P[:, 2] - zt)
        s = np.interp(x, self.xs, self.s)
        return (-s if self.flip else s), -d


def footprint(T, view, cell=0.005, erode=0.0):
    """The triangles T as seen in `view`, as a grid of cells (rows go up). Returns mask, a0, b0."""
    _, fa, fb = VIEWS[view]
    flat = T.reshape(-1, 3)
    A, B = fa(flat).reshape(-1, 3), fb(flat).reshape(-1, 3)
    a0, b0 = A.min() - 2 * cell, B.min() - 2 * cell
    W, H = int((A.max() - a0) / cell) + 3, int((B.max() - b0) / cell) + 3
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    QA, QB = (A - a0) / cell, (B - b0) / cell
    for i in range(len(T)):
        d.polygon([(QA[i, 0], QB[i, 0]), (QA[i, 1], QB[i, 1]), (QA[i, 2], QB[i, 2])], fill=255, outline=255)
    if erode > 0: im = im.filter(ImageFilter.MinFilter(2 * int(erode / cell) + 1))
    return np.asarray(im) > 0, a0, b0


def fit_rect(mask, aspect, max_h, min_h=6, prefer=None):
    """The biggest rectangle (width = aspect x height, in cells) that lies inside the mask, as close to
    `prefer` (col, row) as it can be. Returns centre col, centre row, height - or None when nothing fits."""
    H, W = mask.shape
    I = np.zeros((H + 1, W + 1), np.int64); I[1:, 1:] = mask.cumsum(0).cumsum(1)
    if prefer is None:
        ys, xs = np.nonzero(mask)
        if not len(ys): return None
        prefer = (xs.mean(), ys.mean())
    h = int(min(max_h, H - 1))
    while h >= min_h:
        w = int(round(h * aspect))
        if 0 < w < W:
            sums = I[h:, w:] - I[:-h, w:] - I[h:, :-w] + I[:-h, :-w]
            ys, xs = np.nonzero(sums >= 0.985 * h * w)
            if len(ys):
                k = np.argmin((xs + w / 2 - prefer[0]) ** 2 + (ys + h / 2 - prefer[1]) ** 2)
                return xs[k] + w / 2, ys[k] + h / 2, h
        h = min(h - 1, int(h * 0.94))
    return None


def stack_images(top, bottom, ratio=0.3, gap=0.1):
    """`bottom` (scaled to ratio x the height of `top`) centred under `top`."""
    bh = max(4, int(top.height * ratio))
    bottom = bottom.resize((max(2, int(bottom.width * bh / bottom.height)), bh), Image.LANCZOS)
    g = int(top.height * gap)
    im = Image.new('RGBA', (max(top.width, bottom.width), top.height + g + bh), (0, 0, 0, 0))
    im.alpha_composite(top, ((im.width - top.width) // 2, 0))
    im.alpha_composite(bottom, ((im.width - bottom.width) // 2, top.height + g))
    return im


def find_sunstrips(car, glass_pts):
    """Painted panels lying on the windscreen (a sun strip modelled as part of the body, on the paint
    texture): meshes whose points all sit on the windscreen glass."""
    cell = 0.02
    x0, y0 = glass_pts[:, 0].min(), glass_pts[:, 1].min()
    gx, gy = ((glass_pts[:, 0] - x0) / cell).astype(int), ((glass_pts[:, 1] - y0) / cell).astype(int)
    W, H = gx.max() + 1, gy.max() + 1
    zs = np.zeros((H, W)); n = np.zeros((H, W))
    np.add.at(zs, (gy, gx), glass_pts[:, 2]); np.add.at(n, (gy, gx), 1)
    gz = np.where(n > 0, zs / np.maximum(n, 1), np.nan)
    lo, hi = glass_pts.min(0) - 0.05, glass_pts.max(0) + 0.05
    out = []
    for m in car.kn5.meshes:
        if m.mat is None or not len(m.idx) or m.mat.samplers.get('txDiffuse') not in car.body_textures: continue
        if (m.pos.min(0) < lo).any() or (m.pos.max(0) > hi).any(): continue
        if tri_area3(m).sum() < 0.03: continue
        Q = sample_tris(m.pos[m.idx], 0.015)
        ix = np.clip(((Q[:, 0] - x0) / cell).astype(int), 0, W - 1); iy = np.clip(((Q[:, 1] - y0) / cell).astype(int), 0, H - 1)
        z = gz[iy, ix]
        if (np.abs(z - Q[:, 2]) < 0.045).mean() > 0.8: out.append(m)      # nan (no glass there) counts as off the glass
    return out


def make_window_stickers(car, design, made, copy_from=None, log=print, resolution=None, info=None):
    """Window stickers. Returns {texture: image} and the preview layers [(texel map, rgba array)]."""
    seen = set()

    def wlog(msg):                                 # the same note comes up for outside and inside glass: say it once
        if msg not in seen: seen.add(msg); log(msg)
    ext, inner, ov_ext, ov_inner = window_meshes(car, with_overlays=True, log=log)
    if not ext and not ov_ext:
        log('windows: no glass meshes found on this car'); return {}, []
    glass = ext or ov_ext
    fnt = design.get('font') or DEFAULT_FONT
    txt = rgb(design.get('win_text_colour') or '#ffffff')
    band = rgb(design.get('win_banner_colour') or '#111111')
    num = str(design.get('number') or '').strip() if design.get('win_number', True) else ''
    name = (design.get('name') or '').strip() if design.get('win_name', True) else ''
    banner_txt = (design.get('win_banner') or '').strip()
    logos = {lg['place']: lg for lg in (design.get('logos') or [])
             if lg.get('place') in ('windscreen', 'rear_window', 'side_windows') and os.path.isfile(lg.get('path', ''))}
    acc2 = rgb(design.get('accent2') or '#ffffff')
    h_ban = float(np.clip(design.get('win_banner_height') or 0.12, 0.08, 0.25))
    cell = 0.005

    def logo_img(place):
        lg = logos[place]
        return prep_logo(lg['path'], acc2 if lg.get('tint') else None, lg.get('bg', 'auto'))

    fnt_team = design.get('font_team') or fnt

    def block():                                   # number over name, as one sticker
        n_im = text_image(num, 300, txt, design.get('font_number') or fnt, stroke=0.05, stroke_color=band) if num else None
        m_im = text_image(name, 200, txt, design.get('font_name') or fnt, track=0.06, stroke=0.04, stroke_color=band) if name else None
        if n_im and m_im: return stack_images(n_im, m_im)
        return n_im or m_im

    # ---- which pane is which
    mid = (car.hi[2] + car.lo[2]) / 2
    L = car.length
    isl = glass_islands(glass)

    def sort(isl):
        fr, rr, sd = [], [], []
        for i in isl:
            n, c = i['n'], i['c']
            if abs(n[0]) > 0.5:
                if i['area'] >= 0.03: sd.append(i)
            elif n[1] > 0.95 and abs(c[2] - mid) < 0.2 * L: continue          # glass roof
            elif c[2] > mid and i['area'] > 0.15: fr.append(i)
            elif c[2] <= mid and i['area'] > 0.08: rr.append(i)
        return fr, rr, sd
    front, rear, sides = sort(isl)
    if not front and not sides:
        # all the glass is one piece (a canopy): split it by which way each triangle faces
        T = np.concatenate([i['T'] for i in isl])
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        vn = np.concatenate([m.nrm[m.idx].mean(1) for m in glass])
        n = np.where((n * vn).sum(1, keepdims=True) < 0, -n, n)
        c = T.mean(1); ar = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        parts = []
        for sel in (n[:, 0] > 0.6, n[:, 0] < -0.6, (np.abs(n[:, 0]) <= 0.6) & (c[:, 2] > mid) & (n[:, 2] > 0.2),
                    (np.abs(n[:, 0]) <= 0.6) & (c[:, 2] <= mid) & (n[:, 2] < -0.2)):
            if ar[sel].sum() > 0.03:
                nn = (n[sel] * ar[sel, None]).sum(0)
                parts.append(dict(T=T[sel], n=nn / max(np.linalg.norm(nn), 1e-9), c=(c[sel] * ar[sel, None]).sum(0) / ar[sel].sum(),
                                  area=float(ar[sel].sum())))
        front, rear, sides = sort(parts)

    decals, strips = [], []
    # ---- windscreen banner: follows the top edge of the glass
    if front:
        Tf = np.concatenate([i['T'] for i in front])
        Pf = sample_tris(Tf)
        strips = find_sunstrips(car, Pf)
        bn = [m for m in ov_ext if 'banner' in (m.name + m.mat.name).lower() and m.pos.mean(0)[2] > mid]
        fr = EdgeFrame(np.concatenate([Pf] + [sample_tris(m.pos[m.idx]) for m in strips + bn]))
        h = h_ban
        if strips:
            hs = float(np.percentile(-fr.ab(np.concatenate([m.pos for m in strips]))[1], 99))
            log(f"windows: this car's sun strip is a painted panel ({', '.join(m.name for m in strips)}, {hs * 100:.0f} cm) - "
                'the banner goes on it' + (' and carries on down the glass' if h > hs + 0.01 else ''))
            h = max(h, hs)
        zmin = Pf[:, 2].min() - 0.08
        kw = dict(coords=fr.ab, region=lambda Q, zmin=zmin: Q[:, 2] > zmin)
        full = dict(width=fr.S * 1.02, label='windscreen banner', **kw)       # 1 cm over the top edge, so no clear line is left
        if 'windscreen' in logos:
            lg = logo_img('windscreen')
            if lg.width / lg.height > 2.5:     # a wide picture is the banner itself: stretched across the glass
                decals.append(Decal(lg, 'front', 0.0, -h / 2 + 0.01, h + 0.02, key='win:banner_front', **full))
            else:
                decals.append(Decal(banner_image('', band, txt, fnt, fr.S / h), 'front', 0.0, -h / 2 + 0.01, h + 0.02, key='win:banner_front', **full))
                decals.append(Decal(lg, 'front', 0.0, -h / 2, h * 0.85, label='windscreen logo', key='win:logo_front', **kw))
        else:
            decals.append(Decal(banner_image(banner_txt, band, txt, fnt_team, fr.S / h), 'front', 0.0, -h / 2 + 0.01, h + 0.02, key='win:banner_front', **full))
        log(f'windows: windscreen banner {h * 100:.0f} cm high, {fr.S:.2f} m along the top edge of the glass')
    # ---- rear window: banner along the top edge, number / name / logo where they fit below it
    if rear:
        Tr = np.concatenate([i['T'] for i in rear])
        Pr = sample_tris(Tr)
        rf = EdgeFrame(Pr, flip=True)
        hr = h_ban * 0.8
        zmax = Pr[:, 2].max() + 0.08
        reg = lambda Q, zmax=zmax: Q[:, 2] < zmax
        decals.append(Decal(banner_image(banner_txt, band, txt, fnt_team, rf.S / hr), 'rear', 0.0, -hr / 2 + 0.01, hr + 0.02,
                            width=rf.S * 1.02, coords=rf.ab, region=reg, label='rear window banner', key='win:banner_rear'))
        img = logo_img('rear_window') if 'rear_window' in logos else block()
        if img is not None:
            mask, a0, b0 = footprint(Tr, 'rear', cell, erode=0.03)
            surf = max(float(np.percentile(-rf.ab(Pr)[1], 99)), 1e-3)
            y_top, y_bot = Pr[:, 1].max(), Pr[:, 1].min()
            cut = y_top - (hr + 0.03) * (y_top - y_bot) / surf          # the banner's lower edge, seen from behind
            mask[max(0, int((cut - b0) / cell)):] = False
            ys, xs = np.nonzero(mask)
            fit = fit_rect(mask, img.width / img.height, int(0.6 * (np.ptp(ys) + 1)), prefer=((0.0 - a0) / cell, ys.mean())) if len(ys) else None
            if fit:
                decals.append(Decal(img, 'rear', a0 + fit[0] * cell, b0 + fit[1] * cell, fit[2] * cell, region=reg,
                                    mirror_ok='rear_window' in logos, label='rear window ' + ('logo' if 'rear_window' in logos else 'number and name'),
                                    key='win:rear'))
            else:
                log('windows: no room on the rear window under the banner')
    # ---- side windows
    want = design.get('win_side_place') or 'rear'
    side_img = logo_img('side_windows') if 'side_windows' in logos else block()
    what = 'logo' if 'side_windows' in logos else ' and '.join(w for w, on in (('number', num), ('name', name)) if on)
    for view, sg in (('left', 1), ('right', -1)):
        if side_img is None: break
        to_a = (lambda z: -z) if view == 'left' else (lambda z: z)
        dm = [m for m in ov_ext if 'door' in (m.name + m.mat.name).lower() and m.pos.mean(0)[0] * sg > 0]
        mine = sorted([i for i in sides if i['c'][0] * sg > 0], key=lambda i: i['c'][2])
        targets = []                                   # (what it is, triangles, z range or None, margin)
        if dm:      # the car has its own door-window sticker sheet: put them there
            targets.append(('door window sticker sheet', np.concatenate([m.pos[m.idx] for m in dm]), None, 0.0))
        elif mine:
            rear_i = mine[0]
            z0, z1 = rear_i['T'][..., 2].min(), rear_i['T'][..., 2].max()
            ahead = [i for i in mine[1:] if i['area'] >= 0.08]
            door_i = max(ahead, key=lambda i: i['area']) if ahead else None
            one_long = door_i is None and z1 - z0 > 1.1          # the whole side glass is one piece
            t_rear = ('rear side window', rear_i['T'], (z0, z0 + 0.42 * (z1 - z0)) if one_long else None, 0.025)
            t_door = (('door window', door_i['T'], None, 0.025) if door_i is not None else
                      ('door window', rear_i['T'], (z0 + 0.5 * (z1 - z0), z1), 0.025) if one_long else None)
            if want == 'door' and t_door: targets.append(t_door)
            elif want == 'both' and t_door: targets += [t_rear, t_door]
            else: targets.append(t_rear)
        for tname, T, zr, margin in targets:
            mask, a0, b0 = footprint(T, view, cell, erode=margin)
            if zr is not None:
                c0, c1 = sorted((int((to_a(zr[0]) - a0) / cell), int((to_a(zr[1]) - a0) / cell)))
                mask[:, :max(0, c0)] = False; mask[:, max(0, c1):] = False
            ys, xs = np.nonzero(mask)
            fit = fit_rect(mask, side_img.width / side_img.height, int(0.62 * (np.ptp(ys) + 1))) if len(ys) else None
            if not fit:
                wlog(f'windows: no room for the {what} on the {view} {tname}'); continue
            decals.append(Decal(side_img, view, a0 + fit[0] * cell, b0 + fit[1] * cell, fit[2] * cell,
                                region=lambda Q, sg=sg: Q[:, 0] * sg > 0.1, mirror_ok='side_windows' in logos,
                                label=f'{what} on the {view} {tname}', key='win:side_' + tname.split()[0]))

    # ---- hand changes from the preview (move / size / turn / delete), then where each sticker is, for the preview boxes
    adj = design.get('adjust') or {}
    gone = [d for d in decals if adj.get(d.key, {}).get('deleted')]
    if gone:
        decals = [d for d in decals if d not in gone]
        log(f'windows: left off (deleted on the preview): {", ".join(sorted({d.label for d in gone}))}')
    hand_adjust(decals, adj)
    if info is not None:
        Pg = sample_tris(np.concatenate([i['T'] for i in isl]), 0.01)
        for dc in decals:
            w = dc.width or dc.height * dc.img.width / dc.img.height
            box = dict(a=float(dc.a), b=float(dc.b), h=float(dc.height), w=float(w), rot=float(dc.rot))
            if dc.coords is not None:          # follows the glass edge: its box as the view sees it
                ea, eb = dc.coords(Pg)
                on = (np.abs(ea - dc.a) < w / 2) & (np.abs(eb - dc.b) < dc.height / 2)
                if dc.region is not None: on &= dc.region(Pg)
                if on.sum() > 3:
                    _, fa, fb = VIEWS[dc.view]
                    A, B = fa(Pg[on]), fb(Pg[on])
                    box = dict(a=float(A.min() + A.max()) / 2, b=float(B.min() + B.max()) / 2, w=float(np.ptp(A)), h=float(np.ptp(B)), rot=0.0)
            info.setdefault('decals', []).append(dict(key=dc.key, label=dc.label, view=dc.view, **box))

    # ---- the textures. kind: glass / inner (inside face) / overlay / overlay_in (clear sticker sheets) / strip (painted)
    groups = {}
    for ms, kind in ((ext, 'glass'), (inner, 'inner'), (ov_ext, 'overlay'), (ov_inner, 'overlay_in'), (strips, 'strip')):
        for m in ms: groups.setdefault(m.mat.samplers['txDiffuse'], {}).setdefault(kind, []).append(m)
    back = np.array([28, 28, 30], np.float32)          # the back of a sticker, seen from inside
    cap = 4096 if (resolution or 0) >= 4096 else 2048
    arrs = {}
    for tex, kinds in groups.items():
        img = current_texture(car, tex, made, copy_from)
        if img is None: continue
        if 'strip' not in kinds:
            ms = [m for g in kinds.values() for m in g]
            uv = np.concatenate([m.uv[m.idx] for m in ms]); uv = uv - np.floor(uv.reshape(-1, 2).min(0))
            flat = uv.reshape(-1, 2)
            span = np.percentile(flat, 98, axis=0) - np.percentile(flat, 2, axis=0)
            # glass whose UVs run over two tiles is fine (panes that land on the same texels are left off
            # later); glass that repeats one small patch over and over has no room
            tiled = uv_overlap(ms) > 3.0 or (min(img.size) < 512 and span.min() <= 0.3)
            if tiled and min(img.size) < 512:
                log(f'windows: {tex} is only {img.size[0]}x{img.size[1]} and its glass is tiled - no room for stickers, skipped')
                continue
            # texel size on the glass: small textures are made bigger so writing stays sharp
            uva = 0.5 * np.abs((uv[:, 1, 0] - uv[:, 0, 0]) * (uv[:, 2, 1] - uv[:, 0, 1]) - (uv[:, 2, 0] - uv[:, 0, 0]) * (uv[:, 1, 1] - uv[:, 0, 1])).sum()
            a3 = sum(tri_area3(m).sum() for m in ms)
            texel = np.sqrt(a3 / max(uva * img.size[0] * img.size[1], 1e-9))
            k = 1
            outside = 'glass' in kinds or 'overlay' in kinds          # inside faces only show sticker backs: no need
            W2, H2 = (1 << max(3, int(np.ceil(np.log2(v_)))) for v_ in img.size)     # odd sizes (10x10): to a power of two
            texel = np.sqrt(a3 / max(uva * W2 * H2, 1e-9))
            if outside and not tiled and max(W2, H2) > 2 * min(W2, H2):   # a strip texture: square it first
                W2 = H2 = max(W2, H2); texel = np.sqrt(a3 / max(uva * W2 * H2, 1e-9))
            while outside and not tiled and texel / k > 0.0028 and max(W2, H2) * k * 2 <= cap: k *= 2
            if k > 1 or (W2, H2) != img.size:
                W2, H2 = W2 * k, H2 * k
                log(f'windows: {tex} is {img.size[0]}x{img.size[1]} ({texel * 1000:.0f} mm a texel on the glass) - '
                    f'the skin gets a {W2}x{H2} version so stickers stay sharp')
                r_, a_ = img.convert('RGB').resize((W2, H2), Image.BICUBIC), img.convert('RGBA').getchannel('A').resize((W2, H2), Image.BICUBIC)
                r_.putalpha(a_); img = r_
        arrs[tex] = np.asarray(img.convert('RGBA')).copy()
    # pass 1 outside, pass 2 inside (only the backs of stickers that landed outside; outside wins shared texels)
    hit, touched, changed, layers, names = set(), {}, set(), [], {}
    for inside_pass in (False, True):
        for tex, arr in arrs.items():
            H, W = arr.shape[:2]
            for kind, meshes in groups[tex].items():
                inside = kind in ('inner', 'overlay_in')
                if inside != inside_pass or (inside and not hit): continue
                tm = TexelMap(meshes, W, H, log=lambda s: None)
                keep = arr.copy() if inside else None
                if kind == 'strip':
                    arr[tm.yy, tm.xx, :3] = band.astype(np.uint8); changed.add(tex)
                elif design.get('win_clear', True):
                    if kind.startswith('overlay'):
                        cov = Image.fromarray((tm.covered * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
                        arr[np.asarray(cov) > 0] = 0
                    else:
                        n_old = clean_glass(arr, tm.covered)
                        if n_old and not inside: wlog(f'windows: old stickers removed from {tex}')
                    if not inside: changed.add(tex)
                col = arr[tm.yy, tm.xx, :3].astype(np.float32)
                alp = None if kind == 'strip' else arr[tm.yy, tm.xx, 3].astype(np.float32)
                use = [d for i, d in enumerate(decals) if (not inside) or i in hit]
                col, alp, _, got = apply_decals(col, tm, use, wlog, alp=alp, inside=inside, back=back, allow_move=False,
                                                quiet=True, no_shared=kind != 'strip')
                if not inside: hit |= {decals.index(use[i]) for i in got}
                if inside and not got:                   # nothing lands on this inside glass: leave it as it was
                    arr[:] = keep
                    continue
                if got: changed.add(tex)
                arr[tm.yy, tm.xx, :3] = np.clip(col, 0, 255).astype(np.uint8)
                if alp is not None: arr[tm.yy, tm.xx, 3] = np.clip(alp, 0, 255).astype(np.uint8)
                if inside and tex in touched:            # never paint over texels the outside already uses
                    arr[touched[tex]] = keep[touched[tex]]
                if not inside:
                    m_ = np.zeros((H, W), bool); m_[tm.yy, tm.xx] = True
                    touched[tex] = touched.get(tex, np.zeros((H, W), bool)) | m_
                    if kind != 'strip': layers.append((tm, arr))
                names.setdefault(tex, []).extend(m.name for m in meshes)
    out = {}
    if not hit:
        log('windows: this car has no glass texture with room for stickers - window stickers skipped')
        return out, []
    for i, d in enumerate(decals):
        if i not in hit and not any(d.label in m for m in seen):
            wlog(f'windows: {d.label}: not placed (no glass texture with room for it there)')
    for tex in changed:
        out[tex] = Image.fromarray(arrs[tex], 'RGBA')
        log(f'windows: stickers on {tex} ({", ".join(names.get(tex, []))[:80]})')
    return out, [l for l in layers if any(l[1] is arrs[t] for t in changed)]


def tint_windows(car, design, made, copy_from=None, log=print):
    """Tinted glass: a film of the tint colour behind what is on the glass (stickers stay as they are).
    Darkness 0..0.9 = how much of the light the film stops. The windscreen is left clear unless asked.
    Returns {texture: image} and preview layers [(texel map, rgba array)]."""
    tint = rgb(design['win_tint'])
    dark = float(np.clip(design.get('win_tint_dark') or 0.5, 0.05, 0.9))
    ext, inner = window_meshes(car, log=None)
    if not ext:
        log('windows: no glass found on this car - tint skipped'); return {}, []
    groups = {}
    for m in ext + inner: groups.setdefault(m.mat.samplers.get('txDiffuse'), []).append(m)
    mid = (car.hi[2] + car.lo[2]) / 2
    out, layers = {}, []
    for tex, ms in groups.items():
        img = current_texture(car, tex, made, copy_from) if tex else None
        if img is None: continue
        arr = np.asarray(img.convert('RGBA')).copy()
        H, W = arr.shape[:2]
        tm = TexelMap(ms, W, H, log=lambda s_: None)
        sel = np.ones(len(tm.yy), bool)
        if not design.get('win_tint_windscreen'):
            # the windscreen: glass facing forwards (not sideways) in the front half of the car
            sel &= ~((np.abs(tm.N[:, 0]) < 0.5) & (tm.P[:, 2] > mid))
        if not sel.any(): continue
        yy, xx = tm.yy[sel], tm.xx[sel]
        px = arr[yy, xx].astype(np.float32)
        a = px[:, 3] / 255
        if np.median(a) < 0.9:
            # see-through by its texture alpha: lay the film behind (the "over" rule) - opaque stickers keep their look
            a2 = a + (1 - a) * dark
            px[:, :3] = (px[:, :3] * a[:, None] + tint * (a2 - a)[:, None]) / np.maximum(a2, 1e-6)[:, None]
            px[:, 3] = a2 * 255
        else:
            # the material makes it see-through, not the texture: colour the glass itself
            px[:, :3] = px[:, :3] * (1 - dark) + tint * dark
        arr[yy, xx] = np.clip(px, 0, 255).astype(np.uint8)
        out[tex] = Image.fromarray(arr, 'RGBA')
        layers.append((tm, arr))
        log(f'windows: tinted {tex} ({int(dark * 100)} % dark{", windscreen too" if design.get("win_tint_windscreen") else ", windscreen left clear"})')
    return out, layers


# ------------------------------------------------------------------ DDS writer
def write_dds(img, path, compress=False):
    """DDS with a full mip chain. compress: DXT1 (no see-through parts) or DXT5 (with alpha) - about a quarter
    of the size (DXT5) or an eighth (DXT1), which AC reads like its own textures. Otherwise uncompressed A8R8G8B8."""
    img = img.convert('RGBA')
    if compress and img.width % 4 == 0 and img.height % 4 == 0:
        try:
            return _write_dxt(img, path)
        except Exception:
            pass                                    # anything odd: the plain uncompressed file instead
    # mips: colour and alpha shrink separately. (Resizing RGBA premultiplies alpha, and car textures often
    # have alpha 0 everywhere - that turned every distance level black.)
    rgb_, a_ = img.convert('RGB'), img.getchannel('A')
    levels = []
    while True:
        im = rgb_.copy(); im.putalpha(a_); levels.append(im)
        if rgb_.width == 1 and rgb_.height == 1: break
        size = (max(1, rgb_.width // 2), max(1, rgb_.height // 2))
        rgb_, a_ = rgb_.resize(size, Image.LANCZOS), a_.resize(size, Image.LANCZOS)
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, 0x2100F, img.height, img.width, img.width * 4, 0, len(levels))
    hdr += struct.pack('<IIIIIIII', 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    hdr += struct.pack('<IIIII', 0x401008, 0, 0, 0, 0)
    with open(path, 'wb') as f:
        f.write(hdr)
        for lv in levels:
            f.write(np.asarray(lv)[..., [2, 1, 0, 3]].copy().tobytes())


def _mips(img):
    rgb_, a_ = img.convert('RGB'), img.getchannel('A')
    levels = []
    while True:
        im = rgb_.copy(); im.putalpha(a_); levels.append(im)
        if rgb_.width == 1 and rgb_.height == 1: return levels
        size = (max(1, rgb_.width // 2), max(1, rgb_.height // 2))
        rgb_, a_ = rgb_.resize(size, Image.LANCZOS), a_.resize(size, Image.LANCZOS)


def _write_dxt(img, path):
    fmt = 'DXT1' if img.getchannel('A').getextrema()[0] == 255 else 'DXT5'
    data = []
    for lv in _mips(img):
        b = io.BytesIO()
        lv.save(b, 'DDS', pixel_format=fmt)          # Pillow's block encoder, one level at a time
        data.append(b.getvalue()[128:])
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, 0xA1007, img.height, img.width, len(data[0]), 0, len(data))
    hdr += struct.pack('<II4sIIIII', 32, 0x4, fmt.encode(), 0, 0, 0, 0, 0)
    hdr += struct.pack('<IIIII', 0x401008, 0, 0, 0, 0)
    with open(path, 'wb') as f:
        f.write(hdr)
        for d in data: f.write(d)


# ------------------------------------------------------------------ preview renderer
def view_frame(car, view):
    """The part of the view's plane a preview shows: a0, a1 (left, right edge), b0, b1 (bottom, top), metres."""
    _, fa, fb = VIEWS[view]
    allP = np.concatenate([m.pos for m in car.kn5.meshes if len(m.pos)])
    A, B = fa(allP), fb(allP)
    a0, a1, b0, b1 = np.percentile(A, 0.2), np.percentile(A, 99.8), np.percentile(B, 0.2), np.percentile(B, 99.8)
    pad = 0.04 * (a1 - a0)
    return float(a0 - pad), float(a1 + pad), float(b0 - pad), float(b1 + pad)


def render_view(car, view, tex_imgs, tms=None, width=1000, bg=(235, 236, 240), layers=()):
    """The car from one side, drawn from its real triangles the way the game maps the textures onto
    them: far triangles first, near ones over them. Meshes on a texture in tex_imgs show that texture,
    window stickers (layers: [(texel map, rgba array)]) show on the glass, everything else is grey."""
    vdir, fa, fb = VIEWS[view]
    ss = 2 if width <= 1700 else 1                         # drawn double size and scaled down: smooth edges
    a0, a1, b0, b1 = view_frame(car, view)
    Wp = width * ss; sc = Wp / (a1 - a0); Hp = int((b1 - b0) * sc)
    light = np.array([0.4, 0.8, 0.45]); light /= np.linalg.norm(light)
    texs = [np.asarray(im.convert('RGB')) for im in tex_imgs.values()]
    tex_id = {t.lower(): i for i, t in enumerate(tex_imgs)}
    alphas = [None] * len(texs)
    layer_of = {}
    for tm, arr in layers:
        texs.append(arr[..., :3]); alphas.append(arr[..., 3])
        for nm in set(tm.mesh_of_tri.tolist()): layer_of[nm] = len(texs) - 1
    # which triangle shows at every pixel depends only on the car and the view: kept for the next preview
    gkey = ('view', view, width, tuple(t.lower() for t in tex_imgs), tuple(sorted(layer_of.items())))
    geo_ = _MEMO.get(gkey) if _MEMO.get('car') is car else None
    if geo_ is None:
        geo_ = _view_geometry(car, view, width, tex_id, layer_of, len(tex_imgs), vdir, fa, fb, ss, a0, a1, b0, b1, light)
        if _MEMO.get('car') is car: _MEMO[gkey] = geo_
    Hp, Wp, ys, xs, Gt, tx, uv, tix, St = geo_
    out = np.empty((Hp, Wp, 3), np.float32); out[:] = bg
    col = np.repeat(Gt[:, None].astype(np.float32), 3, 1)
    if len(tx):
        for k, tex in enumerate(texs):
            sel = np.nonzero(tix == k)[0]
            if not len(sel): continue
            H, W = tex.shape[:2]
            u = (uv[sel, 0] * W).astype(np.int64) % W; v = (uv[sel, 1] * H).astype(np.int64) % H
            c = tex[v, u].astype(np.float32) * St[sel, None].astype(np.float32)
            if alphas[k] is not None:                      # glass: stickers and tint show, clear glass stays grey
                al = alphas[k][v, u].astype(np.float32)[:, None] / 255
                c = col[tx[sel]] * (1 - al) + c * al
            col[tx[sel]] = c
    out[ys, xs] = col
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if ss > 1: img = img.resize((width, Hp // ss), Image.LANCZOS)
    return img


def _view_geometry(car, view, width, tex_id, layer_of, n_tex, vdir, fa, fb, ss, a0, a1, b0, b1, light):
    """For one view: every covered pixel, its grey shade, and for textured parts the texture spot it shows."""
    Wp = width * ss; sc = Wp / (a1 - a0); Hp = int((b1 - b0) * sc)
    Ts, Gs, Ss, UVs, TI = [], [], [], [], []
    for m in car.kn5.meshes:
        if not len(m.idx): continue
        T = m.pos[m.idx]
        g = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        ln = np.linalg.norm(g, axis=1); ok = ln > 0
        vn = m.nrm[m.idx].mean(1)
        ti = tex_id.get((m.mat.samplers.get('txDiffuse') or '').lower(), -1) if m.mat is not None else -1
        if ti < 0: ti = layer_of.get(m.name, -1)
        if ti >= 0: ok &= vn @ vdir > 0.02                 # painted panels: the side facing the viewer only
        uv = m.uv[m.idx]; uv = uv - np.floor(uv.min(1, keepdims=True))
        Ts.append(T[ok]); Gs.append((110 + 80 * np.abs((g[ok] / ln[ok, None]) @ light)))
        Ss.append(0.6 + 0.4 * np.clip(vn[ok] @ light, 0, 1)); UVs.append(uv[ok]); TI.append(np.full(ok.sum(), ti))
    T = np.concatenate(Ts); G = np.concatenate(Gs); S = np.concatenate(Ss); UV = np.concatenate(UVs); TI = np.concatenate(TI)
    flat = T.reshape(-1, 3)
    QA = ((fa(flat) - a0) * sc).reshape(-1, 3); QB = ((b1 - fb(flat)) * sc).reshape(-1, 3)
    area2 = np.abs((QA[:, 1] - QA[:, 0]) * (QB[:, 2] - QB[:, 0]) - (QA[:, 2] - QA[:, 0]) * (QB[:, 1] - QB[:, 0]))
    # stickers sit on the glass: drawn as if 3 cm nearer, so frames and damage glass lying on it don't hide them
    # (painted panels 6 mm nearer: damage / dirt copies of the body lie exactly on them)
    order = np.argsort(T.mean(1) @ vdir + np.where(TI >= n_tex, 0.03, np.where(TI >= 0, 0.006, 0.0)))
    order = order[area2[order] > 0.02]
    qa, qb = QA.tolist(), QB.tolist()

    def draw(which):
        im = Image.new('I', (Wp, Hp), -1); d = ImageDraw.Draw(im)
        for i in which:
            d.polygon([(qa[i][0], qb[i][0]), (qa[i][1], qb[i][1]), (qa[i][2], qb[i][2])], fill=i)
        return np.asarray(im, dtype=np.int64)

    def weights(tt, px, py):
        x0, y0 = QA[tt, 0], QB[tt, 0]
        e1x, e1y, e2x, e2y = QA[tt, 1] - x0, QB[tt, 1] - y0, QA[tt, 2] - x0, QB[tt, 2] - y0
        den = e1x * e2y - e2x * e1y; den[np.abs(den) < 1e-9] = 1e-9
        w1 = np.clip(((px - x0) * e2y - e2x * (py - y0)) / den, 0, 1)
        w2 = np.clip((e1x * (py - y0) - (px - x0) * e1y) / den, 0, 1)
        w0 = np.clip(1 - w1 - w2, 0, 1)
        ws = w0 + w1 + w2
        return w0 / ws, w1 / ws, w2 / ws
    idm = draw(order.tolist())
    # far-to-near drawing goes wrong where a big plain part lies just behind small painted panels:
    # there, the painted panel wins if it really is the nearer one at that pixel
    # (parts with no room of their own in the texture - all their UVs on one spot - count as plain here)
    uva = np.abs((UV[:, 1, 0] - UV[:, 0, 0]) * (UV[:, 2, 1] - UV[:, 0, 1]) - (UV[:, 2, 0] - UV[:, 0, 0]) * (UV[:, 1, 1] - UV[:, 0, 1]))
    solid = (TI >= 0) & (uva > 1e-10)
    idt = draw([i for i in order.tolist() if solid[i]])
    D = (T @ vdir)                                            # depth of every corner
    ys, xs = np.nonzero((idm >= 0) & (idt >= 0) & (idm != idt))
    if len(ys):
        ta, tb = idm[ys, xs], idt[ys, xs]
        wa, wb = weights(ta, xs + 0.5, ys + 0.5), weights(tb, xs + 0.5, ys + 0.5)
        da = D[ta, 0] * wa[0] + D[ta, 1] * wa[1] + D[ta, 2] * wa[2]
        db = D[tb, 0] * wb[0] + D[tb, 1] * wb[1] + D[tb, 2] * wb[2]
        sw = ~solid[ta] & (db > da - 0.01)
        idm[ys[sw], xs[sw]] = tb[sw]
    ys, xs = np.nonzero(idm >= 0)
    t = idm[ys, xs]
    Gt = G[t].astype(np.uint8)
    tx = np.nonzero(TI[t] >= 0)[0].astype(np.int32)
    tt = t[tx]
    w0, w1, w2 = weights(tt, xs[tx] + 0.5, ys[tx] + 0.5)
    uv = (UV[tt, 0] * w0[:, None] + UV[tt, 1] * w1[:, None] + UV[tt, 2] * w2[:, None]).astype(np.float32)
    return Hp, Wp, ys.astype(np.int32), xs.astype(np.int32), Gt, tx, uv, TI[tt].astype(np.int16), S[tt].astype(np.float16)


def preview_views(car, tex_imgs, tms, width=1600, layers=()):
    v = {k: render_view(car, k, tex_imgs, tms, width, layers=layers) for k in ('left', 'right', 'front', 'rear')}
    v['top'] = render_view(car, 'top', tex_imgs, tms, width, layers=layers).rotate(90, expand=True)
    return v


def preview_sheet(car, tex_imgs, tms, width=900, layers=()):
    views = [render_view(car, v, tex_imgs, tms, width, layers=layers) for v in ('left', 'right')]
    tv = [render_view(car, v, tex_imgs, tms, width // 2, layers=layers) for v in ('front', 'rear')]
    top = render_view(car, 'top', tex_imgs, tms, width // 2, layers=layers).rotate(90, expand=True)
    H = views[0].height + views[1].height + max(tv[0].height, top.height)
    sheet = Image.new('RGB', (width, H), (235, 236, 240))
    sheet.paste(views[0], (0, 0)); sheet.paste(views[1], (0, views[0].height))
    y = views[0].height + views[1].height
    sheet.paste(tv[0], (0, y)); sheet.paste(tv[1], (tv[0].width, y))
    return sheet


# ------------------------------------------------------------------ the whole job
def pad_texture(img, covered, reach=12):
    """Spread the painted colours out over the texels no triangle owns (the gaps between panels in the
    texture and thin seam triangles). The game blends neighbouring texels, so without this the old
    skin's colour shows as a line along door seams, lamp surrounds and panel edges."""
    img = img.copy()
    have = Image.fromarray((covered * 255).astype(np.uint8))
    for _ in range(reach):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            new = ImageChops.subtract(ImageChops.offset(have, dx, dy), have)      # filled next door, empty here
            img.paste(ImageChops.offset(img, dx, dy), (0, 0), new)
            have = ImageChops.lighter(have, new)
    return img


def spot_parts(tm, out_rgb, colour, log=print):
    """Body parts whose texture coordinates all sit on one spot (a bonnet scoop, a spoiler made to take one
    flat colour) show the colour of that one spot. Where nothing else uses it, it gets the base colour.
    Returns the texels set this way."""
    px = tm.t_px
    pa = 0.5 * np.abs((px[:, 1, 0] - px[:, 0, 0]) * (px[:, 2, 1] - px[:, 0, 1]) - (px[:, 2, 0] - px[:, 0, 0]) * (px[:, 1, 1] - px[:, 0, 1]))
    a3 = 0.5 * np.linalg.norm(np.cross(tm.t_pos[:, 1] - tm.t_pos[:, 0], tm.t_pos[:, 2] - tm.t_pos[:, 0]), axis=1)
    flat = np.nonzero((pa < 0.05) & (a3 > 0))[0]
    filled = np.zeros((tm.H, tm.W), bool)
    if not len(flat): return filled
    spot = np.round(px[flat].mean(1)).astype(int)
    keys, inv = np.unique(spot, axis=0, return_inverse=True)
    inv = inv.ravel()
    done, shared = [], []
    for k, (x, y) in enumerate(keys):
        area = a3[flat[inv == k]].sum()
        if area < 0.005: continue                      # a few stray slivers: not a part
        names = sorted(set(tm.mesh_of_tri[flat[inv == k]]))
        x0, x1, y0, y1 = max(0, x - 3), min(tm.W, x + 4), max(0, y - 3), min(tm.H, y + 4)
        if tm.covered[y0:y1, x0:x1].any():
            shared += names; continue                  # that spot is part of a painted panel too: leave it
        out_rgb[y0:y1, x0:x1] = colour
        filled[y0:y1, x0:x1] = True
        done += names
    if done: log(f'parts with one flat colour set to the base colour: {", ".join(done)[:100]}')
    if shared: log(f'parts with one flat colour that share a spot with a painted panel (they take its colour): {", ".join(shared)[:100]}')
    return filled


def car_catalogue(car_dir, cache_dir=None):
    """What the generator found in the car, as a dict (and a JSON file in cache_dir, reused while the
    model file is unchanged): body / wheel textures, glass, lights, every material with its textures."""
    kn5 = find_main_kn5(car_dir)
    st = os.stat(kn5)
    stamp = [os.path.basename(kn5), st.st_size, int(st.st_mtime)]
    path = os.path.join(cache_dir, os.path.basename(os.path.normpath(car_dir)) + '.json') if cache_dir else None
    if path and os.path.isfile(path):
        try:
            d = json.load(open(path, encoding='utf8'))
            if d.get('model') == stamp: return d
        except Exception: pass
    car = Car(car_dir, log=lambda s_: None)
    ext, inner, ov, ov_in = window_meshes(car, with_overlays=True)
    mats = {}
    for m in car.kn5.meshes:
        if m.mat is None or not len(m.idx): continue
        e = mats.setdefault(m.mat.name, dict(shader=m.mat.shader, see_through=bool(see_through(m.mat)),
                                             textures=dict(m.mat.samplers), meshes=[], area=0.0))
        e['meshes'].append(m.name); e['area'] = round(e['area'] + float(tri_area3(m).sum()), 3)
    d = dict(model=stamp, skins=car.skins, body_textures=car.body_textures, wheel_textures=car.wheel_textures, tyre_textures=car.tyre_textures,
             glass=[m.name for m in ext], glass_inside=[m.name for m in inner], sticker_meshes=[m.name for m in ov + ov_in],
             headlights=[m.name for m in find_headlights(car)], wheels={w: [round(float(v), 3) for v in c] for w, c in car.wheels.items()},
             size=[round(float(v), 3) for v in (car.hi - car.lo)], materials=mats,
             textures_in_model=sorted(car.kn5.textures))
    if path:
        os.makedirs(cache_dir, exist_ok=True)
        json.dump(d, open(path, 'w', encoding='utf8'), indent=1)
    return d


_MEMO = {}       # the last car worked on: its model, texel maps, stock-skin analysis and painted pattern
PATTERN_KEYS = ('base', 'accent', 'accent2', 'text', 'pattern', 'halftone', 'carbon', 'pattern_image', 'pattern_mode',
                'pattern_simplify', 'pattern_recolour')


def generate(car_dir, design, skin_name, out_root=None, resolution=None, log=print, preview_path=None,
             copy_other_from=None, progress=None, views=None, info=None, write=True):
    """write=False: a preview only - everything is worked out and drawn, but no file is written anywhere.
    info (a dict), when given, is filled with where every decal went and each view's frame, so the
    app can let the user move them on the preview."""
    step = progress or (lambda f, t: None)
    step(0.02, 'Reading the car model')
    kn5_ = find_main_kn5(car_dir)
    car_key = (os.path.normpath(car_dir), os.path.getmtime(kn5_), os.path.getsize(kn5_), resolution)
    if _MEMO.get('car_key') != car_key:
        _MEMO.clear()
        _MEMO['car_key'] = car_key
        _MEMO['car'] = Car(car_dir, log)
        _MEMO['tex'] = {}
    else:
        log('same car as last time: model, texture maps and stock skins reused')
    car = _MEMO['car']
    pat_key = tuple(str(design.get(k)) for k in PATTERN_KEYS)
    if _MEMO.get('pat_key') != pat_key:
        for t_ in _MEMO['tex'].values(): t_.pop('pattern', None)
        _MEMO['pat_key'] = pat_key; _MEMO.pop('prof', None)
    skin_id = re.sub(r'[^a-z0-9_]+', '_', skin_name.lower()).strip('_') or 'custom'
    out = os.path.join(out_root or os.path.join(car_dir, 'skins'), skin_id)
    if write and os.path.exists(out) and os.listdir(out):
        raise FileExistsError(f'skin folder already exists: {out}')
    tex_out, tms, ctx = {}, {}, {}
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
        ov = uv_overlap(car.meshes_for(tex))
        if ov > 3.0:
            # every panel reuses the same texels (a plain colour texture): no room for a livery
            log(f'{tex}: every panel shares this texture ({ov:.0f}x over) - only a plain colour is possible on this car')
            step(0.1, 'This car only takes a plain colour (shared paint texture)')
            if ref.size != (W, H):
                r_, a_ = ref.convert('RGB').resize((W, H), Image.LANCZOS), ref.getchannel('A').resize((W, H), Image.LANCZOS)
                r_.putalpha(a_); ref = r_
            a = np.asarray(ref.convert('RGBA')).astype(np.float32)
            lum = a[..., :3].mean(-1, keepdims=True)
            ref_l = max(np.percentile(lum, 90), 1)
            a[..., :3] = np.clip(rgb(design['base']) * np.clip(lum / ref_l, 0.35, 1.1), 0, 255)
            tex_out[tex] = Image.fromarray(a.astype(np.uint8), 'RGBA')
            continue
        k_ = car.body_textures.index(tex) / len(car.body_textures)
        step(0.1 + 0.55 * k_, f'Mapping {tex} onto the car')
        mem = _MEMO['tex'].setdefault(tex, {})
        if 'tm' not in mem or mem['tm'].W != W:
            tm = TexelMap(car.meshes_for(tex), W, H, log); tm.tex = tex
            occ = [m.pos[m.idx] for m in car.kn5.meshes if m.mat is not None and len(m.idx) and not see_through(m.mat)
                   and m.mat.samplers.get('txDiffuse') != tex and 'shadow' not in m.name.lower()]
            tm.occluders = np.concatenate(occ) if occ else None
            step(0.1 + 0.55 * (k_ + 0.3 / len(car.body_textures)), 'Comparing the stock skins')
            mem.clear()
            mem['tm'] = tm
            mem['stock'] = stock_analysis(car, tex, W, H, tm, log)
        tm = mem['tm']
        base, alpha, paint, shade = mem['stock']
        step(0.1 + 0.55 * (k_ + 0.6 / len(car.body_textures)), 'Painting the livery')
        if 'prof' in _MEMO and not ctx: ctx['prof'] = _MEMO['prof']
        cols, forced = render_design(car, tm, paint, design, log, info, ctx, mem)
        if 'prof' in ctx: _MEMO['prof'] = ctx['prof']
        # a decal is never broken: texels inside it that the paint mask left out (a stock logo, a
        # separate trim panel) are painted too - but not lights, grilles or glass
        ok_mesh = np.array([not NOT_PAINT_RE.search(nm) for nm in tm.mesh_of_tri])
        extra = forced & ~paint[tm.yy, tm.xx] & ok_mesh[tm.tri]
        if extra.any():
            paint = paint.copy(); paint[tm.yy[extra], tm.xx[extra]] = True
            names = sorted(set(tm.mesh_of_tri[np.unique(tm.tri[extra])]))
            log(f'decals also cover {extra.sum()} texels outside the paint area ({", ".join(names)[:90]})')
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
        filled = spot_parts(tm, out_rgb, rgb(design['base']), log)
        rgb_img = Image.fromarray(np.clip(out_rgb, 0, 255).astype(np.uint8))
        if write: rgb_img = pad_texture(rgb_img, tm.covered | filled)       # the gaps only matter in the game
        img = rgb_img.copy(); img.putalpha(Image.fromarray(alpha))
        tex_out[tex] = img; tms[tex] = tm
    step(0.68, 'Wheels, windows and lights')
    wheel_out = {}
    if design.get('wheel_colour'):
        for tex in car.wheel_textures:
            both = tex in car.tyre_meshes
            wheel_out[tex] = recolour_wheels(car, tex, design['wheel_colour'], log, only=car.rim_meshes[tex] if both else None,
                                             what='rims')
    if design.get('tyre_colour'):
        for tex in car.tyre_textures:
            both = tex in car.rim_meshes
            wheel_out[tex] = recolour_wheels(car, tex, design['tyre_colour'], log, only=car.tyre_meshes[tex] if both else None,
                                             start=wheel_out.get(tex), what='tyres')
    made = dict(tex_out); made.update(wheel_out)
    glass_layers = []
    if design.get('win_enable'):
        win, glass_layers = make_window_stickers(car, design, made, copy_other_from, log, resolution, info)
        made.update(win)
        for t in win:
            if t in tex_out: tex_out[t] = win[t]
    if design.get('win_tint'):
        tinted, tint_layers = tint_windows(car, design, made, copy_other_from, log)
        made.update(tinted)
        for t in tinted:
            if t in tex_out: tex_out[t] = tinted[t]
        # the tinted textures already carry the stickers: they replace the sticker layers of the same meshes
        names = {nm for tm_, _ in tint_layers for nm in tm_.mesh_of_tri.tolist()}
        glass_layers = [l for l in glass_layers if not set(l[0].mesh_of_tri.tolist()) & names] + tint_layers
    lights = find_headlights(car) if (design.get('lens_colour') or design.get('beam_colour')) else []
    if design.get('lens_colour'):
        made.update(tint_lenses(car, lights, design['lens_colour'], made, copy_other_from, log))
    if write:
        os.makedirs(out, exist_ok=True)
        mine = {t.lower() for t in made} | {os.path.splitext(t)[0].lower() + '.dds' for t in made}
        if copy_other_from:   # copy first, so files made here replace the copies
            src = os.path.join(car_dir, 'skins', copy_other_from)
            for f in os.listdir(src):
                if f.lower() in mine or f.lower() in ('preview.jpg', 'ui_skin.json', 'livery.png', 'generator_preview.png'):
                    continue
                if os.path.isfile(os.path.join(src, f)):
                    shutil.copyfile(os.path.join(src, f), os.path.join(out, f))
        step(0.8, 'Writing the textures')
        for tex, img in made.items():
            name = os.path.splitext(tex)[0] + '.dds'
            for s_ in car.skins:     # use the file-name spelling the car's own skins use
                f_ = find_skin_file(os.path.join(car_dir, 'skins', s_), tex)
                if f_: name = os.path.splitext(os.path.basename(f_))[0] + '.dds'; break
            write_dds(img, os.path.join(out, name), compress=design.get('compress', True))
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
    step(0.9, 'Drawing the preview')
    global LAST_LAYERS
    LAST_LAYERS = glass_layers                      # for tests that draw their own views
    if views is not None: views.update(preview_views(car, tex_out, tms, layers=glass_layers))
    sheet = preview_sheet(car, tex_out, tms, layers=glass_layers) if (views is None or preview_path or write) else None
    if info is not None: info['frames'] = {v: view_frame(car, v) for v in ('left', 'right', 'front', 'rear', 'top')}
    step(1.0, 'Done')
    if preview_path: sheet.save(preview_path)
    log(f'skin saved: {out}' if write else 'preview only - nothing was written to the car')
    return out, sheet, car, tms, tex_out
