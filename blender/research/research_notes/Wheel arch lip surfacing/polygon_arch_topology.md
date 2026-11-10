# Polygon / subdivision wheel arch topology (flared or rolled lip, crisp arch, clean reflections)

Overall note on the sources: there is very little written, specific, authoritative material on this. Most of it is forum posts (Polycount, Blender Artists), course teasers whose detail is in video, and a NURBS (Alias) tutorial. Several key pages could not be fetched (3dmodels.org/Hum3D car tutorial part 3 and Polycount comment pages returned 403), so their content is known only from search snippets. The richest specific numbers come from Nik's own reverse-engineering of Kunos kn5 files (local file `D:\Claude\Claude-\blender\kn5-study\KN5_STUDY.md`). That is first-hand measurement of real shipped AC cars, not a web source, and it is labelled as such below.

## 1. What edge flow do professional car modellers use around a wheel arch?

### Takeaway
The consensus is concentric loops that run all the way round the arch opening, parallel to the lip, with the rest of the side surface's grid ending on them. Radial spokes (fans) appear only in low-poly or older game workflows. Poles and triangles are pushed away from the arch edge, onto flatter panel areas. Kunos cars show the same pattern: an even grid, with 2–3 tight parallel loops on each feature line, the arch lip included.

### Cited Findings
- Polycount advice: "make the topology a full loop around wheel arches and round elements," even when the part is a separate piece, so reflections stay consistent (single forum reply; known from a search snippet, page 403) — [Polycount comment 2703491](https://polycount.com/discussion/comment/2703491/)
- Practitioner advice in the same thread: keep loops in line with the design's natural lines (wheel arches, door cuts), and break the topology at seams the way real panels separate. The OP called keeping consistent edge flow on the wheel arches the main struggle (snippet only) — [Polycount comment 2703491](https://polycount.com/discussion/comment/2703491/)
- Density: loops inside the arches "can be scaled down to give more resolution where you need it but don't go overboard"; another critique said wheel wells "need a few more segments as they look a bit too lowpoly and jagged" (forum critiques, snippets) — [Polycount search results](https://polycount.com/discussion/comment/2704062)
- A Polycount critique flagged "a couple of tris on the front wheel-well" because they interrupt lines that continue towards the rear arch (single comment, snippet) — [Polycount](https://polycount.com/discussion/comment/1809496)
- Blender Artists (JA12): "Put the poles away from edges" (single post) — [Blender Artists: Car rim topology problem](https://blenderartists.org/t/car-rim-topology-problem/619004)
- Blender Artists: odd vertex counts round a circle cause trouble; a six-sided circle was suggested near the headlight (single post, snippet) — [Blender Artists: 1963 Aston Martin DB5](https://blenderartists.org/t/1963-aston-martin-db5/641603)
- CG Cookie course feedback: "the wheel well shape could be achieved with less edge loops." Over-dense base meshes are a common mistake (instructor reply, snippet) — [CG Cookie class page](https://blog.cgcookie.com/?p=35510)
- General pole rules (Polycount-hosted subdivision guide): avoid 6-edge poles, which pinch. 3-edge and 5+-edge poles cause density differences that can pinch, so keep them out of curving or deforming regions — [SubdivisionModeling.com "The Pole" PDF (Polycount wiki)](http://wiki.polycount.com/w/images/4/43/SubdivisionModelingDotCom_The-Pole.pdf); [CG Cookie topology guide](https://blog.cgcookie.com/posts/the-art-of-good-topology-blender/)
- Kunos measurement (Nik's kn5 study, local): loops follow features, not stations. Only 13–28 % of edges lie on constant x/y/z planes, and loops run along shut lines, swage lines, arch lips and window frames "with 2–3 tight parallel loops on each feature." The grid is even at about 20 mm (AE86) whatever the curvature, and about 40 mm on flat roof panels — local file `D:\Claude\Claude-\blender\kn5-study\KN5_STUDY.md` §4
- The local kn5 study also records "concentric loops around the wheel arches" on Kunos cars, and that a loft "wraps straight over wheel arches… Kunos cuts them out and runs concentric loops around them" — local file `D:\Claude\Claude-\blender\kn5-study\REPLICA_PLAN.md`

### Inferences
- The working pattern is two to three concentric rings following the opening (lip edge, a support or turn ring, and a ring out on the side surface). The side-surface grid lines that hit the arch turn and run parallel to it, or end on the outer ring through a 5-pole placed a couple of rings away from the lip.
- An even vertex count round the opening, and matching counts between rings, avoid stray tris.

### Gaps
- No written source gives a recommended number of segments round the arch for a subdivision cage. The "32-vertex circle" figure comes from one AI-summarised course listing and is not confirmed (see section 3).
- No source with diagrams on termination patterns (exactly where the 5-poles go) could be fetched. The advice exists mostly as images in forum threads.

## 2. How is the lip or flare made, and what are typical widths and depths?

### Takeaway
In polygon work the lip is a feature-line ring on the shell. The edge rolls or turns inward and continues as an inner flange or liner, and is kept crisp by tight parallel loops (or creases or solidify rim creases in Blender), not by hard edges. Flares and box arches are modelled as part of the same shell grid, with an extra loop at the lip and another at the turn-under. Real numeric widths in sources are scarce: a 25 mm flange (Alias tutorial), and roughly 5 mm panel returns with a 3–4 mm gap on Kunos cars.

### Cited Findings
- Kunos measurement (local kn5 study): "Lip rolls inward and continues as a liner. Flares and box arches are part of the shell grid, with an extra loop at the lip and the turn-under" — local `KN5_STUDY.md` §5; also "Edges roll back at arches and openings: the arch lip turns inward and a liner continues it" — local `REPORT.md`
- Kunos crispness: hard edges are rare on 2016+ Kunos cars (3–7 % of edges), against 20–37 % on mods, which "look faceted". Normals are plain averages with no weighted-normal trick, so crispness comes from tight loops — local `KN5_STUDY.md` §4
- Alias (NURBS) tutorial: "projecting curves for the 25mm wide wheel arch flange onto the body side," building a flange surface, then moving it out to the wheel's outer edge. CVs on top of the flange were pulled so it stands vertical and lines up with the wheel. Too many CVs make the shape hard to pull out — [Learning Alias: Wheel Arch Blending](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- Same tutorial: the arch is blended into the body with a tubular surface, trimmed, and the gap filled with a free-form fillet. The rear arch that runs up onto the shoulder is a "very tricky surface flow challenge" — [Learning Alias](https://blog.learningalias.co.uk/2010/02/24/autodesk-alias-building-a-car-body/)
- Crease control by loop spacing (general): add one loop each side of an edge and move them closer to sharpen it, further apart to soften it — [Pluralsight: 10 Tips for Automotive Modeling](https://www.pluralsight.com/resources/blog/software-development/0-stunning-10-tips-automotive-modeling)
- Blender Solidify plus Subsurf for a rim lip: put Solidify before Subdivision Surface and set Rim Crease to 1.0, so the rim loop stays sharp. Even Thickness keeps the wall uniform at sharp angles (generic lesson, not car-specific) — [Varsity Tutors: Solidify modifier lesson](https://www.varsitytutors.com/practice/subjects/blender/lessons/use-solidify-modifier-for-thickness-and-shell-like-forms-intro)
- Blender Artists (pauljs75): model the wheel-well opening larger than needed, select the edges round the inside, extrude, and scale them inward. This gives a loop round the opening that subdivides cleanly. This is the polygon equivalent of a turned-in flange (single post) — [Blender Artists: Car rim topology problem](https://blenderartists.org/t/car-rim-topology-problem/619004)
- Panel cut add-on documentation (snippet only): panel lines "should have at least TWO polygons between them." Support loops come from bevel weights plus a Bevel modifier — [hodgson3d Gumroad](https://hodgson3d.gumroad.com/l/synrie) (the fetched page held only a title, so this is unverified)
- One GitHub README (surfacing-lab/Blender-modeller) claims that on its body the arch crowned at 0.702 with support loops either side of every hard line and 0.703 without, for 2.6x the faces. It recommends creases, and says the lower rings must drop past the arch lip or the surface folds back. This is a single, unverified author's measurement — [GitHub surfacing-lab/Blender-modeller](https://github.com/surfacing-lab/Blender-modeller)
- Forum critique: thicken the panel above the front arch to give the arch more presence (snippet) — [Polycount](https://polycount.com/discussion/comment/2709268)

### Inferences
- A practical recipe from these sources: lip ring, then one tight support ring 1–3 mm away on the outer face, then a turn-under ring, then the inner flange or liner going 20–40 mm inward. The flange depth is inferred from the 25 mm Alias flange and is not a measured polygon figure.
- For sim cars, a rolled lip can be cheap: it is the shell's open edge turned in, not a separate thick solid.

### Gaps
- No source gives a typical lip radius or flare outward offset in mm for polygon models.
- No measured inner-flange depth was found for Kunos cars. It could be measured from kn5s with the existing tools (`section.py` and `construction_sheet.py` already show the arch lip).

## 3. How is the arch outline usually established?

### Takeaway
The arch outline is taken from the side-view blueprint, centred on the wheel centre. It is built either by starting from a circle primitive and connecting the body to it, or by building the opening oversized and pulling it in. Booleans are generally discouraged, or used only late, because they wreck subdivision topology. Shrinkwrapping the cage to a reference surface is the common Blender way to cut openings without pinching.

### Cited Findings
- Start the wheel house with a circle, connect the other vertices to it, and avoid booleans (Matthias Püski guide, snippet; page not fetched) — search result for [Scribd: Blender Car modeling](https://www.scribd.com/document/441359547/Blender-Car-modeling)
- A course summary says to apply subsurf to wheel-well contours, use a 32-vertex circle, and align to blueprints "for smooth topology and better shrinkwrapping." This came from a search-engine summary, likely the Lynda/LinkedIn course "Blender: Vehicle Modeling – Adding detail to the front fender", and is not verified on the page — [Lynda: Blender Vehicle Modeling](https://www.lynda.com/Blender-tutorials/Adding-detail-front-fender/180810/363893-4.html)
- Cutting arches with booleans on uneven topology causes problems; apply them only when the mesh is ready (snippet) — [Polycount](https://polycount.com/discussion/comment/2703491/)
- BlenderNation car-modelling tip: "to create holes we use a Shrinkwrap modifier to avoid pinching issues" (detail is in the video) — [BlenderNation: Car Modeling Basics part 3](https://www.blendernation.com/2020/06/15/daily-blender-tip-car-modeling-basics-part-3/)
- Blender Artists post on advanced subsurf techniques to avoid pinching calls shrinkwrap "the magical shrinkwrap modifier" for curvature without distortion (settings not given in text) — [Blender Artists](https://blenderartists.org/t/advanced-subsurf-modeling-techniques-to-avoid-pinching/690739)
- Alias: use the centre of the wheel arch as the pivot, and use the body panel shut lines to hide tangency breaks (snippet from an Autodesk help page) — [Autodesk Alias help: Wheel Arch of a Car](https://help.autodesk.com/cloudhelp/2014/ENU/Alias/files/GUID-545A5B42-8EC5-479D-9739-6C4ACE21DE2B.htm)
- Old game workflow (ZModeler): build a face fan with as many vertices as the wheel-well outline, move the centre vertices to the tyre on the blueprint, and weld to the body. A flat wall stand-in can leave visible gaps — [ETSPE ZModeler tutorial: wheel wells](https://www.etspe.ca/zmt/v2/wwells.html)
- Pluralsight: block wheel wells out with simple primitive shapes, then bridge the two wheel wells to create the side panel between them — [Pluralsight](https://www.pluralsight.com/resources/blog/software-development/0-stunning-10-tips-automotive-modeling)
- A paid Blender Geometry Nodes "Parametric Wheel Arch modifier" moves existing points into an even, customisable arch shape. It "relies on the underlying topology" and does not create new faces — [80.lv](https://80.lv/articles/this-blender-tools-lets-you-create-perfect-wheel-arches); [Gumroad](https://martinlorentzon.gumroad.com/l/parametric-wheel-arch)

### Inferences
- Robust Blender route: a circle (even count, for example 24–32) at the wheel centre in side view, trimmed to the arch angle range, as the lip ring. Bridge the side grid to it. Shrinkwrap the cage (not the lip ring) to a smooth reference body, then relax the rings (LoopTools Relax was suggested by pauljs75) — [Blender Artists](https://blenderartists.org/t/car-rim-topology-problem/619004).

### Gaps
- None of the fetchable sources gives shrinkwrap settings (mode, offset, vertex-group masking of the lip).

## 4. How do they avoid pinching and wobbly reflections round the arch?

### Takeaway
Keep the rings continuous and evenly spaced, keep poles and triangles off the arch and lip, use as few control loops as will hold the shape (dense cages wobble), relax the rings, and shrinkwrap to a smooth reference. Kunos does not use custom or weighted normals. Clean reflections come from an even quad grid and tight loops, with plain averaged normals.

### Cited Findings
- Full loops round arches help keep reflections consistent (snippet) — [Polycount](https://polycount.com/discussion/comment/2703491/)
- Poles away from edges; LoopTools Relax to spread edges evenly round a curve; "there's tension too" on subdivided curves — [Blender Artists](https://blenderartists.org/t/car-rim-topology-problem/619004)
- Shrinkwrap to avoid pinching on holes — [BlenderNation](https://www.blendernation.com/2020/06/15/daily-blender-tip-car-modeling-basics-part-3/); [Blender Artists](https://blenderartists.org/t/advanced-subsurf-modeling-techniques-to-avoid-pinching/690739)
- Pole density differences cause pinching; avoid 6-poles — [Polycount wiki PDF](http://wiki.polycount.com/w/images/4/43/SubdivisionModelingDotCom_The-Pole.pdf)
- Run a smooth preview first; if it looks fine, ngons may not need fixing — [Pluralsight](https://www.pluralsight.com/resources/blog/software-development/0-stunning-10-tips-automotive-modeling)
- Kunos: normals are plain averages with no weighted-normal trick on any car; hard edges are 3–7 % of edges; quad-modelled and triangulated on export, with 89–94 % of tris pairing back into quads — local `KN5_STUDY.md` §4

### Inferences
- Wobble usually comes from uneven ring spacing or a pole on the lip. Fix it by relaxing the rings, moving 5-poles out onto the flat flank, and keeping matching vertex counts between rings.

### Gaps
- No written source covers custom-normal transfer (Data Transfer from a smooth proxy) for car arches specifically. It is a known game-art technique but was not found sourced for arches here.

## 5. Game and sim notes (Assetto Corsa / Kunos): budget, inner wheelhouse, LODs

### Takeaway
There is no official Kunos triangle cap. The evidence is Nik's measurements plus forum rules of thumb. Painted shell about 20–35k tris with edges 18–27 mm apart, whole car 120k–275k tris, LOD B/C/D about 15 % / 4 % / 1 %. Arch lips roll in and continue as a liner. Panel gaps are mostly baked AO lines rather than deep geometry.

### Cited Findings
- Kunos budget (local kn5 study): whole car 120k–275k tris; painted shell about 20–35k with edges 18–27 mm apart and 1,600–3,600 tris/m²; interiors and wheels take most of the budget; LOD B/C/D about 15 % / 4 % / 1 % — local `KN5_STUDY.md` §4
- Shut lines on Kunos cars: about 5 mm returns on both panels, a 3–4 mm gap, and a dark line baked into the skin and gloss maps. The paint normal map is only for damage dents — local `KN5_STUDY.md` §4–5
- Paint atlas: flanks side-on with arches laid out as strips — local `KN5_STUDY.md` §4
- Kunos' informal guidance, as reported on RaceDepartment: more objects means lower performance; rule of thumb under 200 objects for LOD_A plus the HR cockpit, LOD_B about a quarter; LOD_A kn5 under 50 MB; example mod 257k tris and 215 objects (forum poster) — [RaceDepartment DRM Revival thread](https://www.racedepartment.com/threads/drm-revival-paid.149302/page-23)
- A Kunos mod guideline ships in the SDK dev folder; "It's not a formal rule, but it helps." LOD C minimal, LOD D near a placeholder, LOD B hardest to get right (forum poster) — [GTPlanet AC mods thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4477)
- Wheels often sit too deep in the arch; they should sit inside the arch, not flush, with slight camber (forum critique, snippet) — [Polycount](https://polycount.com/discussion/comment/2711261)
- General game-car LOD figures (88Cars3D, for undercarriage only, internally inconsistent): LOD0 100–150k, LOD1 30–50k, LOD2 5–10k polys — [88Cars3D](https://88cars3d.com/2026/01/03/foundational-modeling-precision-topology-for-undercarriage-components-2/) (low reliability)

### Inferences
- At an 18–27 mm shell grid, a 600–700 mm diameter arch opening would carry roughly 50–80 edges round its half-circumference before the 2–3 feature loops. This is an estimate from the Kunos spacing, not a measured arch count.
- The inner wheelhouse in AC is cheap. The rolled lip continues as a simple liner, and the deep wheelhouse is usually dark and low-poly.

### Gaps
- No measured per-arch triangle count or liner depth for Kunos cars. Both are measurable with the existing kn5 tools in `D:\Claude\Claude-\blender\kn5-study\`.
- The Kunos SDK mod guideline document itself was not found online, so its contents are unverified.
