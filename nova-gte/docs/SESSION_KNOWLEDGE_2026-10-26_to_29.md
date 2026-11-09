# Session knowledge: 2026-10-26 to 2026-10-29

Extracted at the end of the session. Nothing in the model or existing project files was changed to produce this
document; it only records what the session established.

**How to read the labels.** Every claim carries one:

| Label | Meaning |
|---|---|
| **VERIFIED** | measured or tested in this session, with the number or output quoted |
| **FILE** | read directly from a project file or git |
| **ESTIMATE** | a value derived from measurement but with stated uncertainty |
| **HYPOTHESIS** | reasoning not yet tested |
| **OTHER-SESSION** | read from the repo but done by a different session; not my work, not re-verified here |

Commits made in this session: `edbbe92` … `ceb21d1`. Everything from `9992d85` onward in the log is
**OTHER-SESSION** work done between 27 and 29 October, including the FreeCAD replica plan; it is noted where it
supersedes something here.

---

## 1. Two measurement errors that invalidated earlier comparisons

These are the most important findings of the session, because both had been silently corrupting work for weeks.

### 1.1 A 30.5 mm frame disagreement between the drawings and the photographs — VERIFIED

**Fault.** Every line traced off a blueprint was pinned to axles at y −1.141 / +1.202 (a Phase-1 frame derived
from FIA overhangs). `body_profile.json`, all seven solved cameras and the whole photogrammetry frame use the
wheelbase midpoint, y = ±1.1715. So anything from a drawing sat 30.5 mm along the car from anything measured off
a photograph, and the two could never be reconciled.

**Fix.** Re-pinned `trace_side.py`, `trace_plan.py`, `trace_roof.py`; moved the wheel and axle guides
(`tools/gen/frame_guides.py`); corrected `reference/blueprints/side_calibration.json`; moved the overlay tyres in
`match_overlay.py` / `match_look.py`.

**Verification.** Regenerated traces moved by exactly −30.5 mm in y with max |Δz| = 0.000000. The plan
half-width at a given y changed by up to 26 mm near the ends (because the plan taper is steep there).
Old files preserved at `blender/data/BACKUP_blueprint_frame_2026-10-26/`.

Commit `09e6e41`. Reasoning in `docs/DECISIONS.md` 2026-10-27 (9).

### 1.2 The camera solve was stale — VERIFIED

**Fault.** `tools/photomatch/ba_result.json` was not the solution of its own `obs.json`; it predated the last
edit of the marks.

**Verification.** Re-running the identical solve dropped the worst camera from **18.6 px RMS to 12.3**.
Consequences: the **windscreen corners moved about 30 mm down**, and the lamp points moved 11–17 mm forward.

Nik had been saying by eye that the screen sat too high. He was right and my numbers were wrong.

**Fix.** Re-solved with a robust loss (`tools/photomatch/ba2.py`, mode `base`, `soft_l1`, `f_scale=2.0`). Stale
file kept as `tools/photomatch/BACKUP_ba_result_stale_2026-10-12.json`.

**Mark error after the re-solve (VERIFIED, median per camera):**

| Camera | Photograph | Median error |
|---|---|---|
| c20, c22, c23, c24 | Nik's car (F294 DVR) | 2.5–3.3 mm |
| cAR | anglia_rear | 4.8 mm |
| cCF | commons front (F400 PTF) | 5.7 mm |
| cS | anglia_side | 7.0 mm |

### 1.3 A fuller camera model was tried and rejected — VERIFIED

**Hypothesis tested.** Wikimedia photographs are usually cropped, which moves the principal point off the image
centre; `ba.py` fixes it at (W/2, H/2), so that could explain the residuals.

**Result.** Freeing the principal point and adding k2 per camera bought only ~12 % of the cost (862.9 → 760.1)
and asked for principal points up to **1000 px off centre** (cCF: cx +849, cy −1084). That is fitting noise, not
a lens. **Rejected.** The residuals are mark-placement error, not lens error.

### 1.4 Two triangulated points are unreliable — VERIFIED

