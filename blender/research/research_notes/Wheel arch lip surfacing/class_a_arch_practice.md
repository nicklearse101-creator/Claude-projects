# Class-A / CAD practice for a wheel arch with a flared or rolled lip

Scope: how professional surface modellers (Alias, ICEM Surf, CATIA ICEM Shape Design, Rhino) lay out and build a wheel arch on a front wing. Source quality is labelled on each finding: **[Primary doc]** = Autodesk / Dassault help pages; **[Tutorial]** = named practitioner tutorial blog; **[Forum]** = McNeel forum practice; **[Article]** = secondary blog/article.

Research date 2026-11-10. 15 tool calls. Wheel-arch-specific primary material exists for Alias (legacy help tutorial + rolled-edge tool docs). I found almost nothing wheel-arch-specific for ICEM Surf or CATIA ICEM Shape Design, and no published OEM flange dimensions.

---

## 1. Patch layout around the wheel opening

### Takeaway
The usual layout is a large, over-built **parent side surface** (body side / wing) that the arch opening is **trimmed** out of, a separate **arch / eyebrow surface** (in Alias, a rail surface or a "square" surface around the opening, plus an inner arch surface along the opening), and a **fillet/blend band** that bridges a deliberately trimmed **gap** between the two. The inner return goes on as a further flange surface, and the inside surfaces are deleted at the end. Sections and patch splits are placed **radially about the arch centre**, with a split at 12 o'clock, and are lined up with panel shut lines wherever possible.

