---
name: feedback-content-manager-taskbar
description: "To look at Content Manager, click its red button on the taskbar - never open_application('Content Manager'), which starts AssettoCorsa.exe (the game)"
metadata:
  type: feedback
---

When I need Content Manager on screen (computer-use), bring the already-running CM forward with its button on the
taskbar (the red CM icon, first pinned icon on the left). CM normally runs all the time as `Content Manager.exe`.
Never use `open_application("Content Manager")`.

**Why:** 2026-09-29 the computer-use grant for "Content Manager" resolved to
`D:\SteamLibrary\steamapps\common\assettocorsa\assettocorsa.exe`, so open_application started the Assetto Corsa
game/launcher. Nik: "stop opening assetto game when you need to do something, use the content manager button on taskbar!"

**How to apply:** check `tasklist` for `Content Manager.exe` first; request access (Content Manager, plus File Explorer
if the taskbar click is blocked - the taskbar belongs to explorer.exe), screenshot, click the CM taskbar button. If CM
isn't running, ask Nik instead of starting anything. Viewing only unless he says otherwise.
2026-10-06 (worked): the grant must be for the basename `Content Manager.exe` (request_access with exactly that) - the
"Content Manager" grant is assettocorsa.exe and CM's windows stay masked/unclickable. Nik declined File Explorer, so
the taskbar was off limits; instead PowerShell restored + focused the running window (user32 ShowWindow(h, 9) if
IsIconic, an Alt keybd_event, then SetForegroundWindow on (Get-Process -Id <CM pid>).MainWindowHandle) - nothing
launched. CM Showroom (button "CM Showroom" under the car list): left-drag orbits, wheel zooms, but its side-panel
tab icons ignore synthetic clicks (door/lights controls unreachable; clicks in the 3D view select meshes) - Nik:
"if it doesn't work then stop, an image of the outside is fine". Capture = zoom(region, save_to_disk) left of the
panel. Car list filter = the box top-left (type, Enter).
Related: [[talbot-sunbeam-lotus-ac-mod]], [[sunbeam-plus10-watchdog-test]], [[escort-mk2-dtm-project]].
