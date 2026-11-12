"""Every pattern as a swatch (side over top, front on the left) on one sheet, in a few colour sets, to judge by eye.
python tests/pattern_sheet.py OUT.png [only_new]"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw, ImageFont
import skingen, patterns_plus

out = sys.argv[1]
keys = [k for k in skingen.PATTERNS if k not in ('picture',)]
if len(sys.argv) > 2: keys = [k for k in keys if k in patterns_plus.NAMES]
SETS = [dict(base='#0c0b10', accent='#7020d2', accent2='#be6eff', text='#f0eef5'),      # Ratty purple (the default)
        dict(base='#f2f2f2', accent='#d01818', accent2='#111111', text='#111111'),      # white / red / black
        dict(base='#0a2a5c', accent='#ff8a00', accent2='#ffffff', text='#ffffff')]      # blue / orange
W = 300
fnt = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 15)
tiles, slow = [], []
for k in keys:
    row = []
    for cs in SETS:
        t = time.time()
        row.append(skingen.pattern_swatch(dict(skingen.DEFAULT_DESIGN, pattern=k, **cs), W))
        if time.time() - t > 1.5: slow.append((k, round(time.time() - t, 1)))
    tiles.append((k, row))
th = tiles[0][1][0].height
cols = 2
cell_w, cell_h = len(SETS) * (W + 6) + 10, th + 28
sheet = Image.new('RGB', (cols * cell_w, ((len(tiles) + cols - 1) // cols) * cell_h), (40, 40, 44))
d = ImageDraw.Draw(sheet)
for i, (k, row) in enumerate(tiles):
    x0, y0 = (i % cols) * cell_w + 5, (i // cols) * cell_h
    d.text((x0, y0 + 3), skingen.PATTERNS[k], fill=(255, 255, 255), font=fnt)
    for j, im in enumerate(row): sheet.paste(im, (x0 + j * (W + 6), y0 + 24))
sheet.save(out)
print('saved', out, len(tiles), 'patterns; slow:', slow or 'none')
