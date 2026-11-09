# Project audit - Phase 0, 2026-11-02

Companion to `CURRENT_STATE.md`. Read-only: nothing in the model, scripts or existing docs was changed.
Compared against `docs/ASSESSMENT_2026-11-02.md` (earlier session, same day) and the master plan's section 18 leads.

## 1. Gate 0 status

- Source of truth: established (active repo, FreeCAD route at wire-frame stage, numpy body comparison-only).
- Rollback path: established (tag `checkpoint-2026-11-02-audit-baseline` on `0cac070`).
- Camera-solve provenance: ESTABLISHED later the same day (section 6). `ba_result.json` reproduces from `obs.json` to within 0.1 mm.

## 2. Claims checked

| Claim (source) | Result |
|---|---|
| Active repo is vauxhall_nova_gte_1989 | VERIFIED |
| FreeCAD network has 96 fitted curves | VERIFIED (96 rows in fairness file; fit json has the lines) |
| No surfaces, no body export from the FreeCAD route | VERIFIED (only curves in the FCStd; no zebra.py; nothing exported) |
| Old numpy body kept for comparison | FILE, consistent with files present |
| Installed AC package is the old 47 MB block-out | VERIFIED size/date (46.7 MB, 20 Oct); triangle count not checked |
| GPU VRAM unknown | RESOLVED: 12 GB (registry) |
| 18 curves over 8 wiggles/m | VERIFIED (18) |
| "10 wobbly lines" (CLAUDE.md, NEXT_WEEK) | CONTRADICTED: DECISIONS (21) names 9; measured numbers differ (section 3) |
| 30.5 mm frame correction applied | FILE only; not re-verified |
| Re-solve moved cCF, c22, c20 by 16-30 mm | FILE only |
| Saloon rear in the 4-view sheet; GA rear gives lamp heights 800/745/685/635 | FILE only |
| Blender MCP protocol 11 vs 15 | NOT tested |

## 3. Curve fairness re-measured (VERIFIED from `fairness_v2fair.json`)

- 18 curves exceed 8 wiggles/m. 8 of them have wobble under 1 mm or length under 0.1 m (ringing or fragments, e.g. `a_pillar`, `bonnet_v`). 10 are real.
- Real, by wobble: `tail_centre#2` 11.4 mm, `crease_front` 7.4, `part_plate_f_1` 6.5 (reference-only group), `centre_screen` 5.6, `window_door` 4.1, `shut_door_rear#2` 3.2, `rear_lamp` 2.9, `rear_body_sil` 2.2, `crease_rear` 1.9, `centre_backlight` 1.3.
- The assessment's "about five" lines undercounts: wiggle rate alone misses smooth-but-offset lines. 36 curves have 3 mm or more wobble; 21 of those are outside the `model_parts` reference group, including `belt#2` 8.8, `centre_roof` 8.4, `moulding_bot` 7.4, `bonnet_shut` 5.6, `window_quarter` 5.5, `centre_bonnet` 5.5. The 3 mm cut-off is my choice, not a project tolerance; a tolerance should be set before triage (master plan section 2.2).
- Implication: triage on wobble amplitude and group, not wiggle rate alone. Probably 15-25 lines need attention, not 5 or 10.

## 3b. Contradictions and document errors

1. Two Nova folders with different model years and different CLAUDE.md. Resolution: `nova-gte` is superseded; leave it, do not edit it.
2. `tools/cad/frame.json` cited in docs does not exist; it is `reference/views/frame.json`.
3. Image-to-3D: CLAUDE.md's header allows it (13 Oct); later lines and STATUS_FOR_CHAT say Meshy is dead and must not be used, even as a ruler. The master plan lists Tripo/Meshy as optional blockout tools. Treat the later decision as binding for the body; NEXT_WEEK allows testing only on small loose parts. Master plan should be amended.
4. Nik's rule (19 Oct) "if it visibly differs from the picture, it is wrong; don't argue from numbers or camera projections" versus numeric gates in the master plan. Compatible only if numbers act as gates and the eye stays the final check. Keep both.
5. Tracked Meshy-era .blend files remain in git despite "Meshy is gone". History bloat, not a correctness issue. Not touched.
6. Camera files dated 26 Oct 23:3x-23:44 while notes describe the re-solve under 27 Oct. Probably a date-labelling slip, unconfirmed.

## 4. Risks in dependency order (upstream first)

