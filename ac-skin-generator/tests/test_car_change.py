"""Picking another car clears the preview of the car before (Nik, 12 Nov): its picture and its logo boxes go, and a
preview of the old car that finishes after the switch is not shown on the new one.
The real window, with a test data folder and two empty test cars; the painting itself is faked (instant).
python -m pytest -p no:cacheprovider tests/test_car_change.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, sys, threading, time
import pytest
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R


@pytest.fixture
def app(tmp_path, monkeypatch):
    data = tmp_path / 'data'                                   # never the real app data
    for k, v in dict(DATA_DIR=data, LOGO_DIR=data / 'logos', SETTINGS=data / 'settings.json',
                     LIBRARY=data / 'logos.json').items():
        monkeypatch.setattr(R, k, str(v))
    monkeypatch.setenv('R4S_WORK', str(tmp_path / 'work'))
    monkeypatch.setattr(R.App, 'add_starter_logos', lambda self: None)
    monkeypatch.setattr(R.skingen, 'car_catalogue', lambda *a, **k: None)
    gate = threading.Event(); gate.set()

    def fake_generate(car, design, name, views=None, info=None, **k):
        gate.wait(20)
        for v in ('left', 'right', 'front', 'rear', 'top'):
            views[v] = Image.new('RGBA', (80, 40), (255, 0, 0, 255))
        info.update(decals=[dict(key='logo0', view='left', a=0, b=0, w=1, h=1, rot=0, label='Logo')],
                    frames={v: (-1, 1, -1, 1) for v in ('left', 'right', 'front', 'rear', 'top')})
        return str(tmp_path / 'out'), None
    monkeypatch.setattr(R.skingen, 'generate', fake_generate)
    cars = tmp_path / 'cars'
    for c in ('car_a', 'car_b'):
        os.makedirs(cars / c / 'skins' / 'stock')
    a = R.App(); a.withdraw()
    a.vars['cars_dir'].set(str(cars)); a.refresh_cars()
    a.gate = gate
    pick(a, 'car_a')
    yield a
    a.destroy()


def pick(app, car):
    app.vars['car'].set(car); app.car_box.event_generate('<<ComboboxSelected>>'); app.update()


def preview(app, during=None):
    """Press Preview and let the app's main loop run until it has finished; `during` runs while it is painting."""
    t0 = time.time()
    if during: app.gate.clear()

    def start():
        app.btn_prev.invoke()
        if during:
            app.after(200, lambda: (during(), app.gate.set()))
        app.after(300, check)

    def check():
        if (app.busy or app.log_box.get('1.0', 'end').count('PREVIEW ONLY') == 0) and time.time() - t0 < 30:
            app.after(50, check); return
        app.after(300, app.quit)                                # let the finished preview reach the window
    app.after(0, start)
    app.mainloop()
    assert not app.busy


def test_preview_shows(app):
    preview(app)
    assert app.views and app.info.get('decals')


def test_other_car_clears_preview(app):
    preview(app)
    app.sel = 'logo0'
    pick(app, 'car_b')
    assert not app.views and not app.info and app.sel is None and app.geom is None


def test_same_car_keeps_preview(app):
    preview(app)
    pick(app, 'car_a')                                          # picked again from the list: nothing changed
    assert app.views and app.info.get('decals')


def test_old_cars_late_preview_not_shown(app):
    preview(app, during=lambda: pick(app, 'car_b'))
    assert app.vars['car'].get() == 'car_b'
    assert not app.views and not app.info
