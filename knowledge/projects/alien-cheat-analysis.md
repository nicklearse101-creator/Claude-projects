---
name: alien-cheat-analysis
description: "AC cheat tools and what they do to physics: Alien v1 (static analysis), Alien V2 + Predator (source; same DLL), No Hesi Cheats, CSP's ALLOW_APPS track opt-in - and which watchdog checks see each part"
metadata:
  node_type: memory
  type: reference
  originSessionId: 697f937a-51fc-411b-a08d-68df19522080
  modified: 2026-09-29T15:30:25.481Z
---

Nik uploaded `acalien_unknowncheats.me__1.zip` (2026-09-29, sha256 66e7c4ed...6d30d)
and asked for everything it does to physics - **never install or run it** (his words:
"Do not install it to my game"). Analysed statically only: files read from the zip in
memory, the DLL parsed as bytes, its PDB (shipped with it!) mined for names. Scratchpad
scripts static_pe.py / pdb_modules.py.

How it works: an ordinary AC Python app (`apps/python/alien`, window "Alien" with
spinners) that imports `acalien.pyd` - a native x64 DLL for AC's Python 3.3, built Aug
2022 (project "AC-Alien", CMake). Running inside acs.exe it pattern-scans the game's code
(SignatureHook, AddressHook fallback) and detours four physics functions with PolyHook 2
(+asmjit/zydis). No game files change, so server checksums can't see it. Also: a
low-level keyboard hook (onKey) and setAllHooked/unload routines (panic key likely; which
key needs disassembly), a MessageBox at load, a debug console.

The physics it changes (UI range -> exported call -> hooked AC function):
- engine torque x0-7.5 (0.1 steps) -> set_tq -> Engine::step (hkproc_engine_step)
- gear ratio x0-2.5 -> set_gearratio -> Drivetrain::getCurrentGear (whole ratio, "final")
- tyre grip x0-3.5 -> set_grip -> Tyre::getCorrectedD (peak friction: cornering, braking,
  traction)
- added downforce 0-30,000 (units not confirmed - probably N; the Dacia weighs 9.9 kN) ->
  set_downforce -> Car::step via RigidBodyODE::addLocalForce - a CONSTANT push, so extra
  grip even at low speed
- "disable collisions with world objects" -> set_noclip -> Car::step via
  RigidBodyODE::setMeshCollideMask (drive through walls/barriers)

What the watchdog sees (built 2026-09-29, commit 8cd17de): torque x1.1 mostly flagged,
x1.2+ always (power check; the "own gear" reading should make x1.1 plain once calibrated);
gear ratio x1.1+ by the gearing check (rpm vs speed off every legal ratio - needs its
first real rpm captures to validate); grip x1.1+ and moderate downforce by cornering vs
field (>6%, 5+ same-model cars) and vs history (tally, >6% over other drivers at that
track+car); blatant grip/downforce also by the grip line (1.30). Not yet: noclip (needs
the track's wall geometry) and a height-squat check for the constant downforce push
(spline position now recorded, which makes "same place on track" exact).
**Web research 2026-09-29** (Nik: "shouldn't work on servers running csp 2.4 or above" -
check). Read-only; UnknownCheats read in the in-app browser (the search/fetch tools are
blocked there; no login, no downloads, cookie banner left alone):
- Nik's zip IS the original: UC thread 511184 lists acalien.zip with the same SHA256.
- Timeline: Alien v1 (Aug 2022) stopped working ONLINE with CSP 0.1.80 previews (Oct 2022,
  "disables itself" online, fine offline). V2/V2.1 (Nov 2022) = CSP Lua app + alien2.dll
  that unlocks CSP's Lua physics library online (adds N2O, autopilot, gear ratios); broken
  by CSP 0.1.80's anticheat (Dec 2022 changelog: harder to hack into CSP; obfuscated names,
  ffi.load removed). Predator (GitHub Jay0Hx, 2024 fork of AlienV2) needs CSP <= 0.1.79 +
  Cheat Engine DLL injection; adds braking/downforce multipliers, XYZ teleport, forced DRS.
  Users report it working online in 2024 on servers that don't require newer CSP.
- CSP 0.2.4's changelog has nothing anti-cheat; the real lever is a server's REQUIRED
  MINIMUM CSP (Server Manager v2: Server > Options > Content Manager Integration > "Enable
  Extra Custom Shaders Patch Options", then "Required Minimum CSP Version" in the race
  config; minimum only). AssettoServer's ClientSecurityPlugin (Patreon, AssettoServer only,
  CSP >= 0.2.0) is the only real client check found - not usable on Nik's/RATBOY's
  acServer + Server Manager setups.
