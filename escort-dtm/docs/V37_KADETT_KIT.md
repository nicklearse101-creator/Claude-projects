# v37 - Kadett S2 body kit on the Escort (22 Nov 2026)

Installed live 22 Nov ~19:50. Backup of what was live: `live_backup_before_v37_kadett_kit_20261122_1950\` (4 kn5s +
ext_config.ini + MD5SUMS). Staging: `export_staging_v37_kadett_kit\`.

## Pipeline (all headless Blender 5.2, scripts in tools\blender)
1. `kk_load.py` - imports the LIVE Escort kn5s (main + LOD b/c/d); round trip checked byte-identical (all 4 True).
   -> `blender\escort_v37 kadett kit 0 live import.blend`
2. `kk_addkadett.py` - adds opel_kadett_s2.kn5 in scene KADETT -> `... kit 1 with kadett ref.blend`
3. `kk_build.py` - removes the NICK3 front clip, sides, tail slats, grille recess, boot wing, front half of the
   NICK3 carbon (old splitter); adds KK_kit / KK_splitter / KK_fins / KK_wing; deepens the diffuser fins -> `... kit 2 built.blend`
4. `kk_finish.py` - rear fixes (below), kit into LOD B/C/D (decimated 0.5 / 0.25 / 0.10), export -> `... kit 3 finished.blend`
5. `qrender.py` - quick workbench renders.

## Fit (measured)
- Wheel centres: Kadett F (-1.561, 0.344) R (0.851, 0.344), tyre r 0.31; Escort F (-1.222, 0.144) R (1.185, 0.127), r 0.268.
- Arches + bumper: scaled 0.865 (tyre ratio) in y/z about each wheel centre, x unchanged (Kadett arch outer 0.988
  covers the Escort tyre outer ~0.94).
- Sills: Escort door bottom edge z 0.054 (y -0.6) .. 0.047 (y 0.5), x 0.687. Kadett sill box (z 0.093-0.404, outer
  x 0.933) squashed so its top sits 4 mm under the door edge, inner edge tucked to x 0.680, bottom z -0.090 (same as NICK3).
  Blended into the arches over Kadett y -1.30..-1.00 and 0.30..0.55.
- Wing: translated (0, +0.311, -0.183) - rear end to rear end, boot deck to deck; parented to hood_trunk (opens with the boot).
- Fins behind the rear wheels: rear-arch transform. Splitter: front-arch transform, cut behind the bumper.
- Diffuser inner fins (x +-0.20, +-0.48): bottom edge now z -0.120 (front) .. -0.095 (rear), like the Kadett's flat-bottomed fins.
- Kit paint: Material #25DQW, UV fixed at (0.857, 0.398) like the NICK3 kit; carbon parts: NICK3_carbon.

## Rear lights / bumper / paint - cause and fix
- 44 rear nodes had kn5 `active = 0` (bumperr_a, tail lights, lenses, bulbs, plate, trunk_a_SUB1, trunklivery_arsw ...),
  set by the NICK3 work; v25 backup had them active. Re-activated (57 node flags main, 17 in LOD B and C).
  Front bumper / side markers / exhaust_a_SUB0/SUB3 / CINTURE_ON / glassrhl_a left as they were.
- body_a_SUB1 used `STOCK_Material #25DQW` (STOCK_metal_detail.dds / STOCK_AO_BODY.dds) - skins colour the car via
  metal_detail.dds, so the rear never got the paint. Now `Material #25DQW` like the rest of the shell (same definition otherwise).
- Red only: INDICATOR_LR/RR + REVERSE_GLASS take BRAKE_GLASS's lens material, their _IN reflectors BRAKE_IN's.
  ext_config: rear turn signals (EMISSIVE_TURNSIGNAL_LEFT_2 / RIGHT_2) and EMISSIVE_REVERSE_0 names emptied.

