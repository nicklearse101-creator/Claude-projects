"""Fill holes left by a build: original areas no built face covers get a filler face fitted to them.

    python fill_holes.py CAR_DIR BUILD_DIR MESHNAME [MESHNAME ...]     (PF_CLIP as for the build)

1. Original triangles whose centre is more than 2.5 mm from every built face = uncovered.
2. Connected groups of them with at least 5 cm2 = holes.
3. Each hole: one surface over its own plane, fitted to the original vertices of the hole (plus a 15 mm rim
   round it, so it meets the faces around it), trimmed to the hole's own outline.
4. Writes BUILD_DIR/fill/panels_fit.json; build it with panel_fit_freecad.py, then merge.py BUILD_DIR adds the
   meshes to the main build.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panel_fit as PF
from exact_dist import point_to_tris


def main():
    car, build = sys.argv[1], sys.argv[2]
    M = np.load(os.path.join(build, 'panels_fit_mesh.npz'))
    Fall = np.concatenate([M[k[:-2] + '_P'][M[k[:-2] + '_F']] for k in M.files if k.endswith('_P')])
    res = []
    for name in sys.argv[3:]:
        V, F, N = PF.load_mesh(car, name); T = V[F]
        A = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        d = point_to_tris(T.mean(1), Fall, cap=0.01) * 1000
        hole = d > 2.5
        # a far CENTRE is not a hole if a built face lies right over it along the triangle's normal: Kunos's long flat
        # triangles cut chords across curves (100-150 mm triangles sag 3-7 mm off a correct surface); a filler laid
        # there doubles a good face (ragged lamp-top corner on the rear quarter). Hole = the normal line through the
        # centre meets no built face within 20 mm.
        if hole.any() and os.environ.get('FH_CHORD', '1') == '1':
            from scipy.spatial import cKDTree
            cB = Fall.mean(1); tree = cKDTree(cB); nT = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
            nT /= np.maximum(np.linalg.norm(nT, axis=1), 1e-12)[:, None]
            covered = 0
            # chord sag only where the triangle's CORNERS are on our faces (< 1.5 mm): then its centre is off only because
            # the flat triangle cuts across a curve. Corners off = a real miss, filled as before (the wing needs those)
            idx_ = np.where(hole)[0]
            dvx = point_to_tris(T[idx_].reshape(-1, 3), Fall, cap=0.01).reshape(-1, 3) * 1000
            corner_ok = dict(zip(idx_, (dvx < 1.5).all(1)))
            for i in np.where(hole)[0]:
                if not corner_ok[i]: continue
                o_ = T[i].mean(0); dn = nT[i]
                cand = Fall[tree.query_ball_point(o_, 0.03 + 0.5 * np.linalg.norm(T[i] - o_, axis=1).max())]
                if not len(cand): continue
                e1, e2 = cand[:, 1] - cand[:, 0], cand[:, 2] - cand[:, 0]; pv = np.cross(dn, e2); det = (e1 * pv).sum(1)
                ok_ = np.abs(det) > 1e-12; inv = np.where(ok_, 1 / np.where(ok_, det, 1), 0); tv = o_ - cand[:, 0]
                uu = (tv * pv).sum(1) * inv; qv = np.cross(tv, e1); vv = (qv * dn).sum(1) * inv; tt = (qv * e2).sum(1) * inv
                if (ok_ & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (np.abs(tt) < 0.02)).any():
                    hole[i] = False; covered += 1
            if covered: print(f'{name}: {covered} far triangles have a built face over them (chord sag, not holes)')
        if not hole.any(): continue
        comps, _ = PF.components(V, F[hole])
        for ci, Fh in enumerate(sorted(comps, key=len, reverse=True)):
            Th = V[Fh]; Ah = 0.5 * np.linalg.norm(np.cross(Th[:, 1] - Th[:, 0], Th[:, 2] - Th[:, 0]), axis=1).sum()
            if Ah < 5e-4: continue
            # rim: neighbouring triangles within 15 mm, for data only (the face is trimmed to the hole's outline)
            c = T.mean(1); ch = Th.mean(1)
            near = np.zeros(len(F), bool)
            for s in range(0, len(F), 2000):
                near[s:s + 2000] = (np.linalg.norm(c[s:s + 2000, None] - ch[None], axis=2) < 0.015).any(1)
            try:
                try:
                    e = PF.fit_panel(f'{name}:fill{ci}', V, Fh, N, verbose=True)
                except Exception:          # a strip too thin for a closed outline (a wall): outline of hole + rim
                    Fr_ = F[near & ~(point_to_tris(T.mean(1), Fall, cap=0.01) * 1000 < 0.5)]
                    e = PF.fit_panel(f'{name}:fill{ci}', V, Fr_, N, verbose=True)
                u = np.unique(F[near]); fr = [np.array(x) for x in e['frame']]
                S = PF.to_plane(V[u], fr)
                dom = [S[:, 0].min() - 0.02, S[:, 0].max() + 0.02, S[:, 1].min() - 0.02, S[:, 1].max() + 0.02]
                try:
                    f, r, cv = PF.select_fit(S, dom)
                except ValueError:         # a few big triangles: too few vertices to cross-check - a plain 4x4
                    f = PF.fit_surface(S, dom, 4, 4, 1e-4); r = np.abs(PF.eval_surface(f, S[:, 0], S[:, 1]) - S[:, 2])
                mm = lambda a: (np.asarray(a) * 1000).tolist()
                e.update(dom=mm(dom), nu=f['nu'], nv=f['nv'], ku=mm(f['ku']), kv=mm(f['kv']),
                         poles=mm(np.stack(list(np.meshgrid(f['gu'], f['gv'], indexing='ij')) + [f['H']], -1)))
                print(f'  hole {ci}: {len(Fh)} triangles, {Ah*1e4:.0f} cm2 -> filler {f["nu"]}x{f["nv"]}, fit p95 {np.percentile(r, 95)*1000:.2f} mm')
                res.append(e)
            except Exception as ex:
                import traceback; traceback.print_exc(limit=3); print(f"  hole {ci}: {Ah*1e4:.0f} cm2 not filled ({ex})")
    out = os.path.join(build, 'fill'); os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, 'panels_fit.json'), 'w'))
    print(f'{len(res)} filler faces -> {out}')


if __name__ == '__main__':
    main()
