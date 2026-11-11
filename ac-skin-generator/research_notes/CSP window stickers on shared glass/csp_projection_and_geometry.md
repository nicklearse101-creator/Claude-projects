# CSP: stickers on one side window when both sides share mirrored UVs in one mesh (projection, mesh split, extra geometry)

Scope: CSP features that place a decal by position instead of UV, or that add, split or re-material geometry per car or per skin. Local install checked read-only: CSP **0.3.1-preview2, build 4295** (`extension/config/data_manifest.ini`), 868 cars, 2167 skin-folder `ext_config.ini` files. Local files are cited as `file:///` links. Web sources are the official CSP docs (cup.acstuff.club, "CUP v65") and the CSP GitHub.

**Short answer for the writer:** CSP has no config-level "projected decal" for car glass. CSP *does* have a documented `[MESH_SPLIT_...]` section that regroups a mesh's triangles by a plane in model space, and it can give the split part **its own material**. Splitting the shared side-glass mesh at X = 0 gives the left and right windows separate materials. A `[SHADER_REPLACEMENT_...]` can then give just one side a different `txDiffuse` (a glass texture with the sticker). CSP's own configs use this mechanism to split Kunos glass and windscreen-banner materials. The other config-only route is `[MODEL_REPLACEMENT_...] INSERT = sticker.kn5`, which adds a sticker quad. Many installed skins do this **from the skin folder**. Lua `projectTexture` / Paintshop do NOT get round the problem, because they paint into the shared UV texture.

---

## 1. Does CSP have projected decals / projected textures for cars (config keys such as [PROJECTED_TEXTURE], [DECAL_...], txDecal, smSticker, car paint stickers)?

### Takeaway
I found no config section that projects a decal onto car meshes by position. Searches for PROJECTED/DECAL/STICKER section names in the CSP configs and the CSP DLL returned nothing. The only "stickers" feature in CSP is a **UV2-mapped stickers layer** (`StickersTexture` / `txStickers`), and only on car-paint, interior and a few multimap shaders, not on the glass shaders. Because UV2 is a second, artist-made unwrap, it *could* be non-mirrored. But it needs a `.uv2` file built in Content Manager from an FBX that has two UV sets, and the glass shaders don't read it.

