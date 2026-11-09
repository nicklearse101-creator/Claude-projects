"""Feature-aligned grid for the CAD body loft (what a modeller does: loops follow the feature lines).

    python cad_feature_grid.py CURVES.npz

Each body section (sill -> roof centre) is split at landmarks found on that section:
    sill (start) | body-side crease | beltline (glass base) | roof edge | roof centre (end)
landmark = the sharpest turn within a height band (missing on a section -> interpolated from its
neighbours). Each segment is resampled to a fixed count, so row j means the same feature on every
section. Rows below the arch tops are bridged across the wheel-arch stations (the arch is cut later).
Adds 'body_grid' [stations, N, 3] to the npz.
"""
import sys
import numpy as np

COUNTS = (14, 14, 12, 18)      # sill->crease, crease->belt, belt->roof edge, roof edge->centre


def turning(C, w=3):
    a = np.zeros(len(C))
    for i in range(w, len(C) - w):
        u, v = C[i] - C[i - w], C[i + w] - C[i]
        a[i] = np.degrees(np.arccos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12), -1, 1)))
    return a


def resample(P, n):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, s[-1], n)
    return np.c_[[np.interp(t, s, P[:, k]) for k in range(3)]].T


def main(path):
    d = dict(np.load(path)); g = float(d['ground'])
    keys = sorted([k for k in d if k.startswith('sec_')], key=lambda k: int(k.split('_')[1]))
    secs = [np.asarray(d[k], float) for k in keys]
    z = np.array([s[0, 2] for s in secs])
    bands = [(g + 0.38, g + 0.62, None), (g + 0.74, g + 0.98, None), (g + 0.98, g + 1.30, 0.30)]
    L = np.full((len(secs), 3), np.nan)
    for i, C in enumerate(secs):
        a = turning(C)
        for j, (lo, hi, xmin) in enumerate(bands):
            m = (C[:, 1] > lo) & (C[:, 1] < hi)
            if xmin is not None: m &= C[:, 0] > xmin
            if m.sum() > 3 and a[m].max() > 8:
                L[i, j] = int(np.argmax(np.where(m, a, -1)))
    # landmarks as arc-length fractions, gaps filled from neighbours, kept in order
    frac = np.full(L.shape, np.nan)
    for i, C in enumerate(secs):
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
        for j in range(3):
            if np.isfinite(L[i, j]): frac[i, j] = s[int(L[i, j])] / s[-1]
    for j in range(3):
        ok = np.isfinite(frac[:, j])
        frac[~ok, j] = np.interp(z[~ok], z[ok], frac[ok, j]) if ok.sum() >= 2 else [0.3, 0.55, 0.75][j]
    frac = np.sort(np.clip(frac, 0.02, 0.98), axis=1)
    grid = []
    for i, C in enumerate(secs):
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]; s /= s[-1]
        cuts = [0.0] + list(frac[i]) + [1.0]; rows = []
        for k in range(4):
            m = (s >= cuts[k]) & (s <= cuts[k + 1])
            seg = C[m] if m.sum() >= 2 else np.array([np.array([np.interp(cuts[k], s, C[:, q]) for q in range(3)]),
                                                     np.array([np.interp(cuts[k + 1], s, C[:, q]) for q in range(3)])])
            r = resample(seg, COUNTS[k] + 1)
            rows.append(r if k == 0 else r[1:])
        grid.append(np.concatenate(rows))
    G = np.array(grid)
    # bridge the rows below each arch top across the arch stations (wells would pull the surface in)
    for zc, yc, r in d['arches']:
        inside = np.abs(z - zc) < r + 0.05
        if inside.sum() == 0 or (~inside).sum() < 2: continue
        lo_i, hi_i = np.where(inside)[0][[0, -1]]
        a_, b_ = max(lo_i - 1, 0), min(hi_i + 1, len(z) - 1)
        for j in range(G.shape[1]):
            if G[a_, j, 1] < yc + r + 0.03 or G[b_, j, 1] < yc + r + 0.03:
                for i in range(lo_i, hi_i + 1):
                    t = (z[i] - z[a_]) / (z[b_] - z[a_]); G[i, j, :2] = (1 - t) * G[a_, j, :2] + t * G[b_, j, :2]
    d['body_grid'] = G
    np.savez(path, **d)
    print('body grid', G.shape, 'landmarks found per band:', np.isfinite(L).sum(0).tolist(), 'of', len(secs))


if __name__ == '__main__':
    main(sys.argv[1])
