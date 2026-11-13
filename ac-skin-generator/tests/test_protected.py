r"""Cars whose model is protected (CSP kn5 encryption scrambles the texture mapping for every tool but the game):
the app says so plainly instead of quietly giving a plain colour, and never tries to undo the protection.
python -m pytest -p no:cacheprovider tests/test_protected.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys, types
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

CARS = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'


def mesh(pos, uv, idx):
    return types.SimpleNamespace(pos=np.asarray(pos, float), uv=np.asarray(uv, float), idx=np.asarray(idx).reshape(-1, 3))


def grid(n=60, size=1.0, scramble=False, seed=0):
    """A flat panel of n x n quads, size metres, mapped onto the texture; scramble = random texture spots per corner."""
    rng = np.random.default_rng(seed)
    g = np.linspace(0, 1, n + 1)
    X, Y = np.meshgrid(g, g)
    pos = np.stack([X.ravel() * size, Y.ravel() * size, np.zeros(X.size)], 1)
    uv = np.stack([X.ravel(), -Y.ravel()], 1)
    if scramble: uv = rng.uniform(-1, 2, uv.shape)
    idx = []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            idx += [a, a + 1, a + n + 1, a + 1, a + n + 2, a + n + 1]
    return mesh(pos, uv, idx)


def test_scrambled_mapping_detected():
    assert skingen.scrambled_uv([grid(scramble=True)]) > 0.5
    assert skingen.scrambled_uv([grid()]) < 0.05
    assert skingen.scrambled_uv([grid(n=10, size=0.05)]) < 0.05        # small, honestly mapped parts are fine


def test_protected_car_said_plainly(tmp_path):
    info, log = {}, []
    skingen.generate(os.path.join(CARS, 'gt4_mclaren_570s'), dict(skingen.DEFAULT_DESIGN), 'p', out_root=str(tmp_path),
                     log=log.append, info=info, write=False)
    assert info.get('protected') is True
    assert any('protected' in l and 'plain colour' in l for l in log)
    assert info.get('missing') == []                                 # nothing to pick: placing can't work on it


def test_normal_car_not_protected(tmp_path):
    info = {}
    skingen.generate(os.path.join(CARS, 'abarth500'), dict(skingen.DEFAULT_DESIGN), 'p', out_root=str(tmp_path),
                     log=lambda *a: None, info=info, write=False)
    assert not info.get('protected')
