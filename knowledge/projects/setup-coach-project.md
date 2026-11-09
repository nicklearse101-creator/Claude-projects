---
name: setup-coach-project
description: "Setup Coach (AC/CSP Lua app) — Alpha shipped at v1.9.0; agreed NEXT PHASE review list, install paths, dev-source-of-truth versioning gotcha, CSP API gotchas, and dev tooling"
metadata: 
  node_type: memory
  type: project
  originSessionId: 06951a76-b443-4ded-b0bf-33a77e7c966d
  modified: 2026-10-05T12:03:37.747Z
---

**STALE as of 2026-09-23**: this memory's "current version" claims below
top out at v1.9.8, but `C:\Users\nickl\Downloads\` now has version files
through `SetupCoach_42_v2.1.1.lua` (dated 2026-09-22) - real work happened
that isn't reflected here. That history lives in the session itself
(titled "Claude markdown file" in the sidebar, cwd `D:\Claude`, not a
dedicated project - see [[ac-physics-watchdog-project]] for why), not in
this memory. Read the session or re-grep the installed file's `VERSION`
before trusting anything version-specific below; don't assume v1.9.8 is
still where things stand.
**Update 2026-10-05 (Setup Coach session):** the entries below ARE current
through v2.6.0 (installed hash 8D16B5EC1257A10D, `SetupCoach_49_v2.6.0.lua`
+ `SetupCoach_49_v2.6.0.zip`, tag v2.6.0; v2.5.2 was 1F875D7706D5F0C5,
v2.5.1 30E46F18B8D544B2) - the v2.x work was recorded here as it happened.
The re-grep advice above still holds.

**v2.6.0 (2026-10-05)** - Nik's bottoming/floor decisions (below, under
v2.5.2) built via superpowers brainstorm -> spec -> plan -> executing-plans
(inline, ledger in repo `.superpowers/sdd/...`, gitignored). Per-end
bottoming chains `travelF/R-bottoming`: packers > slow bump > fast bump >
springs (cautiousSpringTarget: 95%, max +10%/Build) > ride height +1;
same runBranch/ledger/put-backs as balance, run first; bump only, never
rebound (old "creep" reasoning was backwards). Retired 5 stacked writers +
the bottomingActive gate. Floor clearance: per-lap 1 mm histogram of
car.rideHeight (lowest 0.5% ignored) -> floorClearanceStep: lowest end to
10 mm off the floor, never into the aero stall (wings[].groundHeight vs
GH_CL peak), lower only with no bottoming, travel < 90%, reliable calibration
both ends; same mm both ends, 3 clicks max. Log `floor (v2.6.0)` and `track
contacts (v2.6.0, logged only)`. Suite 23 files / 1169. Untested in-game -
first look: the floor line (sane clearances? groundHeight read?). Told Nik:
ride-height raise probably can't fix "running out of travel" in AC (rod
length moves the car, not travel used) - the chain freezes it if so.
GOTCHAS learned this session: (1) Git Bash `sed -i` on the CRLF app file
STRIPPED every CR (restored from a copy) - never sed the app, use Edit or a
binary-mode Lua script; (2) the Bash tool turns `\\n` inside a heredoc
into a real newline - write helper scripts with the Write tool; (3) a
top-level `local` is invisible ABOVE its declaration - buildAdvice
(~line 6270) can't see constants declared near the lever chains (~7100);
test_v260 guards the order. (4) The smoke test never runs Build or the
panel - new code there needs a test that runs the block verbatim (section 6
of test_v260 shows how).

**GIT (since v2.5.0, 2026-09-29):** `D:\Claude\setupcoach-tools` is the
repo (tests, tools, `app/` = snapshot of installed SetupCoach.lua +
manifest.ini + CLAUDE.md). Local identity Nicklearse101, `core.autocrlf
false` (app file is CRLF). Tags v1.1.1..v2.5.0 (past releases imported
from Downloads, dated). The INSTALLED file stays the working copy.
Release routine: bump manifest.ini `VERSION` -> tests + check.ps1 green
-> copy the 3 app files into `app/` -> Downloads copy
`SetupCoach_NN_vX.Y.Z.lua` -> `.\make_release.ps1` (zip: 
`SetupCoach_changelog.txt` at the top, from the header comment, +
apps/lua/setupcoach/ lua+manifest; refuses version mismatch / stale
Downloads copy) -> commit (+ Co-Authored-By trailer) -> tag. SEND NIK
THE ZIP ONLY - changelog inside at the top, no separate .txt (his ask,
2026-09-29).
Check line endings with PowerShell regex (`"`r`n"` counts): in the Bash
tool `grep -c $'\r$'` counts EVERY line, so it can't tell CRLF from LF. Backups are
now just tags (the last file backup is `SetupCoach_backup_v2.4.0.lua`).
`acd/extracted/` (others' car data) is gitignored.

**v2.5.2 (2026-10-05)** - Nik said "continue"; reviewed the 57 v2.5.1
Builds of 29 Sep - 4 Oct (per-Build summary script in the session
scratchpad: parse debug_log.txt blocks -> car/evidence/verdicts/changes).
Fixed: RESET TELEMETRY wiped travelRef (16 Builds on 0.12 m) -> carDataStale
re-read; slow-damper bottoming bypassed lapSupport -> travelHitsConsistent;
bias: airborne-wheel samples dropped from grip sums -> load-only fallback
spent the Sunbeam v6's one-time write (now: 4 wheels loaded, no load
fallback with a grip model, no one-time decision on an overridden gate);
ride-height direction from 1 noisy pair across spring changes -> same-spring
pairs, 2+ agreeing, |median| >= 0.3 mm/click; pressure base ignored live
when no template. Test test_v252_log_review_fixes.lua (53, red-green per
fix). Suite 22 files / 1008. Untested in-game. Gear fix (v2.5.1) STILL
unexercised - no car with per-gear spinners driven since.
NIK'S DECISIONS 2026-10-05 on that list: "Bottoming - one at a time. Ride
height least important. Stiffening springs too much loses grip so be
cautious." / "Leave override as is." / "Add rally mode to the to-do list"
(done: CLAUDE.md "Not yet built") / "App shouldn't just lower a car to aero
peak - it should lower until the car is at minimum available without the
body of the car striking the floor." -> BUILT as v2.6.0 (above). Still open: front damper histogram ratchet
on GT3s; Sunbeam diff flip-flop. CSP signals for floor strikes:
car.collisionDepth/collisionPosition/collidedWith (0 = track, walls too -
unverified in-game), car.rideHeight[0/1], ac.getCarPhysics().wings[i]
.groundHeight. Header "#N since app load" also counts RESET presses; Nik
presses RESET TELEMETRY a lot.

**v2.5.1 (2026-09-29 evening)** - Nik's first v2.5.0 test (Huracan GT3,
Silverstone): "build button messed up the gears". CSP's ac.getSetupSpinners
names gear spinners INTERNAL_GEAR_1..N (forward gear n); AC's saved setups
use INTERNAL_GEAR_2..N+1 (SDK's "names match the INI" is FALSE for gears).
v2.1.1's live carry matched by name -> each gear written into the slot
below (5th got 6th's 0.8857). Fix `alignLiveGearNames` (offset from the two
name sets; no match -> gears not carried). Proven from the Build's own log
(physics 5th 1.031; counts 10 carried / 2 left out only fit CSP 1..N) and
no INTERNAL_GEAR_1 in any of 1500+ saved setups. test_v251_gear_names.lua
(43, red-green checked) on fixtures in `acd/fixtures/` (Nik's own setup
files - fine to commit). Suite 21 files / 954. Untested in-game. The bad
file `setups/ks_lamborghini_huracan_gt3/ks_silverstone/SetupCoach_Optimized.ini`
(18:35) still has wrong 1st/3rd/4th/5th - Nik told; next Build overwrites.

**v2.5.0 (2026-09-29)** - from the 21 v2.4.0 Builds + Nik's Sunbeam mod,
Nik: "go through it carefully and build all" (the Sunbeam is WIP, may
gain dampers): travel vs PACKER_RANGE (TRAVEL key never existed - GT cars
never registered bottoming, long-travel over-registered); Nord-length
tracks count ~5 km sections (gate was overridden 18/21 Builds); bias target
from tyre GRIP (Sunbeam 77% -> 70%, fronts locked first at 69%), handbrake
excluded; springs + diff-coast levers for cars without bars/dampers; one
"Not adjustable" summary line; per car+track last-Build/pending records;
held slides (handbrake / throttle 1 s+) apart from snaps; physics
fingerprint resets learned values on a physics change (first sighting only
records - the Sunbeam's bias decision was made on OLD brakes, so Nik
should press Settings "Re-arm" once). Test
`test_v250_evidence_and_physics.lua` (150) caught a real `DAMPER?_` Lua
pattern bug. Suite 20 files / 916 green. Untested in-game.
KNOWN COSMETIC NIT (fix in the next version, not worth a release alone):
`checkPhysicsFingerprint` sets `self.physicsFirstSeen = (before == nil)`
on every call, and refreshTargets re-runs it on a tyre-compound change, so
a car's first session can log "physics fingerprint: unchanged since this
car was last seen" instead of "first time this car is seen - recorded".
Behaviour is right (nothing is reset either way); make the flag sticky per
car id. (Checked 2026-09-29: the check runs once per car/compound load,
never per frame - classIdeals always gives targetF > 0.)

Setup Coach is a Custom Shaders Patch (CSP) Lua app for Assetto Corsa that
the user is actively developing (telemetry-driven setup advice + an
optimal-setup `.ini` writer). Full project context, hard constraints, and
physics findings live in `CLAUDE.md`, present in two places that must be
kept in sync by hand (plus a snapshot in the git repo's `app/`):
- `D:\SteamLibrary\steamapps\common\assettocorsa\apps\lua\setupcoach\CLAUDE.md`
- `C:\Users\nickl\Downloads\CLAUDE.md`

**Installed app file:** `D:\SteamLibrary\steamapps\common\assettocorsa\apps\lua\setupcoach\SetupCoach.lua`.

## NEXT PHASE — review list (agreed 2026-09-12, after Alpha shipped)

The user asked me to hold these for the next working session rather than
churn them during alpha testing. Raise them when we pick this back up.

**1. ~~manifest.ini VERSION mismatch~~ — FIXED 2026-09-29:** manifest now
`VERSION = 2.5.0`, bumped every release, `make_release.ps1` refuses a
mismatch (Nik OK'd it once releases became a zip carrying both files).
Original note: `manifest.ini` said `VERSION = 2.0.2`
while the app reports `v1.9.0`. Content Manager displays the MANIFEST value,
so testers will report "2.0.2" and muddle bug reports. Cosmetic and
zero-risk to behaviour, BUT fixing it means every tester takes both files
instead of just `SetupCoach.lua` — that distribution hassle is the only
reason it wasn't done immediately. Legacy of the old numbering before the
deliberate 4.9.1 → 1.0.0 relabel.

**2. `windowHud` is dead code in practice.** The app defines
`script.windowMain`, `script.windowHud` AND `script.windowSettings`, but
`manifest.ini` declares only ONE window (`FUNCTION_MAIN = windowMain`). So
the HUD window has never been able to appear — same root cause as the
settings window being unreachable (v1.7.5). If a compact in-race HUD is
wanted, it's a one-line manifest addition plus verifying `windowHud` still
renders sensibly (it hasn't run in a long time, so treat it as unverified).
Note this also means the settings-gear question could potentially be solved
by declaring it in the manifest rather than relying on CSP auto-wiring.

**3. ~~BAKED DAMPER RANGES ARE WRONG~~ — FIXED in v1.9.1.** The user
pushed back on my "don't re-derive" caution with a good point: *"damper and
toe rules can be different, as long as they work for what theyre meant
to"* — correct, and I was over-cautious. The damper rule IS derivable and
now verified: these dampers store a COUNT OF STEPS FROM ZERO (physical =
value*STEP), so the legal range is ceil(MIN/STEP)..floor(MAX/STEP) — rear
rebound 11..32, containing the 26 default. Checked against all six tooltip
defaults AND seven real observed values; all fit. Recorded per car in
`gen_baked_schema.py`'s `CONFIRMED_DAMPER_UNITS` (Ferrari = 'step_multiple',
Lotus stays click-index, proven by live spinner `[0..24]`). Guarded by
`test_damper_ranges.lua`, which asserts a car's own defaults fall inside its
baked ranges — one invariant that catches a wrong unit conversion without
needing to know the right one. Also found: the wrong ranges did ACTIVE
damage, clamping the driver's fast bump 88→22 and 64→20, far below the real
66/45 minima. Original note follows for context:

**3-ORIGINAL (superseded).**
AC's own in-game damper tooltips (shared by the user 2026-09-13) state the
`ferrari_458_gt2` factory defaults: rear rebound **26**, front rebound
**29**, front bump **39**, front fast rebound **185**. My baked maxima are
22/22/20/15 — every default exceeds its own supposed max, which is
impossible. So `readSetupItem`'s SHOW_CLICKS→click-index conversion (and
its port in `gen_baked_schema.py`) is wrong for these fields. A
`MIN/STEP..MAX/STEP` rule fits all six dampers **but then breaks toe**
(toe fits click-index), so the per-field conversion is NOT reliably
inferable offline — **do not attempt a third derivation.** v1.8.0's live
spinner read already supersedes baked values and is consistent by
construction (verified on the Lotus: ini `7000..19000 step 500` → live
`[0..24]`). Residual risk is only the fallback path.

**4. THIS ALSO MEANS v1.6.0's HEADLINE FINDING WAS WRONG** — I reported
that rear rebound had been "pegged at max 22 for months" and that observed
values 24–35 were all silently clamped. They weren't; 26 is the car's
DEFAULT. Corrected in CLAUDE.md's v1.6.0 section with a prominent warning
block. **Lesson: I built a confident narrative on an offline-derived unit
conversion and never sanity-checked it against the simplest available
reality — the car's own default value.** When a derived range says the
factory default is out of range, the range is wrong, not the car.

**5. ~~`SetupCoach.lua`'s changelog still asserts the wrong v1.6.0 claim~~
— DONE in v1.9.1** (corrected in place with a retraction marker, since the
file was being touched for real anyway).

**v2.4.0 — BRANCH PASSES** (2026-09-24). User: once a chain (ARB,
dampers...) has been worked through, cycle back to the branch start and
monitor the group as a whole; chose "put them back to starting value" for
no-effect moves (over report-only). Branch = car+track+signal in
`settings.branchState`; pass ends when problem gone or no lever can move;
group judged baseline→now (2×noise); no-effect moves put back via
writeTuned (skipped if changed since / module off / guard); next window
verifies (restore if worse); improved → next pass, frozen levers get one
more try; no gain or 3 passes → STOPPED + Settings reset button. Also
fixed: ledger held ONE car (now per car, migrates); pending carries track.
Test `test_branch_passes.lua` (100) drives the real extracted runner block
Build by Build - pattern worth reusing for other Build-internal logic.
Suite 19 files / 763 green. Backup `SetupCoach_v2.3.0_backup.lua`.
Gotcha: the app file is CRLF - a ReadAllLines/Join rewrite silently made
it LF; convert back (`.Replace("\n","\r\n")`) after any whole-file rewrite.

**v2.3.0 — CALCULATED TARGETS** (2026-09-24). User asked whether Build
calculates optima or steps by trial and error, then: "Yes build all, but
bear in mind moving brakes too far forward/backward has a big influence on
understeer/oversteer/stability on entry. Make brake balance advise only
after 1 build." Built: brake bias equal-limit split (+1%) written ONCE per
car then advice only (`settings.biasBaselineCars`, re-arm button, ±3% cap,
entry-guard HOLD also counts as the one build); springs stiffen to 92%
median travel use; front ride height to aero peak +2 mm (needs pit mm/click
calibration, fuel-matched); damping-ratio floors 0.30/0.40; camber noise
dead-band + measured gain; ARB/rear dampers/wings jump only after a
measured per-click effect beats 2×noise; final drive exact option (ADVICE
ONLY - gearing still never written). Advice stays click-level (user's
explicit ask). Log: `calculated targets (v2.3.0):` line. Test
`test_calculated_targets.lua` (72); suite 18 files / 663 checks green.
Backup `SetupCoach_v2.2.0_backup.lua` (A3B23BD7B7641E10). Untested live -
first log should show which targets had enough data.

**v2.2.0 — CSP EXTENDED SUSPENSION, all three fixes** (2026-09-24). (1)
Damper event thresholds FIXED at 0.54/1.20 for every car
(`DAMPER_EVENT_MODERATE/SHARP`); crossover logged only. Decided by same-car
A/B in the log: Dacia front rebound 12/12/8/3/16 @0.54 vs 0/0 @0.90;
Huracan pinned at 1.00/2.20 → 0-1 over 1,100 corners. (2) ARB_F/ARB_R
LUT bars: VALUE = 0-based LUT ROW (fr_bmw_btcc text keys + detached|0
row prove it); one row/Build; never onto a 0-stiffness row; per-end
resolution (`arbFSection`/`arbRSection`). (3) DAMPER_* LUT dampers:
per-corner damperSection(); every write curve-checked in writeTuned
via lutDamperMoveOk (force @0.025 & 0.10 m/s, click = setup MIN +
stored); sv8_camaro_v2 rear rebound 12→13 REFUSED (broken click-18 LUT);
unreadable curves not written blind. Log: suspension model: line.
OPEN: does the spinner report a numeric-key LUT bar as 0- or 1-based?
(handled either way via schemaItem.min; log will confirm). Test
`test_lut_suspension.lua` (70). Suite 17 files / 591 checks green.

**2026-09-24 — CLAUDE.md gained a research section from ANOTHER session**
(Escort Mk2 physics rework): "CSP extended suspension: LUT dampers, LUT
ARBs, motion ratios". Findings only, no app code. Verified from this
side and appended: of the user's 649 cars with saved setups, **19 use
`ARB_F`/`ARB_R`** (ARB lever unavailable — whole fr_*_btcc grid, TCR
2024s, Ferrari 296/488 GT3, Lexus RC F) and **11 use `DAMPER_*` clicks**
(slow damper writers skip). Correction to the note: the crossover
problem is NOT LUT-specific — with the 18×/40× anchor **any crossover ≥
0.056 pins thresholds at 1.00/2.20, including the Huracan (0.060)**, which
is why its damper events are tiny. sv8_camaro_v2 `slow_rrebound4.lut`
confirmed broken (force in the speed column). **User then said "All 3" → BUILT in v2.2.0** (below).
Lesson: the app-folder CLAUDE.md can be edited by other sessions — diff
both copies before syncing, and sync newer → older.

**v2.1.1 — Build was RESETTING tyre compound + gearing** (2026-09-22).
User: "before driving, i set my tyre compound and gear ratio. When i press
build optimal setup and load, it reverts back to default." CONFIRMED from
files: Build wrote FINAL_RATIO=6 / TYRES=1, driver's last.ini had 3 / 0;
final.rto index 6 = 3.9166 = drivetrain.ini's FINAL= (the car's DEFAULT).
**Cause: v1.8.1 was half right** — it stopped the live sync touching
unmanaged sections (no writer may touch gearing) but that left them at the
TEMPLATE's values, and the template is last.ini which AC writes only at
session END, so anything set in the setup screen pre-drive is absent. The
output file is a full copy of the template, so every section in it is
applied on load. **KEY DISTINCTION: WRITING a section (a writer choosing a
value) vs CARRYING it (the file stating what's already on the car).**
Unmanaged sections are now CARRIED from live spinners; never ADD a missing
section (v1.8.0's INTERNAL_GEAR_1); CARRY_EXCLUDE = {FUEL} only (unsettled
whether the API reports setup fuel or tank — both logged). Compound
cross-checked vs car.compoundIndex. Test `test_carry_unmanaged.lua` (38)
on the two real files. Also fixed test_managed_sections' GEARING check
testing the GLOBAL fail counter (one bug reported as two).

**v2.1.0 — LEVER CHAINS** (2026-09-22). User: rake went negative ("front
shouldn't be higher than the rear"); "if adjusting arb doesn't stop the
problem in a few clicks, prioritise the next module… and measure how one
affects the other"; ARB/aero split → 180 km/h; "stiffening rear ARB while
increasing rear wing will cancel each other out"; override button for the
2-lap gate. Built: every balance writer is `levers.<name>(regime,
direction) → moved, why`; runner moves ONE lever per regime per Build in
`LEVER_CHAINS` order (low-loose: arb > rearDampers > toeRear > toeFront >
rake; low-tight: arb > toeFront > rearDampers > toeRear > rake; high:
wings > rake > toe). Ledger: `judgePendingLevers` compares the previous
Build's banked rate with this window (helped = verdict gone or −15%); 2
no-effect moves FREEZE the lever for that signal/car
(`settings.leverLedger`, `settings.leverPending`, per car, persisted).
Conflict: opposite low/high verdicts → aero first, low chain HELD. Rake
floor +3 mm via `staticRideHeightR` (`rake:` log line). `ARB_AERO_SPLIT_KMH
= 180`. `OVERRIDE LAP GATE (test)` one-shot button. `writeTuned` returns
(handled, changed). Debug: `effect:`, `levers:`, `Balance <regime>
(<verdict>): lever X moved…`, `GATE OVERRIDDEN`. Test
`test_lever_chain.lua` (59). Backups: `SetupCoach_v1.9.9_backup.lua`,
`SetupCoach_v2.0.1_backup.lua`. **Rule: never add a balance writer that
bypasses the chain.** Gotcha: Windows PowerShell 5.1 `Set-Content
-Encoding utf8` adds a BOM — write app files with
`[IO.File]::WriteAllText(..., UTF8Encoding($false))`.

**v2.0.1 — first night on v2.0.0** (2026-09-22). Huracan GT3 @ Silverstone: 4 Builds/5 declines, machinery worked. Fixes: (1) car.lapCount DROPS on session restart while app state persists → laps merged into one bin (L4 c205), gate declined real laps; now a drop re-syncs and flags the lap pit. (2) CSP reloads the app on restart → persisted `settings.lastBuildRecord` / `settings.buildSerial` so `lastBuildLoaded` and Build numbering survive. (3) Pressure clamp at car min now says CLAMPED. **User's routine: Build → load setup → restart session.** Open question for the user: car reads loose every window (50-70 snap/100 low-speed) after 4 rounds of tightening — levers weak, or driver rotation above the 25/100 bar? No 'did the last change help' feedback yet (per-window rates now logged to build it).

**v2.0.0 — THE LAP AS A WHOLE** (2026-09-21). User's agreed aim, verbatim:
"the app is using telemetry to give a best overall setup based on full
lap analysis… We don't want it to be creating builds just from a couple
of corner's data." Then: "Do it and the lap-consistency check. Update
the debug so we can check it's working. Keep previous version as backup"
→ `Downloads\SetupCoach_v1.9.9_backup.lua` (58236E3092405851). Built:
(1) LAP BINS at each `car.lapCount` increment (flags pit/partial/valid;
`WINDOW_KEYS`); totals still accumulate. (2) GATE `engine:buildEvidence()`:
`settings.buildMinLaps` (Settings slider 1..5, default 2) clean laps AND
`BUILD_MIN_CORNERS`=20 → else `result: DECLINED` log entry, nothing
consumed, panel item BUILD EVIDENCE first. (3) CONSUMPTION
`engine:consumeWindow()` after a successful write (counters/corner
samples/sums/pressure peaks → 0; bins fenced by `windowBinsStart`; keeps
static camber/ride-height/cold-pressure captures, tyre ref, schema, fuel,
bin history); NOT on a "no changes" Build. `lastBuildLoaded: YES/PARTLY/NO`
compares live spinners to `lastBuildWritten`. (4) LAP CONSISTENCY:
`regimeVerdict(self,'low'|'high'|'rear',th)` wraps balanceVerdict — ≥ half
the clean laps must individually agree, else `'inconsistent a/c'`;
`lapSupport(self,key)` for scalars (≥2 events in ≥ half the laps): brake
bias, bottoming (ride/springs/fast-damper dir), toe triggers, diff.
`balanceVerdict` now only called inside regimeVerdict. Debug lines:
`evidence:`, `laps: L3[c42 push 12/9 hi 3/5 tin 4 rtoe 2 lk 6/0 bot 0
dmp a/b|c/d dif r/d]`, `consistency:`, `lastBuildLoaded:`, `evidence
consumed:`; header carries version + Build #. Test
`test_evidence_window.lua` (53) — Corvette sequence declines 3 of 4.
**Rule in CLAUDE.md: the unit of evidence is the lap, not the corner.**

**v1.9.9 — first Corvette Z06 GT3 logs, seven findings** (2026-09-21).
User asked what "no DY0 reference" meant + check debug. Decrypted
`corvette_z06_gt3_2024` (now in `acd/extracted/`). (1) DY0=0 on modern
tyres (load-sensitivity model: DY_REF/FZ0/LS_EXPY) → MECHANICAL GRIP now
normalises vs DY_REF and says so. (2) Rear wing is WING_3 on this car
(aero.ini NAMEs BODY/SPLITTER R/L/REAR WING/DIFFUSER R/L; setup.ini
[WING_3]) — writer now resolves the section via `aeroWingIndex`,
WING_1/2 only fallback; `wingRoleFromName` checks diffuser before rear.
(3) **TOE was the 4th one-way ratchet** (front 11→19/20, rear 14→6 in 4
Builds): now verdict-gated, 1 click/Build, reversible toward zero via
`readSetupItem.zero` (Corvette 10, Ferrari LR 5 / LF 0). (4) Rake 1
click per end per Build (was 4 clicks of rake/Build after v1.9.7). (5)
`HISTOGRAM_MIN_EVENTS=6` floor for front damper histogram + diff (diff
also 25% dominance) — both were acting on 3-4 events, diff flip-flopped.
(6) Crossover typo guard: Corvette FRONT 0.50 / REAR 0.050 → take smaller
when >3× apart; Ferrari 0.03/0.01 = 3× keeps front. (7) DCAMBER_LUT
(cmbr.lut) sampled via ac.DataLUT11 → `peakCamberSrc=live-lut`; matches
coefficients on this car (−4.0°). **Ratchet rule (in CLAUDE.md): a rule
whose action can only go one way needs a counter-signal or a cap.** Test
`test_v199_corvette.lua` (58) on the real decrypted files incl. cmbr.lut.

**v1.9.8 — SLIGHT OVERSTEER IS NOT A FAULT** (2026-09-19). User's rule,
verbatim: "slight oversteer in a normal race car isnt a bad thing, that
should be noted." Now a hard constraint in CLAUDE.md and built in: ONE
`balanceVerdict(self, push, snap, th, useRateFloor)` for every
push-vs-snap decision (ARB, rake both regimes, wings, rearHandlingSignal,
panel ARB/AERO/REAR DAMPERS lines, debug line `balance verdicts:`).
tight = push > 1.25×snap; loose = snap > 1.25×push AND (low speed only)
> `SLIGHT_OVERSTEER_PER_100`=25 snap events per 100 corners; else nil =
left alone, reason logged ('slight'/'mixed'). Understeer has no rate
floor. Found the same defect in four places: ARB wrote front-softer AND
rear-softer in one Build (mixed guard only caught same-bar); low-speed
rake lowered BOTH ends in one Build (real Dacia log, v1.4.1 shape); panel
ARB said "soften front" on any push>th; all pulled a slightly loose car
toward push. **Rear dampers: nil verdict = LEFT ALONE** — rear histogram
fallback removed (structurally biased to "stiffen rebound", the v1.9.3
bug, on exactly the slightly-loose cars). Real sessions: Dacia 76/65 →
'mixed' (left alone; was acted on); kinkl rear 373/235 → still 'loose'.
The 25/100 bar is a first calibration — tune from the debug line, not
theory. Tests: `test_balance_verdict.lua` (41), rear-rebound test updated
(22). Test extractor now strips string literals before counting keywords
("fine for a race car" counted as a `for`).

**v1.9.7 — three fixes from a drift-car log that didn't exist** (2026-09-19).
User drove `bmw_m3_e30_drift` online ~2.5h on 09-18, asked "check debug".
NO Build entry: the Optimized.ini's 09-18 mtime was Content Manager
re-saving the selected setup at launch (byte-identical to the 09-16 Build);
CSP log clean. **Forensics recipe:** compare Optimized *content* to the last
log entry, not mtime; CM session times in `AppData\Local\AcTools Content
Manager\Logs\Main Log_*.log`; `Documents\Assetto Corsa\logs\
custom_shaders_patch.log` covers only the LAST launch. Fixes: (1)
`writeTuned` nudge was `frac×clicks×|cur|` (percentage) with schema only
clamping → 8% of 185 = 15 clicks = whole fast-rebound range = the REAL
mechanism behind v1.9.4's "185→175 in one press"; now `clicks×step`
snapped to grid when a step is known, percentage only otherwise. (2)
`readTyreReference` always read `[FRONT]`; E30 has 3 compounds with
different PRESSURE_IDEAL (38 vs 31) and DCAMBER — now picks
`[FRONT_<car.compoundIndex>]`, cross-checked by SHORT_NAME
(`car:tyresName()` = short name). (3) `writeDebugLog` failures now surface
in setupMsg. **App has NO drift mode** — every balance rule treats
oversteer as a fault (09-16 drift Build cut rear pressures 12 psi off
50-psi wheelspin heat); tell testers. E30 WING_1 (SHOW_CLICKS=1, 1..3,
value 3) = third confirmation of the steps-from-zero rule. Test:
`test_step_nudge_and_compound.lua` (43). E30 decrypted to
`acd/extracted/bmw_m3_e30_drift/`.

**v1.9.6 — LIVE ALWAYS WINS** (2026-09-17). User's rule, verbatim: "live
should always win, that's the whole point of the app, to read live data
and advise on setup accordingly." All three remaining nil-default sites
switched on. (1) setup.ini `readSetupItem` had never returned an item on
any car (schemaLimited=true in every log; BAKED_SETUP_SCHEMA existed only
to work around it). Stored-unit conversion is now a RULE verified on 4
cars vs spinner ranges from real logs: SHOW_CLICKS=2 → 0..(MAX−MIN)/STEP;
SHOW_CLICKS=1 → floor(MIN/STEP)..floor(MAX/STEP) (Ferrari slow+fast
dampers confirmed); CAMBER_* → MIN/MAX ×10, STEP as-is (Kunos abarth500
comment "step is in degrees / 10"). Priority everywhere: **spinner >
setup.ini > baked > generic**; pressure writer got the spinner overlay it
lacked. (2) aero.ini: `aeroLutChecked=false` in every log was a CRASH —
nil-default NAME returned a list, `string.lower(table)` threw inside the
pcall. Not a CSP limit. (3) suspensions.ini crossover: multipliers
re-anchored 9×/20× → **18×/40×** so the validated car (Ferrari, real
thr=0.030) stays at 0.54/1.20 instead of being halved; Lotus/Dacia
(0.050) → 0.90/2.00 — WATCH whether Lotus damper writes go quiet. Debug:
TOE_OUT_LF added to liveSetup sample — SHOW_CLICKS=1 on the Ferrari, rule
predicts stored -10..7; if spinner says 0..17 the SHOW_CLICKS=1 rule is
damper-only and must be narrowed. `test_ini_default_type.lua` (86) loads
the shipped functions from the app source and runs them on real files.
No nil-default `iniGet` reads remain (guarded).

**v1.9.5 — THE LIVE DCAMBER READ NEVER WORKED ON ANY CAR** (2026-09-17).
User asked why the Dacia Sandero Cup's camber used temperature spread
instead of peak-grip angle. Dacia has a PLAIN-TEXT `data/tyres.ini` with
DCAMBER_0=1.3/DCAMBER_1=-15 (peak −2.48°), not in DCAMBER_LOOKUP, log said
n/a — so the "CSP whitelists tyres.ini on encrypted cars" theory (held
since 4.6.0, written into CLAUDE.md as a hard constraint) was impossible.
**Real cause: `ac.INIConfig:get(section, key, default)` uses the DEFAULT'S
TYPE as its return type — SDK: "If not set, list of strings is returned."**
Every `iniGet(..., nil)` + `tonumber` was nil regardless of file content;
PRESSURE_IDEAL used default `0` so it worked — that asymmetry WAS the
whitelist "evidence". Log audit: every peak angle ever logged (2.42/3.09/
3.38) is a lookup value; no live read ever succeeded. Fix: `iniNum(ini,
section, key)` (string default → tonumber, tolerates list), applied to
tyres.ini only (DCAMBER, DY0, PRESSURE_STATIC). New debug fields
`peakCamberSrc=live|lookup|live+lookup|none dy0=F/R`. **Three nil-default
sites LEFT ON PURPOSE** — setup.ini MIN/MAX/STEP (live would out-rank the
baked schema's ×10-camber/step-multiple corrections → v1.7.1 bug reborn),
aero.ini names/LUTs (would start ac.DataLUT11 in app context, unproven),
DAMP_FAST_BUMPTHRESHOLD (re-scales damper thresholds). Each is its own
switch-on decision. Test: `test_ini_default_type.lua` (33) runs both
readers against the real Dacia file. **Lesson (same as ui.checkbox): when
one read works and its neighbour doesn't, diff the CALL before theorising
about the SOURCE.** The camber-oscillation parked item will now be more
visible since the DCAMBER route fires on many more cars.

**v1.9.4 — PRE-RELEASE PHYSICS AUDIT, all findings fixed** (2026-09-14,
"fix all, we can always revert"). User asked for every module to be
checked against what the car is actually doing on track. Signals came
through clean (push/snap = textbook slip-angle differential; lockups/
wheelspin/diff from real slip ratios). Found THREE MORE ONE-WAY LEVERS —
the rear-rebound defect shape repeated: (1) WINGS: hard-coded +1 both
ways, both fired on a mixed car, walked to max, no path down → now
mirrors ARB (add to the wanting axle, or reduce the other if near max;
mixed → act on larger, name the other; near-max snapshotted first). (2)
FAST DAMPERS: no-bottoming → always softer, but fast events measure "track
has kerbs" not "dampers too stiff", so they ratcheted to schema min
(185→175 in ONE press on the Ferrari) → soften now floored at the
control's FACTORY DEFAULT via the live spinner's `defaultValue`. (3) Rear
low-speed rake label said "more rake" for a rear-lowering (= less rake)
action — label fixed, action was always right. (4) `coastPush` renamed
`liftOffSnap` — it's in the snap branch, gated gas<0.15, i.e. lift-off
oversteer. User's instinct "not sure fast rebound ever fires" was
half-right: 6 writes vs 70 for fast bump, but when it fires it goes to
the floor. **The transferable lesson, now named in CLAUDE.md: a "balance"
rule whose output never depends on the handling signal — only on an event
count — resolves the same way every time and isn't measuring anything.
Check any writer for that shape before trusting it.** Front slow dampers
deliberately left on the histogram: front bump/rebound counts are
near-balanced in every real log, so no structural bias, and AC's
front-rebound tooltip is a genuine per-car trade. 28-check test.

**ITEM 4 — DONE in v1.9.3** (2026-09-14, on the user's "Ok, fix the
rebound"). The rear axle's slow-damper direction is now driven by the
handling signal — `rearHandlingSignal(self, th)`, ONE shared function
used by both the REAR DAMPERS advice item and the writer: 'loose' (snap >
push by 25%+) → soften rear rebound AND rear bump; 'tight' (push > snap by
25%+) → stiffen rear rebound within 30% of its limit, bump untouched; nil
→ the old histogram, byte-identical. Front axle deliberately untouched
(AC's front-rebound tooltip is a genuine per-car trade). Verified in
`test_rear_rebound_direction.lua` (19 checks) against both real kinkl
sessions — both flip stiffen→soften. **Design lesson worth keeping: the
histogram was a damper-SYMMETRY heuristic that knew nothing about
handling, and on the rear it was structurally biased because rebound
events always out-number bump events (every real session). A heuristic
that always resolves the same way on one axle isn't measuring anything —
check whether a "balance" rule is actually biased before trusting it.**
The REAR REBOUND EXPERIMENT line stays, repurposed to show snap rates
falling as rear rebound falls on loose cars; if they don't, the fix isn't
working and that's where it shows first.

**REAR REBOUND DIRECTION IS NOW ANSWERED** (was open all alpha): AC's
tooltip says higher rear rebound makes the car LESS stable under braking
and initial turn-in — confirming the user's position, Koni's guide,
Suspension Secrets, and the v1.0.1 finding. The app USED TO stiffen rear
rebound whenever rebound events outnumbered bump (v1.9.2 and earlier) -
pushing the wrong way. Also newly available: higher rear BUMP = more oversteer on throttle
and brake release, lower = more traction. Full tooltip table is captured
in CLAUDE.md under "In-game damper guidance". Acted on in v1.9.3 (see ITEM 4 above). **Worth noting the user was
right about this for the entire session** and I kept deferring it for
data the game could have told us.

Also still open from alpha: rake's weak real-world effect, and
`ac.getCarPhysics().gearRatios` returning nothing on `lotus_exos_125_s1`.

**Dev-source-of-truth gotcha, worth remembering before trusting any
"latest" claim**: the user iterates on this file in a separate claude.ai
web conversation (not this session, no shared history), downloading each
revision to `Downloads\SetupCoach.lua`, `SetupCoach_1.lua`, `_2.lua`, …
incrementing on every save regardless of the actual semantic version
inside the file — **the trailing number in the filename and the
`VERSION` string inside the file are unrelated and have drifted before.**
Never trust either alone; always grep the file itself for
`local VERSION = '...'` and diff/hash against what's actually installed
before assuming a Downloads file is newer. The project was also
deliberately relabelled from `4.9.1` down to `1.0.0` mid-project (real
v1, not a rollback — see the file's own changelog for the reasoning), so
version-number magnitude does not indicate recency either.

**CSP UI API gotcha, cost three failed fixes — check this FIRST for any
widget issue:** `ui.checkbox` returns **whether it was clicked**, NOT the
new value (CSP's own SDK: `---@return boolean @Returns true if checkbox
was clicked`). So `flag = ui.checkbox(label, flag)` sets flag true on the
click frame and false on every frame after — symptom is a checkbox that
won't stay ticked / content that "flashes briefly and vanishes". Correct
idiom: `if ui.checkbox(l, v) then v = not v end`. `ui.slider` is the
opposite — it DOES return the value, so sliders were always fine. The
authoritative source for any CSP `ui.*` signature is on disk at
`D:\SteamLibrary\steamapps\common\assettocorsa\extension\internal\lua-sdk\ac_apps\lib.lua`
— **read it rather than inferring semantics from what looks natural.**
Two wrong theories (ac.storage round-trip, settings-window discoverability)
were shipped before simply grepping that file settled it in one search.

v1.9.2 note: fixed from a real TESTER's log (kinkl, ferrari_458_gt2, first
real validation of the live-setup read on that car) plus one direct
request. (1) REAR REBOUND EXPERIMENT read `parsed` at the end of
buildOptimalSetup, AFTER every writer ran, so it logged the WRITTEN value
as "as driven" — proven directly (Build wrote 24→28, line reported 28).
Every prior session's row was corrupted the same way whenever rebound
actually got written. Fixed by snapshotting the three damper values right
after the live-sync settles `parsed`, before any writer touches it. (2)
DAMP_REBOUND_LR/RR's baked min was still off by one — v1.9.1's
ceil(MIN/STEP)=11 vs the tester's own liveSetup: line showing the real
min is 10. Switched to floor for both bounds; now exact-matches the live
spinner (pinned as an exact check, not just "inside", in
test_damper_ranges.lua). (3) Added an "OPEN NOTES FOLDER" button —
testers couldn't find SetupCoach_Notes. Path resolution was ALREADY
correct (findDocsRoot uses ac.FolderID.ACDocuments, follows OneDrive
redirection same as the game), so this was purely a discoverability
problem, not a detection bug — solved with os.openInExplorer + io.createDir
best-effort, falling back to showing the resolved path as text.
Deliberately held: item 4 (acting on the damper-direction evidence) —
user wants more tester logs first. The kinkl log shows it happening live:
461 corners, midSnap=265 (heavy oversteer), and Build stiffened rear
rebound 24→28 — the opposite of what the tooltip evidence says helps.

v1.7.8 note: added an "All on" button for the module write toggles. Worth
remembering HOW this landed, not just that it did — the first attempt was
a one-time forced reset on upgrade, justified by assuming the earlier
ui.checkbox bug had scrambled the driver's toggles behind their back. They
corrected it flatly: "i ticked the boxes myself and left some unticked,
that's not an error." **Pattern to watch in myself: I reached for a fix
whose justification rested on an unverified assumption about the user's
own state, and the fix it justified (silently overwriting deliberate
choices on upgrade) was more invasive than anything they asked for.** Ask
or check before treating existing user state as damage. Fresh installs
already defaulted all-on, so the real (recurring) need was just a way back
to all-on when starting a new car/track — a button, not a migration.

**v1.8.0 — the big one: CSP can read the car's LIVE setup.**
`ac.getSetupSpinners()` returns every setup item as `{name, label, min,
max, step, value, displayMultiplier, readOnly, units, showClicksMode}` —
`name` matches setup INI section names, `value` is what's on the car right
now. Most of this app's architecture (findTemplateSetup, nudging from
last.ini) existed on the assumption this wasn't readable. It is. That one
call fixes: Builds not accumulating (last.ini only writes on session exit,
so eight consecutive Builds produced byte-identical output), unticked
modules writing stale values instead of current ones, `schemaLimited` cars
having no min/max to clamp against, AND the camber units guesswork
(`displayMultiplier` is the authoritative raw→degrees factor; its
reciprocal is the scale that was reverse-engineered by hand — it
reproduces the driver-confirmed `-3.5° → -35` exactly). Do NOT use
`ac.INIConfig.currentSetup()` — its docs warn pit changes aren't reflected
unless saved, i.e. the same staleness. Live values are synced into
`parsed` in ONE place so every writer inherits them via its existing
`getCurVal()`. Guarded: pcall, type checks, and the entire read is
REJECTED unless every value sits inside its own reported min/max (proves
they share a unit space). **CONFIRMED WORKING in-game** (v1.8.0, real session): the read returned 62
self-consistent sections, `CAMBER_LF` range `-60..10` with
`displayMultiplier 0.1` = -6.0°..+1.0°, exactly matching that car's
decrypted setup.ini — the game confirmed the tenths-of-a-degree theory
itself — plus a live `PRESSURE_LF` of 16 with a real 8..20 range on a car
that previously had NO readable schema. So `ac.getSetupSpinners()` is
reliable and should be the default source for setup values, ranges AND
units from here on.

**v1.8.1 — the scope lesson, worth internalising:** v1.8.0 synced ALL 62
reported sections into the output file, which silently rewrote the
driver's GEAR RATIOS (four INTERNAL_GEAR_n changed, plus an
INTERNAL_GEAR_1 section ADDED that their setup never had). GEARING is
advice-only BY DESIGN and had never had a writer — the blanket sync gave
it one by the side door. Fixed with `MANAGED_SECTIONS`, derived at load
time from `SETUP_PROBE` so it can't drift. **The general lesson: when
wiring a powerful new data source into an app, scope what it's allowed to
TOUCH as deliberately as what it reads — "sync everything available" wrote
to six subsystems the app doesn't reason about (gears, fuel, compound, TC,
engine limiter, brake power).** Right idea, wrong blast radius.

**v2.6.0 is current; v1.9.0 = ALPHA BUILD COMPLETE**, declared by the user after diff/aero/
brake bias were split into three independent toggles (14 module toggles
total now, all default on). Alpha scope: 19 advice modules with per-sector
attribution; 14 independently toggleable write modules, each clamped to the
car's real limits and starting from its ACTUAL current setup so Builds
accumulate; gearing/fuel/compound/TC/engine-limiter/brake-power read and
advised on but never written; self-explaining debug log. Deliberately still
open at alpha: rear rebound direction (REAR REBOUND EXPERIMENT line is
collecting the data), rake's weaker-than-expected real effect, and
`ac.getCarPhysics().gearRatios` returning nothing on at least one car.

As of this session the installed + canonical dev-source file is
**v2.2.0**, `Downloads\SetupCoach_43_v2.2.0.lua` (hash A3B23BD7B7641E10; v2.1.1 = `SetupCoach_42_v2.1.1.lua` = `SetupCoach_v2.1.1_backup.lua`, hash B2DA4C5EAFB0FCE1; v2.1.0 = `SetupCoach_41_v2.1.0.lua`, hash E5E5E6AB2AD6F388; v2.0.1 = `SetupCoach_40_v2.0.1.lua` = `SetupCoach_v2.0.1_backup.lua`, hash 88508994CFB88D85; v2.0.0 = `SetupCoach_39_v2.0.0.lua`, hash D29AABCC655C1452; v1.9.9 = `SetupCoach_38_v1.9.9.lua` = `SetupCoach_v1.9.9_backup.lua`, hash 58236E3092405851; v1.9.8 was `SetupCoach_37_v1.9.8.lua`, hash BB7BAB31CEA6C1DD; v1.9.7 was `SetupCoach_36_v1.9.7.lua`, hash EC72312FE0B4F0D3; v1.9.6 was `SetupCoach_35_v1.9.6.lua`, hash 53F64555EA1D521B; v1.9.5 was `SetupCoach_34_v1.9.5.lua`, hash C3843CF7E0B1E512;
v1.9.4 was `SetupCoach_33_v1.9.4.lua`, hash 2CAE8A40F8939DE1) (edited in place
through `_9`-`_28` from `_8` — don't trust any of these filenames once further
edits happen, re-grep `VERSION` before relying on one again; `_16` is
named `v1.5.0` but actually holds v1.6.0, a fresh instance of exactly the
gotcha above). Superseded/backup copies from this session:
`SetupCoach_4.9.0_backup_preinstall.lua` through
`SetupCoach_1.5.0_backup_preinstall.lua` — note each `X_backup_preinstall`
holds the version BEFORE X. No backup was made for `1.6.0` through
`1.7.8`, so those exact bytes are gone — but the habit finally started at
v1.8.0: **`SetupCoach_1.8.0_backup_preinstall.lua` holds v1.7.8**, which
is the revert point for the live-setup change. Keep doing this before any
core change.

v1.7.7 note — the real fix, and a hard lesson about test stubs. The
flashing checkbox was never ac.storage (v1.7.6's theory) nor windowSettings
discoverability (v1.7.5's) — it was the `ui.checkbox` return-value gotcha
described at the top of this file, present in ALL 17 checkbox call sites,
including four predating this session (Show kPa, Hide OK items, Use temp
analysis, Sample in replay) that had silently never worked because
windowSettings never renders. Fixed with one local `checkbox()` helper
wrapping the documented idiom. **The tooling lesson is the durable part:**
the v1.7.4 smoke-test stub was written as
`checkbox = function(label, cur) return cur end` — encoding MY assumption
rather than the real API — so the test validated the broken code twice
over. A stub that mirrors your belief instead of the real contract is
worse than no stub at all. `smoke_test.lua` now models CSP's real return
semantics plus two regression guards (unclicked pass must not mutate
persisted booleans; clicked pass must flip them), and — importantly — both
were verified to actually FAIL on deliberately broken copies before being
trusted. Do that verification for any future guard: a green test that has
never been shown to go red proves nothing.

v1.7.6 note, superseded by v1.7.7 (the ac.storage theory below was WRONG —
kept only as a record of the wrong turn): the NEW
expand/collapse checkbox added in v1.7.5 (to work around v1.7.4's
unreachable windowSettings) was ITSELF broken - "tick the box, flashes
and vanishes" - because it too was a brand-new `ac.storage`-backed key
with no existing on-disk value, same root-cause SHAPE as the settings-
window discoverability issue (a surface this project can't test except by
shipping). Fixed by moving it off `settings`/ac.storage entirely onto a
plain `engine.showModuleToggles` field (matching `engine.setupMsg` etc.,
existing UI-only state that was never persisted) - eliminates the whole
risk category rather than chasing the exact storage mechanism. **Two real
bugs in a row from one feature (v1.7.4)** - worth defaulting to plain
engine fields for pure UI state going forward, and treating a brand-new
persisted settings key as unverified until a real session confirms it
round-trips.

v1.7.5 note, important cross-app lesson: v1.7.4's 12 new checkboxes were
put in `script.windowSettings` (CSP's dedicated settings-popup function,
reached via a gear icon CSP is supposed to render automatically) and
verified to RUN without error via an improved smoke test - but "runs
without error" never proved the icon that reaches it actually exists in
CSP's UI for this app. It doesn't appear to (or isn't discoverable) -
`manifest.ini` here declares only one `WINDOW_` entry ("main"), and
there's no way to confirm from outside a running game whether CSP hooks
up `windowSettings` automatically regardless. Reported within the hour:
"dont see any boxes". Fixed in v1.7.5 by duplicating the same checkboxes
(via one shared function, `drawModuleToggleCheckboxes`, called from both
places) into `windowMain` itself, collapsed behind a toggle, right above
the Build button - guaranteed reachable since it's the panel already on
screen. **Lesson for any future settings added to this app: don't trust
windowSettings alone to be reachable - either verify the gear icon
actually appears in a real session first, or default new toggles into
windowMain from the start.**

v1.7.4 note: per-module write toggles added (Settings → "Build writes
these modules"), by direct request so a module can be frozen once it's
dialled in without unticking cost every other module's iteration. 11 new
checkboxes + the pre-existing `writeDiffAeroBrake` = 12 total; front/rear
split for dampers (slow+fast) and toe since the writer already loops
per-axle for those and it's a real workflow (rear rebound direction has
been a running, axle-specific debate all session); ARB stays one toggle
since its push/snap logic can redirect to the OTHER bar near a limit, so
a front/rear split wouldn't map onto anything the code decides. **Real bug
caught before shipping**: the front/rear gate was first written as
`front and settings.writeX or settings.writeY` - Lua's `cond and a or b`
"ternary" silently breaks whenever `a` itself can be `false`, which it is
here (a boolean setting) - `front=true, writeX=false` collapsed to `false`
and fell through to return `writeY` instead. Caught by hand-tracing all
four combinations before shipping, not by any test that already existed -
worth remembering `cond and a or b` is unsafe in Lua whenever the middle
value can itself be false/nil, in this codebase or any other. Fixed with
plain if/else, verified in new `setupcoach-tools/acd/test_module_gates.lua`.
Also hardened `smoke_test.lua` itself to actually CALL `windowSettings`
with real ui.* stubs rather than only check it's defined - an empty
`ui = {}` had let a dozen new `ui.checkbox` calls go completely
unexercised by the dev tooling.

**Second test car surfaced this session:** `lotus_exos_125_s1` @ `spa` —
first car other than `ferrari_458_gt2` with a real debug log in this
project. Its `data.acd` has not been decrypted (no `extracted/lotus_exos_125_s1/`
yet) and it has NO entry in `BAKED_SETUP_SCHEMA` — runs fully
`schemaLimited=true`, unclamped percentage-nudge writer on every section,
same exposure the Ferrari had before v1.6.0. Also: `ac.getCarPhysics()`'s
`gearRatios` read fails outright on this car (`topGear=nil` in every log
so far) — v1.7.3 added `gearPhysDiag` to explain why on the next session,
not yet diagnosed.

v1.7.3 note: GEARING's advice was found to be one-directional — it could
only ever say "hitting the limiter, get a taller top gear", never the
mirror-image "not even close to the limiter, get a shorter one", which is
exactly what a driver hit on the Lotus/Spa combo ("barely got into top
gear, nowhere near limiter"). Added that missing check, deliberately built
on `maxGearSeen` (highest gear number actually driven, tracked fresh)
rather than the physics-API ratio read, so it still works on cars where
that read is broken. **GEARING remains advice-only on every car** — there
has never been a Build-time write for it, and building one needs a car's
`GEAR_N`/`FINAL_GEAR_RATIO` ratio-SET contents (`RATIOS=X.rto` references,
not raw numbers) decrypted first to know which direction is actually
shorter — deliberately not guessed, given this project's history of
getting a physics direction backwards when guessed (damper direction
twice, wing role once).

v1.7.1→v1.7.2 note, worth remembering as a pattern not just a bugfix:
v1.7.1 fixed a real symptom (camber Build output ignoring the advice
panel's computed target, collapsing to `-5.00`/`-3.50`) with a real,
reasoned mechanism (don't trust a template value that's wildly outside
the car's real schema range) — and was STILL wrong, because the schema
itself had the wrong units. `CAMBER_LF/RF/LR/RR`'s ini declares
`MIN=-5 ;degrees` etc., and v1.6.0's baked schema trusted that literally
— but the user directly disproved it: setting **-3.5°** via Content
Manager's own camber slider produced a stored raw `VALUE` of **-35**, a
known Kunos legacy quirk where alignment-field `VALUE` is stored in
tenths of a degree regardless of what MIN/MAX/comment claim. So `-24`
(flagged as "stale garbage" in v1.7.1) was always a perfectly legitimate
-2.4°, and the `-35` in the user's own "fastest lap" files (which v1.7.1's
writeup wrongly called corrupted too) was their own deliberately-set
-3.5°. Fixed by ×10-ing the four baked `CAMBER_*` entries (`gen_baked_schema.py`
too, so a future re-bake doesn't reintroduce it) — v1.7.1's sanity check
itself was kept (still a reasonable safety net) and now correctly stays
quiet on legitimate values. **Lesson: when a driver reports the exact
before/after of a value THEY set themselves, that's stronger evidence
than a file's own inline comment — verify against it before trusting the
comment.** Same family as this file's existing "don't dismiss the user's
field reports" lesson from the rear-rebound investigation.

Caught immediately after by the user, before it could bite the next car:
my first pass at this fix over-generalised by pattern-matching on
`CAMBER_` in `gen_baked_schema.py`, i.e. "every car's camber field is
x10". Wrong — a genuinely wide, literal-degree camber range (a real car
can run -8° to 0+) looks numerically identical to a narrow mis-scaled
one; MIN/MAX magnitude alone can't tell them apart either way. Reworked
into `CONFIRMED_UNIT_SCALE`, a per-car_id lookup (currently only
`ferrari_458_gt2 → CAMBER_: 10`) — any other car keeps the ini's literal
numbers until *its own* unit convention is confirmed the same way (ask
the user to set a known value via Content Manager and report the exact
stored VALUE), never assumed from the field name or number size alone.

v1.7.0 note: user reported the "flooring" (bottoming) detector was
overzealous — chasing zero bottoming flags forced ride height excessively
high, when a little kerb scrape is normal on a real track. Two real causes
found and fixed: (1) the detector counted 92% suspension-travel usage
(routine under hard braking) and ANY vertical-G spike, even with low
travel usage (i.e. a kerb slapping a wheel, or a crest unloading the
body — neither is the chassis touching down) as bottoming; tightened to
97% travel and G-spikes now require concurrent ≥85% travel usage, else
they fall into the pre-existing consequence-free "kerb" bucket instead.
(2) bottoming had absolute priority over rake/other SUSPENSION advice and
always won the ride-height write, gated at the same low generic threshold
as everything else; added `bottomTh = th * 2` for ride-height raises, the
SUSPENSION advice slot, and the fast-damper direction flip specifically,
while packer-range widening (the free fix, no ride-height/aero cost)
deliberately stays at the plain threshold. Session-persistent counters
(reset only via the in-app RESET TELEMETRY button) were left alone — true
of every module, not unique to bottoming, out of scope for this fix.

v1.6.0 note — the biggest writer bug found so far, and a reminder that
"the log says it changed" is not proof anything changed. On encrypted cars
`readSetupSchema` returned nothing, so `writeTuned` had no MIN/MAX and its
percentage nudges compounded without a ceiling (simulated: rear rebound
24→78 over 8 Build presses). The car's real max is click index 22, so every
rear-rebound value in months of logs was already out of range and silently
clamped by AC on load — the car sat pinned at max while the log reported
"26 → 30" as real edits. Fixed with `BAKED_SETUP_SCHEMA` (real schema
extracted offline by the acd decoder, emitted by
`setupcoach-tools\acd\gen_baked_schema.py`, applied per-section as a
fallback); **no writer logic changed**, the existing clamp just has real
numbers now. `schemaSource=` in the debug log reports
live/baked/live+baked/none. Only `ferrari_458_gt2` is baked so far —
other cars still run unclamped until generated.
Two things deliberately NOT changed in v1.6.0: rake's weak effect is a
separate, still-open issue (`ROD_LENGTH` was verified never clamped), and
the "should rear rebound go DOWN for rear grip?" question was left to a
new **REAR REBOUND EXPERIMENT** debug line rather than flipped on
secondary sources, because this project has had damper direction backwards
twice already.

v1.5.0 note: `writeDiffAeroBrake` now defaults `true` again (v1.4.0's
narrower default didn't survive a week of real testing) - camber's
DCAMBER route no longer requires a fresh static capture and the advice
panel now uses it too (previously panel-only-ever-thermal was a real,
separate bug from the writer's stricter gate) - `AERO_LOOKUP` baked-data
fallback added (same pattern as DCAMBER_LOOKUP) since live aero.ini reads
are confirmed dead on encrypted cars - GEARING's old live-measurement
system fully retired in favor of `ac.getCarPhysics().gearRatios`, now
trusted and restricted to just top gear + the gear below it.

v1.4.1 note: v1.4.0's raw-counter debug logging paid for itself almost
immediately — found a real ARB self-cancellation bug (push and snap
writers both targeting the same bar in opposite directions within one
Build press) from the very first tester log that had the new counters in
it. Good evidence this kind of instrumentation is worth adding proactively
elsewhere in the app, not just reactively when something looks wrong.

v1.4.0 note: Build's default write scope now stops at Toe (pressures
through toe write automatically; differential/aero/brake bias are
advice-only unless `settings.writeDiffAeroBrake` is turned on) - a
deliberate user request, not a bug fix. Also: this project's own local
`debug_log.txt` (`Documents\Assetto Corsa\SetupCoach_Notes\debug_log.txt`
on this machine) is a genuinely valuable historical record — it confirmed
a real, now long-fixed "only pressure/camber wrote" bug from 2026-09-08,
distinct from a later tester report of the same symptom that turned out
NOT to be the same bug. Worth checking that file directly (not just
whatever log a tester sends) when a write-scope question comes up again.

v1.2.1 note: when the user asked "will this work on all car classes, not
just GT3" (v1.2.0's aero work was verified only against GT3 mods), a real
cross-class check against a kart (`gokart100`) found and fixed a genuine
wing-mislabeling bug (see CLAUDE.md's "Cross-class coverage" section) -
worth remembering the pattern: this user's follow-up questions about scope
("does it work everywhere?") are often worth actually re-testing, not just
reasoning about from the code, since it already found a real bug once.

**Dev tooling** (installed this session — its first run already caught a
real unguarded-nil bug in `saveGripBaseline`/`gripCompareText`, fixed as
part of the v1.1.1 bump): Lua 5.4 (`winget` id `DEVCOM.Lua`) and
`lua-language-server` (`winget` id `LuaLS.lua-language-server`), config and
scripts at `D:\Claude\setupcoach-tools\` — `.luarc.json` (points
`workspace.library` at CSP's shipped
`extension\internal\lua-sdk\ac_apps\lib.lua` for real API-shape checking),
`smoke_test.lua` (loads+executes the file under stock Lua with minimal
`ac`/`ui`/`script` stubs), `check.ps1` (runs syntax + type/API + smoke
checks together — `.\check.ps1` defaults to the installed file). Full
writeup of what it can/can't catch is in the CLAUDE.md "Dev tooling"
section, not duplicated here.

**data.acd decryption is SOLVED** and lives at
`D:\Claude\setupcoach-tools\acd\acd_decoder.py` (`python acd_decoder.py
<car_id>` → `acd\extracted\<car_id>\`; no args = self-test). Don't re-derive
it: the published Ruby reference (`bovis/acd_extractor`) has the key
derivation RIGHT but the keystream application WRONG, and passes its own
fixture anyway, which sends you down a blind alley. The keystream resets per
file (not continuous across the archive) and each plaintext byte is byte 0 of
a 4-byte LE field (not "strip zero bytes"). `solve_key.py` recovers a key by
cryptanalysis (keystream bytes are constrained to ASCII 45–57 since the key
is a dash-joined decimal string) if a car ever fails. Content Manager's
Developer Mode → Content → "Unpack Data" is the GUI alternative the user can
always fall back on.

**Upcoming**: user has a race planned Sunday 2026-09-13 on ferrari_458_gt2 @
Interlagos (blckbox_interlagos) — the exact car/track this whole session's
testing has centered on. Weekend of 2026-09-12/13 will likely bring more
tester debug logs and real A/B stock-vs-Build results to look at.

**Why:** this session burned several turns on exactly the filename/version
confusion described above before locating the real canonical file — worth
front-loading that lesson next time rather than re-deriving it.
**How to apply:** before doing anything with a "latest" SetupCoach file the
user hands over, grep its `VERSION` string and hash/diff it against what's
installed rather than trusting the filename or a claimed version number.

2026-09-29 (Blender session): Nik asked whether SC misreports the Sunbeam's travel (>100%, rear spring always at max).
Checked: SC is RIGHT - the car had the 885 kg Escort's springs; rear range 20-40 capped SC's 38-39 target. Sunbeam v5
makes 46/40 the default and widens ranges (F 30-60, R 20-50) - SC's physics fingerprint will reset its Sunbeam learning.

2026-09-30 (Blender session): the Sunbeam gained ARB_FRONT/ARB_REAR (clicks), DIFF_PRELOAD (Nm value), wider springs
(F 20-90 / R 16-80), damper MAX +45 % (v6), and in v7 a double-wishbone rear with CAMBER_LR/RR + TOE_OUT_LR/RR - SC's
rear-camber/rear-toe/ARB levers now exist on it; fingerprint resets. AC geometry fact worth knowing for any camber-gain
work: WB*/STRUT points are x inboard from the WHEEL CENTRE (not the car centreline), y from wheel centre, z forward.

2026-10-05: ford_escort_mk2_tuned rebuilt as DTM v20 (new physics, 48-item setup incl. ARB, preload, rear camber/toe, wings, 4-way dampers) - SC fingerprint resets; its v19 Nordschleife logs showed 35-90 snaps/100 corners.
