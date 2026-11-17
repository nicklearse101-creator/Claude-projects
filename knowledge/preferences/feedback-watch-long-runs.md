---
name: feedback-watch-long-runs
description: "Every long background run gets a stall/error watchdog (Monitor) so I notice a hang myself, not when Nik asks"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 72978f4c-01cc-4374-ab94-5183fa936984
  modified: 2026-11-17T18:09:46.696Z
---

Every long background job (FreeCAD stages, regress.sh runs, builds) gets a Monitor watchdog at launch: alert when its log has not changed for ~5 min (stall), on error lines (Traceback, "Exception while", mesher failures), and on finish. Also wrap the run in `timeout` (e.g. `timeout 1200 ./regress.sh ...`).

**Why:** 17 Nov 2026 a rear-bumper FreeCAD run hung for 15 min on a mesher failure (MEFISTO) and I only found out when Nik asked "been a long time, what's happening?" - he said I should have a way of checking it myself.

**How to apply:** launch with run_in_background + timeout, then immediately arm Monitor on the log (stall + error + done). Related: [[blender-work-kn5-study]], [[feedback-concise-end-of-turn]].
