r"""Edit a skin that is already on the car (Nik 16 Nov): a stock skin, a downloaded one or one made earlier.
 - engine: design['base_skin'] = a skin's folder: its own paint stays, the design (logos, names, number) goes on top;
 - app: "Start from" on the Car tab lists the car's skins; picking one loads it and previews it by itself. A skin
   made with this app (1.12+) comes back fully editable (its design is saved in it, r4s_design.json); any other skin
   is the starting paint and saves into a NEW folder - the original is never overwritten.
python -m pytest -p no:cacheprovider tests/test_edit_skin.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import json, os, sys
import numpy as np
import pytest
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_car_change import app, pick, preview          # noqa: F401  (app is a fixture)
import rattys4skin as R
import skingen

TALBOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6'


# ---------------------------------------------------------------- engine
def test_skin_paint_kept_under_the_design():
    d = dict(skingen.DEFAULT_DESIGN, base_skin='CRT-Kris', pattern='none', base='#00ff00', number='', team='', name='',
             logos=[], halftone=False)
    *_, car, tms, tex_out = skingen.generate(TALBOT, d, 'x', log=lambda *a: None, write=False)
    tm = tms['body.dds']
    # what the game shows for that skin: its body texture times its colour detail texture (Kunos style); the new
    # skin gets a white detail texture, so that colour is baked into the body texture
    det = np.asarray(car.stock_texture('metal_detail.dds', 'CRT-Kris').convert('RGB')).reshape(-1, 3).mean(0) / 255
    want = (np.asarray(car.stock_texture('body.dds', 'CRT-Kris').convert('RGB').resize((tm.W, tm.H))) * det).astype(int)
    got = np.asarray(tex_out['body.dds'].convert('RGB')).astype(int)
    diff = np.abs(got[tm.yy, tm.xx] - want[tm.yy, tm.xx]).mean()
    assert diff < 12                                           # the skin's own paint, not the green base colour


# ---------------------------------------------------------------- app
def make_skin(app, name, made=False, design=None):
    d = os.path.join(app.vars['cars_dir'].get(), 'car_a', 'skins', name)
    os.makedirs(d, exist_ok=True)
    Image.new('RGB', (8, 8)).save(os.path.join(d, 'preview.jpg'))
    if made: Image.new('RGB', (8, 8)).save(os.path.join(d, 'generator_preview.png'))
    if design is not None: json.dump(design, open(os.path.join(d, 'r4s_design.json'), 'w'))
    return d


def runs(app, monkeypatch):
    calls = []
    monkeypatch.setattr(app, 'run', lambda save, auto=False: calls.append(save))
    return calls


def test_start_from_lists_the_cars_skins(app):
    make_skin(app, 'mine', made=True)
    app.refresh_skins()
    vals = list(app.start_box['values'])
    assert vals[0].startswith('New livery') and any(v.startswith('stock') for v in vals)
    assert any(v.startswith('mine') and 'made with the app' in v for v in vals)


def test_stock_skin_is_a_starting_point_in_a_new_folder(app, monkeypatch):
    calls = runs(app, monkeypatch)
    app.vars['team'].set('OLD')
    app.load_skin('stock')
    d = app.design()
    assert d['base_skin'] == 'stock' and d['team'] == ''
    assert app.vars['skin_name'].get() == 'stock custom'                 # never the original's folder
    assert app.vars['copy_from'].get() == 'stock'                       # its windows, interior... come along
    assert calls == [False]                                             # previewed by itself
    make_skin(app, 'stock_custom', made=True)
    app.load_skin('stock')
    assert app.vars['skin_name'].get() == 'stock custom 2'


def test_app_skin_comes_back_editable(app, monkeypatch, tmp_path):
    Image.new('RGBA', (20, 20), (255, 0, 0, 255)).save(os.path.join(R.LOGO_DIR, 'rat.png'))
    app.library.append(dict(file='rat.png', name='rat', place='', places=[], tint=False)); app.refresh_library()
    rec = dict(version=R.VERSION, skin_name='Race Day', livery=dict(team='RATTY', name='NIK', number='7', pattern='sweep'),
               logos=[dict(file='rat.png', places=['bonnet', 'doors'], bg='auto', tint=True), dict(file='gone.png', places=['roof'])],
               adjust={'logo:bonnet': {'da': 0.1}})
    make_skin(app, 'race_day', made=True, design=rec)
    calls = runs(app, monkeypatch)
    app.load_skin('race_day')
    d = app.design()
    assert (d['team'], d['name'], d['number'], d['pattern']) == ('RATTY', 'NIK', '7', 'sweep')
    assert d['base_skin'] is None and app.vars['skin_name'].get() == 'Race Day'
    assert sorted(l['place'] for l in d['logos']) == ['bonnet', 'doors'] and d['logos'][0]['tint'] is True
    assert d['adjust'] == {'logo:bonnet': {'da': 0.1}}
    assert calls == [False]


def test_create_saves_the_design_in_the_skin(app, tmp_path):
    os.makedirs(tmp_path / 'out', exist_ok=True)
    app.vars['team'].set('SAVED TEAM')
    app.vars['skin_name'].set('My Skin')
    import time
    t = time.time()

    def check():                          # the window's main loop runs (worker threads hand results back through it)
        if (not app.busy and time.time() - t > 0.5) or time.time() - t > 20: app.quit()
        else: app.after(50, check)
    app.after(0, lambda: app.run(save=True)); app.after(50, check)
    app.mainloop()
    rec = json.load(open(tmp_path / 'out' / 'r4s_design.json', encoding='utf8'))
    assert rec['livery']['team'] == 'SAVED TEAM' and rec['skin_name'] == 'My Skin'


def test_new_livery_forgets_the_skin(app, monkeypatch):
    runs(app, monkeypatch)
    app.load_skin('stock')
    monkeypatch.setattr(R.messagebox, 'askyesno', lambda *a, **k: True)
    app.new_livery()
    assert app.design()['base_skin'] is None
