"""Sweep the v7 rear double wishbone through its travel: camber, toe, track change, roll centre.
AC convention (as read from Kunos files): x = inboard from the wheel centre, y = up from it, z = forward.
Here: X = outboard from the car centreline (X = halftrack - x), Y up, Z forward."""
import math
import sys


class _NP:
    """just enough numpy for this script (3-vectors, 6x6 solve)"""
    class V(list):
        def __add__(a, b): return _NP.V(x + y for x, y in zip(a, b))
        def __sub__(a, b): return _NP.V(x - y for x, y in zip(a, b))
        def __mul__(a, k): return _NP.V(x * k for x in a)
        __rmul__ = __mul__
        def __truediv__(a, k): return _NP.V(x / k for x in a)
        def __matmul__(a, b): raise TypeError
    @staticmethod
    def array(x):
        return _NP.M(x) if x and isinstance(x[0], (list, tuple)) else _NP.V(x)
    class M(list):
        def __matmul__(m, v):
            if isinstance(v[0], list):
                return _NP.M([[sum(r[k] * v[k][j] for k in range(len(v))) for j in range(len(v[0]))] for r in m])
            return _NP.V(sum(r[i] * v[i] for i in range(len(v))) for r in m)
    @staticmethod
    def zeros(n):
        return _NP.V([0.0] * n) if isinstance(n, int) else [[0.0] * n[1] for _ in range(n[0])]
    class linalg:
        @staticmethod
        def norm(v): return sum(x * x for x in v) ** 0.5
        @staticmethod
        def solve(A, b):
            n = len(b); M = [list(A[i]) + [b[i]] for i in range(n)]
            for c in range(n):
                piv = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[piv] = M[piv], M[c]
                for r in range(n):
                    if r != c:
                        f = M[r][c] / M[c][c]
                        M[r] = [x - f * y for x, y in zip(M[r], M[c])]
            return _NP.V(M[i][n] / M[i][i] for i in range(n))
np = _NP

sys.path.insert(0, r"D:\Claude\talbot_sunbeam_lotus\tools")
import importlib.util
spec = importlib.util.spec_from_file_location("bc", r"D:\Claude\escort_mk2_dtm\tools\dtm_build.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

HALF = 1.3735 / 2            # Escort DTM rear track / 2
R = 0.268                     # Escort 13in DTM90 slick radius
G = bc.REAR_DWB


def P(key):
    x, y, z = G[key]
    return np.array([HALF - x, y, z])


UF, UR, LF, LR, TI = P("WBCAR_TOP_FRONT"), P("WBCAR_TOP_REAR"), P("WBCAR_BOTTOM_FRONT"), P("WBCAR_BOTTOM_REAR"), P("WBCAR_STEER")
UBJ0, LBJ0, TO0 = P("WBTYRE_TOP"), P("WBTYRE_BOTTOM"), P("WBTYRE_STEER")
WC0 = np.array([HALF, 0.0, 0.0])
SPIN0 = np.array([1.0, 0.0, 0.0])          # wheel axis, outboard
d = lambda a, b: np.linalg.norm(a - b)
L = [d(UBJ0, UF), d(UBJ0, UR), d(LBJ0, LF), d(LBJ0, LR), d(TO0, TI)]


def rot(v):
    a, b, c = v
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def pose(q):
    Rm, t = rot(q[3:]), np.V(q[:3])
    f = lambda p: Rm @ (p - WC0) + WC0 + t
    return f(UBJ0), f(LBJ0), f(TO0), WC0 + t, Rm @ SPIN0


def resid(q, dy):
    u, l, to, wc, _ = pose(q)
    return np.array([d(u, UF) - L[0], d(u, UR) - L[1], d(l, LF) - L[2], d(l, LR) - L[3], d(to, TI) - L[4], wc[1] - dy])


def solve(dy, q):
    for _ in range(50):
        r = resid(q, dy)
        if max(abs(x) for x in r) < 1e-12:
            break
        J = [[0.0] * 6 for _ in range(6)]
        for i in range(6):
            e = np.zeros(6); e[i] = 1e-7; e = np.V(e)
            col = (resid(q + e, dy) - r) / 1e-7
            for j in range(6): J[j][i] = col[j]
        q = q - np.linalg.solve(J, r)
    return q


q = np.zeros(6)
print("arms: upper %.3f m, lower %.3f m, toe link %.3f m" % ((L[0] + L[1]) / 2, (L[2] + L[3]) / 2, L[4]))
print("bump(mm)  camber(deg)  toe(deg, +in)   track change(mm)  wheel fore/aft(mm)")
for dy_mm in (-80, -60, -40, -20, 0, 20, 40, 60, 80):
    q = solve(dy_mm / 1000, q if dy_mm != -80 else np.zeros(6))
    u, l, to, wc, spin = pose(q)
    camber = math.degrees(math.asin(-spin[1]))          # top leaning in = negative
    toe = math.degrees(math.atan2(spin[2], spin[0]))    # axis pointing forward = toe-out (rear-left)
    print("%8d  %11.2f  %14.3f  %16.1f  %18.1f" % (dy_mm, camber, toe, (wc[0] - HALF) * 1000, wc[2] * 1000))

# front-view instant centre and roll centre at static
def line(a, b):
    return np.V(a[:2]), np.V(b[:2])
(p1, p2), (p3, p4) = line(UBJ0, (UF + UR) / 2), line(LBJ0, (LF + LR) / 2)
A = [[p2[0] - p1[0], -(p4[0] - p3[0])], [p2[1] - p1[1], -(p4[1] - p3[1])]]
s, t = np.linalg.solve(A, [p3[0] - p1[0], p3[1] - p1[1]])
ic = p1 + s * (p2 - p1)
cp = np.array([HALF, -R])
k = (0 - cp[0]) / (ic[0] - cp[0])
rc = cp[1] + k * (ic[1] - cp[1]) + R
print("instant centre X=%.2f m (from centreline), Y=%.3f m above hub; roll centre %.0f mm above ground" % (ic[0], ic[1], rc * 1000))
