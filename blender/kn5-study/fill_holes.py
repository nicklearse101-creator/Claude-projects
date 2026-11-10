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
