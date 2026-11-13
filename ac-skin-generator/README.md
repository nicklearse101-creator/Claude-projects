# Ratty's4Skin Generator

Makes liveries for (almost) any Assetto Corsa car. No AI: the design is projected onto
the car from its own 3D model, so writing reads correctly on both sides whatever the
texture layout looks like.

## Install (for anyone)
Run `Rattys4SkinGenerator_Setup.exe` (built into `release/` together with `Rattys4SkinGenerator_vX.Y.Z.zip`, the installer plus "READ ME FIRST.txt" to share). It installs for
the current user - no admin needed - into a folder they choose (**Change…**; default
`%LOCALAPPDATA%\Programs`), always in its own `Rattys4SkinGenerator` folder there; an update offers the folder the
app is in now (moving it removes the old program files). It adds a Desktop and Start-menu shortcut, and appears
in Windows "Installed apps" for removal.
Python is not needed. Windows SmartScreen may warn because the exe is not signed:
"More info" -> "Run anyway".

Settings, the logo library, saved ghosts and car catalogues (the app's data folder) live in `%APPDATA%\Rattys4SkinGenerator`,
or in a `data` folder next to the installed app when "Keep my logos and settings in that folder too" was ticked
(v1.9.0; copied from AppData, the old copy is left). Updates, moves and the uninstaller never delete it.

## Use
Tabs on the left, preview on the right. **Look (v1.8.0):** dark carbon and orange, slanted 'game' tabs and
buttons, the car's name and skin in the strip on top, dark pop-ups and a dark title bar (`theme.py` holds the
whole look; the layout and every setting are as before).
- **Car** - the AC cars folder (found automatically through Steam), the car, the skin name,
  and optionally a skin to copy the other files from. **App colours (v1.10.0):** 7 themes (`theme.THEMES`:
  Carbon Orange, Ratty Purple, Ice Blue, Racing Green, Red Line, Stealth Grey, Light); the choice is saved
  (`ui_theme`) and the app restarts with it (`theme.use()` runs before any window is made).
  **Report this car...** saves `R4S_report_<car>_<time>.zip` on the desktop: report.txt (version, car, model,
  what was not placed), log.txt (home folder taken out), design.json (logo file names only), catalogue.json,
  preview.png - for the Ratty's Racing Discord.
