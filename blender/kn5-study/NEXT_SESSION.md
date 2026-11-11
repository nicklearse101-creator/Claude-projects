# Next session: Blender Work / AE86 replica (handover, 2026-11-11 midday)

**Start here.** Roof neighbours + C-pillar-top corners DONE (11 Nov, 13:00). Next job: the bonnet, then hatch (incl. the hatch
surround: the only uncovered Kunos facets at the rear roof corner are hatch surround, x < 0.45), bumpers, sills.
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
| Door (80 faces incl. glass, mirror, trims; 23 strips) | done | 88.5 % / 99.7 % | - |
| Front wing (arch lip, sub-panels) | done, small items left | 70.5 % / 96.1 % | 92.5 % / 99.3 % |
| Rear quarter + C-pillar (17 strips) | done 11 Nov: pillar + foot = one swept surface (sweep_build.py); small join items left (Next 0) | 85.9 % / 99.3 % | 90.1 % / 98.2 % |
| Roof (crown + rear band + 2 side bands + rear roll) + 7 neighbour strips | 11 Nov (roof_build.py): fair crown, G2 rear roll, strips on its built edges | 65.0 % / 100.0 % | 72.4 % within 0.3 mm, 97.0 % within 1 mm (median 0.13, max 1.2); strips median 0.07-0.27 mm |
| Bonnet, hatch, bumpers, sills | not started | | |

The **vertex** score is the honest one: Kunos uses 100-150 mm flat triangles that cut chords across curves, so the
area score marks a correct smooth surface as "off" between vertices.

