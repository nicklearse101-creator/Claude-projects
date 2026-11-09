"""Blind reconstruction test: how accurately can we rebuild a car body from pictures + published dimensions?

    python blind_test.py CAR_DIR OUT_DIR [--method hull|...]

1. Truth: the car's real outer skin, from its kn5. Wheels, suspension, mirrors, interior and damage meshes
   are removed, as a modeller traces the body. The skin is sliced every DZ along the car; each slice is
   rasterised and flood-filled from outside, so only what is visible from outside counts.
2. Pictures: orthographic side, top and front silhouettes made from the truth. These are ideal blueprints:
   no perspective, no blur. The builder sees ONLY these masks, in pixels, plus the published dimensions
   from specs.json. It scales the views itself (side and top by the published length, front by the
   published width), as it would with real drawings.
3. Build: a from-scratch method turns the masks into a body (`--method`).
4. Score: per slice, the distance from every point of the true outline to the built outline, in mm.
   Positive = the build is outside the truth (too fat), negative = inside. The scores are broken down by
   region, and heat-map pictures are saved.
"""
import sys, os, json, argparse, glob
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5
from section import cut

RES = 0.003      # m per pixel in each slice
DZ = 0.010       # slice spacing (m)
X0, X1 = -1.05, 1.05
SKIP = ('shadow', 'flycam', 'damage', 'dmg', 'collider', 'blur', 'driver', 'beam', 'flame', 'smoke', 'broken')
MIR = ('mirror', 'specchi', 'retro', 'spiegel', 'wing_m', 'wingm')
HERE = os.path.dirname(os.path.abspath(__file__))


def exterior(k, g=0.0, half_w=None):
    keep, mirrors = [], []
    for m in k.meshes:
        path = k.path_of(m.node); nm = (m.name + ' ' + path).lower()
        if any(s in m.name.lower() for s in MIR): mirrors.append(m); continue
        if any(s in nm for s in SKIP): continue
        if any(t in path for t in ('WHEEL_', 'SUSP_', 'DISC_', 'COCKPIT_', 'STEER_')): continue
        if m.mat and m.mat.shader == 'ksBrokenGlass': continue
        keep.append(m)
    P = np.concatenate([m.pos for m in keep]); off = np.cumsum([0] + [len(m.pos) for m in keep])
    I = np.concatenate([m.idx + o for m, o in zip(keep, off)])
    T = P[I]                                   # [ntri, 3 corners, xyz]
    # mirror housings merged into door meshes: drop triangles with ALL corners in a box around each
    # separate mirror mesh (outboard of its inner edge minus 60 mm for the arm)
    drop = np.zeros(len(I), bool)
    for m in mirrors:
        if np.abs(m.pos[:, 0]).min() < 0.3: continue      # interior rear-view mirror
        lo, hi = m.pos.min(0), m.pos.max(0); xin = np.abs(m.pos[:, 0]).min() - 0.06; sg = np.sign(m.pos[:, 0].mean())
        inb = ((T[..., 0] * sg > xin) & (T[..., 1] > lo[1] - 0.10) & (T[..., 1] < hi[1] + 0.10) &
               (T[..., 2] > lo[2] - 0.15) & (T[..., 2] < hi[2] + 0.15))
        drop |= inb.all(1)
    if half_w:
        drop |= ((np.abs(T[..., 0]) > half_w + 0.012) & (T[..., 1] - g > 0.6)).all(1)
    return P, I[~drop]


def truth_slices(P, I, g):
    """Return z stations and a stack of solid masks [nz, nx, ny] (x across, y up from ground)."""
    y0, y1 = g - 0.02, g + 1.60
    nx = int((X1 - X0) / RES); ny = int((y1 - y0) / RES)
    zs = np.arange(P[:, 2].min() + DZ / 2, P[:, 2].max(), DZ)
    stack = np.zeros((len(zs), nx, ny), bool)
    for i, z in enumerate(zs):
        segs = cut(P, I, 2, z)
        im = Image.new('L', (nx, ny), 0); d = ImageDraw.Draw(im)
        for a, b in segs:
            d.line([((a[0] - X0) / RES, (y1 - a[1]) / RES), ((b[0] - X0) / RES, (y1 - b[1]) / RES)], fill=255, width=3)
        if len(segs):   # seal the underside: engine bay / boot / wells open downwards are not visible skin
            hb = g + 0.12; xs = segs[..., 0][(segs[..., 1] > hb - 0.03) & (segs[..., 1] < hb + 0.15)]
            if len(xs):
                d.line([((xs.min() - X0) / RES, (y1 - hb) / RES), ((xs.max() - X0) / RES, (y1 - hb) / RES)], fill=255, width=3)
        a = np.array(im).T[:, ::-1] > 0      # [x, y] with y increasing upward
        # morphological closing: seal panel gaps / small openings (< ~2*CLOSE px) before flood-filling,
        # then grow the outside back so the true outer surface is kept
        sealed = dilate(a, CLOSE)
        out = flood_outside(sealed)
        stack[i] = ~dilate(out, CLOSE) | a
    return zs, stack, (y0, y1)


