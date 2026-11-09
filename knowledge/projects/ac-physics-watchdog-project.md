---
name: ac-physics-watchdog-project
description: "ac-physics-watchdog — general-purpose telemetry anomaly/cheat-detection tool for Ratty's Racing (not Dacia-specific), architecture, gotchas, live-monitoring status"
metadata: 
  node_type: memory
  type: project
  originSessionId: 697f937a-51fc-411b-a08d-68df19522080
  modified: 2026-10-05T06:20:40.878Z
---

## RESUME HERE (2026-10-05) - committed 6fc6c7c, gearing redesign NOT started
- 6fc6c7c (224 tests): ReplayCSVSource drops a MOVING car's bit-identical repeats (server re-sending the
  last state while packets are lost; then a ~100 m catch-up) + report "lost updates" line (>=1%). Melon_44
  Bremgarten 4 Oct = 9.4% lost -> his teleport/46 bursts/braking flags were a bad connection, not a cheat.
  NOT YET: daemon restart (check status.json nobody connected) + `tally` + RATBOY zip rebuild + README/HANDOFF.
- RATBOY results (D:\Downloads champ JSONs, scratch champ_results.py): Dacia Mondello 1 Oct + Wheel of
  Fortune Bremgarten 4 Oct - no lap-time standouts. Tell Nik.
- GEARING FALSE FLAGS (Frazer Nash, Bremgarten 4 Oct; scratch fn_gears.py/fn_spread.py/gear_estimators.py):
  readings rise with accel = wheelspin (1930s tyres + spool diff POWER=COAST=1.0): gear-aware vs its own
  ratio x stint final, 4th +0.7..+2.5%, 3rd +1.5..+4.5%, 2nd +3.4..+10.5%, 1st up to +14%; braking -3..-6%.
  Current check matches ANY gear x final product (20 dense products) -> flags only where products are sparse
  AND nearly blind to x1.1 cheats. GT3s/Dacia gear-aware within +-2.3%. Sunbeam 29 Sep reads -4.6/-5.4% in
  4th/5th at F4.89 (gearing unchanged since 28 Sep) - CHECK against ground-truth wheel_spin (exact ratio)
  first. tyres.ini RADIUS_ANGULAR_K (radius grows K mm per rad/s): FN 0.08, Dacia 0.044, Sunbeam 0.025, GT3
  0.007 - envelope ignores it. PLAN: gear-aware (per-gear options + one final per stint, envelope keeps
  structure), asymmetric tolerance (tight below; above allow slip ~ratio_k/ratio_top), maybe |a|<=2,
  radius growth; feed identified legal ratio to own-gear power. Validate on all rpm captures + planted x1.1.

## Previous resume point (2026-09-29 21:21)
- Commit 67f48fd (212 tests): gearing read stint by stint (a stop >= 2 s at < 1.5 m/s ends a stint) +
  gear_name() (AC raw 0=R, 1=N, 2=1st - confirmed on real rpm); teleport_onto_car judged by the other car's
  PATH (within 4 m of its line, 15 m behind to 5 m ahead, >25 m/s) - pit boxes sit 10.7 m (Phillip Island)
  or more to the side of fast traffic; no honest landing flagged; planted onto cars at 27-39 m/s caught 4/4
  incl. one 12 m behind. .gitignore covers watchdog.ini.BACKUP*.
- watchdog.ini (gitignored, Nik's) has `[analysis] content_dirs` = D:\Claude\talbot_sunbeam_lotus\
  watchdog_reference;Steam cars - added by the Blender session for the +10% Sunbeam test (backup of the ini
  kept). Daemon restarted 21:18 on 67f48fd with it (pid 42500); tally re-judged 21:21 (27 sessions, same 9
  old flags). RATBOY's zip REBUILT from 67f48fd (219 KB, 212 tests from the extracted copy) - ready to send.
  The zip builder is a scratchpad script (gone in a new session): git ls-files of the committed repo +
  RATBOY's single-server watchdog.ini from "ac-physics-watchdog-race-server BACKUP as sent 2026-09-24.zip" ->
  Downloads\ac-physics-watchdog-race-server 2026-09-29.zip, then run the tests from an extracted copy.
- +10% Sunbeam test DONE (see [[sunbeam-plus10-watchdog-test]]): measured x1.12-1.13 exactly as the files
  predict, but NOT flagged - the Sunbeam honestly sits at 0.82 of its ceiling. Next idea offered to Nik:
  power vs field / vs history on own-gear p95; margin from Thursday 1 Oct race night (first with rpm).