1. Camera solve now verified reproducible (section 6), but nothing in the repo records input hashes or run logs, so a later edit to `obs.json` could silently make it stale again. Add a hash check to the pipeline.
2. Features derived from the old solve not yet re-measured: bonnet centreline, nose corner, wiper pivot / scuttle curve, bonnet creases, lamp panel, hatch glass (FILE).
3. Open source conflicts (FILE, DECISIONS (20)-(21)): screen header 21 mm, backlight edge 35 mm, front bumper face 27 mm short, tail length ~25 mm, spoiler y ESTIMATE.
4. No cross-sections (roof crown, tumblehome, belt, shoulder, bonnet, tailgate). Highest-value missing geometry.
5. Curve fairness, section 3.
6. No zebra / strip-light check and no single fixed-view regression command. Parts exist: `render_rect.py`, `ortho_views.py`, `match_look.py`, `overlay_edges.py`.
7. No per-image reference register or measurement schema with uncertainty and held-out flags (master plan section 5). `geo_check.py` compares to the same points used to build (the project's own warning).
8. Downstream, untouched: AC package 47 MB/1.3 M tris, interior, engine bay, physics skeleton, sound.
9. Tooling: Blender MCP mismatch (untested); need a script fallback for every critical step.

## 5. Proposed next step (needs your OK; nothing edited yet)

Step A (DONE, section 6): camera-solve provenance check. Re-run `ba2.py` from `obs.json` into `D:\Claude\_scratch_research\nova_audit\`, compare to `ba_result.json`, report camera and point differences in mm. Expected result: same solution, or a measured drift. Test: numeric diff. Rollback: delete the scratch folder; repo untouched. Stop condition: any disagreement over 2 mm on a point, or the script needs edits to run.
Step B (DONE, section 7): fairness triage from the existing data, tolerance chosen by Claude pending your review. No new tooling.
Step C: then cross-sections, then zebra check, per the assessment's order.

## 6. Step A result - camera solve re-run (2026-11-02)

Method: copied `ba.py`, `ba2.py`, `obs.json`, `ba_cams.json` to `D:\Claude\_scratch_research\nova_audit_2026-11-02\` and ran `ba2.py base soft_l1` (the command DECISIONS (17)/SESSION_KNOWLEDGE give as the accepted solve) twice. Repo untouched. ~10 s per run.
Input hashes (SHA-256, first 16): obs.json A2D93F3F2502EA80; ba_result.json CC1CBFB481707FE4; ba.py 32DE70FC5258F541; ba2.py ABCBA1A28C6C56BA; stale backup 0251CE6E370F3FF7. Full list in the scratch folder's `input_hashes.txt`.

| Comparison (33 triangulated points) | Median | Max |
|---|---|---|
| saved `ba_result.json` vs run A (started from saved) | 0.00 mm | 0.10 mm (QW_RT) |
| saved vs run B (started from the stale 12 Oct file) | 0.00 mm | 0.00 mm |
| saved vs the repo's own `ba2_result_base_soft_l1.json` | 0.00 mm | 0.00 mm |
| saved vs STALE backup | 14.1 mm | 76.0 mm (PLR400); MIR 39, WS_T 33 |

All seven camera poses, focal lengths and k1 values identical between saved and run B. Per-photo median error reproduced exactly: c20 3.3, c22 2.5, c23 2.5, c24 2.8, cAR 4.8, cCF 5.7, cS 7.0 mm (cost 503.53).

VERIFIED: the saved solution is the solution of the current `obs.json`, is deterministic, and does not depend on the starting point. The stale-file story is confirmed (14 mm median shift).
What this does NOT show: that the marks in `obs.json` are right. cCF (12.9 px RMS, max 34 px at WS_T_R) and cS (7.45 px RMS, 20 px at DG_RB_R) remain the weak cameras. Reproducible is not accurate.
Minor: the notes say 34 points; the file holds 33 point entries plus a wheel-radius scalar. Cosmetic.
Stop condition (any point over 2 mm, or script edits needed): not triggered.
## 7. Step B result - fairness triage (2026-11-02)

Data: `blender/data/cad/fairness_v2fair.json` (96 curves, unchanged). Full table: `docs/fairness_triage_2026-11-02.csv`.
Tolerance (ESTIMATE, chosen by Claude, not yet agreed with Nik): views are 500 px/m so 1 px = 2 mm. PASS wobble <= 2 mm (~1 px); MARGINAL 2-4 mm (or > 8 wiggles/m, or out-of-plane > 3 mm); FAIL > 4 mm (> 2 px). Excluded: `model_parts` group (reference only), fragments < 0.10 m, and ringing (> 8 wiggles/m with wobble < 1 mm). "Wobble" is deviation from a fair reference of the curve itself, so it is a fairness measure, not a position error.

| Class | Count |
|---|---|
| FAIL | 16 |
| MARGINAL | 16 |
| ARTEFACT / FRAGMENT (ignore) | 5 / 8 |
| PASS | 19 |
| REFERENCE (excluded) | 32 |

FAIL, by wobble (mm): tail_centre#2 11.4, shut_door_front#1 9.6, belt#2 8.8, centre_roof 8.4, crease_front 7.4, moulding_bot 7.4, tailgate_shut#1 6.2, arch_rear 5.7, centre_screen 5.6, bonnet_shut 5.6, centre_bonnet 5.5, window_quarter 5.5, glass_base#2 5.2, door_bottom#2 4.5, front_a_pillar 4.2, window_door 4.1.
MARGINAL: dlo_top#1, front_roof_crown, front_headlamp#2/#3, rear_panel_recess, shut_door_rear#2, rear_lamp, plan_widest, rear_c_pillar, arch_front, sill, front_body_sil, rear_body_sil, crease_rear, centre_backlight, front_grille. (`front_grille` and `crease_rear` are flagged only by wiggle rate / out-of-plane, a weak signal; wobble is 0.8 and 1.9 mm.)

Findings:
- Earlier estimates were low: "about five" (assessment) and "ten" (CLAUDE.md) versus 16 FAIL + 16 MARGINAL here. Real count depends on the tolerance; at 4 mm it is 16, at 5 mm it is 13.
- Source: of the 32 FAIL/MARGINAL curves, 17 trace the line blueprint, 12 the GA sheet, 2 photo/BA windows, 1 other. This agrees with DECISIONS (21): the drawn line itself wanders, so the fix is re-tracing with the DP tracer or hand-fairing against photos, not smoothing.
- Provenance flag (FILE): the GA traces are labelled "GA 1990 sheet", and REPLICA_PLAN decision 3 says that sheet is the Nov 1990 facelift while the target is pre-facelift. Several flagged front/rear curves (front_a_pillar, front_headlamp, rear_lamp, tail_centre, rear_panel_recess) come from it. Body shell is probably common; lamp and panel detail may not be. Not yet checked against the pre-facelift photos.
- Worst single case, `tail_centre#2`: wobble 11.4 mm but only 8.8 wiggles/m, so a localised kink or offset, not noise. Wiggle rate alone would have under-ranked it.
- Order question: ASSESSMENT puts re-tracing before cross-sections; NEXT_WEEK and master plan section 10 put cross-sections first (they constrain the same surfaces). Following the master plan: cross-sections first.

Proposed next (Step C, approved and run - see section 8): add roof crown, tumblehome, belt, shoulder, bonnet and tailgate sections to the network (`lines_v2` -> `v3`) from the GA front/rear elevations and photos. Expected result: sections as new curves in a new file; existing files untouched. Test: overlay each section on its source view and on the photo through its solved camera; held-out check against a section not used in fitting. Rollback: delete the v3 files (git tag exists). Stop condition: a section disagrees with its source view by more than 5 mm, or sources conflict (screen header, backlight edge) and need your call.
## 8. Step C result - cross-sections v3 (2026-11-02, partial)

New files only; no existing file edited (`nova_lines_v2.blend` hash identical before/after). New: `tools/cad/sections_v3.py`, `tools/cad/blender_show_sections.py`, `blender/data/cad/sections_v3.json`, `blender/nova_sections_v3.blend`; renders in `export/sections_v3_views/` (git-ignored). Nothing committed.

BUILT: half-sections at y = -0.10, 0.10, 0.40, 0.80, 1.15 (roof centre, crown arc, roof lip, glass top/base, belt, widest point; moulding and sill for y <= 0.80). Each point carries class and uncertainty: MEASURED (traces, ~5 mm), ENVELOPE (GA silhouette, +-16 mm), ESTIMATE (carried or skin_x), CONFLICT.
NOT BUILT: bonnet and tailgate sections (no evidence beyond the ESTIMATE crown parameters in `body_profile.json`; needs new photo marks); front/rear-end sections; shoulder/crease sections at the ends. Sections are polylines, not yet fitted fair in FreeCAD, not in `lines_v3`, fairness not measured. So the plan's Step C is partly done: the stop condition ("sources conflict") was triggered for the lower flank; I continued because it affects only the two lowest points, which are flagged.

Findings (VERIFIED = computed from repo data this session):
1. Roof crown: the old crown estimate (35 mm; my normalisation of that parameter is an assumption) is within 8 mm of the GA front silhouette across the central roof, but too flat at the edge: silhouette drop 47 / 66 / 89 mm at x = 0.53 / 0.55 / 0.561 against ~33-36 mm. Held-out `bp_front` (not used in construction) gives 64 mm at x = 0.55 vs GA 66 mm, so the roll-off is real. At x = 0.50-0.53 the two sources differ by up to 17 mm (consistent with the ~2.6 % x-scale distortion noted for GA sheets on a steep slope).
2. GA front and rear silhouettes (both are max |x| over the whole car, so should match) differ by up to 16 mm. The rear one reproduces the SOURCED 1535 mm width (0.7674 vs 0.7675); the front is ~11 mm narrow. Use the rear for width.
3. Lower flank: `moulding_bot` and `sill` x = 0.766 (the numpy shell's skin_x, an ESTIMATE) are 31 and 58 mm outside the GA envelope, but within ~2-8 mm of the held-out `bp_front` outline on most rows (noisy: one row 25 mm). The GA envelope below z ~0.4 is also narrower than the sourced tyre half-width (0.7475). SOURCES CONFLICT, UNRESOLVED. Needs a photo-based check or the GTE sill-skirt dimension; do not change the shell on this evidence.
4. The two "glass top" sources (window curves vs `roof_edge`) disagree by 9-30 mm (largest 30 mm at y = 1.15), against ~5 mm tolerance each. Unresolved. The roof lip to glass-top step also leaves a small hook at the roof corner in the sections: an artefact of combining two sources until resolved.
5. Numpy body bounding box (from the file): z top 1.349 vs SOURCED height 1.365 (-16 mm); length 3.597 vs 3.622 (-25 mm, front bumper 27 mm short is already known); x +-0.7844 vs SOURCED half-width 0.7675 (+17 mm per side). Not decomposed by part, so the width excess may be arches or wheels; per-part breakdown pending.

Tooling note: Blender MCP add-on is protocol 11 vs 15 expected but works via fallbacks (VERIFIED). The live Blender session has the Escort Mk2 project open (`escort_v27.blend`); it was not touched. All Nova scenes were built in separate background Blender processes.
## 9. Regression command v1 (plan section 16 step 8) - built and baselined 2026-11-02

Run: `.venv\Scripts\python.exe tools\regress\run_regression.py` (about 20 s). New files only: `tools/regress/run_regression.py`, `blender_measure_render.py`, `spec_targets.json`. Reports in `reports/regression/<run_id>/` (report.json, report.md, blender.log); images in `export/regression/<run_id>/` (git-ignored). Read-only on the model; exit code 1 if a check that passed last run now fails. Run twice back to back and the second run found no changes (VERIFIED); no tracked file modified.
Every run records commit, uncommitted list, SHA-256 of the inputs (including `obs.json` and `ba_result.json`, which closes the stale-solve risk once someone compares hashes between runs), Blender and FreeCAD versions.
Tolerances were fixed before the first run (ESTIMATE, pending Nik): 3 mm for hard points, 10 mm for overall dimensions. Predictions written before the run all held.

Baseline on `nova_proc.blend` (the numpy body; commit 0cac070 plus untracked files):
| check | target | measured | delta | result |
|---|---|---|---|---|
| wheelbase | 2343 | 2343.0 | 0.0 | PASS |
| track front / rear | 1320 / 1307 | 1320.0 / 1307.0 | 0.0 / 0.0 | PASS |
| tyre radius | 291 | 291.6 | +0.6 | PASS |
| overhang rear | 609 | 610.5 | +1.5 | PASS |
| length | 3622 | 3596.8 | -25.2 | FAIL |
| overhang front | 670 | 643.3 | -26.7 | FAIL (front bumper face, known from DECISIONS (20)) |
| height | 1365 | 1349.2 | -15.8 | FAIL (`Body_Shell` roof; the old `Roof_Panel` reached 1.366) |
| width | 1535 | 1568.7 | +33.7 | FAIL |

Resolves the open point in section 8, finding 5: the width excess is set by `Wing_Front_Left` (1568.7 mm), then the `SHUT_DOOR_FRONT` groove mesh (1565.3) and `Skirt_Left` (1559.0); `Body_Shell` itself is 1534. So the front wing sits ~17 mm per side outboard of three independent sources (FIA 1535 mm, GA rear silhouette 1535 mm, held-out `bp_front` outline 0.764 half-width). Probable cause is the estimated GTE wing-flare in `body_profile.json` (not confirmed). Mirrors add to 1725 mm overall.
Zebra pass: fixed settings (stripe scale 2.5, 48 samples, 1000x625; Cycles CPU, mirror override material, striped world). Baseline images show broadly parallel stripes on the flank with visible steps near the sill, door bottom and arches; judged by eye only, no numeric criterion yet.
Known noise: headless Blender loads the Tripo add-on (port 60600 warning) and prints `use_nodes` deprecation warnings; harmless.
Not covered by v1: reference-drawing overlays, renders through the 7 solved cameras, curvature combs, mesh health (non-manifold, holes, normals), feature positions, FreeCAD surface checks (none exist), AC in-game checks.