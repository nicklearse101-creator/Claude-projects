r"""The app side of 'pick it on the car' and 'Report this car' (Nik, 12 Nov). Real window, test data, faked painting
(see test_car_change.py). python -m pytest -p no:cacheprovider tests/test_pick_ui.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import json, os, sys, types, zipfile
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app, pick, preview          # noqa: F401  (app is a fixture)
import rattys4skin as R

MISSING = [dict(key='logo:bonnet', label='logo on the bonnet')]


def click_at(app, a, b):
    """Click the preview at the spot (a, b) of the view showing."""
    x, y = app.to_screen(app.view_var.get(), a, b)
    app.on_press(types.SimpleNamespace(x=x, y=y))


def test_nothing_missing_no_bar(app):
    preview(app)
    assert not app.miss_bar.winfo_manager()


def test_missing_shown(app):
    app.extra['missing'] = MISSING
    preview(app)
    assert app.miss_bar.winfo_manager() and app.miss_box['values'] == ('logo on the bonnet',)
    pick(app, 'car_b')                                          # another car: the old car's list goes too
    assert not app.miss_bar.winfo_manager()


def test_pick_needs_one_side(app):
    app.extra['missing'] = MISSING
    preview(app)
    app.view_var.set('all'); app.on_view()
    app.start_pick()
    assert app.picking is None and 'side' in app.sel_label.cget('text').lower()


@pytest.mark.parametrize('view, a, b', [('top', 0.2, -0.5), ('left', 0.3, 0.4), ('front', -0.1, 0.2)])
def test_click_sets_the_spot(app, view, a, b):
    app.extra['missing'] = MISSING
    preview(app)
    app.view_var.set(view); app.on_view(); app.update()
    app.adj('logo:bonnet')['da'] = 0.5                          # an old hand move: the picked spot replaces it
    app.start_pick()
    assert app.picking == 'logo:bonnet'
    click_at(app, a, b)
    pin = app.adj()['logo:bonnet']
    assert app.picking is None and 'da' not in pin
    assert list(pin['pin']) == [view] and pin['pin'][view] == pytest.approx([a, b], abs=0.01)
    assert 'preview' in app.sel_label.cget('text').lower()
    saved = json.load(open(R.SETTINGS, encoding='utf8'))['adjust_by_car']['car_a']['logo:bonnet']
    assert saved['pin'][view] == pytest.approx([a, b], abs=0.01)


def test_pick_goes_to_the_design(app):
    app.adjust_by_car['car_a'] = {'logo:bonnet': {'pin': {'top': [0.1, -0.4]}}}
    assert app.design()['adjust']['logo:bonnet']['pin'] == {'top': [0.1, -0.4]}


def test_report_zip(app, tmp_path, monkeypatch):
    monkeypatch.setattr(R, 'desktop_dir', lambda: str(tmp_path / 'Desktop'))
    os.makedirs(tmp_path / 'Desktop')
    monkeypatch.setattr(R.skingen, 'car_catalogue', lambda car, cache_dir=None: {'body': ['skin.dds']})
    shown = []
    monkeypatch.setattr(R.messagebox, 'showinfo', lambda t, m, **k: shown.append(m))
    app.extra['missing'] = MISSING
    preview(app)
    path = app.report_car()
    assert os.path.dirname(path) == str(tmp_path / 'Desktop') and 'car_a' in os.path.basename(path)
    z = zipfile.ZipFile(path)
    assert set(z.namelist()) == {'report.txt', 'log.txt', 'design.json', 'catalogue.json', 'preview.png'}
    rep = z.read('report.txt').decode('utf8')
    assert 'car_a' in rep and R.VERSION in rep and 'logo on the bonnet' in rep
    assert json.loads(z.read('catalogue.json')) == {'body': ['skin.dds']}
    d = json.loads(z.read('design.json'))
    assert all(os.sep not in lg['path'] for lg in d.get('logos') or [])     # file names only, no folders
    assert os.path.expanduser('~') not in z.read('log.txt').decode('utf8')
    assert shown and 'discord' in shown[0].lower()


def test_report_catalogue_fails(app, tmp_path, monkeypatch):
    """A car the app cannot read at all is the one most worth reporting: the zip is still made."""
    monkeypatch.setattr(R, 'desktop_dir', lambda: str(tmp_path))
    monkeypatch.setattr(R.messagebox, 'showinfo', lambda *a, **k: None)
    def broken(*a, **k): raise RuntimeError('no paintable body texture found in this car')
    monkeypatch.setattr(R.skingen, 'car_catalogue', broken)
    z = zipfile.ZipFile(app.report_car())
    assert 'no paintable body texture' in z.read('report.txt').decode('utf8')
    assert 'catalogue.json' not in z.namelist() and 'preview.png' not in z.namelist()
