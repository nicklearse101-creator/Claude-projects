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
- v49d (2nd): sliver clean-up moved into kk_v49.py right after the cut, deleting only slivers with a vertex not in the pre-cut panel (30 + 74); the 1st v49d deleted original swage strips (white lines in game). Library-loaded objects have stale matrix_world - do not compare against them. Flames: ext_config discharge water-temp threshold 70 -> 0, rpm min 5500 -> 3500, probability 1.0, flat-shift rpm 3000 (untested in game).

# v50 (23 Nov ~14:20) - 1980s VFD cluster (Nik picked concept C)
tools/blender/kk_v50.py on the v49 blend -> escort_v50 vfd.blend, kk_v50_export.py -> export_staging_v50. Backup live_backup_before_v50_*.
- Off (kn5 active 0): needles/hubs Object001-006, dashstructure_a_SUB29, lamp strip Object011(+__lr), odometer Object012, trip knob gaugecluster_a_SUB0/1.
- Object010 / DASH_NIGTH / gaugecluster_a_SUB2 also hold the centre-console gauges: only their cluster islands (x > 0.10) deleted.
- Old face-panel bezels of dashstructure_a_SUB28(+__lr) that sat in front of the screen deleted (islands >60 % inside the screen area).
- VFD_SCREEN: cluster-glass outline shrunk 4 mm, 3 mm behind the glass (346 x 116 mm), UV 0..1 (u = driver's left->right, v up),
  material = copy of the RaceLogic ksPerPixel material named VFD_SCREEN.
- extension/vfd_display.lua (1200x400): rev bar graph 34 segments green/amber/red, mph, gear (red near the limiter), fuel bar + litres,
  lap time, indicator arrows, main-beam lamp; ksEmissive 1.4 = backlit. ext_config: [SCRIPTABLE_DISPLAY_...] VFD_SCREEN; odometer
  sections (Object012) and ARROW_TEMP/_2 blanked; cluster needle lights removed from the dash EMISSIVE_LIGHT (console needle kept).
- NOT verified in AC: script drawing, text orientation (u/v), glow level.

## v50b (23 Nov) - VFD mirror + surround fix (kk_v50b.py on "escort_v50 vfd.blend", export kk_v50_export.py)
- VFD_SCREEN UVs: u = 0 at the driver's left (was mirrored in game).
- VFD_BACK: black backing (Material #166GG45) in the screen plane, 45 mm wider each side, 12 mm above the screen,
  plus a 9 mm ceiling strip under the binnacle hood - no view through to the engine bay from the driver's eye.
- Render check (vfdchk2.py, red = see-through): driver/high/side/left views clean; a thin red sliver only from a
  very low eye under the hood lip. Bay view: nothing pokes through the dash top. In-game look not yet confirmed.
- Live backup: D:/ClaudeData/tmp/kadett/live_backup_before_v50b_1418

## Flames v2 (23 Nov 14:31) - still no flames in game (smoke fine)
- Checked: CSP Particles FX flames ENABLED=1; CSP log has no errors for the car; flame position = pipe tips in model space
  (same as the smoke, root transform identity); [EXHAUST_FLAMES] keys match the 123 installed cars that use it.
- Changed: flames.ini EDIT_BIG=1 (all Kunos cars), INTENSITY 60, flames bigger (VSIZE 0.08-0.35, LSIZE 0.6, SIZE_MULT 1.8),
  direction ~27 deg rearward so they show from the chase cam; ext_config intensities 3.0, discharge 3000-9500 rpm
  (old max 8500 = the limiter), limiter flames from 8000. Backups: data.acd.BACKUP_20261123_1431, ext_config.ini.BACKUP_before_flames2_*.
- Not verified in game. If still nothing: CSP Settings > Particles FX > Flames > Debug mode shows which trigger fires.

## Flames v3 (23 Nov 15:10) - own Lua flames
- Nik: v2 still "no flames whatsoever". CSP's [EXHAUST_FLAMES] never fires for this car (offline session, no CSP log
  errors, Particles FX flames enabled) - cause not found.
- New car script extension/exhaust_flames.lua ([SCRIPT_...] in ext_config, all LODs): ac.Particles.Flame emitted at the
  pipe tips via car.bodyTransform - pops on throttle lift >4000 rpm, upshifts with gas, limiter bounce; crackle flicker.
- Backup: ext_config.ini.BACKUP_before_lua_flames_*. Not verified in game.

## Ride height zero = floor (23 Nov 18:19)
- Setup screen showed ~150 F / 200 R mm: car.ini [RIDE] pickups were -0.37 (Kunos Mk1 value, CG-relative), far above the floor.
- Measured lowest body (model space): sills/kit -0.084 at the front axle, kit -0.090 at the rear (diffuser -0.127 sits 0.3 m behind
  the rear axle). Physics y = model y + GRAPHICS_OFFSET y (-0.40) -> PICKUP_FRONT_HEIGHT=-0.484, PICKUP_REAR_HEIGHT=-0.490.
  Expected readings ~36 F / ~80 R mm at the same setup; 0 = sills on the ground.
- Front wing uses height_front_CL/CD.lut (ground-height multipliers) - both shifted by -0.114 so aero is unchanged.
- Backup: data.acd.BACKUP_before_rideheight_zero. Not checked in game.

## Aero v2 (23 Nov 18:25) - Kadett kit aero
- Old aero = Kunos Mercedes 190 Evo2 wings (CL*A ~0.37, 37% front) + Kunos Escort Mk1 body Cd 0.45 x 1.83.
- Measured (model, physics = model + GRAPHICS_OFFSET): splitter 1.92 m wide at z 1.64 / y -0.47; rear wing 2.14 x 0.35 m at
  z -2.44 / y 0.46; diffuser 1.68 m wide, ~z -1.85 / y -0.50; frontal area ~1.9 m2.
- New: BODY Cd 0.44 x 1.90; FRONT (splitter) CL 0.13-0.19 (setup 0-3) x 1.92 with GH LUT peaking ~18 mm sill height, 1.0 at ~38 mm,
  stall below ~8 mm; REAR wing CL 0.26-0.44 (setup 0-4) x 0.749, CD 0.08-0.125; new WING_3 DIFFUSER CL 0.06 x 1.68 with rear GH LUT
  (peak ~40 mm, 1.0 at ~80 mm).
- Default (3/3): CL*A 0.77 (~1440 N at 200 km/h, was ~690 N), 38% front (was 37%); range 0.55-0.80. CdA 0.94 (was 0.91).
- Backup: data.acd.BACKUP_before_aero_v2. Not driven yet.

## v51 flames as meshes (23 Nov 19:10)
- Diagnosis (VFD readout S/E/F/H): the car script runs and emits thousands of ac.Particles.Flame particles, CSP's own flames
  never fire (F0, even with [EXHAUST_FLAMES] removed), nothing draws - yet the Kunos Supra's flames work. Cause not found.
- Now: kk_v51_flames.py adds KK_flame_L1..3 / R1..3 (3 crossed double-sided planes, lengths 0.22/0.34/0.48 m) at the side-exit
  tips, material KK_flame (ksPerPixel, blend 1, emissive 6, KK_FLAME.png generated flame texture). exhaust_flames.lua hides
  them and flickers one length per side on lift-off / upshift / limiter; handbrake >0.5 + >2000 rpm = test flicker.
- Both [EXHAUST_FLAMES] blocks renamed [EXHAUST_FLAMES_OFF_TEST]; VFD still has the temp S/E/F/H readout.
- Live backup: D:/ClaudeData/tmp/kadett/live_backup_before_v51_1910. Not seen in game yet.

## v51b (23 Nov 19:20) - flames confirmed, VFD tyres
- Mesh flames were black: kk_v51_flames.py wrote ksEmissive into the float+vec2 slots (props = name, f, v2, v3, v4); script
  now sets ksEmissive 8 at load, build script fixed (p[4:7]). Nik: "woohoo flames!!". Handbrake test + VFD S/E/F/H readout removed.
- VFD: tyre block between gear and indicators, front row on top: I/M/O surface strip + core temp + pressure, ProTyres-style
  colours (blue cold -> green in window -> yellow/orange -> red). Windows from the tyre curves: S 65-80, M 70-90, H 75-95 C;
  29 psi ideal (+-1 psi green); Vintage GT70 uses optimum +-10 C, 37 psi. Speed/gear shifted left; fuel litres moved off the
  right arrow. Preview: docs/vfd_tyres_preview.png (not yet seen in game).
- 20:36 v51b: CM showroom (no scripts) showed all 6 flame meshes black. Rebuilt: flame dummies active 0 in the kn5 (exporter wraps
  new meshes in a dummy), ksEmissive 6 in the correct vec3 slot; script switches the dummy nodes (findNodes) and keeps setting
  emissive 8 on the meshes. Backup live_backup_before_v51b_2036. In-game show/hide of an inactive kn5 node not yet confirmed.

## ESCORT 16" - separate car ford_escort_mk2_tuned_16 (24 Nov 17:15), the 14" car untouched
- Nik chose "exact scale, car rides higher": arches already touch the 14" tyres (~0-1 mm), so a 16/14 scale needs the wheels
  lower against the body (measured need: front 40 mm, rear 56-65 mm at the kit lip / fins / quarter).
- Model: kk16_wheels.py on "escort_v51 flames.blend" -> escort16_v1.blend: every mesh under WHEEL_LF/RF/LR/RR (rim, tyre,
  disc) scaled 16/14 about the hub (tyre R 0.272 -> 0.308). Export kk16_export.py -> export_staging_16, files ford_escort_mk2_tuned_16*.kn5.
- Data: escort16_data.py re-keys data.acd for the new folder; tyres.ini all compounds RADIUS 0.268->0.3063, RIM_RADIUS
  0.1778->0.2032, WIDTH x16/14 (0.320 / 0.3314), ANGULAR_INERTIA x1.5; suspensions BASEY F -0.250->-0.290, R -0.280->-0.345
  (wheel centre y rel. CG; checked vs model: 0.144-0.40=-0.256, 0.127-0.40=-0.273); lods.ini names. Body ~79 mm higher F,
  ~104 mm R; gearing effectively 14% taller; front splitter now higher (less downforce from the height LUT).
- Folder: copied animations/sfx/skins/texture/ui/extension/collider/shadows (no backups); sfx bank renamed
  ford_escort_mk2_tuned_16.bank + GUIDs.txt paths/bank name rewritten; ui name "... 16in". Not driven yet.
- 17:16 16in aero: same tables (the height LUTs already cut splitter/diffuser at the new heights: readings ~115 F / ~184 R mm
  -> front GH 0.70, diffuser GH 0.63); BODY span 1.90 -> 2.05 (taller tyres, gap under the car), Cd 0.44 -> 0.45, CL -0.04
  (underbody lift); rear wing default ANGLE 3 -> 1. Result at default (front 3, rear 1): ~900 N @200 km/h, ~32% front
  (37% if lowered to ~85/150 mm). Same tables at wing 3 would be 23% front = big high-speed understeer.
  Backup data.acd.BACKUP_before_aero16 (in the 16in folder). Not driven.
- 17:26 16in v2 (Nik): tyres back to the 14in widths. kk16b_width.py on escort16_v1 -> escort16_v2.blend: wheel meshes x14/16
  across the car about the hub (tyre meshes 0.246 / 0.259 wide again, radius 0.310). tyres.ini WIDTH back to 0.28 / 0.29,
  ANGULAR_INERTIA = 14in x1.31 (was x1.5). Backup D:/ClaudeData/tmp/kadett/live16_backup_before_v2_*. Front tyres no longer
  stick out past the flares. Not driven.

## ESCORT 15" - separate car ford_escort_mk2_tuned_15 (24 Nov 17:50); Nik: the 16" ruined the handling (car ~80-105 mm higher)
- Nik: "15 wheels, same size tyres, besides the obvious" = garden swap. The model rims are really 13" (rim lip radius 0.182 =
  13" rim + flange; CM shows R13) although tyres.ini said RIM_RADIUS 0.1778 (14").
