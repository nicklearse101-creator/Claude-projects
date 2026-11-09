# Scripting car-mesh shading clean-up in bpy (Blender 4.1+ / 5.x) and how normals/tangents behave in Assetto Corsa .kn5

Scope note: API facts below come from the Blender 5.2 API reference (docs.blender.org/api/current reports version 5.2), Blender release notes 4.1 to 5.1, and Blender `main` source. Several claims were also checked by a headless test in **Blender 5.2.1 LTS** on a 1,310,720-triangle mesh (655,362 verts, 3,932,160 corners). The script and raw output are saved next to this file: `bench_normals_blender52.py` and `bench_normals_blender52_results.txt` (cited below as "local test"). The test mesh was a noisy ellipsoid (4 m x 2 m x 1.4 m, 0.4 mm positional noise), not the Nova body, so absolute timings are indicative only.

## Q1. Data Transfer of custom normals from a script, applying it, and what changed in Blender 4.1+

### Takeaway
In 4.1+ you no longer need Auto Smooth: add a `DATA_TRANSFER` modifier with `use_loop_data=True`, `data_types_loops={'CUSTOM_NORMAL'}`, pick a `loop_mapping`, and either apply it (`bpy.ops.object.modifier_apply` under `bpy.context.temp_override(...)` works headless) or bake the whole stack with `bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)`. The transfer reads the source's `corner_normals` and writes the destination's `custom_normal` attribute as **INT16_2D on CORNER** (the old "corner fan space" encoding). The modifier leaves that attribute alone if it already exists as a FLOAT_VECTOR "free" normal.

