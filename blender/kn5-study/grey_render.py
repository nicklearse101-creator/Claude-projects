"""Grey smooth-shaded ortho render (numpy z-buffer): Kunos vs our build, same camera, side by side."""
import sys, os, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, r'D:\Claude\Claude-\blender\kn5-study'); os.environ['PF_CLIP'] = '0.45,1,0,1.235,-2.2,-0.5'
import panel_fit as P
C = r'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86'
V, F, Nv = P.load_mesh(C, 'GEO_body')
used = np.unique(F); 
d = np.load(sys.argv[1]); Pb, Fb, Nb = d['P'], d['F'], d['N']

def render(Pv, Fv, Nvv, eye, centre, half, W=900, H=900):
    f = np.array(eye, float); f /= np.linalg.norm(f)               # from target towards eye
    r = np.cross([0, 1, 0], f); r /= np.linalg.norm(r); u = np.cross(f, r)
    X = Pv - centre; sx = X @ r; sy = X @ u; sz = X @ f
    px = (sx / half + 1) * W / 2; py = (1 - sy / half) * H / 2
    Nn = Nvv / np.maximum(np.linalg.norm(Nvv, axis=1), 1e-12)[:, None]
    L1 = f + 0.6 * u + 0.3 * r; L1 /= np.linalg.norm(L1)
    zb = np.full((H, W), -1e9); img = np.full((H, W), 235.0)
    for t in Fv:
        x, y, z = px[t], py[t], sz[t]
        x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), W - 1)); y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), H - 1))
        if x0 > x1 or y0 > y1: continue
        den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(den) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
        b = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den; c = 1 - a - b
        m = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if not m.any(): continue
        zz = a * z[0] + b * z[1] + c * z[2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]; m &= zz > sub
        if not m.any(): continue
        n = a[..., None] * Nn[t[0]] + b[..., None] * Nn[t[1]] + c[..., None] * Nn[t[2]]
        n /= np.maximum(np.linalg.norm(n, axis=-1), 1e-12)[..., None]
        nf = np.where((n @ f)[..., None] < 0, -n, n)               # two-sided
        sh = 40 + 170 * np.clip(nf @ L1, 0, 1) + 45 * np.clip(nf @ f, 0, 1) ** 30
        sub[m] = zz[m]; img[y0:y1 + 1, x0:x1 + 1][m] = sh[m]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

views = [('C-pillar + drip rail, rear 3/4', [1.0, 0.7, -0.9], [0.58, 1.02, -1.45], 0.55),
         ('drip rail / window flange close-up', [1.0, 0.9, -0.5], [0.55, 1.08, -1.25], 0.18)]
tiles = []
for title, eye, cen, half in views:
    a = render(V, F, Nv, eye, np.array(cen), half); b = render(Pb, Fb, Nb, eye, np.array(cen), half)
    t = Image.new('RGB', (1820, 940), 'white'); t.paste(a.convert('RGB'), (0, 40)); t.paste(b.convert('RGB'), (920, 40))
    dr = ImageDraw.Draw(t); dr.text((10, 10), f'Kunos (original)  -  {title}', fill='black'); dr.text((930, 10), 'Ours: fitted CAD faces + ruled strips', fill='black')
    tiles.append(t)
out = Image.new('RGB', (1820, 940 * len(tiles)), 'white')
for i, t in enumerate(tiles): out.paste(t, (0, 940 * i))
out.save(sys.argv[2]); print('saved', sys.argv[2])
