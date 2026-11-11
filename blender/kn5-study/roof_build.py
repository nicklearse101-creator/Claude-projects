"""Roof of the AE86 as a master surface + its bands (research: blender/research/reports/Roof surfacing.md).

    python roof_build.py CAR_DIR OUT_DIR

The Kunos roof region (GEO_body crease region above the cant rails) is three things:
- the CROWN: one full-width surface from the rear line (z ~ -0.896) to the windscreen header, a gentle dome whose
  front rolls down progressively (no line there);
- the REAR BAND: a flat ~16 deg strip from the rear line down to the rear edge (crisp line, ~10 deg turn in one row);
- two SIDE BANDS (rear half only, z < -0.517): ~20 deg strips from the side line (row x ~ 0.461, held by loops at
  0.457 / 0.466) out to the C-pillar shoulder. In front of z -0.517 the drip strip (its own Kunos region) takes over.

Every face is a cubic B-spline height field over the car's PLAN (frame: s = z, t = x, h = y), so a trim curve in plan
is a trim curve in every face's parameter space and a shared edge is literally the same 2D curve in both faces.
- Crown: own least squares on the VERTICES only (Kunos facets are chords up to ~1-2.6 mm inside a roof), knots packed
  toward the front roll, mirror-paired poles (symmetric by construction, no centreline seam), third-derivative fairing
  (thin-plate flattens a crown); lambda = largest whose vertex RMS stays near the Kunos vertex noise (~0.1 mm).
- Bands: fitted to their own vertices + the crown (and each other) sampled along the shared edge (G0 rows).
Writes OUT/panels_fit.json for panel_fit_freecad.py (all faces carry the same plan frame).
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path:
    sys.path.append(r'D:\ClaudeData\pylibs')
from scipy.interpolate import BSpline
import panel_fit as PF

FRAME = [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]   # c (m), e1 = z (s), e2 = x (t), w = y (h)
LAM = float(os.environ.get('RF_LAM', 1e2))
OV = 30.0                                                                    # surface overshoot past the outline (mm)


# ---------- B-spline height field h(s, t) with given interior knots ----------
def bas(t, k, n, d=0, p=3):
    out = np.zeros((len(t), n))
    for i in range(n):
        c = np.zeros(n); c[i] = 1; out[:, i] = BSpline(k, c, p)(np.clip(t, k[p], k[n]), nu=d)
    return out


class HF:
    """cubic height field over (s, t) on [s0, s1] x [t0, t1]; sym = mirror-paired poles in t (t0 = -t1)"""
    def __init__(self, s_in, s_dom, t_in, t_dom, sym=False, p=3, pt=None):
        pt = p if pt is None else pt; self.p, self.pt = p, pt
        self.ks = np.r_[[s_dom[0]] * (p + 1), sorted(s_in), [s_dom[1]] * (p + 1)]
        self.kt = np.r_[[t_dom[0]] * (pt + 1), sorted(t_in), [t_dom[1]] * (pt + 1)]
        self.ns, self.nt = len(self.ks) - p - 1, len(self.kt) - pt - 1
        M = np.eye(self.nt)
        if sym:
            M = np.zeros((self.nt, (self.nt + 1) // 2))
            for j in range(self.nt): M[j, min(j, self.nt - 1 - j)] = 1
        self.T = np.kron(np.eye(self.ns), M)
        g, gw = np.polynomial.legendre.leggauss(max(p, pt) + 2)
        def quad(k):
            br = np.unique(k); t = []; w = []
            for a, b in zip(br[:-1], br[1:]): t += list((g + 1) / 2 * (b - a) + a); w += list(gw * (b - a) / 2)
            return np.array(t), np.array(w)
        ts, ws = quad(self.ks); tt, wt = quad(self.kt)
        Ds = [bas(ts, self.ks, self.ns, d, p) for d in range(4)]; Dt = [bas(tt, self.kt, self.nt, d, pt) for d in range(4)]
        G = lambda D, w: D.T @ (w[:, None] * D); E = 0
        for a, b, c in ((3, 0, 1), (2, 1, 3), (1, 2, 3), (0, 3, 1)):      # integral of the third derivatives squared
            E = E + c * np.kron(G(Ds[a], ws), G(Dt[b], wt))
        self.E = self.T.T @ E @ self.T

    def A(self, s, t, ds=0, dt=0):
        s, t = np.atleast_1d(s).astype(float), np.atleast_1d(t).astype(float)
        return np.einsum('ki,kj->kij', bas(s, self.ks, self.ns, ds, self.p), bas(t, self.kt, self.nt, dt, self.pt)).reshape(len(s), -1) @ self.T

    def fit(self, s, t, h, lam, rows=()):
        """least squares on points (s, t, h) + extra rows [(s, t, h, weight)] + lam * third-derivative energy"""
        A = [self.A(s, t)]; b = [h]
        for s_, t_, h_, w_ in rows: A.append(np.sqrt(w_) * self.A(s_, t_)); b.append(np.sqrt(w_) * h_)
        A = np.vstack(A); b = np.concatenate(b)
        self.c = np.linalg.solve(A.T @ A + lam * self.E + 1e-9 * np.eye(self.E.shape[0]), A.T @ b)
        return self

    def __call__(self, s, t, ds=0, dt=0): return self.A(s, t, ds, dt) @ self.c

    def poles(self):
        p, pt = self.p, self.pt; gs = np.array([self.ks[i + 1:i + p + 1].mean() for i in range(self.ns)])
        gt = np.array([self.kt[j + 1:j + pt + 1].mean() for j in range(self.nt)])
        H = (self.T @ self.c).reshape(self.ns, self.nt)
        return np.stack(list(np.meshgrid(gs, gt, indexing='ij')) + [H], -1)


class MappedCrown:
    """the crown as ONE fair surface whose s direction runs from the rear line (s = 0) to the windscreen header
    (s = 1000): s = 1000 (z - zr(x)) / (zf(x) - zr(x)), zr / zf even quartics in x. A plan-aligned grid needs knots
    every ~140 mm to bend round the curved front roll and then ripples (isophote islands); this one is a single span,
    degree 7 along the car (knots at s 500 / 850 for the front roll) x degree 5 across, mirror-paired poles.
    zr, zf are polynomials of degree 4 <= 5, so the mapping is exact in the x basis: the result is a true B-spline
    surface (poles (Z, X, H)) whose rear edge IS the iso line s = 0."""
    def __init__(self, rear_pts, front_pts, P, xa, s_in=(500, 850), lam=1.0, p=7, pt=5):
        self.cr = np.polyfit(rear_pts[:, 1] ** 2, rear_pts[:, 0], 2); self.cf = np.polyfit(front_pts[:, 1] ** 2, front_pts[:, 0], 2)
        self.err_r = np.abs(self.zr(rear_pts[:, 1]) - rear_pts[:, 0]).max(); self.err_f = np.abs(self.zf(front_pts[:, 1]) - front_pts[:, 0]).max()
        self.f = HF(list(s_in), (-30.0, 1060.0), [], (-xa, xa), sym=True, p=p, pt=pt)
        self.f.fit(self.sp(P[:, 0], P[:, 2]), P[:, 0], P[:, 1], lam)
        self.ks, self.kt, self.p, self.pt = self.f.ks, self.f.kt, p, pt
    def zr(self, x): return np.polyval(self.cr, np.asarray(x) ** 2)
    def zf(self, x): return np.polyval(self.cf, np.asarray(x) ** 2)
    def sp(self, x, z): return (np.asarray(z) - self.zr(x)) / (self.zf(x) - self.zr(x)) * 1000.0
    def __call__(self, s, t, ds=0, dt=0):            # plan (s = z, t = x) like HF
        assert ds == 0 and dt == 0
        return self.f(self.sp(t, s), t)
    def poles(self):
        G = self.f.poles(); gs, gt, H = G[:, 0, 0], G[0, :, 1], G[..., 2]
        B = bas(np.linspace(self.kt[0], self.kt[-1], 60), self.kt, self.f.nt, 0, self.pt); xs = np.linspace(self.kt[0], self.kt[-1], 60)
        cr = np.linalg.lstsq(B, self.zr(xs), rcond=None)[0]; cf = np.linalg.lstsq(B, self.zf(xs), rcond=None)[0]
        Z = cr[None, :] + gs[:, None] / 1000.0 * (cf - cr)[None, :]
        return np.stack([Z, np.broadcast_to(gt, Z.shape), H], -1)
    def to_param(self, Q):                            # plan points (s = z, t = x), mm -> crown parameters (s', x)
        return np.c_[self.sp(Q[:, 1], Q[:, 0]), Q[:, 1]]


# ---------- the roof region and its pieces ----------
def roof_region(car):
    V, F, N = PF.load_mesh(car, 'GEO_body'); c = V[F].mean(1)
    R0 = PF.crease_pieces(V, F[c[:, 1] > 1.0], N)[0]             # largest crease region over the cant rails = roof
    return V, R0, N


def pieces(V, R0):
    Vm = V * 1000; T = Vm[R0]
    side = (np.abs(T[..., 0]) > 463) & (T[..., 2] < -515)         # strictly outside the side line (rear half)
    rear = T[..., 2] < -900                                       # strictly behind the rear line
    crown = ~(side | rear).any(1); rb = rear.any(1)
    sb = ~crown & ~rb; cx = T[..., 0].mean(1)
    return dict(crown=R0[crown], rear=R0[rb], sideR=R0[sb & (cx > 0)], sideL=R0[sb & (cx < 0)])


def loops_with_labels(sets, wid):
    """boundary loop of each set (welded ids) and, per loop edge, which other set shares it (None = free edge)"""
    owner = {}
    for k, Fk in sets.items():
        for f in wid[Fk]:
            for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])): owner.setdefault((min(a, b), max(a, b)), set()).add(k)
    out = {}
    for k, Fk in sets.items():
        lo = PF.boundary_loops(Fk, wid); assert len(lo) == 1, (k, [len(l) for l in lo]); L = lo[0]
        lab = []
        for i in range(len(L)):
            a, b = L[i], L[(i + 1) % len(L)]; o = owner[(min(a, b), max(a, b))] - {k}
            lab.append(next(iter(o)) if o else None)
        out[k] = (L, lab)
    return out


def split_runs(L, lab, P2, thr=35.0):
    """loop -> runs of edges with one neighbour; free runs also split at sharp turns. returns [(ids, label)]"""
    n = len(L); cut = set(i for i in range(n) if lab[i] != lab[i - 1])
    corners = PF.vertex_corners(P2[L], thr)
    cut |= set(corners)
    if not cut: cut = {0}
    cut = sorted(cut); runs = []
    for a, b in zip(cut, cut[1:] + [cut[0] + n]):
        ids = [L[i % n] for i in range(a, b + 1)]; runs.append((ids, lab[a]))
    return runs


def jet_z(f, z, x, e=0.5):
    """value, d/dz, d2/dz2 at constant x (central differences; works for HF and MappedCrown alike)"""
    f0, fp, fm = f(z, x), f(z + e, x), f(z - e, x)
    return f0, (fp - fm) / (2 * e), (fp - 2 * f0 + fm) / e ** 2


def line2d(p, q):
    p, q = np.asarray(p, float), np.asarray(q, float)
    return dict(poles=[(p + (q - p) * k / 3).tolist() for k in range(4)], knots=[0, 0, 0, 0, 1, 1, 1, 1], periodic=False)


def rear_roll(crown, rear, side, rear_line_pts, side_line_pts, outline_pts, a, b):
    """the rear line as a G2 ROLL instead of a crease (Kunos shades it as a soft ~45 mm roll: its 10 deg turn sits
    between vertex rows 25 mm apart and the smoothed normals spread it from row z -871 to -917).
    Rear line R(x) = even quartic through the crown/rear and side/rear edges. The roll runs from zB = R - b (on the
    rear band) to zA = R + a (on the crown, or the side band outside the side line). Parameters (u, x), u = z - zB in
    mm (0..W, W = a + b, constant): z is linear in u and a quartic in x -> exact in a degree-5 x basis. Height = quintic
    Hermite in u matching value, d/dz and d2/dz2 of both neighbours at constant x -> G2 along both edges by construction
    (the tangential derivatives follow from the matched values). Split at the side line x = +-X0 (crown | side band at
    zA): centre piece (front = crown) + two corner pieces (front = side band); on x = X0 both use the same rear band
    and crown = side band there (G0 edge), so the pieces meet exactly and the side line's crease fades out across the
    roll to nothing at the rear band. Returns roll faces (json dicts) and the cut polygons for the neighbours."""
    cR = np.polyfit(rear_line_pts[:, 1] ** 2, rear_line_pts[:, 0], 2)
    R = lambda x: np.polyval(cR, np.asarray(x, float) ** 2)
    errR = np.abs(R(rear_line_pts[:, 1]) - rear_line_pts[:, 0])
    W = a + b
    o = np.argsort(side_line_pts[:, 0]); xe = lambda z: np.interp(z, side_line_pts[o, 0], side_line_pts[o, 1])
    X0 = 461.0
    for _ in range(30): X0 = float(xe(R(X0) + a))
    print(f'roll: rear line R(x) even quartic, max {errR.max():.2f} mm off the old edges; a {a:.0f} b {b:.0f} mm; side line meets zA at x {X0:.2f}')

    def coeffs(front, x):
        zA, zB = R(x) + a, R(x) - b
        fA, dA, kA = jet_z(front, zA, x); fB, dB, kB = jet_z(rear, zB, x)
        p0, q0, r0 = fB, W * dB, W * W * kB; p1, q1, r1 = fA, W * dA, W * W * kA
        H = np.c_[p0, p0 + q0 / 5, p0 + 2 * q0 / 5 + r0 / 20, p1 - 2 * q1 / 5 + r1 / 20, p1 - q1 / 5, p1]
        Z = np.c_[[R(x) - b + W * i / 5 for i in range(6)]].T
        return Z, H

    def piece(front, xa, xb, name, sym=False):
        xs = np.linspace(xa, xb, 600); Z, H = coeffs(front, xs)
        for ni in range(0, 40):
            # the rear band's own x knots (cubic, C2 there) as triple knots, so its jets are exact in this basis
            kr = [k_ for k_ in np.unique(rear.kt[4:-4]) if xa + 8 < k_ < xb - 8]   # (one 1.5 mm from an end: ill-posed, huge end poles)
            ki = sorted(set(np.round(np.linspace(xa, xb, ni + 2)[1:-1], 6)) - set(np.round(kr, 6)))
            ki = [k_ for k_ in ki if all(abs(k_ - r_) > 4 for r_ in kr)]
            kx = np.r_[[xa] * 6, sorted(ki + kr * 3), [xb] * 6]; n = len(kx) - 6
            B = bas(xs, kx, n, 0, 5)
            Hc = np.linalg.lstsq(B, H, rcond=None)[0]; Zc = np.linalg.lstsq(B, Z, rcond=None)[0]
            eh, ez = np.abs(B @ Hc - H).max(), np.abs(B @ Zc - Z).max()
            if eh < 1e-3 and ez < 1e-4: break
        gx = np.array([kx[j + 1:j + 6].mean() for j in range(n)])
        P = np.stack([Zc.T, np.broadcast_to(gx, Zc.T.shape), Hc.T], -1)        # (6, n, 3): (z, x, h) frame mm
        print(f'  {name}: x {xa:.1f}..{xb:.1f}, poles 6 x {n} (deg 5 x 5), coefficient fit {eh * 1000:.2f} um, z {ez * 1000:.3f} um')
        return P, kx

    def check(P, ku, kv, front, name, xr):
        """evaluate the built surface on its edges vs the neighbours: G0 (mm) and normal angle (deg)"""
        n = P.shape[1]; Bu = lambda u_, d=0: bas(u_, ku, 6, d, 5); Bv = lambda v_, d=0: bas(v_, kv, n, d, 5)
        xs = np.linspace(xr[0], xr[1], 50); out = []
        for u_, f_ in ((0.0, rear), (W, front)):
            Su = Bu(np.full(1, u_)); Su1 = Bu(np.full(1, u_), 1)
            pt = np.einsum('i,ijk,lj->lk', Su[0], P, Bv(xs)); du_ = np.einsum('i,ijk,lj->lk', Su1[0], P, Bv(xs)); dv_ = np.einsum('i,ijk,lj->lk', Su[0], P, Bv(xs, 1))
            nr = np.cross(du_, dv_); nr /= np.linalg.norm(nr, axis=1)[:, None]; nr *= np.sign(nr[:, 2:])
            h0, dz, _ = jet_z(f_, pt[:, 0], pt[:, 1])
            e = 0.5; dxx = (f_(pt[:, 0], pt[:, 1] + e) - f_(pt[:, 0], pt[:, 1] - e)) / (2 * e)
            nn = np.c_[-dz, -dxx, np.ones_like(dz)]; nn /= np.linalg.norm(nn, axis=1)[:, None]
            ang = np.degrees(np.arccos(np.clip((nr * nn).sum(1), -1, 1)))
            out.append(f'{"rear" if u_ == 0 else "front"} G0 {np.abs(pt[:, 2] - h0).max() * 1000:.1f} um, normals {ang.max():.4f} deg (at x {xs[np.argmax(ang)]:.0f}; p90 {np.percentile(ang, 90):.4f})')
        print(f'  {name} edges: ' + '; '.join(out))

    faces = []
    PC, kxC = piece(crown, -X0, X0, 'rollC'); ku = [0.0] * 6 + [W] * 6
    check(PC, np.array(ku), kxC, crown, 'rollC', (-X0, X0))
    wC = [line2d((0, -X0), (0, X0)), line2d((0, X0), (W, X0)), line2d((W, X0), (W, -X0)), line2d((W, -X0), (0, -X0))]
    faces.append(dict(name='roof:rollC', frame=FRAME, du=5, dv=5, dom=[[0.0, W], [-X0, X0]], nu=6, nv=PC.shape[1], ku=ku, kv=kxC.tolist(),
                      poles=PC.tolist(), wires=[wC], fit_p95_mm=0.0, fit_max_mm=0.0))
    # corner pieces: front = side band; outer end trimmed on the roof outline (free edges), drawn in (u, x)
    X1 = float(outline_pts[:, 1].max() + 12)
    PR, kxR = piece(side, X0, X1, 'rollR'); check(PR, np.array(ku), kxR, side, 'rollR', (X0, X0 + 25))
    m = (outline_pts[:, 0] > R(491.0) - b - 25) & (outline_pts[:, 0] < R(491.0) + a + 25)
    cz = np.polyfit(outline_pts[m, 0], outline_pts[m, 1], 2); xo = lambda z: np.polyval(cz, z)
    print(f'  outline at the corner: x = quadratic in z, max {np.abs(xo(outline_pts[m, 0]) - outline_pts[m, 1]).max():.2f} mm over {m.sum()} points')
    us = np.linspace(0, W, 40); xq = np.full_like(us, 491.0)
    for _ in range(20): xq = xo(R(xq) - b + us)
    g = PF.fit_curve2d(np.c_[us, xq] / 1000.0, 0.002e-3)
    wo = dict(poles=(g['poles'] * 1000).tolist(), knots=g['knots'].tolist(), periodic=False)
    wR = [line2d((0, X0), (0, xq[0])), wo, line2d((W, xq[-1]), (W, X0)), line2d((W, X0), (0, X0))]
    faces.append(dict(name='roof:rollR', frame=FRAME, du=5, dv=5, dom=[[0.0, W], [X0, X1]], nu=6, nv=PR.shape[1], ku=ku, kv=kxR.tolist(),
                      poles=PR.tolist(), wires=[wR], fit_p95_mm=0.0, fit_max_mm=0.0))
    PL = PR[:, ::-1].copy(); PL[..., 1] *= -1; kxL = (-kxR[::-1]).tolist()
    mir = lambda e: dict(e, poles=[[p_[0], -p_[1]] for p_ in e['poles']])
    faces.append(dict(name='roof:rollL', frame=FRAME, du=5, dv=5, dom=[[0.0, W], [-X1, -X0]], nu=6, nv=PL.shape[1], ku=ku, kv=kxL,
                      poles=PL.tolist(), wires=[[mir(e) for e in wR]], fit_p95_mm=0.0, fit_max_mm=0.0))
    # centre / corner meeting line x = X0: same rear band, crown = side band there
    zz = np.linspace(R(X0) - b, R(X0) + a, 30); hc = PC[:, -1, 2]; hr = PR[:, 0, 2]
    print(f'  centre/corner join at x {X0:.1f}: pole column gap {np.abs(hc - hr).max() * 1000:.1f} um')
    # neighbours cut back to the roll's edges (dense plan polylines on the exact edge curves)
    xx = np.linspace(-700, 700, 141)                     # 10 mm segments: chord sag on R(x) ~3 um (1 mm: crown meshing 8 min)
    cut_front = [{'poly': np.c_[R(xx) + a, xx].tolist() + [[R(700) + a - 400, 700], [R(-700) + a - 400, -700]], 'frame': FRAME}]
    cut_rear = [{'poly': np.c_[R(xx) - b, xx].tolist() + [[R(700) - b + 400, 700], [R(-700) - b + 400, -700]], 'frame': FRAME}]
    return faces, dict(crown=cut_front, sideR=cut_front, sideL=cut_front, rear=cut_rear), dict(R=R, a=a, b=b, X0=X0)


def neighbour_strips(car):
    """the roof's neighbours: every one is a thin Kunos return 2-4 mm wide (windscreen header, the two drip strips,
    the two rear header strips, the small corners at the C-pillar tops). Built with strip_build.py: a side on the
    roof = the roof's own BUILT edge (FreeCAD stage samples it), so the join is exact; a side on a strip is one curve
    shared by both; a side on something not built here (hatch surround, gutter) = fitted to the Kunos vertices.
    Strips touching the roof + strips touching those. Names 'roofnb:rN' (N = crease piece of GEO_body above y 1.0,
    same numbering as the roof region = piece 0); the roof side's nb_name is the prefix 'roof:' = every roof face."""
    import strip_build as SB
    V, F, N = PF.load_mesh(car, 'GEO_body'); c = V[F].mean(1); Fs = F[c[:, 1] > 1.0]
    pcs = PF.crease_pieces(V, Fs, N)
    st = SB.find_strips(V, Fs, N, pcs, PF.components, PF.boundary_loops, amin=1e-5)
    def nbs(s): return {r['nb'] for sd in s['sides'] for r in (sd.get('runs') or [sd])}
    keep = {ri for ri, s in st.items() if 0 in nbs(s)}
    keep |= {ri for ri, s in st.items() if nbs(s) & keep}
    out = []
    def name(nb): return None if nb is None else ('roof:' if nb == 0 else f'roofnb:r{nb}')
    for ri in sorted(keep):
        s = st[ri]
        for sd in s['sides']:
            for r in [sd] + list(sd.get('runs', [])):
                r['nb_name'] = name(r['nb']); r['nb_strip'] = r['nb'] in st
                r['key'] = 'roofnb:' + '|'.join(str(x) for x in r['key'])
            # a side on a region not built here (and not a strip) has no built edge: Kunos vertices
            for r in [sd] + list(sd.get('runs', [])):
                if r['nb'] not in (None, 0) and r['nb'] not in st: r['nb_name'] = None
        out.append(dict(name=f'roofnb:r{ri}', strip=s, frame=s['frame']))
        print(f'roofnb:r{ri}: STRIP {s["width"] * 1e3:.1f} x {s["length"] * 1e3:.0f} mm ({s["mode"]}), neighbours {sorted(map(str, nbs(s)))}')
    return out


