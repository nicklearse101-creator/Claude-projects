---
name: feedback-deploy-check-installed
description: "Before replacing an installed AC car with a project build, archive the installed copy and diff it - Nik edits cars in Content Manager between deploys"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 492adf9d-8819-4b64-a28b-e276d960f362
  modified: 2026-10-12T21:45:22.902Z
---

Before any deploy that replaces an installed car folder (Nova, Sunbeam, Escort...), copy the installed folder to a
clearly named BACKUP outside `content/cars` and list files that differ from the project build. Never rmtree it blind.

**Why:** 2026-10-12 I deployed the Nova with the old deploy.py (rmtree + copy); the installed `data/` had a change at
18:52 that was not in the project, and it was lost with no copy. Nik tweaks cars in Content Manager between deploys.

**How to apply:** the Nova's tools/deploy.py now does this automatically (export/deploy_backups/); for other
projects check mtimes / diff first. Follow [[feedback-backup-naming]] for the backup name. If something was lost,
say so plainly and own it.
