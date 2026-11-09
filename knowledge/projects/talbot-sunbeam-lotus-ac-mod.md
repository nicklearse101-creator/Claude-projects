---
name: talbot-sunbeam-lotus-ac-mod
description: "\"The Sunbeam\": Talbot Sunbeam Lotus 1981 works rally car for Assetto Corsa - rally conversion of the stock Sunbeam mod; physics v7 live; backup_v6 = Nik's MAIN model, got the 6 Oct model update (floor-anchored belts, splitters, Escort 4-cyl + Lotus badge)"
metadata:
  node_type: memory
  type: project
  originSessionId: 2da5ab3d-dfff-4d11-ac13-42a0c3cc473d
  modified: 2026-10-06T08:00:00.000Z
---

## LATEST (2026-10-06) - model update on backup_v6
* Nik: `talbot_sunbeam_lotus_81_works_backup_v6` (four-link axle) is "our main model". His data/data.acd/sfx there
  are his own edits (4-5 Oct) - model changes go in with `tools/install_models.py <car id>` (copies only the four
  sunbeam_rally*.kn5, archives the old ones, refuses while acs.exe runs). The live v7 car still has the 28 Sep model;
  offer it the same files if he wants.
* Done + installed 6 Oct (commit b707106, plan `docs/plans/2026-10-06-belts-splitters-engine.md`): shoulder straps over
  the harness bar down to floor anchors (BELT_anchors_*; tail UVs folded inside the blue webbing band STRAP_BAND or
  they hit the black part of MK2_seats.dds); splitters reworked (rounded-nose lips, long lofts into the flares, rear
  smoothed + rigid-snapped); `build_engine_swap.py` grafts the Escort Mk2 4-cylinder (refs/donor_escort4, exported
  from the Escort blend, gitignored) - it fits (closest 24 mm to the bonnet); `ENGINE = "stock"` swaps back; Lotus
  roundel badge 32 mm on the cam-cover pad where FORD was (Nik asked). The works car really had the Lotus 2.2 16v.
* Gotchas: (1) file renders (bpy.ops.render) show the STOWED stock parts - they're viewport-hidden but render-enabled;
  hide every mesh that is not visible_get() first - `tools/render_stills.py` does it (commit 465c5bb). (2) kn5_compare after adding
  materials: compare material BY NAME - index shifts made 460 untouched nodes look "changed".
* **6 Oct evening: Nik says v7 (the live `talbot_sunbeam_lotus_81_works`) is OBSOLETE - he will delete it himself.**
  backup_v6 is THE car. The build pipeline (build_rally_on_stock, graphics_fit.json, REAR_TYPE DWB) still targets v7 -
  repoint it at v6 (four-link axle physics) before the next full rebuild; never rebuild over v6 without asking.
* Measured v6 in game (Ascari pits, Vintage GT70 tyres; `ac_static_ride.py --any --out export/graphics_fit_backup_v6.json`,
  run from PowerShell - the Bash sandbox sees empty AC shared memory; shared-memory carModel reads "0", use
  Documents\Assetto Corsa\cfgace.ini MODEL=): GRAPHICS_OFFSET 0,-0.403,-0.174 + PITCH -1.80 (was -0.414/-1.85,
  body 11 mm too low). Ready-to-copy fix incl. that + colliders + tank in `staging/v6_collider_tank_fit/README.txt`;
  APPLIED 6 Oct 17:54 after Nik left auto mode (the auto-mode classifier had blocked writes to the car folder):
  data/car.ini offset/pitch/tank + colliders.ini written; old data + data.acd in
  archive/replaced_20261006_175427_backup_v6_data_before_ride_collider_tank_fit. data.acd NOT repacked - Nik does
  Pack data in CM; until then AC still loads the old data.acd. Not yet driven/checked in game.
* **(was OPEN, now applied - see above) (6 Oct, Nik's CM showroom screenshot with debug lines) - collider / fuel tank / rear wheels**, backup_v6:
  - colliders.ini = the STOCK mod's (3 thin slabs for the stock frame: offset 0,-0.365,-0.247, pitch 0) copied by the
    build; our frame is 0,-0.414,-0.174 + pitch -1.85 -> ~7 cm off, 0.2 m short of the nose, 0.5 m short of the tail.
    Tank POSITION 0,-0.15,-1.85 = the Escort Mk1's (0.47 m behind the rear axle, in the bumper). FIX READY, NOT APPLIED:
    `tools/collider_fit.py` (commit 652ca1e, build_rally_on_stock uses it) + staged files in
    `staging/v6_collider_tank_fit/` (4 boxes; tank 0,-0.006,-1.625 = boot floor, y 1.45 / z 0.46 Blender). The auto-mode
    classifier BLOCKED editing (even reading) the installed v6 car folder - Nik must say how to proceed (approve / copy
    the staged files himself). data/ == data.acd contents (checked); data.acd overrides data/, so he re-packs in CM.
  - Rear wheels "not touching the floor" = the showroom draws physics wheels at nominal BASEY: after offset+pitch the
    physics rear hub is 3.3 cm ABOVE the model's wheel, the front 1.4 cm below (the in-game fit of 28 Sep absorbed the
    static ride). NOT changed blind: the proper fix is a fresh in-game static fit (`tools/ac_static_ride.py`, car
    standing in the pits, AC running) for the v5/v6 springs, then GRAPHICS_OFFSET/PITCH. Needs Nik to start AC.
* Screenshots: ONE per finished section (see [[feedback-screenshots-one-per-section]]).

## RESUME HERE (state 2026-09-28 evening)
* **Blender/3D phase finished** (Nik: "we're done with Blender for now, great work"). Next = setup/physics.
* Read `D:\Claude\talbot_sunbeam_lotus\README.md` first (pipeline, tools, open items) and
  `refs\physics_research.md` (Escort-base vs real works car, prioritised: 1 rear axle 5-link+Panhard ->
  4-link with 45 deg upper links; 2 plate LSD ~45/30/40Nm; 3 final.rto -> Salisbury heavy-duty list 3.77-6.17
  (FIA p14), default 4.09; 4 steering 11.3:1 / lock 414; 5 cockpit-adjustable brake bias ~0.62; 6 revs to ~9000
  (works red line 9,250) keeping fat low torque; 7 weight optional - Nik kept 1010; 8 CG unknown).
  Nik has NOT yet said which to do - present, then implement in tools\build_car.py / build_rally_on_stock.py.
