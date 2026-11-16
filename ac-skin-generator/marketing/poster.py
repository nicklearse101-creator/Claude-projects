"""The Ratty's4Skin Generator poster (1080 x 1350, for Discord): real liveries made by the app on four cars."""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))        # the car renders (render_cars.py) and the poster
APP = os.path.dirname(HERE)
FONTS = os.path.join(APP, 'fonts')
W, H = 1080, 1350
PURPLE, ORANGE, WHITE = (155, 61, 255), (255, 106, 0), (245, 245, 250)
random.seed(4)


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight:
        f.set_variation_by_name(weight)
    return f


EMOJI = ImageFont.truetype(r'C:\Windows\Fonts\seguiemj.ttf', 40)


def carbon(w, h):
    """A dark carbon-fibre weave."""
    y, x = np.mgrid[0:h, 0:w]
    cell = 6
    a = ((x // cell + y // cell) % 2).astype(np.float32)
    shine = 0.5 + 0.5 * np.sin((x + y) / cell * math.pi)
    v = 14 + 7 * a * shine + 3 * (1 - a) * (1 - shine)
    img = np.stack([v, v, v * 1.08], -1)
    # vignette + a purple glow from the top
    cx, cy = w / 2, h * 0.32
    r = np.hypot((x - cx) / w, (y - cy) / h)
    img *= np.clip(1.25 - r * 1.5, 0.35, 1.2)[..., None]
    glow = np.exp(-((x - w * 0.5) ** 2 / (w * 0.45) ** 2 + (y - h * 0.3) ** 2 / (h * 0.22) ** 2))
    img += glow[..., None] * np.array(PURPLE) * 0.22
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')


def stripes(img):
    """Slanted racing stripes across two corners."""
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for off, col, wdt, a in ((0, PURPLE, 70, 210), (95, ORANGE, 26, 230), (135, WHITE, 8, 160)):
        d.polygon([(W - 360 + off, 0), (W - 360 + off + wdt, 0), (W, 360 - off - wdt), (W, 360 - off)], fill=col + (a,))
        d.polygon([(0, H - 470 + off), (0, H - 470 + off + wdt), (470 - off - wdt, H), (470 - off, H)], fill=col + (int(a * 0.55),))
    img.alpha_composite(lay)


def glow_text(img, xy, text, f, fill, glow, blur=10, anchor='la', spacing=0):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    draw_spaced(d, xy, text, f, glow + (255,), anchor, spacing)
    g = lay.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(g); img.alpha_composite(g)
    d2 = ImageDraw.Draw(img)
    draw_spaced(d2, xy, text, f, fill, anchor, spacing)


def draw_spaced(d, xy, text, f, fill, anchor='la', spacing=0):
    if not spacing:
        d.text(xy, text, font=f, fill=fill, anchor=anchor); return
    widths = [f.getlength(c) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = xy[0] - (total / 2 if anchor[0] == 'm' else 0)
    for c, wd in zip(text, widths):
        d.text((x, xy[1]), c, font=f, fill=fill, anchor='l' + anchor[1]); x += wd + spacing


def car(path, width):
    im = Image.open(path).convert('RGBA')
    bb = im.getchannel('A').getbbox(); im = im.crop(bb)
    return im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)


def place_car(img, c, x, y, refl=True):
    """Car with a soft shadow and a faded floor reflection; (x, y) = top left."""
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
    d.ellipse([x + c.width * 0.04, y + c.height * 0.86, x + c.width * 0.96, y + c.height * 1.06], fill=(0, 0, 0, 200))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    if refl:
        r = c.transpose(Image.FLIP_TOP_BOTTOM)
        r = r.crop((0, 0, r.width, int(r.height * 0.32)))
        fade = (np.linspace(0.28, 0, r.height) ** 1.5)[:, None] * np.ones((1, r.width))
        a = (np.asarray(r.getchannel('A')).astype(np.float32) * fade).astype(np.uint8)
        r.putalpha(Image.fromarray(a))
        img.alpha_composite(r, (int(x), int(y + c.height - 6)))
    img.alpha_composite(c, (int(x), int(y)))


def speed_lines(img, box, n=38):
    x0, y0, x1, y1 = box
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for _ in range(n):
        y = random.uniform(y0, y1); L = random.uniform(120, 420); x = random.uniform(x0 - 100, x1 - L)
        col = random.choice([PURPLE, ORANGE, WHITE])
        d.line([(x, y), (x + L, y)], fill=col + (random.randint(40, 120),), width=random.choice([2, 3, 4]))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))


poster = carbon(W, H)
stripes(poster)

