# Detail map - every visible feature of the 1989 Nova GTE, where it is measured from, and where the model stands

Written 2026-10-27 after laying the model over the factory GA sheet and the 4-view line blueprint, and rendering it
through all seven solved photo cameras next to the photographs (`export/map/cams_A.jpg`, `cams_B.jpg`,
`side_vs_bp.png`, `ga_vs_model.jpg`). Companion to `docs/REPLICA_PLAN.md`.

**Sources, by code**
- **GA** - factory GA sheet `opel_corsa_a_cc_gsi_GA_drawing_full.jpg` (rectified: `GA_rectified.png`). Side, front,
  rear, **plan** views. Dated Nov 1990 = facelift car: use for hard points, apertures, glass, plan shape - NOT for
  bumpers, lamps, grille.
- **BP** - 4-view line blueprint `corsa_a_4view_blueprint.gif`. Clean side + front. Overhangs 83 mm short: shape
  between the axles only.
- **R##** - Nik's red GTE, `reference/photos/user_red_gte/redgte_##.webp` (F294 DVR, RHD). Aftermarket: black wheels,
  low-profile tyres, rear springs, HT leads, battery, exhaust tip.
- **cS / cAR** - anglia_side / anglia_rear (F400 PTF, factory wheels). **cCF** - commons 1989 GTE front.
- **BA** - the 34 triangulated points (`tools/photomatch/ba_result.json`), 7 solved cameras.
- **BRO** - Oct 1988 brochure (`reference/manuals/`), **FIA** - homologation A-5375, **SPEC** - `docs/SPEC_SHEET.md`.

**Model state, by code:** OK = matches the references; ROUGH = right place, wrong shape or finish; WRONG = visibly
wrong; NONE = not built.

---

## A. Proportions and hard points

| Feature | The car | Source | Model |
|---|---|---|---|
| Length / wheelbase / height / width | 3622 / 2343 / 1365 / 1532 mm | GA, FIA, SPEC | OK |
| Tracks | 1320 / 1307 mm | GA, SPEC | OK (wheels placed on them) |
| Overhangs | 670 front / 609 rear | FIA | OK |
| Side silhouette between the axles | roofline, belt, sill | BP, GA, cS | OK - overlays BP closely (`side_vs_bp.png`) |
| Plan shape (top view) | nose tapers hard from the A-pillar forward, rounded front corners; tail tapers less; screen and tailgate curved in plan | **GA plan view** (only plan source) | ROUGH - plan traced once (`plan_profile.json`) but never checked as a top-view overlay |
| Body tumblehome | greenhouse much narrower than the body, pillars lean in strongly | GA front/rear, BP front | ROUGH - roughly right, never overlaid |
| Body width at axles | FIA 1522 / 1529 | FIA | WRONG by ~1 cm/side (left "for now" on 19 Oct) |

## B. Front end (pre-facelift - photos, not GA)

| Feature | The car | Source | Model |
|---|---|---|---|
| Front bumper | body colour, fine horizontal ribs, 4 red pinstripes in the rib grooves, plate recess, wraps to the arches | R18-20, R22, cCF | OK - the best part of the model (swept section, `tools/front_end.py`) |
| Chin spoiler / lower valance | **grey**, full width, tucked under | R19, R22, cCF | ROUGH - shape there (BUMPER_F_LIP), not grey |
| Number plate | 520 x 111, centred in the recess | R20 | ROUGH - plain plate, no text |
| Grille surround | thin body-colour frame between the lamps; the bonnet front edge overhangs it | R18-20 | ROUGH |
| Grille insert | **black horizontal slats**, chrome "GTE" badge in the centre | R20 | ROUGH - dark block, no slats or badge |
| Headlamps | rectangular, fluted (ribbed) glass lens, H4 reflector behind, thin bezel | R02, R20 | WRONG - flat white blocks, no lens or reflector |
| Indicators | amber, wrapping round the body corner from the headlamp to the wing shut | R20, R22 | ROUGH - geometry there, needs lens/amber |
| Bonnet front edge | shallow V, overhangs the grille surround, rolls down to it | R20, BA BON_* | OK |
| Griffin badge | **white griffin decal** on the bonnet nose, centred | R20, R19 | NONE |
| Front tow eye / fog lamps | GA shows optional fogs ("wahlweise") - **not on the UK GTE photos** | GA, R20 | n/a - leave out |

## C. Bonnet and scuttle

| Feature | The car | Source | Model |
|---|---|---|---|
| Bonnet surface | raised centre panel between **two lengthwise creases that converge towards the front**, outer panels falling to the wings | R19, R20, BP front | ROUGH - creases there; the bonnet reads lumpy/bulbous in front views (cams c20, cCF) |
| Bonnet shut to wings | ~4 mm, flush | R22 | OK (27 Oct (12)-(14)) |
| Bonnet rear edge | curved in plan, centre 115 mm forward of the sides | BA scuttle_curve | OK |
| Scuttle grille | **diamond-slotted** plastic grille across the scuttle, washer jets | R28, R30 | NONE (louvres removed 26 Oct, never redone) |
| Wipers | tandem pair, black, parked at the screen base | R19, R20 | NONE |

