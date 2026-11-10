# Knowledge base

Confirmed lessons and project facts from Nik's Claude sessions, kept in sync
automatically from Claude's memory notes (`~/.claude/projects/D--Claude/memory/`)
by `tools/sync-knowledge/sync_memory.sh` at the end of every Claude turn.
Each note is one fact or lesson; **Why** / **How to apply** lines explain it.
Project notes hold dated status — newest entries are at the top of each note.

- `preferences/` — how Nik wants work done (lessons learned the hard way), plus `global-CLAUDE.md`
- `projects/` — Setup Coach, Sunbeam, Escort DTM, Nova GTE, physics watchdog
- `pc-setup/` — PC quirks and tool installs (drive space, AppData redirect, Meshy, Tripo, Blender skills)
- `racing/` — Ratty's Racing championship and race server

Other confirmed write-ups in this repo: `tools/ac-wiper/` (wiper report + proven toolkit),
`docs/Blender_3D_Modelling_Guide.md`, `docs/reports/`.

## Index
- [NEVER write to C:, not even temp](preferences/feedback-no-c-drive-scratch.md) — the app's scratchpad is on C:; use D:/ClaudeData/tmp, tell subagents too (Nik furious 2026-11-10)
- [Name: Nik](preferences/user-name-nik.md) — spell the user's name NIK, never "Nick"
- [Plugins: only when needed, ask first](preferences/feedback-plugins-ask-first.md) — use plugin skills/tools/MCP only when needed and confirm with Nik before using one (2026-10-05)
- [Content Manager: use the taskbar button](preferences/feedback-content-manager-taskbar.md) — never open_application("Content Manager") (starts the AC game); click the red CM taskbar icon
- [Setup Coach project](projects/setup-coach-project.md) — install paths, dev-source-of-truth filename/version gotcha, dev tooling location; git repo `D:\Claude\setupcoach-tools` + release routine since v2.5.0; current v2.6.0 (bottoming chains, ride height to the floor, 2026-10-05); never `sed -i` the CRLF app file
- [Ratty's Racing Dacia Championship](racing/rattys-racing-dacia-championship.md) — user races as Nicklearse101, real-world context for Setup Coach's Dacia work
- [RATBOY's race server](racing/ratboy-race-server.md) — [race server], online Thu/Sun 19:30-22:00, where race-night results live
- [Claude desktop AppData redirect](pc-setup/claude-desktop-appdata-redirect.md) — Store-app redirect breaks junctions in new AppData folders; uv/Bun/MCP_TIMEOUT fixes for plugin servers (2026-09-27)
- [Talbot Sunbeam Lotus AC mod](projects/talbot-sunbeam-lotus-ac-mod.md) — "the Sunbeam": 1981 works rally conversion of the stock Sunbeam mod; physics v7 live 30 Sep (double-wishbone rear, not historical); BACKUP v6 = real four-link axle = Nik's MAIN model, got the 6 Oct model update (floor-anchored belts, splitters, Escort 4-cyl + Lotus badge; install_models.py); README + git repo
- [Escort Mk2 DTM project](projects/escort-mk2-dtm-project.md) — ford_escort_mk2_tuned DTM: v25 model (V8, Mk2 mirrors, treadplate); v26 live 13 Oct = physics rebuilt on the Kunos Escort Mk1 (Sunbeam recipe; model untouched, BACKUP v25 car = the odd v19/DTM hybrid Nik had); repo D:\Claude\escort_mk2_dtm, uncommitted
- [PC drive space](pc-setup/pc-drive-space.md) — C: full (2 GB free), use D: for work/copies; ~/.claude/plugins/data is a junction to D:\ClaudeData (2026-10-26)
- [Share across projects](preferences/feedback-share-across-projects.md) — carry findings between watchdog / Sunbeam / Setup Coach; digging pre-authorised ("we want the best from everything")
- [Backup naming](preferences/feedback-backup-naming.md) — backups must say BACKUP and never look newer than the live item; live item carries its version; own mix-ups
- [Video tools on Nik's PC](pc-setup/video-tools-on-nicks-pc.md) — no ffmpeg; WinRT MediaComposition via PowerShell reads/writes MP4, helpers in Downloads\BozzaRacingStudios_intro_source
- [ac-physics-watchdog project](projects/ac-physics-watchdog-project.md) — general cheat-detection tool for Ratty's Racing (not just Dacia); git repo since 2026-09-25 (autocrlf off); one-button daemon built 2026-09-22, gotchas, Server Manager API facts, first race night on RATBOY's PC 2026-09-24 (lag noise fixed same night); race 2 of 24 Sep's lap-time standout was a corner cut, physics clean; power + grip checks (each car vs its own files) built 2026-09-29, then Alien V2/Predator checks (bursts, braking vs field/history, teleport onto a car; e7d7b58); gear stints + teleport-by-path committed 67f48fd; 5 Oct lost-updates fix 6fc6c7c (daemon/tally/zip not redone), gearing check redesign planned, not started (RESUME HERE at the top)
- [Sunbeam +10% watchdog test](projects/sunbeam-plus10-watchdog-test.md) — DRIVEN 29 Sep: measured x1.12-1.13 exactly, NOT flagged (Sunbeam honestly at 0.82 of its ceiling) - needs power vs field/history
- [Alien cheat analysis](projects/alien-cheat-analysis.md) — AC cheats vs physics: Alien v1 hooks, Alien V2 + Predator (same DLL, CSP Lua physics API), No Hesi Cheats, ALLOW_APPS tracks on Nik's PC; watchdog coverage + gaps; never install/download cheat binaries
- [Watchdog scope: physics only](projects/watchdog-scope-physics-only.md) — catch physics manipulation, nothing else; no shortcut/track-limit features, lap-time flags judged on physics
- [Sunbeam ideas reminder](projects/sunbeam-ideas-reminder.md) — REMIND NIK 2026-09-29: spare wheel, pedals, engine bay, shift light, belts, track width
- [Screenshots: one per finished section](preferences/feedback-screenshots-one-per-section.md) — Nik wants one final image per section, not progress shots (2026-10-06)
- [Blender skills (cc-blender-skill)](pc-setup/blender-skills-cc-blender-skill.md) — 6 skills in ~/.claude/skills (2026-10-12); call mcp__blender__* (not configured); world-reset default clashes with car blends
- [Nova GTE project](projects/nova-gte-project.md) — vauxhall_nova_gte_1989 AC car; body rebuilt by `sh tools/gen/rebuild_body.sh`; 2026-10-27 fixed a 30 mm blueprint-vs-photo frame error + a stale camera solve, traced the side windows, built the rear end (bumper, lamps, tailgate); NEXT = mirrors, shut lines, wheels, glass
- [Meshy MCP setup](pc-setup/meshy-mcp-setup.md) — user-scope server, key in settings.json env via Nik's own script, bundled claude.exe path (2026-10-13)
- [Tripo CLI setup](pc-setup/tripo-cli-setup.md) — npm tripo-cli 0.6.1, Nik logs in with `tripo.cmd login`, ask before spending credits (2026-10-13)
- [Deploy: archive installed car first](preferences/feedback-deploy-check-installed.md) — never rmtree an installed car blind; Nik edits in CM between deploys (lost a Nova data change 12 Oct)
- [Use the research tool](preferences/feedback-use-research-tool.md) — Nik 2026-10-19: run the deep-research skill on how a problem is properly solved before tackling it
- [Blender: use plugins + skills](preferences/feedback-blender-use-plugins-skills.md) — Nik 2026-10-19: always load the blender-* skills and use blender-mcp tools for Blender work (standing approval)
- [Judge photo matches by eye](preferences/feedback-judge-by-eye.md) — side-by-side vs photo decides, not projected numbers (matched cameras can be locally wrong); check close-up in Blender before moving on
- [Nova: compare to the pictures](preferences/feedback-nova-compare-to-pictures.md) — THE method: plain grey model vs Nik's pictures (grey_studio side/front/rear), same scale, close crops, by eye, one area at a time; no smoothing/pipeline 'non-fixes'
- [Check blueprint AND photo](preferences/feedback-check-blueprint-and-photo.md) — Nik 2026-10-26: cross-check traced drawings against the photos through the solved camera before trusting either
- [Concise, report at end of turn](preferences/feedback-concise-end-of-turn.md) — short messages; at turn end: what was done + a picture
- [Nova: shell only](preferences/feedback-nova-shell-only.md) — Meshy route: ONLY make the shell; never recolour/paint/retexture or export to AC unless Nik asks
- [Comfy MCP reminder](pc-setup/comfy-mcp-reminder.md) — REMIND NIK Mon 2026-11-02: Comfy MCP registered, no ComfyUI workspace yet; ask whether to install on D: (GPU = AMD RX 6700 XT, Python 3.14)
- [Knowledge sync to GitHub](pc-setup/knowledge-sync-to-github.md) — memory auto-copies to Claude- repo knowledge/ via global Stop hook (2026-11-06)
- [Ratty's4Skin Generator](projects/ac-skin-generator-project.md) - no-AI livery app for any AC car + installer (D:/Claude/Claude-/ac-skin-generator); v1.5.0 10 Nov = decals through visible triangles, placement check, edit decals on the preview, fonts, Talbot fix; awaiting Nik's in-game check; test with tests/nik_test.py
- [3D texel preview technique](pc-setup/technique-3d-texel-preview.md) - see/render cars from Python (kn5 reader, texel->3D map, quick ortho render); reuse for Blender work (UV/texture checks, photo comparisons)
- [Blender work project / kn5 study](projects/blender-work-kn5-study.md) — Claude- repo blender/ (2026-11-09): 112 AC cars (incl. single-seaters) + Nova reverse-engineered, spec dimension checks, silhouette compare, Kunos target numbers, kn5 tools; WORKING replica method = PANEL_FIT_TECHNIQUE.md (fitted+trimmed B-spline panels, crisp AE86 door 2026-11-09); 2026-11-10 door 87.6 % / 99.6 %, front wing 72.4 % / 99.5 % within 1 / 3 mm (regress.sh); rear quarter built 2026-11-10 night (78.2 % / 96.8 %); next thin-strip builder, then roof
- [Public repo claude-projects](projects/public-repo-claude-projects.md) — cleaned public mirror of Claude-; auto-updated by a Stop hook (publish_public.py --auto), never commit to it directly
- [FreeCAD AI MCP](pc-setup/freecad-ai-mcp-setup.md) — freecad-ai add-on installed 2026-11-10; MCP `freecad` at 127.0.0.1:3000/mcp, start FreeCAD via D:\FreeCAD-addons launcher first
- [Steward app](projects/steward-app-project.md) — AC incident-review app for Ratty's Racing; plan only (steward-app/PLAN.md), 5 open questions for Nik
