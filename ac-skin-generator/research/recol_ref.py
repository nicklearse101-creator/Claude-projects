"""Interior recolour methods (numpy + Pillow only) - research prototypes.
All images float32 sRGB 0..1, shape (H, W, 3)."""
import numpy as np
from PIL import Image, ImageFilter

# ---------------------------------------------------------------- colour spaces
def to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
               [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
               [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
M2i = np.array([[1, 0.3963377774, 0.2158037573],
                [1, -0.1055613458, -0.0638541728],
                [1, -0.0894841775, -1.2914855480]], np.float32)
M1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                [-1.2684380046, 2.6097574011, -0.3413193965],
                [-0.0041960863, -0.7034186147, 1.7076147010]], np.float32)

def srgb_to_oklab(c):
    lms = to_lin(c) @ M1.T
    return np.cbrt(lms) @ M2.T

def oklab_to_srgb(lab):
    lms = (lab @ M2i.T) ** 3
    return to_srgb(lms @ M1i.T)

def oklab_to_lin(lab):
    return ((lab @ M2i.T) ** 3) @ M1i.T

def gamut_clip(lab):
    """Keep L and hue, reduce chroma until the colour fits in sRGB (bisection, 12 steps)."""
    lin = oklab_to_lin(lab)
    bad = ((lin < -1e-4) | (lin > 1 + 1e-4)).any(-1)
    if not bad.any(): return lab
    L = lab[..., :1]; ab = lab[..., 1:]
    lo = np.zeros(bad.shape, np.float32); hi = np.ones(bad.shape, np.float32)
    for _ in range(12):
        mid = (lo + hi) / 2
        t = np.concatenate([L, ab * mid[..., None]], -1)
        l2 = oklab_to_lin(t)
        ok = ~(((l2 < -1e-4) | (l2 > 1 + 1e-4)).any(-1))
        lo = np.where(ok, mid, lo); hi = np.where(ok, hi, mid)
    s = np.where(bad, lo, 1.0)
    return np.concatenate([np.clip(L, 0, 1), ab * s[..., None]], -1)

def lum709(c):  # on sRGB-encoded values (what GIMP/PS-style tools do)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]

# ---------------------------------------------------------------- HSL helpers (GIMP)
def hsl_to_rgb(h, s, l):
    q = np.where(l < 0.5, l * (1 + s), l + s - l * s); p = 2 * l - q
    def f(t):
        t = t % 1.0
        return np.where(t < 1/6, p + (q - p) * 6 * t, np.where(t < 1/2, q, np.where(t < 2/3, p + (q - p) * (2/3 - t) * 6, p)))
    return np.stack([f(h + 1/3), f(h), f(h - 1/3)], -1)

def rgb_to_hsl(c):
    mx, mn = c.max(-1), c.min(-1); l = (mx + mn) / 2; d = mx - mn
    s = np.where(d < 1e-6, 0, d / np.maximum(1 - np.abs(2 * l - 1), 1e-6))
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    h = np.where(mx == r, ((g - b) / np.maximum(d, 1e-6)) % 6, np.where(mx == g, (b - r) / np.maximum(d, 1e-6) + 2, (r - g) / np.maximum(d, 1e-6) + 4)) / 6
    return np.where(d < 1e-6, 0, h), s, l

# ---------------------------------------------------------------- methods
def m_hsv_hue(src, T, mask=None):
    """Naive hue shift: keep V, take target hue and saturation (fails on grey/black sources)."""
    mx = src.max(-1); mn = src.min(-1)
    th, ts, tl = rgb_to_hsl(T[None, None])
    tmx, tmn = T.max(), T.min(); tsv = 0 if tmx < 1e-6 else (tmx - tmn) / tmx
    s_src = np.where(mx < 1e-6, 0, (mx - mn) / np.maximum(mx, 1e-6))
    # hue rotate: rebuild from HSV with target hue, source sat & value
    h = th[0, 0]; s = s_src; v = mx
    i = np.floor(h * 6); f = h * 6 - i; p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s)
    i = int(i) % 6
    return np.stack([[v, q, p, p, t, v][i], [t, v, v, q, p, p][i], [p, p, t, v, v, q][i]], -1)

def m_gimp_colorize(src, T, mask=None, lightness=0.0):
    th, ts, tl = rgb_to_hsl(T[None, None])
    lum = lum709(src)
    if lightness > 0: lum = lum * (1 - lightness) + lightness
    elif lightness < 0: lum = lum * (1 + lightness)
    return hsl_to_rgb(th[0, 0], ts[0, 0], lum)

