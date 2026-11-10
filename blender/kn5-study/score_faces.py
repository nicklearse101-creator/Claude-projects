"""Exact two-way score of panel_fit faces against the original mesh, face by face.

    python score_faces.py CAR_DIR BUILD_DIR MESHNAME [MESHNAME ...]

BUILD_DIR holds panels_fit_mesh.npz (from panel_fit_freecad.py). For each built face:
  ours -> truth : every vertex of our display mesh to the nearest original triangle (is our face where the car is?)
  truth -> ours : every original vertex near the face to our face (does our face cover the car there?)
plus the face area against the original area it covers. Distances in mm, capped at 20 mm.
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
    print(f"{'face':30s} {'area m2':>8s} {'ours->truth p95/max':>20s} {'truth->ours p95':>16s}")
    for n in names:
        P, F = M[n + '_P'], M[n + '_F']; allP.append(P)
        d1 = point_to_tris(P, T) * 1000
        # original triangles whose centre is within 3 mm of our face: the area this face stands for
        near = point_to_tris(T.mean(1), P[F]) * 1000 < 3
        tv = T[near].reshape(-1, 3)
        d2 = point_to_tris(tv, P[F]) * 1000 if len(tv) else np.zeros(1)
        print(f"{n:30s} {tri_area(P[F]).sum():8.4f} {np.percentile(d1, 95):9.2f} /{d1.max():6.2f} {np.percentile(d2, 95):12.2f}"
              f"   (orig area near it {tri_area(T[near]).sum():.4f})")
    # coverage: how much of the original is within 1 / 3 mm of SOME face of ours
    Fall = np.concatenate([M[n + '_P'][M[n + '_F']] for n in names])
    dc = point_to_tris(T.mean(1), Fall) * 1000; A = tri_area(T)
    print(f"original area covered within 1 mm: {A[dc < 1].sum() / A.sum() * 100:.1f} %, within 3 mm: {A[dc < 3].sum() / A.sum() * 100:.1f} %")


if __name__ == '__main__':
    main()
