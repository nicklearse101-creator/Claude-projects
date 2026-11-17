# 2D livery paint templates and output formats in the major sims (iRacing, ACC, rFactor 2 / LMU, AMS2, AC)

Research date: 17 Nov 2026. Several official pages could not be fetched (LMU support site, Reiza forum thread pages beyond post 1, overtake.gg threads and simracingsetup.com refused automated access with 403 or bot checks), so some facts come from search-engine summaries of those pages. Those are marked "(search summary)". Dates are given where the source showed one; anything from before 2025 is flagged as older.

## iRacing: file naming, size, spec maps, template layers, Trading Paints, folders

### Takeaway
An iRacing custom paint is a flat TGA named `car_<customerID>.tga` (or `car_num_<customerID>.tga` if you paint your own numbers), at 2048x2048 (1024 also accepted), placed in `Documents\iRacing\paint\<car folder>\`. It can have an optional PBR spec map `car_spec_<customerID>.tga` (R = metallic, G = roughness, B = clear coat, A = specular mask) that the sim turns into a `.mip`. iRacing never sends custom paints to other drivers. That is done by the third-party Trading Paints downloader.

### Cited Findings
- **Folder:** a custom TGA goes in `[documents]\iRacing\paint\<your car>\`. The sim uses it in place of its built-in paint shop output, and a tooltip in the paint shop shows the right folder for the chosen car. — [iRacing Custom Paint Policy / support article](https://support.iracing.com/support/solutions/articles/31000133480) (search summary)
- **Naming:** base paint `car_<customerID>.tga`. Team paints use `car_team_<teamID>.tga`, `car_num_team_<teamID>.tga` and `car_spec_team_<teamID>.tga`. — [iRacing 2015 custom paint schemes PDF](https://ir-core-sites.iracing.com/members/pdfs/2015_01_20_custom_paint_schemes.pdf) (older, 2015; search summary) and [Trading Paints help](https://help.tradingpaints.com/painting/how-do-i-create-a-spec-map-file-for-use-in-iracing/) (search summary)
- **Numbers:** `car_<id>.tga` is a "Sim-Stamped Number" paint, where iRacing draws the number on top. `car_num_<id>.tga` is a "Custom Number" paint: the sim uses it instead of `car_<id>.tga` and stamps no number, so the painter draws the numbers themselves. — [iRacing 2015 PDF](https://ir-core-sites.iracing.com/members/pdfs/2015_01_20_custom_paint_schemes.pdf) (older; search summary); [Trading Paints help](https://help.tradingpaints.com/painting/how-do-i-create-a-spec-map-file-for-use-in-iracing/) (search summary)
- **Resolution:** "The cars can be 1024 x 1024 or 2048 x 2048 pixels in size. The suits and helmets are 512 x 512. If they are the wrong size they are ignored." — [iRacing 2015 PDF](https://ir-core-sites.iracing.com/members/pdfs/2015_01_20_custom_paint_schemes.pdf) (OLDER, Jan 2015. Helmet and suit sizes in particular may have changed since.)
- **Spec map channels (PBR):** Red = Metallic (white metallic, black non-metallic). Green = Roughness (white very rough, black smooth and very reflective). Blue = Clear Coat ("unedited and we leave it white typically"). Alpha = Specular Mask, which sets how much of the metallic/roughness effect shows and is used to turn off environment effects on things like holes in panels. It is not used on every car. — [iRacing "Paint Textures" / Custom Spec Maps](https://www.iracing.com/painttextures/)
- **Spec map file:** export as a 24-bit TGA, or 32-bit if it has alpha, named `car_spec_<account number>.tga`. In normal use the sim reads `.mip` files. For the player car only, it checks for a matching `.tga`, and if the TGA is newer than the `.mip` (or no `.mip` exists) it builds the `.mip` in the same folder. Custom spec maps are traded as `.mip` on Trading Paints because they load faster. — [iRacing Paint Textures](https://www.iracing.com/painttextures/)
- Once the final MIP exists, remove the spec TGA, or the sim rebuilds the MIP every launch. Spec maps apply only to the base car paint, not to decal-layer TGAs. — [Trading Paints help: spec map](https://help.tradingpaints.com/painting/how-do-i-create-a-spec-map-file-for-use-in-iracing/) (search summary)
- Custom spec maps must be switched on in iRacing's graphics options. — [Trading Paints help: enabling custom spec maps](https://help.tradingpaints.com/downloader/enabling-custom-spec-maps-in-your-iracing-graphics-options) (page title in search results)
- On some cars, default logos show faintly "ghosted" under a custom paint. This happens on vehicles whose default paints contain a spec map. — [Trading Paints help: ghosted logos](https://help.tradingpaints.com/painting/on-some-vehicles-logos-appear-faintly-ghosted-underneath-my-custom-paint-how-can-i-prevent-this/) (page title / search summary)
- **Template PSD:** each car's Photoshop template includes a "custom spec map" group to build your own spec map from. iRacing advises routing the metallic and roughness layers into channels with layer-group blending options rather than pasting greyscale into channels, which can cause noise. Stamped items take the material type of the spec-map area under them. — [iRacing Paint Textures](https://www.iracing.com/painttextures/)
- **Template guide layers:** a "Turn Off Before Exporting TGA" group holds painting guides, masks and mandatory stamped layers. It must be hidden before export, or those items can show up on the paint if iRacing later tweaks the artwork. iRacing's older guide says the stamped logos in that group "are stamped on by the simulator and therefore they should be turned off before saving the final tga". — [Trading Paints: Paint Builder painting guides](https://help.tradingpaints.com/paint-builder/using-paint-builders-painting-guides/) (search summary); [iRacing 2015 PDF](https://ir-core-sites.iracing.com/members/pdfs/2015_01_20_custom_paint_schemes.pdf) (older)
- **Wireframe layer:** shows the shapes and curvature of body panels. It is hidden by default and is usually white with green lines marking the edge of the car. — [Trading Paints: Paint Builder painting guides](https://help.tradingpaints.com/paint-builder/using-paint-builders-painting-guides/) (search summary)
- Some iRacing PSD templates include an alpha channel. If it is saved out, parts or all of the custom paint can disappear in the sim. — Trading Paints help, likely the [all-black / missing paint troubleshooting page](https://help.tradingpaints.com/downloader/troubleshooting-all-black-custom-paints/) (search summary; the exact page was not confirmed)
- **Trading Paints Paint Builder** (web editor) has an option, on by default, that shows "Car Parts" layers such as lights and stamped logos above the user's artwork. If it is unchecked, the artwork goes on top of the iRacing-stamped template items. — [Trading Paints: changing finish / Paint Builder](https://help.tradingpaints.com/paint-builder/changing-the-finish-of-paint-builder-layers/) (search summary); Paint Builder also lets you set a per-layer finish, which builds the spec map — [Trading Paints: changing the finish of Paint Builder layers](https://help.tradingpaints.com/paint-builder/changing-the-finish-of-paint-builder-layers/) (page title)
- Trading Paints hosts car templates — [tradingpaints.com/cartemplates](https://tradingpaints.com/cartemplates). Template art changes over time, for example the 2024 NASCAR art update and the Gen 4 stock cars — [Trading Paints blog: 2024 NASCAR art update](https://blog.tradingpaints.com/tips-for-iracings-2024-nascar-art-update/), [Gen 4 painting considerations](https://blog.tradingpaints.com/painting-considerations-for-iracings-new-gen-4-stock-cars/)
- iRacing publishes a Custom Paint Policy that painters must follow, covering content rules for custom cars. — [iRacing support](https://support.iracing.com/support/solutions/articles/31000133480)

### Inferences
- An app's output for iRacing would be: `car_<id>.tga` or `car_num_<id>.tga`, 2048x2048, 24-bit RGB with no alpha unless the paint really needs it (an accidental alpha channel is a known way to make paints vanish), plus an optional `car_spec_<id>.tga` with the channel packing R metallic / G roughness / B clear coat (white) / A mask.
- The customer ID is part of the file name, so the app must ask for it (or a team ID).
- Sharing online means Trading Paints (upload plus their Downloader app). The sim itself shows a custom TGA only to the person who has it in their paint folder.

### Gaps
- Current (2026) helmet and suit sizes, and whether any cars now take 4096 paints: only the 2015 PDF states sizes. Not verified for 2026.
- Decal-layer TGA naming (Trading Paints "decal layer") was not fully documented. See [what is a decal layer](https://help.tradingpaints.com/painting/what-is-a-decal-layer/) (not fetched).
- Whether the sim has a documented hot-reload key for paints. No source was found.
- Trading Paints' API or upload format for third-party apps. Not researched or found.

## ACC: Customs folders, decals.png / sponsors.png and their json, sizes, layer meaning, car json

### Takeaway
An ACC custom livery is two optional transparent PNG layers, `decals.png` (max 2048x2048) and `sponsors.png` (max 4096x4096), each with a small json of PBR values. They sit in `Documents\Assetto Corsa Competizione\Customs\Liveries\<customSkinName>\`, and a car/team json in `Customs\Cars\` points to that folder through `customSkinName`. The game lays decals over its own in-game base paint, then sponsors on top, and builds DDS files from the PNGs. Other players see a custom livery only if they have the same files installed.

### Cited Findings
- **Folders:** `C:\Users\<user>\Documents\Assetto Corsa Competizione\Customs\`. The car .json goes in `Customs\Cars`, and the newest json there is your new livery. Texture and json files go in a subfolder of `Customs\Liveries` whose name must match the `customSkinName` value in the car json, which is how ACC links the two. — [simracingsetup: where to find/install ACC liveries](https://simracingsetup.com/assetto-corsa/where-to-find-acc-liveries/) (search summary); [/ovg/ wiki: Getting skins into ACC](https://www.get-good.net/index.php/Getting_Skins_Into_Assetto_Corsa_Competizione) (last edited 6 Apr 2021, game v1.5.9, OLDER)
- After you save a team, the game writes a randomly named .json in `Customs\Cars`, which can be renamed. `customSkinName` must be unique. — [/ovg/ wiki](https://www.get-good.net/index.php/Getting_Skins_Into_Assetto_Corsa_Competizione) (2021)
- **Files:** `decals.png` is the main skin file. `decals.json` is generated by the game and holds the PBR values. `sponsors.png` and `sponsors.json` form the second region. The wiki notes that sponsors.png is required for the Lexus. Not every file is required: one user reports decals.json plus decals.png alone is fine. Other guides also list DDS files, which ACC generates from the PNGs. — [/ovg/ wiki](https://www.get-good.net/index.php/Getting_Skins_Into_Assetto_Corsa_Competizione); [simracingsetup](https://simracingsetup.com/assetto-corsa/where-to-find-acc-liveries/) (search summary)
- **Sizes:** Kunos's design document, released to SRO esports teams, says `decals.png` should be no larger than 2048x2048 and `sponsors.png` no larger than 4096x4096. The community author guesses this is to do with LOD. — [True2Life-Racing how-to, OverTake](https://overtake.gg/threads/true2life-racing-how-to-full-custom-liveries-in-assetto-corsa-competizione.183706/) (search summary; the Kunos document itself was not found)
- **Layer order:** "The decals is layered on first with the sponsors layered on last". Each has its own json of finish settings. — [True2Life-Racing how-to](https://overtake.gg/threads/true2life-racing-how-to-full-custom-liveries-in-assetto-corsa-competizione.183706/) (search summary)
- **PBR json keys:** `baseRoughness`, `clearCoat`, `clearCoatRoughness`, `metallic`. Presets (baseRoughness / clearCoat / clearCoatRoughness / metallic): Glossy 0 / 1 / 0 / 0; Matte 0.45 / 0.3 / 0.6 / 0; Satin 0.45 / 0.1 / 0.3 / 0; Satin Metallic 0.3 / 0.5 / 0.3 / 0.7; Metallic 0 / 1 / 0 / 0.625; Chrome 0 / 1 / 0 / 0.9. — [/ovg/ wiki](https://www.get-good.net/index.php/Getting_Skins_Into_Assetto_Corsa_Competizione) (2021)
- **Limits:** at most two PBR regions (decals and sponsors), and the second is not supported on the Lexus. For best results keep RGB values between 10 and 237. In the Team Editor, setting "Design" to 1 hides some stamped decals but also removes wheel colours, and the effect varies by car (on the McLaren 720S it removes all number plates and stamped decals). — [/ovg/ wiki](https://www.get-good.net/index.php/Getting_Skins_Into_Assetto_Corsa_Competizione) (2021)
- **Templates:** painters use the right `EXT_Skin.psd` for the car. Each contains that car's wireframe, and using the wrong one gives an incorrect-looking livery. ACC also has an in-game livery editor as an alternative to Photoshop. — [simracingsetup ACC livery tutorial](https://simracingsetup.com/assetto-corsa/acc-custom-livery-tutorial/) (search summary; page bot-blocked)
- **Online visibility:** "other racers who do not have the same files installed will not see it". Custom skins are not shared by the game. Livery sites such as Pitskill host ACC liveries for download. — [simracingsetup / search summary](https://simracingsetup.com/assetto-corsa/where-to-find-acc-liveries/)
- Community "conversion templates" exist that move an ACC template to another sim, for example the [BMW M4 GT3 conversion template ACC to rFactor 2](https://www.overtake.gg/downloads/bmw-m4-gt3-conversion-template-acc-to-rfactor-2.48616/) (title only).

### Inferences
- An app's ACC output is RGBA PNGs where transparent pixels let the in-game base colour and template design show through, plus `decals.json` and `sponsors.json` holding the four PBR floats, plus a car json with `customSkinName` set. The two-layer model gives at most two material finishes per livery.
- Race numbers seem to be set in the car or team json in the in-game Team Editor and stamped by the game, not painted, but this is not confirmed (see gaps).

### Gaps
- The official Kunos livery design document and the complete car-json schema (for example `raceNumber`, `skinTemplateKey`, `bannerTemplateKey`, colour IDs, `useEnduranceKit`) were not found. Only `customSkinName` is sourced.
- The names of the DDS files ACC generates (for example `decals_0.dds` / `sponsors_1.dds`) and when it builds them were not sourced.
- Whether Kunos still supplies an official template pack in 2026 and where (the ACC forums were not reached). Exact layer list of `EXT_Skin.psd` (AO, wireframe, guides) not confirmed.
- How the alpha in decals.png blends with the base paint (straight vs premultiplied, partial alpha). Not documented in the sources found.
- Most ACC sources are from 2021 (v1.5 to v1.8). Nothing from 2025-26 confirmed whether the system has changed.

## rFactor 2 and Le Mans Ultimate: livery naming, region/alt files, LMU custom-livery status in 2026

### Takeaway
Under the current material system, an rFactor 2 skin is `alt_<name>.dds` (DXT5, alpha used only for carbon-fibre specular) plus `alt_<name>_Region.dds`, a flat-colour material ID map (DXT1 for up to 5 regions, DXT5 for 6). Both go in `UserData\player\Settings\<car>\<team folder>\`, and rF2 sends them to other drivers automatically as a `.mas` when you join a server. LMU uses the same region idea but takes two uncompressed TGAs (`customskin.tga` + `customskin_region.tga`) in `UserData\Liveries`. You upload them through the showroom for approval, and using them online needs a RaceControl Pro or Pro+ subscription. Since v1.1 (Sept 2025) custom liveries also work offline and on hosted/practice servers.

### Cited Findings
**rFactor 2 (Studio 397 "How to paint a car with the new material system", last modified 12 Jan 2023):** — [docs.studio-397.com](https://docs.studio-397.com/x/lwAqBQ)
- Skin `alt_<name>.dds` (example `alt_AMV.dds`). Region file `alt_<name>_Region.dds` with the suffix `_Region`. The `alt_` prefix is required and the file name must not exceed 12 characters.
- Skin DDS is DXT5 (interpolated alpha), and the alpha channel should hold only the carbon-fibre specular data. Region DDS is DXT1 with no alpha for 1 to 5 regions, or DXT5 with the alpha region copied into the alpha channel for 6 regions.
- "AO is now global": the albedo should contain no baked ambient occlusion or shadows, and the skin needs no AO map.
- Six regions are plain colours: Black, Red, Green, Blue, White and Alpha. Black is the base car-body paint. RGB values must match the templates exactly. Metal flake works only on the Black region. Since build 1131 the Green region can make parts glow at night, such as number panels.
- Materials (Chrome, Shiny Carbon Fibre, Paint, Car Paint, Shiny Vinyl) are assigned per region in the showroom, along with metal-flake strength (Black only) and a lacquer colour.
- Template (Aston Martin GT3 example): layer groups Paint / Sponsors / Numbers, a Main Color layer, solid-colour fill layers with masks, a merged Logos layer, a carbon-fibre mask, a parts layer, and pre-made region layers with fixed RGB.
- Folders: `...\rFactor 2\UserData\player\Settings\AstonMartin_Vantage_GT3_2019\` with a team folder created in-game (for example `AMV_GT3_01XXXX`). Steps: showroom, Customize, +, Create Skin Folder, Reload Skin, Create Team Car.
- Online: skins are sent automatically to everyone on a server when you join. The team folder holds `alt_<name>.dds`, `alt_<name>_Region.dds` and a compressed `alt_<name>.mas`, which is the file sent to the server. Extra files such as windows and helmets can go in the team folder.
- **Older or other naming:** community guides also show legacy names such as `alt10.dds`, `altDRIVER.dds`, `altHELMET.dds`, `<name>_ALT.dds`, and car-number-based skins in a car's folder. — [OverTake: install skins](https://www.overtake.gg/threads/install-skins.130478/) (search summary, older); [get-good: getting skins into rF2](https://get-good.net/index.php/Getting_Skins_Into_rFactor_2) (search summary)

**Le Mans Ultimate:**
- Templates ship with the game in `<Steam>\Le Mans Ultimate\Support\LiveryTemplates`. — [LMU official guide](https://guide.lemansultimate.com/hc/en-gb/articles/13211180344719) (search summary; 403 on fetch); [RaceControl news guide, 18 Jul 2025](https://news.racecontrol.gg/?p=1223)
- Output is two uncompressed TGA files: `customskin.tga` (base design) and `customskin_region.tga` (material regions), placed in `steamapps\common\Le Mans Ultimate\UserData\Liveries`. Press RELOAD in the showroom to load them, set materials there, then press UPLOAD to submit for approval. Approved designs appear in the team's liveries. — [RaceControl news, 18 Jul 2025](https://news.racecontrol.gg/?p=1223)
- LMU region colours: Black = base car material (only region that takes metallic/flake). Red = default carbon preset, which overrides any design it overlaps. Blue/Green = materials such as chrome, stickers or wrap vinyl. White = logos and number plates. — [RaceControl news](https://news.racecontrol.gg/?p=1223)
- Template rules: don't alter the number-plate positioning, the Levels layer or the carbon-coloured areas. Disable the Mask layer before export and keep the Levels layer visible. — [RaceControl news](https://news.racecontrol.gg/?p=1223)
- A team is needed first, and the livery must be assigned to a lineup before signing a car up to an event. In single-driver events players see only liveries of lineups they belong to. — [RaceControl news](https://news.racecontrol.gg/?p=1223)
- Subscription: all players can use the livery showroom, but an active RaceControl Pro or Pro+ subscription is needed to upload and use a custom livery online (June 2025 release notes). A Sept 2025 article repeats that you or your team owner need Pro/Pro+. — [LMU news 9 Jun 2025](https://lemansultimate.com/?p=1996) (search summary); [LMU news 18 Sep 2025](https://lemansultimate.com/lmu-adds-first-elms-content-and-custom-livery-upgrades/) (search summary)
- **v1.1 (Sept 2025) changes:** custom liveries on hosted and practice servers and in single-player race weekends, plus custom numbers and offline use. — [LMU news 18 Sep 2025](https://lemansultimate.com/lmu-adds-first-elms-content-and-custom-livery-upgrades/) (search summary); [RaceControl news](https://news.racecontrol.gg/?p=1397) (search summary). This **contradicts** the older official guide and the July 2025 RaceControl guide, which say liveries are online-only and "not transferred on non-pre-registered servers, such as practice servers or hosted servers". The Sept 2025 v1.1 notes are newer.
- **Sharing:** RaceControl's Livery Hub lets users share, find and set liveries that creators have made public. — [RaceControl: The New Livery Hub launches for LMU](https://news.racecontrol.gg/?p=1406) (search summary)
- 2026: v1.4.2 (22 Sep 2026) added over 90 new official liveries, including 2026 ELMS and Le Mans schemes. No 2026 change to the custom-livery system itself was found. — [Traxion: LMU v1.4.2 patch notes](https://traxion.gg/le-mans-ultimate-v1-4-2-patch-notes-over-90-new-liveries-and-online-fixes-dominate-new-update/) (search summary)

### Inferences
- rF2 and LMU share a "diffuse + flat-colour region ID map" model. An app could generate the region map automatically from its own layer list (base paint = black, carbon = red, chrome/vinyl = blue/green, logos/numbers = white), but the RGB values must match each template exactly.
- LMU apparently expects TGA, while rF2 expects DXT-compressed DDS, so the two need different exporters.
- LMU distribution goes through the in-game upload and approval process and RaceControl, not loose files, so an app can only prepare files for the user to upload.

### Gaps
- LMU texture resolution and whether alpha is used in `customskin.tga`. No source found, and the 4096x6144 figure seen in search came from an AMS2 post, not LMU.
- Whether the Pro/Pro+ requirement still applies in 2026 for online use. Not confirmed after Sept 2025.
- rF2 skin resolution: not stated in the S397 page (commonly 2048 or 4096 by car, but unsourced).
- Whether LMU's `customskin` file name is fixed or per livery (only "customskin" is documented).

## AMS2: custom livery overrides (.dds, override xml), sizes

### Takeaway
AMS2 has no free "add a livery" system. Its "User Livery Overrides" let you replace an existing livery slot locally, using DDS textures and a per-car XML in `Automobilista 2\Vehicles\Textures\CustomLiveries\Overrides\`. Overrides are local-only: other players see the default liveries. Reiza links per-car templates (.rar) in the forum.

### Cited Findings
- Files live in `Automobilista 2\Vehicles\Textures\CustomLiveries\Overrides\`, with one `_dist.xml` file or folder per car. The game-folder files include the steps (naming, folder structure examples, thumbnail previews). Overrides are "local-only but multiplayer compatible" and let users override default liveries "without the need to extract game files". Any texture not supplied falls back to the base livery. Helmet overrides can be defined with a livery, but custom helmets can't be applied to default liveries. You can only replace liveries a car already has: no new liveries, AI drivers or driver assignments. Each car has a template `.rar` link in the first post, plus helmet and driver-suit templates. Some links are wrong. — [Reiza forum: AMS2 User Livery Overrides, first post](https://forum.reizastudios.com/threads/ams2-user-livery-overrides.14819/)
- The XML is named after the car folder (for example `corvette_c5r\corvette_c5r.xml`). Each entry sets a `LIVERY` number, `NAME` and `BASELIVERY`, then points a `BODY` texture at your DDS. — [Reiza forum user posts](https://forum.reizastudios.com/threads/ams2-user-livery-overrides.14819/page-159) (search summary, anecdotal)
- **BASELIVERY conflicts:** one user's Lamborghini livery only worked with `BASELIVERY="Matte"`, while another found `BASELIVERY="Default"` fixed a SilverMetallic base showing red in some cameras. — [Reiza forum](https://forum.reizastudios.com/goto/post?id=316448) (search summary, anecdotal)
- **Format and size:** a commenter says the override directions specify 4096x4096 DDS. Another says that for Chrome-base liveries the painted DDS is DXT1 with a DXT5 specular map, while Matte uses a DXT5 painted DDS with an alpha channel. — [Reiza forum](https://forum.reizastudios.com/goto/post?id=316450) (search summary, anecdotal). A 4096x6144 template size also appeared in an AMS2 template post (search summary, unverified).
- Users want custom skins visible online, but no reply in the thread confirms that is supported. — [Reiza forum first post page](https://forum.reizastudios.com/threads/ams2-user-livery-overrides.14819/)
- Extra textures such as headlights are not always in the templates. One user says a community command-line tool ("PcarsTools") extracts the game's pak files. — [Reiza forum](https://forum.reizastudios.com/goto/post?id=273845) (search summary). (Noted only as a fact. Not researched or recommended. The official route is the override system, which needs no extraction.)

### Inferences
- An app's AMS2 output would be one or more DDS files (likely 4096 wide, DXT1/DXT5 depending on base finish) plus an XML entry pointing a chosen existing `LIVERY` slot and `BASELIVERY` at them.
- The exact XML schema should be read from the `_dist.xml` files shipped in the user's own Overrides folder. That is the most reliable source and it is on the user's disk.

### Gaps
- The official override instructions (in the game's Overrides folder) were not read. The XML tags beyond LIVERY/NAME/BASELIVERY/BODY, spec-map naming and DDS compression are unconfirmed.
- Whether any 2025-26 AMS2 update changed the override system. Not found.

## Templates: who supplies them, what layers they contain, how painters use AO and wireframe layers

### Takeaway
Developers supply the official templates for all of these sims: iRacing per-car PSDs (also mirrored by Trading Paints), Kunos `EXT_Skin.psd` per car for ACC, Studio 397 PSDs for rF2, templates shipped inside the LMU install, and Reiza per-car .rar files on its forum for AMS2. They share a pattern: paint layers at the bottom, then guide layers (wireframe, masks, stamped or locked items, number-plate positions) that painters switch on while working and off before export. Region or spec groups produce the material map. rF2 explicitly says not to bake AO into the paint because the engine applies AO itself.

### Cited Findings
- iRacing: car Photoshop templates include a custom spec map group. — [iRacing Paint Textures](https://www.iracing.com/painttextures/). Templates include a wireframe guide (hidden by default, white with green panel-edge lines) and a "Turn Off Before Exporting TGA" group of masks and mandatory stamped layers. — [Trading Paints: painting guides](https://help.tradingpaints.com/paint-builder/using-paint-builders-painting-guides/) (search summary). Templates also on [Trading Paints car templates](https://tradingpaints.com/cartemplates).
- ACC: per-car `EXT_Skin.psd` containing that car's wireframe. — [simracingsetup ACC tutorial](https://simracingsetup.com/assetto-corsa/acc-custom-livery-tutorial/) (search summary)
- rF2: Paint / Sponsors / Numbers groups, Main Color, carbon mask, parts layer, fixed-RGB region layers. No baked AO or shadows, because AO is global. — [Studio 397 docs, Jan 2023](https://docs.studio-397.com/x/lwAqBQ)
- LMU: templates in `Support\LiveryTemplates`, with Mask layer (disable before export), Levels layer (keep visible), fixed number-plate positions and carbon areas. — [RaceControl news, Jul 2025](https://news.racecontrol.gg/?p=1223)
- AMS2: per-car template `.rar` links plus helmet and suit templates in the Reiza forum first post. — [Reiza forum](https://forum.reizastudios.com/threads/ams2-user-livery-overrides.14819/)
- General practice: hide the wireframe before saving, then unhide it to keep painting. — search summary of a forum post about another sim, cited alongside [Trading Paints: painting guides](https://help.tradingpaints.com/paint-builder/using-paint-builders-painting-guides/) (general practice, not sim-specific)
- AC (for comparison): AC uses a full-car diffuse texture per skin rather than overlay layers. A real AC skin folder (`content\cars\<car>\skins\<skin>\`) holds DDS/PNG textures named after the model's texture slots (for example `body.dds`, `glass.dds`, `metal_detail.dds`), plus `livery.png`, `preview.jpg` and a `ui_skin.json` with `skinname`, `drivername`, `country`, `team`, `number`. — local evidence: [skins\ratty_s on Nik's PC](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/talbot_sunbeam_lotus_81_works_backup_v6/skins/ratty_s/ui_skin.json)

### Inferences
- An app that works in 2D only can treat each template's wireframe and AO layers as preview-only overlays (multiply or overlay in the editor, never exported) and must reproduce each sim's locked guide layers (number plates, stamped logos, carbon areas) as no-paint zones.
- The material map differs per sim. iRacing packs PBR into the RGBA channels of one spec TGA. rF2/LMU use a flat-colour region ID map with materials chosen in the showroom. ACC uses two layers with four PBR floats each in json. AMS2 uses a spec DDS or alpha depending on base livery. AC uses per-texture shaders defined by the car. A shared internal "finish per layer" model can be exported to all of these.

### Gaps
- Exact layer names in current (2026) ACC and LMU templates: not confirmed. The templates are on the user's disk (LMU install, Kunos download) and can be inspected locally.
- Whether iRacing or ACC templates include a separate AO/shading layer as standard. Not confirmed by sources fetched.

## Which sims' car models can a third-party tool read in 3D, and which leave only 2D templates

### Takeaway
Only Assetto Corsa (and unencrypted third-party mods in rF2/AMS2-style games) gives open, readable 3D car models. Even in AC, a growing share of mod cars use CSP kn5 encryption that scrambles the UV mapping for other tools. Official rF2 content is encrypted in its .mas archives, and nothing found suggests iRacing, ACC or LMU car models are meant to be read by third parties. A cross-sim livery tool should work in 2D on the official templates, and use each sim's own showroom (with reload) as the 3D preview. Decryption or extraction was deliberately not researched.

### Cited Findings
- rF2: HDV files for Studio 397's own cars are encrypted and can't be edited, while many third-party car mods are not encrypted and can be extracted with MAS2.exe. — [OverTake: rFactor 2 HDV files](https://www.overtake.gg/threads/rfactor-2-hdv-files.182237/) (search summary, community). The community MAS-Explorer tool unpacks MAS files only when unencrypted. — [OverTake: MAS Explorer](https://www.overtake.gg/downloads/mas-explorer-from-virtua_lm.62469/) (search summary). Components are signed from their .mas contents, so changing a .mas changes its signature. — [S397 packaging tutorial PDF (2012, older)](https://www.studio-397.com/wp-content/uploads/2016/12/rF2_Packaging_Tutorial.pdf) (search summary)
- Users report you can't remake an encrypted car.mas. Skins and overloads go in separate .mas files or an upgrade package instead. — [r/rfactor2 thread mirror](https://reddit.birdcat.cafe/r/rfactor2/comments/1ky6tne/skin_modding_within_an_rfcmp/muv31cf/?context=3) (search summary, community)
- AMS2: the override system works "without the need to extract game files". The game's own textures are in packed files that need a community tool to open. — [Reiza forum](https://forum.reizastudios.com/threads/ams2-user-livery-overrides.14819/); [Reiza forum user post](https://forum.reizastudios.com/goto/post?id=273845) (search summary)
- AC: Nik's Ratty's4Skin Generator reads AC car models directly. Cars encrypted by their maker with CSP kn5 encryption give every other tool a scrambled texture mapping, so the app names them "protected", gives a plain colour only, and never tries to undo the protection. As of 12 Nov 2026 that was 37 of 233 GT3/GT4/touring cars on Nik's PC. — [local: ac-skin-generator README.md](file:///D:/Claude/Claude-/ac-skin-generator/README.md)
- Each sim has an official in-game way to see a 2D paint on the 3D car: rF2 and LMU showroom RELOAD ([S397 docs](https://docs.studio-397.com/x/lwAqBQ), [RaceControl](https://news.racecontrol.gg/?p=1223)), ACC's in-game livery editor and showroom ([simracingsetup](https://simracingsetup.com/assetto-corsa/acc-custom-livery-tutorial/), search summary), and iRacing loading the player's TGA and rebuilding the spec `.mip` ([iRacing](https://www.iracing.com/painttextures/)).

### Inferences
- iRacing, ACC and LMU: treat as 2D-only for a third-party tool. Their models are not published, and LMU runs on the rF2 engine whose official content is encrypted. This is inferred, not confirmed for each title (see gaps).
- rF2 and AMS2: 2D for official cars. Unencrypted third-party rF2 mods may be readable, but a general tool should not depend on that.
- The legitimate 3D-preview route for these sims is the sim's own showroom, or a 2D "flat preview" in the app using the template's wireframe/AO layers.

### Gaps
- No primary source was found stating that iRacing, ACC (Unreal Engine .pak) or LMU car models are encrypted. Not researched further on purpose, because the search tool declined an extraction-themed query and decryption is out of scope.
- Whether Trading Paints' Paint Builder offers a 3D car preview from iRacing's models (and so a licensed 3D route exists for iRacing). Not confirmed.
- The EULA terms on reading packed game files for each sim. Not researched.
