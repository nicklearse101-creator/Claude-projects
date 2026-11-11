# Panel-fit technique (CAD reverse engineering) - the method that made the crisp AE86 door

2026-11-09. Proven on the AE86 door (skin, character lines, window frame) and all of its glass.
Tools: `panel_fit.py` (plain Python: fits) -> `panel_fit_freecad.py` (FreeCAD via `fcrun.sh`, D: only:
trimmed CAD faces, STEP, display mesh) -> exact normals -> Blender. Scoring: `score_exact.py` / `exact_dist.py`.

## The idea in one line
Each panel is **one smooth B-spline surface with as few control points as it needs**, fitted to the
data and **trimmed to its real outline**; character lines are **drawn as fair curves end to end** and
the surfaces either side are **cut exactly on the same curve** - so edges are crisp and surfaces are even
by construction. No smoothing step anywhere.

## Steps
1. **Split like a modeller, not by triangles.**
   - Hard creases (dihedral > 20 deg) -> separate regions (door: upper skin, crease band, lower skin).
   - Inside a region, **character lines** from cross-sections: sharp turns (>10 deg over 12 mm arms) on
     sections every 20 mm, chained along the panel, each fitted as ONE fair curve t = g(s)
     (<= 10 controls, 1 mm tolerance). Sorting triangles by curvature does NOT work (Kunos uses long thin
     triangles -> jagged bands).
   - A strong line (>= 25 deg turn) is a rolled edge: it gets its own narrow **fillet band**, width = the
     band holding 90 % of the turning, measured from the real profile vertices.
   - Openings (window) = section runs broken where no segment covers the interval (NOT where vertices
     are far apart - Kunos vertices can be 40 mm apart on a continuous surface).
2. **Fit each surface to the VERTICES, not the facets.** Vertices lie on the designer's surface
   (lower door skin: 0.08 mm); flat facets between them are chords.
   - Cubic B-spline height field over the panel's best-fit plane, least squares + bending fairing.
   - Uniform clamped knots, poles at Greville points => surface parameter = plane coordinate, so the
     outline projected on the plane IS the trim curve in parameter space.
   - **Control count and fairing by 5-fold cross-validation** (predict vertices the fit has not seen),
     searching **both directions independently** (4..14 each); simplest model within 5 % of the best.
     Tying the counts to the panel's proportions was a bug (door lower skin: 4x4 1.7 mm -> 4x11 0.09 mm).
   - **Folds must be BLOCKED** (hold out whole 40 mm patches, checkerboard), not random vertices: with random
     hold-outs every vertex still has close neighbours on its own mesh row, so grids that ripple BETWEEN the
     data pass the test (zebra showed wood-grain swirls). Blocked folds removed the ripples.
3. **Trim.** Outline = the mesh's boundary loops (largest = outside, others = openings); corners where
   the polygon turns > 35 deg; each side a 2D B-spline pinned to its corners (fewest poles within 0.4 mm,
   light fairing). In FreeCAD: 2D curves -> edges on the surface -> `Part.Face(srf, wire)`, `cutHoles`.
4. **Cut bands on their character lines**: prism over the area between the two line curves, extruded
   along the panel normal, `face.common(prism)`. Neighbouring bands use the identical curve -> crisp line.
5. **Display / export**: even mesh (`MeshPart MaxLength=6`, NOT the default deflection mesher - irregular
   triangles tear zebra stripes) + **exact normals from the surface** as custom normals (how Kunos gets
   smooth reflections from few triangles).
6. **Check**: zebra stripes (reflection Z x 40, emission) side by side with the original, separately
   (hide the other - objects in front of the camera pollute the view); exact two-way distances.

## Results (AE86, method test)
- Glass: 4 pieces, 20-40 controls each, areas match (door glass 0.349 = 0.349 m2), within 3 mm everywhere.
- Door: 8 faces (image: `D:/Claude/_scratch_research/kn5_study/images/door_panelfit_vs_original_zebra.png`, ours left), areas match (0.474/0.287/0.062 vs 0.469/0.286/0.061 m2); lower skin 0.08 mm,
  groove bands 0.03-0.2 mm; zebra as smooth as, or smoother than, the original.
