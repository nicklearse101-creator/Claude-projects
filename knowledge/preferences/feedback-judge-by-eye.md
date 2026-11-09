---
name: feedback-judge-by-eye
description: "Judge model-vs-photo matches by looking at side-by-side images, not by projected numbers; the matched cameras can be wrong locally (Nik, 2026-10-19)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 492adf9d-8819-4b64-a28b-e276d960f362
  modified: 2026-10-19T21:03:59.327Z
---

When checking the model against reference photos, decide by looking at a side-by-side (same view) - if it visibly
differs, it is wrong, whatever the projection maths says.

**Why:** 2026-10-19 on the Nova ([[nova-gte-project]]) I projected the windscreen outline into photo 20 through the
matched camera c20, it "matched", and I argued the glass was in the right place while the side-by-side plainly showed
our glass base far too high. Nik: "why the hell would you think those 2 pictures look the same?" The matched cameras
are only roughly solved (c20 put the headlamps 60 px off while the bonnet matched).

**How to apply:** make a side-by-side render vs the photo, look at it critically, and send that; use projections only
as a rough guide. Also check every change close-up in Nik's Blender before moving on ([[feedback-blender-use-plugins-skills]]).
