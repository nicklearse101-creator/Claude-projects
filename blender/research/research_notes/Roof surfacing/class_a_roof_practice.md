# Class-A roof surfacing practice (Alias / ICEM Surf / CATIA / Rhino) and how the roof joins its neighbours

Context: Kunos AE86 hatchback rebuild as fitted B-spline faces in FreeCAD/OCCT. The roof meets the drip-rail strip (~8 mm, already a ruled strip), the A-pillar tops, the C-pillar tops (station-profile sweep), the windscreen header and the hatch header.

Researched 2026-11-11. Public sources on *roof-specific* Class-A practice are thin: most real content sits in paid courses (LearningAlias, Autodesk's Alias Automotive Class-A series, Lynda/LinkedIn NX/CATIA Class-A courses) or in proprietary OEM standards. Autodesk itself says those OEM tolerance standards "are proprietary and must be learned within the industry". The cited findings below are what could be verified. The inferences are labelled as such.

## 1. Patch layout for a roof: single span vs multi-patch, degree/span counts, crown and camber, oversize-then-trim

### Takeaway
Professional practice favours as few, as simple, single-span (Bezier) patches as possible. Typical degrees are 5 (Rhino's own guide recommends degree 2 or 5 for single-span curves), with experienced users capping at about degree 7. A roof is a primary surface: build it first, from curves checked against curvature combs, and give it enough crown "acceleration" toward the cant rail that the side transition does not have to "perform miracles". No public source gives a roof-specific patch count. One big primary patch, built oversized and trimmed, is the implied norm.

### Cited Findings
- Autodesk lists Bezier surfaces among the Class-A "Golden Rules", for internal continuity and smoothness. It says "The layout of the surface data is the key to Class A modeling": the flow of CVs, hulls and patches across main surfaces and features is the primary consideration — [Autodesk Alias: Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)
- "Single-span NURBS are exactly equivalent to Bezier Math." ICEM Surf works in *order* and Alias in *degree*: degree = order − 1. An ICEM "Patch" is a single-span surface and an ICEM "Curve Segment" is a single-span curve — [Autodesk Alias: NURBS Single-Span](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-4D7B7604-C5C3-4B94-ABDC-741DA54B38E9.htm)
- Bezier patches have no internal continuity breaks, "which is essential for Class A quality surfacing". This comes via the Autodesk ICEM-to-Alias transition material as summarised in search results — [ICEM Transition Guide 2011 (Scribd copy)](https://www.scribd.com/document/212963947/Ice-m-Transition-Guide-2011); [Autodesk NURBS Single-Span](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-4D7B7604-C5C3-4B94-ABDC-741DA54B38E9.htm)
- Rhino's industrial-design guide gives these rules:
  - "Always try to use InterpCrv to draw single-span curves with Degree set to 2 or 5." Degree 2 = 3 CPs (1 free), degree 5 = 6 CPs (4 free). Use degree 3 only when a single-span curve must be G2 at one end and G0 at the other.
  - Build single-span surfaces whenever possible.
  - The primary → secondary → tertiary (blend/fillet) hierarchy is a tree, and the quality of the primaries determines everything downstream.
  - Do not use Rebuild on surfaces: it "will almost always destroy your surface's CP structure".
  - Do not use NetworkSrf/Patch. Do not build 3-sided surfaces, because singular corners make filleting and matching very hard.
  - Never imply G2 across a mirror plane. Two CPs perpendicular to the plane give G1 only.
  - Use EdgeSrf for full manual CP control on four sides, and Sweep2 only when the rails have the same degree and CP count.
  - Build large fillets before small ones.
  — [Rhino: Surface modeling tips](https://www.rhino3d.com/docs/guides/industrial-design/surface-modeling-tips/)
- In single-span math, a single-span curve or surface has (degree + 1) control points per direction, so degree 5 = 6 CPs — [McNeel forum search summary / Rhino guide](https://www.rhino3d.com/docs/guides/industrial-design/surface-modeling-tips/)
- Practitioner opinion on degree (forum, not an authority): "the trick is not to go past degree 7 as far as i know, 5 is even better". G3 does not need every surface at degree ≥7, and transitions can be degree 5 or even 3 — Sabino, [McNeel: Class A surfaces in Rhino, p2](https://discourse.mcneel.com/t/class-a-surfaces-in-rhino/5583?page=2)
- Matching all four edges of a patch to G3 already uses 4 rows of CPs per side, so 8 CPs per direction. Adding one mid-span control gives degree 8 by default. This shows why G3-all-round patches push the degree up — Phil_Cook, [McNeel: Class A surfaces in Rhino, p2](https://discourse.mcneel.com/t/class-a-surfaces-in-rhino/5583?page=2)
- Single-span by itself is not Class A: "A single span surface (in both directions) on itself does not mean Class-A, but it is a part of it." Trimming a Bezier surface with a Bezier curve does not give a single-span edge — [McNeel threads via search summary](https://discourse.mcneel.com/t/single-span-surface-and-curves/33260)
- Rhino users note that big blends such as the car roof, where multiple directions are involved, often need a blend surface early in the model — [McNeel forum, via search summary](https://discourse.mcneel.com/t/heavy-blend-srf/134770.md)
- LearningAlias (roof module, preview text):
  - Start with the roof and model "every curve paying attention to the pencil line, while checking the curvature comb".
  - The roof must be *accelerated* toward the cant rail ("surface crowning"), because the cant rail is a transition surface and the roof must supply the lead-in: "Don't expect a blend to perform miracles."
  - Too little acceleration at the roof edge gives a rough roof-to-cant-rail transition. With adequate acceleration, the roof and rear screen form a suitable transition for the cant rail "and even the C-pillar".
  — [LearningAlias roof module](https://learningalias.co.uk/showmod.php?m=128&t=65)
- Autodesk's Alias Automotive Class-A tutorial series has a dedicated roof sequence:
  - "Roof Scan: Patch Planning" (1.4, ~1:46 video)
  - "Roof Scan: Fitting Primary Surfaces to a Mesh" (1.5, ~25 min, PDF + data)
  - two options for the blend surfaces: fit to the mesh, or build to "theoreticals"
  Only the titles and outline were reachable; the page returned HTTP 403 to fetch — [Alias Automotive tutorials](https://www.autodesk.com/campaigns/alias-automotive-tutorials) (contents via search summary)
- Sabino (forum) advises shaping adjacent primaries so they "lead naturally into the blend", which makes the blend easy — [McNeel: Class A surfaces in Rhino, p2](https://discourse.mcneel.com/t/class-a-surfaces-in-rhino/5583?page=2)

### Inferences
- For the AE86 roof:
  - Build ONE primary roof patch, single span, degree 5 in both directions (6×6 CPs), or degree 5×6 at most. Fit it to the Kunos mesh with crown (lateral Y-Z section) and camber (longitudinal X-Z section) set by the CP rows.
  - Extend it past the drip-rail line, past both headers and over the pillar tops, then trim.
  - This matches the "primary first, quality flows down the tree" rule and the LearningAlias crowning advice. The roof should already carry its edge curvature roll-off toward the gutter, so the drip strip is not a corrective blend.
- A degree 5 single span has 4 interior rows per direction, enough for a symmetric crown plus a slight front/rear asymmetry in camber. If a 6×6 net cannot hold the Kunos shape to tolerance, the next step in pro practice is to raise the degree (to 6–7), not to add spans. Add spans only as a last resort.
- AE86 symmetry: make the roof as a full-width patch symmetric about Y=0 by construction (mirror CP pairs), not as a half-patch mirrored. The Rhino rule says a half-patch joined across the centreline is only G1. A full-width single span avoids a centreline seam entirely, so keep the roof un-split at the centreline.

### Gaps
- No public source gives a specific roof patch count, roof degree, or roof CP net. The Autodesk "Roof Scan: Patch Planning" lesson and the LearningAlias roof module hold this but are video or paywalled.
- No source quantified crown or camber values (e.g. roof crown height per metre of width) for cars of this era.

## 2. Extending the roof under/beyond drip rails, pillars and headers, then trimming; primary vs secondary vs blend

### Takeaway
The roof is a primary, which by convention means a large untrimmed base built oversize. Pillars, headers and gutters either are primaries themselves, or secondary/transitional surfaces between primaries. Corners where three transitions meet a primary are tertiary corner patches (ball corner / corner blend). Exact overshoot distances are not published.

### Cited Findings
- Rhino's guide treats surfaces as a tree: primary, then secondary, then tertiary (blends and fillets). It also says to avoid building from trimmed edges; RebuildEdges repairs them when they block matching. For matching a surface to a trimmed edge, it recommends MatchSrf with "Match edges by closest points" + "Preserve isocurve direction" — [Rhino surface modeling tips](https://www.rhino3d.com/docs/guides/industrial-design/surface-modeling-tips/)
- Alias Ball Corner workflow, in which a corner is built *after* the fillets and *on* a primary:
  1. Select the three intersecting transitional surfaces (the fillets), then the primary surface.
  2. The tool trims the inputs and builds the corner.
  3. A "4th Edge Ratio" shrinks or expands the corner's top edge.
  4. Continuity is chosen as tangent or curvature, with Continuity Check on.
  5. Explicit Control sets the corner's degree and spans in U and V.
  6. The corner rebuilds when the input fillets change.
  Corner Blend is the newer, preferred tool. Since Alias 2025.1 it also blends between four intersecting surfaces — [Alias: Create a ball corner surface between fillets](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-NURBS-Modeling/files/Create-geometry/Build-corner-tertiary-surfaces/GUID-E2E78F2A-62FD-4B98-AE8C-E0F126430A9D.html); [Alias 2025.1 Corner Blend](https://help.autodesk.com/cloudhelp/2025/ENU/Alias-WhatsNew/files/wn-whatsnewinalias2025/wn-alias-corner-blend-2025-1.html)
- Autodesk's Class-A tutorial list includes "Ball Corner" (Square and BallCorner tools), "Five Corner Blend" and "Four and Three Corner Blends". NX and CATIA Class-A courses use the same structure: frame curves → corner blend surfaces → "top blends" → "tertiary blend surfaces" — [Alias Automotive tutorials](https://www.autodesk.com/campaigns/alias-automotive-tutorials); [LinkedIn/Lynda NX Class A: tertiary blends](https://www.lynda.com/NX-tutorials/Tertiary-blend-surfaces/2823259/2267000-4.html); [CATIA V5 Class A: corner blends frame curves](https://www.lynda.com/CATIA-tutorials/Corner-blends-frame-curves/2825343/2938494-4.html) (titles only; content paywalled)
- In CATIA V5, a blend-corner option lets you pick the vertex and set a SETBACK distance, which handles unequal fillet radii meeting at a corner (forum, anecdotal) — [Eng-Tips: ball corners](https://eng-tips.com/threads/ball-corners.166262)
- On the production side (student projects, illustrative only, not OEM):
  - The roof outer panel is extracted from the styling surface. The ditch (gutter) area, front roof rail (windscreen header) and rear roof rail (hatch header) are built to master sections supplied by styling.
  - Ditch areas are spot-welded to the pillars, with the welding kept off the visible upper surface.
  - The ditch tool opening angle is 3°, the minimum draft is 7°, and the header rails are 0.75 mm sheet.
  — [Skill-Lync roof challenge 175](https://skill-lync.com/student-projects/roof-challenge-175); [Skill-Lync roof challenge 81](https://courses.skill-lync.com/student-projects/roof-challenge-81)

### Inferences
- Mapping to the AE86 (C = cited structure applied, I = inference):
  - PRIMARY: roof panel (one patch); windscreen glass surface; hatch glass surface; C-pillar main surface; A-pillar main surface; body side.
  - SECONDARY/TRANSITIONAL: the drip-rail/gutter strip (on a 1980s car the drip rail is a formed lip; in surfacing terms it is a narrow feature on the roof edge, so the existing 8 mm ruled strip is effectively a secondary); the header-to-glass radii (front/rear); the C-pillar shoulder blend (already built G2).
  - TERTIARY: the corners where roof + drip strip + pillar meet, and where roof + header radius + drip strip meet. These are the "ball corner / corner blend" situations: three transitional edges around one primary.
- Overshoot: build the roof with its parameter rectangle extended past every trim line, typically by at least one blend width plus margin. For the AE86, roughly 20–40 mm past the drip line and past each header seam is a sensible starting value (my estimate, not sourced). Trim with curves projected or intersected on it. Keep the untrimmed underlying surface for all matching, because Rhino/Alias guidance says not to build from trimmed edges.
- In OCCT terms: keep `Geom_BSplineSurface` untrimmed, make faces with wires of `Geom2d` pcurves, and match neighbours to the *untrimmed* roof (evaluate derivatives on the base surface along the trim pcurve). This avoids the "trimmed Bezier edge is not single-span" problem.

### Gaps
- No source states the usual overshoot (mm or % of span) for roof primaries.
- No public source describes exactly how OEMs surface the roof gutter or drip rail. No Class-A roof-ditch or drip-moulding method was found; only sheet-metal student projects.

## 3. Joins: drip rail/gutter, A-pillar top, C-pillar top, windscreen header, hatch header; continuity and tolerances

### Takeaway
Industry baselines: G0, G1 and G2 everywhere visible; G3 across main seams where long highlights run. Numeric tolerances that are actually sourced:
- position gap 0.01–0.001 mm for production (Alias)
- tangent break < 0.1° "normally not visible" (Alias)
- Class B example 0.001 mm / 0.2° (Wikipedia's proposed standard)
- Alias curvature deviation metric (R1−R2)/(R1+R2), with the 0.1 default called "way too high"
Feature lines (drip rail, header-to-glass edges) are intentional breaks, so they are judged as G0 edges plus clean radii, not as G2 joins.

### Cited Findings
- Class-A aims "to build to tight tolerances for G0, G1 and G2 continuity". G3 across patch boundaries is used for "perfect" highlights. It is achieved by direct CV modelling with live continuity evaluation, Align, Freeform/Profile Blend, Surface Fillet, Symmetric Fillet and Blend Curves. OEM standards set separate tolerances for A/B/C surfaces, for exterior versus interior, for main blends versus detail fillets, and for split lines, flanges and panel gaps — [Autodesk: Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)
- Alias construction tolerances:
  - For prototyping or production, "a typical Maximum Gap Distance would be between 0.01mm and 0.001mm".
  - "A tangent break of less than 0.1 degrees will normally not be visible on most products."
  - Curvature Deviation = (Radius1 − Radius2) / (Radius1 + Radius2).
  - Very tight tolerances are set temporarily for detailed Continuity Check feedback "when building to Class A standards".
  - Companies usually define their own tolerances.
  — [Autodesk Alias: Continuity 2: Construction Tolerances](https://help.autodesk.com/cloudhelp/2016/ENU/Alias-Tutorials/files/GUID-2FCE06EB-8EF7-4507-92F7-82A73A0DF378.htm)
- An Autodesk tutorial (as summarised in search results) says the old StudioTools default curvature tolerance of 0.1 is absolute, not an angle, and "way too high compared with most CAD packages" — [Autodesk Alias 2014: Curvature Continuity in Surface Modeling](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-9DD73E22-A5EF-4952-BB84-2CEE2109993C.htm) (summary; numbers not re-verified on the page)
- In Alias Construction Options, the General CAD preset is "compatible with most CAD packages" and preset values are locked. The documentation does not print the numbers; they are read in the UI or exported as .json — [Alias 2026 Construction Options](https://help.autodesk.com/cloudhelp/2026/ENU/Alias-Reference/files/Preferences-menu/GUID-4C5924EF-1B5F-4029-ACC5-BD9812D32D18.html)
- Wikipedia's "proposed standard":
  - Class A = G0/G1/G2/G3.
  - Class B = G0/G1, with example tolerances G0 0.001 mm, G1 0.2° max, and undulation Cu 0.003 mm⁻¹.
  - Strictly, Class A only requires curvature and tangency alignment, but many interpret it as G2 or G3.
  — [Wikipedia: Class A surface](https://en.wikipedia.org/wiki/Class_A_surface)
- Forum claims (not standards): Class A position no more than 0.01 mm; neighbouring patches must have coincident curvature at least every 100 mm of contour — [GrabCAD: definition of class A surface](https://grabcad.com/questions/what-is-definition-of-class-a-surface)
- Class-A exteriors target G2 at visible seams, and sometimes G3 across long highlights. Matching curvature combs across a join is a quick G2 check, done before surfaces are built — [Novedge: Surface interrogation history](https://novedge.com/blogs/design-news/design-software-history-surface-interrogation-in-cad-history-techniques-and-industrialized-fairness-analysis)
- Rhino checks:
  - Always measure with EdgeContinuity; do not trust zebra alone.
  - For a large match deviation, insert a knot at the worst point and re-match rather than using "Refine match", which adds isocurves.
  - To match a lower-degree surface to a higher one, raise its degree first.
  — [Rhino surface modeling tips](https://www.rhino3d.com/docs/guides/industrial-design/surface-modeling-tips/)
- A ball/corner blend offers tangent or curvature continuity to the fillets and primary, with continuity check feedback — [Alias Ball Corner](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-NURBS-Modeling/files/Create-geometry/Build-corner-tertiary-surfaces/GUID-E2E78F2A-62FD-4B98-AE8C-E0F126430A9D.html)

### Inferences (per join on the AE86)

| Join | Type | Target (sourced numbers applied) |
|---|---|---|
| Roof ↔ drip-rail strip | Feature edge / secondary | G1 at the roof side of the strip if the strip is a radius rolling off the roof; G0 + crisp edge where the strip turns down into the gutter lip. Position ≤0.01 mm, angle ≤0.1° on the G1 side. Because the strip is only ~8 mm wide, the roof must already roll off (crown acceleration) so the strip is not doing the turning. |
| Roof ↔ windscreen header radius | Secondary blend | G2 on the roof side (the header radius is seen in reflections along its whole width); position ≤0.01 mm, ≤0.1°, curvature deviation as small as feasible. The glass side is a separate part (glass/moulding gap), so the roof face is trimmed at the moulding line with G0 to the glass-moulding feature. |
| Roof ↔ hatch header | Same as windscreen header | G2 roof side, then the trim/shut line to the hatch glass. |
| Roof ↔ C-pillar top | Primary-to-primary via the C-pillar's G2 shoulder | G2. The C-pillar sweep top line should lie ON the roof (G0 ≤0.01 mm), with its cross-tangent and curvature taken from the untrimmed roof along that line. On the AE86 hatch the roof flows into the C-pillar, so this seam carries the long side highlight; aim for G2, and G3 if the highlight still kinks. |
| Roof ↔ A-pillar top | Primary-to-primary, usually via the drip strip | The A-pillar runs into the drip rail, so the visible join is A-pillar ↔ drip strip ↔ roof. Treat it as a tertiary corner. |
| Corners (roof + drip + header, roof + drip + A/C-pillar) | Tertiary corner patches | Ball corner/corner blend style: tangent or curvature continuous to all three neighbours. Accept G1 at very small corners (radius about the strip width). Use a setback-type corner patch rather than forcing the trim curves to meet at a point. |

- The 0.1° tangent figure is the most defensible public number to adopt for the project's G1 check. 0.01 mm is the defensible G0 figure. Both align with the existing door/wing tests if those use 1–3 mm for *shape-to-mesh* deviation (a different measure, see section 4).
- For G2 on a NURBS/OCCT seam, use Alias's curvature-deviation metric (R1−R2)/(R1+R2), measured in the cross-boundary normal section at sample points. No public numeric pass value for Class A was found. Report the value and judge by zebra.

### Gaps
- No public source gives an OEM Class-A curvature-deviation threshold, or G3 numbers.
- No source gives continuity requirements specifically for a drip rail or gutter join, or for header radii. The table above is reasoned from the general hierarchy, not sourced.

## 4. Fairness checks and acceptable deviation when matching a scan

### Takeaway
Pros corroborate several diagnostics: zebra/highlight lines, isophotes, environment maps/light tunnel, curvature combs on sections, mean/Gaussian curvature maps, and numeric continuity reports. A good roof shows stripes gliding continuously across all seams without kinks, bunching or "barber-pole" twist; combs that vary smoothly and match across boundaries; a calm mean-curvature map with one centred dome; and no unexpected saddles. Scan-match tolerances are set per project by the client; no public Class-A number was found.

### Cited Findings
- Alias diagnostic toolset:
  - Stitch for G0 gaps; Surface Continuity for G0/G1/G2 per boundary; Model Check.
  - Curve Curvature locators; Cross-Section Editor.
  - Diagnostic Shading Iso-Angle; Light Tunnel; Saddle Lines; Curvature Evaluation.
  — [Autodesk: Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2022/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)
- Novedge fairness guidance:
  - Zebra is "the fastest proxy for fairness". On a fair surface the lines glide without breaks; at drops in continuity they kink, bunch or splay.
  - Isophotes catch subtler undulations than zebra. HDRI/environment maps can reveal distortions that zebra hides (the example given is a C-pillar).
  - Curvature combs should vary smoothly without spikes.
  - Gaussian maps: unexpected saddles are a warning sign. Mean curvature should change gradually, and abrupt changes cause highlight "chatter". Umbilic position shows whether a dome is centred and fair.
  - Calibrate map scale so variation is visible without saturation.
  - Use standardised HDRI/stripe settings and a mandatory highlight sign-off gate.
  - Use dense, exact sampling, because coarse tessellation can fake or hide waviness.
  - Recheck continuity after kernel conversions.
  — [Novedge: Surface interrogation in CAD](https://novedge.com/blogs/design-news/design-software-history-surface-interrogation-in-cad-history-techniques-and-industrialized-fairness-analysis)
- Highlight lines are view-independent and reflection lines are view-dependent; both use a virtual light of parallel lines. Reflection-line irregularities reveal normal discontinuities and deviations from smoothness. References: Beier & Chen 1994 (highlight-line algorithm, *Computer-Aided Design*); Tosun et al. 2007 (shape optimisation with reflection lines) — [Wikipedia: Reflection lines](https://en.wikipedia.org/wiki/Reflection_lines); [MIT hyperbook: Highlight lines](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node149.html)
- A Class-A guideline document lists dynamic highlight analysis, reflection, curvature and mean-curvature analyses. It flags "abrupt deviation in highlights at common edge" as a failure — [Scribd: Class A document](https://www.scribd.com/document/194688584/Class-a-Document) (via search summary)
- Practitioners still call it subjective: "at the end of the day, defects on Class A surfaces are subjective" (David Dyke) — [CompositesWorld](https://compositesworld.com/articles/automotive-composites-taking-subjectivity-out-of-class-a-surface-evaluation)
- Rhino:
  - Zebra at the highest mesh density, checked both horizontal and vertical, tumbling the view and in orthogonal views.
  - CurvatureGraph with Surface Hair on several sections and directions.
  - Emap for reflections; EdgeContinuity for numbers.
  — [Rhino surface modeling tips](https://www.rhino3d.com/docs/guides/industrial-design/surface-modeling-tips/)
- Scan matching: the modeller "will be given a tolerance by which the NURBS data must match the scan". Scan data always has noise, and the clay may have imperfections. The job is to keep the intended character and filter the flaws, not to chase the scan — [Autodesk Alias: Understanding Class A Modeling, 2024](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.html) (via search summary)
- The Alias tool Fit Scan reshapes an *existing* surface to scan data; it does not create the patch layout. Tebis likewise has the user set the tolerance for how tightly surfaces adhere to digitised data — [Alias 2013: Fit a surface to scan data](https://download.autodesk.com/us/alias/2013help/files/GUID-6351E155-816A-422B-8F95-9163665A0A01.htm); [Tebis reverse engineering](https://www.tebis.com/en/software/cad-software/reverse-engineering)

### Inferences
- For the AE86 roof, the "good" picture is:
  - Lateral zebra stripes (stripes running fore-aft) that stay evenly spaced and parallel across the roof, then tighten smoothly and evenly toward the drip line (the crown acceleration), with no wobble.
  - A mean-curvature map showing a single soft dome whose maximum is near the centre and slightly forward, with no saddle anywhere on the roof skin.
  - Combs on 5–7 transverse and 3–5 longitudinal sections, each comb monotonic or single-humped.
- The Kunos source is a game mesh with faceting. The scan-tolerance principle applies: fit the intent and accept deviation where the mesh is faceted. The project's existing within-1 mm / within-3 mm coverage figures are a reasonable *shape* criterion. Continuity (0.01 mm / 0.1°) is a separate *seam* criterion and should not be relaxed to buy mesh fit.
- Compute zebra/isophote images from the OCCT faces at high tessellation density, with exact normals from the B-spline rather than mesh normals, to avoid the "coarse tessellation fakes waviness" trap.

### Gaps
- No public Class-A scan-to-surface tolerance number (mm) was found for clay or scan data. The only number found (±1.3 mm, Voith) is a general part-inspection example, not Class A.
- No published quantitative highlight criteria (e.g. maximum stripe kink angle) were found.

## 5. Roof-specific tutorials and case studies and what they recommend

### Takeaway
The roof-specific material is:
- Autodesk's Alias Automotive Class-A "Roof Scan" lessons (patch planning, fitting primaries to mesh, blends fitted vs theoretical, corner blends)
- the LearningAlias roof module (crown acceleration toward the cant rail)
- LearningAlias A-pillar and Audi A5 courses (A-pillar blends, roof-to-windscreen blend)
- Rhino forum car builds
All recommend the same order: primaries first, from fair curves → shape primaries to lead into blends → blends → corners, then check highlights.

### Cited Findings
- Autodesk's Alias Automotive Class-A series has lessons 1.4 "Roof Scan: Patch Planning" and 1.5 "Roof Scan: Fitting Primary Surfaces to a Mesh". Blend options are fitted to mesh or built to theoreticals. Corner tools: Ball Corner, Five Corner Blend, Four and Three Corner Blends — [Alias Automotive tutorials](https://www.autodesk.com/campaigns/alias-automotive-tutorials) (via search summary; 403 on fetch)
- LearningAlias roof module (start with the roof, check curvature combs against the pencil line, crown toward the cant rail, roof plus rear screen give the lead-in for cant rail and C-pillar) — [LearningAlias m=128](https://learningalias.co.uk/showmod.php?m=128&t=65)
- LearningAlias hosts an A-pillar blend tutorial (Graham Bullock) and an Audi A5 course with an A-pillar section and a roof-and-windscreen blend step. Content was not verified — [LearningAlias m=113](https://www.learningalias.co.uk/showmod.php?m=113&t=24); [LearningAlias m=203](https://www.learningalias.co.uk/showmod.php?m=203&t=1)
- A Class-A skill-builder outline lists "Parallel Roof Line" and "Roof Window" exercises (index only) — [c3872809.myzen.co.uk](https://c3872809.myzen.co.uk/)
- Rhino workaround for single-span G2 blends: when BlendSrf will not stay at 5 CPs transverse, loft between the edges, ChangeDegree to 5, then MatchSrf to curvature — [McNeel forum, via search summary](https://discourse.mcneel.com/t/heavy-blend-srf/134770.md)
- Rhino Watchmaker's Blend guide: a multi-directional corner patch method, checked with environment reflections and zebra — [Rhino: Watchmaker's blend](https://www.rhino3d.com/docs/guides/modeling/watchmakers-blend/)

### Inferences
- Recommended build order for the AE86 roof, synthesised from the above:
  1. Fair section curves (degree 5 single-span: 1 centreline longitudinal, 3–5 transverse), checked with combs against the Kunos mesh sections.
  2. One oversized single-span degree 5 roof patch through them, with crown accelerating toward the drip line.
  3. Trim lines on the roof: drip line, windscreen header line, hatch header line.
  4. Rebuild or match the drip strip, header radii and C-pillar top to the *untrimmed* roof (G1 strip, G2 headers and C-pillar).
  5. Corner patches last.
  6. Zebra, mean-curvature and EdgeContinuity-equivalent numbers at every seam.
- The project's existing chain strips and the C-pillar station-profile sweep fit this scheme. The main change is to make the roof the *master* that the C-pillar's top line and cross-tangent are taken from, not the other way round.

### Gaps
- The roof-scan lesson PDFs and videos (Autodesk) and the LearningAlias roof/A-pillar content could not be read (403 / paywall). They likely contain the concrete patch layouts and degrees.
- No ICEM Surf or CATIA ICEM Shape Design roof-specific public tutorial was found. The ICEM spec sheets are marketing only.
- The Autodesk University presentation PDF (MA3478) was downloaded but could not be text-extracted (no PDF renderer available), so its contents are unknown.
