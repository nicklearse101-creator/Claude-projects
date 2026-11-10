"""Run the generator (windows on) over the cars named: python tests/some_cars.py OUT_DIR CAR [CAR ...]"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skingen
root = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
d = dict(skingen.DEFAULT_DESIGN); d.update(win_enable=True, name='Nicklearse101')
for c in sys.argv[2:]:
    try:
        skingen.generate(os.path.join(root, c), d, 't', out_root=sys.argv[1], log=lambda s: None); print('OK', c, flush=True)
    except Exception as e:
        print('ERR', c, type(e).__name__, str(e)[:100], flush=True)
    shutil.rmtree(sys.argv[1], ignore_errors=True)
