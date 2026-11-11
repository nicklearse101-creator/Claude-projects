"""AE86 bonnet skin (GEO_hood_SUB1) as Class-A panels (research: blender/research/reports/Bonnet surfacing.md).

    python bonnet_build.py CAR_DIR OUT_DIR

What the Kunos skin (crease region 0) is:
- C: the raised CENTRE panel, full width, symmetric: the middle, the tongue up to the nose roll, and the rear zone
  behind the step's hook (the raised level wraps round the rear end of the outer panel);
- O: two OUTER panels (right fitted, left = its mirror), crowned towards the wing;
- the STEP line between them: a 3.2 mm drop at the rear that dies to nothing at the headlamp-notch corner
  (z ~1720) and, at the rear, hooks ~80 deg outward (R ~44 mm) into a tail that dies at a tip (440.9, 885.2).
  Kunos made it a straight 13 mm ramp whose look comes from averaged normals; we build a G2 band ~20 mm wide:
  quintic Hermite across it from the jets of C (side A) and O (side B), exact B-spline poles.
- Beyond the tail tip the two panels are the SAME surface: C is fitted with G2 rows equal to O along the seam S
  (the band's end cross-section carried on to the rear edge), so the step dies by height, never by width.
- NOSE: a straight -52.5 deg front face F (linear in z, following the bowed plan front edge e(x)) and a G2 roll
  C -> F of constant width across the plan curve, DEGREE 7 in the roll direction: the three end coefficients on each
  side come from the jets of C and F (G2 by construction), the two middle ones get one fitted offset each from the
  Kunos roll vertices (one value for the whole width: the section is constant across x). A quintic (no free shape)
  could not follow Kunos's progressive roll (gentle to z 1855, tight near the face): 4-5 mm high, or C did the
  bending (R 28 mm).
Every face is over the PLAN (frame s = z, t = x, h = y, mm) like roof_build.py. Edge strips, underside: later steps
of the report's build order.
"""
import sys, os, json
from math import comb
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path:
    sys.path.append(r'D:\ClaudeData\pylibs')
from scipy.interpolate import BSpline, splprep, splev
import panel_fit as PF
from roof_build import HF, FRAME, bas, jet_z

MESH = 'GEO_hood_SUB1'
# step line mid-row points (x, z) mm, measured on the Kunos mesh (research notes kunos_bonnet_measurements.md):
# tail tip -> tail -> hook (mid of the two creases) -> main run stations -> notch corner
LINE_PTS = np.array([
    (440.9, 885.2), (403.65, 892.9), (384.65, 897.95), (365.15, 902.9), (354.8, 906.85), (345.35, 912.75),
    (338.95, 919.3), (334.3, 927.85),
    (336.6, 1008), (341.0, 1110), (345.4, 1211), (349.2, 1311), (353.1, 1410), (356.3, 1508), (359.4, 1607),
    (358.4, 1664), (361.5, 1721)])
NOSE_Z = float(os.environ.get('BN_NOSE_Z', 1790))      # without the nose (BN_NOSE=0): C data stops here on the tongue
NOSE = os.environ.get('BN_NOSE', '1') != '0'
NOSE_A = float(os.environ.get('BN_NOSE_A', 72))        # roll start on C: z = e(x) - A (e = plan front edge)
NOSE_B = float(os.environ.get('BN_NOSE_B', 16))        # roll end on the front face: z = e(x) - B
# (best vertex fit was A 68 / B 20: rms 0.24 mm but R_min 43 mm, a visible dark band in grey; A 72 / B 16 gives
#  R_min 68 mm (research target 70-110) and reads like Kunos - judged by eye, 11 Nov)


# ---------- B-spline helpers (degree 5 along the line) ----------
def kv_uniform(a, b, nspan, p=5): return np.r_[[a] * (p + 1), np.linspace(a, b, nspan + 1)[1:-1], [b] * (p + 1)]
def dmat(kv, x, p=5, d=0):
    n = len(kv) - p - 1; b = BSpline(kv, np.eye(n), p, extrapolate=False)
    if d: b = b.derivative(d)
    return np.nan_to_num(b(np.clip(x, kv[0], kv[-1])))


