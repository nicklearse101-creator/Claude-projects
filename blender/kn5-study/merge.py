"""Merge a sub-build (BUILD/fill) into the main build's mesh and normals:  python merge.py BUILD_DIR [SUB=fill]"""
import sys, os
import numpy as np
build = sys.argv[1]; sub = os.path.join(build, sys.argv[2] if len(sys.argv) > 2 else 'fill')
for fn in ('panels_fit_mesh.npz', 'panels_fit_normals.npz'):
    if not os.path.exists(os.path.join(sub, fn)): continue
    a = dict(np.load(os.path.join(build, fn))); b = dict(np.load(os.path.join(sub, fn)))
    a.update(b); np.savez(os.path.join(build, fn), **a)
    print(fn, '+', len(b), 'arrays')
