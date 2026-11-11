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
