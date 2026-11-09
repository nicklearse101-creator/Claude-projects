"""Orthographic silhouettes of a car (side / top / front / rear), aligned on the wheels, and a comparison
of two cars: outline distance in mm and an overlay image. Use it to check a model against another model of
the same car, or against a blueprint mask (any black-on-white PNG at the same mm/px and alignment).

    python silhouette.py A_DIR B_DIR OUT_PREFIX [--mmpx 2] [--align front|mid|rear]

Alignment: origin at the chosen axle station, on the centreline, at the tyre contact height (ground), so
ride height and kn5 origin do not matter. Wheels/tyres are excluded (they move with suspension).
Outputs OUT_PREFIX_{side,top,front}.png overlays (red = A only, blue = B only, dark = both) and prints
IoU and outline distance (median / p95 / max, mm). Also writes OUT_PREFIX_A_side.csv: the side outline as
(z, y) points in mm, a ready template for tracing or for comparing with a blueprint.
"""
import sys, os, glob, argparse
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5
from fairness import nearest_dist

SKIP = ('shadow', 'flycam', 'damage_glass', 'dmg', 'collider', 'blur', 'driver', 'beam', 'plate', 'antenna')
VIEWS = {'side': (2, 1), 'top': (2, 0), 'front': (0, 1)}


def load(car_dir, align):
    kn5 = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize)[-1]
    k = KN5(kn5, load_textures=False)
    W = {n.name[-2:]: n.world[3, :3] for n in k.nodes if n.name in ('WHEEL_LF', 'WHEEL_RF', 'WHEEL_LR', 'WHEEL_RR')}
    tyre_bottom = []
    for n in k.nodes:
        if n.name.startswith('WHEEL_'):
            pass
    meshes = []
    for m in k.meshes:
        p = k.path_of(m.node)
        if 'WHEEL_' in p:
            tyre_bottom.append(m.pos[:, 1].min()); continue
        if any(s in (m.name + p).lower() for s in SKIP) or 'COCKPIT' in p: continue
        meshes.append(m)
    zf = (W['LF'][2] + W['RF'][2]) / 2; zr = (W['LR'][2] + W['RR'][2]) / 2
    z0 = {'front': zf, 'rear': zr, 'mid': (zf + zr) / 2}[align]
    g = min(tyre_bottom) if tyre_bottom else 0
    off = np.array([0, g, z0])
    return [(m.pos - off, m.idx) for m in meshes], dict(wheelbase=zf - zr, zf=zf - z0, zr=zr - z0)


def mask(parts, view, mmpx, box):
    hu, hv = VIEWS[view]
    u0, u1, v0, v1 = box; s = 1000 / mmpx
    W, H = int((u1 - u0) * s) + 1, int((v1 - v0) * s) + 1
    img = Image.new('L', (W, H), 0); d = ImageDraw.Draw(img)
    for P, I in parts:
        U = (P[:, hu] - u0) * s; V = H - (P[:, hv] - v0) * s
        for t in I:
            d.polygon([(U[t[0]], V[t[0]]), (U[t[1]], V[t[1]]), (U[t[2]], V[t[2]])], fill=255)
    return np.array(img) > 0


def outline(mk):
    e = mk & ~(np.roll(mk, 1, 0) & np.roll(mk, -1, 0) & np.roll(mk, 1, 1) & np.roll(mk, -1, 1))
    ys, xs = np.nonzero(e); return np.stack([xs, ys], 1).astype(float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('out')
    ap.add_argument('--mmpx', type=float, default=2.0); ap.add_argument('--align', default='front')
    a = ap.parse_args()
    A, ia = load(a.a, a.align); B, ib = load(a.b, a.align)
    print('wheelbase A/B mm', round(ia['wheelbase'] * 1000), round(ib['wheelbase'] * 1000))
    allp = np.concatenate([P for P, _ in A + B])
    lo, hi = allp.min(0) - 0.05, allp.max(0) + 0.05
    for view, (hu, hv) in VIEWS.items():
        box = (lo[hu], hi[hu], lo[hv], hi[hv])
        ma, mb = mask(A, view, a.mmpx, box), mask(B, view, a.mmpx, box)
        # ride height and tyre size are not shape: find the shift of B (+-80 mm) that best overlaps A
        best = (-1, 0, 0); r = int(80 / a.mmpx); st = max(1, int(4 / a.mmpx))
        for dv in range(-r, r + 1, st):
            for du in ([0] if view == 'top' else range(-r // 2, r // 2 + 1, st)):
                sh = np.roll(np.roll(mb, dv, 0), du, 1)
                v = (ma & sh).sum() / max((ma | sh).sum(), 1)
                if v > best[0]: best = (v, du, dv)
        mb = np.roll(np.roll(mb, best[2], 0), best[1], 1)
        print(f'      B shifted u {best[1] * a.mmpx:+.0f} mm, v {-best[2] * a.mmpx:+.0f} mm to best fit')
        iou = (ma & mb).sum() / max((ma | mb).sum(), 1)
        oa, ob = outline(ma), outline(mb)
        sub = lambda o: o[np.random.default_rng(0).choice(len(o), min(4000, len(o)), replace=False)]
        dab = nearest_dist(np.c_[sub(oa), np.zeros(min(4000, len(oa)))], np.c_[ob, np.zeros(len(ob))], cell=25)
        dba = nearest_dist(np.c_[sub(ob), np.zeros(min(4000, len(ob)))], np.c_[oa, np.zeros(len(oa))], cell=25)
        dd = np.concatenate([dab, dba]) * a.mmpx; dd = dd[np.isfinite(dd)]
        print(f'{view:5s} IoU {iou:.3f}  outline distance mm: median {np.median(dd):.1f}  p95 {np.percentile(dd, 95):.1f}  max {dd.max():.0f}')
        rgb = np.full(ma.shape + (3,), 255, np.uint8)
        rgb[ma & ~mb] = (230, 60, 60); rgb[mb & ~ma] = (60, 110, 230); rgb[ma & mb] = (70, 70, 70)
        Image.fromarray(rgb).save(f'{a.out}_{view}.png')
        if view == 'side':
            pts = oa * a.mmpx; pts[:, 0] += lo[hu] * 1000; pts[:, 1] = (ma.shape[0] - pts[:, 1] / a.mmpx) * a.mmpx + lo[hv] * 1000
            np.savetxt(f'{a.out}_A_side.csv', pts, delimiter=',', fmt='%.1f', header='z_mm,y_mm (origin: axle station, centreline, ground)')


if __name__ == '__main__':
    main()
