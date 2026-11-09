"""Cut a kn5 model with a plane and draw the section (numpy + PIL). Shows how panels are really built:
skin thickness, returns/flanges at openings, shut-line grooves, gaps between panels, glass rebates.

    python section.py CAR.kn5 AXIS VALUE OUT.png [--only SUBSTR,SUBSTR] [--box u0:u1:v0:v1] [--px 4000]

AXIS: x (cut across the car's width -> side profile), z (cut at a station along the car -> cross-section),
      y (horizontal cut -> plan). AC axes: +x left, +y up, +z forward. --box crops in metres (drawn axes).
A 10 mm grid is drawn so gaps and flange depths can be read directly.
"""
import sys, os, argparse, colorsys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5


def cut(P, I, ax, val):
    d = P[:, ax] - val
    s = np.sign(d[I]); s[s == 0] = 1
    hit = ~((s[:, 0] == s[:, 1]) & (s[:, 1] == s[:, 2]))
    segs = []
    for t in I[hit]:
        pts = []
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            if (d[a] > 0) != (d[b] > 0):
                w = d[a] / (d[a] - d[b]); pts.append(P[a] + w * (P[b] - P[a]))
        if len(pts) == 2: segs.append(pts)
    return np.array(segs).reshape(-1, 2, 3)


def draw(k, axis, value, box='', px=1600, only='', skip='dmg,blur,collider,shadow,flycam', legend=True, title=''):
    """Return a PIL image of the section of KN5 object k (see module doc)."""
    ax = 'xyz'.index(axis)
    hu, hv = {0: (2, 1), 1: (0, 2), 2: (0, 1)}[ax]
    only = [s.lower() for s in only.split(',') if s]; skip = [s.lower() for s in skip.split(',') if s]
    res = []
    for m in k.meshes:
        nm = m.name.lower()
        if only and not any(s in nm for s in only): continue
        if any(s in nm for s in skip): continue
        sg = cut(m.pos, m.idx, ax, value)
        if len(sg): res.append((m.name, sg))
    if not res: return Image.new('RGB', (px, px // 2), (250, 250, 250))
    allp = np.concatenate([s.reshape(-1, 3) for _, s in res])
    if box:
        u0, u1, v0, v1 = map(float, box.split(':'))
    else:
        u0, u1 = allp[:, hu].min() - .02, allp[:, hu].max() + .02; v0, v1 = allp[:, hv].min() - .02, allp[:, hv].max() + .02
    sc = px / max(u1 - u0, v1 - v0)
    W, H = int((u1 - u0) * sc) + 1, int((v1 - v0) * sc) + 1
    img = Image.new('RGB', (W, H), (250, 250, 250)); d = ImageDraw.Draw(img)
    step = 0.01 if (u1 - u0) < 0.6 else 0.1
    for g in np.arange(np.ceil(u0 / step) * step, u1, step):
        x = (g - u0) * sc; d.line([(x, 0), (x, H)], fill=(228, 228, 228))
    for g in np.arange(np.ceil(v0 / step) * step, v1, step):
        y = H - (g - v0) * sc; d.line([(0, y), (W, y)], fill=(228, 228, 228))
    for i, (nm, sg) in enumerate(res):
        c = tuple(int(255 * x) for x in colorsys.hsv_to_rgb((i * 0.618) % 1, 0.9, 0.75))
        for p, q in sg:
            d.line([((p[hu] - u0) * sc, H - (p[hv] - v0) * sc), ((q[hu] - u0) * sc, H - (q[hv] - v0) * sc)], fill=c, width=2)
        if legend:
            d.rectangle([8, 8 + i * 14, 18, 18 + i * 14], fill=c); d.text((24, 7 + i * 14), nm[:40], fill=(0, 0, 0))
    d.text((W - 330, H - 18), f'{title}  grid {int(step * 1000)} mm  cut {axis}={value:.3f}', fill=(0, 0, 0))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kn5'); ap.add_argument('axis'); ap.add_argument('value', type=float); ap.add_argument('out')
    ap.add_argument('--only', default=''); ap.add_argument('--skip', default='dmg,blur,collider,shadow')
    ap.add_argument('--box', default=''); ap.add_argument('--px', type=int, default=3000)
    a = ap.parse_args()
    img = draw(KN5(a.kn5, load_textures=False), a.axis, a.value, a.box, a.px, a.only, a.skip)
    img.save(a.out); print('saved', a.out, img.size)


if __name__ == '__main__':
    main()
