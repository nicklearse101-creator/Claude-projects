"""Speed work (v1.9.0): every faster version must give exactly the same result as before.
python -m pytest -p no:cacheprovider tests/test_speed.py -q --basetemp=D:\\ClaudeData\\tmp\\pytest"""
import hashlib, os, shutil, sys, time
import numpy as np
import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMALL_CAR = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\abarth500'


# ---------------------------------------------------------------- spreading colour into the texture gaps
def old_pad_texture(img, covered, reach=12):
    """v1.8.0 pad_texture, kept here as the reference."""
    img = img.copy()
    have = Image.fromarray((covered * 255).astype(np.uint8))
    for _ in range(reach):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            new = ImageChops.subtract(ImageChops.offset(have, dx, dy), have)
            img.paste(ImageChops.offset(img, dx, dy), (0, 0), new)
            have = ImageChops.lighter(have, new)
    return img


def panels(H, W, seed, n=60):
    """A texture-like coverage mask: panels with gaps between them, some touching the edges (the old code wraps)."""
    rng = np.random.default_rng(seed)
    m = np.zeros((H, W), bool)
    for _ in range(n):
        y, x = rng.integers(0, H), rng.integers(0, W)
        h, w = rng.integers(2, max(3, H // 4)), rng.integers(2, max(3, W // 4))
        m[y:y + h, x:x + w] = True
    m[rng.integers(0, H, 40), :] ^= True                      # thin seams
    return m


def test_pad_texture_same_as_before():
    rng = np.random.default_rng(7)
    for H, W in ((97, 131), (256, 200), (64, 64)):
        img = Image.fromarray((rng.random((H, W, 3)) * 255).astype(np.uint8))
        masks = [panels(H, W, s) for s in range(4)] + [np.zeros((H, W), bool), np.ones((H, W), bool),
                                                        rng.random((H, W)) > 0.97]
        for m in masks:
            assert skingen.pad_texture(img, m).tobytes() == old_pad_texture(img, m).tobytes()


def test_pad_texture_fast():
    m = panels(4096, 4096, 3, n=900)
    img = Image.new('RGB', (4096, 4096), (200, 30, 30))
    t = time.time()
    skingen.pad_texture(img, m)
    assert time.time() - t < 4.0                               # was 15 s


# ---------------------------------------------------------------- logos
def old_inside(solid):
    """v1.8.0: the solid part of a logo plus everything it encloses (PIL flood fill from the border)."""
    s = Image.fromarray((solid * 255).astype(np.uint8))
    pad = Image.new('L', (s.width + 2, s.height + 2), 0); pad.paste(s, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)
    return np.asarray(pad)[1:-1, 1:-1] != 128


def test_enclosed_same_as_flood_fill():
    rng = np.random.default_rng(3)
    shapes = [rng.random((80, 120)) > p for p in (0.3, 0.5, 0.6, 0.7)]
    ring = np.zeros((60, 60), bool); ring[10:50, 10:50] = True; ring[15:45, 15:45] = False; ring[25:35, 25:35] = True
    spiral = np.zeros((41, 41), bool)
    for k in range(0, 20, 4):
        spiral[k, k:41 - k] = spiral[40 - k, k:41 - k] = spiral[k:41 - k, k] = spiral[k + 2:41 - k, 40 - k] = True
    shapes += [ring, spiral, np.zeros((5, 7), bool), np.ones((5, 7), bool), panels(150, 90, 1)]
    for s in shapes:
        assert np.array_equal(skingen.enclosed(s), old_inside(s))


def logo_file(path, colour=(220, 20, 20)):
    im = Image.new('RGB', (300, 200), 'white')
    d = ImageDraw.Draw(im); d.ellipse([40, 30, 260, 170], outline=colour, width=18); d.text((120, 90), 'R4S', fill=colour)
    im.save(path)


def test_prep_logo_kept(tmp_path, monkeypatch):
    p = str(tmp_path / 'logo.png'); logo_file(p)
    a = skingen.prep_logo(p)
    opened = []
    real = skingen.Image.open
    monkeypatch.setattr(skingen.Image, 'open', lambda *a_, **k: (opened.append(a_[0]), real(*a_, **k))[1])
    b = skingen.prep_logo(p)
    assert opened == [] and b.tobytes() == a.tobytes() and b.size == a.size        # second time: kept, not redone
    b.putpixel((0, 0), (1, 2, 3, 4))
    assert skingen.prep_logo(p).tobytes() == a.tobytes()                           # callers get their own copy
    skingen.prep_logo(p, tint=(0, 90, 255))
    assert opened == [p]                                                           # another tint is worked out


def test_prep_logo_redone_when_file_changes(tmp_path):
    p = str(tmp_path / 'logo.png'); logo_file(p)
    a = skingen.prep_logo(p)
    logo_file(p, colour=(20, 20, 220)); st = os.stat(p); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 10 ** 9))
    assert skingen.prep_logo(p).tobytes() != a.tobytes()


