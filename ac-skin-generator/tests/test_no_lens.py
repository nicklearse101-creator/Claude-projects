r"""The headlight-lens colour option is gone (Nik 16 Nov: "the cast light in game is the same as the lenses").
No lens controls, and old settings with the lens ticked no longer colour the lamps.
python -m pytest -p no:cacheprovider tests/test_no_lens.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app          # noqa: F401  (app is a fixture)
import rattys4skin as R


def texts(w):
    out = []
    try: out.append(str(w.cget('text')))
    except Exception: pass
    for c in w.winfo_children(): out += texts(c)
    return out


def test_no_lens_controls(app):
    assert not [t for t in texts(app) if 'lens' in t.lower()]
    assert 'Wheels' in app.tabbar.titles and 'Lights & wheels' not in app.tabbar.titles


def test_old_lens_setting_does_nothing(app):
    app.var('use_lens').set(True); app.var('lens_colour').set('#ff0000')
    assert app.design()['lens_colour'] is None


def test_lens_not_saved(app):
    app.save_cfg()
    saved = json.load(open(R.SETTINGS, encoding='utf8'))
    assert 'use_lens' not in saved and 'lens_colour' not in saved
