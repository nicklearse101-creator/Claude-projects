# Replica plan: from "rough shape" to an accurate, usable car model (2026-11-09)

**Aim:** be able to construct an accurate AC car from scratch: exterior, interior and everything else.
- Existing models are used to learn techniques and to score our builds, never as a base mesh.
- The study must reverse-engineer **how** models are built, not just measure them.

## Where we are
- **Blind test (`blind_test.py`):** rebuild the Kunos AE86 from outlines plus dimensions, then score it against the real surface.
  - The outline-only build is the right rough shape, but blocky: about 8 mm median error and only 56 % of the surface within 10 mm.
  - Outlines can't carry character lines, section shapes or glasshouse curvature.
- **Construction numbers** are known from 112 cars (budget, grid, quads, normals, UVs, LODs). The rules for building good surfaces are not.

## How professionals build a car body
1. **Character-line network:** 3D curves for beltline, shoulder, A/B/C pillars, roof edge, arch lips, shut lines and bumper edges, traced from blueprints and photos.
2. **Patch layout:** a quad layout over the curves, with loops along every line and poles (3- and 5-edge vertices) placed on purpose.
3. **Surfaces:** each patch filled smoothly (a subdivided cage), then refined until the reflections flow.
4. **Panels and details:** shut lines as about 5 mm returns, lamps, grilles, trims and badges as separate parts, glass in two layers.
5. **Interior, then game features:** LODs, dummies, UVs and the AO-baked skin.

## Steps
| # | Step | Output | Done when |
|---|---|---|---|
| 1 | **Patch layout + character lines** extracted from Kunos bodies (AE86 first, then 2–3 others) | poles, loop structure, patch count, line network; shown in Blender | we can describe and draw the modeller's surface plan for each car |
| 2 | **Lines → surface experiment:** keep only the line network of the true AE86, fill the rest smoothly, score with the blind-test metric | error versus how many lines are used | we know which lines a replica needs, and the accuracy they give |
| 3 | **Rebuild the AE86 from lines + outlines,** first with lines taken from the model (method test), then with lines traced from pictures (real job) | a quad body built by our generator | median ≤ 3 mm, ≥ 90 % within 10 mm; clean reflection lines |
| 4 | **Interior survey and recipes:** parts list, triangle budget, modelled vs texture-only, baked AO, detail maps | interior recipe | an interior budget and method for our cars |
| 5 | **Build from photos:** camera match, overlay checks with the skin-generator renderer, photos projected onto the model, reflection-line checks | Nova/Sunbeam bodies built this way | passes the blind-test metric on a car with known truth first |

## Analysis tools still to build
- **`patch_layout.py`:** quads, poles, edge-loop tracing, patch decomposition, character lines (creases, ridges, boundaries).
- **`lines_to_surface.py`:** fixed character-line vertices plus a smooth (bi-Laplacian) fill, then a score.
- **Reflection-line render** of any mesh (stripes of light) to judge surface quality the way designers do.
- **Photo overlay and projection,** reusing the skin generator's texel map and renderer.

---

## Results so far (2026-11-09)

### Blind test, Kunos AE86, ideal orthographic outlines (`blind_test.py`)
The score is distance to the true outer skin, every 10 mm along the car. Wheel wells and the underbody are excluded as hidden.

| Build method | Median | Worst 10 % | Within 10 mm |
|---|---|---|---|
| Outlines only (visual hull: side, top, front) | 8.5 mm | 48 mm | 56 % |
| + top-view lines (plan above beltline and roof rail) (`m_lines.py`) | 6.7 mm | 48 mm | 58 % |
| + section shapes learned from 11 other Kunos cars, applied blind (`m_prior.py`) | 6.0 mm | 39 mm | 63 % |
| Corner rounding (`m_round.py`) | worse: eats sills and valances | | dropped |

- **Outline-only builds on 11 other Kunos cars:** median 9–15 mm, 41–55 % within 10 mm.
- **Conclusion:** outlines, even ideal ones, cannot make a replica. Learned section shapes help a little.

### Step 1: how Kunos lays out a body (AE86; Blender view `AE86_layout_view`)
- **Panels:**
  - one mesh for the shell (roof, pillars, quarters, wings, tail)
  - separate meshes for the doors, bonnet, hatch and bumpers
