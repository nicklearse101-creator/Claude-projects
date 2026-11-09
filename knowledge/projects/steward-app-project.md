---
name: steward-app-project
description: Steward app for AC (Ratty's Racing incident review) - plan only, Claude- repo steward-app/PLAN.md (2026-11-09)
metadata:
  type: project
---

Nik wants a steward app for AC. As of 2026-11-09 only the plan exists: `D:\Claude\Claude-\steward-app\PLAN.md`.

The plan:
- Python, built on the watchdog's UDP captures and the Server Manager results.
- A local web page with a track map and incident playback.
- Advisory blame hints; the steward always decides.
- A decision log and a stewards' report.
- Version 2 adds .acreplay files and "watch in game".

Reference: github.com/Stripe76/VirtualStewardMkV (C#, GPL-3.0) and Stripe76/ACLibrary (replay reader, no licence). Learn from them only; don't copy code.

Open questions for Nik: users and PC, penalty types, whether to include track limits (the watchdog is physics-only, see [[watchdog-scope-physics-only]]), replays, where reports go.

Related: [[ac-physics-watchdog-project]], [[ratboy-race-server]].
