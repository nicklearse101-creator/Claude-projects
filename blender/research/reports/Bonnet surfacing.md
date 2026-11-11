# Fade the bonnet step by height, never width

Professional Class-A and reverse-engineering surfacers build a bonnet as a few **primary surfaces** first: a centre panel, the outer panels, and a front face. Then they join them with **secondary transitions** whose size varies along a guide curve: a variable soft-step blend, a nose roll and rolled edges. The edges come last, as flanges and returns built on the finished primaries. For our AE86 replica this means **three height fields over the plan**: a full-width symmetric centre panel C, which also carries the tongue, and two mirrored outer panels O. Every other part is built *from* them. That covers the step band, the nose roll, the 1 mm chamfers, the 7-15 mm returns, the underside cap and the washer nozzles. The measured Kunos mesh corrects the brief in several places. The step is **3.17 mm high at the rear, not 1.7 mm**, and it falls linearly to **zero at the notch corner (z ≈ 1720)**. In plan the two lines **diverge** toward the front, from x ±336.6 to ±359.4, instead of converging. The step's cross-section is a **straight 13 mm ramp** that looks soft only because Kunos averages its vertex normals. The nose ends in a **straight −52.5° face** and a 7 mm horizontal under-lip, so nothing on it is vertical. The returns are **13-15 mm deep, not 3-7 mm**, and the rear flange is **15 mm, not 30 mm**. Local FreeCAD 1.1.4 / OCCT 7.8.1 experiments settle the construction. A **quintic Hermite band** in a shared (arc length, across) plan map gave G2 joins to **1e-7 /mm curvature jump**. A single fitted height field could not hold the step (0.7-3° normal error even with 17-47k poles). `MakeFilling` missed tangency by 7.7°. The run-out rule is the key finding. **Make the step vanish by height with a triple zero, keep its width finite**, and carry the neighbours' knot lines into the band. The rest of this report gives the professional basis, the Kunos numbers, the FreeCAD route, and a 15-step build with numeric acceptance tests.

## Class-A builds the panels first and joins them with a sized blend

Every Class-A package documents the same order: primaries first, transitions second. Autodesk calls "the layout of the surface data" the key to Class A. It sets separate tolerances for main blends, smaller fillets and detail fillets, and it states that there are no absolute continuity rules ([Autodesk Alias](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)). The packages also provide variable transitions driven along a guide curve:

- **Alias Surface Fillet** takes any number of size locators along a 0-1 fillet guide curve. Its construction is by radius or by chord, and its section is G1 Circular, G2 or G3 Curvature, or G2 Curvature/Arc ([Alias 2024 Surface Fillet](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-05F7F4E3-8BCB-4423-A90D-0D4E8AA2FD9B.html)).
- **CATIA's Styling Fillet** varies its radius linearly between two end manipulators, and non-linearly once intermediate ones are added ([CATIA help](https://catiahelp.azurewebsites.net/English/GsdUserMap/fss-t-SurfaceCreation-StylingFillet.htm)).
- **ICEM Surf's Advanced Fillet** offers "Two Chord lengths, 3 Radii, True minimum radius" ([ICEM Surf Advanced Tools](https://www.3ds.com/fileadmin/PRODUCTS-SERVICES/CATIA/PDF/ICEM_Surf_415_Advanced_Tools_Spec_Sheet_K76.pdf)).

No public tutorial builds exactly a raised-centre bonnet step, so the construction for it is inferred from these tool families.

One point decides which family fits the step. The centre and outer panels are near-parallel, a few millimetres apart, so they have **no intersection for a radius fillet to roll on**. A chord-driven or boundary blend between two trim curves is the natural tool. Alias's "Build Theoretical" and CATIA's extrapolation option exist for this case. Panel-gap tools such as Alias Panel Gap and ICEM Tube/Gap build channels with walls, not an S-step ([Alias Panel Gap](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-BDB7551E-A500-41DF-8A81-19A1DA71FFAA.html)).

The fade-out has documented practice:

- **The size law varies along the curve.** It interpolates between locators, or varies linearly between two end values.
- **Continuity is relaxed only at the end points.** A Class-A Y-fillet tutorial gives the run-out surface "G2 at edge C … and G0 at A and B" ([Car Body Design, Y-Fillets](https://www.carbodydesign.com/archive/2010/06/y-fillet-class-a-surfaces-tutorial/3/)). It also splits the surface where G2 cannot be held, and accepts G1 on one edge because it "will fulfill the required level of quality and highlights".
- **Rhino SubD fades a feature by weight.** It ramps the crease weight down to 0 % at both ends ([Rhino SubD crease guide](https://www.rhino3d.com/docs/guides/subd/subd-crease/)).

The nose follows the same hierarchy. A BMW Z4 Class-A hood used "6 parent surfaces with 2 smaller surfaces at the front of the hood + the blends", 16 surfaces in all. It demanded continuity of "min G2 and mostly G3", with a G3 curvature comb as the acceptance picture ([LearningAlias](https://blog.learningalias.co.uk/2010/05/)). Autodesk's own G1/G2/G3 explanation makes the same point: G1 does not stop a highlight peak at a boundary, and G3 "is mostly required" in automotive Class-A ([Alias curvature continuity](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-9DD73E22-A5EF-4952-BB84-2CEE2109993C.htm)). Autodesk has dedicated "Hood Edge" and "Hood Edge Optimisation" lessons, but they returned HTTP 403, so their content is unknown ([Autodesk Alias automotive tutorials](https://www.autodesk.com/campaigns/alias-automotive-tutorials)).

Reverse-engineering practice mirrors this. Parts are segmented into large primaries and highly curved transitional features, "fillets or free-form steps". The primaries are fitted first, and the transitions are rebuilt as small surfaces joining them ([Cardiff RE algorithms](https://orca.cardiff.ac.uk/1811/1/REalgorithms.pdf)). Each programme sets its own scan tolerance. The one public case study used **±0.15 mm, with 97 % of points inside** ([2B Digital](https://2bdigital.sa/?p=23525)).

Stamping research shows that a soft bonnet step is physically real, not just a styling idea. "Subtle feature lines" with **5-20° direction changes need formable radii of 20, 8, 7 and 4 mm** ([Lee et al., IJAT 2021](https://pure.seoultech.ac.kr/en/publications/the-minimum-formable-radius-of-subtle-feature-lines-in-automotive/)).

## Kunos's step is a 3.2 mm straight ramp that dies at the tongue wall

The Kunos skin `GEO_hood_SUB1` is one welded, mirror-exact mesh of **1,026 vertices and 1,934 triangles**. Its 116 boundary edges are all cut edges, and no vertex is split. The measurements below come from our scripts in [D:/ClaudeData/tmp/research_bonnet/kunos/](file:///D:/ClaudeData/tmp/research_bonnet/kunos/).

**Band structure.** Each step line is a **7-row vertex band**:

- Rows 1-3 lie exactly on the centre surface and rows 5-7 exactly on the outer surface. The blend parameter is 0.00, 0.00, 0.00, 0.53, 1.00, 1.00, 1.00 at every station. The mid row sits exactly halfway.
- The cross-section is therefore **flat, then a straight ramp from row 3 to row 5, then flat**. Both creases are plain facet folds of 15-18°, so the band stays inside the main region at the pipeline's 20° crease split ([s10.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s10.py); [step_cross_sections.png](file:///D:/ClaudeData/tmp/research_bonnet/kunos/step_cross_sections.png)).
- The band has vertices only at stations about **100 mm apart**: z 1008, 1110, 1211, 1311, 1410, 1508, 1607, 1664, 1721. Between them it is a ruled strip of long thin triangles.

**Height law.** The height is a **plateau of 3.11-3.17 mm from z 1008 to 1211**. It then falls about **0.6 mm per 100 mm to zero at z ≈ 1720**, while the ramp narrows from about 13 mm to 6.2 mm:

| z (mid row) | 1008 | 1110 | 1211 | 1311 | 1410 | 1508 | 1607 | 1664 | 1721 |
|---|---|---|---|---|---|---|---|---|---|
| Mid-row x (mm) | 336.6 | 341.0 | 345.4 | 349.2 | 353.1 | 356.3 | 359.4 | 358.4 | ~361.5 |
| Step height h (mm) | 3.17 | 3.15 | 3.11 | 2.53 | 1.93 | 1.31 | 0.63 | 0.26 | ≈0 |
| Ramp width, row 3 → 5 (mm) | 12.6 | 13.0 | 13.4 | 13.1 | 12.7 | 11.1 | 9.5 | 6.2 | — |
| Ramp angle vs centre (°) | 15.0 | 14.4 | 13.8 | 11.6 | 9.3 | 7.1 | 4.1 | 2.8 | — |
| Slope break, centre − outer (°) | 1.83 | 1.79 | 1.86 | 1.40 | 1.28 | 0.72 | 0.55 | 0.50 | — |

**Plan curve.** The mid row follows **x(z) = −1.274e−5·z² + 0.07148·z + 277.48**, with a 0.12 mm maximum residual over z 1008-1607. The lines are closest at the rear and **diverge toward the front**. They end in the inner corner of the headlamp notch, where the notch chamfer turns on a plan radius of about **9.3 mm**, in line with the tongue side wall at x ≈ 358-362. The centre-panel boundary therefore *is* the tongue edge, continued rearward as a fading step ([s18.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s18.py); [s16.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s16.py)).

**Rear hook.** At the rear, below z ≈ 930, both creases turn outward through about **80°**. The upper crease, on the outside of the bend, has R = 51.3 mm; the lower has R = 37.0 mm. The tail then runs about 11° rearward of +x and tapers to a point at **(440.9, 859.6, 885.2)**:

| Tail station x (mm) | 364.6 | 384.6 | 403.6 | 440.9 (tip) |
|---|---|---|---|---|
| h (mm) | 2.85 | 1.63 | 0.5 | 0 |
| Ramp width (mm) | 5.4 | 4.3 | 3.1 | — |

On the tail the high side is the *rear* side: the centre level wraps round the rear end of the outer panel. The crease dihedral peaks at 24.8° in the corner ([s17.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s17.py); [zoom_hook_shaded.png](file:///D:/ClaudeData/tmp/research_bonnet/kunos/zoom_hook_shaded.png)).

**Two different panels.** The centre and outer are different surfaces, not a surface and its offset:

- **Slope break.** The outer panel slopes away 1.8° more steeply at the rear and 0.5° more at the front.
- **Crown.** Its transverse radius is about 6.8-7 m near the side edge. The centre is nearly flat: 10-35 m, and slightly concave next to the step ([s26.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s26.py)).
- **Fairness.** The outer panels are fair: column residuals have an RMS of 0.03-0.04 mm. The centre panel is **lumpy**. Whole transverse rows alternate by **±0.6 mm at the 100 mm row pitch**, with the same pattern at every x out to about 365. The exact pitch strongly suggests modelling noise, not design ([s25.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s25.py)).
- **Normals.** The stored normals are the angle-weighted average of the facet normals (median deviation 0.03°). Across the band, the shading therefore changes over rows 2 → 6, about **18 mm**, while the geometry ramps over only 13 mm ([s11.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s11.py); [s15.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s15.py)).

**Choosing the band section.** The research notes disagree here, and the Kunos numbers decide. The soft-step note was written against the brief's 1.7 → 1.2 mm with a 10-15 mm S-section. Kunos has twice the height, a fade to zero, and no S at all. A faithful copy would be a ruled strip between the row-3 and row-5 curves. With the pipeline's **exact** normals, though, its two folds would show as two hard highlight kinks that Kunos's averaged normals never show. This is the same lesson the roof taught: read the line from its rows, not its look, and build the soft look as a roll ([PANEL_FIT_TECHNIQUE.md](file:///D:/Claude/Claude-/blender/kn5-study/PANEL_FIT_TECHNIQUE.md)).

We recommend a **G2 quintic band whose width covers the shading spread**. The following is our own geometry, not a source:

- A quintic smoothstep of height h over width w has a maximum slope of **1.875 h/w** and a minimum radius of **w²/(5.77 h)**.
- At the rear, h = 3.17 mm and w = 20-22 mm give a **maximum slope of 15-16.5°**, matching Kunos's 15° ramp. The minimum radius is **22-26 mm**, inside the 25-50 mm the measurement note expected for a two-fillet G2 version.
- At this width, rows 1, 2, 6 and 7 stay within **0.03 mm** of Kunos and rows 3 and 5 within **about 0.2 mm**. The mid row is exact by symmetry.
- **Scale w(s) as Kunos's ramp width plus 5-9 mm**, falling to about 8-10 mm on the hook tail. That keeps the hook clear of the fold limit (the line radius must stay above w/2) by a factor of about 4.

## A quintic Hermite band was the only FreeCAD route that held G2

Three constructions were tested on Nik's PC. The test geometry was an exact synthetic bonnet with an 8 m × 2.5 m crown, a 914 mm hooked step line, and the brief's 1.7 → 1.2 mm step plus a fade-to-zero variant ([D:/ClaudeData/tmp/research_bonnet/](file:///D:/ClaudeData/tmp/research_bonnet/)).

**(a) Hermite band.** The band is parametrised by arc length s and an across parameter t, with a **shared plan map P(s,t) = A(s) + t·(B(s) − A(s))**. A and B are the ±w/2 plan offsets of the line. The height is a **quintic Hermite in t**, built from the value, first derivative and second derivative of C at A and of O at B. It is the roof's `rear_roll` recipe generalised to a curved line and a variable width ([blend.py](file:///D:/ClaudeData/tmp/research_bonnet/blend.py)).

- **It is exact for a structural reason.** A(s) is both the band's t = 0 curve and the trim curve on C. Matching the 2-jet of the height along that curve is therefore G2. The only remaining error is a 1-D least-squares fit in s, which converges like h⁶.
- **At 32 spans** it gave G0 0.001 µm, 0.00006° and a curvature jump of about 3.6e-7 /mm, against a blend curvature of 0.067 /mm ([a_run.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run.txt)).
- **The OCC side agrees.** OCC evaluation matched numpy to 7e-13 mm, and the three faces sewed into one valid shell at `sewShape(1e-4)` ([a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt)).
- **G1 is not enough.** A cubic (G1) Hermite in the same frame left the full 0.07-0.08 /mm curvature jump at both joins. In the zebra render its stripes hit the join lines bluntly, where the G2 stripes curve in tangentially ([zebra_a.png](file:///D:/ClaudeData/tmp/research_bonnet/zebra_a.png)).

**(b) One fitted height field.** It needed **46,644 poles** to reach 8 µm and still had 0.68° of normal error. At a more practical 5 mm knot spacing (17k poles) the error was 2.9°, with **ringing of up to 43 µm on the flat panels**. Fairing cut the ringing but blurred the step to 6.1° ([b_fit_final.txt](file:///D:/ClaudeData/tmp/research_bonnet/b_fit_final.txt)).

**(c) OCCT `MakeFilling`** kept G0 but missed tangency by a **median of 7.7°** at order G2, and did worse than at order G1 ([c_fill.txt](file:///D:/ClaudeData/tmp/research_bonnet/c_fill.txt)). The roof research explains why. FreeCAD's binding `static_cast`s order 2 to the C1 enum value, which the plate ignores, so "G2" silently runs as C0 ([FreeCAD MakeFilling binding](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/Part/App/BRepOffsetAPI_MakeFillingPyImp.cpp)).

**Untested alternatives.** OCCT's variable-radius fillet has circular sections and needs intersecting faces, which the step does not offer. CurvesWB's BlendSurface interpolates N sampled section blends into a Gordon surface, so it is exact only at the samples ([blend_curve.py](file:///D:/ClaudeData/FreeCAD/Mod/CurvesWB/freecad/Curves/blend_curve.py)). Neither was measured.

**The run-out rule** is the most transferable result:

- **Vanish by height.** Let C equal O plus a height H with a **triple zero** (H = H′ = H″ = 0) on the end cross-section, and carry C's knot lines into s as triple knots. The band then reproduces O exactly at the end: G0 below 0.001 µm, 0.00001°, curvature jump 4e-8 /mm, with no sliver face and no degenerate edge.
- **Carry the knots.** Leaving the knots out cost about 100× (2.9 µm, 0.037°).
- **Do not vanish by width.** Shrinking the width to zero gave curvature up to 13 /mm with a smooth width law. With the height held at 1.2 mm it gave a **near-vertical wall** (89° at 5 mm from the end).
- **Finite height needs a boundary.** A step that keeps its height must leave the panel at an edge ([a_run2.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run2.txt)).

For the AE86 this splits cleanly into two ends:

- **Rear tail tip.** The tip at (440.9, 885.2) sits about 80 mm forward of the rear edge, so it is a true mid-panel die-out. It needs the triple zero along a cross-section running from the tip back to the rear edge, with C and O identical beyond it. Kunos tapers both height and width to a point there; we keep the width finite.
- **Front end.** The front end lands on a boundary, the notch corner, where O itself ends at the lamp-bay wall. A residual slope break there (0.5° at z 1664) is hidden by the notch chamfer.

**Imposing the triple zero on fitted panels.** C and O are both height fields over the plan, so equality of value, gradient and Hessian along that cross-section is **linear in the poles**. The triple zero can therefore go into the least-squares fit as heavy rows, with no iteration. This is our inference; the experiment imposed it analytically through C = O + H.

**Pitfalls that are now measured:**

- **Spans.** Curvature-adapted knots in s (√κ density) reach the 32-uniform accuracy with 16 spans.
- **Meshing.** **Mefisto (`MaxLength 6`) makes slivers on 10-15 mm blends**: aspect ratio p95 168, facet normal error up to 54°. On the whole trimmed shell it crashed FreeCAD ("Not enough memory"). BRepMesh at 0.01 / 0.1 deflection gave aspect p95 3.0 in 0.3 s.
- **Face validity.** `Part.Face(surface, wire_of_3D_edges)` gives valid faces only after `validate()` ([a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt)).

The meshing result refines the pipeline's rule of "MeshPart MaxLength=6, not the deflection mesher". Keep Mefisto on the big panels, where irregular triangles tear the zebra stripes. Mesh the band, roll and strip faces with BRepMesh deflection, or with Mefisto at a MaxLength of w/6 or less.

## The nose is one swept section ending at −52.5°, not a vertical face

The brief's nose, a roll from −15° to −62° that ends in a vertical face, and the edge note's reading of about 53° plus an 8 mm down-facing strip, both resolve in Kunos's columns:

- **Constant section.** The roll is the same section swept across x. Columns at x = 0, 89, 178, 263 and 348 repeat the slope sequence to within ±0.5°.
- **Front edge.** In plan the front edge bows by only 6.3 mm over ±348 (plan R ≈ 9.6 m). Its z is 1907.3 at x = 0 and 1901.0 at x = 348.
- **Slope sequence.** The roll starts at z ≈ 1770 at −14.6°. It tightens through vertex circumradii of about 500 → 390 → 113 → 126 → **72 mm**, then ends in a **straight 40 mm face at −52.5°** (z 1882 → 1907).
- **Tip.** Next come a 0.9 mm facet at −62.4°, a **1 mm chamfer** (r11, 58° to the skin), and a **7.1-7.4 mm horizontal under-lip** (r4, facing down). The lip's open edge rests 0.2 mm above `GEO_details`.

Sources: [s21.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s21.py), [s22.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s22.py), [nose_roll_slopes.png](file:///D:/ClaudeData/tmp/research_bonnet/kunos/nose_roll_slopes.png). The measured roll is progressive, with its curvature concentrated in z 1835-1883. That is the behaviour of a G2/G3 curvature blend, not of a constant-radius G1 fillet, which would kink the highlight at both tangent lines ([Alias fillet sections](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-36EB38AB-0635-4436-8273-E9A74F06907F.htm)).

The pipeline already has the right tool: the roof's exact G2 roll between two height fields across a curve. Here those are **C (top) and a −52.5° front face** that follows the bowed plan front edge. A −52.5° face is still a height field over the plan, and the band width a + b is constant, so the roll is exact in the x basis. Its position is set by two parameters, the roll start and the roll end.

Our own estimate fixes the start and end. A quintic smoothstep has a peak curvature 1.875× its mean. A roll from about **z 1800 (−17.3°) to z 1882** therefore gives a minimum radius of about **75-85 mm**, close to Kunos's 72 mm. Kunos's gentle −14.6 → −17.3° over z 1770-1800 then belongs to C's own forward acceleration, which is the Class-A habit of "accelerating" a primary toward its blend. Fit a and b to the 10 roll rows × 5 columns of **vertices**, not facets. The tight rows' facets sag 0.27-0.66 mm inside the true roll (L²/8R).

**Tongue corners.** The tongue side walls (r7/r8) face ±x at x 358-365:

- **Top edge.** It tapers inward 5 mm, from x 362.6 at z 1733 to 357.4 at z 1900.
- **Wall height.** It falls from 14.2 mm to 7.3 mm toward the nose.
- **Joins.** The wall meets the skin through a 1 mm notch chamfer (r12/r13, 36° to the skin). The roll section runs unchanged out to that chamfer.
- **Plan corner.** The notch's inner corner, where the lamp-bay rear wall r5/r6 meets the tongue wall, is an L-turn of R ≈ 9.3 mm.
- **Corner fills.** Where chamfers and returns meet, Kunos fills the corners with 1-6-triangle patches smaller than 3 mm (r14-r27) ([s14.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s14.py)).

No public source covers a pop-up-lamp tongue corner. The general CAD advice is a setback or corner patch where three blends meet, judged with zebra stripes ([Rhino FilletEdge](https://docs.mcneel.com/rhino/9/help/en-us/commands/filletedge.htm)). With 1 mm chamfers, a G0 or G1 corner fill is enough. These corners are far smaller than the strips around them.

The pipeline's chain-strip sanity check drops chains that turn more than 20° per 20 mm, and the notch chain turns 90° in about 15 mm. Rulings skew by roughly width × turn. That is a problem for strips lying in the turning plane, but not for the 14 mm **vertical walls**, whose top and bottom rails share one plan curve, nor for the 1 mm chamfer (about 1.5 mm of skew). We therefore recommend either a vertical-wall and narrow-chamfer exemption, or a split into a lamp-bay run, a corner piece and a tongue run (our inference).

## Every edge is a 1 mm chamfer on a 7-15 mm return, and the underside is a dark cap

**Real bonnet edges.** A real bonnet edge is the outer skin hemmed 180° over the inner panel:

- **Hem radius.** About ½ × inner thickness + outer thickness, which is **1.1-1.2 mm** for 0.7-0.8 mm steel ([US7241073B2](https://patents.google.com/patent/US7241073)).
- **Hem width.** **8 mm** on straight runs, 6 mm on convex curves and 4 mm at sharp corners ([FormingWorld, BAIC hemming](https://formingworld.com/baic-digital-hemming-workflow/)).
- **Gaps.** OEM bonnet-to-wing gaps are 3-4 mm: **3.6 ± 1.5 mm** with −0.75 mm flush on a 2014 Mustang ([Ford workshop manual](https://reichwein.it/manuals/Mustang_2014/Workshop_Manual_Wiring_Diagrams/Resources/Service_Manual/seb1z003.htm)), and 3 ± 1 mm on a Saab 9-5 ([Saab WIS](https://saabwisonline.com/9-5-9650/2011/8-body/body/adjustment-replacement/hood-adjustment)).

**Kunos edges.** Kunos's edges translate the hem into game geometry, with deeper returns. Every edge runs skin → about 1 mm chamfer → return. Notably, the chamfer width matches the hem's outside radius (our observation):

| Edge | Kunos measured | Brief / notes said | Use |
|---|---|---|---|
| Side chamfer r9/r10 | 1.05-1.17 mm, 29° to the skin | "R 1.5-2 mm round" (edge note) | Kunos chamfer |
| Side return r2/r3 | **13.1-14.2 mm** vertical, 82° to the skin | 3-7 mm (brief) | Kunos |
| Rear flange r1 | **15.0 mm** at 97.7°, no chamfer | 30 mm (brief) | Kunos; the "30 mm" matches the 30-38 mm clearance to the cowl, not a flange |
| Nose chamfer + lip r11/r4 | 0.96-1.18 mm + 7.1-7.4 mm horizontal | "vertical face" | Kunos |
| Lamp-bay wall r5/r6 | 14.05-14.15 mm | — | Kunos |
| Tongue wall r7/r8 | 14.2 → 7.3 mm | ~15-17 mm (edge note) | Kunos table |
| Notch chamfer r12/r13 | ≈0.95 mm, plan corner R 9.3 mm | — | Kunos |
| Side gap to the wing | **3.0 mm (rear) → 0.7-1.0 mm (front)**; wing top 0.1-2.7 mm below | 1.5-2 mm wall-to-wall (edge note) | Section table |
| Rear edge | Free: 30-38 mm to the cowl, 54-67 mm to the glass | — | Unconstrained |

Sources: [s14.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s14.py), [s22.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s22.py), [s28.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s28.py), [s29.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s29.py).

The deeper returns hide the see-through gap at low camera angles. The dark shut line comes from **baked AO in the paint maps**, not from a modelled groove. The repo's 112-car study found that "panel gaps are mostly painted, not modelled" ([KN5_STUDY.md](file:///D:/Claude/Claude-/blender/kn5-study/KN5_STUDY.md)). Kunos's welded, averaged normals also make the outermost 65 mm skin column shade as a soft roll of up to 15-48°. Our exact normals will look crisper there. That is the same deliberate choice the pipeline already made on the rear quarter.

**Underside.** The inner panel should be built the way Kunos and its pipeline build it: **as a cap, not a pressed frame**. The AC pipeline treats `MOTORHOOD` as a damage part pivoted on a null, and requires: "Make sure that you have closed the mesh in the interior … black texture or something very dark." It also says: "carefully cap the holes" ([AC_Pipeline_PUB_Rev2.0.pdf, p.43](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)). Kunos's `GEO_hood_SUB2` (`EXT_underside`, ksPerPixel, normals facing down) is built like this:

- **Size.** 200 vertices and 290 triangles.
- **Perimeter.** Its **108 perimeter vertices coincide with the skin's cut edges**, at the bottom of the returns, the flange and the lip.
- **Rim loop.** A rim loop runs exactly **10.0 mm inside the skin** along its normal, about 15 mm lower vertically.
- **Interior.** Only four interior vertices, **19-30 mm under the skin** ([s31.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s31.py)).

AC has no bonnet-open animation by default, so a modelled inner frame pays only if open-bonnet views are wanted later.

**Washer nozzles.** `GEO_hood_SUB0` (`EXT_details`, ksPerPixelReflection) is two **18.6 × 13.1 × 19.2 mm** nozzles centred at (±235.5, 864.2, 966.2), about 100 mm forward of the rear edge on the centre panel. They sit within 0.13 mm of the skin and are parented under `MOTORHOOD` ([s30.py](file:///D:/ClaudeData/tmp/research_bonnet/kunos/s30.py)).

**Triangle counts.** The edge note's bonnet budget table is **three times too low in absolute terms**. Its script divides an index array that is already reshaped to (n, 3) by 3 again ([hoodbudget.py](file:///D:/ClaudeData/tmp/bonnet_research/scripts/hoodbudget.py); [kn5full.py](file:///D:/Claude/Claude-/blender/kn5-study/kn5full.py)). Its percentage shares stand.

The true AE86 bonnet is about **2,650 triangles**: skin 1,932, underside 288, nozzles about 213 each. These counts agree with the measurement note's 1,934 and 290, and with the Euler count for a welded disc (2V − B − 2). The AC exterior LOD A budget is 125,000 triangles ([AC pipeline, pp.6-8](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)). A bonnet of 3-6k display triangles with exact normals is affordable, as long as the density goes into the band, the roll and the edges.

## A fifteen-step build with numeric acceptance tests

The order follows the master/slave rule: fair primaries first, transitions built from their jets, strips on built edges, caps last. Plan coordinates follow `roof_build.py` (s = z, t = x, h = y). Numbers marked as sourced come from the sections above; the rest are our starting values.

| # | Step | How (existing tool or extension) | Acceptance test |
|---|---|---|---|
| 1 | Extract the regions: r0, r1-r13, corner patches; walk the 7 band rows at each station; classify rows by blend parameter | Existing crease split at 20°; character-line sections; `rows.py` | Rows 1-3 / 5-7 have t = 0 / 1 within 0.05; mirror pairs within 0.1 mm |
| 2 | **O** (right; left mirrored): height field over the plan, domain overshoot 20-40 mm | `panel_fit` least squares on vertices only: rows 5-7 and beyond, the side-edge column, notch-wall tops; blocked 5-fold CV | Vertex RMS ≤ 0.05 mm, max ≤ 0.15 mm (Kunos outer is fair to 0.03-0.04) |
| 3 | **C**: full width, mirror-paired poles; the tongue and nose top up to z ≈ 1800 | Vertices of rows 1-3, the centre and the tongue; third-derivative fairing with 4-5 spans along z, to drop the ±0.6 mm washboard; heavy linear G2 jet rows (value, ∇, ∇²) equal to O along the tail-end cross-section, from the tip (440.9, 885.2) to the rear edge, with C ≡ O beyond | Signed mean residual ≤ 0.05 mm per column; residual pattern is the washboard (RMS ≈ 0.4-0.45, max ≤ 0.7); isophotes smooth; tail seam G0 ≤ 0.01 mm, G1 ≤ 0.05°, Δκ ≤ 5 % |
| 4 | Step line: fair mid-curve through the station mid-rows, the hook crease points and the tail tip | Fewest controls (about 1 per 12 sections); curvature-adapted knots | Within 0.2 mm of the quadratic x(z) over z 1008-1607; hook creases within 0.5 mm; hook mid-radius ≈ 44 mm |
| 5 | Height check H(s) = C − O along the line (an output of steps 2-3, not an input) | Evaluate | Within 0.15 mm of 3.17/3.15/3.11/2.53/1.93/1.31/0.63/0.26/0; tail 2.85/1.63/0.5/0 within 0.2 mm; no kink at z 1211 |
| 6 | Width law w(s) = Kunos ramp + 5-9 mm (≈20-22 mm at the rear, ≥ 8 mm at the tip); offsets A, B | B-spline in s sharing knots with the line | Minimum plan Jacobian > 0 (no fold); line radius > 2w everywhere |
| 7 | **Step band**: quintic Hermite in t from the jets of C at A and O at B; C/O knot lines crossing A/B carried as triple knots; 16-32 adapted spans | Generalise the `roof_build` roll (`blend.py` recipe); trim C and O on A and B as 3D edges | Sampler (41-101 points per edge): G0 ≤ 0.01 mm, G1 ≤ 0.05°, Δκ ≤ 1 % of the band κ (1e-7 /mm reached in the tests); max slope vs C within ±2° of Kunos's 15.0 → 2.8°; Kunos rows 1/2/6/7 ≤ 0.05 mm, rows 3/4/5 ≤ 0.25 mm; tail end G2 to O |
| 8 | **Front face**: −52.5° surface through the column vertices, z 1882-1907, following the bowed plan edge | Small height-field fit, plan R ≈ 9.6 m | Slope −52.5 ± 1°; front edge within 0.3 mm of z 1907.3 → 1901.0 |
| 9 | **Nose roll** C ↔ front face across the plan curve; fit start and end (≈ z 1800 / 1882) to the roll vertices | `roof_build` exact G2 roll | Roll vertices within 0.3 mm; slope per row within 1°; R_min 70-110 mm; both seams G2 as in step 7 |
| 10 | Outline trim curves: side edge (x 628.4 → 630.4 → 627.6), rear edge (z 863.2/853.4/821.0/736.8), notch L-chain with the R 9.3 corner, tapered tongue edge, nose edge | Fit to polylines resampled every 5 mm; `Part.Face(srf, Part.Wire(sortEdges(3D edges)))` + `validate()`; PF_MASTER snapping | Each curve within 0.001 mm of its surface; all faces `isValid()`; outline within 0.3 mm of Kunos |
| 11 | Edge strips on the built edges: chamfers first (side, nose, notch chain), then returns and walls, the rear flange as a fold flange, the nose lip | `strip_build.py`, with a vertical-wall / narrow-chamfer exemption or a corner split for the notch | Widths within 0.3 mm of the table above; median deviation ≤ 0.1 mm; joins 0.00-0.01 mm; winding agrees with exact normals |
| 12 | Corner fills r14-r27 | G0 fill, or `MakeFilling` order 1 checked by our sampler (never `G1Error()`) | No holes; G1 ≤ 0.5° where the patch is larger than 3 mm |
| 13 | Sew; clearance check against GEO_body, the headlamps and GEO_details | `sewShape(0.01)` | One shell; free edges are only the return bottoms; side gap 0.7-3.0 mm, never negative; notch to lamp units ≥ 0.1 mm; no interpenetration |
| 14 | **Underside cap** (rim strip ruled from the return bottoms to a 10 mm inward offset, plus a coarse lid 20-30 mm under the skin) and **nozzles** (separate small solids on C at ±235.5, z 966.2) | Ruled strips; a low-pole lid surface; dark `EXT_underside`; nozzles in a details material under `MOTORHOOD` | Bonnet closed (0 free edges after welding); lid never above the skin; nozzles within 0.2 mm of the skin, size within 1 mm |
| 15 | Mesh, normals, judge | Mefisto MaxLength 6 on C and O; BRepMesh 0.01/0.1 (or MaxLength ≤ w/6) on the band, roll and strips; exact normals | One manifold component; aspect p95 ≤ 5; vertex distance as the main score; facet distance judged against predicted sag (0.1-0.4 mm on panels, 0.3-0.7 mm in the roll); zebra and isophotes beside Kunos, including a view along the bonnet from the windscreen across the hook, with nested loops at the tail tip and no stripe kinks at the band edges |

## Conclusion

The bonnet reverses the roof's lesson in one respect. On the roof, Kunos's geometry was right and its facets were the trap. On the bonnet, Kunos's step *geometry* is a crude ruled ramp, and the design intent lives in its averaged normals. A faithful replica of that ramp would look worse with exact normals than Kunos looks with fake ones. The professional answer is therefore not to copy the vertices more closely. It is to rebuild the transition as the Class-A tools would: a G2 band sized to Kunos's shading spread (about 20 mm), whose height law and plan come from the mesh. The vertices then become acceptance data, kept to within 0.25 mm. The other non-obvious result is topological. The step has two different kinds of end. The front end dies onto a boundary, the tongue wall, and can be loose. The rear tail dies mid-panel and must be a triple-zero seam where the centre and outer panels become the same surface. Because both panels are height fields over the plan, that seam is a set of linear rows in the existing least-squares fitter. No new solver is needed.

Four open risks remain:

- **Synthetic tests only.** The Hermite band was proven on an exact synthetic geometry, not on fitted Kunos panels. The tail seam's jet rows and the ±0.6 mm centre-panel washboard are untested together.
- **Unexplained rear zone.** The centre panel's 2.5° slope change at z ≈ 1017 is either design or noise. It may force a rear band behind the hook.
- **Notch chain.** The 90° turn at the notch corner needs either a strip-builder exemption or a split.
- **Paywalled lessons.** Autodesk's Hood Edge lessons sit behind a 403 and probably hold the real studio patch layout for a nose. The two-panel-plus-band layout here is inferred from tool documentation and from the measured mesh, not copied from a published bonnet build.
