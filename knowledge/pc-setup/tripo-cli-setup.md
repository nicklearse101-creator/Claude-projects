---
name: tripo-cli-setup
description: "Tripo CLI (npm tripo-cli, command `tripo`) installed globally 2026-10-13; Nik signs in himself with `tripo.cmd login`; PowerShell blocks the .ps1 shim"
metadata:
  node_type: memory
  type: reference
  originSessionId: 492adf9d-8819-4b64-a28b-e276d960f362
  modified: 2026-10-13T10:59:27.531Z
---

- `npm install -g tripo-cli` (v0.6.1, Tripo's own docs developers.tripo3d.com/en/docs/cli.md; repo
  vast-enterprise/Tripo-API-CLI) -> %APPDATA%\npm\tripo(.cmd/.ps1). Not `@tripo3d/cli` (a different Go-based
  package, also claims the `tripo` command - don't install both).
- Signed in 2026-10-13 from Nik's phone: I ran `tripo login --region ov --no-open` in the background, relayed the
  link + code, Nik approved; profile default, region ov, balance 0 credits then (new accounts can claim free credits
  in the console). Same flow works whenever he's away from the PC.
- Auth: Nik runs `tripo.cmd login` himself (browser approves, key lands in %USERPROFILE%\.tripo); never take the key
  in chat. Alternative TRIPO_API_KEY env var. Check with `tripo doctor` / `tripo whoami` (masked key, free).
- PowerShell execution policy is Undefined everywhere (= Restricted), so `tripo` in PowerShell hits the blocked
  tripo.ps1 shim: use `tripo.cmd`, cmd.exe or Git Bash. Changing the policy is Nik's call, not mine.
- Headless runs auto-enable `--yes` (no confirmation before spending credits): always ask Nik before `tripo make` /
  `generate` / `ai`. Same rule as Meshy ([[meshy-mcp-setup]]).
