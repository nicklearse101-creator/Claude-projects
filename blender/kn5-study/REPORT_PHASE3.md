# kn5 study, phase 3: 112 cars (2026-11-09)

This phase takes the study from 11 cars to **112**:
- 101 new cars, made up of 77 road and race cars, 12 single-seaters and open cars, 3 traffic cars and 9 classic or rally mods.
- **Split by maker:** 67 Kunos cars, 29 third-party mods and 3 traffic cars. The 12 single-seaters and open cars (also Kunos) and our Nova make up the rest.
- **Checked against published dimensions:** 108 of the 112 cars.

Car lists: `phase3/cars89.txt` and `phase3/open12.txt`.

## Data and tools

**Results:**
- `results/measures.json`: all 112 cars.
- `results/survey.json`: all 112 cars.
- `results/aggregate_112.json`: group medians and technique percentages.
- `results/spec_table.md`: model vs published spec, car by car.

**Published specs:**
- `specs.json`, now covering 108 cars.
- Road cars: parsed automatically from Wikipedia infoboxes (`phase3/fetch.py`, `parse.py`, `build_specs.py`). The infobox block and value for each car were chosen by hand to match the variant.
- Single-seaters, the 787B and the F1 GTR: taken from the web sources listed at the end.

**Measurement fix:** `measure.py` width now runs a 0.6 m spike filter below the beltline.
- This removes mirrors that are part of the door mesh (the Kunos M4, 4C, SLS and others).
- Flares and arches still count, because they run longer than 0.6 m along the car.
- Road-car width error went from a median of 14 mm to 8 mm (75th percentile: 36 → 26 mm).
- `measure.py` now also stores the old raw value as `width_belt_raw` and the name of the widest mesh as `widest_mesh`.
- It also has a fallback for kn5 files whose node names trip the skip list (the stock Sunbeam mod).

## Construction by group

Values are medians, with the interquartile range in brackets.

| | Kunos (67) | Mods (29) | Single-seaters/open (12) | Traffic (3) | Our Nova |
|---|---|---|---|---|---|
| Whole car, triangles | 226k (158–264k) | 283k (191–421k) | 171k | 25k | 1.44M |
| Paint shell, triangles | 28k (23–34k) | 51k (32–80k) | 17.5k | 3.7k | 748k |
| Paint grid, edge length | 24 mm (20–27) | 18.5 mm (14–29) | 18 mm | 68 mm | 5.5 mm |
| Quads | 89 % | 91 % | 88.5 % | 70 % | 60 % |
| Hard edges on paint | 4.8 % | 4.9 % | 12.6 % | 14 % | 2.2 % |
| Plain-average normals | 100 % | 93 % | 100 % | 33 % | yes |
| Unique UVs per side | 93 % | 76 % | 83 % | 33 % | no |
| LODs | 96 % | 59 % | 100 % | 100 % | no |
| Windscreen shader | 97 % | 86 % | 50 % | 0 % | no |
| Damage glass | 94 % | 10 % | 75 % | 0 % | no |
| Rim blur | 99 % | 21 % | 100 % | 0 % | no |
| Alpha-tested parts | 97 % | 72 % | 92 % | 67 % | no |
| Paint skin size | 1024² 37 %, 2048² 54 % | 2048² 59 % | 2048² 58 % | | none |
| Texture data | 34 MB | 69 MB | 32 MB | ~1 MB | |
| Standard dummies | 15 | 7 | 10 | 2 | 5 |

### What this shows
- **The Kunos recipe holds across all 67 cars:**
  - paint shell 23–34k tris on a 20–27 mm grid
  - about 89 % quads
  - plain-average normals on every car
  - LODs, damage glass and rim blur on nearly all of them
  - exported through FBX
  - The 1024² skin with baked AO is the older or road-car standard; 2048² is used where livery detail matters.
- **Mods spend about twice the triangles and texture memory for less accuracy:**
  - Paint shells are denser (51k tris, 18 mm grid).
  - Their dimensions are about four times worse than Kunos (see below).
  - Most skip the game features: only 10 % have damage glass, 21 % rim blur and 59 % LODs.
  - **Lesson:** higher density does not buy accuracy. Measuring does.
