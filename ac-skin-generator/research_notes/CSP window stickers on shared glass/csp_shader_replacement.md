# CSP per-skin ext_config.ini: SHADER_REPLACEMENT, mesh selection and MESH_SPLIT for a sticker on ONE window

Research date 2026-11-11. Installed CSP on Nik's PC: **0.3.1-preview2** (`extension/config/data_manifest.ini`, `SHADERS_PATCH=0.3.1-preview2`). Local sources are read-only reads of `D:\SteamLibrary\steamapps\common\assettocorsa\`. Wiki pages were downloaded as raw markdown from the official `acc-extension-config` GitHub wiki. Scratch scripts (kn5 texture/material reader, DLL string dump) are in `D:\ClaudeData\tmp\csp_scripts\`.

Local source shorthand used below:
- README = [`extension\read me to save yourself some time.txt`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/read%20me%20to%20save%20yourself%20some%20time.txt)
- LUASDK = [`extension\internal\lua-sdk\ac_apps\README.md`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/README.md)
- CFG = `extension\config\cars\...` (CSP's own shipped car configs)
- CARS = `content\cars\...` (868 installed cars; **2,151** per-skin `skins\*\ext_config.ini` files, 433 of them with `[SHADER_REPLACEMENT_...]`, `RESOURCE_FILE_N` used 76 times in skin configs; 451 car-level `extension\ext_config.ini`)

---

## Q1. Exact syntax of [SHADER_REPLACEMENT_...]: targeting by mesh, material or texture; wildcards; lists

### Takeaway
`[SHADER_REPLACEMENT_...]` targets with `MESHES =` or `MATERIALS =` (comma lists, `?` wildcard, `key:value` property selectors such as `texture:` / `shader:` / `material:` / `lod:`, and `'{ ... }'` boolean expressions). A new texture from disk is `RESOURCE_n = <slot>` plus `RESOURCE_FILE_n = file.dds`. **Targeting by `MESHES` gives each matched mesh its own copy of the material**, so the new texture lands on that window only, even when other windows share the same material and texture.

### Cited Findings
- Official syntax header (verbatim from the wiki):
  ```ini
  [SHADER_REPLACEMENT_...]
  ACTIVE = 1    ; set to 0 to disable the whole section (default value is 1)
  SKINS = red?  ; list of skins to use replacement with (only for cars)
  ; First, targets, either materials or meshes (one thing to consider:
  ; for altering material properties, each mesh in MESHES would get its own material, thus
  ; increasing number of GPU calls, so it's better to use MATERIALS where possible):
  MATERIALS = tree?, texture:grass?.dds
  MESHES = mesh_bush_?
  SHADER = ksTree_ppshadows
  SHADER_OVERRIDE_0 = ksTree, ksGrass
  LEAVE_FUNCTIONAL_SHADERS = 1
  PROP_0 = ksAmbient, 0.4          ; or KEY_0 = ksAmbient / VALUE_0 = 0.4 (up to KEY_99/VALUE_99)
  RESOURCE_0 = txDiffuse
  RESOURCE_TEXTURE_0 = name_of_texture_in_kn5.dds ; TEXTURE refers to texture in original model
  RESOURCE_1 = txNormal
  RESOURCE_REF_1 = txDetailNM  ; REF refers to original texture in certain slot
  RESOURCE_2 = txMaps
  RESOURCE_COLOR_2 = 1, 1, 1 ; COLOR creates new 1×1 solid color texture
  RESOURCE_3 = txDetail
  RESOURCE_FILE_3 = custom.dds ; FILE refers to a texture on a disk, next to the config
  FILL_MISSING_TEXTURES = 1
  FORCE_POINT_SAMPLER = 1
  FORCE_MINUS_TWO_LOD_BIAS = 1
  BLEND_MODE = ALPHA_BLEND   ; OPAQUE, ALPHA_TEST, ALPHA_BLEND, TRANSPARENT_AS_BLACK, ADD or ALPHA_ADD, MULTIPLY or ALPHA_MULTIPLY
  CULL_MODE = OFF
  DEPTH_MODE = NORMAL_FORCED
  ```
  — [CSP wiki: General – Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- The wiki says to pair each `RESOURCE_n` with its value by number and not to use `...` there ("here, it's better not to use "..." to make sure key would be paired with its value"). — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- Material sharing switch (verbatim): `SHARED_MATERIALS = 0  ; set to 1 to apply to all meshes sharing the same material, or FORCE to apply even for non-unique materials`. Keys marked `*` (CAST_SHADOWS, IS_TRANSPARENT, IS_VISIBLE, LAYER, LOD_IN/OUT, EXTRA_MASK_PASS...) are "per-object tweaks, those will not create new materials if you're using MESHES and nothing but them". — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- CSP's own generic config explains the default copy behaviour (verbatim comment): `SHARED_MATERIALS = 1  ; do not copy materials; apply only if material is not used for any meshes that don't fit the filter`. — [CFG `generic\generic_fixes.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/generic/generic_fixes.ini)
- Other relevant keys: `STICKERS_FIX = 1 ; shift geometry a bit closer to camera, great for stickers and such`. The author also writes: "I suspect `LESSEQUAL` might be perfect for stickers on cars added with a second layer". — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- Filtering rules: lists are comma-separated. "Patch uses "?" for the same purpose [as Windows '*']" (so `*` is NOT a wildcard). Property filters are `key:value` with no spaces around `:`. — [CSP wiki: General – Filtering](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Filtering)
- Known selectors (wiki list):
  - meshes: `material:`, `renderable:`, `transparent:`, `hasLodDistance:`, `mirror:`
  - nodes and meshes: `parent:`, `child:`, `lod:A`, `active:`, `insideInterior:`, `insideSteeringWheel:`, `first:`, `last:`, `modelRoot:`
  - meshes and materials: `shader:`, `texture:NULL.dds` ("true if at least any used texture matches that name (case-independant)"), `materialProperty:`, `materialResource:`, `supportsDamage:`, `alphaBlend:`, `alphaTest:`, `vegetation:`, `dynamic:`

  — [CSP wiki: Filtering](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Filtering)
- Extended filters ("Since v0.1.25-preview183"): wrap the expression in `{ }`, quote it, and use the operators `!` (NOT), `&` (AND), `^` (the wiki calls it NOR, but its description is XOR) and `|` (OR), with parentheses. Example: `MESHES = '{ lod:A & mesh1 }', '{ lod:B & mesh2 }'`. Property selectors date "Since 0.1.62". — [CSP wiki: Filtering](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Filtering)
- Real selector examples in installed configs:
  - `MATERIALS = '{ shader:ksWindscreen? & alphaTest:yes }'` — [CFG `generic\generic_fixes.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/generic/generic_fixes.ini)
  - `Materials = '{ texture:Plate_D.dds & texture:Plate_NM.dds }'` — [CFG `common\materials_license_plate.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_license_plate.ini)
  - `MESHES = material:CAR_GLASS_black` and `'{ renderable:yes & material:INT_Alcantara & !GEO_Steer_SUB0 }'` — grep of CARS / CFG configs
- Lua SDK: "Filter is regular stuff, the same as used in INI configs. To use complex filter with commas and operators, wrap it in curly brackets as usual." The SDK also warns to restrict to LOD A when projecting on a material, e.g. `ac.findMeshes('{ material:car_paint & lod:A}')`. — [LUASDK](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/README.md)
- Textures can be read from a zip: "you can always put them all in a zip file and refer to them as `SOMETHING = textures.zip::path/in/zip.dds`". — [CSP wiki: General – UV2](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-UV2)
- Section name forms seen in practice: `[SHADER_REPLACEMENT_...]` (auto-index), `[SHADER_REPLACEMENT_0]`, and named forms such as `[SHADER_REPLACEMENT_0_Generic_BlendingForWindscreens]`. — [CFG `generic\generic_fixes.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/generic/generic_fixes.ini)

### Inferences
- For a skin generator, the robust minimal section is:
  ```ini
  [SHADER_REPLACEMENT_0_SKINGEN_WINDOW_RR]
  MESHES = <exact window mesh name>      ; MESHES => this mesh gets its own material copy
  RESOURCE_0 = txDiffuse
  RESOURCE_FILE_0 = skingen_window_rr.dds ; file in the skin folder
  ```
  Use a unique, numbered or named section so it can't collide with a section of the same name in the car-level config. Lookups are per parameter, so a same-named section in the skin file overrides keys of the car-level one (see Q2).
- Plain AC skin overrides replace a texture by file name for every material that uses it. Dropping an edited `glass.dds` into the skin folder would therefore put the sticker on every window sharing that texture. The `MESHES` plus `RESOURCE_FILE` route avoids that, because the new file has a new name and is bound only to the copied material of the chosen mesh.
- Include every LOD that shows the window (`'{ lod:A & GEO_Window_RR }'`, plus the LOD B mesh if it exists), or the sticker will pop in and out with distance.
- Window glass is alpha-blended, and txDiffuse alpha is the glass opacity. The replacement texture must therefore be the original glass texture (same size and alpha) with the sticker composited on it. A sticker-only texture would turn the rest of that window opaque or invisible.

### Gaps
- The wiki does not list a `RESOURCE_SKIN_n` key, and I found none in 2,151 skin configs. Only `RESOURCE_TEXTURE_`, `RESOURCE_REF_`, `RESOURCE_COLOR_` and `RESOURCE_FILE_` are documented.
- The filtering wiki documents no `kn5:` selector. Real configs do use `prefix:name` forms (`DRIVER:HELMET_GLASS_SUB1`, `bell_hp7_v4a:sticker`) and `@A` suffixes (`MESHES = _8@A`, `'g_WIPER2@A=1'`), but no page I found documents them. `@A` appears to mean LOD A (inference only).

---

## Q2. Is skins/SKIN/ext_config.ini loaded and applied only to that skin? Since which version? How are relative texture paths resolved? Is there a SKINS= filter?

### Takeaway
Yes. CSP's own readme lists `ext_config.ini` in the car's skin folder as a lookup level, ranked above the car's `extension\ext_config.ini`, and lookups are merged per parameter. A per-skin file only needs the extra sections. `RESOURCE_FILE` is resolved "next to the config", which in practice means the skin folder. The car-level alternative is a `SKINS =` key inside the section. I could not find which CSP version introduced per-skin configs.

### Cited Findings
- Lookup order (verbatim, CSP readme): "For each car, reading of each parameter goes like that:
  - Try to find the value in CARID__SKINID.ini in Documents\Assetto Corsa\cfg\extension\cars;
  - Try to find it in CARID.ini, in Documents;
  - Check if there is a file ext_config.ini in car's skin folder;
  - Check if there is a file extension\ext_config.ini in car's folder;
  - Look for the value in CARID__SKINID.ini in assettocorsa\extension\config\cars;
  - And, at last, for CARID.ini in assettocorsa\extension\config\cars."

  — [README (local)](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/read%20me%20to%20save%20yourself%20some%20time.txt)
- Includes: "For included files, patch first will check files nearby, then look for files in Documents\Assetto Corsa\cfg\extension\cars, and then for files in assettocorsa\extension\config\cars". So `[INCLUDE: common/materials_glass.ini]` works from a skin file. — [README (local)](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/read%20me%20to%20save%20yourself%20some%20time.txt)
- Live reload: "Patch watches files in both Documents\Assetto Corsa\cfg\extension and assettocorsa\extension\config ... It should reload files immediately." — [README (local)](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/read%20me%20to%20save%20yourself%20some%20time.txt). Live reloading "works for most settings, but not all, like not for [MODEL_REPLACEMENT...] and such". — [CSP wiki: Cars – About guessed configs](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-About-guessed-configs)
- Shader replacements are static. They are applied once at load or after a config change, and "if you change config and remove a [SHADER_REPLACEMENT_...] section, it wouldn't restore original values". — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- The **real-world precedent is exactly this use case**, in `cf_ferrari_296_gt3`:
  - The skin `2023_NLS_1_Frikadelli_30\ext_config.ini` (40 lines; the car-level `extension\ext_config.ini` has 1,421 lines, so the skin file is clearly merged, not a replacement) contains:
    ```ini
    [SHADER_REPLACEMENT_...]
    ACTIVE = 1
    MESHES=EXT_Windows
    RESOURCE_3 = txDiffuse
    RESOURCE_FILE_3 = EXT_Windscreen.dds
    ```
  - `EXT_Windscreen.dds` sits in the skin folder. My kn5 reader found **no** texture of that name in `cf_296_gt3.kn5`: its glass textures are only `glass_clear.dds` and `INT_Windshield_Dirt.dds`.
  - In the kn5, mesh `EXT_Windows` uses material `EXT_Windows` (shader `ksPerPixelReflection`, alpha-blend, `txDiffuse = glass_clear.dds`). `glass_clear.dds` is also used by the materials `EXT_Glass_NM`, `INT_Windows` (meshes DOOR_L_1_SUB3, DOOR_R_1_SUB3, INT_Windows) and `EXT_Glass_Black`.
  - The skin `2023_NLS_Frikadelli_30` also uses `RESOURCE_FILE_0 = ext_glass_headlight.dds`. That file exists only in that skin folder: it is not in the kn5, the car's `extension\` folder or CSP's `cf\Ferrari_296\` folder.

  — local files [CARS `cf_ferrari_296_gt3\skins\2023_NLS_1_Frikadelli_30\ext_config.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/skins/2023_NLS_1_Frikadelli_30/ext_config.ini) and [`cf_296_gt3.kn5`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/cf_296_gt3.kn5), parsed with `D:\ClaudeData\tmp\csp_scripts\kn5mat.py`
- The `SKINS` filter exists in both section types (wiki): `SKINS = red?  ; list of skins to use replacement with (only for cars)` in SHADER_REPLACEMENT and in MODEL_REPLACEMENT. — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements), [CSP wiki: Model replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Model-replacements). Real car-level use: `SKINS =Sydney     ; list of skins to use replacement with (only for cars)` — [CARS `adc_lexus_is200_stock\extension\ext_config.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/adc_lexus_is200_stock/extension/ext_config.ini)
- Community reports: "Save it as ext_config.ini in the skin's folder" to affect one skin only. Also, some skin ext_config files with `[MESH_ADJUSTMENT_3]` broke a car's wipers, and deleting them fixed it. — [GTPlanet AC PC Mods General Discussion thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/) (search snippets; I did not verify the exact page numbers)
- Related per-skin precedent: "When looking for UV2 patch files, CSP checks skin folders first, so that can be used for creating some advanced skins." — [CSP wiki: UV2](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-UV2)

### Inferences
- Because lookups are merged per parameter, a skin file overrides any section of the same name in the car config, and with `[SHADER_REPLACEMENT_...]` auto-indexing it adds sections instead. The generator should use distinctive section names, e.g. `[SHADER_REPLACEMENT_0_SKINGEN_1]`.
- "Next to the config" means files named in a skin `ext_config.ini` are resolved in that skin folder. The Ferrari skins prove this for a texture name that doesn't exist in the kn5.
- The generator must merge with any existing skin `ext_config.ini` instead of overwriting it, since 2,151 installed skins already have one (car paint, lights, etc.). A marker comment block (e.g. `; --- skingen begin/end ---`) would make re-runs safe.

### Gaps
- **Version that introduced per-skin ext_config.ini:** not found. Web searches found no CSP changelog entry, and the wiki doesn't state it. It is long-standing behaviour (the readme ships with current CSP, and thousands of skins rely on it).
- I found no statement on what happens when `RESOURCE_FILE` names a missing file. Two installed skins reference files absent from their folders (`fumi_cp_nissan_200sx_s13\skins\02_blanco` → `GlassExt.dds`, `gmp_bnr34_the_inevitable\skins\04_sonic_silver` → `ext_plate_rear.png`), so the outcome is not documented. The Lua API notes "Since 0.2.2 nothing will happen if the texture is missing" for `setMaterialTexture` ([LUASDK](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/README.md)), but that is the Lua path, not INI.

---

## Q3. Can a replacement point a mesh at a texture that is not in the kn5? Does it work with ksWindscreen, ksPerPixelAlpha and other see-through glass?

### Takeaway
Yes. `RESOURCE_FILE_n` loads any DDS or PNG from disk (and from zips via `file.zip::path`). The Ferrari 296 skins do exactly this on an alpha-blended `ksPerPixelReflection` window mesh. For `ksWindscreen` I found no per-skin RESOURCE_FILE example, but the shader has a `txDiffuse` slot, so the same mechanism should apply.

### Cited Findings
- `RESOURCE_FILE_3 = custom.dds ; FILE refers to a texture on a disk, next to the config`. By contrast, `RESOURCE_TEXTURE_n` "refers to texture in original model". — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- Ferrari 296: an external window mesh with an alpha-blended `ksPerPixelReflection` material gets a skin-folder texture (`EXT_Windscreen.dds`) that is absent from the kn5 (see Q2). — local kn5 parse plus skin config
- Glass shaders in that kn5: `INT_Windshield` uses `ksWindscreen` (blend=1, `txDiffuse = INT_Windshield_Dirt.dds`). So `ksWindscreen` exposes a `txDiffuse` slot that `RESOURCE_0 = txDiffuse` can target. — local kn5 parse of [`cf_296_gt3.kn5`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/cf_296_gt3.kn5)
- Glass-specific CSP template use, with a texture from disk in a skin file: `[INCLUDE: common/materials_glass.ini]` / `[Material_Glass]` / `Materials=...` / `RESOURCE_0 = txDiffuse` / `RESOURCE_FILE_0 = ext_glass_headlight.dds`. — [CARS `cf_ferrari_296_gt3\skins\2023_NLS_Frikadelli_30\ext_config.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/skins/2023_NLS_Frikadelli_30/ext_config.ini). The same pattern appears in CSP's own GT4 "yellow glass" configs. — [CFG `gue\GT4\bmw_f82_yellow_glass.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/gue/GT4/bmw_f82_yellow_glass.ini)
- CSP targets windscreen materials by shader in its generic fix: `MATERIALS = '{ shader:ksWindscreen? & alphaTest:yes }'` then `BLEND_MODE = ALPHA_BLEND` / `CULL_MODE = NONE`. — [CFG `generic\generic_fixes.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/generic/generic_fixes.ini)
- Blend modes other than OPAQUE, ALPHA_TEST and TRANSPARENT_AS_BLACK "might need transparency flag for the mesh" (`IS_TRANSPARENT = 1`). — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- UV2 sticker layers (a separate sticker texture on a second UV set) are supported only by `nePerPixelMultiMap_AT_NMDetail_stickers`, `smCarPaint` (and derivatives) and `stPerPixelMultiMap_specular`. None of these is a glass shader. — [CSP wiki: UV2](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-UV2)

### Inferences
- With `MESHES =` only the texture slot changes; shader, blend mode and the CSP glass settings (from the car-level `[Material_Glass]`) should carry over on the copied material. The Ferrari has a car-level `[Material_Glass] Materials=EXT_Windows` and the skin-level resource swap working together.
- Many cars have separate exterior glass and interior (cockpit-view) glass meshes. A sticker meant to be seen from the cockpit has to go on the interior mesh as well, mirrored if the UVs are shared. `ksWindscreen` meshes are often the interior one.
- Keep the glass texture's original resolution and alpha. For DDS, use a format with alpha (DXT5/BC3 or BC7), or PNG.

### Gaps
- I found no installed example of a per-skin `RESOURCE_FILE` on a `ksPerPixelAlpha` or `ksWindscreen` material specifically. It should work, but that is untested; an in-game check is needed.

---

## Q4. Any CSP way to select PART of a mesh (position, box, left/right, triangles) or to split a mesh?

### Takeaway
Filters cannot select by position, box or triangle; there are no `BOX`, `CENTER/RADIUS` or `isLeft` selectors. CSP does have **`[MESH_SPLIT_...]`**, which regroups whole triangles into a new mesh (optionally with its own new material). It does this either by a plane (`MODE = PLANE`, `SPLIT_AXIS`, `SPLIT_THRESHOLD`), by facing direction (`MODE = LOOK_AT`), or by UV rectangle (`MODE = UV_REGIONS`, which the wiki doesn't document but CSP's own `data_helmets.ini` uses). The new mesh or material can then be targeted by a SHADER_REPLACEMENT. MESH_SPLIT needs a game restart and must come before the sections that use the split mesh.

### Cited Findings
- Official MESH_SPLIT syntax (verbatim from the wiki):
  ```ini
  [MESH_SPLIT_...]
  ACTIVE = 1                ; Quickly enable or disable section
  MESHES = mesh             ; List of meshes to cut
  SPLIT_NAME = name         ; Specify exact mesh name of new split mesh
  SPLIT_POSTFIX =           ; Postfix for the new split mesh, not used if name is set explicitly
  SPLIT_MATERIAL = name     ; Specify exact material name of new split mesh
  SPLIT_MATERIAL_POSTFIX =  ; Postfix for the material for the new split mesh, not used if name is set explicitly
  INSERT_TO = node          ; Specify new parent for new mesh
  INSERT_IN_FRONT = 0
  MODE =                    ; PLANE = Split along a plane based on the SPLIT_AXIS
                            ; LOOK_AT = Split mesh triangles facing given direction
                            ; COPY_FLIPPED = Take mesh, duplicate, then invert direction. Useful to to fix missing interior windows
  ; if MODE = LOOK_AT
  LOOK_AT = 0, 0, 0         ; Cut mesh triangles facing this point relative to the parent of the mesh
  LOOK_AT_THRESHOLD = 0     ; Specify how precisely the faces must be facing the above point to be selected. 0 for all.
  ; if MODE = PLANE
  SPLIT_AXIS = 1, 0, 0      ; axis to cut mesh by (cut will be perpendicular to it, where X is lateral, Y is Longitudinal, Z is vertical
  SPLIT_THRESHOLD = 0.0     ; offset for cut along the line, in meters
  MODEL_SPACE = 0           ; Convert the co-ordinates to use the car root node instead of mesh parent node
  ```
  The wiki also says:
  - "Requires a game restart in order for changes to take effect. Must be placed above any other sections that act on the split meshes."
  - "Splitting does not function recursively, you cannot split a split mesh for a second time."
  - "it's not actually *cutting*, no triangles will be split in two. Just regrouping existing triangles into two different meshes."

  — [CSP wiki: Cars – Meshes splitting](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-Meshes-splitting)
- **UV_REGIONS mode (not on the wiki)**, as used in CSP's shipped helmet data:
  ```ini
  [mesh_split_0]
  MESHES = DRIVER:HELMET_69_SUB1
  MODE = UV_REGIONS
  UV_REFERENCE_SIZE = 1024, 512
  UV_REGIONS_USE_SIZE = 1
  UV_REGION_... = 142.1, 86.5, 110.1, 49.2
  SPLIT_POSTFIX = ___helmet_split
  ```
  — [CFG `extension\config\data_helmets.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/data_helmets.ini)
- The CSP DLL's string table confirms these keys sit together in the MESH_SPLIT parser: `SPLIT_NAME`, `MESH_SPLIT`, `SPLIT_MATERIAL_POSTFIX`, `SPLIT_MATERIAL`, `SPLIT_POSTFIX`, `UV_REFERENCE_SIZE`, `SPLIT_THRESHOLD`, `SPLIT_AXIS`, `LOOK_AT_THRESHOLD`, `ORDERED_NAMING`, `MODEL_SPACE`, `UV_REGION`, `UV_REGIONS_USE_SIZE`, `MODE`, `PLANE`, `INSERT_IN_FRONT`, `INSERT_TO`, `LOOK_AT_NORMALS`, `LOOK_AT`. — strings dumped from the installed [`dwrite.dll`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/dwrite.dll) (CSP 0.3.1-preview2) with `D:\ClaudeData\tmp\csp_scripts\dllstr.py`. `ORDERED_NAMING` and `LOOK_AT_NORMALS` are undocumented.
- Real split-then-retexture chains (CSP's own configs):
  - BMW Z4:
    ```ini
    [MESH_SPLIT_...]
    MESHES = material:CAR_GLASS_black
    SPLIT_MATERIAL_POSTFIX = __csp_glass_fix
    MODE = LOOK_AT
    MODEL_SPACE = 1
    LOOK_AT = 0, 0.5, -0.2
    LOOK_AT_THRESHOLD = 0

    [SHADER_REPLACEMENT_...]
    MATERIALS = CAR_GLASS_black__csp_glass_fix
    ...
    ```
    — [CFG `loaded\bmw_z4.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/bmw_z4.ini)
  - Porsche 911 GT3 Cup 2017, windscreen banner: `MESHES = _8@A`, `SPLIT_MATERIAL_POSTFIX = __csp_banner_fix`, `MODE = LOOK_AT`, then `Materials = EXT_Glass_Banner__csp_banner_fix`. — [CFG `loaded\ks_porsche_911_gt3_cup_2017.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/ks_porsche_911_gt3_cup_2017.ini)
  - Supra: `SPLIT_AXIS = 0, 1, 0`, `SPLIT_THRESHOLD = 0.0`, `SPLIT_POSTFIX = _CUT`, later `SURFACE = SUPRA_LIGHTS_GLASS_CUT`. — [CFG `loaded\ks_toyota_supra_mkiv.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/ks_toyota_supra_mkiv.ini)
  - Commented example: `SPLIT_AXIS = 0, 1, 0  ; axis to cut mesh by (cut will be perpendicular to it)`, `SPLIT_POSTFIX = _CUT   ; name of cut off mesh in this case would be "Headlights_CUT"`. — [CFG `gue\GT4\alpine_yellow_glass.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/gue/GT4/alpine_yellow_glass.ini)
- Left/right split template: CSP's `common/oldschool_lights_reflections.ini` defaults to `SplitAxis = 1, 0, 0`, `SplitThreshold = 0`, `SplitInModelSpace = 0`. It assigns the original mesh `${MeshesToCut}` to `[LOCAL_CUBEMAP_0_LEFT]` (POSITION = +X) and `${MeshesToCut}___loccbmp_cut_` to `[LOCAL_CUBEMAP_0_RIGHT]` (POSITION = -X). — [CFG `common\oldschool_lights_reflections.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/oldschool_lights_reflections.ini)
- Filters have no positional selectors: the documented property list (Q1) has none, and "Features to add later: More properties to filter by." — [CSP wiki: Filtering](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Filtering)
- An alternative is to add sticker geometry instead of splitting:
  - `[MODEL_REPLACEMENT_...]` with `SKINS = red?`, `INSERT = new_model.kn5 ; name of KN5 to insert, should be located next to config file`, `INSERT_IN = COCKPIT_HR` / `INSERT_AFTER`, plus `SCALE`, `ROTATION`, `OFFSET` ("Most of those options have been added in v0.1.60").
  - It "wouldn't work for meshes and nodes with names starting with "AC_" or digits, or containing "WALL"".

  — [CSP wiki: Model replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Model-replacements). CSP's own Ferrari config inserts extra glass kn5s this way (`INSERT=296_yellow_glass.kn5`, `INSERT_AFTER=COCKPIT_HR`). — [CFG `cf\Ferrari_296\296_yellow_glass.ini`](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/cf/Ferrari_296/296_yellow_glass.ini)
- `MESH_ADJUSTMENT` (move/flags only, no geometry selection): `MESHES`, `MOVE_TO`, `MOVE_IN_FRONT`, `LAYER`, `IS_ACTIVE`, `IS_TRANSPARENT`, `IS_RENDERABLE`, `CAST_SHADOWS`. — [CSP wiki: Mesh adjustment](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Mesh-adjustment)
- Lua route (car scripts): `ac.SceneReference:ensureUniqueMaterials()`, `setMaterialTexture('txDiffuse','filename.dds')`, and `projectTexture{...}`, which "Projects texture onto a mesh or few meshes". — [LUASDK](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/README.md)

### Inferences
- Recipe for several windows inside ONE mesh: split first, then retexture the split part through its new material.
  ```ini
  [MESH_SPLIT_0_SKINGEN]
  MESHES = GEO_Windows          ; must be listed ABOVE the shader replacement
  MODE = PLANE
  SPLIT_AXIS = 1, 0, 0          ; lateral -> left/right halves
  SPLIT_THRESHOLD = 0
  MODEL_SPACE = 1               ; car-root coordinates, independent of the mesh's parent node
  SPLIT_NAME = GEO_Windows_skingen
  SPLIT_MATERIAL = skingen_glass_cut

  [SHADER_REPLACEMENT_0_SKINGEN]
  MATERIALS = skingen_glass_cut
  RESOURCE_0 = txDiffuse
  RESOURCE_FILE_0 = skingen_glass_cut.dds
  ```
- If the windows sharing a texture use *different* UV areas, `MODE = UV_REGIONS` is the most precise option, because the generator already knows the UV rectangle of the target window. If they share the *same* UV area, use `MODE = PLANE`: a lateral axis for left/right, a longitudinal axis for front/rear side glass, and two thresholds would need two splits on different meshes, since splits are not recursive. `LOOK_AT` separates by facing (inside/outside, side/rear).
- The generator could choose the axis and threshold automatically: read the kn5 vertex positions of the target window's triangles, as the existing kn5 tools do, and pick a plane that separates them from the other windows.
- Which side of the plane goes into the new mesh is not stated anywhere. In the oldschool template the original mesh is treated as "LEFT" (+X) and the cut part as "RIGHT" (-X), which suggests the cut piece is the negative side. That is unconfirmed, so verify once in game, or set the threshold so the target is unambiguous and test both texture assignments.
- **Axis naming conflict:** the wiki comment says "X is lateral, Y is Longitudinal, Z is vertical". AC/kn5 car space is Y-up and Z-forward, and CSP's configs use `0, 1, 0` for headlight glass. Treat the wiki's Y/Z labels as suspect: verify with the kn5 coordinates, or test in game.
- MODEL_REPLACEMENT INSERT of a generated thin sticker kn5 (a few quads offset ~1 mm from the glass, `DEPTH_MODE = LESSEQUAL` or `STICKERS_FIX = 1`) avoids splitting entirely. It is heavier to implement (writing a kn5), and it needs a restart, since live reload doesn't cover MODEL_REPLACEMENT.

### Gaps
- No documentation found for `UV_REGION_...` value order. `x, y, width, height` in pixels of `UV_REFERENCE_SIZE` when `UV_REGIONS_USE_SIZE = 1` is my reading of the helmet example (`142.1, 86.5, 110.1, 49.2` on 1024×512); x1,y1,x2,y2 when 0 is unverified.
- I found no installed example of `[MESH_SPLIT_...]` inside a **per-skin** ext_config.ini; all 12 MESH_SPLIT sections are in car-level or CSP configs. I also found no documented `SKINS =` key for MESH_SPLIT. A per-skin split should work given the per-parameter lookup chain, but it is untested. Because it changes geometry it needs a full restart, and it could interact with car-level configs that reference the original mesh name (e.g. wipers' `UNDERLYING_SURFACE`, `[Material_Glass]` on that mesh).
- `ORDERED_NAMING` and `LOOK_AT_NORMALS` exist in the DLL but have no documentation.

---

## Q5. Online: does the server need anything, and do other players see per-skin ext_config changes?

### Takeaway
Per-skin ext_config.ini is read locally by each client's CSP while loading that car and skin, so the server needs nothing. Other players see the window sticker only if they have the same skin folder (with the ext_config.ini and the texture) and run CSP. Without CSP, or without the updated skin, they see the stock glass. I found no official statement saying this outright; it follows from the documented lookup chain.

### Cited Findings
- Config lookup is a client-side file chain: Documents cfg, skin folder `ext_config.ini`, car `extension\ext_config.ini`, CSP `extension\config\cars`. Nothing in it comes from the server. — [README (local)](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/read%20me%20to%20save%20yourself%20some%20time.txt)
- Server-side CSP features are separate, opt-in options for "CSP only server", e.g. `[CUSTOM_COLOR]` pit colour change and "Per-car flags" stored in skin IDs in `entry_list.ini`. Servers can also verify file integrity (`[VERIFY_INTEGRITY_...]`, "Available since 0.1.77"). None of this concerns per-skin visual configs. — [CSP wiki: Misc – Server extra options](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Misc-%E2%80%93-Server-extra-options)
- Community tester: ext_config cannot override physics files like car.ini, tyres.ini or engine.ini, "which is intentional to prevent online cheating"; graphics-only data can be overridden. — [GTPlanet AC PC Mods General Discussion thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/) (search snippet; exact page not verified)
- MODEL_REPLACEMENT refuses meshes/nodes starting with "AC_" or digits, or containing "WALL", "to make sure this option couldn't be used for cheating". Visual configs are deliberately kept away from physics/collision meshes. — [CSP wiki: Model replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Model-replacements)

### Inferences
- For Ratty's Racing nights, distribute the generated skin folder (textures + `ext_config.ini`) to every driver, exactly like a normal skin. The server only needs the skin name in `entry_list.ini`, as usual.
- A skin's ext_config only changes visuals (shader replacement / split), so it shouldn't trip the physics checks of the watchdog or AC's data checksums. Those check `data`/physics files, not skin folders (inference; not tested).

### Gaps
- No official CSP document explicitly says "other players see per-skin ext_config changes only if they have the skin". This is inferred from the client-side lookup chain.
- No source found on whether any CSP server option can disable client car configs. None appears in the Server extra options page as read.
