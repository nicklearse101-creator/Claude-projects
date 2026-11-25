"""AE86 bumpers as swept bands (first build: the rear bumper's main profile).

    python bumper_build.py CAR_DIR OUT_DIR [rear]

A Kunos bumper (GEO_rearbumper) is one profile swept along a U-shaped plan line: from one wheel arch round the tail to
the other. Its crease pieces are BANDS along the bumper: every vertical section square to the plan line crosses them in
the same order (rear, top to bottom: [inner lip r5, step r17: interrupted at x 0.34-0.55, a strip later] top r1, edge roll r12, upper face r0, groove r21 + r20,
lower face r0, lower slope r3). Below r3 the section changes (centre recess vs side parts): those pieces are built
separately (generic faces for now).

Build:
- spine: the plan line of the top edge (r1 / r12 shared vertices), one symmetric smoothing curve in plan (x, z);
- stations every STEP along it, vertical planes square to it; each section chained, split into runs by crease piece,
  matched to the band sequence (either direction); each run resampled evenly in arc length between its two crease
  points (consecutive bands share those points exactly);
- left half (x >= 0) only, mirrored: one symmetric set of rows; smoothed along the spine in each row's own frame
  (hatch_build.smooth_rows_local: a turn stays exact) and evaluated evenly, centre row once;
- split back into one grid face per band ('rbump:bK', structured mesh in the FreeCAD stage). Shared rows -> the bands
  meet within the FreeCAD approximation tolerance (0.02 mm).
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(r'D:\ClaudeData\pylibs') and r'D:\ClaudeData\pylibs' not in sys.path:
    sys.path.append(r'D:\ClaudeData\pylibs')
import panel_fit as PF

MIR = np.array([-1.0, 1.0, 1.0])
BRIDGE = 0.0          # m: join section chains across an opening in a band (spec 'bridge')
YCOLS = ()            # band indices whose columns are spaced by height (spec 'ycols')
SPEC = dict(rear=dict(mesh='GEO_rearbumper', bands=[1, 12, 0, 21, 20, 0, 3], spine_pair=(1, 12), anchor_band=2, name='rbump',
                      centre_z=-1.55, mm_per_col=5.0),
            # front: GEO_frontbumper_SUB2 (the skin; SUB0 / SUB1 = the badge + slot inserts, later). bands=[]: every
            # piece through others() (faces / strips / wrap splits) - the per-piece baseline before any sweep
            front=dict(mesh='GEO_frontbumper_SUB2', bands=[0, 1, 13], spine_pair=(1, 14), anchor_band=0, name='fbump',
                       centre_z=1.55, zdir=1, mm_per_col=5.0, bridge=0.15, trim_shrink=0.85,   # ycols=(0,) dropped 25 Nov (arc-length columns: 94.1 -> 95.1 %)
                       extra=['GEO_frontbumper_SUB0', 'GEO_frontbumper_SUB1'], pn=True, extend=0.12, lam=1e-5,
                       # Kunos splits one surface into differently numbered pieces along the bumper: the lip r15
                       # carries on as r68 past x 676; r8 (the face's top, fading crease to r0) ends at x 674; r65 / r99
                       # (a 5 mm line beside the plate recess) and r75 are bits of the face
                       # soft boundaries (piece edges along big triangles over smooth / flat skin, wandering from
                       # station to station: r1 / r14 on the flat top 30-77 mm, r0 / r15 low on the face 8-31 mm) are
                       # merged into one band; bands keep only the real creases
                       alias={68: 15, 15: 0, 14: 1, 8: 0, 65: 0, 99: 0, 75: 0}))

# tail panel: GEO_body behind the hatch (run with PF_NOHATCH=1 PF_CLIP=-0.45,0.45,0.45,0.85,-2.2,-1.95): the raised plate
# panel r0 + the band under it r1 swept along x (straight); the rest per piece
SPEC['tail'] = dict(mesh='GEO_body', bands=[0], spine_pair=(1, 0), spine_bottom=0, anchor_band=0, name='tail', centre_z=-1.5,
                    mm_per_col=5.0, ycols=(0,), trim_shrink=0.85)


def pieces(V, F, N, sp):
    """crease pieces with the spec's alias pieces merged into their band piece (the alias left empty: indices and
    names of every other piece unchanged)"""
    pcs = PF.crease_pieces(V, F, N)
    al = dict(sp.get('alias', {}))
    def tgt(a):
        while a in al: a = al[a]
        return a
    for a in al:
        t = tgt(a)
        if len(pcs[a]): pcs[t] = np.vstack([pcs[t], pcs[a]]); pcs[a] = np.zeros((0, 3), int)
    return pcs
STEP = float(os.environ.get('BB_STEP', 0.015))


def spine(V, pcs, pair, centre_z, step=0.001, zdir=-1):
    """plan line (x, z) of the edge shared by crease pieces pair, left half (x >= 0) from the centre out, as a dense
    3D polyline at y = 0 (m) with arc lengths; symmetric by construction (mirrored points, fit, left half)"""
    import strip_build as SB
    key = lambda X: np.round(X / 2e-5).astype(np.int64)
    A = {tuple(k) for k in key(V[np.unique(pcs[pair[0]])])}
    X = np.array([v for v, k in zip(V[np.unique(pcs[pair[1]])], key(V[np.unique(pcs[pair[1]])])) if tuple(k) in A])
    X = np.unique(np.round(X, 6), axis=0)
    X = np.r_[X, X * MIR]
    ang = np.arctan2(X[:, 0], zdir * (X[:, 2] - centre_z))      # 0 at the tail (zdir -1) / nose (+1) centre, + towards x > 0
    X = X[np.argsort(ang)]; P = np.c_[X[:, 0], np.zeros(len(X)), X[:, 2]]
    a = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    f = SB.fit_graph(a, P, [0, a[-1]], tol=1e-3, nmax=int(np.clip(a[-1] / 0.05, 4, 60)), mu=1e-4)
    S = SB.eval_graph(f, np.linspace(0, a[-1], int(a[-1] / step) + 1))
    S = (S + (S * MIR)[::-1]) / 2                               # exact symmetry
    i0 = int(np.argmin(np.abs(S[:, 0])))
    L = S[i0:]; L[0, 0] = 0.0
    return L, np.r_[0, np.cumsum(np.linalg.norm(np.diff(L, axis=0), axis=1))], f['err']


def _runs(V, T, Lb, cen, o, t):
    import sweep_build as SW
    from blend_build import _section
    m = np.linalg.norm((cen - o)[:, [0, 2]], axis=1) < 0.25
    segs, tri = _section(T[m], o, t)
    if len(segs) < 5: return None, None
    Q, tr = SW._chain_near(segs, tri, o)
    lab = Lb[np.nonzero(m)[0][tr]]
    if BRIDGE > 0:
        # an opening in a band (the front bumper's plate recess, left out of the bands): the section breaks there;
        # chains whose end lies within BRIDGE of ours on the SAME band piece are joined straight across the gap
        rest = np.ones(len(segs), bool)
        kk = {tuple(np.round(q / 1e-6).astype(np.int64)) for q in Q}
        for i_ in range(len(segs)):                         # used: either end on our chain (else re-chained: doubled back)
            if tuple(np.round(segs[i_][0] / 1e-6).astype(np.int64)) in kk or tuple(np.round(segs[i_][1] / 1e-6).astype(np.int64)) in kk: rest[i_] = False
        for _ in range(4):
            idx = np.nonzero(rest)[0]
            if len(idx) < 2: break
            best = None
            for end in (0, -1):
                d_ = np.minimum(np.linalg.norm(segs[idx, 0] - Q[end], axis=1), np.linalg.norm(segs[idx, 1] - Q[end], axis=1))
                j_ = int(np.argmin(d_))
                if d_[j_] < BRIDGE and (best is None or d_[j_] < best[0]): best = (d_[j_], end, idx[j_])
            if best is None: break
            _, end, k_ = best
            Q2, tr2 = SW._chain_near(segs[rest], tri[rest], segs[k_].mean(0))
            lab2 = Lb[np.nonzero(m)[0][tr2]]
            # the chord must carry both chains straight on (no doubling back onto a side chain)
            def _ok(Pa, Pb):                                     # Pa ends at the gap (last point), Pb starts there
                g_ = Pb[0] - Pa[-1]; gl = np.linalg.norm(g_)
                if gl < 1e-6: return True
                ta = Pa[-1] - Pa[max(len(Pa) - 4, 0)]; tb = Pb[min(3, len(Pb) - 1)] - Pb[0]
                ta /= max(np.linalg.norm(ta), 1e-12); tb /= max(np.linalg.norm(tb), 1e-12)
                return ta @ g_ / gl > 0.5 and tb @ g_ / gl > 0.5
            if end == 0:                                        # attach before Q: Q2 must end at our start
                if np.linalg.norm(Q2[0] - Q[0]) < np.linalg.norm(Q2[-1] - Q[0]): Q2, tr2, lab2 = Q2[::-1], tr2[::-1], lab2[::-1]
                if lab2[-1] != lab[0] or not _ok(Q2, Q): break
                Q = np.r_[Q2, Q]; tr = np.r_[tr2, tr2[-1:], tr]; lab = np.r_[lab2, lab2[-1:], lab]   # + the chord's label
            else:
                if np.linalg.norm(Q2[-1] - Q[-1]) < np.linalg.norm(Q2[0] - Q[-1]): Q2, tr2, lab2 = Q2[::-1], tr2[::-1], lab2[::-1]
                if lab2[0] != lab[-1] or not _ok(Q, Q2): break
                Q = np.r_[Q, Q2]; tr = np.r_[tr, tr[-1:], tr2]; lab = np.r_[lab, lab[-1:], lab2]
            kk = {tuple(np.round(q / 1e-6).astype(np.int64)) for q in Q2}
            sub = np.nonzero(rest)[0]
            for i_ in sub:
                if tuple(np.round(segs[i_][0] / 1e-6).astype(np.int64)) in kk or tuple(np.round(segs[i_][1] / 1e-6).astype(np.int64)) in kk: rest[i_] = False
    runs = []
    for k, l in enumerate(lab):
        if not runs or runs[-1][0] != l: runs.append([l, k, k])
        else: runs[-1][2] = k
    return Q, runs


def _match(seq, sq):
    for rev in (False, True):
        q = sq[::-1] if rev else sq
        for j in range(len(seq) - len(q) + 1):
            if seq[j:j + len(q)] == q: return rev, j
    return None


def station_rows(V, pcs, bands, Sp, arc, step, ncol, verbose=True, anchor_band=2, s_max=None, offsets=None, s_full_max=None, yfix=None):
    """rows (n_st, sum(ncol) - len(bands) + 1, 3) of the band sequence at stations every `step` along the left half's
    spine (arc positions returned too); stations whose section does not hold the full sequence are skipped.
    With `offsets` (per band: the columns' arc offsets from the band's crease on the anchor side, m) the stations past
    the last full one (up to s_max, towards the arch) give PARTIAL rows: the longest run of consecutive bands holding
    the anchor band is sampled at those fixed offsets (a band cut short by the arch outline is not squeezed: its
    columns past the outline are NaN, extrapolated later and trimmed away)."""
    Fb = np.vstack([pcs[b] for b in sorted(set(bands))]); Lb = np.concatenate([[b] * len(pcs[b]) for b in sorted(set(bands))])
    T = V[Fb]; cen = T.mean(1); yb = float(np.median(V[np.unique(pcs[bands[0]])][:, 1]))
    ncs = int(sum(ncol) - len(bands) + 1); c0 = np.cumsum([0] + [n - 1 for n in ncol])
    rows, arcs, skipped, partial = [], [], [], 0
    s_end = arc[-1] if s_max is None else s_max
    for s in np.arange(0.0, s_end + 1e-9, step):
        if s <= arc[-1]:
            i = int(np.clip(np.searchsorted(arc, s), 1, len(Sp) - 2))
            o = Sp[i].copy(); t = Sp[min(i + 1, len(Sp) - 1)] - Sp[i - 1]
        else:                                                            # past the spine's end: straight on
            t = Sp[-1] - Sp[-3]; o = Sp[-1] + (s - arc[-1]) * t / np.linalg.norm(t)
        t = t.copy(); t[1] = 0; t /= np.linalg.norm(t); o = o.copy(); o[1] = yb
        Q, runs = _runs(V, T, Lb, cen, o, t)
        if Q is None: skipped.append(s); continue
        seq = [r[0] for r in runs]
        hit = _match(seq, bands)
        if hit is not None and (s_full_max is None or s <= s_full_max + 1e-9):
            rev, j = hit
            rr = runs[j:j + len(bands)]
            if rev: rr = rr[::-1]
            row = []
            for k, (l, a, b) in enumerate(rr):
                P = Q[a:b + 2]
                if rev: P = P[::-1]
                if k in YCOLS:      # a near-vertical band with horizontal feature lines (the front bumper's face):
                    # columns spaced by HEIGHT, so a line at constant height falls on the same column at every station
                    # (by arc length the recess chord / molding moved the columns: vertical ripples, 18 Nov)
                    d = np.r_[0, np.cumsum(np.abs(np.diff(P[:, 1])) + 1e-6)]
                else:
                    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
                q = np.linspace(0, d[-1], ncol[k])
                R = np.c_[[np.interp(q, d, P[:, c]) for c in range(3)]].T
                row.append(R if k == 0 else R[1:])
            row = np.vstack(row)
            if len(bands) == 1 and row[0, 1] < row[-1, 1]: row = row[::-1]   # one band: no sequence fixes its direction (top first)
            rows.append(row); arcs.append(s); continue
        if offsets is None or not arcs or s < arcs[-1]: skipped.append(s); continue
        # partial: the longest run of consecutive bands holding the anchor band
        best = None
        for k0 in range(anchor_band + 1):
            for k1 in range(len(bands) - 1, anchor_band - 1, -1):
                if k1 - k0 + 1 < 2: continue
                h = _match(seq, bands[k0:k1 + 1])
                if h is not None and (best is None or k1 - k0 > best[1] - best[0]): best = (k0, k1, h)
        if best is None: break
        k0, k1, (rev, j) = best
        rr = runs[j:j + k1 - k0 + 1]
        if rev: rr = rr[::-1]
        row = np.full((ncs, 3), np.nan)
        for kk, (l, a, b) in enumerate(rr):
            k = k0 + kk
            P = Q[a:b + 2]
            if rev: P = P[::-1]
            d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
            free_end = (k == k0 and k < anchor_band) or (k == k1 and k > anchor_band)   # cut by the outline here?
            if k < anchor_band:                                             # above the anchor: measured from its lower end
                q = d[-1] - offsets[k][::-1]
            else: q = offsets[k]
            if not free_end: q = np.linspace(0, d[-1], ncol[k])           # both creases present: evenly, as the full rows
            if yfix is not None and k in yfix:
                # a band whose columns are spaced by height (the front face): the same HEIGHTS as the last full row,
                # so its feature lines run on along the same columns; heights the section no longer reaches (the flare
                # took them) are NaN, carried on and trimmed by the band's outline (19 Nov)
                dy = np.r_[0, np.cumsum(np.abs(np.diff(P[:, 1])) + 1e-6)]
                yq = np.abs(np.asarray(yfix[k]) - P[0, 1]); okq = (np.sign(np.asarray(yfix[k]) - P[0, 1]) == np.sign(P[-1, 1] - P[0, 1])) | (yq < 1e-6)
                qq = np.where(okq & (yq <= dy[-1] + 1e-6), yq, np.nan)
                R = np.c_[[np.interp(qq, dy, P[:, c]) for c in range(3)]].T; R[np.isnan(qq)] = np.nan
                row[c0[k]:c0[k] + ncol[k]] = R; continue
            ok = (q >= -1e-6) & (q <= d[-1] + 1e-6)
            R = np.c_[[np.interp(q, d, P[:, c]) for c in range(3)]].T; R[~ok] = np.nan
            row[c0[k]:c0[k] + ncol[k]] = np.where(np.isnan(row[c0[k]:c0[k] + ncol[k]]), R, row[c0[k]:c0[k] + ncol[k]])
        rows.append(row); arcs.append(s); partial += 1
    if verbose:
        print(f'stations: {len(rows)} ({partial} partial, towards the arch) of {len(rows) + len(skipped)} (arc {arcs[0]*1e3:.0f}..{arcs[-1]*1e3:.0f} mm'
              f' of {arc[-1]*1e3:.0f}); skipped at ' + ', '.join(f'{x*1e3:.0f}' for x in skipped[:12]) + (' ...' if len(skipped) > 12 else ''), flush=True)
    return np.array(rows), np.array(arcs)


def vertex_rows3(V, F, Sp, arc, ratio=0.25, min_n=2):
    """Kunos's vertex ROWS of a swept skin from its mesh topology (25 Nov, as rearband_build.vertex_rows_mutual but
    flatness measured in 3D across the sweep - |d(y, d)| / ds - so rows on a near-horizontal top face link too):
    each vertex's neighbour ahead / behind along the spine (ds > 3 mm, flattest), linked only when mutual.
    Returns [(s (n,), X (n, 3))] sorted by s, left half only."""
    import rearband_build as RB
    kk = np.round(V / 1e-6).astype(np.int64); kid = {}
    wid = np.array([kid.setdefault(tuple(k), i) for i, k in enumerate(kk)])
    S = RB.to_sbd(Sp, arc, V); left = V[:, 0] > -1e-6
    nb = {}
    for f in wid[F]:
        for a_, b_ in ((0, 1), (1, 2), (2, 0)):
            a_, b_ = int(f[a_]), int(f[b_])
            if left[a_] and left[b_] and a_ != b_: nb.setdefault(a_, set()).add(b_); nb.setdefault(b_, set()).add(a_)
    def pick(v, sgn):
        best = None
        for n in nb.get(v, ()):
            ds = (S[n, 0] - S[v, 0]) * sgn
            if ds < 0.003: continue
            r = np.hypot(S[n, 1] - S[v, 1], S[n, 2] - S[v, 2]) / ds
            if r < ratio and (best is None or r < best[0]): best = (r, n)
        return None if best is None else best[1]
    ahead = {v: pick(v, 1) for v in nb}; behind = {v: pick(v, -1) for v in nb}
    nxt = {v: n for v, n in ahead.items() if n is not None and behind.get(n) == v}
    has_prev = set(nxt.values()); rows = []
    for v in nb:
        if v in has_prev: continue
        ch = [v]
        while ch[-1] in nxt: ch.append(nxt[ch[-1]])
        if len(ch) >= min_n: rows.append((S[ch, 0], V[ch], np.array(ch)))
    return rows


def row_snap(V, F, Sp, arc, R, A, tol=3e-3, verbose=True):
    """section rows R (stations A along the spine) put onto a SMOOTH profile through Kunos's vertex rows (25 Nov,
    curves first, as the rear band): each vertex row one centripetal Catmull-Rom through its vertices along the spine;
    at a station the rows present there (within tol of the section) ordered along the section, one Catmull-Rom
    through them, and every section point between the first and last row moved to its nearest point on it. The
    sections sampled Kunos's FACETS (low-poly skin, long flat triangles shaded smooth by its normals) and the PN lift
    bulged between them: blotchy, streaky grey. Points outside the rows' span stay."""
    import rearband_build as RB
    rows = vertex_rows3(V, F, Sp, arc)
    curves = []
    for s, X, _ in rows:
        o = np.argsort(s); s, X = s[o], X[o]
        if len(s) >= 3:
            C = RB.catmull_rom(np.c_[s, X], 12); C = C[np.argsort(C[:, 0])]; s, X = C[:, 0], C[:, 1:]
        curves.append((s, X))
    R = R.copy(); moved = []; skipped = []
    for i, a in enumerate(A):
        sec = R[i]
        if np.isnan(sec).any(): continue
        seg = np.linalg.norm(np.diff(sec, axis=0), axis=1); ta = np.r_[0, np.cumsum(seg)]
        dense = np.concatenate([sec[k] + (sec[k + 1] - sec[k]) * np.linspace(0, 1, 20, endpoint=False)[:, None] for k in range(len(sec) - 1)] + [sec[-1:]])
        tdense = np.concatenate([ta[k] + seg[k] * np.linspace(0, 1, 20, endpoint=False) for k in range(len(sec) - 1)] + [ta[-1:]])
        pts = []
        for s, X in curves:
            if not (s[0] - 2e-3 <= a <= s[-1] + 2e-3): continue
            q = np.array([np.interp(a, s, X[:, c]) for c in range(3)])
            dd = np.linalg.norm(dense - q, axis=1); j = int(np.argmin(dd))
            if dd[j] < tol: pts.append((tdense[j], q))
        if len(pts) < 2: continue
        pts.sort(key=lambda p: p[0])
        keep = [pts[0]]
        for p in pts[1:]:
            if p[0] - keep[-1][0] > 3e-4: keep.append(p)
        if len(keep) < 2: continue
        Q = np.array([p[1] for p in keep]); tq = np.array([p[0] for p in keep])
        C = RB.catmull_rom(Q, 24) if len(Q) >= 3 else Q[0] + (Q[1] - Q[0]) * np.linspace(0, 1, 25)[:, None]
        for j in range(len(sec)):
            if tq[0] - 1e-9 <= ta[j] <= tq[-1] + 1e-9:
                dC = np.linalg.norm(C - sec[j], axis=1); k = int(np.argmin(dC))
                # a section point sits ON Kunos's facets: the smooth profile differs by the facet sag only (< 2 mm);
                # farther = the rows mis-ordered there (crossing rows on a fold): leave the point
                if dC[k] < float(os.environ.get('BB_ROWS_CAP', 2.0)) * 1e-3:
                    moved.append(dC[k]); R[i, j] = C[k]
                else: skipped.append(dC[k])
    if verbose and moved:
        print(f'row snap: {len(rows)} vertex rows; {len(moved)} section points moved onto the row profiles, median {np.median(moved) * 1e3:.2f} max {np.max(moved) * 1e3:.2f} mm; {len(skipped)} left (profile > cap away)', flush=True)
    return R


