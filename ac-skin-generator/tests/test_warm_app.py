"""1.16 (Nik 20 Nov): a picked car is got ready for its first preview in the background while the livery is set up;
Preview / Create stop that (the step under way is finished first, then the preview uses what was done).
The real window with a test data folder; the warm-up and the painting are faked.
python -m pytest -p no:cacheprovider tests/test_warm_app.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, sys, threading, time
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app as app_, pick, preview          # noqa: F401  (app_ is a fixture)
import rattys4skin as R


@pytest.fixture
def app(app_, monkeypatch):
    monkeypatch.delenv('R4S_NO_WARM', raising=False)
    calls = []

    def fake_warm(car, design, res, stop, copy_from=None):
        me = dict(car=os.path.basename(car), res=res, design=design, stop=stop, t=time.time())
        calls.append(me)
        while not stop() and time.time() - me['t'] < 20:
            time.sleep(0.02)
        me['stopped'] = stop()
        return False
    monkeypatch.setattr(R.skingen, 'warm_up', fake_warm)
    app_.warm_calls = calls
    yield app_
    app_.stop_warm()


def settle(app, secs=1.2):
    t = time.time()
    while time.time() - t < secs:
        app.update(); time.sleep(0.02)


def test_picking_a_car_gets_it_ready(app):
    pick(app, 'car_b')
    assert not app.warm_calls                                   # not straight away: the picking may go on
    settle(app)
    assert [c['car'] for c in app.warm_calls] == ['car_b']
    assert app.warm_calls[0]['res'] == (4096 if app.vars['hires'].get() else None)
    assert app.warm_calls[0]['design']['logos'] is not None              # the livery as it is set up now
    app.vars['hires'].set(not app.vars['hires'].get())                   # another texture size: got ready again
    app.refresh_skins(); settle(app)
    assert len(app.warm_calls) == 2 and app.warm_calls[0]['stopped']


def test_scrolling_through_cars_starts_one(app):
    for c in ('car_b', 'car_a', 'car_b', 'car_a'):
        pick(app, c)
    settle(app)
    assert [c['car'] for c in app.warm_calls] == ['car_a']


def test_same_car_again_not_started_twice(app):
    pick(app, 'car_b'); settle(app)
    pick(app, 'car_b'); settle(app)
    assert len(app.warm_calls) == 1


def test_other_car_stops_the_last_one(app):
    pick(app, 'car_b'); settle(app)
    pick(app, 'car_a'); settle(app)
    assert [c['car'] for c in app.warm_calls] == ['car_b', 'car_a']
    assert app.warm_calls[0]['stopped'] and not app.warm_calls[1].get('stopped')


def test_preview_stops_it(app):
    pick(app, 'car_b'); settle(app)
    said = []
    real = app.set_progress
    app.set_progress = lambda f, t: (said.append(t), real(f, t))
    preview(app)
    assert app.warm_calls[0]['stopped']
    assert said[0] == 'Finishing getting the car ready…'
    app.set_progress = real


def test_preview_before_it_started(app):
    pick(app, 'car_b')                                          # Preview pressed before the warm-up began: none starts
    preview(app)
    settle(app)
    assert not app.warm_calls


def test_off_by_switch(app, monkeypatch):
    monkeypatch.setenv('R4S_NO_WARM', '1')
    pick(app, 'car_b'); settle(app)
    assert not app.warm_calls


def test_car_with_a_preview_not_got_ready_again(app):
    preview(app)                                                # car_a has a preview now
    pick(app, 'car_a'); settle(app)
    assert not app.warm_calls
