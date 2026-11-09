# Ratty's4Skin Generator – progress summary (9 Nov 2026)

Handover for Cowork. Everything is in the GitHub repo **Claude-** (`main`), folder `ac-skin-generator/`
(local copy: `D:\Claude\Claude-\ac-skin-generator\`).

## What it is
A Windows app that makes a livery (skin) for almost any Assetto Corsa car. It uses no AI: it reads the
car's own 3D model, works out where every texture pixel sits on the car, and projects the design on in 3D.
That means writing comes out the right way round on both sides of the car, whatever the texture layout.

## Status
- **Built and tested by Claude** on three cars: `wtcc_chevrolet_lacetti` (11 skins), `ks_bmw_m4_gt3`
  (35 skins) and `ks_maserati_alfieri` (1 skin, no livery texture).
- **Not yet tested in-game.** Nik is testing it the evening of 9 Nov 2026.
- Installer built: `release\Rattys4SkinGenerator_Setup.exe` (53 MB). Not in git, because GitHub isn't for
  binaries. Rebuild it with `python build.py`.

## Features
| Tab | What it does |
|---|---|
| Car | Finds the AC cars folder through Steam; pick the car and skin name; optionally copy other files (windows, interior) from an existing skin |
| Livery | Base / accent / highlight / text colours; pattern (sweep, stripes, split, none); halftone dots |
| Number & names | Racing number; style (number board, plain, none); shown on doors and/or roof; team wordmark; driver name |
| Logos | Library of logos and pictures (kept between sessions). Each gets a place: doors, bonnet, front wings, rear quarters, lower doors, roof, boot lid, rear panel, front bumper, windscreen banner, rear window, rear side windows. Plain backgrounds are removed; optional glow tint |
| Windows | New window stickers: banner on the windscreen and rear window, number and name on the rear window and rear side windows; removes the old stickers; inside the car the stickers show their dark back |
| Lights & wheels | Headlight lens colour (tints the lamp textures, so the lens and its glow change, no CSP needed); headlight beam colour (CSP, written to the skin's `ext_config.ini`); wheel colour |

**Preview** shows left, right, front and rear views without writing anything. **Create skin in car**
writes a new skin folder and never overwrites an existing one.

## Install and distribution
- Per-user install, no admin needed: `%LOCALAPPDATA%\Programs\Rattys4SkinGenerator`.
- Adds desktop and Start-menu shortcuts, and an entry in Windows "Installed apps" to uninstall it.
- Settings and the logo library live in `%APPDATA%\Rattys4SkinGenerator` and are kept on uninstall.
- The exe isn't signed, so Windows SmartScreen may warn: "More info" → "Run anyway".
- Install, shortcuts, uninstall and the packaged exe were all tested in a sandbox.

## Files
| File | Purpose |
|---|---|
| `rattys4skin.py` | The app window (tkinter) |
| `skingen.py` | Core: car analysis, texel map, design, logos, windows, headlights, DDS writer, preview renderer |
| `kn5.py` | Reader for AC `.kn5` model files |
| `installer.py`, `build.py` | Installer and build script (PyInstaller) |
| `tests/test_gen.py` | Make a skin from the command line |
| `tests/test_stock.py` | Render any installed skin from all sides (checks for mirrored writing) |
| `README.md` | Full user and technical notes |

## How it works (short)
1. Reads the `.kn5` model: meshes, texture coordinates, normals, materials.
2. Finds the body texture(s), meaning the ones the car's skins replace.
3. Maps every texture pixel to a 3D point and a surface direction on the car.
4. Paintable area = pixels that differ between the car's stock skins (lights, grilles, badges stay as they are).
5. Finds the sill, window line, doors (from the wheel positions), arches, bonnet, roof and boot from the geometry.
6. Projects patterns, number, names and logos from the side, top, front and rear views.
7. Writes mipmapped DDS textures, `ui_skin.json`, `livery.png` and, if needed, `ext_config.ini`.

## Also done this session
- **Hand-made Ratty Racing skin** for the Lacetti: black/purple, #101, Nicklearse101. Installed as
  `wtcc_chevrolet_lacetti/skins/ratty_racing_101`; scripts in `lacetti-ratty-skin/`.
  Its first version had mirrored writing on the right side. The generator's 3D preview found the
  problem and it is fixed.
- **Reusable technique** for Blender work (see `tools/3d-texel-preview.md`): read a model in Python,
  map texture pixels to 3D, quick side/front/rear renders. Useful for checking textures and UVs and
  comparing against photos.

## Known limits
- Cars that get their paint colour only from material settings may come out tinted.
- Messy or overlapping texture layouts leave less paintable area (the log says how much).
- Many Kunos cars have plain 16×16 glass textures. On those, window stickers only work where the
  car has a banner mesh.
- On cars with no CSP headlights, the added beam has a generic shape and may need tuning in-game.
- The preview is a quick render (grey glass and wheels); the Content Manager showroom is the real check.

## Next steps
1. Nik tests in-game (Content Manager showroom and on track), especially writing on both sides, the logo
   look, lens/beam colours and window stickers.
2. Fix whatever the test shows.
3. Optional: a GitHub Release for the installer, code signing, more number fonts.
