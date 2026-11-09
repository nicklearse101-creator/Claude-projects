# Decisions log

Record non-obvious choices here: what was decided, why, and what the alternatives were.

## 2026-10-06
- Spec base is the 1989 model year (Vauxhall brochure Oct 1988); car id and folders renamed to vauxhall_nova_gte_1989.
- RHD (UK spec), factory 5J x 14 alloys, pre-facelift, no ABS, sunroof fitted.
- No paid services: blueprints come from free sources only (the-blueprints.com has no Nova drawing on page 1 of Vauxhall; check page 2), otherwise photo-driven modelling scaled to the sourced dimensions.
- Paint: Steel Grey metallic is the period reference for gun-metal grey (PNG chart code 114/82, 1991-94).


## 2026-10-12 - Phase 1
- Phase 1 box car loads in AC (Nik). Steering was reversed with the tie rods behind the axle (realistic: Haynes shows the rack bolted to the bulkhead). AC's rack only pushes one way, so the steering points were mirrored in front of the axle (z positive, same side as Kunos' Escort format reference). Tie-rod end set 10 mm outboard of the balljoint for Ackermann. Revisit if a cleaner way to model a rear rack is found (e.g. a negative STEER_RATIO), checking FFB and wheel animation.
- Git repo started at the project root (local identity Nik). reference/manuals/ is ignored (copyrighted scans).
- Overhangs CONFLICT: FIA A-5375 says front 670 / rear 609 mm, but the GTE side photo (anglia_side.jpg, camera centred on the car) and the brochure dimension drawing both show front and rear overhangs about equal. Kept the sourced 3622 mm length and 2343 mm wheelbase and split the overhangs as the photo shows them (front ~= rear ~= 0.64 m). The photo's ends are also foreshortened by perspective (close camera), so tools/trace_side.py maps it with a smooth odd cubic anchored on the wheel centres and the bumper faces, and vertical scale from the brochure height (1.365 m).
- Body greybox is a scripted loft (blender/scripts/build_body.py) from tools/features_side.json; glass, trim, lamps, skirts and door shut lines are material zones on the shell for now. Wheels (build_wheels.py) are the GTE three-arm alloy read off close-ups of F400 PTF; right-hand wheels are rotated copies (same handedness), brake parts are mirrored.
- Triangle budget note: the polar-grid alloy face is ~15k tris per wheel - rebuild with proper edge-following geometry and LODs in Phase 3/9.

## 2026-10-12 - Shell refit to the photos (task 12)
- Photo cameras: bundle adjustment (tools/photomatch/ba.py) on 7 photos; body points in a photo frame whose ground and wheel centres come from F400 PTF (loaded wheel centre 0.272 m). The model sits on unloaded tyres, so all photo heights are lifted by DZ = 0.0193 m (tools/photomatch/body_profile.json "dz").
- The telephoto front 3/4 (cCF) and the rear-only user photos (c23, c24) are too weak for the global solve; cCF is re-solved alone against the fixed points (tools/photomatch/solve_cam.py) with extra annotations (wheel centres/rim edges, handle, repeater, side glass corners). Expect 1-3 cm camera noise in those views.
- Length CONFLICT resolved to the photos: bumper faces at y -1.775 / +1.766 (3.54 m) against the FIA 3.622 m. The front plate, lamps, grille and rear lamps all sit where the photos put them.
- Shell rebuilt: blender/scripts/body_geom.py (pure Python, shared with the photo-overlay preview tools/photomatch/preview.py) + build_body.py (cut lines, grooves, Blender mesh). Profile numbers in body_profile.json, sources tagged there. Side-view outline error vs anglia_side.jpg: 0.8 cm mean; other views 1.7-2.6 cm (camera noise level).
- End corners: the plan sweep is height-independent (a z-dependent sweep sheared the corners into a visor/fold). This is a compromise of about 2.5 cm between the BA lamp corners (lamps recede more) and the BA bonnet corner (further forward).
- Glass sits about 6 cm inboard of the body side at the belt (BA glass corners); the door top is a rounded shoulder that leans in about 30 degrees from the crease (photos cAR / c22), not a flat shelf.
- Real geometry now: V-groove shut lines (doors, bonnet sides/front/rear, hatch, bumper joints, sunroof, skirt top) and GTE bumper ribs (5 front, 5 rear). Lamp/indicator/grille/tail-lamp openings are cut out of the shell and filled with lamp units (lens, chrome reflector, housing, bulb) in build_details.py.
- Bonnet 'beak': the bonnet front edge dips about 1.5-3 cm at the centre (photos c20 / c22). The two longitudinal bonnet creases are a 7 mm step.
- Rear bumper joint at z 0.560 (under the tail lamps, photos cAR / c24), not at the black panel's lower edge (0.60).
- The Inner solidify no longer uses even thickness (it exploded at the closed ends). Arch liners are separate black tubs because the Boolean on the open shell leaves no wall.
- Device file commits from a re-used staging path can deliver a stale copy: always stage changed files under a new folder (outputs/vHHMMSS/) before committing.

## 2026-10-12 (evening) - Front end corrected against the photos (Claude Code session)
- Checked the two plan folders: `D:\Claude\nova-gte` is the original chat plan (1990 spec, nothing built). Everything
  in it is already in this project, which evolved from it; the one real change is the 1990 -> 1989 model-year
  decision (06 Oct). The build stays on the 1989 spec / car id.
- Overall length CONFLICT revisited: the side photo (anglia_side, cS camera fits both wheel centres to the pixel)
  puts the bumper ends at about 3.60 m, inside the FIA 3622 mm +-1 % tolerance; the model is 3.58 m (front ~1 cm,
  rear ~1 cm short at the corners). Kept for now; revisit with the rear-end rebuild.
- Bonnet front: BA point BON_F (0.599, -1.728, 0.757) was ~6 cm too far forward and ~4 cm too high (depth ambiguity
  of the front views). The real outer corner sits right on the indicator/headlamp top: triangulated from cS + c20 at
  (0.61, -1.663, 0.718). With the centre tip (0, -1.777, 0.740) the front edge is a straight V (plan slope 0.187),
  which overlays the edge in c20, cCF and c22. The nose crown is a near-linear 10 cm drop with a rounded centre
  ridge, blended by shape with an ease-out to the normal bonnet crown by y -1.30 (convex everywhere: no ripple).
- Front wing taper: in the straight-front photo (c20) the indicator's outer edge IS the body silhouette at lamp
  height, so the wing side runs back from the indicator wrap end at <= 0.42 (camera-ray bound) to full width near
  y -1.50. The wing cross-section is shifted inward (keeps its tumblehome), pulled exactly onto the indicator wrap
  line over the lamp height and blended back within 5 cm. Replaces the old plan-rounding clamp, which collapsed the
  side rows into a flat slab and tore the bonnet/wing/indicator corner.
- Front trim: above the indicator top the V edge trims bonnet and wing corner (12 mm lip, never below the lamp tops);
  below it the wing ends on the wrap line with a 7 mm turned-in hem, wraps forward under the indicator to the lamp
  panel, and the lower wing between bumper end and arch is removed (it hung below the bumper).
- Grille surround: two-view triangulation (c20 + cCF) - opening +-0.341 x 0.573-0.650 (agrees with BA GRO_*), face
  raked like the headlamps (0.33) and V-shaped in plan (0.15), groove across the top bar at z 0.666, top edge rising
  from 0.695 to ~0.717 under the bonnet lip.
- Bumper: the side return measured in cS and cCF (mirrored two-view, gaps <= 1.7 cm) has the ribs at z 0.441-0.483,
  red edge 0.311, lip 0.227 - 2-3 cm lower than the front face values, which stay where c20 + cCF put them; the
  profile blends between x 0.50 and 0.72. 25 mm return flanges at the arch ends.
- Blender 5.2 renamed Mesh.set_sharpness_by_angle to set_sharp_from_angle; the part loaders silently skipped it, so
  every generated part was smooth-shaded across hard corners (lumpy grille/lamps). Fixed in build_front/build_wheels.
- Local tool env: the tools were written in the cloud sandbox; `.venv` (Python 3.13 from Blender, numpy/scipy/
  shapely/triangle/opencv-headless/pillow) reproduces front_end.json byte for byte. Scripts run in headless Blender
  (`blender -b blender/nova_gte.blend --python ...`), not through the Blender MCP plugin.
- deploy.py now archives the installed car to export/deploy_backups/<time>_BACKUP_installed_before_deploy and lists
  any installed file that differs from the project. (The 22:43 deploy replaced an installed data/ folder that had a
  change at 18:52 not in the project, without a copy - see the session report.)

## 2026-10-12 (late) - Bonnet and front bumper per Nik's review
- Nik: "the only crease in the bonnet should be running lengthways"; the nose had a raised centre (linear crown
  with a centre ridge). Bonnet section rebuilt: gently crowned centre panel (8 mm) between two lengthways creases
  (traced in c20: x 0.379 at y -1.661 diverging to 0.498 at the screen base), straight outer panels to the shut line
  (3.0 cm drop, matches the cS / c22 shut-line heights).
- Nose re-measured: the c20 tip ray meets the cS silhouette at (0, -1.755, 0.727) - the earlier tip (-1.777, 0.740)
  came from front views only and stuck ~10 px above the side silhouette. Along the corrected straight V (a 0.151,
  corner at the lamps) both photos put the edge level at z 0.722 +- 0.004; the surface rolls down to it over the last
  12 cm (convex, no ridge). Grille surround top lowered to sit under the lip.
- Front bumper lower edges: Nik saw them bowed up in the middle (lip rose 4.3 cm to the centre). Two-view at the
  centre: red/grey 0.325, lip bottom 0.255; nearly level across, ~1 cm lower at the corners, ~2 cm at the side return.

## 2026-10-12 late - bumper rib stripes level
Nik: the red rib lines on both bumpers run straight from end to end, not dipping. The photo measurements disagreed
by ~2 cm between the centre and the side returns (front: centre two-view c20 + cCF 0.497-0.4655, side ~0.476-0.4445;
rear: cAR centre 0.498-0.460, cS side 0.519-0.485). Ribs are now one level band per bumper at the mean of the two
(front 0.4865-0.455, rear 0.5085-0.4725, ESTIMATE, within ~1 cm of each view). Top and lower edges keep their
measured centre/side heights.

