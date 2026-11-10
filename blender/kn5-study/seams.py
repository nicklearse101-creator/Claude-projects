"""Gaps along the joins between built faces (are the panels watertight?).

    python seams.py BUILD_DIR

For each face: its display mesh's boundary vertices; each one that lies within 5 mm of another face is on a
join (the rest are free panel edges). Reports per join: how far those boundary vertices are from the other
face (median / p95 / max, mm). 0 = watertight.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exact_dist import point_to_tris


def boundary_vertices(P, F):
    e = np.sort(np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=1)
    u, c = np.unique(e, axis=0, return_counts=True)
    return np.unique(u[c == 1])


def main():
    M = np.load(os.path.join(sys.argv[1], 'panels_fit_mesh.npz'))
    names = sorted({k[:-2] for k in M.files})
    faces = {n: (M[n + '_P'], M[n + '_F']) for n in names}
    rows = []
    for a in names:
        Pa, Fa = faces[a]; bv = Pa[boundary_vertices(Pa, Fa)]
        for b in names:
            if b == a: continue
            Pb, Fb = faces[b]
            d = point_to_tris(bv, Pb[Fb], cap=0.005) * 1000
            j = d < 5
            if j.sum() >= 5:
                rows.append((a, b, j.sum(), np.median(d[j]), np.percentile(d[j], 95), d[j].max()))
    print(f"{'face':28s} {'joins':28s} {'pts':>4s} {'median':>7s} {'p95':>6s} {'max':>6s}  (mm)")
    for a, b, n, md, p9, mx in rows:
        print(f"{a.split(':', 1)[1]:28s} {b.split(':', 1)[1]:28s} {n:4d} {md:7.2f} {p9:6.2f} {mx:6.2f}")


if __name__ == '__main__':
    main()
