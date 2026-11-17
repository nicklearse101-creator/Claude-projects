# Tint the detail tiles, spare the atlas

Ratty's4Skin can recolour most interiors from the skin folder alone, but only if it works texture by texture rather than part by part. For each part it has to find the material that owns it, find which texture slot holds the colour, and check what else uses that texture. On Kunos cars the visible colour almost never sits in the big cockpit texture. That texture is a grey ambient-occlusion (AO) atlas with alpha near 0, and the colour comes from small tiling **txDetail** tiles such as `leather_seat.dds`, `alcnt.dds` and `carpet.dds`. Kunos's own stock skins already swap those tiles: 94 skin folders on Nik's PC ship their own `leather_seat.dds`. Mods are built three ways: tiny 1–8 px colour swatches (**32 % of colourable mod interior materials**), Kunos-style detail tiles (40 %), and large baked colour atlases that need painting by UV region, the way the body livery is painted. The default write route should be a recoloured texture under the model's exact texture name. It needs no CSP and anyone with the skin sees it. A CSP `SHADER_REPLACEMENT` with `RESOURCE_FILE` (the trick the app already uses for glass, confirmed in game) is only needed when a tiling texture is shared with the outside of the car, or with another part that should get a different colour. Recolour with an OKLab lightness remap. Protect stitching and logos with a k-means mask computed inside the part's own UV region. Never touch txNormal, txMaps, displays, glass, carbon or `metal_detail`. Ship the feature behind an Interior panel that is off by default, so every car that works today gives byte-identical output. Before writing any code, settle three open questions about how AC and CSP behave with one in-game test on each of three cars.

## Scene nodes find the cabin; part words need guard rails

