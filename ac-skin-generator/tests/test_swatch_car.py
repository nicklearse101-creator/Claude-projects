r"""The pattern preview is a simple car (Nik 16 Nov: "a preview of the side and top of the car rather than the split
blank preview"): its side over its top, the pattern on the body, dark windows, wheels, clear around the car.
python -m pytest -p no:cacheprovider tests/test_swatch_car.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen


def swatch(**k):
    return skingen.pattern_swatch(dict(skingen.DEFAULT_DESIGN, **k), 300)


def test_car_shape_on_clear_background():
    im = swatch(pattern='none', base='#ff0000')
    a = np.asarray(im)
    assert im.mode == 'RGBA' and im.width == 300 and 180 < im.height < 280
    assert a[0, 0, 3] == 0 and a[-1, -1, 3] == 0                  # corners: no car
    opaque = a[..., 3] > 200
    assert 0.25 < opaque.mean() < 0.75                            # a car, not a full rectangle
    red = opaque & (a[..., 0] > 150) & (a[..., 1] < 90)
    assert red.mean() > 0.15                                      # the body is the base colour
    dark = opaque & (a[..., :3].max(2) < 70)
    assert dark.mean() > 0.02                                     # windows and tyres


def test_pattern_shows_on_the_body():
    a = np.asarray(swatch(pattern='none', base='#ffffff')).astype(int)
    b = np.asarray(swatch(pattern='gt_sash', base='#ffffff', accent='#0000ff')).astype(int)
    assert (np.abs(a - b).sum(2) > 60).mean() > 0.05


def test_side_over_top():
    a = np.asarray(swatch(pattern='none', base='#00ff00'))
    rows = (a[..., 3] > 200).mean(1)
    gap = np.flatnonzero(rows < 0.02)
    mid = gap[(gap > 40) & (gap < len(rows) - 40)]
    assert len(mid)                                               # two pictures: a clear gap between side and top
