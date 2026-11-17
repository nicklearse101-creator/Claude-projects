r"""The app in 2D mode (protected cars, Nik 17 Nov): the preview shows the paint sheet, the number / names / logos are
dragged on it (its copy on the mirror panel follows, dragging the copy moves the original the mirrored way), the sheet
redraws itself when let go, 'Front of the car' turns the roof / bonnet logos, Create saves the sheet as the picture.
The engine's result is faked here (instant); tests/test_template2d.py checks the real painting.
python -m pytest -p no:cacheprovider tests/test_2d_ui.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import copy, os, sys, time
import numpy as np
import pytest
from PIL import Image, ImageTk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app, preview          # noqa: F401  (app is a fixture)
import rattys4skin as R

SHEET = Image.new('RGBA', (1000, 1000), (40, 0, 80, 255))
CLEAN = Image.new('RGBA', (1000, 1000), (0, 0, 255, 255))
INFO2D = dict(mode='2d', protected=True, source_skin='Template', size=(1000, 1000), front=0,
              islands2d={1: dict(x0=100, x1=500, y0=100, y1=400), 2: dict(x0=100, x1=500, y0=600, y1=900)},
              pairs2d={1: (2, 'v'), 2: (1, 'v')},
              decals2d=[dict(key='2d:number', label='number', u=300.0, v=750.0, w=120, h=80, rot=0.0, island=2,
                             sprite=Image.new('RGBA', (60, 40), (0, 255, 0, 255)), twin=[300.0, 250.0, 120, 80, 180.0])])


@pytest.fixture
def two_d(app, monkeypatch):
    def fake(car, design, name, views=None, info=None, **k):
        info.update(copy.deepcopy({k_: v for k_, v in INFO2D.items()}))
        info['sheet'], info['sheet_clean'] = SHEET.copy(), CLEAN.copy()
        out = os.path.join(os.path.dirname(car), 'out'); os.makedirs(out, exist_ok=True)
        return out, None
    monkeypatch.setattr(R.skingen, 'generate', fake)
    app.geometry('1100x800+-3000+-3000'); app.deiconify(); app.update()
    monkeypatch.setattr(R.messagebox, 'showinfo', lambda *a, **k: None)
    preview(app)
    app.update()
    return app


def shown(app, x, y):
    return np.asarray(ImageTk.getimage(app.preview_img).convert('RGB'))[int(y), int(x)]


def screen(app, u, v):
    ox, oy, k = app.geom2d
    return ox + u * k, oy + v * k


def press_drag(app, u, v, dx, dy):
    x, y = screen(app, u, v)
    app.on_press(type('E', (), dict(x=int(x), y=int(y)))())
    app.on_drag(type('E', (), dict(x=int(x + dx), y=int(y + dy)))())
    app.update()
    return x, y


def test_sheet_shown_with_its_boxes(two_d):
    assert two_d.is2d() and two_d.geom is None
    x, y = screen(two_d, 600, 500)
    assert tuple(shown(two_d, x, y)) == (40, 0, 80)                     # the sheet itself
    assert len(two_d.canvas.find_withtag('box')) == 2                   # the number and its copy
    assert str(two_d.front_bar.winfo_manager()) == 'pack'


def test_drag_moves_it_and_the_copy_follows(two_d):
    k = two_d.geom2d[2]
    x, y = press_drag(two_d, 300, 750, 50, 20)
    assert two_d.sel == '2d:number'
    ad = two_d.adj('2d:number')
    assert ad['u'] == pytest.approx(300 + 50 / k, abs=1) and ad['v'] == pytest.approx(750 + 20 / k, abs=1)
    b = two_d.boxes2d()[0]
    assert b['twin'][0] == pytest.approx(ad['u'], abs=1) and b['twin'][1] == pytest.approx(1000 - ad['v'], abs=2)
    assert two_d.canvas.find_withtag('live')
    assert tuple(shown(two_d, x, y)) == (0, 0, 255)                     # the old spot shows the sheet without decals


def test_dragging_the_copy_moves_the_original_mirrored(two_d):
    k = two_d.geom2d[2]
    press_drag(two_d, 300, 250, 0, 30)                                  # the copy, on the upper panel, dragged down
    assert two_d.adj('2d:number')['v'] == pytest.approx(750 - 30 / k, abs=1)


def test_let_go_redraws_and_edits_work(two_d, monkeypatch):
    calls = []
    monkeypatch.setattr(two_d, 'run', lambda save, auto=False: calls.append(auto))
    press_drag(two_d, 300, 750, 30, 0)
    two_d.on_release(None)
    t = time.time()
    while not calls and time.time() - t < 3: two_d.update(); time.sleep(0.05)
    assert calls == [True]
    two_d.edit('scale', 1.5); two_d.edit('rot', 90)
    assert two_d.adj('2d:number')['scale'] == pytest.approx(1.5) and two_d.adj('2d:number')['rot'] == 90


def test_front_buttons(two_d, monkeypatch):
    monkeypatch.setattr(two_d, 'changed', lambda wait=700: None)
    two_d.front_var.set('180'); two_d.on_front()
    assert two_d.adj('2d:front')['rot'] == 180
