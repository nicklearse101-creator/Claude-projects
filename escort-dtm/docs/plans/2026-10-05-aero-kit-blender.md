# Escort Mk2 DTM - rear spoiler + aero kit in Blender (plan)

Car: `ford_escort_mk2_tuned` ("Ford Escort Mk2 DTM v20"), repo `D:\Claude\escort_mk2_dtm`.
Model by 101Creative, so this is personal use only, same as the Sunbeam.
Written 2026-10-05. It's a plan only, nothing has been built or changed yet.

## Where things stand

* v20 physics already **has** aero in `aero.ini`: `WING_1` FRONT (190 DTM splitter, ground-effect LUT, angle 3,
  setup 0-3) at CoG +2.00 m fwd / -0.33 m up, and `WING_2` REAR (190 DTM wing curves, angle 3, setup 0-4) at CoG
  -2.00 m / +0.30 m. **The 3D model has neither part**, so the car is making DTM downforce with a road-car body.
  This job is mostly about the look, plus putting the physics wing positions where the parts end up.
* The Escort kn5 is **readable** (kn5 v5, not encrypted, 162 textures, 171 materials). Useful existing pieces:
  `carPaint` (body colour), `plastic_rgh_010101FF` (black), `carbonfiber_001`, front bumper `bumperf_a`, rear
  `bumperr_a`, boot lid node `hood_trunk` (AC 0, 0.774, -1.627), plus LODs b/c/d.
* The whole Blender pipeline already exists from the Sunbeam (`D:\Claude\talbot_sunbeam_lotus\tools`):
  lossless `kn5_import` + `ac_kn5_export` (byte-identical round trip), `BodySampler` ray-casting onto the real paint,
  `build_lips` (lips/flares grown from traced panel edges and pinned into the paint), `build_lods`, `kn5_compare`,
  `ac_static_ride`, `bview`. Blender 5.2.1 + Blender MCP are connected (addon protocol 11 vs 13 expected, so it
  works but could be updated).

## Lessons from the Sunbeam kit (these shape the design)

1. Add-ons look fake unless they **start on a real body surface**. Grow them from traced panel edges, in body
   colour, pinned about 0.5 mm into the paint (`build_lips.snap`).
2. Keep side skirts **small**. On the Sunbeam the skirt only needed to blend the arch into the sill.
3. The splitter has to clear the **front tyres at full lock**. The Sunbeam blade touched them twice. v20 also runs
   about 25 mm lower and on 245/255 slicks, so check this at the AC track width and steering lock.
4. Body-colour parts get **one clean paint UV**. Nearest-vertex UVs picked up stripes from the texture. The
   exporter's n-gon tangent bug (black parts) is already fixed.
5. **Save/export before any viewport screenshot.** Blender crashed after big hide/show changes and in Material
   Preview. Use few screenshots and rely on numeric checks.
6. Backups are named `..._backup_vN` / "Ford Escort BACKUP vN - ..." and the live car carries its version.

## Decisions for Nik (recommended defaults in **bold**)

| # | Question | Options |
|---|---|---|
| D1 | Style | **A: 90s DTM** (deep air dam + flat splitter, pedestal rear wing with endplates, small skirts, rear valance with strakes; matches the 190 DTM aero already in the physics) · B: late-70s Group 2 (chin spoiler + boot-lid "tray"/ducktail, bolt-on flares) · C: mix (A at the front, B tray wing) |
| D2 | Wing finish | **black satin / carbon** (no skin or UV issues) · body colour |
| D3 | Arch flares | **only if the 245/255 slicks poke out** (measured in step 2) · always · never |
| D4 | Physics positions | **move `WING_1/2 POSITION` to the built parts** (curves untouched) · leave aero.ini alone |
| D5 | Wing angle visible in setup (0-4) | **fixed visual** · try a CSP/ksanim tie-in later (unverified, research first) |

## Steps

### 0. Safety + setup (about 15 min)
* `tools/install.py backup v20 "before aero kit"` creates `ford_escort_mk2_tuned_backup_v20`
  ("Ford Escort BACKUP v20 - before aero kit").
* New git branch `aero-kit`. Copy the Sunbeam helpers into `escort_mk2_dtm/tools/blender/` (kn5_import,
  ac_kn5_export, kn5_inspect, kn5_compare, build_lods, bview, BodySampler). Copy them rather than import across
  repos, so each project stays rebuildable on its own.
