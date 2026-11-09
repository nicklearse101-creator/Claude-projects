"""Render the body_geom shell (plus wheels) through the bundle-adjusted photo cameras and overlay it on the
reference photos - a fast stand-in for Blender's render_matched.py while fitting the shell.
usage: NOVA_ROOT=... python3 preview.py [cam ...]   -> pv_<cam>.jpg"""
import json, math, os, sys
import numpy as np, cv2
from PIL import Image
ROOT = os.environ.get('NOVA_ROOT', r'D:\Claude\vauxhall_nova_gte_1989')
sys.path.insert(0, os.path.join(ROOT, 'blender', 'scripts'))
import body_geom as g

U = os.environ.get('NOVA_PHOTOS', os.path.join(ROOT, 'reference', 'photos')) + '/'
PH = {'c20': U + 'user_red_gte/redgte_20.webp', 'c22': U + 'user_red_gte/redgte_22.webp', 'c23': U + 'user_red_gte/redgte_23.webp',
      'c24': U + 'user_red_gte/redgte_24.webp', 'cAR': U + 'other_sources/anglia_rear.jpg',
      'cCF': U + 'commons/1989_Vauxhall_Nova_GTE_1.6_Front.jpg', 'cS': U + 'other_sources/anglia_side.jpg'}
B = json.load(open('ba_result.json')); O = json.load(open('obs.json'))
R_LOADED = B['points']['wheel_r_F400']
TRACK = {'F': 1.320, 'R': 1.307}


def project(c, X):
    cp = np.array(B['cams'][c]); W, H = O[c]['W'], O[c]['H']
    R, _ = cv2.Rodrigues(cp[:3]); Xc = X @ R.T + cp[3:6]
    z = Xc[:, 2]; x = Xc[:, 0] / z; y = Xc[:, 1] / z
    s = 1 + cp[7] * (x * x + y * y)
    return np.stack([W / 2 + cp[6] * x * s, H / 2 + cp[6] * y * s], 1), z, R.T @ np.array([0, 0, 1.0]), -R.T @ cp[3:6]


def shell_mesh():
    """Final (swept, photo-frame) left-half shell: vertices, faces, material names."""
    rs, caps, faces, rows = g.loft()
    n = len(rs[0])
    flat = [p for r in rs for p in r] + caps
    V = np.array([g.finalize(p, photo_frame=True) for p in flat])
    U = np.array(flat)
    mats = []
    for f, row in zip(faces, rows):
        c = U[list(f)].mean(0)
        top_k = row - (g.NS - 1) if row >= g.NS - 1 else -1
        mats.append(g.MATS[g.zone(c[0], c[1], c[2], row, top_k)])
    return V, faces, mats, n


def tri_list(V, F, M):
    T, TM = [], []
    for f, m in zip(F, M):
        for k in range(1, len(f) - 1):
            T.append((f[0], f[k], f[k + 1])); TM.append(m)
    return np.array(T), np.array(TM)


def wheel_tris(axle, side, r_out=None):
    """Tyre (dark cylinder) + rim face disc, photo frame."""
    y = g.PF['arch_front'][0] * 0 + (-1.1715 if axle == 'F' else 1.1715)
    xc = side * TRACK[axle] / 2; zc = R_LOADED
    ro = r_out or 0.2916; w = 0.175
    seg = 48; P = []; T = []; C = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        P.append((xc - w / 2, y + ro * math.cos(a), zc + ro * math.sin(a)))
        P.append((xc + w / 2, y + ro * math.cos(a), zc + ro * math.sin(a)))
    for k in range(seg):
        a0, a1 = 2 * k, 2 * ((k + 1) % seg)
        T += [(a0, a0 + 1, a1 + 1), (a0, a1 + 1, a1)]; C += [(25, 25, 25)] * 2
    for sx in (-1, 1):                 # sidewall discs
        cidx = len(P); P.append((xc + sx * w / 2, y, zc))
        for k in range(seg):
            a0, a1 = 2 * k + (sx > 0), 2 * ((k + 1) % seg) + (sx > 0)
            T.append((a0, a1, cidx)); C.append((30, 30, 30))
    # rim face disc on the outer side
    rr = 0.0254 * 14 / 2 * 0.98; xo = xc + side * (w / 2 + 0.002) - side * 0.035
    base = len(P); P.append((xo, y, zc))
    for k in range(seg):
        a = 2 * math.pi * k / seg; P.append((xo, y + rr * math.cos(a), zc + rr * math.sin(a)))
    for k in range(seg):
        T.append((base, base + 1 + k, base + 1 + (k + 1) % seg)); C.append((170, 170, 175))
    return np.array(P), np.array(T), C


