"""The real app window: Preview, then Create skin in car, timed, the way Nik uses it. The car is a copy made of hard
links in a test cars folder on the same drive (no space used; the app only adds a new skin folder there), so the real
car is never touched. Uses a COPY of the app's data folder (APPDATA given on the command line). Runs inside the app's
own main loop (the work thread reports progress through it).
python tests/ui_speed.py APPDATA_COPY WORK_DIR CAR [CAR ...]        (WORK_DIR on the same drive as the game)"""
import os, shutil, sys, time
work = os.path.abspath(sys.argv[2]); cars = list(sys.argv[3:])
# its own copy of the data copy: the app saves the test cars folder in its settings, which must not leak into other checks
import shutil as _sh
_sh.rmtree(os.path.join(work, 'appdata'), ignore_errors=True)
_sh.copytree(os.path.abspath(sys.argv[1]), os.path.join(work, 'appdata'))
os.environ['APPDATA'] = os.path.join(work, 'appdata')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R

ROOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
CARS = os.path.join(work, 'cars')
dialogs = []
R.messagebox.showerror = lambda t, m, **k: dialogs.append(('ERROR', m))
R.messagebox.showwarning = lambda t, m, **k: dialogs.append(('WARNING', m))
R.messagebox.showinfo = lambda t, m, **k: dialogs.append(('INFO', m))
R.messagebox.askyesno = lambda t, m, **k: (dialogs.append(('ASK', m)), True)[1]


def linked_copy(car):
    src, dst = os.path.join(ROOT, car), os.path.join(CARS, car)
    shutil.rmtree(dst, ignore_errors=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for f in files: os.link(os.path.join(root, f), os.path.join(dst, rel, f))


app = R.App()
app.geometry('1500x950+20+20')
problems, st = [], {}


def next_car():
    if not cars:
        print('dialogs:', dialogs or 'none'); print('PROBLEMS:', problems or 'none', flush=True)
        app.destroy(); return
    car = st['car'] = cars.pop(0)
    linked_copy(car)
    app.vars['cars_dir'].set(CARS); app.refresh_cars(); app.update()
    app.vars['car'].set(car); app.car_box.event_generate('<<ComboboxSelected>>'); app.update()
    app.vars['skin_name'].set('ui_speed_test')
    press(False)


def press(save):
    st.update(save=save, t0=time.time())
    (app.btn_save if save else app.btn_prev).invoke()
    app.after(300, wait)


def wait():
    if app.busy and time.time() - st['t0'] < 900:
        app.after(200, wait); return
    took = time.time() - st['t0']
    car = st['car']
    log = app.log_box.get('1.0', 'end')
    if 'ERROR' in log or app.busy: problems.append(f'{car}: error in the log or still busy')
    if not st['save']:
        st['tp'] = took; press(True); return
    made = os.path.join(CARS, car, 'skins', 'ui_speed_test')
    files = sorted(os.listdir(made)) if os.path.isdir(made) else []
    print(f'{car}: Preview {st["tp"]:.1f}s, then Create {took:.1f}s -> {len(files)} files', flush=True)
    if not any(f.endswith('.dds') for f in files) or 'generator_preview.png' not in files:
        problems.append(f'{car}: skin not made ({files})')
    shutil.rmtree(os.path.join(CARS, car), ignore_errors=True)
    app.after(500, next_car)


app.after(500, next_car)
app.mainloop()
