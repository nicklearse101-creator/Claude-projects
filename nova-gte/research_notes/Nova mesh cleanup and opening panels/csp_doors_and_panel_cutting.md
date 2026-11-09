# CSP opening doors, bonnet and tailgate + cutting opening panels from a one-piece body (Nova GTE)

Research date: 2026-10-19. Local CSP install checked: **0.2.12-preview1, build 3467** ([local: extension/installed.log](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/installed.log)). All local files were read only.
Local evidence is cited as `file:///` links. These are primary sources: Kunos' own pipeline PDF, the CSP Lua SDK, real mod configs and ksanim files decoded byte for byte.

---

## 1. Which CSP ext_config sections and keys animate doors, bonnet and boot, and how does the player trigger them?

### Takeaway
CSP has **no dedicated DOOR, HOOD or TRUNK section**. Opening panels use the generic **`[ANIMATION_...]`** section. It plays a `.ksanim` clip from the car's `animations/` folder, driven by an input, usually an **extra switch (`EXTRA_A`…`EXTRA_F`)**. The `[EXTRA_SWITCHES]` section names the switches and can lock them to "car stationary". The player presses the extra-switch keys bound in Content Manager > Settings > Custom Shaders Patch > Controls. On Nik's PC these are already bound to Alt/Ctrl+Alt + numpad keys. `[ANIMATED_...]` is a different thing: spinning parts and wipers.