The most reliable interior signals are AC's own scene nodes, not part words. The table shows how many cars use each signal (179 Kunos cars, 646 mods). It comes from a read-only scan of the 825 cars on Nik's PC whose kn5 could be read ([scan.py](file:///D:/ClaudeData/tmp/interior_scan/scan.py), [analyze.py](file:///D:/ClaudeData/tmp/interior_scan/analyze.py), [markers.py](file:///D:/ClaudeData/tmp/interior_scan/markers.py)).

| Signal | Kunos | Mods |
|---|---|---|
| `COCKPIT_HR` node | 179 of 179 | 432 of 646 |
| `STEER_HR` node | 179 | 588 |
| `CINTURE_ON` node (belts) | 168 | 244 |
| `INT_` token in material names | 97 % | 75 % |

What `COCKPIT_HR` and `COCKPIT_LR` actually do in the game rests only on modder posts, which describe them as a high-res / low-res cockpit LOD switch that CSP also uses ([GTPlanet mods thread](https://gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-3372)). That is enough to use them as markers. It is not enough to rely on their LOD behaviour.

Part words work only with strict matching rules:

1. Lower-case the name.
2. Split it into tokens on `_`, spaces, dots, digit/letter changes and camelCase, so `IntSeatCloth` gives int / seat / cloth.
3. Let "strong" patterns match anywhere, but make short words match a whole token.
4. Throw the name out if it hits an exclusion list.

The false friends are large. Of the names that contain `wheel`, **3,583 in all, only 851 are steering wheels**. Only 32 of 4,084 `brake` names are pedals, 967 of 5,244 `door` names are door cards, 92 of 441 `roof` names are headliners, and 39 of 182 `lever` names are gear levers ([probes.py](file:///D:/ClaudeData/tmp/interior_scan/probes.py)).

Some words mean something else entirely:

| Word | What it usually means |
|---|---|
| `mat` | "material", in 10,703 names (never use it for carpet mats) |
| `inst` | "instance" in ACC-derived mods; `EXT_Carpaint_Inst` is the **outside** body paint in 64 cars |
| `skin` | leather in Kunos interiors (`INT_*Skin*`), not the livery |
| `int` | also appears inside `CINTURE`, `carpaint`, `internal_glass` and `intercooler` |

Glued forms such as `intplastic`, `intchassis` and `intalcantra` are real interior names, so they need a short whitelist ([probes.py](file:///D:/ClaudeData/tmp/interior_scan/probes.py)). The condensed dictionary:

| Part | Reliable names (strong / token) | Must exclude | Cars (Kunos / mods) |
|---|---|---|---|
| Seat shell | seat (not belt/leon/ibiza/cupra), sedil, asiento, backrest, headrest, bucket, recaro, bride, sitz | valve_seat, SEAT brand, lamp *bucket*, emissive/led | 146 / 505 |
| Seat fabric / leather | alcantara, alcnt, suede, leather, leder, pelle, tessut, stoffa, fabric, cloth, velour, stitch, cucitur | exhaust fabric, tyre | 175 / 542 |
| Belts | cintur, seat.?belt, harness, schroth, sabelt, takata, buckle, `cpbelt`; token belt/strap | cambelt/timing/fan belt, pulley, **beltline**, tow strap, warning lights | 170 / 434 |
| Dashboard | dash (not dashcam), cruscott, plancia, planche_de_bord, tableau, armaturen, binnacle | dash + light/glass/display/lcd/gauge/needle/decal | 69 / 417 |
| Door cards | door.?card, door.?panel, int.?door, inner.?door, door.?trim, armrest, intdoor | **door glass**, `ext_carpaint_door`, jambs, outer handles, mirrors | 67 / 197 |
| Roll cage | roll.?cage, roll.?bar, roll.?hoop, gabbia, arceau, jaula; token cage/tube/weld | **anti_roll_bar**, lamp cages, soft_top_cage, undercage, intercooler/exhaust tubes | 36 / 375 |
| Carpet / floor | carpet, tappet, moquet, floormat, footwell; token floor | underfloor, diffuser, plank, splitter, chassis_floor, **never `mat`** | 89 / 242 |
| Headliner | headlin, roof.?lin, int.?roof, ceiling, padiglion, cieldetoit, sun.?visor | `carpaint_roof`, `murcielago`, roof lights, sunroof glass | 6 / 123 |
| Steering wheel | steer (not arm/rack/rod/knuckle), volant(e), lenkrad, swheel, st.?wheel, momo; token stw/sw | road wheels, `susp_steer`, tie rods | 173 / 576 |

Source: [parts.txt](file:///D:/ClaudeData/tmp/interior_scan/parts.txt).

Kunos breaks the part approach in one important way: **it names surfaces, not parts**. `ks_mazda_mx5_cup` has `INT_OCC_Plastic_GREY`, `INT_OCC_Alcantara`, `INT_OCC_Skin_GREY`, `INT_OCC_White_Paint` (the roll bar), `INT_SeatBelts` and `INT_Seams` on meshes called `GEO_Cockpit_HR_SUB0..5`. Only 69 Kunos cars match "dash" and only 6 match "headliner" ([ks_mazda_mx5_cup.json](file:///D:/ClaudeData/tmp/interior_scan/cars/ks_mazda_mx5_cup.json)). So the app needs a second way in: when no part word matches, it groups materials by surface word. The groups are leather / alcantara / fabric / plastic / carpet / painted metal, plus belts, which have their own `CINTURE_*` nodes. Mods built from Forza-style `_a` names (`seatl_a`, `dashpad_a`, `doorcardlf_a`, `pedals_a`; 19 % of mods) are the easiest case, because their names spell the parts out. Meshes with generic names (`polySurface123`, `Object004`) can only be placed by their position inside the body, which nobody has tried yet.

Some names look like interior but must never be recoloured. In Kunos cars these are `INT_Display` (45 cars), `INT_Windscreen` (34) and `INT_LCD` (33). In mods they are `internal_glass` (172), `int_display` (63), `int_lcd` (56), `int_racelogic` (33) and `motecnl` (31) ([parts.txt](file:///D:/ClaudeData/tmp/interior_scan/parts.txt)). The same goes for anything on the ksWindscreen shader, alpha-blended or emissive materials, and the gauge/dial/needle family, which matches 766 cars. Stitches and logos are often separate alpha-tested materials (`INT_Seams`, `INT_cuciture_NM`, `BRIDE_DECAL`). Leaving those out protects them for free ([mats.py](file:///D:/ClaudeData/tmp/interior_recolour/mats.py)).

## Colour lives in three places, depending on who built the car

**Kunos interiors are an AO atlas times a colour tile.** In `ks_porsche_991_carrera_s`, `INT_Occlusion.dds` is a 1024² grey texture (saturation 0.00) with mean alpha **0.00**. The seat leather material takes its tan colour from `leather_seat.dds` (512×256), tiled 50 times. The Miata's red plastic is `PlasticDetail_red.dds`, tiled 180 times ([texsample.py](file:///D:/ClaudeData/tmp/interior_scan/texsample.py)). 57 % of Kunos interior materials carry a txDetail.

Two CSP sources back this reading up. The CSP docs say that in `ksPerPixelMultiMap` materials "Alpha in `txDiffuse` acts as a mask for `txDetail`" ([CSP docs: Paint Shop default names](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom)). CSP's own interior library describes Kunos style as "occlusion map in txDiffuse and color in txDetail" ([materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)). The exact shader formula (a plain multiply, a lerp by alpha, any ×2 factor) was not found in any source. That is the first thing the in-game test has to settle.

**Mods are a mix.** Their most common interior shader is the plain `ksPerPixel` (3,320 materials). **4,592 of 14,158 colourable mod interior materials (32 %, in 341 cars) sit on swatches of 8 px or less**, including exporter-made `rgbaXXXXXXXX` textures ([markers.py](file:///D:/ClaudeData/tmp/interior_scan/markers.py)). Others use a tiled colour diffuse plus a normal map on `ksPerPixelNM_UVMult`. In the S14 mod, for example, one 1844² `leather_dark.dds` colours the dash, door cards, console, parcel shelf and steering rim ([mats.py](file:///D:/ClaudeData/tmp/interior_recolour/mats.py)). The rest bake the colour into big atlases such as `int_ao`, `interior_lod0` and `leather_dark`, up to 4096 px ([tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)).

**Atlases and tiled textures behave in opposite ways.** On a true atlas the parts divide the texture cleanly. On the MX-5 Cup, seven materials share `INT_Cockpit_OCC.dds` and **0.0 % of its texels belong to more than one of them**. The seat-leather mask grows from 12.6 % to 16.0 % after a 2 px dilation and still touches no other part ([atlas test](file:///D:/ClaudeData/tmp/interior_recolour/mx5cup_atlas_seat_red.png)). A tiled texture is the opposite. Abarth's `TEssuto.dds` is used by both the seat cloth and the headliner, with UVs spanning −3.9 to 17.8, so every user covers the whole texture and no skin file can separate them ([dump.py](file:///D:/ClaudeData/tmp/interior_recolour/dump.py)).

**Sharing with the outside is rare, with one big exception.** A large interior texture is also used outside in 24 Kunos cars and 148 mods, but it covers a median of only about **1 % of the interior area**. The real crossover is paint. Kunos `INT_Carpaint` / `INT_OCC_Carpaint` parts (inner door skins, cockpit metal) use `metal_detail.dds`, the same detail texture that skins override for the body colour. A skin-overridden outside detail texture also reaches interior parts in **68 Kunos cars and 115 mods**. In mods, swatches such as `black` (35 cars) and `rgba010101ff` (18) are also shared between inside and outside ([shared.py](file:///D:/ClaudeData/tmp/interior_scan/shared.py), [tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)).

This affects the app today. For Kunos-style paint, the app already writes a plain white copy of the body material's txDetail into every new skin ([skingen.py ~line 3569](file:///D:/Claude/Claude-/ac-skin-generator/skingen.py)). On cars whose interior carpaint uses the same `metal_detail.dds`, that should already be turning inner door skins and cockpit metal into white × AO in app-made skins. This follows from the code and the scan. It has not been checked in game.

Kunos cars also keep a **second copy of the interior colours** in a low-res cockpit texture (`Cockpit_LR.dds`, `INT_LR.dds`): 157 of 179 Kunos cars have one, against 52 mods. In `ks_mazda_miata` the `COCKPIT_LR` material uses `carpet.dds` as its detail, so a detail-tile swap already reaches it. A low-res texture with baked colour would keep the old colour at distance. That last point is inferred, not tested ([tex.txt](file:///D:/ClaudeData/tmp/interior_scan/tex.txt)).

**Interior skin overrides are normal practice, not a hack.** Skins in **295 cars (53 Kunos, 242 mods), 2,361 skins in all,** ship textures that only interior materials use. The most common names are `car_paint_roll_cage.dds` (37 cars), `carpet.dds` (20), `metal_detail_int.dds` (18), `alcnt.dds` (14) and `leather.dds` (13). Counted by skin file, txDetail is the slot overridden most (5,066 files), ahead of txDiffuse (2,846) ([skins2.py](file:///D:/ClaudeData/tmp/interior_scan/skins2.py), [skins.txt](file:///D:/ClaudeData/tmp/interior_scan/skins.txt)). The names differ from car to car, so the app has to read each car's own materials rather than keep a fixed list. Stock skins often carry different interior colours (the 991's skins ship black, white, tan and red `leather_seat.dds`), so "edit existing skin" must start from that skin's interior files.

## Same-name files by default, CSP only for shared tiling textures

**Route A, a texture under the model's own name, is the workhorse.** Any file in `skins\<skin>\` whose name matches a texture in the kn5 replaces that texture everywhere it is used. No CSP is needed, and anyone who has the skin sees it. The evidence for the rule is Kunos's own skin folders, not a written Kunos spec ([local Kunos skin scan](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/)). Because the override is global, it presumably also reaches LOD kn5 files that use the same name; that was not checked. Nor was whether names match without regard to case or file extension, so the app should keep the exact name the kn5 uses, which `skin_file_name` already does. The same global reach is the route's limit: it cannot change one part of a shared tiling texture.

**Route B, a CSP shader replacement in the skin's `ext_config.ini`, handles shared textures.** The documented recipe is a `[SHADER_REPLACEMENT_...]` section with three keys:

1. `MATERIALS = <material names>`.
2. `RESOURCE_0 = txDetail`, or `txDiffuse`.
3. `RESOURCE_FILE_0 = r4s_int_seat.dds`. "FILE refers to a texture on a disk, next to the config", which here means the skin folder.

Other documented details matter too ([CSP docs: Shader replacements](https://cup.acstuff.club/docs/csp/general/shader-replacements), [CSP wiki](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Shader-replacements)):

- `RESOURCE_` keys must be numbered explicitly; `...` is not allowed there.
- Replacements are applied once, at load.
- `MATERIALS` is preferred over `MESHES`, because with `MESHES` "each mesh … would get its own material", which costs extra draw calls.

The app already writes this exact pattern for glass: the Sunbeam `ratty_s` skin points `INT_GLASS_CENTER` at `r4s_windshield2_clear.dds` ([ratty_s ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/talbot_sunbeam_lotus_81_works_backup_v6/skins/ratty_s/ext_config.ini)). Extending it to interiors needs no new mechanism, only the right material and slot names.

**Avoid the routes that look simpler.**

- **`RESOURCE_COLOR_n = r, g, b`** makes a 1×1 solid texture. Every local example uses only 0 or 1, so nobody knows whether it takes 0–1 or 0–255 values, or what alpha it gets. That matters because txDiffuse alpha masks the detail. Writing a tiny 4×4 DDS and using `RESOURCE_FILE` gives the same result without the guesswork.
- **`ksDiffuse` and `ksAmbient`** are single brightness numbers on the Kunos shaders, not RGB tints. Every local use is one number, and CSP's own banner template treats them as brightness ([scan output](file:///D:/ClaudeData/tmp/interior_csp/scan_out.txt), [materials_interior.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/materials_interior.ini)).
- **CSP's interior templates** (`Material_Leather_v2`, `Material_InteriorPBR` with `ColorSource`/`DetailTexture`) are already included by 217 skin configs on Nik's PC. They swap the material to a `nePBR` shader, so the part changes how it shades as well as its colour. They belong in a later "upgrade material" extra, not in a colour picker.
- **A `SKINS =` key inside a skin's own config** is redundant and dangerous. The `Greenthing` skin names a different skin there, so its section never applies. It also uses colon syntax, which fails silently, as do the 13 decimal-comma typos such as `ksDiffuse,0,45` ([Greenthing ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/snp_zhonghua_zidantou_wangan_spec/skins/Greenthing/ext_config.ini)).

No skin on Nik's PC changes the hue of seats or a dash through `ext_config`. Of the 293 interior shader replacements found, the 21 in skins adjust shading, banners, LED panels or glass, never colour ([scan output](file:///D:/ClaudeData/tmp/interior_csp/scan_out.txt)). Route B for colour is therefore new ground and needs its own in-game proof.

**CM Paint Shop is a source of hints, not a method.** Its output is same-name textures, so it is route A. Its tint maths is purely multiplicative: `base * ((1 - mask.r) + gColor * mask.r) * …` ([SpecialPaintShop.fx](https://raw.githubusercontent.com/gro-ove/actools/master/AcTools.Render/Shaders/Special/SpecialPaintShop.fx)). Multiplying cannot lift black leather to white without CM's own preparation passes (`autoLevel`/`desaturate`). It is still useful. CM guesses texture roles from file names (`carpet.dds` tint, `cuciture.dds` seams, `car_paint_roll_cage.dds` solid) ([CSP docs: Paint Shop default names](https://cup.acstuff.club/docs/csp/unrelated/default-names-for-paint-shop-in-custom-showroom)). And a car author's own `ui\cm_paintshop.json` names interior textures by part: `bg_lotus_carlton` labels `leather_1.dds`, `seatbelt.dds` and `carpet.dds`, and `gt4_bmw_m4` labels `metal_detail_int.dds` as "Rollcage" ([bg_lotus_carlton cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bg_lotus_carlton/ui/cm_paintshop.json), [gt4_bmw_m4 cm_paintshop.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gt4_bmw_m4/ui/cm_paintshop.json)). Where such a file exists, its labels confirm the part names better than any dictionary.

**Online, nothing changes for other drivers unless they have the files.** Other drivers see a skin's interior only if they have the same skin, and route B also needs CSP on their PC. The third-party SkinSync tool, which passes skins between players, limits zips to 10 MB (the developer's own figure) ([SkinSync page](https://www.gtplanet.net/forum/downloads/skinsyncplugin-%C2%AE-for-assetto-corsa.7801/reviews)). The app should therefore keep interior files at their original size and never upscale a 256 px detail tile.

## An OKLab lightness remap turns black leather white without losing grain

Most AC interior textures are colourless: the Abarth and MX-5 Cup textures had a median chroma of 0–3 out of 255. That rules out the obvious tools. Hue shift, GIMP Colorize and the W3C/Photoshop "Color" blend all keep the source's brightness, because Colorize uses the pixel luminance as its lightness ([GIMP Colorize docs](https://docs.gimp.org/2.10/en/gimp-tool-colorize.html), [W3C Compositing and Blending](https://www.w3.org/TR/compositing-1/)). So black seats can never turn white or bright red with them.

The local test ran 8 methods × 5 target colours on 11 real interior textures, from abarth cloth and S14 leather to MX-5 Cup detail tiles and a Bride seat atlas ([run_tests.py](file:///D:/ClaudeData/tmp/interior_recolour/run_tests.py)). ΔE_OK is the distance between the target and the output's median colour in OKLab, ×100.

| Method | ΔE_OK, white target | ΔE_OK, red target | Problem seen |
|---|---|---|---|
| Hue shift | 50.6 | 21.0 | turns blue Alcantara "white" into olive |
| GIMP Colorize | 51.1 | 13.3 | khaki/grey instead of white |
| Multiply | 55.1 | 29.7 | cannot lift dark sources |
| Linear-light ratio | 0.1 | 3.9 | chalky white specks on dark leather and noisy Alcantara |
| OKLab remap | 0.1–0.2 | 0.4–0.5 | none in the colour; keeps the grain |

The OKLab remap reached every target within ΔE_OK 0.5 and kept the grain: high-pass correlation with the source was 0.81–0.99. OKLab was built for exactly this kind of edit, keeping perceived lightness steady while hue and chroma change ([Ottosson: OKLab](https://bottosson.github.io/posts/oklab/)).

The recipe works on the part's texels only:

1. Take the material's median OKLab colour as the reference. Use the 90th percentile of lightness instead for pure AO atlases.
2. Set each texel's lightness to the target lightness plus the texel's deviation from the reference, multiplied by a detail gain. The gain is the physical ratio (target lightness ÷ reference lightness) held between **0.6 and about 1.3**.
3. Pass the result through a soft shoulder near 0 and 1.
4. Take the target's hue and chroma, scaled down in darker texels so creases stay shadowy, and add back half of the source's own colour variation.
5. Pull out-of-gamut texels back into sRGB by reducing chroma only, keeping lightness and hue.

The gain limit matters. Dye scales albedo, so physically black-to-white would multiply the grain by about 3.4. But dark DXT textures carry quantisation noise and baked sheen that turn chalky when multiplied up; a cap of 1.8 already looked harsh by eye. The 1.2–1.3 cap is a judgement between the two tested settings, not a measured optimum, so it should sit behind a "texture strength" slider ([recolour_methods test sheets](file:///D:/ClaudeData/tmp/interior_recolour/)).

**Clamp target lightness to what real materials do.** Unity calls non-metal albedo below 0.2 too dark and above 0.8 too bright ([Unity Manual: Materials](https://docs.unity3d.com/es/2021.1/Manual/BestPracticeMakingBelievableVisuals5.html)). Studio 397's PBR tables put rubber at sRGB 53, black paint at 65, white paint at 230 and natural fabric at 158–194 ([Studio 397 PBR guide](https://docs.studio-397.com/x/EgBDAg)). The app should keep its targets between about sRGB 30–50 for black and 230–243 for white. For white it should also lower the target until the brightest grain has headroom, because a white target at sRGB 232 clipped 10–33 % of texels in the tests.

Sources that are flat or nearly flat have no grain to keep. Examples are 16×16 `MAT_*.dds` swatches, flat cage fills, and R32 `nero` leather, which has only 5 distinct levels ([extra_test.py](file:///D:/ClaudeData/tmp/interior_recolour/extra_test.py)). These are simply filled with the target colour, using the same "standard deviation under 6/255" test `recolour_wheels` already uses. The untouched normal map still lights the grain in game.

**Protect stitching and logos with clusters, computed inside the part's UV region.** Sample up to 20,000 of the part's texels and run k-means with k = 4 on (0.4·L, a, b). The biggest cluster is "the material". Each texel's recolour weight then falls off with its distance from that cluster. The distance is asymmetric: lightness counts with weight 0.12 for texels darker than the material, because AO creases are shading, and 0.5 for lighter ones, because white logos are detail.

On the R32's stitched black leather this protected **all 432 orange stitch texels**. On the Bride seat atlas it protected every coloured and white-logo texel and still recoloured 100 % of the dark creases ([mask_test.py](file:///D:/ClaudeData/tmp/interior_recolour/mask_test.py), [extra_test.py](file:///D:/ClaudeData/tmp/interior_recolour/extra_test.py)). The UV region is essential: computed over the whole Bride texture, the biggest cluster was the unused black background (58 %). One failure case is known: a black logo on a light seat reads as shading and gets recoloured. So the mask needs an on/off toggle and an overlay preview.

**Leave normal maps and txMaps alone, and choose between detail tile and atlas deliberately.** txMaps holds specular strength, gloss and reflection in its R/G/B channels, and txNormal holds the grain lighting. Neither depends on the dye ([assettocorsamods: ksPerPixelMultiMap](https://www.assettocorsamods.net/threads/ksperpixelmultimap-how-textures-are-made.3478)).

On a Kunos multimap material, recolouring the detail tile is the natural move, because it is what Kunos skins do. But it changes every material that uses that tile: Abarth's `Skin.DDS` serves the seat leather, the airbag logo and the shift boot ([dump.py](file:///D:/ClaudeData/tmp/interior_recolour/dump.py)). When only one part on a shared tile should change, the other route is to recolour that part's region of the AO atlas toward the target divided by the detail's mean. Where the detail tile is too dark for that (MX-5 Cup `leather.dds` averages 71/255), the tile must be brightened as well. That compensation rests on the unconfirmed multiply assumption, so it waits for the in-game test ([atlas.py](file:///D:/ClaudeData/tmp/interior_recolour/atlas.py)).

**Roll cages and belts are the easy parts.** Cages usually have their own texture. On mods it is often a flat swatch, for example the S14's 200² `car_paint_roll_cage.dds`, and the first skin folder of 19 ADC mods already ships one, so a plain fill is right. On Kunos cars it is an AO-only texture with its own txMaps and a scratches detail (MX-5 Cup `INT_RollBar_OCC.dds`). That gets the shading-ratio remap with txMaps and scratches left alone ([scan.py](file:///D:/ClaudeData/tmp/interior_recolour/scan.py), [atlas.py](file:///D:/ClaudeData/tmp/interior_recolour/atlas.py)). A cage drawn with `metal_detail` is body colour, and giving it its own colour needs route B.

Belts are their own material (MX-5 Cup `Cockpit_Belt.png`, tiled 8.6 times along the strap) with the hardware in separate metal materials. They often carry OMP or Sabelt labels, so the safe default is to leave them as they are.

Speed is not a problem. A 2048² texture converts to OKLab in 0.58 s, and k-means takes 0.78 s. The full-image gamut clip took 5.2 s, and running it only on out-of-gamut texels should cut that a lot (not measured). Detail tiles are 256–512 px, so they will be far faster ([recol.py](file:///D:/ClaudeData/tmp/interior_recolour/recol.py)).

## A recommended design for Ratty's4Skin

### Rows the user sees, defaulting to "keep"

The app gets a collapsible **Interior** panel. Every row starts at "Keep as the car has it", so untouched skins come out exactly as they do now. Each row offers three choices: Keep; a colour picker; or "From stock skin: …". The last choice appears only when stock skins ship different versions of that part's texture (the 991's 13 leather variants, for example). It copies the file unchanged, so it carries no recolour risk at all.

Each row also shows a status chip, for example "skin file", "needs CSP", "also changes: shift boot, airbag cover" or "not found on this car". On Kunos cars, and on any car where part words find nothing, the rows switch to surface groups ("Leather – seats, shift boot"; "Alcantara"; "Grey plastic"; "Carpet"), each listing the parts it covers. Hidden from the user, a dictionary hit or a part label from the car's own `cm_paintshop.json` takes priority over a surface group.

| Row | Choices | Default and notes |
|---|---|---|
| Seats | one colour, plus an optional insert colour when the seat has a separate fabric/alcantara material | Keep; stitching and logos protected automatically |
| Dashboard | one colour (named dash pad / structure, or the plastic surface group) | Keep; displays, gauges and decals never touched |
| Door cards | colour, or "same as seats" | Keep; door glass and outer door paint excluded |
| Roll cage | colour, or "same as body" | Keep; padding, carbon and alloy left alone |
| Carpet | colour (dark range suggested) | Keep; lightness clamped |
| Headliner | colour | Keep; roof lights and sunroof glass excluded |
| Steering wheel | grip colour (leather/alcantara rim only) | Keep; carbon, buttons, paddles, display and logos untouched |
| Belts | webbing colour | Keep; hardware never touched; label warning shown |
| Inner body panels | as now / body colour / own colour (own colour needs CSP) | "As now" keeps today's output, including the white `metal_detail` effect |

Everything else is automatic. That covers detection, choosing the colour slot and the write route, the UV-region and stitch masks, the lightness clamps, the low-res cockpit copy, sharing warnings, and keeping each file's size and alpha.

An "Advanced" fold holds three controls: the texture-strength slider (gain cap 0.6–1.3, default 1.2), the "protect details" toggle, and the raw material list, where any material can be moved to another row or excluded.

There are three previews:

1. **Before/after swatches for each row.** A crop of the part's atlas region, or a 3×3 repeat of its detail tile, with the protection mask as an overlay.
2. **An interior top view.** The app's existing orthographic renderer (`render_view`) draws only the interior meshes, with roof, glass and body hidden. This is new, but the pieces already exist.
3. **One log line per part.** For example: "Seats: leather_seat.dds (txDetail, 512², also INT_Skin_Shift) → skin file".

### Rules for picking the write route per part

The rules run in order, and the first one that fits decides.

| # | Condition | Action |
|---|---|---|
| 1 | Material is glass, display/LCD/gauge, emissive, alpha-blended, ksWindscreen, decal/stitch/logo, carbon, metal/alu/chrome or rubber | Never write |
| 2 | Choose the colour slot | txDetail when `useDetail` is on, the detail is not `null.dds`, and txDiffuse is neutral with mean alpha near 0 (threshold to tune); otherwise txDiffuse |
| 3 | Slot texture is a `metal_detail*` that also serves the body paint | "Body colour" or "own colour" through route B only; never overwrite it by name |
| 4 | Every material using the texture, in any slot, is interior and in this row (or the user accepted the listed sharers) | Route A. Tile or swatch (UV span over about 1.05, or texture of 128² or less): recolour the whole texture. Atlas: recolour only the part's texels, plus 2 px into texels no other part claims |
| 5 | Atlas also used by outside or other-row parts whose texels do not overlap this part | Still route A with the region mask: the other parts' texels stay untouched |
| 6 | Tiling texture shared with outside parts or with a row that wants another colour | Route B: write `r4s_int_<part>.dds`, then a `SHADER_REPLACEMENT` with `MATERIALS` = the owning materials and `RESOURCE_FILE` in the colour slot. Use `MESHES` only when the material itself is shared, and warn that LOD mesh names may differ |
| 7 | Car has a low-res cockpit texture with baked colour | Recolour its matching region; until 3D mapping exists, warn that the old colour shows at distance |
| 8 | Protected car (materials unreadable) | Offer only "From stock skin" copies, and recolouring of interior-only tiles and swatches the stock skins already ship; nothing else |

All route-B sections go through the existing `merge_ini` under a "; Ratty's4Skin interior" comment, so that editing a skin later replaces them instead of piling them up. The app never writes a `SKINS =` key, never writes into the kn5 or the car's `extension` folder, and uses only comma `PROP` syntax.

### Limits and risks

The biggest uncertainty is that no source confirms the shader formula. The working model, "visible colour ≈ AO × detail wherever diffuse alpha is low", rests on decoded textures and on what skins override, not on Kunos or CSP code. If the real formula has a ×2 factor or a lerp, detail-tile targets will come out too light or too dark. Three other behaviours are unverified:

1. The value range of `RESOURCE_COLOR`, which the design avoids.
2. Which config wins when a skin's `ext_config.ini` and the car's own config both target the same material.
3. Whether a route-B replacement on one material really leaves the other users of the texture on the original.

There are also known risks:

- A shared detail tile spreads by design: seats and shift boot change together. The status chip has to say so before the user commits.
- The stitch mask fails on dark logos on light seats.
- Cars with generic mesh names fall back to surface groups, or to nothing.
- The 39 protected and scrambled kn5 files on Nik's PC can't be read at all.
- The existing white `metal_detail` behaviour on Kunos cars may already be greying inner panels in app-made skins. Nik should decide whether "Inner body panels: body colour" becomes the default later. Changing it now would break the rule that working cars stay unchanged.
- Interior files only show for other drivers who have the skin, and route B also needs CSP on their side.

### Phased build plan

| Phase | Scope | Done when |
|---|---|---|
| 0 – Prove it in game | Hand-made test skins on `ks_mazda_mx5_cup` (tinted `leather.dds` and `alcnt.dds`; a route-B `RESOURCE_FILE` on one material of a shared tile; a 0–1 vs 0–255 `RESOURCE_COLOR` pair; low-res cockpit seen from outside), on `adc_nissan_s14_kouki__420` (cage swatch fill; route B on `leather_dark.dds` for the dash only), and on `abarth500` (`TEssuto.dds` seat-only through route B) | Nik confirms in game which formula holds, that route B separates shared users, and which config wins |
| 1 – Read-only catalogue | Classifier (markers, dictionary, exclusions, surface groups, `cm_paintshop.json` hints), colour-slot finder, texture-user graph, routes chosen but nothing written; shown in the log and the "Report this car" zip | Catalogue looks right on Nik's own cars and the cars above; `same_output_cars.py` identical |
| 2 – Route A | OKLab remap, k-means protection, UV-region atlas painting, swatch fills, detail tiles with alpha kept, "From stock skin" choices, row UI with status chips, swatch previews, interior choices saved in `r4s_design.json` | Seats, carpet and cage recolour correctly on the Phase 0 cars and Nik's cars; panel left untouched gives identical output |
| 3 – Route B | `r4s_int_*.dds` plus `SHADER_REPLACEMENT` for shared tiling textures; "Inner body panels: own colour"; "needs CSP" labelling | Shared-texture parts change alone in game; vanilla AC still shows the stock interior without errors |
| 4 – Polish | Interior top-view render, low-res cockpit baked-atlas sync by 3D nearest part, the protected-car fallback, optional CSP PBR "upgrade material" | Each feature confirmed by Nik in game, one car at a time |

Each phase should be tested on the cars Nik actually drives plus the named test cars, not on random batches, and an installer should be built only when a phase is worth shipping.

## Conclusion

Interior colour is mostly a bookkeeping problem. The colour maths is settled: the OKLab remap and the clustered protection mask worked on every real texture tested. The hard part is knowing, for each texture, which slot carries the colour and who else uses it. Once the app builds that texture-user graph, the write route follows almost mechanically, and route A covers most cases. That is plausible because Kunos and hundreds of mod skins already ship interior textures this way on Nik's PC. CSP is a narrow escape hatch for shared tiling textures, not the base of the feature.

The research also turned up something about the app as it is today. The white `metal_detail` it writes for Kunos-style paint very likely already reaches cockpit metal and inner doors. The interior work is the natural place to give Nik that choice explicitly. The open questions (the detail-blend formula, whether route B can separate shared users, and which config wins) can each be answered in a few minutes in game on the MX-5 Cup. Answering them first decides how much of Phase 2's compensation maths is needed at all.
