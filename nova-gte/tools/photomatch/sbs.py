"""photo | render composited over the photo (mismatch shows as red fringes) | render on grey, per camera."""
import sys
from PIL import Image
import preview as pv
M = '/mnt/user-data/uploads/vauxhall_nova_gte_1989/export/match/'
out = sys.argv[1]; suffix = sys.argv[2]; cams = sys.argv[3:]
rows = []
for c in cams:
    ph = Image.open(pv.PH[c]).convert('RGBA')
    rd = Image.open(M + c + suffix).convert('RGBA')
    if rd.size != ph.size:
        rd = rd.resize(ph.size, Image.LANCZOS)
    over = ph.copy(); over.alpha_composite(rd)
    bg = Image.new('RGBA', rd.size, (200, 200, 196, 255)); bg.alpha_composite(rd)
    tiles = []
    for im in (ph, over, bg):
        im = im.convert('RGB'); im.thumbnail((640, 480)); tiles.append(im)
    r = Image.new('RGB', (sum(t.width for t in tiles), max(t.height for t in tiles)))
    x = 0
    for t in tiles:
        r.paste(t, (x, 0)); x += t.width
    rows.append(r)
G = Image.new('RGB', (max(r.width for r in rows), sum(r.height for r in rows))); y = 0
for r in rows:
    G.paste(r, (0, y)); y += r.height
G.save(out, quality=86)
