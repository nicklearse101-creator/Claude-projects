# Shell map - reference body (Nik's Novamodel, scaled and edited)

Model: `export/ref/nova_ref.blend`, object `REF_BODY` (scaled to the FIA dimensions, arches moved to the photo-traced
arches, see DECISIONS 2026-10-19). Map overlay in Blender: collection `SHELL_MAP` (coloured outlines + labels, hidden
in renders). Pictures: `docs/shell_map.jpg` (all views) and `export/ref/scan/MAP_<view>.jpg` (full size).

**Coordinates** - car frame, metres: **x +** = car's left (UK passenger side), **y -** = towards the front,
**z** = height above the ground. Front axle y -1.1715, rear axle y +1.1715. Nose y -1.842, tail y +1.780.

**How it was measured** - ray-scanned depth maps at 2.5 mm from the left, right, front, rear and top
(`blender/scripts/scan_shell.py`); shut lines = grooves deeper than their 1 cm surroundings, openings = rays that pass
into the cabin (`tools/map_features.py`, about +-3 mm); small details read off orthographic cavity renders with a
measured grid (`blender/scripts/render_cavity.py`, `tools/map_grid.py`, about +-1 cm). Every outline was drawn back on
the true-scale views and checked (`tools/map_draw.py`). Left and right sides measure the same to the millimetre
(door lines, windows, arches) - the model is symmetric apart from the items marked R only.

## Glass and openings
| Feature | Where | State in the model |
|---|---|---|
| Windscreen | base y -0.69 / z 0.93 (x +-0.65), header y -0.27 / z 1.29 (x +-0.54) | **solid surface** with horizontal striation artefacts |
| Door glass | y -0.22 to +0.415, z 0.855 to 1.235 (both sides) | **open** (no glass) |
| Front vent glass | triangle from the A-pillar (y -0.68, z 0.86) to the division bar at y -0.24, up to z 1.15 | **open** |
| Quarter glass | y 0.62 to 1.20 at the top / 1.36 at the base, z 0.883 to 1.22 | **open** |
| Tailgate glass | x +-0.545, z 0.92 to 1.28 (plan: y 1.305 to 1.60) | **open** |
| Sunroof | - | **not modelled** (the real GTE has one) |

## Panels and shut lines
| Feature | Where |
|---|---|
| Doors | front shut line **y -0.678**, rear **y +0.455** (both sides, all heights), bottom **z 0.288**, frame top z 1.27; A-pillar edge from (y -0.678, z 0.87) up to the roof |
| Bonnet | shut lines to the wings **x +-0.63**, front edge **y -1.68 (z 0.70 at the centre)**, rear edge at the scuttle **y -0.87** |
| Bonnet creases | two lengthways creases from x +-0.41 (front) to +-0.48 (rear) |
| Transverse bonnet line | y -1.27 between the creases - **not on the real car** |
| Front wings | wing crease / step line z 0.71 (y -1.60 to -0.85) |
| Rear quarters | swage line rising from z 0.70 (y 0.90) to 0.765 (y 1.60) |
| Tailgate | side shut lines **x +-0.565**, lower edge z 0.575 (on the bumper top), top under the roof spoiler (z ~1.30) |
| Roof | y -0.27 to 1.18; drip rails x +-0.59; two lengthways ribs x +-0.39 |
| Roof spoiler | y 1.18 to 1.32, x +-0.47 |
| Scuttle | vent grille + wipers y -0.82 to -0.71, x +-0.47 |

## Bumpers, sills, arches
| Feature | Where |
|---|---|
| Front bumper | face at y -1.84, top **z 0.53**, red-stripe ribs z 0.50-0.56, lower lip z 0.19-0.26; wraps the sides to the arch (y -1.48) |
| Front plate recess | x +-0.25, z 0.33-0.45 (plate text garbled) |
| Front air slots | x +-0.25 to +-0.34, z 0.36-0.40 (either side of the plate) |
| Tow-eye cover | x -0.49 to -0.39 (car's right), z 0.30-0.38 |
| Rear bumper | top **z 0.576**, ribs z 0.52-0.55, body down to z ~0.39, grey valance z 0.19-0.36; wraps to the arch (y 1.47) |
| Rear bumper fittings | x +0.53..+0.57, z 0.35-0.41 (car's left); x -0.47..-0.54, z 0.32-0.37 (car's right, probably the fog lamp) |
| Side skirts | between the arches, bottom z 0.19, top z 0.288 (door bottom), sill groove z 0.236; kicks up ahead of the rear arch (y 0.50 -> 0.81, up to z 0.40) |
| Front arch | y -1.48 to -0.833, top z 0.64 (photo-traced) |
| Rear arch | y 0.81 to 1.47, flat top z 0.58 (photo-traced) |
| Exhaust | pipe under the car's left side; tailpipe x +0.51..+0.60, z 0.26-0.33, y ~1.62-1.70 |

## Lamps and front
| Feature | Where |
|---|---|
| Headlamps | x +-0.405 to +-0.624, z 0.524-0.674, front face y ~-1.79 |
| Front indicators | x +-0.624 to +-0.698, same height, wrapping round to the side (y -1.82 to -1.66) |
| Grille | x +-0.39, z 0.53-0.665, horizontal slats, GTE badge x +-0.09 / z 0.565-0.607 |
| Griffin badge | bonnet nose, x 0, z 0.73-0.755 |
| Tail lamps | x +-0.565 to +-0.68, z 0.565-0.82 (horizontal divisions), wrapping to the side y 1.60-1.68 |
| Side repeaters | front wings, y -0.80 to -0.755, z 0.725-0.755 (both sides) |

## Side and tailgate details
| Feature | Where |
|---|---|
| Mirrors | x +-0.65 to +-0.84, y -0.53 to -0.40, z 0.88-0.97 |
| Door handles + lock | y 0.31-0.40, z 0.75-0.80; lock barrel at y 0.35 / z 0.70 |
| GTE door decal | y -0.65 to -0.39, z 0.43-0.49 (raised lettering) |
| Tailgate handle bar | x +-0.31, z 0.772-0.817 |
| Tailgate lock / badge | x 0, z 0.85-0.90 |
| Rear GTE badge | x +0.36 to +0.54 (car's left), z 0.76-0.80 (lettering mirrored) |
| Rear plate recess | x +-0.25, z 0.626-0.748 (text mirrored) |
| Fuel flap | **right side only**: y 1.40-1.46, z 0.62-0.68 - behind the rear arch; on the real car it is ahead of it (y ~0.85-0.90, side photo) |
| Round fitting | **right side only**, B/C-pillar y 0.49-0.53, z 1.00-1.04 - unidentified, not on the real car |

## Inside (seen through the openings)
Front seats with headrests, rear seat, dashboard, steering wheel and the interior mirror (x +-0.11, z 1.16-1.21) are
modelled; no glass separates them from the outside.

## What this means for the AC build
- Glass must be added: door, vent, quarter and tailgate apertures are empty; the windscreen surface needs replacing
  (striations) - outlines above.
- No materials: paint, black trim (window frames, vent bar, scuttle, grille), grey (skirts, valances), lamps, plates
  all have to be assigned - the outlines above are the zones.
- Model-only artefacts to remove or correct: transverse bonnet line, fuel flap position, the round B/C-pillar fitting,
  mirrored/garbled lettering on the plates and badges (use decals instead).
- Sunroof is missing (standard on the GTE).
