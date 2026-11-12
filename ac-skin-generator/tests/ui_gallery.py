"""The pattern gallery in the real window (a theme of choice), screenshot of it.
python tests/ui_gallery.py APPDATA_COPY WORK_DIR [THEME]"""
import json, os, shutil, sys, time
work = os.path.abspath(sys.argv[2]); th = sys.argv[3] if len(sys.argv) > 3 else 'carbon_orange'
shutil.rmtree(os.path.join(work, 'appdata'), ignore_errors=True)
shutil.copytree(os.path.abspath(sys.argv[1]), os.path.join(work, 'appdata'))
os.environ['APPDATA'] = os.path.join(work, 'appdata')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R
from PIL import ImageGrab
cfg = json.load(open(R.SETTINGS, encoding='utf8')); cfg['ui_theme'] = th
json.dump(cfg, open(R.SETTINGS, 'w', encoding='utf8'))
app = R.App(); app.geometry('1320x840+20+20'); app.update()
app.open_gallery(); g = app.gallery; g.geometry('1010x720+60+60')
t = time.time()
while not app.gallery_done and time.time() - t < 60: app.update(); time.sleep(0.02)
for _ in range(10): app.update(); time.sleep(0.05)
k = 1.5
x, y, w, h = g.winfo_rootx(), g.winfo_rooty(), g.winfo_width(), g.winfo_height()
p = os.path.join(work, f'gallery_{th}.png')
ImageGrab.grab((int(x * k), int(y * k), int((x + w) * k), int((y + h) * k)), all_screens=True).save(p)
print('saved', p, 'in', round(time.time() - t, 1), 's')
app.destroy()
