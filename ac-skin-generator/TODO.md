# Ratty's4Skin Generator – to do

Nik's list, in order. Tick items off here when they are done and checked on his cars.

1. [x] **Tinted windows** – option to tint the car's glass (colour and how dark), on the Windows tab.
2. [x] **Undo my flat-top rule** (`OFF_LIMIT` in skingen.py, added 10 Nov): it cuts the tops off wing writing where
   the wing curves over (Kadett, Talbot). Nik's rule: pictures are never cut, they stretch over curves. Take it out.
   (Any bonnet-corner streaks can be moved by hand on the preview, so no other fix is needed.)
3. [x] Window stickers (banner, number, name) can't be moved or deleted on the preview yet.
4. [x] Smaller skin files (compressed DDS) – 4K skins are about 90 MB each.
5. [x] **Preinstalled logos** – the logo library comes with a starter set of logos already in it after install.
6. [x] **Headlights: lens colour only** – remove the cast-light (CSP beam colour) option; keep only the lens colour change.
7. [x] **Name dictionary from Nik's car library** (after 1-6): scan every car's kn5 (mesh, material and texture
   names) and collect all the different names modders use for the same part (glass, body/paint, wings, doors,
   bonnet, boot, banner, lights, rims, interior...). Make the app recognise them, so logos and window stickers work
   on cars where they are refused now. Check on the cars where it fails today.

Dropped (Nik, 11 Nov): Talbot lower-door name behind the sill trim, Escort Mk2 tuned rear half on
`NICK3_KIT_ATLAS.dds` – no fix needed.

Details of earlier fixes: `PLAN_next_session.md`.

## Done 12 Nov night (v1.10.0)
- [x] 'Pick it on the car': a logo / name / number the app can't place is reported, the user clicks the spot on the
  preview. 'Report this car' button: zip on the desktop (catalogue, log, design, preview) to post on Nik's Discord.
- [x] **Lots more patterns, snazzier** ("go nuts") - 32 new (`patterns_plus.py`) + a pattern gallery, in the spirit of the hand-made Lacetti skin
  (`lacetti-ratty-skin/`); some built-in ones are too simple.
- [x] **Colour theme choice for the app** (Nik 12 Nov night) - 7 themes - the carbon + orange look, plus others to pick from.

## Found by the 233-car check (12 Nov night) - to do
- [x] (v1.10.1) **43 GT3 / GT4 / touring cars only get a plain colour** -> 37 are protected by their makers
  (CSP kn5 encryption: the app now says so, never cracks it); Alfa 156 WTCC, MP4-12C GT3, Volvo S40 BTCC fixed;
  Giuliettas x3 + Cadillac really use a shared / atlas texture (stay plain). Was: (17 GT4s incl. gt4_mclaren_570s, gt4_alpine_a110,
  gt4_bmw_m4; 12 Supercars; fsr_* BTCC; cf_ferrari_296_gt3, mclaren_mp412c_gt3, trr_* GT3s, wtcc_alfa_romeo_156_gta).
  Their livery texture's UVs run v = -1..2 (not 0..1), so `uv_overlap` reads thousands and the app treats the
  paint as shared; several (ACC-style ports) also split paint colour (metal_detail), a baked AO map and a separate
  decals texture (EXT_Decals_Colour). Needs: find how the game maps those UVs, then paint them. List:
  D:/ClaudeData/tmp/r4s_places_gt/_plain_split.json.
- 14 cars have one place refused (mostly boot): they now get the NOT PLACED bar, so the user can pick the spot.
- 2 cars unreadable: gravygarage_street_e36_touring (locked by its maker), ks_ferrari_488_gt3_2020 (only a skins
  folder, no car).

## Future - Nik 13 Nov evening
- [ ] **Centre line / alignment grid** on the preview (not too intrusive) to make placing logos by hand easier.
- [x] (v1.10.2) **Window stickers unreliable** - file names fixed, CSP form fixed, tint redone. Was:: sometimes the app says they're there but they aren't (in game); sometimes they
  show from inside the car but not from outside. (Ask Nik which cars; his Talbot 'ratty_s' skin uses CSP window
  stickers: r4s_ext_glass_center_own.dds / r4s_ext_glass_left_2_own.dds + ext_config.ini.)

## Next - Nik 12 Nov evening (REMIND NIK, "no need to fix these just yet")
- [ ] **Logo list won't scroll with the mouse wheel** unless the app is full screen.
- [ ] **Window tint doesn't always reach the window edges**: on the Corvette (`corvette_z06_gt3r`, his skin
  `test_overwrite`, 12 Nov 18:14) some of the SIDE window tint came out on the windscreen.
- Left for now (Nik): the other 1.8.0 small points (resize redraw, several ghost drawings at once, dark "All sides"
  edges, preview look fault could stop a Create, long names push the version off, fonts folder assumed on C:, Tab key,
  special characters in car names, ghost pictures never cleared).

## Done 12 Nov evening (source only, not in an installer yet)
- 1.8.0 small point 8: picking another car clears the last car's preview (picture + logo boxes); a preview of the old
  car that finishes after the switch is not shown on the new one. `tests/test_car_change.py` (real window, test data
  folder, faked painting).

