# Ford Escort Mk2 DTM (ford_escort_mk2_tuned) - physics rebuild

Nik's "90s DTM" conversion of the Escort Mk2 (model 101Creative, physics base Kunos / graveltrap - personal use only).
v19 was undriveable; v20 (2026-10-05) rebuilt the chassis to Kunos' own DTM-era levels (Mercedes 190E Evo II DTM);
v26 (2026-10-13) rebuilds it again, this time on the Kunos Ford Escort Mk1 (`tools/mk1_build.py`).

## Pipeline
* `tools/mk1_build.py` - **current (v26+)**: builds `staging/ford_escort_mk2_tuned/data` from the Kunos Mk1 files (`ref/ks_ford_escort_mk1`)
  on top of the live car's data (`decoded/data_acd_v25_live`: everything tied to the model / engine / aero kit). Derivation of
  every number is in its docstring and in the v26 section below; it prints a ride/damping/brake report and asserts that every
  setup default equals the physics value it adjusts.
* `tools/dtm_build.py` - the v20-v25 build (kept for history; mk1_build imports its text helpers): builds from `decoded/data_acd` (v19 as installed) plus
  the Kunos Mercedes 190E Evo II DTM tyre model and aero curves (`ref/`). All design values and the reasons are at the
  top of the file; it asserts that every setup default equals the physics value it adjusts and that every LUT exists.
* `tools/install.py backup vN "label"` - the live car as a drivable `..._backup_vN` ("Ford Escort BACKUP vN - label").
* `tools/install.py install [--with-model]` - live data.acd -> `archive/replaced_<time>/`, staged data -> `data/`, car renamed.
  AC loads data.acd over data/, so the acd must go; Nik packs it himself afterwards. The 3D model (export/ kn5s + animations) is
  copied only with `--with-model` (a physics-only install must not overwrite a model Nik may have changed).
* `tools/dwb_kinematics.py` - rear double-wishbone sweep (camber / toe / roll centre) at the Escort's dimensions.
* `decoded/` (all v19-era acds) and `ref/` (Kunos DTM cars) are gitignored - other authors' data.