def main():
    car, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    V, R0, N = roof_region(car)
    sets = pieces(V, R0)
    _, wid = PF.components(V, R0)
    Vm = V * 1000
    print('roof region', len(R0), 'faces; pieces', {k: len(v) for k, v in sets.items()})
    P2 = V[:, [2, 0]]                                             # plan (s, t) in metres, per raw vertex index
    W2 = np.zeros((wid.max() + 1, 2)); W2[wid] = P2               # per welded id
    lw = loops_with_labels(sets, wid)
    edges = {}                                                    # key -> fitted 2D curve (metres), shared by both faces
    wires = {}
    for k, (L, lab) in lw.items():
        es = []
        for ids, nb in split_runs(L, lab, W2):
            key = (tuple(sorted((k, nb))) if nb else (k,), min(ids[0], ids[-1]), max(ids[0], ids[-1]))
            if key in edges:
                e = edges[key]; rev = e['ids'][0] != ids[0]
            else:
                # fitted to the side's polyline resampled every 5 mm (as panel_fit does): with only the vertices (50 mm
                # apart along the drip edge) the curve wiggled +-2 mm between them and the drip strip could not use it
                Q = W2[ids]; dq = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
                tq = np.unique(np.r_[np.arange(0, dq[-1], 0.005), dq]); Qd = np.c_[np.interp(tq, dq, Q[:, 0]), np.interp(tq, dq, Q[:, 1])]
                e = PF.fit_curve2d(Qd, PF.TOL_EDGE, nmax=int(np.clip(dq[-1] / 0.03, 24, 80))); e['ids'] = ids; edges[key] = e; rev = False
            P_ = e['poles'][::-1] if rev else e['poles']
            es.append(dict(poles=(P_ * 1000).tolist(), knots=(1 - e['knots'][::-1] if rev else e['knots']).tolist(),
                           periodic=False, nb=nb, err_mm=e['err'] * 1000, curve=P_))
        wires[k] = es
        print(f'{k:6s} outline: {len(es)} sides', [f"{e['nb'] or 'free'}:{e['err_mm']:.2f}" for e in es])

    def verts(k): u = np.unique(wid[sets[k]]); return Vm[[np.where(wid == w)[0][0] for w in u]]
    HOLD = float(os.environ.get('RF_HOLD', 0.0))
    def data_verts(k):
        """the face's vertices without Kunos HOLDING LOOPS: inner rows within HOLD mm (plan) of the outline. They sit on
        the tight roll Kunos uses to make a line look crisp, not on the face, and would bend the face's edge
        (crown: 12 deg at the side line instead of ~7, 3-5 mm bulge over the 146 mm chord inside it)"""
        u = np.unique(wid[sets[k]]); Lk = set(lw[k][0]); Pb = W2[list(Lk)] * 1000
        keep = [w for w in u if w in Lk or np.linalg.norm(Pb - W2[w] * 1000, axis=1).min() > HOLD]
        return Vm[[np.where(wid == w)[0][0] for w in keep]]
    def edge_samples(k, nb, n=60):
        """points along the shared edge(s) of face k with neighbour nb, in plan mm"""
        pts = []
        for e in wires[k]:
            if e['nb'] != nb: continue
            kv = np.array(e['knots']); Pm = np.array(e['poles']); np_ = len(Pm)
            u = np.linspace(0, 1, n); B = PF.basis(u, kv, np_); pts.append(B @ Pm)
        return np.vstack(pts) if pts else np.zeros((0, 2))

    faces = {}
    # 1. crown: the master surface
    Pc = data_verts('crown'); print('crown data', len(Pc), 'of', len(verts('crown')), 'vertices (holding loops left out)'); xa = np.abs(Pc[:, 0]).max() + OV
    if os.environ.get('RF_PLAN') == '1':             # old plan-grid crown (ripples; kept for comparison)
        crown = HF([-840, -700, -560, -420, -280, -140, 0, 70, 110, 135], (Pc[:, 2].min() - OV, Pc[:, 2].max() + OV),
                   [-300, -150, 0, 150, 300], (-xa, xa), sym=True).fit(Pc[:, 2], Pc[:, 0], Pc[:, 1], LAM)
    else:
        Lc = np.array(lw['crown'][0]); Q = W2[Lc] * 1000                      # crown outline in plan (s = z, t = x)
        crown = MappedCrown(Q[Q[:, 0] < -880], Q[Q[:, 0] > 90], Pc, xa)
        print(f'crown: mapped single span deg {crown.p}x{crown.pt}; rear line / front edge as even quartics: max {crown.err_r:.2f} / {crown.err_f:.2f} mm')
    faces['crown'] = crown
    # 2. rear band: own vertices + the crown along the rear line (G0 rows)
    Pr = verts('rear'); xr = np.abs(Pr[:, 0]).max() + OV; G = edge_samples('rear', 'crown')
    rear = HF([], (Pr[:, 2].min() - OV, Pr[:, 2].max() + OV), [-460, -420, -360, -240, 0, 240, 360, 420, 460], (-xr, xr), sym=True)
    rear.fit(Pr[:, 2], Pr[:, 0], Pr[:, 1], 1e0, rows=[(G[:, 0], G[:, 1], crown(G[:, 0], G[:, 1]), 100.0)])
    faces['rear'] = rear
    # 3. side bands: own vertices + crown along the side line + rear band along their rear edge (G0 rows); L = mirror of R
    Ps = verts('sideR'); G1 = edge_samples('sideR', 'crown'); G2 = edge_samples('sideR', 'rear')
    side = HF([-875, -850, -800, -720, -620], (Ps[:, 2].min() - OV, Ps[:, 2].max() + OV), [], (Ps[:, 0].min() - OV, Ps[:, 0].max() + OV))
    side.fit(Ps[:, 2], Ps[:, 0], Ps[:, 1], 1e0, rows=[(G1[:, 0], G1[:, 1], crown(G1[:, 0], G1[:, 1]), 100.0),
                                                     (G2[:, 0], G2[:, 1], rear(G2[:, 0], G2[:, 1]), 100.0)])
    faces['sideR'] = side
    # 4. the rear line as a G2 roll (RF_ROLL=0: the old crisp line)
    roll, cuts = [], {}
    if os.environ.get('RF_ROLL', '1') != '0':
        rl = np.vstack([edge_samples('rear', nb) for nb in ('crown', 'sideR', 'sideL')])
        ol = np.vstack([edge_samples(k, None) for k in ('sideR', 'rear')]); ol = ol[ol[:, 1] > 470]
        roll, cuts, _ = rear_roll(crown, rear, side, rl, edge_samples('crown', 'sideR'), ol,
                                  float(os.environ.get('RF_ROLL_A', 25)), float(os.environ.get('RF_ROLL_B', 21)))

    res = []
    for k in ('crown', 'rear', 'sideR', 'sideL'):
        f = faces.get(k)
        if k == 'sideL':                                          # exact mirror of the right band: t -> -t
            P = faces['sideR'].poles()[:, ::-1].copy(); P[..., 1] *= -1; f = faces['sideR']
            ku, kv = f.ks, -f.kt[::-1]
        else:
            P = f.poles(); ku, kv = f.ks, f.kt
        # vertex residuals of this face's own data
        D = verts(k); fr = faces['sideR'] if k == 'sideL' else f
        r = (fr(D[:, 2], -D[:, 0] if k == 'sideL' else D[:, 0]) - D[:, 1])
        if os.environ.get('RF_DEBUG'):
            for i in np.argsort(-np.abs(r))[:8]: print(f'      {k} worst: x {D[i, 0]:6.1f} y {D[i, 1]:7.1f} z {D[i, 2]:7.1f}  res {r[i]:+.3f}')
        # seam G0 against each neighbour (heights along the shared edges)
        seams = {}
        for e in wires[k]:
            if e['nb'] and e['nb'] in faces or e['nb'] == 'sideL':
                G = edge_samples(k, e['nb']); g = faces.get(e['nb'], faces['sideR'])
                sgn = -1 if e['nb'] == 'sideL' else 1
                hk = fr(G[:, 0], (-G[:, 1]) if k == 'sideL' else G[:, 1]); hn = g(G[:, 0], sgn * G[:, 1])
                seams[e['nb']] = float(np.abs(hk - hn).max())
        print(f'{k:6s} poles {P.shape[0]}x{P.shape[1]}  vertices {len(D):3d}  rms {np.sqrt(np.mean(r ** 2)):.3f}  max {np.abs(r).max():.3f}  bias {r.mean():+.3f} mm'
              f'  seams (max height gap, mm) ' + ' '.join(f'{a}:{b:.3f}' for a, b in seams.items()))
        wk = [dict(poles=e['poles'], knots=e['knots'], periodic=False) for e in wires[k]]
        if isinstance(f, MappedCrown):                # trim curves in the crown's own parameters (s', x)
            wk = []
            for e in wires[k]:
                Pm = np.array(e['poles']); kv_ = np.array(e['knots']); Q = PF.basis(np.linspace(0, 1, 400), kv_, len(Pm)) @ Pm
                g = PF.fit_curve2d(f.to_param(Q) / 1000.0, 0.005e-3, nmax=60)
                wk.append(dict(poles=(g['poles'] * 1000).tolist(), knots=g['knots'].tolist(), periodic=False))
                print(f'      crown trim curve in (s1, x): {len(g["poles"])} poles, err {g["err"] * 1e6:.1f} um')
        res.append(dict(name=f'roof:{k}', frame=FRAME, du=int(getattr(f, 'p', 3)), dv=int(getattr(f, 'pt', 3)), dom=[[float(ku[0]), float(ku[-1])], [float(kv[0]), float(kv[-1])]],
                        nu=int(P.shape[0]), nv=int(P.shape[1]), ku=[float(x) for x in ku], kv=[float(x) for x in kv], poles=P.tolist(),
                        wires=[wk],
                        fit_p95_mm=float(np.percentile(np.abs(r), 95)), fit_max_mm=float(np.abs(r).max())))
        if cuts.get(k): res[-1]['cut_polys'] = cuts[k]
        if k == 'crown': res[-1]['maxlen'] = 12.0          # big gentle face: coarser display mesh (was 6 min to mesh)
    res += roll
    if os.environ.get('RF_STRIPS', '1') != '0':
        res += neighbour_strips(car)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'roof_data.npz'), V=Vm[np.unique(R0)], R0=R0)
    print('saved', os.path.join(out, 'panels_fit.json'))


if __name__ == '__main__':
    main()
