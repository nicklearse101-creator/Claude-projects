# Setup Coach — CSP Lua app for Assetto Corsa

A Custom Shaders Patch (CSP) Lua app that reads live telemetry and writes
optimised car setup `.ini` files. Currently **v3.1.0** (see the v3.1.0
section first - it overrides older notes below where they disagree; v3.0.0's
calculated baseline was rolled back). Before that **v2.6.2** (Alpha Build
complete at v1.9.0; v2.0.0 = whole-lap evidence model; v2.1.0 = one
lever per regime, measured, with a per-car effectiveness ledger; v2.3.0 =
calculated targets where the physics gives one; v2.4.0 = branch passes —
the chain cycles back and is judged as a group; v2.5.0 = fixes from the
v2.4.0 logs and Nik's Sunbeam mod: the car's own travel range, long-track
sections, brake bias from grip, levers for cars without bars/dampers,
physics fingerprint; v2.5.1 = gear spinner names — the Build was carrying
each gear into the slot below; v2.5.2 = five bugs from the first week of
v2.5.1 Builds — RESET lost the car's travel range, damper bottoming
skipped the lap check, bias samples/override, ride-height calibration
noise, pressure ignored the live base; v2.6.0 = bottoming one fix at a
time — per-end chains packers > slow bump > fast bump > springs > ride
height — and ride height to 10 mm off the floor instead of the aero
peak, never into the aero stall; v2.6.1 = the fast-damper kerb softener
removed, slow rebound follows the springs, rebound damping floor 0.40 ->
0.50 - the car went bouncy after 3-4 Builds of stiffer springs; v2.6.2 =
the floor is the car's ground collider (colliders.ini boxes, rays cast
down from their bottom faces with car.transform + physics.raycastTrack),
checked live against car.rideHeight at the pickups before it is used;
FLOOR panel line, "collider floor" log line). The full version history
and reasoning for every decision below lives in `changelog.txt` next to
the app — this file is the short version to get a fresh session oriented
fast, not a replacement for reading that.

**Code hygiene (Nik, 2026-10-20):** the .lua carries no version history.
No "vX.Y.Z:" notes, no fixed-bug stories in comments - comments say what
the code does and why, briefly. Every change goes into `changelog.txt`
(newest first). The v3 plan is `docs/plans/2026-10-20-calculated-baseline.md`.

Install path on this machine: `D:\SteamLibrary\steamapps\common\assettocorsa`
App file: `...\assettocorsa\apps\lua\setupcoach\setupcoach.lua`
Test car has mostly been a Ferrari 458 GT2 at Spa.

## v3.1.0 — read this first (2026-11-16)

Nik: v3.0.0 "only camber and tyre pressures get written"; go back to the
lever chains "with less strict levers", add a normal / oversteer /
understeer choice, and fix dampers/suspension. v3.0.0's code is in git
(tag v3.0.0, commit 4065da9); 3.1.0 is the 2.6.2 code plus:

- **Relaxed levers**: `LEVER_FREEZE_AFTER` 3, `LEVER_EFFECT_DROP` 0.10,
  `BRANCH_MAX_PASSES` 4, no put-backs and a no-gain pass starts the next
  pass (`engine.branchPutBack` / `engine.branchStopOnNoGain`, both off;
  `test_branch_passes.lua` turns them on to keep that machinery tested).
  Lever history cleared once (`settings.leverRulesVersion` 2). This
  replaces the "put them back" and "1.25x" rules below.
- **Balance target** `settings.balanceMode` normal/oversteer/understeer,
  `BALANCE_MODES` (block between `BALANCE MODES BEGIN/END` markers - tests
  extract it): verdict ratios, slight-oversteer rate, brake-bias margin.
  Every push/snap verdict still goes through `balanceVerdict`.
- **Dampers**: the 0.54/1.20 m/s event counts no longer decide slow
  dampers. `dampHistAdd` puts dt-weighted wheel velocity into
  `dh{Slow,Fast}{Bump,Reb}{F,R}` (knee = `damperKnee`, the car's
  crossover clamped 0.02-0.15), banked per lap via `WINDOW_KEYS`;
  `engine:damperHistVerdict(e)` -> bumpSoft (< 44 % bump time) / rebSoft
  (> 56 %), 20 s minimum, lap-consistent; one click a Build, zeta ceilings
  1.25 / 1.80. Both ends (rear only without a rear handling verdict). The
  old counts still feed kerb/bottoming detection and the fast-damper panel.
  Why: the events tested kerb-strike speeds (10x the slow/fast knee) and
  counted bump and rebound differently (bump rate-limited, rebound per
  frame) - see changelog 3.1.0. Research notes:
  `D:/Claude/research_notes/AC springs and dampers setup/`.
- **Upvalues**: the Build function sits at 67 (Lua 5.4 `luac -l` count,
  incl. _ENV); 2.6.2 ran in game at 68. Add new Build inputs as engine
  methods/fields (`self:balanceModeNow()`, `self:damperHistVerdict()`),
  not new top-level locals.
- Inline comments are still the 2.6.2 ones with version notes - the
  hygiene clean-up is still owed.

## Hard constraints — settled, do not re-litigate

- **Live setup changes from an app are impossible.** The only route is
  `EXT_CONTROLLER` + a physics script editing the car's own data folder,
  which doesn't work on encrypted cars and isn't the same execution
  context as an app anyway. This app writes a `.ini` to the setups folder;
  the user loads it from the in-game Setup screen. Settled for good.
- ~~**Encrypted cars only expose a WHITELIST of tyres.ini fields**~~ —
  **RETRACTED in v1.9.5. There is no whitelist.** `ac.INIConfig:get`'s
  default argument sets its return type (SDK: "If not set, list of
  strings is returned"). `PRESSURE_IDEAL` was read with default `0` and
  worked; `DCAMBER_0/1`, `DY0`, `PRESSURE_STATIC` were read with default
  `nil`, got a string list, and `tonumber(list)` is nil — on every car,
  encrypted or not. Use `iniNum(ini, section, key)` for any numeric read
  that should be nil when absent. `DCAMBER_LOOKUP` is now a genuine
  fallback, not the primary route. See "v1.9.5" below.
- **Never pass `nil` as the default to `ini:get`.** Same class as the
  `ui.checkbox` return-value mistake: an SDK signature read as "obviously
  does X" and never checked. Use `iniNum` / `iniStr` (they also strip
  inline `;` comments, which Kunos files carry on the value line). As of
  v1.9.6 there are **no nil-default reads left** — `test_ini_default_type.lua`
  guards it.
- **Data priority is: live spinner (`ac.getSetupSpinners`) > live
  setup.ini > baked table > generic.** The user's rule: "live should
  always win, that's the whole point of the app." Baked tables
  (`DCAMBER_LOOKUP`, `AERO_LOOKUP`, `BAKED_SETUP_SCHEMA`) are fallbacks,
  not sources of truth — every one of them was built to work around the
  nil-default bug and would not exist otherwise.
- **setup.ini → stored-unit conversion is a rule, verified on 4 cars
  against the spinners** (see `readSetupItem`): SHOW_CLICKS=2 →
  0..(MAX−MIN)/STEP; SHOW_CLICKS=1 → floor(MIN/STEP)..floor(MAX/STEP);
  CAMBER_* → MIN/MAX ×10, STEP as-is (Kunos' own abarth500 comment:
  "step is in degrees / 10"). Don't add per-car overrides for these.
- **The unit of evidence is the lap, not the corner.** Agreed with the
  user (2026-09-21): *"the app is using telemetry to give a best overall
  setup based on full lap analysis… We don't want it to be creating
  builds just from a couple of corner's data."* Since v2.0.0: Build
  declines below `settings.buildMinLaps` clean laps (default 2) and
  `BUILD_MIN_CORNERS` (20); a successful Build **consumes** its window
  (counters, corner samples, pressure peaks → 0; bins fenced); every
  verdict must be agreed by ≥ half the window's clean laps individually
  (`regimeVerdict` / `lapSupport`). Don't add a writer that reads a raw
  counter without going through one of those two. The debug log's
  `evidence:` / `laps:` / `consistency:` / `lastBuildLoaded:` lines are
  how you verify it. **v2.5.0: on a track over 7.5 km the unit is a ~5 km
  SECTION of the lap** (Nordschleife: 4 a lap, by spline position) — the
  gate had been overridden on every Nordschleife Build. Everything that
  says "laps" works on units; ordinary tracks are unchanged.
- **CSP LUT sections are curve-checked before every write.**
  `ARB_F`/`ARB_R` (VALUE = 0-based LUT **row**; row 0 may be "detached")
  and `DAMPER_BUMP/REBOUND_*` (click = setup MIN + stored). Resolved per
  end / per corner by presence, vanilla first. The check lives in
  `writeTuned` (`lutArbMoveOk` / `lutDamperMoveOk`), so no write path can
  skip it; unreadable damper curves are **not** written blind. Damper event
  thresholds are **fixed at 0.54 / 1.20 m/s** for every car — the
  crossover is logged, never used to scale them. See v2.2.0.
- **WRITING a section ≠ CARRYING it.** The output file is a full copy of
  the template, so *every* section it contains is applied on load —
  including ones no writer touches. `MANAGED_SECTIONS` gates the
  **writers**; the live sync must still **carry** the unmanaged sections
  (gearing, tyre compound, TC, limiter, brake power) from the live
  spinners, or the Build silently reverts them to whatever stale
  `last.ini` held. Two hard rules: never **add** a section the template
  lacks (v1.8.0 invented `INTERNAL_GEAR_1`), and `CARRY_EXCLUDE` = FUEL
  only. See v2.1.1. **CSP's gear spinner names are NOT the file's**
  (v2.5.1): `ac.getSetupSpinners()` says `INTERNAL_GEAR_1..N` (forward
  gear n), AC's saved setups say `INTERNAL_GEAR_2..N+1` (0 = reverse,
  1 = neutral) — the SDK's "names match section names of setup INI files"
  is false for gears. `alignLiveGearNames` renames them right after the
  read, offset taken from the two name sets (no match → gears not
  carried). Never carry or compare gear spinners by raw name.
