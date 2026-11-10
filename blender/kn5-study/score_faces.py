"""Exact two-way score of panel_fit faces against the original mesh, face by face.

    python score_faces.py CAR_DIR BUILD_DIR MESHNAME [MESHNAME ...]

BUILD_DIR holds panels_fit_mesh.npz (from panel_fit_freecad.py). For each built face:
  ours -> truth : every vertex of our display mesh to the nearest original triangle (is our face where the car is?)
and for the whole build, truth -> ours as coverage: the share of the original's area within 1 / 3 mm of SOME face
of ours (per-face truth -> ours is not meaningful: Kunos triangles run 40-200 mm, so original triangles near a
face reach into its neighbours). Distances in mm, capped at 20 mm.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panel_fit import load_mesh
from exact_dist import point_to_tris


def tri_area(T):
    return 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)


def main():
    car, build = sys.argv[1], sys.argv[2]
    T = np.concatenate([(lambda V, F, N: V[F])(*load_mesh(car, n)) for n in sys.argv[3:]])
    M = np.load(os.path.join(build, 'panels_fit_mesh.npz'))
    names = sorted({k[:-2] for k in M.files})
    allP = []
    print(f"{'face':30s} {'area m2':>8s} {'ours->truth median/p95/max':>27s}")
    for n in names:
        P, F = M[n + '_P'], M[n + '_F']
        d1 = point_to_tris(P, T) * 1000
        print(f"{n:30s} {tri_area(P[F]).sum():8.4f} {np.median(d1):9.2f} /{np.percentile(d1, 95):6.2f} /{d1.max():6.2f}")
    # coverage: how much of the original is within 1 / 3 mm of SOME face of ours
    Fall = np.concatenate([M[n + '_P'][M[n + '_F']] for n in names])
    dc = point_to_tris(T.mean(1), Fall) * 1000; A = tri_area(T)
    print(f"original area covered within 1 mm: {A[dc < 1].sum() / A.sum() * 100:.1f} %, within 3 mm: {A[dc < 3].sum() / A.sum() * 100:.1f} %")


if __name__ == '__main__':
    main()