## D. Front wings

| Feature | The car | Source | Model |
|---|---|---|---|
| Wing top | carries the bonnet's outer panel over the shut | R22 | OK (27 Oct) |
| **Spear crease** | a pressed crease on the upper wing that **tapers to a point** at both ends (spear / hockey-stick shape), from the headlamp back towards the door; it is what draws the bright line in R22 | **BP side (clearly drawn)**, R22, cS | WRONG - modelled as a straight full-length step at z 0.70 |
| Flared lower panel / arch | "blistered box arch" - lower panel stands proud under the crease, arch lip flanged | SPEC, cS, R22 | ROUGH - flare and lip there, lip profile not checked closely |
| Side repeater | small amber oval on the wing, behind the arch | R22, BA SR | NONE (point is measured: SR) |
| Arch liner | black plastic/ undersealed well | R26-27 | NONE - well open to the background |

## E. A-pillar and windscreen

| Feature | The car | Source | Model |
|---|---|---|---|
| Windscreen glass | green tint, curved | SPEC, R19-20 | **WRONG - pane is a fan from the centre of a half model and leaves a big see-through triangle** (ortho front, every camera) |
| Screen rubber | thick black rubber surround all round | R21 | ROUGH |
| Screen base | sits just above the scuttle grille | R19, BA WS_B | WRONG - lower edge stepped; shell stands 15-37 mm above the scuttle |
| A-pillar | body colour, black drip/gutter strip running up it onto the roof | R21 | ROUGH |

## F. Doors

| Feature | The car | Source | Model |
|---|---|---|---|
| Door shut lines | front, rear, bottom; door top is the window frame | BP, GA, cS | ROUGH - grooves exist (shut_lines.py), door not a separate panel |
| **Quarter-light** | fixed triangular glass at the front of the door window, between the A-pillar and a **black vertical division bar** | **BP side, GA side**, cS, R34 | **NONE - that area is body colour** |
| Drop glass | rest of the door window | BP, BA DG_* | OK - aperture matches BP |
| Window frames | **black** frames round the door glass | R01, R22, R34 | NONE (one red skin) |
| Belt seal | black strip along the window bottom | R34 | NONE |
| Door handle | small black flap handle with lock barrel | R22, BP | NONE (BP and photos give position) |
| GTE decal | grey outline italic "GTE" low on the front of each door | R22, cS | NONE (position measured 19 Oct on the old model) |
| Mirror | body-colour housing sweeping forward, glass on the rear, black rubber edge, black triangular gasket on a grey sail at the quarter-light corner | R34, cS, c22 | ROUGH - built 27 Oct (15) to the measured size; the sail/gasket is a placeholder block |

## G. B-pillar and side glass

| Feature | The car | Source | Model |
|---|---|---|---|
| B-pillar | **black** | R01, R22, R25 | NONE (red) |
| Rear quarter window | fixed glass, black frame, rounded rear corner | BP, GA, cS | ROUGH - aperture close (BA QW_* 17-23 mm out at two corners) |
| Side glass panes | green tint, flush in a black frame | R22 | WRONG - fan triangulation shows as shards |

## H. Rear quarters

| Feature | The car | Source | Model |
|---|---|---|---|
| Rear spear crease | second spear crease on the rear quarter, from the door shut to the tail lamp | **BP side**, cS | WRONG - straight full-length step |
| Rear arch | flared, flatter-topped than the front | BP, cS | ROUGH |
| Fuel filler | round flap, **right-hand rear quarter** | R25, cS | NONE on the shell (was on the old model) |
| C-pillar | wedge-shaped extension carried onto the tailgate sides | R03, R23, GA | ROUGH |

## I. Roof

| Feature | The car | Source | Model |
|---|---|---|---|
| Roof panel | gently crowned, drip strips along both edges | R21, GA | ROUGH |
| **Sunroof** | front-set tilt/slide glass, about half the roof width, black seal (standard on GTE) | R21, BRO p25 | NONE |
| Roof gutters | black strip each side | R21 | NONE |
| Aerial | not seen on R-photos - check before adding | - | - |

## J. Tailgate and rear panel

| Feature | The car | Source | Model |
|---|---|---|---|
| Rear window | **one large pane**, rounded corners, narrower at the top, thick black rubber, heated element lines | R03, R24, GA rear | **WRONG - two dark triangles either side of a body-colour centre bar; see-through** |
| Tailgate centre | no seam - one panel | R24 | **WRONG - vertical seam down the middle (PANEL_R_L/R)** |
| **Roof spoiler** | body-colour spoiler at the top of the tailgate, over the glass | R23, BRO (tailgate spoiler), GA "Heckspoiler" | NONE |
| Rear wiper | single arm, pivot at the bottom centre of the glass | R24 | NONE |
| Griffin decal | white, at the glass-to-panel join, centred | R24 | NONE |
| **Black rear panel** | **matt black panel full width between the lamps**, from the bumper up to just under the glass | R03, R24, BRO "black foil panel" | WRONG - black zone listed, renders red (no separate part) |
| GTE badge | chrome, top left of the black panel | R24 | NONE |
| Handle strip | grey full-width strip with the lock across the top of the black panel | R24 | NONE |
| Plate + plate lamps | yellow plate centred on the black panel, lamps above | R24 | ROUGH - PLATE_LAMP_R only |