- kk15_wheels.py on "escort_v51 flames.blend" -> escort15_v1.blend: rims (not discs) x15/13 radially, width unchanged; tyres
  unchanged in shape, moved out radially by the rim-lip growth (+28 mm: 0.175-0.272 -> 0.203-0.300). kk15_export.py.
- escort15_data.py: RIM_RADIUS 0.1905, RADIUS 0.268 -> 0.296, ANGULAR_INERTIA x1.15; suspension, widths, aero untouched ->
  car 28 mm higher, gearing ~10% taller. Tyre tops now ~28 mm into the arch lips/liners (the arches are for later).
- Folder built like the 16" one (sfx bank/GUIDs renamed, ui "... 15in"). The 16" car is still installed. Not driven.

## 24 Nov 18:05 - 15" brakes + rear-wheel wobble fix (all cars)
- 15" brakes: kk15b_brakes.py - discs (for_rotorxx) and calipers (for_caliperxx, under SUSP_xx) x15/13 in the wheel plane
  (disc R 0.133 -> 0.153), same thickness; brakes.ini MAX_TORQUE 2000 -> 2310 (bigger effective disc radius).
- Wobble: the original wheel model's rims were off the spin axis (tyres true to 0.1 mm): rear lip/barrel +1.8..+2.6 mm,
  rear spoke face +2.9 mm, front lip +1.4 mm, front face +1.1 mm -> rims bobbed against the tyres. kk_wheel_centre.py centres
  each rim part (ring parts on their outer circle, spoke faces on the hub/nut circle 0.03-0.06 m) -> all within 0.3 mm.
  13" car: "escort_v52 wheels true.blend" -> export_staging_v52 (installed). 15": rebuilt from v52 (kk15_wheels -> escort15_v1,
  kk15b_brakes -> escort15_v4, export_staging_15, installed). 16" rebuilt (escort16_v4) but Nik had deleted that car - not installed.
  Note: the 13" car's tyres.ini still says RIM_RADIUS 0.1778 (14") though the model rims are 13" - left as is.
