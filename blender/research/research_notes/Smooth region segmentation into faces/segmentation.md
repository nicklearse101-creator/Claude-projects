# Segmenting a smooth, coarse low-poly region into designer faces and blends (AE86 C-pillar)

Scope: how reverse-engineering tools and the literature split a region with no sharp crease (dihedral < 20 deg) into primary faces, rolling/shoulder blends and transitions, and which methods still work when a face is ONE facet wide (the C-pillar top: ~45 mm, no interior vertex; shoulder ~75 deg total turn over ~30 mm in 2-3 facet rows; side face; deck flare at the foot; 455 tris over 1.1 m; single height-field fit misses by p95 2.4 mm).

Scratch copies of the papers read in full for this note are in D:\ClaudeData\tmp\research_cpillar (gelfand.txt, lavoue.txt, wu_kobbelt.txt).

## 1. What commercial RE tools do (Geomagic Design X, PolyWorks, Mesh2Surface, CATIA DSE, NX, PowerShape, Ansys) and which parameters they expose

### Takeaway
The vendors publish very little about their algorithms. Geomagic (Design X / Wrap / Studio) is the only one whose method can be traced. Its patent and the Várady/Facello/Terék papers describe a pipeline that classifies the mesh into "primary regions", "connecting features" (blends, whose centre line is a "smooth edge") and "vertex blends". It does this with curvature-based indicator functions, Morse-complex/watershed segmentation and one sensitivity value, not with dihedral thresholds. The settings users actually see are a single "sensitivity" (Design X), a "similarity angle" plus fitting tolerance (PowerShape), and curvature-angle and length limits (Ansys). I found no documentation of defaults or parameters for PolyWorks, Mesh2Surface, CATIA DSE or NX.

