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
  (doors, roof), team wordmark, driver name, a font for each of the three (any font installed on the PC), and a grid to choose where each is written (front wings,
  lower doors, doors, rear quarters, bonnet, roof, boot, rear, front). Writing switches to a readable
  colour and gets a thin outline, so it shows over any pattern.
- **Logos** - your library of logos and pictures. Add images once; give each a place:
  doors, bonnet, front wings, rear quarters, lower doors, roof, boot lid, rear panel,
  front bumper, windscreen banner, rear window, rear side windows. Optional glow tint.
- **Windows** - new window stickers: a banner that follows the top edge of the windscreen and rear
  window (full width, height 8-25 cm, default 12), number and driver name on the rear window and on the
  side windows you choose (rear side windows, front door windows or both); optionally removes the
  stickers already there. Inside the car the stickers show their dark back.
- **Lights & wheels** - headlight lens colour (tints the lamp textures, so the lens and its
  glow change), headlight beam colour (Custom Shaders Patch, written to the skin's
  `ext_config.ini`), wheel colour.

**Preview** renders left, right, front, rear and top views (1600 px) without writing anything; pick a
view or "Open full size".
**Edit on the preview:** pick one side, click a logo, number or name (each has a dashed box), then drag to
move it, mouse wheel to resize, Shift+wheel to turn, or use the Bigger / Smaller / Turn / Flip / Reset buttons.
Flip mirrors the picture on that side (so a logo can face forwards on both sides). Moves, sizes and turns
apply to both sides of the car alike. Press Preview again to redraw. The changes are remembered per car.
**Placement check** (in the log): logos, numbers and writing never cover each other - where a logo and
names share a place the logo is made smaller and the names go under it, and anything that would cover
another decal or hang off its panel is moved clear (the log says what moved, or what did not fit). A progress bar shows each stage; closing mid-build asks first.
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
   over themselves. Hidden surfaces (arch liners, doubled panels, damage meshes) get nothing. Where
   the left and right of the car share texels (mirrored UVs) a side decal slides along the car to get
   clear; if it can't, it is left off whole, with a line in the log. Long writing shrinks to its panel.
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
7. Headlights: front light meshes found by name and position; lens tint on their texels;
   beam colour overrides the car's CSP `[LIGHT_HEADLIGHT_n] COLOR`, or adds a headlight pair
   at the lamps when the car has none.
8. The painted colours are spread into the texture's gaps between panels (12 texels), so the old skin's
   colour cannot show as a line along seams and lamp surrounds.
9. `car_catalogue()` lists what was found in a car (body / wheel textures, glass, lights, every material and
   its textures) into `%APPDATA%\Rattys4SkinGenerator\catalogue\CAR.json`, reused while the model is unchanged.
10. Output: mipmapped uncompressed DDS, `ui_skin.json`, `livery.png`, `ext_config.ini`.

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
- Cars with only plain glass textures (many Kunos cars) can only get the windscreen banner
  where they have a banner mesh.
- The preview draws the car's real triangles with the new textures (as the game maps them), but with
  no glass shading and grey wheels; check in the showroom.

Tested on wtcc_chevrolet_lacetti, ks_bmw_m4_gt3 and ks_maserati_alfieri.