# --- title
glow_text(poster, (W / 2, 128), "RATTY'S4SKIN", font('RussoOne-Regular.ttf', 116), WHITE, PURPLE, blur=14, anchor='ms')
glow_text(poster, (W / 2, 196), 'GENERATOR', font('Orbitron[wght].ttf', 58, 'Black'), ORANGE, (120, 40, 0), blur=8,
          anchor='ms', spacing=14)
ImageDraw.Draw(poster).text((W / 2, 248), 'YOUR OWN ASSETTO CORSA LIVERY IN MINUTES, NOT HOURS.',
                            font=font('TitilliumWeb-BoldItalic.ttf', 31), fill=(225, 225, 235), anchor='ms')

# --- hero car + three more
speed_lines(poster, (0, 300, W, 560))
hero = car(os.path.join(HERE, 'ks_ferrari_488_gt3_left.png'), 1000)
place_car(poster, hero, (W - hero.width) / 2, 286)
row_y = 286 + hero.height + 52
small = [car(os.path.join(HERE, f'{n}_left.png'), 330) for n in ('ks_audi_r8_lms', 'ks_porsche_911_gt3_r_2016', 'wtcc_chevrolet_lacetti')]
for i, c in enumerate(small):
    place_car(poster, c, 22 + i * 352, row_y + (12 if i == 1 else 0))

# --- what it does
fy = row_y + max(c.height for c in small) + 62
feats = [('🎨', 'Pick a car, pick colours, pick from 50 patterns'),
         ('🔢', 'Number, team & driver name in 20 racing fonts'),
         ('🖼️', 'Drop in logos and drag them round the car live'),
         ('🪟', 'Window banners & tint'),
         ('✨', 'Gloss, metallic, pearl or matte paint (CSP)'),
         ('💾', "One click and it's in the game")]
panel = Image.new('RGBA', poster.size, (0, 0, 0, 0)); pd = ImageDraw.Draw(panel)
pd.rounded_rectangle([60, fy - 20, W - 60, fy + len(feats) * 49 + 2], 18, fill=(10, 8, 18, 175), outline=PURPLE + (200,), width=3)
poster.alpha_composite(panel)
d = ImageDraw.Draw(poster)
ff = font('ChakraPetch-Bold.ttf', 31)
for i, (em, t) in enumerate(feats):
    y = fy + i * 49
    d.text((96, y - 4), em, font=EMOJI, embedded_color=True)
    d.text((158, y + 2), t, font=ff, fill=WHITE)

# --- the punch line
by = fy + len(feats) * 49 + 68
glow_text(poster, (W / 2, by + 44), 'NO PHOTOSHOP. NO TEMPLATES. NO AI.', font('RussoOne-Regular.ttf', 50), WHITE, PURPLE, blur=9, anchor='ms')
glow_text(poster, (W / 2, by + 104), 'JUST PICK, PREVIEW, RACE.', font('Exo2-Italic[wght].ttf', 52, 'Black Italic'), ORANGE,
          (110, 35, 0), blur=7, anchor='ms')
# --- bottom bar: what it runs on (left), made for Ratty's Racing + badge (right)
bar = Image.new('RGBA', poster.size, (0, 0, 0, 0)); ImageDraw.Draw(bar).rectangle([0, H - 64, W, H], fill=(6, 5, 12, 200))
ImageDraw.Draw(bar).line([(0, H - 64), (W, H - 64)], fill=PURPLE + (220,), width=3)
poster.alpha_composite(bar)
logo = Image.open(os.path.join(APP, 'starter_logos', 'ratty_racing_logo.jpg')).convert('RGBA').resize((92, 92), Image.LANCZOS)
m = Image.new('L', logo.size, 0); ImageDraw.Draw(m).ellipse([0, 0, 91, 91], fill=255); logo.putalpha(m)
ring = Image.new('RGBA', (100, 100), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([0, 0, 99, 99], fill=PURPLE + (255,))
ring.alpha_composite(logo, (4, 4))
poster.alpha_composite(ring, (W - 118, H - 112))
d = ImageDraw.Draw(poster)
d.text((W - 134, H - 32), "MADE FOR RATTY'S RACING", font=font('TitilliumWeb-Black.ttf', 24), fill=WHITE, anchor='rm')
d.text((26, H - 54), '🏁', font=EMOJI, embedded_color=True)
d.text((80, H - 32), 'Assetto Corsa  ·  Windows 10/11', font=font('TitilliumWeb-BoldItalic.ttf', 22), fill=(185, 185, 200), anchor='lm')

poster.convert('RGB').save(os.path.join(HERE, 'Rattys4Skin_poster.png'), optimize=True)
print('saved', poster.size, 'punch line ends at', by + 110, 'bar at', H - 64)
