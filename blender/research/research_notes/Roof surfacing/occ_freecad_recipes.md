# OpenCASCADE / FreeCAD 1.1.4 recipes for a car ROOF face (fit, G1/G2 join, trim, check, sew)

All numbers below were measured on Nik's PC on 2026-11-11 with FreeCAD 1.1.4 (OCCT 7.8.1, numpy 1.26.4) run headless through `kn5-study/fcrun.sh`. Scripts and raw logs: `D:\ClaudeData\tmp\research_roof\occ\` (`common.py` test geometry + continuity checker, `lsq.py` scattered least-squares fitter, `t1_fit.py` ... `t6_pcurve_sew.py`, logs `t*.txt`).

Test set-up (synthetic, so errors can be measured against a known answer): an analytic roof z(x, y) over x 0..1400 mm, plan half-width 600 mm at mid-length narrowing to 560.8 mm at the ends (tumblehome), 65 mm cross crown, 29 mm length camber, a cubic asymmetry and a 3 mm Gaussian bump near the rear (so it is not a polynomial). Four 100 mm "neighbour" strip faces (left/right cant rails, front header, rear) were interpolated on the same function outward of the roof boundary, so the exact answer is G2 to all four. "dev" = distance from 300 fresh truth points to the fitted surface (`projectPoint(...,"LowerDistance")`). Edge continuity = my own sampler (41 samples per shared edge; G0 gap, normal angle, and difference of normal curvature dk across the edge; reference curvature k ~ 3.6e-4 1/mm, i.e. ~2.8 m radius).

## 1. Fitting a large smooth B-spline surface: Part.BSplineSurface.approximate / interpolate, and scattered points

### Takeaway
`Part.BSplineSurface.approximate` (GeomAPI_PointsToBSplineSurface) only takes a rectangular grid of points (rows = u iso-lines); it fits a station/profile grid to 0.005 mm in milliseconds but cannot take scattered points (a 1xN row is refused, a reshaped scatter gives 480 mm garbage). For scattered mesh vertices the two working routes in FreeCAD 1.1.4 are (a) GeomPlate point constraints (`Part.GeomPlate.BuildPlateSurface` or `BRepOffsetAPI.MakeFilling.add(Point)`), 0.004 mm on 300-2000 points but slow above ~1000 points, and (b) an own numpy least-squares fit on fixed knots + `buildFromPolesMultsKnots`, ~1 s, 0.02-0.2 mm, and it can carry G0/G1/G2 rows along arbitrary trim curves.