### Cited Findings
- No `[PROJECTED…]`, `[DECAL…]` or `[STICKER…]` section headers appear anywhere in `extension/` configs. A case-insensitive byte search of the CSP binary (`dwrite.dll`, 143 MB, which now holds the shaders: "Actual content have been moved to dwrite.dll" per `shaders.zip`) found no such section strings either. Local search, [extension folder](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/)
- The car paint template documents the only sticker feature: "; Optional stickers using UV2 (use UV2 generation tool to add UV2 to models)", with `StickersTexture =` ("texture with stickers"), `StickersMapsTexture =` ("optional overlay for txMaps (active where opaque), mapped by UV2") and `StickersCoverDetails = 0`. These map to `RESOURCE_1 = txStickers`, `RESOURCE_2 = txStickersMaps` and `PROP extStickersMode`. — [materials_carpaint.ini lines 183-186, 350-355](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_carpaint.ini). The same block is in [materials_interior.ini lines 252-254, 429-431](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)
- UV2 shaders: "nePerPixelMultiMap_AT_NMDetail_stickers", "smCarPaint (and derivatives)" and "stPerPixelMultiMap_specular (and stPerPixelMultiMap_specular_damage_dirt)". UV2 comes from a separate binary file: in Content Manager `Content/Tools/Creator`, an FBX with meshes that have two UV sets is turned into a `.uv2` file, saved next to the KN5 with the same name (`car.kn5` + `car.uv2`). "When looking for UV2 patch files, CSP checks skin folders first". UV2 is half precision. — [CSP docs: UV2](https://cup.acstuff.club/docs/csp/general/uv2); also [CSP wiki: General – UV2](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-UV2)
- Docs syntax for the non-carpaint UV2 shader: `[SHADER_REPLACEMENT_...]`, `SHADER = nePerPixelMultiMap_AT_NMDetail_stickers`, `PROP_... = extStickersMode, 1`, `RESOURCE_0 = txStickers`, `RESOURCE_FILE_0 = my_texture_pack.zip::stickers.dds`. The `extStickersMode` flags are 1 = on, 2 = hide details, 4 = txStickersMaps, 8 = txStickersNormals (flag 8 "added in v0.1.80-preview446"). — [CSP docs: UV2](https://cup.acstuff.club/docs/csp/general/uv2)
- The glass templates (`Material_Glass` → `SHADER = smGlass`, `Material_MultiEmissiveGlass` → `smGlass_emissive`, `Material_PhotoelasticGlass` → `smGlass_phel`) expose IOR, thickness, refraction, normal map and mask-pass parameters. They have no stickers, UV2 or projection inputs. — [materials_glass.ini lines 19-110](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_glass.ini)

### Inferences
- A UV2 sticker layer could in principle give one-side-only stickers, because UV2 is a separate unwrap that need not mirror. But it needs (a) an FBX re-export with a second UV set and a CM-built `.uv2`, and (b) a UV2-capable shader on the glass. Moving glass to `nePerPixelMultiMap_AT_NMDetail_stickers` or `smCarPaint` would lose the glass look. That makes it impractical for a skin generator compared with section 2.
- The `.uv2` file is looked up in skin folders first, so a per-skin UV2 is technically possible. Nobody in the local install does this for glass.

### Gaps
- No source says whether `smGlass` or the Kunos glass shaders (`ksPerPixelAlpha`, `ksWindscreen…`) read UV2. The docs list only the three shader families above.
- I could not confirm that no undocumented decal feature exists, because CSP is closed-source. The DLL string search is suggestive, not proof.

---

## 2. Can CSP shader replacement give a mesh a shader that blends a second texture by object-space position, or a mask that differs left/right? (And the mesh-split alternative)

### Takeaway
No shader option for a position-based (planar or X-sign) mask was found. **The left/right separation itself is possible through `[MESH_SPLIT_...]`.** It regroups the triangles of a mesh by a plane (`SPLIT_AXIS` / `SPLIT_THRESHOLD`, optionally in model space). With `SPLIT_MATERIAL_POSTFIX` the split part gets a new material named `<original>+<postfix>`. A normal `[SHADER_REPLACEMENT_...]` on that new material can then give one window its own `txDiffuse`. This is config-only and documented. CSP's own configs use it on Kunos glass and windscreen banners.

### Cited Findings
- Official syntax: `[MESH_SPLIT_...]`, `MESHES = Headlights ; list of meshes to cut`, `SPLIT_AXIS = 1, 0, 0 ; axis to cut mesh by (cut will be perpendicular to it)`, `SPLIT_THRESHOLD = 0.0 ; offset for cut along the line, in meters`, `SPLIT_POSTFIX = _CUT ; name of cut off mesh in this case would be "Headlights_CUT"`. It is "not an actual cutting, no triangles will be split in two. Just regrouping existing triangles between two different meshes." It is described as meant for "very rare cases of preparing a config to an already existing car". — [CSP docs: Meshes splitting](https://cup.acstuff.club/docs/csp/cars/meshes-splitting)
- CSP's own config for the Kunos BMW Z4 uses the material-postfix variant on glass:
  ```
  [MESH_SPLIT_...]
  MESHES = material:CAR_GLASS_black
  SPLIT_MATERIAL_POSTFIX = __csp_glass_fix
  MODE = LOOK_AT
  MODEL_SPACE = 1
  LOOK_AT = 0, 0.5, -0.2
  LOOK_AT_THRESHOLD = 0

  [SHADER_REPLACEMENT_...]
  MATERIALS = CAR_GLASS_black__csp_glass_fix
  IS_TRANSPARENT = 0
  BLEND_MODE = OPAQUE
  SHADER = ksPerPixel
  ```
  — [extension/config/cars/loaded/bmw_z4.ini lines 227-242](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/bmw_z4.ini); the same block is in bmw_z4_drift.ini and bmw_z4_s1.ini
- The same mechanism is applied to windscreen banner glass and then restyled through the new material: `MESHES = _8@A`, `SPLIT_MATERIAL_POSTFIX = __csp_banner_fix`, followed by `[Material_WindscreenBanner] Materials = EXT_Glass_Banner__csp_banner_fix`. — [extension/config/cars/loaded/ks_porsche_911_gt3_cup_2017.ini lines 139-152](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/ks_porsche_911_gt3_cup_2017.ini); likewise `MESHES = GEO_windshield_banner@A` in [ks_toyota_ae86_drift.ini line 347](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/ks_toyota_ae86_drift.ini)
- The plane-mode split by X is in real use: `MESHES = 102, sm_42, sm_44`, `SPLIT_AXIS = 1, 0, 0`, `SPLIT_THRESHOLD = 0.0`, `SPLIT_POSTFIX = _CUT` — [streetcarpack_toyota_mr2_sw20/extension/ext_config.ini lines 16-20](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/streetcarpack_toyota_mr2_sw20/extension/ext_config.ini). A glass mesh split by Y is used in [extension/config/cars/gue/GT4/alpine_yellow_glass.ini lines 3-7](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/gue/GT4/alpine_yellow_glass.ini)
- A CSP template shows that `MODEL_SPACE` goes with the plane split: `SplitAxis = 1, 0, 0`, `SplitThreshold = 0`, `SplitInModelSpace = 0` → `[MESH_SPLIT_0_LOCALCUBEMAP] … MODEL_SPACE = ${SplitInModelSpace}`. Its purpose is splitting left/right headlights for local cubemaps. — [extension/config/cars/common/oldschool_lights_reflections.ini lines 1-28](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/oldschool_lights_reflections.ini)
- Key strings in the CSP binary next to `MESH_SPLIT` include: `SPLIT_NAME`, `SPLIT_MATERIAL_POSTFIX`, `SPLIT_MATERIAL`, `SPLIT_POSTFIX`, `_right_`, `UV_REFERENCE_SIZE`, `SPLIT_THRESHOLD`, `SPLIT_AXIS`, `LOOK_AT_THRESHOLD`, `ORDERED_NAMING`, `MODEL_SPACE`, `UV_REGION`, `UV_REGIONS_USE_SIZE`, `MODE`, `PLANE`, `LOOK_AT_NORMALS`, `LOOK_AT`. These suggest the modes PLANE / LOOK_AT / LOOK_AT_NORMALS / UV_REGION. Only some of them are documented. — local byte search of [dwrite.dll](file:///D:/SteamLibrary/steamapps/common/assettocorsa/dwrite.dll)
- Shader replacement: "Per-mesh targeting gives each mesh its own material". `RESOURCE_0 = txDiffuse` with `RESOURCE_FILE_N = custom.dds` loads a texture from disk. `SKINS = red?` limits the section to skins (cars only). Targeting is by name, `?` wildcards or properties only; the docs list no position or side filter. — [CSP docs: Shader replacements](https://cup.acstuff.club/docs/csp/general/shader-replacements)
- Scene-query filters include `material:`, `lod:A`, `insideInterior:yes`, `insideSteeringWheel:yes`, `insideWheel:yes` and others. I found no position or side filter. — [CSP docs: Filtering](https://cup.acstuff.club/docs/csp/general/filtering); [CSP docs: Scene queries](https://cup.acstuff.club/docs/csp/general/scene-queries)
- Per-skin glass texture swap from a skin folder is proven in the installed cars. Skin `ext_config.ini` contains `[SHADER_REPLACEMENT_...] MESHES=EXT_Windows / RESOURCE_3 = txDiffuse / RESOURCE_FILE_3 = EXT_Windscreen.dds`, and `EXT_Windscreen.dds` exists only inside the 8 skin folders that use it (not in `extension/`). — [cf_ferrari_296_gt3/skins/2023_n24_20_wtm/ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/skins/2023_n24_20_wtm/ext_config.ini)

### Inferences
- **Recipe (car-level split + skin-level texture), syntax assembled from the cited examples:**
  ```
  ; content/cars/<car>/extension/ext_config.ini  (skin-neutral: both halves keep the same texture unless replaced)
  [MESH_SPLIT_...]
  MESHES = <side_glass_mesh>@A          ; or material:<GlassMaterial> ; @A / lod:A keeps it to LOD A as CSP's own configs do
  SPLIT_AXIS = 1, 0, 0                  ; plane perpendicular to car X = the centreline
  SPLIT_THRESHOLD = 0
  MODEL_SPACE = 1                       ; cut in car model coordinates, not mesh-local ones
  SPLIT_MATERIAL_POSTFIX = __one_side   ; split triangles get material "<GlassMaterial>__one_side"

  ; content/cars/<car>/skins/<skin>/ext_config.ini  (proven pattern for skin-folder textures)
  [SHADER_REPLACEMENT_...]
  MATERIALS = <GlassMaterial>__one_side
  RESOURCE_0 = txDiffuse
  RESOURCE_FILE_0 = glass_sticker_side.dds   ; file sits in the skin folder
  ```
  Alternative without the material postfix: `SPLIT_POSTFIX = _CUT`, then `[SHADER_REPLACEMENT_...] MESHES = <mesh>_CUT`, since per-mesh targeting makes a unique material.
- The sticker texture for the split side can be the normal glass texture with the sticker drawn the right way round for that side. The other side keeps the original texture with no sticker. The mirrored-UV problem goes away because the two sides now sample different textures.
- The plane mode appears to be the default when `SPLIT_AXIS` is given. None of the plane examples set `MODE`; only the LOOK_AT examples do.
- "No triangles will be split", so this only works if no side-glass triangle straddles X = 0. That holds for side windows. A mesh holding windscreen + side windows would also be split down the windscreen centre, which is harmless if the windscreen texture is unchanged.
- Animated or opening windows: the split mesh probably keeps its parent node, so it should still follow door/window animations. This is not verified.

### Gaps
- **Which half gets the postfix** (the +X or −X side of the plane) is not documented. It needs an in-game test; flip it with `SPLIT_AXIS = -1, 0, 0` or a different threshold sign. AC's sign convention for car-left is also not stated in the docs.
- `MODEL_SPACE` is not documented on the docs page; its meaning comes from the template variable name. The default MODE name (`PLANE`) comes from binary strings only.
- Whether `SPLIT_POSTFIX` and `SPLIT_MATERIAL_POSTFIX` can be combined is untested; the examples use one or the other.
- **Whether `[MESH_SPLIT_...]` works from a skin-folder `ext_config.ini` is unverified.** None of the 2167 local skin configs uses it; all 11 local MESH_SPLIT users are car `extension/` or CSP `config/cars/` files. Whether `SKINS =` is honoured inside MESH_SPLIT is also unknown. Splitting at car level (above) avoids the question.
- I found no evidence of any shader parameter that masks by world or object position (for example a left/right flag). The CSP shader sources are not public in the installed build.

---

## 3. Can CSP add geometry from config (an extra KN5 sticker quad) per car or per skin, and from a skin folder?

### Takeaway
Yes. `[MODEL_REPLACEMENT_...]` with `INSERT = extra.kn5` plus `INSERT_AFTER` and/or `INSERT_IN`, optionally with `OFFSET` / `ROTATION` / `SCALE`, inserts a KN5 into the car model. It works from a **skin folder's `ext_config.ini`, with the KN5 resolved from the skin folder**. This is shown by thousands of local skin configs (2123 MODEL_REPLACEMENT sections). An inserted quad is its own mesh with its own material and texture, so a sticker on one window only is trivial.

### Cited Findings
- Documented keys: `ACTIVE`, `FILE = model.kn5` (which KN5/LOD to modify), `SKINS = red?` ("Only for cars"), `HIDE = name1, name2`, `INSERT = new_model.kn5` ("should be located next to config file"), `INSERT_AFTER = node_or_mesh`, `INSERT_IN = COCKPIT_HR` (use `INSERT_AFTER`, `INSERT_IN` or both), `MULTIPLE = 0`, `MERGE = 0`, `SCALE = 1, 1, 1` ("For cars, X is left-right and Y is up-down"), `ROTATION = 0, 0, 0` (heading, pitch, roll in degrees), `OFFSET = 0, 0, 0` (meters). "Most of those options have been added in v0.1.60, previous versions only had FILE, HIDE, INSERT and INSERT_AFTER." Names starting with `AC_`, a digit, or containing `WALL` cannot be replaced. — [CSP docs: Model replacements](https://cup.acstuff.club/docs/csp/general/model-replacements)
- Skin-folder example, with the inserted KN5s present **only** in the skin folders (`numberlights.kn5`, `gl.kn5`, `amrlmgt3.kn5`), one section per LOD:
  ```
  [MODEL_REPLACEMENT_1]
  FILE=aston_vantage_gt3_evo.kn5
  HIDE=
  INSERT=numberlights.kn5
  INSERT_AFTER=COCKPIT_HR
  [MODEL_REPLACEMENT_2]
  FILE=aston_vantage_gt3_evo_lod_b.kn5
  INSERT=numberlights.kn5
  INSERT_AFTER=COCKPIT_LR
  ```
  — [acf_aston_martin_vantage_gt3_evo/skins/2024_ELMS_59_Racing Spirit of Leman/ext_config.ini lines 17-40, 55-59, 82-86](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/acf_aston_martin_vantage_gt3_evo/skins/2024_ELMS_59_Racing%20Spirit%20of%20Leman/ext_config.ini)
- A skin-folder insert with explicit transform keys: `FILE=honda_nsx_gt3_evo_acc.kn5`, `INSERT=numberplate.kn5`, `INSERT_AFTER = HONDA_NSX_GT3_EVO`, `SCALE = 1, 1, 1`, `ROTATION = 0, 0, 0`, `OFFSET = 0.000, 0.000, 0.0`. The KN5s (`numberplate.kn5`, `numberplate EM.kn5`, `pleds.kn5`, `GTE_Led.kn5`) sit in the skin folder. — [ac_friends_honda_nsx_gt3_evo/skins/2023_IMSA_Racers_Edge_WTR_93_Road_America/ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ac_friends_honda_nsx_gt3_evo/skins/2023_IMSA_Racers_Edge_WTR_93_Road_America/ext_config.ini)
- Car-level inserts with `INSERT_IN` and transforms: `INSERT = bdb_stock.kn5`, `INSERT_AFTER = GEO_body_main`, `INSERT_IN = GEO_body_main`, `MULTIPLE = 0`, `MERGE = 0`, `SCALE = 0.989, 0.989, 0.989`, `OFFSET = 0, -0.6685, 0.089 ; L-R / U-D / F-B`. — local grep across `content/cars/*/extension/ext_config.ini` (one of several matching files)
- Local survey: across the 868 cars there are 2530 `[MODEL_REPLACEMENT` sections, **2123 of them in skin-folder configs**. Section counts in skin configs also include 546 `[SHADER_REPLACEMENT`, 82 `[MESH_ADJUSTMENT` and 2627 `[INCLUDE`. — local grep over [content/cars](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/)
- `SKINS =` in a car-level `[SHADER_REPLACEMENT_...]` is used in the wild (`SKINS = 2023_IMSA_Racers_Edge_WTR_93_Road_America`), and the docs list `SKINS` for MODEL_REPLACEMENT too. — [CSP docs: Model replacements](https://cup.acstuff.club/docs/csp/general/model-replacements); local grep
- A forum user reported that a skin-folder `ext_config.ini` with `[SHADER_REPLACEMENT_0] MATERIALS = Body` "did not work"; the thread has no confirmed resolution. — [GTPlanet AC mods thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14632359). This conflicts with the thousands of working local skin configs; the reported failure was probably specific to that case.

### Inferences
- **Recipe for a sticker quad from the skin folder** (syntax assembled from the cited examples):
  ```
  ; content/cars/<car>/skins/<skin>/ext_config.ini
  [MODEL_REPLACEMENT_...]
  FILE = <car_main>.kn5          ; LOD A only is usually enough for a sticker
  INSERT = window_sticker_left.kn5   ; lives in the skin folder; quad modelled in car coordinates, ~1-2 mm outside the glass
  INSERT_IN = <door_or_window_node>  ; or INSERT_AFTER = <some mesh>; use the moving node if the window/door animates
  OFFSET = 0, 0, 0
  ```
  The sticker KN5 carries its own alpha-tested or alpha-blended material (for example `ksPerPixelAT`, or `ksPerPixelMultiMap_AT` with `IS_TRANSPARENT`). The skin generator would have to write a tiny KN5, which is feasible with the project's own KN5 tools. OFFSET/ROTATION/SCALE take effect relative to the insert target.
- Z-fighting and transparency sorting against the glass are the practical risks. A small outward offset plus `[SHADER_REPLACEMENT_...] MESHES = <sticker mesh>` with `IS_TRANSPARENT = 1`, `BLEND_MODE = ALPHA_BLEND` / `ALPHA_TEST` and `DEPTH_MODE = LESSEQUAL_NOWRITE` (all keys listed in the shader-replacement docs) should manage it. This needs an in-game check.
- This route also works on non-CSP? No. Plain AC ignores `ext_config.ini`, so both routes need CSP (any 0.1.60+ build for the transform keys).

### Gaps
- No official doc page states that the skin-folder `ext_config.ini` is merged or that `INSERT` resolves relative to the skin folder. The evidence is the widespread working usage in installed mods (files present only in skin folders).
- Behaviour when the skin changes at runtime (Content Manager showroom or in-game skin switch) without reloading the car was not checked.

---

## 4. How does the CSP Paintshop (in-game car paint app) handle mirrored UVs and stickers?

### Takeaway
Paintshop paints by **projecting stamps and stickers from a world-space position onto the selected meshes, rendered into the skin texture (UV space)** through `ac.SceneReference:projectTexture`. Its "symmetry" draws the stamp a second time mirrored across car X. So it has the same limitation: a sticker projected onto one side window lands in the shared UV area and shows on both windows.

### Cited Findings
- The source selects meshes by material with `carNode:findMeshes('{ material:'..hoveredMaterial..' & lod:A }')`. It paints into an editing canvas used as the material's `txDiffuse` (`selectedMeshes:setMaterialTexture('txDiffuse', editingCanvas)`), and draws each stroke with `selectedMeshes:projectTexture(pr)`, where `pr = { filename = tex, pos = pos, look = dir, up = up, size = size, depth = …, doubleSided = brush.paintThrough, mask1 = maskingCanvas, … }`. With "With symmetry" it mirrors `lpos.x, ldir.x, lup.x = -lpos.x, -ldir.x, -lup.x` in car-local space and calls `projectTexture` again. The initial mesh list excludes glass damage: `findMeshes('{ ! material:DAMAGE_GLASS & lod:A }')`. — [Paintshop.lua (CSP GitHub), lines 12, 75, 1399-1429](https://raw.githubusercontent.com/ac-custom-shaders-patch/app-paintshop/main/Paintshop.lua)
- README: "Different tools for mirroring", "Pen pressure support"; stamps are "easily extendable with new brushes, stickers, patterns"; export "would use original texture as an AO map and apply it on top of the result"; "needs at least CSP 0.1.77"; known issue: "projecting other side, mirroring stamp, blur and smudge might not work propely in 0.1.78". — [app-paintshop README](https://github.com/ac-custom-shaders-patch/app-paintshop)
- `projectTexture` is documented as "Projects texture onto a mesh or few meshes, draws result. Use in when updating a dynamic texture, display or an extra canvas. Position, and directions are set in world space." `projectShader` has `withDepth`: "nearest to projection position triagles will have higher priority (in case of overlapping UV)". — [lua-sdk ac_apps/lib.lua lines 10680-10760](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/lib.lua)

### Inferences
- `withDepth` only decides which overlapping triangle *writes* the texel. Both windows still *read* the same texel, so the sticker still shows on both sides (one mirrored). Projection into a texture cannot fix a shared mirrored UV. It needs separate texture space (UV2), a separate material (MESH_SPLIT), or separate geometry (INSERT).
- Paintshop is useful as a placement preview, not as a fix.

### Gaps
- I did not test Paintshop on a mirrored-UV glass mesh in game.

---

## 5. Lua car scripts / scriptable displays: can a skin ship a script that renders a sticker by position?

### Takeaway
Car Lua scripts (`[SCRIPT_...]` and `[SCRIPTABLE_DISPLAY_...]` in a car config, SDK `ac_car_scriptable_display`) have the scene API to **create a mesh from vertices** (`createMesh`), **load and attach a KN5** (`loadKN5`), re-texture meshes, and give a split mesh unique materials. A script could build a sticker quad at a given position on one window at runtime and pick per-skin textures via `ac.getCarSkinID`. I found no evidence that a script can be declared from a *skin-folder* config. Scriptable displays and `setMaterialTexture` draw in UV space, so they share the mirrored limitation.

### Cited Findings
- SDK path rules: `"ac_car_scriptable_display": { "paths": [ "content/cars/*/extension*", "extension/config/cars/*", "extension/lua/cars/*" ], "withoutIO": true }`. No skin-folder path is listed. — [lua-sdk/rules.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/rules.json)
- A car script declaration in the wild: `[SCRIPT_0] SCRIPT = sandero_cockpit_wipers.lua / SKIP_FRAMES = 0 / ACTIVE_FOR_UNFOCUSED = 1 / ACTIVE_FOR_LOD = A / ACTIVE_FOR_NEAREST = 6`. — [cup_dacia_sandero/extension/ext_config.ini lines 94-99](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cup_dacia_sandero/extension/ext_config.ini). Only 9 `[SCRIPT_` sections exist across 868 cars, and **none of the 2167 skin configs contain `[SCRIPT_` or `[SCRIPTABLE_DISPLAY_`**. — local grep
- API in the car-script SDK: `_ac_SceneReference:createMesh(name, materialName, vertices, indices, keepAlive, moveData)` ("Create a new mesh with a given name and attach it as a child"); `ac.MeshVertex.new(pos, normal, uv)`; `ac.VertexBuffer` / `ac.IndicesBuffer` ("limited by 16 bits"); `:loadKN5(filename)` ("KN5 filename relative to script folder or AC root folder. Since 0.2.5, you can instead pass a table with filename and a filter"); `:ensureUniqueMaterials()`; `:setMaterialTexture('txDiffuse', 'file.dds' | rgbm | {callback…})` (since 0.2.2 a missing file does nothing); `:applyShaderReplacements(data, includeType)`; `:applySkin(skinTableOrFolder)` (folder string "Since 0.3.0"); `ac.getCarSkinID(carIndex)` ("Get selected skin ID (name of skin's folder)"); and `ac.findMeshes()` from the car root ("For car scripts, car's root"). — [lua-sdk ac_car_scriptable_display/lib.lua around lines 3090, 9530-9570, 10175-10200](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_car_scriptable_display/lib.lua); [ac_apps/lib.lua lines 9930-10160, 10660-10700](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/lib.lua)
- `projectTexture` and `projectShader` (world-space projection into a dynamic texture or canvas; custom HLSL through `projectShader`, template `extension/internal/shader-tpl/project.fx`) are in the same API. — [ac_apps/lib.lua lines 10680-10760](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/lib.lua)

### Inferences
- A per-car (not per-skin) script in `content/cars/<car>/extension/` could do: `local skin = ac.getCarSkinID(0)`; look for `skins/<skin>/window_sticker.dds`; if present, `createMesh` a quad (or `loadKN5` a quad) under the window node with that texture. This puts per-skin stickers anywhere by position. It needs a car-level script install (it touches the car's extension folder) and a CSP version with these APIs (0.2.x+). It is more fragile than the INI routes.
- `ac.getCarSkinID(0)` uses a car *index*. A car script should use its own car's index, not 0, which may be another car online. Not verified for the car-script context.
- `withoutIO: true` means car scripts have no general file IO, but texture and KN5 loading by path is still offered. Whether a script can load files from the skin folder path was not tested.

### Gaps
- No source says whether `[SCRIPT_...]` placed in a skin-folder `ext_config.ini` runs. There is no local example; it would need testing.
- The CSP minimum version for `createMesh` in car scripts was not found (the SDK text gives none).
