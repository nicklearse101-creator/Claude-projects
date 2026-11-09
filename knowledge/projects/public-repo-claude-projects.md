---
name: public-repo-claude-projects
description: Public cleaned mirror of the private Claude- repo = github.com/nicklearse101-creator/claude-projects; refresh with tools/publish_public.py (2026-11-09)
metadata:
  type: project
---

Nik wanted to share his work, so on 2026-11-09 we made a public copy of the private Claude- repo, called `claude-projects`. It has a fresh history, so the old commits are not included. Local clone: `D:\Claude\claude-projects`.

**Why:** the private repo's history contains his email, the race-server/Discord addresses and decrypted Kunos/mod car data.
Nik asked to hide the email and the server info only. He chose to keep everything else, including the knowledge/ notes and the Pictures file list `nova-gte/export/map/sp_list.txt`. He agreed to leave out the game data.

**How to apply:**
- Keep saving to Claude- as normal.
- Refresh the public copy with `python tools/publish_public.py` (`--dry-run` first) after meaningful steps or when Nik wants to show something.
- Never commit to claude-projects by hand.
- Add any new decrypted game-data folder to the EXCLUDE list in the script.

Related: [[knowledge-sync-to-github]], [[blender-work-kn5-study]].