CLOSE = 5   # px (15 mm): closes gaps up to ~30 mm


def dilate(a, n):
    b = a.copy()
    for _ in range(n):
        c = b.copy()
        c[1:] |= b[:-1]; c[:-1] |= b[1:]; c[:, 1:] |= b[:, :-1]; c[:, :-1] |= b[:, 1:]
        b = c
    return b


def flood_outside(wall):
    im = Image.fromarray(np.where(wall, 255, 0).astype(np.uint8)).copy()   # fromarray images are read-only views
    ImageDraw.floodfill(im, (0, 0), 128)
    return np.array(im) == 128


def pictures(stack):
    side = stack.any(axis=1)      # [z, y]
    top = stack.any(axis=2)       # [z, x]
    front = stack.any(axis=0)     # [x, y]
    return side, top, front


def bbox(mask, axis):
    idx = np.where(mask.any(axis=axis))[0]; return idx[0], idx[-1] + 1


def build_hull(side, top, front, spec, zs, ylim):
    """Visual hull from the 3 views, each scaled from its own pixels by the published dimensions.
    Returns a function that gives the built solid [nx, ny] for a truth station z."""
    y0, y1 = ylim
    # side + top: scale from the published length (pixel length of the side mask -> spec length)
    z_a, z_b = bbox(side, 1); px_len = (z_b - z_a)
    k_side = spec['length'] / 1000 / (px_len * DZ)            # builder's metres per truth metre along z
    zc_truth = zs[z_a] + (px_len * DZ) / 2                      # builder centres the car on its mid-length
    # front: scale from the published width
    x_a, x_b = bbox(front, 1); k_front = spec['width'] / 1000 / ((x_b - x_a) * RES)
    xc = X0 + (x_a + x_b) / 2 * RES

    def solid(z):
        # where does this truth station land in each (mis)scaled view? builder coords -> mask indices
        zb = (z - zc_truth) * k_side                      # builder's z (m from mid-length)
        # sample side view at builder z: builder frame shares scale k_side for z and y
        zi = int(round(((zb / k_side) + zc_truth - zs[0]) / DZ))  # identity for the side view itself
        if zi < 0 or zi >= len(side): return np.zeros(front.shape, bool)
        nx, ny = front.shape
        yy = np.arange(ny) * RES                           # truth y above y0
        # side view was drawn at true scale, the builder rescales it by k_side about the ground;
        # a built point at height h comes from side pixel h / k_side
        yi_side = np.clip(np.round(yy / k_side / RES).astype(int), 0, ny - 1)
        col = side[zi][yi_side]                            # [ny]
        xx = X0 + np.arange(nx) * RES
        xi_top = np.clip(np.round(((xx - xc) / k_side + xc - X0) / RES).astype(int), 0, nx - 1)
        row = top[zi][xi_top]                              # [nx]
        xi_f = np.clip(np.round(((xx - xc) / k_front + xc - X0) / RES).astype(int), 0, nx - 1)
        yi_f = np.clip(np.round(yy / k_front / RES).astype(int), 0, ny - 1)
        fr = front[np.ix_(xi_f, yi_f)]
        return row[:, None] & col[None, :] & fr
    # truth station z maps to built station z' = zc + (z - zc) * k_side: compare like with like by
    # evaluating the built body at the same physical z
    def solid_at(z):
        return solid(zc_truth + (z - zc_truth) / k_side)
    return solid_at, dict(k_side=k_side, k_front=k_front)


def outline(a):
    inner = a.copy()
    inner[1:-1, 1:-1] = a[1:-1, 1:-1] & a[:-2, 1:-1] & a[2:, 1:-1] & a[1:-1, :-2] & a[1:-1, 2:]
    return np.argwhere(a & ~inner)


def score(zs, stack, built_fn, ylim):
    rows = []   # z, x, y, signed distance (m)
    for i, z in enumerate(zs):
        t = stack[i]; b = built_fn(z)
        ot = outline(t)
        if not len(ot): continue
        ob = outline(b)
        if not len(ob):
            d = np.full(len(ot), np.nan)
        else:
            d = np.empty(len(ot))
            for s in range(0, len(ot), 2000):
                q = ot[s:s + 2000]
                dd = ((q[:, None, :] - ob[None, :, :]) ** 2).sum(-1)
                d[s:s + 2000] = np.sqrt(dd.min(1)) * RES
            inside = b[ot[:, 0], ot[:, 1]]
            d = np.where(inside, d, -d)      # truth outline inside the build -> build too fat (+)
        x = X0 + ot[:, 0] * RES; y = ot[:, 1] * RES + (ylim[0])
        rows.append(np.c_[np.full(len(ot), z), x, y, d])
    return np.concatenate(rows)


