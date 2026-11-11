# How AC livery makers and modders put stickers on windows, including shared or mirrored glass

Scope: real-world practice for window stickers in Assetto Corsa: windscreen banners, rear-window and side-window numbers and names. It covers vanilla AC and Custom Shaders Patch (CSP) 0.2.x era, so a skin generator can pick a method per car.

Method: web search and fetch, plus a read-only survey of Nik's 868 installed cars. The survey covered per-skin `ext_config.ini`, skin texture names, `cm_paintshop.json`, Kunos SDK skin templates, and ASCII mesh, material and texture names pulled from kn5 files (no geometry or UV parsing). Local evidence is cited as `local:` paths, not URLs. OverTake.gg and GTPlanet return HTTP 403 to the fetch tool, so findings from those sites come from search-result snippets only and are marked "(snippet)".

---

## 1. How Kunos and the big mod teams build window stickers (separate overlay meshes? naming?)

### Takeaway
Kunos and the large teams (RSS, ACF, Kunos GT3/GT4/Cup cars) almost always build window stickers as a **separate overlay mesh with its own material and texture**. Skins then just override that one texture file. Exterior and interior often have separate banner meshes. Common names are `GEO_BANNER` / `EXT_BANNER` / `INT_BANNER` with `EXT_Banner.dds`, `EXT_Glass_Banner` with `GLASS_Banner.dds`, `*_sponsor` glass meshes, `*number_glass*`, and per-door `*_DOOR_L` / `*_DOOR_R` decal meshes. The window glass itself usually stays a plain tinted or dirt texture.

