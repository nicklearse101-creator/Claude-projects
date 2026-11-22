# Content Manager (gro-ove/actools) car AO / shadow baking

All code paths are in https://github.com/gro-ove/actools (master, fetched 2026-11-22). Raw base: https://raw.githubusercontent.com/gro-ove/actools/master/ . Local copies of fetched files: D:\ClaudeData\tmp\actools.

## Which CM features bake AO/shadows, and which source files implement them

### Takeaway
Two separate bakers exist. (1) "Baked shadows" (Custom Showroom, car texture dialog, per texture or per object) bakes an AO map in the UV space of the car's own texture: this is the one to re-implement. (2) "Ambient shadows" (body_shadow.png / tyre_N_shadow.png) is a top-down ground-contact shadow image, not a texture AO.

### Cited Findings
- UV-space AO baker: `AcTools.Render/Kn5SpecificSpecial/BakedShadowsRenderer.cs`, base class `ShadowsRendererBase.cs` (light distribution, iterations), shaders in `AcTools.Render/Shaders/Special/SpecialShadow.fx` (techniques `Ao`, `AoResult`, `AoGrow`), depth material in `Kn5SpecificSpecial/DepthMaterialsFactory.cs`. UI view-model `AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs`, settings panel `AcManager/UserControls/BakedShadowsSettings.xaml`. — [BakedShadowsRenderer.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificSpecial/BakedShadowsRenderer.cs), [SpecialShadow.fx](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Shaders/Special/SpecialShadow.fx), [ViewModel](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs)
- Ground-contact "Ambient shadows" baker: `AmbientShadowRenderer.cs` (same base class), params in `AcManager/CustomShowroom/AmbientShadowParams.cs`; writes `body_shadow.png` (512 px, 64 px padding cropped off) and `tyre_{0..3}_shadow.png` (64 px, 32 px padding) into the car folder. — [AmbientShadowRenderer.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificSpecial/AmbientShadowRenderer.cs)
- Author's in-app tip (`AcManager/About/ImportantTips/Custom Showroom Shadows Baking.txt`): CM "puts hundreds and thousands of lights randomly distributed on a sky, builds a shadow map for each of them and sums them up"; it is explicitly contrasted with ray tracing and SSAO, and meant for "some mod not having AO map". — [tip text](https://github.com/gro-ove/actools/blob/master/AcManager/About/ImportantTips/Custom%20Showroom%20Shadows%20Baking.txt)
- `Base/PostEffects/AO/*` (Hbao, Ssao) and `Shaders/PpAo/*` are screen-space AO for live rendering, unrelated to baking.

### Inferences
- For a numpy re-implementation only BakedShadowsRenderer + SpecialShadow.fx matter.

### Gaps
- I found no code in `AcManager/PaintShop/*` that generates or applies an AO map (see last section).

## The method (BakedShadowsRenderer)

