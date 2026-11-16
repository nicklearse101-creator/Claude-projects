"""Liveries on four cars for the poster - preview only (write=False: nothing is written to any car)."""
import os, sys
sys.path.insert(0, r'D:\Claude\Claude-\ac-skin-generator')
import skingen
import rattys4skin as R
import numpy as np

# poster only: parts with no livery texture (tyres, rims, trim) drawn dark instead of the preview's light grey
_geo = skingen._view_geometry
def _dark(*a, **k):
    Hp, Wp, ys, xs, Gt, tx, uv, ti, S = _geo(*a, **k)
    return Hp, Wp, ys, xs, (Gt.astype(np.float32) * 0.26 + 8).astype(np.uint8), tx, uv, ti, S
skingen._view_geometry = _dark

ROOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
OUT = os.path.dirname(os.path.abspath(__file__))        # (car renders are .png: not kept in git)
LOGO = r'D:\Claude\Claude-\ac-skin-generator\starter_logos\ratty_racing_logo.jpg'
F = R.list_fonts()
jobs = [
    ('ks_ferrari_488_gt3', dict(base='#101014', accent='#9b3dff', accent2='#ff6a00', text='#ffffff', pattern='ratty_swoosh',
                                number='23', team='RATTY RACING', name='NICKLEARSE101', font_team=F['Racing: Russo One'],
                                font_number=F['Racing: Orbitron Black'], font_name=F['Racing: Exo 2 Black Italic'])),
    ('ks_porsche_911_gt3_r_2016', dict(base='#f4f4f4', accent='#ff6a00', accent2='#9b3dff', text='#111111', pattern='gt_sash',
                                       number='7', team='RATTY RACING', halftone=True, font_team=F['Racing: Racing Sans One'],
                                       font_number=F['Racing: Bungee'])),
    ('ks_audi_r8_lms', dict(base='#0d1b3d', accent='#00c8ff', accent2='#ffffff', text='#ffffff', pattern='kinetic_arrows',
                            number='101', team='RATTY RACING', font_team=F['Racing: Orbitron Black'], font_number=F['Racing: Russo One'])),
    ('wtcc_chevrolet_lacetti', dict(base='#ffd400', accent='#111111', accent2='#e10600', text='#111111', pattern='splinter_camo',
                                    number='44', team='RATTY RACING', font_team=F['Racing: Black Ops One'], font_number=F['Racing: Squada One'])),
]
only = sys.argv[1:] or [c for c, _ in jobs]
for car, extra in jobs:
    if car not in only: continue
    d = dict(skingen.DEFAULT_DESIGN, logos=[dict(path=LOGO, place='bonnet', tint=False, bg='auto'),
                                             dict(path=LOGO, place='rear_quarters', tint=False, bg='auto')],
             win_enable=True, win_banner='RATTY RACING', team_places=['front_wings', 'boot', 'rear'], name_places=['front_wings'],
             number_doors=True, number_roof=True)
    d.update(extra)
    views = {}
    try:
        skingen.generate(os.path.join(ROOT, car), d, 'poster', log=lambda *a: None, views=views, info={}, write=False)
        for v in ('left', 'right', 'top', 'front'):
            views[v].save(os.path.join(OUT, f'{car}_{v}.png'))
        print('done', car, flush=True)
    except Exception as e:
        print('FAILED', car, e, flush=True)
