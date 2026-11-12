"""The real window at the default, smallest and test sizes, in the same screen-scaling mode as the built exe
(not DPI aware: Windows scales the whole window): Preview, Create skin in car and the progress bar must be inside
the window on every tab. Saves a picture per size. Uses a COPY of the app's data folder.
python tests/ui_layout.py APPDATA_COPY OUT_DIR"""
import os, sys, time
os.environ['APPDATA'] = os.path.abspath(sys.argv[1])
out = sys.argv[2]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R
from PIL import ImageGrab

os.makedirs(out, exist_ok=True)
app = R.App()
app.attributes('-topmost', True)
problems = []


def settle():
    for _ in range(10): app.update(); time.sleep(0.05)


def shot(name):
    full = ImageGrab.grab()                                   # physical pixels; this process works in scaled ones
    k = full.width / app.winfo_screenwidth()
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    full.crop((int(x * k), int(y * k), int((x + w) * k), int((y + h) * k))).save(os.path.join(out, name + '.png'))


def inside(w):
    wy, wh = w.winfo_rooty() - app.winfo_rooty(), w.winfo_height()
    return w.winfo_ismapped() and wh > 2 and wy >= 0 and wy + wh <= app.winfo_height()


for geom in ('1320x840', '1000x640', '1500x950'):
    app.geometry(geom + '+20+20'); settle()
    for i in range(6):
        app.tabbar.select(i); settle()
        for name, w in (('Preview', app.btn_prev), ('Create skin in car', app.btn_save), ('progress bar', app.prog)):
            if not inside(w): problems.append(f'{geom} tab {i}: {name} not inside the window')
    app.tabbar.select(3); settle(); shot('layout_' + geom)
    print(geom, 'window', app.winfo_width(), 'x', app.winfo_height(), '- Create button bottom at',
          app.btn_save.winfo_rooty() - app.winfo_rooty() + app.btn_save.winfo_height(), flush=True)
print('PROBLEMS:', problems[:6] or 'none', f'({len(problems)})' if problems else '')
app.destroy()