NRM = None           # Kunos's vertex normals of the swept mesh (set by build for line_loft)


def hermite_profile(Q, Ns, tdir, n_seg=30):
    """a profile through the nodes Q as cubic Hermite segments whose tangents come from Kunos's NORMALS at the nodes
    (the tangent = the chord direction made square to the node's normal, in the station plane); a node without a
    normal (a sharp corner, the section's ends) takes one-sided chord tangents. Kunos's skin is low-poly, shaded smooth
    by these normals: this is the surface its shading shows (the PN lift built it per triangle: blotches)."""
    k = len(Q); out = []
    chord = np.diff(Q, axis=0); L = np.linalg.norm(chord, axis=1)
    def tang(i, side):
        n = Ns[i]
        if n is None or not np.isfinite(n).all() or np.linalg.norm(n) < 1e-9:
            c = chord[i] if side > 0 else chord[i - 1]
            return c / max(np.linalg.norm(c), 1e-12)
        n = n - (n @ tdir) * tdir; n /= max(np.linalg.norm(n), 1e-12)
        c = (Q[min(i + 1, k - 1)] - Q[max(i - 1, 0)])
        m = c - (c @ n) * n; m /= max(np.linalg.norm(m), 1e-12); cu = c / max(np.linalg.norm(c), 1e-12)
        # a normal that disagrees with the chords by > 20 deg belongs to something else (an opening's wall the
        # sweep bridges, a crease vertex): chord tangent there (a 14 mm bulge across the plate recess otherwise)
        return m if m @ cu > np.cos(np.radians(float(os.environ.get('BB_HERM_DEG', 20)))) else cu
    for i in range(k - 1):
        m0 = tang(i, 1) * L[i]; m1 = tang(i + 1, -1) * L[i]
        u = np.linspace(0, 1, n_seg + 1)[:, None] if i == k - 2 else np.linspace(0, 1, n_seg, endpoint=False)[:, None]
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        out.append(h00 * Q[i] + h10 * m0 + h01 * Q[i + 1] + h11 * m1)
    return np.concatenate(out)


