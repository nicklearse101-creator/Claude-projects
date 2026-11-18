r"""Interior colours (Nik 17-18 Nov; tested in game on the MX-5 Cup: purple seats, "orange as orange" cage).
 - parts found by name (belts before seats, stitches / displays / LOD sheets left alone);
 - colour tiles: OKLab lightness matching with the grain kept; shading sheets: the unshadowed level becomes the colour,
   nothing paler than it; a texture shared with other parts: only this part's texels;
 - a texture the outside of the car uses is never changed; off = nothing written.
python -m pytest -p no:cacheprovider tests/test_interior.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
import pytest
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen
import interior as I

CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
MX5 = os.path.join(CARS, 'ks_mazda_mx5_cup')


@pytest.fixture(scope='module')
def mx5():
    return skingen.Car(MX5, log=lambda *a: None)


def test_parts_found_on_the_mx5(mx5):
    parts, notes = I.find_parts(mx5)
    got = {g: {j['tex']: j['kind'] for j in jobs} for g, jobs in parts.items()}
    assert got['seats'] == {'leather.dds': 'tile'}
    assert got['alcantara'] == {'alcnt.dds': 'tile'}
    assert got['cage'] == {'INT_RollBar_OCC.dds': 'sheet'}
    assert 'Cockpit_Belt.png' in got['belts']                          # belts, not seats
    alltex = {t for v in got.values() for t in v}
    assert 'Stitches.png' not in alltex and 'PlasticDetail.dds' not in alltex   # stitches kept; plastic is the outside's too


def lum(img):
    a = np.asarray(img.convert('RGB')).astype(np.float32) / 255
    return I.oklab(a)


def test_tile_takes_the_colour_and_keeps_the_grain(mx5):
    src = skingen.load_image(mx5.kn5.textures['leather.dds'])
    out = I.recolour(src, (155, 61, 255), 'tile')
    a, b = lum(src), lum(out)
    target = I.oklab(np.array([155, 61, 255], np.float32) / 255)
    assert abs(np.median(b[..., 0]) - target[0]) < 0.03
    assert np.median(b[..., 2]) < -0.1                                   # purple (blue side of b*)
    hp = lambda L: L - np.asarray(Image.fromarray((L * 255).astype(np.uint8)).resize((64, 64)).resize(L.shape[::-1]), np.float32) / 255
    assert np.corrcoef(hp(a[..., 0]).ravel(), hp(b[..., 0]).ravel())[0, 1] > 0.7        # the grain


def test_sheet_never_paler_than_the_colour(mx5):
    src = skingen.load_image(mx5.kn5.textures['INT_RollBar_OCC.dds'])
    out = I.recolour(src, (255, 106, 0), 'sheet')
    t = I.oklab(np.array([255, 106, 0], np.float32) / 255)
    b = lum(out)
    used = lum(src)[..., 0] > 0.08
    assert b[..., 0][used].max() <= t[0] + 0.01
    assert abs(np.percentile(b[..., 0][used], 90) - t[0]) < 0.03       # the unshadowed paint = the colour


def test_region_only_its_own_texels():
    img = Image.new('RGB', (64, 64), (128, 128, 128))
    mask = np.zeros((64, 64), bool); mask[:, :32] = True
    out = np.asarray(I.recolour(img, (255, 0, 0), 'region', mask).convert('RGB')).astype(int)
    assert (out[:, 40:] == 128).all() and (out[:, :20, 0] > 150).all()


def test_written_in_the_skin_and_off_writes_nothing(tmp_path):
    d = dict(skingen.DEFAULT_DESIGN, logos=[], number='', team='', name='',
             interior={'cage': '#ff6a00', 'seats': '#9b3dff', 'dash': '#202020'})
    skingen.generate(MX5, d, 'in', out_root=str(tmp_path), log=lambda *a: None)
    files = set(os.listdir(tmp_path / 'in'))
    assert {'INT_RollBar_OCC.dds', 'leather.dds', 'MAT_Dash_Fiber.dds'} <= files
    assert 'PlasticDetail.dds' not in files
    skingen.generate(MX5, dict(d, interior=None), 'off', out_root=str(tmp_path), log=lambda *a: None)
    off = set(os.listdir(tmp_path / 'off'))
    assert not off & {'INT_RollBar_OCC.dds', 'leather.dds', 'MAT_Dash_Fiber.dds'}


def test_app_interior_tab(tmp_path, monkeypatch):
    from test_theme_choice import make_app        # noqa
    import rattys4skin as R
    data = tmp_path / 'data'
    for k, v in dict(DATA_DIR=data, LOGO_DIR=data / 'logos', SETTINGS=data / 'settings.json', LIBRARY=data / 'logos.json').items():
        monkeypatch.setattr(R, k, str(v))
    monkeypatch.setattr(R.App, 'add_starter_logos', lambda self: None)
    a = R.App(); a.withdraw()
    try:
        assert a.design()['interior'] is None                               # off on a fresh start
        assert 'Interior' in a.tabbar.titles
        a.vars['int_cage'].set(True); a.vars['int_cage_col'].set('#00ff00')
        assert a.design()['interior'] == {'cage': '#00ff00'}
    finally:
        R.tk.Tk.destroy(a)
