# Blueprints

Nik supplied these 2026-10-26.

## Factory general-arrangement drawing (the important one)
`opel_corsa_a_cc_gsi_GA_drawing_full.jpg` and the close-ups of it
(`GA_side_elevation*.jpg`, `GA_front_elevation*.jpg`, `GA_rear_elevation.jpg`, `GA_drawing_small.jpg`).

Adam Opel AG, **Typ Corsa-A-CC GSI**, drawing `ZI.185.712/1-I/8-1990`, Pruef-Nr. F/7059/90, drawn
14.11.1990, approved stamp 14.11.1990, sheet no. 49689. Orthographic side, front, rear and plan views
plus a brake schematic, steering-wheel variants and the wheel table.

Dimensions printed on it:

| | mm |
|---|---|
| Wheelbase | 2343 |
| Length | 3622 (Ausf. X3758) |
| Height | 1365 |
| Width | 1532 |
| Track front / rear | 1320 / 1307 |
| Front view, ground to ? | 695 |
| Rear view, ground to lamp functions | 800 / 745 / 685 / 635 |

Every one of these matches `docs/SPEC_SHEET.md` already, which is a good independent check on the FIA
A-5375 figures: 3622 length, 2343 wheelbase, 1532 width, 1365 height, 1320 front track. The rear track
reads **1307**, which settles the 1300 vs 1307 question in the spec sheet in favour of 1307.

Wheels on the drawing: 4 1/2 J x 13 ET49 (RONAL 90 135 773) and **5 J x 14 ET49** (90 223 744, GE/HN,
RONAL/IMSA) with 165/65 R14 78S - the GTE wheel, confirming the spec sheet.

Caveat: this is the **CC GSI** sheet dated Nov 1990, so it is the facelift car. The hard points (wheelbase,
track, length, height, width, glass and door apertures) carry over, but bumpers, lamps and grille do not -
our car is pre-facelift. Use it for the side profile, apertures and hard points, not for the front or rear
end detail.

## Other
`corsa_a_4view_blueprint.gif` - a clean 4-view line blueprint (3-door 3622 / 2343 / 1365 / 1532 / 1320 /
1300 and a 4-door-ish 3955 variant below it). Good for overlaying; no provenance, so treat it as secondary
to the factory sheet.

## Calibration of the line blueprint, and what it is good for (2026-10-26)

`corsa_a_4view_blueprint.gif`, side elevation. Its own dimension extension lines sit at px 31 (nose),
145 (front axle), 582 (rear axle) and 691 (tail), the drawn ground line at py 266, and a circle fit to
the front tyre gives centre (146.4, 210.3) r 54.3 px.

One scale fits almost everything:

| | px | at 5.36156 mm/px | printed / known |
|---|---|---|---|
| wheelbase | 437 | 2343 | **2343** |
| front tyre radius | 54.3 | 291 | 291.5 (175/65 R14, unloaded) |
| ground to roof | 254.6 | 1365 | **1365** |
| overall length | 660 | 3539 | **3622** |

So the drawing sits on unloaded tyres like the model and needs no dz, and the only figure that does not
fit is its own overall length - it is **83 mm short**, all of it in the overhangs.

That is the drawing's error, not the spec's. On the factory GA sheet the two dimension arrows measure
918 px and 588 px, a ratio of 1.561 against the 1.546 that 3622/2343 demands - right, within the
keystone of a photographed sheet - while this line drawing's 660/437 = 1.510 is 2.4% out.

**Use it for shape and for anything between the axles; do not take overall length or overhang from it.**
Independent agreement with `tools/photomatch/body_profile.json`, which never saw this drawing:

| | blueprint | photos | diff |
|---|---|---|---|
| door shut lines | -0.648 / +0.500 | -0.670 / +0.465 | 22 / 35 mm |
| crease height | 0.70..0.76 | 0.747 | - |
| rear arch crown (flat top) | 0.553 | 0.577 | 24 mm |
| front arch crown | 0.652 | 0.641 | 11 mm |
| rear of body | +1.786 | +1.766 | 20 mm |

`tools/trace_side.py` pulls the side's lines off it into `blender/data/side_profile.json`;
`tools/blueprint_overlay.py` puts it and an orthographic render of the model in the same world rectangle.