### Cited Findings
- FreeCAD signature (docstring, FreeCAD 1.1.4): `approximate(Points, DegMin, DegMax, Continuity, Tolerance [, X0, dX, Y0, dY])`, keyword `ParamType='Uniform'|'Centripetal'|'ChordLength'`, or the smoothing variant `approximate(Points, DegMax, Continuity, Tolerance, LengthWeight, CurvatureWeight, TorsionWeight)`; "with this smoothing algorithm, continuity C1 requires DegMax >= 3 and C2, DegMax >= 5"; Continuity is an int 0/1/2 — [introspect.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/introspect.txt)
- OCCT: input is a 2D array `Points(i,j)`, first index = U; DegMin/DegMax defaults 3/8, Continuity default C2, Tol3D default 1e-3 = max distance points-to-surface; ParType ChordLength (default) / Centripetal / IsoParametric; the smoothing Init minimises "Weight1*CurveLength + Weight2*Curvature + Weight3*Torsion" — [OCCT GeomAPI_PointsToBSplineSurface](https://occt3d.com/dev/doc/refman/html/class_geom_a_p_i___points_to_b_spline_surface.html)
- `interpolate(points2d)` is always degree 3, C2 — [OCCT GeomAPI_PointsToBSplineSurface](https://occt3d.com/dev/doc/refman/html/class_geom_a_p_i___points_to_b_spline_surface.html); FreeCAD docstring says the same — [introspect.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/introspect.txt)
- Measured (grid of stations x profiles on the roof, `t1_fit.txt`):
  - `DegMin=3, DegMax=3, Continuity=2` fails with "GeomAPI_PointsToBSplineSurface: Surface not done" on every grid (15x11, 29x21, 57x41). Use DegMax >= 5 for C2 — [t1_fit.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t1_fit.txt)
  - `DegMin=3, DegMax=5, C2, Tol 0.01`: 29x21 grid -> degree 5x4, 13x5 poles, dev max 0.0049 mm, 0.02 s; Centripetal vs ChordLength made no real difference on an even grid (0.0047 vs 0.0049) — [t1_fit.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t1_fit.txt)
  - `DegMax=8, Tol 0.001`: degree 8x8, 27x9 poles, dev < 0.0001 mm — [t1_fit.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t1_fit.txt)
  - Smoothing variant (DegMax 5, Tol 0.05): LengthWeight=1 -> 0.0049 mm; CurvatureWeight=1 -> 0.0049 mm; (0.1, 0.5, 0.4) -> 0.0056 mm; always 15x6 poles. On a 15x11 coarse grid the curvature-only weight was worst (0.0114 mm). The weights hardly matter for clean data; they matter for noisy grids (not tested) — [t1_fit.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t1_fit.txt)
  - `interpolate` 29x21 -> 31x23 poles, 0.5 s, dev 0.0002 mm (passes through noise too; avoid on mesh data) — [t1_fit.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t1_fit.txt)
  - Scattered points: `approximate(Points=[list_of_300])` -> "not enough points given"; 300 random points reshaped to 15x20 -> dev max 482 mm. Not usable for scatter — [t1_fit.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t1_fit.txt)
- Own least squares for scattered points (`lsq.py`, measured in `t2_lsq.txt`): plan projection u = x/1400, v = (y+600)/1200; clamped uniform bicubic knots; all three coordinates solved together; thin-plate-like penalty on S_uu, S_uv, S_vv sampled on a 30x30 grid; solve with `numpy.linalg.lstsq`; build with `Part.BSplineSurface().buildFromPolesMultsKnots(poles, umults, vmults, uknots, vknots, False, False, 3, 3)`. My numpy basis matched OCC evaluation to 4e-16 (value), 2e-14 (d1), 9e-14 (d2) — [t2_lsq.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t2_lsq.txt)
  - The smoothing weight must be small: with my scaling lam = 1e-3 flattened the crown (dev 21 mm); lam = 1e-7..1e-9 is right for clean data, lam = 1e-7 for 0.3 mm noise (lam 1e-9 with noise -> 2-7 mm wiggles near the unsupported plan-rectangle corners) — [t2_lsq.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t2_lsq.txt)
  - Free fit (no boundary rows), 2000 clean points, 12x10 spans, lam 1e-9: dev max 0.016 mm, mean 0.001 mm, 0.4 s. More spans (20x16) did not help (0.056 mm) — [t2_lsq.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t2_lsq.txt)
  - With G0+G1 boundary rows (weight 300 x sqrt(N/1000)), lam 1e-7, 12x10 spans: N=1000 clean dev max 0.031 / mean 0.005 mm; N=1000 noise 0.3 mm dev max 0.22 / mean 0.06 mm; N=2000 clean 0.023 / 0.004 mm; ~1.1 s each — [t2_lsq.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t2_lsq.txt)
- GeomPlate as a scattered-point fitter (measured, `t3_plate_*.txt`): 4 boundary curves (order 0) + N point constraints, `Degree=3, NbPtsOnCur=15, NbIter=2`, then `makeApprox(Tol3d=0.01, MaxSegments=12, MaxDegree=8, MaxDistance=0.01, CritOrder=0, Continuity='C1')` -> 16x16 poles degree 8: N=300 dev max 0.0051 mm (perform 0.05-0.07 s); N=1000 0.0040 mm (1.1-1.7 s); N=2000 0.0042 mm (6.5-9.6 s). Boundary curves alone (N=0) give dev 2.3 mm (a plate is only as good as its constraints) — [t3_plate_0_300.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_0_300.txt), [t3_plate_2000.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_2000.txt)
- Loading the LSQ fit as the plate's initial surface (`bp.loadInitSurface(srf)`) did not help: 300 points dev 0.0089 mm vs 0.0060 mm without — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)
- OCCT describes plate as deforming a surface "so that it conforms to a given number of curve or point constraints", "minimizing energy input"; "If not already given in the input, an initial surface is calculated"; conversion via MakeApprox — [OCCT Modeling Algorithms guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)

### Inferences
- Recipe for a roof from game-mesh vertices: (1) if the data can be resampled to stations x profiles (as for the C-pillar), `approximate(..., DegMin=3, DegMax=5..8, Continuity=2, Tolerance=0.01)` is the fastest and very accurate; (2) for raw scattered vertices use the own-LSQ fit when you also need boundary continuity rows (fast, controllable), or GeomPlate/MakeFilling when you have <= ~1000 points and want the highest accuracy with no tuning.
- The degree-8, 16x16 to 23x23 pole surfaces from GeomPlate are heavier than the 15x13 bicubic LSQ surface; for a game model that later gets tessellated this does not matter, but for later editing/regression the bicubic is nicer.
- Plan projection (u = x, v = y) only works because a roof is a height field; for a general panel use a best-fit plane (PCA) or the station/profile parameters of a base surface.

Minimal snippets:
```python
# grid fit (stations x profiles)
s = Part.BSplineSurface()
s.approximate(Points=grid, DegMin=3, DegMax=5, Continuity=2, Tolerance=0.01, ParamType='Centripetal')
# smoothing variant (keywords!)
s.approximate(Points=grid, DegMax=5, Continuity=2, Tolerance=0.05, LengthWeight=0.1, CurvatureWeight=0.5, TorsionWeight=0.4)

# scattered points through GeomPlate
bp = Part.GeomPlate.BuildPlateSurface(Degree=3, NbPtsOnCur=15, NbIter=2)
for e in boundary_edges: bp.add(Part.GeomPlate.CurveConstraint(Boundary=e.Curve, Order=0, NbPts=15))
for p in pts:            bp.add(Part.GeomPlate.PointConstraint(Point=p))      # p = FreeCAD.Vector
bp.perform()
bs = bp.surface().makeApprox(Tol3d=0.01, MaxSegments=12, MaxDegree=8, MaxDistance=0.01, CritOrder=0, Continuity='C1')
```

### Gaps
- Not tested: noisy data through `approximate`'s smoothing weights, and real game-mesh vertices (faceting rather than random noise). The synthetic truth is smooth; a real roof mesh has sparse vertices at low-poly density.
- Not tested: PCA/base-surface parametrisation for non-height-field panels, and adaptive knot insertion.

## 2. GeomPlate / MakeFilling with point constraints plus G1 (and G2) boundary constraints to neighbour faces

### Takeaway
In FreeCAD 1.1.4 only `Part.BRepOffsetAPI.MakeFilling` can make a plate tangent to neighbour faces: `add(edge_of_neighbour, neighbour_face, 1, True)` plus `add(Vector)` per data point gave G1 to 0.0045 deg and dev 0.0007-0.002 mm (300-2000 points, 0.16-7 s). `Part.GeomPlate.CurveConstraint` only takes a bare 3D curve, so Order=1 raises "Curve must be on a Surface". G2 is not reachable through either binding: MakeFilling order 2 is cast to GeomAbs_C1 and behaves exactly like order 0 (identical numbers), and 3 is refused. For G2 use the own-LSQ fitter with linearised curvature rows.

### Cited Findings
- `Part.GeomPlate` exposes `BuildPlateSurface`, `CurveConstraint`, `PointConstraint`; `Part.PlateSurface` is a separate convenience class with `makeApprox` — [introspect2.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/introspect2.txt)
- `BuildPlateSurface(Surface=None, Degree=3, NbPtsOnCur=10, NbIter=3, Tol2d=1e-5, Tol3d=1e-4, TolAng=0.01, TolCurv=0.1, Anisotropy=False)`; methods `add(constraint)`, `loadInitSurface(surf)`, `perform()`, `surface()`, `surfInit()`, `curves2d()`, `order()`, `sense()`, `G0Error([i])`, `G1Error([i])`, `G2Error([i])` — [FreeCAD BuildPlateSurfacePyImp.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/GeomPlate/BuildPlateSurfacePyImp.cpp)
- `CurveConstraint(Boundary=<Geom curve>, Order=0, NbPts=10, TolDist=1e-4, TolAng=0.01, TolCurv=0.1)` wraps the curve in a plain `GeomAdaptor_Curve` — no support face can be passed; `setG0/G1/G2Criterion` raise NotImplementedError — [FreeCAD CurveConstraintPyImp.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/GeomPlate/CurveConstraintPyImp.cpp)
- Measured: `CurveConstraint(..., Order=1)` -> `RuntimeError('GeomPlate_CurveConstraint.cxx : Curve must be on a Surface')` — [t3_plate_0_300.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_0_300.txt)
- `PointConstraint(Point=<Vector>, Order=0, TolDist=1e-4)` calls only the 3D-point constructor; no (U, V, Surface) tangency form is bound — [FreeCAD PointConstraintPyImp.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/GeomPlate/PointConstraintPyImp.cpp)
- `Part.PlateSurface(Surface, Points, Curves, Degree, NbPtsOnCur, NbIter, Tol2d, Tol3d, TolAng, TolCurv, Anisotropie)`: `Curves` is accepted but ignored (`// TODO`); `makeApprox(Tol3d=0.01, MaxSegments=9, MaxDegree=3, MaxDistance=1e-4, CritOrder=0, Continuity='C1', EnlargeCoeff=1.1)`, Continuity is a case-sensitive string and unknown strings silently become C1 — [FreeCAD PlateSurfacePyImp.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/PlateSurfacePyImp.cpp)
- Measured: `Part.PlateSurface(Points=424 points, Degree=3, NbIter=2)` crashed freecadcmd with "Access violation" — use `GeomPlate.BuildPlateSurface` instead — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)
- `MakeFilling(Degree=3, NbPtsOnCur=15, NbIter=2, MaxDegree=8, MaxSegments=9, Tol2d=1e-5, Tol3d=1e-4, TolAng=0.01, TolCurv=0.1, Anisotropy=False)`. `add` overloads: `add(Vector)`, `add(Support=face, Order)`, `add(Constraint=edge, Order, IsBound=True)`, `add(edge, face, Order, IsBound=True)`, `add(U, V, face, Order)`; orders outside 0..2 are refused and cast with `static_cast<GeomAbs_Shape>(order)` (the message says "0 -> C0, 1 -> G1, 2 -> G2") — [FreeCAD BRepOffsetAPI_MakeFillingPyImp.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/BRepOffsetAPI_MakeFillingPyImp.cpp)
- Measured: `setApproxParam(MaxDeg=8, MaxSegments=9)` with keywords raises "'MaxDeg' is an invalid keyword argument"; pass positionally `setApproxParam(8, 9)`, `setResolParam(3, 15, 2, False)`, `setConstrParam(1e-5, 1e-4, 0.01, 0.1)`. `mf.shape()` returns a generic `Part.Shape` (no `.Surface`); use `mf.shape().Faces[0]` — [t3_plate_0_300.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_0_300.txt)
- OCCT `BRepFill_Filling`: free points `Add(gp_Pnt)` are hard-coded `GeomAbs_C0`; `Add(U, V, Support, Order)` builds `GeomPlate_PointConstraint(U, V, surface, Order, ...)`; edge+face constraints pass the order through unchanged; the only test on the order is `== GeomAbs_C0` — [OCCT BRepFill_Filling.cxx (V7_8_0)](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_8_0/src/BRepFill/BRepFill_Filling.cxx)
- Measured, 4 neighbour edges + N free points (`t3_plate_*.txt`):

  | N | order | time | poles | dev max / mean (mm) | edge G0 (mm) | edge G1 (deg) | dk_cross (1/mm) |
  |---|---|---|---|---|---|---|---|
  | 0 | 0 | 0.03 s | 23x23 d8 | 2.30 / 0.49 | 0.0012 | 0.353 | 5.6e-5 |
  | 0 | 1 | 0.02 s | 23x23 d8 | 1.03 / 0.29 | 0.0005 | 0.0054 | 5.5e-5 |
  | 300 | 0 | 0.07 s | 16x16 d8 | 0.0052 / 0.0009 | 0.0026 | 0.018 | 1.2e-5 |
  | 300 | 1 | 0.16 s | 23x23 d8 | 0.0022 / 0.0002 | 0.0007 | 0.0045 | 7.2e-6 |
  | 1000 | 1 | 1.4 s | 23x23 d8 | 0.0010 / 0.0001 | 0.0007 | 0.0048 | 6.9e-6 |
  | 2000 | 1 | 7.0 s | 23x23 d8 | 0.0007 / 0.0001 | 0.0007 | 0.0046 | 6.7e-6 |
  | any | 2 | = order 0, identical digits | | | | | |

  — [t3_plate_0_300.txt](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_0_300.txt), [t3_plate_1000.txt](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_1000.txt), [t3_plate_2000.txt](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_2000.txt) (local)
- The plate's own `G1Error()/G2Error()` read 0.0000 in every case, including order 0 where my sampler measured 0.35 deg; do not trust them as a continuity check — [t3_plate_0_300.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_0_300.txt)
- The edge passed to `add(edge, face, ...)` must be the neighbour face's own edge (it needs a pcurve on that face); I picked it as the face edge closest to the 3D boundary curve — [t3_plate.py, local](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate.py)
- G2 via own LSQ (`lsq.py`, rows n.S_ij = II_neighbour(S_i, S_j) using the previous iterate's tangents, 2 extra solves, 1000 points, `t4_g2_trim_sew.txt`): without G2 rows dk_cross 2.3e-5 (6 % of k); G2 weight 3 -> 7.7e-6 (2 %), dev 0.012 mm; weight 30 -> 1.3e-6 (0.4 %), G1 0.0037 deg, G0 0.0003 mm, dev 0.015 mm; 3.3 s — [t4_g2_trim_sew.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t4_g2_trim_sew.txt)
- More spans hurt the boundary curvature match (16x12: dk 5.1e-5; 24x18: 1.3e-4 at G2 weight 0.3), i.e. the extra freedom wiggles at the edges unless the smoothing/G2 weights rise with it — [t4_g2_trim_sew.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t4_g2_trim_sew.txt)

### Inferences
- The earlier finding "order-2 G2 silently treated as C0" is explained: FreeCAD casts int 2 to GeomAbs_C1 (OCCT enum order C0, G1, C1, G2, C2 ...), and BRepFill_Filling/GeomPlate do not act on C1, so it behaves as C0; real G2 (enum 3) is blocked by FreeCAD's 0..2 check. The enum order is from my OCCT knowledge, but the identical order-0/order-2 numbers confirm the behaviour.
- Best plate recipe: MakeFilling, Degree 3 (5 was worse earlier), NbPtsOnCur 15, NbIter 2, MaxDeg 8, MaxSegments 9, neighbour edges at order 1, free data points via `add(Vector)`. Keep data points a few mm away from the boundary (I used a 5 mm margin) so they do not fight the boundary constraint. Time grows roughly with the cube of the constraint count (0.16 s / 1.4 s / 7 s for 300 / 1000 / 2000), so decimate to ~500-1000 points.
- MakeFilling needs the boundary as a closed loop of neighbour edges; for a roof whose trim lines are not existing edges (e.g. the roof only partly bounded by built faces), the own-LSQ route is more flexible because its G1/G2 rows can sit on any 3D curve.

```python
mf = Part.BRepOffsetAPI.MakeFilling()
mf.setResolParam(3, 15, 2, False)          # Degree, NbPtsOnCur, NbIter, Anisotropy  (positional!)
mf.setConstrParam(1e-5, 1e-4, 0.01, 0.1)    # Tol2d, Tol3d, TolAng, TolCurv
mf.setApproxParam(8, 9)                     # MaxDeg, MaxSegments
for e, f in [(edgeF, faceF), (edgeR, faceR), (edgeB, faceB), (edgeL, faceL)]:
    mf.add(e, f, 1, True)                   # 1 = G1; 2 is NOT G2
for p in pts: mf.add(p)                     # free G0 points
mf.build(); roof = mf.shape().Faces[0]
```

### Gaps
- Not tested: `add(Support=face, Order)` free constraints, `IsBound=False` interior curve constraints (e.g. a styling line across the roof), and Anisotropy=True for a long narrow roof.
- A true G2 plate would need a C++ or pybind call (GeomAbs_G2 = 3) outside FreeCAD's binding; not attempted.

## 3. Tangent/normal constraints at interior points (GeomPlate_PointConstraint order 1)

### Takeaway
Only through MakeFilling: `mf.add(u, v, guide_face, 1)` makes the filling pass through the guide face's point with the guide's tangent plane. Nine such constraints on a G1-bounded fill cut the normal error at those points from 0.24 deg (order 0) to 0.008 deg and the overall dev from 1.03 mm to 0.12 mm. `Part.GeomPlate.PointConstraint` cannot do it (3D point only; `setPnt2dOnSurf` exists but no surface can be attached).

### Cited Findings
- `PointConstraint` binding: keywords `Point, Order, TolDist`, constructs `GeomPlate_PointConstraint(gp_Pnt, order, tolDist)`; it "cannot create a point on a face with tangent order 1 directly from Python" — [FreeCAD PointConstraintPyImp.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/GeomPlate/PointConstraintPyImp.cpp)
- MakeFilling `add(U, V, Support, Order)` -> `GeomPlate_PointConstraint(U, V, BRep_Tool::Surface(face), Order, myTol3d, myTolAng, myTolCurv)` — [FreeCAD BRepOffsetAPI_MakeFillingPyImp.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/BRepOffsetAPI_MakeFillingPyImp.cpp); [OCCT BRepFill_Filling.cxx](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_8_0/src/BRepFill/BRepFill_Filling.cxx)
- Measured (4 G1 edges + 9 probe points, guide = 57x41 grid fit of the truth): no points: dist 1.05 mm, angle 0.169 deg, dev 1.03 mm; order 0: dist 0.0008 mm, angle 0.242 deg, dev 0.55 mm; order 1: dist 0.0007 mm, angle 0.0082 deg, dev 0.12 mm; each ~0.4 s — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)
- In the own-LSQ route a normal constraint at any point is two linear rows, n.S_u = 0 and n.S_v = 0 (used for the boundary G1 rows, G1 0.007 deg at weight 300) — [t2_lsq.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t2_lsq.txt)

### Inferences
- Useful to pin the roof's crown line or a few photo-measured normals: build a rough guide face (e.g. a station/profile approximate), then add a handful of `(u, v, guide, 1)` constraints. Many point-tangent constraints cost like many points (cubic growth).

### Gaps
- Order 2 (curvature) at points not testable for the same GeomAbs_C1 cast reason.

## 4. Trimming a fitted surface by 3D curves

### Takeaway
Most robust in FreeCAD 1.1.4: `Part.Face(surface, Part.Wire(sorted 3D edges))` then `face.validate()` (M1b) — valid, 4 edges, boundary exactly on the curves, 0.035 s, and the only face variant that later sewed. `generalFuse(face, edges, fuzzy)` (M5) and `BOPTools slice` with extruded walls (M4) also work (0.03 s / 0.17 s) but split edges at the corners (6-7 edges). Building pcurves yourself from `Surface.parameter` samples (M1) gives a valid face but one that would not sew. `Face.project` + `makeSplitShape` failed in this test (projected curves up to 113 mm off; wrong piece).

### Cited Findings
- Measured on the LSQ roof surface (plan rectangle, larger than the roof) trimmed by the 4 neighbour boundary curves (which lie on it within ~0.0002 mm) — [t4_g2_trim_sew.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t4_g2_trim_sew.txt):

  | method | time | valid | edges | max boundary dev (mm) |
  |---|---|---|---|---|
  | M1 pcurves from `srf.parameter()` samples -> `Geom2d.BSplineCurve2d.interpolate` -> `c2d.toShape(srf)` -> `Part.Face(srf, wire)` | 0.145 s | True | 4 | 0.0002 |
  | M1b `Part.Face(srf, Part.Wire(Part.__sortEdges__(edges3d)))` + `validate()` | 0.035 s | True | 4 | 0.0000 (tol 2.5e-4) |
  | M2 `big.project(edges)` + `Part.makeSplitShape(big, [(wire, big)])` | 0.21 s | True | 4 | 32.5 (wrong piece) |
  | M3 `big.makeParallelProjection(wire, -Z)` + `Part.Face(srf, wire)` | 0.27 s | True | 7 | 0.0002 |
  | M4 `BOPTools.SplitAPI.slice(big, extruded walls, 'Split')` | 0.17 s | True | 7 | 0.0002 |
  | M5 `big.generalFuse(edges3d, 1e-3)` | 0.028 s | True | 6 | 0.0000 |
- `Face.project([edges])` returned 4 edges whose maximum distance to the original curves was 112.9 mm; `makeSplitShape` then returned the same 1 676 600 mm2 face in both lists (roof area 1 657 876 mm2) — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)
- `Part.makeSplitShape(shape, [(wire_or_edge_or_compound, face)], checkInterior=True)` is BRepFeat_SplitShape; the wire "must lie on the face"; returns (faces left of the wires, remaining shape) — [introspect2.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/introspect2.txt)
- GeomPlate's own route: `bp.curves2d()` returns the boundary as 4 BSplineCurve2d on the plate; `Part.Face(approx_surface, Part.Wire([c.toShape(approx) for c in curves2d]))` gave a valid 4-edge face with tolerance 1e-7 — [t3_plate_2000.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_2000.txt)
- OCCT: "The edges on a face must have a parametric curve description"; if missing "it is computed by projection, moreover, the calculation is possible only for the planar face" (MakeFace context) — [OCCT Modeling Algorithms guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html). In practice `face.validate()` (ShapeFix) added the pcurves on the curved B-spline surface in M1b — [t4_g2_trim_sew.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t4_g2_trim_sew.txt)
- M1 faces (pcurve-built edges) had BSplineCurve 3D curves but still did not sew (20 free edges) even after `face.fix(...)` or `ShapeFix.Edge().fixAddCurve3d(e)`; the M1b face sewed (16 edges, 12 free) — [t6_pcurve_sew.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t6_pcurve_sew.txt)

