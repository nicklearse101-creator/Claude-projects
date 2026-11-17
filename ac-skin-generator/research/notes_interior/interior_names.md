# Interior part names and textures in Assetto Corsa cars (scan of Nik's own install)

Method and sources (read-only scan, 17 Nov 2026). Every number below comes from these local files:
- Scanner and per-car records: [scan.py](file:///D:/ClaudeData/tmp/interior_scan/scan.py) read every main `.kn5` in `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\` (868 car folders). It records texture names and sizes, materials (shader, samplers, props) and meshes (name, material, parent nodes, area), plus every image file in every `skins\*\` folder. One JSON per car is in [cars/](file:///D:/ClaudeData/tmp/interior_scan/cars/). Nothing in the game folder was written.
- **825 cars parsed** (179 Kunos, 646 mods). 43 could not be used: 4 folders have no kn5 (`ks_ferrari_488_challenge_evo`, `ks_ferrari_488_gt3_2020`, `lsg_rx7_fc3s`, `Claude outputs`), and 39 kn5 files are protected or scrambled (all RSS cars, 5 Gravy Garage street cars, `bdb_nissan_skyline_r31_wagon`, `dngs_toyota_ae86_levin_coupe`, `formula_k`, `ford_escort_mk2_rally_spec_(night)`, `RadaS13.5_Christmas_Public`). Some RSS files use a header variant with an extra int after the texture count; the scanner copes with that, but their node and material data still fails to parse.
- Kunos = folder `ks_*` or an original Kunos car id (abarth500, bmw_*, ferrari_458/f40/laferrari…, lotus_*, mclaren_mp412c, mercedes_sls, pagani_*, p4-5_2011, ruf_yellowbird, shelby_cobra_427sc, tatuusfa1, ktm_xbow_r), with an empty or "Kunos" author field. Everything else counts as a mod.
- Coverage by ui tags (parsed cars): race 360, street 228, vintage 118, drift 93, gt3 89, touring 86, btcc 57, gte 45, gt4 38, rally 30, tcr 26, truck 19, f1 15, dtm 14.
- Analysis scripts: [analyze.py](file:///D:/ClaudeData/tmp/interior_scan/analyze.py) (the part dictionary and its counts, output in [parts.txt](file:///D:/ClaudeData/tmp/interior_scan/parts.txt)), [analyze2.py](file:///D:/ClaudeData/tmp/interior_scan/analyze2.py) (textures, output in [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt), and skins, output in [skins.txt](file:///D:/ClaudeData/tmp/interior_scan/skins.txt)), [skins2.py](file:///D:/ClaudeData/tmp/interior_scan/skins2.py), [probes.py](file:///D:/ClaudeData/tmp/interior_scan/probes.py) (false friends), [markers.py](file:///D:/ClaudeData/tmp/interior_scan/markers.py), [shared.py](file:///D:/ClaudeData/tmp/interior_scan/shared.py), [texsample.py](file:///D:/ClaudeData/tmp/interior_scan/texsample.py) (decodes a few textures to see where the colour is) and [tokens.py](file:///D:/ClaudeData/tmp/interior_scan/tokens.py) (finds the words used under COCKPIT_HR).
- Below, a "car count" means the number of cars where at least one mesh, material or texture name matches. Mesh / mat / txDiffuse / txDetail say which kind of name matched.

## Which names identify each interior part, how many cars use them, and which are false friends?

### Takeaway
Use the scene structure first, then the names. The standard AC nodes `COCKPIT_HR`/`COCKPIT_LR`, `STEER_HR`/`STEER_LR` and `CINTURE_ON`/`CINTURE_OFF` mark the interior in every Kunos car and in most mods. After that comes the `INT_` token (97 % of Kunos cars, 75 % of mods). The part words (seat, belt, steer, carpet, cage…) only work with word-boundary rules and an exclusion list. Bare substrings such as `int`, `wheel`, `brake`, `door`, `roof`, `stick` and `center` match mostly the wrong things.

### Cited Findings

**1. Structural markers (the most reliable signals)**
- Car counts for the AC node names are below. A car counts when a mesh's parent node or the mesh itself has that name. Source: inline count over [cars/](file:///D:/ClaudeData/tmp/interior_scan/cars/), using [analyze.py](file:///D:/ClaudeData/tmp/interior_scan/analyze.py).

  | Node | Kunos cars (of 179) | Mod cars (of 646) |
  |---|---|---|
  | COCKPIT_HR | 179 | 432 |
  | COCKPIT_LR | 179 | 185 |
  | STEER_HR | 179 | 588 |
  | STEER_LR | 177 | 151 |
  | CINTURE_ON | 168 | 244 |
  | CINTURE_OFF | 163 | 227 |
  | SHIFT_HR | 25 | 2 |
- Kunos cars almost always (157 of 179) have a separate low-resolution cockpit texture (`Cockpit_LR.dds`, `INT_LR.dds`, `cockpitLR.dds`…). Only 52 mods have one. This texture is a second copy of the interior colours. For example, `ks_mazda_miata` has material `COCKPIT_LR` on `Cockpit_LR.dds` with detail `carpet.dds`. — [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt), [texsample output for ks_mazda_miata](file:///D:/ClaudeData/tmp/interior_scan/texsample.py)
- Generic interior words. The table gives the share of cars that have at least one material (mat) or mesh with the word. — [markers.py](file:///D:/ClaudeData/tmp/interior_scan/markers.py)

  | Word | Kunos mat | Kunos mesh | Mods mat | Mods mesh |
  |---|---|---|---|---|
  | `INT_` / `int` as a whole token | 97 % | 73 % | 75 % | 67 % |
  | `cockpit` / `cpit` / typos `ccokpit`, `cockcpit` | 72 % | 74 % | 28 % | 46 % |
  | `interior` | 17 % | 16 % | 44 % | 42 % |
  | `inside` / `inner` | 11 % | 20 % | 18 % | 21 % |
  | `interno` / `interna` | 6 % | 14 % | 6 % | 3 % |
  | `cab` / `cabin` (whole word) | - | - | 7 % | 4 % |

  `innen` / `habitacle` / `abitacolo` were found in 1 mod mesh only. `int` glued to the next word (`intdash`, `IntSeatCloth`, `intplastic`, `intchassis`, `intalcantra`) appears in 8 % of mod materials.
- Naming families seen on the PC. — [markers.py](file:///D:/ClaudeData/tmp/interior_scan/markers.py)
  - `GEO_` mesh prefix: 94 % of Kunos cars, 47 % of mods.
  - Forza-style part names with a `_a` suffix, such as `seatl_a`, `dashpad_a`, `dashstructure_a`, `doorcardlf_a`, `floor_a`, `pillartrim_a`, `centerconsolestructure_a`, `steeringcolumn_a` and `pedals_a`, often written as `leather_mgl|seatr_a`: 122 mods (19 %).
  - ACC-style instance names (`mi_*`, `*_Inst`, `EXT_Carpaint_Inst`, `INT_Occlusion_Inst`): 84 mods (13 %).

**2. The part dictionary.** The rules are in [analyze.py](file:///D:/ClaudeData/tmp/interior_scan/analyze.py) (`D`); car counts come from [parts.txt](file:///D:/ClaudeData/tmp/interior_scan/parts.txt).

Matching rule used throughout:
1. Lower-case the name.
2. "Strong" patterns may match anywhere in the name.
3. "Token" patterns must match a whole token. Tokens are made by splitting on `_`, space and `.`, between digits and letters, and at camelCase (`IntSeatCloth` gives int, seat, cloth).
4. A name is thrown out if it hits an exclusion.

| Part | Strong patterns (anywhere) | Whole-token words | Exclude (false friends) | Cars (Kunos / mods) | mesh · mat · txDiffuse · txDetail |
|---|---|---|---|---|---|
| **Seat (shell)** | `seat` (not followed by belt / leon / ibiza / cupra), `sedil` (it), `asiento` (es), `backrest`, `headrest`, `sottosedil` (it, under-seat), `sedadl` (cz), `kubelsitz`, `schalensitz` (de) | seat(s), sitz*, siege, banco (pt), bucket, recaro, bride, cushion, fotel (pl), baquet (fr), sedile, sedili | valve_seat, SEAT brand (seat_leon…), headlight/taillight *bucket*, warning/light/lamp/emissive/indicator/led | 651 (146 / 505) | 515 · 467 · 243 · 78 |
| **Seat fabric / leather** | alcantara, alcnt, suede, velvet, vellut (it), tessut (it), stoffa (it), textile, leather, leder (de), pelle (it), cuero (es), cuir (fr), couro (pt), tartan, pepita, cucitur (it, stitching), stitch, velour, fabric, cloth | seam(s), tela, skai, stof* | exhaust (`ext_exhaust_fabric`), tyre | 717 (175 / 542) | 262 · 627 · 445 · **515** |
| **Belts / harness** | cintur (it: CINTURE_ON/OFF), seat.?belt, harness, ceinture (fr), schroth, sabelt, takata, buckle, gurt (de), hosentr | belt*, cinto (pt), strap, cinture* | cambelt/timing/fan belt, belt drive, pulley, **beltline**, **tow strap**, warning_seatbelts, fuel `tank_belt` | 604 (170 / 434) | 524 · 519 · 511 · 84 |
| **Dashboard (colourable)** | dash (not dashcam), cruscott (it), plancia (it), armaturen (de), tableau / planche (fr: `planche_de_bord`, `tableau_bord`), tablero (es), binnacle | painel* (pt), bord, dashboard | dash + light/glass/display/lcd/screen/gauge/dial/needle/led/symbol/decal/logo/sticker | 486 (69 / 417) | 360 · 315 · 217 · 53 |
| *Instruments (do NOT colour)* | gauge, dial, needle, cluster, display, lcd, screen, digital, tacho, speedo, motec, racelogic | tach*, rpm, arrow, hud, dials | - | 766 (179 / 587) | 739 · 681 · 620 · 35 |
| **Door cards** | door.?card, doorpanel, door.?panel, int.?door, inner.?door, door.?int, door.?trim, door.?inside, doorcloth, door + leather/alcantara, türverk (de), pannello porta (it), panneau porte (fr), forro porta (pt), tapizado (es), armrest, door pull | portiera, portiere (it), porte (fr), porta(s) (it/pt), intdoor(s), doorcard* | **door glass** (`int_glass_door_r`, `geo_inner_door_glass_l`), `ext_carpaint_door_l` (int inside carpaINT), `ext_bandes_portieres` (fr exterior stripes), door jamb, exterior handle, mirror | 264 (67 / 197) | 241 · 81 · 25 · 1 |
| **Roll cage** | roll.?cage, typos `roolcage`/`rollecage`, roll.?bar, roll.?hoop, safety.?cage, gabbia (it), käfig (de), arceau (fr), jaula / antivuelco (es), santantonio (it), chassis.?cage | cage(s), weld*, tube(s), tubi (it), roll | **anti_roll_bar** (suspension), light/lamp **cages** (turnlight_cage, brakelights_cage, frontlight_cage, reverselightcage), soft_top_cage, undercage, fuelcell_cage, intercooler/air/exhaust/bumper/shock tubes, exhaust_weld | 411 (36 / 375) | 335 · 260 · 194 · 78 |
| **Carpet / floor** | carpet, tapis (fr), moquet (fr/it), tappet (it: tappeto, tappetini), alfombr / moqueta (es), teppich (de), tapete (pt), floormat, footwell | floor*, piso, boden*, pavimento, suelo | underfloor, ext floor, diffuser, plank, skid, bed floor, chassis_floor, splitter. **Never use `mat`**: it means *material* in 10,703 names (`mat_carbon`, `Material #25`) | 331 (89 / 242) | 172 · 219 · 170 · **139** |
| **Headliner / roof lining** | headlin, roof.?lin, int.?roof, roof.?int, inner.?roof, ceiling, padiglion (it), dachhimmel (de), ciel de toit (fr: `cieldetoit`), sun.?visor, plafon (ru/pl dome light) | cielo (it), introof, techo (es), teto* (pt), himmel, visor(s) | `carpaint_roof` / `ext_carpaint_roof` (int inside paINT), `murcielago` contains cielo, roof lights (`int_rooflight`, `plafon_light`), sunroof glass. Also: `roof` + an interior marker (`int_occ_fabric_roof`, 7 cars) is the headliner. | 129 (6 / 123) | 84 · 76 · 26 · 1 |
| **Steering wheel** | steer (not steer arm / rack / axle / link / rod / knuckle), volant (fr/it/es/pt: volante), lenkrad (de), swheel, stwheel, st.?wheel, kierownic (pl), momo, paddle | stw, sw, omp, steering* | **road wheels** (`wheel_lf`, `wheel_b`, `g_wheel_hub_lr`), `g_susp_steer_lf`, `arm_steer_l`, steering rack, tie rod, `steerarm_middle` | 749 (173 / 576) | 706 · 500 · 416 · 99 |
| **Centre console** | console (not overhead console), consolle (it), consola (es/pt), mittelkonsol (de), center.?stack, centre.?stack, (transmission) tunnel | console(s), armrest | **center / centre / middle** alone: mirror_center (37 cars), mirrormiddle (24), damage_glass_center (25), brake_light_center, centre caps (`mk2_revo_centrecap`); overheadconsole_a (headliner area); console lights | 140 (14 / 126) | 121 · 54 · 20 · 4 |
| **Gear knob / lever** | gear.?knob, shift.?knob, gear.?stick, gear.?lever, gear.?shift, shifter (not shifter led/light), cambio (it/es; `guaina_cambio` = gear gaiter), pomello (it), pommeau / levier (fr), schalt (de), palanca (es), alavanca (pt), manopol* cambio, shift.?boot, gaiter, guaina | shift, knob, gear, sequential, selector, pomo | **sticker(s)** (stick), engine gearing / gearbox, `g_susp_*_gear`, susp **levers**, shift lights/LEDs (`cluster_shiftled`), shift paddles (steering wheel), `gopro_knob`, radio/console knobs, gear indicator display | 430 (106 / 324) | 376 · 158 · 101 · 4 |
| **Pedals** | pedal, pedali / pedale (it), pedaliera (it), accelerator, throttle.?pedal, brake.?pedal, clutch.?pedal, gas.?pedal, pedal.?box, frizione (it) | pedal(s), gaspedal, clutch | **brake** alone (discs, calipers, brake lights), clutch_disc, throttle body/cable, gas tank/cap, brake pad | 315 (74 / 241) | 220 · 147 · 119 · 12 |
| Handbrake (extra) | hand.?brake, e.?brake, parking brake, freno a mano, handbremse, frein à main | hbrake, handbrake | brake lights (`ext_emissive_brakelights` contains e_brake) | 120 (2 / 118) | 102 · 43 · 16 · 3 |
| Pillar trim (extra) | pillar.?trim, a/b/c.?pillar, montante (it) | pillar(s) | ext / paint / glass (`a_pillar_black_glass`) | 66 (1 / 65) | 52 · 20 · 1 · 0 |
| Window / seat net (extra) | window.?net, safety.?net, int.?net, whole-word net / rete, netting | net(s) | **bonnet** (`BONNET_SUB0` contains net_), `massaneta` (pt door handle), fishnet, grills | 183 (10 / 173) | 114 · 172 · 155 · 36 |

**3. Most common real names per part.** Counts are numbers of cars. Source: [parts.txt](file:///D:/ClaudeData/tmp/interior_scan/parts.txt).
- **Seat**
  - Meshes: `seat` 40, `int_seat` 37, `seatl_a` 32, `_seat` 29, `seats` 19, `geo_seat(s)` 27, `seatdriver` / `seatpassenger` 9, `asientos` 8, `bride_vios3` 8, `rally_seat_l_shell` / `_fab` 7, `geo_sedili` 5 (Kunos).
  - Materials: `int_seat` 42, `IntSeatCloth` 31, `seat_alcantara` 20, `int_seat_fabric` 11, `INT_OCC_Fabric_Seat` 9, `int_alcantara_sedile_occ` 7, `int_stoffa_extra_sedile` 7.
  - Textures: `seat` 22, `seatdriver` 13, `int_seat` 11, `bride_seat` 8, `banco2` 6.
  - Detail: `leather_seat` 17 (10 of them Kunos).
- **Fabric / leather**
  - Materials: `int_alcantara` 43, `leather` 39, `int_seams` 39, `int_cuciture` 39 (Kunos 38), `int_fabric` 36, `int_leather` 35, `steer_leder` 17.
  - txDetail: `alcnt` 195 (Kunos 70), `leather` 132, `tessuto` 33, `int_cloth` 31, `t_fabric_archliner_d_grey` 28, `leather_top` 28.
- **Belts**
  - Meshes: `CINTURE_ON` 303, `CINTURE_OFF` 284, `seatbeltl_a` 29, `geo_belt_passenger` 8.
  - Materials: `int_belt` 86, `int_belts` 54, `seatbelt` 43, `belt_schroth` 34, `int_cinture` 33, `int_cintura` 25.
  - Textures: `Cockpit_Belt` 140 (Kunos 76), `belt` 43, `cinture` 41, `belt_schroth_color` 37, `cintura_color` 30, `cpbelt` 30.
- **Dash**
  - Meshes: `dashpad_a` 56, `dashstructure_a` 53, `int_dash` 50, `dash` 25, `dashboard` 17.
  - Materials: `int_dash` 29, `dash` 25, `int_dashboard` 12 (Kunos 10), `tableau_bord` 9, `int_plancia` (Kunos).
  - Textures: `dash` 22, `planche_de_bord` 9, `mat_plancia` (Kunos `abarth500`).
- **Door cards**
  - Meshes: `doorcardlf_a` 39, `int_door_l` / `_r` 28, `geo_int_door_l` / `_r` 17, `GEO_IntDoor_L` (Kunos), `geo_inner_door_l_hr` (Kunos).
  - Materials: `int_doortags` 20, `doorpanel` 3, `int_door_card` 3, `interieur_porte` 2.
- **Cage**
  - Meshes: `rollcage` 49, `int_rollcage` 35, `_rollcage` 31, `rollcage_a` 27, `int_cage` 20, `rollbar` 11, `jaula_hr` 4.
  - Materials: `rollcage` 32, `int_rollcage` 30, `cage` 26, `int_welding` 14.
  - Textures: `car_paint_roll_cage` 39, `weld` 12, `rollbar_col` 10.
  - txDetail: `detail_tube_mix2_colour` 13, `detail_tube_mix_colour` 10.
- **Carpet**
  - Meshes: `floor_a` 58, `carpet` 23, `geo_int_carpet` 11, `int_carpet` 11.
  - Materials: `int_carpet` 40, `carpet` 27, `int_occ_carpet` 13, `int_tappeto*` (Kunos).
  - Textures: `carpet` 40, `carpet_grey` 23.
  - txDetail: `carpet` 90 (Kunos 45).
- **Headliner**
  - Meshes: `roof liner` 21, `interior_headliner` 6, `int_headliner` 5, `introof` 4, `cieldetoit2` 2.
  - Materials: `headliner` 22, `int_roof` 6, `ceiling` 3, `teto` 2.
- **Steering wheel**
  - Meshes: `STEER_HR` 115, `GEO_Steer_HR` 58, `GEO_Steer_LR` 54, `steeringcolumn_a` 26, `steering_wheel` 24.
  - Materials: `int_steer` 68, `int_steer_carbon` 57, `steer_leder` 17, `volant` 12, `volante` 9, `int_logo_volante` (Kunos).
  - Textures: `steer_hr2` 42, `int_steer_colour` 38, `int_steer_ao` 38, `skin_volante` 7 (Kunos).
- **Console**
  - Meshes: `centerconsolebezels_a` 43, `centerstackbezels_a` 41, `centerconsolestructure_a` 23.
  - Materials: `console` 6, `int_pelle_consolle` 3 (Kunos).
  - Textures: `int_console_labels` 7, `int_console` 4.
- **Gear**
  - Meshes: `gear` 32, `_gear_shifter` 27, `shifter` 21, `geo_shift` 18 (Kunos 15), `geo_guaina_cambio` 16 (Kunos 15), `geo_manopolo_cambio` 6, `int_gearstick` 7.
  - Materials: `shifter` 10, `int_skinned_gearshift` 5, `int_guaina_cambio` 4, `boule_levier` / `metal_levier` (fr) 2.
- **Pedals**
  - Meshes: `pedals_a` 43, `_pedals` 39, `pedals` 22, `throttlepedal` / `brakepedal` 7, `carbonio pedaliera` 5.
  - Materials: `int_pedals` 33 (Kunos 20), `int_pedali` 11, `int_pedali_nm` 7.
  - Textures: `pedals` 30, `pedali` 24 (all Kunos).

**4. False-friend sizes.** Each probe gives the number of distinct per-car names that contain the substring, and how many of them really are the part. — [probes.py](file:///D:/ClaudeData/tmp/interior_scan/probes.py)
- `int`: 29,747 names, of which 24,463 carry a real interior marker. The rest are mostly:
  - `CINTURE_ON` / `OFF` (c-**int**-ure, 303 / 284 cars)
  - `internal_glass` 172
  - `carpaint` 160, `ext_carpaint` 90, `car_paint` 67, `car_paint_rims` 54
  - `EXT_Carpaint_Inst` 64
  - `intercooler` 46
  - `car_paint_roll_cage` 45

  The glued but real interior names `intplastic` (37), `intchassis` (33) and `intalcantra` (31) are missed by a whole-token-only rule.
- `seat`: 2,632 names, 2,345 of them really seats. The rest are seatbelts (`seatbelt` 59, `seatbeltl_a` 29…), plus `valve_seat` (engine, 4) and `seat_leon_wheel_style1` (car brand).
- `wheel`: 3,583 names, only 851 of them steering wheels.
- `brake`: 4,084 names, only 32 of them pedals.
- `door`: 5,244 names, 967 of them door cards. The others are outer doors, door glass, handles, jambs and sills.
- `roof`: 441 names, 92 of them headliner.
- `floor`: 370 names, 363 of them interior floor (safe on its own, but watch `underfloor` and `chassis_floor`).
- `cage`: 780 names, 707 of them roll cage. The rest are lamp cages, `soft_top_cage` and `undercage`.
- `stick`: 340 names, only 48 of them gear sticks. The rest are mostly stickers.
- `gear`: 402 names, 304 of them gear levers.
- `shift`: 836 names, 760 of them shifters. The rest are shift lights and paddles.
- `knob`: 174 names, 118 of them gear knobs (`gopro_knob` is a false friend).
- `lever`: 182 names, only 39 of them gear levers. The rest are suspension levers.
- `center`: 953 names, 449 of them console. `centre`: 72, 9 of them console. `middle`: 168, none of them console.
- `belt`: 2,089 names, 1,863 of them seat belts. Two real belt forms are easy to miss: the glued `cpbelt` (32) and `int_handlebelt` (29, a door pull strap in Kunos cars).
- `dash`: 2,352 names, 1,929 of them colourable dash. The rest are mostly `dash_glass` (26) and `dash_light` (15).
- `tube`: 272 names, 240 of them cage tubes. `weld`: 140 names, 136 of them cage welds.
- `inst`: 352 names. In ACC-derived mods `inst` means **instance**, not instrument: `EXT_Carpaint_Inst` is the outside body paint in 64 cars, for example `alpine_a110_gt4` on `GEO_BODY` and `GEO_DOOR_L`.
- `net`: 979 names, 678 of them nets. The rest include `bonnet` 26.
- `boot`: 205 names, 21 of them gear boots. The rest are the car boot (trunk).
- `console`: 559 names, 419 of them console. The rest are overhead consoles.
- `cab` matches cables (`int_cables` 21) as well as cabin.
- `pad` matches `dashpad_a` but also brake pads and paddles.
- `trim` (774) and `panel` (253) are interior or exterior with no way to tell from the name.
- `porta`: in the ADC Corvette C5 cars, `porta00-24` are rubber door seals (material `borracha`).
- `sw` is mostly the steering wheel (`sw_buttons`, `int_sw_leather`), but `turnlight_sw_left` is not.
- `pit` matches cockpit but also `led_pit` (pit-limiter light).
- `skin`: in Kunos interiors `INT_*Skin*` means **leather** (detail `leather.dds` in 39 materials, `skin_volante` = steering wheel leather). It is not the livery.

**5. Names that look interior but must never be recoloured**
- Kunos material counts: `INT_Display` 45, `INT_Windscreen` 34, `INT_LCD` 33, `INT_GLASS` (ksWindscreen shader), `int_vetro_display` 9.
- In mods: `internal_glass` 172, `int_display` 63, `int_lcd` 56, `int_racelogic` 33, `motecnl` 31.

Sources: [parts.txt](file:///D:/ClaudeData/tmp/interior_scan/parts.txt), [probes.py](file:///D:/ClaudeData/tmp/interior_scan/probes.py).

**6. Kunos names by surface, not by part**
- In `ks_mazda_mx5_cup` the interior materials are `INT_OCC_Plastic_GREY`, `INT_OCC_Carpaint`, `INT_OCC_Alcantara`, `INT_OCC_Skin_GREY`, `INT_OCC_Plastic_Detail_GREY`, `INT_OCC_White_Paint` (roll bar), `INT_SeatBelts` and `INT_Seams`. They sit on meshes `GEO_Cockpit_HR_SUB0..5`, `GEO_IntDoor_L_SUB0` and `GEO_Rollbar`.
- In `ks_porsche_991_carrera_s` they are `INT_Skin_Grey`, `INT_Plastic_Flat`, `INT_Carpet_fine` / `_Base`, `INT_Alcantara` and `INT_Plastic_Speaker_Octagon`.
- So the Kunos dashboard is seldom named. Only 69 Kunos cars match "dash", and 6 match "headliner".

Source: [cars/ks_mazda_mx5_cup.json](file:///D:/ClaudeData/tmp/interior_scan/cars/ks_mazda_mx5_cup.json), [texsample.py run](file:///D:/ClaudeData/tmp/interior_scan/texsample.py).

**7. Surface words on colourable interior materials**

| Surface words | Kunos materials (cars) | Mod materials (cars) |
|---|---|---|
| leather / pelle / leder / cuir / skin | 502 (139) | 921 (306) |
| alcantara / alcnt / suede | 150 (82) | 506 (286) |
| fabric / cloth / tessuto / stoffa / velvet | 197 (119) | 518 (312) |
| plastic / plastica | 532 (163) | 1,737 (489) |
| carbon | 198 (112) | 755 (366) |
| metal / alu / chrome / steel | 571 (172) | 2,497 (528) |
| rubber / gomma / borracha | 104 (89) | 265 (198) |
| carpet | 117 (81) | 199 (130) |
| carpaint inside the cabin | 74 (68) | 39 (32) |

Source: inline run built on [analyze2.py](file:///D:/ClaudeData/tmp/interior_scan/analyze2.py).

### Inferences
- A practical detection order for the app:
  1. A mesh under `COCKPIT_HR`, `COCKPIT_LR`, `STEER_*` or `CINTURE_*`, or a material or texture with an interior token, means interior.
  2. Drop glass, display, LCD, gauge, needle, LED, emissive, decal, logo and mirror, the ksWindscreen shader and alpha-blended materials.
  3. Give the part from the dictionary above.
  4. If no part matches, fall back to a surface group (leather / alcantara / fabric / plastic / carbon / metal / carpet). This matters most for Kunos cars, which name surfaces rather than parts.
- `int` must be a whole token: `INT_`, `_int_`, or camelCase `Int` followed by a capital. Glued forms (`intdash`, `intplastic`, `intseat`…) need a short whitelist of the following words. Never match `int` inside a word (paint, print, tint, cinture, intercooler, intake).
- The most dangerous words are `wheel`, `brake`, `door`, `roof`, `center`/`middle`, `stick`, `lever`, `mat`, `inst`, `net` and `boot`. They should never be used without a qualifier or an interior marker.
- Italian is the second language of AC interiors because of Kunos: cinture/cintura, cuciture, tessuto, sedile/sedili, volante, cambio/guaina/manopolo, pedali, plancia, tappeto/tappetini, rete, tubi, pelle, velluto, gomma, plastica, metallo, vetro, loghi, piantone. Portuguese (borracha, painel, porta, teto, banco, acabamento, adesivo) and French (planche de bord, tableau, arceau, ciel de toit, levier, pommeau, portière, tapis) also show up in mods.

### Gaps
- No ground truth for "is this mesh really inside the cabin" beyond node names and words. Meshes with generic names (`polySurface123`, `Object004`, `polymsh_detached65`) can only be placed by position inside the body, which was not done.
- Spanish and German words are rare in this install, and some words from the brief never appear. Cars containing each word anywhere in a mesh, material or texture name (substring count):

  | Word | Cars | Word | Cars | Word | Cars |
  |---|---|---|---|---|---|
  | volant(e) | 83 | cucitur | 67 | tessut | 64 |
  | sedil | 47 | cambio | 42 | pedali | 33 |
  | tappet | 15 | cruscott | 14 | planche | 13 |
  | asiento | 10 | plancia | 10 | tableau | 10 |
  | banco | 9 | teto | 9 | painel | 8 |
  | jaula | 5 | moquette | 3 | teppich | 2 |
  | tablero | 2 | boden | 1 | arceau | 1 (plus a skin file in the Mygale cars) |
  | lenkrad | 1 | | | | |

  **Never found:** `sitz`, `himmel`, `schalt`, `cielo`, `tapis`, `alfombr`, `forro`. They stay in the dictionary as cheap extras, but on this PC they are unproven. (Inline count over [cars/](file:///D:/ClaudeData/tmp/interior_scan/cars/).)
- What the `COCKPIT_HR` / `COCKPIT_LR` nodes do in the game was not checked against official docs. A web search turned up only GTPlanet modder posts, which describe them as a high-res / low-res cockpit LOD switch that CSP also uses ([GTPlanet mods thread](https://gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-3372)). The page itself returned HTTP 403, so this rests on the search summary only.

## How are interior textures set up (atlas vs per-part, sizes, shaders, colour in the detail texture)?

### Takeaway
Kunos interiors almost always use a grey, colourless ambient-occlusion atlas as txDiffuse (alpha about 0) and put the colour and grain into small tiling **txDetail** textures. Those detail tiles have names like `leather_seat.dds`, `alcnt.dds`, `carpet.dds` and `PlasticDetail_red.dds`, and skins replace them by name. Mods are mixed:
- about a third of their colourable interior materials use 1–8 px solid-colour swatch textures;
- others use big baked colour atlases (`int_ao`, `interior_lod0`, `leather_dark`, up to 2048–4096 px);
- 40 % use txDetail the Kunos way.

### Cited Findings
**Shaders.** These are the shaders on colourable interior materials. — [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)

| Shader | Kunos (3,206 materials) | Mods (14,158 materials) |
|---|---|---|
| ksPerPixelMultiMap | 936 | 2,935 |
| ksPerPixelMultiMap_NMDetail | 779 | 2,554 |
| ksPerPixelNM | 412 | 1,522 |
| ksPerPixel | 326 | **3,320** |
| ksPerPixelReflection | 325 | 1,572 |
| ksPerPixelNM_UVMult | 152 | 1,670 |
| ksPerPixelAT_NM | 78 | 192 |
| ksPerPixelAT | 77 | 168 |
| ksSkinnedMesh / ksSkinnedMesh_NMDetaill | 36 / 24 (gear boots, leather) | - |

**Samplers.**
- Kunos: txNormal 2,466, txMaps 1,824, txDetail 1,824, txNormalDetail 822.
- Mods: txNormal 9,029, txMaps 5,641, txDetail 5,641, txNormalDetail 2,611, txEmissive 24.
- Kunos: **57 %** of interior materials have a txDetail, and 39 % have an AO-named txDiffuse (occ / ao / occlusion / ambocc / bake). 1,166 materials have both.
- Mods: 40 % have a txDetail and 20 % an AO-named txDiffuse. 2,689 have both.

**Sizes (largest side) of interior txDiffuse.**
- Kunos (materials per size):

  | Size | ≤16 px | 32 | 64 | 128 | 256 | 512 | 1024 | 2048 |
  |---|---|---|---|---|---|---|---|---|
  | Materials | 225 | 68 | 154 | 138 | 519 | **1,158** | 900 | 41 |
- Mods: 1 px **2,921**, 32 px 1,376, 128 px 1,450, 256 px 857, 512 px 1,959, **1024 px 2,056**, 2048 px 1,185, 4096 px 82.

**Sizes of txDetail.**
- Kunos: mostly 256 px (499) and 512 px (747) tiles, plus 128 px (230) and a 4 px swatch group (121).
- Mods: 1 px 1,517, 512 px 1,896, 256 px 714, 1024 px 337, 2048 px 47.

**Atlas vs per-part.** — [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)
- Distinct interior txDiffuse per car:
  - Kunos: median 8 (quartiles 6–11).
  - Mods: median 12 (quartiles 8–18).
- The largest interior texture covers a median **49 %** of the interior mesh area in both groups.
- An atlas (one texture covering more than half the interior area and used by 3 or more materials) appears in 76 of 179 Kunos cars and 148 of 617 mods.
- Most common largest interior textures:
  - Kunos: `Cockpit_LR` 22, `INT_OCC` 17, `INT_Cockpit_OCC` 13, `INT_Occlusion` 10, `INT_Cockpit_Occlusion` 9, `interiors_ao` 7.
  - Mods: `int_ao` 28, `hi_carbfbd` 23, `leather_dark` 20, `int_occ` 17, `INT_Occlusion_Colour` 17, `interior plastic` 16, `interior` 14, `carpet` 11, `interior_lod0` 10.

**Where the colour is (decoded textures).** — [texsample.py](file:///D:/ClaudeData/tmp/interior_scan/texsample.py)
- `ks_porsche_991_carrera_s`
  - `INT_Occlusion.dds` is 1024², grey (saturation 0.00) with alpha mean **0.00**.
  - Material `INT_Skin_pointed` (ksPerPixelMultiMap_NMDetail, detailUVMultiplier 50) takes its colour from `leather_seat.dds` (512×256, mean RGB 0.66/0.57/0.44, tan).
  - Material `INT_Plastic_Grey_satinata_BO` takes it from `plastic_bottom.dds` (tan, UV multiplier 180).
- `ks_mazda_miata`
  - `int_AO3.dds` is 1024², grey, alpha 0.00.
  - `int_plastic_red` uses `PlasticDetail_red.dds` (pure red, multiplier 180).
- `ks_toyota_ae86`
  - `interiors_ao.dds` is grey with alpha 0.00.
  - `INT_body` uses `metal_detail.dds` as its detail.
- Detail UV multipliers seen: 15–250 for tiles, 0 for no tiling.

**Body paint inside the cabin.**
- Kunos `INT_Carpaint` / `INT_OCC_Carpaint` (inner door skins, cockpit metal) use `metal_detail.dds`, the same detail texture the skin overrides for the body colour. Examples: `ks_mazda_mx5_cup` and `ks_porsche_991_carrera_s`.
- In 68 of 179 Kunos cars and 115 of 646 mods, a skin-overridden detail texture is also on interior parts. — [shared.py](file:///D:/ClaudeData/tmp/interior_scan/shared.py)

**Swatches.** — [markers.py](file:///D:/ClaudeData/tmp/interior_scan/markers.py)
- Mods: 4,592 of 14,158 colourable interior materials (32 %, in 341 cars) use a txDiffuse of 8 px or less, or one named `rgbaXXXXXXXX` (exporter-made solid-colour textures such as `rgba010101ff`).
- Kunos: 63 of 3,206 (2 %, 32 cars).
- In every parsed car, every interior txDiffuse is embedded in the kn5, so a skin replaces it by file name.

**Material props.** All interior materials carry ksAmbient / ksDiffuse / ksSpecular / ksSpecularEXP / ksEmissive. Materials with a detail texture also have `useDetail` and `detailUVMultiplier`. NMDetail materials have `detailNormalBlend`. — [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)

**Placeholder detail textures.** A `null.dds` placeholder is the txDetail in 137 Kunos and 251 mod interior materials. Kunos `NULL.dds` is 16 px, grey, alpha 0.

### Inferences
- In Kunos-style materials the AO atlas alpha is about 0 and the detail tile carries the colour, and skins change interior colour by swapping the tile (next question). So the detail texture is what decides the visible colour wherever the diffuse alpha is low.
  - Recolouring a Kunos interior part therefore means writing a tinted copy of its **txDetail** into the skin. The grain and alpha of the tile must be kept.
  - Repainting the AO atlas would not do it.
  - This is inferred from texture data. The exact shader formula was not confirmed from documentation (see Gaps).
- A detail tile is per material, not per mesh. One tile can colour several parts (for example `leather_seat.dds` on seats and other trim). The app should show which parts share a tile before changing it.
- `metal_detail.dds` is the body paint colour. Interior carpaint parts follow it on purpose, so the app should not override it for an interior change.
- For mods there are three cases:
  1. **Swatch-based**: override the 1–8 px texture by name. But swatches such as `black.dds` are often shared with outside parts, so check usage first.
  2. **Detail-based**: as for Kunos.
  3. **Baked colour atlas** (`int_ao`, `interior_lod0`, `leather_dark`, `hi_carbfbd`): needs UV-region painting with the texel map, like the body livery.
- The low-res cockpit texture (`Cockpit_LR.dds` and similar, used by `COCKPIT_LR`) needs the same colour change. Otherwise the interior seen from outside or at distance keeps the old colour. This is inferred from the separate LR textures. In-game LOD behaviour was not tested.

### Gaps
- The shader maths (how txDiffuse alpha mixes txDetail in ksPerPixelMultiMap and NMDetail, and what txMaps channels mean for interiors) could not be confirmed from an official source. Searches found only forum fragments ([assettocorsamods thread](https://www.assettocorsamods.net/threads/ksperpixelmultimap-how-textures-are-made.3478) has no formula; the [CSP sdk-shaders repo page](https://www.github.com/ac-custom-shaders-patch/sdk-shaders) only lists shader variants). The "colour lives in txDetail" conclusion rests on decoded textures and on what skins override.
- CSP `ext_config` interior overrides (for example SHADER_REPLACEMENT on interior materials) were not scanned.

## How many skins already ship interior textures, and under which names?

### Takeaway
Overriding interior textures from skins is common. In **295 cars** (53 Kunos, 242 mods), 2,361 skins ship textures used only by interior materials. Another 121 cars touch the interior only through textures shared with the outside, mainly `metal_detail.dds`. Kunos skins swap leather, alcantara and carpet detail tiles. Mod skins mostly swap cage colour swatches and interior colour textures.

### Cited Findings
**Totals** (skins made by Ratty's4Skin left out). — [skins2.py output](file:///D:/ClaudeData/tmp/interior_scan/skins2.py), [skins.txt](file:///D:/ClaudeData/tmp/interior_scan/skins.txt)
- 825 cars with skins, 8,901 skins (Kunos 2,215, mods 6,686).
- Skins that override **any** texture used by a colourable interior material: 422 cars (Kunos 100, mods 322), 4,152 skins.
- Skins that ship textures used **only** inside (not by any outside material; helmets, plates and decals left out): **295 cars (Kunos 53, mods 242), 2,361 skins (451 + 1,910)**.
- Cars whose skins touch the interior only through textures shared with the outside: Kunos 46, mods 75.

**Interior-only override names, by number of cars**

| Name | Cars | Name | Cars |
|---|---|---|---|
| `car_paint_roll_cage.dds` | 37 | `carpet.dds` | 20 |
| `metal_detail_int.dds` | 18 | `alcnt.dds` | 14 |
| `leather.dds` | 13 | `leather_seat.dds` | 12 |
| `leather_top.dds` | 11 | `steer_hr2.png` | 10 |
| `metal_detail_2.dds` | 9 | `leather_dark.dds` | 9 |
| `planche_de_bord.dds` | 9 | `leather_bottom.dds` | 8 |
| `leather_2.dds` | 7 | `metal_detail_3.dds` | 7 |
| `interior_lod0.dds` | 6 | `interior metal.dds` | 6 |
| `nardi_grip.dds` | 6 | `cuciture.dds` | 6 |
| `steer_hr1.png` | 5 | `int_net_colour.dds` | 5 |
| `plastic_bottom.dds` | 5 | `speakers_octagon.dds` | 5 |
| `belt.dds` | 4 | `seat.dds` | 4 |
| `floor.dds` | 4 | `seatpassenger.png` | 4 |
| `belt_schroth_nm.dds` | 4 | `rollcage.dds` | 3 |
| `dash.dds` | 3 | `cockpit_belt.dds` | 3 |
| `int_ao.dds` | 3 | `cab_door.dds` | 3 |

**Kunos override names, by number of skin files**

| Name | Files | Name | Files |
|---|---|---|---|
| `metal_detail.dds` | 1,007 (body paint, also on interior carpaint) | `leather_seat.dds` | 94 |
| `leather_bottom.dds` | 89 | `skin_00.dds` | 84 |
| `plastic_bottom.dds` | 58 | `speakers_octagon.dds` | 56 |
| `metal_detail_int.dds` | 49 | `leather_top.dds` | 49 |
| `carpet.dds` | 46 | `leather_2.dds` | 45 |
| `leather_1.dds` | 40 | `leather_3.dds` | 40 |
| `alcnt.dds` | 37 | `custom_trim_d.dds` | 28 |
| `cuciture.dds` | 27 | `leather_trim_red.dds` | 26 |
| `int_sponsor.dds` | 19 | `plastic_top.dds` | 19 |
| `tessuto_color.dds` | 17 | `plasticdetail_color.dds` | 17 |
| `leather_cust1.dds` | 17 | `mat_plancia.dds` | 16 |

**Which sampler slot is overridden.**
- By skin files: txDetail 5,066, txDiffuse 2,846, txNormalDetail 293, txMaps 223, txNormal 155.
- By cars (interior-only overrides): txDiffuse 214, txDetail 148, txMaps 30, txNormal 21.

**Parts touched by interior-only overrides** (cars): seat fabric 105, seat 95, cage 92, steering 77, dash 53, belts 32, carpet 31, door cards 21, gear 18, headliner 8, pedals 7, console 6, handbrake 6.

**Sizes of the overriding files:** 4 px 852 files, 16 px 146, 32 px 547, 64 px 367, 128 px 764, 256 px 845, **512 px 2,586**, 1024 px 719, 2048 px 690, 4096 px 92. — [skins.txt](file:///D:/ClaudeData/tmp/interior_scan/skins.txt)

**Cars where most skins carry interior textures** (skins doing it / skins in the car):
- `legends_ford_34_coupe` 78/79 (`cockpitcolor1.dds`, `cockpitcolor2.dds`)
- `mygale_m21_f4` 55/55 (`arceau.dds`, `headrest.dds`)
- `rr_phantom` 42/43 (`carpet`, `cuciture`, `leather1/2`, `int_ao`)
- `ford_sierra_cosworth_rs500_dtm_90s` 29/32 (`bodycolor_inside.dds`, `cagebake.dds`)
- `adc_nissan_180sx` 28/28 (`car_paint_roll_cage.dds`, `interior metal.dds`)
- `actk_citroen_ax_proto_morette` 26/27 (`rollcage_metal_detail.dds`, `tole_metal_detail.dds`)
- `gt4_mercedes_amg` 18/31 (`metal_detail_int.dds`)
- `ks_lamborghini_aventador_sv` 28/34 (`custom_trim_d`, `leather_trim_red`, `console_trim_detail`)
- `ks_corvette_c7_stingray` 25/25 (`leather_1/2/3`, `cuciture`)
- `ks_ferrari_812_superfast` 19/24 (`leather_cust1/2`)
- `ks_ruf_rt12r` 17/17 (`metal_detail_int.dds`)
- `ks_toyota_ae86` 16/16 (`tessuto_color`, `plasticdetail_color`)
- `ks_porsche_991_carrera_s` 14/16 (`alcnt`, `carpet`, `leather_seat/top/bottom`, `plastic_bottom`)

Source: [skins2.py](file:///D:/ClaudeData/tmp/interior_scan/skins2.py).

**Decoded examples of skin-supplied interior textures.** — [texsample.py](file:///D:/ClaudeData/tmp/interior_scan/texsample.py)
- `ks_porsche_991_carrera_s` `leather_seat.dds`, 13 skins: black 0.16 grey (`00_guards_red`), white 0.96 (`02_white`), tan (`04_racing_yellow`), red 0.48/0.22/0.23 (`05_carmine_red`).
- `ks_toyota_ae86` `tessuto_color.dds`: grey / blue (0.18/0.25/0.34) / red (0.53/0.11/0.10) by skin.
- `adc_nissan_180sx` `car_paint_roll_cage.dds`: a **4×4** swatch per skin (white, magenta, yellow).
- `ks_ruf_rt12r` `metal_detail_int.dds` (256²): orange / green / black / blue / light blue by skin.

**Interior-looking skin files that match no texture in the main kn5.** 79 cars have these. Examples: `car_paint_roll_cage.dds` 81 files, `c4_cockpit1b_detail.dds` 68, `carpet.dds` 22, `holdenv8_dash.dds` 20, `seatdriver.png` 15, `mat_plancia.dds` 10, `car_paint_interior.dds` 10, `interior_paint_main1.dds` 8, and normal maps with double extensions (`seatdriver_nm.png.png`). — [skins.txt](file:///D:/ClaudeData/tmp/interior_scan/skins.txt)

### Inferences
- Skin overrides already work for interiors and are widely used. The app can write interior textures into a skin folder under the model's exact texture name, the same way it does for the body.
- The names skins use are the model's own detail and swatch names, not one standard. The app must read each car's materials; a fixed name list will not work.
- Unmatched interior files in skins are probably left over from other versions of the car, other LOD kn5s, or CSP configs. The app should not rely on them, and it should ignore them when it copies stock skins.
- When a stock skin already overrides an interior texture, the app's "edit existing skin" mode should start from that skin's file, not the model's. For example, the 991's skins carry different leather colours.

### Gaps
- LOD kn5 files (`*_LOD_B.kn5`…) and `COCKPIT_LR` in other kn5 files were not scanned. Unmatched skin files may match textures there.
- Whether CSP `ext_config` sections inside skins change interiors (some skins carry `ext_config.ini`) was not checked.

## How often is an interior texture shared with outside parts?

### Takeaway
Rarely in any way that matters. A large shared texture appears in 24 of 179 Kunos cars and 148 of 646 mods, but it covers only about 1 % of the interior area (median). The real crossover is the **paint colour detail**: Kunos `metal_detail.dds` on interior carpaint parts (68 Kunos cars, 115 mods). In mods, small colour swatches (`black`, `rgba010101ff`, `chrome`) are also shared between inside and outside.

### Cited Findings
**Large shared textures.** — [shared.py](file:///D:/ClaudeData/tmp/interior_scan/shared.py)
- An interior txDiffuse of 256 px or more is also used by a non-interior material in 24 of 179 Kunos cars and 148 of 646 mods.
- Median interior-area share on those textures: 0.01 (quartiles 0.00–0.04 Kunos, 0.00–0.05 mods).
- Examples: Kunos `ext_details_d`, `bolts_d`, `skin_00`, `nuts_and_bolts`; mods `darkalumi`, `trans_1`, `mk2_rev_white`, `black`, `chrome`, `slcr_blackalu`.

**Livery on interior parts.** The skin-overridden outside txDiffuse (the livery) is also on interior parts in only 3 Kunos cars and 23 mods.

**Paint detail on interior parts.** A skin-overridden detail texture used outside is also on interior parts in 68 Kunos cars and 115 mods. — [shared.py](file:///D:/ClaudeData/tmp/interior_scan/shared.py)

**Shared with EXT-named materials.** Interior textures also used by `EXT_`-named or body-named materials: 32 Kunos cars and 168 mods. The shared textures are mainly swatches and hardware: `black` 35, `rgba010101ff` 18, `rgba000000ff` 13, `null` 12, `chrome` 8. Median area share is 0.01 for Kunos and 0.05 for mods. — [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)

### Inferences
- Before overriding a texture for an interior colour, the app should check that no outside material uses it. A check per texture name is enough.
- Where a texture is shared:
  - small swatches: warn, or skip the part;
  - `metal_detail` / carpaint: tell the user that part takes the body colour.

### Gaps
- "Outside" here means "not classed as interior by name or node". Generically named meshes could be put on the wrong side. 3D-position checks (inside the cabin box) were not done.

## Kunos cars vs mods

### Takeaway
Kunos is uniform. Every car has `COCKPIT_HR`/`LR`, `STEER_HR`, `INT_`-prefixed materials named by surface, grey AO atlases of 512–1024 px with coloured detail tiles, Italian part words, and a separate `Cockpit_LR` texture. Mods vary a lot: 67 % have `COCKPIT_HR`, 75 % use `INT_`. Some use English part names, Forza `_a` names or ACC `_Inst` names. They lean on solid-colour swatches and big baked colour atlases, and their skins more often ship interior colour files.

### Cited Findings
| Feature | Kunos (179 cars) | Mods (646 cars) |
|---|---|---|
| COCKPIT_HR / COCKPIT_LR | 179 / 179 | 432 / 185 |
| STEER_HR | 179 | 588 |
| CINTURE_ON | 168 | 244 |
| `INT_` token in materials | 97 % | 75 % |
| `interior` word in materials | 17 % | 44 % |
| Interior materials with txDetail | 57 % | 40 % |
| AO-named interior txDiffuse | 39 % | 20 % |
| Interior materials on ≤8 px swatches | 2 % | 32 % |
| Distinct interior txDiffuse per car (median) | 8 | 12 |
| Most common shader | ksPerPixelMultiMap 936, NMDetail 779 | ksPerPixel 3,320, MultiMap 2,935 |
| Separate low-res cockpit texture | 157 | 52 |
| Cars with interior-only skin overrides | 53 | 242 |

Sources: [markers.py](file:///D:/ClaudeData/tmp/interior_scan/markers.py), [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt), [skins2.py](file:///D:/ClaudeData/tmp/interior_scan/skins2.py), and the node counts above.

**Example dumps.** — [cars/ks_audi_r8_lms_2016.json](file:///D:/ClaudeData/tmp/interior_scan/cars/ks_audi_r8_lms_2016.json)
- Kunos `ks_audi_r8_lms_2016`:
  - Interior materials `INT_PLASTIC_DARK`, `INT_CARBON1`, `INT_METAL_GRAY`, `INT_RUBBER` and `INT_PLASTIC_WHITE` are all on `INT_OCC.dds` (1024², uncompressed) with different detail tiles (`plastic_dark.dds`, `Merc_Carbon_INT.dds`, `rubber.dds`, `plastic_white.dds`).
  - The seats use `INT_seat_OCC.dds` (512²) with `carpet_blue.dds` / `carpet_dark.dds` details.
  - The belts are `INT_CINTURA` on `cinture.dds`.
- Mods built on the ACC pattern (bcrc / gt4_* cars): `INT_Occlusion_Inst` with detail `INT_Cab_Color.dds`, `INT_Occlusion_Colour.dds` or `metal_detail_int2.dds`. The colour again sits in the detail texture. — inline query over [cars/](file:///D:/ClaudeData/tmp/interior_scan/cars/)

**Kunos-only Italian words** seen in names: `cuciture` (stitching), `tessuto` (fabric), `sedili` (seats), `guaina_cambio` (gear gaiter), `manopolo_cambio` (gear knob), `pedali`, `plancia`, `tappeto` / `tappetini`, `piantone` (steering column), `rete` (net), `tubi_maniglia` (grab-handle tubes), `skin_volante`, `logo_volante`. — [parts.txt](file:///D:/ClaudeData/tmp/interior_scan/parts.txt), [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)

### Inferences
- For Kunos cars an interior colour feature can be a **material/detail-tile picker**: list the interior materials with their detail tile and tint the tile into the skin. Swap both the HR detail and the `Cockpit_LR` texture.
- For mods the app needs three modes: detail tile, swatch override, or atlas painting by UV region (like the body). The app has to pick the mode per material from the texture size and whether a txDetail is present.
- Mods named by Forza-style `_a` parts (19 %) are the easiest to map to parts, because they spell out `seatl_a`, `dashpad_a`, `doorcardlf_a`, `pillartrim_a`, `pedals_a`, `steeringwheel_a` and so on.

### Gaps
- Protected cars (all RSS, several Gravy Garage) could not be read. Their naming is unknown and their interiors cannot be recoloured from the kn5.
- Kunos was identified by folder name and author. A few mods named `ks_*` by other authors would have been counted as mods only if their author field is set.
