"""Draw the UV layout of chosen kn5 meshes over the texture they use (PIL; no Blender needed).

    python uv_sheet.py CAR.kn5 SAMPLER OUT.png MESH_SUBSTR [MESH_SUBSTR ...]
    e.g. python uv_sheet.py toyota_ae86.kn5 txDiffuse body_uv.png GEO_body GEO_extdoor GEO_hood bumper

Each mesh gets its own line colour; the legend is printed. Shows how the texture space is used:
unique vs shared (mirrored) islands, island scale per panel, empty space, tiling outside 0-1.
"""
import sys, os, io
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kn5full import KN5

COL = [(255, 60, 60), (60, 200, 255), (255, 210, 0), (120, 255, 120), (255, 120, 255), (255, 150, 50), (180, 180, 255)]


def main(path, sampler, out, *subs, size=2048):
    k = KN5(path)
    meshes = [m for m in k.meshes if any(s.lower() in m.name.lower() for s in subs)]
    tex = None
    for m in meshes:
        t = m.mat.samplers.get(sampler) if m.mat else None
        if t and t[1] in k.textures:
            try:
                tex = Image.open(io.BytesIO(k.textures[t[1]])).convert('RGB'); print('texture', t[1], tex.size)
            except Exception as e:
                print('cannot read', t[1], e)
            break
    img = (tex.resize((size, size)) if tex else Image.new('RGB', (size, size), (40, 40, 40)))
    img = Image.blend(img, Image.new('RGB', img.size, (0, 0, 0)), 0.45)
    d = ImageDraw.Draw(img)
    for ci, m in enumerate(meshes):
        c = COL[ci % len(COL)]
        uv = m.uv.copy()
        # kn5 (via ksEditor FBX import) stores v as -v_blender, i.e. image row = 1 + v (top-down)
        px = np.stack([uv[:, 0] * size, (uv[:, 1] - np.floor(uv[:, 1].min())) * size], 1)
        for a, b, cc in m.idx:
            d.polygon([tuple(px[a]), tuple(px[b]), tuple(px[cc])], outline=c)
        print(f'{m.name:30s} colour {c}  uv x[{uv[:,0].min():.3f},{uv[:,0].max():.3f}] v[{uv[:,1].min():.3f},{uv[:,1].max():.3f}]')
    img.save(out)


if __name__ == '__main__':
    main(*sys.argv[1:])
