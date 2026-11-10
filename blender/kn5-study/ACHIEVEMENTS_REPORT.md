# Blender Work project: what we've achieved (report, 2026-11-09)

The long-term goal is to build accurate Assetto Corsa cars from scratch (exterior, interior, everything)
from pictures and dimensions, for our own projects (Nova GTE, Sunbeam, Escort and future cars).

The route:
1. Reverse-engineer how professional AC cars are built.
2. Prove we can rebuild a car **when the original is available as a guide** (the "method test").
3. Then do it from photos.

Nik's rule: other cars are for learning technique only, never a base mesh or a shortcut.

Everything is in the private repo `nicklearse101-creator/Claude-`, folder `blender/kn5-study/`.
A cleaned copy is also published automatically to the public repo `claude-projects`.

---

## 1. How AC cars are built: 112 cars studied

**What we studied:**
- 112 cars: 67 Kunos, 29 mods, 12 single-seaters and open cars, 3 traffic cars, plus our own Nova.
- Every car was read straight from its game files with our own kn5 reader.
- Each was measured against published dimensions (Wikipedia specs, `specs.json`).
- Each was graded on construction: triangle budget, mesh grid, quads, symmetry, normals, UV and skin
  layout, LODs, dummies, panel gaps, and how lamps and grilles are made.

**Accuracy:**
- Kunos cars are within about 1 % of the real cars. Wheelbase is a median of 2 mm off.
- Mods are about 4× less accurate and use about 2× the triangles.

**The Kunos recipe:**
- **Body:** half the car is modelled and mirrored exactly. 89–94 % of faces are quads.
- **Painted shell:** 20–35k triangles on an 18–27 mm grid. Edge loops follow the car's features, not
  evenly spaced stations.
- **Shut lines:** about a 5 mm turned-in return with a 3–4 mm gap, darkened by ambient occlusion (AO)
  baked into a white skin texture.
- **Skin and texture:** one "unfolded car" texture sheet. The paint normal map is used only for damage.
- **Glass:** very low-poly. The door glass is 41 triangles; a separate "mask" mesh carries the black edge
  print.
- **Details:** lamps, grilles, badges and trims are separate meshes.
- **Single-seaters:** rigid suspension parts animated with `car_susp_XX` files.

**Our Nova block-out:** the dimensions are exact, but the construction fails the recipe. It has about
30× the triangles on the paint, no skin UVs and no LODs.

**Tools built (reusable on any car):**
- `kn5full.py`: the kn5 reader.
- `measure.py` and `compare_specs.py`: dimensions against published specs.
- `survey.py`: construction scorecard.
- `silhouette.py`: outline comparison.
- `section.py` and `construction_sheet.py`: cross-sections.
- `blender_import.py`: imports a car into Blender in about 3 seconds.
- Plus the phase-3 batch scripts.

Details: `KN5_STUDY.md`, `REPORT.md`, `REPORT_PHASE2.md`, `REPORT_PHASE3.md`.

## 2. What a replica needs: blind tests on the AE86

**Blind test from outlines** (`blind_test.py`): rebuild the Kunos AE86 from perfect side, top and
front outlines, then score it against the real surface.

| Built from | Median error | Within 10 mm |
|---|---|---|
| Outlines only | 8.5 mm | 56 % |
| + cross-section shapes learned from 11 other cars | 6.0 mm | 63 % |

Conclusion: outlines alone can never make a replica.

**How Kunos lays out a body (patch-layout study):**
- The shell is one mesh. Doors, bonnet, hatch and bumpers are separate meshes.
- Panel edges follow a recipe: a 5 mm return, then a 5 mm holding loop, then 10 mm.
- Loops run around the wheel arches and parallel to every edge.
- Triangle fans thin out the flat areas.

**Lines → surface** (`lines_to_surface.py`): keep only the real car's lines and fill the rest smoothly.
- Panel outlines plus creases plus soft feature lines plus a few sections give a 1.1 mm median, with
  87 % of the body within 3 mm.
- On 17 cars, outlines and creases alone gave a 0.65 mm median.

Conclusion: **a replica = accurate character lines + good surfaces between them.**

## 3. Approaches we tried and dropped (and why)

- **Smooth-fill generators** gave lumpy results, as Nik said they would ("smoothing has never worked").
  - Sectional loft from rays: 3.3 mm median.
  - Panel height fields.
  - Quad-sphere.
  - All dropped.
- **Pivot to CAD-style building:** curves first, then exact surfaces.
  - We researched how professionals model cars in Blender: `blender/research/Blender car modelling techniques.md`.
  - **FreeCAD 1.1.4** (OpenCASCADE CAD kernel) was found on Nik's PC and now runs headless from D: only
    (`fcrun.sh`; nothing touches C:).
- **Door tests:**
  - Coons and Gordon curve networks: about 1.7 mm. The Coons patch folded, which a one-way score hid.
  - Lofts.
- **Whole-car "strip" builds (v1–v5):**
  - The car was sliced into about 400 strips cut from the real mesh.
  - Numerically fine, but it looked patchy: slivers at joins, draped glass, no shut lines.
  - It also isn't how a modeller works, so it doesn't carry over to photos.
  - Two of our own errors surfaced during this work:
    - Our scorer added about 1 mm of fake error to every result. We replaced it with exact
      point-to-surface scoring (`score_exact.py`).
    - The v4 edge-cleaning step silently deleted 6 % of the car. We caught it and fixed it (v5 coverage
      is 91 % of the skin within 3 mm, with surfaces 0.11 mm median from the real skin).

