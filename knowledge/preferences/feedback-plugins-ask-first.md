---
name: feedback-plugins-ask-first
description: "Use plugins (plugin skills/tools/MCP servers) only when actually needed, and ask Nik for confirmation before using one"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 06951a76-b443-4ded-b0bf-33a77e7c966d
  modified: 2026-10-05T12:10:10.761Z
---

Nik, 2026-10-05: "Only use plugins when needed, ask for confirmation."

**Why:** said right after the v2.6.0 Setup Coach build, where plugin process skills (superpowers brainstorming/writing-plans/executing-plans etc.) were invoked throughout, and the final message listed every unconnected plugin server. It narrows his global CLAUDE.md line "Use plugin skills and tools whenever they fit the task", and this later instruction wins.

**How to apply:** default to built-in tools (Read/Edit/Bash/PowerShell/Grep). Reach for a plugin skill, plugin tool or MCP server only when the task genuinely needs it, and ask Nik first (one line: which plugin and why). Don't list unconnected plugin servers unless the task depends on one. His other plugin rules still stand: keep all plugins installed, never suggest removing them, never install one without his yes. Related: [[setup-coach-project]].
