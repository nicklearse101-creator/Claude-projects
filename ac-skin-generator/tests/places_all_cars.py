"""Which logo places work on every installed car: a logo is put on every place (doors, bonnet, roof, boot...)
the way the app does it, and each car's JSON says which places took it and which refused it (and why).
For the name dictionary work: run before / after a change and compare.
python tests/places_all_cars.py OUT_DIR [CARS_DIR] [WORKERS] [CAR ...]"""
import glob, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
# SKINGEN_DIR: another copy of the generator to test (e.g. the last commit's, for a 'before' run)
sys.path.insert(0, os.environ.get('SKINGEN_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PLACES = ['doors', 'bonnet', 'front_wings', 'rear_quarters', 'lower_doors', 'roof', 'boot', 'rear', 'front']
MAX_SKINS = 6        # enough stock skins to find the paint, keeps big car packs quick


def logo_file(out):
    from PIL import Image, ImageDraw
    p = os.path.join(out, '_logo.png')
    if not os.path.isfile(p):
        im = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((4, 4, 396, 196), 30, fill=(230, 30, 30, 255))
        im.save(p)
    return p


def one(car_dir, out, logo):
    import warnings; warnings.filterwarnings('ignore')
    import numpy as np
    import skingen
    name = os.path.basename(os.path.normpath(car_dir))
    t0 = time.time()
    r = dict(car=name)
    try:
        car = skingen.Car(car_dir, log=lambda s: None)
        r['skins'] = len(car.skins)
        car.skins = car.skins[:MAX_SKINS]
        r['body'] = car.body_textures
        tms = []                                 # every body texture: decals land on whichever one has the panel
        for tex in car.body_textures:
            if skingen.uv_overlap(car.meshes_for(tex)) > 3.0:
                if not tms: r['plain_colour_only'] = True
                continue
            ref = None
            for s in car.skins:
                ref = car.stock_texture(tex, s)
                if ref is not None: break
            if ref is None: ref = skingen.load_image(car.kn5.textures[tex])
            W, H = ref.size
            if max(W, H) != 2048:                    # the app works at 2048 or more
                k = 2048 / max(W, H); W, H = int(W * k), int(H * k)
            tm = skingen.TexelMap(car.meshes_for(tex), W, H, lambda s: None); tm.tex = tex
            occ = [m.pos[m.idx] for m in car.kn5.meshes if m.mat is not None and len(m.idx) and not skingen.see_through(m.mat)
                   and m.mat.samplers.get('txDiffuse') != tex and 'shadow' not in m.name.lower()]
            tm.occluders = np.concatenate(occ) if occ else None
            base, alpha, paint, shade = skingen.stock_analysis(car, tex, W, H, tm, lambda s: None)
            tms.append((tex, tm, paint))
        if tms and not r.get('plain_colour_only'):
            tex, tm, paint = tms[0]
            r['paint'] = round(float(paint.sum() / max(1, tm.covered.sum())), 3)
            prof = skingen.side_profile(car, tm, paint)
            pan = skingen.top_panels(car, tm, paint, prof['belt'], tex)
            r['top_panels'] = {k: [round(float(v), 3) for v in x] for k, x in pan.items()}
            d = dict(skingen.DEFAULT_DESIGN, team='', name='', number='',
                     logos=[dict(path=logo, place=p, tint=False) for p in PLACES])
            rgb = skingen.rgb
            logs = []
            decals = skingen.place_decals(car, tm, paint, d, prof, rgb(d['base']), rgb(d['accent']), rgb(d['accent2']),
                                          rgb(d['text']), logs.append)
            landed = {}
            for i, (tex, tm, paint) in enumerate(tms):
                col = np.zeros((len(tm.P), 3))
                _, _, forced, got = skingen.apply_decals(col, tm, decals, logs.append if i == 0 else (lambda m: None),
                                                         allow_move=(i == 0))
                for k in got:
                    landed.setdefault(decals[k].key.split(':')[1], set()).add(decals[k].view)
            asked = {}
            for dc in decals: asked.setdefault(dc.key.split(':')[1], []).append(dc.view)
            r['landed'] = {k: sorted(v) for k, v in landed.items()}
            r['refused'] = {p: ('no top panel found' if p not in asked else
                                'missed ' + ','.join(v for v in asked[p] if v not in landed.get(p, ())))
                            for p in PLACES if len(landed.get(p, ())) < max(1, len(asked.get(p, [])))}
            r['log'] = [l for l in logs if 'no surface' in l or 'only' in l]
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
    logo = logo_file(out)
    fails = {}
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(one, c, out, logo) for c in cars]
        for i, f in enumerate(as_completed(futs)):
            name, err = f.result()
            if err: fails[name] = err
            if i % 50 == 0: print(f'{i}/{len(cars)}', flush=True)
    json.dump(fails, open(os.path.join(out, '_failed.json'), 'w'), indent=1)
    print(f'done: {len(cars)} cars, {len(fails)} failed')