- Backups: D:/ClaudeData/tmp/kadett/live_backup_<car>_before_wheelfix_<time>. Not seen in game.

## 24 Nov 18:29 - 15" SetupCoach-equivalent setups (tools/escort15_setups.py)
- All 9 SetupCoach_Optimized*.ini of the 13" car -> setups/ford_escort_mk2_tuned_15/generic/SetupCoach_<track>[_1].ini:
  rods -28 clicks (body/aero back to the 13" heights), final drive x0.296/0.268 (15" final.rto now 2.77 2.91 3.09 3.25
  3.41 3.49 3.68 3.85 - added 3.41 and 3.85), brake power x0.956 (100 -> 96); everything else identical.
- Nurburgring rear rods 25 -> 0 (3 mm short of equivalent). AC was running while final.rto was written (applies next load).
- 19:16 15" car: rear physics TRACK 1.5735 -> 1.5345 (= front) for rotation (wider rear = rear grip = push); rear
  [GRAPHICS_OFFSETS] WHEEL/SUSP_LR/RR 0.03 -> 0.0495 so the visual wheels stay put. Backup data.acd.BACKUP_before_rear_track.
  Not driven. Setup ideas given to Nik (not applied): diff preload 80 -> 30-40, coast 35 -> 20-25; rear ARB 5000 ->
  12500-17500, front 40000 -> 35000; brake bias 70 -> 66-67; less rear toe-in.