def line_loft(V, F, Sp, arc, R, A, ncol, tol=1.5e-3, verbose=True):
    """the swept bands rebuilt CURVES FIRST (25 Nov, the rear band's method): Kunos's vertex rows (vertex_rows3) in
    spine coordinates (s, height y, outward d), each a Catmull-Rom through its vertices, held at its end values past
    them; at every station the rows lying on the section (within tol) ordered along it, ONE centripetal Catmull-Rom
    through them (plus the section's own end points where no row reaches them), each band resampled between its
    crease points with its column count by arc length. The band boundaries = the section's crease points snapped to
    the profile. Replaces the section points themselves (Kunos's facets) and the PN lift: blotchy, streaky grey."""
    import rearband_build as RB
    rows = vertex_rows3(V, F, Sp, arc)
    # Kunos's normal at each row vertex (the mean over its welded copies that face its own side: a crease's two
    # normals stay apart), as spine-frame components (n_y, n_d, n_s) so they ride along with the station frame
    HERM = os.environ.get('BB_LOFT_HERM', '1') == '1'
    lines = []
    for s, X, ch in rows:
        S = RB.to_sbd(Sp, arc, X); o = np.argsort(S[:, 0]); S = S[o]
        nrm = NRM[ch[o]] if NRM is not None else np.zeros((len(S), 3))
        P0, T0, O0 = RB.frame_at(Sp, arc, S[:, 0])
        Nc = np.c_[nrm[:, 1], (nrm * O0).sum(1), (nrm * T0).sum(1)]
        S = np.c_[S, Nc]
        if len(S) >= 3:
            C = RB.catmull_rom(S, 12); S = C[np.argsort(C[:, 0])]
        lines.append(S)
    up = np.array([0.0, 1.0, 0.0]); P_, T_, O_ = RB.frame_at(Sp, arc, A)
    c0 = np.cumsum([0] + [n - 1 for n in ncol]); out = R.copy(); used = []
    for i, a in enumerate(A):
        sec = R[i]
        if np.isnan(sec).any(): continue
        seg = np.linalg.norm(np.diff(sec, axis=0), axis=1); ta = np.r_[0, np.cumsum(seg)]
        k20 = np.linspace(0, 1, 20, endpoint=False)
        dense = np.concatenate([sec[k] + (sec[k + 1] - sec[k]) * k20[:, None] for k in range(len(sec) - 1)] + [sec[-1:]])
        tden = np.concatenate([ta[k] + seg[k] * k20 for k in range(len(sec) - 1)] + [ta[-1:]])
        nodes = []
        for S in lines:
            if not (S[0, 0] - float(os.environ.get('BB_LOFT_HOLD', 0.005)) <= a <= S[-1, 0] + float(os.environ.get('BB_LOFT_HOLD', 0.005))): continue
            y, d, ny, nd, ns = [np.interp(a, S[:, 0], S[:, c]) for c in range(1, 6)]
            q = P_[i] + y * up + d * O_[i]; nq = ny * up + nd * O_[i] + ns * T_[i]
            dd = np.linalg.norm(dense - q, axis=1); j = int(np.argmin(dd))
            if dd[j] < tol: nodes.append((tden[j], q, nq))
        for tq, q in ((0.0, sec[0]), (ta[-1], sec[-1])):          # the section's ends where no row reaches them
            if not nodes or min(abs(n_[0] - tq) for n_ in nodes) > 2e-3: nodes.append((tq, q, None))
        # the section's SHARP corners (a turn > 25 deg: the bottom lip's hook, folds) are nodes too: the spline
        # rounded the lip's hook by 5 mm where no vertex row runs exactly on it
        e1 = sec[1:-1] - sec[:-2]; e2 = sec[2:] - sec[1:-1]
        cs = (e1 * e2).sum(1) / np.maximum(np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1), 1e-12)
        for j in np.nonzero(cs < np.cos(np.radians(float(os.environ.get('BB_LOFT_TURN', 25)))))[0] + 1:
            nodes = [n_ for n_ in nodes if abs(n_[0] - ta[j]) > 1.5e-3] + [(ta[j], sec[j], None)]
        nodes.sort(key=lambda n_: n_[0]); keep = [nodes[0]]
        for n_ in nodes[1:]:
            if n_[0] - keep[-1][0] > 5e-4: keep.append(n_)
        used.append(len(keep))
        Q = np.array([n_[1] for n_ in keep])
        if HERM and NRM is not None and len(Q) >= 3:
            C = hermite_profile(Q, [n_[2] for n_ in keep], T_[i])
        else:
            C = RB.catmull_rom(Q, 30) if len(Q) >= 3 else Q[0] + (Q[-1] - Q[0]) * np.linspace(0, 1, 31)[:, None]
        cl = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
        # band boundaries: the section's crease points -> nearest point of the profile (arc position on C)
        def on_c(p): return cl[int(np.argmin(np.linalg.norm(C - p, axis=1)))]
        bnd = [on_c(sec[c0[k]]) for k in range(len(ncol))] + [on_c(sec[-1])]
        for k in range(len(ncol)):
            tt = np.linspace(bnd[k], bnd[k + 1], ncol[k])
            out[i, c0[k]:c0[k] + ncol[k]] = np.c_[[np.interp(tt, cl, C[:, c]) for c in range(3)]].T
    if verbose:
        mv = np.linalg.norm(out - R, axis=2)[~np.isnan(R[..., 0])]
        print(f'line loft: {len(lines)} vertex rows; profile nodes per station median {np.median(used):.0f}; points moved median {np.median(mv) * 1e3:.2f} p95 {np.percentile(mv, 95) * 1e3:.2f} max {mv.max() * 1e3:.2f} mm', flush=True)
    return out


