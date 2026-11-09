# Assetto Corsa WTCC wipers — project report

**Date:** 2026-11-04
**Goal:** give eight WTCC mod cars working windscreen wipers in Assetto Corsa (with Custom Shaders Patch), including rain clearing.
**Result:** all eight have wipers. The user checked them in-game and approved them ("really good").
**Toolkit:** `Claude outputs\ac_wiper_toolkit.zip`. See `TOOLS.md` inside.

---

## 1. Final state of every car

| Car | Wipers | Sweep | How it was done |
|---|---|---|---|
| Alfa Romeo 156 GTA | 1, centre pivot | ~162° | First car. Rigid sweep with no per-frame tilt. Approved as "perfect". |
| Alfa Romeo 156 | 1, centre pivot | 161° | `rigid` |
| BMW 320si | 2, tandem | 85° (user's choice) | `rigid`, two tracks in one animation |
| Chevrolet Lacetti | 2, tandem | 85° | `rigid` |
| Peugeot 407 | 1, centre pivot | 160° (user confirmed) | `rigid`, keeps the node's built-in scale |
| Seat Toledo | 1, moved to the centre | 158° | `rigid` with `--offset` and `--park-rot` |
| Seat Leon TDI | 1, central (it had none) | 167° | `transplant` (copied from the Toledo), then `rigid` |
| Honda Accord | 1, central (its two wipers were merged into the cockpit) | 157° | `extract` (kept its own centre wiper, deleted the other), then `rigid` |

Each car folder now holds:
- `animations/car_wiper.ksanim`: the wiper sweep. CSP plays it when the wipers are switched on.
- `extension/ext_config.ini`: a `[WIPERS_TRACE_...]` section so CSP clears rain where the blade passes.
- `<car>.kn5.bak_wiper`: the base model that `rigid` rebuilds from.
- `<car>.kn5.bak_original`: the untouched model, on cars whose geometry was changed (Leon, Honda).

**To undo** a car, copy `.bak_original` (or `.bak_wiper` where there is no `.bak_original`) back over the `.kn5`, then delete `car_wiper.ksanim` and `ext_config.ini`.

**Not covered:** the Honda's distant-view model (`_lod_a.kn5`) still shows its two original static wipers. This is only visible far away.

---

## 2. The working technique (reusable)

1. **Inspect the model.** List the kn5 node tree and find the wiper and windscreen meshes by name or material (e.g. `CPITWIPER`).
   - If there is no separate wiper, search for long, thin loose parts along the bottom edge of the windscreen inside bigger meshes. The Honda's wipers were merged into its cockpit mesh.
2. **Get the geometry right first.**
   - The pivot is the hub at the wiper's inner end.
   - Trace the windscreen's outline (its open edges) to get the bottom edge and pillar positions. Don't estimate them from nearby vertices.
3. **Fit the rotation axis by measurement.** Choose the axis tilt and lean so that the **blade's underside** (not just the lowest vertex) stays closest to the glass across the sweep.
4. **Animate the wiper as one rigid piece.**
   - Each frame is a sweep about the pivot, plus a small tilt of the whole wiper about the pivot (like the arm spring) to keep the blade near the glass.
   - Eased motion: park, full sweep, park, over 100 frames.
5. **Write the animation, keeping the node's own scale.** Self-check by replaying the written frames.
6. **Rain clearing:** add `ext_config.ini` with `WIPERS_TRACE` naming the wiper and windscreen meshes.
7. **The user checks in-game and sets the sweep angle.** Rerun changing only that value.

Single wipers use a central pivot with a mirror sweep: it parks along the bottom edge and sweeps to the mirror-image position, about 157–167°. Tandem pairs use the same angle for both (85° here).

---

## 3. Successes

- **Measuring instead of guessing.** Every placement and axis came from the actual model geometry. A small Python reader for the kn5 format made this possible without Blender or the AC SDK.
- **Checking the format against Kunos cars.** Before writing anything, I confirmed the ksanim layout and quaternion convention by comparing a Kunos car's kn5 node matrix with its `car_wiper.ksanim` frame 0. As a result, the very first animation worked in-game.
- **Fitting the axis on the blade, not the vertices.** Measuring the gap per 2 cm slice of the blade's underside gave reliable fits. Measuring the single lowest vertex had misled me (on the BMW the tip ended 10 cm above the glass).
- **One-piece wiper with a per-frame arm tilt.** This looks natural and keeps the blade within about 5–30 mm of the glass on every car.
- **Replay self-check.** Rebuilding each written frame and comparing it with the intended pose caught problems before the game did, and it is how the Peugeot scale bug was proved fixed.
- **Model surgery that worked:**
  - `transplant`: copied a wiper between cars, reusing a matching material on the target, so no textures were needed.
  - `extract`: cut merged wiper parts out of a big mesh and deleted the unwanted ones. Exactly the four wiper pieces were removed (127 triangles).
- **Speed once the tool existed.** After the first three cars, each car took minutes. Builds ran in the background, several at once.
- **Backups and rebuild-from-backup.** Every rebuild started from an untouched copy, so experiments never stacked up or corrupted a car.

## 4. Failures (and why)

| What went wrong | Cause | Fix / lesson |
|---|---|---|
| **Cutting the wipers into hinged pieces** to press the blade flat onto the curved glass | It hit the numbers (blade within ~1–5 mm), but in-game every cut wiper looked visibly broken: steps and kinks between the pieces. | Removed completely. Keep wipers **one solid piece**; a small gap to the glass is far less noticeable than a broken-looking wiper. |
| Chasing "0 mm to the glass" | A straight blade can't follow a curved, faceted windscreen. Trying to force it caused the over-engineering above. | Aim for "looks right", not a number. |
| Peugeot wiper rendered kinked and skewed | Its wiper node carries a built-in scale (0.70 × 0.80 × 0.80). My animation frames wrote scale = 1. | Always read the node's scale and write it into every frame (`ksanim_frame` does this now). |
| BMW first fit: tip 10 cm above the glass | The axis was judged on the lowest vertex, which sat near the hub. | Fit on the blade underside, sliced along its length. |
| Toledo wiper moved to the A-pillar | The pivot ended up on the glass. I'd estimated the windscreen edge from nearby vertices and set the pivot 2 cm too high, and the sweep wasn't lined up with the pillar. | Trace the real outline. In the end the user preferred a central wiper anyway. |
| I chose sweep angles myself (e.g. BMW 62°) | The user wanted 85°. Sweep is a judgement call made in-game. | Build with a provisional angle, say so, and let the user set it. |
| Seating search reported false results | The measurement sampled too few points: some slices only had side-face points, and blades often rest partly in the scuttle. | Sample surfaces densely. Ignore "off the glass" for the parked pose and the first ~15° of sweep. |
| Small slips | A missing `import os`; `printf` turning `\a` in a Windows path into a bell character; a bash heredoc that failed to parse. | Use the file-writing tool for files containing paths. Run a quick test after every refactor. |

## 5. Lessons learnt

**Working with the user**
- The user judges in-game. Numbers are only a guide. Show screenshots' worth of facts, then let them decide.
- Leave the sweep angle and placement for the user to confirm. State clearly what is provisional.
- Prefer a simple look (one solid wiper, a central pivot) over a technically "perfect" fit.
- When the user says stop, stop straight away and report exactly what state the files are in.

**Technical**
- kn5 v6: textures, then materials, then the node tree. Matrices are row-vector, with translation in row 3. A material's property block is name + 40 bytes. Mesh vertices are 44 bytes (position, normal, uv, tangent).
- ksanim v2: frames of quaternion (x, y, z, w), position and scale. Nodes are matched by name, and a track **replaces** the node's local transform.
- CSP plays `animations/car_wiper.ksanim` with the wipers on. `[WIPERS_TRACE_...] SURFACE= / WIPERS=` controls rain clearing.
- Windscreen meshes often include the side windows. Filter by z (e.g. `--glass-zmin 0.3`) or by the glass outline.
- Parked wipers often sit partly inside the scuttle or glass. Match the original pose rather than "fixing" it.
- Mod nodes can be rotated, scaled or mirrored. Never assume an identity transform.

**Process**
- Prove the file format on a known-good example before generating anything.
- Work on a scratch copy, verify, then install.
- Make every command rebuild from an untouched backup so re-runs are safe.
- Keep a self-check in the pipeline (replay what was written).
- Run long builds in the background and in parallel when doing several cars.

## 6. Applying this to other projects

The same approach works for any small animated part on an AC car (or similar binary-model game): wipers, flaps, aero elements, doors, mirrors.
1. Read the binary model yourself.
2. Locate the part from its geometry.
3. Fit motion parameters by measuring against the surrounding geometry.
4. Write the game's own animation format, verified against a stock example.
5. Self-check by replaying it.
6. Let the user judge in-game.

The toolkit's `KN5` reader, the transform helpers and the ksanim writer are reusable as they are.
