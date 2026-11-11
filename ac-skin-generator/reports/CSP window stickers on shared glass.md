# Give one window its own material

Custom Shaders Patch (CSP) can put a sticker on exactly one window, but never by painting the shared texture. Anything placed in shared or mirrored texels shows on every window that samples them, so the fix is always to give the target window **its own material**. When the target window is a separate mesh, a per-skin `ext_config.ini` with `[SHADER_REPLACEMENT_...]`, `MESHES = <that mesh>`, `RESOURCE_0 = txDiffuse` and `RESOURCE_FILE_0 = <new texture in the skin folder>` does the job, because targeting by `MESHES` copies the material for that mesh alone. Ferrari 296 GT3 skins installed on Nik's PC already ship exactly this on an alpha-blended window. When both windows sit inside one mesh, a `[MESH_SPLIT_...]` plane cut along the centreline (`SPLIT_AXIS = 1, 0, 0`, `MODEL_SPACE = 1`) first regroups the triangles into two meshes, then the same texture swap targets the split piece. CSP's own configs use this chain, but no installed skin runs it from a skin folder, and the docs don't say which half gets the new name. The most robust but most laborious route is to generate a small sticker KN5 and insert it from the skin folder with `[MODEL_REPLACEMENT_...] INSERT =`; installed skin configs on Nik's PC contain about 2,120 model-replacement sections. Projected decals, UV2 sticker layers, the Paintshop app and Lua projection do not solve the problem: they either paint back into the shared texels or need shaders that glass does not use. Every method beyond painting a window's own UV area needs CSP on each viewer's PC and the complete skin folder on each client; the server needs nothing. The generator should choose a method per car from a ladder. First come dedicated banner meshes and unique UV areas (vanilla AC), then a per-mesh texture swap, then a split, and an inserted KN5 last. Throughout, the shared texture stays mirror-safe for drivers without CSP.

## The pros avoid shared glass by building separate banner meshes

