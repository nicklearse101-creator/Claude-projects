---
name: feedback-no-c-drive-scratch
description: "NEVER write temp/scratch files to C: - not even the Claude app's own scratchpad (AppData\\Local\\Temp\\claude); use D:\\ClaudeData\\tmp, and tell subagents the same"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3eac5946-e454-4696-9cbe-8aa69aa524d5
  modified: 2026-11-12T23:06:12.562Z
---

Nothing Claude makes may be saved on C:, including temporary files. The Claude app's session "scratchpad"
(C:\Users\nickl\AppData\Local\Temp\claude\...\scratchpad) IS on C: - do not use it. Use D:\ClaudeData\tmp\<session or task>
for scratch scripts, clones, test outputs; D:\Claude\_scratch_research for research work files.

**Why:** C: is nearly full (5 GB free of 222 GB, see [[pc-drive-space]]). On 2026-11-10 Nik found 2.4 GB of Claude temp
files there (skin-generator .dds tests 1 GB, a GitHub-search agent's repo clones 0.28 GB, ...) and was furious:
"NOTHING EVER GETS SAVED TO C DRIVE!!!!!! EVER!!!"

**12 Nov 2026 update:** Nik said the old "never touch my real install" rule was a bad-mood rule - I may keep his apps up to
date myself (standing permission). But installs go on D: ("no not C ... D is preferred"). Ratty's4Skin Generator lives in
`D:\Rattys4SkinGenerator` (logos/settings in its `data` folder, desktop shortcut points there, no Installed-apps registry
entry). To update it: back up to `D:\Rattys4SkinGenerator_BACKUP_v<old>`, run `installer.install_files('build/app.zip', ...)`
(replaces the program, never `data`), restore the old uninstall.ps1, check data hashes unchanged, run `--selftest`. Don't
rewrite shortcuts or the registry (they're on C:).

**How to apply:** every scratch path, every subagent prompt (say "work only on D:, scratch in D:\ClaudeData\tmp"),
every git clone and test output goes to D:. Before ending a session, check C:\Users\nickl\AppData\Local\Temp\claude for
anything this session left and clear it.
