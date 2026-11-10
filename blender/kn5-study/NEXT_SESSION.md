# Next session: Blender Work / AE86 replica (handover, 2026-11-09 night)

**Start here.**
1. Read `ACHIEVEMENTS_REPORT.md` (what's done and why).
2. Read `PANEL_FIT_TECHNIQUE.md` (the method that works).
3. Then follow the plan below.

Older background: `HANDOVER.md` (kn5 study tools and environment) and `REPLICA_PLAN.md` (the full
results log).

## Where we are
- The **panel-fit method** (fitted B-spline surfaces, trimmed to their outline, with character lines cut
  exactly) is proven on the AE86 **door** (8 faces) and **all glass** (4 pieces). Nik is happy with the
  door.
- It's a **method test**: the curves come from the real Kunos AE86. Later they will come from photos.
- The earlier whole-car strip build (`cad_panels.py`, v5) is superseded; use it only as a reference.

## How to run (Nik's PC, everything on D:)
```bash
cd /d/Claude/Claude-/blender/kn5-study
C=D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86
OUT=D:/Claude/_scratch_research/kn5_study/blind/door
python panel_fit.py $C $OUT GEO_extdoorL_SUB1:b0,2 GEO_extdoorL_SUB1:r1,5 GEO_extglassL   # fit (about 15 s)
PF_IN='D:\Claude\_scratch_research\kn5_study\blind\door' ./fcrun.sh panel_fit_freecad.py   # CAD faces, STEP, mesh
# then exact normals: PF.exact_normals(p, mesh points) -> panels_fit_normals.npz -> Blender (custom normals)
python score_faces.py $C $OUT GEO_extdoorL_SUB1 GEO_extglassL   # per-face distance + coverage (about 2 min)
```

**Spec syntax** (after the mesh name):
- `:rN`: the Nth crease region, as one surface.
- `:bN`: crease region N split into character-line bands.
- `:0,1`: connected pieces (glass).
- `:fall`: curvature pieces (experimental; don't use).

**Blender:**
- Collection `AE86_door_fit`: our faces `fit_*` and the originals `truth_*`, shown with the `zebra`
  material.
- Blender's Python has **no PIL**, so run the analysis outside Blender and load npz files inside.
- Hide whichever set you aren't looking at; objects in front of the camera spoil comparisons.

**FreeCAD:** run only through `fcrun.sh` (D: paths, CurvesWB in `D:\ClaudeData\FreeCAD\Mod`). Never
use C:.

## Plan (in order)

### A. Finish the door properly
1. **Fixed (2026-11-09): the crease strip looked recessed.** The cause was not normals: the 5 mm ledge
   face on top of the strip (region `r5`, facing upward) was missing, so the background showed through as
   grooves. Adding `r5` fixed it.
   - Lesson: **include every small outward-facing crease region** (ledges and chamfers, from about
     0.001 m²). Make this automatic: fit all regions of a panel whose normals face out.
   - **Fixed (2026-11-10): the strip was rounded** because region `r2` was really two faces (the flat
     strip plus a 5 mm chamfer past a ~31 deg turn) and the strip has no vertices across its 30 mm middle.
     Narrow regions now get short section arms, so the chamfer line is found, and sharp lines snap to their
     corner vertex. Spec `GEO_extdoorL_SUB1:b2`. Strip 0.06 mm to the original, flat across (< 0.02 mm bow).
2. **Window frame ring (`r0:b0`) and beltline roll (`r0:b1`)** (2026-11-10, door build `blind/door_v4`):
   - The frame ring held the beltline's steep 3 mm lip (the roll was invisible within 12 mm of the panel
     edge). Arms now shrink at section ends and a roll reaching the edge owns it. Ring vertex fit 1.45 ->
     0.79 mm (faces: 1.61 -> 1.33 mm p95 to the original).
   - Roll faces 3.06 -> 2.43 mm p95. Still the weakest face: Kunos has only ~9 vertex rows along 1.3 m
     there, and the window corners fold over the door plane. Corner patches (`PF_CORNERS=1`) were tried and
     are unstable (13-18 vertices); off by default.
   - Next: build the roll as a true blend (tangent to the skin below and the frame), or a swept profile
     along its line, instead of fitting sparse vertices. Also a white streak low on the front of the door
     in the zebra view (`images/door_v4_vs_original_zebra.png`): check which face.
   - Whole door: original area within 1 mm of our faces 68.9 -> 71.9 %, within 3 mm 88.9 -> 89.4 %
     (`score_faces.py`; its per-face figure is ours -> original only).
3. **Done 2026-11-10: the roll as a true blend.** Roll = skin surface minus a drop profile D(s, rho), tangent to
   the skin by construction (join 0.00 mm), rows aligned between window edge and boundary, its own along/across
   directions as a general B-spline. Roll median 1.23 -> 0.37 mm. Still open: the rear window corner (up to
   13 mm over a small area: Kunos folds the roll into the B-pillar there).
4. **Done: joins.** `seams.py` measures gaps. Outline sides are fitted to their 5 mm-resampled polyline (the
   ledge face was 390 mm short; closed outlines overshot). All skin joins <= 0.24 mm p95 except the window
   corners. `seams.py` still counts separate parts sitting within 5 mm as joins: limit it to one mesh.
5. **Done: shut-line returns** (`PF_RETURNS=5 PF_RETURNS_ON=...` in the FreeCAD step): 5 mm ruled strip
   square to the skin on free outer edges, none on glass or the window opening. Front/rear ends match the
   original within 1 mm; bottom 1.1 mm (Kunos turns it under at an angle). With every original face fitted,
   the real returns are built directly, so the generator matters for the photo phase.
6. **Done: door parts and every small face** (`:rall`, `:rall!0,1,2,5`): window trims, mirror, glass, lock
   barrel, frame channel and flanges. Faces that wrap > 70 deg are split automatically (`wrap_split`).
   Fallbacks: prism trim when the parameter trim fails, standard mesher when Mefisto fails.
   **Complete door** (`blind/door_full`): 80 faces, 84.9 % of the original within 1 mm, 99.4 % within 3 mm.
   Picture: `images/door_complete_vs_original_grey.png` (local).
   Full build:
   ```bash
   python panel_fit.py $C $OUT GEO_extdoorL_SUB1:b0,2 GEO_extdoorL_SUB1:r1,5 'GEO_extdoorL_SUB1:rall!0,1,2,5' GEO_extdoorL_SUB0:rall mirrorL:rall GEO_extglassL
   PF_RETURNS=5 PF_RETURNS_ON='SUB1:r0:,SUB1:r1,SUB1:r2:,SUB1:r5' PF_IN=... ./fcrun.sh panel_fit_freecad.py   # ~100 s
   ```
7. Still open on the door: wrap-split pieces meet with small steps (G0 only, up to ~3 mm on the mirror boss);
   the rear window corner of the roll.

### B0. Front wing - in progress (2026-11-10, build `blind/wing`)
Run: `PF_CLIP=0,1,0,2,0.62,2 python panel_fit.py $C $OUT GEO_body:arch0` then the FreeCAD step (no returns).
Research: `blender/research/reports/Wheel arch lip surfacing.md`, `blender/research/github_finds.md`.
- Done: wing picked out of the shell (clip box reaching past the door edge, so the real shut-line edge is kept;
  outline slits/teeth removed); wing top over its own plane, trimmed by its own outline (0.5 mm median);
  arch found automatically (R 354 mm, edge within 6 mm of a circle), lip 70 mm wide, lip in arch coordinates
  matched to the side faces (join 0.3 mm median). Wing: 49 % of the original within 1 mm, 79 % within 3 mm.
- By eye: the lip edge still shows as a soft ridge, and the side face above the arch is lumpier than the
  original (`images/wing_arch_v1_vs_original_grey.png`).
- 2026-11-10 later: the lip now follows the WHOLE opening edge as a rail (arc length along the edge x distance in,
  1112 mm corner to corner): on the AE86 the flare runs down the straight rear edge to the bottom of the wing,
  30 mm proud of the body behind it (that was the "11 mm lower band"). Fixed: borrowed vertex rows ignored the
  lip mask. Score dipped to 40 % within 1 mm / 76 % within 3 mm because the side band now holds what is left:
  short character lines that STOP at the arch (the door's crease strip continues 220 mm, door to arch; a piece
  in front of the arch). The band method needs lines that run edge to edge; these end at an opening.
- Plan for the side: split the wing into sub-panels at the arch, as Class-A modellers do (patch boundaries on
  lines through the arch ends, lined up with the shut lines): behind-the-arch, in-front-of-the-arch and
  above-the-arch. Each then has lines running edge to edge and the band method works unchanged. Also try
  FreeCAD ReverseEngineering.approxSurface (tested on the door skin: 0.12 mm p95, not a height field) for
  any piece that wraps.
- 2026-11-10 afternoon: sub-panels done (above / behind / in front of the arch centre), a ledge seen edge-on
  becomes a STEP cut line (the rocker strip behind the arch: 14.6 -> 1.4 mm and 0.03 mm), FreeCAD approxSurface
  fallback (`re_fit_freecad.py`, used when a face fits worse than 3 mm and RE does better). Wing now 53.9 % within
  1 mm, 83.7 % within 3 mm (`images/wing_v2_vs_original_grey.png`). Splitting the lip into arch + run-outs was
  tried and reverted (worse).
- Left on the wing: (1) the lip (0.55 mm median but 4-10 mm p95 at its ends, where the flare meets the front
  crease strip and the rear wall); (2) a slot above the front of the arch = the crease-strip faces (r2/r4) not
  built yet - add them with `:rall` like the door; (3) the roll behind the arch (rear:b1, 5 mm p95, its blend
  conversion loses 4 mm - widen the conversion grid); (4) the front tip of the wing.
- 2026-11-10 evening (after Nik's "act like a pro" push): `regress.sh` rebuilds + scores door and wing after every
  change. Fixes: crease-strip faces built (`rall!0`), hole-filler safety net (`fill_holes.py` + `merge.py`), lip ends
  where the flare ends and stops at the rear wall (varying width), surfaces cover their whole band, rolls kept only
  if better than a plain fit, cross-check blocks sized from vertex spacing, and the Class-A rule: fairest surface
  within tolerance. **Door 87.6 % within 1 mm / 99.6 % within 3 mm; wing 72.4 % / 99.5 %.**
  On the original's VERTICES the wing is ~88 % within 1 mm (median 0.25 mm); the area score is harsh on Kunos's
  long flat facets across curves.
- Next on the wing: like-for-like zebra (both shown as exact smooth surfaces) to judge the remaining swirls on the
  wing top and the lip's front end; the small roll behind the arch (rear:b1, 38 vertices, 5.9 mm - straddles the
  crease-strip chamfers); fragments at the bottom-rear corner. Then plan B: rear quarter, roof, bonnet.
- Live FreeCAD: the FreeCAD AI MCP (http://127.0.0.1:3000/mcp) works from any session by plain HTTP
  (`fc_call.sh (kn5-study) TOOL JSON`); switch_document {"document_name": ...} before set_view/capture.
- Next (older list): (1) the lower band behind the arch (11 mm p95) = the flare run-out corner: per the research, stop the
  lip short and close the corner with a G1 filling patch (`Part.BRepOffsetAPI_MakeFilling`); (2) G1 lip edge:
  constrain the lip's outer pole rows to the side face (research: rows 0/1 from the panel edge/tangent);
  (3) the side crease strip faces (`:rall`) and the sill stub; (4) consider CurvesWB trims on the surface
  (`Sketch_On_Surface` / `face_builder.shapefix_builder`) instead of prisms.

### B1. Rear quarter + C-pillar - first build done (2026-11-10 night, build `blind/quarter_w`, in `regress.sh`)
Run: `PF_CLIP=0.45,1,0,1.235,-2.2,-0.5 python panel_fit.py $C $OUT GEO_body:w0 'GEO_body:rall!0'`, FreeCAD step,
then `fill_holes.py` + FreeCAD + `merge.py` (as the wing).
- On the quarter the arch flare is ALREADY its own crease faces (r5 lip, r4 return), so the arch method finds no
  flare: plain bands + `:rall` do it.
- The side wraps round the rear corner into the strip under the tail lamp (faces rearward): one height field
  can't (10-23 mm). New spec `:wN` = ONE cut at the corner: the main sub-panel is every triangle within 45 deg
  (`PF_WRAP`) of the region's dominant direction, the rest its own sub-panels; each by the band method over its own
  plane, data padded 20 mm past the seam. (k-means on normals sliced the tumblehome side into strips and lost all
  its character lines - don't.) Side keeps its 4 lines; all bands <= 3 mm p95.
- Score: area 69.8 -> 77.9 % within 1 mm, 89.4 -> 98.7 % within 3 mm; VERTICES 87.9 % / 98.1 % (median 0.24 mm).
  `miss_map.py` (new) draws the original coloured by distance in side/top/rear views and prints area + vertex scores.
- The C-pillar strip (r1) has NO Kunos vertices along its middle 600 mm (two long flat triangles): our smooth face
  passes the vertices (median 0.4 mm) but not those chords. Splitting it or approxSurface gained nothing; kept whole.
- By eye (`images/quarter_v1_close_grey.png`): shape right; faults: (1) the 45 deg corner cut shows as a FOLD - the
  side and rear sub-panels need a G1 corner (shared tangent / blend patch, or a soft cut line fitted through the
  corner with both faces built against it like the roll blend); (2) kink where the C-pillar meets the roof rail
  (clip edge at y 1.235 - check against the roof once built); (3) the lip above the tail-lamp opening is a thin
  sliver vs the original's ledge; (4) small marks low on the rear corner and at the sill below the B-pillar.
- **Same night, fixed** (build `blind/quarter_p`, `images/quarter_v2_grid_grey.png`):
  - (1) was NOT our cut: the "fold" was a hole-filler patch (10 mm off) over the C-pillar corner. Cause: the r1 face is
    right (vertices median 0.54 mm) but Kunos's 100-150 mm flat triangles sag 3-7 mm off it, and `fill_holes.py` took
    the sag for holes and laid a second bad face over a good one. Fix: a far triangle is a hole only if the normal line
    through its centre meets NO built face within 20 mm (`FH_CHORD=0` = old behaviour). Area score drops (the fillers
    were only chasing chords); vertex score unchanged. r1 stays ONE face (the 45 deg split runs along the whole pillar).
  - Crack at the lower rear corner: wrap sub-panels now (a) are fitted AFTER the main side with samples of its finished
    surfaces as data on the main side of the seam (position + slope match, as the arch lip; `PF_WMATCH`), and (b) share
    ONE smooth seam curve, fitted in a frame halfway between the two faces through the middle of the zig-zag zone; each
    outline reaches one triangle past it, then the far side is cut away (`cut_polys` in the FreeCAD step; `PF_SEAM`).
  - Thin dark lines along the side's character lines = bands 1-3 mm apart ON their line (sparse data, each band
    extrapolates alone). **Line pinning** (fit_bands, all panels, `PF_LINEMATCH`): average both bands' heights along each
    shared line (only where the line runs and both have data within 40 mm), refit both with it as heavily weighted data
    (more controls if pinning costs > 25 % / 0.3 mm). Quarter band joins 0.3-2.3 mm median -> 0.1-0.4 mm.
  - Chord rule tightened: a far triangle counts as sag only if a face lies over it AND its three corners sit within
    1.5 mm of our faces (corners off = real miss, still filled; the wing needed those: vertices 91.8 -> 92.5 %).
  - Quarter now: area 78.2 % within 1 mm / 96.8 % within 3 mm; vertices 86.5 % / 97.9 % (median 0.24 mm).
    Door 87.6 -> 87.9 % (line pinning); wing area 72.4/99.5 -> 70.6/96.1 (chords no longer patched), vertices 92.5/99.3.
- **Next on the quarter:** the lamp-top step = four flat strips ~8 mm wide x 260 mm (r13 rear-facing, r14 up, r17/r18
  down); fitted as separate trimmed faces they overlap/gap ~1 mm = ragged. Build narrow strips as RULED surfaces between
  shared 3D edge curves (each boundary between two regions fitted once as a fair 3D B-spline, used by both sides) -
  the same builder then serves shut-line returns, lamp surrounds, window flanges. Also a hairline down the edge beside
  the lamp opening (r27 return) and a small notch at the sill.

### B. Rest of the body, panel by panel (yes, the car is built in pieces)
Kunos: the shell is one mesh (`GEO_body`), and doors, bonnet, hatch and bumpers are separate. We
follow the same split, then split each panel into surfaces at creases and character lines.

- **Order:** front wing → rear quarter and C-pillar (first build done, corner fold to fix) → roof → bonnet → hatch → front and rear bumpers
  → sills.
- **Known limit:** a panel that wraps more than about 70° (wing top into side, bumper corners) is not
  one height field over a plane.
  - Option 1: split at the wrap with a character line (preferred; it's what modellers do).
  - Option 2: add a parametric fit (parameters from a coarse base surface, then iterate).
- **Wheel arches:** the arch lip is a feature line, with the arch cut as an outline or opening.

### C. Assemble and check the whole car
- Mirror the left half to the right.
- Run exact two-way scores against the full skin.
- Zebra and grey views from all sides.
- One final picture per finished section, not progress shots (Nik's preference).

### D. Make it an AC-ready model
- **Display/export mesh:** sample each face as a **quad grid** in its parameter space following the
  Kunos recipe (about a 20 mm grid, 20–35k triangles on the paint, loops along the lines). Use exact
  normals.
- **Skin and setup:** unfolded skin UV, baked AO, LODs, standard dummy names, two-layer glass.

### E. Afterwards
- Lamps, grille and badges as parts.
- **Interior** survey and recipe (budget, modelled vs texture-only, AO).
- **From photos:**
  - trace outlines and character lines on photos and blueprints (Nova first; it already has solved
    cameras and traced windows);
  - run the same fit, trim and cut pipeline with a few sections;
  - check against the photos by eye.
- Parked: the steward app (`steward-app/PLAN.md`) and Nova grading ("not yet").

## Rules Nik has set (keep)
- **Drives:** everything runs on **D:**; nothing uses C:.
- **Communication:** short messages; at the end of each turn, say what was done and show one picture;
  judge matches by eye.
- **No smoothing "fixes".** Build crisp surfaces from curves.
- **Saving:** save to the Claude- repo, then commit and push after each step; the public copy updates
  itself.
- **Assets:** never commit game assets (kn5, textures, images of them are gitignored; the `images/`
  here are our own builds).
- **Blender work:** load the blender-* skills and use the blender-mcp tools (standing approval).
