# Reverse engineering AC cars: complete write-up (9-10 November 2026)

This is everything we have achieved so far in the Blender Work project: what we learned, what worked, what we
dropped, the techniques that made the difference, and where every file is on the PC and on GitHub.

**The goal:** build accurate Assetto Corsa cars from scratch (exterior, interior, everything) from pictures and
dimensions, for our own cars (Nova GTE, Sunbeam, Escort and future ones).

**The route:**
1. Learn how professional AC cars are built.
2. Prove we can rebuild a car when the original is there as a guide (the "method test", on the Kunos AE86).
3. Do the same from photos.

**Nik's rule:** other cars are for learning technique only, never a base mesh or a shortcut.

---

## Quick map: where everything is

| What | On the PC | On GitHub (private repo `nicklearse101-creator/Claude-`) |
|---|---|---|
| Project folder (code + reports) | `D:\Claude\Claude-\blender\kn5-study\` | `blender/kn5-study/` |
| **Start here (next session)** | `D:\Claude\Claude-\blender\kn5-study\NEXT_SESSION.md` | `blender/kn5-study/NEXT_SESSION.md` |
| The working method + lessons | `...\kn5-study\PANEL_FIT_TECHNIQUE.md` | `blender/kn5-study/PANEL_FIT_TECHNIQUE.md` |
| Story so far (short report) | `...\kn5-study\ACHIEVEMENTS_REPORT.md` | `blender/kn5-study/ACHIEVEMENTS_REPORT.md` |
| Full results log | `...\kn5-study\REPLICA_PLAN.md` | `blender/kn5-study/REPLICA_PLAN.md` |
| 112-car study reports | `...\kn5-study\KN5_STUDY.md`, `REPORT.md`, `REPORT_PHASE2.md`, `REPORT_PHASE3.md` | same names in `blender/kn5-study/` |
| Tools / environment notes | `...\kn5-study\HANDOVER.md` | `blender/kn5-study/HANDOVER.md` |
| Research reports | `D:\Claude\Claude-\blender\research\reports\` | `blender/research/reports/` |
| Research notes (raw) | `D:\Claude\Claude-\blender\research\research_notes\` | `blender/research/research_notes/` |
| Blender modelling research | `D:\Claude\Claude-\blender\research\Blender car modelling techniques.md` | `blender/research/` |
| Useful GitHub projects found | `D:\Claude\Claude-\blender\research\github_finds.md` | `blender/research/github_finds.md` |
| This write-up | `D:\Claude\Claude-\blender\REVERSE_ENGINEERING_WRITEUP.md` | `blender/REVERSE_ENGINEERING_WRITEUP.md` |
| Work files, builds, pictures (NOT in git) | `D:\Claude\_scratch_research\kn5_study\` | - (game data and renders stay local) |
| Comparison pictures | `D:\Claude\_scratch_research\kn5_study\images\` | - |
| Regression builds (door, wing, quarter) | `D:\Claude\_scratch_research\kn5_study\regress\` | - |
| Study .blend (AE86 vs 205) | `D:\Claude\_scratch_research\kn5_study\kn5_study_AE86_vs_205.blend` | - |
| Temp files | `D:\ClaudeData\tmp\` (nothing on C:) | - |
| FreeCAD 1.1.4 + CurvesWB | `D:\FreeCAD\`, add-ons in `D:\ClaudeData\FreeCAD\Mod` | - |
| The AE86 used for the method test | `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ks_toyota_ae86` | - |

**Public copy:** a cleaned mirror is published automatically to `github.com/nicklearse101-creator/claude-projects`
(local clone `D:\Claude\claude-projects`), same paths (`blender/kn5-study/...`). Emails, server addresses and decrypted
Kunos/mod car data are removed.

Git history for this work: `git log -- blender/` in `D:\Claude\Claude-` (about 30 commits, 9-10 Nov).

---

## 1. Phase 1-3: how AC cars are built (112 cars)

**What we did:** read 112 cars straight from their game files with our own kn5 reader: 67 Kunos, 29 mods,
12 single-seaters and open cars, 3 traffic cars, plus our Nova. We measured each against published dimensions
and graded how it is built.

**Accuracy findings**
- Kunos cars are within about 1 % of the real car: wheelbase median 2 mm off; length ±26 mm, width ±36 mm.
- Height always reads low (AC ride height), which is expected.
- Mods are about 4x less accurate and use about 2x the triangles.
- The spec check catches real mod errors (Clio track width, Kadett).
- Same car by different authors: outlines agree to about 10 mm.

**The Kunos recipe (confirmed on all 67 Kunos cars)**
- Half the car modelled and mirrored exactly; 89-94 % quads.
- Painted shell 20-35k triangles on an 18-27 mm grid; edge loops follow the features, not even stations.
- Whole car about 242k triangles (AE86).
- Shut lines: about 5 mm turned-in return, 3-4 mm gap, darkened by AO baked into a white skin texture.
- One "unfolded car" 2048² paint sheet; the paint normal map is damage only.
- Glass is tiny (door glass 41 triangles); a separate "mask" mesh carries the black print. Two-layer glass.
- Lamps, grilles, badges and trims are separate meshes. Interior = baked AO x tiling detail texture.
- Standard dummy names; LODs at 22 % / 7 % / under 1 %.
- Single-seaters: rigid suspension parts animated with `car_susp_XX.ksanim`, about 13 % hard edges.
- Kunos bends the vertex normals of shut-line returns by 25-45° to make them look soft (found 10 Nov).

**Our Nova block-out:** dimensions exact, construction fails the recipe (about 30x the paint triangles, no skin
UVs, no LODs).

**Tools built (work on any car)** - all in `blender/kn5-study/`:

| Tool | Does |
|---|---|
| `kn5full.py` | Reads any kn5 (meshes, normals, UVs, materials, textures) |
| `analyze.py` | Construction summary of a car |
| `measure.py`, `specs.json`, `compare_specs.py` | Dimensions vs published specs (`specs.json` built from Wikipedia) |
| `survey.py` | Construction scorecard |
| `silhouette.py` | Side/top/front outline comparison between two models |
| `section.py`, `construction_sheet.py` | Cross-sections and construction sheets |
| `shape_rules.py`, `fairness.py` | Shape rules and fairness measures |
| `uv_sheet.py` | UV / skin layout sheets |
| `blender_import.py` | Imports a car into Blender in about 3 s |
| `phase3/` | The 112-car batch scripts (fetch specs, parse, aggregate) |

Results: `blender/kn5-study/results/` (e.g. `aggregate_112.json`, `spec_table.md`, `survey.json`).
Reports: `KN5_STUDY.md`, `REPORT.md` (AE86 vs 205), `REPORT_PHASE2.md` (8 more cars), `REPORT_PHASE3.md` (112 cars).

---

## 2. What a replica needs: blind tests on the AE86

| Test | Result | Lesson |
|---|---|---|
| Rebuild from perfect side/top/front outlines (`blind_test.py`) | 8.5 mm median, 56 % within 10 mm | Outlines alone can never make a replica |
| + section shapes learned from 11 other cars | 6.0 mm median, 63 % within 10 mm | Still not enough |
| Lines -> surface (`lines_to_surface.py`): panel outlines + creases + soft feature lines + a few sections | 1.1 mm median, 87 % within 3 mm | **A replica = accurate character lines + good surfaces between them** |
| Outlines + creases only, on 17 cars | 0.65 mm median | Confirms it |

Patch-layout study (`panel_study.py`, `results/panel_study_*.json`): the shell is one mesh, doors / bonnet / hatch /
bumpers separate; panel edges are a 5 mm return, a 5 mm holding loop, then 10 mm; loops run round the arches and
parallel to every edge.

---

## 3. Approaches tried and dropped (and why)

| Approach | Files | Why dropped |
|---|---|---|
| Sectional loft from rays | `car_loft.py`, `step3_rebuild.py` | 3.3 mm median and lumpy |
| Panel height fields, quad-sphere | `step3b_panels.py`, `step3c_quadsphere.py` | Lumpy ("smoothing has never worked" - Nik was right) |
| Coons / Gordon curve networks | `coons_test.py`, `gordon.py`, `freecad_gordon_test.py` | About 1.7 mm; the Coons patch folded (a one-way score hid it) |
| Lofts | `panel_loft.py` | Not crisp |
| Whole-car "strip" builds v1-v5 (about 400 strips cut from the mesh) | `cad_panels.py`, `cad_build_*.py`, `cad_feature_grid.py` | Numerically fine (v5: 91 % within 3 mm, 0.11 mm median) but looked patchy: slivers, draped glass, no shut lines. Not how a modeller works, so useless for photos |
| Sorting triangles by curvature | - | Kunos's long thin triangles give jagged bands |

Two of our own mistakes caught on the way:
- The old scorer added about 1 mm of fake error to everything -> replaced by exact point-to-surface scoring
  (`score_exact.py`, `exact_dist.py`).
- The v4 edge clean-up silently deleted 6 % of the car -> caught and fixed.

The turn that mattered: **pivot to CAD-style building** (curves first, then exact surfaces), using FreeCAD 1.1.4
(OpenCASCADE kernel), found on Nik's PC and run headless from D: only (`fcrun.sh`).

---

## 4. The method that works: panel-fit CAD reverse engineering

Full method and every lesson: **`blender/kn5-study/PANEL_FIT_TECHNIQUE.md`**.
Code: `panel_fit.py` (fits, plain Python) -> `panel_fit_freecad.py` (trimmed CAD faces, STEP, display mesh, exact
normals, run through `fcrun.sh`) -> `strip_build.py` (thin strips) -> Blender.

**The idea in one line:** each panel is one smooth B-spline surface with as few control points as it needs, fitted
to the data and trimmed to its real outline; character lines are drawn as fair curves end to end and the surfaces
either side are cut exactly on the same curve - crisp edges and even surfaces by construction, no smoothing step.

### The techniques (what makes it work)

1. **Split like a modeller.** Hard creases (> 20°) -> separate regions. Inside a region, character lines from
   cross-sections every 20 mm (sharp turns over arms scaled to the region), each fitted as ONE fair curve. Strong
   lines get their own narrow fillet band.
2. **Fit to the vertices, not the facets.** Kunos vertices lie on the designer's surface (lower door skin 0.08 mm);
   the flat triangles between them are chords.
3. **Control count by blocked cross-validation.** Hold out whole 40 mm patches (checkerboard), search both
   directions independently (4..14). Random hold-outs let ripples through (zebra showed wood grain).
4. **Class-A rule:** the fairest surface within tolerance (smooth harder while within 25 % / 0.3 mm of the best fit).
5. **Trim to the real outline:** outline sides as 2D B-splines in the surface's own parameter space (fitted to the
   polyline resampled every 5 mm, never to sparse vertices).
6. **Cut bands on their character lines:** neighbours use the identical curve -> crisp line.
7. **Line pinning:** neighbouring bands averaged on their shared line and refitted (joins 0.3-2.3 mm -> 0.1-0.4 mm).
8. **Rolled edges built FROM the neighbour** (skin minus a drop profile, tangent by construction), not fitted freely.
9. **Wheel arches** (`:archN`): arch found automatically on the outline (AE86 front R 354 mm); the lip built as a
   "rail" along the whole opening edge, matched to the side faces; the wing split into sub-panels at the arch.
10. **Corner wraps** (`:wN`): a panel wrapping a corner is cut ONCE at 45°; the minor piece is fitted against the
    finished main surface and both are cut on one smooth seam curve.
11. **Thin strips** (`strip_build.py`, new 10 Nov late): narrow steps, returns and ledges are ruled surfaces between
    shared side curves; a side on a wide face IS that face's own built edge (refitted to 0.02 mm). Joins 0.00-0.01 mm.
12. **Every small face fitted** (`:rall`); the hole filler (`fill_holes.py`) is a safety net only, and it ignores
    Kunos chord sag (it used to lay bad patches over correct faces).
13. **Display:** even mesh (`MaxLength 6`) + **exact surface normals** + triangle winding matching those normals.
14. **Check by eye** in grey and zebra, same camera, side by side with the original - plus exact two-way scores.

### Results on the Kunos AE86 (method test)

| Panel | Faces | Area within 1 / 3 mm | Kunos vertices within 1 / 3 mm | Picture (local) |
|---|---|---|---|---|
| Glass (4 pieces) | 4 | areas match (door glass 0.349 = 0.349 m²), all within 3 mm | - | `glass_panelfit_zebra.png` |
| Door (skin, crease, groove, roll, frame, glass, mirror, trims) | 80 (21 strips) | **88.4 % / 99.7 %** | - | `door_complete_vs_original_grey.png`, `door_panelfit_vs_original_zebra.png` |
| Front wing (arch lip, sub-panels) | about 25 | 70.5 % / 96.1 % | **92.5 % / 99.3 %** | `wing_v4_zebra.png` |
| Rear quarter + C-pillar | about 40 (14 strips) | 78.3 % / 96.8 % | **86.3 % / 97.9 %** | `quarter_v2b_grid_grey.png`, `lamptop_strips_vs_kunos_grey.png` |
| Roof, bonnet, hatch, bumpers, sills | - | not started | - | - |

Pictures are in `D:\Claude\_scratch_research\kn5_study\images\` (local only: they include renders of the Kunos car).
The vertex score is the honest one: Kunos's 100-150 mm flat triangles cut chords across curves, so a correct smooth
surface reads as "off" between vertices on the area score.

Nik's verdicts: door - "oh my god that's a really good door"; rear quarter - "really fast and produced a really good
result".

### Progress over the two days (door within 1 mm)
71.9 % (first panel fit) -> 73.6 % (roll as true blend) -> 84.9 % (every face, returns) -> 87.6 % (Class-A rule)
-> 87.9 % (line pinning) -> 88.4 % (thin strips).

### Tools of the method (all in `blender/kn5-study/`)

| Tool | Does |
|---|---|
| `panel_fit.py` | Fits panels (spec syntax `:rN`, `:rall`, `:bN`, `:archN`, `:wN`; switches `PF_*`) |
| `panel_fit_freecad.py` | FreeCAD stage: trimmed faces, band cuts, strips, returns, STEP, display mesh, exact normals |
| `strip_build.py` | Thin-strip detection, spine, shared side curves |
| `re_fit_freecad.py` | FreeCAD approxSurface fallback |
| `fill_holes.py`, `merge.py` | Safety-net hole filler and merging its faces in |
| `score_faces.py`, `score_exact.py`, `exact_dist.py` | Exact area scores (within 1 / 3 mm) |
| `miss_map.py` | Area + vertex scores and side/top/rear miss pictures |
| `seams.py` | Gaps along joins between faces |
| `pack_build.py` | One npz (points, faces, exact normals) for Blender |
| `regress.sh` | Rebuild + score door, wing, quarter (~6 min) - run after every change |
| `fcrun.sh`, `fc_call.sh` | Headless FreeCAD on D:; calls to the live FreeCAD AI MCP |

How to run everything: `NEXT_SESSION.md` ("How to run").

---

## 5. Research done (deep-research reports)

| Report | Path (PC: `D:\Claude\Claude-\blender\research\`; GitHub: `blender/research/`) | Used for |
|---|---|---|
| How pros model cars in Blender | `Blender car modelling techniques.md` | Pivot to curves-first CAD building |
| Wheel arch lip surfacing | `reports/Wheel arch lip surfacing.md` (+ 3 notes in `research_notes/Wheel arch lip surfacing/`) | The arch / lip tool |
| Narrow strip surfacing between panels | `reports/Narrow strip surfacing between panels.md` (+ 3 notes in `research_notes/Narrow strip surfacing between panels/`) | The thin-strip builder |
| Useful open-source projects | `github_finds.md` | Background |

Key research findings applied: build strips on the panels' own edges (Alias Panel Gap, Geomagic/Várady pipeline);
ruled walls for flat steps, fillets for visible rolls; OpenCascade's `makeRuledSurface` keeps the edges it is given
and pairs rails by normalised parameter; industry joins are 0.01-0.001 mm, angle breaks under 0.1° invisible.

---

## 6. Lessons we paid for (the short list)

- Score exactly and both ways, and look in grey or zebra: point samples and one-way scores hid real problems.
- Kunos uses long thin triangles: classify with curves and sections, never per triangle.
- Fit to vertices, validate on held-out patches, never smooth as a "fix", never trim to a global smooth curve.
- Display meshes need even triangles + exact normals + correct winding, or reflections tear / faces go dark.
- Never fill "holes" that are only Kunos chord sag.
- FreeCAD closest-point lookups can return far local minima: cut curves at known parameters.
- `makeRuledSurface` automatic orientation can flip a rail: pass orientation 1.
- Everything runs on D:; FreeCAD only through `fcrun.sh`; game assets and renders never go in git.

The full list with dates is at the bottom of `PANEL_FIT_TECHNIQUE.md`.

---

## 7. What's next

From `NEXT_SESSION.md`:
1. Thin strips along several neighbours (the 1.4 m drip rail r7) as chains of curves; trim wide faces on curves
   fitted to the Kunos crease; fix `seams.py` for narrow strips.
2. Rear quarter and front wing leftovers (hairline by the lamp opening, sill notch, zebra on the wing top).
3. The rest of the body: roof -> bonnet -> hatch -> bumpers -> sills.
4. Assemble and mirror the whole car; final pictures per section.
5. Make it AC-ready: quad display mesh (~20 mm grid, 20-35k paint tris), unfolded skin UV, baked AO, LODs, dummies,
   two-layer glass.
6. Lamps, grille, badges, interior survey; then **from photos**, Nova first (solved cameras and traced windows exist).