* Project is now a **git repo** (first commit 39d7bb3, 2026-09-28; .gitignore excludes archive/staging/export
  kn5/blend and other authors' assets). Commit after each change.
* Nik uses **Setup Coach** on this car (setups in Documents\Assetto Corsa\setups\talbot_sunbeam_lotus_81_works:
  Nordschleife, Bathurst, Adelaide) - setup files store final.rto INDEXES; range changes shift his setups.
  **Setup Coach v2.5.0 (2026-09-29)** was shaped by this car: springs + diff-coast balance levers (it has no
  bars/dampers), travel vs its own 140/120 mm PACKER_RANGE, Nordschleife counted in 4 sections, bias target
  from tyre grip (~70%, not the 77% load split), and a physics fingerprint that resets Setup Coach's learned
  values whenever this car's physics files change (adding dampers later is handled). Fixture copy of the data:
  `D:\Claude\setupcoach-tools\acd\extracted\talbot_sunbeam_lotus_81_works` (re-extract with acd_decoder.py after
  physics changes if the Setup Coach tests should follow). See [[setup-coach-project]].
* Installed copy's data was **packed to data.acd (CM) at 17:03** with front camber MIN -4.5 (was -2.5) - baked
  into build_rally_on_stock.py; a rebuild reproduces the installed data exactly. Installing a new build brings back
  a plain data/ folder (re-pack in CM if the server needs it).
* Open: harness "a bit loose" TODO; RALLY_TRACK_ADD 0.096 vs flares' ideal 0.081.
* **PHYSICS PHASE STARTED 2026-09-28 18:13** (Nik: keep current as backup, start with rear axle, he tests):
  - BACKUP = separate car `talbot_sunbeam_lotus_81_works_v1` ("... (v1 backup - Escort chassis)") made by
    tools\backup_car.py (decodes data.acd -> data/, renames sfx bank/GUIDs, copies his setups); git tag
    v1-escort-chassis. Old `_baseline` car ("(baseline)", Nik noticed it's Escort-based too) = v0.10: Escort
    chassis with 2nd gear 1.60, placeholder power (~210 Nm wheel), FFMULT 2.752, old final list, camber -2.5,
    OLD model (no LODs/cage/seats/scoop). Offered to delete it (redundant) - awaiting Nik's answer.
  - v2 (installed, ui version 0.6): build_car.AXLE_SECTION = 4 links: Escort lower arms + 2 upper links 45 deg in
    plan from the diff top (axle end +-0.11, y +0.12, z 0.03 -> car +-0.36, 0.12, 0.28), no Panhard; side view level
    like the Escort. Rear roll centre ~0.315 -> ~0.415 m. Only suspensions.ini changed. AWAITING NIK'S TEST.
    Tuning levers if too loose/twitchy: lower REAR_UPPER y (roll centre), or add anti-squat by raising car ends.
  - Nik tested v2: "feels good, do the rest" -> backup car `_v2` ("v2 backup - four-link only"), tag v2-four-link.
  - **v3 installed 2026-09-28 18:45** (commit aadf5ac), all in build_car.py constants: DIFF 0.45/0.30/40 Nm;
    final.rto order 6.17,5.38,4.89,4.55,4.27,4.09 (Salisbury, FIA p14),3.89 (std),3.77 (Salisbury),3.70,3.54 (std)
    (10 slots; idx 5 and 9 keep 4.1/3.54, idx 7 3.89->3.77 = Adelaide setup), FINAL
    4.09; STEER_RATIO 11.3 / LOCK 414 (wheel lock 28.1 -> 36.6 deg; LINEAR_STEER_ROD_RATIO untouched), FFMULT
    2.30*11.3/16 = 1.62 (assumes AC rim force scales with 1/ratio - ASK Nik how the weight feels); brakes
    FRONT_SHARE 0.62 + COCKPIT_ADJUSTABLE 1; LIMITER 9000 (RPM_THRESHOLD 9300), torque held to 8000 (peak 322 hp
    @7500 crank), AI/auto shift 8600/6000; INERTIA 1.60,1.40,3.83. Weight 1010 & CG 0.57 NOT changed (Nik's earlier
    call / no data). Saved setups keep their own diff/bias values - only preload + ranges change for them.
    AWAITING NIK'S TEST. Watch: wheels may poke through arches at full 36.6 deg lock.
  - 19:14: Nik's "feels good / diff not applied" test was actually in the `_v2` BACKUP (my naming made it look
    newest - see [[feedback-backup-naming]]). RENAMED: backups now `..._backup_v1` / `..._backup_v2`
    ("Talbot Sunbeam BACKUP v1 - Escort chassis" / "... v2 - four-link only"; setups folders renamed too; v2's CM-
    packed data.acd unpacked first - acd is keyed to the folder name). Live car = "Talbot Sunbeam Lotus Rally v3"
    (PHYSICS_VERSION in build_rally_on_stock). driver3d PRELOAD_RPM 6200 -> 7500 (SHIFT_PRELOAD_RPM; stock driver3d
    overrides build_car's). v3 still UNTESTED by Nik. Logs: no car errors (only stock-mod lights OFF_COLOR /
    WATER_TEMP LUT noise); 18:03 crash was in DWrite (UI text) while paused, not the car.
  - Nik: "the car is amazing i love it!!" (v3 physics). 2026-09-28 ~20:00 cosmetics installed (build_extras):
    gear gaiter (soufflet + stitch materials, both cockpits + LODs via OLD_CONTROLS (box, materials)) removed;
    Escort shifter base (gear_shift_base_SUB0-7) upright in the console opening (plate z 0.325); shifter +
    handbrake RESTYLEd to stock interior materials (volant leather knob top 62 mm + grip, painted_metal_smooth,
    metal_smooth chrome, rubber hoses); SLIDER rally sliding windows on both door glasses (frame + pane + tab,
    parented to DOOR_L/R, no_lod). Gotcha: a stock material replaced everywhere is purged from the .blend on save
    (needle_material now reuses RALLY_needle_red). Blender may be restarted empty - open the .blend first.
  - data.acd: NIK PACKS IT HIMSELF (CM) and says he'll unpack before asking for changes. Still, before each
    install decode the live car's data (acd_decoder) and diff against a fresh build - his hand edits (e.g. the
    camber range) must be carried into the build scripts, since an install replaces the whole folder.
* The history below is chronological (oldest first); the early from-scratch model parts are superseded.

"The Sunbeam" = a **Talbot Sunbeam Lotus** car mod for Assetto Corsa that Nik
wants to build **from scratch** in Blender (not from a downloaded Sketchfab
model - he stopped a Sketchfab search for it on 2026-09-27). Earlier planning
happened in claude.ai chats this machine has no record of; Nik expects it to be
known, so don't ask "which Sunbeam" again. Started in Claude Code 2026-09-27.