def _setlum(c, l):
    d = l - (0.3 * c[..., 0] + 0.59 * c[..., 1] + 0.11 * c[..., 2]); c = c + d[..., None]
    L = (0.3 * c[..., 0] + 0.59 * c[..., 1] + 0.11 * c[..., 2])[..., None]
    n = c.min(-1, keepdims=True); x = c.max(-1, keepdims=True)
    c = np.where(n < 0, L + (c - L) * L / np.maximum(L - n, 1e-6), c)
    c = np.where(x > 1, L + (c - L) * (1 - L) / np.maximum(x - L, 1e-6), c)
    return c

def m_w3c_color(src, T, mask=None):
    """W3C/Photoshop 'Color' blend: target hue+chroma, source luminosity."""
    Tb = np.broadcast_to(T, src.shape)
    return _setlum(Tb.copy(), 0.3 * src[..., 0] + 0.59 * src[..., 1] + 0.11 * src[..., 2])

def m_multiply(src, T, mask=None):
    return src * T

def ref_stats(src, mask):
    lab = srgb_to_oklab(src)
    sel = lab[mask] if mask is not None else lab.reshape(-1, 3)
    return lab, np.median(sel, 0)

def m_ratio_linear(src, T, mask=None, roll=True):
    """Shading ratio in linear light: out = T * Y/Yref (Yref = median); screen-like roll-off above 1."""
    lin = to_lin(src); Y = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    Yref = np.median(Y[mask] if mask is not None else Y)
    S = Y / max(Yref, 1e-4)
    Tl = to_lin(T)
    out = Tl * np.minimum(S, 1)[..., None]
    if roll:
        hi = np.clip(S - 1, 0, None)[..., None]
        out = out + (1 - out) * (1 - np.exp(-hi * Tl.max() * 1.0))  # smooth into white instead of clipping
    return to_srgb(out)

def m_oklab_mult(src, T, mask=None):
    """OKLab: L_out = L_t * L/L_ref (same contrast RATIO), chroma from target + source chroma deviations."""
    lab, ref = ref_stats(src, mask); t = srgb_to_oklab(T)
    out = np.empty_like(lab)
    out[..., 0] = t[0] * lab[..., 0] / max(ref[0], 1e-3)
    out[..., 1:] = t[1:] * (lab[..., :1] / max(ref[0], 1e-3)) + (lab[..., 1:] - ref[1:])
    return oklab_to_srgb(gamut_clip(out))

def m_oklab_add(src, T, mask=None, gain=1.0):
    """OKLab: L_out = L_t + gain*(L - L_ref) (same perceptual contrast AMOUNT); chroma scaled with lightness."""
    lab, ref = ref_stats(src, mask); t = srgb_to_oklab(T)
    out = np.empty_like(lab)
    dL = lab[..., 0] - ref[0]
    out[..., 0] = t[0] + gain * dL
    # soft limits so deep shadows/highlights do not clip flat
    out[..., 0] = softclip(out[..., 0], 0.0, 1.0)
    k = np.clip(out[..., 0] / max(t[0], 1e-3), 0, 1.5)[..., None]   # chroma follows lightness (darker = less chroma)
    out[..., 1:] = t[1:] * k + (lab[..., 1:] - ref[1:])
    return oklab_to_srgb(gamut_clip(out))

def softclip(x, lo, hi, knee=0.08):
    """Linear in the middle, smooth (tanh) shoulder within `knee` of each limit."""
    y = x.copy()
    a = lo + knee; b = hi - knee
    y = np.where(x < a, a - knee * np.tanh((a - x) / knee), y)
    y = np.where(x > b, b + knee * np.tanh((x - b) / knee), y)
    return y

def m_hybrid(src, T, mask=None, gmin=0.6, gmax=1.8, noise_floor=0.0):
    """Recommended: OKLab lightness remap. Deviations from the material's median are scaled by the
    lightness ratio (physical multiply) but limited to [gmin, gmax] so black->white does not blow up
    DXT noise and white->black keeps some visible grain. Target chroma scaled by local lightness."""
    lab, ref = ref_stats(src, mask); t = srgb_to_oklab(T)
    g = float(np.clip(t[0] / max(ref[0], 1e-3), gmin, gmax))
    dL = lab[..., 0] - ref[0]
    if noise_floor > 0:   # soften tiny deviations (quantisation noise) before they are amplified
        dL = np.sign(dL) * np.maximum(np.abs(dL) - noise_floor, 0)
    out = np.empty_like(lab)
    out[..., 0] = softclip(t[0] + g * dL, 0.0, 1.0)
    k = np.clip(out[..., 0] / max(t[0], 1e-3), 0, 1.3)[..., None]
    out[..., 1:] = t[1:] * k + (lab[..., 1:] - ref[1:]) * 0.5
    return oklab_to_srgb(gamut_clip(out)), g