### Inferences
- Recipe: fit the surface a little larger than the roof (plan rectangle), then `roof = Part.Face(srf, Part.Wire(Part.__sortEdges__([neighbour boundary edges...]))); roof.validate()`. Use the neighbours' actual edges (or curves already lying on the surface within ~1e-3 mm) so the trim and the shared edge are the same curve — that is also what makes sewing trivial.
- If the trim curve is not on the surface (e.g. a styling line from the photo), first make it lie on the surface: sample it, project the samples with `srf.parameter(p)` / `projectPoint`, interpolate in 3D (or 2D), then use M1b; or use M5 `generalFuse` with a fuzzy value just above the curve's off-surface distance. Avoid `Face.project` for long curves over a big face until its 113 mm error is understood.

```python
w = Part.Wire(Part.__sortEdges__(trim_edges))   # 3D edges lying on srf
roof = Part.Face(srf, w); roof.validate()        # ShapeFix adds pcurves
assert roof.isValid()
# alternative: res, _ = srf.toShape().generalFuse(trim_edges, 1e-3); pick the piece containing an interior point
```

### Gaps
- Why the M1 (self-made pcurve) face refuses to sew and why `Face.project` drifted 113 mm were not root-caused (possibly SameParameter flags / vertex sharing for M1, and projection direction or face-boundary clipping for M2).
- Not tested: `BRepAlgo_NormalProjection` options (it is behind `Face.project`; no direct binding with tolerance/continuity settings was found).

