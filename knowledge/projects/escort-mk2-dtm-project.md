---
name: escort-mk2-dtm-project
description: "Nik's Escort Mk2 '90s DTM' conversion (car ford_escort_mk2_tuned) - v20-v25 Merc-190-based chassis, then v26 (13 Oct) physics rebuilt on the Kunos Escort Mk1 (Sunbeam recipe); what the live car really was; where the decoded data lives"
metadata:
  type: project
---

Car: `content/cars/ford_escort_mk2_tuned` = "Ford Escort Mk2 DTM v19" (mod by 101Creative & graveltrap - personal use
only, like the Sunbeam). Goal: handle like a 90s DTM car; Nik (2026-10-05): "awful and undriveable". The conversion
was done outside any CCD session (no transcript/notes found). Live loads data.acd (no data/ folder). Backups in the car
folder: data.acd.original_backup (the original mod: 980 kg, ~220 whp, 4-speed), data_backup_cm.acd (an earlier try with
"DTM Slick" tyres, 90/75 springs, wing angles 2/4), data.acd.pre_rally_backup (= v19 with the 5-link axle), plus car
`ford_escort_mk2_tuned_backup_pre_rally`. All decoded to `D:\Claude\escort_mk2_dtm\decoded\`; Kunos refs (Merc 190
Evo II DTM, Alfa 155 V6 Ti, M3 E30 DTM) decoded to `D:\Claude\escort_mk2_dtm\ref\`.

Diagnosis (v19 vs Kunos DTM refs): springs 35/26 kN/m (refs 80-200 / 60-105; softer than the original 44/40 despite
+70 kg); dampers bump 840/880 (refs 5300-10600 - ~10x under-damped); push rods 0.14/0.126 m (refs ~0) -> sits 140-180 F
/ 175-225 R mm (Setup Coach); packers 140/120 mm (refs 45-100); tyres default "Semislicks" DY 1.28 235 mm r0.268 (refs
"Slicks Soft DTM90" DY 1.48); ~406 whp (refs 306-333); diff coast 0.02 + preload 102 (refs 0.20-0.40 / 0-50); brakes
1800 Nm (refs 2500); steering 720/13 = 55 deg wheel angle (refs 14-32); aero = road car, net REAR LIFT ~-290 N @200 km/h
(refs +680..+800 N downforce); rear = Sunbeam four-link live axle (refs: independent). Setup Coach (Nordschleife 23 Sep):
35-90 oversteer snaps per 100 corners (slight <= 25), every session "loose".
Fix plan offered 2026-10-05: scripted rebuild like the Sunbeam (git, BACKUP v19 car first, stage/install), DTM90 slick
model resized to the Escort wheels, DTM-level springs/dampers/bars/ride height, splitter+wing downforce, diff/brakes/
steering lock to ref levels, rear = reuse the Sunbeam v7 DWB generator (validated by kinematic sweep) or a tuned live
axle - Nik to choose. Data.acd must be moved aside (AC prefers it over data/), Nik packs.
Related: [[talbot-sunbeam-lotus-ac-mod]], [[setup-coach-project]], [[feedback-backup-naming]].

## 2026-10-05 ~07:20 - v20 BUILT + INSTALLED (Nik: "double wishbone, build")
Repo `D:\Claude\escort_mk2_dtm` (git, tag v20-dtm-rebuild; decoded/ ref/ staging/ archive/ gitignored). Build:
`tools/dtm_build.py` (all values + reasons at the top; asserts setup defaults == physics, LUTs exist) ->
`tools/install.py install` (live data.acd moved to archive/replaced_20261005_071622, data/ written, ui renamed).
Live = "Ford Escort Mk2 DTM v20"; v19 = car `ford_escort_mk2_tuned_backup_v19` "Ford Escort BACKUP v19 - DTM
conversion as it was" (acd decoded to data/, bank renamed, setups copied).
v20: Sunbeam v7 DWB rear (same pivots; Escort sweep: same camber/toe, RC 80 mm), HUB 45; springs 80/70 kN/m, dampers
7500/9500 F 6000/8500 R + fast 2500/5000, 2500/4000, ARB 45000/15000, packers 85/65 mm, bump stops 120000, camber -3/-1.5,
toe +0.0002 / -0.0004; Kunos DTM90 slicks S/M/H (default M) at r0.268 rim 0.1778, 245/255, ang. inertia x0.69;
190 DTM splitter (ground-effect LUT) + wing curves, angles 3/3, WING_1 0-3 / WING_2 0-4 in setup; diff 0.60/0.35/40;
brakes 2500 Nm 0.70 cockpit-adjustable (CSP advanced brake block dropped); STEER_LOCK 390 (30 deg); INERTIA
1.55,1.25,3.90; rods 0.012/0.055 (~25 mm below the ORIGINAL mod's stance - calculated, UNVERIFIED look). New 48-item
setup.ini (ARB, preload, rear camber/toe, bias, wings, 4-way dampers). Watchdog envelope: v20 lat/brake ceilings =
Merc 190 DTM's exactly (file-level check only). Model has per-corner WHEEL/SUSP nodes - DWB displays fine.
NOT done/verified: driving (Nik), stance look, AC log check after first run; old v19 setups don't fit - start from
default; Setup Coach fingerprint resets. Live is an unpacked data/ folder - Nik packs.

## 2026-10-05 ~17:10 - v21 AERO KIT INSTALLED (Nik: "go with the defaults" on the plan docs/plans/2026-10-05-aero-kit-blender.md)
Defaults = 90s DTM style, black satin wing, no flares (model tyres sit inside the arches), aero POSITION moved to the
parts, fixed-angle visual wing. Branch `aero-kit`, tag v21-aero-kit. BACKUP = `ford_escort_mk2_tuned_backup_v20`
("Ford Escort BACKUP v20 - before aero kit") - also the untouched model SOURCE for escort_scene.load_all().
Pipeline in tools/blender (README section): Sunbeam kn5_import/ac_kn5_export copied + fixed for kn5 v5 (no extra
header int) and LOD files that list all 171-172 materials (kn5_materials on the scene, fake users) -> all 4 files
round-trip BYTE-IDENTICAL. build_aero.py: wing on hood_trunk (boot lid animates in hood_anim.ksanim - wing opens
with it; LODs have no hood_trunk -> root), air dam from fenders_a_SUB2's boundary edge (z 0.010), splitter, skirts
from sill ray casts at z 0.045, rear lip from body_a_SUB1's rear edge with exhaust notch x 0.28-0.46 (+X = car's
left), strakes. Paint = "Material #25DQW" (AO_BODY + metal_detail x25) UV (0.857,0.398) AO 0.93; black =
"Material #166GG45" window trim. export_aero.compare(): every original node identical, AERO_* only added.
aero.ini: splitter 0,-0.42,1.65 (v20's -0.33 put it ~0.17 m up, past height_front_CL.lut's 0.13 m end), wing
0,0.50,-2.13 -> downforce +12 %, balance 46 % front unchanged. CoG in model space = -GRAPHICS_OFFSET.
NOT verified in game yet: look in CM showroom, AC log, ground clearance (estimates: dam 60 / splitter 57 / skirts
87 mm), mirror view past the wing. Live is a plain data/ folder - Nik packs.

## 2026-10-05 ~18:15 - v22 installed (Nik: v21 "feels ok, but the brakes are very sharp"; remove boot lip; 400 bhp)
Nik removed the original boot lip in Blender (deleted the mesh child of wing_a_SUB1 - 837 verts, black trim; the
dummy stays). I mirrored it: LOD_B/C wing_a_SUB1 is the merged black-trim mesh of the whole car -> deleted only faces
fully inside the lip's world box (x +-0.72, y 1.99-2.18, z 0.545-0.655; B -328, C -183 faces); LOD_D wing_a_SUB1 was
the lip alone -> object removed. export_aero.export() + name-aligned compare: only those nodes differ. Blend saved;
copy "blender/escort_aero BACKUP before rear-lip removal.blend". He said "export that as the v20 model" - live was
already v21, so it became v22 (told him).
Physics v22 (tag v22-400bhp, branch aero-kit): brakes 2100 Nm (v20 bug: 2500 Nm copied from the 190 without the
smaller-tyre correction -> ~1.8 g, locking); power_dtm.lut x400/466 (UI 400 bhp / 409 Nm / ~275 km/h; curves scaled from
backup_v19's ui = idempotent); fuel 2.91 km/l; final 3.09 kept (limiter 278 km/h ~= drag-limited 276 at 400 bhp, CdA
0.91 with default wings). Build now deletes proview_nodes.ini (AC regenerates). BACKUP v21 = "Ford Escort BACKUP v21 -
466 bhp, original boot lip". Live is a plain data/ folder - Nik packs.

## 2026-10-05 ~18:50 - v23 installed + rear-DWB-on-the-model PLAN awaiting Nik
Nik: remove the riveted black piece (= rear-arch stone guards: rivets = ALL of body_a_SUB11, plate = islands of black
trim body_a_SUB6 inside |x| 0.66-0.82, y 0.70-0.98, z -0.03..0.34; LOD B/C plate islands in the merged wing_a_SUB1);
windscreen banner removed by Nik (glassflivery_a_SUB0/1 + glassfintlivery_a_SUB0) - I also removed its interior face
glassfintlivery_a_SUB1 (material gls_windsheild_interior_banner, same box) + all LOD copies; skirts: build_aero.SKIRT
y -0.872..0.832 (front arch opening / rear arch rounded corner), taper 0, sections every 5 mm near the ends - outer face
follows the flares' kick (front +4 cm). Brakes 1680 Nm (Nik drove 80 % of 2100 and liked it; slider 70-100 %) - his
saved setups at 80 % must go back to 100 %. Camber: Setup Coach on v22 - front -3.7 static ran -2.3..-2.65 loaded
(tyre peak -2.48) = fine; rear wanted -3.9..-4.5 and hit the -3.5 limit -> rear range -5.0..0, defaults F -3.5 R -2.5.
Note v22 SC also read low-speed loose (78-195 snaps/100 corners, short sessions). BACKUP v22 car made; tag v23-model-tidy.
PLAN (not started, Nik asked to see it first): docs/plans/2026-10-05-rear-dwb-visual.md - leaf springs/axle/U-bolts/
dampers are suspension_a_SUB3/SUB1/SUB4 (static under suspension_a); new parts from dtm_build.REAR_DWB pivots
(WHEEL_LR world centre 0.714, 1.192, 0.092; Blender x = car left, +y = rear, z up); clearances: lower pivots 63-67 mm
from exhaust, upper pivots 26-44 mm under boot floor. Animation options A static / B upright on SUSP node / C CSP car
Lua script (medium confidence - prototype one corner). Recommended B first, then C.
Blender MCP gotcha: export_aero.compare() is positional - after a removed node everything reads "changed"; use a
name-aligned walk. Temp cameras for close-ups: create TMP_* camera, look(mode=camera), then delete + restore.

## 2026-10-05 ~23:00 - v24 installed (tag v24-model-doors-tank, commit af6801f; BACKUP v23 car made)
Nik's list: continue rear DWB, colliders "out of line", doors don't open, stainless tank where CM's yellow box is,
exhaust silencer not level, sequential shifter same height, door cards/winders/handles off, keep his "1.8" badge
removal (he deleted fenders_a_SUB6.001 - that mesh ALSO held a small front-centre emblem, now gone too; mention if
he asks), remove the cabin fire extinguisher. All done; renders in docs/plans/img/v24_*.png (sent).
* Rear DWB: plan's "upper pivots under the boot floor" was WRONG (owned in the plan doc) - they're inside the car
  (z 0.25 vs floor 0.105); turret posts down + pivot shaft (build_rear_dwb.TURRET).
* CM screenshot maths: fitted a camera to the red colliders.ini box (1 px) -> the cyan box = INERTIA box drawn from the
  model origin (not a collider); CM's fuel box = 55 l as 4:2:1 (0.76x0.38x0.19). collider.kn5 hugs the body within
  3 cm, same convention as Kunos 190 (model space). Model -> physics: up -0.400, forward -0.140.
* colliders.ini now floor box bottom at the floor pan + front-overhang box (handling only changes when bottoming -
  watch Nordschleife). FUELTANK -1.77 (tank met the boot wall).
* Doors: DOOR_L/R nodes (parts split from merged meshes), animations/car_door_L/R.ksanim (v2: quat xyzw, pos, scale;
  AC x = Blender x = car's left; -70 deg left), ext_config [ANIMATION_2]/[ANIMATION_3] on Extra C.
* Door cards removed -> outer skin faces out (AC culls) -> built AERO_door_inner_L/R (offset copy, body colour).
* Gotchas: kn5_pristine meshes export STORED normals - clear it on anything rotated (exhaust). Region deletes on
  merged LOD meshes need material filters; level_exhaust's region pass nudged boot bolts + a LOD B triangle - restored
  from a saved copy. Appended objects (libraries.load) have stale matrix_world - use the live object's.
* Tyres "left narrower" (Nik): main/LOD B/C tyres identical both sides (0.203 F / 0.223 R), winding fine, no per-side
  CSP config - not found; asked Nik for a screenshot. LOD D had no WHEEL_LF at all (original mod) - added.
NOT verified in game: doors in CM showroom / Extra C, collider bottoming, look of tank/shifter, AC log. Live = data/
folder - Nik packs.

## 2026-10-06 ~04:00 - v25 installed overnight (tag v25-v8-mirrors-treadplate, a00cb09; BACKUP v24 car = old 4-cyl)
Nik's list (6 Oct, "plan and build", then "I'm going to bed, I'll need screenshots"): door ends open, treadplate +
handle inside doors, rear ARB, battery back so the tank sits on the floor, shifter "bolted on afterthought", engine to
spec (asked confidence + backup), treadplate passenger footrest, Mk2 wing mirrors that reflect; mid-way: inside window
trim removed (v24 card removal took it - restored from the v23 blend), cabin fire extinguisher (gone in v24).
All built: tools/blender/v25.py + build_v8.py (+ build_tank changes); renders docs/plans/img/v25_1..9 (sent).
* Engine: no clean donor V8 (Kunos Lotus DFV merged/too tall) -> procedural compact 4.0 V8, own kn5 materials with
  generated DDS (cast alu / crinkle / anodised). Old engine kept in the blend as no_export (+ OLDENG_* bay islands);
  v25.swap_engine_back() restores. Honest: geometry detailed, textures cleaner than the original's baked photo look.
* Viewport gotcha for screenshots: TRIM "Material #166GG45" shows its light AO texture in Blender but is near-black
  in AC (ambient/diffuse 0.06); 503ds the reverse. Swap the image node temporarily (+ image.alpha_mode NONE for the
  body) for representative shots; restore before saving/exporting.
* Mistakes caught + fixed: move_battery's region rule dragged floor-pan/underbody verts (restored from the v24 blend,
  rule now boot equipment meshes only); the first V8 stow also took the 3 brake/clutch reservoir bases + a front
  canister/bracket (restored). bpy.data.libraries.load mutates the list you pass - pass a copy.
NOT verified in game: mirror reflections, V8 under AC lighting, door ends/handles, LOD look. Live = data/ - Nik packs.

## 2026-10-13 ~18:05 - v26 installed: physics rebuilt on the Kunos Escort Mk1 (Nik: "re-write the escort dtm v25 physics to be modelled on the kunos escort mk1")
* **Live car was NOT my v25 build.** Its data.acd (Nik packed 11 Oct 17:38, data/ unpacked 21:37) had a v19-era suspensions.ini
  (springs 45k, dampers 840/880, rods 0.10/0.126, STRUT_CAR z 0.003 = non-Mk1 caster, 5-link axle, tyres DTM90 from CM's tyre tool, brakes
  1800 Nm + CSP advanced block, diff 0.6/0.3/110, FFMULT 2.152) but v25's setup.ini ranges; Nik's Setup Coach setups (11 Oct) ran DTM values
  on top (springs 75/45, dampers ~11000, camber -4.2). Who/why unknown (not in any session). Model kn5s = my v25 export byte-for-byte.
  Saved as `decoded/data_acd_v25_live` + car `ford_escort_mk2_tuned_backup_v25` ("Ford Escort BACKUP v25 - physics as it was (before Mk1 rebuild)").
* Kunos Mk1 (885 kg, strut front / 5-link axle, GT70 tyres, 1800 Nm brakes) = the parent of this mod's physics AND of the Sunbeam. Nik's
  main Sunbeam (backup_v6) = Mk1 + mass-scaled springs 46/40, Mk1 dampers, diff 0.45/0.30/40, Mk1 aero - same recipe used here.
* v26 (`tools/mk1_build.py`, repo D:\Claude\escort_mk2_dtm, NOT committed - system rule: commit only when asked): K = 1050/885; springs 46/40,
  dampers/ARB 15000/rear 0/bump stops x K, rods 0.040/0.080 (= v20-v25 design stance, live hybrid sat ~60 mm higher), Mk1 hardpoints incl. caster,
  tyres GT70 resized (r .268, 255/265, FZ0 x K) = compound 0 + DTM90 S/M/H compounds 1-3, brakes 1800 Nm 70 % + cockpit bias, diff .45/.30/40,
  inertia 1.40,1.50,4.30 (the real Mk1 box; my old note of 1.60,1.35,3.83 was the Sunbeam's), FFMULT 2.30, 44-item setup.ini. Kept: V8 400 bhp
  6-speed, aero kit curves, ABS/TC, tracks/offsets/colliders/mirrors/fuel tank. Build report: ride 2.01/2.07 Hz = Mk1's, same damping ratios.
* install.py is now physics-only by default (`--with-model` copies export/); backup() no longer doubles CRs. Installed as plain data/ - Nik packs.
* NOT verified in game (AC not run): stance/arch gaps, splitter+floor clearance, steering weight, the DWB-looking rear on the model vs axle physics
  (DWB rear with Mk1 rates = small change in build_suspensions via dtm_build.REAR_DWB). Old setups don't fit - start from Default.
