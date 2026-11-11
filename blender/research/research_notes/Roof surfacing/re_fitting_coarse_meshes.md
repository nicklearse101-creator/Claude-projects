# Fitting large, low-curvature smooth panels (car roof) to a coarse triangle mesh without chord-sag bias

Scope: how RE tools and the literature fit one smooth B-spline face to sparse/coarse facet data, how to use vertex normals, which fairing to use and how to weight it, how to deal with chord sag, and what accuracy is normal. It includes a small numpy experiment run for this note (scripts in `D:\ClaudeData\tmp\research_roof\`: `sag_test.py`, `sag_test2.py`, `sag_test3.py`). Experiment set-up: truth is z = -x²/(2·3000) - y²/(2·5000) mm (a crowned roof-like patch, 1400 x 1100 mm). The mesh has about 150 mm edges with jittered vertices: 80 vertices, 126 triangles. Vertices sit exactly on the truth. The fit is one cubic tensor-product B-spline (8x6 or 6x5 controls), scored by RMS and max vertical error against the truth on a dense grid. Experiment numbers are tagged [EXP] and cite the local script, not the web.

## 1. How commercial RE tools fit large smooth surfaces (parameters, deviation targets, coarse data)

### Takeaway
The vendors all expose the same few controls: a control-point/patch count or "resolution", one smoothness factor or penalty weight, and a maximum-deviation tolerance. Underneath is penalised least squares, as in the literature: data term plus λ times a fairness energy, usually the thin-plate energy. Public docs give names and defaults but almost no tuning numbers. None of the docs I found has a dedicated mode for coarse chordal meshes. They assume dense scan meshes, where chord sag is negligible.

### Cited Findings
- Siemens NX `FitSurfaceBuilder` fits "surfaces through facet bodies or point sets/groups". Its API defaults are Degree 3, U/V Degree 5, U/V Patches 1, uniform-patch flags, and an integer `SmoothFactor` (default 0). The docs don't say what the smoothness value does numerically. Some properties need the nx_freeform_2 licence. — [NX Open FitSurfaceBuilder (NX 12)](https://docs.plm.automation.siemens.com/data_services/resources/nx/12/nx_api/custom/en_US/nxopen_python_ref/NXOpen.Features.FitSurfaceBuilder.html); [NX 10](https://docs.plm.automation.siemens.com/data_services/resources/nx/10/nx_api/en_US/custom/nxopen_python_ref/NXOpen.Features.FitSurfaceBuilder.html)
  - So NX's default for a "fit to facets" face is one Bézier-like patch of degree 5x5 (6x6 controls), not a many-knot cubic. For a smooth panel, raising the degree on one span is the vendor default, rather than adding knots.
- CATIA QSR "Power Fit" takes a point cloud plus processed profile curves. It can make a surface constrained to the profiles, a trimmed surface, or a surface from the points inside a region, with an optional Init Surface. "Point Gap" sets the maximum allowed surface-to-cloud error, and "Spikes Deviation" shows the error as comb lines starting at the Point Gap value. "Basic Surface Recognition" fits planes, spheres and cylinders. — [toutiao CATIA QSR tutorial (Chinese)](https://www.toutiao.com/zixun/7504085896560658470/)
- CATIA QSR's user guide mentions an "N-side domain approach with boundary constraints and deviation tolerance through inner points" (excerpt only). — [QSR user guide on Scribd](https://www.scribd.com/document/382904033/qsrug)
- CATIA QSR "Automatic Surface" (2005/06) is marketed as a one-click mesh-to-surface conversion with "perfect boundary continuity (tangency)", i.e. G1, not G2. — [IBM/Dassault PLM forum slides](https://public.dhe.ibm.com/software/emea/se/pres/plmforum06/AutomaticSurfaceReconstruction.pdf)
- PolyWorks|Modeler fits a network of NURBS patches over a polygonal model. It offers G0, G1 or G2 continuity control across patch boundaries and "automatic G2 surface fitting" where the patches have rectangular topology. No dialog parameter names or numbers are given. — [Laser Design: PolyWorks Modeler](https://www.laserdesign.com/?p=5114)
- Geomagic Design X: Auto Surface makes a surface patch network that follows the mesh. A UMD tutorial warns that it may not work well on complex geometry. Release 2022.0 added a "Keep Patch Network in the Tree" option so the network can be edited by hand. Mesh Fit and Auto Surface are tiered features (selective auto-surfacing in higher tiers). — [UMD Dozuki guide](https://dozuki.umd.edu/Guide/Modifying+Scan+Result+using+Geomagic+Design+X/28); [Design X 2022.0 release notes](https://download.laserscanning-europe.com/Geomagic/GeomagicDesignX_ReleaseNotes_v2022.0.0.pdf); [Design X plan comparison 2025](https://proto3000.com/wp-content/uploads/2026/01/Geomagic_DesignX_Plan_Comparison_Flyer_2025.pdf)
- Geomagic Studio's NURBS workflow from faceted meshes often needs curve smoothing, removing control points, and straightening sections. Fitting parameters are described in terms of a normal tolerance. — [Digital Engineering: Geomagic Studio 10](https://www.digitalengineering247.com/article/geomagic-studio-10-improves-your-workflow/Additive-Manufacturing)
- Ansys LS-PrePost "Surface from mesh" exposes a "Max Tol". After fitting it reports the control-point grid it chose (for example 21 x 31 in U/V) plus max and mean deviation. In other words, the tool raises the control-point count until the tolerance is met. — [Ansys LS-PrePost tutorial 6.1](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/lsdyna_prepost_tut/ch08s01.html)
- Autodesk Alias "Surface from Mesh" has a Smooth option with a Smooth Factor and a deviation check. — [Autodesk Alias help: Surface from Mesh](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Tool-Palette-Reference/files/Surfaces-palette/GUID-DC182FBE-C78A-4258-A8A7-558D9C3796D6.html)
- A patent on "scalable and precise fitting of NURBS surfaces to large-size mesh representations" uses a weight that trades the least-squares result against a smoothing term based on thin-plate deformation energy. — [US 10614178 (USPTO)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10614178)
- A practitioner forum claim (single user, not verified): Geomagic, Rapidform and Paraform are "limited to tangency or limited curvature continuity". — [eng-tips thread](https://www.eng-tips.com/threads/what-is-a-class-a-surface.21173/post-130332)

### Inferences
- The industrial recipe is: pick a low control count, keep a single smoothness weight, and raise the control count only until a deviation tolerance is met (LS-PrePost reports exactly this; NX defaults to one patch). Our approach of one cubic per face, few controls and light fairing is in line with that.
- The tools assume dense scan data, where any point on a facet is effectively on the surface. Our mesh breaks that assumption (sag of 1 mm or more). The tools' answer would be "tolerance on vertices", which is what we already score.

### Gaps
- I couldn't find the Geomagic Design X Auto Surface / Mesh Fit dialog parameters with defaults in public pages. The 2014 user guide PDF (https://www.engineering.pitt.edu/contentassets/52314f399aba40fa86709314a569641c/geomagicdesignx2014userguide.pdf) exists but was too large (>10 MB) to fetch. From memory, not verified: Design X Mesh Fit has a "Resolution" choice (control-point count vs allowable deviation), a smoothness slider, and Auto Surface has "Mesh Fit" vs "Feature Following" network methods. Treat these as unverified.
- I found no public PolyWorks numbers for smoothness or deviation defaults, and no NX user-guide meaning for `SmoothFactor`.
- I found no vendor documentation on coarse, chordal (low-poly) meshes specifically.

## 2. Using vertex normals as fitting data (Hermite / point + normal fitting)

### Takeaway
There are two families. (a) Derivative or Hermite constraints: add residuals n·S_u = 0 and n·S_v = 0 at the vertices (linear in the controls for fixed parameters). (b) Point-to-tangent-plane error ("tangent distance"): residual (S(u_k) - p_k)·n_k, which lets the surface slide along the data and is the near-field approximant of squared distance in Pottmann's work. [EXP] Normals only help if they are accurate to about 0.1 degree. Mesh-averaged game normals (0.2 degrees mean, 0.5 degrees max inside; over 1 degree on boundaries) made the fit worse unless they were weighted very low. Weight them by their noise: w_n ≈ σ_pos² / σ_angle².

### Cited Findings
- Pottmann & Leopoldseder ("A concept for parametric surface fitting which avoids the parametrization problem", CAGD 2003) define standard fitting as Σ‖x(u_k,v_k) - p_k‖² + λF_s. They note that parameter estimation "largely effects the result". They replace the point error with local quadratic approximants of the squared distance function. Squared distance to the footpoint is only good in the "far field". In the near field, "it is much better to use ... the squared distance to the tangent plane at the normal footpoint". The full non-negative approximant is d/(d+ρ1)·x1² + d/(d+ρ2)·x2² + x3² (ρ = principal radii). — [Pottmann & Leopoldseder preprint (TU Wien)](https://www.dmg.tuwien.ac.at/geom/ig/papers/pot129.pdf)
- Wang, Pottmann & Liu (ACM TOG 2006) found the SD error term gives faster and more stable convergence than point distance (PD) and tangent distance (TD). TD minimisation (well known in computer vision) amounts to Gauss-Newton. — [TU Wien: Fitting B-spline curves by SDM](https://www.geometrie.tuwien.ac.at/geom/ig/publications/oldpub/2006/wpl_curves_06/wpl_curves_06.html); [HKU: optimisation methods for subdivision surface fitting](https://i.cs.hku.hk/GraphicsGroup/publications/pdf/Design%20and%20Analysis%20of%20Optimization%20Methods%20for%20Subdivision%20Surface%20Fitting.pdf)
- Homogeneous MLS (H-MLS) fits curves and surfaces to point-normal pairs by minimising an objective that matches both the points and the planes through them with the given normals. With all μ_i = 0 it reduces to a plain bicubic B-spline fit. — [arXiv 1912.10194, Anisotropic mesh filtering by H-MLS](https://arxiv.org/pdf/1912.10194)
- Penalised least squares for scattered data with derivative values (Hermite data): a weight λ moves the result between energy minimisation (λ large) and discrete least squares (λ small). — [J. Comput. Math. 27(6) 2009](https://admin.global-sci.org/uploads/Issue/JCM/v27n6/802-811_short.pdf)
- An RWTH report notes the Pottmann et al. approach gets superlinear convergence for only a small computational overhead for surface normals. — [RWTH IGPM report 446](https://www.igpm.rwth-aachen.de/Download/reports/pdf/IGPM446.pdf)
- [EXP] Angle-weighted face-normal averages on the 150 mm mesh, compared with the true normals: interior vertices mean 0.18 degrees, max 0.48 degrees; boundary vertices mean 1.21 degrees, max 1.73 degrees. — `D:\ClaudeData\tmp\research_roof\sag_test2.py`
- [EXP] Vertices only (no normals), λ tiny, 8x6: RMS 0.005 mm. Adding slope rows (dz/dx = -n_x/n_z, dz/dy = -n_y/n_z), RMS / max by normal-row weight w_n (in mm², each slope row multiplied by √w_n):
  - exact normals + 0.1 degree noise: w_n = 100 → 0.006 / 0.021; 1e4 → 0.057 / 0.164
  - + 0.3 degree noise: 100 → 0.010 / 0.030; 1e4 → 0.171 / 0.492
  - + 1 degree noise: 100 → 0.026 / 0.079; 1e4 → 0.570 / 1.647
  - real mesh-averaged normals: 100 → 0.033 / 0.113; 1e3 → 0.210 / 0.665; 1e4 → 0.448 / 1.238
  - With exact normals and 0.05 mm vertex noise, w_n = L² = 22 500 helped (RMS 0.001 to 0.002), but with 1 degree noise it gave RMS 0.65 to 0.76 mm. — `D:\ClaudeData\tmp\research_roof\sag_test.py`, `sag_test2.py`

### Inferences
- Rule for the normal weight: a slope residual is in radians and a position residual in mm. Weight each family by the inverse of its variance: w_n ≈ (σ_z / σ_θ)². With σ_z ≈ 0.05 mm and σ_θ ≈ 0.3 degrees (0.0052 rad), w_n ≈ 90 mm², which matches the break-even near 100 in the sweep. A 1 degree tilt over a 150 mm edge is 2.6 mm of height, so heavily weighted normals will drag the fit.
- Use normals only where they are trustworthy: interior vertices whose ring of face normals is consistent (the existing 4 degree flatness test is the same idea). Drop or down-weight boundary and crease vertices, where averaging mixes faces from other panels; there the error was over 1 degree even on a perfect quadric.
- Artist normals in a game mesh may be hand-edited or averaged across smoothing groups, so measure their accuracy first. On the real roof, compare each vertex normal with the fitted surface normal after a vertices-only fit. The spread of that angle gives σ_θ.
- Tangent-plane residuals (S - p)·n (with the data normal, or the surface normal in TDM) are the better way to use normals for parameter-free sliding. They reduce the need for good (u,v) parameters on a big face, which matters more than the extra shape information.

### Gaps
- I couldn't fetch Weiss et al. (CAGD 2002) full text (403 / not in repository), so I can't say whether they use normals. The abstract covers initial parametrisation, a strategy keeping tight tolerances and smoothness together, "weakly defined control points", and shape-dependent knot refinement. — [dblp](https://dblp.uni-trier.de/rec/journals/cagd/WeissARV02.html); [scispace abstract](https://scispace.com/papers/advanced-surface-fitting-techniques-37x150ekoh)
- I found no published accuracy numbers specifically for B-spline fitting with artist-supplied (game) normals.

## 3. Fairing / regularisation for large panels, and choosing the weight

### Takeaway
The standard choice is the simplified thin-plate energy ∫(x_uu² + 2x_uv² + x_vv²). It penalises curvature itself, so on a crowned roof it flattens the crown as λ grows. [EXP] At λ where it starts to smooth noise it already biased the fit by -0.05 to -0.7 mm. A third-derivative (curvature-variation) energy does not penalise constant curvature: across six decades of λ it never biased the crown and it denoised better than no fairing. Choose λ with GCV/CV, or with the discrepancy principle when vertex noise is known. In Pottmann's iterative scheme λ is decreased from iteration to iteration.

### Cited Findings
- The usual formulation is least squares plus λF_s, with F_s the "simplified thin plate energy" ∫∫(x_uu² + 2x_uv² + x_vv²) du dv. It is quadratic in the controls, so the fit is one linear system. — [Pottmann & Leopoldseder preprint](https://www.dmg.tuwien.ac.at/geom/ig/papers/pot129.pdf)
- In iterative active-surface fitting, the smoothing term matters most in the first steps, to avoid bad parametrisation or loops. Later it "is less important. Thus the smoothing factor λ is decreased from iteration to iteration". Any quadratic functional can be used and it may change per step, so Greiner's non-linear fairness can be built in. The optional term µ∫(x_u² + x_v²) favours constant-speed isoparametric lines. Example: bicubic with 24 x 6 controls, samples 500 → 3000, converged after 20 iterations. — [Pottmann & Leopoldseder preprint](https://www.dmg.tuwien.ac.at/geom/ig/papers/pot129.pdf)
- Weiss et al. frame the tension: a surface that is "too smooth" cannot meet tight tolerances at highly curved areas, while one that is "too accurate" may oscillate. Knot count and placement and the smoothing weights should be set "without user assistance". — [Weiss et al. 2002 (scispace abstract)](https://scispace.com/papers/advanced-surface-fitting-techniques-37x150ekoh); [search summary of abstract via SZTAKI record](https://eprints.sztaki.hu/2966/)
- Smoothing-parameter selection: GCV is the common default (R's `smooth.spline` offers GCV by default, and OCV). GCV can have multiple minima, and a local one can give a wiggly fit. — [arXiv 2205.15157](https://arxiv.org/pdf/2205.15157)
- ML/REML vs CV-type criteria rest on different assumptions about the data-generating process. — [Krivobokova, GCV vs REML (Göttingen)](https://www.uni-goettingen.de/de/document/download/c8761e7966f9b6e2369b0d56baf7e732.pdf/GCV_REML.pdf)
- "Little agreement in the literature" on which selection method to use on real data. The L-curve, rarely used for smoothing, worked "very well" in Frasso's examples, without a compelling explanation why. — [MDPI Stats 4(3) 42](https://mdpi.com/2571-905X/4/3/42); [Leiden thesis](https://studenttheses.universiteitleiden.nl/access/item%3A3597368/view)
- Difference penalties (P-splines) are the robust/standard discrete proxy. — [arXiv 2012.13295](https://arxiv.org/pdf/2012.13295)
- [EXP] Same crowned patch, vertices with 0.1 mm Gaussian noise, 8x6 cubic, integrated energies by quadrature (RMS / max / mean bias in mm):
  - no fairing: 0.078 / 0.233
  - thin-plate λ = 1e2: 0.096 / 0.313 / -0.049
  - thin-plate λ = 1e3: 0.342 / 0.966 / -0.197
  - thin-plate λ = 1e4: 0.979 / 2.077 / -0.700
  - thin-plate λ = 1e5: 4.93 / 12.1 / -2.67
  - third-derivative energy, λ = 1e5 → 1e10: RMS 0.075 → 0.033, max 0.224 → 0.062, bias about -0.02 throughout
  — `D:\ClaudeData\tmp\research_roof\sag_test3.py`
- [EXP] Control-net second differences (our current style) at λ = 1e-4 (scaled by Σw) raised RMS from 0.005 to 0.30 to 0.49 mm on noise-free data. Control-net third differences with clamped knots did worse than second differences, because the clamped end spans make the boundary controls non-uniform, so a quadric's control net has non-zero third differences near the edges. — `D:\ClaudeData\tmp\research_roof\sag_test.py`, `sag_test2.py`

### Inferences
- For a roof (near-constant curvature in each direction), penalise curvature variation (third derivatives, ∫ of S_uuu², S_uuv², S_uvv², S_vvv²), not curvature. Compute it as an integrated energy (Gram matrix or quadrature). Don't use control-net differences on clamped knot vectors, or use them only on interior controls.
- If we keep second-difference fairing, its λ must be tiny. Even "light" fairing lowers the crown by tenths of a mm, and scoring on vertices may hide that, because CV picks λ from vertex residuals that see the bias.
- Weight choice with a known noise level (discrepancy principle): the artist's vertices are exact up to float/export rounding, so the noise is small. Choose the largest λ for which the RMS vertex residual stays at about σ, e.g. 0.02 to 0.05 mm. Cross-check with leave-one-out or k-fold CV on vertices (which we do). Because GCV can have local minima, scan λ over decades and look at the curve rather than trusting one minimiser.
- The control count is itself the main regulariser here. 80 vertices against 48 controls is already well determined for a quadric. Add controls only if the vertex residual exceeds the tolerance.

### Gaps
- I found no source comparing thin-plate vs curvature-variation energy specifically for automotive panels with numbers. The bias result is from our synthetic test (a pure quadric favours the third-derivative energy more than a real roof with varying curvature would).
- I didn't retrieve a direct source on the discrepancy principle for smoothing splines; the rule above is standard regularisation practice, not cited here.

## 4. Dealing with chord sag: vertices vs facet samples; normal-based refinement (PN triangles, Phong tessellation)

### Takeaway
Down-weighting chordal facet samples doesn't remove the bias; it only scales it. [EXP] Equal weights gave -1.25 mm bias and vertices x20 still gave -0.64 mm, so curved-facet interiors must be dropped or corrected. PN triangles reproduce the surface to about 0.006 mm with exact normals. Phong tessellation needs α = 1/2, not the paper's default visual α = 3/4: α = 3/4 overshoots by half the sag and α = 1 by the full sag. Both are only as good as the normals. With real averaged normals the corrected interior samples were still 0.28 mm RMS, 1 mm max off, with a -0.17 mm mean bias. Vertices (plus carefully weighted normals) beat any synthetic interior sample.

### Cited Findings
- PN triangles (Vlachos, Peters, Boyd, Mitchell, I3D 2001) replace each flat triangle with one cubic Bézier patch that matches the vertex positions and normals. The normal field is linear or quadratic. The surface is G1 only at vertices and G0 across edges ("smoother, though not necessarily everywhere tangent continuous"). PNG1 (Fünfzig et al.) adds G1. — [ACM DOI 10.1145/364338.364387](https://doi.org/10.1145/364338.364387); [Wikipedia: Point-normal triangle](https://en.wikipedia.org/wiki/Point-normal_triangle); [Fünfzig et al. comparison of local parametric C0 Bézier interpolants](https://cfuenfzig.lima-city.de/Publications/AComparisonOfLocalParametricC0BezierInterpolants_CG2010.pdf); [Symmetry 8(13) 2016](https://www.scribd.com/document/444976341/symmetry-08-00013)
- PN control net: w_ij = (P_j - P_i)·N_i; b210 = (2P1 + P2 - w12·N1)/3 (and the other five edge points likewise); E = mean of the six edge points; V = (P1 + P2 + P3)/3; b111 = E + (E - V)/2 (Kato 2002 proposed E + 5(E - V)). The definition "ensures that the original vertex normals are reproduced". — [Wikipedia: Point-normal triangle](https://en.wikipedia.org/wiki/Point-normal_triangle)
- Phong tessellation (Boubekeur & Alexa, ACM TOG 27(5), SIGGRAPH Asia 2008) applies Phong normal interpolation to positions: the linear point is projected onto the three vertex tangent planes, the projections are blended barycentrically, and the result is mixed with the linear point by a shape factor α. It is a local refinement for smoother silhouettes. — [Boubekeur, Phong Tessellation page](https://www.telecom-paristech.fr/~boubek/papers/PhongTessellation/); [Crossref record](https://api.crossref.org/works/10.1145%2F1409060.1409094)
- [EXP] Interior samples (barycentric grid n = 6, interior only) vs truth on the 150 mm mesh:
  - flat facet: mean -1.315, RMS 1.355, max 2.56 mm
  - Phong α = 0.75: mean +0.656, max 1.27
  - Phong α = 1.0: mean +1.313, max 2.55
  - Phong α = 0.5: mean -0.001, max 0.007
  - PN triangle, exact normals: max 0.006
  - PN triangle, mesh-averaged normals: mean -0.173, RMS 0.288, max 1.00
  - Phong α = 0.5, mesh-averaged normals: mean -0.173, RMS 0.281, max 0.92
  - with 1 degree normal noise: PN RMS 0.61, max 1.97; Phong α = 0.75 max 3.95
  — `D:\ClaudeData\tmp\research_roof\sag_test.py`, `sag_test2.py`
- [EXP] Fit results, 8x6, λ tiny, exact normals (RMS / bias, mm):
  - vertices only: 0.005 / +0.001
  - + flat samples, equal weight: 1.263 / -1.256
  - vertices x20 + flat samples: 0.679 / -0.665
  - + Phong(0.75) samples: 0.631 / +0.627
  - + PN samples: 0.004 / -0.001
  - With 1 degree normal noise, + PN samples: 0.28; vertices only: 0.034. — `D:\ClaudeData\tmp\research_roof\sag_test.py`

### Inferences
- Why α = 1/2 is exact for quadrics: on a parabola, projecting the chord midpoint onto the two end tangent planes and averaging moves it by twice the sag (L²/4κ⁻¹ vs the needed L²/8κ⁻¹). Phong's visual default α = 3/4 is tuned for looks, not accuracy. (This derivation is mine, and the experiment confirms it to 0.007 mm.)
- Chord sag for an edge of length L on radius R is about s ≈ L²/(8R): 150 mm on R = 3 m gives 0.94 mm and on R = 5 m 0.56 mm. Facet interiors are worse than edge midpoints because the triangle spans a diagonal (our mean facet error was -1.3 mm).
- Practical policy for the AE86 roof:
  1. Fit to vertices (exact data) only.
  2. Use facet-interior samples only where the three corner normals agree to within the threshold (truly flat facets). On curved facets, drop the interior samples rather than down-weight them.
  3. If interior coverage is needed (for example for trimming or to stabilise sparse regions), generate samples by PN or Phong α = 0.5 from interior-vertex normals only, give them low weight (σ ≈ 0.3 mm), and never use them on boundary rows.
  4. Optionally add slope or tangent-plane rows at interior vertices, weighted by (σ_z/σ_θ)².
- Alternative: the edge midpoint corrected by its two end normals (a cubic Hermite edge curve, i.e. the PN edge) is the most reliable extra sample. It only uses the two normals on that edge, and edges are shared by two facets, so it is unambiguous.
- The vertex-only score is exactly what the tools' tolerance means, but it can't see bulging between vertices. Also score held-out vertices (k-fold), and the deviation from PN or Hermite edge-midpoints as a soft secondary check.

### Gaps
- I didn't read the Phong Tessellation paper PDF (redirect chain), so I can't confirm from the source which α the authors recommend; α = 3/4 as their default comes from memory. The α = 1/2 exactness is from our own derivation and test.
- I found no RE-tool documentation on chord-sag correction for low-poly input.

## 5. Typical achievable accuracy and error metrics for body panels

### Takeaway
Public sources give no universal number. Tolerances are set per programme (OEM, supplier, quality). Reported practice is max/mean deviation on the data plus continuity metrics (G1 angle about 0.2 degrees, curvature-continuity checks). For our case the data itself is only accurate between vertices to the sag (about 1 mm). A sensible target is vertex deviation of 0.1 mm or less, held-out vertices about 0.2 mm, and the crown not biased.

### Cited Findings
- Class A surfaces strictly have curvature and tangency alignment; many people read Class A as G2 (or even G3). — [Wikipedia: Class A surface](https://en.wikipedia.org/wiki/Class_A_surface)
- Wikipedia's Class A/B tables give example tolerances such as G0 = 0.001 mm and G1 = 0.2 degrees max (another revision: G0 = 0 mm, G1 = 0.2 degrees, Cu = 0.1 mm⁻¹). The scheme is described as not standardised, and revisions disagree. — [Wikipedia: Class A surface](https://en.wikipedia.org/wiki/Class_A_surface); [IPFS mirror](https://en.wikipedia-on-ipfs.org/wiki/Class_A_surface)
- In reverse engineering, a clay model is scanned and rebuilt as NURBS, and the modeller is given a tolerance the NURBS data must match. Scan data always has some noise, which the modeller must reject while keeping the design character. — [Autodesk Alias: Understanding Class A Modeling](https://help.autodesk.com/cloudhelp/2024/ENU/Alias-Getting-Started/files/theory-builders/GUID-64611955-D2CC-44F2-98F0-D4F1FE931D8B.html)
- Surface definitions and tolerances "will normally be defined by the consensus of Engineering, the Plant, Quality and the Supplier" (forum). — [eng-tips](https://www.eng-tips.com/threads/what-is-a-class-a-surface.21173/post-130332)
- Tools report max and mean deviation after fitting (LS-PrePost), or show deviation as combs against a Point Gap (CATIA). — [Ansys LS-PrePost tutorial](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/lsdyna_prepost_tut/ch08s01.html); [toutiao CATIA QSR tutorial](https://www.toutiao.com/zixun/7504085896560658470/)
- InnovMetric case studies (Bushwacker, Pratt & Miller) describe PolyWorks NURBS of vehicle body parts used as CAD baselines, but give no deviation numbers. — [Bushwacker case study](https://c-7022-20160308-www-innovmetric-com.i.icims.com/case-studies/bushwacker); [Pratt & Miller case study](https://c-7022-20160308-www-innovmetric-com.i.icims.com/case-studies/pratt-and-miller)
- Campana, Gerbino & Renno (DESIGN 2002) cover NURBS fitting for RE of sheet-metal parts, focused on deviation and smoothing (no numbers in the abstract). — [Design Society](https://designsociety.org/publication/29602/New+Surface+Fitting+Approach+in+Reverse+Engineering+of+Sheet+Metal+Parts)
- Pottmann & Leopoldseder report mean and max deviation per iteration for a triangulated clay model (24 x 6 bicubic), i.e. mean plus max on the mesh is the academic metric too. — [Pottmann & Leopoldseder preprint](https://www.dmg.tuwien.ac.at/geom/ig/papers/pot129.pdf)

### Inferences
- The commonly quoted 0.1 to 0.5 mm scan-to-Class-A band couldn't be confirmed from a primary public source. Treat it as folklore unless a programme spec is found.
- For a game-mesh rebuild the binding limit is the data, not the tools. Vertices are exact, the interior is uncertain by up to the sag, and normals are good to about 0.2 to 0.5 degrees. Suitable metrics: vertex max/RMS (target 0.1 mm or less), held-out vertex RMS (for overfitting), signed mean bias over the crown (must be about 0, which catches fairing flattening), and the G1 angle at trimmed boundaries (0.2 degrees or less if we follow the Class-A style G1 figure).

### Gaps
- I found no primary, numeric deviation spec (OEM or vendor) for scan-to-Class-A body panels, and no published RE study of a low-poly (game) mesh with sub-mm results.
