"""Window stickers on every installed car: banner, rear-window and side-window number / name, the way the app
makes them, and which ones are left off and why. One JSON per car.
python tests/windows_all_cars.py OUT_DIR [CARS_DIR] [WORKERS] [CAR ...]"""
import glob, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.path.insert(0, os.environ.get('SKINGEN_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def one(car_dir, out):
    import warnings; warnings.filterwarnings('ignore')
    import skingen
    name = os.path.basename(os.path.normpath(car_dir))
    t0 = time.time()
    r = dict(car=name)
    try:
        car = skingen.Car(car_dir, log=lambda s: None)
        d = dict(skingen.DEFAULT_DESIGN, win_enable=True, win_side_place='rear', name='Driver Name')
        logs = []
        info = {}
        made, layers = skingen.make_window_stickers(car, d, {}, None, logs.append, 2048, info)
        r['asked'] = sorted({x['label'] for x in info.get('decals', [])})
        r['left_off'] = [l.strip() for l in logs if 'left off' in l]
        r['no_room'] = [l.strip() for l in logs if 'no room' in l or 'not placed' in l]
        r['skipped'] = [l.strip() for l in logs if 'skipped' in l]
        r['textures'] = sorted(made)
        r['glass'] = next((l for l in logs if l.startswith('windows: glass =')), '')
    except Exception as e:
        r['error'] = f'{type(e).__name__}: {e}'
    r['secs'] = round(time.time() - t0, 1)
    json.dump(r, open(os.path.join(out, name + '.json'), 'w', encoding='utf8'), indent=1)
    return name, r.get('error')


if __name__ == '__main__':
    out = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    os.makedirs(out, exist_ok=True)
    cars = [os.path.join(root, c) for c in sys.argv[4:]] or sorted(glob.glob(os.path.join(root, '*', '')))
    fails = {}
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(one, c, out) for c in cars]
        for i, f in enumerate(as_completed(futs)):
            name, err = f.result()
            if err: fails[name] = err
            if i % 50 == 0: print(f'{i}/{len(cars)}', flush=True)
    json.dump(fails, open(os.path.join(out, '_failed.json'), 'w'), indent=1)
    print(f'done: {len(cars)} cars, {len(fails)} failed')