def band_fair(R, ncol, mu=None, verbose=True):
    """each band's profile at each station faired BETWEEN its creases (25 Nov): the band's column points get a
    second-difference fairing with both end points (the creases) held - a band is one smooth face between two lines,
    so across it nothing crisp is lost. The PN-lifted section points kink 0.1-0.5 mm from column to column (Kunos's
    facets): lengthwise streaks along the bumper in grey."""
    mu = float(os.environ.get('BB_BANDFAIR', 3.0)) if mu is None else mu
    R = R.copy(); c0 = np.cumsum([0] + [n - 1 for n in ncol]); mv = []
    for k, n in enumerate(ncol):
        if n < 5: continue
        D = np.zeros((n - 2, n))
        for r in range(n - 2): D[r, r:r + 3] = (1, -2, 1)
        M = np.eye(n) + mu * D.T @ D
        # hold the ends: rows 0 and n-1 replaced by identity constraints
        M[0] = 0; M[0, 0] = 1; M[-1] = 0; M[-1, -1] = 1
        Mi = np.linalg.inv(M)
        for i in range(len(R)):
            P = R[i, c0[k]:c0[k] + n]
            if np.isnan(P).any(): continue
            Q = Mi @ P; mv.append(np.linalg.norm(Q - P, axis=1)); R[i, c0[k]:c0[k] + n] = Q
    if verbose and mv:
        mv = np.concatenate(mv); print(f'band fair (mu {mu:g}): points moved median {np.median(mv) * 1e3:.3f} p95 {np.percentile(mv, 95) * 1e3:.3f} max {mv.max() * 1e3:.3f} mm', flush=True)
    return R


def fair_columns(Sp, arc, R, A, ds=None, verbose=True):
    """every grid column (a line along the sweep: a crease, a band edge or a line on a face) as ONE fair curve
    (25 Nov, curves first - the door way): the column's points in spine coordinates (height y, outward offset d) fitted
    as y(s), d(s) with a control every ds along the sweep, then put back on their stations. The sections sample
    Kunos's low-poly facets: each station's profile jitters by the facet chords (0.5-1.5 mm) - streaks and blotches
    along the bumper in grey. Across the sweep nothing is smoothed: creases stay crisp."""
    import rearband_build as RB
    ds = ds or float(os.environ.get('BB_FAIR_DS', 0.08))
    R = R.copy(); ok = ~np.isnan(R[..., 0]); up = np.array([0.0, 1.0, 0.0])
    P_, T_, O_ = RB.frame_at(Sp, arc, A)
    dom = [A.min() - 0.05, A.max() + 0.05]; n = int(np.clip((A.max() - A.min()) / ds, 4, 30)); mv = []
    for j in range(R.shape[1]):
        m = ok[:, j]
        if m.sum() < 6: continue
        y = R[m, j, 1]; d = ((R[m, j] - P_[m]) * O_[m]).sum(1); tg = ((R[m, j] - P_[m]) * T_[m]).sum(1)
        fy = PF.fit_func(A[m], y, dom, tol=1e-4, nmax=n); fd = PF.fit_func(A[m], d, dom, tol=1e-4, nmax=n)
        Q = P_[m] + PF.eval_func(fy, A[m])[:, None] * up + PF.eval_func(fd, A[m])[:, None] * O_[m] + tg[:, None] * T_[m]
        mv.append(np.linalg.norm(Q - R[m, j], axis=1)); R[m, j] = Q
    if verbose and mv:
        mv = np.concatenate(mv); print(f'fair columns: {R.shape[1]} lines, {n} controls each; points moved median {np.median(mv) * 1e3:.2f} p95 {np.percentile(mv, 95) * 1e3:.2f} max {mv.max() * 1e3:.2f} mm', flush=True)
    return R


def pn_eval(P, Nt, uvw):
    """points of the PN triangle (Vlachos 2001) over corners P (3x3) with unit normals Nt at barycentrics uvw (k x 3)"""
    P1, P2, P3 = P; N1, N2, N3 = Nt
    wij = lambda Pi, Pj, Ni: (Pj - Pi) @ Ni
    b210 = (2 * P1 + P2 - wij(P1, P2, N1) * N1) / 3; b120 = (2 * P2 + P1 - wij(P2, P1, N2) * N2) / 3
    b021 = (2 * P2 + P3 - wij(P2, P3, N2) * N2) / 3; b012 = (2 * P3 + P2 - wij(P3, P2, N3) * N3) / 3
    b102 = (2 * P3 + P1 - wij(P3, P1, N3) * N3) / 3; b201 = (2 * P1 + P3 - wij(P1, P3, N1) * N1) / 3
    E = (b210 + b120 + b021 + b012 + b102 + b201) / 6; Vc = (P1 + P2 + P3) / 3; b111 = E + (E - Vc) / 2
    u, v, w = [np.asarray(uvw)[:, i:i + 1] for i in range(3)]
    return (P1 * u ** 3 + P2 * v ** 3 + P3 * w ** 3 + b210 * 3 * u * u * v + b120 * 3 * u * v * v + b201 * 3 * u * u * w
            + b021 * 3 * v * v * w + b102 * 3 * u * w * w + b012 * 3 * v * w * w + b111 * 6 * u * v * w)


def pn_sample(V, F, N, n=5):
    """dense points on the PN triangles of (V, F) with vertex normals N: (n+1)(n+2)/2 per triangle (corners shared)"""
    Nn = N / np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    uvw = np.array([(i / n, j / n, (n - i - j) / n) for i in range(n + 1) for j in range(n + 1 - i)])
    return np.unique(np.round(np.vstack([pn_eval(V[f], Nn[f], uvw) for f in F]), 7), axis=0)


def pn_lift(V, F, N, X, tol=2e-4, Nc=None):
    """points X lying on Kunos's flat triangles moved onto the curved PN triangle (Vlachos 2001: the cubic patch the
    triangle's vertex normals describe, i.e. the surface Kunos's smooth shading shows). A section through big facets
    sits up to the facet's sagitta inside the shaded surface, by a different amount at every column: across the
    columns that read as streaks along the sweep (the front bumper's corner, 19 Nov). Points further than tol from
    every triangle (chords across a bridged opening) are left as they are."""
    from scipy.spatial import cKDTree
    from exact_dist import point_to_tris
    X = np.asarray(X, float); sh = X.shape; X = X.reshape(-1, 3); out = X.copy()
    ok = ~np.isnan(X[:, 0]); T = V[F]; tc = cKDTree(T.mean(1))
    Nn = N / np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    moved = []
    for i in np.nonzero(ok)[0]:
        x = X[i]; kk = tc.query(x, 12)[1]
        d = [point_to_tris(x[None], T[k][None])[0] for k in kk]; j = int(np.argmin(d))
        if d[j] > tol: continue
        f = F[kk[j]]; P1, P2, P3 = V[f]; Nf = Nn[f] if Nc is None else Nc[kk[j]]   # Nc: per-corner normals (crease-aware)
        # barycentrics of x's projection on the flat triangle
        e1, e2 = P2 - P1, P3 - P1; r = x - P1
        a11, a12, a22 = e1 @ e1, e1 @ e2, e2 @ e2; b1, b2 = r @ e1, r @ e2; det = a11 * a22 - a12 ** 2
        if det < 1e-18: continue
        v = (a22 * b1 - a12 * b2) / det; w = (a11 * b2 - a12 * b1) / det; u = 1 - v - w
        u, v, w = np.clip([u, v, w], 0, 1); s_ = u + v + w; u, v, w = u / s_, v / s_, w / s_
        flat = u * P1 + v * P2 + w * P3; pn = pn_eval(V[f], Nf, np.array([[u, v, w]]))[0]
        out[i] = x + (pn - flat); moved.append(np.linalg.norm(pn - flat))
    if moved: print(f'PN lift: {len(moved)} of {ok.sum()} row points moved, median {np.median(moved)*1e3:.2f} max {np.max(moved)*1e3:.2f} mm', flush=True)
    return out.reshape(sh)


