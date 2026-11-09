import sys
from PIL import Image
import preview as pv
cams = sys.argv[2:]; out = sys.argv[1]
ims = []
for c in cams:
    pv.overlay(c, out=f'pv_{c}.jpg'); ims.append(Image.open(f'pv_{c}.jpg'))
G = Image.new('RGB', (1600, 1200 if len(ims) > 2 else 600))
for i, im in enumerate(ims):
    im = im.copy(); im.thumbnail((800, 600)); G.paste(im, ((i % 2) * 800, (i // 2) * 600))
G.save(out, quality=85)
