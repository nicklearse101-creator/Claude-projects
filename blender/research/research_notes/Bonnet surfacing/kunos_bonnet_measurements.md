# Kunos ks_toyota_ae86 bonnet: measured description for a panel-by-panel replica

All numbers are measured directly from the game asset `content/cars/ks_toyota_ae86/toyota_ae86.kn5` (meshes GEO_hood_SUB1 skin, GEO_hood_SUB2 underside, GEO_hood_SUB0 washer nozzles, plus GEO_body, GEO_details and GEO_headlight* for gaps), loaded read-only with `panel_fit.load_mesh(..., raw=True)`. Units are mm, AC axes (x right, y up, z forward). Unless a side is named, the right half (x > 0) is quoted. The mesh is mirror-exact, so every number holds for the left half with x negated.

"Sources" below are the measuring scripts and their output pictures in `D:/ClaudeData/tmp/research_bonnet/kunos/`. Each finding can be re-run from the script named next to it. There are no web sources: the subject is one specific mesh.

Overall: the skin (SUB1) is 1026 vertices and 1934 triangles. It is 1261.6 wide (x ±630.8), runs z 717.4..1907.3 (1190 long) and y 638.0..875.0. It is ONE welded mesh: no duplicate vertices anywhere (0 vertices within 0.2 mm of another), and no open seams except the panel's cut edges (116 boundary edges, 0 non-manifold). So every vertex has ONE normal, even at the 98° rear fold. The crease split (20° dihedral) gives 28 regions: r0 is the main skin (1274 triangles, 1.296 m²), r1..r13 are the edge features, and r14..r27 are 1-6-triangle corner patches. Pictures: `bonnet_regions_iso.png`, `bonnet_regions_top.png`, `bonnet_regions_front_iso.png`, `bonnet_regions_nose_close.png`, `wire_top.png` (top-view wireframe, coloured by region), `dihedral_map_right.png` (edge dihedrals, right half).

## 1. The soft step lines (x ~ ±330..375 in r0)

### Takeaway
Each step line is a 7-row vertex band. Geometrically it is a STRAIGHT ramp (two coplanar facets between rows 3 and 5), not an S-curve. The centre panel is higher; the drop is 3.17 mm at the rear and fades linearly to 0 at the front (z ≈ 1720), where the line runs into the inner corner of the headlamp notch, in line with the tongue side wall. The soft S look comes only from plain angle-weighted vertex normals; no normals are bent here. At the rear the line turns outward through a ~80° corner (R ≈ 37-51 mm) into a tail that tapers to a point at (440.9, 859.6, 885.2).

### Cited Findings
- **Vertex structure.** The band has exactly 7 longitudinal vertex rows. They have vertices ONLY at the transverse stations z ≈ 1008, 1110, 1211, 1311, 1410, 1508, 1607, 1664, 1721 (≈100 mm pitch, 57 mm for the last two). Between stations the band is long thin triangles (≈100 mm × 2-7 mm), i.e. a ruled strip. Row offsets from the mid row (row 4), at z 1311: −13.7, −8.7, −6.5, 0, +6.5, +9.2, +14.2 mm. At z 1008 they are −12.8, −8.5, −6.3, 0, +6.3, +9.7, +15.3 [s10.py output `s10_out.txt`; rows walked by `rows.py`](D:/ClaudeData/tmp/research_bonnet/kunos/s10.py).
- **Which rows move.** Rows 1-3 lie exactly on the centre-panel surface and rows 5-7 exactly on the outer-panel surface: blend parameter t = 0.00, 0.00, 0.00, 0.53, 1.00, 1.00, 1.00 at every station. The mid row sits exactly halfway between rows 3 and 5. For example, y relative to the inner fit at z 1008 is −0.01, −1.69, −3.38 for rows 3, 4, 5. So the cross-section is flat → straight ramp → flat. The two creases (row 3 = upper, row 5 = lower) are sharp facet folds; there is no geometric radius. Rows 1-2 and 6-7 are support rows that confine the normal smoothing [s10.py](D:/ClaudeData/tmp/research_bonnet/kunos/s10.py); [step_cross_sections.png](D:/ClaudeData/tmp/research_bonnet/kunos/step_cross_sections.png).
- **Step height and ramp along the main run.** h is centre fit minus outer fit at the mid row, with fits along the transverse vertex row: an even quartic for the centre (rms 0.03-0.10) and a cubic for the outer (rms 0.001-0.007). Local tangent lines through rows 1-3 and 5-7 agree to ±0.03 mm.

  | z (mid row) | mid-row x | h (mm) | ramp width row3→row5 (mm) | ramp angle vs centre surface | slope break (centre − outer, along row) |
  |---|---|---|---|---|---|
  | 1008 | 336.6 | 3.17 | 12.6 | 15.0° | 1.83° |
  | 1110 | 341.0 | 3.15 | 13.0 | 14.4° | 1.79° |
  | 1211 | 345.4 | 3.11 | 13.4 | 13.8° | 1.86° |
  | 1311 | 349.2 | 2.53 | 13.1 | 11.6° | 1.40° |
  | 1410 | 353.1 | 1.93 | 12.7 | 9.3° | 1.28° |
  | 1508 | 356.3 | 1.31 | 11.1 | 7.1° | 0.72° |
  | 1607 | 359.4 | 0.63 | 9.5 | 4.1° | 0.55° |
  | 1664 | 358.4 | 0.26 | 6.2 | 2.8° | 0.50° |
  | 1721 | ~361.5 | ≈0 (rows within 0.2 mm in y, slope only) | — | — | — |

  50 mm spacing: the mesh has band vertices only at the stations above (≈100 mm apart). In between, the band is single long triangles, so the values midway are linear interpolations by construction: z ≈ 1059: h 3.16, ramp 12.8; 1160: 3.13 / 13.2; 1261: 2.82 / 13.3; 1360: 2.23 / 12.9; 1459: 1.62 / 11.9; 1557: 0.97 / 10.3; 1635: 0.45 / 7.8; 1692: ≈0.13 / ≈3 mm. The mesh does not contain finer detail.
  h is a plateau of 3.1-3.2 mm from z 1008 to 1211, then falls linearly at ≈0.6 mm per 100 mm to 0 at z ≈ 1720 [s10.py](D:/ClaudeData/tmp/research_bonnet/kunos/s10.py); [step_line_summary.png](D:/ClaudeData/tmp/research_bonnet/kunos/step_line_summary.png).
