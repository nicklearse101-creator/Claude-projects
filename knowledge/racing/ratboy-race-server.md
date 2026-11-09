---
name: ratboy-race-server
description: "RATBOY's race-server Server Manager web address and when it's online - where Ratty's Racing race-night results live"
metadata:
  node_type: memory
  type: reference
  originSessionId: 697f937a-51fc-411b-a08d-68df19522080
  modified: 2026-09-24T22:08:23.557Z
---

RATBOY's race server (the PC that hosts Ratty's Racing race nights) runs
Server Manager at **[race server]** - live timing at
`/live-timing`, results at `/results`, API at `/api/results/list.json`
(use `?server=0`; his watchdog.ini's `web_server_index = 0` worked there).
Online usually **Thursdays and Sundays 19:30-22:00 UK time** only (Nik,
2026-09-24); outside that it times out. Race-night results live there,
not on Nik's own server (`[race server]`, which hosts the
Sunday/Thursday/GT3/Drift practice servers).

Pull a session's lap times from it with
`python -m physics_watchdog results --server-url [race server] --server 0 --type RACE --list 5`
(then `--file <name>`), or `--attach <capture folder>` to match the file
to a capture by session type/end time and fill in its report. Pending as
of 2026-09-24: race 2 of that night (started 21:10) has no lap-time
section - the watchdog was stopped before END_SESSION. Nik said yes to a
one-off scheduled task, `fetch-ratboy-race2-results`, firing Sun
2026-09-27 19:45 (retries every ~10 min until 22:00; re-arms itself if it
started outside the window). If asked about it, check
`list_task_runs` / the capture's report for a "fetched later" section.
See [[ac-physics-watchdog-project]].
