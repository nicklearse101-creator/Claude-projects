r"""Triangles stretched over more than one whole texture width (tiled underbodies, broken triangles) can't hold a
picture: they must not make a car 'plain colour only' (overlap) nor be drawn over the panels (texel map).
python -m pytest -p no:cacheprovider tests/test_tiled_uv.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen
from test_protected import grid, mesh

CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'


def giant():
    """One triangle whose texture corners are hundreds of texture widths apart."""
    return mesh([[0, 0, 0.5], [0.4, 0, 0.5], [0, 0.4, 0.5]], [[-300.0, -5.0], [900.0, -130.0], [12.0, 60.0]], [0, 1, 2])


def test_overlap_ignores_stretched_triangles():
    clean = skingen.uv_overlap([grid(n=30)])                          # under 2000 triangles (uv_overlap's cap)
    assert clean < 1.5 and skingen.uv_overlap([grid(n=30), giant()]) == pytest.approx(clean, rel=0.05)


def test_texel_map_ignores_stretched_triangles():
    g = grid(); g.nrm = np.tile([0, 0, 1.0], (len(g.pos), 1)); g.name = 'panel'
    t = giant(); t.nrm = np.tile([0, 0, 1.0], (3, 1)); t.name = 'giant'
    a = skingen.TexelMap([g], 128, 128, lambda *x: None, skip_stretched=True)
    b = skingen.TexelMap([g, t], 128, 128, lambda *x: None, skip_stretched=True)     # (body paint only)
    assert np.array_equal(a.covered, b.covered)
    assert np.allclose(a.P, b.P)                                   # every texel still belongs to the panel


@pytest.mark.parametrize('car', ['wtcc_alfa_romeo_156_gta', 'mclaren_mp412c_gt3'])
def test_cars_get_a_livery(car, tmp_path):
    logo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'starter_logos', 'ratty_racing_logo.jpg')
    d = dict(skingen.DEFAULT_DESIGN, logos=[dict(path=logo, place='doors', tint=False, bg='auto')])
    info, log = {}, []
    skingen.generate(os.path.join(CARS, car), d, 't', out_root=str(tmp_path), log=log.append, info=info, write=False)
    assert not any('only a plain colour' in l for l in log)
    assert {x['view'] for x in info['decals'] if x['key'] == 'logo:doors'} == {'left', 'right'}


def test_overlap_counts_every_triangle():
    """A detailed panel (7200 triangles) mapped once onto the texture reads about 1, not more (no cap)."""
    assert skingen.uv_overlap([grid(n=60)]) < 1.3


def test_volvo_s40_gets_a_livery(tmp_path):
    info, log = {}, []
    skingen.generate(os.path.join(CARS, 'pm3dm_volvo_s40_btcc'), dict(skingen.DEFAULT_DESIGN), 't', out_root=str(tmp_path),
                     log=log.append, info=info, write=False)
    assert not any('only a plain colour' in l for l in log)
    assert info['missing'] == []          # an exhaust tip spread over the livery used to take the panels' texels


def test_big_parts_never_left_out_of_the_count():
    """Only small odd parts are left out: when the 'odd' triangles are a big share of the surface (an atlas car, like the
    Cadillac) the count is as before, so such a car stays 'plain colour' instead of a grey body with painted trim."""
    g = grid(n=30)
    stretched = grid(n=30, size=1.0); stretched.uv = stretched.uv * 0.05            # a whole panel squeezed into a corner
    stretched.pos = stretched.pos * 1.0 + [0, 0, 1.0]
    tiny = grid(n=5, size=0.02); tiny.pos = tiny.pos + [0, 0, 2.0]                  # an exhaust tip over the whole texture
    assert skingen.uv_overlap([g, tiny]) == pytest.approx(skingen.uv_overlap([g]), rel=0.05)
    assert skingen.uv_overlap([g, stretched], skip_hogs=True) == pytest.approx(skingen.uv_overlap([g, stretched], skip_hogs=False))


def test_cadillac_stays_plain(tmp_path):
    log = []
    skingen.generate(os.path.join(CARS, 'bcrc_caddi_gt3'), dict(skingen.DEFAULT_DESIGN), 't', out_root=str(tmp_path),
                     log=log.append, info={}, write=False)
    assert any('only a plain colour' in l for l in log)


def test_main_texture_protected_means_whole_car(tmp_path):
    info, log = {}, []
    skingen.generate(os.path.join(CARS, 'supercars_gen3_camaro_ak'), dict(skingen.DEFAULT_DESIGN), 't', out_root=str(tmp_path),
                     log=log.append, info=info, write=False)
    assert info.get('protected') and not info.get('decals')
