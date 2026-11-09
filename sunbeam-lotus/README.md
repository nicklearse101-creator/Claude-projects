# Talbot Sunbeam Lotus rally - Assetto Corsa car (personal project)

Status 2026-09-28: **3D/Blender work done** (Nik: "we're done with Blender for now"). Next phase: setup/physics -
start with `refs/physics_research.md`.
Model update 2026-10-06 (Nik): harness tails anchored to the floor, splitters reworked, Escort Mk2 4-cylinder in the
bay with a Lotus badge - installed into `..._backup_v6` only ("our main model"; model files only,
`tools/install_models.py`). The live v7 car still has the 28 Sep model. Plan: `docs/plans/2026-10-06-belts-splitters-engine.md`.

Car id `talbot_sunbeam_lotus_81_works`, in game "Talbot Sunbeam Lotus Rally". It is a rally conversion of the
existing mod `talbot_sunbeam_lotus_lhd_stock` (model by marcel du PMU / Mr.Hunt, v1.1 by ACTK) plus parts grafted
from the Escort Mk2 rally-spec mod (Alan Mc Enroe). **Personal use only - do not share or put on a server without
those authors' permission.** Physics: our own, on a Kunos `ks_ford_escort_mk1` base (`refs/donor_data`).

## Rebuild and install (the whole pipeline is scripted)

1. **Blender 5.2** with `blender/sunbeam_rally_on_stock_model.blend` open (Blender MCP), run in Blender:
   ```python
   load("build_rally_parts").build()   # everything on the car (see below) - repeatable, same result every time
   load("export_rally").export()       # -> export/sunbeam_rally.kn5, saves the .blend
   load("build_lods").build_all()      # -> export/sunbeam_rally_lod_{b,c,d}.kn5, saves the .blend
   ```
   (`load` = importlib from `tools/`, as in every script.) Save/export BEFORE taking viewport screenshots - Blender
   has crashed on screenshots after big hide/show changes (unsaved work lost).
2. **Stage** (outside Blender, any time): `build_rally_on_stock.build()` with `CAR` pointed at `staging/<car id>` -
   builds data/ (physics from `build_car.build_data()` + model-tied values), ui, skins, sfx, extension, copies the
   kn5s. A rebuild reproduces the installed car byte-for-byte (checked 2026-09-28).
3. **Install**: `python tools/install_staged.py` - refuses while `acs.exe` runs; the old version goes to
   `archive/replaced_<timestamp>/`. Model-only change to a car whose physics Nik edited himself:
   `python tools/install_models.py <car id>` copies just the four `sunbeam_rally*.kn5` (old ones archived).

Rendering stills to files (bpy.ops.render): the stock parts the build stows (`mod_*` originals, the stock engine) are
hidden in the viewport but still render-enabled - hide every mesh that is not `visible_get()` first, or the render
shows the stock car. `tools/render_stills.py` does that (camera/sun/floor, cutaways by clip distance, bonnet off).

Note: the installed copy's `data/` was packed into `data.acd` (Content Manager) on 2026-09-28; installing a new build
brings back a plain `data/` folder - re-pack in CM if the server needs it.

## What build_rally_parts.build() does (in order)

| Script | Makes |
|---|---|
| `build_extras.restore_modified()` | puts back stock meshes edited last time (`mod_*` copies) so each build starts clean |
| `build_lips.py` | ALL body-colour trim as one mesh per side (`RALLY_flares`): front splitter lip -> loft -> front flare -> sill lip -> rear flare -> loft -> rear lip, pinned 0.5 mm into the paint; lips are mouldings with a rounded nose (not a knife edge), long Hermite lofts into the flares, the rear run smoothed as one and rigid-snapped onto the valance; exhaust notch handled; black blades `RALLY_blade_front/rear` (rounded leading edge, tapered ends, rear strakes as fins) |
| `build_rally_parts.py` | Escort Mk2 wheels (trued up, ksTyres), spot lamps + bar, mud flaps; calls the others |
| `build_cage.py` | stripped rear + bulkhead, FIA amendment 7 roll cage (black) + harness bar, Escort buckets, harnesses (CINTURE_ON/OFF) fitted to the real driver body; shoulder straps over the harness bar and down to floor anchors at y 1.10 (adjuster, snap hook, eye bolt, plate - `BELT_anchors_*`), tail UVs kept on the webbing (`STRAP_BAND`) |
| `build_extras.py` | bonnet scoop (grille + hole into the bay) + pins, front plate on bumper, sequential shifter in the old gaiter, Escort hydraulic handbrake, old controls removed (both cockpits), enlarged exhaust, red needles, side stripes lifted off the paint (anti z-fighting) |
| `build_engine_swap.py` | `ENGINE = "escort4"`: the Escort Mk2 4-cylinder (exported from the Escort blend to `refs/donor_escort4`, gitignored) grafted into the bay at the Escort's own position (axles 6 mm apart), filtered (under the false bay floor / inside Sunbeam parts / past the firewall / the FORD letters), below z 0.12 cut; the stock engine + bay bits touching it kept but not exported; Lotus badge (`refs/badge_textures`, drawn by the script) on the cam-cover pad where FORD was. `ENGINE = "stock"` puts the stock engine back |