Mirrored UVs are a space-saving modelling choice that a skinner cannot undo. When symmetric parts share one UV area, the texture flips on one side, and the only real fix is a separate UV map for the part ([r/iRacing via redlib](https://redlib.belloworld.it/r/iRacing/comments/1f9wuoz/well_this_is_disappointing)). For AC skinners, model UVs "can't be changed" without editing the model ([OverTake skinning tutorial](https://overtake.gg/threads/skinning-assetto-corsa-cars-from-nothing-using-mudbox-and-photoshop.147080/page-6)). AC makes it worse: a skin-folder texture replaces every texture of that file name, in every material that uses it, so an edited `glass.dds` lands on every window that shares it. AC also has no decal shader, so forum advice has long been that decals must be real 3D objects on the car ([GTPlanet](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-13878439)).

The big teams therefore build window stickers as **separate overlay meshes with their own material and texture**, and skins just override that one file. Kunos's Porsche 911 GT3 R 2016 has `GEO_BANNER` with material `EXT_BANNER` and texture `EXT_Banner.dds`, plus a separate `INT_BANNER`, and every one of its skins carries an `EXT_Banner.dds` ([kn5](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_porsche_911_gt3_r_2016/porsche_911_gt3_r.kn5)). The Kunos Ferrari 296 GT3 goes further, with per-side `EXT_DECALS_DOOR_L` / `EXT_DECALS_DOOR_R` and `EXT_GLASS_DOOR_L` / `_R` meshes ([kn5](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_ferrari_296_gt3/ferrari_296_gt3.kn5)), and the Celica ST185 has `GEO_Doorsticker_L` / `_R` ([kn5](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_celica_st185/toyota_celica.kn5)). Across Nik's 868 installed cars, **6,223 skin-folder textures in 503 cars** have banner, sticker, decal, window or glass names (the count also includes light and helmet glass). `ext_banner_colour.dds` alone appears 660 times in 66 cars, and `banner.dds` 435 times in 55 ([content/cars survey](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/)). The McLaren 650 GT3 is the instructive exception: it has no banner mesh, and its banner is painted into `Glass_Windows_D.dds`. CSP even ships a `Material_WindscreenBanner` template for such meshes, built on `ksWindscreen` with `IS_TRANSPARENT = 1` ([materials_interior.ini](https://github.com/ac-custom-shaders-patch/acc-extension-config/blob/master/config/cars/common/materials_interior.ini)).

Two details matter for a generator. Cockpit views often use a separate interior banner texture, so writing only the exterior file leaves the sticker missing or wrong from the driver's seat ([OverTake banner pack](https://www.overtake.gg/downloads/assetto-corsa-windscreen-banner-pack.7472/)). And one interior windscreen texture had a mirror line down the middle; the fix was to re-UV-map the glass, which only the modder can do, not a skin ([GTPlanet](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4532)).

When the car lacks a suitable mesh, skinners with CSP add or remove one per skin. Twelve skins of `bm_amg_evo_gt3_2020` hide the stock banner and insert their own with `HIDE=EXT_Banner001, EXT_Banner002`, `INSERT=Banner.kn5`, `INSERT_AFTER=COCKPIT_HR` ([skin folder](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bm_amg_evo_gt3_2020/skins/%234_HRT_DTM_2021/)). A Renault 5 Turbo skin switches off a built-in window logo with `[MESH_ADJUSTMENT_...] MESHES = turbo_window_logo / IS_RENDERABLE = 0` ([ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/renault_5_turbo_r/skins/blanc_turbo/ext_config.ini)). Without CSP, skinners fall back on panes with unique UVs, on designs that read fine mirrored, or on no side-window text at all. I found no AC-specific guide to mirrored side-window stickers. OverTake and GTPlanet block automated fetches, so beyond the installed files, community practice here rests on search-result snippets.

## A per-skin shader replacement gives one mesh its own texture

CSP looks up each car parameter through a chain of config files, and `ext_config.ini` in a car's skin folder is one link in it. That file ranks below the user's Documents configs and above the car's own `extension\ext_config.ini` and CSP's shipped configs ([CSP readme](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/read%20me%20to%20save%20yourself%20some%20time.txt)). Because lookups merge per parameter, a skin file only needs its extra sections. The Frikadelli Ferrari 296 skin's 40-line file adds to the car's 1,421-line config rather than replacing it ([skin ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/skins/2023_NLS_1_Frikadelli_30/ext_config.ini)). The minimal section for one window is:

```ini
; content/cars/<car>/skins/<skin>/ext_config.ini
; --- skingen begin ---
[SHADER_REPLACEMENT_0_SKINGEN_WINDOW_RR]
MESHES = GEO_Window_RR, GEO_Window_RR_LOD_B   ; exact mesh names, comma list, '?' is the wildcard
RESOURCE_0 = txDiffuse
RESOURCE_FILE_0 = skingen_window_rr.dds       ; file in this skin folder, name not used in the kn5
; --- skingen end ---
```

The documented header lists `MATERIALS` and `MESHES` as targets and warns that "each mesh in MESHES would get its own material". `RESOURCE_FILE_n` "refers to a texture on a disk, next to the config". The other resource kinds are `RESOURCE_TEXTURE_n` (a texture already in the kn5), `RESOURCE_REF_n` (the texture already in a given slot) and `RESOURCE_COLOR_n` (a solid colour). The wiki asks for numbered pairs rather than `...` here ([CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)). That material copy is the whole trick. With the default `SHARED_MATERIALS = 0`, CSP duplicates the material for the matched mesh. A value of `1` would leave materials uncopied and apply the change only where no other mesh shares the material ([generic_fixes.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/generic/generic_fixes.ini)). Targets accept comma lists, `?` as the wildcard (`*` is not one) and `key:value` selectors such as `material:`, `shader:`, `texture:` and `lod:`. They also accept quoted boolean expressions such as `'{ lod:A & GEO_Window_RR }'`, using `!`, `&`, `|` and `^` ([CSP wiki: Filtering](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Filtering)). **No selector picks by position, side or triangle**, which is why the one-mesh case needs a split.

The precedent is exact. Skin configs of `cf_ferrari_296_gt3` contain `MESHES=EXT_Windows`, `RESOURCE_3 = txDiffuse`, `RESOURCE_FILE_3 = EXT_Windscreen.dds`. That file exists only in the skin folders, and the kn5 has no texture of that name. Mesh `EXT_Windows` uses an alpha-blended `ksPerPixelReflection` material whose `glass_clear.dds` is shared with three other glass materials ([skin config](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/skins/2023_NLS_1_Frikadelli_30/ext_config.ini); [kn5](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/cf_ferrari_296_gt3/cf_296_gt3.kn5)). A `trr_amr_vantage_gt3` skin does the same for one headlight glass mesh, though with the undocumented spelling `RESOURCE_0_FILE`, which the generator should not copy ([skin config](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/trr_amr_vantage_gt3/skins/N24H_69_Doerr%20Motorsport/ext_config.ini)). The same Ferrari kn5 shows that `ksWindscreen` has a `txDiffuse` slot, so the mechanism should reach interior windscreens too. But no installed skin swaps a texture on a `ksWindscreen` or `ksPerPixelAlpha` window, so that needs one check in game.

The replacement texture has to respect how glass renders. The copied material keeps its shader and blend mode, so the new file should be the original glass texture at its original size, alpha intact, with the sticker composited on top. A sticker-only image would turn the rest of the pane opaque or invisible. It needs a format with alpha (BC3/DXT5, BC7 or PNG). Its name must not match any texture in the kn5; otherwise vanilla AC's by-name skin override would also apply it to every material using that name. If the target window's UVs are mirrored, the art is flipped in UV space so it reads correctly in 3D; the generator can work this out from the kn5's UV-to-position mapping. The section must list every LOD mesh that shows the window, or the sticker pops in and out with distance. It must also list the interior glass mesh if the sticker should be visible from the cockpit.

Two unknowns remain. CSP does not document what happens when `RESOURCE_FILE` names a missing file (two installed skins do exactly that), so the generator must always ship the file. And one GTPlanet user reported that a skin-folder `SHADER_REPLACEMENT` "did not work". That report is unresolved and contradicted by the hundreds of working examples installed here ([GTPlanet](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14632359)). Shader replacements reload live when the file changes, but removing a section does not restore the original values until a restart ([CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)).

## MESH_SPLIT separates windows that live in one mesh

A per-mesh swap cannot help when the left and right windows are one mesh, because that mesh has one material. CSP's answer is `[MESH_SPLIT_...]`, which regroups whole triangles into a new mesh, optionally with a new material. Its documented keys are ([CSP wiki: Meshes splitting](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-Meshes-splitting)):

```ini
[MESH_SPLIT_...]
MESHES = mesh             ; meshes to cut
SPLIT_NAME = name         ; exact name of the new mesh (or SPLIT_POSTFIX = _CUT)
SPLIT_MATERIAL = name     ; exact new material name (or SPLIT_MATERIAL_POSTFIX)
INSERT_TO = node          ; optional new parent
MODE = PLANE              ; PLANE, LOOK_AT or COPY_FLIPPED
SPLIT_AXIS = 1, 0, 0      ; the cut is perpendicular to this axis
SPLIT_THRESHOLD = 0.0     ; offset along the axis, in metres
MODEL_SPACE = 0           ; 1 = car-root coordinates instead of the mesh parent's
LOOK_AT = 0, 0, 0         ; LOOK_AT mode: take triangles facing this point
LOOK_AT_THRESHOLD = 0
```

The wiki's rules shape everything. A split "requires a game restart" and "must be placed above any other sections that act on the split meshes". It cannot be repeated on a split mesh. And it is "not actually *cutting*": no triangle is split in two, so a triangle that straddles the plane goes whole to one side. CSP's helmet data also uses an undocumented `MODE = UV_REGIONS`, with a `UV_REFERENCE_SIZE` and `UV_REGION_...` rectangles ([data_helmets.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/data_helmets.ini)). The installed CSP binary has two more undocumented keys among the split parser's strings, `ORDERED_NAMING` and `LOOK_AT_NORMALS` ([dwrite.dll](file:///D:/SteamLibrary/steamapps/common/assettocorsa/dwrite.dll)).

CSP uses split-then-retexture chains in its own configs for Kunos cars. For the BMW Z4 it splits `MESHES = material:CAR_GLASS_black` with `SPLIT_MATERIAL_POSTFIX = __csp_glass_fix`, then a `[SHADER_REPLACEMENT_...]` targets `CAR_GLASS_black__csp_glass_fix` ([bmw_z4.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/bmw_z4.ini)). It does the same to the Porsche 911 GT3 Cup 2017 windscreen banner ([ks_porsche_911_gt3_cup_2017.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/ks_porsche_911_gt3_cup_2017.ini)). An installed MR2 mod splits meshes at the centreline with `SPLIT_AXIS = 1, 0, 0`, `SPLIT_THRESHOLD = 0.0` ([MR2 ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/streetcarpack_toyota_mr2_sw20/extension/ext_config.ini)), and CSP's local-cubemap template cuts the same way to separate left and right headlights ([oldschool_lights_reflections.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/oldschool_lights_reflections.ini)). For a skin generator the chain becomes:

```ini
[MESH_SPLIT_0_SKINGEN]            ; must sit above the replacement that uses it
MESHES = GEO_Windows
MODE = PLANE
SPLIT_AXIS = 1, 0, 0              ; lateral: left/right halves
SPLIT_THRESHOLD = 0
MODEL_SPACE = 1
SPLIT_NAME = GEO_Windows_skingen

[SHADER_REPLACEMENT_0_SKINGEN]
MESHES = GEO_Windows_skingen
RESOURCE_0 = txDiffuse
RESOURCE_FILE_0 = skingen_windows_half.dds
```

One centreline cut is usually enough, even when the mesh holds the windscreen and all four side windows. Front and rear windows on the same side normally occupy different UV areas, so the half's private texture can carry the sticker in the target window's area only. The windscreen is cut in two along triangle edges, but it looks unchanged because both halves keep its texels. A possible advantage of naming the new mesh rather than setting `SPLIT_MATERIAL` is that the split piece should keep the original material. If so, car-level settings that target the glass by material name, such as a `[Material_Glass]` upgrade, would still reach it before the per-mesh replacement copies the material. That is my inference, not documented behaviour.

Three questions must be settled in game before the generator relies on this.

**Which side becomes the new mesh?** Nothing documents it. CSP's cubemap template treats the original mesh as the +X side and the cut piece as −X, which suggests the cut is the negative side, but that is inference.

**Which sign of X is car-left?** The axis labels are muddled: the wiki labels Y longitudinal and Z vertical, while the model-replacement docs say "for cars, X is left-right and Y is up-down" ([CSP docs: Model replacements](https://cup.acstuff.club/docs/csp/general/model-replacements)). X is lateral in both, so a left/right split is safe, but neither page says which sign is car-left. This and the first question are global CSP behaviour, so a single test on one car settles both for every car.

**Does a split work from a skin folder?** No installed skin-folder config uses `[MESH_SPLIT_...]`; all of the dozen or so installed examples are car-level, and no `SKINS =` key is documented for splits. The per-parameter lookup suggests a skin-level split works, but nobody has tested it. Putting it at car level instead would change the car mod for every skin, and that file would have to be sent to every driver separately.

## An inserted sticker KN5 sidesteps the UVs entirely

When a window's UVs cannot carry a sticker at all, or a single non-repeatable split cannot isolate it, the generator can add geometry instead. `[MODEL_REPLACEMENT_...]` takes the following keys ([CSP docs: Model replacements](https://cup.acstuff.club/docs/csp/general/model-replacements)), most of them "added in v0.1.60":

| Key | Purpose |
|---|---|
| `FILE` | which kn5 (LOD) to modify |
| `INSERT = new_model.kn5` | kn5 to add; it "should be located next to config file" |
| `INSERT_AFTER`, `INSERT_IN` | where to attach the inserted kn5 (either key or both) |
| `HIDE` | meshes to hide |
| `SKINS` | limits the section to listed skins (cars only) |
| `SCALE`, `ROTATION`, `OFFSET` | transform of the inserted model |

Of 2,530 `[MODEL_REPLACEMENT` sections across Nik's cars, **about 2,120 are in skin-folder configs**. Many insert kn5s that exist only in those skin folders. The Aston Martin Vantage GT3 Evo skins insert `numberlights.kn5`, one section per LOD ([skin ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/acf_aston_martin_vantage_gt3_evo/skins/2024_ELMS_59_Racing%20Spirit%20of%20Leman/ext_config.ini)). A JZA80 skin inserts a body decal, `junya_decal.kn5`, with an alpha-tested `ksPerPixelAT_NM` material ([skin folder](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/naz_jza80_ridox_modern/skins/07_csj_demo/)). A generated sticker would be a few quads modelled in car coordinates, a millimetre or two outside the glass, with its own alpha-tested material:

```ini
[MODEL_REPLACEMENT_0_SKINGEN]
FILE = <car_main>.kn5
INSERT = skingen_sticker_rr.kn5
INSERT_IN = <window or door node>   ; use the moving node if the window or door animates
```

The costs are real. The generator must write a valid kn5, which the project's existing kn5 tools make feasible but not trivial. Model replacements need a restart, because live reload skips them ([CSP wiki: About guessed configs](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-About-guessed-configs)). Meshes and nodes whose names start with `AC_` or a digit, or contain `WALL`, cannot be used. Z-fighting and transparency sorting against the glass need tuning with keys such as `STICKERS_FIX = 1` ("great for stickers"), `DEPTH_MODE` and `IS_TRANSPARENT` ([CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)). A skin with custom geometry should also set `CUSTOM_SKIN_SHADOWS = 1`, so CSP caches its shadows separately ([CSP wiki: Fake Shadows FX](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-Fake-Shadows-FX)). In exchange, the sticker gets its own UVs, resolution and alpha, and works whatever the glass mapping is.

## Projection, UV2, Paintshop and Lua all land back in the shared texels

CSP has no projected-decal feature for cars. No `[PROJECTED…]`, `[DECAL…]` or `[STICKER…]` sections appear in its configs or in strings from its binary. CSP is closed source, so this is strong evidence rather than proof. Its only sticker layer is a separate texture mapped through UV2, a second unwrap stored in a `.uv2` file. Content Manager builds that file from an FBX with two UV sets, and only `nePerPixelMultiMap_AT_NMDetail_stickers`, `smCarPaint` and `stPerPixelMultiMap_specular` read it ([CSP docs: UV2](https://cup.acstuff.club/docs/csp/general/uv2)). CSP checks skin folders first for `.uv2` files, so a per-skin unwrap is technically possible. But the glass templates (`smGlass`, `smGlass_emissive`, `smGlass_phel`) have no sticker or UV2 input ([materials_glass.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_glass.ini)), and moving glass to a car-paint shader loses the glass look.

The Paintshop app paints by projecting stamps from world space into the material's `txDiffuse` canvas through `projectTexture`. Its symmetry option simply mirrors the stamp across car X and projects it again ([Paintshop.lua](https://raw.githubusercontent.com/ac-custom-shaders-patch/app-paintshop/main/Paintshop.lua)). The SDK's `withDepth` option only decides which of two overlapping triangles writes a texel ([lua-sdk lib.lua](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/lib.lua)). Both windows still read that texel, so a projected sticker still shows on both sides, mirrored on one.

Car Lua scripts could build a sticker quad at runtime with `createMesh` or `loadKN5` and pick per-skin textures with `ac.getCarSkinID`. But the SDK's path rules list car scripts only under the car's `extension` folders and CSP's config folders ([rules.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/rules.json)), and no installed skin config declares a script. That makes scripts a car-level feature, not a skin feature. `ui_skin.json` holds only skin metadata and plays no part.

## CSP is required on every viewer's PC; the server needs nothing

| Method | Two separate meshes, shared texels | Both windows in one mesh | Needs CSP | Restart to see changes | Proven from a skin folder |
|---|---|---|---|---|---|
| Paint the window's own UV area | Only if UVs are unique | Only if UVs are unique | No | No | Yes (vanilla) |
| `SHADER_REPLACEMENT` + `MESHES` + `RESOURCE_FILE` | Yes | No | Yes | No (live reload) | Yes |
| `MESH_SPLIT` + `SHADER_REPLACEMENT` | Not needed | Yes | Yes | Yes | No (untested) |
| `MODEL_REPLACEMENT` `INSERT` sticker kn5 | Yes | Yes | Yes | Yes | Yes |
| UV2 stickers / Paintshop / Lua projection | No | No | Yes | — | — |

The installed CSP is 0.3.1-preview2 ([data_manifest.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/data_manifest.ini)). All the INI routes predate it comfortably: quoted filter expressions date from 0.1.25-preview183, and property selectors from 0.1.62 ([CSP wiki: Filtering](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Filtering)). Model-replacement transforms date from 0.1.60, and Paintshop needs 0.1.77 ([app-paintshop](https://github.com/ac-custom-shaders-patch/app-paintshop)). I could not find which version introduced per-skin `ext_config.ini`, but the current readme documents it, and more than 2,100 installed skins depend on it.

Online, the sticker is purely a client-side affair. CSP finds configs through a chain of local files and gets nothing from the server ([CSP readme](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/read%20me%20to%20save%20yourself%20some%20time.txt)). AC does not share skins automatically; at most a server can offer download links through Content Manager's missing-content feature ([Emperor Servers wiki](https://wiki.emperorservers.com/assetto-corsa-server-manager/share-content-with-content-manager-wrapper)). Every driver needs the livery under the same name in the same car folder ([RaceDepartment](https://racedepartment.com/threads/how-to-use-custom-liveries-online.197286/)). So another driver sees the one-window sticker only with **the identical skin folder** (the `ext_config.ini` plus every DDS and kn5 it names) **and** CSP. A driver with the skin but no CSP sees the shared texture as painted. The server only needs the skin name in its entry list, as for any skin. CSP's server options are opt-in, and no source says whether its integrity checks (`[VERIFY_INTEGRITY_...]`, since 0.1.77) cover skin folders ([CSP wiki: Server extra options](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Misc-%E2%80%93-Server-extra-options)). According to one community tester, `ext_config` cannot override physics files such as car.ini or tyres.ini, which is "intentional to prevent online cheating" ([GTPlanet](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/)). A sticker config should therefore not trip the physics-only watchdog, though nobody has tested that.

## A five-rung ladder chooses the method per car

The decision is made per window, from the kn5, before any pixel is drawn. For each target window, the generator should read:

- the mesh name and its LOD meshes;
- the material, shader and diffuse texture;
- how many texels the window's triangles cover, and whether the UVs are mirrored;
- whether any other mesh samples the same texels;
- whether the window shares its mesh with its mirror twin;
- whether an interior twin mesh exists.

| Rung | What the kn5 shows | Method | CSP | Evidence |
|---|---|---|---|---|
| 1 | A dedicated banner, sticker, sponsor, number or decal mesh covers the pane (incl. per-side `_L` / `_R`) | Paint that texture; hide an unwanted side with `HIDE` or `IS_RENDERABLE = 0` | No (hiding: yes) | Kunos, RSS, ACF practice |
| 2 | The window has its own UV area that no other mesh samples | Paint only that area of the shared texture | No | Vanilla AC |
| 3 | The window is its own mesh but shares texels with another | Per-skin `SHADER_REPLACEMENT`, `MESHES`, `RESOURCE_FILE` | Yes | Ferrari 296 skins |
| 4 | The window shares a mesh and texels with its mirror twin | Per-skin `MESH_SPLIT` plane cut, then rung 3 on the split piece | Yes | CSP's own configs; per-skin untested |
| 5 | The UVs cover too few texels for a legible sticker, or one cut cannot isolate the window | Insert a generated sticker kn5 with `MODEL_REPLACEMENT` | Yes | AMG and Aston skins |

On rungs 3 to 5 the shared texture stays untouched, or carries only a mirror-safe design, so non-CSP viewers see clean glass rather than backwards text. Where that matters, numbers and names can go on the door instead. More than 2,100 installed skins already have an `ext_config.ini`, so the generator must merge into an existing file, never overwrite it. It should keep its own sections inside a marked block with distinctive names such as `[SHADER_REPLACEMENT_0_SKINGEN_1]`, so re-runs replace only its own lines and cannot collide with a section of the same name at car level. It must also ship every file the block names inside the skin folder, so one download is complete.

One in-game session on a car Nik actually races should precede any rollout. That session must answer four questions:

- Does a per-skin texture swap work on a `ksWindscreen` or `ksPerPixelAlpha` pane?
- Does a skin-level `MESH_SPLIT` load at all?
- Which side of the plane gets the new name, and which sign of X is car-left?
- What happens when a `RESOURCE_FILE` is missing?

## Conclusion

The question looks like an image problem, but it is a topology problem. A sticker reaches one window only when that window has private texels, and CSP's whole toolbox is just three ways to create them: copy a material, regroup triangles, or add geometry. The generator's decisive component is therefore its kn5 analysis rather than its compositing. The method follows from mesh boundaries, UV extent and texel sharing, and the compositing step only changes in which texture it writes to and whether it flips the art.

The remaining unknowns are smaller than they look. The side convention of `MESH_SPLIT`, the sign of car X and skin-level split support are CSP-wide behaviours, so one test resolves them for all 868 cars. Car-specific risk then shrinks to UV quality, which the generator can measure in advance. The real constraint is social, not technical: every rung above vanilla shows only for drivers who have both CSP and the identical skin folder. For Ratty's Racing, that makes skin distribution part of the feature, and the non-CSP view a design target in its own right.
