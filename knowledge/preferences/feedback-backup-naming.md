---
name: feedback-backup-naming
description: "Name backups/copies so they can never look newer than the live version; don't blame Nik for picking the wrong one"
metadata:
  node_type: memory
  type: feedback
  originSessionId: f778f6e8-659c-4806-87b8-4260adc4c47b
  modified: 2026-09-28T18:14:39.088Z
---

When making a backup copy of something Nik uses (cars, builds, files), label it unmistakably as a BACKUP and put
the version in the LIVE item's name too. Never give a backup a bare version suffix next to an unnumbered live item.

**Why:** 2026-09-28 I backed up the Sunbeam car as `talbot_sunbeam_lotus_81_works_v2` next to the live
`talbot_sunbeam_lotus_81_works`; "_v2" looked like the newest version, Nik tested it, and I then told him he'd driven
the backup - he pointed out (rightly, annoyed) "you're the one who named them wrongly, not me".

**How to apply:** backups as `<id>_backup_vN` / "... BACKUP vN - what it is"; live item shows its current version
(e.g. "Talbot Sunbeam Lotus Rally v3"). When a mix-up happens, own the cause first rather than implying user error.
Related: [[talbot-sunbeam-lotus-ac-mod]].
