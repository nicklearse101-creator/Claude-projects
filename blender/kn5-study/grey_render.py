"""grey Lambert render of a triangle mesh (orthographic), optional coloured error dots - shared by the picture scripts"""
import numpy as np
from PIL import Image, ImageDraw


def render(Pv, Fv, Nvv, eye, centre, half, W=800, H=800, dots=None):
    f = np.array(eye, float); f /= np.linalg.norm(f)
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
        zz = a * z[0] + b * z[1] + c * z[2]; sub = zb[y0:y1 + 1, x0:x1 + 1]; m &= zz > sub
        if not m.any(): continue
        n = a[..., None] * Nn[t[0]] + b[..., None] * Nn[t[1]] + c[..., None] * Nn[t[2]]
        n /= np.maximum(np.linalg.norm(n, axis=-1), 1e-12)[..., None]
        nf = np.where((n @ f)[..., None] < 0, -n, n)
        sh = 40 + 170 * np.clip(nf @ L1, 0, 1) + 45 * np.clip(nf @ f, 0, 1) ** 30
        sub[m] = zz[m]; img[y0:y1 + 1, x0:x1 + 1][m] = sh[m]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGB')
    if dots is not None:
        Pd, e = dots; dr = ImageDraw.Draw(im); Xd = Pd - centre
        for p, ee in zip(Xd, e):
            if p @ f < -0.0 and False: continue
            qx, qy = (p @ r / half + 1) * W / 2, (1 - p @ u / half) * H / 2
            col = (0, 160, 0) if ee < 0.3 else (230, 160, 0) if ee < 1 else (230, 0, 0)
            rad = 2 if ee < 1 else 4
            dr.ellipse([qx - rad, qy - rad, qx + rad, qy + rad], fill=col)
    return im
