# Bonnet edges: nose roll, tongue, flanges, shut lines and inner panel (real Class-A practice and sim car models)

Scope: how a car bonnet is built at its edges, gathered for the 1983 AE86 Trueno bonnet replica. The replica has a nose tongue between the headlight bays at x +-358 mm, which rolls from -15 deg to -62 deg slope over its last 100 mm into a vertical front face. It also has 3-7 mm side returns and steps, a 30 mm rear flange, washer nozzles and an underside panel.

Two kinds of evidence are used:
- **Public web sources.** Each has its URL.
- **My own measurements of the Kunos `ks_toyota_ae86` LOD A model.** Kunos built this car, so it is the best "how the pros did this exact bonnet" reference.
  - Model: `D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86/toyota_ae86.kn5`
  - Read with the repo's reader `D:/Claude/Claude-/blender/kn5-study/kn5full.py`.
  - Scripts: `D:/ClaudeData/tmp/bonnet_research/scripts/hood*.py`
  - Axes are AC's: +y up, +z forward, +x = car's left, in metres.
  - Any slope angle I quote from it is the angle of the **smoothed vertex normal** from vertical. That is close to the surface slope but not exact.
  - These measurements are cited as [Kunos AE86 kn5, measured].

---

## Q1. Nose roll: one surface, or a primary surface plus a rolled blend? What continuity, and how is it judged?

### Takeaway
In Class-A practice a hood nose that turns 50-90 deg is not one primary surface. It is built as:
- a fairly flat primary surface (or a small set of them),
- a separate front surface,
- and a blend or fillet between them that can vary in radius along its length.

The minimum continuity is G2, and G3 is the norm in automotive Class-A. The work is judged with curvature combs and highlight checks (iso-angle, light tunnel, zebra, saddle lines). Kunos's own AE86 nose rolls progressively, from about 14 deg to about 52 deg over its last ~137 mm. That is close to the replica's target. The roll is made with ever-denser edge loops in one smooth-shaded mesh, with no crease.

