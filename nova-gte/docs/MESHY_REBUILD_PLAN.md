# Nova GTE shell: section-by-section rebuild over the Meshy shell (plan, 2026-10-20)

Agreed with Nik 2026-10-20. Pick up here next week.

## Ground rules from Nik

- **Shell only.** Don't export to AC, don't change textures or colours, don't paint, and don't touch the interior unless Nik asks.
- **Do exactly the step asked.** Show Nik each section, then stop.
- **Keep the Meshy texture as it is.** Nik changes the colour later.
- **Doors must open.** They stay separate objects.

## Where things are

| What | Where |
|---|---|
| Current shell (smoothed, texture intact, doors cut) | `blender/nova_meshy.blend`: objects `Meshy_Body`, `DOOR_L`, `DOOR_R` |
| Shell before smoothing | `blender/BACKUP_nova_meshy_before_smoothing.blend` |
| Shell before the door cut | `blender/BACKUP_nova_meshy_before_doors.blend` |
| Source model, Meshy remesh (300k tris, clean UVs) | `export/meshy/f400_v1_remesh300k.glb` (+ `_textures/`) |
| Original Meshy model (2.6M tris) | `export/meshy/f400_v1.glb`, base colour `f400_v1_base_color.png` |
| Photos Meshy used (one car, F400 PTF) | `reference/meshy_input/` |
| Nik's grey reference pictures | `reference/photos/grey_studio/{side,front,rear}.png` |
| Scripts | `tools/gen/` (below) |
| Old procedural build (phases 1–12, stopped) | `blender/nova_proc.blend`, `blender/scripts/proc/` |
| Abandoned recolour/export attempt (don't use) | `blender/nova_meshy_car.blend` |

## How the current shell was made (to rebuild it if needed)

All runs are headless: `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup ...`. Without `--factory-startup` the blender-mcp add-on hangs headless runs.

1. Fit the remesh to the Nova frame (x+ = car's left, y− = front, z up, ground z = 0, length 3.622 m centred):
   `--python tools/gen/fit_meshy.py -- export/meshy/f400_v1_remesh300k.glb blender/nova_meshy.blend`
2. Put the axles on y −1.141 / +1.202 and weld the UV-seam vertices:
   `blender/nova_meshy.blend --python tools/gen/prep_meshy.py -- -0.0215 1.0`
3. Cut the doors (`DOOR_L` / `DOOR_R`, inner skin, body jambs, front hinge pivots at y −0.69, z 0.58):
   `--python tools/gen/cut_doors.py`
4. Smooth: `--python tools/gen/smooth_taubin.py -- 80 out.blend`
   - Taubin smoothing, moving each vertex only along its normal.
   - The door outline ±2.5 cm and the side-window band are pinned.
5. Checks:
   - `tools/gen/door_test.py` renders the doors open and closed.
   - The scratchpad `wavy_view.py` uses a metal_carpaint matcap that shows the waves. Re-create it if needed.

## Measurements of the Meshy shell (before any width/height scaling)

| | Measured | Spec |
|---|---|---|
| Length | 3.622 (scaled to it) | 3.622 |
| Wheelbase | 2.342 | 2.343 |
| Track | ~1.31 | 1.32 / 1.30 |
| Height | 1.338 | 1.365 |
| Body width, no mirrors | 1.58 | 1.532 |

Nik said close is fine and we scale later.

**Door outline (y, z),** read off the model's own shut lines:

```
(-0.700,0.305) (0.475,0.305) (0.475,0.865) (0.415,0.865) (0.415,1.265) (-0.195,1.265) (-0.690,0.860)
```

- Front edge vertical at y −0.70, then up the A-pillar to the roof rail at z 1.265.
- Rear edge at y 0.475 below the belt line, 0.415 (window frame) above it.
- Bottom at z 0.305.

Belt line z ≈ 0.86.

## Gotchas learned (don't repeat)

- **Never use Blender Decimate (collapse) on the textured Meshy mesh.** It scrambles the UVs at seams (white/grey patches). Use Meshy's remesh (5 credits) for a lower count.
- **Weld the glTF UV-seam vertices (`remove_doubles` 1e-4) before any cutting or smoothing.** UVs live on the face corners, so the texture is kept. Without the weld the door inner skin grows fins along every seam.
- **Don't use Solidify on the generated triangles.** It throws spikes; use a copied inner skin instead.
- **Normal-filter denoising crumples this mesh.** Sun 2007 (`tools/gen/smooth_shell.py`) failed, as does dihedral-angle edge pinning: 36% of the edges are over 25°.
- **Appended objects need `view_layer.update()` and `matrix_basis`.** Otherwise `matrix_world` is identity.
- **The first view in Material Preview can show the right door striped** while the shader compiles. It isn't a fault.

## THE PLAN: trace outlines, rebuild sections

One section at a time; show Nik each one before the next.

1. **Trace the outlines on the Meshy shell, per section:**
   - shut lines (bonnet, doors, tailgate);
   - window openings and wheel-arch lips;
   - character lines: beltline crease, bumper top and bottom edges, grille and lamp openings.
   - Sources are the geometry (folds and steps), the texture (dark shut lines and rubbers) and the door outline above. Store each line as a curve or polyline object.
2. **Rebuild each section as a clean, even quad grid inside its traced outline:**
   - A Coons patch from the boundary curves.
   - Fitted to the Meshy surface, with a smoothness term so it follows the overall shape but not the lumps. This is a least-squares fit to the nearest Meshy surface points plus a Laplacian fairing term.
   - Edges end exactly on the traced lines, so they stay crisp.
   - Mirror on X where the section crosses the centre line.
3. **Order:** bonnet first, as the test (large, smooth, shows waves worst). Then front wings, doors (separate, openable), roof, rear quarters, tailgate, front bumper, rear bumper, sills and arches.
4. **Check each section:**
   - reflective (matcap) render against the Meshy shell;
   - side by side with Nik's pictures (`grey_studio`) at the same scale;
   - close-ups in Blender.
5. **Texture last:** bake Meshy's base colour across onto the new panels (Cycles, Selected to Active, colour only). The colours stay unchanged. Only when Nik says.

A cheap fallback if time is short: copy shading normals from a smoothed proxy onto the shell (Data Transfer modifier). This calms the reflections without changing shape or texture.

## Meshy account

- **Key:** `MESHY_API_KEY` in `~/.claude/settings.json` env. Fixed 2026-10-20; Nik's hand edit had a typo. A backup of his version is at `settings.json.BACKUP_before_meshy_fix`.
- **Credits:** about 2,392 left after this session (75 used: 2 × 35 for the multi-image models, 5 for the remesh; the failed run was refunded).
- **Task ids:**
  - F400 model: `01a15a3d-9dcd-73f2-a7d4-43fb3d187a23`
  - Red-car model: `01a15a39-272d-727e-86da-572dac0f44ff`
  - Remesh: `01a15a55-4e66-71f0-8350-d3c0d4f8acd4`
  - Download links expire 2026-10-23, but the files are already saved locally.

## Bonnet done (2026-10-26) — `blender/nova_meshy_bonnet.blend`

`tools/gen/rebuild_bonnet.py` (+ `tools/gen/panel_view.py` for the banded-reflection check render).
`blender/nova_meshy.blend` is untouched; the rebuilt one is the `_bonnet` file.

Outline traced on the shell itself (ortho top renders at 1 mm/px: base colour + 16-bit height map):

| Edge | Traced | How |
|---|---|---|
| Side shut lines | x = ±0.597, dead straight | dark line in the texture, y −0.85…−1.65, scatter ±3 mm |
| Rear (scuttle) | y = −0.700 | height-map curvature minimum (left −0.72, right −0.66, centre masked by the wiper blob) |
| Front (nose fold) | y = −1.6768 + 0.0978·x² (rms 6 mm) | marched forward until dz/dy > 0.55; the fold bows 35 mm forward at the centre |

Panel: 49 × 41 even quad grid (~25 mm), node heights raycast off the shell (3×3 supersampled, median),
then a Laplacian-regularised fit (λ=30, Jacobi) — moved the surface 2.2 mm mean / 24 mm max. The four
boundary rings are faired along the ring only and pinned, so the panel still meets the wings and scuttle at
the shell's own height. 18 mm lip down from the edge; body opening bisected on the traced line with a 4 mm
shut gap and a 45 mm inward jamb.

**UV gotcha:** sampling a UV per grid node off its own hit triangle puts the corners of one quad on different
atlas islands and the quad sweeps the whole texture (dark jigsaw over the bonnet). Fix: one affine 3D→UV map
per face, taken from the triangle under the face centre, applied to all four corners. Texture unchanged.

## 2026-10-26: back to the blocky model, Meshy as the ruler (Nik)

Nik: "it might be easier if we carried on editing the blocky model we made from scratch". So the section
rebuild now happens on `blender/nova_proc.blend` (the phases 1-12 procedural shell), with the Meshy shell
appended into it as a hidden `MESHY_REF` collection to measure against (`tools/gen/add_meshy_ref.py`).
The Meshy-only route is parked at `blender/nova_meshy_bonnet.blend` (shell with the rebuilt bonnet).

- `tools/gen/rebuild_bonnet.py` takes `--ref / --panel / --cut / --uv / --symmetric`, so the same fit runs on
  either model. On the blocky one: `--ref MESHY_REF --panel Hood_Panel --cut Hood --symmetric` (heights
  mirror-averaged, no UVs - the blocky model has no texture).
- `tools/gen/ruler_view.py` renders the blocky model in clay with the ruler ghosted red over it. Objects whose
  name contains "Guide", and the zero-face profile curves, are kept out of the render (Chassis_Guide is a
  solid block that hides the car).
- Where the blocky model stood before the bonnet went in (raycast, not the height map):

  | y | Meshy ruler z (x 0 / 0.45) | old blocky Hood z |
  |---|---|---|
  | -0.72 | 0.912 / 0.898 | 0.939 flat |
  | -1.00 | 0.866 / 0.859 | 0.890 flat |
  | -1.30 | 0.820 / 0.811 | 0.851 flat |
  | -1.60 | 0.755 / 0.736 | 0.764 flat |

  So the blocky bonnet sat 10-30 mm high and had no crown at all.
- REAR_Y moved to -0.678: the texture trace reads -0.65..-0.69 and the blocky model already puts its
  screen base (`Chassis_Front`) there, so the panel mates with it.

**Beware the height map:** `scratchpad height_top.py` writes PNG through the sRGB transfer, so reading it
back as linear gives z values ~20 mm high. Only `x`/`y` positions off it are trustworthy; take heights from
`ray_cast`.

Next sections, in order: front wings (they stand ~25 mm proud of the new bonnet along the shut lines),
scuttle / screen base, then doors, roof, rear.

## Front wings done (2026-10-26) — `tools/gen/rebuild_wing.py`

A wing wraps from horizontal to vertical, so it is sampled radially, not from above: at each y station a fan
of rays is cast inward from an origin inside the body (x 0, z 0.55), giving the body's own cross-section
r(theta). The panel's four edges are read off that profile:

| Edge | How |
|---|---|
| top | where the surface crosses \|x\| = 0.599, just outboard of the bonnet panel -> one parallel shut line |
| bottom | the first break going down: the hit normal stops facing the ray, a radius step > 35 mm, or the skin wraps under. That single curve is the arch lip where the arch is and the valance/sill bottom elsewhere |
| rear | y = -0.700, the door's front shut line as the doors were cut in the Meshy shell |
| front | y = -1.642, where the bonnet's nose fold reaches the shut line; forward of that is the front panel / headlamp section |

Grid 39 x 33 resampled by arc length, radii fitted with the same Laplacian term (moved 2.2 mm mean /
17.7 mm max), 18 mm lip inward from the edge. The skin the panels now carry is removed from
`Fender_Front_Left` and `Hood` by proximity (BVH, 80 mm) rather than by rule.

Two traps, both of which showed up as spikes hanging off the arch:

- **A radius drop does not find the arch lip.** A ray through the arch opening hits the inner wing or the
  tyre and comes back with a perfectly plausible radius. The reliable test is the hit normal: on the outer
  skin it faces the ray, inside an opening it does not (`face < 0.15`).
- **Do not fair the boundary rings hard.** The wing's lower edge has real corners where the arch lip meets
  the valance; the bonnet's `fair_ring(lam=8, 400)` cut them off by over 100 mm. Mild (lam 1, 30) plus an
  outlier-only median across stations (replace a station only if it is more than 8 deg off the local median)
  keeps the corners and kills the spikes.

Still open on the wing: the arch opening sits slightly smaller and higher at its front end than the ruler's.

Next: front panel / headlamps / bumper (the ragged blocky bits ahead of the wing), then scuttle and screen
base, then doors, roof, rear.

## Front end done (2026-10-26) — and a correction to the bonnet

**The Meshy shell is not the ruler for the nose.** Raycasting it against the project's own photo work shows
its nose is the weakest part of the generated mesh: the fold my `find_fold` picked up sits ~60 mm low and
~80 mm short of where the bonnet's leading edge actually is. The project already had that edge triangulated
from the matched cameras (docs/DECISIONS.md, 2026-10-12 late): a **straight V in plan,
y = -1.755 + 0.151·|x|, level at z = 0.722** (photo frame; + DZ 0.0193 for the model frame), both photos
agreeing within 4 mm. A rough read of `reference/meshy_input/f400_side.jpg` (wheelbase as the scale) gives
0.729 — the same edge.

So `rebuild_bonnet.py` now uses the measured edge by default and lifts the last 300 mm of the panel onto it
(smoothstep, convex, 41–80 mm of lift); `--fold` goes back to the shell's own fold. `rebuild_wing.py` takes
its front edge from the same V. Everything the ruler is still good for — the crown, the section, the arch —
is unchanged.

**The front end itself is not modelled here.** `tools/front_end.py` already generates it from the multi-view
triangulations in `tools/photomatch/ba_result.json` plus the c20 / cCF / c22 / cS overlays, which is the most
accurate front-end data the project has: bumper (4 ribs, red pinstripes, plate recess, grey chin lip), lamp
panel, grille surround + insert + groove, headlamps (glass, housing, chrome reflector) and the wrap-round
indicators. `tools/gen/add_front_end.py` loads that JSON into the blocky model (+DZ), deletes the blocky
parts it replaces (`Bumper_Front_GTE`, `Housing_Grille`, `Housing_Headlight_*`) and trims the old nose skin
off `Hood` and `Fender_Front_*` ahead of the bonnet edge. 17 parts, 17 245 faces.

**Judge it painted, not in clay.** `ruler_view.py` gained a `paint` mode that renders the body in the car's
own gunmetal. Against `grey_studio/front.png` in light clay the grille looks far too small and short — but
on a dark grey car the body-colour grille surround (z 0.551–0.70) reads as part of the black opening
(z 0.573–0.650), and measured that way the photo and the model agree. Nearly "corrected" a part that was
already right.

Open on the front: headlamp lenses are blank white (material work); the bumper rib band is an acknowledged
±1 cm estimate in front_end.py (the views disagree by ~2 cm); the grey valance looks a little deep against
the photo.

Next: scuttle and screen base, then doors, roof, rear.

## Scuttle done (2026-10-26) — and the bonnet's REAR edge was wrong too

`tools/gen/rebuild_scuttle.py`. The dark transverse line I first traced on the shell at about y −0.68 is the
**screen base** (the glass edge), not the bonnet's rear edge: the bonnet stops well in front of it, with the
cowl panel and the wiper spindles between. The project had measured all three on one plan curve
(`tools/photomatch/body_profile.json` → `scuttle_curve`, from the c20 + cCF triangulated centre wiper pivot
at (0, −0.800, 0.933) with 2–6 mm ray gaps, the washer jets at ±0.175, −0.811, and the louvre row and screen
seal just behind them; ESTIMATE ±1.5 cm):

    bonnet rear edge   y = -0.900 + 0.33 x²   (never closer than 50 mm to the screen base)
    screen base        y = min(-0.740 + 0.29 x², -0.702)
    louvres            |x| < 0.46, 8..48 mm ahead of the base, 11 mm pitch, 6 mm slots, broken at the pivots

So the bonnet was ~220 mm too long at the centre, swallowing the whole scuttle. `rebuild_bonnet.py` now takes
its rear edge from that curve. The scuttle panel is a 49 × 13 quad patch between the two lines, heights
raycast off the ruler (good here — the shell's cowl is well covered by the photos Meshy was given),
mirror-averaged (the shell's wiper blob is not symmetric, the car is) and faired; 160 mm wide at the centre.
Its rear edge bridges up to whatever `Chassis_Front` starts at, which is the screen-base riser until the
glass gets rebuilt, and that edge is marked sharp — smooth-shaded it reads as a fat rounded bar. Its front
edge returns 40 mm downward so the bonnet's shut line is a dark gap, not a view of the background.

Next: doors, roof and glass, rear.

## Front wings rebuilt again (2026-10-26) — Nik: "the shape looks wrong"

He was right, and measuring it said why. Against the project's own traces the wing fitted to the Meshy shell was:

| | shell / old panel | measured | 
|---|---|---|
| arch lip, over the top | z 0.615 at the axle | **0.641** (`arch_shapes.front`, traced on anglia_side — cS, hubs to 1 px) |
| body half-width at the wing | 0.710–0.739 | **0.742–0.762** (`halfw`, FIA A-5375: 1522 at the front axle, 1535 max) |
| GTE flare step | none — the fairing had smoothed it away | **~8 mm crisp step** at z ≈ 0.70–0.704 (`wing_flare`), headlamp corner to door |

So the arch opening was ~26 mm tight all round the top and the car was 15–30 mm narrow per side here. The
shell is no more the ruler for the wing than it was for the nose.

`rebuild_wing.py` now:
- takes its lower edge from the traced arch inside the arch, blending over 70 mm into the detected break at
  each end (valance ahead, sill behind) — a hard switch there left notches and spikes;
- widens each station onto the measured half-width, zero at the top edge (the bonnet shut line is traced and
  right) ramping to full from the widest row down, and faded out ahead of y −1.50 where the wing genuinely
  tapers in towards the indicator (`front_taper`);
- splits each station's profile into two bands at the flare step so **row KSTEP lands on the step at every
  station**. Snapping the nearest row per station instead makes the step jump rows and zig-zag visibly along
  the whole wing. The riser is 1.5 mm and the mesh is marked sharp at 35°.

Still open: small crease artefacts at the arch's lower corners, and the GTE's grey arch trims and sill
skirts are not modelled yet.
