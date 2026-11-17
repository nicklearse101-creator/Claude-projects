# Recolouring AC interior materials in their textures (numpy + Pillow)

Scope: recolouring fabric/cloth seats, Alcantara, leather, plastic dashboards and door cards, painted roll cages, carpet and headliner in Assetto Corsa textures while keeping weave, stitching, grain and baked AO; light-to-dark and dark-to-light; part-only recolour on shared textures; stitch/logo protection; interaction with txNormal, txMaps and detail textures. Web sources plus local read-only tests on installed cars (abarth500, ks_mazda_mx5_cup, adc_nissan_s14_kouki__420, adc_nissan_skyline_r32_sedan). Scratch scripts and image sheets are in `D:\ClaudeData\tmp\interior_recolour\` (`recol.py` = all methods, `run_tests.py`, `mask_test.py`, `extra_test.py`, `sheet_*.png`, `metrics.json`).

---

## Q1. Which colour transforms keep material detail best, including light-to-dark and dark-to-light?

### Takeaway
Work in OKLab and remap lightness: put the material's median lightness at the target's lightness and add the source's local lightness deviations back on top (scaled by a limited gain), with the target's hue and chroma scaled by local lightness. In tests on 11 real interior textures this hit the target colour almost exactly (mean ΔE_OK ≤ 0.5×10⁻² on every target) and kept the grain (high-pass correlation 0.81–0.99). Hue shift, GIMP Colorize, the Photoshop/W3C "Color" blend and plain Multiply all keep the source's brightness, so black seats cannot turn white or bright red with them. A linear-light ratio (pure Multiply idea) reaches the colour but blows dark sources' highlight specks up to chalky white.

### Cited Findings
- GIMP Colorize turns the layer into a greyscale image and tints it, "as if seen through coloured glass"; controls are Hue 0–1, Saturation 0–1, Lightness −1…+1, and picking a colour sets the sliders — [GIMP 2.10 docs: Colorize](https://docs.gimp.org/2.10/en/gimp-tool-colorize.html).
- GIMP's Colorize code takes the pixel luminance as HSL lightness (`lum = GIMP_RGB_LUMINANCE(r,g,b)`; L > 0: `lum = lum·(1−L)+L`; L < 0: `lum = lum·(1+L)`), then rebuilds the colour in HSL with the fixed hue and saturation. So output lightness = source luminance, and full saturation only appears where source luminance ≈ 0.5 — [GIMP 2.8 gimpoperationcolorize.c, via the earlier research note](https://sources.debian.org/src/gimp/2.8.18-1%2Bdeb9u1/app/gegl/gimpoperationcolorize.c); older version [GIMP 2.2 colorize.c](https://sources.debian.org/src/gimp/2.2.13-1etch4/app/base/colorize.c).
- W3C non-separable blend modes: `Lum(C) = 0.3R + 0.59G + 0.11B`; `Color(Cb, Cs) = SetLum(Cs, Lum(Cb))` (hue and saturation from the top colour, luminosity from the backdrop); `ClipColor` pulls out-of-range channels toward L — [W3C Compositing and Blending Level 1](https://www.w3.org/TR/compositing-1/) (formulas quoted in `D:\Claude\research_notes\Encrypted cars 2D livery painting\uv_layout_algorithms.md` Q4).
- No official Adobe formula for Photoshop Colorize or Color mode was found. A Unity forum poster says Photoshop uses 0.3R + 0.59G + 0.11B luminance (unofficial), and Adobe community users measured shifted grey values after Color blending — [Unity discussions: Hue, Saturation, Color and Luminosity blend modes](https://discussions.unity.com/t/hue-saturation-color-and-luminosity-blend-modes/688397); [Adobe community: Color blend mode question](https://community.adobe.com/t5/photoshop-ecosystem-discussions/question-about-color-blend-mode/m-p/12206824) (search-result summaries; pages not opened).
- OKLab (Ottosson): linear sRGB → LMS (M1 rows 0.4122214708/0.5363325363/0.0514459929; 0.2119034982/0.6806995451/0.1073969566; 0.0883024619/0.2817188376/0.6299787005) → cube root → Lab (M2 rows 0.2104542553/0.7936177850/−0.0040720468; 1.9779984951/−2.4285922050/0.4505937099; 0.0259040371/0.7827717662/−0.8086757660); inverse given too. L predicts perceived lightness far better than CIELAB in his tests, hue is close to the best tested spaces, and the stated uses include greyscale with perceived lightness kept and changing saturation without changing hue or lightness. OKLCh: C = √(a²+b²), h = atan2(b, a) — [Björn Ottosson: A perceptual color space for image processing](https://bottosson.github.io/posts/oklab/).
- Reinhard et al. 2001, "Color Transfer between Images" (IEEE CG&A 21(5):34–41, DOI 10.1109/38.946629): per channel, subtract the source mean, scale by the ratio of standard deviations, add the target mean, in the decorrelated lαβ space (often re-implemented in CIELAB) — [academia.edu listing](https://www.academia.edu/9445485/Color_Transfer_between_Images); [Brown CS129 colour-matching lab code](https://cs.brown.edu/courses/cs129/2020_Fall/labs/lab_colormatching/colormatch.py); [Overview of colour transfer, arXiv 2204.13339](https://arxiv.org/pdf/2204.13339) (secondary sources; the original paper was not opened).
- Target lightness limits, Unity: for non-metal painted surfaces "an albedo value below 0.2 is too dark and an albedo value above 0.8 is too bright", and a very dark albedo "causes an unusual lighting response" — [Unity Manual: Making believable visuals, Materials](https://docs.unity3d.com/es/2021.1/Manual/BestPracticeMakingBelievableVisuals5.html).
- Target lightness, rFactor 2 PBR guide (general PBR reference, not rF2-specific): rubber 0.031 linear / 53 sRGB; black acrylic paint 0.05 / 65 sRGB; white acrylic paint 0.8 / 230 sRGB; coloured paint 0.15–0.35 / 107–158 sRGB; natural silk fabric 0.35–0.55 / 158–194 sRGB; coal 0.04 / 59 sRGB; no value for leather or plastic — [Studio 397 docs: PBR – An Introduction / Authoring Guide](https://docs.studio-397.com/x/EgBDAg).
- Unity's "Dark Dielectric Materials" guide reportedly lists black leather at sRGB 35/36/38, black synthetic fabric 44/43/43, black dyed cotton 41/42/44, and black velvety fabric 38/37/38 (a Scribd copy gives 51/52/51, so the copies conflict); it says most guides recommend albedo 50–243 sRGB. **Search snippet only: the PDF could not be fetched** (old URL is dead) — [Unity Dark Dielectric Materials PDF](https://docs-alpha.unity3d.com/cn/2018.1/uploads/ExpertGuides/Dark_Dielectric_Materials.pdf); [Scribd copy](https://www.scribd.com/document/452618278/Dark-Dielectric-Materials-pdf).
- Local test: 8 methods × 5 targets (red 170/20/25, white 232/232/228, black 30/30/30, tan 176/132/88, blue 28/58/150) on 11 real interior textures. Sources included abarth500 Skin.DDS (dark leather, OKLab L 0.36), TEssuto.dds (cloth, L 0.56), Carpet.DDS, S14 leather_dark.dds (L 0.27), bride_alcantara_blue.dds (blue, R channel 0), cloth04_mgrey, R32 carpet_charcoal (L 0.25), MX-5 Cup alcnt.dds / leather.dds detail textures, the MX-5 Cup AO atlas seat region, and the roll-bar AO. Mean over sources (dE = OKLab distance of the output median from the target ×100; detail = std of 7×7 high-pass L, output/source; corr = high-pass correlation):

  | method | red dE / detail / corr | white dE / detail / corr | black dE / detail / corr |
  |---|---|---|---|
  | HSV hue shift (keep V) | 21.0 / ×1.00 / 1.00 | 50.6 / ×1.00 / 1.00 | 17.5 / ×1.00 / 1.00 |
  | GIMP Colorize | 13.3 / ×0.97 / 0.99 | 51.1 / ×1.04 / 1.00 | 16.7 / ×1.00 / 1.00 |
  | W3C "Color" blend | 7.3 / ×0.84 / 0.96 | 52.9 / ×1.00 / 1.00 | 16.6 / ×1.00 / 1.00 |
  | Multiply (src × T) | 29.7 / ×0.44 / 0.88 | 55.1 / ×0.92 / 1.00 | 10.0 / ×0.18 / 0.84 |
  | linear-light ratio T·Y/Y_med, roll-off | 3.9 / ×1.90 / 0.95 | 0.1 / ×1.57 / 0.78 | 0.0 / ×0.65 / 0.90 |
  | OKLab L multiply (L_t·L/L_ref) | 0.5 / ×1.18 / 0.99 | 0.2 / ×1.75 / 0.79 | 0.0 / ×0.66 / 0.90 |
  | OKLab L add (L_t + ΔL) | 0.4 / ×1.00 / 0.99 | 0.1 / ×0.85 / 0.81 | 0.0 / ×1.00 / 0.95 |
  | OKLab hybrid (gain = clamp(L_t/L_ref, 0.6, 1.8)) | 0.5 / ×1.18 / 0.99 | 0.1 / ×1.39 / 0.81 | 0.0 / ×0.66 / 0.91 |

  — [Local test: run_tests.py + metrics.json](file:///D:/ClaudeData/tmp/interior_recolour/run_tests.py)
- Seen by eye on the sheets: hue shift does nothing on neutral grey/black sources (most interior textures are neutral: abarth and MX-5 Cup textures had median chroma 0–3/255), and on the blue Alcantara it turns "white" into olive. GIMP Colorize and Color blend give dark maroon/navy from black leather, and khaki/grey instead of white from grey cloth. Linear ratio gives chalky white specks on red/blue from dark leather and from the noisy Alcantara (its highlight ratios reach about 3× the median). OKLab add looks most natural for black→white and for the noisy Alcantara. OKLab multiply/hybrid give stronger, slightly harsher grain, and the white target clips (oklab_mult clipped 33 % of texels, hybrid 17 %, add 10 %, linear ratio with roll-off 1 %) — [Local sheets: sheet_s14_leather_dark.png, sheet_abarth_cloth_TEssuto.png, sheet_s14_alcantara_blue.png](file:///D:/ClaudeData/tmp/interior_recolour/).
- Very dark sources carry little detail: R32 `common_leather02_nero_diffuse.dds` has only 5 distinct green levels (21–24/255, i.e. flat black). S14 `leather_dark.dds` has 98 levels (G p1/p50/p99 = 16/40/89), abarth Skin.DDS 58 levels, R32 carpet_charcoal 30 levels — [Local test: extra_test.py](file:///D:/ClaudeData/tmp/interior_recolour/extra_test.py).
- Normal-map "cavity" (negative divergence of the tangent normal's xy) on abarth Skin_NM.dds gives a plausible-looking leather grain on a flat red, but it hardly matches the baked diffuse detail (high-pass correlation −0.12; detail std 2.18 vs 3.83) — [Local test: extra_test.py, sheet_extra.png](file:///D:/ClaudeData/tmp/interior_recolour/sheet_extra.png).
- Speed on a 2048² texture (this PC, numpy): sRGB→OKLab 0.58 s, back 0.31 s (round-trip error 0.000/255), hybrid incl. a 12-step bisection gamut clip over the whole image 5.2 s, k-means mask 0.78 s — [Local timing](file:///D:/ClaudeData/tmp/interior_recolour/recol.py).
- The app's current `recolour_wheels` already does a sRGB-space shading ratio: `shade = clip(lum / p85(lum), 0.25, 1.15)`, `new = colour × shade` — [skingen.py lines 1926–1968](file:///D:/Claude/Claude-/ac-skin-generator/skingen.py).

### Inferences
- **Recommended transform ("OKLab lightness remap"):** float32 sRGB 0..1, region = the part's texels (Q3), weight w = material mask (Q2):
  ```python
  lab  = srgb_to_oklab(src);  t = srgb_to_oklab(T)            # T = target sRGB
  ref  = np.median(lab[region], 0)                             # material colour (use p90 of L for pure AO atlases, see Q4)
  g    = np.clip(t[0] / max(ref[0], 1e-3), 0.6, 1.3)           # detail gain: physical ratio, limited
  L    = softclip(t[0] + g * (lab[..., 0] - ref[0]), 0, 1)     # tanh shoulder within 0.08 of 0 and 1
  k    = np.clip(L / max(t[0], 1e-3), 0, 1.3)[..., None]       # darker texels -> less chroma (shadow)
  ab   = t[1:] * k + 0.5 * (lab[..., 1:] - ref[1:])            # keep half the source's own colour variation
  out  = oklab_to_srgb(gamut_clip(np.dstack([L, ab])))         # reduce chroma only (keep L, hue) until in sRGB
  res  = src * (1 - w) + out * w
  ```
  Tests used gain limits 0.6–1.8 (hybrid) and 1.0 (add). By eye, 1.8 is too harsh for black→white, so an upper limit of about 1.2–1.3 is a judgement call between the two tested settings, not a measured optimum. Expose it as a "texture strength" slider.
- **Why limit the gain:** dye changes albedo multiplicatively, so physically all variation scales with lightness (gain = L_t/L_ref; ×3.4 for black→white). But dark textures carry 8-bit/DXT quantisation and baked sheen that, scaled ×3, turn into chalky noise (seen with the linear ratio). Going light→dark, a gain of 0.6 or more keeps grain visible where pure physics would flatten it.
- **Target lightness clamp:** keep the target between about sRGB 30–50 (black) and 230–243 (white), per the PBR guides above. For white, also lower the target L until `L_t + g·p99(ΔL) ≤ 0.97`, so grain highlights have headroom: a white target at sRGB 232 clipped 10–33 % of texels.
- **Gamut clip speed:** do the bisection only on the texels that are out of gamut (usually a few %), not the whole image; that should bring the 5 s down a lot (not measured).
- **Flat or near-flat sources** (16×16 MAT_*.dds, flat roll-cage fills, R32 nero leather with 5 levels): there is nothing to keep, so fill with the target. In game, the normal map still lights the grain, because txNormal is untouched. Optionally multiply by a mild normal-map cavity (strength ≤ 0.5) for "dirt in the grain". It is plausible but not equal to a baked diffuse.
- **Hue shift and Colorize/Color blend** are only acceptable for coloured-to-coloured recolours of similar lightness (e.g. blue Alcantara → red). They should not be the default, since most AC interior textures are neutral grey/black.
- **Reinhard mean/std transfer** needs a target image. With a single target colour, it reduces to the remap above (mean → target, std scaled by the gain), so a separate implementation adds nothing.

### Gaps
- No official Adobe formulas for Hue/Saturation Colorize or the Color blend mode; only community reverse-engineering.
- The measured black leather/fabric albedos (Unity Dark Dielectric guide) could not be opened; values are from a search snippet and two copies disagree.
- All judgements are on 2D texture sheets. None of the recolours were checked in-game under AC lighting (Nik's in-game check is the real test, as with the CSP paint finish).

---

## Q2. How to keep stitching, logos, labels and other small contrasting details from being recoloured

### Takeaway
Use k-means (k = 4) in OKLab inside the part's texel region. Take the biggest cluster as "the material", and give each texel a soft recolour weight that falls off with distance from that cluster. Use full weight on chroma (a, b), a high weight for texels lighter than the material (white logos/labels), and a low weight for texels darker than it (AO creases are shading, not detail). On a stitched black leather and a Bride seat atlas this protected 100 % of the coloured stitches/pads and white logos and recoloured 100 % of the dark creases. Many stitches and logos are not in the material texture at all: they are separate alpha-tested decal materials and are protected for free.

### Cited Findings
- R32 sedan `common_leather02_nero_stitches_orange_double_diffuse.dds` (32×128 tile, black leather with baked orange double stitches): k-means on (0.4·L, a, b) found the stitch cluster (11 % share, a/b = 0.041/0.066). The mask excluded 10.9 % of texels, against 10.5 % with chroma > 0.05; 100 % of the 432 coloured stitch texels were protected. Masked red/white keep orange stitches; unmasked turns the stitches pink/white — [Local test: mask_test.py, sheet_masks.png](file:///D:/ClaudeData/tmp/interior_recolour/sheet_masks.png).
- R32 `BRIDEBLACKKOUKI.DDS` (1024² seat atlas with an "illest" logo, a RECARO badge, a buckle, a blue/purple harness pad and BRIDE lettering, 40 % UV coverage). Without the part's UV region, the biggest cluster was the unused black background (58 % share), so the mask must be computed inside the UV region. Inside it, the symmetric k-means mask protected all coloured (n = 11 873) and white-logo (n = 4 903) texels but recoloured only 21 % of dark neutral creases (n = 16 157). The asymmetric distance (L weight 0.12 below the material, 0.5 above, full a/b) recoloured 100 % of creases and still protected 100 % of logos and coloured parts — [Local test: mask_test.py / extra_test.py](file:///D:/ClaudeData/tmp/interior_recolour/extra_test.py).
- A simpler "distance from the median colour, threshold = median + 4·MAD" mask worked on the stitched tile (10.5 % excluded) but failed on the Bride atlas (0 % excluded): the multimodal dark seat makes the spread too large — [Local test: mask_test.py](file:///D:/ClaudeData/tmp/interior_recolour/mask_test.py).
- Kunos and mod cars often model stitches and logos as separate materials. MX-5 Cup: `INT_Seams` (ksPerPixelAT, Stitches.png) and `INT_Seam_Shift`. abarth500: `INT_cuciture_NM` (ksPerPixelAT, cuciture.DDS) and `INT_Logo_Airbag`. S14 mod Bride seat: `BRIDE_DECAL` (bride_decals_1.dds with alpha), `BRIDE_STROCHKA` (stitching, black.dds) — [Local probe: probe.py / mats.py](file:///D:/ClaudeData/tmp/interior_recolour/mats.py).

### Inferences
- **Mask recipe:** sample ≤ 20 000 texels of the region → k-means k = 4 (15 iterations, numpy) on (0.4·L, a, b) → main = largest cluster. Per texel: `d = sqrt((wL·ΔL)² + Δa² + Δb²)` with `wL = 0.12` if ΔL < 0 else 0.5; weight `w = 1 − clip((d − 0.035)/(0.035), 0, 1)`; then a 1 px Gaussian blur of w to avoid hard edges. This took 0.8 s on 2048².
- **Known failure cases:** a black logo on a light seat (darker-than-material neutral, treated as shading and recoloured); stitches the same colour as the material (nothing to protect anyway); perforation dots (darker, so recoloured, which is correct). Offer a "protect details" toggle and a preview of the mask overlay, so Nik can spot mistakes.
- Before masking, skip materials whose name/texture says decal, logo, stitch, seam, cuciture, strochka, label or badge (they are separate on many cars). Alpha-tested materials (ksPerPixelAT, `alpha_tested`) are usually stitches/decals.

### Gaps
- Not tested on light seats with dark logos, or on textures where the logo has the same hue as the material.
- No sim-modding tutorial describing automated stitch protection was found; the method is from these local tests only.

---

## Q3. Recolouring only the texels one part uses when its texture is shared

### Takeaway
It depends on how the texture is mapped. On **atlas** textures (UVs inside 0..1, e.g. Kunos `INT_Cockpit_OCC.dds`), the parts' UV triangles partition the texture cleanly: 0.0 % overlap on the MX-5 Cup. So a texel mask rasterised from the part's triangles (the app's `uv_coverage`) plus a 2 px bleed into unclaimed texels recolours exactly one part. On **tiled material** textures (UVs spanning many repeats, e.g. abarth TEssuto.dds used by both seat cloth and headliner, or S14 leather_dark.dds used by dash, door cards, console and steering rim), every user covers the whole texture. A skin texture then cannot separate the parts; only a CSP shader replacement that gives one material its own file can.

### Cited Findings
- MX-5 Cup `INT_Cockpit_OCC.dds` (512², neutral AO, alpha 0): 7 materials use it — Plastic_GREY 28.2 %, Carpaint 7.5 %, SkinShift 0.2 %, Alcantara 7.3 %, Skin_GREY (seat leather) 12.6 %, a carbon WIP 0.6 %, Plastic_Detail 1.4 % of the atlas; texels claimed by more than one material 0.0 %, by none 42.2 %. Seat-leather mask 12.6 % → 16.0 % after 2 px dilation, with 0.00 % hitting other parts. Recolouring that region red left all other parts untouched — [Local test: atlas.py, extra_test.py, mx5cup_atlas_seat_red.png](file:///D:/ClaudeData/tmp/interior_recolour/mx5cup_atlas_seat_red.png).
- abarth500 tiled textures: `TEssuto.dds` 256² used by `INT_Zona1_tessuto` (seat cloth) and `INT_Tessuto_soffitto` (headliner), UV span −3.9…17.8; `Skin.DDS` 256² used by `INT_Skin`, `INT_Logo_Airbag` and as txDetail of the shift boot, UV −28.9…30.8; `MAT_Plastica_Grigia.DDS` 16² used by 4 materials — [Local test: dump.py](file:///D:/ClaudeData/tmp/interior_recolour/dump.py).
- S14 mod: `leather_dark.dds` (1844²) is the diffuse of 7+ materials (dash structure, door cards, centre console, parcel shelf, steering rim `SUPRA_INT_STEER_RIM`) — [Local test: mats.py](file:///D:/ClaudeData/tmp/interior_recolour/mats.py).
- A scan of installed cars shows mod cars mostly build interiors from small tiled material textures (cloth_brightgrey, leather_dark, carpet_grey, common_alcantara01_black_diffuse, each with a normal map), while Kunos-style cars use AO atlases plus tiled detail textures — [Local test: scan.py](file:///D:/ClaudeData/tmp/interior_recolour/scan.py).
- CSP shader replacement: `MATERIALS = …` / `MESHES = …` select targets, `SKINS = …` limits it to listed skins (cars only), `RESOURCE_N = txDiffuse` + `RESOURCE_FILE_N = custom.dds` (file next to the config) or `RESOURCE_COLOR_N = r, g, b` (1×1 solid texture), `PROP_N = ksAmbient, 0.4` sets properties; MATERIALS is preferred over MESHES (each mesh gets its own material, more GPU calls). Giving one material of a shared texture its own file this way is implied but not stated explicitly — [CSP docs: Shader replacements](https://cup.acstuff.club/docs/csp/general/shader-replacements).
- A modder on GTPlanet notes that ext_config can change shaders on a single material or mesh and make it skin-specific — [GTPlanet AC mods thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4580) (search-result summary).

### Inferences
- **Detect the mapping type per part:** if the part's UVs span more than about 1.05 in u or v (`np.ptp(m.uv, 0)`), or the texture is tiny (≤ 128²), treat it as tiled. Recolouring it affects every material using that texture, so list those materials/meshes to Nik ("leather also changes: steering rim, door cards"). Otherwise build the texel mask: `uv_coverage(part_meshes, size)` at texture resolution, dilate 2–3 px (`rank_filter(..., 5, 'max')`) but only into texels no other material claims (prevents mip/DXT bleed seams without touching neighbours).
- Make the per-part texture in the skin folder only when the texture is an atlas. For tiled shared textures, the honest options are: (a) recolour the whole material class (all leather), or (b) a CSP `SHADER_REPLACEMENT` per material in the skin's ext_config with `RESOURCE_FILE_0` pointing at the recoloured copy (CSP-only; vanilla AC ignores it). Where the skin itself is the target, `SKINS = <skin>` keeps it per skin. Untested here.
- Skins override kn5 textures by file name, so the recoloured texture goes into the skin folder under the same name (as the app already does for body/wheels). Never write into the kn5.

### Gaps
- Whether a skin-folder `ext_config.ini` (rather than `extension/ext_config.ini` in the car) is read by CSP was not confirmed.
- Not verified in-game that a CSP RESOURCE_FILE replacement on one material of a shared texture leaves the other material on the original.

---

## Q4. Interaction with txNormal, txMaps (specular/gloss/reflection) and detail textures

### Takeaway
Leave txNormal and txMaps alone. Grain lighting comes from the normal map, and specular strength/sharpness/reflection come from txMaps (R/G/B), neither of which depends on dye colour. With a detail texture (ksPerPixelMultiMap with useDetail = 1), the visible colour is roughly diffuse × detail (community description). So either recolour the detail texture, which changes every material using it, or recolour the AO atlas region with the detail's darkening compensated. Kunos interiors (MX-5 Cup) are exactly this: a neutral AO atlas times tiled grey detail textures (leather.dds mean 71/255, alcnt.dds 134/255).

### Cited Findings
- txMaps channels (forum consensus): red = specular intensity, green = gloss/sharpness (very sensitive at the low end), blue = reflection intensity; to go from a broad soft highlight to a small sharp one, raise both red and green — [Overtake: txSpecular – how it works?](https://overtake.gg/threads/txspecular-how-it-works.276528) (search-result summary; page returned 403 when fetched); [assettocorsamods: ksPerPixelMultiMap how textures are made](https://www.assettocorsamods.net/threads/ksperpixelmultimap-how-textures-are-made.3478).
- CSP's `stPerPixelMultiMap_specular` (Stereo) adds a txSpecular map for highlight colour and can keep AO in txMaps' alpha; `ksPerPixelMultiMap_emissive` adds a txEmissive colour mask — [CSP sdk-shaders README](https://www.github.com/ac-custom-shaders-patch/sdk-shaders).
- Detail blending (community, not official): diffuse and txDetail combine like a Multiply, controlled by the diffuse alpha; the detail colour only fully shows where the diffuse is white, and diffuse alpha must be black where the detail should show — [assettocorsamods: txDetail with ksPerPixelMultiMap](https://assettocorsamods.net/goto/post?id=20528) (quoted in the earlier research note). The exact formula in Kunos/CSP shader code was not found (the acc-shaders GitLab doc pages returned no shader logic).
- MX-5 Cup materials on the atlas: Skin_GREY/SkinShift use detail `leather.dds` + `leather_nm.dds` (×40); Alcantara uses `alcnt.dds` + `alcnt_nm.dds` (×40); Plastic uses `PlasticDetail.dds` (flat 93/255, ×40); Dash uses `MAT_Dash_Fiber` (×200); Carpaint uses `metal_detail.dds` (×50). The atlas alpha is 0 everywhere, so the detail shows fully. Detail means: leather 71, alcnt 134, PlasticDetail 93 (neutral). txMaps medians per part: leather R23 G129 B23, Alcantara R29 G167 B29, plastic R31 G177 B31, carpaint R46 G218 B46 — [Local test: atlas.py](file:///D:/ClaudeData/tmp/interior_recolour/atlas.py).
- `INT_OCC_Carpaint` uses `metal_detail.dds` (the body-paint detail, red in the kn5; skins ship their own). abarth500 `INT_Plancia` (dashboard) also uses `metal_detail.dds` as detail, and the abarth skin `black_red` ships `MAT_plancia.dds` + `metal_detail.dds`. Body-coloured interior panels therefore follow the body colour automatically — [Local test: probe.py](file:///D:/ClaudeData/tmp/interior_recolour/probe.py).
- Mod cars mostly use `ksPerPixelNM_UVMult` with a tiled diffuse + tiled normal (e.g. S14 leather_dark + leather02_rough_normals, cloth04_mgrey + cloth07_normals), no detail — [Local test: mats.py](file:///D:/ClaudeData/tmp/interior_recolour/mats.py).

### Inferences
- **What to edit, per shader:**
  - `ksPerPixel*`/`*_UVMult` with a coloured tiled diffuse: recolour the diffuse (Q1).
  - `ksPerPixelMultiMap*` with useDetail = 1 and a neutral AO atlas: the reference level is the *unoccluded* AO (p90 of L in the region), not the median. Set the AO-atlas target to `T / detail_mean` (per channel, linear light) so that atlas × detail ≈ T. Where that exceeds 1 (detail too dark, e.g. leather.dds at 0.28 linear-ish), also recolour/brighten the detail texture. That affects all parts using it (leather.dds = seats + shift boot), which is usually fine since they are the same material.
  - Detail = `metal_detail.dds`: it is body colour; leave it unless Nik wants the interior panels different from the body.
  - Keep `txMaps` unchanged. A dye change does not change gloss or reflectance in the real material, and on a white seat the same specular simply shows less contrast. Do not darken txMaps when going dark.
  - Keep `txNormal` unchanged; it carries the grain under all colours.
- The physically-motivated split for flat sources (Q1) relies on this: txNormal gives the grain in game, so a flat recolour is acceptable.
- Verify the diffuse × detail assumption in game on one Kunos car before relying on the compensation maths.

### Gaps
- Exact ksPerPixelMultiMap formula (detail × diffuse vs lerp by alpha, any ×2 factor) not confirmed from shader source.
- Meaning of the detail textures' alpha (leather.dds mean alpha 99, alcnt 176) not found.

---

## Q5. Roll cages: painted metal recolour with specular kept; carbon/aluminium must stay

### Takeaway
Roll cages usually have their own material and texture, so a cage recolour rarely needs masks. On mod cars it is often a small flat colour texture (S14: `car_paint_roll_cage.dds`, 200² flat red) that many mod skins already ship per skin: just fill it with the new colour. On Kunos cars it is an AO-only texture with its own txMaps and a scratches detail (MX-5 Cup `INT_RollBar_OCC.dds`): recolour by shading ratio from the unoccluded level and keep txMaps. Carbon and aluminium are separate materials/textures; exclude them by texture/material name and by "no paint colour".

### Cited Findings
- S14 mod: `Material #805` (ksPerPixelMultiMap, Diffuse = `car_paint_roll_cage.dds`, Maps = `map.dds`, Detail = `metal_detail.dds` ×50) and `Material #806` (ksPerPixel, same diffuse) on `rollcage_sub1/4`. The texture is 200×200, uniform 238/28/33 (L 73/73/73 at p5/p50/p95). Padding (`rollcage_sub3`) is a separate material — [Local test: dump.py / mats.py](file:///D:/ClaudeData/tmp/interior_recolour/dump.py).
- Installed-car scan: `car_paint_roll_cage.dds` sits in the first skin folder of 19 ADC mods (adc_bmw_e92_m3_low__420, adc_datsun_510__420, adc_datsun_sunny_ute__420, adc_ford_fpv_ute__420, adc_ford_mustang__420, adc_holden_vy_ute__420, adc_lexus_is200_xe-10, adc_mazda_fc__420, adc_mazda_mx5__420, adc_mazda_rx7__420, adc_nissan_350z__420, adc_nissan_s13.4__420, adc_nissan_s13__420, adc_nissan_s14_dsa__420, adc_nissan_s14_kouki__420, adc_nissan_s15__420, adc_nissan_silvia_s13_luke_v, adc_nissan_skyline_r32__420, adc_toyota_cresta__420), and `rollcage_metal_detail.dds` in actk_citroen_ax_proto skins, `rollcage.dds` in adc_bmw_e46__420 skins — [Local test: scan.py](file:///D:/ClaudeData/tmp/interior_recolour/scan.py).
- A GTPlanet modder: most or all skin folders (of a given mod) have their own rollcage texture colour, interior paint texture colour, gear knob colour and team logo texture — [GTPlanet AC mods thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4580) (search-result summary).
- MX-5 Cup: `INT_OCC_White_Paint` (ksPerPixelMultiMap) on `GEO_Rollbar` with Diffuse = `INT_RollBar_OCC.dds` (512², neutral AO, covers 63 % of it), Maps = `INT_RollBar_OCC_MAP.dds` (median R80 G188 B80), Detail = `scratches2.dds` (mean 240, ×10) — [Local test: atlas.py](file:///D:/ClaudeData/tmp/interior_recolour/atlas.py).
- Aluminium/carbon examples are separate: S14 `BRIDE_RELSA` (aluminium01_light.dds), `BRIDE_BOLT` (brushedalu2.dds); MX-5 Cup carbon uses `MAT_Carbon.dds` detail; abarth `INT_Metallo_*` materials — [Local test: mats.py](file:///D:/ClaudeData/tmp/interior_recolour/mats.py).

### Inferences
- Find the cage by material/mesh/texture name (`cage|roll|rollbar|bar_|gabbia|käfig|arceau`), confirm it is a painted material (not `carbon|alu|chrome|steel|metal(?!_detail)` and not a txDetail-only reference), and recolour only its txDiffuse:
  - flat texture (std < 6/255, the same test as `recolour_wheels`): fill with T;
  - AO texture: `out = T × AO / p90(AO)` in linear light, with the Q1 remap for the grain;
  - leave txMaps, scratches detail and txNormal as they are, so the paint keeps its gloss and scratches.
- If the cage diffuse is `metal_detail.dds` itself (body-colour cage), recolouring it would recolour the body. Offer "same as body" vs "own colour" (own colour needs a CSP replacement, see Q3).
- Very bright targets on a cage: keep ≤ ~sRGB 230 (white acrylic paint 230 sRGB per the S397 table, Q1).

### Gaps
- Kunos cage textures were only checked on the MX-5 Cup; other Kunos race cars may bake the cage into the main interior atlas, which would need the texel mask from Q3.

---

## Q6. Seat belts and harnesses

### Takeaway
Belts are their own material and texture on both Kunos and mod cars, with the buckles/hardware in separate metal materials. Treat them as a separate, optional "belts" colour (default: leave as stock), recolour the webbing texture with the same OKLab remap, and never touch the hardware materials.

### Cited Findings
- MX-5 Cup: `INT_SeatBelts` (ksPerPixelNM, `Cockpit_Belt.png` 128×256 + `Cockpit_Belt_NM.png`) on `CINTURE_OFF/ON` and the LOD cockpit; UV span 1.0 × 8.6 (tiled along the strap); hardware on `INT_Decals_Plastic_Balck_REF` (INT_Decals_Metal.dds) — [Local test: mats.py / atlas.py](file:///D:/ClaudeData/tmp/interior_recolour/atlas.py).
- abarth500: `INT_Cintura` (ksPerPixel, `Cockpit_Belt.DDS` 128×256, neutral grey L50 85) on CINTURE meshes; S14 mod: `cloth_strap01.dds` (64², dark) for seat belts — [Local test: probe.py / dump.py](file:///D:/ClaudeData/tmp/interior_recolour/probe.py).
- Some mods ship belt textures per skin: `Belt.dds` in adc_bmw_e46 skins; ac_friends_honda_nsx_gt3_evo has `Belt_OMP_Colour.dds` (brand-coloured harness) — [Local test: scan.py](file:///D:/ClaudeData/tmp/interior_recolour/scan.py).

### Inferences
- Belts often carry brand logos/labels (OMP, Sabelt) and coloured stitching. Use the Q2 mask, and be careful with low-contrast labels; skipping belts by default is safest.
- Belt meshes are found by names like `belt|cintur|harness|gurt|ceinture|strap` (the app already has similar regexes for lights).

### Gaps
- No sim-racing guide on harness recolouring was found; findings are from the local car files only.

---

## Q7. References from sim modding and 3D texturing practice

### Takeaway
Web sources specific to AC interior recolouring are thin. Community practice is "edit the interior textures the skin folder carries in GIMP/Paint.NET and save as DDS", with per-skin roll cage/interior/gear-knob textures on many mods and CSP ext_config for per-material or per-skin changes. No rFactor 2 or iRacing interior-painting guide with a colour method was found; PBR albedo charts give the useful numbers for target lightness.

### Cited Findings
- GTPlanet AC mods thread: textures are DDS files in the car/skin folder referenced by name; back up skins before applying an interior update; skin folders carry their own rollcage/interior paint/gear knob/team logo textures; skinners edit in Paint.NET or GIMP, and the slow part is making 2D stickers and compressing PNG to DDS — [GTPlanet AC mods thread (search summary)](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4545).
- A downloadable Recaro seat pack for AC includes textures and a video on fitting the seats (an alternative to recolouring: swap the seat) — [itch.io: AC – Recaro seats](https://shiftclub.itch.io/ac-recaro-seats) (search-result summary).
- Studio 397's PBR guide gives general albedo/roughness tables (Q1), but nothing on rF2 cockpit/seat customisation — [Studio 397 docs](https://docs.studio-397.com/x/EgBDAg).

### Inferences
- The method in Q1–Q6 follows standard texturing practice: a neutral "material" layer (grain, AO) tinted by a colour layer, with normal and gloss maps left alone. The local tests are the evidence that it works on AC's actual textures, so the in-game check matters more than further web sources.

### Gaps
- No RaceDepartment/OverTake/YouTube interior-painting tutorial with a concrete colour method was found (OverTake pages returned 403). No Substance Painter documentation was fetched, so "tint a neutral base" is presented as general practice, not a cited Substance workflow.
