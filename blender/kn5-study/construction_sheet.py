"""One row of construction sections per car: centreline profile, mid-door section, front-arch section,
door shut-line plan cut. Places the cuts automatically from the wheel nodes and measure.py landmarks.

    python construction_sheet.py OUT.png CAR_DIR [CAR_DIR ...]
"""
import sys, os, glob
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5
from section import draw
from measure import measure

INT = 'dmg,blur,collider,shadow,flycam,int,cockpit,seat,steer,belt,cinture,dash,pedal,driver,roll,cage,gauge,dial'
PW, PH = 700, 430


def fit(img):
    img = img.copy(); img.thumbnail((PW, PH)); c = Image.new('RGB', (PW, PH), (255, 255, 255))
    c.paste(img, ((PW - img.width) // 2, (PH - img.height) // 2)); return c


def row(car_dir):
    kn5 = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize)[-1]
    k = KN5(kn5, load_textures=False); m = measure(car_dir)
    W = {n.name[-2:]: n.world[3, :3] for n in k.nodes if n.name in ('WHEEL_LF', 'WHEEL_RF', 'WHEEL_LR', 'WHEEL_RR')}
    zf = (W['LF'][2] + W['RF'][2]) / 2; zr = (W['LR'][2] + W['RR'][2]) / 2; zmid = (zf + zr) / 2
    g = m.get('ground', 0) / 1000; half_w = m['width'] / 2000; yc = W['LF'][1]
    panels = [
        draw(k, 'x', 0.01, skip=INT, legend=False, px=1400, title='centreline'),
        draw(k, 'z', zmid, skip='dmg,blur,collider,shadow,flycam,driver', legend=False, px=1400, title='mid-wheelbase'),
        draw(k, 'z', zf, skip=INT, legend=False, px=1400, title='front axle',
             box=f'{half_w - 0.42:.3f}:{half_w + 0.06:.3f}:{g - 0.02:.3f}:{g + 0.95:.3f}'),
        draw(k, 'y', g + 0.65, skip=INT, legend=False, px=1400, title='plan y=650',
             box=f'{half_w - 0.35:.3f}:{half_w + 0.05:.3f}:{zmid - 0.9:.3f}:{zmid + 0.9:.3f}'),
    ]
    out = Image.new('RGB', (PW * 4, PH + 20), (255, 255, 255)); d = ImageDraw.Draw(out)
    for i, p in enumerate(panels): out.paste(fit(p), (i * PW, 20))
    d.text((6, 4), f"{m['car']}   L{m['length']:.0f} W{m['width']:.0f} H{m['height']:.0f} WB{m['wheelbase']:.0f}", fill=(0, 0, 0))
    return out


if __name__ == '__main__':
    rows = [row(c) for c in sys.argv[2:]]
    S = Image.new('RGB', (PW * 4, sum(r.height for r in rows)), (255, 255, 255)); y = 0
    for r in rows: S.paste(r, (0, y)); y += r.height
    S.save(sys.argv[1]); print('saved', sys.argv[1], S.size)
