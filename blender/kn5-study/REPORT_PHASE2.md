# Phase 2: eight more cars, accuracy techniques tested (2026-11-09)

This follows `REPORT.md` (AE86 vs 205). That report has been corrected where the wider data disproved it:
symmetry, slivers, door construction and authoring package.

The cars, chosen for spread of era, body type and author:

| Car | Made by | Why |
|---|---|---|
| `bmw_m3_e30` | Kunos (base game) | 80s saloon with box flares |
| `ks_ford_escort_mk1` | Kunos | 70s; base for our Escort project |
| `ks_abarth_595ss` | Kunos | 60s tiny car, round lamps, chrome |
| `ks_mazda_mx5_nd` | Kunos | modern, complex surfaces |
| `ks_audi_sport_quattro` | Kunos | 80s box arches |
| `clio_williams_p` | mod | 90s small hatch (Nova class) |
| `opel_kadett` | mod (Kadett C GT/E) | 70s GM coupe |
| `renault_5_turbo_r` | mod | 80s small hatch, wide body |

The AE86, the 205 and our installed Nova block-out were re-run through the same tools.

Data and images (not in git, they contain game assets): `D:\Claude\_scratch_research\kn5_study\`
(`measures.json`, `survey.json`, `cs_*.png` section sheets, `sil_*` silhouette overlays, `paint_texture_sets.png`).

## 1. Dimensions vs published specs (`measure.py`, `specs.json`, `compare_specs.py`)

Model minus spec in mm. Specs are road-car figures found online today; sources are in `specs.json`.

| car | length | width | height | wheelbase | track F | track R | variant |
|---|---|---|---|---|---|---|---|
| ks_toyota_ae86 | 4195 (-10) | 1622 (-3) | 1273 (-62) | 2400 (+0) | 1355 (+0) | 1350 (+5) | road car |
| Peugeot_205_EVO1_GrB | 3797 (-28) | 1659 (-15) | 1333 (-21) | 2530 (-10) | 1420 (-10) | 1420 (-10) | rally car |
| bmw_m3_e30 | 4355 (+10) | 1696 (+16) | 1341 (-29) | 2578 (+16) | 1431 (+19) | 1431 (-3) | road car |
| ks_ford_escort_mk1 | 3974 (-4) | 1695 (+126) | 1304 (-42) | 2400 (-0) | 1373 (+128) | 1359 (+89) | race car with flares (width/track not comparable) |
| ks_abarth_595ss | 2995 (+25) | 1356 (+36) | 1293 (-32) | 1837 (-3) | 1121 (+0) | 1121 (-14) | 595 SS on 500 body |
| ks_mazda_mx5_nd | 3908 (-8) | 1738 (+2) | 1169 (-56) | 2309 (-1) | 1496 (+1) | 1502 (-3) | road car |
| ks_audi_sport_quattro | 4134 (-26) | 1809 (+29) | 1341 (-3) | 2206 (-18) | 1496 (+31) | 1496 (-6) | road car |
| clio_williams_p | 3697 (-15) | 1653 (+12) | 1297 (-68) | 2470 (-2) | **1440 (+68)** | **1400 (+49)** | road car |
| opel_kadett | 4113 (-14) | **1678 (+98)** | 1299 (-41) | 2392 (-3) | 1349 (+49) | **1427 (+128)** | rally-style mod |
| renault_5_turbo_r | 3669 (+5) | 1736 (-14) | 1276 (-47) | 2420 (-10) | 1320 (-26) | 1444 (-30) | road Turbo 1 |
| vauxhall_nova_gte_1989 (ours) | 3622 (+0) | 1535 (+0) | 1367 (+3) | 2343 (+0) | 1320 (+0) | 1307 (+7) | 20 Oct block-out |

**What it shows**
- Kunos models are accurate to **about 1 %**:
  - wheelbase within 18 mm (median 1 mm)
  - length within 26 mm
  - width within 36 mm
  - track within 31 mm on road cars
- So a reference-quality model should hit: **wheelbase ±10, length ±25, width ±25, track ±20 mm.**
- **Height always reads 3–68 mm low.** AC cars sit at their in-game ride height, but published height
  is unladen road height. Height is not an accuracy test unless the ride height is set to the road figure.
- **The check catches modding errors.** The Clio mod's wheels are 49–68 mm too wide for a Williams. The
  Kadett's rear track is 128 mm over spec and its body is 98 mm wide, which suggests a widened rally body
  or a scaling error. The method works without opening Blender.
- **Our Nova block-out matches its published figures exactly.** Our measurement-first approach gets
  dimensions right; what it lacks is construction quality (section 2).

**How the template measures** (the gotchas found while testing, now built into `measure.py`):
- **Wheelbase and track:** from the `WHEEL_xx` dummy centres. These are the most reliable numbers in any
  model.
- **Tyre size:** the outermost mesh on each wheel. **Rim diameter is measured over the flange, so it reads
  about nominal + 50 mm.**
- **Ground:** the lowest point of the tyres. Never assume y = 0; one mod sits 156 mm below its origin.
- **Length:** raw extent without number plates. Spike filters cut real bumper noses because of sparse
  vertices.
- **Width:** measured **below the beltline with mirror-named meshes removed**. Mirrors are often merged into
  the door mesh (MX5, AE86), so a name filter alone fails.
- **Height:** raw roof, unless an antenna is detected, in which case it is spike-filtered.
- **Also measured:** overhangs, windscreen/backlight rake, belt height and tyre-to-arch gap. These are
  useful landmarks when matching photos.

## 2. How each car is built (`survey.py`, `fairness.py`, `construction_sheet.py`)

| car | made by | car tris | paint tris | paint edge mm | paint tris/m² | quads % | hard-edge % | paint texture | texel px/m | L/R UVs shared | tex MB | LOD B/C/D % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ks_toyota_ae86 | Kunos | 242k | 26k | 18.8 | 2990 | 89.8 | 4.4 | 2048² | 457 | 0.0 | 29.6 | 23/7/0.1 |
| bmw_m3_e30 | Kunos | 127k | 19k | 26.9 | 1650 | 90.8 | 26.6 | 2048² | 456 | 0.0 | 34.1 | 17/2/2 |
| ks_ford_escort_mk1 | Kunos | 234k | 36k | 18.0 | 3090 | 91.2 | 3.2 | 1024² | 208 | 0.04 | 31.2 | 11/4/0.6 |
| ks_abarth_595ss | Kunos | 166k | 24k | 19.6 | 3347 | 92.3 | 4.0 | 1024² | 276 | 0.0 | 30.4 | 18/4/0.9 |
| ks_mazda_mx5_nd | Kunos | 188k | 33k | 19.0 | 3573 | 89.2 | 4.8 | 1024² | 283 | 0.09 | 28.1 | 15/4/0.5 |
| ks_audi_sport_quattro | Kunos | 179k | 23k | 26.6 | 1882 | 89.0 | 7.1 | 1024×512 | 139 | 0.01 | 32.1 | 16/4/2 |
| Peugeot_205_EVO1_GrB | mod | 118k | 15k | 35.2 | 1085 | 86.9 | 22.7 | 4096² | 720 | 0.0 | 85.1 | none |
| clio_williams_p | mod | 191k | 52k | 22.0 | 3798 | 91.3 | 33.4 | 2048² | (tiled) | 0.24 | 104.5 | 46/19/8 |
| opel_kadett | mod | 275k | 60k | 9.9 | 6375 | 94.2 | 4.1 | 4096² | 720 | 0.59 | 133.0 | none |
| renault_5_turbo_r | mod | 216k | 45k | 18.8 | 4947 | 92.5 | 1.2 | 4096² | 1054 | 0.0 | 86.0 | none |
| vauxhall_nova_gte_1989 | **ours** | **1442k** | **747k** | **5.5** | **59291** | 60.1 | 2.2 | 4×4 | 31 | 0.28 | 0.1 | none |

Surface layout (`fairness.py`, main paint mesh):

| car | exact-mirror verts % | edges on z-stations / x-planes / waterlines % |
|---|---|---|
| Kunos AE86 / E30 / Escort / 595 / MX5 / Quattro | 98.5 / 99.6 / 97.9 / 99.9 / 89.3 / 99.5 | 13–22 / 16–28 / 15–26 |
| Clio / Kadett mods | 98.8 / 99.9 | 17–27 / 25–33 / 14–32 |
| 205 / R5 Turbo mods | 0 / 0.1 (asymmetric by 0.5–0.8 mm: converted or scanned) | 14–18 / 16–26 / 16–25 |
| Nova block-out | one side only | 30 / 16 / **68** (waterline-dominated generated grid) |

### 2.1 Rules that hold on every professional car

1. **Half model, mirrored exactly.** All Kunos shells have 89–100 % exact mirror vertices. The UVs are then
   re-laid per side; Kunos shares under 10 % of UV space between left and right, so skins can differ
   side to side. The Kadett mod shares 59 %, so its skins can't.
2. **Quad modelling, triangulated on export.** 89–94 % pair back into quads on *every* car, mods
   included. The quad estimator is validated against Blender's Tris-to-Quads to within 1.5 percentage
   points.
3. **Paint shell about 20–35k triangles, edges 18–27 mm, 1,600–3,600 tris/m².** Every car is between 120k
   and 275k triangles in total. Interiors and wheels take most of the budget, not the shell.
4. **Edge loops follow features, not stations.** Only 13–28 % of edges lie on constant-z, constant-x or
   constant-y planes. Loops run along shut lines, swage lines, arch lips and window frames, with tight
   parallel loops on each feature (seen close up on AE86, Quattro and Escort). Our section sweep makes
   station loops by construction; it must keep adding **features as rows** to match this.
5. **Smooth normals, plain average.** No weighted normals on any car. Hard edges are rare on Kunos 2016+
   cars (3–7 %); the older E30 (27 %) and the mods (20–37 %) use more, and look more faceted.
6. **Panel gaps and shadows are baked into the skin, not modelled deep.** Every Kunos paint diffuse
   (`skin_00`) is a **white sheet with baked ambient occlusion**: shut lines, recesses, badge outlines and
   panel edges are dark lines. The `txMaps` green channel (gloss) carries the same AO, so gaps also lose
   their shine. **The normal map on the paint is only for damage dents** (`Damage_NM`), never panel lines.
   Geometry provides just a small return at each gap.
7. **Paint texture budget:**
   - Kunos 2016+ uses a **1024² skin** (140–280 px/m) plus tiling detail (`metal_detail`,
     `detailUVMultiplier` 20–70).
   - The older AE86 and E30 use 2048² (about 460 px/m).
   - Mods use 4096² with no gain in look; texture memory is 3–4× higher (85–133 MB vs about 30 MB).
8. **Interiors use baked AO plus tiling detail materials** (`interiors_ao.dds`, `cockpit_AO.dds`,
   and leather/fabric/plastic detail maps).
9. **The standard package on every Kunos car:**
   - LOD B/C/D at about 15 % / 4 % / 1 %
   - `ksBrokenGlass` damage glass, `RIM_BLUR`, a skinned gear-lever boot
   - door/wiper/shift/steer animations, plus suspension animations on the Escort and 595
   - dummies `WHEEL/SUSP/DISC/COCKPIT_HR/LR/STEER_HR/LR/DOOR_L/R/FRONT/REAR_BUMPER/WIPER/FLYCAM/DAMAGE_GLASS`
   - None of the mods has the full set.

### 2.2 How specific shapes are built
- **Door construction varies.** Single skin plus a separate door card (AE86, 595), or boxed door edges with
  a 40–60 mm jamb (Quattro, E30, Kadett). Both look right in-game. Single skin is cheaper and is the
  safer default.
- **Grilles are geometry first.** The Escort grille is real thin bars over a dark backing panel, not an
  alpha cut-out. Alpha-test is kept for small or fine things: nuts and bolts, seams, belts, dial needles,
  and the MX5's mesh grille insert (`GEO_Grid`).
- **Headlamps have three parts:**
  - a domed lens mesh (`ksPerPixelNM_UVMult`), whose fluting is a **normal map**, not geometry
  - a separate chrome reflector bowl
  - a bulb
  - Lamp glow comes from `LIGHT_*` nodes and config, not `ksEmissive` (0 on every car).
- **Badges and lettering are separate small meshes sitting on the panel** (Escort `FORD` letters, E30
  logos with a normal map). They are not cut into the shell.
- **Flares and box arches are part of the shell grid,** with an extra loop at the lip and the turn-under.
  They are not separate add-on parts, except where the real car bolts them on.
- **Wheel arches roll inward** and continue as a liner, as `roll_edges.py` does.
- **Glass:** an outer pane plus an inner pane (`ksWindscreen`) on every car. Damage panes are separate.
- **Pipeline tells:**
  - Every car is exported via FBX.
  - `polymsh_*` names (E30, MX5, Escort, Quattro) point to Softimage XSI.
  - The 205 and R5 are not exactly symmetric and carry game-rip names: they were converted from other
    games.

## 3. Techniques tested for building an accurate car

| # | Technique | Tool | Test | Result |
|---|---|---|---|---|
| T1 | Measure a model against published dimensions | `measure.py` + `specs.json` + `compare_specs.py` | 11 cars | **Works.** Kunos ±1 %; catches mod errors (Clio track, Kadett). Height needs ride-height care. |
| T2 | Compare silhouettes with another model or a blueprint, aligned on the wheels with best-fit for ride height | `silhouette.py` | Sanity: Kunos E30 vs its own Gr.A variant | IoU 0.996, median 0 mm. **Works.** |
| | | | Kunos AE86 Trueno vs BDB AE86 coupe (different author) | Front and glasshouse agree; the real hatch-vs-notchback roof difference shows clearly (side IoU 0.92). |
| | | | Kunos M3 E30 vs Fumi E30 340i (different author, non-M3 body) | Glasshouse agrees, median 8.5 mm. M3 box flares and wing show as differences (side IoU 0.955). |
| T3 | Standard construction sections at the centreline, mid-wheelbase, front axle and a plan cut | `construction_sheet.py` (uses `section.py`) | 11 cars | **Works:** shows door type, arch lip, glass layers and floor in one sheet per car. |
| T4 | Grade construction (budget, grid, quads, hard edges, UV sharing, texel, LODs, package) | `survey.py`, `fairness.py` | 11 cars | **Works:** a one-line scorecard per car; Nova fails on budget, grid, UVs and package. |
| T5 | Export the side outline as a mm template (z, y from the front axle and ground) | `silhouette.py` (`*_A_side.csv`) | AE86, E30 | Works; ready to overlay on blueprints or photos. |
| T6 | Surface fairness from curvature noise | `fairness.py` | 11 cars | **Inconclusive:** it depends on mesh density (a dense mesh scores "smooth"). Kept for comparing models at equal density only. |

**Takeaways for building any car accurately**
1. **Start from the wheels.** Wheelbase and track are the best-published and best-modelled numbers. Place
   the wheel centres first, then fit the body to them. Check with `measure.py`: aim for wheelbase ±10,
   length/width ±25, track ±20 mm.
2. **If any other model of the car exists** (any AC mod, even a poor one), use `silhouette.py` as an
   independent second opinion on the outline. Two independent modellers agree to about 10 mm on shared
   parts, so a larger gap marks a feature worth re-checking against photos.
3. **Model the left half, mirror exactly, quads,** with an 18–27 mm grid and features as tight loops.
   Keep the paint shell at about 25k triangles.
4. **Panel gaps are small returns plus baked AO.** Bake AO into a white 1024–2048² skin laid out as an
   unfolded car, unique per side.
5. **Use detail meshes for badges, lamps and grilles.** Put lens fluting and fine texture into normal
   maps; use alpha only for small mesh-like parts.

## 4. Nova scorecard (installed 20 Oct block-out)
- **Dimensions:** pass, exact to spec.
- **Construction:** fails.
  - Paint shell 747k triangles (about 30× Kunos), 5.5 mm grid, 59k tris/m², 60 % quads.
  - No skin UVs or AO, no LODs.
  - Missing dummies: DOOR, MOTORHOOD, bumpers, LIGHT, WIPER, DAMAGE_GLASS, FLYCAM.
- The current section-built body has not been exported, so it is not graded yet.

## 5. Tools added in phase 2
| File | Use |
|---|---|
| `measure.py` | Dimension and landmark template from any kn5 |
| `specs.json` | Published dimensions with sources (add new cars here) |
| `compare_specs.py` | Model-vs-spec table |
| `survey.py` | Construction and technique scorecard per car; paint shell found by area |
| `fairness.py` | Station-loop layout, exact-mirror test, curvature noise |
| `silhouette.py` | Aligned silhouette overlays, IoU and outline distance, side-profile CSV template |
| `construction_sheet.py` | Four standard sections per car in one image |
| `section.py` | Now also importable (`draw()`) |
