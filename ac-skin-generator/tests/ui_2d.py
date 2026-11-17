r"""Real-window check of the 2D mode (protected cars), off screen, scratch data folder (never Nik's): preview the
Ferrari 296 GT3, save what the sheet view shows, drag the number, let go, save it after the automatic redraw.
python tests/ui_2d.py D:\ClaudeData\tmp\ui_2d"""
import os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else r'D:\ClaudeData\tmp\ui_2d')
shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
os.environ['R4S_WORK'] = os.path.join(out, 'work'); os.environ['R4S_NO_TOUR'] = '1'
import rattys4skin as R
from PIL import ImageTk

data = os.path.join(out, 'data')
R.DATA_DIR, R.LOGO_DIR, R.SETTINGS, R.LIBRARY = data, os.path.join(data, 'logos'), os.path.join(data, 's.json'), os.path.join(data, 'l.json')
os.makedirs(R.LOGO_DIR)
shutil.copy(os.path.join(os.path.dirname(R.__file__), 'starter_logos', 'ratty_racing_logo.jpg'), os.path.join(R.LOGO_DIR, 'rat.jpg'))
R.App.add_starter_logos = lambda self: None
R.messagebox.showinfo = lambda *a, **k: None
app = R.App()
app.geometry('1400x900+-3000+-3000')
app.vars['cars_dir'].set(r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'); app.refresh_cars()
app.vars['car'].set('cf_ferrari_296_gt3'); app.refresh_skins()
for k, v in dict(base='#2a0a4a', accent='#9b3dff', accent2='#ff6a00', text='#ffffff', number='101',
                 team="RATTY'S RACING", name='NICKLEARSE101').items():
    app.vars[k].set(v)
app.vars['pattern_name'].set(R.skingen.PATTERNS['splinter_camo'])
app.vars['font_team_name'].set('Racing: Exo 2 Black Italic'); app.vars['font_number_name'].set('Racing: Russo One')
app.library.append(dict(file='rat.jpg', name='rat', place='roof', places=['roof'], tint=False)); app.refresh_library()


def loop(until, secs):
    t = time.time()
    def check():
        if until() or time.time() - t > secs: app.quit()
        else: app.after(100, check)
    app.after(100, check); app.mainloop()


def grab(name):
    im = ImageTk.getimage(app.preview_img).convert('RGBA')
    for item in app.canvas.find_withtag('live'):
        x, y = app.canvas.coords(item)
        ph = next(p for p in app._live_imgs if str(p) == app.canvas.itemcget(item, 'image'))
        sp = ImageTk.getimage(ph).convert('RGBA'); im.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))
    im.convert('RGB').save(os.path.join(out, name + '.png'))


app.update()
t0 = time.time()
app.run(save=False)
loop(lambda: not app.busy and app.views, 300)
print(f'first preview {time.time() - t0:.1f} s, 2D: {app.is2d()}, decals: {[d["key"] for d in app.info.get("decals2d", [])]}')
app.update(); grab('1_sheet')
b = next(b for b in app.boxes2d() if b['key'] == '2d:number')
ox, oy, k = app.geom2d
x0, y0 = ox + b['u'] * k, oy + b['v'] * k
app.on_press(type('E', (), dict(x=int(x0), y=int(y0)))())
for s_ in range(1, 9): app.on_drag(type('E', (), dict(x=int(x0 + 6 * s_), y=int(y0)))())
app.update(); grab('2_dragging')
t0 = time.time(); app.on_release(None)
loop(lambda: app._auto_job is None and not app.busy and app.adj() == app.adjust_gen, 120)
app.update(); grab('3_after_let_go')
print(f'redrawn by itself in {time.time() - t0:.1f} s')
app.destroy()