## 4. The method that works: panel-fit CAD reverse engineering (the crisp door)

Full method: **`PANEL_FIT_TECHNIQUE.md`**. Code: `panel_fit.py` (fitting) and `panel_fit_freecad.py`
(CAD faces).

1. **Split the panel the way a modeller would:**
   - at hard creases;
   - along character lines found from cross-sections, each drawn as one fair curve from end to end;
   - strong rolls get their own narrow fillet band.
2. **Fit each surface as one smooth B-spline to the original's vertices.** The vertices lie on the
   designer's surface: the lower door skin fits to 0.09 mm.
   - The number of control points is the fewest that predicts held-out 40 mm patches best (blocked
     cross-validation).
   - That gives clean, even surfaces with no smoothing pass.
3. **Trim** each surface to the real panel outline in FreeCAD, then cut the bands **exactly on the
   shared character-line curve**. That's what makes the lines crisp.
4. **Display and export** use an even mesh with **exact surface normals**, which is how Kunos gets
   smooth reflections.
5. **Check** with zebra reflection stripes side by side against the original, plus exact two-way
   distances.

**Results:**
- **Glass:** 4 pieces, 20–40 control points each. The areas match the original (door glass 0.349 m²
  vs 0.349 m²) and every piece is within 3 mm. Image: `D:/Claude/_scratch_research/kn5_study/images/glass_panelfit_zebra.png`.
- **Door:** 8 faces (skin, crease band, groove, beltline roll, window frame). The areas match within
  1 %. The zebra stripes match the original and are as smooth or smoother.
  - Image: `D:/Claude/_scratch_research/kn5_study/images/door_panelfit_vs_original_zebra.png` (ours on the left; local only, it includes a render of the Kunos original).
  - Nik: "oh my god that's a really good door".

**Why it matters for photos:** the inputs are exactly what photos and blueprints provide: panel
outlines, character lines and a few sections per surface. The fit, trim and cut machinery stays the
same.

## 5. Other things set up this session

- **Public repo `claude-projects`:**
  - a cleaned mirror (emails, server addresses and decrypted game data removed);
  - refreshed automatically after every Claude turn by a Stop hook (`tools/publish_public.py --auto`);
  - it refuses to push if anything sensitive remains.
- **Steward app** (AC incident review for Ratty's Racing): a plan only, in `steward-app/PLAN.md`.
  Parked until later.

## 6. Lessons we paid for

- **Score exactly and both ways, and look in grey or zebra.** Point-sample scores and one-way scores
  both hid real problems.
- **Kunos uses long thin triangles,** so anything that classifies individual triangles comes out
  jagged. Work with curves and sections instead.
- **Fit to vertices, not facets,** and validate on held-out *patches*, not single points.
- **Never trim to a global smooth curve,** and never add "smoothing" as a fix.
- **Display meshes need even triangles plus exact normals,** or the zebra stripes tear.
- **Everything runs on D:** (FreeCAD via `fcrun.sh`, with temp folders on D:).

## 7. 10 November: door finished, front wing and rear quarter built

The panel-fit method went from "one good door skin" to three complete panels, checked after every change by
`regress.sh` (rebuild + score door, wing and quarter).

| Panel | Faces | Area within 1 / 3 mm | Kunos vertices within 1 / 3 mm |
|---|---|---|---|
| Door (with glass, mirror, trims) | 80 | 87.9 % / 99.6 % | - |
| Front wing | ~25 | 70.6 % / 96.1 % | 92.5 % / 99.3 % |
| Rear quarter + C-pillar | ~40 | 78.2 % / 96.8 % | 86.5 % / 97.9 % |

The vertex score is the honest one: Kunos's 100-150 mm flat triangles cut chords across curves, so a correct smooth
surface reads as "off" between vertices on the area score.

**What made it work**
- **Door:** every small face fitted (a missing 5 mm ledge read as a groove); rolled edges built as true blends from
  the neighbouring skin (tangent by construction) instead of fitted to sparse vertices; 5 mm shut-line returns.
- **Front wing:** the wheel arch found automatically on the outline; the lip built in its own "rail" coordinates
  along the whole opening edge and matched to the side faces; the wing split into sub-panels at the arch, as
  Class-A modellers do, so character lines run edge to edge; the fairest surface within tolerance, not the closest.
- **Rear quarter:** a panel that wraps a corner is cut once at 45 deg from its main direction; the minor piece is
  fitted against the finished main surface and both are cut on one smooth seam curve. Neighbouring bands are pinned
  to their shared character line (joins 0.1-0.4 mm), which also improved the door.
- **The hole filler was making things worse** in places: it took Kunos's chord sag for holes and laid a second, bad
  patch over a correct face. It now fills only real misses.

**Nik's verdict on the quarter's first build:** "really fast and produced a really good result".

**Next:** a thin-strip builder (narrow steps and returns as ruled surfaces between shared edge curves - the
quarter's lamp-top step is the first case), then the roof, bonnet, hatch, bumpers and sills.
