"""Interior colours (Nik 17-18 Nov; research/Interior colours for AC skins.md; tested in game on the MX-5 Cup:
seats purple + cage "orange as orange").

The interior is found by name (AC's own COCKPIT_HR / COCKPIT_LR nodes, the INT_ token, part words - whole words only,
with the false friends the scan of 825 cars found). Each part is recoloured in the texture that holds its colour:

  colour tile   a small tiling detail texture (Kunos leather / alcantara / carpet tiles): OKLab lightness matching, the
                grain kept (detail gain 0.6 - 1.3);
  shading sheet the part's own texture is grey shading (AO, e.g. the MX-5's roll bar): recoloured from its unshadowed
                level (90th percentile) as a ratio, never paler than the colour (baked highlights went peach in the sun);
  baked colour  a coloured texture shared by several parts: only this part's texels (from its mesh's mapping), stitches
                and logos (colours far from the part's own) kept.

A texture any outside part also uses is never changed (e.g. the MX-5 dash plastic tile is the exterior trim's too), nor
displays, glass, carbon, metal parts or the body colour texture (metal_detail). Written as same-name textures in the skin
(no CSP needed), like the car's own stock skins do."""
import re
import numpy as np
from PIL import Image

GROUPS = {          # key: (name shown, pattern on material + mesh names) - checked in this order (belts before seats:
    # 'INT_SeatBelts')
    'belts': ('Seat belts', r'cintur|seat_?belt|belts?(?![a-z])|harness|sabelt|gurt'),
    'seats': ('Seats & leather', r'seat|sedil|sitz|asiento|bucket|recaro|sparco|bride|leather|pelle|cuoio|(?<=int_)skin|occ_skin|_skin_'),
    'alcantara': ('Alcantara / suede', r'alcant|alcnt|suede|scamosc'),
    'fabric': ('Fabric / cloth', r'fabric|cloth|tessut|stoff|tela(?![a-z])|textile'),
    'cage': ('Roll cage', r'roll_?bar|rollbar|roll_?cage|(?<![a-z])cage|gabbia|roll(?![a-z])|tubolar'),
    'carpet': ('Carpet / floor', r'carpet|tappet|moquette|floor_?mat|teppich'),
    'dash': ('Dashboard', r'dash(?!pad_lights)|plancia|cruscotto|armatur|tablero'),
}
ORDER = list(GROUPS)
# never coloured: displays, glass, lights, carbon / metal, stickers, gauges (and their look-alike names)
SKIP_RE = re.compile(r'glass|window|windscr|lcd|display|screen|monitor|gauge|dial|needle|decal|logo|badge|sticker|'
                     r'carbon|chrome|alu(?![a-z])|alumin|metal(?!_?paint)|steel|light|lamp|led(?![a-z])|mirror|shadow|'
                     r'blur|emissive|(?<![a-z])ext_|stitch|seam|cucitur|simbol|symbol|digit|number', re.I)
INTERIOR_RE = re.compile(r'(?<![a-z])int(?![a-z])|int_|_int(?![a-z])|interior|interno|cockpit|abitacolo|'
                         + '|'.join(g[1] for g in GROUPS.values()), re.I)
# detail textures that are not a colour (scratches, noise, the body colour ...)
NOT_COLOUR_DETAIL = re.compile(r'metal_detail|scratch|noise|dirt|black|white|flat|grey|gray|plain|dust|damage|nm|normal', re.I)


def is_interior(mesh):
    """Inside the car: under AC's cockpit nodes, or named so."""
    par = [p.upper() for p in (getattr(mesh, 'parents', None) or ())]
    if any(p.startswith('COCKPIT_') for p in par): return True
    return bool(INTERIOR_RE.search(mesh.mat.name) or INTERIOR_RE.search(mesh.name))


def group_of(mesh):
    text = f'{mesh.mat.name} {mesh.name} {mesh.mat.samplers.get("txDetail") or ""}'
    if SKIP_RE.search(mesh.mat.name) or SKIP_RE.search(mesh.name): return None
    for k in ORDER:
        if re.search(GROUPS[k][1], text, re.I): return k
    return None


def find_parts(car):
    """{group: [job]} - job = dict(tex, kind 'tile' / 'sheet' / 'region', meshes, materials); and the log of what was
    left alone and why."""
    users = {}                        # texture -> [(mesh, slot)]
    for m in car.kn5.meshes:
        if m.mat is None or not len(m.idx): continue
        for slot, t in m.mat.samplers.items():
            if t: users.setdefault(t, []).append((m, slot))
    inside = {id(m): is_interior(m) for m in car.kn5.meshes if m.mat is not None and len(m.idx)}
    parts, notes = {}, []
    by_tex = {}
    for m in car.kn5.meshes:
        if m.mat is None or not len(m.idx) or not inside.get(id(m)): continue
        g = group_of(m)
        if g is None: continue
        det = m.mat.samplers.get('txDetail')
        dif = m.mat.samplers.get('txDiffuse')
        if det and not NOT_COLOUR_DETAIL.search(det) and m.mat.props.get('useDetail', 1) != 0:
            tex, kind = det, 'tile'
        elif dif:
            tex, kind = dif, 'sheet'
        else:
            continue
        if SKIP_RE.search(tex): continue              # display symbols, stitches ... by their texture's name
        by_tex.setdefault((tex, kind), {}).setdefault(g, []).append(m)
    for (tex, kind), groups in by_tex.items():
        outside = [m.mat.name for m, _ in users.get(tex, []) if not inside.get(id(m))]
        if outside:
            notes.append(f'{tex}: also used outside the car ({", ".join(sorted(set(outside))[:3])}) - left as it is')
            continue
        if 'metal_detail' in tex.lower(): continue
        mine = {id(x) for v in groups.values() for x in v}
        strangers = [m for m, _ in users.get(tex, []) if id(m) not in mine]      # other interior parts on it
        if len(groups) > 1 or (kind == 'sheet' and strangers):
            # one texture, several parts: each only on its own texels
            if kind == 'tile':
                notes.append(f'{tex}: one tile for {", ".join(GROUPS[g][0].lower() for g in groups)} - they change together')
                g = next(g for g in ORDER if g in groups)
                parts.setdefault(g, []).append(dict(tex=tex, kind='tile', meshes=[x for v in groups.values() for x in v]))
                continue
            for g, ms in groups.items():
                parts.setdefault(g, []).append(dict(tex=tex, kind='region', meshes=ms,
                                                    others=[x for g2, v in groups.items() if g2 != g for x in v] + strangers))
        else:
            g, ms = next(iter(groups.items()))
            parts.setdefault(g, []).append(dict(tex=tex, kind=kind, meshes=ms))
    return parts, notes


