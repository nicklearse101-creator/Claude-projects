r"""Speed-ups that must not change a single pixel (Nik 16 Nov: "faster without losing functionality").
 - square max / min filters as two 1-D passes: the same pixels as PIL's MaxFilter / MinFilter (edges repeated),
   ~20x quicker for the big windows the stock-skin comparison uses (35 x 35 on a 2K texture);
python -m pytest -p no:cacheprovider tests/test_rank_filter.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys, time
import numpy as np
import pytest
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen


@pytest.mark.parametrize('size', [3, 5, 7, 13, 35])
@pytest.mark.parametrize('op', ['max', 'min'])
def test_same_pixels_as_pil(size, op):
    rng = np.random.default_rng(size)
    for arr in (rng.integers(0, 256, (97, 131), dtype=np.uint8),
                ((rng.random((120, 90)) > 0.93) * 255).astype(np.uint8)):
        im = Image.fromarray(arr)
        want = im.filter(ImageFilter.MaxFilter(size) if op == 'max' else ImageFilter.MinFilter(size))
        got = skingen.rank_filter(im, size, op)
        assert np.array_equal(np.asarray(want), np.asarray(got))


def test_faster_on_a_big_mask():
    im = Image.fromarray(((np.random.default_rng(1).random((2048, 2048)) > 0.5) * 255).astype(np.uint8))
    t = time.time(); im.filter(ImageFilter.MinFilter(35)); slow = time.time() - t
    t = time.time(); skingen.rank_filter(im, 35, 'min'); fast = time.time() - t
    assert fast < slow / 4