- **Plan curve of the main run.** The mid row is x(z) = −1.274e−5·z² + 0.07148·z + 277.48 (max residual 0.12 mm, z 1008-1607). Its heading is 2.6° outward-per-forward at z 1008 and 1.75° at z 1607. So the two lines are CLOSEST together at the rear (±336.6 at z 1008) and DIVERGE toward the front (±359.4 at z 1607), ending at x ≈ 358-362. That is the x of the tongue side wall (top edge x 362.6 at z 1733, tapering to 357.4 at z 1900). Crease polylines: upper crease (row 3) x = 330.4/334.5/338.7/342.7/346.7 at z 1008.6/1110.5/1212.5/1311.5/1410.7; lower crease (row 5) x = 342.9/347.5/352.1/355.8 at z 1008.1/1110.0/1212.0/1311.1. The full list is in `step_creases.json` [s18.py](D:/ClaudeData/tmp/research_bonnet/kunos/s18.py).
- **Front end.** Between z 1664 and 1721 the rows converge (offsets −11.0, −4.4, −2.4, 0, 3.8, 7.6, 14.8 at z 1664). They run into the inner corner of the headlamp notch, where the notch chamfer r12/r13 turns through a plan corner of R ≈ 9.3 mm (centre (371.9, 1733.9)). The step is ≈0 there. The line therefore ends ON the tongue wall line [s16.py zoom_front_end_wire.png](D:/ClaudeData/tmp/research_bonnet/kunos/zoom_front_end_wire.png); notch-corner circle fit in this session.
- **Rear end (the hook).** Below z ≈ 930 both creases turn outward. The upper crease follows (329.3, 924.5) → (334.9, 916.2) → (342.3, 909.9) → (352.7, 904.1) → (364.0, 900.2) → (383.9, 895.8) → (403.5, 892.1). The lower crease follows (339.3, 931.2) → (343.0, 922.4) → (348.4, 915.6) → (356.9, 909.6) → (366.3, 905.6) → (385.4, 900.1) → (403.8, 893.7). Circle fits to the corner points give R = 51.3 mm (upper; it is the outside of the bend, centre (373.2, 950.8)) and R = 37.0 mm (lower, centre (374.7, 941.7)), max error 0.3 mm. The total turn is ≈80° (heading changes from straight rearward to 100.7°, i.e. the tail runs ≈11° rearward of +x). The tail tapers to a single vertex at (440.9, 859.6, 885.2). The facet dihedral at the creases peaks at 24.8° in the corner (vs 15-18° on the main run), so the ramp is steepest there [s17.py, s18.py](D:/ClaudeData/tmp/research_bonnet/kunos/s18.py); [zoom_hook_wire.png / zoom_hook_shaded.png](D:/ClaudeData/tmp/research_bonnet/kunos/zoom_hook_shaded.png).
- **Step along the tail.** These come from the 6-7 rows across the tail, using local tangent lines: x ≈ 364.6 h ≈ 2.85 mm, ramp 5.4 mm; x ≈ 384.6 h ≈ 1.63 mm, ramp 4.3 mm; x ≈ 403.6 h ≈ 0.5 mm, ramp 3.1 mm; x = 440.9 h = 0 (tip). On the tail the higher side is the REAR side: the raised centre level wraps round the rear end of the outer panel. Vertex list from this session's tail dump; plotted in [step_line_summary.png](D:/ClaudeData/tmp/research_bonnet/kunos/step_line_summary.png).
- **Normals.** Stored normals match the angle-weighted average of incident facet normals: median deviation 0.03° on r0, p95 0.88°. Area-weighted (median 0.29°, p95 14°) and plain (median 0.10°, p95 2.6°) averages match worse [s11.py](D:/ClaudeData/tmp/research_bonnet/kunos/s11.py). Across the band, the lateral normal tilt at z 1110 is +0.92, +0.92, +7.98, +15.0, +8.92, +2.78, +2.71° for rows 1-7. The facet tilts are 0.91 (flat), 14.99 (both ramp facets) and 2.6-2.8 (outer). So rows 3 and 5 carry the half-way normal and row 4 the ramp normal: shading changes over rows 2→6 (≈18 mm) while the geometry ramps over rows 3→5 (≈13 mm). No band vertex has a bent normal (>1° off angle-weighted) except the hook tip (403.8, 861.0, 893.7): 3.0° [s12.py, s15.py](D:/ClaudeData/tmp/research_bonnet/kunos/s15.py).