- 19:38 15" car, Nik: other way round - rear back to TRACK 1.5735 / offsets 0.03; FRONT TRACK 1.5345 -> 1.5735 (= rear),
  front WHEEL/SUSP offsets 0.05 -> 0.0305 so the visual front wheels stay put. Backup data.acd.BACKUP_before_front_track. Not driven.
- 20:06 15" car engine: power_dtm.lut reshaped like a race-cammed 4.0 V8 (Rover-style): same ~349 bhp (now @7800), peak
  358 Nm @6000; 61% of peak at 3000 rpm (was 84%), 46% at 2000; small dip at 4300; sharper fall-off 8100-8600.
  ui_car.json curves/specs = physics (was +15%: 409 Nm / 400 bhp). Backups data.acd.BACKUP_before_torque_curve,
  D:/ClaudeData/tmp/kadett/ui_car_15.BACKUP_before_torque.json. No Rover V8 sound on Nik's PC. Not driven.

## 24 Nov 20:13 - 15" car: bonnet exhausts replace the side exits (kk15c_bonnet_exhaust.py -> escort15_v5.blend)
- KK_exhaust_pipes/tips/dark rebuilt (same names): per bank a 70 mm pipe from the header turn-down (x 0.31, y -1.00, z 0.27)
  up/outward through the bonnet at x 0.525, y -1.02 (just outboard of the bonnet vents), 100 mm tip pointing up + 17 deg out
  + 12 deg back, rolled lip, soot disc, black collar on the bonnet. Side exits gone.