# ------------------------------------------------------------------ colour (OKLab; numpy only)
M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
M2i = np.linalg.inv(M2).astype(np.float32)
M1i = np.linalg.inv(M1).astype(np.float32)


def to_lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def oklab(c): return np.cbrt(to_lin(c) @ M1.T) @ M2.T


def lin_of(lab): return ((lab @ M2i.T) ** 3) @ M1i.T


def srgb_of(lab):
    """OKLab -> sRGB, chroma reduced (lightness and hue kept) where the colour is outside sRGB."""
    lab = lab.copy()
    lo, hi = np.zeros(lab.shape[:-1], np.float32), np.ones(lab.shape[:-1], np.float32)
    bad = ((lin_of(lab) < -1e-4) | (lin_of(lab) > 1 + 1e-4)).any(-1)
    if bad.any():
        ab = lab[..., 1:].copy()
        for _ in range(12):
            mid = (lo + hi) / 2
            t = lab.copy(); t[..., 1:] = ab * mid[..., None]
            ok = ~((lin_of(t) < -1e-4) | (lin_of(t) > 1 + 1e-4)).any(-1)
            lo = np.where(ok, mid, lo); hi = np.where(ok, hi, mid)
        lab[..., 1:] = np.where(bad[..., None], ab * lo[..., None], ab)
    return to_srgb(lin_of(lab))


def recolour(img, target, kind, mask=None):
    """The texture with its colour changed to target (r, g, b 0-255), detail kept. mask: only those texels."""
    a = np.asarray(img.convert('RGBA')).astype(np.float32) / 255
    rgb = a[..., :3]
    lab = oklab(rgb)
    L = lab[..., 0]
    t = oklab(np.array(target, np.float32) / 255)
    sel = mask if mask is not None else (L > 0.02)
    if not sel.any(): return img
    out = lab.copy()
    if kind == 'tile':
        ref = np.median(lab[sel], axis=0)
        g = float(np.clip(t[0] / max(ref[0], 1e-3), 0.6, 1.3))
        Lo = np.clip(t[0] + g * (L - ref[0]), 0, 1)
        k = np.clip(Lo / max(t[0], 1e-3), 0, 1.3)[..., None]
        out[..., 0] = Lo
        out[..., 1:] = t[1:] * k + (lab[..., 1:] - ref[1:]) * 0.5
    else:   # 'sheet' / 'region': shading as a ratio of the unshadowed level, never paler than the colour
        ref = np.percentile(L[sel], 90)
        r = np.clip(L / max(ref, 1e-3), 0, 1.0)
        out[..., 0] = t[0] * r
        out[..., 1:] = t[1:] * r[..., None]
        if kind == 'region':
            # stitches, logos, piping: texels far from the part's own colour stay as they are
            med = np.median(lab[sel], axis=0)
            d = np.sqrt(((lab[..., 1:] - med[1:]) ** 2).sum(-1) * 4 + np.maximum(L - med[0], 0) ** 2)
            sel = sel & (d < 0.12)
    res = rgb.copy()
    res[sel] = srgb_of(out[sel])
    o = np.dstack([res, a[..., 3]])
    return Image.fromarray(np.clip(np.round(o * 255), 0, 255).astype(np.uint8), 'RGBA')


def paint_interior(car, colours, current_texture, made, texel_map, rgb, log):
    """{texture: image} with the interior colours (colours = {group: '#rrggbb'}); every texture done once even when
    several parts use it."""
    parts, notes = find_parts(car)
    for n in notes: log(f'interior: {n}')
    out = {}
    for g in ORDER:
        col = colours.get(g)
        if not col: continue
        if g not in parts:
            log(f'interior: {GROUPS[g][0].lower()} - not found in this car'); continue
        for job in parts[g]:
            tex = job['tex']
            img = out.get(tex) or current_texture(tex)
            if img is None: continue
            mask = None
            if job['kind'] == 'region':
                W, H = img.size
                own = texel_map(job['meshes'], W, H).covered
                other = texel_map(job['others'], W, H).covered if job.get('others') else np.zeros_like(own)
                mask = own & ~other
            out[tex] = recolour(img, tuple(int(v) for v in rgb(col)), job['kind'], mask)
            log(f'interior: {GROUPS[g][0].lower()} -> {col} ({tex}, {job["kind"]})')
    return out
