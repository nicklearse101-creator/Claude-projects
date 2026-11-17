"""Cross-build join check (17 Nov): joins between two builds: A's open boundary edges near B (within 15 mm) -> gap to B's triangles, per A face;
and A's triangles lying ON B (centre within 0.5 mm of B, normals within 20 deg) = two owners.
    python build_joins.py A_build_dir_or_npz B_build_dir_or_npz"""
import sys, os; sys.path.insert(0, r'D:\Claude\Claude-\blender\kn5-study'); sys.path.append(r'D:\ClaudeData\pylibs')
import numpy as np
from exact_dist import point_to_tris
def load(p):
    if p.endswith('.npz'):
        d = np.load(p); P = d['P'] / (1000 if np.abs(d['P']).max() > 10 else 1)
        return {str(n): (P, d['F'][d['L'] == i]) for i, n in enumerate(d['names'])}
    M = np.load(os.path.join(p, 'panels_fit_mesh.npz')); out = {}
    for k in M.files:
        if k.endswith('_P'): out[k[:-2]] = (M[k], M[k[:-2] + '_F'])
    return out
A, B = load(sys.argv[1]), load(sys.argv[2])
TB = np.concatenate([P[F] for P, F in B.values()]); lo, hi = TB.reshape(-1, 3).min(0) - 0.015, TB.reshape(-1, 3).max(0) + 0.015
NB = np.cross(TB[:, 1] - TB[:, 0], TB[:, 2] - TB[:, 0]); NB /= np.maximum(np.linalg.norm(NB, axis=1), 1e-15)[:, None]
from scipy.spatial import cKDTree
cB = cKDTree(TB.mean(1))
print(f'{"A face":28s} {"edges near B":>12s}  gap median / p95 / max mm   overlap tris')
tot_ov = 0
for n, (P, F) in sorted(A.items()):
    if not len(F): continue
    e = np.sort(np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 1); u, c = np.unique(e, axis=0, return_counts=True); be = u[c == 1]
    M = (P[be[:, 0]] + P[be[:, 1]]) / 2
    near = np.all((M > lo) & (M < hi), 1)
    s = ''
    if near.any():
        d = point_to_tris(M[near], TB) * 1000; m = d < 15
        if m.any(): s = f'{m.sum():12d}  {np.median(d[m]):6.2f} / {np.percentile(d[m], 95):6.2f} / {d[m].max():6.2f}'
    C = P[F].mean(1); inb = np.all((C > lo) & (C < hi), 1); ov = 0
    if inb.any():
        dc = point_to_tris(C[inb], TB) * 1000; cand = np.where(inb)[0][dc < 0.5]
        if len(cand):
            NA = np.cross(P[F[cand, 1]] - P[F[cand, 0]], P[F[cand, 2]] - P[F[cand, 0]]); NA /= np.maximum(np.linalg.norm(NA, axis=1), 1e-15)[:, None]
            _, j = cB.query(C[cand]); ov = int((np.abs((NA * NB[j]).sum(1)) > np.cos(np.radians(20))).sum())
    tot_ov += ov
    if s or ov: print(f'{n:28s} {s:45s} {ov:6d}')
print('overlap triangles total', tot_ov)
