---
name: blender-skills-cc-blender-skill
description: Six Blender skills from RobLe3/cc-blender-skill installed in ~/.claude/skills (2026-10-12); they call mcp__blender__* which is NOT configured - Nik decides; world-reset default clashes with the car blends
metadata:
  node_type: memory
  type: reference
  originSessionId: f778f6e8-659c-4806-87b8-4260adc4c47b
  modified: 2026-10-12T11:46:00.862Z
---

Installed 2026-10-12 at Nik's request (copies, not links), repo commit 11016c9a5847897491dde935c346571bd7548e3d (v1.3.0):
`C:\Users\nickl\.claude\skills\` text-to-blender, blender-pro-workflow, blender-modeling, blender-materials,
blender-uv-texturing, blender-export. Nothing else from the repo; no Python packages.

- They name tools `mcp__blender__execute_blender_code` etc. (needs an MCP server named exactly `blender`).
  `claude mcp list` (CLI is NOT on PATH - bundled at
  `%APPDATA%\Claude\claude-code\<ver>\<hash>\claude.exe`) showed no servers. The Blender MCP these sessions
  actually use is the PLUGIN one, tools `mcp__plugin_blender-mcp_blender__*` (addon blender_mcp.py in Blender 5.2,
  port 9876). Nik will decide whether to run `claude mcp add blender uvx blender-mcp` - don't add it unasked.
- All six list unscoped `Bash` in `allowed-tools` (used only for `ls` checks of output files).
- text-to-blender ALWAYS resets the scene world (deletes all world nodes) and switches the viewport to Material
  Preview; recipes write to `/tmp/...`. On the Sunbeam/Escort car blends that would wipe their world setup, and
  Material Preview + screenshots has crashed Blender before ([[talbot-sunbeam-lotus-ac-mod]]) - don't follow those
  defaults on the car projects ([[escort-mk2-dtm-project]]).
- It routes to skills NOT installed (blender-lighting, -cameras, -rendering, -animation, wireframe-to-3d,
  blender-skill-harmonizer, quality-refinement-autoloop, reference-look-calibration, closed-surface-uv-coverage,
  reference-to-3d) and to missing reference files (intent-routing.md, code-execution-rules.md).
