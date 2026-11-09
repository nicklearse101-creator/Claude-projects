---
name: feedback-nova-compare-to-pictures
description: "Nova (and any car model work) - the job is to LOOK at Nik's reference pictures and make the model match them; plain grey model vs picture, side by side, same scale, every change (Nik, 2026-10-19, after a wasted day)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 492adf9d-8819-4b64-a28b-e276d960f362
  modified: 2026-10-19T21:27:35.429Z
---

The whole point of the car-model work is: look at the pictures Nik sends, compare the model to them, and change the
model until it looks like them. Nothing else counts as progress.

**How to apply (every change, every area):**
- Use a PLAIN GREY model (one grey for the body, dark glass) - no paint colours, no lookdev lighting, no false colours.
  Nik: "you're getting confused with the paint colours everywhere. when we worked on the escort and talbot you just
  looked at a grey model".
- Reference = Nik's grey studio pictures `reference/photos/grey_studio/{side,front,rear}.png` (Nik 2026-10-19) plus the
  red-car photos. Compare side by side at the SAME SCALE and crop CLOSE on the area (tools/compare_grey.py,
  blender/scripts/grey_views.py, blueprint empties blender/scripts/blueprints_ref.py). Read positions off the picture
  (e.g. measure a line's height in pixels -> mm) and move the model's feature onto it.
- Look with your own eyes and say what differs (line too low, arch too wide, bend that shouldn't be there). If it
  visibly differs, it is wrong - never argue from projection maths or "the numbers match" (see [[feedback-judge-by-eye]]).
- One area at a time, check it close up in Nik's Blender, then show Nik that one picture. Don't run long automatic
  pipelines (smoothing, denoise, normal tricks) and call them fixes - Nik: "stop wasting time with non-fixes".
- Do it like the Escort/Sunbeam work ("Blender" session): targeted edits, checked in Blender against the pictures.

**Why:** 2026-10-19 on [[nova-gte-project]] I spent a whole day on scripted smoothing/normal transfer, coloured renders
and camera projections, claimed things matched, and the model barely changed; obvious faults (windscreen too high,
wing line 3 cm too low, rear bumper bend, arches) were only found once a plain grey model was put next to the pictures.

**Replace, don't repair (Nik 2026-10-19, after the clean-swept bumper):** "make new parts from scratch every time to
replace the part you're working on". For each part (bumpers, arches, panels, scuttle, wipers...) build new clean
geometry fitted to the pictures/measurements and delete the bought model's version - don't try to smooth or nudge
the bought mesh (its triangles are too messy; in-place fixes failed all day). Example: blender/scripts/bumper_sweep.py.

2026-10-26 (Nik, after a white-clay bonnet render next to his red photo: "that looks nothing like it, stop wasting
my time"): only send a comparison when the model genuinely matches, and make it like-for-like (same angle, same
tone/lighting - not light clay vs a dark or red car). A picture sent as "proof" that a feature is in, when it does
not visibly show it, costs his time and trust. If it doesn't match yet, say so in one line and keep working.

2026-10-26 (Nik: "you need to be way more accurate in your analysis of pictures and drawing over the lines"):
never call an overlay "close" or tick it from a downscaled image. Check every line at FULL resolution, zoomed on
it, with thin (1 px) model lines, and state the offset measured in pixels AND mm. Same when tracing lines off
photos/drawings: follow the actual edge, verify the trace drawn back over the image at full size.
