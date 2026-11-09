# How AC car models are made: reverse-engineered from two cars (2026-11-09)

Part of the Blender work project (`blender/`). Goal: learn how professional Assetto Corsa cars are built,
measure it, and turn it into rules and checks for our own model generation (Nova, Sunbeam, Escort).

- **Main study:** Kunos `ks_toyota_ae86`. This is the professional standard: 1980s car, made by Kunos.
- **Check model:** `Peugeot_205_EVO1_GrB`. Community mod, 1980s hatch, the closest in type to the Nova.
- **Our own model:** the installed `vauxhall_nova_gte_1989` measured the same way. This is the old 20 Oct
  block-out, not the current FreeCAD/section body.

Everything here was **measured from the kn5 files**, or seen in Blender after importing with
`blender_import.py`. Study blend (not in git, contains game assets):
`D:\Claude\_scratch_research\kn5_study\kn5_study_AE86_vs_205.blend`. Per-mesh CSVs, trees and images are
in the same folder.

## 1. Headline numbers

| | Kunos AE86 | 205 Group B mod | Our Nova (installed block-out) |
|---|---|---|---|
| Main kn5 triangles | **242k** | 119k | **1.44M** |
| Painted shell triangles | ~28k (body 12k, doors 3.4k each, bumpers 3.8k each, roof 1.9k) | ~15k | ~370k (paint_gunmetal parts) |
| Body edge length (median) | **20 mm** (roof/flat areas 40 mm) | 35–75 mm | **5–7 mm** |
| Body triangles per m² | 2.7–3.5k | 0.5–1.9k | 25–80k |
| Paired back into quads | **88–91 %** | 86–91 % | not measured |
| Hard (split-normal) edges on body | 88 of 17k (0.5 %) | 794 of 4.3k (18 %) | ~1.5 % |
| Sliver triangles (<5° angle) | 23 % of paint tris (thin quads in tight loops, normal) | 28 % | 2 % |
| Materials / textures | 46 / 62, 30 MB | 43 / 52, 85 MB | 28 / 56, 0.1 MB |
| LODs | A 242k, B 54k (22 %), C 16k (7 %), D 216 | none | none |
| Body texel density | 460–490 px/m (2048² paint atlas) | 530–880 px/m (4096² atlas) | ~4 px/m (flat colour) |

The Nova block-out has six times the triangles of a full Kunos car, mostly spent on noise. A Kunos-grade
shell is about **28k triangles of clean quads**.

## 2. How the Kunos car is built (the recipe)

### 2.1 Pipeline
- **Exported through FBX:** the root node is `FBX: toyota_ae86.fbx`, then converted in ksEditor, which
  splits objects with several materials into `_SUB0.._SUBn`. (Corrected in phase 2: the authoring package
  varies between Kunos cars, and the `polymsh_*` names on E30/MX5/Escort point to Softimage XSI.)
- **Quad modelling, triangulated only on export.** Re-pairing triangles (`join_triangles`, 30°/60°)
  gives back 88–91 % quads with clean, even edge flow.
- **Built as a half and mirrored** (corrected in phase 2): 98.5 % of body vertices have an exact mirror
  partner (`fairness.py`). The UVs were re-laid after mirroring so every island is unique per side,
  because skins need both sides.

### 2.2 Surface and density
- An **even grid of about 20 mm** over the whole body. It does not get much denser on curves (median
  edge 18–23 mm whether the bend is 0° or 60°). The roof panel is the exception: 40 mm squares on the
  flat, 10–18 mm on the bends.
- **Crisp lines come from tight extra edge loops, not from hard edges.** 99.5 % of the body's edges
  are smooth-shaded, and the 99th-percentile bend across a smooth edge is 100°. Sharpness comes from
  loops a few mm apart at every feature: shut lines, rubbing strip, arch lip, door handle recess.