# ---------- the step line ----------
class Line:
    """fair plan curve through LINE_PTS, parametrised by arc length s (mm) from the tail tip (s = 0) to the notch.
    left = +90 deg from the direction of travel = the C (raised) side all along (rearward on the tail, inward on
    the main run)."""
    def __init__(self, pts, smooth=None):
        x, z = pts[:, 0], pts[:, 1]
        smooth = len(pts) * 0.15 ** 2 if smooth is None else smooth
        tck, _ = splprep([x, z], s=smooth, k=5)
        u = np.linspace(0, 1, 20001); X, Z = splev(u, tck)
        d = np.r_[0, np.cumsum(np.hypot(np.diff(X), np.diff(Z)))]
        self.tck, self.u, self.d, self.L = tck, u, d, d[-1]
        self.err = max(np.min(np.hypot(X - a, Z - b)) for a, b in pts)
    def at(self, s):
        u = np.interp(s, self.d, self.u)
        x, z = splev(u, self.tck); dx, dz = splev(u, self.tck, der=1); ddx, ddz = splev(u, self.tck, der=2)
        sp = np.hypot(dx, dz); T = np.c_[dx, dz] / sp[:, None]
        N = np.c_[-T[:, 1], T[:, 0]]                       # left normal (x, z)
        kap = (dx * ddz - dz * ddx) / sp ** 3
        return np.c_[x, z], T, N, kap
    def project(self, P, n=4000):
        """signed distance (+ = C side) and arc parameter of plan points P (x, z); beyond the ends: extended tangents"""
        s = np.linspace(0, self.L, n); Q, T, N, _ = self.at(s)
        out_d = np.zeros(len(P)); out_s = np.zeros(len(P))
        for i, p in enumerate(P):
            k = np.argmin(((Q - p) ** 2).sum(1)); r = p - Q[k]
            out_s[i] = s[k] + r @ T[k]; out_d[i] = r @ N[k]
        return out_d, out_s


def width_law(s, L, line):
    """band width (mm): ~20 at the rear main run (Kunos 15 deg ramp + its ~18 mm shading spread), 16 through the
    hook (line radius ~44 > 2 w), 8 at the tail tip, tapering to 10 at the notch"""
    P, _, _, _ = line.at(np.atleast_1d(s)); z = P[:, 1]
    s_hook = line.project(np.array([[334.3, 927.85]]))[1][0]
    w = np.where(s < s_hook, 8 + (16 - 8) * np.clip(s / max(s_hook, 1), 0, 1), 0.0)
    main = 20 - 10 * np.clip((z - 1400) / (1721 - 1400), 0, 1)
    ramp = np.clip((s - s_hook) / 60.0, 0, 1)
    return np.where(s < s_hook, w, 16 + (main - 16) * ramp)


# ---------- data ----------
def skin(car):
    V, F, N = PF.load_mesh(car, MESH, raw=True)
    R0 = PF.crease_pieces(V, F, N)[0]
    u = np.unique(R0); P = V[u] * 1000                    # (x, y, z) mm
    return V, F, N, R0, P


def classify(P, line, tip, sdir):
    """C / O membership of skin vertices (right half, x >= 0), from the step line and the seam S (from the tail tip
    along sdir = the band's end cross-section, to the rear edge). Points within 1.2 mm of the line: neither (Kunos
    mid row = halfway up its ramp)."""
    X = np.c_[np.abs(P[:, 0]), P[:, 2]]
    d, s = line.project(X)
    isC = d > 1.2; isO = d < -1.2
    beyond = s < 0                                          # past the tail tip (outboard of S): O (= C there)
    isC = np.where(beyond, False, isC); isO = np.where(beyond, True, isO)
    front = s > line.L                                      # ahead of the notch corner: tongue (C) or nothing
    oe = (X[:, 0] >= 366) & (X[:, 1] < 1730)                   # the outer panel's front edge (lamp bays, z 1715-1727)
    isC = np.where(front, ~oe & (X[:, 0] < 366), isC); isO = np.where(front, oe, isO)
    return isC, isO, d, s


# ---------- fits ----------
def fit_rows(hf, s, t, h, lam, drows=(), w=1.0):
    """least squares on points + derivative rows [(s, t, ds, dt, value, weight)] + lam * third-derivative energy"""
    A = [hf.A(s, t)]; b = [h]
    for s_, t_, ds_, dt_, v_, w_ in drows:
        A.append(np.sqrt(w_) * hf.A(s_, t_, ds_, dt_)); b.append(np.sqrt(w_) * np.atleast_1d(v_))
    A = np.vstack(A); b = np.concatenate(b)
    hf.c = np.linalg.solve(A.T @ A + lam * hf.E + 1e-9 * np.eye(hf.E.shape[0]), A.T @ b)
    return hf


def jets(f, z, x):
    """value, d/dz, d/dx, d2/dz2, d2/dzdx, d2/dx2 of a plan height field f(s = z, t = x)"""
    return [f(z, x, a, b) for a, b in ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2))]


