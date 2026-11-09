"""Panel-by-panel CAD build, step 2 (freecadcmd via fcrun.sh): one B-spline surface per strip, exact
through its feature-aligned sections; sampled straight into quads. Env: CAD_IN (npz), CAD_OUT (prefix)."""
import os, time
import numpy as np
import FreeCAD as App, Part
d = np.load(os.environ['CAD_IN']); OUT = os.environ['CAD_OUT']
t0 = time.time(); out = {}; faces = []; bad = 0
for k in d.files:
    G = np.asarray(d[k], float) * 1000.0           # mm for OpenCASCADE
    ns, nv, _ = G.shape
    try:
        s = Part.BSplineSurface()
        s.interpolate([[App.Vector(*p) for p in row] for row in G])
        faces.append(s.toShape())
        nu, nvv = max(ns * 2, 4), max(nv * 2 - 1, 3)
        u0, u1, v0, v1 = s.bounds()
        P = np.array([[tuple(s.value(u0 + (u1 - u0) * i / (nu - 1), v0 + (v1 - v0) * j / (nvv - 1))) for j in range(nvv)] for i in range(nu)]) / 1000.0
        lo, hi = G.min((0, 1)) / 1000.0 - 0.02, G.max((0, 1)) / 1000.0 + 0.02
        if (P < lo).any() or (P > hi).any():     # B-spline overshoot: fall back to the sections themselves
            bad += 1
            Gm = G / 1000.0
            r = np.linspace(0, ns - 1, nu); i0 = np.clip(np.floor(r).astype(int), 0, ns - 2); w = (r - i0)[:, None, None]
            P = (1 - w) * Gm[i0] + w * Gm[i0 + 1]
            P = np.stack([np.c_[[np.interp(np.linspace(0, nv - 1, nvv), np.arange(nv), row[:, q]) for q in range(3)]].T for row in P])
        out[k] = P
    except Exception as e:
        bad += 1; print('strip', k, 'failed:', e)
Part.makeCompound(faces).exportStep(OUT + '.step')
np.savez(OUT + '.npz', **out)
print('strips', len(out), 'fallbacks', bad, 'time', round(time.time() - t0, 1), 's')