### Cited Findings
- **Kunos Porsche 911 GT3 R 2016:** meshes `GEO_BANNER` (with `GEO_BANNER_SUB0/1`), material `EXT_BANNER`, texture `EXT_Banner.dds`, plus `INT_BANNER` and `GEO_INT_Window_L` / `GEO_INT_Window_R`. Every one of its skins carries an `EXT_Banner.dds` (sample skin `00_gt3`: ac_crew, EXT_Banner, Skin_00, Skin_00_MAP, metal_detail). — local: `content\cars\ks_porsche_911_gt3_r_2016\porsche_911_gt3_r.kn5` and its `skins\00_gt3\`
- **Kunos Nissan GT-R GT3:** materials `EXT_Glass_Banner` and `INT_Glass_Banner`, texture `GLASS_Banner.dds`; separate meshes `GEO_windscreen`, `GEO_window_SIDE_L`, `GEO_window_SIDE_R`; plus `INT_text_sponsor` with `INT_text_Sponsor.dds`. — local: `content\cars\ks_nissan_gtr_gt3\nissan_gtr_gt3.kn5`
- **Kunos Ferrari 296 GT3:** `EXT_Banner` with `EXT_Banner_Colour.dds`, `INT_BANNER`, plus separate per-side meshes `EXT_DECALS_DOOR_L` / `EXT_DECALS_DOOR_R`, `EXT_GLASS_DOOR_L` / `EXT_GLASS_DOOR_R` and `INT_DECALS_DOOR_L/R`. — local: `content\cars\ks_ferrari_296_gt3\ferrari_296_gt3.kn5`
- **Kunos Toyota Celica ST185:** `GEO_EXT_BANNER` / `EXT_BANNER` / `EXT_Banner.dds`, `GEO_INT_BANNER`, and separate `GEO_Doorsticker_L` / `GEO_Doorsticker_R` meshes. — local: `content\cars\ks_toyota_celica_st185\toyota_celica.kn5`
- **Other Kunos examples:**
  - Porsche Cayman GT4 Clubsport: `EXT_GLASS_BANNER` with `EXT_banner.dds`, and separate `EXT_GLASS_LEFT` / `EXT_GLASS_RIGHT`.
  - Lamborghini Huracán GT3: `GEO_Sponsor` with `INT_sponsor.dds`.
  - Porsche 911 Carrera RSR: `GEO_int_glass_sponsor` with `INT_Glass_sponsor.dds`.
  - Mazda 787B: `INT_Window_Banner` with `glasslabel_inside.dds`.
  - McLaren 650 GT3 is the exception: no banner mesh. Its banner is painted into `Glass_Windows_D.dds`.
  - Source: local, the main kn5 of each car under `content\cars\`.
- **RSS:**
  - GTM Mercer V8: `GEO_BANNER_EXT` / `GEO_BANNER_INT`, `EXT_Banner` / `INT_Banner`, `EXT_Banner.dds`, `WINDSCREEN_SPOTTER_1/2`, and per-side `GEO_DOOR_WINDOW_L_LODA` / `GEO_DOOR_WINDOW_R_LODA`.
  - GTM Bayer V8: `GEO_Banners`, `INT_Banners`, `Banner.dds`.
  - Source: local, `content\cars\rss_gtm_mercer_v8\rss_gtm_mercer.kn5` and `rss_gtm_bayer_v8.kn5`.
- **ACF Aston Martin Vantage GT3:** material `MI_Vehicle_Windows_Stickers` with `MI_Vehicle_Windows_Stickers_baseColor.dds` (Unreal-export style naming). — local: `content\cars\acf_aston_martin_vantage_gt3\aston_vantage_gt3_evo.kn5`
- **Skin texture overrides across the 868 installed cars:** 6,223 skin-folder textures in 503 cars have banner, sticker, decal, window or glass names. This count also includes light and helmet glass. The most common names:

  | Texture name | Files | Cars |
  |---|---|---|
  | `ext_banner_colour.dds` | 660 | 66 (GT3 cars by ACF, BM, TRR, CF, BK, FSR) |
  | `banner.dds` | 435 | 55 |
  | `ext_glass.dds` | 298 | 37 |
  | `ext_decals_colour.dds` | 189 | 36 |
  | `ext_banner.dds` | 91 | 12 (Kunos + RSS) |
  | `zb_windows.dds` | 109 skins | 1 (supercars_holden_zb) |
  | `ext_sponsor_glass.dds` | — | 24 skins (ks_audi_tt_vln) |
  | `ext_number_glass.dds` | — | 20 skins (ks_audi_tt_cup) |
  | `int_glass_numbers.dds` | — | 6 cars (WTCR / TCR) |
  | `window_decal.dds` + `driver_banner.dds` | — | 6 Supercars Gen3 cars |
  | `glass_decals.dds` | — | 32 skins (Sierra RS500 DTM) |
  | `windowbanner.dds` | — | 16 skins (tg_beetle_cup) |

  Source: local, scan of `content\cars\*\skins\**`.
- **Kunos SDK skin templates:** 148 template folders, 32 of which include glass or banner templates. Examples:
  - `ks_mazda_mx5_cup\Glass_BANNER.psd`
  - `ks_toyota_ae86_drift\windshield_banner.psd`
  - `rtr_audi_tt_cup\EXT_number_glass.psd`
  - `rtr_audi_tt_vln\EXT_Sponsor_GLASS.psd`
  - `pp_porsche_911_gt3_cup_2017\EXT_Sideglass.psd`
  - `rtr_mclaren_p1_gtr\EXT_Windows_Black_BANNER.psd`
  - `ks_ferrari_488_gt3_2020\EXT_Glass_sponsor.psd`

  Source: local, `sdk\dev\skin_templates\`.
- **Community banner pack:** it names the per-car windscreen files for Kunos GT cars, for example "Nissan GT3 - GLASS_Banner", "McLaren GT3 - Glass_Windows_D". It notes that internal views need a separate internal file. — [OverTake windscreen banner pack](https://www.overtake.gg/downloads/assetto-corsa-windscreen-banner-pack.7472/) (snippet)
- **Installing a window sticker is a file swap in the skin folder.** For example, a BetCity MX-5 Cup sticker replaces `EXT_Glass_BANNER` in the skin folder. — [OverTake BetCity MX5 Cup window sticker](https://www.overtake.gg/downloads/betcity-mazda-mx5-cup-window-sticker-for-assetto-corsa.73095/) (snippet)
- **CSP template for banner meshes:** CSP ships `[TEMPLATE: Material_WindscreenBanner]`, described as "Windscreen banner, including masking pass and shadowing colorization". It uses `SHADER = ksWindscreen`, `IS_TRANSPARENT = 1` and a `bannerMode` property. Its options are `BlurBackground`, `RainDrops` ("set to 0 if mesh overlays interior windscreen"), `WindscreenMesh` (to fix render order when the banner overlays the interior windscreen), `CastShadowsThreshold`, `MaskPass` and `ColorfulShadowing`. — [acc-extension-config materials_interior.ini](https://github.com/ac-custom-shaders-patch/acc-extension-config/blob/master/config/cars/common/materials_interior.ini)
- **Skins fix banner rendering through CSP:**
  - Ferrari 296 GT3 skins: `[SHADER_REPLACEMENT_...] MATERIALS = INT_BANNER / IS_TRANSPARENT = 1 / BLEND_MODE = ALPHA_TEST / SHADER = ksWindscreen`.
  - BM Audi R8 skins: `MATERIALS = EXT_Banner / BLEND_MODE = ALPHA_TEST`.
  - Source: local, `content\cars\ks_ferrari_296_gt3\skins\2023_IMSA_21_AFCorse\ext_config.ini` and `content\cars\bm_audi_r8_lms_evo_2019\skins\ACF_VLN_#23_Gerards_Thoennissen\ext_config.ini`.