## K. Tail lamps

| Feature | The car | Source | Model |
|---|---|---|---|
| Lamp unit | tall vertical unit at each rear corner, black surround | R04, R07, R24 | ROUGH - geometry there, all renders red |
| Bands (top to bottom) | red (brake/tail) - red - **amber** indicator - **clear** reverse | R04, R07; heights **800 / 745 / 685 / 635** | GA rear (dimensioned) | ROUGH - bands built on GA heights 27 Oct, no lens materials |
| Lens texture | fine ribbed optics | R04 | NONE |

## L. Rear bumper and under-tail

| Feature | The car | Source | Model |
|---|---|---|---|
| Rear bumper | body colour, ribbed, **red pinstripes** | R24, R07 | ROUGH - deep in the rear ortho; ribs there |
| Lower valance | **grey** | R24, cAR | ROUGH - shape, not grey |
| Tow eye | red, right side | R24 | NONE |
| Exhaust | single tailpipe, **left** side (R-photos: aftermarket tip) | cAR, R23 | NONE |

## M. Sills and skirts

| Feature | The car | Source | Model |
|---|---|---|---|
| Sill extensions | **grey**, full length, run back round the front of the rear arch, ~12 mm proud | R01, R22, cS | ROUGH - shape OK (traced 26 Oct), not grey |

## N. Wheels, tyres, brakes

| Feature | The car | Source | Model |
|---|---|---|---|
| Alloys | 5J x 14 ET49 three-arm, dark insert, "VAUXHALL" on one arm | BRO p34/38, GA wheel table, cS | OK (traced face, 27 Oct (15)) |
| Tyres | 175/65 HR14 | BRO | OK |
| Front brake | 236 x 20 vented disc, single-piston caliper | FIA | OK |
| Clearance | front tyre 0.3 mm from the shell's front arch edge at rest | - | WRONG - fix before AC |

## O. Underside (R26-27, GA plan)
Rear torsion beam (black) with drums, single exhaust pipe to a rear silencer behind the axle, fuel tank under the
rear seat with straps, red textured underseal, front subframe and wishbones, gearbox. Model: NONE (needed only as a
simplified underside for AC).

## P. Interior (R08-17, R33, R35; SPEC lines 248-252) - RHD
Grey dash with round end vents, binnacle with speedo 20-120 mph, 4 small gauges, tacho 0-7k (red from ~6.3k);
3-spoke black wheel with griffin; centre stack (radio, clock, switches, heater controls); console with gear lever;
high-back sports seats in grey "Laser" velour with red and light-grey stripes, grey plastic back shells; door cards
grey with dark velour insert, red pinstripe, pull handle, speaker pad, winder; black carpet; rear seat with separate
head restraints; parcel shelf. Model: NONE in the measured build (an LHD-mirrored first pass existed on the old model).

## Q. Engine bay (R28-32; reference/research/1989_Nova_GTE_Engine_Bay_Reference)
Transverse E16SE, "VAUXHALL EFi" plenum, rocker cover "1.6 INJECTION", Bosch airflow meter on a black airbox at the
front corner, body-colour strut towers, wiper motor, diamond scuttle grille, washer bottle and expansion tank,
brake servo/reservoir, felt bulkhead, bonnet insulation, prop rod. Model: NONE.

---

## Measured accuracy now (geo_check, 27 Oct (15))
58 point checks (34 BA points + mirrors): median **9.3 mm**; 10 within 5 mm, 32 within 5-15 mm, 16 over 15 mm.
Worst real ones (single-view MIR / BON_F / PNL_B excluded): DSR_B 94 mm (skirt), HG_B 25 mm (hatch glass bottom),
QW_FB 23 mm, DG_RT 20 mm (known bad point), QW_RT 17 mm.

## What makes it read as "not a Nova", in order
1. **Rear end** - split tailgate, triangle glass, no black panel, no spoiler, lamps not readable.
2. **No colour/trim breakup** - the car is defined by black frames/B-pillar/rear panel, grey skirts and valances,
   red pinstripes, white griffins, amber and clear lenses. The model is one red skin.
3. **Broken glass** - see-through fans in the screen and tailgate; shards in the side glass.
4. **Front face** - flat white headlamps, no slatted grille or badge, no griffin, bonnet reading lumpy.
5. **Missing signature shapes** - the spear creases, the quarter-light and division bar, the sunroof.
6. **Surface quality** - meshes built point by point ripple and stair-step; the bumper (one swept section) is the
   only part with production-car surfaces.
