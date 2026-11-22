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
