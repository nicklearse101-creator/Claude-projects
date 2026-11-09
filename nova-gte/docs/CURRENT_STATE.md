# Current state - Vauxhall Nova GTE (AC mod), audited 2026-11-02

Read-only Phase 0 audit (AI_Automotive_Modelling_Master_Plan, section 4). No geometry or existing file was changed.
Labels: VERIFIED = checked directly this session. FILE = read from a repo document, not re-checked.
ESTIMATE / HYPOTHESIS as stated. OTHER-SESSION = claim from an earlier session note.

## 1. Source of truth

- Active repo: `D:\Claude\vauxhall_nova_gte_1989` (VERIFIED: has .git, newest files, CLAUDE.md names it as workspace root).
- `D:\Claude\nova-gte` is the superseded 1990 scaffold (VERIFIED: no .git, older files, CLAUDE.md says "workspace root: not decided yet"). Leave in place; do not work in it.
- Git (VERIFIED): branch `master`, HEAD `0cac070`, no stashes. Working tree clean except 4 untracked docs
  (ASSESSMENT_2026-11-02, NEXT_WEEK, SESSION_KNOWLEDGE_2026-10-26_to_29, STATUS_FOR_CHAT).
- Rollback point (VERIFIED, created this session): annotated tag `checkpoint-2026-11-02-audit-baseline` on `0cac070`.

## 2. Which body is authoritative

- Approved route (FILE: CLAUDE.md, REPLICA_PLAN.md, DECISIONS 2026-10-27 (16)-(21)): FreeCAD character-line network -> NURBS surfaces -> panels.
- What actually exists of that route (VERIFIED): `cad/nova_lines_v2.FCStd` (163 KB) and `blender/data/cad/lines_v2_fit.json`
  hold 96 fitted curves. No surfaces, no panels, no zebra tool (`tools/cad/zebra.py` does not exist).
- The numpy body `blender/nova_proc.blend` (27 Oct 14:32) is the only complete body. Per DECISIONS (16) it is comparison-only,
  except glass. Do not patch it further.
- Conclusion: the FreeCAD route is the primary route but is at wire-frame stage. Nothing surfaced, exported or driven.

## 3. Assetto Corsa package

- Installed: `...\content\cars\vauxhall_nova_gte_1989\vauxhall_nova_gte_1989.kn5`, 46.7 MB, written 20 Oct (VERIFIED size/date).
- FILE: it is the Phase 1 block-out / old reference-model build, ~1.3 M triangles (triangle count not re-checked). Physics `data/` is the Phase 1 skeleton.
- Repo copy: `car/vauxhall_nova_gte_1989/` (39 files, 46.8 MB). Deploy only via `tools/deploy.py` (archives the installed copy).

## 4. Tools (VERIFIED unless noted)

| Item | Result |
|---|---|
| FreeCAD | 1.1.4 (rev 20260928) at `D:\FreeCAD\bin\freecadcmd.exe`; Curves workbench: FILE (installed per notes) |
| Blender | "Blender 5.2" install folder; notes say 5.2.1 (patch level not checked) |
| Project Python | `.venv` Python 3.13.13, numpy 2.5.4, scipy 1.18.1, opencv 5.0.0 |
| Git | works; GitKraken and Desktop Commander plugins present on the PC |
| Blender MCP | NOT tested this session. FILE: add-on protocol 11 vs 15 expected (NEXT_WEEK) |
| ComfyUI | not examined; no workflow needs it yet |

## 5. Hardware (VERIFIED)

Ryzen 5 PRO 4650G, 63.8 GB RAM, Radeon RX 6700 XT with 12 GB VRAM (registry value; resolves the "VRAM unverified" note).
`D:` free space ~96 GB of ~1 TB (`export/` alone is 2.5 GB, git-ignored).

## 6. Repo inventory (VERIFIED sizes)

blender 949 MB/177 files; export 2,540 MB/1,565; reference 546 MB/146 (photos git-ignored); car 47 MB/39; tools 0.9 MB/159;
docs 0.7 MB/15; cad 4 files; data 5 files. 376 tracked files, including ~27 .blend files (17 `BACKUP_*`, several Meshy-era).

## 7. Measurement foundation (FILE unless noted)

- One world frame: car faces -Y, Z up, origin on ground midway between axles, model z = photo z + 0.0193.
- Frame file is at `reference/views/frame.json` (VERIFIED; docs wrongly cite `tools/cad/frame.json`).
- 7 solved cameras, 34 triangulated points, robust re-solve. Median mark error 2.5-7.0 mm by photo set. Not re-run today.
- Not reliable (do not build to): DG_RT, DG_RB, MIR, BON_F, PNL_B, DSR_B.
- Curve fairness (VERIFIED, recomputed from `fairness_v2fair.json`): 96 curves, median 3.25 wiggles/m, median wobble 1.85 mm, max 11.4 mm.
  See PROJECT_AUDIT section 3 for the triage.
