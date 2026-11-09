# Build phases

Each phase ends with something drivable or inspectable in AC. Do not start a phase's detail work until the previous phase's "Done when" is met, except where noted.

## Phase 0 - References and specs
- [ ] Collect the reference pack (below) into `reference/`
- [ ] Fill every GAP in `SPEC_SHEET.md`, resolve each CONFLICT with a stated reason
- [ ] Confirm RHD, facelift variant and wheel/tyre spec with the user

**Reference pack**
- Brochure, press kit, workshop manual, 2+ period road tests
- Photos of a genuine late-run GTE: front, rear, both sides, all four 3/4 views, roof, underside, wheel close-ups, badges, lamps, door handles, mirrors, glass etched markings
- Interior: dash and instrument cluster (straight on), centre console, switchgear, steering wheel, seats (front/rear, side bolsters), door cards, headlining, pedals, boot, load cover
- Engine bay: full view, air intake and manifold, ancillaries, battery, fuse box, bonnet underside
- Audio: cold start, idle, steady revs, full-throttle pulls, lift-off, inside and outside the car, ideally an E16SE Nova or Corsa A GSi
- Blueprints, ideally orthographic, correctly scaled to the sourced wheelbase

**Done when:** spec sheet has no unexplained gaps for body dimensions and mass, and the photo set covers every area above.

## Phase 1 - Pipeline proof
- [ ] Inspect a stock Kunos car in ksEditor and record node names, shaders and file layout in `EXPORT_NOTES.md`
- [ ] Blender scene with correct scale and the AC node hierarchy, using a placeholder box body and four wheels
- [ ] Determine and document working FBX export settings
- [ ] Export to KN5 and load in AC
- [ ] Skeleton physics (`car.ini`, `drivetrain.ini`, `suspensions.ini`, `tyres.ini`, `brakes.ini`) so the box drives
- [ ] Deploy script and a quick check script (file presence, ini sanity)

**Done when:** the box car loads in AC, wheels spin and steer, suspension moves, and the car drives.

## Phase 2 - Exterior shell
- [ ] Blueprint-driven greybox at correct dimensions
- [ ] Body panels with correct shut lines and panel gaps: bonnet, wings, doors, tailgate, sills, bumpers
- [ ] Arches placed relative to the wheels, checked in-game
- [ ] Subdivision pass and surface review against photos

**Done when:** silhouette and proportions overlay cleanly on the reference photos from each of the main angles.

## Phase 3 - Exterior details
- [ ] Glass, A/B/C pillars, seals and trim
- [ ] Headlamps, indicators, tail lamps with working light nodes
- [ ] Grille, badges, GTE-specific trim, door handles, mirrors, wipers, aerial, fuel flap
- [ ] Wheels, tyres, brake discs/drums and calipers, visible suspension parts
- [ ] Underbody, exhaust, tow eye

**Done when:** the exterior reads as a GTE from every angle with no placeholder parts left.

## Phase 4 - Interior
- [ ] Dash, binnacle and gauges (working needles for speed, rpm, fuel, temperature)
- [ ] Steering wheel and column, pedals, gear lever and gaiter, handbrake
- [ ] Seats, door cards, rear seats, headlining, carpets, boot
- [ ] Driver model and animation nodes, mirrors, cockpit lighting

**Done when:** cockpit view matches reference photos and all instruments move correctly.

## Phase 5 - Engine bay
- [ ] Engine and ancillaries, intake, battery, fluid reservoirs, wiring and hoses
- [ ] Bonnet underside, bulkhead, inner wings

**Done when:** engine bay is complete with the bonnet open (if an animation is wanted) and plausible from photos.

## Phase 6 - Full physics (can be drafted any time once specs exist)
- [ ] `engine.ini` and `power.lut` from the sourced power and torque figures
- [ ] Gear ratios, final drive, differential, clutch
- [ ] Suspension geometry derived from the car's own dimensions, spring/damper rates from sourced data
- [ ] Tyres, brakes, aero, fuel consumption, AI data, setup ranges
- [ ] No ABS or traction control (not fitted to the real car)
- [ ] Validation: 0-100, top speed and a lap-style test against the targets in the spec sheet, measured with the telemetry logger

**Done when:** acceleration and top speed land in the sourced ranges and the car drives sensibly with no wheel/arch or ground-contact problems.

## Phase 7 - Materials and skin
- [ ] UVs, texture sets, correct KS shaders
- [ ] Metallic gun-metal grey paint skin, with clearcoat and flake tuned in-game
- [ ] Glass, rubber, plastics, chrome, fabrics, dirt and wear options
- [ ] Skin preview image and `ui` assets

**Done when:** the car looks right in daylight, at night and in the showroom.

## Phase 8 - Sound
- [ ] Decide source: real E16SE recordings (preferred) or a retuned stock bank as placeholder
- [ ] Build the bank with engine on/off, interior/exterior, intake, exhaust, transmission, tyres and body sounds
- [ ] `GUIDs.txt` and bank wired to the car

**Done when:** idle, rev range, lift-off and limiter all sound right inside and outside the car.

## Phase 9 - Polish and release
- [ ] LODs and collider
- [ ] Damage, dirt, lights and CSP extras
- [ ] UI data, badge, preview and specs shown in Content Manager
- [ ] AI line behaviour, setup screen sanity check
- [ ] Pack `data.acd` for release, final in-game test on the server
