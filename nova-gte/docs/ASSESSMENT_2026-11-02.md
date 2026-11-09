# Technical assessment — 1989 Vauxhall Nova GTE, 2026-11-02

Required first deliverable, answering the six questions. Read-only inspection; no model or project file was
changed to produce this. Labels: **VERIFIED** = measured or read this session; **FILE** = read from the repo;
**ESTIMATE** / **HYPOTHESIS** as stated.

---

## 1. Current state of the model

**Two parallel bodies exist. This is the single most important thing to know.**

| | Numpy build | FreeCAD curve network |
|---|---|---|
| File | `blender/nova_proc.blend` (2.8 MB, 27 Oct 14:32) | `cad/nova_lines_v2.FCStd`, viewed as `blender/nova_lines_v2.blend` (27 Oct 19:26) |
| What it is | a complete, closed body: shell, bonnet, wings, scuttle, sills, rear end, bumpers, lamps, glass, mirrors, wheels | **96 fitted B-spline curves only** — a wire frame, no surfaces |
| Status | **kept for comparison only**; not to be patched further except glass (Nik, DECISIONS (16)) | the approved route forward |

**FILE.** `CLAUDE.md` and `docs/REPLICA_PLAN.md` record Nik's approval on 2026-10-27 to move the body to a
FreeCAD character-line network → NURBS surfaces → panels. Decisions (16)–(21). That supersedes the numpy build.

**What is genuinely finished and should be retained** (answers Priority 6 — very little needs rebuilding):

- The **photogrammetry foundation**: 7 solved cameras, 34 triangulated points, re-solved 27 Oct with a robust
  loss. Median mark error 2.5–3.3 mm on Nik's four photographs, 4.8 mm rear, 5.7 mm front, 7.0 mm side.
- **Every traced drawing** in `blender/data/` — they are now curve inputs.
- The **measurement frame**: all six drawing views resampled into one world frame at 500 px/m
  (`tools/cad/views.py`, `reference/views/*.png`, `frame.json`), verified by overlaying the model on all six.
- The **front bumper, grille, lamp panel and indicators** (`tools/front_end.py`) — built by the right method
  already (one section swept along a measured path); Nik has repeatedly called these good.
- The **GTE wheels and door mirrors** (`add_wheels.py`, `add_mirrors.py`), both on measured positions.
- The **AC export chain**: own KN5 writer, collider, deploy script.
- The **check tools**: `geo_check.py`, `match_look.py`, `overlay_edges.py`, and critically
  `tools/photomatch/bp_on_photo.py`.

Nothing in the list above should be discarded. The only thing being abandoned is the numpy *surfacing* method.

---

## 2. Most important inaccuracies

### 2.1 The curve network is not fair enough to surface on — VERIFIED (measured this session)

Measured from `blender/data/cad/fairness_v2fair.json`, 96 curves:

- wiggles per metre: **median 3.2**, but **18 curves over 8/m**
- wobble from a fair reference of itself: median 1.9 mm, 1 curve over 10 mm

Worst offenders:

| Curve | wiggles/m | wobble | length | Note |
|---|---|---|---|---|
| `a_pillar` | **92.9** | 0.0 mm | 0.56 m | wobble 0 — so this is *oscillation with no amplitude*, i.e. a numerical artefact of the fit, not a bent line |
| `bonnet_v` | 34.4 | 0.0 mm | 0.61 m | same signature |
| `dlo_top#2` | 42.9 | 0.5 mm | 0.07 m | 70 mm fragment — too short to mean anything |
| `window_door` | 11.6 | **4.1 mm** | 2.01 m | real, and long: this one matters |
| `centre_screen` | 10.3 | **5.6 mm** | 0.65 m | real |
| `part_plate_f_1` | 10.7 | 6.5 mm | 0.62 m | `model_parts` group — reference only, not a line to surface on |
| `shut_door_rear#2` | 12.5 | 3.2 mm | 0.32 m | real |
| `crease_rear` | 10.9 | 1.9 mm | 0.92 m | real |

