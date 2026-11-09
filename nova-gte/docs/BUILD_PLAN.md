# Build plan: Vauxhall Nova GTE 1989 (vauxhall_nova_gte_1989)

Status: DRAFT for approval. No building starts until Nik says go.
Specs: docs/SPEC_SHEET.md. Decisions: docs/DECISIONS.md. References: reference/.

## Phase 1 - Blender scene and reference setup
- One .blend, real-world units (metres), car faces -Y, origin at centre of front axle line on ground.
- Dimension anchors from the spec sheet (length, width, height, wheelbase 2343 mm, tracks, 175/65 R14 rolling circumference about 1.776 m).
- Reference images placed as image planes in side, front, rear and top views. Free blueprints are too small, so the red-GTE and Commons photos are used to correct proportions by overlay.
- Checkpoint: Nik reviews the scene screenshot.

## Phase 2 - Body shell (low-poly to mid)
- Blockout of the shell as one clean quad mesh: roofline, pillars, sills, wheel arches, bonnet and tailgate shut lines.
- Pre-facelift GTE details: front bumper and spoiler, side skirts, rear spoiler, decals later.
- Separate objects for doors, bonnet, tailgate, bumpers, glass, lights.
- Checkpoint: side, front and rear overlay against photos.

## Phase 3 - Body detail
- Panel gaps, door handles, mirrors, wipers, badges, headlamps and tail lamps, grille, exhaust, number plate recess, fuel flap, sunroof.
- Gun-metal grey paint (Steel Grey reference), RHD.

## Phase 4 - Wheels, tyres and running gear
- Factory 5J x 14 three-arm alloys, 175/65 HR14 tyres, 236 mm vented front discs and rear drums, calipers, hubs.
- Visible suspension: struts, springs, wishbones, anti-roll bars, driveshafts, rear beam.

## Phase 5 - Interior and engine bay
- Dashboard (mirror the LHD references for RHD), seats, door cards, gear lever, three-spoke wheel, instruments, pedals, headlining, sunroof.
- Engine bay: 1.6 E16SE, airbox, injection, battery, struts, brake servo, fluid reservoirs.
- Underbody simplified; LODs after the main model.

## Phase 6 - UVs, materials and textures
- UV layout per part, PBR materials (paint, glass, rubber, chrome, plastics, fabric), dirt and wear off by default.
- Skins: default gun-metal grey, extras optional.

## Phase 7 - Assetto Corsa conversion
- Reuse the Sunbeam export pipeline (D:\Claude\talbot_sunbeam_lotus\tools): naming, kn5, ui folder, colliders, LODs, driver model, animations (doors, wipers if wanted), lights.
- Folder: content/cars/vauxhall_nova_gte_1989.

## Phase 8 - Physics (data/)
- car.ini: mass 834 kg plus driver, CG estimate front-heavy, wheelbase 2.343 m, tracks from spec sheet.
- engine.ini and power.lut from the brochure torque curve (135 Nm flat 3500-5000, 74 kW @ 5600), idle 900-950, fuel cut about 6200.
- drivetrain.ini: ratios 3.55/2.14/1.43/1.12/0.89, final 3.74, open diff (confirm), clutch 200 mm.
- suspensions.ini: struts front, torsion-beam rear, spring rates from spec derivation (front about 22 N/mm, rear about 25 N/mm), alignment from Haynes, anti-roll bars.
- tyres.ini: 175/65 R14 road tyre, pressures 1.8/1.6 bar.
- brakes.ini: 236 mm vented front, drums rear, no ABS.
- Dampers and ride height are estimates, flagged in the file comments.
- Sound: deferred (Nik's call), temporary placeholder bank.

## Phase 9 - Test and tune
- In-game test: top speed (117 mph), 0-60 (about 9.1 s), lift-off oversteer behaviour, understeer balance.
- Fix-ups and a final README with sources and known estimates.

## Open items before or during the build
- Rev limit, damper rates, ride height (estimates stand until a source is found).
- Engine sound.
- Straight-on profile and front underside photos (nice to have).

## Approval needed
1. OK to start Phase 1 (Blender via the connected Blender tool)?
2. Mesh target: about how heavy should the model be? Suggested: about 150k triangles for the exterior and cockpit, with LODs.
3. Interior detail level: full dashboard and seats with working gauge needles?