- GROUND TRUTH (commits 0e72f83, 1dc9322, 222 tests): ground_truth.py + RecordGroundTruth.bat read AC's
  shared memory (read-only) for the car driven on this PC -> captures/ground_truth/<time>__<car>__<track>.csv
  (throttle, fuel, air density, rpm, gear, speed, accG, per-wheel slip/load/spin); `groundtruth --analyse`
  judges full-throttle half-seconds vs the files (fuel as weight, AC's air density for drag) + fits force
  factor / extra drag. First real recording 29 Sep 22:03 (Nik driving the honest Sunbeam at the Nurburgring;
  a 2nd recorder with wheel columns from 22:06 in captures/ground_truth/wheels/): at CONFIRMED full throttle
  the Sunbeam reaches 0.846 of its files (2nd gear 0.80, 3rd 0.85) - so not the driver. AC's air there
  1.099 kg/m^3 (watchdog assumes 1.2), fuel 40 L.
  FULL recording (42 min, 40k full-throttle half-seconds): 0.784 overall; fit force x0.78, drag -0.12 m^2 -
  but 1st/2nd are grip-limited; with the files' drag kept, a constant ~0.85 of the files' FORCE reproduces
  3rd 0.826 / 4th 0.803 / 5th ~0.75 (measured 0.71) almost exactly. RULED OUT from AC's own numbers: pedals
  (gas 98%+, brake 0, clutch 1.0), throttle.lut (ends 100|100 on both cars), ballast 0, fuel (counted),
  limiter (3 of 1,864 windows), gearing, drag, wheelspin in 3rd-5th (~1.8% slip in 5th), engine damage.
  Dacia (UDP, fuel/air-corrected) ~0.94 - so the Sunbeam loses ~9% more. LEAD: AC models altitude (air
  1.102 at the Nurburgring, 26 C; ~1.18 at sea level) - if engines lose power in thin air (engine.ini
  ALTITUDE_SENSITIVITY 0.1 on both cars; formula unknown) that's ~7%. TEST proposed to Nik: the Sunbeam at
  a sea-level track (Mondello) with RecordGroundTruth.bat - back to ~0.92+ = altitude (then the watchdog
  must allow for each track's air); still 0.85 = something in our Sunbeam build.
  WHEEL DATA (captures/ground_truth/wheels/, 22:06-22:50 + 22:51-23:01; 41k power-limited windows): a
  force share fits (x0.82, rms 556 N) - adding drag changes nothing (+0.04 m^2, files' drag is right), a
  constant drag fits worse (579 N); front tyres read the same AC slip flat out as coasting (no toe scrub).
  ~5% is MEASUREMENT: driven rears run +4.9% faster than the road at full power, and inferring the ratio
  from rpm/speed inflates the predicted force by (1+slip) - same flaw in power_check's own-gear figure.
  FIX TO BUILD: judge own-gear against each gear's steady (low-slip) ratio from gear_check, per stint.
  Effective rolling radius at speed 0.299 F / 0.302 R vs tyres.ini 0.295 -> best-gear ceiling ~2.5% high.
  So ~10% still genuinely missing - altitude test pending.
  GOTCHA (cost me two false "hung recorder" alarms): on Nik's PC `python` is Python 3.14's install-manager
  shim - the real interpreter is a CHILD process; the shim shows ~0 CPU and WaitReason UserRequest. And
  NTFS shows a file being written as 0 bytes / old mtime until its handle closes. Check the child / the
  task output before calling a process hung.
- Nik's first rpm captures (29 Sep): Dacia @ Mondello (final drive changed mid-session; per stint every
  gear within 2%; best-gear p95 0.87, own-gear 0.891/0.881 per setup) and Huracan GT3 @ Silverstone (gears
  within 0.3%, own-gear 0.93). Own-gear flag line still unset.

`ac-physics-watchdog` is a general-purpose telemetry-based physics-anomaly
tool for **[[rattys-racing-dacia-championship|Ratty's Racing]]** as a whole —
**not exclusive to the Dacia Sandero championship.** That investigation was
just the first real use case that drove its development; it applies to any
car/event/server in the league. Don't assume a future capture or analysis
request is about that specific case or its (undisclosed) suspect unless
said so.

Source: `C:\Users\nickl\Downloads\ac-physics-watchdog\` (Python, tested with
pytest — `python -m pytest tests/`). **Git repo since 2026-09-25** (initial
commit 86c33b2, branch main, 128 tests passing at that point). Git for
Windows was installed that day via winget at `C:\Program Files\Git\cmd\git.exe`
(may not be on PATH in an older shell - use the full path). Repo-local
`core.autocrlf=false` on purpose: CRLF conversion would break the hash-compare
with the AC-deployed recorder copy. Repo-local author "Nick". The stale
pre-daemon nested copy is renamed `_old_ac-physics-watchdog_2026-09-20/`
and gitignored - never run or edit it. Commit before making changes.
Sessions deliberately stay in `D:\Claude` (Nik's call, 2026-09-25) because
all memory lives under that folder's project dir - work on the repo with
full paths and `git -C <repo>`; don't suggest switching the working folder. In-game companion app deployed to
`D:\SteamLibrary\steamapps\common\assettocorsa\apps\python\PhysicsWatchdogRecorder\`
— keep both copies in sync by hand (hash-compare after editing either) and
remember AC only reloads Python apps on a full process restart, so an edit
never affects an already-running capture.

**Two independent analysis modes**, `python -m physics_watchdog <cmd>`:
- `replay <csv>` — per-car absolute physics limits (teleport/accel/cornering
  vs. that car's own physical ceiling). Good for a blatant hack, weak for a
  one-make grid since a real advantage never crosses an absolute limit.
- `compare <csv>` — ranks all cars against the field's own median+MAD
  (robust to one outlier dragging its own baseline). **This is the real
  signal for a one-make race** — always run both, but weight `compare`.
- `live`/`record <host> <port> --local-port <port>` — live UDP capture
  straight from the AC dedicated server's plugin protocol (own client,
  `physics_watchdog.udp_client`), separate from the in-game recorder app.
  **Does NOT produce a session_info.csv** (that sidecar is in-game-app-only)
  — a live capture identifies drivers only by car_id, cross-reference
  against the server's live-timing chat log by connect/disconnect timestamp
  if you need a name.

**Known structural limitation, not a bug:** wheel-physics columns
(slip/load/nd_slip) are only ever real for **car_id 0** — whichever car
AC's engine is fully, locally simulating in that specific replay/session.
Every other car gets a flat sentinel (`nd_slip=0.001, load=100.0`, zero
variance). Confirmed both in a replay and structurally (CSP's
`ac.getCarPhysics()` is documented "not available in replays or for remote
cars" — same wall from the Lua side, so a Lua rewrite wouldn't fix it
either; not worth doing for this reason). **Open, unresolved question worth
retesting**: whether car_id 0's *position/velocity* data (not just wheel
physics) is also un-smoothed/full-resolution vs. other cars' possibly
network-interpolated feed — this would explain unusually large braking/
cornering peaks for whoever happens to be car_id 0, as an artifact rather
than real driving difference. Test by checking if the same peak-stat gap
appears for car_id 0 regardless of who that is across different captures.

**Live monitoring confirmed working end-to-end 2026-09-21** against the
real Sunday Ratty's Racing server: Listen Address `127.0.0.1:9701`, Send
Address moved from the original `127.0.0.1:9700` to `127.0.0.1:9702` (a
free port, since AC's plugin only accepts one consumer at the configured
Send Address). Verified Server Manager's own live-timing/stored-times kept
working fine concurrently while `physics_watchdog` was also attached —
cross-checked a live capture's car_id against the server's chat-log
connect/disconnect timestamps and it matched exactly. Send Address is
staying at 9702 going forward (user's call).

Real, known tool bug (confirmed, not yet fixed): `field_compare.py`'s
`dist km` column sums raw frame-to-frame distance without filtering the
same session-start teleport artifact `detector.py` already knows to flag —
produces absurd totals (1000s of km in a 25-min race) for any driver who
happened to get a teleport-glitched sample. Doesn't affect the
percentile-based standout stats, only that one column. Confirmed by
re-running `compare` on the same capture with the first 10s trimmed
(`tools/shrink_for_upload.py --window 10 999999 --target-mb <big>`) — distances
became normal, standout stats were unchanged.

**The one-button monitor (built 2026-09-22, running on the user's PC):**
`StartWatchdog.bat` / `StopWatchdog.bat` (desktop shortcuts "AC Watchdog -
Start/Stop") run `python -m physics_watchdog daemon` under pythonw with a
pystray tray icon (grey idle / green capturing / orange flagged). It sits
on the Sunday server's UDP plugin port (9701/9702), auto-opens a capture
folder per session (`captures/<date>_<track>_<session>/capture.csv` +
session_info from NEW_CONNECTION/CAR_INFO + laps.csv + events.csv +
meta.json), closes on END_SESSION / session change / 60s idle, then
analyses in a thread: detector + field comparison, anomalies cross-
referenced against the collision log and a 10s session-start grace, plus
the session's lap-time results pulled from Server Manager's web API
(`/results/download/<file>.json`, named by the END_SESSION packet) →
`report.txt` with a VERDICT line, `captures/latest_report.txt`,
`captures/flags.log`, tray notification. `python -m physics_watchdog
results [--latest|--type RACE|--file X|--json path]` does the lap-time
ranking for any past session with no capture — the "investigate later
without being on" path. Server Manager API facts: endpoints answer
unauthenticated on the league server; `?server=1` selects Sunday; rate
limit 5 req/20s. Config `watchdog.ini` (auto-created); log
`captures/watchdog.log`. **Multi-server since 2026-09-22:** one daemon,
one `[server.<name>]` section each, one `ServerMonitor` thread per server,
captures under `captures/<server>/`. Ratty's Racing runs FOUR instances via
`E:\AC Manager\assetto-multiserver-manager.exe` (live configs at
`E:\AC Manager\servers\SERVER_0N\assetto\cfg\server_cfg.ini`): SERVER_00
Thursday (?server=0), SERVER_01 Sunday (1, UDP plugin 9701/9702 — the only
one configured), SERVER_02 "GT3 Silverstone" (2), SERVER_03 Drift (3). As of
2026-09-25 Sunday (9701/9702), Thursday (9703/9704) and GT3 (9705/9706) are
all enabled and monitored; only Drift (9707/9708) is still disabled - it
needs its ports set in Server Manager first. Real bug found by the end-to-end test: Windows
UDP `SIO_UDP_CONNRESET` — a send to a dead port makes the next recvfrom
raise ConnectionResetError, which would have killed the daemon every time
Server Manager restarted the AC server; fixed in udp_client + pinned by a
test. 62 tests pass. Verified against a fake server end-to-end and a live
idle run; **not yet seen recording a real session** — that's the next
Sunday. User's brief for it: unobtrusive, "press a button and it's on",
flags suspicions, can draw on server results when not in game.

**First real daemon captures, 2026-09-22 — both flagged, both false
positives, both fixed same day.** Two solo shakedown sessions (Thursday
practice @ Taupo, GT3 qualifying @ Silverstone) auto-captured/analysed
correctly (names, car models, session boundaries all right) but both got
FLAGGED. Real findings, not capture bugs:
1. `detector.py`'s parked-car guard (`STATIONARY_SPEED_MS`) only suppressed
   a position jump when the car was stationary on BOTH sides — missed
   "driver returns to pits" / "session rotates car to next grid slot",
   where it's moving right up to the jump. Fixed: now `settled = jumped
   AND sample stationary after` (checked against teleport, decel AND
   cornering, not just teleport — both real cases showed teleport +
   impossible_accel together). **First attempt was too broad** — dropping
   the "AND jumped" requirement also suppressed a genuinely impossible
   instant stop with no position discontinuity at all; caught immediately
   because `test_impossible_deceleration_detected` went red. Lesson: this
   project's recurring pattern (front/rear ternary in Setup Coach, the
   rear-rebound histogram bias) of "a plausible-sounding fix quietly
   breaks an unrelated case" struck again, same as always caught by
   already having a test for the OTHER case, not by care while writing it.
2. `ks_lamborghini_huracan_gt3` had no `car_limits.py` entry — real, clean,
   continuous hard braking (54→30 m/s) tripped the generic default's
   `max_decel_ms2=20.0` eighteen times. Added a real entry derived from
   `data.acd` (decrypted with [[setup-coach-project]]'s
   `setupcoach-tools\acd\acd_decoder.py` — same tool, different project),
   same methodology as the Dacia entry: top_speed_ms from gearbox math
   (85.1 m/s at the limiter + margin), accel/decel/lateral-g left at the
   generous Dacia/RSS collision-tolerance numbers on purpose (this car
   races wheel-to-wheel, tightening those to performance would flag every
   incident — same reasoning as the Dacia entry's own comment).
3. `physics_watchdog report --save` was writing a stray
   `flags.log`/`latest_report.txt` into the capture's per-server folder
   instead of the daemon's shared `captures/` root — it guessed the root
   from the path (`dirname(capture_dir)`), which is only correct for a
   single-server layout. Fixed by making it explicit (`--captures-root`,
   opt-in, `None` = just write report.txt) instead of guessed.

**Process layout since 2026-09-23 (after a real outage):** Windows closed
the daemon as "not responding" at 02:23 (Application event 1002 /
AppHangB1 - check `Get-WinEvent` Application log for pythonw if it ever
dies again) and it stayed dead 11 hours. The only window it had was
pystray's, in-process. Now: `StartWatchdog.bat` -> `supervise`
(windowless, supervisor.py) -> children `daemon` (windowless, writes
`captures/status.json` heartbeat every 5s) + `tray` (own process, reads
status.json, red = no heartbeat 30s). Supervisor restarts on unexpected
exit with backoff 5/15/60/300s, kills+restarts a daemon silent for 180s,
gives up on the tray after 5 failures/10min, never on the daemon.
Daemon exit codes: 0 clean, 2 config, 3 all monitors down (retry), 4
already running. Supervised daemon (env PHYSICS_WATCHDOG_SUPERVISED=1)
leaves the STOP file for the supervisor. `daemon --stop` kills the
supervisor tree FIRST on timeout (killing only the daemon would get it
restarted). Children's stderr -> `captures/daemon.stderr.log` /
`tray.stderr.log`. Doesn't survive a reboot on Nik's PC - autostart NOT
enabled there (only offered); RATBOY's zip (rebuilt 2026-09-23 with this
version) uses EnableAutostart.bat. When checking "is monitoring OK?",
check `daemon --status` AND the log tail AND whether a "watchdog stopped"
line follows the last start - a start with no stop and no process means
it was killed. A "STOP file seen" line means a human stopped it (tray
menu / StopWatchdog.bat) - ask before restarting, don't just restart.
**Lesson from my own supervisor (2026-09-24):** the first version killed a
healthy daemon on ONE failed read of status.json - on Windows, a file
atomically replaced every 5s while other processes read it will sometimes
refuse an open. A liveness check must require the failure to persist for
the whole window (track "last provable heartbeat", don't judge by the
latest read) - same shape as this project's other "one sample isn't a
pattern" lessons. Fixed; regression-tested against the old logic first.

**Orphaned-capture recovery, added 2026-09-23** in response to "can you
automatically check monitoring?" — checking found 2 real capture folders
(sunday + gt3) stuck open forever from an earlier daemon process that got
killed abruptly (both stopped at the exact same instant, 18:11:45, almost
certainly one of MY OWN background-task hard-kills during the previous
day's dev iteration, not a code bug). Nothing had been recovering these on
its own — real gap for a system meant to be unattended. Fixed:
`session_recorder.find_orphaned_captures()` (any folder with capture.csv
but no report.txt) + `repair_orphan_meta()` (recomputes rows/cars_seen/
duration_s from the real CSV, since the stale open-time meta.json just
says rows=0), run by `Watchdog._recover_orphans()` once at startup before
any monitor thread exists — safe by construction, a fresh process's
SessionRecorders always start with capture=None, so anything matching the
orphan signature at that exact moment can only be left over from a
previous process. Proven live (stopped the real daemon, planted a
synthetic orphan, restarted, watched it get recovered before the servers
even reconnected) as well as unit-tested. Bonus finding from recovering
the real orphans by hand: Sunday's session (SryLostIntrest,
`frazer_nash_TT_1934`, no car_limits.py entry) flagged 18 anomalies,
mostly kerb strikes/spins in an untuned generic-default car. **I called
its 888 m jump (t=674.6) a "genuine teleport-while-still-driving" - WRONG,
found 2026-09-24:** it lands exactly on the car's own pit box (its first
sample of the session, same spot as its two other resets) at 0.59 m/s -
a return to pits, only flagged because the guard's cut-off is 0.5 m/s.
Lesson: check WHERE a jump lands (own pit box / start slot) before
calling it a teleport.

**DONE 2026-09-24 - per-car limits are automatic (car_data.py):**
accel/decel/lateral = collision tolerance (90/175/8.0) for EVERY car, now
the generic default; top-speed ceiling derived from the car's own gearbox
(data.acd via vendored acd.py): min(tallest legal x1.2, max(default
gearing x1.2, 100)). Trusted only after checking against real data (Dacia
reproduces hand value 49.91 exactly; every observed capture top speed
under its ceiling; Frazer Nash's 888 m jump + 10g spikes still flagged
while braking noise vanished - the jump later turned out to be a pit
reset, see above). Gotchas found: a mod's data.acd may
only decrypt with the LOWERCASED folder name (frazer_nash_TT_1934) - wrong
key gives garbage, not an error, so validate the output reads as INI; GT3
.rto files hold absurdly long final drives (tallest legal alone is
meaningless); the old `ks_ferrari_458_gt2` entry never matched (real id
`ferrari_458_gt2`). Content found via Steam's libraryfolders.vdf, or
`[analysis] content_dirs` in watchdog.ini. Derivations logged to
`captures/derived_limits.json` and quoted in every report.

**First race night on RATBOY's PC, Thu 2026-09-24 (Dacia @ Taupo, 13
drivers, practice/qualy/2 races):** worked end to end - names, sessions,
Server Manager results all fine, no crashes; no tray (pystray not
installed there, harmless). Nik brought the captures back as a Google
Drive zip (`D:\Downloads\captures-20260924T204641Z-1-001.zip`). Verdict:
nothing suspicious, but the absolute detector threw 1,869 flags, ALL
noise: ~1,770 were 6-10 m "teleports" in 0.1 s = remote drivers'
internet jitter (a late position update then a catch-up); the rest were
pit resets landing at 0.5-0.8 m/s (guard cut-off 0.5) and a few lag
catch-ups. Key facts learned: the HOST's own car (RATBOY, on the server
PC) has zero jitter, so it shows the LOWEST raw 0.1 s braking/lateral
percentiles every session - raw per-sample percentiles partly measure
connection quality (CatflooCat, laggiest, showed the highest). The one
field standout (Bozza, race 2, accel p99.5 +81%) was a crash: 69 contact
events, 7 laps, top samples all within 2 s of contact at <17 m/s; over 1 s
with contact excluded he sits at the field median every session. Session
changes arrive as SESSION_INFO(next) -> END_SESSION -> car updates ->
NEW_SESSION, which leaves an empty stub folder per session change (real
capture gets a `_2` suffix) and meta.json labelled with the NEXT session.
**Fixed same night (Nik: "Yes"):** teleport check over a 1 s window;
reset cut-off 1.5 m/s, resets kept on `PhysicsWatchdog.resets` and listed
per driver in the report (never counted); field comparison skips +-2 s
around logged contact for ALL behaviour percentiles incl. speed (a shove
inflates top speed too - caught by the new test); recorder stamps each
capture with its own session + waits up to 10 s after END_SESSION for
NEW_SESSION. 119 tests, all 8 new ones proven to fail on the old code.
Re-run: race night 4/4 clean; Nik's own servers clean except known
one-sample cornering spikes. RATBOY's zip rebuilt (154 KB; SETUP.md now
has "Updating"); Nik's local watchdog restarted on the new code.
**I proposed then DROPPED the 0.5 s windowed derivative** after testing
it: it tightens the field so much (lat-g p99.5 within 0.01 g over 13
drivers) that tiny differences become standouts (laggy connection,
pit-exit launch count). Lesson: validate a "more robust" metric against
the false-positive side on real multi-driver data before promising it.
Open follow-ups in HANDOFF: windowed metric done properly (MAD floor +
accel at speed), and don't rank tiny fields (a 3-car Thursday practice
flagged Darren Shepsman braking +12% - two-person "field").

**Direction after the race night (2026-09-24):** Nik questioned how
filtering noise will ever point to cheating, and expects "once we have
more data we can make it more useful". He declined further filters for
now ("not just yet" to the small-field rule). Agreed plan: keep capturing
race nights, then build a cross-night per-driver "car fingerprint" on the
measures skill can't move much - acceleration at speed (30-38 m/s band:
whole grid 1.18-1.34 m/s^2 every session on 2026-09-24; ~10% more power
would give ~1.45-1.5), cornering limit (grid within ~1% with 0.5 s
smoothing), clean-air top speed - and calibrate "stands out" from the
honest spread across nights. Frame each noise fix as making real flags
readable (1,869 false flags would bury a real one), and remember raw
captures are kept, so everything can be re-analysed later.

**POWER CHECK built 2026-09-29 (idea 1 of 3 from the Sunbeam project, Nik:
"Do 1"):** `envelope.py` (ceiling a(v) from the car's own files: power.lut
= WHEEL torque x best legal ratio incl. .rto lists / driven tyre radius,
x (1 + wastegated turbo boost summed), minus drag 0.5*1.2*CdA*v^2 (wings at
lowest legal drag, LUT_GH_CD min) and rolling resistance PER kN OF WEIGHT
(validated flat vs speed; "Newtons per tyre" drifted), over mass + engine/
gearbox/wheel inertia) + `power_check.py` (1 s least-squares speed slope +
g*grade above 24 m/s, minus 2 s around contacts / car <30 m ahead / ceiling
<0.25; flag if p95 > 1.05) + report section "Power check" + anomaly kind
"over_power" (tally: "power") + LimitsResolver.envelope(). 152 tests (TDD).
Real data: honest 0.70-0.99 (race-night Dacias 0.85-0.99, GT3s 0.78-0.88),
nobody over 1.0 anywhere; software +10% power 1.01-1.18, +20% 1.21-1.41.
Over-1.0 windows cluster at the same track spots for all drivers (+-5%
track noise); slipstream only ~2% on the Dacia. Daemon restarted on it
2026-09-29 07:02; `tally` re-judged all history (no power flags).
Committed on main: 9355341 (power), 2c0bc87 (grip), 2138d8f (docs: "Nik"
not "Nick" - see [[user-name-nik]]; editing power_check/grip_check even in
a docstring changes the tally's code hash, so restart the daemon + run
`tally` after any such commit). **GRIP CHECK built the
same day** (Nik: "do what you can without me in game"): `grip_check.py` +
envelope.max_lateral/max_braking (grippiest compound, DY_REF/DX_REF x
(Fz/FZ0)^(LS-1) at EQUAL load on all 4 tyres, camber bonus
1+D0^2/(4|D1|), all downforce; braking adds the MOST drag), measured over
the power check's shared 1 s windows (power_check.clean_windows - now also
skips any window whose path averages > 150 m/s: resets/garbled samples):
cornering = mean speed x slope of the velocity's heading, braking =
-(speed slope + g*grade). Tyre files are NOT tight ceilings: honest top-1%
cornering 0.60-1.01 (Dacia at Taupo 0.80-0.82, every driver every session;
Mondello 0.90-0.96 - its surfaces.ini ROAD FRICTION=1.12 vs Taupo 0.98;
Frazer Nash up to 1.01, its file understates grip; GT3 0.85-0.89; Camotos
0.60-0.66), braking 0.61-0.98. So the flag is a blatant-hack backstop: p99
> 1.30 AND at >= 5 separate 100 m places (the Frazer Nash has 5-8 places
over 1.3 - only its 1.01 p99 keeps it clear; both rules are needed).
Kinds over_grip_cornering/_braking (tally "grip"). 167 tests. Daemon
restarted on 2138d8f 2026-09-29 09:46; `tally` re-judged (no power or grip
flags anywhere). NOT BUILT (proposed): a field / cross-night comparison on
the cornering number with a minimum effect size - the way to catch a +10%
grip car. RATBOY's update: `Downloads\ac-physics-watchdog-race-server
2026-09-29.zip` (built from 2138d8f with his own single-server
watchdog.ini by the scratchpad script build_race_zip.py - git ls-files +
RATBOY's ini from the old zip; 167 tests pass from the extracted copy); the zip he has now
is kept as `...race-server BACKUP as sent 2026-09-24.zip`. Nik sends it;
RATBOY follows SETUP.md "Updating".
**Aimed at the Alien cheat, same day** (see [[alien-cheat-analysis]]; Nik: "Yes
go ahead"): a5348b2 = captures keep `gear,rpm,spline` (CAR_UPDATE always
carried them; daemon recording them since 2026-09-29 ~11:20); 8cd17de =
gear_check.py (rpm vs speed -> overall ratio per raw gear value, steady
samples only: >10 m/s, |a|<3, MAD/median<3%, >=30 samples; flag >5% off
every legal gear x final product - UNVALIDATED, no real rpm capture existed),
power "own gear" p95 (torque at real rpm through real ratio via
CarEnvelope.accel_at - reported only, needs calibration from real
captures), grip_check.cornering_vs_field (>6% over the median of >=4 other
judged cars of the model), tally history comparison (driver_flags.json
schema 2 keeps per-driver measures cornering/power/power_own; >6% over the
median of >=5 OTHER drivers' sessions at the same track+model -> "cornering
vs history", computed at every tally). Real data: race-2 cornering
0.798-0.809, no new flags anywhere after re-judging. Daemon restarted on
8cd17de 11:44; RATBOY zip rebuilt from 8cd17de (206 KB, 189 tests from the
extracted copy) - still not sent. NEXT: when the first captures with rpm
exist, check the gearing readings (AC's gear numbering, honest wheelspin
offset) and where honest own-gear power sits, then set its flag line.
Ideas 2 (known-cheat test bench: Sunbeam copies +5/10/20% via
build_car.CRANK_TORQUE, driven with the daemon on) and 3 (AC shared memory
ground truth vs the UDP feed, car_id-0 question) = scheduled reminder task
`remind-watchdog-ideas-2-3`, 29 Sep 18:00.
Facts found: Nik's SERVER_00 config has DisableChecksums=false (RATBOY's
race server unknown - ask him); the recorder app's recording.csv of 28 Sep
20:26 is STATIONARY (max 1 km/h) and each run overwrites it - no Sunbeam
driving data yet; names differ between Nik's servers and RATBOY's
(Gouranga_Man/Gouranga Man, Philsmin/philsmin) so the tally splits them.

**Aimed at Alien V2 / Predator, 2026-09-29 afternoon** (Nik: "Build all you
need to build"; see [[alien-cheat-analysis]]): commit e7d7b58, 205 tests.
Calibrated on all 32 captures FIRST (scratchpad calibrate_new_checks.py /
calibrate_landings.py): honest braking p99 vs same-model field -16%..+14%
(drivers brake differently; cornering within 1%) -> BRAKING margin 0.25
for field (grip_check.braking_vs_field) and history (tally, schema 3 keeps
"braking"); power windows >1.5x ceiling at <=2 separate 100 m places for
every honest car -> "power_bursts" = >1.5 at 5+ places (PLACE_M moved to
power_check); 205 slow landings ("resets"), none within 18.7 m of a car
doing >20 m/s (pit-lane pass 6 m at 19.4 m/s) -> "teleport_onto_car" =
landed <1.5 m/s within 10 m of a car doing >25 m/s (other car's last
update carried forward by velocity, max age 0.5 s); TELEPORT_KINDS are
never excused by a collision any more. Re-judge: no new flags anywhere.
Planted into copies of the real race_2 capture (scratchpad
inject_cheats.py): teleport onto cars at 27-39 m/s caught 3/3, at 21-23 m/s
missed (by design); bursts +2/+3 m/s^2 x8 caught (6 places), +1 -> 4
places; braking push +3 m/s^2 on the median braker caught (+27%), +2 not.
Also pytest.ini (testpaths=tests - bare pytest used to wander into the
gitignored _old_* copy and error), tools/physics_permission_probe (read-only
CSP app showing physics.allowed(), untested in game - luac + stub run only).
Daemon restarted on e7d7b58 16:26 (nobody connected); tally re-judged 16:29;
RATBOY zip REBUILT from e7d7b58 (216 KB, 205 tests from the extracted copy)
- still not sent.

**Flag tally, built 2026-09-24** (Nik wanted "a tally of repeat
offenders" to get ideas for later; small-field rule deferred "later"):
`tally.py` - `driver_flags.json` per analysed capture, `captures/
flag_tally.txt` per driver, daemon refreshes it (no re-analysis),
`physics_watchdog tally` re-judges stale ones (hash of the analysis
modules), `physics_watchdog import <zip>` files RATBOY's Drive zips under
captures/race/ (race night of 2026-09-24 already imported). Matching is
by NAME - "Nicklearse" (local servers) vs "Nicklearse101" (race server)
are two rows; GUID matching offered as a follow-up. RATBOY's installed
zip predates the tally (nothing needed from him; import tallies his
sessions). **Gotcha:** never pipe StartWatchdog.bat's output (`| Out-Null`)
- the detached supervisor inherits the pipe and the tool call hangs;
don't kill that task (killing a task tree has killed the daemon before) -
`daemon --stop` releases it, then start unpiped.

**First real finding, 2026-09-27 (race 2 of 24 Sep, results fetched while
the server was on):** the lap-time check flagged RATBOY's sector 2 best
(41.536 vs field median 43.720). Traced with the capture: RATBOY's LAST lap ran
straight across the inside of the hook just after the S1/S2 line - 176 m vs
median 209 m, 6.6 s vs 9.5 s, up to ~20-30 m past the track's AI edges, 0
cuts recorded, nobody within 40 m, no collision; server timestamps confirm
the lap really took ~117 s. Of 569 passes that night (all drivers, all
sessions) only 3 were >15 m short, all RATBOY (race 2 laps 13 and 7,
qualifying on a lap that recorded 3 cuts). No position changed (P9, 4.9 s
behind P8). Physics on that lap was normal (outside the cut, speeds matched
the other laps; top speed 39.8 m/s vs 38.4-40.4) and the current physics
checks flag nobody in race 2 - so in the tool's terms race 2 is CLEAN.
Nik's answer (2026-09-28): shortcuts are out of scope, physics
manipulation only - see [[watchdog-scope-physics-only]]. Reusable method
(scratchpad scripts, not in the repo): align results.json laps to laps.csv
by exact lap_time_ms, sector lines = position at lap start + S1; gate A->B
route length/time per pass vs the field; AI edges from `ai/fast_lane.ai` v7
(16-byte header, N x (x,y,z,len,id), int N, N x 18 floats: [5] sideLeft,
[6] sideRight); map.png pixel = ((x+X_OFFSET)/SCALE_FACTOR,
(z+Z_OFFSET)/SCALE_FACTOR) from data/map.ini (map.png is the AI line drawn
DRAWING_SIZE wide, not the real surface) - use it for physics questions
only, never to build shortcut detection. 27 Sep (Phillip Island) lap-time
check via the scheduled job: no standouts in qualifying or either race.
Also: imported
race-night report.txt files are RATBOY's originals (old code, stale
FLAGGED verdicts) - only driver_flags.json was re-judged (clean).

**Was the top TO DO as of 2026-09-22: stop hand-deriving `car_limits.py`
per car.** User's explicit ask right after the Huracan GT3 work: "will
need to work a system, where you dont need to keep analysing cars." Full
reasoning/options are in HANDOFF.md's "To do" list — worth reading before
picking this up, since it also questions whether the real fix is loosening
DEFAULT_LIMITS's accel/decel/lateral-g (already collision-tolerant-only by
design) rather than adding more per-car entries at all.

**Rest of the TO DO list lives in `HANDOFF.md` ("To do")** — the user asked to keep
the **Discord webhook** (daemon posts each session's report.txt to a
private channel when the session ends, so reports get off RATBOY's
race-server PC while it's still on) parked there: "we'll work on Discord
later, keep it on the To Do List" (2026-09-22). Raise it when the race
server is set up or when they ask what's next; it needs a webhook URL
from them. Race server = RATBOY's PC, only on for races; Nik has web
access to its Server Manager ([[ratboy-race-server]] - address, Thu/Sun
19:30-22:00) and will set the plugin ports himself;
RATBOY's part is Python + unzip + EnableAutostart.bat (zip with a
pre-filled single-server `watchdog.ini` and `SETUP.md` was sent
2026-09-22).

**New, untested addition (2026-09-21): `csp_online/`** — a CSP Lua "online
script" (`broadcaster/broadcaster.lua`, server-pushed to every connected
client, reads that client's own wheel physics, broadcasts via
`ac.OnlineEvent`) plus a normal Lua app (`collector/`, has file I/O unlike
the online-script sandbox, captures position/velocity for every car and
logs every broadcaster's wheel data into one CSV matching
`PhysicsWatchdogRecorder.py`'s schema). Purpose: the owner-only wheel-
physics wall applies live or replayed, Python or Lua — this is a way
around it for LIVE sessions specifically, since a client is always "local"
to its own car. General-purpose across any car, not Dacia-specific — user
was explicit about this. Only syntax-checked (`luac -p`), never run
against real `ac`/`ui`/`script` — see `csp_online/DEPLOYMENT.md` for the
full list of what's confirmed from CSP's own shipped SDK
(`extension/internal/lua-sdk/ac_online_script/`) vs. still needs a live
test (chiefly: whether slipRatio/slipAngle/ndSlip are actually readable
for remote cars via this Lua path the way the Python bridge's read
wasn't). Test plan is practice server first, real cars, before ever
touching the race server. Non-obvious gotcha worth remembering: broadcast
under `car.sessionID`, never `car.index` — `ac.getCar(0)` (=own car)
always self-reports `.index = 0` regardless of real race slot, so `.index`
would collide every broadcaster under the same fake ID.

**Why:** burned real effort this session assuming things (a "bug" that was
actually already documented as a deliberate tradeoff in `recorder.py`'s own
docstring) before reading what was already there — check existing
docstrings/README/HANDOFF before flagging something as new.
**How to apply:** before touching this repo again, re-read `README.md` and
`HANDOFF.md` in the repo root — they're kept current and detailed, written
in the same style as this memory, and often already answer the question.
