r"""Help for first-time users (Nik 16 Nov): a guided tour on the first start and a tip on every control, both
switched off with "Show help" on the Car tab; "Show me round" starts the tour again.
(conftest.py keeps the tour away from the other tests; these switch it back on.)
python -m pytest -p no:cacheprovider tests/test_tour.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import json, os, sys, time
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_theme_choice import make_app      # noqa: F401  (fixture)
import rattys4skin as R
import tour


@pytest.fixture(autouse=True)
def tour_on(monkeypatch):
    monkeypatch.delenv('R4S_NO_TOUR', raising=False)


def pump(a, secs):
    t = time.time()
    while time.time() - t < secs: a.update(); time.sleep(0.02)


def test_tour_on_first_start_and_every_step_shows_its_control(make_app):
    a = make_app()
    a.geometry('1320x840+-3000+-3000'); a.deiconify()
    pump(a, 1.5)
    assert a.tour is not None and a.tour.i == 0
    n = len(a.tour.steps)
    assert n >= 12
    for k in range(n):
        tab, w, head, text = a.tour.steps[a.tour.i]
        assert head and text
        if w is not None:
            assert w.winfo_ismapped(), head                    # its tab is showing
        a.tour.next(); a.update()
    assert a.tour is None
    assert json.load(open(R.SETTINGS))['tour_done'] is True


def test_no_tour_once_done_or_with_help_off(make_app):
    a = make_app({'tour_done': True})
    pump(a, 1.5)
    assert a.tour is None
    R.tk.Tk.destroy(a)
    b = make_app({'tips': False})
    pump(b, 1.5)
    assert b.tour is None


def test_show_me_round_starts_it_again(make_app):
    a = make_app({'tour_done': True})
    a.start_tour(); a.update()
    assert a.tour is not None
    a.tour.close()
    assert a.tour is None


def test_tips_on_controls(make_app):
    a = make_app()
    tips = a.tooltips
    assert len(tips) >= 40
    t = next(t for t in tips if t.w is a.help['pattern'] or t.w.master is a.help['pattern'])
    t.show(); assert t.win is not None
    t.hide(); assert t.win is None
    a.vars['tips'].set(False)
    t.enter(); t.show()
    assert t.win is None                                      # help off: no tips