def test_prep_logo_picture_flag_kept(tmp_path):
    p = str(tmp_path / 'photo.png')
    Image.fromarray((np.random.default_rng(1).random((90, 120, 3)) * 255).astype(np.uint8)).save(p)
    assert skingen.prep_logo(p).info.get('picture') and skingen.prep_logo(p).info.get('picture')


# ---------------------------------------------------------------- the pattern on several cores
@pytest.fixture(scope='module')
def small_car():
    return skingen.Car(SMALL_CAR, log=lambda *a: None)


def test_pattern_threads_same(small_car):
    tex = small_car.body_textures[0]
    tm = skingen.TexelMap(small_car.meshes_for(tex), 1024, 1024, lambda *a: None)
    d = dict(skingen.DEFAULT_DESIGN, pattern='sweep', carbon=True)
    one = skingen.aa_pattern(d, tm, small_car, 0.3, 0.8, workers=1, chunk=1 << 16)
    many = skingen.aa_pattern(d, tm, small_car, 0.3, 0.8, workers=4, chunk=1 << 16)
    assert np.array_equal(one, many)


# ---------------------------------------------------------------- Preview, then Create
def design():
    return dict(skingen.DEFAULT_DESIGN, number='7', name='NIK', team='RATTY',
                logos=[dict(path=os.path.join(HERE, 'starter_logos', 'ratty_racing_logo.jpg'), place='doors', tint=False, bg='auto')])


def sums(out):
    r = {}
    for root, _, files in os.walk(out):
        for f in files:
            r[f] = hashlib.sha256(open(os.path.join(root, f), 'rb').read()).hexdigest()
    return r


@pytest.fixture(scope='module')
def runs(tmp_path_factory):
    """A fresh Create; a Create straight after a Preview of the same design; the same with the kept painting thrown away
    in between (as v1.8.0 did): what was redone, what came out, what the Create said."""
    root = tmp_path_factory.mktemp('gen')
    calls = dict(render=0, sheet=0)
    real_render, real_sheet = skingen.render_design, skingen.preview_sheet

    def render(*a, **k): calls['render'] += 1; return real_render(*a, **k)

    def sheet(*a, **k): calls['sheet'] += 1; return real_sheet(*a, **k)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(skingen, 'render_design', render); mp.setattr(skingen, 'preview_sheet', sheet)
        r = {}
        for name, steps in (('fresh', ('create',)), ('after_preview', ('preview', 'create')),
                            ('no_reuse', ('preview', 'forget', 'create'))):
            skingen._MEMO.clear(); calls.update(render=0, sheet=0)
            shutil.rmtree(root / 'run', ignore_errors=True)                     # same folder and skin name every time
            for st in steps:
                if st == 'forget': skingen._MEMO.pop('render', None); continue
                views, info, log = {}, {}, []
                out, *_ = skingen.generate(SMALL_CAR, design(), 'speed', out_root=str(root / 'run'), log=log.append,
                                           views=views, info=info, write=st == 'create')
            r[name] = dict(files=sums(out), views={k: v.tobytes() for k, v in views.items()}, info=info, log=log,
                           calls=dict(calls))
        return r


def test_create_after_preview_paints_once(runs):
    n = runs['fresh']['calls']['render']
    assert n >= 1 and runs['after_preview']['calls']['render'] == n            # the Create reused the Preview's painting
    assert runs['no_reuse']['calls']['render'] == 2 * n


def test_create_after_preview_same_skin(runs):
    a, b, c = runs['fresh'], runs['after_preview'], runs['no_reuse']
    assert a['files'] == b['files'] == c['files'] and len(a['files']) > 3
    assert a['views'] == b['views'] == c['views'] and a['info'] == b['info'] == c['info']


def test_create_after_preview_same_messages(runs):
    assert runs['after_preview']['log'] == runs['no_reuse']['log']             # what the painting said is said again


def test_create_draws_no_unused_sheet(runs):
    assert all(r['calls']['sheet'] == 0 for r in runs.values())
