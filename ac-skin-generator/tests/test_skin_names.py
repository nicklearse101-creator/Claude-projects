r"""A skin's textures must carry exactly the file names the car's model asks for: the game looks them up by name, so
'glass.dds' for a model texture called 'glass.png' is simply ignored (Nik 13 Nov: Talbot window stickers, tint and
headlight lens colour never showed). The file is written in the format its name says.
python -m pytest -p no:cacheprovider tests/test_skin_names.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys, types
import numpy as np
import pytest
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
TALBOT = os.path.join(CARS, 'talbot_sunbeam_lotus_81_works_backup_v6')


def fake_car(tmp_path, skins):
    """A car folder whose stock skins hold the given files."""
    for s, files in skins.items():
        os.makedirs(tmp_path / 'skins' / s)
        for f in files: open(tmp_path / 'skins' / s / f, 'wb').write(b'x')
    return types.SimpleNamespace(skins=list(skins)), str(tmp_path)


@pytest.mark.parametrize('tex, skins, want', [
    ('glass.png', {'a': []}, 'glass.png'),                         # nothing in the stock skins: the model's own name
    ('body.dds', {'a': []}, 'body.dds'),
    ('Body.DDS', {'a': ['body.dds']}, 'body.dds'),                  # the stock skins' spelling wins
    ('glass.png', {'a': ['Glass.PNG']}, 'Glass.PNG'),
    ('lights.jpg', {'a': []}, 'lights.jpg'),
])
def test_skin_file_name(tmp_path, tex, skins, want):
    car, d = fake_car(tmp_path, skins)
    assert skingen.skin_file_name(car, d, tex) == want


@pytest.mark.parametrize('name, magic', [('t.dds', b'DDS '), ('t.png', b'\x89PNG'), ('t.jpg', b'\xff\xd8'), ('t.tga', None)])
def test_written_in_the_named_format(tmp_path, name, magic):
    img = Image.new('RGBA', (64, 32), (10, 200, 30, 128))
    p = str(tmp_path / name)
    skingen.write_texture(img, p)
    data = open(p, 'rb').read()
    if magic: assert data.startswith(magic)
    back = skingen.load_image(data).convert('RGB')
    assert back.size == (64, 32) and np.abs(np.asarray(back, int) - [10, 200, 30]).max() < 12


def test_talbot_skin_uses_the_models_names(tmp_path):
    d = dict(skingen.DEFAULT_DESIGN, win_enable=True, lens_colour='#ffd21f', win_tint='#203040')
    out, *_ = skingen.generate(TALBOT, d, 'names', out_root=str(tmp_path), log=lambda *a: None, write=True)
    files = {f.lower() for f in os.listdir(out)}
    assert 'glass.png' in files and 'glass.dds' not in files
    assert 'feux_sunbeam.png' in files and 'feux_sunbeam.dds' not in files
    assert open(os.path.join(out, 'glass.png'), 'rb').read(4) == b'\x89PNG'
