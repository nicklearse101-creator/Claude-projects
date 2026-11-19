r"""The app keeps where the last preview put everything (1.15, Nik 19 Nov): info['placed'] goes into the adjustments as
'at' - without counting as a change (no second preview) - and is saved; a spot changed while the preview was being made
is left alone; 'Pick it on the car' and Reset take it away; adjustments saved before 1.15 get the new logo keys.
The real window with a test data folder; the painting is faked (instant).
python -m pytest -p no:cacheprovider tests/test_keep_layout_app.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app, pick, preview          # noqa: F401  (app is a fixture)
import rattys4skin as R

AT = {'left': [0.1, 0.5, 0.3], 'right': [-0.1, 0.5, 0.3]}


def test_spots_kept_after_a_preview(app):
    app.extra['placed'] = {'logo0': AT}
    preview(app)
    assert app.adj()['logo0'] == {'at': AT}
    assert app.adj() == app.adjust_gen                    # not a change: the car is not drawn again for it
    saved = json.load(open(R.SETTINGS, encoding='utf8'))
    assert saved['adjust_by_car']['car_a']['logo0'] == {'at': AT}


def test_hand_moves_kept_with_the_spot(app):
    app.adj('logo0')['da'] = 0.2
    app.extra['placed'] = {'logo0': AT}
    preview(app)
    assert app.adj()['logo0'] == {'da': 0.2, 'at': AT} and app.adj() == app.adjust_gen


def test_reset_while_painting_is_not_undone(app):
    app.adj('logo0')['at'] = AT
    app.extra['placed'] = {'logo0': AT}
    preview(app, during=lambda: app.adj().pop('logo0'))  # 'Reset' pressed while the preview was being made
    assert 'logo0' not in app.adj()


def test_pick_takes_the_kept_spot_away(app):
    app.extra['placed'] = {'logo0': AT}
    preview(app)
    app.picking = 'logo0'; app.view_var.set('left'); app.geom = (0, 0, 80, 40)
    app.set_pick(40, 20)
    assert 'at' not in app.adj()['logo0'] and 'pin' in app.adj()['logo0']


def test_old_logo_keys_upgraded(app):
    Image.new('RGBA', (60, 40), (200, 30, 30, 255)).save(os.path.join(R.LOGO_DIR, 'rat.png'))
    app.library.append(dict(file='rat.png', name='rat', places=['doors'], tint=False))
    app.adjust_by_car['car_a'] = {'logo:doors': {'da': 0.1}}
    d = app.design()
    assert d['adjust'] == {'logo:doors:rat.png': {'da': 0.1}}
    assert app.adj() == {'logo:doors:rat.png': {'da': 0.1}}          # kept that way (saved with the settings)