def fill_nan_rows(R, A):
    """NaN columns of the partial rows carried on from their last valid rows (G1: a cubic through the last 4 along the
    spine, its end tangent), so the grid stays whole; they lie past the arch outline and are trimmed away"""
    R = R.copy()
    for j in range(R.shape[1]):
        ok = ~np.isnan(R[:, j, 0])
        if ok.all(): continue
        iv = np.nonzero(ok)[0]; last = iv[-1]
        for i in range(iv[0], last):                                     # gaps between valid rows: along the spine
            if np.isnan(R[i, j, 0]): R[i, j] = [np.interp(A[i], A[iv], R[iv, j, c]) for c in range(3)]
        P = R[iv[-4:], j]; a = A[iv[-4:]]
        c = np.linalg.lstsq(np.vander(a - a[-1], min(4, len(a)), increasing=True), P, rcond=None)[0]
        tg = c[1] if len(c) > 1 else np.zeros(3)
        for i in range(last + 1, len(R)):
            if np.isnan(R[i, j, 0]): R[i, j] = R[last, j] + (A[i] - A[last]) * tg
    return R


def grid_project(G, X, iters=8):
    """closest points of X on the grid's index-space spline (row index s, column index t): (s, t, distance m); as
    hatch_build.grid_project, with the degree lowered for narrow grids (a 2 mm groove band has 3 columns)"""
    from scipy.interpolate import RectBivariateSpline
    from scipy.spatial import cKDTree
    nr, nc, _ = G.shape; kx, ky = min(3, nr - 1), min(3, nc - 1)
    Sp = [RectBivariateSpline(np.arange(nr, dtype=float), np.arange(nc, dtype=float), G[:, :, k], kx=kx, ky=ky, s=0) for k in range(3)]
    def ev(s, t, a=0, b=0): return np.stack([Sp[k].ev(s, t, dx=a, dy=b) for k in range(3)], -1)
    ss, tt = np.meshgrid(np.arange(0, nr - 1 + 1e-9, 0.25), np.arange(0, nc - 1 + 1e-9, 0.25), indexing='ij')
    _, k = cKDTree(ev(ss.ravel(), tt.ravel())).query(X); s, t = ss.ravel()[k].copy(), tt.ravel()[k].copy()
    for _ in range(iters):
        P = ev(s, t); Su, Sv = ev(s, t, 1, 0), ev(s, t, 0, 1); r = X - P
        A11, A12, A22 = (Su * Su).sum(1), (Su * Sv).sum(1), (Sv * Sv).sum(1); b1, b2 = (r * Su).sum(1), (r * Sv).sum(1)
        det = A11 * A22 - A12 ** 2 + 1e-18
        s = np.clip(s + (A22 * b1 - A12 * b2) / det, 0, nr - 1); t = np.clip(t + (A11 * b2 - A12 * b1) / det, 0, nc - 1)
    return s, t, np.linalg.norm(X - ev(s, t), axis=1)


def end_trim(V, Fp, Gk, s_t, tol=2e-3):
    """the outline a band face keeps when the sweep runs on past where the band ends (BB_EXT): the band piece's outer
    loop near the left end, projected into the grid's index space (row s, column t), gives each column's last row
    s_end(t); the polygon (s_end(t), t) on the left, its mirror on the right, mapped back onto the grid surface (3D,
    metres). None when the band runs the grid's full length."""
    from scipy.interpolate import RectBivariateSpline
    nr, nc, _ = Gk.shape
    _, wid_ = PF.components(V, Fp); rep_ = {w: i for i, w in enumerate(wid_)}
    L3 = [V[[rep_[w] for w in L]] for L in PF.boundary_loops(Fp, wid_)]
    X = max(L3, key=lambda X: np.linalg.norm(np.diff(X, axis=0), axis=1).sum())
    X = X[X[:, 0] > 0]
    # densify the outline (Kunos's edges are long): 1 mm steps
    Xd = [X[0]]
    for a, b in zip(X[:-1], X[1:]):
        n_ = max(1, int(np.linalg.norm(b - a) / 1e-3)); Xd += list(a + (b - a) * (np.arange(1, n_ + 1) / n_)[:, None])
    X = np.array(Xd)
    s_, t_, d_ = grid_project(Gk, X)
    m = (d_ < tol) & (s_ > s_t - 2) & (s_ < nr - 1.3) & (t_ > 0.3) & (t_ < nc - 1.3)
    if m.sum() < 5: return None
    tt = np.arange(0, nc - 1 + 1e-9, 0.25); se = np.full(len(tt), np.nan)
    for i, t0 in enumerate(tt):
        w = m & (np.abs(t_ - t0) < 0.5)
        if w.any(): se[i] = np.median(s_[w])
    ok = ~np.isnan(se)
    if ok.sum() < 2: return None
    # a column with no outline point in the run-on rows runs past the grid's end (the outline there lies beyond the
    # last row): it keeps the full length (interpolating from the flare columns cut the top bands short: a gap, 19 Nov)
    # ... but a gap BETWEEN columns that have outline points is interpolated: at the rib the outline runs over Kunos's
    # bevel, more than tol off our straight-on rib, and those columns ran full length (a jog in the edge, the rib
    # poking out over the flare, 19 Nov)
    iv = np.nonzero(ok)[0]; inner = (np.arange(len(tt)) > iv[0]) & (np.arange(len(tt)) < iv[-1])
    se = np.where(ok, se, np.where(inner, np.interp(tt, tt[ok], np.nan_to_num(se[ok])), nr - 1))
    # the per-bin medians zig-zag by a few tenths of a row (the edge then stepped: notches of daylight beside the flare,
    # whose outline is snapped onto this edge); Kunos's edge is a straight-ish line here: a light 5-bin average
    k_ = np.array([1, 2, 3, 2, 1], float); k_ /= k_.sum()
    sp_ = np.convolve(np.r_[[se[0]] * 2, se, [se[-1]] * 2], k_, 'valid')
    se = np.where(se < nr - 1.3, np.minimum(sp_, nr - 1), se)
    se = np.clip(se, s_t, nr - 1)
    if (se > nr - 1.3).all(): return None
    kx, ky = min(3, nr - 1), min(3, nc - 1)
    Sp = [RectBivariateSpline(np.arange(nr, dtype=float), np.arange(nc, dtype=float), Gk[:, :, c], kx=kx, ky=ky, s=0) for c in range(3)]
    ev = lambda s, t: np.stack([Sp[c].ev(s, t) for c in range(3)], -1)
    left = ev(se, tt); right = ev((nr - 1) - se[::-1], tt[::-1])
    return np.r_[left, right]


def fit_best(nm, V, Fw, N):
    """PF.fit_panel over the piece's best-fit plane, and (BB_FRAME2, default on) over the plane square to its MEAN
    vertex normal; the one with the smaller fit p95 is kept. A piece that wraps (the front flare r5 runs round the
    arch and over onto the top) leans its best-fit plane: p95 3.9 mm there, 1.8 over the mean-normal plane (19 Nov)."""
    a = PF.fit_panel(nm, V, Fw, N, verbose=False)
    if os.environ.get('BB_FRAME2', '1') != '1': return a
    P = V[np.unique(Fw)]; w = N[np.unique(Fw)].mean(0); w /= max(np.linalg.norm(w), 1e-12)
    if abs(w @ np.array(a['frame'][3])) > np.cos(np.radians(5)): return a        # the same plane, near enough
    z = np.array([0, 0, 1.0]); e1 = z - (z @ w) * w
    if np.linalg.norm(e1) < 0.5: y = np.array([0, 1.0, 0]); e1 = y - (y @ w) * w
    e1 /= np.linalg.norm(e1)
    try: b = PF.fit_panel(nm, V, Fw, N, verbose=False, fr=(P.mean(0), e1, np.cross(w, e1), w))
    except Exception: return a
    if b['fit_p95_mm'] < 0.8 * a['fit_p95_mm']:
        print(f'{nm}: mean-normal plane fits better (p95 {a["fit_p95_mm"]:.2f} -> {b["fit_p95_mm"]:.2f} mm)', flush=True); return b
    return a