## 2026-10-13 - alloy wheel face re-measured
The anglia_side (cS) front-right and rear-right wheels were rectified onto the wheel face plane (the camera is almost
perpendicular) and the openings fitted to the photo grey levels on both wheels (tools/wheel_face.py docstring).
Arm width and the window layout were close; the real changes: slots +-24 mm from the arm axis (were +-38 mm, at the arm
edges - the arms read as thin bars), 17 mm wide, r 80-160 mm; window outer radius 153 mm (was 165); 6 mm fillets; the
centre cap is not a separate small pentagon - it has straight edges across the arms at 73 mm and the windows bite
V-notches into its other sides (checked on the sharper cCF front-left wheel). Cap material now the same silver as the
face (photos). Brakes: darker cast iron and a black backing plate / dust shield behind the drum/disc (ESTIMATE shape)
so the openings don't show the arch behind. The EEVEE look-dev still lights the drum (no occlusion); AC's shadows will
darken it - check in game.

## 2026-10-13 - windscreen base, scuttle and bonnet rear edge
The model had a straight screen base at y -0.70, a black scuttle band and a straight bonnet rear edge at -0.765. Photos:
the centre wiper pivot triangulates (c20 + cCF, ray gaps 2-6 mm) to (0, -0.800, 0.933) and the washer jets to
(+-0.175, -0.811, 0.928) - both were on the model's bonnet. The scuttle is a body-colour panel with a row of vent
louvres just ahead of the screen seal (c20, cCF - not black), and the bonnet rear edge is curved in plan (centre ~-0.90,
~-0.83 at the crease ends). Now (body_profile scuttle_curve): bonnet rear edge y = -0.90 + 0.33 x^2 (groove polyline),
screen base y = -0.74 + 0.29 x^2 capped at the old -0.702 towards the corners (the screen and A-pillars there matched
the photos; moving the corners twisted the screen against the A-pillar), the loft's screen surface kept and extended
down at its own slope, scuttle panel from 6 mm under the bonnet edge to the base, 4 mm riser + 12 mm black seal.
The base position is a compromise: the pivot/seal positions alone say -0.76..-0.78, the scuttle height (pivot and
louvre rows in both photos) with the unchanged screen surface gives -0.74. New parts: SCUTTLE_VENT (louvres, jets),
wipers rebuilt with pivots 60 mm ahead of the base and arms to the blade centres.
The interior dash ends (x +-0.64) poke out through the A-pillar bases - fix in the interior pass.

## 2026-10-13 - interior fitted to the body
The dash ends (x +-0.64) poked 10 cm out through the A-pillar bases and the floor pan's rear corners went into the rear
wheel houses. build_interior now measures the cabin's inner surface (rays from the centreline onto BODY_shell with its
Inner solidify / BODY_glass) and lofts the dash profile across it, so every dash row ends on the inner skin; the door
cards and rear quarter trims are panels 12 mm inside the inner skin (padded upper band, red pinstripe, diagonal pull,
release lever, winder, map pocket - photo 14); the rear floor is narrowed between the wheel houses. A check script
(no vertex of any INTERIOR part outside the inner surface) passes. Shapes are still first-pass (seats, binnacle).

## 2026-10-13 - shell round 2 (Nik: roof, rear, wavy scuttle, wing steps)
- **Wavy scuttle/bonnet edge:** the curved bonnet rear edge and screen base had been cut across the loft rows,
  leaving sliver faces that shaded as a dashed, wavy band. Now the loft keeps straight rows there and build_body
  bends the rows themselves onto the plan curves (warp_scuttle, like the end sweeps); heights are resampled from the
  unbent surface, so the bonnet and screen keep their shape. Car-paint matcap check: smooth.
- **Wing steps (flares):** both wings have a flared lower panel under a crisp step (photos). Step height from cS
  rays on the shell (checked against the side repeater, 5 mm): front 0.700-0.704, rear 0.680-0.689 (photo frame).
  Step ~12 mm, flare blends back by z 0.47 so the FIA maximum width (1535 mm at the front wing) is unchanged;
  fades towards the doors and at the lamp ends. The side profile got three more rows (ledge + flare), which also
  removes some of the banding on the sides. ESTIMATE size.
- **Tailgate glass:** corners triangulated c24 + cAR: bottom +-0.555 at z 0.905 (= BA HG_B), top +-0.40 at z ~1.225
  (the model had +-0.525, square corners). Now an inset panel (glass_panels.py): rounded outline, glass recessed
  12 mm in a black rubber channel, shell holed underneath (ragged hole edge hidden by the seal). The C-pillars are
  now the broad body-colour wedges of the photos.
- **Roof lip:** the separate plate on the roof replaced by the roof's rear edge carried ~2 cm over the recessed glass
  top, kept low enough not to change the measured roof silhouette.
- **Sunroof:** same inset-panel treatment (rounded corners, seal), dark tinted glass (blind under it). Position
  unchanged (fore-aft not measurable from the photos).
- **Roof drip rails:** body-colour rail with the dark gutter line along each roof edge, ~2.6 cm above the window
  frame tops (cS: line within ~7 mm).
- **Windscreen surround:** black rubber along the header and up both A-pillars (c20 / cCF / redgte_21).
- **Boot trim:** handle bar re-measured on cAR (x +-0.32, z 0.750-0.789, round ends) with the lock; GTE letters
  built as strokes at x 0.384-0.543 (was a plain block); parts follow the panel's plan sweep.

## 2026-10-13 - wheel arches traced, bonnet waves fixed (Nik: rear arch flat, bonnet still wavy)
- **Arches:** the fitted circles were wrong - the rear arch top sat 6 cm too high (0.621 vs 0.561) and round,
  while the real rear arch is flat-topped at tyre-top height with the bumper end as its rear edge. Both lip outlines
  are now traced on cS (luminance edges by column and row, cross-checked with the earlier hand trace) and stored as
  polylines (body_profile arch_shapes). Everything that used the circles now uses them: shell cutters, front/rear
  cut kills, groove masks, bumper ends (front_end / rear_end arch_end), skirt ends, liners. Liners are tubs that open
  out 35 mm / 80 mm inside the lip so the tyre (top ~ lip top, as on the real car) clears them.
- **Bonnet waves:** cause found - the centreline was a monotone spline through 6 photo points and its curvature
  jumped by 4x between knots; reflections showed every jump. One quadratic (constant curvature) fits all six points
  within 1.3 mm, so the bonnet now uses that fit analytically (top_bonnet_fit). The nose roll-down is (1-s)^3 over
  0.15 m (was squared over 0.12 m), so its curvature fades to zero instead of stopping in a line. The scuttle row
  bend was ruled out (stripes identical with it disabled). Stripe renders: even, straight, creases crisp.

## 2026-10-13 - tailgate, roof visor, C-pillars (Nik: boot area and roof nothing like the real car)
- **Roof visor:** the spoiler is the roof's own end, flush with the roof line (side photo: no raised blade), trailing
  edge at y 1.375 (cS silhouette corner) / z ~1.27 (c24 + cAR triangulate the underside at 1.275, ray gap 1 mm),
  ~12 mm red edge face, black underside; ends run out into the pillar tops.
- **Tailgate glass:** recessed 35 mm below the tailgate surface with body-colour walls and a 12 mm black seal
  (glass_panels wall_seal), so it sits deep between the pillars and under the visor as in c23/c24/redgte_25.
  Outline overlays on cAR / c24 match within a few px.
- **Tailgate shut line:** triangulated from cS (mirrored) x cAR as a 3D line (fit residuals 2-3 px): 45 deg, parallel
  to the quarter-glass rear edge and ~15 cm behind it, running into a top shut line across the roof at y 1.19. It
  was a vertical cut at x 0.585, 12 cm too far back, which made the pillar's side face 2.4x too wide.
- **Flat pillar fins:** the hatch crown no longer drops 4-5 cm at the edges beside the glass (hatch_fin).
- **C-pillar facets:** where the tailgate slope cuts down through the side rows, the cut segment's rows are now
  re-spaced evenly up to the cut (clamp_top) instead of collapsing at the crossing point, which made the rows jump
  between stations (twisted faces, faceted reflections). Stripe check: much smoother; small kinks remain at the
  roof corner.
- **Rear wiper:** re-seated on the recessed glass, parked along its bottom with the arm to a pivot under the glass.
- Not yet: the pillar's lower tip forming a ledge over the tail lamp, tail-lamp surround shape.
- Follow-up: the tailgate side shut line now stops at the tail-lamp top (below it the body corner turns hard and the
  groove crumpled it); the horizontal groove at z 0.815 across the tailgate is gone (no such line in c24 / cAR); the
  flat-fin crown blends in/out over 12 cm / 4 cm at the very tail (a 5 cm ramp twisted the lower pillar).
- Glass openings (tailgate, sunroof) are cut by exact Boolean prisms along the outlines (CUT_glass_*), not by
  deleting faces - clean rounded edges, smooth recess walls. Tail lamps got the black surround and thin black
  dividers between red / amber / clear (photos), lens bands 20 / 45 / 100 %.
- Shading normals: the zone cuts and the pushed-in shut-line grooves sliced the C-pillars into slivers that shaded
  as zigzags. BODY_shell now ends with a Data Transfer modifier taking custom corner normals from a hidden smooth
  copy of the shell before the grooves are pushed (BODY_normals_src, outer skin within 6 mm only, so the inner layer
  keeps its own). Panel gaps stay visible through their black material. The kn5 writer reads corner normals, so AC
  gets the same shading (export checked: 155 meshes, 345k tris). Limited by a vertex group to the rear sides
  (y > 0.30, z 0.80-1.27, smooth non-boundary vertices only): applied everywhere it sawed sharp edges and folds.

## 2026-10-13 - rule change: Tripo / Meshy generated meshes allowed
Nik changed the "modelled entirely from scratch, no imported meshes" rule: AI-generated meshes from Tripo or Meshy,
made from our own reference photos / blueprints, may be used (still scaled, aligned and checked against the photos and
the FIA dimensions). Also fixed: build_details deleted the front indicators (INDICATOR_F_L/R from build_front) via a
legacy name list whenever it ran after build_front.

## 2026-10-13 - round 4 (Nik: "looks like a Nova that's been in a crash")
- Root cause of most of the "crash" look in my images: lookdev.render() never called setup(), so every photo-matched
  comparison used the raw build materials (near-clear glass showing a brightly lit cabin = "pale crumpled pillar",
  flat paint). Fixed; the comparisons now show what the model is.
- Real geometry faults fixed: X-shaped folds on the C-pillars (glass bulge cut off by the tailgate truncation + the
  pushed-in diagonal shut line) - the bulge now shrinks with the truncated segment and the pillar groove is gone;
  two lines on the wings (step at 0.70 + old crease at 0.728) merged into one measured shoulder crease / step line
  (crease_z), 8 mm step on the wings only; spoiler lip thicker with a body-colour trailing face; no shut line across
  the roof; drip rails taper into the skin at their ends; tailgate glass corners tighter (25 / 40 mm).
- Front indicators restored (build order bug, see the rule-change entry).

