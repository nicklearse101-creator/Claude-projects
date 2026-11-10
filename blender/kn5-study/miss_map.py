"""Where a build misses the original: the original's triangles coloured by distance to the nearest built face
(green < 1 mm, yellow < 3 mm, orange < 6 mm, red beyond), drawn flat in side / top / rear views, each built face
labelled at its centre. Plain PIL, no Blender.

    python miss_map.py CAR_DIR BUILD_DIR OUT.png MESHNAME [MESHNAME ...]     (PF_CLIP as for the build)
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_fit import load_mesh
from exact_dist import point_to_tris


def main():
    car, build, out = sys.argv[1:4]
    T = np.concatenate([(lambda V, F, N: V[F])(*load_mesh(car, n)) for n in sys.argv[4:]])
    M = np.load(os.path.join(build, 'panels_fit_mesh.npz'))
    names = sorted({k[:-2] for k in M.files})
    Fall = np.concatenate([M[n + '_P'][M[n + '_F']] for n in names])
    d = point_to_tris(T.mean(1), Fall, cap=0.02) * 1000
    col = np.where(d[:, None] < 1, [[60, 170, 75]], np.where(d[:, None] < 3, [[240, 210, 40]],
                   np.where(d[:, None] < 6, [[245, 130, 48]], [[220, 30, 40]])))
    lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0); S = 600
    views = [('side', 2, 1, -1, 0), ('top', 2, 0, -1, 1), ('rear', 0, 1, 1, 2)]    # rear: seen from behind
    H = sum(int((hi[k] - lo[k]) * S) + 30 for _, _, k, _, _ in views)
    W = max(int((hi[j] - lo[j]) * S) for _, j, _, _, _ in views) + 20
    img = Image.new('RGB', (W, H + 10), 'white'); dr = ImageDraw.Draw(img); oy = 20
    for title, j, k, sj, ax in views:
        def P(p): return (10 + sj * (p[..., j] - (hi[j] if sj < 0 else lo[j])) * S, oy + (hi[k] - p[..., k]) * S)
        # paint far-from-viewer first: side view seen from +x (outside left), top from +y, rear from -z
        depth = T.mean(1)[:, ax] * (-1 if ax == 2 else 1)
        for i in np.argsort(depth):
            x_, y_ = P(T[i]); dr.polygon(list(zip(x_, y_)), fill=tuple(int(c) for c in col[i]), outline=(90, 90, 90))
        dr.text((10, oy - 15), title, fill='black'); oy += int((hi[k] - lo[k]) * S) + 30
    img.save(out)
    A = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    # vertices lie on the designer's surface; Kunos's long flat facets are chords between them (a 600 mm triangle
    # across a curved strip is 'missed' by a correct smooth surface), so report both
    U = np.unique(T.reshape(-1, 3), axis=0); dv = point_to_tris(U, Fall, cap=0.02) * 1000
    print(f'{out}: area within 1 mm {A[d < 1].sum() / A.sum() * 100:.1f} %, 3 mm {A[d < 3].sum() / A.sum() * 100:.1f} %; '
          f'vertices within 1 mm {(dv < 1).mean() * 100:.1f} %, 3 mm {(dv < 3).mean() * 100:.1f} % (median {np.median(dv):.2f} mm)')


if __name__ == '__main__':
    main()
