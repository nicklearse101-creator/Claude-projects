import FreeCAD as App, Part, math, importlib
ok = {}


def tryit(name, fn):
    try:
        ok[name] = fn()
    except Exception as e:
        ok[name] = "FAILED: %s" % e


V = App.Vector
pts = [[V(i * 0.1, j * 0.1, 0.02 * math.sin(i) * math.cos(j)) for j in range(8)] for i in range(10)]


def approx():
    s = Part.BSplineSurface(); s.approximate(Points=pts, DegMin=3, DegMax=6, Continuity=2, Tolerance=1e-3)
    return "%d x %d poles" % (s.NbUPoles, s.NbVPoles)


def interp():
    s = Part.BSplineSurface(); s.interpolate(pts); return "%d x %d poles" % (s.NbUPoles, s.NbVPoles)


tryit("BSplineSurface.approximate (points -> smooth surface)", approx)
tryit("BSplineSurface.interpolate", interp)


def bc(a, b, c):
    k = Part.BSplineCurve(); k.interpolate([a, b, c]); return k.toShape()


E = [bc(V(0, 0, 0), V(.5, 0, .05), V(1, 0, 0)), bc(V(1, 0, 0), V(1, .5, .05), V(1, 1, 0)),
     bc(V(1, 1, 0), V(.5, 1, .05), V(0, 1, 0)), bc(V(0, 1, 0), V(0, .5, .05), V(0, 0, 0))]
W = Part.Wire(E)
G = {}


def filled():
    G["f"] = Part.makeFilledFace(W.Edges); return "area %.3f" % G["f"].Area


tryit("makeFilledFace (curve network -> patch)", filled)


def coons():
    import Part as P
    s = P.BSplineSurface()
    f = Part.Face(Part.makeRuledSurface(E[0], E[2]))
    return "ruled ok" if f.isValid() else "invalid"


tryit("makeRuledSurface", coons)
doc = App.newDocument("p")


def surfwb(t):
    def f():
        import Surface  # noqa
        doc.addObject(t, t.split(":")[-1]); return "ok"
    return f


for t in ("Surface::Filling", "Surface::GeomFillSurface", "Surface::Sections", "Surface::Extend", "Surface::Cut"):
    tryit(t, surfwb(t))


def split():
    f = G.get("f") or Part.Face(W)
    line = Part.LineSegment(V(.3, -.1, .2), V(.3, 1.1, .2)).toShape()
    proj = f.makeParallelProjection(line, V(0, 0, -1))
    parts = f.generalFuse([proj])[0]
    G["f"] = f
    return "%d faces after splitting by the projected shut line" % len(parts.Faces)


tryit("project a shut line onto a face and split it", split)


def thick():
    t = G["f"].makeOffsetShape(0.0012, 1e-5, fill=True); G["t"] = t; return "solid valid %s" % t.isValid()


tryit("thicken panel (offset fill)", thick)
tryit("fillet panel edges (rolled edge)", lambda: "valid %s" % G["t"].makeFillet(0.0008, G["t"].Edges[:2]).isValid())
tryit("distance surface <-> point (checks)", lambda: round(G["f"].distToShape(Part.Vertex(V(.5, .5, .3)))[0], 4))


def mesh():
    import MeshPart
    m = MeshPart.meshFromShape(Shape=G["f"], LinearDeflection=0.0005, AngularDeflection=0.1); return m.CountFacets


tryit("tessellate to mesh (MeshPart)", mesh)
for mod in ("ReverseEngineering", "Inspection", "TechDraw", "CurvesWB", "freecad.Curves"):
    tryit("module " + mod, lambda mod=mod: (importlib.import_module(mod), "yes")[1])
for k, v in ok.items():
    print("%-55s %s" % (k, v))
