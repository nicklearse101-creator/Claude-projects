# Next week - what the two briefs add to the replica plan

Written 2026-10-29 after reading (a) `Nova_GTE_Image_Tools_and_Body_Reconstruction_Brief_for_Claude.docx` and (b) the
ChatGPT share "Building Nova Cockpit" (generic advice on tools for the interior). Checked against
`docs/REPLICA_PLAN.md` and DECISIONS 2026-10-27 (16)-(21). Nothing external was re-verified; tool claims in the
briefs are theirs.

## Where we are (so the list below makes sense)
Plan approved: body moves to a FreeCAD character-line network -> NURBS surfaces -> panels. 96 curves fitted; the
10 lines still too wobbly are listed in DECISIONS (21). Not yet measured: spoiler, C-pillar, screen header, and
**cross-sections** (roof crown, tumblehome) - decision (19) says the network has the flank and ends but no sections.

## Worth doing, in this order

1. **Zebra / strip-light check - the one real gap.** Both the plan (4.2) and the docx name it; nothing exists yet
   (only mentioned in docs). Build `tools/cad/zebra.py`: long strip lights (or a striped emission world) in Blender
   on a clay material, fixed cameras, run on every panel and on the numpy shell for a baseline. FreeCAD's
   ZebraTool (Curves WB, installed) does the same on the NURBS face before it is ever meshed. Do it BEFORE
   surfacing - it is what tells us whether a line network is fair enough, and it judges what Nik actually
   complains about (surface flow), which silhouette overlays cannot.
2. **Cross-sections from GA front/rear + photos.** The docx's central point - silhouette matching is necessary but
   not sufficient - is exactly our history (side profile right, car "not a Nova"). Sections at roof crown,
   belt, shoulder, bonnet and tailgate are the missing curves; add them to the network (lines_v2 -> v3) before
   fixing the wobbly lines, because they constrain the same surfaces.
3. **One fixed-view comparison sheet as a standing regression test.** Seven fixed views (front, rear, L, R, top,
   two three-quarters), clay, same lens, with the strip-light pass; run after every change to catch regressions
   elsewhere. We have the pieces (`render_rect.py`, `ortho_views.py`, `match_look.py`) - join them into one
   command and a contact sheet.
4. **Per-image reference log.** `SOURCES_NIK.md` / `REFERENCE_LINKS.md` record sources but not, per photo: view,
   lens/perspective, which features it can constrain, confidence. A small TSV next to `reference/photos/` - cheap,
   and it stops a perspective photo being used as an elevation again.
5. **Ask Nik for a walkaround.** He owns the car in the R## photos. One slow 360 deg video plus straight side /
   front / rear shots at a fixed distance is the single input that would make photogrammetry viable (COLMAP /
   Meshroom as a CROSS-CHECK of our own bundle adjustment, not a replacement). Caveat: glossy dark paint and glass
   are hard for it; treat as reference, not geometry. No ffmpeg on this PC (video frames would need the WinRT route
   in memory, or `pip install opencv-python` which the project .venv already has).

## From the cockpit chat - for the interior track, not the body
- **Scene inspector + validator.** One script that checks every node name the ini files reference exists
  (`WHEEL_xx`, `SUSP_xx`, `DISK_xx`, `STEER_HR`, `COCKPIT_HR`, `ARROW_*`), pivots on real axes, materials present,
  scale untouched. Also item 7 of my own audit backlog. Cheap; do it before the interior starts.
- **Parametric gauge builder** (diameter, depth, marks, range, needle length, pivot) - reuse for speedo, tacho and
  the four small gauges. Sensible; matches how the bumper was built.
- **Do not take from it:** "use ChatGPT Images to compensate for Claude" (I read images directly; and a generated
  dash is not evidence); Meshy/Tripo for the dash (rejected for the body; only worth testing on small loose parts
  such as vents, switches, gear knob).

## Ignore (and why)
| Item | Why not |
|---|---|
| Image-to-3D for the shell | Tried, deleted 26 Oct: generated surface carried 4-78 mm lumps. |
| NeRF / Gaussian splatting | Not a clean mesh; no capture set. |
| Super-resolution / upscaling | Invents edges - contradicts the mm-level goal. |
| Reverse-image search | Nik already supplied sources; found nothing new on disk (decision (16)). |
| Generated "missing angle" images | Not evidence. |

## Housekeeping
- Blender MCP add-on is protocol 11 vs 15 expected: `uvx mcp-for-blender install-addon`, restart Blender. (`look`
  currently ignores camera arguments.)
- Sandbox shell checks failed intermittently on 28 Oct; if it recurs, retry rather than working around it.