### Cited Findings
- **Design X Auto Segment:** one main control, "sensitivity". A practitioner (CATI) uses a low sensitivity of about 50-60 on the whole mesh so regions do not fragment. Under-segmented areas are then fixed with "Resegment" (higher sensitivity on chosen regions only) or with "Split", where you draw a line from one region edge to another to cut a region by hand — [CATI blog](https://www.cati.com/?p=126341)
- Design X regions are groups of triangles and points sorted into geometry classes; a flat area becomes a plane region, for example — [GoEngineer](https://www.goengineer.com/geomagic-design-x/)
- **Design X 2022** added a new Region Segmentation algorithm and a "CAD Tessellated Mesh" option, aimed at meshes tessellated from CAD. This is the closest vendor analogue to a game/Kunos mesh (large flat facets) — [Design X 2022 release notes](https://download.laserscanning-europe.com/Geomagic/GeomagicDesignX_ReleaseNotes_v2022.0.0.pdf)
- Automatic region segmentation is listed only in the top Design X tier — [MatterHackers listing](https://www.matterhackers.com/store/l/geomagic-design-x-software/sk/MQN1PQSV)
- **Geomagic pipeline (patent US8004517: Várady, Facello, Terék, Edelsbrunner, Gloth)** — [Google Patents US8004517](https://patents.google.com/patent/US8004517):
  - Objects are modelled as large functional "primary" surfaces joined by highly curved transitions ("connecting features") and vertex blends at junctions.
  - Indicator functions are piecewise linear and defined at mesh vertices.
  - The "translational" indicator is estimated from a neighbourhood of about 20-30 points per vertex. A least-squares plane is fitted through the origin to the normals on the Gauss sphere. Translational strength is high when the first eigenvalue is small and the second large.
  - The ratio of principal curvatures k1/k2 also indicates translation: near 1 means weak, large means strong.
  - Vertex-blend areas are where the principal-curvature ratio exceeds a threshold.
  - A 6x6 slippability matrix is listed as another indicator.
  - Segmentation is watershed-like on the Morse complex: one region per indicator maximum, cancellations ranked by persistence |f(u)-f(v)|. A single "sensitivity" threshold, user-set or computed from surface complexity, picks the level. The patent explicitly avoids global preset curvature thresholds.
  - "Separator sets" are grown from polylines until translational strength falls below a threshold (no value given), then thinned.
  - The feature skeleton is traced through the middle of separator sets (Runge-Kutta along the translational direction field).
  - **Blend boundaries ("thickening" a smooth edge):** the mid-curve sits at the cross-sectional MAXIMUM of a similarity indicator. The two boundaries sit at the two adjacent cross-sectional MINIMA of the same indicator. An alternative for rolling-ball features uses a spine curve plus a radius function.
  - Setbacks for vertex blends come from the maximum width of the adjacent edge features plus an optional positive correction.
  - Sharp edges are found separately: a multi-scale measure of how strongly the normals in a neighbourhood split into two clusters, compared with a threshold.
  - No numeric thresholds are given anywhere in the patent text.
- **Original paper:** Várady, Facello & Terék, "Automatic Extraction of Surface Structures in Digital Shape Reconstruction", GMP 2006, LNCS 4077, doi 10.1007/11802914_1. Keywords: segmentation, combinatorial Morse theory, curve tracing, vertex blends. The "feature skeleton" is a curve network on the mesh that represents the region structure — [Springer Professional](https://www.springerprofessional.de/automatic-extraction-of-surface-structures-in-digital-shape-reco/1224232). Full text not retrieved.
- **PowerShape "Segment Mesh"** exposes:
  - Similarity angle: lower values separate high-curvature regions on smooth meshes; higher values suit coarser meshes with stronger discontinuities.
  - Surface matching tolerance.
  - Primitive types, Extend primitives, Reclaim regions, fit inside/middle/outside.
  - No defaults stated.
  - [Autodesk PowerShape help](https://help.autodesk.com/cloudhelp/2022/ENU/PWRS-ReferenceHelp/files/GUID-17A3FEEA-751B-4FED-9BFC-5DC8BAAB7BE6.htm)
- **Ansys "Feature Detect Fillets"** exposes min/max fillet length, "min fillet curvature" (a curvature ANGLE in degrees), and relative tolerance (0.001 when disabled). Fillet length L = R x theta x pi/180 — [Ansys help v25.1](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/icm_help/igeom_featuredetectfillets.html)
- **Dassault "Fillet detection method"** patent: circles are fitted to a mesh segment. The segment is a fillet if and only if the mean circle-fitting error is below a first threshold, plus a radius-variance test. The mean radius parameterises the fillet — [Justia patent 20240135733](https://patents.justia.com/patent/20240135733)
- **Mesh2Surface (Rhino):** marketing only says "curvature based mesh segmentation" plus primitive extraction; no parameter documentation found — [Novedge listing](https://novedge.com/products/buy-mesh2surface-for-rhinoceros); [Mesh2Surface datasheet](https://cdn.shopify.com/s/files/1/0663/4245/3481/files/Mesh2Surface-Rhino-Rapid_Scan_3D.pdf)
- **PolyWorks Modeler:** reseller text says it extracts CAD entities from polygonal models and does curvature-based sampling while meshing; no segmentation parameters published — [Laser Design](https://www.laserdesign.com/?p=5114)

### Inferences
- Every vendor tool reduces segmentation to one scale knob: sensitivity, similarity angle, or curvature angle plus length. None of them is dihedral-per-edge. On a coarse mesh that knob behaves like "how much total normal turn per unit width counts as a transition". The "CAD Tessellated Mesh" mode in Design X 2022 is evidence that the defaults tuned for dense scans misbehave on big-facet CAD/game meshes, so a dedicated path is warranted.
- Ansys's L = R*theta and Dassault's "circle-fit error + radius variance" test give a cheap, implementable "is this a fillet?" check that needs only one cross-section polyline per station. Our shoulder: theta ~ 75 deg = 1.31 rad over L ~ 30 mm gives R ~ 23 mm.

### Gaps
- No public numeric defaults for Design X sensitivity (range, default) or its "CAD Tessellated Mesh" algorithm. The Pitt-hosted 2014 Design X user guide exceeded the fetch size limit (>10 MB) and was not read.
- No documentation found for PolyWorks, Mesh2Surface, CATIA DSE (Digitized Shape Editor) or Siemens NX reverse engineering segmentation parameters; these remain unverified.
- The FreeCAD wiki "Mesh Segmentation" page (curvature-based and best-fit segmentation, the closest tool in our own stack) was blocked by bot protection. Its parameters (curvature tolerances, minimum faces per segment) were not confirmed this session. Check FreeCAD's MeshCore source (MeshSegmentAlgorithm / curvature segment classes) locally.

## 2. Academic methods (Várady/Benkő/Martin, VSA and its blend variant, slippage, curvature clustering, primitive fitting, normal tensors) and which survive "one facet across"

### Takeaway
Methods that work on vertex neighbourhoods all assume tens of samples per face, so they break down when a face is one facet wide:
- slippage uses m = 30 vertices;
- the Geomagic indicators use 20-30 points;
- curvature-tensor k-means (Lavoué) classifies vertices.

Methods that cluster FACES do not need interior vertices:
- VSA and its hybrid version with rolling-ball blend proxies (Wu & Kobbelt);
- Attene's hierarchical primitive fitting;
- Lavoué's region merging, once a region graph exists.

For our C-pillar the most directly usable published recipe is Wu & Kobbelt's hybrid VSA (plane / sphere / cylinder / rolling-ball blend proxies). One caveat: its blend fitting uses about 30-barycenter windows along the spine, and the authors call blend finding/fitting a weak point.

### Cited Findings
**Várady school (point clouds / dense meshes)**
- Benkő & Várady, "Segmentation methods for smooth point regions of conventional engineering objects", CAD 36(6):511-523, 2004. Segmentation is easy when regions are bounded by sharp edges and small blends; it gets hard when smoothly connected regions must be separated. Three-phase direct segmentation using local geometric and statistical estimates (abstract-level only) — [Scilit record](https://scilit.com/publications/9d1cd2853f67d93b68f6c5d54b713ab5)
- Benkő, Martin & Várady, "Algorithms for reverse engineering boundary representation models", CAD 33(11), 2001. Pipeline: segmentation of point data into regions → translational/rotational surfaces with smooth constrained profiles → B-rep topology → blends added last — [search summary of Cardiff ORCA PDF](https://orca.cardiff.ac.uk/1811/1/REalgorithms.pdf). Full text returned HTTP 403, so details are unverified.
- Kós, Martin & Várady, "Methods to recover constant radius rolling ball blends in reverse engineering", CAGD 17(2):127-160, 2000 — [SZTAKI eprints record](https://eprints.sztaki.hu/2459/). Full text blocked (403); method details are unverified.
- Benkő, Kós, Várady, Andor & Martin, "Constrained fitting in reverse engineering", CAGD 19(3):173-205, 2002. Fits multiple surfaces while enforcing constraints, to reach CAD tolerances and reproduce regularities — [SZTAKI eprints](https://eprints.sztaki.hu/2967/)

**Slippage (Gelfand & Guibas, SGP 2004)** — [paper PDF](https://geometry.stanford.edu/lgl_2024/papers/gg-ssulsa-04/gg-ssulsa-04.pdf)
- Build a 6x6 matrix C = sum [c_i; n_i][c_i; n_i]^T with c_i = p_i x n_i. Centre the patch at its centroid and scale it to average radius 1 first.
- An eigenvalue lambda_j is "small" if lambda_6/lambda_j > g, with g = 100-300.
- Number of small eigenvalues: 3 for plane/sphere, 2 for cylinder, 1 for revolution/extrusion.
- Initial patches are m vertices crawled on the mesh; their examples use m = 30.
- Bottom-up merging uses a priority queue. Similarity = Gaussian F of the (k+1)-th singular value of the stacked signatures [X_1..k Y_1..k], times a confidence cutoff G that blocks patches larger than N from "dropping" a slippable motion.
- Multi-pass merging: k = 3 first (planes, spheres), then k >= 2, then k >= 1. The Gaussian is widened each pass.
- Post-processing: large regions absorb small ones; border points go to the MORE slippable region; one-slippable seam regions are thinned to at most 5 vertices wide.
- It finds a cylinder joining a plane smoothly with no sharp edge. Plane-cylinder joins come out as separate one-slippable components "which can be replaced by a surface blend" [BMV01].
- The method is most sensitive to m. Too small an m gives "essentially random" signatures and over-segmentation.

**Curvature-tensor clustering for CAD meshes (Lavoué, Dupont & Baskurt, CAD 37, 2005)** — [paper PDF](https://perso.liris.cnrs.fr/fdupont/publications/2005-CAD.pdf)
- Sharp edges are found by a dihedral threshold first.
- Triangles whose three vertices are all "sharp" are subdivided by adding a centre vertex ("mesh enrichment for badly tessellated CAD objects"); the added vertices are removed afterwards.
- Curvature tensor: normal-cycle method (Cohen-Steiner/Morvan), which can be averaged over a geodesic region.
- Vertices are clustered by k-means in (|Kmin|, Kmax) space; K is user-set and "not critical", e.g. 5 or 18.
- Triangle-based region growing, then region-adjacency-graph merging with D_ij = DC_ij x N_ij x S_ij:
  - DC_ij = |c_i - c_ij| + |c_j - c_ij|, where c_ij is the curvature of the BOUNDARY vertices. This separates regions with the same curvature but a significant boundary between them.
  - N_ij = min(P_i, P_j) / P_ij (perimeter nesting).
  - S_ij = 1e-5 if an area < A_min, else 1.
- Merging threshold 5 (Fandisk, Swivel) or 20 (Pawn), with objects scaled to bounding-box length 1. A region-growing threshold of 50 was also used.

**Variational Shape Approximation (CGAL implementation of Cohen-Steiner, Alliez & Desbrun 2004)** — [CGAL 6.1 Surface_mesh_approximation](https://doc.cgal.org/6.1/Surface_mesh_approximation/index.html); [CGAL class reference](https://doc.cgal.org/5.6/Surface_mesh_approximation/classCGAL_1_1Variational__shape__approximation.html)
- Planar proxies on FACES. L2,1 (normal deviation, default) or L2 metric.
- Seeding: hierarchical (default), random or incremental.
- Stop criteria: max_number_of_proxies (default num_faces/3 when neither criterion is given) and/or min_error_drop (default 0.1 in 5.x).
- Lloyd relaxation, proxy teleportation, anchor extraction. Chord subdivision is split at the furthest vertex; examples use subdivision_ratio 0.3.

**Hybrid VSA with rolling-ball blends (Wu & Kobbelt, Eurographics 2005, CGF 24(3):277-284)** — [paper PDF](https://graphics.rwth-aachen.de/publication/87/hybrid1.pdf)
- Each region fits plane, sphere, cylinder and blend B = (c(t), r); the type with the lowest energy wins.
- Progressive schedule: planes only until stable, then spheres and cylinders, then blends.
- L2 metric = (d1² + d2² + d3² + d1d2 + d1d3 + d2d3)|T|/6. Blend distance d = |dist(v, c(t)) - r|.
- L2,1 uses the proxy normal: g - c_perp for cylinders and blends. The radius cannot be found from normals alone, so fitting always uses L2.
- Cylinder axis = robust mean of min-curvature directions. If their deviation is too large, the region is "isotropic" and gets no cylinder. Barycenters are projected onto the plane normal to the axis and a 2D circle is fitted (Pratt).
- Blend fitting:
  - (1) fit a quadratic B-spline (at most 15 control points; end linearity constraints with large weight) through the face barycenters;
  - (2) for windows of m ≈ 30 barycenters sorted by foot-point parameter, project onto the normal plane and fit 2D circles;
  - (3) reject if the radius deviation Δr exceeds a threshold, else fit a B-spline spine through the circle centres with r = mean;
  - extrapolate the spine ends with tangent rays (infinite cylinders) so the region can grow.
- The authors list "finding the blend regions" and blend fitting as weak points needing heuristics.

**Hierarchical fitting of primitives (Attene, Falcidieno & Spagnuolo, Visual Computer 22(3):181-193, 2006)** — [CNR IRIS record](https://iris.cnr.it/handle/20.500.14243/52370); [EfPiSoft](https://efpisoft.sourceforge.net/)
- Every triangle starts as its own cluster. The adjacent pair that best fits a plane, sphere or cylinder is merged, giving a binary tree.
- The same error metric is used for all primitives.
- About 8 s for a 100K-face mesh.
- Open-source implementation: EfPiSoft.

**Normal-tensor feature classification**
- Normal voting tensor eigenvalues: one dominant = face, two = edge, three = corner — [Yadav et al. arXiv 1607.07427](https://arxiv.org/pdf/1607.07427)
- Normalised eigenvalue thresholds used in one CAD-mesh paper: corner if λ3 > 0.1, face if λ2 < 0.02, strong edge if λ2 > 0.1 and λ3 < 0.02 — [Stony Brook PG 2011 feature classification](https://www3.cs.stonybrook.edu/~qin/research/2011-pg-feature-classification.pdf) (thresholds as reported in the search summary, not re-read from the PDF)
- Feature-line extraction on CAD triangle meshes (Vidal, Wolf & Dupont, GRAPP 2011): tangent-plane region growing accepts a triangle if its normal is within 23 deg of the current plane. Scales are 4-28 % of the minimum bounding-box dimension (planes) and 1-17 % (curvature). It targets crest lines made of mesh edges, not fillet boundaries — [paper PDF](https://scitepress.org/Papers/2011/33617/pdf/index.html)

**Fillet segmentation on tessellated models**
- Di Angelo, Di Stefano & Morabito: secondary features (fillets, rounds, grooves, sharp edges) from principal-curvature analysis with fuzzy membership, because deterministic curvature thresholds proved unreliable; regions are grown from nodes matching a radius. Designed for HIGH-DENSITY tessellations — [Springer IJIDeM 2018](https://link.springer.com/article/10.1007/s12008-017-0426-8) (abstract via search; full text paywalled)
- DeFillet (SIGGRAPH 2025): rolling-ball centres found among Voronoi candidates of surface samples (osculating spheres) — [DeFillet project page](https://xiaowuga.github.io/pub/DeFillet.html)

### Inferences
- **Why vertex-based methods fail here.** The pillar top has two vertex rows and no interior vertex, so every top vertex is also a shoulder vertex.
  - Any per-vertex classification (curvature k-means, slippage with m = 30, Geomagic indicators over 20-30 points) gives the top face no vertices of its own.
  - A 30-vertex crawl on a 455-triangle, 1.1 m mesh spans roughly 150-300 mm, several times the pillar's whole cross-section, so the signatures would be "essentially random" (Gelfand's own warning).
  - Lavoué's fix for "three sharp vertices" triangles (insert a centre vertex) is the published precedent for giving one-facet-wide faces a sample of their own.
- **Face-based clustering survives.** A facet has exactly one normal, so VSA L2,1 and Attene-style merging can put a single facet strip into a plane (or ruled) proxy.
  - Plain planar VSA cannot represent the shoulder: it will either split the 2-3 shoulder rows into extra planes or absorb them into the top/side proxies.
  - Wu & Kobbelt's blend proxy is the right model, but its 30-barycenter windows must be replaced by per-station cross-sections. The shoulder has only about 2-3 facets across × N stations along.
- **Slippage at the right scale.** Slippage is still conceptually useful if applied per cross-section band rather than per vertex. A band of the pillar (top + shoulder + side over ~100 mm length) is close to an extrusion (1-slippable). A top-only or side-only strip is more slippable (planar, 3-slippable). The blend is the 1-slippable seam between them, which is exactly Gelfand's finding that plane-cylinder joins come out as separate one-slippable seams.
- **Developable/ruled patches.** A one-facet-wide strip is trivially a ruled surface between its two boundary polylines. So "top face = ruled/developable strip lofted between its two long edges" matches the data exactly. This fits the project's existing strip_build.py approach (ruled strips on shared edges).

### Gaps
- No full text was obtained for Benkő & Várady 2004, Benkő-Martin-Várady 2001, Kós-Martin-Várady 2000 or Várady-Facello-Terék 2006 (403, paywall or no PDF). Their exact tests and thresholds for separating smoothly connected regions are unverified.
- I found no published VSA variant that explicitly targets low-poly meshes with one-facet-wide faces.
- Segmentation into developable patches (e.g. Julius, Kraevoy & Sheffer's D-Charts) was not researched this session.
- The Stony Brook eigenvalue thresholds come from a search summary, not a re-read of the PDF.

## 3. Locating face/blend boundaries, estimating blend extent and radius from a few facet rows, and deciding "blend between two faces" vs "one curved face"

### Takeaway
The published consensus is to work across the feature, in cross-sections:
- the blend centre is where the normal-turn (curvature) indicator peaks;
- the two blend boundaries are where it falls back to its adjacent minima (Geomagic patent);
- the radius comes from circle fits to cross-sections, accepted only if fit error and radius variance are small (Dassault patent, Wu & Kobbelt), or from L = R*theta (Ansys).

"Blend vs one curved face" rests on three signals:
- strongly anisotropic curvature (k1/k2 large, translational);
- curvature concentrated in a narrow band between two low-curvature regions (Lavoué's boundary-curvature term);
- a single surface failing the fit tolerance.

### Cited Findings
- **Boundary placement:** mid-curve at the cross-sectional maximum of the indicator; boundaries at the two adjacent cross-sectional minima; a stabilisation term damps oscillation on noisy data; rolling-ball alternative = spine + radius function — [US8004517](https://patents.google.com/patent/US8004517)
- **Blend vs primary:** blend areas show low translational strength or exceed a curvature-ratio threshold; primary surfaces are the remaining low-curvature regions — [US8004517](https://patents.google.com/patent/US8004517)
- **Fillet acceptance test:** mean circle-fit error below a threshold AND a radius-variance test; mean radius = fillet radius — [Justia 20240135733](https://patents.justia.com/patent/20240135733)
- **Blend fitting (Wu & Kobbelt):** windowed 2D circle fits on planes normal to a fitted spine; reject the blend if Δr exceeds a threshold, else r = mean radius; the cylinder axis comes from min-curvature directions, with an "isotropic" rejection when they scatter — [Wu & Kobbelt 2005](https://graphics.rwth-aachen.de/publication/87/hybrid1.pdf)
- **Fillet length/angle/radius relation:** L = R x theta(deg) x pi/180; detection limits are set by a min curvature angle and min/max length — [Ansys help](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/icm_help/igeom_featuredetectfillets.html)
- **Separating same-curvature regions:** regions with the same curvature but a significant boundary are separated by comparing each region's curvature with the curvature of its boundary vertices (DC_ij term) — [Lavoué et al. 2005](https://perso.liris.cnrs.fr/fdupont/publications/2005-CAD.pdf)
- **Fit-test ordering:** Gelfand's post-processing assigns border points to the more slippable (simpler) region, letting planes eat into seams. Their seam regions were thinned to 5 vertices wide max — [Gelfand & Guibas 2004](https://geometry.stanford.edu/lgl_2024/papers/gg-ssulsa-04/gg-ssulsa-04.pdf)
- **Scale sensitivity:** both the Gelfand neighbourhood (m) and the Geomagic sensitivity set how wide a transition appears. A larger m widens one-slippable regions — [Gelfand & Guibas 2004](https://geometry.stanford.edu/lgl_2024/papers/gg-ssulsa-04/gg-ssulsa-04.pdf); [US8004517](https://patents.google.com/patent/US8004517)

### Inferences
These are concrete for our mesh, not taken from sources.

**1. The 1D cross-section turn profile is the right indicator on coarse meshes.**
- At each station along the pillar, intersect the mesh with the plane normal to the pillar's long direction. This gives a polyline across top → shoulder → side.
- For each polyline segment take the facet normal. For each crossed mesh edge record the turn angle Δφ_k (signed, about the station tangent) and the arc length s_k.
- The discrete curvature is κ_k ≈ Δφ_k / (half-width of the two adjacent segments). This is the coarse-mesh version of the patent's "indicator across the feature".
- Blend centre = argmax κ. Blend boundaries = the adjacent local minima, or better the points where cumulative turn reaches about 5 % and 95 % of the bend's total turn.
- Use hysteresis on κ to stop single noisy edges from splitting faces:
  - high threshold to start a blend, e.g. κ > 1/(3 R_expected);
  - low threshold to end it, e.g. κ < 1/(10 R_expected).
- These thresholds are my suggestion; no source gives numbers.

**2. Radius from the turn.** Our shoulder turns 75 deg (1.31 rad) over about 30 mm, so R ≈ 30/1.31 ≈ 23 mm (Ansys L = Rθ). Cross-check with:
- (a) a 2D Pratt/Kasa circle fit to the shoulder polyline VERTICES at each station (vertices lie on the designer surface, facet midpoints do not);
- (b) the normal-based centre fit: each vertex p_i with unit normal n_i satisfies p_i − R·n_i = c. That is linear in (c, R), so 3 equations per vertex and 4 unknowns (2D: 2 per vertex, 3 unknowns), solvable with numpy lstsq. Two or three vertex rows across give 6-9 equations per station, enough. Pool several stations of a constant-radius blend for robustness.
- Accept a constant-radius blend if the circle-fit RMS is below 0.3-0.5 mm and the radius CV across stations is below about 15-20 % (my suggested values, in the spirit of the Dassault/Wu-Kobbelt tests). Otherwise use a variable-radius blend (spine + r(t)).

**3. Facet sag explains much of the current error.** Chord sag on a 23 mm radius is R(1 − cos(θ/2)):
- a 37.5 deg facet (two rows over 75 deg) sags about 23 × (1 − cos 18.75°) ≈ 1.2 mm;
- 25 deg facets (three rows) sag about 0.55 mm.

Any surface fitted to facet barycenters or dense facet samples will sit about 0.5-1.2 mm inside the true shoulder. Fit blends to vertices (and vertex normals), never to sampled facet interiors. This is consistent with a single height field missing by p95 2.4 mm.

**4. Blend vs one curved face: decision rule.** Call the bend a BLEND between two faces if all of these hold:
- (i) the turn is concentrated: the blend width w_b = s_end − s_start is less than about 1/2 of both adjacent face widths, and the adjacent faces' own κ is below about 1/5 of the blend's peak κ;
- (ii) the curvature is anisotropic along the pillar (the turn profile repeats station to station with slowly varying R and direction; k1/k2 large);
- (iii) top ∪ shoulder ∪ side fails a single-surface tolerance (we already know it does: 2.4 mm), while top, side and the blend each fit within about 0.3-0.5 mm.

Otherwise, at the deck flare at the foot, where the turn spreads over many rows and becomes doubly curved, treat it as one freeform face. Here the patent's "vertex blend / curvature-ratio" logic applies: where k1/k2 falls toward 1, the translational blend ends and an n-sided vertex-blend or setback region begins.

**5. Practical numpy pipeline for the pillar.**
- (a) Pick the pillar long axis (PCA of the region, or the existing feature curve).
- (b) Slice at stations every 20-30 mm.
- (c) Build the turn profile per station and find the blend boundary points with hysteresis.
- (d) Fit smooth B-spline curves through the boundary points along the length. These are the face/blend boundary lines. This is the patent's "trace boundaries left and right of the stable centre".
- (e) Assign facets wholly between the lines to top, shoulder or side. Split straddling facets by the boundary curve (trim) rather than by facet.
- (f) Fit the top and side as ruled or low-degree B-spline faces to their boundary polylines and vertices. Fit the shoulder as a rolling-ball blend (spine + r(t)) from per-station circle fits, or as a G1 blend built from the top and side faces with the measured setback.
- (g) Optionally run a few Wu-Kobbelt-style Lloyd iterations (reassign facets to the proxy with the lowest L2 error, refit) to relax the boundaries.

### Gaps
- No source gives numeric curvature, turn or width thresholds for "blend vs face"; the hysteresis, CV and RMS numbers above are my suggestions and must be tuned on the AE86 data.
- The Kós/Martin/Várady 2000 comparison of rolling-ball radius-recovery methods could not be read (403). That is the paper that would rank the radius estimators (spine/offset, normal-line intersection, cross-section circles) on real data.

## 4. Methods that use per-vertex normals (vs facet normals) for segmenting game / CAD-export meshes

### Takeaway
Most published segmentation methods use either estimated normals or facet normals:
- slippage takes point + normal pairs, from mesh normals or plane fits;
- VSA L2,1 uses facet normals;
- the Geomagic translational indicator uses normals on the Gauss sphere.

I found no method designed around authored per-vertex normals of game meshes. Since slippage and Gauss-sphere indicators only need (point, normal) samples, a coarse mesh's smooth vertex normals can stand in for the missing samples, with caution.

### Cited Findings
- Slippage needs only points and normals. With connectivity, normals are estimated from the incident triangles; without it, from plane fits (MNG04). The 6x6 matrix is built from (p × n, n) — [Gelfand & Guibas 2004](https://geometry.stanford.edu/lgl_2024/papers/gg-ssulsa-04/gg-ssulsa-04.pdf)
- Geomagic's translational strength comes from a least-squares plane fit through the origin to the normals mapped on the Gauss sphere (small first and large second eigenvalue = strong translation) — [US8004517](https://patents.google.com/patent/US8004517)
- VSA's L2,1 metric uses facet normals; the best normal proxy is the area-weighted average normal — [CGAL 6.1 docs](https://doc.cgal.org/6.1/Surface_mesh_approximation/index.html)
- Wu & Kobbelt compute L2,1 with facet normal n_T against the proxy normal at the facet barycenter. For spheres and cylinders the radius cannot be recovered from normals alone, so they fit with L2 positions — [Wu & Kobbelt 2005](https://graphics.rwth-aachen.de/publication/87/hybrid1.pdf)
- Vidal et al. use, among 43 features, the angle between the unit VERTEX normals of the two vertices opposite an edge, and the vertex-normal variation of Lee & Lee 2002 — [Vidal, Wolf & Dupont 2011](https://scitepress.org/Papers/2011/33617/pdf/index.html)
- Normal voting tensors classify face/edge/corner from eigenvalues of normal outer products over a neighbourhood — [arXiv 1607.07427](https://arxiv.org/pdf/1607.07427)

### Inferences
**1. Gauss-sphere test per region with vertex normals.** For a candidate region, stack its unit vertex normals and take the SVD of the 3xN matrix, a numpy one-liner.
- One dominant direction (normals clustered) = plane.
- Normals on a great circle (smallest singular value small, the other two large) = extrusion or cylinder or blend; the null direction is the blend's spine direction.
- This needs no neighbourhood crawl and works with 6-10 normals, which is what one station of top + shoulder + side gives.

**2. Vertex normals give the circle centre directly.** The (c, R) least-squares fit from p − R·n = c (Section 3) uses vertex normals. It is the coarse-mesh version of the rolling-ball/osculating-sphere idea behind DeFillet and Kós et al.

**3. Caveat on authored normals.** On a smooth-shaded Kunos mesh, a vertex on the top/shoulder seam carries an AVERAGED normal: it belongs to neither the top face nor the blend. Mitigations:
- use facet normals to classify faces;
- use vertex normals only for (a) the turn profile (they give a smoother κ) and (b) the blend-centre fit, excluding seam vertices whose normal is far from both the top-face proxy and the fitted circle normal;
- check whether the kn5 has split normals (duplicated positions with different normals) along the pillar. If so, the artist's smoothing groups already mark the face boundaries; that is an inference about game-mesh authoring, not a sourced fact.

**4. Per-face curvature from vertex-normal differences** (Rusinkiewicz-style: fit a 2x2 second fundamental form per triangle from the normal differences along its three edges) gives curvature inside a one-facet-wide face, which vertex-only methods cannot. This is from background knowledge; it was not verified as a source this session.

### Gaps
- No source specifically addresses segmentation of game/real-time meshes using artist-authored vertex normals or smoothing groups.
- Rusinkiewicz (2004) per-face curvature from vertex normals was not fetched and is cited from background knowledge only.
- Mean-shift clustering of normals on meshes was not covered by any source retrieved this session.
