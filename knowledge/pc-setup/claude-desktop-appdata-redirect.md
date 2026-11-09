---
name: claude-desktop-appdata-redirect
description: Claude desktop is a Store (MSIX) app - NEW AppData folders created from its shells are redirected to a private copy where junctions break; plugin MCP fixes of 2026-09-27
metadata:
  node_type: memory
  type: reference
  originSessionId: 06951a76-b443-4ded-b0bf-33a77e7c966d
  modified: 2026-09-27T10:28:11.707Z
---

The Claude desktop app is an MSIX package (`C:\Program Files\WindowsApps\Claude_*`), and Claude Code plus every shell/MCP server it starts inherit its package context. Windows redirects **new** top-level folders they create under `%APPDATA%` / `%LOCALAPPDATA%` into `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\...` (folders that already existed, like `%APPDATA%\npm` or `Python314\Scripts`, are written for real). Plain files work through the redirect; **junctions/symlinks inside it don't resolve** ("path not found" even though the target lists fine).

Hit on 2026-09-27: uv's managed Python (`%APPDATA%\uv\python`, minor-version junction) broke the browser-use plugin. Fix, in `~/.claude/settings.json` `env`: `UV_PYTHON_INSTALL_DIR=C:\Users\nickl\.local\share\uv\python`, `UV_CACHE_DIR=C:\Users\nickl\.cache\uv`, plus `MCP_TIMEOUT=90000` (engine default 30000; browser-use and Desktop Commander fetch `@latest` each start, cold starts measured 40 s / 28 s). uv 0.12.19 installed via pip into Python314\Scripts, Bun 1.4.2 via `npm -g` (both on the app's PATH, so no app restart). A 60 MB unusable first download is left in the LocalCache `Roaming\uv` copy.

**How to apply:** when a tool run from Claude on this PC fails with a path that "exists but can't be found", check for a junction/symlink under a redirected AppData folder and move the tool's data dir outside AppData. Test a server's startup with an MCP `initialize` handshake rather than trusting the session's connect status. Discord plugin still needs the user's bot token in `~/.claude/channels/discord/.env` (LF endings - the server splits on `\n` only). Related: [[setup-coach-project]].
