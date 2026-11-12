"""Drive the real app window like a user: pick cars from the list, set logos on the Logos tab (incl. Clear all),
pick a lens colour from the chart, press Preview and wait, and check the log for errors. Uses a COPY of the app's
data folder (APPDATA given on the command line), never the real one. Saves a picture of the window per step.
python tests/ui_drive.py APPDATA_COPY OUT_DIR CAR [CAR ...]"""
import os, sys, time, json
os.environ['APPDATA'] = os.path.abspath(sys.argv[1])          # before the app is imported: its data folder
out = sys.argv[2]; cars = sys.argv[3:]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ctypes
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)   # screen pixels = window pixels, for the screenshots
except Exception: pass
import rattys4skin as R
from PIL import ImageGrab

os.makedirs(out, exist_ok=True)
dialogs = []
R.messagebox.showerror = lambda t, m, **k: dialogs.append(('ERROR', m))
R.messagebox.showwarning = lambda t, m, **k: dialogs.append(('WARNING', m))
R.messagebox.askyesno = lambda t, m, **k: (dialogs.append(('ASK', m)), True)[1]
problems = []

app = R.App()
app.geometry('1500x950+20+20'); app.attributes('-topmost', True)
for _ in range(20): app.update(); time.sleep(0.05)


def show_tab(i):
    app.tabbar.select(i); app.update()


def shot(name):
    app.update(); time.sleep(0.3); app.update()
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(os.path.join(out, name + '.png'))


def pick_car(name):
    app.vars['car'].set(name)
    app.car_box.event_generate('<<ComboboxSelected>>'); app.update()


# --- logos tab: two logos on the bonnet, one on the doors; the 'On the car' list; Clear all; set again
lib = app.library
def set_place(i, place_name):
    app.tree.selection_set(str(i)); app.on_logo_select(); app.place_var.set(place_name); app.on_place(); app.update()
set_place(0, 'Bonnet'); set_place(1, 'Bonnet'); set_place(2, 'Doors (big)')
used = [app.used_tree.item(i)['values'] for i in app.used_tree.get_children()]
print('On the car list:', used)
if len([u for u in used if u[1] == 'Bonnet']) != 2: problems.append(f'On the car list wrong: {used}')
show_tab(3); shot('logos_set')
app.clear_logos()
left = [lg for lg in app.library if lg.get('place')]
print('after Clear all:', len(left), 'logos still placed; list:', [app.used_tree.item(i)['values'] for i in app.used_tree.get_children()])
if left: problems.append('Clear all left logos placed')
set_place(0, 'Bonnet'); set_place(2, 'Doors (big)')

# --- lens colour chart: only the bright 16; a dark saved colour is snapped to the nearest bright one
app.vars['use_lens'].set(True); app.vars['lens_colour'].set('#000000')
d = app.design()
print('black lens colour becomes', d['lens_colour'])
if d['lens_colour'] not in R.LENS_COLOURS: problems.append('lens colour not limited')
anchor = app.btn_prev
app.swatch_picker(anchor, app.vars['lens_colour'], R.LENS_COLOURS); app.update()
tops = [w for w in app.winfo_children() if str(w).startswith('.!toplevel')]
btns = [b for b in tops[-1].winfo_children()] if tops else []
print('lens chart buttons:', len(btns))
if len(btns) != 16: problems.append(f'lens chart has {len(btns)} colours')
show_tab(5); shot('lens_chart')
btns[9].invoke(); app.update()
print('picked', app.vars['lens_colour'].get())

# --- windows on, the old 'Windows etc. from' value that broke every car
app.vars['win_enable'].set(True)
app.vars['copy_from'].set('2014-2015')
cars_left = list(cars)
state = {}


def next_car():
    if not cars_left:
        first, _ = state['first']                  # picking a car again: its ghost comes back from disk at once
        pick_car(cars[-1] if len(cars) > 1 else '')
        t = time.time(); pick_car(first)
        while app.ghost_car != first and time.time() - t < 5: app.update(); time.sleep(0.02)
        again = time.time() - t
        print(f'ghost of {first} again after {again:.2f} s', flush=True)
        if again > 1: problems.append(f'ghost from disk took {again:.1f} s')
        print('PROBLEMS:', problems or 'none', flush=True)
        for i in range(6): show_tab(i); shot(f'tab_{i}')
        show_tab(3); shot('end_logos_tab'); app.destroy(); return
    car = cars_left.pop(0)
    pick_car(car)
    print(f'== {car}: Windows etc. from = "{app.vars["copy_from"].get()}"', flush=True)
    state.update(car=car, tg=time.time())
    app.after(200, wait_ghost)


def wait_ghost():
    # the ghost of the car just picked: drawn in the background (or loaded from its kept picture)
    car = state['car']
    if app.ghost_car != car and time.time() - state['tg'] < 60:
        app.after(200, wait_ghost); return
    took = time.time() - state['tg']
    print(f'   ghost: {"ready" if app.ghost_car == car else "MISSING"} after {took:.1f} s', flush=True)
    if app.ghost_car != car or app.ghost is None: problems.append(f'{car}: no ghost')
    if not os.path.isfile(R.ghost_cache_path(os.path.join(app.vars['cars_dir'].get(), car))):
        problems.append(f'{car}: ghost not kept on disk')
    state.setdefault('first', (car, took))
    if not state.get('shot_before'):
        state['shot_before'] = True; app.views = {}; app.redraw(); shot('before_preview')
    state.update(n0=len(dialogs), t0=time.time())
    app.run(save=False)
    app.after(500, wait_car)


def wait_car():
    car = state['car']
    if app.busy and time.time() - state['t0'] < 900:
        app.after(500, wait_car); return
    log = app.log_box.get('1.0', 'end')
    open(os.path.join(out, car + '_log.txt'), 'w', encoding='utf8').write(log)
    bad = [l for l in log.splitlines() if l.startswith('ERROR') or 'Traceback' in l]
    new_d = dialogs[state['n0']:]
    print(f'   {time.time() - state["t0"]:.0f} s, errors in log: {bad[:3]}, dialogs: {new_d[:3]}', flush=True)
    if bad or new_d: problems.append(f'{car}: {bad[:2]} {new_d[:2]}')
    if app.busy: problems.append(f'{car}: still busy after 15 min')
    def side_shots():
        shot(car + '_preview')
        app.view_var.set('left'); app.on_view(); shot(car + '_left')
        app.view_var.set('all'); app.on_view()
        next_car()
    app.after(1500, side_shots)


app.after(200, next_car)
app.mainloop()