def others(V, F, N, pcs, bands, pre, amin=2e-5):
    """every crease piece that is not a swept band, as panel_fit's 'rall' path builds a part: narrow pieces as ruled
    strips (strip_build) whose sides on a neighbour are that neighbour's BUILT edge, wide pieces as fitted faces. Every
    face of piece r<i> is named '<pre>:r<i>...' (the bands too: '<pre>:r0b2', '<pre>:r0eL'), so a strip side's
    nb_name '<pre>:r<nb>' finds its neighbour's faces by prefix."""
    import strip_build as SB
    out = []
    st = SB.find_strips(V, F, N, pcs, PF.components, PF.boundary_loops, amin=amin)
    # crease pieces of 1-3 triangles (the small folds at the arch ends are fans of facets, each its own crease piece):
    # too small for a fitted face (no outline wire). Touching ones (a shared edge) that face the same way are one
    # group -> one corner fill, its outline snapped onto the built edges in the FreeCAD stage
    _, wid = PF.components(V, F)
    tiny = [ri for ri, Fr in enumerate(pcs) if 0 < len(Fr) <= 3 and ri not in set(bands) and ri not in st]
    nr_ = {ri: (lambda n: n / np.linalg.norm(n))(N[pcs[ri]].mean((0, 1))) for ri in tiny}
    vs_ = {ri: set(wid[pcs[ri].ravel()]) for ri in tiny}
    par = {ri: ri for ri in tiny}
    def root(a):
        while par[a] != a: a = par[a]
        return a
    for i, a in enumerate(tiny):
        for b in tiny[i + 1:]:
            if len(vs_[a] & vs_[b]) >= 2 and nr_[a] @ nr_[b] > 0.3: par[root(b)] = root(a)
    groups = {}
    for ri in tiny: groups.setdefault(root(ri), []).append(ri)
    for g in groups.values():
        cf = corner_fill(V, F, N, np.concatenate([pcs[r] for r in g]), f'{pre}cf:r{g[0]}')
        if cf: out.append(cf)
        else: print(f'{pre}cf:r{g[0]} ({len(g)} pieces): no single outline - skipped', flush=True)
    tiny = set(tiny)
    # right-hand pieces (x < 0) that are a left piece mirrored: built as its mirror (front bumper r6 was fitted on its
    # own, 18 mm off, while its twin r5 was right; the mirror check said 10.9 mm). BB_MIRROR=0: off.
    mkey = lambda X: frozenset(map(tuple, np.round(X * 2e3).astype(np.int64)))
    twin = {}
    if os.environ.get('BB_MIRROR', '1') == '1':
        left_ = {mkey(V[np.unique(Fr)]): ri for ri, Fr in enumerate(pcs) if len(Fr) and V[np.unique(Fr)][:, 0].min() > 1e-4}
        for ri, Fr in enumerate(pcs):
            if not len(Fr): continue
            X_ = V[np.unique(Fr)]
            if X_[:, 0].max() < -1e-4 and ri not in tiny and ri not in set(bands):
                li = left_.get(mkey(X_ * MIR))
                if li is not None and li not in tiny: twin[ri] = li
    for ri, Fr in enumerate(pcs):
        if ri in set(bands) or ri in twin or not len(Fr): continue
        T_ = V[Fr]; A_ = np.linalg.norm(np.cross(T_[:, 1] - T_[:, 0], T_[:, 2] - T_[:, 0]), axis=1).sum() / 2
        if A_ < amin: continue
        if ri in st:
            s_ = st[ri]
            for sd in [x for sub in s_.get('subs', [s_]) for x in sub['sides']]:
                for r in [sd] + list(sd.get('runs', [])):
                    if isinstance(r['key'], str): continue
                    r['nb_name'] = None if r['nb'] is None else f'{pre}:r{r["nb"]}'
                    r['nb_strip'] = r['nb'] in st and r['nb'] not in set(bands)
                    r['key'] = f'{pre}:' + '|'.join(str(x) for x in r['key'])
            subs = s_.get('subs') or [s_]
            for k, sub in enumerate(subs):
                out.append(dict(name=f'{pre}:r{ri}' + (f'f{k}' if len(subs) > 1 else ''), strip=sub, frame=sub['frame']))
            continue
        if ri in tiny: continue              # grouped below
        parts = PF.wrap_split(V, Fr, N)
        for wi, Fw in enumerate(parts):
            if len(parts) > 1 and len(Fw) < 4: continue
            nm = f'{pre}:r{ri}' + (f'w{wi}' if len(parts) > 1 else '')
            try:
                out.append(fit_best(nm, V, Fw, N))
            except Exception as ex:
                cf = corner_fill(V, F, N, Fw, f'{pre}cf:r{ri}' + (f'w{wi}' if len(parts) > 1 else ''))
                if cf: out.append(cf)
                print(f'{nm} fit failed ({ex}): ' + ('corner fill' if cf else 'skipped'), flush=True)
    import re
    for ri, li in twin.items():
        for o in [o for o in out if re.match(rf'{re.escape(pre)}:r{li}(?!\d)', o['name'])]:
            out.append(dict(name=re.sub(rf'^{re.escape(pre)}:r{li}', f'{pre}:r{ri}', o['name']), mirror_of=o['name']))
    if twin: print(f'mirrored pieces: {len(twin)}', flush=True)
    # left / right corner fill pairs: the right one (x < 0) = the left one mirrored, so both snap the same way (built
    # apart, r62 and r63 snapped 180 / 101 of their outline points onto different neighbours, 17 Nov)
    from scipy.spatial import cKDTree
    cfo = [o for o in out if o.get('corner_fill')]
    for b_ in [o for o in cfo if np.array(o['corner_fill']['outline'])[:, 0].mean() < 0]:
        Xb = np.array(b_['corner_fill']['outline'])
        for a_ in [o for o in cfo if np.array(o['corner_fill']['outline'])[:, 0].mean() > 0]:
            if abs(a_['corner_fill']['area'] - b_['corner_fill']['area']) > 0.03 * a_['corner_fill']['area']: continue
            Xa = np.array(a_['corner_fill']['outline']) * [-1, 1, 1]
            if cKDTree(Xa).query(Xb)[0].mean() < 1.0:
                out[out.index(b_)] = dict(name=b_['name'], mirror_of=a_['name']); break
    print(f'other pieces: {sum(1 for o in out if o.get("strip"))} strips, {sum(1 for o in out if o.get("corner_fill"))} corner fills, '
          f'{sum(1 for o in out if not o.get("strip") and not o.get("corner_fill"))} faces', flush=True)
    return out


def clip_tris(V, Fr, N, m, n, margin):
    """triangles Fr clipped to (X - m).n <= margin: a new (V, F, N) with the cut points shared between neighbours
    (an edge is cut once, keyed by its welded end positions)"""
    key = lambda i: tuple(np.round(V[i], 6))
    Vo, No, idx, F2, cut = [], [], {}, [], {}
    def vid(i):
        k = key(i)
        if k not in idx: idx[k] = len(Vo); Vo.append(V[i]); No.append(N[i])
        return idx[k]
    def eid(a, b):
        ka, kb = key(a), key(b)
        if kb < ka: a, b, ka, kb = b, a, kb, ka
        if (ka, kb) not in cut:
            sa, sb = (V[a] - m) @ n - margin, (V[b] - m) @ n - margin; t = sa / (sa - sb)
            q = V[a] + t * (V[b] - V[a]); nq = N[a] + t * (N[b] - N[a])
            cut[(ka, kb)] = len(Vo); Vo.append(q); No.append(nq / np.linalg.norm(nq))
        return cut[(ka, kb)]
    for f in Fr:
        sd = (V[f] - m) @ n - margin
        if (sd > 0).all(): continue
        poly = []
        for k in range(3):
            a, b = f[k], f[(k + 1) % 3]
            if sd[k] <= 0: poly.append(vid(a))
            if (sd[k] <= 0) != (sd[(k + 1) % 3] <= 0): poly.append(eid(a, b))
        for k in range(1, len(poly) - 1): F2.append([poly[0], poly[k], poly[k + 1]])
    return np.array(Vo), np.array(F2, int), np.array(No)
def corner_fill(V, F, N, Fr, name, clip=None):
    """a small piece as a corner fill (as bonnet_build): its one outline every 1 mm + inner vertices, in mm.
    clip = (point, normal) in metres: the outline is clipped to the side (X - point) . normal <= 0 (a groove end past
    the sweep's last station: its clipped edge lies on that plane = on the sweep's end row)"""
    _, wid = PF.components(V, F); rep = {}
    for i, w in enumerate(wid): rep.setdefault(w, i)
    loops = PF.boundary_loops(Fr, wid)
    if len(loops) != 1 and len(Fr) == 1: loops = [list(wid[Fr[0]])]   # a lone triangle: its own three corners
    if len(loops) != 1: return None
    Q = V[[rep[w] for w in loops[0]]] * 1000
    if clip is not None:                                   # Sutherland-Hodgman on one plane
        c0, cn = np.asarray(clip[0]) * 1000, np.asarray(clip[1]); h = (Q - c0) @ cn; Qc = []
        for i in range(len(Q)):
            a_, b_, ha, hb = Q[i], Q[(i + 1) % len(Q)], h[i], h[(i + 1) % len(Q)]
            if ha <= 0: Qc.append(a_)
            if (ha <= 0) != (hb <= 0): Qc.append(a_ + (b_ - a_) * ha / (ha - hb))
        Q = np.array(Qc)
        if len(Q) < 3: return None
    Q = np.r_[Q, Q[:1]]
    dq = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.arange(0, dq[-1], 1.0)
    R = np.c_[[np.interp(t, dq, Q[:, k]) for k in range(3)]].T
    inner = V[[rep[w] for w in sorted(set(wid[Fr.ravel()]) - set(loops[0]))]] * 1000 if len(Fr) > 1 else np.zeros((0, 3))
    if clip is not None and len(inner): inner = inner[(inner - np.asarray(clip[0]) * 1000) @ np.asarray(clip[1]) <= 0]
    T = V[Fr] * 1000; A = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2
    if A < 0.5 or len(R) < 3: return None                  # degenerate slivers (0 mm2 facets)
    nrm = N[Fr].mean((0, 1)); nrm /= np.linalg.norm(nrm)
    return dict(name=name, frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0], nrm.tolist()],
                corner_fill=dict(outline=R.tolist(), inner=inner.tolist(), area=float(A), normal=nrm.tolist()))


