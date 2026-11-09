# How Assetto Corsa cars are built: the complete kn5 study (2026-11-09)

Part of the Blender work project (`blender/`). This single document covers everything done so far. It
replaces reading `REPORT.md` (phase 1: AE86 vs 205) and `REPORT_PHASE2.md` (phase 2: eight more cars) one
after the other. Both are kept for their detail.

**Goal:** learn how professional AC cars are made, measure it, and turn it into rules, target numbers and
tested tools for building accurate cars of our own (Nova, Sunbeam, Escort and any future car).

**Method:**
- Read every installed kn5 directly with our own reader.
- Import into Blender 5.2 through the Blender MCP to inspect edge flow.
- Cut cross-sections, draw UV layouts over the textures, and measure topology and shading.
- Measure dimensions and compare them with published road-car figures found online.

Everything below was measured, not assumed. Three early claims that the wider data disproved are corrected
(section 9).

> **Update, phase 3 (112 cars):** the study now covers 112 cars: 67 Kunos, 29 mods, 12 single-seaters/open cars, 3 traffic cars and our Nova. Results are in `REPORT_PHASE3.md`. The Kunos recipe below holds on all 67 Kunos cars: paint shell 23-34k tris, 20-27 mm grid, 89 % quads, 100 % plain normals. Their wheelbase matches specs to a median of 2 mm. Mods use about 2x the triangles but are about 4x less accurate. Single-seaters use rigid suspension meshes animated with car_susp_XX.ksanim. Width is now measured with a 0.6 m spike filter so mirrors drop out (road-car median error 8 mm).

---

## 1. The cars studied

| Car (AC folder) | Made by | Era / type | Why it was chosen |
|---|---|---|---|
| `ks_toyota_ae86` | Kunos | 1983 hatch | First, deepest study: the professional standard |
| `bmw_m3_e30` | Kunos (base game) | 1986 saloon | Box flares, rear wing |
| `ks_ford_escort_mk1` | Kunos | 1970 saloon (RS1600 race) | Base for our Escort project |
| `ks_abarth_595ss` | Kunos | 1960s tiny car | Round lamps, chrome bumpers |
| `ks_mazda_mx5_nd` | Kunos | 2015 roadster | Modern complex surfaces |
| `ks_audi_sport_quattro` | Kunos | 1984 coupe | Box arches |
| `Peugeot_205_EVO1_GrB` | mod | 1984 rally hatch | Closest in type to the Nova |
| `clio_williams_p` | mod | 1993 hatch | Nova-class small hatch |
| `opel_kadett` | mod | 1977 Kadett C GT/E | 70s GM coupe |
| `renault_5_turbo_r` | mod | 1980 wide-body hatch | Small hatch, wide body |
| `vauxhall_nova_gte_1989` | **ours** | 20 Oct block-out | Graded against all of the above |

The current section-built Nova body has never been exported, so it is not graded yet.

---

## 2. Dimensions: how accurate are the models?

Model minus published spec, in mm. Sources are in section 11 and `specs.json`.