### Cited Findings
- **[Primary doc]** Autodesk's Alias "Wheel Arch of a Car" tutorial opens by locating the arch centre: a circle in side view matched to the mesh arch, which is then used as the **pivot for the sections**. The inner arch is a **railed surface** built from a three-point arc fitted to the mesh plus two more curves closing the opening. The large arch curve is **projected onto the side panels**. Use "as few sections as possible, with one at the top (12 o'clock)", pivoting about the arch centre, and "where possible align sections with body-panel shut lines to hide tangency breaks". A railed **transition surface** is built between four curves. Continuity with the side panels comes first, and curvature continuity between the new surfaces can wait. Finally the "inside surfaces" are deleted, leaving the finished arch. — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)
- **[Primary doc]** The same page says to use shut lines to hide continuity problems (e.g. the door shut line on the front wing can carry a tangency break instead of forcing curvature), and to "always work to the centre of the shut lines". — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)
- **[Tutorial]** LearningAlias (front "eyebrow"):
  1. Project the curves for a **25 mm-wide wheel arch flange** onto the body side.
  2. Build the flange surface on the body side.
  3. Move the flange out to the line of the wheel's outer edge.
  4. Pull the top CVs so the flange runs vertical and lines up with the wheel.

  The author calls a more common alternative "build a **square surface** where the flange should go, then project inner and outer curves onto it". A **Tubular Surface** then cuts curves on both the arch and the body side. The intersected areas are trimmed away to leave a gap, and the gap is filled with **Free Form Fillet**. — [LearningAlias: Wheel Arch Blending](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- **[Tutorial]** LearningAlias (rear eyebrow carried onto the shoulder): build the arch as **one square surface deep enough to intersect both the body side and the shoulder**, intersect, trim all back, cut a gap with a tubular surface, and build the Free Form Fillet in **three pieces**. "Heavy CV pulling" was needed at the top of the arch. — [LearningAlias: Wheel Arch Blending](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- **[Tutorial]** LearningAlias "Wheel Arch Anti Tangent" (Kevin de Smet), on a production-style arch:
  - The parent body-side surface was modelled so that the trim edge and the patch's natural edge meet in an "anti-tangent" vertex (opposite directions, about a 10 degree tangent difference) inside a **clean four-sided UV structure**. The fillets were added along the theoretical style edge.
  - The alternative adds a small extra patch, which leaves a **five-sided gap** that someone filled with a power fill. The author prefers a **trimmed five-sided CV-built surface** for the top arch patch, so no power fill is needed.
  - Power fills give "forced G2" at the boundaries with an often uneven interior.

  — [LearningAlias: Wheel Arch Anti Tangent](https://blog.learningalias.co.uk/?p=4073)
- **[Forum]** McNeel forum (AlW): the wheel opening can be **trimmed from the basic shape**, or the **transverse sections can be arranged radially around it** and surfaced with a two-rail sweep or NetworkSrf. The **inboard flange can be a one-rail sweep joined to the basic shape**. Use as few curves and control points as possible, with consistent point counts and spacing across sections. — [McNeel: Approach to very curvy car fenders](https://discourse.mcneel.com/t/approach-to-very-curvy-car-fenders/35114)
- **[Forum]** McNeel (Pascal Golay, McNeel staff): trim into a **clean, over-built surface** that forms that side of the fender, and build the smaller surfaces to meet the big one, not the reverse. Bobi: build the main surface first, then add border/crease surfaces. A rounded surface needs a rounded border, and near-straight borders forced the main surface to be less smooth. — [McNeel: Srf match challenge unsolved](https://discourse.mcneel.com/t/srf-match-challenge-unsolved/98637)
- **[Article]** General Class-A layout rules:
  - Place boundaries only at real creases, split lines, shadow gaps or flow transitions.
  - Prefer few, long patches.
  - Keep U/V directions consistent across neighbouring patches.
  - Keep convergences 4-way and avoid 5+ way.
  - Route star points into occluded or low-reflection zones.
  - Avoid "accordion" layouts of many short patches, where highlights pulse at each seam.

  — [Novedge: Alias Patch Layout Mastery](https://novedge.com/blogs/design-news/alias-patch-layout-mastery-5-class-a-strategies-for-clean-highlights-stable-edits-and-engineering-ready-surfaces)

### Inferences
- A practical programmatic layout, synthesised from the above:
  1. **S0**: an untrimmed parent side surface, over-built past the opening.
  2. **S1**: an arch/eyebrow surface. This is a ring band, split into 2–3 spans along the arch (e.g. front-lower, top, rear-lower, with a split at 12 o'clock), parameterised radially about the arch centre: u runs along the arch, v runs across the lip.
  3. **F**: a fillet band between S0's trim edge and S1, built in 2–3 pieces matching S1's splits.
  4. **R**: an inner return flange, a one-rail sweep along the opening edge.

  Ends land on the sill/bumper split lines.
- Radial sections pivoting on one arch centre give every across-lip section the same orientation logic, which keeps parameterisation consistent along a curved rail.

### Gaps
- No primary ICEM Surf or CATIA document gives a wheel-arch-specific patch count. The "2–3 spans" figure is my inference from the Alias three-piece fillet, not a sourced rule.

---

## 2. Defining the opening outline and the lip feature line

### Takeaway
In Alias practice the arch outline starts as a **2D side-view curve** (an arc about the wheel centre, fitted to reference) that is **projected onto the side surface** to become a curve-on-surface. That curve is the trim line, the lip feature line, or the rail for the flange. Flange inner and outer curves are projected the same way. The flare is then pushed outward to the **tyre's outer face**, so the lip edge is placed relative to the wheel, not just the panel.

### Cited Findings
- **[Primary doc]** The arch is drawn with the three-point arc tool and fitted to the mesh, and the large arch curve is projected onto the side panels. The section and transition curves are projected onto the arch. — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)
- **[Tutorial]** The flange curves (25 mm wide) are projected onto the body side, and the flange is moved out to "where the wheel's outer edge will sit". — [LearningAlias: Wheel Arch Blending](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- **[Primary doc]** Alias rolled-edge tools take a **curve-on-surface, iso-parametric line or surface edge** as the input boundary. For Fillet Flange the input boundary "is kept as the finished component's specification": the fillet is built first to preserve the perimeter, and the flange is added afterwards. — [Alias 2024: Fillet Flange](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-6C6C9216-B6EB-4FAF-B8DA-D62CB5E5831B.html)
- **[Primary doc]** Tube Flange places a tube that touches the selected **contact line**, "where highlights change". The input line is therefore the highlight/feature line, not the cut edge. — [Alias 2015: Create rolled edge surfaces](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Modeling/files/Create_rolled_edge_surfaces.htm)
- **[Secondary]** A student fender project cites a European requirement of ≥10 mm fender-to-wheel clearance, checked against the wheel's outermost face. This is unverified, and the regulation text was not checked. — [Skill-Lync fender wheel arch challenge](https://skill-lync.com/student-projects/fender-design-wheel-arch-challenge-336)

### Inferences
- Two different lines are involved:
  - the **feature (highlight) line**, where Tube Flange's tube contacts the side surface, i.e. where the lip roll starts;
  - the **cut/opening edge**, which Fillet Flange preserves as the specification.

  Implementing both as curves-on-surface of S0 gives a stable lip width: the offset between them along the surface.
- I found no source that builds the outline as an offset of the tyre envelope. Practice is a side-view arc about the wheel centre plus a clearance check against the tyre's outer face.

### Gaps
- No source states a standard offset between the feature line and the opening edge, other than the LearningAlias 25 mm flange width.

---

## 3. Building the flare/lip: tools and methods

### Takeaway
There are three families of method:
- **(a) Rolled-edge tools** (Alias Tube Flange / Fillet Flange, ICEM Flange / Fillet+) build a constant- or variable-radius roll plus a straight flange in one operation.
- **(b) Build-and-blend**: an eyebrow/arch surface, an intersecting tubular cut to make a gap, then a free-form fillet/blend (Alias Free Form Fillet or Free Form Blend; Rhino BlendSrf or FilletSrf, then MatchSrf).
- **(c) Section sweeps**: radial sections along the arch rail (Alias Rail surface; Rhino Sweep2 or NetworkSrf), with the inboard flange as a one-rail sweep.

### Cited Findings
- **[Primary doc]** The Alias **rolled edge family** creates "both the flange and the surface fillet with a single tool".
  - **Tube Flange**: a tube touching the contact line plus a linear flange. The flange is set by **Sweep Angle** or **Parting Line** (vector + draft angle).
  - With **G1** continuity the tube has 360-degree sections that are trimmed. With **G2** the 360-degree section is removed and the tube runs between the contact line and the flange.
  - **Single surface** builds one combined surface. The other option splits the result at curve and surface boundaries.

  — [Alias 2015: Create rolled edge surfaces](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Modeling/files/Create_rolled_edge_surfaces.htm); [Alias 2024: Tube Flange](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-71AD4A98-9709-4696-97F6-551DE7BB72D5.html)
- **[Primary doc]** Alias **Fillet Flange** parameters:
  - **Wall** type: Draft (pull-direction vector) or Normal (90 degrees to the surface), with an optional angle.
  - The fillet is built against this temporary wall, then the flange comes off the fillet end, tangent to it.
  - Flange type: **Sweep Angle** (default 90 degrees) or **Parting Line** (default draft 0).
  - Flange **Length**, **Create Flange** on/off.
  - **Variable**: only ONE of Radius, Flange Length or Flange Angle may vary, set with manipulators along the rail.
  - **Shift Method**: Fillet Only (default) or Flange + Fillet fits the result inside the wall envelope.
  - Continuity can be tangent or curvature.
  - The docs describe the tool as useful for cut lines that need a set gap distance.

  — [Alias 2024: Fillet Flange](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-6C6C9216-B6EB-4FAF-B8DA-D62CB5E5831B.html); [Alias 2015: Create rolled edge surfaces](https://help.autodesk.com/cloudhelp/2015/ENU/Alias-Modeling/files/Create_rolled_edge_surfaces.htm)
- **[Primary doc]** In Alias's legacy wheel-arch tutorial, **transition curves should have curvature only at the body-panel end**, "because a fillet surface will be added to the outer section later". The transition surface is a **railed surface** between four curves, with surface settings that create curvature continuity to the body panel. — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)
- **[Tutorial]** The Tubular Surface → trim gap → **Free Form Fillet** sequence (see section 1). Too many CVs on the flange make it impossible to shape. — [LearningAlias: Wheel Arch Blending](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- **[Primary doc / vendor]** ICEM Surf has **Flanges** and **Fillet+** commands. Their references and parameters (flange length, angle) are stored and can be re-picked with "Pipettes" (ICEM Surf 2022+). — [3DS community: ICEM Surf Parametric Fillets and Flanges](https://3dswym.3dexperience.3ds.com/post/catia-creative-design-styling-user-community/icem-surf-tips-tricks-parametric-fillets-and-flanges_VUlQhlj9Q0G-CTYLnKj0xA). The ICEM Surf Advanced Tools module adds fillet types such as two chord lengths, 3 radii and true minimum radius. — [ICEM Surf 415 Advanced Tools spec sheet](https://www.3ds.com/fileadmin/PRODUCTS-SERVICES/CATIA/PDF/ICEM_Surf_415_Advanced_Tools_Spec_Sheet_K76.pdf)
- **[Forum]** Rhino:
  - **Jim Carruthers**: trim out a curve, then **BlendSrf** with **position continuity on the wheel side**. Bulge the original surfaces out first, so the blend has less work to do.
  - **Paul39**: follow with **MatchSrf**, or use **NetworkSrf** if you have clean curves, or a variable-radius **FilletSrf**.
  - **Martin Siegrist**: Rhino 8 FilletSrf offers Arc, Deformable (non-rational, G1, with a tangency slider; degrees 4–5 add a bulge slider) and G2 types.

  — [McNeel: Smooth transition to wheel arch](https://discourse.mcneel.com/t/smooth-transition-to-wheel-arch-how/205775)
- **[Article]** When BlendSrf struggles on complex trims, build **BlendCrv** sections between the edges and **Sweep2** with them as profiles. — [Novedge: BlendSrf workflow](https://novedge.com/blogs/design-news/rhino-3d-tip-blendsrf-workflow-for-smooth-surface-transitions)

### Inferences
- For code, the most direct analogue of the rolled-edge tools is:
  1. Take a rail curve-on-surface on S0 (the feature line).
  2. At each station, form a local frame: tangent along the rail, the S0 normal, and a wall vector (surface normal or a fixed pull/draft direction, e.g. inboard −Y with a draft angle).
  3. Sweep a circular or conic arc of radius r from tangent-to-S0 through the sweep angle (about 90 degrees for a turned-in lip).
  4. Extend a straight flange of length L tangent to the arc end.
- As in Alias, allow only one of r / L / angle to vary along the rail, interpolated between key stations. This is the "rolled lip". A flared lip is better built with method (b): eyebrow surface, gap, then a G2 blend.

### Gaps
- No primary ICEM Shape Design (CATIA V5) wheel-arch walkthrough was found. ICEM command names come from vendor community posts only.

---

## 4. Continuity targets, blend width along the arch, end conditions

### Takeaway
The target is **G2 (curvature) between the side surface and the lip blend** where the highlight must read as continuous. G3 is used in high-end work. **G1 is accepted** where geometry forbids G2, typically at the arch-to-rear-fender transition, and is hidden at shut lines. Blend size is usually **variable** along the arch: one parameter varies, driven by manipulators or key stations. Corners and ends are resolved by landing patch splits on **shut lines** (door, bumper, sill) and by avoiding power-fill N-sided patches.

### Cited Findings
- **[Primary doc]** Class-A baseline: tight tolerances for G0, G1 and G2, with **G3 often used** across patches for clean reflections. — [Autodesk: Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2019/ENU/Alias-Tutorials/files/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.htm)
- **[Tutorial]** Filleted intersection blends of this kind are described as requiring G3 (advanced). — [LearningAlias: Wheel Arch Blending](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- **[Primary doc]** Continuity with the side panels comes first. Shut lines (e.g. the front wing to door) can conceal a **tangency-only** break instead of forcing curvature. — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)
- **[Primary doc]** Rolled-edge fillets can be tangent or curvature continuous. Only one of radius, flange length or flange angle can be variable, with manipulators added along the rail (shift-click) for variable fillets. — [Alias 2024: Fillet Flange](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-6C6C9216-B6EB-4FAF-B8DA-D62CB5E5831B.html)
- **[Forum]** At a rear fender / wheel arch, the modeller targeted G1 because "curvature would not be possible due to the geometry of the wheel arch". MatchSrf gave poor zebras there. Raising U degree to 5 helps but is a workaround (Pascal Golay). — [McNeel: Srf match challenge unsolved](https://discourse.mcneel.com/t/srf-match-challenge-unsolved/98637)
- **[Forum]** BlendSrf with **G0 on the wheel side** is used for a quick arch transition. — [McNeel: Smooth transition to wheel arch](https://discourse.mcneel.com/t/smooth-transition-to-wheel-arch-how/205775)
- **[Article]** Use controlled G1 where an intentional edge is wanted and G2 where reflections must flow. Don't default to G2 everywhere. — [Novedge: Alias Patch Layout Mastery](https://novedge.com/blogs/design-news/alias-patch-layout-mastery-5-class-a-strategies-for-clean-highlights-stable-edits-and-engineering-ready-surfaces)
- **[Tutorial]** The top-of-arch corner is resolved with an "anti-tangent" vertex (about a 10 degree tangent difference) in a clean four-sided patch, or with a trimmed five-sided CV surface. Power fills (forced G2 at the edges, uneven interior) are avoided. — [LearningAlias: Wheel Arch Anti Tangent](https://blog.learningalias.co.uk/?p=4073)

### Inferences
- Implementation target:
  - **G2** side surface → lip blend.
  - **G1 or G2** blend → flange/return. In Alias, choosing G2 removes the full-circle tube, so the roll is a curvature-matched blend rather than a true arc.
  - **G0 + a gap** at sill/bumper split lines, where the arch band simply ends on the split plane.
- Vary the roll radius smoothly: larger at the top (more visible) and tapering toward the ends, or constant for a simple rolled lip. The sources show variable radius is standard but give no specific taper law.

### Gaps
- No source gives a numeric blend-width law along the arch, or typical radii for a production wheel-arch lip roll.

---

## 5. The inward flange/return and the wheelhouse

### Takeaway
The return is a **flange off the end of the roll**: a straight ruled extension tangent to the fillet end, set by sweep angle (about 90 degrees, i.e. turned inboard) or by a parting/draft vector, with a set length. In Rhino practice it is a one-rail sweep along the opening edge. Physically, the outer skin's inner lip is joined (welded or hemmed and sealed) to the inner wheelhouse. In CAD the inside surfaces are often deleted, leaving only the visible arch.

### Cited Findings
- **[Primary doc]** Flange via **Sweep Angle** (default 90 degrees), or **Parting Line** (the fillet is rotated until its end tangent matches a pull vector, with a draft angle default of 0). **Length** is set explicitly. With Draft wall + Parting Line flange, two pull directions are needed. — [Alias 2024: Fillet Flange](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-6C6C9216-B6EB-4FAF-B8DA-D62CB5E5831B.html)
- **[Forum]** The inboard flange can be a one-rail sweep joined to the basic shape. — [McNeel: Approach to very curvy car fenders](https://discourse.mcneel.com/t/approach-to-very-curvy-car-fenders/35114)
- **[Primary doc]** The inside surfaces are deleted at the end of the wheel-arch build. — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)
- **[Secondary/enthusiast]** Real arches have an inner lip where the outer sheet meets the inner wheel well, typically welded and sealed, in an **L shape**. "Rolling" turns it into a tighter V or flat U to gain tyre clearance. — [Apex Wheels: Will you need rolled fenders?](https://apexwheels.com/blog/technical-discussion/tech-article-will-you-need-rolled-fenders)

### Inferences
- For a game or AC-style mesh, an L-section return of roughly 10–25 mm, turned about 90 degrees inboard and running parallel to the wheel axis (draft vector = car Y), is consistent with the 25 mm flange in the LearningAlias tutorial and with the L-lip description. **Treat these numbers as inference, not a sourced OEM standard.**

### Gaps
- No source gives OEM flange depth, angle or hem radius for wheel-arch returns. The searches turned up only enthusiast articles on fender rolling.

---

## 6. Common pitfalls

### Takeaway
The main failure modes are:
- too many CVs on the flange/lip, so it can't be shaped and ripples;
- crowded CVs at tight bends, so the outline distorts the shape;
- building small surfaces first and forcing the main surface to fit them;
- power-filled or N-sided patches at the arch top;
- twisted or inconsistent parameterisation on curved rails, including the Sweep2 bulge;
- forcing G2 where the geometry only allows G1.

### Cited Findings
- **[Tutorial]** "You don't want too many CV's on your flange." Carrying the eyebrow into the shoulder makes the flow hard, and the arch top needed heavy CV pulling. — [LearningAlias: Wheel Arch Blending](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- **[Forum]** Crowding control points at a sharp bend lets the outline distort the design shape, and zebras wiggle. Overly complex trimmed edges leave gaps that tolerance changes won't close. Build the main surface first. — [McNeel: Srf match challenge unsolved](https://discourse.mcneel.com/t/srf-match-challenge-unsolved/98637)
- **[Tutorial]** Power fills of five-sided gaps give forced G2 at the edges with an uneven interior. A trimmed CV-built five-sided patch or a four-sided anti-tangent layout is preferred. — [LearningAlias: Wheel Arch Anti Tangent](https://blog.learningalias.co.uk/?p=4073)
- **[Forum]** Sweep2 rotates and scales the profile to reach a farther rail, which can bulge the surface. — [McNeel: Sweep 2 rails bulge](https://discourse.mcneel.com/t/sweep-2-rails-bulge/27728)
- **[Article]** Keep rails fair and non-crossing, and refit rails and sections, for Sweep2. — [Novedge: Sections, rails and continuity](https://novedge.com/blogs/design-news/rhino-3d-tip-rhino-surfacing-sections-rails-and-continuity)
- **[Article]** Twisted parameterisation rotates highlights. Keep U/V consistent around convergences. Fix curvature spikes near convergences by rerouting or buffer patches, not by adding patches. Avoid 5+ way star points in hero views. — [Novedge: Alias Patch Layout Mastery](https://novedge.com/blogs/design-news/alias-patch-layout-mastery-5-class-a-strategies-for-clean-highlights-stable-edits-and-engineering-ready-surfaces)
- **[Primary doc]** If the mesh/scan highlights are poor, don't match it exactly. Check highlights over fit. — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)

### Inferences
- For programmatic sweeps around a near-semicircular arch:
  - Use a rotation-minimising or radial frame, the arch-centre pivot from the Alias tutorial, rather than a Frenet frame. This avoids twist at the 12 o'clock apex.
  - Sample the rail by arc length, not raw parameter.
  - Keep the number of section stations the same in every span.
  - Avoid a degenerate (collapsed-edge) patch at the arch top by splitting the band there rather than closing a patch to a point.

### Gaps
- No source explicitly discusses singular/collapsed patches at the arch top. The closest material is the anti-tangent vertex and five-sided patch discussion.
