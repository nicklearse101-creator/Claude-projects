# Narrow strip surfacing between panels: FreeCAD Part / OCCT implementation recipes

Scope: building a narrow ruled or lofted strip between two 3D B-spline curves, and trimming the two wide neighbouring B-spline panels on those same curves, so that all faces share exact edges (watertight, sewable). Covers FreeCAD Python (Part module), OCCT/pythonocc, and CurvesWB.

Source note: many findings come from primary sources on Nik's PC. These are the docstrings compiled into FreeCAD's `Part.pyd` (FreeCAD install at `D:\FreeCAD`, user dir `v1-1`, so FreeCAD 1.1) and the installed CurvesWB source (`%APPDATA%\FreeCAD\v1-1\Mod\CurvesWB\freecad\Curves\*.py`). Links for those point to the public GitHub copies of the same files. The OCCT behaviour comes from the OCCT V7_8_0 source on GitHub (BRepFill.cxx, GeomFill_Generator.cxx, GeomFill_Profiler.cxx) and the OCCT reference manual.

## Q1. Strip construction: makeRuledSurface vs makeLoft / BRepFill, orientation, parameter pairing, curve and surface approximation options, GeomFill classes

### Takeaway
`Part.makeRuledSurface(e1, e2[, orientation])` is a thin wrapper around `BRepFill::Face` (edges) or `BRepFill::Shell` (wires). `BRepFill::Face` reuses the input edges and vertices as-is and gives them exact straight-line pcurves on the new face. That makes it the natural strip builder for watertight work: whatever edge object you pass in becomes a shared edge. The rulings pair points by normalised parameter (a linear remap of the knots onto one common range), never by arc length. So twist is decided entirely by how the two input curves are parametrised.

