# Vanishing soft step on a bonnet: local experiments (FreeCAD 1.1.4 / OCCT 7.8.1, numpy/scipy)

All numbers come from local runs on Nik's PC, 2026-11-11. Scripts, logs, BREPs and a zebra image are in `D:\ClaudeData\tmp\research_bonnet\`:
- `geom.py`: test geometry and B-spline helpers.
- `blend.py`: approach (a).
- `a_run.py` / `a_run2.py` / `a_occ.py`: approach (a) runs, with logs `a_run.txt`, `a_run2.txt`, `a_occ.txt`.
- `b_fit.py`: approach (b), log `b_fit_final.txt`.
- `c_fill.py`: OCCT MakeFilling test, log `c_fill.txt`.
- `zebra.py`: renders `zebra_a.png`.

**Test geometry (synthetic and exact).**
- Units are mm. x runs along the car (0 is the front edge, 1000 the rear) and y runs across the car.
- Outer panel: zo = 700 + 0.10x − 6e-5x² + 1.5e-8x³ − 2e-4y² − 1e-10y⁴ + 4e-8xy². This is a polynomial of total degree 4, so it is stored exactly as a degree-5 Bezier. Its crown radius is about 2.5 m across and 8 m along.
- Centre panel: zc = zo + H(x).
  - **Case A**: H falls linearly from 1.7 mm at x 40 to 1.2 mm at x 900.
  - **Case Z**: H is 1.7 mm up to x 650. It then follows a quintic smoothstep down to 0 at x 900, so H, H′ and H″ are all 0 at x 900. As a B-spline in x this is exact with triple knots at x 650 and x 900.
- Step line: a degree-5 B-spline in plan view, 914 mm long.
  - At the front it starts with a hook (minimum radius 154 mm), then converges and ends heading +x at (900, 182).
  - A "tight" variant has a 27 mm minimum radius.
- Width law: w falls linearly from 15 mm to 10 mm along the line. Variants: a constant 12 mm, and width shrinking to 0.
- Join metrics:
  - G0 gap.
  - Maximum normal angle.
  - Normal-curvature jump |Δκ| across the edge, along it, and at 45°.
  - The metrics are computed analytically with numpy and cross-checked in OCC with the roof project's `common.continuity` (Surface.parameter + getDN).

---

## Q1. Which method gives G2 on both sides, exact joins (<0.01 mm), clean isophotes and a clean vanishing end?

### Takeaway
Approach (a) was the only method that met every target, by orders of magnitude:
- G0 below 0.001 µm, normals within 0.0001°, curvature jump about 1e-7 /mm (against about 0.07 /mm of curvature inside the blend).
- The faces sew into one valid shell.
- At a height-to-zero end it turns into the outer panel exactly, with no extra topology.

Approach (b), a single fitted height field, is not G2-faithful at any affordable pole count: 0.7–3° normal error and 8–65 µm height error at 3–5 mm knots, with ringing on the flat panels. OCCT's MakeFilling (Surface::Filling with G2 constraints) on the full strip kept G0 but missed tangency by a median of 7.7°.

### Cited Findings

