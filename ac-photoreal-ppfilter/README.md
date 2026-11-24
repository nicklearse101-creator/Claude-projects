# PhotoReal ppfilter (Assetto Corsa + CSP + Pure)

A photo-realistic post-processing filter built on Pure's own `pure` filter.
Pure's files are **not** stored here. `make_photoreal.py` reads `pure.ini` and
`pure_scripts/pure.lua` from the AC install and writes patched copies:

- `system/cfg/ppfilters/PhotoReal.ini`
- `system/cfg/ppfilters/pure_scripts/PhotoReal.lua` (Pure loads the script with the same name as the filter)

Run `python make_photoreal.py` again after every Pure update.

Two filters are generated:
- **PhotoReal**: with the camera-look colour LUT ("camera look" 0.8).
- **PhotoReal Grain**: the same filter with camera sensor grain instead ("camera look" 0, "grain" 1.0, "grain size" 0.35). It uses Pure's Spice sensor noise, driven from the script's `update_SPICE(ctrl, dt)` hook, so the grain is strongest in dark areas like a real sensor. Raise "camera look" to combine both techniques.

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
| Camera look (v2.3, new slider) | none | 0.8: colour LUT from `make_lut.py` (film S-curve, olive foliage, slightly muted sky, warm highlights, whites stay white); written to `extension/textures/color_grading/PhotoReal.png` |
| Shadow depth (v2, new slider) | none | 0 by default (0.2 crushed foliage to black); raises sun-to-shade contrast in direct sun only |

## Using it

1. Content Manager > Settings > Assetto Corsa > Video > Post-processing: set the filter to **PhotoReal**. Weather FX must be **Pure**.
2. In-game, open the **Pure PP** app from the right-edge app bar, then **Script > Style** to fine-tune the sliders live ("photo-realistic", "photo saturation", "photo warmth", "shadow depth", "camera look", tonemapping).
3. Tune against real reference photos of the same track, time of day and weather.

## Status

- v1: car looked good in-game on rt_macau; scenery still looked game-like (mostly track assets and midday light).
- v2.0: haze + shadow depth. Haze overrode `ac.setFogDistance` from the script; in-game it put a blue veil over everything (cockpit included). Don't override Pure's fog from the ppfilter script.
- v2.1: haze removed, shadow depth kept. In-game: shade too dark.
- v2.2: user-tuned defaults: photo-realistic 0.75, shadow depth 0. Looked right in-game on rt_macau (2026-11-24).
- v2.4: added the PhotoReal Grain variant. Not yet checked in-game.
- v2.3: camera-look colour LUT (`lut_preview.jpg`: top is before, bottom is after, applied to a v2.2 screenshot). Not yet checked in-game.
- Distance blur was considered and left out: no depth buffer in Pure's ppfilter script hook, and real cameras keep distance sharp anyway.

## CSP / AC settings

Tried with Extra FX (SSLR, ASSAO, SS lighting), a bigger shadow map and bigger cubemaps, then cheaper variants. Rain at 4K dropped to 40-53 fps. On 2026-11-24 the user chose to restore their original CSP/video settings and use only the ppfilter. The filter needs no special CSP settings beyond Pure as the Weather FX.