### Cited Findings
**makeRuledSurface / makeLoft signatures (FreeCAD 1.1 docstrings)**
- `makeRuledSurface(Edge|Wire, Edge|Wire)`: "Create a ruled surface out of two edges or wires. If wires are used then these must have the same number of edges." — [FreeCAD Part.pyd docstring (local D:\FreeCAD\lib\Part.pyd)](file:///D:/FreeCAD/lib/Part.pyd)
- `makeLoft(list of wires,[solid=False,ruled=False,closed=False,maxDegree=5])`. `makeShellFromWires(Wires)` also requires "the same number of edges". — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- CurvesWB calls the keyword form `Part.makeRuledSurface(path=sh1, profile=sh2, orientation=1)`, so a third `orientation` argument exists (0 = automatic, 1 = forward, 2 = reversed). — [CurvesWB Sketch_On_Surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/Sketch_On_Surface.py); [CurvesWB _utils.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/_utils.py)

**What makeRuledSurface does internally (FreeCAD source)**
- `TopoShape::makeElementRuledSurface` needs exactly 2 shapes. It calls `BRepFill::Face(...)` for edges and `BRepFill::Shell(...)` for wires, and never calls GeomFill directly. If one input is a wire and the other an edge, the edges are converted with `makeElementWires()`. — [FreeCAD TopoShapeExpansion.cpp](https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Mod/Part/App/TopoShapeExpansion.cpp)
- Orientation 0 (automatic) samples each curve at `0.9*First + 0.1*Last` and at the mirrored parameter, and swaps the points if an edge is `TopAbs_REVERSED`. It then forms `n1 = v1 x v2` and `n2 = v3 x v4`, and reverses S2 `if (n1.Dot(n2) < 0)`, because the face would otherwise be twisted. Orientation 2 always reverses S2. Orientation 1 does nothing. — [FreeCAD TopoShapeExpansion.cpp](https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Mod/Part/App/TopoShapeExpansion.cpp)
- The Part::RuledSurface feature's Orientation enum is `"Automatic", "Forward", "Reversed"` and defaults to Automatic. Its `execute()` does no reparametrisation. — [FreeCAD PartFeatures.cpp](https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Mod/Part/App/PartFeatures.cpp)
- CurvesWB's own `ruled_surface(e1,e2)` in ribbon.py repeats the same cross-product orientation test in Python, with a comment pointing to `PartFeatures.cpp#171`. — [CurvesWB ribbon.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/ribbon.py)

**BRepFill::Face internals (OCCT 7.8.0 source): the key to shared edges**
- It reads each edge's curve with `BRep_Tool::Curve(Edge,L,f,l)` and trims it with `Geom_TrimmedCurve` if the edge range is shorter than the curve. A REVERSED edge has its curve reversed and its vertices swapped. — [OCCT BRepFill.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/BRepFill/BRepFill.cxx)
- The surface comes from `GeomFill_Generator` (`AddCurve(C1); AddCurve(C2); Perform(Precision::PConfusion())`). — [OCCT BRepFill.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/BRepFill/BRepFill.cxx)
- **Edge1 and Edge2 are the original input edges, reused in the wire.** The input vertices are reused too. Only the two cross edges (Edge3/Edge4, the `UIso` curves at the ends, or a degenerate edge if the ends coincide) are new. — [OCCT BRepFill.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/BRepFill/BRepFill.cxx)
- Pcurves are exact iso-lines: `B.UpdateEdge(Edge1, new Geom2d_Line(gp_Pnt2d(0,f2), gp_Dir2d(±1,0)), Face, T)`, and the same at `(0,l2)` for Edge2. Because the edges are the input edges, this step adds a pcurve for the new face onto the caller's edge. All edges are then set to SameParameter/SameRange False, `BRepLib::SameParameter(Face)` is called, and the tolerance is `Precision::Confusion()` (1e-7). — [OCCT BRepFill.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/BRepFill/BRepFill.cxx)
- `BRepFill::Shell(Wire1, Wire2)` computes a ruled surface between two wires, which "must have the same number of edges". — [OCCT BRepFill reference](https://occt3d.com/dev/doc/refman/html/class_b_rep_fill.html)

**Parameter pairing: GeomFill_Generator / GeomFill_Profiler**
- `GeomFill_Profiler::Perform(PTol)`: each curve becomes a BSpline in `AddCurve` (`GeomConvert::CurveToBSplineCurve`, or `GeomConvert_ApproxCurve` for trimmed conics). The widest parameter range becomes the target `[UFirst,ULast]`. Each curve's knots are remapped linearly onto it with `BSplCLib::Reparametrize(UFirst,ULast,Knots)`. Degrees are raised to the maximum (`C->IncreaseDegree(myDegree)`). Knots are unified by `InsertKnots(Ki, Mi, PTol, False)` both ways. — [OCCT GeomFill_Profiler.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/GeomFill/GeomFill_Profiler.cxx)
- Fallback `UnifyBySettingMiddleKnots`: if the knot counts still differ, interior knots are averaged by index (`aMidKnot /= theCurves.Length()`). That changes the parametrisation, but not by arc length. — [OCCT GeomFill_Profiler.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/GeomFill/GeomFill_Profiler.cxx)
- `GeomFill_Generator::Perform` copies each section's poles into one column of the grid, with V degree 1 and V knots = section index (`VKnots(j) = j-1`, end multiplicity 2). So 2 curves give an exact bilinear-in-V ruled B-spline surface. — [OCCT GeomFill_Generator.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/GeomFill/GeomFill_Generator.cxx)

**Curve / surface approximation options (FreeCAD 1.1 docstrings)**
- `BSplineCurve.approximate(Points=..., DegMin=3, DegMax=8, Tolerance=1e-3, Continuity='C2', ...)`:
  - Continuity is one of `'C0','G1','C1','G2','C2','C3','CN'`.
  - `LengthWeight / CurvatureWeight / TorsionWeight` switch to variational smoothing. With smoothing, Continuity must be C0, C1 (DegMax >= 3) or C2 (DegMax >= 5).
  - `Parameters=` gives explicit parameters, and is only used when the weights are null.
  - `ParamType = 'Uniform' | 'Centripetal' | 'ChordLength'` is only used when neither weights nor Parameters are given.
  - "Continuity of the spline defaults to C2. However, it may not be applied if it conflicts with other parameters (especially DegMax)." — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- `BSplineCurve.interpolate(Points=..., PeriodicFlag=False, Tolerance=1e-6, Parameters=..., InitialTangent/FinalTangent, Tangents + TangentFlags)`. It defaults to chord-length parametrisation, and continuity drops to C1 when tangents are given or the curve is periodic. — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- `BSplineSurface.approximate(Points=2D array, DegMin, DegMax, Continuity=0|1|2, Tolerance, X0,dX,Y0,dY, ParamType, LengthWeight, CurvatureWeight, TorsionWeight)`. With smoothing, C1 needs DegMax >= 3 and C2 needs DegMax >= 5. `BSplineSurface.interpolate(points)` always gives degree 3, C2. — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- Other curve tools:
  - `Wire.approximate([Tol2d, Tol3d=1e-4, MaxSegments=10, MaxDegree=3]) -> BSpline`.
  - `Curve.approximateBSpline(Tolerance, MaxSegments, MaxDegree, [Order='C2'])`.
  - `Curve.toNurbs((first,last))`.
  - `BSplineCurve.makeC1Continuous(tol=1e-6, ang_tol=1e-7)` reduces knot multiplicities "keeping the geometry". — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)

**GeomFill_BSplineCurves (2/3/4 boundary fill)**
- Constructors take 2, 3 or 4 BSpline curves plus a style: `GeomFill_Stretch` ("flattest patch"), `GeomFill_Coons`, or `GeomFill_Curved` ("most rounded patch").
- The two-curve form raises `Standard_ConstructionError` "if the curves are not contiguous". So it is a boundary-patch filler, not a ruled surface between two parallel rails.
- `Surface()` returns a `Geom_BSplineSurface`. The docs warn "Some problems may show up with rational curves." — [OCCT GeomFill_BSplineCurves reference](https://occt3d.com/dev/doc/refman/html/class_geom_fill___b_spline_curves.html)
- FreeCAD also exposes `makeFilledSurface(list of curves, tolerance)` and `makeFilledFace(list of edges)`, plus a `BRepOffsetAPI_MakeFilling` binding (`add`, `build`, `G0Error/G1Error/G2Error`, `loadInitSurface`, `setApproxParam`, `setConstrParam`, `setResolParam`), and `BRepOffsetAPI_MakePipeShell` (`setAuxiliarySpine`, `setSpineSupport`, `setTrihedronMode`, `setTolerance`, `setMaxDegree`...). — [FreeCAD Part.pyd docstrings/symbols](file:///D:/FreeCAD/lib/Part.pyd)

### Inferences
- For a strip whose two long edges must be exactly shared, prefer `Part.makeRuledSurface(edgeA, edgeB)` (BRepFill::Face) over `makeLoft`/`makeFilledFace`. It is the only route confirmed here to reuse the caller's edge TShapes, and it gives exact iso-line pcurves on the strip. A loft or plate builds new boundary geometry.
- The strip is linear across its width (V degree 1). If the strip must be curved across its width (e.g. a crowned shut-line return), a ruled surface is the wrong surface type. Then build the strip as a 3- or 4-row `BSplineSurface.buildFromPolesMultsKnots` whose outer pole rows are exactly the boundary curves' poles. The edges are then iso-curves of the strip and can still be shared (see Q3).
- `makeRuledSurface`'s automatic orientation only checks the curves at 10 % / 90 %. For a strip between two nearly parallel rails it is reliable, but pass `orientation=1` once you have oriented the curves yourself, so a degenerate case does not silently flip.

### Gaps
- I did not read the full `BRepFill::Shell` source, so whether wire-to-wire shells also reuse the input edges is not confirmed (likely, by analogy).
- `GeomFill_ConstrainedFilling` was not researched in this pass.

## Q2. Getting the trim edges onto the neighbour panels: pcurves, projection, Part.Face(surface, wire), cutting

### Takeaway
The robust FreeCAD pattern, used throughout CurvesWB, is to put the boundary on the neighbour surface as a 2D curve: get or build a `Geom2d` curve in the panel's (u,v) space, then call `c2d.toShape(panelSurface, first, last)`. That gives an edge that lies exactly on the panel, with its pcurve, and a 3D curve OCCT computes from it. Then build the trimmed panel with `Part.Face(panelSurface, wire)` and `validate()`. Boolean trims (`common`/`cut` with a prism, `BOPTools.SplitAPI.slice`) work, but they create new intersection edges that are not your boundary curve.

### Cited Findings
- `Face.project(shapeList) -> Shape` projects shapes onto a face. `Shape.makeParallelProjection(shape, dir)` and `makePerspectiveProjection(shape, pnt)` project an edge or wire onto a shape. — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- `Face.curveOnSurface(Edge) -> (curve2d, min, max) or None` returns the pcurve of an edge on the face. `Edge.curveOnSurface(idx)` returns a 5-tuple (curve2d, surface, placement, first, last). — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- CurvesWB Sketch-on-Surface recipe, verbatim pattern:
  1. Project an edge onto a helper quad face with `proj = quad.project([oe])`.
  2. For each projected edge, `c2d, fp, lp = quad.curveOnSurface(e)`.
  3. Build `ne = c2d.toShape(face.Surface, fp, lp)` (the 2D curve rebuilt on the target surface).
  4. If the vertex tolerance is below the edge tolerance, `ne.fixTolerance(et, Part.Vertex)`.
  5. Make wires with `Part.sortEdges`, then call `w.fixWire(face, 1e-7)` before building faces. — [CurvesWB Sketch_On_Surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/Sketch_On_Surface.py)
- CurvesWB `validated_face(w, surf)`: build `f = Part.Face(surf, w)`, then `f.validate()`. On `Part.OCCError`, double the wire tolerance with `w.fixTolerance(tol)` up to `maxtol = 1e-4` and retry, otherwise return a null face. Holes are added with `f.cutHoles(wires)` then `f.validate()`. — [CurvesWB Sketch_On_Surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/Sketch_On_Surface.py)
- CurvesWB curveOnSurface / blend_curve / ShapeMapper build edges the same way: `self.curve2D.toShape(self.face, first, last)` and `line.toShape(surface, fp, lp)` for iso lines. — [CurvesWB curveOnSurface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/curveOnSurface.py); [CurvesWB ShapeMapper.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/ShapeMapper.py)
- CurvesWB Trim Face tool: wires are translated and extruded along a direction into cutting tools (`w.extrude(-v*d*2)`), then `BOPTools.SplitAPI.slice(face, cuttool, "Split", 1e-6)` runs. The piece kept is the one where `f.isPartOfDomain(u, v)` holds for the picked (u,v). — [CurvesWB TrimFace.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/TrimFace.py)
- `Part.makeSplitShape(shape, [(edge|wire|compound, face), ...], checkInterior=True)`: "The face must be part of the specified shape and the edge, wire or compound must lie on the face." It returns faces left of the wires, and the remainder. — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- FreeCAD binds `ShapeFix_Edge` with:
  - `fixAddPCurve(edge, face, isSeam, prec)` or `fixAddPCurve(edge, surface, placement, isSeam, prec)`;
  - `fixSameParameter(edge, tolerance)` or `fixSameParameter(edge, face, tolerance)`;
  - `fixAddCurve3d`, `fixVertexTolerance`, `fixReversed2d`, `fixRemovePCurve`. — [FreeCAD Part.pyd docstrings/symbols](file:///D:/FreeCAD/lib/Part.pyd)
- `BRepLib::BuildCurves3d(S, Tolerance, Continuity=GeomAbs_C1, MaxDegree=14, MaxSegment=0)` builds missing 3D curves from pcurves. `BRepLib::SameParameter(S, Tolerance=1e-5, forced=false)` recomputes pcurves to match the 3D curve's parametrisation. `BRepLib::UpdateTolerances(S, verifyFaceTolerance=false)`. — [OCCT BRepLib reference](https://occt3d.com/dev/doc/refman/html/class_b_rep_lib.html)

### Inferences
- **Recommended order (exact by construction):**
  1. Define each boundary in the (u,v) space of the panel it belongs to, as a `Geom2d` B-spline: `Part.Geom2d.BSplineCurve2d`, interpolated through projected (u,v) points from `surface.parameter(pt)` or `projectPoint(...,"LowerDistanceParameters")`.
  2. Build `eA = c2dA.toShape(panelA.Surface, a, b)`, which carries an exact pcurve on A.
  3. Build `eB` on panel B the same way.
  4. Run `strip = Part.makeRuledSurface(eA, eB, 1)`. BRepFill::Face reuses eA and eB and adds iso-line pcurves on the strip.
  5. Make panel A with `Part.Face(panelA.Surface, Part.Wire([eA, ...other edges of A]))`, and the same for B.
  6. Combine with `Part.Shell([faceA, strip, faceB])`.

  Each long edge is then one TShape, with an exact pcurve on both faces. There is nothing to sew and the edge tolerance stays near 1e-7.
- If the boundary is designed as a 3D curve rather than in (u,v), its 3D curve will not lie exactly on the panel. Project it with `panel.project([edge])` or `ShapeFix_Edge.fixAddPCurve(edge, panelFace, False, tol)`, then `fixSameParameter`. The edge tolerance grows to roughly the curve-to-surface deviation. Keep the deviation well under the sewing tolerance, or snap the curve to the surface first by projection.
- Boolean trimming (`face.common(prism)`, `cut`, `slice`) recomputes the edge as a surface/surface intersection. The strip edge and the panel edge are then two different approximations, and must be sewn. Use it only as a fallback.

### Gaps
- I could not confirm from source whether FreeCAD's `Part.Face(surface, wire)` constructor automatically computes missing pcurves (BRepBuilderAPI_MakeFace + ShapeFix) or relies on existing ones. CurvesWB's tolerance-doubling `validate()` loop suggests it sometimes needs help.
- Whether `Part.makeSplitShape` (BRepFeat_SplitShape) keeps the exact given edge in the split result, rather than a copy, was not verified.
- pythonocc-specific examples (GeomProjLib.Curve2d, BRepAlgo_NormalProjection, ShapeConstruct_ProjectCurveOnSurface, `BRepBuilderAPI_MakeEdge(Geom2d_Curve, Geom_Surface)`) were not fetched this session. The class names are standard OCCT, but their argument details are unverified here.

## Q3. Guaranteeing shared edges, sewing, and checking gaps

### Takeaway
The best watertightness comes from topological sharing (the same edge object in both faces' wires), not from sewing. Sewing (`BRepBuilderAPI_Sewing`, FreeCAD `sewShape()`) is the repair path when faces were built separately: it merges coincident edges within a tolerance, and the resulting tolerance can be large if the input faces already carry large tolerances. Check with `check(True)`, `isValid()`, `Shell.getFreeEdges()`, `getBadEdges()`, `getTolerance(1, Part.Edge)` and `distToShape`.

### Cited Findings
- `BRepBuilderAPI_Sewing(tolerance=1.0e-06, option1=true (sew), option2=true (analyse degenerated), option3=true (cut free edges), option4=false (non-manifold))`:
  - `Add`, `Perform`, `SewedShape()` (face/shell/solid/compound, null if nothing was built);
  - `NbFreeEdges/FreeEdge(i)`, `NbMultipleEdges` ("Sewing will not be done in case of multiple edges"), `NbDegeneratedShapes`;
  - `SetMinTolerance/SetMaxTolerance`, `SetFaceMode`, `SetFloatingEdgesMode`, `SetLocalTolerancesMode` (working tolerance = base + local edge tolerances), `SetNonManifoldMode`. — [OCCT BRepBuilderAPI_Sewing reference](https://occt3d.com/dev/doc/refman/html/class_b_rep_builder_a_p_i___sewing.html)
- FreeCAD: `Shape.sewShape()`, "Sew the shape if there is a gap", takes no tolerance argument in the docstring. CurvesWB's pattern is `shell = Part.Shell(faces); shell.sewShape()`, optionally followed by `solid.fixTolerance(1e-5)`. — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd); [CurvesWB Sketch_On_Surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/Sketch_On_Surface.py); [CurvesWB HelicalSweepFP.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/HelicalSweepFP.py)
- In FreeCAD's own code, `makeElementOffset` builds `BRepBuilderAPI_Sewing sewTool;` with no explicit tolerance ("Sew has it's own default tolerance"). — [FreeCAD TopoShapeExpansion.cpp](https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Mod/Part/App/TopoShapeExpansion.cpp)
- An OCCT forum report of a 20 mm tolerance after sewing two faces was answered: the high tolerance was not caused by sewing but came from the input faces. — [OCCT forum via search summary: "sewing two faces results very high tolerance"](https://dev.opencascade.org/content/sewing-two-faces-results-very-high-tolerance) (only the search snippet was seen; the page itself was not fetched)
- Checking tools in FreeCAD 1.1:
  - `check([runBopCheck=False])` is "a more detailed check as done in isValid()".
  - `getTolerance(mode, ShapeType)`: mode 0 = average, >0 = max, <0 = min.
  - `overTolerance(value, ShapeType)` and `inTolerance(min, max, ShapeType)`.
  - `fixTolerance(value, ShapeType)` and `limitTolerance(tmin, tmax, ShapeType)`.
  - `distToShape(shape, tol=1e-7) -> (dist, vectors, infos)`, where infos give the topo type, index and (u,v) or u for each solution.
  - Bindings: `Shell.getFreeEdges()`, `getBadEdges()`, `ShapeFix_Shell` (`perform`, `fixFaceOrientation`, `numberOfShells`, `errorFaces`, `setNonManifoldFlag`), `ShapeFix_Shape`, `ShapeFix_Wire` (`fixGaps3d`, `fixGaps2d`, `fixConnected`, `fixSmall`, `fixSeam`...), `ShapeFix_FixSmallFace` (`fixStripFace`, `fixSpotFace`), `ShapeFix_FreeBounds`, `ShapeFix_ShapeTolerance`. — [FreeCAD Part.pyd docstrings/symbols](file:///D:/FreeCAD/lib/Part.pyd)
- `removeSplitter()` "Removes redundant edges from the B-REP model". — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)

### Inferences
- Suggested acceptance test for one panel/strip/panel triple:
  - `sh = Part.Shell([fA, strip, fB])`.
  - `len(sh.getFreeEdges().Edges)` should equal only the outer boundary edges.
  - `sh.check(True)` should raise nothing.
  - `sh.getTolerance(1, Part.Edge)` should be close to 1e-7 when edges are truly shared, and well under 0.01 mm when sewn.
  - Sample points along each shared edge and check `fA.distToShape(Part.Vertex(p))[0]` and the same on the strip.
  - If faces were built separately, compare `len(sh.Edges)` before and after `sewShape()`. Sewing should reduce the count by one per shared seam.
- If you must sew, pass an explicit tolerance through the OCCT API (pythonocc `BRepBuilderAPI_Sewing(tol)`), set to about 2-5x the worst measured curve-to-surface deviation. FreeCAD's `sewShape()` exposes no tolerance in its docstring.
- `ShapeFix_FixSmallFace.fixStripFace` exists precisely because thin strip faces are a known failure case. A very narrow strip (width close to the tolerance) can be flagged or removed by healing. Keep strip width at least 100x the edge tolerance.

### Gaps
- The FreeCAD 1.1 docstring for `sewShape()` shows no arguments. Whether the binding takes an optional tolerance argument in 1.1 was not verified.
- No quantitative data was found on how much tolerance grows after `common()`/`cut()` on B-spline faces. Only anecdotal forum reports.

## Q4. Rulings twist: reparametrisation, compatible knots, building the ruled BSplineSurface by hand

### Takeaway
Because OCCT pairs the two rails by linearly normalised parameter, a ruled strip twists wherever the two curves' parameter speeds differ (e.g. one interpolated by chord length over a different point distribution). Two fixes exist:
- Make the two rails share a parametrisation **before** making the edges (same point count, same parameters, same knots). This keeps edges exact.
- Use CurvesWB's HQ ruled surface reparametrisation. This **approximates new rail curves**, so the strip edges are no longer your original curves.

### Cited Findings
- `insertKnots(list_of_floats, list_of_ints, tol=0.0, bool_add=True)`. If `bool_add` is False an existing knot's multiplicity is raised to `mult`; otherwise it is increased by `mult`. Knots outside the range are ignored and multiplicity is capped at the degree. — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- `increaseDegree(Degree)` changes the poles, weights and multiplicities but not the knots table. `scaleKnotsToBounds(u0=0, u1=1)` rescales knots without changing the shape (curve and surface versions). — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- `buildFromPolesMultsKnots(poles, [mults, knots, periodic, degree, weights, CheckRational])` exists for curves, 2D curves and surfaces. — [FreeCAD Part.pyd docstring](file:///D:/FreeCAD/lib/Part.pyd)
- CurvesWB curve-matching recipe (curves_to_surface.py):
  - `match_degrees()` raises every curve to the max degree with `c.increaseDegree(max_degree)`.
  - `normalize_knots()` calls `c.scaleKnotsToBounds()`.
  - `match_knots()` runs `curves[0].insertKnots(c.getKnots(), c.getMultiplicities(), tol2d, False)` for each other curve, then inserts curve 0's knots back into each.
  - `U_linear_surface()` builds an explicit ruled surface: `bs.buildFromPolesMultsKnots(poles=[row0,rowN], [2,2], vmults, [0,1], vknots, False, vperiodic, 1, VDegree, weights)`. — [CurvesWB curves_to_surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/curves_to_surface.py)
- CurvesWB `orient_curves(c1,c2)` compares the two "diagonal" line pairs with `distToShape` and reverses c2 if the straight pairing is closer. `shift_origin(c1,c2,num)` (closed curves only) picks the offset that minimises total ruling length, then `insertKnot` + `setOrigin`. `ruled_surface(e1,e2, normalize, autotwist)` combines these, then calls `Part.makeRuledSurface`. — [CurvesWB curves_to_surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/curves_to_surface.py)
- CurvesWB HQ Ruled Surface ("The 2 edges (or wires) are reparametrized before surface creation"):
  - `rp.reparametrize(c1, c2, num=Samples(20), smooth_start=0.2, smooth_end=0.2, method=3)`, then `Part.makeRuledSurface(nc1.toShape(), nc2.toShape())`.
  - The methods: 1 = project points of e1 onto e2 (`distToShape`), 2 = the reverse, 3 = whichever gives more ascending pairs, 4 = normal planes of the chord.
  - The paired parameters are filtered and stretched at the ends, then each curve is rebuilt by `BSplineAlgorithms.reparametrizeBSplineContinuouslyApprox(curve, old_params, new_params, max_cp)` with 10-80 control points. — [CurvesWB HQRuledSurfaceFP.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/HQRuledSurfaceFP.py); [CurvesWB reparametrize.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/reparametrize.py)
- `normalized_bspline()` in reparametrize.py converts a wire with `e1.approximate(1e-15, 1e-7, 25, 999)` and an edge with `Curve.toBSpline(First, Last)`, then normalises the knots. — [CurvesWB reparametrize.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/reparametrize.py)

### Inferences
- **Exact-edge workflow for low twist:** generate both rails from one common parameter t. For example:
  - sample the design centre-line at N stations;
  - at each station take the two boundary points (A side and B side) and their (u,v) on the respective panels;
  - interpolate both 2D pcurves with `interpolate(Points=uvA, Parameters=ts)` and `interpolate(Points=uvB, Parameters=ts)`, using the **same** `ts` list.

  Their 3D images then correspond station by station, so the rulings follow the stations. No later reparametrisation is needed, and the edges stay exact. (Note: a pcurve's parameter is carried to the 3D curve by `toShape`/`BuildCurves3d`, which should preserve the t-correspondence closely. Confirm with a ruling-direction check.)
- **If the rails already exist:** HQ-reparametrise them, then use the **new** curves `nc1`, `nc2` as the boundary for everything. Project them onto the panels (or snap them, see Q2) and trim the panels on those. Never trim on the old curves while the strip uses the new ones.
- A simple twist metric: sample t, form the ruling `S(t,1)-S(t,0)`, and measure its angle to the design cross-section plane (or its dot product with the rail tangent). Rulings should be roughly perpendicular to both rails.

### Gaps
- `BSplineCurve.reparametrize` exists for surfaces (descriptor seen in Part.pyd), but its docstring for curves was not extracted. I found no FreeCAD API for composing a curve with a 1D reparametrisation function while keeping the geometry exact. `Geom2dAdaptor`-based reparametrisation was not found in FreeCAD Python.

## Q5. CurvesWB tools relevant here and their Python entry points

### Takeaway
CurvesWB already contains every building block: ruled-surface orientation and anti-twist, knot matching, sketch-on-surface pcurve mapping, face trimming, Gordon surfaces and sweeps. All are plain Python modules under `freecad.Curves`, importable without the GUI command where they do not depend on FreeCADGui.

### Cited Findings
- The modules installed on Nik's PC include:
  - `HQRuledSurfaceFP`, `reparametrize`, `curves_to_surface` (`ruled_surface`, `orient_curves`, `shift_origin`, `match_knots`, `U_linear_surface`, plus a curve-matching surface class with `match_degrees/normalize_knots/match_knots/match_curves/interpolate`);
  - `Sketch_On_Surface` (`validated_face`, `BoundarySorter`, `map_shape`);
  - `TrimFace`, `curveOnSurface` (`curveOnSurface(edge, face)` with `normalFace`, `binormalFace`, offset 2D curves);
  - `blend_curve`, `blendSurface`, `gordon` / `gordonFP`, `Sweep2Rails`, `pipeshellFP`, `splitCurves_2`, `joinSurfacesFP`, `match_wires`, `nurbs_tools`, `BSplineAlgorithms`, `BSplineApproxInterp`, `continuity_check`, `ZebraTool`, `SurfaceAnalysisFP`. — [CurvesWB repo, freecad/Curves](https://github.com/tomate44/CurvesWB/tree/master/freecad/Curves)
- Import style inside the workbench: `from freecad.Curves import reparametrize as rp` and `from freecad.Curves import _utils`. — [CurvesWB HQRuledSurfaceFP.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/HQRuledSurfaceFP.py)
- `blend_curve.py` builds its result as `shell = Part.Shell([f1, bsface, f2])`. This is the same panel/strip/panel triple topology, from a working tool. — [CurvesWB blend_curve.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/blend_curve.py)
- `Ribbon(e1, f1, e2, f2)` in ribbon.py builds a ruled surface between two edges, wraps each rail as `curveOnSurface(c, face)`, and builds a parameter map from planes normal to the mid-curve, so that cross-sections stay orthogonal. — [CurvesWB ribbon.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/ribbon.py)

### Inferences
- For headless scripts, import `freecad.Curves.reparametrize`, `curves_to_surface` and `Sketch_On_Surface.validated_face` directly. Some modules (e.g. ribbon.py's `import nurbs_tools`, HQRuledSurfaceFP importing FreeCADGui) need the GUI or path tweaks.

### Gaps
- I did not read gordon.py, blendSurface.py or splitCurves_2.py in detail. The CurvesWB wiki pages for each tool were not fetched.

## Q6. Known pitfalls

### Takeaway
The main failure modes are:
- boundary curves that do not lie on the panel surface (tolerance growth);
- boolean-generated duplicate edges that must be sewn;
- parameter mismatch between rails (twist);
- orientation flips (bow-tie strips);
- thin or sliver faces that healing tools treat as defects.

### Cited Findings
- makeRuledSurface twist from opposite curve directions is handled only by the automatic orientation's cross-product test at 10 %/90 %. — [FreeCAD TopoShapeExpansion.cpp](https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Mod/Part/App/TopoShapeExpansion.cpp)
- Rulings pair by normalised parameter. When knot counts disagree, the fallback averages interior knots by index, which can move rulings unexpectedly. — [OCCT GeomFill_Profiler.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/GeomFill/GeomFill_Profiler.cxx)
- If the ends of a rail pair coincide, BRepFill::Face makes a degenerated cross edge (`B.Degenerated(Edge3, True)`). That gives a triangular strip end with a degenerate edge, a known source of meshing and sewing trouble. — [OCCT BRepFill.cxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_0/src/BRepFill/BRepFill.cxx)
- Face validation sometimes needs the wire tolerance raised (CurvesWB doubles it up to 1e-4 before giving up). — [CurvesWB Sketch_On_Surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/Sketch_On_Surface.py)
- A large tolerance after sewing usually comes from the input faces, not from sewing itself. — [OCCT forum (search snippet)](https://dev.opencascade.org/content/sewing-two-faces-results-very-high-tolerance)
- Sewing skips edges shared by more than two faces. — [OCCT BRepBuilderAPI_Sewing reference](https://occt3d.com/dev/doc/refman/html/class_b_rep_builder_a_p_i___sewing.html)
- Closed (periodic) rails need the seam origin aligned (CurvesWB `shift_origin`). Otherwise the strip twists a full turn. — [CurvesWB curves_to_surface.py](https://github.com/tomate44/CurvesWB/blob/master/freecad/Curves/curves_to_surface.py)

### Inferences
- In practice, avoid `common()`/`cut()` for the panel trims and build the trimmed panels directly with `Part.Face(surface, wire)` from shared edges. This removes the tolerance growth, sliver and seam-edge problems from the boolean path.
- Keep the panel surfaces slightly larger than the trimmed area (untrimmed B-spline extends past the strip edge). Then the pcurves stay strictly inside the parameter domain, and the boundary never coincides with a knot-line edge of the surface.

### Gaps
- I found no measured statistics on sliver-face frequency or tolerance growth in FreeCAD booleans on B-spline panels.
