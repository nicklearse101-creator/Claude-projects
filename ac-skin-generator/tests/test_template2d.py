r"""2D mode for CSP-protected cars (Nik 17 Nov; tested in game on the Ferrari 296 GT3: "looks good").
The car's paint sheet (its maker's template skin) is painted directly: pattern + colours times the sheet's own shading,
carbon / see-through parts and the background untouched, the number etc. on the side panels with a mirror copy on
the other side, the template's working files (PSD, wireframe ...) not copied, its LED number panel shows the number.
Cars that are not protected are not touched by any of this.
python -m pytest -p no:cacheprovider tests/test_template2d.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen
import template2d as T

CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
F296 = os.path.join(CARS, 'cf_ferrari_296_gt3')
TALBOT = os.path.join(CARS, 'talbot_sunbeam_lotus_81_works_backup_v6')
TEX = 'EXT_Skin_Colour.dds'
LOGO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'starter_logos', 'ratty_racing_logo.jpg')


@pytest.fixture(scope='module')
def car():
    return skingen.Car(F296, log=lambda *a: None)


@pytest.fixture(scope='module')
def made(tmp_path_factory):
    out = tmp_path_factory.mktemp('f296')
    info, logs = {}, []
    d = dict(skingen.DEFAULT_DESIGN, pattern='splinter_camo', base='#2a0a4a', accent='#9b3dff', accent2='#ff6a00',
             text='#ffffff', number='101', team="RATTY'S RACING", name='NIK', compress=True,
             logos=[dict(path=LOGO, place='roof', tint=False, bg='auto')])
    skingen.generate(F296, d, 'two d', out_root=str(out), log=logs.append, info=info, views={})
    return out / 'two_d', info, logs


def test_source_is_the_makers_template(car):
    (skin, img), sheet = T.sheet_for(car, TEX)
    assert skin == 'Template' and img.size == (4096, 4096)
    assert len(sheet.islands) > 10
    assert any(fl == 'v' for _, fl in sheet.pairs.values())          # the two sides, one above the other


def test_mirror_maps_back(car):
    _, sheet = T.sheet_for(car, TEX)
    i = next(k for k, (_, fl) in sheet.pairs.items() if fl == 'v')
    I = sheet.islands[i]
    j, u2, v2 = sheet.mirror(i, I['cx'], I['cy'] - 40)
    k, u3, v3 = sheet.mirror(j, u2, v2)
    assert k == i and abs(u3 - I['cx']) < 1 and abs(v3 - (I['cy'] - 40)) < 1


def test_sheet_painted_carbon_and_alpha_kept(made, car):
    out, info, logs = made
    assert info['mode'] == '2d' and info['source_skin'] == 'Template' and info['protected']
    got = np.asarray(skingen.load_image(str(out / TEX)).convert('RGBA')).astype(int)
    tpl = np.asarray(skingen.load_image(os.path.join(F296, 'skins', 'Template', TEX)).convert('RGBA')).astype(int)
    assert np.abs(got[..., 3] - tpl[..., 3]).mean() < 2                       # the template's alpha (carbon parts)
    carbon = tpl[..., 3] < 8
    assert np.abs(got[carbon][:, :3] - tpl[carbon][:, :3]).mean() < 8         # carbon parts untouched
    _, sheet = T.sheet_for(car, TEX)
    assert np.abs(got[sheet.paint][:, :3] - tpl[sheet.paint][:, :3]).mean() > 40   # the panels are painted


def test_number_on_the_sides_with_a_mirror_copy(made):
    _, info, _ = made
    keys = {d['key']: d for d in info['decals2d']}
    assert {'2d:number', '2d:team', '2d:name'} <= set(keys) and any(k.startswith('2d:logo:') for k in keys)
    assert keys['2d:number']['twin'] is not None


def test_skin_files(made):
    out, _, logs = made
    files = set(os.listdir(out))
    assert {TEX, 'ext_config.ini', 'lumirank_font.zip', 'ui_skin.json'} <= files
    assert not any(f.lower().endswith(('.psd', '.xcf')) or 'wireframe' in f.lower() or f == 'EXT_Skin_Colour.png' for f in files)
    ini = open(out / 'ext_config.ini', encoding='utf8').read()
    assert 'ROLE_0_TEXT = 101' in ini and 'CarPaintMaterial' in ini


def test_unprotected_car_untouched():
    info = {}
    skingen.generate(TALBOT, dict(skingen.DEFAULT_DESIGN, logos=[]), 'x', log=lambda *a: None, info=info, write=False)
    assert 'mode' not in info and not info.get('protected')
