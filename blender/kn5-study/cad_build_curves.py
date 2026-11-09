"""CAD car build, step 1 (plain Python): extract the curves a surface modeller would use.

    python cad_build_curves.py CAR_DIR OUT_DIR

Method test: the curves come from the true model's outer skin. Later they come from photos/blueprints.
AC frame (x left, y up, z forward), left half (x >= 0). Output OUT/<car>_cad_curves.npz:
  stations  [n] z of each body section;  sec_k  section k as points (sill -> side -> roof centre)
  nose_y/tail_y heights of the end-panel slices; nose_k / tail_k slice curves (centre -> side)
  z_front, z_rear  where the body loft ends and the end panels start
  arches  (z, y, r) per axle
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blind_test as B
import car_loft as CL
from section import cut


def ray_envelope(segs2, c, angles):
    """outermost hit of rays from c (2D) against 2D segments; nan where nothing"""
    a, b = segs2[:, 0], segs2[:, 1]
    out = np.full((len(angles), 2), np.nan)
    for k, t in enumerate(angles):
        d = np.array([np.cos(t), np.sin(t)])
        e = b - a; w = a - c
        den = d[0] * e[:, 1] - d[1] * e[:, 0]
        ok = np.abs(den) > 1e-12
        s = np.where(ok, (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / np.where(ok, den, 1), -1)     # along ray
        u = np.where(ok, (w[:, 0] * d[1] - w[:, 1] * d[0]) / np.where(ok, den, 1), -1)          # along segment
        hit = ok & (s > 0) & (u >= 0) & (u <= 1)
        if hit.any():
            out[k] = c + d * s[hit].max()
    return out


def resample(P, step):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    n = max(int(d[-1] / step), 4)
    t = np.linspace(0, d[-1], n)
    return np.c_[[np.interp(t, d, P[:, k]) for k in range(P.shape[1])]].T


def main(car_dir, out):
    ctx = B.setup(car_dir, out)
    g = ctx['ground']
    T, n = CL.skin_triangles(ctx, car_dir)            # left-half outer skin triangles
    P = T.reshape(-1, 3); I = np.arange(len(P)).reshape(-1, 3)
    zmin, zmax = P[:, 2].min(), P[:, 2].max()
    hw = P[:, 0].max()
    z_front, z_rear = zmax - 0.36, zmin + 0.30
    # --- body sections every 100 mm between the end panels
    stations = np.r_[np.arange(z_rear, z_front, 0.10), z_front]
    c = np.array([0.0, g + 0.55])
    ang = np.radians(np.arange(-75, 90.01, 0.5))
    secs = {}
    for k, z in enumerate(stations):
        s = cut(P, I, 2, z)
        if not len(s): continue
        E = ray_envelope(s.reshape(-1, 2, 3)[:, :, :2], c, ang)
        ok = np.isfinite(E[:, 0])
        # nothing under the car: drop hits low down near the centre line
        ok &= ~((E[:, 1] < g + 0.30) & (E[:, 0] < 0.6 * hw))
        E = E[ok]
        if len(E) < 20: continue
        E = np.r_[E, [[0.0, E[-1, 1]]]] if E[-1, 0] > 0.002 else E      # finish on the centre line
        secs[f'sec_{k}'] = np.c_[resample(E, 0.008), np.full(len(resample(E, 0.008)), z)]
    # --- end panels: horizontal slices (plan curves centre -> side) of the nose and tail
    def end_slices(zcut, front):
        ys = np.arange(g + 0.16, P[:, 1].max(), 0.025); res = {}
        for j, y in enumerate(ys):
            s = cut(P, I, 1, y)
            if not len(s): continue
            Q = s.reshape(-1, 3)
            Q = Q[(Q[:, 2] >= zcut) if front else (Q[:, 2] <= zcut)]
            if len(Q) < 10: continue
            xb = np.arange(0, Q[:, 0].max() + 0.003, 0.004)
            idx = np.clip((Q[:, 0] / 0.004).astype(int), 0, len(xb) - 1)
            zz = np.full(len(xb), np.nan)
            for i, v in zip(idx, Q[:, 2]):
                if front: zz[i] = v if not (zz[i] >= v) else zz[i]
                else: zz[i] = v if not (zz[i] <= v) else zz[i]
            ok = np.isfinite(zz)
            if ok.sum() < 10: continue
            C = np.c_[xb[ok], np.full(ok.sum(), y), zz[ok]]
            res[j] = resample(C, 0.008)
        return ys, res
    ny, nose = end_slices(z_front, True); ty, tail = end_slices(z_rear, False)
    meas = ctx['meas']
    arches = [list(a) for a in ctx['arches']]
    np.savez(os.path.join(out, f"{ctx['car']}_cad_curves.npz"), stations=stations, z_front=z_front, z_rear=z_rear,
             arches=np.array(arches), ground=g, half_width=hw,
             **secs, **{f'nose_{j}': v for j, v in nose.items()}, **{f'tail_{j}': v for j, v in tail.items()})
    print(json.dumps(dict(sections=len(secs), nose=len(nose), tail=len(tail), z_front=round(z_front, 3), z_rear=round(z_rear, 3),
                          arches=[[round(v, 3) for v in a] for a in arches])))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
