# Next session: Blender Work / AE86 replica (handover, 2026-11-10 late)

**Start here.**
1. Read this page (where we are, how to run, what's next).
2. `PANEL_FIT_TECHNIQUE.md`: the method that works, with every lesson we paid for (bottom of the file).
3. `ACHIEVEMENTS_REPORT.md`: the story so far (section 7 = the 10 Nov work on the door, wing and rear quarter).

Older background: `HANDOVER.md` (kn5 study tools and environment), `REPLICA_PLAN.md` (the full results log).

## Where we are
The car is being rebuilt panel by panel from fitted CAD surfaces (B-spline faces trimmed to their real outlines,
cut exactly on their character lines). It is a **method test** on the Kunos AE86: the curves come from the real
model now; later they will come from photos.

| Panel | State | Area within 1 / 3 mm | Kunos vertices within 1 / 3 mm |
|---|---|---|---|
| Door (80 faces incl. glass, mirror, trims; 21 strips) | done | 88.4 % / 99.7 % | - |
| Front wing (arch lip, sub-panels) | done, small items left | 70.5 % / 96.1 % | 92.5 % / 99.3 % |
| Rear quarter + C-pillar (14 strips) | lamp-top step done, small items left | 78.3 % / 96.8 % | 86.3 % / 97.9 % |
| Roof, bonnet, hatch, bumpers, sills | not started | | |

The **vertex** score is the honest one: Kunos uses 100-150 mm flat triangles that cut chords across curves, so the
area score marks a correct smooth surface as "off" between vertices.

Pictures (local, not in git): `D:\Claude\_scratch_research\kn5_study\images\` - `door_complete_vs_original_grey.png`,
`wing_v4_zebra.png`, `quarter_v2b_grid_grey.png` (latest quarter: v2 / v2b / Kunos).

## How to run (Nik's PC, everything on D:)
```bash
cd /d/Claude/Claude-/blender/kn5-study
./regress.sh all          # rebuild + score door, wing, quarter (~6 min). Run after EVERY change to the fitters.
```
Reference (2026-11-10 late, with thin strips): **door 88.4 / 99.7, wing 70.5 / 96.1, quarter 78.3 / 96.8** (area within 1 / 3 mm).

One panel by hand (the quarter as an example):
```bash
C=D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86
R=D:/Claude/_scratch_research/kn5_study/blind/quarter_x
export PF_CLIP=0.45,1,0,1.235,-2.2,-0.5                         # the panel's box in AC metres (x, y, z ranges)
python panel_fit.py $C $R GEO_body:w0 'GEO_body:rall!0'         # fit (~30 s)
PF_IN="$(cygpath -w $R)" ./fcrun.sh panel_fit_freecad.py        # CAD faces, STEP, display mesh (~2 min)
python fill_holes.py $C $R GEO_body                              # safety net for real holes
PF_IN="$(cygpath -w $R/fill)" ./fcrun.sh panel_fit_freecad.py && python merge.py $R
python miss_map.py $C $R D:/ClaudeData/tmp/miss.png GEO_body    # misses drawn side/top/rear + area AND vertex scores
python seams.py $R                                               # gaps along joins between our faces
python pack_build.py $R D:/ClaudeData/tmp/build.npz              # one npz for Blender (points, faces, exact normals)
```
Clip boxes: wing `0,1,0,2,0.62,2`; quarter `0.45,1,0,1.235,-2.2,-0.5`.

**Spec syntax** (after the mesh name):
- `:rN` one crease region as one surface; `:rall` / `:rall!0,1` every region (except those listed).
- `:bN` region N split into character-line bands.
- `:archN` region N has a wheel arch whose lip is part of it (front wing).
- `:wN` region N wraps a corner: one cut at 45 deg from its main direction, minor pieces matched to the main one
  and cut on one smooth seam curve (rear quarter).
- `:0,1` connected pieces (glass).

**Switches** (all on by default; `=0` turns off): `PF_LINEMATCH` (bands pinned to their shared lines), `PF_WMATCH`
and `PF_SEAM` (wrap sub-panels), `PF_BLEND` (rolls built from their neighbour), `PF_RE` (FreeCAD approxSurface
fallback), `FH_CHORD` (hole filler ignores Kunos chord sag). `PF_WRAP` = wrap cut angle (45).

**Blender** (blender-mcp; standing approval, load the blender-* skills; never reset the world):
- Collection `AE86_quarter`: `quarter_orig` (Kunos, its own normals), `quarter_fit_*` builds, `orig_regions` and
  `m_faces` (faces in random colours, for finding which face is which), lights `LGT-q_*`, camera `cmp_cam`.
  Other collections are excluded from the view layer; `AE86_door_full` and `AE86_wing` hold the door and wing.
- Load a packed build: npz -> `me.from_pydata` with AC (x, y, z) -> Blender (x, -z, y), smooth shading, custom
  normals from `N`, material `grey_clay`. Render ours and Kunos with the same camera, one hidden at a time, and
  put them side by side with PIL outside Blender (Blender's Python has no PIL).

**FreeCAD:** only through `fcrun.sh` (D: paths, CurvesWB in `D:\ClaudeData\FreeCAD\Mod`). Live FreeCAD MCP:
`fc_call.sh TOOL JSON` (http://127.0.0.1:3000/mcp).

## Next (in order)

### 1. Thin strips - DONE 10 Nov late (`strip_build.py`, see PANEL_FIT_TECHNIQUE.md "Thin strips")
Narrow crease faces are ruled surfaces on shared side curves; a side on a wide face is that face's own built edge.
Lamp-top channel (r17 / r13 / r14 / r18) now matches Kunos in grey (`images/lamptop_strips_vs_kunos_grey.png`).
Left to do:
- **Multi-neighbour sides:** a long side made of runs along several faces (rear quarter r7, the 1.4 m drip rail: r1,
  r4, r21) needs a chain of curves (rail = wire, `makeRuledSurface` on wires). r7 stays an ordinary face meanwhile.
- **Wide faces trimmed on strip-strip curves:** today a strip takes the wide face's edge as it is (0.5-1 mm from the
  Kunos crease); the next step is to fit that edge once from the Kunos crease and trim the wide face on it (2D curve
  in its parameter space, `toShape(surface)`, the same edge object in both faces, as the research recommends).
- `seams.py` reads a narrow strip's far edge as a join (p95 ~4 mm on strips under 5 mm wide): measure joins only on
  boundary vertices whose nearest face is the strip's recorded neighbour.

### 2. Rear quarter leftovers
- A hairline down the vertical edge beside the lamp opening (the r27 return).
- A small notch at the sill below the B-pillar.
- The kink where the C-pillar meets the roof rail (clip edge at y 1.235): judge it once the roof is built.

### 3. Front wing leftovers
- Like-for-like zebra (both as exact smooth surfaces) to judge swirls on the wing top and the lip's front end.
- The small roll behind the arch (rear:b1, 38 vertices, 5.9 mm), fragments at the bottom-rear corner.

### 4. Rest of the body, panel by panel
Order: **roof** -> bonnet -> hatch -> front and rear bumpers -> sills. Kunos keeps the shell as one mesh (`GEO_body`)
with doors, bonnet, hatch and bumpers separate; we follow that split, pick each panel out with a clip box, then the
crease / band / wrap machinery. Rules that already hold:
- Corner wraps: `:wN` (one cut, matched seam). Arches: `:archN` when the lip is inside the region; when Kunos made the
  lip its own crease faces (rear quarter), plain bands + `:rall` do it.
- Fit every small face (`:rall`); the hole filler is a safety net only.

### 5. Assemble and check the whole car
Mirror the left half to the right; exact scores against the full skin; zebra and grey from all sides; one final
picture per finished section.

### 6. Make it AC-ready
Quad display mesh per face (~20 mm grid, 20-35k tris on the paint, loops along the lines, exact normals); unfolded
skin UV, baked AO, LODs, standard dummy names, two-layer glass.

### 7. Afterwards
Lamps, grille, badges; interior survey; then **from photos** (Nova first: it has solved cameras and traced windows):
trace outlines and character lines, run the same fit/trim/cut, check by eye. Parked: steward app, Nova grading.

## What happened on 10 Nov late (thin strips)
- Deep research (3 threads + report) on narrow strips between panels; report in `blender/research/reports/`.
- `strip_build.py` + FreeCAD stage: 14 strips on the quarter, 21 on the door, 5 on the wing; door 87.9 -> 88.4 %.
- Triangle winding now follows the exact normals for every face (fixes dark ruled faces).

## What happened on 10 Nov (short log)
Full detail is in git history and `ACHIEVEMENTS_REPORT.md` section 7.
- **Door finished:** crease strip (missing 5 mm ledge face; chamfer found with short section arms), window frame
  ring, beltline roll built as a true blend from the skin (tangent by construction), joins measured (`seams.py`),
  5 mm shut-line returns, every small face (`:rall`, wrap split > 70 deg). 80 faces.
- **Front wing:** wing picked out of the shell with a clip box; arch found automatically (R 354 mm); the lip follows
  the whole opening edge as a rail and stops where the flare stops; sub-panels at the arch (above / behind / in
  front) so character lines run edge to edge; ledges seen edge-on become step cut lines; FreeCAD approxSurface
  fallback; `regress.sh`; Class-A rule (fairest surface within tolerance).
- **Rear quarter (night):**
  - the side wraps round the rear corner into the strip under the lamp: `:wN` cuts once at 45 deg (k-means on
    normals sliced the tumblehome side into strips and lost its lines - don't);
  - the minor piece is fitted after the side with samples of the side's finished surfaces as data beside the seam,
    and both are cut on ONE smooth seam curve fitted halfway between them (no zig-zag teeth, no crack);
  - **line pinning** (all panels): neighbouring bands averaged and refitted on their shared line - joins 0.3-2.3 mm
    median -> 0.1-0.4 mm; it also lifted the door 87.6 -> 87.9 %;
  - **hole filler fixed:** it was laying bad second patches over correct faces where Kunos's flat triangles sag off
    the curve (the "fold" over the C-pillar corner). A far triangle is chord sag, not a hole, when a face lies over it
    along its normal and its three corners sit within 1.5 mm of our faces;
  - the C-pillar (r1) stays ONE surface: the 45 deg split runs along the whole pillar, and approxSurface gained nothing.
- New tools: `miss_map.py`, `pack_build.py`; FreeCAD step takes `cut_polys` (several cut areas per face).

## Rules Nik has set (keep)
- **Drives:** everything runs on **D:**; nothing uses C: (temp files in `D:\ClaudeData\tmp`).
- **Communication:** short messages; at the end of each turn, say what was done and show one picture; judge matches
  by eye (grey side by side with the original, same camera).
- **No smoothing "fixes".** Build crisp surfaces from curves.
- **Saving:** commit and push to the Claude- repo after each step; the public copy updates itself.
- **Assets:** never commit game assets or renders of them (kn5, textures, `images/` stay local).
- **Blender work:** load the blender-* skills and use the blender-mcp tools (standing approval).
- **Research first:** run the deep-research skill on how a new kind of problem is properly solved before tackling it
  (the wing's arch research is in `blender/research/reports/`).
