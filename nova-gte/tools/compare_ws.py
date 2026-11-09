"""Side-by-side of the windscreen base area: photos 22 / 20 vs the model's EEVEE renders (export/match/c22_ee.png,
c20_ee.png) -> export/match/windscreen_base_compare.jpg"""
import os
from PIL import Image, ImageDraw, ImageEnhance
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load_r(p, bg=(150, 160, 150)):
    im = Image.open(p).convert("RGBA"); b = Image.new("RGBA", im.size, bg + (255,)); b.alpha_composite(im); return b.convert("RGB")
rows = []
for cam, phf, box in (("c22", "user_red_gte/redgte_22.webp", (330, 200, 880, 360)), ("c20", "user_red_gte/redgte_20.webp", (300, 230, 960, 400))):
    ph = Image.open(os.path.join(ROOT, "reference", "photos", phf)).convert("RGB")
    rd = load_r(os.path.join(ROOT, "export", "match", cam + "_ee.png")).resize(ph.size)
    rows.append((ph.crop(box), ImageEnhance.Brightness(rd.crop(box)).enhance(1.5)))
W = max(r[0].width for r in rows) * 2 + 8; H = sum(r[0].height for r in rows) + 40
S = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(S); yy = 20
d.text((6, 4), "REAL CAR (photos 22 and 20)", fill=(0, 0, 0)); d.text((W // 2 + 6, 4), "OURS, same cameras", fill=(0, 0, 0))
for a, b in rows:
    S.paste(a, (0, yy)); S.paste(b, (W // 2 + 4, yy)); yy += a.height + 10
S.save(os.path.join(ROOT, "export", "match", "windscreen_base_compare.jpg"), quality=90)
print(S.size)
