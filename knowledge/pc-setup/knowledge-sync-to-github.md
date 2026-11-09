---
name: knowledge-sync-to-github
description: "memory notes auto-sync to the Claude- repo's knowledge/ folder by a global Stop hook (2026-11-06)"
metadata:
  node_type: memory
  type: reference
  originSessionId: 1a2d51ff-a8f8-496e-aa87-2daa1632b841
  modified: 2026-11-06T18:00:10.813Z
---

Nik asked (2026-11-06) for all confirmed knowledge to live in the private GitHub repo
nicklearse101-creator/Claude- (local D:\Claude\Claude-), kept in sync.

- `tools/sync-knowledge/sync_memory.sh` copies this memory folder into `knowledge/`
  (preferences / projects / pc-setup / racing), deletes notes removed here, copies
  ~/.claude/CLAUDE.md as `preferences/global-CLAUDE.md`, rebuilds `knowledge/README.md`
  from MEMORY.md, then commits + pushes `knowledge/` only.
- Run by an async global Stop hook in ~/.claude/settings.json at the end of every turn.
- New notes are filed by frontmatter type; files matching API-key/token patterns are skipped
  (warning shown). ~/.claude/settings.json itself holds the Meshy key - never copy it to the repo.

**How to apply:** just keep memory notes accurate; no manual copying needed. If Nik says the
repo is stale, run the script by hand and check its systemMessage.
