"""Open each of the app's own pop-ups in the real window (dark messages, Edit text, lens colour chart), take a
picture of each, close it. Uses a COPY of the app's data folder (APPDATA given on the command line).
python tests/ui_dialogs.py APPDATA_COPY OUT_DIR"""
import os, sys, time
os.environ['APPDATA'] = os.path.abspath(sys.argv[1])
out = sys.argv[2]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ctypes
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
import rattys4skin as R
import theme
from PIL import ImageGrab

os.makedirs(out, exist_ok=True)
app = R.App()
app.geometry('1500x950+20+20'); app.attributes('-topmost', True)
for _ in range(20): app.update(); time.sleep(0.05)
problems = []


def grab(win, name, pad=30):
    win.update(); time.sleep(0.3); win.update()
    x, y, w, h = win.winfo_rootx(), win.winfo_rooty(), win.winfo_width(), win.winfo_height()
    ImageGrab.grab(bbox=(x - pad, y - pad - 30, x + w + pad, y + h + pad)).save(os.path.join(out, name + '.png'))


def message(fn, args, name, button, expect):
    def close():
        if not theme._open_dialogs:
            problems.append(f'{name}: no dialog open'); return
        d = theme._open_dialogs[-1]
        grab(d, name)
        d.buttons[button].invoke()
    app.after(700, close)
    got = fn(*args)
    print(f'{name}: returned {got!r}')
    if got != expect: problems.append(f'{name}: returned {got!r}, expected {expect!r}')


message(R.messagebox.showerror, (R.APP_NAME, 'Pick a car first (Car tab).'), 'dlg_error', 'OK', None)
message(R.messagebox.showinfo, (R.APP_NAME, 'Make a preview first.'), 'dlg_info', 'OK', None)
message(R.messagebox.askyesno, (R.APP_NAME, 'You already made a skin called "ratty_101" for this car.\n\nReplace it with the new one?'),
        'dlg_yesno', 'Yes', True)
message(R.messagebox.askyesno, (R.APP_NAME, 'Take every logo off the car (all set to "Not used")?'), 'dlg_yesno_no', 'No', False)

# Edit text: a team name box picked on the preview (stand-in for a real pick)
key = 'team name (doors)'
app.view_decals = lambda: [dict(key=key, label='Team name (doors)', view='left')]
app.sel = key
app.edit_text()
tops = [w for w in app.winfo_children() if str(w).startswith('.!toplevel')]
if not tops: problems.append('Edit text did not open')
else:
    grab(tops[-1], 'dlg_edit_text'); tops[-1].destroy()

# lens colour chart
app.swatch_picker(app.btn_prev, app.vars['lens_colour'], R.LENS_COLOURS)
tops = [w for w in app.winfo_children() if str(w).startswith('.!toplevel')]
if not tops: problems.append('lens chart did not open')
else:
    grab(tops[-1], 'dlg_lens_chart'); tops[-1].destroy()

print('PROBLEMS:', problems or 'none')
app.destroy()
