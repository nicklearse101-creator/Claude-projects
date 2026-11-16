r"""Sporty fonts for the team and driver names (Nik 16 Nov: "we need more interesting/sporty looking fonts").
Free Google Fonts (Open Font Licence) built into the app, at the top of every font list as "Racing: ...", so friends
get them whatever fonts their PC has. Variable fonts are used at a heavy weight ("file.ttf#Black").
python -m pytest -p no:cacheprovider tests/test_racing_fonts.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen
import rattys4skin as R

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def racing():
    return [(n, p) for n, p in R.list_fonts().items() if n.startswith('Racing: ')]


def test_racing_fonts_listed_first():
    names = list(R.list_fonts())
    rf = racing()
    assert len(rf) >= 16
    assert names[:len(rf)] == [n for n, _ in rf]
    for _, p in rf:
        assert os.path.isfile(p.split('#')[0])


def test_every_racing_font_writes():
    for n, p in racing():
        im = skingen.text_image('RATTY 23', 80, (255, 255, 255), p)
        a = np.asarray(im)[..., 3]
        assert im.width > 100 and (a > 128).mean() > 0.05, n


def test_heavy_weight_of_a_variable_font():
    ink = lambda inst: (np.asarray(skingen.text_image('RACING', 80, (255, 255, 255),
                                                     os.path.join(HERE, 'fonts', 'Orbitron[wght].ttf') + inst))[..., 3] > 128).sum()
    assert ink('#Black') > ink('#Regular') * 1.3


def test_licences_and_build():
    fams = {f.split('-')[0].split('[')[0].lower() for f in os.listdir(os.path.join(HERE, 'fonts')) if f.endswith('.ttf')}
    lic = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(HERE, 'fonts', 'licences'))}
    assert fams <= lic
    assert "'fonts'" in open(os.path.join(HERE, 'build.py'), encoding='utf8').read()