- Flame meshes rebuilt at the tips (kk_v51_flames fixed: plane axes now square to the flame dir - vertical flames were slivers).
- ext_config PARTICLES_FX_EXHAUST_0/1 + flames.ini: tips (AC) +-0.5551, 0.7532, 0.9999; dir +-0.3008, 0.9324, -0.2005.
- Installed (AC was running - restart). Backup D:/ClaudeData/tmp/kadett/live15_backup_before_bonnet_exh_*. Not seen in game.
- 20:27 15" car v6 (Nik: chrome, 8 of them): kk15d_zoomies.py -> escort15_v6.blend: 8 stacks (4 per bank, y -1.35/-1.22/-1.09/
  -0.97, x +-0.525), 45 mm primaries from the ports, 90 mm tips, collars; own KK_chrome (ksPerPixelMultiMap, white maps,
  fresnel 0.85/1.0, useDetail 0 - detail slot = skin colour) + cylindrical UVs (old pipes had no UVs -> black). Flames: one
  per stack in KK_flame_L/R1..3 (lengths 0.15/0.24/0.34). ext_config: 8 PARTICLES_FX_EXHAUST_0..7; flames.ini 8 flames.
  Material-name fix: KK_flame.001 -> KK_flame in blend + kn5_materials list. Backup live15_backup_before_zoomies_*. Not seen in game.
- 20:45 15" stacks "ghosted": tube faces pointed inward (AC culls back faces -> see-through walls, torn tops). kk15d_zoomies
  tube() now orients faces outward (inner lip inward, 12 mm deep); chrome isAdditive 0, fresnelC 0.92, diffuse 0.2;
  flame material name clash fixed in the script. Checked with backface-culling render. Installed.
- 15" exhaust_flames.lua (repo copy extension/exhaust_flames_15in.lua): limiter flames GREEN (ksEmissive 0.15,9,1.2 x flame
  texture) when revs rise within 200 rpm of the limiter with gas > 0.5; lift-off/upshift flames orange. Not seen in game.
- 20:50 Nik: chrome stacks still looked wrong (mirror chrome reflected dark -> black). kk15e_stack_cage_mat.py -> escort15_v7:
  stacks use the roll cage's Material #26DDDSA (AO_1 atlas) with all UVs at the cage tube's median UV (0.308, 0.4226);
  KK_chrome dropped. Installed. Not seen in game.
- 20:58 Still black in game. Cause: normal-mapped shaders + constant UVs (v7a) / no UVs (v5) -> calc_tangents gives zero
  tangents -> black. kk15e now gives each part real cylindrical/planar UVs squeezed into a 4 mm atlas patch around the cage
  tube's (and bumper's) median UV -> valid tangents (checked: 0 bad of 20160 loops), same colour. Lesson: new meshes on
  normal-mapped materials need non-degenerate UVs. Installed. Not seen in game.

