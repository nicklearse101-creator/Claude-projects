# Ratty's4Skin Generator

Makes liveries for (almost) any Assetto Corsa car. No AI: the design is projected onto
the car from its own 3D model, so writing reads correctly on both sides whatever the
texture layout looks like.

## Install (for anyone)
Run `Rattys4SkinGenerator_Setup.exe` (built into `release/`, about 53 MB). It installs for
the current user - no admin needed - into `%LOCALAPPDATA%\Programs\Rattys4SkinGenerator`,
adds a Desktop and Start-menu shortcut, and appears in Windows "Installed apps" for removal.
Python is not needed. Windows SmartScreen may warn because the exe is not signed:
"More info" -> "Run anyway".

Settings and the logo library live in `%APPDATA%\Rattys4SkinGenerator` (kept on uninstall).

## Use
Tabs on the left, preview on the right.
- **Car** - the AC cars folder (found automatically through Steam), the car, the skin name,
  and optionally a skin to copy the other files from.
- **Livery** - base / accent / highlight / text colours and a pattern: sweep, twin centre stripes,
  two-tone split, triple side stripes, centre band over the top, chevron nose, hockey stick, tricolour
  diagonal bands, front-to-rear fade, chequered flag fade, geometric shards, hexagon fade, digital camo,
  lightning bolt, sunburst rays, tiger stripes, paint splatter, pinstripe bundle, plain - or **a pattern
  from a picture**: a side view of a car (fitted to this car's profile) or a flat wrap print, simplified so
  writing and small stickers melt away, in the picture's colours or yours. Inspired by classic liveries (Martini, Gulf, Marlboro, Porsche/Ford, BMW M) and modern wraps;
  all patterns are 3D functions, so they wrap round the car without seams.
- **Number & names** - racing number, number style (board, plain, none), where it shows
  (doors, roof), team wordmark, driver name, and a grid to choose where each is written (front wings,
  lower doors, doors, rear quarters, bonnet, roof, boot, rear, front). Writing switches to a readable
  colour and gets a thin outline, so it shows over any pattern.
- **Logos** - your library of logos and pictures. Add images once; give each a place:
  doors, bonnet, front wings, rear quarters, lower doors, roof, boot lid, rear panel,
  front bumper, windscreen banner, rear window, rear side windows. Optional glow tint.
- **Windows** - new window stickers: banner across the windscreen and rear window, number
  and driver name on the rear window and rear side windows; optionally removes the stickers
  already there. Inside the car the stickers show their dark back.
- **Lights & wheels** - headlight lens colour (tints the lamp textures, so the lens and its
  glow change), headlight beam colour (Custom Shaders Patch, written to the skin's
  `ext_config.ini`), wheel colour.

**Preview** renders left, right, front, rear and top views (1600 px) without writing anything; pick a
view or "Open full size". A progress bar shows each stage; closing mid-build asks first.
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
   +Z forward). Texels shared by two surfaces get no side writing, so nothing can be mirrored.
6. Windows: glass meshes (and sticker overlay meshes such as Kunos' `EXT_Banner`) get the same
   projection; plain 16x16 glass textures are skipped. Inside glass only gets the backs of
   stickers that landed outside.
7. Headlights: front light meshes found by name and position; lens tint on their texels;
   beam colour overrides the car's CSP `[LIGHT_HEADLIGHT_n] COLOR`, or adds a headlight pair
   at the lamps when the car has none.
8. Output: mipmapped uncompressed DDS, `ui_skin.json`, `livery.png`, `ext_config.ini`.

## Build
`python build.py` (needs Python 3 with pillow, numpy, pyinstaller) -> `dist/` app folder and
`release/Rattys4SkinGenerator_Setup.exe`. `Run from source.bat` runs it without building.
`Rattys4SkinGenerator.exe --selftest CAR_DIR` makes a test skin in %TEMP% and writes
`%TEMP%\r4s_selftest.txt`.

## Limits
- Cars whose paint colour comes only from material settings may tint the result.
- Messy or overlapping UV layouts give less paintable area (the log says how much).
- Cars with only plain glass textures (many Kunos cars) can only get the windscreen banner
  where they have a banner mesh.
- The preview is a quick software render (no glass shading, wheels grey); check in the showroom.

Tested on wtcc_chevrolet_lacetti, ks_bmw_m4_gt3 and ks_maserati_alfieri.
