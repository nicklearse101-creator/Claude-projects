r"""Real-window check of moving a logo live (Nik 16 Nov), off screen, with a scratch data folder (never Nik's):
preview the Talbot with a doors logo, drag it 40 cm back, save what the preview shows while it moves, let go and
save what the car looks like after the automatic redraw.
python tests/ui_live.py D:\ClaudeData\tmp\ui_live"""
import os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else r'D:\ClaudeData\tmp\ui_live')
shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
os.environ['R4S_WORK'] = os.path.join(out, 'work')
import rattys4skin as R
from PIL import Image, ImageTk

data = os.path.join(out, 'data')
R.DATA_DIR, R.LOGO_DIR, R.SETTINGS, R.LIBRARY = data, os.path.join(data, 'logos'), os.path.join(data, 's.json'), os.path.join(data, 'l.json')
os.makedirs(R.LOGO_DIR)
shutil.copy(os.path.join(os.path.dirname(R.__file__), 'starter_logos', 'ratty_racing_logo.jpg'), os.path.join(R.LOGO_DIR, 'rat.jpg'))
R.App.add_starter_logos = lambda self: None
app = R.App()
app.geometry('1400x900+-3000+-3000')
app.vars['cars_dir'].set(r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'); app.refresh_cars()
app.vars['car'].set('talbot_sunbeam_lotus_81_works_backup_v6'); app.refresh_skins()
app.vars['base'].set('#f2f2f2'); app.vars['pattern_name'].set(R.skingen.PATTERNS['gt_sash'])
app.library.append(dict(file='rat.jpg', name='rat', place='doors', places=['doors'], tint=False)); app.refresh_library()


def loop(until, secs):
    t = time.time()
    def check():
        if until() or time.time() - t > secs: app.quit()
        else: app.after(100, check)
    app.after(100, check); app.mainloop()


def grab(name):
    """What the preview canvas shows: the picture plus the live logos on it (drawn off screen: no screen grab)."""
    im = ImageTk.getimage(app.preview_img).convert('RGBA')
    for item in app.canvas.find_withtag('live'):
        x, y = app.canvas.coords(item)
        ph = next(p for p in app._live_imgs if str(p) == app.canvas.itemcget(item, 'image'))
        sp = ImageTk.getimage(ph).convert('RGBA'); im.alpha_composite(sp, (int(x), int(y)))
    im.convert('RGB').save(os.path.join(out, name + '.png'))


app.update()
app.run(save=False)
loop(lambda: not app.busy and app.views and app.clean is not None, 240)
app.view_var.set('left'); app.on_view(); app.update()
grab('1_preview')
d = next(d for d in app.view_decals() if d['key'].startswith('logo'))
x0, y0 = app.to_screen('left', d['a'], d['b'])
app.on_press(type('E', (), dict(x=int(x0), y=int(y0)))())
px = 0.4 / app.metres_per_pixel('left')
for k in range(1, 11):
    app.on_drag(type('E', (), dict(x=int(x0 + px * k / 10), y=int(y0 - px * k / 40)))())
app.update()
grab('2_while_moving')
t0 = time.time()
app.on_release(None)
loop(lambda: app._auto_job is None and not app.busy and app.adj() == app.adjust_gen and app.clean is not None, 120)
app.update()
grab('3_after_let_go')
print(f'redrawn by itself in {time.time() - t0:.1f} s; picked still: {app.sel}')
app.destroy()
print('saved in', out)
