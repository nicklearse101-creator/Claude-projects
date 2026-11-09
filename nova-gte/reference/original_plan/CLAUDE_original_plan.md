# Vauxhall Nova GTE 1.6 (1990) - Assetto Corsa car, built from scratch

## Goal
Build a complete Assetto Corsa car mod of the **Vauxhall Nova GTE 1.6, 1990 model year (UK-spec)**, modelled entirely from scratch in Blender. No imported, ripped or borrowed meshes.

Target: exterior, interior, engine bay, sound and physics all faithful to the real car, in a **metallic gun-metal grey** paint.

"Perfect" is the end goal. We get there through milestones (see `docs/PHASES.md`), and **every milestone must leave the user with a car they can drive in AC.**

## Environment
- Windows PC. Assetto Corsa at `D:\SteamLibrary\steamapps\common\assettocorsa`
- Blender is installed. Blender MCP is an option the user wanted to try.
- Custom Shaders Patch (CSP) and Content Manager are in use.
- The car is for the user's own server ("Ratty's Racing").
- Workspace root: not decided yet. On first run, propose a path **outside** the AC install (e.g. `D:\mods\nova-gte`) and confirm with the user.

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

## What is decided vs still to confirm
Decided: 1.6 GTE, 1990, built from scratch, gun-metal grey, high detail inside and out.

Confirm with the user before relying on them:
- **RHD (UK-spec)?** Assumed yes.
- **Pre- or post-1990 facelift look?** The Corsa A was facelifted in 1990 and the Nova likely changed too. Needs reference photos of a genuine late GTE.
- **Wheels/tyres and exact GTE trim items:** read from reference photos, not memory.
- **Engine sound source:** real E16SE recordings vs a retuned stock bank as a placeholder.

## Planned folder layout
```
nova-gte/
  CLAUDE.md
  docs/            SPEC_SHEET.md, PHASES.md, DECISIONS.md, EXPORT_NOTES.md
  reference/       photos/  blueprints/  manuals/  audio/
  blender/         nova_gte.blend  scripts/
  export/          FBX and KN5 outputs
  car/vauxhall_nova_gte_1990/     <- the AC car package
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

## Current status
- Phase 0 in progress. Spec research started in chat (`docs/SPEC_SHEET.md`). Gear ratios, final drive, tyre size, brake sizes, track widths and spring/damper rates are **not found yet**.
- Reference pack not collected yet.
