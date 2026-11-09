# Regression run 20261102-174306-0cac070

commit `0cac070` (master) + 12 uncommitted/untracked; blend `blender/nova_proc.blend` (b3d10132c59d7b26); Blender 5.2.1 LTS; FreeCAD 1.1.4 Revision: 20260928 (Git shallow)
elapsed 12 s; images: `D:\Claude\vauxhall_nova_gte_1989\export\regression\20261102-174306-0cac070`

| check | target | measured | delta | tol | status | source |
|---|---|---|---|---|---|---|
| wheelbase_mm | 2343 | 2343.0 | +0.0 | 3 | **PASS** | FIA A-5375 p2 (SPEC_SHEET, resolved) |
| track_front_mm | 1320 | 1320.0 | +0.0 | 3 | **PASS** | SPEC_SHEET (SOURCED), as quoted in ASSESSMENT_2026-11-02 |
| track_rear_mm | 1307 | 1307.0 | +0.0 | 3 | **PASS** | SPEC_SHEET (SOURCED), as quoted in ASSESSMENT_2026-11-02 |
| tyre_radius_mm | 291 | 291.6 | +0.6 | 3 | **PASS** | 175/65 R14 unloaded radius, SPEC_SHEET (SOURCED) |
| length_mm | 3622 | 3596.8 | -25.2 | 10 | **FAIL** | FIA p2 (SPEC_SHEET, resolved) |
| width_mm | 1535 | 1568.7 | +33.7 | 10 | **FAIL** | FIA p2, measured at the front wing behind the axle |
| height_mm | 1365 | 1349.2 | -15.8 | 10 | **FAIL** | BROCHURE p35 |
| overhang_front_mm | 670 | 643.3 | -26.7 | 10 | **FAIL** | FIA p2 |
| overhang_rear_mm | 609 | 610.5 | +1.5 | 10 | **PASS** | FIA p2 |

Width set by: [['Wing_Front_Left', 1568.7], ['SHUT_DOOR_FRONT', 1565.3], ['Skirt_Left', 1559.0]]. Height set by: [['Body_Shell', 1349.2], ['GLASS_SCREEN_L', 1296.1]]. Mirrors add: overall 1725.0 mm.
53 objects, 126290 polygons.

vs previous run (none - this is the baseline): regressions none; changed >= 1 mm: none

Not covered by v1: reference-drawing overlays (tools/cad/overlay.py, render_rect.py exist separately); renders through the 7 solved photo cameras (match_look.py, overlay_edges.py); curvature comb / zebra on FreeCAD NURBS faces (no surfaces exist yet); mesh health: non-manifold, holes, self-intersection, normals; feature positions (lamps, pillars, shut lines) - only overall and hard-point dimensions are checked; wheel arch gap / ride height / AC in-game check.
