---
name: nova-gte-project
description: "Vauxhall Nova GTE 1989 AC car - body rebuilt by tools/gen/rebuild_body.sh; 2026-10-27 fixed a 30 mm blueprint-vs-photo frame error and a stale camera solve, traced the windows, built the rear end. ONE LOFTED SHELL (FreeCAD NURBS loft from the traced rulers, apertures boolean-cut) replaces panel-by-panel; MESHY IS DELETED and must not be used for anything; compare from EVERY angle not just the side; bonnet has a central RIDGE - repo D:/Claude/vauxhall_nova_gte_1989"
metadata:
  node_type: memory
  type: project
  originSessionId: 492adf9d-8819-4b64-a28b-e276d960f362
  modified: 2026-10-26T23:48:22.661Z
---

## 2026-10-27 - RESUME HERE: frames fixed, windows traced, rear end built
- ONE SCRIPT REBUILDS THE BODY: `sh tools/gen/rebuild_body.sh` (sill -> bonnet -> scuttle -> wing -> rear end ->
  shell2 -> fit_shell -> cut_apertures2 -> organise). Intermediates in export/tmp (C: is full).
- TWO ERRORS FOUND AND FIXED (commit 09e6e41, docs/DECISIONS.md "2026-10-27 (9)"):
  1. blueprint traces were pinned at axles -1.141/+1.202, photos/cameras/body at +-1.1715 -> everything from a
     drawing was 30.5 mm along the car from everything from a photo. Re-pinned; old JSONs in
     blender/data/BACKUP_blueprint_frame_2026-10-26/.
  2. tools/photomatch/ba_result.json was NOT converged for the current obs.json (cCF 18.6 px vs 12.3). Re-solved
     robustly with ba2.py; stale one = BACKUP_ba_result_stale_2026-10-12.json. Windscreen corners came down
     ~30 mm (Nik was right), lamp points 11-17 mm forward. Free principal point + k2 TESTED AND REJECTED.
- THE METHOD THAT WORKS, and Nik asked for it as standing practice (2026-10-26): check blueprint AND photo
  against each other. tools/photomatch/bp_on_photo.py draws traced lines + measured points onto a photo through
  its solved camera. That is how the window edges were settled.
- Windows: both side apertures are now traced outlines (tools/windows.py -> blender/data/windows.json), each
  edge fitted as a function with the corners solved where they cross. Triangulated DG_RT/DG_RB are NOT used -
  they sit mid-B-pillar, ~55 mm behind the glass edge the blueprint and the photo agree on. Shell glass band
  8 -> 20 rows to kill the staircase.
- Rear end built for the first time: tools/gen/add_rear_end.py imports the bumper rear_end.py had been making
  since 12 Oct but nothing ever loaded, plus new tools/tail_lamps.py and tools/rear_panel.py (the whole
  tailgate). KEY LESSON: the shell is a loft of sections along y, so it CANNOT hold a vertical rear face -
  the tail must be its own panel, seamed where halfw(y)*sect(z) meets it.
- STILL MISSING on the body: door mirrors, door shut lines, wheels, glass in the apertures, scuttle louvres,
  backlight recess/visor, small see-through holes at the screen base and bonnet front corners. Then interior.
- Checks: tools/gen/geo_check.py (now measures glass corners to the aperture EDGE), match_overlay + overlay_edges
  (cyan outline on photo), match_look (lit render through a solved camera), ortho_views, tools/edge_error.py.

## 2026-10-26 LATE: ONE LOFTED SHELL, AND NIK'S STANDING RULES

NIK'S RULES, said plainly and more than once - follow them:
1. **Meshy is for nothing but the general shape of the car.** Not to build from, not to overlay, not to compare
   against. It is DELETED from nova_proc.blend (tools/gen/drop_meshy.py). Do not reintroduce it.
2. **Check the work.** Never say something is fine without measuring it against the pictures. The check that works
   is silhouette-against-silhouette through the picture's own alpha channel. Comparing the model to the number it
   was built from proves nothing and has hidden real 25 mm errors.