### Cited Findings
**4.1 normals API changes (all still valid in 5.x):**
- `Mesh.use_auto_smooth` was removed. Face-corner normals are now used automatically when smooth and flat-shaded faces are mixed, and meshes always use custom normals if they exist. — [Blender 4.1 Python API notes](https://developer.blender.org/docs/release_notes/4.1/python_api/)
- `Mesh.auto_smooth_angle` was removed. The notes say it was "Replaced by a modifier (or operator) controlling the "sharp_edge" attribute". The mesh itself no longer knows anything about smoothing by angle. — [Blender 4.1 Python API notes](https://developer.blender.org/docs/release_notes/4.1/python_api/)
- `create_normals_split`, `calc_normals_split` and `free_normals_split` were removed and replaced by the `Mesh.corner_normals` collection, which updates automatically. `MeshLoop.normal` became read-only. Custom normals must be set with `normals_split_custom_set` or `normals_split_custom_set_from_vertices`. — [Blender 4.1 Python API notes](https://developer.blender.org/docs/release_notes/4.1/python_api/)
- The base state of a mesh is now the same as the old "Auto Smooth on at 180°". Blender chooses vertex, face or face-corner normals automatically. In Edit Mode the operator is "Set Sharpness by Angle"; in other modes it is "Shade Smooth by Angle". — [Blender 4.1 Modeling notes](https://developer.blender.org/docs/release_notes/4.1/modeling/)
- The Auto Smooth option was replaced by a modifier node-group asset ("Smooth by Angle"). — [Blender 4.1 Nodes & Physics notes](https://developer.blender.org/docs/release_notes/4.1/nodes_physics/)

**Current (5.2) `bpy.types.Mesh` members:**
- `corner_normals`: `bpy_prop_collection[MeshNormalValue]`, read-only. Each face corner's split normal, "influenced by vertex normals, sharp faces, sharp edges and custom normals"; it may be empty. — [bpy.types.Mesh](https://docs.blender.org/api/current/bpy.types.Mesh.html)
- `has_custom_normals` (bool, read-only). `normals_domain` (read-only, `'POINT'|'FACE'|'CORNER'`): "the attribute domain that gives enough information to represent the mesh's normals". `vertex_normals` and `polygon_normals` are also available. — [bpy.types.Mesh](https://docs.blender.org/api/current/bpy.types.Mesh.html)
- `normals_split_custom_set(normals)` takes per-corner normals, and `normals_split_custom_set_from_vertices(normals)` takes per-vertex normals. In both, zero vectors mean "keep the automatic normal". — [bpy.types.Mesh](https://docs.blender.org/api/current/bpy.types.Mesh.html)
- `set_sharp_from_angle(*, angle=π)` "Resets and fills the "sharp_edge" attribute" from the face angle across manifold edges. `shade_smooth()` removes the `sharp_face` attribute, and `shade_flat()` sets `sharp_face` True on every face. `calc_tangents(*, uvmap='')`, `free_tangents()`, `calc_loop_triangles()` and `validate()` are also available. — [bpy.types.Mesh](https://docs.blender.org/api/current/bpy.types.Mesh.html)
- Operators: `bpy.ops.object.shade_smooth_by_angle(angle=0.523599, keep_sharp_edges=True)` and `bpy.ops.object.shade_auto_smooth(use_auto_smooth=True, angle=0.523599)`. The second one "add[s] modifier to automatically set the sharpness of mesh edges". — [bpy.ops.object](https://docs.blender.org/api/current/bpy.ops.object.html)

**Custom normal storage (4.5+):**
- Commit d3f84449ad ("Mesh: Add "free" custom normals") added a "dumb vector" storage option using the **"custom_normal" attribute**. These normals are direction vectors in object local space, stored on vertices, faces or face corners, alongside the existing "smooth corner fan space" storage. Free normals are adjusted for whole-mesh transforms "but in general they're not updated for vertex deformations". The existing custom-normal editing operators did not work with free normals at that time. — [Blender commit d3f84449ad](https://projects.blender.org/blender/blender/commit/d3f84449ad)
- Release notes: a "free" custom normal storage format was added, and it "can be significantly faster than the existing "Tangent Space" storage mode". The Set Mesh Normal geometry node can edit both formats. — [4.5 Modeling](https://developer.blender.org/docs/release_notes/4.5/modeling/); [4.5 Geometry Nodes](https://developer.blender.org/docs/release_notes/4.5/geometry_nodes/)
- Source: the corner-fan format is declared as `AttributeMetaData{AttrDomain::Corner, AttrType::Int16_2D}`. `Mesh::normals_domain()` returns the domain of an existing `custom_normal` attribute. — [mesh_normals.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/blenkernel/intern/mesh_normals.cc)
- Local test: after `normals_split_custom_set_from_vertices`, `me.attributes["custom_normal"]` is `('INT16_2D', 'CORNER')`, `has_custom_normals=True` and `normals_domain='CORNER'`. — local test (`bench_normals_blender52_results.txt`)

**Data Transfer modifier API (5.2):**
- `data_types_loops` takes a set of `'CUSTOM_NORMAL'`, `'COLOR_CORNER'` and `'UV'`, and `use_loop_data` (default False) must be True. `data_types_edges` takes `'SHARP_EDGE'`, `'SEAM'`, `'CREASE'`, `'BEVEL_WEIGHT_EDGE'` and `'FREESTYLE_EDGE'`. `data_types_polys` takes `'SMOOTH'` and `'FREESTYLE_FACE'`. — [bpy.types.DataTransferModifier](https://docs.blender.org/api/current/bpy.types.DataTransferModifier.html)
- Other properties: `object` (source), `use_object_transform` (default True, evaluates source and destination in world space), `loop_mapping` (default `'NEAREST_POLYNOR'`), `mix_mode` (default `'REPLACE'`), `mix_factor` [0,1], `vertex_group`, `invert_vertex_group`, `use_max_distance`/`max_distance` (default 1.0), `ray_radius` (default 0.0) and `islands_precision`. — [bpy.types.DataTransferModifier](https://docs.blender.org/api/current/bpy.types.DataTransferModifier.html)
- `loop_mapping` items:
  - `TOPOLOGY`: identical topology only.
  - `NEAREST_NORMAL`: nearest corner with the best matching normal.
  - `NEAREST_POLYNOR`: nearest corner whose face normal best matches.
  - `NEAREST_POLY`: nearest corner of the nearest face.
  - `POLYINTERP_NEAREST`: "interpolated corners of the nearest source face".
  - `POLYINTERP_LNORPROJ`: interpolated corners of the source face hit by projecting along the corner normal.
  — [Dt Method Loop Items](https://docs.blender.org/api/current/bpy_types_enum_items/dt_method_loop_items.html)
- `mix_mode` items: `REPLACE`, `ABOVE_THRESHOLD`, `BELOW_THRESHOLD`, `MIX`, `ADD`, `SUB`, `MUL`. — [Dt Mix Mode Items](https://docs.blender.org/api/current/bpy_types_enum_items/dt_mix_mode_items.html)
- The manual says Mix Factor interpolates between the original and the new value, and a Vertex Group "allows per-element control of the Mix Factor". Lower `ray_radius` is more accurate but can be slower; the manual suggests "a low radius for dense source meshes". Topology mapping is "best suited for a destination mesh that's a deformed copy of the source". — [Manual: Data Transfer Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/data_transfer.html)
- Conflict: the API reference lists `mix_factor` "default 0.0", but the modifier's `init_data()` sets `mix_factor = 1.0f`, `mix_mode = CDT_MIX_TRANSFER` (REPLACE) and `lmap_mode = MREMAP_MODE_LOOP_NEAREST_POLYNOR`. The local test confirms that a new modifier reports `mix_factor=1.0`. — [MOD_datatransfer.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/modifiers/intern/MOD_datatransfer.cc); local test
- Source behaviour:
  - The transfer reads the source's evaluated `corner_normals()`, so the source's own sharp edges and custom normals count.
  - If `mix_factor != 1` or a vertex group is used, it starts from the destination's current `corner_normals()`.
  - It then bakes the result with `normals_corner_custom_set(...)` into `lookup_or_add_for_write_span<short2>("custom_normal", Corner)`, using the destination's `sharp_face` and a writable `sharp_edge` span.
  - If that typed lookup fails, it returns without changing anything.
  - Source comment: "no islands precision for now here", so `islands_precision` does nothing in the modifier.
  — [data_transfer.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/blenkernel/intern/data_transfer.cc); [MOD_datatransfer.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/modifiers/intern/MOD_datatransfer.cc)

**Applying from a script:**
- Signature: `bpy.ops.object.modifier_apply(*, modifier='', report=False, merge_customdata=True, single_user=False, all_keyframes=False, use_selected_objects=False)`. `merge_customdata` means "Merge UVs ... that share a vertex to account for imprecision in some modifiers". — [bpy.ops.object](https://docs.blender.org/api/current/bpy.ops.object.html)
- `Context.temp_override(*, window=None, screen=None, area=None, region=None, **keywords)` is a context manager; its keyword arguments override context members such as `active_object`. — [bpy.types.Context](https://docs.blender.org/api/current/bpy.types.Context.html)
- `BlendDataMeshes.new_from_object(object, *, preserve_all_data_layers=False, depsgraph=None)` returns the final evaluated geometry when given an evaluated object. By default it computes only the layers needed for display and render, so pass `preserve_all_data_layers=True` and `depsgraph` to keep UV maps, vertex groups and the rest. `Object.to_mesh()` is the temporary, object-owned version (free it with `to_mesh_clear()`). — [bpy.types.BlendDataMeshes](https://docs.blender.org/api/current/bpy.types.BlendDataMeshes.html); [bpy.types.Object](https://docs.blender.org/api/current/bpy.types.Object.html)
- Local test, background mode, Blender 5.2.1:
  - Both methods worked headless.
  - `with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]): bpy.ops.object.modifier_apply(modifier=m.name, merge_customdata=False)` returned `{'FINISHED'}` in 2.6 s at 1.31M tris.
  - The `new_from_object` swap also worked.
  - After either, `custom_normal` stayed `INT16_2D/CORNER`.
  — local test

**Free-normal pitfall (verified):**
- The Weighted Normal modifier asks for `lookup_or_add_for_write_span<short2>("custom_normal", Corner)` and returns the mesh unchanged if that fails (`if (!clnors) return result;`). — [MOD_weighted_normal.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/modifiers/intern/MOD_weighted_normal.cc)
- Local test on a mesh whose `custom_normal` is FLOAT_VECTOR/CORNER (free normals):
  - The Weighted Normal modifier changed nothing.
  - `normals_split_custom_set_from_vertices()` also changed nothing.
  - Neither raised an error.
  — local test

### Inferences
- **Recipe: transfer custom normals from a smoothed proxy, headless.** Verified pattern from the local test:
  ```python
  import bpy
  body = bpy.data.objects["body"]; proxy = bpy.data.objects["body_proxy"]
  # 0) guard: the transfer writes INT16_2D corner normals; a FLOAT_VECTOR 'custom_normal' makes it a silent no-op
  a = body.data.attributes.get("custom_normal")
  assert a is None or a.data_type == 'INT16_2D', a.data_type
  body.data.shade_smooth()                       # clears sharp_face; keep panel-gap sharp_edge marks as wanted
  dt = body.modifiers.new("NormalsFromProxy", 'DATA_TRANSFER')
  dt.object = proxy
  dt.use_object_transform = True                 # proxy sits at the same world transform
  dt.use_loop_data = True
  dt.data_types_loops = {'CUSTOM_NORMAL'}
  dt.loop_mapping = 'POLYINTERP_NEAREST'         # smooth interpolation; 'NEAREST_POLYNOR' is ~1.7x faster
  dt.mix_mode = 'REPLACE'; dt.mix_factor = 1.0   # set explicitly (API doc default disagrees with source)
  dt.vertex_group = "paint_only"                 # optional: weight = per-corner mix factor
  # dt.use_max_distance = True; dt.max_distance = 0.002   # ignore far matches (e.g. across panel gaps)
  with bpy.context.temp_override(object=body, active_object=body,
                                 selected_objects=[body], selected_editable_objects=[body]):
      bpy.ops.object.modifier_apply(modifier=dt.name, merge_customdata=False)
  # or apply the whole stack without operators:
  # dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg)
  # me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
  # old = body.data; body.modifiers.clear(); body.data = me; bpy.data.meshes.remove(old)
  ```
- The transfer copies the proxy's corner normals including its sharp edges. If the proxy carries the body's old (noisy) INT16_2D custom normals, you transfer the noise back. Remove `proxy.data.attributes["custom_normal"]` (or clear custom normals) on the proxy first, so its own smooth vertex normals are used. The local test did this for every proxy.
- `merge_customdata=False` is the safer choice when applying, so UVs are not welded by the "imprecision" merge. Normal transfer does not change UVs, so there is nothing to merge.
- `modifier_apply` runs on original data. A multi-user mesh needs `single_user=True` or a unique copy first.
- **INT16_2D custom normals are stored relative to the automatic fan normal.** Changing topology or sharpness after setting them changes the final normals. Examples: re-triangulating, adding a Smooth by Angle modifier later in the stack, or calling `set_sharp_from_angle`. See the triangulation test in Q5. Do the clean-up last, after geometry and sharp edges are final.
- Because `normals_corner_custom_set` receives a writable `sharp_edge` span, transfer and weighted-normal operations can add `sharp_edge` marks where the new normals need a split fan. Re-check sharp edges after applying if the exporter or later steps rely on them. This is an inference from the source signature; it was not measured.
- Order the stack Shrinkwrap -> (sharpness: `set_sharp_from_angle` or Smooth by Angle) -> Data Transfer *or* Weighted Normal. Weighted Normal without a vertex group recomputes every corner and overwrites earlier custom normals (see Q3).

### Gaps
- No official statement on whether `custom_normal` stored on a `sharp_face=True` face changes the final normal. The source shows sharp faces "implicitly cause sharp edges" in fan computation, which suggests one fan per corner. Keeping painted panels `shade_smooth()` avoids the question.
- The API reference `mix_factor` "default 0.0" versus `init_data` 1.0 discrepancy is not explained anywhere I found. Always set it explicitly.

## Q2. Building a smoothed proxy in a script, and which methods preserve panel creases

### Takeaway
For a 1M+ triangle body, fast smoothers work well: `CORRECTIVE_SMOOTH` with `use_only_smooth=True` (0.4 s for 20 iterations) or a `bmesh.ops.smooth_vert` loop (1.7 s for 10 iterations). The `LAPLACIAN_SMOOTH` modifier is impractically slow at this size (about 100 s per iteration). All of these are restricted per vertex (vertex group, or the `verts=` list for bmesh). That restriction is how you protect creases and shut lines. Subdivision and Remesh are a poor fit at 1.2M triangles.

### Cited Findings
- `CorrectiveSmoothModifier` properties:
  - `factor` (default 0.5) and `iterations` (default 5).
  - `smooth_type` `'SIMPLE'` or `'LENGTH_WEIGHTED'`.
  - `use_only_smooth`, "Apply smoothing without reconstructing the surface".
  - `use_pin_boundary`, "Excludes boundary vertices from being smoothed".
  - `rest_source` `'ORCO'` or `'BIND'`, and `vertex_group`/`invert_vertex_group`.
  — [bpy.types.CorrectiveSmoothModifier](https://docs.blender.org/api/current/bpy.types.CorrectiveSmoothModifier.html)
- Manual: Length Weight "can give higher quality smoothing in some cases, by better preserving the shape of the original form". Factor values outside 0-1 distort the mesh. Pin Boundaries "Prevent[s] boundary vertices from smoothing". — [Manual: Smooth Corrective](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/corrective_smooth.html)
- `LaplacianSmoothModifier` properties: `iterations` (default 1), `lambda_factor` (0.01), `lambda_border` (0.01), `use_volume_preserve` (True), `use_normalized` (True), `use_x/y/z`, and `vertex_group`. — [bpy.types.LaplacianSmoothModifier](https://docs.blender.org/api/current/bpy.types.LaplacianSmoothModifier.html)
- bmesh smoothers:
  - `bmesh.ops.smooth_vert(bm, verts=[], factor=0, mirror_clip_x/y/z=False, clip_dist=0, use_axis_x/y/z=False)` is basic averaging. The axis flags default to False, so set them all True or nothing moves.
  - `bmesh.ops.smooth_laplacian_vert(bm, verts=[], lambda_factor=0, lambda_border=0, use_x/y/z=False, preserve_volume=False)` is Desbrun implicit fairing.
  - Both act only on the `verts` you pass.
  — [bmesh.ops](https://docs.blender.org/api/current/bmesh.ops.html)
- Local test at 1.31M tris (655k verts). Noise metric = mean angle between corner normals and the analytic ellipsoid normal; the noisy input was 2.77°:
  - `CORRECTIVE_SMOOTH` x20, `use_only_smooth=True`, `LENGTH_WEIGHTED`, factor 0.5: applied in **0.39 s**, result 0.50°.
  - `bmesh.ops.smooth_vert` x10, factor 0.5: **1.73 s**, plus `from_mesh` 0.39 s and `to_mesh` 0.12 s; result 0.32°.
  - `LAPLACIAN_SMOOTH` x2, lambda 1.0, volume preserve: **198.8 s**, result 1.50°.

  An earlier run at 327k tris took 73 s for 10 Laplacian iterations. — local test
- Local test: after `bm.to_mesh()` the proxy still carried the body's INT16_2D `custom_normal`. bmesh round-trips the attribute. — local test

### Inferences
- **Recipe: crease-aware proxy.**
  ```python
  proxy = body.copy(); proxy.data = body.data.copy(); proxy.name = "body_proxy"
  bpy.context.scene.collection.objects.link(proxy)
  if "custom_normal" in proxy.data.attributes:            # use the proxy's own smooth normals
      proxy.data.attributes.remove(proxy.data.attributes["custom_normal"])
  # protect creases: vertex group = everything EXCEPT verts on sharp edges / near shut lines
  m = proxy.modifiers.new("cs", 'CORRECTIVE_SMOOTH')
  m.use_only_smooth = True; m.smooth_type = 'LENGTH_WEIGHTED'
  m.factor = 0.5; m.iterations = 20; m.use_pin_boundary = True
  m.vertex_group = "smooth_ok"                              # weight 0 / absent on crease rows
  ```
  bmesh equivalent: `bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not any(not e.smooth for e in v.link_edges)], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)` in a loop. `BMEdge.smooth == False` marks a sharp edge.
- **Crease preservation:**
  - Corrective Smooth's `use_pin_boundary` keeps open boundary loops fixed. If panel gaps are modelled as real holes or separate shells, that protects the gap edges.
  - Creases inside a continuous surface (swage lines, arch lips) must be excluded through the vertex group or the `verts` list. Otherwise the proxy rounds them and the transferred normals soften the crease in AC's reflections.
  - Combine with `use_max_distance` on the Data Transfer, so corners across a gap do not pick up the other panel.
- Corrective Smooth with `use_only_smooth=False` reconstructs the surface toward the rest shape. That is the opposite of what a proxy needs, so keep `use_only_smooth=True`.
- Subdivision Surface would quadruple 1.2M triangles to about 4.8M per level. Voxel Remesh needs a voxel smaller than the panel gaps (millimetres) to keep them, at a huge triangle count. Neither suits a proxy at this size; use them only on a cut-out region. This is inference; neither was benchmarked.
- Positional smoothing shrinks convex areas slightly. A proxy only lends normals, so this hardly matters, but with `NEAREST_*` mappings a large shrink moves the "nearest" match. Keep iterations modest, or Shrinkwrap the proxy back onto the body (Q4) before transferring.

### Gaps
- No source or benchmark found for how well each smoother keeps true curvature on car panels specifically. The noise metric above is synthetic.
- `bmesh.ops.smooth_laplacian_vert` was not timed.

## Q3. Weighted Normal modifier from a script and how it interacts with custom normals

### Takeaway
`WEIGHTED_NORMAL` (`mode` FACE_AREA / CORNER_ANGLE / FACE_AREA_WITH_ANGLE, `weight` 1-100 with 50 neutral, `thresh`, `keep_sharp`, `use_face_influence`, `vertex_group`) writes INT16_2D corner custom normals. It needs no Auto Smooth in 4.1+ and runs in about 0.7-1.3 s at 1.31M tris. Without a vertex group it replaces every existing custom normal. With a vertex group, corners outside the group keep their current normals, including transferred ones.

### Cited Findings
- `WeightedNormalModifier` properties:
  - `mode` is `'FACE_AREA'` (default), `'CORNER_ANGLE'` or `'FACE_AREA_WITH_ANGLE'`.
  - `weight` int [1,100], default 50 ("50 is neutral").
  - `thresh` [0,10], default 0.01.
  - `keep_sharp` (default False): "Keep sharp edges as computed for default custom normals, instead of setting a single weighted normal for each vertex".
  - `use_face_influence` (default False).
  - `vertex_group` and `invert_vertex_group`.
  — [bpy.types.WeightedNormalModifier](https://docs.blender.org/api/current/bpy.types.WeightedNormalModifier.html)
- Manual: Weight works "a bit like a contrast setting". Keep Sharp preserves sharp edges, "though smoothing will still happen if there are multiple faces between any two Sharp edges". Face Influence uses face strengths set by the Set Strength tool or the Bevel modifier. The modifier changes the mesh's custom normals. — [Manual: Weighted Normal Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/normals/weighted_normal.html)
- 4.2 moved Normal Edit and Weighted Normal into a new "Normals" modifier menu. This is a UI change only; the type identifier stays `'WEIGHTED_NORMAL'`. — [Blender 4.2 Modeling notes](https://developer.blender.org/docs/release_notes/4.2/modeling/)
- Source:
  - The modifier writes `"custom_normal"` as `short2` on `AttrDomain::Corner` and uses/creates `"sharp_edge"`.
  - Without a vertex group it sets all corners via `normals_corner_custom_set_from_verts`.
  - With a vertex group it first computes the current corner normals (including existing custom normals). It then overwrites only the corners whose vertex got a non-zero weighted normal, so out-of-group corners keep their existing values.
  - Group membership is tested with `BKE_defvert_find_index(...) != nullptr`, i.e. membership, not weight.
  — [MOD_weighted_normal.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/modifiers/intern/MOD_weighted_normal.cc)
- Local test at 1.31M tris: FACE_AREA with keep_sharp evaluated in 0.70 s; CORNER_ANGLE with keep_sharp in 1.30 s. New-modifier defaults were mode FACE_AREA, weight 50, thresh 0.01, keep_sharp False. — local test

### Inferences
- **Recipe:**
  ```python
  wn = body.modifiers.new("WN", 'WEIGHTED_NORMAL')
  wn.mode = 'FACE_AREA'; wn.weight = 50; wn.thresh = 0.01
  wn.keep_sharp = True            # respect panel-gap sharp_edge marks
  wn.vertex_group = ""            # "" = whole mesh (overwrites any transferred normals!)
  ```
  Then apply as in Q1.
- On a dense, fairly uniform scan- or AI-generated body, area weighting changes little: all faces are similar in size. Weighted Normal mainly helps low-poly hard-surface parts (bevelled edges next to big flats). For noisy dense paint, Data Transfer from a smoothed proxy is the stronger tool. Weighted Normal cannot remove noise, because it only re-weights the noisy face normals. Use one or the other on a region, not both stacked over the whole mesh.
- Because membership (not weight) drives the vertex group, a group with 0-weight members still counts those vertices as affected. Remove vertices from the group rather than painting 0.

### Gaps
- No benchmark of `FACE_AREA_WITH_ANGLE` or `use_face_influence` at this size; expect similar or slightly higher cost than CORNER_ANGLE.

## Q4. Shrinkwrap projection of a clean mesh onto the original

### Takeaway
`SHRINKWRAP` exposes `wrap_method` (NEAREST_SURFACEPOINT default, PROJECT, NEAREST_VERTEX, TARGET_PROJECT), `wrap_mode` (ON_SURFACE default, INSIDE, OUTSIDE, OUTSIDE_SURFACE, ABOVE_SURFACE), `offset`, and `project_limit` / axis / cull options. TARGET_PROJECT gives the smoothest result; the manual calls it "significantly slower". It moves vertices only. Normals then follow the new geometry, plus any fan-relative custom normals, so transfer or recompute normals after it.

### Cited Findings
- `ShrinkwrapModifier` properties:
  - `target`, `auxiliary_target`.
  - `wrap_method` (default `'NEAREST_SURFACEPOINT'`) and `wrap_mode` (default `'ON_SURFACE'`).
  - `offset` (default 0.0), `project_limit` (0 = off) and `subsurf_levels` [0,6].
  - `use_project_x/y/z`, `use_negative_direction` (default False), `use_positive_direction` (default True).
  - `cull_face` (default `'OFF'`), `use_invert_cull`, and `vertex_group`/`invert_vertex_group`.
  — [bpy.types.ShrinkwrapModifier](https://docs.blender.org/api/current/bpy.types.ShrinkwrapModifier.html)
- `wrap_method` items: `NEAREST_SURFACEPOINT`, `PROJECT` ("along a given axis"), `NEAREST_VERTEX` and `TARGET_PROJECT` ("along the interpolated vertex normals of the target"). — [Shrinkwrap Type Items](https://docs.blender.org/api/current/bpy_types_enum_items/shrinkwrap_type_items.html)
- `wrap_mode` items:
  - `ON_SURFACE`: offset applied towards the original point.
  - `INSIDE` and `OUTSIDE`.
  - `OUTSIDE_SURFACE`: offset always to the outside.
  - `ABOVE_SURFACE`: offset "exactly along the target normal".
  — [Modifier Shrinkwrap Mode Items](https://docs.blender.org/api/current/bpy_types_enum_items/modifier_shrinkwrap_mode_items.html)
- Manual on Target Normal Project: "similar to Nearest Surface Point, but produces a much smoother projection in return for being significantly slower". It treats non-manifold boundary edges as thin cylinders and "ignores flat shading". For Project, vertices that never touch the target stay where they were. Subdivision Levels applies a temporary Catmull-Clark subdivision before wrapping. Inside/Outside are "very crude collision detection" and unstable near sharp angles. — [Manual: Shrinkwrap Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/shrinkwrap.html)
- Free custom normals are "not updated for vertex deformations". Corner-fan (INT16_2D) normals are stored relative to the automatic normals, so they move with deformation. — [Blender commit d3f84449ad](https://projects.blender.org/blender/blender/commit/d3f84449ad)
- Local test, smoothed 1.31M-tri proxy wrapped back onto the noisy original (about 0.33 mm mean move):
  - NEAREST_SURFACEPOINT: 0.31 s.
  - PROJECT along vertex normals in both directions, no axis set: 0.18 s.
  - TARGET_PROJECT: 0.21 s.

  These are near-coincident surfaces, which is the fast case. — local test

### Inferences
- **Recipe: clean retopo/proxy -> conform to original body.**
  ```python
  sw = clean.modifiers.new("Conform", 'SHRINKWRAP')
  sw.target = body
  sw.wrap_method = 'TARGET_PROJECT'      # smoothest; 'NEAREST_SURFACEPOINT' when surfaces already coincide
  sw.wrap_mode = 'ON_SURFACE'            # or 'OUTSIDE_SURFACE' with a small +offset to avoid z-fighting
  sw.offset = 0.0
  sw.vertex_group = "conform"            # exclude shut-line rows / openings
  # PROJECT variant: no use_project_x/y/z -> along the clean mesh's vertex normals
  # sw.wrap_method = 'PROJECT'; sw.use_negative_direction = True; sw.use_positive_direction = True
  # sw.project_limit = 0.01              # 10 mm: don't jump across gaps
  ```
- Typical uses on the Nova:
  - (a) Wrap a clean, lower-poly retopo shell onto the dense AI body. Its smooth normals are then naturally clean; this is the "clean mesh projected onto original" route.
  - (b) Wrap the smoothed proxy back onto the original before Data Transfer, so the proxy has the body's exact shape and clean normals. NEAREST_* mappings then match correctly.

  NEAREST_SURFACEPOINT snaps to the nearest point regardless of direction. On a noisy target it reproduces the noise in positions, though less in normals. That is why the normals should come from the smooth proxy rather than be recomputed on the wrapped dense mesh.
- On thin parts (door skins, lips) nearest-point wrapping can snap to the wrong side. Use `project_limit`, `cull_face`, or TARGET_PROJECT for these cases.

### Gaps
- No benchmark of a far-from-target wrap (for example a coarse retopo shell centimetres away) at 1M+ target triangles. The manual says only that TARGET_PROJECT is "significantly slower".

## Q5. Performance on ~1M-triangle meshes, headless, plus tangent/triangulation behaviour your exporter depends on

### Takeaway
At 1.31M triangles everything except the Laplacian Smooth modifier finishes in seconds headless. The biggest risks are correctness, not speed. Re-triangulating after custom normals are set (bmesh or a Triangulate modifier without `keep_custom_normals`) distorted them by up to 55° in a test. `calc_tangents` aborts on n-gons, and kn5 has no slot for the MikkTSpace bitangent sign.

### Cited Findings
- Local test timings, Blender 5.2.1, background mode, 1,310,720 tris / 3.93M corners:

  | Operation | Time |
  |---|---|
  | `normals_split_custom_set_from_vertices` | 1.66 s |
  | `normals_split_custom_set` (per corner) | 9.60 s |
  | `corner_normals.foreach_get` | 0.03 s |
  | `calc_tangents` | 0.27 s |
  | `loops.foreach_get` tangent + bitangent_sign | 0.51 s |
  | Data Transfer `NEAREST_NORMAL` eval | 1.54 s |
  | Data Transfer `NEAREST_POLYNOR` eval | 1.66 s |
  | Data Transfer `POLYINTERP_NEAREST` eval | 2.86 s |
  | Data Transfer `POLYINTERP_LNORPROJ` eval | 5.73 s |
  | Data Transfer apply via `modifier_apply` | 2.63 s |
  | Weighted Normal eval | 0.7 to 1.3 s |
  | Shrinkwrap eval (near-coincident target) | 0.2 to 0.3 s |
  | `set_sharp_from_angle` | 0.04 s |
  | Corrective Smooth x20 | 0.39 s |
  | bmesh `smooth_vert` x10 | 1.73 s |
  | Laplacian Smooth x2 | 198.8 s |

  — local test
- All four Data Transfer mappings gave the same residual noise (0.50°) when the source was a smooth proxy. Interpolated mappings cost 1.7 to 3.7 times more. — local test
- `bpy.ops.object.shade_auto_smooth(angle=...)` works in background mode under `temp_override`. It returned `{'FINISHED'}` and added a `NODES` modifier named "Smooth by Angle". — local test
- Triangulation versus fan-space custom normals. Local test: a 400x400 quad grid (160k quads), wavy plus noise, with custom normals set from vertices (tilted 16.7°). Maximum deviation of corner normals from the set custom normal:
  - 0.26° on the quads.
  - **55.3°** after `bmesh.ops.triangulate`.
  - **55.3°** after a Triangulate modifier with `keep_custom_normals=False`.
  - 0.26° with `keep_custom_normals=True`.
  - 0.26° when the quads were kept and only `calc_loop_triangles()` was read.

  — local test
- `TriangulateModifier.keep_custom_normals`: "Try to preserve custom normals. Warning: Depending on chosen triangulation method, shading may not be fully preserved, "Fixed" method usually gives the best result here" (default False). — [bpy.types.TriangulateModifier](https://docs.blender.org/api/current/bpy.types.TriangulateModifier.html)
- `calc_tangents` behaviour:
  - It needs a UV map ("Tangent space computation needs a UV Map ... aborting").
  - It reports "Tangent space can only be computed for tris/quads, aborting" when n-gons are present.
  - It runs MikkTSpace with the mesh's `corner_normals()` as the normal input, so custom normals are respected.
  - It stores a float4 tangent with w = ±1 as the orientation, exposed as `MeshLoop.tangent` and `MeshLoop.bitangent_sign`.

  — [rna_mesh_api.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/makesrna/intern/rna_mesh_api.cc); [mesh_tangent.cc](https://projects.blender.org/blender/blender/src/branch/main/source/blender/blenkernel/intern/mesh_tangent.cc)
- Release-note speed-ups:
  - 4.1: topology maps for normals are "over 5 times faster" (parallelised), and face-corner normals are cached and recalculated less often. — [4.1 Modeling](https://developer.blender.org/docs/release_notes/4.1/modeling/)
  - 4.4: up to 15% faster playback with sharp edges or custom normals. — [4.4 Modeling](https://developer.blender.org/docs/release_notes/4.4/modeling/)
  - 4.5: face-corner and custom normals "calculated over twice as fast". — [4.5 Geometry Nodes](https://developer.blender.org/docs/release_notes/4.5/geometry_nodes/)
  - Free normals gave "25 times better playback" in a simple test. — [commit d3f84449ad](https://projects.blender.org/blender/blender/commit/d3f84449ad)
- The project's own exporter (`tools/ac_kn5_export.py`, `mesh_groups()`):
  - It reads the *evaluated* mesh (`obj.evaluated_get(depsgraph).to_mesh()`), so unapplied Data Transfer or Weighted Normal modifiers are already baked into the exported normals.
  - It triangulates by reading `me.loop_triangles`, which leaves the mesh untouched and is therefore safe for custom normals.
  - It calls `calc_tangents(uvmap=...)`, falling back to an arbitrary perpendicular tangent on `RuntimeError` (n-gons).
  - It reads `me.loops` tangents but never `bitangent_sign`.
  - It converts axes with `(x, z, -y)`, flips V, and transforms normals by the inverse matrix.
  - It deduplicates vertices on (vertex index, normal rounded to 4 dp, UV rounded to 5 dp).
  - It splits chunks to 65,535 vertices.

  — local file `D:\Claude\vauxhall_nova_gte_1989\tools\ac_kn5_export.py` lines 124-189

### Inferences
- Keep the exporter's `loop_triangles` approach. Never `bmesh.ops.triangulate` a mesh that already carries INT16_2D custom normals; `blender/scripts/details_ref.py` does this on its own data. If triangulation is required, use a Triangulate modifier with `keep_custom_normals=True` and `quad_method='FIXED'`, or set the custom normals *after* triangulating.
- Do the clean-up on the final topology. Any later change shifts the fan-relative stored values: decimate, triangulate, `set_sharp_from_angle`, a Smooth by Angle modifier after the transfer, or merge-by-distance.
- Apply, rather than keep live, the Data Transfer on the 1.2M body. Each export or viewport depsgraph update otherwise re-runs 1.5 to 6 s of transfer, plus Corrective Smooth on the proxy if that is live too.
- Make sure the painted body has no n-gons (tris/quads only). Otherwise `calc_tangents` aborts and the exporter falls back to arbitrary tangents. That is harmless for a flat normal map, but wrong if the car paint or any material on that mesh uses `txNormal` or a real normal map.
- The exporter drops `bitangent_sign`. Where UVs are mirrored, the shader's reconstructed bitangent will be flipped relative to MikkTSpace. The paint usually uses no normal map, so this matters only for normal-mapped parts with mirrored UVs (see Q6 gaps).
- The rounding of the dedup key (normals to 4 dp) is fine for transferred smooth normals. It also means adjacent chunks share identical normals at split boundaries, so the 65,535-vertex chunking creates no shading seams.

### Gaps
- The test mesh was synthetic. Timings on the real Nova body (non-uniform density, multiple materials, panel gaps) will differ, especially for POLYINTERP mappings and Shrinkwrap with far targets.
- The "Simplify" option that turns off corner/custom normals in the viewport (4.1) was not checked for its Python property name or headless effect.

## Q6. Assetto Corsa side: how kn5 and AC/CSP use normals and tangents, seams, smoothing practice, and the ksEditor/FBX path

### Takeaway
A kn5 mesh vertex is simply position(float3), normal(float3), uv(float2), tangent(float3), with 16-bit indices. There are no smoothing groups and no bitangent sign. Whatever per-corner normals the exporter writes is exactly what AC shades with. A "hard edge" is two vertices with different normals, and a seam appears in AC only where the written normals differ. Kunos' pipeline says custom normals are supported via FBX and stresses smooth curved surfaces for reflections. It budgets about 125k triangles for the *whole* LOD A exterior, roughly a tenth of the Nova body alone.

### Cited Findings
- Content Manager's kn5 code (gro-ove/actools) defines the vertex as `public Vec3 Position, Normal, Tangent; public Vec2 Tex;` with `ushort[] Indices`. The writer emits `Position, Normal, Tex, Tangent` per vertex. Vertex equality compares all four fields. — [Kn5Node.cs](https://github.com/gro-ove/actools/blob/master/AcTools/Kn5File/Kn5Node.cs); [Kn5Writer.cs](https://github.com/gro-ove/actools/blob/master/AcTools/Kn5File/Kn5Writer.cs)
- The open-source Blender kn5 exporter (moppius/blender-assetto-corsa-tools):
  - It writes `write_vector3(co)`, `write_vector3(normal)`, `write_vector2(uv)`, `write_vector3(tangent)` per vertex.
  - It deduplicates vertices on (co, normal, uv, tangent).
  - It flips V (`-uv[1]`) and splits meshes above 2^16 vertices.
  - It gets tangents from `calc_tangents()`.
  - It triangulates with bmesh first and reads the legacy `loop.normal`.
  - Its README targets Blender 3.0.

  — [moppius/blender-assetto-corsa-tools](https://github.com/moppius/blender-assetto-corsa-tools); [exporter/node_writer.py](https://raw.githubusercontent.com/moppius/blender-assetto-corsa-tools/main/exporter/node_writer.py)
- A search summary of the older hagn99 Blender kn5 exporter page says it lists "wrong tangent-space values" as a known bug. I saw only the search snippet, not the page; low confidence. — [hagn99 Blender Kn5 Exporter](https://www.sites.google.com/site/hagn99/assettocorsa/blender-kn5-exporter)
- Kunos' official car pipeline (`AC_Pipeline_PUB_Rev2.0.pdf`), local copy at `D:\SteamLibrary\steamapps\common\assettocorsa\sdk\dev\car_pipeline_2.0rev\` and also on [Scribd](https://www.scribd.com/document/501206878/AC-Pipeline-PUB-Rev2-0):
  - FBX data used by the AC engine: "Polygon mesh", "Normals (custom normals are supported)", "Texture coordinate UV (one layer only is read from the AC engine)", bones, nulls, hierarchy, animation and basic transforms.
  - Supported exporters are the FBX 2014/2015 plugins for XSI and 3ds Max; "The 2016 plugin is unsupported!"
  - "The mesh must be (when possible) in quads. Do NOT triangulate the mesh if it is not necessary."
  - Budgets: "LOD A exterior: 125,000 triangles", LOD B 20-25k, LOD C 10-12k, LOD D 2-3k; HR cockpit 125,000.
  - On LODs: "try to reduce the model keeping the curved parts smooth, parts that create evident reflections, such as glass or curved parts of the body."
  - The internal windscreen glass is a copy of the exterior glass "with the normals pointing to the interior".
- The AC modding forum (fughettaboutit, moderator, Jan 2023):
  - ksEditor "only knows material names from the fbx".
  - Shader and texture setup happens in ksEditor; "anything related to that in Blender will not end up in ksEditor".
  - Users are pointed to the SDK pipeline PDF.

  The thread does not discuss normals. — [assettocorsamods.net: Shading Basics (from Blender to KS)](https://assettocorsamods.net/threads/shading-basics-from-blender-to-ks.3053/)
- CSP can rewrite normals at load time for **tracks**:
  - `[SMOOTH_NORMALS_...]` with `MESHES`, `MATERIALS`, `PRECISION = 0.0001` and `NORMAL_CONTRIBUTION = 0`. It groups vertices closer than PRECISION and averages their normals; a non-zero normal contribution helps keep edges.
  - The stated purpose is surfaces that are not smooth, where Rain FX puddle reflections break apart.
  - `[ALTER_NORMALS_...]` rotates normals toward a direction.
  - The page documents these only under tracks.

  — [CSP docs: Tracks / Meshes manipulation](https://cup.acstuff.club/docs/csp/tracks/meshes-manipulation)
- FBX/3ds Max context, from search summaries only, not opened:
  - Autodesk's FBX docs say the 3ds Max FBX importer keeps smoothing-group data and discards explicit normal edits when both are present. — [Autodesk FBX: Importing Explicit Normals and Smoothing Groups](https://download.autodesk.com/us/fbx/20112/3dsmax/files/WS73099cc142f487557bfaa8da122ec01152f4652.htm)
  - Smoothing groups shade faces that share an edge and a group as one smooth surface, and a vertex gets as many normals as there are groups meeting there. — [Autodesk 3ds Max: Adjusting Normals and Smoothing](https://help.autodesk.com/cloudhelp/2016/ENU/3DSMax/files/GUID-FF29D920-7338-4614-8A72-B5C94D47889B.htm)
  - A Blender issue covers FBX export of face smoothing without custom normals. — [Blender add-ons #104434](https://projects.blender.org/blender/blender-addons/issues/104434)
- Blender 4.5 extended `Mesh.calc_smooth_groups(use_bitflags=False, use_boundary_vertices_for_bitflags=False)` so smooth groups can account for boundary vertices, "the expected way to generate smooth groups by some other DCCs and game engines to correctly recompute normals from this data". — [Blender 4.5 Python API notes](https://developer.blender.org/docs/release_notes/4.5/python_api/)
- Generic tangent-space fact, not AC-specific: mirrored UVs need a tangent handedness sign (the tangent's w component) or the bitangent comes out reversed. — [WorldViz forum](https://forum.worldviz.com/archive/index.php/t-4656.html?pda=1); [Blender #53750](https://projects.blender.org/blender/blender/issues/53750)

### Inferences
- **Seams in AC:**
  - Because a kn5 vertex carries exactly one normal, every place where Blender's `corner_normals` differ across an edge becomes duplicated vertices with different normals, which reads as a hard edge in AC. Causes include `sharp_edge`, `sharp_face`, custom-normal discontinuities, and fans split by the transfer.
  - On panel gaps and shut lines that is desirable. On continuous paint it shows up as kinks or "broken" reflections, which car paint's environment reflections exaggerate.
  - So before export: no unintended sharp edges on painted panels, smooth-shaded paint, and normals from a smooth source.
  - Chunk splits (65,535 vertices) and UV seams do *not* cause shading seams, because the duplicated vertices keep the same normal.
- **Smoothing groups do not exist in kn5.** On the ksEditor/FBX route, the Kunos statement "custom normals are supported" suggests exporting FBX with normals and not relying on smoothing groups. That would be Blender FBX "Normals Only" plus custom normals, but it is untested here.
  - The project's direct Blender-to-kn5 exporter skips this question entirely: it writes Blender's final corner normals.
  - `calc_smooth_groups` is only needed for formats that rebuild normals from groups.
- **Density versus the budget.** The Nova body at about 1.2M triangles is roughly 10x Kunos' whole-exterior LOD A budget (125k).
  - With 16-bit indices it becomes about 10 or more mesh chunks (each 65,535 vertices or fewer), and each chunk is a separate kn5 mesh node, i.e. a draw call.
  - Clean normals matter more than triangle count for reflections. A cleaned, lower-density body (for example a retopo shell shrinkwrapped onto the scan, Q4) is the route the pipeline guidance points to: "keeping the curved parts smooth".
- **Tangents in AC.** The kn5 tangent is float3 with no handedness. AC's shaders must assume one bitangent orientation, but I found no source saying which.
  - For the car paint this matters only if a normal map (`txNormal`) is used on the paint.
  - On normal-mapped parts, avoid mirrored or flipped UV islands, or bake separate unmirrored UVs.
  - Tangents must be transformed with the same axis swap as normals; the project's exporter does this, while the moppius exporter writes raw `loop.tangent` without axis conversion.
- CSP's `[SMOOTH_NORMALS_...]` is a track-config tool. Even if it worked in a car config (undocumented), it averages by position with a fixed threshold, so it could also smooth intended panel-gap edges. Fixing normals in Blender is the controllable route.

### Gaps
- No source found on how AC's original shaders (`ksPerPixelMultiMap`, `ksPerPixel`) or CSP reconstruct the bitangent (handedness) from the kn5 float3 tangent, or whether CSP's car paint replacement recomputes normals or tangents. CSP shaders are not public, and none of the searches returned shader-level documentation.
- No source found on whether ksEditor recomputes tangents on FBX import or reads them from the FBX, or how it treats Blender FBX "Face"/"Edge" smoothing versus custom normals beyond "custom normals are supported".
- No source found with explicit Kunos/CSP guidance on "recommended smoothing practice for car paint" beyond the pipeline's "keep the curved parts smooth" for reflections. No AC-specific reports of custom-normal *bugs* were found, and the 2023 forum threads mention only generic "black car" and flipped-normal problems.
- Whether CSP `[SMOOTH_NORMALS_...]` or `[ALTER_NORMALS_...]` sections are honoured in car `ext_config` files is undocumented on the page found.
