# Algorithms for painting a car livery directly on a 2D texture layout (numpy + Pillow only)

Scope: segmenting an Assetto Corsa body texture (DDS, panels on a flat background, baked shading) into UV islands, recognising which island is which, recolouring with the shading kept, laying patterns and logos across islands, and using a Content Manager AO bake as a template. Constraint: numpy + Pillow only (no scipy/OpenCV).

Local evidence used throughout: two read-only probe scripts were run on three Talbot Sunbeam body textures (`CRT-Kris\body.dds` 2048² DXT5, `Talbot MessDraw #16\body.dds` 2048², `ratty_s\body.dds` 4096² downsampled to 2048) from `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6\skins\`. Scripts and label previews are in `D:\ClaudeData\tmp\uvseg_test\` (`uvseg_probe.py`, `uvseg_probe2.py`, `*_labels.png`, `*_rgb.png`). Nothing in the game folder was modified.

---

## Q1. Segmenting a body texture into UV islands (connected components, morphology, background detection)

### Takeaway
Run-based connected-component labelling with a vectorised union-find (the same machinery the app already uses in `enclosed()`) labels a 2048² texture in about 0.4 s in pure numpy; with a border-modal background colour, a threshold of ~10, a 1-px close+open, and per-island hole filling it cleanly finds the Talbot's islands. It fails on a painted skin whose paint is as dark as the background, so the mask should come from a template/AO bake or from the union of several skins, not from the skin being painted.

### Cited Findings
- Run-based labelling groups consecutive foreground pixels of a row into runs, gives each run a provisional label, and merges runs that overlap runs in the previous row with union-find (find = root lookup, union = merge); this is the standard "run-length + union-find" CCL family, reported up to 35 % faster than other run-length algorithms on real datasets in one paper — [MDPI Algorithms 18(6):344](https://www.mdpi.com/1999-4893/18/6/344); [Lacassagne et al., ICIP 2015 (LIP6)](https://largo.lip6.fr/~lacas/Publications/ICIP15.pdf); a Rust reference implementation with path compression and union-by-rank plus a second pass writing each run's label back is in [locus-core segmentation.rs](https://docs.rs/crate/locus-core/0.4.0/source/src/segmentation.rs). (These were seen as search summaries; the numpy specifics below come from the local code, not from these sources.)
- The app already contains a numpy run-based 4-connected labeller: `enclosed()` extracts runs with `np.diff` on a padded mask, finds overlapping runs in the row above with two `np.searchsorted` calls on keys `row*big+start` / `row*big+end`, joins them by repeated `np.minimum.at` + pointer jumping (`lab = lab[lab]`), and paints runs back with a cumulative-sum "mark" array — [skingen.py lines 559-590](file:///D:/Claude/Claude-/ac-skin-generator/skingen.py).
- Generalising that function to full labelling needs only (a) an overlap pad of 1 px for 8-connectivity (`lo = searchsorted(ke, prev_row_key + s - 1, 'right')`, `hi = searchsorted(ks, prev_row_key + e + 1, 'left')`) and (b) `np.unique(lab, return_inverse=True)` then `np.repeat` to write labels per run. Implemented and run as `label()` in the probe; labelling plus 18 islands' features took 0.4-0.6 s per 2048² texture — [Local probe uvseg_probe.py](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- Background is not always black: `CRT-Kris` has modal border colour (0,0,0) (99 % of border pixels), `Talbot MessDraw #16` has (36,36,36) (100 % of border); both have exactly 60.8 % of pixels equal to the background, i.e. the same UV coverage (39.2 %) — [Local probe output, uvseg_probe.py](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- Threshold sensitivity is low on a clean skin: on `CRT-Kris`, pixels within 0/4/8/16/32 of the background colour were 60.8/62.3/63.5/64.2/65.2 % — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- With threshold 10, raw 8-connected labelling of `CRT-Kris` gave 60 components; after a 1-px closing then 1-px opening (shift-based dilate/erode) it gave 32, of which 10 are ≥2000 px. `MessDraw` gave 7 components, all ≥2000 px. The large islands were: one top view (bonnet+roof+hatch, 14.6-15.1 % of texture), two side islands (8.1-9.1 % each), one rear/tailgate island (2.5-3.8 %), and thin vertical strips (bumper/valance parts) — [Local probe + label preview](file:///D:/ClaudeData/tmp/uvseg_test/CRT-Kris_labels.png).
- Painted black lettering, numbers and black panels become "background": in `CRT-Kris` the number "713", the sponsor text and the windscreen area left holes in the islands; filling holes per island (label the complement 4-connected, keep only complement components that touch the bbox border) filled 18,815 px of holes in each side island and 115,750 px in the top view (the latter includes real window openings) — [Local probe 2](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe2.py).
- On `ratty_s` (a mostly black livery), 83.7 % of pixels equal the black background and segmentation broke into 304 raw / 359 cleaned components with no clean side or top island — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- DXT compression leaves measurable 4×4 blockiness: mean horizontal gradient on 4-px block boundaries vs inside blocks was 1.34× (`CRT-Kris`), 1.15× (`MessDraw`) — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py); BC1/DXT1 stores each 4×4 block as two RGB 5:6:5 endpoints plus 2-bit indices (four colours per block), DXT5/BC3 adds a separate alpha block with two 8-bit endpoints and 3-bit indices — [Wikipedia: S3 Texture Compression](https://en.wikipedia.org/wiki/S3_Texture_Compression).
- Pillow reads DXT1/DXT3/DXT5 (RGBA mode), DX10, BC5, ATI1/ATI2 and uncompressed DDS, and since 11.2.1 can save DXT1, DXT3, DXT5, BC2, BC3 and BC5 (`im.save(out, pixel_format="DXT1")`); BC7 is not listed as readable or writable — [Pillow image file formats: DDS](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html).

### Inferences
- Recommended mask pipeline (all numpy): (1) background colour = modal colour of the 1-px border (`np.unique(border, axis=0, return_counts=True)`), never assume black; (2) `fg = max(|rgb - bg|) > 10` (also OR with `alpha < 250` only if the alpha channel is known to be a mask, since AC diffuse alpha often carries detail/reflection data); (3) 1-px close then 1-px open to bridge DXT edge cracks and drop specks; (4) 8-connected `label()`; (5) drop components < ~0.05 % of the texture or attach them to the nearest big island; (6) per-island hole fill (complement components not touching the island's bbox edge).
- Best source for the mask, in order: a Content Manager AO bake or UV-wireframe export of the car (see Q7); the union of non-background masks over all skins installed for the car (each skin leaves different parts dark, so the union recovers coverage; the Talbot has 13 skin folders); the stock/lightest skin; the skin being edited only as a last resort.
- Hole filling should be stored as two masks: `island` (raw coverage) and `island_filled`. Paint into `island_filled` (filling windows/holes is harmless because those texels are unused or hidden), but measure seams/coverage on `island`.
- Thresholding must happen on the decoded DDS; a 1-px close is enough for DXT1/5 artefacts on the Talbot. A 2-px close risks merging islands that sit 2-4 px apart (the strips on the Talbot are 20-60 px wide with small gaps).

### Gaps
- No published numpy-only (scipy-free) CCL reference implementation was found; the method is validated only by the local probe.
- Only one car's layout (Talbot, two UV variants) was tested; layouts that split doors, bumpers and wings into separate islands were not tested.

---

## Q2. Recognising which island is which, and its orientation, from shape features

### Takeaway
On the Talbot layout three shape cues identify the panels reliably: (1) a global mirror axis of the whole foreground (IoU ≈ 0.87-0.90 about a horizontal line); (2) mirrored pairs found by flipping one island's mask and computing IoU (0.93-0.99), with Hu invariant I7 having opposite signs for the pair; (3) exactly two deep notches (wheel arches) on one long edge of each side island, which marks the sill edge and the wheel positions. The top view is the largest island that is self-symmetric about the global axis. Which end is the front is not reliably decidable from shape alone, so the app should guess and ask the user to confirm with one click.

### Cited Findings
- Image moments: raw `M_pq = ΣΣ x^p y^q I(x,y)`, centroid `(M10/M00, M01/M00)`, central moments `μ_pq`, orientation `θ = ½·atan2(2μ'11, μ'20 − μ'02)`, covariance eigenvalues `λ = (μ'20+μ'02)/2 ± ½√(4μ'11² + (μ'20−μ'02)²)` (elongation = √(λ1/λ2)), scale-normalised `η_ij = μ_ij / μ00^((i+j)/2+1)` and the seven Hu invariants; I1-I6 are unchanged by reflection while I7 changes sign under reflection, so it can distinguish mirror images — [Wikipedia: Image moment](https://en.wikipedia.org/wiki/Image_moment).
- Measured features of the Talbot islands (`CRT-Kris` / `MessDraw`): top view 1446×672 bbox, aspect 2.15-2.17, fill 0.64-0.65, θ ≈ 0°, self-symmetry IoU UD 0.89-0.90 vs LR 0.43-0.44; side islands 1585×503, aspect 3.15-3.19, fill 0.43-0.49, θ ≈ ±3-4°, elongation 4.4-4.6, self-symmetry UD 0.31-0.34; rear island 370-450 × 617-627, UD self-symmetry 0.98-0.99; thin strips aspect 4-26 with UD self-symmetry 0.93-1.00 — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- Mirrored pairs: the two side islands match best after a vertical flip (flipUD IoU 0.93 on `CRT-Kris`, 0.99 on `MessDraw`, 0.88 on the black `ratty_s`), versus 0.31-0.49 unflipped; their log-Hu I1-I4 values agree to about ±0.06 and their I7 signs are opposite (+1/−1) in all three textures; their PCA angles are equal and opposite (+3.8°/−3.8°, +3.1°/−3.1°) — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- Global layout symmetry: the whole foreground of both 2048² Talbot skins mirrors about the horizontal line y = 1031.0 with IoU 0.895 (`MessDraw`) and 0.871 (`CRT-Kris`), found by scanning candidate axes and maximising `Σ fg[r] & fg[c−r]` — [Local probe 2](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe2.py).
- Wheel-arch notch detector: for each bbox edge, depth to the first island pixel per column/row (after hole filling); runs of depth > 18 % of the island's other dimension longer than 6 % of the edge are notches. Both side islands gave exactly 2 notches on the edge facing the global axis and 0 on the other three edges (e.g. upper side: bottom edge notches at x 121-383 and 1157-1426 of 1575; lower side: top edge at 120-383 and 1157-1426), while the top view gave 0 on every edge — [Local probe 2](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe2.py).
- The Blender add-on LiveryHelper advertises that a livery element can be "mirrored on the other side of the car automatically" (it works on the 3D model) — [Blender Extensions: Livery Helper](https://extensions.blender.org/add-ons/livery-helper/).

### Inferences
- Classification recipe (works for the Talbot; untested elsewhere):
  1. Find the global mirror axis (scan horizontal and vertical candidates; keep the one with the higher IoU, accept if IoU > ~0.75).
  2. Pair islands: same area within 8 %, then compare one mask with the other flipped about that axis (IoU > 0.85) and confirm opposite I7 sign. Pairs straddling the axis are left/right parts.
  3. Unpaired islands whose own self-symmetry about the global axis is high (IoU > 0.85) are centre-line parts: the largest = top view (bonnet/roof/boot), others = front, rear, bumpers, valances.
  4. Among pairs, the pair with 2 arch notches on one long edge is the body sides; that edge is the sill (down). Arch notch centres give the wheel positions in texture space (useful for number placement and for registering the two sides, see Q5).
  5. Orientation along the length: PCA θ gives the length axis; its sign ambiguity is resolved by the sill edge for sides. Front vs rear: no robust cue was found (overhangs were 120 vs 148 px, too close; skew of the length profile was ±0.05). Guess (e.g. bonnet scoop hole / smaller glass hole) and ask the user once ("Is the front on the left?"), then store the answer per car.
- Which side is left vs right needs the same one-time confirmation, or a preview render; shape alone cannot tell (the islands are exact mirrors).
- If the global mirror axis is weak (layouts with sides packed side-by-side or rotated 90°), fall back to pair matching with all four flips (same, flipLR, flipUD, rot180), which the probe already computes.
- Small parts (mirrors, handles, badges) are best left unclassified as "small parts" and painted with the body colour.

### Gaps
- No paper or tool was found that classifies car panels from a 2D UV atlas image (see Q3); the rules above are derived from one car and need testing on more layouts (e.g. Kunos cars, cars with separate door/wing islands, layouts rotated 90°).
- Front/rear and left/right cannot be inferred reliably from shape only; no source found that solves this without the 3D mesh.

---

## Q3. How existing tools and research handle panel detection on texture atlases

### Takeaway
No livery tool or paper found does automatic panel recognition from the flat texture image. Real tools either use the 3D mesh (Blender add-ons, Content Manager's Paint Shop / Custom Showroom) or ship hand-made layered templates (wireframe + AO + masks) that painters use by eye. The app's image-only approach is therefore new ground, and a "template" (AO + wireframe) export from Content Manager is the closest the community gets to automatic masks.

### Cited Findings
- Mesh-side island detection: a Blender commit adds a `UVIslands` class that grows islands by triangles sharing UV edges, i.e. islands are computed from mesh connectivity, not pixels — [bf-blender-cvs, May 2022](https://lists.blender.org/pipermail/bf-blender-cvs/2022-May/173582.html).
- Pixel-side overlap checks in engines rasterise each triangle's covered texels and look for repeated indices — [Unreal Engine forum: removing UV overlap](https://forums.unrealengine.com/t/automatically-removing-uv-overlap-if-generated/2058031).
- A 2026 arXiv paper on atlas-based 3D asset segmentation projects per-view segmentation labels into the UV atlas (from 3D to 2D, the reverse direction) — [arXiv 2606.17824](https://arxiv.org/pdf/2606.17824) (seen in a search summary only, not read in full).
- Template workflow in other sims: BeamNG's guide describes screenshotting the 2D texture/UV layout, removing the background so only wireframe body panels are left, and painting over it — [BeamNG skin tutorial](https://documentation.beamng.com/modding/materials/vehicle/skinsystem/skintutorial).
- Flight-sim paint kits are layered source files (e.g. PSD) with editable layers and mapping information rather than flat textures — [FlyAwaySimulation: aircraft paint kits](https://flyawaysimulation.com/ask/answers/aircraft-paint-kits-flight-simulator/).
- Trading Paints' Paint Builder documentation covers layer finishes and spec maps (metallic/roughness/clearcoat; spec MIP must be generated by iRacing), not panel detection — [Trading Paints help: finish of Paint Builder layers](https://help.tradingpaints.com/paint-builder/changing-the-finish-of-paint-builder-layers/); [iRacing: Custom Spec Maps](https://www.iracing.com/?p=245837).
- MSFS Livery Tools (Python, GitHub) packages liveries, creates texture maps from glTF and converts to DDS via texconv — again mesh-based — [leandroarndt/msfs_livery_tools](https://github.com/leandroarndt/msfs_livery_tools).
- CSP's Custom Showroom Paint Shop uses fixed file names such as `metal_detail_skin_<X>.dds` for car skin fills (solid fills, X 2-8) — [CSP docs: default names for Paint Shop](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom).

### Inferences
- Since every established tool relies on the mesh or a human-made template, the app should treat auto-recognition as a best guess shown to the user (coloured overlay with labels "Top", "Left side", "Right side", "Front", "Rear", "Small parts") with click-to-fix, rather than as a silent decision.
- The app's existing 3D path (`render_view`, texel→3D maps) remains the gold standard for unencrypted cars; the 2D path is a fallback for encrypted kn5s.

### Gaps
- Trading Paints / iRacing official templates and any automatic masking in their tools were not found in documentation.
- No open-source GitHub project doing image-only UV island classification for car liveries was found.

---

## Q4. Recolouring a panel while keeping baked shading/AO

### Takeaway
Use a "shading ratio" recolour: estimate the panel's reference paint colour, compute per-pixel shading `S = Lum(pixel) / Lum(ref)`, and output `target × S` (with a screen-like roll-off where S > 1 so highlights stay). This is Multiply generalised to non-white bases; GIMP Colorize and the W3C/Photoshop "Color" mode are alternatives but both tie the result's lightness to the base's lightness, so they turn a dark target pale on a white car unless the luminance is remapped. Very dark (black) base paint has too little shading information (and DXT 5:6:5 quantisation) to recolour cleanly.

### Cited Findings
- W3C Compositing and Blending Level 1 formulas (Cb = backdrop, Cs = source, 0..1): Multiply `Cb×Cs`; Screen `Cb + Cs − Cb×Cs`; Overlay = HardLight(Cs, Cb); HardLight `Cs ≤ .5 ? Cb×2Cs : Screen(Cb, 2Cs−1)`; SoftLight `Cs ≤ .5 ? Cb − (1−2Cs)·Cb·(1−Cb) : Cb + (2Cs−1)·(D(Cb) − Cb)` with `D(Cb) = Cb ≤ .25 ? ((16Cb−12)Cb+4)Cb : √Cb`; non-separable `Lum(C) = 0.3R + 0.59G + 0.11B`, `SetLum(C,l)` adds `l − Lum(C)` to each channel then `ClipColor` (pull channels toward L if any < 0 or > 1); `Color(Cb,Cs) = SetLum(Cs, Lum(Cb))`, `Luminosity(Cb,Cs) = SetLum(Cb, Lum(Cs))`; results are clamped to range — [W3C Compositing and Blending Level 1](https://www.w3.org/TR/compositing-1/).
- Photoshop's Color mode "preserves the luma of the bottom layer, while adopting the hue and chroma of the top layer", in a hue/chroma/luma space that is different from HSL and HSV; Overlay = `2ab` if a < 0.5 else `1 − 2(1−a)(1−b)` (a = base); Pegtop soft light `(1−2b)a² + 2ba` is smooth at b = 0.5, while Photoshop's piecewise soft light has a local-contrast discontinuity — [Wikipedia: Blend modes](https://en.wikipedia.org/wiki/Blend_modes).
- GIMP Colorize (GEGL `gimp:colorize`): per pixel `lum = GIMP_RGB_LUMINANCE(r,g,b)`; if lightness L > 0: `lum = lum·(1−L) + L`; if L < 0: `lum = lum·(1+L)`; then HSL→RGB with the fixed hue and saturation and `hsl.l = lum`; alpha copied. A source comment says an earlier multiply-by-luminance step in the legacy code was a bug — [GIMP 2.8 gimpoperationcolorize.c](https://sources.debian.org/src/gimp/2.8.18-1%2Bdeb9u1/app/gegl/gimpoperationcolorize.c). GIMP docs describe Colorize as rendering the layer as a greyscale image seen through coloured glass — [GIMP docs: Colorize](https://docs.gimp.org/en/gimp-tool-colorize.html).
- Assetto Corsa detail-multiplied paint (community sources, no official Kunos doc found): AC combines txDiffuse and txDetail under control of the diffuse alpha, behaving like a Multiply layer, so detail colour only fully shows where the diffuse is white; diffuse alpha must be black where detail should show; Kunos street cars change colour by swapping a small detail texture; for complex liveries one modder suggests a white txDetail with all colour in txDiffuse; metal_detail alpha controls specular falloff (mostly black with white specks for metal flake) — [assettocorsamods: txDetail with ksPerPixelMultiMap](https://assettocorsamods.net/goto/post?id=20528); [assettocorsamods: ksPerPixelMultiMap how textures are made](https://www.assettocorsamods.net/threads/ksperpixelmultimap-how-textures-are-made.3478); [Cimmerian AC conversion guide](https://cimmerian.gitbook.io/assetto-corsa-conversion/changing-the-car-look/making-the-car-look-good). Sources partly conflict on whether detail alpha or diffuse alpha is the main blend control.
- The default Kunos AO texture is reported to be the AO bake with the green channel full white — [Overtake AC modding questions thread](https://overtake.gg/threads/ac-modding-questions-thread.129295/page-116) (forum claim).
- BC1/DXT1 colour endpoints are RGB 5:6:5 (5 bits red/blue, 6 bits green) — [Wikipedia: S3TC](https://en.wikipedia.org/wiki/S3_Texture_Compression).
- On the Talbot skins, side-panel luminance spans p5 ≈ 8 to p95 ≈ 207 with median ≈ 75 (painted liveries, so this mixes paint and shading) — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).

### Inferences
- Shading-ratio recolour (recommended default; numpy, float32, values 0..1):
  ```python
  L   = 0.299*r + 0.587*g + 0.114*b                     # or W3C 0.3/0.59/0.11
  ref = np.percentile(L[panel], 75)                      # paint colour level on lit, unshadowed areas
  S   = L / max(ref, 0.04)                               # shading/AO factor, 1 = fully lit paint
  out = T * np.minimum(S, 1)[..., None]                  # Multiply part (shadows, AO)
  hi  = np.clip(S - 1, 0, None) / max(S[panel].max() - 1, 1e-3)
  out = out + (1 - out) * hi[..., None]                  # Screen-like roll-off for highlights
  ```
  where `T` is the target RGB. With a white stock car (ref ≈ 1) this is exactly Multiply; with mid-grey stock paint it behaves like Overlay with mid-grey as neutral; with coloured stock paint the hue is discarded because only luminance enters S.
- W3C "Color" mode with luminance remap, for when the user wants the exact target hue and lightness: `out = SetLum(T, Lum(T) × S)` (ClipColor handles overflow). Plain Color mode (`SetLum(T, Lum(base))`) or GIMP Colorize keep the base's brightness, so navy on a white car comes out light blue; GIMP Colorize also maps mid-grey (lum 0.5) to the fully saturated colour and white to white, so the target colour is reproduced only where base lum equals the target's HSL lightness.
- Edge cases:
  - Very dark base (black or dark-green stock paint, ref < ~0.1): S is computed from few 8-bit levels and DXT 5:6:5 steps (8/255 in R and B), so scaling to a bright target amplifies banding and block noise. Smooth S with a small box blur (numpy cumulative-sum box filter) and cap S at ~1.5, or better, take S from an AO bake (Q7) instead of the skin.
  - Very light base: Multiply is exact; highlights clip at 1 (fine).
  - Coloured stock paint: compute S from luminance only (never per-channel division), otherwise the old hue leaks into shadows.
  - Painted logos/stripes in the base skin: they lower or raise S locally and will "ghost" through the new colour; detect them as outliers of S (e.g. S < 0.35 or strong chroma difference from the panel median) and replace S there with a blurred neighbourhood value, or warn that the base is not a clean template.
- For AC cars whose body paint comes from a detail texture (diffuse = grey AO, alpha black where the detail shows), a plain colour change may not need any 2D painting: write a solid `metal_detail` fill and leave the diffuse alone. Livery work goes into txDiffuse with a white detail, per the community advice above.

### Gaps
- No official Kunos/CSP documentation of the exact ksPerPixelMultiMap blend formula was found; only forum descriptions.
- Exact GIMP luminance weights (`GIMP_RGB_LUMINANCE` macro) were not shown on the fetched page; GIMP 2.x used Rec. 709 weights (0.2126/0.7152/0.0722) as far as I know, but that is not verified here.
- Adobe's own blend-mode help page returned HTTP 403, so Photoshop formulas come from the W3C spec and Wikipedia.

---

## Q5. Laying a 2D pattern across islands so it reads continuously

### Takeaway
Define one "car coordinate" frame (x along the car from front, y up from the sill, z across) and give every island a 2D affine map from car coordinates to texture pixels, built from its bbox/PCA axes and registered on features (wheel-arch centres for sides, bbox ends for top/front/rear). Patterns are then generated once in car space and sampled per island. For mirror-paired sides related by a vertical flip in the texture, geometric patterns map by the pure flip, but readable text/logos must be rotated 180° at the mirrored position, which is exactly what a hand-made, in-game-tested Talbot skin does.

### Cited Findings
- The two Talbot side islands are related by a vertical flip in texture space (flipUD IoU 0.93-0.99), have equal and opposite PCA angles (±3-4°), and their arch notches sit at the same x ranges (≈120-383 and 1157-1426 of a 1574-1575 px wide bbox) — [Local probes](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe2.py).
- In the `CRT-Kris` skin (made by a skinner and used in game) the racing number "713", the sponsor lettering and the BP/agv logos on the lower side island appear rotated 180° relative to the upper island, at vertically mirrored positions — [Local preview CRT-Kris_rgb.png](file:///D:/ClaudeData/tmp/uvseg_test/CRT-Kris_rgb.png).
- PCA/moment orientation gives the island's length axis (`θ = ½ atan2(2μ11, μ20 − μ02)`) — [Wikipedia: Image moment](https://en.wikipedia.org/wiki/Image_moment).
- LiveryHelper (Blender) mirrors livery elements to the other side automatically using the 3D model — [Blender Extensions: Livery Helper](https://extensions.blender.org/add-ons/livery-helper/).

### Inferences
- Per island store `A` (2×3 affine) such that `tex = A · [x_car, y_car, 1]`. For a side island: texture x axis ↔ car length (sign set by the front/rear answer), texture y ↔ height (sign set by the sill edge from the arch notches). Register x by least squares on the two arch centres (so the left and right sides line up even if their bboxes differ by a pixel or two) and y on sill/roof-line extremes.
- Pattern sampling: build the pattern as a function or a large image in car space, then for each island invert its affine and sample (`np` index arithmetic, nearest or bilinear) only inside `island_filled`. Stripes cross from side to top view continuously only if both islands use the same car-x scale; register the top view's x on its bbox ends against the side's overall length (bumper to bumper), and accept that the side/top boundary (roof gutter, sill) will not match pixel-for-pixel without the 3D model.
- Mirror rule for flipUD pairs: geometry/pattern content → same car coordinates, i.e. texture position flipped about the global axis (direction "forward" is preserved because x is unchanged). Text and logos that must read correctly from outside → place at the flipped position and rotate the decal image 180° (flipUD of the geometry plus a horizontal flip of the glyphs). For layouts paired by flipLR, the equivalent rule is position flipLR and decal rot180; derive it from the pair's best flip found in Q2.
- If the PCA angle of an island is small but non-zero (±3-4° on the Talbot sides), rotate the pattern by that angle rather than aligning to the bbox; otherwise long stripes visibly climb along the car.

### Gaps
- Continuity across island boundaries (side to bonnet, side to bumper) cannot be guaranteed without 3D data; no image-only source addresses this.
- Behaviour for layouts with non-uniform UV scale (stretched islands) was not tested.

---

## Q6. Placing logos/numbers by dragging on the texture view, and keeping them off seams

### Takeaway
Keep a per-island "distance to island edge" map (cheap with repeated 1-px erosion or a two-pass chamfer in numpy) and, while the user drags, show the island the logo's centre sits in, the fraction of logo alpha that falls outside the island or within a few pixels of its edge, and auto-mirror the logo to the paired island using the rules in Q5. Clip to the island mask on bake and pad edges afterwards.

### Cited Findings
- A distance transform labels each pixel with its distance to the nearest boundary/obstacle pixel, under Euclidean, taxicab (city-block) or Chebyshev metrics; exact Euclidean needs special treatment on a grid; Felzenszwalb & Huttenlocher's "Distance transforms of sampled functions" is the standard linear-time reference — [Wikipedia: Distance transform](https://en.wikipedia.org/wiki/Distance_transform).
- On the Talbot side island, 89 % (`MessDraw`) / 84 % (`CRT-Kris`) of island pixels are ≥10 px from an edge and 59 % / 50 % are ≥40 px from an edge (city-block via repeated erosion, after hole filling) — [Local probe 2](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe2.py).
- On the Talbot, each body side (doors, wings, quarter) is a single island; panel shut lines are drawn in the texture, not island boundaries — [Local label preview](file:///D:/ClaudeData/tmp/uvseg_test/CRT-Kris_labels.png).
- The app already pads painted colour into unowned texels with up to `reach` rounds of 4-neighbour copying, restricted to texels within `reach` of a painted texel (texture wraps at its edges) — [skingen.py pad_texture() lines 3152-3179](file:///D:/Claude/Claude-/ac-skin-generator/skingen.py).
- Padding/dilation extends island border colours outwards into the gutters so downsampled mips do not mix neighbouring shells; Unity's docs advise gutters at least double the edge padding; a rule of thumb is ~16 px at 1024² (2 px at the 128² mip) — [Adobe Substance 3D Painter: Texture dilation or padding](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/technical-support/workflow-issues/export-issues/texture-dilation-or-padding); [Unity 4.6 manual: alpha maps](https://docs.unity3d.com/462/Documentation/Manual/HOWTO-alphamaps.html); [Polycount discussion](https://polycount.com/discussion/comment/594563).

### Inferences
- Distance map in numpy: city-block via a two-pass raster scan is a Python loop (slow); faster in numpy is repeated erosion with shifted ORs (≈40 iterations of 4 slice operations on 2048² is well under a second), or a separable approximation with cumulative sums. Precompute once per car.
- Drag feedback: island id under the cursor = `label[y, x]`; `outside = Σ alpha·(label != id)` and `near_edge = Σ alpha·(dist < 6)`; colour the bounding box green/amber/red; optional snap = move the logo along the gradient of the distance map until `outside == 0`.
- Shut lines inside a side island (doors) show as thin dark lines in an AO bake; a ridge detector on AO (pixel darker than the median of a 9-px window by > 0.15) gives a "shut line" mask to warn when a number crosses a door gap.
- On bake: composite logos only inside `island_filled`, then run `pad_texture` (or equivalent dilation) with reach ≥ 8 px at 2048² so mips and DXT blocks at island edges do not pull in background colour; DXT blocks are 4×4, so a padding of at least 4 px is the minimum to keep each edge block single-coloured.
- Mirrored placement should be automatic but optional (numbers on both sides, sponsor on both sides), using the pair transform from Q2/Q5 (position mirrored, decal rotated 180° for flipUD pairs).

### Gaps
- No source specific to livery editors' seam-avoidance UX was found; the drag-feedback design is an inference.

---

## Q7. Detecting and using a "template" from a Content Manager AO bake

### Takeaway
Content Manager's Custom Showroom can compute an AO map for a texture (the "…" menu on txDiffuse, with a selectable resolution) and show/export the UV mapping (wireframe); these are what skinners use as templates. An AO image is near-greyscale with white = unoccluded and the unused area black/flat, so the same segmentation pipeline applied to it yields far cleaner islands than a painted skin, and its values are the shading factor S for recolouring. Reported quality is mixed (blocky squares, occasional black output).

### Cited Findings
- In CM's Custom Showroom you can create an AO map for a texture, export the texture or replace it on the car, and view the object's mapping; users report clicking the three dots on the txDiffuse texture, choosing "calculate AO" and a resolution; an Italian guide says to export the WIRE map and the AO map at the same size (e.g. 1024×1024) and overlay them in Photoshop — [Cimmerian AC conversion guide](https://cimmerian.gitbook.io/assetto-corsa-conversion/changing-the-car-look/making-the-car-look-good); [GTPlanet AC mods discussion](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4033) (community sources, partly machine-translated; these details came from a search-engine summary across several forum posts, and the exact post for each detail was not opened).
- A skinner used CM to generate AO layers at higher resolution than the car's template, but reports the AO is "very far from being perfect" with visible blocky squares affecting the base colour; another user got a black image from "calculate AO" while the mesh map still generated; CM-generated AO can show seams on the model — [Overtake: alternative ways to generate higher-resolution AO maps](https://www.overtake.gg/threads/alternative-ways-to-generate-higher-resolution-ao-maps.157626/) (page returned 403 to direct fetch; content from search summaries); [Overtake AC modding questions thread](https://overtake.gg/threads/ac-modding-questions-thread.129295/page-116).
- AC has no real-time AO in the base game, so modders UV-map meshes and bake AO into textures — [Cimmerian AC conversion guide](https://cimmerian.gitbook.io/assetto-corsa-conversion/changing-the-car-look/making-the-car-look-good) (search summary). For comparison, Studio 397's (rFactor 2, not AC) skin documentation asks for the AO bake at native 4096×4096 to be mixed into the skin — [Studio 397 docs](https://docs.studio-397.com/x/twct) (search summary).
- The default Kunos AO texture is reported to be the AO bake with the green channel set to full white — [Overtake AC modding questions thread](https://overtake.gg/threads/ac-modding-questions-thread.129295/page-116) (forum claim).

### Inferences
- Auto-detect "this image is an AO bake": channel spread small (`mean(max(rgb) − min(rgb)) < 6` over foreground), or exactly one channel near 255 everywhere (the Kunos green-channel quirk: then use the other channels), bimodal histogram with a large flat background, no saturated colours. Detect "this is a UV wireframe": very sparse thin lines (foreground < ~10 %, mostly 1-2 px wide after a 1-px opening removes almost everything).
- Using an AO bake: resize to the skin's size with `Image.BOX`/`LANCZOS` if needed; island mask = `AO > small threshold` → `label()` → hole fill; S (shading) = AO / percentile-95 of AO per island; recolour = `target × S` (Q4) and composite logos under or over the AO as the user chooses (AO over logos looks painted-on).
- Using a wireframe export: islands = regions enclosed by the outer contour of the line drawing, i.e. `enclosed(lines)` (existing function) then `label()`; interior triangle edges can be ignored after filling.
- Combine sources: final island mask = AO mask ∪ wireframe-enclosed mask ∪ union-of-skins mask, with AO preferred for shading.
- Warn on AO images whose foreground coverage differs strongly (>5 %) from the skin's foreground, which signals the AO was baked for another texture slot or UV set.

### Gaps
- Exact current CM menu names and the default background colour/alpha of CM's exported AO and wireframe images were not confirmed from an official source; a test export from CM on the user's PC is needed.
- Whether CM's AO export carries alpha or uses a black background is unknown.

---

## Q8. Pitfalls: seams, mirrored/overlapping UVs, padding/bleed, DXT artefacts

### Takeaway
The main traps are (1) dark paint being taken as background, (2) mirrored or stacked UVs where one texel region serves both sides (painting text there makes it read backwards on one side), (3) islands split by seams so one panel is several islands, (4) no padding at island edges, which lets background colour bleed in through mips and DXT blocks, and (5) DXT 4×4 blocks smearing colours across edges and quantising dark shading.

### Cited Findings
- Dark livery areas merge with a black background (84 % "background" on `ratty_s`; holes for black lettering on `CRT-Kris`) — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- Padding is the standard fix for mipmap bleeding at UV seams; gutters between shells should be at least twice the padding — [Adobe Substance 3D Painter: dilation/padding](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/technical-support/workflow-issues/export-issues/texture-dilation-or-padding); [Unity manual](https://docs.unity3d.com/462/Documentation/Manual/HOWTO-alphamaps.html); a GameDev.net post states the minimum padding equals the filter footprint at the coarsest mip used, scaled by 2^n at finer levels — [GameDev.net: UV maps with linear filtering](https://nene.gamedev.net/forums/topic/699809-uv-maps-with-linear-filtering-problem).
- Users report CM AO and UV transfers showing seams on the 3D object — [Overtake AC modding questions thread](https://overtake.gg/threads/ac-modding-questions-thread.129295/page-116).
- BC1/BC3 store one 4-colour palette per 4×4 block with 5:6:5 endpoints — [Wikipedia: S3TC](https://en.wikipedia.org/wiki/S3_Texture_Compression); measured block-edge gradient ratios 1.03-1.34 on Talbot skins — [Local probe](file:///D:/ClaudeData/tmp/uvseg_test/uvseg_probe.py).
- The app's `pad_texture` exists precisely because "the game blends neighbouring texels, so without this the old skin's colour shows as a line along door seams" — [skingen.py docstring](file:///D:/Claude/Claude-/ac-skin-generator/skingen.py).

### Inferences
- Overlapping/stacked UVs (both sides mapped to the same texels) cannot be detected from the image alone; symptoms are a missing mirror partner for a big side-like island. If a body side has no flipped partner, warn that text on it will read backwards on one side of the car and offer "symmetric designs only" for that island.
- Seam-split panels: neighbouring islands with matching edge profiles (e.g. a wing split from a door) can be grouped by checking whether their facing edges have matching shading along the boundary; simpler: let the user shift-click to group islands into one "panel".
- Thresholds must be applied before any resizing (resampling blurs the boundary); masks for a 4096² skin should be computed at 4096² or computed at 2048² and upsampled with NEAREST plus a 2-px dilation.
- When writing the result as DXT1/DXT5 via Pillow, run padding first (≥4 px) so every edge block contains only paint colours; also avoid pure-black (0,0,0) paint next to transparent texels in DXT1 mode, since DXT1's c0 ≤ c1 mode reserves an index for transparent black.
- Store the island map, pair transforms and the user's front/left answers per car (e.g. a JSON next to the app's car cache) so recognition runs once.

### Gaps
- No sources were found on automatically detecting stacked/overlapping UVs from a texture image alone.
- The DXT1 transparent-black behaviour of Pillow's encoder (whether it ever chooses the 3-colour mode) was not verified.
