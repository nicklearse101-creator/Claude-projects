"""Signed outline error of the model vs the photo silhouette, grouped by where on the body the model outline
point is. +cm = model sticks out beyond the photo outline (too big there), -cm = model inside (too small).
usage: region_diff.py cam [cam ...]"""
import sys, numpy as np, cv2
import preview as pv
from outline_diff import idrender

BANDS = [(0.0, 0.45, 'low'), (0.45, 0.85, 'mid'), (0.85, 2.0, 'high')]


def fill(mask):
    m = mask.astype(np.uint8) * 255
    h, w = m.shape
    ff = m.copy(); pad = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, pad, (0, 0), 255)
    return (m | (255 - ff)) > 0


def diff(c, verbose=True):
    seg = fill(cv2.imread(f'seg_{c}.png', 0) > 0)
    P, _, _, _ = idrender(c)
    _, full = pv.render(c)
    m = fill(full > 0)
    cp = np.array(pv.B['cams'][c]); f = cp[6]
    R, _ = cv2.Rodrigues(cp[:3]); t = cp[3:6]
    edge = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    edge &= m                                           # model-side outer outline pixels (shell only below)
    d_out = cv2.distanceTransform((~seg).astype(np.uint8), cv2.DIST_L2, 5)
    d_in = cv2.distanceTransform(seg.astype(np.uint8), cv2.DIST_L2, 5)
    vs, us = np.where(edge)
    X = P[vs, us]; ok = ~np.isnan(X).any(1)
    vs, us, X = vs[ok], us[ok], X[ok]
    s = np.where(seg[vs, us], -d_in[vs, us], d_out[vs, us])
    depth = (X @ R.T + t)[:, 2]
    cm = s * depth / f * 100
    rows = []
    for y0 in np.arange(-1.8, 1.8, 0.2):
        for z0, z1, bn in BANDS:
            for side, sel in (('near', None), ('far', None)):
                cam_x = (-R.T @ t)[0]
                nearsel = np.sign(X[:, 0]) == np.sign(cam_x)
                k = (X[:, 1] >= y0) & (X[:, 1] < y0 + 0.2) & (X[:, 2] >= z0) & (X[:, 2] < z1) & (nearsel if side == 'near' else ~nearsel)
                if k.sum() >= 6:
                    rows.append((y0 + 0.1, bn, side, np.median(cm[k]), np.percentile(cm[k], 20), np.percentile(cm[k], 80), int(k.sum())))
    if verbose:
        print(f'== {c}: y-bin band side  median cm (p20..p80) n')
        for r in rows:
            flag = ' <<' if abs(r[3]) > 1.5 else ''
            print(f'{r[0]:+.1f} {r[1]:4s} {r[2]:4s} {r[3]:+5.1f} ({r[4]:+5.1f}..{r[5]:+5.1f}) {r[6]:4d}{flag}')
    return rows


if __name__ == '__main__':
    for c in sys.argv[1:]:
        diff(c)