- **Livery** - base / accent / highlight / text colours and a pattern: sweep, twin centre stripes,
  two-tone split, triple side stripes, centre band over the top, chevron nose, hockey stick, tricolour
  diagonal bands, front-to-rear fade, chequered flag fade, geometric shards, hexagon fade, digital camo,
  lightning bolt, sunburst rays, tiger stripes, paint splatter, pinstripe bundle, plain - or **a pattern
  from a picture**: a side view of a car (fitted to this car's profile) or a flat wrap print, simplified so
  writing and small stickers melt away, in the picture's colours or yours. Inspired by classic liveries (Martini, Gulf, Marlboro, Porsche/Ford, BMW M) and modern wraps;
  all patterns are 3D functions, so they wrap round the car without seams.
  **v1.10.0: 32 more** (`patterns_plus.py`, layered like the hand-made Lacetti skin): Ratty swoosh, endurance
  wedge, 90s touring arcs, retro triple bands, kinetic arrows, speed lines, shark gills, wave flow, halftone
  burst, low-poly shatter, splinter camo, dragon scales, circuit board, topographic lines, digital glitch,
  racing flames, brushstrokes, neon grid, carbon lower body, fade stripes, tribal blades, chequer scatter,
  diamond mesh, diagonal split, pixel dissolve, starfield, electric arcs, barcode rear, ribbon twist, GT sash,
  paint drips, tech honeycomb. **Gallery...** shows them all in the design's colours (click to use).
- **Number & names** - racing number, number style (board, plain, none), where it shows
  (doors, roof), team wordmark, driver name, a font for each of the three (any font installed on the PC), and a grid to choose where each is written (front wings,
  lower doors, doors, rear quarters, bonnet, roof, boot, rear, front). Writing switches to a readable
  colour and gets a thin outline, so it shows over any pattern.
- **Logos** - your library of logos and pictures. It comes with a starter set (about 230 logos) on
  first start; add your own images once and give each a place: doors, bonnet, front wings, rear quarters,
  lower doors, roof, boot lid, rear panel, front bumper, windscreen banner, rear window, rear side windows.
  Optional glow tint. Several logos can share one place: they start side by side, each with its own box
  to move on the preview. **Not placed (v1.10.0):** a logo / name / number with no place found on the car
  (or that lands on no surface) is listed in a NOT PLACED bar after Preview (`info['missing']`); the user
  picks the spot on one view and it is kept as `adjust[key]['pin'] = {view: [a, b]}` (side panels: the
  other side mirrored).
- **Windows** - new window stickers: a banner that follows the top edge of the windscreen and rear
  window (full width, height 8-25 cm, default 12), number and driver name on the rear window and on the
  side windows you choose (rear side windows, front door windows or both); optionally removes the
  stickers already there. Inside the car the stickers show their dark back. **Tinted windows**: a colour
  and how dark (5-90 %), the windscreen only when ticked; stickers stay on top of the tint.
- **Lights & wheels** - headlight lens colour (tints the lamp textures, so the lens and its
  glow change), rim colour and tyre colour (separate).
- **Smaller files** (Car tab, on by default) - compressed textures (DXT1, or DXT5 where there is
  transparency), about a quarter of the size: a 4K skin texture is about 22 MB instead of 90 MB.

**Preview** renders left, right, front, rear and top views (1600 px) without writing anything (the skin in
the car does not change - press **Create skin in car** for that); pick a
view or "Open full size".
The preview shows the car cut out on a garage floor (carbon background, hazard stripes, a reflection) with a
**ghost** of the car being edited behind it: its own front view drawn from its 3D model as orange lines (no
textures, so no badges). The ghost is drawn in the background when a car is picked and kept in
`ghosts` in the app's data folder (redrawn if the car's model changes). "PREVIEW ONLY · NOT SAVED"
shows until the skin is created.
**Edit on the preview:** pick one side, click a logo, number or name (each has a dashed box), then drag to
move it, mouse wheel to resize, Shift+wheel to turn, or use the Bigger / Smaller / Turn / Flip / Reset buttons.
**Edit text...** changes the words, font and colour of one team / driver box; **Delete** removes a logo, number or
name (Reset all brings it back). Preview again is quick: the car and pattern are kept from the last preview.
Flip mirrors the picture on that side (so a logo can face forwards on both sides). Moves, sizes and turns
apply to both sides of the car alike. Press Preview again to redraw. The changes are remembered per car.
**Placement:** logos, numbers and writing go where you asked. Nothing is moved, shrunk or left off because
it overlaps something else - move it on the preview if you want it elsewhere. Where a logo and names share a
place the logo is made smaller and the names go under it; a decal hanging off its panel (over a sill or an
opening) is slid onto the panel, and the log says so. A progress bar shows each stage; closing mid-build asks first.
**Create skin in car** writes a new skin folder. If you already made a skin with that name, it asks
whether to replace it (the old one goes only once the new one is built); skins the app didn't make are
never overwritten. In Content Manager
pick the skin and click "Update preview".

## How it works (`skingen.py`)
1. `kn5.py` reads the model: meshes with UVs/normals, materials, embedded textures.
2. Body textures = diffuse textures the stock skins override, ranked by 3D area (wheel
   textures separate). If no skin overrides one, the paint material's own kn5 texture is used
   (skins can override any kn5 texture by file name).
3. Every body triangle is rasterised into texture space, giving each texel a 3D position and
   normal (closest-point barycentrics; thin sliver triangles drawn first).
4. Paintable texels = texels that differ between the stock skins; lights, grilles, badges and
   interior stay. Baked shading from the brightest stock value per texel.
