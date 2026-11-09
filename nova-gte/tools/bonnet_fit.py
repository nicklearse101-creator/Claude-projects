"""Clean bonnet surface from the top scan of the current body (export/ref/scan/bonnet_top.npz, blender/scripts -> scan
at 2.5 mm): outline (front edge, side shut lines, rear edge) and two smooth panels meeting at straight creases.
Writes export/ref/bonnet_fit.json for blender/scripts/bonnet_new.py.
Run: .venv\\Scripts\\python.exe tools\\bonnet_fit.py"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = np.load(os.path.join(ROOT, "export", "ref", "scan", "bonnet_top.npz"))
Z, NZ, xs, ys = d["Z"], d["NZ"], d["xs"], d["ys"]
XC0, XC1 = 0.3875, 0.1146                       # crease x = XC0 + XC1 (y + 1.64)  (traced on the scan, straight)
xc = lambda y: XC0 + XC1 * (y + 1.64)
Yn = lambda y: (y + 1.27) / 0.42


def edges():
    """Front / rear edge per column: the bonnet top runs from the rear edge forward until the surface turns down
    steeply (normal z < 0.55) - the edge over the grille / headlamps; rear edge = the scuttle drop (z falls 8 mm)."""
    front, rear = [], []
    for i, x in enumerate(xs):
        if abs(x) > 0.62:
            continue
        col, nz = Z[:, i], NZ[:, i]
        j = np.argmin(abs(ys + 1.25))
        a = j
        while a > 0 and np.isfinite(col[a - 1]) and nz[a - 1] > 0.55 and col[a] - col[a - 1] < 0.02:
            a -= 1
        b = j
        while b < len(ys) - 1 and np.isfinite(col[b + 1]) and col[b + 1] > col[b] - 0.008:
            b += 1
        front.append((float(x), float(ys[a]))); rear.append((float(x), float(ys[b])))
    return np.array(front), np.array(rear)


def sides():
    """Side shut line per row: the groove (local z minimum) near |x| 0.63."""
    out = []
    for j, y in enumerate(ys):
        if y < -1.66 or y > -0.88:
            continue
        r = []
        for s in (1, -1):
            m = (xs * s > 0.60) & (xs * s < 0.67) & np.isfinite(Z[j])
            if m.sum() < 3:
                r.append(np.nan); continue
            k = np.where(m)[0][np.argmin(Z[j][m] - 0.3 * (xs[m] * s - 0.6))]   # deepest relative to the slope
            r.append(abs(xs[k]))
        out.append((float(y), float(np.nanmean(r))))
    return np.array(out)


def poly_c(x, y):
    Y = Yn(y); return np.stack([x ** (2 * i) * Y ** j for i in range(4) for j in range(7)], 1)


def poly_o(u, y):
    Y = Yn(y); return np.stack([u ** i * Y ** j for i in range(3) for j in range(6)], 1)


def robust(A, z):
    k = np.ones(len(z), bool)
    for _ in range(5):
        c = np.linalg.lstsq(A[k], z[k], rcond=None)[0]
        r = A @ c - z
        k = np.abs(r) < 2.5 * r[k].std() + 2e-4
    return c, float(r[k].std()), float(np.abs(r).max())


def main():
    # outline from the shut-line grooves (high-pass of the scan, 2026-10-19): front edge y -1.680 to |x| 0.45 curving
    # back to -1.645 at the corners; rear edge -0.896 at the centre to -0.870 outboard; sides x 0.6275 (y -1.65) to
    # 0.6425 (y -0.90)
    cf = np.polyfit(np.array([0.0, 0.2025, 0.36, 0.49, 0.6025]) ** 2, [-1.680, -1.680, -1.678, -1.665, -1.645], 2)
    cr = np.polyfit(np.array([0, 0.2, 0.4, 0.55, 0.64]) ** 2, [-0.896, -0.887, -0.872, -0.866, -0.866], 2)
    cs = np.polyfit([-1.65, -0.90], [0.6275, 0.6425], 1)
    yf = lambda x: np.polyval(cf, x * x); yr = lambda x: np.polyval(cr, x * x); xside = lambda y: np.polyval(cs, y)
    XX, YY = np.meshgrid(xs, ys)
    inside = (np.abs(XX) < xside(YY) - 0.015) & (YY > yf(XX) + 0.012) & (YY < yr(XX) - 0.012) & np.isfinite(Z)
    inside &= ~((np.abs(XX) < 0.05) & (YY < -1.60))                                 # griffin badge
    u = np.abs(XX) - xc(YY)
    mc = inside & (u < -0.02); mo = inside & (u > 0.02)
    ccen, sc, mxc = robust(poly_c(XX[mc], YY[mc]), Z[mc])
    cout, so, mxo = robust(poly_o(u[mo], YY[mo]), Z[mo])
    res = {"crease": [XC0, XC1], "front_x2": cf.tolist(), "rear": cr.tolist(), "side": cs.tolist(),
           "centre": ccen.tolist(), "outer": cout.tolist(), "Yn": [1.27, 0.42],
           "fit_rms_mm": [round(sc * 1000, 2), round(so * 1000, 2)], "fit_max_mm": [round(mxc * 1000, 1), round(mxo * 1000, 1)]}
    json.dump(res, open(os.path.join(ROOT, "export", "ref", "bonnet_fit.json"), "w"), indent=1)
    print("front edge y at x 0 / 0.3 / 0.6:", [round(float(yf(x)), 4) for x in (0, 0.3, 0.6)])
    print("rear edge y at x 0 / 0.3 / 0.6:", [round(float(yr(x)), 4) for x in (0, 0.3, 0.6)])
    print("side x at y -1.6 / -0.9:", [round(float(xside(y)), 4) for y in (-1.6, -0.9)])
    print("fit rms mm", res["fit_rms_mm"], "max", res["fit_max_mm"])


if __name__ == "__main__":
    main()
