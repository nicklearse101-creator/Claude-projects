"""Nik 23 Nov, Escort Mk2: in sunlight the red parts of his livery showed white. The car's paint material uses its body
picture as its shine map too (txMaps = AO_BODY.dds, like txDiffuse; red = full specular, no gloss -> a white glare).
The skin now keeps the shine map as the car's maker made it: the car's own picture, given to those materials through
CSP (ext_config.ini), so the livery's colours no longer change how the paint shines.
python -m pytest -p no:cacheprovider tests/test_shine_map.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen as S
from kn5 import Mesh


class Mat:
    def __init__(self, name, diff, maps=None):
        self.name, self.shader, self.props = name, 'ksPerPixelMultiMap', {}
        self.samplers = {'txDiffuse': diff, **({'txMaps': maps} if maps else {})}


class FakeCar:
    def __init__(self, mats):
        T = np.zeros((3, 3))
        self.kn5 = type('K', (), {})()
        self.kn5.meshes = [Mesh(name=f'm{k}', pos=T, nrm=T, uv=np.zeros((3, 2)), idx=np.arange(3).reshape(1, 3), mat=m,
                                parents=()) for k, m in enumerate(mats)]
        self.kn5.textures = {}


def test_materials_whose_shine_map_is_the_painted_picture():
    car = FakeCar([Mat('Material #25DQW', 'AO_BODY.dds', 'AO_BODY.dds'), Mat('paint2', 'AO_BODY.dds', 'ao_body.DDS'),
                   Mat('own_maps', 'AO_BODY.dds', 'BODY_MAPS.dds'), Mat('no_maps', 'AO_BODY.dds'),
                   Mat('other', 'GLASS.dds', 'GLASS.dds')])
    got = S.shine_maps_painted(car, {'AO_BODY.dds': object()})
    assert got == {'AO_BODY.dds': ['Material #25DQW', 'paint2']}
    assert S.shine_maps_painted(car, {'BODY_MAPS.dds': object()}) == {}       # only its own picture counts


def test_written_shine_map_and_ini(tmp_path):
    car = FakeCar([Mat('Material #25DQW', 'AO_BODY.dds', 'AO_BODY.dds')])
    grey = Image.new('RGBA', (64, 64), (89, 89, 89, 255))
    said = []
    ini = S.write_shine_maps(car, {'AO_BODY.dds': ['Material #25DQW']}, str(tmp_path), lambda t: grey, said.append)
    f = tmp_path / 'r4s_ao_body_shine.dds'
    assert f.is_file()
    back = np.asarray(S.load_image(str(f)).convert('RGB'))
    assert np.abs(back.astype(int) - 89).max() <= 2
    assert 'MATERIALS = Material #25DQW' in ini and 'RESOURCE_0 = txMaps' in ini and 'RESOURCE_FILE_0 = r4s_ao_body_shine.dds' in ini
    assert ini.startswith('[SHADER_REPLACEMENT_...]') and said
