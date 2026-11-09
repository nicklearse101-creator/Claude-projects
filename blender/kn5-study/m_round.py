"""Blind-test build method: visual hull, then convex corners rounded with radius R (morphological opening).

The radius comes from ctx['round_mm'] (or env ROUND_MM). It is learned on OTHER cars (education), then
applied blind. Optionally per region: ctx['round_by_region'] = {(zone, band): mm}, where zone is
front/mid/rear (by axle) and band is lower/upper (split at the waist height).
"""
import os
import numpy as np
import blind_test as B


def _erode(a, n):
    b = a.copy()
    for i in range(n):
        c = b.copy()
        c[1:] &= b[:-1]; c[:-1] &= b[1:]; c[:, 1:] &= b[:, :-1]; c[:, :-1] &= b[:, 1:]
        if i % 2:   # alternate 4- and 8-neighbourhood: close to a round structuring element
            c[1:, 1:] &= b[:-1, :-1]; c[:-1, :-1] &= b[1:, 1:]; c[1:, :-1] &= b[:-1, 1:]; c[:-1, 1:] &= b[1:, :-1]
        b = c
    return b


def _dilate(a, n):
    return ~_erode(~a, n)


def opening(a, r_px):
    if r_px <= 0: return a
    return _dilate(_erode(a, r_px), r_px) & a


def build(ctx):
    fn, info = B.build_hull(ctx['side'], ctx['top'], ctx['front'], ctx['spec'], ctx['zs'], ctx['ylim'])
    r_mm = float(ctx.get('round_mm', os.environ.get('ROUND_MM', 40)))
    r_px = int(round(r_mm / 1000 / ctx['RES']))
    def f(z):
        return opening(fn(z), r_px)
    info['round_mm'] = r_mm
    return f, info
