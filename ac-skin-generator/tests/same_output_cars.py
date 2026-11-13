"""Old code vs new code on several cars: the same three steps a user does, every output fingerprinted and timed.
  1. Preview (design A)   2. Preview after changing the colours (design B)   3. Create skin in car (design B)
R4S_VARIANT=2: a second design with the other features (tint, tyres, picture pattern, carbon, compressed, not 4K,
hand edits on the preview, copy from a stock skin).
Fingerprints: every view, the decal positions, the log text and (Create) every file written.
Design = Nik's saved settings and logos (read only), window stickers, wheels and lens colour on.
python tests/same_output_cars.py SRC_DIR OUT_JSON CAR [CAR ...]
  SRC_DIR = the code to test (a copy of the old version, or this folder). Scratch folder: OUT_JSON + '_out'.
Compare two runs with:  python tests/same_output_cars.py --compare OLD_JSON NEW_JSON"""
import hashlib, json, os, shutil, sys, time, warnings
warnings.filterwarnings('ignore')

if sys.argv[1] == '--compare':
    old, new = (json.load(open(p)) for p in sys.argv[2:4])
    bad = 0
    for car in old:
        if car not in new: print(f'{car}: missing in the new run'); bad += 1; continue
        o, n = old[car]['sums'], new[car]['sums']
        diff = sorted(k for k in set(o) | set(n) if o.get(k) != n.get(k))
        for k in [k for k in diff if k.endswith(' log')]:
            # the window-sticker messages come in a different order from run to run (old code too): same lines = same
            texts = []
            for p, tag in ((sys.argv[2], 'old'), (sys.argv[3], 'new')):
                f = f'{p}.{car}.{k.split()[0]}.log.txt'
                texts.append(sorted(open(f, encoding='utf-8').read().replace(os.path.abspath(p) + '_out', '<out>')
                                    .splitlines()) if os.path.isfile(f) else None)
            if texts[0] is not None and texts[0] == texts[1]: diff.remove(k)
        t = '  '.join(f'{s}: {old[car]["times"].get(s, 0):5.1f}s -> {new[car]["times"].get(s, 0):5.1f}s' for s in old[car]['times'])
        print(f'{car:48s} {"IDENTICAL" if not diff else "DIFFERENT"} ({len(o)} items)   {t}')
        for k in diff[:8]: print('     differs:', k)
        bad += bool(diff)
    print('PROBLEMS:', bad or 'none')
    sys.exit(1 if bad else 0)

src, out_json, cars = sys.argv[1], sys.argv[2], sys.argv[3:]
sys.path.insert(0, os.path.abspath(src))
import skingen
import rattys4skin
assert os.path.abspath(skingen.__file__).startswith(os.path.abspath(src)), skingen.__file__

ROOT = r'D:\SteamLibrary\steamapps\common\assettocorsa\content\cars'
TMP = os.path.abspath(out_json) + '_out'           # each run its own scratch folder (two runs at once must not clash)
APP = os.path.join(os.environ['APPDATA'], 'Rattys4SkinGenerator')

d = dict(skingen.DEFAULT_DESIGN)
s = json.load(open(os.path.join(APP, 'settings.json')))
d.update({k: v for k, v in s.items() if k in d})
d['logos'] = [dict(path=os.path.join(APP, 'logos', l['file']), place=p_, tint=l.get('tint'), bg=l.get('bg', 'auto'))
              for l in json.load(open(os.path.join(APP, 'logos.json'))) for p_ in rattys4skin.places_of(l)]
d.update(win_enable=True, wheel_colour='#d0d0d0', lens_colour='#ffd21f', beam_colour=None, number='101',
         team='RATTY RACING', name='NICKLEARSE101')
if d.get('pattern') == 'picture' and not d.get('pattern_image'): d['pattern'] = 'sweep'
d2 = dict(d, base='#1a3a8a', accent='#ff6a00')
RES = 4096 if s.get('hires', True) else None
VARIANT = os.environ.get('R4S_VARIANT', '1')
if VARIANT == '2':      # the other features: tint, tyres, picture pattern, carbon, compressed, not 4K, hand edits, copy-from
    HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = dict(d, win_tint='#203040', win_tint_dark=0.6, win_tint_windscreen=True, tyre_colour='#303030', carbon=True,
             avoid_mirror=True, compress=True, pattern='picture', pattern_mode='side_left', pattern_simplify='medium',
             pattern_image=os.path.join(HERE, 'starter_logos', 'ratty_racing_logo.jpg'), team_places=['doors', 'bonnet'],
             name_places=['doors'])
    d2 = dict(d, accent='#ff6a00')                # + hand edits made after the first preview (see below)
    RES = None


def h(b): return hashlib.sha256(b).hexdigest()


def img_sum(im): return h(im.mode.encode() + str(im.size).encode() + im.tobytes())


results = json.load(open(out_json)) if os.path.isfile(out_json) else {}
for car in cars:
    print('###', car, flush=True)
    skingen._MEMO.clear()
    sums, times = {}, {}
    try:
        skins = sorted(e for e in os.listdir(os.path.join(ROOT, car, 'skins')) if os.path.isdir(os.path.join(ROOT, car, 'skins', e)))
        copy_from = skins[0] if VARIANT == '2' and skins else None
        for step, design, write in (('preview_A', d, False), ('preview_B', d2, False), ('create_B', d2, True)):
            if VARIANT == '2' and step == 'preview_B':    # move / size / turn one box, delete another, edit the team text
                keys = [x['key'] for x in info.get('decals', [])]
                adj = {'team name:doors': dict(text='NIK RACING', colour='#ff0000')}
                if keys: adj[keys[0]] = dict(da=0.08, db=-0.03, scale=1.2, rot=6, flip=['left'])
                if len(keys) > 1: adj[keys[-1]] = dict(deleted=True)
                d2['adjust'] = adj
            shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
            views, info, lines = {}, {}, []
            t = time.time()
            out, *_ = skingen.generate(os.path.join(ROOT, car), dict(design), 'same_test', out_root=TMP, resolution=RES,
                                       log=lines.append, views=views, info=info, write=write, copy_other_from=copy_from)
            views['all'] = rattys4skin.App.compose(views)
            views['all_rgba'] = rattys4skin.App.compose(views, rgba=True)
            if write: views['all'].save(os.path.join(out, 'generator_preview.png'))
            times[step] = round(time.time() - t, 1)
            for k, im in views.items(): sums[f'{step} view {k}'] = img_sum(im)
            sums[f'{step} info'] = h(json.dumps(info, sort_keys=True, default=str).encode())
            sums[f'{step} log'] = h(chr(10).join(map(str, lines)).encode())
            open(out_json + f'.{car}.{step}.log.txt', 'w', encoding='utf-8').write(chr(10).join(map(str, lines)))
            if write:
                for root, _, files in os.walk(out):
                    for f in files:
                        p = os.path.join(root, f)
                        sums[f'{step} file {os.path.relpath(p, out)}'] = h(open(p, 'rb').read())
            print(f'  {step}: {times[step]}s', flush=True)
    except Exception as e:
        import traceback; traceback.print_exc()
        sums['error'] = repr(e)
    results[car] = dict(sums=sums, times=times)
    json.dump(results, open(out_json, 'w'), indent=1, sort_keys=True)
print('saved', out_json)
