import FreeCAD as App, Part, pkgutil, importlib
V = App.Vector
import freecad.Curves as C
mods = sorted(m.name for m in pkgutil.iter_modules(C.__path__))
print("Curves modules:", len(mods), [m for m in mods if any(k in m.lower() for k in ("gordon", "network", "blend", "sweep", "approx", "curves_to_surface", "isocurve", "comb", "zebra"))])
from freecad.Curves import gordon
# 3 profiles x 3 guides on a gently curved grid -> Gordon surface
def bs(pts):
    c = Part.BSplineCurve(); c.interpolate([V(*p) for p in pts]); return c
profiles = [bs([(0, y, 0), (0.5, y, 0.05 + 0.02 * y), (1, y, 0)]) for y in (0, 0.5, 1)]
guides = [bs([(x, 0, z), (x, 0.5, z + 0.02 * 0.5), (x, 1, z + 0.0)]) for x, z in ((0, 0), (0.5, 0.05), (1, 0))]
try:
    g = gordon.InterpolateCurveNetwork(profiles, guides, 1e-4, 1e-4)
    s = g.surface()
    print("Gordon surface OK:", s.NbUPoles, "x", s.NbVPoles, "poles; face valid:", Part.Face(s).isValid())
except Exception as e:
    print("Gordon FAILED:", e)
