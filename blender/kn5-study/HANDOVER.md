# Handover: kn5 study / Blender work project (as of 2026-11-09, 10:10)

Read this first in a new session, then `KN5_STUDY.md` (the full write-up).

## What this is
Nik asked for the master-plan Blender work project to start with reverse engineering how Assetto Corsa
cars are built. The aim is to reuse whatever works when generating our own models (Nova, Sunbeam,
Escort, future cars).

Done so far:
- **112 cars studied** (phase 3, `REPORT_PHASE3.md`): 67 Kunos, 29 mods, 12 single-seaters/open cars, 3 traffic cars, our Nova.
- **Measured against published dimensions** found online.
- **Construction rules extracted:** budget, grid, quads, symmetry, shading, UV/skin layout, panel gaps,
  how lamps, grilles and badges are made.
- **13 tools built and tested** for checking any car's accuracy and construction.

## Where everything is

| What | Where | On GitHub? |
|---|---|---|
| Full write-up | `blender/kn5-study/KN5_STUDY.md` | yes |
| Phase reports (detail) | `blender/kn5-study/REPORT.md`, `REPORT_PHASE2.md`, `REPORT_PHASE3.md` | yes |
| Phase-3 batch scripts and car lists | `blender/kn5-study/phase3/` | yes |
| Tools (13 Python files) | `blender/kn5-study/*.py` | yes |
| Published specs with sources | `blender/kn5-study/specs.json` | yes |
| Result data (our measurements) | `blender/kn5-study/results/` (`measures.json`, `survey.json`, `spec_table.md`, per-car CSV/JSON) | yes |
| Project index | `blender/README.md` | yes |
| Images, sections, silhouettes, extracted textures, study .blend | `D:\Claude\_scratch_research\kn5_study\` (117 MB) | **no, local PC only.** These contain game assets, which must not be published. Regenerate them with the tools if needed. |
| Memory note | `~/.claude/projects/D--Claude/memory/blender-work-kn5-study.md` (synced to repo `knowledge/` by the Stop hook) | yes, via sync |

- **Repo:** https://github.com/nicklearse101-creator/Claude- (branch `main`; local clone `D:\Claude\Claude-`).
- **Game files:** `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\<car>\`.

## Environment (Nik's PC)
- **Python:** system Python 3.14 with numpy 2.5 and Pillow 12. No scipy or matplotlib; the tools need
  neither.
- **Run tools:** from `D:\Claude\Claude-\blender\kn5-study`. Use Windows paths (`D:/...`) inside
  `python -c` strings; `/d/...` only works as a bash argument.
- **Blender:** 5.2.1 LTS with the Blender MCP plugin (`mcp__plugin_blender-mcp_blender__*`).
  - The add-on is **outdated** (protocol 11 vs 15) but works.
  - Nik can update it with `uvx mcp-for-blender install-addon`, then re-enable it in Blender.
  - Load the blender-* skills before Blender work; this is Nik's standing approval.
- **Import a car into Blender** (about 3 s), inside `execute_blender_code`:
  ```python
  import sys; sys.path.insert(0, r'D:\Claude\Claude-\blender\kn5-study')
  import blender_import as bi
  col, k = bi.load(r'D:\SteamLibrary\...\cars\ks_toyota_ae86\toyota_ae86.kn5', r'D:\Claude\_scratch_research\kn5_study\ae86', prefix='AE86')
  ```
  The car faces -Y. Hide `ksBrokenGlass` meshes and empties for clean views.
- **Cloud session:** the tools run anywhere with numpy and Pillow, but need the kn5 files. Those exist
  only on Nik's PC (`list_computer_folders` / `request_computer_folder` if available). Without them, work
  from `results/` and the reports.

## Quick commands
```bash
cd /d/Claude/Claude-/blender/kn5-study
C=D:/SteamLibrary/steamapps/common/assettocorsa/content/cars
python measure.py $C/<car> --out m.json && python compare_specs.py m.json specs.json   # dimensions vs spec
python survey.py s.json $C/<car>                                                       # construction scorecard
python silhouette.py $C/<carA> $C/<carB> out_prefix                                    # outline compare
python construction_sheet.py out.png $C/<car>                                          # 4 standard sections
```

## Key results to remember
- **Accuracy:** Kunos is within about 1 % of published specs. Targets for our cars: wheelbase ±10, length
  and width ±25, track ±20 mm. Height reads low because of AC ride height, so it is not a fair test.
- **Construction recipe:**
  - half model mirrored exactly
  - 89–94 % quads
  - paint shell 20–35k tris on an 18–27 mm grid
  - loops follow features, not stations
  - smooth shading, plain-average normals
- **Panel gaps:** about 5 mm returns at a 3–4 mm gap, with **dark AO baked into a white skin** (and the
  gloss map). The paint normal map is damage only.
- **Skin:** unfolded-car atlas, unique per side, 1024–2048².
- **Details:**
  - badges, chrome, lamp parts and grille bars are separate meshes
  - lens fluting is a normal map
  - alpha only for small mesh-like parts
- **Nova block-out:** dimensions exact. Construction fails:
  - 1.44M tris; 747k on the paint shell, about 30× Kunos
  - 5.5 mm grid
  - no skin UVs, LODs or standard dummies

## Open items / suggested next steps (not started; Nik said "not yet" to the first)
1. **Export the current section-built Nova body and grade it:** `measure.py`, `survey.py`,
   `construction_sheet.py`. Nik deferred this ("Not yet").
2. **Test `silhouette.py` against a real blueprint mask** (the Nova GA drawings or photos) instead of
   another kn5.
3. **AO-bake test:** bake AO into a white skin for one of our cars and compare in-game with the Kunos
   look.
4. **Apply the rules to the generators:**
   - feature-following loops instead of waterline-dominated rows
   - about 20 mm grid
   - shut lines as 5 mm returns plus baked AO
   - Kunos dummy names, LODs, two-layer glass
5. **Repo clean-up before sharing (waiting on Nik):** remove `nova-gte/export/map/sp_list.txt` (personal picture file names), the `knowledge/` memory sync, and the decrypted Kunos/mod car data (`escort-dtm/ref`, `sunbeam-lotus/refs`, `staging`). Commit author emails are visible too. Choices: a separate clean repo, or a history rewrite.
6. Phase-3 scratch files (wiki texts, per-car CSVs 14 MB): `D:\Claude\_scratch_research\kn5_study\p3\`.

## Gotchas found
- **Skinned kn5 meshes have a short trailer** (material, layer, lod in/out only). The older
  `ac-skin-generator/kn5.py` and wiper-toolkit readers would break on them; `kn5full.py` is fixed.
- **kn5 V is stored negated** (image row = 1 + v).
- **AC axes:** +x left, +y up, +z forward. Node matrices are row-vector, with translation in row 3.
- **Never assume ground is y = 0.** Use the tyre bottoms; the R5 mod is 156 mm below its origin.
- **Mirrors are often merged into door meshes,** so measure width below the beltline.
- **The fairness metric depends on mesh density.** Don't use it to rank models of different density.
- **Thin triangles (<5°) are normal** on pro models (about 23 %, from holding loops). Not a fault.
- **Don't commit** game textures, kn5 files or images of them. `.gitignore` already blocks
  `*.kn5 *.blend *.dds *.png`.