## 2026-10-13 - Nik's worst areas: rear end, roof & glass, wing mirrors (red side-by-side review)
- Side windows: glass top re-measured on cS (colour scan above the windows) - ~3 cm lower than the old cant line;
  the side now has the black window frame, a body-colour band and the drip gutter above the glass, as on the car.
- Mirrors: rebuilt to the photo size - 17 cm long (y), 12 cm tall wedge, 16 cm out from the door, glass on the rear
  face, black base under the housing (was a 9 cm rounded box on a stalk).
- Tailgate glass: wider top (+-0.44), black border / recess instead of body-colour walls.
- Tail lamps: recessed 14 mm in a black surround with dividers, widened to the body corner (x_out 0.712), black rear
  panel only between the lamps (the zone used to run out past the lamps to the corner).
- Look-dev: lens colours, lighter reflective glass (cabin visible as in the photos).

## 2026-10-13 - Generated body (TRELLIS) replaces the procedural shell in AC
- Nik extended the rule to free image-to-3D models and asked to export the generated car. TRELLIS
  (trellis-community/TRELLIS Space, multi-image: Wikimedia E19 GTE front + rear 3/4, anglia side photo) gave a mesh
  that reads as a Nova GTE far better than the procedural shell. tools/gen: none yet - generation via gradio_client
  from D:\Claude\_tools\hfgen (anonymous ZeroGPU quota, ~1 run/day; Nik's account token would give more).
- blender/scripts/fit_generated.py: tyre contacts -> wheelbase 2.343 (FIA), width at the axles 1.522/1.529 (FIA),
  roof 1.365 (brochure), axles on the WHEEL empties; the better (+x) half mirrored. Fitted vs the matched photo
  cameras: within a few cm.
- prep_generated.py: generated wheels cut out (our wheels), windows cut with slabs from the photo-matched procedural
  glass (GEN_GLASS), materials per face from the nearest procedural zone (flat paint/trim/lamps; the recoloured
  photo texture looked dirty), 3 mm inner Solidify. export_gen.py writes the package (procedural kn5 in git history,
  installed copy archived by deploy.py). The kn5 writer can now embed image files (material prop ac_tex).
- Known rough: lumpy 25k-tri surface (TRELLIS.2 at 1536 should be much cleaner - quota), no shut lines, lamps not
  wired in lights.ini yet, interior fitted to the old shell.

## 2026-10-19 - Reference model (Nik's Novamodel.blend) scaled and edited to the real dimensions
- One high-detail mesh (1.9M faces, no textures/materials, arbitrary units). Scaled uniformly to the FIA length 3622: its length/width/height then match the real car within ~2 mm (body width 1532, roof 1367). Only error: wheels/arches - model wheelbase 2257 (-86 mm), wheels 542 mm vs 583.
- blender/scripts/fit_reference.py: fit (scale, nose at the FIA front overhang), split_wheels (loose parts: body / 4 wheels / specks), y_shift_arch (front arch 35 mm forward with a y-only remap of every vertex - no surface can pass through another), arch_morph_smooth (arch lips onto the cS-traced arch_shapes: closest-point offsets smoothed along the lip, Gaussian-blended, short upward reach). First attempts (arc-length pairing, nearest-sample, x-weighted) crumpled the bumper corners - checked against the original in Blender each time.
- Result (export/ref/nova_ref.blend, REF_BODY): length 3622, body width 1532, wheelbase 2343, overhangs 670/609, our wheels at the real track; width at the axles 1500/1507 (FIA 1522/1529), mirrors 1688 (brochure 1725).

## 2026-10-20 - Front end, front wings and front arch rebuilt as new parts
- Nik: build each part new instead of repairing the bought mesh. blender/scripts/front_new.py: grille frame (body
  colour, groove across the top band), recessed black grille with 7 slats and staggered dividers, headlamp units
  (clear glass, amber indicator wrapping back to the wing, black bezel, chrome reflector). Sizes from the grey front
  picture (camera FRONT_CAM in grey_views.py: ~11 m away, f 1975 px - from plate width, track, mirrors and body width;
  heights anchored on the plate), detail from the red Commons front photo. DET_LAMP_HEAD / DET_LAMP_IND_* keep their
  names (lights.ini, ext_config.ini).
- blender/scripts/wing_new.py: front wings from a section scan of the old wing (R(y, phi) about x 0.40 z 0.55, both
  sides averaged, light smoothing, old lip rolls masked), new quad grid trimmed to the real edges (door shut y -0.6825,
  bonnet gap, lamp unit, bumper top z 0.537, arch, sill z 0.292) with rolled edges.
- Front arch: traced on the grey side picture (export/ref/arch_front_pic.json). The solved side camera (grey_cams.json)
  puts the picture's wheel centres ~25-35 mm behind the model's (camera registration, both axles alike), so traces
  from that picture are shifted by the wheel-centre offset before use. Result: the wheel sits centred in the arch as
  in the picture; arch top 0.637 (was 0.645), front edge ~20 mm further forward at the bottom (bumper end follows,
  bumper_sweep.arch_y).

## 2026-10-26 - side profile: the blueprints calibrated, and the doors rebuilt

**The line blueprint's length is wrong, the spec sheet's 3622 is right.** Calibrating
`corsa_a_4view_blueprint.gif` on its own dimension marks gives a scale that reproduces the printed
wheelbase (2343), the printed height (1365 exactly) and the 175/65 R14's unloaded radius (291 mm), but
makes the car 3539 mm long instead of 3622. The factory GA sheet's own two dimension arrows measure in
the ratio 1.561, against the 1.546 that 3622/2343 demands, so the factory sheet is consistent and the
redrawn line blueprint is 2.4% short in the overhangs. Decision: trace shape and anything between the
axles off the line blueprint; take length and overhang from the spec sheet. Details and the
blueprint-vs-photos cross-check table are in `reference/blueprints/README.md`.

This also **withdraws the 2026-10-26 reading that the blocky rear overhangs the drawing's tail** - the
drawing's tail is short. What is real is the other way round: `Bumper_Rear_GTE` reaches y +1.839 and
`BUMPER_F` y -1.815, which makes the model 3654 mm long, **32 mm over** the homologated 3622. To correct
in the rear-end step, by bringing the rear bumper back to +1.807.

**The drawing sits on unloaded tyres**, like the model, so its z needs no dz. An earlier pass added the
0.0193 photo-frame offset to it as well and so read the front arch 40 mm high; it is 11 mm.

**Doors** (`tools/gen/rebuild_door.py`). Sampled along x rather than from above or radially, since the
panel is near-vertical; a Coons patch over four traced edges - the two shut lines from the blueprint
(neither is a plain vertical: the front one curls forward into the sill, the rear sweeps back over the
arch), the door's own lower edge from the blueprint, and the belt line from the photo measurements -
then the same Laplacian fit the bonnet and wings use. Shut lines placed on the photo-measured
`zones.shut_y`; door 1135 mm long.

Two things worth remembering from it:
- The Meshy shell is **23-25 mm narrow per side at the door**, matching the 15-30 mm found at the wing.
  The correction is uniform over the panel's height. Ramping it in and out towards the top and bottom
  edges (to leave them where the shell put them) bows the door out by the full correction in the middle
  and reads as a crease across the door.
- `tools/gen/add_meshy_ref.py` was **losing the door objects' transforms** on append, so `MESHY_REF_DOOR_L/R`
  sat 744 mm inboard and the door area of the ruler was a hole that rays went straight through. The source
  transforms are now baked into the mesh data via a scratch copy before anything is appended.

## 2026-10-26 (later) - off the Meshy shell and onto the drawings

Nik: *"The meshy shell is only for reference. It's irrelevant i think now we have more detailed diagrams
to run off."* and *"you can save time by mirroring the left side to the right side"*. Also: ignore the
saloon on the line blueprint - only the hatchback views are ours.

**The factory GA sheet is now measurable.** `tools/rectify_ga.py` finds the sheet's ruled drawing frame
in the photograph and warps it to a rectangle, which squares every view on it up
(`reference/blueprints/GA_rectified.png`). That is what unlocks the plan view, which no other source
gives.

It is not perfect. The paper was not flat, and one homography leaves about 2.5% of local distortion,
enough that the sheet disagrees with itself: the front elevation's own 1532 marks read 1572 on the scale
its own 1320 track marks give. So the rule is the same one the side elevation already has - **drawings
for shape, spec sheet for size**:

- `tools/trace_plan.py` traces the plan outline and fits ONE lateral scale to the three SOURCED FIA
  widths (1522 front axle / 1529 rear / 1535 max). Residuals +3, -10, +7 mm, so the drawn taper and the
  sourced widths are the same shape. Between the arches the FIA figures win (SOURCED, and the body is
  parallel there); outboard of y -1.25 / +1.25 the plan wins, because body_profile is an ESTIMATE at the
  ends and the plan is the only measurement of the taper. `halfw_merged` is the blend.
- `tools/trace_section.py` traces the front elevation's silhouette, which being a projection is the
  body's section envelope: parallel from the sill to z 0.65, then in 17 mm by z 0.75 and 52 mm at the
  belt. Normalised, so it carries shape only. Its own flank width reads 0.9% off the FIA figure.
  Only the front elevation is readable - the rear one has the tailgate, lamps and half a dozen leaders
  crossing its silhouette.

Both tracers had to deal with the sheet's label leader lines, which touch the outline and are straight
enough that no median filter tells them from the body. The plan is extracted by taking, per column, the
pair of ink runs most nearly symmetric about the plan's own centreline - a leader has no partner at the
mirrored distance. The elevations take the nearer of the two sides per row, since a leader reaches the
car from one side only.

**The door is now built from the drawings alone**: x(y, z) = halfw(y) * section(z), the product of an
orthographic plan and an orthographic end elevation. It comes out smooth, so the Laplacian fit the
shell-sampled panels needed is gone. The Meshy shell is still the ruler for the bonnet, the scuttle and
the wings' section; nothing new will use it.

**Mirroring.** Only the left door is built; a Mirror modifier makes the right. Half the geometry and the
two sides cannot drift apart. (The wings are still a left/right pair from the earlier pass.)

**Tidying** (`tools/gen/tidy_side.py`). The wings were built to y -0.700, where the door was cut out of
the Meshy shell, but the door is on the photo-measured -0.670 and the blueprint reads -0.648, so -0.700
was the outlier and left a 30 mm gap. The wing's rear boundary ring is extruded onto the shut line
rather than the wing being rebuilt, which keeps everything measured about it. Then the blocky slab's
torn leftovers go: faces now behind a finished panel, faces floating with no neighbour, degenerate
faces. Fender_Front_Left 85 -> 34, Hood 15 -> 12, Side_Profile_Door_Left 3652 -> 3389.

Checked against `reference/photos/grey_studio/side.png` at the same scale: roof, belt, bonnet line, the
A-pillar and both door shut lines all land within a few tens of mm. What still reads wrong is all
unbuilt - the greenhouse, the sill and the rear quarter are still the blocky slab.

## 2026-10-26 (3) - the rocker and the GTE sill skirt, traced off the picture

**The blueprint runs out here.** The line drawing is a base-model Corsa A: it carries the rocker's own
lower edge (the `sill` line, z 0.246 at the front falling to 0.239 at the rear) and the door's lower edge
(`door_bottom`, z 0.30), but the GTE's bolt-on sill skirt is not on it at all. So the rocker is built
from the drawing and the skirt from Nik's grey side picture.

**Reading the picture properly.** `tools/photomatch/grey_cams.json` already held a camera solved for that
picture against the bundle-adjusted 3D points, so a point on the body can be projected onto the picture
and read back. `tools/trace_skirt.py` walks up the body's own surface - x(y, z) = halfw(y) * section(z),
the same surface the door is built on - projects each step, and reads the luminance along that path. The
skirt's top edge is a step up in brightness going up.

Two passes, because the edge changes direction: along the car, seeded in the middle of the flat run and
followed out both ways with a 6 mm slope limit; then up the kick-up in front of the rear wheel, where
the edge climbs 200 mm in 150 mm and has no single height per station, followed the other way round -
one y per height. Exactly the split the blueprint tracer needs for the pillars.

The tolerance matters. With a loose one the follower climbs onto the **lower body crease**, a soft
shading change about 100 mm higher that runs the whole length of the car; it then draws a plausible but
quite wrong "kick-up" over the rear arch. Checked at 14x on the picture: the crest is at (y +0.80,
z 0.484) and the crease is a separate line above it.

**The cross-check that matters.** The third pass takes the lowest pixel of the car at each station, read
on the same surface. It lands on the blueprint's `sill` line to **-8 mm mean, 24 mm spread** over the
whole run. Two independent sources - a photograph through a solved camera, and an orthographic drawing -
agreeing to under a centimetre is the evidence that the camera, the plan taper and the section envelope
are all right.

**Results.** Skirt top flat at z 0.318-0.329 from the front arch to y +0.64, then the kick-up to a crest
at (+0.780, 0.501); body bottom 0.236-0.243. Rocker 58 mm tall at mid (0.246 to 0.304), meeting the
door's own lower edge with no step because both come off `door_bottom`.

**The skirt is body-coloured, not grey.** `tools/side_parts.py` had it as `trim_grey`. On the white GTE
in reference/photos/commons/1989_Vauxhall_Nova_GTE__15643768649_.jpg the skirt is plainly the same white
as the car; on Nik's gun-metal picture it only looks like a darker part because its face is turned down
and away from the light. That is the very step the tracer keys on, so the trace still holds - only the
material was wrong. The same photograph settles the third item on this section's list: **the wheel
arches carry no trim**, their lips belong to the wing and the rear quarter.

**Both ends follow the arch lips.** Each row of the skirt's section finds its own end by a fixed point
against the traced lip outlines in `body_profile.arch_shapes`, because the row's height decides where the
lip is and the lip decides the row's end. Without it the skirt stopped at y +0.78 with a 260 mm open
edge hanging in the wheel arch.

**Proudness is the one ESTIMATE**: 12 mm, from the earlier reading of photos 01/22/cAR (side_parts.py
used 15). No picture we have shows the section squarely.

**Also done:** the wings were cut out of the Meshy shell and stopped at z 0.3475, where the shell's own
sill ended, leaving a 25 mm slit between the wing and the top of the skirt behind the front arch. Their
lower rear boundary is extruded down onto the sill line in `tidy_side.py`, the same treatment their rear
edge already gets at the door shut - the wing is not rebuilt, so nothing measured about it is lost.

**Still wrong and known:** the rear quarter and the rear arch are the old blocky slab, so the skirt's
rear end meets a stepped edge; the greenhouse is still the slab; the model is 3654 mm bumper to bumper
against the homologated 3622.

## 2026-10-26 (4) - the roof panel, and what Nik's eye caught

**Nik's four observations, measured.** All four are right:

- *Waves on the front wing*: each vertex sits 4.3 mm RMS off the mean of its own neighbours, worst
  78 mm. That is the Meshy shell's lumpiness, carried through the Laplacian fit.
- *The bonnet bent upwards at the front*: along its centreline the model sits 25-53 mm **below** the
  blueprint's `bonnet_top` from y -1.55 back to -1.00, so its nose reads lifted relative to its own
  rear. (The +150 mm at y < -1.68 is not real - the traced line dives over the front edge there.)
- *The door does not line up with the wing*: at the shut line the wing is **11 to 48 mm narrower** than
  the door. The door is right - within 3 mm of the drawings at every height - and the wing is not.
- *The door's top half is the old blocky drawing*: correct, and by design so far. Door_Left stops at
  z 0.868, the belt. The window frame, glass and pillars above it are the slab.

**Why the front end looks better than the rest.** The bumper, grille and lamps were built from
triangulated 3D points measured in the photographs (tools/front_end.py, the BA solution) - real
measurements. The bonnet and the wings were sampled off the Meshy shell and smoothed with a Laplacian
term, so they inherit both its lumps and its narrowness. The door, the rocker and the skirt are the
first panels built purely from drawings, which is exactly why they are clean and why the wing no longer
meets the door. **The wings and the bonnet need rebuilding on the same rulers.**

**The roof.** Three traced curves, one per view:
- crown(y), the centreline height, straight off the side elevation (`roof` + `roof_b`; the rearward
  follow was extended from px 520 to 600 so it reaches the backlight header at y +1.298);
- arch(|x|), from the front elevation's silhouette in section_profile.json - flat to |x| 0.15, -17 mm at
  0.30, -44 at 0.45, -89 at the drip rail. Re-tracing the front elevation's top edge directly only found
  the windscreen header's inner line and the mirror, so the section is used as it stands;
- outline(y), the roof's half-width. The sheet's plan view gives it badly: the drip rail is drawn as a
  close pair of lines and the symmetric-pair trace swaps between them, +-15 mm of noise against a ~25 mm
  real taper, coming out with a waist in the middle and wide ends - wrong both ways. So the *shape*
  comes from body_profile `glass_top_x`, the same line triangulated from the photographs, and only the
  *size* from the section (0.5536 m at the drip height). The two agree to 4 mm at y +0.4 to +0.6 and
  diverge only at the ends, where the sheet trace is worst.

Cross-check: the roof's edge lands at z 1.274 against the 1.287 the photographs give for the drip gutter,
and the glass top at x 0.538 against the section's own silhouette. 13 mm.

Roof half-width 0.5516 at mid, 0.5130 at the screen header, 0.5345 at the backlight header. Left half
only, Mirror clipped on the centreline. The slab lost 1547 more faces to it.

**Next:** the A/B/C pillars, the window frames and the glass - which is what finally takes the door's
top half off the slab - then the rear quarter and tailgate, then the rear end and the 32 mm length
correction. And the wing and bonnet rebuild above.

## 2026-10-26 (5) - the Meshy shell is out of the file, and the front wing is rebuilt

Nik, bluntly and rightly: the shell is for the general shape of the car and nothing else - not to build
from, not to overlay, not to compare against - and I had been using it for all three. And: check the
work instead of announcing that it is fine.

**The shell is gone from the working blend.** tools/gen/drop_meshy.py removes MESHY_REF (270,648 faces)
and the two door copies. Everything it was standing in for is traced now: blender/data/{side, plan,
section, roof, skirt}_profile.json and tools/photomatch/body_profile.json.

**The front wing was the worst of it.** Cut out of the shell and smoothed, it carried 4.3 mm RMS of
vertex-to-neighbour noise, sat 11-48 mm narrower than the door at their shared shut line, and its wheel
arch was a flat-topped tunnel with a diagonal cut across the back. The traced arch lip was sitting in
the file the whole time (`arch_shapes.front`, 32 points off the side photograph) and was not being used.

Rebuilt in tools/gen/rebuild_wing_drawn.py, the way the door and the rocker were:
- surface x(y, z) = halfw(y) * section(z). At the wing's front corner the plan reads x 0.677 at
  y -1.657 against the 0.6752 the photographs triangulate for that corner - 2 mm, so the drawing holds
  this far forward;
- the arch cut to the traced lip - crown z 0.641, against the blueprint's 0.657;
- the rear edge on the door's own shut line, so the step closes from both sides: both panels now reach
  x 0.7629 there, to four decimal places;
- the shoulder step from `wing_flare`, 8 mm proud below z 0.700-0.704;
- a rolled lip round the arch instead of a paper edge.

**Two things the check caught that the first build got wrong**, both found by looking rather than by
assuming:
1. A 105 mm hole along the top. The flank surface is the car's widest at each height, so it describes
   the wing's side but not its top - above the shoulder the wing rolls inboard and dies into the
   bonnet's shut line at x 0.595. The top edge is now read off the bonnet and scuttle panels themselves
   and the wing turns over onto it through a quarter-ellipse.
2. That edge, taken raw, is whichever vertices happen to land nearest each station, so the roll came out
   corrugated. It is resampled and meaned over 60 mm - it is a shut line, not a feature.

**And one that was poisoning every panel.** The traced section was jumping up to 7 mm of width between
rows 3.8 mm apart - a staircase left by the median filter, then put back by the normalise-and-force-the-
greenhouse-to-narrow steps. On a panel spanning as much height as the wing it reads as horizontal bands
across the paint. tools/trace_section.py now runs a mean over about 25 mm of height at the end: the
row-to-row kink over the wing's band falls from 0.55 mm to 0.04 mm, and the shape moves by under 1 mm.
Every drawing-derived panel - door, rocker, skirt, wing, roof - was rebuilt on the corrected section.

**Still wrong, and not being claimed otherwise:** the bonnet is still Meshy-derived and still sits
25-53 mm below the blueprint's line from y -1.55 back to -1.00, so its nose reads lifted - that is the
next rebuild. The wing's front lower corner is a flat slab where it should wrap round to the indicator.
The greenhouse, rear quarter and tailgate are still the blocky slab.

## 2026-10-26 (6) - the two faults Nik named in the wing

**1. The wing ran past the lights.** It was being built forward to y -1.755, while the headlamp glass
starts at -1.745 - so the panel stuck out in front of the lamp unit. The wing's real front edge is the
shut line beside the indicator, raked back as it rises, and it was already triangulated from the
photographs in body_profile `front_taper`: wb (0.6752, -1.6567, 0.5599) at the bottom, wt
(0.669, -1.6214, 0.7015) at the top - 0.249 of rake per metre of height. redgte_22 shows the same thing
plainly: the lamp unit is the front of the car and the wing comes down just outboard of the indicator.
The wing now runs to -1.657 at the bottom and -1.564 at the top, and the stations ahead of the rake are
pulled back onto it.

**2. The arch lip was a ridge, not a concave step.** The first build took the skin out to the opening
and then rolled it *down and outwards* into a bead. redgte_22 at the front wheel shows the opposite:
the skin runs out to the opening, turns in through a tight corner, and the flange folds back **up**
inside the wheel well, so the lip reads as a recessed step. Rebuilt that way - and only inside the arch
opening, since the sill and bumper edges are not flanges.

**3. Two things the checking caught, both mine.** The wing's top was rolled over a quarter-ellipse
starting 75 mm below the bonnet shut, which put a crease straight across the panel; the real wing leaves
the flank gradually and is already lying over when it reaches the shut, so the pull-in is now blended
with a curve that is flat at both ends.

And the top edge itself was corrugated, twice over, for the same underlying reason: it was read off the
bonnet and scuttle panels by taking the outermost vertex at each station. Those panels sit on a lattice
about 25 mm apart in x, so that scan hops between interior columns - a 56 mm sawtooth. Taking the
panels' actual *boundary* was not enough either, because their front and rear boundary rows also run
outboard of x 0.40. Filtering to x > 0.57 finally isolates the side edge: a clean line at x 0.595 with z
rising from 0.738 to 0.893, and the smoothing now moves it by 4.0 mm rms in x and 2.9 mm in z.

**Still wrong and not being claimed otherwise:** the bonnet is still Meshy-derived and its nose still
sits lifted; the wing's lower front corner is a flat slab where it should wrap to the indicator; there
is a void between the wing's front bottom edge and the bumper.

## 2026-10-26 (7) - the bonnet, and a frame error of mine

The old Hood_Panel came off the Meshy shell and sat 25-53 mm below the drawn line from y -1.55 back to
-1.00 - too flat, so relative to its own rear the nose read lifted, which is what Nik saw. It was also
the thing corrugating the wing's top edge, because the wing is built to meet it.

Rebuilt from measurements that were already in the file, and two sources agree on them:
- **centreline**: `top_bonnet_fit` - a quadratic fitted to six photo points, chosen over a spline
  because the spline's curvature jumped 4x between knots and showed as waves in the reflections;
- **crown across**: `crown.bonnet`, 30 mm, quadratic in |x|/x_shut;
- **the front V**: `front_panel.bonnet_v` - a straight V from the tip (0, -1.755) opening at a = 0.151
  to the corner (0.605, -1.664), both photographs putting its height at 0.722 +- 4 mm;
- **the nose roll**: `nose_roll` - down to that edge over 150 mm, fading as (1-s)^3 (power 2 left a
  curvature step, which reads as a line in the reflections);
- **the creases**: `bonnet_creases` - two lengthwise, traced in redgte_20, 8 mm deep.

**The frame error.** Built from those directly, the bonnet still read 13-32 mm below the photograph's
own silhouette. `body_profile` is in the photo/BA frame - ground at the loaded tyre contact - and model
z is photo z + 19.3 mm. Every other quantity taken from that file gets that: belt, cant, arch_shapes,
the glass corners. `top_bonnet_fit` and the front edge's height did not. Adding it closes the gap.

Worth recording how it was found, because the drawings alone would not have caught it: the model and
the picture were compared **silhouette to silhouette**, column by column, using the picture's own alpha
channel. Before the rebuild: 25-53 mm low. After the rebuild, before the frame fix: 13-32 mm low. After:
**0 to -13 mm, -7 mm mean** - within a pixel of the picture at its resolution.

A check that was *not* good enough: reading the model's height on the centreline and comparing it to the
fit. That agreed to 5 mm while the panel was still 25 mm out, because it was comparing the model to the
same number the model was built from.

The bonnet and the wing now meet with a clean 3.0 mm shut gap in x and 0.0 mm in z at every station from
y -1.60 to -0.90.

**Still outstanding:** the wing's lower front corner is a flat slab where it should wrap to the
indicator; the void between the wing's front bottom edge and the bumper; the greenhouse, rear quarter
and tailgate are still the blocky slab; the model is 3654 mm bumper to bumper against 3622.

## 2026-10-26 (8) - the bonnet has a ridge, and the drawings say how deep

Nik: the bonnet has a ridge down the middle and its sides slope down to the wing; the side profile fits but the
section does not. He is right, and the drawings carry it.

**The line blueprint's hatchback front view** (top right of corsa_a_4view_blueprint.gif - the bottom pair is the
saloon, which is not our car) shows the two lengthwise bonnet creases head-on, as short diagonals where the raised
centre panel meets the sloping outer one, at |x| 351 to 440 mm. That is `bonnet_creases` seen from the front:
x 379 mm at the nose rising to 498 at the scuttle. redgte_20, straight down the bonnet, shows the same two lines
either side of the griffin.

