---
name: meshy-mcp-setup
description: "Meshy MCP server (@meshy-ai/meshy-mcp-server) added to Claude Code user scope 2026-10-13; key lives in ~/.claude/settings.json env, set by Nik's own script; bundled claude CLI path"
metadata:
  node_type: memory
  type: reference
  originSessionId: 492adf9d-8819-4b64-a28b-e276d960f362
  modified: 2026-10-13T10:45:21.847Z
---

- Meshy MCP added 2026-10-13 at user scope in ~/.claude.json: `cmd /c npx -y @meshy-ai/meshy-mcp-server` (v0.6.4,
  repo meshy-dev/meshy-mcp-server, 28 tools, starts in ~3 s). No key in that config: MESHY_API_KEY is read from
  ~/.claude/settings.json `env` (inherited by MCP servers, like the UV_* fixes in [[claude-desktop-appdata-redirect]]).
- Nik sets the key himself: `powershell -ExecutionPolicy Bypass -File "$HOME\.claude\scripts\set-meshy-key.ps1"`
  (hidden prompt -> set-meshy-key.js writes env.MESHY_API_KEY, keeps settings.json.BACKUP_before_meshy_key). Never
  ask Nik to paste the key into chat. Free check that the key works: meshy_check_balance. Generation costs credits
  (Pro plan needed) - ask before any paid call.
- No `claude` on PATH here: the desktop app's CLI is `%APPDATA%\Claude\claude-code\<version>\<hash>\claude.exe`
  (2.1.295 on 2026-10-13); use it for `claude mcp add-json --scope user ...` / `mcp get` / `mcp remove`.
