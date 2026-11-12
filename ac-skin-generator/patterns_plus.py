"""More livery patterns (v1.10, Nik 12 Nov: "we need a lot more ... go nuts"). Layered designs in the spirit of the
hand-made Ratty Racing Lacetti skin: bands with pinstripe edges, dot fields that fade, glows and gradients.
Every pattern is a function of the car's surface in 3D (so it wraps round the car without seams) and uses only the
design's four colours: base, accent, highlight (accent2) and text. The app averages four points per texel, so the
edges come out smooth.

Coordinates: x across the car (+ = left side), y up, z forward. s = 0 at the front .. 1 at the rear; h = 0 at the sill
.. 1 at the window line (the roof is above 1). Sides are where the surface faces sideways, tops where it faces up."""
import numpy as np

NAMES = {
    'ratty_swoosh': 'Ratty swoosh (rising bands + dots)',
    'endurance_wedge': 'Endurance wedge',
    'touring_arcs': '90s touring arcs',
    'retro_bands': 'Retro triple bands',
    'kinetic_arrows': 'Kinetic arrows',
    'speed_lines': 'Speed lines',
    'shark_gills': 'Shark gills',
    'wave_flow': 'Wave flow',
    'halftone_burst': 'Halftone burst',
    'lowpoly': 'Low-poly shatter',
    'splinter_camo': 'Splinter camo',
    'dragon_scales': 'Dragon scales',
    'circuit': 'Circuit board',
    'topo': 'Topographic lines',
    'glitch': 'Digital glitch',
    'flames': 'Racing flames',
    'brushstrokes': 'Brushstrokes',
    'neon_grid': 'Neon grid',
    'carbon_lower': 'Carbon lower body',
    'fade_stripes': 'Fade stripes (lines to dots)',
    'tribal_blades': 'Tribal blades',
    'chequer_scatter': 'Chequer scatter',
    'diamond_mesh': 'Diamond mesh fade',
    'diagonal_split': 'Diagonal split + glow seam',
    'pixel_dissolve': 'Pixel dissolve',
    'starfield': 'Starfield + shooting star',
    'electric': 'Electric arcs',
    'barcode': 'Barcode rear',
    'ribbon_twist': 'Ribbon twist',
    'gt_sash': 'GT sash',
    'paint_drips': 'Paint drips',
    'tech_honeycomb': 'Tech honeycomb',
}


# ------------------------------------------------------------------ helpers
def _hash(*ints):
    h = np.zeros(np.shape(ints[0]), dtype=np.int64)
    for k, v in zip((73856093, 19349663, 83492791, 2654435761), ints):
        h = h ^ (np.asarray(v).astype(np.int64) * k)
    return (h & 0x7fffffff) % 10007 / 10007.0


