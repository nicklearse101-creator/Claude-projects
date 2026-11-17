---
name: skin-gen-reminder-nov16
description: "REMIND NIK - skin generator next list (16 Nov evening), to start only AFTER he has tested 1.11.0: edit existing skins, encrypted cars via 2D template, interior colours, other sims"
metadata:
  node_type: memory
  type: project
  originSessionId: 3ff76d07-0207-43b0-a903-b8e467f5b675
  modified: 2026-11-16T19:24:48.960Z
---

Nik, 16 Nov 2026 evening: "Things to do once I've tested the most recent" (1.11.0).

1. DONE 17 Nov (1.12.0 'Start from'). Skin drop-down to edit a skin made earlier AND stock skins; picking one auto-loads a preview ("to make it easier for stupid people").
2. IN PROGRESS 17 Nov: research done (ac-skin-generator/research/Encrypted cars 2D livery painting.md); phase-0 hand test skin 'R4S 2D test' written into cf_ferrari_296_gt3 (research/proto_2d_f296.py) - Nik tested 17 Nov 17:12: "looks good" - camo + template shading + carbon right, side 101 boards read correctly; first letter of RATTY'S cut by a panel edge; roof logo came out turned 180 (bottom towards the front). Next: real 2D mode (plan proposed 17 Nov, waiting for his go). Encrypted (CSP-protected) cars: he paints them by hand from the body texture / Content Manager's AO (2D layout -> GIMP -> .dds + .png, usually under 10 MB). Bring that into the app as a 2D template mode, lighter files. **"DON'T BREAK ANYTHING WE HAVE SO FAR!!"** - prove with tests/same_output_cars.py.
3. Interior colours (same AO/GIMP idea); needs a dictionary of interior texture/mesh names like the body one; use CSP info (GitHub, online, local extension/config).
4. How to make it work for the other big sims - the 2D template engine of item 2 is the route in.

Also written in ac-skin-generator/TODO.md ("Next - Nik 16 Nov evening").

**Why:** he wants to test 1.11.0 first (paint finish is untested in game).
**How to apply:** wait for his 1.11.0 feedback, fix that first, then start these in order. Use the research tool first (see [[feedback-use-research-tool]]). See [[ac-skin-generator-project]].