### Inferences
- A faithful replica does not need an S-section surface. Kunos's shape is two offset panels joined by a ruled, near-planar ramp 13 mm wide, ≈15° to the centre panel at the rear and fading to 0. If a CAD-quality soft look is wanted, a proper G2 replica would be two fillets (convex at row 3, concave at row 5) with radii of order (ramp width)/tan(angle) ≈ 25-50 mm at the rear. That design choice is ours, not Kunos's; Kunos fakes the softness with normals alone.
- The ramp is the obvious candidate for the ruled-strip builder: two built edges (row 3 on the centre panel, row 5 on the outer panel) plus a straight ruling.
- The line's end at the notch corner, in line with the tongue wall (x ≈ 358-362), suggests the designer intent: the centre-panel boundary IS the tongue edge, continued rearward as a fading step.

### Gaps
- Transition widths are quantised by the 7 rows. Kunos's mesh cannot say what the real car's fillet radii are; only the ramp and the facet folds exist.
- Between stations (100 mm) the band is straight in plan by construction, so the plan curve's curvature is only known at the station vertices.

## 2. Centre panel vs outer panels: one surface with a step, or two surfaces?

### Takeaway
They are two different surfaces, not one surface plus an offset. Across the step the outer panel slopes away 1.8° more steeply at the rear (0.5° at the front). It is crowned more (transverse R ≈ 6.4-7 m near the side edge) than the almost flat centre panel (transverse R 10-35 m, slightly concave near the step). The gap between the outer surface and the centre surface extrapolated outward grows from 3.2 mm at the step to ≈14.7 mm at x = 560 (z 1008).