def main():
    car, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    V, F, N, R0, P = skin(car)
    line = Line(LINE_PTS)
    print(f'step line: {line.L:.0f} mm, through the measured points within {line.err:.2f} mm')
    Q0, T0, N0, _ = line.at(np.array([0.0]))
    tip = Q0[0]; sdir = N0[0]       # S: from the tip along the band's end cross-section, rearward (the tail's C side)
    right = P[:, 0] >= -1e-6
    Pr = P[right]
    isC, isO, d, s = classify(Pr, line, tip, sdir)
    print(f'right-half skin vertices {len(Pr)}: C {isC.sum()}, O {isO.sum()}, on the line {(~isC & ~isO).sum()}')

    # O (right): fair cubic over its territory (Kunos outer panel is fair to 0.03-0.04 mm)
    Do = Pr[isO]
    oz = [float(x) for x in os.environ.get('BN_OZ', '1133,1300,1417').split(',') if x]
    ox = [float(x) for x in os.environ.get('BN_OX', '').split(',') if x]
    O = HF(oz, (690.0, 1760.0), ox, (290.0, 660.0), p=5, pt=int(os.environ.get('BN_OPT', 3)))
    fit_rows(O, Do[:, 2], Do[:, 0], Do[:, 1], float(os.environ.get('BN_LAMO', 1e2)))
    ro = O(Do[:, 2], Do[:, 0]) - Do[:, 1]
    print(f'O  {O.ns}x{O.nt} poles  vertices {len(Do)}  rms {np.sqrt(np.mean(ro ** 2)):.3f}  max {np.abs(ro).max():.3f} mm')

    # C: full width, mirror-paired poles; tongue only up to the roll start (NOSE_Z without the nose); G2 rows = O along S
    if NOSE:
        nose = front_face(Pr)
        sel = isC & (Pr[:, 2] < nose['e'](np.abs(Pr[:, 0])) - NOSE_A + 1.0)
    else:
        sel = isC & (Pr[:, 2] < NOSE_Z)
    Dc = Pr[sel]; Dc = np.r_[Dc, Dc * [-1, 1, 1]]          # both halves (Kunos is mirror-exact)
    zk = [float(x) for x in os.environ.get('BN_CZ', '880,960,1040,1250,1450,1650').split(',')]
    xk = [float(x) for x in os.environ.get('BN_CX', '150,300,400,470').split(',')]
    C = HF(zk, (690.0, 1900.0 if NOSE else 1830.0), sorted([-x for x in xk] + xk), (-520.0, 520.0), sym=True, p=5, pt=5)
    ks = np.linspace(-12.0, 60.0, 37)                      # S from 12 mm ahead of the tip (across the band end) to the rear edge
    Sx = tip[0] + ks * sdir[0]; Sz = tip[1] + ks * sdir[1]
    WS = float(os.environ.get('BN_WS', 1e3))
    rows = []
    for (a, b), wgt in (((0, 0), WS), ((1, 0), WS * 1e2), ((0, 1), WS * 1e2), ((2, 0), WS * 1e4), ((1, 1), WS * 1e4), ((0, 2), WS * 1e4)):
        rows.append((Sz, Sx, a, b, O(Sz, Sx, a, b), wgt))
    fit_rows(C, Dc[:, 2], Dc[:, 0], Dc[:, 1], float(os.environ.get('BN_LAMC', 10)), rows)
    rc = C(Dc[:, 2], Dc[:, 0]) - Dc[:, 1]
    print(f'C  {C.ns}x{C.nt} poles  vertices {len(Dc)}  rms {np.sqrt(np.mean(rc ** 2)):.3f}  max {np.abs(rc).max():.3f}  bias {rc.mean():+.3f} mm')
    js = [np.abs(a - b).max() for a, b in zip(jets(C, Sz, Sx), jets(O, Sz, Sx))]
    print('seam S (C - O): value %.4f mm, dz %.5f, dx %.5f, d2 %.2e %.2e %.2e' % tuple(js))
    # step height along the line: C - O at the line (an output: compare with the Kunos table)
    for z_, h_ in () and ((1008, 3.17), (1110, 3.15), (1211, 3.11), (1311, 2.53), (1410, 1.93), (1508, 1.31), (1607, 0.63), (1664, 0.26)):
        x_ = 277.48 + 0.07148 * z_ - 1.274e-5 * z_ ** 2
        print(f'   H at z {z_}: ours {float((C(z_, x_) - O(z_, x_))[0]):5.2f}  Kunos {h_:.2f} mm')
    # slopes across the line at the band edges (+-10 mm) vs Kunos's own rows (rows 1-3 on C, 5-7 on O)
    bad = []
    for z_ in (1008, 1110, 1211, 1311, 1410, 1508, 1607):
        k = np.abs(Pr[:, 2] - z_) < 3
        kc = k & (d > 4) & (d < 17); ko = k & (d < -4) & (d > -17)
        if kc.sum() < 2 or ko.sum() < 2: continue
        gc = np.polyfit(Pr[kc, 0], Pr[kc, 1], 1)[0]; go = np.polyfit(Pr[ko, 0], Pr[ko, 1], 1)[0]
        xl = 277.48 + 0.07148 * z_ - 1.274e-5 * z_ ** 2
        ac = float(C(z_, xl - 10, 0, 1)[0]); ao = float(O(z_, xl + 10, 0, 1)[0])
        hc = float(C(z_, xl - 10)[0]) - np.polyval(np.polyfit(Pr[kc, 0], Pr[kc, 1], 1), xl - 10)
        ho = float(O(z_, xl + 10)[0]) - np.polyval(np.polyfit(Pr[ko, 0], Pr[ko, 1], 1), xl + 10)
        bad.append(max(abs(np.degrees(np.arctan(ac) - np.arctan(gc))), abs(np.degrees(np.arctan(ao) - np.arctan(go)))))
        print(f'   z {z_}: slope across C {np.degrees(np.arctan(ac)):5.2f} (Kunos rows {np.degrees(np.arctan(gc)):5.2f})  O {np.degrees(np.arctan(ao)):5.2f} ({np.degrees(np.arctan(go)):5.2f}) deg;'
              f' height at A {hc:+.2f}, at B {ho:+.2f} mm')
    print(f'   worst slope miss at the band edges: {max(bad):.2f} deg')
    np.savez(os.path.join(out, 'bonnet_fit.npz'), Oc=O.c, Cc=C.c)

    # ---- the step band (right; left = mirror) ----
    band, A_, B_ = step_band(line, C, O)
    # ---- outline (Kunos skin boundary, plan) and the territory polygons ----
    wires = outline_wires(V, R0)
    Sfar = tip + sdir * ((tip[1] - 600.0) / -sdir[1])       # S carried on rearward to z 600 (past the rear edge)
    xz = lambda Pl: [[float(q[1]), float(q[0])] for q in Pl]  # (x, z) -> frame (s = z, t = x)
    mir = lambda Pl: [[q[0], -q[1]] for q in Pl]
    thin = lambda Pl: Pl[np.r_[np.arange(0, len(Pl) - 1, max(1, int(len(Pl) * 5.0 / line.L))), len(Pl) - 1]]   # ~5 mm segments
    A_, B_ = thin(A_), thin(B_)
    # O territory + band (cut from C); at the notch end it follows the band's (slanted) end edge A -> B before turning
    # out at A's z (a constant-z cut from A left a wedge between the band end and O that no face covered)
    # ... and then runs FORWARD along x = B's x: everything outboard of the tongue ahead of the band belongs to O (C kept a
    # flap over O along the lamp-bay front edge: two owners, found by mesh_holes.py)
    polyO = xz(np.r_[A_, [B_[-1]], [[B_[-1, 0], 2100.0], [700.0, 2100.0], [700.0, 600.0], Sfar]])
    polyC = xz(np.r_[B_, [[B_[-1, 0], 2000.0], [200.0, 2000.0], [200.0, 600.0], Sfar]])   # C territory + band (cut from O)
    res = []
    cC = [polyO, mir(polyO)]
    if NOSE:
        roll, cut_c, cut_f = nose_roll(nose, C, Pr, wires)
        cC.append(cut_c)
        res.append(nose['face'](wires, cut_f)); res.append(roll)
    res.append(hf_face('hood:centre', C, wires, cC, maxlen=10.0))
    if os.environ.get('BN_STRIPS', '1') != '0':
        res += edge_strips(car)
    res.append(hf_face('hood:outerR', O, wires, [polyC]))
    res.append(hf_face('hood:outerL', O, [[dict(e, poles=mir(e['poles'])) for e in w] for w in wires], [mir(polyC)], mirror=True))
    for nm, P_ in (('hood:bandR', band['P']), ('hood:bandL', band['P'] * [1, -1, 1])):
        res.append(dict(name=nm, frame=FRAME, du=5, dv=5, nu=6, nv=int(P_.shape[1]), ku=[0.0] * 6 + [1.0] * 6, kv=band['kv'].tolist(),
                        dom=[[0.0, 1.0], [0.0, float(line.L)]], poles=P_.tolist(), own_plane=True,
                        wires=wires if nm.endswith('R') else [[dict(e, poles=mir(e['poles'])) for e in w] for w in wires],
                        maxlen=float(os.environ.get('BN_BANDLEN', 2.5)), fit_p95_mm=0.0, fit_max_mm=0.0))
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    print('saved', os.path.join(out, 'panels_fit.json'))
    return line, C, O


