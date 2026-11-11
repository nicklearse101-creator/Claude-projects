---
name: blender-work-kn5-study
description: Blender work project (Claude- repo blender/) started 2026-11-09 - kn5 reverse-engineering of 112 AC cars (incl. single-seaters) + Nova; spec dimension checks, silhouette compare, target numbers for generated cars
metadata:
  node_type: memory
  type: project
  originSessionId: e3c6919d-db77-4ec5-b018-abdda29cd136
  modified: 2026-11-09T09:55:36.553Z
---

Nik's "master plan" Blender work project lives in `D:\Claude\Claude-\blender\` (README index). First item, 2026-11-09:
`blender/kn5-study/` = tools (kn5full reader, analyze, blender_import, uv_sheet, section, shape_rules) + REPORT.md.
Work files and study blend: `D:\Claude\_scratch_research\kn5_study\` (kn5_study_AE86_vs_205.blend; game assets, not in git).

Kunos recipe (measured on ks_toyota_ae86):
- About 242k tris for the whole car; painted shell about 28k.
- Quads with about 20 mm spacing (40 mm on flat areas); 0.5 % hard edges; crisp lines come from tight extra loops.
- Single skin; shut lines are about 5 mm returns with a 3–4 mm gap, darkened in the texture; two-layer glass.
- One 2048² "unfolded car" paint atlas.
- Interior = baked AO diffuse × tiling txDetail.
- Standard dummy names; LODs at 22 % / 7 % / <1 %.

The installed Nova block-out (20 Oct) is 1.44M tris with 5–7 mm edges (thin triangles are NOT a fault: about 23 % of Kunos paint tris are under 5°). Next: export the current section-built body and grade it with analyze.py / shape_rules.py.

Phase 2 (same day): 8 more cars (E30, Escort Mk1, 595, MX5 ND, Sport quattro, Clio Williams, Kadett C, R5 Turbo) in REPORT_PHASE2.md.
- Tested techniques: measure.py + specs.json + compare_specs.py. Kunos is within about 1 %: wheelbase ±18, length ±26, width ±36 mm.
- Height always reads low (AC ride height). The check catches mod errors (Clio track, Kadett).
- silhouette.py: same-car models from different authors agree to about 10 mm.
- construction_sheet.py, survey.py and fairness.py; the fairness metric is density-dependent, so inconclusive.
- Kunos rules: half model mirrored exactly; 89–94 % quads; paint shell 20–35k tris on an 18–27 mm grid; loops follow features, not stations.
- Kunos paint skin = white 1024² with baked AO (shut lines dark), gloss carries the same AO, and the paint normal map is damage only.
- Nova block-out: dimensions exact, construction fails.

Phase 3 (same day, REPORT_PHASE3.md): 112 cars in total (67 Kunos, 29 mods, 12 single-seaters/open, 3 traffic, Nova).
- Specs come from Wikipedia infoboxes via curl (Python urllib fails on an expired cert).
- Kunos recipe confirmed on all 67 cars. Wheelbase matches specs to a median of 2 mm.
- Mods use about 2x the triangles and are about 4x less accurate.
- Single-seaters: rigid suspension meshes animated with car_susp_XX.ksanim, about 13 % hard edges.
- measure.py width now uses a 0.6 m spike filter below the belt, so mirrors drop out (road-car median 8 mm).
- Repo is private. Sensitive items were found and reported to Nik; he has not yet chosen how to clean up.

Gotchas: skinned kn5 meshes have a short trailer (material, layer, lod in/out only); kn5 V is stored negated.

Related: [[nova-gte-project]], [[feedback-blender-use-plugins-skills]].

Replica work (2026-11-09, REPLICA_PLAN.md). Nik's rule: build from scratch, using other cars only as education, never as a base mesh.
- Blind test on the AE86 (blind_test.py):
  - outlines only: median 8.5 mm, 56 % within 10 mm
  - + learned section shapes from 11 cars: 63 %
  - Outlines can't make a replica.
- Lines -> surface (lines_to_surface.py): panel outlines + creases + soft feature lines + sections every 400 mm, with a thin-plate fill, give median 1.1 mm and 87 % within 3 mm.
- So the method is: character-line network first, then smooth quad patches. Panel-edge recipe: 5 mm return, 5 mm holding loop, 10 mm.
- Next step: rebuild the AE86 from lines (generator test), then from pictures.
- The Blender scene (unsaved) has the AE86_layout_view and AE86_lines_test collections.
- 2026-11-09 afternoon: Nik said smoothing-based building never works (blobby, no crisp edges). Agreed.
  - Smoothing generators are dropped (thin-plate, quad-sphere, height fields): best 2.4-2.9 mm, but lumpy.
  - New direction is CAD-style curves -> exact patches. A Gordon network on the AE86 door gave 2.3 mm median and 87 % within 3 mm, but my numpy tracing/trimming was buggy.
  - Next: build panels in Blender natively (Bezier curves -> lofted or bridged loops through the sections), score both ways, check in grey.
  - Always score both ways: a one-way score hid a folded patch.
- CAD on the PC: FreeCAD 1.1.4 at D:\FreeCAD\bin\freecadcmd.exe runs headless Python with OpenCASCADE (loft, BSpline interpolate, makeFilledFace, STEP).
  - It was tested on the AE86 door sections: as accurate as our own loft (1.7 mm, 91 % within 3 mm).
  - Plan: use it as the surfacing engine for builder v2, then sample the surfaces into quads for Blender.
  - OpenSCAD 2021 and truescad are CSG/SDF tools, not useful for car bodies.
- Nik (2026-11-09): nothing should use C:. Run FreeCAD via blender/kn5-study/fcrun.sh.
  - It sets TEMP and FREECAD_USER_HOME/DATA to D:\ClaudeData; the CurvesWB copy is in D:\ClaudeData\FreeCAD\Mod.
- First CAD body: one B-spline surface over the whole body looks like draped cloth.
  - Avoid dense-curve lofts (OCC hangs) and 0.4 mm meshing.
  - Next step is panel-by-panel Gordon patches.

**THE WORKING METHOD (2026-11-09 evening; Nik: "a really good door, save that technique")**: `blender/kn5-study/PANEL_FIT_TECHNIQUE.md`.
- One smooth B-spline per surface, fitted to the vertices; control counts chosen by cross-validation, searched in both directions independently.
- Trimmed to the real outline in FreeCAD.
- Character lines are fair curves, with bands cut exactly on them (prism common).
- Even mesh plus exact normals; zebra check.
- Tools: panel_fit.py -> panel_fit_freecad.py (fcrun.sh) -> exact normals -> Blender collection AE86_door_fit.
- Proven on the AE86 door and glass.
- Scoring: score_exact.py. The old point-sample scorer added about 1 mm of fake error.
- The v5 strip build (cad_panels.py) is superseded.
- Next: the window-frame and shoulder-roll bands (about 1.5 mm), then the rest of the car panel by panel, then shut-line returns.

2026-11-10 night: rear quarter built (`:wN` corner split, seam matching + one smooth seam curve, line pinning for all bands, hole filler ignores Kunos chord sag). regress.sh reference: door 87.9/99.6, wing 70.6/96.1, quarter 78.2/96.8 (area within 1/3 mm; vertex scores are the honest ones). NEXT = thin-strip builder (ruled strips between shared edge curves; lamp-top step first), then roof. Handover: blender/kn5-study/NEXT_SESSION.md.

2026-11-11 night: chain-side strips (drip rail r7 0.09 mm), fold flanges (C-pillar window flange r6 = two ruled strips), strip sanity checks + sharp-corner rule; regress reference door 88.5/99.7, wing 70.5/96.1, quarter 79.4/96.9 (vertices 88.2/98.6). Found by eye: our C-pillar r1 reads as a round tube - vertex-only fit bulges up to 9.8 mm over Kunos's flat top facet; flat facets (corner normals within 4 deg) are real data, chords are not. r1 = top + shoulder + side + foot fan, needs research then a multi-face build (NEXT_SESSION.md "Next 0"). Grey pictures without Blender: grey_render.py; sections: sections.py.

2026-11-11 morning: research report 'Smooth region segmentation into faces' (blender/research/reports); C-pillar built as a station-profile surface (blend_build.py, spec :pillar1: top line + G2 shoulder + side line per 25 mm station, smoothed defining points, FreeCAD approximate); pillar vertices p95 0.5 mm (was 2.4), looks right in grey; quarter 84.4/99.5. NEXT: the foot (tail-top corner, r1x10) + its join to the pillar, then roof.

2026-11-11 (later): C-pillar foot done - pillar + foot = ONE station-profile sweep (sweep_build.py; foot = flat deck + wrapped skirt joined by one roll continuing the pillar shoulder, not a vertex blend); deck = own face cut on the sweep edge; FreeCAD approximate fails quietly on long grids -> interpolate fallback. Regress: door 88.5/99.7, wing 70.5/96.1, quarter 85.9/99.3 (vertices 90.1/98.2), commit 09e30e7. Roof research report done (blender/research/reports/Roof surfacing.md). Foot touch-ups done same morning (commit 97b8ce4: stations resampled from a stable anchor, deck cut on the sweep's real edge, sweep band as deck tangent data; quarter 85.8/99.3). NEXT = the ROOF per the report. Nik confirmed: small holes at joins get closed by sewing at assembly (later); bumpers are body panels, lamps/grille/badges come after the shell.

2026-11-11 (afternoon): ROOF first build (roof_build.py + roof_score.py, commits 24081a2 + handover). Kunos roof = crown + rear band (line z -0.896) + side bands (rear half, side line x 0.461). Crown = ONE fair surface mapped rear line->header (single span deg 7x5); Kunos roof vertex heights are lumpy 0.3-0.7 mm (normals fair) and the centreline row is a ~1.1 mm half-model ridge - fair crown ignores both. Vertices median 0.19 / max 1.2 mm, area within 3 mm 100 %. Judge fairness with isophote islands. NEXT = soften the rear line (G1 roll band + corner patch), then neighbours (drip strips, headers, C-pillar top r1x00) from the roof's edges. Picture images/roof_v1_grey.png.
