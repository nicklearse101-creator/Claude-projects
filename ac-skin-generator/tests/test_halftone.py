r"""Halftone dots (Nik 16 Nov: "it doesn't seem to do anything") - they were drawn by the Sweep pattern only. Now
every pattern gets them: dots on the lower sides, big near the sills and fading out upwards, only on plain base
colour (the pattern's own shapes stay clean), in a colour that shows on the base.
python -m pytest -p no:cacheprovider tests/test_halftone.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

CAR = skingen.SwatchCar()


def side(n=200):
    z, y = np.meshgrid(np.linspace(1.9, -1.9, n), np.linspace(0.16, 0.8, n // 2))
    P = np.stack([np.full(z.size, 0.86), y.ravel(), z.ravel()], 1)
    return P, np.tile([1.0, 0, 0], (len(P), 1))


def colours(pattern, halftone, P, N, **k):
    d = dict(skingen.DEFAULT_DESIGN, pattern=pattern, halftone=halftone, base='#ffffff', accent='#d01010', **k)
    return skingen.pattern_colours(d, P, N, CAR, 0.15, 0.8, lambda m: None)


@pytest.mark.parametrize('pattern', ['none', 'stripes', 'split', 'speed_lines', 'gt_sash'])
def test_dots_on_every_pattern(pattern):
    P, N = side()
    off, on = colours(pattern, False, P, N), colours(pattern, True, P, N)
    changed = np.abs(on - off).sum(1) > 1
    assert changed.mean() > 0.03                          # plenty of dots
    plain = np.abs(off - skingen.rgb('#ffffff')).sum(1) < 1
    assert not (changed & ~plain).any()                  # only on plain base colour


def test_dots_fade_upwards():
    P, N = side()
    d = np.abs(colours('none', True, P, N) - colours('none', False, P, N)).sum(1) > 1
    low, high = d[P[:, 1] < 0.35].mean(), d[P[:, 1] > 0.6].mean()
    assert low > 0.1 and high < low / 3


def test_dots_show_on_a_base_like_the_accent():
    """Accent = base colour: the dots take the text colour instead, so they still show."""
    P, N = side()
    c = skingen.pattern_colours(
        dict(skingen.DEFAULT_DESIGN, pattern='none', halftone=True, base='#d01010', accent='#d01010', text='#ffffff'),
        P, N, CAR, 0.15, 0.8, lambda m: None)
    assert (np.abs(c - skingen.rgb('#d01010')).sum(1) > 100).mean() > 0.03
