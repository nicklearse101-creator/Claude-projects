"""Catalogue every installed car (what the generator finds: body / wheel textures, glass, stickers, lights,
every material with its textures and meshes) into one JSON per car, for the name dictionary work.
python tests/catalogue_all_cars.py OUT_DIR [CARS_DIR] [WORKERS]"""
import glob, json, os, sys, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def one(car_dir, out):
    import warnings; warnings.filterwarnings('ignore')
    import skingen
    name = os.path.basename(os.path.normpath(car_dir))
    try:
        skingen.car_catalogue(car_dir, out)
        return name, None
    except Exception as e:
        return name, f'{type(e).__name__}: {e}'


if __name__ == '__main__':
    out = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    os.makedirs(out, exist_ok=True)
    cars = sorted(glob.glob(os.path.join(root, '*', '')))
    fails = {}
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(one, c, out) for c in cars]
        for i, f in enumerate(as_completed(futs)):
            name, err = f.result()
            if err: fails[name] = err
            if i % 50 == 0: print(f'{i}/{len(cars)}', flush=True)
    json.dump(fails, open(os.path.join(out, '_failed.json'), 'w'), indent=1)
    print(f'done: {len(cars)} cars, {len(fails)} failed')