### Cited Findings
**`[ANIMATION_...]` (official CSP docs)**
- Section `[ANIMATION_...]`, one block per animation. Keys: `INPUT` (or `BIND_TO` as an alternative), `FILE` (ksanim in the `animations` folder), `TIME` (duration), `INPUT_AS_PROGRESS`, `LOOP_WHILE_ACTIVE`, `LOOP_KEEP_UNTIL_DONE`, `TICK_TOCK_MODE`, `AFFECTS_INTERIOR_SHAPE` (updates the interior reflection mask while playing; slower), `HOLD_STATE` (commented "for hoods and such"), `BLEND_STATE`, `LUT`. The minimum is `INPUT` + `FILE`. — [CSP docs: Cars/Animations](https://cup.acstuff.club/docs/csp/cars/animations); same content on the [acc-extension-config wiki mirror](https://github-wiki-see.page/m/ac-custom-shaders-patch/acc-extension-config/wiki/Cars-%E2%80%93-Animations)
- Two modes. **Trigger mode** (default): the animation goes to 100% when the input is over its threshold and back to 0% otherwise; `INPUT_THRESHOLD` and `INPUT_THRESHOLD_INVERSE` adjust this. **Progress mode** (`INPUT_AS_PROGRESS = 1`): the input value sets the position directly. Loop options have no effect in progress mode. — [CSP docs: Cars/Animations](https://cup.acstuff.club/docs/csp/cars/animations)
- Official minimal example: `[ANIMATION_...]` / `INPUT = REVERSE` / `FILE = animation.ksanim` / `TIME = 0.5`. — [CSP docs: Cars/Animations](https://cup.acstuff.club/docs/csp/cars/animations)

**Real configs on this PC (857 cars scanned)**
- `[ANIMATION_...]` is the 9th most common car-config section locally (686 blocks). The ksanim names it plays for opening panels include `car_door_L/R.ksanim` (about 450 files across case variants), `hood.ksanim`, `hood_anim.ksanim`, `car_hood.ksanim`, `trunk.ksanim`, `boot.ksanim`, `car_rear_hood.ksanim`, `car_door_LR/RR.ksanim` and `scissor_door_left/right.ksanim`. — local scan of [content/cars/*/extension/ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/)
- Two binding syntaxes are in use. One is documented, `INPUT = EXTRA_C`. The other, `BIND_TO_EXTRA_C=1`, is widely used but is not on the current docs page (95 `BIND_TO_EXTRA_C`, 66 `BIND_TO_EXTRA_B`, 30 `_A`, 20 `_D`, 7 `_E` locally). — local scan; example [bg_lotus_carlton ext_config](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bg_lotus_carlton/extension/ext_config.ini)
- **Lotus Carlton mod (closest relative to the Nova on disk)** binds every panel to its own switch:
  ```ini
  [ANIMATION_0]
  FILE=car_door_L.ksanim
  TIME= 3.0
  BIND_TO_EXTRA_D=1
  [ANIMATION_1]
  FILE=car_door_R.ksanim
  TIME= 3.0
  BIND_TO_EXTRA_C=1
  [ANIMATION_2]
  FILE=car_door_LR.ksanim   ; rear doors share EXTRA_E
  TIME= 3.0
  BIND_TO_EXTRA_E=1
  [ANIMATION_4]
  FILE=hood.ksanim
  TIME= 3.0
  BIND_TO_EXTRA_B=1
  [ANIMATION_5]
  FILE=trunk.ksanim
  TIME= 3.0
  BIND_TO_EXTRA_F=1
  ```
  — [local: bg_lotus_carlton/extension/ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bg_lotus_carlton/extension/ext_config.ini)
- **GT4 Alpine A110**: a "stationary only" door switch, both doors on one switch:
  ```ini
  [EXTRA_SWITCHES]
  SWITCH_C = Open Doors
  SWITCH_C_FLAGS =  STATIONARY_ONLY
  [ANIMATION_...]
  FILE=car_door_l.ksanim
  TIME= 1.5
  BIND_TO_EXTRA_C=1
  [ANIMATION_...]
  FILE=car_door_r.ksanim
  TIME= 1.5
  BIND_TO_EXTRA_C=1
  ```
  `SWITCH_C_FLAGS = STATIONARY_ONLY` appears in 16 local configs. — [local: gt4_alpine_a110/extension/ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gt4_alpine_a110/extension/ext_config.ini)
- Fully commented template used by several mods (BMW E46 boot, Altezza hood): `INPUT = EXTRA_B`, `FILE = boot.ksanim`, `TIME = 3.0`, `INPUT_AS_PROGRESS = 0`, `LOOP_WHILE_ACTIVE = 0`, `LOOP_KEEP_UNTIL_DONE = 1`, `TICK_TOCK_MODE = 0`, `AFFECTS_INTERIOR_SHAPE = 1`. — [local: adc_bmw_e46/extension/ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/adc_bmw_e46/extension/ext_config.ini)
- Nik's own Escort project used `[ANIMATION_1] FILE=hood_anim.ksanim TIME=1 BIND_TO_EXTRA_D=1`, with `car_door_L.ksanim` and `car_door_R.ksanim` both on `BIND_TO_EXTRA_C=1`. — [local: escort_mk2_dtm archive ext_config](file:///D:/Claude/escort_mk2_dtm/archive/replaced_20261006_035100/ext_config.ini)
- Real `TIME` values seen: 1 s (Escort), 1.5 s (Alpine), 2.5 s (doors) and 3 s (hood) on the F1 Safety Car mod, 3 s (Lotus Carlton). — local configs above and [Maxes_F1_Safety_Car ext_config](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/Maxes_F1_Safety_Car/extension/ext_config.ini)

**Extra switches: how the player triggers them**
- Cars get up to 4 extra switches, or 6 since CSP 0.1.76: `EXTRA_A`…`EXTRA_F`. In `controls.ini` they are `__EXT_LIGHT_A`…`__EXT_LIGHT_F`. `[EXTRA_SWITCHES]` takes `SWITCH_A = Role` (shown during loading) and `SWITCH_A_FLAGS =` with flags `HOLD_MODE`, `STATIONARY_ONLY`, `NEURAL_GEAR_ONLY` (sic) and `REQUIRES_BRAKE`. Users bind buttons in Content Manager's controls settings, Patch section. Switch states feed instruments, emissives, animations, Lua (`car.extraA`…) and dynamic controllers (`LIGHT_EXTRA_A`…). — [CSP docs: Cars/Extra switches](https://cup.acstuff.club/docs/csp/cars/extra-switches)
- Nik's current bindings: `__EXT_LIGHT_A` = Alt+Numpad7 (KEY=0x67, KEY_MODIFICATOR=18), `_B` = Alt+Numpad8 (0x68), `_C` = Alt+Numpad9 (0x69), `_D` = Alt+Numpad+ (0x6B), `_E` = Ctrl+Alt+Numpad7, `_F` = Ctrl+Alt+Numpad8. — [local: Documents/Assetto Corsa/cfg/controls.ini](file:///C:/Users/nickl/Documents/Assetto%20Corsa/cfg/controls.ini), lines 650-690
- Real mods use the role string for the HUD/loading label, e.g. `SWITCH_C = open doors` (14 local configs). — local scan
- Inputs listed in the CSP inputs reference: `OPENDOORS` ("are doors opened?"), `EXTRA_A`…`EXTRA_F` ("is Extra A thing on?"), `SPEED`, `HANDBRAKE`, `STALLED`, `RPM`. There is no pit-lane or "in pits" input on that page. — [CSP docs: Cars/Instruments inputs](https://cup.acstuff.club/docs/csp/cars/instruments-inputs)
- `INPUT` also accepts expressions such as `INPUT='calc:1-EXTRA_A-SPEEDLIMITER'` (17 local configs). — local scan of `ext_config.ini` files

**Other door-related CSP hooks**
- Lua SDK (all script types): `car.isDriverDoorOpen` (boolean). Apps, online, tools and new-modes scripts also get `ac.setDriverDoorOpen(carIndex, isOpen, instant)` ("Toggles driver door animation."). The bundled CspDebug app has an "Open door" button that calls it. — [local: lua-sdk/ac_apps/lib.lua lines 4136, 14307-14311](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/lib.lua); [local: CspDebug.lua line 389](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-apps/CspDebug/CspDebug.lua)
- CSP changelog entries (from CM's cached CSP manifest):
  - 0.1.77: Lua "access some gameplay API (… toggle drivers, open car doors …)".
  - 0.2.1: "Side mirrors on doors with Real Mirrors enabled take into account door rotation when opened".
  - 0.2.5: "Option to mix in external audio with opened doors", "Door sounds … introduced by CSP, are fixed", "Loaded replays no longer play door sound at the start".
  - 0.2.7: WindscreenFX reflections "mostly for the way interior part of glass looks with an open door".
  - 0.2.8: "Deforming hoods and trunks are fixed".
  — [local: CM Temporary/Patch/Manifest.json](file:///C:/Users/nickl/AppData/Local/AcTools%20Content%20Manager/Temporary/Patch/Manifest.json)
- Courtesy-light template in CSP: `[MIXIN: OpenDoorLight]` generates `EMISSIVE_OPENDOORS_...` and `LIGHT_OPENDOORS_0`, with default colour `16, 15.6, 6` and lag 0.8. The turn-signal light template has `RELATIVE_TO = … ${AnimatedDoors…}`, which attaches a light to a door node so it moves with the door. — [local: extension/config/cars/common/custom_emissive.ini lines 9, 21, 374, 641-660](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/custom_emissive.ini)
- **Physics-driven swinging:** the closest documented feature is `[WOBBLY_BIT_N]`, with `NAME` (node), `CONNECTED_TO` (x,y,z pivot "around which it will rotate"), `MAX_RANGE` (a distance, not an angle), `DAMPENING_LAG`, `G_GAIN`, `GRAVITY_GAIN`, `OFFSET_GAIN` (return force), `STIFF_AXIS` and `STIFF_AXIS_STIFFNESS`, `G_FILTER` and `DEFAULT_GRAVITY_INCLUDED_ALREADY`. Doors are not mentioned, and there are no hinge angle limits. — [CSP docs: Cars/Wobbly bits](https://cup.acstuff.club/docs/csp/cars/wobbly-bits)
- Damage behaviour of the bonnet and boot: `[DEFORMING_HOOD]` with `NAME = MOTORHOOD` and `[DEFORMING_REAR]` with `NAME = REARHOOD`. Keys: `MAX_DAMAGE` (km/h), `OFFSET_Y_MIDDLE`, `OFFSET_Y_END`, `OFFSET_Z_END`, `BULGING_*`, `NOISE_*`, `Z_FACTOR`, `Z_BIAS`. `NAME` is the "parenting node containing all meshes to deform". Doors are listed only as a possible future addition. — [CSP docs: Cars/Deforming bonnets](https://cup.acstuff.club/docs/csp/cars/deforming-bonnets)
- `[ANIMATED_...]` in car configs is for spinning or windmill nodes (`NODE`, `SPIN_AXIS`, `WINDMILL_DIR`, `SPEED_MULT`). `[ANIMATED_WIPER_N]` is for procedural wipers (`GROUP_0_PIVOT`, `GROUP_0_AXIS` …). Neither is for doors. — [local: ford_escort_mk2_tuned ext_config](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ford_escort_mk2_tuned/extension/ext_config.ini); [local: config/cars/loaded/ks_toyota_ae86.ini lines 274-331](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/loaded/ks_toyota_ae86.ini)

### Inferences
- **Suggested Nova block** (a design suggestion, not a tested config). It uses the documented `INPUT` key and keeps the Escort convention C = doors, D = bonnet:
  ```ini
  [EXTRA_SWITCHES]
  SWITCH_C = Driver door
  SWITCH_C_FLAGS = STATIONARY_ONLY
  SWITCH_D = Bonnet
  SWITCH_D_FLAGS = STATIONARY_ONLY
  SWITCH_E = Tailgate
  SWITCH_E_FLAGS = STATIONARY_ONLY
  SWITCH_F = Passenger door
  SWITCH_F_FLAGS = STATIONARY_ONLY

  [ANIMATION_...]
  INPUT = EXTRA_C
  FILE = car_door_R.ksanim      ; RHD: driver door is on the right
  TIME = 1.5
  AFFECTS_INTERIOR_SHAPE = 1

  [ANIMATION_...]
  INPUT = EXTRA_F
  FILE = car_door_L.ksanim
  TIME = 1.5
  AFFECTS_INTERIOR_SHAPE = 1

  [ANIMATION_...]
  INPUT = EXTRA_D
  FILE = bonnet.ksanim
  TIME = 2.0

  [ANIMATION_...]
  INPUT = EXTRA_E
  FILE = tailgate.ksanim
  TIME = 2.0
  AFFECTS_INTERIOR_SHAPE = 1
  ```
  On Nik's keyboard this gives Alt+Num9 (driver door), Alt+Num+ (bonnet), Ctrl+Alt+Num7 (tailgate) and Ctrl+Alt+Num8 (passenger door).
- Keep the standard names `car_door_L.ksanim` and `car_door_R.ksanim` for the doors. Vanilla AC, CM's showroom and CSP's driver-door API use those names (see Q2). Bonnet and tailgate clips can use any name, because only the `[ANIMATION_...]` block references them.
- `STATIONARY_ONLY` matches the brief "in the pits / when stopped". It blocks changing the switch while moving; whether a panel already open stays open while driving is not documented.
- Mirrors: Nova door mirrors sit on the doors, so parent them to the door nodes. CSP 0.2.1 makes Real Mirrors follow door rotation.

### Gaps
- No documentation of what `HOLD_STATE` and `BLEND_STATE` actually do beyond "for hoods and such".
- `BIND_TO_EXTRA_X=1` is undocumented on the current docs page, although it works in hundreds of released mods. Use `INPUT = EXTRA_X` to stay on the documented path.
- No documented config for **door sounds** on custom cars. CSP has door audio events (the 0.2.5 changelog; the SDK uses `'/cars/lada_revolution/door'` as an example FMOD event name), but I found no ext_config key that ties a car door sound to an `[ANIMATION_...]`.
- No CSP feature found for physics-driven doors that swing open while driving. `WOBBLY_BIT` is the only approximation and has no angular limits.
- Not confirmed which state drives the `OPENDOORS` input. It is probably the driver-door state from `ac.setDriverDoorOpen`, but that is unverified.

---

## 2. Does CSP open doors on its own from mesh names, need .ksanim files, or rotate nodes procedurally? What about the driver getting in and out?

### Takeaway
CSP does **not** open panels just because nodes are named DOOR_L or HOOD. Every working example on disk plays a **ksanim clip that animates named dummy nodes**. A ksanim is a tiny binary file that Nik's Escort tooling already writes from Python, so no 3ds Max or ksEditor is needed. Procedural rotation is possible from a car Lua script (`ac.findNodes(...):setRotation(...)`), but no released car on disk does it that way. There is **no driver getting-in/out animation**. Kunos driver clips are steering and shifting only, and CSP's "driver door" API only plays the door clip.

### Cited Findings
- Kunos standard car clip names: `car_door_R.ksanim` and `car_door_L.ksanim`, "PingPong for the animation to open the … door (the closing animation should be the open animation in reverse. Do not animate the closing sequence!)". Also `car_wiper.ksanim`, `lights.ksanim`, `car_shift.ksanim`, `car_susp_*.ksanim` and `car_wing.ksanim`, and "You can create all the animations needed… use new names". — [local: sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf p.62](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- "Never animate the mesh. Always animate the NULLs only!" The same technique applies to "doors, gearbox levers, or any other parts". When exporting an animated null, also export the hierarchy above it, "as the name of an object inside the editor is determined by its position in the hierarchy tree". — [local: AC_Pipeline_PUB_Rev2.0.pdf p.60-61](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- "For a simple door animation, the 'close' and 'open' frames are enough, the game will interpolate the rest." — [local: AC_Pipeline_PUB_Rev2.0.pdf p.61](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- Driver animation clip names are only `steer.ksanim`, `shift.ksanim`, `shift_dw.ksanim` and `shift_up.ksanim`. The SDK "Driver animation" folder has only `DRIVE_BASE.fbx` and `DriverRig_1.7.rar`; there is no entry or exit clip. — [local: AC_Pipeline_PUB_Rev2.0.pdf p.61](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf); [local: sdk/dev/car_pipeline_2.0rev/Driver animation/](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/)
- **ksanim v2 binary format, verified by decoding real files with every byte accounted for:**
  - Header: `int32 version (2)`, `int32 nodeCount`.
  - Per node: `int32 nameLen`, the name bytes, `int32 frameCount`, then `frameCount × 10 float32`: rotation quaternion (x, y, z, w), translation (x, y, z) and scale (x, y, z), local to the node's parent.
  - Decoded files: the AE86 `car_door_L.ksanim` (16,074 bytes, 4 nodes × 100 frames) and the Lotus Carlton `hood.ksanim`, `trunk.ksanim` and `car_door_L.ksanim`.
  — decoded locally with a throwaway parser; files at [ks_toyota_ae86/animations](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86/animations/) and [bg_lotus_carlton/animations](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bg_lotus_carlton/animations/)
- Nik's Escort project already has a working writer, `write_door_ksanim(path, door, open_deg, frames=100)`. It writes ksanim v2 for one node and rotates the door empty's kn5 rest pose about the vertical axis with ease-in/out. Its docstring says "AC axes: x left, y up, z forward", and it uses the same `TO_AC` matrix as the Nova exporter. — [local: escort_mk2_dtm/tools/blender/model_fixes.py lines 216-333](file:///D:/Claude/escort_mk2_dtm/tools/blender/model_fixes.py); [local: vauxhall_nova_gte_1989/tools/ac_kn5_export.py line 31](file:///D:/Claude/vauxhall_nova_gte_1989/tools/ac_kn5_export.py)
- **Single-node clips work in a released mod.** The Lotus Carlton's ksanims each hold one node (`DOOR_LF`, `DOOR_LR`, `TRUNK`; `hood.ksanim` holds `HOOD` + `HOOD_1`), with no parent chain. — decoded [bg_lotus_carlton/animations](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bg_lotus_carlton/animations/)
- Node names are free for CSP `[ANIMATION_...]` clips. Real examples: `FRONT_HOOD` (Aston Vantage GT3), `HOOD`/`TRUNK` (Lotus Carlton), `boot`, `boot001`… (BMW E46, a boot plus strut nodes), `Hood_1..3` (F1 Safety Car) and `MOTORHOOD` (Sunbeam backup v1). — decoded ksanims under [content/cars](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/)
- Procedural option: Lua placed in `content/cars/*/extension*` uses the `ac_car_scriptable_display` SDK ([local: lua-sdk/rules.json](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/rules.json)). That SDK provides:
  - `ac.findNodes(s)`;
  - `SceneReference:setRotation(axis, angleRad)` ("Replaces orientation of a node … with rotational matrix") and `:rotate(axis, angleRad)`;
  - `SceneReference:setAnimation(filename, position, force)` ("Loads animation from a file … sets animation position" 0..1);
  - `car.extraA`…`car.extraF`.

  Cars load such scripts with `[SCRIPT_...] SCRIPT="name.lua"` (e.g. gmp_bnr34). — [local: lua-sdk/ac_car_scriptable_display/lib.lua lines 3986-3991, 8788, 8866, 8875, 9319](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_car_scriptable_display/lib.lua); [local: gmp_bnr34_the_inevitable ext_config](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gmp_bnr34_the_inevitable/extension/ext_config.ini)
- `ac.setDriverDoorOpen(carIndex, isOpen, instant)` is documented only as "Toggles driver door animation". `ac.setDriverVisible(carIndex, isVisible)` can hide the driver. — [local: lua-sdk/ac_apps/lib.lua lines 14297-14311](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/internal/lua-sdk/ac_apps/lib.lua)
- **CM showroom:** Content Manager's stored Custom Showroom settings include `"LeftDoorOpen":false,"RightDoorOpen":false` beside `HeadlightsEnabled` and `ShowDriver`. — [local: AcTools Content Manager/Values.data](file:///C:/Users/nickl/AppData/Local/AcTools%20Content%20Manager/Values.data)
- A GTPlanet forum answer (seen only as a search snippet; the page returned 403 to fetch) told someone who wanted closed doors in CM previews to "remove the door animation from the animation folder, make previews, replace it". — [GTPlanet AC mods thread](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14556892)
- The older vanilla route seen in the Sunbeam base mod: `data/extra_animations.ini` with `[ANIMATION_0] FILE=ENGINE_MOTORHOOD.ksanim MIN=0 MAX=60`. — [local: talbot_sunbeam_lotus_81_works_backup_v1/data/extra_animations.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/talbot_sunbeam_lotus_81_works_backup_v1/data/extra_animations.ini)

### Inferences
- With rotation-only frames, a ksanim needs the **node origin exactly on the hinge line**. The Lotus Carlton door and hood clips keep translation constant and change only the quaternion. Its trunk clip also moves the translation, from (1.0698, -1.769) to (1.1351, -1.7002) in y/z. That shows you can fake an offset hinge (gooseneck or tailgate hinge) by animating translation as well.
- Opening angles and directions measured from the decoded clips (AC axes: +X = car's left, +Y up, +Z forward):

  | Clip | Rotation | Angle |
  |---|---|---|
  | Lotus `DOOR_LF` | about −Y (quat y = −0.4226) | 50.0° |
  | Lotus `HOOD` | about −X (quat x = −0.3837) | 45.1° |
  | Lotus `TRUNK` | about +X (quat x = +0.5736) | 70.0° |
  | AE86 `DOOR_L` and `DOOR_L_1` | — | about 75° |
  | Escort | — | 70° |

  So for the Nova: left door negative about Y, right door positive about Y. A tailgate hinged at the roof edge opens positive about X. A scuttle-hinged bonnet opens negative about X. Flip the sign for a front-hinged bonnet.
- The AE86 nodes carry a −90° X rest rotation (the 3ds Max Z-up convention baked in). The Lotus Carlton nodes carry an identity rest rotation, the Blender-style export our exporter produces. The Escort writer multiplies the rest quaternion by the opening rotation, which handles both cases.
- The simplest route is to reuse `write_door_ksanim` and generalise it with an axis argument for the bonnet and tailgate. A Lua approach would also need a script per car and would not run in CM's showroom.
- CM's showroom almost certainly plays `car_door_L.ksanim` and `car_door_R.ksanim` for its Left/Right door toggles. That is an inference from the setting names and the preview anecdote, and is untested. No evidence was found that CM's showroom plays CSP `[ANIMATION_...]` bonnet or tailgate clips.

### Gaps
- No CSP documentation of the driver-door API's exact behaviour: which ksanim it plays (presumably the driver-side `car_door_*`, chosen by driver position) and whether the driver model moves. I found no getting-in or getting-out animation anywhere.
- Semantics of vanilla `extra_animations.ini` `MIN`/`MAX` are not documented in the sources found (speed? damage?).
- CM Custom Showroom behaviour was inferred from setting names. The actools source could not be searched without a GitHub login, and the CM exe is packed.

---

## 3. Where are the CSP docs, and what do the local templates contain?

### Takeaway
The current official CSP docs live at **cup.acstuff.club/docs/csp/cars/** (45 car pages). The useful pages here are Animations, Extra switches, Wobbly bits, Deforming bonnets, Instruments inputs and Node adjustments. The older acc-extension-config GitHub wiki has the same Animations text. The local `extension/config/cars/common/` folder has **no door-animation template**; only `custom_emissive.ini` mentions doors, and only for courtesy lights. Kunos' **AC_Pipeline_PUB_Rev2.0.pdf** in the AC SDK folder is the authoritative source for null names and hierarchy.

### Cited Findings
- CSP car docs index (sidebar of any page): pages include animations, extra-switches, wobbly-bits, deforming-bonnets, node-adjustments, instruments-inputs, meshes-splitting, driver-model, physics-scripts and 37 others. — [CSP docs: Tips and tricks (index)](https://cup.acstuff.club/docs/csp/cars/tips-and-tricks)
- `[NODE_ADJUSTMENT_...]` only re-parents or toggles nodes (`NODES`, `MOVE_TO`, `IS_ACTIVE`; example: moving a stray interior mesh into `COCKPIT_HR`). It has no rotation or pivot keys. — [CSP docs: Cars/Node adjustments](https://cup.acstuff.club/docs/csp/cars/node-adjustments)
- The Driver model page covers only `[SHADOWED_DRIVER]` and `[DRIVER3D_MODEL]` / `[DRIVER3D_HIDE_OBJECT_...]`. Nothing about doors. — [CSP docs: Cars/Driver model](https://cup.acstuff.club/docs/csp/cars/driver-model)
- Files in local `extension/config/cars/common/`: custom_emissive, custom_rims, materials_*, gt3/f1 lights, navigators, displays, etc. Only `custom_emissive.ini` matches DOOR/HOOD/TRUNK/ANIMATED, through the OpenDoorLight mixin and the `AnimatedDoors` parameter. — [local: extension/config/cars/common/](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/common/)
- The per-car CSP configs in `extension/config/cars/loaded/` contain only `[ANIMATED_WIPER_...]` among the animation-type sections (60 blocks). No door blocks. — local scan of [extension/config/cars/](file:///D:/SteamLibrary/steamapps/common/assettocorsa/extension/config/cars/)
- Kunos pipeline PDF location: `sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf` (76 pages), with `Scene templates/` example FBX/MAX files. — [local](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/); the community guide points to the same PDF: [assettocorsamods "Your FIRST car" guide](https://assettocorsamods.net/goto/post?id=7197)
- Community animation tutorial: animate dummies in 3ds Max, export FBX with Bake Animation, open it in ksEditor ("FBX Animation"), and a ksanim is generated beside the FBX. That tutorial is for a track ferris wheel and uses `[ANIMATED_...] NODE= ANIMATION= DURATION=` (the track syntax). — [assettocorsamods: TUTORIAL Animation in Assetto Corsa](https://assettocorsamods.net/goto/post?id=15423)

### Inferences
- With no template to `@INCLUDE`, the Nova needs explicit `[EXTRA_SWITCHES]` + `[ANIMATION_...]` blocks (Q1).
- The track `[ANIMATED_...]` syntax from the ferris-wheel tutorial does not apply to cars. Do not mix it up with car `[ANIMATION_...]`.

### Gaps
- No CSP Discord-derived guide dedicated to opening car panels was found on assettocorsamods, overtake.gg or GTPlanet in the searches run.

---

## 4. How do modders cut opening panels out of a one-piece body mesh?

### Takeaway
Cut each panel along its real shut line into its own object, and give it real thickness at the edge. Then build what becomes visible when it opens: the door or tailgate inner skin, the jambs and shut faces on the body, and a dark closed "box" behind every opening so you never see into the model. Put a null or empty at the hinge (pivot), parent the panel meshes to it, and animate only the null. Kunos names: `DOOR_L`/`DOOR_R` for exterior doors, `DOOR_L_1`/`DOOR_R_1` for interior door parts under `COCKPIT_HR`, and `MOTORHOOD`/`REAR_HOOD` for damage pivots. Collision is unaffected, because AC uses a separate `collider.kn5`.

### Cited Findings
**Kunos rules (primary)**
- Null list:
  - Damage nulls placed "in the PIVOT point of the object around which the object rotates upon impact": `FRONT_BUMPER`, `REAR_BUMPER`, `MOTORHOOD`, `REAR_HOOD`, `FRONT_WING`, `REAR_WING`, `REAR_EXTRACTOR`.
  - Additional dummies: `WIPER_#`, `FRONT_LIGHT`, `DISPLAY_DATA`.
  - "`DOOR_L` and `DOOR_R` for exterior door animation (A and B)"; "`DOOR_L_1` and `DOOR_R_1` for interior door animation (A only)".
  — [local: AC_Pipeline_PUB_Rev2.0.pdf p.14](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- Mesh parts:
  - DOORS: "optional - only in LOD A if present on the model. In LOD B the doors are not animated but welded to the main body".
  - MOTORHOOD: "if needed, must be present in LOD A and LOD B".
  — [local: AC_Pipeline_PUB_Rev2.0.pdf p.15](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- Car damage guidelines:
  1. "Make sure that you have closed the mesh in the interior. You put a black texture or something very dark to ensure that there is no gaping hole behind the moving objects."
  2. Place the dummy at the logical rotation point; "For the MOTORHOOD it can be the hinges".
  3. "Detach parts only that don't leave holes in the car when moving, or carefully cap the holes."

  Nulls and parts stay separate in LOD B; in LOD C they can be attached to the body. — [local: AC_Pipeline_PUB_Rev2.0.pdf p.43](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- Door hierarchy for animation export: interior door meshes and nulls sit under `COCKPIT_HR` because the cockpit swaps between HR and LR. "The LR door will be hidden. So we have duplicated the door animation nulls with animation included, and placed them outside of COCKPIT_HR." "Remember to include all the cockpit door nulls" when exporting. — [local: AC_Pipeline_PUB_Rev2.0.pdf p.64](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- LOD B must contain the same animated null hierarchy and names as LOD A for exterior animations, "but not for … the doors nulls under the Cockpit_HR null". — [local: AC_Pipeline_PUB_Rev2.0.pdf p.63](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- Door glass: "Internal GLASS objects on the doors must be linked to the appropriate EXTERIOR door nulls." The internal glass is "a copy of the external polygons of the glass, but … normals pointing to the interior", with the KsWindscreen shader. — [local: AC_Pipeline_PUB_Rev2.0.pdf p.39](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- AO baking: for the cockpit, "place the doors" open (as pictured) and "Keep the doors far enough to avoid a dark occlusion on the borders and the doorsill". — [local: AC_Pipeline_PUB_Rev2.0.pdf p.54-55](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- Collider: "a simple solid object with as low polygon count as possible", ≤40-60 triangles, material "GL", closed, pivot at 0,0,0, saved as `collider.kn5`. Opening panels therefore never touch collision. — [local: AC_Pipeline_PUB_Rev2.0.pdf p.36](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf)
- Damage config on the same bonnet node (vanilla `damage.ini`): `[VISUAL_OBJECT_0] NAME=MOTORHOOD`, `STATIC_ROTATION_AXIS=-1,0,0`, `STATIC_ROTATION_ANGLE=2.5`, `OSCILLATION_AXIS`, `DAMAGE_ZONE=FRONT`, `MIN_SPEED=20`, `FULL_SPEED=60`. The same car also has CSP `[DEFORMING_HOOD] NAME=MOTORHOOD` and a `MOTORHOOD` ksanim, so one node serves damage, deformation and opening. — [local: talbot_sunbeam_lotus_81_works_backup_v1/data/damage.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/talbot_sunbeam_lotus_81_works_backup_v1/data/damage.ini); [its ext_config.ini line 157](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/talbot_sunbeam_lotus_81_works_backup_v1/extension/ext_config.ini)

**General modelling technique (secondary)**
- Separating hood, doors and trunk starts by cutting along an edge loop around each door. — [Lynda/LinkedIn Learning "Blender: Vehicle Modeling – Separating hood, doors, trunk"](https://www.lynda.com/Blender-tutorials/Separating-hood-doors-trunk/180810/363907-4.html) (search snippet only; the course is paywalled)
- Panel-gap technique in Blender:
  1. Mark the gap edges sharp.
  2. Put their vertices in a vertex group.
  3. Stack Edge Split → Solidify → Bevel, with Bevel limited to the group.

  Pitfall: other sharp edges make Solidify misbehave; fix it by limiting Solidify to a vertex group. — [Habrador: Adventures making doors in Blender](https://blog.habrador.com/2018/10/adventures-making-doors-in-blender.html)
- Simply cutting the door out of a subdivided body "looked poor". The advice was to use subsurf-hole and rolled-edge techniques, which give the panel a rounded, turned-in edge. — [Blender Artists: how to make car door apparent](https://blenderartists.org/t/how-to-make-car-door-apparent/337788)
- BeamNG workflow wiki (seen as a search snippet; the page now redirects to documentation.beamng.com): door jambs are "a bit tricky" but can be worked out from photos, and "the door itself would just be the inverse of the door jamb". For hoods and trunks, keep the underside fairly flat and simplified. — [BeamNG Vehicle Creation Workflow](https://wiki.beamng.com/Vehicle_Creation_Workflow)
- Polycount critique of game cars with opening doors:
  - Close the gap at the top of the inside of the door "to stop the player seeing into your model".
  - Too few divisions look weak with the doors open.
  - In one WIP the door was too thick and the hinge gap too large from inside; the real door's section follows the window angle.

  — [Polycount comment 1208083](https://polycount.com/discussion/comment/1208083); [Polycount comment 1588865](https://polycount.com/discussion/comment/1588865) (forum experience, not standards)

**Nik's own precedent (Escort Mk2, 5 Oct)**
- The Escort donor model had "no door nodes - every door part was merged into car-wide meshes". The fix split each door's mesh islands, inside a door-shaped bounding box, out into new objects. Those objects were parented to `DOOR_L`/`DOOR_R` ARROWS empties placed at the hinge (`HINGE = x 0.745, y -0.660, z 0.45`, "inside the doors' front edge"). The main model only was changed: "LODs keep closed doors". Opening angle: `DOOR_OPEN_DEG = 70`. — [local: escort_mk2_dtm/tools/blender/model_fixes.py lines 216-305](file:///D:/Claude/escort_mk2_dtm/tools/blender/model_fixes.py)
- Inner door skins had to be built because "the outer skin faces outwards, so from the cabin AC would cull" it. The skins were made in body colour and re-parented to the door nodes. Low-res cockpit copies of moved seals were dropped because they "would z-fight". — [local: model_fixes.py lines 179-230](file:///D:/Claude/escort_mk2_dtm/tools/blender/model_fixes.py)
- The Nova exporter writes each object's transform relative to its parent: `local = parent_world.inverted() @ obj.matrix_world`, converted with `TO_AC`. — [local: vauxhall_nova_gte_1989/tools/ac_kn5_export.py lines 31, 114-123, 218-223](file:///D:/Claude/vauxhall_nova_gte_1989/tools/ac_kn5_export.py)

### Inferences
Suggested Nova workflow, synthesised from the above (not tested on the Nova):
1. **Mark shut lines** on the one-piece body from the reference photos. Nova shut lines: door front, rear and sill edges plus the window frame; the bonnet perimeter (check whether its rear edge meets the scuttle and whether the front edge includes the grille); the tailgate perimeter around the rear glass, down to the bumper line. Add or slide edge loops so each shut line is a clean loop. Duplicate the faces inside the loop and separate them into the panel object, so the body keeps a matching hole edge.
2. **Gap and turn-in.** Inset or extrude the hole edge on the body inward 15-25 mm to make the jamb flange, and turn the panel edge in by the same depth. That gives the 3-5 mm visual gap and thickness without a boolean. Solidify limited to a rim vertex group (the Habrador method) is an alternative. Apply modifiers before export; the kn5 exporter writes evaluated meshes, but confirm this.
3. **Fill behind the openings:**
   - Door aperture: B-pillar shut face, A-pillar hinge face, sill top.
   - Bonnet: engine bay closeout. The Nova plan already includes an engine bay, which also matters because the bonnet will open over it.
   - Tailgate: boot floor, side trims, parcel shelf, tailgate seal flange.

   Use a dark material where detail is not worth it (Kunos rule).
4. **Inner skins.** Each door needs a door card plus an inner metal skin (the door shut face). The tailgate needs its inner frame. The bonnet needs an underside skin, flat and simple per BeamNG. Normals must face inward, because AC back-face culls (Escort finding).
5. **Pivot empties.** `DOOR_L` and `DOOR_R` at the front hinge line. `MOTORHOOD` (or a custom name such as `BONNET`) at the bonnet hinges. A tailgate empty at the roof-edge hinges. Keep the empties' rotation identity in Blender, like the Lotus Carlton, so the ksanim rest quaternion is trivial. Parent to the root/body node: the panel mesh(es), handle, lock, door glass (exterior and interior copy), mirror, card and seals. Put the tailgate glass, rear wiper and third brake light under the tailgate node. Remember to also parent any emissive meshes, and CSP lights via `RELATIVE_TO`.
6. **Naming.**
   - Use `DOOR_L`/`DOOR_R` for the doors.
   - For the bonnet, either use `MOTORHOOD`, so vanilla damage wobble and CSP `DEFORMING_HOOD` work on the same node, or a custom name if damage isn't wanted.
   - For the tailgate, `REAR_HOOD` is the Kunos damage name. CSP's deforming docs example uses `REARHOOD`; that `NAME` is configurable anyway.
   - Node names must be unique in the kn5, because ksanims address nodes by name.
7. **Interior door split (optional, Kunos-style).** If door cards sit under `COCKPIT_HR`, add `DOOR_R_1`/`DOOR_L_1` empties under `COCKPIT_HR` and animate both nulls in the same clip, as the AE86 does (`DOOR_L` + `DOOR_L_1` + `DOOR_ARM_L`). Otherwise keep everything under `DOOR_x` outside the cockpit, like the Lotus Carlton.
8. **LODs.** Per Kunos, doors are welded in LOD B, but the bonnet must be separate in LOD A and B. Open panels will snap shut visually when AC switches to LOD B at distance. This is acceptable for pit use.
9. **Collision.** Nothing to do. `collider.kn5` stays a closed ≤60-triangle box.
10. **Hinge axis nicety.** Real door hinge axes are usually tilted slightly. A quaternion about a tilted axis in the writer would reproduce that. This is general automotive knowledge, not sourced here.

### Gaps
- No primary source gives exact recommended gap widths or flange depths for AC cars. The 3-5 mm gap and 15-25 mm flange above are typical real-car figures from general knowledge, not from a cited source.
- Nova-specific hinge positions, bonnet hinge side and opening angles were not researched here. They need the reference photos or the workshop manual.
- Whether the Nova kn5 exporter applies modifiers (Solidify, Bevel) at export was not checked in detail; `mesh_groups(obj, depsgraph, …)` suggests it uses evaluated meshes, but this is unverified.

---

## 5. Example cars to learn from

### Takeaway
Six cars already on this PC show complete, working patterns: the Kunos AE86, Lotus Carlton, GT4 Alpine A110, Aston Vantage GT3, BMW E46 and Nik's own Escort. Copying their structure is safer than following forum descriptions.

### Cited Findings
- **ks_toyota_ae86 (Kunos).** `animations/` holds `car_door_L.ksanim`, `car_door_R.ksanim`, `lights.ksanim`, `car_wiper.ksanim`, `steer.ksanim` and `shift.ksanim`. The door clip animates `COCKPIT_HR` (static), `DOOR_L_1`, `DOOR_L` and `DOOR_ARM_L` (the check-strap arm); doors open about 75°. No ext_config is needed, because these are vanilla clip names. — [local: ks_toyota_ae86/animations](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86/animations/)
- **bg_lotus_carlton (mod).** Kn5 nodes `DOOR_LF`, `DOOR_RF`, `DOOR_LR`, `DOOR_RR`, `HOOD`, `HOOD_1`, `TRUNK`. Single-node clips with identity rest rotation. Doors 50°, hood 45°, trunk 70°. Each panel has its own extra switch (config in Q1). — [local: bg_lotus_carlton](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/bg_lotus_carlton/)
- **gt4_alpine_a110.** `[EXTRA_SWITCHES]` role names with `STATIONARY_ONLY`; both doors on `EXTRA_C`, 1.5 s. — [local: gt4_alpine_a110/extension/ext_config.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/gt4_alpine_a110/extension/ext_config.ini)
- **acf_aston_martin_vantage_gt3.** `car_hood.ksanim` animates `FRONT_HOOD`, with static entries for `GEO_FRONT_HOOD`, `INT_FRONT_HOOD`, `EXT_DECALS_FRONT_HOOD` and `EXT_PARTS_FRONT_HOOD`: a bonnet with separate outer, inner, decal and hardware children. — decoded [acf_aston_martin_vantage_gt3/animations/car_hood.ksanim](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/acf_aston_martin_vantage_gt3/animations/)
- **adc_bmw_e46.** `boot.ksanim` moves 5 nodes (`boot`, `boot001`…`boot004`), i.e. the lid plus its hinge or strut parts. Bound with `INPUT = EXTRA_B`, `TIME = 3.0`, `AFFECTS_INTERIOR_SHAPE = 1`. — [local: adc_bmw_e46](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/adc_bmw_e46/)
- **Nik's Escort project.** Blender-side door split, inner skins and a ksanim writer (Q2, Q4). — [local: escort_mk2_dtm/tools/blender/model_fixes.py](file:///D:/Claude/escort_mk2_dtm/tools/blender/model_fixes.py)
- **Porsche 911 GT3 2022 CSP-features mod.** Users open its doors through "Extra Option A, B, C and D in the Controls > Patch settings" (as reported in the download's discussion). — [overtake.gg: Porsche 911 GT3 2022 CSP features](https://overtake.gg/downloads/porsche-911-gt3-2022-csp-features.43619/updates) (search snippet)

### Inferences
- For the Nova, the Lotus Carlton is the best structural template: a Blender-style single-node rig with one switch per panel. Use the AE86 when you want a check-strap arm or the Kunos interior/exterior door-null split. Use the Aston Vantage when the bonnet has a separate inner skin and hardware children.

### Gaps
- No Kunos stock car on disk opens its bonnet or tailgate, so there is no Kunos reference for those clips; mods are the only examples.
- Not checked whether the Nova's current `animations/` folder holds anything; a quick listing showed it empty. The Nova ext_config currently has only `[EMISSIVE_TURNSIGNAL_LEFT_0]`, `[EMISSIVE_TURNSIGNAL_RIGHT_0]` and `[EMISSIVE_REVERSE_0]`, so `EXTRA_A`…`F` are all free.
