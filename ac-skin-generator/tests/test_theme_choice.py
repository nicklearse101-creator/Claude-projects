"""App colour themes (Nik 12 Nov): every theme readable, the chosen one used from the start, choosing one saves it
and restarts the app. python -m pytest -p no:cacheprovider tests/test_theme_choice.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import json, os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import theme
import rattys4skin as R


def lum(h):
    c = np.array(theme.hexc(h)[:3]) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.fixture(autouse=True)
def back_to_default():
    yield
    theme.use('carbon_orange')


@pytest.mark.parametrize('name', list(theme.THEMES))
def test_theme_readable(name):
    theme.use(name)
    assert contrast(theme.TEXT, theme.PANEL) >= 7 and contrast(theme.TEXT, theme.FIELD) >= 7
    assert contrast(theme.MUTED, theme.PANEL) >= 3.5
    # words on the accent are big bold button words (the approved carbon orange look is 2.9)
    assert contrast(theme.ON_ACC, theme.ACC) >= 2.5 and contrast(theme.ON_ACC2, theme.ACC2) >= 3
    assert contrast(theme.ACC, theme.BG) >= 3                     # the accent shows on the window


def test_use_changes_the_look():
    theme.use('ratty_purple')
    assert theme.ACC == '#9b3dff' and theme._KINDS['primary'][0] == '#9b3dff'
    theme.use('light')
    t = theme.text_image('A', 20)                                 # words default to the theme's text colour (dark)
    px = np.asarray(t)[..., :3][np.asarray(t)[..., 3] > 250]
    assert len(px) and px.mean() < 60
    g = np.asarray(theme.garage(200, 120, 90))[:60, 20:180, :3]
    assert g.mean() > 150                                         # a light garage, not the dark carbon
    theme.use('no such theme')
    assert theme.THEME == 'carbon_orange'


@pytest.fixture
def make_app(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    for k, v in dict(DATA_DIR=data, LOGO_DIR=data / 'logos', SETTINGS=data / 'settings.json',
                     LIBRARY=data / 'logos.json').items():
        monkeypatch.setattr(R, k, str(v))
    monkeypatch.setattr(R.App, 'add_starter_logos', lambda self: None)
    os.makedirs(data, exist_ok=True)
    apps = []

    def make(settings=None):
        if settings: json.dump(settings, open(R.SETTINGS, 'w'))
        a = R.App(); a.withdraw(); apps.append(a); return a
    yield make
    for a in apps:
        try: R.tk.Tk.destroy(a)                                   # the real one (a test may have faked it)
        except Exception: pass


def test_saved_theme_used(make_app):
    a = make_app({'ui_theme': 'ice_blue'})
    assert theme.THEME == 'ice_blue' and a.vars['ui_theme_name'].get() == 'Ice Blue'


def test_default_theme(make_app):
    make_app()
    assert theme.THEME == 'carbon_orange'


def test_choose_theme_saves_and_restarts(make_app, monkeypatch):
    a = make_app()
    started = []
    monkeypatch.setattr(R.subprocess, 'Popen', lambda cmd, **k: started.append(cmd))
    gone = []
    monkeypatch.setattr(a, 'destroy', lambda: gone.append(1))
    a.vars['ui_theme_name'].set('Ratty Purple'); a.on_theme()
    assert json.load(open(R.SETTINGS))['ui_theme'] == 'ratty_purple'
    assert started and gone
    assert started[0][0] == sys.executable and started[0][-1].endswith('rattys4skin.py')


def test_no_restart_while_building(make_app, monkeypatch):
    a = make_app()
    started = []
    monkeypatch.setattr(R.subprocess, 'Popen', lambda cmd, **k: started.append(cmd))
    shown = []
    monkeypatch.setattr(R.messagebox, 'showinfo', lambda t, m, **k: shown.append(m))
    a.busy = True
    a.vars['ui_theme_name'].set('Red Line'); a.on_theme()
    assert not started and shown and json.load(open(R.SETTINGS))['ui_theme'] == 'red_line'   # used next time


def test_font_preview_uses_theme_text(make_app):
    a = make_app({'ui_theme': 'light'})
    from PIL import ImageTk
    im = ImageTk.getimage(a.font_image(None, 'ABC'))
    px = np.asarray(im)[..., :3].reshape(-1, 3)
    assert px.min(0).max() < 90                                  # dark words on the light field


# ---------------------------------------------------------------- the pattern gallery
def pump(a, until, secs=20):
    import time
    t = time.time()
    while not until() and time.time() - t < secs: a.update(); time.sleep(0.02)


def test_gallery_shows_every_pattern(make_app):
    a = make_app()
    a.open_gallery()
    pump(a, lambda: a.gallery_done)
    keys = [k for k in R.skingen.PATTERNS if k != 'picture']
    assert a.gallery.winfo_exists() and list(a.gallery_tiles) == keys
    assert all(t['img'] is not None for t in a.gallery_tiles.values())


def test_gallery_pick(make_app):
    a = make_app()
    a.open_gallery(); pump(a, lambda: a.gallery_done)
    a.gallery_pick('ratty_swoosh')
    assert a.vars['pattern_name'].get() == R.skingen.PATTERNS['ratty_swoosh']
    assert not a.gallery.winfo_exists()


def test_gallery_in_my_colours(make_app):
    a = make_app()
    a.vars['accent'].set('#00ff00')
    a.open_gallery(); pump(a, lambda: a.gallery_done)
    im = a.gallery_tiles['split']['pil']
    px = np.asarray(im)[..., :3].reshape(-1, 3)
    assert ((px[:, 1] > 200) & (px[:, 0] < 60)).mean() > 0.1    # the green accent is in the picture
