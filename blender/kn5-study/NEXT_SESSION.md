# Next session: Blender Work / AE86 replica (handover, 2026-11-12 morning)

**Start here.** HATCH in progress (report `blender/research/reports/Hatch surfacing.md`). The hatch is NOT a separate Kunos
mesh: it is GEO_body crease piece 2 + returns (pieces 4, 14, 22, 116/117), and the quarter's old "C-pillar" sweep (r1p,
r1x00, r1d0) WAS its side band. Built 12 Nov (`hatch_build.py` + `hatch_score.py`, `./regress.sh hatch` ~4 min): ONE U-shaped
sweep (side bands + tail roll, left half marched to the centreline and mirrored, symmetric to 0.0004 mm) + header + deck.
Skin vertices median 0.15 mm, 94 % within 1 mm; pillars 100 % within 1 mm. NEXT (in order):
- **Lower corners** (the weak spot): Kunos wraps them in a FAN of straight vertex rows 15-20 deg apart; sections between
  rows see only chord points (up to ~4 mm sag), so the corner creases. Build the corner stations THROUGH the Kunos rows
  (find the rows from the bottom-edge vertices up to the knee) or a dedicated corner patch; the outline's small corner tab
  (x +-673, z -1964, up to 12 mm miss) needs its own small patch (with the corner bits 116/117).
- Header / pillar-top join: plane cut + fitted header; looks clean in v3 grey, header max 1.1 mm.
- Returns: ring (piece 4, 20 mm, closed: cut at x = 0), glass-bottom wall (14), bottom return (22) with strip_build on the
  built edges; then watertight check, clearance.
- Quarter: rebuild with `PF_NOHATCH=1` (spec without `pillar1`, `rall!0`), its drip rail's hatch-side rail from the
  hatch's faces (`PF_FOREIGN`); regress order roof -> hatch -> quarter (regress.sh already builds the hatch before the
  quarter, but the quarter step does NOT use PF_NOHATCH yet: both builds still make the left side band).
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
| Bonnet (skin, nose, 13 edge strips, corner rounds, underside, nozzles) | done 11 Nov | | skin 100 % within 1 mm, edges 99.2 % |
| Hatch (U sweep + header + deck) | skin built 12 Nov (hatch_build.py); lower corners, returns, quarter switch left | | skin median 0.15 mm, 94.4 % within 1 mm (pillars 100 %, tail 90.5 %: corners) |
| Bumpers, sills | not started | | |

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

### 3c. Bonnet - first build 11 Nov (`bonnet_build.py`)
- Kunos skin = GEO_hood_SUB1 crease region 0 (1274 tris, mirror-exact). C (raised centre, full width, sym poles, deg 5,
  z knots 880/960/1040/1250/1450/1650, x knots +-150/300/400/470, lam 10): vertices rms 0.30, max 0.71 mm = Kunos's own
  +-0.6 mm lengthwise washboard (rows alternate at 100 mm; our fair C ignores it, by design). O (outer, right fitted,
  left mirrored, deg 5 x 3, single span across): rms 0.21 mm (the washboard reaches its rows near the line).
- Step line: fair plan spline through the measured mid-row points, tail tip (440.9, 885.2) -> hook (R ~44) -> notch
  corner (361.5, 1721), 914 mm; left side = C all along (rearward on the tail). Band = quintic Hermite across from C's
  jets at A and O's at B (width 8 mm at the tip, 16 through the hook, 20 on the rear main run, 10 at the notch),
  55 poles along incl. 9 triple-knot crossings of C / O knot lines; Hermite fit 1 um.
- The tail dies by height: C fitted with G2 rows = O along the seam S (the band's end cross-section carried on
  rearward): value 0.6 um, slopes 1e-4. Behind the tip (s < 0) everything is O (= C there).
- Classification lessons: the outer panel's FRONT edge vertices (lamp bays, x >= 366, z < 1730) must be O data, or O
  dives 9 mm at the notch; the rear zone behind the hook needs C knots at x +-400/470 (else 1.8 mm misses there).
- FreeCAD: all bonnet faces use the outline-prism cut (own_plane) + cut_polys; cut polygons thinned to ~5 mm segments
  (4000-point polygons hung OCC for 13 min). Build 2 min.
- Score (Kunos vertices, no nose): median 0.13, p95 0.55, max 1.27 mm, 99.6 % within 1 mm; band rows max 0.69 mm.
  Picture `images/bonnet_v1_panels_step_grey.png`. Visible: tiny gap/dip at the notch corner where band, C and O end.

**Nose - DONE 11 Nov pm** (`front_face` + `nose_roll` in bonnet_build.py; `BN_NOSE=0` = old build; picture
`images/bonnet_v2_nose_roll_grey.png`, roll choice `images/bonnet_v2_nose_A_vs_B_grey.png`):
- Kunos nose = one section swept across x: rows at the same heights in every column (front-face rows y 655.40 / 639.27
  everywhere), shifted in z by the bowed plan front edge e(x) (6.3 mm over +-348; even quartic in x, 0.28 mm = Kunos chords).