def build(car, out, which='rear'):
    import hatch_build as HB
    sp = SPEC[which]
    V, F, N = PF.load_mesh(car, sp['mesh']); pcs = pieces(V, F, N, sp)
    global BRIDGE, YCOLS; BRIDGE = sp.get('bridge', 0.0); YCOLS = tuple(sp.get('ycols', ())) if os.environ.get('BB_YCOLS', '1') == '1' else ()
    bands = sp['bands']
    if not bands:
        res = others(V, F, N, pcs, [], sp['name'])
        os.makedirs(out, exist_ok=True); json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w')); return
    if sp.get('spine_bottom') is not None and os.environ.get('PF_NOBAND') == '1':
        # the tail's plate panel without the rear lower band (rearband_build.py owns it, 24 Nov): the pair's edge was
        # the band's; the spine = plan line of the panel's own bottom edge (its lowest boundary points)
        import rearband_build as RBB
        Fp = pcs[sp['spine_bottom']]; _, wid_ = PF.components(V, Fp); pos_ = {}
        for i_, w_ in enumerate(wid_): pos_.setdefault(int(w_), V[i_])
        Xb = np.array([pos_[int(w_)] for L_ in PF.boundary_loops(Fp, wid_) for w_ in L_])
        Xb = Xb[Xb[:, 1] < Xb[:, 1].min() + 0.012]
        Sp, arc, err = RBB.spine(Xb, centre_z=sp['centre_z'])
    else:
        Sp, arc, err = spine(V, PF.crease_pieces(V, F, N), sp['spine_pair'], sp['centre_z'], zdir=sp.get('zdir', -1))   # raw pieces: the pair's edge
    print(f'spine: {arc[-1]*1e3:.0f} mm (left half), fit max {err*1e3:.2f} mm', flush=True)
    # columns per band: from the band's typical width
    R0, _ = station_rows(V, pcs, bands, Sp, arc, 0.1, [3] * len(bands), verbose=False)
    w = [np.median([np.linalg.norm(np.diff(r[2 * k:2 * k + 3], axis=0), axis=1).sum() for r in R0]) for k in range(len(bands))]
    ncol = [int(np.clip(round(x * 1e3 / sp['mm_per_col']) + 1, 3, 40)) for x in w]
    print('bands', bands, 'widths', [round(x * 1e3, 1) for x in w], 'columns', ncol, flush=True)
    R, A = station_rows(V, pcs, bands, Sp, arc, STEP, ncol, anchor_band=sp['anchor_band'])
    ROWS = os.environ.get('BB_ROWS', '1' if sp.get('rows') else '0') == '1'
    FAIR = os.environ.get('BB_FAIR', '1' if sp.get('fair') else '0') == '1'
    if os.environ.get('BB_DUMP'): np.savez(os.environ['BB_DUMP'], R=R, A=A, Sp=Sp, arc=arc)
    LOFT = os.environ.get('BB_LOFT', '1' if sp.get('loft') else '0') == '1'
    if LOFT:
        global NRM; NRM = N
        R = line_loft(V, np.vstack([pcs[b] for b in sorted(set(bands))]), Sp, arc, R, A, ncol)
    elif FAIR:
        R = fair_columns(Sp, arc, R, A)
    elif ROWS:
        R = row_snap(V, np.vstack([pcs[b] for b in sorted(set(bands))]), Sp, arc, R, A)
    elif os.environ.get('BB_PN', '1' if sp.get('pn') else '0') == '1':
        R = pn_lift(V, np.vstack([pcs[b] for b in sorted(set(bands))]), N, R)
    if os.environ.get('BB_BANDFAIR', str(sp.get('band_fair', ''))):
        R = band_fair(R, ncol)
    if sp.get('trim_shrink'):
        # the stations past the point where a band starts to shrink (front: the side flare r5 cuts into the face
        # towards the corner, its rows crumpled the grid there) are dropped; the end faces take that part
        c0t = np.cumsum([0] + [n - 1 for n in ncol])
        Wb = np.array([[np.linalg.norm(np.diff(r[c0t[k]:c0t[k] + ncol[k]], axis=0), axis=1).sum() for k in range(len(bands))] for r in R])
        ab_ = sp['anchor_band']                          # the face band only (the top band narrows where r8 ends: legit)
        ok = Wb[:, ab_] > sp['trim_shrink'] * np.median(Wb[:, ab_])
        last = len(ok) if ok.all() else int(np.argmin(ok))
        if last < len(R): print(f'stations trimmed at {A[last]*1e3:.0f} mm (a band shrinks there): {len(R) - last} dropped', flush=True)
        R, A = R[:last], A[:last]
    # column offsets per band (from the crease on the anchor side) at the last full stations: for the partial rows
    c0_ = np.cumsum([0] + [n - 1 for n in ncol]); offs = []
    for k in range(len(bands)):
        Rk = R[-5:, c0_[k]:c0_[k] + ncol[k]]
        d = np.c_[np.zeros(len(Rk)), np.cumsum(np.linalg.norm(np.diff(Rk, axis=1), axis=2), axis=1)].mean(0)
        offs.append(d if k >= sp['anchor_band'] else d[-1] - d[::-1])
    if float(os.environ.get('BB_TAIL', 0)) > 0:      # partial rows towards the arch (tried 17 Nov: rows kink and fold there)
        R, A = station_rows(V, pcs, bands, Sp, arc, STEP, ncol, anchor_band=sp['anchor_band'], s_max=arc[-1] + float(os.environ['BB_TAIL']), offsets=offs)
        R = fill_nan_rows(R, A)
    ext = float(os.environ.get('BB_EXT', sp.get('extend', 0)))
    if ext > 0:
        # the sweep carried on past the trim towards the arch (front: the face's rib and round ran out at the end face,
        # a seam; 19 Nov): partial rows, the face band at the last full row's HEIGHTS (yfix), the columns the flare
        # takes carried on along the spine and trimmed by the band's outline in the FreeCAD stage
        a_t = A[-1]; ab_ = sp['anchor_band']
        yf = {ab_: R[-1, c0_[ab_]:c0_[ab_] + ncol[ab_], 1].copy()}
        R2, A2 = station_rows(V, pcs, bands, Sp, arc, STEP, ncol, anchor_band=ab_, s_max=a_t + ext, offsets=offs,
                              s_full_max=a_t, yfix=yf)
        new = A2 > a_t + 1e-9
        # the other bands (the narrow top lip / top face) are not sampled again: their sections there mismatch (a kink
        # in the lip 30 mm before the end, 19 Nov); they ride on as the last full row's profile with the face band
        keepc = np.zeros(R2.shape[1], bool); keepc[c0_[ab_]:c0_[ab_] + ncol[ab_]] = True
        R2[np.ix_(new, ~keepc)] = np.nan
        if ROWS and new.any():
            R2[new] = row_snap(V, np.vstack([pcs[b] for b in sorted(set(bands))]), Sp, arc, R2[new], A2[new])
        elif os.environ.get('BB_PN', '1' if sp.get('pn') else '0') == '1' and new.any():
            R2[new] = pn_lift(V, np.vstack([pcs[b] for b in sorted(set(bands))]), N, R2[new])
        assert int((~new).sum()) == len(R), (int((~new).sum()), len(R)); R2[~new] = R
        nanf = np.isnan(R2[new][..., 0]).mean() if new.any() else 0
        print(f'extended: {new.sum()} partial rows to {A2[-1]*1e3:.0f} mm (trim at {a_t*1e3:.0f}), {nanf*100:.0f} % of their points carried on', flush=True)
        # points the section no longer reaches: the last full row's profile slid along with the row's nearest valid
        # point (per column along the spine they were extrapolated one by one: a crinkled, jagged end)
        i0 = int((~new).sum()) - 1
        for i in np.nonzero(new)[0]:
            v_ = ~np.isnan(R2[i, :, 0])
            if not v_.any(): R2[i] = R2[i - 1]; continue
            iv = np.nonzero(v_)[0]
            # the other bands (top lip / top face): moved along the SPINE from the last full row (riding on the face
            # band's top point they followed its jitter where the face meets the rib's bevel: a kink in the top
            # round near the end, 19 Nov); the face band's own run-out points (past the flare, trimmed) still slide
            def _sp(s):
                if s <= arc[-1]: return np.array([np.interp(s, arc, Sp[:, c]) for c in range(3)])
                t_ = Sp[-1] - Sp[-3]; return Sp[-1] + (s - arc[-1]) * t_ / np.linalg.norm(t_)
            # straight on along the spine's tangent at the last full row (the spine itself bends into the arch past
            # there; Kunos's top lip runs straight: the lip kinked up following it)
            t0_ = _sp(A2[i0] + 0.01) - _sp(A2[i0] - 0.01); t0_[1] = 0; t0_ /= np.linalg.norm(t0_)
            dsp = (A2[i] - A2[i0]) * t0_
            for j in np.nonzero(~v_)[0]:
                if not keepc[j]: R2[i, j] = R2[i0, j] + dsp; continue
                jv = iv[np.argmin(np.abs(iv - j))]; R2[i, j] = R2[i0, j] + (R2[i, jv] - R2[i0, jv])
        R, A = R2, A2
        N_MAIN = i0 + 1

    if A[0] > 1e-6:                                            # the centre station: the mirror plane
        pass
    # symmetric data set: left rows + mirrored rows at arcs -a
    keep = A > 1e-6
    A_ = np.r_[-A[keep][::-1], A]; R_ = np.r_[(R[keep] * MIR)[::-1], R]
    ab = sp['anchor_band']; anchor = int(np.cumsum([0] + [n - 1 for n in ncol])[ab] + ncol[ab] // 2)     # a point on the upper face
    # 25 Nov: the front bumper's rows smoothed harder along the sweep (lam 1e-5; the normal-residual search stopped at
    # 1e-8): the PN-lifted sections' station-to-station jitter showed as blotches round the corner; same accuracy
    lam0 = float(os.environ['BB_LAM']) if os.environ.get('BB_LAM') else sp.get('lam')
    if ext > 0 and lam0 is None:     # the smoothing strength from the main rows (the partial rows' noise would pull it to its floor)
        km = np.abs(A_) <= A[N_MAIN - 1] + 1e-9
        lam0 = HB.smooth_rows_local(A_[km], R_[km], spacing=float(os.environ.get('BB_SPACING', 0.03)), col=anchor, nrm_rms=1e-4, nrm_p99=4e-4)[3]
    fsm, nrms, nmax_, lam = HB.smooth_rows_local(A_, R_, spacing=float(os.environ.get('BB_SPACING', 0.03)), col=anchor,
                                                 nrm_rms=1e-4, nrm_p99=4e-4, lam=lam0)
    n_half = int(np.ceil(A[-1] / STEP))
    a_l = np.linspace(0, A[-1], n_half + 1)
    a_all = np.r_[-a_l[::-1], a_l[1:]]
    G = fsm(a_all); G = (G + (G * MIR)[::-1]) / 2
    print(f'grid {G.shape[0]} rows x {G.shape[1]}: smoothing lambda {lam:.0e}, normal rms {nrms*1e3:.3f} max {nmax_*1e3:.2f} mm', flush=True)
    res = []
    nr = len(G); c0_ = np.cumsum([0] + [n - 1 for n in ncol])
    for k, b in enumerate(bands):
        nb = N[np.unique(pcs[b])].mean(0); nb /= np.linalg.norm(nb)
        res.append(dict(name=f'{sp["name"]}:r{b}b{k}', maxlen=float(os.environ.get('BB_MAXLEN', 8)), structured=True,
                        grid=(G[:, c0_[k]:c0_[k] + ncol[k]] * 1000).tolist(), frame=[[0, 0, 0], [1, 0, 0], [0, 1, 0], nb.tolist()], band_piece=int(b)))
        if ext > 0:
            tr = end_trim(V, pcs[b], G[:, c0_[k]:c0_[k] + ncol[k]], int(np.searchsorted(a_all, A[N_MAIN - 1] - 1e-9)))
            if tr is not None:
                res[-1]['trim'] = (tr * 1000).tolist(); print(f'r{b}: band face trimmed at its ends by the outline ({len(tr)} points)', flush=True)
        if BRIDGE > 0:
            # openings the sweep bridged (the plate recess, the lower intake): the band piece's inner boundary loops
            # lying within the swept span, cut out of the grid face in the FreeCAD stage
            _, wid_ = PF.components(V, pcs[b]); rep_ = {w: i for i, w in enumerate(wid_)}
            L3 = [V[[rep_[w] for w in L]] for L in PF.boundary_loops(pcs[b], wid_)]
            if len(L3) > 1:
                L3.sort(key=lambda X: -np.linalg.norm(np.diff(np.r_[X, X[:1]], axis=0), axis=1).sum())
                xmax = np.abs(G[0, c0_[k]:c0_[k] + ncol[k], 0]).min()
                hs = [X for X in L3[1:] if np.abs(X[:, 0]).max() < xmax - 0.005]
                if hs:
                    res[-1]['holes'] = [(X * 1000).tolist() for X in hs]
                    print(f'r{b}: {len(hs)} openings cut from the band (' + ', '.join(f'{np.ptp(X[:, 0])*1e3:.0f} mm wide' for X in hs) + ')', flush=True)
    # END faces at the arch (left; right = mirror): the sweep stops at its last full station; each band piece's
    # triangles past that station's plane are one fitted face over its own plane, with the sweep's last rows of that
    # piece as extra data (so it meets the band), cut exactly on the plane of the sweep's last row (the hatch header's
    # join to its pillars, 12 Nov). A piece split in two bands (the face r0 above and below the groove) is ONE end
    # face: the groove closes to a point before the arch and the face runs on round its end.
    Lr = G[-1]; m_ = Lr.mean(0); n_ = np.linalg.svd(Lr - m_)[2][2]
    if n_ @ (G[-2].mean(0) - m_) < 0: n_ = -n_                            # points back into the sweep (that side is cut)
    _, wid = PF.components(V, F)
    for b in dict.fromkeys(bands):
        ks = [k for k, bb in enumerate(bands) if bb == b]
        Fp = pcs[b]; cv = ((V[Fp] - m_) @ n_)
        Fe = Fp[(cv.min(1) < -1e-4) & (V[Fp][:, :, 0].mean(1) > 0)]        # any corner past the plane, left half
        if len(Fe) < 2: print(f'r{b}: no end region', flush=True); continue
        comps = PF.components(V, Fe)[0]; Fe = max(comps, key=len)
        if len(Fe) <= 3:
            # a few triangles (the groove's ends, 3 each, tapering to a point): a corner fill on the outline clipped at
            # the plane, snapped onto the end faces and the sweep's end row (a fitted face of its own sat 1.2-1.4 mm
            # off its neighbours: the slit at the groove end); the right one = its mirror (snapping there found no mirrored faces yet)
            cf = corner_fill(V, F, N, Fe, f'{sp["name"]}cf:r{b}eL', clip=(m_, n_))
            if cf: cf['corner_fill']['dense'] = True        # a long sliver: dense Coons sides
            if cf:
                res.append(cf); res.append(dict(name=f'{sp["name"]}cf:r{b}eR', mirror_of=cf['name']))   # mirrors are made last (after the end faces' mirrors)
            print(f'r{b}: end = corner fills over {len(Fe)} triangles', flush=True); continue
        X = np.vstack([G[-3:, c0_[k]:c0_[k] + ncol[k]].reshape(-1, 3) for k in ks])
        # Kunos's long thin triangles straddle the plane and reach up to 77 mm back over it: the end region's outline
        # then folds over itself in the fit plane and the trim cut a false opening (a 150 mm slot of daylight through
        # r0eL at the arch, 17 Nov). Clip the region 3 mm past the plane first (the exact plane cut trims the rest).
        Vc, Fc, Nc = clip_tris(V, Fe, N, m_, n_, 3e-3)
        if os.environ.get('BB_PN', '1' if sp.get('pn') else '0') == '1':
            # the end region's few big triangles: their corners alone let the fit pick a coarse face that dropped the
            # face's horizontal rib and round (a seam where the sweep, which has them, ends; 19 Nov). Dense points on
            # the PN surface (what Kunos's shading shows) are fit data too.
            Xd = pn_sample(Vc, Fc, Nc, int(os.environ.get('BB_PN_N', 5)))
            print(f'r{b}: end face data + {len(Xd)} PN points', flush=True)
            X = np.r_[X, Xd]
        try:
            e = PF.fit_panel(f'{sp["name"]}:r{b}eL', Vc, Fc, Nc, extra=X, extra_rep=3)
        except Exception as ex:
            print(f'r{b}: end face failed ({ex})', flush=True); continue
        e['cut_planes'] = [[(m_ * 1000).tolist(), n_.tolist()]]
        res.append(e); res.append(dict(name=f'{sp["name"]}:r{b}eR', mirror_of=f'{sp["name"]}:r{b}eL'))
        print(f'r{b}: end face over {len(Fe)} triangles (bands {ks})', flush=True)
    trims = [np.array(r['trim']) / 1000 for r in res if r.get('trim')]
    if trims and os.environ.get('BB_TRIM_SNAP', '1') == '1':
        # the band faces' trimmed ends are the edge their neighbours (the flare r5) meet: those pieces' outlines are
        # snapped onto it (panel_fit.master_snap, the edge given as segments) and fitted through it, so both faces end
        # on ONE edge (each on its own copy of Kunos's outline missed by ~1 mm, up to 7 at the rib: slivers of
        # daylight along the flare, 19 Nov). Only the dense end parts: the polygon's long sides are chords.
        sA_, sB_ = [], []
        for T in trims:
            a, b = T[:-1], T[1:]; ok = (np.linalg.norm(b - a, axis=1) < 0.01) & (np.sign(a[:, 0]) == np.sign(b[:, 0]))
            sA_.append(a[ok]); sB_.append(b[ok])
        PF._MASTER["bb:trim"] = (np.vstack(sA_), np.vstack(sB_)); os.environ['PF_MASTER'] = 'bb:trim'
        os.environ.setdefault('PF_MASTER_TOL', '0.005')   # the rib's bevel: Kunos's outline 2.5-5 mm off our face's end
        print(f'trim edges: {sum(len(a) for a in sA_)} segments are the master edge for the other pieces', flush=True)
    if os.environ.get('BB_OTHERS', '1') == '1':
        res += others(V, F, N, pcs, bands, sp['name'])
        if os.environ.get('PF_MASTER') == 'bb:trim': del os.environ['PF_MASTER']; os.environ.pop('PF_MASTER_TOL', None)
        # the part's other Kunos meshes (front: SUB0 = recess back panels + badge, SUB1 = slot inserts), per piece
        for k_, mn in enumerate(sp.get('extra', [])):
            V2, F2, N2 = PF.load_mesh(car, mn)
            print(f'== {mn}', flush=True)
            res += others(V2, F2, N2, PF.crease_pieces(V2, F2, N2), [], f'{sp["name"]}{k_}')
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    np.savez(os.path.join(out, 'grid.npz'), G=G, arcs=a_all, raw=R_, raw_arc=A_, ncol=ncol, bands=bands)
    print('saved', os.path.join(out, 'panels_fit.json'), flush=True)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'rear')
