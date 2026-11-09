import sys, time, os
import numpy as np
import FreeCAD as App, Part
sys.path.insert(0, os.path.join(App.getUserAppDataDir(), 'Mod', 'CurvesWB', 'freecad'))
from Curves import gordon
S = np.load('D:/Claude/_scratch_research/kn5_study/blind/door_loft_c0_12.npz')['S']   # [8 sections, 43 pts]; crease at index 19
V = lambda p: App.Vector(*map(float, p))
def bs(pts):
    c = Part.BSplineCurve(); c.interpolate([V(p) for p in pts]); return c
out = {}
t = time.time()
for name, (a, b) in {'lower': (0, 19), 'upper': (19, 42)}.items():
    prof = [bs(s[a:b + 1]) for s in S]
    gi = sorted(set([a, (2 * a + b) // 3, (a + 2 * b) // 3, b]))
    guides = [bs(S[:, i]) for i in gi]
    net = gordon.InterpolateCurveNetwork(prof, guides, 1e-4, 1e-8)
    srf = net.surface()
    u0, u1, v0, v1 = srf.bounds()
    G = np.array([[tuple(srf.value(u0 + (u1 - u0) * i / 219, v0 + (v1 - v0) * j / 99)) for j in range(100)] for i in range(220)])
    out[name] = G
    print(name, 'gordon ok', srf.NbUPoles, 'x', srf.NbVPoles, 'poles; guides at', gi)
np.savez('D:/Claude/_scratch_research/kn5_study/blind/fc_gordon_door.npz', **out)
print('time', round(time.time() - t, 2))