`DG_RT` and `DG_RB` (door glass rear corners) sit about **55 mm behind** the glass edge that the blueprint and
the photograph agree on — they land in the middle of the B-pillar. Cause: they are seen only by two cameras
looking from nearly the same direction, so depth is unconstrained.

Also flagged as single-view and therefore unreliable: `MIR`, `BON_F`, `PNL_B`; `DSR_B` has weak depth.

**Decision:** the side windows are built from the traces, not from those points.

---

## 2. Reference and diagram findings

### 2.1 The 4-view line blueprint has no rear elevation of our car — VERIFIED

On `reference/blueprints/corsa_a_4view_blueprint.gif`:
- top-left = hatchback **side** (ours; 3622 length, 2343 wheelbase, 1365 height marks)
- top-right = hatchback **front** (tracks 1320/1300, width 1532)
- bottom-left = **saloon** side (3955)
- bottom-right = **saloon rear** (width 1540) — **not our car**

Checking the tail against the bottom-right view would have been checking against the wrong car.

### 2.2 The factory GA sheet does have a hatchback rear elevation — VERIFIED

`reference/blueprints/GA_rear_elevation.jpg` (2992 × 2244) is a rear elevation of the hatchback and dimensions
the tail-lamp colour bands in millimetres above the ground:

| Height | Band |
|---|---|
| **800 mm** | top of the lamp |
| **745 mm** | brake/tail → reflector |
| **685 mm** | reflector → indicator (red → amber) |
| **635 mm** | indicator → reverse (amber → clear) |

Labelled down the right-hand side as *Brems- und Schlußleuchte*, *Rückstrahler*, *Blinkleuchte*,
*Rückfahrleuchte*. Rear track dimensioned 1307.

**Cross-check (VERIFIED):** the drawing's 800 mm lamp top agrees with the triangulated `TL_TI` at 804 mm — 4 mm
apart, so both sources describe the same lamp. The 4298 px commons rear photograph agrees on band order and on
the red/amber break within about 12 mm. The drawing now governs the band heights (`tools/tail_lamps.py`).

### 2.3 Blueprint and photograph agree on the window apertures; two measured points do not — VERIFIED

Drawing the traced edges onto `anglia_side` through its own solved camera (`tools/photomatch/bp_on_photo.py`)
puts **all four edges of both side windows** on the real car's glass. The same overlay puts `DG_RT`/`DG_RB`
mid-B-pillar (§1.4).

Numeric agreement after tracing (VERIFIED):

| Point | Measured z (model frame) | Traced line | Δ |
|---|---|---|---|
| DG_RT | 1.247 | dlo_top 1.247 | **0 mm** |
| QW_FT | 1.237 | qw_top 1.250 | 13 mm |
| QW_RT | 1.229 | qw_top 1.242 | 13 mm |
| QW_FB | 0.876 | qw_bot 0.882 | 6 mm |

The quarter window's traced top runs a consistent ~13 mm high, so it is shifted onto the measured corners with a
front-to-rear ramp; the door window needs no shift.

### 2.4 Other reference facts — FILE

- The line blueprint is **2.4 % short in the overhangs**: calibrated on its own marks it gives a 3539 mm car
  against the homologated 3622. Rule: **trace shape from the drawing, take length and overhangs from the spec
  sheet.**
