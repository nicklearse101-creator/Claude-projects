"""'Pick it on the car' in the real window, on a real car: the app is made to find no bonnet panel, a logo is asked for
on the bonnet, Preview says it is not placed, the spot is picked on the Top view, Preview puts it there. Screenshots of
both previews. Uses a COPY of the app data and a hard-linked copy of the car (see ui_speed.py).
python tests/ui_pick.py APPDATA_COPY WORK_DIR CAR"""
import os, shutil, sys, time, types
work = os.path.abspath(sys.argv[2]); CAR = sys.argv[3]
shutil.rmtree(os.path.join(work, 'appdata'), ignore_errors=True)
shutil.copytree(os.path.abspath(sys.argv[1]), os.path.join(work, 'appdata'))
os.environ['APPDATA'] = os.path.join(work, 'appdata')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R
from PIL import ImageGrab

ROOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
CARS = os.path.join(work, 'cars')
real_panels = R.skingen.top_panels


def no_bonnet(*a, **k):                     # this car's bonnet is "not found"
    p = real_panels(*a, **k); p.pop('bonnet', None); return p
R.skingen.top_panels = no_bonnet
for f in ('showerror', 'showwarning', 'showinfo'):
    setattr(R.messagebox, f, lambda t, m, f=f, **k: print(f.upper(), m))

src, dst = os.path.join(ROOT, CAR), os.path.join(CARS, CAR)
shutil.rmtree(dst, ignore_errors=True)
for root, dirs, files in os.walk(src):
    rel = os.path.relpath(root, src); os.makedirs(os.path.join(dst, rel), exist_ok=True)
    for f in files: os.link(os.path.join(root, f), os.path.join(dst, rel, f))

app = R.App()
app.geometry('1500x950+20+20')
for lg in app.library:                      # the Ratty logo on the bonnet (the others stay where they were)
    if 'ratty' in lg['file'].lower(): lg['place'] = 'bonnet'; break
app.adjust_by_car.pop(CAR, None)
problems, st = [], {}


def shot(name):
    app.update(); k = 1.5                   # the window's numbers are at 100 %, the screen is at 150 %
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    p = os.path.join(work, name)
    ImageGrab.grab((int(x * k), int(y * k), int((x + w) * k), int((y + h) * k)), all_screens=True).save(p)
    print('screenshot', p, flush=True)


def press(then):
    st['t0'] = time.time(); app.btn_prev.invoke()

    def wait():
        if app.busy and time.time() - st['t0'] < 600: app.after(300, wait); return
        app.after(500, then)
    app.after(500, wait)


def start():
    app.vars['cars_dir'].set(CARS); app.refresh_cars(); app.update()
    app.vars['car'].set(CAR); app.car_box.event_generate('<<ComboboxSelected>>'); app.update()
    press(first_done)


def first_done():
    miss = [m['key'] for m in app.missing]
    print('not placed after the first preview:', miss, flush=True)
    if 'logo:bonnet' not in miss or not app.miss_bar.winfo_manager(): problems.append('bonnet logo not reported')
    app.view_var.set('top'); app.on_view(); app.update()
    shot('pick_1_not_placed.png')
    app.miss_box.current([m['key'] for m in app.missing].index('logo:bonnet')); app.start_pick()
    car = R.skingen.Car(os.path.join(CARS, CAR), log=lambda *a: None)
    b = -(car.hi[2] - 0.45)                 # top view: a spot on the bonnet, 45 cm from the front of the car
    x, y = app.to_screen('top', 0.0, b)
    app.on_press(types.SimpleNamespace(x=x, y=y))
    print('picked:', app.adj().get('logo:bonnet'), '|', app.sel_label.cget('text'), flush=True)
    press(second_done)


def second_done():
    on = [d for d in app.info.get('decals', []) if d['key'] == 'logo:bonnet']
    print('bonnet logo boxes:', [(d['view'], round(d['a'], 2), round(d['b'], 2)) for d in on],
          '| not placed now:', [m['key'] for m in app.missing], flush=True)
    if not on or any(m['key'] == 'logo:bonnet' for m in app.missing): problems.append('bonnet logo not placed after the pick')
    if 'ERROR' in app.log_box.get('1.0', 'end'): problems.append('error in the log')
    app.view_var.set('top'); app.on_view(); app.update()
    shot('pick_2_placed.png')
    print('PROBLEMS:', problems or 'none', flush=True)
    shutil.rmtree(dst, ignore_errors=True)
    app.destroy()


app.after(500, start)
app.mainloop()
