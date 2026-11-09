1989 Vauxhall Nova GTE — RHD interior / dashboard reference pack
=====================================================================

Purpose
-------
Research pack for recreating a standard, UK right-hand-drive 1989 Nova GTE interior in Blender.
This pack contains a local HTML reference board with direct image links and source pages, plus
a modelling/scaling note. The source photos are hosted by their original publishers; they are
not embedded locally because this runtime could not retrieve the image files directly.

Most useful visual references
-----------------------------
1. Anglia Car Auctions — 1989 Nova GTE, driver-side dashboard / steering wheel / instrument cluster:
   Image: https://angliacarauctions.co.uk/images/lots/2598/2588~1/0019_QzSgXp_lg.jpeg
   Source page: https://angliacarauctions.co.uk/auctions/2598-19-Aug-2023/2588~1-1989-vauxhall-nova-gte

2. Anglia Car Auctions — wider dashboard, front seats and console:
   Image: https://angliacarauctions.co.uk/images/lots/2598/2588~1/0018_BIojSt_lg.jpeg
   Source page: https://angliacarauctions.co.uk/auctions/2598-19-Aug-2023/2588~1-1989-vauxhall-nova-gte

3. Anglia Car Auctions — seats and door card trim:
   Image: https://angliacarauctions.co.uk/images/lots/2598/2588~1/0017_fTojcv_lg.jpeg
   Source page: https://angliacarauctions.co.uk/auctions/2598-19-Aug-2023/2588~1-1989-vauxhall-nova-gte

4. Manor Park Classics — dashboard and centre console view:
   Image: https://goauctionmpc.blob.core.windows.net/stock/2817-5.jpg?v=63863285174253
   Source page: https://www.manorparkclassics.com/auction/lot/lot-65---1989-vauxhall-nova-gte/?lot=2852&sd=1

5. Car & Classic — another 1989 GTE dashboard angle:
   Image: https://assets.carandclassic.com/uploads/new/15993621/17f98d15-6b4e-4bc0-8936-473441afc223.jpg?fit=fillmax&h=1200&ixlib=php-4.1.0&q=85&s=9957831f680e1035c888a5e1c0f90c09&w=1200
   Source page: https://www.carandclassic.com/auctions/1989-vauxhall-nova-gte-nQYXxn

6. October 1989 UK Vauxhall Nova colour sales brochure (includes GTE; potentially useful for factory trim):
   https://www.carandclassic.com/car/C1432255

What the photos show
--------------------
- UK RHD layout: steering wheel and instrument binnacle on the right.
- Grey dashboard / centre stack; three-spoke Vauxhall wheel; analogue instrument cluster.
- Period cassette-radio position, central vents and heater controls.
- Manual gear lever and simple centre console.
- Grey cloth sports seats with red/grey striped inserts and coordinated door cards.
- These are surviving cars and may have age-related changes. Use the period brochure and multiple photos
  to check details; do not copy aftermarket radios, alarms, mats or modifications as factory equipment.

Important: scaling
------------------
Do NOT treat a perspective interior photo as a dimensionally accurate orthographic blueprint. The camera
angle and lens distort proportions, and the photos do not include a known-size reference in the same plane.

Useful published exterior envelope dimensions commonly listed for the Nova hatchback:
- Overall length: approximately 3,810 mm
- Overall width: approximately 1,610 mm
- Wheelbase: approximately 2,343 mm

These are whole-car dimensions, not dashboard measurements. Confirm against a reliable factory manual or
measurements of an actual car before using them as hard constraints. For Blender, set units to Metric and
work in metres (e.g. wheelbase 2.343 m) or millimetres consistently.

Recommended dimensioning workflow for Claude Code / Blender
------------------------------------------------------------
1. Build the shell or floorpan first and set wheel centres 2.343 m apart as a provisional reference.
2. Establish the steering-column centre on the RIGHT side. Never mirror a left-hand-drive dashboard photo
   blindly; some details and trim parts may differ.
3. Use front-on photos for dashboard width and component placement only if the camera is close to square-on.
4. Use side-on views for seat/console relationships; use close-ups for vents, switchgear, radio aperture,
   gauge layout, steering wheel and upholstery pattern.
5. Keep dimensions of dash, wheel, seats and console as provisional parameters until verified from a manual
   or physical measurements. Do not infer millimetre precision from auction photos.
6. Model the standard trim first: avoid aftermarket steering wheels, bucket seats, harnesses, carbon trim,
   modern head units and non-original gauges.
7. Keep photo-derived measurements labelled as estimates in the .blend file and in any generated scripts.

Image usage / rights
--------------------
These photos are linked from auction/listing pages and remain owned by their respective rights holders.
This pack is a research index, not a grant of permission to redistribute the photographs. Follow each
publisher's terms and obtain permission if redistributing or publishing renders that reproduce protected
photographs closely.