**(a) Construction**
- The surface is parametrised by s (arclength along the line) and t (0 to 1 across the step).
- Plan map: P(s,t) = A(s) + t·(B(s) − A(s)). A and B are the ±w/2 plan offsets of the line, fitted as degree-5 B-splines in s with shared knots.
- Height: a quintic Hermite in t, written as Bernstein coefficients [p0, p0+q0/5, p0+2q0/5+r0/20, p1−2q1/5+r1/20, p1−q1/5, p1]. p, q and r are the value, D·∇z and Dᵀ(∇²z)D of zc at A and of zo at B, with D = B − A taken from the *fitted* A and B.
- The six coefficients are least-squares fitted in the same s basis. The result is 6 × n poles, degree 5 × 5.
- This is the roof `rear_roll` recipe, extended with variable width and a plan curve — [blend.py](file:///D:/ClaudeData/tmp/research_bonnet/blend.py)

**(a) Case A (1.7 → 1.2 mm, w 15 → 10)** — [a_run.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run.txt)

| Spans in s (knots) | Poles | Centre-side join | Outer-side join |
|---|---|---|---|
| 8 uniform | 6×13 | G0 1.5 µm, 0.023° | G0 2.6 µm, 0.036°, Δκ along 7e-5 /mm |
| 16 uniform | 6×21 | G0 0.13 µm, 0.0033° | G0 0.25 µm, 0.0059° |
| 32 uniform | 6×37 | G0 0.001 µm, 0.00006°, Δκ cross 2e-9, along 3.6e-7 /mm | G0 0.003 µm, 0.0001° |
| 16 curvature-adapted | 6×21 | G0 0.003 µm, 0.00007° | G0 0.004 µm, 0.00013° |

- Inside the blend, the maximum cross curvature is 0.067 /mm (radius about 15 mm). The maximum slope relative to the outer panel is 12.5°.

**(a) Case Z (vanishing end), with the centre panel's knot lines carried into s** — [a_run2.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run2.txt)
- The centre panel has knot lines at x 650 and x 900. These were added as triple knots at the s values where A crosses them.
- 32 adapted spans (6×40 poles):
  - Centre join: G0 below 0.001 µm, 0.00005°, Δκ at most 3e-7 /mm.
  - End edge (s = L, x 900) against the outer panel: G0 below 0.001 µm, 0.00001°, Δκ 4e-8 /mm.

**OCC-native check** — [a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt)
- The numpy evaluation and the OCC BSplineSurface agree to 7e-13 mm.
- `common.continuity` on the trimmed faces:
  - Case A, both joins: G0 0.0000 µm, 0.000001°, Δκ about 1e-8 /mm.
  - Case Z, centre join: G0 0.0003 µm, 0.00003°, Δκ 1.8e-7 /mm.
- `sewShape(1e-4)` gives one valid shell of 3 faces. Only the 9 outer boundary edges are free, and the maximum tolerance is 1.8e-6 mm (A) or 1.8e-4 mm (Z).

**G1-only comparison** — [a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt); [zebra_a.png](file:///D:/ClaudeData/tmp/research_bonnet/zebra_a.png)
- A cubic Hermite in the same frame (value and slope only) gives a curvature jump of 0.072–0.080 /mm at both joins. That is the full blend curvature, against about 1e-7 /mm for the G2 version.
- In the zebra image:
  - G2 stripes curve into the join lines tangentially.
  - G1 stripes hit the joins bluntly.
  - The G2 vanishing end closes in smooth nested loops.

**(b) One height field (u = x, v = y)** — [b_fit_final.txt](file:///D:/ClaudeData/tmp/research_bonnet/b_fit_final.txt)
- Least-squares fit on a 1 mm or 0.5 mm grid of a smoothstep step over the plan distance (case Z), domain 1000 × 400 mm.

| Fit | Poles | Max height error | Max normal error in the step band | On the "flat" panels |
|---|---|---|---|---|
| Degree 5, 20 mm knots | 1,375 | 542 µm | 11.2° | — |
| Degree 5, 5 mm knots | 17,425 | 65 µm | 2.9° | ringing up to 43 µm, normal error 1.4° |
| Degree 5, 3 mm knots | 46,644 | 8 µm | 0.68° | flat normal error 0.38° |
| Degree 3, 3 mm knots | 45,696 | 11 µm | 0.89° | — |
| Clustered knots, 2 mm in the line band | 16,740 | 18.5 µm | about 1.0° | about 1.0° |

- Fairing (second-derivative penalty, λ = 100) cuts the flat-panel normal error to 0.6°. It also blurs the step: height error 238 µm and normal error 6.1° in the band.
- OCC `BSplineSurface.approximate` (tolerance 0.05, 301 × 301 points over a 300 mm patch) took 1.4 s, produced 65 × 63 poles, and was 34 µm off between the grid points.

**(c) OCCT MakeFilling (Surface::Filling, i.e. BRepFill_Filling / GeomPlate)** — [c_fill.txt](file:///D:/ClaudeData/tmp/research_bonnet/c_fill.txt)
- Set-up: case Z, A edge on the centre face and B edge on the outer face, both with order G2, and straight C0 cross edges at the ends. The strip is 906–924 mm long and 10–15 mm wide.
- Results:
  - Run time 0.0–0.1 s, giving a degree-8 surface of 23 × 23 poles (44 × 44 when tuned).
  - G0 0.7–5 µm.
  - Normals 6.3–9.2° off along the first 80 % of the edge (median 7.7°). Only near the vanishing end, where there is no step left, do they fall to 0.1–0.9°.
  - Δκ is about the curvature itself (6e-3 /mm).
- Order G1 did worse: G0 1.4–1.7 mm, median normal error 0.84° (maximum 7.2°).
- Tuning (PointsOnCurve 60, Iterations 4, MaximumSegments 40, MaximumDegree 8) changed nothing.

### Inferences
- (a) is exact because the plan map is shared exactly: A(s) is both the blend's t = 0 plan curve and the trim curve on the centre height field. Matching z, ∂t z and ∂tt z along that curve therefore gives the full 2-jet match, i.e. G2. The only remaining error is the 1-D least-squares fit in s, which converges like h⁶.
- (b) has to resolve a 10–15 mm feature with a tensor grid that cannot follow a curved line. The pole count explodes (17–47 k poles for about 1 mm²-level fidelity in only a 1000 × 400 patch), and the result rings. It is not usable for a crisp soft step.
- MakeFilling gave a G1 error of 6–9° on this 1:70 strip, with G2 order doing worse than G1. That suggests the plate ignores or mis-weights the tangency constraints on long thin strips. It is not a replacement for (a) in this pipeline. See the Gaps for whether shorter segments would behave better.

### Gaps
- Variable-radius fillet (BRepFilletAPI), GeomFill Coons/Curved/Stretch, Surface Sections and the CurvesWB Blend Surface / Gordon tools were **not tested** — the coordinator limited this to one OCCT tool.
  - From reading the CurvesWB source: its BlendSurface samples N cross-section blend curves (G-continuity per curve) and interpolates them into a Gordon surface. So its continuity is exact only at the sampled sections — [blend_curve.py](file:///D:/ClaudeData/FreeCAD/Mod/CurvesWB/freecad/Curves/blend_curve.py). This was not measured.
  - Fillets are circular, so G1 only, but this was not measured here.
- MakeFilling was tried only on the full strip. Short segments (50–100 mm), or a plate seeded with an initial surface, were not tried.
- The (b) truth function is a smoothstep over the plan distance, not the identical (a) composite. The "flat" error zones also include the edges of the fit domain.

---

## Q2. What happens as the height goes to 0, and how do you end a feature cleanly?

### Takeaway
**Make the step vanish by height, never by width.** Define the centre panel as outer + H, where H has a triple zero (H = H′ = H″ = 0) on the end cross-section, and carry H's knot lines into the blend as triple knots. The Hermite blend then reproduces the outer surface exactly at the end:
- no sliver faces;
- no degenerate edge;
- G2 across the end edge.

Shrinking the width to 0 instead creates a collapsed edge and exploding curvature. With finite height it produces a vertical crease.

### Cited Findings

**Height → 0, finite width (case Z, 32 adapted spans with carried knots)** — [a_run2.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run2.txt)
- End edge against the outer panel: G0 below 0.001 µm, 0.00001°, Δκ 4e-8 /mm.
- The zebra loops close smoothly — [zebra_a.png](file:///D:/ClaudeData/tmp/research_bonnet/zebra_a.png)

**Without carrying the x 650 / 900 knots (same 32 adapted spans)** — [a_run2.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run2.txt)
- Centre join: G0 2.9 µm, 0.037°, Δκ along 1.8e-4 /mm.
- End edge: G0 1.0 µm, 0.037°.
- At 8 spans: 31–44 µm and 0.2–0.47°.

**Width → 0 over the last 150 mm with a smooth law (case Z)** — [a_run2.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run2.txt)
- Minimum area element 2e-3 mm²; maximum cross curvature 13 /mm.
- The offset fit error (29 µm) becomes comparable to the remaining width (0.2 mm at L−20, 0.02 mm at L−5).
- The outer join degrades to 0.5° and Δκ 15 /mm.

**Width → 0 with the height staying 1.2 mm (case A)** — [a_run2.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run2.txt)
- Slope 44° at L−50, 85° at L−20, 89° at L−5 (93.5° maximum).
- Cross curvature 54 /mm at L−20, 995 /mm at L−5, 1,540 /mm maximum.
- In effect, a crease or wall.

**Linear (C0-kinked) width law to 0** — [a_run.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run.txt)
- Outer join 1.47°; the cross-derivative |St| was still 0.136 mm at the end point instead of 0.

### Inferences
- **Clean run-out recipe**:
  1. Choose the end cross-section (here x = 900, perpendicular to the line's end tangent).
  2. Make H(ξ) a C2 smoothstep to 0 there, so the centre panel osculates the outer panel along that cross-section.
  3. Let the centre face beyond the end be the same surface as the outer (zc ≡ zo there).
  4. Keep the width finite all the way to the end.

  Topologically, the end is just one more G2 edge between the blend's s = L iso-curve and the outer face.
- **If the step must keep a finite height (1.2 mm) at an end**, the line has to leave the panel at a boundary (shut line, bonnet edge). It cannot stop mid-panel without a corner patch.
- **For fitted (Kunos-derived) panels**: fit the outer panel, then fit the centre as outer + δ(x, y) with δ forced to a triple zero at the run-out. Do not fit two independent surfaces and hope they meet.

### Gaps
- Run-outs where the end cross-section is not perpendicular to the line, or where H vanishes along a curve rather than a straight line, were not tested.

---

## Q3. Pitfalls: knot spacing, fairing, hooked or crossing lines, meshing thin blends

### Takeaway
1. **Carry every neighbour knot line** that the blend edges cross into s as triple knots (degree 5 gives C2). Leaving them out costs about 100× in accuracy.
2. **Curvature-adapted knots** in s halve the spans needed.
3. The **plan offsets only fold** if the line radius drops below w/2 on the concave side. This did not happen at 27 mm radius.
4. **Mefisto meshing (MaxLength) produces slivers** on 10–15 mm blends and crashed on the trimmed shell. **BRepMesh with deflection** is fast and well shaped.

### Cited Findings

**Knot spacing** — [a_run.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run.txt), [a_run2.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run2.txt)
- Uniform knots over the 914 mm line:

  | Spans | Offset fit error | G1 |
  |---|---|---|
  | 8 | 174 µm | 0.036° |
  | 16 | 10 µm | 0.006° |
  | 32 | 0.08 µm | 0.0001° |

- A sqrt-curvature knot density (`adapt = 2`) reaches the 32-uniform accuracy at 16 spans.
- Carrying the neighbour's knots changed case Z at 32 adapted spans from G0 2.9 µm / 0.037° to below 0.001 µm / 0.00005°.

**Hooked lines** — [a_run.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run.txt)
- Hook radius 154 mm and tight radius 27 mm, with w 15 → 10: the minimum plan-map Jacobian was 9.9 (it equals the local width, so there is no fold). No accuracy loss: G1 0.0001° at 32 spans.

**Fairing (b)** — [b_fit_final.txt](file:///D:/ClaudeData/tmp/research_bonnet/b_fit_final.txt)
- Raising λ from 1e-2 to 1e2 trades flat-panel normal error (1.4° → 0.6°) for step fidelity (65 µm → 238 µm in the band).

**Meshing, blend face (case A; case Z similar)** — [a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt)

| Mesher and settings | Triangles | Time | Aspect p95 / max | Longest edge | Facet-normal error vs exact (p95 / max) |
|---|---|---|---|---|---|
| BRepMesh LinearDeflection 0.01, Angular 0.1 | 25.6k | 0.30 s | 3.0 / 19 | 24 mm | 0.72° / 2.3° |
| BRepMesh 0.05 / 0.2 | 3.6k | 0.04 s | 5.5 / 22 | 46 mm | 1.7° / 4.7–6.6° |
| Mefisto MaxLength 6 | 1,755 | 0.8 s | **168 / 3,653** | — | **max 54°** |
| Mefisto MaxLength 2 | 7.5k | **11 s** | 12.5 / 39 | — | max 2.4° |

- Scaling the blend's U parameter range from 1 to 12.5 made no difference to Mefisto.
- On the whole trimmed shell, Mefisto logged "MEFISTO_2D failed … COMPERR_EXCEPTION" on 3 sub-shapes and FreeCAD then died with "Not enough memory available".
- With BRepMesh, the whole 3-face shell at deflection 0.01 gave 35.6k triangles in 0.44 s.

**Face building** — [a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt)
- `Part.Face(surface, wire_of_3D_edges)` returned invalid faces until `face.validate()` was called; afterwards they were valid and sewed cleanly.

### Inferences
- The pipeline's default `PF_MAXLEN = 6` Mefisto meshing (see `panel_fit_freecad.py`) should not be used on blend or step faces. Use BRepMesh deflection meshing there, or Mefisto with MaxLength ≤ w/6.
- **Crossing or merging lines** (for example two step lines meeting at a V) cannot be handled by one (s, t) patch. They need splitting plus a corner or N-sided patch. This was not tested.

### Gaps
- Mesh watertightness across the shared edges was not isolated: the whole-shell BRepMesh mesh had 183 open edges, which is consistent with the outer boundary only, but this was not verified edge by edge.
- The fold threshold (radius < w/2) was not reached with the tested lines; it is stated from offset-curve geometry, not measured.
- Crossing lines were not tested.

---

## Q4. Runtime of each approach

### Takeaway
All approaches are sub-second except Mefisto meshing:
- **(a)**: tens of milliseconds to build and about 0.3 s to verify.
- **(b)**: 0.01–0.4 s per least-squares fit, but 17–47 k poles.
- **MakeFilling**: about 0.1 s, but wrong tangency.

### Cited Findings

**(a)** — [a_run.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_run.txt), [a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt)
- Numpy build: 10 ms (8 spans), 25 ms (32 spans), 50–60 ms (64 spans), 130–150 ms (128 spans).
- OCC BSplineSurface: 1.6 ms. Trimmed faces: 45–84 ms. `sewShape`: 2–12 ms.
- `common.continuity` (101 samples): about 0.3 s per edge.

**(b)** — [b_fit_final.txt](file:///D:/ClaudeData/tmp/research_bonnet/b_fit_final.txt)
- Separable grid least-squares fit: below 0.01 s at 20 mm knots, 0.14 s at 5 mm (401 k points), 0.37 s at 3 mm (1.6 M points).
- OCC `approximate`: 1.4 s for 301 × 301 points.

**MakeFilling** — [c_fill.txt](file:///D:/ClaudeData/tmp/research_bonnet/c_fill.txt)
- 0.0–0.1 s per recompute.

**Meshing** — [a_occ.txt](file:///D:/ClaudeData/tmp/research_bonnet/a_occ.txt)
- BRepMesh: 0.04–0.44 s. Mefisto: 0.8 s (MaxLength 6) and 11 s (MaxLength 2) per blend face.

### Inferences
- Runtime is not a deciding factor. Choose (a) for quality; its cost is dominated by verification sampling and meshing.

### Gaps
- Environment correction: the system `python` (3.14) on this PC has numpy but **no scipy or matplotlib**. All experiments ran in FreeCAD's bundled Python 3.11, which has numpy 1.26.4, scipy 1.16.3 and matplotlib 3.10.8.
- A KD-tree nearest-point query on a densely sampled curve was very slow (4 s per 100 k far-field points). Sampling the line at about 1 mm and refining with Newton fixed it.
