"""The real window in every colour theme, side by side on one sheet (Car tab showing, a car picked).
Uses a COPY of the app data. python tests/ui_themes.py APPDATA_COPY WORK_DIR CAR"""
import json, os, shutil, sys, time
work = os.path.abspath(sys.argv[2]); CAR = sys.argv[3]
shutil.rmtree(os.path.join(work, 'appdata'), ignore_errors=True)
shutil.copytree(os.path.abspath(sys.argv[1]), os.path.join(work, 'appdata'))
os.environ['APPDATA'] = os.path.join(work, 'appdata')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R, theme
from PIL import Image, ImageGrab, ImageDraw, ImageFont

shots = []
for name in theme.THEMES:
    cfg = json.load(open(R.SETTINGS, encoding='utf8'))
    cfg.update(ui_theme=name, car=CAR)
    json.dump(cfg, open(R.SETTINGS, 'w', encoding='utf8'))
    app = R.App(); app.geometry('1320x840+20+20'); app.update()
    app.refresh_skins()
    t0 = time.time()
    while app.ghost is None and time.time() - t0 < 60:          # the car's ghost behind the preview
        app.update(); time.sleep(0.1)
    try: app.tabbar.select(0)                                 # the Car tab (it has the theme choice)
    except Exception: pass
    for _ in range(10): app.update(); time.sleep(0.05)
    k = 1.5
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab((int(x * k), int(y * k), int((x + w) * k), int((y + h) * k)), all_screens=True)
    shots.append((theme.THEMES[name][0], im)); print(name, im.size, flush=True)
    app.destroy()
tw = 900
fnt = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 22)
tiles = [(n, im.resize((tw, int(im.height * tw / im.width)))) for n, im in shots]
th = tiles[0][1].height + 34
sheet = Image.new('RGB', (2 * tw + 10, ((len(tiles) + 1) // 2) * th), (60, 60, 64))
d = ImageDraw.Draw(sheet)
for i, (n, im) in enumerate(tiles):
    x0, y0 = (i % 2) * (tw + 10), (i // 2) * th
    d.text((x0 + 6, y0 + 4), n, fill='white', font=fnt); sheet.paste(im, (x0, y0 + 34))
p = os.path.join(work, 'themes.jpg'); sheet.save(p, quality=90); print('saved', p)
