"""Preview views with a clean cut-out (alpha = the car's coverage) and the ghost view.
python -m pytest -p no:cacheprovider tests/test_render_alpha.py -q"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6'


@pytest.fixture(scope='module')
def car():
    return skingen.Car(CAR, log=lambda *a: None)


def test_alpha_rgb_identical(car):
    plain = np.asarray(skingen.render_view(car, 'left', {}, width=400))
    rgba = np.asarray(skingen.render_view(car, 'left', {}, width=400, alpha=True))
    assert rgba.shape[2] == 4
    assert np.array_equal(plain, rgba[..., :3])


def test_alpha_coverage(car):
    a = np.asarray(skingen.render_view(car, 'left', {}, width=400, alpha=True))[..., 3]
    h, w = a.shape
    assert a[2, 2] == 0
    assert a[int(h * 0.6), w // 2] == 255          # the door, middle of the car


def test_ghost_view(car):
    g = skingen.ghost_view(car)
    assert g.mode == 'RGBA' and g.width == 1200
    a = np.asarray(g)[..., 3]
    assert a.min() == 0 and a.max() == 255