- **One lever per regime per Build, measured before the next.** The
  user (2026-09-22): *"if adjusting arb doesn't stop the problem in a few
  clicks, prioritise the next module that would have an effect and
  measure how one affects the other."* Since v2.1.0 every balance writer
  is a function in `levers` and `runLeverChains` moves the first
  available, non-frozen lever of `LEVER_CHAINS[regime-direction]`. The
  next Build judges it (`judgePendingLevers`: helped = verdict gone or
  rate −15 %); two no-effect moves freeze that lever **for the current
  pass** of that branch (`settings.leverLedger`, genuinely per car since
  v2.4.0 — before that a second car overwrote the first). Opposite low/high verdicts
  → aero lever first, low chain HELD. **Never add a balance writer that
  bypasses the chain.** ARB/aero split is **180 km/h** (user's number).
  Rake has a floor: "less rake" refuses at ≤ +3 mm measured rake.
  v2.5.0: low chains carry **springs** (roll-stiffness split) and **diff
  coast** (lift-off/entry only) after the ARB and dampers — on a car with
  no bars or dampers they're the real levers. Levers are chosen by what
  the car HAS, never by car id.
  **v2.6.0: bottoming is chained too.** Nik (2026-10-05): *"Bottoming -
  one at a time. Ride height least important. Stiffening springs too much
  loses grip so be cautious."* Each end that runs out of travel on most
  clean laps (`travelSignal`: max-travel hits through
  `travelHitsConsistent`) has a chain, `travelF-bottoming` /
  `travelR-bottoming`: packers > slow bump > fast bump > springs (+10 % a
  Build max) > ride height (+1 click). Same runner (`runBranch`), ledger,
  freeze, branch passes and put-backs as balance; run **before** the
  balance chains; no measured-response jumps. **Never add a bottoming
  writer outside the chain, and never stiffen rebound for bottoming** —
  too much rebound packs a car down over a run of bumps (the old
  "too-soft rebound creeps" reasoning was backwards). The damper loops
  leave an end with a travel verdict to its chain.
- **A branch is judged as a group, and moves that did nothing are put
  back.** The user (2026-09-24): *"Once the Build has been through the
  cycle of adjusting particular modules in a chain… it should cycle
  through to the beginning of that particular branch and monitor the
  group as a whole"* and **"put them back to starting value."** Since
  v2.4.0 each signal on each car **at each track** has a branch record
  (`settings.branchState`): pass baseline (rate, noise, Build) and every
  move with the sections it changed. A pass ends when the problem is gone
  or no lever can move; the group is judged baseline → now (same noise
  test); no-effect moves are **put back** through `writeTuned` (guards
  apply) unless the section changed since or its module is off; the next
  window checks the put-backs (restored if worse). Improved → next pass
  from the top with frozen levers given one more try; no gain or 3 passes
  → STOPPED (advice only; Settings "Reset lever history"). Never add a
  balance move that doesn't record into the branch.
- **Calculate where the physics gives a target; step only where it
  doesn't.** The user (2026-09-24): *"if the app knows a certain damper,
  arb, spring will be at or close to optimum at a specific adjustment,
  just put it straight there."* Since v2.3.0: springs (v2.6.0: to 95 %
  travel use, **at most +10 % a Build** — was 92 % / +30 %), ride height
  (v2.6.0: **the lowest end's median lap 10 mm off the floor**, both ends
  by the same mm, never into the aero stall, lowered only with no
  bottoming, < 90 % travel use and a reliable pit calibration at both ends;
  was "front to the aero-map peak + 2 mm" — Nik: *"it should lower until
  the car is at minimum available without the body of the car striking
  the floor"*), damping
  ratio floors, brake bias, camber (measured gain) go straight to target;
  ARB / rear dampers / wings jump only when an earlier window **measured**
  their per-click effect above the lap-to-lap noise (else 1–2 clicks).
  A section set by a calculated target is not re-moved by a lever in the
  same Build. **Advice stays click-level** so the driver can trim.
- **Brake bias: ONE calculated write per car, then advice only.** The
  user: *"moving brakes too far forward/backward has a big influence on
  understeer/oversteer/stability on entry. Make brake balance advise only
  after 1 build."* The first Build with enough hard-braking data decides
  it (write, already-there, or HELD by an entry guard) and marks the car
  done in `settings.biasBaselineCars`; capped ±3 %. Re-arm is a Settings
  button. Never add a repeating bias writer. **v2.5.0: the target is the
  front's share of the tyres' GRIP (tyres.ini DX_REF/FZ0/LS_EXPX, or
  DX0/DX1), not of the load** — AC tyres grip less per kilo as load rises;
  the load split put the Sunbeam at 77 % while its fronts locked first at
  69 % (grip model: 69 %). Handbrake use never counts as a brake lockup or
  a braking sample. **v2.5.2:** a braking sample needs all four wheels
  loaded; a car whose tyres have a grip model never falls back to load
  alone; the one-time decision is never made on an overridden lap gate.
- **Travel is measured against the car's own range** (v2.5.0):
  `PACKER_RANGE` from suspensions.ini, the live setup's adjustable
  packers (mm) per corner. Never a fixed number — the old `TRAVEL` key
  doesn't exist on any car, and the 0.12 m fallback hid GT-car bottoming
  and invented it on long-travel cars. Telemetry `suspensionTravel` counts
  from full droop (the Sunbeam reads 63 mm of 140 at rest). **v2.5.2:**
  anything `reset()` clears that `refreshTargets` reads from the car must
  be re-read — `self.carDataStale` forces it (RESET TELEMETRY had left 16
  Builds on 0.12 m).
- **A car id is not a physics version** (v2.5.0): Nik builds his own
  cars (the Sunbeam changed v1→v3 in a day). The physics fingerprint
  (`settings.physicsPrints`) resets everything learned about a car when
  its physics files change. Anything new that the app LEARNS per car must
  be added to `engine:forgetLearned`.
- **Records are per car + TRACK** (v2.5.0): last-Build record, pending
  lever moves, branch passes. Only the lever ledger and the calibrations
  are per car.
- **Gearing is advice only — Build never writes it**, even now that the
  exact final-drive option is calculated.
- **Slight oversteer in a normal race car is not a fault.** The user's
  rule (2026-09-19), verbatim: *"slight oversteer in a normal race car
  isnt a bad thing, that should be noted."* A car that rotates a little
  is faster and nicer to drive than one that pushes; the app must not
  tune it out. Every push-vs-snap decision goes through **one** function,
  `balanceVerdict` — `tight` (push > 1.25× snap), `loose` (snap > 1.25×
  push AND, at low speed, > `SLIGHT_OVERSTEER_PER_100` = 25 snap events
  per 100 corners), or nil = left alone with the reason logged
  (`slight` / `mixed`). Understeer has no rate floor (it's slow at any
  rate). Don't add a new push-vs-snap rule anywhere without going
  through it. The 25/100 bar is a first calibration — tune it from the
  `balance verdicts:` debug line, not from theory.
- **Plain Lua file writes cannot create a missing folder.**
- **Not every documented CSP field exists in app context on every build** —
  wrap anything uncertain in `pcall`. A per-wheel `.abs` field once threw a
  hard error that silently killed the rest of the frame's update loop.

## Confirmed via CSP's own shipped Lua type definitions

Verified directly from `extension/internal/lua-sdk` (the actual files CSP
ships, not forum posts) — checked across three separate copies, all
agreeing:

- `ac.DataLUT11.carData(carIndex, fileName)` — works in **app context**,
  not just physics scripts. This was an open question for most of the
  project; now settled.
- `ac.getTrackSectorName(trackProgress)` — exact signature confirmed.
- `car.wheels[i].angularSpeed`, `.surfaceValidTrack` (bool),
  `.surfaceSectionIndex` — all real, confirmed fields on `ac.StateWheel`.
- `car.clutch`: **1 means pedal fully DEPRESSED, i.e. clutch DISENGAGED** —
  this is the reading for the app-context struct (`ac.StateWheel`'s
  sibling car struct, lua-sdk line ~4064) and what the gearing module's
  clutch gate assumes (`clutch < 0.05` = engaged). Worth knowing CSP's own
  SDK is not internally consistent here: a *different* struct used for
  control input/override (lua-sdk line ~16809) documents the same field
  name with the opposite sense ("1 for fully depressed... clutch fully
  engaged"). Likely not a contradiction in practice so much as two
  different things sharing a name — one is a physical pedal-position
  readout, the other a logical engagement override — but verify against
  the actual struct you're reading, not the field name alone. Separately,
  this app's user has their clutch axis inverted in Content Manager's
  control bindings (needed for it to behave correctly in-game), which is
  the likely real explanation for why the earlier Python reference's
  same-named field implied the opposite polarity: it may have been
  reading a raw/uninverted hardware value rather than the game-logical
  one `car.clutch` reports. Don't trust naming similarity across
  different AC APIs or across raw-vs-logical input layers — verify
  directly.
- `car.gear`: integer, 0 = neutral, -1 = reverse, doesn't pass through 0 on
  sequential shifts (use `engagedGear` if you need the version that does).

Genuinely still unconfirmed: `angularSpeed`'s exact unit (assumed rad/s in
the gearing module, sanity-bounded rather than trusted blindly — check
`debug_log.txt`'s `gearRatios` line on the next real session).

## Real bugs already found — don't reintroduce this class of mistake

- **Lua table keys must be valid identifiers.** A car ID with a hyphen
  (`p4-5_2011`, the Ferrari P4/5) crashed the *entire script* at load time
  when used as a bare table key — Lua read `p4`, then choked on `-5_2011`
  as a malformed number. Fixed by quoting every key in the DCAMBER lookup
  table (`['p4-5_2011']=...`). If you ever add more entries, keep them
  quoted.
- **Lua locals aren't hoisted.** Caught twice: a helper function
  (`carLikelyHasRealAero`) was defined after its first use in the same
  block, and a gearing calculation referenced `rpm`, which only exists in
  the separate per-frame `update` function, not in `buildAdvice` where the
  code actually lived. Check function/scope boundaries directly, don't
  assume a variable used elsewhere in the file is in scope.
- **Damper direction was backwards twice** before landing correctly: a
  side crossing its velocity threshold *more* often is the *softer* side
  (less resistance, reaches that speed more easily) — the fix is to
  stiffen the dominant side or soften the recessive one, not the reverse.
  Verified against the real "damper velocity histogram" technique, not
  just derived from first principles.
- **Fast dampers**: AC's own in-game hint text is explicit — lower values
  absorb more energy over kerbs; very stiff means the damper barely moves
  and the car gets launched. Direction depends on whether bottoming is
  also happening (stiffen) or not (soften), never a blanket "always
  stiffen."
- **ARB should never only soften.** Balance depends on the front:rear
  ratio, so stiffening the *other* end achieves the same balance shift —
  matters once repeated Build presses would otherwise walk one bar to its
  floor with nothing counteracting it.
- **Old camber logic had a real bug**: after checking thermal spread, it
  fell through to "static camber more negative than -1.15° is too much" —
  which fires on every GT car as a matter of course (they run -2° to
  -3.5°), so it permanently read "reduce neg camber" regardless of what
  the tyres were doing. Now uses either the DCAMBER peak-grip calculation
  or a thermal-spread fallback, never a fixed universal number.

## Physics findings, with sourcing (don't re-derive from scratch)

- **Rake** (front ride height lower relative to rear): checked against
  nine independent real-world sources, unanimous — more rake reduces
  understeer, less rake increases it. High confidence, implemented.
- **Front rebound softening for turn-in understeer**: investigated,
  *not* implemented. Two credible damper-manufacturer sources (Koni,
  Penske) gave genuinely different answers depending on which phase of
  the corner they were describing. Left as a known idea, not built on
  one source's word.
- **AC's damper model is a simplified piecewise-linear approximation**,
  confirmed directly from Kunos' own developer blog (base AC uses "4-5
  linear values for bump, rebound, fast bump and rebound and threshold
  times" — ACC's later "fully blown damper graphs" are a different,
  newer model). This doesn't undermine the balance-based damper logic —
  if anything a linear model behaves *more* predictably against it than
  a real multi-stage valve would.
- **Aero curves are not always monotonic** — a McLaren F1 GTR 96's front
  splitter peaks at 3° and is stalled by 8°; some open-wheel ground-effect
  cars flip from downforce to lift past a certain ride height. The AERO
  module reads each car's own curve at runtime (`ac.DataLUT11`) where
  possible, with a car-class-based caveat as fallback.
- **DCAMBER_LUT overrides the DCAMBER_0/1 quadratic** on cars that define
  it, so the peak-camber calculation from those coefficients is an
  approximation, not exact, on such cars.

## CSP extended suspension: LUT dampers, LUT ARBs, motion ratios (2026-09-24)

Researched in the Escort Mk2 physics-rework session (a separate project,
not a Setup Coach change) by decrypting 71 installed cars' `data.acd` and
reading CSP's own docs (`cup.acstuff.club/docs/csp/cars/suspension`).
**This is the cause of the `DAMPER_*` "alternate naming" gap logged as
known-deferred in the v1.3.1 section-name scan.** It isn't a naming
style. It's a different damper model whose sliders hold click indices,
not N·s/m. No app code was changed. Everything below is findings plus
suggested directions.

**How it's switched on (CSP docs and every real file agree).**
- `suspensions.ini [_EXTENSION] DAMPER_LUTS=1` (docs: "currently
  required") plus a `dampers.ini` with `[HEADER] ENABLE=1`. `gt4_audi_r8`
  ships a complete, enabled `dampers.ini` but has `DAMPER_LUTS=0` and no
  `DAMPER_*` sliders. The flag is the switch; the file alone does nothing.
- **DWB2 axles only** (`USE_DWB2=1`, `TYPE=DWB`). The docs name DWB2 as
  the supported type. All 6 strut-front cars with the feature
  (gt4_bmw_m4, gt4_bmw_m4_g82, gt4_camaro, gt4_ford_mustang,
  gt4_panoz_avezzano, gt4_toyota_supra) keep linear front dampers, even
  where `dampers.ini` lists front LUTs. On some of them those front LUT
  files aren't in the package at all.

**dampers.ini format.** `[FRONT]`/`[REAR]` keys `BUMP_SLOW_<n>=x.lut` and
`REBOUND_SLOW_<n>=x.lut`. Each LUT is `damper speed (m/s) | force (N)`.
`<n>` is the setup click. Clicks without their own LUT are linearly
interpolated between neighbours (e.g. LUTs at 0/10/20/30/40, slider
0..24). The docs also allow `BUMP_FAST_<n>`/`REBOUND_FAST_<n>`, but none
of the 15 real cars use them: fast damping stays the linear
`DAMP_FAST_*` in suspensions.ini. On LUT axles, authors set
`DAMP_BUMP=DAMP_REBOUND=0`. The docs also say "motion ratio will be
applied to dampers", so LUT force is at the damper, not the wheel.

**setup.ini and saved-setup semantics (verified on real files).**
- Sections are `DAMPER_BUMP_<LF|RF|LR|RR>` / `DAMPER_REBOUND_<...>`, with
  integer `MIN`/`MAX`, `STEP=1`, `SHOW_CLICKS=2`, and an explicit
  `DEFAULT=`. The default has to be explicit because the linear value in
  suspensions.ini is 0, so there's nothing to derive it from.
- Saved `VALUE` is the click. In a real `last.ini`, gt4_alpine_a110 has
  `DAMPER_BUMP_LF VALUE=12` (DEFAULT 12). sv8_camaro_v2 has bump
  `MIN=1 DEFAULT=6`, and its saved setup reads `VALUE=5` on all four
  corners, while rebound (`MIN=0 DEFAULT=9`) saved 9. That fits
  VALUE = steps from MIN, the same as index-based vanilla sliders. It's
  one data point, so confirm it before relying on it.
- **Mixed conventions in one car.** On strut-front cars, the front uses
  vanilla `DAMP_BUMP_LF` (an N·s/m slider, 10600..25000/1200) and the rear
  uses `DAMPER_BUMP_LR` (clicks). gt4_toyota_supra's real saved setup
  contains both `DAMP_BUMP_LF VALUE=9` and `DAMPER_BUMP_LR VALUE=13`.
  Writers must resolve the section name per corner, not per car.
- `MAX` can stop short of the highest LUT (slider 0..24/0..25 over LUTs
  up to 40), which leaves the top curves unreachable.
- `DAMPER_FAST_*` setup sections (in the v1.3.1 gap note) weren't seen on
  any of these 15 cars. They're presumably the counterpart of the
  documented `BUMP_FAST_<n>` LUTs. That's unverified.

**What one click does (real curves).** The gt4_* pack (14 of the 15 cars)
shares the same LUT files, in two variants (a 0-40 click set and a 0-60
click set). Click 0 is roughly linear: about 4,000 N·s/m in bump, and
4,000 to 6,500 in rebound. The top click is strongly
digressive: about 45,000-59,000 N·s/m below 0.025 m/s, flattening to
about 7,000-11,000 N·s/m between 0.05 and 0.25 m/s. So clicks mostly move
**low-speed** force (body control), much less high-speed force (kerbs).
Don't treat "+1 click" as a fixed N·s/m step.

**Real curve defects to guard against (same lesson as non-monotonic aero).**
- The top-click LUTs in that library drop force at the far end, e.g.
  4500 N @ 0.3 m/s to 3000 N @ 1.0 m/s (a negative slope). With fast
  thresholds at 0.3, it's unknown whether CSP ever reaches that region.
- sv8_camaro_v2's `slow_rrebound4.lut` (rear rebound, top click 18) has
  the force values copied into the speed column (`2686.7|2686.7` ...).
  At real damper speeds it therefore reads almost zero force: **max rear
  rebound on that car is close to no rebound damping at all.** The front
  equivalent is fine. Pushing "stiffen rear rebound" to the max would do
  the opposite of what's intended. Sanity-check any damper LUT (speed
  values roughly 0-2 m/s, force rising) before trusting click direction.

**readDamperCrossover on these cars.** On LUT axles, the gt4_* cars set
`DAMP_FAST_BUMPTHRESHOLD` to 0.30-0.40 m/s. That's a device to let the LUT
cover the slow range, not a real valve knee. `valid()` accepts anything
up to 0.5, so thr = 0.30 gives velModerate/velSharp = clamp(5.4) /
clamp(12) = **1.00 / 2.20, pinned at the upper clamps**. That's about 1.85x
the Ferrari's 0.54/1.20, so these cars would log far fewer damper events.
The v1.9.9 comment "every other real value seen is 0.01..0.11" no longer
holds. Suggested: when `DAMPER_LUTS=1` on that axle, don't take the
threshold at face value (fall back to 0.030, or derive a knee from the
LUT's slope change). Not implemented; that's this project's decision.

**Extended ARBs (also index sliders).** `[ARB] EXTEND=1` (plus
`FRONT_MOTION_RATIO`/`REAR_MOTION_RATIO`). The setup sections are
`ARB_F`/`ARB_R`, each with `LUT=file.lut` (index | stiffness) and **no
MIN/MAX/STEP**. Example: gt4_bmw_m4 `1|42600 2|51400 3|63800`. In a real
saved setup, gt4_alpine_a110 has `ARB_F VALUE=3`. 9 of the 71 cars use
this, including a TCR (fw_cupra_tcr_2024), and gt4_audi_r8 mixes a LUT
`ARB_F` with a vanilla rear. The ARB writer only probes
`ARB_FRONT`/`ARB_REAR`, so it **silently skips these cars' ARBs**. Their
range is the LUT's own first and last index.

**Other DWB2 keys seen.** `MOTION_RATIO=file.lut` per axle (deflection |
ratio; gt4_bmw_m4's rear is a constant 0.8). On those axles, SPRING_RATE
is probably the spring rate, not the wheel rate that vanilla files state.
Standard physics gives wheel rate ≈ k·MR², but the docs only say MR is
"applied to dampers". `BUMP_STOP_LUT=file.lut` (deflection | force, must
start with 0|0; seen on ltkaeri_honda_s2000_gt1_amuse). There's also a
new rear `TYPE=ML` on fw_cupra_tcr_2024.

**Untested in app context:** whether `ac.INIConfig.carData` exposes
`dampers.ini` or `[_EXTENSION]` on encrypted cars (the whitelist).
`DAMPER_*` / `ARB_F` sections in the live setup work as a detector either
way.

**Which installed cars.** `DAMPER_LUTS=1`: gt4_alpine_a110,
gt4_aston_martin_vantage, gt4_bmw_m4, gt4_bmw_m4_g82, gt4_camaro,
gt4_ford_mustang, gt4_ginetta_g55, gt4_mclaren_570s, gt4_mercedes_amg,
gt4_mercedes_amg_evo, gt4_panoz_avezzano, gt4_saleen_s1, gt4_sin_r1,
gt4_toyota_supra, sv8_camaro_v2. `USE_DWB2=1` without LUT dampers:
corvette_z06_gt3_2024, lamborghini_huracan_evo2_gt3,
porsche_992_gt3_r_2023, ks_ferrari_296_gt3_2023, ks_bmw_m4_gt3_2022,
mclaren_720s_gt3_evo, acf_aston_martin_vantage_gt3_evo,
rss_gtm_mercer_v8, ltkaeri_honda_s2000_gt1_amuse. The main test cars
(ferrari_458_gt2, lotus_exos_125_s1, cup_dacia_sandero,
ks_abarth500_assetto_corse) are all vanilla, which is why this never
surfaced in testing.

**Verified from the Setup Coach side (2026-09-24, against v2.1.1 code).
All three gaps below were then FIXED in v2.2.0 at the user's request —
see the v2.2.0 section; this block is kept as the evidence.**
- *Section gap, sized on the user's own saved setups* (649 cars under
  `Documents\Assetto Corsa\setups`, not the 71-car decrypt sample):
  **19 cars use `ARB_F`/`ARB_R`**, so `SETUP_PROBE.arb` (only
  `ARB_FRONT`/`ARB_REAR`) finds nothing and the ARB lever — first in both
  low-speed chains — reports "no ARB section on this car". Includes the
  whole `fr_*_btcc` grid (7 cars), `fw_audi_rs3/cupra/elantra_tcr_2024`,
  `cf_ferrari_296_gt3`, `ferrari_488_gt3_acc_sprint`, `lexus_rcf_gt3_acc`,
  `gt4_alpine_a110`, `gt4_aston_martin_vantage`, `gt4_audi_r8`.
  **11 cars use `DAMPER_BUMP/REBOUND_*`**, so the slow damper writers
  (front histogram and the rear-dampers lever) find nothing: `sv8_*_v2`
  (3), several `gt4_*`, `bk_audi_r8_lms_2019`,
  `cf_bentley_continental_gt3_2018`. Most are mixed (25 of 28 cars also
  carry vanilla sections — e.g. `fr_bmw_btcc`: `ARB_F`/`ARB_R` but vanilla
  `DAMP_BUMP_*`), confirming "resolve per corner / per section, not per
  car". v2.1.0's chain means none of this is silent any more; it is still
  a real loss of the primary balance lever on those cars.
- *readDamperCrossover — correction to the note above.* On `gt4_bmw_m4`
  (front vanilla `0.060`, rear LUT `0.3`) the v2.1.0 typo guard (axles
  > 3× apart → take the smaller) already picks **0.060**, so the LUT
  axle's 0.3 does not reach the thresholds there. The wider problem is not
  LUT-specific: with the 18×/40× anchor, **any crossover ≥ 0.056 m/s pins
  both thresholds at the clamps (1.00 / 2.20)**. Run through the real
  function: `gt4_bmw_m4` 0.060 → 1.00/2.20; `sv8_camaro_v2` 0.093 →
  1.00/2.20; **`ks_lamborghini_huracan_gt3` 0.060/0.060 → 1.00/2.20**;
  `ferrari_458_gt2` 0.030 → 0.54/1.20. That is why the Huracan windows log
  2–5 slow damper events against dozens on the Ferrari, and why the
  rear-dampers lever is starved on it. Fix belongs to the anchor/clamps,
  not just to LUT axles.
- *`sv8_camaro_v2` `slow_rrebound4.lut` (rear rebound, click 18) confirmed
  broken*: rows are `2686.72|2686.72 …` — first real point at 2,686 m/s,
  so ≈ 0 N at real shaft speeds; clicks 12→18 interpolate *down* from a
  sane curve (`slow_rrebound3.lut`: 0.025 m/s → 939 N) to that. Front
  `slow_frebound4.lut` has the same forces with correct speeds. Any future
  LUT-damper writer must sanity-check monotonicity before trusting "+1
  click = stiffer".

### Vanilla damper model: reference numbers (same research)

- Two-stage linear: the slow coefficient applies below
  `DAMP_FAST_*THRESHOLD` and the fast one above it. None of the 56
  scanned cars without `DAMPER_LUTS` has a damper curve key, which agrees
  with the Kunos-blog finding above.
- Per-corner maths: sprung mass = TOTALMASS × axle share / 2 − HUB_MASS;
  ride frequency = √(k/m) / 2π; ζ = c / (2√(k·m)). In vanilla,
  SPRING_RATE is the wheel rate (Kunos' own file comment says so).
- Real vanilla files (frequency F/R in Hz; ζ slow bump/rebound for
  front · rear; ARB F/R in N·m):

| car | Hz F/R | ζ F bump/reb · R bump/reb | ARB F/R |
|---|---|---|---|
| bmw_m3_e30_dtm | 4.91/3.80 | 0.54/0.74 · 0.60/1.00 | 44000/14400 |
| btcc_1992_bmw_318i | 4.21/3.80 | 1.00/1.00 · 0.63/1.06 | 44000/14400 |
| alfa_romeo_75_gruppo_a_s1 | 3.66/3.29 | 0.81/0.81 · 0.97/1.46 | 31000/9400 |
| ford_sierra_cosworth_rs500_dtm_90s | 3.14/3.25 | 0.87/0.87 · 0.96/1.44 | 20000/8400 |
| ks_mercedes_190_evo2 | 2.81/3.23 | 1.17/1.17 · 1.19/1.79 | 44000/14400 |
| amr_v8_vantage_gt4 | 3.04/3.01 | 0.62/0.74 · 0.63/0.79 | 50000/15000 |
| ks_toyota_gt86 (road) | 1.33/1.41 | 0.41/1.13 · 0.77/1.06 | 39000/5000 |
| ford_escort_mk2_tarmac (mod) | 1.71/2.42 | 0.18/0.76 · 0.26/0.68 | 12500/0 |

- Patterns: on every period race car, the rebound coefficient is at least
  the bump coefficient (1.0-1.7x). On RWD touring cars, rear ARB is about
  30-40 % of front. Race-car front ride frequency is 3-5 Hz. Mod cars can
  sit far outside this: the Escort tarmac's front bump ζ is 0.18 and its
  rebound/bump ratio is 4.3x. Don't assume a mod's baseline is sane.
- Bump-stop domination (a hypothesis from one car, not validated by
  telemetry): when PACKER_RANGE is small and BUMP_STOP_RATE is high, the
  car rides the stops and damper changes feel like they do nothing. The
  Escort rework showed this pattern: 80-90 mm of travel, 100,000 N/m
  stops, and a driver report that the dampers were "almost as if they're
  not there". It hasn't been confirmed by a fix. A possible signature:
  suspension travel pinned at the limit while damper advice keeps firing
  means fix travel first.

## Data assets baked into the Lua file

- **DCAMBER fallback lookup**: ~102 cars' real DCAMBER_0/1 coefficients,
  86 from a community reference table (`base.json`, sourced from the
  "Camber Extravaganza" app's data) plus 8 more extracted directly from
  real `data.acd` files during this project. A handful of those 8 are
  keyed under guessed slugs, not confirmed real installed folder IDs —
  harmless if unmatched (falls through to the thermal method), not yet
  verified correct.
- **Pressure, thermal, and class-based fallback tables** for cars whose
  `tyres.ini` isn't fully readable.

## Not yet built (known, deliberately deferred)

- AWD differential (the Evo VI's centre diff is a controller-chain
  architecture, not the simple `POWER`/`COAST`/`PRELOAD` fields — RWD/FWD
  only for now).
- Gearing writer (no confirmed way to write `.rto` ratio files from app
  context) — currently read-only prediction, not a Build-time write.
- Wet-weather constant profile.
- Session A/B history beyond the existing single Grip Trend baseline.
- **Rally mode** (Nik, 2026-10-05: "Add rally mode to the to-do list").
  Why: on gravel / rallycross-style driving the app reads deliberate
  sliding as a fault — the Sunbeam logged 100–185 snaps per 100 corners at
  Knockhill, Blackwood and england_rally_01 (held slides caught only part
  of it), the verdict went "loose", and the levers softened the rear ARB /
  rear dampers to stop slides the driver wanted. Diff power/preload also
  flip-flopped Build to Build there. Not designed yet — open questions: how
  it's switched on (Settings toggle, per car, or by track surface), what
  counts as a fault when sliding is the technique (snap rate vs a much
  higher bar, or exit traction / wheelspin instead), and which modules
  behave differently (balance levers, diff, pressures on loose surfaces).
- **Track contacts** (v2.6.0 logs them only): whether `collidedWith == 0`
  body contacts with their car-space position can tell a floor strike
  from a wall hit, and then feed the floor step. Raising ride height for
  the aero stall (an end already under its GH_CL peak) is also logged
  only.

## Cross-class coverage (audited v1.2.1, prompted by "will this work on
cars other than GT3?")

The overwhelming majority of this app is class-agnostic by construction -
ARB/springs/dampers×2/ride height/toe/brake bias/camber/mechanical grip/
tyres/fuel/performance/weather/packer range are all generic threshold +
corner-probe logic with no class branching at all. The only real
per-class behaviour:
- **DIFFERENTIAL is explicitly RWD/FWD only** - AWD gets an honest "not
  analysed by this app" rather than wrong advice (confirmed: a real AWD
  car's data has no DIFFERENTIAL section at all, just an EXT_CONTROLLER
  chain). Same exclusion applies to the live gear-ratio measurement.
- `carLikelyHasRealAero`'s class-tag list and `classIdeals`'s pressure
  matrix are advisory/fallback only - they widen a caveat or supply a
  last-resort number, never gate whether a module runs. An unlisted class
  just gets the plainer default, not an error.
- DCAMBER_LOOKUP already spans road cars, classic rally, LMP, formula and
  GT, not just GT3 - confirmed from the table contents, not assumed.

**A real bug was found and fixed this way**: v1.2.0's aero additions were
verified only against real GT3 cars. Checking a real kart (`gokart100`)
during this audit found the fixed WING_1=front/WING_2=rear convention
(inherited from SETUP_PROBE, predating v1.2.0) doesn't hold there - its
WING_1/WING_2 are NAMEd MID_L/MID_R (driver-lean side wings), with the
real FRONT-named wing at WING_3. v1.2.1 resolves each wing's role from its
NAME field first, falling back to position only when NAME is blank -
never when NAME says something else. Confirmed fixed by re-tracing against
the same kart file directly. Honest residual gap: a car with an unusual
wing order AND a blank NAME would still fall through to the positional
guess - narrower than before, not eliminated, since there's no way to ID a
wing's role with neither a name nor a LUT-shape signal to go on.

## v2.6.0 — bottoming one fix at a time, ride height to the floor

**Prompt (Nik, 2026-10-05, after the v2.5.2 review):** *"Bottoming - one
at a time. Ride height least important. Stiffening springs too much loses
grip so be cautious. Leave override as is. Add rally mode to the to do
list. App shouldn't just lower a car to aero peak- it should lower until
the car is at minimum available without the body of the car striking the
floor"*. Answers: order packers → slow bump → fast bump → springs → ride
height; springs max +10 %/Build, aim 95 %; clearance 10 mm; stop at the
aero stall; extend the existing chains (approach A). Then "Plan and
build". Spec / plan: `docs/superpowers/specs|plans/2026-10-05-bottoming-
chains-floor-clearance*` in the repo.

**Bottoming chains.** `travelSignal(self, 'F'|'R', th)` → verdict
`'bottoming'` (max-travel hits through `travelHitsConsistent`), hits,
rate per 100 corners, laps agreeing/considered. `LEVER_CHAINS`
`travelF-bottoming` / `travelR-bottoming` = `packersX > bumpX >
fastBumpX > springRateX > rideRaiseX`, built per Build by one factory
`travelLeversFor(e)` (presence-based; every section it moves is
`calc.touched = 'the bottoming chain'`). `springRate*` =
`cautiousSpringTarget(k, use)` = k × min(use / 0.95, 1.10), rounded up
onto the grid but never past +10 % (rounded down when the cap binds), one
click minimum; sets `springsMovedForTravel`. `rideRaise*` = +1 click via
`rideDir` (hoisted above the levers), refused when `calc.rideMoved`. The
runner's loop is `runBranch(key, verdict, label, prefix)`; `runTravel(e)`
runs front then rear before `run('high')` / `run('low')`, HELD when
`calc.floorRaised`; `verdictOf` / `rateOf` / `seOf` serve both kinds of
key; the judge reads travel keys through `travelSignal` and
`lapRateStats('travelX', 'hits')`. Retired: the max-travel spring
writer, the packer writer (raw `bottoming` count), slow dampers
stiffening bump AND rebound, fast dampers stiffened for bottoming, the
bottoming ride raise, and the Build-wide `bottomingActive` gate.

**Floor clearance.** Per clean lap and end, a 1 mm histogram of
`car.rideHeight[0/1]` (on track, > 30 km/h); `floorHistClearance` = the
height above all but the lowest 0.5 % (nil under 200 samples or a median
under 10 mm) → `bin.clrF/clrR`. Window counters `floorHitsF/R` (≤ 1 mm,
0.5 s). Fast corners: `ac.getCarPhysics().wings[aeroWingIndex.front|
diffuser].groundHeight` sums (pcall). Track contacts (`collidedWith == 0`,
`collisionDepth > 0`, `collisionPosition` car space per the SDK) —
**logged only**. `floorClearanceStep(a)` (pure) → raise by the deficit
under 10 mm; lower by the surplus, limited by the stall room (fast-corner
ground height − GH_CL peak, splitter and diffuser; front falls back to
`hsRhF`), only with no lap-consistent bottoming, both median travel uses
< 90 % and reliable calibration both ends; else hold. `floorClicks`: same
mm both ends, down rounded down and capped at what both ends can do in 3
clicks, up rounded up, 1 click where the calibration isn't reliable.
Sets `calc.rideMoved`, `calc.floorRaised` (raise). Replaces the v2.3.0
aero-peak block; `RIDE_PEAK_MARGIN_MM` gone. The constants the panel
names (`SPRING_*`, `FLOOR_TARGET_MM`, `FLOOR_LOWER_TRAVEL_MAX`) are
declared above `buildAdvice` — a top-level local is invisible above its
declaration (caught by a test before shipping).

**Debug:** `floor (v2.6.0): lowest point on the median lap F x / R y mm
over n laps (target 10) · contacts … per lap · stall room … · calibration
… -> LOWER/RAISE/HOLD …`, `track contacts (v2.6.0, logged only): …`,
`Bottoming front|rear: lever X moved …; max-travel hits Y per 100 corners
banked …`, travel branches in `branches`, travel levers in `levers`,
`ride height to the floor: …` in `calculated targets`.

`test_v260_bottoming_floor.lua` (135) — travel signal + judging, cautious
springs, chain/module tables, the ten levers on a Sunbeam-v6-like and a
GT3-like car, floor histogram + banking, `floorClearanceStep` /
`floorClicks` cases, log/panel guards, and (section 6) the floor step's
write block and the new panel lines run verbatim — the smoke test never
runs Build or the panel. `test_branch_passes.lua` (127) drives travel
chains Build by Build through the real runner. Suite: 23 files, 1169
counted checks, all green. **Untested in-game** — first thing
to read on a real night: the `floor` line (does `car.rideHeight` give
sane clearances, does `groundHeight` read on the Huracan/Evo2), and the
`track contacts` line.

## v2.5.2 — five bugs from the first week of v2.5.1 Builds

**Prompt.** "continue" (2026-10-05) after a week of driving: 57 Builds,
29 Sep – 4 Oct — Sunbeam (live, `_backup_v6`, `_cheat_plus10`) at the
Nürburgring GP, Bathurst, Brands Hatch, Knockhill, Blackwood,
england_rally_01; `lamborghini_huracan_gt3_evo2` and
`fsr_audi_lms_evo_ii_gt3` at Imola. Reviewed from a per-Build summary.
Worked: the physics fingerprint (both Sunbeam changes caught — 30 Sep
car/suspensions/setup/tyres, 4 Oct tyres), held slides, summaries, range
limits, branch passes. The v2.5.1 gear fix is still unexercised: no Build
since was on a car with per-gear spinners.

1. **RESET TELEMETRY wiped car data** — `reset()` puts travelRef back to
   0.12 m / "not read yet" (and the gear-physics reads), but
   `refreshTargets` early-returns for the same car + compound, so only a
   ≥ 2 s pit stop re-read it: 16 Builds on 120 mm. Fix:
   `self.carDataStale = true` in `reset()`; `refreshTargets` re-reads when
   stale. NB the button also resets `buildsThisSession`, so the header's
   "#N since app load" means "since app load or RESET" (nearly every
   Build said #1).
2. **Slow-damper "bottoming needs support" bypassed lapSupport** (raw
   `springsHits > th`) → `travelHitsConsistent(self, key, count, th)`.
3. **Brake bias**: a braking sample needs all four wheels loaded (an
   airborne wheel had a nil grip force → load count > grip count →
   load-only fallback); a tyre with a grip model never falls back to load
   (`biasTarget` returns nil and counts the grip samples); the one-time
   decision is skipped (advice line) when `gateOverridden`.
4. **Ride-height calibration**: points carry the axle's spring setting (a
   4th field; `parsePointStore` reads 2–4); pairs need equal springs;
   `rideCalSlope` returns `slope, pairs, reliable`, reliable = ≥
   `RIDE_CAL_MIN_PAIRS` (2) pairs agreeing on the sign and |median| ≥
   `RIDE_CAL_MIN_SLOPE` (0.3 mm/click). `rideDir` and the aero front target
   use `reliable`; log "x mm/click from n same-spring pairs, reliable / not
   reliable yet".
5. **Pressure base** = `getCurVal(parsed, section)`, template or live — it
   was `usedBase and …`, so a car with no template file ignored the live
   pressure (Evo2: live 18 psi → wrote 28.5).

Also: `physicsFirstSeen` sticky per car until the commit clears it; diff
power "to back up the preload increase" only when the preload changed.

**Found, not changed — Nik's call** (report of 2026-10-05): the bottoming
response stacks (calculated springs + slow dampers + fast dampers + ride
height in one Build, every Build — **fixed in v2.6.0**); the front damper histogram ratchets
front bump on GT3s (+2 clicks a Build to near max, then rebound −2); the
override button runs a full-strength Build on 0–15 corners (25 of 57
Builds); rally driving reads 100–185 snaps/100 corners → "loose" levers
for deliberate sliding; diff power/preload alternate Build to Build on the
Sunbeam; the Evo2 aero target (its `height_front_CL.lut` really peaks at
20 mm, but whether `car.rideHeight` matches the LUT's ground-height
reference is unverified — `ac.getCarPhysics().wings[i].groundHeight`
would settle it).

`test_v252_log_review_fixes.lua` (53; each fix reverted on its own in a
scratch copy turns its checks red). `test_calculated_targets.lua` gained
the two constants + a reliability check. Suite: 22 files, 1008 counted
checks, all green. **Untested in-game.**

## v2.5.1 — Build was carrying the gears into the wrong slots

**Report (Nik, 2026-09-29, first test of v2.5.0):** *"check silverstone,
huracan gt3. build button messed up the gears. it's not even supposed to
touch them."* Build 18:35:15 (gate overridden, 1 clean lap).

**Evidence.** The written `SetupCoach_Optimized.ini` had 1st 2.1579, 3rd
1.5217, 4th 1.3076 and **5th 0.8857 = 6th's ratio**; that Build's own log
had physics at car load 5th 1.031 / 6th 0.886 and the driven final 4.167.
Its `liveSetup` line: `template was stale on INTERNAL_GEAR_6 2->7,
FINAL_RATIO 3->4, INTERNAL_GEAR_2 1->3, INTERNAL_GEAR_4 3->4`, **10**
carried, **2** left out. CSP names the gear spinners `INTERNAL_GEAR_1..6`
(the car's setup.ini `[GEAR_n]`); AC saves `INTERNAL_GEAR_2..7`. No saved
setup of the 1500+ on this PC has an `INTERNAL_GEAR_1` — v1.8.0's
"invented" section was CSP's 1st gear all along. Shifted back one slot the
live values are the stock 2nd–6th (drivetrain.ini) with Nik's 4.1666 final,
and only that naming makes the counts add up (the car's non-gear unmanaged
items: FINAL_RATIO, ENGINE_LIMITER, BRAKE_POWER_MULT, ABS, TC → 5 + 5
gears = 10; `INTERNAL_GEAR_1` + one unknown = 2 left out). First Build since
v2.1.1 on a car with per-gear spinners; every other car carried only
final drive / TC / brake power, so it never showed.

**Fix.** `alignLiveGearNames(live, parsed, note)` right after
`readLiveSetupSpinners()`: live+1 == template gear names → rename (items
copied, `section` updated, the read map untouched); equal → as is (a future
CSP fix); else → gear spinners dropped, template keeps its gears, log says
so; no gear spinners or no gear sections → unchanged. Log: `liveSetup: 60
sections · gears renamed: CSP INTERNAL_GEAR_1..6 = the file
INTERNAL_GEAR_2..7, values a,b,c,d,e,f` (1st..6th as carried — check them
against the car's .rto lists).

**Tests.** `test_v251_gear_names.lua` (43) on the real written file
(`acd/fixtures/huracan_silverstone_2026-09-29_1835_built.ini`) + the car's
.rto lists: disabling the fix reproduces that file's exact gearbox
(red-green checked). `test_carry_unmanaged.lua` no longer reads the live
setups folder (the 2026-09-22 files were overwritten; their numbers are
constants now, the carry runs on the fixture). Suite: 21 files, 954
counted checks, all green. **Untested in-game** — first thing to check:
the `gears renamed` line and that loading the Build leaves the gearbox as
it was.

## v2.5.0 — what the v2.4.0 logs and the Sunbeam project showed

**Prompt.** "Check logs and look at the Blender project, see if there's
any ideas we can use for here" → report → **"Go through it carefully and
build all please. The Sunbeam is a work in progress. Dampers etc may be
added at a later date."** Backup: `Downloads\SetupCoach_backup_v2.4.0.lua`
(DC49ACABEF0C94C7). Evidence: 21 v2.4.0 Builds — Escort Mk2 (Nord),
Dacia (Taupo), axfor Camotos R6 (Nord, Phillip Island), and Nik's
`talbot_sunbeam_lotus_81_works` (Nord, Adelaide, Bathurst): Escort-Mk1
physics base, live rear axle, NO bars, NO adjustable dampers, no rear
toe/camber; physics changing under one id (see the Sunbeam memory).

1. **Travel range** (`readTravelRef`, `refreshTravelRef`): PACKER_RANGE
   per axle, live PACKER_RANGE_xx per corner (mm; SHOW_CLICKS rule), every
   corner against its own range; static travel at rest from the pits;
   re-read each pit stop. The old `TRAVEL` key exists on no car (ten
   checked) → everything was vs 0.12 m: GT cars logged 0 bottoming ever,
   the Sunbeam 70–113 per window (ride height + springs up every Build).
2. **Evidence units** (`unitsPerLapFor`, `bankEvidenceUnit`): laps over
   7.5 km split into ~5 km sections by spline position (Nord 4, Le Mans 3);
   forward crossing banks a section, the lap line closes the last one,
   reversing never double-banks, a jump over a section is partial, lap-
   valid drop flags only its own section. Wording via `EV_UNIT` (laps /
   sections). The unit in progress at a Build is partial (applies to
   laps too). The gate was overridden on 18 of 21 Builds.
3. **Brake bias from grip**: `tyreBrakeForce` (LS model DX_REF·FZ0·
   (Fz/FZ0)^LS_EXPX, or linear DX0+DX1·kN) summed per axle in the braking
   accumulator (`brkCapFSum/RSum/N`); Sunbeam 76.1 % load → 69.0 % grip →
   target 70.0 %. `handbrakeRecent` (1.5 s) excludes samples and rear
   lockups. BRAKE line: lockups disagreeing with the target are named and
   outrank it (`liveBiasPct` from the spinner read / the Build).
4. **Levers for cars without bars/dampers**: `levers.springs` (loose →
   rear softer, or front stiffer if the rear is at its softest / running
   out of travel; tight → mirror; stands aside if the travel checks moved
   springs this Build — `springsMovedForTravel`), `levers.diff` (coast only;
   more lock for lift-off oversteer, less for entry push, lap-supported;
   RWD/FWD). Rear-damper lever says "no adjustable rear dampers on this car".
   `absentSections` → ONE "Not adjustable on this car" line (was ~20
   SKIPPED lines); `rangeLimits` → one "Range limits reached" line
   (camber, pressure, spring, bias). Neither line alone makes a Build write.
5. **Per car + track records** (`parseKeyedStore` & co., "car>track>
   payload|…", legacy single records still read): last-Build record and
   pending lever moves. A move waits for the next Build at ITS track.
6. **Held slides** (`slideEp`, `heldSlides`, `HELD_SLIDE_S` = 1 s): an
   oversteer episode started with the handbrake or held on the throttle
   ≥ 1 s moves its snap counts to heldSlides; real snaps count exactly as
   before (cooldowns unchanged, so the 25/100 calibration stands). Bins
   clamp at 0 (a count moved across a unit boundary).
7. **Physics fingerprint** (`checkPhysicsFingerprint` in `refreshTargets`,
   `forgetLearned`): parsed content of car/suspensions/setup/brakes/
   drivetrain/tyres/aero/engine .ini + final.rto list, two polynomial
   hashes (no bit ops — LuaJIT). First sighting records only; a change
   re-arms the bias write and clears rideCal, camberGain, ledger, branches,
   pending, last-Build record for that car; the next Build and the panel
   say so (and warn that saved setups store list positions).
8. **Ride-height direction** from the pit calibration's slope sign
   (`rideDir`): bottoming raise + rake follow it; "⚠ verify direction"
   only until measured.

**Debug:** `held slides (v2.5.0)`, `evidence units (v2.5.0): … · physics
fingerprint: …`, travel as share of the car's range (+ source, at rest),
`sections:` instead of `laps:` on long tracks (bins `L3.2` = lap 3
section 2, `held n`), the physics-change first change line, the two
summary lines.

`test_v250_evidence_and_physics.lua` (150) runs the shipped blocks
(unit banking, snap episodes, braking accumulator, levers, summaries,
fingerprint) against the extracted Sunbeam + ten other cars' real files.
It caught a real bug: the family pattern `DAMPER?_BUMP_` (Lua `?` makes
the R optional, so it never matched `DAMP_`). Suite: 20 files, 916
counted checks, all green. Untested in-game.

**Version control (v2.5.0):** `D:\Claude\setupcoach-tools` is a git repo
(local identity Nicklearse101, `core.autocrlf false` — the app file is
CRLF). `app/` holds a snapshot of the installed `SetupCoach.lua`,
`manifest.ini`, `CLAUDE.md`; the INSTALLED file stays the working copy.
All 37 releases v1.1.1–v2.4.0 imported from Downloads as dated, tagged
commits. **Release routine:** set `manifest.ini` `VERSION` to the new
version (Content Manager shows the manifest's) → tests + check.ps1 green
→ copy the three app files into `app/` → Downloads copy
`SetupCoach_NN_vX.Y.Z.lua` → `.\make_release.ps1` (builds
`SetupCoach_NN_vX.Y.Z.zip`: `SetupCoach_changelog.txt` at the top — every
version, from the header comment — plus `apps/lua/setupcoach/`
SetupCoach.lua + manifest.ini; refuses a manifest/app version mismatch or
a Downloads copy that differs from the installed file) → commit (with the
Co-Authored-By trailer) → tag `vX.Y.Z`. The zip is the one thing sent —
changelog inside, no separate file (Nik, 2026-09-29).
`acd/extracted/` (other people's car data) is gitignored — never commit it.

## v2.4.0 — branch passes: cycle back, judge the group, put back no-effect moves

**Prompt.** *"Once the Build has been through the cycle of adjusting
particular modules in a chain, such as arb, dampers etc. It should cycle
through to the beginning of that particular branch and monitor the group
as a whole. Is that something that's already happening?"* It wasn't:
every Build started at the top and took the first non-frozen lever,
**frozen was permanent** (a frozen lever is never moved, so never
re-judged), each move was judged only against the window before it, and
nothing recorded where the problem stood when the branch started. Asked
whether end-of-pass no-effect moves should be put back or only reported:
**"Go, put them back to starting value."** Backup:
`Downloads\SetupCoach_v2.3.0_backup.lua` (C76F9730511FE243).

**Model.** Branch = car + track + key (`low-loose` …). States: `active`
→ (`verify`) → `active` (next pass) / `done` / `stopped`. Stored in
`settings.branchState` (records `|`, fields `>`, moves `+`, move parts
`~`, sections `SEC=before/after` — folder names can't contain `|`/`>`;
`fmtNum` never writes an exponent). Newest 40 records kept.

1. **Moves record their sections**: the runner snapshots every
   `MANAGED_SECTIONS` value before a lever call and diffs after.
   `judgePendingLevers` hands its verdicts (`self.leverJudgements`) to the
   branch; a move never judged (another car/track Build between) becomes
   `unjudged` and is **kept**.
2. **Pass end** — problem gone (verdict ≠ direction, incl. slight/mixed)
   or no lever can move. Group verdict `branchGroupEffect`: effect > 2 ×
   √(seBase² + seNow²), else the 15 % rule.
3. **Put-back** (`branchKeepValues`): a section keeps the value after the
   last move on it that helped (or was never judged), else the pass-start
   value. Skipped + logged if it changed since the pass left it, its
   lever's module is now off (`LEVER_MODULE`), or `writeTuned` refuses
   (damping floor, LUT curve, calculated target). Put-back sections are
   `calc.touched` for that Build; the branch is HELD that Build.
4. **Verify** next Build: rate rose beyond the noise with the signal
   present (or a fixed problem came back) → **restore** the put-backs.
   Not loaded → put-backs applied again.
5. **Then**: fixed → `done` (a returning problem starts a new pass 1,
   ledger as-is); improved and pass < 3 → next pass from the top, frozen
   levers reopened with one try left (`ineff = FREEZE − 1`), per-click
   `sens` kept; if nothing was put back the chain re-runs in the same
   Build; no gain → `stopped`; pass 3 improved → `stopped (capped)`.
6. **Also fixed**: ledger store is `car>items|car2>items` (old
   `car|items` migrates; 30 cars kept); `leverPending` carries the track
   (4th field) and a window at another track doesn't judge it; branch
   store + ledger also commit on a "no changes" Build (the judgements
   consumed at its start would otherwise be lost). `writeTuned`'s
   `calc.touched` refusal names who set the section.

**Debug:** `branches (v2.4.0, car at track): low-loose ACTIVE pass 2:
baseline … at Build #n, now … · moves: arb helped [ARB_REAR 5→4]; …`,
plus `Branch … pass N ENDED (…): a → b per 100 … = IMPROVED/NO GAIN/FIXED`
and one `put-back:` line per section. Settings: **Reset lever history
for this car** (ledger + all its branches).

`test_branch_passes.lua` (100) extracts the **whole shipped runner block**
and drives it Build by Build with stub Build locals (fake setup, scripted
verdicts/rates, levers that move real values) alongside the real
`judgePendingLevers`/ledger/store code and a replay of the app's commit.
Suite: 19 files, 763 counted checks, all green. Untested in-game.

## v2.3.0 — calculated targets instead of click-by-click

**Prompt.** The user noticed Build moves most things 1–2 clicks and asked
whether the app calculates optima or steps by trial and error ("Research
and report"). After the report: **"Yes build all, but bear in mind moving
brakes too far forward/backward has a big influence on understeer/
oversteer/stability on entry. Make brake balance advise only after 1
build."** Backup: `Downloads\SetupCoach_v2.2.0_backup.lua`
(A3B23BD7B7641E10).

**Groundwork.** `readSetupItem` keeps `raw = {min, step, showClicks}` so
`physicalOf(item, stored)` / `storedOf(item, phys)` convert clicks ↔ real
units (N·s/m, N/m…). `refreshSchema` reads `self.chassis` (mass, CG,
hub masses, spring base rates, motion ratios) and the final-drive options
(`self.finalOptions`). `cornerSprungMass`, `cornerSpringRate` (nil on
DWB2 motion-ratio axles — not trusted).

1. **Brake bias** (`biasTarget`): during straight-line hard braking
   (brake > 0.7, −0.9 g, speed > 60, little steer/lat) it averages the
   front wheel-load share x; equal-limit split = x·rF / (x·rF + (1−x)·rR)
   with tyre radii, **+1 %** stability margin. Needs ≥ 30 samples in ≥ 4
   braking zones. One write per car (see hard constraint), capped ±3 %;
   forward HELD on lap-agreed turn-in push / front lockups, rearward HELD
   on lift-off snap / rear lockups / loose rear. The old ±1 lockup writer
   is retired; the BRAKE advice line carries target, trims and trade-off.
2. **Springs** (stiffening only, when the median clean lap uses > 92 % of
   travel): k_new = k × min(use / 0.92, 1.30) — i.e. ≤ +30 % per Build,
   rounded up onto the grid. No travel data / unknown rate → the old steps.
3. **Front ride height to the aero peak**: target = GH_CL peak + 2 mm vs
   fast-corner (> 180 km/h, > 0.5 g) front ride height, converted with a
   **pit-measured mm/click** (every stop ≥ 2 s in the pit records
   clicks ↔ static height; fuel-matched within 5 L; median pairwise
   slope). Uncalibrated → not written. ≤ 3 clicks; rake stands aside when
   the front was set.
4. **Damping-ratio floors** (vanilla `DAMP_*` with known spring rate):
   ζ = c / 2√(k·m) ≥ 0.30 bump / 0.50 rebound (v2.6.1, was 0.40 - anti-
   bounce); pre-pass lifts in one move to floor × 1.05, and `writeTuned`
   refuses any soften below it. **v2.6.1: rebound follows the springs** -
   each corner's slow rebound is snapshotted before the chains run; a
   corner whose ratio fell while its rebound was left alone (a spring move
   did it) is lifted back in the same Build (`test_v261_rebound_follows`).
5. **Camber**: DCAMBER route has a noise dead-band max(0.05°, 2×SE) and
   a measured gain (loaded vs static, ≥ 3 Builds spanning 0.3°, clamped
   0.5–2.0, `settings.camberGain`).
6. **Measured-response jumps** (ARB, rear dampers, wings only):
   `judgePendingLevers` keeps a per-click effect (`sens`, 7th ledger
   field) only if effect > 2 × √(seBefore² + seAfter²) from per-lap rates
   (`lapRateStats`); the runner then moves ceil(needed / sens) clicks
   (≤ 4; LUT bars ≤ 2) toward other-rate × 1.25 (loose-low: ≥ 25/100).
   Old 3-field pending records still parse.
7. **Final drive** (advice only): ideal = current × 0.975 × limiter /
   rpm at Vmax; nearest `final.rto` option named; on the limiter → next
   longer option.

**Debug:** one line, `calculated targets (v2.3.0): bias … · travel use …
· front ride … · damping ratio … · camber gain … · final drive …`, plus
`[measured-response jump: n]` on lever lines.

`test_calculated_targets.lua` (72): Huracan real numbers (front bump ζ
0.97; rear rebound min 0.18 → +5 clicks to 0.47; bias 59.1 → 60.1 %;
final drive 4.49 ideal on the 4.5 the driver picked). Suite: 18 files,
663 counted checks, all green. Older guards moved to the new lever
signatures / bias writer / gearing wording.

**Calibration still needs real laps:** two pit stops at different front
ride clicks (similar fuel) before the ride-height target writes; three
Builds with different camber before the gain is measured; a lever needs
one measured move before it can jump.

## v2.2.0 — CSP extended suspension: fixed thresholds, LUT bars, LUT dampers

**Prompt.** After checking the research section above ("Check .md for
recent updates"), the user said **"All 3"**. Backup:
`Downloads\SetupCoach_v2.1.1_backup.lua` (B2DA4C5EAFB0FCE1).

**1. Damper event thresholds fixed at 0.54 / 1.20 m/s** (`DAMPER_EVENT_
MODERATE/SHARP`). They're compared against wheel-travel velocity, 5–50×
above any crossover, so scaling by the crossover had no physical basis,
and it never ran before v1.9.6 — the fixed pair *is* the validated
calibration. Decided by a same-car A/B in the real log: Dacia front
rebound events 12/12/8/3/16 at 0.54/1.20 vs **0/0** at the scaled
0.90/2.00 the same evening; Huracan (0.060 → pinned 1.00/2.20) 0–1 across
1,100+ corners. Crossover still read and logged. `test_ini_default_type`
and `test_v199_corvette` guards moved from the retired 18×/40× to this.

**2. CSP LUT anti-roll bars `ARB_F`/`ARB_R`** (19 of the user's cars).
`SETUP_PROBE.arb` knows them; `arbFSection`/`arbRSection` resolve per end
by presence. **VALUE = 0-based LUT row** — proven by `fr_bmw_btcc`, whose
keys are text and whose row 0 is `detached|0` (corrects the research
note's "range = first/last index"). `readLutArb` (per car, in
`refreshSchema`) reads `setup.ini LUT=` and the LUT via `ac.DataLUT11`
(`getPointOutput`), recording rows, stiffness by row, `rising`,
`firstUsableRow`. Lever rules: one row per Build; limits at the limit
(not 1.5 steps short); never onto a 0-stiffness row; non-rising LUT not
written; range from spinner else LUT row count. Unreadable LUT →
direction assumed, first row off-limits. Also fixed: push with only a
rear bar used to report "no ARB section"; a refused soften now falls
through to stiffening the other end.

**3. CSP LUT dampers `DAMPER_BUMP/REBOUND_*`** (11 cars). In `SETUP_PROBE`
(so managed + schema-read); `damperSection(kind, corner)` resolves per
corner in the axle loop, the rear-dampers lever and the rebound snapshot.
`readLutDampers` reads `dampers.ini` `[FRONT|REAR] BUMP_SLOW_<n>` /
`REBOUND_SLOW_<n>` (n = click in MIN..MAX units) and setup MINs;
`lutDamperForce` interpolates between defined clicks like CSP.
`lutDamperMoveOk`: force at 0.025 and 0.10 m/s must move in the intended
direction (±1 N). **sv8_camaro_v2 rear rebound 12→13 is refused** (its
click-18 curve is broken, so 13 is softer). Unreadable curves → refused.
LUT sections with no current value are never invented from a schema
midpoint.

**Debug:** `suspension model: dampers F … · R … · ARB F … · R …` and
`DAMPER_REBOUND_LR` / `ARB_F` in the liveSetup sample. **Open question the
next BTCC/GT4 log settles:** does the spinner report a numeric-key LUT
bar's range as 0-based (row) or 1-based (key)? The code handles either via
`schemaItem.min`, but the log should confirm.

`test_lut_suspension.lua` (70) on real files for sv8_camaro_v2,
gt4_bmw_m4, gt4_alpine_a110, fr_bmw_btcc. Suite: 17 files, 591 counted
checks, all green.

## v2.1.1 — Build was resetting tyre compound and gearing

**Report.** *"before driving, i set my tyre compound and gear ratio. When
i press 'build optimal setup' and load, it reverts back to default."*

**Confirmed from the files.** Build 18:20:56 wrote `FINAL_RATIO=6`,
`TYRES=1`; the driver's own `generic/last.ini` (written at session end,
18:25) has `FINAL_RATIO=3`, `TYRES=0`. In this car's `final.rto`, index 6
= **3.9166** — the value `drivetrain.ini` gives as `FINAL=`, i.e. the
car's default; index 3 = 4.5000, the shorter one the driver picked.
"Reverts to default" was literal. The same log had read the compound
correctly elsewhere (`tyreDataSrc=tyres.ini [FRONT "Slick Soft"]` =
index 0), so the app knew and wrote otherwise.

**Cause — v1.8.1 was half right.** It stopped the live sync touching
unmanaged sections (correct: no writer may touch gearing), but "not
synced" left them at the **template's** values, and the template is
`last.ini`, which AC writes only when a session *ends*. Anything set in
the setup screen before driving is absent from it. The log said
`13 unmanaged/left alone incl. gearing` every Build — "left alone"
described the writer while the file quietly stated old values.

**Fix.** Unmanaged sections are **carried** from the live spinners.
Rules kept: never add a missing section (v1.8.0's `INTERNAL_GEAR_1`);
`readOnly` skipped; writers still gated by `MANAGED_SECTIONS`. Compound
additionally cross-checked against `car.compoundIndex` and corrected on
disagreement. `CARRY_EXCLUDE = {FUEL = true}` — every other unmanaged
spinner describes the *car*, fuel describes the *stint*, and it is not
yet established whether the API reports the setup's starting fuel or the
tank; carrying a part-empty tank into a setup file would be worse than
the bug. The log prints both numbers to settle it.

**Debug:** `liveSetup: … N managed synced, M unmanaged CARRIED from live
(gearing/compound/fuel/TC - never written, now never reverted; template
was stale on FINAL_RATIO 6->3, TYRES 1->0), … · compound 0 confirmed
against the car · FUEL not carried: template 30 vs live 12 …` and
`TYRES` / `FINAL_RATIO` added to the sampled sections.

`test_carry_unmanaged.lua` (38) runs the app's own readIniFile /
getCurVal / ensureSectionValue against the two real files and `final.rto`.
Also fixed: `test_managed_sections.lua`'s GEARING check tested the global
`fail` counter, so one earlier failure reported as two.

## v2.1.0 — lever chains: one lever, measured, then the next

**Prompt (user, 2026-09-22):** rake went negative; "there should be
something to determine whether one module over another needs adjusting…
if adjusting arb doesn't stop the problem in a few clicks, prioritise the
next module… and measure how one affects the other"; ARB/aero threshold
to 180 km/h; "stiffening rear ARB while increasing rear wing will cancel
each other out"; a button to override the 2-lap gate for testing.
Backups: `Downloads\SetupCoach_v1.9.9_backup.lua`,
`Downloads\SetupCoach_v2.0.1_backup.lua`.

**Structure.** ARB, rear dampers, front toe, rear toe, rake and wings are
now `levers.<name>(regime, direction) → moved, why`. The bottoming raise,
front damper histogram, springs, fast dampers, brake bias, diff, camber
and pressure stay outside the chain (not balance levers). The runner
(end of `buildSetup`'s writer block) walks `LEVER_CHAINS[key]`:

| key | chain |
|---|---|
| low-loose | arb → rearDampers → toeRear → toeFront (reverse) → rake |
| low-tight | arb → toeFront → rearDampers → toeRear (reverse) → rake |
| high-loose | wings → rake → toeRear |
| high-tight | wings → rake → toeFront |

`writeTuned` now returns `(handled, changed)`; a lever counts as moved
only if a value changed.

**Ledger.** `engine:judgePendingLevers(car, th, lastBuildLoadedVerdict)`
runs before any writer: for each `settings.leverPending` entry
(`car|serial|key:lever:rateBefore;…`) it compares this window's rate
(oversteer or push per 100 corners) — helped if the verdict is gone or
the rate fell ≥ `LEVER_EFFECT_DROP` (0.15); `ineff` resets on help,
`frozen` at `LEVER_FREEZE_AFTER` (2). Stored per car in
`settings.leverLedger` (`car|key:lever:tries:ineff:frozen:last;…`). Not
judged when `lastBuildLoaded` is NO (window wasn't driven on that Build).

**Conflict rule.** Opposite low/high verdicts: high chain runs, low
chain HELD with a note. Same-direction verdicts: one lever each.

**Rake floor.** `staticRideHeightR` captured with the front;
`RAKE_MIN_MM = 3`; the rake lever refuses "less rake" at/below it and the
log prints `rake: static front X mm rear Y mm = +Z mm rake`.

**Split.** `ARB_AERO_SPLIT_KMH = 180` (was 160).

**Override.** `OVERRIDE LAP GATE (test)` button beside Build; one-shot
(`engine.gateOverrideOnce`), log line `GATE OVERRIDDEN (test button)`.

**Debug lines to verify with:** `effect (previous Build #n): high-loose
via wings: 31.5 -> 33.8 per 100 corners (NO EFFECT) [1/2 without
effect]`; `levers (chain order, ledger for this car): high-loose: wings=
FROZEN(2 tries, 2 no-effect, last no-effect) > rake > toeRear · …`;
`Balance high-speed (loose): lever wings moved (first in the chain);
oversteer rate 31.5 per 100 corners banked to judge it next window`;
`Balance low-speed (tight): HELD this Build - high-speed says loose…`;
`rake: static front 72 mm rear 74 mm = +2 mm rake`.

`test_lever_chain.lua` (59) replays the Huracan's four wing moves
through the ledger. Suite: 15 files, all green.

## v2.0.1 — first night on v2.0.0: Huracan GT3 @ Silverstone

4 Builds, 5 declines, all logged and explained. The gate/bins/
consistency/consumption machinery worked as designed. Three fixes:

1. **`car.lapCount` goes backwards on a session restart** while the app
   keeps its state. The user's routine is Build → load setup → restart.
   `lapCount > lastLapCount` was false for three real laps; the first
   boundary that fired banked them as one bin (`L4 c205`, `L5 c242`) →
   gate saw "0 clean laps" and declined three Builds it should have
   allowed. Now a drop re-syncs the counter, starts the bin there and
   flags the lap pit (restart = out-lap from the pit box). Header shows
   `N session restarts seen`.
2. **CSP reloads the app on a session restart** → "Build #1 this
   session" every time and `lastBuildLoaded: n/a` always. Last Build's
   written values + a running serial now persist in `ac.storage`
   (`settings.lastBuildRecord` = `carId|HH:MM:SS|SEC=v|…`,
   `settings.buildSerial`) and are restored for the same car.
3. **Pressure clamp now says so**: rears ran 29.7/29.9 hot vs 26 target
   with cold already at the 15 psi floor; three Builds wrote "→ cold
   15.0" silently. Note now reads `[CLAMPED at this car's minimum 15 –
   wanted 12.3; this much heat is coming from sliding…]`.

**Seen, not changed — the user's call.** The car read `loose` in all
three regimes with every clean lap agreeing (2/2, 3/3) in every window:
50–70 low-speed / ~30 high-speed snap per 100 corners, unchanged after
four rounds (rear ARB → min, front ARB 8→14/15, rear rebound 10→4, rear
wing 5→11, front wing 1→0, rake −4 clicks). Either the levers don't move
this signal, or this driver's rotation exceeds the 25/100 bar. There is
no "did the last change help" feedback yet; the per-window rates are now
logged to build one from (compare the window's snap rate with the
previous window's; freeze a lever whose move didn't reduce it).

`test_evidence_window.lua` now 70 (restart sequence + storage round-trip).

## v2.0.0 — the lap as a whole: evidence gate, consumption, lap consistency

**Prompt.** The user asked whether the app builds from full-lap analysis
or "a couple of corners' data," and — after the honest answer that it only
half did — said: *"Do it and the lap-consistency check. Update the debug
so we can check it's working. Keep previous version as backup."* Backup:
`Downloads\SetupCoach_v1.9.9_backup.lua` (hash 58236E3092405851).

**What was true before.** All counters accumulated session-wide (good),
but Build acted on 3 events (`th=2`), never consumed what it acted on,
and had no concept of a lap. Corvette log: four Builds inside two
Nordschleife laps (corner samples 80/88/202/97), each stacking 2 clicks.

**The four pieces** (block comment above `BUILD_MIN_CORNERS` in the app):
1. **Lap bins** — at each `car.lapCount` increment, the counters since the
   previous boundary are banked (`WINDOW_KEYS`) with flags: `pit`
   (`car.isInPitlane` seen during the lap), `partial` (app loaded
   mid-lap, from `splinePosition` on the first frame), `valid`
   (`car.isLastLapValid`). Totals still accumulate for every consumer.
2. **Gate** — `engine:buildEvidence()`: `clean ≥ settings.buildMinLaps`
   (slider 1..5 in Settings, default 2) and `corneringSamples ≥ 20`.
   Declined → own log entry `result: DECLINED`, nothing consumed, panel
   item **BUILD EVIDENCE** (first line) says what's missing.
3. **Consumption** — `engine:consumeWindow()` after a successful write:
   counters, corner samples, camber/grip/aero sums, pressure peaks → 0;
   `windowBinsStart` fences earlier bins. Kept: static camber & ride
   height captures, cold-pressure capture, tyre ref, schema, fuel, bin
   history. Build message gains "[telemetry consumed – drive N+ clean
   laps…]". `lastBuildWritten` (managed sections) is compared to the live
   spinners next time → `lastBuildLoaded: YES/PARTLY/NO`.
4. **Lap consistency** — `regimeVerdict(self, 'low'|'high'|'rear', th)`
   wraps `balanceVerdict`; with ≥ 2 clean laps the totals' verdict acts
   only if ≥ half the laps agree individually, else note
   `'inconsistent a/c'`. `lapSupport(self, key)` does the same for
   scalars (≥ 2 events in ≥ half the laps): lockF/lockR (brake bias),
   bottoming (ride raise, springs, fast-damper direction), turninPush &
   rearToeEvents (toe), diffRotationEvents/diffEvents. `balanceVerdict`
   is now called only from inside `regimeVerdict`.

**Not consumed on a "no changes" Build** — the data wasn't acted on, so it
keeps accumulating.

**Debug lines to verify with:** `evidence: window since … · laps: clean=
pit= partial= · corners= · gate: … -> PASS|DECLINED`; `laps: L3[c42 push
12/9 hi 3/5 tin 4 rtoe 2 lk 6/0 bot 0 dmp 3/4|2/5 dif 0/1] …` (P/~/X
flags); `consistency: low=… a/c · high=… · rear=… · lockF a/c …`;
`lastBuildLoaded:`; `evidence consumed:`. Header now carries the app
version and Build number.

`test_evidence_window.lua` (53) simulates the Corvette sequence (three of
four Builds decline), a one-lap oversteer spike (`inconsistent 1/4`), pit
and partial laps excluded, consumption fencing. Manifest still says
`VERSION = 2.0.2` (NEXT PHASE item 1) — closer now, still not equal.

## v1.9.9 — first Corvette Z06 GT3 logs: seven findings

Four Builds in 17 minutes at the Nordschleife on `corvette_z06_gt3_2024`
(decrypted to `acd/extracted/corvette_z06_gt3_2024/`), plus a 1934
Frazer Nash. The user asked what "no DY0 reference" meant.

1. **DY0 vs DY_REF.** `DY0` is the old linear load model's peak
   coefficient; modern tyres (this one: `DY0=0 DY1=0`, `DY_REF=1.81
   FZ0=3000 LS_EXPY=0.72`) leave it 0. MECHANICAL GRIP now normalises
   against `DY_REF` when DY0 is 0 and says so. Measured F 1.41 / R 1.34
   = ~78 % / 74 % of DY_REF (a loaded tyre has less than the reference
   available, so the % reads slightly low on an aero car).
2. **Rear wing is `WING_3`** on this car (aero.ini: BODY / SPLITTER R /
   SPLITTER L / REAR WING / DIFFUSER R / DIFFUSER L; setup.ini `[WING_3]`
   "Rear wing"). Four Builds skipped it. `resolveWingSection` now uses
   `aeroWingIndex` (role→index from aero.ini NAMEs) when the live setup
   has that section, syncing its value first; WING_1/2 is the fallback.
   `wingRoleFromName` checks `diffuser` before `rear`.
3. **Toe was the fourth one-way ratchet.** Front toe 11→19 of 20, rear
   14→6, in four Builds. Now verdict-gated, 1 click/Build, reversible
   toward zero (never past it). `readSetupItem` exposes `zero` (stored
   index of zero toe: Corvette 10, Ferrari LR 5, LF 0) and
   `schemaWithLive` carries it.
4. **Rake: 1 click per end per Build**, always (v1.9.7's sizing had
   made it 2 per end = 4 clicks of rake per Build; 16 clicks in 17 min).
5. **`HISTOGRAM_MIN_EVENTS = 6`** before a count-ratio rule may write:
   front damper histogram (was stiffening on 3/0 events) and the diff
   (flip-flopped on 3 vs 2 then 4 vs 3). Diff also needs 25 % dominance.
6. **Crossover typo guard.** This car's file: FRONT 0.50, REAR 0.050. >3×
   apart → take the smaller. Ferrari 0.030/0.010 = exactly 3× keeps its
   front value (anchor).
7. **`DCAMBER_LUT`** (cmbr.lut) sampled via `ac.DataLUT11` for the real
   peak → `peakCamberSrc=live-lut`. On this car it agrees with the
   coefficients (−4.0°); not guaranteed elsewhere.

**Rule of thumb now written into three places:** a rule whose action
can only ever go one way is a ratchet; find its counter-signal or cap it.
Wings (v1.9.4), fast dampers (v1.9.4), rear rebound (v1.9.3), toe
(v1.9.9). Rake and brake bias have counter-signals; camber and pressure
are absolute-target modules.

`test_v199_corvette.lua` (58) runs the shipped readers on the decrypted
Corvette files, including its real cmbr.lut.

## v1.9.8 — slight oversteer is not a fault

**Prompt.** After the drift-car note ("every balance rule treats
oversteer as a fault"), the user: *"slight oversteer in a normal race car
isnt a bad thing, that should be noted."* Recorded as a hard constraint
above, and built in.

**What was wrong — the same defect in four places.** Push and snap were
judged independently, or by "larger raw count wins":
- **ARB** softened the front for any push > th AND the rear for any snap
  > th in the same Build (both bars down = balance unchanged, more roll);
  the mixed-case guard only caught the two aiming at the *same* bar.
- **Rake, low speed** did it per end — a real Dacia log has `LF 5→4 (more
  rake for push)` and `LR 5→4 (less rake for oversteer)` in one Build.
  Both ends down, rake unchanged, car 1 click lower. Same shape as the
  v1.4.1 ARB self-cancellation.
- **Panel ARB line** said "soften front" whenever push > th, regardless of
  the oversteer count beside it.
- A slightly loose car was pulled toward push by all of them.

**Fix.** `balanceVerdict(self, push, snap, th, useRateFloor)` — see the
hard-constraints entry for the rule. Used by: ARB writer, rake (both
regimes), wings, `rearHandlingSignal` (mid+high, rate floor on), the ARB /
AERO / REAR DAMPERS panel lines, and a new debug line
`balance verdicts: low=… high=… rear=…` with the snap-per-100 rate.
`balanceLeftAloneNote` gives the panel and the Build log the same wording
for a nil verdict, so they can't disagree.

**Rear dampers: nil verdict = left alone.** The histogram fallback is
gone from the rear axle. It was structurally biased there (rebound events
out-number bump in every real session) and resolved to "stiffen rear
rebound" — the v1.9.3 bug — on exactly the slightly-loose cars this
version protects. Front keeps its histogram (AC's front-rebound tooltip
is a per-car trade).

**Real sessions re-run under the rule.** Dacia 17 Sep 20:05 (push 76 /
snap 65, 62 corners): `mixed` → ARB and rake left alone (was: front ARB
softened, and the both-ends-down rake pair). kinkl Ferrari 17:15 rear
signal (373 snap / 235 push, 81/100): still `loose` — v1.9.3's fix stands.
kinkl low-speed pair alone (215/265, ratio 1.23): `mixed`.

**Watch in the next logs.** How often `low=slight` and `low=mixed` appear,
and whether testers report a car that *feels* loose while the verdict
says slight — that's the signal to lower the 25/100 bar.

`test_balance_verdict.lua` (41, loads the shipped functions);
`test_rear_rebound_direction.lua` updated (22).

## v1.9.7 — found while looking for a drift-car log that wasn't there

**The non-finding first.** The user drove the `bmw_m3_e30_drift` online at
Mid-Ohio for ~2.5 h on 2026-09-18 (five sessions per Content Manager's
logs) and asked for the debug to be checked. No Build entry exists from
that day. `setups/bmw_m3_e30_drift/nagp_mid_ohio/SetupCoach_Optimized.ini`
has an 18 Sep 19:52 mtime but is **byte-identical to the 16 Sep Build**
(same `-32.00` camber, `29.8/18.9` pressures) — CM re-saves the selected
setup ~9 s before each launch (`server_temp.ini` at 22:28:51 vs launch at
22:28:42 is the same pattern). CSP's `custom_shaders_patch.log` for the
last session shows the app loaded clean, no Lua errors. Conclusion: Build
wasn't pressed. **How to check this next time:** compare the Optimized
file's *content* to the last log entry, not its timestamp; read
`AppData\Local\AcTools Content Manager\Logs\Main Log_*.log` for session
times; `Documents\Assetto Corsa\logs\custom_shaders_patch.log` only covers
the *last* launch.

**Drift cars and this app.** There is no drift mode. Every balance rule
treats oversteer as a fault: the 16 Sep drift Build softened rear
rebound/bump "for oversteer", added rear toe-in, and cut rear cold
pressures **12 psi** because wheelspin had the rears at 50 psi hot. On a
drift car that is the app doing exactly what it's built to do, to a car
that wants the opposite. Not a bug; a scope boundary worth stating to
testers.

**1. Nudge size ignored the step (`writeTuned`).** Every nudge was
`frac × clicks × |cur|` — a percentage of the current value — with the
schema used only to clamp. Fine on a 0..24 click index (floors to 1). On
the Ferrari's fast rebound (175..190) 8 % of 185 is **15 clicks, the whole
range** — the real mechanism behind v1.9.4's "185→175 in one press" (the
ratchet chose the direction; this chose the distance). Dacia ARB at 21079
on a 1000 N/m grid, same cause. Now `clicks × step`, snapped to the grid,
whenever a step is known (every car since v1.9.6); percentage only with no
step. Log lines say `, 2 clicks of 1000`. Rake now moves up to 2 clicks
instead of ~1 — watch it.

**2. tyres.ini read the wrong compound (`readTyreReference`).** Always
`[FRONT]`. The E30's real file (decrypted): compounds 0/1 `PRESSURE_IDEAL=38
DCAMBER_0=1.1 DY0=1.21`; compound 2 (Semislick) `31 / 1.2 / 1.29`. Semislick
drivers got a hot target 7 psi high. Picked by `car.compoundIndex`,
cross-checked by `SHORT_NAME` (`car:tyresName()` is the short name),
fallback `[FRONT]`. `tyreDataSrc=tyres.ini [FRONT_2 "Semislick"]` in the log.

**3. `writeDebugLog` failed silently.** Now appends
`[debug log NOT written: <why>]` to the on-screen Build message and writes
the reason at the top of the next successful entry.

**SHOW_CLICKS=1, third confirmation.** E30 `WING_1`: SHOW_CLICKS=1, MIN=1
MAX=3 STEP=1, live-synced value 3. Click-index would make the range 0..2;
steps-from-zero makes it 1..3. On a wing, not a damper.

`test_step_nudge_and_compound.lua` (43 checks). E30 data now in
`acd/extracted/bmw_m3_e30_drift/`.

## v1.9.6 — live always wins: the other three nil-default reads switched on

v1.9.5 fixed tyres.ini and parked setup.ini / aero.ini / suspensions.ini
as "each its own decision". The user's decision: *"live should always
win, that's the whole point of the app, to read live data and advise on
setup accordingly."* All three on, each regression risk handled where it
lives.

**setup.ini (`readSetupItem`).** Had never returned an item on any car —
`schemaLimited=true` in every log ever written; `BAKED_SETUP_SCHEMA`
exists to work around this one function. The risk: live out-ranks baked
per section and the reader lacked the baked table's per-car unit
corrections. Resolved by checking the reader's stored-unit conversion
against the live spinner ranges those cars reported in real logs, on
four cars' real decrypted setup.ini — and making it a rule (table in
"Hard constraints"). SHOW_CLICKS=1 → step-multiple is confirmed on the
Ferrari's slow AND fast dampers (10..32, 175..190); the old reader
treated 1 and 2 identically, which is why `gen_baked_schema.py` grew
`CONFIRMED_DAMPER_UNITS`. Pressure — the one writer without the spinner
overlay — now gets it. `schemaSource` labels renamed `setup.ini` /
`baked` / `setup.ini+baked`.

**aero.ini (`checkAeroLutRisk`).** The nil-default `NAME` read returned a
list; a list is truthy and `~= ''`, so `wingRoleFromName` called
`string.lower()` on a table and threw — inside the function's own pcall,
so the whole check returned nothing. **That is what `aeroLutChecked=false`
in every log was.** Not a CSP limitation; a crash on the first line of
the loop. All downstream consumers are advice caveats + informational
CL capture, pcall-guarded, never feed a writer.

**suspensions.ini (`readDamperCrossover`).** The damper event thresholds
scale off this: 9×/20× chosen so "a typical 0.06" reproduced the
on-track-validated 0.54/1.20. Real files: Ferrari 0.030 front / 0.010
rear, Lotus 0.050, Dacia 0.050, Abarth 0.100. The validated car is the
Ferrari at 0.030 — 9×/20× would have **halved its thresholds** the moment
the read worked, a re-tune of the most-tested car disguised as a bug fix.
Re-anchored to the real number: **18× / 40×**. Ferrari byte-identical;
Lotus/Dacia → 0.90 / 2.00 (fewer damper events than before — watch
whether the Lotus's damper writes go quiet); Abarth → the clamps.
**[v2.2.0: the "watch" item came true — the scaled thresholds deleted the
damper signal (Dacia front rebound 0/0 vs 12/12/8/3/16). Scaling retired;
every car is back on the fixed 0.54 / 1.20. See v2.2.0.]**

**Verify in the next logs.** `schemaSource=setup.ini` (or
`setup.ini+baked` on the Ferrari), `aeroLutChecked=true` with
`aeroPeaks front=~48mm` on a GT car, `damperCrossover=0.030 m/s (live
suspensions.ini)`, `peakCamberSrc=live`, and `TOE_OUT_LF=` in the
liveSetup sample on the Ferrari — the rule predicts a stored range of
`-10..7` for that SHOW_CLICKS=1 section; if the spinner says `0..17`, the
SHOW_CLICKS=1 rule is damper-only and needs narrowing.

`test_ini_default_type.lua` (86 checks) loads the shipped `iniStr` /
`iniNum` / `readSetupItem` / `wingRoleFromName` out of the app source and
runs them against the real files.

## v1.9.5 — the live DCAMBER read never worked, on any car

**Prompt.** The driver asked why the Dacia Sandero Cup's camber was being
judged by tread-temperature spread ("F spread +1°C — in the window")
instead of the tyre's peak-grip angle, with the panel showing the loaded
front at −1.45°.

**Evidence chain.**
- `content/cars/cup_dacia_sandero/data/tyres.ini` is **plain text on
  disk** (unpacked `data/` folder next to a `data.acd`), with
  `DCAMBER_0=1.3`, `DCAMBER_1=-15` → peak −2.48°. Not encrypted, not in
  `DCAMBER_LOOKUP`, and the log said `peakCamberF=n/a`. The
  "encrypted-car whitelist" theory could not explain that.
- SDK, `_ac_INIConfig:get(section, key, defaultValue, offset)`:
  *"defaultValue: Defines type of value to return, is returned if value
  is missing. If not set, list of strings is returned."*
- Every `iniGet(ini, s, k, nil)` + `tonumber(...)` was therefore nil
  regardless of file contents. `PRESSURE_IDEAL` used default `0` → worked.
  That asymmetry was the entire basis of the whitelist theory (4.6.0).
- Log audit across all sessions: every peak angle ever recorded (2.42°,
  3.09°, 3.38°) is a `DCAMBER_LOOKUP` value. The two cars not in the
  table (Dacia, F2004) are n/a. **No live read ever succeeded.**
- `test_ini_default_type.lua` (33 checks) models the SDK rule in a stub
  and runs both readers against the real Dacia file: old → nil, new →
  1.3 / −15 / 2.48°.

**Fix.** `iniNum(ini, section, key)` — asks for a string default, converts
with `tonumber`, tolerates a list return. Applied to the tyres.ini reads
only: DCAMBER_0/1 (camber's primary route now runs on every car whose
file carries the coefficients; live beats lookup), DY0 (MECHANICAL GRIP
can now show "% of this tyre's peak"), PRESSURE_STATIC (stored, unused).
Debug line gains `peakCamberSrc=live|lookup|live+lookup|none dy0=F/R`.

**Same bug, deliberately not switched on** *(superseded by v1.9.6 — all
three are now on; kept here for the reasoning at the time)* — each
changes behaviour and gets its own decision:
- `readSetupItem` MIN/MAX/STEP: live out-ranks baked per section, and the
  live reader has no ×10-camber / step-multiple-damper knowledge → the
  v1.7.1 units bug returns. v1.8.0's spinners already give real ranges.
- aero.ini WING names / LUT files: would start exercising
  `ac.DataLUT11` in app context — `aeroLutChecked=false` in every log.
- suspensions.ini `DAMP_FAST_BUMPTHRESHOLD`: re-scales damper event
  thresholds per car; the 0.06 default is the on-track-validated
  calibration.

**What to check in the next Dacia log.** `peakCamberSrc=live`,
`peakCamberF=2.48°`, and the CAMBER panel line switching from "spread"
wording to "loaded −1.45° vs this tyre's −2.48° peak (−1.03°) → add neg
camber ~10 clicks". Known parked item now more visible: the camber
oscillation (loaded moves ~1.4× static; the DCAMBER route applies the
full loaded deficit to static, so it will overshoot on the first Build
and come back on the second).

**Lesson, again.** Same shape as v1.7.7's `ui.checkbox`: an SDK signature
assumed rather than read, and a coincidence (one key worked, one didn't)
promoted to a theory and written into three comments and this file as
fact. When one read works and its neighbour doesn't, diff the *call*
before theorising about the *source*.

## v1.9.4 — pre-release physics audit: three more one-way levers closed

The driver asked, before a new test build, for every module to be checked
against *what the car is actually doing on track* — the rear-rebound
lesson generalised. **The signals came through clean**: push/snap is
textbook slip-angle differential (`frontSlip − rearSlip`, ±2.2° at
>0.45g), and lockups, wheelspin and diff signals all come from slip
ratios that genuinely measure the phenomenon. What did *not* come through
clean were three more **levers that could only turn one way** — the exact
defect behind rear rebound — plus a mislabel and a misnomer.

### Audit results

| module | verdict |
|---|---|
| ARB, rake, toe, brake bias, differential, springs, pressures, camber, rear dampers, bottoming, gearing | **sound** — left alone |
| Front slow dampers | **acceptable** — still histogram, but front bump/rebound counts are near-balanced in every real log (34/38, 106/113, 22/21), so it isn't structurally biased like the rear was; AC's front-rebound tooltip describes a per-car trade with no blanket rule |
| **Wings** | **one-way ratchet — fixed** |
| **Fast dampers** | **one-way ratchet on bumpy tracks — fixed** |
| Rear low-speed rake | **label lied — fixed** |
| `coastPush` | **misnomer — renamed** |

### The fixes

**1. Wings.** Direction was hard-coded `+1` for both. Front rose on every
high-speed push, rear on every high-speed snap, *both* fired in the same
Build when both crossed threshold, and nothing could ever bring either
down. A mixed car at high speed walked both wings to max and paid in drag
on every straight. Real log: front splitter pinned at max, rear wing
`5→6→7`. Aero balance is a **ratio**, like ARB: push is cured by more
front *or* less rear, and less rear costs less drag. Now mirrors the ARB
writer exactly — prefer adding to the axle that wants more, but if that
wing is near max, reduce the *other*; when both signals fire, act only on
the larger and name the other; near-max snapshotted once before either
writes (the v1.4.1 self-cancellation lesson).

**2. Fast dampers.** Without bottoming, direction was always *softer* —
but fast events measure "this track has kerbs," not "these dampers are
too stiff," so they walked to the schema minimum Build after Build. Real
logs: fast rebound `185→175` (the Ferrari's floor, in **one** press),
`21→18→17→16` over three Builds on the Lotus, fast bump `81→68→66`. AC's
tooltip: too-low fast rebound "can provoke a bouncing of the tyres …
making the front end lose grip on bumps and kerbs." The soften direction
is now **floored at the control's factory default** (`defaultValue` from
the live spinner API). Stiffening for bottoming is untouched. The driver
noted fast rebound rarely fires — correct, 6 writes vs 70 for fast bump —
but when it does, the Ferrari case shows it hitting the floor in a single
press. **v2.6.1: the whole kerb softener is removed** (Nik: "it's useless.
abolish it.") - fast dampers move only through the bottoming chain's
fastBump lever, and the panel no longer advises softening them.

**3. Label.** Low-speed oversteer lowers the rear — correct, less rake
counters oversteer — but the log line said *"more rake"*, a copy-paste of
the front/push branch. Action right, description wrong.

**4. Rename.** `coastPush` → `liftOffSnap`. It's counted inside the
*snap* branch, gated on `gas < 0.15`: lift-off oversteer, nothing to do
with push. Diagnostic only, but it sat in the experiment line under a name
pointing the wrong way.

Verified in `test_wing_and_fast_damper.lua` (28 checks) against the real
tester session and the real Ferrari/Lotus fast-damper sequences.

**The pattern worth naming:** four of the five defects found today
(rear rebound, wings, fast dampers, and arguably rear toe's one-way
nature) share one shape — a rule whose output never depends on the
handling signal, only on an event count, so it resolves the same way
every time. *A "balance" rule that always resolves one way isn't
measuring anything.* Worth checking any future writer against that
before trusting it.

## v1.9.3 — REAR DAMPER DIRECTION, fixed

The one this project got wrong the longest. Fixed on the driver's
go-ahead after holding for more tester logs.

**What was wrong.** The slow-damper writer used a pure event-histogram:
whichever side has more velocity-threshold crossings is "comparatively
soft", so stiffen it. That's a damper-symmetry heuristic with no knowledge
of what the car is doing — and on the rear it was structurally biased,
because rebound events out-number bump events in *every* real session
logged (216 vs 46, 110 vs 25, 45 vs 20). So the rear branch almost always
resolved to "stiffen rear rebound." A tester's 461-corner session with
**265 oversteer events** got rear rebound stiffened `24→28`. AC's own
tooltip for that control: higher rear rebound = *"less stable under
braking and initial turn in."* The app was making a loose car looser, by
design, on every Build.

**The fix.** On the rear axle, the **handling signal decides direction**;
the histogram is only the fallback when neither oversteer nor understeer
clearly dominates (25%+ margin, above threshold):

| rear handling | rear rebound | rear bump | AC tooltip basis |
|---|---|---|---|
| **loose** (snap ≫ push) | **softer** | **softer** | lower rebound = "more stable at initial turn in"; lower bump = "more traction and stability on brake release" |
| **tight** (push ≫ snap) | **stiffer**, within 30% of limit | untouched | higher rebound = "much more agile on slow turns that need the whole car to rotate" — but also less stable under braking, hence headroom |
| neither | histogram, unchanged | histogram | — |

Front axle deliberately untouched — AC's front-rebound tooltip describes a
genuine per-car trade, so the histogram stays the honest fallback there.
Bottoming override (stiffen both) still takes precedence over everything.

**One shared function** (`rearHandlingSignal`) feeds both the REAR DAMPERS
advice item and the writer, so the panel can never promise one direction
while Build does another. Verified in `test_rear_rebound_direction.lua`
(19 checks): both real tester sessions flip stiffen→soften; a pushing car
stiffens; a mixed car is byte-identical to old behaviour; the 25% margin
is enforced; and the source guards assert one definition, two call sites.

The REAR REBOUND EXPERIMENT log line stays, repurposed: it should now show
snap rates **falling** across sessions as rear rebound falls on loose cars.
If it doesn't, that's the fix not working, and that line shows it first.

**Credit where due:** the driver held this position from the first
session, against the histogram logic, and was right. It took AC's own
tooltip to end the argument — and it should have been read first.

## v1.9.2 — three fixes from a real tester's log, plus a discoverability fix

From a tester's log (`kinkl`, `ferrari_458_gt2`), the first real validation
of v1.9.x's live-setup read on the Ferrari — and it caught two real bugs.

**1) REAR REBOUND EXPERIMENT was logging the WRITTEN value as "as
driven".** The line exists to record the rebound setting the car *actually
ran*, independent of what Build was about to do — but it read `parsed`
from inside `logLines`, built at the very end of the function, by which
point every writer had already run. Proven directly: Build wrote rear
rebound `24→28`, and the line reported **28** as driven. Every prior
session's row was contaminated the same way whenever rear rebound actually
got written — likely common, given v1.6.0/v1.9.1's history. Fixed by
snapshotting the three damper values right after the live-setup sync
settles `parsed` to what was actually run, before any writer can touch it.

**2) `DAMP_REBOUND_LR/RR`'s baked min was still one off.** v1.9.1 used
`ceil(MIN/STEP)` = `ceil(3780/360)` = 11, but the same log's `liveSetup:`
line reported the real minimum as **10**, straight from
`ac.getSetupSpinners()` — ground truth, not inference. Switched to
`floor(MIN/STEP)` for both bounds; now matches the live spinner exactly.
Pinned as an exact-match check in `test_damper_ranges.lua`, since this is
the one field with a live-verified precise bound.

**3) "OPEN NOTES FOLDER" button**, by direct request — testers were
struggling to find `SetupCoach_Notes`. The path was already resolved
correctly (`findDocsRoot` uses CSP's own `ac.FolderID.ACDocuments`, which
follows a moved or OneDrive-redirected Documents folder the same way the
game itself does) — the problem was pure discoverability, not detection.
One button, next to RESET TELEMETRY / SAVE PIT NOTES, creates the folder
if needed and opens it in Explorer (`os.openInExplorer`). Falls back to
showing the resolved path as text if the open call ever fails.

**Deliberately not done:** item 4 (acting on the in-game damper direction
evidence) — holding for more tester logs first, by request. The same log
that fed these fixes also shows it happening live: a 461-corner session
with `midSnap=265` (heavy oversteer) where Build stiffened rear rebound
`24→28`, the opposite of what the tooltip evidence says helps.

## v1.9.1 — baked damper ranges corrected (v1.6.0's finding retracted)

AC's own in-game damper tooltips quote `ferrari_458_gt2`'s factory
defaults: rear rebound **26**, front rebound **29**, front bump **39**,
rear bump **24**, front fast rebound **185**, front fast bump **81**.
Every one sat *outside* the range v1.6.0 baked (22/22/20/20/15/22). A car's
own default cannot be out of its own range.

**The wrong ranges did real damage**, not merely nothing: with fast bump
baked at `0..22` against a true `66..88`, a Build clamped this driver's
front fast bump **88 → 22** and rear **64 → 20** — far below the legal
minimum, while claiming to protect them from values that were never out of
range.

**Cause.** `readSetupItem` maps every `SHOW_CLICKS` field to a click index
`0..numSteps` (physical = `MIN + index*STEP`). These dampers instead store
a **count of steps from zero** (physical = `value*STEP`), so the legal
stored range is `ceil(MIN/STEP)..floor(MAX/STEP)` — rear rebound `11..32`,
which contains the 26 default. Verified against two independent sources:
all six tooltip defaults, and every damper value in the driver's real setup
files (185, 101, 88, 64, 43, 34, 32 — all inside the new ranges, all "out
of range" under the old).

**Not universal, and deliberately not inferred.** `lotus_exos_125_s1`'s
dampers *are* click-index (proven by the live spinner returning `[0..24]`
for an ini of `MIN=7000 MAX=19000 STEP=500`), and the Ferrari's own toe
fields are click-index too despite sharing `SHOW_CLICKS=1` with its
dampers. Per-field conventions genuinely differ, so the rule is recorded
per car from that car's own numbers in `gen_baked_schema.py`'s
`CONFIRMED_DAMPER_UNITS` — the same evidence-first pattern as camber units.

**Guard:** `test_damper_ranges.lua` asserts the car's defaults and observed
values all fall inside the baked ranges, read out of the shipped file. One
invariant — *a default cannot be out of range* — catches a wrong unit
conversion without needing to know which conversion is right. Verified to
fail against v1.6.0's numbers.

Scope note: v1.8.0 already prefers the live spinner's `min`/`max` over
anything baked, so only sessions where that read is unavailable ever
reached these numbers.

## NEXT PHASE — review list

Parked deliberately during alpha testing rather than churning the build.

**1. ~~`manifest.ini` VERSION mismatch~~ — FIXED 2026-09-29 (v2.5.0).**
The manifest says `VERSION = 2.5.0` and the release routine bumps it with
every version (`make_release.ps1` refuses a mismatch). The reason it was
parked went away when Nik asked for releases as a zip, which carries both
files anyway. Original note: the manifest said `VERSION = 2.0.2`
while the app reports `v1.9.0`. Content Manager displays the *manifest*
value, so testers will report "2.0.2" and muddle bug reports. Cosmetic and
zero-risk to behaviour — but fixing it means every tester takes both files
rather than just `SetupCoach.lua`, which is the only reason it's parked.
Legacy of the numbering before the deliberate 4.9.1 → 1.0.0 relabel.

**2. `windowHud` is dead code in practice.** (v1.9.2 added
`os.openInExplorer`/`io.createDir` calls, pcall-guarded and NOT yet
verified in a real session — worth checking their result once a tester's
log or report confirms the button actually opened Explorer, since that
would also settle whether this app's I/O permissions extend that far.) The app defines
`script.windowMain`, `script.windowHud` *and* `script.windowSettings`, but
`manifest.ini` declares only one window (`FUNCTION_MAIN = windowMain`). The
HUD window has therefore never been able to appear — same root cause as the
settings window being unreachable (v1.7.5). A compact in-race HUD would be a
one-line manifest addition plus verifying `windowHud` still renders (it
hasn't run in a long time — treat as unverified). This also suggests the
settings-gear problem might be solvable by declaring the window in the
manifest rather than relying on CSP auto-wiring it.

**3. ~~Baked damper ranges are WRONG~~ — FIXED in v1.9.1** (kept for context). See the correction at
the top of the v1.6.0 section. AC's own damper tooltips give factory
defaults (rear rebound 26, front rebound 29, front bump 39, front fast
rebound 185) that all exceed the baked maxima (22/22/20/15). The
SHOW_CLICKS→click-index conversion in `readSetupItem` and
`gen_baked_schema.py` is wrong for these fields, and the correct rule is
not inferable offline (a `MIN/STEP..MAX/STEP` rule fits all six dampers
but breaks toe). **Do not derive a third rule.** Delete the baked damper
entries — v1.8.0's live spinner read already supersedes them and is
consistent by construction — and confirm against one real Ferrari
`liveSetup:` log line. Until then, any session where the live read fails
clamps rear rebound to 22, below the car's own 26 default.

**4. ~~Act on the damper direction now that the game has answered it~~ — DONE in v1.9.3.** Original note: See
"In-game damper guidance" below. Rear rebound is the live one: the app
currently STIFFENS rear rebound when rebound events outnumber bump events,
and the game states higher rear rebound makes the car *less* stable under
braking and initial turn-in. Also worth wiring in: higher rear BUMP gives
more oversteer on throttle and brake release, lower gives more traction —
a lever the app doesn't currently reason about in those terms.

**5. ~~Correct the v1.6.0 entry in `SetupCoach.lua`'s changelog~~ — DONE in v1.9.1.** Original note:
the same way as CLAUDE.md. Deliberately not done yet: it's comment-only,
but editing the installed file mid-alpha changes its hash and would
diverge from what testers are running.

Plus, carried over from alpha: rake's weak real-world effect, and
`ac.getCarPhysics().gearRatios` returning nothing on `lotus_exos_125_s1`
(`gearPhysDiag` will explain it).

## In-game damper guidance (Assetto Corsa's own tooltips)

First-party, verbatim from the setup screen on `ferrari_458_gt2` — the most
authoritative damper reference this project has, and it settles a question
that was open for the whole of alpha.

| lever | higher | lower |
|---|---|---|
| **Rear rebound** | **less stable under braking and initial turn-in**, but much more agile on slow turns needing the whole car to rotate | stable at initial turn-in, but can provoke inertia movements of the rear on chicanes / fast direction changes |
| **Front rebound** | more stable under acceleration and on fast direction changes | eliminates understeer under acceleration, but more sluggish changing direction |
| **Rear bump** | more reactive, better precision, but **more oversteer under acceleration or on brake release entering a turn** | more predictable, slower reactions, **more traction and stability on brake release**; lowers tyre temp/wear |
| **Front bump** | more reactive, better precision, stability under braking; higher tyre temps and wear | more predictable but slower, less precise, less stable under braking; lowers tyre temp/wear |
| **Front fast rebound** | slower extension, limits shock from a compressed spring; too high and it can't extend after a kerb — front stays low (good aero, but no travel left for the next bump) | extends freely, but can bounce the tyres and lose front grip over bumps/kerbs |
| **Front fast bump** | absorbs less kerb impact but limits spring compression, so the spring can't load up and bounce back violently; makes the front nervous over kerbs | absorbs more energy over bumps/kerbs, but must not bounce back down and upset the car |

**Why this matters:** "higher rear rebound = less stable" confirms the
driver's position, held all session and supported by Koni's tuning guide,
Suspension Secrets, and this project's own v1.0.1 finding. The app's
damper-histogram logic stiffens the side with more events, which on the
rear axle pushes *against* this. That was left deliberately unresolved
pending data (the REAR REBOUND EXPERIMENT line, v1.6.0) — the game has now
answered it directly.

## v1.9.0 — ALPHA BUILD COMPLETE

Differential, aero and brake bias split into three independent toggles, by
request: *"these 3 modules should have separate tickboxes. if we can fix
that, i think we can call this our Alpha Build complete."*

They'd shared one switch (`writeDiffAeroBrake`) since v1.4.0 pulled them
out of Build's default scope and v1.5.0 put them back. Three levers on
three unrelated subsystems had no reason to share a switch once every
other module had its own — freezing a dialled-in brake bias also froze the
wings. Now **14 independent module toggles**, all defaulting on.

The old key survives for one purpose: a migration that runs at most once,
carrying a deliberate "I turned that off" across to all three, then
consuming itself. Same principle as backing out v1.7.8's forced all-on
reset — an explicit choice is never quietly reverted.

### Alpha scope, as it stands

- Live telemetry analysis across **19 advice modules**, with per-sector
  attribution where the track exposes sectors.
- Build writes **14 independently toggleable modules**, each clamped to the
  car's *real* limits, starting from the car's **actual current setup**
  (v1.8.0) so repeated Builds accumulate instead of repeating.
- Gearing, fuel, compound, TC, engine limiter and brake power are read and
  advised on but **never written** (v1.8.1).
- Car data read live where CSP allows, with offline-decrypted fallbacks
  (`DCAMBER_LOOKUP`, `AERO_LOOKUP`, `BAKED_SETUP_SCHEMA`) for what it doesn't.
- Self-explaining debug log: every counter, gate, data source and fallback
  that fed a Build, recorded at the moment Build was pressed.

### Known open items, deliberately not closed for alpha

- ~~**Rear rebound direction** is still unresolved~~ — **ANSWERED
  2026-09-13** by AC's own in-game tooltips (see "In-game damper
  guidance"): higher rear rebound makes the car *less* stable under
  braking and initial turn-in. The app's logic still pushes the other way;
  acted on in v1.9.3 - the rear axle's direction is now handling-driven.
- **Rake's real-world effect** remains weaker than expected (v1.6.0 ruled
  out clamping as the cause).
- **`ac.getCarPhysics().gearRatios`** has been seen returning nothing on at
  least one car; `gearPhysDiag` (v1.7.3) exists to explain it.

## v1.8.1 — v1.8.0's sync was too broad and rewrote GEARING

Reported immediately and correctly: *"gearing shouldnt be getting changed
by the app - only recommend shortening or lengthening final gear."*

v1.8.0 synced **all 62** sections the game reported into the output file.
Only about half are things this app reasons about; the rest — gear ratios,
fuel, tyre compound, traction control, engine limiter, brake power — it has
no business writing. On a real session that changed four `INTERNAL_GEAR_n`
values and **added** an `INTERNAL_GEAR_1` section the driver's setup never
had. GEARING has never had a writer by design; v1.8.0 gave it one by the
side door.

**Fix:** `MANAGED_SECTIONS`, derived at load time from `SETUP_PROBE` so it
can't drift from what the writers actually handle. The live sync touches
only those. Everything else is read, reasoned about, advised on, and left
exactly as the base file had it. The `liveSetup:` log line now reports the
unmanaged count, so "left alone incl. gearing" is visible per Build.

GEARING's two actionable lines now name the **final drive** as the lever
and state outright that Build never writes gearing.

Guarded by `setupcoach-tools/acd/test_managed_sections.lua`, which reads
`MANAGED_SECTIONS` out of the real source rather than restating it (a
hand-copied list would drift and only ever prove itself right), asserts
every gear/fuel/compound/TC section is excluded, asserts the tuned sections
*are* included so it can't pass vacuously, and asserts every actionable
GEARING line carries the advice-only wording. Verified to fail when a gear
section is deliberately let into `SETUP_PROBE`.

**v1.8.0's core idea is confirmed working in a real session** — the live
read returned 62 self-consistent sections, `CAMBER_LF` range `-60..10` with
`displayMultiplier 0.1` (= -6.0°..+1.0°, exactly matching that car's
decrypted `setup.ini`), and a live `PRESSURE_LF` of 16 with a real 8–20
range on a car that previously had **no readable schema at all**. The
mistake was scope, not approach.

## v1.8.0 — Build starts from the car's ACTUAL setup, not a file

**This is the root cause behind most of what went wrong this week**, and
the driver diagnosed it: *"any last.ini are saved on session exit, so they
dont write until i leave. To have the optimal setups accumulate then data
needs to be from what's currently set to the car."*

Every Build nudged from `findTemplateSetup`'s `last.ini`, which AC only
writes when a session **ends** — so mid-session the base never moved.
Eight consecutive Builds in one real session produced byte-identical
output: ARB `30→34`, ride height `24→23`, toe `12→13`, pressure `base 20`
every time. Builds weren't accumulating; each was the same first step
re-taken. It also meant unticking a module wrote that stale file's value
rather than what the car was running — how unticking pressures produced
**20 psi, that car's literal maximum**, on a car being run at ~16.

**The fix.** `ac.getSetupSpinners()` (CSP's shipped SDK) returns every
setup item as `{name, label, min, max, step, value, displayMultiplier,
readOnly, units, showClicksMode}` — `name` matches setup INI section names,
`value` is what's on the car *right now*. Live values are synced into the
parsed base document in **one place**, so every writer picks them up via
the `getCurVal()` it already calls. No call site changed. Five problems
close at once:

1. **Builds accumulate** — the base is the car, not a file.
2. **"Untick = leave it alone" is literally true** — untouched sections
   carry the live value into the output.
3. **`schemaLimited` cars get real `min`/`max`/`step`** for the first
   time, so the unclamped nudge path (which walked one car's rear rebound
   to 78 against a real limit of 22) is unreachable.
4. **Camber units stop being guesswork** — `displayMultiplier` is the
   game's own raw→degrees factor; its reciprocal is the scale this file
   spent three versions inferring, and it reproduces the driver-confirmed
   case exactly (`-3.5°` stored as `-35`).
5. **No decryption needed** for any of it.

`ac.INIConfig.currentSetup()` is deliberately **not** used — its own docs
warn pit changes aren't reflected unless the file was saved: the same
staleness, one layer along.

**Safety.** This replaces the core data source and can't be verified
outside a running game, so: `pcall`-guarded, every field type-checked, and
the **whole read is rejected unless self-consistent** — any value outside
its own reported `min`/`max` proves those numbers aren't in the same unit
space, and clamping against them would be meaningless (exactly the trap
`setup.ini` sets by declaring camber `MIN`/`MAX` in degrees while `VALUE`
is tenths). On rejection or unavailability the old template path takes
over unchanged. A new `liveSetup:` debug-log line reports what came back,
so **one session settles this** rather than another round of inference.

Logic verified in `setupcoach-tools/acd/test_live_setup.lua` (15 checks,
including the guard rejecting mixed unit spaces). That test states plainly
that it validates logic against an *assumed* API shape — because a stub
encoding an assumption is what let the v1.7.6 checkbox bug through twice.

**Revert point:** `SetupCoach_1.8.0_backup_preinstall.lua` holds v1.7.8.

## v1.7.8 — "All on" button, and a corrected assumption

Request: "maybe it would be better if the initial setting was all modules
on, so they could be unchecked as the setup progresses."

The first attempt was a **one-time forced reset on upgrade**, justified by
assuming v1.7.4–1.7.6's `ui.checkbox` bug had scrambled everyone's toggles
behind their back. The driver corrected that directly: *"i ticked the
boxes myself and left some unticked, that's not an error."* The premise
was wrong, and the behaviour it justified — silently overwriting
deliberate choices on upgrade — would have been exactly the wrong thing
to ship. Backed out entirely.

What actually fits: fresh installs **already** begin all-on (every default
is `true`), so nothing was broken for a new user. What was missing is a
way to return to all-on when *starting a new car or track*, before
progressively freezing modules again as each is dialled in — a recurring
need a one-time migration would have served exactly once. So: a plain
**"All on"** button under the checkbox list. Nothing automatic; an un-tick
is never overridden without being asked for.

**Also fixed a false positive in v1.7.7's own new test guard**, caught the
first time it ran against real code. The clicked-pass check asserted that
*every* boolean in a settings table must flip — wrong, since settings
legitimately hold booleans that aren't checkboxes (it tripped on a
migration marker). It now counts how many checkboxes were actually drawn
and asserts exactly that many settings changed, comparing like with like.
Both guards re-verified to still fail on deliberately broken copies
afterwards — a guard that has never been shown to go red proves nothing.

## v1.7.7 — the actual cause: `ui.checkbox` returns *clicked*, not value

Found by reading CSP's own shipped SDK definition instead of guessing a
third time (`extension/internal/lua-sdk/ac_apps/lib.lua`):

```lua
---@return boolean @Returns `true` if checkbox was clicked.
if ui.checkbox('My checkbox', myFlag) then myFlag = not myFlag end
```

So `flag = ui.checkbox(label, flag)` sets the flag true on the frame you
click it, and **false on every frame after** — precisely "tick the box,
the menu flashes briefly and vanishes." v1.7.6's `ac.storage` theory was
simply wrong; storage was never involved. (`ui.slider` *does* return the
value — `@return number @Possibly updated slider value` — so every slider
here was always fine. Only checkboxes were wrong.)

**All 17 checkbox call sites had it**, including four long predating the
module toggles (Show kPa, Hide OK items, Use temp analysis, Sample in
replay). Never noticed because they all live in `windowSettings`, which
(v1.7.5) appears never to render for this app — so those lines never ran
and stored defaults survived. The module toggles were simply the first
checkboxes this app ever drew in a window that genuinely displays. Latent
severity worth noting: had `windowSettings` ever rendered, it would have
silently forced `writeDiffAeroBrake` false a frame later, quietly
disabling differential/aero/brake writing.

Fixed with one local `checkbox(label, value)` helper wrapping the
documented idiom and returning the value the flag should now have, so
`flag = checkbox(label, flag)` reads naturally *and* is correct.

**Tooling lesson — the part worth keeping.** v1.7.4 added the smoke-test
stub `checkbox = function(label, cur) return cur end`, which encoded the
*wrong assumption*, so the test cheerfully validated broken code twice. A
stub mirroring your own belief rather than the real API is worse than no
stub. `smoke_test.lua` now models CSP's real return semantics and adds two
regression guards — **both verified to actually fail on deliberately
broken copies before being trusted**:
1. drawing the settings window with nothing clicked must not change any
   persisted boolean (catches this exact bug), and
2. drawing it with everything clicked must flip every one (catches the
   opposite — a checkbox dead to click).

Coverage boundary, documented in the test: both guards detect the broken
idiom only via flags whose value differs from what broken code forces
(false unclicked / true clicked). This file's 12 default-true write
toggles make that immediate, but a file of only default-false flags could
slip through the unclicked pass.

## v1.7.6 — v1.7.5's expand toggle itself was broken

Reported immediately: "tried to tick the box but whatever menu is
supposed to be loading flashes briefly and vanishes." The checkbox
controlling the inline module-toggle list in `windowMain` had been stored
in `settings` — an `ac.storage`-backed, persisted table — and it was a
**brand new key** with no existing value in the already-saved settings
file on disk. The exact symptom (draws for a moment, then immediately
collapses) matches a storage write not completing before the very next
frame reads the field back — a class of bug that can't be fully diagnosed
from outside a running game.

Rather than chase the exact `ac.storage` mechanism, moved the field off
storage entirely: it's now a plain `engine.showModuleToggles` field, same
as `engine.setupMsg`/`engine.exportMsg` and other UI-only state already
in this file that never needed to survive an app restart. A plain
in-memory field can't have a storage round-trip race at all.

**Two real bugs in a row from the same change** (v1.7.4's unreachable
`windowSettings`, now this) — not because the checkbox logic was wrong
either time, but because both live in surfaces (CSP's settings-popup
wiring, `ac.storage`'s first-write behavior) this project has no way to
test except by shipping and waiting for a real session's report. Worth
being more conservative next time: prefer plain `engine` fields for
anything that's genuinely just UI state, and don't assume a new persisted
settings key round-trips correctly until it's actually been confirmed
working in a session.

## v1.7.5 — v1.7.4's checkboxes were unreachable

Fixed within the hour of shipping v1.7.4: "dont see any boxes to turn off
the option of those modules". Not a bug in the checkboxes themselves —
`windowSettings` ran clean in the smoke test (which now genuinely calls
it, added for v1.7.4). The real issue: `script.windowSettings` is CSP's
own special popup, normally reached via a small gear icon on the app's
title bar — and this project's `manifest.ini` declares only one
`WINDOW_` entry ("main"); `windowSettings` is just a reserved function
name CSP is *supposed* to hook up automatically, with no way to confirm
from outside a running game that it actually was for this app.

Rather than debug a game-side icon that can't be inspected remotely, the
same checkboxes moved to somewhere guaranteed reachable: a collapsed-by-
default **"Which modules does Build write?"** toggle directly in
`windowMain`, right above the BUILD OPTIMAL SETUP button — exactly where
a driver is already looking. The checkbox list is defined once
(`drawModuleToggleCheckboxes`) and called from both `windowMain` and
`windowSettings`, so there's no risk of the two drifting apart —
`windowSettings` keeps showing them too, in case the gear icon does exist
for whoever prefers it there.

## v1.7.4 — per-module write toggles

Direct request: "tickboxes for the modules... if unticked, that module
will not be touched, remains at the current value... once a module is
satisfactory it can be left at the desired value." New Settings section,
**Build writes these modules**, one checkbox per module. Unticking one
makes Build skip it entirely — the value stays exactly what's already in
the setup file, even while the live advice panel keeps flagging it. Only
the *write* is gated, same convention the pre-existing `writeDiffAeroBrake`
toggle already used — advice text is unaffected either way.

**Granularity** matches the advice panel's own module names wherever the
writer's code already treats them separately:
- Front/rear **dampers** (slow) and **fast** dampers → 4 independent
  toggles, because the writer already loops per-axle for these, and
  it's a genuinely real workflow already seen in this project (rear
  rebound direction has been under active, separate debate from front).
- Front/rear **toe** → 2 toggles, same reason.
- **ARB** deliberately stays ONE toggle, not front/rear — its own logic
  can redirect a push/snap signal to the *other* bar when one is near its
  limit, so a front/rear split wouldn't correspond to anything the code
  actually decides.
- **Packer range** (bottoming's other lever, alongside ride height)
  travels with the **Suspension** toggle — it has no separate advice-panel
  identity of its own to match.
- **Differential/aero/brake bias** keep their existing single combined
  toggle, unchanged — no new reason to split it further.

Full list: Pressures, Camber, Suspension (ride height/rake + packer
range), Springs, ARB, Front/Rear dampers, Fast front/rear dampers,
Front/Rear toe, Differential/aero/brake bias. All default **on**, so
upgrading never silently narrows what an existing setup already relied
on. A new `moduleGates:` debug log line records every toggle's state at
Build time, so a category showing unchanged is immediately explained as
"module off" rather than needing to be puzzled over as a bug.

**Caught before shipping** — worth remembering as a general Lua trap, not
just this bug: the front/rear gate for fast dampers and toe was first
written as `front and settings.writeX or settings.writeY`, the classic
"ternary" idiom — and classically wrong here because the *middle* value
is itself a boolean. When `front=true` and `writeX=false`, `front and
writeX` collapses to `false`, which falls through to `or writeY` and
silently returns the WRONG toggle's value. Caught by hand-tracing all
four true/false combinations before shipping (now a standing test,
`setupcoach-tools/acd/test_module_gates.lua`) and replaced with a plain
`if/else`. `cond and a or b` is unsafe in Lua whenever `a` can itself be
`false` or `nil` — this codebase has no other instances of the pattern
(confirmed by grep across the whole file after the fix).

Also extended `smoke_test.lua` to actually *call* `windowSettings` with
real (if trivial) `ui.*` stubs, rather than only confirming the function
exists — an empty `ui = {}` meant a dozen new `ui.checkbox` calls would
have gone completely unexercised by the dev tooling otherwise.

## v1.7.3 — GEARING's missing "too tall" case

Reported on a new car (`lotus_exos_125_s1` @ Spa): "barely got into top
gear, nowhere near limiter." Two separate gaps.

**1) GEARING was one-directional.** Its only advice ever was "you're
hitting the limiter, get a taller top gear" (`limiterTime > 0.6s`). There
was no check for the opposite, equally real problem — gearing already too
*tall*, never getting near the limiter — so this exact session read `ok`
regardless of how badly undergeared the car was. Fixed with a
mirror-image check: if the highest gear actually driven this session
(`maxGearSeen`) is the gear the car was in at its recorded top speed, and
that speed's RPM sits below 88% of the car's own rev limiter, GEARING now
flags `act` → "shorten top gear".

**2) The physics-API gear-ratio read failed outright on this car** —
`topGear=nil topGearRatio=n/a` for the whole session, no way to tell why
from the log alone. Added `gearPhysDiag`, logging `okPhys`/`isAvailable`/
`gearRatios` presence separately, so the next session on this car
explains itself. The new "too tall" check deliberately does **not**
depend on this read — it uses `maxGearSeen` (tracked independently,
highest gear number actually driven) specifically so it still works when
the ratio read is broken, as it is here.

**Not done: an actual Build-time write for gearing.** It has never
existed, on any car — GEARING has only ever been advice text. This car's
`setup.ini` exposes gearing as `GEAR_1..GEAR_7`/`FINAL_GEAR_RATIO`, each a
`RATIOS=X.rto` reference into a named ratio *set*, not a raw adjustable
number — picking a shorter ratio safely needs that set's real contents
(which direction is shorter, what options exist), not decrypted for this
car yet. Guessing that blind repeats a mistake this project has made
before (damper direction, wing role) and wasn't worth risking for a first
pass — logged as a real, separate next step.

## v1.7.2 — v1.7.1's own diagnosis was wrong, corrected by the user

v1.7.1 treated `CAMBER_LF=-24` as stale garbage because it didn't fit the
ini's literal `MIN=-5`/`MAX=-1.2` taken as real degrees. It wasn't
garbage — the driver had set that corner's camber themselves, and
confirmed it directly: setting **-3.5°** via Content Manager's own camber
slider produced a stored `VALUE` of **-35**, not -3.5. `-24` was always a
perfectly legitimate -2.4°; the app's own v1.6.0/v1.7.0 baked schema had
the **units** wrong, not the driver's setup file.

**Root cause.** `CAMBER_LF/RF/LR/RR` are a well-known Kunos legacy quirk:
`MIN`/`MAX`/`STEP` in the ini describe the slider's real-degree range
(even commented `;degrees`), but `VALUE` itself is stored in **tenths of
a degree** — a ×10 mismatch the ini text never reflects. `BAKED_SETUP_SCHEMA`'s
camber entries were baked straight from the ini's literal numbers
(`min=-5,max=-1.2`), describing the wrong unit — which is exactly why
v1.7.1's sanity check (sound logic, wrong input) misfired: `-24`
genuinely doesn't fit `-5..-1.2` real degrees; it only failed to fit
because the *range* was wrong, not the value.

**Fix.** The four `CAMBER_*` baked entries are now ×10 (e.g. `CAMBER_LF:
-50..-12` instead of `-5..-1.2`), matching `VALUE`'s real stored unit.
This also means the runtime's own existing scale heuristic
(`schemaItem.min` magnitude `> 15` → tenths-of-a-degree) now fires
correctly on its own — no new special-casing needed at read/write time,
just the correct baked numbers. `gen_baked_schema.py` is fixed the same
way for any future re-bake. **v1.7.1's stale-anchor sanity check is
kept** — reasonable safety net for genuinely corrupted future data — it
just no longer misfires now that the range it checks against is correct.
Verified against the real session numbers in
`setupcoach-tools/acd/test_camber_units.lua`: `-24 → -33.5` raw (-3.35°),
`-18 → -29.4` raw (-2.94°), both sensible changes matching the physics
delta exactly — and the user's own `-35` (their own -3.5°) is now
correctly trusted rather than "corrected" away.

**Lesson worth keeping close:** v1.7.1 was a real, reasoned fix for a
real symptom, and was still wrong, because it trusted the ini's own
`MIN`/`MAX` comment over checking what the game/CM actually store. Direct
field evidence — the user setting a value themselves and reporting the
exact before/after — beats a documented convention whenever the two
conflict.

## v1.7.1 — camber's own version of the rear-rebound bug

Reported with real evidence: three actual setup files. The freshly-Built
one had `CAMBER_LF=-5.00`; the two files the driver had actually raced
fastest with carried `CAMBER_LF=-35`. Advice panel states a specific
optimal angle; Build wasn't writing anything close to it.

**Root cause.** Camber is the one module that computes an absolute
physics target (tyre's own peak-grip angle vs. what it measured on
track) and adds that delta to `baseVal`, the value sitting in the
template file. That's fine when `baseVal` is trustworthy — but this was
the *first* session camber ever had a real schema (v1.6.0's bake), and
`last.ini`'s `CAMBER_LF` was still `-24`, left over from every session
before that, written under the old blind heuristic with nothing to check
it against. `-24` isn't a real angle on any car once the true range
(`-5..-1.2`, confirmed straight from the decrypted `setup.ini`:
`MIN=-5 ;degrees`) is known — but the code trusted it anyway, added a
small delta, and clamped: `-24 + delta` lands nowhere near the legal
range, so the clamp just slams it onto the boundary and reports the
boundary as if it were the computed answer. The `-35` in the driver's own
"fastest" files is the same corruption from an earlier session — never a
real degree value either.

**Fix.** `baseVal` is now sanity-checked against the real schema range
before being trusted as the anchor. When it's wildly outside (more than a
full range-width past either bound — comfortably separates "stale
garbage" from "a real value that's just near the edge"), the anchor falls
back to the schema's own midpoint, same fallback this function already
uses when there's no template value at all. From this session's real
numbers, this now writes `-4.05°`/`-2.64°` instead of `-5.00°`/`-3.50°` —
an answer connected to the physics delta, not a boundary artifact.
Verified against the real logged deltas in
`setupcoach-tools\acd\test_camber_anchor.lua`, including a check that a
genuinely near-edge real value (not stale) is left alone rather than
being wrongly "corrected".

Scope: only affects sections that do degrees-based absolute math on top
of a template value — currently just camber, on the one car with a baked
schema. The generic percentage-nudge writer used everywhere else (ARB,
springs, dampers, etc.) has no equivalent unit/anchor ambiguity to get
wrong.

## v1.7.0 — "flooring" (bottoming detection) toned down

Direct field report: reaching zero bottoming flags forced ride height
excessively high, and a little kerb scrape on a real track is normal —
not something the app should be fighting to eliminate. Two separate
problems, both fixed; user was explicit either angle (sensitivity or
priority) was fine, so both were done.

**1) Detector was too sensitive.** Bottoming fired at 92% of physical
suspension travel (`suspensions.ini` TRAVEL) — routine under hard braking
on a stiff race setup, not evidence of chassis contact. Raised to 97%. Far
worse: a bare vertical-G spike (`vertG > 2.8` or `< -0.4`) counted as
bottoming with **no travel-usage check at all**, so a hard kerb strike
(wheel gets slapped, chassis nowhere near the ground) or a crest/
compression (body unloads, suspension nowhere near full travel) were both
logged as bottoming. Both G-triggers (now `3.2`/`-0.6`) additionally
require travel usage ≥85% on the same tick; otherwise they fall through
to the pre-existing "kerb" bucket, which carries no write consequence —
matching the fact that a kerb clip is fine and shouldn't push ride height
up. SPRINGS' own 95%-travel check (stiffen spring — separate, stricter
signal) was pulled out of the nested `if` into its own top-level check:
it only worked before because 95% happened to already imply the old 92%
gate, and raising that gate past 95% would have silently broken it.

**2) Bottoming had absolute priority over rake and everything else.** Any
bottoming signal past the plain per-event threshold (`th`, the Settings
slider, default 2) completely pre-empted rake in the SUSPENSION advice
slot, and Build would always raise ride height — never rake — for as long
as it held. New `bottomTh = th * 2` now gates ride-height raises, the
SUSPENSION advice choice, and the fast-damper stiffen/soften flip
specifically; rake keeps the plain `th`. A marginal/occasional bottoming
signal no longer locks out rake for the rest of the session. **Packer
range widening deliberately stays at the plain `th`** — more room before
the packers costs no ride height or aero platform, so it's the free fix
and doesn't need the higher bar.

Not changed: the underlying counters (bottoming included) still only
reset via the RESET TELEMETRY button — true of every module, not unique
to bottoming, and out of scope here. Worth hitting Reset between
meaningfully different test runs so a bumpy earlier session doesn't keep
biasing later advice; the in-app "adjust one thing at a time" note already
implies this workflow.

## v1.6.0 — the uncapped-nudge bug (BAKED_SETUP_SCHEMA)

> ### ⚠️ CORRECTION (2026-09-13) — the headline claim below is WRONG
>
> The driver shared Assetto Corsa's own in-game damper tooltips, which
> state the car's factory defaults outright:
>
> | field | this section claims max | **game's stated default** |
> |---|---|---|
> | rear rebound | 22 | **26** |
> | front rebound | 22 | **29** |
> | front bump | 20 | **39** |
> | front fast rebound | 15 | **185** |
>
> A car's own default cannot be out of its own range, so the baked damper
> ranges are wrong — and with them the claim that "the car sat at maximum
> rear rebound" for months. Values of 24–30 were **normal**, not silently
> clamped. Only 34/35 were plausibly over.
>
> The cause is `readSetupItem`'s SHOW_CLICKS conversion (ported into
> `gen_baked_schema.py`), which maps every SHOW_CLICKS field to a click
> index `0..numSteps`. That's right for some fields and wrong for these.
> A rule of `MIN/STEP..MAX/STEP` fits all six damper fields — **and then
> fails on toe**, which does fit the click-index rule. So the per-field
> conversion is NOT reliably inferable offline; do not attempt a third
> derivation.
>
> **Already mitigated:** v1.8.0 prefers the live spinner's own
> `min`/`max` (internally consistent by construction, verified exactly on
> `lotus_exos_125_s1`: ini `7000..19000 step 500` → live `[0..24]`), so
> wherever the live read works these baked numbers are overridden.
> **Residual risk:** if the live read fails, the fallback still clamps
> rear rebound to 22 — *below* the car's 26 default — dragging dampers
> down. Fix is on the NEXT PHASE list: delete the baked damper ranges
> rather than re-derive them, and confirm against a real Ferrari
> `liveSetup:` log line.
>
> What below remains TRUE: the unclamped percentage nudge compounds, and
> clamping to real limits was the right response. Only the specific
> numbers and the "pegged at max" conclusion were wrong.

**The most consequential writer bug found so far.** On cars whose
setup.ini isn't readable in-game (encrypted — the normal case, and true
for the test car in every log), the writer had no MIN/MAX to clamp
against, so `writeTuned` nudged a PERCENTAGE of the current value with no
ceiling — and compounded, since each press takes its percentage of the
already-raised value. Simulated from the real observed start value, 8
presses takes rear rebound 24→28→32→37→43→50→58→67→78. The car's real
limit, from its own decrypted setup.ini, is click index **22**. Every
rear-rebound value in months of logs (24, 26, 28, 30, 34, 35) was already
past it — AC silently clamps on load, so the car sat at maximum rear
rebound while the log kept reporting "26 → 30" as real changes. That also
explains why stiffening never balanced the bump/rebound counts: nothing
was actually moving.

Fixed with `BAKED_SETUP_SCHEMA` — the real schema, extracted offline via
this project's decryptor and generated by `gen_baked_schema.py` so values
are drop-in identical to the live reader's output (SHOW_CLICKS index
conversion included). Applied per-SECTION wherever live can't supply one.
**No writer logic changed** — the existing clamp just has real numbers
now. Verified by simulation: first press pulls the out-of-range 24 back
DOWN to 22, then stops writing rather than logging phantom changes.
`schemaSource=` in the debug log says `live`/`baked`/`live+baked`/`none`.

Regenerate for another car: decrypt it, then
`python gen_baked_schema.py <car_id>` and paste the block in.

**Explicitly NOT fixed by this**, worth not conflating:
- *"Rake isn't doing much"* — checked, different cause. `ROD_LENGTH` is
  genuinely 0–50 front / 0–60 rear and observed 17→19→21 values sit well
  inside it, so ride height was never clamped. The small steps are just
  what a percentage nudge yields from a base in the teens. Still open.
- *Whether stiffening rear rebound is right at all* — real sources (Full
  Grip Motorsport, Suspension Secrets) and this project's own v1.0.1 Koni
  finding both say excess REAR rebound stiffness makes a car loose,
  arguing the balance logic pushes the wrong way on that axle. NOT
  changed on secondary sources alone, given this project has had damper
  direction backwards twice. Instead the debug log now carries a **REAR
  REBOUND EXPERIMENT** line: rebound as actually driven, next to
  midSnap/highSnap/spinR/coastPush and rear dy, all per 100 clean corners
  so different-length sessions compare directly. Read it as a trend
  across sessions at genuinely different rebound settings — if snap/spin
  rates rise as rebound rises, the logic should flip.

## v1.5.0 — four changes after a week of real testing, by direct request

- **`writeDiffAeroBrake` now defaults to `true`** — v1.4.0's narrower
  default didn't hold up to a week of real use. Toggle stays for anyone
  who wants the narrower scope back.
- **Camber's DCAMBER route no longer needs a fresh static capture.** The
  gate was `if peakAngle and curStatic`, but curStatic was only ever used
  downstream for a unit-scale derivation that already had a complete
  fallback chain — the gate was stricter than the code beneath it needed.
  One missed pit-stop capture used to silently downgrade the WHOLE
  session to the thermal-spread proxy (wide 0-12°C dead zone, reads "in
  the window" across a real range of static settings). Separately, and
  worse: **the advice panel had always used the thermal method only**,
  never DCAMBER, regardless of whether real coefficients existed — fixed
  to share the writer's own DCAMBER verdict (±0.05° dead zone) when
  available.
- **`AERO_LOOKUP` added**, same pattern as `DCAMBER_LOOKUP` and the same
  reason: the live aero.ini read is confirmed dead in practice on real
  encrypted cars (`aeroLutChecked=false` in every real log seen), despite
  offline decryption confirming real data exists. Seeded with
  `ferrari_458_gt2` (front/diffuser peak 0.050m, dynamic controller on
  diffuser/SPEED_KMH) via `acd_decoder.py`. Also: the AERO caveat's
  peak-height note was nested inside the `aeroLutRisk` branch, which only
  ever reflects the live read — meaning it could never show on exactly
  the cars needing the baked fallback. Fixed to show whenever a peak
  height is known, either source.
- **GEARING now tracks only top gear (+ the one below it)**, not every
  gear — the old live per-gear measurement system (clutch-gated,
  15-frame streak) is retired outright; it never once produced a value in
  any real session logged this project. `ac.getCarPhysics().gearRatios`
  index-vs-`car.gear` alignment, open since v1.2.0, is now trusted rather
  than flagged unconfirmed: consistent, physically sane, monotonically
  decreasing values across multiple real sessions on the same car.

## ARB self-cancellation bug (v1.4.1) — found via v1.4.0's own diagnostics

v1.4.0's raw-counter logging immediately paid for itself: a real tester
session (ferrari_458_gt2, Interlagos, midPush=69 AND midSnap=94 both above
threshold in the same Build press) showed `ARB rear: 5 -> 6` immediately
followed by `ARB rear: 6 -> 5` in the same changes list - two logged
"changes" that netted to zero. Cause: the push and snap ARB writers each
called `nearMin()` live against the setup file being built, so whichever
ran SECOND could see the FIRST one's just-applied write and reverse its
own decision as a result (front was near minimum, so push redirected to
stiffening rear; snap then saw rear no longer looked near-minimum and
softened it straight back).

Fixed by snapshotting both bars' near-minimum status ONCE, before either
signal writes anything. When both signals genuinely want the SAME bar
moved in OPPOSITE directions (a real mixed-balance car), only the larger
signal by raw event count wins, with an explicit note in the change
description about the smaller one being left for the next Build. Traced
against the exact real numbers from that session
(midPush=69 vs midSnap=94, front already near minimum) - confirms rear ARB
now correctly softens (the oversteer fix, since 94 > 69) instead of
stiffening-then-cancelling.

## Build's write scope (v1.4.0) — settings.writeDiffAeroBrake

Build now writes pressures -> suspension/rake -> springs -> dampers (slow+
fast) -> ARB -> camber -> toe by default, and stops there. Differential,
wing (aero), and brake bias stay advice-only (still shown and explained in
the panel, just not auto-written) unless `settings.writeDiffAeroBrake` is
turned on in the Settings screen (off by default). This was a deliberate
request, not a bug fix - it draws the write boundary at the same
"mechanical platform + alignment" vs "drivetrain/aero/brake balance" line
`buildAdvice`'s own header comment has described since 3.0.0.

This came out of investigating a tester report of "only pressure/camber
wrote despite the panel showing several [act] items". That investigation
found and CONFIRMED a real historical version of this exact bug in this
project's own local `debug_log.txt` (2026-09-08 21:27:13, 26 skip lines,
all pre-auto-template-detection era messages) - already fixed hours later
that same night, well before this session and well before the tester's
build. The tester's own log carried none of that old signature (template
found, zero skip lines for the un-written categories), pointing at "those
counters genuinely hadn't crossed threshold yet at Build time" rather than
a live regression - but that was never fully provable from the log as it
existed. Fixed by also logging the raw event counters (bottoming, damper/
ARB/toe/lockup counts) at the moment Build is pressed, so this is directly
readable from the log next time rather than inferred from a screenshot's
unknown timestamp relative to the last Build press.

## First real tester session (v1.3.0, ferrari_458_gt2 @ Interlagos)

A tester's `debug_log.txt` gave two real, field-confirmed data points:

- **`physGearRatios` populated with a physically sane shape**: `2:2.846
  3:2.000 4:1.611 5:1.320 6:1.160 7:1.000` - monotonically decreasing, right
  where a sequential gearbox should be - while the live-measured
  `gearRatios` got nothing at all that session. First real evidence the
  index-vs-`car.gear` alignment question from v1.2.0 is fine (index N ->
  gear N). Worth another session or two of corroboration before actually
  switching GEARING's predicted-rpm text over to it, but this is a good
  sign.
- **`aeroLutChecked=false`, `aeroPeaks front=n/a diffuser=n/a`,
  `aeroDynamic: none found`** on this exact car, despite offline decryption
  this session confirming it genuinely has a `LUT_GH_CL` curve (peaks
  ~48mm) and a `DYNAMIC_CONTROLLER` on the diffuser. ~~Most likely
  explanation: this encrypted car's `aero.ini` isn't on CSP's live
  whitelist for `ac.INIConfig.carData`, the same shape of gap already known
  for tyres.ini's DCAMBER fields, now confirmed to extend to aero.ini too.~~
  **v1.9.5: wrong for the same reason as DCAMBER** — the aero.ini
  `NAME`/`LUT_GH_CL`/`WING`/`INPUT` reads all pass `nil` as the default
  and get a string list back. The aero.ini read was never exercised.
  Switched on in v1.9.6 (it was the `string.lower(table)` crash, not
  `ac.DataLUT11`).
  Degraded exactly as designed (silently falls back to the class-based
  caveat) - not a bug, but a real, now-confirmed limitation worth knowing
  going in rather than assuming the v1.2.0 aero work fires on encrypted
  cars in practice.

Also worth remembering when reading a tester's debug log: the advice panel
is LIVE (whatever's currently accumulated), but the Build writer only ever
sees counters as they stood at the moment Build was actually pressed. A
session with multiple Build presses and continued driving after the last
one will show a panel with more flagged items than what actually got
written - not a bug, just needs another Build press to pick up.

## Verifying on next real test session

Check `debug_log.txt` for: `sectorsAvailable`, `aeroLutChecked`/
`aeroLutRisk`, and (since v1.5.0) the `topGear=.../topGearRatio=.../
secondTopGearRatio=...` line — sanity-check topGearRatio is a plausible
top-gear ratio (often <1.5, sometimes ~1.0 or a touch below for a real
overdrive top gear - the old "1.5-6" range was for gear 2+, not top gear
specifically) and that topGearNum matches the car's actual top gear. If
`topGearNum=nil`, that's the "not in replays/for remote cars" caveat
firing, or `.isAvailable` being false on this car.
- `aeroPeaks`/rideHeight line — sanity-check `front=`/`diffuser=` land
  somewhere plausible (per real GT3 cars checked, ~40–60mm) rather than a
  clearly-wrong number, and that `static front=` roughly matches what the
  in-game setup screen shows for this car's front ride height.
- `aeroDynamic` line — see whether any real car in your collection actually
  fires this (all cars checked so far for this were GT3; unknown how common
  it is outside that class).
- The AERO panel's `live cl F/R` text — sanity-check the numbers are in a
  plausible CL range for the car/class, not wildly off.

## Physics research findings (v1.2.0), from real unencrypted GT3 aero.ini
files — test car's own data is encrypted, so `ks_lamborghini_huracan_gt3`,
`trr_mclaren_720_gt3` and `fsr_audi_lms_evo_ii_gt3` stood in (same
technique the DCAMBER lookup table already used):

- **Front splitter/diffuser `LUT_GH_CL` peaks around 0.045–0.050m** on both
  GT3 cars checked (1.02–1.07× multiplier), with a HARD near-ground stall
  below ~0.038m (near-zero, not a gentle taper) and a steady decline above
  ~0.065m down to ~20% of peak by 0.155m. The rear wing had **no** GH_CL
  curve on either car — rake's aero benefit runs through front+diffuser
  only, never the rear wing.
- **`DYNAMIC_CONTROLLER_N` sections** (not part of the static AOA/GH
  curves) exist on all 3 real GT3 cars checked, all keyed on
  `INPUT=SPEED_KMH` driving the diffuser (`WING=3`). Confirmed concretely
  on the Huracan: +12° extra angle below ~70 km/h, ramping (`FILTER=0.80`)
  to +0° by 120 km/h. Full `INPUT` vocabulary these sections can use (per
  CSP modding references, not all directly observed): `SPEED_KMH, BRAKE,
  GAS, STEER, LATG, LONG, RPMS, GEAR, SUS_TRAVEL_LR/RR, AVG_TRAVEL_REAR,
  LOAD_SPREAD_LF/RF, SLIPANGLE_*/SLIPRATIO_*, OVERSTEER_FACTOR,
  REAR_SPEED_RATIO, WHEEL_STEER_DEG, CONST`.
- `ac.getCarPhysics(carIndex)` (`ac.StateCarPhysics`, confirmed in CSP's
  shipped type definitions) exposes `.gearRatios[]`, `.gearRatio`,
  `.finalRatio`, `.clutchState`, and `.wings[i].cl/.cd/.aoa/.groundHeight` —
  documented "not available in replays or for remote cars", with its own
  `.isAvailable` field suggesting it can be false even when the struct
  itself isn't nil. `.clutchState` (physics-engine's own computed
  engagement) is a possible cleaner alternative to the ambiguous
  `car.clutch` pedal-position reading for gating gear-ratio measurement —
  not yet used.
- `car.rideHeight[0]`/`[1]` (front/rear, confirmed in **metres** on
  `ac.StateCar`) is real, live ride-height telemetry this project didn't
  know existed until this pass — same units as the aero GH_CL LUT's
  x-axis, which is what makes the peak-height-vs-current-ride-height
  comparison above possible without another unit-guessing exercise.

## data.acd decryption (working, validated)

`D:\Claude\setupcoach-tools\acd\acd_decoder.py` decrypts any encrypted car's
`data.acd` offline. `python acd_decoder.py <car_id> [...]` extracts to
`acd\extracted\<car_id>\`; running it with no args re-runs its self-test.

Getting there took a wrong turn worth recording. Two published community
implementations (`bovis/acd_extractor` Ruby, `0danny/AssettoTools` C#) agree
on the key-derivation math, and that math is CORRECT — but the Ruby one is
wrong about how the keystream is applied, and porting it faithfully produced
garbage on every real car while still passing that repo's own test fixture
(which its own encoder had evidently generated, so it only ever proved
round-trip consistency with itself). The fix came from cryptanalysis rather
than more porting: the cipher is a repeating-keystream subtraction and the
key is a dash-joined decimal string, so every keystream byte is ASCII 45–57
(`-`, `0`–`9`) — only 13 possibilities per position. With ~3000 bytes of
ciphertext each key position gets hundreds of constraints, which pins the
whole key uniquely. `solve_key.py` does this; it recovered a key identical to
what the existing `get_key()` already produced, proving the derivation was
never the problem. The two real bugs:
- **The keystream RESETS per file**, it does not run continuously across the
  archive (the C# reader is right, the Ruby one is wrong).
- **Each original byte is byte 0 of a 4-byte little-endian field.** The Ruby
  "strip any zero bytes from the group" approach desyncs the instant an
  encrypted byte is legitimately `0x00`.

Validated three independent ways on `ferrari_458_gt2`: `PRESSURE_IDEAL`
decrypts to 26/27 psi F/R (matching the live-telemetry figure already in this
file); `DCAMBER_0/1` decrypt to 1.65/−14, **confirming the DCAMBER_LOOKUP
entry for this car against primary data** rather than the community table it
came from; and those coefficients give −1.65/(2×−14) = 3.376°, matching the
3.38° peak this project derived by hand at the start.

**The v1.2.0 aero research is now confirmed on the actual test car**, not
just the GT3 stand-ins: `LUT_GH_CL` present on FRONT (`WING_1`) and DIFFUSER
(`WING_3`), blank on REAR (`WING_2`); front splitter peaks at **48mm**
(1.08×) with the hard near-ground collapse below ~44mm and reaching 0.0 by
155mm; and a `DYNAMIC_CONTROLLER_0` on the diffuser keyed to `SPEED_KMH`,
+12° tapering 40→90 km/h. Every substitute-car finding held.

**Lead worth chasing**: the full `setup.ini` schema (62 sections with real
MIN/MAX/STEP/SHOW_CLICKS) is now readable offline for encrypted cars. This
does NOT remove the app's runtime template-file requirement — ~~in-game the Lua
app still only gets CSP's whitelisted `ac.INIConfig.carData`~~ (v1.9.5: the
live setup.ini read failed for the nil-default reason, not a whitelist;
v1.9.6: on, with the unit conventions verified against the spinners) — but it means
per-car schema could be baked in the way DCAMBER_LOOKUP already is. Also
noticed and NOT yet resolved: `CAMBER_LF` reads `SHOW_CLICKS=0, MIN=-5,
MAX=-1.2, STEP=1` (i.e. raw degrees), which sits awkwardly against the
camber writer's derived "tenths of a degree" scaling — worth investigating
before trusting either, not yet a confirmed bug in anything.

## Real-setups section-name scan (v1.3.1)

`Documents\Assetto Corsa\setups\` holds 1561 real saved setup files across
400+ cars (GT3/GT4/LMP/BTCC/DTM/WRC rally/drift/karts/classics) - none
encrypted, unlike car data. `scan_setup_sections.py` in the tools folder
tallies every section name that actually appears, as a real-world check on
SETUP_PROBE's coverage claim. Findings:

- Existing dual-naming defenses are pointed the right way: `FRONT_BIAS`
  beats `BRAKE_BIAS` 1464-to-0 in this sample, `ROD_LENGTH` beats
  `RIDE_HEIGHT` 5611-to-0. Confirms those choices, no action needed.
- **Fixed**: `DIFF_RAMP_POWER`/`DIFF_RAMP_COAST`, an alternate diff naming
  used by 92 real files (~6% of the sample), wasn't probed at all - and
  the differential writer hardcoded the literal `'DIFF_POWER'` string
  rather than iterating `SETUP_PROBE.diffPower`, so this needed a writer
  fix, not just a probe-list addition. Both done in v1.3.1.
- **Known, deferred**: `DAMPER_BUMP`/`DAMPER_REBOUND`/`DAMPER_FAST_BUMP`/
  `DAMPER_FAST_REBOUND` (alternate damper naming, ~10 real files worth) -
  smaller footprint, and fixing it properly touches two separate
  hardcoded writer blocks (slow + fast dampers) instead of one. Not done
  yet.
  **Cause found 2026-09-24:** these aren't just a different name. They
  are CSP `DAMPER_LUTS=1` click sliders (index-valued, one LUT per
  click), and on strut-front cars they sit alongside vanilla `DAMP_*`
  fronts in the same file. See "CSP extended suspension" near the top.
- Confirmed out-of-scope-by-design, not gaps: gearing sections
  (`INTERNAL_GEAR`/`FINAL_RATIO`/`GEARSET`) - the app has no gearing
  writer at all, by design; electronics/engine sections (`ABS`,
  `TRACTION_CONTROL`, `ENGINE_LIMITER`, `TURBO`, `MGUK_*`, `BRAKE_DUCT`)
  - never advised on; meta sections (`CAR`, `TYRES`, `FUEL`, `ABOUT`,
  `__EXT_PATCH`) - not adjustable parameters.

## DCAMBER_LOOKUP audit (v1.3.0)

Every entry checked against real data via the decoder (see below): 88
already matched, 7 were genuinely wrong values (now corrected - biggest was
ferrari_458_s3: stored 1.2, real 2.0), 4 had correct values under guessed
keys (now renamed to the real folder, confirmed by decryption - e.g.
'mclaren_f1_gtr' -> ks_mclaren_f1_gtr), 3 remain genuinely unresolved and
inert (no installed car matches even loosely, and the only candidates found
were unrelated third-party mods - forcing one would repeat the mistake, not
fix it). `audit_dcamber.py` in the tools folder re-parses the table straight
out of the Lua source, so it can be re-run any time the table changes and
never silently drifts out of sync.

## Dev tooling (installed, not in-game)

Lua 5.4 (`DEVCOM.Lua`) and `lua-language-server` (`LuaLS.lua-language-server`)
are installed via `winget` on this machine. Scripts and config live in
`D:\Claude\setupcoach-tools\` (outside this app folder on purpose — CSP scans
`apps/lua/<name>/` for app files, and dev tooling has no business in there):

- `.luarc.json` — points `workspace.library` at CSP's own shipped
  `extension/internal/lua-sdk/ac_apps/lib.lua`, so the checker validates
  field/function access against the *real* `ac.*`/`ui.*`/`ac.StateCar`/
  `ac.StateWheel`/`ac.StateSim` shapes — the same file this project already
  hand-verifies API claims against, just automated.
- `smoke_test.lua` — loads and executes the real file top-to-bottom under
  stock Lua with minimal `ac`/`ui`/`script` stubs (`ac.storage` returns its
  argument unchanged), then confirms every `script.*` entry point exists.
  Catches load-time failures and top-level mistakes; exercises **zero**
  real game logic.
- `check.ps1` — runs all three: `luac -p` (syntax), the type/API check, and
  the smoke test, in that order. `.\check.ps1` checks the installed file;
  `.\check.ps1 -Path <file>` checks anything else.

**What this can and can't catch**, worth remembering next session:
- The type/API check only sees through values whose type it can infer.
  `car`/`sim` parameters need an explicit `---@param car ac.StateCar` (or
  `ac.StateCar?` where the function is meant to tolerate nil) above the
  function for the checker to validate field access inside it — see
  `engine:update`/`buildAdvice`/`refreshTargets`/etc. for the pattern. An
  unannotated function is invisible to this check, not confirmed clean by it.
- None of this replaces an actual in-game session — no real telemetry, no
  real `ac.INIConfig.carData`, none of CSP's actual runtime quirks.
- CSP's exact embedded Lua version was never confirmed in this project;
  `runtime.version` in `.luarc.json` is set to "Lua 5.4" as a reasonable
  guess matching the installed interpreter, not a verified fact.

**Already paid for itself once**: the very first annotated run (v1.1.1)
found `engine:saveGripBaseline`/`engine:gripCompareText` dereferencing a
`car` parameter that `windowMain` passes in straight from `ac.getCar(0)` —
documented nilable — without a guard, unlike `drawHeader` right next to
them which already has one. Same bug *class* as the `.abs` crash: an
uncaught error there wouldn't crash the app, but would silently stop that
frame's UI draw partway through. Fixed with `if not car then return end`,
matching the existing pattern elsewhere in the file. Two other findings
from that same run were investigated and confirmed as non-issues, not
bugs: `math.atan2` genuinely isn't in stock Lua 5.4 (it's 5.1/5.2/LuaJIT)
but the only call site was already `pcall`-wrapped; and `script.onSimUpdate`
being defined twice is an intentional monkey-patch (the second definition
captures and wraps the first to set a `_simBound` flag), not a mistake.
