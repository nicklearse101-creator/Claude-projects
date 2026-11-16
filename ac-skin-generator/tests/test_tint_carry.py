r"""A tester "couldn't remove a window tint once it was tinted" (Nik 16 Nov). Cause: "Windows etc. from" listed skins
the app had made, so a new skin copied the old one's tinted glass (and its CSP sections). The list now shows only the
car's own skins, and the engine refuses an app-made skin as the source (old saved settings).
python -m pytest -p no:cacheprovider tests/test_tint_carry.py -q --basetemp=D:\ClaudeData\tmp\pytest"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen

TALBOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars\talbot_sunbeam_lotus_81_works_backup_v6'


def test_source_list_has_only_the_cars_own_skins():
    made = [s for s in skingen.stock_skins(TALBOT) if os.path.isfile(os.path.join(TALBOT, 'skins', s, 'generator_preview.png'))]
    assert 'ratty_s' in made                                      # (Nik's tinted Talbot skin is one of them)
    src = skingen.source_skins(TALBOT)
    assert src and not set(src) & set(made)


def test_tint_off_gives_clear_glass_even_from_a_tinted_skin(tmp_path):
    logs = []
    d = dict(skingen.DEFAULT_DESIGN, win_tint=None, win_enable=False, logos=[], number='', team='', name='')
    skingen.generate(TALBOT, d, 'clear', out_root=str(tmp_path), copy_other_from='ratty_s', log=logs.append)
    out = tmp_path / 'clear'
    assert not (out / 'glass.png').exists() and not (out / 'ext_config.ini').exists()
    assert any('made by this app' in m for m in logs)