def front_face(Pr):
    """the nose's straight front face: e(x) = plan front edge (Kunos skin row y 639.27, even quartic), height
    h = a(x) + b(x) (z - e(x)) fitted to the face rows (z > e - 26, without the 0.9 mm tip facet), a / b even in x.
    As a B-spline: degree 1 in z (exactly straight), degree 5 in x."""
    X, H, Z = np.abs(Pr[:, 0]), Pr[:, 1], Pr[:, 2]
    fr = (np.abs(H - 639.27) < 0.05) & (X < 352)
    ce = np.polyfit(X[fr] ** 2, Z[fr], 2); e = lambda x: np.polyval(ce, np.asarray(x, float) ** 2)
    fm = (X < 352) & (Z > e(X) - 26) & (H > 639.0)
    bf = lambda z, x: np.c_[np.ones_like(x), x ** 2, x ** 4, z - e(x), (z - e(x)) * x ** 2]
    cf = np.linalg.lstsq(bf(Z[fm], X[fm]), H[fm], rcond=None)[0]
    def f(z, x, *_):
        z, x = np.broadcast_arrays(np.atleast_1d(np.asarray(z, float)), np.atleast_1d(np.asarray(x, float)))
        return bf(z, x) @ cf
    rf = f(Z[fm], X[fm]) - H[fm]
    print(f'nose front face: edge e(x) through {fr.sum()} points (max {np.abs(e(X[fr]) - Z[fr]).max():.2f} mm = Kunos chords),'
          f' slope {np.degrees(np.arctan(cf[3])):.2f} deg, {fm.sum()} vertices rms {np.sqrt(np.mean(rf ** 2)):.3f} max {np.abs(rf).max():.3f} mm')
    def face(wires, cut):
        z0, z1, x1 = 1855.0, 1930.0, 420.0
        xs = np.linspace(-x1, x1, 801); kx = np.r_[[-x1] * 6, np.linspace(-x1, x1, 13)[1:-1], [x1] * 6]; n = len(kx) - 6
        Bx = bas(xs, kx, n, 0, 5); gx = np.array([kx[j + 1:j + 6].mean() for j in range(n)])
        Hc = [np.linalg.lstsq(Bx, f(z_, np.abs(xs)), rcond=None)[0] for z_ in (z0, z1)]
        err = max(np.abs(Bx @ h_ - f(z_, np.abs(xs))).max() for h_, z_ in zip(Hc, (z0, z1)))
        P = np.stack([np.stack([np.full(n, z_), gx, h_], -1) for z_, h_ in zip((z0, z1), Hc)])
        print(f'  front face B-spline: 2 x {n} poles (deg 1 x 5), fit {err * 1000:.2f} um')
        return dict(name='hood:noseface', frame=FRAME, du=1, dv=5, nu=2, nv=n, ku=[z0, z0, z1, z1], kv=kx.tolist(),
                    dom=[[z0, z1], [-x1, x1]], poles=P.tolist(), wires=wires, own_plane=True,
                    cut_polys=[dict(poly=cut, frame=FRAME)], maxlen=4.0, fit_p95_mm=0.0, fit_max_mm=0.0)
    return dict(e=e, f=f, face=face)