Pictures (local, not in git): `D:\Claude\_scratch_research\kn5_study\images\` - `door_complete_vs_original_grey.png`,
`wing_v4_zebra.png`, `quarter_v6_foot_sweep_grey.png` (latest quarter: Kunos / before / now, foot close-ups).

## How to run (Nik's PC, everything on D:)
```bash
cd /d/Claude/Claude-/blender/kn5-study
./regress.sh all          # rebuild + score door, wing, quarter, roof (~7 min). Run after EVERY change to the fitters.
```
Reference (2026-11-11 13:00, one owner per surface): **door 88.5 / 99.7, wing 70.5 / 96.1, quarter 85.6 / 99.3** (area within 1 / 3 mm;
the quarter now leaves the roof's triangles out and snaps to the roof's edges);
**roof vertices 72.4 / 97.0 % within 0.3 / 1 mm** (`./regress.sh roof`, 50 s; also prints the neighbour strips).

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

### 0. C-pillar foot - DONE 11 Nov (sweep_build.py); small join items left
The foot is NOT a 3-way vertex blend: it is a flat deck + one wrapped skirt (side -> broad plan corner -> rear face)
joined by one tight roll that continues the pillar's shoulder. So the pillar's stations carry on past its end, marched
along the roll's spine (steered on the virtual sharp corner X, normal kept parallel to the deck) round the corner and
across the rear: 32 pillar + 22 foot stations, ONE grid surface (no pillar/foot join). Foot profile = top line (last
60 mm) + G2 blend + side curve c3 u^3 + c4 u^4; blend ends by a model search, pass 2 near smoothed setbacks; raw rows
smoothed column by column. The deck interior = face `r1d0` (fit to its own vertices + the sweep's top rows, cut on the
sweep's top edge by a band poly). `PF_PILLAR_FOOT=0` restores the old pillar + `r1x10` foot face.
Lessons (paid for): smoothing profile PARAMETERS separately broke their coupling (rows 7.7 mm off); smoothing the
setbacks hard can't follow the real 30 -> 3 mm change at the corner (77 %); FreeCAD `approximate` failed QUIETLY on the
54 x 32 grid (6 poles, 17 mm off) - the grid face now falls back to `interpolate` when approximate misses by > 0.5 mm.
Touch-ups done (11 Nov, `images/quarter_v7_foot_touchups_grey.png` / `_close.png`):
- corner pinch + pinhole: the blend's ends jittered between stations and columns tied to them slid along the surface
  (18 mm kinks, the interpolated grid pinched) -> every station is resampled at fixed arc distances from its anchor
  (the point nearest the virtual corner X) before the column smoothing (`PF_SWEEP_RESAMPLE`, default on);
- cracks on the deck join: the deck is cut on the grid face's REAL top edge (`cut_grid_edge` in the FreeCAD stage; a
  polyline through the stations cut chords, ~0.5 mm short round the corner); the prism may only SPLIT the face, so the
  deck-side pieces are kept by their centre of mass; the deck outline reaches 20 mm past the edge so the cut makes it;
- the pillar-base notch: the deck gets the sweep's flat top band (E0 + 0/8/16/24 mm) as tangent data - lumps gone.
  (A constant top arm put a hump over the window edge: reverted.)
Left: two faint hairlines on the deck join (sewing will close them), a thin dark sliver along the drip-rail edge near
the notch - check when the roof is built.

### 0b. C-pillar r1 - pillar part (11 Nov morning, kept as the first 32 stations)
Research: `blender/research/reports/Smooth region segmentation into faces.md` (12-step pipeline). Built
(`blend_build.py`, spec `GEO_body:pillar1`, in regress.sh):
- Sections square to r1's main axis; on 'pillar-like' stations (total turn 40-85 deg, < 110 mm wide) the designer
  profile = top LINE + G2 quintic shoulder blend + side LINE. A / D (blend ends) = where the signed cumulative turn
  passes 5 % / 95 %; the blend is fitted only to the TURN points (they lie on Kunos row edges = on the surface; points
  on diagonal edges are chords). The profile's defining data (edge points, A, D, blend tensions) is smoothed along the
  length, then every profile rebuilt; FreeCAD `approximate` through the grid (tol 0.02 mm).
- Stretch s -645..+135 mm (PF_PILLAR_S): 32 stations; top 34 mm, shoulder chord 22 mm turning 63 deg, side <= 21 mm;
  the shoulder widens to 37 mm at the foot. Pillar vertices p50 0.17, p95 0.50, max 0.73 mm (was p95 2.4 mm).
- Ends (roof junction `r1x00`, foot `r1x10`) = ordinary faces with the pillar's 3 end station rows as extra data
  (PF_PILLAR_JOIN) and an exact plane cut (`cut_planes`, new in the FreeCAD stage) at the end stations.
- Quarter 79.4 / 96.9 -> **84.4 / 99.5 %** area within 1 / 3 mm (vertices 88.3 / 98.6 %). Grey:
  `images/quarter_v5_pillar_grey.png`, sections `images/cpillar_sections_v5.png`.
Left:
- **Foot (r1x10)** = the whole tail-top corner (deck wrapping ~90 deg into the rear panel), one height field, p95
  2.4 mm; join to the pillar 0.5 mm median / 2.7 mm p95, visible as a soft line. MakeFilling on its Kunos outline
  failed (10 edges incl. clip teeth; `BRep_API: command not done` with points). Next try: split it like the pillar
  (deck top line + corner blend + rear face, stations along the car's x axis) or `:w` corner split, with the pillar's
  end rows as data; then a small G1 fill only where the shoulder dies out.
- Roof end (r1x00): faint line at the join (0.36 / 1.15 mm) - judge again once the roof is built.
- Flat-facet samples (corner normals within theta_max = 8 tau / L, tau 0.3 mm) as data in fit_panel / fit_bands:
  tested, not yet switched on.

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

### 3b. Roof - first build 11 Nov (`roof_build.py`, `roof_score.py`)
Run: `./regress.sh roof` (30 s), or by hand `python roof_build.py $C $R && PF_IN="$(cygpath -w $R)" ./fcrun.sh panel_fit_freecad.py && python pack_build.py $R X.npz &&
python roof_score.py $C X.npz`. Pictures: `images/roof_v2_rear_roll_grey.png` (Kunos / crisp line / roll), `images/roof_v1_grey.png`; crown isophotes `images/roof_crown_isophotes.png`.
Grey Kunos/before/now: `python D:/ClaudeData/tmp/roof/grey3.py BEFORE.npz NOW.npz OUT.png` (uses `view.py` there).
What the Kunos roof region (GEO_body, 422 tris, exactly symmetric, full width) really is:
- **crown** from the rear line (z ~ -0.896) to the windscreen header; the front rolls down progressively (no line);
- **rear band**: a flat ~16 deg strip behind a crisp-ish line (~10 deg turn in one row) down to the rear edge;
- **side bands** (rear half only, z < -0.517): ~20 deg strips outside the side line (x ~ 0.461, Kunos holding loops at
  0.457 / 0.466), out to the C-pillar shoulder; in front of z -0.517 the drip strip (own Kunos region) takes over.
How it is built: every face is a B-spline over the PLAN (frame s = z, t = x, h = y) so shared trim curves are the same 2D
curve in both faces; bands are fitted to their vertices + the crown / each other along the shared edges (G0 rows,
seams 0.003-0.03 mm). The crown is ONE surface mapped to its edges: s' = 1000 (z - zr(x)) / (zf(x) - zr(x)) (rear line /
front edge as even quartics, so the map is exact in the x basis), single span degree 7 along x degree 5 across, knots at
s' 500 / 850, mirror-paired poles; trim curves converted to (s', x) (1-4 um). FreeCAD stage now reads `du` / `dv`.
Lessons (paid for, all with isophote maps - `iso()` stripes of n.L, islands = waviness):
- Kunos roof VERTEX HEIGHTS are lumpy at 0.3-0.7 mm, but its vertex NORMALS are fair. A plan-grid crown fitted to the
  vertices (9x14 cubic, 0.09-0.14 mm RMS) ripples visibly in grey; third-derivative fairing only clears it at lambda 1e7
  (1 mm RMS, 3 mm max). Normals as slope data are inconsistent with the heights (p95 20-30 deg near the edges where
  Kunos averages across creases; interior ok) and do not fix it either.
- The centreline row sits ~1.1 mm HIGH against every smooth symmetric crown: Kunos's half-model leaves a slight ridge
  at x = 0 (row slopes 1.5 deg at once beside the centreline, 2.4 deg further out). Our fair crown ignores it - by
  design (the real roof and Kunos's own normals are smooth there).
- Leaving the holding loops out of the crown data made the side bulge WORSE (9.7 mm): kept in (RF_HOLD=0).
- Fair crown + chords: the facet distance in the 313-459 mm side strip is real chord sag (~1.3 mm predicted), not error.
**Rear roll - DONE 11 Nov midday** (`rear_roll` in roof_build.py, `RF_ROLL=0` = old crisp line):
- Kunos rows across the line (x 0): z -833 / -871 / -896 / -917 / -942, facet slopes 2.0 / 5.5 / 15.7 / 16.1 deg; the
  vertex normals are plain averages of those facets, so AC shades the 10 deg turn as a soft roll from row -871 to -917.
  The side line (holding loops x 457 / 466 round 461.5) runs straight on through the rear band to the rear edge: the
  two lines simply cross.
- Rear line R(x) = even quartic through the old crown/rear and side/rear edges (0.27 mm). Roll from zB = R - 21 (rear
  band) to zA = R + 25 (crown; side band outside the side line) = `RF_ROLL_A` / `RF_ROLL_B`. Parameters (u, x), u =
  z - zB: z linear in u, quartic in x -> exact. Height = QUINTIC Hermite in u matching value, d/dz, d2/dz2 of both
  neighbours at constant x -> G2 on both edges by construction (checked: G0 0 um, normals <= 0.0002 deg; 0.05 deg in
  the last 1.5 mm at the ends). One span deg 5 across, deg 5 along with the rear band's x knots as TRIPLE knots (its
  jets are only C2 there; without them 0.08 deg); a knot 1.5 mm from an end made huge end poles - dropped.
- Split at the side line x = +-461.5 (where it meets zA): centre piece (front = crown, untrimmed natural edges) +
  two corner pieces (front = side band, outer end trimmed on the roof outline in (u, x)). Pieces meet within 5 um;
  the side line's crease fades out across the roll to nothing at the rear band.
- Neighbours cut back with plan polygons on the exact edges (`cut_polys`, 10 mm segments: 1 mm segments made the crown
  mesh 124k tris / 8 min; now 30k / 22 s; the FreeCAD stage takes a per-face `maxlen`, crown 12 mm).
- Joins on the built meshes: roll to crown / rear band 1-6 um (p95 5 um); corner pieces 0.06-0.12 mm = display-mesh
  chord sag on the tight side-band curvature (the surfaces meet exactly).
- Scores: vertices 67.2 -> 67.9 % within 0.3 mm, 97.0 % within 1 mm, max 1.2 mm unchanged (the roll sits up to ~0.9 mm
  under the old corner vertex row at z -896, as a real radius must).
- White specks in grey renders: NOT pinholes (every face's open edges form one loop = its outline); z-buffer raster misses.
Left (in order):
1. Nik (11 Nov): the roll "looks ok"; he will judge it properly later, with the complete car. Keep RF_ROLL_A / _B
   (25 / 21 mm) until then; narrower = sharper. Don't spend more time on it now.
2. Neighbours - DONE 11 Nov 12:00 (`neighbour_strips` in roof_build.py, `RF_STRIPS=0` = off). Every roof neighbour in
   Kunos is a thin return 2-4 mm wide (crease pieces of GEO_body above y 1.0; piece 0 = roof): windscreen header r11,
   drip strips r12/r13, rear header strips r9 (on the roof) + r10 (on r9 and the hatch surround r1), corners r18/r19.
   Built by strip_build: the roof side's nb_name is the prefix 'roof:' (every roof face), so its rail IS the roof's
   built edge (0.02 mm); strips are named 'roofnb:rN'; a side on a region not built here = Kunos vertices.
   Kunos strip vertices -> ours (median / max): r9 0.11, r10 0.18, r11 0.17/0.42, r12/r13 0.07/0.38, r18/r19 0.27/1.10.
   Fixes on the way: the roof outline sides are now fitted to the polyline resampled every 5 mm (fitted to vertices
   50 mm apart they wiggled +-2 mm and the drip strip could not use the edge; roof vertices 67.9 -> 72.4 % within
   0.3 mm); `face_edge_points` keeps, where two built edges run side by side, only the one nearer the Kunos side
   (crown outline vs side-line edge at the drip strip's rear end); `regress.sh all` unsets PF_CLIP before the roof
   (the quarter's clip box broke the roof step). Picture `images/roof_v3_neighbour_strips_grey.png`.
   **C-pillar-top corners - DONE 11 Nov 13:00** (picture `images/roof_v4_cpillar_corners_grey.png`):
   - Rear header strips r9/r10 wrap ~30 mm down round each rear roof corner: built as CHAIN strips now (strip_build
     prefers the chain version when its spine is > 3 % longer; strips under 5 mm may turn 30 deg per 20 mm, wider
     ones 20). r9/r10 Kunos vertices max 20 -> 1.27 mm.
   - **One owner per surface:** the quarter build used to remake the roof's edge (a side-band sliver, the header
     strip ends, the drip-end corner) -> two overlapping surfaces, blotches in grey. `PF_NOROOF=1` makes
     `load_mesh` leave out every triangle the roof build owns (`roof_build.roof_owned`: roof + its neighbour strips);
     quarter clip y now 1.3 (the 1.235 clip orphaned 4 C-pillar-top triangles = the white line across the pillar top).
   - **The roof is the master** (`PF_MASTER` = its packed build): in `fit_panel`, a piece's outline loop that runs
     within 2.5 mm of the master's open boundary is densified (2 mm) and moved onto it, and those points are fit
     data (x3). Window-surround panel (quarter r4) <-> roof: gap median 0.32 -> 0.04 mm. regress.sh builds the roof
     FIRST, then the quarter. Quarter 85.8 -> 85.6 % (r4 fit p95 0.29 -> 0.54 mm: it now passes through the
     roof's edge, incl. the vertex-fitted wrap ends).
   - Tried and dropped: the roof's strips taking the QUARTER's built pillar edges (`PF_FOREIGN`, per-face BREPs in
     `<build>/faces/` - the mechanism stays): it fed the old quarter edge error round in a circle. Masters first.
   - Left (small): r18/r19 corner strips and the wrap ends use Kunos vertices for their pillar side (0.6-0.8 mm);
     Kunos shades its 2-4 mm returns as soft rolls (bent normals), ours are crisp (exact normals) - judge on the
     complete car.
3. The side line itself is a ~9 mm roll in Kunos (holding loops 457 / 466) and still a crease in ours - same quintic
   roll machinery along x if Nik wants it softer.

### 4. Rest of the body, panel by panel
**Roof research done:** `blender/research/reports/Roof surfacing.md` (16-step build table). Key points: roof = master
surface, one full-width face overshooting 20-40 mm, degree 5 single span vs cubic by cross-validation; fit VERTICES only
(roof facets are chords: the 4 deg flat-facet rule would wrongly feed sagged samples - use 8 tau / L ~ 0.9 deg);
third-derivative fairing, not thin-plate (it flattens the crown); score vertex RMS + signed crown bias, not area within
1 mm; own numpy least squares with G1/G2 rows (MakeFilling can't do G2); trim with `Part.Face(srf, wire)`; then refit
r1x00 and the drip strips from the roof's own edge.
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

## What happened on 11 Nov (13:00)
- C-pillar-top corners: header strips wrap the corners (chain strips), one owner per surface (PF_NOROOF), the roof as
  master for the quarter (PF_MASTER, roof built first), quarter clip y 1.3; regress.sh clip leaks fixed.

## What happened on 11 Nov (noon)
- Roof neighbour strips (7 per car) built on the roof's own edges; roof outline resampling; edge sampler picks the
  nearer of two parallel edges; regress.sh PF_CLIP fix. Door / wing / quarter unchanged (88.5 / 70.5 / 85.8).

## What happened on 11 Nov (midday)
- Roof rear line rebuilt as an exact G2 quintic roll (3 faces), neighbours cut back on its edges; roof added to
  regress.sh; roof build 9 min -> 30 s. Picture `images/roof_v2_rear_roll_grey.png`.

## What happened on 11 Nov (night)
- Chain sides (drip rail r7, door SUB1 r12/r14), fold flanges (C-pillar window flange r6 as two strips), sanity checks
  incl. the sharp-corner rule (door SUB0 r4 stays a face). Commit 7b29ae3.
- Blender was not running: grey pictures made with `grey_render.py` (numpy z-buffer,
  smooth shading, same ortho camera for Kunos and ours).
- Found the C-pillar "tube" (Next 0).

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
