---
name: sunbeam-plus10-watchdog-test
description: "Known-cheat test: +10% Sunbeam BUILT 2026-09-29 20:30 (CHEAT in CM) + watchdog reference/content_dirs set; still to do: daemon restart (after the watchdog WIP), Server Manager event, Nik drives it"
metadata:
  node_type: memory
  type: project
  originSessionId: 697f937a-51fc-411b-a08d-68df19522080
  modified: 2026-09-29T20:22:04.549Z
---

## RESULT 2026-09-29 20:40-21:16 - TEST DRIVEN (Sunday server switched to ks_nurburgring by Nik)
Capture `captures/sunday/2026-09-29_2040_ks_nurburgring_practice` (both cars, same driver name "Nicklearse":
car 1 = honest v4, car 2 = cheat; report came out CLEAN). Judged against the honest reference:
- honest p95 0.815 (own gear 0.829), cheat 0.918 (own gear 0.929) -> x1.127 / x1.121, matching the files'
  prediction (+10.6% at 25 m/s rising to +13.4% at 45 - drag unchanged); by speed band x1.09 (24-30 m/s),
  x1.10, x1.12, x1.17 (>42). The watchdog MEASURES +10% precisely.
- NOT flagged: the absolute line is p95 > 1.05 of the car's theoretical ceiling, set on Dacias that honestly
  reach 0.85-0.99; this Sunbeam honestly reaches only 0.82, so +10% lands at 0.92 (it would need ~+28%).
- Lesson: a strong car needs RELATIVE checks - power vs field (same model) and vs history (other drivers'
  sessions at the track+car), on own-gear p95, like cornering. Honest same-driver spread is tiny (Nik's Dacia
  setups 0.891 vs 0.881); the cross-driver own-gear spread is unknown until Thursday 1 Oct's race night (first
  with rpm). Offered to Nik; nothing built yet. Also: the report's power/gearing tables can't tell two cars
  with the same driver name apart (show the model when a name repeats).
- Nik to put the Sunday server back to Phillip Island (league practice).

## STATUS 2026-09-29 ~20:30 - CAR BUILT (Blender session, Nik: "build the +10% cheat lotus", name must say Cheat in CM)
- `tools/make_cheat_car.py 10` (Sunbeam repo, commit f5eee98) -> `content/cars/talbot_sunbeam_lotus_81_works_cheat_plus10`,
  CM + in-game name "Talbot Sunbeam CHEAT +10% power (watchdog test)", description "WATCHDOG TEST CAR - NOT FOR
  RACING...", specs 352 bhp. Copy of live v4 (dampers incl.); ONLY power.lut x1.10 (+ SCREEN_NAME) differ - asserted.
  Setups copied. Id is `_cheat_plus10` (not the `_test_plus10` planned below).
- Honest reference: `D:\Claude\talbot_sunbeam_lotus\watchdog_reference\<cheat id>\data` (gitignored; on D: so it can
  never reach RATBOY's zip). Nik's watchdog.ini had NO content_dirs key (auto-detect) - added under [analysis]:
  reference;D:\SteamLibrary\...\content\cars (CRLF kept; copy `watchdog.ini.BACKUP-2026-09-29-before-cheat-reference`).
  Verified with the watchdog's own code: cheat id -> reference, live id -> Steam, all 6 cars in derived_limits.json
  resolve as before, CLI _limits() uses it. Envelope: real +10% car max accel 1.102/1.106/1.115/1.134 x honest at
  15/25/35/45 m/s (drag unchanged, so the surplus grows with speed) -> expect power check ~1.10-1.13.
- NOT done: daemon restart (reads content_dirs only at start) - HOLD until the Anti Cheat session's uncommitted
  WIP (gear stints done, report.py wording + teleport fix TODO, 208 pass / 2 fail) is finished + committed, nobody
  connected. Until then `python -m physics_watchdog replay/compare <capture.csv>` already judges it right (CLI reads
  watchdog.ini). Then steps 3-4 below (Server Manager upload of v4 + cheat car, Nik drives both).
- If the live Sunbeam physics change (v5...), delete the cheat car + its reference and re-run the tool.

Nik asked (2026-09-29 ~19:30) "now make the sunbeam +10%", then parked it: "we'll do it another time,
make a note". NOTHING was built or changed for it yet. It is idea 2 of the watchdog ideas (known-cheat test
bench) - see [[ac-physics-watchdog-project]] and [[talbot-sunbeam-lotus-ac-mod]].

Purpose: drive a real +10% car past the watchdog to measure the true detection floor, and above all to set
the "own gear" power flag line (honest own-gear p95 so far: Dacia 0.891/0.881 on two setups, Huracan GT3
0.93 - Nik's first rpm captures, 29 Sep). +10% should read ~1.1x honest in its own gear.

Plan worked out:
1. New tool in the Sunbeam repo, modelled on `D:\Claude\talbot_sunbeam_lotus\tools\backup_car.py`: copy the
   live car `talbot_sunbeam_lotus_81_works` (v4) to `talbot_sunbeam_lotus_81_works_test_plus10`, shown as
   something like "Talbot Sunbeam TEST +10% power (watchdog test)" (must never look like a newer live car -
   [[feedback-backup-naming]]); decode data.acd if packed (acd is keyed to the folder name); rename sfx bank +
   GUIDs.txt; copy Nik's setups; scale power.lut (WHEEL torque) x1.10. Refuse while acs.exe runs.
2. The watchdog must judge it against the HONEST files, as a server judges a cheater against its own copy:
   a reference folder (e.g. `ac-physics-watchdog\reference_cars\talbot_sunbeam_lotus_81_works_test_plus10\data\`
   holding the honest v4 data) listed FIRST in watchdog.ini `[analysis] content_dirs` (";"-separated; blank =
   Steam auto-detect, so add the Steam `content\cars` after it). LimitsResolver takes the first folder that has
   the car. Restart the daemon afterwards (only when status.json shows nobody connected).
3. Server: the Sunbeam is on NO server. Server Manager `E:\AC Manager` runs four league servers - SERVER_00
   Thursday (Dacia, Mondello, UDP 9703/9704), SERVER_01 Sunday (axfor_camotos_r6, Phillip Island, 9701/9702),
   SERVER_02 GT3 Silverstone (9705/9706), SERVER_03 Drift (Brooklyn Park, UDP plugin NOT set; watchdog
   [server.drift] disabled, would be 9707/9708). Nik must upload both cars (honest v4 + test) to Server Manager
   and run an event on a server of his choosing - his call, they're all league servers.
4. Nik drives ~5 laps in the honest v4, then ~5 in the +10% car, same track and session. Compare best-gear and
   own-gear p95; set the own-gear flag line from it.

2026-09-29 23:18: cheat car REBUILT from v5 (springs 46/40); reference = v5 honest files (verified identical to live);
envelope gap unchanged 1.102-1.134. The v4-based cheat car/reference/setups are in the Sunbeam archive.

2026-09-30: live Sunbeam is now v7 (double-wishbone rear). The cheat car + its reference stay v5-based (consistent with
each other); rebuild with make_cheat_car.py only if a new test should match the live car.
