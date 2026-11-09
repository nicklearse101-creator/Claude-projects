# NICK3 v36a - flare to the clip's crest line, crisp and flush

Blend: `D:\Claude\escort_mk2_dtm\blender\escort_v27 WIP v36a flare to clip crest.blend` (v35 `escort_v27.blend` untouched). NOT exported; live install is still v33.

## What the user asked
Flare must reach the clip's rounded top edge (the crest, approved red line), run the full clip width, follow the curve round the corner and down the clip's vertical rear edge to the bottom arch line. Crisp, flush. Measure to 1 mm.

## Rebuild after the Blender crash (all scripts in tools\blender, data in tools\blender\data)
1. Crest (data\crest_L_1mm.json): per 1 mm station on the straight line (0.7047,-1.7927)->(0.9121,-1.5815), the 1 mm cross-section's slope-break (largest slope drop over +-3 mm, z .205-.265), then median(31)+Gaussian(10) on the offset. 305 mm long, 306 pts, z .216-.241. |final - raw break| mean 0.58 mm, p90 1.35, max 5.9 (one ~40 mm stretch where the clip has two close edges and the raw break jumps 12 mm between them; the smoothed line bridges it). Mirror for the right side (clip is mirror-exact at the corner, 0.0 mm).
   Extension (crest_L_1mm_ext.json): +14 mm along the end tangent to the clip's rear top edge (0.9164,-1.5678) so no clip tab is left between the crest end and the corner line.
2. S = distance from crest to where the pristine flare crosses the clip (45-67 mm, last 3 samples clamped to 34).
3. nick3_lip_warp.py: measure_corner() (bisection, verified: .9234/-1.5502 at z=.02 ... .9176/-1.5666 at z=.22) -> FLARE_V36pre_* (154 verts/side, max 39.7 mm in y, 7.7 in z). Lip outer face ends on the clip's vertical rear edge.
4. nick3_clip_skin.py: lofted shoulder strip (front boundary on the crest, rear = S+14 mm under the flare), env=0, lift 1.5 mm ramping to a 0.6 mm floor at free edges, clip normals interpolated (down-facing back-face hits flipped), cells beyond the clip's rear edge and folded quads dropped.
5. nick3_v36_build.py run(): reset to V36pre, strips, grounds (clip+strip), subdiv/ease/smooth/cover (margin 0.3 mm), drop needle faces, blend flare normals toward the ground's within 8 mm, join strips into NICK3_side_L/R.

## Verified (1 mm)
- Strip front boundary vs crest polyline: plan mean 0.53 mm, max 2.1 mm (L), 2.0 (R); mean 0.53 mm of that is the 0.6 mm normal lift on a steep face. Vertical height over clip at the boundary: mean 1.3 mm (L 1.28, R 1.23), p90 1.3, max 5.6 (extension end at the corner).
- Lip at the vertical edge: flare outer x - clip wall x = 0.0 mm at the edge (z .12, .18, left, before the strip work); rolls inboard behind the edge.
- Flare/strip junction step: 0.04-0.7 mm along most of the length, up to 1.8 mm at the wing-end side and 2.7 mm at the very corner end.
- Tyre clearance (min radial vertex gap, both sides): 23.4 mm, unchanged vs v35, no vertices inside the tyre (R 271.6 mm).
- Flare alone was a closed shell; now flare + open strip: 370 boundary edges (364 strip, 6 from deleted needle faces under the strip).

## Known defects / limits
- Wing-end start of the strip (first ~40 mm) is a thin tail; the flare is 78 mm behind the crest there.
- A hairline shading streak where the old flare edge meets the strip (sub-mm step) and one ~2 mm dark hairline near the corner.
- LOD B/C/D flares are NOT updated (they never had the blend).
- Strip sits 0.6 mm (normal) proud of the clip at its free edge, rising to ~2-3 mm over the clip across the shoulder.
- Colour split (body_a_SUB1 material) deliberately left alone; rear bumper untouched; splitter rectangle stays removed.
- Tooling note: device_commit_files delivers the previous version of a just-edited file; commit twice and check the md5/length on D:.

---
# v36c - arch flows to the crest (replaces the flat shelf)

