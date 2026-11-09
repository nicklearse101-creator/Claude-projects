# Vauxhall Nova GTE 1.6 (1989) — Assetto Corsa mod: where the model stands

**Written 2026-10-27** as a briefing for Claude in chat mode, which has no access to the PC.
Everything below is the exterior body only. Physics, interior, sound and the AC package are untouched since
Phase 1.

---

## 1. The goal and the rules

Build a complete AC car mod of the **Vauxhall Nova GTE 1.6, 1989 UK spec** (RHD, pre-facelift, sunroof,
factory 5J×14 three-arm alloys, 175/65 HR14), modelled from scratch in Blender, in metallic gun-metal grey.
Workspace `D:\Claude\vauxhall_nova_gte_1989`, git repo, Blender 5.2.1.

Standing rules that matter for anyone advising on this:

- **Never invent numbers.** Every dimension traces to `docs/SPEC_SHEET.md`, tagged SOURCED / ESTIMATE /
  PLACEHOLDER.
- **Judge by eye against the pictures**, not by projected numbers — a matched camera can be locally wrong.
- **Cross-check the blueprints against the photographs** before trusting either (this has already caught two
  real errors, see §4).
- **Meshy is dead.** The body once came from a Meshy image-to-3D shell. It is deleted from the blend and must
  not be used for anything, not even as a comparison ruler.
- Shell only — no painting, texturing or exporting to AC unless asked.

---

## 2. How the car is built now

One command rebuilds the whole body from the measured data:

```
sh tools/gen/rebuild_body.sh
```

which runs, in order:

| step | script | what it makes |
|---|---|---|
| 1 | `rebuild_sill.py` | rocker + GTE grey sill skirt |
| 2 | `rebuild_bonnet_drawn.py` | bonnet (centre ridge, two lengthwise creases, front V) |
| 3 | `rebuild_scuttle_drawn.py` | scuttle between bonnet and screen |
| 4 | `rebuild_wing_drawn.py` | front wing, with its own rolled arch lip |
| 5 | `add_rear_end.py` | rear bumper + valance, tail lamps, tailgate panel |
| 6 | `build_shell2.py` | the body shell: a loft of measured cross-sections along the car |
| 7 | `fit_shell.py` | culls shell faces that the separate panels cover |
| 8 | `cut_apertures2.py` | wheel arches, side windows, windscreen, backlight |
| 9 | `roll_edges.py` | turns every open edge back under itself |
| 10 | `shut_lines.py` | door and tailgate shut lines, as real grooves |
| 11 | `add_glass.py` | glass in every aperture |
| 12 | `organise.py` | sorts into NOVA_NEW / NOVA_OLD / NOVA_GUIDES, hides the last two |

Result: **37 parts in `NOVA_NEW`**, output `blender/nova_proc.blend`.

### The measurement sources

Everything is built from two kinds of measurement, never from guesses:

**Photogrammetry** (`tools/photomatch/`). Seven photographs of three real GTEs, with 34 points triangulated
across them by bundle adjustment (`ba.py`, now `ba2.py`) — lamp corners, indicator corners, grille corners,
door handle, side repeater, every window corner, the screen and hatch glass corners. Anchors are the known
wheelbase and tracks, the 520 × 111 mm number plates and the tyre radius. Output `ba_result.json`.

**Traced drawings** (`tools/trace_*.py`). The 4-view line blueprint (side elevation) and a photographed
factory GA sheet, rectified (`rectify_ga.py`) to give the plan view and front elevation. Output
`blender/data/*.json`.

The frame: car faces −Y, Z up, +X is the car's left, origin on the ground midway between the axles
(y = ±1.1715). Photo-frame z is on loaded tyres; the model is on unloaded ones, so **model z = photo z +
0.0193**. That 19.3 mm offset has bitten more than once.

---

## 3. The technique that works, and why it matters

The front bumper and grille look right and the rest of the car did not. The reason turned out to be
structural, not cosmetic, and it is now the guiding principle:

**`tools/front_end.py` builds the bumper as one cross-section swept along a measured plan path.** The section
has about forty rows and every feature of the part is one of them — seven rows over the 50 mm top roll, five
rows per rib groove, exact rows at the plate recess edges, eight rows down the tucked-in lower face. The first
and last rows are **returns**: the surface turns back behind itself, so the part has no raw edge anywhere.
Features fade in and out along the path with smoothstep blends, never step.

Everything else was a plain surface with holes cut through it afterwards. A cut goes **across** the rows, so
its edge is a staircase of whatever cells it landed in, and the panel is a single skin with a raw boundary —
which is exactly what reads as paper.

Three things have been brought over to the bumper's way of working:

- **Every open edge is rolled** (`roll_edges.py`). For each boundary vertex a frame is built on the surface —
  normal, boundary tangent, and the in-surface direction pointing into the opening — and a small section is
  swept along the boundary. Arch lips roll over and turn back into the wheel well; window and screen openings
  step back into the rebate the glass sits in; the floor edge folds inboard. Edges that butt against another
  panel are found with a BVH and get a shut return instead, which opens a real gap.
- **The window apertures are rows of the section, not cuts across it** (`build_shell2.py`). The glass band
  starts exactly on each window's lower edge and ends on its upper one wherever a window exists. Aperture
  error against the triangulated glass corners went from 10–100 mm to 13–23 mm and the staircase is gone.
- **Shut lines are grooves with walls** (`shut_lines.py`), made the way the grille groove is made — the traced
  line sampled onto the body with a five-row section laid across it.

---

## 4. Two measurement errors found and fixed (2026-10-27)

These matter because they invalidate a lot of earlier comparison work.

**(a) A 30.5 mm frame error between the drawings and the photographs.** Every line traced off a blueprint was
pinned to axles at y −1.141 / +1.202 (a phase-1 frame derived from FIA overhangs), while `body_profile.json`,
every solved camera and the whole photogrammetry frame use the wheelbase midpoint at ±1.1715. So anything from
a drawing sat 30.5 mm along the car from anything from a photograph, and the two could never be reconciled.
Traces re-pinned, wheel and axle guides moved, calibration corrected; old files kept under
`blender/data/BACKUP_blueprint_frame_2026-10-26/`.

**(b) The camera solve was stale.** `ba_result.json` predated the last edit of the marks, so it was not the
solution of its own observation file. Re-solving with a robust loss drops the worst camera from 18.6 px RMS to
12.3. Consequences: **the windscreen corners came down about 30 mm** — which is what Nik had said by eye — and
the lamp points moved 11–17 mm forward. Median mark error now 2.5–3.3 mm on the best four photographs, 4.8 on
the rear, 5.7 on the front, 7.0 on the side. A fuller camera model (free principal point + k2, testing the
"cropped photo" theory) was tried and **rejected** — it buys 12% of the cost and asks for principal points up
to 1000 px off centre, which is fitting noise.

**A third, found by cross-checking:** the triangulated door-glass rear corners (DG_RT, DG_RB) sit in the
middle of the B-pillar, about 55 mm behind the glass edge that the blueprint and the photograph agree on. They
are the one pair only two near-parallel cameras see. They are no longer used; the side windows are built from
the traces (`tools/windows.py`). Also worth knowing: **the 4-view line blueprint has no rear elevation of our
car** — the bottom-right view on that sheet is the saloon. The factory GA sheet does have one
(`GA_rear_elevation.jpg`), and it dimensions the tail lamp's colour bands at **800 / 745 / 685 / 635 mm** above
the ground. Its 800 mm lamp top agrees with the triangulated 804, so both sources describe the same lamp, and
the lamp now uses the drawing's heights.

---

## 5. What is built

- Front end (bumper with ribs and red GTE inserts, grey chin lip, plate recess, lamp panel, grille surround +
  insert + groove, headlamps, wrap-round indicators) — **this is the good part**
