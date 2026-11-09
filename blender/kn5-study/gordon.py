"""Gordon surface (curve network -> exact surface) for panels that are height fields in their own view.

A side panel: depth x = f(y, z) (Blender frame: y along the car, z up). The network:
  waterlines  x_i(y) at heights z_i   (incl. the crease line height, and near the top and bottom edges)
  verticals   x_j(z) at positions y_j (sections across the panel)
Gordon:  S = P_z + P_y - P_yz
  P_z  = cubic spline in z through the waterlines (at each y)
  P_y  = cubic spline in y through the verticals (at each z)
  P_yz = tensor spline through the network's crossing points
The surface passes EXACTLY through every curve; nothing is smoothed. Creases: the network is split into
separate Gordon patches at crease heights (C0 between them = a sharp line).
"""
import numpy as np


def natural_spline_weights(knots, t):
    """matrix W (len(t) x len(knots)) so that spline(t) = W @ values, natural cubic spline"""
    k = np.asarray(knots, float); n = len(k)
    if n == 1: return np.ones((len(t), 1))
    if n == 2:
        w = np.clip((t - k[0]) / (k[1] - k[0]), -0.5, 1.5); return np.c_[1 - w, w]
    h = np.diff(k)
    # second derivatives M = A^-1 B y  (natural: M0 = Mn = 0)
    A = np.zeros((n, n)); Bm = np.zeros((n, n)); A[0, 0] = A[-1, -1] = 1
    for i in range(1, n - 1):
        A[i, i - 1] = h[i - 1] / 6; A[i, i] = (h[i - 1] + h[i]) / 3; A[i, i + 1] = h[i] / 6
        Bm[i, i - 1] = 1 / h[i - 1]; Bm[i, i] = -1 / h[i - 1] - 1 / h[i]; Bm[i, i + 1] = 1 / h[i]
    Mm = np.linalg.solve(A, Bm)          # M = Mm @ y
    tt = np.clip(t, k[0], k[-1])
    seg = np.clip(np.searchsorted(k, tt) - 1, 0, n - 2)
    W = np.zeros((len(t), n))
    for r, (x, s) in enumerate(zip(tt, seg)):
        a, b = k[s], k[s + 1]; hh = b - a
        A_ = (b - x) / hh; B_ = (x - a) / hh
        W[r, s] += A_; W[r, s + 1] += B_
        c1 = ((A_ ** 3 - A_) * hh * hh / 6); c2 = ((B_ ** 3 - B_) * hh * hh / 6)
        W[r] += c1 * Mm[s] + c2 * Mm[s + 1]
    # linear extrapolation outside the knots
    lo, hi = t < k[0], t > k[-1]
    if lo.any():
        g = (t[lo] - k[0]) / (k[1] - k[0]); W[lo] = 0; W[lo, 0] = 1 - g; W[lo, 1] = g
    if hi.any():
        g = (t[hi] - k[-2]) / (k[-1] - k[-2]); W[hi] = 0; W[hi, -2] = 1 - g; W[hi, -1] = g
    return W


def gordon(ys, zs, z_lines, X_wl, y_lines, X_vt):
    """ys, zs: output grid axes. z_lines: waterline heights; X_wl[i] = depth along ys of waterline i.
    y_lines: vertical positions; X_vt[j] = depth along zs of vertical j. Returns depth grid [len(ys), len(zs)]."""
    Wz = natural_spline_weights(z_lines, zs)            # [nz, ni]
    Wy = natural_spline_weights(y_lines, ys)            # [ny, nj]
    Pz = np.asarray(X_wl).T @ Wz.T                      # [ny, nz]
    Py = Wy @ np.asarray(X_vt)                          # [ny, nz]
    # crossing values: waterline i at y_j (should equal vertical j at z_i; average for consistency)
    Wy_at = natural_spline_weights(y_lines, np.asarray(y_lines))
    yi = [int(np.argmin(np.abs(ys - yj))) for yj in y_lines]; zi = [int(np.argmin(np.abs(zs - zk))) for zk in z_lines]
    Cx = 0.5 * (np.asarray(X_wl)[:, yi] + np.asarray(X_vt)[:, zi].T)     # [ni, nj]
    Pyz = Wy @ Cx.T @ Wz.T
    return Pz + Py - Pyz
