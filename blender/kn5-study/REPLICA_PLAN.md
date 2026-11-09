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
