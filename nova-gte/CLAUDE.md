# Vauxhall Nova GTE 1.6 (1989 spec) - Assetto Corsa car, built from scratch

## Goal
Build a complete Assetto Corsa car mod of the **Vauxhall Nova GTE 1.6, built to the 1989 model-year spec (UK-spec)**, modelled in Blender. No ripped or borrowed meshes from other games/mods. **AI-generated meshes from image-to-3D tools - Tripo, Meshy, or free open models such as Hunyuan3D / TRELLIS (e.g. run on Hugging Face) - generated from our own reference photos/blueprints are allowed** (Nik, 2026-10-13) - they still have to be scaled, aligned and checked against the photos and measured dimensions before use.

Target: exterior, interior, engine bay, sound and physics all faithful to the real car, in a **metallic gun-metal grey** paint.

"Perfect" is the end goal. We get there through milestones (see `docs/PHASES.md`), and **every milestone must leave the user with a car they can drive in AC.**

## Environment
- Windows PC. Assetto Corsa at `D:\SteamLibrary\steamapps\common\assettocorsa`
- Blender is installed. Blender MCP is an option the user wanted to try.
- Custom Shaders Patch (CSP) and Content Manager are in use.
- The car is for the user's own server ("Ratty's Racing").
- Workspace root: `D:\Claude\vauxhall_nova_gte_1989` (set up 2026-10-06, next to the user's Sunbeam and Escort projects in `D:\Claude`).

## Working rules
1. **Never invent numbers.** Every dimension and physics value must trace to `docs/SPEC_SHEET.md`, tagged SOURCED, ESTIMATE or PLACEHOLDER. Where the ini format allows it, add a comment with the tag.
2. **Conflicting sources:** record every value in the spec sheet, pick one, say why.
3. **Develop with a loose `data/` folder** (no `data.acd`) so files stay editable. Pack to `data.acd` only for release.
4. **Use git.** Commit per milestone. Log non-obvious choices in `docs/DECISIONS.md`.
5. **Never overwrite an existing car** in AC's `content/cars`. Deploy a copy via a script, and ask before replacing a same-named folder.
6. **Verify in-game after any geometry change** (wheel position in arch, ground contact, ride height) *before* tuning handling. Do not blame or tune handling while the wheels are in the wrong place.
7. **Do not port another car's values literally** (damping ratios, hardpoints, etc.). Derive from this car's own geometry and sourced specs. Other cars can be used as format references only.
8. **Judge handling with data, not guesses.** Use a CSP Lua telemetry logger (speed, inputs, per-wheel slip/load, suspension travel) and compare against the validation targets in the spec sheet.
9. **Keep screenshots to a minimum.** Rely on tool-call results and targeted checks, not a screenshot after every action.
10. **Only use skills/plugins the task actually needs.**
11. At each milestone report briefly: what changed, what is verified, what is not.
12. **Save everything to the D drive. Never write anything to C: ** - no files, scripts, renders, exports, caches or temp files (Nik, 2026-11-02). Put scratch work in `D:\Claude\_scratch_research\`, and point TEMP/cache paths at D: for any tool that supports it.

## What is decided vs still to confirm
Decided: 1.6 GTE built to the 1989 spec (Vauxhall's Oct 1988 brochure; car id `vauxhall_nova_gte_1989`), own build (AI image-to-3D generation - Tripo, Meshy, Hunyuan3D, TRELLIS etc. - allowed since 2026-10-13), gun-metal grey, high detail inside and out, **RHD (UK spec)**, **factory alloy wheels** (5J x 14, three-arm design, 175/65 HR14), **pre-facelift** body and interior, no ABS, sunroof fitted (standard on GTE), **free blueprints only (no paid services)**.

Still to confirm with the user:
- Engine sound source: real E16SE recordings vs a retuned stock bank as a placeholder.
- Paint: Steel Grey metallic as the period reference for gun-metal grey.

## Planned folder layout
```
nova-gte/
  CLAUDE.md
  docs/            SPEC_SHEET.md, PHASES.md, DECISIONS.md, EXPORT_NOTES.md
  reference/       photos/  blueprints/  manuals/  audio/
  blender/         nova_gte.blend  scripts/
  export/          FBX and KN5 outputs
  car/vauxhall_nova_gte_1989/     <- the AC car package
    data/          car.ini engine.ini power.lut drivetrain.ini suspensions.ini
                   tyres.ini brakes.ini aero.ini setup.ini ai.ini ...
    ui/            ui_car.json  badge.png
    skins/gunmetal_grey/
    sfx/
    animations/
  tools/           deploy script, validation/check scripts, telemetry app
```

## AC package conventions (verify before use)
These are from general AC modding knowledge and **must be checked against a stock Kunos car opened in ksEditor** before the scaffold is finalised. Record the result in `docs/EXPORT_NOTES.md`.
- Model node names believed to be needed: `WHEEL_LF/RF/LR/RR`, `SUSP_LF/RF/LR/RR`, `DISC_LF/RF/LR/RR`, `STEER_HR`, `COCKPIT_HR`.
- Blender FBX export settings (axes, scale, apply transforms) are **not assumed**. Determine them in Phase 1 with a test model and write them down.
- LOD files, collider, `ui_car.json`, skin preview and sound `GUIDs.txt`/bank: copy structure from a stock car, do not guess.

## Who does what
**Claude in the claude.ai chat** (research and drafting, no access to the PC): spec research, reference planning, drafting ini/lut data from sourced figures, sound plan, script drafting, reviewing screenshots and logs the user pastes in.

**Claude Code** (on the user's PC): running Blender and scripts, building the model, writing the car package, deploying to AC, running checks.

Anything produced in chat should be saved into `docs/` or `tools/` so Claude Code picks it up.

## How to work on the model (Nik, 2026-10-19 - read this first)
- The job is to make the model look like the pictures. LOOK at the reference pictures and compare.
- Use a plain grey model (no paint colours) next to `reference/photos/grey_studio/{side,front,rear}.png` at the same
  scale, cropped close on the area being fixed (`blender/scripts/grey_views.py` + `tools/compare_grey.py`; blueprint
  overlays in Blender: `blender/scripts/blueprints_ref.py`). Read positions off the picture and move the model to them.
- If it visibly differs from the picture, it is wrong - don't argue from numbers or camera projections.
- One area at a time, checked close up in Blender, then show Nik. No smoothing/denoise/pipeline "fixes".

## Current status
- **2026-10-27 (latest): APPROVED by Nik - `docs/REPLICA_PLAN.md` is the plan (body moves to a FreeCAD
  curve-network -> NURBS model, scripts in `tools/cad/`; trim colours allowed as separate parts; pre-facelift detail
  from the photos). Decisions: DECISIONS.md 2026-10-27 (16). Feature list: `docs/DETAIL_MAP.md`.
  FreeCAD 1.1.4 at `D:\FreeCAD\bin\freecadcmd.exe` + Curves workbench. Do not patch the numpy shell further
  (except glass) - it stays only for comparison.**
- **Character-line network (REPLICA_PLAN step 4), DECISIONS (19)-(21):** `tools/cad/lines_v2.py` ->
  `blender/data/cad/lines_v2.json` (v1 + GA end/plan traces + part outlines + photo marks), fitted fair by
  `D:\FreeCAD\bin\freecadcmd.exe tools/cad/run_fc.py` (env NOVA_LINES=lines_v2.json; runs build_curves.py) ->
  `lines_v2_fit.json` + `cad/nova_lines_v2.FCStd`. Checks: `check_lines.py`, `check_swing.py`, `fairness.py`.
  GA traces: guides in `tools/cad/trace_spec.json`, `trace_view.py` (DP tracer). Photo marks: `tools/photomatch/
  epi.py` + `marks_v2.py` (point features only). Blender view: `blender/nova_lines_v2.blend` (CAD_LINES_V2).
  Next: re-trace/fair the 10 lines still wobbly (list in (21)), measure spoiler / C-pillar / screen header, then
  surfaces. Lines must be fair before any surface is built on them (Nik, 27 Oct).**
- **The numpy build (kept for comparison until the FreeCAD body beats it): the body is built from the measurements - photogrammetry (`tools/photomatch/`) and traced
  drawings (`blender/data/*.json`) - by `sh tools/gen/rebuild_body.sh` -> `blender/nova_proc.blend`. Meshy is gone
  and must not be used, not even as a ruler. (The old "shell only" rule is lifted for trim colours - (16).)
  Method: build parts the way `tools/front_end.py` builds the bumper (one section swept along a measured path,
  features as rows, edges rolled). Latest reasoning: newest entries at the bottom of `docs/DECISIONS.md`.**
- Bonnet-to-wing shut done 2026-10-27 (12)-(13): shared shut line and cross-slope in
  `blender/data/shut_bonnet_wing.json`, wing flush with the bonnet, gutter under the gap (`add_shut_gutter.py`).
  (14): A-pillar hole closed, banding fixed (B-spline fit of the bonnet_shut trace, `tools/gen/trace_fit.py`),
  shoulder crease given an angle change (shape estimate). Left: sliver at the bonnet V corner, door shut behind wing.
- (15): door mirrors (`add_mirrors.py`) and the GTE wheels (`add_wheels.py` -> blender/scripts/build_wheels.py) are
  on the measured car. Next faults seen: door window too short at the front (should run along the A-pillar to the
  mirror), front tyre 0.3 mm from the shell's front arch edge, no wheel-arch liners.
- Not built yet: interior, engine bay, scuttle louvres, badges/wipers. The installed AC
  car (20 Oct) is the old reference-model build; physics `data/` is still the Phase 1 skeleton.
- `docs/MESHY_REBUILD_PLAN.md` is historical (Meshy route, superseded 2026-10-26).
- Phase 1 done (box car drove, 12 Oct). Phase 2/3 in progress: shell refit to the photos, front end rebuilt as
  separate generated parts and corrected against the photos (12 Oct evening, see DECISIONS.md), interior first pass.
- Nik (12 Oct): the model overall still needs fixing section by section after the front - side/arches, rear end,
  roof/glass, wheels, then interior. Check each section against the photos with the matched cameras
  (`blender/scripts/render_matched.py`, `lookdev.py`) before moving on.
- How to build/export/deploy: docs/EXPORT_NOTES.md. Deploy only with tools/deploy.py (archives the installed copy).

## Body-kit / sill / arch method (added 2026-11-02)
For flared sills, wheel arches, skirts or any crisp swept body-kit part, read `docs/RING_LOFT_BODYKIT_METHOD.md` first (ring-loft technique proven on the Escort NICK3 kit; scripts in `D:\Claude\_tools\ring_loft_bodykit\`).