| car | length | width | height | wheelbase | track F | track R | note |
|---|---|---|---|---|---|---|---|
| ks_toyota_ae86 | 4195 (-10) | 1622 (-3) | 1273 (-62) | 2400 (+0) | 1355 (+0) | 1350 (+5) | road car |
| Peugeot_205_EVO1_GrB | 3797 (-28) | 1659 (-15) | 1333 (-21) | 2530 (-10) | 1420 (-10) | 1420 (-10) | rally car |
| bmw_m3_e30 | 4355 (+10) | 1696 (+16) | 1341 (-29) | 2578 (+16) | 1431 (+19) | 1431 (-3) | road car |
| ks_ford_escort_mk1 | 3974 (-4) | 1695 (+126) | 1304 (-42) | 2400 (-0) | 1373 (+128) | 1359 (+89) | race flares: width/track not comparable |
| ks_abarth_595ss | 2995 (+25) | 1356 (+36) | 1293 (-32) | 1837 (-3) | 1121 (+0) | 1121 (-14) | 595 SS on 500 body |
| ks_mazda_mx5_nd | 3908 (-8) | 1738 (+2) | 1169 (-56) | 2309 (-1) | 1496 (+1) | 1502 (-3) | road car |
| ks_audi_sport_quattro | 4134 (-26) | 1809 (+29) | 1341 (-3) | 2206 (-18) | 1496 (+31) | 1496 (-6) | road car |
| clio_williams_p | 3697 (-15) | 1653 (+12) | 1297 (-68) | 2470 (-2) | **1440 (+68)** | **1400 (+49)** | road car |
| opel_kadett | 4113 (-14) | **1678 (+98)** | 1299 (-41) | 2392 (-3) | 1349 (+49) | **1427 (+128)** | rally-style mod |
| renault_5_turbo_r | 3669 (+5) | 1736 (-14) | 1276 (-47) | 2420 (-10) | 1320 (-26) | 1444 (-30) | road Turbo 1 |
| vauxhall_nova_gte_1989 (ours) | 3622 (+0) | 1535 (+0) | 1367 (+3) | 2343 (+0) | 1320 (+0) | 1307 (+7) | block-out |

**Findings**
- **Kunos models are accurate to about 1 %:**
  - wheelbase within 18 mm (median 1 mm)
  - length within 26 mm
  - width within 36 mm
  - track within 31 mm
- **Target tolerances for our cars:** wheelbase ±10, length ±25, width ±25, track ±20 mm.
- **Height always reads 3–68 mm low.** AC cars sit at their in-game ride height, but published height is
  the unladen road car. Height is only a test if the ride height is set to the road figure.
- **The check finds mod errors without opening Blender.** Clio Williams wheels are 49–68 mm too wide; the
  Kadett's rear track is 128 mm over spec and its body 98 mm wide.
- **Our Nova block-out is exact.** Measurement-first works for dimensions; construction is the weak point
  (section 3).

---

## 3. Construction: the numbers

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

Surface layout (main paint mesh):

| group | exact-mirror vertices | edges on z-stations / x-planes / waterlines |
|---|---|---|
| Kunos AE86, E30, Escort, 595, MX5, Quattro | 98.5 / 99.6 / 97.9 / 99.9 / 89.3 / 99.5 % | 13–22 / 16–28 / 15–26 % |
| Clio, Kadett mods | 98.8 / 99.9 % | 17–27 / 25–33 / 14–32 % |
| 205, R5 Turbo mods | 0 / 0.1 % (0.5–0.8 mm asymmetric: converted or scanned) | 14–18 / 16–26 / 16–25 % |
| Nova block-out | one side only | 30 / 16 / **68 %** (waterline-dominated generated grid) |

AE86 detail:
- Body 12k triangles, doors 3.4k each, bumpers 3.8k each, roof 1.9k.
- Only 0.5 % of body edges are hard.
- About 23 % of paint triangles are under 5°. These are the thin quads of tight holding loops, which is
  normal.

---

## 4. The professional recipe (true on every Kunos car)

1. **Half model, mirrored exactly.** 89–100 % of shell vertices have an exact mirror partner. The UVs are
   then re-laid per side: Kunos shares under 10 % of UV space between left and right, so skins can differ
   side to side.
2. **Quad modelling, triangulated on export.** 89–94 % of triangles pair back into quads on every car,
   mods included.
3. **Budget:**
   - Whole car 120k–275k triangles.
   - Painted shell about 20–35k, with edges 18–27 mm apart and 1,600–3,600 tris/m².
   - Interiors and wheels take most of the budget.
4. **Even grid, denser only at features.** The AE86 body's edges are about 20 mm whatever the curvature.
   Flat roof panels go to about 40 mm.
