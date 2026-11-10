---
name: freecad-ai-mcp-setup
description: "freecad-ai add-on (ghbalf, v0.33.0-alpha) installed 2026-11-10; FreeCAD MCP server \"freecad\" at http://127.0.0.1:3000/mcp, user scope; start FreeCAD via the launcher first"
metadata:
  node_type: memory
  type: reference
  originSessionId: 86b9308a-049a-4fcb-aa67-de99f6889d31
  modified: 2026-11-10T10:43:18.145Z
---

- Nik uses FreeCAD 1.1 at `D:\FreeCAD` (bin\freecad.exe). User Mod dir `%APPDATA%\FreeCAD\v1-1\Mod` (also has CurvesWB).
- Add-on cloned to `D:\FreeCAD-addons\freecad-ai` (git, master 08d637d), junctioned into the Mod dir as `freecad-ai`.
- MCP: Claude Code user-scope server `freecad`, HTTP `http://127.0.0.1:3000/mcp`, no auth token (loopback only).
  It only answers while FreeCAD runs with `mcp_server_http.py`: `D:\FreeCAD-addons\Start FreeCAD with AI MCP.bat`
  (or the add-on's "MCP Server" toolbar button). ~61 tools: sketch/pad/pocket/loft/sweep, describe_model, measure,
  list_faces/edges, section_object, named undo, capture_viewport, export_model (STEP/STL), execute_code.
- Registered with the bundled CLI (no `claude` on PATH): `%LOCALAPPDATA%\Claude-Data\claude_*\claude-code\<ver>\<hash>\claude.exe`
  (2.1.317 on 2026-11-10; the [[meshy-mcp-setup]] path is outdated). Sessions started before 2026-11-10 10:50 need a restart to see the tools.
- Ideas worth porting to the Blender tools: see [[blender-work-kn5-study]].