- The photographed GA sheet retains ~2.5 % local distortion after rectification, and disagrees with itself (the
  front elevation's own 1532 marks read 1572 on the scale its own 1320 track marks give). Same rule applies.
- High-resolution photographs already on disk, unused at the start of the session:
  `1989_Vauxhall_Nova_GTE_1.6_Rear.jpg` 4298 × 2834, `Vauxhall_Nova_GTE.jpg` 4896 × 3672,
  `1991_Opel_Corsa_GSi.jpg` 13150 × 8970. Online searching found nothing better (auction listings cap at
  ~1200 px).

---

## 3. The construction principle established this session

**The finding.** The front bumper and grille are the only parts Nik has called good. The difference from
everything else is structural, not cosmetic.

`tools/front_end.py` builds the bumper as **one cross-section swept along a measured plan path**, where every
feature of the part is a *row* of that section:

- seven rows over the 50 mm top roll-over
- five rows per rib groove
- exact rows at the number-plate recess edges
- eight rows down the tucked-under lower face
- **first and last rows are returns** — the surface turns back behind itself, so there is no raw edge anywhere

and features fade along the path with smoothstep, never step:

```python
def side_t(x):                      # 0 in the centre region, 1 at the corners
    t = min(1.0, max(0.0, (abs(x) - 0.25) / 0.40))
    return t * t * (3 - 2 * t)
```

Everything else was a plain surface with **holes cut through it afterwards**. A cut runs *across* the rows, so
its edge is a staircase of whatever cells it landed in, and the panel is a single skin with a raw boundary —
which is what reads as paper.

Three changes brought the rest of the body toward that method:

### 3.1 Aperture edges as rows of the section — VERIFIED
`build_shell2.py`: the glass band now starts exactly on each window's lower edge and ends on its upper one
wherever a window exists, eased in and out over 55 mm so the band does not kink at the ends. Glass band
refined 8 → 20 rows (≈46 mm → ≈18 mm cells).

**Measured result:** aperture error against the triangulated glass corners went from **10–100 mm to 13–23 mm**,
and the staircase disappeared from the overlays.

### 3.2 Every open edge rolled — VERIFIED (geometry), NOT TESTED in game
`tools/gen/roll_edges.py`. Per boundary vertex: surface normal `n`, boundary tangent `t`, and `h = n × t`
flipped to point *into the opening*; then a small section swept along the boundary.

Six profiles: `arch` (rolls over the lip and turns back into the wheel well), `window`, `screen` (step back into
the glass rebate), `floor` (folds inboard), `hem` (short fold on a free edge), `shut`.

Two refinements that mattered:
- an edge that **butts another panel** is detected with a BVH of the other parts (within 12 mm) and given a
  `shut` return that pulls the edge back 2.2 mm to open a real gap, rather than a flange into fresh air;
- an edge the generator has **already rolled** (the wing and sill build their own arch lips) is detected by
  comparing a boundary face's normal with the face behind it (>52°) and left alone. Rolling twice produced the
  visible flaps.

### 3.3 Shut lines as grooves with walls — VERIFIED (geometry)
`tools/gen/shut_lines.py`, built the way `front_end.py` builds the grille groove: resample the traced line, find
the body surface and normal with a BVH, lay a five-row section across it (lip, wall, floor, wall, lip).
Three lines: `shut_door_front`, `shut_door_rear`, `tailgate_shut`.

### 3.4 Glass derived from the hole — VERIFIED (geometry)
`tools/gen/add_glass.py`. The pane is **the innermost ring of the rebate `roll_edges` already made**, pushed in
4 mm and filled — so it cannot disagree with its aperture. Five panes: both side windows, both halves of the
hatch glass, the windscreen.

---

## 4. Approaches that failed, and why

| Approach | Why it failed |
|---|---|
| **Boolean cuts for apertures** | An exact boolean needs a closed solid. On the open one-skin shell it invented cap faces *inside* the car that filled the windows from behind, and threw a spike under the floor. Replaced by face-removal-by-outline + boundary snapping (`cut_apertures2.py`). |
| **Free principal point + k2 in the camera model** | §1.3 — fitted noise. Rejected on the numbers. |
| **Meshy / AI image-to-3D shell** | Generated surface carried 4.3 mm RMS vertex-to-neighbour lumps, worst 78 mm; nose ~60 mm low, ~80 mm short. Deleted from the blend on Nik's instruction. **A generated mesh is not a measurement.** |
| **FreeCAD NURBS loft (this session's attempt)** | A 56 × 34 section loft hung ~10 min at 2 GB; de-duplication produced inconsistent knots. Only ~20 sections with identical point counts worked. Dropped at the time. (Superseded: OTHER-SESSION work later adopted FreeCAD successfully — see §7.) |
| **Heavy smoothing of the bonnet edge** | A 160 mm running mean was a reasonable response to a lumpy Meshy-derived bonnet, and became a bug the moment the bonnet became analytic — it threw the fitted edge up to 24 mm off in x and 29 mm in z. **A fix that masks a symptom becomes the next bug once the cause is removed.** |
| **Judging matches on downscaled overlays** | Repeatedly over-claimed that areas matched. Nik had to correct me each time. Replaced by full-resolution checks quoting px *and* mm. |
| **Clay renders for shape judgement** | They hide creases. The glossy-red matched-camera render (`match_look.py`) is what draws them. |
| **`look` with camera arguments via blender-mcp** | Ignored. The add-on is protocol 11 against expected 15. Fix: `uvx mcp-for-blender install-addon`, then restart Blender. |

---

## 5. Faults found and fixed this session

| Symptom | Confirmed cause | Status |
|---|---|---|
| Whole tail of the car missing; see-through rear | The backlight cut tested `y` only; at the back of the car the frame/roof segments wrap the *entire* rear face, so it removed the lot | **FIXED** — cut now also required to lie within 45 mm of the glass's own plane (faces removed 351 → 114) |
| Rear came out as a rounded blob with the lamps buried in it | **A station loft along the car cannot hold a vertical rear face** — every point of one has the same `y`, so the last stations collapse into a sliver | **FIXED** — tailgate built as its own panel (`tools/rear_panel.py`) with a seam solved per height where `halfw(y)·sect(z)` meets it |
| The windscreen aperture was not a closed hole at all | `fit_shell` was culling the shell's own skin under the scuttle, and that opening ran into the screen aperture — the two were one ragged hole across the whole scuttle | **FIXED** — scuttle removed from `KEEP`; the shell keeps its surface and the scuttle sits on it |
| Triangular shard visible through the windscreen glass | The pane was one n-gon over an outline ordered by angle around its centroid, which is not strictly convex, so it triangulated across itself | **FIXED** — fan from the centre |
| Ragged flaps along the wing and sill | Edges the generators had already rolled were being rolled a second time | **FIXED** — §3.2 |
| Rear bumper absent from the car | `tools/rear_end.py` had been generating it since 12 Oct but **nothing ever imported it** | **FIXED** — `tools/gen/add_rear_end.py` written |
| Quarter window top 25–33 mm low | `dlo_top_b` stops at the B-pillar and was being held flat beyond it | **FIXED** — dedicated `qw_*` traces |

---

## 6. The one fault left open at the end of my commits

### Bonnet-to-wing shut: 7–10 mm wide, opening to ~40 mm at the nose — VERIFIED

Target is about 4 mm. This is the dark gash across the front wing in every front-three-quarter render.

**Measured (model frame, bonnet edge vs wing top edge):**

| y | gap in x | gap in z |
|---|---|---|
| −1.60 | +41.9 mm | −38.1 mm |
| −1.45 | +9.0 | −8.5 |
| −1.30 | +7.0 | −8.2 |
| −1.15 | +7.0 | −9.2 |
| −1.00 | +7.9 | −10.1 |
| −0.90 | +8.0 | −11.0 |
| −0.80 | +14.4 | −14.5 |

**Three causes found; two fixed:**
1. The wing was built 3 mm outboard of the bonnet's edge **and** `roll_edges` pulls both edges back 2.2 mm each —
   the allowance was counted twice. `SHUT_T` set to 0.
2. The wing's top edge was fitted to the bonnet through a 160 mm running mean (see §4). Window cut to ~12 mm.
3. The bonnet's boundary was sampled per station at 4 decimal places, so at its front corner the V edge and the
   side edge landed on **separate stations** and the fit picked up a 12 mm zigzag. Rounding to 3 dp makes them
   share a station and the max-x test keeps the side edge.

Edge-fit worst case in z improved 31.8 mm → 7.3 mm, but **the gash was still visible in the render**.

**Diagnosis of the remainder (HYPOTHESIS, stated at the time):** the wing's top edge is still a *resample of the
bonnet's mesh* rather than the bonnet's own curve. The fix is for the two panels to share **one shut-line
curve**, each offset by half the gap.

**OTHER-SESSION:** commit `9992d85` "Bonnet-to-wing shut: one shared line, the nose corner, and the shell tube in
the gap" indicates this was subsequently done, with the shared line in `blender/data/shut_bonnet_wing.json`. Not
verified by me.

---

## 7. Where the project went after my commits — OTHER-SESSION, not verified here

Recorded so this document is not read as current state.

`CLAUDE.md` and `docs/REPLICA_PLAN.md` show the body has since moved to a **FreeCAD character-line network →
NURBS surfaces → panels** approach (approved by Nik 2026-10-27, DECISIONS (16)). FreeCAD 1.1.4 at
`D:\FreeCAD\bin\freecadcmd.exe` with the Curves workbench installed. 96 curves fitted
(`blender/data/cad/lines_v2_fit.json`); ten lines listed as still too wobbly to surface on.
The numpy build described in §3 is kept **for comparison only** and is not to be patched further except glass.

That supersedes the FreeCAD failure in §4: at ~20 sections with identical point counts and the Curves workbench
installed, it works.

---

## 8. Uncertainties and assumptions

- **No part of the current body has been exported or driven.** The installed AC package
  (`content/cars/vauxhall_nova_gte_1989`) is the Phase 1 block-out from 12 October. Everything in §3 is
  geometric and photographic evidence only.
- **Camera accuracy is the floor on photographic comparison.** 2.5–7 mm median mark error means a 5 mm panel
  disagreement is at the edge of what the photographs can settle.
- The `cS` camera barely moved in the re-solve, so belt, cant, arch and flare measurements taken from it stand.
  `cCF`, `c22` and `c20` moved 16–30 mm, so anything derived from them — bonnet centreline points, the nose
  corner, the wiper pivot / `scuttle_curve`, the bonnet creases, `front_end.py`'s lamp panel, the hatch glass —
  **should be re-measured**. Not done.
- **ESTIMATE:** the rear panel's centreline profile is interpolated between four measured heights
  (TL_BI 0.562 → y0 1.736; plate 0.668 → 1.731; TL_TI 0.804 → 1.732; HG_B 0.900 → 1.640). The shape between them
  is assumed smooth.
- **ESTIMATE:** `A_WRAP = 0.88`, `P_WRAP = 6.4` in `y_face(x) = 1.735 − 0.88·|x|^6.4` reproduce the four
  triangulated tail-lamp corners to 2–8 mm, but the exponent is fitted, not measured.
- **Unresolved, logged at the time:** the GA screen header reads z 1.29 against BA `WS_T` 1.269 (the drawn line
  may be the rubber or the frit), and the GA backlight edge at z 1.20 reads x 0.49 against BA `HG_T` 0.525.
- **Unverified claim:** the AMD RX 6700 XT reports 4 GB VRAM to Windows; I believe the card is 12 GB but did not
  confirm it.

---

## 9. Outstanding tasks

Body (now on the FreeCAD track — see `docs/NEXT_WEEK.md` for the full argument):

1. **Zebra / strip-light inspection.** The one tool both the replica plan (4.2) and Nik's docx brief call for and
   that does not exist. FreeCAD's ZebraTool (Curves WB, installed) works on the NURBS face before meshing. Do it
   **before** surfacing — it is what judges whether the line network is fair enough, and it tests surface flow,
   which silhouette overlays cannot.
2. **Cross-sections** (roof crown, tumblehome, belt, shoulder, bonnet, tailgate) from the GA front/rear views and
   the photographs. DECISIONS (19) records that the network has the flank and ends but **no sections**. This is
   the direct answer to "silhouette matches but it still isn't a Nova".
3. **One fixed-view regression sheet** — seven views (front, rear, L, R, top, two three-quarters), clay, same
   lens, plus the strip-light pass, run after every change. Pieces exist (`render_rect.py`, `ortho_views.py`,
   `match_look.py`); they need joining into one command.
4. **Per-image reference log** — view, lens/perspective, what each photo can constrain, confidence. Prevents a
   perspective photo being used as an elevation again.
5. **Ask Nik for a walkaround video** of his own car plus fixed-distance side/front/rear stills. Would make
   photogrammetry viable as a cross-check on our own solve. Caveat: dark gloss paint and glass are hard for it;
   reference, not geometry. No ffmpeg on this PC.

Still not built at all: interior, engine bay, scuttle louvres, badges, wipers, wheel-arch liners.

Infrastructure:

6. **Blender MCP add-on is behind** (protocol 11 vs 15). `uvx mcp-for-blender install-addon`, restart Blender.
7. **Comfy MCP** is installed and registered but has no ComfyUI workspace — see `comfy-mcp-reminder` memory;
   Nik asked to be reminded Monday 2026-11-02.

---

## 10. File paths

**Written or substantially changed this session**

| Path | What |
|---|---|
| `tools/gen/rebuild_body.sh` | the whole-body build chain (12 steps) |
| `tools/gen/roll_edges.py` | rolls every open edge into a return |
| `tools/gen/shut_lines.py` | door and tailgate shut lines as grooves |
| `tools/gen/add_glass.py` | glass derived from each aperture's rebate |
| `tools/gen/add_rear_end.py` | imports bumper, valance, plate lamp, tail lamps, rear panel |
| `tools/gen/frame_guides.py` | moves the wheel/axle guides onto the BA frame |
| `tools/windows.py` | both side-window outlines → `blender/data/windows.json` |
| `tools/tail_lamps.py` | lamps on the GA band heights → `blender/data/tail_lamps.json` |
| `tools/rear_panel.py` | the whole tailgate → `blender/data/rear_panel.json` |
| `tools/cmp_stack.py` | photo-over-model comparison stacks |
| `tools/photomatch/ba2.py` | re-solve with a robust loss and optional free principal point |
| `tools/photomatch/ba_loo.py` | leave-one-photo-out validation |
| `tools/photomatch/bp_on_photo.py` | **drawing + measured points onto a photo through its own camera** |
| `tools/photomatch/marktiles.py`, `marksheet.py` | pixel-gridded mark tiles and audit sheets |
| `tools/photomatch/plate_corners.py` | sub-pixel number-plate corners (520 × 111 mm anchor) |
| `tools/photomatch/seed_cam.py`, `ruler.py` | seed a new camera; mm ruler drawn onto a photo |
| `docs/STATUS_FOR_CHAT.md` | standalone briefing for chat mode |
| `docs/NEXT_WEEK.md` | what the two external briefs add |

**Key data and references**

- `tools/photomatch/ba_result.json` — 34 triangulated points + 7 cameras (re-solved)
- `tools/photomatch/BACKUP_ba_result_stale_2026-10-12.json` — the stale solve
- `tools/photomatch/body_profile.json` — photo-frame profile; **model z = photo z + 0.0193**
- `blender/data/windows.json`, `tail_lamps.json`, `rear_panel.json`, `side_profile.json`
- `blender/data/BACKUP_blueprint_frame_2026-10-26/` — pre-fix traces
- `reference/blueprints/GA_rear_elevation.jpg` — the factory rear elevation (§2.2)
- `blender/BACKUP_nova_proc_before_frame_fix_2026-10-26.blend`
- `docs/DECISIONS.md` entries 2026-10-27 (9), (10), (11)

**Elsewhere**

- `D:\Claude\reports\AI_Mod_Development_Methods_Audit_Claude_2026-10-28.md` — cross-project methods audit
  (32 methods, 31 failures, with coverage register)
- `C:\Users\nickl\.claude\plugins\data` → junction to `D:\ClaudeData\plugins\data` (C: was down to 3.5 GB);
  old copy kept as `plugins\data_BACKUP_before_move_to_D`

---

## 11. Rules confirmed this session

- **Cross-check the drawing against the photograph through the solved camera before trusting either.** This
  caught §1.4 immediately and would have caught §1.1 weeks earlier.
- **A check that compares the model to the number it was built from proves nothing.** Reading the bonnet's height
  on the centreline agreed to 5 mm while the panel was 25 mm out.
- **Quote a number with a unit, or do not claim a match.**
- **Build features as rows of a swept section; do not cut across a finished grid.**
- **Choose the parameterisation per region, not per car.**
- **A generated mesh is a sketch, never a measurement.**
- **Never boolean an open surface.**
- **When Nik's eye and my overlay disagree, his eye has been right every time so far** (windscreen height, arch
  shape, wing quality).
