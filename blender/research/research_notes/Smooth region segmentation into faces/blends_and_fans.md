# Blends and fans: fitting primary faces, shoulder blends (G1/G2) and multi-face corner regions, runnable headless in FreeCAD 1.1 / OCC 7.8

Scope: the AE86 C-pillar. A flat top face about 45 mm wide, a shoulder bend of about 75 deg over about 30 mm, then the side face, over 1.1 m. At the foot it fans into the deck and the rear quarter.

Some findings come from scripted tests I ran on this PC (FreeCAD 1.1.4, OCC 7.8.1, headless FreeCADCmd with FREECAD_USER_HOME/TEMP set to D:). The scripts are in `D:\ClaudeData\tmp\research_cpillar\scripts\` (probe.py, exp1.py to exp4.py). They are cited as "local test" with the script path.

Several primary sources could not be fetched: the Cardiff ORCA PDFs of Kós/Martin/Várady and Benkő/Martin/Várady return 403/HTML, the FreeCAD wiki is behind Anubis bot protection, and the Semantic Scholar API returned 429. Statements about those papers' internals are therefore limited to what the citation records and abstracts say.

## Q1. Blend recognition and (variable) radius estimation from mesh data, including vanishing blends

### Takeaway
The standard reverse-engineering (RE) method is "segment, fit primaries, then recover the blend from the primaries plus the points in the blend band". Kós/Martin/Várady give methods for constant-radius rolling-ball blends. They left variable-radius blends and vertex blends as further work, which Kós addressed separately in 2000. Commercial tools such as Geomagic Design X do the same in user-facing form: auto-segment the mesh, then "estimate radius from mesh" as averaged values along the edge. For our coarse game mesh, a per-station estimate is the robust approach. Fit the two flats in each cross-section, measure the turn angle θ(s) and the bend width, and convert these to r(s). A vanishing shoulder then shows up as r(s)→0 or θ(s)→0.

### Cited Findings
- Kós, Martin and Várady, "Methods to recover constant radius rolling ball blends in reverse engineering", Computer Aided Geometric Design 17 (2000) 127–160. It compares methods for recovering constant-radius rolling-ball blends from measured data. The authors state that variable-radius rolling-ball blends and vertex blends are the subject of further research. — [SZTAKI eprints record](https://eprints.sztaki.hu/2459/); [search abstract, dblp](https://dblp.org/rec/journals/cagd/KosMV99)
- A follow-up exists: G. Kós, "Recovering variable radius rolling ball blends in reverse engineering", CIRP Design Seminar 2000. Only the citation record was reachable, not the method text. — [SZTAKI eprints record](https://eprints.sztaki.hu/2322/)
- Benkő, Martin and Várady, "Algorithms for Reverse Engineering Boundary Representation Models", covers the overall RE pipeline that produces CAD-ready B-rep models from point data. The full text (Cardiff ORCA) returned 403 to automated fetches. — [Cardiff ORCA PDF](https://orca.cardiff.ac.uk/1811/1/REalgorithms.pdf)
- Background from the literature on variable-radius rolling-ball (VRRB) blends: the spine curve of a VRRB blend can be obtained as the intersection of the two primary surfaces' offset surfaces, with varying offset distances. — [search result summary of VRRB literature](https://ir.lib.nycu.edu.tw/bitstream/11536/824/1/A1997YA42800002.pdf) (the snippet's exact attribution is unverified)
- The blend-recognition patent literature notes that many modelers support variable-radius blends whose cross-sectional radius varies along the edge. — [US patent 6760038, "Method for recognizing blends in solid models"](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6760038)
- Geomagic Design X workflow, per a vendor tutorial:
  - The mesh is first segmented with Auto Segment.
  - The fillet tool's "Estimate Radius from Mesh" lets you click a filleted mesh edge and returns an averaged radius, which can be edited.
  - For variable fillets, you match the CAD radius values to the averaged values along the mesh, or type them in. — [CIMquest, "Reverse Engineering Variable Fillets"](https://cimquest-inc.com/?p=13124); [Design X 2014 user guide (PDF)](https://www.engineering.pitt.edu/contentassets/52314f399aba40fa86709314a569641c/geomagicdesignx2014userguide.pdf)
- Alias exposes the same idea from the modelling side: a variable fillet surface whose radius is controlled at points along its length. — [Autodesk Alias help, "Control the radius along the length of a variable fillet surface"](https://download.autodesk.com/us/alias/2013help/files/GUID-076464B6-D27B-4179-9D43-D7E3E9D10258.htm)

### Inferences
- **Per-station radius estimator, suited to a coarse mesh.** Slice the mesh with planes perpendicular to the pillar spine every 25–50 mm. In each slice:
  1. Fit a line or low-order curve to the points of the top flat and of the side flat, excluding a guard band around the bend.
  2. Compute the turn angle θ and the virtual sharp corner X, where the two lines intersect.
  3. For a circular blend tangent to both lines, the setback from X to each tangent point is d = r·tan(θ/2), and the arc length is s = r·θ.
  4. Estimate r either from the measured setback (distance from X to where the mesh leaves each fitted line by more than a tolerance) or from the arc length.
  5. Alternatively, least-squares fit a circle tangent to both lines to the bend-band points. That is a one-parameter fit in r, which is well posed even with only 2–4 facets across the bend.
- Worked example for the stated numbers: θ = 75° (1.309 rad) and arc length about 30 mm give r ≈ 30/1.309 ≈ 23 mm, and setback d ≈ 23·tan(37.5°) ≈ 17.6 mm on each side.
- A game mesh with few facets across the bend cannot tell circular from conic or G2 profiles. Fit the one-parameter r(s) and choose the profile type (circular or G2) by design intent, not from the data.
- **Vanishing shoulder.** Watch θ(s) and r(s) along the spine. The shoulder "dies out" where θ(s)→0, because the flats become coplanar, or where the setback falls below the facet size. Two ways to model it:
  - Model r(s) going to 0 at a station s0, a vanishing blend.
  - Stop the blend at a setback station before s0 and treat the rest as part of the fan patch (Q4).
- Smooth r(s) with a low-order B-spline or polynomial in s, about 4–6 control values over 1.1 m. Per-station noise on a coarse mesh will otherwise ripple the blend, which shows up immediately in zebra.

### Gaps
- I could not read the full texts of Kós/Martin/Várady 2000 or Kós CIRP 2000 (403), so their exact spine and radius estimators and accuracy figures are not reported here.
- I found no official documentation of CATIA DSE/GSD "fillet from mesh" or any vanishing-blend recognition algorithm.

## Q2. Building the shoulder blend in OCC/FreeCAD (rolling-ball fillet, sweeps, G1/G2 section blends) between two separate B-spline faces

### Takeaway
There are two routes that work headless in FreeCAD 1.1, both tested here.

**(A) OCC rolling-ball fillet** on a sewn shell:
1. Make the top and side primary faces meet along a real shared edge (extend, intersect, trim, sew).
2. Call `shell.makeFillet(r1, r2, [edge])`.

This gives a G1 rolling-ball blend with a linearly varying radius, even down to r2 = 0. Measured G1 error was 1e-4 deg.

**(B) A custom section blend:**
1. Choose trim lines on each primary face.
2. At N stations, build a `Surface.BlendPoint`/`Surface.BlendCurve` (built into FreeCAD 1.1's Surface module) that matches the face derivatives to G1 or G2.
3. Loft the sections.

This gives exactly G2 at the boundaries (zero measured curvature jump), and you can choose any width or radius law. It does not need the faces to intersect at all. Route B is the closest analogue of the beltline "true blend from the skin". It is also the route to use if a G2 shoulder is wanted.

### Cited Findings
- **`BRepFilletAPI_MakeFillet` basics.**
  - "A fillet is a smooth face replacing a sharp edge."
  - The edge must be shared by two faces.
  - The fillet propagates automatically along edges in smooth (tangent) continuity with the edge.
  - Constant radius: `Add(r, edge)`.
  - Variable radius: `Add(ParAndRad, edge)` with an array of (parameter, radius) `gp_Pnt2d` pairs, e.g. (0,10), (50,20), (130,60) on a 200-long edge.
  - Section shape is set with `SetFilletShape(ChFi3d_Rational | ChFi3d_QuasiAngular | ChFi3d_Polynomial)`.
  - — [OCCT Modeling Algorithms user guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)
- The same guide warns that when a Law function is used as a fillet's evolution law, "it is important that the function is always positive". — [OCCT Modeling Algorithms user guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)
- OCC users report very mixed results with the `ParAndRad` variable-radius overload. The OCC tracker also has issues where fillets silently fail when the radius exceeds the available geometry, e.g. issue 31209: radius 0.5 failed while 0.2 worked. — [OCC tracker 31209](https://tracker.dev.opencascade.org/view.php?id=31209); [OCC tracker 30208](https://tracker.dev.opencascade.org/view.php?id=30208)
- **What FreeCAD exposes.** FreeCAD 1.1.4 / OCC 7.8.1 Python offers only `Shape.makeFillet(radius, edgeList)` and `Shape.makeFillet(radius1, radius2, edgeList)`, where the second form is a linear radius variation. The `ParAndRad` and law overloads are not exposed. The Part module also exposes:
  - `Part.BRepOffsetAPI.MakeFilling`
  - `Part.BRepOffsetAPI.MakePipeShell`, with `setAuxiliarySpine`, `setBiNormalMode`, `setSpineSupport`, `setTrihedronMode`, `setTransitionMode`, `setForceApproxC1`, `setMaxDegree`, `setMaxSegments`, `setTolerance`, `simulate`
  - `Part.GeomPlate.BuildPlateSurface`, `CurveConstraint`, `PointConstraint`
  - `Part.makeFilledFace`, `Part.makeFilledSurface(curves, tol)`, `Part.makeSweepSurface(path, profile, [tol])`
  - `Surface.BlendPoint` and `Surface.BlendCurve`

  No `LocalAnalysis` binding is exposed. — local test `D:\ClaudeData\tmp\research_cpillar\scripts\probe.py`, `exp1.py`
- **Local test of route A.** Two separate interpolated B-spline faces were built: a top of 1100 × 45 mm and a side of 60 mm at 75 deg, with a 3 mm sinusoidal sag along the length. They were combined with `Part.makeShell([top, side])` and `.sewShape()`, giving one shared edge. Then `makeFillet(15,15,[e])`, `(15,2)`, `(15,0.01)` and `(15,0.0)` all succeeded with `isValid()==True` and three faces each. The r = 15→0 case produced a fillet face of half the area, i.e. a linear taper to zero. The maximum normal angle across both fillet boundary edges was ≤ 0.0001 deg, 25 samples per edge. — local test `D:\ClaudeData\tmp\research_cpillar\scripts\exp1.py`, `exp2.py`
- **The OCC fillet is G1 only.** Rolling-ball fillets are G1 by construction: a circular cross-section tangent to both faces. That is why Class-A tools offer separate curvature-continuous blends. In Alias, "Surface Fillet" builds blends between primary surfaces and "Freeform Blend" adds control over continuity. — [Autodesk Alias, Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm); [Novedge, Alias capabilities](https://novedge.com/blogs/design-news/mastering-automotive-design-5-essential-autodesk-alias-capabilities-for-elite-surface-modeling-and-visualization)
- **CurvesWB `BlendSurface`** (tomate44, `freecad/Curves/blend_curve.py`). Its building blocks:
  - `PointOnEdge` (continuity 0–5) builds the derivative vectors from `getD0`/`getDN`.
  - `BlendCurve(point1, point2)` interpolates a Bézier through both endpoint derivative stacks. `scale1`/`scale2` are the tension parameters, relative to the chord.
  - `minimize_curvature()` and `minimize_angular_variation()` use `scipy.optimize.minimize` (Nelder–Mead) over the two scales.
  - `EdgeOnFace` builds cross curves on the face from 2D offset curves.

  `BlendSurface(edge1, face1, edge2, face2)` builds a ruled surface between the two edges as rails and samples BlendCurves along them (`perform(20)`). It then interpolates them (`CurvesToSurface`) and combines the result with ruled and U-linear surfaces through a Gordon construction. — [CurvesWB source, blend_curve.py](https://raw.githubusercontent.com/tomate44/CurvesWB/master/freecad/Curves/blend_curve.py)
- CurvesWB is an add-on, installed via the Addon Manager. Its README calls it experimental. It also offers a parametric blend curve between two edges up to G2, and a Gordon surface over a curve network: at least 2 guides × 2 profiles, with each curve touching all curves of the other family. — [FreeCAD wiki, Curves Workbench](https://wiki.freecad.org/Curves_Workbench/en); [Curves GordonSurface](https://wiki.freecad.org/Curves_GordonSurface); [CurvesWB GitHub](https://github.com/easyw/CurvesWB). CurvesWB is not installed in `D:\FreeCAD\Mod`, per the local check.
- **Local test of route B.** The same two faces were trimmed 15 mm from the sharp edge on each side, with 23 stations along 1100 mm. Each station used `Surface.BlendPoint([P, D1, D2])`, `Surface.BlendCurve(b1, b2)`, `setSize(0, s, True)`, `setSize(1, s, True)` and `compute()`, and the sections were lofted with `Part.makeLoft([...], False, False)`.

  | Blend | Section curve | Surface | Boundary gap | Max normal angle | Max curvature jump | Section curvature profile |
  |---|---|---|---|---|---|---|
  | G1, size 0.5 | degree-3 Bézier | 3×4 | 0.0000 mm | 0.0000 deg | 0.45 1/mm | 0.45 at ends, about 0.015 mid |
  | G2, size 0.5 | degree-5 Bézier | 5×4, 6×17 poles | 0 | 0 | 0.000000 1/mm | 0 → 0.168 → 0.016 |
  | G2, size 0.7 | degree-5 Bézier | 5×4 | 0 | 0 | 0 | peak 0.097 |
  | G2, size 1.0 | degree-5 Bézier | 5×4 | 0 | 0 | 0 | 0 → 0.042–0.060 → 0, a roughly constant-radius core of about 17–24 mm |

  Gotchas found:
  - **Derivative direction.** D1 at the start point must point from face 1 toward the blend, i.e. −dS/dv when v runs away from the edge. D1 at the end point must point into face 2, i.e. +dS/dv along the curve's direction of travel. With both pointing "toward the edge", sections kinked, with curvature spikes above 2 1/mm.
  - **Tension.** Small relative sizes (0.35–0.5) concentrate curvature near the ends. Size ≈ 1.0 of the chord gave the most even curvature.

  — local test `D:\ClaudeData\tmp\research_cpillar\scripts\exp3.py`
- **`GeomFill_ConstrainedFilling`** fills a contour of 3 or 4 boundaries, optionally with tangency (`GeomFill_BoundWithSurf`), into a B-spline. **`GeomFill_Pipe`** sweeps a section along a path; it supports a circular section of constant radius, a constant section, or a section evolving between two curves. The `FillingStyle` choices are:
  - `Stretch` (flattest)
  - `Coons`
  - `Curved` (roundest)

  — [OCCT Modeling Algorithms user guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)
- **Other offerings.** Rhino's variable fillet in Grasshopper is a separate rolling-ball approach. ICEM Surf offers fillets and flanges along a guide curve. — [McNeel forum, variable fillet](https://discourse.mcneel.com/t/variable-fillet-in-gh/93036); [ICEM Surf Advanced Tools spec](https://www.3ds.com/fileadmin/PRODUCTS-SERVICES/CATIA/PDF/ICEM_Surf_415_Advanced_Tools_Spec_Sheet_K76.pdf)

### Inferences
- **Recipe B, recommended for the C-pillar shoulder.**
  1. Fit the top and side height-field faces only to points outside the bend band, as now.
  2. Choose trim curves on each face as offset lines at distance d(s) from the virtual sharp intersection. Take d(s) = r(s)·tan(θ(s)/2) from Q1, smoothed.
  3. At N ≈ 25–45 stations (one every 25–45 mm), take P and D1 (and D2 for G2) from the face surfaces at the trim points in the cross direction, using `Surface.getDN(u,v,0,1)` and `getDN(u,v,0,2)`.
  4. Build `Surface.BlendCurve` with relative sizes ≈ 0.8–1.0, or optimise the size per station for minimum curvature variation, as CurvesWB's `minimize_curvature` does.
  5. Loft with `Part.makeLoft(wires, solid=False, ruled=False)`, or interpolate with `BSplineSurface.buildFromNSections`.
  6. Use the loft's boundary iso-curves as the new trim edges of the primaries, so the boundaries coincide exactly.

  Two notes. Cross-derivatives must be taken perpendicular to the trim curve, not along the faces' v-isos, if those are not perpendicular. And all sections must have the same degree, which is automatic: degree 3 for G1, degree 5 for G2.
- **Recipe A, a quick G1 option.** Extend both primaries past the shoulder, intersect them, trim them, sew them, then `makeFillet(r_start, r_end, [edge])`. FreeCAD only gives a linear r law. For a non-linear law, split the edge into pieces with linear r each, or use the OCC `ParAndRad` overload through OCP/pythonocc. Neither OCP nor pythonocc is available in this FreeCAD build.
- **Vanishing shoulder with route B.** Let d(s) and the section sizes go to 0 at s0. The sections then degenerate to a point and the loft fails, so stop the section blend at a setback station s1 < s0 and close the region s1..s0 with the fan patch (Q4). Route A's r→0 test shows OCC tolerates a taper to 0 radius on a simple edge. That is an observation from one test, and it contradicts the docs' "law must be positive" caution, so it is not a guarantee.

### Gaps
- I did not test `MakePipeShell` with an auxiliary-spine or law section, `Part.makeSweepSurface`, or the OCC ChFi3d walking ("BRepBlend"/"BlendFunc") classes directly. They are not exposed in FreeCAD Python.
- The FreeCAD wiki page for CurvesWB "BlendSurf2" was blocked by bot protection, so its exact property names (continuity/scale) were not confirmed from the wiki. Only the library source (above) was read.

## Q3. Order of operations: primaries, extension, intersection, blend, trim; recovering primaries under the blend

### Takeaway
Professional practice, in Class-A and in RE alike, is:
1. Primary (main) surfaces, built low-degree and larger than needed, to their theoretical intersections.
2. Secondary surfaces.
3. Blends and fillets, then flanges and split lines.
4. Trim and sew last.
5. Evaluate with curvature combs and highlight (zebra) lines.

Avoiding early or over-trimming keeps edits possible. In our pipeline, the primaries must therefore be fitted and extended under the shoulder before the blend is built. With a mesh that only covers the flats, the extension comes from the primary's own low-degree fit, extrapolated a few tens of mm. It does not come from the bend points.

### Cited Findings
- Alias treats G0/G1/G2 as the Class-A baseline, with G3 as the higher goal. Building the main shapes first is the primary design activity. Surface Fillet and Freeform Blend build controlled blends between primaries. Round is used for detail fillets on sharp-edged models. Tolerances are set separately for main blends, smaller fillets and detail fillets. — [Autodesk Alias, Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)
- A practitioner recommendation: build low-degree primary surfaces to theoretical intersections, use isoparametric curves for secondary surfaces, refine primary curves before loft/sweep/blend, and avoid over-trimming early. — [Novedge, Rhino Class-A surfacing workflow](https://novedge.com/blogs/design-news/rhino-3d-tip-class-a-surfacing-workflow-in-rhino); [Autodesk Fusion blog, Class A tips](https://www.autodesk.com/products/fusion-360/blog/our-top-5-surfacing-tips-and-tricks-for-class-a-geometry/)
- A 2013 Autodesk University ICEM-to-Alias deck notes that Bézier patches give smooth single-span patches without internal continuity breaks, which is valued in Class-A. It also notes that curvature plots reveal G3 breaks at edit points. — [AU 2013 MA3477-P, Simon Alford](https://static.au-uw2-stg.autodesk.com/MA3477-P_presentation_3477_au_2013_class_presentation_MA3277-P_SimonAlford.pdf)
- RE literature (Kós/Martin/Várady) recovers blends from the already-reconstructed primary surfaces. Variable-radius and vertex blends were treated as a later step. — [SZTAKI eprints 2459](https://eprints.sztaki.hu/2459/)
- OCC's fillet requires a real edge shared by two faces, so the primaries must already intersect and be sewn. — [OCCT Modeling Algorithms user guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)

### Inferences
- **Pipeline order for the C-pillar:**
  1. Segment: top flat, side flat, bend band, deck, rear quarter.
  2. Fit each primary height field to its own points only, excluding the bend band, over a domain extended 20–40 mm beyond its data edge into the band. Keep the fit low-degree (degree 3, few spans) and add a smoothing or regularisation term, so the extrapolation is controlled.
  3. Check the extension: in each cross-section, the extended primaries should meet near the "virtual sharp" corner implied by the bend points. The virtual corner is where tangents from both flats meet. This is the same check as the line intersection in Q1.
  4. Route A: intersect with `top.common()`/`section()` or `Part.BSplineSurface.intersect`, split, sew, fillet. Route B: no intersection needed; compute trim offset curves and build the section blend.
  5. Trim the primaries back to the blend boundary curves, using the loft's boundary isos as edges.
  6. Build the fan (Q4) against the trimmed boundaries.
  7. Check continuity (Q5).
- Fitting the primaries over the bend band would pull them toward the rounded profile and bias both the angle and the radius. Excluding a guard band of about 1 setback (≈ 15–18 mm here) on each side of the bend is the key data-side step.

### Gaps
- I found no authoritative step-by-step published workflow, such as an official Alias or ICEM manual chapter, that spells out "extend, intersect, blend, trim". The sequence above comes from multiple practitioner and vendor sources. No source was found on how commercial RE tools extrapolate primaries under blends.

## Q4. Fan / vertex-blend regions where three or more faces or a dying blend meet

### Takeaway
The literature's answer is the setback vertex blend (Várady & Rockwood). The edge blends are stopped at setback distances from the corner, and the resulting n-sided hole is filled with an n-sided patch that is G1 to the surrounding ribbons: transfinite or Gregory patches, or I-patches.

In OCC/FreeCAD the practical tool is `BRepOffsetAPI.MakeFilling` (BRepFill_Filling / GeomPlate) with G1 edge constraints taken from the adjacent faces, plus optional point constraints from the mesh. In a local test of a 4-sided hole in a known smooth surface, it achieved:

| Constraint, degree | G1 error | Max deviation from the true surface |
|---|---|---|
| G1, degree 3 | 1.4e-5 rad (≈ 0.0008 deg) | 0.012 mm |
| C0 | — | 0.08 mm |
| Degree 5 | — | about 1.2–1.7 mm (much worse) |

The resulting surface is heavy: 8×8 degree, 16×16 to 23×23 poles. "G2" edge constraints produced results identical to C0 in FreeCAD 1.1.4.

ICEM Surf's "Corner Blend" is the commercial equivalent: one patch between three intersecting surfaces, with trimming and continuity adjustment.

### Cited Findings
- Setback vertex blends merge edge blends by broadening them at certain distances from the vertex. Várady & Rockwood 1997 build them with a control-frame construction using a repeated-chamfering strategy. — [Geometric construction for setback vertex blending (index record)](https://acnpsearch.tweb-dev.unibo.it/singlejournalindex/5129645)
- Salvi et al. (CAD 43 (2011) 1330–1340) define transfinite surface interpolation over irregular n-sided domains from tangential ribbons. Most such schemes guarantee only G1, and some generalise to G2. — [Salvi et al. (PDF copy)](https://kevinpolisano.github.io/pdf-storage/M2-MSIAM/Modelisation_surfacique/MS_article.pdf)
- For ribbon-based multi-sided patches with cross-derivative constraints, a setback vertex blend can misbehave with a convex polygonal domain or excessive ribbon magnitudes. — [Constrained modeling of multi-sided patches](https://www.bohrium.com/paper-details/constrained-modeling-of-multi-sided-patches/872791067315929088-2576)
- Sipos, Várady and Salvi (2022) approximate triangular-mesh regions with implicit multi-sided I-patches. Ribbons (Liming surfaces or I-lofts) are fitted to the corner points and normals estimated from the mesh. The interior is fitted by Nelder–Mead on the weights with a weight-ratio limit ω = 5. G1 to the ribbons holds by construction.

  Reported accuracy (% of bounding-box diagonal):
  - Concept car, 28 patches: average 0.016 %, max 0.12 %.
  - Shoe last: average 0.069 %, max 0.35 %.

  These are implicit patches, not B-splines, so they are not directly usable in OCC. — [arXiv 2204.11070](https://ar5iv.labs.arxiv.org/html/2204.11070); [Sipos SMI 2020 slides](https://3dgeo.iit.bme.hu/~sipos/presentations/smi2020/2020%20SMI%20-%20Sipos.pdf)
- ICEM Surf Advanced Tools "Corner Blend" creates a single patch between three intersecting surfaces and a support, with trimming and continuity adjustment in the same operation. — [ICEM Surf 415 Advanced Tools spec sheet](https://www.3ds.com/fileadmin/PRODUCTS-SERVICES/CATIA/PDF/ICEM_Surf_415_Advanced_Tools_Spec_Sheet_K76.pdf)
- **`BRepFill_Filling` (= `BRepOffsetAPI_MakeFilling`) parameters and defaults:**
  - `Degree=3, NbPtsOnCur=15, NbIter=2, Anisotropie=false, Tol2d=1e-5, Tol3d=1e-4, TolAng=0.01, TolCurv=0.1, MaxDeg=8, MaxSegments=9`.
  - The recommended Degree is "i+2 where i is the maximum order of the constraints".
  - Tol3d is the maximum distance between the surface and the constraints.
  - TolAng is the maximum angle between the surface normal and the constraints.
  - TolCurv is the maximum curvature difference.
  - `Add(edge, order, IsBound)` takes tangency from the edge's first face. `Add(edge, supportFace, order, IsBound)` takes it from the given face. `Add(supportFace, order)` is a free constraint. `Add(gp_Pnt)` and `Add(U, V, face, order)` are point constraints.
  - `LoadInitSurface(face)` requires an initial surface with orthogonal dS/du and dS/dv, "If this condition breaks, distortions of resulting surface are possible".
  - `G0Error()`, `G1Error()` and `G2Error()` exist, overall or per constraint.

  — [OCCT reference, BRepFill_Filling](https://occt3d.com/dev/doc/refman/html/class_b_rep_fill___filling.html); [BRepOffsetAPI_MakeFilling.hxx](https://git.rbts.co/OpenCascade/occt/raw/branch/step_losing_attrs/src/BRepOffsetAPI/BRepOffsetAPI_MakeFilling.hxx); [BRepFill_CurveConstraint (7.8)](https://dev.opencascade.org/doc/occt-7.8.0/refman/html/classBRepFill__CurveConstraint.html)
- **GeomPlate directly.** Use `GeomPlate_BuildPlateSurface(3,15,2)` with `BRepFill_CurveConstraint(curve, order)` and `GeomPlate_PointConstraint(P, order)`, then `Perform()`. Approximate to a B-spline with `GeomPlate_MakeApprox(plate, Tol=1e-4, MaxSeg=9, MaxDegree=8, dmax=max(1e-4, 10*G0Error()), CritOrder=0)`. — [OCCT Modeling Algorithms user guide](https://occt3d.com/dev/doc/overview/html/occt_user_guides__modeling_algos.html)
- **FreeCAD binding gotchas** (local test):
  - `Part.BRepOffsetAPI.MakeFilling()` rejected the 10 positional constructor arguments. Construct it empty, then call `setResolParam(deg, nbPts, nbIter, False)`, `setConstrParam(tol2d, tol3d, tolAng, tolCurv)` and `setApproxParam(maxDeg, maxSeg)`.
  - `add(edge, face, order, True)` takes order 0/1/2 (the error text: "0 -> C0, 1 -> G1, 2 -> G2").

  — local test `D:\ClaudeData\tmp\research_cpillar\scripts\exp3.py`, `exp4.py`
- **Local hole-fill quality test.** A 300 × 300 mm smooth B-spline (40 mm sine bump plus twist) was cut into 3×3 patches with `BSplineSurface.segment`. The 30 %-wide centre patch was removed and the hole refilled with MakeFilling, using its 4 edges with their support faces.

  | Order | Degree, NbPtsOnCur, NbIter | G0Error | G1Error | Max deviation | Result |
  |---|---|---|---|---|---|
  | C0 | 3, 15, 2 | 8.9e-5 | — | 0.083 mm | degree 8×8, 16×16 poles |
  | G1 | 3, 15, 2 | 3.2e-5 | 1.37e-5 rad | 0.012 mm | |
  | G1 | 3, 30, 4 | 6.8e-6 | 2.0e-6 rad | 0.012 mm | 23×23 poles |
  | G1 | 5, 30, 4 | 3.5e-2 | 7.1e-4 rad | 1.18 mm | degree 5 is worse |
  | "G2" (order 2) | — | — | — | — | identical to C0 in every setting: G1Error and G2Error reported 0, deviation 0.083 mm |

  The "G2" edge constraint was effectively ignored in this build. — local test `D:\ClaudeData\tmp\research_cpillar\scripts\exp3.py`

### Inferences
- **Recipe for the C-pillar foot fan:**
  1. Build top, side, shoulder blend (to setback station s1), deck primary and rear-quarter primary as trimmed faces. Leave an n-sided hole, typically 3–5 sides, around where the shoulder dies.
  2. Choose the hole boundary so that each side lies on exactly one neighbouring face: blend end section, top-face edge, side-face edge, deck edge, quarter edge.
  3. Fill with `MakeFilling`: `setResolParam(3, 20–30, 3–4, False)`, `setConstrParam(1e-5, 0.01–0.05 mm, 0.01 rad or less, 0.1)`, `setApproxParam(8, 9)`. Use `add(edge, face, 1, True)` (G1) for each boundary edge.
  4. Optionally add `add(gp_Pnt)` point constraints, i.e. `mf.add(Vector)`, from the mesh vertices inside the hole, so the fan follows the game mesh. Use few points (10–30) and keep them away from the boundary, or they fight the G1 constraints.
  5. Check `G1Error()` (radians) and the deviation from the mesh.
- **Setback distance.** Stop the shoulder blend about 1–2 blend widths before the point where the shoulder disappears in the mesh, so the fan has room to absorb the transition.
- The fan result is a high-degree (8×8) dense patch. That is fine for rendering and AC export, but not "Class-A light". If a lighter patch is wanted, re-approximate with `BSplineSurface.approximate` on points sampled from it, then re-check G1.
- Do not rely on FreeCAD's order = 2 (G2) edge constraint in MakeFilling. If G2 at the fan boundaries matters, a Gordon or loft of `Surface.BlendCurve` G2 sections (route B of Q2) is the controllable alternative. A 3- or 4-sided fan can also be split into 4-sided Gordon patches, using CurvesWB Gordon if it is installed.
- `GeomFill_ConstrainedFilling` (3–4 boundaries, Coons/Curved/Stretch) is lighter. It is only reachable through OCP or pythonocc, not FreeCAD's Part module, and has fewer quality controls.

### Gaps
- I did not test a true 3-sided or 5-sided hole, or point constraints inside MakeFilling. Quality for those configurations on the actual C-pillar foot is untested.
- I found no source describing an RE tool's automatic handling of a blend that vanishes into a corner (as opposed to a setback vertex blend).
- I did not confirm whether `Part.makeFilledFace` exposes support faces or G1 constraints. Its docstring only says "Create a face out of a list of edges".

## Q5. Checking continuity numerically in OCC/FreeCAD (G1 angle, G2 curvature, zebra)

### Takeaway
OCC's `LocalAnalysis_SurfaceContinuity` is the reference point-pair checker. Its defaults are: EpsNul, EpsC0, EpsC1, EpsC2 and EpsG1 = 0.001, Percent = 0.01 (curvature variation for G2), and Maxlen = 10000. EpsG1 is in radians. FreeCAD's Python does not expose it. A short numpy-style check gives the same information: sample boundary points, project to both faces, compare normals (G1) and normal curvatures in the cross direction (G2). `MakeFilling.G1Error()` gives the fill's own figure.

### Cited Findings
- **`LocalAnalysis_SurfaceContinuity`** checks C0, C1, C2, G1 and G2 between two points on two surfaces.
  - Constructor defaults: `EpsNul=0.001, EpsC0=0.001, EpsC1=0.001, EpsC2=0.001, EpsG1=0.001, Percent=0.01, Maxlen=10000`.
  - IsG1 is true when the C0 value < EpsC0 and the G1 angle < EpsG1.
  - G2 uses the maximum normal-curvature gap, with "Percent" as the allowed curvature variation.
  - Accessors include `IsG1`, `IsG2`, `G1Angle`, `C0Value` and `G2CurvatureGap` (7.8).

  — [OCCT 7.8 reference, LocalAnalysis_SurfaceContinuity](https://dev.opencascade.org/doc/occt-7.8.0/refman/html/classLocalAnalysis__SurfaceContinuity.html); [OCE CDL source](https://diyhpl.us/cgit/oce/tree/src/LocalAnalysis/LocalAnalysis_SurfaceContinuity.cdl); [pythonocc docs](https://cdn.jsdelivr.net/gh/tpaviot/pythonocc-core@804f7f3/doc/apidoc/0.18.1/OCC.LocalAnalysis.html)
- In GeomPlate, the G1 criterion for a curve constraint is "the greatest angle allowed between the constraint and the target surface". — [OCCT reference, BRepFill_CurveConstraint](https://dev.opencascade.org/doc/refman/html/class_b_rep_fill___curve_constraint.html)
- **What FreeCAD 1.1.4 offers for building such a checker:** `Part.BSplineSurface.normal(u,v)`, `.parameter(pnt)`, `.getDN(u,v,nu,nv)`, `.curvature(u,v,type)`, `.curvatureDirections(u,v)`, `Face.curvatureAt`, `Face.normalAt`, `Face.derivative1At`/`derivative2At`, `BSplineSurface.Continuity`, and `MakeFilling.G0Error()/G1Error()/G2Error()`. There is no LocalAnalysis binding. — local test `D:\ClaudeData\tmp\research_cpillar\scripts\probe.py`
- **Checker used in the local tests (works headless):**
  - G1: for k boundary samples, `p = edge.valueAt(t)`; `(ua,va) = Sa.parameter(p)`; `(ub,vb) = Sb.parameter(p)`; angle = acos(|na·nb|).
  - G2: normal curvature in the cross direction t from the first and second fundamental forms, built from `getDN` (E, F, G and L, M, N), as κn = (L a² + 2M ab + N b²)/(E a² + 2F ab + G b²) with t = a·Su + b·Sv. Compare |κa − κb|.
  - Measured results: OCC fillet 1e-4 deg; G1 section blend 0 deg / Δκ 0.45 1/mm; G2 section blend 0 deg / Δκ 0.

  — local test `D:\ClaudeData\tmp\research_cpillar\scripts\exp2.py`, `exp3.py`
- Class-A evaluation is done with curvature combs and highlight lines. Curvature plots reveal G3 breaks at edit points. — [AU 2013 ICEM-to-Alias deck](https://static.au-uw2-stg.autodesk.com/MA3477-P_presentation_3477_au_2013_class_presentation_MA3277-P_SimonAlford.pdf); [Autodesk Alias, Class A](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)

### Inferences
- **Suggested acceptance thresholds for this project** (my inference, aligned with the OCC defaults):
  - G0 ≤ 0.01–0.05 mm.
  - G1 ≤ 0.1 deg (≈ 0.0017 rad; OCC's EpsG1 default 0.001 rad ≈ 0.057 deg is stricter).
  - G2: relative curvature gap ≤ 1–5 %, or an absolute Δκ ≤ 0.001 1/mm on near-flat faces, where relative measures blow up.
- **Zebra headless.** Compute, per mesh vertex of a fine tessellation (`face.tessellate(0.05)`), stripe = floor(k · angle(n, L)) mod 2 for a fixed light direction L. Then render with the existing quick ortho renderer (see the 3D texel preview technique notes). G1 breaks show as stripe kinks and G2 breaks as stripe width jumps.

### Gaps
- I did not verify the exact G2 pass formula inside `LocalAnalysis_SurfaceContinuity.cxx`. The docs only say "Percent" is the allowed curvature variation.
