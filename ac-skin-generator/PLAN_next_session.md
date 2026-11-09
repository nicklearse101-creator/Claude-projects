# Ratty's4Skin Generator – plan for the next session

Written 9 Nov 2026 after Nik's in-game test of v1.3.2 on `wtcr_peugeot_308_gti_ss`.

**Working:** the overwrite option; no errors so far. Everything is placed in roughly the right spots.
**To fix:** (1) the windscreen banner, (2) writing and pictures breaking across panels, (3) nothing on the
side windows.

Test car for all three: `wtcr_peugeot_308_gti_ss`. Check each fix on the Lacetti, Audi Sport quattro,
BMW M4 GT3 and Escort Mk2 too (`tests/batch_cars.py` for crashes).

---

## 1. Windscreen banner is a mess

**What Nik saw:** our banner mixed with the original windscreen sticker; parts of the old banner still
showing; ours squeezed to the old strip.

**Causes found (Peugeot):**
- **Wrong parts counted as glass.** `window_meshes()` picks up anything with "glass"/"window" in its
  name: chrome trim (`glass` / chrome), black frames (`Windows_dark`, `windscreen01` / black),
  painted window frames (`window_part` / carpaint), and even the **rear lights** (`Stop_red`,
  `Stop_orange`, `Stop_clear`, `gabarite_glass`). Those widen the "windscreen", move its top edge, and
  their tiny shared textures (8x8, 16x16) get "cleaned".
- **The old sticker isn't fully removed.** `clean_glass()` keeps the most common colour as "plain
  glass". When the stock windscreen sticker is large, its white can win, so parts of it survive.
- **The banner is a flat rectangle from the front.** It doesn't follow the curved top edge of the
  glass, so on a raked, curved windscreen it gets cut or misplaced.

**Fixes:**
1. **Stricter glass selection.** A mesh is a window only if all of these hold:
   - it uses a glass/transparent shader (or a material with an alpha-blend mode);
   - its name doesn't match light/stop/brake/tail/indicator/gabarite/chrome/frame/trim/black;
   - it isn't the body paint material;
   - it isn't in the front/rear light areas.

   Print the chosen glass meshes in the log.
2. **Proper clean.** Old stickers are opaque; clear glass is see-through. Make every texel on the glass
   more opaque than the clear-glass level plain glass (use the alpha histogram, not the colour mode).
   Also clear the whole UV area of a stock banner overlay mesh.
3. **Banner that follows the glass.** Build it in the windscreen's own surface coordinates: across =
   distance along the top edge, down = distance from that edge. That way it hugs the curved top edge
   at a fixed height.
4. **Banner height option.** Default 12 cm; user choice 8–25 cm. Width is always the full glass.
5. **If the car has its own banner mesh** (Kunos `EXT_Banner`), draw the picture straight into that
   mesh's UV rectangle (stretched, the right way round). If it's shorter than the chosen height, also put
   the banner on the glass behind it, so the two line up.
6. **Picture banners stretch full-width at the chosen height** (already in 1.3.x). Keep that, and use
   the new edge-following placement.

## 2. Writing and pictures break across panels (front wing logo, wordmark ghosting)

**What Nik saw:**
- The logo on the front wing is split, with a band missing.
- "RATTY RACING" / "Nicklearse101" is doubled, with a faint copy lower down.
- Things wrap onto the next surface round the arch.

**Causes:**
- **No depth test.** Each decal is projected straight from the side, and *every* surface facing that
  way inside its rectangle gets it. That includes hidden surfaces behind or under the outer skin: inner
  arch liners, double-skinned panels, damage/dirt duplicate meshes, the flare edge. Hence ghost copies
  and pieces "on the next surface".
- **Steep surfaces get stretched pieces.** Facing threshold 0.35 means surfaces up to about 70° from
  the view still take the decal, so curved arch lips and creases show stretched or broken bits.
- **Panels skipped inside the logo.** The missing band is probably a panel whose texels are marked
  shared or fixed, so the decal skips it.

**Nik's rule: never break a picture. Stretch it over curves, arches and panel steps, keeping it whole.**
No fading or cutting at steep surfaces.

**Fixes:**
1. **Depth test per decal (main fix).** Rasterise the decal's rectangle into a grid of about 5 mm
   cells. Keep only the front-most (outer) surface in each cell, with a tolerance of about 15 mm.
   Hidden and inner surfaces (arch liners, doubled panels, damage meshes) get nothing: no ghost copies.
2. **Stretch over the whole outer surface.** Every outer texel inside the decal's footprint gets its
   part of the picture, however steeply it is angled: arch lips, flares and creases included. So the
   picture runs on unbroken (stretched where the surface turns away). Drop the facing cut-off for side
   decals, apart from surfaces facing completely away (backs of panels).
3. **No holes inside a decal.** Texels marked "shared" or "fixed" inside a decal's footprint must not
   leave a gap in the picture. Find out what the missing band on the Peugeot's wing logo is:
   - **A separate panel:** include it.
   - **Truly mirrored UVs:** move the decal so it doesn't straddle them.

   Log the mesh names.
4. **Gentle placement nudge (optional).** Only so that a logo isn't centred right on an arch edge. It
   must never shrink or crop the picture.
5. **Check.** Add a "debug overlay" preview that colours each decal's texels, to show where it lands
   and confirm it is whole.

## 3. Nothing on the side windows

**Causes found (Peugeot):**
- **The "rear-most side window" is found from all side-facing "glass".** That includes the rear lights
  (`Stop_*`) and chrome trims, so the number and name are aimed at the tail lights, not the window.
- **The side windows are all one mesh (`Side_windows`).** It's on `windows.dds` (512x512) in a small UV
  area. If left and right share texels, writing would come out mirrored, so it's skipped.

**Fixes:**
1. **Find side windows with the stricter glass selection** (1.1). Pick the rear-most side-glass
   *panel* per side by splitting glass into connected pieces (islands), not single points.
2. **Check whether left and right side glass really share texels** (3D shared test, as for the body).
   - **If they don't:** place number and name on each side's rear window.
   - **If they do:** only symmetric content can go there (a logo without text, or the number when it
     reads the same mirrored). Say so in the log and the app.
3. **Low-resolution glass.** If `windows.dds` is small, upscale it like the 16x256 case (texel size
   check, not just "min size < 512").
4. **Option to choose which side windows** get the number / name: rear side windows, front door windows
   (driver's name usually goes there), or both.

---

## Order of work
1. Stricter glass selection (fixes parts of 1 and 3), with logging. *(small)*
2. Depth test (outer surface only) + stretch decals over curves, never break them (fixes 2, also helps the windows). *(medium)*
3. Alpha-based glass clean + banner overlay UV fill. *(medium)*
4. Edge-following banner + height option. *(medium)*
5. Side windows: island split, shared check, upscale, door-window option. *(medium)*
6. Smart placement search. *(medium, after 2)*
7. Re-test on the five cars + `tests/batch_cars.py`; rebuild the installer (v1.4.0); update README and
   `COWORK_SUMMARY.md`.

## Done before this plan (for reference)
v1.3.2 fixed black distance mipmaps; glass never painted as body; plain-colour (shared texture) cars
detected; stock-skin comparison streamed (much faster); lens tint skips shared chrome; overwrite of
app-made skins; batch test (30 random cars, 0 crashes).
