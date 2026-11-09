# Spec sheet - Vauxhall Nova GTE 1.6 (1989 spec, car id vauxhall_nova_gte_1989)

Confidence tags: **BROCHURE** (Vauxhall's own Oct 1988 Nova brochure, MY1989), **FIA** (manufacturer's declaration on the FIA homologation form), **SOURCED** (from a listing, article or aggregator, still unverified against a factory document), **CONFLICT** (sources disagree - every value listed, one picked with a reason), **GAP** (not found yet), **ESTIMATE** (reasoned value, not a direct source).

Last update: 2026-10-06 (second pass: Vauxhall's Oct 1988 brochure read page by page; its figures override aggregator sites). **Decided with the user: 1989 base, RHD (UK spec), factory alloy wheels, pre-facelift, free blueprints only.**

## Primary source 2: Vauxhall Nova brochure, Oct 1988 (MY1989)
`reference/manuals/Vauxhall_Nova_Brochure_1989_Oct1988.pdf` (40 pages; https://archive.org/details/VauxhallNovaBrochure1989). GTE pages 22-25, technical pages 34-35, alloy wheel p38, RHD dash p21 and p25, rear 3/4 of a red GTE with alloys p24.

## Primary source: FIA homologation A-5375
`reference/manuals/FIA_homologation_5375_GroupA_Opel_Nova_GTE_Corsa_GS.pdf` (69 pages, downloaded from the FIA historic database).
- Group A form for the **"Vauxhall Nova GTE / Opel Corsa GSi"**, manufacturer General Motors Europe, valid from **1 Jan 1989** (to 1 Jan 2001). Pre-facelift car, so it covers our 1990 GTE.
- Pages 1-16 are the basic form (the road car). Pages 17-69 are 13 extensions (1989-1992), mostly competition options (VO) - do not use those for the road car.
- Photos in the form: front and rear 3/4 (p1, a white GTE), engine out and in the bay (p11), combustion chamber, injection, manifolds, gearbox casing (p12), front and rear running gear, brakes, **dashboard** (p13, an LHD Opel - mirror it for our RHD car), suspension drawing (p15), interior dimensions (p16).
- The form gives no kerb weight and no track widths.

## Production
| Item | Value | Tag | Source |
|---|---|---|---|
| Launch | Frankfurt Motor Show 1987 (UK sales from May 1988) | SOURCED | Classics World, Adrian Flux, Wikipedia, Parkers |
| UK sale as 1.6i GTE | May 1988 - Nov 1990 | SOURCED | Parkers |
| Successor | 1.6i GSi from Nov 1990 | SOURCED | Parkers |
| Body / drive | 3-door hatch, front-wheel drive, manual | SOURCED | Parkers |
| Gearbox | 5-speed manual | SOURCED | auto-data, encyCARpedia |
| Survivors | 46 on UK roads (HowManyLeft figure quoted by PistonHeads) | SOURCED | PistonHeads |

### Pre- or post-facelift? -> **pre-facelift** (resolved, confirm with photos)
- Corsa A facelift **September 1990**: "new bumpers, headlights, grille, and interior" (Wikipedia; same wording in Adrian Flux).
- UK naming: "Nova GTE" on pre-facelift cars, "later models were all called GSi" (Wikipedia). "the same badge [GSi] applied to UK cars following the facelift" (Classics World).
- A 1990 GTE for sale was "one of the very last before they became the GSi" (PistonHeads).
- So a 1990 GTE has the **pre-facelift** bumpers, headlights, grille and interior.
- Only dissent: encyCARpedia lists the GTE as 1988-1989 and the GSi from 1990. Outvoted by Parkers' sale dates and the PistonHeads 1990 GTE.
- To do: confirm against photos of a genuine late-1990 (G/H-registered) GTE.

## Engine
| Item | Value | Tag | Source |
|---|---|---|---|
| Capacity | 1598 cc, inline 4, SOHC, 2 valves per cylinder | SOURCED | Parkers, Schaeffler, encyCARpedia |
| Bore x stroke | **79.0 x 81.5 mm** (399.48 cc per cylinder; max bore 79.05) | FIA, resolved | FIA p2-3. Agrees with encyCARpedia and ultimatespecs; the 80.0 x 79.5 on auto-data is wrong for this car |
| Installation | Front, transverse, inclined 7 deg 50' forward | FIA | p2 |
| Block / head | Cast-iron block, light-alloy head | FIA | p3 |
| Crankshaft | Cast iron, one piece, 5 main bearings of 55 mm, minimum weight 11 252 g | FIA | p3 |
| Con rod | Cast iron, 129.8 mm between centres, minimum weight 427 g | FIA | p3 |
| Flywheel | Minimum 7150 g with starter ring | FIA | p3 - use for engine inertia |
| Valvetrain | SOHC, toothed belt, rocker arms. Inlet valve 33 mm, exhaust 29 mm, lift 9.775 mm both | FIA | p4-5 |
| Compression | **10.0:1** | BROCHURE, resolved | p34 |
| Engine code | **E16SE** (Schaeffler 05.1988-03.1992; ultimatespecs Corsa A 1.6 GSi). C16SE = later catalysed engine (auto-data 1992-93 GSi, automobile-sportive) | SOURCED, confirm | A pre-facelift UK GTE is pre-catalyst (Classics World), which fits E16SE |
| Catalysed version | 98 PS (Wikipedia) - **not** our car | SOURCED | Wikipedia |
| Injection | **Bosch LE-Jetronic** (Bosch/GME), electronic, air-flow (volume) meter, injectors in the inlet manifold, 55 mm throttle | FIA, resolved | p4. Matches "Bosch multi-point" in Classics World and Hagerty |
| Engine mapping | by Irmscher | SOURCED | Wikipedia |
| Power | **100 PS / 74 kW (99 bhp) @ 5600 rpm** | SOURCED | encyCARpedia GTE, Adrian Flux, Wikipedia (101 PS), ultimatespecs, Parkers |
| Power rpm | 5600 (non-cat) vs 6000 (the 98 hp 1990 variant) | CONFLICT, resolved | 6000 rpm belongs to the catalysed engine. Use 5600 |
| Torque | **135 Nm (100 lb ft) @ 3400 rpm** vs 132 Nm (97 lb ft) | CONFLICT, resolved | 132 Nm is the catalysed GSi (encyCARpedia 1990 GSi, 97 bhp). Use 135 Nm |
| Torque curve | Read from the brochure graph (approximate): ~90 Nm @1000, ~115 @2000, ~132 @3000, ~135 flat 3500-5000, ~131 @5500, ~118 @6000. Power peaks 74 kW @ ~5600. Curve ends at 6000 rpm | BROCHURE (graph read, ESTIMATE of values) | p34. Use for power.lut |
| Engine features | Bosch L3.1 Jetronic with deceleration fuel cut-off and automatic cold start, breakerless electronic ignition, hydraulic tappets, toothed cam belt, alloy cross-flow head, five-bearing crank with four counterweights. Unleaded OK. Max speed 117 mph | BROCHURE | p34 |
| Rev limit, idle | - | GAP | Workshop manual. Placeholder: fuel cut ~6200 (ESTIMATE, curve ends 6000) |

## Transmission
| Item | Value | Tag | Source |
|---|---|---|---|
| Gearbox | GM 5-speed manual, in the engine bay, lever on the tunnel. Gate: R top-left, 5th top-right | FIA | p6 |
| Gear ratios (road car) | **1st 3.55 (39:11), 2nd 2.14 (45:21), 3rd 1.43 (30:21), 4th 1.12 (37:33), 5th 0.89 (33:37), reverse 3.31** | FIA, resolved | p6, "Handschaltung" column |
| Final drive | **3.74 (71:19)**, spur gear | FIA, resolved | p7 |
| Competition options (not our car) | Rally ratios 2.54 / 1.76 / 1.42 / 1.19 / 1.04; finals 3.94-5.17 | FIA | p6, p10. Do not use for the road car |
| Brochure check | Brochure lists a 5-speed "close-ratio" box as standard with exactly the road ratios above; 15.8 mph per 1000 rpm in 4th, 19.9 in 5th | BROCHURE | p34. Implies rolling circumference ~1.776 m (radius ~0.283 m) |
| Gearbox family | F13 / F15 (Quaife kit for "Corsa & Nova F13/F15") | SOURCED | Not needed for physics now the ratios are known |
| Clutch | Single plate 7.9 in (200 mm), Bowden-cable operated | FIA, BROCHURE | p5; brochure p34 |
| Shift feel | "rubbery gearshift" (Autocar) | SOURCED | Hagerty |

## Mass and dimensions
| Item | Value | Tag | Source |
|---|---|---|---|
| Kerb weight | **834 kg** | BROCHURE, resolved | p35 (GTE 3-door). Others (845, 876, 820 kg) are road-test or other-model figures |
| Gross vehicle weight | **1260 kg** | BROCHURE | p35 |
| Length | **3622 mm** | FIA, resolved | p2. Overhangs below + wheelbase add up to it. (Parkers 3632, facelift GSi 3650+ - not our car) |
| Overhangs | **Front 670 mm, rear 609 mm** | FIA | p2 |
| Width | **1535 mm overall**, measured at the front wing behind the axle | FIA, resolved | p2 (Parkers 1549, encyCARpedia 1532) |
| Body width at axles | **1522 mm at the front axle, 1529 mm at the rear axle** | FIA | p2 |
| Height | **1365 mm** (53.7 in) | BROCHURE | p35 |
| Wheelbase | **2343 mm** (both sides) | FIA, resolved | p2. Also encyCARpedia, auto-data, cararac, vehiclescore. The 2450 mm listing is an error |
| Interior | Height above front seats 959, width at front seats 1280, height above rear seats 942, width at rear seats 1294, steering wheel to brake pedal 635, steering wheel to rear bulkhead 1540 (all mm) | FIA | p16 - use for the cockpit and driver position |
| Width, brochure | 1532 mm excluding mirrors, 1725 mm including mirrors | BROCHURE | p35 |
| Front / rear track | **1320 / 1307 mm** | SOURCED (matches the FIA body widths) | encyCARpedia (GTE), auto-data (GSi); brochure gives none |
| Fuel tank | **42 L** (9.2 gal), steel, under the rear seat pan | FIA, BROCHURE | p5; brochure p35 |
| CoG height, weight distribution | - | GAP | - |

## Chassis
| Item | Value | Tag | Source |
|---|---|---|---|
| Front suspension | MacPherson strut, coil springs | FIA | p7, photo T p13 |
| Rear suspension | Torsion-beam axle with coil springs (photo U shows the beam) | FIA | p7, p13, drawing p15. encyCARpedia agrees |
| Dampers | One per wheel, telescopic hydraulic, front and rear | FIA | p8 |
| GTE vs SR | Stiffer front springs, uprated dampers, larger front and rear anti-roll bars. Rear: compound crank with progressive-rate mini-block coil springs. Classics World: "35 per cent stiffer springs than SR" | BROCHURE p35 (relative only), SOURCED | No absolute rates yet |
| Brake system | Dual-circuit hydraulic, one master cylinder 20.64 mm bore, Ate/Delco vacuum servo, pressure regulator in the master cylinder | FIA | p8 |
| Front brakes | **Vented disc 236 x 20 mm**, one cast-iron single-piston caliper (52 mm bore), 2 pads, pad rubbing surface 235 mm outer / 147 mm inner diameter, pad length 98 mm | FIA | p8-9 |
| Rear brakes | **Drum 200 mm** inside diameter, 2 shoes 28 mm wide, one wheel cylinder 17.46 mm bore | FIA | p8 |
| Handbrake | Lever on the tunnel, Bowden cable, rear wheels | FIA | p9 |
| Brake bias | Not stated - derive from the piston and drum sizes above plus the regulator | ESTIMATE later | - |
| ABS | **None**. Brochure option list has no ABS; auto-data lists ABS only on the 1992-93 GSi | BROCHURE, resolved | p34-35 |
| Steering | Rack, **ratio 21.4:1**, no power assistance | FIA | p9 |
| Steering lock | **3.9 turns** lock to lock, energy-absorbing column, non-adjustable | BROCHURE | p35 (Classics World said 3.8) |
| Turning circle | **9.35 m** | BROCHURE | p35 |
| Spring / damper rates, ride height, alignment | - | GAP | - |

## Wheels and tyres
| Item | Value | Tag | Source |
|---|---|---|---|
| Wheel diameter | 14 in, front and rear | FIA | p8 |
| Wheel width | **5J** | BROCHURE | p34 |
| Tyres | **175/65 HR14** low-profile radial (GTE); 165/65 TR14 is the SR with alloys | BROCHURE, resolved | p34. Old conflict note follows for the record: 165/65 (auto-data 1992-93 GSi), "50-profile" (Classics World) are wrong for this car | Read the sidewall in the reference photos, or the handbook. Gearing check (ESTIMATE, static tyre diameter): with the FIA 5th gear and final drive, 188 km/h needs 5693 rpm on 175/65 R14, 5823 on 165/65, 5938 on 185/55 and 6257 on 175/50. Power peaks at 5600, so 175/65 R14 fits best (20.5 mph per 1000 rpm in 5th) |
| Standard wheels | 5J x 14 steel with "star-patterned" silver flush wheel covers (body-colour covers on Glacier White) | BROCHURE | p34 |
| **Alloy wheels (chosen)** | 5J x 14 factory alloy, three-armed design with a dark insert, "VAUXHALL" lettering on one arm, silver finish. Optional on the GTE | BROCHURE | p34, p38 (image), p24 (red GTE with alloys) |
| PCD / centre bore | **4 x 100**, centre bore 56.6 mm | SOURCED (wheel-fitment guide, carlsalter) - verify | Not yet from a manual |
| Offset | Factory 14 in wheels ET 47.5 or 49 mm (PNG club); fitment guide says 40-45 | CONFLICT | Use ET 47.5 as a placeholder, check against photos |

## Aero
| Item | Value | Tag | Source |
|---|---|---|---|
| Drag coefficient | **0.37** (GTE) | BROCHURE | p35 |
| Frontal area | - | GAP | Compute from blueprint |

## Performance (validation targets)
| Item | Value | Tag | Source |
|---|---|---|---|
| 0-60 mph | **9.1 s** (Autocar road test, 1988) - best measured figure | SOURCED | Classics World, Hagerty |
| 0-60 mph claimed | 8.7 s (Vauxhall claim) | SOURCED | Adrian Flux |
| 0-100 km/h | 9.5 s (auto-data 1988, encyCARpedia), 8.9 s (automobile-sportive), 9.8 s (1990 cat variant) | CONFLICT | Use the Autocar 0-60 as the main target |
| Top speed | 117 mph / 188 km/h | SOURCED | encyCARpedia, Adrian Flux, Hagerty, auto-data |

Acceptance test for physics: a standing-start and top-speed run in AC should land inside these ranges.

## Bodywork (FIA p1, p9-10)
- Unitary steel body, 3-door hatch (2 doors + tailgate), 5 seats
- Plastic parts: front bumper with spoiler, rear bumper, side spoilers (skirts), rear spoiler, front grille
- Laminated windscreen, safety glass elsewhere
- Front windows manual crank or electric; rear side windows fixed
- Sunroof: sliding/tilting glass roof with louvred blind is **standard on the GTE** (BROCHURE p25); the FIA form's "nein" is just a homologation simplification
- Photos A and B (p1): white GTE, white multi-hole wheels, "GTE" badge on the grille and the rear panel, "GTE" decal low on the front of each door, skirts, body-coloured bumpers, tailgate spoiler

## Exterior trim (BROCHURE pp22-25, 38 plus text sources - confirm in photos)
- Colour-coded front grille, bumpers, front and rear spoilers, door mirror housings; aerodynamic sill extensions
- Black foil panel between the tail lamps, GTE badge on the tailgate (p24)
- Red insert on the bumpers only for GTE, red pinstripes
- Green tinted glass
- Body-coloured grille, bumpers and spoilers (Adrian Flux)
- "blistered box arches", "Audi Quattro-style flared arches" (Classics World, Hagerty)
- Side skirts (Classics World buyer's guide)
- GTE decals on both front doors (Car & Classic auction, 1989 GTE)
- Red pinstriping (PistonHeads, 1990 GTE)
- Tilt-and-slide sunroof on two of the GTEs found - standard or option is a GAP
- Pre-facelift bumpers, headlights and grille (see Production)

## Interior (BROCHURE pp21, 25 plus text sources - confirm in photos)
- RHD GTE dash photographed on brochure p25; SR dash and shifter on p21
- Laser cloth trim: grey velour with pink/red and grey stripes; sports front seats; 60/40 split rear seat
- 3-spoke sports steering wheel with the Vauxhall griffin
- Sports instrumentation: rev counter, voltmeter, oil pressure gauge, low-fuel light; quartz clock, cigar lighter
- Philips DC670 radio/cassette (4 x 4.5 W), cassette storage, two-door central locking
- Sports seats: "great seats" (Autocar via Hagerty). "progressively better bolstering and fabrics on SR/SRi/GTE" (Car & Classic guide)
- Grey cloth on a Glacier White 1989 GTE (auction listing)
- Non-adjustable steering wheel on an offset column (Classics World)
- Radio: Philips 552 radio-cassette in one 1989 car (Classics World), "original Vauxhall tape deck" in another (Car & Classic) - read the unit from photos
- Pre-facelift dash and interior (the facelift changed the interior)

## Sound character
- "rorty exhaust note", "cheeky trademark rasp" (Classics World)

## Paint
- Target: metallic gun-metal grey (decided).
- 1989 brochure colours: Calypso Red (shown on GTE), Carmine Red, Glacier White, Laser Blue, Aquamarine, Nordic Blue, Astro Silver, Steel Grey (metallic, shown on a Merit saloon). Two-coat metallic is optional on the GTE; black also optional.
- **Steel Grey metallic is the closest period match** to gun-metal grey. Not confirmed as offered on the GTE. PNG club chart: Steel Grey Met 114/82 (91-94), nothing earlier; paintnuts also sells "Steel Grey Metallic 184" and "114". Oct 1989 colour brochure V7364 not found. Since the paint is a free choice anyway, treat Steel Grey as the reference tone.

## Still open
- Spring rates, damper rates, anti-roll bar sizes, ride height, camber/toe/caster (Haynes manual is lending-only on archive.org; text not readable)
- Alloy offset and PCD from a primary source
- Rev limit, idle speed
- Track widths from a primary source
- Frontal area, CoG height, weight distribution
- Brake bias (derive from the piston and drum sizes)
- Paint code and whether Steel Grey was offered on the GTE
- MY1990 differences from MY1989
- Audio recordings (E16SE)

Resolved this pass from the brochure: kerb weight, compression, Cd, tyres, wheels, sunroof, ABS (none), steering lock, turning circle, torque curve, rolling circumference.

Best remaining sources: Vauxhall brochure and press kit (1989/1990 Nova range), Haynes / Vauxhall workshop manual, period road tests (Autocar 1988 GTE test, Motor, Performance Car), owners' club technical pages.

## Sources
First chat pass:
- Parkers, Nova 1.6i GTE: https://www.parkers.co.uk/vauxhall/nova/hatchback-1983/16i-gte-3d/specs/
- Parkers, Nova 1.6i GSi: https://www.parkers.co.uk/vauxhall/nova/hatchback-1983/16i-gsi-3d/specs/
- Schaeffler listing (E16SE): https://new.rolling.hu/catalog/SCHAEFFLER/vauxhall-nova-hatchback-s83-16-gsi
- vehiclescore, Nova weight: https://vehiclescore.co.uk/car-weight/vauxhall/nova
- vehiclescore, Nova dimensions: https://vehiclescore.co.uk/car-dimensions-check/vauxhall/nova
- cararac, Nova dimensions: https://cararac.com/dimensions/vauxhall/nova.html
- auto-data, Corsa A 1.6 GSi (1988-90): https://www.auto-data.net/fr/opel-corsa-a-facelift-1987-1.6-gsi-100hp-2133
- auto-data, Corsa A facelift 1990 1.6 GSi: https://www.auto-data.net/en/opel-corsa-a-facelift-1990-1.6-gsi-98hp-25994
- automobile-sportive, Corsa A GSi: https://www.automobile-sportive.com/guide/opel/corsagsi.php

2026-10-06 (Cowork):
- **Vauxhall Nova brochure, Oct 1988**: https://archive.org/details/VauxhallNovaBrochure1989
- Wheel fitment guide: https://www.carlsalter.com/vauxhall-wheel-fitments.html
- PNG club colour chart: https://www.pngclub.com/forum/archive/index.php/t-62322.html
- **FIA homologation A-5375 (Group A), Vauxhall Nova GTE / Opel Corsa GSi**: https://historicdb.fia.com/car/opel-nova-gte-corsa-gs (PDF: https://historicdb.fia.com/sites/default/files/car_attachment/1601055001/homologation_form_number_5375_group_a.pdf, saved in `reference/manuals/`)
- Autocar group test 3 Aug 1988, Nova GTE v Charade GTti v Fiesta XR2 (scans on Flickr - not read yet): https://www.flickr.com/photos/triggerscarstuff/albums/72157616120879200/
- encyCARpedia, Nova GTE 1988-89: https://www.encycarpedia.com/vauxhall/88-nova-gte-hatch
- encyCARpedia, Nova GSi 1990-91: https://www.encycarpedia.com/vauxhall/90-nova-gsi-hatch
- Wikipedia, Opel Corsa (Corsa A section): https://en.wikipedia.org/wiki/Opel_Corsa
- ultimatespecs, Corsa A 1.6 GSi: https://www.ultimatespecs.com/car-specs/Opel/3326/Opel-Corsa-A-16-GSi.html
- auto-data, Corsa A facelift 1990 1.6 GSi 101 hp: https://www.auto-data.net/en/opel-corsa-a-facelift-1990-1.6-gsi-101hp-2134
- Classics World, Nova GTE test (1989 car, Autocar figures): https://classicsworld.co.uk/?p=34026
- Classics World, Nova buyer's guide: https://classicsworld.co.uk/guides/vauxhall-nova-buyers-guide/
- Hagerty, Nova GTE ad break (Autocar quotes): https://www.hagerty.co.uk/articles/ad-break-the-vauxhall-nova-gte-was-too-hot-for-an-xr2-to-handle/
- Adrian Flux, Nova cult classic: https://www.adrianflux.co.uk/cult-classics/vauxhall-nova/
- PistonHeads, 1990 Nova GTE for sale: https://www.pistonheads.com/news/ph-spottedykywt/rose-tinted-vauxhall-nova-gte-for-sale/48153
- Car & Classic, Nova models and specs: https://www.carandclassic.com/buyer-guides/vauxhall-nova-models-and-specs
- Car & Classic auction, 1989 Nova GTE (red, 112 photos): https://www.carandclassic.com/us/auctions/1989-vauxhall-nova-gte-nQYXxn
- Car & Classic, 1989 Nova GTE (Glacier White): https://carandclassic.com/car/C1786051
- Quaife F13/F15 gear kit: https://shop.quaife.co.uk/shop/gear-kits/h-pattern-2/synchromesh-2/vauxhall-opel-f13-f15-5-speed-synchromesh-quaife-gearkit/
- PNG club gearbox thread: https://www.pngclub.com/forum/archive/index.php/t-61935.html

## Chassis derivations (added 2026-10-06, third pass)
All values below are ESTIMATE or SOURCED-parts-data. No factory spring or damper rates were found; they were derived from aftermarket catalogue dimensions (Autodoc listings for the Nova 1.6 GSi, which shares the GTE's parts).

| Item | Value | Tag | Basis |
|---|---|---|---|
| Front coil spring (KYB RC1518 / Metzger 2240901) | 305 mm long, 130 mm outer dia, 11.5 mm wire, 6.25 coils | SOURCED (parts catalogue) | Autodoc. Alternative Monroe SP0112: 315 mm, 128 mm, 11.2 mm wire |
| Front spring rate | **about 22 N/mm (range 20-25)** | ESTIMATE | k = G d^4 / (8 D^3 n), G = 79.3 GPa, mean dia 118.5 mm, active coils 4.25-5.25 |
| Rear coil spring (KYB RX5105 / Monroe SN0672) | 215 mm long, 140 mm outer dia, 12 mm wire, 5.5 coils, constant wire | SOURCED (parts catalogue) | Autodoc. Mini-block progressive alternative SP0672: 219 mm, 148 mm, 12 mm wire. Monroe SP0747 (14 mm wire, reinforced) is probably van/estate |
| Rear spring rate | **about 25 N/mm (range 22-28)** for the constant-wire spring; the progressive mini-block spring starts nearer 20 N/mm and stiffens | ESTIMATE | same formula, mean dia 128 mm, active coils 3.5-4.5. Brochure says the GTE uses progressive mini-block rear springs |
| Which spring is the GTE's | Not identified. Catalogue lists the GSi without separating GTE from other trims | GAP | Brochure: stiffer front springs than SR |
| Wheel rate | Spring rate x motion ratio squared. Use motion ratio about 0.9 front (strut, angled spring), about 0.8 rear (beam) | ESTIMATE | Refine from the car's own geometry in Blender |
| Front anti-roll bar | 20-22 mm (forums disagree: 18, 20, 22 mm exist across the range; GSi tie bars 22 mm) | SOURCED (forum), CONFLICT | PNG club threads t-117703, t-155217 |
| Rear anti-roll bar | **18 mm**, flat bar bolted at the beam ends. GTE, GSi, SRi had the thickest rear bar | SOURCED (forum) | PNG club t-143865 |
| Ride height | GTE/GSi sits about 10 mm lower than other Novas | SOURCED (forum, weak) | PNG club t-114712. Absolute height: derive from the brochure side photo and wheel radius |
| Damper | Gas/oil telescopic, uprated over SR (brochure). Rates not published | GAP | Derive: aim for about 0.3 critical damping bump and 0.5 rebound, then tune against the telemetry logger |
| Alignment (camber, castor, toe) | Not found. Opel workshop manual only, which is not online | GAP | PLACEHOLDER from period norm in car data, flagged as such |
| Unsprung / weight distribution | Not found | GAP | ESTIMATE: ~62/38 front/rear for a FWD hatch, to be checked against the front axle load in the Autocar test if found |

Spring-rate sanity check: front wheel rate about 18-20 N/mm on roughly 260 kg sprung mass per corner gives a ride frequency of about 1.4-1.5 Hz, which is right for a firm 1980s hot hatch. Rear about 1.6 Hz on a lighter corner.

Unreachable sources (402/403): migweb threads on Nova suspension, steves nova site.

## Reference car: user's red GTE photos (added 2026-10-07)
`reference/photos/user_red_gte/redgte_01..17.webp` - 17 photos supplied by the user of a Calypso-red RHD GTE (F-plate, so 1988-89). Personal reference only, do not redistribute. Notes read from the photos (SOURCED from the photos, check against the brochure where they differ):
- redgte_01 front 3/4: body-colour grille with GTE badge, rectangular headlamps with the amber indicator wrapping at the corner, red horizontal pinstripes on the front bumper over a grey lower valance, grey sill extensions, "GTE" decal low on the front door, body-colour door mirrors, black window frames and B-pillar. **The black multi-spoke alloys on this car are aftermarket, not the factory wheels.**
- redgte_02 headlamp close-up: ribbed rectangular lens, H4, E9 approval marks.
- redgte_03 rear quarter: matt black panel between the tail lamps on the tailgate, thick black rubber seal around the rear glass.
- redgte_04 and redgte_08 tail lamp: three-part lamp in a black surround (upper red, lower red, amber indicator, clear reverse segment at the bottom, in the bumper-side corner), moulded part number 5973598.
- redgte_05 spare wheel well under the boot floor with a red strap hook; grey felt boot side trim.
- redgte_06 boot: fold-down parcel shelf, split carpeted floor, grey side trims with a speaker-style grille, red tow eye on the rear bumper, single tailpipe at the left of the bumper, red pinstripes on the rear bumper.
- redgte_07 and redgte_10 dash and centre stack: grey dash with radio, clock, hazard switch and heater vents; 3-spoke black wheel with the griffin; round vents at each end of the dash; glovebox with a push latch; switch pairs (rear wiper/fog) to the right of the cluster; centre console with cassette tray and gear lever; studded rubber pedal covers plus a dead pedal.
- redgte_11 instrument cluster: speedo 20-120 mph with an inner km/h scale (marked w=1810), four small gauges (battery top-left, oil pressure top-right, coolant bottom-left, fuel bottom-right, fuel has an "R" reserve mark), tachometer 0-7 x1000 with the red zone starting at about 6.3k. Odometer shows 79 299 miles.
- redgte_12-17 interior: Laser striped velour in grey with red and light-grey stripes, high-back sports front seats with integral head restraints, grey plastic seat-back shells and recline levers, separate head restraints on the rear seat, black loop-pile carpet.
- Door cards: grey plastic with a dark velour insert, thin red pinstripe, moulded pull handle, round speaker pad, manual window winder, pocket at the bottom, interior handle recess.

### Red GTE photo batch 2 (redgte_18..35, 2026-10-07)
Same car (RHD, F294 DVR). Items that are NOT original on this car: black aftermarket alloys and low-profile tyres, blue coilover springs at the rear, red competition HT leads, modern Bosch battery. Everything else looks factory.
- Front (18-20): body-colour grille surround carrying a black slatted grille with a "GTE" badge; the bonnet front edge overhangs the surround. White griffin decal on the bonnet near the front edge. Two shallow raised ridges run from each wing across the bonnet. Rectangular headlamps with the amber indicator wrapped round the corner. Front bumper has fine horizontal ribs with red pinstripes and a recess for the plate, with a grey lower valance. Tandem windscreen wipers. Amber side repeater on the front wing.
- Sunroof (21): front-set tilt/slide glass roof with a black surround seal, roughly half the roof width.
- Side (22-25, 31): "GTE" decal low on the front door, grey sill extensions that run back round the rear wheel arch, small flap-style door handles, round fuel filler flap on the rear quarter, black B-pillar and window frames. Door mirrors are body colour with a black rubber edge and a black triangular base gasket on a grey sail.
- Rear (23-25): matt black lower tailgate panel with "GTE" at the top left, a grey full-width handle strip with the lock, white griffin decal on the glass-to-panel join, rear wiper, rear bumper with red pinstripes and a grey valance, single tailpipe at the left, red tow eye at the right. The tailgate sides taper back as a wedge-shaped extension of the C-pillar.
- Underside (26-27): rear torsion beam painted black with a drum brake at the wheel, the exhaust runs in a single steel pipe to a rear silencer behind the axle, fuel tank under the rear seat with red body-colour textured underseal, tank straps visible. Blue spring on the rear is aftermarket.
- Engine bay (28-31): transverse 1.6 with silver "VAUXHALL EFi" plenum, cast rocker cover reading "1.6 INJECTION" in red, distributor on the left end (from the front of the car), silver Bosch airflow meter on the black airbox at the front corner, strut towers painted body colour, wiper motor and a scuttle grille with a diamond-slotted pattern, washer bottle and coolant expansion tank on the passenger side, brake fluid reservoir, black felt bulkhead panel, underbonnet felt insulation with a courtesy lamp, thin prop rod, data plates on the front slam panel.
- Boot and rear seat (32-35): lift-up carpeted parcel shelf, two-section carpeted boot floor (split for the 60/40 seat), grey side trims with speaker grilles on the top, plastic pull caps, spare wheel under the floor. Rear seat is the same striped velour as the fronts, with lap-and-diagonal belts and a plain grey rear-quarter trim with a recessed pull.


---

## Haynes workshop manual figures (Corsa/Nova 1983-93, incl. Ch.13 supplement) - added 2026-10-07

Source tag SOURCED unless stated (read from scanned page images). Archive: `reference/manuals/corsa_workshop/`. The supplement's project cars include a 1989 Nova 1.6 GTE.

### 1.6 injection engine (E16SE, Bosch L3.1-Jetronic), Ch.13 p232-234
- Bore x stroke 79.0 x 81.5 mm, 1598 cc. Compression 10.0:1 (C16SE cat version 9.8:1).
- Output (DIN) 74 kW (100 bhp) at 5600 rpm. RESOLVED: matches the 100 PS / 74 kW @ 5600 rpm already in this sheet (SOURCED x6). Haynes idle/CO/pressure/timing/oil figures fill the old idle GAP.
- Camshaft code D, lift 5.61 mm inlet / 6.12 mm exhaust (listed under the 1.6 block; moderate confidence).
- Gudgeon pin 55.0 x 18.0 mm. Oil 3.5 L with filter (dipstick min-max 1.0 L). Cooling system 6.1 L. Thermostat opens 92 C, fully open 107 C, cap 1.20-1.35 bar.
- Idle 900-950 rpm, CO 0.2-0.4 %, fuel pressure 2.5 bar (manifold vent open), pump 1 L/min at 12 V. Ignition timing 10 deg BTDC at idle (Hall-effect distributor, MSTS).
- Air filter Champion U559, fuel filter Champion L201, oil filter Champion G102. Clutch driven plate 200 mm.
- Remaining GAPS: rev limit (placeholder fuel cut ~6200), valve clearances (hydraulic tappets, none needed).

### Transmission
- F16 5-speed on E16SE; final drive 3.74:1 (table column F13/5 CR). Individual ratios are not in Haynes; the FIA-form ratios above (3.55/2.14/1.43/1.12/0.89, final 3.74) stand and Haynes confirms the 3.74 final.

### Brakes
- Front ventilated discs (GTE/GSi): 236.0 mm dia, 20.0 mm thick, min 18.0 mm (Ch.9 standard disc is also 236.0 mm).

### Wheels, tyres, weight
- 5J x 14 (pressed steel or alloy), 175/65 HR 14.
- Cold pressures 175/65 HR14: normal 1.8 bar front / 1.6 bar rear (26/23 psi); fully loaded 2.0 / 2.2 bar (29/31 psi). Use 1.8/1.6 as the AC starting pressure reference.
- Kerb weight Nova GTE 3-door 834 kg (confirms brochure). Rear track 1300 mm (hatchback, 1991 on; check vs 1989). Towing: 800 kg braked.

### Suspension geometry (laden = two front occupants + half tank)
| Item | GTE value |
|---|---|
| Front camber | 0 deg 45' neg to 0 deg 45' pos |
| Front castor (1988 on) | 0 deg 45' pos to 2 deg 45' pos |
| Front toe (Ch.8) | unladen 0.5 mm in to 1.5 mm out; laden 0 to 2.0 mm out |
| Rear camber (1987 on) | 0 deg 40' neg to 1 deg 35' neg |
| Rear toe (GTE/GSi) | 0 to 4.0 mm toe-in |
| Front camber/castor | not adjustable |
Haynes closes the old alignment GAP. Starting values for AC (ESTIMATE from the ranges): front camber -0.3 deg, castor 1.8 deg, front toe about 1 mm out, rear camber -1.1 deg, rear toe about 2 mm in.

### Steering
- Ratio 21.4:1; 3.8 turns lock to lock (Haynes) vs 3.9 (brochure) = CONFLICT, trivial; use 3.8. Rack centring 419-422 mm.

### Torque settings (Nm), for detail modelling
Wheel bolts 90; strut-to-knuckle 110; control arm pivot 75; tie-bar/balljoint nuts 100; knuckle clamp bolt 30; strut rod nut 55; strut top nuts 30; rear axle pivot 105; rear shock lower bolt 60.



### Other sources checked 2026-10-12
- ultimatespecs / auto-data: 101 PS @ 5600, 135 Nm @ 3400, 117 mph, 0-60 9.1 s, wheelbase 2343 mm, 42 L tank, front discs and rear drums, no ABS on the 1989 car. SOURCED, agrees with the sheet.
- Classics World: springs 35 percent stiffer than the SR, bigger anti-roll bars, 3.8 turns lock to lock, no power steering. Supports the derived rates.
- migweb, corsasport, carfolio and Parkers block automated fetching: not worked around.

