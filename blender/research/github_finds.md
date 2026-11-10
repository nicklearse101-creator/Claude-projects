# GitHub finds: mesh -> trimmed B-spline panels (2026-11-10)

Ranked by usefulness for the AE86 door / front wing work (FreeCAD 1.1 + numpy).

1. tomate44/CurvesWB (LGPL-2.1, active, already installed in %APPDATA%/FreeCAD/v1-1/Mod/CurvesWB)
   - Trim by UV curves instead of prism booleans: Sketch_On_Surface.py:275 `c2d.toShape(face.Surface, fp, lp)`,
     ShapeMapper.py:110/571, then lib/face_builder.py `shapefix_builder(surface, wires)` (Part.ShapeFix.Face + validate).
   - lib/trimmed_surface.py `TrimmedSurface(face).extend(...)` - oversize a surface before trimming.
   - blendSurfaceFP_new.py + blend_curve.py `PointOnEdge(edge, continuity=n)` - blend surface between edge-on-face
     pairs with G1/G2+ and auto-scale: candidate for rolled edge / arch lip.
   - curves_to_surface.py `Gordon`, `CurvesOn2Rails`; gordonFP.py - curve-network surfaces.
   - TrimFace.py = the same extrude-and-slice approach we use (splitAPI.slice).
   - ZebraTool.py, continuity_check.py - G1/G2 checks.
2. FreeCAD ReverseEngineering module (installed, PCL built in; no fitBSpline in this build)
   - `approxSurface(Points, UDegree, VDegree, NbUPoles, NbVPoles, Smooth, Weight, Grad, Bend, Curv,
     Iterations, Correction, PatchFactor, UVDirs)` - smoothed LSQ with iterative parameter correction
     (not a height field). Cross-check our fitter; use where a patch wraps.
   - regionGrowingSegmentation, featureSegmentation, sampleConsensus (PCL).
3. tpaviot/pythonocc-demos examples/core_geometry_geomplate.py - GeomPlate_BuildPlateSurface +
   CurveConstraint(order 0/1/2) + PointConstraint + MakeApprox. FreeCAD equivalent: Surface workbench Filling.
4. lizOnly/nurbsfit (MIT, research, CUDA + C++ GoCoPP - do not run) - read uv_trimming.py: inlier points -> UV,
   Delaunay, drop long edges, border path = trim polygon in UV.
5. David-Feldt/breptile (MIT) - analytic surfaces only; breptile/brep.py sew/heal/unify recipe
   (BRepBuilderAPI_Sewing, ShapeFix, UnifySameDomain).
6. rainman110/occ_gordon (Apache-2.0) - Gordon surfaces, conda-forge + pythonocc only; CurvesWB covers it.
7. orbingol/NURBS-Python (MIT, maintenance) - grid-only fitting; nothing beyond what we have.

Nothing usable found: automotive Class-A / flange code; car body from sketches (True2Form, flow-complex
curve-net papers have no code). pymadcad.reverse fits primitives only.
