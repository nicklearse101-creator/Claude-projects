"""Nik 23 Nov: on the Lacetti the livery did not reach the edges - the A-pillar edges, sills, arch flares and mirrors
stayed black, because all 11 stock skins keep them the same. They take the livery now; grilles, intakes, lamps and
the mirror glass stay as they are.
python -m pytest -p no:cacheprovider tests/test_trims.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen as S

LACETTI = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\wtcc_chevrolet_lacetti'
pytestmark = pytest.mark.skipif(not os.path.isdir(LACETTI), reason='the Lacetti is not installed')


@pytest.fixture(scope='module')
def maps():
    car = S.Car(LACETTI, lambda *a: None)
    tex = car.body_textures[0]
    out = {}
    for on in (False, True):
        S.PAINT_TRIMS, S.AO_SHADING = on, False
        mem = {}
        S._map_texture(car, tex, 1024, 1024, mem, lambda *a: None)
        out[on] = mem
    S.PAINT_TRIMS, S.AO_SHADING = True, True
    return car, out


def painted_share(car, mem, where, dark=False):
    tm = mem['tm']; paint = mem['stock'][2]
    sel = where(tm.P, tm.N, car)
    if dark: sel &= mem['stock'][0][tm.yy, tm.xx].mean(-1) < 25          # (the black flare, not the painted wing)
    return paint[tm.yy[sel], tm.xx[sel]].mean(), sel.sum()


ARCH = lambda P, N, car: ((P[:, 0] > car.hi[0] - 0.2) & (np.abs(P[:, 2] - car.wheels['WHEEL_LF'][2]) < 0.55)
                          & (P[:, 1] > car.lo[1] + 0.25) & (P[:, 1] < car.lo[1] + 0.75) & (N[:, 0] > 0.5))
GRILLE = lambda P, N, car: ((P[:, 2] > car.hi[2] - 0.35) & (np.abs(P[:, 0]) < 0.3) & (P[:, 1] > car.lo[1] + 0.45)
                            & (P[:, 1] < car.lo[1] + 0.7) & (N[:, 2] > 0.5))


def test_arch_flares_take_the_livery(maps):
    """The black flare round the front wheel (seen from the side): left out before, painted now."""
    car, m = maps
    tm = m[True]['tm']
    w = car.wheels['WHEEL_LF']
    sel = ((tm.P[:, 0] > car.hi[0] - 0.25) & (np.abs(tm.P[:, 2] - w[2]) < 0.7) & (tm.P[:, 1] < w[1] + car.wheel_r + 0.2)
           & (tm.N[:, 0] > 0.5))
    before, after = m[False]['stock'][2][tm.yy, tm.xx], m[True]['stock'][2][tm.yy, tm.xx]
    left_out = sel & ~before
    assert left_out.sum() > 200 and after[left_out].mean() > 0.8


def test_grille_stays(maps):
    car, m = maps
    before, n = painted_share(car, m[False], GRILLE)
    after, _ = painted_share(car, m[True], GRILLE)
    assert n > 100 and after <= before + 0.05


def test_mirror_glass_stays_housing_painted(maps):
    car, m = maps
    tm = m[True]['tm']; paint = m[True]['stock'][2]
    mir = np.array([bool(S.MIRROR_RE.search(n_)) for n_ in tm.mesh_of_tri])[tm.tri]
    back = mir & (tm.N[:, 2] < -0.7)
    side = mir & (np.abs(tm.N[:, 2]) < 0.3)
    assert paint[tm.yy[side], tm.xx[side]].mean() > 0.8
    was = m[False]['stock'][2]
    assert back.sum() > 50 and paint[tm.yy[back], tm.xx[back]].mean() <= was[tm.yy[back], tm.xx[back]].mean()


def test_lamps_never(maps):
    car, m = maps
    lamps = m[True].get('lamps')
    assert lamps is not None and not (m[True]['stock'][2] & lamps).any()


def test_only_more_paint(maps):
    car, m = maps
    a, b = m[False]['stock'][2], m[True]['stock'][2]
    assert not (a & ~b).any() and (b & ~a).any()
