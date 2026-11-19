r"""Lights stay as they are (Nik 18 Nov, Lacetti: "the skin has been written over the head and tail lights" and "a window
tint ... tinted the headlights too").
 - lamps drawn on the body texture (Lacetti: light_front, rear_light, brake_light, FLASH_LIGHT, the INT_LIGHT housing)
   keep the stock look - no paint, pattern or decal on them;
 - lamp glass that shares the window texture is not tinted (without needing CSP);
 - the paint finish (CSP) is not put on lamp materials.
python -m pytest -p no:cacheprovider tests/test_lamps.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

LAC = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\wtcc_chevrolet_lacetti'
BODY_LAMPS = {'light_front', 'light_front_direction', 'FLASH_LIGHT', 'rear_light', 'brake_light', 'carbody_SUB3'}
GLASS_LAMPS = {'light_glass_front01', 'light_glass_rear01'}


@pytest.fixture(scope='module')
def car():
    return skingen.Car(LAC, log=lambda *a: None)


def cover(meshes, W, H):
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for m in meshes:
        uv = m.uv[m.idx]; uv = uv - np.floor(uv.min(1, keepdims=True))
        for t in (uv * [W, H]).tolist():
            d.polygon([tuple(p) for p in t], fill=255)
    return im


def only(car, tex, names, W, H):
    """Texels only the named meshes use, one texel in from their edge."""
    ms = [m for m in car.kn5.meshes if m.mat is not None and len(m.idx) and m.mat.samplers.get('txDiffuse') == tex]
    a = np.asarray(cover([m for m in ms if m.name in names], W, H).filter(ImageFilter.MinFilter(3))) > 0
    b = np.asarray(cover([m for m in ms if m.name not in names], W, H).filter(ImageFilter.MaxFilter(3))) > 0
    return a & ~b


def rgb_of(path):
    return np.asarray(skingen.load_image(path).convert('RGB')).astype(np.float32)


@pytest.fixture(scope='module')
def made(tmp_path_factory):
    out = tmp_path_factory.mktemp('lamps')
    d = dict(skingen.DEFAULT_DESIGN, base='#00ff00', accent='#400040', pattern='diagonal_split', logos=[], number='',
             team='', name='', compress=False, win_tint='#2617db', win_tint_dark=0.8, paint_finish='pearl')
    skingen.generate(LAC, d, 'lamps', out_root=str(out), log=lambda *a: None)
    return out / 'lamps'


def test_body_lamps_keep_their_stock_look(car, made):
    tex = 'chevrolet_lacetti_body.dds'
    got = rgb_of(str(made / tex)); H, W = got.shape[:2]
    stock = np.asarray(car.stock_texture(tex, car.skins[0]).convert('RGB').resize((W, H), Image.LANCZOS)).astype(np.float32)
    sel = only(car, tex, BODY_LAMPS, W, H)
    assert sel.sum() > 3000
    diff = np.abs(got[sel] - stock[sel]).mean(-1)
    assert diff.mean() < 2 and (diff > 30).mean() < 0.01, (diff.mean(), (diff > 30).mean())


def test_lamp_glass_not_tinted(car, made):
    tex = 'chevrolet_lacetti_windows.dds'
    got = rgb_of(str(made / tex)); H, W = got.shape[:2]
    src = np.asarray(skingen.current_texture(car, tex, {}).convert('RGB').resize((W, H))).astype(np.float32)
    sel = only(car, tex, GLASS_LAMPS, W, H)
    assert sel.sum() > 20000
    assert np.abs(got[sel] - src[sel]).mean() < 2
    win = only(car, tex, {'windows01_SUB1'}, W, H)
    assert np.abs(got[win] - src[win]).mean() > 20                   # the windows themselves are tinted


def test_no_paint_finish_on_lamps(car):
    ini = skingen.paint_finish_ini(car, 'pearl', log=lambda *a: None)
    assert 'chevrolet_lacetti_body' in ini
    for mat in ('INT_LIGHT', 'LIGHT_FRONT', 'LIGHT_DIRECTION'):
        assert mat not in ini