3. **Compare from EVERY angle.** tools/gen/ortho_views.py renders front/rear/side/top square-on; tools/cmp_views.py
   stacks each against grey_studio. The front and rear caught a barrel-sided body and a far-too-narrow roof that the
   side view could not show.
4. Use the tools that are installed instead of arguing they will not help.

APPROACH CHANGED: panel-by-panel was not converging - eight panels that met badly, weeks without a shell, while a
friend's ChatGPT-built Xsara VTS mod has a full body, interior and engine. Now: ONE shell, then apertures and shut
lines cut into it. tools/gen/shell_freecad.py lofts it as a NURBS surface in FreeCAD from the traced rulers
(body_profile top/floor silhouette, plan taper, front-elevation section) -> export/shell.step + shell.obj;
tools/gen/import_shell.py brings it in; tools/gen/cut_apertures.py booleans the arches, both side windows, the
screen and the backlight from the traced outlines.
LOFT TRAPS: 56 sections x 34 points ran 10 min at 2 GB without finishing - use ~20 well-placed sections. Every
section needs the SAME point count: de-duplicating per station gave different knot structures and the surface swung
to twice the car's width. Map the master section floor->BELT->top, not floor->top, or the body comes out barrel-sided.

BONNET HAS A CENTRAL RIDGE (Nik, 2026-10-26): the sides slope DOWN to the wing from a raised centre panel between
the two lengthwise creases. The line blueprint's hatchback front view (top-right of corsa_a_4view_blueprint.gif;
the bottom pair is the saloon - ignore it) shows both creases head-on at |x| 351-440 mm, matching bonnet_creases.
The drop to the wing is ~40 mm, not the 30 mm crown.bonnet carries: bonnet_top and bonnet_shut are traced
independently and are 40 mm apart at y -1.20. rebuild_bonnet_drawn.py now solves the drop per station so the edge
lands exactly on bonnet_shut, and holds the section flat between the creases.

FRAME TRAP: body_profile is in the PHOTO frame; model z = photo z + DZ 0.0193. Everything from it needs + DZ.
Missing it on top_bonnet_fit put the bonnet 13-32 mm low and the error survived three checks.

Panels built from drawings only: bonnet, front wing, door, rocker, GTE sill skirt (body-coloured, NOT grey), roof.
The wing's front edge is a measured PLANE (front_panel.wing_edge + normal), not a y cut; the arch lip is a RECESSED
FLANGE folding back up inside the well, not a rolled bead.

CAD TOOLS INSTALLED 2026-10-26: FreeCAD 1.1.4 at D:/FreeCAD (moved out of D:\Claude, where its installer had put
it alongside the projects - do not run its uninstaller from there); OpenSCAD 2021.01 at D:/openscad; geometry-script
add-on enabled in Blender with its skill junctioned into ~/.claude/skills; TrueScad runs in the browser at
hmeyer.github.io/truescad. Sources cloned under D:/Claude: geometry-script, truescad, FreeCAD, openscad,
garden-skills (web/video skills - nothing for the car).

