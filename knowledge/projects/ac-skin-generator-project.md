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

**v1.5.2 (10 Nov 2026 evening)** is current (zip release/Rattys4SkinGenerator_v1.5.2.zip). 1.5.0 = Nik's 2nd list (seams, Talbot body, placement check, edit on preview, fonts); 1.5.1 = Preview writes nothing + says so (Nik's 'blue dashboard' was an OLD 9 Nov skin still in the car - he had only previewed), app scratch on the game drive; 1.5.2 = rims/tyres separate, Talbot body_2.dds stripes painted ("carPaint" contains "int_" - interior regex needs (?<![a-z])int_), ONE placement for all paint textures (ctx), one-UV-spot parts (bonnet scoop) get base colour, OFF_LIMIT stops side decals streaking onto flat tops, decals move up/down off mirrored texels. `PLAN_next_session.md` has every version + open items. **RESUME HERE:** Nik's in-game check of 1.5.2 (Talbot, Kadett); open = wing-top letter clipping on curved creases, Talbot lower-door name behind sill trim, Escort rear half on NICK3_KIT_ATLAS, window stickers not hand-movable, DXT output. Test scratch goes to D:/ClaudeData/tmp/skin_gen (never C:).

**Key findings (v1.4.0):** (1) broken writing was folded/overlapping UVs - the triangle owning a texel was often hidden; decals are now painted through the really-visible triangles (`decal_hits`: sample triangles, front-most per 5 mm cell, mini raster nearest-last). (2) The Peugeot's "old banner" was a painted body panel (`window_part` on skin_00) lying on the windscreen - `find_sunstrips` finds such panels by geometry. (3) The old texel-splat preview HID these faults; `render_view` now draws the real triangles with UV lookup (trust it). (4) kn5 material blend/alpha flags are read now (`Material.blend`) - glass = see-through material. Test with `tests/nik_test.py CAR OUT [key=value]` (uses Nik's saved app settings; `ZOOM=left,right` env for big views; `debug_decals=true`).

**Nik's rule (9 Nov):** decals/pictures must never be broken or cut - stretch them over curves, arches and panel steps; only hide them on inner/hidden surfaces (depth test).

**Lessons:** never judge UV-strip orientation by eye (Lacetti right side is upside down; first skin came out mirrored). Verify with the 3D preview (`tests/test_stock.py CAR SKIN out.png`). The Bash tool mangles backslashes in heredocs (`\b`, `\n` became control chars / newlines) - write patch scripts with the Write tool instead.

**How to apply:** extend the generator for skin work; render both sides before claiming text reads right. Related: [[escort-mk2-dtm-project]], [[talbot-sunbeam-lotus-ac-mod]].
