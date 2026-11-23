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

# v43 (23 Nov ~08:10) - Nik: fix the right front arch tip; "make sure the arch isn't crumpled anywhere"
kk_v40.build_kit around the arches (z > 0.28, within 0.62 m of a wheel), replacing v42's subdivide/press:
1. blend along the surface: from the kit edge on the wing (boundary verts < 10 mm off) every vertex within 7 cm across the
   surface has its gap to the body scaled by smoothstep(r/7cm) (the crest stood 1-3 cm proud ~1 cm in from the edge);
2. trim faces lying within 3 mm of the body; 3. spike relax: edge verts > 3 mm off their neighbours' line moved 70 % to it and
   re-seated (that was the blade at the top-rear corner, both sides identical); 4. 6 light smoothing passes (edge/on-body fixed);
5. nothing under the wing's surface (re-seated 1.2 mm out).
kk_v40_extras.cut_hidden_arches: a wing face only counts as hidden if the kit is > 8 mm in front on a horizontal ray AND rays angled
up-out and down-out (horizontal-only removed wing faces visible from above past the kit's edge = dark gaps).
Dead ends tried (in git history of kk_v40.py): nearest-point flush (folds on the swage line), subdivide+press (crumpled),
edge-line relax on the subdivided mesh (sawtooth), "above the wing seen from above" cut (ate the arch tops).
Known: faint lighter shading where the kit lies on the rear quarters at the very edge; small original Kadett ridges on the rear-left arch top.

# 23 Nov ~08:12 - REVERTED to v41 (Nik: v43 "ruined the shape of the arch")
Live = export_staging_v41 again (v43 kept in live_backup_before_revert_to_v41_*). NOTE: tools/blender/kk_v40.py now contains the
v42/v43 arch-top passes - rebuilding from it does NOT give v41; v41 = git version of kk_v40.py at commit 39cf9b7 (Claude-).

# v44 (23 Nov ~08:20) - Nik: "remove the part that creates a step to the body ... keeping the exact original bodykit arch shape"
= v41 shape + trim only: faces lying within 3 mm of the body around the arches removed, spike-only edge fix, nothing under the wing;
NO surface blend / smoothing (RESHAPE = False in kk_v40.py). Edge gap after trim: median 1.3 mm, p95 5.7 mm.
Arch cut-out keeps the multi-direction cover test (no gaps). Known: a small sliver at the rear-left arch's top-front edge.

# 23 Nov ~08:25 - REVERTED to v41 again (Nik: v44 "looks like utter crap"). Live = export_staging_v41.

# v45 (23 Nov ~08:40) - Nik: kit 5 mm in towards the body all round; sill vents black carbon (or bonnet mesh)
tools/blender/kk_v45.py on the v41 blend: KK_kit, KK_kit_inner, KK_fins, vent/sill fills + backings, exhaust trim rings moved
5 mm towards the centreline (x), all LODs; vent fills (KK_sill_mesh, KK_vent_mesh) -> NICK3_carbon, planar UV 1/m like the diffuser.
Arch shape otherwise = v41. Backup: v41 is export_staging_v41.

# v46 (23 Nov ~08:40) - Nik: "big improvement, move it in another 5 mm": kk_v46.py = kk_v45.py run on the v45 blend (kit 10 mm in in total). export_staging_v46. v45 kept in export_staging_v45.

# v47 (23 Nov ~08:55) - Nik: see-through arches; belts gone, anchors still on the shelf
tools/blender/kk_v47.py on the v46 blend. Belts: v40's belts_to_floor produced NaN vertices (straps vanished in game) - original strap
meshes re-taken from the kit-0 live import and re-routed (centreline binned, y 0.55 -> floor anchor y 0.95, floor z 0.13 + 15 mm);
CINTURE_ON (driving belts, switched off by NICK3) active again and re-routed; anchor eyes (Object001csaas/001, CINTURE_OFF_SUB1__lr
islands on the shelf) moved to the floor anchors. Arches: KK_arch_liners = black (#166GG45) curved roof R 0.335 over each wheel
(-25..205 deg) from x 0.50 (front, wheels steer) / 0.60 (rear) out to 0.975, plus an inner wall; both faces drawn; LOD B/C too.
Known: stair-stepped edge of the cut wing panel visible on the inside of the front pods (from the v40 arch cut, per-face).

# v47b (23 Nov ~09:00) - liners stuck out past the kit in game (x 0.975 > kit outer after the 10 mm move): liners now x_in..0.86, arc -10..190 deg. Reinstalled.

# v48 (23 Nov ~09:05) - Nik: working yellow rectangular fog lamps under the indicators on high beam; rear lights brake only
tools/blender/kk_v48.py on the v47 blend: KK_fog_housing (black) on the valance (x +-0.475..0.605, z 0.108..0.163, y -1.77..-1.838),
KK_fog_bezel (#503ds), KK_fog_lens (own mesh + own yellow material KK_fog_lens); LOD B/C too. ext_config: new
[EMISSIVE_HIGHBEAM_...] NAME=KK_fog_lens COLOR=255,170,20,8 CAST_LIGHT=1. Rear: lights.ini BRAKE_0/1 OFF_COLOR 0,0,0 (no tail glow,
data.acd patched, backup data.acd.BACKUP_20261123_0905; data/ mirrored); [EMISSIVE_BRAKE_1] NAME=all rear lens sections, INPUT=BRAKE,
INPUT_THRESHOLD 0.95 -> 0.05; rear fog glow (EMISSIVE_EXTRA_B_2 FOG_GLASS) removed; indicators/reverse already off (v37).
Not verified in AC: fog lamp light on high beam, rear lenses off with headlights on.

# v48b (23 Nov ~09:10) - Nik: rear lights only must not show orange/white; normal tail lights with headlights stay. Reverted the v48 rear changes: data.acd from data.acd.BACKUP_20261123_0905 (lights.ini OFF_COLOR 12/25 again), data/lights.ini from its backup, ext_config from BACKUP_before_v48 + the fog-lamp section re-added. Orange/white stay off as since v37 (red lens material on indicator/reverse sections, their CSP emissives emptied).

# TODO next (Nik 23 Nov 09:11, "fix that after usage reset"): old arch lips still visible under the kit's arches as jagged teeth
Cause: kk_v40_extras.cut_hidden_arches deletes whole faces of fenders_a_SUB2 / body_a_SUB1 -> sawtooth edge; since v44 the cover
test only removes faces hidden from 3 ray directions, so the original lip band under the kit's lip stays and shows through the gap.
Plan: cut the wing/quarter panels along a SMOOTH arc (bmesh.ops.bisect_plane per angle step / boolean with a cylinder-like cutter)
a few mm inside the kit's lip radius per angle (kit lip profile already measured in cut_hidden_arches as prof[(wheel, side)]),
delete everything inside that arc, all four arches; arch liners (kk_v47) then close the view. Check in side + low close views
before installing. Live = v48b; v47/v48 blends build from the v46 blend.

# v49 (23 Nov ~12:45) - Nik: red goes white in sun; paintable wing/mirrors/splitter/diffuser; belts black in game; LODs old; old arch lips
tools/blender/kk_v49.py (+ kk_v49_export.py) on the v48 blend -> escort_v49.blend, export_staging_v49.
- Paint: Material #25DQW had txMaps = AO_BODY (the skin livery) -> red channel = full specular -> red flashed white. Now txMaps =
  ESCORT_BODY_MAPS.dds (4x4 solid 170,230,190 = spec .67 gloss .9 refl .75), added to the kn5 texture list.
- KK_wing, KK_splitter, NICK3 carbon (diffuser), AERO_mirror_L/R -> Material #25DQW, planar UVs stacked in a free AO_BODY strip
  u 0.91-0.995, v 0.06-0.79 (occupancy checked). Default skin: that strip is dark, so they look as before until a skin paints it.
- Belts: CINTURE_ON (shown in game) had Material #101III/AO_98 vs CINTURE_OFF (#100TT34/AO_97, the yellow ones in CM): ON meshes now
  copies of the OFF meshes (SUB1, SUB0, SUB1__lr).
- Arches: exact-boolean cut of fenders_a_SUB2/body_a_SUB1 along a smooth curve 10 mm outside the kit's lip (kit profile per 3 deg,
  5-pt smoothed), x 0.5..1.2 per side, all four arches.
- LODs B/C/D regenerated from the main model (decimate 0.30/0.12/0.04, LOD files without textures) - old LODs had the NICK3 spoiler.
- v49b: headlight lens glassrhl_a (lights.ini LIGHT_0) had kn5 active 0 since the NICK3 work (v25 had it on) -> on, all LODs. Re-exported export_staging_v49.
- v49c: belts - v49 copy of OFF into ON undone (driver not wearing them, still not yellow in game): CINTURE_ON meshes back from the v48 blend; all CINTURE meshes on own yellow material copies (KK_belt_*, textures BELT_Y_97/98/STRAP from the belts own AO, alpha 255, isAdditive 0). Anchor eyes keep #100TT34. Why CM showed yellow is not found.

# 23 Nov ~13:25 - brakes (Nik: car "wants to keep going" under braking): data.acd brakes.ini MAX_TORQUE 1680 -> 2000, electronics.ini [ABS] SLIP_RATIO_LIMIT 0.12 -> 0.18 (acd_patch.py; backups data.acd.BACKUP_20261123_1322 / _1323). data/ folder has no brakes.ini/electronics.ini.
- v49d: the v49 exact-boolean arch cut left sliver triangles that poked out behind the rear arches as spikes in game (confirmed in a render of the installed kn5). kk_v49d.py deletes slivers (L > 4 cm, area/L^2 < 0.02) of fenders_a_SUB2/body_a_SUB1 in the arch zones (240 + 573). Re-rendered: gone.
