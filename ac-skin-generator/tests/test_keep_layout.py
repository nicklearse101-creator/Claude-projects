r"""What is already on the car stays where it is (Nik 19 Nov: "It's irritating having set it all up and then everything
moves because i added another logo somewhere - only new logos/names should be moved to fit, not ones already on the
car"). After each preview the engine reports where everything went (info['placed']); the app keeps that as
adjust[key]['at'], and the next preview puts those back there. Only new ones are placed, slid / shrunk to fit round them.
Logos are known by their file, so adding one higher in the list never hands it another's spot.
python -m pytest -p no:cacheprovider tests/test_keep_layout.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import copy, os, sys
import pytest
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
CAR = os.path.join(CARS, 'abarth500')
TALBOT = os.path.join(CARS, 'talbot_sunbeam_lotus_81_works_backup_v6')
F296 = os.path.join(CARS, 'cf_ferrari_296_gt3')
RAT = os.path.join(HERE, 'starter_logos', 'ratty_racing_logo.jpg')


@pytest.fixture(scope='module')
def logos(tmp_path_factory):
    d = tmp_path_factory.mktemp('logos')
    out = {}
    for name, col, size in (('blue', (30, 60, 220, 255), (300, 120)), ('green', (30, 200, 60, 255), (200, 200))):
        im = Image.new('RGBA', size, (0, 0, 0, 0))              # a logo on a see-through background
        ImageDraw.Draw(im).rectangle([4, 4, size[0] - 5, size[1] - 5], fill=col)
        p = str(d / f'{name}.png'); im.save(p); out[name] = p
    out['rat'] = RAT
    return out


def lg(path, place):
    return dict(path=path, place=place, tint=False, bg='auto')


def run(car, out, logos=(), adjust=None, **design):
    d = dict(skingen.DEFAULT_DESIGN, number='', team='', name='', adjust=copy.deepcopy(adjust or {}), logos=list(logos))
    d.update(design)
    info, log = {}, []
    skingen.generate(car, d, 'keep', out_root=str(out), log=log.append, info=info, views=None, write=False)
    return info, log


def boxes(info, key):
    return {d['view']: d for d in info.get('decals', []) if d['key'] == key}


def kept(adjust, info):
    """What the app does after a preview: the spots it reports kept in the adjustments."""
    return skingen.merge_placed(copy.deepcopy(adjust or {}), info['placed'])


def same(b1, b2, tol=0.002):
    assert set(b1) == set(b2) and b1
    for v in b1:
        for k in ('a', 'b', 'h'):
            assert abs(b1[v][k] - b2[v][k]) < tol, (v, k, b1[v][k], b2[v][k])


def overlap(d1, d2):
    """How much of the smaller box the other covers (0..1), same view."""
    if d1['view'] != d2['view']: return 0.0
    ia = max(0.0, min(d1['a'] + d1['w'] / 2, d2['a'] + d2['w'] / 2) - max(d1['a'] - d1['w'] / 2, d2['a'] - d2['w'] / 2))
    ib = max(0.0, min(d1['b'] + d1['h'] / 2, d2['b'] + d2['h'] / 2) - max(d1['b'] - d1['h'] / 2, d2['b'] - d2['h'] / 2))
    return ia * ib / min(d1['w'] * d1['h'], d2['w'] * d2['h'])


def key(place, path):
    return f'logo:{place}:{os.path.basename(path)}'


def test_logo_keys_go_by_file(tmp_path, logos):
    info, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')])
    assert set(boxes(info, key('doors', logos['blue']))) == {'left', 'right'}


def test_logo_stays_when_another_is_added_to_its_panel(tmp_path, logos):
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')])
    a1 = kept({}, i1)
    i2, log = run(CAR, tmp_path, [lg(logos['blue'], 'doors'), lg(logos['green'], 'doors')], a1)
    same(boxes(i1, key('doors', logos['blue'])), boxes(i2, key('doors', logos['blue'])))
    new = boxes(i2, key('doors', logos['green']))
    assert set(new) == {'left', 'right'}
    old = boxes(i2, key('doors', logos['blue']))
    # the blue logo fills most of the door: the new one goes round it (smaller), or the user is told to move it
    assert all(overlap(new[v], old[v]) < 0.02 for v in new) or any('covers' in l for l in log)


def test_new_logo_goes_round_the_old_one(tmp_path, logos):
    small = {key('bonnet', logos['green']): {'scale': 0.5}}      # made smaller on the preview: room left beside it
    i1, _ = run(CAR, tmp_path, [lg(logos['green'], 'bonnet')], small)
    i2, log = run(CAR, tmp_path, [lg(logos['green'], 'bonnet'), lg(logos['blue'], 'bonnet')], kept(small, i1))
    same(boxes(i1, key('bonnet', logos['green'])), boxes(i2, key('bonnet', logos['green'])))
    old, new = boxes(i2, key('bonnet', logos['green']))['top'], boxes(i2, key('bonnet', logos['blue']))['top']
    assert overlap(new, old) < 0.02
    assert any('placed round' in l for l in log)


def test_new_one_goes_the_same_way_on_both_sides(tmp_path, logos):
    i1, _ = run(CAR, tmp_path, [lg(logos['green'], 'rear_quarters')])
    i2, _ = run(CAR, tmp_path, [lg(logos['green'], 'rear_quarters'), lg(logos['blue'], 'rear_quarters')], kept({}, i1))
    new = boxes(i2, key('rear_quarters', logos['blue']))
    assert abs(new['left']['a'] + new['right']['a']) < 0.01 and abs(new['left']['b'] - new['right']['b']) < 0.01
    old = boxes(i2, key('rear_quarters', logos['green']))
    for v in new: assert overlap(new[v], old[v]) < 0.02, v


def test_new_logo_higher_in_the_list_does_not_take_the_old_spot(tmp_path, logos):
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')])
    i2, _ = run(CAR, tmp_path, [lg(logos['green'], 'doors'), lg(logos['blue'], 'doors')], kept({}, i1))
    same(boxes(i1, key('doors', logos['blue'])), boxes(i2, key('doors', logos['blue'])))


def test_hand_moves_stay_on_top_of_the_kept_spot(tmp_path, logos):
    k = key('doors', logos['blue'])
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')], {k: {'da': 0.1, 'db': 0.02}})
    a1 = kept({k: {'da': 0.1, 'db': 0.02}}, i1)
    i2, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors'), lg(logos['green'], 'doors')], a1)
    same(boxes(i1, k), boxes(i2, k))


def test_spot_kept_is_before_the_hand_moves(tmp_path, logos):
    k = key('doors', logos['blue'])
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')], {k: {'da': 0.1, 'db': -0.02, 'scale': 1.2}})
    for v, box in boxes(i1, k).items():
        sgn = -1 if v == 'right' else 1
        a, b, h = i1['placed'][k][v]
        assert abs(a - (box['a'] - sgn * 0.1)) < 1e-3 and abs(b - (box['b'] + 0.02)) < 1e-3 and abs(h - box['h'] / 1.2) < 1e-3


def test_names_stay_when_a_logo_is_added_to_their_place(tmp_path, logos):
    d = dict(team="RATTY'S RACING", name='NIK', team_places=['front_wings'], name_places=['front_wings'])
    i1, _ = run(CAR, tmp_path, [], **d)
    i2, log = run(CAR, tmp_path, [lg(logos['rat'], 'front_wings')], kept({}, i1), **d)
    same(boxes(i1, 'team name:front_wings'), boxes(i2, 'team name:front_wings'))
    same(boxes(i1, 'driver name:front_wings'), boxes(i2, 'driver name:front_wings'))
    new = boxes(i2, key('front_wings', logos['rat']))
    assert new
    names = [d_ for d_ in i2['decals'] if d_['key'].endswith('name:front_wings')]
    clear = all(overlap(new[v], n) < 0.02 for v in new for n in names if n['view'] == v)
    assert clear or any('covers' in l for l in log)       # fitted round them, or told to move it


def test_roof_number_stays_when_a_roof_logo_is_added(tmp_path, logos):
    i1, _ = run(TALBOT, tmp_path, [], number='7')
    i2, _ = run(TALBOT, tmp_path, [lg(logos['rat'], 'roof')], kept({}, i1), number='7')
    same(boxes(i1, 'number:roof'), boxes(i2, 'number:roof'))
    same(boxes(i1, 'number:doors'), boxes(i2, 'number:doors'))


def test_first_preview_is_as_before(tmp_path, logos):
    """Nothing kept yet: the same layout as 1.14 (two logos side by side on the door)."""
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors'), lg(logos['green'], 'doors')])
    b, g = boxes(i1, key('doors', logos['blue'])), boxes(i1, key('doors', logos['green']))
    base = lambda d: d['b'] - d['slid'][1]                 # (before the placement check slid it onto the panel)
    assert abs(base(b['left']) - base(g['left'])) < 0.01 and b['left']['a'] != g['left']['a']


def test_old_keys_are_upgraded(logos):
    lgs = [lg(logos['blue'], 'doors'), lg(logos['green'], 'doors'), lg(logos['rat'], 'bonnet')]
    adj = {'logo:doors': {'da': 0.1}, 'logo:doors:2': {'deleted': True}, 'logo:bonnet': {'scale': 1.5}, 'number:doors': {'db': 0.1}}
    up = skingen.upgrade_logo_keys(adj, lgs)
    assert up == {key('doors', logos['blue']): {'da': 0.1}, key('doors', logos['green']): {'deleted': True},
                  key('bonnet', logos['rat']): {'scale': 1.5}, 'number:doors': {'db': 0.1}}


def test_engine_still_reads_old_keys(tmp_path, logos):
    i0, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')])
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')], {'logo:doors': {'db': 0.05}})
    k = key('doors', logos['blue'])
    b0 = boxes(i0, k)['left']                              # (moved by hand: never slid by the placement check)
    assert abs(boxes(i1, k)['left']['b'] - (b0['b'] - b0['slid'][1]) - 0.05) < 0.005


def test_reset_one_places_it_afresh(tmp_path, logos):
    """'Reset' takes its kept spot away: it is placed again, round the others."""
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors'), lg(logos['green'], 'doors')])
    a1 = kept({}, i1)
    a1.pop(key('doors', logos['green']))
    i2, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors'), lg(logos['green'], 'doors')], a1)
    same(boxes(i1, key('doors', logos['blue'])), boxes(i2, key('doors', logos['blue'])))
    assert boxes(i2, key('doors', logos['green']))


def test_merge_keeps_what_is_there():
    adj = {'k': {'da': 0.1, 'at': {'left': [1, 2, 3]}}}
    out = skingen.merge_placed(adj, {'k': {'left': [9, 9, 9], 'right': [-1, 2, 3]}, 'n': {'top': [0, 0, 1]}})
    assert out['k'] == {'da': 0.1, 'at': {'left': [1, 2, 3], 'right': [-1, 2, 3]}} and out['n'] == {'at': {'top': [0, 0, 1]}}


def test_create_after_preview_reuses_the_painting(tmp_path, logos, monkeypatch):
    """The kept spots added after a preview do not make Create paint the whole car again."""
    i1, _ = run(CAR, tmp_path, [lg(logos['blue'], 'doors')])
    calls = []
    real = skingen._paint_texture
    monkeypatch.setattr(skingen, '_paint_texture', lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    run(CAR, tmp_path, [lg(logos['blue'], 'doors')], kept({}, i1))
    assert not calls


def test_2d_logo_stays_when_another_is_added(tmp_path, logos):
    i1, _ = run(F296, tmp_path, [lg(logos['blue'], 'roof')])
    b1 = {d['key']: d for d in i1['decals2d']}
    i2, _ = run(F296, tmp_path, [lg(logos['blue'], 'roof'), lg(logos['green'], 'roof')], kept({}, i1))
    b2 = {d['key']: d for d in i2['decals2d']}
    kb, kg = '2d:logo:blue.png', '2d:logo:green.png'
    for k_ in ('u', 'v', 'h'): assert abs(b1[kb][k_] - b2[kb][k_]) < 1.5, k_
    bx = lambda d: (d['u'] - d['w'] / 2, d['v'] - d['h'] / 2, d['u'] + d['w'] / 2, d['v'] + d['h'] / 2)
    x0, y0, x1, y1 = bx(b2[kb]); X0, Y0, X1, Y1 = bx(b2[kg])
    assert max(0, min(x1, X1) - max(x0, X0)) * max(0, min(y1, Y1) - max(y0, Y0)) < 0.02 * b2[kg]['w'] * b2[kg]['h']