5. **Edge loops follow features, not stations.** Only 13–28 % of edges lie on constant-z, constant-x or
   constant-y planes. Loops run along shut lines, swage lines, arch lips and window frames, with 2–3 tight
   parallel loops on each feature.
6. **Crisp lines from tight loops, smooth-shaded.**
   - Hard edges are rare on Kunos 2016+ cars (3–7 %).
   - The older E30 (27 %) and the mods (20–37 %) use more, and look faceted.
   - Normals are **plain averages**, with no weighted-normal trick on any car.
7. **Panel gaps are mostly painted, not modelled.**
   - Geometry: each panel turns in about 5 mm at the gap, leaving a 3–4 mm opening, with no deep groove.
   - Every Kunos paint diffuse is a **white sheet with baked ambient occlusion**: shut lines, recesses and
     badge outlines are dark lines.
   - The `txMaps` gloss channel carries the same AO, so gaps also lose their shine.
   - The paint normal map is **only for damage dents**.
8. **Paint texture:** an "unfolded car" atlas, unique per side:
   - flanks side-on, with arches as strips
   - roof, deck and bonnet flat in the middle
   - bumpers unrolled along the bottom
   - small parts in the corners

   Kunos 2016+ uses **1024²** (140–280 px/m) plus a tiling metal-detail map
   (`detailUVMultiplier` 20–70). The older AE86 and E30 use 2048² (about 460 px/m). Mods use 4096² with no
   visible gain and 3–4× the texture memory (85–133 MB vs about 30 MB).
9. **Interior:** a low-res baked AO image as diffuse (`interiors_ao`, `cockpit_AO`) multiplied by small
   tiling leather, fabric and plastic detail maps.
10. **Glass:** an outer pane plus an inner pane (`ksWindscreen`) about 10 mm inside, plus separate
    `ksBrokenGlass` damage panes.
11. **Standard package on every Kunos car:**
    - LOD B/C/D at about 15 % / 4 % / 1 %
    - `RIM_BLUR` meshes, a skinned gear-lever boot
    - animations: doors, wiper, shift and steer, plus suspension on the Escort and 595
    - dummies `WHEEL_xx, SUSP_xx, DISC_xx, RIM_BLUR_xx, COCKPIT_HR/LR, STEER_HR/LR, DOOR_L/R,
      MOTORHOOD, FRONT/REAR_BUMPER, LIGHT_L/R, WIPER*, FLYCAM_*, DAMAGE_GLASS_*`
12. **Pipeline:** every car was exported via FBX (`FBX: ….fbx` root). ksEditor splits multi-material
    objects into `_SUBn`. `polymsh_*` names (E30, MX5, Escort, Quattro) point to Softimage XSI.

---

## 5. How specific shapes are built

| Shape | How the pros do it |
|---|---|
| Doors | Either a single skin plus a separate door card about 100 mm inside (AE86, 595), or boxed edges with a 40–60 mm jamb (Quattro, E30, Kadett). Both look right; single skin is cheaper and the default. |
| Shut lines | About 5 mm returns on both panels, a 3–4 mm gap, and a dark line baked into the skin and gloss maps. |
| Wheel arches | Lip rolls inward and continues as a liner. Flares and box arches are part of the shell grid, with an extra loop at the lip and the turn-under. |
| Grilles | Real geometry bars over a dark backing panel (Escort). Alpha cut-outs only for small fine parts: nuts and bolts, seams, belts, dial needles, the MX5 mesh insert. |
| Headlamps | Three parts: a domed lens mesh whose fluting is a **normal map** (`ksPerPixelNM_UVMult`), a separate chrome reflector bowl, and a bulb. The glow comes from `LIGHT_*` nodes and config (`ksEmissive` is 0 on every car). |
| Badges, lettering | Separate small meshes sitting on the panel (Escort `FORD` letters), sometimes normal-mapped (E30). Never cut into the shell. |
| Chrome | Separate meshes with reflection shaders (595 chrome bumpers, lamp surrounds). |
| Underside | One simple flat or stepped shell. |
| Gear lever boot | Skinned mesh with two bones (`SHIFTER_BONE_1/2`). |

