# Industry workflows for narrow surface strips (steps, flanges, shut-line returns) between car body panels

Scope note: 16 tool calls (web search and fetch). The primary sources are Autodesk Alias help pages, which are detailed and public. ICEM Surf, CATIA ICEM Shape Design/GSD and Geomagic Design X documentation for these specific tools is mostly not public (manuals sit behind 3DS/Hexagon logins or in Scribd copies), so coverage of those tools is thin. Each gap is marked. Anything not tied to a source is under "Inferences" and labelled as practitioner knowledge.

## 1. How each tool models a narrow step / flange between two panels

### Takeaway
In professional tools a narrow step or gap is not a hand-lofted strip. It is a generated set of surfaces: fillet (G1/G2 to the panel) + ruled flange (V degree 1) + optional ruled close-out. The tool builds it along a chain of tangent-continuous curves-on-surface, and the same command trims the panel back to the fillet edge. Alias's Panel Gap, Fillet Flange and Multi-Surface Draft are the documented examples. Rhino has no dedicated tool, so users build it from Sweep2/BlendSrf/MatchSrf.

### Cited Findings
**Autodesk Alias: Surfaces > Rolled Edge > Panel Gap** (the closest documented match to a "step between two panels")
- It creates the whole set of surfaces for a finished gap along a set of tangent-continuous surface curves: the flanges that define the edges, the fillets between the panel and the edges, and an optional close-out surface at the bottom. — [Alias Panel Gap 2015](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgePanelgap.htm); [Alias 2014 Flange Surfaces overview](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-462B9CDD-B8ED-4317-87B1-547F9281588C.htm)
- Inputs: one or more G1 (tangent-continuous) surface curves on the panel. It can split one set of surfaces or create the gap between two separate sets. — [Alias Panel Gap](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgePanelgap.htm)
- **The flange surfaces are ruled in V (degree 1).** "Closeout Flanges" makes a ruled surface joining the bottom edges of the primary and secondary flanges. — same source
- Gap width: "Gap distance" (shortest distance between primary and secondary rolled edges). "Gap Position" = "Center line" (centred on the input curves) or "Primary side" (primary geometry on the curves, gap offset to one side). It is variable along the length: constant from the ends to the outer manipulators, interpolated between interior ones. A "Gap check" with a "Threshold" tolerance colours deviation quills green or red. — same source
- Flange direction: "Sweep angle" (default 90° to the input surface), "Parting line" (pull vector X/Y/Z/View/Picked + "Draft angle", default 0°), or "Relative to Primary". "Length" sets flange depth. — same source
- An imaginary "wall" surface (not added to the model) guides the primary fillet. Fillet size is set by "Center radius", "Tangent offset" (sphere tangent to surface and wall) or "Both". "Form factor" runs from 0.1 to 2.0. — same source
- Continuity of the fillet to the panel: "G1 Tangent" (default) or "G2 Curvature", with a green/yellow Continuity Check. — same source
- Surface structure: "Single surface" or "Multiple surfaces" (split at input curve and surface boundaries). "Bezier surfaces" gives single-span Bézier patches (default U degree 5). Explicit U/V degree is 3 to 6, with "Maximum spans" and a "Short Edge Tolerance" against tiny spans. — same source
- **Trimming of the wide panel:** "Trim Type" = "Off", "Curves-on-surface" (puts the fillet-edge curves on the panel without trimming), or "Automatic" (default; trims the panel to the fillet edges if the fillets run to the surface ends). The panel boundary therefore comes from the same computed fillet edge, so the shared edge is exact by construction. — same source

**Alias: Fillet Flange** (one panel edge turned down: a shut-line return)
- It creates a surface fillet along edges, curves-on-surface, boundary edges or isoparms, plus a "linear extension" flange. **The flange's V degree is always 1.** — [Alias Fillet Flange 2015](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgeFilletflange.htm)
- Flange type: "Sweep Angle" (where along the fillet the flange becomes tangent, default 90°) or "Parting Line" (vector + draft, default 0). Length can be variable. With Create Flange off, the fillet is still trimmed per the sweep/parting setting. Wall = Normal or Draft (pull vector + draft angle). — same source
- The fillet is G1 or G2 to the base surfaces. "Auto Trim" either trims the input surfaces or only places curves-on-surface. Start/End range sliders (0 to 1) set the extent. — same source
- Alias describes the tool as creating "a finish on the edges of a surface model". — same source
- Tube Flange is the variant for when control of the contact line matters most. — [Alias Tube Flange 2024](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-71AD4A98-9709-4696-97F6-551DE7BB72D5.html) (title and search snippet only)

