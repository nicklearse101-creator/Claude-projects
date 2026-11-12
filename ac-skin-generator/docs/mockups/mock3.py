"""Part 2 pictures: ghost = the car being edited; after a preview and before one. Throwaway."""
import os, shutil
import mock, mock2
from mock import P
HERE = os.path.dirname(os.path.abspath(__file__))
shutil.copy(os.path.join(HERE, 'ghost_talbot.png'), os.path.join(HERE, 'ghost_front.png'))
th = dict(mock.THEMES['B_carbon_orange']); th['name'] = ''
mock.preview_bg = mock2.preview_bg_mix
mock.render(th, 'E_preview_with_own_ghost.jpg')

# before any preview: no car drawn, just its ghost and a prompt
orig_text = mock.text
SUB = {'LEFT SIDE': 'TALBOT SUNBEAM LOTUS', 'chucknorris  ·  DOORS (BIG)  ·  selected': 'NO PREVIEW YET',
       'PREVIEW ONLY · NOT SAVED': 'READY', 'STAGE 4 / 6  ·  LOGOS': 'READY', '66%': ''}
def text(img, x, y, s, *a, **k):
    if s.startswith(('talbot_', 'Pattern:', 'Number 101', 'Logos:', 'PREVIEW ONLY -')):
        return 0
    return orig_text(img, x, y, SUB.get(s, s), *a, **k)
mock.text = text
def place_car(img, x, y, width, floor_y):
    orig_text(img, 1035, 600, 'PRESS  PREVIEW', mock.bahn(46), mock.hexc('#ffffff'), anchor='mm', italic=0.2,
              glow=mock.hexc(th['acc'], 200))
    orig_text(img, 1035, 648, 'to see your livery on the car', mock.segoe(15), mock.hexc(th['muted']), anchor='mm')
    return -9999, -9999, 1.0
mock.place_car = place_car
mock.dashed_rect = lambda *a, **k: None
_glow = mock.glow_shape
mock.render(th, 'F_before_preview.jpg')