# ---------------------------------------------------------------- masks
def box(a, r):
    """Box blur radius r (edge-repeat), numpy cumulative sums."""
    p = np.pad(a, ((r, r), (r, r)) + ((0, 0),) * (a.ndim - 2), mode='edge').astype(np.float64)
    c = p.cumsum(0); c = np.concatenate([np.zeros_like(c[:1]), c], 0)
    p = (c[2 * r + 1:] - c[:-2 * r - 1])
    c = p.cumsum(1); c = np.concatenate([np.zeros_like(c[:, :1]), c], 1)
    return ((c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1) ** 2).astype(np.float32)

def kmeans(X, k, iters=15, seed=0):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), k, replace=False)]
    for _ in range(iters):
        d = ((X[:, None, :] - C[None]) ** 2).sum(-1); lab = d.argmin(1)
        for j in range(k):
            if (lab == j).any(): C[j] = X[lab == j].mean(0)
    return C, lab

def material_mask(src, region=None, k=3, wL=0.4, soft=(0.035, 0.07), sample=20000):
    """Weight 1 = the part's main material (recolour), 0 = contrasting detail (stitches, logos, piping).
    k-means on OKLab (L down-weighted, because AO/grain change L a lot but not hue); main cluster =
    the biggest; weight falls off with distance to its centre."""
    lab = srgb_to_oklab(src)
    X = lab * np.array([wL, 1, 1], np.float32)
    sel = X[region] if region is not None else X.reshape(-1, 3)
    rng = np.random.default_rng(1)
    S = sel[rng.choice(len(sel), min(sample, len(sel)), replace=False)]
    C, lab_ = kmeans(S.copy(), k)
    main = C[np.bincount(lab_, minlength=k).argmax()]
    d = np.sqrt(((X - main) ** 2).sum(-1))
    w = 1 - np.clip((d - soft[0]) / (soft[1] - soft[0]), 0, 1)
    return w, C, np.bincount(lab_, minlength=k) / len(lab_)

def median_dist_mask(src, region=None, wL=0.4, nsig=4.0):
    """Simpler: distance from the median colour, threshold = nsig * MAD-based spread."""
    lab = srgb_to_oklab(src); X = lab * np.array([wL, 1, 1], np.float32)
    sel = X[region] if region is not None else X.reshape(-1, 3)
    med = np.median(sel, 0); d = np.sqrt(((X - med) ** 2).sum(-1))
    s = 1.4826 * np.median(np.abs((d[region] if region is not None else d) - np.median(d))) + 1e-3
    t = np.median(d) + nsig * s
    return 1 - np.clip((d - t) / max(t, 1e-3), 0, 1)

def nm_cavity(nm, strength=1.0, r=2):
    """Cavity/crevice factor from a tangent-space normal map (no height integration): negative divergence
    of the normal's xy = valleys. Returns a multiplier ~[1-strength*.., 1]."""
    n = nm[..., :2] * 2 - 1
    gx = np.gradient(n[..., 0], axis=1); gy = np.gradient(-n[..., 1], axis=0)  # DirectX-style green handled by sign
    div = box((gx + gy)[..., None], r)[..., 0]
    s = np.percentile(np.abs(div), 95) + 1e-6
    return 1 - strength * np.clip(-div / s, 0, 1) * 0.5

# ---------------------------------------------------------------- metrics
def metrics(src, out, T, mask=None):
    ls = srgb_to_oklab(src)[..., 0]; lo = srgb_to_oklab(out)[..., 0]
    hs = ls - box(ls[..., None], 3)[..., 0]; ho = lo - box(lo[..., None], 3)[..., 0]
    m = mask if mask is not None else np.ones(ls.shape, bool)
    corr = float(np.corrcoef(hs[m], ho[m])[0, 1]) if hs[m].std() > 1e-6 and ho[m].std() > 1e-6 else 0.0
    med = np.median(srgb_to_oklab(out)[m], 0); t = srgb_to_oklab(T)
    dE = float(np.sqrt(((med - t) ** 2).sum()) * 100)
    o8 = np.round(out * 255)[m]
    clip = float(((o8 <= 0) | (o8 >= 255)).any(-1).mean() * 100)
    return dict(dE=dE, detail_src=float(hs[m].std() * 100), detail_out=float(ho[m].std() * 100), corr=corr, clip=clip,
                L_src=float(np.median(ls[m])), L_out=float(np.median(lo[m])), levels=int(len(np.unique(o8.sum(-1)))))

def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255

def save(a, p):
    Image.fromarray(np.clip(np.round(a * 255), 0, 255).astype(np.uint8)).save(p)