## 3D model / aero kit (Blender 5.2 + Blender MCP, `blender/escort_aero.blend`)
Run inside Blender with `tools/blender` on `sys.path`:
```python
import escort_scene, build_aero, export_aero
escort_scene.load_all()       # imports the untouched model (backup_v20 car's kn5 + LODs b/c/d); roundtrip() = byte-identical check
build_aero.build()            # AERO_* parts; build_aero.check() = sizes, ground/tyre clearance, attachment
# v24 - after build_aero.build(), which deletes every aero_part (these included):
import build_rear_dwb, build_tank, model_fixes
build_rear_dwb.remove_leaf_rear(); build_rear_dwb.build()   # leaf springs/axle out, DWB rear from dtm_build.REAR_DWB
build_tank.remove_old_tanks(); build_tank.build()           # old fuel cell/pot/extinguisher/under-floor tank out, stainless tank
model_fixes.level_exhaust(); model_fixes.strip_doors(); model_fixes.replace_gear_lever(); model_fixes.remove_extinguisher()
model_fixes.build_door_inner_skins(); model_fixes.build_doors()   # DOOR_L/R nodes; then write_door_ksanim(...) x2
export_aero.export()          # -> export/*.kn5 (main + LODs); export_aero.compare("A".."D") = original nodes unchanged
```
then `python tools/mk1_build.py` + `python tools/install.py install --with-model` (copies the exported kn5s + export/animations
too, binds the doors to Extra C in ext_config, old files archived).
`export_aero.compare()` is positional: after a removed node everything reads "changed" - diff by node path instead.
v25 (after the v24 steps; one-shot edits, plan + outcome in docs/plans/2026-10-06-v25-plan.md):
```python
import v25, build_v8
v25.door_boxes(); v25.restore_window_trim(v23_blend); v25.footrest(); v25.rear_arb(); v25.build_mirrors()
v25.clear_boot(); v25.move_battery(); build_tank.build()        # tank on the floor (battery back)
v25.blend_shifter(v23_blend)                                    # lever out of the original gaiter
v25.stow_old_engine(); build_v8.build(); build_v8.clear_bay(); build_v8.clear_lr()   # V8 swap
v25.swap_engine_back()                                          # BACKUP path: the old 4-cyl back, V8 out
```
`no_export` objects (the old engine `engine_a_*`, `OLDENG_*` bay islands) stay in the blend but are skipped on export.
`model_fixes` steps are one-shot edits of the blend (the blend is the master since Nik edits it too); the regions in
`build_tank.REGIONS` have no material filter, so on a re-run check the LODs (merged meshes) as in the v24 audit.
Parts: inverted-NACA pedestal wing + Gurney + endplates on the boot lid (`hood_trunk`, opens with the boot), body-colour
air dam grown from the valance edge with a black splitter blade, small body-colour sill skirts, black rear lip with an
exhaust notch + 4 strakes. Body colour = the car's paint material (one lit texel); black = the window-trim material.
Ground clearances are estimates from the model (air dam ~60 mm, splitter ~57 mm, skirts ~87 mm) - check in game.
`blender/` and `export/` are gitignored (101Creative's model).

## Versions
| Version | What | Car |
|---|---|---|
| v19 | soft road springs 35/26, dampers ~840, rods +140/+126 mm, semislicks, road aero (rear lift), coast 0.02, four-link axle | `ford_escort_mk2_tuned_backup_v19` "Ford Escort BACKUP v19 - DTM conversion as it was" |
| v20 | double-wishbone rear (Sunbeam v7 geometry: -0.82 deg camber @ +40 mm, bump steer < 0.04 deg, RC 80 mm), springs 80/70, dampers 7500/9500 F 6000/8500 R, ARB 45000/15000, packers 85/65 mm, DTM90 slicks S/M/H 245/255, 190 DTM splitter + wing (adjustable), diff 60/35 % + 40 Nm, brakes 2500 Nm 70 % with cockpit bias, lock 30 deg, inertia box 1.55,1.25,3.90, ride ~25 mm below the original mod | `ford_escort_mk2_tuned_backup_v20` "Ford Escort BACKUP v20 - before aero kit" |
| v21 | 90s DTM aero kit on the model (wing, air dam + splitter, skirts, rear lip); aero.ini splitter/wing POSITION moved to the parts (0,-0.42,1.65 / 0,0.50,-2.13): splitter now inside its ground-effect curve, downforce +12 %, balance unchanged 46 % front | `ford_escort_mk2_tuned_backup_v21` "Ford Escort BACKUP v21 - 466 bhp, original boot lip" |
| v22 | model: the original boot lip (`wing_a_SUB1`) removed by Nik in Blender, mirrored in LODs B/C (faces in the lip's box) and D (node); engine x400/466 = 400 bhp (same curve shape); brakes 2500 -> 2100 Nm (v20 forgot the smaller tyre: same braking force at the road as the 190 DTM); fuel 2.91 km/l; gearing kept - 3.09 final now meets the limiter (278 km/h) right at the ~276 km/h drag-limited top speed | `ford_escort_mk2_tuned_backup_v22` "Ford Escort BACKUP v22 - boot lip removed, 2100 Nm brakes" |
| v23 | model: windscreen banner removed (Nik; + its interior face `glassfintlivery_a_SUB1`), rear-arch riveted stone guards removed (`body_a_SUB11` rivets + plate islands of `body_a_SUB6`, LODs matched), skirts run arch to arch at full section following the flares (`build_aero.SKIRT`); brakes 1680 Nm (= Nik's 80 % of 2100) with a 70-100 % slider; camber defaults -3.5 F / -2.5 R, rear range to -5.0 (Setup Coach hit the old -3.5 limit) | `ford_escort_mk2_tuned_backup_v23` "Ford Escort BACKUP v23 - leaf-spring model, no opening doors" |
| v24 | model: leaf-spring axle replaced by the physics' double wishbone (A-arms, toe links, coilovers, drive shafts; uprights ride on SUSP_LR/RR; upper inner pivots sit inside the car above the floor over the axle - turret posts down to it); stainless 55 l tank on a cradle where CM draws the physics tank, old fuel cell/pot/front-wall cylinder/boot extinguisher/under-floor tank removed; exhaust silencer levelled (was rolled 17 deg, yawed 14, pitched 4) and tail pipe straight; door cards, winders, handles, lock knobs off + body-colour inner door skins; opening doors (DOOR_L/R + car_door_L/R.ksanim, 70 deg, also on Extra C); sequential shifter (knob where the old one was); cabin extinguisher removed; Nik's "1.8" badge removal kept; LOD D gets its missing left-front tyre. Physics: colliders.ini on the floor pan + a front-overhang box (old floor box sat 3-5 cm up); fuel tank -1.70 -> -1.77 (tank met the boot wall) | `ford_escort_mk2_tuned_backup_v24` "Ford Escort BACKUP v24 - old 4-cyl engine, no mirrors" |
| v25 | model: door ends closed (body colour), inner door panels in dull steel treadplate (new kn5 material + generated textures) with grab handle + release lever, inside window trim restored (v24's card removal took it); rear anti-roll bar modelled (physics already had one, 15000 adjustable); battery moved back/out and the tank sits on the boot floor (stepped bottom, pads, straps; fuel lines/straps/pumps cleared); sequential lever now rises out of the original gaiter (no box); 4.0 V8 (90 deg, DOHC, crinkle covers, coil packs, plenum + throttle body, dry sump + tank, 4-into-1 headers into the original front pipe) replacing the 4-cyl (kept in the blend, not exported); treadplate passenger footrest; Mk2 door mirrors with reflecting glass (mirrors.ini L/C/R). Physics: FUELTANK y -0.148 (tank on the floor), mirrors.ini | `ford_escort_mk2_tuned_backup_v25` "Ford Escort BACKUP v25 - physics as it was (before Mk1 rebuild)" - NB its physics is the 13 Oct live hybrid, see below |
| v26 | physics only, model untouched: chassis rebuilt on the Kunos Ford Escort Mk1 (strut front with the Mk1's caster, 5-link live axle, Mk1 hardpoints), springs 46/40 kN/m, dampers, front ARB 15000 / rear 0, bump stops all = Mk1 x 1.186 (mass 1050 / 885), rods 0.040/0.080 (Mk1; = the v20-v25 design stance), Vintage GT70 tyre model resized (r 0.268, 255/265, FZ0 x 1.186) as compound 0 + DTM90 slicks S/M/H as compounds 1-3, Mk1 brakes 1800 Nm / 70 % front / cockpit bias, diff 0.45/0.30/40 (Sunbeam), inertia 1.40,1.50,4.30, FFMULT 2.30, STEER 450/16, new 44-item setup.ini. Kept: V8 400 bhp, 6-speed, aero kit curves, ABS/TC, all model-tied files | live, "Ford Escort Mk2 DTM v26" |

Planned, not started: rear suspension on the model -> double wishbone, `docs/plans/2026-10-05-rear-dwb-visual.md`.

## v26 physics - how it was derived (13 Oct 2026)
Nik: "re-write the escort dtm v25 physics to be modelled on the Kunos Escort Mk1". Recipe = the Talbot Sunbeam's (Mk1 physics
that Nik loves): the Mk1 file set is the template and only mass-dependent rates change; model-tied files are kept.
* **Found first:** the live "v25" car's data.acd (packed by Nik 11 Oct) was NOT the v20-v25 DTM chassis from this repo - its
  suspensions.ini was v19-era (springs 45 kN/m, dampers 840/880, rods 0.10/0.126, STRUT_CAR z 0.003) while setup.ini still had
  the DTM ranges, and Nik's saved setups (Setup Coach, 11 Oct) ran DTM values on top (springs 75/45, dampers ~11000, ARB 8/3 clicks,
  camber -4.2). Whoever changed it isn't in any session history. That hybrid is `decoded/data_acd_v25_live` and the BACKUP v25 car.
* Mass ratio K = 1050 / 885 = 1.186. Springs 38000 x K = 45.1k -> 46k, 34000 x K -> 40k (the setup's 2 kN/m grid; = Sunbeam v6).
  Dampers x K snapped to the setup grid, front ARB 12500 x K -> 15000, bump stop x K. Result (printed by the build): ride 2.01/2.07 Hz
  (Mk1 1.99/2.08), static deflection 62/58 mm (63/57), damping ratio bump/rebound 0.41/0.65 and 0.24/0.52 (0.41/0.66, 0.25/0.52).
* Tyre: Mk1 Vintage GT70 (DY 1.287, DX 1.297, load sensitivity 0.71/0.72) at r 0.268 / 255 / 265 (CM's measurement of the model),
  angular inertia x (0.268/0.288)^2, FZ0 x K - same grip level at this car's static load. DTM90 S/M/H (Merc 190 files) are compounds 1-3.
* Brakes: Mk1's 1800 Nm = 1.30 g capacity on this car (Mk1 1.44 g; Nik liked ~1.22 g in v23 - the Brake power slider 80-100 % reaches 1.04 g).
  Handbrake 1600 Nm, bias 70 % (Mk1 69.5), disc node names/glow from the live car.
* Stance: S = rod - m g / k. v20-v25 design -23/+22 mm, v26 -22/+22 mm (Mk1 rods), the 13 Oct live car +38/+75 mm. Aero kit ground effect
  (splitter 0.08 m at design ride) and the colliders were built for the lower stance. UNVERIFIED in game.
* Dropped from the hybrid: CSP `[_EXTENSION]` TORQUE_MODE_EX=2 (the original mod's; neither Mk1 nor Sunbeam has it), rear camber/toe
  setup items (live axle), the brakes' CSP advanced system (Mk1's simple one), CM tyre-tool files (`__cm_*`).
* Not verified in game: nothing could be driven from this session (AC not run). Check: ride height/arch gaps, splitter and floor clearance,
  steering weight (caster is back to the Mk1's 8.3 deg from the hybrid's 3 deg; FFMULT 2.30 is the Sunbeam's equivalent), rear-axle
  look against the double-wishbone parts on the model (v24 modelled a DWB rear; physics is the Mk1 axle again - a DWB rear with Mk1 rates
  is a one-section change in mk1_build.build_suspensions() using dtm_build.REAR_DWB).
* Old saved setups (incl. Setup Coach's) do not fit: setup.ini ranges changed, values are stored as clicks - start from Default.
  `Documents/Assetto Corsa/setups/ford_escort_mk2_tuned_backup_v25` holds copies of the old ones.

## Diagnosis (v19 vs Kunos DTM cars) and open points
See memory `escort-mk2-dtm-project`. Ride height was set by calculation (rods from the original mod's 0.060/0.099,
corrected for the stiffer springs) - check the stance and adjust in setup; bake Nik's preferred heights into the
build. Old v19 setups (Documents/Assetto Corsa/setups/ford_escort_mk2_tuned) don't fit v20's ranges - start from default.
