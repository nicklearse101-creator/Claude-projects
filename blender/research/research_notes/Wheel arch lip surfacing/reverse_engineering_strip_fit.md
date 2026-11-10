# Reverse-engineering a surface strip along a curved boundary (wheel-arch lip / flare) with OpenCASCADE / FreeCAD Python

Scope: methods for (a) detecting a lip/fillet band along an opening edge in a mesh, (b) parameterising points by (arc length s along a rail, distance t across), (c) fitting a B-spline surface (sweep, variable-section sweep, or tensor B-spline in (s,t)), (d) G1 join to the adjacent panel, (e) trimming. Target: numpy + FreeCAD 1.1 (OCC ~7.8).

Source note: Cardiff ORCA full texts (Várady/Benkő/Martin, Kós blend-radius paper) returned HTTP 403, and the FreeCAD wiki returned a bot-block page, so those are cited from abstracts/search snippets only. OCC API facts come from the official reference pages (occt3d.com mirror of dev.opencascade.org) and from the FreeCAD `.pyi` stubs (mirror of FreeCAD's source on Hugging Face).

## Standard RE methods for fillet/blend recognition and reconstruction (rolling ball, variable radius, spine + cross-section, swept-surface fitting)

### Takeaway
The classic RE pipeline (Várady, Martin, Cox 1997; Benkő, Martin, Várady 2001) fits the primary surfaces first and adds blends afterwards. A constant-radius rolling-ball blend is then fully set by its radius plus the two primary surfaces (Kós, Martin, Várady 2000). Swept regions are reduced to 2D curve fitting of projected points, with continuity constraints added as equations. For a free-form lip whose section changes along the arch, the matching literature is "sweep-surface fitting" (Ueng and Lai 1998): fit B-spline cross-sections moved along a B-spline profile/spine by nonlinear least squares.

### Cited Findings
- Benkő, Martin, Várady (2001, CAD 33(11):839-851): reconstructs solid models of "conventional engineering objects" from multi-view point clouds. Such objects are bounded by simple analytic surfaces, swept surfaces and blends. The steps are segmentation, extrusion/revolution fitting, B-rep topology, then adding blends — [search summary of ORCA/Bib records](https://orca.cardiff.ac.uk/1811/1/REalgorithms.pdf)
- Benkő et al.: fitting a swept region "reduces to a curve fitting problem after projecting the original 3D data points", with constraint equations that enforce the required continuity — [ORCA (snippet)](https://orca.cardiff.ac.uk/1811/1/REalgorithms.pdf); constrained-fitting companion paper: [ConstrainedFitting.pdf](https://orca.cardiff.ac.uk/1812/1/ConstrainedFitting.pdf)
- Kós, Martin, Várady, "Methods to recover constant radius rolling ball blends in reverse engineering", CAGD 17(2):127-160 (2000), DOI 10.1016/S0167-8396(99)00043-6. Once the primary surfaces are known, finding the radius gives the whole blend surface. The paper compares several radius-estimation algorithms — [ORCA record](https://orca.cardiff.ac.uk/13565), [SZTAKI](https://eprints.sztaki.hu/2459/)
- Variable-radius follow-up: G. Kós, "Recovering variable radius rolling ball blends in reverse engineering", CIRP Design Seminar, Haifa 2000. Full text is not in the repository — [SZTAKI 2322](https://eprints.sztaki.hu/2322/), [SZTAKI 2648](https://eprints.sztaki.hu/2648)
- Terminology: the spine curve is the path of the rolling-ball centre. The cross-section is the profile through the centre and the two contact points — [Liu et al. TVC 2005 mesh blending](https://yushen-liu.github.io/main/pdf/LiuYS_TVC05Meshblending.pdf)
- Ueng and Lai (1998), "A sweep-surface fitting algorithm for reverse engineering", Computers in Industry 35(3):261-273. The surface is B-spline cross-sections moved along a B-spline profile curve. Fitting is nonlinear least squares with parameter optimisation. The paper reports less memory and CPU time than B-spline surface fitting and more uniform cross-sections than B-spline or lofted fits — [bohrium record](https://www.bohrium.com/paper-details/a-sweep-surface-fitting-algorithm-for-reverse-engineering/811161574281576448-2477), [acnp](https://acnpsearch.tweb-dev.unibo.it/singlejournalindex/55973115). Related: Ueng, Lai, Doong, "Sweep-surface reconstruction from three-dimensional measured data" (CAD). It adds conversion of the sweep to a composite spline surface for CAD/CAM — [zhenzhi record](https://data.zhenzhi.com/details/1/876509924)
- Mesh fillet detection, industrial method (Dassault patent application). Compute a curvature tensor field (normal cycles, quadric fitting or circle fitting). Trace curves along maximal-curvature directions and fit a circle to each. Flag a fillet when the mean circle-fit error is below a threshold, and use the radius variance as a further test. Build the fillet feature from the average radius — [Justia patent 20240135733](https://patents.justia.com/patent/20240135733), [EPO EP4345673](https://data.epo.org/publication-server/rest/v1.2/patents/EP4345673NWA1/document.html)
- Fillet radius without prior segmentation: find the optimal plane orthogonal to the fillet, intersect it with the mesh, and least-squares fit a circle to the section points (Korean paper, 2005) — [koreascience](https://koreascience.kr/article/JAKO200532217917382.pdf)
- Caveats for curvature-based blend detection. Earlier mesh blend recognition fails when the blend's neighbouring faces are not planar. On toroidal blends, curvature is constant along the profile circle but varies across the surface — [UEA accepted manuscript](https://ueaeprints.uea.ac.uk/id/eprint/73650/2/Accepted_Manuscript.pdf). The usual pipeline is per-vertex principal curvatures, region growing, then refitting each segment — [SciTePress 2019](https://www.scitepress.org/Papers/2019/73967/73967.pdf)
- Spine estimation for pipe-like surfaces: fit local cylinders by moving least squares, then approximate the spine by G1 arcs and lines — [Bauer et al.](https://ddg.math.uni-goettingen.de/pub/bauer-ParametricReconstruction.pdf)
- Scanned edges used as rails and profiles for swept surfaces (Schreve, Stellenbosch dissertation) — [search summary](https://core.ac.uk/download/37374423.pdf)
- Kinematic-surface / slippage detection handles sweeps with arbitrary central curve and profile (Miandarhoie and Khalili 2016) — [modares PDF](https://mme.modares.ac.ir/article_9174_3acb2a202ae4bea8840224e6fce16fd0.pdf?lang=en)

### Inferences
- A wheel-arch lip is not a true rolling-ball blend. It is a rolled return flange plus a flare whose section changes round the arch, so constant-radius recovery (Kós) only fits the small radius at the lip crown. Ueng-Lai sweep fitting, or a tensor B-spline in (s,t), is the better model for the whole band. Use rolling-ball / circle-fit ideas only to detect the band and to measure the crown radius per section.
- Practical detection recipe for a mesh, following the patent's circle-fit test and the orthogonal-plane section idea:
  1. Get the opening boundary loop: boundary edges, or the sharp edge at the lip's inner fold.
  2. Resample it to a smooth rail C(s), chord-length / arc-length parameterised (`Part.BSplineCurve().approximate(Points=..., ParamType='ChordLength')`).
  3. At each station s_i, cut the mesh with the plane normal to C'(s_i) (numpy triangle-plane intersection, or `Mesh.Mesh.crossSections` / `MeshPart.projectShapeOnMesh` in FreeCAD).
  4. In each 2D section, fit a line or arc to the outer (panel) part. The lip band starts where the residual against the panel fit, or the section's discrete curvature, goes above a threshold.
  5. Stack the start/end distances t0(s), t1(s) along s to get the band edges. Smooth them with a 1D spline.
- Using section planes normal to the rail is more robust on a noisy scan or photo-traced mesh than per-vertex principal curvature, because each 2D section can be fitted with plain robust 1D methods.

### Gaps
- Full texts of Kós/Martin/Várady (constant and variable radius) and Benkő 2001 could not be read (HTTP 403 or no full text), so their exact radius estimators and their recommended method are unknown here.
- No source found that deals specifically with flared or rolled wheel-arch lips in RE.

## Fitting a sweep: rail estimation, moving frame (RMF vs Frenet), cross-section fitting, surface build, G1 to a neighbour

### Takeaway
Use an arc-length-parameterised B-spline rail. Use a rotation-minimising frame (Wang et al. 2008 double reflection), not Frenet, which flips at inflections and is undefined on straight runs. Better still, take the frame normal from the adjacent panel surface (a "support" or "binormal" mode). Express each data point as (s, t, h) in that frame, fit the section h(t) per station (or a full 2D tensor spline h(s,t)), and build the surface either with OCC's MakePipeShell from several fitted section wires, or directly as a least-squares tensor B-spline. Least-squares in numpy gives the best control over G1, because the first two pole rows can be pinned.

### Cited Findings
- Rotation-minimising frames: the double reflection method (Wang, Jüttler, Zheng, Liu, ACM TOG 27(1), 2008) builds each frame from the previous one with two reflections. Its global error is fourth order, against second order for the projection (Klok) and rotation (Bloomenthal) methods, at similar cost. It is simpler and faster than RK4 on the RMF ODE, and it is defined for any C1 regular curve — [HKU PDF](https://i.cs.hku.hk/GraphicsGroup/publications/pdf/Computation%20of%20rotation%20minimizing%20frames.pdf), [HKU hub](https://hub.hku.hk/handle/10722/152386)
- OCC `BRepOffsetAPI_MakePipeShell` trihedron modes: `SetMode(IsFrenet)` (Frenet, or corrected Frenet if false), `SetDiscreteMode()`, `SetMode(gp_Ax2)` (fixed trihedron, all sections parallel), `SetMode(gp_Dir BiNormal)` (constant angle to a binormal), `SetMode(SpineSupport)` (binormal from a support surface's normals; each spine edge must have a representation on a face of the support), and `SetMode(AuxiliarySpine, CurvilinearEquivalence, KeepContact)` with BRepFill_NoContact / Contact / ContactOnBorder — [OCC refman](https://occt3d.com/dev/doc/refman/html/class_b_rep_offset_a_p_i___make_pipe_shell.html)
- Further MakePipeShell calls: `Add(Profile, WithContact, WithCorrection)` adds a section; the first and last may be vertices; WithCorrection rotates the section orthogonal to the spine tangent. `SetLaw(Profile, Law_Function, ...)` gives a homothetic (scaling) law. `SetTransitionMode` takes Transformed, RightCorner or RoundCorner. Also `SetMaxDegree` / `SetMaxSegments` (V direction) and `SetForceApproxC1` (tries a C1 approximation when the sweep is C0). Warnings: combining Add and SetLaw is "not recommended". The auxiliary spine mode is "incompatible with hometetic laws" [sic]. Auxiliary spine with keep-contact gives "only CO surface". RoundCorner is only reliable with WithCorrection=True — [OCC refman](https://occt3d.com/dev/doc/refman/html/class_b_rep_offset_a_p_i___make_pipe_shell.html)
- FreeCAD Python wrapper `Part.BRepOffsetAPI_MakePipeShell(spine_wire)` methods (from the `.pyi` stub):
  - `setFrenetMode(bool)`, `setTrihedronMode(point, direction)`, `setBiNormalMode(direction)`, `setSpineSupport(shape)`
  - `setAuxiliarySpine(wire, CurvilinearEquivalence: bool, TypeOfContact: int)` with 0 = none, 1 = contact, 2 = contact on border
  - `add(Profile, WithContact=False, WithCorrection=False)` and `add(Profile, Location, ...)`, `remove`
  - `isReady`, `getStatus`, `build`, `shape`, `makeSolid`, `firstShape`, `lastShape`, `generated(S)`, `simulate(nbsec)`
  - `setTolerance(tol3d, boundTol, tolAngular)`, `setTransitionMode(0|1|2)`, `setMaxDegree`, `setMaxSegments`, `setForceApproxC1`
  - There is no `setLaw` in the Python wrapper.
  — [FreeCAD .pyi (HF mirror)](https://huggingface.co/AbdulElahGwaith/FreeCAD/blob/main/src/Mod/Part/App/BRepOffsetAPI_MakePipeShell.pyi)
- A FreeCAD tracker issue, "BRepOffsetAPI_MakePipeShellPy.setAuxiliarySpine problems" (#2961), reports problems with the auxiliary-spine wrapper — [FreeCAD tracker 2961](https://tracker.freecad.org/view.php?id=2961). A 2009 OCC forum user got a sweep working with SetMode(auxiliary spine) and then Add(profile) — [OCC forum](https://dev.opencascade.org/content/making-pipe-geomline)
- `GeomFill_Pipe` has a constructor `(Path, Curve1, Curve2, Radius)`: a constant-radius pipe with two guide lines, i.e. the circular rolling-ball section between two contact curves. It also has modes for a circular section of constant radius, a constant section, and a section evolving between two curves. In the OCC 8.0 reference the two-guide constructor appears on `GeomFill_SweepSectionGenerator` — [GeomFill_Pipe.hxx](https://git.rbts.co/OpenCascade/occt/raw/commit/a34bddcfd60b401f81f8f8bbd500ee644c48e6ee/src/GeomFill/GeomFill_Pipe.hxx), [OCC refman](https://dev.opencascade.org/doc/refman/html/class_geom_fill___pipe.html), [SweepSectionGenerator](https://dev.opencascade.org/doc/refman/html/class_geom_fill___sweep_section_generator.html)
- FreeCAD Curves workbench (external add-on): Sweep2Rails takes two rails plus at least two profiles, or a ruled surface plus profiles. GordonSurface skins a curve network and needs at least two guides and two profiles — [Curves Sweep2Rails](https://wiki.freecad.org/Curves_Sweep2Rails), [Curves GordonSurface](https://wiki.freecad.org/Curves_GordonSurface), [Curves WB](https://wiki.freecad.org/Curves_Workbench/en)
- Tensor B-spline approximation in OCC is `GeomAPI_PointsToBSplineSurface`:
  - `(Points, DegMin=3, DegMax=8, Continuity=C2, Tol3D=1e-3)`
  - `(Points, ParType, ...)` with ParType Approx_ChordLength (default), Centripetal or IsoParametric
  - `(Points, Weight1, Weight2, Weight3, DegMax, Continuity, Tol3D)` for variational smoothing
  - a ZGrid form
  - `Interpolate(...)`, which always gives degree 3 / C2
  - Input is a TColgp_Array2OfPnt grid; index 1 is U, index 2 is V
  — [OCC refman](https://occt3d.com/dev/doc/refman/html/class_geom_a_p_i___points_to_b_spline_surface.html)
- In FreeCAD, `Part.BSplineSurface().approximate(...)` wraps that class. The commit that added it shows `approximate(points, degMin, degMax, continuity, tol)` plus a Z-grid variant. The curve version accepts `ParamType` ('Uniform', 'Centripetal', 'ChordLength') and `LengthWeight` / `CurvatureWeight` / `TorsionWeight`. With non-zero weights, continuity must be C0, C1 or C2 — [surface commit](https://gitea.suzanne.soy/suzanne.soy/FreeCAD/commit/70bb37ab9d730e1961a46096fbce8e1b49b91f7d), [curve commit](https://gitea.suzanne.soy/suzanne.soy/FreeCAD/commit/f13f57ef3d2e1dbef8c3bfb47bda44759c1accdd)

### Inferences
These are my own engineering recommendations, built from the cited APIs plus standard B-spline practice. Verify them in FreeCAD 1.1.

- **Rail.** Fit `rail = Part.BSplineCurve(); rail.approximate(Points=pts, DegMax=5, Tolerance=..., ParamType='ChordLength')`. Reparameterise to arc length by sampling `rail.length(u0, u)` or by refitting on uniform arc-length samples. Then s = arc length, normalised to [0,1].
- **Frame.** Compute an RMF in numpy by double reflection (r_i, t_i are the frame vector and tangent at sample i):
  - v1 = x_{i+1} - x_i; c1 = v1·v1
  - rL = r_i - (2/c1)(v1·r_i)v1; tL = t_i - (2/c1)(v1·t_i)v1
  - v2 = t_{i+1} - tL; c2 = v2·v2
  - r_{i+1} = rL - (2/c2)(v2·rL)v2
  For an arch lip it is often better to set r(s) = the panel normal at C(s), projected perpendicular to C'(s): this is what `setSpineSupport(panelFace)` does. That keeps "across" (t) tied to the panel, which suits the G1 join.
- **Parameterisation of points.** For each mesh point p:
  1. Find s* = argmin |p - C(s)|, via `rail.parameter(FreeCAD.Vector(p))` (OCC point projection) or a KD-tree on dense rail samples followed by a Newton step.
  2. Set d = p - C(s*), t = d·r(s*) (across, in-panel), h = d·b(s*) (height off the panel, where b = T x r).
  The band is then data h(s,t), or (t,h) sections per s.
- **Surface options, in order of control:**
  1. **numpy least-squares tensor B-spline** in (s,t). Use a clamped cubic knot vector in each direction and basis matrices N_s and N_t (Cox-de Boor; `scipy.interpolate.BSpline.design_matrix` if scipy is there). Solve min ||A·P - X||^2 + λ||D2·P||^2 for the 3D poles. Hand the poles to `Part.BSplineSurface().buildFromPolesMultsKnots(poles, umults, vmults, uknots, vknots, False, False, udeg, vdeg)`. This works on scattered points; the OCC approximate needs a grid.
  2. **Resample to a grid, then `Part.BSplineSurface().approximate(Points=grid, DegMin=3, DegMax=5, Continuity=2, Tolerance=tol)`**. Resample by evaluating a smoothed h(s,t), e.g. from method 1 or per-section spline fits, on a regular (s_i, t_j) grid and mapping back to 3D. This is quick, but it has no edge constraints.
  3. **MakePipeShell**: sections fitted at k stations become `Part.BSplineCurve` wires placed in the rail frame. Then:
     ```
     ps = Part.BRepOffsetAPI_MakePipeShell(Part.Wire(rail.toShape()))
     ps.setSpineSupport(panelFace)   # or ps.setFrenetMode(False)
     for w, v in sections:
         ps.add(w, v, WithContact=False, WithCorrection=True)
     ps.build()
     face = ps.shape().Faces[0]
     ```
     Sections must be compatible (same orientation and edge count). G1 to the panel is not guaranteed; it depends on each section's end tangent.
  4. **GeomFill_Pipe(path, c1, c2, R)**: only if the lip really is a constant-radius roll between two contact curves. It is not obviously exposed in FreeCAD Python.
- **G1 to the adjacent panel inside the least-squares fit.** Choose the strip's t direction so that t = 0 is the junction curve on the panel.
  - Pole row 0: take it from the panel boundary curve. For an exact shared edge, use the panel's isocurve or a projected curve with the same knots in s.
  - Pole row 1: constrain it to row0 + α_k·(panel cross-boundary tangent at the matching Greville point), with α_k > 0 unknowns or a single shared α. This is the standard sufficient condition for G1: the row-1 poles lie on the panel's tangent planes along the shared boundary, matched on the same s knot vector.
  - Solve the remaining rows by least squares. This is the linear "constraint equations" approach that Benkő et al. describe for swept regions.
- **Alternative G1 route without custom code:** `Part.BRepOffsetAPI_MakeFilling` with the panel edge added at Order=1 against the panel face, plus data points from the lip (see below).

### Gaps
- No working FreeCAD Python example of `setSpineSupport` or `setAuxiliarySpine` was found. Issue #2961 says the auxiliary-spine wrapper has had problems. Test it before relying on it.
- The exact keyword list of `Part.BSplineSurface.approximate` in FreeCAD 1.1 (whether it takes ParamType or LengthWeight like the curve version) is not confirmed. Check with `help(Part.BSplineSurface.approximate)`.
- The full text of Ueng-Lai was not available, so their exact objective function and parameter-correction steps are unknown.

## OpenCASCADE / FreeCAD tools for filling, G1 constraints, fillets and offsets — call patterns and caveats

### Takeaway
For a G1 patch that also passes through scan points, `Part.BRepOffsetAPI_MakeFilling` (BRepFill_Filling / GeomPlate) is the built-in tool. It takes edge constraints with a support face and Order 0/1/2 (C0/G1/G2), free face constraints, point constraints and an initial surface, and it reports G0/G1/G2 errors. Use MakePipeShell for rail-driven sweeps. Use `GeomAPI_PointsToBSplineSurface` (via `Part.BSplineSurface.approximate`) for gridded data.

### Cited Findings
- FreeCAD `Part.BRepOffsetAPI_MakeFilling` (N-side filling) methods:
  - `setConstrParam(Tol2d=1e-5, Tol3d=1e-4, TolAng=0.01, TolCurv=0.1)`
  - `setResolParam(Degree=3, NbPtsOnCur=15, NbIter=2, Anisotropy=False)`
  - `setApproxParam(MaxDeg=8, MaxSegments=9)`
  - `loadInitSurface(face)`
  - `add(Edge, Order, IsBound=True)`, `add(Edge, Support, Order, IsBound=True)`, `add(Support, Order)` (free face constraint), `add(Point)`, `add(U, V, Support, Order)`
  - `build()`, `isDone()`, `shape()`, `G0Error(i)`, `G1Error(i)`, `G2Error(i)`
  — [FreeCAD .pyi (HF mirror)](https://huggingface.co/AbdulElahGwaith/FreeCAD/blob/main/src/Mod/Part/App/BRepOffsetAPI_MakeFilling.pyi)
- Order must be 0, 1 or 2, meaning C0, G1 or G2 — [FreeCAD MakeFillingPyImp.cpp](https://huggingface.co/AbdulElahGwaith/FreeCAD/blob/main/src/Mod/Part/App/BRepOffsetAPI_MakeFillingPyImp.cpp)
- In OCC, a G1 edge constraint means the surface passes through the edge's 3D curve and keeps tangency with the edge's first face. The result is made by deforming the initial surface to meet the constraints — [OCC BRepFill_Filling 7.8](https://dev.opencascade.org/doc/occt-7.8.0/refman/html/classBRepFill__Filling.html), [MakeFilling.hxx](https://git.rbts.co/OpenCascade/occt/raw/branch/step_losing_attrs/src/BRepOffsetAPI/BRepOffsetAPI_MakeFilling.hxx)
- The Surface workbench `Surface::Filling` object can be scripted. Boundary edges go in as a LinkSubList on `BoundaryEdges`, and a "Support surface" can be set. The wiki example with a cylinder support reports a much closer match to the cylindrical face — [Surface Filling wiki](https://wiki.freecad.org/Surface_Filling)
- `GeomAPI_PointsToBSplineSurface` periodic option: keep the first and last rows distinct when `thePeriodic` is true — [OCC refman](https://occt3d.com/dev/doc/refman/html/class_geom_a_p_i___points_to_b_spline_surface.html)

### Inferences
These come from general OCC/FreeCAD knowledge; check them in FreeCAD 1.1.

- **G1 lip patch with MakeFilling:**
  ```
  f = Part.BRepOffsetAPI_MakeFilling()
  f.setResolParam(Degree=3, NbPtsOnCur=20, NbIter=3)
  f.setApproxParam(MaxDeg=8, MaxSegments=16)
  f.add(junctionEdge, panelFace, 1)   # G1 to the panel
  f.add(lipOuterEdge, 0)              # C0 at the free lip edge
  f.add(sideEdges..., 0)
  for p in lipSamplePoints:
      f.add(FreeCAD.Vector(*p))       # point constraints pull the shape to the scan
  f.loadInitSurface(initFace)         # e.g. the least-squares tensor spline
  f.build()
  print(f.G0Error(), f.G1Error())
  ```
  The junction edge should lie on panelFace, i.e. be one of its edges or a curve on it, so that a pcurve exists. Many point constraints make GeomPlate slow, so subsample to a few hundred.
- **BRepFilletAPI_MakeFillet** (`shape.makeFillet(radius, edges)` in FreeCAD) only works when the lip is a fillet between two existing solid faces. For a free-form flared arch it rarely matches a scan. Use it only to get a crown radius after the faces are built.
- **Offsets for the lip's thickness/return flange:** `face.makeOffsetShape(offset, tol)` (BRepOffsetAPI_MakeOffsetShape) or `Part.makeThickness`. Offsetting a B-spline face with a radius smaller than the offset self-intersects, so keep the crown radius larger than the panel thickness.
- **Trimming:**
  - Project the trim curve onto the face with `face.project([edge])`, or build a pcurve by `face.Surface.parameter(pt)` sampling.
  - Make a trimmed face with `Part.Face(face.Surface, wire)` or `Part.Face(face, wire)`. Alternatively split with `face.common(prismOrSolid)` / `face.cut(tool)`, or `BOPTools.SplitAPI.slice`.
  - The parametric route is simplest when the strip's (s,t) are its native (u,v): trim lines then become isoparametric. `surf.segment(u0, u1, v0, v1)` cuts the B-spline exactly, with no Booleans.
- **Joining G1 to the panel as one shell:** after building, `Part.Shell([panelFace, lipFace])` then `.sewShape()` / `Part.Shell(...).removeSplitter()`. Check the angle along the shared edge by sampling normals on both faces at matching points (`face.normalAt(u, v)`).

### Gaps
- `GeomFill_ConstrainedFilling`, `GeomFill_BSplineCurves` and the GeomPlate low-level classes (`GeomPlate_BuildPlateSurface`, `GeomPlate_MakeApprox`) were not checked for FreeCAD Python bindings. They appear to need pythonocc or OCP rather than FreeCAD's Part module. `Part.BSplineSurface` has related builders (e.g. `buildFromNSections`, and Coons/Gordon via the Surface workbench `GeomFillSurface`), but their signatures were not confirmed this session.

## Blend running out at a free panel edge, and corners where the arch meets another feature

### Takeaway
I found no direct source on run-outs. The OCC tools offer three handles: sweep end sections that may be a vertex (a section that collapses to zero), `ContactOnBorder` for a width that varies with the auxiliary rail, and in filling, mixing G1 constraints on the panel edge with C0 constraints at the run-out. In practice, fade the section height h to zero (or into the panel's own profile) over a short s-interval, and trim on the panel's edge.

### Cited Findings
- MakePipeShell allows the first and last sections to be a vertex rather than a wire, so a sweep can collapse to a point — [OCC refman](https://occt3d.com/dev/doc/refman/html/class_b_rep_offset_a_p_i___make_pipe_shell.html), [FreeCAD .pyi](https://huggingface.co/AbdulElahGwaith/FreeCAD/blob/main/src/Mod/Part/App/BRepOffsetAPI_MakePipeShell.pyi)
- With `BRepFill_ContactOnBorder` the auxiliary spine is a boundary and the width varies. With `BRepFill_Contact` the width is constant. Both auxiliary-spine contact modes give only C0 surfaces — [OCC refman](https://occt3d.com/dev/doc/refman/html/class_b_rep_offset_a_p_i___make_pipe_shell.html)
- For rail fractures (corners in the spine), MakePipeShell transition modes are Transformed, RightCorner (needs a connected, planar intersection of the neighbouring pieces) and RoundCorner (reliable only with WithCorrection=True) — [OCC refman](https://occt3d.com/dev/doc/refman/html/class_b_rep_offset_a_p_i___make_pipe_shell.html)
- In RE pipelines, blends are added after the primary faces and topology are set, so blend ends are handled once the faces they meet are known — [Benkő/Martin/Várady 2001 (abstract)](https://orca.cardiff.ac.uk/1811/1/REalgorithms.pdf)

### Inferences
- **Run-out at a free edge** (the lip meets the sill or bumper cut line):
  1. Run the strip's s-range a little past the free edge.
  2. Fade the cross-section height to zero by multiplying h(s,t) by a smooth step (C2 smoothstep) over the last 20-50 mm. Add the fade as weighted pseudo-data in the least-squares fit, so the surface lies down onto the panel.
  3. Trim exactly with `surf.segment` or by Boolean against the panel's free-edge plane/curve.
  Then G1 holds along the junction all the way to the end, and the end itself is just a trim curve.
- **Corners where the arch meets another feature** (a swage line, door shut, bumper): do not force one sweep through the corner. End the lip strip at a cross-section before the corner and fill the gap with `MakeFilling`:
  - G1 to the lip strip's end edge
  - G1 to the other feature's face
  - G1 to the panel
  - C0 on the free side, plus a few scan points
  This N-sided patch is what GeomPlate is designed for, and its G1Error() tells you whether the corner closed.
- **Keep the rail and section count low** (cubic, few spans) so the strip stays fair. Judge fairness by eye against the photos and the mesh (Nik's method) rather than by residuals alone.

### Gaps
- No paper or forum source found on the topology or geometry of fillet run-out ("blend termination" / "vertex blend" in RE) that the search could read. The setback-vertex-blend literature (Várady, Rockwood) was not reached this session.
