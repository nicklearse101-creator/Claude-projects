# Recolouring AC car interiors per skin with CSP and Content Manager (no kn5 or data edits)

Scope: legitimate, documented ways to change the colour of seats, dashboard, door cards, roll cage, carpet and similar parts from a car's `skins\<skin>\` folder. The three routes are (a) a skin texture that uses the same name as a texture in the kn5, (b) a CSP `ext_config.ini` placed in the skin folder, and (c) CM Paint Shop rules in `ui\cm_paintshop.json`.

Method: read-only scan of Nik's install `D:\SteamLibrary\steamapps\common\assettocorsa` (all `content\cars\*\extension\ext_config.ini`, `content\cars\*\skins\*\ext_config.ini`, and CSP's `extension\config\cars\**.ini`, using a parser script in `D:\ClaudeData\tmp\interior_csp\scan.py` with raw output in `scan_out.txt`), plus the CSP docs (cup.acstuff.club, the GitHub wiki) and CM source code (github.com/gro-ove/actools). Today is 2026-11-17, and the installed CSP configs are the ones Nik's CSP currently ships.

Local file links use `file:///` URLs. Spaces are encoded as `%20` and `#` as `%23`.

---

## Q1. Can interior textures be overridden by name from the skin folder (route a)?

### Takeaway
Yes. This is the standard AC skin mechanism and Kunos itself uses it for interiors: Kunos skin folders on Nik's PC carry many interior textures (`leather_seat.dds`, `carpet.dds`, `metal_detail_int.dds` and others). Any file in `skins\<skin>\` whose name matches a texture in the kn5 replaces that texture everywhere it is used, which is also the route's main weakness when a texture is shared.

### Cited Findings
- Interior texture names found across Kunos (`ks_*`) skin folders on Nik's PC, with the number of skin folders that contain each one: `leather_seat.dds` 94, `leather_bottom.dds` 89, `leather_top.dds` 49, `carpet.dds` 46, `leather_1/2/3.dds` 40 to 45 each, `metal_detail_int.dds` 34 (roll cage or interior paint), `stock_dash_cf.dds` 33, `custom_trim_d.dds` 28, `leather_trim_red.dds` 26, `int_sponsor.dds` 19, `interior_details.dds` 18, `cinture.dds` (belts) 11, `int_stitching.dds` 10, `belt_colour.dds` 9, `leather_dash.dds` 6. — [Local scan of content\cars\ks_*\skins\*\](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/)
- Community texture packs for AC tell users to copy interior textures into every skin folder. One mod notes that most skin folders carry their own roll-cage, interior-paint, gear-knob and team-logo textures, and that a mod update overwrites them. — [GTPlanet AC mods thread (forum, community-reported)](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14503009)
- CM's Paint Shop guesses each texture's role from its file name, and the guessed names include interior ones: `carpet.dds` (carpets, tint), `cuciture.dds` (interior seams, tint), `seat_logo_D.dds` (tint), `PlasticDetail_color.dds` (plastic, solid), `cloth_detail.dds` (cloth, solid), `cloth_seats.dds` (seats, tint), `alcnt.dds` (interior, tint), `leather.dds` (tint), `car_paint_roll_cage.dds` (roll cage, solid). Numbered variants 0 to 6 also exist: `interior_plastics_detail<X>.dds`, `carpet<X>.dds`, `INT_Trim<X>.dds`, `INT_fabric<X>.dds`, `leather_seat<X>.dds`, `alcnt_cust<X>.dds`, `leather_<X>.dds`. These names exist to match original Kunos cars and some mods. — [CSP docs: Default names for Paint Shop in Custom Showroom](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom)
- The same page says that in `ksPerPixelMultiMap`-style materials, "Alpha in `txDiffuse` acts as a mask for `txDetail`". — [CSP docs: Default names for Paint Shop](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom)
- CSP's interior material library says Kunos-style interior materials keep the occlusion map in `txDiffuse` and the colour in `txDetail`: "Those templates are meant for materials set in Kunos style: with occlusion map in “txDiffuse” and color in “txDetail”". — [Local: extension\config\cars\common\materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)

