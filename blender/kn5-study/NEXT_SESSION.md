# Next session: Blender Work / AE86 replica (handover, 2026-11-09 night)

**Start here.**
1. Read `ACHIEVEMENTS_REPORT.md` (what's done and why).
2. Read `PANEL_FIT_TECHNIQUE.md` (the method that works).
3. Then follow the plan below.

Older background: `HANDOVER.md` (kn5 study tools and environment) and `REPLICA_PLAN.md` (the full
results log).

## Where we are
- The **panel-fit method** (fitted B-spline surfaces, trimmed to their outline, with character lines cut
  exactly) is proven on the AE86 **door** (8 faces) and **all glass** (4 pieces). Nik is happy with the
  door.
- It's a **method test**: the curves come from the real Kunos AE86. Later they will come from photos.
- The earlier whole-car strip build (`cad_panels.py`, v5) is superseded; use it only as a reference.

## How to run (Nik's PC, everything on D:)
```bash
cd /d/Claude/Claude-/blender/kn5-study
C=D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86
OUT=D:/Claude/_scratch_research/kn5_study/blind/door
python panel_fit.py $C $OUT GEO_extdoorL_SUB1:b0 GEO_extdoorL_SUB1:r1,2 GEO_extglassL   # fit (about 40 s)
PF_IN='D:\Claude\_scratch_research\kn5_study\blind\door' ./fcrun.sh panel_fit_freecad.py   # CAD faces, STEP, mesh
# then exact normals: PF.exact_normals(p, mesh points) -> panels_fit_normals.npz -> Blender (custom normals)
python score_exact.py BUILD.npz        # exact two-way score (strip grids); exact_dist.point_to_tris for meshes
```

**Spec syntax** (after the mesh name):
- `:rN`: the Nth crease region, as one surface.
- `:bN`: crease region N split into character-line bands.
- `:0,1`: connected pieces (glass).
- `:fall`: curvature pieces (experimental; don't use).

**Blender:**
- Collection `AE86_door_fit`: our faces `fit_*` and the originals `truth_*`, shown with the `zebra`
  material.
- Blender's Python has **no PIL**, so run the analysis outside Blender and load npz files inside.
- Hide whichever set you aren't looking at; objects in front of the camera spoil comparisons.

**FreeCAD:** run only through `fcrun.sh` (D: paths, CurvesWB in `D:\ClaudeData\FreeCAD\Mod`). Never
use C:.

## Plan (in order)

### A. Finish the door properly
1. **Bug Nik spotted (2026-11-09):** the narrow crease strip between the upper and lower door skin
   (`r2`) looks recessed on ours but stands out on the original.
   - Likely cause: the panel normal `w` in `frame_of` takes its sign from authored vertex normals, which
     can point inward on a narrow band, so the exact normals (and the shading) come out flipped.
   - Fix: orient `w` outward from the car (as in `cad_panels.skin_by_mesh`), then re-check the zebra
     and grey views.
   - If it's still recessed, compare its section with the original's (`section.py`).
2. **Window frame band (`b0`) and beltline roll (`b1`)** are about 1.5 mm p95, against 0.1–0.3 mm on
   the rest.
   - Try splitting the frame from the top of the roll.
   - Try building the roll as a true blend (tangent to both neighbours).
3. **Watertight joins:** each face's outline is currently fitted on its own (within 0.4 mm). Fit each
   shared boundary once, as a 3D curve, and use it on both faces.
4. **Shut-line returns:** use the measured recipe (about 5 mm return, 3–4 mm gap; bumpers about 20 mm).
   Build each return as a ruled or offset surface from the trimmed edge.
5. **Door parts** as separate meshes, as Kunos does: trims (`GEO_extdoorL_SUB0`), mirror, handle.

### B. Rest of the body, panel by panel (yes, the car is built in pieces)
Kunos: the shell is one mesh (`GEO_body`), and doors, bonnet, hatch and bumpers are separate. We
follow the same split, then split each panel into surfaces at creases and character lines.

- **Order:** front wing → rear quarter and C-pillar → roof → bonnet → hatch → front and rear bumpers
  → sills.
- **Known limit:** a panel that wraps more than about 70° (wing top into side, bumper corners) is not
  one height field over a plane.
  - Option 1: split at the wrap with a character line (preferred; it's what modellers do).
  - Option 2: add a parametric fit (parameters from a coarse base surface, then iterate).
- **Wheel arches:** the arch lip is a feature line, with the arch cut as an outline or opening.

### C. Assemble and check the whole car
- Mirror the left half to the right.
- Run exact two-way scores against the full skin.
- Zebra and grey views from all sides.
- One final picture per finished section, not progress shots (Nik's preference).

### D. Make it an AC-ready model
- **Display/export mesh:** sample each face as a **quad grid** in its parameter space following the
  Kunos recipe (about a 20 mm grid, 20–35k triangles on the paint, loops along the lines). Use exact
  normals.
- **Skin and setup:** unfolded skin UV, baked AO, LODs, standard dummy names, two-layer glass.

### E. Afterwards
- Lamps, grille and badges as parts.
- **Interior** survey and recipe (budget, modelled vs texture-only, AO).
- **From photos:**
  - trace outlines and character lines on photos and blueprints (Nova first; it already has solved
    cameras and traced windows);
  - run the same fit, trim and cut pipeline with a few sections;
  - check against the photos by eye.
- Parked: the steward app (`steward-app/PLAN.md`) and Nova grading ("not yet").

## Rules Nik has set (keep)
- **Drives:** everything runs on **D:**; nothing uses C:.
- **Communication:** short messages; at the end of each turn, say what was done and show one picture;
  judge matches by eye.
- **No smoothing "fixes".** Build crisp surfaces from curves.
- **Saving:** save to the Claude- repo, then commit and push after each step; the public copy updates
  itself.
- **Assets:** never commit game assets (kn5, textures, images of them are gitignored; the `images/`
  here are our own builds).
- **Blender work:** load the blender-* skills and use the blender-mcp tools (standing approval).
