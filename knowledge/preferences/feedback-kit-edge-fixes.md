---
name: feedback-kit-edge-fixes
description: "Nik expects small kit-fit fixes (proud edge, tip) to be quick; diagnose geometry first, don't trial-and-error rebuilds"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c27446ac-194b-4ace-8388-a9b2ff39d003
  modified: 2026-11-23T08:10:23.574Z
---

23 Nov 2026, Escort v42-v43: a "slightly proud" arch edge + tip took ~10 full rebuild/render cycles of guessing (flush snap, subdivide+press, relax, top-cut...). Nik: "I thought this would be a 2 minute job".

**Why:** each guess cost a 1-2 min rebuild plus renders, and several made it worse; the real causes (one spike vertex on the trimmed edge; arch cut-out removing wing faces visible from above) were found only by printing vertex gaps and toggling parts.

**How to apply:** for a local defect, first measure it (print the vertices/gaps in that small box, toggle candidate parts in one render), then make one targeted change. What finally worked for kit edges on a body: surface-distance blend (gap x smoothstep over ~7 cm from the edge), 3 mm trim, spike-only edge relax, light smooth, no-penetration pass; body cut-out only where hidden from several ray directions. See escort-dtm docs/V37_KADETT_KIT.md v43. Related: [[escort-mk2-dtm-project]], [[feedback-judge-by-eye]].
