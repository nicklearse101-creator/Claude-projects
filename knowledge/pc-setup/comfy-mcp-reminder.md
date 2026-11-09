---
name: comfy-mcp-reminder
description: "REMIND NIK on Mon 2026-11-02 (first session after the restart): Comfy MCP is registered but there is no ComfyUI workspace yet - ask whether to install it on D:"
metadata:
  node_type: memory
  type: project
  originSessionId: 89a00829-bab3-450e-a4db-0a0bb133d892
  modified: 2026-10-29T10:07:17.573Z
---

**Remind Nik at the start of the first session on or after Monday 2026-11-02** (he asked on 2026-10-29, "remind me when
we restart Monday"). Say it once, briefly, then drop it if he waves it off.

State left on 2026-10-29:
- `comfy-cli` 1.23.0 and `comfy-mcp` 0.10.0 installed in Python314 (`...\Python314\Scripts\comfy.exe`, `comfy-mcp.exe`).
- `comfy-mcp` registered at user scope in `~/.claude.json` with `COMFY_BIN` set to the absolute `comfy.exe` path
  (backup: `~/.claude.json.BACKUP_before_comfy_mcp_2026-10-29`). MCP handshake tested OK; it targets
  `127.0.0.1:8188`, never Comfy Cloud.
- **No ComfyUI workspace exists** (none on C: or D:), so nothing to drive yet.

**Decisions to put to Nik:**
1. Install one on D: (`comfy --workspace D:\ComfyUI install`)? C: has only ~3.5 GB free, D: ~100 GB.
2. GPU is an AMD RX 6700 XT (Windows reports 4 GB; the card is believed to be 12 GB - unconfirmed). Docs suggest 8-24 GB
   for images only, video needs 24+. On Windows AMD means DirectML or ROCm - comfy-cli can pick wrongly.
3. System Python is 3.14; PyTorch support for it is unverified, so the install may need an older Python.
4. Honest value: for the Nova it is low - generated images are not evidence and it does not help the surface work.

After install + app restart: `comfy launch` (leave running), then call `server_info`.
Docs: https://docs.comfy.org/agent-tools/mcp.md
Related: [[pc-drive-space]], [[nova-gte-project]].