def nose_roll(nose, C, Pr, wires, a=None, b=None):
    """G2 roll C -> front face across z = e(x) - a .. e(x) - b (constant width W = a - b). Parameters (u, x),
    z = e(x) - a + u. Height = degree-7 Bernstein in u / W: c0..c2 from C's jets at the start, c5..c7 from the face's
    jets at the end (G2 by construction), c3 / c4 = the straight split of c2..c5 plus one fitted offset each (least
    squares on the Kunos roll vertices). Returns the roll face and the cut polygons for C and the face."""
    a = NOSE_A if a is None else a; b = NOSE_B if b is None else b; W = a - b; e, f = nose['e'], nose['f']
    def coeffs(x):
        zA = e(x) - a; c0, d0, k0 = jet_z(C, zA, x); c7, d7, k7 = jet_z(f, zA + W, x)
        q0, r0, q1, r1 = W * d0, W * W * k0, W * d7, W * W * k7
        c = [c0, c0 + q0 / 7, c0 + 2 * q0 / 7 + r0 / 42, None, None, c7 - 2 * q1 / 7 + r1 / 42, c7 - q1 / 7, c7]
        c[3] = c[2] + (c[5] - c[2]) / 3; c[4] = c[2] + 2 * (c[5] - c[2]) / 3
        return np.array(c)
    bern = lambda t: np.array([comb(7, i) * t ** i * (1 - t) ** (7 - i) for i in range(8)])
    X, H, Z = np.abs(Pr[:, 0]), Pr[:, 1], Pr[:, 2]
    m = (X < 352) & (Z > e(X) - a) & (Z < e(X) - b)
    Bm = bern((Z[m] - e(X[m]) + a) / W); cm = coeffs(X[m])
    h0 = (cm * Bm).sum(0); dl = np.linalg.lstsq(np.c_[Bm[3], Bm[4]], H[m] - h0, rcond=None)[0]
    r = h0 + Bm[3] * dl[0] + Bm[4] * dl[1] - H[m]
    print(f'nose roll: z = e(x) - {a:.0f} .. e(x) - {b:.0f} (W {W:.0f} mm), degree 7, middle offsets {dl[0]:+.2f} / {dl[1]:+.2f} mm;'
          f' {m.sum()} roll vertices rms {np.sqrt(np.mean(r ** 2)):.3f} max {np.abs(r).max():.3f} mm')
    x1 = 420.0; xs = np.linspace(-x1, x1, 1201); cs = coeffs(np.abs(xs)); cs[3] += dl[0]; cs[4] += dl[1]
    Zs = np.stack([e(xs) - a + W * i / 7 for i in range(8)])
    for ni in range(10, 80, 4):
        kx = np.r_[[-x1] * 6, np.linspace(-x1, x1, ni + 2)[1:-1], [x1] * 6]; n = len(kx) - 6; Bx = bas(xs, kx, n, 0, 5)
        Hc = np.linalg.lstsq(Bx, cs.T, rcond=None)[0]; Zc = np.linalg.lstsq(Bx, Zs.T, rcond=None)[0]
        eh, ez = np.abs(Bx @ Hc - cs.T).max(), np.abs(Bx @ Zc - Zs.T).max()
        if eh < 1e-3 and ez < 1e-4: break
    gx = np.array([kx[j + 1:j + 6].mean() for j in range(n)])
    P = np.stack([Zc.T, np.broadcast_to(gx, Zc.T.shape), Hc.T], -1)            # (8, n, 3)
    tt = np.linspace(0, 1, 801); c0 = coeffs(np.zeros(1))[:, 0]; c0[3] += dl[0]; c0[4] += dl[1]
    hz = c0 @ bern(tt); zz = e(0.0) - a + W * tt
    d1 = np.gradient(hz, zz); d2 = np.gradient(d1, zz); kap = -d2 / (1 + d1 ** 2) ** 1.5
    print(f'  roll poles 8 x {n} (deg 7 x 5), coefficient fit {eh * 1000:.2f} um; section at x 0: slope {np.degrees(np.arctan(d1[1])):.1f}'
          f' -> {np.degrees(np.arctan(d1[-2])):.1f} deg, R_min {1 / kap[2:-2].max():.0f} mm, inflection {(kap[2:-2] < -1e-6).any()}')
    roll = dict(name='hood:noseroll', frame=FRAME, du=7, dv=5, nu=8, nv=n, ku=[0.0] * 8 + [W] * 8, kv=kx.tolist(),
                dom=[[0.0, W], [-x1, x1]], poles=P.tolist(), wires=wires, own_plane=True, maxlen=3.0, fit_p95_mm=0.0, fit_max_mm=0.0)
    # cut lines on e(x) - a / e(x) - b: 42 mm segments (chord sag ~0.02 mm). 10 mm segments made Mefisto mesh the
    # centre 4x finer (99k tris, 4 min instead of 25k / 34 s). The outline is behind z 1730 beyond x +-362.
    xx = np.linspace(-420, 420, 21)
    cut_c = np.c_[e(xx) - a, xx].tolist() + [[2100.0, 420.0], [2100.0, -420.0]]
    cut_f = np.c_[e(xx) - b, xx].tolist() + [[1600.0, 420.0], [1600.0, -420.0]]
    return roll, cut_c, cut_f