Blend: `D:\Claude\escort_mk2_dtm\blender\escort_v27 WIP v36c arch flows to crest.blend` (v36b untouched). NOT exported.
Script: `tools\blender\nick3_v36_flow.py` (`run_flow(C, S_mm, smooth_iters=6)`, `check(side)`), with `nick3_clip_skin.py` (soft_normals accepts clip=None).

## Why
User (08:37): "that's just a flat smudge. The top line of the arch should flow to where the blue ends, making the arch and clip look like one flowing piece".
Measured cause: along the crest normal the pristine flare top sits 105-115 mm below the clip, then ramps (slope 1.0-1.9) through the clip surface at r = S; the clip shoulder is slope ~0.5. v36b filled the gap with a clip-copied strip (+1.5 mm shelf) and eased the ramp onto it, leaving a shelf then a slope jump (0.5 -> 1.0) at the old edge.

## Method
- Per crest station k (extended crest, 2 mm), r = distance behind the crest, Rb = S + 30 mm.
- Height above the clip d(r): cubic Hermite, d(14 mm)=0 with d'=0 (tangent to the clip, after the crest's rounded roll-off), d(Rb)=pristine flare height over the clip, d'(Rb)=pristine flare slope minus clip slope (so it joins the arch with no kink).
- Strip (crest -> S+14 mm) uses clip + d(r); last 12 mm dive 2.5 mm so its free rear edge is buried.
- Flare top-surface vertices with r < Rb are displaced to the same surface (weighted by depth below the top, so shell thickness is kept); the flare sits 1.5 mm UNDER the strip in front of S+2 mm and crosses to +1.2 mm over it by S+12 mm (this removed the hairline crease at the old flare edge, which was a 1-2.5 mm ridge of the old front wall).
- Surface never goes below the local clip max (+0.5 mm); cover() against the clip; smooth_flare 6 passes.