## 5. Measuring G1/G2 continuity between two faces along a shared edge in FreeCAD Python

### Takeaway
No LocalAnalysis binding is needed: sample the edge, get (u, v) on each face with `Surface.parameter(p)`, compare positions (G0), normals (G1) and normal curvatures in the cross-edge, along-edge and 45 deg directions from `getDN` first/second derivatives (G2). This checker (`common.continuity`) is what all numbers above use.

### Cited Findings
- Available primitives: `BSplineSurface.parameter`, `normal`, `getDN(u, v, nu, nv)`, `curvature(u, v, 'Max'|'Min'|'Mean'|'Gauss')`, `curvatureDirections(u, v)`; `Face.curvatureAt`, `derivative1At`, `derivative2At`, `normalAt` — [introspect.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/introspect.txt)
- CurvesWB's continuity tool (`continuity_check.py`) samples the seam, averages the two normals and makes small 2D "star" lines in the plane normal to the seam, parallel-projected onto both faces, for visual checking; it does not output numbers — [CurvesWB continuity_check.py, local copy D:\ClaudeData\FreeCAD\Mod\CurvesWB\freecad\Curves\continuity_check.py](file:///D:/ClaudeData/FreeCAD/Mod/CurvesWB/freecad/Curves/continuity_check.py)
- Method implemented (normal curvature from the second fundamental form): express direction d in (S_u, S_v) by least squares (a, b); k_n = n.(S_uu a^2 + 2 S_uv a b + S_vv b^2) / |a S_u + b S_v|^2, with the second face's normal flipped to agree with the first — [common.py, local](file:///D:/ClaudeData/tmp/research_roof/occ/common.py)
- Sanity of the checker: a grid fit that is G2 by construction read G0 0.003 mm, G1 0.0099 deg, dk_cross 3.3e-6 against k 3.3e-4; a G1-only plate read dk_cross ~5.5e-5 (15 % of k), and the order-0 plate 0.35 deg — the checker separates the cases clearly — [t1_fit.txt](file:///D:/ClaudeData/tmp/research_roof/occ/t1_fit.txt), [t3_plate_0_300.txt](file:///D:/ClaudeData/tmp/research_roof/occ/t3_plate_0_300.txt) (local)

### Inferences
- Suggested pass marks for a game-car body: G0 < 0.01 mm, G1 < 0.05 deg, G2 |dk| < 5 % of the local curvature (or < 1e-5 1/mm on a roof). Also report dk_along: if it is not ~0 the two faces disagree in G1/G0 along the edge.
- Trim the first/last 2 % of the edge when sampling (corner singularities), and sample on the shared 3D curve, not on one face's iso-line.

```python
def nk(s, u, v, d, nref):                      # normal curvature of surface s in 3D direction d
    Su, Sv = s.getDN(u, v, 1, 0), s.getDN(u, v, 0, 1)
    n = Su.cross(Sv); n.normalize(); n = n if n.dot(nref) >= 0 else -n
    a, b = np.linalg.lstsq(np.array([[Su.x, Sv.x], [Su.y, Sv.y], [Su.z, Sv.z]]), np.array([d.x, d.y, d.z]), rcond=None)[0]
    t = Su*a + Sv*b
    return n.dot(s.getDN(u, v, 2, 0)*(a*a) + s.getDN(u, v, 1, 1)*(2*a*b) + s.getDN(u, v, 0, 2)*(b*b)) / t.dot(t)
# per edge sample p, tangent t: ua,va = sA.parameter(p); ub,vb = sB.parameter(p)
# G0 = |sA.value-sB.value|; G1 = angle(nA, nB); cross = nA x t; G2 = |nk(sA,..,cross,nA) - nk(sB,..,cross,nA)|
```

### Gaps
- No published FreeCAD/OCCT reference for numeric G2 checks was looked up; the method is standard differential geometry, verified here only by the consistency of results.

## 6. Sewing faces into one shell and meshing it watertight (brief)

### Takeaway
`shape.sewShape(tol)` works in place and returns None; on a Compound or Shell of roof + 4 neighbours it produced one Shell with 16 edges / 12 free (the outer border) at tol 1e-6, 1e-3 and 1e-2 when the roof was trimmed with the neighbours' own 3D edges. `MeshPart.meshFromShape` of the sewn shell gives one connected, manifold mesh whose only boundary is the outer border (5877 mm); the unsewn compound meshes as separate pieces.

### Cited Findings
- `sewShape` returned `NoneType`; the shape became a Shell with 1 shell, 16 edges, 12 free edges, for Compound or Shell input and tol 1e-6/1e-3/1e-2 — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)
- `generalFuse(fuzzy 1e-3)` + `Part.Shell(res.Faces)` gives the same topology (16 edges, 12 free, valid) in 0.46 s — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)
- Mesh (`MeshPart.meshFromShape(Shape=..., LinearDeflection=0.1, AngularDeflection=0.2, Relative=False)`): unsewn compound 2519 points, boundary 292 edges / 10 943 mm, 3 components (with this face set); sewn shell 2454 points, 4750 triangles, boundary 156 edges / 5877 mm = the expected outer border, 1 component, no non-manifold edges — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)
- A roof face trimmed with self-made pcurve edges (M1) did not sew at any tolerance (Compound, 20 free edges) — [t6_pcurve_sew.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t6_pcurve_sew.txt)
- `Part.ShapeFix.Shape`, `Part.ShapeFix.Shell` etc. are bound (FixFreeShellMode, perform, shape) for repairing a sewn result — [t5_sew_split_pt.txt, local](file:///D:/ClaudeData/tmp/research_roof/occ/t5_sew_split_pt.txt)

### Inferences
- For the full body: trim every panel with the shared 3D edges (M1b), collect all faces in a Compound, `sewShape(0.01)` once, check free edges == the intended open borders (`shape.ancestorsOfType(edge, Part.Face)` count < 2), then mesh with MeshPart; vertices on shared edges are then shared, so the AC kn5 mesh has no cracks.
- `sewShape` has no "non-manifold" or "cutting" options exposed; if those are needed, `generalFuse` + `Part.Shell` is the alternative.

### Gaps
- Not tested: sewing dozens of faces with tolerance mismatches, `Part.Shape.fix` / `ShapeFix.Shell` repair after sewing, and MeshPart's Mefisto/Netgen mesher options for the final game mesh density.
