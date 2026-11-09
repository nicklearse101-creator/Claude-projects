"""Run the generator (all features on) over many installed cars and report crashes.
python tests/batch_cars.py OUT_DIR [N] [CARS_DIR]"""
import glob, os, random, shutil, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import skingen

out = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
root = sys.argv[3] if len(sys.argv) > 3 else r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
cars = sorted(c for c in os.listdir(root) if os.path.isdir(os.path.join(root, c, 'skins')))
random.seed(7)
pick = random.sample(cars, min(n, len(cars)))
d = dict(skingen.DEFAULT_DESIGN)
d.update(name='Nicklearse101', win_enable=True, lens_colour='#ffd21f', beam_colour='#fff2c8', wheel_colour='#7020d2',
         pattern='hockey')
ok, fail, skip = [], [], []
for car in pick:
    t = time.time()
    dst = os.path.join(out, car)
    shutil.rmtree(dst, ignore_errors=True)
    try:
        skingen.generate(os.path.join(root, car), d, 'batch', out_root=dst, log=lambda s: None)
        ok.append(car); print(f'OK    {car} ({time.time() - t:.0f}s)', flush=True)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        skip.append((car, str(e))); print(f'SKIP  {car}: {str(e)[:100]}', flush=True)
    except Exception as e:
        fail.append((car, traceback.format_exc())); print(f'FAIL  {car}: {type(e).__name__}: {e}', flush=True)
    shutil.rmtree(dst, ignore_errors=True)
print(f'\n{len(ok)} ok, {len(skip)} clear message, {len(fail)} crashed')
for car, tb in fail:
    print('\n=====', car); print(tb[-1500:])