### Cited Findings
- A BMW Z4 hood Class-A build used "6 parent surfaces with 2 smaller surfaces at the front of the hood + the blends", and the author says it could be done with 3 parent surfaces.
  - The hood used 16 surfaces, "the minimum that would accurately follow the design lines".
  - Very large surfaces are avoided because they give "horrid bulging edges".
  - Source: [LearningAlias, BMW Z4 hood Class A](https://blog.learningalias.co.uk/2010/05/)
- The same source says Class-A surface continuity is "min G2 and mostly G3". The model must be fully closed ("no gaps"), and a "perfect Class A Curvature Comb, Depicting G3" is the acceptance test. — [LearningAlias](https://blog.learningalias.co.uk/2010/05/)
- G1 (tangent) matching gives no guarantee that a highlight flows across a boundary without a peak. G2 matches curvature across the boundary. G3 curvature combs show no peak at the boundary, and G3 "is mostly required in Class-A Surfacing in the automotive industry". — [Autodesk Alias: Curvature Continuity in Surface Modeling](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-9DD73E22-A5EF-4952-BB84-2CEE2109993C.htm) (from the search summary of the page)
- Alias's Class-A tutorial pairs checks with stages (from the search summary):
  - boundary continuity: Curve Curvature and Cross-Section Editor
  - continuity flow: Iso-Angle and Light Tunnel
  - highlight flow: Saddle Lines
  - Source: [Autodesk: Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2019/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)
- An automotive surfacing forum view (from the search summary): "a good blend is always determined by the quality of the main, less curved surfaces. You cannot compensate this in a blend." — summarised in search results for [McNeel discourse on G0-G3](https://discourse.mcneel.com/t/understanding-g0-g2-g3-in-relation-to-curvature-combs-continuity/146065). This is opinion and secondhand.
- Alias Surface Fillet "builds controlled blends between primary surfaces". Rolled-edge finishes are made "with a fillet and a flange surface" (the Fillet-Flange / Tube-Flange tools). — [Autodesk Alias NURBS surface modelling](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Video-Tutorials/files/alias-nurbs-surface-modeling.html)
- Alias fillet cross-section types — [Alias: fillet cross section and continuity](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-36EB38AB-0635-4436-8273-E9A74F06907F.htm)
  - "Lead", with a peak radius or knee ratio
  - "G1 Circular", with a centre radius
  - "G2 Curvature" or "G3 Curvature", enforced "on both sides or only one side (the other side will be tangent)"
  - a Form Factor that sets the CV distribution across the section
- A variable-radius fillet can carry several radius manipulators along its length, each with its own value. One Alias page (search snippet) says the LEAD option gives a visible curvature break, but its curvature result gives a better highlight than CIRCULAR. — [Alias: control the radius along a variable fillet](https://download.autodesk.com/us/alias/2013help/files/GUID-076464B6-D27B-4179-9D43-D7E3E9D10258.htm). The highlight remark comes from a search snippet and was not verified on the page.
- Autodesk's Class-A tutorial series has dedicated "Hood Edge" (5.23) and "Hood Edge Optimisation" (5.24) lessons with video, PDF and data. — [Autodesk Alias automotive tutorials](https://www.autodesk.com/campaigns/alias-automotive-tutorials) (from the search listing; the page returned HTTP 403 to my fetch, so their content is unverified)
- **Kunos AE86 centre-line nose section (x = 0)** [Kunos AE86 kn5, measured]:

  | Distance from front tip (mm) | Normal angle from vertical | Gap to next row (mm) |
  |---|---|---|
  | Bonnet body, from 1044 mm (rear edge) | ~6-10 deg | ~100 |
  | 137 | 14.5 deg | |
  | 108 | 16.0 deg | |
  | 92 | 17.6 deg | |
  | 72 | 19.5 deg | |
  | 52 | 25.7 deg | |
  | 39 | 34.2 deg | |
  | 25 | 45.4 deg | |
  | 13 | 52.5 deg | |

  - Measured tip-to-rear, the centre-line row spacing is 59 / 59 / 37 / 29 / 16 / 20 / 20 / 13 / 14 / 12 mm, so the edge loops tighten as the roll tightens.
  - Below 52.5 deg the surface runs on down at about 53 deg to a small rounded lower tip (y 0.6385, z 1.9073). It then turns under in a ~8 mm down-facing strip (normal ~179 deg), which joins the underside panel.
  - The Kunos centre line therefore **never reaches vertical**. It ends about 53 deg from horizontal, with a ~2 mm round under the tip.
  - All of this is one smooth-shaded mesh, `GEO_hood_SUB1`, with **0 hard-edge vertex splits**.

### Inferences
- The replica's progressive -15 deg to -62 deg roll over 100 mm, ending in a vertical face, should be built the Class-A way:
  - a primary top surface that stays gently curved (about 6-15 deg slope),
  - a front face surface,
  - a G2 (ideally G3) variable-section blend between them.
- The measured Kunos profile shows the curvature rising smoothly (14->20->26->34->45->52 deg in 20-13 mm steps). That is the "progressive / flowline" behaviour a lead-type or G2/G3 curvature fillet gives, rather than a constant-radius G1 circular fillet.
- A constant-radius G1 fillet would show a curvature jump, a highlight kink, at each tangent line. Check it with zebra or iso-angle lines run front to back across the nose.
- Inference from the Kunos data: the real AE86 nose probably does not become fully vertical at the centre line either. The steepest visible part is about 50-55 deg, then a small under-roll.
  - Check the "vertical front face" target against photos (side view at the tongue).
  - Possibility: a vertical face may exist only on the tongue's front edge or at the bay corners.
- Inference for a mesh or sim build: loop spacing in the roll should shrink to about 12-20 mm, from ~60-100 mm on the flat, to keep the highlight smooth under plain averaged normals.

### Gaps
- I found no public OEM document giving a hood nose radius or roll angle for any car. Autodesk's "Hood Edge" lesson PDFs could not be fetched (403).
- I did not confirm whether real Class-A studios build a rolled nose as a "flowline" surface (a swept section along the front edge) or as a variable fillet. Both tool families exist in Alias. No source says which is preferred for hood noses.

---

## Q2. How does a tongue between the headlight bays meet its side walls?

### Takeaway
I found no public bonnet-specific source on this. The general CAD rules are: build the corner as a setback or corner-blend patch where three blends meet, and check it with zebra stripes.

In the Kunos AE86:
- The tongue edge sits at x ≈ 0.348 to 0.358 m, which matches the replica's ±358 mm.
- Its side edge is a rounded corner about 10 mm wide that follows the full nose-roll profile.
- Beside the tongue (x > 0.36) the bonnet stops at z ≈ 1.72 m, where the pop-up lids begin.

### Cited Findings
- Rhino's FilletEdge has a "Setback" option for corners the standard algorithm handles poorly, and its documentation uses zebra analysis to compare corner transition quality. — [Rhino FilletEdge docs](https://docs.mcneel.com/rhino/9/help/en-us/commands/filletedge.htm) (from the search summary)
- Zebra stripes that flow smoothly from face to face show a clean blend. — [Onshape fillet help](https://cad.onshape.com/help/Content/fillet.htm) (from the search summary)
- Alias Panel Gap / Fillet-Flange (see Q3) build the fillet, the flange, and an optional close-out at the gap. These are the tools an Alias modeller would use for the tongue-to-headlight-lid shut line. — [Alias: create panel gaps with rolled edges](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-80615479-575D-4118-A3DF-13F08FF1A5BA.htm)
- **Kunos AE86 tongue** [Kunos AE86 kn5, measured]:
  - Plan outline of the bonnet:
    - At x 0.33-0.36 the bonnet reaches z 1.901 (the tongue tip).
    - At x 0.36-0.39 it reaches only z 1.847, the start of the corner.
    - At x > 0.39 it ends at about z 1.72 (the headlight-lid shut line).
  - At the tongue's side, sections at x = 0.3481, 0.3529, 0.3567 and 0.3580 all repeat the same nose-roll profile, with y running 0.7256 -> 0.6375 between z 1.722 and z 1.90.
    - So the tongue corner is a **~10 mm-wide round** (four loops across x).
    - The roll profile is swept unchanged through the corner.
    - The side face is the short vertical strip at x ≈ 0.358-0.359, y 0.638-0.655 (about 17 mm deep at the front).
  - The bonnet's side edge outboard of the bays turns down at its rear corner. The bonnet is not cut out around the lids. The lids are separate meshes; they are not part of `MOTORHOOD`.

### Inferences
- Build the tongue as an extension of the bonnet top, with the nose-roll section swept along the tongue front.
  - Its side edges are a ~10 mm round into a short side return of ~15-17 mm, running along the shut line to the headlight lid.
  - The corner where the nose roll meets the side round is a three-way blend. Use a setback corner patch (or equal-radius tangent-line ends) so the zebra lines don't pinch.
- The step between the tongue and the headlight-lid surface is a real panel gap. Treat it like any other shut line (Q3): a return plus a dark AO line, not a deep slot.

### Gaps
- I found no public engineering drawing or Class-A tutorial for a pop-up-headlamp tongue corner. That includes the AE86, RX-7 FB/FC, MR2 AW11 and Corvette C4.
- I did not measure the exact corner round radius in plan (only its ~10 mm footprint). That needs a dense section script.

---

## Q3. Real bonnet edges: hem flanges, panel gaps and flush, visible edge radius, return depth

### Takeaway
A production bonnet edge is the outer skin's flange folded 180 deg over the inner panel's flange (a hem).

| Item | Typical value |
|---|---|
| Hem width | ~8 mm on straight runs, ~6 mm on convex curves, ~4 mm at sharp corners; outer flanges can drop to 6 mm or less in curved and cut-line areas |
| Conventional hem radius | ½ × inner thickness + outer thickness, about 1.1-1.2 mm for 0.7-0.8 mm steel |
| Bonnet-to-wing gap | 3-4 mm nominal, about ±1-1.5 mm tolerance |
| Flush | Bonnet often set slightly under-flush (0 to -2 mm) |

### Cited Findings
- **Hem radius:** "the radius is equal to one-half the inner panel thickness plus the outer panel thickness" for a conventional hem. — [US7241073B2 Sheet metal hem](https://patents.google.com/patent/US7241073)
- **Marriage gap** (between the hem layers, filled with adhesive): "generally approximately 2 millimeters" for conventional hems. — [US7241073B2](https://patents.google.com/patent/US7241073)
- **Flange length:** in cut-line and curved areas, outer flanges may need to be cut "to 6 millimeters or less". — [US7241073B2](https://patents.google.com/patent/US7241073)
- **Inner panel thickness:** conventional steel is about 0.7-0.8 mm, aluminium about 0.9-1.2 mm. — [US7241073B2](https://patents.google.com/patent/US7241073)
- **Pre-hem steps:** about 45 deg in one pass, or 60 deg then 30 deg. — [US7241073B2](https://patents.google.com/patent/US7241073)
- **How the hem looks:** a larger hem makes the gap look larger, and a smaller hem gives "a crisper cut line and a smaller perceived margin". — [US7241073B2](https://patents.google.com/patent/US7241073)
- **Hood roll-hemming widths (BAIC / AutoForm study):** 8 mm on flat straight areas, 6 mm on convex circular areas, 4 mm at sharp angles.
  - Some sharp corners "require removal of the hemming".
  - The flange angle before hemming should be held at 90-105 deg.
  - Designers set the outer hemming width from experience.
  - Source: [FormingWorld: BAIC digital hemming workflow](https://formingworld.com/baic-digital-hemming-workflow/)
- **Hem types:** the flat hem is the most common; rope hems bend past 180 deg and are then pressed. — [FormingWorld](https://formingworld.com/?p=7367) (from the search summary)
- **Mastic between inner and outer:** the hood design project says the mastic points should be at most 5 mm apart. — [Skill-Lync hood design](https://skill-lync.com/student-projects/hood-design-week-2-1011) (a student project; low authority)
- **Gap and flush specs** (gap = the opening; flush = height difference, negative = bonnet lower):

  | Car | Bonnet-to-wing gap | Flush | Source |
  |---|---|---|---|
  | Ford Mustang 2014 | 3.6 ± 1.5 mm | -0.75 ± 1.5 mm | [Ford workshop manual, section 501-35](https://reichwein.it/manuals/Mustang_2014/Workshop_Manual_Wiring_Diagrams/Resources/Service_Manual/seb1z003.htm) |
  | Saab 9-5 | 3 ± 1 mm | | [Saab WIS hood adjustment](https://saabwisonline.com/9-5-9650/2011/8-body/body/adjustment-replacement/hood-adjustment) |
  | Mercedes W205/W253, W212 | about 3-4 mm | | [MBWorld W205 panel gap PDF](https://mbworld.org/forums/attachments/c-class-w205/325067d1455402251-hood-bumper-gap-w205-w253_panel_gaps.pdf); [MBWorld W212 gap PDF](https://mbworld.org/forums/attachments/e-class-w212/418582d1542231358-left-front-fender-replacement-gap-dimensions-hoods-doors-lids.pdf) (search summary; tolerance ±0.5-1 mm) |
  | Vehicle in an NHTSA-filed bulletin | (not given) | 2.0 ± 1.5 mm under-flush, going to 0.0 at the rear | [NHTSA bulletin MC-10225222](https://static.nhtsa.gov/odi/tsbs/2022/MC-10225222-9999.pdf) |

  - A vendor page gives a 3.5-4.5 mm hood-to-wing target. That is marketing, not an OEM spec. — [iFactory gap-and-flush](https://ifactoryapp.com/industries/automotive-manufacturing/gap-and-flush-measurement-vision-ai)
- **Alias Panel Gap tool:** "the ultimate rolled edge tool". It builds the flanges, the fillets between panel and edge, and an optional close-out surface at the bottom of the gap. Inputs must be G1 tangent continuous.
  - Gap distance, flange length and flange angle are parameters.
  - With Variable geometry on, the gap width can vary along its length.
  - Source: [Alias: create panel gaps with rolled edges](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-80615479-575D-4118-A3DF-13F08FF1A5BA.htm)
  - Older documentation adds a constant "Primary radius" circular fillet tangent to the panel, a "Secondary radius", and "Gap distance" (the shortest distance between the two rolled edges). — [Alias 2012: Rolled Edge > Panel Gap](https://download.autodesk.com/us/alias/2012help/files/SurfacesRollededgePanelgap.htm) (from the search summary)

### Inferences
- **Visible edge radius, inferred:** a flat hem's outside radius is about outer thickness + ½ inner thickness.
  - For a 1983 steel bonnet (sheet about 0.7-0.8 mm, typical but not sourced for the AE86) that is **R ≈ 1.1-1.2 mm**.
  - Seen from outside, then, the bonnet edge is a tight ~1-1.5 mm round turning down into the hem.
  - The "return" visible in the gap is the hem's outer face: the outer skin thickness plus marriage gap plus inner flange, about 3-4 mm of metal stack, folded about 8 mm deep.
  - Behind that sits the inner panel's flange and frame, set well back.
- **For the replica:**
  - A 3-4 mm gap to the wing, set flush to about 1 mm under.
  - Edge round R 1-2 mm. (Kunos used about 1.5-2 mm; see Q5. A slightly larger round reads better at game resolutions.)
  - Side returns about 8-15 mm deep.
  - The replica's planned 3-7 mm returns are plausible as the real hem face, but are shallower than Kunos's ~15 mm. Kunos's deeper return hides the see-through gap from low viewing angles.
- **The 30 mm rear flange:** on a real bonnet the rear edge is also a hem (~8 mm) against the inner panel, and the inner panel's rear frame runs below it.
  - A 30 mm downturn is more than a hem. It may be the inner-panel rear frame, or the cowl-side seal ledge, seen in photos.
  - Kunos models the rear edge as a ~15 mm vertical return (Q5).
  - This last point is inference; check it against photos.

### Gaps
- I found no AE86-specific gap/flush spec. A Toyota AE86 body repair manual (1983-87) would have it but is not public online.
- I found no source for 1980s Toyota hood sheet thickness.
- No source gave a standard "visible return depth" for a hem as a design number. The above is derived from the hem build-up.

---

## Q4. Pop-up headlight bonnet specifics (AE86, RX-7 FB/FC, MR2 AW11, Corvette C4)

### Takeaway
I found no public engineering or Class-A data for any pop-up-headlamp bonnet. The best available reference is the Kunos AE86 model itself, measured above and below.

### Cited Findings
- Searches turned up only parts listings for the AE86 bonnet: reproduction steel bonnets, Seibon carbon OEM-style bonnets, and FRP options. None gives inner-frame or front-edge construction. — [Battle Garage reproduction AE86 steel hood](https://shop.battlegarage-rs.com/products/corolla-84-87-hood); [Seibon AE86 OEM-style carbon hood](https://shop.battlegarage-rs.com/products/seibon-84-87-toyota-levin-ae86-oem-style-carbon-fiber-hood)
- **Kunos AE86 bonnet overall** [Kunos AE86 kn5, measured]:
  - Centre-line length from rear edge (z 0.8632) to front tip (z 1.9073): **1044 mm**.
  - Half-width at the rear: **631 mm** (overall about 1262 mm).
  - Tongue half-width: **~358 mm**.
  - Outboard of the tongue the bonnet ends at z ≈ 1.72 m, where the pop-up lids begin. The lids are separate `LIGHT_*` meshes.
- **Kunos RX-7 FC (`ks_mazda_rx7_spirit_r`)** bonnet: 602 tris — 552 carpaint + 50 black plastic, with no separate underside material [Kunos kn5 survey, measured].

### Inferences
- For the replica, the tongue / headlight-lid shut line can be treated as an ordinary panel gap (Q3), since the lids are separate parts.
- Inference: the AE86 headlight lid sits slightly below the bonnet top or flush with it. That needs checking in photos. The measured Kunos tongue side wall (about 17 mm at the front) is the step the lid closes against.

### Gaps
- I found no public drawings, repair-manual pages or Class-A material for AE86 / RX-7 / MR2 AW11 / Corvette C4 bonnet edges or inner frames. Teardown photos on owners' forums (AEU86.org) are the likely next source, but I did not find one with usable dimensions.

---

## Q5. Sim car models: how Kunos and others model bonnet edges, shut lines and the inner panel

### Takeaway
Kunos models a bonnet as:
- **one smooth-shaded outer skin with a short geometric return** (about 15 mm deep, ~1.5-2 mm edge round) on every edge,
- leaving a narrow gap of about 1.5-2 mm wall-to-wall to the body's own return,
- **with the dark shut line carried by baked ambient occlusion (AO)** in the paint diffuse and gloss maps.

The underside is a **separate, very low-poly, dark "underside" material** welded to the skin's boundary. It closes the box so that no hole shows when the bonnet moves in damage. Kunos's own pipeline requires this capping.

BeamNG says not to fake panel bevels with normal maps on body panels.

### Cited Findings
- Kunos pipeline, car damage section:
  - The `MOTORHOOD` is a damage part, pivoted on a null "it can be the hinges".
  - "Make sure that you have closed the mesh in the interior. You put a black texture or something very dark to ensure that there is no gaping hole behind the moving objects."
  - "Detach parts only that don't leave holes in the car when moving, or carefully cap the holes."
  - Source: `D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf`, p.43 (Kunos "AC Pipeline Rev 2.0", shipped with the AC SDK)
- Kunos pipeline, other rules:
  - `MOTORHOOD` "Depends on car type — if needed, must be present in LOD A and LOD B".
  - In LOD C parts "such as wings, bumpers, the hood" may be merged into the body.
  - The damage mask must "Never paint the roof and the top of the bonnet".
  - Meshes should be "(when possible) in quads. Do NOT triangulate the mesh if it is not necessary."
  - Source: AC_Pipeline_PUB_Rev2.0.pdf, pp.3, 9, 44 (local SDK file, path above)
- Kunos pipeline on AO:
  - Bake exterior AO at 4096 (double resolution).
  - Keep doors far enough apart to avoid dark occlusion on borders.
  - Retouch the AO in Photoshop to "soft gradients".
  - Use wide padding against black bleeding.
  - Source: AC_Pipeline_PUB_Rev2.0.pdf, pp.54-55 (local SDK file)
- Repo study of 112 AC cars [local: `D:/Claude/Claude-/blender/kn5-study/KN5_STUDY.md`, sections 4.7 and 5]:
  - "Panel gaps are mostly painted, not modelled."
  - Each panel turns in about 5 mm at a gap, leaving a 3-4 mm opening.
  - Every Kunos paint diffuse is a white sheet with baked AO in which shut lines show as dark lines; the `txMaps` gloss channel carries the same AO.
  - The paint normal map is used only for damage dents.
  - Normals are plain averages; hard edges are rare on Kunos 2016+ cars (3-7 %).
- **Kunos AE86 bonnet structure** [Kunos AE86 kn5, measured]: under the `MOTORHOOD` null there are three sub-meshes, 882 tris in all.

  | Mesh | Material / shader | Tris | Verts | What it is |
  |---|---|---|---|---|
  | `GEO_hood_SUB1` | `EXT_HOOD` / ksPerPixelMultiMap | 644 | 1026 | Outer skin, with 0 hard-edge splits |
  | `GEO_hood_SUB2` | `EXT_underside` / ksPerPixel | 96 | 200 | Underside / inner panel; all normals face down |
  | `GEO_hood_SUB0` | `EXT_details` / ksPerPixelReflection | 142 | 236 | Two washer nozzles |

- **Underside detail** [Kunos AE86 kn5, measured]:
  - 108 of its 200 vertices **coincide (<0.5 mm) with the outer skin's boundary vertices**, so the bonnet is a closed shell.
  - It is a coarse lid following the bonnet's shape. On the centre line it has only ~6 stations along 1044 mm.
  - It sits **~30 mm below the outer skin mid-bonnet** (z 1.3) and **~18 mm below near the nose** (z 1.72).
  - It spans the same plan outline (x max 0.6308 at z 1.0, the same as the skin).
- **Side return** [Kunos AE86 kn5, measured]:
  - At z = 1.278 the top surface ends at x 0.6272, y 0.7959.
  - It rounds over through x 0.6282 / 0.6290 / 0.6299 (about a **1.5-2 mm round**).
  - It then drops vertically to y 0.7817: **return depth ≈ 14 mm**.
  - Similar values at z 0.717 (top 0.8599 -> 0.8448, 15 mm) and z 1.574 (0.7466 -> 0.7321, 14.5 mm).
- **Gap to the wing** [Kunos AE86 kn5, measured]:
  - The body's own return wall is at x ≈ 0.6302-0.6316, and its top round starts at about x 0.634-0.640.
  - So **wall-to-wall gap ≈ 1.5-2 mm** (minimum vertex distance bonnet-to-body: 1.75 mm).
  - **Visible edge-to-edge** (bonnet tangent line to wing tangent line) ≈ 6-7 mm.
  - Bonnet top vs wing top: within ~1.5 mm (essentially flush).
  - These are vertex-sampled, so ±1 mm.
- **Rear edge, at the cowl** [Kunos AE86 kn5, measured]: on the centre line the top round (normal −41 deg) leads into a vertical rear-facing return from y 0.875 to 0.860 (**15 mm**), and the underside starts there. There is no 30 mm flange.
- **Washer nozzles** [Kunos AE86 kn5, measured]:
  - There are two, at x ±0.226-0.244 and z 0.955-0.974, about 92-111 mm forward of the bonnet rear edge.
  - Each is about **18 mm wide × 19 mm long × 13 mm tall**, about 71 tris, sitting on the skin.
  - They are separate meshes in a reflective details material, **parented under `MOTORHOOD`** so they move with the bonnet.
- **BeamNG official guide:**
  - Inside and outside of panels "should have the same topology", or "the inside polygons will poke out on deformation".
  - "all meshes should have back faces if the inside is visible".
  - "avoid using normal maps for body panels (they create unwanted reflection artifacts…)". Model a 3D bevel where its radius is noticeable at default camera distance.
  - "Focus higher poly density on visible areas; reduce for hidden parts."
  - Source: [BeamNG vehicle modelling docs](https://docs.beamng.com/modding/vehicle/vehicle-art/modeling/)
- BeamNG's older guide (search summary) suggests vertex spacing of about 6.35 mm (0.25") to represent panel gaps. — [BeamNG Modeling and Texturing Guide](https://wiki.beamng.com/Modeling_and_Texturing_Guide) (secondhand; not verified on the page)
- Forum claim, unverified: "for games like Forza, they did higher poly meshes, and it's just a flat color shader". Another artist keeps a hood underside flat and simple. — summarised from [Polycount discussion](https://polycount.com/discussion/comment/2806670). Forum hearsay, not Turn 10.

### Inferences
- **Kunos recipe for the replica's edges:**
  - an outer skin with an R ~1.5-2 mm edge round,
  - a ~14-15 mm vertical return on the sides, rear and tongue, kept as one smooth-shaded mesh,
  - a wall-to-wall gap of about 2 mm to the wing's return (visible gap about 4-7 mm including rounds),
  - the dark shut-line read added by baked AO, not a modelled groove.
- The replica's 3-7 mm returns are fine where a real step exists. For see-through protection on the sides and rear, though, Kunos goes to ~15 mm.
- **The underside on Kunos is a cap, not a pressed inner panel.** It is coarse (96 tris), dark, welded to the skin's return bottom, and only noticeable when the bonnet opens or lifts in damage.
  - The replica's "underside panel" can follow this route: a simple shape-following lid 15-30 mm below the skin.
  - It can be upgraded to a modelled inner frame only if open-bonnet views matter. AC has no bonnet-open animation by default; the `MOTORHOOD` null serves damage.
- Washer nozzles belong in the `MOTORHOOD` hierarchy as separate small detail meshes, at roughly 70 tris each.

### Gaps
- The Kunos pipeline PDF says nothing explicit about panel-gap geometry or return depth. The Kunos numbers above are measured from one car.
- I found no official Turn 10 / Polyphony / Kunos talk (GDC or similar) on bonnet edge modelling.
- I did not check whether the AE86 AO texture carries a dark line along the tongue/lid shut line, though it is very likely given the repo study.

---

## Q6. Typical polygon budget for a bonnet in a sim car

### Takeaway
Kunos LOD A bonnets are about **300-1,300 tris (about 0.7-1.7 % of the car)**. The outer paint skin is about 200-700 tris, and the underside about 70-110 tris when present. One outlier, the Celica ST185, reaches 2,268 tris because of its vents and grilles.

The AC pipeline budget is 125,000 tris for the LOD A exterior.

### Cited Findings
- **AC pipeline triangle targets:**
  - LOD A exterior 125,000 tris
  - LOD B 20,000-25,000 (shown at 15 m or closer)
  - LOD C 10,000-12,000
  - LOD D 2,000-3,000
  - HR cockpit 125,000
  - Default LOD out-distances: 15 / 45 / 200 / 1500 m
  - Source: AC_Pipeline_PUB_Rev2.0.pdf, pp.6-8 (local SDK file: `D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf`)
- **Kunos `MOTORHOOD` survey**, LOD A main kn5 [Kunos kn5 survey, measured with `D:/ClaudeData/tmp/bonnet_research/scripts/hoodbudget.py`]:

  | Car | Bonnet tris | Share of car | Parts (material: tris) |
  |---|---|---|---|
  | ks_toyota_ae86 | 882 | 1.1 % of 80,619 | skin 644, underside 96, nozzles 142 |
  | ks_mazda_rx7_spirit_r (FC) | 602 | 0.7 % | carpaint 552, plastic 50 |
  | bmw_m3_e30 | 443 | 1.0 % | carpaint 256, details 93, black 64, logos 30 |
  | ks_ford_escort_mk1 | 1,310 | 1.7 % | paint 698, letters 208, metal 362+26, bolts 16 |
  | ks_toyota_supra_mkiv | 778 | 0.8 % | body 566, underside 106, plastic 106 |
  | ks_nissan_skyline_r34 | 644 | 0.7 % | carpaint 502, black 142 |
  | ks_mazda_miata (NA, pop-up) | 682 | 0.9 % | chassis 588, black 68, plastic 26 |
  | ks_toyota_celica_st185 | 2,268 | 2.4 % | details 1,138, body 1,046, underside 73, grid 11 |
  | ks_porsche_911_carrera_rsr | 625 | 1.0 % | |
  | abarth500 | 296 | 0.8 % | |

  ks_audi_sport_quattro has no `MOTORHOOD` null.
- Repo study [local `KN5_STUDY.md`]: Kunos body quads run on an 18-27 mm grid, about 40 mm on the flat roof and bonnet. LOD B/C/D are about 15 % / 4 % / 1 % of LOD A.
- rFactor 1 forum guidance (other sim, older): about 15,000-25,000 tris for a high-res car including wheels. — [RaceSimCentral optimal polycount](https://community.racesimcentral.net/goto/post?id=3332) (from the search summary)

### Inferences
- A Kunos-grade AE86 replica bonnet for LOD A: aim at about **600-900 tris for the skin** (more is affordable — 125k budget vs the Kunos AE86's 80.6k total — but put it into the nose roll and edges, not the flat).
- Add **~100 tris for the underside cap** and **~70 tris per washer nozzle**.
- Doubling the skin to about 1,500 tris for a smoother nose-roll highlight would still be under 2 % of the LOD A budget.
- In LOD B the bonnet stays a separate `MOTORHOOD` part. Its share should be about 15 % of LOD A (about 100-150 tris).

### Gaps
- Non-Kunos sim titles (iRacing, ACC, GT7, Forza) publish no per-panel polygon figures that I could find.