- Still weaker: the window frame band and the shoulder roll (~1.5 mm p95) - next to refine.

## Lessons that cost time (do not repeat)
- Measure exactly: point-to-point scoring on 4 mm samples added ~1 mm of fake error to everything.
- Never trim panel edges to a global smooth fit (v4 cubic edge trim silently removed 6 % of the car).
- Glass in Kunos cars is tiny (door glass 41 tris); the black "mask" mesh is texture, not shape.
- Blender's bundled Python has no PIL: run kn5/section analysis outside Blender, load npz inside.

- (2026-11-10) Section arms must fit the region: a fixed 12 mm arm skips narrow regions (45 mm strip) and
  hides turns within 12 mm of a panel edge. Arms now scale with region width and shrink at section ends.
- (2026-11-10) Sharp lines sit on a vertex: snap to it, and keep band overlap tight across them (a 2 mm
  overlap pulled a chamfer vertex 1 mm past the corner into the flat strip: 0.31 -> 0.08 mm).
- (2026-11-10) Kunos vertex rows can be 25 mm apart across and 150 mm apart along: a band edge with no data
  swings wildly. Across soft bounds, take the next vertex row (at most 50 mm out); never across a sharp line.
- (2026-11-10) Limit a character line's controls to about one per 12 sections, or it chases facet corners
  and swings past its last hit.
- (2026-11-10) Report face scores to the original's facets (`score_faces.py`), not vertex-fit p95; per-face
  original -> ours is meaningless with 200 mm Kunos triangles; use whole-build coverage.

- (2026-11-10) Rolled edges with sparse data: build them FROM the neighbour (skin minus a drop profile, zero
  value and slope at the boundary) instead of fitting them freely; give them their own along/across directions.
- (2026-11-10) Fit outline curves to the polyline resampled every 5 mm, never to sparse vertices alone (long
  sides wiggle, closed ovals overshoot by 100 mm).
- (2026-11-10) Fit every face, however small (`:rall`); faces wrapping > 70 deg split by normal direction.

## For the photo phase
The inputs are exactly what photos/blueprints give: panel outlines, character lines (traced curves) and a
few sections/points per surface. The fit + trim + band-cut machinery is unchanged.

- (2026-11-10 night, rear quarter) A panel wrapping a corner (side into tail): ONE cut at 45 deg from its dominant
  direction (`:wN`), never k-means slices. The minor sub-panel is fitted after the main one with samples of the main's
  finished surfaces as data beside the seam, and both are cut on one smooth seam curve (not the triangle zig-zag).
- (2026-11-10 night) Bands must be PINNED to their shared character line (average both heights on the line, refit both
  with it weighted): sparse data lets neighbours disagree by 1-3 mm and it shows as dark lines.
- (2026-11-10 night) Never fill "holes" that are only Kunos chord sag: test whether a built face lies over the triangle
  along its normal, not just its centre's distance.


## Thin strips (2026-11-10 late, `strip_build.py`)
Research: `blender/research/reports/Narrow strip surfacing between panels.md` (Alias Panel Gap / Fillet Flange, the
Várady/Geomagic pipeline, OCCT source). Every source builds the strip ON the panels' own edges, never fits it and makes
it meet them afterwards.
- **Detect:** a crease region with width (area / length) < 15 mm and length > 10 x width, one outline, two long sides
  (runs of its outline shared with one neighbour each, or free) both covering >= 70 % of it. Default on (`PF_STRIPS=0`
  turns it off); a strip whose sides cover < 85 % of its length (a side made of runs along several neighbours: the
  1.4 m drip rail r7) stays an ordinary face for now.
- **Spine:** midline from nearest-point pairs between the two sides (not equal arc fractions: one side can run
  longer), parametrised by side A's arc length, then by its own; every curve of the strip is a 3D B-spline whose
  parameter = arc length along the spine (curved strips work).