**Target: the 1981 works rally car** (Nik, 2026-09-27). Project folder
`D:\Claude\talbot_sunbeam_lotus\` - `blender\sunbeam_lotus_1981_works.blend`,
`refs\photos\` (6 photos, copied/renamed from Pictures\Saved Pictures: 3 road
cars, 3 rally replicas - none of an actual works car). Scene convention: metres,
car faces -Y, ground Z=0, origin midway between axles; REF collection has the
real-size box (3829x1603x1395, wheelbase 2413, Wikipedia) and the side photo
scaled to the wheelbase. Overhangs (0.654/0.762) and hub height 0.29 are
provisional; AC axis convention still to be confirmed with an early ksEditor
test export. Sketchfab "HighPoly Talbot Sunbeam Lotus 1981" (figoureuxa) is
NOT downloadable and has no licence - view-only reference.
Blueprints: getoutlines "1977 Talbot Sunbeam" (free) is the WRONG car (4-door
saloon) - renamed WRONG-CAR_* in refs\blueprints. the-blueprints.com free
Talbot Sunbeams are side-view-only road cars (no better than the side photo).
The right one is the-blueprints.com paid vector "Talbot Sunbeam Lotus (1979)"
#16124, $25: rally spec (arches, 4-lamp pod), front/top/rear/side, SVG/DXF,
1:25 - Nik chose NOT to buy; "just use" its free watermarked preview
(1280x905, refs\blueprints\the-blueprints_preview-wm_...jpg, cropped to
refs\blueprints\views\bp_{side,front,top,rear}.png). Placed in the .blend as
REF_blueprint_* image empties, all four aligned 2026-09-27. Scale 2.413/415.5 m/px
(wheelbase and 1395 height lines agree to 0.3%; the "1603" width line spans the
flared arches = ~1.71 m at that scale - check vs homologation). Blueprint gives
overhangs 0.693 F / 0.727 R, hub height 0.277, single mirror on the car's right. FIA historic DB (historicdb.fia.com) has Sunbeam Lotus homologation
entries - source for works-car track/wheels/weights later.

**Priority (Nik, 2026-09-27): "a working, detailed car"** - no specific
driver/event; pipeline-first, then detail. **v0.1 installed 2026-09-27** as
`content\cars\talbot_sunbeam_lotus_81_works` (blockout, untested in-game - Nik
to try in CM showroom/AC). Pipeline, all in `talbot_sunbeam_lotus\tools\`:
- `ac_kn5_export.py` - my own Blender->kn5 writer (no ksEditor): v6 + extra int
  781233, ksPerPixel + tiny DDS swatch per material, each object = dummy with
  local transform + mesh children; run in Blender via importlib, export_kn5(path,
  top_objects[, collider=True]). Top objects: BODY_blockout, BODY_arch_flares,
  SUSP_LF/RF/LR/RR (-> WHEEL_xx -> TYRE_xx mesh), COCKPIT_HR/LR, STEER_HR;
  collider = COLLIDER_hull (convex hull, "GL" material).
- `kn5_inspect.py` - reads any kn5 (materials, tree, winding, UVs) to verify.
- `build_car.py` - rebuilds data/ui/sfx/skin/shadows (never the kn5s). Physics
  = Kunos ks_ford_escort_mk1 (decrypted to refs\donor_data) + Sunbeam numbers;
  node-referencing inis (lights, mirrors, blurred_objects, analog_instruments,
  proview_nodes) emptied because the blockout has no such parts. Sound = Escort
  bank copied + GUIDs.txt lines from content\sfx\GUIDs.txt renamed to our id.
  GRAPHICS_OFFSET formula: y = -(tyre R + weighted |BASEY|), z = -(WB/2 -
  (1-CG_LOCATION)*WB) - reproduces the stock mod's own offset. AC power.lut is
  WHEEL torque (Escort lut ~200 bhp vs "260+bhp" UI).
**First in-game test 2026-09-27**: loads, drove ~1 min at Nordschleife, clean
exit; AC measured 198.5 whp and car bounds matching our dims/offset. Log showed
`RADIUS FRONT, P:0.300, G:0.000` (graphics tyre radius not found) - cause: I had
WHEEL_xx parented under SUSP_xx and named the tyre TYRE_xx. **Kunos layout:
WHEEL_xx and SUSP_xx are TOP-LEVEL siblings** (both at the hub; WHEEL holds
RIM_xx, DISK_xx, TIRE_xx (dummy+mesh of the same name), RIM_BLUR_xx; SUSP holds
calipers/hubs). Fixed + re-exported; Nik confirmed the showroom renders correctly (wheels in
the arches) 2026-09-27, track re-test pending (check log for G:0.300). Next =
v0.2 proper bodyshell; side-view feature lines (DLO, pillars, door, bumpers,
lights, arch/flare radii, belt 0.89 not 0.86) traced into
`tools\features_side.json`. Harmless log noise:
"GEAR COULD NOT FIND GEAR_1" (donor setup.ini has no per-gear items), flames.ini
missing, 0 brake disc meshes, car_wiper.ksanim default. AC rewrites an empty
proview_nodes.ini with the current node tree - reset it after renaming nodes.
**v0.2 exported 2026-09-27** (Nik: "it works really well" on v0.1): body now
from `tools\build_body.py` (loft; one side curve LOWER+GREEN resampled with
"keep vertices below the corner, stack the rest under it" - PILE - so rings never
jump; windows = bisect-cut edges + inset 12 mm, seals = inset walls), details from
`tools\build_details.py` (lamp pod per Nik's collage `refs\photos\rally_replica_
collage_front_rear_side_11.jpg`: 2 big upper + 2 small lower lamps; silver bumpers
with black ends; mirrors both sides; mudflaps behind all 4 wheels; new flares),
export via `tools\export_car.py` export(snapshot) (collider hull, proview reset,
preview.jpg). lights.ini now: HEADLIGHT, LAMP_POD_SUB1, BRAKE TAILLIGHT. Tyres use
ksTyres (CSP "No tyre meshes found" without it). Not yet: panel gaps, real
wheels, transparent glass + interior, livery/UVs.
**v0.3 exported 2026-09-27** after Nik said v0.2 "doesnt look much like the real
car": overlay on the wheelbase-scaled road photo (progress\04_overlay...png) showed
the SILHOUETTE matches; the gap was surface/detail. Added: materials via ac_preset
(paint/chrome/glass/trim/lens -> ksPerPixelMultiMap with Kunos Escort props + txMaps
swatch), black window surrounds/B-pillar/belt + black lower valances, shut-line
grooves (doors, bonnet, tailgate; bevel+push), `tools\build_wheels.py` (15" 8-spoke
rims, profiled tyres, discs under WHEEL_xx). Fixed A-pillar sawtooth: classify faces
against the SAME straight line the bisect cuts (a_pillar_z), not the curved corner.
Rebuild order: build_body.build(), build_details.build(), build_wheels.build(),
export_car.export(snapshot). Paint scheme still undecided (asked Nik).
**Verdict on v0.3 (Nik, 2026-09-27): "shockingly bad, nothing like the real car"
- "the car drives nicely, it just looks awful".** Lesson: a body generated purely
from code (lofted sections + boxes + flat swatch colours, no UVs/textures) can get
the silhouette right but reads as a toy; the bar is the stock mod's hand-modelled,
textured look (showed it in CM showroom: green, detailed interior, cage). Don't
present scripted geometry as close to the real car. Physics/pipeline are the parts
that work. **Nik chose (2026-09-27): rally version ON the existing stock mod's model.**
`tools\build_rally_on_stock.py` rebuilds `talbot_sunbeam_lotus_81_works` (same id;
UI "Talbot Sunbeam Lotus Rally" v0.4): their kn5+LODs, collider, textures, skins,
animations, CSP extension, sound (bank renamed + GUIDs.txt id-replaced), and their
model-tied data (lods, lights, mirrors, cameras, instruments, driver3d, dash_cam,
flames, colliders, sounds, car.ini [GRAPHICS]); OUR physics (build_car.build_data)
with track 1.329/1.342 + tyre 0.295 on 13" rim to fit their wheels/arches, and
GRAPHICS_OFFSET recomputed so their model keeps its place relative to the wheels
under our CG (0,-0.398,-0.175). Own v0.3 model archived to
`talbot_sunbeam_lotus\archive\v0.3_own_model\`. PERSONAL USE ONLY - needs
marcel du PMU / Mr.Hunt / ACTK permission before sharing or server use (credited
in ui_car.json). Their model is LHD (Nik had asked for RHD). Nik confirmed v0.4 sits right + clean log.
**kn5 round-trip (2026-09-27): `tools\kn5_import.py` + `ac_kn5_export.py` re-export
the stock kn5 BYTE-IDENTICAL** (checked by SHA). Keeps textures (bytes, order, in
`refs\stock_kn5_textures`, listed on scene kn5_textures), materials verbatim (JSON
kn5_def), dummies (kn5_matrix exact floats while unmoved), mesh flags + bounding
sphere, exact normals/tangents (corner attrs kn5_nrm/kn5_tan, used while
kn5_pristine), vertex order by first use; objects with custom prop no_export are
skipped. Needs numpy -> run inside Blender. Skinned meshes (class 3, e.g. Kunos
driver/shifter boots) NOT supported yet; encrypted kn5s won't read.
Blend for this: `blender\sunbeam_rally_on_stock_model.blend` (own-model blend untouched).
**Rally look target (Nik's photos 2026-09-27): yellow body + green side band,
body-colour FLARED arches (he corrected me - "there is definitely flared arches"),
8-spoke wheels, four spot lamps, black mud flaps.** Stock model facts: Blender
space wheel centres z 0.145 (ground ~-0.155), body side x ~0.79-0.81; paint =
carPaint (skin metal_detail.dds), stripe band meshes = carPaint_2 (metal_detail_2.dds).
v0.5 (2026-09-27): `tools\build_rally_parts.py` (flares traced from measured stock
arch openings, carPaint + nearest-body UVs; 13" 8-spoke rims EXT_rally_rim under
RIM_xx with stock rims no_export; tyres x1.12 wide; RALLY_lamps; RALLY_mudflaps),
`tools\export_rally.py` -> `export\sunbeam_rally.kn5`, then build_rally_on_stock.py
copies it in (single LOD - stock LODs lack rally parts), track +0.10 (1.429/1.442),
lights.ini + RALLY_lamps_SUB1, skin `rally_yellow_green` (flat DDS paint/stripe/gold
rim). **Nik on v0.5: "awful, the arches are way too big and the wheels are
rubbish ... try harder on the arches - they're almost there"; told me to use
existing AC wheels, e.g. the Escort Mk2's.**
v0.6 (2026-09-27): flares slimmer (lip 42 mm proud, 75 mm spread, taper to nothing
at the ends, stop at z 0.06 - no tails; one clean paint UV for all flare verts -
nearest-vertex UVs picked up an underside texel = zebra stripes). Wheels grafted
from `ford_escort_mk2_rally_spec` (Alan Mc Enroe; personal use) via
kn5_import(primary=False, prefix="MK2_") into collection DONOR_MK2: Revolution
rims + Kumho tyres, scaled to R 0.295 on the stock WHEEL centres; tread/wall
given ksTyres materials (MK2_TREAD_tyres/MK2_WALL_tyres) built from Mk2 textures.
Track +0.096 (1.425/1.438) computed so tyre edge sits 12 mm inside the lip;
RIM_RADIUS 0.2159. Gotchas: BodySampler must exclude our own carPaint parts
(old flares contaminated side_x); CM recreates skins/ right after deletion ->
copytree(dirs_exist_ok=True); scaled graft normals need inverse-transpose +
renormalise (fixed in exporter).
Nik on v0.6: "proportions are good" but arch edges "jagged and weird"; wanted
proper spot lamps. v0.7 (2026-09-27): flares = 11-point rounded SECTION, 120
stations, body side_x samples Gaussian-smoothed along the arch (raw stock-mesh
samples are noisy = the jaggedness); front arch's forward end stops at the bumper
bottom (z 0.20). Spot lamps = copies of the stock fog lamp (housing __slod, chrome
bezel SUB3, reflector SUB4, fluted lens glasslfl_a_SUB0, clear glass SUB1; right
side copied from the right lamp, matched by material) scaled to 190/150 mm on a
black bar; stock fog lamps no_export; lights.ini LIGHT_19-22 =
RALLY_SPOT_{LU,LD,RU,RD}_a_SUB0. Gotcha: .copy() carries custom props - copies of a
no_export object must have no_export deleted.
Nik on v0.7: mud flaps didn't line up with the body; wanted arches blending into
flared side skirts + race-style splitters front/rear. v0.8 (2026-09-27):
FLARE_ENDS per arch end (front fwd end at bumper z 0.20 tapered; sill-side ends
untapered into the skirt at SKIRT_Z 0.075; rear arch rear end at valance z 0.15
- the v0.7 rear flare hung below the body). RALLY_skirts (carPaint, rounded bottom
lip LIP_OUT proud, blends into door by z ~0.315, overlaps into both flares).
RALLY_splitter_front (air dam 0.150->0.035 + 8 mm blade 60 mm proud, 260 mm under)
and RALLY_splitter_rear (drop panel to 0.075, blade 40 mm, 4 strakes), black
plastic; outlines = fitted quartic y(x) from robust percentiles (raw extremes were
wavy from plate/brackets). Mud flaps at each arch's trailing edge, centred on the
AC tyre x (0.7125/0.719, not the model's), bottom 70 mm off ground. Stock body
facts (Blender): sill bottom z 0.10-0.12 tucked to x 0.71; front valance bottom
z 0.144 (y -1.92); rear 0.153 (y 1.86-1.90).
Nik on v0.8: "side skirt is rubbish, it only needed to be a small detail to blend
the bottom of the arch in"; splitters "cool but look detached and fake". v0.9
(2026-09-27): skirt removed; flares built along a path (flare_path): ends either
"taper" or "sweep" - the lip line fillets round (FILLET_R 0.095) and runs
SWEEP_LEN 0.14 along the sill, height AND width pinching to a point. Splitters
replaced by body-colour lips grown from the stock carPaint valance bottom edge
(valance_edge: robust quartic fit in x^2 - front edge is z ~0.053 at y -1.655,
tucked well behind the bumper; rear z ~0.157 at y 1.81, only to x 0.48), carrying
the panel's slope then curving out/down (front drop 50 reach 75 mm, rear 55/30),
fading into the corners, with a thin black blade (6 mm) along the bottom and 30 mm
strakes at the rear. Lesson: add-ons read as fake when they don't start ON a real
body surface - grow them from traced panel edges, in body colour.
Nik's AC shots of v0.9: flares rendered BLACK and like a detached fin; arch
"disconnected at the top"; rear mud flap top didn't reach the rear arch.
v0.10 (2026-09-27) fixes: (1) EXPORTER BUG - calc_tangents raises on n-gons
(our generated parts have n-gon end caps) and the except branch dropped the UVs
too -> every vertex UV (0,0) = black corner of body.dds. Now UVs are always kept,
tangents fall back to any perpendicular. Check exported UVs with a kn5 parse when
a part renders black. (2) BodySampler.side_x now ray-casts (BVH of stock
carPaint+carPaint_2) instead of max-of-nearest-vertices, which sat up to 20 mm
off the wing's big polygons -> the flare-top gap. (3) Rear mud flap moved 20 mm
inside the arch opening (35 mm behind the tyre) with its top at the arch edge
+15 mm (z 0.275) so it meets the arch under the flare lip; front flap unchanged
(steering clearance). Nik: flares "look ok in blender".
**LODs (2026-09-27)**: `tools\build_lods.py` build_all() - imports the stock mod's
CM-generated LODs (b 40k/c 18k/d 4k tris, NO textures - AC resolves LOD textures
by name from the main kn5) into scenes LOD_B/C/D, no_exports their stock rims/
tyres/fog lamps, adds decimated copies of our rally parts (materials remapped to
the LOD's same-named ones; wheels under the LOD's WHEEL_xx; LOD d has no wheel
nodes -> wheels fixed at AC track x), exports export\sunbeam_rally_lod_{b,c,d}.kn5
with share_textures=True (46.4k/19.6k/4.0k tris). GOTCHA: stock LOD files have a
rotated FBX root (Z-up children) - call view_layer.update() after import before
parenting by world matrix. build_rally_on_stock writes 4-LOD lods.ini (15/45/201).
**Rear ride height too high in-game (Nik)**: Escort physics puts rear hubs lower
vs body than our level model; Kunos Escort (level model, hubs y 0.269) compensates
with GRAPHICS_PITCH_ROTATION=-0.55 (NEGATIVE lowers the tail). Fix = graphics only
(physics unchanged, he likes the handling): `tools\ac_static_ride.py` reads shared
memory (cgHeight, rideHeight pickups -> pitch, wheelLoad/RATE squash) with the car
stationary in AC, writes export\graphics_fit.json; build_rally_on_stock applies it
(GRAPHICS_OFFSET y + PITCH). Not yet measured - needs the car sitting in the pits.
Front splitter touched front tyres (Nik): lip x_end 0.69->0.67, fade 0.50->0.48
(lip now +-0.66, blade +-0.60; AC front tyre inner edge x 0.587).
Everything re-exported to export\ but NOT installed yet (Nik mid-race) - install
= run build_rally_on_stock.py.
**Real-spec research (2026-09-27, Nik asked; research only, nothing changed)** in
`refs\real_car_specs.md`. KEY BUG: FIA p5 close-ratio 2nd gear is 1.80 (39/21x30/31),
NOT 1.60 as installed. Power 245 hp@7000 / 256 Nm@6000, 1000 kg (tech-racingcars
wikidot; Bonhams "up to 240"); final drives 3.54-4.75 (std 3.89, ours 4.10 is
homologated); works brakes 304/292 vented, 4-pot. Nik's concern: don't ruin the
handling he likes - approach = one group at a time vs saved baseline, tyres last.
Nik approved: 2nd gear 1.80, real power curve, final drive + brake balance in setup
(weight NOT approved - stays 1010). Done 2026-09-27: build_car.py now has
CRANK_TORQUE (245 hp@7000/256 Nm@6000) x DRIVELINE 0.85 -> power.lut, UI curves show
crank; FINAL_OPTIONS -> final.rto (FIA list, default 4.10); brake bias was ALREADY
in the Escort setup.ini (52-80%). **Ride height measured live** (ac_static_ride.py
works - AC shared memory readable from this sandbox): rear hub 7.8 cm lower vs
body than front -> GRAPHICS_OFFSET 0,-0.414,-0.174 + PITCH -1.85 (export\
graphics_fit.json, auto-applied by build_rally_on_stock). Sign reasoning: AC is
right-handed (X left, Y up, Z fwd), Rx(+) = nose down, Kunos Escort -0.55 on same
physics -> negative = tail down; not yet confirmed in game. Baseline car installed
as `talbot_sunbeam_lotus_81_works_baseline` ("(baseline)", old physics, ride fix
applied) for A/B. New build STAGED in `talbot_sunbeam_lotus\staging\` (built with
m.bc.CAR = m.CAR = stage) - install with tools\install_staged.py once acs.exe is
closed (moves old version to archive\replaced_<ts>).
Installed 21:43; Nik: "looks great, sits at the right height" (pitch sign
CONFIRMED: negative = tail down). Then (2026-09-27): front blade capped x_max 0.55
(now +-0.54, still touched at +-0.60); FFMULT 2.752 -> 2.30 ("steering very heavy");
**+75 bhp by Nik's choice** - REAL_CRANK_TORQUE kept, CRANK_TORQUE = real x 320/245
(320 bhp @ 7000, 334 Nm, 272 whp), UI 320bhp. Installed. Baseline car still old physics.
**Swinging line at top of windscreen** (Nik, cockpit view, moves under braking) =
stock mod bug: driver3d.ini HIDE_OBJECT "DRIVER:DRIVER:HELMET_1975_SUB0" (typo) so
that helmet part of driver_70 rendered at the camera and swung with head movement.
build_rally_on_stock.fix_driver3d() rewrites the hide list (also applied to baseline).
**Spot lamps on MAIN BEAM** (lights.ini LIGHT_n = headlights on, no high-beam notion):
removed from lights.ini; CSP ext_config appended (build_rally_on_stock.spot_lamp_csp):
[EMISSIVE_HIGHBEAM_...] per lens + [LIGHT_EXTRA_...] beam per lamp bound to the
lens (BOUND_TO + BOUND_EMISSIVE_MAX=30, BIND_TO_HEADLIGHTS=0), kn5-space positions.
Syntax copied from CSP's shipped configs; the BOUND_EMISSIVE behaviour is
UNVERIFIED in game - awaiting Nik's night test. Stock ext_config has
IS_LOW_BEAM_AVAILABLE=1 already.
Nik 2026-09-28: helmet line GONE (confirmed); spot lamps STILL dark; rear wheels
wobble. Causes found: (a) lamp glow was on the fluted lens _a_SUB0, but the stock
fog lamp's front cover _a_SUB1 (gls_clear_FFB25F99, ksPerPixel blend 0) is OPAQUE
and hides it -> now MESHES=_a_SUB1, _a_SUB0, COLOR=400,385,340,0.2 (as CSP's
ks_alfa_33_stradale config, which pairs EMISSIVE_HIGHBEAM + BOUND_TO/
BOUND_EMISSIVE_MAX exactly like ours), BOUND_TO=_a_SUB1, BOUND_EMISSIVE_MAX=60.
(b) Escort Mk2 donor rear tyre/outer rim/nuts modelled with 2.0 deg camber (spokes
not), all wheel parts 7-8 mm off-centre -> build_rally_parts.true_up_wheel():
per round part, SVD-fit axis, rotate onto WHEEL node X and centre on it (valve
follows tread), then scale so tread r = 0.295. Verified 0.00 deg / centred.
Installed; awaiting Nik's test. (Also noted: after the ray-cast BodySampler the
ideal track add is 0.081, installed stays 0.096 - Nik likes the look.)
Nik next: tread "looks disconnected" + lamps STILL dark. Causes: (a) my per-part
true-up moved tread vs sidewall 6.8 mm apart (donor shares their edge verts; vertex-
mean centres are biased by uneven vertex spacing) -> true_up_wheel now aligns RIGID
GROUPS (tyre = tread+wall; rim = outer+inner rim+nuts+valve; spokes) by SVD axis of
round members + extent-midpoint centre of the key part -> gap 0.01 mm, tilt <=0.24,
centres <=0.5 mm. (b) the stock fog lamp's "foglightl_a__slod" is a matt-grey
STONE-GUARD COVER over the lens (36 forward faces, 7 mm in front) - lamps could never
be seen lit. Dropped from build_spot_lamps + LOD lamp_keep. Lens is amber
(FFB25F99) -> glow/beam now selective yellow. Nik's CSP: USE_HIGHBEAM_BY_DEFAULT=1
(headlights on = high beam; Alt+L toggles), so EMISSIVE_HIGHBEAM does fire.
Installed 2026-09-28; awaiting check. Debug lesson: before blaming config, look at
what's physically in front of an emissive mesh.
Nik: tyres GOOD; spot lamps WORK but "now have covers over the lenses" - the stock
fog-lamp glass is amber rgbaffb25f99 drawn opaque (blend 0) + solid amber reflector.
v0.14: LAMP_DRESS/spot_material() in build_rally_parts - lamp-only material copies:
SUB1+SUB0 -> "RALLY_spot_glass" (copy of the car's windscreen "glass",
ksPerPixelReflection blend 1), SUB4 -> "RALLY_spot_reflector" (same shader, blend 0,
grey texture, high spec/fresnel). Glow MESHES now SUB4, SUB1, SUB0; warm white again.
LOD lamp_keep: b SUB3/4/1/0, c SUB3/4/1, d SUB3. CONFIRMED by Nik 2026-09-28:
"lights are working and clear/very reflective" - spot lamps DONE (reflector spec
1.6 / fresnel 0.7 in LAMP_DRESS if he ever wants them toned down).
Nik asked "slightly less reflective/mirror-like" -> toned down (reflector spec 0.8,
exp 120, fresnel 0.3/0.55; glass spec 1.3, fresnel max 0.45) + spot_material now
rewrites kn5_def every build (it used to reuse the existing material). Installed.
**Stripped rear + roll cage DONE 2026-09-28** (installed, awaiting Nik's in-game verdict):
tools\build_cage.py, called at the end of build_rally_parts.build(). Cage = FIA p24
amendment 7 photo 11 (Safety Devices, 38 mm tube, 22.7 kg): main hoop y 0.72 (behind
the stock belt reels, which reach y 0.68), front hoop up A-pillars + header across the screen
top, 2 roof bars, 2 rear stays onto the rear arch tops (y 1.10), 1 diagonal right stay foot ->
left main-hoop corner (the photo shows a REAR diagonal, not a roof one). Dark satin grey
material RALLY_cage (rgba383838ff). check() reports clearance per member (min 6.6 mm;
front legs pass through the dash ends on purpose). Weight NOT changed (1010) - said the
bench/trim removal roughly offsets the 22.7 kg; offer to add it if he wants.
GOTCHAS found: the stock model has NO floor under the rear bench and the boot's front
wall faces the boot only -> removing the bench alone = see-through to the road (AC is
single-sided). Fixed with RALLY_rear_bulkhead (cabin-facing panel at y 1.165 up to z
0.745 + floor strip). Do NOT strip floor_a_SUB8 (rear armrests) - it leaves a hole in the
side trim; floor_a_SUB6/7/8 + trunkbay_a_SUB1/6/7 are repainted painted_metal_smooth
(stock black inner metal) instead. Stripped: parcelshelf_a_SUB0/1/2, trunkbay_a_SUB8/10,
pillartrim_a_SUB2 (sun visors, where the header bar runs). LODs merge meshes BY
MATERIAL (bench velvet/leather shared with front seats) -> build_lods.strip_rear drops
faces by material + y; LOD cage rebuilt with 8/6 sides (none in LOD d), not decimated.
DRIVEREYES in car.ini is in MODEL space: Blender (0.30, 0.244, 0.965).
Nik: "cage looks good" -> made BLACK (rgba101010ff, satin: spec 0.35/exp 30), and Escort Mk2
donor high-back BUCKETS fitted (build_cage.fit_buckets): stock seatl_a_SUB0/2/3/4/5 stripped
(SUB1 = belt buckle stalks kept); buckets placed by fitting occupant surfaces to the stock seat
(driver pose is made for it): shift (dx to centre 0.336, -0.16, -0.07), no recline -> zero
clipping, ~2-3 cm gaps. Bucket has no flat base - lowest line is two side flanges at seat
centre +-0.195 -> black flat-topped riser rails RALLY_seat_mounts there (no_decimate in LODs).
LOD DROP is now material -> predicate on face centre (seat frame = paint_010101FF inside
-0.35<y<0.45, z<0.66). Nik: seats "spot on".
HARNESSES added 2026-09-28 (build_cage.fit_harness) + seats RE-PLACED from the DRIVER
SKELETON: parse animations/driver_base_pos.knh (tree: name, 16f row-major matrix, child
count) + steer.ksanim v2 (per node: name, frames, 10f = quat xyzw, t, s) at frame 50 ->
bone world pos (AC->Blender (x,-z,y)). Both cars use driver_70 with the same posture; ours
is (dy -0.1466, dz -0.149) vs the Escort's (x mirrored, dx -0.0036). The STOCK Sunbeam
driver sat ~12 cm DOWN INTO the stock seat, so the first bucket fit (to stock seat
surfaces) was 8 cm too high. Now seats + belts use the bone shift (+1 cm lift so flanges
clear the carpet) -> buckets sit on the floor, riser rails removed. DRIVEREYES is NOT a
reliable body reference (Escort's eye is 13 cm ahead of its head bone). Driver belts =
donor CINTURE_ON/cinture_off SUB0/1 mirrored (mesh baked + reverse_faces + custom_normal
removed) under dummies CINTURE_ON / CINTURE_OFF (Kunos names, uppercase); passenger gets
the donor's loose belt unmirrored (always shown). Shoulder straps wrap round a new
HARNESS BAR in the cage (y 0.72, z 0.763) via bisect + bend. Stock 3-point belts
(seatbeltl_a_*, seatl_a_SUB1) and tailgate strings (ficelles) stripped. Belts not in LODs.
Nik in game: worn belts clipped through the driver's shoulders (Escort driver sits more
upright - ours is reclined further; worn set was up to 5.4 cm inside chest/belly).
FIX: tools\driver_pose.py = the REAL driver body: reads content\driver\driver_70.kn5
incl. SKINNED meshes (kn5 class 3: 3 flag bytes, bones [name + 16f inverse bind], 76-byte
verts = 11f + 4 weights + 4 bone-index floats, ushort idx, then mat/layer/lodIn/lodOut =
16 bytes, NO bsphere) posed with knh+ksanim (bone names carry "DRIVER:" prefix - strip).
build_cage.clear_of_driver pushes the CINTURE_ON webbing out to 6 mm off the suit
(subdivide near body, push + Laplacian-smooth displacement, fade to 0 at 15 cm so anchors/
bar wraps stay) and moves buckle hardware islands rigidly. Verified in Blender with the
posed driver (REF_driver object in a REFERENCE collection, not exported). Installed
2026-09-28 ~10:00. Computer-use access to acs.exe was granted for in-game looks (F6 cycles
car cams; F1 cockpit). Still offered: front carpet out.
Nik 2026-09-28: belts now "over the shoulders as they should be" BUT **TODO (come back
later, his words): "a bit loose on driver body"** - they stand off the suit too much. Levers:
BELT_CLEAR (6 mm) is only a minimum; straps that were never inside the Escort-shaped harness
still float where our reclined driver's chest/belly is further back. Fix idea: also PULL
webbing vertices within ~4 cm of the suit IN to BELT_CLEAR (shrink-wrap both ways), same
smoothing/fade.
2026-09-28 ~10:30 installed tools\build_extras.py (called after build_cage):
- BONNET SCOOP from Nik's photos of RTA 43X (black box scoop, rear of bonnet, opening
  forward; photo scoop ~30 cm wide -> +15 cm = 46 cm as asked), 30 cm long, 11/7 cm tall,
  on the bonnet (rear edge concave: y -0.874 centre), parented to MOTORHOOD, zeroBlack inside.
- FRONT PLATE (Plate_LODA002) lifted 5 cm + 6 mm forward onto the bumper face (top just
  under the lamp bar); LODs moved by material EXT_PLATE_plastic (build_lods.move_front_plate).
- SEQUENTIAL SHIFTER = Escort donor gear_shift_* parts, knob placed in our driver's right
  fist at shift.ksanim frame 75 (fist = mean of finger middle joints + thumb tip + wrist;
  glove CENTROID is biased to the wrist cuff - don't use it). Our shift anim keeps the hand
  ~0.68 m up at the centreline and pushes 6 cm forward (frames 50->99); the stock knob was
  25 cm lower/forward. Stock lever (Levier, centerconsolebezels_a_SUB10/11/15) stripped; stock
  road HANDBRAKE (islands of centerconsolebezels_a_SUB2/7/8 in HR and LR cockpits) moved
  18 cm back via mod_ copies; black riser (3.7 cm) under the shifter base. no_lod.
- driver_pose.py gained shift_frame / only / knh_car (Escort has no knh - borrow ours).
Offered: Escort hydraulic handbrake (centerconsolebezels_a020_*), animated lever (lever is
static; hand slides ~3 cm either way over the knob).
2026-09-28 13:24 installed ("aesthetics largely complete after this; next = setup/physics"):
- BIG GOTCHA: shift.ksanim ALSO carries DRIVER root + RIG_Center/Hips 31 cm further back &
  9 cm higher than steer.ksanim; AC only applies its MOVING nodes (arm/hand). driver_pose now
  filters shift to moving nodes. Real fist mid-stroke (0.034,-0.336,0.586) = just above the OLD
  knob -> shifter now rises out of the stock gaiter (tilt 9.6 deg toward driver), only
  gear_shift_sub001_SUB0/1 grafted (base/cable in tunnel). Stock road handbrake back in place.
- Escort HYDRAULIC HANDBRAKE (a020_SUB11/4/7/5/0/16 + piping_1) mirrored across its lever
  (graft(mirrored=True)), lever axis (-0.075,-0.345) on the tunnel side right of the stick.
- SCOOP v2 = Nik's hand-scaled size (he scaled the object: 30 cm wide, y -1.29..-0.965,
  h 6.6 -> 2.2 cm): carPaint single UV from hood, flared foot + rear ramp, black duct, grille
  bars, HOLE cut through all MOTORHOOD meshes (bisect + delete via mod_ copies) -> engine shows.
- BONNET PINS (chrome plate/pin/R-clip) at (+-0.55, -1.70), parented to MOTORHOOD.
- LIPS: tools\build_lips.py - front/rear lips follow a traced lower-edge PATH (valance fit +
  raw corner / quarter-panel edge) and carry on ~6 cm up the arch edge UNDER the flare's
  tapered end (ending the flare at a set size = step; running flare lower = folded mess).
  Outward dir = smoothed levelled body normal. Front lip drop 50->30 mm (raised). Front blade to
  x 0.70 with rear edge pulled in near tyres. Rear lip both halves built (no mirror) with an
  exhaust notch (x 0.37-0.57) on the left.
- SILL LIP: flare_and_sill() = one path LF + sill + LR; sweeps settle at SILL_E 0.45.
- EXHAUST tips x1.5 across + 2 cm out, collector x1.3 (mod_ copies; LODs by material).
- restore_modified() undoes all mod_ copies at the start of build_extras.build().
2026-09-28 13:40 installed (Nik: join messy / old stick+handbrake still there / needles):
- ALL body-colour trim is now ONE mesh RALLY_flares (build_lips.build): front lip -> Hermite
  LOFT -> flare (flare_rings(), cut at JOIN_TRIM z 0.25 front / 0.17 rear) -> sill -> flare ->
  loft -> rear lip; every section 12 pts [attached .. free edge, return]. Both halves built
  explicitly (rear notch for exhaust on left) and joined with remove_doubles. Made with
  build_cage.make_obj, NOT replace(): recalc_face_normals flipped the open strip (rear flare
  and sill came out inside-out). Front lip ends x 0.64, rear lip y_end 1.71 (1.66 twisted).
- old gear stick + road handbrake DELETED from both COCKPIT_HR and COCKPIT_LR (the outside-view
  cockpit has its own merged copies) by loose-part boxes OLD_CONTROLS; LODs by face centre.
- ARROW_SPEED/RPM -> RALLY_needle_red (rgbaff0b0099, emissive 0.9/0.05/0.03).
2026-09-28 13:58 installed (Nik: front corner gap, rear lip floating + exhaust area, rear join messy,
red on all needles):
- build_lips.snap(): every lip/loft/flare section's attached point pinned 0.5 mm INSIDE the paint
  surface (was 3-9 mm off: valance_edge fit != real panel), next 4 points follow (SNAP_W).
- Rear arch END now "sweep" (z 0.23, R 0.110, L 0.030): a cut end's section lay fore-aft vs the lip's
  up-down -> 90 deg twist; RADIUS MUST EXCEED FLARE WIDTH (75 mm) or the section folds (R 0.07 crumpled).
  Plus smooth_window() over sweep->loft->lip (REAR_JOIN_BACK 30 / ON 25 sections) removes the hump.
- Exhaust: left valance has a notch x 0.39-0.54 up to z 0.21 (right side solid). Lip now CONTINUOUS,
  lowered to z 0.157 across the notch (EXHAUST_ZONE, left half built separately, right plain).
  Tips: stock size through the notch, flare to 1.5x only behind the valance (y-dependent scale +
  stretch, bisected first - long faces would taper) - uniform 1.5x clipped the notch walls.
- all 6 ARROW_* needles red.
2026-09-28 14:12 installed: stripe FLICKER at distance (Nik: "fade in and out as if blurring", game AND
Blender) = Z-FIGHTING, not LOD: stock carPaint_2 stripe sheets (fenderslivery_a_SUB0, BANDES_LAT_ARRIERE,
EXT_BANDES_PORTIERES[_L]) floated only 0.01-0.57 mm off carPaint. build_extras.lift_stripes lifts them to
>= 1.5 mm (mod_ copies, 4 passes for creases); build_lods.lift_stripes: b 3 / c 8 / d 15 mm (stock LOD
stripes were 0-26 mm, some inside the paint). build_rally_parts.build() now calls restore_modified() FIRST
so the BodySampler never samples last build's edited copies (rebuilds were drifting, track_add 0.081->0.083).
Nik: "blender work is largely done" -> next = setup/physics (and the loose-harness TODO).
- BLENDER CRASHED on a solid-view screenshot after hiding ~150 objects (lost unsaved rebuild;
  scripts make it harmless) -> always export/save BEFORE screenshots after a rebuild.
BLENDER CRASH GOTCHA: setting a material's surface_render_method='BLENDED' + alpha
while the viewport was in Material Preview, then taking a screenshot, crashed
Blender (unsaved build lost; file reopened from last save). Keep viewport SOLID for
screenshots after material edits; export (which saves) before screenshots.
CM access: Nik GRANTED computer-use for content manager.exe on 2026-09-27 (viewing).
Placeholders to tune: TOTALMASS 1010, CG_LOCATION 0.57, tyre R 0.300 (15"),
power curve ~200 whp, FINAL 4.10, Escort springs/dampers/tyres.
Content Manager: first request denied, later granted (see below) - still ask before
doing anything beyond looking.

**Right-hand drive** (Nik, 2026-09-27) - cockpit goes on the car's right (-X in
Blender). **FIA homologation** downloaded (Nik's OK): Group 2 no. 1700, valid
2 Jan 1980 - 1 Jan 1982 = the 1981 works car. `refs\homologation\*.pdf` (25 MB,
44 pages; no PDF renderer on the PC - page JPEGs extracted to `pages\imgNN.jpg`,
page numbers = file order). Facts: WB 2413; overhangs 689 F / 727 R (p7);
length 3829 / 3750 without bumpers; body width at axles 1628 (p1); strut front,
live axle rear, coil springs, rack & pinion no PAS; 2174cc 95.3x76.2 DOHC 16v
belt; alt gear ratios 2.30/1.60/1.36/1.14/1.00 R 2.82 + FT3 90 L tank (p17);
from Jul 1980 steel bonnet + toughened rear glass (p28); **15" wheels** (p30,
Jan 1981); 1981 facelift grille/bumper valid from 1 Oct 1981 (p43). Track and
flares are NOT on the Group 2 form (free under Group 2) - the blueprint's 1.466 m
track stays the estimate; tyre size still open (blueprint R 0.277 looks small
for 15" rally tyres - measure off a works-car side photo scaled by wheelbase).

**Blockout v1 done 2026-09-27** (BODY collection): BODY_blockout = 80 lofted
cross-sections (Mirror + EXACT Boolean arch pockets from hidden CUT_wheel_arches),
BODY_arch_flares (wedge bands, lip X 0.865 F / 0.877 R), WHEELS_placeholder
(R 0.277, track 1.466 read off the blueprint front view - unverified; stock is
1.329/1.342). Profiles traced by `talbot_sunbeam_lotus\tools\trace_blueprint.py`
-> profiles.json. Known blockout flaws: stepped C-pillar/hatch sides, flat
bonnet, blunt front. Snapshot in `progress\01_blockout_3q.png`. Blender MCP
gotcha: after setting region_3d view_rotation/location call `r3d.update()` or
get_viewport_screenshot returns the stale view.

**Stock reference mod** (installed by Nik 2026-09-27):
`content\cars\talbot_sunbeam_lotus_lhd_stock` by "marcel du PMU / Mr.Hunt", v1.1
by ACTK - someone else's mod: use its FACTS only, never its mesh/textures.
data.acd decrypted to `refs\stock_mod_data\` (acd_decoder.extract_car with an
out_root). Stock facts: WB 2.413, track F 1.329 / R 1.342, tyre R 0.295 on 13"
rim, TOTALMASS 1055, front STRUT / rear live AXLE, GRAPHICS_OFFSET 0,-0.365,-0.247.
Its kn5 node tree (read with scratchpad-style kn5_nodes.py - walks nodes, skips
buffers) proves **AC axes: Y up, front = +Z, car's left = +X**; standard node
names WHEEL_/SUSP_/TYRE_/RIM_/DISC_{LF,RF,LR,RR}, STEER_HR/LR, COCKPIT_HR/LR,
DOOR_L/R, MOTORHOOD, REAR_HOOD, FRONT_/REAR_BUMPER, WIPER*. Our Blender layout
(car faces -Y, Z up) maps to that exactly with Blender's default FBX axes
(forward -Z, up Y): Blender +X = car's left = AC +X.

Tools on the PC: Blender 5.2.1 LTS driven via the blender-mcp plugin (Sketchfab +
Poly Haven enabled, Poly Pizza key missing - their /settings/api page 404s);
AC SDK at `D:\SteamLibrary\steamapps\common\assettocorsa\sdk\` (editor\ksEditor.exe
for FBX -> .kn5, audio\ for FMOD). Reference cars installed: ks_ford_escort_mk1,
ford_escort_mk2_rally_spec (+ variants), ks_audi_sport_quattro_rally.
[[setup-coach-project]]'s acd decoder reads reference cars' data.acd for physics.
Related: [[rattys-racing-dacia-championship]], [[ac-physics-watchdog-project]]
(car_data.py derives its top-speed ceiling from the car's own files automatically).

## From the watchdog work, 2026-09-29 (Nik: share findings across projects)
- Nik on v4: "a lot of fun sliding it around. It really feels like I imagine an 80's rally car would feel" -
  protect that feel in any physics change.
- AC delivers only ~85% of the files' drive FORCE at CONFIRMED full throttle in 3rd-5th (ground truth from
  AC's shared memory, 42 min at the Nurburgring, fuel + AC's air density counted; pedals, limiter, wheelspin,
  gearing, drag, engine damage all ruled out) - the Dacia ~94%. Leading suspect: altitude (Nurburgring air
  1.10 vs ~1.18 at sea level; engine.ini ALTITUDE_SENSITIVITY 0.1) - test = the Sunbeam at Mondello with
  RecordGroundTruth.bat. If it stays ~85% at sea level, something in our build costs ~15% of the intended
  272 whp (Nik loves the current feel - report, don't "fix" without asking). Chased in
  [[ac-physics-watchdog-project]] RESUME HERE.
- Quickest upshifts for Nik's stock gearing (overall 10.96/8.43/5.87/4.77/4.14; power.lut peak 274 whp @
  7500, limiter 9000): 1-2 8400, 2-3 8700, 3-4 8225, 4-5 7975 rpm - a shift light ~8300 rpm would suit (the
  ideas list says ~8600). Shifting on the limiter costs a little in every gear.
- The +10% cheat car's peak 313 Nm is above the clutch's MAX_TORQUE 300 (the v4's 284 is under it).

## Parked: +10% power test car for the watchdog
Nik asked for a "+10%" Sunbeam (known-cheat test for the ac-physics-watchdog), then parked it (29 Sep):
plan in [[sunbeam-plus10-watchdog-test]] - a separate TEST car id made like backup_car.py, never touching the
live car.

## 2026-09-29 - v4 adjustable dampers
Live car = "Talbot Sunbeam Lotus Rally v4" (DAMPERS tab: bump/fast bump/rebound/fast rebound x4 corners, `build_car.DAMPER_RANGES`).
`talbot_sunbeam_lotus_81_works_backup_v3` = the car before that. Build safely with `tools/stage_build.py` then
`install_staged.py` (build_rally_on_stock loads its OWN copy of build_car, so patch `b.bc.CAR`, not just `bc.CAR` -
an earlier attempt wrote a stray data/ folder into the live car; removed, Nik OK'd). Nik's 20:10 repack had no hand edits.
Nik has his own cloud backup of the car. Ideas list: see [[sunbeam-ideas-reminder]].
Damper facts (checked 2026-09-29): v4 uses AC's standard bilinear dampers - no .lut needed (Kunos AE86 tuned/drift:
live axle + DAMP_* setup items, no luts). CSP LUT dampers are a separate optional system (DAMPER_LUTS=1, dampers.ini,
DAMPER_BUMP_xx click items). AC loads data.acd over a data/ folder - Nik knows; he packs deliberately because running from data/ can cause in-game errors. Installing v-next as a plain data/ folder is fine (his words: "writing to data folder is fine"); he packs it himself afterwards - don't lecture him on acd precedence.
Setup Coach v2.5.0 fingerprints physics: v4 resets its Sunbeam learning; it reads setup.ini live so should use the dampers.
2026-09-29 ~20:30: `tools/make_cheat_car.py 10` built the watchdog's +10% CHEAT Sunbeam (`..._cheat_plus10`) - see [[sunbeam-plus10-watchdog-test]]. Rebuild it if the live physics change.

## 2026-09-29 ~23:20 - v5 springs (Nik: "yes")
Nik: Setup Coach says >100% travel and always maxes the rear spring - misreporting? NO: v1-v4 kept the Kunos Escort
Mk1's springs 38/34 N/mm + travel (Escort 885 kg, 55% F; Sunbeam 1010 kg, 57% F) -> ~half the travel used at rest,
median Nurburgring GP lap 110-112% F / 103-106% R of PACKER_RANGE (140/120 mm) = on the packers every lap. Mass-scaled
45/37, Setup Coach's own target 45-46/38-39; Nik drove 46/40 (+ SC's stiffer damper clicks) and loved it.
v5 (commit 764db73): defaults 46000/40000, setup spring ranges F 30-60 / R 20-50 step 2 (springs are stored as N/mm
VALUES in saved setups, so no saved setup changed); push rods 0.040->0.029 / 0.080->0.070 to keep v4's stance
(ROD_LENGTH setup units 0.1 mm, stored as CLICKS - MIN/STEP untouched; F step 1 mm, R step 10 mm). Dampers untouched.
BACKUP v4 = `..._backup_v4` "Talbot Sunbeam BACKUP v4 - before stiffer default springs", tag v4-dampers.
Cheat car rebuilt from v5 (v4-based one + reference + setups in archive/replaced_20260929_231842_..._v4).
Old SC setups with the rear raised +20..40 mm (Adelaide/Bathurst/Nordschleife) = the tail-high look; can go back to default.
Live v5 is a plain data/ folder - Nik packs it himself.

## 2026-09-30 ~00:55 - v6 bars/preload + v7 double-wishbone rear (Nik asked for both)
v6 (tag v6-bars-preload): ARB_FRONT 5000-40000 step 2500 (default 12500 = the Escort's, unchanged) + ARB_REAR 0-12000
step 1500 (default 0 = off, as always; a works 1/2 inch rose-jointed rear bar ~6000 = click 4 - ex-works listings);
DIFF_PRELOAD 10-200 step 10 (default 40); springs F 20-90 / R 16-80; damper MAX +45 % (MIN/STEP kept -> saved clicks keep
meaning). Defaults unchanged, so v6 drives as v5. Live axle: NO rear camber/toe (one-piece housing; Kunos' AE86 has none).
v7 (tag v7-double-wishbone, LIVE): [REAR] TYPE=DWB (build_car.REAR_TYPE/REAR_DWB/apply_rear_dwb), [AXLE] removed, rear
HUB_MASS 110->40, STATIC_CAMBER -1.0, TOE_OUT -0.0004, CAMBER_LR/RR (-3..0) + TOE_OUT_LR/RR (-100..40 step 5) setup items.
NOT historical - the works car = four-link live axle (in since v2); Nik: "or double wishbone (yes!)".
Geometry by kinematic sweep (scratchpad dwb_kinematics.py/dwb_opt.py, pure python - no numpy on Nik's PC): camber
-0.82 deg @ +40 mm, bump steer within 0.035 deg over +-60 mm (LEADING toe link above hub; a trailing one toed out 0.25
deg/20 mm = roll oversteer), roll centre 90 mm. Rear stance by calculation only (rod 0.070 kept) - check the look.
Model: per-corner WHEEL/DISC/SUSP nodes, no axle node -> independent rear wheels display fine.
BACKUPs: v5 "before adjustable bars and preload", v6 "four-link axle, adjustable bars" (= the real-axle car to go back to).
AC FACTS: WB*/STRUT points are x INBOARD FROM THE WHEEL CENTRE, y up from it, z forward (Kunos Lotus Exos only works
that way; our strut then has a real ~13 deg KPI). Axle cars' leftover WB points (x~1.2-1.5) are unused placeholders.
Setup units: camber saved as 0.1 deg (VALUE=-41 = -4.1), toe in 1e-5 (TOE_OUT -0.00045 = -45); ARB/toe/dampers/heights
SHOW_CLICKS=2 = saved as clicks from MIN; springs/preload/camber SHOW_CLICKS=0 = saved as values.
Cheat car stays v5-based (its watchdog reference is v5 too - consistent); rebuild only if a test needs v7.

- 2026-11-07: tried a horn via sfx\GUIDs.txt (E30 horn GUID); AC then refused the car with "damaged, packed data can't be read" (data.acd error), Nik asked to revert - GUIDs.txt restored byte-identical, no horn. data.acd last changed 2026-11-05, so the error is probably not from the horn lines; unverified.

- 2026-11-07: Nik renamed the BACKUP v6 folder to talbot_sunbeam_lotus_81_Rally -> AC 'packed data can't be read' (data.acd is keyed to the folder name; decoder test: opens as ..._works_backup_v6). Renamed back at Nik's choice. Renaming a car needs data.acd re-packed for the new name (no packer tool yet; CM can unpack/pack). Horn attempt reverted, no horn.
- 2026-11-07 (later): horn re-added after folder rename-back: one line in sfx\GUIDs.txt mapping E30 horn {985af071-...} to event:/cars/talbot_sunbeam_lotus_81_works_backup_v6/horn; backup sfx\GUIDs_BACKUP_before_horn_2026-11-07.txt.
