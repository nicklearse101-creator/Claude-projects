# Export notes

Filled in 2026-10-12 from the working pipeline (Phase 1 used this instead of FBX + ksEditor).

## Pipeline
1. `blender/nova_gte.blend` is built by scripts in `blender/scripts/` (run headless:
   `blender -b blender/nova_gte.blend --python <script>`; each has a `build()`):
   `phase1_scene` (once: helpers, placeholder) -> `build_body` (shell + glass, from `body_geom.py` +
   `tools/photomatch/body_profile.json`) -> `build_front` (loads `blender/data/front_end.json`, `side_parts.json`,
   `rear_end.json`) -> `build_details`, `build_wheels`, `build_interior` -> `export_car`.
2. Generated parts come from plain-Python tools in `tools/` (`front_end.py`, `side_parts.py`, `wheel_face.py`,
   using `meshkit.py`), run with the project `.venv` (`.venv\Scripts\python.exe tools\front_end.py
   blender\data\front_end.json`, env `NOVA_ROOT=D:\Claude\vauxhall_nova_gte_1989`).
3. `export_car.export()` writes `car/vauxhall_nova_gte_1989/vauxhall_nova_gte_1989.kn5` and `collider.kn5` with
   `tools/ac_kn5_export.py` (the Sunbeam project's kn5 writer + glass blending). No FBX / ksEditor step.
4. `tools/build_car.py` writes `data/` from spec-sheet values; `tools/deploy.py` copies the package into AC.

## Conventions (as used and loading in AC)
- Blender: car faces -Y, Z up, +X = car's left, origin on the ground midway between the axles, metres.
- kn5: "sc6969" version 6 (+ extra int 781233 like Kunos files); AC space Y up, front +Z: (x, y, z) -> (x, z, -y),
  a proper rotation (winding kept); UV v stored negated; mesh nodes split at 65535 vertices; one node per material.
- Each Blender object becomes a dummy node with its local transform; mesh children per material. Objects with
  custom property `no_export` are skipped (cutters, collider hull, cameras).
- Helper nodes (empties): WHEEL_LF/RF/LR/RR and SUSP_LF/RF/LR/RR at the wheel centres, COCKPIT_HR, COCKPIT_LR,
  STEER_HR. Tyre/rim/disc meshes are children of WHEEL_xx (TIRE_xx with ksTyres, RIM_xx, DISK_xx - brakes.ini
  DISCS_GRAPHICS points at DISK_xx). Steering wheel mesh STEER_WHEEL is a child of STEER_HR. Gauge needles
  ARROW_SPEED / ARROW_RPM / ARROW_FUEL / ARROW_WATER (+ VOLT, OIL) for analog_instruments.ini.
- Materials: Blender material custom props `ac_shader` (ksPerPixel / ksPerPixelMultiMap / ksTyres) and `ac_preset`
  (paint, chrome, glass, trim, lens -> property sets in ac_kn5_export.PRESETS); colours become small embedded DDS
  swatches. Glass: `ac_blend` 1, `ac_alpha`.
- Collider: convex hull of a thinned copy of the evaluated shell (a few hundred triangles), material "GL".
- Exported collections: BODY (shell, glass), FRONT, SIDE, REAR, DETAILS, INTERIOR + the helper empties.
- Not yet verified against a stock car in ksEditor: LOD files, driver model/animations, lights.ini node names.