### Inferences
- The professional standard is a dedicated, alpha-tested overlay mesh per sticker zone (windscreen banner, often rear screen, sometimes each side window or door), each with its own UV space. A generator should first look for materials whose names contain `banner`, `sticker`, `sponsor`, `number`, `decal` together with `glass` or `window`, and paint into those textures.
- Exterior and interior banners are often separate textures (`EXT_Banner` vs `INT_BANNER` / `INT_Glass_Banner`). If the generator writes only the exterior one, the sticker can be missing or wrong from the cockpit view.
- Per-side `_L` / `_R` sticker meshes are how modders avoid the mirrored-UV problem at the source (Ferrari 296 door decals, Celica door stickers).

### Gaps
- No URD or VRC cars are installed (0 `urd_` / `vrc_` folders), and no web source described their conventions, so their naming is unverified.
- Mesh names were read as raw strings, without UV parsing. Whether a given car's `GEO_window_L` and `GEO_window_R` share a mirrored UV island cannot be told from names. The project's own kn5 reader (blender/ tools) could check this per car.

---

## 2. What skinners do when side windows share mirrored UVs

### Takeaway
There is no in-texture fix for a shared, mirrored UV area: whatever is painted shows on both sides, reversed on one. Skinners use one of these approaches:
1. Use only panes with unique UVs (windscreen and rear-screen banners).
2. Use designs that read fine mirrored, or skip side-window text.
3. Ask the modder for (or use) a separate sticker mesh.
4. With CSP, give one pane its own texture or hide or insert meshes per skin in the skin's `ext_config.ini`.

