---
name: ac-skin-generator-project
description: "Ratty's4Skin Generator (no-AI livery app for any AC car, installer for sharing) + Ratty Racing Lacetti skin; UV-mirroring lesson"
metadata:
  node_type: memory
  type: project
  originSessionId: b5d0974f-1d45-42d3-b3a7-17366915de1f
  modified: 2026-11-09T23:03:42.426Z
---

"Ratty's4Skin Generator" (Nik's chosen name, 2026-11-09) in `D:\Claude\Claude-\ac-skin-generator\`: `rattys4skin.py` (tk app, tabs Car/Livery/Number & names/Logos/Windows/Lights & wheels), `skingen.py` (core), `kn5.py`, `installer.py`, `build.py` -> `release\Rattys4SkinGenerator_Setup.exe` (53 MB, per-user install, desktop shortcut, uninstall entry; not in git). User data in %APPDATA%\Rattys4SkinGenerator (settings, logo library). Projects designs from the 3D model; logo library with placements; window stickers (glass + Kunos EXT_Banner overlays); headlight lens tint + CSP beam colour via skin ext_config.ini (per-skin ext_config confirmed from real skins). Nik tested in-game 9 Nov (Escort, Audi Sport quattro, Peugeot 308): placement works, loads in CM, overwrite works; open issues are in the plan below.

Hand-made skin: `wtcc_chevrolet_lacetti/skins/ratty_racing_101`, scripts in `lacetti-ratty-skin/`.

**v1.5.0 (10 Nov 2026)** is current: v1.4.0 fixed Nik's first in-game list (banner mess, decals breaking across panels, side windows); v1.5.0 his second (base colour into every seam via `pad_texture`; Talbot works - body texture found though no skin overrides it; logos + names share a place, `arrange_decals` + on-panel coverage check; decals moved / sized / turned / flipped with the mouse on the preview, saved per car as `adjust_by_car`; fonts for team / driver / number; plain black rims; `car_catalogue()` JSON in %APPDATA%). `PLAN_next_session.md` lists both and what is open. **RESUME HERE:** Nik's in-game check of v1.5.0; open = ford_escort_mk2_tuned rear half is on NICK3_KIT_ATLAS (not painted), window stickers not hand-movable, DXT output.

**Key findings (v1.4.0):** (1) broken writing was folded/overlapping UVs - the triangle owning a texel was often hidden; decals are now painted through the really-visible triangles (`decal_hits`: sample triangles, front-most per 5 mm cell, mini raster nearest-last). (2) The Peugeot's "old banner" was a painted body panel (`window_part` on skin_00) lying on the windscreen - `find_sunstrips` finds such panels by geometry. (3) The old texel-splat preview HID these faults; `render_view` now draws the real triangles with UV lookup (trust it). (4) kn5 material blend/alpha flags are read now (`Material.blend`) - glass = see-through material. Test with `tests/nik_test.py CAR OUT [key=value]` (uses Nik's saved app settings; `ZOOM=left,right` env for big views; `debug_decals=true`).

**Nik's rule (9 Nov):** decals/pictures must never be broken or cut - stretch them over curves, arches and panel steps; only hide them on inner/hidden surfaces (depth test).

**Lessons:** never judge UV-strip orientation by eye (Lacetti right side is upside down; first skin came out mirrored). Verify with the 3D preview (`tests/test_stock.py CAR SKIN out.png`). The Bash tool mangles backslashes in heredocs (`\b`, `\n` became control chars / newlines) - write patch scripts with the Write tool instead.

**How to apply:** extend the generator for skin work; render both sides before claiming text reads right. Related: [[escort-mk2-dtm-project]], [[talbot-sunbeam-lotus-ac-mod]].
