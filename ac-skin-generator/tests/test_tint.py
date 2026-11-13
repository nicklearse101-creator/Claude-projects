r"""Tinted windows, done the way Content Manager's paint shop does it (Nik 13 Nov: "the window tint still sucks"):
the whole glass texture gets the film, so it reaches every edge; the windscreen (unless asked) keeps its area clear
with a margin, so no tint creeps onto it; lamps that share the glass texture get a clear copy through CSP.
python -m pytest -p no:cacheprovider tests/test_tint.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
TINT = '#203040'


@pytest.fixture(scope='module')
def talbot():
    return skingen.Car(os.path.join(CARS, 'talbot_sunbeam_lotus_81_works_backup_v6'), log=lambda *a: None)


@pytest.fixture(scope='module')
def corvette():
    return skingen.Car(os.path.join(CARS, 'corvette_z06_gt3r'), log=lambda *a: None)


def run(car, windscreen=False):
    d = dict(skingen.DEFAULT_DESIGN, win_tint=TINT, win_tint_dark=0.6, win_tint_windscreen=windscreen)
    out, layers, clear = skingen.tint_windows(car, d, {}, None, lambda *a: None)
    return out, clear


def alpha_up(car, tex, img):
    before = np.asarray(skingen.load_image(car.kn5.textures[tex]).convert('RGBA').resize(img.size)).astype(int)
    after = np.asarray(img.convert('RGBA')).astype(int)
    return after[..., 3] - before[..., 3]


def ws_texels(car, tex, img):
    """Texels the windscreen triangles cover (outside glass, facing forward, front half of the car)."""
    ext, inner = skingen.window_meshes(car)
    ws = [skingen.windscreen_part(car, m) for m in ext + inner if m.mat.samplers.get('txDiffuse') == tex]
    ws = [m for m in ws if m is not None]
    tm = skingen.TexelMap(ws, img.width, img.height, lambda *a: None)
    return tm.yy, tm.xx


def test_whole_texture_tinted_to_the_edges(talbot):
    out, _ = run(talbot, windscreen=True)
    up = alpha_up(talbot, 'glass.png', out['glass.png'])
    assert (up > 20).mean() > 0.97                                   # every texel, not just the mapped ones


def test_windscreen_left_clear(corvette):
    out, _ = run(corvette)
    img = out['EXT_Glass.dds']
    up = alpha_up(corvette, 'EXT_Glass.dds', img)
    yy, xx = ws_texels(corvette, 'EXT_Glass.dds', img)
    assert len(yy) > 1000
    assert (np.abs(up[yy, xx]) <= 2).mean() > 0.99                  # the windscreen: as it was
    assert (up > 20).mean() > 0.5                                    # the rest: tinted


def test_lamps_and_separate_windscreen_get_a_clear_copy(talbot):
    _, clear = run(talbot)
    meshes = {m for c in clear for m in c['meshes']}
    assert 'EXT_GLASS_CENTER' in meshes and 'INT_GLASS_CENTER' in meshes      # the windscreen, outside and in
    assert any(m.startswith('RALLY_SPOT') for m in meshes)                     # spot lamps on the glass texture
    assert not any(m in meshes for m in ('EXT_GLASS_LEFT_2', 'EXT_GLASS_REAR', 'EXT_GLASS_DOOR_L'))


def test_windscreen_tinted_when_asked(talbot):
    _, clear = run(talbot, windscreen=True)
    meshes = {m for c in clear for m in c['meshes']}
    assert 'EXT_GLASS_CENTER' not in meshes and any(m.startswith('RALLY_SPOT') for m in meshes)


def test_skin_has_the_clear_copies(tmp_path):
    d = dict(skingen.DEFAULT_DESIGN, win_tint=TINT, win_tint_dark=0.6)
    out, *_ = skingen.generate(os.path.join(CARS, 'talbot_sunbeam_lotus_81_works_backup_v6'), d, 'tint', out_root=str(tmp_path),
                               log=lambda *a: None, write=True)
    ini = open(os.path.join(out, 'ext_config.ini')).read()
    assert 'EXT_GLASS_CENTER' in ini and 'RALLY_SPOT' in ini
    for line in ini.splitlines():
        if line.startswith('RESOURCE_FILE_0'):
            assert os.path.isfile(os.path.join(out, line.split('=', 1)[1].strip()))
