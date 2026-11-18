---
name: feedback-sonnet-for-research
description: "Research/search subagents run on Sonnet (model \"sonnet\") to save cost; Opus keeps the judgement and the code"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 72978f4c-01cc-4374-ab94-5183fa936984
  modified: 2026-11-18T00:15:56.027Z
---

Spawn research, web-search, read-and-summarise and codebase-search subagents with `model: "sonnet"` (Agent tool), including the agents the deep-research skill launches. Keep Opus (myself) for deciding how findings apply, geometry/fitting judgement and writing the code.

**Why:** Nik 2026-11-18: Sonnet is more cost effective for research agents; gathering is retrieval work Sonnet does well.

**How to apply:** pass `model: "sonnet"` on every research/explore Agent call unless a task truly needs deep reasoning (then say why). Still lean on research per [[feedback-use-research-tool]].