- Front face F: h = a(x) + b(x) (z - e(x)), fitted to the face rows (z > e - 26): slope -52.53 deg, rms 0.25 mm. B-spline
  degree 1 x 5 (exactly straight along z).
- Roll: parameters (u, x), z = e(x) - A + u, W = A - B constant -> exact in x. A QUINTIC G2 Hermite could not do it: Kunos's
  roll is progressive (only 6 deg turn over z 1770-1855, then 31 deg in the last 27 mm), so a quintic sat 4-5 mm high, or
  (roll starting late) C did the bending (R 28 mm). Now DEGREE 7: c0-c2 from C's jets, c5-c7 from F's (G2 by
  construction; checked on the poles: G0 0.3 um, slopes equal, d2h/dz2 diff 5e-8 /mm), c3 / c4 = straight split + ONE
  fitted offset each for the whole width (x-dependent offsets overfitted: +-12 mm swings).
- A / B chosen by eye: best vertex fit A 68 / B 20 (rms 0.24, R_min 43 mm) showed a dark band in grey; A 72 / B 16
  (R_min 68 mm, research target 70-110) reads like Kunos -> default (`BN_NOSE_A` / `BN_NOSE_B`). No inflection.
- C now takes tongue data up to the roll start (z < e - A + 1) and its domain runs to z 1900 (its jets at the roll start).
  C max 0.71 -> 0.84 mm (the new tongue rows), band-edge slope miss 0.85 -> 1.07 deg.
- Scores: nose 135 vertices median 0.17, p95 0.46, max 0.76 mm, 100 % within 1 mm; all 695 skin vertices median 0.13,
  99.7 % within 1 mm. The 0.9 mm tip facet (-62.4 deg) is left to the nose chamfer strip (step 11).
- Lesson: cut polygons with 10 mm segments across the centre face made Mefisto mesh it 4x finer (99k tris, 4 min); 42 mm
  segments (chord sag 0.02 mm) -> 25k / 34 s. panel_fit_freecad.py now says when Mefisto fails and falls back.

**Edges - DONE 11 Nov evening** (`edge_strips` in bonnet_build.py, `BN_STRIPS=0` = skin only; picture
`images/bonnet_v3_edges_grey.png`; build 3.5 min):
- Every Kunos edge crease region of GEO_hood_SUB1 is a ruled strip (strip_build): side chamfers r9/r10 (1.2 mm) -> side
  returns r2/r3 (13.6 mm); nose chamfer r11 -> lip r4 (7.3 mm); notch chamfers r12/r13 (1.3 mm, CHAIN round the R 9.3
  notch corner) -> lamp-bay walls r5/r6 + tongue walls r7/r8; rear flange r1 (15.7 mm straight wall). Skin side = the
  skin's built edge ('hood:' prefix, 0.01-0.12 mm); strip-strip curves shared.
- strip_build options (default off, the bonnet turns them on): `corner_free_w` (chains narrower than this skip the
  sharp-corner check: the 1.3 mm notch chamfer turns 90 deg), `ruled_inside` (a region with inside vertices that are within
  `SA_TOL` 0.3 mm of the rulings is a plain strip: the flange's holding rows), `vctrl_mm` per strip (Kunos-vertex rail
  control spacing; 4 mm on the notch chamfers: their wall-side rail was 1.9 mm off round the corner, now 0.28).
  `SB_PAR_MAX` (parallel-rulings exemption) exists but is off: merging corner patches into walls lost the corners.
