"""The alignment grid in the real window: Preview of a real car, then the Left and Top views with the grid, screenshots.
Uses a COPY of the app data. python tests/ui_grid.py APPDATA_COPY WORK_DIR CAR"""
import os, shutil, sys, time
work = os.path.abspath(sys.argv[2]); CAR = sys.argv[3]
shutil.rmtree(os.path.join(work, 'appdata'), ignore_errors=True)
shutil.copytree(os.path.abspath(sys.argv[1]), os.path.join(work, 'appdata'))
os.environ['APPDATA'] = os.path.join(work, 'appdata')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R
from PIL import Image
for f in ('showerror', 'showwarning', 'showinfo'):
    setattr(R.messagebox, f, lambda t, m, f=f, **k: print(f.upper(), m))
app = R.App(); app.geometry('1500x950+20+20')
shots, st = [], {}


def shot(name):
    """The preview as the canvas holds it, drawn off-screen (never a screen grab: other windows may be on top):
    the app's own picture, then the canvas's grid lines and boxes at their exact coordinates."""
    app.update()
    from PIL import ImageTk, ImageDraw
    im = ImageTk.getimage(app.preview_img).convert('RGB')
    d = ImageDraw.Draw(im)
    for it in app.canvas.find_withtag('grid') + app.canvas.find_withtag('grid_centre') + app.canvas.find_withtag('box'):
        xy = app.canvas.coords(it)
        col = app.canvas.itemcget(it, 'fill') or app.canvas.itemcget(it, 'outline') or '#ffffff'
        if app.canvas.type(it) == 'line': d.line(xy, fill=col, width=1)
        elif app.canvas.type(it) == 'polygon': d.polygon(xy, outline=col)
    shots.append(im)


def start():
    app.vars['car'].set(CAR); app.car_box.event_generate('<<ComboboxSelected>>'); app.update()
    st['t0'] = time.time(); app.btn_prev.invoke(); app.after(500, wait)


def wait():
    if app.busy and time.time() - st['t0'] < 600: app.after(300, wait); return
    for v in ('left', 'top'):
        app.view_var.set(v); app.on_view(); app.update(); time.sleep(0.3); shot(v)
    print('grid lines', len(app.canvas.find_withtag('grid')), 'centre', len(app.canvas.find_withtag('grid_centre')))
    w = max(s.width for s in shots)
    sheet = Image.new('RGB', (w, sum(s.height for s in shots)), 'black'); y = 0
    for s in shots: sheet.paste(s, (0, y)); y += s.height
    sheet.thumbnail((1600, 2000)); p = os.path.join(work, 'grid.png'); sheet.save(p); print('saved', p)
    app.destroy()


app.after(500, start)
app.mainloop()
