r"""A blank canvas (Nik 16 Nov: friends got "RATTY RACING" and Nik's name on a fresh install). Every start of the app
begins a new, blank livery: no team, driver, number or banner words, a plain white car, no logos on it, no window
stickers or tint. Kept: the cars folder, the car, the app colours and file options, and the logo library itself.
"Start new livery" clears the livery the same way at any time. A restart for new app colours keeps the livery.
python -m pytest -p no:cacheprovider tests/test_blank_start.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_theme_choice import make_app      # noqa: F401  (fixture)
import rattys4skin as R


def blank(d):
    assert d['team'] == '' and d['name'] == '' and d['number'] == '' and d['win_banner'] == ''
    assert d['pattern'] == 'none' and d['base'].lower() == '#ffffff'
    assert d['logos'] == [] and not d['win_enable'] and d['win_tint'] is None
    assert d['wheel_colour'] is None and d['tyre_colour'] is None and not d['adjust'] and d['paint_finish'] == 'standard'


def used_before(cars):
    os.makedirs(os.path.join(cars, 'car_a', 'skins', 'stock'), exist_ok=True)
    os.makedirs(R.LOGO_DIR, exist_ok=True)
    Image.new('RGBA', (20, 20), (255, 0, 0, 255)).save(os.path.join(R.LOGO_DIR, 'rat.png'))
    json.dump([dict(file='rat.png', name='rat', place='bonnet', places=['bonnet'], tint=False)], open(R.LIBRARY, 'w'))
    return dict(cars_dir=cars, car='car_a', team='RATTY RACING', name='Nicklearse101', number='101', pattern='sweep',
                base='#0c0b10', win_enable=True, win_banner='RATTY RACING', use_tint=True, use_wheels=True,
                ui_theme='ratty_purple', compress=False, show_grid=False,
                adjust_by_car={'car_a': {'logo:bonnet': {'da': 0.1}}})


def test_fresh_install_is_blank(make_app):
    blank(make_app().design())


def test_restart_is_blank_but_keeps_car_and_options(make_app, tmp_path):
    a = make_app(used_before(str(tmp_path / 'cars')))
    blank(a.design())
    assert a.vars['car'].get() == 'car_a' and a.vars['cars_dir'].get() == str(tmp_path / 'cars')
    assert R.theme.THEME == 'ratty_purple' and a.vars['compress'].get() is False and a.vars['show_grid'].get() is False
    assert [l['file'] for l in a.library] == ['rat.png']                     # the library stays
    assert json.load(open(R.LIBRARY))[0]['places'] == []


def test_new_colours_restart_keeps_the_livery(make_app, tmp_path, monkeypatch):
    a = make_app(used_before(str(tmp_path / 'cars')))
    a.vars['team'].set('MY TEAM')
    monkeypatch.setattr(R.subprocess, 'Popen', lambda cmd, **k: None)
    monkeypatch.setattr(a, 'destroy', lambda: None)
    a.vars['ui_theme_name'].set('Ice Blue'); a.on_theme()
    R.tk.Tk.destroy(a)
    b = make_app()
    assert b.design()['team'] == 'MY TEAM'
    R.tk.Tk.destroy(b)
    c = make_app()                                                            # and only that once
    assert c.design()['team'] == ''


def test_start_new_livery_button(make_app, tmp_path, monkeypatch):
    a = make_app(used_before(str(tmp_path / 'cars')))
    a.vars['team'].set('X'); a.vars['name'].set('Y'); a.vars['number'].set('7')
    a.vars['pattern_name'].set(R.skingen.PATTERNS['sweep']); a.vars['use_tint'].set(True)
    a.library[0]['places'] = ['doors']; a.adjust_by_car['car_a'] = {'k': {'da': 1}}
    a.views = {'left': Image.new('RGBA', (10, 10))}
    monkeypatch.setattr(R.messagebox, 'askyesno', lambda *x, **k: True)
    a.new_livery()
    blank(a.design())
    assert a.views == {} and a.vars['car'].get() == 'car_a'
    assert [l['file'] for l in a.library] == ['rat.png']


def test_start_new_livery_can_be_cancelled(make_app, monkeypatch):
    a = make_app()
    a.vars['team'].set('KEEP ME')
    monkeypatch.setattr(R.messagebox, 'askyesno', lambda *x, **k: False)
    a.new_livery()
    assert a.vars['team'].get() == 'KEEP ME'