5. Placement from the geometry: sill and window line, doors between the wheels
   (`WHEEL_LF`… nodes), arches from the wheel size, bonnet / roof / boot from the uppermost
   flat surfaces. Decals are projected per view with AC's axes (+X = car's left, +Y up,
   +Z forward).
   **A decal is never broken.** It is painted through the triangles that are really visible in its
   footprint (front-most surface per 5 mm cell, 15 mm tolerance), nearest last, however steeply they are
   angled - so it stretches whole over arches, creases and panel steps, also where the car's UVs fold
   over themselves. Hidden surfaces (arch liners, doubled panels, damage meshes) get nothing. Nothing is mirrored by
   the app: where the car itself uses one picture for both sides of a panel (mirrored UVs, e.g. the Kadett
   bonnet) the decal is still put where asked, and the log notes that it also shows (mirrored) on the other
   side. Long writing shrinks to its panel.
   `debug_decals=True` in the design tints every decal's footprint (see `tests/nik_test.py`).
6. Windows: a mesh is glass only if its name says so, its material is see-through, it is not on the
   paint texture and it is not a light, trim, frame or chrome part (the log lists the glass used).
   Old stickers are found by opacity (clear glass is see-through, stickers are not). The banner is
   drawn in the glass's own surface coordinates (along the top edge / down from it). A sun strip
   modelled as a painted panel on the windscreen is found from the geometry and takes the banner;
   Kunos-style overlay meshes (`EXT_Banner`) too. Side stickers go on the rear-most pane per side
   (panes = connected pieces of glass), sized to fit inside it. Small glass textures are enlarged
   by texel size; tiled glass textures and glass shared between windows are skipped. Inside glass
   only gets the backs of stickers that landed outside.
   **CSP stickers:** where the glass picture is shared with another window (or both sides are one mesh), the
   window gets its own copy of the picture through the skin's `ext_config.ini` (`[SHADER_REPLACEMENT] MESHES=` the
   pane; for a both-sides mesh first `[MESH_SPLIT]` at the centre line, original = +X = left, cut = -X). Only
   ext_config + textures in the skin folder: no kn5 is added or changed (online checksums). Research:
   `reports/CSP window stickers on shared glass.md`.
   Tint: the glass texels get a film colour behind what is already on the glass (see-through textures)
   or are blended towards it (opaque ones); window stickers are drawn over the tint.
7. Headlights: front light meshes found by name and position; lens tint on their texels. Pop-up
   covers and other painted parts on the body texture are never tinted.
7b. **Name dictionary.** Modders name the same part in many ways and languages. Collected from all 868 cars
   in Nik's library (`tests/catalogue_all_cars.py`, `tests/places_all_cars.py` compare before / after):
   - glass: window, windscreen / windscr, windshield, glass / glas, win_, parabrezza, vetro, lunotto, scheibe,
     vidro, vidrio, parabrisas, luneta, cristal, verre, vitre, pare-brise, lasi, ruit (a see-through material
     whose texture says glass counts when the mesh is window-sized and high on the car); not glass: lights
     (farol, faro, fari, pisca, milha, tulipa, fog, ltl / rtl...), covers, guards, deflectors, stickers, plates;
   - window sticker sheets: banner, sun strip, window_sticker, windows_decals, decal_glass, Glass_Sticker...;
   - headlights: headlight / headlamp, lamp, faro, fari, farol, fanal, phare, scheinwerfer, koplamp, ajovalo,
     high / low beam (HBEAM, LBEAM), DRL, projector, xenon; indicators (freccia, intermitente, pisca,
     clignotant) are not headlights;
   - bonnet / boot lid: hood, bonnet, capot, cofano, (motor)haube, kapot, konepelti, frunk, trunk, boot,
     tailgate, hatch, coffre, baule, heckklappe, decklid, liftgate, portellone, maletero, kofferraum,
     achterklep, engine cover - front or back is told by where the part sits;
   - paint: carpaint, paint, livery, body colour, carrozzeria, carroceria, carrosserie, karosserie,
     lackierung, vernice, pintura, peinture; a part whose name says car paint is paint even when it also
     says light / grille / window (pop-up `HeadLight R CarPaint`, `EXT_Carpaint_FGrill`);
   - wheels and rims by whole words only (`rim`, `rims`, `rim_lf`...: never inside primera or trim);
     exporters' `_mesh` endings are not grille mesh; interior shells (`body_int`) do not count when picking
     the body texture.
   - the main body texture (it decides where every logo goes) is the biggest outside area with skin / paint /
     livery / body names first: on ~165 cars (most Kunos, GT3 and GT4 cars) a cockpit-shadow, mechanics or
     underbody texture used to win. On a 152-car sample, places refusing a logo went from 177 to 18 (left:
     karts, bikes, trucks, open cars with no roof, estates with no boot lid).
