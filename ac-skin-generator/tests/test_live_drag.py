r"""Logos move for real on the preview (Nik 16 Nov: "the logo is moved in real time and not a dashed outline ... much
easier than pressing Preview every time a small change is made").
 - the preview knows each decal's picture (its 'sprite') and, a moment after the preview, the car without its decals
   (clean views): a moved logo is drawn at its new spot over the car with its old spot cleared, while it moves;
 - when it is let go (or sized / turned / flipped / deleted) the car is redrawn by itself, no Preview press, and the
   picked logo stays picked; logos can be moved while that redraw runs.
python -m pytest -p no:cacheprovider tests/test_live_drag.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import copy, os, sys, time
import numpy as np
import pytest
from PIL import Image, ImageTk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app, preview          # noqa: F401  (app is a fixture)
import rattys4skin as R
import skingen

TALBOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6'
LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'starter_logos', 'ratty_racing_logo.jpg')


# ---------------------------------------------------------------- the engine
@pytest.fixture(scope='module')
def talbot_preview():
    views, info = {}, {}
    d = dict(skingen.DEFAULT_DESIGN, logos=[dict(path=LOGO, place='doors', tint=False, bg='auto')], number='', team='')
    skingen.generate(TALBOT, d, 'x', log=lambda *a: None, views=views, info=info, write=False)
    return views, info


def test_decals_carry_their_picture(talbot_preview):
    _, info = talbot_preview
    d = next(x for x in info['decals'] if x['key'] == 'logo:doors' and x['view'] == 'left')
    assert isinstance(d['sprite'], Image.Image) and d['sprite'].mode == 'RGBA' and max(d['sprite'].size) <= 512
    assert d['flip'] in (True, False) and isinstance(info['serial'], int)


def test_clean_views_have_no_decals(talbot_preview):
    views, info = talbot_preview
    clean = skingen.clean_views(info['serial'])
    assert set(skingen.clean_views(info['serial'], which=('left',))) == {'left'}
    assert set(clean) >= {'left', 'right', 'front', 'rear', 'top'}
    a, b = (np.asarray(v['left'].convert('RGB')).astype(int) for v in (views, clean))
    diff = np.abs(a - b).sum(2) > 30
    assert 0.003 < diff.mean() < 0.2                      # the logo's spot differs, the rest of the car is the same
    assert skingen.clean_views(info['serial'] + 1) is None    # an older preview: nothing


# ---------------------------------------------------------------- the app
RED, BLUE = (255, 0, 0, 255), (0, 0, 255, 255)


@pytest.fixture
def live(app, monkeypatch):
    app.extra.update(decals=[dict(key='logo0', label='Logo', view='left', a=0.0, b=0.0, w=0.5, h=0.5, rot=0.0,
                                  slid=[0.0, 0.0], flip=False, sprite=Image.new('RGBA', (50, 50), (0, 255, 0, 255)))],
                     serial=1)
    monkeypatch.setattr(R.skingen, 'clean_views', lambda serial, **k: {v: Image.new('RGBA', (80, 40), BLUE)
                                                                     for v in ('left', 'right', 'front', 'rear', 'top')})
    app.geometry('900x700+-3000+-3000'); app.deiconify(); app.update()
    preview(app)
    app.view_var.set('left'); app.on_view(); app.update()
    pump(app, lambda: 'left' in app.clean)
    return app


def pump(app, until, secs=10):
    """Run the window's main loop (worker threads hand their results back through it) until `until` or `secs`."""
    t = time.time()

    def check():
        if until() or time.time() - t > secs: app.quit()
        else: app.after(30, check)
    app.after(30, check)
    app.mainloop()


def shown(app):
    return np.asarray(ImageTk.getimage(app.preview_img).convert('RGB')).astype(int)


def drag(app, dx, dy):
    x0, y0 = app.to_screen('left', 0.0, 0.0)
    app.on_press(type('E', (), dict(x=int(x0), y=int(y0)))())
    app.on_drag(type('E', (), dict(x=int(x0 + dx), y=int(y0 + dy)))())
    app.update()
    return x0, y0


def test_moving_logo_drawn_live_old_spot_cleared(live):
    x0, y0 = drag(live, 120, 0)
    assert live.sel == 'logo0'
    assert live.canvas.find_withtag('live')                   # the logo's own picture, at the new spot
    px = shown(live)[int(y0), int(x0)]
    assert px[2] > 200 and px[0] < 60                         # the old spot shows the car without the logo (blue)


def test_let_go_redraws_by_itself(live, monkeypatch):
    calls = []
    real = R.skingen.generate
    monkeypatch.setattr(R.skingen, 'generate', lambda *a, **k: (calls.append(copy.deepcopy(a[1].get('adjust'))), real(*a, **k))[1])
    drag(live, 60, 0)
    live.on_release(None)
    pump(live, lambda: calls and not live.busy, 15)
    pump(live, lambda: False, 0.5)
    assert calls and calls[-1]['logo0']['da'] != 0          # the new spot went to the redraw
    assert live.sel == 'logo0'                                # still picked


def test_can_move_while_redrawing(live):
    live.busy = True
    drag(live, 40, 0)
    assert live.adj('logo0').get('da', 0) != 0
    live.busy = False