`stage_build.py` builds into `staging/` only (safe; then `install_staged.py`). Helpers: `driver_pose.py` (the AC driver posed from our knh/ksanim - `reference_object()`), `bview.py` (viewport
views), `kn5_import/ac_kn5_export/kn5_inspect/kn5_compare` (lossless kn5 round trip + checks), `ac_static_ride.py`
(ride-height fit from AC shared memory -> `export/graphics_fit.json`). Old from-scratch model scripts
(`build_body/details/wheels`, `export_car`, `trace_blueprint`) are superseded (model archived in `archive/v0.3_own_model`).

## Physics versions (each kept as a drivable backup car + git tag)

| Version | What | Backup car / tag |
|---|---|---|
| v1 | Kunos Escort Mk1 chassis + FIA gearbox, real power +75 bhp, FFB 2.30 | `talbot_sunbeam_lotus_81_works_backup_v1` ("Talbot Sunbeam BACKUP v1 - Escort chassis"), tag `v1-escort-chassis` |
| v2 | + Sunbeam four-link rear axle (45 deg upper links, no Panhard) - Nik: "feels good" | `..._backup_v2` ("Talbot Sunbeam BACKUP v2 - four-link only"), tag `v2-four-link` |
| v3 | + plate LSD 45/30/40 Nm, Salisbury final drives, 11.3:1 rack (FFB 1.62), cockpit brake bias 62 %, revs to 9000, inertia height 1.40 | `..._backup_v3` ("Talbot Sunbeam BACKUP v3 - before adjustable dampers"), tag `v3-lsd-ratios`; arm-to-lever animation from 7500 rpm |
| v4 | + adjustable dampers: DAMPERS tab in setup.ini (bump / fast bump / rebound / fast rebound x 4 corners, `build_car.DAMPER_RANGES`); fast-damper defaults nudged <2 % onto a click (front 1434->1400, 2089->2100) | `..._backup_v4` ("Talbot Sunbeam BACKUP v4 - before stiffer default springs"), tag `v4-dampers` |
| v5 | springs sized for the Sunbeam's weight: 46/40 N/mm (was the 885 kg Escort's 38/34 - it rode on its packers every lap, Setup Coach 110 % F / 103 % R), setup ranges 30-60 / 20-50 step 2, push rods 29 / 70 mm to keep the stance (`build_car.apply_springs`) | `..._backup_v5` ("Talbot Sunbeam BACKUP v5 - before adjustable bars and preload"), tag `v5-springs` |
| v6 | adjustable anti-roll bars (front 5000-40000, default 12500; rear 0-12000, default 0 = off, a works 1/2" bar ~6000), diff preload 10-200 Nm (default 40), springs 20-90 / 16-80, damper maxima +45 % - defaults unchanged, drives as v5 | `..._backup_v6` ("Talbot Sunbeam BACKUP v6 - four-link axle, adjustable bars"), tag `v6-bars-preload` |
| v7 | double-wishbone rear (NOT historical - the works car kept the four-link live axle; Nik's pick), hub 40 kg/corner, camber -1.0 / toe-in 0.0004, rear camber (-3..0) and toe setup items; geometry checked by kinematic sweep (`build_car.REAR_DWB`, `REAR_TYPE`) | the live car, "Talbot Sunbeam Lotus Rally v7" |

`tools/make_cheat_car.py 10` makes the watchdog's known-cheat test car `..._cheat_plus10` ("Talbot Sunbeam CHEAT +10% power (watchdog test)"): the live car with power.lut x1.10, nothing else changed; the honest files go to `watchdog_reference/<id>/data` (gitignored), listed first in ac-physics-watchdog's `watchdog.ini [analysis] content_dirs` so the watchdog judges it against the real car. Rebuild it whenever the live physics change (move the old car, its reference and its setups to archive/ first - done for v5).

`tools/backup_car.py v4 "what it is"` makes `..._backup_v4` / "Talbot Sunbeam BACKUP v4 - what it is" from the live car. Bump `PHYSICS_VERSION` with each physics change. Backups are always called BACKUP - never give one a bare version suffix (it was mistaken for the newest car).

## Open items

* Harness belts "a bit loose on the driver's body" (Nik) - pull webbing within ~4 cm of the suit in to 6 mm
  (`build_cage.clear_of_driver` only pushes out today).
* `RALLY_TRACK_ADD` in `build_rally_on_stock.py` is 0.096 while the current flares' ideal is 0.081 (tyres ~7 mm
  further out than designed) - revisit with the physics.
* Physics: see `refs/physics_research.md`.

## Reference material

`refs/homologation` (FIA 1700 + 44 page scans), `refs/real_car_specs.md`, `refs/physics_research.md`,
`refs/donor_data` (Kunos Escort Mk1 data), `refs/stock_mod_data` (stock Sunbeam mod data). Decrypting any car's
data.acd: `D:\Claude\setupcoach-tools\acd\acd_decoder.extract_car(car_id, Path(out))`.

## Ideas from the Escort donor (2026-09-28, not started)

Spare wheel in the stripped rear; Escort rally pedals; engine-bay detail under the scoop grille; shift light
(donor RPM_LED_0/1); interior mirror / banner / wipers; plus the open items above. Nik to choose.
* Optional later: CSP LUT dampers (`[_EXTENSION] DAMPER_LUTS=1` in suspensions.ini + `dampers.ini` + one
  speed|force .lut per click point, setup items `DAMPER_BUMP_xx` / `DAMPER_REBOUND_xx` as click numbers) for shaped
  (e.g. digressive) curves - examples in Nik's install: gt4_alpine_a110, gt4_bmw_m4, sv8_camaro_v2. v4 uses AC's
  standard bilinear dampers (numbers in suspensions.ini, no .lut), exactly like Kunos' live-axle AE86.
