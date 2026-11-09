import sys, time
import numpy as np
import FreeCAD as App, Part
print('FreeCAD', App.Version()[:3])
d = np.load('D:/Claude/_scratch_research/kn5_study/blind/door_loft_c0_12.npz'); S = d['S']   # 8 sections x 43 pts (Blender frame)
t = time.time()
curves = []
for s in S:
    pts = [App.Vector(*map(float, p)) for p in s]
    c = Part.BSplineCurve(); c.interpolate(pts); curves.append(c)
# 1) loft through the sections (OCC ThruSections, smooth)
wires = [Part.Wire([c.toShape()]) for c in curves]
loft = Part.makeLoft(wires, False, False)          # solid=False, ruled=False
face = loft.Faces[0]; surf = face.Surface
print('loft:', type(surf).__name__, 'faces', len(loft.Faces), round(time.time() - t, 2), 's')
# 2) B-spline surface through the section points directly (interpolating, exact)
grid = np.array(S)
bs = Part.BSplineSurface()
bs.interpolate([[App.Vector(*map(float, p)) for p in row] for row in grid])
print('interpolated bspline surface: degree', bs.UDegree, bs.VDegree, 'poles', bs.NbUPoles, 'x', bs.NbVPoles)
# evaluate both on a quad grid and save
def sample(s, nu=220, nv=120):
    u0, u1, v0, v1 = s.bounds()
    return np.array([[tuple(s.value(u0 + (u1 - u0) * i / (nu - 1), v0 + (v1 - v0) * j / (nv - 1))) for j in range(nv)] for i in range(nu)])
np.savez('D:/Claude/_scratch_research/kn5_study/blind/fc_door.npz', loft=sample(surf), bspl=sample(bs))
# 3) is the Gordon / Coons machinery available?
import inspect
print('GeomFill in Part:', [n for n in dir(Part) if 'Fill' in n or 'Gordon' in n or 'Coons' in n][:10])
try:
    import Surface; print('Surface workbench module ok:', [n for n in dir(Surface) if not n.startswith('_')][:12])
except Exception as e: print('Surface module:', e)
print('step export test'); loft.exportStep('D:/Claude/_scratch_research/kn5_study/blind/fc_door.step'); print('ok')
