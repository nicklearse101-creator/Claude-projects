# Content Manager (CM) livery-painting features: templates, AO, Paint Shop, and CSP-protected cars

Research date 2026-11-17. Main evidence is CM's own source code (github.com/gro-ove/actools). That repo is current: its latest commits are from 2026-06-17 ([commits](https://github.com/gro-ove/actools/commits/master)). The official Paint Shop manual is older: posted 2017-04-12, last edited 2017-08-30 ([acstuff forum thread 16](https://acstuff.club/f/d/16-content-manager-paint-shop), read through the forum API at https://acstuff.club/f/api/discussions/16). Where the 2017 manual and the 2026 code differ, the code is newer. Local examples come from D:\SteamLibrary\steamapps\common\assettocorsa\content\cars (read only). Scratch downloads are in D:\ClaudeData\tmp\cm_research.

## Q1. Custom Showroom "Car texture" dialog: what do View mapping, Calculate AO, Export and Replace produce, and where are the files saved?

### Takeaway
The "Car texture" dialog has four buttons:
- **View mapping**: renders the UV wireframe of every mesh that uses the chosen texture. The lines are pure green on a fully transparent background. The default size is the texture's own size, with 512/1024/2048/4096 or custom options. It saves as PNG (also DDS or JPEG).
- **Calculate AO**: bakes a grayscale ambient-occlusion map onto that texture's UV layout, at the texture's size or 512/1024/2048/custom. It saves as DDS (DXT5 by default), PNG or JPEG.
- **Export**: dumps the raw embedded texture from the kn5. It only shows in Developer mode, and only when the kn5 is editable.
- **Replace**: writes a new texture into the kn5 file itself. It is a modelling tool, not a skinning tool.

Save dialogs for these images open in the car's folder (the folder that holds the kn5). Every result opens in GIMP. A DDS opens in GIMP 2.10+ natively.