## Verified (live Blender, both sides)
- Strip footprint 2 mm grid (4877 pts/side): flare top below clip+0.2 mm at 17 pts (L) / 17 (R), all at station 0 (the wing-end tail) - no other holes.
- Second-difference scan (1 mm) across 30 stations: 13 kinks >1.2 mm on L, mostly 1.3-2 mm at r 130-146 mm (behind the blend, in the pristine flare), one 6-7 mm spike at station 10 (wing-end tail).
- Clip vertices: 0.0 mm difference from CLIP_ORIG_v34. Tyre clearance 23.4 mm (unchanged), 0 vertices inside the tyre. Flare shells: 364 boundary edges each (the strip's outer boundary), 0 non-manifold, 0 degenerate faces.

## Known defects (honest)
- Wing-end start of the strip: thin pointed tail with a hairline and a bump (stations 0-20).
- Faint shading streaks along the crest (interpolated clip normals are noisy) and a bump/pinch at the clip-corner end.
- The sweep is shallow: surface starts rising ~50 mm behind the crest; if the user wants the top line to rise sooner, increase DRB / lower R0 or d'(R0) > 0.
- LOD B/C/D not updated. Not exported (live install still v33).

---
# v36d - wing end smoothed, lump removed (user, 18:15: "it goes to the right place, but it looks rough, needs smoothing out and this lump removing from the bottom edge of the wing")

Blend: `D:\Claude\escort_mk2_dtm\blender\escort_v27 WIP v36d wing end smoothed.blend` (v36c, v36b, v35 untouched). NOT exported. Script: `nick3_v36_flow.py` `build_all(C, S_mm)`.

## Changes
- Lump = the thin pointed sliver where the crest meets the clip's rear edge at the wing end (strip first columns, 2-3 mm high, a few mm wide). Strip start now trims to >= 60 % of full width, fades the first 12 mm flush onto the clip and rounds the corner (quarter-ellipse, 14 mm).
- Smoothing: z-Laplacian (10 passes, 30 extra in the wing-end box) on the arch->crest surface for r > 14 mm behind the crest (crest boundary and first 14 mm stay on the clip), re-cover the clip, normals re-derived from the smoothed geometry there (clip-normal noise gave the streaks). An earlier all-the-way-to-the-crest version gave a bright bead along the crest, so the weight is 0 inside 14 mm.
- Small fin at the flare's wing end (up to 24 mm over the clip) flattened with a 3-D Laplacian (14 passes, box x .686-.742, y -1.750..-1.668).
- Pinched cells (< 0.8 mm edges where the crest curves) welded; this softened a hairline crease on the right side.
- Final cover pass at 1.2 mm.

## Verified (both sides)
Clip 0.0 mm vs CLIP_ORIG_v34; tyre gap 23.4 mm, 0 inside; 0 non-manifold, 0 degenerate, 0 NaN; flare+strip boundary is one loop (335-337 edges); strip footprint (1926 pts/side, k>=10): flare top below clip at 4 points on L (worst -0.14 mm), 0 on R (min +0.58 mm).

## Known defects (honest)
- Faint soft crease still visible on the right just behind the wing-end nose (~20 mm), and a hairline near the start edge.
- The remaining sharp edges at the flare's own wing-end cap are original design; the small fin on the clip beside the headlight opening is part of the untouched clip.
- Sweep still gentle (rises ~50 mm behind the crest). LODs B/C/D not updated. Not exported.

---
# v36e / v36f - lip to clip, arch to the user's red lines (user 19:03: "bring the arch to there, simple. in a nice smooth line, not jagged")

Blend (new, nothing earlier overwritten): `D:\Claude\escort_mk2_dtm\blender\escort_v27 WIP v36f arch to red lines.blend`. NOT exported (live install still `export_staging_nick3_v33_smooth_body_material`). Earlier v36e blends kept. Scripts: `tools\blender\nick3_v36e_lip.py` (lip geometry); the v36f steps below were run as inline Blender code (not yet saved as a script).

## Method (native-tool style, all on NICK3_side_L/R, clip untouched)
- Red lines read off the user's screenshot by template-matching it into a Blender capture and un-projecting through a virtual camera (validated 0.2 px on 6 landmarks): U = upper/outer arch edge, I = lip edge along the wheel opening, B = strip's lower boundary on the clip.
- I line: polar radial warp about the axle so the lip edge follows the smoothed user curve; U line: sharp-edge rim verts snapped to a degree-5 fit of U (max dev 2.7 px), neighbours blended by IDW.
- Strip footprint (open boundary loop on the clip): 1D Laplacian along the loop in windows (tip and rear end), displacement propagated into the dense strip by edge-length falloff (16 mm), then re-hugged to the clip at +1 mm using a *normal-filtered* nearest-point query on the clip (only clip faces facing the same way as the strip).
- Front tip hook: the strip tip wrapped around a thin returned flange of the clip (clip has an inner sheet ~4-5 mm behind the outer sheet there). Faces hugging the wrong-facing sheet were deleted (R 163, L 185), the tiny hidden holes filled/triangulated, tiny detached fragments (<100 faces) removed. The strip and main flare skin are separate face components (R 1693 / 6536 faces, L 1623 / 6549 before cleanup) - do not delete "small" components by size ranking.
- Rippled slope above the strip: 30 passes of weighted Laplacian on strip verts >1.8 mm above the clip (R 170 verts, L 169, max move 3.6 mm), boundary and clip-hugging verts untouched.
- Normals refreshed per side with set_normals_from_faces(keep_sharp=True) after every geometry change.

## Verified (both sides)
Clip 0.0 mm vs BK_v36d_clip; tyre clearance 23.4 mm both sides; 0 non-manifold edges; 0 faces < 0.05 mm2; strip boundary one loop (R 342 edges, L 322); L vs mirrored R front verts: median 0.06 mm, p95 2.0 mm, max 12 mm (tip windows were smoothed independently).

## Known defects (honest)
- Slope between strip and arch still shows soft wrinkles in shading (not flat); lip edge has a small pinch where it meets the clip (R, near x -0.73 y -1.74 z 0.25 region and the rear end).
- A small fold remains at the old rear-end spike on both sides (few mm).
- LOD B/C/D (NICK3_LOD_side_*) not updated; pale fin facets at clip lower rear corner are pre-existing; helper data still in the blend (LK_V, vertex groups, BK_* backup meshes, DEV attribute) - clean before export.
- Not exported. Export only when the user says "export".