**205 mod, a converted game model:**
- Names give it away (`peu_205t16_84_lod0_trunk_body…`, `-mesh-mesh-mesh`, Spanish node names).
- 35–75 mm edges and 18–23 % hard edges, so it looks faceted.
- Closed-box doors.
- One 4096² atlas with the livery painted in, which is hard to reskin.
- No LODs and a minimal hierarchy.

It is a useful example of what to avoid.

---

## 6. Accuracy techniques: built and tested

| # | Technique | Tool | Test | Result |
|---|---|---|---|---|
| T1 | Dimension template vs published specs | `measure.py` + `specs.json` + `compare_specs.py` | 11 cars | **Works.** Kunos ±1 %, finds mod errors. Height needs ride-height care. |
| T2 | Silhouette overlay, wheel-aligned, best-fit for ride height | `silhouette.py` | Kunos E30 vs its own Gr.A variant | IoU 0.996, median 0 mm (sanity check passed) |
| | | | Kunos AE86 Trueno vs BDB AE86 coupe (other author) | Front and glasshouse agree; real hatch-vs-notchback roof difference shows (side IoU 0.92) |
| | | | Kunos M3 E30 vs Fumi E30 340i (other author) | Glasshouse within median 8.5 mm; M3 flares and wing show as differences (side IoU 0.955) |
| T3 | Side outline exported as a mm template (from front axle and ground) | `silhouette.py` → `*_A_side.csv` | AE86, E30 | Works; ready for blueprint or photo overlay |
| T4 | Standard construction sections: centreline, mid-wheelbase, front axle, plan cut | `construction_sheet.py` (uses `section.py`) | 11 cars | Works; door type, arch lip, glass layers and floor in one image |
| T5 | Construction scorecard: budget, grid, quads, hard edges, UV sharing, texel, LODs, package | `survey.py` | 11 cars | Works; the quad estimate matches Blender's Tris-to-Quads within 1.5 points |
| T6 | Layout and exact-mirror test | `fairness.py` | 11 cars | Works; separates half-mirrored models from converted or scanned ones |
| T7 | Surface smoothness from curvature noise | `fairness.py` | 11 cars | **Inconclusive.** It depends on mesh density; use only to compare models of equal density |
| T8 | UV atlas drawn over its texture | `uv_sheet.py` | AE86, 205 | Works; shows atlas layout, side sharing, stretching |
| T9 | Edge bend, density vs curvature, normal weighting | `shape_rules.py` | AE86, 205, Nova | Works; found the even 20 mm grid and the plain-average normals |

**Measurement gotchas built into `measure.py`:**
- **Wheelbase and track:** from the `WHEEL_xx` dummies. These are the most reliable numbers in any model.
- **Tyre:** the outermost mesh on the wheel.
- **Rim:** measured over the flange, so it reads about nominal + 50 mm.
- **Ground:** the lowest point of the tyres. Never assume y = 0; one mod sits 156 mm below its origin.
- **Length:** raw extent without number plates. Spike filters cut real bumper noses because the vertices
  are sparse there.
- **Width:** measured below the beltline with mirror meshes removed. Mirrors are often merged into the doors.
- **Height:** raw roof, unless an antenna is detected.

---

## 7. How to build an accurate car (any car): the workflow

1. **Specs first.** Add the car's published length, width, height, wheelbase and tracks to `specs.json`,
   with sources.
2. **Wheels first.** Place the wheel centres from wheelbase and track. They are the best-published and
   best-modelled numbers; fit the body to them.
3. **Reference outline.** If any other AC model of the car exists, even a poor one, use `silhouette.py`
   as an independent second opinion and export its side-outline CSV. Two independent modellers agree to
   about 10 mm on shared parts; a bigger gap marks something to re-check against photos and blueprints.