### Inferences
- On a Kunos-style interior, the cheapest per-skin recolour is often a small tiling colour texture saved under the `txDetail` name (for example `leather_seat.dds` when that is the detail map). The AO and shape stay in the untouched `txDiffuse`. Which slot holds the colour has to be checked per car (CM Showroom, or Nik's kn5 reader).
- A same-name override applies to every material and every LOD kn5 that references that texture. It cannot target a single part when the texture is shared (see Q6).
- A same-name override works without CSP, so it is the most portable route. CSP `ext_config` tricks need CSP on the viewer's PC.

### Gaps
- I found no official Kunos document that states the override rule (any file in the skin folder that matches a kn5 texture name wins). The evidence here is Kunos's own skin folders and community practice, not a spec.
- Not verified: whether file names are matched case-insensitively, and whether the file extension has to match (`.dds` vs `.png`). Nik's tool should keep the exact name the kn5 uses.

---

## Q2. Exact `ext_config.ini` syntax (route b): swap an interior material's texture for a skin-folder file, or colour it without any new texture

### Takeaway
To swap a texture, use `[SHADER_REPLACEMENT_...]` with `MATERIALS` (preferred) or `MESHES`, then `RESOURCE_n = <slot>` and `RESOURCE_FILE_n = file.dds`. The file is looked up "next to the config", which means the skin folder when the `ext_config.ini` sits in the skin. To set a flat colour without a texture, use `RESOURCE_COLOR_n = r, g, b`, which creates a 1×1 solid texture in that slot. `ksDiffuse` and `ksAmbient` are single-number brightness multipliers on the Kunos shaders, not RGB tints. A true colour tint without a texture is therefore done by putting a 1×1 colour into the slot that is multiplied in, usually `txDetail` on Kunos-style multimap interiors.

### Cited Findings
- Documented `SHADER_REPLACEMENT` keys, quoted from the official example:
  - `MATERIALS = tree?, texture:grass?.dds`, `MESHES = mesh_bush_?`, and `SKINS = red?` with the comment "list of skins to use replacement with (only for cars)".
  - `SHADER = ksTree_ppshadows`, and `SHADER_OVERRIDE_0 = ksTree, ksGrass` ("if original is ksTree, use ksGrass instead").
  - `PROP_0 = ksAmbient, 0.4` and `PROP_... = ksEmissive, 1, 0, 0`, where "..." fills indices automatically. The alternative form is `KEY_0 = ksAmbient` / `VALUE_0 = 0.4`, up to `KEY_99`.
  - `RESOURCE_0 = txDiffuse` plus one of four sources:
    - `RESOURCE_TEXTURE_0 = name_of_texture_in_kn5.dds` ("TEXTURE refers to texture in original model")
    - `RESOURCE_REF_1 = txDetailNM` ("REF refers to original texture in certain slot")
    - `RESOURCE_COLOR_2 = 1, 1, 1` ("COLOR creates new 1×1 solid color texture")
    - `RESOURCE_FILE_3 = custom.dds` ("FILE refers to a texture on a disk, next to the config")
  - Do not use "..." with `RESOURCE_` keys, so that each slot stays paired with its source.
  - `FILL_MISSING_TEXTURES = 1` creates missing textures automatically. The defaults are white `txDiffuse`, `txMaps` and `txDetail`, and a flat `(127,127,255)` normal map.
  - `BLEND_MODE` accepts OPAQUE, ALPHA_TEST, ALPHA_BLEND, TRANSPARENT_AS_BLACK, ADD/ALPHA_ADD and MULTIPLY/ALPHA_MULTIPLY. Opaque and alpha test are the fastest.
  
  — [CSP docs: Shader replacements (CUP v65 page)](https://cup.acstuff.club/docs/csp/general/shader-replacements); [CSP wiki: General – Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- Prefer `MATERIALS` over `MESHES`: when properties change, "each mesh in MESHES would get its own material", which adds GPU draw calls. — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- Shader replacements are static. They are applied once, during loading or after a config change, and removing a section does not restore the old values until the car reloads. — [CSP wiki: Shader replacements (search summary)](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- CSP's own template code confirms four ways to name a texture source. A number or a table becomes `RESOURCE_COLOR_n`, a value starting with `/` becomes `RESOURCE_TEXTURE_n` (a kn5 texture), a value containing "." becomes `RESOURCE_FILE_n`, and anything else becomes `RESOURCE_REF_n`. This is the `_InteriorPBR_GuessResourceType` function. — [Local: materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)
- `RESOURCE_COLOR` in real use on Nik's PC. Every `gt4_*` car (alpine_a110, aston_martin_vantage, audi_r8, bmw_m4 and others) blacks out an interior display's diffuse with `MATERIALS = INT_Racelogic`, `RESOURCE_2 = txDiffuse`, `RESOURCE_COLOR_2 = 0,0,0` (plus `emChannelsMode`/`emSkipDiffuseMap` props). `gt4_bmw_m4` uses `RESOURCE_COLOR_0 = 1, 1, 1`, and `naz_jza80_ridox_modern` uses `RESOURCE_COLOR_1 = 1, 1, 1`. — [Local: gt4_alpine_a110\extension\ext_config.ini, line ~1181](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gt4_alpine_a110/extension/ext_config.ini); [Local: gt4_bmw_m4\extension\ext_config.ini, line 1180](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gt4_bmw_m4/extension/ext_config.ini)
- `RESOURCE_FILE` from a skin folder already works in Nik's own tool. The Sunbeam skin `ratty_s` (Ratty's4Skin) has `MESHES = INT_GLASS_CENTER`, `RESOURCE_0 = txDiffuse`, `RESOURCE_FILE_0 = r4s_windshield2_clear.dds`, and the same pattern on `EXT_GLASS_*` meshes. — [Local: talbot_sunbeam_lotus_81_works_backup_v6\skins\ratty_s\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/talbot_sunbeam_lotus_81_works_backup_v6/skins/ratty_s/ext_config.ini)
- A skin-folder `RESOURCE_TEXTURE` example from a third-party skin: `MATERIALS = EXT_Carpaint_Inst`, `PROP_... = detailUVMultiplier, 700`, `RESOURCE_3 = txDetail`, `RESOURCE_TEXTURE_3 = carbon_fiber2.dds`. — [Local: ng_lexus_rcf_gt3\skins\VRomans\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ng_lexus_rcf_gt3/skins/VRomans/ext_config.ini)
- `PROP` names used on Nik's PC, counted over every shader replacement (car / skin / CSP-config): `ksDiffuse` 448 / 120 / 157, `ksAmbient` 440 / 122 / 138, `ksSpecular`, `ksSpecularEXP`, `fresnelC`, `fresnelEXP`, `fresnelMaxLevel`, `ksEmissive`, `detailUVMultiplier`, `useDetail`, `detailNormalBlend`, `extExtraSharpLocalReflections`, `extColoredReflection`, `isAdditive`, `ksAlphaRef`, `emSkipDiffuseMap`, `emChannelsMode`. Two skins also use `extSaturation`, `extMaskPass` and `extMaskPassColor`. — [Local scan output](file:///D:/ClaudeData/tmp/interior_csp/scan_out.txt)
- In every local file, `ksDiffuse` and `ksAmbient` are set as one number. The only 13 cases with several values are decimal-comma typos such as `PROP_...= ksDiffuse,0,45`, meant as 0.45. `ksEmissive`, by contrast, is documented with three values (`ksEmissive, 1, 0, 0`). — [Local scan](file:///D:/ClaudeData/tmp/interior_csp/scan_out.txt); [CSP docs: Shader replacements](https://cup.acstuff.club/docs/csp/general/shader-replacements)
- CSP's windscreen-banner template scales brightness by setting `ksAmbient` and `ksDiffuse` to `Brightness * 0.4` each, which treats them as scalar brightness. — [Local: materials_interior.ini, Material_WindscreenBanner](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)
- CSP PBR textures accept inline solid colours, for example `TextureEmAoMeRo = 'color::0,0,0,0', ribbed-chipped-metal_ao.png, ...`. "Instead of packing channels ... you can instead simply provide up to four textures and/or solid colors as placeholders." This applies to the `materials_pbr.ini` templates. — [Local: extension\config\cars\common\materials_pbr.ini, lines 40-60](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_pbr.ini)

### Inferences
- Minimal per-skin recipe for a flat seat colour in `skins\<skin>\ext_config.ini` (built from the documented keys, not tested in game):
  ```ini
  [SHADER_REPLACEMENT_...]
  MATERIALS = INT_Seat_Leather        ; real material name from CM Showroom / kn5 reader
  RESOURCE_0 = txDetail               ; Kunos-style multimap: colour lives in txDetail
  RESOURCE_COLOR_0 = 0.55, 0.05, 0.05 ; 1x1 solid colour
  ```
  For a material where the colour sits in `txDiffuse`, use `RESOURCE_0 = txDiffuse` with `RESOURCE_FILE_0 = r4s_int_seat.dds`, a recoloured copy of the original texture. A `RESOURCE_COLOR` on `txDiffuse` throws away all AO, stitching and logos, which is acceptable for small plain parts only.
- To make a part darker or lighter without changing its hue, use `PROP_... = ksDiffuse, x` and `PROP_... = ksAmbient, x` (scalars). For hue, change a texture slot.
- `PROP_... = extSaturation, x` (seen in two skins) may desaturate a texture before a colour is multiplied in, but CSP documents nothing about it (see Gaps).

### Gaps
- Not documented: the value range of `RESOURCE_COLOR` (0 to 1 floats or 0 to 255; every local example uses only 0 or 1), whether a 4th alpha component is accepted, and what alpha the 1×1 texture has. These matter because `txDiffuse` alpha masks `txDetail`. Test in game.
- Not found: an official CSP option named "tint", "MULTIPLY" (other than `BLEND_MODE`), or "extColor" for opaque materials, or any documentation for `extSaturation`. I found no evidence of a documented `ksDiffuse` RGB multiplier.
- The exact `ksPerPixelMultiMap` formula for how `txDetail` and `txDiffuse` combine is not quoted in the docs I reached. CSP shader sources were not fetched.

---

## Q3. CSP interior templates (`common/materials_interior.ini`) and whether they work per skin

### Takeaway
CSP ships an interior material library: `Material_Leather(_v2)`, `Material_Fabric(_v2)`, `Material_Carpet(_v2)`, `Material_Velvet`, `Material_Plastic(_v2)`, `Material_DashboardLeather`, `Material_Carbon`, `Material_Metal`, `Material_Fur`, and the generic `Material_InteriorPBR`. They are pulled in with `[INCLUDE: common/materials_interior.ini]`, and 217 skin `ext_config.ini` files on Nik's PC already include it. `Material_InteriorPBR` exposes `ColorSource` (DIFFUSE, DIFFUSE_NORMALIZED, FORCE_WHITE, DESATURATE) and `DetailTexture`/`DiffuseTexture`, and these accept a solid colour. That gives a documented route to "AO from the original texture, colour from config".

### Cited Findings
- From the template: `ColorSource = DIFFUSE_NORMALIZED ; where to take diffuse color from, valid values: DIFFUSE, DIFFUSE_NORMALIZED, FORCE_WHITE, DESATURATE`, `OcclusionSource = LUMINANCE ; ... NONE, LUMINANCE, MAPS_ALPHA`, `Brightness`, `Smoothness`, `Metalness`, `Reflectance`, and `HasDetailNormals = 1 ; set to 0 for meshes with “ksPerPixelMultiMap” shader`. — [Local: materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)
- The template converts these settings into `nePBR_MultiMap*` shaders. It writes `RESOURCE_0 = txDetail` from `DetailTexture` and `RESOURCE_3 = txDiffuse` from `DiffuseTexture`, through `_InteriorPBR_GuessResourceType`, so a number or table becomes `RESOURCE_COLOR_n`. It sets `PROP_0_PBCOLORSOURCE` from `ColorSource` and `PROP_0_KSDIFFUSE` from `Brightness`. — [Local: materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)
- The `_v2` templates (Leather, Fabric, Carpet, Plastic, Aluminium) extend `Material_InteriorPBRDetail`, which uses CSP's own PBR detail-normal textures (`common/pbr_leather_bumpy.dds`, `common/pbr_fabric.dds`, `common/pbr_carpet.dds`, and so on). Its line `ColorSource = $" ${DiffuseAsAO:exists} and 'FORCE_WHITE' or discard() "` means `DiffuseAsAO = x` makes the diffuse act as AO only. — [Local: materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)
- Usage pattern, in the same form as the carpaint templates: a section `[Material_Leather_v2]` with `Materials = ...`. CSP's own car configs restrict template sections to particular skins with a `Skins = ` key, for example `[Material_CarPaint_Solid]` with `Skins = Nero, Biancospino, 0_rosso_alfa` in `ks_alfa_mito_qv.ini`. — [Local: extension\config\cars\loaded\ks_alfa_mito_qv.ini, lines 40-60](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/ks_alfa_mito_qv.ini)
- Skin-level `ext_config.ini` is a supported location. The Fake Shadows FX docs describe a `CUSTOM_SKIN_SHADOWS` option "to make CSP cache shadows for different skins separately" that can be set in a single skin's extension config. — [CSP wiki: Cars – Fake Shadows FX (search summary)](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-Fake-Shadows-FX)
- Third-party skins on Nik's PC that include the interior library: 217 files. One example is `ks_bmw_m4_gt3\skins\wss_team_livery_e2584bbf6b\ext_config.ini`, which has `[INCLUDE]` with `INCLUDE=common/materials_interior.ini`. Another is `crsh_porsche_gt3_2019_endurance\skins\2022_KCMG_Motorsports_2`, which uses `[SHADER_REPLACEMENT_99:Material_InteriorPBRDetail]` with `Materials=EXT_Rim`, `BrightnessAdjustment=0.3` and `Metalness=0.8`. — [Local: wss_team_livery ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_bmw_m4_gt3/skins/wss_team_livery_e2584bbf6b/ext_config.ini); [Local: KCMG skin ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/crsh_porsche_gt3_2019_endurance/skins/2022_KCMG_Motorsports_2/ext_config.ini)
- CSP's `materials_interior.ini` comment links to the INIpp format documentation. — [INIpp](https://github.com/ac-custom-shaders-patch/inipp)

### Inferences
- A per-skin seat colour that keeps the original shading could look like this (inferred from the template code, not tested):
  ```ini
  [INCLUDE: common/materials_interior.ini]
  [Material_Leather_v2]
  Materials = INT_Seat_Leather
  DiffuseAsAO = 1                   ; original txDiffuse used as AO only
  DetailTexture = 0.55, 0.05, 0.05  ; becomes RESOURCE_COLOR_0 on txDetail
  ```
  `Material_InteriorPBR` with `ColorSource = DESATURATE` plus a coloured `DetailTexture` is another option. Both swap the material to a CSP `nePBR` shader, so the material will also look different (PBR shading), not only change colour. They only work with CSP and only for viewers whose CSP is new enough.
- Inside a skin's own `ext_config.ini`, a `SKINS =` key is redundant and risky. If it names a different skin, the section never applies (see Q4, Greenthing).

### Gaps
- No CSP page states which CSP version first read `skins\<skin>\ext_config.ini`, or how a skin config merges with the car's `extension\ext_config.ini` (append, override, order). Practice shows they stack, because skins add sections on top of car configs. I have not verified this against a doc.
- Not tested: whether `DetailTexture = r, g, b` is accepted by the parser in the form the guess function implies (a table or number).

---

## Q4. Real interior examples found on Nik's PC (quoted)

### Takeaway
Most interior sections found in skin `ext_config.ini` files adjust shading (`ksDiffuse`, `ksAmbient`, specular) or banners and displays rather than colour. Texture swaps by `RESOURCE_FILE` exist (Nik's own Sunbeam skins, glass). Solid `RESOURCE_COLOR` swaps exist only in car-level configs (the GT4 pack). None of the skins scanned recolours seats or a dash by hue through `ext_config`, so the colour-by-config recipes above are new ground.

### Cited Findings
- Scan totals: 293 shader-replacement sections whose `MATERIALS` or `MESHES` mention interior keywords. 21 are in skin configs, 160 in car configs and 112 in CSP configs. — [Local scan output](file:///D:/ClaudeData/tmp/interior_csp/scan_out.txt)
- A skin makes a whole interior trim darker or lighter (BMW E60 M5, skin `300_Alpine_White_III`):
  ```ini
  [SHADER_REPLACEMENT_...]
  MATERIALS = INT_Trim_OCC
  PROP_0 = detailUVMultiplier, 200
  PROP_1 = ksDiffuse, 0.4
  PROP_5 = ksAmbient, 0.4
  PROP_7 = detailNormalBlend, 0.0
  ```
  — [Local: gmp_e60_m5_ericsson\skins\300_Alpine_White_III\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gmp_e60_m5_ericsson/skins/300_Alpine_White_III/ext_config.ini)
- Skin-level interior plastics and decals (Kunos Ferrari 296 GT3, skin `2024_WEC_54_Vista`): `MATERIALS = INT_PLASTIC_BLACK` with `PROP_... = ksAmbient, 0.4`, `ksDiffuse, 0.4`, `ksSpecular, 0.3`, `ksSpecularEXP, 80`. `MATERIALS = INT_DECALS` gets `ksAmbient 0.7` and `ksDiffuse 0.5`. — [Local: ks_ferrari_296_gt3\skins\2024_WEC_54_Vista\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_ferrari_296_gt3/skins/2024_WEC_54_Vista/ext_config.ini)
- Interior banner switched to the windscreen shader in skins (Ferrari 296 GT3, Porsche 992 GT3 R): `MATERIALS = INT_BANNER`, `IS_TRANSPARENT = 1`, `BLEND_MODE = ALPHA_TEST`, `SHADER = ksWindscreen`. — [Local: porsche_992_gt3_r\skins\2023 DTM Team Bernhard 75\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/porsche_992_gt3_r/skins/2023%20DTM%20Team%20Bernhard%2075/ext_config.ini)
- Skin making the interior trim chrome-like (Fumi 200SX, skin `02_blanco`): `MATERIALS=centertrim`, `PROP_...=ksAmbient,-0.0`, `PROP_...=ksDiffuse,-0.0`, `ksSpecular,2`, `ksSpecularEXP,20000`. — [Local: fumi_cp_nissan_200sx_s13\skins\02_blanco\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/fumi_cp_nissan_200sx_s13/skins/02_blanco/ext_config.ini)
- Broken example, kept as a lesson (`snp_zhonghua_zidantou_wangan_spec`, skin `Greenthing`): `SKINS = Natsu_Pink`, `MESHES = INT_DASHPLASTIC , INT_LEATHER`, `PROP_0 = ksAmbient: 0.9`, `PROP_1 = ksDiffuse: 0.9`. It uses colon syntax instead of commas, and `SKINS` names another skin. — [Local: Greenthing\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/snp_zhonghua_zidantou_wangan_spec/skins/Greenthing/ext_config.ini)
- Probably-wrong template use (`bdb_nissan_silvia_s14`, skin `Silver_Moss`): `[TEMPLATE: Material_Carbon EXTENDS Material_InteriorPBR]` with `Materials = uras1, uras3, uras5` and `DetailTexture = common/carbon.png`. This redefines the template rather than instantiating it. — [Local: Silver_Moss\ext_config.ini, lines 36-49](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bdb_nissan_silvia_s14/skins/Silver_Moss/ext_config.ini)
- Car-level interior display blackout with a solid colour (GT4 pack): `MATERIALS = INT_Racelogic`, `PROP_...= emChannelsMode, 1`, `PROP_...= emSkipDiffuseMap, 1`, `RESOURCE_2 = txDiffuse`, `RESOURCE_COLOR_2 = 0,0,0`. — [Local: gt4_alpine_a110\extension\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gt4_alpine_a110/extension/ext_config.ini)
- Car-level interior specular tweak: `gmp_jzs161_ridox`, with `MATERIALS = INT_New2_Mats, INT_MOMO_STITCH` and `PROP_... = ksSpecular, 0.01`. — [Local: gmp_jzs161_ridox\extension\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gmp_jzs161_ridox/extension/ext_config.ini)
- Most "interior" keyword hits in skins are the LED position panel (`LED_PANEL_` on `lumirank_3`, with `INSERT_AFTER=COCKPIT_HR`). These are not colour changes. — [Local: porsche_992_gt3_r\skins\2023 Team Parker Racing #62\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/porsche_992_gt3_r/skins/2023%20Team%20Parker%20Racing%20%2362/ext_config.ini)

### Inferences
- The proven, working pattern on Nik's PC is `MESHES` or `MATERIALS` with `RESOURCE_n` and `RESOURCE_FILE_n` in a skin config. Ratty's4Skin already writes it and it has been confirmed in game for glass. Extending it to interior materials needs no new mechanism, only the right material and slot names.

### Gaps
- The scan only looked at `SHADER_REPLACEMENT` sections. Interior colour set through other CSP sections in skins was not searched exhaustively.

---

## Q5. CM Paint Shop (`ui\cm_paintshop.json`): interior entries, masks and replacements (route c)

### Takeaway
Paint Shop supports interior parts through three entry types:
- `"type": "color"` gives a solid fill, or a tint of the original texture with `autoLevel`, `desaturate` or `tintBase`.
- `"color"` with `pairs` adds a `source` and a `mask` per texture.
- `"type": "replacement"` with `candidates` swaps between ready-made textures.

A mask's R, G, B and A channels select colours 1, 2, 3 and 4. Each channel blends from "no tint" (0) to "full tint" (1) by multiplying the colour in. Paint Shop produces textures named after the target `texture`, so its output is route (a), same-name skin textures.

### Cited Findings
- The rules file is `cm_paintshop.json` in the car's `ui` folder. Fallbacks are the "Paint Shop" folders under `AppData\Local\AcTools Content Manager\Data` and `Data (User)`. The file is JSON with comments, either an object keyed by car ID whose values are arrays of entries, or a bare array. — [acstuff Paint Shop thread (search summary; page needs JS)](https://acstuff.club/f/d/16/5)
- Entry types accepted by CM's parser (case-insensitive):
  - `color` → `ColoredItem`. This is the default when `type` is missing.
  - `carpaint` → `CarPaint`, or `ComplexCarPaint` when `mapsTexture` is set.
  - `pattern`, `tintedwindow`, `licenseplate`, `solidcolorifflagged`, `transparentifflagged`, `replacedifflagged`.
  - `replacement` → `Replacement`, with `MultiReplacement` as the fallback.
  
  — [CM source: AcManager/PaintShop/PaintShop.cs](https://raw.githubusercontent.com/gro-ove/actools/master/AcManager/PaintShop/PaintShop.cs)
- Keys read for `color` entries: `pairs`, which is either an array or an object keyed by texture name. Each pair has `source`, `mask` and `overlay`. `texture` is used only when there are no `pairs`. The remaining keys are `tintBase`, `defaultColor`, `defaultColors`, `colors`, `allowedColors`, `liveryColor`, `liveryColors`, `autoLevel`, `desaturate`, `desaturateMax` and `adjust`/`adjustment`. Source strings accept a channel suffix such as `@self:R`. When there are no `pairs`, the code builds the entry as `TintedEntry(e.GetBoolValueOnly(KeyTintBase) == true || sourceParams.RequiresPreparation ? ...`. Keys for `replacement`: `texture`/`textures` plus `candidates` (name → source), or nested candidates (name → texture → source) for `MultiReplacement`. Keys for `carpaint`: `texture`, `mapsTexture`, `mapsAutoLevel`, `colorAvailable`, `flakesAvailable`, `defaultColor`, `candidates` (with an optional `colored` flag), `patternTexture`, `patterns` and `liveryStyle`. — [CM source: PaintShop.cs](https://raw.githubusercontent.com/gro-ove/actools/master/AcManager/PaintShop/PaintShop.cs)
- Without a `pairs` mask, a plain `color` entry registers `new PaintShop.TintedEntry(PaintShopSource.White, null, null)`, a white source with no mask. The colour comes from `CarPaintColors`. — [CM source: ColoredItem.cs](https://raw.githubusercontent.com/gro-ove/actools/master/AcManager/PaintShop/ColoredItem.cs)
- Shader maths, quoted verbatim:
  - Tint: `float4 result = float4(base.rgb * gColor.rgb, alpha);`, with alpha `saturate(gAlphaAdjustments.x + base.a * gAlphaAdjustments.y)`.
  - Masked tint: `base * ((1 - mask.r) + gColor * mask.r) * ((1 - mask.g) + gColors[0] * mask.g) * ((1 - mask.b) + gColors[1] * mask.b) * ((1 - mask.a) + gColors[2] * mask.a)`.
  
  So R selects colour 1, G colour 2, B colour 3 and A colour 4. Both are multiplicative tints, and an overlay is alpha-composited on top. Desaturate and auto-level are separate passes. — [CM source: AcTools.Render/Shaders/Special/SpecialPaintShop.fx](https://raw.githubusercontent.com/gro-ove/actools/master/AcTools.Render/Shaders/Special/SpecialPaintShop.fx)
- Counts of entry types across the 55 `cm_paintshop.json` files on Nik's PC: `color` 164, `carpaint` 91, `pattern` 25, `licensePlate` 11, `replacement` 10, `tintedWindow` 9. — [Local scan of content\cars\*\ui\cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/)
- Interior example `bg_lotus_carlton`: tinted interior textures and a wood replacement.
  ```json
  { "type": "color", "name": "04. Leather 1", "texture": "leather_1.dds", "autoLevel": true, "defaultColor": "#FFFFFF" },
  { "type": "color", "name": "12. Seatbelt", "texture": "seatbelt.dds", "autoLevel": true, "defaultColor": "#FFFFFF" },
  { "type": "color", "name": "13. Carpet 1", "texture": "carpet.dds", "autoLevel": true, "defaultColor": "#FFFFFF" },
  { "type": "replacement", "name": "18. Wood", "texture": "wood.dds", "candidates": { "Wood 01": "./cm_paintshop/wood_01.dds", ... } }
  ```
  It also has entries for Stitching 1-3, Carpet Trunk, Roof, Hood Fabric and Trunk Fabric. — [Local: bg_lotus_carlton\ui\cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bg_lotus_carlton/ui/cm_paintshop.json)
- Roll-cage examples:
  - `gt4_bmw_m4`: `{ "type": "color", "name": "03. Rollcage", "texture": "metal_detail_int.dds", "autoLevel": true, "defaultColor": "#FFFFFF" }`. — [Local: gt4_bmw_m4\ui\cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gt4_bmw_m4/ui/cm_paintshop.json)
  - `adc_bmw_e46` uses carPaint for the cage: `"type": "carPaint", "name": "#2 Rollcage", "texture": "metal_detail_2.dds", "mapsTexture": "rollcage1ia.dds"`, plus `"#6 Cloth"` on `metal_detail_4.dds`. — [Local: adc_bmw_e46\ui\cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/adc_bmw_e46/ui/cm_paintshop.json)
  - `actk_citroen_ax_proto` also uses carpaint: `"type": "carpaint", "name": "rollcage", "texture": "rollcage_metal_detail.dds"`, and `"body internal"` on `tole_metal_detail.dds`. — [Local: actk_citroen_ax_proto\ui\cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/actk_citroen_ax_proto/ui/cm_paintshop.json)
- Masked two-colour example (RSS GT Ferruccio 55 rims): `"rim.dds": { "source": { "path": "rim.dds", "desaturate": true }, "mask": "./rim_mask.png" }` with `"defaultColors": [ "#ffff00", "#232323" ]`. In the shipped `rim_mask.png` (512×512, inside `ui\cm_paintshop.zip`), 251,331 pixels are pure G (colour 2) and 10,813 are R+B (colour 1, plus the unused colour 3). Single-colour masks such as `caliper_mask.png` and `Decals_mask.png` are white (all channels) where tinted and black elsewhere. Files given as `./...` are read from `ui\cm_paintshop.zip` or the matching folder. — [Local: rss_gt_ferruccio_55\ui\cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/rss_gt_ferruccio_55/ui/cm_paintshop.json); [Local: rss_gt_ferruccio_55\ui\cm_paintshop.zip (read in memory)](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/rss_gt_ferruccio_55/ui/cm_paintshop.zip)
- The "solid" vs "tint" roles in CM's name guessing match the two code paths. `PlasticDetail_color.dds` and `cloth_detail.dds` are solid. `carpet.dds`, `cloth_seats.dds`, `leather.dds` and `alcnt.dds` are tint. — [CSP docs: Default names for Paint Shop](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom)

### Inferences
- `autoLevel: true` (used on every `bg_lotus_carlton` interior entry) almost certainly sets `RequiresPreparation`. The original texture is then auto-levelled and tinted, keeping its grain and stitching. A plain `color` entry without it is a solid fill on a white source. The flag name suggests this, but I did not read the `GetSourceParams` code.
- Paint Shop masks mark texels with mask channel values in the target texture's own UV space, one mask per texture in `pairs`. The mask has to match the texture's resolution and layout, and the base is multiplied, so a dark base cannot be lifted to a light colour unless `desaturate`/`autoLevel` prepares it. Ratty's4Skin could reuse this exact maths (`base × lerp(1, colour, mask)` per channel) for interiors.
- Paint Shop's output is a same-name texture in the skin, so it inherits every limit of route (a): shared textures change everywhere they are used, and no CSP is needed to see the result.

### Gaps
- Not confirmed from source: how Paint Shop saves (into the selected skin folder or a new one, with or without a skin JSON). I did not reach the save code (`LiteShowroomTools.PaintShop.cs`, `ToolsKn5ObjectRenderer.PaintShop.cs`).
- Not confirmed: what happens to an unused mask channel when fewer colours are defined (whether it defaults to white, meaning no change). The RSS rim mask has A=255 everywhere and works with two colours, which suggests that unset slots are white.
- The acstuff Paint Shop thread (acstuff.club/f/d/16) needs JavaScript and its API returned 404, so the original author documentation was only seen through a search snippet.

---

## Q6. Pitfalls: shared textures, detail textures, alpha, LODs, online visibility

### Takeaway
The big risks are these:
- A same-name override or a `MATERIALS` replacement hits every user of a shared texture or material, often exterior trim too.
- Kunos-style colour lives in a tiling `txDetail` that is masked by the `txDiffuse` alpha.
- `RESOURCE_COLOR` on `txDiffuse` wipes AO and logos.
- Wrong PROP syntax fails silently.
- Other drivers see a skin's interior only if they have the same skin files, and CSP for `ext_config` changes.

### Cited Findings
- Shared material vs mesh targeting: `MATERIALS` changes every mesh that uses that material. `MESHES` limits the change but "each mesh in MESHES would get its own material", which adds GPU calls. — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- A forum report says a car-wide material change affected unrelated parts. — [GTPlanet AC mods thread (forum)](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14632801)
- Shared interior and exterior textures in practice: `adc_bmw_e46` paints the roll cage with a carPaint entry on `metal_detail_2.dds`, and `actk_citroen_ax_proto` paints `body internal` with `tole_metal_detail.dds`. Car paint "detail" textures are routinely reused for interior metal, so recolouring a `metal_detail*.dds` by name can repaint cage, inner body and outer panels together. — [Local: adc_bmw_e46 cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/adc_bmw_e46/ui/cm_paintshop.json); [Local: actk_citroen_ax_proto cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/actk_citroen_ax_proto/ui/cm_paintshop.json)
- Detail texture and alpha: the `txDiffuse` alpha masks `txDetail` on multimap materials. Kunos-style interiors carry AO in `txDiffuse` and colour in `txDetail`. — [CSP docs: Default names for Paint Shop](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom); [Local: materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)
- `txDetail` tiles through the `detailUVMultiplier` prop, which skins often change (for example `PROP_... = detailUVMultiplier, 700`). A colour texture made for `txDetail` must be tile-safe. — [Local: ng_lexus_rcf_gt3\skins\VRomans\ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ng_lexus_rcf_gt3/skins/VRomans/ext_config.ini)
- Silent syntax failures: decimal-comma `ksDiffuse,0,45` (13 cases on Nik's PC) and colon syntax `ksAmbient: 0.9`. Neither is valid `PROP` syntax, which is `PROP_n = name, value`. — [Local scan](file:///D:/ClaudeData/tmp/interior_csp/scan_out.txt); [CSP docs: Shader replacements](https://cup.acstuff.club/docs/csp/general/shader-replacements)
- Static application: changes appear on load or config reload, and removing a section does not undo it live. — [CSP wiki: Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)
- Online: there is no Kunos or CM document on this. Community reports say others do not see a downloaded skin unless they have the same skin installed. SkinSync P2P is a third-party tool that transfers skins between players, needs CM and CSP 2.11 or later, and is limited to 10 MB zips (self-reported by its developer). — [GTPlanet: SkinSync plugin page](https://www.gtplanet.net/forum/downloads/skinsyncplugin-%C2%AE-for-assetto-corsa.7801/reviews); [BisectHosting: uploading custom skins to an AC server](https://help.bisecthosting.com/hc/en-us/articles/40518920826907-How-to-Upload-Custom-Car-Skins-to-an-Assetto-Corsa-Server)
- CSP keeps a per-skin shadow cache option (`CUSTOM_SKIN_SHADOWS`) for skins with custom geometry. This only matters if a skin's `ext_config` hides or adds meshes, not for colour. — [CSP wiki: Fake Shadows FX](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-Fake-Shadows-FX)

### Inferences
- The safest interior recolour for a Ratty's4Skin feature works like this:
  1. Find the material that owns the part and the slot that holds its colour (`txDiffuse`, or `txDetail` for Kunos style).
  2. If the texture is used only by interior materials, write a same-name recoloured texture. This needs no CSP and is visible to anyone who has the skin.
  3. If the texture is shared with exterior parts, write a renamed file (`r4s_*.dds`) and point only the interior material at it with `MATERIALS = ...`, `RESOURCE_n = slot` and `RESOURCE_FILE_n = r4s_....dds`. This needs CSP. Use `MESHES` only when the material itself is shared with exterior meshes.
- Preserve the `txDiffuse` alpha when recolouring a diffuse, because it masks `txDetail`. A recolour that rewrites alpha will change where the detail colour shows.
- LOD kn5s usually reuse the same textures and material names, so both a same-name override and a `MATERIALS` replacement should also reach the LODs. A `MESHES` replacement may not, because LOD mesh names often differ. Check per car.
- Encrypted or CSP-protected cars (seen by Ratty's4Skin as 'protected') may block material inspection, but a same-name skin texture still works if the texture names are known.

### Gaps
- Not verified: how a skin `ext_config.ini` interacts with a car's `extension\ext_config.ini` when both target the same material (which one wins).
- Not verified: whether online servers with CSP "extra options" can block skin `ext_config` features. No source found.
- CSP shader source for `ksPerPixelMultiMap` and `nePBR_MultiMap` was not read, so the exact detail and diffuse blend maths are not quoted. An in-game test on one of Nik's cars is the way to settle it.
