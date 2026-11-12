"""The v1.10 patterns: sane colours, the same every time, drawn on the sides and the top, quick enough.
python -m pytest -p no:cacheprovider tests/test_patterns_plus.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys, time
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen, patterns_plus

CAR = skingen.SwatchCar()
rng = np.random.default_rng(5)
n = 60000
SIDE = np.stack([np.full(n, 0.86), rng.uniform(0.05, 1.2, n), rng.uniform(-2.1, 2.1, n)], 1)
TOP = np.stack([rng.uniform(-0.8, 0.8, n), np.full(n, 1.3), rng.uniform(-2.1, 2.1, n)], 1)
NS, NT = np.tile([1.0, 0, 0], (n, 1)), np.tile([0, 1.0, 0], (n, 1))
PAL = [(12, 11, 16), (112, 32, 210), (190, 110, 255), (240, 238, 245)]


def run(k, P, N, pal=PAL):
    return patterns_plus.paint(k, np.tile(np.float32(pal[0]), (len(P), 1)), P, N, CAR, 0.15, 0.8, *pal)


@pytest.mark.parametrize('k', list(patterns_plus.NAMES))
def test_pattern(k):
    t = time.time()
    a, b = run(k, SIDE, NS), run(k, TOP, NT)
    assert time.time() - t < 2.0
    for c in (a, b):
        assert c.shape == (n, 3) and np.isfinite(c).all() and c.min() >= 0 and c.max() <= 255
    assert np.array_equal(a, run(k, SIDE, NS))                               # the same every time
    changed = lambda c: (np.abs(c - np.float32(PAL[0])).max(1) > 10).mean()
    assert changed(a) > 0.02 and changed(b) > 0.005                         # something on the side and on top
    assert changed(a) < 0.995                                               # and not the whole side


@pytest.mark.parametrize('k', list(patterns_plus.NAMES))
def test_pattern_uses_the_colours(k):
    """Another accent colour shows up in the pattern: it is drawn in the design's colours, not fixed ones
    (carbon lower body is carbon by design, so its accent edge is what changes)."""
    other = [PAL[0], (20, 200, 40), PAL[2], PAL[3]]
    assert not np.array_equal(run(k, SIDE, NS), run(k, SIDE, NS, other))


def test_names_listed_in_the_app():
    assert all(skingen.PATTERNS[k] == v for k, v in patterns_plus.NAMES.items())
    assert list(skingen.PATTERNS)[-2:] == ['picture', 'none']