* `blender/escort_aero.blend` and `export/*.kn5` go in .gitignore (other authors' assets).

### 1. Round-trip gate (must pass before any modelling)
* Import `ford_escort_mk2_tuned.kn5` and the 3 LODs into Blender, re-export unchanged, and **SHA-compare** them.
  Known limits: skinned meshes (class 3) and kn5 v5 vs the exporter's default v6. If it isn't byte-identical,
  fix the importer/exporter first. Don't model on a pipeline that changes the car.

### 2. Measure the body (scripted, numbers not screenshots)
* Trace with BodySampler (BVH of `carPaint`): front valance/bumper lower edge, sill line, arch openings,
  rear valance edge, and the **boot lid outline + rear edge** (wing feet and pedestal footprint).
* Tyre fit: v20 track + 245/255 widths vs the arch lips. This decides D3.
* Static ride: `ac_static_ride.py` with the car in the pits, which gives v20's real ground clearance at the
  splitter and valance.
* Convert `aero.ini` CoG-relative positions to model space (GRAPHICS_OFFSET 0,-0.400,-0.140, pitch -0.3,
  CG_LOCATION) and drop REF empties where physics thinks the splitter/wing are.

### 3. Build the parts: `tools/blender/build_aero.py`, one function per part, repeatable
| Part | Design (style A) | Material |
|---|---|---|
| Rear wing | aerofoil main plane (chord ~260 mm, span inside body width ~1.35 m), Gurney lip, flat endplates, 2 pedestal stalks bolted to the boot lid, top about level with the roof's rear edge; parented to `hood_trunk` (opens with the boot) | D2 |
| Front air dam + splitter | air dam grown down from `bumperf_a`'s lower edge (build_lips path method) + 6-8 mm flat blade ~50 mm proud; tyre-lock and ground clearance checked in code | carPaint + black blade |
| Side skirts | small sill lip joining front dam to rear valance, height pinched into the arch ends | carPaint |
| Rear valance/diffuser | drop panel under `bumperr_a` with 4 strakes, exhaust notch kept | black |
| Flares (if D3) | Sunbeam `flare_path` sections, sweep ends into the sill lip | carPaint |
* Each part gets `check()` (clearances, penetration, symmetry) and gets reported in numbers.
* One overview render per part, after saving.

### 4. Materials + UVs
* Body-colour parts use the existing `carPaint`, with every UV on one clean paint texel picked from the skins.
  Check against each skin in `skins/`, since a livery won't flow onto new parts.
* Black/carbon parts reuse the existing materials (no new textures where possible).

### 5. LODs
* `build_lods` adds decimated parts to lod_b/c, and a simple wing box only in lod_d. LOD textures resolve by name
  from the main kn5.

### 6. Export + install
* Export main + LOD kn5s to `export/`, then use `kn5_compare` vs stock. **Only new nodes added; everything else
  identical.**
* Extend `install.py` to copy the kn5s. The live kn5s go to `archive/replaced_<time>/` first. `lods.ini`,
  collider and CSP extension stay unchanged.
* If D4: `dtm_build.py` updates `WING_1/2 POSITION` only, so Setup Coach's fingerprint will reset.

### 7. Verify (before calling it done)
* AC log after the first load: no missing-node or texture errors.
* Content Manager showroom (Nik's look): wing, dam, skirts and valance sit on the body, nothing floats.
* In-game checks: rear-view mirror not blocked by the wing; no splitter/tyre contact at full lock; no floor
  scraping at v20 ride height (or say how much).
* Nik's verdict, then git tag `v21-aero-kit` and a README version row.

## Risks
* The importer may not handle every Escort mesh type (skinned parts). Step 1 catches this.
* The splitter vs the lower v20 stance needs real ride-height numbers (step 2), not guesses.
* The boot lid **does** animate (`hood_anim.ksanim` moves the trunk). A wing parented to `hood_trunk` will lift
  with the boot, which is correct for a lid-mounted wing. Check that it doesn't clip the rear screen or roof when
  the boot is open.
* Moving the aero positions changes the handling slightly, which is why D4 is Nik's call.
