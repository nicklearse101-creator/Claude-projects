"""A left-only build plus its mirror image (x -> -x), one npz: P (m), F, N (and L, names when present).
    python mirror_build.py IN.npz OUT.npz
Used as the MASTER for a build that spans both halves (the tail panel against the quarter, which is built left only)."""
import sys, numpy as np
d = np.load(sys.argv[1]); P = d['P'] / (1000 if np.abs(d['P']).max() > 10 else 1); F = d['F']
N = d['N'] if 'N' in d.files else np.zeros_like(P)
M = np.array([-1.0, 1.0, 1.0])
out = dict(P=np.r_[P, P * M], F=np.r_[F, F[:, [0, 2, 1]] + len(P)], N=np.r_[N, N * M])
if 'L' in d.files: out['L'] = np.r_[d['L'], d['L']]
if 'names' in d.files: out['names'] = d['names']
np.savez(sys.argv[2], **out); print(sys.argv[2], len(out['P']), 'points', len(out['F']), 'triangles')