- Corner fills (new FreeCAD stage, `corner_fill` entries): the Kunos corner patch outline (1 mm) is snapped onto the
  nearest built edge (1.5 mm); its SIDES are the snap runs. Two long runs on two strips (wall ends) -> **G1 round**: cubic
  Hermite sections leaving each wall along its own surface (arc handle length), lofted (r14-r21: front outer corners,
  notch corners, rear corners, nose corners - they now read rounded like Kunos's averaged normals). Otherwise a Coons
  patch on the 4 runs (r22-r25). `makeFilledFace` ballooned 10-14 mm off - never use it here; Part.makeFilling does
  not exist in FreeCAD 1.1.
- Notch skin gap fixed: C's cut at the band's notch end now follows the band's slanted end edge (a wedge was uncovered).
- `pack_build.py` bug fixed: normals were looked up by name PREFIX ('hoodnb:r1' took 'hoodnb:r10' -> zeros -> black
  flange). Exact name first now; any earlier build with r1/r10-style names may have had zero normals on some faces.
- Scores: skin 695 vertices median 0.13, 100 % within 1 mm; edges (526 Kunos vertices r1-r13) median 0.06, p95 0.50,
  max 1.2 mm, 99.2 % within 1 mm (the rounds sit up to ~1.2 mm off Kunos's flat corner triangles).
- Left: pin-holes ~1-2 mm on top of each round (round top vs chamfer ends + skin corner) -> sew step; the rounds' outline
  is 1.8-2.8 mm off Kunos's chord outline by design (a real radius); seams.py still reads narrow strips' far edges as joins.

**Steps 13-14 - DONE 11 Nov night** (picture `images/bonnet_v5_complete_grey.png`; `./regress.sh bonnet` 3.8 min):
- OCC sewing (`sew_build.py`, kept for later) REFUSES the boolean-cut skin faces (centre, outer L/R, bands) even at 1 mm,
  though the joins measure 0.02 mm; strips, corner fills and nose faces do sew. Part::Sewing is not available headless;
  ShapeFix / rebuilding did not help. Not solved - the watertight check is done on the meshes instead:
- `mesh_holes.py BUILD.npz 0.3 [--fill OUT]`: a face's boundary edge is free when > 0.3 mm from every other face; free
  edges chained into groups. Found a real defect: C kept a FLAP over O along the lamp-bay front edge (two owners) -> polyO
  now runs forward along x = B-end ahead of the band. Left: 8 pin-holes (2-10 mm, corner meetings) -> fan patches
  ('holefill:k', mesh only). Remaining free = the real open bottoms (flange+returns 3.3 m, lip, walls) + 4 bits <= 2 mm.
- `clearance.py`: vs every Kunos mesh within 40 mm (GEO_body, headlights, details, wipers, side lights): closest approach
  ours = Kunos's (body 1.01 / 0.98, headlights 0.02 / 0.01, details 0.14 / 0.14 mm); 'behind our surface' counts equal
  Kunos's own under the same test (shared seats); side gap at z 1650 2.71 vs 2.62 mm.
- `underside_build.py`: cap from OUR free bottom loop (chained, 10 mm resample) -> rim 10 mm inside / 10 mm under the
  skin -> lid on a 120 mm plan grid 25 mm under the skin (Delaunay, inside the rim). 1623 tris, never above the skin,
  Kunos SUB2 vertices median 0.9 / p95 5.3 mm. Washer nozzles (Kunos SUB0 measured per z: 18.6 x 11.5 mm to z 963, then a
  quarter-ellipse to 8.4 mm at a blunt front): superellipse loft, own-vertex end caps; Kunos vertices median 0.48 / max 1.2.
- Left (for the AC-ready stage): the notch pin-hole fan shades dark; the lid shows faint facets; nozzle front face crisper
  than Kunos's; B-rep sewing of the skin faces.

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

## What happened on 12 Nov (morning)
- Hatch measured: part of GEO_body (piece 2, 1270 tris), exactly symmetric; the quarter's 'C-pillar' was its side band.
- `hatch_build.py`: U sweep = sweep_build's pillar stations (unchanged) + the foot march run on to x = 0 over the whole
  skin (`Fm`), then: pass 2 re-cut square to a smooth spine (the march's own planes swung +-0.3 rad round the corner);
  rows anchored at the 15 deg turn point (the old anchor / blend ends jittered 2-24 mm); top arm 25 mm (deck is its own
  face); rows end ON a fair outer-edge curve (scalloped skirt edge before); one symmetric smoothing spline along the spine
  (30 mm knots); mirrored; FreeCAD `approximate` deg 5 (dev 0.001 mm) with a STRUCTURED mesh from the grid's (u, v)
  (5 min of srf.parameter() normals -> 20 s).
- `sweep_build`: `SIDE_C2` = skirt curve with curvature at D (u^2 term) and the quintic blend made G2 to it
  (w = 2.5 c2 b^2 on the 4th control point): side rms 0.6-0.8 -> 0.15-0.45 mm. `edge_cos` (steep-edge filter) kept as an
  option, off: it starved the corner sections.
- `panel_fit_freecad`: deck cut polygon thinned by Douglas-Peucker (0.02 mm): 155k triangles / 19 min -> 10-40k / 10-80 s.
- Tried and dropped: vertex refinement of the grid (offset field on Kunos vertices, `HT_REFINE=1`): vertices median 0.10
  but ridges along the knee and pillars in grey (index-space bicubic vs the real surface, field too free).
- Pictures (local): `D:/ClaudeData/tmp/hatch/hatch_v3_grey.png`, `v3_botcorner.png`, `wire_corner_b.png` (Kunos fan).

## What happened on 11 Nov (night)
- Bonnet complete: mesh watertight check (C flap over O fixed, 8 pin-holes filled), clearance = Kunos, underside cap, nozzles.

## What happened on 11 Nov (evening)
- Bonnet edges: 13 edge strips, 12 corner fills (G1 rounds on wall corners), notch skin gap, pack_build normals bug.

## What happened on 11 Nov (afternoon, late)
- Bonnet nose: straight front face + degree-7 G2 roll (shape chosen by eye, R_min 68 mm); bonnet build 2.5 min.

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
