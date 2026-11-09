# Replica plan - from "getting there" to an accurate Nova GTE

Written 2026-10-27. Read with `docs/DETAIL_MAP.md` (every feature, its source, and the model's state now).
Status: **proposal for Nik**. Decisions needed are at the end.

## 1. Where we are, honestly

The side silhouette between the axles is right - it overlays the line blueprint closely - and so are the hard
points, wheels, front bumper and bonnet shut. What makes it read as "not a Nova" is, in order:

1. the **rear end** (split tailgate, triangle glass, no black panel, no spoiler, lamps unreadable);
2. **no colour/trim breakup** - the Nova is recognised by its black frames, B-pillar and rear panel, grey skirts
   and valances, red pinstripes, white griffins, amber and clear lenses;
3. **broken glass** (see-through fans in the screen and tailgate, shards in the side glass);
4. the **front face** (flat white lamps, plain grille, no griffin, bonnet reading lumpy);
5. **missing signature shapes** - spear creases, quarter-light and division bar, sunroof, roof spoiler;
6. **surface quality** - every body part except the bumper is built point by point in numpy, so it ripples and
   stair-steps, and each fix has needed another patch (rolled edges, gutters, culls, trace fits).

Point 6 is the root. The bumper looks right because it is one section swept along one measured path. That is how a
car body is really defined: a small network of **character lines**, with smooth surfaces stretched between them.
We have the tool for that and have barely used it.

## 2. The approach: a CAD surface model, driven by measured curves

**FreeCAD 1.1.4 is installed (`D:\FreeCAD`) and was tested headless on 27 Oct:** B-spline surface
interpolate/approximate through point grids, filled patches from a curve network, the Surface workbench
(Filling, GeomFillSurface, Sections, Extend, Cut), projecting a shut line onto a face and splitting the panel on it,
thickening a panel to a valid solid, point-to-surface distance, tessellation to mesh, and the Inspection,
ReverseEngineering and TechDraw modules - all work. Two limits found: filleting a thin panel's edges gave an invalid
solid (so hems/rolled edges will be swept sections, see 4.4), and the free *Curves* add-on (Gordon surfaces) is not
installed - optional, free from the Addon Manager.

So the body moves out of numpy and into FreeCAD, scripted (`freecadcmd`, everything in `tools/cad/`, rebuilt by
one command like `rebuild_body.sh` today). Blender stays for what it is good at: details, materials, UVs, looking
at it, and the AC export.

```
 drawings + photos          FreeCAD                          Blender                        AC
 (traces, BA points)  ->  character-line network  ->  panels (NURBS) -> mesh  ->  details, trim, glass,  ->  kn5
                          surfaces between lines      split on shut lines         materials, UVs, LODs
                          checks vs every source      gaps, hems, flanges
```

What carries over unchanged: the photogrammetry (7 solved cameras, 34 points, all the tools), every trace in
`blender/data/` (they become curve inputs), the GA rectification and calibrations, `trace_fit.py`, the wheels, the
mirror measurements, the front bumper and grille (`front_end.py` - already the right method; re-host it later), the
check tools (geo_check, match_look, overlays) and the AC export pipeline.

## 3. The measurement foundation (do first)

1. **One frame for everything.** Car faces -Y, Z up, origin on the ground midway between the axles, unloaded tyres
   (model z = photo z + 0.0193). Put every drawing into it: GA side, front, rear and **plan** (rectified, scaled
   per its own dimension marks - along-car 3.497 mm/px; across-car fitted to the sourced widths, as
   `trace_plan.py` already does), and the line blueprint side/front (5.36156 mm/px, axles pinned). Output: one
   calibration file `tools/cad/frame.json` and the views as scaled images FreeCAD and Blender can both load.
2. **Cross-check drawings against photos before trusting either** (`bp_on_photo.py`) - the rule that already caught
   two frame errors.
3. **More photogrammetry where the drawings say nothing** - the rear (glass corners, black panel corners, spoiler
   tip, lamp corners, plate), the spear-crease end points on both wings and quarters, quarter-light corners and the
   division bar, sunroof corners, B-pillar top/bottom, fuel flap centre, door handle, GTE decal corners, griffin
   decals. Mark them in the 7 solved photos with the existing marksheet / marktiles tools and re-solve (ba2.py).
   Target: every point seen by at least two non-parallel cameras (MIR, BON_F, PNL_B, DSR_B are single-view and
   must be re-marked or dropped).

## 4. Build order

Every step ends with something Nik can look at, side by side with the photos, before the next starts.

### 4.1 The character-line network (the "wire frame" of the Nova) - the key checkpoint
Each line is a 3D B-spline made from **two orthographic traces** (side + plan, or side + front - the standard
blueprint method), snapped to BA points where they exist, fitted (not smoothed) within one drawing pixel
(`trace_fit.py`):

- centreline profile (roof, screen, bonnet, nose; tailgate, tail)
- plan outline at the widest line, at the belt, at the roof edge
- belt line; **spear creases** (front wing and rear quarter, with their tapered ends)
- sill line and rocker; arch outlines (front and rear, with the flange line)
- DLO: windscreen, **quarter-light + division bar**, drop glass, rear quarter window, tailgate glass
- A-, B-, C-pillar edges; roof drip lines; sunroof opening
- shut lines: bonnet, wing-to-door, door front/rear/bottom, tailgate (top, sides, bottom), fuel flap
- front: bonnet V, lamp-panel outline, grille opening, bumper top and bottom; rear: black panel outline, lamp
  outlines, bumper top and bottom, spoiler edge

Checkpoint: the curves alone, rendered over the GA side/front/rear/plan and through all 7 cameras onto the photos.
**If the wire frame looks like a Nova from every camera, the surfaces will.** Nothing gets surfaced until it does.

### 4.2 Surfaces
Patch by patch between the curves, G1 (tangent) across every shared boundary: body side (door + quarter), roof,
bonnet, wings, tailgate, front and rear ends; the GTE flares and spear creases as their own narrow transition
patches so they stay crisp. Each patch is checked for curvature and with zebra stripes (a striped environment in
Blender) - waves show immediately.

### 4.3 Panels
Split the surfaces on the projected shut lines into the real panels: bonnet, 2 wings, 2 doors, tailgate, 2 rear
quarters + roof (one piece with the body), bumpers, skirts, spoiler. Gaps by offsetting the shut curve on the
surface (4 mm bonnet/doors, measured per shut where photos allow). Doors and tailgate as separate parts so they can
open in AC later.

### 4.4 Thickness, hems and flanges
Thicken panels (tested OK). Hems and the arch flanges as a profile swept along the trimmed edge (FreeCAD pipe
shell) rather than fillets, which failed on thin panels in the test - prove this on the bonnet first. If it
fights us, tessellate and keep `roll_edges.py` for this one job.

### 4.5 Glass and black trim
Glass panes made from the same DLO curves as the openings (so they cannot disagree), proper surfaces, not fans -
this also ends the see-through bug. Rubber seals and black frames swept along the DLO; black B-pillar applique,
quarter-light division bar, belt seals, roof drip strips.

### 4.6 Details (Blender or CAD, whichever suits each part)
Headlamps (lens with the fluted pattern, H4 reflector, bezel), indicators, tail lamps (4 bands on GA heights, black
surround, lens optics), slatted grille + chrome GTE badge, griffin decals (bonnet, tailgate), GTE door decals (grey
outline italic), rear GTE badge, handle strip, plates and plate lamps, side repeaters, door handles, mirrors
(already measured; refine the sail/gasket), wipers (tandem front, single rear), scuttle diamond grille and washer
jets, sunroof glass and seal, roof spoiler, fuel flap, tow eye, single tailpipe, wheel-arch liners, simplified
underside.

### 4.7 Colour zones and materials
Gunmetal metallic paint; matt black (rear panel, B-pillar, frames); grey plastic (skirts, valances); red pinstripes;
chrome badges; green-tint glass; lamp lens materials; rubber. Checked against R##/cS/cAR with match_look in the
paint colour of each photo, then switched to gun-metal grey.

### 4.8 Then the rest of the car (separate tracks)
Interior (RHD, from R08-17 and the brochure), engine bay (R28-32 and the reference pack), AC conversion (UVs, LODs -
the old installed build was 1.3 M tris / 47 MB, far too heavy for online racing; collider, lights, animations), physics and sound - the existing
plans in `docs/PHASES.md` stand.

## 5. How accuracy is judged (every step)

| Check | Tool | Target |
|---|---|---|
| Distance from the surface to every BA point (two-view points only) | geo_check.py / FreeCAD distToShape | <= 5 mm median, no point over 10 mm (now: 9.3 mm median, 16 points over 15 mm) |
| Orthographic overlay on GA side/front/rear/plan and the line blueprint | blueprint_overlay.py, TechDraw views | within one drawing line (~5 mm) between the axles; overhangs from GA/FIA, not the line blueprint |
| Render through each solved camera next to its photo, and outlines drawn on the photo | match_look.py, overlay_edges.py | silhouette and every panel line within ~5 px; the photo and the render read the same |
| Surface quality | zebra / curvature in Blender | no waves, steps or kinks except the real creases |
| Nik's eye, close up, one area at a time | - | it looks like his car |

A change that improves the numbers but looks wrong is wrong (Nik, 19 Oct).

## 6. Order of work and rough size

| Step | What Nik sees at the end | Size |
|---|---|---|
| 3. Measurement foundation | all drawings in one frame; new BA points on the rear, creases, quarter-light, sunroof | 1-2 sessions |
| 4.1 Curve network | the Nova as a 3D wire frame over every drawing and photo | 2 sessions |
| 4.2-4.3 Surfaces and panels | a smooth grey body with real shut lines | 3-4 sessions |
| 4.4-4.5 Hems, glass, black trim | the body with glass and frames - the first time it should *read* as a Nova | 2 sessions |
| 4.6-4.7 Details and colours | the exterior finished, compared photo by photo | 3-4 sessions |
| AC | drivable in AC with the new body, LODs | 1-2 sessions |

Until 4.5 is done, nothing more is patched on the numpy shell - each patch has been working around the method.
The one exception worth doing at once is the glass (a proper fill instead of a fan), because it is cheap and it is
in every picture.

## 7. Decisions for Nik

1. **Move the body to FreeCAD (curve network -> NURBS surfaces -> panels)?** The current build would be kept for
   comparison until the new one beats it on every check.
2. **Colours and trim now?** The working rule has been "shell only, no painting". Much of the likeness is the
   black/grey trim, so I'd like to build the trim as separate parts with their plain colours from step 4.5 (no
   textures yet).
3. **Pre-facelift detail:** the GA sheet is the Nov 1990 facelift. Front and rear detail comes from your car and
   the anglia/commons photos - confirm that is what you want matched.
4. **Free add-on:** OK to install the FreeCAD *Curves* workbench (free, Addon Manager) if the built-in surfaces
   struggle with the multi-sided corners?
5. **More photos (optional, free):** a straight-on side and a high plan-ish shot of your car, and close-ups of
   the quarter-light/mirror sail, rear spoiler, roof drip, fuel flap and door handle, would tighten the weakest areas.
