"""Ratty Racing black/purple livery for wtcc_chevrolet_lacetti.
Builds chevrolet_lacetti_body.dds (4096x2048, mipmapped A8R8G8B8) from:
  - the 8 stock skins (their differences give the paintable-area mask, the
    brightest value per pixel gives baked shading, skin 6 gives fixed parts)
  - the Ratty Racing logo.
Coordinates below are in 2000x1000 "preview units" (scaled by K).
Side panels: bottom strip = car's left, top strip = car's right stored upside down:
shapes are mirrored vertically, writing is rotated 180 (checked with the 3D preview).
"""
import sys, glob, struct, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

CAR = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\wtcc_chevrolet_lacetti"
LOGO = sys.argv[1]
OUT = sys.argv[2]            # output folder
W, H = 4096, 2048
K = W / 2000.0
def P(x, y): return (x * K, y * K)

BLACK = (12, 11, 16)
PURPLE_D = (46, 8, 92)
PURPLE = (112, 32, 210)
NEON = (190, 110, 255)
WHITE = (240, 238, 245)

FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
def font(size, style="Bold Condensed"):
    f = ImageFont.truetype(FONT, int(size))
    f.set_variation_by_name(style)
    return f

# ---------------------------------------------------------------- stock data
stack = []
for s in ['19', '20', '23', '30', '31', '36', '6', '72']:
    f = glob.glob(os.path.join(CAR, 'skins', s, 'chevrolet_lacetti_body.*'))[0]
    stack.append(np.asarray(Image.open(f).convert('RGB').resize((W, H), Image.LANCZOS)).astype(np.float32))
A = np.stack(stack)
base = A[6].copy()                       # skin 6 = fixed parts source
sd = A.std(0).mean(-1)
paint = Image.fromarray(((sd > 9) * 255).astype(np.uint8))
paint = paint.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))   # close logo holes
pd_ = ImageDraw.Draw(paint)
for x0, y0, x1, y1 in [(793, 788, 922, 918), (793, 82, 922, 212),   # door number boards
                       (1150, 425, 1300, 575),                       # roof number board
                       (1876, 15, 1992, 468)]:                       # rear wing text band
    pd_.rectangle([P(x0, y0), P(x1, y1)], fill=255)
paint = paint.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
mask = np.asarray(paint).astype(np.float32) / 255.0

lum = A.mean(-1).max(0)
lum = np.asarray(Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(14))).astype(np.float32)
ref = np.percentile(lum[mask > 0.5], 90)
shade = np.clip(lum / ref, 0.6, 1.0) ** 0.8

# ---------------------------------------------------------------- logo prep
def prep_logo(path):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    # cyan/blue glow -> purple: pixels where blue dominates red
    blueish = np.clip((b - r) * 3.0, 0, 1)[..., None]
    lumv = (0.3 * r + 0.59 * g + 0.11 * b)[..., None]
    sat = (mx - mn)[..., None]
    purple = np.stack([0.62 * b + 0.25 * g, 0.18 * g + 0.10 * b, b * 1.0], -1)  # violet from blue/cyan
    purple = purple * 0.85 + lumv * np.array([0.35, 0.15, 0.45])
    out = a * (1 - blueish) + np.clip(purple, 0, 1) * blueish
    # alpha: drop the black background softly
    bg = np.array([2, 14, 31]) / 255.0
    dist = np.sqrt(((a - bg) ** 2).sum(-1)) * 255
    alpha = np.clip((dist - 28) / 40, 0, 1)
    al = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    rgba = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    rgba.putalpha(al)
    return rgba.crop(rgba.getbbox())

logo = prep_logo(LOGO)
logo.save(os.path.join(os.path.dirname(OUT.rstrip('\\/')) if False else os.path.dirname(__file__), 'logo_purple.png'))

def paste_logo(canvas, cx, cy, size, rot=0, glow=True):
    lg = logo.copy()
    lg.thumbnail((int(size * K), int(size * K)), Image.LANCZOS)
    if rot: lg = lg.rotate(rot, expand=True, resample=Image.BICUBIC)
    x, y = int(cx * K - lg.width / 2), int(cy * K - lg.height / 2)
    if glow:
        g = Image.new('RGBA', lg.size, NEON + (0,))
        g.putalpha(lg.getchannel('A').filter(ImageFilter.GaussianBlur(18 * K / 2)).point(lambda v: int(v * 0.55)))
        canvas.alpha_composite(g, (x, y))
    canvas.alpha_composite(lg, (x, y))

