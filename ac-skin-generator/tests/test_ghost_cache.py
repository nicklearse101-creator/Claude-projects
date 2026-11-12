"""The ghost of the car being edited: its cache on disk, and that a slow ghost from an earlier car is ignored.
python -m pytest -p no:cacheprovider tests/test_ghost_cache.py -q"""
import os, sys, time, types
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R


def test_ghost_cache_valid(tmp_path):
    kn5, cache = tmp_path / 'car.kn5', tmp_path / 'car.png'
    kn5.write_bytes(b'x' * 10)
    assert not R.ghost_cache_valid(str(cache), str(kn5))                 # no cache yet
    Image.new('RGBA', (4, 4)).save(cache)
    assert not R.ghost_cache_valid(str(cache), str(kn5))                 # a picture with no record of the model
    R.save_ghost(Image.new('RGBA', (4, 4)), str(cache), str(kn5))
    assert R.ghost_cache_valid(str(cache), str(kn5))                     # made from this model
    t = os.path.getmtime(kn5)
    kn5.write_bytes(b'y' * 12); os.utime(kn5, (t - 1000, t - 1000))      # mod updated by a copy keeping an OLDER date
    assert not R.ghost_cache_valid(str(cache), str(kn5))


def test_ghost_cache_path():
    p = R.ghost_cache_path(r'D:\x\content\cars\some_car')
    assert p.endswith(os.path.join('ghosts', 'some_car.png')) and p.startswith(R.DATA_DIR)


def test_stale_ghost_ignored():
    redraws = []
    app = types.SimpleNamespace(ghost_token=2, ghost=None, ghost_car='', _bg_cache='old', redraw=lambda: redraws.append(1))
    old, new = Image.new('RGBA', (2, 2)), Image.new('RGBA', (3, 3))
    R.App._set_ghost(app, 1, old, 'car_a')                               # from a car picked before: ignored
    assert app.ghost is None and app.ghost_car == '' and not redraws
    R.App._set_ghost(app, 2, new, 'car_b')
    assert app.ghost is new and app.ghost_car == 'car_b' and app._bg_cache is None and redraws == [1]


def _stub(**kw):
    import queue
    app = types.SimpleNamespace(_ghost_q=queue.Queue(), _ghost_pending=0, ghost_token=0, ghost=None, ghost_car='',
                                _bg_cache='x', redraws=[], timers=[])
    app.redraw = lambda: app.redraws.append(1)
    app.after = lambda ms, fn, *a: app.timers.append(ms)
    app._set_ghost = lambda *a: R.App._set_ghost(app, *a)
    app._poll_ghost = lambda: R.App._poll_ghost(app)
    app.__dict__.update(kw)
    return app


def test_poll_ghost_applies_result_from_thread():
    """The drawing thread never calls Tk: it queues the ghost; the window picks it up (works before mainloop too)."""
    img = Image.new('RGBA', (3, 3))
    app = _stub(ghost_token=2, _ghost_pending=1)
    app._ghost_q.put((2, img, 'car_b'))
    R.App._poll_ghost(app)
    assert app.ghost is img and app.ghost_car == 'car_b' and app._ghost_pending == 0 and app.timers == []


def test_poll_ghost_waits_while_drawing():
    app = _stub(ghost_token=1, _ghost_pending=1)
    R.App._poll_ghost(app)
    assert app.ghost is None and app.timers                           # nothing yet: looks again a little later