## 24 Nov 21:00 - 15" car: backfires + doorless
- exhaust_flames.lua: backfire pops with the flames - car's own bank events cars/:own/backfire_ext (vol 1.8, exterior) and
  backfire_int (vol 1.2, cockpit), pool of 4, at the stacks, ~70% of flame flicks, >= 70 ms apart, pitch 0.9-1.15.
- kk15f_doorless.py -> escort15_v8.blend: DOOR_L/DOOR_R active 0 (not deleted); KK_door_bars = X of 42 mm tube per side from
  the A-pillar cage leg (z 0.20 / 0.62) to the main-hoop leg (z 0.62 / 0.15), ends sunk 15 mm, cage material + atlas-patch UVs.
- BACKUP of the whole installed 15" car before this: D:/ClaudeData/tmp/kadett/BACKUP_15in_before_doorless_20261124_2054
  (kn5s, data.acd, extension, ui_car.json) - copy back to restore; blend before = escort15_v7. Not seen in game.
- 21:03 doorless sound (Nik chose option 2): exhaust_flames.lua plays the car's engine_ext event in the cockpit only
  (interior mult 1, exterior/track 0), volume 0.45, at the stacks, params rpms/throttle each frame. Backup of the script:
  D:/ClaudeData/tmp/kadett/exhaust_flames_15.BACKUP_before_open_cockpit.lua. Not heard in game.
- 21:08 Nik: doors gone in the showroom but back in game - the CSP door animations ([ANIMATION_2/3] car_door_L/R.ksanim on
  Extra C) bring the door nodes back. Both renamed [ANIMATION_n_OFF_DOORLESS]; exhaust_flames.lua also hides DOOR_L/DOOR_R
  every 30 frames. Backup ext_config_15.BACKUP_before_door_anim_off.ini. Not checked in game.
- 21:12 cockpit engine a touch quieter (backfires unchanged): open-exhaust layer 0.45 -> 0.35, [AUDIO_VOLUME] ENGINE_INT 0.9.
  "Window frame still there": object-coloured render of escort15_v8 shows only the body aperture seal + drip rail in the
  opening - likely the door animation (fixed 21:08); asked Nik for a screenshot if it persists.
- 21:25 doorless "frame from inside": the cockpit-only mesh dashstructure_a_SUB0 (COCKPIT_HR, + __lr) holds the door
  quarter-light frame (vertical post y~-0.16 + diagonal). kk15g_quarterlight.py -> escort15_v9: islands wholly inside
  |x| 0.5-0.70, y -0.52..-0.12, z 0.64..1.04 deleted (34 + 24 islands, both sides); A-pillar trim and aperture seal kept.
  Checked from the driver's eye. Installed (backup live15_backup_before_quarterlight_*). Not seen in game.

## 24 Nov 21:55 - 15" car: race engine + primaries from the real ports (escort15_v10 -> v12; v9 = backup)
- Nik: stacks' pipe routing odd (pipes started beside the engine, through inner wings/strut towers) + "engine needs to look
  better and more racey"; chose all four: ITBs/velocity stacks, red crinkle cam covers, race dress-up, black & alloy.
- kk15h_engine.py (v9 -> v10): road plenum + front throttle body/filter deleted; 8 ITBs (machined bodies, polished flared
  trumpets to z 0.595, dark plates) at x +-0.135 over the intake ports; cam covers KK_redcrinkle (red tint of v8_crinkle_d,
  same NM); V8_alloy split -> KK_V8_block satin black (islands z<0.30, |x|<0.25) + heads etc machined alloy; distributor at
  the front + 8 yellow HT leads; braided fuel lines (rails -> bulkhead, front crossover) with red/blue anodised fittings.
  kk15h2_engine_fix.py: old injectors poking into the trumpets deleted, leads re-routed along the cover tops, bigger
  "V8 4.0" on the cover outer faces. Textures generated (copies in textures_src/).