def edge_strips(car):
    """the skin's edges (research step 11), all Kunos crease regions of GEO_hood_SUB1 built as ruled strips
    (strip_build.py): side chamfers r9/r10 (1.2 mm) -> side returns r2/r3 (13.6 mm); nose chamfer r11 (1.0 mm) -> lip
    r4 (7.3 mm); notch chamfers r12/r13 (1.3 mm, round the R 9.3 mm notch corner: chain strips, corner check waived
    below 2 mm wide) -> lamp-bay walls r5/r6 (14 mm) + tongue walls r7/r8 (12 mm); rear flange r1 (15.7 mm straight
    wall with holding rows: 'straight across'). A side on the skin (crease region 0) = the skin's BUILT edge (every
    face named 'hood:...'); a side on another strip = one curve shared by both; a free side = Kunos vertices.
    The corner fills r14-r27 (< 50 mm2 each) are not strips: later."""
    import strip_build as SB
    V, F, N = PF.load_mesh(car, MESH, raw=True)
    pcs = PF.crease_pieces(V, F, N)
    st = SB.find_strips(V, F, N, pcs, PF.components, PF.boundary_loops, amin=1e-7, corner_free_w=0.002, ruled_inside=True)
    name = lambda nb: None if nb is None else ('hood:' if nb == 0 else (f'hoodnb:r{nb}' if nb in st else None))
    out = []
    for ri in sorted(st):
        s = st[ri]
        for sd in s['sides']:
            for r in [sd] + list(sd.get('runs', [])):
                r['nb_name'] = name(r['nb']); r['nb_strip'] = r['nb'] in st
                r['key'] = 'hoodnb:' + '|'.join(str(x) for x in r['key'])
        if s['mode'] == 'chain' and s['width'] < 0.002:
            s['vctrl_mm'] = 4.0                                # its Kunos-vertex rail turns round the R 9.3 mm notch corner
        out.append(dict(name=f'hoodnb:r{ri}', strip=s, frame=s['frame']))
        nbs = [r['nb'] for sd in s['sides'] for r in (sd.get('runs') or [sd])]
        print(f'hoodnb:r{ri}: STRIP {s["width"] * 1e3:.1f} x {s["length"] * 1e3:.0f} mm ({s["mode"]}), neighbours {nbs}')
    # corner fills (research step 12): every other crease region; FreeCAD snaps its outline onto the built edges
    _, wid = PF.components(V, F); rep = {}
    for i, w in enumerate(wid): rep.setdefault(w, i)
    cf = []
    for ri in range(1, len(pcs)):
        if ri in st: continue
        Fr = pcs[ri]; loops = PF.boundary_loops(Fr, wid)
        if len(loops) != 1: print(f'hoodcf:r{ri}: {len(loops)} outlines - skipped'); continue
        Q = V[[rep[w] for w in loops[0]]] * 1000; Q = np.r_[Q, Q[:1]]
        dq = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
        t = np.r_[np.arange(0, dq[-1], 1.0)]
        R = np.c_[[np.interp(t, dq, Q[:, k]) for k in range(3)]].T
        inner = V[[rep[w] for w in sorted(set(wid[Fr.ravel()]) - set(loops[0]))]] * 1000
        T = V[Fr] * 1000; A = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2
        nrm = N[Fr].mean((0, 1)); nrm /= np.linalg.norm(nrm)
        out.append(dict(name=f'hoodcf:r{ri}', frame=FRAME, corner_fill=dict(outline=R.tolist(), inner=inner.tolist(), area=float(A), normal=nrm.tolist())))
        cf.append(ri)
    print(f'edge strips: {len(st)}; corner fills: {["r%d" % r for r in cf]}')
    return out