**HYPOTHESIS, and the first thing to test:** the headline "18 curves over 8/m" overstates the problem. Curves
with high wiggles/m but ~0 mm wobble are ringing in the fit, not a wobbly line, and several others are fragments
under 100 mm. The genuinely unfair, surfaceable lines look to be about five: `window_door`, `centre_screen`,
`shut_door_rear#2`, `crease_rear`, and `centre_bonnet` (5.5 mm wobble). That should be confirmed before any
re-tracing effort is spent.

### 2.2 No cross-sections exist — FILE, and the most consequential gap

DECISIONS (19) records that the network has the flank and the ends but **no sections**. There is no roof crown,
no tumblehome, no belt or shoulder section. This is the direct cause of the complaint that has run through the
whole project: *the side profile overlays the blueprint closely and the car still does not read as a Nova.*
A silhouette constrains the outline; only sections constrain the crown between the outlines.

### 2.3 The plan view disagrees with the model at the nose — FILE (DECISIONS (18))

Overlaying the current model on all six drawing views showed the **plan view's nose is rounder and narrower at
the front corners than the model's**. Noted as "the first thing the curve network has to fix, and one the side
views could never show".

### 2.4 Unresolved source conflicts — FILE (DECISIONS (20), (21))

| Feature | Conflict |
|---|---|
| Screen header | GA reads z 1.29, BA `WS_T` reads 1.269 (21 mm). The drawn line may be the rubber or the frit. |
| Backlight edge at z 1.20 | GA x 0.49 vs BA `HG_T` 0.525 (35 mm) |
| Front bumper face | FIA overhang puts it at y −1.8415; `BUMPER_F` reaches −1.815 (**27 mm short**) |
| Tail length | GA side view reads ~25 mm long against the BA tail lamps and the FIA rear overhang |
| Spoiler y | still an ESTIMATE; sits slightly high against the rear photograph |

### 2.5 Measurements that should be re-derived — VERIFIED (flagged 27 Oct, not yet done)

The 27 Oct re-solve moved cameras `cCF`, `c22` and `c20` by 16–30 mm on the car. Anything derived from them
should be re-measured: bonnet centreline points, the nose corner, the wiper pivot / `scuttle_curve`, the bonnet
creases, `front_end.py`'s lamp panel, the hatch glass. `cS` barely moved, so belt, cant, arch and flare stand.

### 2.6 Not dimensional, but blocking release

The last installed AC package (20 Oct) is the Phase 1 block-out, and `docs/REPLICA_PLAN.md` 4.8 records it was
**1.3 M triangles / 47 MB — far too heavy for online racing**. Nothing of the current body has ever been
exported or driven.

---

## 3. References available to correct them

**Dimensional, SOURCED** — `docs/SPEC_SHEET.md`: length 3622, wheelbase 2343, height 1365, tracks 1320/1307,
width 1532, front/rear overhang 670/609 (FIA A-5375), 175/65 R14 unloaded radius 291 mm.

**Drawings** — all six views already in one world frame at 500 px/m (`reference/views/`, `tools/cad/frame.json`):

