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
| "photo-realistic" slider default | 0.5 | 0.75 (camera-style exposure metering, more bloom, Uchimura-AgX tonemap; 1.0 crushed shade) |
| Saturation (new slider) | none | 0.92, luminance kept |
| Warmth (new slider) | none | 1.00 (red/blue balance, 0.9 to 1.1) |
| Lens ghosts at full photo-realism | 1.00 | 0.35 |
| Afterimage at full photo-realism | 3.00 | 1.00 |
| Chromatic aberration | off | subtle (0.0015 lateral) |
| Vignette | 0.001 | 0.15, FOV dependent |
| Shadow depth (v2, new slider) | none | 0 by default (0.2 crushed foliage to black); raises sun-to-shade contrast in direct sun only |

## Using it

1. Content Manager > Settings > Assetto Corsa > Video > Post-processing: set the filter to **PhotoReal**. Weather FX must be **Pure**.
2. In-game, open the **Pure PP** app from the right-edge app bar, then **Script > Style** to fine-tune the sliders live ("photo-realistic", "photo saturation", "photo warmth", "shadow depth", tonemapping).
3. Tune against real reference photos of the same track, time of day and weather.

## Status

- v1: car looked good in-game on rt_macau; scenery still looked game-like (mostly track assets and midday light).
- v2.0: haze + shadow depth. Haze overrode `ac.setFogDistance` from the script; in-game it put a blue veil over everything (cockpit included). Don't override Pure's fog from the ppfilter script.
- v2.1: haze removed, shadow depth kept. In-game: shade too dark.
- v2.2: user-tuned defaults: photo-realistic 0.75, shadow depth 0. Looked right in-game on rt_macau (2026-11-24).
- Distance blur was considered and left out: no depth buffer in Pure's ppfilter script hook, and real cameras keep distance sharp anyway.
