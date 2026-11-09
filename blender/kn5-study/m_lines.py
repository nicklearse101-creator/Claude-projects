"""Blind-test build method: visual hull + traced plan feature lines (body outline in plan above the beltline
and above the roof rail, as drawn inside a blueprint's top view). Above each line's height, a point must
also lie inside that plan outline. Optional corner rounding (ROUND_MM)."""
import os
import numpy as np
import blind_test as B
from m_round import opening


def build(ctx):
    fn, info = B.build_hull(ctx['side'], ctx['top'], ctx['front'], ctx['spec'], ctx['zs'], ctx['ylim'])
    zs, RES, X0 = ctx['zs'], ctx['RES'], ctx['X0']
    ny = ctx['front'].shape[1]; yy = ctx['ylim'][0] + np.arange(ny) * RES
    r_px = int(round(float(os.environ.get('ROUND_MM', 0)) / 1000 / RES))
    def f(z):
        s = fn(z)
        i = int(round((z - zs[0]) / (zs[1] - zs[0])))
        if 0 <= i < len(zs):
            for h, plan in ctx['lines'].values():
                s[:, yy >= h] &= plan[i][:, None]
        return opening(s, r_px) if r_px else s
    info['lines'] = {k: round(float(v[0]), 3) for k, v in ctx['lines'].items()}
    return f, info
