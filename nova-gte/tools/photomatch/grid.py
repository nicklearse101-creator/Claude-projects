import sys
from PIL import Image, ImageDraw
src, out, x0, y0, x1, y1, k = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7]), float(sys.argv[7])
step = int(sys.argv[8]) if len(sys.argv) > 8 else 10
im = Image.open(src).convert('RGB')
c = im.crop((x0, y0, x1, y1)); c = c.resize((int((x1-x0)*k), int((y1-y0)*k)), Image.LANCZOS)
d = ImageDraw.Draw(c)
for gx in range((x0//step+1)*step, x1, step):
    major = gx % (step*5) == 0
    d.line([((gx-x0)*k, 0), ((gx-x0)*k, c.size[1])], fill=(255,255,0) if major else (110,110,0))
    if major: d.text(((gx-x0)*k+2, 2), str(gx), fill=(0,255,255))
for gy in range((y0//step+1)*step, y1, step):
    major = gy % (step*5) == 0
    d.line([(0, (gy-y0)*k), (c.size[0], (gy-y0)*k)], fill=(255,255,0) if major else (110,110,0))
    if major: d.text((2, (gy-y0)*k+2), str(gy), fill=(0,255,255))
c.save(out)