- **Sides:** only the stretch running ALONG the spine (ds/darc > 0.7) - at the ends the outline turns across the strip.
  A side on a wide face = that face's BUILT edge sampled every 1 mm (only where its tangent runs along the side) and
  refitted: 0.01-0.02 mm. A side shared by two strips, or free = fitted once to the Kunos boundary (one control per
  20 mm, 0.3 mm) and reused by both strips.
- **Surface:** `Part.makeRuledSurface(e1, e2, 1)` - orientation 1, automatic flipped a rail (bow-tie, double area).
  Each rail runs to its own end corners (slanted ends kept). Cut rails at known parameters, never with Geom
  closest-point lookups (they returned far local minima: a 0.7 mm rail).
- **Triangle winding** must agree with the exact normals (ruled faces mesh inward): renderers shade a back-facing
  triangle with its normal flipped - the lamp-top wall came out dark although the geometry matched to 0.1 mm.
- Result (rear quarter): 14 strips, each within 0.1 mm median of Kunos; joins on shared edges 0.00-0.01 mm median.
  Kunos bends the vertex normals of its returns 25-45 deg (soft look); we keep exact normals.

### Chain sides, fold flanges, sanity checks (2026-11-11)
- **Chain sides:** when no two single-neighbour runs make the long sides, the strip's ends are the two outline vertices
  farthest apart (first from the centroid, then from that one) and the outline between them is the two sides, each a
  chain of runs (drip rail r7: [r4 roof + r1 C-pillar] and [free gutter lip + strip r21]). ONE curve per side, fitted
  to the built edges of every wide neighbour along it (0.02 mm per point) plus Kunos vertices where no edge reaches
  (0.3 mm per point; `fit_graph` takes a per-point tolerance). The curve is also stored under each run's key, so a
  neighbouring strip (r21) reuses it: exact join. Chain strips are built first.
- **Fold flanges:** a region up to 30 mm wide and > 25 x as long counts as a strip when it is straight across (no
  vertex inside) or has ONE fold row (inside vertices at a constant distance from a side, std < 1.5 mm): two ruled
  strips side A -> fold curve -> side B, sharing the fold curve (C-pillar window flange r6: 7 mm step + 14 mm flange,
  was an ordinary face at p95 5.2 mm).
- **Sanity checks** (strip dropped, region stays an ordinary face): each side a graph over the spine within 3 mm; ruled
  area 0.5-2 x the region's; for chains, no corner sharper than 20 deg per 20 mm (the door's U-shaped window-frame strip:
  inner and outer rails differ in length round the corner and the rulings skew - covered 50 % instead of 94 %).
  In FreeCAD, a side curve that misses its face-edge samples by > 1 mm is refitted from the Kunos vertices alone.
- Results: drip rail 0.09 mm median (97 % of vertices within 1 mm); quarter area 78.3 -> 79.4 % within 1 mm, vertices
  86.3 -> 88.2 %; door 88.4 -> 88.5 %; wing unchanged.

### Flat facets are data, chords are not (2026-11-11 finding, not yet in the fitters)
Kunos's vertex normals tell a flat facet from a chord: where a triangle's three corner normals agree (within ~4 deg)
the facet is meant flat, so its inside is real surface; where they differ it cuts a chord across a curve. Fitting to
vertices only, our C-pillar (r1) bulged up to 9.8 mm over the pillar's flat top facet (45 mm with no vertex across it):
it reads as a round tube in grey, though the vertex score is fine. Samples of the flat facets (every 15 mm) as extra fit
data: flat-facet misses p95 3.9 -> 1.2 mm. See `images/cpillar_sections_kunos_vs_ours.png` (sections z = const).

### Soft-shoulder pillars: station profiles (2026-11-11, `blend_build.py`, spec `:pillarN`)
A region whose cross-section is flat face -> shoulder -> flat face with no crease (the C-pillar) is NOT one fitted
surface (a height field rounds it into a tube) and vertex-neighbourhood segmentation can't split it (its top face has
no vertex of its own). Measure the turn per cross-section instead (research report "Smooth region segmentation into
faces"): station sections every 25 mm; top and side = straight lines through the points outside the turn (5 % / 95 %
of the signed cumulative turn); shoulder = G2 quintic Bezier tangent to both lines, fitted only to the turn points (on
Kunos row edges, so on the surface). Smooth the profile's defining points along the length, not grid columns (column
smoothing moved points 1-2 mm). Ends: ordinary faces given the pillar's last rows as data + exact plane cuts.