- Unverified bypass claims (UC 2024: manifest edit; "servers with latest CSP still have
  cheaters"); commercial "No Hesi Cheats" NHC 2.0 (Apr 2026) claims "Bypass Any Server",
  "Undetected", a car decrypter - no details.
- Cheaters deliberately use SMALL boosts (asked for grip +0.3-0.9%; +2-4% was "too
  obvious", 2-4 km/h faster in corners) - below the watchdog's 6% cornering margin.

**Source-level investigation 2026-09-29 (afternoon)** - Nik: "investigate the other
software, download and inspect if necessary". Cheat DLLs NOT downloaded (safety rule:
untrusted executables, even with his OK); read the published Lua source on GitHub
(Jay0Hx/alien_v2 + Jay0Hx/predator) in the in-app browser instead:
- Predator's codeloom.dll == Alien V2's alien2.dll (same git blob sha ccbb817c...,
  1,160,192 B). Predator's Lua never loads it (no ffi) - injected with Cheat Engine,
  so it presumably just unlocks CSP's physics API. Alien V2 (manifest: itisluiz v2.1)
  ffi.loads it and calls its exports: lj_setGripMultiplier (0-5x), lj_set/get/
  resetGearRatio (per gear -5..8), lj_setNoclip, lj_disablePitLimiter,
  lj_overrideLapTime ("laps will never be invalid").
- Everything else in both is CSP's own Lua physics API every frame: addForce forward
  at throttle ("Power"), against travel ("Braking"), downward ("Downforce kg" - units
  fake: force x dt x 100), setTyresTemperature(optimum), setCarBodyDamage/EngineLife,
  setCarFuel (freeze), setCarAutopilot + setAILevel/Aggression (+ Predator's
  setExtraAIGrip, setAITopSpeed), Predator also setCarVelocity (XYZ +-10 m/s, squat/
  hop/jump buttons), setCarPosition (teleport to a driver, online), setDriverName
  (steal name, online), allowCarDRS, engageGear. Alien V2 NOS = forward push after
  0.7 s of HEADLIGHT FLASHING. AI-trolling buttons are offline-only.
- Alien V2 presets: Legit = grip x1.10, downforce 26, brake 2.5, NOS 0.9, optimal
  tyre temps; Fast = grip 1.30, power 1.5, brake 60, NOS 10; Extreme = 9x etc.
- Nik's CSP = 0.2.12-preview1 (dwrite.dll). Its SDK (extension\internal\lua-sdk\
  ac_apps\lib.lua): physics.allowed() gates it; addForce/setCarVelocity/
  setCarPosition/setCarFuel/autopilot all "invalidate current lap"; setDriverName
  "announces new name online to other clients".
- TRACK OPT-IN: surfaces.ini [_SCRIPTING_PHYSICS] ALLOW_APPS=1 (+ extended physics)
  = "Allow Lua apps to access physics API" (cup.acstuff.club). On Nik's PC:
  akv8_goldcoast, balaton_park_circuit/gp, melbourne22/melbourne_f1_2022 have it
  (Hamburg_by_4r's ALLOW_TOOLS sits in [SURFACE_7] - ignored). Genuine file, so
  checksums pass; whether CSP still blocks apps ONLINE is untested. League tracks
  recorded so far (Taupo, Mondello, Phillip Island, Bremgarten, Silverstone) don't.
- No Hesi Cheats (nohesicheats.space, live 25 Apr 2026, ~$28-31/month): no technical
  detail; blurbs copy-pasted from shooter cheats (aimbot, ESP health bars, ring-0
  bypass, HWID spoofer) - low credibility, possibly scam/malware loader. Car
  Decrypter (20 Mar 2026) claims edited data.acd cars pass server validation - the
  power/grip/gearing checks measure against the server's genuine files anyway.
- Others: FearLess CE table t=24177 (lap timer/AI freeze, offline, no physics);
  itch.io "cheat menu" devlog = template lure (claims nitro); OverTake thread 252600
  (Dec 2022): Alien V2 lap override seen online (0.01 s laps). elitepvpers =
  Cloudflare human check, sethioz = 403 - not bypassed.
- Watchdog gaps found -> BUILT same day (e7d7b58, Nik: "Build all you need to
  build"): braking vs field/history (+25%), power bursts (>1.5x at 5+ places),
  teleport onto a car (lands still within 10 m of a car >25 m/s), teleports no
  longer excused by collisions. Floors: bursts < ~+1 m/s^2, braking push
  < ~0.3 g, teleports onto cars < 90 km/h. NOT built: noclip (needs wall
  geometry), height-squat (Legit downforce ~8 kg if addForce is one physics
  step per call, which CSP's "scale your force by dt" note suggests - its
  real effect is grip x1.1, caught by cornering vs field/history), velocity
  kicks (set speed <= ~60 km/h - no advantage). Fuel freeze invisible
  (envelope = empty tank); DRS n/a.