## Not verified / known
- Not checked in AC yet (look, LODs, door opening past the sill top, wing vs boot opening, collider untouched).
- Sill vents squash to slots (sill is 0.45x the Kadett's height). Kadett's sill/arch rivets and wing decals not copied.
- ext_config has an older "WIDER TARMAC EXTENSION" (MESH_ADJUSTMENT SCALE 1,1.06,1 on fenders_a_SUB2 / body_a_SUB1) -
  not ours, left alone; if CSP applies it, the shell is 6 % taller in game than in Blender.
- Reverse/indicator sections are red but unlit; brake lighting still from lights.ini BRAKE_0 = BRAKE_GLASS only.

# v38 (22 Nov ~20:30) - Nik: holes, floating grille, no splitter supports, see-through arches, front bumpers missing, rough join, mesh in the sill holes, wider track
Script `tools\blender\kk_v38.py` (on "kit 2 built" blend) -> `escort_v38 kadett kit blended.blend`, export_staging_v38_kadett_kit. Backup of v37: live_backup_before_v38_kadett_blend_*.
- Holes: NICK3 had cut the wheel openings out of fenders_a_SUB2 (8776->6104 tris) and body_a_SUB1 (20547->19281) - whole panels restored from BACKUP v25.
- Front bumper, side markers, front indicators (Object016/017) were deleted meshes - restored from v25 (LOD B/C: under the LOD root).
- Join: kit boundary verts that sat on the Kadett body (<10 mm, 192) pulled onto the Escort body (+1.5 mm), shift faded over 70 mm; arch<->sill transitions Laplacian-smoothed.
- Kit given 2.5 mm thickness with rims (solid from behind). Even-offset made 2 runaway verts at -14 m - off, clamp 1.0.
- Vents (6 loops) filled: steel mesh (Material #41dda ptn_grillsquare, alpha tested, 120 repeats/m) 6 mm in + black backing 30 mm in.
- Splitter rods: Kadett Plane.009 thin islands, front-arch transform, Material #503ds. NICK3 alloy grille at the nose (y < -1.6) removed.
- Track: data.acd suspensions.ini TRACK F 1.3345 -> 1.570, R 1.3735 -> 1.580 (tools/acd_patch.py, only that file re-encrypted, round-trip checked;
  data.acd.BACKUP_20261122_2005 in the car folder); data/ mirrored. AC puts the wheel centre at TRACK/2 (Kadett: 1.50/2 = its 0.749 pivot).
  Tyre outer ~0.945/0.955 vs arch lip 0.988. Handling WILL change (wider track) - old setups / Setup Coach baseline.

# v39 (22 Nov ~20:45) - Nik: track too wide (put back), mesh in only 1 of 4 sill vents, step between arches and body, plate RS 4000
- Track: data.acd restored from data.acd.BACKUP_20261122_2005 (TRACK 1.3345 / 1.3735), data/ from its backup; the wide acd kept as data.acd.BACKUP_v38_wide_track_*. Nik sets track himself.
- `kk_v39.py` (on "kit 2 built"): near the joins the kit is draped onto the body (within 25 mm of the join, eased out by 85 mm, 1.2 mm off the body);
  back skin is its own part KK_kit_inner, thickness tapering to 0 at the joins, cast shadow OFF (the v38 2.5 mm double skin gave
  shadow acne - the fine diagonal pattern in Nik's shots). Exporter: new mesh nodes now take cast/visible/transparent/renderable from kn5_flags.
- Sill vents: one steel-mesh sheet + black backing per sill just inside the straight outer face (all 4 vents); loop fills only for the arch vents.
- Plate: tools/plate_rs4000.py - "RS" kept, "0" = the plate's own last 0 mirrored, "4" drawn with the plate's line/stroke weights;
  normal map rebuilt with the gradient->normal fit from the original pair. Originals kept as kn5_textures_v37/PLATE_2*.dds.ORIGINAL_RS1800.
- Known: small notch at the front arch's top-rear corner; faint dashed shut line along the door bottom where the sill top meets the body.
- 22 Nov 20:32: v39 was overwritten in the car folder by a save of the v38 model (Content Manager open with v38; Nik moved
  WHEEL_/SUSP_ nodes: front x 0.80725 -> 0.82989, rear 0.80675 -> 0.80945). That save kept as live_cm_save_2032\. Its 8 node
  matrices copied exactly into v39 (verified identical) and v39 reinstalled 20:37. Lesson: close CM's showroom/model tools
  (or reload the car) before installing, or a save from CM puts the old model back.

# v40 (23 Nov ~00:45) - Nik's list of 22 Nov 20:53 + RaceLogic placement
Build: `tools\blender\kk_v40.py` (+ `kk_v40_extras.py`) on "kit 2 built" -> `escort_v40 kadett kit.blend`, export_staging_v40. Backup of v39: live_backup_before_v40_*.
- Sill mesh both sides: new faces' normals weren't updated before the orientation check, so the right sheet faced inward (culled). Sheets now
  follow the sill outer edge (flat cap 0.030 in the straight part - the v39 sheet poked through the sill top = the "long gap"/dashed line;
  front part rises with the vent). Sill top under the doors: no pull/drape (v37 tuck); restored v25 sill lip under the shelf trimmed.
- Arch-to-sill open corner (right side showed a dark triangle) patched.
- Original arches cut: fenders_a_SUB2 / body_a_SUB1 faces fully hidden behind the kit (side rays) or inside the kit's wheel openings
  (|x| > 0.68, radius < kit lip radius per 5 deg) deleted (3366 / 1714 faces).
- Exhaust: Y-piece from the V8 collector (0.21, 0.03, -0.02) to twin side exits (x +-0.948, y 0.18, z -0.03) just behind the rear sill vents,
  steel pipes r 32 mm, tips r 40 mm, sooty inside, black trim ring on the sill. flames.ini ADDED to data.acd (there was none - no flames at all):
  2 flames, model coords, out and slightly back, INTENSITY 45, FLASH_THRESHOLD 4. ext_config: discharge 0.02 -> 1.0, flat-shift on (1.5),
  limiter on (0.7), flame light x3, exhaust smoke particles enabled at the side exits.
- Scuttle knob: islands of grille_a_SUB4_SUB0 + body_a_SUB5 by the left wiper (Object014 was a wiper part - left alone).
- Belts: CINTURE_OFF shoulder straps (+__lr) re-routed from the parcel shelf (y 1.34) to the floor behind the seats (y 0.95, floor z 0.13).
- Door back faces: AERO_door_back_L/R = flipped door skins 1.5 mm inward under the door dummies (window frame visible from inside).
- Dash: tripmeter box (ZERO/TOTAL/INTERVAL + TRIPMASTER) removed island-wise from the merged interior meshes inside
  x -0.515..-0.165, y -0.63..-0.38, z 0.37..0.735; the original dash recess behind it stays.
- RaceLogic: Kunos ks_bmw_m4_gt3 unit (Object001/002 islands + RACE_LOGIC screen + decal) on a black bracket on the dash top at
  (0.02, -0.565), facing the driver's eye (0.29, 0.05, 0.95) - beside the wheel, visible without moving the head. Display:
  extension/racelogic_display.lua (running lap time, last lap held 4 s), font extension/fonts/impact.ttf, [SCRIPTABLE_DISPLAY_...] in ext_config.
- Plate: RS 4000 in the RS 1800 layout (RS untouched, 4000 in the 1800 space, digits interlocking 20.8 px).
- Nik's WHEEL_/SUSP_ node positions (CM save 22 Nov 20:32) re-applied.
- Not verified in AC: flames/particles frame (model coords assumed from the M4), RaceLogic script, LOD look.

# v41 (23 Nov ~08:00) - kit paint matches the body
Kit (KK_kit + KK_kit_inner) still uses the body's Material #25DQW, but its texture coordinates now follow one vertical strip of the
body's own rear quarter (body_a_SUB1, y 1.8, behind the rear wheel) chosen by vertex height (kx.column_uvs). AO_BODY on the side panels
shades 139 (z 0.12) .. 211 (z 0.5); the old single texel (0.857, 0.398) was 238, so the kit read lighter than the body. The strip is plain
on the hillclimb livery skin too. Tried first: per-vertex UVs from the panel inboard of each vertex - dragged UV seams/other islands onto
the flares (scribbles), dropped. Backup of v40: live_backup_before_v41_*.

# v42 (23 Nov ~07:50) - Nik: "a piece of the kit slightly proud of the bodywork" at the top of the front arches
Cause: the Kadett flare's upturned top edge, draped onto the wing, stood a few mm proud as a band, with a fin at the top-rear tip.
kk_v40.build_kit now, around the arches (z > 0.28, within 0.62 m of a wheel): subdivides the kit (2 cuts - the Kadett mesh is coarse),
trims every face lying within 7 mm of the body (the kit edge then starts where it lifts off, zero thickness), presses what stands
<= 12 mm off the wing straight in along x (fade to 25 mm; nearest-point snapping folded on the swage line), then 12 smoothing passes.
Known: small tip left at the RIGHT front arch's top-rear corner, faint creases at the very edge. Backup of v41: live_backup_before_v42_*.