**How far it drops** was the number I had wrong. `crown.bonnet` carries 30 mm, applied as a smooth dome from the
centreline. But the blueprint has both ends of the section traced independently: `bonnet_top` is the centreline and
`bonnet_shut` is the bonnet-to-wing joint. At y -1.20 those are 0.901 and 0.861 - a **40 mm** drop, not 30, and
the first rebuild's edge sat 12 mm proud of the shut line as a result.

So the section is no longer a dome with a guessed depth. It is flat from the centreline out to the crease, then
falls away, and the drop is solved at each station so the edge lands exactly on the blueprint's own shut line:
0 mm mean, 0 min, 0 max, by construction. Two independently traced lines now define the bonnet's cross-section
between them, with the creases setting where the flat centre ends.

## 2026-10-27 (9) - two frame errors, the windows traced properly, and the rear end built

Three days of comparisons had been made through a 30 mm frame error and a camera solve that was never
re-converged. Both are fixed, and the whole body is now rebuilt by one script, `tools/gen/rebuild_body.sh`:

    sill -> bonnet -> scuttle -> wing -> rear end -> shell -> fit (cull what the panels cover)
         -> apertures -> organise

**The blueprint traces sat 30.5 mm along the car from everything else.** `tools/trace_side.py`,
`trace_plan.py` and `trace_roof.py` pinned the drawings on axles at y -1.141 / +1.202 (phase 1, from the FIA
overhangs), while `body_profile.json`, every solved camera and the whole photogrammetry frame put the origin
midway between the axles, at +-1.1715. So every line taken off a drawing - window tops, bonnet shut, the plan
taper, the roof outline - was 30.5 mm out against every line taken off a photograph. The traces are re-pinned,
the wheel and axle guides moved (`tools/gen/frame_guides.py`), `side_calibration.json` and the overlay tyres
corrected, and the old JSONs kept in `blender/data/BACKUP_blueprint_frame_2026-10-26/`. Along the car the
traces move by exactly -30.5 mm; the plan half-width at a given y changes by up to 26 mm near the ends.