## 2026-10-26: BACK TO THE BLOCKY MODEL, MESHY AS THE RULER (Nik's call, mid-turn)
Nik: "it might be easier if we carried on editing the blocky model we made from scratch" -> section rebuild now
happens on blender/nova_proc.blend (procedural phases 1-12), with the Meshy shell appended as a hidden MESHY_REF
collection to measure against (tools/gen/add_meshy_ref.py). Meshy-only route parked at blender/nova_meshy_bonnet.blend.
BONNET DONE both ways (commit 7f6eeb6). Outline traced on the Meshy shell: sides straight x +-0.597, rear y -0.678,
front fold y = -1.6768 + 0.0978 x^2. Panel = 49x41 quad grid, heights raycast off the ruler + Laplacian fit (keeps the
crown, drops the lumps), boundary rings faired along the ring and pinned. tools/gen/rebuild_bonnet.py is
parameterised (--ref/--panel/--cut/--uv/--symmetric); tools/gen/ruler_view.py = clay model + red ghosted ruler
(hide anything named *Guide* or with 0 faces, else Chassis_Guide's block hides the car).
The old blocky bonnet sat 10-30 mm high and had NO crown.
FRONT WINGS done same day (46046f1, tools/gen/rebuild_wing.py): a wing wraps horizontal->vertical so it is sampled
RADIALLY (fan of rays per y station from x0/z0.55 inside the body = the body's own cross-section). Edges read off the
profile: top where |x| crosses 0.599 (one shut line with the bonnet), bottom = first break going down (arch lip where
the arch is, valance elsewhere), rear y -0.700 (door shut), front y -1.642. Covered skin removed from
Fender_Front_Left + Hood by BVH proximity (80 mm), not by rule. Open: the arch opening is slightly small/high at its
front end. NEXT: front panel / headlamps / bumper, then scuttle + screen base, doors, roof, rear.
FRONT END done (63c258a): NOT modelled by hand - tools/front_end.py already generates it from the multi-view
triangulations (ba_result.json + c20/cCF/c22/cS overlays): bumper w/ ribs + plate recess + grey lip, lamp panel,
grille surround/insert/groove, headlamps, wrap-round indicators. tools/gen/add_front_end.py loads that JSON (+DZ
0.0193 photo->model frame), deletes the blocky parts and trims the old nose off Hood/Fenders.
BIG CORRECTION: the Meshy shell's NOSE is its weakest part - ~60 mm low and ~80 mm short at the bonnet's leading
edge. The real edge (docs/DECISIONS.md 12 Oct late, confirmed by a read of f400_side.jpg) is a STRAIGHT V IN PLAN
y = -1.755 + 0.151|x|, LEVEL at z 0.722 (photo frame). rebuild_bonnet.py now uses it and lifts the last 300 mm onto
it (--fold reverts); rebuild_wing.py takes its front edge from the same V. The ruler is still right for crown,
section and arch.
JUDGE IT PAINTED: ruler_view.py 'paint' mode renders the body in gunmetal. In light clay against the dark grey
grey_studio/front.png the grille looks far too small - on a dark car the body-colour surround (z 0.551-0.70) reads
as part of the black opening (0.573-0.650). Measured properly they agree; nearly 'fixed' a correct part.
SCUTTLE done (034eaf7, tools/gen/rebuild_scuttle.py) - and the bonnet's REAR edge was wrong too: the dark line I
traced on the shell at y -0.68 is the SCREEN BASE (glass edge), not the bonnet's rear edge. body_profile.json
"scuttle_curve" (c20+cCF: wiper pivot 0,-0.800,0.933, washer jets +-0.175,-0.811, louvre row) has all three:
bonnet rear y = -0.900 + 0.33x^2, screen base y = min(-0.740 + 0.29x^2, -0.702), louvres |x|<0.46, 8-48 mm ahead
of the base, 11 mm pitch, 6 mm slots, broken at the pivots. The bonnet had been ~220 mm too long at the centre.
Scuttle panel = quad patch between the two lines, heights off the ruler, mirror-averaged + faired, 160 mm wide at
the centre; rear edge MARKED SHARP (smooth-shaded the screen-base step reads as a fat rounded bar) and bridged up
to Chassis_Front; front edge returns 40 mm down so the shut line is a dark gap not the background.
LESSON: before trusting a line traced off the Meshy shell, check tools/photomatch/body_profile.json + front_end.py
+ docs/DECISIONS.md - the project already has most body lines triangulated from matched cameras.
WINGS REBUILT 26 Oct (de08956) after Nik: "the shape looks wrong" - he was right. vs the project's traces the
shell-fitted wing had the arch lip 26 mm TIGHT all round the top (arch_shapes.front, traced on anglia_side/cS,
hubs to 1 px), the body 15-30 mm NARROW per side (halfw: FIA 1522 front axle / 1535 max), and NO flare step - the
Laplacian fairing had smoothed the GTE's ~8 mm step (wing_flare, z 0.700-0.704, headlamp corner to door) away.
Now: lower edge = traced arch, blended over 70 mm into the detected break at each end (hard switch = notches
+ spikes); each station widened onto halfw, zero at the bonnet shut line, faded out ahead of y -1.50 where the
wing really tapers to the indicator (front_taper); profile split into TWO BANDS at the step so one grid row
(KSTEP) lands on it at EVERY station - snapping the nearest row per station makes the step jump rows and zig-zag
down the whole wing. Open: small crease artefacts at the arch's lower corners; grey arch trims + sill skirts not
modelled.
NEXT: doors, roof + glass, rear.
WING TRAPS: a radius drop does NOT find the arch lip (a ray through the opening hits the inner wing/tyre and comes
back plausible) - use the hit NORMAL (stops facing the ray). And never fair the boundary rings hard: the wing's lower
edge has real corners (arch lip meets valance) and the bonnet's fair_ring(lam 8, 400) cut them off by >100 mm; use
mild fairing + an outlier-only median across stations.
GOTCHAS: Blender writes PNG through sRGB, so a height map read back as linear is ~20 mm high - take heights from
ray_cast, not from a rendered height map. Sampling a UV per grid node off its own hit triangle straddles Meshy's
atlas islands (dark jigsaw); use one affine 3D->UV map per face from the triangle under the face centre.

## 2026-10-20 late: MESHY BODY (earlier route)
Meshy key in ~/.claude/settings.json env (Nik's hand edit had MESHI typo + missing comma - fixed). F400 PTF 4 views
(reference/meshy_input: commons 1989 GTE front/rear + anglia side/rear, same car, factory alloys) -> meshy latest
multi-image, 2k geometry, 4k tex (35 cr) = export/meshy/f400_v1.glb (red-car set red_v1.glb = Nik's black wheels,
worse). tools/gen: fit_meshy (orient/scale to 3.622, measure), prep_meshy (axles -0.0195, decimate 0.15 -> 394k),
cut_doors (DOOR_L/R from the model's own shut lines, inner skin, jambs, hinge pivots), door_test, view_glb.
blender/nova_meshy.blend. Nik: close match OK, scale later; leave interior until the shell is decent; doors must open.
Generated proportions: wheelbase 2.342, track 1.31, height 1.339, body width 1.58 (spec 1.532).
Shell now from Meshy REMESH (f400_v1_remesh300k.glb, 5 cr) - Blender collapse decimation scrambles the UVs, never use
it. prep_meshy welds UV-seam verts (1e-4) BEFORE cut_doors (else inner-skin fins). Smoothing = smooth_taubin.py 80
passes (normal-only Taubin, door outline +-2.5 cm and side-window band pinned); Sun-2007 denoise crumples this mesh.
Backups: BACKUP_nova_meshy_before_smoothing.blend.
NEXT (Nik 2026-10-20, agreed, little time this week): option 4 = trace panel outlines/feature lines ON the Meshy shell
(shut lines, window openings, arch lips, beltline/bumper lines) and rebuild each section as a clean quad panel fitted
smoothly to it; one section at a time, show Nik each; start with the BONNET as the test; texture baked across last
(unchanged colours); doors stay separate/openable. Research run was cancelled (nothing found). nova_meshy_car.blend (recolour/export attempt) = abandoned per Nik.

## 2026-10-20 evening: PROCEDURAL ROUTE STOPPED AT PHASE 12 (Nik: "the car looks crap") -> MESHY NEXT
Phases 1-12 done + committed (last d812270; phase 11 normals fix 8f55656, phase 5 audit fix 700be98); saved as
blender/nova_proc.blend + blender/BACKUP_nova_proc_phase12_2026-10-20.blend. Nik wants Meshy (image-to-3D) instead;
I listed what's needed (key check via free meshy_check_balance, model/cost confirmation, best reference images,
output format GLB/FBX). Earlier generated-body route (TRELLIS, nova_gen.blend, fit/prep/export_gen.py) is the
pipeline to reuse for fitting a Meshy model to the FIA dims + our wheels/interior/export.

## 2026-10-20: PROCEDURAL REBUILD REPLACES THE PHOTO-MATCHED REFERENCE MODEL (Nik: "Replace with procedural")
Nik's phase-by-phase spec ("Opus 5.5 topology & geometry manifesto"): each zone its own mesh object (Chassis_Guide,
Hood, Door_Left, Fender_Front_Left, Bumper_Front...), select verts by coordinates/masks never by index, every edit
ends with remove_doubles(0.0001) + normals_make_consistent, every script ends with a self-audit that raises on
>= 1 mm deviation. Scripts: blender/scripts/proc/phaseN_*.py -> blender/nova_proc.blend (headless, --factory-startup).
Phase 1 done (phase1_bounds.py: box 3.622x1.532x1.365 on z=0 centred, axles from FIA overhangs 670/609 at y -1.141 /
+1.202, z 0.2916, tracks 1.320/1.300 (Nik's 1.300; sheet says 1.307), scene['nova_gte_dimensions']). Next: side
profile outline. The old ref pipeline (rebuild_ref.py, front_new/wing_new/bonnet_new/bumper_sweep) stays in git as
reference only; the deployed car is still from it until the procedural one replaces it.

Project: `D:\Claude\vauxhall_nova_gte_1989` (git, car id `vauxhall_nova_gte_1989`, 1989 spec, RHD, factory 5J x 14
alloys, pre-facelift, gun-metal grey). `D:\Claude\nova-gte` = Nik's ORIGINAL chat plan (1990, nothing built) - the
project already contains all of it; only change is 1990 -> 1989 (decided 6 Oct). Read the project's CLAUDE.md,
docs/DECISIONS.md and docs/EXPORT_NOTES.md first.

- Cowork (cloud) built it 6-12 Oct; its tools assume numpy/scipy/shapely/triangle/cv2 - locally use the project
  `.venv` (Python 3.13 = Blender's interpreter; Python 3.14 has no `triangle` wheel). Run Blender scripts headless
  (`blender -b blender/nova_gte.blend --python ...`) - no Blender MCP plugin needed. Blender GUI may have the blend
  open: it showed no unsaved changes 12 Oct; tell Nik to File > Revert if he looks at it.
- Photo matching: 7 solved cameras in tools/photomatch/ba_result.json (c20/c22/c23/c24 = redgte_20.., cAR/cS =
  anglia_rear/side (F400 PTF), cCF = commons 1989 GTE front). cS (side) is the most reliable (wheels match to the
  pixel); front views have depth ambiguity - BA points seen only from the front can be cm off (BON_F was 6 cm off).
  Triangulate with two views; cS + cCF see opposite sides -> mirror one ray. Compare with matched-camera renders
  (render_matched.py flat / lookdev.py EEVEE) - scratch helpers I wrote: sbs_crop / blend_crop / gridcrop.
- Nik 12 Oct: "the current model is pretty bad, it will all need fixing once you are done with the bonnet" -> after
  the front (done 12 Oct, 68abbd6): side/arches, rear end, roof/glass/sunroof, wheels (see RESUME below), interior. One final image per section
  ([[feedback-screenshots-one-per-section]]).
- Open: length 3.58 m vs FIA 3.622 (side photo says ~3.60); wing corner above the indicator still faceted;
  lamp/glass materials; physics still Phase 1 skeleton. NO triangle target (Nik 2026-10-13: "irrelevant") - never
  raise tri counts / LODs as a goal again.

## 13 Oct evening: GENERATED BODY ROUTE (Nik: "they can't be any rougher than what we've spent days on")
Rule extended (8a0e489): free image-to-3D (Hunyuan3D/TRELLIS on Hugging Face) allowed. HF connector is signed in
(OAuth, account nicklearse101, not PRO) but its Space `invoke` is off (gradio=none) - so Spaces are called with
gradio_client from venv D:\Claude\_tools\hfgen (uv, py3.12), anonymously. trellis-community/TRELLIS multi-image
(E19 GTE front+rear 3/4 Wikimedia photos + anglia_side) took 61 s -> export/gen/trellis_multi3.glb: reads clearly as a
Nova GTE (far better than the procedural shell), but lumpy, 25k tris, one rear quarter textured black, 1.77 x 3.622 x
1.43 m when scaled to length (too wide/tall -> non-uniform scale to FIA dims). Next: TRELLIS.2 (microsoft/TRELLIS.2,
res 1536) single-image test, then pick a base and turn it into the AC body (scale to FIA, our wheels, materials).
Scripts: scratchpad trellis_gen.py / trellis2_gen.py / gen_view.py (copy into tools/gen when kept).
DEPLOYED 13 Oct 17:27 (Nik: "stop wasting time on paint and just export it"): generated body in AC (8d406c8) -
blender/nova_gen.blend + fit_generated.py / prep_generated.py / export_gen.py (zone materials from the procedural
parts, windows cut with procedural-glass slabs, our wheels + interior). Anonymous ZeroGPU quota used up until ~14 Oct
17:15; TRELLIS.2 run (res 1536, scratchpad trellis2_gen.py) is the next step, then re-run fit/prep/export.
Nik logged this PC in (hf auth login, browser OAuth, account Nicklearse101w; tools/gen scripts pass get_token()) but
the free account hit 'ZeroGPU runs limit' 13 Oct. Nik made a TRELLIS.2 model on the website himself
(export/gen/nik_sample/sample_1626.glb, 283k tris, crisp front/sides, black aftermarket wheels): its rear is guessed
and 11 cm short -> zone materials go ragged at the rear (blender/nova_gen_t2.blend). Plan: Nik generates the REAR
from a rear 3/4 photo on the TRELLIS.2 page, I splice front (sample) + rear (rear run) at the door's rear shut line.

Related: [[talbot-sunbeam-lotus-ac-mod]] (kn5 writer origin), [[escort-mk2-dtm-project]].

## RESUME HERE (12 Oct ~23:15)
Done 12 Oct (commits 68abbd6, e7a91ea, 3f51d8a): front end, bonnet (two lengthways creases + level front edge
z 0.722, tip re-triangulated with the cS silhouette), front bumper lower edges levelled, rear bumper as
tools/rear_end.py parts, continuous belt line, hatch glass/seal/black-panel zones, exhaust moved. Nik reviews in his
open Blender: reload it for him with the blender-mcp plugin (revert_mainfile via a timer; he OK'd the plugin for
this) only after checking bpy.data.is_dirty is False. He asked: few pictures (usage), accuracy to the photos,
go round the whole shell first, polish later; he'll re-check the bonnet front at the end.
Bumper rib stripes levelled end to end (Nik's request; 4d14321, 3523c42).
13 Oct: wheels re-measured (c1a0361), door glass division bar (925dcd5), scuttle/screen base/bonnet rear edge on a
plan curve with louvres + jets + wipers (c97e90a). Greenhouse side lines, mirror, handle checked OK vs cS. Sunroof
width OK (c20), fore-aft unmeasurable - polish pass. Interior fitted to the shell's inner surface (48448ca).
First round of the whole car DONE 13 Oct, shown in Nik's Blender. Nik then: shell first, interior after; roof/rear
"rubbish", scuttle wavy, "wing step" missing. Shell round 2 done 13 Oct (491a64d): wing flares (wing_flare), scuttle
rows bent not cut (warp_scuttle), tailgate glass + sunroof as inset panels (glass_panels.py), roof lip, drip rails,
windscreen surround, boot trim. 13 Oct round 3 (after Nik: "absolutely rubbish", sent blueprints, rear arch must be
flat): arches traced from cS as polylines (arch_shapes), bonnet waves = spline curvature jumps -> quadratic fit
(top_bonnet_fit), roof visor flush (TE 1.375/1.27), tailgate glass recessed 35 mm + Boolean-cut openings, measured
tailgate shut line (SHUT_TG), clamp_top re-spacing, tail-lamp frames, SmoothNormals data-transfer on rear sides
(817d366). kn5 exported in the project, NOT deployed. Nik's verdict on round 3: "looks like a Nova that's been in a crash",
roof/rear/spoiler wrong, used most of his weekly limit. He CHANGED THE RULE (8af18cc): Tripo/Meshy generated meshes
allowed. Tripo CLI (API) balance is 0 - his 145 credits are on the tripo3d.ai web studio (separate wallet). Next =
a generated body from photos, then scale/align/split for AC. Be economical with usage.
Tripo free web tier can't export -> back to the procedural model. Round 4 (4a0393f): lookdev.render() never ran
setup() - all my matched comparisons had used see-through raw materials (the "crash" look); fixed. Also fixed X folds
on C-pillars, double wing line (crease_z = step line), spoiler lip, roof shut line, drip-rail ends. ALWAYS judge with
lookdev renders (setup applied) + clay_matched (scratchpad) before showing Nik. Not deployed yet.
Meshy/Tripo not options (Nik). Best review format: model painted RED (scratchpad ld_red.py -> export/match_red,
sbs_red.py) next to the photos - grey made me misjudge. Nik's worst areas: rear end, roof & glass, wing mirrors ->
fixed 13 Oct (b6293fa, 7573ff9): window top 3 cm lower + black frame + body band, mirror wedge 17x12 cm, tailgate
glass black border, tail lamps recessed/widened to the corner. c24 is weakly calibrated (too high) - don't judge the
roof from it.
DEPLOYED to AC 13 Oct 13:58 (Nik asked; backup export/deploy_backups/20261013_135809_*, only kn5s differed).
Other Nova files searched (D:, user folders): only the plan skeleton (D:\Claude\nova-gte = Downloads zip) + AC setups
-> copied to reference/original_plan + reference/ac_setups (4624a3f). Refs in project: FIA 5375 PDF, Oct-1988
brochure PDF, 1983-93 Corsa workshop manual PDF (reference/manuals). 13 Oct after deploy: mirror sail enlarged
(3bf112b, in the project kn5, NOT yet deployed). A separate "pillar tip" flap over the lamp looked stuck-on -> removed;
RESUME: make the C-pillar fins themselves stand proud of the tailgate (shell change, rear section), then whatever Nik
flags next (review in red side-by-side). Nik pasted a Hugging Face token in chat 13 Oct - told him to revoke it;
never use pasted tokens. Earlier open shell items: crisp C-pillar rear edge, wing corner above the indicator, rear
wiper on the recessed glass, tail lamp surrounds. 337k tris (BODY 118k, FRONT 61k, REAR 54k,
WHEELS 71k). Not exported/deployed since 12 Oct 22:44 - asked Nik before deploying. NEXT (polish pass, after Nik's
review): bonnet front with Nik, interior shapes (seats, binnacle pod), tri budget + LODs, materials, export + deploy +
in-game check.
Earlier wheel notes (done): cS wheel faces were rectified onto the wheel plane and averaged two wheels x 3-fold
(scratchpad rect.py / sym.py / wov.py; wov1.png = current design over the photo, not yet looked at). Measured:
arms at 30/150/270 deg, half-width ~0.075 (model 0.070, OK); window outer r ~0.160, inner corners meet ~0.09 at the
window centre (model's disk-minus-arm-bands layout is right). WRONG in the model: the slots sit +-0.021 from the arm
axis, parallel to it, r 0.085-0.16, ~10-12 mm wide (model SLOT_P 0.038, 0.080-0.160). The centre cap is bigger and
softer than the model's sharp pentagon (check in r_LF_raw / r_RR_raw). Then roof/sunroof/glass, side details
(mirrors, handles), interior.
14 Oct: DEPLOYED spliced TRELLIS.2 body (b55d7f1): front = sample_1626 (13 Oct), rear = sample_rear (14 Oct),
cut at y -0.189, via blender/scripts/splice_generated.py. Material zones still ragged where the shapes differ; not checked in-game.
14 Oct Nik saw it in CM: "shape much better than our attempt, needs a lot of cleanup". Waiting till Monday (usage).
CLEANUP PLAN: smooth lumpy panels (Corrective/Laplacian smooth on paint faces, keep edges), material zones by
the generated shape itself instead of nearest procedural part (ragged black/red patches at rear panel, bumper
stripes, sills), headlamp/tail lamp as clean separate parts, mirror fix, seal the splice seam, check interior fit.
19 Oct: NEW BASE = Nik's own high-detail model D:\Claude\Novamodel.blend (1 mesh "classic car 3d model", 1.9M faces,
no materials, arbitrary units; copy at export/ref/Novamodel_src.blend). Scaled to FIA length its body matches within
~2 mm; only the wheelbase/arches were off (2257, wheels 542 mm). fit_reference.py -> export/ref/nova_ref.blend
(REF_BODY, wheels split to REF_WHEELS hidden, our WHEELS at the real axles): wheelbase 2343, overhangs 670/609,
arches on the cS-traced arch_shapes (8ca30db). Width at axles 1500/1507 (FIA 1522/1529), mirrors 1688 (1725).
ALWAYS check in Nik's Blender with the blender-mcp `look` tool (he wants that), confirm the file reloaded first
(timer-based reload: a look straight after can show the OLD scene). Next: materials (model has none), glass (window
openings empty), interior check, export to AC.
19 Oct: SHELL MAP done (a4d5bd4): docs/SHELL_MAP.md + docs/shell_map.jpg, SHELL_MAP collection in nova_ref.blend.
Key: doors y -0.678/+0.455, bottom z 0.288; bonnet shut lines x +-0.63, front edge y -1.68, rear -0.87; tailgate
shut lines x +-0.565; door/vent/quarter/tailgate glass OPEN, windscreen striated surface, no sunroof; model faults:
transverse bonnet line y -1.27, fuel flap behind the rear arch (real: ahead), round fitting on R B/C-pillar,
mirrored lettering. Tools: scan_shell.py, render_cavity.py, map_features.py, map_grid.py, map_draw.py, shell_map.py.
19 Oct: reference car with glass + materials DEPLOYED (export/ref/nova_ref_mat.blend; prep_reference.py,
export_ref.py; 1.3M tris, 50 MB kn5). Model is LHD inside - our RHD wheel/gauges overlaid. Next = docs/MODEL_TODO.md
(bonnet line, fuel flap, pillar fitting, sunroof, mirrored lettering, LHD interior, widths, pinstripes, lamps/lights, LODs).

- 2026-10-19 (later): MODEL_TODO items 1-6, 8-13 done and deployed (last commit cab86b5). Pipeline now:
  fit_reference -> rebuild_ref.py [fix_shape, prep_reference, frames_ref, details_ref] -> export_ref -> tools/deploy.py.
  Plates from tools/make_plates.py (made-up "F160 GTE"). lights.ini + extension/ext_config.ini written, not yet
  checked in AC at night. Nik paused for the usage reset: NEXT = item 14 interior colours (photo-sampled greys,
  striped seats, seat centres x +-0.36 front / +-0.49 rear), then 15 LODs (1.1 M verts, 56 MB).

- 2026-10-19 evening: research report reports/Nova mesh cleanup and opening panels.md (deep-research). Shading now by
  normal transfer from a smoothed copy (normals_ref.py, last step before frames/details; all faces smooth; bumper rib
  bands soft). Deployed 74c4d10. Still jagged: edge LINES (grille surround, headlamp tops, bonnet front edge/shut
  lines, window ledges, tail-lamp edges, scuttle-end folds) = geometry, needs edge straightening/rebuild. Opening
  panels: per-panel hinge dummy + .ksanim (Escort's write_door_ksanim to generalise) + CSP [ANIMATION_x] on EXTRA
  switches C/D/E/F (STATIONARY_ONLY); Kunos names DOOR_L/R, MOTORHOOD, REAR_HOOD; template car = Lotus Carlton mod.
  driver3d.ini names steer.ksanim which doesn't exist.
