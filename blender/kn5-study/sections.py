"""Cross-sections z = const of Kunos (black) vs our build (red), drawn at 4x scale-up per station."""
import sys, os, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, r'D:\Claude\Claude-\blender\kn5-study'); os.environ['PF_CLIP'] = '0.45,1,0,1.235,-2.2,-0.5'
import panel_fit as P
C = r'D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86'
V, F, Nv = P.load_mesh(C, 'GEO_body'); TK = V[F]
d = np.load(sys.argv[1]); TB = d['P'][d['F']]
def cut(T, z):
    out = []
    dz = T[:, :, 2] - z; s = np.sign(dz)
    m = (s.min(1) < 0) & (s.max(1) > 0)
    for t, e in zip(T[m], dz[m]):
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if e[i] * e[j] < 0: a = e[i] / (e[i] - e[j]); pts.append(t[i] + a * (t[j] - t[i]))
        if len(pts) == 2: out.append(pts)
    return np.array(out)
zs = [float(x) for x in sys.argv[3].split(',')]
win = float(sys.argv[4]) if len(sys.argv) > 4 else 0.12
Wp = 600; img = Image.new('RGB', (Wp * len(zs), Wp + 30), 'white'); dr = ImageDraw.Draw(img)
for k, z in zip(range(len(zs)), zs):
    A = cut(TK, z); B = cut(TB, z)
    # centre on the pillar: kunos points with y > 0.8
    pcs = P.crease_pieces(V, F, Nv); R1 = V[np.unique(pcs[int(os.environ.get('SEC_R', 1))])]
    near = R1[np.abs(R1[:, 2] - z) < 0.05]; c = near.mean(0) if len(near) else A.reshape(-1, 3).mean(0)
    sc = Wp / (2 * win)
    def tp(p): return (k * Wp + Wp / 2 + (p[0] - c[0]) * sc, 30 + Wp / 2 - (p[1] - c[1]) * sc)
    for segs, col, w in ((A, (0, 0, 0), 3), (B, (220, 30, 30), 1)):
        for a, b in segs: dr.line([tp(a), tp(b)], fill=col, width=w)
    dr.text((k * Wp + 8, 8), f'z = {z:.2f} m   (window {2*win*1000:.0f} mm; black Kunos, red ours)', fill='black')
    dr.line([(k * Wp, 0), (k * Wp, Wp + 30)], fill=(180, 180, 180))
img.save(sys.argv[2]); print('ok')