### Pillar + foot as one sweep (2026-11-11, `sweep_build.py`)
A shoulder that runs on past a pillar's end round a corner (the C-pillar's roll between rear deck and skirt) is one
station-profile sweep along a curved spine, not a vertex blend: march stations along the virtual sharp corner X (top
line x side tangent), keep the station normal in the deck plane, side = curve c3 u^3 + c4 u^4 (G2 to the blend). Smooth
the raw profile ROWS column by column, never the parameters one by one. Deck interior = own face cut on the sweep's top
edge. FreeCAD `approximate` can fail quietly on long uneven grids: check its deviation and fall back to `interpolate`.
Quarter 84.4 -> 85.9 % (vertices 88.3 -> 90.1 %).
Touch-ups (same day): resample every station at fixed arc distances from a STABLE anchor (nearest point to X) - columns
tied to jittery blend ends slide and an interpolated grid pinches; cut neighbouring faces on the grid face's real edge,
not a station polyline; give the neighbour face the sweep's flat band as tangent data.

### Roof: master surface + bands over the plan; a crisp-looking line as an exact G2 roll (2026-11-11, `roof_build.py`)
- Every roof face is a height field over the PLAN (s = z, t = x, h = y), so a trim curve is the same 2D curve in every
  face. Crown = ONE fair surface mapped from the rear line to the header (single span, deg 7 x 5, mirror-paired poles);
  a plan grid needs knots every ~140 mm and ripples. Judge fairness with isophote maps, not the vertex RMS: Kunos roof
  heights are lumpy (0.3-0.7 mm) and its half-model leaves a ~1.1 mm ridge on the centreline; the fair crown ignores both.
- Read a "soft" Kunos line from its rows, not its look: vertex normals are plain averages of the neighbouring facets,
  so a 10 deg turn between rows 25 mm apart SHADES as a ~45 mm roll. Build that as a roll, centred on the line.
- Roll between two height fields f (front) and g (back) across a curve R(x): parameters (u, x) with u = z - (R - b),
  width a + b constant, so z is linear in u and polynomial in x (exact in the x basis). Height = quintic Hermite in u
  through the value, d/dz and d2/dz2 of g at u = 0 and f at u = a + b, at constant x: G2 on both edges by construction
  (tangential derivatives follow from the matched values), no fitting to vertices at all. Bernstein form: b0 = p0,
  b1 = p0 + p0'/5, b2 = p0 + 2p0'/5 + p0''/20 (mirror for b3-b5), derivatives scaled by the width.
- Put the neighbours' own knots into the roll's along-line basis (triple knots for a cubic neighbour: its jets are
  only C2 there), but never a knot within a few mm of the roll's end (ill-posed, huge end poles).
- Where another line crosses (the side line), split the roll on it: each piece takes the face on its side as the front
  surface; they meet exactly because both front faces agree on the crossing line and share the back face; the
  crossing line's crease fades out across the roll.
- Cut the neighbours back with plan polygons on the exact edge at ~10 mm segments (1 mm segments: 4x the triangles,
  8 min to mesh one face). The FreeCAD stage takes a per-face `maxlen` for big gentle faces.
- Neighbours of a master surface are built ON its edges: every AE86 roof neighbour is a 2-4 mm Kunos return, so they
  are strip_build strips whose roof-side rail is the roof's built edge (nb_name = a name prefix covering every roof
  face). Two lessons: fit outline trim curves to the polyline resampled every 5 mm, also in special builders (the
  roof's drip edge wiggled +-2 mm between vertices 50 mm apart); where two built edges run side by side near a strip
  side, take only the one nearer the Kunos side, never a mix.