### Takeaway
Per light direction: render the car depth-only into an orthographic shadow map; rasterise the target meshes into UV space (vertex position = UV) and per texel evaluate (normal-mapped Lambert term x PCF shadow lookup of the texel's world position). Sum over N directions, divide, brightness and gamma, dilate UV islands, downsample. That is N shadow-mapped directional lights accumulated in UV space.

### Cited Findings
(all from BakedShadowsRenderer.cs, ShadowsRendererBase.cs, SpecialShadow.fx, DepthMaterialsFactory.cs unless noted)

**Directions**
- `Iterations`: class default 500 (ShadowsRendererBase), UI default 5000 (slider 100-10000, clamped 10..1,000,000). `PoissonSampling = true` default.
- Poisson mode: `UniformPoissonDiskSampler.SampleSquare(N, false)` gives about N points in [-1,1]^2 (Bridson sampling, min distance from `EstimateCircleMinimumDistance(N+10)`, extras removed, scaled so max |coord| = 1). `CropPoisson` maps the y range to [cos(thetaFrom+90deg), cos(thetaTo+90deg)] (splitting into horizontal bands when the range is narrow). Then theta = acos(clamp(y, +-0.9999)) - pi/2, phi = x*pi, direction = `MathF.ToVector3Rad(theta, phi)` = (sin(pi/2-theta)cos(phi), cos(pi/2-theta), sin(pi/2-theta)sin(phi)), Y up, theta = elevation. Since y is linear in the sample, directions are uniform in sin(elevation) (equal-area), azimuth uniform.
- Random mode (`PoissonSampling=false`): rejection-sample the unit ball, normalise, keep where Y in [sin(from), sin(to)].
- Elevation range `ΘFromDeg`/`ΘToDeg`: class default -10..50; UI default 0..60 (sliders +-89.9999). Tip: 0..90 = full hemisphere; -90..90 = lights all around (for wheels/rims).
- Direction vector = surface-to-light; shadow camera sits at `dir * FarZ * 0.5` looking at the origin.

**Shadow map**
- Orthographic CameraOrtho, Width = Height = length of the car bounding box size vector (diagonal; fallback 4), NearZ 1, FarZ 20, camera 10 m from the origin along the light direction, up +Y, frustum culling disabled.
- Resolution `MapSize`: class and UI default 2048. Depth format R24G8_Typeless (24-bit depth), cleared to 1. With a ~5-6 m diagonal that is roughly 2.5-3 mm per shadow texel (my arithmetic).
- Occluders: the whole car (all nodes via `Kn5DepthOnlyConverter`), skipping nodes with `CastShadows == false` and nodes hidden in the showroom renderer (`CopyStateFrom` also copies door/lights/wing/extra animation state, wheel alignment). Only the receivers are filtered to meshes using the chosen texture/object (`UtilsRendererBase.Flatten`, ignoring txDetail/txNormalDetail mappings).
- Double sided: each mesh is drawn twice into the same depth map, once with front-face culling (DepthBias = int(100*biasFront), SlopeScaledDepthBias = biasFront) and once with back-face culling (DepthBias = int(100*biasBack), slope = biasBack). Class defaults biasFront 0, biasBack 0.8; UI defaults 0 and 0.7 (70 %). Tip: the first pass draws only back faces ("usually no problem with self-shadowing"), the second only front faces with a positive and quite big offset. So both back and front faces occlude, and the raster depth bias is the only self-shadow protection (no normal-offset). (Unit meaning of D3D11 DepthBias, about 2^-24 per unit on 24-bit depth, is my inference from D3D11, not stated in CM.)
- Transparent/alpha-tested parts: the depth shader does `clip(alphaTex.a - alphaRef - 0.0001)` using txDiffuse alpha (txNormal alpha for ksPerPixelNM, `_AT` shaders, ksSkinnedMesh) when the material blend mode is not Opaque or is AlphaTested. Multimap shaders, ksTyres, ksBrakeDisc and "damage" shaders get no alpha clip (always opaque occluders). So ordinary glass with alpha above alphaRef still occludes.
- No ground plane exists in the baked renderer (scene is the car only). With From >= 0 no light comes from below, so none is needed; a fake ground bounce is available through `Ambient` (below).

**Per-texel evaluation (technique `Ao`: vs_Ao / ps_Ao)**
- Vertex shader output position = (u*2-1, -v*2-1), i.e. the mesh is drawn flattened into UV space (V flipped). The mesh is redrawn once for each integer UV tile offset in -10..10 where any vertex lies, so tiled UVs are folded into 0..1 (overlaps resolved by MAX blend). Triangle winding is fixed in UV (FixClockwiseness) so UV-mirrored triangles are not culled.
- World normal = normal-map sample (material's txNormal, tangent frame from vertex N and T, bitangent = cross(N,T)); flat normal if no txNormal or a "damage" shader. (`gNormalUvMult` is set but not used in ps_Ao.)
- `ambient = saturate(worldPos.y * 2) * gAmbient` (gAmbient = UI Ambient/100, default 0)
- `light = saturate(dot(normal, lightDir)) * (1 - ambient) + ambient`
- `shadow = SampleCmpLevelZero(samShadow, shadowPos.xy, shadowPos.z)`: comparison sampler MIN_MAG_MIP_LINEAR (2x2 bilinear PCF), ComparisonFunc LESS (lit when receiver depth < stored depth), BORDER with border 1.0 (outside the map is lit).
- Output colour `light * shadow` (grey), alpha 1.

**Accumulation**
- Per light the UV render goes to an 8-bit RGBA target (`_bufferF1`, cleared transparent, MAX blend), then is added (ONE/ONE ADD) into `_bufferFSum` (R32G32B32A32_Float). Alpha accumulates as well. DrawLight returns 1, so t = Iterations; no extra elevation weighting beyond the Lambert term.

**Normalisation (technique `AoResult`)**
- `count = t / SkyBrightnessLevel`; SkyBrightnessLevel = UI Brightness/100 (class default 2.5, UI default 2.2, slider 50-350 %).
- `v = saturate( pow( max(sum.x / count, 0), Gamma ) ) + dither`, i.e. `v = clip( (mean(light*shadow) * Brightness)^Gamma, 0, 1 )`. Gamma = UI Gamma/100 (class default 0.5, UI default 0.6, slider 0-500 %). Dither = lerp(0.00196, -0.00196, frac(0.25 + dot(uv, screenSize*0.5))), about +-0.5/255. Output grey RGB, alpha = accumulated alpha (clamps to 1 in the 8-bit target where covered).

**Post-processing**
- Padding: `Padding` iterations (class and UI default 4, slider 0-10), each running `AoGrow` twice. AoGrow keeps a texel if it and its 8 neighbours all have alpha > 0.95; otherwise takes the per-channel MAX of neighbours with alpha > 0.95 from an 11x11 grid sampled at 0.5-texel steps (+-2.5 texels), alpha forced to 0 if the result alpha <= 0.9. Runs at the supersampled resolution before downsampling.
- Resolution: requested W x H; render buffers are `ResolutionMultiplier = sqrt(PixelDensity)` per axis (UI PixelDensity default 4, slider 1-8, so 2x2 supersampling; class default 2).
- Optional FXAA (`UseFxaa` default true), then `DownsampleHelper` technique `Average` (PpDownsample.fx): 9x9 point samples, offsets x,y in -1..1 step 0.25 times 0.5 destination pixel, weight w = sqrt((1.5-|x|)^2 + (1.5-|y|)^2), normalised.
- `FullyTransparent` (UI default true): final copy writes (rgb, 0) (`CopyFullyTransparent` in PpBasic.fx).

### Inferences
- CPU equivalent: N (500 is already smooth, CM default 5000) directions uniform in sin(elevation) over 0..60 deg (UI default) or 0..90; per UV texel mean over directions of max(0, n.l) * visibility (two-sided occluders, alpha-cut parts skipped, small slope/depth bias); `out = clip((mean*2.2)^0.6, 0, 1)`; dilate islands about 4 padding steps; render at 2x and downsample.
- Ray traced equivalent: visibility along the ray from the texel (offset a few mm) in each direction.
- Rough sanity value (my arithmetic, unverified against real output): unoccluded upward-facing texel, light uniform in sin(theta) over 0..60 deg, mean n.l = 0.433; times 2.2 = 0.95; ^0.6 = 0.97. Vertical sides get lower values, undersides about 0 unless Ambient > 0.

### Gaps
- Handedness of the UV tile offset/V flip taken as coded; not verified by comparing an output map.
- Whether mirrored/skinned nodes are transformed the same in the depth renderer was not checked.
- I did not run CM or compare a produced AO map.

## Output: file name, format, target texture, paint shop

### Takeaway
CM shows the result in a viewer and saves via a dialog, defaulting to the baked texture's name; nothing is automatically written into the car. I found no evidence that the paint shop uses or multiplies an AO map.

### Cited Findings
- `CalculateAo` runs `renderer.Shot(TextureName, ObjectPath, ...)` and returns PNG bytes of the render buffer; the viewer shows "Generated AO map" next to the original texture. Save dialog: `SaveDefaultFileName = TextureName`, directory = the kn5's folder, filters DDS/JPEG/PNG. — [ViewModel](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs)
- DDS saved with `DdsEncoder.SaveAsDds(..., UseDxt5 ? DXT5 : LuminanceTransparency)` (UseDxt5 default true). JPG via ImageUtils.Convert quality 97. PNG: if FullyTransparent, round-trips through JPEG q97 (alpha dropped), else raw PNG bytes.
- Size: user prompt "WxH" or a preset, -1 = original texture size (fallback 1024).
- Saved defaults (SaveableData, key "_carTextureDialog", presets category "Baked Shadows"): From 0, To 60, Brightness 220, Gamma 60, PixelDensity 4, Ambient 0, ShadowBias 0, ShadowBiasCullBack 70, Iterations 5000, Padding 4, ShadowMapSize 2048, UseFxaa true, FullyTransparent true, UseDxt5 true.
- Option meanings (tip text): From/To = elevation range of lights; Brightness, Gamma = output curve; Ambient = fake ground-reflected light; Bias (first)/(second) = shadow offsets for back/front faces; Iterations = number of lights; Padding = extra pixels around UV islands (seams); Pixel density = resolution multiplier with downscale; Shadow maps' resolution; FXAA smoothing.
- Ambient shadows (ground shadow, for completeness; AmbientShadowParams/AmbientShadowRenderer): Diffusion 60 %, Brightness 200 %, Iterations 3000 (renderer 2000), HideWheels, Fade, CorrectLighting (weight by |light.y|), Poisson, ExtraBlur, UpDelta 0.05, BodyMultiplier 0.8, WheelMultiplier 0.69 in renderer / 0.35 UI. Same many-lights idea: top-down ortho depth camera, lights from elevation above yThreshold = 0.95 - Diffusion*0.95 up to 90 deg, double-sided depth, texels on the ground plane add `multiplier` where depth > 0.99 (unoccluded), 11-tap H+V blur (weights 0.05,0.05,0.1,0.1,0.1,0.2,0.1,0.1,0.1,0.05,0.05; twice if ExtraBlur), `1 - saturate(sum/count)` with an edge fade. Not needed for UV AO.

### Gaps
- Paint shop AO usage (multiply over a white base) is unconfirmed: I found no AO step in the `AcManager/PaintShop/*` file list or `SpecialPaintShop.fx` (I did not read them in full). Per the author tip the baked map is meant to be saved as the AO texture a mod lacks; how AC's shaders consume it is not in this code.
- Forum/doc sources (RaceDepartment, overtake.gg, acstuff.ru) were not searched in depth; a web search for the class names returned nothing relevant.