### Cited Findings
- **Why it mirrors:** symmetric parts often share one UV area to save space, which flips the texture on one side. A separate UV map for the part is the fix, at some resolution cost. This is iRacing-context, but the principle is engine-agnostic. — [r/iRacing thread (redlib mirror)](https://redlib.belloworld.it/r/iRacing/comments/1f9wuoz/well_this_is_disappointing) (snippet)
- **UVs are fixed for skinners:** model UVs "can't be changed" without editing the model. — [OverTake Mudbox/Photoshop skinning tutorial](https://overtake.gg/threads/skinning-assetto-corsa-cars-from-nothing-using-mudbox-and-photoshop.147080/page-6) (snippet)
- **The mirrored side is fixed by hand:** a tutorial paints one side with X mirroring, then corrects the reversed side in Photoshop by moving the logo and transforming it into place. That only works where the two sides have separate UV areas. — [simracingsystem "Skinning From Nothing"](https://www.simracingsystem.com/showthread.php?tid=2249) (snippet); [OverTake skinning thread](https://www.overtake.gg/threads/skinning-assetto-corsa-cars-from-nothing-using-mudbox-and-photoshop.147080/) (snippet)
- **Decals as 3D objects:** AC has no decal shader, so decals have to be 3D objects on the car; Blender shrinkwrap was suggested to fit them. — [GTPlanet AC mods thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-13878439) (snippet)
- **A mirror line inside one texture:** a known problem where an internal windscreen texture is mapped with a mirror line down the middle. The fix described was re-UV-mapping the internal glass, which is a modder-side fix. — [OverTake / GTPlanet results for windscreen banner search](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4532) (snippet)
- **Skins insert their own sticker meshes (CSP):** 12 skins of `bm_amg_evo_gt3_2020` ship a `Banner.kn5` plus `banner.dds` and use `[MODEL_REPLACEMENT_...] HIDE=EXT_Banner001, EXT_Banner002 / INSERT=Banner.kn5 / INSERT_AFTER=COCKPIT_HR`. The inserted kn5 holds mesh `Banner_alt` (from "kunos merc banner.fbx") with `ksPerPixelReflection` and `ksAlphaRef`. — local: `content\cars\bm_amg_evo_gt3_2020\skins\#4_HRT_DTM_2021\`
- **A third-party body-sticker kn5 in a skin:** a JZA80 skin ships `junya_decal.kn5` (mesh `GEO_EXT_Body_Junya_Decal`, shader `ksPerPixelAT_NM`, texture `junya_side_logo.dds`) and inserts it with `INSERT=junya_decal.kn5 / INSERT_AFTER=COCKPIT_HR`. — local: `content\cars\naz_jza80_ridox_modern\skins\07_csj_demo\`
- **Inserted kn5 files live next to the config:** CSP model replacement documents `INSERT` as "name of KN5 to insert, should be located next to config file", so a per-skin kn5 sits in the skin folder. — [CSP wiki: General – Model replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Model-replacements)
- **Skins hide sticker meshes they do not want:**
  - Renault 5 Turbo skin: `[MESH_ADJUSTMENT_...] MESHES = turbo_window_logo / IS_RENDERABLE = 0`.
  - RX-7 FD skins: `HIDE=ext_stickers, ext_stickers_R`.
  - Source: local, `content\cars\renault_5_turbo_r\skins\blanc_turbo\ext_config.ini` and `content\cars\rize_efini_rx7_fd3s_keisuke_1\skins\01_itsdraik_M8_Montego_Blue_Metallic\ext_config.ini`.
- **Per-mesh texture swap from a skin (CSP):** a Vantage GT3 skin gives one mesh its own texture with `[SHADER_REPLACEMENT_...] MESHES=EXT_Glass_Emissive_Front001 / RESOURCE_0=txDiffuse / RESOURCE_0_FILE=yellowglass.dds`. 55 per-skin configs on the PC use `RESOURCE_*` texture keys. — local: `content\cars\trr_amr_vantage_gt3\skins\N24H_69_Doerr Motorsport\ext_config.ini`
- **The documented syntax for that swap:**
  - `RESOURCE_0 = txDiffuse` with `RESOURCE_FILE_<n> = custom.dds`, "a texture on a disk, next to the config".
  - `SKINS = ...` filter (cars only).
  - Targeting by `MESHES` gives each mesh its own material, at the cost of extra GPU draw calls.
  - The wiki does not show the `RESOURCE_0_FILE` spelling used in the Vantage skin.
  - Source: [CSP wiki: General – Shader replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)

### Inferences
- **The CSP skin-only fix for mirrored or shared side glass** is a per-skin `[SHADER_REPLACEMENT_...]` with `MESHES = <one side's window mesh>`, `RESOURCE_0 = txDiffuse` and `RESOURCE_FILE_0 = <that side's own texture>`.
  - The texture holds that side's art pre-flipped horizontally where the UV is mirrored.
  - Because targeting by `MESHES` splits the material, it no longer shares the texture with the other pane.
  - It only works if the two panes are separate meshes, or can be split with CSP mesh splitting (untested).
  - Without CSP, both sides fall back to the shared texture. The generator should therefore put a "mirror-safe" version, or nothing, in the shared texture.
- **Inserting a dedicated sticker kn5 per skin** (the AMG `Banner.kn5` pattern) gives the best quality, with its own UVs and alpha. It means authoring geometry for each car, so it suits a few flagship cars rather than a generic generator.
- **Hiding a glass pane with `HIDE` is not a sticker fix**: it removes the window. `HIDE` and `IS_RENDERABLE = 0` only make sense on dedicated sticker meshes. Example: hide the car's built-in `*_stickers_R` mesh and keep `_L`, or hide the built-in banner and insert your own.
- **Without CSP, the honest fallback for shared or mirrored side glass** is no text on the side glass: use symmetric graphics (stripes, solid sunstrip blocks, non-text logos), or put the number or name on the body door instead.

### Gaps
- None of the forum pages where skinners discuss mirrored side-window UVs in AC could be fully read (OverTake and GTPlanet return 403), so this rests on snippets plus local practice. I found no AC-specific guide that addresses mirrored side-window stickers directly.
- Not verified: whether CSP accepts `RESOURCE_0_FILE` as an alias for the documented `RESOURCE_FILE_0`. The installed skin uses the former, but its effect was not checked in-game.
- Not verified: whether `[SHADER_REPLACEMENT_...]` with `MESHES` works when two panes are one mesh with mirrored UVs. It almost certainly cannot separate them, because there is only one material and one mesh. CSP "Meshes splitting" exists as a wiki topic but was not researched.

---

## 3. Tools and templates that handle window decals

### Takeaway
No mainstream tool places mirrored-aware window stickers.
- **Kunos SDK PSD templates** provide banner and glass templates for about 20 cars.
- **Content Manager Paint Shop** handles window tint (`tintedWindow`) and simple colour or mask fills of banner textures, defined per car in `ui/cm_paintshop.json`. It does not place text or numbers on glass.
- **The CSP Lua "paintshop" app** paints on the car in-game (CSP only).

### Cited Findings
- **CM Paint Shop rules** live in `cm_paintshop.json` in the car's `ui` folder, with fallbacks in CM's AppData Data folders. It has a `tintedWindow` type (an extended Color with an optional fixed colour). `ext_glass.dds` is the exterior window colour by convention. — [search summary of CM Paint Shop docs / acstuff](https://acstuff.ru/f/d/16/5) (snippet; the acstuff.club page itself is a JS app and did not render)
- **CSP Custom Showroom Paint Shop default names:** `ext_glass.dds` = "glass with optional transparency"; license plate `Plate_D.dds` / `Plate_NM.dds`. No default banner or decal names. — [CSP wiki: Default names for Paint Shop in Custom Showroom](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Unrelated-%E2%80%93-Default-names-for-Paint-Shop-in-Custom-Showroom)
- **Paint Shop on Nik's PC:** 57 installed cars ship `ui\cm_paintshop.json`. Entry types used: `color` 170, `carPaint` 91, `pattern` 28, `licensePlate` 11, `replacement` 10, `tintedWindow` 9 (textures such as `glass.dds`, `glass70.dds`, `Adjustable_Glass.dds`). — local: `content\cars\*\ui\cm_paintshop.json`
- **The only window-banner Paint Shop entry found** is on RSS GT Ferruccio 55: `{"type": "color", "name": "Windscreen Banner", "pairs": {"Decals.dds": {"source": "./Decals.dds", "mask": "./Decals_mask.png"}}}`. It recolours a masked area and does not place text. RSS Bayer Hybrid has `{"type":"color","name":"Banner","texture":"banner_paints_1.dds"}`. — local: `content\cars\rss_gt_ferruccio_55\ui\cm_paintshop.json`, `content\cars\rss_mph_bayer_hybrid_v8\ui\cm_paintshop.json`
- **CSP paintshop app:** a Lua app for drawing on cars in AC; it needs CSP 0.1.77+. — [GitHub ac-custom-shaders-patch/app-paintshop](https://github.com/ac-custom-shaders-patch/app-paintshop) (snippet)
- **Kunos SDK templates:** `sdk\dev\skin_templates` has 148 car folders; 32 files are glass or banner templates (list in section 1). — local: `sdk\dev\skin_templates\`; the folder is also cited in [OverTake/GTPlanet search results](https://www.overtake.gg/threads/skinning-assetto-corsa-cars-from-nothing-using-mudbox-and-photoshop.147080/) (snippet)

### Inferences
- The generator can read `ui/cm_paintshop.json`, where present, as a hint to which textures are glass (`tintedWindow`) or banner (`name` containing "Banner"). Most cars do not have one (57 of 868).
- Where the Kunos SDK has a banner PSD for a car, the generator can use it as a UV-layout reference for that car's banner texture.

### Gaps
- I could not read the full CM Paint Shop documentation (the acstuff.club page renders client-side), so any CM support for text or number placement on glass is unconfirmed. None was seen in the 57 local files.

---

## 4. Skin-only tricks that hide a sticker on one side (ui_skin.json, materials, alpha, per-skin CSP)

### Takeaway
`ui_skin.json` cannot do this; it holds only metadata. The real skin-only levers all need CSP: a per-skin `ext_config.ini` with `[MODEL_REPLACEMENT_...] HIDE=`, `[MESH_ADJUSTMENT_...] IS_RENDERABLE = 0`, or `[SHADER_REPLACEMENT_...]` per mesh (texture swap, blend mode). Without CSP, a skin can only change textures, and alpha in a shared texture hides the sticker on both sides at once.

### Cited Findings
- **Per-skin ext_config is widespread:** 2,167 skin-level `ext_config.ini` files exist across the installed cars. Section counts include `MODEL_REPLACEMENT_` 2,127, `SHADER_REPLACEMENT_` 553 and `MESH_ADJUSTMENT_` 82, and the key `HIDE` appears 1,867 times. — local: `content\cars\*\skins\*\ext_config.ini`
- **`[MESH_ADJUSTMENT_...]` keys:** `MESHES`, `MATERIALS` (warning: "all objects using same mat would be affected"), `IS_ACTIVE`, `IS_TRANSPARENT`, `IS_RENDERABLE`, `CAST_SHADOWS`, `LAYER`, `MOVE_TO`, `MOVE_IN_FRONT`. — [CUP docs: mesh adjustment](https://cup.acstuff.club/docs/csp/mesh-adjustment)
- **`[MODEL_REPLACEMENT_...]` keys:** `HIDE` "meshes or nodes to hide (no protected meshes)", `SKINS` "list of skins to use replacement with (only for cars)", and `INSERT` / `INSERT_AFTER` / `INSERT_IN`. — [CSP wiki: Model replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Model-replacements)
- **The same per-skin logic can live in the car-level config:** 451 cars have a car-level `extension\ext_config.ini`, and 75 model, mesh or shader sections in them are gated with `SKINS =`. Example: `bdb_mazda_miata_na1` hides `TurboGlass, TurboDecals` for listed skins. — local: `content\cars\bdb_mazda_miata_na1\extension\ext_config.ini`
- **Third-party lookup order:** a RaceDepartment user lists where CSP looks for a car's config, including `CARID__SKINID.ini` in `Documents\Assetto Corsa\cfg\extension\cars` and `ext_config.ini` in the car's skin folder, ranked above the car-level config. — [RaceDepartment RSS formula tyre config post](https://www.racedepartment.com/threads/rss-formula-tyre-config-for-shaders-patch-dynamic-lights.157841/) (snippet; third-party, not official)
- **Forum reports of per-skin configs:** HIDE in a skin's `ext_config.ini` "worked"; a similar edit in a shared config "would hide it in all skins"; one user's `SHADER_REPLACEMENT_0` in a skin folder had no effect, with no answer given. — [GTPlanet AC mods thread](https://gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4160) (snippet)
- **Shadow cache for custom skin geometry:** `CUSTOM_SKIN_SHADOWS = 0 ; change to 1 to make CSP cache shadows for different skins separately (could be used in single skin's extension config), for skins with custom geometry`. This is relevant when a skin inserts a sticker kn5. — [CSP wiki: Fake Shadows FX](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-Fake-Shadows-FX)
- **Alpha-test banner textures:** the inserted banner meshes use `ksAlphaRef`, and per-skin configs set `BLEND_MODE = ALPHA_TEST` on banner materials. So a fully transparent pixel in the sticker texture hides the sticker where that texel is used. — local: `bm_amg_evo_gt3_2020\skins\#4_HRT_DTM_2021\Banner.kn5`; `bm_audi_r8_lms_evo_2019\skins\...\ext_config.ini`

### Inferences
- **Hide one side's sticker:** if the car has separate L/R sticker meshes, use `HIDE=<mesh>` or `[MESH_ADJUSTMENT_...] MESHES=<mesh> / IS_RENDERABLE=0` in the skin's `ext_config.ini`.
- **Shared or mirrored texture on two pane meshes:** use `[SHADER_REPLACEMENT_...] MESHES=<pane> / RESOURCE_0=txDiffuse / RESOURCE_FILE_0=<own.dds>`. This gives one pane its own (possibly empty or flipped) texture, so the sticker shows only on the other side or reads correctly on both.
- **Pure texture alpha cannot separate sides** that sample the same texels.
- **`IS_RENDERABLE=0` with `MATERIALS=`** hides every mesh using that material, so target by `MESHES` when hiding stickers.
- **Write per-skin settings into the skin's own `ext_config.ini`**, not the car's `extension\ext_config.ini`. A car-level edit affects all skins unless it is gated with `SKINS=`, and it modifies the car mod itself.

### Gaps
- No official CSP page found here states the per-skin `ext_config.ini` load and merge rules. Support is strongly evidenced by 2,167 working-in-the-wild files, but merge semantics are undocumented in what I read: whether a skin config replaces or merges with the car config, and how `[..._...]` auto-indices combine.
- The report that `SHADER_REPLACEMENT` in a skin folder failed is unexplained. It may have been a material-name mismatch, or CSP version behaviour; worth an in-game test on one car before relying on per-mesh texture swaps.

---

## 5. Online: what other drivers see with a per-skin ext_config.ini

### Takeaway
AC does not send skin files over the network. Each client renders a car from its own local copy of the skin folder, and only CSP reads `ext_config.ini`. Another driver sees the CSP window-sticker fix only if they have the identical skin folder installed (`ext_config.ini` plus any extra `.dds` / `.kn5` it references) **and** run CSP. Without the skin they see some other skin. With the skin but no CSP, they see the plain textures: the shared-glass fallback, and any built-in sticker meshes the config would have hidden.

### Cited Findings
- **No built-in skin sharing:** "AC has no support for automatically sharing skins through the game"; servers can host skins and share them through Content Manager's "Install missing content", but only with direct download links. — [OverTake: download missing car/track/server content](https://www.overtake.gg/threads/download-missing-car-track-server-content.165183/) (snippet); [Emperor Servers wiki: share content with CM wrapper](https://wiki.emperorservers.com/assetto-corsa-server-manager/share-content-with-content-manager-wrapper)
- **Every driver needs the skin:** each driver must download the livery under the same name into the same car folder. — [RaceDepartment: how to use custom liveries online](https://racedepartment.com/threads/how-to-use-custom-liveries-online.197286/) (snippet)
- **Car-level `ext_config.ini` is a CSP file** in `content\cars\<car>\extension\`, so it has no effect without CSP. — [CSP acc-extension-config wiki](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki)
- **A sticker fix can involve several files:** the per-skin sticker fix seen locally depends on extra files in the skin folder (`Banner.kn5`, `banner.dds`, `yellowglass.dds`, `junya_decal.kn5` + `glass_sticker.dds`). — local: skin folders listed in sections 2 and 4

### Inferences
- **Ratty's Racing grids are a closed community** sharing skins through the race server and CM, so per-skin CSP configs are acceptable. The generator must package `ext_config.ini` and every referenced texture and kn5 inside the skin folder, so one download is complete.
- **Make the non-CSP view acceptable on purpose:** the shared or mirrored texture should hold a mirror-safe design, or be blank where text would read backwards. The CSP layer then adds or corrects text.
- **Avoid car-level edits for livery features:** they would change the car for everyone and can conflict with the mod author's updates.
- **Check any online integrity setting before relying on per-skin kn5 inserts.** CSP has server-side options to restrict client configs, but none of the sources read here document them.

### Gaps
- I found no official CSP or AssettoServer documentation on how per-skin `ext_config.ini` behaves online, including whether servers can enforce or strip it. The takeaway is inference from how AC loads skins locally plus community posts.
- Not tested: what happens when two clients both have CSP but different versions of the skin's `ext_config.ini`. Presumably each sees their own copy.
