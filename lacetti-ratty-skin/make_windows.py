"""Window textures for the Ratty Racing Lacetti skin, built over stock skin 6.
Same orientation as stock (stock text reads correctly in-game)."""
import sys, os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CAR = r"D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\wtcc_chevrolet_lacetti"
OUT = sys.argv[1]
SRC = os.path.join(CAR, 'skins', '6')
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
def font(size, style="Bold Condensed"):
    f = ImageFont.truetype(FONT, int(size)); f.set_variation_by_name(style); return f

def text(d, xy, s, size, fill, anchor="mm", style="Bold Condensed"):
    d.text(xy, s, font=font(size, style), fill=fill, anchor=anchor)

def rot_text(img, center, s, size, fill, angle):
    f = font(size)
    t = Image.new('RGBA', (int(f.getlength(s)) + 20, int(size * 1.5)), (0, 0, 0, 0))
    ImageDraw.Draw(t).text((t.width / 2, t.height / 2), s, font=f, fill=fill, anchor="mm")
    t = t.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(t, (int(center[0] - t.width / 2), int(center[1] - t.height / 2)))

def write_dds(img, path):
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
            a = np.asarray(lv.convert('RGBA'))
            f.write(a[..., [2, 1, 0, 3]].copy().tobytes())

PURPLE = (60, 12, 110, 255)
NEON = (190, 110, 255, 255)
WHITE = (245, 243, 250, 255)

# ---- exterior windows (512x512)
w = Image.open(os.path.join(SRC, 'chevrolet_lacetti_windows.dds')).convert('RGBA')
glass = w.getpixel((160, 150))          # plain tinted glass pixel (colour + alpha)
d = ImageDraw.Draw(w)
# windscreen: wipe banner + name, new two-tone banner
top = Image.new('L', w.size, 0); td = ImageDraw.Draw(top)
td.rectangle([0, 0, 330, 100], fill=255)
win_shape = np.asarray(w.getchannel('A')) > 0
area = np.asarray(top) > 0
arr = np.asarray(w).copy()
sel = area & win_shape
arr[sel] = glass
band = sel & (np.arange(512)[:, None] < 62)
arr[band] = (14, 12, 20, 255)
stripe = sel & (np.arange(512)[:, None] >= 62) & (np.arange(512)[:, None] < 68)
arr[stripe] = NEON
low = sel & (np.arange(512)[:, None] >= 68) & (np.arange(512)[:, None] < 100)
arr[low] = PURPLE
w = Image.fromarray(arr)
d = ImageDraw.Draw(w)
text(d, (160, 34), "RATTY RACING", 42, WHITE)
text(d, (160, 84), "NICKLEARSE101", 22, WHITE, style="SemiBold Condensed")
# rear window: banner + name (keep flag)
d.rectangle([20, 203, 317, 236], fill=(14, 12, 20, 255))
d.rectangle([20, 236, 317, 239], fill=NEON)
text(d, (168, 220), "RATTY RACING", 30, WHITE)
d.rectangle([110, 298, 230, 332], fill=glass)
text(d, (168, 315), "NICKLEARSE101", 26, WHITE)
# side windows: replace "R. Huff" (reads bottom-to-top)
for (x0, y0, x1, y1), c in [((378, 108, 402, 192), (390, 150)), ((470, 228, 494, 300), (482, 264))]:
    d.rectangle([x0, y0, x1, y1], fill=glass)
    rot_text(w, c, "NICKLEARSE101", 20, WHITE, 90)

# ---- interior view of the windscreen (1024x512): back of the banner
wi = Image.open(os.path.join(SRC, 'chevrolet_lacetti_windows_interior.dds')).convert('RGBA').resize((1024, 512))
ai = np.asarray(wi).copy()
# wipe stock text: copy a clean column across each row of the banner area
for y in range(20, 250):
    ai[y, 85:745] = ai[y, 756]
wi = Image.fromarray(ai)
di = ImageDraw.Draw(wi)
text(di, (415, 72), "RATTY RACING", 78, (20, 18, 28, 255))
text(di, (95, 150), "NICKLEARSE101", 52, (20, 18, 28, 255), anchor="lm")

os.makedirs(OUT, exist_ok=True)
write_dds(w, os.path.join(OUT, 'chevrolet_lacetti_windows.dds'))
write_dds(wi, os.path.join(OUT, 'chevrolet_lacetti_windows_interior.dds'))
w.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'windows_flat.png'))
wi.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'windows_interior_flat.png'))
print('done')