**`ba_result.json` was not the solution of the current `obs.json`.** It was written on 12 Oct before the marks
were last edited, and re-running the same solve drops cCF from 18.6 px rms to 12.3. Re-solved with a robust
loss (`tools/photomatch/ba2.py`, same camera model and anchors as `ba.py`); the stale file is kept as
`BACKUP_ba_result_stale_2026-10-12.json`. What moved: **the windscreen corners came down about 30 mm** - which
is what Nik saw and said - and the lamp points moved 11-17 mm forward. Median mark error is now 2.5-3.3 mm on
the four F294 photos, 4.8 mm on cAR, 5.7 on cCF, 7.0 on cS.

A fuller camera model was tried first and **rejected**: freeing each camera's principal point and adding k2
(the cropped-photo hypothesis) buys 12% of the cost and asks for principal points up to 1000 px off centre,
which is fitting noise. The residuals are mark-placement error, not lens error.

**Windows: the blueprint and the photograph agree, and the triangulated B-pillar corners do not.** Drawing the
traced edges onto `anglia_side` through its solved camera (`tools/photomatch/bp_on_photo.py`) puts all four
edges of both side windows on the real car's glass. DG_RT and DG_RB, by contrast, land in the middle of the
B-pillar, about 55 mm behind the glass edge - they are the one pair that only two cameras see from nearly the
same direction. So `tools/windows.py` builds both apertures from the traces (each edge fitted as a function and
the corners solved where they cross) and uses the measured corners only where they do sit on the outline: the
quarter window's traced top runs 13 mm high at both QW_FT and QW_RT, so it is shifted onto them.

New traces for it: `dw_front_edge`, `dw_rear_edge`, `dw_bot`, `qw_top`, `qw_bot`, `qw_front_edge`,
`dlo_top_fwd`. `dlo_top_b` used to coast through the B-pillar and then hold flat, which left the quarter
window's top 25-33 mm low. Both window bottoms are taken from the longest run of the trace that holds one
height - at the front it drops onto the door trim, at the rear it climbs the pillar's lower corner.

The shell's glass band went from 8 rows to 20 so the cuts land on an 18 mm grid rather than a 46 mm one; the
window edges stopped reading as a staircase against the photographs.

**The rear end exists now.** It never did: `Bumper_Rear_GTE` was the blocky leftover and was hidden, and the
loft simply cannot make a tail. A loft of cross-sections along the car has no way to hold a vertical rear face -
every point of one has the same y, so the last stations collapse into a sliver and the tail came out as a
rounded blob with nothing behind it. Three new parts, built the way the bonnet and wings are:

- `tools/gen/add_rear_end.py` imports the bumper and valance that `tools/rear_end.py` had been generating
  since 12 Oct but which nothing ever put in the blend.
- `tools/tail_lamps.py` - the lamps on the shell's own rear-face curve `y = 1.735 - 0.88|x|^6.4`, which
  reproduces the four triangulated lamp corners to 2-8 mm, with the colour bands measured down the lens on the
  4298 px commons rear photograph (red to 0.502, black divider, amber to 0.768, clear below).
- `tools/rear_panel.py` - the whole tailgate, from the bumper top to the glass's top corners, on that same
  curve across the car and on a centreline profile read off TL_BI / the number plate / TL_TI / HG_B. Its
  outboard edge follows the seam where the panel meets the shell's own skin `halfw(y) * sect(z)`, solved per
  height; using the plan half-width alone put the seam 60 mm outside the car up at the glass.

The backlight cut was also wrong in a way that only showed once there was a tail to lose: it tested y alone,
and at the back of the car the frame and roof segments wrap the entire rear face, so it had been removing the
whole tail. It now also has to lie within 45 mm of the glass's own plane.

Rendered through the `cAR` camera and laid over that photograph, the model covers the real car's roofline,
glass, quarter panel, tail and bumper. What is still visibly missing there: door mirrors, door shut lines,
wheels, and glass in the apertures.