4. **Build:**
   - left half only, mirrored exactly
   - quads on an 18–27 mm grid (about 40 mm on flat roof and bonnet)
   - features as 2–3 tight loops, smooth-shaded, plain normals
   - paint shell about 25k triangles
5. **Details as separate parts:**
   - badges, chrome, lamp lens, reflector and bulb, grille bars
   - lens fluting and fine texture in normal maps
   - alpha only for small mesh-like parts
6. **Panels:** a single skin with about 5 mm returns at a 3–4 mm gap, rolled arch and opening edges, and
   separate door cards.
7. **Skin:** an unfolded-car atlas, unique per side, 1024–2048², with **baked AO** in the white diffuse and
   gloss maps.
8. **Package:** Kunos dummy names, two-layer glass plus damage glass, LOD B/C/D at about 15 / 4 / 1 %,
   `RIM_BLUR`, door, wiper and shift animations.
9. **Check:**
   - `measure.py` + `compare_specs.py`: wheelbase ±10, length and width ±25, track ±20 mm
   - `survey.py` for construction against the Kunos numbers
   - `construction_sheet.py` for sections
   - finally, by eye against photos

### What this means for our existing tools
- **Section sweep** (`front_end.py`, `build_shell2.py`): keep the quad grid, but loops must follow
  features. Our station-loop grid is 68 % waterlines on the block-out, against 15–26 % on Kunos.
- **`roll_edges.py`** matches the Kunos arch and opening treatment. Keep it.
- **`shut_lines.py`** (5-row groove) is more geometry than Kunos uses. Prefer about 5 mm returns plus a
  baked AO line; keep grooves only where they are seen close up.
- **Budget:** the Nova block-out is 1.44M triangles, about 6× a full Kunos car and about 30× on the
  paint shell. Generate fewer, better-placed rows.
- **Missing from the Nova:**
  - skin UVs and AO
  - LODs
  - dummies DOOR, MOTORHOOD, bumpers, LIGHT, WIPER, DAMAGE_GLASS, FLYCAM
  - two-layer glass

---

## 8. Tools (folder `blender/kn5-study/`; numpy and PIL only, importer runs in Blender 5.2)

| File | Use | Example |
|---|---|---|
| `kn5full.py` | Full kn5 reader: node tree, matrices, mesh flags, material props, textures | library |
| `analyze.py` | Per-mesh and per-material CSVs, node tree, LOD summary | `python analyze.py CAR_DIR OUT_DIR` |
| `blender_import.py` | kn5 into Blender: welded topology, custom normals, UVs, textured materials, dummy hierarchy, car faces -Y, about 3 s per car | inside Blender: `bi.load(kn5, out_dir, prefix='AE86')` |
| `uv_sheet.py` | UVs drawn over their texture | `python uv_sheet.py CAR.kn5 txDiffuse out.png GEO_body ...` |
| `section.py` | Plane cut with a 10 mm grid; `draw()` importable | `python section.py CAR.kn5 z 0.0 out.png` |
| `shape_rules.py` | Bend per edge, density vs curvature, normal weighting | `python shape_rules.py CAR.kn5 GEO_body` |
| `measure.py` | Dimension and landmark template | `python measure.py CAR_DIR ... --out m.json` |
| `specs.json` | Published dimensions with sources | add new cars here |
| `compare_specs.py` | Model-vs-spec table | `python compare_specs.py m.json specs.json` |
| `survey.py` | Construction and technique scorecard | `python survey.py out.json CAR_DIR ...` |
| `fairness.py` | Station layout, exact-mirror test, curvature noise | `python fairness.py CAR_DIR MESH ...` |
| `silhouette.py` | Aligned silhouette overlays, IoU, outline distance, side CSV | `python silhouette.py A_DIR B_DIR out_prefix` |
| `construction_sheet.py` | Four standard sections per car in one image | `python construction_sheet.py out.png CAR_DIR ...` |

