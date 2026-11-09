---
name: technique-3d-texel-preview
description: "Python technique to \"see\" a car without Blender - texel map (texture pixel -> 3D point/normal) + quick software render; Nik wants it used for Blender work"
metadata:
  node_type: memory
  type: reference
  originSessionId: b5d0974f-1d45-42d3-b3a7-17366915de1f
  modified: 2026-11-09T09:13:38.758Z
---

Built for the skin generator (2026-11-09); Nik asked to reuse it for Blender work. Code: `D:\Claude\Claude-\ac-skin-generator\skingen.py` (+ `kn5.py`).

- **kn5 reader** (`kn5.py`): meshes in world space with UVs, normals, materials/samplers, embedded textures. Fast (numpy), no Blender or SDK.
- **TexelMap**: rasterises triangles into texture space so every texel knows its 3D position + normal. Handles tiled UVs (shift per triangle), seams (interiors first, edge pixels only where empty), thin slivers (closest-point barycentrics, thin triangles drawn first). Also flags texels shared by two surfaces (mirrored/overlapping UVs).
- **render_view**: orthographic preview of any side (left/right/front/rear/top) = grey shell from all triangles (painter's order) + textured texels splatted with a z-buffer. A car renders in ~3 s. `tests/test_stock.py CAR SKIN out.png` renders an existing skin.
- **Views/axes**: AC +X = car's left, +Y up, +Z forward; view functions give "as a person sees it" coordinates, so text orientation can be checked objectively.

**How to apply in Blender work:** check UV layout / texture orientation / mirrored text without opening Blender; make quick side/front/rear previews of a model with its textures to compare against photos (see [[feedback-nova-compare-to-pictures]], [[feedback-judge-by-eye]]); paint or bake textures by projecting from 3D (decals per view) instead of guessing in UV space. Can be ported to read Blender exports (OBJ/glTF) too. Related: [[ac-skin-generator-project]], [[nova-gte-project]], [[blender-skills-cc-blender-skill]].