def ss(e0, e1, v):
    """Smooth 0..1 between e0 and e1 (either way round)."""
    t = np.clip((v - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def line(d, w):
    """1 inside a stripe of half-width w around d = 0 (d = distance to its centre line)."""
    return (np.abs(d) < w).astype(np.float32)


def vnoise(u, v, seed=0):
    """Smooth value noise, about 1 bump per unit."""
    iu, iv = np.floor(u), np.floor(v)
    fu, fv = u - iu, v - iv
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    a, b = _hash(iu, iv, seed), _hash(iu + 1, iv, seed)
    c, d = _hash(iu, iv + 1, seed), _hash(iu + 1, iv + 1, seed)
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


def fbm(u, v, seed=0, octaves=3):
    t, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        t = t + amp * vnoise(u * 2 ** o, v * 2 ** o, seed + o * 17); tot += amp; amp *= 0.5
    return t / tot


def curve(f, u, step=0.002):
    """f(u) for a smooth 1-D function, worked out every `step` metres and looked up (much quicker on millions
    of points)."""
    lo, hi = float(u.min()), float(u.max())
    us = np.arange(lo - step, hi + 2 * step, step)
    return np.interp(u, us, f(us))


def field(f, u, v, step=0.004):
    """f(u, v) for a smooth 2-D function, worked out on a grid every `step` metres and looked up (bilinear)."""
    u0, v0 = float(u.min()) - step, float(v.min()) - step
    nu, nv = int((float(u.max()) - u0) / step) + 3, int((float(v.max()) - v0) / step) + 3
    if nu * nv > 6_000_000: return f(u, v)                # an odd shape: just work it out everywhere
    gu, gv = np.meshgrid(u0 + np.arange(nu) * step, v0 + np.arange(nv) * step, indexing='ij')
    grid = f(gu, gv)
    fu, fv = (u - u0) / step, (v - v0) / step
    iu, iv = np.clip(fu.astype(np.int64), 0, nu - 2), np.clip(fv.astype(np.int64), 0, nv - 2)
    tu, tv = fu - iu, fv - iv
    return ((grid[iu, iv] * (1 - tu) + grid[iu + 1, iv] * tu) * (1 - tv) +
            (grid[iu, iv + 1] * (1 - tu) + grid[iu + 1, iv + 1] * tu) * tv)


def dots(u, v, g, r, stagger=True):
    """1 inside the dots of a grid (spacing g, metres) whose radius is r (metres, may vary per point)."""
    row = np.floor(v / g)
    u2 = u + (row % 2) * g / 2 if stagger else u
    du = u2 - (np.floor(u2 / g) + 0.5) * g
    dv = v - (row + 0.5) * g
    return ((du * du + dv * dv) < r * r).astype(np.float32)


class Geo:
    """Where every point is on the car."""
    def __init__(self, P, N, car, sill, belt):
        self.x, self.y, self.z = P[:, 0], P[:, 1], P[:, 2]
        self.L = car.length
        self.sh = max(belt - sill, 1e-3)
        self.sill, self.belt = sill, belt
        self.s = (car.hi[2] - self.z) / self.L
        self.h = (self.y - sill) / self.sh
        self.half = (car.hi[0] - car.lo[0]) / 2
        self.ax = np.abs(self.x)
        nx, ny = np.abs(N[:, 0]), N[:, 1]
        self.side = ss(0.3, 0.55, nx)                  # 1 on the sides, 0 on the top
        self.top = ss(0.45, 0.7, ny) * (1 - self.side)
        fw = [c for w, c in car.wheels.items() if w.endswith('F')]
        rw = [c for w, c in car.wheels.items() if w.endswith('R')]
        self.fz = np.mean([c[2] for c in fw]) if fw else car.hi[2] - 0.2 * self.L
        self.rz = np.mean([c[2] for c in rw]) if rw else car.lo[2] + 0.2 * self.L
        self.wy = np.mean([c[1] for c in fw + rw]) if fw + rw else sill
        self.wr = getattr(car, 'wheel_r', 0.3)
        self.n = len(P)


class Pal:
    def __init__(self, base, acc, acc2, txt):
        f = lambda c: np.asarray(c, np.float32)
        self.base, self.acc, self.acc2, self.txt = f(base), f(acc), f(acc2), f(txt)

    def mix(self, a, b, t):
        t = np.asarray(t, np.float32)
        return a * (1 - t[..., None]) + b * t[..., None] if t.ndim else a * (1 - t) + b * t


def lay(col, a, c):
    """Put colour c (one colour or one per point) over col with coverage a (0..1 per point)."""
    a = np.clip(np.asarray(a, np.float32), 0, 1)[:, None]
    return col * (1 - a) + np.asarray(c, np.float32) * a


# ------------------------------------------------------------------ the patterns
def ratty_swoosh(g, col, p):
    """Two bands rising from the front wheel to the rear pillar, pinstripes between and above them, a dot field
    fading off the top one; over the top a centre band with pinstripes (the Lacetti look)."""
    l = 0.05 + 0.85 * g.s                                     # the main band's top edge, rising to the rear
    sd = g.side
    col = lay(col, sd * (g.h < l - 0.3) * (0.3 + 0.5 * g.s), p.acc * 0.45)                  # deep tint under the bands
    col = lay(col, sd * ((g.h < l) & (g.h > l - 0.3)), p.mix(p.acc * 0.5, p.acc, ss(0.0, 0.85, g.s)))
    col = lay(col, sd * line(g.h - (l - 0.36), 0.012), p.acc2)
    col = lay(col, sd * line(g.h - (l + 0.05), 0.018), p.acc2)
    l2 = l + 0.12                                            # a thinner second band above, from the middle back
    col = lay(col, sd * ((g.h > l2) & (g.h < l2 + 0.07)) * ss(0.3, 0.45, g.s), p.acc)
    col = lay(col, sd * line(g.h - (l2 + 0.1), 0.006) * ss(0.25, 0.4, g.s), p.acc2)
    d = (g.h - (l2 + 0.14)) * g.sh                           # metres above the stripes
    r = 0.017 * np.clip(1 - d / 0.32, 0, 1) * ss(0.95, 0.45, g.s)
    col = lay(col, sd * (d > 0) * dots(g.z, g.y, 0.034, r), p.acc)
    t = g.top                                                # over the top
    col = lay(col, t * (g.ax < 0.17), p.mix(p.acc, p.acc * 0.5, ss(0.0, 0.17, g.ax)))
    col = lay(col, t * line(g.ax - 0.205, 0.01), p.acc2)
    col = lay(col, t * line(g.ax - 0.245, 0.004), p.acc)
    return col


def endurance_wedge(g, col, p):
    """A big wedge from the nose, its edge falling to the rear, a highlight edge and a fine line; a chevron on top."""
    e = 1.05 - 1.25 * g.s
    sd = g.side
    col = lay(col, sd * (g.h < e), p.mix(p.acc, p.acc * 0.7, ss(0, 0.6, g.s)))
    col = lay(col, sd * ((g.h > e + 0.04) & (g.h < e + 0.1)), p.acc2)
    col = lay(col, sd * line(g.h - (e + 0.14), 0.008), p.txt)
    ch = g.s - (0.12 + 0.5 * g.ax / g.half)                 # chevron pointing forward
    col = lay(col, g.top * (ch < 0), p.acc)
    col = lay(col, g.top * ((ch > 0.015) & (ch < 0.04)), p.acc2)
    col = lay(col, g.top * line(ch - 0.06, 0.005), p.txt)
    return col


def touring_arcs(g, col, p):
    """Big arcs sweeping up over the rear wheel (90s touring cars), colour filling behind them."""
    cz, cy = g.rz + 0.55 * g.L, g.sill - 1.4
    r = np.sqrt((g.z - cz) ** 2 + (g.y - cy) ** 2)
    R = 2.0 + 0.0 * r
    behind = g.z < cz
    sd = g.side
    col = lay(col, sd * behind * (r > R + 0.34), p.mix(p.acc * 0.75, p.acc, ss(0.3, 0.9, g.s)))
    col = lay(col, sd * behind * ((r > R) & (r < R + 0.14)), p.acc)
    col = lay(col, sd * behind * ((r > R + 0.18) & (r < R + 0.25)), p.acc2)
    col = lay(col, sd * behind * line(r - (R + 0.29), 0.012), p.txt)
    off = g.x - 0.28 * g.half                                # over the top: three stripes off-centre
    for k, (c, w) in enumerate(((p.acc, 0.07), (p.acc2, 0.035), (p.txt, 0.012))):
        col = lay(col, g.top * line(off - (0.0 if k == 0 else 0.11 + 0.06 * (k - 1)), w), c)
    return col


def retro_bands(g, col, p):
    """Three bands along the side kicking up over the rear wheel; three stripes over the top."""
    h0 = 0.42 + 0.42 * ss(0.62, 0.95, g.s)
    sd = g.side * ss(0.02, 0.06, g.s)
    for k, (c, w) in enumerate(((p.acc, 0.07), (p.acc2, 0.045), (p.txt, 0.02))):
        c0 = h0 - k * 0.15 - (0.0 if k == 0 else 0.0)
        col = lay(col, sd * line(g.h - c0, w), c)
    for k, (c, w) in enumerate(((p.acc, 0.06), (p.acc2, 0.035), (p.txt, 0.014))):
        col = lay(col, g.top * line(g.x - (0.32 - k * 0.12) * g.half * 0 - (0.14 - k * 0.11), w), c)
    return col


def kinetic_arrows(g, col, p):
    """A row of forward-pointing arrows along the lower side, growing towards the front, and a speed line."""
    n = 8
    k = (g.s - 0.08) / 0.82
    ph = (k * n - np.abs(g.h - 0.27) * 3.2) % 1.0                 # tips forward, arms swept back
    inside = (k > 0) & (k < 1) & (np.abs(g.h - 0.27) < 0.2)
    size = 0.5 - 0.3 * np.clip(k, 0, 1)
    sd = g.side
    col = lay(col, sd * inside * (ph < size), p.mix(p.acc2, p.acc, np.clip(k, 0, 1)))
    col = lay(col, sd * line(g.h - 0.55, 0.012) * ss(0.05, 0.25, g.s), p.acc)
    col = lay(col, sd * line(g.h - 0.6, 0.005) * ss(0.25, 0.5, g.s), p.acc2)
    pa = (g.s * 9 - g.ax * 3.0) % 1.0                         # arrows down the bonnet / roof centre too
    col = lay(col, g.top * (g.ax < 0.2) * (pa < 0.28), p.acc)
    return col


def speed_lines(g, col, p):
    """Streaks of different lengths along the side, starting at random points and running to the rear."""
    sd = g.side
    for plane, v, w, m in ((sd, g.h, 0.06, 1.0), (g.top, g.x / g.half, 0.11, 1.0)):
        row = np.floor(v / w)
        a, b, c = _hash(row, 3), _hash(row, 7), _hash(row, 11)
        start = 0.08 + 0.55 * a
        thick = w * (0.12 + 0.22 * b)
        frac = v - (row + 0.5) * w
        on = (g.s > start) & (np.abs(frac) < thick) & (c > 0.25)
        dash = ((g.s * 26 + a * 7) % 1.0) < (0.95 - 0.6 * ss(0.65, 1.0, g.s))
        colr = np.where((c > 0.62)[:, None], p.acc2, p.acc)
        col = lay(col, plane * on * dash * ss(start, start + 0.12, g.s), colr)
    return col


def shark_gills(g, col, p):
    """Big slanted slashes behind the front wheel, getting shorter, highlight edges, a streak running back."""
    u = (g.fz - g.z) - 0.5 * (g.y - g.wy)
    sd = g.side
    for i in range(5):
        u0 = g.wr + 0.12 + i * 0.15
        w = 0.085 - 0.008 * i
        m = (g.h > 0.12 + 0.03 * i) & (g.h < 0.98 - 0.11 * i)
        col = lay(col, sd * m * ((u > u0) & (u < u0 + w)), p.mix(p.acc, p.acc * 0.6, np.full(g.n, i / 5)))
        col = lay(col, sd * m * ((u > u0 + w + 0.008) & (u < u0 + w + 0.022)), p.acc2)
    end = g.wr + 0.12 + 5 * 0.15
    streak = (u > end) & (np.abs(g.h - 0.42) < 0.06 * ss(1.0, 0.0, (u - end) / 2.2))
    col = lay(col, sd * streak, p.acc)
    col = lay(col, g.top * (line(g.ax - 0.12, 0.03) + line(g.ax - 0.18, 0.01)), p.acc)
    return col


def wave_flow(g, col, p):
    """Two flowing waves along the side over a tinted lower body; waves across the top."""
    ph = 2 * np.pi * g.s
    w1 = 0.55 + 0.2 * np.sin(ph * 1.6 + 0.6)
    w2 = w1 - 0.2 + 0.06 * np.sin(ph * 3.1)
    sd = g.side
    col = lay(col, sd * (g.h < w2), p.mix(p.acc * 0.55, p.acc * 0.85, ss(0, 1, g.s)))
    col = lay(col, sd * ((g.h > w2 + 0.03) & (g.h < w1)), p.acc)
    col = lay(col, sd * line(g.h - (w1 + 0.04), 0.014), p.acc2)
    col = lay(col, sd * line(g.h - (w2 + 0.015), 0.006), p.txt)
    off = 0.35 * g.half * np.sin(ph * 1.4)
    col = lay(col, g.top * line(g.x - off, 0.11), p.acc)
    col = lay(col, g.top * line(g.x - off - 0.15, 0.015), p.acc2)
    return col


def halftone_burst(g, col, p):
    """Dots bursting out from the door (where the number sits), big in the middle; rings around it."""
    cz, cy = (g.fz + g.rz) / 2 - 0.05 * g.L, g.sill + 0.55 * g.sh
    d = np.sqrt((g.z - cz) ** 2 + (g.y - cy) ** 2)
    r = 0.019 * np.clip(1 - d / 1.7, 0, 1) ** 0.7
    sd = g.side
    col = lay(col, sd * (d > 0.42) * dots(g.z, g.y, 0.04, r), p.mix(p.acc2, p.acc, ss(0.4, 1.2, d)))
    col = lay(col, sd * line(d - 0.36, 0.014), p.acc)
    col = lay(col, sd * line(d - 0.4, 0.005), p.acc2)
    bz = g.L * 0.0 + (g.z - (g.fz - 0.15))                     # the bonnet: dots fanning back from the nose
    dt = np.sqrt(bz ** 2 + g.x ** 2)
    col = lay(col, g.top * dots(g.z, g.x, 0.045, 0.02 * np.clip(1 - dt / 1.6, 0, 1)), p.acc)
    return col


def lowpoly(g, col, p):
    """Faceted triangles, each its own shade, base at the front going to accent at the rear."""
    cs = 0.3
    for plane, u, v in ((g.side, g.z, g.y), (g.top, g.z, g.x)):
        iu, iv = np.floor(u / cs), np.floor(v / cs)
        fu, fv = u / cs - iu, v / cs - iv
        tri = (fu + fv > 1).astype(np.int64)
        h = _hash(iu, iv, tri, 5)
        k = np.clip(g.s * 1.15 - 0.1 + (h - 0.5) * 0.35, 0, 1)
        c = p.mix(p.base, p.acc, k) * (0.8 + 0.4 * h)[:, None]
        c = np.where((h > 0.93)[:, None], p.acc2, c)
        col = lay(col, plane, c)
    return col


def splinter_camo(g, col, p):
    """Sharp splinter camouflage in three tones."""
    for plane, u0, v0 in ((g.side, g.z, g.y), (g.top, g.z, g.x)):
        for k, (ang, cw, ch, thr, c) in enumerate(((0.5, 0.42, 0.2, 0.5, p.acc * 0.6 + p.base * 0.4),
                                                    (-0.35, 0.36, 0.16, 0.6, p.acc),
                                                    (0.9, 0.3, 0.12, 0.8, p.acc2))):
            u = u0 * np.cos(ang) + v0 * np.sin(ang)
            v = -u0 * np.sin(ang) + v0 * np.cos(ang)
            iu = np.floor(u / cw); fv = v / ch + (_hash(iu, k) - 0.5) * 2.0 + u / cw * 0.6
            iv = np.floor(fv)
            col = lay(col, plane * (_hash(iu, iv, k + 9) > thr), c)
    return col


def dragon_scales(g, col, p):
    """Overlapping scales growing in from the rear, outlined in the highlight colour."""
    gs = 0.085
    for plane, u, v in ((g.side, g.z, g.y), (g.top, g.z, g.x)):
        row = np.floor(v / gs)
        uu = u + (row % 2) * gs / 2
        col_i = np.floor(uu / gs)
        du = uu - (col_i + 0.5) * gs
        dv = v - (row + 1.0) * gs                                # centre on the row's top edge: scales hang down
        d = np.sqrt(du * du + dv * dv)
        show = _hash(col_i, row, 4) < ss(0.25, 0.75, g.s) * 1.2
        inside = (d < gs * 0.62) & show
        shade = np.clip(1 - (-dv) / gs, 0.35, 1)
        col = lay(col, plane * inside, p.acc * shade[:, None] * 0.9)
        col = lay(col, plane * show * line(d - gs * 0.6, 0.004), p.acc2)
    return col


def circuit(g, col, p):
    """Circuit-board traces: runs along the car with jogs, pads at their ends, over a faint board tint at the rear."""
    gs = 0.1
    for plane, v in ((g.side, g.y), (g.top, g.x)):
        row = np.floor(v / gs); fv = v / gs - row - 0.5
        cell = np.floor(g.z / gs); fu = g.z / gs - cell - 0.5
        start = 0.2 + 0.6 * _hash(row, 1)                     # each run starts somewhere and runs to the rear
        run = (_hash(row, 2) < 0.6) & (g.s > start) & (_hash(cell, row, 3) > 0.12)
        tw = 0.09
        col = lay(col, plane * ss(0.25, 0.9, g.s) * 0.25, p.acc * 0.5)
        col = lay(col, plane * run * (np.abs(fv) < tw), p.acc2)
        jog = run & (_hash(cell, row, 4) < 0.18) & (np.abs(fu) < tw) & (fv > 0)      # up to the next row
        col = lay(col, plane * jog, p.acc2)
        s_cell = 1 - (cell * gs - (g.z.min() if False else 0)) * 0          # (pads where a run starts)
        first = run & (np.abs(g.s - start) < gs / g.L * 0.6)
        r2 = fu * fu + fv * fv
        col = lay(col, plane * (_hash(row, 2) < 0.6) * (np.abs(g.s - start) * g.L < 0.06) * (np.abs(fv) < 0.35), p.acc)
        pad = (_hash(cell, row, 5) < 0.06) & run & (r2 < 0.12)
        col = lay(col, plane * pad, p.acc)
        col = lay(col, plane * pad * (r2 < 0.03), p.base)
    return col


def topo(g, col, p):
    """Contour lines of a rolling landscape, every fourth line in the highlight colour."""
    for plane, u, v in ((g.side, g.z, g.y), (g.top, g.z, g.x)):
        sel = plane > 0
        f = np.zeros(g.n)
        if sel.any(): f[sel] = field(lambda a, b: fbm(a * 1.3 + 3.0, b * 1.3, 2), u[sel], v[sel]) * 9
        fr = f - np.floor(f)
        on = np.abs(fr - 0.5) > 0.42
        major = (np.floor(f) % 4) == 0
        col = lay(col, plane * 0.18 * (np.floor(f) / 9), p.acc)
        col = lay(col, plane * on * ~major, p.acc)
        col = lay(col, plane * on * major, p.acc2)
    return col


def glitch(g, col, p):
    """Blocks shifted sideways with colour-split edges over the rear half, scanlines."""
    for plane, v, w in ((g.side, g.h, 0.075), (g.top, g.x / g.half, 0.12)):
        row = np.floor(v / w)
        a, b = _hash(row, 21), _hash(row, 22)
        s0 = 0.35 + 0.45 * a
        on = (g.s > s0) & (b > 0.3)
        c = np.where((b > 0.75)[:, None], p.acc2, np.where((b > 0.55)[:, None], p.txt, p.acc))
        col = lay(col, plane * on, c)
        col = lay(col, plane * ((g.s > s0 - 0.03) & (g.s < s0 - 0.015)) * (b > 0.3), p.acc2)
        col = lay(col, plane * ((g.s > s0 - 0.055) & (g.s < s0 - 0.045)) * (b > 0.3), p.acc * 0.6)
        scan = ((g.y if plane is g.side else g.x) / 0.018 % 1.0) < 0.35
        col = lay(col, plane * on * scan * 0.25, p.base)
    return col


def flames(g, col, p):
    """Hot-rod flames licking back from the nose, highlight-coloured at the root, outlined in the text colour."""
    for plane, v, span in ((g.side, g.h, 3.2), (g.top, g.ax / g.half, 2.2)):
        t = (v * span) % 1.0
        tongue = (1 - np.abs(t * 2 - 1)) ** 1.6
        wob = 0.03 * np.sin(v * 23)
        edge = 0.16 + 0.32 * tongue + wob
        if plane is g.side: edge = edge * ((g.h > 0.05) & (g.h < 1.0))
        inside = g.s < edge
        col = lay(col, plane * inside, p.mix(p.acc2, p.acc, ss(0.0, 0.35, g.s / np.maximum(edge, 1e-3) * 0.35)))
        col = lay(col, plane * ((g.s >= edge) & (g.s < edge + 0.012)), p.txt)
    return col


def brushstrokes(g, col, p):
    """Three broad painted strokes with rough edges and bristle streaks."""
    sd = g.side
    for k, (a, b, w, c) in enumerate(((0.25, 0.45, 0.13, p.acc), (0.62, -0.25, 0.08, p.acc2), (0.85, -0.5, 0.04, p.txt))):
        cen = a + b * g.s + 0.04 * np.sin(g.s * 9 + k)
        rough = (vnoise(g.z * 9, k * 3.0, 40 + k) - 0.5) * 0.06
        dv = g.h - cen
        inside = (np.abs(dv) < w + rough) & (g.s > 0.05 + 0.1 * k) & (g.s < 0.95 - 0.05 * k)
        streak = 0.82 + 0.18 * np.sin(dv / w * 18 + _hash(np.floor(dv / w * 6), k) * 6)
        col = lay(col, sd * inside, c * streak[:, None])
    d = g.x - (g.s - 0.5) * g.half * 0.9                         # one stroke diagonally over the top
    rough = (vnoise(g.z * 8, 1.7, 50) - 0.5) * 0.08
    col = lay(col, g.top * (np.abs(d) < 0.16 + rough), p.acc * (0.85 + 0.15 * np.sin(d * 60))[:, None])
    return col


def neon_grid(g, col, p):
    """A glowing perspective grid on the lower half, lines closer together towards the sill, a bright horizon."""
    sd = g.side * (g.h > 0.0)
    hz = 0.55
    k = np.clip((hz - g.h) / hz, 0, 1)
    rows = (np.sqrt(k) * 6) % 1.0
    below = g.h < hz
    zc = (g.fz + g.rz) / 2
    u = (g.z - zc) / (0.15 + k * 1.2)                        # lines fan out from a point on the horizon
    lines_v = (np.abs(u / 0.22 - np.round(u / 0.22)) < 0.05 * (0.4 + k)) & below
    lines_h = (rows < 0.1) & below & (k > 0.03)
    col = lay(col, sd * below * 0.45 * k, p.acc * 0.35)
    col = lay(col, sd * (lines_h | lines_v), p.acc)
    col = lay(col, sd * ss(hz + 0.15, hz, g.h) * (g.h > hz) * 0.6, p.acc2)
    col = lay(col, sd * line(g.h - hz, 0.012), p.acc2)
    col = lay(col, g.top * (line(g.ax - 0.15, 0.008) + line(g.ax - 0.19, 0.004)), p.acc)
    return col


def carbon_lower(g, col, p):
    """Bare carbon on the lower body and a bonnet panel, set off by a highlight edge."""
    def weave(u, v):
        t = 0.0125
        a = (np.floor(u / t) + np.floor(v / t)) % 2
        k = ((u / t) % 1.0) if True else 0
        return np.where((a > 0)[:, None], np.float32([34, 34, 37]), np.float32([22, 22, 24])) * (0.9 + 0.2 * k)[:, None]
    e = 0.3 + 0.12 * g.s
    sd = g.side
    col = lay(col, sd * (g.h < e), weave(g.z + g.y, g.z - g.y))
    col = lay(col, sd * ((g.h > e + 0.015) & (g.h < e + 0.05)), p.acc)
    col = lay(col, sd * line(g.h - (e + 0.075), 0.007), p.acc2)
    pan = (g.s < 0.28) & (g.ax < 0.4)
    col = lay(col, g.top * pan, weave(g.z + g.x, g.z - g.x))
    edge = pan & ((g.s > 0.265) | (g.ax > 0.38))
    col = lay(col, g.top * edge, p.acc)
    return col


def fade_stripes(g, col, p):
    """Diagonal stripes, solid at the front, breaking up into shrinking dots towards the rear."""
    for plane, v in ((g.side, g.y), (g.top, g.x)):
        u = g.z * 0.8 + v * 0.6
        per = 0.13
        fr = (u / per) % 1.0
        width = 0.5 * ss(0.95, 0.15, g.s)
        solid = g.s < 0.45
        col = lay(col, plane * solid * (fr < width), p.mix(p.acc2, p.acc, ss(0, 0.45, g.s)))
        # the rear: the stripes become rows of dots along their own direction
        w2 = -g.z * 0.6 + v * 0.8
        r = per * 0.5 * width
        col = lay(col, plane * ~solid * dots(w2, u, per * 0.5, r, stagger=False), p.acc)
    return col


def tribal_blades(g, col, p):
    """Sharp curved blades sweeping back from the front wheel."""
    sd = g.side
    for k in range(3):
        c = 0.25 + 0.22 * k
        t = np.clip((g.s - 0.08 - 0.06 * k) / 0.55, 0, 1)
        cen = c + 0.35 * t ** 2
        w = 0.07 * np.sin(np.pi * np.clip(t, 0, 1)) ** 0.8 * (1 - 0.25 * k)
        on = (np.abs(g.h - cen) < w) & (t > 0) & (t < 1)
        col = lay(col, sd * on, p.acc if k != 1 else p.acc2)
        col = lay(col, sd * (np.abs(np.abs(g.h - cen) - w - 0.012) < 0.004) * (t > 0.05) * (t < 0.95), p.txt)
    t = np.clip(g.s / 0.6, 0, 1)
    w = 0.08 * np.sin(np.pi * t)
    col = lay(col, g.top * (np.abs(g.ax - 0.08 - 0.3 * t) < w), p.acc)
    return col


def chequer_scatter(g, col, p):
    """A chequered band at the front whose squares break loose and scatter to the rear, getting smaller."""
    for plane, v in ((g.side, g.y), (g.top, g.x)):
        cs = 0.07 * (1 - 0.5 * ss(0.3, 1.0, g.s))
        iu, iv = np.floor(g.z / cs), np.floor(v / cs)
        chk = ((iu + iv) % 2) == 0
        keep = _hash(iu, iv, 31) > ss(0.18, 0.85, g.s) * 1.05
        band = g.s < 0.8
        col = lay(col, plane * band * keep * chk, p.acc)
        col = lay(col, plane * band * keep * ~chk * 0.35, p.acc2)
    return col


def diamond_mesh(g, col, p):
    """A diamond lattice, bold at the rear, fading to fine lines at the front, over a soft gradient."""
    for plane, v in ((g.side, g.y), (g.top, g.x)):
        u1, u2 = (g.z + v) / 0.12, (g.z - v) / 0.12
        d = np.minimum(np.abs(u1 % 1.0 - 0.5), np.abs(u2 % 1.0 - 0.5))
        w = 0.04 + 0.2 * ss(0.15, 0.95, g.s)
        col = lay(col, plane * ss(0.0, 1.0, g.s) * 0.45, p.acc * 0.6)
        col = lay(col, plane * (d > 0.5 - w), p.mix(p.acc2, p.acc, ss(0.2, 0.9, g.s)))
    return col


def diagonal_split(g, col, p):
    """Two-tone split along a steep diagonal with a glowing seam."""
    for plane, v in ((g.side, g.h * g.sh), (g.top, g.x)):
        dd = (g.s - 0.45) * g.L * 0.5 - v * 0.9
        col = lay(col, plane * (dd > 0), p.acc)
        col = lay(col, plane * np.exp(-(dd / 0.05) ** 2) * 0.8, p.acc2)
        col = lay(col, plane * line(dd + 0.09, 0.008), p.txt)
    return col


def pixel_dissolve(g, col, p):
    """Solid accent at the rear dissolving into bigger and fewer pixels towards the front."""
    for plane, v in ((g.side, g.y), (g.top, g.x)):
        for cs, thr0, c in ((0.05, 0.0, p.acc), (0.025, 0.1, p.acc2)):
            iu, iv = np.floor(g.z / cs), np.floor(v / cs)
            sc = ((g.lz_s(iu, cs) if False else g.s))
            on = _hash(iu, iv, int(cs * 1000)) < ss(0.15, 0.75, sc) - thr0
            col = lay(col, plane * on, c)
    return col


def starfield(g, col, p):
    """Stars of different sizes and a shooting star with a fading tail along the side."""
    for plane, v in ((g.side, g.y), (g.top, g.x)):
        cs = 0.09
        iu, iv = np.floor(g.z / cs), np.floor(v / cs)
        hx, hy, hs = _hash(iu, iv, 61), _hash(iu, iv, 62), _hash(iu, iv, 63)
        du = g.z - (iu + 0.2 + 0.6 * hx) * cs; dv = v - (iv + 0.2 + 0.6 * hy) * cs
        r = np.where(hs > 0.7, 0.002 + 0.008 * (hs - 0.7) / 0.3, 0)
        col = lay(col, plane * ((du * du + dv * dv) < r * r), np.where((hs > 0.93)[:, None], p.acc2, p.txt))
        col = lay(col, plane * np.exp(-(du * du + dv * dv) / (r * r * 9 + 1e-9)) * (hs > 0.9) * 0.5, p.acc)
    hc = 0.7 - 0.35 * g.s                                       # the shooting star: head near the front, tail behind
    tail = ss(0.85, 0.12, g.s) * (g.s > 0.1)
    w = 0.012 + 0.03 * ss(0.85, 0.12, g.s)
    col = lay(col, g.side * tail * (np.abs(g.h - hc) * g.sh < w), p.mix(p.acc, p.acc2, ss(0.8, 0.15, g.s)))
    col = lay(col, g.side * np.exp(-(((g.s - 0.1) * g.L) ** 2 + ((g.h - hc) * g.sh) ** 2) / 0.003), p.txt)
    return col


def electric(g, col, p):
    """Crackling electric arcs along the lower side, glowing."""
    for plane, u, v, c0 in ((g.side, g.z, g.h, 0.3), (g.top, g.z, g.ax / g.half, 0.25)):
        for k in range(3):
            path = c0 + 0.12 * k + curve(lambda q, k=k: 0.12 * (fbm(q * 2.5, np.full_like(q, k * 5.0), 70 + k) - 0.5) * 2
                                         + 0.03 * (vnoise(q * 18, np.full_like(q, float(k)), 80) - 0.5), u)
            d = np.abs(v - path)
            reach = (g.s > 0.08 + 0.1 * k) & (g.s < 0.95)
            col = lay(col, plane * reach * np.exp(-(d / 0.05) ** 2) * 0.45, p.acc)
            col = lay(col, plane * reach * (d < 0.012), p.acc2)
            col = lay(col, plane * reach * (d < 0.005), p.txt)
    return col


def barcode(g, col, p):
    """Barcode stripes across the rear third, then sharp thin bars."""
    for plane in (g.side, g.top):
        u = g.z
        bar = np.floor(u / 0.022)
        on = (_hash(bar, 91) > 0.45) & (g.s > 0.62) & (g.s < 0.97)
        if plane is g.side: on = on & (g.h > 0.25) & (g.h < 0.9)
        col = lay(col, plane * on, np.where((_hash(bar, 92) > 0.8)[:, None], p.acc2, p.acc))
        col = lay(col, plane * line(g.s - 0.6, 0.004), p.acc2)
    return col


def ribbon_twist(g, col, p):
    """Two ribbons twisting round each other along the side; where one is in front it is brighter."""
    ph = 2 * np.pi * g.s * 2.2
    c1, c2 = 0.5 + 0.22 * np.sin(ph), 0.5 - 0.22 * np.sin(ph)
    w1 = 0.05 + 0.04 * (0.5 + 0.5 * np.cos(ph)); w2 = 0.05 + 0.04 * (0.5 - 0.5 * np.cos(ph))
    front1 = np.cos(ph) > 0
    sd = g.side * ss(0.03, 0.08, g.s) * ss(0.98, 0.92, g.s)
    for first in (False, True):
        for c, w, col_, is1 in ((c1, w1, p.acc, True), (c2, w2, p.acc2, False)):
            mine = (front1 == is1) == first
            col = lay(col, sd * mine * (np.abs(g.h - c) < w), col_ * (0.75 + 0.25 * (np.cos(ph) * (1 if is1 else -1) + 1) / 2)[:, None])
    col = lay(col, g.top * line(g.x - 0.12 * np.sin(ph), 0.05), p.acc)
    col = lay(col, g.top * line(g.x + 0.12 * np.sin(ph), 0.05), p.acc2)
    return col


def gt_sash(g, col, p):
    """A wide diagonal sash from the roof down across the door, edged, like classic endurance cars."""
    for plane, v in ((g.side, g.h * g.sh), (g.top, -g.ax)):
        dd = (g.z - (g.fz + g.rz) / 2) * 0.75 + v * 0.65 - 0.25
        col = lay(col, plane * (np.abs(dd) < 0.24), p.acc)
        col = lay(col, plane * (np.abs(np.abs(dd) - 0.27) < 0.018), p.acc2)
        col = lay(col, plane * (np.abs(np.abs(dd) - 0.31) < 0.006), p.txt)
    return col


def paint_drips(g, col, p):
    """Paint poured over the top and running down the sides in drips of different lengths."""
    col = lay(col, g.top, p.acc)
    col_i = np.floor(g.z / 0.07)
    ln = 0.15 + 0.7 * _hash(col_i, 101) ** 1.5
    bot = 1.0 - ln
    du = (g.z / 0.07) % 1.0 - 0.5
    wid = 0.32 + 0.1 * _hash(col_i, 102)
    drip = (np.abs(du) < wid * np.clip((g.h - bot) / 0.08, 0.35, 1)) & (g.h > bot)
    blob = (du * 0.07) ** 2 + ((g.h - bot) * g.sh) ** 2 < (wid * 0.07) ** 2
    col = lay(col, g.side * ((g.h > 0.92) | drip | blob), p.acc)
    col = lay(col, g.side * line(g.h - 0.9, 0.008), p.acc2)
    return col


def tech_honeycomb(g, col, p):
    """Outlined hexagons with a glow; some filled, more of them towards the rear."""
    sz = 0.075
    for plane, v in ((g.side, g.y), (g.top, g.x)):
        q = (2 / 3 * g.z) / sz
        r = (-1 / 3 * g.z + np.sqrt(3) / 3 * v) / sz
        # nearest hex centre (cube rounding)
        cx, cz_ = q, r; cy = -cx - cz_
        rx, ry, rz = np.round(cx), np.round(cy), np.round(cz_)
        dx, dy, dz = np.abs(rx - cx), np.abs(ry - cy), np.abs(rz - cz_)
        fix_x = (dx > dy) & (dx > dz); fix_y = ~fix_x & (dy > dz)
        rx = np.where(fix_x, -ry - rz, rx); ry = np.where(fix_y, -rx - rz, ry); rz = np.where(~fix_x & ~fix_y, -rx - ry, rz)
        dist = np.maximum(np.maximum(np.abs(rx - cx), np.abs(ry - cy)), np.abs(rz - cz_))   # 0 centre .. 0.5 edge
        show = _hash(rx, rz, 111) < ss(0.1, 0.8, g.s)
        fill = _hash(rx, rz, 112) > 0.8
        col = lay(col, plane * show * fill * (dist < 0.42), p.acc * 0.8)
        col = lay(col, plane * show * np.exp(-((dist - 0.47) / 0.04) ** 2) * 0.5, p.acc)
        col = lay(col, plane * show * (dist > 0.455), p.acc2)
    return col


FUNCS = {k: globals()[k] for k in NAMES}


def paint(pat, col, P, N, car, sill, belt, base, acc, acc2, txt):
    """The pattern `pat` over the colours col (one per point)."""
    g = Geo(P, N, car, sill, belt)
    out = FUNCS[pat](g, np.asarray(col, np.float32), Pal(base, acc, acc2, txt))
    return np.clip(out, 0, 255)
