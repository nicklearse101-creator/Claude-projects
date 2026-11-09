---
name: pc-drive-space
description: "Nik's C: drive is full (2 GB free of 223 GB, 2026-09-28) - put work, temp output and copies on D:; plugins\data junctioned to D:\ClaudeData (2026-10-26)"
metadata:
  node_type: memory
  type: user
  originSessionId: f778f6e8-659c-4806-87b8-4260adc4c47b
  modified: 2026-09-28T18:29:42.654Z
---

C: is nearly full (223 GB, ~2 GB free on 2026-09-28) and Nik plans to clean it up. D: (932 GB, ~105 GB free) is
fine to use - put project files, large temp output, backups and copies on D:, not C:.

Offsite backup of projects (e.g. `D:\Claude\talbot_sunbeam_lotus`, ~3.3 GB incl. archive): Nik may set up a Google
Drive connector for it later ("it can wait") - don't upload anything until he has and says so. Note the Sunbeam
project contains other mod authors' assets (personal use) - keep any cloud copy private.
Related: [[talbot-sunbeam-lotus-ac-mod]].

2026-10-26: `C:\Users\nickl\.claude\plugins\data` is now a **junction to `D:\ClaudeData\plugins\data`** (Nik asked to move
it and send new plugin data there; .claude is outside AppData so the junction resolves). Old copy left as
`plugins\data_BACKUP_before_move_to_D` (832 KB) until Nik says to delete it. The bigger plugin folders on C: are
`plugins\cache` (47 MB) and `plugins\marketplaces` (15 MB) - not moved.
