# AC wiper toolkit

Tools for adding working windscreen wipers to Assetto Corsa cars (CSP). They read and write the game's own `.kn5` models and `.ksanim` animations directly. You don't need Blender or the AC SDK.

Proven on 8 WTCC cars (2026-11-04). See `AC_Wiper_Project_Report.md` for what worked, what failed and why.

## Requirements
- Python 3.10+ and **numpy**. If numpy isn't installed globally: `pip install --target <folder> numpy`, then run with `PYTHONPATH=<folder>`.
- Keep all four `.py` files in the same folder (the helpers load `ac_wiper.py` from beside themselves).
- Close the car in Content Manager or the AC showroom before writing to its files.

## Files

| File | Purpose |
|---|---|
| `ac_wiper.py` | The main tool. Commands are listed below. It also works as a library: kn5 reader, transform helpers, ksanim writer. |
| `centre.py` | For a single wiper: works out a **central** pivot (same depth below the glass edge as the original), the park turn, the axis and the mirror sweep. Prints the `rigid` arguments. |
| `find_wiper.py` | Finds wipers **merged into other meshes** (long, thin, loose parts at the base of the windscreen). |
| `outline.py` | Prints the windscreen's real **outline** (bottom edge, pillar edges). Use it for placing pivots instead of guessing. |

## `ac_wiper.py` commands (recommended)

| Command | What it does |
|---|---|
| `tree CAR.kn5` | Lists every node and mesh with its material and world bounds. Start here: `tree CAR.kn5 \| grep -i "wip\|wind\|glass\|parabr"` |
| `fitaxis CAR.kn5 --wiper A[,B] --glass G [--glass-zmin 0.3] --pivot-end max-x --sweep 85` | Finds each wiper's rotation axis (tilt and lean) that keeps the **blade** closest to the glass over the sweep. It also says where the blade would leave the windscreen, and prints arguments ready for `rigid`. |
| `rigid CAR.kn5 --wiper A[,B] --glass G --tilt T --lean L --sweep ±S --pivot-end max-x --out animations/car_wiper.ksanim` | **The method that works.** Animates each wiper as **one solid piece**: a sweep about the pivot, plus a whole-wiper tilt on every frame so the blade stays near the glass. It keeps the node's own scale, rebuilds from `.bak_wiper` each run, and self-checks by replaying the written frames. |
| `rigid ... --offset dx:dy:dz --park-rot deg --park-axis tilt:lean` | Moves the wiper first (e.g. to the centre) and turns its park position. This writes only that node's matrix into the kn5. |
| `extract CAR.kn5 --mesh M --keep-box x0:x1:y0:y1:z0:z1 [--drop-box ...]` | Cuts a merged wiper out of a bigger mesh into its own `wiper` node (same material) and deletes other merged parts. It saves `.bak_original`. |
| `transplant CAR.kn5 --donor OTHER.kn5 --wiper wiper --material "<target material>" --offset dx:dy:dz` | Copies a wiper from another car into one that has none, using one of the target's own materials (choose one with the same shader and texture as the donor's). It saves `.bak_original`. |

Older commands: `fit` and `check` (first-generation mirror fit), and `bend`, which is **deprecated**: it cuts the wiper into hinged pieces, which looks broken in-game.

## Workflow for a new car
1. Run `tree`. If there is no wiper node, run `find_wiper.py CAR.kn5 <windscreen>`. Then use `extract` (wiper merged into a mesh) or `transplant` (no wiper at all).
2. Single wiper: `centre.py CAR.kn5.bak_wiper wiper <glass> 0.3 max-x`, then paste the printed `RIGID ...` args into `ac_wiper.py rigid`.
   Two wipers (tandem): `fitaxis ... --sweep 85`, then `rigid` with the printed args and `--sweep -85`.
3. Check the `rigid` output. The blade is typically within ±5–30 mm of the glass, and `replay error` should be 0.000 mm.
4. Write `extension/ext_config.ini`:
   ```ini
   [WIPERS_TRACE_...]
   SURFACE = <windscreen mesh>
   WIPERS = <wiper mesh(es)>
   ```
5. Check in-game. The sweep angle and placement are the user's call. Rerun with only `--sweep`, `--offset` or `--park-rot` changed.

## Conventions worth knowing
- Coordinates: +y is up, +z is forward, and **+x is the car's left**.
- `--pivot-end max-x` means the hub is at the wiper's +x end. Check that against the `tree` bounds.
- A negative `--sweep` usually means "up the glass". `fitaxis` and `centre.py` print the correct sign.
- Every write keeps backups: `.bak_wiper` is the base `rigid` rebuilds from, and `.bak_original` is the untouched model where geometry was changed. To undo, copy a backup back over the `.kn5`.