def region_report(R, g, wheels):
    z, x, y, d = R.T; h = y - g; ad = np.abs(d) * 1000
    zf, zr = wheels
    reg = {
        'all': np.ones_like(z, bool),
        'front (ahead of front axle)': z > zf,
        'rear (behind rear axle)': z < zr,
        'middle (between axles)': (z <= zf) & (z >= zr),
        'low (< 0.35 m)': h < 0.35,
        'waist (0.35-0.85 m)': (h >= 0.35) & (h < 0.85),
        'upper (> 0.85 m, glasshouse/roof)': h >= 0.85,
    }
    out = {}
    for k, m in reg.items():
        v = ad[m & np.isfinite(ad)]
        if len(v): out[k] = dict(n=int(len(v)), median_mm=round(float(np.median(v)), 1),
                                 p90_mm=round(float(np.percentile(v, 90)), 1),
                                 within_10mm_pct=round(float(np.mean(v <= 10) * 100), 1),
                                 bias_mm=round(float(np.median(d[m & np.isfinite(d)] * 1000)), 1))
    return out


def heatmaps(R, path, title):
    """Side view (z,y) and top view (z,x): worst |error| per pixel, green 0 -> red 40 mm."""
    z, x, y, d = R.T; ad = np.clip(np.abs(np.nan_to_num(d, nan=0.1)) * 1000, 0, 40) / 40
    s = 0.006
    def img(u, v, w):
        iu = ((u - u.min()) / s).astype(int); iv = ((v.max() - v) / s).astype(int)
        A = np.full((iu.max() + 1, iv.max() + 1), -1.0)
        np.maximum.at(A, (iu, iv), w)
        rgb = np.full(A.shape + (3,), 255, np.uint8)
        m = A >= 0
        rgb[m, 0] = (255 * np.clip(2 * A[m], 0, 1)).astype(np.uint8)
        rgb[m, 1] = (255 * np.clip(2 - 2 * A[m], 0, 1)).astype(np.uint8)
        rgb[m, 2] = 40
        return Image.fromarray(rgb.transpose(1, 0, 2)[:, ::-1])  # front of car on the left
    a = img(z, y, ad); b = img(z, x, ad)
    W = max(a.width, b.width); canvas = Image.new('RGB', (W + 40, a.height + b.height + 110), 'white')
    dr = ImageDraw.Draw(canvas)
    dr.text((20, 10), title, fill='black'); dr.text((20, 28), 'worst error per point seen from the side (top) and from above (bottom): green 0 mm -> yellow 20 -> red 40+ mm', fill='black')
    canvas.paste(a, (20, 55)); canvas.paste(b, (20, 75 + a.height))
    canvas.save(path)


def setup(car_dir, out, save=False):
    """Truth slices, pictures, traced lines and arches for one car (truth cached in OUT)."""
    os.makedirs(out, exist_ok=True)
    car = os.path.basename(os.path.normpath(car_dir))
    meas = {r['car']: r for r in json.load(open(os.path.join(HERE, 'results', 'measures.json')))}[car]
    kn5 = sorted(glob.glob(os.path.join(car_dir, '*.kn5')), key=os.path.getsize, reverse=True)[0]
    k = KN5(kn5, load_textures=False)
    W = {n.name[-2:]: n.world[3, :3] for n in k.nodes if n.name in ('WHEEL_LF', 'WHEEL_RF', 'WHEEL_LR', 'WHEEL_RR')}
    g = min(m.pos[:, 1].min() for m in k.meshes if 'WHEEL_LF' in k.path_of(m.node) and 'blur' not in m.name.lower())
    cache = os.path.join(out, f'{car}_truth.npz')
    if os.path.exists(cache):
        c = np.load(cache); zs, stack, ylim = c['zs'], c['stack'], tuple(c['ylim'])
    else:
        P, I = exterior(k, g, meas['width'] / 2000)
        zs, stack, ylim = truth_slices(P, I, g); np.savez_compressed(cache, zs=zs, stack=stack, ylim=ylim)
    side, top, front = pictures(stack)
    # the builder gets the true car's overall sizes (here the truth silhouettes), so the score is the
    # method's error only; published-vs-model differences are measured separately (compare_specs.py)
    z_a, z_b = bbox(side, 1); x_a, x_b = bbox(front, 1)
    spec = dict(length=(z_b - z_a) * DZ * 1000, width=(x_b - x_a) * RES * 1000)
    if save:
        for nm, m in (('side', side.T[::-1]), ('top', top.T), ('front', front.T[::-1])):
            Image.fromarray((~m * 255).astype(np.uint8)).save(os.path.join(out, f'{car}_picture_{nm}.png'))
    # wheel arches: a modeller traces the arch lip from the side photo; the wells behind it are hidden.
    arches = []
    for ax in ('F', 'R'):
        c = (W['L' + ax] + W['R' + ax]) / 2
        r = meas[f'tyre_d_{ax.lower()}'] / 2000 + max(meas.get(f'arch_gap_{ax.lower()}', 30), 0) / 1000
        arches.append((c[2], c[1], r))
    # traced feature lines (as drawn inside a blueprint's top view): plan outline of the body above the
    # beltline and above the roof rail -> top silhouettes of the truth above those heights
    yy0 = ylim[0] + np.arange(stack.shape[2]) * RES
    roof = yy0[stack.any((0, 1))].max()
    lines = {}
    for nm, h in (('belt', g + meas.get('belt_h', 800) / 1000), ('roofrail', roof - 0.08)):
        lines[nm] = (h, stack[:, :, yy0 >= h].any(axis=2))
    ctx = dict(side=side, top=top, front=front, spec=spec, zs=zs, ylim=ylim, RES=RES, DZ=DZ, X0=X0,
               arches=arches, ground=g, car=car, lines=lines, meas=meas, stack=stack, W=W)
    return ctx