**Alias: Multi-Surface Draft**
- It creates a flange (draft) surface along "an edge, or a chain of edges", with Explicit Control or Bezier output. It can build surfaces on both sides of a curve, as a pair or as a single surface. — [Alias 2014 Flange Surfaces overview](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-462B9CDD-B8ED-4317-87B1-547F9281588C.htm)

**Alias: blend/fillet tools for higher continuity**
- For G3-quality transitions Alias lists Freeform Blend, Profile Blend, Surface Fillet, Symmetric Fillet, Blend Curves, Object Edit > Align and direct CV modelling. — [Alias "Understanding Class A Modeling" 2024](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.html)

**Rhino**
- Rhino docs: use Sweep2 "when you want to control the location of the edges of the surface; for example, when using the edges of other surfaces as the rail curves." — [Rhino basic curves and surfaces guide](https://www.rhino3d.com/new-source/docs/guides/modeling/rhino-basic-curves-surfaces) (seen in search snippet)
- BlendSrf "creates a transitional surface between two surface, polysurface, or extrusion edges". Users report that ticking "Interior shapes" improves results, and that some options can leave the blend only G0 on each side. — McNeel Discourse threads in search results, e.g. [blend surface edge continuity](https://discourse.mcneel.com/t/blend-surface-edge-continuity/155258) (snippet only, not fetched)
- McNeel staff (Dale Fugier) confirm that RhinoCommon `Brep.CreateBlendSurface` and the BlendSrf command "are only similar in name only" (different code). His workaround for blends where edges meet at the ends is `Brep.CreateFromSweep` including the edge intersection points, plus at least one shape curve from `Brep.CreateBlendShape`. — [McNeel Discourse: Sweep2 rails edge continuity / BlendSrf component](https://discourse.mcneel.com/t/sweep2-rails-edge-continuity-and-or-blendsrf-component/110972)
- A forum suggestion in search results (thread not verified): run Sweep2 with the input surface edges as rails and BlendCrv curves as sections, then MatchSrf the result to the neighbours if closer continuity is needed. Loft between the edges is an alternative. — snippet from McNeel Discourse search results ([example thread](https://discourse.mcneel.com/t/how-do-i-handle-sweep2-problems-srf-blending-problem/155071)); exact attribution unverified

**Geomagic Design X**
- The car-body approach described in vendor and reseller material is "hybrid modelling": polygon (mesh) fitting for organic panels plus feature modelling for prismatic details. Selective Surfacing (since Design X 2020) is aimed at parts with both organic and prismatic features. Auto-surfacing wraps the whole model in 4-sided NURBS patches, giving a "dumb solid" that is poor for downstream editing. — [Hawk Ridge: hybrid modeling with Design X](https://hawkridgesys.com/blog/hybrid-modeling-with-geomagic-design-x); [rev360x full-car hybrid modeling](https://rev360x.blogspot.com/2025/08/hybrid-modeling-polygon-fitting-feature.html) (search snippets)
- Surfaces are fitted to mesh "regions" made with Auto Segment. — [CATI: impact of regions in Design X](https://www.cati.com/?p=126341) (snippet)

**ICEM Surf / CATIA**
- ICEM Surf's public product pages only mention control-point manipulation, "Matching" and real-time diagnostics. No public page describing a flange/step tool was found. — [3DS ICEM Surf](https://www.3ds.com/products-services/catia/products/icem-surf/)
- CATIA treats faces with an angular discontinuity below the tangency tolerance (0.5° or less) as tangent-continuous (G1). An IBM APAR describes styling fillets failing G1 when G2 was requested. — IBM support notes found via search ([HD77175](https://www.ibm.com/support/pages/apar/HD77175)) (snippet; not fetched)

### Inferences
- Common pattern across the documented tools: **fillet (curvature-continuous to the A-surface) + ruled (degree-1) flange + optional ruled close-out.** The fillet carries the reflections, so it gets G1/G2. The flange is a straight wall because it is a pressed or draft face, so a ruled surface is the industry default there, not a compromise.
- Shared edges are exact because the command builds the strip and computes the trim curve on the panel in the same operation (curves-on-surface at the fillet edge, then trim). The panel is never fitted to the strip afterwards.
- Practitioner knowledge, unsourced: in Rhino the equivalent is (1) project or pull the feature curve onto the panel, (2) Offset-on-surface (OffsetCrvOnSrf) to get the second edge, (3) Split/Trim the panel with those curves, (4) build the strip with Sweep2/NetworkSrf/BlendSrf using the trimmed edges as rails, (5) check with EdgeContinuity / Zebra.

### Gaps
- No public ICEM Surf manual pages for flange/step tools were reachable. A Scribd "Surf Manual English" exists but was not fetched.
- CATIA ICEM Shape Design / GSD flange (e.g. GSD "Sweep" with reference surface + angle, ICEM "Flange") documentation was not found in public form.
- No Geomagic Design X step-by-step for small fillets or steps on body panels was found. The only source is the 2014 user guide PDF (not fetched): https://www.engineering.pitt.edu/contentassets/52314f399aba40fa86709314a569641c/geomagicdesignx2014userguide.pdf
- No help pages for Alias "Profile", "Square" or "Ruled" were fetched.

## 2. Curve-first workflow: shared boundary curves, fairness, trimming

### Takeaway
The documented Alias tools are driven by **curves-on-surface** that must be tangent-continuous (G1) chains. The tool then derives both strip edges from them (gap distance, fillet radius) and trims the panel on the derived fillet edge. Alias stresses CV/hull layout as "the key", not a separate curve-first doctrine.

### Cited Findings
- Panel Gap's inputs must be G1 surface curves on the panel. Gap Position "Center line" places the gap centred on the curve. "Primary side" puts one edge on the curve and offsets the other. — [Alias Panel Gap](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgePanelgap.htm)
- Trim Type "Curves-on-surface" lays the fillet-edge curves on the panel without trimming; "Automatic" trims to them. — same source
- Fillet Flange accepts edges, curves-on-surface, boundary edges or iso-parametric lines as input. — [Alias Fillet Flange](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgeFilletflange.htm)
- Alias: "The layout of the surface data is the key to Class A modeling". Good CV layout is a core discipline. Highlight flow is checked with Diagnostic Shading, Saddle Lines, Iso-Angle and Light Tunnel; cross-boundary checks use Locators > Curve Curvature and the Cross-Section Editor. — [Alias Understanding Class A](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.html)
- Rhino's Sweep2 is the tool for using existing surface edges as rails, so the new surface's edges are the neighbours' edges. — [Rhino guide](https://www.rhino3d.com/new-source/docs/guides/modeling/rhino-basic-curves-surfaces)

### Inferences
- The robust order is: one fair driving curve → derived curve(s) at fixed distance on the panel → trim panels on those curves → build the strip on the trimmed edges (rails). That way both neighbours and the strip reference the same curve objects.
- Requiring a G1 input chain is how the tools keep the strip fair: a kink in the driving curve becomes a kink in the fillet and flange.

### Gaps
- No source found describing how ICEM/CATIA modellers fair feature lines (e.g. curve-quality tolerances, curvature combs) specifically for narrow strips.

## 3. Ruled vs G1 blend; how an ~8 mm step is treated

### Takeaway
Documented practice: the **flange wall is ruled (degree 1)** and the **transition from the visible panel into the wall is a fillet with G1 (default) or G2 continuity**, never a bare crease. A Panel Gap has a primary and a secondary fillet, so a step is "rolled radius each side + straight wall", optionally closed by a ruled close-out.

### Cited Findings
- Flange surfaces are ruled in V (degree 1). The close-out between flange bottoms is ruled. Fillets default to G1 and can be G2. — [Alias Panel Gap](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgePanelgap.htm)
- Fillet Flange: the flange V degree is always 1; the fillet is G1 or G2 to the base. — [Alias Fillet Flange](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgeFilletflange.htm)
- Class A is generally taken to mean at least G2 on visible surfaces. Strictly it requires "curvature and tangency alignment". — [Wikipedia: Class A surface](https://en.wikipedia.org/wiki/Class_A_surface)
- Alias names separate tolerance and standards categories for "main blends versus smaller and detail fillets" and for "split lines, flanges, and panel gaps". In other words, OEM standards treat flanges and detail fillets separately from main A-surfaces. — [Alias Understanding Class A](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.html)

### Inferences
- For a 5 to 10 mm strip: a ruled surface is acceptable for the non-reflective wall or flange part. Where the strip meets a visible panel, a small G1/G2 fillet (rolled edge) is the professional default. A sharp crease reads as a highlight break and is normally only used where the real part has a sharp pressed edge, then softened by a small radius.
- A ruled strip between two trimmed panel edges is automatically G0 on both long edges (its rails are the edges), but only G1 if the panels happen to be tangent to the ruling direction. That is why tools add fillets rather than relying on the ruled wall alone.

### Gaps
- No public source gives typical radii for the fillets on an 8 mm step (e.g. 1 to 3 mm). This needs OEM standards or training material.

## 4. Continuity tolerances (G0 / G1 / G2) and minimum radii

### Takeaway
There is **no universal standard**. Each OEM sets its own. The only vendor-published guidance found: Alias says a typical maximum G0 gap is **0.01 mm to 0.001 mm** for prototyping/production, and a tangent break **below 0.1°** is normally invisible. CATIA's built-in G1 threshold is **0.5°**. A French proposal sets Class B at **G0 0.001 mm, G1 0.2°**.

### Cited Findings
- "Typical Maximum Gap Distance would be between 0.01mm and 0.001mm" (prototyping/production). A tangent break "less than 0.1 degrees" will normally not be visible on most products. G2 is measured as Curvature Deviation = (R1 − R2)/(R1 + R2), with no numeric threshold given. Each company develops its own tolerances. Presets exist for downstream CAD (e.g. "Catia V5") and "General CAD settings". — [Alias Continuity 2: Construction Tolerances](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-2FCE06EB-8EF7-4507-92F7-82A73A0DF378.html)
- In Alias construction tolerances, "Topology Distance" is typically twice the G0 position value. — [Kerry King Alias reference R6 constTols](https://kerryking.myzen.co.uk/html/reference/R6_constTols.htm)
- "There are no absolute rules for tolerances or continuity levels". Standards are proprietary and set per automotive company. Checks: Surface Edit > Stitch (G0 gaps), Evaluation > Surface Continuity, Evaluation > Model Check. — [Alias Understanding Class A](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.html)
- Proposed classification (French engineers; Class A not standardised): Class B = G0 0.001 mm, G1 0.2° max, undulation Cu = 0.003 mm⁻¹. No numbers are given for Class A. — [Wikipedia: Class A surface](https://en.wikipedia.org/wiki/Class_A_surface). One mirror quotes Class B G0 as 0 mm instead (search snippet), so the figure differs between copies.
- CATIA treats faces with angular discontinuity below 0.5° as G1-continuous (tangency tolerance). — IBM support note via search ([IBM support](https://www.ibm.com/support/pages/node/5488983)) (snippet, not fetched)

### Inferences
- Reasonable working targets taken from the above: G0 ≤ 0.01 mm (tight: 0.001 mm), G1 ≤ 0.1° on visible edges (0.5° is only CATIA's "counts as tangent" threshold), G2 judged by curvature combs/zebra rather than a fixed number.
- For a game-asset or mesh pipeline (kn5), these CAD tolerances are far tighter than visible needs. The point that carries over is that the strip and both panels share identical edge curves (G0 by construction), with tangent matching on the visible side.

### Gaps
- No source found for OEM-specific numbers (e.g. 0.005 mm / 0.05° / 5 % curvature). Search did not find any public OEM spec.
- No source found for minimum styling radii on feature lines or steps. Search results only covered sheet-metal bend radius as a multiple of thickness (1T to 2T), which is a forming limit, not a styling rule.

## 5. Shut-line returns (panel edge turning inward ~5 mm)

### Takeaway
In Alias a shut-line return is a **Fillet Flange** (one panel) or a **Panel Gap** (both panels at once): a G1/G2 rolled-edge fillet off the A-surface, then a ruled flange at a sweep angle or along a pull/parting direction with draft. The panel is trimmed back to the fillet edge automatically.

### Cited Findings
- Panel Gap builds primary and secondary rolled edges (fillet + flange) on each side of the gap. Gap distance = shortest distance between the two rolled edges. The flange is set by sweep angle (default 90°) or parting-line vector + draft. There is an optional close-out. The panel is auto-trimmed to the fillet edges. — [Alias Panel Gap](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgePanelgap.htm); see also [Create panel gaps with rolled edges (Alias 2013)](https://download.autodesk.com/us/alias/2013help/files/GUID-80615479-575D-4118-A3DF-13F08FF1A5BA.htm) (not fetched)
- Fillet Flange: fillet + linear (degree-1) flange of set or variable length, oriented by sweep angle or parting line/draft. Auto Trim on the base surface. — [Alias Fillet Flange](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Reference/files/SurfacesRollededgeFilletflange.htm)
- OEM standards cover "split lines, flanges, and panel gaps" as their own category. — [Alias Understanding Class A](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.html)

### Inferences
- To reproduce a shut-line return outside Alias: take the shut-line curve on the panel → offset it on the surface by the rolled-edge width → trim the panel there → build a fillet strip (G1 to the panel) from the trim edge to a curve displaced inward along the pull direction → add a ruled flange ~5 mm deep from the fillet's far edge. The visible gap width is measured between the two rolled edges, not between the raw trim lines.

### Gaps
- No public source gave typical automotive gap widths, flange depths or rolled-edge radii for shut lines.
- No ICEM Surf or CATIA equivalent procedure was found publicly.