def text_img(txt, size, fill, style="Bold Condensed", stroke=0, stroke_fill=None, track=0):
    f = font(size * K, style)
    w = sum(f.getlength(c) for c in txt) + track * K * (len(txt) - 1) + 20
    hgt = int(size * K * 1.4)
    im = Image.new('RGBA', (int(w + stroke * 2 * K + 20), hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 10 + stroke * K
    for c in txt:
        d.text((x, size * K * 0.15), c, font=f, fill=fill, stroke_width=int(stroke * K), stroke_fill=stroke_fill)
        x += f.getlength(c) + track * K
    return im.crop(im.getbbox())

def paste_img(canvas, im, cx, cy, rot=0, flipv=False):
    if flipv: im = im.transpose(Image.FLIP_TOP_BOTTOM)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    canvas.alpha_composite(im, (int(cx * K - im.width / 2), int(cy * K - im.height / 2)))

# ---------------------------------------------------------------- design
# 1) mirrored layer: drawn in the bottom half, mirrored to the top half
L = Image.new('RGBA', (W, H), BLACK + (255,))
d = ImageDraw.Draw(L)

# fine carbon-ish diagonal texture in the black (very subtle)
tex = Image.new('L', (W, H), 0); td = ImageDraw.Draw(tex)
for i in range(-H, W, 7):
    td.line([(i, 0), (i + H, H)], fill=10, width=2)
L = Image.composite(Image.new('RGBA', (W, H), (22, 20, 30, 255)), L, tex.point(lambda v: v * 6))
d = ImageDraw.Draw(L)

# purple sweep: low at the front, rising toward the rear quarter
def grad_poly(pts, c0, c1, x0, x1):
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([P(*p) for p in pts], fill=255)
    g = np.zeros((H, W, 3), np.float32)
    t = np.clip((np.arange(W) / K - x0) / (x1 - x0), 0, 1)[None, :, None]
    g[:] = np.array(c0) * (1 - t) + np.array(c1) * t
    gi = Image.fromarray(g.astype(np.uint8)).convert('RGBA')
    L.paste(gi, (0, 0), m)

grad_poly([(430, 1000), (430, 955), (760, 930), (1180, 870), (1500, 800), (1705, 755), (1705, 1000)],
          PURPLE_D, PURPLE, 500, 1650)
# neon edge stripes following the sweep
def stripe(off, th, col):
    pts = [(430, 955 - off), (760, 930 - off), (1180, 870 - off), (1500, 800 - off), (1760, 745 - off)]
    poly = pts + [(x, y - th) for x, y in reversed(pts)]
    d.polygon([P(*p) for p in poly], fill=col)
stripe(14, 7, NEON)
stripe(30, 3, PURPLE)

# halftone dots dissolving upward from the sweep (front half)
for yy in np.arange(700, 960, 9):
    for xx in np.arange(440, 1300, 9):
        # sweep top line at this x
        edge = np.interp(xx, [430, 760, 1180, 1500, 1760], [955, 930, 870, 800, 745]) - 40
        dist = edge - yy
        if 0 < dist < 120:
            r = 3.6 * (1 - dist / 120) * K
            ox = 4.5 if int(yy / 9) % 2 else 0
            cx, cy = P(xx + ox, yy)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PURPLE)

# angular shard behind the rear wheel arch
d.polygon([P(1560, 1000), P(1640, 860), P(1680, 860), P(1610, 1000)], fill=BLACK)
d.polygon([P(1620, 1000), P(1690, 870), P(1705, 870), P(1640, 1000)], fill=NEON)

# mirror the graphics (shapes only) to the top strip = the car's right side
arr = np.asarray(L).copy()
arr[:H // 2] = arr[H // 2:][::-1]
L = Image.fromarray(arr)

# side writing / logos. Measured from the 3D model: both strips have the front at the
# left, the right-side (top) strip is stored upside down, so its writing is ROTATED 180
# (not flipped) at the vertically mirrored position.
def draw_side(canvas, right):
    yy = (lambda y: 1000 - y) if right else (lambda y: y)
    r = 180 if right else 0
    pnl = Image.new('RGBA', (int(118 * K), int(112 * K)), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pnl)
    pd.rounded_rectangle([0, 0, pnl.width - 1, pnl.height - 1], radius=int(10 * K), fill=WHITE, outline=NEON, width=int(4 * K))
    n = text_img("101", 78, BLACK, track=-2)
    pnl.alpha_composite(n, ((pnl.width - n.width) // 2, (pnl.height - n.height) // 2))
    paste_img(canvas, pnl, 858, yy(852), rot=r)
    paste_img(canvas, text_img("RATTY RACING", 34, WHITE, track=3), 690, yy(815), rot=r)
    paste_img(canvas, text_img("NICKLEARSE101", 17, NEON, style="SemiBold Condensed", track=5), 690, yy(842), rot=r)
    paste_logo(canvas, 1100, yy(858), 172, rot=r)

side = Image.new('RGBA', (W, H), (0, 0, 0, 0))
draw_side(side, False)
draw_side(side, True)
L.alpha_composite(side)

# 2) non-mirrored top-view graphics (bonnet / roof / boot) and bumpers / wing
T = Image.new('RGBA', (W, H), (0, 0, 0, 0))
td = ImageDraw.Draw(T)
# centre twin pinstripes along bonnet, roof, boot
for off in (-62, 56):
    td.rectangle([P(300, 500 + off), P(1720, 500 + off + 6)], fill=NEON)
# roof: purple panel fading out to the sides
roof = np.zeros((H, W, 4), np.uint8)
ys = np.arange(H) / K
fade = np.clip(1 - np.abs(ys - 500) / 120, 0, 1) ** 1.5
roof[..., 0], roof[..., 1], roof[..., 2] = PURPLE
xs = np.arange(W) / K
xm = ((xs > 930) & (xs < 1310)).astype(np.float32)
roof[..., 3] = (fade[:, None] * xm[None, :] * 200).astype(np.uint8)
T.alpha_composite(Image.fromarray(roof))
# roof number, readable from the left side like the stock layout
rn = text_img("101", 150, WHITE, stroke=3, stroke_fill=BLACK, track=-4)
paste_img(T, rn, 1120, 500, rot=90)
# bonnet: soft black backing disc, then big logo, tops toward the windscreen
disc = Image.new('L', (W, H), 0)
ImageDraw.Draw(disc).ellipse([P(530 - 175, 500 - 175), P(530 + 175, 500 + 175)], fill=255)
disc = disc.filter(ImageFilter.GaussianBlur(25 * K))
T.paste(Image.new('RGBA', (W, H), BLACK + (255,)), (0, 0), disc)
paste_logo(T, 530, 500, 330, rot=-90)
# boot: wordmark, readable from behind
bt = text_img("RATTY RACING", 40, WHITE, track=3)
paste_img(T, bt, 1560, 500, rot=90)
# rear bumper band (right column): wordmark reading bottom-to-top
rb = text_img("RATTY RACING", 70, WHITE, track=6)
paste_img(T, rb, 1765, 500, rot=90)
rb2 = text_img("RATTY RACING", 56, NEON, track=6)
paste_img(T, rb2, 1955, 235, rot=90)
paste_img(T, rb2, 1955, 765, rot=90)
# front bumper/splitter (left column): wordmark reading top-to-bottom
fb = text_img("RATTY RACING", 40, NEON, track=4)
paste_img(T, fb, 275, 285, rot=-90)
paste_img(T, fb, 275, 715, rot=-90)
L.alpha_composite(T)

# ---------------------------------------------------------------- composite
des = np.asarray(L.convert('RGB')).astype(np.float32)
des = des * shade[..., None]
out = base * (1 - mask[..., None]) + des * mask[..., None]
out = np.clip(out, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(os.path.dirname(__file__), 'body_flat.png'))

# ---------------------------------------------------------------- DDS writer (A8R8G8B8 + mips, alpha 0 like stock)
def write_dds(img, path):
    levels = []
    im = img
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
            a = np.asarray(lv.convert('RGB'))
            bgra = np.zeros(a.shape[:2] + (4,), np.uint8)
            bgra[..., 0], bgra[..., 1], bgra[..., 2] = a[..., 2], a[..., 1], a[..., 0]
            f.write(bgra.tobytes())

os.makedirs(OUT, exist_ok=True)
write_dds(Image.fromarray(out), os.path.join(OUT, 'chevrolet_lacetti_body.dds'))
print('done')
