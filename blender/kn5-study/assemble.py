"""Whole car from the regress builds (step 5 of the plan): every part's mesh, left-only builds mirrored to the right,
one npz (P metres, F, N, L part label), plus grey pictures from all sides next to Kunos's shell.
    python assemble.py CAR_DIR REGRESS_DIR OUT.npz [OUT.png]"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panel_fit as PF

MIR = np.array([-1.0, 1.0, 1.0])
# part -> mesh files (relative to REGRESS_DIR); the first that exists is used
PARTS = {
    'door': ['door/panels_fit_mesh.npz'],
    'wing': ['wing/panels_fit_mesh.npz', 'wing/fill/panels_fit_mesh.npz'],
    'quarter': ['quarter/build.npz'],
    'roof': ['roof/build.npz'],
    'hatch': ['hatch/build.npz'],
    'bonnet': ['bonnet/build_full.npz', 'bonnet/build.npz'],
    'sill': ['sill/panels_fit_mesh.npz'],
    'tail': ['tail/build.npz'],
    'rearband': ['rearband/build.npz'],
    'frontband': ['frontband/build.npz'],
    'wingband': ['wingband/build.npz'],
    'frontbumper': ['frontbumper/build.npz'],
    'rearbumper': ['rearbumper/build.npz'],
}
KUNOS = ['GEO_body', 'GEO_extdoorL_SUB0', 'GEO_extdoorL_SUB1', 'GEO_extdoorR_SUB0', 'GEO_extdoorR_SUB1', 'GEO_hood_SUB0',
         'GEO_hood_SUB1', 'GEO_hood_SUB2', 'GEO_frontbumper_SUB0', 'GEO_frontbumper_SUB1', 'GEO_frontbumper_SUB2', 'GEO_rearbumper']


def load_any(p):
    """(P metres, F, N) from a build.npz (P/F/N) or a panels_fit_mesh.npz (+ its _normals.npz): faces concatenated"""
    d = np.load(p)
    if 'P' in d.files:
        P = d['P'] / (1000 if np.abs(d['P']).max() > 10 else 1)
        N = d['N'] if 'N' in d.files else np.zeros_like(P)
        return P, d['F'], N
    nf = p.replace('_mesh.npz', '_normals.npz'); dn = np.load(nf) if os.path.exists(nf) else None
    Ps, Fs, Ns, off = [], [], [], 0
    for k in sorted({k[:-2] for k in d.files}):
        P = d[k + '_P'] / (1000 if np.abs(d[k + '_P']).max() > 10 else 1)
        Ps.append(P); Fs.append(d[k + '_F'] + off); off += len(P)
        Ns.append(dn[k] if dn is not None and k in dn.files and len(dn[k]) == len(P) else np.zeros_like(P))
    return np.concatenate(Ps), np.concatenate(Fs), np.concatenate(Ns)


def inside(poly, Q):
    """points Q (k x 2) inside the closed polygon poly (n x 2): even-odd ray casting"""
    a, b = poly, np.roll(poly, -1, axis=0); r = np.zeros(len(Q), bool)
    for (x0, y0), (x1, y1) in zip(a, b):
        c = (y0 > Q[:, 1]) != (y1 > Q[:, 1])
        xi = x0 + (Q[:, 1] - y0) * (x1 - x0) / ((y1 - y0) if y1 != y0 else 1e-12)
        r ^= c & (Q[:, 0] < xi)
    return r


def vnormals(P, F):
    n = np.zeros_like(P); t = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    for c in range(3): np.add.at(n, F[:, c], t)
    return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]


def main():
    car, R, out = sys.argv[1], sys.argv[2], sys.argv[3]
    if os.environ.get('PICTURE_ONLY') == '1':                  # re-draw the picture from an existing OUT.npz
        d = np.load(out); picture(car, d['P'], d['F'], d['N'], sys.argv[4]); return
    Ps, Fs, Ns, Ls, names, off = [], [], [], [], [], 0
    for i, (part, files) in enumerate(PARTS.items()):
        got = [load_any(os.path.join(R, f)) for f in files if os.path.exists(os.path.join(R, f))]
        if not got: print(f'{part:12s} MISSING'); continue
        P = np.concatenate([g[0] for g in got]); F = np.concatenate([g[1] + sum(len(h[0]) for h in got[:j]) for j, g in enumerate(got)])
        N = np.concatenate([g[2] for g in got])
        if part == 'wing' and os.path.exists(os.path.join(R, 'wingband/band_grid.npz')) and os.path.exists(os.path.join(R, 'wingband/build.npz')):
            # the wing band (frontband_build.py wing side, 25 Nov) replaces the wing's faces over its footprint: wing
            # triangles whose centroid lies inside the band's outline (side view, z-y) and outside its holes are dropped
            bg = np.load(os.path.join(R, 'wingband/band_grid.npz')); E = bg['outline']
            # (only triangles wholly inside: on the edge the two overlap by part of a triangle - no sawtooth gap)
            if 'end_wing' in bg.files and os.environ.get('ASM_EXACT', '1') == '1':
                # (26 Nov) exact: the wing cut ON the band's outline (B-A straight across the groove end), crossing
                # triangles split there; the flat end face between the band's edge B-C-A and the wing's surface on A-B
                import wingend as WE
                Pb_, Fb_, _ = load_any(os.path.join(R, 'wingband/build.npz'))
                if (np.linalg.norm(N, axis=1) < 0.5).any(): N = vnormals(P, F)
                P, F, N, n_in, n_x = WE.clip_mesh(P, F, N, bg['end_wing'])
                # the wing feathered onto the band's edge (their surfaces met 0.3-4 mm apart: a line along the seam)
                A_, B_ = bg['end_ABC'][0], bg['end_ABC'][2]
                Nb_ = load_any(os.path.join(R, 'wingband/build.npz'))[2]
                Vk_, Fk_, _ = PF.load_mesh(car, 'GEO_body', raw=True); Fk_ = Fk_[(Vk_[Fk_][:, :, 0].min(1) > 0.7) & (Vk_[Fk_][:, :, 2].min(1) > 0.85) & (Vk_[Fk_][:, :, 2].max(1) < 1.05) & (Vk_[Fk_][:, :, 1].min(1) > 0.5)]
                if (np.linalg.norm(Nb_, axis=1) < 0.5).any(): Nb_ = vnormals(Pb_, Fb_)
                P0_ = P; P, n_f, dmax, _ = WE.feather(P, F, bg['end_wing'], Pb_, Fb_, skip_seg=(B_, A_), ymin=0.40, zmin=0.705, seg_target=(Vk_, Fk_))   # the arch edge above y 0.40 and the top seam (Kunos continuous across both); the door shut (z 0.70), the sill end and the lip's 25 mm step low down are left
                mv = np.abs(P[:, 0] - P0_[:, 0]) > 0
                if mv.any(): N[mv] = vnormals(P, F)[mv]
                _, _, _, N = WE.feather(P0_, F, bg['end_wing'], Pb_, Fb_, skip_seg=(B_, A_), ymin=0.40, zmin=0.705, N=N, Nb=Nb_, seg_target=(Vk_, Fk_))
                print(f'wing: {n_f} vertices feathered onto the band edge (steps up to {dmax * 1e3:.2f} mm closed)')
                Pe, Fe, Ne, gap = WE.end_face(Pb_, Fb_, P, F, bg['end_ABC'])
                print(f'wing: {n_in} triangles under the wing band dropped, {n_x} split on its outline; end face {len(Fe)} tris (band / wing x at B, A apart {gap[0]:.2f} / {gap[1]:.2f} mm)')
                F = np.r_[F, Fe + len(P)]; P = np.r_[P, Pe]; N = np.r_[N, Ne]
                E = None
            if E is None: pass
            else:
             iv = inside(E[:, [2, 1]], P[:, [2, 1]]) & (P[:, 0] > 0.6)
             for k in [k for k in bg.files if k.startswith('hole')]: iv &= ~inside(bg[k][:, [2, 1]], P[:, [2, 1]])
             inn = iv[F].all(1)
             F = F[~inn]; print(f'wing: {inn.sum()} triangles under the wing band dropped')
        if (np.linalg.norm(N, axis=1) < 0.5).any(): N = vnormals(P, F)
        left_only = P[:, 0].min() > -0.05
        if left_only:                                    # mirror: x -> -x, winding flipped
            n0 = len(P); P = np.r_[P, P * MIR]; N = np.r_[N, N * MIR]; F = np.r_[F, F[:, [0, 2, 1]] + n0]
        Ps.append(P); Fs.append(F + off); Ns.append(N); Ls.append(np.full(len(F), i)); names.append(part); off += len(P)
        print(f'{part:12s} {len(F):8d} tris  x {P[:, 0].min():+.2f}..{P[:, 0].max():+.2f}' + ('  (left half mirrored)' if left_only else ''))
    P, F, N, L = np.concatenate(Ps), np.concatenate(Fs), np.concatenate(Ns), np.concatenate(Ls)
    np.savez_compressed(out, P=P, F=F, N=N, L=L, names=np.array(names))
    print(f'car: {len(F)} tris -> {out}')
    # score: every Kunos shell vertex -> the nearest of ours
    from exact_dist import point_to_tris
    from scipy.spatial import cKDTree
    TB = P[F]; tc = cKDTree(TB.mean(1))
    for kn in KUNOS:
        try: V, Fk, _ = PF.load_mesh(car, kn, raw=True)
        except StopIteration: continue
        X = V[np.unique(Fk)]
        e = np.empty(len(X))
        for j in range(0, len(X), 2000):            # nearest 64 triangles by centroid, exact distance to those
            Xj = X[j:j + 2000]; ii = tc.query(Xj, 64)[1]
            e[j:j + 2000] = [point_to_tris(x[None], TB[k_]).min() for x, k_ in zip(Xj, ii)]
        e *= 1000
        print(f'  {kn:24s} {len(X):5d} vertices: median {np.median(e):.2f}  within 1 / 3 mm {np.mean(e < 1) * 100:5.1f} / {np.mean(e < 3) * 100:5.1f} %')
    if len(sys.argv) > 4: picture(car, P, F, N, sys.argv[4])


def picture(car, P, F, N, png):
    if True:
        from grey_render import render
        from PIL import Image, ImageDraw
        g = {'render': render}
        Vs, Fk_, Nk, o_ = [], [], [], 0
        for kn in KUNOS:
            try: V, Fk, Nn = PF.load_mesh(car, kn, raw=True)
            except StopIteration: continue
            Vs.append(V); Fk_.append(Fk + o_); Nk.append(Nn); o_ += len(V)
        V, Fk, Nk = np.concatenate(Vs), np.concatenate(Fk_), np.concatenate(Nk)
        views = [([1, 0.5, 1], [0, 0.7, 0], 2.4), ([1, 0.5, -1], [0, 0.7, 0], 2.4), ([1, 0.05, 0], [0, 0.7, 0], 2.3), ([0, 1, 0.001], [0, 0.7, 0], 2.3)]
        img = Image.new('RGB', (1600, 800 * len(views)), 'white')
        for i, (eye, cen, half) in enumerate(views):
            img.paste(g['render'](V, Fk, Nk, eye, np.array(cen, float), half), (0, 800 * i))
            img.paste(g['render'](P, F, N, eye, np.array(cen, float), half), (800, 800 * i))
        d_ = ImageDraw.Draw(img); d_.text((10, 10), 'Kunos', fill=(0, 0, 0)); d_.text((810, 10), 'ours (CAD panels)', fill=(0, 0, 0))
        img.save(png); print('picture', png)


if __name__ == '__main__':
    main()