MATC = {'paint_gunmetal': (150, 40, 45), 'glass_tint': (40, 50, 55), 'trim_black': (15, 15, 15), 'trim_grey': (80, 80, 85),
        'lamp_clear': (220, 220, 210), 'lamp_red': (160, 10, 10), 'lamp_amber': (230, 120, 10), 'panel_gap': (0, 0, 0), 'liner': (10, 10, 10)}


def render(c, mats=None, glass_in_mask=False):
    W, H = O[c]['W'], O[c]['H']
    V, F, M, n = shell_mesh()
    # mirror
    VR = V.copy(); VR[:, 0] *= -1
    T, TM = tri_list(V, F, M)
    TR = T[:, ::-1] + len(V)
    VA = np.vstack([V, VR]); TA = np.vstack([T, TR]); TMA = np.concatenate([TM, TM])
    cols = []
    cen = VA[TA].mean(1)
    keep = np.ones(len(TA), bool)
    for k, (cy, cz, r) in g.arches(photo_frame=True).items():
        inside = ((cen[:, 1] - cy) ** 2 + (cen[:, 2] - cz) ** 2 < r * r) & (np.abs(cen[:, 0]) > 0.5)
        keep &= ~inside
    TA, TMA, cen = TA[keep], TMA[keep], cen[keep]
    C = [MATC[m] for m in TMA]
    GL = [m == 'glass_tint' for m in TMA]
    allP = [VA]; allT = [TA]; allC = C; allG = GL
    off = len(VA)
    # arch liners (dark discs at |x| 0.55)
    for k, (cy, cz, r) in g.arches(photo_frame=True).items():
        for sx in (-1, 1):
            seg = 40; P = [(sx * 0.55, cy, cz)] + [(sx * 0.55, cy + r * math.cos(2 * math.pi * i / seg), cz + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
            P = [p for p in P]; Tl = [(0, 1 + i, 1 + (i + 1) % seg) for i in range(seg)]
            # only the part above the floor line
            allP.append(np.array(P)); allT.append(np.array(Tl) + off); allC += [MATC['liner']] * seg; allG += [False] * seg; off += len(P)
    for axle in 'FR':
        for sx in (-1, 1):
            P, Tw, Cw = wheel_tris(axle, sx)
            allP.append(P); allT.append(Tw + off); allC += Cw; allG += [False] * len(Cw); off += len(P)
    P = np.vstack(allP); T = np.vstack(allT); C = np.array(allC, float); G = np.array(allG)
    uv, z, fwd, cam = project(c, P)
    tri_uv = uv[T]; tri_z = z[T]
    ok = (tri_z > 0.2).all(1)
    # shading: normal vs view
    a, b, cc = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    nrm = np.cross(b - a, cc - a); nl = np.linalg.norm(nrm, axis=1) + 1e-12; nrm /= nl[:, None]
    view = (a + b + cc) / 3 - cam; view /= np.linalg.norm(view, axis=1)[:, None]
    light = np.array([0.3, -0.4, 0.85]); light /= np.linalg.norm(light)
    sh = 0.45 + 0.35 * np.abs((nrm * view).sum(1)) + 0.2 * np.clip(np.abs(nrm @ light), 0, 1)
    order = np.argsort(-tri_z.mean(1))
    img = np.zeros((H, W, 3), np.uint8); mask = np.zeros((H, W), np.uint8)
    ID = np.full((H, W), -1, np.int32)
    for t in order:
        if not ok[t] or nl[t] < 1e-12:
            continue
        pts = np.round(tri_uv[t] * 4).astype(np.int32)
        col = tuple(int(v) for v in np.clip(C[t] * sh[t], 0, 255))
        cv2.fillConvexPoly(img, pts, col, lineType=cv2.LINE_8, shift=2)
        if glass_in_mask or not G[t]:
            cv2.fillConvexPoly(mask, pts, 255, shift=2)
    return img, mask


def overlay(c, mats=None, out=None, crop=None, show_pts=True):
    img, mask = render(c, mats)
    ph = np.array(Image.open(PH[c]).convert('RGB')).astype(np.float32)
    a = (mask > 0)[..., None] * 0.35
    o = ph * (1 - a) + img.astype(np.float32) * a
    e = cv2.Canny(img, 30, 80)
    sil = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    o[e > 0] = [255, 255, 0]
    o[sil > 0] = [0, 255, 255]
    if show_pts:
        W = O[c]['W']; s = max(2, W // 500)
        for nme, xy in O[c]['pts'].items():
            cv2.circle(o, tuple(int(v) for v in xy), s + 1, (255, 0, 0), -1)
    im = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))
    if crop:
        im = im.crop(crop)
    im.thumbnail((1600, 1200))
    im.save(out or f'pv_{c}.jpg', quality=88)
    return img, mask


if __name__ == '__main__':
    for c in (sys.argv[1:] or PH):
        overlay(c); print('saved', c)