**Data and images** (not in git, they contain game assets): `D:\Claude\_scratch_research\kn5_study\`
- tables and data: `measures.json`, `survey.json`, per-car CSVs, `spec_table.md`
- section sheets `cs_1..5.png`, silhouette overlays `sil_*`, `paint_texture_sets.png`, UV sheets
- summary images `kn5_study_summary.png`, `phase2_summary.png`
- study blend `kn5_study_AE86_vs_205.blend`

---

## 9. Corrections made along the way
- "The AE86 is not built from mirrored halves" was **wrong**: 98.5 % of its body vertices are exact mirrors.
  Only the UVs are per side.
- "Kunos has about 0 sliver triangles" was **wrong**: about 23 % of paint triangles are under 5°, from
  tight holding loops. Thin triangles are not a fault.
- "Single skin everywhere" holds for the AE86 and 595 only. The Quattro, E30 and Kadett have boxed door
  edges.
- "Modelled in 3ds Max" is not provable. Every car came via FBX, and several show Softimage XSI naming.

## 10. Limits and gotchas
- **kn5 quirks:**
  - V is stored negated (image row = 1 + v); the importer flips it.
  - Skinned meshes have a short trailer (material, layer, lod in/out only), which broke the older reader.
  - The node world matrix is row-vector with translation in row 3.
- **Axes:** AC is +x left, +y up, +z forward. The Blender import maps the car to face -Y.
- **Published specs disagree** by up to about 20 mm between sources. Values are the best-supported
  figures, not factory drawings.
- **Height** comparisons include ride-height differences (section 2).
- **Blender MCP add-on** is behind (protocol 11 vs 15). It works through fallbacks; update with
  `uvx mcp-for-blender install-addon`, then re-enable it in Blender.
- **Not yet done:**
  - export and grade the current section-built Nova body
  - test the silhouette tool against a real blueprint mask
  - an AO-bake test for skins

## 11. Sources for published dimensions
- AE86: [Toyota global lineage](https://www.toyota-global.com/company/history_of_toyota/75years/vehicle_lineage/car/id60009032/), track [aeu86.org](https://www.aeu86.org/?p=142)
- 205 T16: [FIA Group B homologation 262](https://historicdb.fia.com/sites/default/files/car_attachment/1611151201/homologation_form_number_262_group_b.pdf)
- BMW M3 E30: [Wikipedia](https://en.Wikipedia.com/wiki/BMW_M3), [auto-data](https://auto-data.net/en/bmw-m3-coupe-e30-2.3-200hp-30376)
- Escort Mk1: [Unique Cars & Parts](https://www.uniquecarsandparts.com.au/ford_escort_mark_1_technical_specifications)
- Fiat 500 / 595: [Wikipedia](https://en.wikipedia.org/wiki/Fiat_500)
- MX-5 ND: [cars-data](https://cars-data.com/en/mazda/mx-5/nd/skyactiv-g-160-gt-m--83345/specs)
- Sport quattro: [Juwra](https://juwra.com/audi_quattro_sport.html), [supercars.net](https://www.supercars.net/blog/1984-audi-sport-quattro/)
- Clio Williams: [cars-data](https://cars-data.com/en/renault/clio/1994-hatchback-6904/williams-16v--10457/specs)
- Kadett C GT/E: [auto-data](https://www.auto-data.net/en/opel-kadett-c-coupe-2.0-gt-e-115hp-1959)
- R5 Turbo: [Wikipedia](https://en.wikipedia.org/wiki/Renault_5_Turbo), [Juwra](https://juwra.com/renault_r5_turbo.html)
- Nova: [AutoHints](https://www.autohints.com/vauxhall/nova/nova-cc/1-6-gsi-100-hp-42038), [auto-data](https://auto-data.net/en/vauxhall-nova-cc-1.2-s-58hp-6259)
