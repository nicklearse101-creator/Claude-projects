# Normal-aware B-spline fitting to a coarse low-poly mesh (Kunos AE86 C-pillar)

Scope: (a) fitting with position + normal (Hermite) data, (b) telling flat-intended facets from chords, (c) rebuilding the intended smooth surface between sparse vertices from positions + normals (PN / Phong / Nagata / NLSA) and using it as dense virtual samples. Everything aimed at Python + numpy least squares, FreeCAD/OCC headless.

Sources actually read in full text for this note: Boschiroli, Fünfzig, Romani, Albrecht, "A comparison of local parametric C0 Bézier interpolants for triangular meshes", Computers & Graphics 2011 (author preprint, July 2010), called **[BFRA]** below; Wang, Pottmann, Liu, "Fitting B-spline curves to point clouds by curvature-based squared distance minimization", ACM TOG 25(2) 2006, called **[WPL]**; the OCCT reference page for GeomAPI_PointsToBSplineSurface; the Blender 4.3 manual page for the Weighted Normal modifier. Local copies of the two PDFs and their extracted text are in `D:\ClaudeData\tmp\research_cpillar\` (`dl\comparison.pdf`, `comparison.txt`, `dl\sdm_tr143.pdf`, `sdm.txt`).

---

## Q1. Normal-constrained (Hermite) least-squares B-spline surface fitting: how normal constraints are linearised, weighted, and where it is described

### Takeaway
No standard library takes normals: OCC's `GeomAPI_PointsToBSplineSurface` accepts only points (plus length/curvature/torsion smoothing weights). Normal data has to go in as extra linear rows you build yourself. With the (u,v) parameters held fixed, the tangency conditions `n·S_u = 0` and `n·S_v = 0` are linear in the control points. For a height field they become exact slope rows `f_x = -n_x/n_z`, `f_y = -n_y/n_z`. The fitting literature ([WPL]) says point-to-tangent-plane ("tangent distance") error terms are a Gauss-Newton step. That step is fast but can be unstable where curvature is high, and a curvature-aware squared-distance term is more robust. For fairness, [WPL] use a small bending-energy weight (β = 0.001, α = 0 for membrane).

### Cited Findings
- OCCT `GeomAPI_PointsToBSplineSurface` has four approximation entry points: points with DegMin/DegMax/Continuity/Tol3D; the same plus ParType (ChordLength by default, Centripetal, IsoParametric); a variational version with **Weight1, Weight2, Weight3**; and a Z-grid height field `(ZPoints, X0, dX, Y0, dY, …)`. Defaults are DegMin = 3, DegMax = 8, Continuity = C2, Tol3D = 1e-3. The smoothing variant minimises "Weight1*CurveLength + Weight2*Curvature + Weight3*Torsion". None of these methods accepts tangent or normal input. — [OCCT reference: GeomAPI_PointsToBSplineSurface](https://occt3d.com/dev/doc/refman/html/class_geom_a_p_i___points_to_b_spline_surface.html)
- [WPL] set out the three classic error terms for a data point X_k with foot point P(t_k) on the current fit:
  - PD (point distance), `||P+(t_k) − X_k||²`, gives linear (slow) convergence. PDM "is also widely used for surface fitting", including Hoppe et al. 1994, Forsey & Bartels 1995, Greiner et al. 2002 and Weiss et al. 2002.
  - TD (tangent distance), `e_TD = [(P+(t_k) − X_k)ᵀ N_k]²` with N_k the unit normal of the current fit at the foot point. It measures distance to the tangent line or plane. TD minimisation is a Gauss-Newton iteration, which is "unstable for target shapes with high curvature variations".
  - SD (squared distance), a curvature-based second-order term. With d the signed distance and ρ the curvature radius: for d < 0, `e_SD = d/(d−ρ)·[(P+−X)ᵀT]² + [(P+−X)ᵀN]²`; for 0 ≤ d < ρ the tangential coefficient is clamped to 0, i.e. `max{0, d/(d−ρ)}`, so SD reduces to TD there. [WPL] show SDM is a quasi-Newton method and that it outperforms PDM and TDM. — [Wang, Pottmann, Liu 2006 (TU Wien copy)](https://www.geometrie.tuwien.ac.at/geom/ig/papers/tr143.pdf)
- [WPL] objective: `f = ½ Σ e_k + α F1 + β F2`, where `F1 = ∫||P'||²` (membrane/stretch) and `F2 = ∫||P''||²` (bending). "The same values of energy coefficients α = 0 and β = 0.001 are used for all the examples" (uniform-knot cubic, curves normalised to their test scale). One example uses a smoothing coefficient λ = 0.005. — [WPL](https://www.geometrie.tuwien.ac.at/geom/ig/papers/tr143.pdf)
- Weiss, Andor, Renner, Várady, "Advanced surface fitting techniques", CAGD 19(1):19–42, 2002 (DOI 10.1016/S0167-8396(01)00086-3). Per the abstract and summaries, it uses a hybrid "approximation + smoothness" (variational) functional. It argues that from data points alone the smoothing weights can hardly be set in one step, so it proposes an iterative strategy to hold tight tolerances and smoothness at once, plus initial parametrisation and shape-dependent knot refinement. I did not get the full text, so its exact weight schedule is not here. — [SZTAKI eprints](https://eprints.sztaki.hu/2966/), [dblp](https://dblp.uni-trier.de/rec/journals/cagd/WeissARV02.html)
- Hoppe et al. (SIGGRAPH 1996) fit G1 B-spline surfaces of arbitrary topology to unorganised points. G1 is maintained by a surface-spline construction, so "fitting the surface to the data involves only a sparse linear least squares problem with a few linear constraints". — [Eck & Hoppe 1996](https://hhoppe.com/bspline.pdf)
- An MIT thesis (core.ac.uk record 4407164) has a section titled "B-spline surface least squares fitting with normal vector constraints" with "specifying target normal vectors". I saw only the table of contents; the PDF download returned HTTP 403. — [core.ac.uk 4407164](https://core.ac.uk/download/4407164.pdf)
- Other point+normal (Hermite) fitting work exists, e.g. homogeneous MLS fitting of point-normal pairs (arXiv 1912.10194), and VALVEFIT (arXiv 2505.09790), which adds a normal-orientation regularisation term to B-spline fitting. — [arXiv 1912.10194](https://arxiv.org/pdf/1912.10194), [arXiv 2505.09790](https://arxiv.org/pdf/2505.09790)

### Inferences
These are my derivations, not taken from a source. Check them on the C-pillar data.
- **Parametric tangency rows.** With `S(u,v) = Σ_ij N_i(u) M_j(v) P_ij` and (u_k, v_k) fixed, use
  `S_u(u_k,v_k) = Σ N_i'(u_k) M_j(v_k) P_ij` and `S_v = Σ N_i(u_k) M_j'(v_k) P_ij`.
  The rows `n_k · S_u(u_k,v_k) = 0` and `n_k · S_v(u_k,v_k) = 0` are linear in the 3·(nu·nv) unknowns (one scalar row each, coupling x, y and z). They are homogeneous, so they cannot pull the surface anywhere on their own. They only work alongside the position rows and a fairness term.
  - Scale each row by `h / |S_u^prev|` (and `h / |S_v^prev|`), using the previous iterate's tangent length. The residual then reads as approximately `h · sin(angle error)` in mm, where h is a characteristic length (half the facet edge, 50–75 mm on Kunos). Without this scaling the row's weight depends on the parametrisation speed.
- **Height-field form (exact, no iteration).** For `z = f(x,y)` in a local frame whose z axis is the mean normal of the region, a data normal `n = (n_x, n_y, n_z)` with n_z > 0 gives `f_x(x_k,y_k) = −n_x/n_z` and `f_y(x_k,y_k) = −n_y/n_z`. These are linear rows in the coefficients via the basis derivatives. Multiply by h to convert slope error to mm-equivalent.
  - Reject normals with n_z < cos 60° (slope > 1.7). Beyond that the gradient blows up, and the height field is the wrong representation anyway. This is the "flat top + shoulder + side" problem: split into separate faces rather than force one graph.
- **Weighting rule of thumb.** A slope (angle) error δ at a vertex causes about h·δ of position error at distance h. If Kunos normals are trustworthy to σ_n degrees and positions to σ_p mm, pick `w_n/w_p ≈ σ_p / (h · σ_n[rad])`.
  - Example: σ_p = 0.3 mm, h = 60 mm, σ_n = 1° (0.0175 rad) gives w_n/w_p ≈ 0.3. So normal rows should be similar to, or a bit weaker than, position rows once scaled by h. Do not make them dominant: normals that come from averaging have systematic bias at region boundaries (see Q4).
- **Tangent-plane (TD) position rows instead of 3-D point rows.** With a data normal available, the row `n_k · (S(u_k,v_k) − X_k) = 0` lets the surface slide tangentially. This is [WPL]'s TD term, but using the mesh's normal rather than the fit's. It reduces the effect of parametrisation error.
  - [WPL] warn TD alone is unstable where curvature is high, so keep a small tangential component, e.g. 0.1× the normal weight, or the 3-D point rows at low weight.
- **Fairness.** Prefer bending (thin-plate) energy `∫ S_uu² + 2 S_uv² + S_vv²` over membrane `∫ S_u² + S_v²` for car panels. Membrane energy shrinks and flattens towards boundaries, and [WPL] themselves used α = 0 (membrane off) with a small bending weight.
  - Normalise the energy to the patch size: multiply by L² for a patch of size L, so λ is dimensionless.
  - Then choose λ by leave-one-out (or k-fold) cross-validation on the true vertices, ideally on the in-between "flat-intended" samples. That yields an error measure the fit did not see.
- **OCC route.** OCC's built-in smoothing weights cannot take normals. Solve the Hermite least squares in numpy, then hand the poles to `Geom_BSplineSurface` directly rather than going through `GeomAPI_PointsToBSplineSurface`.

### Gaps
- I could not read the full text of Weiss et al. 2002, Pottmann & Leopoldseder, Hoschek & Lasser, or the NURBS Book ch. 9, so I have no source-stated weight values for normal rows in surface fitting. The weighting rule above is derived, not cited.
- The MIT thesis with an explicit "normal vector constraints" section was blocked (HTTP 403).

---

## Q2. Reconstructing the intended curved surface from vertex positions + normals (PN triangles, Phong tessellation, Nagata, NLSA/Walton-Meek): formulas, error, use as virtual samples, behaviour on flat facets

### Takeaway
All four local schemes build one Bézier triangle per mesh triangle from just its three positions and three normals. For dense virtual samples on consistent data, Nagata (quadratic) is the most accurate on spheres and tori. However, it is numerically unstable when the two normals of an edge are nearly parallel, which is exactly the flat-intended case. **PN triangles (cubic) are the robust choice:**
- they reproduce the tangent planes at the vertices;
- their control points stay within l/6 of the edges;
- they give the best cross-edge normal continuity on real low-poly meshes;
- they are only 1e-5·R inside a sphere at Kunos-like edge angles.

Phong tessellation with α = 3/4 is the least accurate and bulges outward, so do not use it as data. All of these schemes reduce to the flat triangle when the corner normals equal the face normal.

### Cited Findings
- **Notation.** Triangle p0, p1, p2 with normals n0, n1, n2; `w_ij = (p_j − p_i)·n_i`. All schemes use only the triangle's own three points and normals. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
- **PN triangles** (Vlachos, Peters, Boyd, Mitchell, I3D 2001): cubic Bézier triangle.
  - Corners: `b300 = p0, b030 = p1, b003 = p2`.
  - Edges: `b210 = (2p0 + p1 − w01 n0)/3`, `b120 = (2p1 + p0 − w10 n1)/3`, `b021 = (2p1 + p2 − w12 n1)/3`, `b012 = (2p2 + p1 − w21 n2)/3`, `b102 = (2p2 + p0 − w20 n2)/3`, `b201 = (2p0 + p2 − w02 n0)/3`. Each is the 1/3 point of the edge projected into the nearest corner's tangent plane.
  - Centre: `m = (sum of the 6 edge points)/6`, `V = (p0+p1+p2)/3`, `b111 = m + (m − V)/2`.
  - Each boundary curve's control points stay within l/6 of the edge, where l is the longest edge, so the patch "provably remains close to the flat triangle". — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
  - A secondary source says Kato (2002) suggested an alternative centre point `b111 = E + 5(E − V)`. Not verified in a primary source. — [Wikipedia: Point-normal triangle](https://en.wikipedia.org/wiki/Point-normal_triangle)
- **Phong tessellation** (Boubekeur & Alexa, SIGGRAPH Asia 2008, ACM TOG 27(5) art. 141):
  - Evaluate the flat point p(u,v,w), project it onto the three vertex tangent planes, and blend the projections barycentrically to get s*. Then `s_α = (1−α)p + α s*`; the paper proposes α = 3/4.
  - As a quadratic Bézier triangle: `b110 = (p0+p1)/2 + α·[½(π0(p1)+π1(p0)) − (p0+p1)/2]`, and similarly for the other edges. π_i(x) is the projection of x onto the tangent plane at p_i: `π_i(x) = x − ((x − p_i)·n_i) n_i`.
  - Phong with α = 1/3 gives edge points equal to the average of the two PN edge control points. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf); paper record [ACM / SIGGRAPH history](https://history.siggraph.org/?p=195171)
- **NLSA triangles** (Barrera et al.) are shown to be exactly Phong tessellation with α = 1/2. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
- **Nagata patch** (Nagata, CAGD 2005): quadratic.
  - Edge curve `x(t) = p0 + (d − c)t + c t²`, where d = p1 − p0.
  - Define `ν = (n0+n1)/2`, `Δν = (n0−n1)/2`, `d̄ = d·ν`, `Δd = d·Δν`, `Δc = n0·Δν`, `c = n0·n1 = 1 − 2Δc`.
  - Curvature coefficient: `c_1 = Δd/(1−Δc)·ν + d̄/Δc·Δν` for c ≠ ±1, else 0.
  - Bézier form: `b110 = (p0+p1)/2 − c_1/2`. This is the point on the intersection line of the two tangent planes closest to the edge midpoint. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
- **Nagata instability.** When the two tangent planes are near parallel, their intersection line runs off to infinity and the patch inflates. The fix is a threshold ε: set c_1 = 0 if `Δc ≤ ε` or `1 − Δc ≤ ε`. On real meshes ε "must be set quite high": Bunny ε = 0.03, Monsterfrog 0.01, Vase 0.06. Regular sphere and torus meshes work with ε = 0. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
- **Accuracy vs a unit sphere** (icosahedron refined by 4-splits, mean signed distance ± sd and [min, max], R = 1). — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf), Table 3

  | Level | Scheme | Mean ± sd | [min, max] |
  |---|---|---|---|
  | i = 0 (20 triangles) | Phong | +0.0153 | max 0.027 |
  | | Nagata ε = 0 | +0.0029 | max 0.013 |
  | | PN | −0.032 | min −0.0586 |
  | | NLSA | −0.037 | min −0.0587 |
  | i = 1 (80 triangles) | Phong | +0.0157 | max 0.023 |
  | | Nagata | +3.0e-4 | max 1.26e-3 |
  | | PN | −2.8e-3 | min −6.3e-3 |
  | i = 2 (320 triangles) | Phong | +5.0e-3 | max 8.2e-3 |
  | | Nagata | +2.1e-5 | max 8.9e-5 |
  | | PN | −1.9e-4 | min −4.7e-4 |
  | i = 3 (1280 triangles) | Phong | +1.34e-3 | max 2.2e-3 |
  | | Nagata | +1.3e-6 | max 5.8e-6 |
  | | PN | −1.2e-5 | min −3.1e-5 |

  - Ranking given: "Nagata triangles perform best, followed by PN triangles and NLSA triangles, whereas Phong tessellation exhibits the worst approximation behaviour".
  - Phong bends outward, while PN and NLSA lie inside the sphere. PN is too shallow because of its b111 choice.
  - The torus (r1 = 1, r2 = 0.5) shows the same ordering.
- **Real low-poly meshes** (cross-edge normal continuity, mean cos between adjacent patch normals): "PN triangles give the best continuity", ranked PN > Phong > NLSA > Nagata. Nagata is worst because its ε threshold makes many edges straight. Examples: Vase PN 0.987 vs Phong 0.945 vs Nagata 0.797. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf), Table 6
- **PN artifacts.** On "inflection" edges (normals tilting the same way relative to the edge's orthogonal plane), cubic PN boundary curves can produce "artifacts or ondulations". On quad meshes triangulated with a diagonal, the two triangles beside the diagonal get opposite-sign Gaussian curvature near it. In the Bunny, 58 % of edges are inflection edges, which drives high curvature magnitudes in PN. Quadratic schemes, by contrast, "generate fairly planar patches" on the triangulated Vase. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
- **Phong α.** It is a global flatness control: α = 0 gives the flat mesh and α = 1 full Phong. The authors note Phong "usually … is too inflated", which is why α exists. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
- **Walton–Meek** gives a G1 surface but uses a blending (non-polynomial) approach, so [BFRA] exclude it from the comparison. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)

### Inferences
- **Flat facets are reproduced exactly by PN and Phong.** If all three normals equal the face normal n_f and the vertices lie in that plane, then `w_ij = (p_j − p_i)·n_f = 0`. Every PN control point stays in the plane, and the Phong projections π_i(x) leave in-plane points unchanged. So a "flat-intended" triangle gives flat virtual samples automatically. This confirms the 4° flat-sample trick, but it also means PN samples are only as good as the vertex normals.
  - In Nagata, parallel normals hit the singular case and the coefficient is set to 0, which is also flat. Near-parallel but inconsistent normals blow up, though.
- **Scale to Kunos.** The angle between the normals across an edge is about L/R.
  - Icosahedron levels i = 0, 1, 2, 3 have edge angles of roughly 63°, 32°, 16° and 8° (edge lengths ≈ 1.05, 0.55, 0.27, 0.14 of R).
  - A 100–150 mm Kunos facet on a body panel with R ≈ 1000–2000 mm has an edge angle of about 3–9°. That is the i = 3 regime or finer.
  - Scaling Table 3 at i = 3 to R = 1000 mm: PN max error ≈ 0.03 mm, Nagata ≈ 0.006 mm, but Phong (α = 3/4) ≈ 2.2 mm outward.
  - On a tighter shoulder radius (R ≈ 150–300 mm, edge angle ≈ 30–45°, i ≈ 1 regime), PN max error ≈ 6.3e-3·R ≈ 1–2 mm inward. Nagata would be ≈ 0.2–0.4 mm if it were stable.
- **Recommendation for virtual samples.**
  - Use cubic PN boundary curves. Each is a cubic Hermite curve with end tangents projected into the vertex tangent planes and lengths ≈ L/3.
  - Sample PN interiors at about 5–10 points per triangle, weighted below true vertices (e.g. 0.3–0.5 of the vertex weight).
  - On tight radii, optionally replace an edge with the Nagata quadratic when the normal angle across it exceeds about 5° and the data are consistent, i.e. both `|w_ij|` and `|w_ji|` are similar in size and of the expected sign.
  - Never use Phong α = 3/4 as data.
- **Important for "chord" triangles.** PN samples are not chord samples. They follow the vertex tangent planes, so they bulge off the flat chord by about the sag. That is what makes them suitable inside chord triangles where raw facet samples are forbidden.
  - Risk: on inflection edges and diagonal-split quads (common in Kunos meshes, which are triangulated quads), PN puts S-shaped undulations into the samples. Down-weight PN samples on triangles that have an inflection edge, i.e. where `w_ij` and `w_ji` have the same sign (see Q3).

### Gaps
- I did not read the original Vlachos 2001, Boubekeur & Alexa 2008, or Nagata 2005/2010 papers directly; formulas are from the [BFRA] reformulation. The Nagata 2010 G1 paper (J. Applied Math, DOI 10.1155/2010/952420) returned HTTP 503.
- There is no published error figure for car-panel-like, anisotropic, long-thin triangles. The sphere and torus tests use near-equilateral triangles.

---

## Q3. Detecting from vertex normals whether a triangle is a chord over a curve or genuinely flat, and estimating chord sag

### Takeaway
Use per-edge tests, not only a "three normals agree" test. For each edge, `w_ij = (p_j − p_i)·n_i` measures how far p_j sits off p_i's tangent plane. On a circular arc with chord L and an angle θ between the end normals: `|w_ij| ≈ L·θ/2` and the sag (mid-chord to arc) is `s = (L/2)·tan(θ/4) ≈ L·θ/8`. Classify an edge as a chord when its predicted sag exceeds the fitting tolerance. The edge type (convex, concave, inflection) follows from the signs of `w_ij` and `w_ji`.

### Cited Findings
- [BFRA] measure the "curvedness" of each triangle by the cosine between its vertex normals and its face normal (mean 0.81–0.98 over their test meshes). They classify each edge as convex, concave or inflection "by the directions of the two vertex normals relative to a plane orthogonal to the edge" (after Vlachos et al.). — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf), Table 4
- PN edge control points are built from `w_ij = (p_j − p_i)·n_i`, the signed offset of p_j from the tangent plane at p_i. This is the quantity that encodes the edge bending. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)
- Nagata's coefficient is defined from `c = n0·n1` and is singular as c → 1. In practice the threshold ε on `Δc = (1 − c)/2` was set to 0.01–0.06. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)

### Inferences
Elementary geometry, derived here; no source fetched for it.
- **Sag formula.** Circle radius R, chord L, end normals at angle θ (the arc turns θ, half-angle φ = θ/2). Then `L = 2R sin φ` and `s = R(1 − cos φ) = (L/2)·tan(φ/2)`. For small θ, **s ≈ L·θ/8** (θ in rad), equivalently **s ≈ L²/(8R)**. Also `w_ij = −L sin φ ≈ −L·θ/2`.
  - Worked numbers:
    - L = 120 mm, θ = 4° (0.0698 rad): s ≈ 1.05 mm.
    - L = 45 mm, θ = 4°: s ≈ 0.39 mm.
    - L = 150 mm, θ = 2°: s ≈ 0.65 mm.
  - So the current 4° "flat-intended" threshold still allows up to about 1 mm sag on 120–150 mm triangles. To bound sag by a tolerance τ, use **θ_max = 8τ/L**. For τ = 0.3 mm and L = 120 mm that is 0.02 rad ≈ 1.15°. For the 45 mm C-pillar facet, 4° is fine (0.39 mm).
- **Per-edge classifier (numpy).** For edge e = p_j − p_i with |e| = L, compute `a_i = n_i·e/L` and `a_j = n_j·e/L`. These are the sines of each end normal's tilt along the edge.
  - Curvature along the edge: `κ_e ≈ (n_j − n_i)·e / L²`. Here n·e/L is the sine of the tilt, so the difference over L is the turn rate.
  - Predicted sag: `s_e ≈ |κ_e|·L²/8`.
  - Edge types:
    - **chord-convex**: a_i < 0 < a_j (normals splay apart; outward-oriented normals on a convex panel);
    - **chord-concave**: the opposite signs;
    - **inflection**: a_i and a_j have the same sign, the edge is S-shaped and PN will undulate;
    - **flat**: |a_i|, |a_j| < sin(θ_max/2) and the face normal agrees with both normals.
- **Triangle class.** "Flat-intended" if all three edges are flat **and** the vertex normals agree with the face normal within θ_max. Testing against the face normal matters: three mutually agreeing normals that are all tilted off the face plane mean a tilted chord, not a flat facet.
  - "Chord" if any edge has s_e > τ. For chord triangles, use only vertices, PN or Nagata virtual samples, and normal rows, never raw facet samples.
- **Consistency check (catches bad normals).** On a true arc, `w_ij ≈ −w_ji` (symmetric). Large asymmetry, e.g. `|w_ij + w_ji| > 0.5·max(|w_ij|, |w_ji|)`, flags a vertex whose normal is biased: averaged across a crease, or from a region boundary (see Q4). Down-weight or drop that vertex's normal rows.

### Gaps
- No source gives Kunos-specific thresholds. θ_max and the asymmetry ratio above are suggestions to tune against the C-pillar's known flat top and shoulder.

---

## Q4. What vertex normals mean in game-art pipelines (weighted normals, baked high-poly normals); likely Kunos convention; reliability as tangency data

### Takeaway
Game-art normals are shading devices, not measured tangents. Blender's Weighted Normal modifier (face-area or corner-angle weighting) exists to "make some faces appear very flat". With face-area weighting, large flat faces pull their vertex normals onto the flat-face normal, and the curvature is pushed into the small faces (bevels, shoulders). So normals on big flat facets are good flatness indicators, but normals at the boundary between a flat and a curved region are biased. I found no documentation of the normal convention Kunos uses.

### Cited Findings
- Blender Weighted Normal modifier: it "changes the custom normals of a mesh, using various selectable methods", which can help "make some faces appear very flat during shading".
  - **Modes**: Face Area (bigger faces weigh more); Corner Angle (weight from the angle the face forms at the vertex, which is Blender's default way of combining face normals); Face Area and Angle (the product).
  - **Weight**: "a bit like a contrast setting"; "A value of 50 means all faces are weighted uniformly", above 50 increases the contrast and below 50 reduces it.
  - **Threshold**: rounding for equal weights.
  - **Keep Sharp**: preserves sharp edges.
  - **Face Influence**: weak/medium/strong face strengths (e.g. from Bevel's Set Strength); if three faces meet and one is strong, only the strong face's normal is used. — [Blender 4.3 manual: Weighted Normal Modifier](https://docs.blender.org/manual/en/4.3/modeling/modifiers/normals/weighted_normal.html)
- In [BFRA]'s test meshes, the vertex-to-face normal cosine ranged down to 0.0012 (Bunny) and even negative values, i.e. "degenerate normals" pointing out of the triangle's half space (Monsterfrog teeth and tail). Those are exactly where tangent-plane continuity broke worst. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)

### Inferences
- **Area- or angle-weighted vertex normals are averages of the adjacent face normals.** At a vertex shared by a large flat facet and a curved shoulder strip, the normal is tilted part-way towards the shoulder. With corner-angle weighting that is roughly in proportion to the angles subtended. Consequences:
  - a truly flat facet whose corners lie on the flat/curve border fails the "three corner normals agree within 4°" test, so it is under-detected;
  - normal rows at those border vertices pull the flat top into a slight roll-off.
  - Mitigation: in the flat region, replace a border vertex's normal with the flat region's face normal. In the curved region, keep it, or recompute it from the curved-side faces only (a one-sided normal).
- **If the artist used face-area weighting or custom normals,** normals on small chamfer or transition faces are deliberately wrong as tangents (the shading is pushed into them). Treat normals on thin or small triangles, e.g. area < 10 % of the region median, as low-confidence.
- **Recompute and compare.** Compute area-weighted and angle-weighted normals from the Kunos geometry yourself and compare them with the stored normals.
  - If the stored normals match the recomputed ones within about 0.5°, they carry no extra information beyond the geometry. They are then a smoothed estimate of the facet geometry, and their value as "intended curvature" is limited to what the averaging implies.
  - If they differ systematically, they were authored (custom, weighted, or from a high-poly bake) and are probably more informative about the intended surface.
  - This test is cheap and decides how much weight w_n deserves.

### Gaps
- I found no Assetto Corsa or Kunos documentation on how car mesh normals are produced (3ds Max smoothing groups vs custom or weighted normals vs a high-poly bake). I did not search 3ds Max's own weighted-normal tools within the call budget.
- I found no source quantifying the accuracy of area- vs angle-weighted normals against the true surface normal on coarse meshes.

---

## Q5. Robust weighting near hard edges (split normals), and avoiding ripples between sparse rows (fairing choice, cross-validation)

### Takeaway
Where a vertex has split normals (hard edge, ~0.5 % of Kunos edges), use the corner normal belonging to the face being fitted, or drop that vertex's normal rows entirely. Treat hard edges as face boundaries, not data inside one surface. To stop ripples between sparse vertex rows, use a small bending (thin-plate) fairness term rather than membrane: [WPL] use α = 0 and β = 0.001 for curves. Normal rows themselves also suppress ripples, because they pin the slope at each vertex. Choose the fairness weight by cross-validation on the vertices.

### Cited Findings
- OCC's variational surface approximation exposes only length, curvature and torsion criteria weights (Weight1/2/3), with no normal input. — [OCCT reference](https://occt3d.com/dev/doc/refman/html/class_geom_a_p_i___points_to_b_spline_surface.html)
- [WPL]: `f = ½ Σ e_k + α ∫||P'||² + β ∫||P''||²`, with α = 0 and β = 0.001 in all examples; "a non-zero but small value of α" may speed up convergence when the initial curve is far from the target. — [WPL](https://www.geometrie.tuwien.ac.at/geom/ig/papers/tr143.pdf)
- Weiss et al. 2002 say the smoothing weights cannot be set appropriately in one step from data points alone, and use an iterative strategy instead. — [SZTAKI eprints](https://eprints.sztaki.hu/2966/)
- Degenerate or crease normals are where interpolation schemes break G1 most. — [BFRA](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf)

### Inferences
- **Hard edges.** In a kn5 mesh a hard edge shows up as duplicated vertices with different normals. Build the face-segmentation boundaries along these. For a surface fitted on one side, use only that side's corner normals. Never average across a split: averaging produces exactly the "degenerate normal" bias.
- **Ripple control.**
  - Bending energy with λ normalised by patch size. Start with λ·L² ≈ 1e-3 relative to unit-weight position rows; this mirrors [WPL]'s β = 0.001 on normalised data, but is not a source value for surfaces.
  - Use the fewest knots that meet the tolerance, i.e. knot spans no smaller than the vertex spacing (100–150 mm). More spans than data rows invite ripples, and normal rows only partly constrain them.
  - Normal rows add 2 constraints per vertex, roughly tripling the information per vertex, so they allow about 1.5–2× more control points before ripples appear (inference).
- **Cross-validation loop.**
  - Hold out 10 % of the vertices, fit, and measure their distance to the fitted surface and their normal angle error.
  - Sweep λ over {1e-5 … 1e-1} and w_n/w_p over {0.1, 0.3, 1}, and pick the minimum held-out p95.
  - Also check the deviation at the centroids of flat-intended facets (should be ≈ 0) and at the PN-predicted mid-points of chord triangles (should be ≈ 0 relative to PN, ≤ τ).
  - This gives one metric that catches both the C-pillar bulge (9.8 mm over the 45 mm facet) and over-flattening of the shoulder.
- **Flat top + shoulder + side cannot be one height field.** Split at the curvature break: the per-edge κ_e from Q3 jumps there. Fit each region separately with its own frame, then join with the strip or fillet builder. Do not raise the knot count to force a single surface.

### Gaps
- I found no source comparing thin-plate vs membrane fairing specifically for normal-constrained surface fitting, and no published λ for surfaces in mm units. Values above are starting points to tune.
