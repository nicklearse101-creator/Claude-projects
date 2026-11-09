# Ring-loft body-kit method (sills, arches, flares) - how the NICK3 side pieces were built

Written 2026-11-02 after the Escort Mk2 "NICK3 kit" one-piece side pieces (sill + front arch + rear arch). Use it for any
flared sill / wheel-arch / skirt work in Blender, e.g. the Vauxhall Nova GTE body kit. Source scripts live in
`D:\Claude\escort_mk2_dtm\tools\blender\` and a copy is in `D:\Claude\_tools\ring_loft_bodykit\`.

## Why this method
Hand-modelled or sculpted arches looked wobbly ("play doh"): waves of +-5 mm, unclear edges. A **ring loft** gives crisp,
controlled, perfectly regular surfaces: one fixed cross-section (a closed ring of 16 points) is swept along a path, and the
ring is only changed by tables the author controls. Everything is numbers, so it is repeatable, measurable and mirror-exact.

## The three pieces
1. **Sill = ring loft along Y** (`nick3_sill.py`). 16-point (x,z) ring (`MID`) is the flat middle section. Over |y| from `Y_BLEND`
   (0.62) to `Y_END_F/R` a smoothstep blends `MID` into an `END_F` / `END_R` ring. Ends are fitted to sit INSIDE the arch envelope.
2. **Arch = surface of revolution about the wheel axis** (`nick3_side.py`, `build_arch_bm`). One 16-point wedge ring per angle
   step theta (2.5 deg main, 4/7.5/15 deg for LOD B/C/D). Ring layout: 8 top-slope points, 5 soffit points, 3 buried points.
   Parameter tables per theta: `rl` lip radius (the wheel-hole circle, keep clear of the tyre), `rf` far radius, `xo` outer x,
   `xf` far-edge x on the body (`nick3_side_xfar.json`). `FIT_TOP/FIT_SOF/FIT_BUR` are the ring shape.
3. **Union** (`nick3_side_build.py`). Front arch U sill U rear arch with a Boolean EXACT modifier on temp objects, evaluated with
   `bpy.data.meshes.new_from_object`, giving ONE closed shell per side (checked: 0 boundary, 0 non-manifold, 1 shell).
   Right side = mirror (side=-1). Constant UV (one paint texel), `recalc_face_normals`.

## Front-end blend (the flare running onto the clip) - `FB`, `DRAPE`, `FARX`
- `FB`: the far (top) line leaves the r_far circle tangentially and follows a cubic Bezier to a chosen end point `E`;
  past the angle where the lip height equals E.z it runs forward at lip height.
- `FARX`: far-edge x is taken from the REAL body surface (ray cast, fender) minus 6 mm, so the edge sits inside the body (no flap).
- `DRAPE`: ring points hovering above the neighbouring part (clip top, found by ray cast) are eased down onto it (4 mm lip, 10 cm falloff)
  so the flare is flush, no ledge. `bs` shortens the buried ring part in the blend zone so nothing hangs free.
- Do not make rings collapse to zero thickness where they are exposed (that gave floating sheets and slivers).

## Workflow (what to do on a new car)
1. Measure first: wheel centres, tyre radius, body far-edge x along the arch (ray cast along -x), arch lip circle, outer edge of the
   neighbouring parts. Put the numbers in tables. Never judge by eye.
2. Build one ring-loft piece at a time, view close-ups both sides and from below, fix tables, rebuild (the script rebuilds all LODs in ~1 s).
3. Union, then verify: manifold/shell count, tyre clearance (`nick3_measure.clearance`), see-through ray tests with `scene.ray_cast`
   (skip excluded objects by looping), down-ray gap checks, and look at every join. Check both sides and every LOD.
4. Back up the blend before every rebuild; keep script backups (`.bak_vNN`).
5. Export with the kn5 exporter (`ac_kn5_export.export_kn5`) to a NEW staging folder, inspect with `kn5_inspect`, then install with backup + md5.

## Lessons / gotchas
- Do NOT build a bmesh BVH of many objects: it crashed Blender (60 s MCP timeout). Use `scene.ray_cast` loops or small per-object BVHs.
- The arch top slope limits how far the sill end can reach outboard: compute the arch envelope numerically at the sill end plane and clamp the END ring
  to it, instead of guessing (guessing left a flat end face sticking out).
- Keep the arch lip radius above tyre radius (rear tail once dipped under the tyre: 0.017 mm clearance). Check clearance after every table change.
- Boolean EXACT needs closed rings with end caps; open rings give non-manifold output.
- Stock parts left floating after removing a bumper (side marker lenses `Object016/017`) look like thorns: mark them `no_export` (the exporter skips them) rather than deleting.
- Blender MCP calls time out at 60 s; keep each call small. Namespace persists only in `bpy.app.driver_namespace`.
- Exact values used on the Escort (front arch centre -1.2177,.1481; rear 1.1924,.0921; lip r .295/.305; outer x ~.926) are in `nick3_side.py`; they are Escort numbers,
  NOT for the Nova - re-measure.

## Files
- `nick3_sill.py` (sill ring + `build_bm`), `nick3_side.py` (arch tables, ring, FB/DRAPE/FARX), `nick3_side_build.py` (union + LOD build + object creation),
  `nick3_side_xfar.json` (far-edge x tables), `nick3_measure.py` (tyre clearance), `ac_kn5_export.py`, `kn5_inspect.py`, `escort_scene.py` (scene/LOD helpers).
- Escort history: v31 one-piece sides, v32 front flare onto clip, side markers removed. Escort blend: `D:\Claude\escort_mk2_dtm\blender\escort_v27.blend`.

## Using it on the Nova
Copy `ring_loft_bodykit` scripts, change the module constants (wheel centres, tyre radius, table values, `MID/END` rings, LOD list, object/parent names in
`create_objects`) after measuring the Nova. The Nova shell is a single body, so replace the clip-specific `CLIPTOP` / `FARX` with ray casts against the Nova's
own shell. Follow the same checks.


## Update 2026-11-02 (v33): finish, material, tail
- **Smooth finish.** The kn5 exporter writes `me.corner_normals`, so flat-shaded bmesh faces came out faceted in game ("rectangles"). `nick3_side_build.smooth_bm` now sets
  every face smooth and marks only edges steeper than `CREASE_DEG` (40) as sharp. This is the biggest single fix; sampling density was not the problem.
- **Same material as the body.** The paint colour of the body is the skin-driven `AO_BODY.dds` in material `Material #25DQW` (shader ksPerPixelMultiMap + metal_detail.dds). The kit
  material NICK3_KIT_PAINT (own atlas + white detail map) read as plastic. `nick3_side_build.MATERIAL_NAME` now points at `Material #25DQW` and `nick3_side.UVT=(0.311,0.26)`
  is a flat paint texel of AO_BODY.dds (0.898-0.941 grey in both the stock and skin textures). Do NOT use `STOCK_Material #25DQW` (embedded stock texture, not skin-driven).
- **Tail taper.** `ARCH['rear']['tail']=(span,rf_end,xo_end)`: over the last `span` degrees of the arch the ring shrinks to a tiny closed tip instead of ending in a flat cap. Only the
  last ~10 deg of the rear tail moved (72 vertices, max 32 mm at the very tip; measured against the v33a blend).
- One closed shell per side is unchanged (Boolean EXACT union); with smooth normals the sill/arch joins read as one surface. A geometric blend of the join zones was not needed.