def run(car_dir, out, method='hull', save=True):
    ctx = setup(car_dir, out, save)
    side, top, front, spec, zs, ylim = (ctx[k] for k in ('side', 'top', 'front', 'spec', 'zs', 'ylim'))
    arches, g, car, meas, stack, W = (ctx[k] for k in ('arches', 'ground', 'car', 'meas', 'stack', 'W'))
    if method == 'hull':
        fn, info = build_hull(side, top, front, spec, zs, ylim)
    else:
        import importlib; mod = importlib.import_module(method)
        fn, info = mod.build(ctx)
    info['arches'] = [[round(v, 3) for v in a] for a in arches]
    nx, ny = front.shape; yy = ylim[0] + np.arange(ny) * RES; xx = X0 + np.arange(nx) * RES
    tin = meas['track_f'] / 2000 - 0.13          # inner face of the tyre: the arch cut stops here
    fn0 = fn
    def fn(z):
        s = fn0(z).copy()
        for zc, yc, r in arches:
            if abs(z - zc) < r:
                s[np.ix_(np.abs(xx) > tin, (yy - yc) ** 2 + (z - zc) ** 2 < r ** 2)] = False
        return s
    R = score(zs, stack, fn, ylim)
    keep = np.ones(len(R), bool)     # score the outer skin only: not the wells behind the arch openings
    for zc, yc, r in arches:
        keep &= ((R[:, 0] - zc) ** 2 + (R[:, 2] - yc) ** 2 > (r - 0.005) ** 2) | (np.abs(R[:, 1]) < tin)
    keep &= R[:, 2] - g > 0.10       # the underside (floor, exhaust, sump) is not in any photo
    # wells and underbody inboard of the tyres, low down, are hidden in every photo (not the end faces)
    zlo, zhi = zs[stack.any((1, 2))][[0, -1]]
    keep &= ~((R[:, 2] - g < 0.35) & (np.abs(R[:, 1]) < tin) & (R[:, 0] > zlo + 0.25) & (R[:, 0] < zhi - 0.25))
    R = R[keep]
    rep = dict(car=car, method=method, info=info,
               regions=region_report(R, g, ((W['LF'][2] + W['RF'][2]) / 2, (W['LR'][2] + W['RR'][2]) / 2)))
    if save:
        np.save(os.path.join(out, f'{car}_{method}_errors.npy'), R)
        json.dump(rep, open(os.path.join(out, f'{car}_{method}_report.json'), 'w'), indent=1)
        heatmaps(R, os.path.join(out, f'{car}_{method}_heat.png'), f'{car}: method {method}')
    return dict(zs=zs, stack=stack, fn=fn, R=R, rep=rep, ctx=ctx)


def short(rep):
    return chr(10).join(f"{k:36s} median {v['median_mm']:6.1f}  p90 {v['p90_mm']:6.1f}  <=10mm {v['within_10mm_pct']:5.1f}%  bias {v['bias_mm']:+.1f}"
                     for k, v in rep['regions'].items())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('car'); ap.add_argument('out'); ap.add_argument('--method', default='hull')
    a = ap.parse_args()
    r = run(a.car, a.out, a.method)
    print(short(r['rep']))


if __name__ == '__main__':
    main()
