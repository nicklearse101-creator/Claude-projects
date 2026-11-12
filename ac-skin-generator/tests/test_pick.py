"""'Pick it on the car' (Nik, 12 Nov): a logo / name / number the app cannot place is reported (info['missing']) instead
of quietly left off, and a spot picked on the preview (adjust[key]['pin'] = {view: [a, b]}) puts it there.
python -m pytest -p no:cacheprovider tests/test_pick.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\abarth500'
LOGO = os.path.join(HERE, 'starter_logos', 'ratty_racing_logo.jpg')


def run(place, adjust=None, no_bonnet=False, monkeypatch=None, out=None):
    real = skingen.top_panels
    if no_bonnet:                                   # a car where the app finds no bonnet panel
        def fake(*a, **k):
            p = real(*a, **k); p.pop('bonnet', None); return p
        monkeypatch.setattr(skingen, 'top_panels', fake)
    d = dict(skingen.DEFAULT_DESIGN, number='', team='', name='', adjust=adjust or {},
             logos=[dict(path=LOGO, place=place, tint=False, bg='auto')])
    info, log = {}, []
    skingen.generate(CAR, d, 'pick', out_root=str(out), log=log.append, info=info, views=None, write=False)
    monkeypatch.setattr(skingen, 'top_panels', real)
    return info, log


@pytest.fixture(scope='module')
def car():
    return skingen.Car(CAR, log=lambda *a: None)


def boxes(info, key):
    return {d['view']: d for d in info.get('decals', []) if d['key'] == key}


def test_placed_logo_not_missing(monkeypatch, tmp_path):
    info, _ = run('doors', monkeypatch=monkeypatch, out=tmp_path)
    assert info['missing'] == [] and set(boxes(info, 'logo:doors')) == {'left', 'right'}


def test_no_place_found_is_reported(monkeypatch, tmp_path):
    info, log = run('bonnet', no_bonnet=True, monkeypatch=monkeypatch, out=tmp_path)
    assert [m['key'] for m in info['missing']] == ['logo:bonnet']
    assert 'bonnet' in info['missing'][0]['label'] and not boxes(info, 'logo:bonnet')
    assert any('pick it on the car' in l.lower() for l in log)


def test_picked_spot_used_when_no_place_found(monkeypatch, tmp_path, car):
    b = -(car.hi[2] - 0.45)                        # top view: b = -z; a spot on the bonnet, near the front
    info, _ = run('bonnet', adjust={'logo:bonnet': {'pin': {'top': [0.0, b]}}}, no_bonnet=True,
                  monkeypatch=monkeypatch, out=tmp_path)
    assert info['missing'] == []
    box = boxes(info, 'logo:bonnet')['top']
    assert abs(box['a']) < 0.01 and abs(box['b'] - b) < 0.01


def test_picked_side_spot_goes_on_both_sides(monkeypatch, tmp_path, car):
    a, b = 0.3, 0.6
    info, _ = run('doors', adjust={'logo:doors': {'pin': {'left': [a, b]}}}, monkeypatch=monkeypatch, out=tmp_path)
    bx = boxes(info, 'logo:doors')
    assert info['missing'] == []
    assert (round(bx['left']['a'], 3), round(bx['left']['b'], 3)) == (a, b)
    assert (round(bx['right']['a'], 3), round(bx['right']['b'], 3)) == (-a, b)       # the same spot on the other side


def test_logo_landing_nowhere_is_reported(monkeypatch, tmp_path):
    info, _ = run('doors', adjust={'logo:doors': {'db': 5.0}}, monkeypatch=monkeypatch, out=tmp_path)   # moved off the car
    assert [m['key'] for m in info['missing']] == ['logo:doors']
    assert not boxes(info, 'logo:doors')
