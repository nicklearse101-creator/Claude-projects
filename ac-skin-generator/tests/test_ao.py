"""1.17 (Nik 22 Nov: "make AO map ... and have a white base"): the paint's light and shade baked from the car's own shape
(ao_bake, the way Content Manager's "Baked shadows" does it), never read from the old skins' pictures.
python -m pytest -p no:cacheprovider tests/test_ao.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ao_bake, skingen as S
from kn5 import Mesh

SMALL_CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\abarth500'


def test_suns_spread_over_the_sky():
    d = ao_bake.sky_dirs(200)
    assert d.shape == (200, 3) and np.allclose(np.linalg.norm(d, axis=1), 1)
    el = np.degrees(np.arcsin(d[:, 1]))
    assert el.min() >= 0 and el.max() <= 60
    assert abs(d[:, 0].mean()) < 0.05 and abs(d[:, 2].mean()) < 0.05          # all round, not from one side


def quad(x0, x1, y, z0, z1, down=False):
    T = np.array([[[x0, y, z0], [x1, y, z0], [x1, y, z1]], [[x0, y, z0], [x1, y, z1], [x0, y, z1]]], float)
    return T[:, ::-1] if down else T


def box(x0, x1, y0, y1, z0, z1):
    out = [quad(x0, x1, y1, z0, z1), quad(x0, x1, y0, z0, z1, True)]
    for x in (x0, x1):
        out.append(np.array([[[x, y0, z0], [x, y1, z0], [x, y1, z1]], [[x, y0, z0], [x, y1, z1], [x, y0, z1]]], float))
    for z in (z0, z1):
        out.append(np.array([[[x0, y0, z], [x1, y0, z], [x1, y1, z]], [[x0, y0, z], [x1, y1, z], [x0, y1, z]]], float))
    return np.concatenate(out)


def test_open_panel_light_under_a_roof_dark():
    floor = quad(-2, 2, 0, -2, 2)                                          # a 4 m floor, a roof 0.3 m over its middle
    roof = box(-0.6, 0.6, 0.3, 0.35, -0.6, 0.6)
    occ = np.concatenate([floor, roof])
    P = np.array([[1.7, 0.0, 1.7], [0.0, 0.0, 0.0], [0.0, 0.35, 0.0]])      # open floor, under the roof, on the roof
    N = np.array([[0, 1, 0], [0, 1, 0], [0, 1, 0]], float)
    ao = ao_bake.bake(occ, P, N)
    assert ao[0] > 0.9 and ao[2] > 0.9
    assert ao[1] < 0.5 * ao[0]


def test_open_side_as_light_as_open_top():
    """Occlusion only: a door facing the side is not darker than the roof (the game lights the car itself)."""
    floor = quad(-2, 2, 0, -2, 2)
    post = box(-1.9, -1.6, 0.0, 1.0, -0.15, 0.15)                          # a post standing on the floor
    occ = np.concatenate([floor, post])
    P = np.array([[-1.6, 0.8, 0.0], [-1.75, 1.0, 0.0]]); N = np.array([[1, 0, 0], [0, 1, 0]], float)
    side, top = ao_bake.bake(occ, P, N)
    assert side > 0.9 and top > 0.9 and abs(side - top) < 0.08


def test_stop_asked():
    occ = quad(-1, 1, 0, -1, 1)
    assert ao_bake.bake(occ, np.zeros((1, 3)), np.array([[0, 1, 0.0]]), stop=lambda: True) is None


class Mat:
    def __init__(self, name='paint', blend=0, alpha_tested=False, shader='ksPerPixel'):
        self.name, self.blend, self.alpha_tested, self.shader, self.samplers = name, blend, alpha_tested, shader, {}


def test_what_casts_shadows():
    T = quad(0, 1, 0, 0, 1)
    mk = lambda name, **k: Mesh(name=name, pos=T.reshape(-1, 3), nrm=np.tile([0, 1, 0.0], (6, 1)), uv=np.zeros((6, 2)),
                                idx=np.arange(6).reshape(2, 3), mat=k.pop('mat', Mat()), parents=(), **k)
    meshes = [mk('body', cast=True, shown=True), mk('glass', mat=Mat(blend=1), cast=True, shown=True),
              mk('no_shadow', cast=False, shown=True), mk('GEO_Rim_Blur', cast=True, shown=True),
              mk('body_shadow', cast=True, shown=True), mk('damage_glass', cast=True, shown=True),
              mk('hidden', cast=True, shown=False), mk('old_reader', mat=Mat())]          # (no flags: casts)
    occ = ao_bake.occluders(meshes, S.see_through)
    assert len(occ) == 2 * 2                                               # body and old_reader only


@pytest.fixture(scope='module')
def car():
    return S.Car(SMALL_CAR, log=lambda *a: None)


def test_shade_from_the_shape_kept_per_car(car, tmp_path, monkeypatch):
    tex = car.body_textures[0]
    monkeypatch.setattr(S, 'AO_CACHE_DIR', str(tmp_path / 'ao'))
    said = []
    a = S.ao_shade(car, tex, 512, 512, said.append)
    assert a.shape == (512, 512) and a.dtype == np.float32
    assert a.min() >= S.AO_FLOOR - 1e-6 and a.max() <= 1 + 1e-6
    assert said and os.listdir(tmp_path / 'ao')
    baked = []
    monkeypatch.setattr(ao_bake, 'bake', lambda *x, **k: baked.append(1))
    said2 = []
    b = S.ao_shade(car, tex, 512, 512, said2.append)                       # from the kept file: not baked again
    assert not baked and not said2 and np.allclose(a, b, atol=2e-3)


def test_border_texels_baked_full_size(car, monkeypatch):
    """Scaled up from the small bake, a texel beside another part would mix the two: those are baked at full size."""
    monkeypatch.setattr(S, 'AO_CACHE_DIR', None)
    tex = car.body_textures[0]
    tm = S.TexelMap(car.meshes_for(tex), 2048, 2048, lambda *a: None, skip_stretched=True)
    sizes, real = [], ao_bake.bake
    monkeypatch.setattr(ao_bake, 'bake', lambda o, P, N, **k: (sizes.append(len(P)), real(o, P, N, **k))[1])
    a = S.ao_shade(car, tex, 2048, 2048, lambda m: None, tm_full=tm)
    assert len(sizes) == 2 and 0 < sizes[1] < 0.5 * len(tm.yy)          # some texels, not most
    b = S.ao_shade(car, tex, 2048, 2048, lambda m: None)                   # without: scaled up only
    assert a.shape == b.shape and not np.array_equal(a, b)


def test_no_cache_folder_nothing_written(car, tmp_path, monkeypatch):
    monkeypatch.setattr(S, 'AO_CACHE_DIR', None)
    monkeypatch.chdir(tmp_path)
    S.ao_shade(car, car.body_textures[0], 256, 256, lambda m: None)
    assert not os.listdir(tmp_path)


def test_paint_shaded_from_the_shape(car, monkeypatch):
    monkeypatch.setattr(S, 'AO_CACHE_DIR', None)
    tex = car.body_textures[0]
    mem = {}
    S._map_texture(car, tex, 512, 512, mem, lambda m: None)
    shade = mem['stock'][3]
    assert np.allclose(shade, S.ao_shade(car, tex, 512, 512, lambda m: None, tm_full=mem['tm']))
    monkeypatch.setattr(S, 'AO_SHADING', False)                            # the old way still there
    old = {}
    S._map_texture(car, tex, 512, 512, old, lambda m: None)
    assert np.array_equal(old['stock'][3], S.stock_analysis(car, tex, 512, 512, old['tm'], lambda m: None)[3])