## Done 12 Nov (v1.9.0)
- Speed (Nik: "can we optimise it to work faster"): Create straight after a Preview: Talbot 68 -> 15 s, Kadett
  54 -> 15 s, S13 71 -> 24 s, Lacetti 27 -> 11 s, Ferrari 296 GT3 75 -> 19 s; first Preview of a car ~15-20 %
  faster, Preview after a change ~30 % (Talbot 52 -> 36 s). Skins, preview pictures, logo boxes and messages
  identical to v1.8.0 on 9 cars (Nik's 4 + E30, 296 GT3, quattro rally, 500, 155) - `tests/same_output_cars.py`;
  all 480 logo files prepared identically (1920 checks). Old code's window-sticker messages come in a random order
  from run to run (set order) - harmless, the compare allows it. Not done yet (bigger job): decal placement
  (`decal_hits`) and drawing the five views, the rest of a Preview's time.
  Second round of checks (Nik: "test again"): a second design with the other features (tinted windows, tyres,
  picture pattern, carbon, smaller files, not 4K, hand edits / delete / Edit text on the preview, copy from a stock
  skin; `R4S_VARIANT=2`) identical on 4 cars; peak memory lower (Ferrari 296 GT3 4K: 7.4 -> 6.7 GB). Found and
  fixed: a reused Create repeated the picture pattern's message; the pattern picture cache could clash between cores.
- Installer: choose the folder; option to keep logos and settings in it (`data` next to the exe); finds an old install
  whose Installed-apps entry is missing (Nik's 11 Nov one); moving with the desktop box unticked removes the old
  desktop shortcut. Tests: `tests/test_installer.py`, `tests/test_speed.py`, `tests/install_e2e.py` (real build
  installed, run, updated, uninstalled in a test folder, 27 checks; never touches the real install or desktop).

## Done 12 Nov (v1.8.0)
- Game look (Nik: "like a need for speed home screen"): carbon + orange reskin, same layout; garage preview
  with a ghost of the car being edited. Spec / plan: `docs/2026-11-12-game-look-ui-*.md`. Skins byte-identical
  to v1.7.2 (`tests/same_output.py`). Tests: `tests/test_theme_*.py`, `test_ghost_cache.py`,
  `test_render_alpha.py`, `ui_drive.py`, `ui_dialogs.py`.

## Done 11 Nov (code + checked on the Kadett / Talbot previews; in-game check by Nik still to do)
- 1 tinted windows (Windows tab: colour, how dark, windscreen optional), 2 flat-top rule gone, 3 window stickers have
  preview boxes (move / size / delete), 4 "Smaller files" (DXT1/DXT5 with mipmaps, on by default), 5 starter logos
  (`python make_starter_logos.py` before `build.py`; 233 from Nik's library), 6 beam colour option gone.
- Nik 11 Nov: no mirroring at all. Logos go exactly where asked; several logos on one panel sit side by side, each
  movable; nothing is moved / shrunk / left off for overlapping. NOTE: where the car itself uses one picture for both
  halves of a panel (Kadett bonnet), a logo also shows mirrored on the other half - that is the car's model, the app
  cannot stop it.
- 7 so far: wheel/rim names no longer match inside words (primera, trim, root 'FBX:' node) -> 29 refused cars now
  work (BTCC 1991-99 set); glass names in pt/es/fr/de/fi/nl, Kunos 'WCWINDOW_COCKPIT', 'carpaint' no longer 'int';
  window sticker sheets (window_sticker, windows_decals, decal_glass, Glass_Sticker...) recognised as sticker sheets;
  light words (farol, pisca, milha, tulipa, fara, fog, ltl/rtl, covers) kept off the glass. Tools:
  tests/catalogue_all_cars.py (all cars -> JSON) to compare before / after.

## Done 11 Nov evening (v1.7.0)
- 7 part 2: paint names (carrozzeria / carrozeria, carroceria, carrosserie, karosserie, lackierung, vernice, pintura,
  peinture; a part whose name says car paint is paint even if it says light / grille / window); exporters' `_mesh`
  endings are not grille mesh; bonnet / boot lid words in 10 languages, front or back by position; headlight words
  (fari, fanale, farol, phare, koplamp, ajovalo, high / low / full beam, DRL, projector, xenon), indicators (freccia,
  intermitente, pisca, clignotant) kept out; inner-pane words (wewn, innen, interno, interne, interieur); rally spot
  lamps are not windows.
- Main body texture: the biggest OUTSIDE area (interior / cockpit parts don't count) with skin / paint / livery / body
  names first. ~165 cars (most Kunos and GT3 cars) had a cockpit-shadow, mechanics or underbody texture as the main
  one - that one sets where every logo goes.
- A logo whose spot is an opening (air intake / grille at the default front-bumper height) looks up / down / sideways
  for the panel; preview boxes show where decals really went (and moving one by hand starts from there).
- Headlight lens tint: lamps drawn on the body texture are tinted, painted texels (pop-up covers) are not.
- Window stickers: left off again when the car uses the glass's picture for another window too (>= 10 % of it, or
  backwards on the other side) - the no-mirroring change had let a backwards '101' show on the Kadett's door window.
- Tools: tests/places_all_cars.py (a logo on every place of every car, which places refuse it; SKINGEN_DIR for a
  'before' run with an older copy).