- kk15d_zoomies_v11.py (v10 -> v11): primaries from the real exhaust ports (x +-0.257, z 0.30; y +x -1.385/-1.28/-1.175/
  -1.07, -x +0.02) up between head and inner wing, exits x +-0.355, y -1.40/-1.30/-1.20/-1.13, tips up + 9 deg out;
  V8_exhaust (old headers/downpipes) hidden. kk15e (cage material + UVs) -> v12. Smoke/flames.ini/backfire point moved.
- Mishap: path edits failed once - escort15_v6 overwritten (superseded), v7 overwritten then restored from .blend1.
- Installed; backup D:/ClaudeData/tmp/kadett/live15_backup_before_race_engine_*. Not seen in game.
- 22:10 Nik: engine showed the BMW/RaceLogic atlas in game although every kn5 reference was right (checked node -> material
  -> texture in the file). The 6 generated textures were PNG; converted to uncompressed DDS (kk15i_tex_dds.py) like every
  other car texture. Stacks moved forward + equal 100 mm spacing: exits y -1.46/-1.36/-1.26/-1.16 (rear clear of the vent).
  Rear panel strip (rear-facing lower part of trunk_a_SUB0, body paint) -> UVs into a plain lid spot (0.8744, 0.4688)
  (kk15j_rearstrip.py) so it takes the lid colour on every skin. Chain v10 -> v11 (stacks) -> v12 (cage mat) -> v13 (DDS)
  -> v14 (strip). Smoke / flames.ini / backfire point moved. Installed (backup live15_backup_before_v14_*). Not seen in game.
- 22:30 Still the M4 decal atlas on the engine (and untouched parts, e.g. coolant tank) after DDS. Adding textures to this
  kn5 shifts the donor M4/RaceLogic textures (were 187-194) and the game mixes them up - format irrelevant. Nik: "use
  textures like the old engine". kk15k_existing_tex.py -> escort15_v15: no new textures (list identical to v9's 196, same
  order); red crinkle = v8_red_d + v8_crinkle_nm, block = v8_crinkle_black, heads = v8_cast_alu, trumpets/lettering =
  NICK3_alloy, leads = KK_fog_lens_col (yellow), braid = v8_alu_d. LESSON: don't add textures to this kn5 - reuse existing.
  Installed. Not seen in game.

## 25 Nov 08:00 - 15" car: horn = arm out of the window + middle finger
- driver_70 rig: RIG_Arm/ForeArm/HAND_L etc, NO finger bones (hand = gripping fist). kk15l_finger.py -> escort15_v16:
  KK_finger (glove-dark capsule, 18 x 80 mm, along AC +Z at the origin, kn5 active 0, bumperFrame_radiator - no new texture).
- extension/horn_gesture.lua ([SCRIPT_...] in ext_config): while car.hornActive, eases (dt*10) the left upper arm toward
  out-of-the-window (out 0.85, up 0.05, fwd 0.2) and the forearm up (up 0.92, out 0.25), rotating world matrices about the
  joints and writing locals (world x parentWorld^-1); KK_finger placed 70 mm up from the wrist along the forearm with
  mat4x4.look, shown when the pose is > 60 % up. Outward side = sign of (shoulder - car.position) . car.side.
- Texture list unchanged (196). Installed (backup live15_backup_before_finger_*). NOT seen in game - bone axes/order of
  AC's driver animation vs the car script are unverified.
- 19:35 Nik: arm comes out but jittery/flickery/intermittent, no finger seen (it was buried 70 mm up the hand), hand open.
  horn_gesture.lua v2: game-pose cache (each touched bone's local refreshed only when the game rewrites it - never
  building on our own output); world maths from RIG_Clave_L world (never written) down Arm -> ForeArm -> ForeArm_END -> HAND;
  the rig DOES have finger joints (HAND_Index/Middle/Ring/Pinkie1..6, thumbs HAND_L/R_Thumb): the left hand's middle joints
  get identity rotation (straight) when the arm is > 50 % up, others keep the curled grip; restored on release. KK_finger
  kept hidden (unused). Not seen in game.