- **Normals are plain averages.** The stored normals match the unweighted face average (median 0.26°)
  better than the area-weighted one (1.03°). There is no weighted-normal or custom-normal trick, which
  is ordinary smoothing-group behaviour.

### 2.3 Panels, gaps and thickness (sections, `section.py`)
- **Single-sided skin on the AE86** (phase 2: other cars differ; the Quattro, E30 and Kadett have boxed door edges). The cross-section at mid-door shows the exterior door skin and a
  separate interior door card with about 100 mm of nothing between them. The roof is one sheet.
- **Shut lines are tiny returns.** At the door's rear edge the door skin turns in about 5 mm and the
  body has a matching short chamfer, leaving a gap of about 3–4 mm. There is no deep groove. The dark
  gap you see in-game is mostly **painted into the texture** (black strips along every shut line in
  `body.dds`).
- **Edges roll back** at arches and openings: the arch lip turns inward and a liner continues it.
  This is the same idea as our `roll_edges.py`.
- **Glass is two layers:** an outer pane (`ksPerPixelReflection`) plus an inner pane (`ksWindscreen`
  for the screen) about 10 mm inside, plus separate `ksBrokenGlass` damage meshes.
- The underside is one flat plane (`GEO_Underside`).

### 2.4 UVs and textures
- **The paint atlas is an "unfolded car" on one 2048² `body.dds`.** It is shared by body, doors,
  bumpers and roof:
  - left and right flanks as side-on projections, wheel arches laid out as strips
  - roof, rear deck and bonnet flat in the middle
  - bumpers unrolled into long strips along the bottom
  - mirrors and small parts in the leftover corners
- The atlas is laid out so a livery painter can work on it, and this is what CM skins rely on.
- **Interior uses a low-res baked AO image as the diffuse** (`interiors_ao.dds` 1024²), multiplied by
  small **tiling detail textures** (leather, fabric, plastic, 64–512 px) through `txDetail` and
  `detailUVMultiplier`. Very cheap, and it looks rich.
- Exterior paint uses `ksPerPixelMultiMap_damage_dirt` with body (2048), maps (512), detail (64 tiling),
  damage (2048), damage normal (512) and dirt (1024).
- Most small parts share one `details.dds` (512×256) or `interiors_details.dds` atlas.

### 2.5 Hierarchy (what AC and CSP read)
- Standard dummies:
  - wheels and brakes: `WHEEL_xx`, `RIM_xx`, `RIM_BLUR_xx`, `SUSP_xx`, `DISC_xx`
  - cockpit: `COCKPIT_HR`, `COCKPIT_LR`
  - opening panels: `DOOR_L`, `DOOR_R`, `MOTORHOOD`, `FRONT_BUMPER`, `REAR_BUMPER`
  - lamps: `LIGHT_L`, `LIGHT_R`
  - glass damage: `DAMAGE_GLASS_*`
  - cameras: `FLYCAM_*`
  - wipers: `WIPER1/3/5`
- The gear lever is a **skinned mesh** (`SHIFTER_BONE_1/2`).
- Animations: door L/R, shift, wiper, lights, steer (`.ksanim`).
- Rims have separate blur meshes, swapped in at speed.

## 3. How the 205 mod compares

- **The source is a converted game model**, not built for AC. The names give it away
  (`peu_205t16_84_lod0_trunk_body___5956_vertices_12380_faces`, `-mesh-mesh-mesh`, Spanish `matricula`,
  `luz_freno_tra`).
- **Quad-based too (86–91 %), but coarser:** 35–75 mm edges, with few holding loops.
- **Faceted shading:** 18 % of shell edges are hard, against 0.5 % on Kunos. Flat panels look fine,
  but curves show facets.
- **Doors are closed boxes** (outer skin, a 40–70 mm jamb, inner panel), more "real" than Kunos's single
  skin, and twice the effort for something nobody sees in-game.
- **One 4096² atlas for everything:** the livery is painted in, and engine, interior and decals share
  the sheet. It is hard to reskin, the texture memory is huge (85 MB), and some islands are stretched
  (front bumper).