## 2026-10-27 (10) - why the bumper looks right and the body does not

Nik: *"the bumper and grille are really good... the rest of the car = like a child made it out of paper"*, and
*"apply that technique to the rest of the car"*. He is right, and the difference is structural, not cosmetic.

`tools/front_end.py` builds the bumper as **one cross-section swept along a measured plan path**. The section
has about forty rows and every feature of the part is one of them: seven rows over the 50 mm top roll, five
rows per rib groove, exact rows at the plate recess edges, eight rows down the tucked-in lower face. The first
and last rows are **returns** - the surface turns back behind itself - so the part has no raw edge anywhere.
Features fade in and out along the path through smoothstep blends (`side_t`, `corner_t`), never step.

Everything else was a plain surface with holes cut through it afterwards. A cut goes **across** the rows, so its
edge is a staircase of whatever cells it happened to land in, and the surface is one skin with a raw boundary -
which is exactly what reads as paper.

Three things changed today towards the bumper's way of working:

**Every open edge is now rolled** (`tools/gen/roll_edges.py`). For each boundary vertex the script builds a
frame on the surface - normal, boundary tangent, and the in-surface direction pointing into the opening - and
sweeps a small section along the boundary. Wheel arches roll over the lip and turn back into the well; window
and screen openings step back into the rebate the glass sits in; the shell's bottom edge folds flat inboard.
An edge that butts against another panel is told apart from a free edge with a BVH of the other parts, and gets
a shut return instead: the edge is pulled back 2.2 mm along the surface so there is a real 4.4 mm gap, then
turned under, and the panel on the other side does the same.

**The window apertures are rows of the section now, not cuts across it.** `build_shell2.py` makes the glass
band start exactly on each window's lower edge and end exactly on its upper one wherever a window exists
(eased in and out over 55 mm so the band does not kink at the ends). The top and bottom of both openings are
therefore grid lines. Measured against the triangulated glass corners, the aperture edges went from 10-100 mm
out to 13-23 mm, and the staircase is gone from the overlays.

**The tail lamps' colour bands come from the factory drawing.** `reference/blueprints/GA_rear_elevation.jpg` -
which this project had never opened - is a rear elevation of the *hatchback* with the bands dimensioned above
the ground: 800, 745, 685, 635, named down the side as brake/tail, reflector, indicator, reverse. Its 800 mm
top agrees with the triangulated TL_TI at 804, so the drawing and the photographs are measuring the same lamp;
the drawing wins on the band positions. Worth recording that the **4-view line blueprint has no rear elevation
of our car** - the bottom-right view on that sheet is the saloon's.

**Still built the old way, and still looking it:** the front wing, the scuttle, the bonnet and the rear panel
are cut grids whose shut edges are ragged, and rolling those edges makes the raggedness more visible rather
than less. Each needs rebuilding as a swept section in the bumper's manner, with the shut line as a row of the
section rather than wherever the grid was trimmed.

## 2026-10-27 (11) - shut lines, glass, and the hole under the windscreen

Carrying on with the bumper's way of working.

**Panel shut lines** (`tools/gen/shut_lines.py`). The door is not a separate panel here - the shell carries
that whole area - so nothing marked where it started or stopped and the side read as one blob. The three
near-vertical lines are now real grooves, made the way `front_end.py` makes the groove under the grille: the
traced line is resampled, the body is sampled at each point (nearest point and normal on a BVH of the painted
parts) and a five-row section is laid across it - lip, wall, floor, wall, lip - so the groove has sides to
catch the light rather than being a painted line. Lines: `shut_door_front`, `shut_door_rear`, `tailgate_shut`,
all traced on the side elevation.

**Glass** (`tools/gen/add_glass.py`). Every aperture was cut right through a one-skin body, so the car was
see-through. The glass is not modelled from coordinates of its own: `roll_edges.py` has already turned each
aperture's edge back into the rebate the glass sits in, so the pane is the innermost ring of that rebate,
pushed in 4 mm and filled. It therefore cannot disagree with the hole. Five panes: both side windows, the
hatch glass (two halves, one per side of the rear panel) and the windscreen.

The windscreen needed its own path. On the half-model its aperture is not a loop at all, and finding out why
turned up a real fault: **`fit_shell` was culling the shell's own skin under the scuttle**, and that opening
ran straight into the screen aperture, so the two were one ragged hole across the whole scuttle - which is
exactly what the base of the screen looked like. The scuttle is out of `KEEP` now; the shell keeps its surface
there and the scuttle panel sits on it. The screen pane is gathered from the boundary vertices lying along the
measured WS_B - WS_T line and filled, so it is still the body's own hole.

**Double rolls.** `roll_edges.py` was rolling edges that the generators had already rolled - the wing and the
sill build their own arch lips - which is what put flaps along them. It now compares a boundary face's normal
with the one behind it and leaves an edge alone if the surface has already turned over.

Still outstanding: the screen aperture's lower edge is stepped where it crosses the shell's stations, the
wing's lower front corner has a notch by the indicator, and there are no mirrors or wheels.

## 2026-10-27 (12) - the bonnet-to-wing shut: one shared line, the nose corner, and a tube in the gap

The shut was measured before changing anything, by casting rays straight down across it at each station and
recording which part is on top. That showed it was **three faults, not one**, and that the one the last
commit suspected (the wing's top being a resample of the bonnet mesh) was the smallest of them:

1. **A tube of shell standing in the gap.** Ahead of the windscreen the shell's upper rows (glass band, drip,
   roof) have nowhere to go and collapse onto the shut line, into a closed tube about 6 x 12 mm at x 0.600-0.606,
   y -1.62 to -0.70, standing 1-51 mm *above* the bonnet and wing. Its faces point sideways, so fit_shell's
   normal-ray test never met a panel and kept it. That tube is the light line that ran along the gap, and it
   hid the panels' real edges - which were already within about 3 mm of each other mid-length.
   `fit_shell.py` now drops any shell face within 12 mm of the shared shut line and not below it (179 faces,
   exactly the tube). A first attempt - drop faces with kept panels on both sides - caught only one face and
   was removed.
2. **The wing's top corner cut off at the nose.** The wing's front edge is the measured indicator-wrap plane
   through IND_OB / IND_OT, and the wing used it all the way up. That plane runs back as it comes inboard (x is
   its largest normal component): at the bonnet's corner, x 0.605, it was at y -1.56, 100 mm behind the
   corner at -1.664. body_profile already said what should happen - `front_panel.z_split`: below it the wing ends
   on the wrap line, above it the bonnet's V edge trims the bonnet and the wing corner. The wing never read
   z_split. It does now (eased over +-6 mm), so bonnet, wing and indicator meet at the bonnet's corner. Also:
   `wing_edge` and `z_split` are BA points, in the photo frame, and get + DZ like everything else from that file.
3. **The wing's top edge is the bonnet's own edge.** `rebuild_bonnet_drawn.py` writes its u = 1 column - the
   exact vertices of its side edge - and `rebuild_scuttle_drawn.py` its x = X_SIDE column, to
   `blender/data/shut_bonnet_wing.json`; `rebuild_wing_drawn.py` builds its top on those points. No mesh scan, no
   station rounding, no smoothing (the old scan is still in the file behind `OLD_SCAN = False`).

**Measured after** (rays from above, bonnet's top surface to the wing's): plan gap 0.1-1.4 mm, with the wing
4.6-7.5 mm below the bonnet's rolled edge - a true gap of about 5-7 mm along the whole shut, against 7-10 mm
mid-length and 17-94 mm at the nose before. The nose corner closes to 0.3 mm in plan. geo_check on the 58
points: no distance moved by more than 0.5 mm except the side repeater (0.2 mm). Through the c22 camera
(`export/match/shut_c22_close.jpg`: photo / before / after) the shut now reads as one fine line, as on the car.

