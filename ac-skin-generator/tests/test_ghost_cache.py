"""The ghost of the car being edited: its cache on disk, and that a slow ghost from an earlier car is ignored.
python -m pytest -p no:cacheprovider tests/test_ghost_cache.py -q"""
import os, sys, time, types
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rattys4skin as R


def test_ghost_cache_valid(tmp_path):
    kn5, cache = tmp_path / 'car.kn5', tmp_path / 'car.png'
    kn5.write_bytes(b'x')
    assert not R.ghost_cache_valid(str(cache), str(kn5))                 # no cache yet
    Image.new('RGBA', (4, 4)).save(cache)
    t = time.time()
    os.utime(kn5, (t - 100, t - 100)); os.utime(cache, (t, t))
    assert R.ghost_cache_valid(str(cache), str(kn5))                     # made after the model
    os.utime(kn5, (t + 100, t + 100))
    assert not R.ghost_cache_valid(str(cache), str(kn5))                 # the car was updated since


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
