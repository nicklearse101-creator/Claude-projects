"""Pack a build (panels_fit_mesh.npz + exact normals) into one npz for Blender: P, F, N (normals per vertex), L (face
label per triangle), names.   python pack_build.py BUILD_DIR OUT.npz"""
import sys, os
import numpy as np
b, out = sys.argv[1], sys.argv[2]
M = np.load(os.path.join(b, 'panels_fit_mesh.npz')); Nn = np.load(os.path.join(b, 'panels_fit_normals.npz'))
names = sorted({k[:-2] for k in M.files}); P, F, N, L, off = [], [], [], [], 0
for i, n in enumerate(names):
    p, f = M[n + '_P'], M[n + '_F']; P.append(p); F.append(f + off); L += [i] * len(f); off += len(p)
    k = [x for x in Nn.files if x.startswith(n)]
    N.append(Nn[k[0]] if k and Nn[k[0]].shape == p.shape else np.zeros_like(p))
np.savez(out, P=np.concatenate(P), F=np.concatenate(F), N=np.concatenate(N), L=np.array(L), names=np.array(names))
print(out, len(names), 'faces', off, 'points')
