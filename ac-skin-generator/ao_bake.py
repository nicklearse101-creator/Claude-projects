"""Ambient occlusion baked from the car's own model (1.17, Nik 22 Nov: "make AO map in content manager and have a white
base"). The livery's light and shade then come from the shape of the car, never from the old skin's picture.

The way Content Manager bakes it (actools "Baked shadows", BakedShadowsRenderer.cs - research in
reports/Car AO baking on CPU.md): many suns spread over the sky (elevation 0-60 degrees), a depth map of the car from
each, every texel lit by the suns it can see (light = n.L), averaged. Unlike CM, divided by what the texel would get
with nothing round it (occlusion only - the game adds the sun's own light and shade), then ^ 0.6 (CM's gamma).
Here on the CPU with numpy: the car's surface as dense points splatted into each depth map (np.maximum.at), the
texels of a texture tested against it."""
import numpy as np

VERSION = 7                      # (in the cache names: a change here bakes again)
DIRS = 128                       # suns (CM: 500-5000 with a GPU; averaged texels are smooth from ~100)
ELEVATION = (0.0, 60.0)          # degrees above the horizon (CM's default)
RES = 512                        # depth map pixels across the car (about 1 cm a pixel)
GAMMA = 0.6                      # softer deep shadows (CM's output gamma)
SKIP_RE = ('blur', 'shadow', 'damage', 'dirt', 'dmg', 'crack', 'broken')


def sky_dirs(n=DIRS, elevation=ELEVATION):
    """Suns spread evenly: uniform in sin(elevation) (equal sky area), azimuth by the golden angle. Y is up."""
    k = np.arange(n) + 0.5
    s0, s1 = np.sin(np.radians(elevation[0])), np.sin(np.radians(elevation[1]))
    s = s0 + (s1 - s0) * k / n
    az = k * np.pi * (3 - np.sqrt(5))
    c = np.sqrt(1 - s * s)
    return np.stack([c * np.cos(az), s, c * np.sin(az)], 1)


def occluders(meshes, see_through):
    """The parts that cast shadows: as the model says (cast shadows on), not glass (light goes through it), not
    blurred-wheel copies, shadow planes or damage / dirt copies lying over the panels."""
    out = []
    for m in meshes:
        if not len(m.idx) or not getattr(m, 'cast', True) or not getattr(m, 'shown', True): continue
        if m.mat is not None and see_through(m.mat): continue
        if any(w in m.name.lower() for w in SKIP_RE): continue
        out.append(m.pos[m.idx])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def surface_points(T, spacing, seed=1):
    """Points over the triangles T (n, 3, 3), about one per spacing x spacing, never fewer than one each (big flat
    panels get as many as they need - no gaps in the depth maps)."""
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    cnt = np.maximum(1, np.ceil(area / spacing ** 2)).astype(np.int64)
    rep = np.repeat(np.arange(len(T)), cnt)
    rng = np.random.default_rng(seed)
    u, v = rng.random(len(rep)), rng.random(len(rep))
    f = u + v > 1; u[f], v[f] = 1 - u[f], 1 - v[f]
    S = T[rep, 0] + (T[rep, 1] - T[rep, 0]) * u[:, None] + (T[rep, 2] - T[rep, 0]) * v[:, None]
    return np.concatenate([S, T.reshape(-1, 3)]).astype(np.float32)        # (the corners too: thin parts)


def _basis(d):
    up = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(up, d); u /= np.linalg.norm(u)
    return u, np.cross(d, u)


def bake(occ_tris, P, N, dirs=None, res=RES, gamma=GAMMA, stop=None):
    """AO (0..1) at the points P with normals N (the texels of a texture). None when stop() said so."""
    dirs = sky_dirs() if dirs is None else dirs
    lo, hi = occ_tris.reshape(-1, 3).min(0), occ_tris.reshape(-1, 3).max(0)
    centre = (lo + hi) / 2
    half = np.linalg.norm(hi - lo) / 2 * 1.02                              # any view of the car fits
    px = 2 * half / res
    Q = surface_points(occ_tris, 0.7 * px) - centre.astype(np.float32)
    P = (P - centre).astype(np.float32); N = N.astype(np.float32)
    bad = ~np.isfinite(N).all(1)                                           # (a few texels on squashed triangles)
    if bad.any(): N = N.copy(); N[bad] = (0, 1, 0)
    Pn = P + N * np.float32(1.0 * px)                                      # off its own surface by a pixel
    acc = np.zeros(len(P), np.float32)
    for d in dirs:
        if stop is not None and stop(): return None
        u, v = _basis(d)
        B = np.stack([u, v, d], 1).astype(np.float32)
        q = Q @ B
        ix = np.clip((q[:, 0] / px + res / 2).astype(np.int32), 0, res - 1)
        iy = np.clip((q[:, 1] / px + res / 2).astype(np.int32), 0, res - 1)
        zb = np.full(res * res, -np.inf, np.float32)
        np.maximum.at(zb, iy * res + ix, q[:, 2])                          # the surface nearest that sun, per pixel
        zb = zb.reshape(res, res)
        g = zb.copy()                                                      # 3 x 3: no pinholes between the points
        g[1:] = np.maximum(g[1:], zb[:-1]); g[:-1] = np.maximum(g[:-1], zb[1:])
        z2 = g.copy(); z2[:, 1:] = np.maximum(z2[:, 1:], g[:, :-1]); z2[:, :-1] = np.maximum(z2[:, :-1], g[:, 1:])
        cos = np.clip(N @ d.astype(np.float32), 0, 1)
        p = Pn @ B
        jx = np.clip((p[:, 0] / px + res / 2).astype(np.int32), 0, res - 1)
        jy = np.clip((p[:, 1] / px + res / 2).astype(np.int32), 0, res - 1)
        slope = np.sqrt(np.clip(1 - cos * cos, 0, 1)) / np.maximum(cos, 0.2)
        lit = z2[jy, jx] <= p[:, 2] + px * (1.5 + 1.5 * np.minimum(slope, 4))
        acc += cos * lit
    # occlusion only: the light a texel gets over what it would get facing the same way with nothing round it, so an
    # open door is as light as an open roof (the game lights the car from its sun itself); faces turned down to the
    # ground (that the sky hardly reaches) darken as they turn
    ref = np.clip(N @ dirs.T.astype(np.float32), 0, 1).mean(1)
    up = float(np.clip(dirs[:, 1], 0, 1).mean())
    return np.clip(acc / len(dirs) / np.maximum(ref, 0.25 * up), 0, 1) ** gamma