### Cited Findings
- Along each transverse vertex row, the outer fit minus the centre fit extrapolated, at x = mid-row / 420 / 500 / 560, is: z 1008: −3.17 / −6.09 / −10.12 / −14.67; z 1311: −2.53 / −4.23 / −7.00 / −10.61; z 1508: −1.31 / −1.84 / −2.70 / −4.47; z 1607: −0.63 / −1.20 / −2.02 / −2.79 [s10.py](D:/ClaudeData/tmp/research_bonnet/kunos/s10.py); [row_profiles_minus_inner.png](D:/ClaudeData/tmp/research_bonnet/kunos/row_profiles_minus_inner.png).
- Local slopes along the row right at the step (the rows' own tangent lines, no extrapolation): centre −0.84°, outer −2.37° at z 1008; −0.36° / −1.34° at z 1311; −0.44° / −1.01° at z 1607 [s10.py](D:/ClaudeData/tmp/research_bonnet/kunos/s10.py).
- Transverse radii of curvature (positive = crowned): centre panel at x = 0 / 150 / 300: 10.5 / 17.0 / −20.2 m (z 1008), 21.6 / 36.9 / −32.7 m (z 1410). Outer panel at x = 450 / 520 / 590: 36 / 11.4 / 6.8 m (z 1008), 68 / 12.8 / 7.1 m (z 1410). Both panels flatten toward the nose (z 1607: centre 29-92 m, outer 46-780 m) [s26.py](D:/ClaudeData/tmp/research_bonnet/kunos/s26.py).
- Longitudinally the two panels have similar slope progressions. Along columns, centre x = 0 goes −9.1° (z 1017) to −14.6° (z 1770); outer x = 497 goes −7.8° (z 996) to −12.8° (z 1714). The centre panel is 1.3-1.7° steeper at equal z [s23.py](D:/ClaudeData/tmp/research_bonnet/kunos/s23.py).
- Transverse vertex rows are bowed in plan: each row is ≈40 mm further forward at x = 0 than at x = ±630 (e.g. row through z 1017 at the centre is at z 977 at the side) [s9.py](D:/ClaudeData/tmp/research_bonnet/kunos/s9.py).
- Rear-zone observation: in the centre panel the slope changes by 2.5° across the row at z ≈ 1017 (−6.6° → −9.1°), against 1.2° in the outer panel. The zone behind it (z 863-1017, around the hook) is flatter (−6.3..−6.7°) [s23.py](D:/ClaudeData/tmp/research_bonnet/kunos/s23.py).

### Inferences
- Build three surfaces: the centre panel, which also carries the tongue and nose roll, plus two outer panels (mirror). Do not build one surface and push the outer part down. The step strip then joins two independently fitted edges.
- The rear zone behind the hook (z < ≈1017) may behave as its own band of surface (flatter, joining the cowl edge). Whether that 2.5° change is design or modelling noise cannot be separated from the lumpiness in section 6.

### Gaps
- The centre-panel extrapolation to x = 560 uses an even quartic fitted on x ≤ 337. The local slope break is robust; the far-out numbers are indicative only.

## 3. The nose roll on the tongue (|x| < 358, z > 1650)

### Takeaway
The roll is a constant section swept across x. Every column from x = 0 to 348 has the same slope sequence within 0.5°, and the front edge is curved in plan by only 6.3 mm over ±348 (plan R ≈ 9.6 m). It starts at z ≈ 1770 (−14.6°), tightens through R ≈ 500 → 390 → 113 → 126 → 72 mm, and ends in a STRAIGHT 40 mm face at −52.5° (z 1882 → 1907). That is followed by a 0.9 mm facet at −62.4°, a 1 mm chamfer (r11) and a 7 mm downward-facing under-lip (r4). The "vertical front face" in the brief is actually that −52.5° straight face plus the horizontal under-lip; nothing is vertical.

### Cited Findings
- Column x = 0, as vertex z / y / slope of the following segment: 1673.9 / 740.2 / −13.5°; 1732.9 / 726.1 / −14.4°; 1769.8 / 716.6 / −14.6°; 1799.0 / 709.0 / −17.3°; 1815.5 / 703.9 / −18.0°; 1835.2 / 697.5 / −21.0°; 1855.0 / 689.9 / −30.4°; 1868.5 / 681.9 / −38.0°; 1882.6 / 671.0 / −52.8°; 1894.4 / 655.4 / −52.3°; 1906.9 / 639.3 / −62.4°; 1907.3 / 638.5 (edge). Vertex circumradii: 497 (z 1799), 1799 (1815), 393 (1835), 113 (1855), 126 (1868), 72 (1882), straight (1894), 61 (1907, the 0.9 mm kink). Columns x = 89, 178, 263 and 348 repeat these to ±0.5° and ±25 mm in R. The roll's z positions shift back with the plan curve of the front edge: edge z 1907.3 at x = 0, 1906.6 at 89, 1905.8 at 178, 1903.4 at 263, 1901.0 at 348 [s21.py](D:/ClaudeData/tmp/research_bonnet/kunos/s21.py); [nose_roll_slopes.png](D:/ClaudeData/tmp/research_bonnet/kunos/nose_roll_slopes.png).
- The roll has 10 transverse vertex rows (z ≈ 1770, 1799, 1815, 1835, 1855, 1869, 1883, 1894, 1907, 1907.3), 15-21 mm apart; nose triangles have a median area of 674 mm² [s20.py, s26.py](D:/ClaudeData/tmp/research_bonnet/kunos/s26.py).
- From z 1770 to the edge the turn is −14.6° → −52.5° over ≈112 mm of arc: mean R ≈ 170 mm, but concentrated in z 1835-1883 (R 72-126) [s21.py](D:/ClaudeData/tmp/research_bonnet/kunos/s21.py).
- The edge goes r0 → r11 → r4. The r0|r11 dihedral is 58.2° and r11|r4 is 58.6°. r11 is 0.96-1.18 mm wide, with normal (0, −0.51, 0.86). r4 is 7.1-7.4 mm deep (7.4 at the centre, 7.1 at x = ±357), with normal (0, −1, 0.015), i.e. a horizontal lip under the nose [s14.py, s22.py](D:/ClaudeData/tmp/research_bonnet/kunos/s22.py).
- Tongue side walls r7/r8 are at x = 358.0..364.8, z 1729..1900, facing ±x (normal (1, 0.02, 0.05)). Their top edge (the r0|r13 line) runs x 362.6 (z 1733) → 361.1 (1796) → 359.7 (1847) → 358.0 (1889) → 357.4 (1900), so it tapers inward 5 mm. Wall height falls from 14.2 mm (z 1729) to 13.4 (1796), 12.3 (1862), 11.3 (1876) and 7.3 mm (z 1900). The wall meets the skin through the 1 mm notch chamfer r12/r13 (r0|r13 dihedral mean 36.4°, r13|r8 38.9°) [s22.py; notch dump in this session](D:/ClaudeData/tmp/research_bonnet/kunos/s22.py).
- Bent normals appear only on the tongue edge: at (361.1, 706.8, 1795.6) the stored normal is 6.6° off the angle-weighted normal, at (357.4, 639.3, 1900.3) 5.3°, at (360.5, 707.0, 1795.5) 3.1°, and at (360.8, 702.6, 1810.3) 2.8° [s12.py](D:/ClaudeData/tmp/research_bonnet/kunos/s12.py).

### Inferences
- The roll can be built as one profile curve (the column polyline above, resampled) swept along the slightly curved plan front edge. A G2 roll from −14.6° to −52.5°, R_min ≈ 70-110 mm, then a straight −52.5° flank, matches the vertices.
- The facets in the tight part sit well inside the true roll: chord sag L²/8R = 19.5²/(8×72) ≈ 0.66 mm and 15.7²/(8×113) ≈ 0.27 mm. A fitted replica should pass THROUGH the vertices, not through the facets.

### Gaps
- With 15-20 mm row spacing, radii below ≈30 mm cannot be resolved. The 61 mm "radius" at the edge is a 0.9 mm bevel facet, not a measured round.

## 4. The edge regions r1..r13

### Takeaway
Every edge feature is a thin strip (L/W 15-900). The pattern is: skin → (≈1 mm chamfer) → 7-15 mm return/flange. The chamfers are 1 mm wide and 29-58° to the skin. Because the mesh is welded with averaged normals, the outermost skin column (≈65 mm wide triangles) shades as a soft roll of up to 15-48° even though it is geometrically flat.

### Cited Findings

| region | what | width (mm) min/median/max | length (mm) | angle | thin strip (w<15, L>10w)? |
|---|---|---|---|---|---|
| r1 | rear flange (turn-down at cowl edge), normal (0, 0, −1) | 15.01 / 15.02 / 15.07 | 1311 (full width, curved in plan) | 97.7° to skin, directly (no chamfer) | yes (15.0, L/W 87, borderline on width) |
| r2/r3 | side returns, vertical, normal (±1, 0.025, 0.006) | 13.1 / 13.8 / 14.2 (14.1 at the ends, 13.1 at z 1377) | 1006 (z 717-1713) | 50.5° to chamfer; 82° to skin | yes (L/W 73) |
| r9/r10 | side chamfers, normal (±0.62, 0.78, 0.11) | 1.05 / 1.15 / 1.17 | 1006 | 29.4° to skin (28.7-37.9), 50.5° to return | yes (L/W ≈ 870) |
| r4 | nose under-lip, horizontal, facing down | 7.13 / 7.27 / 7.40 | 714 (x ±357) | 58.6° to r11; 123° to the last skin facet | yes (L/W 98) |
| r11 | nose chamfer, normal (0, −0.51, 0.86) | 0.96 / 0.96 / 1.18 | 715 | 58.2° to skin, 58.6° to r4 | yes (L/W ≈ 740) |
| r5/r6 | lamp-bay step faces (rear wall of the headlamp notch), normal (±0.05, 0.02, 1.0) | 14.05 / 14.06 / 14.15 | 258 (x 366-624, z 1714.5-1727.4; edge line runs back 10.8 mm over 250 mm = 2.5°) | 40.9° to chamfer; ≈76° to skin | yes (L/W 18) |
| r7/r8 | tongue side walls, normal (±1, 0.02, 0.05) | 7.3 / 13.4 / 14.2 (falls toward the nose, see section 3) | 197 (z 1729-1900) | 38.9° to chamfer (21.7-61.3); ≈84° to skin | yes (L/W 15) |
| r12/r13 | notch chamfer, L-shaped round the lamp-bay edge and tongue edge; plan corner R ≈ 9.3 mm | ≈0.95 (area 437 mm² / 460 mm) | 460 (258 + 197 + corner) | 36.4° to skin (24-46), 40.9° to r5/r6, 38.9° to r7/r8 | yes (L/W ≈ 480) |
| r14-r27 | 1-6-triangle corner patches where two chamfers or returns meet (e.g. r14/15 at (±624..627, 1712..1715), r16/17 at (±365..366, 1727..1729), r18/19 at the rear-flange/side-return corners) | < 3 | < 15 | — | corner fills, not strips |

Sources: [s14.py](D:/ClaudeData/tmp/research_bonnet/kunos/s14.py) (areas, shared-edge lengths, dihedrals); [s22.py](D:/ClaudeData/tmp/research_bonnet/kunos/s22.py) (chain-to-chain widths). r13's chain width in s22 is wrong because it is L-shaped, so the area/length figure is used.

- Plan of the side edge (top of the side chamfer): x 628.4 (z 800), 630.4 (1000), 630.0 (1200), 629.4 (1400), 629.0 (1600), 627.6 (1690). It is a slight plan bow of ≈2.8 mm [s29.py](D:/ClaudeData/tmp/research_bonnet/kunos/s29.py).
- Plan of the rear edge (top of r1): z 863.2 (x = 0), 853.4 (200), 821.0 (400), 736.8 (600), 717.4 (630). It is not a circle: a circle through the centre and corner would put x = 400 at 806, not 821 [s29.py](D:/ClaudeData/tmp/research_bonnet/kunos/s29.py).
- Normals at the edges. The stored normal at the skin's border vertices is tilted from the adjacent skin facets by 14.8° (side, r0|r10), 48.4° (rear, r0|r1), 29.1° (nose, r0|r11) and 18.2° (notch, r0|r13). The chamfer|return vertices are tilted 25.4° from the return facets. The adjacent skin column spans x ≈ 563 → 629 (≈65 mm), so its shading fades from flat to a 15° tilt across 65 mm [s34 inline run, this session; method as s11.py](D:/ClaudeData/tmp/research_bonnet/kunos/s11.py).

### Inferences
- All of r1, r2/r3, r4, r5/r6, r7/r8, r9/r10, r11 and r12/r13 qualify for the ruled-strip builder between built edges. The 1 mm chamfers in particular are pure rulings between the skin's border curve and the return's top curve.
- A replica with true geometric chamfers and split normals will look crisper at the edges than Kunos's. Kunos's 65 mm-wide soft shading comes from the welded averaged normals, not from the shape. If the in-game look must match, either build a real small fillet (≈ 5-15 mm) or keep the edge welded and smooth-shaded the same way.

### Gaps
- The kn5 holds no smoothing-group or bevel metadata, so whether the 1 mm chamfers were modelled or are a bevel modifier result cannot be told.

## 5. Symmetry

### Takeaway
Mirror-exact about x = 0 for all three meshes.

### Cited Findings
- SUB1: every mirrored vertex lands on a vertex within 0.0001 mm (point-to-surface max 0.0001 mm); 28 vertices are on the axis. SUB2: max 0.0000 mm, 6 on-axis vertices. SUB0: max 0.0000 mm (two separate nozzles at ±235.5) [s30.py](D:/ClaudeData/tmp/research_bonnet/kunos/s30.py).

### Inferences
- Build the right half and mirror it. The centre column of vertices is at x = 0, so the centre panel needs a symmetric (even-in-x) surface or a mirrored half with G1/G2 continuity at x = 0.

### Gaps
- None.

## 6. Facet sag, triangle sizes, and lumpiness

### Takeaway
The skin is coarse: centre-panel triangles have ≈89 mm legs, outer ≈79 mm, nose ≈37 mm. The OUTER panels are fair (column residuals rms 0.03-0.04 mm). The CENTRE panel, and the step band with it, is LUMPY lengthwise: whole transverse rows alternate +0.6 / −0.6 mm against a smooth cubic at 100 mm pitch, the same pattern at every x from 0 to ≈365 mm. The amplitude dies out to ±0.3 at x ≈ 430 and ±0.1-0.2 at x ≥ 500. This is the same order as the roof's 0.3-0.7 mm lumps.

### Cited Findings
- **Column residuals** from a cubic in z over stations z 1008..1664: x = 0, 89, 177, 257, 337-364 give [0.06, −0.07, −0.28, +0.62, −0.60, +0.56, −0.57, +0.27] (rms 0.42-0.45); x ≈ 430: rms 0.26; x ≈ 500: rms 0.18; x ≈ 563: rms 0.16 [s25.py](D:/ClaudeData/tmp/research_bonnet/kunos/s25.py); [lumpiness_columns.png](D:/ClaudeData/tmp/research_bonnet/kunos/lumpiness_columns.png).
- **Per-column fits.** Over z 1017-1733 (9 vertices), a cubic fit gives rms 0.43 mm, max 0.65 and leave-one-out rms 0.75 for centre columns x = 0..248. Over z 1098-1720 (10 vertices), the outer columns give rms 0.026 (x 497) and 0.042 (x 562), with LOO 0.05-0.07 [s24.py](D:/ClaudeData/tmp/research_bonnet/kunos/s24.py).
- **Segment slopes** along the centre column x = 0 zig-zag: −9.14, −9.02, −9.82, −9.07, −11.08, −10.72, −13.02, −13.47°. Along x = 497 they fall steadily: −7.84, −8.49, −8.53, −8.89, −9.71, −10.71, −11.79, −12.82° [s23.py](D:/ClaudeData/tmp/research_bonnet/kunos/s23.py).
- **Step height is not affected.** The step's own h(z) is smooth (plateau, then linear), so rows 1-7 of the band move up and down together with the centre panel's rows [s10.py](D:/ClaudeData/tmp/research_bonnet/kunos/s10.py).
- **Transverse fairness.** Within a row the centre fit (even quartic, 3 terms) has rms 0.03-0.10 mm and the outer cubic 0.001-0.007 mm [s10.py](D:/ClaudeData/tmp/research_bonnet/kunos/s10.py).
- **Triangle sizes.** Median areas: centre 3975 mm² (≈89 mm legs, edges median 100 mm), outer 3091 mm² (≈79 mm legs, edges median 83 mm), nose roll 674 mm² (≈37 mm). Band triangles are ≈100 × 2-7 mm [s26.py](D:/ClaudeData/tmp/research_bonnet/kunos/s26.py).
- **Chord sag implied by the vertex normals** (arc through each edge's end normals): centre panel median 0.11, p90 0.28, max 0.38 mm; outer panels median 0.14, p90 0.41, max 0.70 mm. The longitudinal curvature alone (R ≈ 8 m along z) gives ≈0.15 mm on a 100 mm chord. In the nose roll the sag reaches 0.3-0.7 mm on the R 72-126 mm rows (see section 3). The normal-based numbers for the band and creases are not meaningful (they span folds) [s26.py](D:/ClaudeData/tmp/research_bonnet/kunos/s26.py).
- **Shading pictures** with the stored normals vs flat facets: [shade_vnormals_top_lowsun.png](D:/ClaudeData/tmp/research_bonnet/kunos/shade_vnormals_top_lowsun.png), [shade_facets_top_lowsun.png](D:/ClaudeData/tmp/research_bonnet/kunos/shade_facets_top_lowsun.png), and the `_iso` pair.

### Inferences
- When fitting the centre panel, smooth lengthwise. Do not interpolate the row heights, or the ±0.6 mm washboard will be copied. A least-squares surface with 4-5 spans along z, scored with tolerance ≈0.6 mm on the centre panel and ≈0.1 mm on the outer panels, matches what the data can support.
- Score replicas against VERTICES, not against facet samples. The facets sit 0.1-0.4 mm (panels) and 0.3-0.7 mm (nose roll) inside the smooth surface the vertices describe.

### Gaps
- Whether the centre-panel washboard is Kunos editing noise or a real feature cannot be proven from the mesh alone. Its exact 100 mm row pitch and the same amplitude at every x strongly suggest modelling noise.

## 7. Underside SUB2 and nozzles SUB0

### Takeaway
SUB2 is a coarse inner skin (200 vertices, 290 triangles, 1.286 m²). Its perimeter coincides with the skin's cut edges; a rim loop runs exactly 10.0 mm inside the skin (normal offset, 15 mm vertically); the middle is a few sparse vertices 19-30 mm under the skin. It is not a detailed offset surface. SUB0 is two 18.6 × 13.1 × 19.2 mm washer nozzles sitting on the skin at x = ±235.5, z ≈ 966.

### Cited Findings
- 108 SUB2 vertices lie on the skin (distance < 1 mm): these are the shared bottom edges of the returns, flanges and lip. 88 vertices are 6-12 mm from the skin: the rim loop, at exactly 10.0 mm 3D distance (9.0-10.2), ≈15 mm vertically. The loop runs along the rear (y 844-858, z 735-873), the sides (x ≈ 618-621), the notch (z 1706-1716), the tongue (x ≈ 349-361) and the nose (z ≈ 1886-1890). 4 vertices are 12-30 mm away: centre (0, 781.3, 1299.4) 29.6 mm below the skin; (0, 710.9, 1716.0) 19.2 mm; (±348.8, 710.9, 1716.0) 16.1 mm. SUB2's mean normal is (0, −0.983, −0.185), i.e. facing down. Mirror-exact [s30.py, s31.py](D:/ClaudeData/tmp/research_bonnet/kunos/s31.py).
- SUB0, each nozzle: 118 vertices, bbox x 225.7..244.3, y 858.7..871.9, z 954.7..973.9 (size 18.6 × 13.1 × 19.2 mm), centre (±235.5, 864.2, 966.2). The closest nozzle vertex is 0.13 mm from the skin, so it sits on the skin [s30.py](D:/ClaudeData/tmp/research_bonnet/kunos/s30.py).

### Inferences
- For the replica's underside, a 10 mm inward normal offset of the skin's border, plus a flat-ish inner panel, reproduces SUB2. It has no styling content.

### Gaps
- SUB2's interior was not surveyed triangle by triangle (only 4 interior vertices exist, so there is little to survey).

## 8. How the bonnet meets the body

### Takeaway
- **Sides:** a tight shut line. The horizontal gap from the bonnet's side-return face to the wing's inner edge narrows from 3.0 mm (rear) to 0.7-1.0 mm (front). The wing top sits 0.1-2.7 mm below the bonnet edge.
- **Rear:** no shut line to the windscreen. The bonnet's rear edge stops 30-38 mm short of the cowl/scuttle top (GEO_details), and the windscreen glass base is 54-67 mm behind it.
- **Front:** the nose under-lip rests 0.2 mm on GEO_details.
- **Notch:** the notch faces are 0.1-1.6 mm from the pop-up headlamp units, and the notch top edge is 1.2-3.5 mm from the lamp lids (GEO_headlight*_SUB2).

### Cited Findings
- **Side gap.** Sections at constant z give the bonnet return outer face x and the wing (GEO_body) innermost point within 30 mm below the bonnet top:

  | z | bonnet return face x | wing edge x | wing edge y | gap (mm) |
  |---|---|---|---|---|
  | 800 | 629.6 | 632.6 | 850.3 | 3.0 |
  | 1000 | 630.7 | 632.9 | 832.1 | 2.2 |
  | 1200 | 630.3 | 632.0 | 804.0 | 1.7 |
  | 1400 | 629.8 | 631.0 | 773.0 | 1.2 |
  | 1600 | 629.3 | 630.0 | 736.8 | 0.7 |
  | 1690 | 628.0 | 629.0 | — | 1.0 |

  The wing top surface just outboard (x 634-640) is at y 852.6 vs bonnet top edge 854.4 (z 800), 834.4 vs 834.5 (z 1000), 806.2 vs 807.1 (z 1200), 775.3 vs 777.1 (z 1400), 739.0 vs 741.4 (z 1600), 720.5 vs 723.2 (z 1690). The 3D distance from the bonnet top-edge line to GEO_body is 2.9-4.1 mm (median 3.1) [s28.py, s29.py](D:/ClaudeData/tmp/research_bonnet/kunos/s29.py).
- **Rear.** Sections at constant x: bonnet rear edge z 863.2 / 853.4 / 821.0 / 736.8 at x = 0 / 200 / 400 / 600; flange y 860..875 at x = 0. The nearest GEO_details (cowl) point to the bonnet's top-rear corner is 38.0 / 32.3 / 32.3 / 30.2 mm away. The windscreen (GEO_glasses) is 67 / 65 / 61 / 54 mm away (glass base at z 797.1 / 788.7 / 760.7 / 683.6). The rear flange's open edge is 4-21 mm from GEO_details (median 16) [s28.py, s29.py](D:/ClaudeData/tmp/research_bonnet/kunos/s29.py).
- **Front and notch** (exact point-to-triangle distances): r4 under-lip open edge → GEO_details 0.2 mm; r11 nose chamfer top edge → GEO_details 0.7 mm; r6 lamp-bay face open edge → GEO_headlightL_SUB1 0.5-1.5 mm (GEO_details 0.2 mm at x 618); r8 tongue wall open edge → GEO_headlightL_SUB1 0.1-1.6 mm (median 0.3); notch top edge (r0|r13) → GEO_headlightL_SUB2 1.2-3.5 mm (median 1.9). GEO_headlightL/R_SUB2 (the pop-up lid) spans x ±359..627, y 630..724, z 1716..1901, filling the notch [s27.py, s28.py](D:/ClaudeData/tmp/research_bonnet/kunos/s28.py).

### Inferences
- The replica's side edge must stay within ≈0.7-3 mm of the wing. A tapered gap (wider at the rear) is what Kunos has. The rear edge is free (30+ mm clearance), so the rear flange shape is not constrained by neighbours.
- The notch outline must follow the pop-up lid within ≈1-3 mm.

### Gaps
- The kn5 "L" headlamp meshes are at +x. I kept Kunos's names and did not resolve which side of the real car that is.

## Pictures (all in D:/ClaudeData/tmp/research_bonnet/kunos/)
- `bonnet_regions_iso.png`, `bonnet_regions_top.png`, `bonnet_regions_front_iso.png`, `bonnet_regions_nose_close.png`: crease regions coloured.
- `wire_top.png`: top-view wireframe (1 px = 1 mm), coloured by region.
- `dihedral_map_right.png`: right half, edges coloured by dihedral.
- `shade_vnormals_*.png` vs `shade_facets_*.png`: what the stored normals do.
- `step_line_summary.png`: plan of the creases, h(z), ramp width and slope break, and the hook tail.
- `step_cross_sections.png`: the 7-row band sections at all stations.
- `row_profiles_minus_inner.png`: whole transverse rows minus the centre fit.
- `probe_sections.png`: early facet sections.
- `zoom_hook_wire.png`, `zoom_hook_shaded.png`, `zoom_front_end_wire.png`, `zoom_front_end_shaded.png`.
- `nose_roll_slopes.png`, `lumpiness_columns.png`.