- **How single-seaters and open cars differ:**
  - **Small paint shells:** 7–70k tris. Bodywork is a small part of the car; suspension, engine and cockpit take the rest.
  - **Fine grid:** 18 mm.
  - **About 2.5× the hard edges** of road cars (12.6 %), for wing and sidepod edges, splitters and endplates.
  - **Suspension:** every exposed wishbone and pushrod is a separate rigid mesh, animated by `car_susp_LF/RF/LR/RR.ksanim` that follows wheel travel. None of it is skinned.
    - The Ferrari 312/67 and the X-Bow each have one skinned mesh, a flexible boot.
  - **Other animated parts:** the SF70H has `car_wing.ksanim` (DRS), and the 312/67 has `extra_nose`.
  - **Gearshifts:** cockpit and gearshift animations are standard (shift, or shift_up/shift_dw, plus steer). Older cars have a `SHIFT_HD` dummy.
  - **Skins:** from 512² (Lotus 72D, Maserati 250F) up to 2048². Period single-seaters reach 89–93 % quads with very low triangle counts; the Lotus 49 paint shell is 7k tris.
- **Traffic cars:** 68 mm grid and 70 % quads. This is how far you can cut a car down before it reads as low-poly.

## Dimension accuracy (model − published)

The table shows the median |diff| in mm, with the 90th percentile and the number of cars n. Width and track are scored on road cars only.

| Group | Length | Width | Height | Wheelbase |
|---|---|---|---|---|
| Kunos | 14 (p90 102, n 60) | 7 (45, 39) | 20 (59, 55) | **2** (16, 63) |
| Mods | 56 (116, 28) | 22 (78, 16) | 49 (80, 25) | 8 (26, 28) |
| Single-seaters | 18 (n 5) | — | — | 6 (32, 10) |

- **Wheelbase is the strongest check:** 2 mm on Kunos cars. It is fixed by the wheel dummies, and teams publish it.
- **Most large errors are variant mismatches, not modelling errors:**
  - 917K long/short tail
  - Performante and BC bodies longer than the base car
  - BX 4TC vs a plain BX
  - wide-arch race cars against road-car widths
  - Height reads low because of AC ride height.
- **Genuine mod errors found:**
  - **Saxo Cup:** wheelbase −104 mm.
  - **BX 4TC:** wheelbase −44 mm.
  - **Alto Works (traffic):** one plate mesh about 1 m off-car, so it reads 2.6 m wide.
  - **Tesla Model 3 (traffic):** about 290 mm too wide, because of an extra plane.
  - **Volvo V70 (traffic):** wheelbase +50 mm.
  - **Lotus 25 tracks:** −140 mm. This may be a source problem; the two sources disagree on wheelbase.

## Takeaways for our builds (adds to KN5_STUDY section 7)
1. **Fix wheelbase and track first,** using the wheel dummies. Target ±10 mm.
2. **Measure width below the beltline with the 0.6 m spike filter,** and keep mirrors as separate meshes.
3. **Paint shell budget:**
   - road car: 25–35k tris on a 20–25 mm grid
   - single-seater bodywork: 10–25k tris on an 18 mm grid, with more hard edges on aero parts
4. **Single-seater suspension:** build each arm as its own rigid mesh under the `SUSP_` dummies, pivoted at its inner mount, and animate it with `car_susp_XX.ksanim`. Don't skin it.
5. **Ship the game features:** LODs, damage glass and rim blur. Kunos always has them; most mods don't.
6. **Check every spec against the exact variant.** Most "errors" in this study were the wrong variant.

## Sources for single-seater and race specs
- **Ferrari 312T:** f1technical.net; ultimatecarpage.com
- **Lotus 25 and Lotus 72:** supercars.net
- **Ferrari 312:** f1technical.net; flyinglap.com.br
- **Mazda 787B:** ultimatecarpage.com
- **McLaren F1 GTR:** auto-data.net; McLaren 1995 GTR spec sheet
- **From Wikipedia:** Tatuus FA010, Ferrari SF70H, Lotus 49, Lotus 98T, Maserati 250F, Ferrari F2004
- **BMW 1M:** from memory; marked unverified in `specs.json`