### Cited Findings
**The dialog**
- The dialog is titled "Car texture". It shows a 240×240 preview, the texture type, format, dimensions, file size and a "Used for:" list (the materials that use the texture). Its button row has View mapping (split button), Calculate AO (split button with "Show options"), Replace (split button with Rename / Fork / Change texture) and Export. — [Kn5TextureDialog.xaml](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml)
- To reach the dialog, painters click body parts in CM Showroom and check which texture is in the txDiffuse slot. This comes from a community post; only a search snippet was seen. — [OverTake skinning thread p.7](https://overtake.gg/threads/skinning-assetto-corsa-cars-from-nothing-using-mudbox-and-photoshop.147080/page-7)

**View mapping (UV wireframe)**
- Clicking the main button uses the size of the loaded texture (fallback 1024×1024). The drop-down offers 512, 1024, 2048, 4096 or a custom "WxH" prompt (default suggestion 2048x2048). — [Kn5TextureDialog.xaml.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml.cs)
- The render goes to CM's temporary storage as "<texture name> UV.png" and opens in an image viewer with a Save option. Save offers PNG (straight copy), DDS (re-encoded as RGBA4444) or JPEG, and the save dialog starts in the folder of the car's kn5. — [Kn5TextureDialog.xaml.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml.cs)
- The renderer draws in wireframe mode with no culling and antialiased lines. It clears to `Color.Transparent` and writes a PNG. — [UvRenderer.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificSpecial/UvRenderer.cs)
- Which meshes are drawn: only those whose material uses the chosen texture name. UVs outside 0–1 are wrapped back into the square, sampling up to 16 UV tiles per mesh. — [UvRenderer.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificSpecial/UvRenderer.cs)
- The UV shader plots the first texture coordinate and returns `float4(0, 1, 0, 1)` for every pixel, so lines are opaque pure green (#00FF00). — [SpecialUv.fx](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Shaders/Special/SpecialUv.fx)

**Calculate AO (ambient-occlusion bake)**
- The drop-down offers "Calculate 512×512 / 1024×1024 / 2048×2048 Map", "Calculate map of custom size", and "Show options". There is no 4096 preset, but a custom size can be 4K. The main button uses the texture's own size (fallback 1024). — [Kn5TextureDialog.xaml](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml); [BakedShadowsRendererViewModel.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs)
- Default bake settings, stored as presets under "Baked Shadows":

  | Setting | Default |
  |---|---|
  | Light angle range ("From" / "To") | 0° to 60° |
  | Brightness | 220 |
  | Gamma | 60 |
  | Pixel density | 4 |
  | Ambient | 0 |
  | Bias (second) | 70 |
  | Iterations | 5000 |
  | Padding | 4 px |
  | Shadow map size | 2048 |
  | FXAA | on |
  | Fully transparent | on |
  | Use DXT5 for DDS | on |

  — [BakedShadowsRendererViewModel.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs)
- Tooltips in the options panel:
  - Padding avoids artefacts on UV borders seen from far away.
  - Be careful with pixel density for ≥4K maps.
  - With DXT5 off, the DDS is saved as Luminance+Alpha 8.8, which is twice as heavy.

  — [BakedShadowsSettings.xaml](https://github.com/gro-ove/actools/blob/master/AcManager/UserControls/BakedShadowsSettings.xaml)
- Every visible, shadow-casting node of the model casts shadows. The bake is projected only onto the meshes that use the chosen texture. The renderer copies its state from the open showroom, and the output is a PNG byte stream with transparent clears. — [BakedShadowsRenderer.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificSpecial/BakedShadowsRenderer.cs); [BakedShadowsRendererViewModel.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs)
- The result viewer shows two images, "Generated AO map" and "Original texture". Only the first can be saved.
  - The default file name is the texture's name, in the kn5's folder.
  - DDS is saved as DXT5, or Luminance+Alpha if DXT5 is off.
  - JPEG is saved at quality 97.
  - With "Fully transparent" on, a PNG save is first passed through JPEG conversion, then saved as PNG.

  — [BakedShadowsRendererViewModel.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs)
- The Paint Shop manual points to this feature: CM can generate its own AO textures for a pattern's base layer when no AO texture can be found. — [CM Paint Shop manual (2017)](https://acstuff.club/f/d/16-content-manager-paint-shop)

**Export**
- Export saves the texture's raw bytes exactly as stored in the kn5, usually a DDS. The save dialog starts in the active skin's folder or the kn5 folder, with the texture's name. — [Kn5TextureDialog.xaml.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml.cs)
- Export is only available when the texture data exists, the kn5 is editable, and CM's Developer mode is on (`SettingsHolder.Common.DeveloperMode`). Otherwise the button is hidden. — [Kn5TextureDialog.xaml.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml.cs)
- A kn5 is "editable" only when it was loaded with full materials and nodes. — [Kn5Basic.cs](https://github.com/gro-ove/actools/blob/master/AcTools/Kn5File/Kn5Basic.cs)

**Replace**
- Replace writes the chosen image into the kn5's own texture table and rewrites the kn5. It warns if the file is not DDS. The same menu has Rename, Fork (a copy of the texture for one material) and Change texture (point a material at another texture). All of them need an editable kn5. — [Kn5TextureDialog.xaml.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml.cs)

### Inferences
- A painter's template from CM is two images at the texture's own size, made from the same dialog: "<tex> UV.png" (green lines, transparent) and an AO image (grayscale). An app could produce the same thing from a readable kn5: the UV0 wireframe of every mesh using the texture, wrapped into 0–1.
- Because the UV PNG has a transparent background, it can be layered straight on top in GIMP. Saving the UV as JPEG would lose that transparency. This is not tested, but JPEG has no alpha.
- "Fully transparent" most likely makes the AO's alpha channel transparent, so the car's txDetail colour shows through in AC's car-paint shaders. The PNG/JPEG path drops alpha, so those saves give a plain opaque grayscale AO, which is what a painter wants as a base layer. I did not confirm the exact shader behind this option (I could not find it in the repo).
- Painters should avoid Replace: it changes the shared model file, not a skin. Skins belong as loose files in skins/<skin>/.

### Gaps
- I could not confirm where the Developer mode switch is in CM's Settings UI. The code only names the setting.
- I found no screenshots or official docs page for the "Car texture" dialog. Behaviour here is read from source, not tested in the app.
- I did not confirm whether View mapping can draw UV2 (the second UV set). The shader uses only the first texture coordinate.

## Q2. Do these features work on CSP-protected (encrypted) cars?

### Takeaway
By default, no. CSP-encrypted kn5 files do not load in CM's Custom Showroom. The Car texture dialog, View mapping, Calculate AO, Export and Paint Shop all live inside that showroom, so none of them are available. There are two exceptions, both chosen by the car's author:
- the author asked for their encryption to be supported in CM, or
- the author shipped an unencrypted stand-in model under `[LOD_HR]` in lods.ini. CM then uses that model, and its UVs are only as good as the author made it.

### Cited Findings
- The CSP docs say by default, "your cars won't work in Custom Showroom". An author can ask for support to be added in a future CM update, with a warning that this adds another way to steal the model. — [CUP docs: kn5 encryption](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- The same page describes a legitimate workaround for authors: an unencrypted kn5 listed under `[LOD_HR]` in lods.ini. AC ignores it and CM uses it as the default model. The docs suggest making this model deliberately less usable in game (MeshSmooth, interior or wheels removed, meshes merged). — [CUP docs: kn5 encryption](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- The encryption protects the kn5 model file, meaning its geometry and its embedded textures. That page says nothing about skins folders, templates or Paint Shop. — [CUP docs: kn5 encryption](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- History: only the old basic encryptor supported Custom Showroom, and that encryptor is described as broken. Its no-showroom variant and later versions (v3, v5, v6, v9 for CSP 0.3.0) are listed without showroom support. — [CUP docs: about old encryption](https://cup.acstuff.club/docs/about-old-encryption)
- CM's kn5 reader accepts only files that start with the standard kn5 signature. Otherwise it throws "Not a valid KN5 file." — [Kn5Basic.cs](https://github.com/gro-ove/actools/blob/master/AcTools/Kn5File/Kn5Basic.cs)
- Paint Shop runs inside the Custom Showroom (LiteShowroomTools.PaintShop) and saves through the showroom renderer. — [LiteShowroomTools.PaintShop.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/LiteShowroomTools.PaintShop.cs)
- CSP has its own in-game Lua paint app, "app-paintshop", for drawing on cars in AC. It needs CSP 0.1.77 or newer. I did not verify whether it works on protected cars. — [ac-custom-shaders-patch/app-paintshop](https://github.com/ac-custom-shaders-patch/app-paintshop)

### Inferences
- I did not test an encrypted file in CM, so the exact failure is unconfirmed. Since the reader needs the standard signature, a protected car most likely fails to load in Custom Showroom: an error, or no model.
- With an `[LOD_HR]` stand-in, View mapping and Calculate AO would work on the stand-in. They only match the in-game car if the stand-in keeps the same UVs. MeshSmooth or merged meshes may change them, and a removed interior means no interior templates. Check a template made this way against the car in game.
- Skins on protected cars are still loose textures in content/cars/<car>/skins/<skin>/, because AC loads skin-folder textures over the kn5's ones. A painter can open the shipped skin DDS files in GIMP as a starting point, and an app can do the same, without touching the protected kn5. This follows from AC's skin system; the CSP page does not state it.
- For a 2D app on protected cars, the only legitimate template sources are: the author's own template pack, the existing skin textures, an `[LOD_HR]` model if present, and any loose files in ui/cm_paintshop/. Never the encrypted kn5.

### Gaps
- I found no official statement on which current authors or encryption versions have opted into CM showroom support, and no list of protected cars that ship `[LOD_HR]`.
- I could not reach current (2025–2026) forum threads that describe exactly what CM shows for a protected car. The simracingsystem tutorial failed with an expired certificate, and acstuff forum pages render only through the API.

## Q3. CM Paint Shop format (ui/cm_paintshop.json): how does it describe paintable areas, masks and patterns, and could an app reuse it?

### Takeaway
cm_paintshop.json is a lenient JSON file (comments allowed). Each entry names a car texture and says how to make it:
- a solid or tinted colour (`color`, `tintedWindow`)
- car paint, made of txDetails colour, txMaps and txDiffuse pattern layers (`carPaint`)
- a pattern (`pattern`)
- a licence plate (`licensePlate`)
- flagged or candidate replacements

Masks and patterns are images whose R/G/B channels pick colours 1/2/3. Numbers, labels and flags are placed in texture-pixel coordinates. Resources marked "./" live in ui/cm_paintshop/ (or ui/cm_paintshop.zip) and are plain loose files.

An app can read this file to get, for each car:
- the exact texture file names to write
- default colours
- mask and pattern images (when they ship as loose files)
- number and name-panel positions on the 2D texture

Plain texture names refer to textures inside the kn5, which a protected car does not expose.

### Cited Findings
**Where CM looks for rules and how it saves**
- Rule lookup order:
  1. ui/cm_paintshop.json in the car folder
  2. "Paint Shop" folders in `AppData\Local\AcTools Content Manager\Data` and `Data (User)`
  3. an online database

  Each file is an object keyed by car ID, holding an array of options. Resources go in a folder or ZIP next to the JSON with the same name. — [CM Paint Shop manual (2017)](https://acstuff.club/f/d/16-content-manager-paint-shop)
- The online rules come from GitHub repos. The CM tip links MadMat13/CM-Paint-Shop, and the loader fetches a repo's releases through the GitHub API and caches them under CM's "Temporary\Paint Shop\<sha1 of URL>". — [Paint Shop.txt tip](https://github.com/gro-ove/actools/blob/master/AcManager/About/ImportantTips/Paint%20Shop.txt); [PaintShopRulesLoader.cs](https://github.com/gro-ove/actools/blob/master/AcManager.Tools/Helpers/PaintShopRulesLoader.cs)
- Saving writes into the car's skins folder. It either overwrites the current skin or creates a new skin, suggested ID "generated" (made unique). It writes the DDS files plus a `cm_skin.json` with the chosen options, then generates a preview. — [LiteShowroomTools.PaintShop.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/LiteShowroomTools.PaintShop.cs)
- Output DDS format: RGBA8888 for small textures and DXT5 for large ones, txMaps without alpha. A suffix on the texture name forces a format: `:dxt1`, `:dxt5`, `:l`, `:la`, `:rgb565`, `:rgba4444`, `:rgba`, `:rgb`. — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)

**Auto-detection when there are no rules**
- The 2017 manual lists car paint ("Metal_detail.dds", "metal_detail.dds", "car_paint.dds", "carpaint.dds", ...), rims ("car_paint_rims.dds", "metal_detail_rim.dds"), calipers, roll cage, "ext_glass.dds" (windows) and "Plate_D.dds"/"Plate_NM.dds" (plates). txMaps comes from the first material using `ksPerPixelMultiMap_damage_dirt`. — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)
- The newer CUP list adds indexed names (`metal_detail_<2–8>`, `metal_detail_skin_<X>`, `rim_detail_<X>`, `leather_<0–6>`, `carpet<X>`, `INT_fabric<X>` ...) and says names are matched to suit Kunos cars and some mods. — [CUP docs: default names for Paint Shop](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom)

**Option types and their fields**
- **Common fields:** `type` (a missing type means a colour option), `name`, `enabled` (only car paint and plates start enabled). An option can also be the string `"@guess"`, or another car's ID to inherit its rules. — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)
- **`color`:**
  - `texture`
  - `tintBase` (tint the existing texture instead of filling it)
  - `pairs` (texture → {`source`, `mask`})
  - `defaultColor` / `defaultColors` (with a mask, colours 1/2/3 apply to the mask's red/green/blue channels)
  - `autoLevel` / `desaturate` (prepare the source first)

  — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)
- **`tintedWindow`:** all `color` fields plus `defaultOpacity` (default 0.23) and `fixedColor`. — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)
- **Flagged types:** `transparentIfFlagged`, `solidColorIfFlagged` (`color`, `opacity`) and `replacedIfFlagged` (`pairs`), each with `inverse`. — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)
- **`carPaint`** controls three layers:
  - txDetails: `texture`, `defaultColor`, `colorAvailable`, `flakesAvailable`, `flakesSize` (default 512), `candidates` (named replacement textures, optionally `colored`)
  - txMaps: `mapsTexture`, `mapsAutoLevel`, `mapsDesaturate`, `mapsDefaultTexture`
  - txDiffuse livery: `patternTexture`, `patternBase` (the AO base), `patternOverlay` (badges on top), `patternSize`, `patterns[]`

  — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)
- **Each pattern:**
  - `pattern`: an image whose red, green and blue channels are colours 1, 2 and 3. Its alpha marks where txDetails shows instead. It can also be a plain hex colour such as `#00000000`.
  - `defaultColors` (1–3; without them the pattern is not colourable), `overlay`, `size`
  - `numbers[]`, each with `size`, `font` (name or TTF resource), `left`/`top` in pixels, `angle`, `horizontalAlignment`, `verticalAlignment`, `color` (fixed, or the index of a pattern colour), `weight`, `style`, `stretch`

  — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)
- **`pattern`:** the pattern part of carPaint on its own, with `texture`, `base`, `overlay`, `size`, `patterns`. **`licensePlate`:** `style` (from CM's "Data\License Plates"), `texture` (default Plate_D.dds), `normals` (default Plate_NM.dds). — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)

**How texture references work**
- A plain name means a texture inside the kn5. `./name` means a file in the rules resources. `#rrggbb(aa)` means a solid colour. `@self` means the same kn5 texture.
- An object form `{path, autoLevel, desaturate}` prepares a texture first. A suffix picks or shuffles channels, e.g. `tex.dds:a` or `:rgb0`. Separate channels can also be built from several sources, e.g. `{ "red": "...:a", "blue": "./mask.png:r", "alpha": "#88ffffff" }`.

  — [CM Paint Shop manual](https://acstuff.club/f/d/16-content-manager-paint-shop)

**Newer than the 2017 manual (from the 2026 code)**
- The loader also recognises:
  - patterns: `flags`, `labels`, `decals`, `role`, `underlay`, `overlayWithoutAo`, `underlayWithoutAo`
  - car paint and maps: `mapsMask`, `allowedColors`
  - livery icon: `liveryStyle`, `liveryPriority`, `liveryColor(s)`
  - options: `replacement` with `candidates`, `guessColorsFromPreviews`

  Its type names are lower-case strings ("carpaint", "tintedwindow", "licenseplate", "solidcolorifflagged", ...). — [PaintShop.cs](https://github.com/gro-ove/actools/blob/master/AcManager/PaintShop/PaintShop.cs)
- The source has one class per option type: CarPaint, ComplexCarPaint, ColoredItem, TintedWindows, LicensePlate, Replacement, MultiReplacement, ReplacedIfFlagged, SolidColorIfFlagged, TransparentIfFlagged, TexturePattern, plus guessing (PaintShop.Guess.cs). — [actools/AcManager/PaintShop](https://github.com/gro-ove/actools/tree/master/AcManager/PaintShop)

**Real local examples (read only)**
- **Survey:** 55 local cars have ui/cm_paintshop.json. Entry `type` counts:

  | type | count |
  |---|---|
  | color | 164 |
  | carPaint / carpaint / CarPaint | 67 / 22 / 2 |
  | pattern | 25 |
  | licensePlate | 11 |
  | replacement | 10 |
  | tintedWindow | 9 |

  — local scan of D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\*\ui\cm_paintshop.json
- **Body paint whose txMaps is an AO-style map**, `...\cars\citroen_saxo_cup\ui\cm_paintshop.json`:
  `{ "type": "carPaint", "name": "1. Body Color", "texture": "metal_detail.dds", "mapsTexture": "AO_body_map.dds", "mapsAutoLevel": true, "defaultColor": "#FFFFFF" }`
- **Number and name panel placed in texture pixels**, `...\cars\rss_formula_1990\ui\cm_paintshop.json`. One `pattern` entry for texture "90_Masters.dds" has:
  - underlay `"./90_Masters.dds"`, a loose file that really exists at `ui\cm_paintshop\90_Masters.dds`
  - a flag at left 512 / top 433, size 200
  - a pilot-name label at 512/126, size 120
  - a number at 512/777, size 275, Arial weight 700
- **Tinted window**, `...\cars\adc_corvette_c5_sd\ui\cm_paintshop.json`:
  `{ "type": "tintedWindow", "texture": "glass70.dds", "defaultOpacity": 0.23, "fixedColor": false }`
- **Replacement with candidates**, `...\cars\nohesi_traffic_tesla_truck\ui\cm_paintshop.json`: "11 Window Tint" replaces texture `black_20_percent_alpha.dds` with named candidates "0%", "20%", "40%", "60%", "N/A", which point to `./cm_paintshop/...dds`. That car's ui folder has no cm_paintshop subfolder, so those candidate files are missing locally.
- **The files are not strict JSON:**
  - many end with trailing commas (`],\n}`)
  - some use a bare top-level array (all rss_* cars)
  - some key the array by a different car ID than the folder: adc_bmw_e46 uses "lm_bmw_e46_nfsmw", adc_corvette_c5_sd uses "lm_corvette_c5", nohesi_traffic_tesla_truck uses "traffic_car_15_nohesi"

  — local files above

### Inferences
- **For a 2D app, cm_paintshop.json gives:**
  - which skin-folder texture names are paintable, so the app knows exactly which DDS names to write
  - default colours
  - which layer each texture is: txDetails colour, txMaps, or txDiffuse livery
  - any loose mask, AO or pattern images in ui/cm_paintshop/ (R/G/B = colour 1/2/3 regions)
  - pixel positions for numbers, names and flags on the livery texture

  The rss_formula_1990 example puts the number box at (512,777) on a 1024-wide texture.
- **Limit on protected cars:** entries that only name kn5 textures (most local ones, e.g. "metal_detail.dds", "AO_body_map.dds") still give names and defaults. Their pixel data lives in the encrypted kn5, so the app can't read it. Only `./` resources and existing skin-folder files are readable.
- **Parser needs:** a parser should
  - accept comments and trailing commas
  - match `type` case-insensitively
  - accept either a bare array or an object keyed by any car ID

  The local files have all of these, and the code compares lower-case type names. I did not check how CM picks the right key in a car-local file, so this part is inferred.
- `liveryStyle` (e.g. "CornerTriangle" in actk_citroen_ax_proto) probably controls CM's auto-generated livery icon. I inferred this from the key names and found no doc.

### Gaps
- No official doc covers the post-2017 keys (`flags`, `labels`, `decals`, `role`, `underlay`, `replacement`, `liveryStyle`, `mapsMask`). Their meanings are inferred from names and local usage only.
- I did not open the MadMat13/CM-Paint-Shop rules repo to see how many cars it covers or whether its masks would fit protected cars.
- The purpose of `ui/cm_textures.json` (seen in rss_gt_lanzo_v12) is unknown.

## Q4. Typical community workflow for painting a car (including a protected one) with CM + GIMP/Photoshop

### Takeaway
For a readable car, the CM workflow is:
1. Open the car in CM Showroom.
2. Click the body to find its txDiffuse texture and open it in "Car texture".
3. View mapping at the texture's own size, then save the PNG.
4. Calculate AO at the same size, then save it as PNG.
5. Layer them in GIMP or Photoshop: AO at the bottom, livery in the middle, UV lines on top (hidden at export).
6. Export DDS with the exact texture name into skins/<new skin>/.

For a protected car, steps 1–4 normally fail. A painter falls back to the author's template, the car's existing skin DDS files, or CM Paint Shop rules shipped in ui/, unless the author added CM support or an `[LOD_HR]` model.

### Cited Findings
- One community tutorial says making your own template is much easier with Content Manager installed, including for cars without official templates, and uses CM's showroom for previews. Only a search snippet was seen; the page failed with an expired TLS certificate. — [SimRacingSystem tutorial](https://simracingsystem.com/showthread.php?tid=2249)
- Painters find which texture a panel uses by clicking parts in CM Showroom and reading the txDiffuse assignment (snippet only). — [OverTake skinning thread](https://overtake.gg/threads/skinning-assetto-corsa-cars-from-nothing-using-mudbox-and-photoshop.147080/page-7)
- A skinning guide says GIMP works as well as Photoshop. It recommends DDS DXT5 (BC3), mipmaps disabled, at most 4096 px (2048 for decals), and the NVIDIA DDS plugin for exporting. Only a search snippet was seen. — [AC skin guide](https://sites.google.com/view/acskinguide)
- **The CM side of the workflow, from source:**
  - View mapping and Calculate AO both default to the texture's own size, so both layers line up pixel for pixel.
  - Save dialogs open in the car folder.
  - The UV PNG is transparent with green lines.
  - Paint Shop and Replace/Export are separate paths.

  — [Kn5TextureDialog.xaml.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/Kn5TextureDialog.xaml.cs); [BakedShadowsRendererViewModel.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/BakedShadowsRendererViewModel.cs)
- Protected cars don't open in Custom Showroom by default. The `[LOD_HR]` stand-in is the author-side option. — [CUP docs: kn5 encryption](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)

### Inferences
**Readable car, step by step (from the source code, not tested in the app):**
1. In CM, open the car → Showroom (Custom Showroom).
2. Click the body panel and open its txDiffuse texture, which opens "Car texture". Note the dimensions and the "Used for" materials.
3. Click View mapping (the main button gives the texture's size) → Save as PNG, e.g. "<tex> UV.png".
4. Click Calculate AO (the main button gives the same size; use "Show options" to tune it) → Save as PNG.
5. In GIMP: open the AO as the base layer. Add livery layers above it, using Multiply over the AO or AO on top in Multiply. Put the UV PNG on top as a guide and hide it before export.
6. Export as DDS (DXT5/BC3, or DXT1 where no alpha is needed) with the exact texture name, into content/cars/<car>/skins/<skin>/.
7. Reload the skin in CM Showroom or in game to check.

**Protected car:**
1. Check whether the showroom loads it. If it does (CM support or `[LOD_HR]`), use the steps above, then verify UV fit in game.
2. If it doesn't, use the author's template folder if one ships (some mods include a `template` folder, e.g. local adc_bmw_e46, which may not itself be protected).
3. Or open an existing skin's DDS from skins/ as a base.
4. Or use ui/cm_paintshop/ resources and cm_paintshop.json for texture names, masks and number positions.
5. CSP's in-game paint app is another possible route. It is unverified on protected cars.

### Gaps
- I found no current (2025–2026) tutorial or thread written specifically about painting CSP-protected cars with CM. The forum and tutorial sources seen are older or snippet-only.
- I did not confirm that the CSP app-paintshop works on protected cars, or what format it exports.
- None of this was tested hands-on in CM in this session. All CM behaviour comes from reading the source.
