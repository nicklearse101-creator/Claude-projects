"""Least-squares cubic B-spline fit of a pixel trace - numpy only (runs inside Blender's Python too).

The traced drawing lines are read at the blueprint's pixel pitch (2.7 mm in height, 5.4 mm along the car on the
side elevation), so a trace is a staircase: its height steps a whole pixel at a time. A running mean of it still
ripples, and the ripple shows as waves in the reflections. The data cannot resolve anything finer than a pixel, so
the curve used is the smoothest one consistent with it: a cubic B-spline with knots KNOT apart, fitted by least
squares, and accepted only if it stays within TOL (one pixel) of every traced point.

    from trace_fit import bspline_fit
    f, worst = bspline_fit(y, z, knot=0.12)       # f(y_array) -> z_array, worst deviation in metres
"""
import numpy as np


def _basis(x, t, k=3):
    """Cox-de Boor: all B-spline basis functions of degree k on knot vector t, evaluated at x."""
    x = np.asarray(x, float)
    n = len(t) - k - 1
    B = np.zeros((len(x), len(t) - 1))
    for i in range(len(t) - 1):
        B[:, i] = (x >= t[i]) & (x < t[i + 1])
    B[x >= t[-1], n - 1] = 1.0                      # include the right end
    for d in range(1, k + 1):
        Bn = np.zeros((len(x), len(t) - 1 - d))
        for i in range(len(t) - 1 - d):
            a = (x - t[i]) / (t[i + d] - t[i]) if t[i + d] > t[i] else 0.0
            b = (t[i + d + 1] - x) / (t[i + d + 1] - t[i + 1]) if t[i + d + 1] > t[i + 1] else 0.0
            Bn[:, i] = a * B[:, i] + b * B[:, i + 1]
        B = Bn
    return B[:, :n]


def bspline_fit(x, y, knot=0.12, k=3):
    x = np.asarray(x, float); y = np.asarray(y, float)
    o = np.argsort(x); x, y = x[o], y[o]
    span = x[-1] - x[0]
    m = max(1, int(round(span / knot)))
    inner = np.linspace(x[0], x[-1], m + 1)
    t = np.r_[[x[0]] * k, inner, [x[-1]] * k]
    A = _basis(x, t, k)
    c, *_ = np.linalg.lstsq(A, y, rcond=None)

    def f(q):
        q = np.clip(np.asarray(q, float), x[0], x[-1])
        return _basis(q, t, k) @ c

    worst = float(np.abs(f(x) - y).max())
    return f, worst
