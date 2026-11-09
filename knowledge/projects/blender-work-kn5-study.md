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
