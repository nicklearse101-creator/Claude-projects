"""Nik 22 Nov: the old skin's colours showed along panel edges in the game (the Accord's lime green as yellow lines).
They sat in the texture's gaps between panels, beyond the 12 texels pad_texture fills: the game's smaller texture levels
(mipmaps) blend them in. fill_gaps fills EVERY gap: near the panels exactly as pad_texture, further out from the panels
around it (pull-push) - nothing of the old skin is left between the panels.
python -m pytest -p no:cacheprovider tests/test_gap_fill.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, sys, time
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skingen as S
from test_speed import panels


def case(H, W, seed, n=40):
    rng = np.random.default_rng(seed)
    cov = panels(H, W, seed, n)
    a = np.zeros((H, W, 3), np.uint8); a[..., 0] = 255                   # the old skin: red
    paint = np.stack([np.zeros((H, W)), rng.integers(0, 256, (H, W)), rng.integers(0, 256, (H, W))], -1).astype(np.uint8)
    a[cov] = paint[cov]                                                    # the new paint: no red in it
    return Image.fromarray(a), cov


def test_no_old_colour_left_between_panels():
    for H, W in ((300, 257), (512, 512), (97, 640)):
        img, cov = case(H, W, 3)
        out = np.asarray(S.fill_gaps(img, cov))
        assert out[..., 0].max() == 0                                      # no red anywhere


def test_near_the_panels_as_before_and_panels_untouched():
    img, cov = case(400, 300, 5)
    old, new = np.asarray(S.pad_texture(img, cov)), np.asarray(S.fill_gaps(img, cov))
    near = old[..., 0] == 0                                                # what pad_texture filled (and the panels)
    assert np.array_equal(new[near], old[near])
    assert np.array_equal(new[cov], np.asarray(img)[cov])


def test_nothing_painted_nothing_changed():
    img, _ = case(64, 64, 1)
    assert np.asarray(S.fill_gaps(img, np.zeros((64, 64), bool))).tobytes() == img.tobytes()


def test_far_gaps_take_the_colour_around_them():
    a = np.zeros((256, 256, 3), np.uint8); a[...] = (255, 0, 0)
    cov = np.zeros((256, 256), bool)
    cov[:, :60] = True; a[:, :60] = (0, 0, 200)                           # a blue panel left, a green one right
    cov[:, 200:] = True; a[:, 200:] = (0, 200, 0)
    out = np.asarray(S.fill_gaps(Image.fromarray(a), cov)).astype(int)
    assert out[128, 75, 2] > out[128, 75, 1]                               # next to blue: blue-ish
    assert out[128, 185, 1] > out[128, 185, 2]                             # next to green: green-ish


def test_fast_on_4k():
    m = panels(4096, 4096, 3, n=900)
    img = Image.new('RGB', (4096, 4096), (200, 30, 30))
    t = time.time()
    S.fill_gaps(img, m)
    assert time.time() - t < 6.0
