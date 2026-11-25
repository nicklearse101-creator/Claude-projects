---
name: feedback-ac-native-first
description: "For AC car features, use the native AC/CSP way first (ksanim animations, ext_config sections) and check how installed mods do it before writing custom Lua hacks"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c27446ac-194b-4ace-8388-a9b2ff39d003
  modified: 2026-11-25T20:27:42.057Z
---

Nik 25 Nov 2026, Escort horn middle-finger gesture: I spent 4 rounds moving driver bones from a Lua car script (jitter,
double arm, flicker) when the normal AC way is a .ksanim animation (like steer/shift) bound in ext_config. Nik: "you really
should've thought of that yourself ... basic game stuff and all we've ever done is Assetto Corsa". An installed mod already
did exactly this (bdb_mazda_miata_na1/animations/fuck.ksanim).

**Why:** the native mechanism is what the game is built for; script hacks fight the game's own update order.

**How to apply:** before building any AC car feature, (1) grep Nik's installed cars (content/cars/*/animations, */extension)
for an existing example, (2) use ksanim + [ANIMATION_...] / ext_config sections if they fit, (3) only then consider Lua.
Related: [[escort-mk2-dtm-project]], [[feedback-kit-edge-fixes]].