8. The painted colours are spread into the texture's gaps between panels (12 texels), so the old skin's
   colour cannot show as a line along seams and lamp surrounds.
9. `car_catalogue()` lists what was found in a car (body / wheel textures, glass, lights, every material and
   its textures) into `catalogue\CAR.json` in the app's data folder, reused while the model is unchanged.
11. **Speed (v1.9.0, same skins byte for byte):** the gap spreading (8) looks only at empty texels near paint
   (15 s -> under 1 s per 4K texture); a Create straight after a Preview of the same design reuses the painted
   textures (with the same messages and decal boxes); logos are prepared once (kept until the file changes) and
   their enclosed parts found on runs of pixels, not by a pixel flood fill; the 4-point pattern is worked out on up
   to 4 cores and added up in the same order; the Create no longer draws an extra preview sheet the app never
   used. Checked with `tests/same_output_cars.py` (old vs new code, 9 cars incl. Kunos) and `tests/test_speed.py`.
10. Output: mipmapped DDS (compressed DXT1 / DXT5 by default, uncompressed with "Smaller files" off),
   `ui_skin.json`, `livery.png`.

## Build
`python build.py` (needs Python 3 with pillow, numpy, pyinstaller) -> `dist/` app folder and
`release/Rattys4SkinGenerator_Setup.exe`. `Run from source.bat` runs it without building.
`Rattys4SkinGenerator.exe --selftest CAR_DIR` makes a test skin in %TEMP% and writes
`%TEMP%\r4s_selftest.txt`.

## Limits
- Body parts that sit on a texture shared with other things (a kit atlas, plain colour swatches) keep
  their own colour: only the car's livery texture can be painted.
- A part with no room of its own in the texture (all its UVs on one spot) takes one flat colour.
- Wheels and headlight lenses only change where the car has a texture for them that nothing else uses.
- Cars whose paint colour comes only from material settings may tint the result.
- Messy or overlapping UV layouts give less paintable area (the log says how much).
- **Windows (v1.10.2, Nik 13 Nov "the window stickers don't work"):** skin textures now carry exactly the file name the
  model asks for (`skin_file_name`: 'glass.png' stayed 'glass.dds' before and the game ignored it - stickers, tint and
  lens colour never showed on such cars), written in that format (`write_texture`). Tint = the whole glass texture
  (Content Manager paint-shop 'tintedWindow' style), windscreen area kept clear with a margin unless asked, parts that
  share the glass texture and must stay clear (lamps, a windscreen of its own) get a clear copy through CSP. CSP
  sections use the documented `[SHADER_REPLACEMENT_...]` form (Nik's in-game test: MESHES + RESOURCE_FILE works on a
  mesh whose material other windows share; `SHARED_MATERIALS = FORCE` applies to ALL meshes of that material - never use).
- **Protected models (v1.10.1):** cars encrypted by their maker with CSP kn5 encryption show every other tool a
  scrambled texture mapping (`scrambled_uv` > 0.5: small triangles whose corners land far apart in the texture). The
  app names them, gives a plain colour only (whole car when the main paint texture is protected) and never tries to
  undo the protection. 37 of 233 GT3 / GT4 / touring cars on Nik's PC (12 Nov).
- **v1.10.1:** triangles stretched over more than a whole texture width (tiled underbodies, broken triangles) no
  longer count as 'shared paint' nor take body texels; tiny parts spread over the livery (an exhaust tip) don't count
  as sharing when they are under 5 % of the surface, and on such cars go under the panels in the texel map. Fixed
  wtcc_alfa_romeo_156_gta, mclaren_mp412c_gt3, pm3dm_volvo_s40_btcc. uv_overlap no longer stops at 2000 triangles.
- Cars with only plain glass textures (many Kunos cars) can only get the windscreen banner
  where they have a banner mesh.
- The preview draws the car's real triangles with the new textures (as the game maps them), but with
  no glass shading and grey wheels; check in the showroom.

Tested on wtcc_chevrolet_lacetti, ks_bmw_m4_gt3 and ks_maserati_alfieri.
