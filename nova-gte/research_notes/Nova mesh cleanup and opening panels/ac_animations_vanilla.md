# Opening doors, bonnet and boot lid in vanilla Assetto Corsa (no CSP): files, formats, node naming, tooling

Research date: 2026-10-19. Where a source is a file on Nik's PC (Kunos SDK PDF, Kunos car files, acs.exe), the link is a `file:///` path. These are primary sources. Facts marked "measured" were read directly from real files with small Python parsers written for this research. Pages on overtake.gg (formerly RaceDepartment) returned HTTP 403 to the fetcher, so those threads are cited only from search-result snippets and flagged as such.

Key local sources used throughout:
- Kunos "Assetto Corsa Pipeline for Community Modders R2.0" (ships with the game SDK): [AC_Pipeline_PUB_Rev2.0.pdf](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf) (public mirror: [Scribd](https://www.scribd.com/document/501206878/AC-Pipeline-PUB-Rev2-0)). Below it is called "Kunos Pipeline R2.0".
- Content Manager / AcTools source: [gro-ove/actools](https://github.com/gro-ove/actools). Shallow-cloned locally to `D:\Claude\_scratch_research\actools` and read there.
- Real Kunos cars in `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ks_*` (129 Kunos cars installed, 857 cars total).

---

## 1. The .ksanim file format: binary layout, frame counts, playback, open-source readers and writers

### Takeaway
.ksanim is a very simple little-endian binary file. It holds an int32 version (1 or 2) and an int32 node count. Each node then has a length-prefixed name, an int32 frame count, and one full **local transform per frame**: a 4x4 matrix in v1, or quaternion + translation + scale in v2. There is no timing or fps field. Kunos door, light and wiper clips are v2 with 100 frames. The only complete open-source reader and writer found is AcTools (Content Manager), in C#. Writing ksanim straight from our own Blender exporter is easy and needs no third-party tool.

### Cited Findings
- **Header**: one int32 `Version`. AcTools reads it with `ReadInt32()`. — [KsAnimReader.cs](https://github.com/gro-ove/actools/blob/master/AcTools/KsAnimFile/KsAnimReader.cs); [KsAnimHeader.cs](https://github.com/gro-ove/actools/blob/master/AcTools/KsAnimFile/KsAnimHeader.cs)
- **Node count**: after the header comes an int32 entry count, then the entries. If version == 2 an entry is read as V2, otherwise as V1. Entries with zero frames are dropped. — [KsAnim.FromFile.cs](https://github.com/gro-ove/actools/blob/master/AcTools/KsAnimFile/KsAnim.FromFile.cs)
- **Per-node entry, v1**: `NodeName = ReadString()`, then int32 keyframe count, then that many `ReadMatrix()`. Each matrix is 16 consecutive float32 (64 bytes). — [KsAnimReader.cs](https://github.com/gro-ove/actools/blob/master/AcTools/KsAnimFile/KsAnimReader.cs); [ReadAheadBinaryReader.cs](https://github.com/gro-ove/actools/blob/master/AcTools/ReadAheadBinaryReader.cs)
- **Per-node entry, v2**: `NodeName = ReadString()`, int32 keyframe count, then for each keyframe `new KsAnimKeyframe(ReadQuat(), ReadVec3(), ReadVec3())`. That is rotation quaternion (4 float32), then translation ("Transition", 3 float32), then scale (3 float32): 40 bytes per frame. — [KsAnimReader.cs](https://github.com/gro-ove/actools/blob/master/AcTools/KsAnimFile/KsAnimReader.cs); [KsAnimEntry.cs](https://github.com/gro-ove/actools/blob/master/AcTools/KsAnimFile/KsAnimEntry.cs)
- **Strings**: `ReadString()` reads an int32 length and then that many bytes. This is the same string encoding as KN5. — [ReadAheadBinaryReader.cs](https://github.com/gro-ove/actools/blob/master/AcTools/ReadAheadBinaryReader.cs)
- **Quaternion order**: `ReadQuat()` reads 4 consecutive floats into `Quat(x, y, z, w)`. Measured: Kunos rest-pose frames read as (0, 0, 0, 1), which confirms w is last. — [ReadAheadBinaryReader.cs](https://github.com/gro-ove/actools/blob/master/AcTools/ReadAheadBinaryReader.cs); measured on [ks_mazda_miata car_door_L.ksanim](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_mazda_miata/animations/car_door_L.ksanim)
- **v2 to matrix**: CM builds each frame as `Matrix.Scaling(scale) * Matrix.RotationQuaternion(rotation) * Matrix.Translation(translation)`. This is the DirectX row-vector convention with translation in the 4th row, the same layout as KN5 node matrices. — [KsAnimExtension.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5Specific/Animations/KsAnimExtension.cs)
- **Writer**: `KsAnimWriter` writes the version int, the count, then each entry: name, frame count, and either the matrices (v1) or Rotation, Transition, Scale per frame (v2). CM's current default version is 2 (`KsAnimActualVersion = 2`). — [KsAnimWriter.cs](https://github.com/gro-ove/actools/blob/master/AcTools/KsAnimFile/KsAnimWriter.cs); [CommonAcConsts.cs](https://github.com/gro-ove/actools/blob/master/AcTools/CommonAcConsts.cs)
- **Size check (measured)**: ks_mazda_miata `car_door_L.ksanim` is v2 with 4 nodes (COCKPIT_HR, DOOR_L001, DOOR_L002, DOOR_L) of 100 frames each, and is 16,074 bytes. The layout predicts 4+4 + Σ(4+len(name)+4+100×40) = 8 + 34 + 16,032 = 16,074. That is an exact match, so the layout above is confirmed. — measured on [car_door_L.ksanim](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_mazda_miata/animations/car_door_L.ksanim)
- **Frames are full LOCAL transforms, not deltas (measured)**: Miata `DOOR_L` frame 0 has translation (0.789, 0.527, 0.536) and identity rotation. That is identical to the `DOOR_L` dummy's local matrix in `mazda_miata.kn5` (t = 0.789, 0.527, 0.536). — measured on [mazda_miata.kn5](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_mazda_miata/mazda_miata.kn5) and its car_door_L.ksanim
- **CM confirms the same convention when writing**: its "KsAnim switch generator" fills ksanim v1 frames with the KN5 node's own `.Transform` (the "show" frame) or a near-zero scale matrix (the "hide" frame). — [KsAnimSwitchGenerator.xaml.cs](https://github.com/gro-ove/actools/blob/master/AcManager/Pages/ContentTools/KsAnimSwitchGenerator.xaml.cs)
- **Frame counts in Kunos content (measured)**: across all `ks_*` cars, 113 of 115 `car_door_L/R` files are v2 with exactly 100 frames per node (2 have 101). All 28 `lights.ksanim` are v2 with 100 frames. 110 of 114 `car_wiper.ksanim` are v2 with 100 frames (4 have 101). — measured over `content/cars/ks_*/animations`
- **Both versions are used by Kunos (measured)**: 1,034 Kunos ksanim files are v2 and 8 are v1 (ks_ferrari_f138 steer/shift files, ks_praga_r1 car_shift, ks_stockcar_* steer). So the game reads both versions. Among mod cars on this PC: 1,971 v2 and 199 v1. — measured over `content/cars/*/animations`
- **Rotation magnitudes (measured)**: Miata `DOOR_L` rotates 65.0° about the parent's −Y (vertical) axis between the first and last frame. AE86 `DOOR_R_1` rotates 74.9°. Miata pop-up `HEADLIGHT_HB` rotates about X (lateral). — measured on ks_mazda_miata and ks_toyota_ae86 animations
- **Static nodes are included**: Kunos door clips also carry unchanging entries for parent nodes. Miata `car_door_L` has `COCKPIT_HR` with 100 identical frames, and AE86 `car_door_R` includes `COCKPIT_HR` as well. — measured on ks_mazda_miata and ks_toyota_ae86 car_door ksanims
- **How CM plays a clip**: each entry's node is found by name (`parent.GetDummyByName(entry.NodeName)`), and its `LocalMatrix` is overwritten every tick. Position 0..1 is mapped to `position * frameCount`, and the two neighbouring frame matrices are linearly blended. Entries with only 1 frame are skipped by default (`skipFixed`). Resetting restores the node's original KN5 transform. CM watches the .ksanim file and hot-reloads it when it changes. — [KsAnimAnimator.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5Specific/Animations/KsAnimAnimator.cs)
- **Playback modes (Kunos)**: "There are two types of pre-programmed playbacks: 1) Ping-pong … 2) Loop". "The specific naming conventions have a pre-programmed playback in-game, so the engine knows whether the playback should be LOOP or PING-PONG." — [Kunos Pipeline R2.0](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf), section 7 "Clips and naming conventions"
- **Durations come from ini files or engine defaults, not from the ksanim**: CM uses 1 s for both doors (`new AnimationBase("car_door_L.ksanim", 1f)`). Light animations take `TIME` from `lights.ini [LIGHT_ANIMATION_n]` (default 1). Wing animations take `TIME` (default 1). — [CarData.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Data/CarData.cs)
- **Other tools**: a "Blender ksanim/knh exporter 0.4" exists (overtake.gg thread "Misc Blender ksanim/knh exporter 0.4", seen only as a search result because the page returned 403). A user on assettocorsamods.net used it with Blender 2.91 and said it was made for 2.80/2.81. — [overtake.gg thread (403, title only)](https://www.overtake.gg/threads/blender-ksanim-knh-exporter.177330/); [assettocorsamods.net "FBX Animation" (3DCat, 10 Feb 2021)](https://assettocorsamods.net/threads/fbx-animation.2498/)
- The moppius Blender KN5 exporter and its older Hagn version do not export animations: "No support for skinned meshes (needed for animations)", and "Only geometry of mesh objects will be exported". — [Hagn's Blender Kn5 Exporter page](https://www.sites.google.com/site/hagn99/assettocorsa/blender-kn5-exporter); [moppius/blender-assetto-corsa-tools listing](https://awesome.ecosyste.ms/projects/github.com%2Fmoppius%2Fblender-assetto-corsa-tools)

### Inferences
- **Writer spec for our exporter.** Write the file little-endian as follows:
  - `int32 version=2`, `int32 nodeCount`.
  - For each node: `int32 len` + ASCII name, `int32 frameCount`.
  - Then per frame: `float32 qx,qy,qz,qw, tx,ty,tz, sx,sy,sz`.

  Or use v1 and write 16 float32 per frame in exactly the matrix layout `ac_kn5_export.py` already writes for KN5 dummies (`kn5_matrix()`); this avoids decomposing into quaternions. Both versions are read by the game, since Kunos ships both.
- **Each frame must be the node's local matrix relative to its KN5 parent**, built with the same Blender to AC axis conversion as the KN5 (AC: +Y up, +Z forward, +X = car's left; Miata DOOR_L sits at +X). Frame 0 of an "opening" clip should be bit-identical to the rest matrix written into the .kn5. Otherwise the part jumps when the clip first takes control. The 3DCat thread's "default state at the end of the animation" and "mesh vanishes" problems fit a mismatch between the clip and the KN5 rest pose or axes.
- **Use 100 frames to match Kunos.** The count is not mandatory, because playback is normalised 0..1 across however many frames exist. A plain rotation needs only a handful of frames (two would interpolate linearly in CM). Even so, 100 avoids the chord error of matrix lerp on large swings: CM blends matrices linearly rather than slerping quaternions, which shrinks the part mid-way between two distant keys.
- **Include only the nodes you intend to move.** Every listed node's local matrix is overwritten, so an entry for a node whose KN5 transform later changes would pin it to stale values.

### Gaps
- No primary source says how acs.exe itself interpolates between frames (slerp or matrix lerp) or what fps it assumes. CM's behaviour is documented above; the game's is not.
- The name encoding beyond ASCII is unverified. Keep names ASCII.
- The Blender "ksanim/knh exporter 0.4" source and download could not be retrieved (overtake.gg 403). No GitHub repository for it was found.

---

## 2. How animations are authored: ksEditor FBX import, the 3ds Max workflow, Blender workflows

### Takeaway
Kunos' own route is: animate dummies/nulls in 3ds Max, export an FBX containing only the animated nulls, then in ksEditor use File > Open FBX Animation with the car FBX loaded. ksEditor then writes `<fbxname>.ksanim` next to the FBX automatically. Blender modders either use the old ksanim exporter add-on or bake animation to FBX and go through ksEditor. Both routes have known axis and default-pose pitfalls. Because our pipeline writes .kn5 directly, the cleanest route for the Nova is to write .ksanim directly from Blender with the same transform code.

### Cited Findings
- Kunos ksEditor steps: "Open the car FBX in the editor. - Open the ANIMATION with the Open FBX Animation option under the File tab … When an animation is loaded it automatically saves a clip_name.ksanim file in the same folder where your FBX file is located, there is no need to manually export the animation clip." Also: "Every time you load an animation, a .ksanim file is saved with the same name as the source FBX. If your fbx is not named properly, you have to rename your clips to match our name conventions." — [Kunos Pipeline R2.0](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf), "Exporting animations from the editor"
- ksEditor has an "Animation" tab with a playback slider and a "Car Animations" tab with test sliders. — same source; also confirmed by UI strings in [ksEditor.exe](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/editor/ksEditor.exe) ("Open FBX Animation", "Animations", "Car Animations", `loadFBXAnimation`, `loadCarAnimations`)
- ksEditor's native library contains `FBXImporter.loadAnimation`, `Animation.save`, the string ".ksanim", the folder "/animations", and the error "Load Animation Failed, check the fbx version details : Importer->Initialize FAILED". ksEditor ships `fbxsdk-2014.1.dll`. — strings in [ksNet.dll](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/editor/ksNet.dll); file list of `sdk/editor`
- 3ds Max export rule: "The mesh must be scaled 1:1, rotation must be frozen on the mesh (reset Xform in 3DS Max) and objects should not have animated transformations. Only the dummies/nulls may have different transformations. When they are animated they can be rotated and scaled". The PDF gives separate FBX export settings "to export the base asset with no animation" and "to export animated nulls/dummies". — [Kunos Pipeline R2.0](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf), section 1b
- Driver clips are exported as separate FBX files containing only the animated parts. Kunos: "For every animation you must export a copy of the driver.fbx with ONLY the animated parts needed for the desired clip." — same source, "Driver animations"
- Door clips should animate the opening only: `car_door_R.ksanim` / `car_door_L.ksanim` are "PingPong … (the closing animation should be the open animation in reverse. Do not animate the closing sequence!)". `lights.ksanim` is "PingPong … Animate the opening sequence ONLY". `car_wiper.ksanim` is "Loop … animate the full animation back and forth". The PDF's car_door_L line says "right-hand side door", an obvious copy-paste typo. — same source, "Car animation clip names"
- Blender plus the FBX route (community): one modder "export[ed] as FBX (Selected objects only), bake animation, import into kseditor with the car, then extract the ksanim". The default state still came out wrong. With the ksanim exporter 0.4, "the animated parts default state is at the end of the animation rather than the start" and triggering it "makes the animated mesh vanish entirely". The poster then reported success with a two-level dummy hierarchy: `HEADLIGHTS` (empty) > `HEADLIGHTS_ANIM` (empty) > meshes. — [assettocorsamods.net "FBX Animation" (3DCat, Feb 2021)](https://assettocorsamods.net/threads/fbx-animation.2498/)
- Community summary (search snippet; page not fetchable): "export an fbx with each animation (just the empties that are animated), then after you've imported the main car's fbx, import the animation fbx using the menu option. It'll create a ksanim of the same name as your animation fbx." — [overtake.gg "ksEditor: how to create car_doorL.ksanim…" (403, snippet only)](https://www.overtake.gg/threads/kseditor-how-to-create-car_doorl-ksanim-and-other-ksanim-files.119403/)
- Axis pitfall: a modder's Blender-exported wiper ksanim worked in game, but the orientation was "flipped back 90 degrees away from the windshield". Importing only the empties as an FBX animation into ksEditor animated nothing. — [overtake.gg wiper thread (search snippet)](https://overtake.gg/threads/help-needed-wiper-animation-odd-texture-and-missing-bits.228877)
- A modder asked on assettocorsamods.net for the frame counts of car_door/car_wiper/wing clips. Nobody answered. The same poster described steer.ksanim as "200 frames in a loop" and shift clips as 20 frames. — [assettocorsamods.net "frame for animation objects" (denis370, Dec 2019)](https://assettocorsamods.net/threads/frame-for-animation-objects.1846/). The Kunos PDF confirms steer is 200 frames (frames 0/100/200 match).

### Inferences
- The ksEditor route needs the car loaded from FBX in ksEditor, with names and hierarchy matching. That does not fit our Blender to .kn5 exporter. Writing .ksanim directly is simpler and avoids the FBX axis and bake pitfalls listed above. Blender can still author the motion: keyframe the hinge empties, then let the exporter sample `matrix_local` per frame.
- The "flipped 90°" and "wrong default pose" reports are exactly what you get if the clip's frames are not converted with the same Z-up to Y-up basis change, or not with the same parent chain, as the KN5 nodes. A self-check is worth adding to our exporter: assert that ksanim frame 0 equals the KN5 local matrix for each animated node.

### Gaps
- The Kunos PDF's screenshots of the 3ds Max animation FBX export settings are images; their exact checkbox values were not extracted.
- No first-hand Blender 5.x ksanim workflow was found. Every community Blender report is from Blender 2.8–2.9.

---

## 3. Which data files reference animations in vanilla AC, and what vanilla can actually open (doors, bonnet, boot) vs CSP

### Takeaway
Vanilla AC recognises a fixed set of clip names in `animations/`: `car_door_L/R`, `lights`, `car_shift`, `car_shift_up/dw`, `car_steer_extra`, the suspension clips, driver `steer`/`shift`, and in the showroom also `car_wiper`. It also reads `data/wing_animations.ini`, which ties any custom-named clip to an aero WING's angle. **Vanilla has no dedicated bonnet or boot-lid animation slot and no in-game "open door" control** (no trigger found; see Gaps). The only vanilla way to make a bonnet or tailgate player-operable is the community trick of driving a clip from a dummy, aero-neutral WING whose angle is set in the pit setup menu. Proper keyboard/extra-switch control of doors, bonnet and boot needs CSP.

### Cited Findings
- **Engine-recognised car clip names (Kunos)**: `car_shift`, `car_susp_LF/LR/RF/RR` ("Controlled by engine"), `car_door_R`, `car_door_L`, `car_wiper`, `lights` (pop-up lights, "e.g. Ferrari F40"), `car_shift_up`, `car_shift_dw`. "The names listed above are recognized automatically and managed by the game engine." Kunos adds: "You can also use new names and then engage them from an .ini script (such as active DRS, wings etc.) … On certain cars we created animations called wing_rear.ksanim or wing_side.ksanim. These optional animations are managed from .ini scripts." — [Kunos Pipeline R2.0](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf), "Car animation clip names"
- **What acs.exe (the vanilla game) loads**: its strings include `/animations/lights.ksanim`, `/animations/car_shift_dw.ksanim`, `/animations/car_shift_up.ksanim`, `/animations/car_shift.ksanim`, `/animations/car_steer_extra.ksanim`, `/data/wing_animations.ini`, `/animations/car_door_L.ksanim`, `/animations/car_door_R.ksanim`, `/data/extra_animations.ini`, `/animations/steer.ksanim`, `/animations/shift.ksanim`, `shift_up`, `shift_dw`. A search for "wiper" found **no** string in acs.exe. Next to `wing_animations.ini` the strings `VERSION`, `FILE`, `/animations/`, `WING`, `INVERTED`, `SPEED` appear. Next to `extra_animations.ini` the strings `ROTATING_OBJECTS`, `AXIS`, `RPM` appear. — strings measured from [acs.exe](file:///D:/SteamLibrary/steamapps/common/assettocorsa/acs.exe)
- **What the vanilla Kunos showroom (acShowroom.exe) loads**: `/animations/car_door_L.ksanim`, `/animations/car_door_R.ksanim`, `/animations/lights.ksanim`, `/animations/car_shift.ksanim`, `/animations/car_wiper.ksanim`, `/data/wing_animations.ini` (with `ANIMATION_`, `NEXT`, `PREV`), `/data/extra_animations.ini`, `CINTURE_ON`, `USE_ANIMATED_SUSPENSIONS`, and the FMOD car sound event path pieces `event:/cars/` + `/door`. — strings measured from [acShowroom.exe](file:///D:/SteamLibrary/steamapps/common/assettocorsa/acShowroom.exe)
- **wing_animations.ini syntax (vanilla mechanism used by wings/DRS)**: sections `[ANIMATION_n]` with `WING=<aero.ini WING index>`, `FILE=<clip>.ksanim`, `MIN=<angle>`, `MAX=<angle>`. Optional `[HEADER] VERSION=2`, `NEXT=`, `SPEED=`, `TIME=`. Real example (js_fairlady_z32): `[ANIMATION_0] WING=0 FILE=car_wing.ksanim MIN=0 MAX=60 NEXT=1 SPEED=4`. Key usage across 49 local files: FILE/MIN/MAX 49, WING 43, SPEED 2, VERSION 1, NEXT 1. — measured from `content/cars/*/data/wing_animations.ini`; CM's parser reads `FILE`, `TIME` (default 1), `WING` (default 0), `NEXT`, `MIN` (default 0), `MAX` (default 60) — [CarData.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Data/CarData.cs)
- **Player-adjustable wing in the pit setup menu (vanilla setup.ini)**: example `[WING_2] SHOW_CLICKS=0 TAB=AERO NAME=Rear wing MIN=0 MAX=5 STEP=1 POS_X=0.5 POS_Y=6 HELP=HELP_REAR_WING`. — measured from [adc_bmw_e36_m3__420 setup.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/adc_bmw_e36_m3__420/data/setup.ini)
- **CM's own tool uses that trick**: "Generate .ksanim to use for a wing for hiding or showing geometry configurable in car setup menu." Its suggested config block (`[WING_BASED_SWITCH_...]`) is for CSP, but the clip itself is a normal wing animation. — [KsAnimSwitchGenerator.xaml / .cs](https://github.com/gro-ove/actools/blob/master/AcManager/Pages/ContentTools/KsAnimSwitchGenerator.xaml.cs)
- **Mods on this PC that animate bonnets/boots/doors do it through CSP, not vanilla**:
  - `btcc_1992_peugeot_405` and `btcc_1993_renault_19_s` have `wing_animations.ini` entries `WING=4 FILE=hood.ksanim MIN=0 MAX=100` and `WING=5 FILE=trunk.ksanim`, but their aero.ini only defines WING_0..2, so in vanilla those entries have nothing to drive them.
  - `ford_escort_mk2_tarmac` references `WING=6 FILE=hood_anim.ksanim` (no WING_6 exists) and actually drives the bonnet from CSP `ext_config.ini`: `[ANIMATION_1] FILE=hood_anim.ksanim TIME=1 BIND_TO_EXTRA_D=1`.
  - `gravygarage_oaktree_street_s13_tye_2023` drives `hood.ksanim` and `scissor_door_left/right.ksanim` with CSP `[ANIMATION_...]` + `BIND_TO_EXTRA_A/B`.

  — measured from those cars' `data/wing_animations.ini`, `data/aero.ini` and `extension/ext_config.ini` under [content/cars](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars)
- **Light animations**: `lights.ksanim` is engine-recognised (above). CM also reads `lights.ini [LIGHT_ANIMATION_n] FILE= TIME=` and always adds `lights.ksanim`. Real mod example: `[LIGHT_ANIMATION_0] FILE=lights.ksanim TIME=0.9`. — [CarData.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Data/CarData.cs); measured from [adc_corvette_c5_sd lights.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/adc_corvette_c5_sd/data/lights.ini)
- **extra_animations.ini**: real files on this PC hold `[ROTATING_OBJECT_n] NAME= RPM= AXIS=` (for example a kart clutch and BMW fans), which matches the vanilla acs.exe strings. CM additionally reads `[ANIMATION_n] FILE= TIME=` from this file as showroom "Extras". — measured from [acfl_gokart extra_animations.ini](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/acfl_gokart/data/extra_animations.ini); [CarData.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Data/CarData.cs)
- **driver3d.ini references clips**: `[STEER_ANIMATION] NAME=steer.ksanim LOCK=360`, `[SHIFT_ANIMATION] BLEND_TIME / POSITIVE_TIME / STATIC_TIME / NEGATIVE_TIME`. — [Kunos Pipeline R2.0](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf), "Driver scripts"
- **CSP (brief, covered in depth by the other researcher)**: car mods' doors are opened in CSP through "Extra Option A–D" bindings in the controls (user comment on a 911 GT3 CSP mod). The "Door opener" download binds `car_door_L/R.ksanim` to a controller button through `ext_config.ini` (search snippet). — [overtake.gg Porsche 911 GT3 2022 CSP features (user comment)](https://overtake.gg/downloads/porsche-911-gt3-2022-csp-features.43619/updates); [overtake.gg "Door opener" (403, snippet only)](https://www.overtake.gg/downloads/door-opener.31072/)
- **Nova package today (measured)**: `car/vauxhall_nova_gte_1989/animations/` contains only `.gitkeep`, so there is no ksanim at all, not even `steer.ksanim`, although `data/driver3d.ini` says `[STEER_ANIMATION] NAME=steer.ksanim`. `data/wing_animations.ini` holds only the comment "; filled in once the model has these nodes". `lights.ini` has `[LIGHT_0] [LIGHT_1] [BRAKE_0]`. An `extension/ext_config.ini` already exists. — [Nova car folder](file:///D:/Claude/vauxhall_nova_gte_1989/car/vauxhall_nova_gte_1989)

### Inferences
- **Doors (vanilla)**: shipping `animations/car_door_L.ksanim` and `car_door_R.ksanim` is the vanilla-standard, engine-recognised way. They are loaded by acs.exe and by the Kunos showroom, which also plays the car's FMOD `door` event. CM's showroom and CSP both use the same files, so authoring them is never wasted work.
- **Bonnet and tailgate (vanilla)**: there is no reserved clip name. The vanilla options are:
  - **(a) Setup-menu wing.** Add an aero-neutral `[WING_n]` in aero.ini (zero CL/CD LUTs), a `[WING_n]` in setup.ini (for example MIN=0 MAX=1 STEP=1, NAME=Bonnet), and `[ANIMATION_x] WING=n FILE=bonnet.ksanim MIN=0 MAX=1` in wing_animations.ini. Repeat with another wing for the tailgate. The panel then opens when the player changes the value in the pit setup screen. This is the same principle as CM's switch generator.
  - **(b) Leave them static in vanilla** and expose them through CSP extra switches. Our existing ext_config.ini already supports that (other researcher's scope).

  Option (a) is a hack: it adds setup items and its behaviour on track or online is untested.
- **Pop-up headlights** (not relevant to the Nova, but they show the mechanism): `lights.ksanim` plays automatically with the headlight switch. Do not repurpose it for the bonnet.
- The Nova's missing `steer.ksanim` is outside this task, but worth flagging to the main thread. acs.exe loads `/animations/steer.ksanim` per driver3d.ini, so the driver's steering animation probably does nothing today.

### Gaps
- **The in-game trigger for `car_door_L/R.ksanim` in vanilla acs.exe was not found.** The file is loaded (string present), and the Kunos PDF says the engine manages it as PingPong, but no source found says when vanilla plays it on track or in the pits. Whether the Kunos showroom (acShowroom.exe) exposes a door toggle in its UI was also not confirmed; only the file loads and the door sound event are evidenced.
- Whether vanilla acs.exe honours `lights.ini [LIGHT_ANIMATION_n]` and `extra_animations.ini [ANIMATION_n]` is unverified: those section names were not found next to the file-name strings in acs.exe. CM reads both, and CSP may.
- The semantics of the wing_animations keys `INVERTED`, `SPEED` and `NEXT`/`PREV` in vanilla are not documented by any source found. Only the string names and real-world uses are evidenced.
- The setup-menu-wing hack for a bonnet has not been tested in game or online. It is an inference from how wing animations work.

---

## 4. Node naming and hierarchy conventions for opening panels (hinge dummies, door children, LODs) and how .ksanim targets nodes

### Takeaway
Each opening panel needs its own **dummy (null) whose origin sits on the hinge axis**, with all the panel's meshes as children. The .ksanim entry names that dummy exactly and replaces its local matrix each frame. Kunos uses `DOOR_L`/`DOOR_R` for exterior doors and `DOOR_L_1`/`DOOR_R_1` for the interior door card under `COCKPIT_HR`. For bonnet and boot, `MOTORHOOD` and `REAR_HOOD` are Kunos' damage-pivot names, also placed at the hinge. Names must be unique.

### Cited Findings
- Kunos dummy names: "DOOR_L and DOOR_R for exterior door animation (A and B)", "DOOR_L_1 and DOOR_R_1 for interior door animation (A only)", "WIPER_# for wiper animation", "FRONT_LIGHT for headlight animation". Damage nulls "must be placed in the PIVOT point of the object around which the object rotates upon impact": FRONT_BUMPER, REAR_BUMPER, **MOTORHOOD**, **REAR_HOOD**, FRONT_WING, REAR_WING, REAR_EXTRACTOR. — [Kunos Pipeline R2.0](file:///D:/SteamLibrary/steamapps/common/assettocorsa/sdk/dev/car_pipeline_2.0rev/AC_Pipeline_PUB_Rev2.0.pdf), section 3a
- "The EDITOR will recognize these essential NULLs in order to define the rotation pivot of … any animatable object in the car. NOTE: Any object that is not a child of a NULL/DUMMY will be managed like part of the CAR CHASSIS." — same source, section 3
- LODs: "DOORS optional - only in LOD A if present on the model. In LOD B the doors are not animated but welded to the main body". Yet the dummy list says DOOR_L/R are "(A and B)". Separately: "LOD B must contain the same null hierarchy and names of animated nulls as LOD A for the exterior (suspension, wings, pop-up lights), but not for … the doors nulls under the Cockpit_HR null." MOTORHOOD "if needed, must be present in LOD A and LOD B". — same source (note the internal inconsistency about doors in LOD B)
- "The AC engine does not support 2 OBJECTS with the same NAME in the same model. This will cause the game to crash." — same source, section 1
- **Real Kunos hierarchy (measured, ks_mazda_miata `mazda_miata.kn5`)**:
  - Root `FBX: mazda_hr.FBX`.
  - Child `DOOR_L` dummy at t=(0.789, 0.527, 0.536), i.e. the front hinge, left side, with identity rotation. Its children are `door_left`, `windshield_left` (door glass), `door_left001`, `door_handle_left`, `mirror_left`, `sidemirror plastic rim_left`, `door_plastic_left`, `windshield_hr_int_left` and `DAMAGE_GLASS_LEFT_1`. Each mesh is a dummy with a same-named mesh child, e.g. `door_left` dummy > `door_left` mesh.
  - Interior: `COCKPIT_HR` > `DOOR_L001` dummy at the **same hinge position** (0.789, 0.527, 0.536) > `door left`, `GEO_door_rubber_L`. Also `COCKPIT_HR` > `DOOR_L002`.
  - `MOTORHOOD` dummy at (0, 0.801, 0.526), at the rear edge/cowl (the hinge line), with `GEO_Motorhood`, `GEO_EXT_BONNET_UNDERSIDE` and `ext_bonnet_plastic` as children.
  - Pop-up `HEADLIGHT_HB` dummy at (0, 0.700, 1.489) holds the lamp parts.

  — measured from [mazda_miata.kn5](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_mazda_miata/mazda_miata.kn5)
- **Matching ksanim (measured)**: Miata `car_door_L.ksanim` targets `COCKPIT_HR` (static), `DOOR_L001`, `DOOR_L002` and `DOOR_L` (each swinging 65°). `lights.ksanim` targets `HEADLIGHT_HB`. AE86 `car_door_R.ksanim` targets `COCKPIT_HR`, `DOOR_R_1`, `DOOR_R` and `DOOR_ARM_R` (a door check-arm rotating 32.7°). So **one clip moves the exterior door, the interior door card and linkages together**, all by name. — measured from ks_mazda_miata and ks_toyota_ae86 `animations/`
- AE86 `DOOR_R` and `COCKPIT_HR` carry a −90° X rest rotation (quaternion (−0.7071, 0, 0, 0.7071)), and `DOOR_R_1`'s swing axis is local Z. So the rotation axis in a clip is expressed in whatever the parent's local frame is. — measured from [ks_toyota_ae86 car_door_R.ksanim](file:///D:/SteamLibrary/steamapps/common/assettocorsa/content/cars/ks_toyota_ae86/animations/car_door_R.ksanim)
- Node lookup: CM resolves each ksanim entry with `GetDummyByName(entry.NodeName)` and changes only that node's `LocalMatrix`, so children follow through the hierarchy. — [KsAnimAnimator.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5Specific/Animations/KsAnimAnimator.cs)
- Community fix for a Blender-made clip: put a separate animation empty between the parent dummy and the meshes (`HEADLIGHTS` > `HEADLIGHTS_ANIM` > meshes). — [assettocorsamods.net "FBX Animation"](https://assettocorsamods.net/threads/fbx-animation.2498/)
- **Nova's current KN5 (measured)**: `ROOT` > `REF_BODY` (26 sub-meshes), plus detail dummies such as `DET_FRAME_DOOR_L`/`R`, `DET_LAMP_HEAD_DUMMY` etc. All dummies sit at (0, 0, 0) with world-space-positioned mesh children. No door, bonnet or tailgate is a separate hinged node yet. — measured from [vauxhall_nova_gte_1989.kn5](file:///D:/Claude/vauxhall_nova_gte_1989/car/vauxhall_nova_gte_1989/vauxhall_nova_gte_1989.kn5)

### Inferences
**Recommended Nova hierarchy (vanilla-compatible; CSP-ready).** Exported KN5 local matrices: hinge dummies at the hinge point, children re-expressed relative to them.

```
ROOT
├─ REF_BODY ...                     (shell with door, bonnet and hatch apertures)
├─ DOOR_L   (dummy @ left front hinge axis, identity rest rotation)
│   ├─ door skin, door glass, handle, mirror, window frame (DET_FRAME_DOOR_L), seals
├─ DOOR_R   (mirror of DOOR_L)
├─ MOTORHOOD (dummy @ bonnet hinge line; Nova bonnet hinges at the scuttle/rear edge)
│   └─ BONNET_ANIM? (optional inner empty if damage and animation must not fight; see Gaps)
│       └─ bonnet skin, underside, badge
├─ REAR_HOOD (dummy @ tailgate hinge line at the roof's rear edge)
│   └─ tailgate skin, rear glass, wiper, badge, spoiler
└─ COCKPIT_HR
    ├─ DOOR_L_1 (dummy @ same hinge as DOOR_L)  └─ interior door card, pull, winder
    └─ DOOR_R_1 (dummy @ same hinge as DOOR_R)  └─ ...
```

Clips to write into `animations/`:

- `car_door_L.ksanim` = entries {DOOR_L, DOOR_L_1}, 100 frames, 0° → ~65–70° about the AC vertical axis (Kunos Miata 65°, AE86 75°).
- `car_door_R.ksanim` = the same for the right side.
- `bonnet.ksanim` = {MOTORHOOD} (or the inner anim empty), rotating about the lateral X axis.
- `tailgate.ksanim` = {REAR_HOOD} (or the inner anim empty).

Only the door clips have engine-recognised names. Bonnet and tailgate need wing_animations.ini (vanilla hack) or CSP bindings.

Further points:
- Keep the hinge dummy's rest rotation at identity where possible (as Miata's `DOOR_L` does), so the clip is a pure rotation about one parent-frame axis. A tilted real hinge axis is still fine, because every frame is a full matrix.
- Keep names unique and ASCII. Animate only the dummies, not the meshes, as Kunos requires.
- A clip's node list must not include any node whose transform must stay free, such as parents. Kunos does include a static COCKPIT_HR entry, which is harmless only because the values equal the rest pose.
- LOD B and lower: weld doors into the body (Kunos practice), but keep any exterior animated null names consistent if bonnet or tailgate animation should also show in LOD B.

### Gaps
- No source says whether a MOTORHOOD/REAR_HOOD dummy that is both a damage pivot (damage.ini / colliders) and animated by a ksanim behaves well: the animation overwrites the local matrix that damage might also modify. Using an inner `*_ANIM` empty under the damage dummy is the cautious choice, but it is untested.
- Whether AC's node lookup is case-sensitive was not verified. File names of clips appear in mixed case in mods (`car_door_l` 86×, `CAR_DOOR_L` 37× on this PC), which works on Windows' case-insensitive filesystem.

---

## 5. How Content Manager's showroom / previews can open doors and play the other animations

### Takeaway
CM's Custom Showroom (and its previews generator) has its own ksanim player. It can open the left and right doors (fixed file names `car_door_L.ksanim` and `car_door_R.ksanim`, 1 s, with door sound), loop wipers (`car_wiper.ksanim`), play light animations, toggle each `wing_animations.ini` entry, and toggle each `extra_animations.ini [ANIMATION_n]` "extra". It hot-reloads the .ksanim when the file changes, which makes it the fastest test bench for our exported clips. None of this needs CSP.

### Cited Findings
- `CarData.GetLeftDoorAnimation()` returns `new AnimationBase("car_door_L.ksanim", 1f)`, and the right door uses `car_door_R.ksanim`. — [CarData.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Data/CarData.cs)
- `Kn5RenderableCar` exposes `LeftDoorOpen`/`RightDoorOpen` (animating to target 1 or 0) and `HasLeftDoorAnimation`/`HasRightDoorAnimation`, and calls `Sound?.Door(...)` on open and close (close sound offset 0.21 s). Wipers use `CreateAnimator(RootDirectory, "car_wiper.ksanim")` with `Loop`. There are `Wings` (wing_animations.ini) and `Extras` (extra_animations.ini) entries, with display names derived from the ksanim file name. — [Kn5RenderableCar.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5Specific/Objects/Kn5RenderableCar.cs)
- Preview settings carry `LeftDoorOpen`/`RightDoorOpen`, so CM-generated preview images can show doors open. — [CmPreviewsSettings.cs](https://github.com/gro-ove/actools/blob/master/AcManager/CustomShowroom/CmPreviewsSettings.cs); [DarkPreviewsOptions.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5SpecificForwardDark/DarkPreviewsOptions.cs)
- `KsAnimAnimator` watches the clip file (`SimpleDirectoryWatcher.WatchFile`) and reloads it on change. — [KsAnimAnimator.cs](https://github.com/gro-ove/actools/blob/master/AcTools.Render/Kn5Specific/Animations/KsAnimAnimator.cs)
- A GTPlanet user suggested removing the door animation from the animation folder while making previews to avoid open-door previews, which suggests some preview paths open doors by default (forum snippet). — [GTPlanet AC PC mods discussion (search snippet)](https://www.gtplanet.net/forum/threads/assetto-corsa-pc-mods-general-discussion.307899/post-14556926)

### Inferences
- **Test loop for the Nova**:
  1. Export the KN5 and the ksanim files.
  2. Open the car in CM's Custom Showroom and toggle Left/Right door, wings (for the bonnet/tailgate hack) or extras.
  3. Edit and re-export the ksanim. CM reloads it live without restarting.

  A clip that only "works in CM" proves the format and node names. In-game behaviour (vanilla wing hack, CSP bindings) still needs a session test.
- Putting bonnet/tailgate clips in `extra_animations.ini [ANIMATION_n] FILE=… TIME=…` gives CM showroom toggles for free. Whether vanilla acs.exe does anything with that section is unverified (see Q3 Gaps), so it costs nothing in vanilla.

### Gaps
- CM's exact UI labels and menu location for the door/wing/extra toggles were not checked: the XAML files were not fully reviewed and the CM UI was not opened.
