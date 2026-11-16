r"""Paint finish (Nik 16 Nov: "Metallic, Gloss and pearlescent would be cool options"). Custom Shaders Patch's own
car-paint templates (extension/config/cars/common/materials_carpaint.ini - 1,250 skins on Nik's PC use them) switched
on from the skin's ext_config.ini for the car's paint materials. Paint on an old plain shader (no maps / detail
texture) gets gloss or matte through its own material values instead.
python -m pytest -p no:cacheprovider tests/test_paint_finish.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
from types import SimpleNamespace as NS
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

TALBOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6'


@pytest.fixture(scope='module')
def talbot():
    return skingen.Car(TALBOT, log=lambda *a: None)


def test_paint_materials(talbot):
    assert skingen.paint_materials(talbot) == ['carPaint', 'carPaint_2']


@pytest.mark.parametrize('finish, template, extra', [
    ('gloss', 'Material_CarPaint_Solid', 'FresnelMax'),
    ('metallic', 'Material_CarPaint_Metallic', 'UseNewFlakes = 1'),
    ('pearl', 'Material_CarPaint_Pearl', 'PearlescentFlakes'),
    ('matte', 'Material_CarPaint_Matte', 'Materials'),
])
def test_finish_uses_csp_template(talbot, finish, template, extra):
    t = skingen.paint_finish_ini(talbot, finish, log=lambda *a: None)
    assert '[INCLUDE: common/materials_carpaint.ini]' in t and f'[{template}]' in t
    assert 'CarPaintMaterial = carPaint, carPaint_2' in t and 'Materials = carPaint, carPaint_2' in t and extra in t
    assert t.index('[INCLUDE') < t.index(f'[{template}]')


def test_standard_writes_nothing(talbot):
    assert skingen.paint_finish_ini(talbot, 'standard') == '' and skingen.paint_finish_ini(talbot, None) == ''


def fake_car(shader):
    mat = NS(name='paint', shader=shader, samplers={'txDiffuse': 'body.dds'}, props={'isAdditive': 2.0, 'fresnelMaxLevel': 0.5})
    return NS(kn5=NS(meshes=[NS(mat=mat, idx=[0, 1, 2], name='body')]), body_textures=['body.dds'], dir=r'D:\nowhere\cars\x')


def test_old_shader_gets_gloss_values():
    logs = []
    t = skingen.paint_finish_ini(fake_car('ksPerPixel'), 'metallic', log=logs.append)
    assert 'INCLUDE' not in t and 'MATERIALS = paint' in t and 'ksSpecularEXP' in t
    assert any('gloss' in m for m in logs)
    m = skingen.paint_finish_ini(fake_car('ksPerPixel'), 'matte', log=logs.append)
    assert 'sunSpecular, 0' in m


def test_written_in_the_skin(tmp_path):
    d = dict(skingen.DEFAULT_DESIGN, paint_finish='metallic', logos=[], number='', team='', name='')
    skingen.generate(TALBOT, d, 'met', out_root=str(tmp_path), log=lambda *a: None)
    ini = open(tmp_path / 'met' / 'ext_config.ini', encoding='utf8').read()
    assert '[Material_CarPaint_Metallic]' in ini and '[INCLUDE: common/materials_carpaint.ini]' in ini
