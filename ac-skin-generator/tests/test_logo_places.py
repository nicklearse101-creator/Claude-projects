r"""One logo on several parts of the car (Nik 13 Nov: "if I put it on the rear quarter and bonnet, it gets moved off
one surface"). Picking a place adds it; 'Take off' removes one; 'Not used' removes all; old libraries carry over.
python -m pytest -p no:cacheprovider tests/test_logo_places.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import json, os, sys
import pytest
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app, pick, preview          # noqa: F401  (app is a fixture)
import rattys4skin as R
import skingen

CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\abarth500'


def add_logo(app, name='rat'):
    f = name + '.png'
    Image.new('RGBA', (60, 40), (200, 30, 30, 255)).save(os.path.join(R.LOGO_DIR, f))
    app.library.append(dict(file=f, name=name, place='', tint=False))
    app.refresh_library()
    i = len(app.library) - 1
    app.tree.selection_set(str(i)); app.update()
    return i


def choose(app, place):
    app.place_var.set(R.PLACE_NAMES.get(place, 'Not used')); app.place_box.event_generate('<<ComboboxSelected>>'); app.update()


def placed(app):
    return [(os.path.basename(l['path']), l['place']) for l in app.design()['logos']]


def test_one_logo_on_two_places(app):
    add_logo(app)
    choose(app, 'bonnet'); choose(app, 'rear_quarters')
    assert placed(app) == [('rat.png', 'bonnet'), ('rat.png', 'rear_quarters')]
    assert 'Bonnet' in app.tree.set('0', 'place') and 'Rear quarters' in app.tree.set('0', 'place')
    assert len(app.used_tree.get_children()) == 2
    saved = json.load(open(R.LIBRARY, encoding='utf8'))[0]
    assert saved['places'] == ['bonnet', 'rear_quarters']


def test_same_place_twice_is_once(app):
    add_logo(app)
    choose(app, 'bonnet'); choose(app, 'bonnet')
    assert placed(app) == [('rat.png', 'bonnet')]


def test_take_one_off(app):
    add_logo(app)
    choose(app, 'bonnet'); choose(app, 'rear_quarters')
    row = next(r for r in app.used_tree.get_children() if app.used_tree.set(r, 'place') == 'Rear quarters')
    app.used_tree.selection_set(row); app.update()
    app.take_off()
    assert placed(app) == [('rat.png', 'bonnet')]


def test_not_used_takes_all_off(app):
    add_logo(app)
    choose(app, 'bonnet'); choose(app, 'doors')
    choose(app, '')
    assert placed(app) == []


def test_background_or_tint_change_keeps_the_places(app):
    add_logo(app)
    choose(app, 'bonnet'); choose(app, 'doors')
    app.place_var.set(R.PLACE_NAMES['roof'])                     # showing in the box, but not picked
    app.bg_var.set(R.BG_MODES['keep']); app.on_logo_props()
    app.tint_var.set(True); app.on_logo_props()
    assert placed(app) == [('rat.png', 'bonnet'), ('rat.png', 'doors')]
    assert app.library[0]['bg'] == 'keep' and app.library[0]['tint'] is True


def test_old_library_carries_over(app):
    lib = [dict(file='old.png', name='old', place='doors', tint=False)]
    Image.new('RGBA', (20, 20), (0, 0, 0, 255)).save(os.path.join(R.LOGO_DIR, 'old.png'))
    json.dump(lib, open(R.LIBRARY, 'w', encoding='utf8'))
    app.library = app.load_library(); app.refresh_library()
    assert placed(app) == [('old.png', 'doors')]


def test_both_painted_on_the_car(tmp_path):
    logo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'starter_logos', 'ratty_racing_logo.jpg')
    d = dict(skingen.DEFAULT_DESIGN, number='', team='', name='',
             logos=[dict(path=logo, place='bonnet', tint=False, bg='auto'), dict(path=logo, place='rear_quarters', tint=False, bg='auto')])
    info = {}
    skingen.generate(CAR, d, 'two', out_root=str(tmp_path), log=lambda *a: None, info=info, write=False)
    keys = {x['key'] for x in info['decals']}
    assert {'logo:bonnet', 'logo:rear_quarters'} <= keys and info['missing'] == []
