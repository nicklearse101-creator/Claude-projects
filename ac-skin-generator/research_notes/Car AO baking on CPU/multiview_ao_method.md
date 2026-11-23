# Multi-view depth-map (shadow-map) AO baking on CPU with numpy

Scope note: web search found NO source describing exactly "numpy depth maps from N directions into texture space". Sourced facts below come from GPU Gems ch.17 (the canonical shadow-map AO method), Adobe Substance Bakers docs, Unity Asset Transformer docs, Polycount/xNormal snippets and the numpy issue tracker. Items under "Inferences" are my arithmetic or judgement; the z-buffer benchmark in section 4 was measured locally (numpy 2.5.4, this PC).

## 1. Number of directions N and direction distribution

### Takeaway
Standard practice (GPU Gems) is 128-1024 directions, uniformly distributed on the sphere (not a lat/long grid), averaged in a float accumulator; a hemisphere/dome suffices when the object stands on a plane. 256 is a sensible CPU default; 128 is the practical floor for smooth results, and a bilateral filter lets you go lower.

### Cited Findings
- GPU Gems ch.17: good results need "128 to 1024" lights (shadow maps); distribute them uniformly on the sphere, not as evenly spaced polar coordinates which cluster at the poles. — [GPU Gems ch.17](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)
- Same chapter: for an object standing on a plane a dome/hemisphere of lights is enough; results are averaged in a floating-point accumulation buffer (16-bit half float may lack precision when summing bent-normal vectors); bent normal = sum of (light dir x visibility), normalised. — [GPU Gems ch.17](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)
- GPU Gems baking to texture: unwrap the mesh using the UV coordinate as screen-space position and render occlusion into that layout (the GPU analogue of the texel-to-3D-point approach). — [GPU Gems ch.17](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)
- Substance Bakers "Ambient Occlusion from Mesh": default 64 secondary rays, default distribution Cosine (suited to shading) vs Uniform (suited to masking), default spread angle 180. — [Adobe Substance 3D Bake docs](https://experienceleague.adobe.com/en/docs/substance-3d/bakers/bakers-settings/ambient-occlusion-from-mesh)
- Unity Asset Transformer AO bake: `samples` accepts powers of two 8..4096 (example uses 32); blue-noise-distributed error in texture space so quality is "good even with quite a few samples"; then an edge-preserving filter (three Gaussians on texel position, AO value, normal; example sigmaPos=2, sigmaValue=0.2, sigmaNormal=0.2). — [Unity docs](https://docs.unity.com/en-us/asset-transformer-sdk/2026.4/manual/functions/bakeao.md)
- xNormal guidance (secondary sources, opinion): default ray count too low; one tutorial suggests 256+ rays and spread angle near max (179.5). A Polycount user says 128-256 rays is "preview quality", production 1024-2048 with 4x AA, spread 160 fine, cosine distribution. (Search snippets only; the Polycount page returned 403 on fetch.) — [Polycount](https://polycount.com/discussion/comment/1132049), [CryEngine xNormal AO page](https://www.cryengine.com/docs/static/engines/cryengine-3/categories/1114113/pages/15745535)
- Real-time AO research: diminishing returns with ray count; in one test no noticeable difference between 32 and 64 rays per point (snippet only). — [Springer chapter via search](https://rd.springer.com/content/pdf/10.1007/978-1-4842-4427-2_15.pdf)

### Inferences
- Cosine weighting: AO = (1/pi) * integral V(w) cos(theta) dw. Depth maps are shared across all texels, so per-normal cosine-distributed rays are impossible; the natural fit is a fixed global direction set (uniform on the sphere) with per-texel weights w_i = max(n.d_i, 0), AO = sum(w_i * V_i) / sum(w_i). This is standard importance weighting, not a quoted recipe.
- Fixed N directions give banding (discrete shadow edges) rather than noise; at N=256 angular spacing is about sqrt(4pi/256) = 0.22 rad (~12.6 deg). Light bilateral filtering hides it; N=256-512 for the final result. Judgement, not sourced.
- Fibonacci/golden-spiral gives near-uniform coverage deterministically (z_i = 1-(2i+1)/N, phi_i = i*golden angle). I found no source comparing it with random/stratified for AO; GPU Gems only mandates "uniform on the sphere".
- Recommended: N=256 for final, 64-128 preview. With a ground plane (section 3) only the upper hemisphere is needed, so use a 512-point sphere set restricted to d.z>0 (about 256 maps).

### Gaps
- No source comparing Fibonacci vs random vs stratified AO error; no source on banding with a shared direction set.

## 2. Depth map resolution, bias, normal offset

### Takeaway
GPU Gems gives no numbers for resolution or bias. Derived guidance: pixel size <= ~5 mm for a 4.5-5 m car (1024 px orthographic over a ~5.6 m bounding-sphere diameter gives ~5.5 mm/pixel; 2048 px gives ~2.8 mm), bias of 1.5-2 pixel footprints plus a slope term and a normal offset.

### Cited Findings
- GPU Gems: shadow-map streaking at the lit/shadow terminator is reduced by multiplying the shadow term by a function of the surface normal and light direction (keeps the side facing away from the light fully dark); the only self-shadow fix described. No bias or resolution figures given. — [GPU Gems ch.17](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)
- Substance Bakers: "Min Occluder Distance" default 0.00001 and "Max Occluder Distance" default 0.1 (relative to bbox diagonal when enabled, 1.0 = diagonal); Ignore Backface recommended enabled "most of the time" to avoid artifacts. — [Adobe Substance 3D Bake docs](https://experienceleague.adobe.com/en/docs/substance-3d/bakers/bakers-settings/ambient-occlusion-from-mesh)
- Substance's precision bias works opposite to intuition (lower value = more precision but bigger artefacts) (search snippet). — [Adobe Substance 3D Bake docs](https://helpx.adobe.com/substance-3d-bake/bakers-settings/ambient-occlusion-from-mesh.html)

### Inferences (my derivation, not sourced)
- Orthographic projection per direction (distant light). Fit one bounding sphere (radius ~2.8 m for a 4.5 m car) so any direction fits one fixed pixel size p = 2R/res.
- Texel lit if d_texel <= d_map + bias. Robust start: bias = 1.5-2 p + p*min(tan(theta),5) (theta = angle between normal and light), plus shift the texel point along its normal by 1-2 p before projecting (normal offset). At p~5 mm: bias ~8-10 mm, offset ~5-10 mm. Larger values cause peter-panning, which for AO only lightens tight creases (< ~1 cm gaps) - acceptable for a skin AO.
- Skip directions with n.d < ~0.05: weight ~0, and grazing angles are where acne is worst, so cosine weighting suppresses it for free.
- Surfaces facing away (n.d<0) are unlit by definition; no depth test needed.

### Gaps
- No sourced numeric bias for orthographic AO shadow maps; tune by eye on the real mesh (door seams, grille gaps, wheel arches).

## 3. Ground plane and occluder policy (glass, interior, double-sided, duplicates)

### Takeaway
Baker practice: optional invisible ground plane under the bbox with an offset to control strength; Ignore Backface option; self-occlusion filter by mesh name. For a car on the ground, use the dome only, or a real ground occluder at tyre-contact height. Coplanar duplicate meshes must be excluded from the occluder set by name/material.

### Cited Findings
- Substance: Ground Plane simulates an invisible plane under the mesh bounding box (XZ axis) that rays collide with; Ground Plane Offset shifts it away from the mesh, reducing the effect; offset is absolute, not relative. — [Adobe Substance 3D Bake docs](https://experienceleague.adobe.com/en/docs/substance-3d/bakers/bakers-settings/ambient-occlusion-from-mesh)
- Substance: "Ignore Backface" (Never/Always/By Mesh Name) and "Self Occlusion" (Always / By Mesh Name filter) let specific meshes be excluded as occluders. — same page
- GPU Gems: when the object stands on a plane only a hemisphere of lights is needed. — [GPU Gems ch.17](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)

### Inferences
- (a) "Dome only": use directions with d.z>0 and normalise by the sum of weights over that set; sills still darken from the body above and wheels. (b) "Ground occluder": keep the full sphere, treat below-horizon directions as blocked at ground height z0 for texels above z0; this darkens lower panels strongly. Put z0 at/just below tyre contact, and consider weighting below-horizon directions by ~0.5 to avoid black sills. Judgement.
- Occluders: opaque body panels, wheels/tyres, brakes, bumpers, mirrors, exhaust. Glass should not occlude (transparent). Interior texels: bake with glass excluded and the body shell as occluder, or skip interior. Judgement; decide per project.
- Exclude by name/material: shadow planes, glass, damage/dirt/decal copies lying on panels, light cones/flare planes, separate driver mesh. A coplanar duplicate otherwise shadows its twin within the bias zone and gives noise. Mitigations: (1) exclude by name; (2) otherwise drop occluder points within the bias distance whose normal agrees with the texel; (3) bake the duplicate's texels from the base panel's AO.
- Thin double-sided shells (mirror glass, grilles, mesh): in point splatting both faces become occluder points anyway; single-sided opaque panels need nothing special.

### Gaps
- No documentation found on how xNormal/Marmoset handle ground-plane height or transparent materials (xNormal help not retrievable).

## 4. Building the z-buffer with numpy (measured)

### Takeaway
Splat dense surface sample points with `np.minimum.at`. On current numpy this was the FASTEST option measured here (0.05 s for 8M points into 1024^2); sort-based approaches were 4-70x slower. Older advice to avoid `ufunc.at` is outdated.

### Cited Findings
- Old numpy (1.9.2, 2015-2019 benchmarks): ufunc.at was 10-25x slower than carefully written alternatives (e.g. bincount for sums); for min/max the sort-based routes were roughly equal to ufunc.at (~40 ms vs ~43 ms for 100k indices). Issue closed Feb 2023 after a fix (numpy PR #23136) with "rerun the benchmarks". — [numpy issue 5922](https://github.com/numpy/numpy/issues/5922)
- Packing depth into high bits and payload into low bits of an int64 so one min selects nearest sample plus payload (Futhark gist; idea ports to numpy). — [gist](https://gist.github.com/athas/e0bad36bb30f8f791c7ed36bd591074b)
- Point-based rendering with a min-depth-per-pixel buffer is an established technique. — [Schuetz et al. 2019, arXiv 1908.02681](https://arxiv.org/pdf/1908.02681)

### Own measurement (numpy 2.5.4, 1024x1024 float32 buffer, random depths; script D:\ClaudeData\tmp\bench_zb.py)
| points | np.minimum.at | lexsort + first-per-pixel | packed int64 sort | argsort(z desc) + last-wins assign |
|---|---|---|---|---|
| 2 M | 0.02 s | 0.83 s | 0.07 s | 0.16 s |
| 8 M | 0.05 s | 3.49 s | 0.21 s | 0.77 s |
All four produced identical buffers. Use `np.minimum.at` on a float32 buffer initialised to +inf. Caveat: random pixel indices; real projected points are spatially coherent (should be as fast or faster, untested).

### Inferences
- Sample spacing: spacing in object space should be <= ~0.5 p so that surfaces at up to ~60 deg grazing (projected density falls by cos theta) leave no holes. Car surface area is roughly 25-40 m2 (my estimate), so 2.5 mm spacing = ~4-6.5 M points; the same cloud serves every direction. Per direction cost ~ project 5M points + min.at + texel lookup, roughly 0.1-0.2 s, so N=256 takes about 30-60 s (estimate, untested end-to-end).
- Generate points once: per triangle, stratified barycentric samples, count ~ area/spacing^2, with at least vertices + centroid for tiny triangles.
- Holes at grazing slivers: 3x3 min-filter on the depth map (np.minimum over 9 shifted views) is cheap and conservative (acts like +1 px bias).
- True triangle rasterisation in numpy is irregular and slower; splatting is simpler and fast enough.

### Gaps
- No existing open-source numpy implementation of this exact method found (searches returned only GPU Gems and ray-tracing bakers).

## 5. Cheat-sheet (derived; tune by eye)
- N = 256 Fibonacci directions on the sphere (64-128 preview); weights max(n.d,0), skip n.d<0.05; AO = sum(w V)/sum(w) over the same direction set (upper hemisphere + ground policy).
- Orthographic depth map over the bounding sphere, 1024-2048 px (~5.5 or ~2.8 mm/pixel).
- Splat points at <= 0.5 p spacing; float32 depth; `np.minimum.at`; 3x3 min filter.
- Bias = 1.5-2 p + p*min(tan theta,5); normal offset 1-2 p.
- Optional bilateral blur of baked AO (sigmaPos ~2 texels, sigmaValue ~0.2, normals respected), allowing N down to 64-128.
- Exclude glass / shadow planes / dirt-damage copies / driver by name or material.
- Substance defaults for comparison: 64 rays, cosine, spread 180, ignore backface on, optional ground plane with offset.
