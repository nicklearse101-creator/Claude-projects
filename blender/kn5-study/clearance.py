"""Clearance of a built panel against the Kunos parts around it (research: Bonnet surfacing.md step 13).

    python clearance.py CAR_DIR BUILD.npz KUNOS_MESH[,KUNOS_MESH...] [NEIGHBOUR ...]

For each neighbour mesh (default: every mesh with > 20 vertices within 40 mm of the Kunos panel's box): its
vertices near the panel -> distance to OUR faces and to the KUNOS panel meshes (closest approach, p5). A neighbour
vertex is INSIDE ours when it lies behind our surface (along our normal at the nearest vertex) within 5 mm: a
penetration. Side gap to the wing (bonnet): GEO_body vertices beside the side returns, per 100 mm station.
"""
import sys, os, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panel_fit as PF
from panel_fit import KN5
if os.path.isdir(r'D:/ClaudeData/pylibs') and r'D:/ClaudeData/pylibs' not in sys.path: sys.path.append(r'D:/ClaudeData/pylibs')
from exact_dist import point_to_tris


def main():
    car, build, kmeshes = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
    d = np.load(build); P, F, N = d['P'], d['F'], d['N']
    kn5 = sorted(glob.glob(os.path.join(car, '*.kn5')), key=os.path.getsize)[-1]; k = KN5(kn5, load_textures=False)
    M = {m.name: m for m in k.meshes}
    KT = np.concatenate([M[n].pos.astype(float)[M[n].idx.reshape(-1, 3)] for n in kmeshes])
    KP = np.concatenate([M[n].pos.astype(float) for n in kmeshes]); KN = np.concatenate([M[n].nrm.astype(float) for n in kmeshes])
    lo, hi = KT.reshape(-1, 3).min(0) - 0.04, KT.reshape(-1, 3).max(0) + 0.04
    names = sys.argv[4:] or [m.name for m in k.meshes if m.name not in kmeshes and
                             np.sum(np.all((m.pos >= lo) & (m.pos <= hi), axis=1)) > 20]
    TB = P[F]
    from scipy.spatial import cKDTree
    tree = cKDTree(P); ktree = cKDTree(KP)
    print(f'{"neighbour":30s} {"verts":>6s}  {"ours min / p5":>15s}  {"Kunos min / p5":>15s}  inside ours / inside Kunos (same test)')
    for n in names:
        V = M[n].pos.astype(float); V = V[np.all((V >= lo) & (V <= hi), axis=1)]
        if not len(V): continue
        do = point_to_tris(V, TB) * 1000; dk = point_to_tris(V, KT) * 1000
        _, j = tree.query(V); s = ((V - P[j]) * N[j]).sum(1) * 1000
        inside = (s < -0.05) & (do < 5) & (dk > 0.05)        # behind our surface, but not touching Kunos's (shared seats)
        _, jk = ktree.query(V); sk = ((V - KP[jk]) * KN[jk]).sum(1) * 1000; ink = (sk < -0.05) & (dk < 5)
        print(f'{n:30s} {len(V):6d}  {do.min():6.2f} / {np.percentile(do, 5):6.2f}  {dk.min():6.2f} / {np.percentile(dk, 5):6.2f}  '
              f'{inside.sum():4d} / {ink.sum():4d}' + (f' (deepest {do[inside].max():.2f} mm at {np.round(V[inside][np.argmax(do[inside])] * 1000)})' if inside.any() else ''))
    # side gap: GEO_body vertices outboard of the side returns, per station along z
    if 'GEO_body' in M:
        V = M['GEO_body'].pos.astype(float); X = np.abs(P[:, 0])
        side = X > X.max() - 0.003                           # our outermost faces (the side returns)
        print('side gap to GEO_body (wing), per station: z, ours, Kunos (mm)')
        Kv = KT.reshape(-1, 3)
        for z in np.arange(0.75, 1.75, 0.1):
            ms = side & (np.abs(P[:, 2] - z) < 0.02)
            mb = (np.abs(V[:, 2] - z) < 0.02) & (np.abs(V[:, 0]) > X.max()) & (np.abs(V[:, 0]) < X.max() + 0.02) & (V[:, 1] > P[ms, 1].min() - 0.01 if ms.any() else False)
            if not ms.any() or not mb.any(): continue
            mk = (np.abs(Kv[:, 2] - z) < 0.02) & (np.abs(Kv[:, 0]) > np.abs(Kv[:, 0]).max() - 0.003)
            go = (np.abs(V[mb, 0]).min() - X[ms].max()) * 1000
            gk = (np.abs(V[mb, 0]).min() - np.abs(Kv[mk, 0]).max()) * 1000 if mk.any() else np.nan
            print(f'   z {z * 1000:5.0f}: {go:5.2f}  {gk:5.2f}')


if __name__ == '__main__':
    main()