| Source | Gives | Caveat (FILE) |
|---|---|---|
| Line blueprint, hatchback side | side silhouette, openings, shut lines | **2.4 % short in the overhangs** — 3539 mm vs 3622. Shape only; size from the spec sheet. |
| Line blueprint, hatchback front | width, tracks | — |
| Factory GA side / front / rear / **plan** | plan shape, apertures, hard points | ~2.5 % residual distortion; the sheet disagrees with itself (front elevation's 1532 marks read 1572 on its own track scale). Each axis of each view carries its own scale. |
| `GA_rear_elevation.jpg` | **tail-lamp band heights 800 / 745 / 685 / 635 mm**, rear track 1307 | its 800 mm lamp top agrees with triangulated `TL_TI` at 804 mm |

**Trap, VERIFIED:** the 4-view blueprint's bottom-right view is the **saloon rear**, not ours. Only the top two
views are the hatchback.

**Photographic** — 7 solved cameras; 69 photographs in `reference/photos/` (35 of Nik's own car) plus
`commons2/` pre-facelift Sport/SR/L hatchbacks (same body, no GTE kit). High-resolution unused: the 4298 px
commons rear, 4896 px `Vauxhall_Nova_GTE.jpg`.

**Known-unreliable, VERIFIED:** `DG_RT` / `DG_RB` land ~55 mm behind the real glass edge (two near-parallel
cameras only). `MIR`, `BON_F`, `PNL_B` are single-view; `DSR_B` has weak depth. Do not build to these.

---

## 4. Recommended modelling approach

**Keep the approved hybrid. Do not restart, and do not revert to polygon modelling.**

1. **Primary surfaces: NURBS in FreeCAD**, driven by the measured character-line network, G1 across shared
   boundaries. This is already approved and the tooling is built and tested (FreeCAD 1.1.4 + Curves workbench;
   Gordon surfaces, Sweep2Rails, blendSurface, ZebraTool all verified headless on 27 Oct).
2. **Panels** split from the surfaces on projected shut lines — so the gap is constant *by construction*. This
   is the direct fix for the bonnet-to-wing gash, where two panels each fitted themselves to the other's mesh
   and a 4 mm gap became 7–40 mm.
3. **Hems, flanges, trim, glass and all detail: Blender**, swept along the trimmed edges. Filleting a thin
   panel gave an invalid solid in the FreeCAD test, so these are swept sections, not fillets.
4. **Keep `front_end.py` as it is.** It is already the right method and is the one part Nik approves of.

**Why not the alternatives:** a single polygon mesh is what produced every ripple-and-patch cycle in this
project; subdivision rounds off the crisp creases a Nova is recognised by; and image-to-3D was tried and deleted
(4.3 mm RMS lumps, worst 78 mm).

**Do not surface until the lines are fair.** A wobble in a line becomes a ripple in the panel — that is the wing
banding all over again.

---

## 5. Proposed validation procedure

Run all five after every change; a change that improves the numbers but looks wrong is wrong.

| Check | Tool | Pass condition |
|---|---|---|
| Distance to every two-view BA point | `geo_check.py` / FreeCAD `distToShape` | ≤ 5 mm median, none over 10 mm (**now: 9.3 mm median, 16 points over 15 mm**) |
| Overlay on all six drawing views | `tools/cad/overlay.py`, `render_rect.py` | within one drawing line (~5 mm) between the axles; overhangs from GA/FIA, never the line blueprint |
| Render through each of the 7 solved cameras beside its photograph | `match_look.py`, `overlay_edges.py` | silhouette and every panel line within ~5 px |
| **Surface flow — the missing check** | zebra stripes: FreeCAD `ZebraTool` on the face, strip lights in Blender on clay | no waves, steps or kinks except the real creases |
| Nik's eye, close up, one area at a time | — | it looks like his car |

Two standing rules, both earned: **cross-check the drawing against the photograph through its solved camera
before trusting either**; and **a check that compares the model to the number it was built from proves nothing**
(reading the bonnet height on the centreline agreed to 5 mm while the panel was 25 mm out).

---

## 6. Next concrete modelling task

**Triage the 18 unfair curves, then add the missing cross-sections — in that order, before any surfacing.**

Specifically, and in this sequence:

1. **Separate real unfairness from fit artefacts** (§2.1). Classify each of the 18 by wobble amplitude and
   length; expect ~5 genuinely bad lines rather than 18. Cheap, and it decides how much re-tracing is needed.
2. **Re-trace or hand-fair those few** against the photographs with the DP tracer.
3. **Add the cross-sections** — roof crown, tumblehome, belt, shoulder, bonnet, tailgate — from the GA front and
   rear elevations and the photographs (`lines_v2` → `v3`). §2.2. This is the highest-value geometric work
   outstanding.
4. **Build the zebra/strip-light check** (§5) and run it on the curve network's curvature strips before any
   surface exists.
5. Only then: first surface patch, on the flank, where the evidence is strongest.

I have **not** started step 1 — see the note below.

---

## Status of this session

Nik's usage limit was reached while this assessment was being prepared. What is done: the read-only inspection
and this document, including the fairness measurement in §2.1, which is new this session. What is **not** done:
any modelling, the triage in step 1, and the geo_check re-run (the 9.3 mm figure in §5 is quoted from
`docs/REPLICA_PLAN.md`, not re-measured today). Nothing in the model or any existing project file was changed.