- **Panel-edge recipe** (median spacing going inwards from the edge):
  - Body and doors: boundary → 5 mm turned-in return → 5 mm holding loop → 10 mm → main grid.
  - Bumpers: a deeper return of about 20 mm, then a 3 mm holding loop.
- **Triangles:**
  - Clean quad rebuilding tops out at 90–93 %. The remaining triangles are real and are the modeller's density changes.
  - They sit on the flatter areas (median bend 11°), while quads carry the curved areas (median 21°).
  - In other words: clean loops on features, triangle fans to thin out flat areas.
- **Loop flow:**
  - concentric loops around the wheel arches
  - loops parallel to every panel edge
  - a coarse regular grid on the roof that tightens towards its edges
  - corner joins at panel corners and pillar bases

### Step 2: lines → surface (`lines_to_surface.py`)
The true AE86 panels are kept only on the chosen lines; every other vertex is rebuilt as the smoothest (thin-plate) surface through those lines.

| Lines kept | Body: median | Body: within 3 mm | Door: within 3 mm | Bumpers: within 3 mm |
|---|---|---|---|---|
| panel outlines | 7.9 mm | 24 % | 18 % | 13–19 % |
| + sharp creases (> 30°) | 2.3 mm | 59 % | 73 % | 46–50 % |
| + soft feature lines (> 12°) | 1.5 mm | 81 % | 93 % | 84–85 % |
| + sections every 400 mm | **1.1 mm** | **87 %** | **98 %** | 84–85 % |

- **A plain grid is less efficient:** sections and waterlines every 400 mm, with no character lines, gives only 54 % of the body within 3 mm. A grid every 100 mm is needed to reach about 80 %.
- **Conclusion:** a replica needs about 2 mm accuracy on the character lines (outlines, creases, soft feature lines) plus a few sections. Smooth surfaces between them then land within 1–3 mm.
  - So the job is: **get those lines right from the references, then fill smooth quad patches between them.**
  - This is exactly the professional curve-network workflow.

### Next
- **Step 3:** rebuild the AE86 from lines + outlines.
  - First with the lines taken from the model, to test the generator: quad patches, panel-edge recipe, thin-plate fill.
  - Then with lines traced from pictures.
- Steps 4 and 5 as above.

### Step 3, first try: our own mesh, a sectional loft (`step3_rebuild.py`)
- **Mesh:** our own quad mesh, one ring of 160 rays every 20 mm along the car (33k quads).
- **Starting shape:** the best outline build (`m_prior`), smoothed.
- **Lines from the true model:**
  - creases over 12° on the outer skin
  - window outlines
  - full sections every 400 mm, pinned along each ring's own rays
- **Fill:** the smoothest surface through the pins, with a weak pull to the outline build.
- **Score:** each ring against the true outer outline at its station.

| Lines used | Median | Worst 10 % | Within 3 mm | Within 10 mm |
|---|---|---|---|---|
| none (outline build only) | 6.3 mm | 30 mm | 28 % | 64 % |
| sections only | 5.3 | 35 | 36 | 65 |
| creases + window outlines | 4.0 | 22 | 40 | 80 |
| **all** | **3.3** | **19** | **47** | **82** |

Soft pins (strength 0.01–0.3) were no better; a weaker pull to the outline build was worse.

**What stops it reaching the 1.1 mm that Kunos's own layout gets from the same lines (step 2):**
1. **Ends:** a lengthwise loft can't make the near-vertical front and rear faces. Rays converge into star-shaped artefacts there. Kunos makes the ends as separate panels: the bumpers and the tail panel.
2. **Loops don't follow the lines:** lines land on scattered ring vertices and pull out dimples. In Kunos meshes, edge loops run along every line, so a line is a continuous loop and not a set of pins.
3. **Arches and openings:** the loft wraps straight over wheel arches and windows. Kunos cuts them out and runs concentric loops around them.

**Next generator (step 3, second try): patch based, like the professionals.**
- Split the body into panels, the way Kunos does: sides, roof, bonnet, boot or hatch, front and rear end panels and bumpers.
- Each panel is a quad patch whose **edge loops are the character lines** (curves resampled into loops) with a smooth fill inside.
- Arches and windows are boundaries with concentric loops.
- Then the panel-edge recipe: a 5 mm return, a 5 mm holding loop and a 10 mm loop.

