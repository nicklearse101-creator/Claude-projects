---
name: feedback-check-blueprint-and-photo
description: Nik 2026-10-26 - always cross-check the blueprints against the photographs before trusting either
metadata:
  node_type: memory
  type: feedback
  originSessionId: 89a00829-bab3-450e-a4db-0a0bb133d892
  modified: 2026-10-27T03:58:47.469Z
---

Nik: *"Always compare blueprints and pictures to double check."*

**Why:** on the Nova this immediately settled a real conflict. The traced blueprint said the door glass's rear
edge is at y 0.447; the triangulated photo points DG_RT / DG_RB said 0.39. Drawing the traced edges onto the
side photograph through its own solved camera showed the blueprint sitting exactly on the real glass and the
two measured points sitting in the middle of the B-pillar, 55 mm behind it. Neither source alone would have
caught it - the measured points look fine in a table, and the blueprint alone could have been the wrong car.

**How to apply:** before building from any traced line, project it onto a photograph through that photograph's
solved camera and look. In the Nova project that is `tools/photomatch/bp_on_photo.py` (lines from
`blender/data/side_profile.json` or `windows.json`, plus measured points, drawn on a photo). Where they agree,
build. Where they disagree, find out which is wrong rather than averaging them. Related:
[[feedback-judge-by-eye]], [[feedback-nova-compare-to-pictures]], [[nova-gte-project]].
