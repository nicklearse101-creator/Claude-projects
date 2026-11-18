r"""Phase 0 of interior colours (research/Interior colours for AC skins.md): one hand-made test skin, checked in game
before anything goes into the app. Car: ks_mazda_mx5_cup (Kunos: grey occlusion atlas + small tiling colour tiles).
  leather tile  leather.dds        -> Ratty purple   (leather parts, gear boot)
  alcantara     alcnt.dds          -> dark purple
  roll bar      INT_RollBar_OCC.dds -> orange        (its own texture: only the roll bar uses it)
Everything else is the stock skin "00_official". Recolour = OKLab lightness remap (research/recol_ref.py, m_hybrid).
Writes a NEW skin folder 'R4S interior test' (refuses if it exists).  python research/proto_interior_mx5.py"""
import os, shutil, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import skingen
import recol_ref as RC

CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\ks_mazda_mx5_cup'
OUT = os.path.join(CAR, 'skins', 'R4S interior test')
JOBS = (('leather.dds', '#9b3dff'), ('alcnt.dds', '#3a1060'), ('INT_RollBar_OCC.dds', '#ff6a00'))


def recolour(img, hexcol):
    a = np.asarray(img.convert('RGBA')).astype(np.float32) / 255
    T = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
    if 'occ' in getattr(img, 'r4s_name', '').lower():
        # a shading sheet (AO): its brightest, unshadowed level is the paint itself - measured from the middle the
        # bright tubes came out nearly white (Nik 18 Nov: "the orange roll cage is more like a tint")
        lab = RC.srgb_to_oklab(a[..., :3]); L = lab[..., 0]
        ref = np.percentile(L[L > 0.08], 90); t = RC.srgb_to_oklab(T)
        out = np.empty_like(lab)
        r = np.clip(L / ref, 0, 1.0)      # never paler than the colour (baked highlights went peach in the sun)
        out[..., 0] = t[0] * r
        out[..., 1:] = t[1:] * r[..., None]
        rgb, g = RC.oklab_to_srgb(RC.gamut_clip(out)), 1.0
    else:
        rgb, g = RC.m_hybrid(a[..., :3], T, None, gmin=0.6, gmax=1.3)
    out = np.dstack([rgb, a[..., 3]])
    return Image.fromarray(np.clip(np.round(out * 255), 0, 255).astype(np.uint8), 'RGBA'), g


def main():
    if os.path.exists(OUT): sys.exit(f'{OUT} exists already - not touched')
    car = skingen.Car(CAR, log=lambda *a: None)
    src = os.path.join(CAR, 'skins', '00_official')
    os.makedirs(OUT)
    for f in os.listdir(src):
        if f.lower() not in ('preview.jpg', 'ui_skin.json'):
            shutil.copyfile(os.path.join(src, f), os.path.join(OUT, f))
    sheet = []
    for tex, col in JOBS:
        img = skingen.load_image(car.kn5.textures[tex]); img.r4s_name = tex
        new, g = recolour(img, col)
        name = skingen.skin_file_name(car, CAR, tex)
        skingen.write_texture(new, os.path.join(OUT, name), compress=False)
        print(f'{tex}: {img.size} -> {col} (detail gain {g:.2f}) written as {name}')
        a, b = img.convert('RGB').resize((256, 256)), new.convert('RGB').resize((256, 256))
        pair = Image.new('RGB', (520, 256), (20, 20, 20)); pair.paste(a, (0, 0)); pair.paste(b, (264, 0)); sheet.append(pair)
    s = Image.new('RGB', (520, len(sheet) * 266), (20, 20, 20))
    for i, p in enumerate(sheet): s.paste(p, (0, i * 266))
    s.save(r'D:\ClaudeData\tmp\interior_mx5_before_after.png')
    # (18 Nov: a CSP 'more diffuse light' setting for the cage was tried and dropped - it overexposed the sunlit tubes)
    import json
    json.dump({'skinname': 'R4S interior test', 'drivername': 'Nicklearse101', 'country': '', 'team': "Ratty's Racing", 'number': 101},
              open(os.path.join(OUT, 'ui_skin.json'), 'w'), indent=4)
    print('written:', OUT, sorted(os.listdir(OUT)))


if __name__ == '__main__':
    main()
