"""The patterns on real cars, to judge by eye: per car one sheet with every pattern (left side over the top view).
Pattern only (no number, names or logos), main body texture only. python tests/pattern_cars.py OUT_DIR CAR [CAR ...]
PATTERNS=a,b,c to draw only some."""
import os, sys, time, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw, ImageFont
import skingen, patterns_plus

ROOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
out_dir, cars = sys.argv[1], sys.argv[2:]
os.makedirs(out_dir, exist_ok=True)
pats = os.environ.get('PATTERNS', '').split(',') if os.environ.get('PATTERNS') else list(patterns_plus.NAMES)
fnt = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 16)
COL = dict(base='#0c0b10', accent='#7020d2', accent2='#be6eff', text='#f0eef5')
for name in cars:
    t0 = time.time()
    skingen._MEMO.clear()
    car = skingen.Car(os.path.join(ROOT, name), log=lambda *a: None)
    tex = car.body_textures[0]
    ref = None
    for s in car.skins:
        ref = car.stock_texture(tex, s)
        if ref is not None: break
    if ref is None: ref = skingen.load_image(car.kn5.textures[tex])
    W, H = ref.size; k = 2048 / max(W, H); W, H = int(W * k), int(H * k)
    tm = skingen.TexelMap(car.meshes_for(tex), W, H, lambda *a: None); tm.tex = tex
    base, alpha, paint, shade = skingen.stock_analysis(car, tex, W, H, tm, lambda *a: None)
    tiles = []
    for pat in pats:
        d = dict(skingen.DEFAULT_DESIGN, pattern=pat, number='', team='', name='', logos=[], **COL)
        img, _ = skingen._paint_texture(car, tm, {}, base, paint, shade, d, [], None, {}, lambda *a: None)
        img = img.copy(); img.putalpha(Image.fromarray(alpha))
        L = skingen.render_view(car, 'left', {tex: img}, {tex: tm}, width=520)
        T = skingen.render_view(car, 'top', {tex: img}, {tex: tm}, width=520)
        T = T.rotate(90, expand=True) if T.height > T.width else T
        T = T.resize((520, int(T.height * 520 / T.width)))
        tile = Image.new('RGB', (520, 24 + L.height + T.height), (40, 40, 44))
        ImageDraw.Draw(tile).text((4, 2), patterns_plus.NAMES.get(pat, pat), fill='white', font=fnt)
        tile.paste(L, (0, 24)); tile.paste(T, (0, 24 + L.height))
        tiles.append(tile)
    cols = 4
    tw, th = tiles[0].width, max(t.height for t in tiles)
    sheet = Image.new('RGB', (cols * (tw + 6), ((len(tiles) + cols - 1) // cols) * (th + 6)), (25, 25, 28))
    for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * (tw + 6), (i // cols) * (th + 6)))
    p = os.path.join(out_dir, f'{name}.jpg'); sheet.save(p, quality=88)
    print(f'{name}: {len(pats)} patterns in {time.time() - t0:.0f} s -> {p}', flush=True)