def hf_face(name, f, wires, cut_polys, maxlen=6.0, mirror=False):
    P = f.poles()                                           # (ns, nt, 3) = (z, x, h)
    ku, kv = f.ks, f.kt
    if mirror:                                              # x -> -x: poles reversed across t, knots mirrored
        P = P[:, ::-1] * [1, -1, 1]; kv = (-np.asarray(kv))[::-1]
    return dict(name=name, frame=FRAME, du=int(f.p), dv=int(f.pt), nu=int(P.shape[0]), nv=int(P.shape[1]),
                ku=[float(x) for x in ku], kv=[float(x) for x in kv], dom=[[float(ku[0]), float(ku[-1])], [float(kv[0]), float(kv[-1])]],
                poles=P.tolist(), wires=wires, own_plane=True, cut_polys=[dict(poly=cp, frame=FRAME) for cp in cut_polys], maxlen=maxlen,
                fit_p95_mm=0.0, fit_max_mm=0.0)


def outline_wires(V, R0):
    """the skin's boundary loop(s) in plan (s = z, t = x, mm), sides split at corners, each fitted to its polyline
    resampled every 5 mm"""
    _, wid = PF.components(V, R0); rep = {w: i for i, w in enumerate(wid)}
    out = []
    for L in PF.boundary_loops(R0, wid):
        P2 = V[[rep[w] for w in L]][:, [2, 0]]
        ci = PF.vertex_corners(P2, 35.0)
        if len(ci) < 2: ci = [0, len(P2) // 2]
        es = []
        for a, b in zip(ci, ci[1:] + [ci[0] + len(P2)]):
            Q = np.r_[P2, P2][a:b + 1]; dq = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
            tq = np.unique(np.r_[np.arange(0, dq[-1], 0.005), dq]); Qd = np.c_[np.interp(tq, dq, Q[:, 0]), np.interp(tq, dq, Q[:, 1])]
            e = PF.fit_curve2d(Qd, PF.TOL_EDGE, nmax=int(np.clip(dq[-1] / 0.03, 24, 80)))
            es.append(dict(poles=(e['poles'] * 1000).tolist(), knots=e['knots'].tolist(), periodic=False))
        out.append(es)
    out.sort(key=lambda w: -len(w))
    return out[:1]


def step_band(line, C, O, nspan=24, nsamp=4000):
    """G2 band between C (side A, left of the line) and O (side B): plan P(s, t) = A(s) + t (B(s) - A(s)), height =
    quintic Hermite in t of the jets of C at A and O at B (value, d/dt, d2/dt2), all as degree-5 B-splines in s
    (research: vanishing_blend_experiments.md, blend.py). Knot lines of C crossed by A and of O crossed by B go in as
    triple knots (their surfaces are only C2 there)."""
    L = line.L; s = np.linspace(0, L, nsamp)
    Q, T, Nl, kap = line.at(s); w = width_law(s, L, line)
    A = Q + 0.5 * w[:, None] * Nl; B = Q - 0.5 * w[:, None] * Nl            # (x, z)
    dens = 1 + 3.0 * np.sqrt(np.abs(kap)) * np.sqrt(L)
    c = np.r_[0, np.cumsum(0.5 * (dens[1:] + dens[:-1]) * np.diff(s))]
    inner = list(np.interp(np.linspace(0, c[-1], nspan + 1)[1:-1], c, s))
    cross = []
    for P_, f in ((A, C), (B, O)):
        for col, kn in ((1, f.ks), (0, f.kt)):
            for k in np.unique(kn[f.p + 1:-(f.p + 1)] if col == 1 else kn[f.pt + 1:-(f.pt + 1)]):
                for i in np.nonzero(np.diff(np.sign(P_[:, col] - k)))[0]:
                    sc = s[i] + (k - P_[i, col]) / (P_[i + 1, col] - P_[i, col]) * (s[i + 1] - s[i])
                    if 3.0 < sc < L - 3.0: cross.append(sc)
    inner = [k for k in inner if all(abs(k - c_) > 4.0 for c_ in cross)]
    kv = np.r_[[0.0] * 6, sorted(inner + cross * 3), [L] * 6]
    M = dmat(kv, s)
    Aj = np.linalg.lstsq(M, A, rcond=None)[0]; Bj = np.linalg.lstsq(M, B, rcond=None)[0]
    Af, Bf = M @ Aj, M @ Bj; D = Bf - Af; dx, dz = D[:, 0], D[:, 1]
    c0, cz, cx, czz, czx, cxx = jets(C, Af[:, 1], Af[:, 0])
    o0, oz, ox, ozz, ozx, oxx = jets(O, Bf[:, 1], Bf[:, 0])
    q0 = cz * dz + cx * dx; r0 = czz * dz * dz + 2 * czx * dz * dx + cxx * dx * dx
    q1 = oz * dz + ox * dx; r1 = ozz * dz * dz + 2 * ozx * dz * dx + oxx * dx * dx
    Hc = np.c_[c0, c0 + q0 / 5, c0 + 2 * q0 / 5 + r0 / 20, o0 - 2 * q1 / 5 + r1 / 20, o0 - q1 / 5, o0]
    Zj = np.linalg.lstsq(M, Hc, rcond=None)[0]
    n = M.shape[1]; P = np.zeros((6, n, 3))
    for i in range(6):
        XZ = (1 - i / 5) * Aj + (i / 5) * Bj
        P[i, :, 0], P[i, :, 1], P[i, :, 2] = XZ[:, 1], XZ[:, 0], Zj[:, i]       # frame (s = z, t = x, h)
    eA = max(np.abs(Af - A).max(), np.abs(Bf - B).max()); eH = np.abs(M @ Zj - Hc).max()
    H = c0 - o0
    print(f'band: {n} poles along ({len(cross)} triple-knot crossings), offsets fit {eA * 1000:.1f} um, Hermite fit {eH * 1000:.1f} um;'
          f' height C - O at the edges: tip {H[0]:+.3f}, max {H.max():.2f}, notch end {H[-1]:+.3f} mm; width {w.min():.0f}-{w.max():.0f} mm')
    return dict(P=P, kv=kv), Af, Bf


if __name__ == '__main__':
    main()
