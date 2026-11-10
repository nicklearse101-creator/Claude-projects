---
name: feedback-no-c-drive-scratch
description: "NEVER write temp/scratch files to C: - not even the Claude app's own scratchpad (AppData\\Local\\Temp\\claude); use D:\\ClaudeData\\tmp, and tell subagents the same"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 3eac5946-e454-4696-9cbe-8aa69aa524d5
  modified: 2026-11-10T10:48:23.749Z
---

Nothing Claude makes may be saved on C:, including temporary files. The Claude app's session "scratchpad"
(C:\Users\nickl\AppData\Local\Temp\claude\...\scratchpad) IS on C: - do not use it. Use D:\ClaudeData\tmp\<session or task>
for scratch scripts, clones, test outputs; D:\Claude\_scratch_research for research work files.

**Why:** C: is nearly full (5 GB free of 222 GB, see [[pc-drive-space]]). On 2026-11-10 Nik found 2.4 GB of Claude temp
files there (skin-generator .dds tests 1 GB, a GitHub-search agent's repo clones 0.28 GB, ...) and was furious:
"NOTHING EVER GETS SAVED TO C DRIVE!!!!!! EVER!!!"

**How to apply:** every scratch path, every subagent prompt (say "work only on D:, scratch in D:\ClaudeData\tmp"),
every git clone and test output goes to D:. Before ending a session, check C:\Users\nickl\AppData\Local\Temp\claude for
anything this session left and clear it.