- 19:55 Nik: wrong angle ("looks like he broke his arm"), fingers not clenched, still flickers; wants arm straight out to the
  car alongside (or forwards). Installed Gravy Garage cars have no gesture files; CSP has no gesture feature. Found
  ac.updateDriverModel() ("use it before moving driver nodes manually ... next model update overwriting your custom
  positioning will be skipped") - the flicker cause. horn_gesture.lua v3: call it every frame, aim from the fresh pose
  (upper arm out 0.95 / up 0.12 / fwd 0.1, forearm up), wrist (ForeArm_END + HAND) straightened (identity rotation),
  middle joints straight, index/ring/pinkie grip rotation squared (tight fist). Not seen in game.
- 20:20 Nik (watched in game): TWO arms at once, both flickering - one posed, one the old grip. The game has more than one
  driver copy (detailed + distance) with the same bone names; v1-v3 only posed the first match. horn_gesture.lua v4 poses
  every copy (arms:at(i), each with its own forearm/hand/finger joints found under it). Not seen in game yet.
- 20:40 Nik: still two blurry arms - "just make an animation file like the steering and shifting". Lua bone posing dropped.
  tools/make_horn_ksanim.py -> animations/horn_gesture.ksanim (v2, 19 bones, 21 frames): the left arm chain
  (Arm/ForeArm/ForeArm_END/HAND_L) + left-hand thumb and fingers 1-3. Frame 0 = our steer.ksanim centre frame (normal grip);
  last frame = the bdb_mazda_miata_na1 fuck.ksanim end pose (right arm, fingers 4-6) mirrored to the left: q (x,y,z,w) ->
  (x,-y,-z,w), checked on our steer anim L/R pairs; same driver rig (bone lengths match to 2 mm); our translations kept;
  slerp, ease in-out. ext_config: [ANIMATION_...] FILE=horn_gesture.ksanim INPUT=HORN TIME=0.6 (Miata's keys); the Lua
  section renamed [SCRIPT_OFF_HORN_LUA]. Backup ext_config.ini.BACKUP_before_horn_ksanim_*. Not seen in game.
- 20:47 Nik: "works well" - horn ksanim confirmed in game.

## 25 Nov 21:00 - 15" car: no backfire sound, flames per cylinder
- Nik: the backfire sound hid too much of the engine; flames should come from one cylinder at a time, not 4 at once.
- kk15m_flames_per_cyl.py -> escort15_v17: KK_flame_L1..3/R1..3 split per stack -> KK_flame_<L|R><stack 1-4>_<len 1-3>
  (24 meshes, 6 faces each, faces to the nearest stack by y; same KK_flame material/flags; textures still 196).
- exhaust_flames.lua: backfire AudioEvent pool + pop() removed (cockpit open-exhaust layer kept). Bursts (lift-off,
  upshift, green limiter) now step through the Rover V8 firing order 1-8-4-3-6-5-7-2 (odd = left bank front-back, even =
  right bank) every 20-70 ms; each cylinder pops with 45 % chance (60 % on the limiter) for 40-120 ms, random length.
  Checked with a stubbed Lua run: single stacks light in sequence. Installed (backup
  D:/ClaudeData/tmp/kadett/live15_backup_before_per_cyl_*). Not seen in game.

## 25 Nov 22:00 - original car gets the 15" torque curve
- Nik asked why the 15" shows 50 bhp less: label only - both power_dtm.lut curves peak at ~349 bhp (the original's ui says
  400 bhp / 409 Nm, x1.15 crank-style; the 15" ui shows the curve's own 349 / 358). Nik: leave the labels.
- Then: original ford_escort_mk2_tuned gets the same realistic curve - power_dtm.lut copied from the 15" acd
  (acd_patch.put_file; backup data.acd.BACKUP_20261125_2159; copy in export/power_dtm_realistic.lut). Original's ui_car.json
  untouched. Not driven yet.
- 22:10 Nik: backfire sound back at half the old volume - pool restored (ext 1.8 -> 0.9, int 1.2 -> 0.6), a pop with 70 %
  of the cylinder flames (min 70 ms apart). Backup D:/ClaudeData/tmp/kadett/exhaust_flames.lua.BACKUP_before_backfire_half_*.
