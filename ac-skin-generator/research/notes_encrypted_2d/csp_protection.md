# CSP kn5 model protection (encryption): what it hides, what stays readable, and legitimate livery workflows

Scope note: this covers only what is visible or readable without circumventing the protection, plus the stated policy and normal livery workflows. Nothing here describes how the protection works inside or how to undo it, and none of that was looked into. Local checks were read-only, run on this PC's Assetto Corsa install (CSP 0.3.1-preview2, build 4295, from `extension\config\data_manifest.ini`), with scratch scripts in `D:\ClaudeData\tmp\csp_prot\`. Date of research: 2026-11-17.

## Q1. What does CSP protection change in a kn5, and what stays plain?

### Takeaway
The official docs only say that the kn5 is "protected" and only CSP (or, if the author allows it, CM's Custom Showroom) can load it. They do not list which fields are encrypted. Read-only checks on this PC show what a plain reader actually gets from CSP-protected car kn5s:
- **Plain:** the file header, material names, shader names, material properties and texture-slot bindings, node and mesh names, and vertex positions and normals (car-sized extents, unit-length normals).
- **Not usable:** the UV channel is scrambled, with values up to about ±280 instead of 0..1.
- **Placeholders only:** every embedded texture is a 70-byte 1×1 PNG.

### Cited Findings
- CSP can encrypt car and track kn5 files "to protect models from being edited or stolen". Encrypted models only work in AC with CSP installed, or optionally in Content Manager's Custom Showroom. In the original AC they display incorrectly. — [CUP docs: kn5 encryption](https://cup.acstuff.club/docs/csp/misc/kn5-encryption); [CSP wiki: Misc – KN5 encryption](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Misc-%E2%80%93-KN5-encryption) (last edited 11 May 2021 by Ilja Jusupov, 16 revisions)
- The docs do not say whether geometry, UVs, names or textures are each encrypted. They say only that the model is protected. The encrypter also applies lossless compression to textures, so encrypted files can be smaller than the originals. — [CSP wiki: KN5 encryption](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Misc-%E2%80%93-KN5-encryption); [CUP docs](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- Process:
  - The encrypter writes a new `*_encrypted.kn5` beside the original, which the author swaps in by hand.
  - "There is no way to decrypt a model", so authors must keep backups.
  - Limits: no uppercase letters in folder names, no duplicate mesh names, and mesh and texture names of 200 characters or fewer.
  - Encrypter versions v1 to v3 are listed on the wiki.
  — [CUP docs](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- There are two modes:
  - `kn5enc_…exe` protects the model only.
  - `kn5enc_…_acdchecksum.exe` ties the model to `data.acd`. The model stops working if the data is changed. The data itself is "not encrypted", so it stays visible and copyable, only protected against changes.
  — [CUP docs](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- Users report what this looks like in practice. After editing an encrypted mod's `data.acd`, the game showed "failed to decrypt model" and drew the car as "blue polygon crystals" (Jan 2023, CSP 0.1.73–0.1.79). Some "softly encrypted" mods still allowed data edits. — [Steam discussion, Jan–Dec 2023](https://steamcommunity.com/app/244210/discussions/0/3759977302532019084)
- Newer encryptors exist, described in an archive page on older encryptors:
  - v3: Ninja Ripper protection "can be circumvented".
  - v5: better against Ninja Ripper, needs LODs, and has a server lock.
  - v6: no LODs needed.
  - v9: built for CSP 0.3.0; needs Steam and Google sign-in.
  - The author: encryption without a server "can't hold for long anymore". The page does not say which data any version covers.
  — [CUP: about old encryption](https://cup.acstuff.club/docs/about-old-encryption)
- The author admits there are limits: "anybody could still get original model with textures" by intercepting GPU data, and the author is "not an expert". — [CUP docs](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- **Local (read-only), CSP-protected cars on this PC:**
  - **Header:** `cf_ferrari_296_gt3`, `gt4_mclaren_570s`, `gt4_alpine_a110` and `gt4_bmw_m4` each start with the normal `sc6969` magic and version 6.
  - **Plain-readable parts:** the material table (for example 51 materials on the 296: `EXT_Wiper`/`ksPerPixelReflection`, `EXT_Mechanics`/`ksPerPixelMultiMap`, `EXT_Disc`/`ksBrakeDisc`…), sampler bindings and node/mesh names (`WIPER_3`, `SUSP_Caliper_LF_SUB1`…).
  - **Embedded textures:** the kn5 holds the full texture list by name (82 to 93 entries), but every entry is a 70-byte, 1×1-pixel PNG placeholder. The texture data totals about 0.01 MB against kn5 sizes of 31–39 MB. For comparison, unprotected `ks_bmw_m4_gt3` has 118.8 MB of real embedded DDS and `ks_maserati_alfieri` 32.6 MB.
  — local scripts `D:\ClaudeData\tmp\csp_prot\peek.py`, `sizes.py`
- **Local (read-only), geometry as a plain reader sees it:**
  - **Positions:** a car-sized bounding box (296 GT3: x ±1.22 m, y −0.03..1.58 m, z −2.28..2.50 m).
  - **Normals:** 100 % unit length.
  - **UVs:** they range from −278 to +279 in u and −43 to +44 in v (570S: about ±51 / ±46), where a normal car has roughly 0..1. Unprotected `ks_maserati_alfieri`: u −1.5..3.6.
  - **Small triangles:** 88–90 % of triangles under 3 cm have UV corners more than a quarter of the texture apart. Unprotected cars: 0–1 %.
  — local `D:\ClaudeData\tmp\csp_prot\geom.py`, `sizes.py`; detection function `scrambled_uv` in `D:\Claude\Claude-\ac-skin-generator\skingen.py` (lines 463–473)
- **Local, a second group of kn5s:** 38 car kn5s cannot be parsed by a plain reader at all, even at the texture table.
  - All 29 `rss_*` cars, 5 `gravygarage_*` cars, and 4 others.
  - Some of the 38 are just empty 0-byte files, meaning broken installs.
  - The RSS and Gravygarage files still start with `sc6969` and version 6.
  - The app already reports these as "protected (locked)" through its parse-error path (`kn5.py` line 45).
  — local `D:\ClaudeData\tmp\csp_prot\scan.py`; [kn5.py](D:\Claude\Claude-\ac-skin-generator\kn5.py)
- CSP's own config docs treat "protected meshes" as a category. The Model-replacements `HIDE` key takes "meshes or nodes to hide (no protected meshes)". — [CSP wiki: Model replacements](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/General-%E2%80%93-Model-replacements) (quoted in the earlier note `D:\Claude\Claude-\ac-skin-generator\research_notes\CSP window stickers on shared glass\livery_maker_practice.md`; not re-fetched here)

### Inferences
- For a livery tool, the decisive change is that the UV channel can't be used, together with the embedded textures being placeholders. Names, material and shader setup, sampler bindings and rough geometry are still visible, so a tool can tell which texture file is the paint (for example `EXT_Carpaint_*` materials sample `EXT_Skin_Colour.dds`). It cannot place anything on the 3D car from the kn5.
- There are at least two visible protection states on this PC:
  - (a) The kn5 parses, but has scrambled UVs and placeholder textures: 153 cars, consistent with the current CSP encrypter.
  - (b) The kn5 can't be parsed past the header: the RSS and Gravygarage cars. These may be the newer server-locked encryptors (v5 to v9), but nothing here confirms that.
- Detection without circumvention can rely on what is visible:
  - (1) The texture table holds only tiny placeholders (all entries ≤ 100 bytes). This is a cheap check and needs no geometry.
  - (2) The `scrambled_uv` share is above 0.5.
  - (3) The plain reader fails on a file that starts with `sc6969` and is not empty.
  - Check (1) agreed with check (2) on all 4 cars tested.

### Gaps
- No official document lists which kn5 fields the encrypter covers (positions? normals? names?). The visible-state description above is empirical, from 4 cars checked in depth and 153 by texture table, and covers only the encrypter versions present on this PC. The internals were deliberately not investigated.
- It was not checked whether the visible vertex positions are the true geometry. They are car-sized, but the docs say the model renders wrongly without CSP.
- Whether group (b) is CSP's newer encryptor or another tool is unknown.

## Q2. Is the body texture of a protected car still a normal image showing the real UV layout?

### Takeaway
Yes for textures in the **skins folders**, no for the textures **inside the protected kn5**.
- **Skins folders:** `skins\<skin>\*.dds` files are ordinary DDS images, not encrypted, and the livery painted in them follows the real UV layout that the game uses.
- **Inside the kn5:** the embedded copies are 1×1 placeholders. A livery app therefore has to take the base or stock body texture from a skin folder (or a template the maker shipped), never from the kn5.

### Cited Findings
- **Local, `cf_ferrari_296_gt3`:**
  - The skin `2023_GTWC_14_Emil Frey Racing` holds `EXT_Skin_Colour.dds` (4096×4096, 89.5 MB uncompressed DDS), `EXT_Skin_Map.dds` (4096², 89.5 MB), `EXT_Banner_Colour.dds` (2048×512, DXT5), tyre textures and `ext_config.ini`.
  - Opened with Pillow, `EXT_Skin_Colour.dds` is a normal livery sheet: body panels laid out flat with sponsor logos, the number 14 and team name, the same layout as the maker's wireframe.
  — local `D:\ClaudeData\tmp\csp_prot\skins.py`; preview `D:\ClaudeData\tmp\csp_prot\cf_ferrari_296_gt3_EXT_Skin_Colour.dds.png`
- **Local, `gt4_mclaren_570s`:** every skin carries `EXT_BODY_AO.dds`, a readable 4096² DX10 ambient-occlusion map, plus `metal_detail.dds`. — local `skins.py`
- The app's own planning note already assumes "the stock body texture is readable even when the model's UVs are scrambled". The check above shows this holds for the **skin-folder** texture only, because the kn5-embedded copies are placeholders. — [TODO.md item 2](D:\Claude\Claude-\ac-skin-generator\TODO.md)
- A community guide warns that for modded cars you should check whether the creator included a template, and that "some mods haven't been UV mapped in a way that allows for making skins". This is about UV design, not encryption. — [Cimmerian AC conversion guide](https://cimmerian.gitbook.io/assetto-corsa-conversion/changing-the-car-look/making-the-car-look-good) (search snippet)

### Inferences
- AC skins work by placing same-named texture files in `skins\<name>\`, which override the kn5's textures. Protected cars still need real, plain textures there to show a livery, so the skin-folder textures are the intended, open interface for painters.
- A 2D "template mode" can legitimately:
  - start from a stock skin's body texture, or from the maker's template or AO;
  - paint in texture space;
  - write same-named files into a new skin folder.
  None of this needs the kn5's UVs.
- Without UVs, the tool cannot know which 3D panel a texel belongs to, except from 2D cues: the maker's wireframe, the AO map, the islands visible in an existing livery, and the alpha in `livery.png`.

### Gaps
- Not checked across all 153 cars that every protected car ships a full-size body texture in at least one skin folder. Some (for example traffic cars) may have none.

## Q3. What do the CSP docs and author, and mod makers, say about protection and about painting skins for protected cars?

### Takeaway
The CSP author (Ilja Jusupov / x4fab) frames encryption as a reluctant, imperfect anti-theft measure:
- Don't encrypt Kunos or others' content without permission.
- Keep encrypters private.
- Reconsider encrypting at all.
- Disputes go through the author.

There is no official CSP guidance on skins or liveries for encrypted cars. Nothing found forbids reading the plain skin-folder textures, which is simply the normal skinning workflow. Painters report the practical cost: no AO or UV template unless the maker ships one.

### Cited Findings
- **Policy:**
  - "Do not encrypt Kunos or someone else's content without permission". It may break the files or get them decrypted, and CSP may show a warning about stolen content.
  - The author asks people to reconsider encryption and values AC's openness, including for learning how cars are built.
  - Encryption is seen as justified mainly for models likely to attract re-releasers.
  — [CUP docs](https://cup.acstuff.club/docs/csp/misc/kn5-encryption); [CSP wiki](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Misc-%E2%80%93-KN5-encryption)
- **Disputes:** for stolen content that someone encrypted, the author offers to mediate, and may in some cases provide a special tool tied to that offender's key. This is a dispute-resolution path, not a general one. — [CSP wiki](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Misc-%E2%80%93-KN5-encryption)
- **Keep encrypters private:** sharing one "is like releasing all your content decrypted". — [CSP wiki](https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki/Misc-%E2%80%93-KN5-encryption)
- **Custom Showroom:**
  - Encrypted cars don't work there by default. Support can be requested, but the author warns it may make models easier to steal.
  - The suggested alternative is a separate, deliberately simplified, unencrypted model referenced from `lods.ini` (`[LOD_HR]`) for CM.
  — [CUP docs](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)
- **CM changelog:** "Custom Showroom no longer opens encrypted models it can't decrypt" (build 0.8.2686.39678). An older build (0.8.2149) supported more encrypted kn5s. — [CM detailed changelog](https://acstuff.club/f/d/10-content-manager-detailed-changelog/273) (from a search snippet only; the forum page failed to load, so not verified first-hand)
- **Painters on GTPlanet** (search snippets only; GTPlanet returned 403, so posters and dates are unverified):
  - A modder making liveries for an encrypted car said they worked "without the proper AO mapping" because it is encrypted, so the liveries would lack AO.
  - Another asked for an unencrypted copy of a paid mod so the AO mapping could be shared, or whether AO could be applied through `ext_config`.
  — [GTPlanet AC mods thread, post 14594330](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14594330), [post 14594463](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14594463)
- **Paid encrypted releases:** a paid encrypted GR86 drift car is sold "ONLY as encrypted version (you are not able to modify 3d model)". — [Payhip listing](https://payhip.com/b/x8khi) (search snippet)
- **A maker's change of mind:** a Nissan 180SX mod that was released encrypted was later re-released "Unencrypted, PSD files included". — [Gumroad listing](https://h17feb4.gumroad.com/l/vlyqu) (search snippet)
- **Community scepticism:** some modders see little point in encrypting, because models can still be ripped from the GPU. — [assettocorsamods.net thread](https://assettocorsamods.net/threads/how-can-i-encrypt-a-car-or-circuit-thanks.2914/) (search snippet)
- **CSP's in-game Paintshop app** (CSP ≥ 0.1.77) paints directly on the car in game: Shift-click the exterior, paint, then export a texture. On export it uses the original texture as an AO map. The README says nothing about encrypted cars. — [ac-custom-shaders-patch/app-paintshop](https://github.com/ac-custom-shaders-patch/app-paintshop)

### Inferences
- **Reading textures only:** the protection's stated target is editing and stealing the **model** (and, optionally, tampering with physics). A tool that reads only the plain skin-folder textures and the visible material and texture names, and writes new skin files, does the same as any human livery painter. That sits within the normal, intended use. Reading or reconstructing the scrambled UVs would cut against both the stated purpose and the author's request.
- **Painting in game:** because the game itself (with CSP) renders protected cars correctly, in-game tools such as CSP Paintshop are a sanctioned route to 3D-placed paint on protected cars. Whether Paintshop works on encrypted cars was not confirmed.

### Gaps
- No statement was found from the CSP author or CUP specifically about liveries or skin templates for encrypted cars, or about third-party tools reading skin textures. The CSP Discord was not searchable.
- The CM changelog wording and build number come only from a search snippet.
- The GTPlanet quotes could not be checked first-hand (HTTP 403). Treat them as anecdotal.
- No 2025–2026 changes to the encrypter's documentation were found. The wiki was last edited in 2021, and the archive page mentions v9 for CSP 0.3.0.

## Q4. How do modders ship skin templates (PSD, AO, wireframe) for protected cars?

### Takeaway
Makers of protected cars usually put the painting aids **inside the skins folder** as plain files:
- a "Template" skin with a PSD/XCF of the body texture;
- a wireframe PNG of the UV layout;
- a PNG or DDS AO map;
- a working `ext_config.ini`;
- sometimes a PDF guide.

On this PC, 100 of the 153 CSP-protected cars ship some template-like file. The remainder are mostly traffic cars, karts and street or drift cars with none.

### Cited Findings
- **Local, `cf_ferrari_296_gt3` (protected, scrambled_uv 0.88):**
  - It ships skins `Template`, `Template Endu`, `Template GTD` and `Template GTDPro`, each containing `EXT_Skin_Colour.psd`, `.xcf`, `.png` and `.dds`, `Wireframe.png` (4096² RGBA, the UV layout drawn in green lines), `livery.png`, `preview.jpg`, an `ext_config.ini`, a font zip and "Alpha for carbon.png".
  - It also ships a "Ferrari 296 Skin Documentation.pdf". The PDF explains that aero packages are switched by Model replacements in the skin's `ext_config.ini`, and that "I created a template skin for each body kit… a working ext_config.ini… a png AO map… a banner texture". It lists `[INCLUDE:cf/ferrari_296/…ini]` lines per spec, and notes that an `EXT_Numberplate_Emissive.dds` uses the "same mapping as normal Skin texture".
  — local files under `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\cf_ferrari_296_gt3\`; wireframe thumbnail `D:\ClaudeData\tmp\csp_prot\wire_296.png`
- **Local scan of the 153 cars whose kn5 holds only placeholder textures** (`scan.py`):
  - Template-like files: 100 have PSD/XCF, wireframe, AO, a template folder/file or a skin document.
  - ADC drift cars (`adc_*`): typically AO plus a template folder and often PSD/XCF.
  - GT4 pack: per-skin AO such as `EXT_BODY_AO.dds`, some with PSD.
  - `supercars_gen3_*`: AO plus wireframe plus PSD.
  - `fsr_*` BTCC: PSD and template folders.
  - None: `nohesi_traffic_*`, `traffic_aegis_*`, karts, and several street cars.
  - Caveat: the "AO" hits include AO textures that the car's materials use as working textures, not only templates.
- **Base-game templates:** official Kunos templates live in `sdk\dev\skin_templates\`. For mods, painters rely on templates from the mod maker or extract textures with CM or kn5 tools. That route is closed for protected kn5s, whose embedded textures are placeholders. — [OverTake skinning tutorial](https://overtake.gg/threads/skinning-assetto-corsa-cars-from-nothing-using-mudbox-and-photoshop.147080) (search snippet); local finding above
- **Workarounds for missing previews:** a mod exists for "when the model is encrypted and the previews don't match up", which turns the Kunos preview into a photo-mode location. — [OverTake download 59498](https://www.overtake.gg/downloads/preview-as-a-photomode-location.59498/) (search snippet; page returned 403)
- **CM's AO tool:** a CM user generated AO in CM's showroom and used it as a template. Whether CM can generate AO for encrypted cars was not shown. Given the changelog line above, Custom Showroom refuses encrypted models it can't decrypt. — [GTPlanet thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/page-4794) (search snippet)

### Inferences
- For protected cars, the legitimate template sources, in order of quality:
  1. a template skin the maker shipped (PSD/XCF + wireframe + AO);
  2. an AO map in a skin folder;
  3. the body texture of an existing stock skin (its painted islands show the layout);
  4. `livery.png` / `preview.jpg` for colour picking.
  An app can look for these by name: `skins\Template*`, `*wire*`, `*_AO*`, `*.psd`/`*.xcf`, `*.pdf`.
- CM's own AO and UV-template generation needs the model loaded in Custom Showroom. For encrypted cars this is very likely unavailable, which is presumably why makers ship AO and wireframes themselves. This is inferred, not confirmed by CM documentation.
- Skin-level `ext_config.ini` files (Model replacements, `[INCLUDE:…]`) are plain text and maker-supplied. A livery app should copy them from the template or stock skin it starts from, so that body-kit switches still work.

### Gaps
- No general repository or standard for templates of encrypted cars was found. It is up to each maker.
- This was not cross-checked against the cars the user actually races (the scan is install-wide).

## Q5 (from the objective). How do tools detect a protected model, and what can a third-party livery app legitimately use?

### Takeaway
Detection needs only visible structure:
- the texture table holds only tiny placeholders;
- the UVs fail a sanity check (`scrambled_uv` > 0.5);
- or a non-empty `sc6969` file won't parse.

The legitimate working set is everything that is plain:
- skin-folder textures (DDS/PNG), maker templates, AO and wireframes, `livery.png`/`preview.jpg`;
- kn5 material, shader, sampler and texture **names** (to know which file is the paint);
- `ext_config.ini` and other CSP config text;
- `ui_skin.json`.

Off-limits: the scrambled UVs, the kn5-embedded texture data, and anything that would reconstruct them.

### Cited Findings
- **The app's current detection:** `scrambled_uv(meshes)` measures the share of triangles under 3 cm whose UV corners are more than 0.25 apart (about 0 on honest cars, 0.8–0.95 on protected ones). The app then offers a plain colour only and "never tries to undo the protection". `kn5.py` turns parse failures into a "protected (locked)" message. — [skingen.py](D:\Claude\Claude-\ac-skin-generator\skingen.py) lines 463–473, 3407–3414; [kn5.py](D:\Claude\Claude-\ac-skin-generator\kn5.py) line 45; [README.md](D:\Claude\Claude-\ac-skin-generator\README.md) lines 211–214
- **Scale on this PC:** 37 of 233 GT3/GT4/touring cars (app check, 12 Nov). Install-wide: 153 of 846 car folders that have a kn5 hold only placeholder textures, and 38 more can't be parsed. — [README.md](D:\Claude\Claude-\ac-skin-generator\README.md); local `scan.py`
- **What is plain:** material and texture names, shader and sampler bindings, and skin-folder DDS files (see Q1 and Q2 local findings).
- **The data.acd mode** leaves data readable and copyable, protected only against changes. Writing new skin folders does not touch `data.acd` or the kn5. — [CUP docs](https://cup.acstuff.club/docs/csp/misc/kn5-encryption)

### Inferences
- **A cheaper detector:** a placeholder-texture check (all kn5 texture entries ≤ 100 bytes, usually 1×1 PNG) is faster than parsing geometry. It also explains directly why kn5-embedded textures can't serve as the base image.
- **Safe-design rules for the app:**
  - Read only the plain kn5 tables (names) and the skin folders.
  - Never read the meshes' UVs for protected cars except to detect protection.
  - Never write to the kn5 or `data.acd`.
  - Ship only new skin folders.
  This matches both the CSP author's stated intent and existing community practice.

### Gaps
- No official CSP or CM statement explicitly blesses or forbids third-party tools reading skin textures or kn5 names. The conclusion that this is acceptable is inferred from the stated purpose (protecting models and physics) and from normal skinning practice.