- No LODs. It has the minimum AC hierarchy (WHEEL, SUSP, COCKPIT_HR, MOTORHOOD, FRONT_BUMPER) and lots of
  unnamed `Object00x` nodes.

**Verdict:** the 205 shows what a conversion looks like. The AE86 is the standard to copy.

## 4. What this means for our generated models

These are rules for `build_shell2.py`, `front_end.py`, `roll_edges.py`, `shut_lines.py` and future cars.
Each one is a target number that can be checked with the tools here.

1. **Budget:** whole car about 250k triangles, painted shell about 28k, about 3k tris/m². We are at 6×
   that on the installed Nova. Generate fewer, better-placed rows rather than dense rows.
2. **Grid:** about 20 mm along and across flowing panels; 40 mm on flat roof/bonnet areas, with extra
   rows only at features. This matches our "features as rows" method (M010): Kunos's holding loops
   *are* feature rows.
3. **Quads only, triangulate at export.** Our swept-section method already makes quad grids. Keep it.
   (Thin triangles from tight holding loops are normal: about 23 % of Kunos paint triangles are under 5°.)
4. **No hard edges on paint.** Make crisp lines with 2–3 rows a few mm apart, smooth-shaded, and use
   plain-average normals.
5. **Shut lines:** about 5 mm returns on both panels, a 3–4 mm gap, and a **dark strip in the texture or
   AO bake**. Our 5-row groove (`shut_lines.py`) is more geometry than Kunos uses; keep it only where it
   is seen close up.
6. **Single skin + rolled edges + separate interior cards.** No closed door boxes.
7. **Glass:** outer pane plus inner pane about 10 mm inside, plus damage glass if we want CSP/AC damage.
8. **UVs:** one 2048² "unfolded car" paint atlas (flanks side-on, roof and bonnet top-down, bumpers as
   strips), unique per side, at about 450–500 px/m. That makes our cars skinnable in CM and fits
   `ac-skin-generator`.
9. **Interior:** baked AO diffuse plus tiling detail textures (`txDetail`, `detailUVMultiplier`).
10. **Hierarchy:** use the Kunos dummy names (section 2.5) from the start, plus LOD B/C/D at about
    22 % / 7 % / under 1 %.

## 5. Tools (all numpy; the Blender importer runs inside Blender 5.2)

| File | Use |
|---|---|
| `kn5full.py` | Full kn5 reader: node tree, matrices, all mesh flags, material props, textures. Handles the **short skinned-mesh trailer** that broke the older readers. |
| `analyze.py CAR_DIR OUT` | Per-mesh CSV: tris, split ratio, hard edges, seams, edge length, tris/m², texel px/m, slivers, symmetry. Also materials CSV, node tree and LOD summary. |
| `blender_import.py` | Imports a kn5 into Blender with welded vertices (real topology), custom normals, UVs, textured materials (ks props kept as custom properties) and the full dummy hierarchy, correctly oriented (car faces -Y). About 3 s per car. |
| `uv_sheet.py` | Draws mesh UVs over their texture, to see atlas layout. |
| `section.py` | Cuts a plane through the car with a 10 mm grid: thickness, gaps, flanges, glass layers. |
| `shape_rules.py` | Bend per edge, density vs curvature, hard edges, which normal weighting was used. |

Use them on any installed car, including our own exports, to grade them against the Kunos numbers in
section 1.

## 6. Notes and limits
- kn5 v6 stores V as negative (image row = 1 + v). The importer flips it, and liveries read the right
  way round.
- The installed Nova measured here is the 20 Oct block-out. The current section-built body has never
  been exported, so it is not graded yet. Next step: export it and run `analyze.py` and `shape_rules.py`.
- The Blender MCP add-on is behind (protocol 11 vs 15). It worked through fallbacks. To update it:
  `uvx mcp-for-blender install-addon`, then re-enable it in Blender.
