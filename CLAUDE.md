# Saving work

This repository is where all work from Claude sessions is saved (cloud
sessions, Claude Code on the PC, Remote Control and Cowork).

- Save work here as you go: commit after each meaningful step and push to
  GitHub straight away. Don't wait until the end of the session.
- Before ending a turn, check `git status`. If anything is uncommitted or
  unpushed, commit and push it.
- Use short, plain commit messages that say what was made or changed.
- Keep each project in its own top-level folder (e.g. `blender/`,
  `anti-cheat/`, `setup-coach/`) so work from different sessions doesn't
  get mixed up.
- Don't commit files over 100 MB (GitHub rejects them), passwords, API keys
  or other secrets. Large Blender or game files should be mentioned to the
  user instead of committed.
- If a push fails, say so plainly; the work stays committed locally until
  it can be pushed.
- A safety-net hook (`.claude/hooks/autosave.sh`) also commits and pushes
  anything left over at the end of each turn, as "Auto-save" commits. It
  is a backup, not a replacement for proper commits.
- `main` is the branch to save to. If a session is given its own branch
  (cloud sessions are), work there and say so; it can be merged into
  `main` afterwards.

# Public copy (claude-projects)

This repo is **private**. A cleaned **public** copy lives at
github.com/nicklearse101-creator/claude-projects (local clone `D:\Claude\claude-projects`).

- Keep working and saving here as normal. Never commit directly to the public repo.
- After meaningful changes (end of a project step, or when Nik wants to show something), refresh it:
  `python tools/publish_public.py` (use `--dry-run` to check first).
- The script publishes only committed files, removes emails and race-server/Discord addresses,
  leaves out decrypted Kunos/mod car data, and refuses to push if anything sensitive remains.
  New game-data folders must be added to its EXCLUDE list before publishing.