**Still not right here:**
- The remaining step. At the shut the bonnet slopes about 23 deg across the car and the wing arrives at about
  57 deg (it follows the flank section's tumblehome up to the top), so rolling each edge back 2.2 mm along its
  own surface leaves the wing's lip 5-7 mm lower. On the car the two surfaces are flush across the shut. The fix
  is to make the wing's top rows arrive with the bonnet's own cross-slope (tangent-continuous across the shut)
  rather than the flank's - a shape change to the wing's top, to be checked against redgte_20/22.
- 0.6-1.3 mm see-through slits in the gap at y -1.58..-1.40 and -0.80..-0.72: nothing sits under the shut. The
  real car has the wing's inner flange (a gutter) there, which also makes the gap read dark.
- Present before and after, not touched: a dark notch where the shut meets the scuttle at the A-pillar, a dark
  sliver at the door's front shut behind the wing, and the windscreen pane's fan triangulation showing.

Backup of the blend before this: `blender/BACKUP_nova_proc_before_shared_shut_2026-10-27.blend`.

## 2026-10-27 (13) - the wing flush with the bonnet, and the gutter under the shut

**Flush.** The wing's top used a smootherstep pull-in off the flank, which is flat at both ends in the pull but
still arrives at the shut along the flank section's own slope - about 57 deg against the bonnet's 23 - so the
two met at a fold and the wing's rolled lip sat 5-7 mm below the bonnet's. The bonnet and scuttle scripts now
also write their cross-slope dz/dx at the side edge (`bonnet_slope`, `scuttle_slope` in
`blender/data/shut_bonnet_wing.json`; 0 to -0.72, i.e. 0-36 deg), and the wing's top rows are a cubic Hermite in
the section plane: leaving the shoulder step along the flank's tangent, arriving at the shut along the bonnet's.
Tangent-continuous at both ends. Old curve kept behind `FLUSH_TOP = False`.

**Gutter.** `tools/gen/add_shut_gutter.py` (new step in rebuild_body.sh, after shut_lines): the wing's inner
flange, a dark U channel along the shared shut line in the surface's own frame - lips 7 mm deep at +-12 mm,
floor 16 mm deep over +-4 mm, below roll_edges' shut returns (4 mm deep, out to 8.7 mm). `SHUT_GUTTER_BONNET`.

**Measured** (rays from above): plan gap 3.2-4.4 mm all along (target 4.4); carried across the gap on the
bonnet's own slope the wing's lip is 0-2.4 mm below the bonnet's (was 5-7); slopes either side of the gap
-0.39 / -0.49 at y -1.20. Every ray into the gap now lands on the gutter - no see-through. Through c22
(`export/match/shut_flush_c22_close.jpg`: photo / before (12) / now) the wing reads as the bonnet's outer panel
carried over the shut, as on the car. geo_check: unchanged except the side repeater, 16.3 -> 17.9 mm (the
wing's upper flank moved with the new top curve - check when the repeater is placed).

Seen in the viewport and still to do on this panel: the shoulder flare step reads more softly than the crisp
highlight line in redgte_22; faint banding on the wing's top towards the nose; the dark notch where the shut
meets the scuttle at the A-pillar.

## 2026-10-27 (14) - the wing: shoulder crease, banding, and the hole at the A-pillar

**The notch at the A-pillar was a hole, and (12) made it.** Rays from the viewport's angle went straight through
a 35 x 40 mm opening at x 0.605, y -0.74..-0.70, z 0.93-0.97, between the scuttle, the wing's top and the shell.
The shut-line cull in fit_shell ran the full length of the shared line, including the scuttle stretch behind the
bonnet, where the shell is not a collapsed tube but the real side wall at the foot of the A-pillar. It now stops at
the bonnet's rear edge (y -0.781). The gutter also runs 20 mm past the line's rear end so it ends under that wall
(a pinhole remained otherwise), and roll_edges skips `SHUT_GUTTER*` - the previous build's gutter is still in the
blend at that step and must not be rolled or count as a neighbour. Checked: 0 see-through rays from the viewport
angle; along the whole shut from above, 0.

**Banding: two pixel staircases, fitted not smoothed.**
- The bonnet_shut trace climbs in 2.7 mm pixel steps every 5.4 mm; its 9-tap mean still rippled ~0.5 mm every
  ~50 mm, and both the bonnet's edge drop and the wing's top carry it - the streaks ran across the shut onto the
  bonnet. From the nose back to y -0.84 it is now a least-squares cubic B-spline, knots 120 mm
  (`tools/gen/trace_fit.py`): 135 of 138 trace points within one pixel, worst 3.5 mm (one isolated point),
  moving the old curve by up to 3.6 mm. Behind -0.84 the trace jumps 32 mm onto the cowl - a different feature -
  and the old curve is kept, blended over 20 mm.
- The plan half-width (3.5 mm samples) steps the same way; the wing now uses a local quadratic fit of it (+-12 mm,
  within 0.03 mm of the trace on average, 0.48 worst), easing back to the raw trace over the last 60 mm so the
  wing still meets the shell's door at x 0.7629. This alone barely changed anything - the bonnet_shut trace was the
  main cause.
- Above z_split ~20 wing stations are pulled back onto the bonnet's V line but keep their own x, landing 0.1 mm
  apart as sliver faces; merged at 0.8 mm (no real rows are closer than 2.5 mm). Slivers 27 -> 5.
Viewport (studio light, specular): the wing's top and the bonnet's edge now shade clean.

**Shoulder crease - SHAPE ESTIMATE.** The panel above the crease leaned in no more than the panel below (19 vs
21 deg off vertical at y -1.10), so the crease was an 8 mm offset only. No drawing gives the upper panel's lean
(the GA front elevation's outline at those heights is the door's). Above the crease the wing now heads for the shut
along the chord, curving onto the bonnet's slope: 35-43 deg above the crease, 19-20 below, ledge 56. Eases back to
the flank over the last 150 mm before the door shut. In the c22 / cS renders it reads somewhat stronger but still
not the crisp bright line of redgte_22 - that may be the render's sky as much as the shape; judge in the viewport
and in AC.

geo_check against this morning: unchanged except the side repeater, 16.3 -> 11.0 mm (closer).
Still here: a small sliver at the bonnet's V corner above the indicator; the open door shut behind the wing.

## 2026-10-27 (15) - door mirrors and wheels on the measured car

**Mirrors** (`tools/gen/add_mirrors.py`, new step after add_glass). Body-colour housing (SPEC_SHEET "colour-coded
... door mirror housings"; both red cars), glass on the rear face, black base plate from the window line.
- Tip x 0.8625 = the brochure's 1725 mm across the mirrors (SOURCED).
- Side outline from anglia_side (cS), read on a pixel grid and back-projected through cS's solved camera onto
  x = -0.8625 (cS looks at the car's right side): rear edge y -0.393 (z 0.868-0.980), top to (-0.479, 0.990),
  front edge down to (-0.532, 0.883); 120 mm tall, ~140 mm long. Assuming x 0.72 instead moves it <= 15 mm. Agrees
  with the 13 Oct note (17 x 12 cm, 16 cm out) and the old shell map (y -0.53..-0.40, z 0.88-0.97).
- Checked in both cameras with the outline drawn onto the photographs (`export/match/mir_proj.jpg`): on the housing
  in cS; in c22 within ~10-20 px (the rounded outer end slightly long). The side repeater, drawn as a check point,
  lands on the repeater in both photos.
- **BA point MIR (y -0.207) is wrong** - single-view, it projects onto the door glass behind the mirror in cS. Not used.
- ESTIMATES: housing inboard end x 0.725, 14 mm corner radius, base plate shape, glass inset.

**Wheels** (`tools/gen/add_wheels.py`, new step after add_mirrors). The wheels measured and built on 12-13 Oct for
the first route are reused unchanged - `blender/scripts/build_wheels.py` with the traced face in
`blender/data/wheel_face.json` (5J x 14 three-arm alloy, 175/65 R14, 236 mm vented disc + caliper front, 200 mm drum
rear, AC names WHEEL_xx -> TIRE_xx / RIM_xx / DISK_xx). Placed at y +-1.1715 (FIA wheelbase), x +-0.660 / +-0.6535
(SPEC_SHEET tracks 1320 / 1307), z 0.2916 (unloaded 175/65 R14). Through cS (`export/match/wheels_cS_pair.jpg`) the
wheels sit in the arches where the photograph has them, rim/tyre proportion 0.70 vs 0.67 in the photo.
- Static clearance: tyre tops 58 mm (front) / 61 mm (rear) below the arch lips. **The front tyre's leading edge at
  z ~0.33 is 0.3 mm from the shell's front arch edge** (inside the wing's arch flange) - fine at rest, not with
  steering lock or bump travel. Check before the AC test.
- match_look renders the real wheels now (rubber / alloy / dark brakes) and adds its placeholder tyres only when
  the blend has none. organise and roll_edges know the new part names.

geo_check: unchanged against this morning except the side repeater (16.3 -> 11.0 mm, from (14)).

Seen and not touched: the door glass's front edge. On the car the door window runs forward along the A-pillar
down to the mirror; the model's door aperture stops at a near-vertical edge at y -0.21 and the shell is body colour
in front of it (cS render vs photo). Also: no inner wheel-arch liners (the well is open to the background).

## 2026-10-27 (16) - Nik's decisions on the replica plan

On `docs/REPLICA_PLAN.md` section 7 (Nik, 12:02):
1. **Yes** - the body moves to FreeCAD: character-line network -> NURBS surfaces -> panels. The numpy build is kept
   for comparison until the new one beats it on every check; no more patching it except the glass.
2. **Yes** - black/grey trim and plain colours as separate parts from step 4.5. This replaces the "shell only, no
   painting" rule (textures still later).
3. **"Whatever is easiest"** - so: pre-facelift detail from Nik's car (R##) and the anglia/commons photos, as now;
   the Nov 1990 GA sheet only for hard points, apertures, glass and the plan shape.
4. **Yes** - FreeCAD Curves workbench installed (git clone of tomate44/CurvesWB @ c08e21b into
   `%APPDATA%\FreeCAD\v1-1\Mod\CurvesWB`). Checked headless: loads, Gordon (curve-network) surface builds a valid
   face; also Sweep2Rails, blendSurface, approximate, ZebraTool, curves_to_surface.
5. **More photos: "there are many pictures on this PC".** Searched C:, D:, E:, F: (names and image folders). The
   only Nova pictures are the 69 already in `reference/photos/` (35 of Nik's car, commons, anglia, grey studio),
   plus the brochure and FIA PDFs. Nothing new found; Nik to point at a folder if there is one elsewhere.

## 2026-10-27 (17) - glass: no more see-through panes

Every pane was a fan of triangles from its outline's centroid, and the windscreen's outline was gathered from the
shell's boundary vertices within 55 mm of the straight WS_B-WS_T line. Two faults made the big triangle hole seen in
every front and rear view:
- the screen is curved in plan (base ~80 mm further forward at the centre - scuttle_curve k), so the straight line
  missed the middle of the bottom edge; the header at the top is straight in plan. The test now shifts each point by
  the plan curve, fading from full at the base to none at the top;
- the fan from the centroid leaves wedges wherever the outline is not star-shaped round it. Panes are now
  triangulated as polygons on their own plane (mathutils tessellate_polygon); the angle-sorted screen outline is
  rotated to start and end at the centreline gap, and its ends are pulled onto x = 0 (the shell's nearest column is
  at x 0.009, which left an 18 mm crack between the mirrored halves).
Checked by ray grids from the front, rear and side: no see-through point in any aperture. Interim only - the FreeCAD
body will make the glass from the same DLO curves as the openings (REPLICA_PLAN 4.5).

Photo sources Nik supplied (attachment `vauxhall_nova_gte_sources.md`, saved as reference/SOURCES_NIK.md): Wikimedia
Commons category, two Flickr albums (enthusiast set; 1988 road-test scans), Pinterest board, Classic Car Reviews and
Classics World galleries - free to view. Alamy and Dreamstime are paid stock - not used (no paid sources).

## 2026-10-27 (18) - measurement foundation: every drawing in one world frame

`tools/cad/views.py` resamples the GA sheet's side, plan, front and rear views and the line blueprint's side and
front into fixed world rectangles at 500 px/m (`reference/views/*.png`, `frame.json` with every calibration and its
source in the docstring). `tools/cad/render_rect.py` renders any blend into exactly the same rectangles with
orthographic cameras, and `tools/cad/overlay.py` lays one on the other (drawing ink red, model grey, outline blue).

New calibrations, read off pixel-gridded crops: GA side ground row 521 and 3.934 mm/px vertical (roof 1365); GA front
centreline 2464.8, ground 515, 3.856 mm/px up, 3.423 mm/px across (1532 over the widest body); GA rear centreline
440.5, ground 513.5, 3.889 / 3.474 mm/px (its 800 mm lamp mark reads 815, 2%); line blueprint front centreline 940.5,
ground 270, 5.36156 mm/px. The sheet's across-car and along-car scales differ by ~12% (photographed paper), so every
axis of every view carries its own scale.

Checked by overlaying the current (photo-verified) model on all six (`export/cad/ov_now_sheet.jpg`): roofline, glass,
wheels, sills, width, greenhouse and mirrors line up in every view, so the calibrations hold. Already visible: the
**plan view's nose is rounder and narrower at the front corners than the model's** - the first thing the curve
network has to fix, and one the side views could never show.

## 2026-10-27 (19) - character-line network v1, and the curve fit that hung

**Lines** (`tools/cad/lines.py` -> `blender/data/cad/lines_v1.json`): 28 lines, left half, each assembled from two
sources (y/z from one, x from another, both recorded per line): centreline (bonnet, screen, roof, backlight, photo
profile), belt, both spear creases, mouldings, door bottom, sill, both arches, door/tailgate shut lines, glass base,
DLO top, both window outlines, roof edge, GA plan outline, bonnet shut, bonnet V, screen base/header, A-pillar.

**Curves** (`tools/cad/build_curves.py`, FreeCAD -> `cad/nova_lines.FCStd` + `lines_v1_fit.json`): least-squares
cubic B-splines with uniform knots, accepted within one pixel of the source drawing (5.36 mm line blueprint, 3 mm
otherwise), knots halved from 120 mm only while needed. Two fixes today:
- **The 12:22 run hung** (100% CPU for 2 h+): a line got more knot spans than it had points, the least-squares
  system went singular and the curve swung wildly, and the deviation check then sampled it every 0.5 mm. Spans are
  now capped at (points-1)/3 and the sampling at 20 000 points; the whole build takes seconds. The hung process
  (freecadcmd PID 23008) could not be stopped from here (permission) - Nik to end it, or OK it.
- **Corners.** One smooth curve rounds off real corners (window corners, the foot of a shut line), which is most of
  what pushed lines over tolerance. Lines are now split at corners and fitted piecewise. Corners are measured as
  the turn between 40 mm chords either side - over ~15 mm a single drawing-pixel step reads as a 30-40 deg turn and
  the first version found 8-14 false corners on smooth lines.
Result: 24 of 28 within one source pixel. Over: centre_top_photo 11.4 mm (photo-fitted profile, bulges past the
tail in the side view - drop or re-fit), roof_edge 14.9 mm (6 points only), centre_screen 6.8, glass_base 6.2,
tailgate_shut 5.5 (just over). Belt (9) and glass_base (12) corners still to be checked as real or trace joins.

**Checkpoint images** (`tools/cad/check_lines.py` -> `export/cad/lines_v1/`, sheets `lines_v1_sheet1/2.jpg`):
on the line-blueprint side view and the GA plan the lines follow the drawing; on the photos the side lines land on
the real car's features (cS, c22). **Missing before surfacing:** the rear end (tailgate glass, black panel, lamps,
bumper top/bottom, spoiler), the front end (lamp panel, grille opening, bumper), and cross-sections (roof crown,
tumblehome) from the GA front and rear views and the photos.

**Glass, a correction.** A later edit of mine to add_glass.py (hatch back to a fan) was a mistake made on a stale
intermediate blend; ray grids showed the committed version (17) is see-through-free front and rear and mine was not.
Reverted, and the committed nova_proc.blend restored.

**Nik's sources (attachment, 14:28)** are in reference/SOURCES_NIK.md. Wikimedia Commons: of ~110 Nova files only
the 5 GTE ones (already here) are our car; pre-facelift 3-door Sport/SR/L hatchbacks (same body, no GTE kit) and
the 1993 GSi (facelift - body only) are being fetched to `reference/photos/commons2/` with licences/authors in
`_licences.tsv` (`tools/fetch_commons.ps1`; Wikimedia rate-limits scripted downloads, so 2400 px thumbnails, slowly).

## 2026-10-27 (20) - character-line network v2: the ends of the car

Nik: "add to those measurements for better accuracy, seems to be a lot of lines missing". v1 had the flank and
little else. v2 (`tools/cad/lines_v2.py` -> `blender/data/cad/lines_v2.json`, fitted to `lines_v2_fit.json` and
`cad/nova_lines_v2.FCStd`, shown in Blender as collection CAD_LINES_V2, copy saved as `blender/nova_lines_v2.blend`)
is v1 plus 47 lines - 96 curves once split at gaps:
- **Traced from the GA end and plan views** (`tools/cad/trace_view.py` with guides in `tools/cad/trace_spec.json`,
  read off `tools/cad/grid_view.py` crops; each guide is snapped to the drawing's ink and points with no ink under
  them are dropped, not invented). Rear: backlight outline, spoiler top and bottom, C-pillar outer line, tail lamp,
  black panel recess, tailgate bottom, bumper top and bottom. Front: A-pillar outer line, screen header, grille
  opening, headlamp + indicator, bumper top. Side: the tail centreline (outermost tail line = tailgate centre
  profile). Plan: front and rear bumper corners. End silhouettes front and rear are kept as group "envelope"
  (max |x| at each z - a check for the surface, not a line on it; hidden in Blender, left off the photo overlays).
- **The missing coordinate** comes from a second source, recorded per line: rear-face plan curve (fits BA TL_BI /
  TL_BO to 1 mm) for lamp/panel; side tail line at x=0 to the BA HG_T-HG_B line at the glass edge for the backlight
  (parabolic in between - ESTIMATE); WS_T / WS_B line for the screen header and A-pillar; FIA overhangs for the
  bumper faces (front -1.8415, rear +1.7805; the GA's facelift bumpers sit 1.5-2 cm further out).
- **Parts already built from measured points** (lamp panel, grille, headlamp, indicator, plate, bonnet, scuttle,
  wing, skirt, rear panel, tail lamp, bumpers, valances, bonnet crease) as group "model_parts", flagged
  from_model - reference, not truth.
- centre_top_photo dropped (bulged 11 mm off its points and ~10 cm above the tail).

**Checks.** Against the anglia rear photo the GA tail lamp lands on the lamp, the backlight outline on the glass,
the tail centreline ends on the wiper pivot. GA lamp corners vs BA: within 5-9 mm. Two disagreements left open:
the GA screen header is z 1.29 against BA WS_T 1.269 (the GA line may be the rubber or frit), and the GA backlight
edge at z 1.20 is x 0.49 against BA HG_T 0.525. The spoiler's y is still an estimate and sits slightly high in
the rear photo. Front bumper: FIA puts the face at y -1.8415; BUMPER_F reaches -1.815 (27 mm short). The rear
(1.782) matches.

**Two curve-fit bugs found and fixed** (`build_curves.py`, new `tools/cad/check_swing.py`):
- The fit was only checked data -> curve, so a curve could throw a loop across a gap in the points and still pass:
  the tail trace "fitted within 3.6 mm" while swinging 1.2 m out and back, plan_rear_bumper swung 1.7 m to the
  origin (minimum-norm least squares puts unsupported poles at zero). Now: a faint second-difference penalty on
  the poles, a curve -> data swing check that refuses finer knots that loop, and dense lines are split at gaps
  (> 30 mm and 8x the median step) into runs `name#1`, `name#2` instead of being bridged. This also fixed v1
  lines that had been bridging gaps unseen (door_bottom 40 mm, shut lines, glass_base, belt).
- Result: 6 of 96 curves stray more than 10 mm from their source polyline - roof_edge (6 points, 15 mm),
  centre_screen 11, rear_lamp 11, part_skirt 15, part_plate 13, part_scuttle 12 - all at corners or sparse data.

**Still to do:** new photogrammetry marks (rear glass corners, spoiler ends, quarter-light, sunroof, fuel flap,
handle, decals) to replace the ESTIMATE y values; then the surfaces.

## 2026-10-27 (21) - are the lines wonky, and does it matter? Fairing, a better tracer, new photo marks

Nik: "some of your lines look a bit wonky... will that affect the build?" Yes, if left: the surfaces are built
through the curve network, so a wobble in a line becomes a ripple in the panel (the wing banding all over again).

**Measured** (`tools/cad/fairness.py` -> `export/cad/fairness_<tag>/`, `blender/data/cad/fairness_<tag>.json`):
for every curve, the deviation from a fair reference of itself (cubic, knots every 200 mm, split at real corners),
sign changes of the second derivative per metre, and curvature extrema per metre with a curvature strip on the
sheets. Causes found: (1) the fit took the finest knots needed to touch every pixel within 1 px, so it followed the
pixel noise - most of the wobble; (2) the GA tracer chose each sample on its own and hopped between drawn lines a
few px apart (tail, lamp lens, screen rubber); (3) a hard switch between two y sources at the C-pillar foot (a
27 mm step).

**Fixed.** `trace_view.py` snaps by dynamic programming with a cost per px of sideways jump, so it stays on one line.
`build_curves.py` fits fair: many knots (20 mm) and a third-difference penalty raised by bisection as far as the
data allow - worst point <= 1.5 px and RMS <= 0.6 px of the source - with points > 3 px off dropped as tracer hops
(none were needed after the DP tracer). The old fit is kept as FIT=v1 for comparison. C-pillar sources blended over
z 0.85-0.92. `tools/cad/run_fc.py` runs FreeCAD scripts with exceptions shown (freecadcmd swallowed one silently).
Result over the 53 measured lines: curvature extrema per metre median 7.7 -> 3.2, lines over 8 /m 24 -> 10,
wobble median 4.2 -> 2.3 mm. Still not fair enough for surfacing: centre_bonnet, centre_screen, sill, arch_rear,
tailgate_shut, glass_base, screen_base, rear_bumper_top#1, front_headlamp#2 - mostly line-blueprint traces where
the drawn line itself wanders; to be re-traced with the DP tracer from the views, or faired by hand against photos.

**New photo marks** (`tools/photomatch/epi.py`: epipolar line of a mark drawn into the second photo, then
triangulation; `grid_photo.py`; `marks_v2.py` -> `blender/data/cad/marks_v2.json`). Point features only:
LOCK_R (tailgate lock, c24+cAR, rays 1.2 mm apart) at (-0.017, 1.716, 0.780) and BADGE_R (griffin, 7.5 mm) at
(-0.018, 1.661, 0.867). Edge features (glass bottom, tailgate lower edge, spoiler edge) were tried and rejected:
in cAR they run nearly along the epipolar line, so their depth is unreliable, and the spoiler's edge is a different
physical edge seen from above (c24) and below (cAR, c23). Both points sit 17-18 mm off x=0 - a small x bias of
the rear cameras, or the badge and lock really are off-centre; noted, not corrected.

**What the marks changed.** The backlight was given an 8 cm plan bulge from the GA side tail line; the badge and
the glass-top ray say the glass and tailgate are nearly flat in plan - the centre ~1 cm behind the BA corner line
HG_T-HG_B (now GLASS_BULGE 10 mm). Below z ~1.05 the GA side tail silhouette is the quarter corners, not the
tailgate centre, and is dropped. The tailgate's bottom edge was on the rear face (6 cm too far back); it now sits
in the tailgate plane, which the badge confirms to 7 mm. The GA side view also reads the tail ~2.5 cm long against
the BA tail lamps and the FIA rear overhang.

**Still estimates:** the spoiler's y (it projects above the car in the anglia rear photo), the C-pillar above the
belt (lands ~3 cm inside the quarter's edge in cAR), the windscreen header height (GA 1.29 vs BA 1.269).
