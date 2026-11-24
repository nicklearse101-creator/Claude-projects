# PhotoReal ppfilter (Assetto Corsa + CSP + Pure)

A photo-realistic post-processing filter built on Pure's own `pure` filter.
Pure's files are **not** stored here. `make_photoreal.py` reads `pure.ini` and
`pure_scripts/pure.lua` from the AC install and writes patched copies:

- `system/cfg/ppfilters/PhotoReal.ini`
- `system/cfg/ppfilters/pure_scripts/PhotoReal.lua` (Pure loads the script with the same name as the filter)

Run `python make_photoreal.py` again after every Pure update.

## What it changes from `pure`

| Area | Pure | PhotoReal |
|---|---|---|
| "photo-realistic" slider default | 0.5 | 1.0 (camera-style exposure metering, more bloom, Uchimura-AgX tonemap) |
| Saturation (new slider) | none | 0.92, luminance kept |
| Warmth (new slider) | none | 1.00 (red/blue balance, 0.9 to 1.1) |
| Lens ghosts at full photo-realism | 1.00 | 0.35 |
| Afterimage at full photo-realism | 3.00 | 1.00 |
| Chromatic aberration | off | subtle (0.0015 lateral) |
| Vignette | 0.001 | 0.15, FOV dependent |

## Using it

1. Content Manager > Settings > Assetto Corsa > Video > Post-processing: set the filter to **PhotoReal**. Weather FX must be **Pure**.
2. In-game, open the **Pure Config** app > PP tab to fine-tune the sliders live ("photo-realistic", "photo saturation", "photo warmth", tonemapping).
3. Tune against real reference photos of the same track, time of day and weather.

## Status

Version 1: generated and Lua syntax-checked; not yet checked in-game.
