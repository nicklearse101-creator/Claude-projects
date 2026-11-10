---
name: ac-skin-generator-project
description: "Ratty's4Skin Generator (no-AI livery app for any AC car, installer for sharing) + Ratty Racing Lacetti skin; UV-mirroring lesson"
metadata:
  node_type: memory
  type: project
  originSessionId: b5d0974f-1d45-42d3-b3a7-17366915de1f
  modified: 2026-11-09T21:17:42.574Z
---

"Ratty's4Skin Generator" (Nik's chosen name, 2026-11-09) in `D:\Claude\Claude-\ac-skin-generator\`: `rattys4skin.py` (tk app, tabs Car/Livery/Number & names/Logos/Windows/Lights & wheels), `skingen.py` (core), `kn5.py`, `installer.py`, `build.py` -> `release\Rattys4SkinGenerator_Setup.exe` (53 MB, per-user install, desktop shortcut, uninstall entry; not in git). User data in %APPDATA%\Rattys4SkinGenerator (settings, logo library). Projects designs from the 3D model; logo library with placements; window stickers (glass + Kunos EXT_Banner overlays); headlight lens tint + CSP beam colour via skin ext_config.ini (per-skin ext_config confirmed from real skins). Nik tested in-game 9 Nov (Escort, Audi Sport quattro, Peugeot 308): placement works, loads in CM, overwrite works; open issues are in the plan below.

Hand-made skin: `wtcc_chevrolet_lacetti/skins/ratty_racing_101`, scripts in `lacetti-ratty-skin/`.

**RESUME HERE (next session):** `ac-skin-generator/PLAN_next_session.md` - banner mess, decals breaking across panels (needs depth test), nothing on side windows; test car wtcr_peugeot_308_gti_ss. v1.3.2 is the current installer.

**Nik's rule (9 Nov):** decals/pictures must never be broken or cut - stretch them over curves, arches and panel steps; only hide them on inner/hidden surfaces (depth test).

**Lessons:** never judge UV-strip orientation by eye (Lacetti right side is upside down; first skin came out mirrored). Verify with the 3D preview (`tests/test_stock.py CAR SKIN out.png`). The Bash tool mangles backslashes in heredocs (`\b`, `\n` became control chars / newlines) - write patch scripts with the Write tool instead.

**How to apply:** extend the generator for skin work; render both sides before claiming text reads right. Related: [[escort-mk2-dtm-project]], [[talbot-sunbeam-lotus-ac-mod]].
