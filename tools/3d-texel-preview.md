# Seeing a 3D model from Python (texel map + quick render)

Made for the AC skin generator (`ac-skin-generator/skingen.py`, `kn5.py`), useful for Blender work.

- `kn5.py` - reads an AC `.kn5`: world-space meshes, UVs, normals, materials, embedded textures.
- `TexelMap` - rasterises triangles into texture space: every texel gets its 3D position and
  normal. Handles tiled UVs, seams, sliver triangles; flags texels used by two surfaces.
- `render_view(car, 'left'|'right'|'front'|'rear'|'top', textures, texelmaps)` - orthographic
  preview: grey shell plus the textured surface, about 3 s per car.
- `tests/test_stock.py CAR_DIR SKIN out.png` - renders any installed skin from all sides
  (quick check for mirrored writing).

Uses for Blender work: check UV / texture orientation without opening Blender, make quick
side/front/rear previews to compare against photos, project decals or paint from 3D instead
of guessing in UV space. Can be adapted to OBJ/glTF exports.
