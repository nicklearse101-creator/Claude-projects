# My preferences (every project)

- **Plugins:** Keep only the plugins I actually use enabled. Unused skills and plugins can be cleared up or disabled (I asked for this on 2026-10-05).
- Use plugin skills and tools only when the task actually needs them, and ask me for confirmation first (which plugin and why). If a plugin the task needs has a connection that needs signing in or fails to connect, tell me rather than silently working around it.
- When a task would go better with a plugin I don't have, suggest it (search my plugin catalog and show the install card). Never install one without my yes.

# Assetto Corsa car modding

- Before car-mod work (wipers, animations, kn5/ksanim), read `D:\AC_Wiper_Project\` (also copied in `D:\SteamLibrary\steamapps\common\assettocorsa\Claude outputs\`) — start with `AC_Wiper_Project_Report.md` (successes, failures, lessons) and `ac_wiper_toolkit\TOOLS.md` (the proven tools, also zipped as `ac_wiper_toolkit.zip`). Keep wipers one solid piece; the user sets sweep angles after checking in-game.

# GitHub saving

- Save all work to the Claude- repository at D:\Claude\Claude- (main branch, one folder per project, e.g. escort-dtm, sunbeam-lotus, nova-gte, tools). Commit and push after each meaningful step. Never commit secrets or files over 100 MB (.kn5, .blend, textures and renders are gitignored; use Git LFS if they must be tracked). Keep the repo on D:, never C:.
- A cleaned PUBLIC copy of the Claude- repo is github.com/nicklearse101-creator/claude-projects (D:\Claude\claude-projects). Keep saving to Claude- as normal; a global Stop hook refreshes the public copy automatically (sensitive info removed) via `tools/publish_public.py --auto`. Never commit to the public repo directly.