### Step 3, second try: panel-based generator (`step3b_panels.py`)
- **Panels by facing direction:**
  - side `x=f(z,y)`, the left half built and mirrored, as Kunos does
  - top `y=f(z,x)`
  - front end `z=f(x,y)`
  - rear end `z=f(x,y)`
- **Mesh:** each panel is our own 10 mm quad grid. A cell belongs to a panel where its surface faces that way (slope under 45°). Arches are cut out.
- **Lines:** taken from the true model, drawn into each panel's grid.
- **Fill:** thin-plate, with a weak pull to the outline build.
- **Score:** 3D distance to the true outer skin, including the end faces.

| Generator | Median | Worst 10 % | Within 3 mm | Within 10 mm |
|---|---|---|---|---|
| panels, outline build only | 6.8 mm | 27 mm | 27 % | 62 % |
| panels + model lines (pull 0.002) | 3.9 | 18 | 41 | 79 |
| panels + model lines (pull 0.0001) | **3.5** | **14.5** | **45** | **83** |

| Panel (pull 0.002) | Median | Within 10 mm |
|---|---|---|
| side | 3.0 mm | 83 % |
| top | 3.1 mm | 78 % |
| front | 6.0 mm | 69 % |
| rear | 5.1 mm | 72 % |

**Still to fix:**
1. **Seams:** panels meet at a jagged 45° boundary. They need stitching into one mesh, or proper patch boundaries along the shoulder and end lines, as Kunos uses.
2. **Ripples:** lines are drawn as separate points, which leaves ripples. They should be drawn as continuous polylines and used as edge loops.
3. **Ends:** the pop-up lamps, grille and tail recesses aren't modelled. These are detail parts, built as separate meshes like Kunos.
4. **Panel-edge recipe** (5 mm return and holding loops) and the separate panel meshes: not yet added.
5. **Scoring gap:** the score only looks from our surface to the truth. It should also check the other way, true skin to our surface, so coverage holes count.

### Step 3, third try, and a change of technique (2026-11-09 afternoon)
- **Quad-sphere generator (`step3c_quadsphere.py`):** one seamless quad mesh fitted with thin-plate smoothing.
  - It removed the seams: 2.9 mm median, 51 % within 3 mm.
  - It still looks lumpy: ripples and terraces, and ribs on the tail.
- **Panel generator re-scored** with the fair dense-skin metric: 2.4 mm median, 60 % within 3 mm, 86 % within 10 mm. It still has seams and ripples.
- **Nik's verdict:** smoothing-based building never gives crisp edges or flat surfaces. **Agreed, and dropped.** Every method so far was "rough blob, then smooth towards the lines".
- **New technique, CAD/professional surfacing:** curves first, then patches computed exactly from their curves.
  - **Coons patch** (4 edge curves, `coons_test.py`): it can't bulge beyond its own edges. The AE86 door skin bows out about 70 mm past its tucked-in edges, so Coons alone fails.
  - **Gordon surface** (edge curves plus sections across the panel, `gordon.py`):
    - The door skin as 2 patches split at the body-side crease, each with 5 waterlines × 5 verticals.
    - **2.3 mm median, worst 10 % 3.7 mm, 87 % within 3 mm.** Nothing is smoothed, and the surface passes exactly through every curve.
  - **Not yet robust:** results swing with network density, and the trimmed mesh had holes. The causes were my numpy curve tracing and trimming, where sections ran past the panel outline, not the method.
- **Lesson on scoring:** always score both ways (truth → build and build → truth) and look in grey. A folded Coons patch scored "3 mm" one way and was garbage.

**Next: build in Blender itself with native patch tools instead of numpy height fields.**
- Clean Bezier curves per panel: outline, crease and sections. These are traced; in the method test they come from the model.
- Resample each curve to a matching point count, then loft or Bridge Edge Loops through the sections, so edge loops lie exactly on the curves.
- Panel edges as their own loops, with the 5 mm return and holding loops.
- Score both ways and check in grey after every panel.