- Bonnet with its centre ridge and two lengthwise creases
- Scuttle
- Front wings with rolled arch lips and the shoulder step
- Body shell: flanks, belt shoulder, glass band, frame/drip, roof arch, rear face
- Rocker and GTE sill skirt
- Rear end: bumper + valance, tail lamps with four colour bands, full tailgate panel with the black GTE panel
  and number plate, plate lamp
- Wheel arches, both side windows, windscreen and backlight, all cut and rolled
- Glass in all five apertures
- Door front, door rear and tailgate shut lines

## 6. What is not built

- **Door mirrors** — nothing at all
- **Wheels and tyres** — placeholder cylinders in renders only, no wheel in the blend
- Interior, engine bay
- Scuttle louvres (removed when the scuttle was rebuilt, never redone)
- Backlight recess and roof visor
- Badges, decals, wipers, aerial, fuel filler

## 7. Known faults, in order of how bad they look

1. **The bonnet-to-wing shut is 7–10 mm wide and opens to about 40 mm at the nose**, against roughly 4 mm on
   the car. This is the big dark gash across the front wing. Three causes found; two fixed (a doubled gap
   allowance, and a 160 mm running average left over from when the bonnet was Meshy-derived and lumpy). The
   remaining cause: the wing's top edge is a *resample of the bonnet's mesh* rather than the bonnet's own
   curve. **The fix is to give the bonnet and the wing one shared shut-line curve** so the gap is 4 mm by
   construction. This is the next job.
2. The windscreen aperture's lower edge is stepped where it crosses the shell's stations — the screen is not
   yet grid-aligned the way the side windows now are.
3. The wing's lower front corner has a notch by the indicator.
4. No mirrors and no wheels, which is most of why renders still read as unfinished.

---

## 8. Checking tools (all of these exist and work)

- `tools/gen/geo_check.py` — distance from each of the 34 triangulated points to the model surface; glass
  corners are measured to the aperture **edge**, not the nearest panel
- `tools/gen/match_overlay.py` + `tools/overlay_edges.py` — model outline drawn in cyan on each photograph
  through that photograph's own solved camera
- `tools/gen/match_look.py` — the model rendered glossy red under a sky through a solved camera, which is what
  makes creases and panel breaks visible; a clay render shows none of them and has misled more than once
- `tools/photomatch/bp_on_photo.py` — **the cross-check tool**: traced drawing lines and measured points drawn
  onto a photograph through its solved camera
- `tools/photomatch/marktiles.py`, `marksheet.py` — pixel-gridded tiles for placing and auditing marks
- `tools/gen/ortho_views.py`, `tools/cmp_stack.py` — orthographic views, photo-over-model stacks

## 9. Recent commits

```
ceb21d1  Close analysis of the front wing: measure the bonnet shut, fix the glass fan
6214652  Shut lines, glass in every aperture, and fix the hole under the scuttle
9188ce5  Roll every open edge, make the window apertures rows of the section
09e6e41  Fix the two frame errors, trace the windows properly, build the rear end
edbbe92  Shell rebuilt from measured sections; bonnet length, scuttle and screen base fixed
```

Full reasoning for every decision is in `docs/DECISIONS.md`, newest entries at the bottom
(2026-10-27 (9), (10), (11)).

---

## 10. If you are advising on this

The useful questions are about **method**, not about numbers — the numbers are all measured and recorded.
Specifically:

- How should two adjacent panels share a shut-line curve so the gap is constant by construction? (Fault 1.)
- Is a station loft along the car the right structure for a car body at all, given it cannot represent a
  vertical rear face — the tailgate had to be built as a separate panel for exactly this reason?
- Is there a better way to get an aperture's edge onto the grid than forcing section rows onto it?
- Door mirrors and wheels are the next visible wins. The wheels are a known part: 5J × 14 three-arm GTE alloy,
  175/65 HR14, unloaded radius 291 mm.
